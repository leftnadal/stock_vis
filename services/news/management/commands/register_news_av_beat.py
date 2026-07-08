"""
register_news_av_beat — AV broad 뉴스 수집 PeriodicTask를 DB에 멱등 등록 (Bug #28).

DatabaseScheduler 사용 시 config/celery.py의 beat_schedule dict는 런타임 무시되므로
(공통버그 #28), 실제 스케줄은 django_celery_beat.PeriodicTask(DB)로 등록한다.
register_chainsight_beats.py와 동일 패턴(CrontabSchedule + PeriodicTask.update_or_create).

등록 beat:
  - collect-av-broad-news @ 01:00 UTC 매일 (A안): collect_av_broad_news 로 broad
    NEWS_SENTIMENT 수집(topics 미지정=전체, LATEST). co-mention(2+종목) 소스.
    하류 체인(extract_co_mentions 10:00 ET · load_event_groups 22:15 UTC)은 기존 등록됨
    → collect(01:00 UTC) < extract(14:00 UTC) < load(22:15 UTC) 순서 보장.

시각은 timezone="UTC"로 명시 등록(ET crontab의 DST 드리프트 회피).

사용:
    python manage.py register_news_av_beat            # dry-run (등록 계획만)
    python manage.py register_news_av_beat --apply    # 실제 등록
    # --apply 후 celery beat 재시작 필요.
"""

from django.core.management.base import BaseCommand

BEATS = [
    {
        "name": "collect-av-broad-news",
        "task": "services.news.tasks.collect_av_broad_news",
        "minute": "0",
        "hour": "1",
        "timezone": "UTC",  # 01:00 UTC = 10:00 KST (A안)
        "day_of_week": "*",  # 매일
    },
]


class Command(BaseCommand):
    help = "AV broad 뉴스 수집 PeriodicTask(collect-av-broad-news)를 DB에 멱등 등록."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="실제 등록 수행. 기본은 dry-run (등록 계획만 출력).",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        # import는 handle 안에서(django_celery_beat 미설치 환경 대비)
        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        for beat in BEATS:
            tz = beat.get("timezone", "UTC")
            dow = beat.get("day_of_week", "*")
            dow_label = "daily" if dow == "*" else dow

            if not apply_changes:
                self.stdout.write(
                    f"[dry-run] would register {beat['name']} "
                    f"@ {beat['hour']}:{beat['minute'].zfill(2)} {tz} ({dow_label})"
                )
                continue

            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=beat["minute"],
                hour=beat["hour"],
                day_of_week=dow,
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
                    f"{verb}: {obj.name} @ {beat['hour']}:{beat['minute'].zfill(2)} {tz} ({dow_label})"
                )
            )

        if not apply_changes:
            self.stdout.write(self.style.WARNING("dry-run: 아무것도 등록하지 않음."))
