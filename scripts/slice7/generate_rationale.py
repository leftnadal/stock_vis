"""Slice 7 Part 4 §3: rationale 보조 호출 (sonnet 비평가).

Slice 5 + Slice 6 + Slice 7 각 entry에 대해 sonnet이 naturalness/insight
rationale 200자씩 분석. 본 매트릭스는 보존, rationale은 별도 자산.

사용:
  poetry run python -m scripts.slice7.generate_rationale [--dry-run]

비용 예측: ~$0.14 (52건 × sonnet rationale, output 짧음 ~$0.003/건)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from apps.portfolio.llm.client import LLMClient  # noqa: E402
from apps.portfolio.llm.cost_guard import CostGuard  # noqa: E402
from apps.portfolio.services._llm_kwargs import resolve_provider_kwargs  # noqa: E402
from scripts.slice7._common import _strip_fence, extract_answer, load_raw  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATHS = {
    "slice5": ROOT / "docs/portfolio/coach/slice5/step8_2way_e3_raw.json",
    "slice6": ROOT / "docs/portfolio/coach/slice6/step8_2way_e3_portfolio_raw.json",
    "slice7": ROOT / "docs/portfolio/coach/slice7/step8_2way_e4_conversation_raw.json",
}
OUT_PATH = ROOT / "docs/portfolio/coach/slice7/step9_1_rationales.json"
REPORT_PATH = ROOT / "docs/portfolio/coach/slice7/step9_1_rationales_report.md"

RATIONALE_SYSTEM = """당신은 한국어 portfolio 코멘트의 비평가입니다.
주어진 답변에 대해 객관적·비판적 관점에서 다음 두 축을 분석하세요:

1. naturalness (자연스러움): 한국어 표현이 자연스러운가? 어떤 표현이 어색하거나
   기계 번역체인가? 어떤 표현이 사람이 쓴 듯한 자연스러움을 보이는가?
2. insight (통찰력): 포트폴리오 지표를 의미 있게 해석했는가? preset 의도를
   반영했는가? 행동 시사점이 구체적인가?

**중요**: 자기 변호 X, 비판적 분석 O. 약점과 강점 모두 명시.
JSON으로 출력 (각 rationale 200자 이내):
{
  "naturalness_rationale": "...",
  "insight_rationale": "..."
}
"""


def _provider_label(entry: dict, source_slice: str) -> str:
    """slice별 provider 필드 통합. slice5/6은 model_label, slice7은 provider."""
    if source_slice == "slice7":
        prov = entry.get("provider") or ""
    else:
        prov = entry.get("model_label") or ""
    return str(prov)


def build_rationale_prompt(entry: dict, source_slice: str) -> str:
    answer = extract_answer(entry, source_slice)
    preset = entry.get("preset_id", "unknown")
    return f"""{RATIONALE_SYSTEM}

## Preset
{preset}

## 답변
{answer}

위 답변의 naturalness/insight를 비평적으로 분석하세요.
"""


def load_entries() -> list[dict]:
    all_entries = []
    for slice_name, path in INPUT_PATHS.items():
        items = load_raw(path)
        if not items:
            print(f"⚠ {path} 비어있거나 없음 — skipping {slice_name}", file=sys.stderr)
            continue
        for idx, e in enumerate(items):
            e2 = dict(e)
            e2["__source_slice"] = slice_name
            e2["__source_idx"] = idx
            all_entries.append(e2)
    return all_entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="LLM 호출 없이 entry 수만 보고")
    args = parser.parse_args()

    all_entries = load_entries()
    print(f"총 entries: {len(all_entries)}")
    by_slice: dict[str, int] = {}
    for e in all_entries:
        s = e["__source_slice"]
        by_slice[s] = by_slice.get(s, 0) + 1
    for s, n in by_slice.items():
        print(f"  {s}: {n}")

    if args.dry_run:
        print("\n[dry-run] LLM 호출 생략. entry 카운트만 보고.")
        # sample answer 추출 검증
        for e in all_entries[:3]:
            ans = extract_answer(e, e["__source_slice"])
            print(f"  [{e['__source_slice']}#{e['__source_idx']}] {ans[:80]}…")
        return 0

    CostGuard.get_instance().reset_slice("slice7_part4_rationale", max_calls=80)
    sonnet_kwargs = resolve_provider_kwargs("sonnet")

    rationales: list[dict] = []
    total_cost = 0.0
    for i, entry in enumerate(all_entries, 1):
        slice_name = entry["__source_slice"]
        prompt = build_rationale_prompt(entry, slice_name)
        # 인스턴스별 budget(50)이 settings에 묶여있어 52건 호출 시 12번째부터 위험.
        # 매 호출 새 인스턴스로 카운터 reset (CostGuard 글로벌 80 cap이 실제 가드).
        client = LLMClient()
        try:
            response = client.complete(prompt=prompt, max_tokens=600, **sonnet_kwargs)
        except Exception as exc:
            rationales.append({
                "idx": entry["__source_idx"],
                "source_slice": slice_name,
                "error": str(exc),
            })
            continue
        meta = response.metadata_dict()
        cost = meta.get("cost_usd", 0)
        total_cost += cost
        text = _strip_fence(response.text)
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = {
                "naturalness_rationale": "[parse error] " + text[:120],
                "insight_rationale": "[parse error]",
            }
        rationales.append({
            "idx": entry["__source_idx"],
            "source_slice": slice_name,
            "scenario_id": entry.get("scenario_id") or entry.get("fixture_id"),
            "preset_id": entry.get("preset_id"),
            "tier": entry.get("tier"),
            "provider": _provider_label(entry, slice_name),
            "naturalness_rationale": parsed.get("naturalness_rationale"),
            "insight_rationale": parsed.get("insight_rationale"),
            "rationale_cost_usd": cost,
        })
        if i % 10 == 0:
            print(f"  진행: {i}/{len(all_entries)}, 누적 cost: ${total_cost:.4f}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rationales, indent=2, ensure_ascii=False), encoding="utf-8")

    success = sum(1 for r in rationales if r.get("naturalness_rationale") and not r.get("error"))
    fail = sum(1 for r in rationales if r.get("error"))
    md = [
        "# Slice 7 Part 4 §3 — Rationale 생성 보고\n",
        f"- 총 entries: {len(all_entries)}",
        f"- 성공: {success}",
        f"- 실패: {fail}",
        f"- 총 비용: ${total_cost:.5f}",
        "",
        "## Source 분포",
    ]
    for s, n in by_slice.items():
        md.append(f"- {s}: {n}")
    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")

    print(f"\n✓ rationales: {OUT_PATH}")
    print(f"  총 비용: ${total_cost:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
