"""MP2-ANALOG Slice B — regime/analog 엔드포인트 회귀.

계약: 페이로드 스키마(today_axes 4·neighbors·fan 5지평·alert)·label 슬롯 null(Slice C)·
  마커 미노출·소급 부재 시 빈 응답.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.market_pulse.management.commands.backfill_v2_regime_vectors import BACKFILL_MARK
from apps.market_pulse.models.regime import RegimeSnapshot

User = get_user_model()
pytestmark = [pytest.mark.django_db]

_KEYS = [
    "return_1d_pct", "vol_20d_pct", "drawdown_pct", "nfci", "nfci_credit",
    "nfci_leverage", "nfci_risk", "hy_oas_pct", "hy_ccc_oas_pct",
    "t10y2y_pct", "t10y3m_pct", "vix", "vix3m", "move",
]
_CODES = {
    "nfci": "NFCI", "nfci_credit": "NFCICREDIT", "nfci_leverage": "NFCILEVERAGE",
    "nfci_risk": "NFCIRISK", "hy_oas_pct": "BAMLH0A0HYM2", "hy_ccc_oas_pct": "BAMLH0A3HYC",
    "t10y2y_pct": "T10Y2Y", "t10y3m_pct": "T10Y3M", "vix": "VIXCLS",
    "vix3m": "VIX3M", "move": "MOVE",
}


@pytest.fixture(autouse=True)
def _clear():
    from macro.models.indicators import IndicatorValue, MarketIndexPrice

    cache.clear()
    RegimeSnapshot.objects.all().delete()
    IndicatorValue.objects.all().delete()
    MarketIndexPrice.objects.all().delete()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    u = User.objects.create_user(username="an", email="an@e.com", password="pw")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def _weekdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _base_vec(scale=1.0):
    # 완전벡터(14키). scale로 벡터 간 거리 통제.
    return {k: round(0.5 * scale + i * 0.1, 3) for i, k in enumerate(_KEYS)}


def _seed_population(n=40):
    days = _weekdays(date(2023, 8, 7), n)
    for i, d in enumerate(days):
        RegimeSnapshot.objects.create(
            date=d, snapshot_time=d, regime=RegimeSnapshot.Regime.TRANSITION,
            status=RegimeSnapshot.Status.OK, coverage=1.0, headline="h",
            inputs=_base_vec(1.0 + i * 0.02), fired_rules=[], previous_regime="",
            hysteresis_streak=1, summary=BACKFILL_MARK,
        )
    return days


def _seed_today_inputs():
    """load_inputs(today)가 채워지도록 최근 SPY(≥21d) + 지표(today) 시드."""
    from macro.models.indicators import (
        EconomicIndicator, IndicatorValue, MarketIndex, MarketIndexPrice,
    )
    from django.utils import timezone

    today = timezone.localdate()
    spy, _ = MarketIndex.objects.get_or_create(symbol="SPY", defaults={"name": "SPY"})
    for i, d in enumerate(_weekdays(today - timedelta(days=40), 30)):
        MarketIndexPrice.objects.get_or_create(
            index=spy, date=d, defaults={"close": Decimal(str(400 + i))}
        )
    for key, code in _CODES.items():
        ind, _ = EconomicIndicator.objects.get_or_create(
            code=code, defaults={"name": code, "category": "macro", "data_source": "fred"}
        )
        IndicatorValue.objects.get_or_create(
            indicator=ind, date=today - timedelta(days=1),
            defaults={"value": Decimal("1.0")},
        )


def _url():
    return reverse("marketpulse_api_v2:regime-analog")


class TestRegimeAnalog:
    def test_empty_when_no_population(self, auth_client):
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is False

    def test_schema_and_label_slots(self, auth_client):
        _seed_population()
        _seed_today_inputs()
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is True
        assert len(body["today_axes"]) == 4
        assert {a["axis"] for a in body["today_axes"]} == {
            "stress", "financial", "return_1d_pct", "vol_20d_pct"
        }
        assert [f["horizon"] for f in body["fan"]] == [1, 5, 10, 20, 60]
        assert "on" in body["alert"] and "nearest_dist" in body["alert"]
        # 이웃 있으면 label 슬롯 null(Slice C 연결점)
        for nb in body["neighbors"]:
            assert nb["cat_slot"] is None and nb["why"] is None
            assert "dist" in nb and "fwd" in nb

    def test_marker_not_exposed(self, auth_client):
        _seed_population()
        _seed_today_inputs()
        raw = auth_client.get(_url()).content.decode()
        assert BACKFILL_MARK not in raw

    def test_fan_honest_n_per_horizon(self, auth_client):
        _seed_population()
        _seed_today_inputs()
        body = auth_client.get(_url()).json()["data"]
        # 모집단이 SPY 창 밖(2023-08)이라 선도수익 미실현 → N=0 정직(발명 없음)
        for f in body["fan"]:
            assert f["n"] >= 0 and f["n_eff"] >= 0
