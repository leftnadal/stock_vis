"""SFI-I1 Part 4 — beat sync 커맨드 dry-run smoke (DB 무접촉).

등록(prod-write)은 병진 수동. 여기선 커맨드 로드·스케줄 상수·dry-run 출력만 검증.
"""
from io import StringIO

from django.core.management import call_command

from apps.portfolio.management.commands import sync_analyst_signals_beat as cmd


def test_schedule_constants():
    assert cmd.BEAT_TASK == "apps.portfolio.tasks.ingest_analyst_signals"
    assert cmd.CRONTAB["hour"] == "18" and cmd.CRONTAB["minute"] == "30"
    assert cmd.CRONTAB["timezone"] == "America/New_York"
    assert cmd.CRONTAB["day_of_week"] == "1-5"


def test_dry_run_no_db_write():
    out = StringIO()
    call_command("sync_analyst_signals_beat", "--dry-run", stdout=out)
    text = out.getvalue()
    assert "[dry-run]" in text
    assert "portfolio-analyst-signals-daily" in text
    assert "18:30" in text
