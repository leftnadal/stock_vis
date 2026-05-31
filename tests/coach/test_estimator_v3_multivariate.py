"""Slice 13 Step 0a #51 — estimator_v3 다변량 OLS fit 단위 테스트.

신모델 검증:
  - tokens = a + b × chars (단변량 ratio → OLS 교체)
  - (EP, model) → EP → GLOBAL fit lookup 우선순위
  - 경계 입력 (chars=0/None, entry_point 미지정, 미등록 model)
  - 시그니처 하위호환 보장
"""

from __future__ import annotations

import pytest

from apps.portfolio.measure import estimator_v3 as e3


def test_global_fit_constants_loaded():
    """GLOBAL_OUTPUT_FIT은 (a, b) 튜플로 정의되어야 한다."""
    assert isinstance(e3.GLOBAL_OUTPUT_FIT, tuple)
    assert len(e3.GLOBAL_OUTPUT_FIT) == 2
    a, b = e3.GLOBAL_OUTPUT_FIT
    assert isinstance(a, (int, float))
    assert isinstance(b, (int, float))


def test_entry_point_fits_8_groups_registered():
    """ENTRY_POINT_OUTPUT_FITS에 8개 진입점 모두 등록."""
    expected = {"e1", "e2", "e3", "e3_portfolio", "e4_conversation", "e5", "e6", "rationale"}
    assert set(e3.ENTRY_POINT_OUTPUT_FITS) == expected


def test_global_fallback_chars_zero_or_none_returns_zero():
    """chars None/0/음수 → 0."""
    assert e3.estimate_output_tokens(None) == 0
    assert e3.estimate_output_tokens(0) == 0
    assert e3.estimate_output_tokens(-100) == 0


def test_unknown_entry_point_uses_global_fit():
    """미등록 EP → GLOBAL_OUTPUT_FIT 사용."""
    a, b = e3.GLOBAL_OUTPUT_FIT
    expected = max(0, int(a + b * 500))
    assert e3.estimate_output_tokens(500, entry_point="unknown_ep") == expected
    assert e3.estimate_output_tokens(500, entry_point=None) == expected


def test_ep_model_fit_takes_precedence_over_ep_only():
    """(EP, model) 셀이 등록되어 있으면 EP-only fit보다 우선."""
    # e4_conversation × claude-haiku-4-5 → cell fit 존재
    cell = e3.ENTRY_POINT_MODEL_OUTPUT_FITS.get(("e4_conversation", "claude-haiku-4-5"))
    assert cell is not None
    a, b = cell
    expected = max(0, int(a + b * 1000))
    result = e3.estimate_output_tokens(
        1000, entry_point="e4_conversation", model="claude-haiku-4-5"
    )
    assert result == expected


def test_ep_only_fallback_when_cell_missing():
    """(EP, model) 셀 없음 → EP-only fit fallback.

    rationale은 sonnet-4-5만 셀이 있고 haiku는 없음. haiku 요청 시 EP-only로 fallback.
    """
    # rationale에 haiku 셀이 없는지 확인
    assert ("rationale", "claude-haiku-4-5") not in e3.ENTRY_POINT_MODEL_OUTPUT_FITS
    a, b = e3.ENTRY_POINT_OUTPUT_FITS["rationale"]
    expected = max(0, int(a + b * 500))
    assert (
        e3.estimate_output_tokens(500, entry_point="rationale", model="claude-haiku-4-5")
        == expected
    )


def test_model_short_normalizes_versioned_id():
    """모델 ID에서 version suffix 제거: 'claude-haiku-4-5-20251001' → 'claude-haiku-4-5'."""
    assert e3._model_short("claude-haiku-4-5") == "claude-haiku-4-5"
    assert e3._model_short("claude-haiku-4-5-20251001") == "claude-haiku-4-5"
    assert e3._model_short("claude-sonnet-4-5") == "claude-sonnet-4-5"


def test_estimate_never_returns_negative():
    """OLS intercept가 음수여도 결과는 0으로 clip — 안전 보증."""
    # e2 fit: a=-32.94, b=0.9057. chars=1 → -32.94 + 0.9057 = -32 → clip 0
    result = e3.estimate_output_tokens(1, entry_point="e2")
    assert result >= 0


def test_legacy_ratio_constants_preserved():
    """구모델 ratio 상수는 backtest baseline 비교용으로 보존되어야 함."""
    assert hasattr(e3, "ENTRY_POINT_OUTPUT_RATIOS")
    assert hasattr(e3, "GLOBAL_OUTPUT_RATIO")
    assert "e1" in e3.ENTRY_POINT_OUTPUT_RATIOS
    assert e3.GLOBAL_OUTPUT_RATIO == pytest.approx(0.7584)


def test_signature_backward_compatible():
    """estimate_output_tokens 시그니처: (chars, entry_point, model) — 변경 없음."""
    import inspect
    sig = inspect.signature(e3.estimate_output_tokens)
    params = list(sig.parameters.keys())
    assert params == ["expected_output_chars", "entry_point", "model"]
    assert sig.parameters["expected_output_chars"].default is None
    assert sig.parameters["entry_point"].default is None
    assert sig.parameters["model"].default == e3.DEFAULT_MODEL
