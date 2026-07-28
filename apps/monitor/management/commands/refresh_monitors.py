"""ingest → evaluate 체이닝 수동 트리거 (MON-P2-INGEST/BEAT).

체이닝 로직 본체는 서비스 함수 `pipeline.refresh_monitors`에 있고, 본 커맨드와
Celery beat 태스크(`apps.monitor.tasks.refresh_monitors_task`)가 이를 각각 얇게
호출한다(MON-P2-BEAT §3). 커맨드는 수동/온디맨드 트리거 전용. 예:
    python manage.py refresh_monitors                 # 전체 stock 모니터
    python manage.py refresh_monitors --monitor <id>  # 특정 모니터
"""
from django.core.management.base import BaseCommand

from apps.monitor.models import Monitor
from apps.monitor.services.ingest import BACKFILL_DAYS
from apps.monitor.services.pipeline import refresh_monitors


class Command(BaseCommand):
    help = "ingest(EODSignal→Reading) 후 evaluate 체이닝 (수동, 서비스 함수 호출)"

    def add_arguments(self, parser):
        parser.add_argument("--monitor", dest="monitor", default=None)
        parser.add_argument("--days", dest="days", type=int, default=BACKFILL_DAYS)

    def handle(self, *args, **options):
        qs = Monitor.objects.filter(scope=Monitor.Scope.STOCK)
        if options["monitor"]:
            qs = qs.filter(id=options["monitor"])

        results = refresh_monitors(queryset=qs, backfill_days=options["days"])
        for res in results:
            self.stdout.write(
                f"  {res['monitor_id'][:8]}: score={res['overall_score']} "
                f"state={res['state']} ingested={res['ingested']} "
                f"coverage={res['data_coverage']}"
            )
        self.stdout.write(self.style.SUCCESS(f"refresh 완료: {len(results)}개 모니터"))
