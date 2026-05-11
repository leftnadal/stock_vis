"""Slice 6 Part 4 Step 9.1 — Manual eval 표 양식 생성.

raw.json (10 entries) → eval_form.md (blind 평가 표) + eval_key.json (blind 해제용)

- LLM provider 라벨 가림 (haiku/sonnet 구분 가림)
- entry 순서 randomize (seed=42 고정, 재현 가능)
- naturalness/insight 평점 입력 칸 제공 (1~5)
- preset_id 표시 유지 (preset 외삽 분석에 필요)
- V 식별자(V1~V5)는 fixture prefix에서 추출

지시서 코드 가정 (entries[i]["provider"]/["commentary"]/["cost_usd"])과 실제 raw 구조
(results[i]["model_label"]/["parsed"]/["metadata"]["cost_usd"]) 매핑 처리.

Usage:
    python -m scripts.slice6.prepare_manual_eval
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from scripts.validation._setup import init_django

init_django()


RAW_PATH = Path("docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json")
EVAL_FORM_PATH = Path("docs/portfolio/coach/slice6/step9_1_eval_form.md")
EVAL_KEY_PATH = Path("docs/portfolio/coach/slice6/step9_1_eval_key.json")


def _format_commentary(parsed: dict) -> str:
    """parsed dict 6 필드 → 사용자 가독 텍스트."""
    lines = [
        f"**Holistic Assessment**: {parsed.get('holistic_assessment', '?')}",
        "",
        f"**Diversification**: {parsed.get('diversification_comment', '?')}",
        "",
        f"**Sector Balance**: {parsed.get('sector_balance_comment', '?')}",
        "",
        f"**Risk Concentration**: {parsed.get('risk_concentration_comment', '?')}",
        "",
        f"**Preset Alignment**: `{parsed.get('preset_alignment', '?')}`  |  **Confidence**: {parsed.get('confidence', '?')}/5",
    ]
    return "\n".join(lines)


def _v_prefix(fixture: str) -> str:
    """v1_concentrated_balanced → V1."""
    parts = fixture.split("_")
    return parts[0].upper() if parts else fixture


def main() -> int:
    if not RAW_PATH.exists():
        print(f"[ERROR] {RAW_PATH} 미존재. Step 7+8 실행 필요.")
        return 1

    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    results = raw["results"]
    assert len(results) == 10, f"expected 10 entries, got {len(results)}"

    # randomize with fixed seed
    indexed = list(enumerate(results))
    random.Random(42).shuffle(indexed)

    key_map: dict[str, dict] = {}
    lines = [
        "# Slice 6 Part 4 Manual Eval Form",
        "",
        "> **평가 방법**: 각 entry에 대해 naturalness (자연스러움) / insight (통찰력)를 1~5점으로 평가.",
        "> **Blind**: LLM provider 라벨 가림. preset_id만 노출 (외삽 분석용).",
        "> **Scale**: 1=매우 부족, 2=부족, 3=보통, 4=좋음, 5=매우 좋음",
        "",
        "## 평가 기준",
        "",
        "- **naturalness**: 한국 개인 투자자가 읽을 때 어색함 없이 자연스럽게 흘러가는가?",
        "  - 1: 기계 번역 같음 / 3: 무난 / 5: 사람이 쓴 것처럼 자연스러움",
        "- **insight**: 포트폴리오 지표(분산/섹터/리스크 집중)를 의미 있게 해석하는가?",
        "  - 1: 숫자만 나열 / 3: 기본 해석만 / 5: 지표 간 관계 + preset 의도 + 행동 시사점 명확",
        "",
        "---",
        "",
    ]

    for eval_id, (orig_idx, entry) in enumerate(indexed, start=1):
        model_label = entry.get("model_label", "unknown")
        preset_id = entry.get("preset_id", "unknown")
        fixture = entry.get("fixture", "unknown")
        v_label = _v_prefix(fixture)
        parsed = entry.get("parsed") or {}
        commentary = _format_commentary(parsed)

        key_map[str(eval_id)] = {
            "original_idx": orig_idx,
            "provider": model_label,         # haiku / sonnet
            "preset_id": preset_id,           # garp / quality_factor / ...
            "v_label": v_label,               # V1~V5
            "fixture": fixture,
            "expected_alignment": entry.get("expected_alignment"),
        }

        lines.extend([
            f"## Eval #{eval_id} (preset={preset_id} | {v_label})",
            "",
            commentary,
            "",
            "- naturalness: [   ] / 5",
            "- insight:     [   ] / 5",
            "",
            "---",
            "",
        ])

    EVAL_FORM_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVAL_FORM_PATH.write_text("\n".join(lines), encoding="utf-8")
    EVAL_KEY_PATH.write_text(
        json.dumps(key_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✓ eval form: {EVAL_FORM_PATH} ({len(indexed)} entries)")
    print(f"✓ blind key: {EVAL_KEY_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
