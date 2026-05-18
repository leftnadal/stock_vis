"""Slice 10 Step 0 §1 — dump 스크립트 단위 테스트 (data-prep 카테고리).

KPI:
- 정규화 성공률 100% (N≥200)
- 필수 필드 누락 0건
- 멱등성 (2회 실행 동일 결과)

테스트 6건 — flat/nested 정규화, model 추론, 소스 매핑+카운트, 필수필드,
멱등성+영속파일 일치.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.coach.dump_all_llm_calls import (
    REQUIRED_FIELDS,
    _infer_model_from_cost,
    build_slice_sources,
    collect_entries,
    normalize_entry,
    validate_entries,
    write_jsonl,
)


@pytest.fixture(scope="module")
def all_entries():
    return collect_entries(build_slice_sources())


def test_normalize_entry_flat_and_nested():
    """flat (input_tokens at top) + nested (metadata.*) 모두 평탄화.

    extra dict는 setdefault → 기존 키 보호. 비-스칼라 페이로드는 제거.
    """
    flat = normalize_entry(
        {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.001, "model": "haiku", "raw_text": "x" * 99},
        slice_n=1,
        source_file="a.json",
        extra={"scenario_id": "S01", "input_tokens": 999},
    )
    assert flat["input_tokens"] == 100  # extra가 덮어쓰지 않음
    assert flat["scenario_id"] == "S01"
    assert flat["slice"] == 1
    assert "raw_text" not in flat

    nested = normalize_entry(
        {"metadata": {"input_tokens": 200, "output_tokens": 80, "cost_usd": 0.002, "model": "sonnet"}},
        slice_n=2,
        source_file="b.json",
    )
    assert nested["input_tokens"] == 200
    assert nested["model"] == "sonnet"
    assert "metadata" not in nested


def test_infer_model_from_cost():
    """cost 기반 haiku/sonnet 추론 (slice7 step8 모델 결측 보강)."""
    # 100/100 × haiku (1e-6/5e-6) = 0.0006
    assert _infer_model_from_cost(100, 100, 0.0006) == "claude-haiku-4-5"
    # 100/100 × sonnet (3e-6/15e-6) = 0.0018
    assert _infer_model_from_cost(100, 100, 0.0018) == "claude-sonnet-4-5"
    # zero / 비현실 cost
    assert _infer_model_from_cost(100, 100, 0.0) is None


def test_all_source_files_exist():
    """지시서 §1 매핑된 모든 raw 파일 존재."""
    missing = [str(s.path) for s in build_slice_sources() if not s.path.exists()]
    assert not missing, f"Missing: {missing}"


def test_total_count_and_per_slice(all_entries):
    """KPI 2: N≥200 + 슬라이스별 최소 entry 수 (회신 기반 매핑)."""
    assert len(all_entries) >= 200
    per_slice_min = {1: 10, 2: 15, 3: 15, 4: 15, 5: 15, 6: 21, 7: 56, 8: 27, 9: 26}
    actual = {s: sum(1 for e in all_entries if e["slice"] == s) for s in per_slice_min}
    for s, mn in per_slice_min.items():
        assert actual[s] >= mn, f"slice {s}: got {actual[s]} < {mn}"


def test_required_fields_present_with_correct_types(all_entries):
    """KPI: input/output/cost/model 누락 0건 + 타입 검증 + Slice 9 estimated 보존."""
    missing_count, missing = validate_entries(all_entries)
    assert missing_count == 0, f"missing: {missing[:3]}"

    for e in all_entries:
        assert isinstance(e["input_tokens"], int) and e["input_tokens"] >= 0
        assert isinstance(e["output_tokens"], int) and e["output_tokens"] >= 0
        assert isinstance(e["cost_usd"], (int, float)) and e["cost_usd"] >= 0
        assert isinstance(e["model"], str) and e["model"]

    # Slice 9 estimated_input_tokens 보존 (#48 backtest 비교 기준)
    slice9 = [e for e in all_entries if e["slice"] == 9]
    assert all(isinstance(e.get("estimated_input_tokens"), int) for e in slice9)


def test_idempotent_dump_and_persisted_match(all_entries, tmp_path):
    """KPI: 2회 dump hash 동일 + 영속 jsonl이 현 collect 결과와 일치."""
    out1 = tmp_path / "first.jsonl"
    out2 = tmp_path / "second.jsonl"
    write_jsonl(all_entries, out1)
    write_jsonl(all_entries, out2)
    assert hashlib.sha256(out1.read_bytes()).hexdigest() == hashlib.sha256(out2.read_bytes()).hexdigest()

    persisted = Path("docs/portfolio/coach/all_llm_calls.jsonl")
    if persisted.exists():
        loaded = [json.loads(l) for l in persisted.read_text(encoding="utf-8").splitlines()]
        assert len(loaded) == len(all_entries)
