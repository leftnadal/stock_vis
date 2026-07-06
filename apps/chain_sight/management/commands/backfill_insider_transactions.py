"""
InsiderTransactionRecord 백필 (TH-2, 1회성 — beat 아님).

설계서 theme_heat_design.md v1.2.1 §5.1:
- 대상 = EOD 스크리닝 유니버스(S&P 500) ∪ 테마 구성종목. Cycle 1 은 sector 엔티티만이라
  테마 구성종목은 S&P 500 에 포섭 → 유니버스 = SP500Constituent(is_active).
- 깊이 3년, E1 페이지네이션 순회, dedup_key upsert 멱등.
- FMP 접근: docs/audits/fmp_insider_access_report.md (E1/E2/E3 PASS).

사용:
    python manage.py backfill_insider_transactions --dry-run          # 표본 10종목 연결/형상 검증 (무적재)
    python manage.py backfill_insider_transactions --dry-run --limit 10
    python manage.py backfill_insider_transactions --limit 20         # 20종목 실백필
    python manage.py backfill_insider_transactions                    # 전체 유니버스 3년 백필
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.chain_sight.services.insider_service import backfill_symbol, map_fmp_row
from packages.shared.api_request.providers.fmp.client import (
    FMPClient,
    FMPPremiumError,
)
from packages.shared.stocks.models import SP500Constituent


class Command(BaseCommand):
    help = "FMP E1 로 InsiderTransactionRecord 3년 백필 (멱등 upsert). --dry-run 은 무적재 검증."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="무적재 — 표본 연결/형상만 검증")
        parser.add_argument("--limit", type=int, default=None, help="대상 종목 수 제한 (표본)")
        parser.add_argument("--years", type=int, default=3, help="백필 깊이 (년, 기본 3)")

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        years = opts["years"]
        today = timezone.now().date()
        cutoff = today - timedelta(days=365 * years)

        symbols = list(
            SP500Constituent.objects.filter(is_active=True)
            .order_by("symbol")
            .values_list("symbol", flat=True)
        )
        # FMP 프리미엄 402 회피: '.' 포함 심볼 제외 (Bug #23)
        symbols = [s for s in symbols if "." not in s]

        limit = opts["limit"]
        if dry_run and limit is None:
            limit = 10  # dry-run 기본 표본
        if limit is not None:
            symbols = symbols[:limit]

        client = FMPClient(api_key=settings.FMP_API_KEY)
        self.stdout.write(
            f"대상 {len(symbols)}종목 · 깊이 {years}년 (cutoff {cutoff}) · "
            f"{'DRY-RUN(무적재)' if dry_run else '실백필'}"
        )

        if dry_run:
            self._dry_run(client, symbols)
            return

        totals = {"created": 0, "updated": 0, "skipped": 0, "future_skipped": 0,
                  "pages": 0, "premium": 0, "errors": 0}
        for i, sym in enumerate(symbols, 1):
            try:
                res = backfill_symbol(client, sym, cutoff)
                for k in ("created", "updated", "skipped", "future_skipped", "pages"):
                    totals[k] += res[k]
                if i % 25 == 0:
                    self.stdout.write(f"  … {i}/{len(symbols)} (누적 created={totals['created']})")
            except FMPPremiumError:
                totals["premium"] += 1
                self.stderr.write(f"  premium skip: {sym}")
            except Exception as e:  # noqa: BLE001 — 백필 격리, 한 종목 실패가 전체 중단 금지
                totals["errors"] += 1
                self.stderr.write(f"  error {sym}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"완료: created={totals['created']} updated={totals['updated']} "
            f"skipped={totals['skipped']} future_skipped={totals['future_skipped']} "
            f"pages={totals['pages']} premium={totals['premium']} errors={totals['errors']}"
        ))

    def _dry_run(self, client, symbols):
        """표본 page0 조회 → 행수·거래일 범위 리포트 (무적재)."""
        total_rows = 0
        for sym in symbols:
            try:
                rows = client.get_insider_trading_search(sym, page=0, limit=100)
            except FMPPremiumError:
                self.stdout.write(f"  {sym:6} premium(402) skip")
                continue
            except Exception as e:  # noqa: BLE001
                self.stdout.write(f"  {sym:6} error: {e}")
                continue
            mapped = [m for m in (map_fmp_row(r) for r in rows) if m]
            total_rows += len(mapped)
            dates = sorted(m["transaction_date"] for m in mapped)
            span = f"{dates[0]}~{dates[-1]}" if dates else "—"
            self.stdout.write(f"  {sym:6} rows={len(mapped):3} span={span}")
        self.stdout.write(self.style.SUCCESS(f"DRY-RUN 표본 총 {total_rows}행 (무적재)"))
