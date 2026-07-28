"""Slice 16 Step 0-A — #68 ledger 정합 단언 (entry_point + slice_id).

배경: Slice 15 P3-C 실 호출에서 ledger 행이 `slice="default"`, `entry_point=null`로
떨어지는 부정합 발견. Step 0-A에서 두 부정합을 동시 해소:

  1. `CostGuard.slice_id` 기본값을 env `COACH_RUNTIME_SLICE_ID`(기본 "runtime")로
     변경 → reset_slice() 명시 호출 없는 운영 view 경로에서도 의미값 기록.
  2. `LLMClient.complete(entry_point=...)` 옵션 인자 추가 + ledger append에 전달.
  3. e1~e6_service 6곳에서 `entry_point="eN"` 명시 전달.

본 테스트는 (1) 기본값 정합 + (2,3) caller→client→ledger 흐름 정합을 함께 단언.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from apps.portfolio.llm.client import LLMClient
from apps.portfolio.llm.cost_guard import CostGuard
from apps.portfolio.llm.cost_ledger import read_records
from apps.portfolio.schemas.llm import LLMResponse

# ─────────────────────────────────────────────────────────────
# (1) CostGuard 기본 slice_id 정합
# ─────────────────────────────────────────────────────────────


def test_costguard_default_slice_id_uses_env_default():
    """env 미설정 시 CostGuard 기본 slice_id == 'runtime' (Slice 16 default)."""
    # 환경변수 격리 — 명시적으로 unset 후 검증
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("COACH_RUNTIME_SLICE_ID", None)
        guard = CostGuard()  # 새 인스턴스 (싱글톤 우회로 default_factory만 검증)
        assert guard.slice_id == "runtime", (
            f"기본 slice_id가 'default'가 아닌 'runtime'이어야 함 — 실제={guard.slice_id}"
        )


def test_costguard_default_slice_id_respects_env_override():
    """COACH_RUNTIME_SLICE_ID=slice99 → CostGuard 기본 slice_id == 'slice99'."""
    with patch.dict(os.environ, {"COACH_RUNTIME_SLICE_ID": "slice99"}):
        guard = CostGuard()
        assert guard.slice_id == "slice99"


def test_costguard_default_slice_id_is_never_default_string():
    """기본 slice_id가 절대로 'default'가 아님 — #68 부정합 차단 단언."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("COACH_RUNTIME_SLICE_ID", None)
        guard = CostGuard()
        assert guard.slice_id != "default", (
            "CostGuard 기본 slice_id='default'는 #68 부정합 — env 또는 reset_slice()로 의미값 채택 필요"
        )


# ─────────────────────────────────────────────────────────────
# (2,3) caller → client.complete(entry_point) → ledger 전 흐름
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def isolated_ledger(tmp_path, monkeypatch):
    """ledger를 임시 파일로 격리 (운영 ledger 오염 차단)."""
    ledger_path = tmp_path / "test_cost_ledger.jsonl"
    monkeypatch.setenv("COST_LEDGER_PATH", str(ledger_path))
    return ledger_path


def _fake_llm_response() -> LLMResponse:
    return LLMResponse(
        text='{"summary": "ok", "confidence": "medium", "metrics_table": ""}',
        provider="anthropic",
        model="claude-haiku-4-5",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        latency_ms=500,
        fallback_from=None,
    )


def test_client_complete_passes_entry_point_to_ledger(isolated_ledger, monkeypatch):
    """`client.complete(entry_point='e1')` → ledger 행에 entry_point='e1' 기록."""
    # CostGuard 싱글톤을 초기화해 env override 채택
    monkeypatch.setenv("COACH_RUNTIME_SLICE_ID", "slice16-test")
    CostGuard._instance = None  # 싱글톤 재초기화 강제

    # provider 호출은 mock — 실 LLM 미사용 ($0)
    client = LLMClient()
    with patch.object(client, "_call_with_retry", return_value=_fake_llm_response()):
        client.complete(prompt="hi", entry_point="e1")

    records = read_records(isolated_ledger)
    assert len(records) == 1
    row = records[0]
    assert row["entry_point"] == "e1", (
        f"client.complete(entry_point='e1')가 ledger에 전달돼야 함 — 실제={row.get('entry_point')!r}"
    )
    assert row["slice"] == "slice16-test", (
        f"CostGuard.slice_id가 env에서 채택돼 ledger에 기록돼야 함 — 실제={row.get('slice')!r}"
    )


def test_client_complete_without_entry_point_keeps_backward_compat(
    isolated_ledger, monkeypatch
):
    """`entry_point` 미전달 시 ledger entry_point=null — 기존 호출 무손상."""
    monkeypatch.setenv("COACH_RUNTIME_SLICE_ID", "slice16-test")
    CostGuard._instance = None

    client = LLMClient()
    with patch.object(client, "_call_with_retry", return_value=_fake_llm_response()):
        client.complete(prompt="hi")  # entry_point 미전달

    records = read_records(isolated_ledger)
    assert len(records) == 1
    assert records[0]["entry_point"] is None, (
        "기존 호출은 entry_point=null 유지 (backward-compat)"
    )


# ─────────────────────────────────────────────────────────────
# (3) coach service 6곳 entry_point 명시 검증
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "service_module,expected_entry",
    [
        ("apps.portfolio.services.coach.e1_service", "e1"),
        ("apps.portfolio.services.coach.e2_service", "e2"),
        ("apps.portfolio.services.coach.e3_service", "e3"),
        ("apps.portfolio.services.coach.e4_service", "e4"),
        ("apps.portfolio.services.coach.e5_service", "e5"),
        ("apps.portfolio.services.coach.e6_service", "e6"),
    ],
)
def test_coach_service_source_contains_entry_point_literal(
    service_module, expected_entry
):
    """6 service 소스에 `entry_point="eN"` literal이 존재 — 회귀 가드."""
    import importlib
    import inspect

    mod = importlib.import_module(service_module)
    src = inspect.getsource(mod)
    expected_literal = f'entry_point="{expected_entry}"'
    assert expected_literal in src, (
        f"{service_module} 소스에 {expected_literal!r}가 client.complete() 호출 인자로 존재해야 함"
    )
