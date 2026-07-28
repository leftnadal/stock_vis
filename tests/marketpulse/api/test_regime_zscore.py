"""MP2-TREND S4 — regime/zscore 전용 엔드포인트 회귀.

계약: baseline(소급 모집단)·z serve-time·다운샘플·null 전파·라이브/소급 이음새·
  마커 미노출·소급 부재 시 빈 응답.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.market_pulse.management.commands.backfill_v2_regime_vectors import BACKFILL_MARK
from apps.market_pulse.models.regime import RegimeSnapshot

User = get_user_model()

pytestmark = [pytest.mark.django_db]

# 7 룰-구동 지표 벤치값(std>0 위해 vix만 흔들고 나머지는 고정 → nfci 등은 σ=0=insufficient 검증도 겸)
_BASE_INPUTS = {
    "vix": 15.0, "move": 90.0, "hy_oas_pct": 3.0, "nfci": -0.4,
    "t10y2y_pct": 0.5, "t10y3m_pct": -0.3, "drawdown_pct": -2.0,
}


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    RegimeSnapshot.objects.all().delete()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="z", email="z@e.com", password="pw")
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _weekdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _mk(d, *, synth, inputs, cov=1.0):
    RegimeSnapshot.objects.create(
        date=d, snapshot_time=d, regime=RegimeSnapshot.Regime.TRANSITION,
        status=RegimeSnapshot.Status.OK, coverage=cov, headline="h",
        inputs=inputs,
        fired_rules=[], previous_regime="", hysteresis_streak=1,
        summary=BACKFILL_MARK if synth else "",
    )


def _seed(n_synth=40, n_live=4, vary_vix=True, anomaly=False):
    days = _weekdays(date(2023, 7, 10), n_synth)
    for i, d in enumerate(days):
        inp = dict(_BASE_INPUTS)
        if vary_vix:
            inp["vix"] = 15.0 + (i % 7)  # σ>0
        _mk(d, synth=True, inputs=inp)
    if anomaly:  # 마지막 소급행에 극단 vix
        last = RegimeSnapshot.objects.filter(summary=BACKFILL_MARK).order_by("-date").first()
        last.inputs = {**dict(_BASE_INPUTS), "vix": 999.0}
        last.save()
    live_days = _weekdays(date(2026, 4, 27), n_live)
    for d in live_days:
        _mk(d, synth=False, inputs=dict(_BASE_INPUTS))
    return days


def _url():
    return reverse("marketpulse_api_v2:regime-zscore")


class TestRegimeZScore:
    def test_empty_when_no_synth(self, auth_client):
        # 소급 모집단 없음(라이브만)
        for d in _weekdays(date(2026, 4, 27), 3):
            _mk(d, synth=False, inputs=dict(_BASE_INPUTS))
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is False
        assert body["components"] == []

    def test_schema_and_baseline(self, auth_client):
        _seed()
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is True
        keys = {c["key"] for c in body["components"]}
        assert keys == {"vix", "move", "hy_oas_pct", "nfci", "t10y2y_pct", "t10y3m_pct", "drawdown_pct"}
        vix = next(c for c in body["components"] if c["key"] == "vix")
        assert vix["insufficient"] is False
        assert vix["baseline"]["n"] >= 30
        assert isinstance(vix["series"], list) and vix["series"][0]["z"] is not None
        # 고정값 지표(move 등)는 σ=0 → insufficient + z null
        move = next(c for c in body["components"] if c["key"] == "move")
        assert move["insufficient"] is True
        assert all(p["z"] is None for p in move["series"])
        # meta
        assert body["meta"]["live_start"] == "2026-04-27"
        assert body["meta"]["low_confidence_until"]  # 20영업일째

    def test_z_null_on_missing_component(self, auth_client):
        _seed()
        # 한 소급행의 vix 결측 → 그 날 z null
        row = RegimeSnapshot.objects.filter(summary=BACKFILL_MARK).order_by("date")[5]
        row.inputs = {k: v for k, v in _BASE_INPUTS.items() if k != "vix"}
        row.save()
        cache.clear()
        body = auth_client.get(_url()).json()["data"]
        vix = next(c for c in body["components"] if c["key"] == "vix")
        nulls = [p for p in vix["series"] if p["z"] is None]
        assert len(nulls) >= 1

    def test_live_and_synth_seam(self, auth_client):
        _seed()
        body = auth_client.get(_url()).json()["data"]
        vix = next(c for c in body["components"] if c["key"] == "vix")
        dates = {p["date"] for p in vix["series"]}
        assert any(dt.startswith("2023-07") for dt in dates)  # 소급
        assert "2026-04-27" in dates  # 라이브

    def test_marker_not_exposed(self, auth_client):
        _seed()
        raw = auth_client.get(_url()).content.decode()
        assert BACKFILL_MARK not in raw
        assert "summary" not in json.loads(raw)["data"]["components"][0]

    def test_insufficient_when_below_30(self, auth_client):
        _seed(n_synth=20)  # <30
        body = auth_client.get(_url()).json()["data"]
        vix = next(c for c in body["components"] if c["key"] == "vix")
        assert vix["insufficient"] is True
        assert all(p["z"] is None for p in vix["series"])

    def test_downsample_reduces_older(self, auth_client):
        days = _seed(n_synth=140, n_live=0)  # >90 → 다운샘플 발동
        body = auth_client.get(_url()).json()["data"]
        vix = next(c for c in body["components"] if c["key"] == "vix")
        # 전체 140 행 > 반환 포인트 수(오래된 구간 주간 축소)
        assert len(vix["series"]) < 140
        # 최근 90 영업일은 일간 유지 → 꼬리 90 날짜가 원본 최근 90과 일치
        tail = [p["date"] for p in vix["series"]][-90:]
        assert tail == [d.isoformat() for d in days[-90:]]
