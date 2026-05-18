"""Slice 11 Step 0 §2 — messages 보존 hook 단위 테스트 (#52).

KPI:
- hook 멱등성 PASS (동일 hash → 1회만 저장)
- toggle off 동작 PASS (STOCKVIS_LLM_MESSAGE_DUMP=0)
- redact 룰 동작 (API key, password 마스킹)

테스트 6건 — 멱등성, toggle, redact, 다중 호출, slice 격리, hash 결정성.
"""

from __future__ import annotations

import json
import os

import pytest

from portfolio.measure import message_dumper as md


@pytest.fixture
def isolated_jsonl(tmp_path):
    """slice별 JSONL 파일을 tmp_path로 격리."""
    return tmp_path / "slice_test" / "llm_messages.jsonl"


@pytest.fixture(autouse=True)
def _ensure_toggle_default(monkeypatch):
    monkeypatch.setenv(md.ENV_TOGGLE, "1")
    yield


def _msg(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def test_dump_writes_record_and_returns_true(isolated_jsonl):
    """첫 호출 → 파일 생성 + record append + True 반환."""
    appended = md.dump_llm_call(
        messages=[_msg("user", "안녕하세요")],
        system="당신은 도우미입니다",
        model="claude-haiku-4-5",
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.0001,
        slice_n=99,
        out_path=isolated_jsonl,
    )
    assert appended is True
    lines = isolated_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["model"] == "claude-haiku-4-5"
    assert rec["input_tokens"] == 10
    assert rec["slice"] == 99
    assert "hash" in rec and len(rec["hash"]) == 64


def test_idempotent_same_call_writes_once(isolated_jsonl):
    """동일 (messages, system, model) 2회 호출 → 첫 번째만 append."""
    args = dict(
        messages=[_msg("user", "동일 호출")],
        system="sys",
        model="m",
        input_tokens=1,
        output_tokens=1,
        cost_usd=0.0,
        slice_n=99,
        out_path=isolated_jsonl,
    )
    assert md.dump_llm_call(**args) is True
    assert md.dump_llm_call(**args) is False  # dedupe hit
    lines = isolated_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1


def test_toggle_off_skips_dump(isolated_jsonl, monkeypatch):
    """STOCKVIS_LLM_MESSAGE_DUMP=0 → 파일 미생성 + False 반환."""
    monkeypatch.setenv(md.ENV_TOGGLE, "0")
    result = md.dump_llm_call(
        messages=[_msg("user", "x")],
        system=None,
        model="m",
        input_tokens=1,
        output_tokens=1,
        cost_usd=0.0,
        slice_n=99,
        out_path=isolated_jsonl,
    )
    assert result is False
    assert not isolated_jsonl.exists()


def test_redact_masks_secrets_in_messages_and_system(isolated_jsonl):
    """messages/system 안의 API_KEY / password / Anthropic sk-ant 마스킹."""
    appended = md.dump_llm_call(
        messages=[_msg("user", "API_KEY=sk-ant-abcdef1234567890XYZ_secret-stuff")],
        system="password=p@ssw0rd123!",
        model="m",
        input_tokens=1,
        output_tokens=1,
        cost_usd=0.0,
        slice_n=99,
        out_path=isolated_jsonl,
    )
    assert appended
    rec = json.loads(isolated_jsonl.read_text(encoding="utf-8").splitlines()[0])
    content = rec["messages"][0]["content"]
    assert "<REDACTED>" in content
    assert "sk-ant-abcdef" not in content
    assert "<REDACTED>" in rec["system"]
    assert "p@ssw0rd" not in rec["system"]


def test_different_calls_append_separately(isolated_jsonl):
    """messages 다름 → 다른 hash → 두 번째도 append."""
    base = dict(system="s", model="m", input_tokens=1, output_tokens=1, cost_usd=0.0, slice_n=99, out_path=isolated_jsonl)
    assert md.dump_llm_call(messages=[_msg("user", "A")], **base)
    assert md.dump_llm_call(messages=[_msg("user", "B")], **base)
    lines = isolated_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    hashes = {json.loads(l)["hash"] for l in lines}
    assert len(hashes) == 2


def test_hash_deterministic_across_calls():
    """compute_call_hash는 동일 입력 → 동일 출력. ordering 변경에도 robust."""
    h1 = md.compute_call_hash([_msg("user", "x")], "s", "m")
    h2 = md.compute_call_hash([_msg("user", "x")], "s", "m")
    h3 = md.compute_call_hash([_msg("user", "y")], "s", "m")
    assert h1 == h2
    assert h1 != h3
    # redact 적용 전 raw key 기반 → 일관성
    assert len(h1) == 64
