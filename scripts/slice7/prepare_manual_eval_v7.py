"""Slice 7 Part 4 §6: 통합 manual eval form 생성 (38 entries, blind).

Slice 5 + Slice 6 + Slice 7 entries → 2 stage 분리 blind 평가 양식.
각 entry에 rationale + reference + metadata 첨부.

seed=42 randomize 재현 가능. eval form은 provider/preset/source_slice 모두 가리고
번호만 표시 (key.json에 매핑 보존).

사용:
  poetry run python -m scripts.slice7.prepare_manual_eval_v7
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from scripts.slice7._common import extract_answer, load_raw

ROOT = Path(__file__).resolve().parents[2]
RATIONALES_PATH = ROOT / "docs/portfolio/coach/slice7/step9_1_rationales.json"
METADATA_PATH = ROOT / "docs/portfolio/coach/slice7/step9_2_auto_metadata.json"
REFERENCES_PATH = ROOT / "docs/portfolio/coach/slice7/step9_3_reference_pairs.json"
RAW_PATHS = {
    "slice5": ROOT / "docs/portfolio/coach/slice5/step8_2way_e3_raw.json",
    "slice6": ROOT / "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json",
    "slice7": ROOT / "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json",
}
OUT_FORM = ROOT / "docs/portfolio/coach/slice7/step9_4_eval_form_v7.md"
OUT_KEY = ROOT / "docs/portfolio/coach/slice7/step9_4_eval_key_v7.json"


def _is_haiku(provider: str | None) -> bool:
    return bool(provider and "haiku" in str(provider).lower())


def _is_sonnet(provider: str | None) -> bool:
    return bool(provider and "sonnet" in str(provider).lower())


def _provider_label(entry: dict, source_slice: str) -> str:
    if source_slice == "slice7":
        return str(entry.get("provider") or "")
    return str(entry.get("model_label") or "")


def _render_entry(eval_id: int, e: dict, lines: list[str]) -> None:
    # provider/preset/source_slice 모두 가린다 (blind)
    lines.append(f"## Eval #{eval_id}")
    lines.append(f"\n**답변**:\n```\n{e['answer']}\n```")
    rationale = e.get("rationale") or {}
    if rationale:
        nat_r = rationale.get("naturalness_rationale") or "—"
        ins_r = rationale.get("insight_rationale") or "—"
        lines.append("\n**Rationale (sonnet 비평)**:")
        lines.append(f"- naturalness: {nat_r}")
        lines.append(f"- insight: {ins_r}")
    metadata = e.get("metadata") or {}
    if metadata:
        lines.append("\n**Auto Metadata**:")
        lines.append(f"- metric_citation_accuracy: {metadata.get('metric_citation_accuracy', '—')}")
        lines.append(f"- preset_intent_keyword_count: {metadata.get('preset_intent_keyword_count', '—')}")
        lines.append(
            f"- answer_length: {metadata.get('answer_length', '—')} "
            f"(z={metadata.get('answer_length_zscore', '—')})"
        )
        lines.append(f"- referenced_metrics_count: {metadata.get('referenced_metrics_count', '—')}")
    lines.append("\n- naturalness: [ ? ] / 5")
    lines.append("- insight: [ ? ] / 5")
    lines.append("- note (선택): ")
    lines.append("\n---\n")


def main() -> int:
    if not RATIONALES_PATH.exists() or not METADATA_PATH.exists() or not REFERENCES_PATH.exists():
        print(
            "⚠ 의존 파일 부족 — Phase B (generate_rationale) + §4/§5 스크립트 먼저 실행",
            file=sys.stderr,
        )
        return 1

    rationales = {
        f"{r['source_slice']}_{r['idx']}": r
        for r in json.loads(RATIONALES_PATH.read_text(encoding="utf-8"))
    }
    metadatas = {
        f"{m['source_slice']}_{m['idx']}": m
        for m in json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    }
    references = json.loads(REFERENCES_PATH.read_text(encoding="utf-8"))

    all_entries: list[dict] = []
    for slice_name, path in RAW_PATHS.items():
        items = load_raw(path)
        for i, e in enumerate(items):
            r_key = f"{slice_name}_{i}"
            all_entries.append({
                "source_slice": slice_name,
                "idx": i,
                "preset_id": e.get("preset_id"),
                "tier": e.get("tier"),
                "provider": _provider_label(e, slice_name),
                "answer": extract_answer(e, slice_name),
                "rationale": rationales.get(r_key, {}),
                "metadata": metadatas.get(r_key, {}),
            })

    # seed=42 randomize (provider blind)
    random.Random(42).shuffle(all_entries)

    haiku_entries = [e for e in all_entries if _is_haiku(e["provider"])]
    sonnet_entries = [e for e in all_entries if _is_sonnet(e["provider"])]

    # blind key (eval_id → 원본 매핑)
    key_map: dict[str, list[dict]] = {"haiku_stage1": [], "sonnet_stage2": []}
    for i, e in enumerate(haiku_entries, 1):
        key_map["haiku_stage1"].append({
            "eval_id": i,
            "source_slice": e["source_slice"],
            "idx": e["idx"],
            "provider": e["provider"],
            "preset_id": e["preset_id"],
            "tier": e["tier"],
        })
    for i, e in enumerate(sonnet_entries, 1):
        key_map["sonnet_stage2"].append({
            "eval_id": i,
            "source_slice": e["source_slice"],
            "idx": e["idx"],
            "provider": e["provider"],
            "preset_id": e["preset_id"],
            "tier": e["tier"],
        })

    lines = [
        "# Slice 7 Part 4 Manual Eval Form (v7)\n",
        "> **방법론 업그레이드 (#1=A의 A+C+D)**: rationale + reference + metadata 제공",
        "> **2 stage**: Stage 1 = haiku (이 문서 §Stage 1) / Stage 2 = sonnet (조건부, §Stage 2)",
        "> **분포 폭 KPI**: rubric §C.6 자동 게이트 (≥ 3.0 필수)",
        "> **참조**: rubric §B.1 sample 5건 (평가 전 반드시 검토)\n",
        "## Reference Examples (rubric §B.1 압축)\n",
    ]
    for name, ref in references.items():
        lines.append(f"- **{name}** ({ref['score']}): {ref['summary']} — 신호: {ref['key_signal']}")
    lines.append("\n---\n")

    lines.append("# Stage 1 — haiku 평가 (먼저 진행)\n")
    for i, e in enumerate(haiku_entries, 1):
        _render_entry(i, e, lines)

    lines.append("\n# Stage 2 — sonnet 평가 (조건부, score_stage1 verdict='proceed' 시)\n")
    for i, e in enumerate(sonnet_entries, 1):
        _render_entry(i, e, lines)

    OUT_FORM.write_text("\n".join(lines), encoding="utf-8")
    OUT_KEY.write_text(json.dumps(key_map, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✓ eval form: {OUT_FORM}")
    print(f"✓ eval key:  {OUT_KEY}")
    print(f"  Stage 1 (haiku):  {len(haiku_entries)} entries")
    print(f"  Stage 2 (sonnet): {len(sonnet_entries)} entries (조건부)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
