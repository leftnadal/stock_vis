"""CostGuard 단위 테스트 (Slice 3 D3.C)."""

from __future__ import annotations

import pytest

from portfolio.llm.cost_guard import CostGuard
from portfolio.llm.exceptions import LLMBudgetExceededError


@pytest.fixture(autouse=True)
def reset_guard():
    """매 테스트 전후 깨끗한 상태."""
    guard = CostGuard.get_instance()
    guard.reset_slice("test_slice", max_calls=50)
    yield
    guard.reset_slice("test_slice", max_calls=50)


def test_initial_state():
    guard = CostGuard.get_instance()
    assert guard.call_count == 0
    assert guard.max_calls == 50
    assert guard.slice_id == "test_slice"


def test_record_call_increments():
    guard = CostGuard.get_instance()
    guard.record_call(cost_usd=0.005, model="claude-haiku-4-5")
    assert guard.call_count == 1
    assert guard.total_cost_usd == 0.005
    assert len(guard.records) == 1


def test_reset_slice_clears():
    guard = CostGuard.get_instance()
    guard.record_call(cost_usd=0.01, model="haiku")
    guard.reset_slice("new_slice", max_calls=30)
    assert guard.call_count == 0
    assert guard.max_calls == 30
    assert guard.slice_id == "new_slice"


def test_budget_exceeded_raises():
    guard = CostGuard.get_instance()
    guard.reset_slice("test", max_calls=2)
    guard.record_call(cost_usd=0.01, model="haiku")
    guard.record_call(cost_usd=0.01, model="haiku")
    with pytest.raises(LLMBudgetExceededError):
        guard.record_call(cost_usd=0.01, model="haiku")


def test_status_dict():
    guard = CostGuard.get_instance()
    status = guard.status()
    assert status["call_count"] == 0
    assert status["remaining"] == 50
    assert "started_at" in status
    assert "records_count" in status
