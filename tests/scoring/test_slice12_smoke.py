"""Slice 12 Part 3 — Smoke matrix 결과 검증 (LLM 호출 없음, JSON 후검증).

`docs/portfolio/coach/slice12/part3_smoke_results.json`을 읽어 KPI 자동 체크.
LLM 호출은 별도 스크립트(`scripts/slice12_part3_smoke.py`)에서 사전 실행.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RESULTS_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "portfolio"
    / "coach"
    / "slice12"
    / "part3_smoke_results.json"
)


@pytest.fixture(scope="module")
def smoke_data():
    if not RESULTS_PATH.exists():
        pytest.skip("smoke results 미생성 (matrix 미실행)")
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


def test_15_cases_executed(smoke_data):
    """KPI 1: 15 case 전부 실행."""
    assert smoke_data["summary"]["n_cases_executed"] == 15


def test_schema_fitting_all_pass(smoke_data):
    """KPI 2: 15/15 schema fitting PASS (Slice 12 Step 0a #58 효과)."""
    assert smoke_data["summary"]["n_fitting_pass"] == 15


def test_total_cost_under_part3_cap(smoke_data):
    """KPI 3: 총 비용 < $0.20 (Part 3 단독 cap)."""
    assert smoke_data["summary"]["total_cost_usd"] < 0.20


def test_all_cases_have_commentary(smoke_data):
    """KPI 4: 모든 case의 commentary 비어 있지 않음."""
    for c in smoke_data["cases"]:
        if c["schema_fitting_pass"]:
            assert len(c["commentary"]) > 0, f"empty commentary: {c['fixture']}"


def test_gate_triggered_count_matches_design(smoke_data):
    """KPI 5: gate 발동 실제 = 6건 또는 그 이상 (income×2 + factor×2 + 빈 dict 3건).

    의도된 gate (income/factor_gate, income_edge, factor_edge): 4건
    추가 자연 0 (value/growth/special_edge 빈 dict): 3건
    총 7건 gate_triggered 예상 (smoke 판정 휴리스틱).
    """
    n_gate = smoke_data["summary"]["n_gate_triggered_actual"]
    assert n_gate >= 6, f"gate 발동 너무 적음: {n_gate}"


def test_designed_gate_cases_all_triggered(smoke_data):
    """KPI 6: 의도된 gate 4건 (income_edge, income_gate, factor_edge, factor_gate) 모두 발동."""
    designed_gate_fixtures = {
        "income_edge", "income_gate", "factor_edge", "factor_gate",
    }
    triggered = {c["fixture"] for c in smoke_data["cases"] if c["gate_triggered"]}
    missing = designed_gate_fixtures - triggered
    assert not missing, f"의도된 gate 미발동: {missing}"


def test_all_provider_haiku(smoke_data):
    """KPI 7: 모든 호출 haiku (글쓰기 가설 7/7 정착)."""
    for c in smoke_data["cases"]:
        if c["schema_fitting_pass"]:
            # provider는 "anthropic" 또는 "haiku" 라벨 — model에 "haiku" 포함
            assert "haiku" in c.get("model", "").lower(), (
                f"non-haiku model: {c['fixture']} = {c.get('model')}"
            )
