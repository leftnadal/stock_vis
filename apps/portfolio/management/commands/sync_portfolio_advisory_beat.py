"""권유 자동 기록 beat DB 등록 — 멱등 동기화 커맨드 (SLICE20A, 공통버그 #28).

DatabaseScheduler 환경에서 DB PeriodicTask가 유일한 진실(config dict 스케줄 금지).
advisory 태스크(`apps.portfolio.tasks.advisory_all_users`)의 CrontabSchedule + PeriodicTask를
get_or_create/upsert. 몇 번 실행해도 동일 최종 상태(멱등).

스케줄: 19:15 America/New_York — snapshot beat(19:00 ET) 이후, 스냅샷 정착 후 권유 기록.
timezone은 CrontabSchedule.timezone 필드로 지정(DST 자동, UTC 고정 금지).

사용: `python manage.py sync_portfolio_advisory_beat` (멱등) / `--dry-run` 예정만 출력.
※ prod 등록은 랜딩 후 운영 단계(이 슬라이스는 커맨드 정의까지 — 19c snapshot beat와 동일 유보).
"""

from django.core.management.base import BaseCommand

ADVISORY_BEAT_NAME = "portfolio-advisory-daily"
ADVISORY_BEAT_TASK = "apps.portfolio.tasks.advisory_all_users"
ADVISORY_CRONTAB = {
    "minute": "15",
    "hour": "19",
    "day_of_week": "1-5",
    "day_of_month": "*",
    "month_of_year": "*",
    "timezone": "America/New_York",
}
ADVISORY_BEAT_DESCRIPTION = (
    "권유 자동 기록(trigger=auto·사후분석 표본) — 목표 보유 사용자 전원 run_advisory. "
    "19:15 ET (snapshot beat 19:00 ET 이후)."
)


class Command(BaseCommand):
    help = "포트폴리오 권유 nightly beat DB 등록 (멱등, #28)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.stdout.write(
                f"[dry-run] {ADVISORY_BEAT_NAME} → {ADVISORY_BEAT_TASK} "
                f"@ {ADVISORY_CRONTAB['hour']}:{ADVISORY_CRONTAB['minute']} "
                f"{ADVISORY_CRONTAB['timezone']} (dow={ADVISORY_CRONTAB['day_of_week']})"
            )
            return

        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        schedule, _ = CrontabSchedule.objects.get_or_create(**ADVISORY_CRONTAB)
        _, created = PeriodicTask.objects.update_or_create(
            name=ADVISORY_BEAT_NAME,
            defaults={
                "task": ADVISORY_BEAT_TASK,
                "crontab": schedule,
                "description": ADVISORY_BEAT_DESCRIPTION,
                "enabled": True,
            },
        )
        verb = "생성" if created else "갱신"
        self.stdout.write(
            self.style.SUCCESS(f"✅ {verb}: {ADVISORY_BEAT_NAME} → {ADVISORY_BEAT_TASK}")
        )
