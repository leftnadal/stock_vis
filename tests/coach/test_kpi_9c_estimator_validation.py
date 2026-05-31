"""Slice 11 Step 0 §5 — KPI 9c skeleton (#48 v3 첫 실측 검증).

**스켈레톤만 등록**. 실제 발동은 Slice 11 Part 3 smoke 첫 LLM 호출 시점.

룰:
  count_tokens(messages, system, model)  → estimated_input_tokens
  client.messages.create(messages, system, model) → response.usage.input_tokens

  KPI 9c PASS = |estimated - actual| / actual × 100 ≤ 2%
  FAIL → #48 재오픈

이 파일은 Part 3에서 실측 데이터를 채워 본격 PASS/FAIL 판정한다.
Step 0에서는 import + skeleton 함수만 검증.
"""

from __future__ import annotations

import pytest

from apps.portfolio.measure.estimator_v3 import estimate_input_tokens

KPI_9C_THRESHOLD_PCT = 2.0


def measure_kpi_9c_delta(
    estimated_input_tokens: int,
    actual_input_tokens: int,
) -> float:
    """KPI 9c 측정 — |est-actual| / actual × 100.

    Part 3 smoke에서 호출자가 count_tokens + actual response.usage를 모은 뒤
    이 함수로 delta% 계산. KPI_9C_THRESHOLD_PCT 비교는 호출자 책임.
    """
    if actual_input_tokens <= 0:
        raise ValueError("actual_input_tokens must be > 0")
    return abs(estimated_input_tokens - actual_input_tokens) / actual_input_tokens * 100


def test_kpi_9c_delta_helper_computes_percent():
    """delta helper 동작 검증 (Part 3 실측 채우기 전 sanity check)."""
    assert measure_kpi_9c_delta(100, 100) == 0.0
    assert measure_kpi_9c_delta(98, 100) == pytest.approx(2.0)
    assert measure_kpi_9c_delta(102, 100) == pytest.approx(2.0)


def test_kpi_9c_threshold_value():
    """임계 ≤ 2% 명시."""
    assert KPI_9C_THRESHOLD_PCT == 2.0


def test_kpi_9c_estimator_callable_skeleton():
    """estimator_v3.estimate_input_tokens가 import 가능 + callable (Part 3 발동 대기)."""
    assert callable(estimate_input_tokens)


@pytest.mark.skip(reason="Part 3 smoke 실측 시점에 발동 — Step 0 스켈레톤")
def test_kpi_9c_real_call_within_2pct():
    """Part 3 진입 시:
    1. messages = [...]; system = "..."; model = "claude-haiku-4-5"
    2. est = estimate_input_tokens(messages, system, model)
    3. response = client.messages.create(...)  # 실측
    4. actual = response.usage.input_tokens
    5. delta = measure_kpi_9c_delta(est, actual)
    6. assert delta <= KPI_9C_THRESHOLD_PCT
    """
    raise AssertionError("Part 3 발동 — 실측 채워야 함")
