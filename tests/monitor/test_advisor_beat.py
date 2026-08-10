"""ADVISOR beat 배선 통합 검증 (MON-P4-LA T2).

태스크 서명·PeriodicTask 등록을 실제 beat 호출 경로 그대로 검증(직접 함수 호출 대체
금지 — as_of 서명 사건 재발 방지). 등록 task 문자열이 실제 태스크로 apply 실행되는지까지.
"""
import pytest
from django.core.management import call_command
from django_celery_beat.models import PeriodicTask

from apps.monitor import tasks as monitor_tasks

ADVISOR_BEAT = "advisor-daily-briefing"
ADVISOR_TASK_PATH = "apps.monitor.tasks.advisor_briefing_task"


@pytest.mark.django_db
class TestAdvisorTask:
    def test_disabled_is_noop(self, settings):
        settings.ADVISOR_ENABLED = False
        r = monitor_tasks.advisor_briefing_task.apply().get()
        assert r["status"] == "disabled"

    def test_enabled_runs_over_monitors(self, settings, monkeypatch, monitor):
        # ADVISOR_ENABLED=True + EOD 신선 → stock 모니터 loop. 스냅샷 없는 monitor는 스킵.
        settings.ADVISOR_ENABLED = True
        monkeypatch.setattr("apps.monitor.tasks.is_eod_fresh", lambda *a, **k: True)
        r = monitor_tasks.advisor_briefing_task.apply().get()
        assert r["status"] == "ok"
        assert r["created"] == 0 and r["skipped"] == 1  # AAPL, 스냅샷 없음 → 스킵

    def test_failure_isolated_per_symbol(self, settings, monkeypatch, monitor):
        # D2: 한 종목 generate_briefing 예외 → 그 종목만 failed, 태스크는 완주.
        settings.ADVISOR_ENABLED = True
        monkeypatch.setattr("apps.monitor.tasks.is_eod_fresh", lambda *a, **k: True)

        def _boom(m):
            raise RuntimeError("llm down")

        monkeypatch.setattr(
            "apps.monitor.services.advisor_briefing.generate_briefing", _boom
        )
        r = monitor_tasks.advisor_briefing_task.apply().get()
        assert r["status"] == "ok" and r["failed"] == 1


@pytest.mark.django_db
class TestAdvisorBeatRegistration:
    def test_task_path_matches_registered_name(self):
        # 등록될 task 문자열 = 실제 태스크의 celery 이름(서명 정합)
        assert monitor_tasks.advisor_briefing_task.name == ADVISOR_TASK_PATH

    def test_sync_registers_disabled_beat(self):
        call_command("sync_monitor_beat")
        t = PeriodicTask.objects.get(name=ADVISOR_BEAT)
        assert t.enabled is False  # 기본 OFF(이중잠금)
        assert t.task == ADVISOR_TASK_PATH
        assert t.crontab.hour == "18" and t.crontab.minute == "50"
        assert t.crontab.day_of_week == "1-5"
        assert t.crontab.timezone.key == "America/New_York"

    def test_sync_preserves_manual_enable(self):
        # get_or_create → 수동 점등 후 멱등 재실행이 되돌리지 않는다(§8 점등 보존)
        call_command("sync_monitor_beat")
        t = PeriodicTask.objects.get(name=ADVISOR_BEAT)
        t.enabled = True
        t.save()
        call_command("sync_monitor_beat")  # 재실행
        t.refresh_from_db()
        assert t.enabled is True
