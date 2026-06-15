"""MP-UX-S3a — _regime_detail regime_history_30d 데이터원 테스트.

국면 타임라인 데이터원(렌더 아님). breadth/concentration history_30d 패턴 재사용 검증.
"""
from __future__ import annotations

from datetime import date as date_cls
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.market_pulse.models.regime import RegimeSnapshot

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="rh", email="rh@e.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _mk_snapshot(d, regime):
    return RegimeSnapshot.objects.create(
        date=d, snapshot_time=d, regime=regime,
        status=RegimeSnapshot.Status.OK, coverage=0.9,
        headline="h", fired_rules=[], previous_regime="", hysteresis_streak=1,
    )


def _url():
    return reverse("marketpulse_api_v2:card-detail", kwargs={"card_id": "regime"})


class TestRegimeHistory30d:
    def test_history_shape_and_order(self, auth_client):
        base = date_cls(2026, 6, 15)
        stages = [
            RegimeSnapshot.Regime.LATE_BULL,
            RegimeSnapshot.Regime.TRANSITION,
            RegimeSnapshot.Regime.BULL_EXPANSION,
        ]
        for i, st in enumerate(stages):
            _mk_snapshot(base - timedelta(days=i), st)

        body = auth_client.get(_url()).json()["data"]
        hist = body["regime_history_30d"]
        assert len(hist) == 3
        # 오름차순(과거→현재) + {date, stage} 형태
        assert [h["date"] for h in hist] == [
            (base - timedelta(days=2)).isoformat(),
            (base - timedelta(days=1)).isoformat(),
            base.isoformat(),
        ]
        assert {h["stage"] for h in hist} == {
            "LATE_BULL", "TRANSITION", "BULL_EXPANSION",
        }
        # stage는 raw enum (FE가 regime.* 키로 번역) — 한글 아님. 최신(base)=stages[0]=LATE_BULL
        assert hist[-1]["stage"] == "LATE_BULL"
        assert hist[0]["stage"] == "BULL_EXPANSION"  # 최古(base-2)=stages[2]

    def test_caps_at_30(self, auth_client):
        base = date_cls(2026, 6, 15)
        for i in range(35):
            _mk_snapshot(base - timedelta(days=i), RegimeSnapshot.Regime.LATE_BULL)
        hist = auth_client.get(_url()).json()["data"]["regime_history_30d"]
        assert len(hist) == 30

    def test_single_snapshot_graceful(self, auth_client):
        _mk_snapshot(date_cls(2026, 6, 15), RegimeSnapshot.Regime.CRISIS)
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is True
        assert len(body["regime_history_30d"]) == 1
        assert body["regime_history_30d"][0]["stage"] == "CRISIS"

    def test_no_snapshot_unavailable(self, auth_client):
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is False
        assert "regime_history_30d" not in body
