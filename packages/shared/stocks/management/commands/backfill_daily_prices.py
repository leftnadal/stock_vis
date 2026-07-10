"""
DailyPrice 3년 백필 관리 명령 (TH-9, 결정14=A) — stocks 도메인 소유 쓰기.

C6/C7(Theme Heat) 활성용 테마 유니버스 종목 3년 가격 이력을 공유 정본 DailyPrice 에 백필.
겹침 대조 게이트(조정 규약 불일치 종목 정지·상신) + 멱등 upsert + foreground blocking.

사용:
    python manage.py backfill_daily_prices --symbols-from-universe --years 3
    python manage.py backfill_daily_prices --symbols AAPL MSFT --years 3
    python manage.py backfill_daily_prices --symbols-from-universe --dry-run   # 겹침 대조만
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "테마 유니버스 종목 DailyPrice 3년 백필 (겹침 대조 게이트, 결정14=A)."

    def add_arguments(self, parser):
        parser.add_argument("--symbols-from-universe", action="store_true",
                            help="대상 = SP500Constituent(is_active) − '.' 심볼(FMP 402 회피).")
        parser.add_argument("--symbols", nargs="*", default=None, help="명시 종목 목록.")
        parser.add_argument("--years", type=int, default=3)
        parser.add_argument("--error-threshold", type=float, default=0.005,
                            help="겹침 close 상대오차 정지 임계(기본 0.5%).")
        parser.add_argument("--dry-run", action="store_true", help="쓰기 없이 겹침 대조만.")
        parser.add_argument("--force", action="store_true",
                            help="겹침 게이트 우회 교체(TH-11 결정18, 기업행동 정렬 통과분 전용).")

    def handle(self, *args, **opts):
        from django.conf import settings

        from packages.shared.api_request.providers.fmp.client import FMPClient
        from packages.shared.stocks.models import SP500Constituent
        from packages.shared.stocks.services.daily_price_backfill import backfill_daily_prices

        if opts["symbols"]:
            symbols = [s.upper() for s in opts["symbols"]]
        elif opts["symbols_from_universe"]:
            symbols = sorted(
                s for s in SP500Constituent.objects.filter(is_active=True)
                .values_list("symbol", flat=True)
                if "." not in s
            )
        else:
            raise CommandError("--symbols-from-universe 또는 --symbols 필요.")

        to_date = timezone.now().date()
        from_date = to_date - timedelta(days=365 * opts["years"])
        self.stdout.write(
            f"백필 대상 {len(symbols)}종 × {opts['years']}년 "
            f"({from_date}~{to_date}) dry_run={opts['dry_run']}"
        )

        client = FMPClient(api_key=settings.FMP_API_KEY)
        r = backfill_daily_prices(
            client, symbols, from_date, to_date,
            error_threshold=opts["error_threshold"], dry_run=opts["dry_run"],
            force=opts["force"],
        )

        self.stdout.write(self.style.SUCCESS(
            f"written={r['written']} symbols_written={len(r['symbols_written'])} "
            f"halted={len(r['halted'])} errors={len(r['errors'])}"
        ))
        self.stdout.write(
            f"겹침 오차: max={r['overlap_max_err']} median={r['overlap_median_err']}"
        )
        if r["halted"]:
            self.stdout.write(self.style.WARNING(f"정지 종목(오차>{opts['error_threshold']}): {r['halted']}"))
        if r["errors"]:
            self.stdout.write(f"errors: {dict(list(r['errors'].items())[:20])}")
