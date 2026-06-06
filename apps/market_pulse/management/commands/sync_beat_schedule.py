"""
sync_beat_schedule — DatabaseScheduler `PeriodicTask.task` 경로 reconcile (Bug #28).

소속: apps/market_pulse/management/commands (app 레이어 운영 커맨드).
역할: `config/celery.py`의 `app.conf.beat_schedule[name]['task']`를 진실의 소스로 두고,
  DB `PeriodicTask.task` 컬럼만 reconcile. monorepo PR4(2026-05-31) 이후 task name이
  옛 경로(`marketpulse.tasks.*`)로 남아 있으면 Beat 디스패치가 ImportError → unregistered
  task로 실패하는 패턴을 해소.

사용:
    python manage.py sync_beat_schedule              # dry-run (기본, diff 출력만)
    python manage.py sync_beat_schedule --apply      # 실제 UPDATE

원칙:
    - dict에 없는 name은 무시(extra DB rows 정보 출력).
    - dict에 있지만 DB에 없는 name은 경고만(생성 안 함).
    - schedule/crontab/enabled 등 다른 필드는 건드리지 않음(task 컬럼 only).
    - idempotent: 이미 일치하면 0 rows.
    - --apply 후 celery beat 재시작 필요.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask


class Command(BaseCommand):
    help = "Beat schedule DB row 의 task 경로를 settings dict 와 reconcile (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="실제 DB UPDATE 수행. 기본은 dry-run (변경 사항만 출력).",
        )

    def handle(self, *args, **options) -> None:
        from config.celery import app

        schedule = app.conf.beat_schedule or {}
        apply_changes: bool = options["apply"]

        changes: list[tuple[str, str, str]] = []
        missing_db: list[str] = []
        for name, entry in schedule.items():
            expected_task = (entry or {}).get("task")
            if not expected_task:
                continue
            current = (
                PeriodicTask.objects.filter(name=name)
                .values_list("task", flat=True)
                .first()
            )
            if current is None:
                missing_db.append(name)
                continue
            if current != expected_task:
                changes.append((name, current, expected_task))

        dict_names = {n for n, e in schedule.items() if (e or {}).get("task")}
        db_names = set(PeriodicTask.objects.values_list("name", flat=True))
        extra_db = sorted(db_names - dict_names)

        for name, old, new in changes:
            self.stdout.write(f"{name}: {old} -> {new}")

        if missing_db:
            self.stdout.write(
                self.style.WARNING(
                    f"dict 에 있지만 DB 에 없는 schedule: {missing_db} (생성 안 함)"
                )
            )
        if extra_db:
            self.stdout.write(
                self.style.WARNING(
                    f"DB 에 있지만 dict 에 없는 schedule: {extra_db} (스킵)"
                )
            )

        if not changes:
            self.stdout.write(self.style.SUCCESS("동기화 필요 없음 (0 rows)"))
            return

        if apply_changes:
            updated = 0
            for name, _old, new in changes:
                updated += PeriodicTask.objects.filter(name=name).update(task=new)
            self.stdout.write(self.style.SUCCESS(f"{updated} rows updated"))
            self.stdout.write(
                self.style.WARNING("celery beat 재시작 필요 (스케줄러 캐시 갱신).")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"[dry-run] {len(changes)} rows would be updated")
            )
            self.stdout.write("--apply 플래그로 실제 UPDATE 수행")
