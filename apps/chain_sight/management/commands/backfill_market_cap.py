"""ego 서빙 심볼 market cap 백필 (⑳-3 S3-MINDMAP S1 — L2-X 선행).

FMP /stable/quote로 ego 서빙 심볼(비-rejected RelationConfidence 등장 심볼) market cap을
수집해 Stock.market_capitalization에 기록한다. L2-X mcap 3분위 층화의 데이터 선행.

    python manage.py backfill_market_cap --dry-run       # 5심볼 프로브(필드 확인)
    python manage.py backfill_market_cap --apply          # 전수 백필(idempotent)
    python manage.py backfill_market_cap --apply --limit 50

rate limit: FMP Starter 300/분 → 0.25s 간격. idempotent(update). 결측 심볼 목록 보고.
"""

import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.chain_sight.models import RelationConfidence
from packages.shared.api_request.providers.fmp.client import FMPClient
from packages.shared.stocks.models import Stock

SLEEP_S = 0.25  # FMP 300/분 안전


def serving_symbols():
    served = RelationConfidence.objects.exclude(domain_review_status="rejected")
    return sorted(
        set(served.values_list("symbol_a", flat=True))
        | set(served.values_list("symbol_b", flat=True))
    )


def _market_cap(quote):
    """FMP quote dict에서 market cap 추출(필드명 방어)."""
    for k in ("marketCap", "market_cap", "marketCapitalization"):
        v = quote.get(k)
        if v:
            return v
    return None


class Command(BaseCommand):
    help = "ego 서빙 심볼 market cap 백필(FMP /stable/quote → Stock.market_capitalization)"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="전수 백필(미지정=5심볼 프로브)")
        parser.add_argument("--limit", type=int, default=0, help="상한(0=무제한)")
        parser.add_argument("--only-missing", action="store_true",
                            help="market_capitalization 결측 심볼만(재개용)")

    def handle(self, *args, **opts):
        client = FMPClient(api_key=settings.FMP_API_KEY)
        syms = serving_symbols()
        # Stock 레코드 존재 심볼만 대상(없으면 기록 불가)
        stock_syms = set(
            Stock.objects.filter(symbol__in=syms).values_list("symbol", flat=True)
        )
        targets = [s for s in syms if s in stock_syms]
        self.stdout.write(
            f"ego 서빙 심볼 {len(syms)} · Stock 존재 {len(targets)} · dry_run={not opts['apply']}"
        )

        if not opts["apply"]:
            probe = targets[:5]
            self.stdout.write(f"프로브 {len(probe)}심볼:")
            for s in probe:
                q = client.get_quote(s)
                self.stdout.write(f"    {s}: marketCap={_market_cap(q)}")
                time.sleep(SLEEP_S)
            self.stdout.write("dry-run: DB 무기록. (--apply 로 전수)")
            return

        if opts["only_missing"]:
            have = set(
                Stock.objects.filter(symbol__in=stock_syms)
                .exclude(market_capitalization__isnull=True)
                .exclude(market_capitalization=0)
                .values_list("symbol", flat=True)
            )
            targets = [s for s in targets if s not in have]
            self.stdout.write(f"  --only-missing: 결측 {len(targets)}심볼만 처리")
        if opts["limit"]:
            targets = targets[: opts["limit"]]

        updated, missing, errors = 0, [], []
        for i, s in enumerate(targets, 1):
            try:
                mc = _market_cap(client.get_quote(s))
                if mc:
                    Stock.objects.filter(symbol=s).update(market_capitalization=mc)
                    updated += 1
                else:
                    missing.append(s)
            except Exception as e:  # noqa: BLE001
                errors.append((s, f"{type(e).__name__}"))
            if i % 100 == 0:
                self.stdout.write(f"  진행 {i}/{len(targets)} (updated={updated})")
            time.sleep(SLEEP_S)

        # 커버리지 재측정
        filled = (
            Stock.objects.filter(symbol__in=stock_syms)
            .exclude(market_capitalization__isnull=True)
            .exclude(market_capitalization=0)
            .count()
        )
        self.stdout.write(
            f"✅ 백필 완료: updated={updated} · marketCap 결측={len(missing)} · 오류={len(errors)}"
        )
        self.stdout.write(f"   커버리지: {filled}/{len(syms)} = {100 * filled / len(syms):.1f}%")
        if missing:
            self.stdout.write(f"   결측 심볼: {missing[:30]}{'...' if len(missing) > 30 else ''}")
        if errors:
            self.stdout.write(f"   오류 심볼: {errors[:10]}")
