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

# MON-P4-LA — ADVISOR L-A 정기 브리핑 beat. 18:50 ET(monitor-refresh 18:45 스냅샷 생성 +5분).
# **enabled=False로 최초 생성 후 get_or_create로 점등 상태 보존**(update_or_create가 아님 —
# 배포 승인 후 수동 enable을 멱등 재실행이 되돌리지 않게). ADVISOR_ENABLED와 이중잠금.
ADVISOR_BEAT_NAME = "advisor-daily-briefing"
ADVISOR_BEAT_TASK = "apps.monitor.tasks.advisor_briefing_task"
ADVISOR_CRONTAB = {
    "minute": "50",
    "hour": "18",
    "day_of_week": "1-5",
    "day_of_month": "*",
    "month_of_year": "*",
    "timezone": "America/New_York",
}
ADVISOR_BEAT_DESCRIPTION = (
    "ADVISOR L-A 정기 브리핑 — EOD 후행 18:50 ET. 기본 OFF(enabled=False + "
    "ADVISOR_ENABLED 이중잠금). 점등은 배포 승인 후 수동(MON-P4-LA §8)."
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
            self.stdout.write(
                f"[dry-run] would get_or_create {ADVISOR_BEAT_NAME} @ 18:50 America/New_York "
                f"enabled=False (점등 보존)"
            )
            self.stdout.write(f"[dry-run] 삭제 예정 thesis={n_legacy}, monitor+advisor beat 2건 등록")
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

        # ③ advisor 브리핑 beat — get_or_create(최초만 enabled=False, 이후 수동 점등 보존)
        adv_crontab, _ = CrontabSchedule.objects.get_or_create(**ADVISOR_CRONTAB)
        adv_obj, adv_created = PeriodicTask.objects.get_or_create(
            name=ADVISOR_BEAT_NAME,
            defaults={
                "task": ADVISOR_BEAT_TASK,
                "crontab": adv_crontab,
                "interval": None,
                "enabled": False,
                "description": ADVISOR_BEAT_DESCRIPTION,
            },
        )
        adv_state = (
            "created(enabled=False)" if adv_created
            else f"exists(enabled={adv_obj.enabled} 보존)"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"advisor beat [{adv_state}] {adv_obj.name} "
                f"@ {adv_crontab.hour}:{adv_crontab.minute} {adv_crontab.timezone}"
            )
        )
