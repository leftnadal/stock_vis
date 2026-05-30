"""Phase 1 — Agent별 도메인 분리 보고서 Beat schedule을 DB에 등록.

DatabaseScheduler 사용 환경에서 config dict는 무시되므로 PeriodicTask 직접 등록.
common-bugs #28 대응 패턴 (metrics-daily-report-7am-kst와 동일).

실행: `python manage.py register_agent_report_tasks`
멱등: 이미 등록된 항목은 update_or_create로 갱신.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, PeriodicTask

# (name, domain, hour, minute) — 모두 KST
AGENT_SCHEDULES = [
    ("agent-report-data-6am-kst", "data", 6, 0),
    ("agent-report-backend-615am-kst", "backend", 6, 15),
    ("agent-report-qa-630am-kst", "qa", 6, 30),
    ("agent-report-design-645am-kst", "design", 6, 45),
]


class Command(BaseCommand):
    help = "Register agent report Beat schedules (data/backend/qa/design)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="실제 등록 없이 어떤 항목이 등록될지만 출력",
        )

    def handle(self, *args, **opts):
        dry_run = opts.get("dry_run", False)
        tz = "Asia/Seoul"

        registered = []
        for name, domain, hour, minute in AGENT_SCHEDULES:
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=str(minute),
                hour=str(hour),
                day_of_week="*",
                day_of_month="*",
                month_of_year="*",
                timezone=tz,
            )

            if dry_run:
                self.stdout.write(
                    f"[DRY] {name}: cron={hour:02d}:{minute:02d} {tz} task=metrics.tasks.send_agent_report_task domain={domain}"
                )
                registered.append(name)
                continue

            task, created = PeriodicTask.objects.update_or_create(
                name=name,
                defaults={
                    "crontab": schedule,
                    "interval": None,
                    "task": "metrics.tasks.send_agent_report_task",
                    "args": json.dumps([domain]),
                    "kwargs": json.dumps({}),
                    "enabled": True,
                    "description": f"Phase 1 agent domain report: {domain} (KST {hour:02d}:{minute:02d})",
                },
            )
            status = "CREATED" if created else "UPDATED"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{status} {name} → {hour:02d}:{minute:02d} KST domain={domain}"
                )
            )
            registered.append(name)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"총 {len(registered)}개 schedule {'DRY-RUN' if dry_run else '등록 완료'}."
            )
        )
