"""MP2-TREND Slice 2 — breadth MA20 기준선 파생 + regime 전환일 파생 테스트.

조회-시 파생(모델 저장 0, 마이그레이션 0). additive만 — 기존 필드 회귀 없음(E7).
- breadth: ad_line_ma20(per-date, <20일 null) + ma_deviation_streak_days(latest)
- regime: transition_dates(previous_regime≠regime 파생)
"""
from __future__ import annotations

from datetime import date as date_cls
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.models.snapshot import BreadthSnapshot

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="t2", email="t2@e.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _breadth_url():
    return reverse("marketpulse_api_v2:card-detail", kwargs={"card_id": "breadth"})


def _regime_url():
    return reverse("marketpulse_api_v2:card-detail", kwargs={"card_id": "regime"})


def _mk_breadth(d, ad_line):
    return BreadthSnapshot.objects.create(
        date=d,
        snapshot_time=timezone.now(),
        universe="SPY",
        advance_count=250,
        decline_count=250,
        ad_line=ad_line,
        ad_line_change=0,
    )


def _mk_regime(d, regime, previous_regime=""):
    return RegimeSnapshot.objects.create(
        date=d,
        snapshot_time=timezone.now(),
        regime=regime,
        previous_regime=previous_regime,
        status=RegimeSnapshot.Status.OK,
        coverage=0.9,
        headline="h",
        fired_rules=[],
        hysteresis_streak=1,
    )


@pytest.mark.django_db
class TestBreadthMA20:
    def test_ma20_accuracy_and_null_boundary(self, auth_client):
        # 25일: ad_line = 100, 200, 300, ... 2500 (일 100씩 증가)
        base = date_cls(2026, 6, 1)
        for i in range(25):
            _mk_breadth(base + timedelta(days=i), ad_line=(i + 1) * 100)
        res = auth_client.get(_breadth_url())
        assert res.status_code == 200
        hist = res.json()["data"]["history_30d"]
        assert len(hist) == 25  # 25일 전부 표시(30 미만)
        # 경계: 앞 19일(인덱스 0~18)은 20일 미만 → null
        for i in range(19):
            assert hist[i]["ad_line_ma20"] is None, f"idx {i} should be null"
        # 20번째 이후는 MA20 존재. idx19 = 평균(ad_line[0..19]) = (100+..+2000)/20 = 1050
        assert hist[19]["ad_line_ma20"] == pytest.approx(1050.0)
        # 최신(idx24) = 평균(ad_line[5..24]) = (600+..+2500)/20 = 1550
        assert hist[24]["ad_line_ma20"] == pytest.approx(1550.0)

    def test_deviation_streak(self, auth_client):
        # 20일 평탄(ad_line=1000) → 기준선 1000. 이후 5일 하락(950 4일 + 마지막 상승).
        base = date_cls(2026, 6, 1)
        for i in range(20):
            _mk_breadth(base + timedelta(days=i), ad_line=1000)
        # idx20~23: 기준선 아래(이탈), idx24: 기준선 위로 복귀
        for i, ad in zip(range(20, 24), [900, 880, 870, 860]):
            _mk_breadth(base + timedelta(days=i), ad_line=ad)
        _mk_breadth(base + timedelta(days=24), ad_line=2000)  # 최신 복귀
        res = auth_client.get(_breadth_url())
        # 최신일(2000)은 기준선 위 → streak 0
        assert res.json()["data"]["ma_deviation_streak_days"] == 0

    def test_deviation_streak_active(self, auth_client):
        # 20일 평탄(1000) 후 3일 연속 이탈로 종료
        base = date_cls(2026, 6, 1)
        for i in range(20):
            _mk_breadth(base + timedelta(days=i), ad_line=1000)
        for i, ad in zip(range(20, 23), [950, 940, 930]):
            _mk_breadth(base + timedelta(days=i), ad_line=ad)
        res = auth_client.get(_breadth_url())
        assert res.json()["data"]["ma_deviation_streak_days"] == 3

    def test_breadth_contract_regression_additive_only(self, auth_client):
        # E7: 기존 history_30d 필드 불변 — additive(ad_line_ma20)만 추가.
        base = date_cls(2026, 6, 1)
        for i in range(5):
            _mk_breadth(base + timedelta(days=i), ad_line=(i + 1) * 100)
        data = auth_client.get(_breadth_url()).json()["data"]
        assert data["available"] is True
        point = data["history_30d"][0]
        # 기존 필드 전부 존재
        for k in ("date", "advance", "decline", "ad_line", "ad_line_change"):
            assert k in point
        # additive 필드
        assert "ad_line_ma20" in point
        assert "ma_deviation_streak_days" in data
        # 5일뿐 → 전부 MA null, streak 0(경계 graceful)
        assert point["ad_line_ma20"] is None
        assert data["ma_deviation_streak_days"] == 0


@pytest.mark.django_db
class TestRegimeTransitionDates:
    def test_transition_dates_derivation(self, auth_client):
        base = date_cls(2026, 6, 1)
        B = RegimeSnapshot.Regime
        # 초기 → 전환 없음(previous 빈값), 2일차 전환, 3일차 유지, 4일차 전환
        _mk_regime(base, B.BULL_EXPANSION, previous_regime="")
        _mk_regime(base + timedelta(days=1), B.LATE_BULL, previous_regime=B.BULL_EXPANSION)
        _mk_regime(base + timedelta(days=2), B.LATE_BULL, previous_regime=B.LATE_BULL)
        _mk_regime(base + timedelta(days=3), B.TRANSITION, previous_regime=B.LATE_BULL)
        data = auth_client.get(_regime_url()).json()["data"]
        assert data["transition_dates"] == [
            (base + timedelta(days=1)).isoformat(),
            (base + timedelta(days=3)).isoformat(),
        ]

    def test_regime_contract_regression_additive_only(self, auth_client):
        # E7: regime_history_30d {date, stage} 불변 — transition_dates만 additive.
        base = date_cls(2026, 6, 1)
        B = RegimeSnapshot.Regime
        _mk_regime(base, B.BULL_EXPANSION, previous_regime="")
        _mk_regime(base + timedelta(days=1), B.LATE_BULL, previous_regime=B.BULL_EXPANSION)
        data = auth_client.get(_regime_url()).json()["data"]
        hist = data["regime_history_30d"]
        assert set(hist[0].keys()) == {"date", "stage"}  # 기존 형태 불변
        assert "transition_dates" in data  # additive
        assert isinstance(data["transition_dates"], list)
