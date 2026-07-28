"""
FRED 3년치 매크로 시리즈 백필 (PR §6).

FRED가 제공하는 3년 전체를 1회 적재한다. FRED ICE BofA 시리즈는 2026-04부터
최근 3년만 제공하므로, 이 백필이 원장(MacroSeriesHistory)에 과거를 영구
확보하는 유일한 기회다.

★ 운영 규칙: 반드시 포그라운드 블로킹 실행 (harness reaping 표준 정책 —
   백그라운드 프로세스는 reaper가 살해함). nohup/& 백그라운드 실행 금지.

백필 완료 후 compute_all_signals()를 동기 호출해 초기 상태를 생성한다
(flag 무관 — 운영자가 명시 실행한 백필이므로).

사용:
    python manage.py backfill_macro_series --start 2023-07-01
    python manage.py backfill_macro_series --start 2023-07-01 --end 2026-07-07
"""
from django.core.management.base import BaseCommand

from ...constants import FRED_SERIES


class Command(BaseCommand):
    help = (
        "FRED 3년치 매크로 시리즈 백필 (포그라운드 블로킹 전용 — 백그라운드 실행 금지). "
        "완료 후 초기 CreditSignalState 생성."
    )

    def add_arguments(self, parser):
        parser.add_argument("--start", default="2023-07-01", help="시작일 YYYY-MM-DD")
        parser.add_argument("--end", default=None, help="종료일 YYYY-MM-DD (기본: FRED 최신)")

    def handle(self, *args, **options):
        start = options["start"]
        end = options["end"]

        from packages.shared.api_request.fred_client import FREDClient
        from ...services.ingest_service import ingest_series
        from ...services.signal_service import compute_all_signals

        self.stdout.write(
            self.style.WARNING(
                "⚠ 포그라운드 블로킹 실행 — 완료까지 이 프로세스를 종료하지 마세요."
            )
        )
        client = FREDClient()

        total = {"created": 0, "updated": 0, "skipped": 0}
        for series_id in FRED_SERIES:
            result = ingest_series(
                client,
                series_id,
                observation_start=start,
                observation_end=end,
                limit=100000,  # 3년 전체 (일별 ~756 관측치 + 여유)
            )
            for k in total:
                total[k] += result.get(k, 0)
            self.stdout.write(
                f"  {series_id}: created={result.get('created', 0)} "
                f"updated={result.get('updated', 0)} skipped={result.get('skipped', 0)}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"백필 완료: created={total['created']} updated={total['updated']} "
                f"skipped={total['skipped']} (시리즈 {len(FRED_SERIES)}종, {start}~{end or 'latest'})"
            )
        )

        # 초기 상태 생성 (flag 무관 — 운영자 명시 실행)
        results = compute_all_signals()
        self.stdout.write(self.style.SUCCESS(f"초기 CreditSignalState 생성: {results}"))
