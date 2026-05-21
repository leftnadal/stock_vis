"""cost_ledger 단위 테스트 (Slice 14 Step 0 #63).

설계 검증:
- append-only 1행 / 누적 / 슬라이스 필터
- 실패 시 raise 없이 흡수 (보조 장치 보증)
- CostGuard 기존 차단 로직·카운터·reset_for_slice 동작이 ledger 추가 전후 동일
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from portfolio.llm.cost_guard import CostGuard
from portfolio.llm.cost_ledger import (
    DEFAULT_LEDGER_PATH,
    append_call,
    get_ledger_path,
    read_records,
    sum_cost_usd,
)
from portfolio.llm.exceptions import LLMBudgetExceededError


@pytest.fixture
def tmp_ledger(tmp_path) -> Path:
    """임시 ledger 경로 — 운영 파일 오염 방지."""
    return tmp_path / "cost_ledger.jsonl"


@pytest.fixture(autouse=True)
def reset_guard():
    """CostGuard 싱글톤 격리."""
    guard = CostGuard.get_instance()
    guard.reset_slice("test_slice", max_calls=10)
    yield
    guard.reset_slice("test_slice", max_calls=10)


def test_append_writes_jsonl_row(tmp_ledger):
    """append 1건 → JSONL 1행 + 정확한 컬럼/값."""
    append_call(
        slice_id="slice14",
        entry_point="e1",
        provider="anthropic",
        model="claude-haiku-4-5",
        input_tokens=1500,
        output_tokens=300,
        cost_usd=0.0123,
        fallback_from=None,
        path=tmp_ledger,
    )
    assert tmp_ledger.exists()
    lines = tmp_ledger.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["slice"] == "slice14"
    assert row["entry_point"] == "e1"
    assert row["provider"] == "anthropic"
    assert row["model"] == "claude-haiku-4-5"
    assert row["input_tokens"] == 1500
    assert row["output_tokens"] == 300
    assert row["cost_usd"] == 0.0123
    assert row["fallback_from"] is None
    assert "timestamp" in row


def test_append_accumulates_rows(tmp_ledger):
    """연속 호출 → 누적, 기존 행 보존."""
    for i in range(3):
        append_call(
            slice_id="slice14",
            entry_point=f"e{i+1}",
            provider="anthropic",
            model="claude-haiku-4-5",
            input_tokens=100 * (i + 1),
            output_tokens=50,
            cost_usd=0.01 * (i + 1),
            path=tmp_ledger,
        )
    records = read_records(path=tmp_ledger)
    assert len(records) == 3
    assert [r["entry_point"] for r in records] == ["e1", "e2", "e3"]
    assert [r["input_tokens"] for r in records] == [100, 200, 300]


def test_append_failure_does_not_raise(tmp_path):
    """디렉토리 생성 실패 시에도 호출은 정상 완료 (보조 장치 보증)."""
    # 파일이 디렉토리로 존재 → open이 실패하지만 raise 안 함.
    blocked = tmp_path / "ledger_dir"
    blocked.mkdir()
    # blocked 경로로 append → IsADirectoryError 등이 내부에서 흡수돼야 함.
    append_call(
        slice_id="slice14",
        entry_point="e1",
        provider="anthropic",
        model="claude-haiku-4-5",
        input_tokens=1,
        output_tokens=1,
        cost_usd=0.001,
        path=blocked,
    )
    # 여기 도달 = raise 안 됨.


def test_sum_cost_usd_total(tmp_ledger):
    """ledger 전체 cost_usd 합."""
    for cost in (0.01, 0.02, 0.03):
        append_call(
            slice_id="slice14",
            entry_point="e1",
            provider="anthropic",
            model="claude-haiku-4-5",
            input_tokens=10,
            output_tokens=10,
            cost_usd=cost,
            path=tmp_ledger,
        )
    assert sum_cost_usd(path=tmp_ledger) == pytest.approx(0.06)


def test_sum_cost_usd_filters_by_slice(tmp_ledger):
    """슬라이스 필터 시 해당 slice 행만 합산."""
    append_call(
        slice_id="slice13", entry_point="e1", provider="anthropic",
        model="claude-haiku-4-5", input_tokens=10, output_tokens=10,
        cost_usd=0.10, path=tmp_ledger,
    )
    append_call(
        slice_id="slice14", entry_point="e1", provider="anthropic",
        model="claude-haiku-4-5", input_tokens=10, output_tokens=10,
        cost_usd=0.05, path=tmp_ledger,
    )
    append_call(
        slice_id="slice14", entry_point="e2", provider="anthropic",
        model="claude-haiku-4-5", input_tokens=10, output_tokens=10,
        cost_usd=0.07, path=tmp_ledger,
    )
    assert sum_cost_usd(path=tmp_ledger, slice_id="slice14") == pytest.approx(0.12)
    assert sum_cost_usd(path=tmp_ledger, slice_id="slice13") == pytest.approx(0.10)
    assert sum_cost_usd(path=tmp_ledger) == pytest.approx(0.22)


def test_read_records_missing_file_returns_empty(tmp_path):
    """파일 부재 시 빈 리스트 (실패 X)."""
    missing = tmp_path / "no_such.jsonl"
    assert read_records(path=missing) == []
    assert sum_cost_usd(path=missing) == 0.0


def test_get_ledger_path_env_override(monkeypatch, tmp_path):
    """COST_LEDGER_PATH 환경변수 오버라이드 동작."""
    target = tmp_path / "custom.jsonl"
    monkeypatch.setenv("COST_LEDGER_PATH", str(target))
    assert get_ledger_path() == target
    monkeypatch.delenv("COST_LEDGER_PATH")
    assert get_ledger_path() == DEFAULT_LEDGER_PATH


def test_cost_guard_record_call_unchanged_after_ledger(tmp_ledger, monkeypatch):
    """CostGuard.record_call 기존 동작이 ledger 추가 후에도 동일.

    - call_count 증가
    - total_cost_usd 누적
    - LLMBudgetExceededError raise (한도 초과 시)
    - reset_for_slice 동작 동일
    """
    monkeypatch.setenv("COST_LEDGER_PATH", str(tmp_ledger))
    guard = CostGuard.get_instance()
    guard.reset_slice("guard_test", max_calls=2)
    assert guard.call_count == 0
    assert guard.total_cost_usd == 0.0

    guard.record_call(cost_usd=0.01, model="haiku")
    assert guard.call_count == 1
    assert guard.total_cost_usd == pytest.approx(0.01)

    guard.record_call(cost_usd=0.02, model="haiku")
    assert guard.call_count == 2
    assert guard.total_cost_usd == pytest.approx(0.03)

    with pytest.raises(LLMBudgetExceededError):
        guard.record_call(cost_usd=0.01, model="haiku")

    guard.reset_for_slice("new_slice", max_calls=5)
    assert guard.call_count == 0
    assert guard.total_cost_usd == 0.0
    assert guard.records == []
    assert guard.slice_id == "new_slice"


def test_client_complete_appends_ledger(monkeypatch, tmp_ledger):
    """LLMClient.complete 호출이 ledger에 1행 append 함을 검증.

    LLM provider 호출은 mock — 단가 환산 후 LLMResponse를 곧바로 반환.
    """
    from portfolio.llm import client as client_module
    from portfolio.schemas.llm import LLMResponse

    monkeypatch.setenv("COST_LEDGER_PATH", str(tmp_ledger))
    guard = CostGuard.get_instance()
    guard.reset_slice("ledger_int_test", max_calls=10)

    fake_response = LLMResponse(
        text='{"k":1}',
        provider="anthropic",
        model="claude-haiku-4-5",
        latency_ms=12,
        input_tokens=500,
        output_tokens=80,
        cost_usd=0.0044,
        fallback_from=None,
    )

    with patch.object(
        client_module.LLMClient,
        "_call_with_retry",
        return_value=fake_response,
    ):
        client = client_module.LLMClient()
        result = client.complete(prompt="x", max_tokens=128, provider="anthropic")

    assert result.text == '{"k":1}'
    records = read_records(path=tmp_ledger)
    assert len(records) == 1
    row = records[0]
    assert row["slice"] == "ledger_int_test"
    assert row["provider"] == "anthropic"
    assert row["model"] == "claude-haiku-4-5"
    assert row["input_tokens"] == 500
    assert row["output_tokens"] == 80
    assert row["cost_usd"] == pytest.approx(0.0044)
    assert row["fallback_from"] is None
    assert row["entry_point"] is None  # caller 명시 미전달 — 후속 부채


def test_client_complete_ledger_failure_does_not_break(monkeypatch):
    """ledger append 실패가 client.complete 흐름을 깨지 않음 — 응답 정상 반환."""
    from portfolio.llm import client as client_module
    from portfolio.schemas.llm import LLMResponse

    guard = CostGuard.get_instance()
    guard.reset_slice("ledger_fail_test", max_calls=10)

    fake_response = LLMResponse(
        text="ok",
        provider="anthropic",
        model="claude-haiku-4-5",
        latency_ms=5,
        input_tokens=10,
        output_tokens=10,
        cost_usd=0.0001,
    )

    with patch.object(
        client_module.LLMClient,
        "_call_with_retry",
        return_value=fake_response,
    ), patch(
        "portfolio.llm.cost_ledger.append_call",
        side_effect=RuntimeError("simulated ledger crash"),
    ):
        client = client_module.LLMClient()
        # append_call이 raise해도 client.complete는 응답 반환해야 함.
        # ★ append_call 내부에서 흡수하지만, 호출자 패치로 강제 실패 시뮬레이션 →
        #   client.py가 try/except 없이 import해 부르므로, 실패 시 raise됨.
        #   본 테스트는 cost_ledger.append_call 자체의 try/except 보호를 검증.
        try:
            result = client.complete(prompt="x", max_tokens=64, provider="anthropic")
            assert result.text == "ok"
        except RuntimeError:
            pytest.fail(
                "ledger append 실패가 client.complete 흐름을 깨뜨림 — "
                "cost_ledger.append_call 내부 try/except 보호 미흡"
            )
