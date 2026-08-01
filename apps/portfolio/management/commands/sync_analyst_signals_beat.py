"""AnalystSignal ingest beat DB 등록 — 멱등 동기화 커맨드 (SFI-I1, 공통버그 #28).

DatabaseScheduler 환경에서 DB PeriodicTask가 유일한 진실(config dict 스케줄 금지).
`apps.portfolio.tasks.ingest_analyst_signals`의 CrontabSchedule + PeriodicTask upsert.

스케줄: 18:30 America/New_York — snapshot beat(19:00 ET) **앞**(forward 신호가 스냅샷·권유
앞에 준비되도록). timezone은 CrontabSchedule.timezone 필드(DST 자동, UTC 고정 금지).

★ 실행 = 병진 수동(DB PeriodicTask = prod-write). Claude Code는 커맨드 정의까지.
사용: `python manage.py sync_analyst_signals_beat` (멱등) / `--dry-run` 예정만 출력.
"""

from django.core.management.base import BaseCommand

BEAT_NAME = "portfolio-analyst-signals-daily"
BEAT_TASK = "apps.portfolio.tasks.ingest_analyst_signals"
CRONTAB = {
    "minute": "30",
    "hour": "18",
    "day_of_week": "1-5",
    "day_of_month": "*",
    "month_of_year": "*",
    "timezone": "America/New_York",
}
BEAT_DESCRIPTION = (
    "coach 유니버스(보유∪관심) forward 신호(price target·grades·ratings) nightly 수집 "
    "→ AnalystSignalSnapshot append + Stock.analyst_* 미러. 18:30 ET (snapshot 19:00 앞). "
    "estimates 무접촉(chain_sight 정본, D-I1-4)."
)


class Command(BaseCommand):
    help = "AnalystSignal ingest nightly beat DB 등록 (멱등, #28)"

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
