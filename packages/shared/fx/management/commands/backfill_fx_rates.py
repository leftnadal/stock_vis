"""FX 환율 백필 관리 커맨드 (SLICE19B). 재실행 idempotent.

    python manage.py backfill_fx_rates            # USDKRW 전체 가용 범위
    python manage.py backfill_fx_rates --pair USDKRW
"""

from django.core.management.base import BaseCommand

from packages.shared.fx.services import DEFAULT_PAIR, backfill_rates


class Command(BaseCommand):
    help = "FMP 래퍼 경유로 통화쌍 과거 일간 환율을 ExchangeRate에 백필(idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--pair", default=DEFAULT_PAIR, help="통화쌍 (기본 USDKRW)")

    def handle(self, *args, **opts):
        result = backfill_rates(pair=opts["pair"])
        self.stdout.write(
            self.style.SUCCESS(
                f"FX backfill {result['pair']}: fetched={result['fetched']} "
                f"created={result['created']} updated={result['updated']}"
            )
        )
