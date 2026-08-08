"""AnalystSignal ingest beat DB 등록 — 멱등 동기화 커맨드 (SFI-I1, 공통버그 #28).

DatabaseScheduler 환경에서 DB PeriodicTask가 유일한 진실(config dict 스케줄 금지).
`apps.portfolio.tasks.ingest_analyst_signals`의 CrontabSchedule + PeriodicTask upsert.

스케줄: **19:30 America/New_York** (SPOT-DAY-CONVENTION 수리, D-I3-4) — spot 기준가가
항상 T(당일) 종가가 되도록 EOD 전량 적재 후행에 배치. 선행 적재 = S&P500 18:00 ET +
비S&P500 monitor freshness 18:45 ET(`ensure_price_freshness`). snapshot(19:00)·advisory
(19:15)는 AnalystSignalSnapshot을 읽지 않으므로 그 뒤로 이동해도 하류 파손 없음.
timezone은 CrontabSchedule.timezone 필드(DST 자동, UTC 고정 금지).

★ 실행 = 병진 수동(DB PeriodicTask = prod-write). Claude Code는 커맨드 정의까지.
사용: `python manage.py sync_analyst_signals_beat` (멱등) / `--dry-run` 예정만 출력.
"""

from django.core.management.base import BaseCommand

BEAT_NAME = "portfolio-analyst-signals-daily"
BEAT_TASK = "apps.portfolio.tasks.ingest_analyst_signals"
CRONTAB = {
    "minute": "30",
    "hour": "19",  # SPOT-DAY-CONVENTION 수리(D-I3-4): 18→19 ET, T 종가 적재 후행 보장
    "day_of_week": "1-5",
    "day_of_month": "*",
    "month_of_year": "*",
    "timezone": "America/New_York",
}
BEAT_DESCRIPTION = (
    "coach 유니버스(보유∪관심) forward 신호(price target·grades·ratings) nightly 수집 "
    "→ AnalystSignalSnapshot append + Stock.analyst_* 미러. 19:30 ET (EOD+monitor freshness "
    "후, spot=T 종가 보장; snapshot/advisory는 ASS 미독으로 순서 무관). "
    "estimates 무접촉(chain_sight 정본, D-I1-4)."
)


class Command(BaseCommand):
    help = "AnalystSignal ingest nightly beat DB 등록 (멱등, #28)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.stdout.write(
                f"[dry-run] {BEAT_NAME} → {BEAT_TASK} "
                f"@ {CRONTAB['hour']}:{CRONTAB['minute']} {CRONTAB['timezone']} "
                f"(dow={CRONTAB['day_of_week']})"
            )
            return

        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        schedule, _ = CrontabSchedule.objects.get_or_create(**CRONTAB)
        task, created = PeriodicTask.objects.update_or_create(
            name=BEAT_NAME,
            defaults={
                "task": BEAT_TASK,
                "crontab": schedule,
                "description": BEAT_DESCRIPTION,
                "enabled": True,
            },
        )
        verb = "생성" if created else "갱신"
        self.stdout.write(self.style.SUCCESS(f"✅ {verb}: {BEAT_NAME} → {BEAT_TASK}"))
