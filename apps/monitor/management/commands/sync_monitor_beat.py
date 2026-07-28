"""Monitor 평가 beat DB 등록 — 멱등 동기화 커맨드 (MON-P2-BEAT §5, 공통버그 #28).

DatabaseScheduler 환경에서 DB PeriodicTask가 유일한 진실(config dict 스케줄 금지).
실행 시:
  ① 폐기된 thesis eod_pipeline beat 4레코드가 남아 있으면 삭제(앱 폐기 잔재 회수, §2).
  ② monitor refresh 태스크의 CrontabSchedule + PeriodicTask를 get_or_create/upsert.
몇 번을 실행해도 동일 최종 상태(멱등) — 배포/환경 재현마다 재실행한다.

스케줄: 18:45 America/New_York — EOD 창 18:00~18:35 ET 종료 후 10분 버퍼.
timezone은 CrontabSchedule.timezone 필드로 지정 → DST 자동 처리(UTC 고정 시각 금지).
기존 배치 지배 관례(CrontabSchedule 대다수가 America/New_York, CELERY_TIMEZONE 동일)와
일치하며, 폐기된 thesis 선행 4레코드도 동일 tz(m=0/15/30/35 h=18)였다.

사용: `python manage.py sync_monitor_beat` (멱등) / `--dry-run`으로 예정만 출력.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

# 폐기된 thesis 앱 eod_pipeline/summary beat — 회수 대상(§2, 결정 1=A). §0에서 캡처:
#   thesis-update-readings   / thesis.tasks.eod_pipeline.update_indicator_readings   / m=0  h=18 dow=1-5 tz=America/New_York
#   thesis-calculate-scores  / thesis.tasks.eod_pipeline.calculate_scores            / m=15 h=18 dow=1-5 tz=America/New_York
#   thesis-create-snapshots  / thesis.tasks.eod_pipeline.create_snapshots_and_alerts / m=30 h=18 dow=1-5 tz=America/New_York
#   thesis-generate-summaries/ thesis.tasks.summary.generate_thesis_summaries        / m=35 h=18 dow=1-5 tz=America/New_York
LEGACY_THESIS_TASK_NAMES = [
    "thesis-update-readings",
    "thesis-calculate-scores",
    "thesis-create-snapshots",
    "thesis-generate-summaries",
]

MONITOR_BEAT_NAME = "monitor-refresh-daily"
MONITOR_BEAT_TASK = "apps.monitor.tasks.refresh_monitors_task"
MONITOR_CRONTAB = {
    "minute": "45",
    "hour": "18",
    "day_of_week": "1-5",
    "day_of_month": "*",
    "month_of_year": "*",
    "timezone": "America/New_York",
}
MONITOR_BEAT_DESCRIPTION = (
    "Monitor 허브 — EOD 후 refresh(ingest→evaluate). 18:45 ET (EOD 창 종료 +10분 버퍼)."
)


class Command(BaseCommand):
    help = "Monitor refresh beat DB 등록 + 구 thesis beat 회수 (멱등, #28)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]

        # ① 폐기된 thesis beat 잔재 삭제 (멱등: 없으면 no-op)
        legacy_qs = PeriodicTask.objects.filter(name__in=LEGACY_THESIS_TASK_NAMES)
        n_legacy = legacy_qs.count()
        if dry:
            for t in legacy_qs:
                self.stdout.write(f"[dry-run] would delete legacy thesis beat: {t.name}")
            self.stdout.write(f"[dry-run] would upsert {MONITOR_BEAT_NAME} @ 18:45 America/New_York")
            self.stdout.write(f"[dry-run] 삭제 예정 thesis={n_legacy}, monitor beat 1건 등록")
            return
        legacy_qs.delete()

        # ② monitor refresh beat upsert (멱등)
        crontab, _ = CrontabSchedule.objects.get_or_create(**MONITOR_CRONTAB)
        obj, created = PeriodicTask.objects.update_or_create(
            name=MONITOR_BEAT_NAME,
            defaults={
                "task": MONITOR_BEAT_TASK,
                "crontab": crontab,
                "interval": None,
                "enabled": True,
                "description": MONITOR_BEAT_DESCRIPTION,
            },
        )
        verb = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"thesis 회수 {n_legacy}건 · monitor beat [{verb}] {obj.name} "
                f"@ {crontab.hour}:{crontab.minute} {crontab.timezone} (dow={crontab.day_of_week})"
            )
        )
