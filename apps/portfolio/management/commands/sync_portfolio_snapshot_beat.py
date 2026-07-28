"""포트폴리오 자산 스냅샷 beat DB 등록 — 멱등 동기화 커맨드 (SLICE19C, 공통버그 #28).

DatabaseScheduler 환경에서 DB PeriodicTask가 유일한 진실(config dict 스케줄 금지).
스냅샷 태스크(`apps.portfolio.tasks.snapshot_all_users`)의 CrontabSchedule + PeriodicTask를
get_or_create/upsert. 몇 번 실행해도 동일 최종 상태(멱등).

스케줄: 19:00 America/New_York — monitor refresh(18:45 ET) 이후, EOD 가격 정착 후.
timezone은 CrontabSchedule.timezone 필드로 지정(DST 자동, UTC 고정 금지).

사용: `python manage.py sync_portfolio_snapshot_beat` (멱등) / `--dry-run` 예정만 출력.
※ prod 등록은 랜딩 후 운영 단계(이 슬라이스는 커맨드 정의까지 — dev/prod 실행은 별도).
"""

from django.core.management.base import BaseCommand

SNAPSHOT_BEAT_NAME = "portfolio-snapshot-daily"
SNAPSHOT_BEAT_TASK = "apps.portfolio.tasks.snapshot_all_users"
SNAPSHOT_CRONTAB = {
    "minute": "0",
    "hour": "19",
    "day_of_week": "1-5",
    "day_of_month": "*",
    "month_of_year": "*",
    "timezone": "America/New_York",
}
SNAPSHOT_BEAT_DESCRIPTION = (
    "포트폴리오 자산 스냅샷(dd·flow 토대) — 목표 보유 사용자 전원 upsert. "
    "19:00 ET (monitor refresh 이후, EOD 정착 후)."
)


class Command(BaseCommand):
    help = "포트폴리오 스냅샷 nightly beat DB 등록 (멱등, #28)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        if dry:
            self.stdout.write(
                f"[dry-run] {SNAPSHOT_BEAT_NAME} → {SNAPSHOT_BEAT_TASK} "
                f"@ {SNAPSHOT_CRONTAB['hour']}:{SNAPSHOT_CRONTAB['minute']} "
                f"{SNAPSHOT_CRONTAB['timezone']} (dow={SNAPSHOT_CRONTAB['day_of_week']})"
            )
            return

        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        schedule, _ = CrontabSchedule.objects.get_or_create(**SNAPSHOT_CRONTAB)
        task, created = PeriodicTask.objects.update_or_create(
            name=SNAPSHOT_BEAT_NAME,
            defaults={
                "task": SNAPSHOT_BEAT_TASK,
                "crontab": schedule,
                "description": SNAPSHOT_BEAT_DESCRIPTION,
                "enabled": True,
            },
        )
        verb = "생성" if created else "갱신"
        self.stdout.write(
            self.style.SUCCESS(f"✅ {verb}: {SNAPSHOT_BEAT_NAME} → {SNAPSHOT_BEAT_TASK}")
        )
