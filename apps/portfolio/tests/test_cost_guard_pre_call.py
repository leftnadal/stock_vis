"""Slice 13 Step 0b #62 — estimator → CostGuard 사전 추정 단위 테스트.

검증 항목:
  - estimate_call_cost 비용 산정 (input/output 토큰 × 단가)
  - PRE_CALL_SAFETY_BUFFER 1.25 적용 (check_pre_call_budget 반환)
  - non-blocking: 예산 초과 시 WARNING만 + 호출은 진행 (raise 없음)
  - 기존 CostGuard 동작 불변 (cumulative_usd/slice_usd/reset/budget guard)
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.portfolio.llm import cost_guard as cg
from apps.portfolio.measure import estimator_v3 as e3


@pytest.fixture(autouse=True)
def _reset():
    """매 테스트 깨끗한 상태 + estimator cache 격리.

    cumulative_usd는 reset_slice가 보존하므로 직접 0으로 초기화 필요.
    """
    guard = cg.CostGuard.get_instance()
    guard.reset_slice("test_slice", max_calls=50)
    guard.cumulative_usd = (
        0.0  # 테스트 격리 — Slice 9 #43 cumulative는 reset_slice가 보존
    )
    e3.reset_cache()
    # 슬라이스 ④ #3: 구 e3.set_client 주입 → 코어 count_tokens가 생성하는 anthropic.Anthropic 패치.
    mock_client = MagicMock(
        messages=MagicMock(
            count_tokens=MagicMock(return_value=SimpleNamespace(input_tokens=100))
        )
    )
    with patch("anthropic.Anthropic", return_value=mock_client), patch(
        "packages.shared.llm.providers.anthropic._resolve_api_key",
        return_value="fake-key",
    ):
        yield
    guard.reset_slice("test_slice", max_calls=50)
    guard.cumulative_usd = 0.0
    e3.reset_cache()


# ============================================================
# estimate_call_cost — 비용 산정
# ============================================================


def test_estimate_call_cost_haiku_basic():
    """haiku 모델 단가로 비용 산정.

    input=100 tokens × $0.80/1M = $0.00008
    output=estimate(chars=200, e1, haiku) × $4.0/1M
    """
    guard = cg.CostGuard.get_instance()
    cost = guard.estimate_call_cost(
        input_text="dummy",
        expected_output_chars=200,
        entry_point="e1",
        model="claude-haiku-4-5",
    )
    output_tokens = e3.estimate_output_tokens(
        200, entry_point="e1", model="claude-haiku-4-5"
    )
    expected = 100 / 1_000_000 * 0.80 + output_tokens / 1_000_000 * 4.0
    assert cost == pytest.approx(expected, rel=1e-9)


def test_estimate_call_cost_sonnet_pricing():
    """sonnet 모델은 단가 더 높음 (input $3 / output $15)."""
    guard = cg.CostGuard.get_instance()
    cost = guard.estimate_call_cost(
        input_text="dummy",
        expected_output_chars=500,
        entry_point="e4_conversation",
        model="claude-sonnet-4-5",
    )
    output_tokens = e3.estimate_output_tokens(
        500, entry_point="e4_conversation", model="claude-sonnet-4-5"
    )
    expected = 100 / 1_000_000 * 3.0 + output_tokens / 1_000_000 * 15.0
    assert cost == pytest.approx(expected, rel=1e-9)


def test_estimate_call_cost_unknown_model_falls_back_to_sonnet():
    """미등록 모델 → sonnet 단가 fallback (client.py 동일 정책)."""
    guard = cg.CostGuard.get_instance()
    cost = guard.estimate_call_cost(
        input_text="x",
        expected_output_chars=100,
        entry_point="e1",
        model="unknown-model-id",
    )
    # estimator도 unknown model → EP-only fit으로 fallback
    output_tokens = e3.estimate_output_tokens(
        100, entry_point="e1", model="unknown-model-id"
    )
    expected = 100 / 1_000_000 * 3.0 + output_tokens / 1_000_000 * 15.0
    assert cost == pytest.approx(expected, rel=1e-9)


def test_estimate_call_cost_does_not_record_anything():
    """★ 사전 추정은 cumulative/slice 누적에 영향 없음 (ADDITIVE 원칙)."""
    guard = cg.CostGuard.get_instance()
    initial_cum = guard.cumulative_usd
    initial_slice = guard.slice_usd
    initial_count = guard.call_count
    guard.estimate_call_cost(
        input_text="x",
        expected_output_chars=200,
        entry_point="e1",
        model="claude-haiku-4-5",
    )
    assert guard.cumulative_usd == initial_cum
    assert guard.slice_usd == initial_slice
    assert guard.call_count == initial_count


# ============================================================
# check_pre_call_budget — SAFETY BUFFER + non-blocking
# ============================================================


def test_pre_call_safety_buffer_constant():
    """PRE_CALL_SAFETY_BUFFER = 1.25 (estimator P-level delta 기반)."""
    assert cg.PRE_CALL_SAFETY_BUFFER == 1.25


def test_check_pre_call_budget_buffer_applied():
    """raw × 1.25 = buffered (estimator max delta 24.58% 흡수)."""
    guard = cg.CostGuard.get_instance()
    result = guard.check_pre_call_budget(estimated_cost_usd=0.10)
    assert result["raw_estimate_usd"] == 0.10
    assert result["buffered_estimate_usd"] == pytest.approx(0.125)


def test_check_pre_call_budget_within_budget_no_warning(caplog):
    """예산 여유 시 would_exceed_* False + 로그 없음."""
    guard = cg.CostGuard.get_instance()
    # default cap=$1.00, threshold=$4.00. raw $0.05 × 1.25 = $0.0625.
    with caplog.at_level(logging.WARNING, logger="portfolio.llm.cost_guard"):
        result = guard.check_pre_call_budget(estimated_cost_usd=0.05)
    assert result["would_exceed_slice_cap"] is False
    assert result["would_exceed_threshold"] is False
    assert not any("pre-call" in r.message for r in caplog.records)


def test_check_pre_call_budget_non_blocking_over_cap(caplog):
    """slice cap 초과 추정 시 WARNING만, raise 없음 (non-blocking)."""
    guard = cg.CostGuard.get_instance()
    guard.slice_usd = 0.95  # cap $1.00에 거의 도달
    # buffered = 0.10 × 1.25 = 0.125 → slice_usd + buffered = 1.075 > 1.00
    with caplog.at_level(logging.WARNING, logger="portfolio.llm.cost_guard"):
        result = guard.check_pre_call_budget(estimated_cost_usd=0.10)
    assert result["would_exceed_slice_cap"] is True
    assert any("slice cap" in r.message for r in caplog.records)


def test_check_pre_call_budget_non_blocking_over_threshold(caplog):
    """cumulative threshold 초과 추정 시 WARNING만, raise 없음."""
    guard = cg.CostGuard.get_instance()
    guard.cumulative_usd = 3.95  # threshold $4.00에 거의 도달
    with caplog.at_level(logging.WARNING, logger="portfolio.llm.cost_guard"):
        result = guard.check_pre_call_budget(estimated_cost_usd=0.10)
    assert result["would_exceed_threshold"] is True
    assert any("threshold" in r.message for r in caplog.records)


# ============================================================
# 기존 CostGuard 동작 불변 검증
# ============================================================


def test_existing_record_call_still_increments():
    """record_call() — Slice 13 변경 영향 없음."""
    guard = cg.CostGuard.get_instance()
    guard.record_call(cost_usd=0.005, model="claude-haiku-4-5")
    assert guard.call_count == 1
    assert guard.total_cost_usd == pytest.approx(0.005)


def test_existing_reset_slice_still_clears():
    """reset_slice() 동작 무수정."""
    guard = cg.CostGuard.get_instance()
    guard.record_cost(0.5)
    assert guard.slice_usd > 0
    guard.reset_slice("new_slice")
    assert guard.slice_usd == 0.0


def test_existing_50_call_budget_still_blocks():
    """PER_INSTANCE_LIMIT=50 budget guard 동작 무수정 (instance_call_count 기준)."""
    from apps.portfolio.llm.exceptions import LLMBudgetExceededError

    guard = cg.CostGuard.get_instance()
    # instance limit는 50이므로 51회째에서 raise
    for _ in range(50):
        guard.record_call(cost_usd=0.001, model="claude-haiku-4-5")
    with pytest.raises(LLMBudgetExceededError):
        guard.record_call(cost_usd=0.001, model="claude-haiku-4-5")
