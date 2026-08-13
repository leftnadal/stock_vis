"""
CS-P3-UNIVERSE Slice1 — 승인 명단(exact/alias 확정 후보)을 유니버스에 편입.

경로: FMP 프로필(업종 2단·CIK) → Stock.update_or_create → DailyPrice 백필.
재사용: StockService.get_company_profile + daily_price_backfill 서비스 (FDXF 편입으로 입증된 경로).
멱등: update_or_create + 겹침대조 upsert (재실행 안전).

호출당 FMP = 심볼당 2콜 (프로필 1 + 가격 1). get_quote 미사용(3콜 회피).

사용:
    python manage.py induct_cs_universe --manifest /path/to/cs_p3_manifest.json --dry-run
    python manage.py induct_cs_universe --manifest /path/to/cs_p3_manifest.json --years 1
    python manage.py induct_cs_universe --manifest ... --limit 5      # 파일럿
    python manage.py induct_cs_universe --manifest ... --skip-prices  # 프로필만
"""

import json
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

logger = logging.getLogger("CS_P3_INDUCT")


class Command(BaseCommand):
    help = "CS-P3 승인 명단 유니버스 편입 (FMP 프로필+CIK → Stock → 가격 백필, 멱등)."

    def add_arguments(self, parser):
        parser.add_argument("--manifest", required=True, help="cs_p3_manifest.json 경로")
        parser.add_argument("--years", type=int, default=1, help="가격 백필 기간(년, 기본1≈250거래일).")
        parser.add_argument("--limit", type=int, default=None, help="상위 N종만(파일럿).")
        parser.add_argument("--skip-prices", action="store_true", help="프로필/CIK만, 가격 백필 생략.")
        parser.add_argument("--dry-run", action="store_true", help="FMP/DB 무접촉, 계획만 출력.")

    def handle(self, *args, **opts):
        from django.conf import settings

        from packages.shared.api_request.providers.fmp.client import FMPClient
        from packages.shared.api_request.stock_service import StockService
        from packages.shared.stocks.models import Stock
        from packages.shared.stocks.services.daily_price_backfill import backfill_daily_prices

        with open(opts["manifest"]) as f:
            manifest = json.load(f)
        if opts["limit"]:
            manifest = manifest[: opts["limit"]]
        tickers = [m["ticker"].upper() for m in manifest]
        cik_by = {m["ticker"].upper(): m.get("cik") for m in manifest}
        dry = opts["dry_run"]
        prefix = "[DRY RUN] " if dry else ""

        self.stdout.write(f"{prefix}편입 대상 {len(tickers)}종 (years={opts['years']} skip_prices={opts['skip_prices']})")
        if dry:
            self.stdout.write("계획(FMP/DB 무접촉): " + ", ".join(tickers))
            missing_cik = [t for t in tickers if not cik_by.get(t)]
            self.stdout.write(f"CIK 결측: {len(missing_cik)} {missing_cik}")
            return

        svc = StockService()
        # ── Phase 1: 프로필 + CIK → Stock ─────────────────────────────
        created, updated, dropped = [], [], {}
        for t in tickers:
            try:
                resp = svc.get_company_profile(t)
            except Exception as e:  # noqa: BLE001
                dropped[t] = f"profile_exception:{repr(e)[:60]}"
                logger.warning("CS_P3 profile 예외 %s: %s", t, e)
                continue
            if not getattr(resp, "success", False) or resp.data is None:
                dropped[t] = f"profile_fail:{getattr(resp, 'error', 'no_coverage')}"
                logger.warning("CS_P3 profile 실패(FMP 무커버?) %s", t)
                continue
            p = resp.data
            defaults = {
                "stock_name": p.name,
                "sector": p.sector,
                "industry": p.industry,
                "market_capitalization": p.market_cap,
                "pe_ratio": p.pe_ratio,
                "eps": p.eps,
                "beta": p.beta,
                "dividend_yield": p.dividend_yield,
                "exchange": p.exchange,
                "description": p.description,
                "asset_type": "Common Stock",
                "cik": cik_by.get(t),
            }
            defaults = {k: v for k, v in defaults.items() if v is not None}
            _, was_created = Stock.objects.update_or_create(symbol=t, defaults=defaults)
            (created if was_created else updated).append(t)
            logger.info("CS_P3 induct %s (%s) sector=%s cik=%s", t, "new" if was_created else "upd", p.sector, cik_by.get(t))

        self.stdout.write(self.style.SUCCESS(
            f"프로필 편입: created={len(created)} updated={len(updated)} dropped={len(dropped)}"
        ))
        if dropped:
            self.stdout.write(self.style.WARNING(f"드롭(FMP 무커버 등): {dropped}"))

        # ── Phase 2: 가격 백필 ────────────────────────────────────────
        if opts["skip_prices"]:
            self.stdout.write("가격 백필 생략(--skip-prices).")
            return
        induced = created + updated
        if not induced:
            self.stdout.write("편입 성공 0종 — 가격 백필 생략.")
            return
        to_date = timezone.now().date()
        from_date = to_date - timedelta(days=365 * opts["years"])
        client = FMPClient(api_key=settings.FMP_API_KEY)
        r = backfill_daily_prices(client, induced, from_date, to_date, dry_run=False)
        self.stdout.write(self.style.SUCCESS(
            f"가격 백필: written={r['written']} symbols_written={len(r['symbols_written'])} "
            f"halted={len(r['halted'])} errors={len(r['errors'])}"
        ))
        if r["halted"]:
            self.stdout.write(self.style.WARNING(f"겹침 정지: {r['halted']}"))
        if r["errors"]:
            self.stdout.write(f"가격 errors: {dict(list(r['errors'].items())[:20])}")
        # 커버리지 요약 (편입 KPI용)
        covered = len(r["symbols_written"])
        self.stdout.write(f"가격 커버: {covered}/{len(induced)}종 적재")
