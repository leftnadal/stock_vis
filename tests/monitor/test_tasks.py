"""Monitor beat 태스크 + sync 커맨드 검증 (MON-P2-BEAT §7).

커버:
  - 신선도 가드 순수 판정(is_eod_fresh): 오늘 EOD 있음/없음.
  - refresh_monitors_task: EOD 신선 → 서비스 호출 / stale → 재시도(countdown=1200) /
    재시도 소진 → 경고 후 skip.
  - sync_monitor_beat: 구 thesis 4레코드 삭제 + monitor beat 등록 + 멱등성(2회 실행 동일).
"""
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from celery.exceptions import MaxRetriesExceededError, Retry
from django.core.management import call_command
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from apps.monitor import tasks as monitor_tasks
from apps.monitor.management.commands.sync_monitor_beat import (
    LEGACY_THESIS_TASK_NAMES,
    MONITOR_BEAT_NAME,
    MONITOR_BEAT_TASK,
)


# ── 신선도 가드 순수 판정 ──────────────────────────────────────────────────


class TestIsEodFresh:
    def test_fresh_when_latest_equals_today(self):
        today = date(2026, 7, 9)
        assert monitor_tasks.is_eod_fresh(today, latest=today) is True

    def test_stale_when_latest_behind(self):
        today = date(2026, 7, 9)
        assert monitor_tasks.is_eod_fresh(today, latest=date(2026, 7, 8)) is False

    def test_stale_when_explicit_none(self):
        today = date(2026, 7, 9)
        # latest를 명시 sentinel로 넘기면 DB 조회 없이 순수 판정 — None은 조회 트리거라
        # 여기선 '오늘과 다른 과거일'로 no-data 아닌 stale을 순수 검증.
        assert monitor_tasks.is_eod_fresh(today, latest=date(1970, 1, 1)) is False

    @pytest.mark.django_db
    def test_stale_when_db_empty(self):
        today = date(2026, 7, 9)
        # EODSignal 0건 → latest_eod_date()=None → stale.
        assert monitor_tasks.is_eod_fresh(today, latest=None) is False

    @pytest.mark.django_db
    def test_reads_latest_from_db(self):
        from packages.shared.stocks.models import EODSignal, Stock

        stock = Stock.objects.create(symbol="AAPL", stock_name="Apple Inc.")
        d = date.today()
        EODSignal.objects.create(stock=stock, date=d, close_price=100.0, composite_score=0.1)
        assert monitor_tasks.latest_eod_date() == d
        assert monitor_tasks.is_eod_fresh(d) is True
        assert monitor_tasks.is_eod_fresh(d + timedelta(days=1)) is False


# ── refresh_monitors_task 경로 ────────────────────────────────────────────


@pytest.mark.django_db
class TestRefreshMonitorsTask:
    def test_runs_refresh_when_eod_fresh(self):
        """EOD 신선 → 서비스 함수 refresh_monitors를 as_of=ET오늘로 호출, status=ok."""
        et = date(2026, 7, 9)
        with patch.object(monitor_tasks, "et_today", return_value=et), patch.object(
            monitor_tasks, "is_eod_fresh", return_value=True
        ), patch(
            "apps.monitor.services.pipeline.refresh_monitors",
            return_value=[
                {"ingested": 3, "state_changed": True},
                {"ingested": 2, "state_changed": False},
            ],
        ) as mock_refresh:
            result = monitor_tasks.refresh_monitors_task.apply().get()

        mock_refresh.assert_called_once_with(as_of_date=et)
        assert result["status"] == "ok"
        assert result["monitors"] == 2
        assert result["readings_ingested"] == 5
        assert result["state_changed"] == 1
        assert result["as_of"] == et.isoformat()

    def test_retries_when_eod_stale(self):
        """오늘 EOD 미도착 → self.retry(countdown=1200) 호출(재스케줄 경로)."""
        et = date(2026, 7, 9)
        with patch.object(monitor_tasks, "et_today", return_value=et), patch.object(
            monitor_tasks, "is_eod_fresh", return_value=False
        ), patch.object(
            monitor_tasks.refresh_monitors_task, "retry", side_effect=Retry()
        ) as mock_retry, patch(
            "apps.monitor.services.pipeline.refresh_monitors"
        ) as mock_refresh:
            # Retry는 재스케줄 신호 — eager 모드에서 전파될 수 있으므로 tolerant 포착.
            try:
                monitor_tasks.refresh_monitors_task.apply()
            except Retry:
                pass

        mock_retry.assert_called_once_with(countdown=monitor_tasks.RETRY_COUNTDOWN)
        mock_refresh.assert_not_called()

    def test_skips_after_max_retries(self):
        """재시도 소진(MaxRetriesExceededError) → 경고 후 skip, 서비스 호출 안 함."""
        et = date(2026, 7, 9)
        with patch.object(monitor_tasks, "et_today", return_value=et), patch.object(
            monitor_tasks, "is_eod_fresh", return_value=False
        ), patch.object(
            monitor_tasks.refresh_monitors_task,
            "retry",
            side_effect=MaxRetriesExceededError(),
        ), patch(
            "apps.monitor.services.pipeline.refresh_monitors"
        ) as mock_refresh:
            result = monitor_tasks.refresh_monitors_task.apply().get()

        assert result["status"] == "skipped_stale_eod"
        assert result["as_of"] == et.isoformat()
        mock_refresh.assert_not_called()


# ── sync_monitor_beat 커맨드 ──────────────────────────────────────────────


def _make_legacy_thesis_beats():
    """폐기된 thesis eod_pipeline beat 4레코드를 재현(삭제 검증용)."""
    cron, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="18", day_of_week="1-5", day_of_month="*", month_of_year="*"
    )
    for name in LEGACY_THESIS_TASK_NAMES:
        PeriodicTask.objects.create(
            name=name, task=f"thesis.tasks.eod_pipeline.{name}", crontab=cron
        )


@pytest.mark.django_db
class TestSyncMonitorBeat:
    def test_registers_monitor_beat_with_et_schedule(self):
        call_command("sync_monitor_beat")

        pt = PeriodicTask.objects.get(name=MONITOR_BEAT_NAME)
        assert pt.task == MONITOR_BEAT_TASK
        assert pt.enabled is True
        assert pt.interval is None
        cron = pt.crontab
        assert cron.minute == "45"
        assert cron.hour == "18"
        assert cron.day_of_week == "1-5"
        assert str(cron.timezone) == "America/New_York"

    def test_deletes_legacy_thesis_beats(self):
        _make_legacy_thesis_beats()
        assert PeriodicTask.objects.filter(name__in=LEGACY_THESIS_TASK_NAMES).count() == 4

        call_command("sync_monitor_beat")

        assert PeriodicTask.objects.filter(name__in=LEGACY_THESIS_TASK_NAMES).count() == 0
        # thesis 흔적 0 (task 경로 기준으로도)
        assert not PeriodicTask.objects.filter(task__icontains="thesis").exists()

    def test_idempotent_second_run(self):
        _make_legacy_thesis_beats()
        call_command("sync_monitor_beat")
        after_first = {
            "monitor_count": PeriodicTask.objects.filter(name=MONITOR_BEAT_NAME).count(),
            "thesis_count": PeriodicTask.objects.filter(
                name__in=LEGACY_THESIS_TASK_NAMES
            ).count(),
            "crontab_id": PeriodicTask.objects.get(name=MONITOR_BEAT_NAME).crontab_id,
        }

        call_command("sync_monitor_beat")  # 2회차 — 동일 최종 상태여야
        after_second = {
            "monitor_count": PeriodicTask.objects.filter(name=MONITOR_BEAT_NAME).count(),
            "thesis_count": PeriodicTask.objects.filter(
                name__in=LEGACY_THESIS_TASK_NAMES
            ).count(),
            "crontab_id": PeriodicTask.objects.get(name=MONITOR_BEAT_NAME).crontab_id,
        }

        assert after_first == after_second
        assert after_second["monitor_count"] == 1
        assert after_second["thesis_count"] == 0

    def test_dry_run_changes_nothing(self):
        _make_legacy_thesis_beats()
        call_command("sync_monitor_beat", "--dry-run")

        # dry-run은 삭제·생성 없이 예정만 출력
        assert PeriodicTask.objects.filter(name__in=LEGACY_THESIS_TASK_NAMES).count() == 4
        assert not PeriodicTask.objects.filter(name=MONITOR_BEAT_NAME).exists()
