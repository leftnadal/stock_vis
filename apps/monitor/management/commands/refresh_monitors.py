"""ingest → evaluate 체이닝 (MON-P2-INGEST, 수동 트리거).

판독 이식 후 곧바로 평가 파이프라인 실행 → 스냅샷·상태·display 갱신. 예:
    python manage.py refresh_monitors                 # 전체 stock 모니터
    python manage.py refresh_monitors --monitor <id>  # 특정 모니터
"""
from django.core.management.base import BaseCommand

from apps.monitor.models import Monitor
from apps.monitor.services.ingest import BACKFILL_DAYS, ingest_readings_for_monitor
from apps.monitor.services.pipeline import evaluate_monitor


class Command(BaseCommand):
    help = "ingest(EODSignal→Reading) 후 evaluate 체이닝 (수동)"

    def add_arguments(self, parser):
        parser.add_argument("--monitor", dest="monitor", default=None)
        parser.add_argument("--days", dest="days", type=int, default=BACKFILL_DAYS)

    def handle(self, *args, **options):
        qs = Monitor.objects.filter(scope=Monitor.Scope.STOCK)
        if options["monitor"]:
            qs = qs.filter(id=options["monitor"])

        for m in qs:
            ingest_readings_for_monitor(m, backfill_days=options["days"])
            res = evaluate_monitor(m)
            self.stdout.write(
                f"  {m.target_ref}: score={res['overall_score']} "
                f"state={res['state']} coverage={res['data_coverage']}"
            )
        self.stdout.write(self.style.SUCCESS(f"refresh 완료: {qs.count()}개 모니터"))
