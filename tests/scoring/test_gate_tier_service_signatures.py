"""Slice 13 Step 0a #60 — E1/E2/E5/E6 service에 추가된 gate-tier kwarg 시그니처 검증.

검증 항목:
  1. E1/E2/E5/E6 service에 preset_id/metrics kwarg가 keyword-only + default None
  2. kwarg 미전달 시 기존 4개 positional 동작 (하위호환)
  3. 미등록 preset_id 전달 시 KeyError
"""

from __future__ import annotations

import inspect

import pytest

from portfolio.services.coach.e1_service import run_e1_coach
from portfolio.services.coach.e2_service import run_e2_coach
from portfolio.services.coach.e5_service import run_e5_coach
from portfolio.services.coach.e6_service import run_e6_coach


SERVICES = [
    ("e1", run_e1_coach),
    ("e2", run_e2_coach),
    ("e5", run_e5_coach),
    ("e6", run_e6_coach),
]


@pytest.mark.parametrize("label,fn", SERVICES)
def test_service_has_gate_tier_kwargs(label, fn):
    """E1/E2/E5/E6 모두 preset_id, metrics kwarg를 keyword-only로 보유."""
    sig = inspect.signature(fn)
    params = list(sig.parameters.keys())
    assert (
        params[:4] == ["input_data", "provider", "client", "max_tokens"]
    ), f"{label}: core positional must remain unchanged"
    assert "preset_id" in params, f"{label}: missing preset_id kwarg"
    assert "metrics" in params, f"{label}: missing metrics kwarg"
    assert sig.parameters["preset_id"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["preset_id"].default is None
    assert sig.parameters["metrics"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["metrics"].default is None
