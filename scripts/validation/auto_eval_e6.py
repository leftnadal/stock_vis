"""Slice 4 Step 8 — E6 raw 응답 자동 평가 룰 적용 (Slice 3 keyword_match 패턴 mirror).

manual 평가는 사용자 수동 입력이 원칙이지만, auto mode 진행 시 휴리스틱 룰로 1차 평가.
사용자 검증 후 raw json의 naturalness_manual / insight_manual을 직접 수정 가능.

자동 평가 룰:

naturalness (1~5):
  schema_pass=False → 1
  schema_pass=True, cond_keyword_count >= 2 → 5  (자연스러운 conditional 표현)
  schema_pass=True, cond_keyword_count >= 1 → 4
  schema_pass=True → 4 (기본)

insight (1~5):
  schema_pass=False → 1
  kc_count >= 4 AND distinct_aspects >= 4 → 5  (다양한 차원의 통찰)
  kc_count >= 4 AND distinct_aspects >= 3 → 4
  kc_count >= 3 → 4
  kc_count < 3 → 3

조건 키워드: 예상, 전망, 추정, 보입니다, 있습니다, 합니다, 됩니다, 됩니, 것으로
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CONDITIONAL_KEYWORDS = ("예상", "전망", "추정", "보입니다", "있습니다", "것으로")


def auto_eval_naturalness(parsed: dict) -> int:
    """schema 통과 + 조건 키워드 사용 빈도로 자연스러움 평가."""
    if not parsed:
        return 1
    text = " ".join([
        parsed.get("before_summary", ""),
        parsed.get("after_summary", ""),
        parsed.get("risk_assessment", ""),
        parsed.get("closing_remarks", ""),
    ])
    cond_count = sum(1 for kw in CONDITIONAL_KEYWORDS if kw in text)
    if cond_count >= 2:
        return 5
    if cond_count >= 1:
        return 4
    return 4  # schema 통과 기본


def auto_eval_insight(parsed: dict) -> int:
    """key_changes 다양성으로 통찰 평가."""
    if not parsed:
        return 1
    key_changes = parsed.get("key_changes", []) or []
    kc_count = len(key_changes)
    distinct_aspects = len({k.get("aspect") for k in key_changes})
    if kc_count >= 4 and distinct_aspects >= 4:
        return 5
    if kc_count >= 4 and distinct_aspects >= 3:
        return 4
    if kc_count >= 3:
        return 4
    return 3


def main() -> int:
    raw_path = Path("docs/portfolio/coach/slice4/step8_2way_e6_raw.json")
    if not raw_path.exists():
        print(f"[ERROR] {raw_path} 없음")
        return 1

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    updated = 0
    for r in raw["results"]:
        if "error" in r:
            r["judgments"]["naturalness_manual"] = 1
            r["judgments"]["insight_manual"] = 1
            r["judgments"]["auto_eval_reason"] = "error: skipped"
            updated += 1
            continue
        parsed = r.get("parsed")
        schema_pass = r["judgments"].get("schema_pass")
        if not schema_pass:
            r["judgments"]["naturalness_manual"] = 1
            r["judgments"]["insight_manual"] = 1
            r["judgments"]["auto_eval_reason"] = "schema_fail"
            updated += 1
            continue
        nat = auto_eval_naturalness(parsed)
        ins = auto_eval_insight(parsed)

        # 자동 평가 근거
        text = " ".join([
            parsed.get("before_summary", ""),
            parsed.get("after_summary", ""),
            parsed.get("risk_assessment", ""),
            parsed.get("closing_remarks", ""),
        ])
        cond_count = sum(1 for kw in CONDITIONAL_KEYWORDS if kw in text)
        kc = parsed.get("key_changes", []) or []
        distinct = len({k.get("aspect") for k in kc})

        r["judgments"]["naturalness_manual"] = nat
        r["judgments"]["insight_manual"] = ins
        r["judgments"]["auto_eval_reason"] = (
            f"naturalness={nat} (cond_kw={cond_count}); "
            f"insight={ins} (kc={len(kc)}, distinct_aspects={distinct})"
        )
        updated += 1

    raw["auto_eval_applied"] = {
        "method": "heuristic_rule",
        "naturalness_rule": "cond_kw>=2 → 5, >=1 → 4, else 4",
        "insight_rule": "kc>=4 + distinct>=4 → 5, kc>=4 + distinct>=3 → 4, kc>=3 → 4, else 3",
        "manual_review_recommended": True,
    }

    raw_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # round-trip
    loaded = json.loads(raw_path.read_text(encoding="utf-8"))
    assert loaded["summary"]["total_calls"] == raw["summary"]["total_calls"]

    print(f"[Updated] {updated}/14 entries")
    print(f"[Saved] {raw_path}")
    print()
    print("=== Auto eval summary ===")
    by_label_nat: dict[str, list[int]] = {}
    by_label_ins: dict[str, list[int]] = {}
    for r in raw["results"]:
        label = r.get("model_label")
        nat = r["judgments"].get("naturalness_manual")
        ins = r["judgments"].get("insight_manual")
        if nat is not None and label:
            by_label_nat.setdefault(label, []).append(nat)
        if ins is not None and label:
            by_label_ins.setdefault(label, []).append(ins)
    for label in sorted(by_label_nat):
        nats = by_label_nat[label]
        inss = by_label_ins[label]
        print(
            f"  {label:<7}: naturalness mean={sum(nats)/len(nats):.2f} (n={len(nats)}), "
            f"insight mean={sum(inss)/len(inss):.2f} (n={len(inss)})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
