"""EODSignal → IndicatorReading 이식 (MON-P2-INGEST, 수동 트리거).

beat 등록은 별도(MON-P2-BEAT). 예:
    python manage.py ingest_readings                    # 전체 stock 모니터
    python manage.py ingest_readings --monitor <id>     # 특정 모니터
    python manage.py ingest_readings --days 60          # 백필 길이 override
"""
from django.core.management.base import BaseCommand

from apps.monitor.models import Monitor
from apps.monitor.services.ingest import BACKFILL_DAYS, ingest_readings_for_monitor


class Command(BaseCommand):
    help = "EODSignal → IndicatorReading 이식 (stock scope, 멱등)"

    def add_arguments(self, parser):
        parser.add_argument("--monitor", dest="monitor", default=None)
        parser.add_argument("--days", dest="days", type=int, default=BACKFILL_DAYS)

    def handle(self, *args, **options):
        qs = Monitor.objects.filter(scope=Monitor.Scope.STOCK)
        if options["monitor"]:
            qs = qs.filter(id=options["monitor"])

        total = 0
        for m in qs:
            results = ingest_readings_for_monitor(m, backfill_days=options["days"])
            for r in results:
                total += r["ingested"]
                self.stdout.write(
                    f"  {r['symbol']} [{r['source_key']}]: {r['status']} "
                    f"ingested={r['ingested']} null_skip={r['skipped_null']}"
                )
        self.stdout.write(
            self.style.SUCCESS(f"이식 완료: {qs.count()}개 모니터, 총 {total} readings")
        )
