"""CostGuard 단위 테스트 (Slice 3 D3.C + Slice 8 Part 1 #33 이중 카운터)."""

from __future__ import annotations

import pytest

from portfolio.llm.cost_guard import CostGuard
from portfolio.llm.exceptions import BudgetExceededError, LLMBudgetExceededError


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


# ============================================================
# Slice 8 Part 1 #33 — 이중 카운터 분리 (5건)
# ============================================================


def test_cost_guard_per_instance_limit():
    """instance 카운터 50회 PASS, 51회 시 BudgetExceededError(scope='instance')."""
    guard = CostGuard.get_instance()
    # slice 한도는 충분히 크게 (instance만 검증)
    guard.reset_slice("test_per_instance", max_calls=200)
    for i in range(50):
        guard.record_llm_call()
    assert guard.instance_call_count == 50
    with pytest.raises(BudgetExceededError) as excinfo:
        guard.record_llm_call()
    assert excinfo.value.scope == "instance"
    assert excinfo.value.count == 51
    assert excinfo.value.limit == 50


def test_cost_guard_per_slice_limit():
    """slice 카운터 100회 PASS, 101회 시 BudgetExceededError(scope='slice').

    instance 한도 우회를 위해 start_instance()로 instance 카운터를 주기적으로 reset.
    """
    guard = CostGuard.get_instance()
    guard.reset_slice("test_per_slice", max_calls=100)
    # instance 한도 (50)를 회피하기 위해 50회마다 start_instance
    for i in range(100):
        if i == 50:
            guard.start_instance()
        guard.record_llm_call()
    assert guard.call_count == 100
    # instance counter는 마지막 batch (50회)
    assert guard.instance_call_count == 50
    with pytest.raises(BudgetExceededError) as excinfo:
        guard.start_instance()  # instance reset
        guard.record_llm_call()  # 101회째
    assert excinfo.value.scope == "slice"
    assert excinfo.value.count == 101
    assert excinfo.value.limit == 100


def test_cost_guard_start_instance_resets_only_instance_counter():
    """start_instance()는 instance 카운터만 reset, slice 카운터·비용·records 모두 보존."""
    guard = CostGuard.get_instance()
    guard.reset_slice("test_start_instance", max_calls=100)
    for _ in range(10):
        guard.record_call(cost_usd=0.005, model="haiku")
    assert guard.call_count == 10
    assert guard.instance_call_count == 10
    assert guard.total_cost_usd == pytest.approx(0.05)
    assert len(guard.records) == 10

    guard.start_instance()

    # slice 카운터·비용·records 보존
    assert guard.call_count == 10
    assert guard.total_cost_usd == pytest.approx(0.05)
    assert len(guard.records) == 10
    # instance 카운터만 0으로
    assert guard.instance_call_count == 0


def test_cost_guard_reset_for_slice_idempotent():
    """reset_for_slice()는 reset_slice의 alias로 멱등 패턴 유지. 두 카운터 모두 0."""
    guard = CostGuard.get_instance()
    for _ in range(5):
        guard.record_call(cost_usd=0.005, model="haiku")
    assert guard.call_count == 5
    assert guard.instance_call_count == 5

    # alias 동작
    assert CostGuard.reset_for_slice is CostGuard.reset_slice

    # 1차 reset
    guard.reset_for_slice("slice_x", max_calls=80)
    assert guard.call_count == 0
    assert guard.instance_call_count == 0
    assert guard.max_calls == 80
    assert guard.total_cost_usd == 0.0
    assert guard.records == []

    # 2차 reset (멱등)
    guard.reset_for_slice("slice_x", max_calls=80)
    assert guard.call_count == 0
    assert guard.instance_call_count == 0


def test_cost_guard_singleton_preserved():
    """get_instance()가 항상 동일 인스턴스 반환 + Slice 8에서도 단일성 유지."""
    g1 = CostGuard.get_instance()
    g2 = CostGuard.get_instance()
    assert g1 is g2
    # reset 후에도 동일
    g1.reset_slice("test_singleton", max_calls=10)
    g3 = CostGuard.get_instance()
    assert g3 is g1
    # 변경이 모든 참조에 반영
    g1.record_llm_call()
    assert g2.call_count == 1
    assert g3.call_count == 1
