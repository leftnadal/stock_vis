"""
Chain Sight 일배치 beat 등록 관리 명령 (CS-M2 Slice 3).

DatabaseScheduler 사용 시 config dict는 무시되므로(bug #28) PeriodicTask를
DB에 직접 등록한다. 멱등(update_or_create).

등록 대상:
  - chainsight-event-group-leadership-daily  (보드 ON 신선도 — 그룹 재적재 + C leadership)
  - chainsight-attention-daily   (M1 — STEP0가 미등록 지적, 함께 등록)
  - chainsight-leadership-daily  (M2 — 신규)

순서(신선도): EventGroup 그룹·eg: 점수(22:15)를 attention(22:30)·leadership(22:40)보다
앞서 갱신 → 보드 ON이 읽기 전 그룹/점수가 최신.

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
        # 보드 ON 신선도: 그룹 재적재 + C leadership. attention(22:30)보다 앞선 22:15.
        "name": "chainsight-event-group-leadership-daily",
        "task": "chainsight-event-group-leadership-daily",
        "minute": "15",
        "hour": "22",
    },
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
