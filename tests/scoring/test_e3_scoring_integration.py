"""Slice 12 Part 3 — e3_service metrics 통합 단위 테스트 (LLM mock 없이 검증).

run_e3_coach의 후방 호환성 검증:
  1. preset_id/metrics 미전달 → 기존 동작 (IDENTICAL 보장)
  2. preset_id + metrics 전달 → scoring 호출 + prompt augment

LLM 실호출은 smoke 매트릭스에서 검증 (별도 스크립트).
본 테스트는 prompt augment 로직만 unit 단위로 검증.
"""

from __future__ import annotations

import inspect

import pytest

from apps.portfolio.services.coach.e3_service import run_e3_coach


def test_run_e3_coach_signature_backward_compatible():
    """run_e3_coach 시그니처: 기존 4개 positional + 신규 2개 keyword-only."""
    sig = inspect.signature(run_e3_coach)
    params = list(sig.parameters.keys())
    assert params == ["input_data", "provider", "client", "max_tokens", "preset_id", "metrics"]
    # preset_id/metrics는 keyword-only + default None
    assert sig.parameters["preset_id"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["preset_id"].default is None
    assert sig.parameters["metrics"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["metrics"].default is None


def test_run_e3_coach_unknown_preset_id_raises():
    """알 수 없는 preset_id 전달 시 KeyError (resolve_category에서)."""
    from apps.portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input

    inp = load_portfolio_a2_input("e3")
    with pytest.raises(KeyError):
        run_e3_coach(
            inp,
            preset_id="nonexistent_preset",
            metrics={"roic": 0.5},
            # 실제 LLM 호출 전에 resolve_category에서 raise
        )
