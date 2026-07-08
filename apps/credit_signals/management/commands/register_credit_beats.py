"""
credit_signals beat 등록 관리 명령 (PR §5).

DatabaseScheduler는 config dict를 무시하므로(bug #28) PeriodicTask를 DB에 직접
멱등 등록한다(register_chainsight_beats 패턴 복제). 암묵 자동 등록 금지 —
반드시 이 커맨드를 명시 실행해야 beat가 산다.

★ §5 추가 요구: 등록 전 기존 beat와의 시간 충돌을 조회·출력한다
   (thesis 앱 beat 충돌 이슈 미결 상태 → 같은 (hour, minute)에 몰리지 않게 확인).

스케줄 (Asia/Seoul):
  - ingest_fred_daily_task        매일 07:30 (미 동부 마감 + FRED 반영 이후)
  - check_credit_ingest_succeeded 매일 09:00

사용:
    python manage.py register_credit_beats           # 충돌 검사 + 등록/갱신
    python manage.py register_credit_beats --dry-run # 미적용, 충돌 검사 + 계획만 출력
"""
from django.core.management.base import BaseCommand

BEATS = [
    {
        "name": "credit-signals-ingest-fred-daily",
        "task": "apps.credit_signals.tasks.ingest_fred_daily_task",
        "minute": "30",
        "hour": "7",
        "timezone": "Asia/Seoul",
        "day_of_week": None,  # 매일
    },
    {
        "name": "credit-signals-verify-ingest",
        "task": "apps.credit_signals.tasks.check_credit_ingest_succeeded",
        "minute": "0",
        "hour": "9",
        "timezone": "Asia/Seoul",
        "day_of_week": None,  # 매일 (주말은 태스크 내부에서 통과)
    },
]


class Command(BaseCommand):
    help = "credit_signals 일배치(ingest/verify) PeriodicTask를 DB에 멱등 등록 (+ 충돌 검사)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="실제 등록 없이 충돌 검사 + 등록 계획만 출력.",
        )

    def _report_conflicts(self, PeriodicTask):
        """등록하려는 (hour, minute)에 이미 걸린 다른 beat를 출력 (§5)."""
        self.stdout.write("── 기존 beat 충돌 검사 ──")
        our_names = {b["name"] for b in BEATS}
        found_any = False
        for beat in BEATS:
            same_time = (
                PeriodicTask.objects.filter(
                    crontab__hour=beat["hour"], crontab__minute=beat["minute"]
                )
                .exclude(name__in=our_names)
                .select_related("crontab")
            )
            if same_time.exists():
                found_any = True
                for pt in same_time:
                    tz = getattr(pt.crontab, "timezone", "?")
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ 동일 시각 {beat['hour']}:{beat['minute']} — "
                            f"'{pt.name}' (tz={tz}) 이미 등록됨 "
                            f"[신규 '{beat['name']}' tz={beat['timezone']}]"
                        )
                    )
        if not found_any:
            self.stdout.write("  충돌 없음 (07:30 / 09:00 Asia/Seoul 비어 있음).")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        self._report_conflicts(PeriodicTask)

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
