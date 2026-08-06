"""SFI-I3 Part 4 — score_analyst_signals 판정 리포트 커맨드 스모크."""
from datetime import date, datetime, timezone
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from packages.shared.stocks.models import AnalystSignalSnapshot


@pytest.mark.django_db
def test_command_renders_report_sections():
    a = AnalystSignalSnapshot.objects.create(
        symbol="RPT", target_consensus=Decimal("110"), spot_at_capture=Decimal("100"),
        grade_consensus="Buy",
    )
    AnalystSignalSnapshot.objects.filter(pk=a.pk).update(
        captured_at=datetime(2026, 1, 5, 22, 30, tzinfo=timezone.utc)
    )
    out = StringIO()
    call_command("score_analyst_signals", "--as-of", "2026-01-10", stdout=out)
    text = out.getvalue()
    assert "재현 좌표" in text
    assert "SCORING_VERSION" in text
    assert "【Tier 1 — 판정 과목】" in text
    assert "【Tier 2 — 관측 과목】" in text
    assert "AdvisoryRun=" in text  # 헤더에 apps 계층 행수 주입(규칙 6)
    # 표본 미도달 과목은 은폐하지 않고 명시
    assert "표본 미도달" in text


@pytest.mark.django_db
def test_command_runs_on_empty_db():
    out = StringIO()
    call_command("score_analyst_signals", "--as-of", "2026-01-10", stdout=out)
    assert "재현 좌표" in out.getvalue()
