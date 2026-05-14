"""Slice 7 Part 4 §4: 자동 metadata 계산.

평가자가 정량 신호로 cross-check할 수 있도록 metadata 계산:
  - metric_citation_accuracy: referenced_metrics가 portfolio_metrics 실재 키인가? (I4 진단)
  - preset_intent_keyword_count: 답변에 preset 키워드 포함 수 (휴리스틱)
  - answer_length: 답변 길이
  - answer_length_zscore: 분포 내 z-score
  - referenced_metrics_count: 인용 지표 수

사용:
  poetry run python -m scripts.slice7.calc_auto_metadata
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean, stdev

from scripts.slice7._common import (
    extract_answer,
    load_raw,
    portfolio_metrics_keys,
    referenced_metrics,
)


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "docs/portfolio/coach/slice7/step9_1_rationales.json"
RAW_PATHS = {
    "slice5": ROOT / "docs/portfolio/coach/slice5/step8_2way_e3_raw.json",
    "slice6": ROOT / "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json",
    "slice7": ROOT / "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json",
}
OUT_PATH = ROOT / "docs/portfolio/coach/slice7/step9_2_auto_metadata.json"


# preset 키워드 매핑 (1차 휴리스틱 — Slice 8 #24에서 일반화 예정)
PRESET_KEYWORDS = {
    "garp": ["garp", "균형", "합리적 가격", "성장과 가치"],
    "buffett_quality_value": ["buffett", "가치", "고품질", "moat", "roic", "fcf"],
    "dividend_growth": ["배당", "dividend", "안정", "방어", "현금흐름"],
    "quality_factor": ["quality", "roic", "수익성", "안정 이익"],
    "concentrated_value": ["집중", "high conviction", "확신", "buffett"],
    "concentrated_portfolio": ["집중", "concentration"],
}


def count_preset_keywords(text: str, preset_id: str) -> int:
    text_lower = text.lower()
    preset_lower = (preset_id or "").lower()
    keywords: list[str] = []
    for k, v in PRESET_KEYWORDS.items():
        if k in preset_lower:
            keywords = v
            break
    if not keywords:
        return 0
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def _build_raw_index() -> dict:
    """(source_slice, idx) → raw entry."""
    index: dict = {}
    for slice_name, path in RAW_PATHS.items():
        for i, e in enumerate(load_raw(path)):
            index[(slice_name, i)] = e
    return index


def main() -> int:
    if not INPUT_PATH.exists():
        print(f"⚠ {INPUT_PATH} 미존재 — Phase B (generate_rationale.py) 먼저 실행", file=sys.stderr)
        return 1
    rationales = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    raw_index = _build_raw_index()

    # 답변 길이 분포
    lengths: list[int] = []
    for r in rationales:
        key = (r.get("source_slice"), r.get("idx"))
        raw = raw_index.get(key)
        if not raw:
            continue
        lengths.append(len(extract_answer(raw, r.get("source_slice", ""))))

    avg_len = mean(lengths) if lengths else 0
    std_len = stdev(lengths) if len(lengths) > 1 else 1

    metadatas: list[dict] = []
    for r in rationales:
        slice_name = r.get("source_slice", "")
        key = (slice_name, r.get("idx"))
        raw = raw_index.get(key) or {}
        answer = extract_answer(raw, slice_name)
        portfolio_keys = portfolio_metrics_keys(raw)
        referenced = referenced_metrics(raw, slice_name)

        if referenced and portfolio_keys:
            valid = sum(1 for m in referenced if m in portfolio_keys)
            citation_accuracy = round(valid / len(referenced), 2)
        else:
            citation_accuracy = None

        preset_match = count_preset_keywords(answer, r.get("preset_id", ""))
        z = round((len(answer) - avg_len) / std_len, 2) if std_len else 0

        metadatas.append({
            "idx": r.get("idx"),
            "source_slice": slice_name,
            "scenario_id": r.get("scenario_id"),
            "preset_id": r.get("preset_id"),
            "tier": r.get("tier"),
            "provider": r.get("provider"),
            "metric_citation_accuracy": citation_accuracy,
            "preset_intent_keyword_count": preset_match,
            "answer_length": len(answer),
            "answer_length_zscore": z,
            "referenced_metrics_count": len(referenced),
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(metadatas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ auto metadata: {OUT_PATH}")
    print(f"  분포: avg_length={avg_len:.0f}, std_length={std_len:.0f}, n={len(metadatas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
