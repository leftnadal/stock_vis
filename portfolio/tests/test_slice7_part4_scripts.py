"""Slice 7 Part 4 §3~6 스크립트 회귀 테스트 (LLM 호출 없음).

- _common.extract_answer: slice5/6/7 각 구조에서 답변 추출
- _common.load_raw: data['entries'] / data['results'] 호환
- _common.referenced_metrics: slice별 인용 지표 추출
- prepare_reference_pairs: 5건 sample 생성
- generate_rationale --dry-run: 의존 파일만 로드, 52건 카운트
- calc_auto_metadata / prepare_manual_eval_v7: 의존 가드 (rationales 미존재 시 종료)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SLICE7_DIR = ROOT / "docs/portfolio/coach/slice7"


# ===== _common 헬퍼 =====


def test_common_load_raw_slice5_results_key():
    from scripts.slice7._common import load_raw

    items = load_raw(ROOT / "docs/portfolio/coach/slice5/step8_2way_e3_raw.json")
    assert len(items) == 14
    assert "model_label" in items[0]


def test_common_load_raw_slice7_entries_key():
    from scripts.slice7._common import load_raw

    items = load_raw(
        ROOT / "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json"
    )
    assert len(items) == 28
    assert "provider" in items[0]


def test_common_load_raw_missing_returns_empty():
    from scripts.slice7._common import load_raw

    items = load_raw(ROOT / "docs/portfolio/coach/nonexistent.json")
    assert items == []


def test_common_extract_answer_slice5_uses_one_liner():
    from scripts.slice7._common import extract_answer, load_raw

    items = load_raw(ROOT / "docs/portfolio/coach/slice5/step8_2way_e3_raw.json")
    ans = extract_answer(items[0], "slice5")
    # slice5 parsed.comments[].one_liner 합쳐서 추출
    assert len(ans) > 50
    assert "investing" not in ans.lower() or "투자" in ans or "수익" in ans


def test_common_extract_answer_slice6_uses_holistic_fields():
    from scripts.slice7._common import extract_answer, load_raw

    items = load_raw(
        ROOT / "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json"
    )
    ans = extract_answer(items[0], "slice6")
    # slice6 parsed의 5 fields 합쳐서 추출
    assert len(ans) > 50


def test_common_extract_answer_slice7_strips_fence_and_uses_answer():
    from scripts.slice7._common import extract_answer, load_raw

    items = load_raw(
        ROOT / "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json"
    )
    ans = extract_answer(items[0], "slice7")
    # ```json fence 제거되고 answer 키 추출
    assert "```" not in ans
    assert len(ans) > 50


# ===== §5 prepare_reference_pairs =====


def test_prepare_reference_pairs_produces_5_samples(tmp_path, monkeypatch):
    from scripts.slice7 import prepare_reference_pairs as mod

    out_path = tmp_path / "refs.json"
    monkeypatch.setattr(mod, "OUT_PATH", out_path)
    rc = mod.main()
    assert rc == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(data) == 5
    assert set(data.keys()) == {f"sample_{i}" for i in range(1, 6)}
    # 양극단 1점·5점 sample 존재
    assert any("nat=1" in v["score"] for v in data.values())
    assert any("nat=5" in v["score"] and "ins=5" in v["score"] for v in data.values())


# ===== §3 generate_rationale dry-run =====


def test_generate_rationale_dry_run_counts_52_entries(monkeypatch, capsys):
    """LLM 호출 없이 entry 카운트만 확인 — 52건 (slice5=14 + slice6=10 + slice7=28)."""
    from scripts.slice7 import generate_rationale as mod

    monkeypatch.setattr(sys, "argv", ["generate_rationale", "--dry-run"])
    rc = mod.main()
    assert rc == 0
    captured = capsys.readouterr()
    assert "총 entries: 52" in captured.out
    assert "slice5: 14" in captured.out
    assert "slice6: 10" in captured.out
    assert "slice7: 28" in captured.out


# ===== §4/§6 의존 가드 =====


def test_calc_auto_metadata_guards_missing_rationales(tmp_path, monkeypatch, capsys):
    from scripts.slice7 import calc_auto_metadata as mod

    monkeypatch.setattr(mod, "INPUT_PATH", tmp_path / "missing.json")
    rc = mod.main()
    assert rc == 1
    captured = capsys.readouterr()
    assert "미존재" in captured.err or "Phase B" in captured.err


def test_prepare_manual_eval_v7_guards_missing_deps(tmp_path, monkeypatch, capsys):
    from scripts.slice7 import prepare_manual_eval_v7 as mod

    monkeypatch.setattr(mod, "RATIONALES_PATH", tmp_path / "missing.json")
    rc = mod.main()
    assert rc == 1


# ===== §8 score_stage1 의존 가드 (Stage 1 평가 미진행 시) =====


def test_score_stage1_guards_missing_filled(tmp_path, monkeypatch, capsys):
    from scripts.slice7 import score_stage1 as mod

    monkeypatch.setattr(mod, "FILLED_PATH", tmp_path / "missing.md")
    rc = mod.main()
    assert rc == 1


# ===== §9/§10 의존 가드 =====


def test_prepare_stage2_form_guards_missing_verdict(tmp_path, monkeypatch, capsys):
    from scripts.slice7 import prepare_stage2_form as mod

    monkeypatch.setattr(mod, "STAGE1_VERDICT", tmp_path / "missing.json")
    rc = mod.main()
    assert rc == 1


def test_score_final_guards_missing_stage1(tmp_path, monkeypatch, capsys):
    from scripts.slice7 import score_final as mod

    monkeypatch.setattr(mod, "STAGE1_PATH", tmp_path / "missing.json")
    rc = mod.main()
    assert rc == 1


def test_score_final_normalize_provider():
    from scripts.slice7.score_final import normalize_provider

    assert normalize_provider("anthropic_haiku") == "haiku"
    assert normalize_provider("haiku") == "haiku"
    assert normalize_provider("claude-haiku-4-5") == "haiku"
    assert normalize_provider("anthropic_sonnet") == "sonnet"
    assert normalize_provider("claude-sonnet-4-5") == "sonnet"
    assert normalize_provider(None) == "unknown"
    assert normalize_provider("") == "unknown"
