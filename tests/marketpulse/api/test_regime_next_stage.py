"""MP-UX-S3b — 다음 단계까지 margin 산출 테스트.

compute_next_stage_margin 단위(임계 단일소스 = rules.yaml 읽기) + cards detail 통합.
임계 하드카피 0 — rules.yaml 값으로 계산.
"""
from __future__ import annotations

from datetime import date as date_cls

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.regime.next_stage import compute_next_stage_margin

User = get_user_model()


# ── 단위: compute_next_stage_margin (DB 불필요 — rules.yaml 읽기만) ──

class TestComputeNextStageMargin:
    def test_late_bull_next_is_transition(self):
        # LATE_BULL(idx3) → 인접 상위(더 심각) = TRANSITION(idx2)
        out = compute_next_stage_margin("LATE_BULL", {"vix": 22.3, "hy_oas_pct": 2.8})
        assert out["next_stage"] == "TRANSITION"
        by_ind = {m["indicator"]: m for m in out["margins"]}
        # vix>=25 → 25-22.3=2.7 / hy_oas_pct>=3.5 → 3.5-2.8=0.7 (rules.yaml 값)
        assert by_ind["vix"]["to_threshold"] == pytest.approx(2.7)
        assert by_ind["hy_oas_pct"]["to_threshold"] == pytest.approx(0.7)
        # 미제공 지표(nfci/t10y2y/t10y3m)는 actual None → to_threshold None (graceful)
        assert by_ind["nfci"]["actual"] is None
        assert by_ind["nfci"]["to_threshold"] is None
        # closest = 가장 가까운 미발동 = hy_oas_pct(0.7). 헬퍼는 'closest' 키 반환
        assert out["closest"]["indicator"] == "hy_oas_pct"

    def test_crisis_has_no_higher_stage(self):
        out = compute_next_stage_margin("CRISIS", {"vix": 50})
        assert out["next_stage"] is None
        assert out["margins"] == []
        assert out["closest"] is None

    def test_bull_expansion_next_is_late_bull(self):
        out = compute_next_stage_margin("BULL_EXPANSION", {"vix": 18})
        assert out["next_stage"] == "LATE_BULL"
        inds = {m["indicator"] for m in out["margins"]}
        assert "vix" in inds  # LATE_BULL: vix>20 / hy_oas_pct>2.5 / t10y2y_pct<0.3

    def test_boundary_at_threshold_not_pending(self):
        # vix 정확히 25 → to_threshold 0 → 미발동 아님(>0 거짓) → closest 제외
        out = compute_next_stage_margin("LATE_BULL", {"vix": 25.0})
        by_ind = {m["indicator"]: m for m in out["margins"]}
        assert by_ind["vix"]["to_threshold"] == pytest.approx(0.0)
        assert out["closest"] is None  # 유일 제공 지표가 경계값 → pending 없음

    def test_empty_inputs_graceful(self):
        out = compute_next_stage_margin("LATE_BULL", None)
        assert out["next_stage"] == "TRANSITION"
        assert all(m["actual"] is None for m in out["margins"])
        assert out["closest"] is None


# ── 통합: cards detail payload ──

@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="ns", email="ns@e.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class TestRegimeDetailMargin:
    def test_payload_has_next_stage_and_margins(self, auth_client):
        RegimeSnapshot.objects.create(
            date=date_cls(2026, 6, 15), snapshot_time=date_cls(2026, 6, 15),
            regime=RegimeSnapshot.Regime.LATE_BULL,
            status=RegimeSnapshot.Status.OK, coverage=0.9,
            headline="h", fired_rules=[], previous_regime="LATE_BULL",
            hysteresis_streak=5, inputs={"vix": 22.3, "hy_oas_pct": 2.8},
        )
        body = auth_client.get(
            reverse("marketpulse_api_v2:card-detail", kwargs={"card_id": "regime"})
        ).json()["data"]
        assert body["next_stage"] == "TRANSITION"
        assert len(body["margins"]) > 0
        assert body["next_stage_closest"]["indicator"] == "hy_oas_pct"
