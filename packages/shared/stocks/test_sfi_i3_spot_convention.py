"""SFI-I3 SPOT-DAY-CONVENTION 수리 — epoch 코호트 분리 (D-I3-5)."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from packages.shared.stocks.services import analyst_scoring as sc


def test_convention_epoch_constant():
    assert sc.CONVENTION_EPOCH == date(2026, 8, 7)
    assert sc.SCORING_VERSION == 1  # 수식 무변경 — epoch은 코호트 축


@pytest.mark.django_db
def test_pinned_epoch_split_pre_and_post():
    from packages.shared.stocks.models import AnalystSignalSnapshot as A

    # pre-epoch pinned (2026-08-06 발화, 혼합 관례)
    a_pre = A.objects.create(symbol="EPC", target_consensus=Decimal("110"),
                             spot_at_capture=Decimal("100"))
    A.objects.filter(pk=a_pre.pk).update(
        captured_at=datetime(2026, 8, 6, 22, 31, tzinfo=timezone.utc))
    # post-epoch pinned (2026-08-07 발화, T 관례)
    a_post = A.objects.create(symbol="EPC", target_consensus=Decimal("120"),
                              spot_at_capture=Decimal("105"))
    A.objects.filter(pk=a_post.pk).update(
        captured_at=datetime(2026, 8, 7, 23, 30, tzinfo=timezone.utc))

    r = sc.score_tier1(date(2026, 8, 20))
    es = r["cohorts"]["pinned"]["epoch_split"]
    assert es["convention_epoch"] == "2026-08-07"
    assert es["pre_mixed"] == 1
    assert es["post_t"] == 1


@pytest.mark.django_db
def test_derived_cohort_has_no_epoch_split():
    r = sc.score_tier1(date(2026, 8, 20))
    assert "epoch_split" in r["cohorts"]["pinned"]
    assert "epoch_split" not in r["cohorts"]["derived"]
