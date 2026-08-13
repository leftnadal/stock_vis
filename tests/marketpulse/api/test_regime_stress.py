"""MPS-1 MP-STRESS — regime/stress 엔드포인트 회귀.

계약(§3.1 payload): score·level_band·percentile{value,window_days}·
  direction{stress{d5,d20,state}, price{vs_ma20,vs_ma60,state}}·categories[5]·as_of.
  baseline = 소급 모집단(고정 잣대) / 마커 미노출 / 소급 부재 시 빈 응답 / 판정 무접촉.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.market_pulse.management.commands.backfill_v2_regime_vectors import BACKFILL_MARK
from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.regime.stress import STRESS_CATEGORIES

User = get_user_model()
pytestmark = [pytest.mark.django_db]

_KEYS = [
    "return_1d_pct", "vol_20d_pct", "drawdown_pct", "nfci", "nfci_credit",
    "nfci_leverage", "nfci_risk", "hy_oas_pct", "hy_ccc_oas_pct",
    "t10y2y_pct", "t10y3m_pct", "vix", "vix3m", "move",
]


@pytest.fixture(autouse=True)
def _clear():
    from macro.models.indicators import MarketIndexPrice

    cache.clear()
    RegimeSnapshot.objects.all().delete()
    MarketIndexPrice.objects.all().delete()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    u = User.objects.create_user(username="st", email="st@e.com", password="pw")
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


def _weekdays_ending(end, n):
    """end(포함) 이하 거래일 n개를 오름차순으로 — 최신 스냅샷=오늘 시나리오 재현."""
    out, d = [], end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


def _vec(scale):
    return {k: round(0.5 * scale + i * 0.1, 3) for i, k in enumerate(_KEYS)}


def _seed_population(n=35):
    """고정 잣대용 소급 모집단(std>0, n≥30)."""
    for i, d in enumerate(_weekdays(date(2023, 8, 7), n)):
        RegimeSnapshot.objects.create(
            date=d, snapshot_time=d, regime=RegimeSnapshot.Regime.TRANSITION,
            status=RegimeSnapshot.Status.OK, coverage=1.0, headline="h",
            inputs=_vec(1.0 + i * 0.02), fired_rules=[], previous_regime="",
            hysteresis_streak=1, summary=BACKFILL_MARK,
        )


def _seed_live_rising(n=25):
    """최근 라이브 스냅샷 — 벡터 단조 증가(스트레스 악화). 최신 = 최고."""
    days = _weekdays_ending(timezone.localdate(), n)
    for i, d in enumerate(days):
        RegimeSnapshot.objects.update_or_create(
            date=d,
            defaults=dict(
                snapshot_time=d, regime=RegimeSnapshot.Regime.LATE_BULL,
                status=RegimeSnapshot.Status.OK, coverage=1.0, headline="h",
                inputs=_vec(2.0 + i * 0.05), fired_rules=[], previous_regime="",
                hysteresis_streak=1, summary="live",
            ),
        )
    return days


def _seed_spy_rising(n=65):
    from macro.models.indicators import MarketIndex, MarketIndexPrice

    spy, _ = MarketIndex.objects.get_or_create(symbol="SPY", defaults={"name": "SPY"})
    for i, d in enumerate(_weekdays(timezone.localdate() - timedelta(days=100), n)):
        if d > timezone.localdate():
            break
        MarketIndexPrice.objects.get_or_create(
            index=spy, date=d, defaults={"close": Decimal(str(300 + i))}
        )


def _url():
    return reverse("marketpulse_api_v2:regime-stress")


class TestRegimeStress:
    def test_empty_when_no_population(self, auth_client):
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is False

    def test_payload_contract(self, auth_client):
        _seed_population()
        _seed_live_rising()
        _seed_spy_rising()
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is True
        assert isinstance(body["score"], float)
        assert body["level_band"] in {"stable", "caution", "severe"}
        assert set(body["percentile"]) == {"value", "window_days"}
        assert body["percentile"]["window_days"] >= 1
        # direction 2종
        assert set(body["direction"]["stress"]) == {"d5", "d20", "state"}
        assert set(body["direction"]["price"]) == {"vs_ma20", "vs_ma60", "state"}
        # categories 5개(표시축) 전수
        assert {c["key"] for c in body["categories"]} == set(STRESS_CATEGORIES)
        assert all({"key", "z", "d5"} == set(c) for c in body["categories"])
        assert body["as_of"] == timezone.localdate().isoformat()
        # band 잠정 표기(정직)
        assert body["meta"]["band_provisional"] is True

    def test_rising_series_worsening_and_uptrend(self, auth_client):
        _seed_population()
        _seed_live_rising()
        _seed_spy_rising()
        body = auth_client.get(_url()).json()["data"]
        # 단조 증가 벡터 → 스트레스 악화
        assert body["direction"]["stress"]["state"] == "worsening"
        assert body["direction"]["stress"]["d5"] > 0
        assert body["direction"]["stress"]["d20"] > 0
        # 상승 SPY → 종가 > MA20 > MA60
        assert body["direction"]["price"]["state"] == "uptrend"
        # 최신이 역사 최고 → 백분위 100
        assert body["percentile"]["value"] == pytest.approx(100.0)

    def test_marker_not_exposed(self, auth_client):
        _seed_population()
        _seed_live_rising()
        _seed_spy_rising()
        raw = auth_client.get(_url()).content.decode()
        assert BACKFILL_MARK not in raw

    def test_regime_snapshots_untouched(self, auth_client):
        """판정 무접촉 증빙: 조회가 RegimeSnapshot을 쓰지 않음(read-only)."""
        _seed_population()
        _seed_live_rising()
        _seed_spy_rising()
        before = list(
            RegimeSnapshot.objects.order_by("date").values_list("date", "regime", "status")
        )
        auth_client.get(_url())
        after = list(
            RegimeSnapshot.objects.order_by("date").values_list("date", "regime", "status")
        )
        assert before == after
