"""Monitor 평가 파이프라인 수동 실행 (MON-P2-S3).

beat 주기 등록은 별도 스텝(EOD 창 18:00~18:35 ET 경합 설계 + DB PeriodicTask #28).
본 커맨드는 수동/온디맨드 트리거 전용.

예:
    python manage.py evaluate_monitors                 # 전체 active Monitor
    python manage.py evaluate_monitors --monitor-id X  # 특정 Monitor
    python manage.py evaluate_monitors --user alice     # 특정 사용자
"""
from django.core.management.base import BaseCommand

from apps.monitor.models import Monitor
from apps.monitor.services.pipeline import evaluate_monitors


class Command(BaseCommand):
    help = "Monitor 평가 파이프라인 실행 (지표 스코어→집계→스냅샷→상태)"

    def add_arguments(self, parser):
        parser.add_argument("--monitor-id", dest="monitor_id", default=None)
        parser.add_argument("--user", dest="user", default=None,
                            help="username 필터")
        parser.add_argument("--include-paused", action="store_true",
                            help="status=paused/archived 포함 (기본: 제외)")

    def handle(self, *args, **options):
        qs = Monitor.objects.all()
        if options["monitor_id"]:
            qs = qs.filter(id=options["monitor_id"])
        if options["user"]:
            qs = qs.filter(user__username=options["user"])
        if not options["include_paused"]:
            qs = qs.exclude(status__in=[Monitor.Status.PAUSED, Monitor.Status.ARCHIVED])

        results = evaluate_monitors(qs)
        changed = sum(1 for r in results if r["state_changed"])
        self.stdout.write(
            self.style.SUCCESS(
                f"평가 완료: {len(results)}개 Monitor, 상태변경 {changed}건"
            )
        )
        for r in results:
            self.stdout.write(
                f"  - {r['monitor_id'][:8]} score={r['overall_score']} "
                f"state={r['state']}{' *' if r['state_changed'] else ''}"
            )
