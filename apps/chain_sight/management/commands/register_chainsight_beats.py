"""
Chain Sight 일배치 beat 등록 관리 명령 (CS-M2 Slice 3).

DatabaseScheduler 사용 시 config dict는 무시되므로(bug #28) PeriodicTask를
DB에 직접 등록한다. 멱등(update_or_create).

등록 대상:
  - chainsight-event-group-leadership-daily  (보드 ON 신선도 — 그룹 재적재 + C leadership)
  - chainsight-attention-daily   (M1 — STEP0가 미등록 지적, 함께 등록)
  - chainsight-leadership-daily  (M2 — 신규)
  - chainsight-pair-aggregation  (버그 #28 — RelationPairSnapshot 집계, ET 11:30 매일)

순서(신선도): EventGroup 그룹·eg: 점수(22:15)를 attention(22:30)·leadership(22:40)보다
앞서 갱신 → 보드 ON이 읽기 전 그룹/점수가 최신.

★ prod 적용은 사용자 수동 실행 지점. 이 파일은 메커니즘만 제공한다.

사용:
    python manage.py register_chainsight_beats          # 등록/갱신
    python manage.py register_chainsight_beats --dry-run  # 미적용, 계획만 출력
"""

from django.core.management.base import BaseCommand

# BEATS 엔트리 스키마:
#   name/task/minute/hour (필수)
#   timezone   (optional, 기본 "UTC")   — 없으면 UTC로 crontab 평가
#   day_of_week(optional, 기본 "1-5")   — 없으면 평일. None → 매일("*")
# 기존 엔트리는 timezone/day_of_week 키가 없어 기본값(UTC·평일)으로 동작 불변(하위호환).
#
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
    {
        # 관계 쌍 relevance 집계 → RelationPairSnapshot (해자 궤적 적립, 버그 #28).
        # update_relation_confidence(America/New_York 11:00, 매일) 직후 11:30 실행 —
        # 신뢰 갱신 → 집계 순. confidence와 동일 America/New_York(ET)이라 DST 자동 처리로
        # 순서가 3·11월 경계에서도 깨지지 않는다(UTC 고정 금지). full-path task.
        "name": "chainsight-pair-aggregation",
        "task": "apps.chain_sight.tasks.relation_tasks.aggregate_relation_pairs_task",
        "minute": "30",
        "hour": "11",
        "timezone": "America/New_York",
        "day_of_week": None,  # 매일 (confidence가 매일이므로)
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
            tz = beat.get("timezone", "UTC")
            dow_raw = beat.get("day_of_week", "1-5")
            cron_dow = "*" if dow_raw is None else dow_raw
            dow_label = "daily" if cron_dow == "*" else cron_dow

            if dry_run:
                self.stdout.write(
                    f"[dry-run] would register {beat['name']} "
                    f"@ {beat['hour']}:{beat['minute']} {tz} ({dow_label})"
                )
                continue

            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=beat["minute"],
                hour=beat["hour"],
                day_of_week=cron_dow,
                day_of_month="*",
                month_of_year="*",
                timezone=tz,
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
                    f"{verb}: {obj.name} @ {beat['hour']}:{beat['minute']} {tz} ({dow_label})"
                )
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run: 아무것도 등록하지 않음."))
