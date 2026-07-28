"""TIMING-P2.5 정합 엔진 검증 — 변동성 스케일링(예측 아님) 수치·가드·API."""
import math
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.monitor.models import Monitor
from apps.monitor.services import coherence
from apps.monitor.services.scenario_suggest import recompute_coherence, suggest_scenario

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="coh_user", password="pw12345")


@pytest.fixture
def stock(db):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol="TSTC", stock_name="Test Co")


@pytest.fixture
def prices(stock):
    """변동성 있는 상승 시계열 N일."""
    from packages.shared.stocks.models import DailyPrice

    def _make(n=140, base=100.0, step=0.3, wiggle=1.5):
        for i in range(n):
            d = date(2026, 1, 1) + timedelta(days=i)
            c = base + i * step + (wiggle if i % 2 else -wiggle)
            DailyPrice.objects.create(
                stock=stock, date=d,
                open_price=Decimal(str(c)), high_price=Decimal(str(c + 2)),
                low_price=Decimal(str(c - 2)), close_price=Decimal(str(c)),
                volume=1_000_000,
            )
        return date(2026, 1, 1) + timedelta(days=n - 1)

    return _make


# ── 순수 함수 수치 검증 ────────────────────────────────────────────────────────

def test_horizon_for_target_numeric():
    # ln(110/100)/0.02 = 4.7655 → ²=22.71 td → ×7/5=31.8 cal → 4.54주→5주=35일
    assert coherence.horizon_for_target(100, 110, 0.02) == 35


def test_horizon_clamp_bounds():
    # 아주 가까운 목표 → 최소 14일 클램프
    assert coherence.horizon_for_target(100, 100.5, 0.05) == 14
    # 아주 먼 목표 → 최대 180일 클램프
    assert coherence.horizon_for_target(100, 500, 0.005) == 180


def test_horizon_invalid():
    assert coherence.horizon_for_target(100, 90, 0.02) is None  # target<entry
    assert coherence.horizon_for_target(100, 110, None) is None  # σ 없음
    assert coherence.horizon_for_target(100, 110, 0) is None


def test_target_for_horizon_roundtrip():
    # t=35일 → t_td=25, exp(0.02×5)=1.10517 → ~110.52
    t = coherence.target_for_horizon(100, 35, 0.02)
    assert abs(float(t) - 100 * math.exp(0.02 * 5)) < 0.01


def test_rr_ratio():
    assert coherence.rr_ratio(100, 130, 90) == 3.0  # (130-100)/(100-90)
    assert coherence.rr_ratio(100, 130, 100) is None  # risk 0
    assert coherence.rr_ratio(100, 130, 110) is None  # risk 음수


@pytest.mark.django_db
class TestDailySigma:
    def test_sufficient(self, stock, prices):
        prices(140)
        s = coherence.daily_sigma("TSTC")
        assert s is not None and s > 0

    def test_insufficient(self, stock, prices):
        prices(30)  # < SIGMA_MIN_ROWS+1
        assert coherence.daily_sigma("TSTC") is None


# ── suggest_scenario 확장 ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSuggestExtended:
    def test_prefill_four_fields(self, stock, prices):
        as_of = prices(140)
        r = suggest_scenario("TSTC", as_of=as_of)
        assert r["available"] is True
        assert r["entry_suggest"] is not None
        assert r["stop_suggest"] < r["entry_suggest"]
        assert r["target_suggest"] is not None
        assert r["horizon_days"] is not None
        assert r["deadline_suggest"] is not None
        assert r["rr_suggest"] is not None
        assert r["captions"]["target"] and r["captions"]["deadline"]

    def test_regression_base_keys(self, stock, prices):
        as_of = prices(140)
        r = suggest_scenario("TSTC", as_of=as_of)
        # 기존 P2 키 보존
        for k in ("available", "symbol", "close", "support_low", "entry_suggest", "atr", "stop_suggest", "basis"):
            assert k in r


# ── recompute_coherence 양방향 ────────────────────────────────────────────────

@pytest.mark.django_db
class TestRecompute:
    def test_target_given_returns_horizon(self, stock, prices):
        as_of = prices(140)
        r = recompute_coherence("TSTC", entry=100, target=110, stop=90, as_of=as_of)
        assert r["coherent_horizon_days"] is not None
        assert r["coherent_deadline"]
        assert r["rr"] == 1.0  # (110-100)/(100-90)
        assert "예측 아님" in r["note"]

    def test_deadline_given_returns_target(self, stock, prices):
        as_of = prices(140)
        dl = (as_of + timedelta(days=35)).isoformat()
        r = recompute_coherence("TSTC", entry=100, deadline=dl, stop=90, as_of=as_of)
        assert r["coherent_target"] is not None
        assert float(r["coherent_target"]) > 100  # 상승 목표

    def test_sigma_none_graceful(self, stock, prices):
        as_of = prices(30)  # σ 산출 불가
        r = recompute_coherence("TSTC", entry=100, target=110, as_of=as_of)
        assert r["sigma"] is None
        assert "coherent_horizon_days" not in r  # 정합 산출 생략


@pytest.mark.django_db
class TestSuggestAPI:
    def _client(self, owner):
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(user=owner)
        return c

    def test_recompute_params_add_coherence(self, owner, stock, prices):
        prices(140)
        r = self._client(owner).get(
            "/api/v1/monitor/scenario-suggest/",
            {"symbol": "TSTC", "entry": "100", "target": "110", "stop": "90"},
        )
        assert r.status_code == 200
        assert "coherence" in r.data
        assert r.data["coherence"]["rr"] == 1.0

    def test_no_recompute_params_no_coherence_key(self, owner, stock, prices):
        prices(140)
        r = self._client(owner).get("/api/v1/monitor/scenario-suggest/", {"symbol": "TSTC"})
        assert r.status_code == 200
        assert "coherence" not in r.data  # entry 없으면 재계산 없음
