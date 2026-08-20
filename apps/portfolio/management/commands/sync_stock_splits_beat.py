"""StockSplit ingest beat DB 등록 — 멱등 동기화 커맨드 (I3-SPLIT-GUARD, 공통버그 #28).

DatabaseScheduler 환경에서 DB PeriodicTask가 유일한 진실(config dict 스케줄 금지).
`apps.portfolio.tasks.ingest_stock_splits`의 CrontabSchedule + PeriodicTask upsert.

스케줄: **19:45 America/New_York** (dow 1-5) — analyst 신호(19:30) 이후 nightly 체인
최후미. 채점은 수동 커맨드라 수집 시점 민감도 없음(19:30 analyst → 19:45 splits → 20:00
financials, 충돌 0 실측). timezone은 CrontabSchedule.timezone 필드(DST 자동, UTC 고정 금지).

★ 실행 = 병진 수동(DB PeriodicTask = prod-write). Claude Code는 커맨드 정의까지.
사용: `python manage.py sync_stock_splits_beat` (멱등) / `--dry-run` 예정만 출력.
"""

from django.core.management.base import BaseCommand

BEAT_NAME = "portfolio-stock-splits-daily"
BEAT_TASK = "apps.portfolio.tasks.ingest_stock_splits"
CRONTAB = {
    "minute": "45",
    "hour": "19",  # analyst 19:30 이후, 체인 최후미(20:00 financials 前)
    "day_of_week": "1-5",
    "day_of_month": "*",
    "month_of_year": "*",
    "timezone": "America/New_York",
}
BEAT_DESCRIPTION = (
    "coach 유니버스(보유∪관심) 액면분할 이력 nightly 수집 → StockSplit append/skip. "
    "19:45 ET (analyst 19:30 후). 채점(analyst_scoring)의 예측~만기 구간 분할 감지 "
    "→ unscoreable:corporate_action 원료 (I3-SPLIT-GUARD, D-SPLIT-1)."
)


class Command(BaseCommand):
    help = "StockSplit ingest nightly beat DB 등록 (멱등, #28)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.stdout.write(
                f"[dry-run] {BEAT_NAME} → {BEAT_TASK} "
                f"@ {CRONTAB['hour']}:{CRONTAB['minute']} {CRONTAB['timezone']} "
                f"(dow={CRONTAB['day_of_week']})"
            )
            return

        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        schedule, _ = CrontabSchedule.objects.get_or_create(**CRONTAB)
        task, created = PeriodicTask.objects.update_or_create(
            name=BEAT_NAME,
            defaults={
                "task": BEAT_TASK,
                "crontab": schedule,
                "description": BEAT_DESCRIPTION,
                "enabled": True,
            },
        )
        verb = "생성" if created else "갱신"
        self.stdout.write(self.style.SUCCESS(f"✅ {verb}: {BEAT_NAME} → {BEAT_TASK}"))
