"""
register_newsfix_sync_beat — NewsEntity→StockNews 물질화 sync PeriodicTask 등록 (NEWSFIX-SYNC-BE).

DatabaseScheduler 사용 시 config/celery.py의 beat_schedule dict는 런타임 무시되므로
(공통버그 #28), 실제 스케줄은 django_celery_beat.PeriodicTask(DB)로 등록한다.
register_news_av_beat.py 와 동일 패턴(CrontabSchedule + PeriodicTask.update_or_create).

등록 beat:
  - newsfix-sync-stocknews @ 17:30 ET Mon-Fri (America/New_York) — sync_news_entities_to_stock_news.
    근거: EOD bake(run-eod-pipeline)가 18:30 ET Mon-Fri(config/celery.py:642)에 enricher를 돌린다.
    sync를 그 1시간 전에 완료해 당일 실뉴스가 StockNews에 실려 있게 한다. ET(America/New_York)
    전용 crontab으로 bake와 함께 DST를 따라 이동(1시간 간격 유지).

⚠ **enabled=False 로 등록**(Gate 4): 코드/등록만 준비, 라이브 활성화는 배포 카드에서 사용자 수동
  (`PeriodicTask enabled=True` 전환 + celery beat 재시작). backfill 선행 권장.

사용:
    python manage.py register_newsfix_sync_beat            # dry-run (등록 계획만)
    python manage.py register_newsfix_sync_beat --apply    # enabled=False 로 등록
    # 활성화(별도·배포 카드): PeriodicTask(name='newsfix-sync-stocknews').enabled=True + beat 재시작
"""

from django.core.management.base import BaseCommand

BEATS = [
    {
        "name": "newsfix-sync-stocknews",
        "task": "services.news.tasks.sync_news_entities_to_stock_news",
        "minute": "30",
        "hour": "17",
        "timezone": "America/New_York",  # 17:30 ET = bake(18:30 ET) 1시간 전, DST 동반
        "day_of_week": "1-5",  # 평일(bake 스케줄과 정합)
    },
]


class Command(BaseCommand):
    help = (
        "NewsEntity→StockNews sync PeriodicTask(newsfix-sync-stocknews)를 "
        "DB에 enabled=False 로 멱등 등록(Gate 4). 기본 dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="실제 등록 수행(enabled=False). 기본은 dry-run(등록 계획만).",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]

        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        for beat in BEATS:
            tz = beat.get("timezone", "UTC")
            dow = beat.get("day_of_week", "*")

            if not apply_changes:
                self.stdout.write(
                    f"[dry-run] would register {beat['name']} "
                    f"@ {beat['hour']}:{beat['minute'].zfill(2)} {tz} (dow={dow}) "
                    f"enabled=False"
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
                    "enabled": False,  # Gate 4 — 활성화는 배포 카드에서 수동
                },
            )
            verb = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{verb}: {obj.name} @ {beat['hour']}:{beat['minute'].zfill(2)} {tz} "
                    f"(dow={dow}) enabled={obj.enabled}"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "  ⚠ enabled=False — 라이브 활성화(enabled=True + beat 재시작)는 "
                    "배포 카드에서 사용자 수동. backfill 선행 권장."
                )
            )

        if not apply_changes:
            self.stdout.write(self.style.WARNING("dry-run: 아무것도 등록하지 않음."))
