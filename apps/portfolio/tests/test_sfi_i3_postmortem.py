"""SFI-I3 Part 3 ⑤ advisory 사후분석 v0 테스트."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.portfolio.models_my import AdvisoryRun, PortfolioSnapshot
from apps.portfolio.services.advisory_postmortem import advisory_postmortem_v0

User = get_user_model()


def _run(user, ts, knobs, snapshot=None):
    r = AdvisoryRun.objects.create(
        user=user, trigger="auto", output={}, knobs_snapshot=knobs, snapshot=snapshot,
    )
    AdvisoryRun.objects.filter(pk=r.pk).update(run_at=ts)
    return r


@pytest.mark.django_db
def test_postmortem_counts_and_knob_variation():
    u = User.objects.create(username="pm1")
    _run(u, datetime(2026, 1, 5, 23, 15, tzinfo=timezone.utc), {"A": 0.1, "G": 5, "w": 1, "L": 2, "E": 3})
    _run(u, datetime(2026, 1, 6, 23, 15, tzinfo=timezone.utc), {"A": 0.2, "G": 5, "w": 1, "L": 2, "E": 3})
    # manual 1건 (run_at을 as_of 창 안으로 설정 — auto_now_add 우회)
    m = AdvisoryRun.objects.create(user=u, trigger="manual", output={}, knobs_snapshot={})
    AdvisoryRun.objects.filter(pk=m.pk).update(
        run_at=datetime(2026, 1, 7, 23, 15, tzinfo=timezone.utc)
    )

    r = advisory_postmortem_v0(date(2026, 1, 10))
    assert r["auto_run_count"] == 2
    assert r["manual_run_count"] == 1
    assert r["knob_variation"]["A"]["distinct"] == 2  # 0.1, 0.2
    assert r["knob_variation"]["G"]["distinct"] == 1  # 상수


@pytest.mark.django_db
def test_postmortem_nav_h21_realized_and_caveat():
    u = User.objects.create(username="pm2")
    PortfolioSnapshot.objects.create(user=u, date=date(2026, 1, 5), total_krw=Decimal("1000"))
    PortfolioSnapshot.objects.create(user=u, date=date(2026, 2, 10), total_krw=Decimal("1100"))
    r = advisory_postmortem_v0(date(2026, 3, 1))
    nav = r["nav_trajectory"]["pm2"]
    assert "RUN-TOTAL-PERSIST" in nav["caveat"]  # 캐비앗 의무
    assert nav["h21_realized"]["delta_krw"] == "100.00"
    assert nav["h21_realized"]["pct"] == pytest.approx(0.1)


@pytest.mark.django_db
def test_postmortem_nav_immature():
    u = User.objects.create(username="pm3")
    PortfolioSnapshot.objects.create(user=u, date=date(2026, 1, 5), total_krw=Decimal("1000"))
    r = advisory_postmortem_v0(date(2026, 1, 8))  # 21거래일 미도달
    nav = r["nav_trajectory"]["pm3"]
    assert nav["h21_realized"]["status"] == "immature"
    assert nav["h21_realized"]["earliest_maturity_est"] is not None
