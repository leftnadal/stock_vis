"""MP2-TREND Slice 3(R1) — 국면 재료 판정-거리 소형 다중.

룰-구동 7지표 raw 시계열 + rules.yaml 도출 컷 + 판정거리(비교 방향 존중). z-score 아님.
조회-시 파생(모델 저장 0, 마이그레이션 0). 컷 하드코딩 0 — rules.yaml 단일소스.
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
from apps.market_pulse.regime.classifier import load_rules
from apps.market_pulse.regime.component_cuts import (
    TARGET_INDICATORS,
    build_components,
    extract_indicator_cuts,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="t3", email="t3@e.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _regime_url():
    return reverse("marketpulse_api_v2:card-detail", kwargs={"card_id": "regime"})


def _mk_regime(d, regime, inputs, previous_regime=""):
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
        inputs=inputs,
    )


class TestCutExtraction:
    def test_cuts_match_rules_yaml_exactly(self):
        # 컷 도출 정확성 — rules.yaml 실측값과 지표별 cuts 전량 대조(하드코딩 0).
        cuts = extract_indicator_cuts(load_rules())
        # vix 4컷(20/25/30/40), value 오름차순
        vix = [(c["value"], c["regime"], c["op"]) for c in cuts["vix"]]
        assert vix == [
            (20, "LATE_BULL", ">"),
            (25, "TRANSITION", ">="),
            (30, "BEAR_CONTRACTION", ">="),
            (40, "CRISIS", ">="),
        ]
        # drawdown_pct 2컷(-20/-10)
        dd = [(c["value"], c["regime"], c["op"]) for c in cuts["drawdown_pct"]]
        assert dd == [(-20, "CRISIS", "<="), (-10, "BEAR_CONTRACTION", "<=")]
        # move 단일 컷
        assert [(c["value"], c["regime"]) for c in cuts["move"]] == [(150, "CRISIS")]
        # nfci 3컷, hy_oas 4컷, t10y2y 2컷, t10y3m 1컷 — 전 7지표 커버
        assert len(cuts["nfci"]) == 3
        assert len(cuts["hy_oas_pct"]) == 4
        assert len(cuts["t10y2y_pct"]) == 2
        assert len(cuts["t10y3m_pct"]) == 1
        # 7지표 전부 도출됨
        for key in TARGET_INDICATORS:
            assert key in cuts


class TestNearestCutDistance:
    def _components(self, latest_inputs):
        base = date_cls(2026, 6, 1)
        hist = [{"date": base, "regime": "BULL_EXPANSION", "inputs": latest_inputs}]
        return {c["key"]: c for c in build_components(hist, load_rules())}

    def test_gt_direction_vix(self):
        # vix=22.4 → 다음 미통과 컷 = 25(TRANSITION), 거리 +2.6. 20은 통과(crossed).
        comp = self._components({"vix": 22.4})["vix"]
        assert comp["nearest_cut_distance"]["cut"] == 25
        assert comp["nearest_cut_distance"]["distance"] == pytest.approx(2.6)
        assert comp["nearest_cut_distance"]["regime"] == "TRANSITION"
        crossed_vals = [c["value"] for c in comp["crossed_cuts"]]
        assert crossed_vals == [20]  # vix>20 통과

    def test_lt_direction_drawdown(self):
        # drawdown_pct=-7 → 다음 미통과 컷 = -10(BEAR, <=), 내려가야 통과 → 거리 3.
        comp = self._components({"drawdown_pct": -7.0})["drawdown_pct"]
        assert comp["nearest_cut_distance"]["cut"] == -10
        assert comp["nearest_cut_distance"]["distance"] == pytest.approx(3.0)
        assert comp["crossed_cuts"] == []  # 아무 컷도 통과 안 함

    def test_lt_crossed_state(self):
        # drawdown_pct=-25 → -20·-10 둘 다 통과(<=). nearest None(미통과 없음).
        comp = self._components({"drawdown_pct": -25.0})["drawdown_pct"]
        crossed_vals = sorted(c["value"] for c in comp["crossed_cuts"])
        assert crossed_vals == [-20, -10]
        assert comp["nearest_cut_distance"] is None

    def test_missing_indicator_null(self):
        # inputs에 키 없음 → current null, nearest null, crossed 빈(경계 graceful).
        comp = self._components({"vix": 15.0})["move"]  # move 키 없음
        assert comp["current"] is None
        assert comp["nearest_cut_distance"] is None
        assert comp["crossed_cuts"] == []


@pytest.mark.django_db
class TestRegimeComponentsPayload:
    def test_components_served_with_series(self, auth_client):
        base = date_cls(2026, 6, 1)
        for i in range(5):
            _mk_regime(
                base + timedelta(days=i),
                RegimeSnapshot.Regime.LATE_BULL,
                inputs={"vix": 21.0 + i, "move": 100.0, "hy_oas_pct": 2.6},
            )
        data = auth_client.get(_regime_url()).json()["data"]
        comps = {c["key"]: c for c in data["components"]}
        assert set(comps) == set(TARGET_INDICATORS)  # 7지표
        vix = comps["vix"]
        assert len(vix["series"]) == 5  # 일별 1점(5일)
        assert vix["series"][-1]["value"] == pytest.approx(25.0)  # 최신
        assert vix["unit"] == ""
        # 컷은 payload에 그대로(FE 하드코딩 없이 소비)
        assert [c["value"] for c in vix["cuts"]] == [20, 25, 30, 40]

    def test_daily_sampling_one_row_per_date(self, auth_client):
        # RegimeSnapshot unique_together=(date,) — update_or_create로 하루 1행.
        #   같은 날 재저장 시 갱신(다중 스냅샷 → 대표 1점) 확인.
        d = date_cls(2026, 6, 10)
        snap = _mk_regime(d, RegimeSnapshot.Regime.LATE_BULL, inputs={"vix": 21.0})
        snap.inputs = {"vix": 28.0}  # intraday 갱신 시뮬(같은 날)
        snap.save()
        data = auth_client.get(_regime_url()).json()["data"]
        vix = {c["key"]: c for c in data["components"]}["vix"]
        assert len(vix["series"]) == 1  # 하루 1점
        assert vix["series"][0]["value"] == pytest.approx(28.0)  # 갱신 반영

    def test_contract_regression_additive_only(self, auth_client):
        # 기존 regime 필드 불변 — components만 additive.
        _mk_regime(date_cls(2026, 6, 1), RegimeSnapshot.Regime.BULL_EXPANSION, inputs={})
        data = auth_client.get(_regime_url()).json()["data"]
        for k in ("regime", "regime_history_30d", "transition_dates", "inputs", "next_stage"):
            assert k in data  # 기존 계약 불변
        assert "components" in data  # additive
        assert isinstance(data["components"], list)
