"""
Chain Sight 일배치 beat 등록 관리 명령 (CS-M2 Slice 3).

DatabaseScheduler 사용 시 config dict는 무시되므로(bug #28) PeriodicTask를
DB에 직접 등록한다. 멱등(update_or_create).

등록 대상:
  - chainsight-attention-daily   (M1 — STEP0가 미등록 지적, 함께 등록)
  - chainsight-leadership-daily  (M2 — 신규)

★ prod 적용은 사용자 수동 실행 지점. 이 파일은 메커니즘만 제공한다.

사용:
    python manage.py register_chainsight_beats          # 등록/갱신
    python manage.py register_chainsight_beats --dry-run  # 미적용, 계획만 출력
"""

from django.core.management.base import BaseCommand

# 평일(월~금) UTC 기준 스케줄. attention 먼저, leadership을 약간 뒤로(데이터 의존).
# 22:30 UTC ≈ 07:30 KST 익일. leadership은 attention 직후 22:40.
BEATS = [
    {
        "name": "chainsight-attention-daily",
        "task": "chainsight-attention-daily",
        "minute": "30",
        "hour": "22",
    },
    {
        "name": "chainsight-leadership-daily",
        "task": "chainsight-leadership-daily",
        "minute": "40",
        "hour": "22",
    },
]


class Command(BaseCommand):
    help = "Chain Sight 일배치(attention/leadership) PeriodicTask를 DB에 멱등 등록."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="실제 등록 없이 등록 계획만 출력.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # import는 handle 안에서(django_celery_beat 미설치 환경 대비)
        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        for beat in BEATS:
            if dry_run:
                self.stdout.write(
                    f"[dry-run] would register {beat['name']} "
                    f"@ {beat['hour']}:{beat['minute']} UTC (Mon-Fri)"
                )
                continue

            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=beat["minute"],
                hour=beat["hour"],
                day_of_week="1-5",
                day_of_month="*",
                month_of_year="*",
                timezone="UTC",
            )
            obj, created = PeriodicTask.objects.update_or_create(
                name=beat["name"],
                defaults={
                    "task": beat["task"],
                    "crontab": schedule,
                    "enabled": True,
                },
            )
            verb = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{verb}: {obj.name} @ {beat['hour']}:{beat['minute']} UTC (Mon-Fri)"
                )
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run: 아무것도 등록하지 않음."))
