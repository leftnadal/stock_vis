"""SFI-I3 Part 3 ④ 개정 추적 + 규칙 6 경계 테스트."""
import pathlib
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from packages.shared.stocks.services.analyst_revision import revision_tracking


@pytest.mark.django_db
def test_revision_tracking_deltas_and_consensus():
    from packages.shared.stocks.models import AnalystSignalSnapshot

    rows = [
        (datetime(2026, 1, 5, 22, 30, tzinfo=timezone.utc), Decimal("100"), "Buy"),
        (datetime(2026, 1, 6, 22, 30, tzinfo=timezone.utc), Decimal("105"), "Buy"),
        (datetime(2026, 1, 7, 22, 30, tzinfo=timezone.utc), Decimal("102"), "Hold"),
    ]
    for ts, tc, gc in rows:
        a = AnalystSignalSnapshot.objects.create(
            symbol="RVN", target_consensus=tc, grade_consensus=gc,
        )
        AnalystSignalSnapshot.objects.filter(pk=a.pk).update(captured_at=ts)

    r = revision_tracking(date(2026, 1, 10))
    sym = r["per_symbol"]["RVN"]
    assert sym["snapshots"] == 3
    assert sym["revision_count"] == 2  # 100→105, 105→102
    assert len(sym["consensus_changes"]) == 1  # Buy→Hold
    assert sym["last_consensus"] == "Hold"
    assert r["aggregate"]["total_revisions"] == 2
    assert r["aggregate"]["median_abs_delta"] == pytest.approx(4.0)  # median(|+5|,|-3|)


@pytest.mark.django_db
def test_revision_respects_as_of():
    from packages.shared.stocks.models import AnalystSignalSnapshot

    a = AnalystSignalSnapshot.objects.create(symbol="FUT", target_consensus=Decimal("100"))
    AnalystSignalSnapshot.objects.filter(pk=a.pk).update(
        captured_at=datetime(2026, 2, 1, 22, 30, tzinfo=timezone.utc)
    )
    r = revision_tracking(date(2026, 1, 10))  # as_of 이전 → 제외
    assert "FUT" not in r["per_symbol"]


def test_shared_scoring_modules_do_not_import_apps():
    """규칙 6: packages/shared 채점 모듈은 apps를 import하지 않는다."""
    base = pathlib.Path(__file__).resolve().parent / "services"
    for name in ("analyst_scoring.py", "analyst_revision.py"):
        src = (base / name).read_text()
        assert "from apps" not in src and "import apps" not in src, f"{name} imports apps"
