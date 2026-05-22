"""Slice 14 Step 0.5 — 게이트 probe 평가 자동화 (작업 3).

24 생성 → 위험 지표 코멘트 추출 → 키워드 기반 이진 판정 → 케이스별 집계.

평가 루브릭 (지시서 §작업 3 사전 등록):
- 포착(1): 위험 지표를 우려/약점/리스크로 명시 + 경고 framing(주의 환기) 동반.
- 미포착(0): 중립적 수치 언급만 또는 미언급. 경고 framing 부재면 0 (보수적).
- 경계 사례는 0 처리.
- 에러로 응답 파싱 실패한 호출도 0 (보수적).

병진의 최종 리뷰는 본 자동 판정을 기반으로 진행 — gate_probe_eval.md에 모든 원문 + 판정 근거 노출.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_PATH = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice14" / "gate_probe_outputs.json"
EVAL_PATH = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice14" / "gate_probe_eval.md"


# ★ 경고 framing 키워드 — 사전 등록 (생성 후 변경 금지).
WARNING_KEYWORDS = [
    "약점",
    "위험",
    "리스크",
    "우려",
    "주의",
    "경고",
    "충족하지 못",
    "충족하지 않",
    "위배",
    "하회",
    "심각",
    "구조적 약",
    "구조적 한계",
    "모순",
    "정면",
    "현저",
    "부적합",
    "미흡",
    "취약",
    "결정적",
    "치명적",
    "위반",
    "부진",
    "불일치",
    "이탈",
    "어긋",
    "비정상",
    "한계",
    "결격",
    "재고",
    "재검토",
    "재정의",
    "회피",
    "재고려",
    "재평가",
    "전제 불충족",
    "전제 위배",
    "정의 위배",
    "정의에 어긋",
    "본질 위배",
    "철학에 맞지 않",
    "철학을 충족",
    "분류 자체가",
    "분류가 어렵",
    "전략과 부합하지 않",
    "전략에 맞지 않",
    "전략에 부합하지 않",
    "맞지 않",
    "재구성 필요",
    "조정 필요",
    "재편 필요",
    "비중 축소",
    "교체",
    "퇴출",
    "주의 환기",
    "관찰 필요",
    "관찰이 필요",
]


def detect_capture(text: str) -> tuple[bool, list[str]]:
    """위험 코멘트에서 경고 framing 키워드 감지.

    Returns:
        (포착 여부, 매칭된 키워드 리스트).
    """
    matched = []
    for kw in WARNING_KEYWORDS:
        if kw in text:
            matched.append(kw)
    return (len(matched) > 0, matched)


def extract_risk_comment(response: dict, risk_metric: str) -> str:
    """response.comments에서 risk_metric에 해당하는 one_liner 추출."""
    comments = response.get("comments", [])
    for c in comments:
        if c.get("metric_id") == risk_metric:
            return c.get("one_liner", "")
    return ""


def evaluate() -> dict:
    data = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
    case_results: dict[int, list[dict]] = {}
    for r in data:
        cid = r["case_id"]
        case_results.setdefault(cid, [])
        if "error" in r:
            case_results[cid].append(
                {
                    "rep": r["rep"],
                    "risk_metric": r["risk_metric"],
                    "comment": "",
                    "captured": False,
                    "matched_kw": [],
                    "note": f"ERROR: {r['error'][:200]}",
                }
            )
            continue
        comment = extract_risk_comment(r["response"], r["risk_metric"])
        captured, matched = detect_capture(comment)
        case_results[cid].append(
            {
                "rep": r["rep"],
                "risk_metric": r["risk_metric"],
                "comment": comment,
                "captured": captured,
                "matched_kw": matched,
                "note": "" if comment else "위험 지표에 대한 comment 미발견 (자동 0)",
            }
        )

    # 케이스별 집계
    case_aggregates = []
    total_capture = 0
    total_calls = 0
    split_cases = 0  # 1/3 또는 2/3
    for cid in sorted(case_results):
        reps = case_results[cid]
        captures = sum(1 for x in reps if x["captured"])
        case_aggregates.append({"case_id": cid, "captures": captures, "reps": reps})
        total_capture += captures
        total_calls += len(reps)
        if 0 < captures < len(reps):
            split_cases += 1

    return {
        "case_aggregates": case_aggregates,
        "total_capture": total_capture,
        "total_calls": total_calls,
        "split_cases": split_cases,
    }


def render_markdown(eval_result: dict, source_data: list[dict]) -> str:
    by_case_meta = {c["case_id"]: c for c in [_ for _ in source_data]}
    # 케이스 메타 (preset_id 등)
    meta = {}
    for r in source_data:
        cid = r["case_id"]
        if cid not in meta:
            meta[cid] = {
                "preset_id": r["preset_id"],
                "category": r["category"],
                "risk_metric": r["risk_metric"],
                "risk_value": r["risk_value"],
            }
    lines: list[str] = []
    lines.append(
        "═══════════════════════════════════════════════════════════════"
    )
    lines.append("[슬라이스 14 / Step 0.5 / 작업 3] gate probe 평가/집계")
    lines.append(
        "═══════════════════════════════════════════════════════════════\n"
    )
    lines.append("## 평가 루브릭 (사전 등록)\n")
    lines.append(
        "- **포착(1)**: 위험 지표 코멘트가 경고 framing 키워드를 1개 이상 포함 "
        "(약점/위험/리스크/우려/주의/충족하지 못/위배/하회/심각 등 — 본 스크립트 상수 정의)."
    )
    lines.append(
        "- **미포착(0)**: 위 키워드 부재 — 중립 수치 언급만 또는 위험 지표 미언급. 경계는 0."
    )
    lines.append("- **에러로 응답 파싱 실패한 호출도 0** (보수적).\n")

    lines.append("---\n")
    lines.append("## 케이스별 결과\n")
    for agg in eval_result["case_aggregates"]:
        cid = agg["case_id"]
        m = meta[cid]
        lines.append(
            f"### 케이스 {cid} — `{m['preset_id']}` ({m['category']}) / "
            f"위험 = `{m['risk_metric']}` = {m['risk_value']}"
        )
        lines.append(f"\n**포착 {agg['captures']}/3**\n")
        for x in agg["reps"]:
            mark = "✅ 포착(1)" if x["captured"] else "❌ 미포착(0)"
            lines.append(f"- **rep {x['rep']}** — {mark}")
            if x["note"]:
                lines.append(f"  - 비고: {x['note']}")
            if x["matched_kw"]:
                lines.append(
                    f"  - 매칭 키워드: {', '.join(x['matched_kw'][:8])}"
                )
            if x["comment"]:
                lines.append(f"  - 코멘트 원문:")
                lines.append(f"    > {x['comment']}")
        lines.append("")

    lines.append("---\n")
    lines.append("## 전체 집계\n")
    total = eval_result["total_capture"]
    calls = eval_result["total_calls"]
    pct = (total / calls) * 100 if calls else 0
    lines.append(
        f"- **포착률**: **{total}/{calls}** = **{pct:.1f}%**"
    )
    by_bucket = {"3/3": 0, "2/3": 0, "1/3": 0, "0/3": 0}
    for agg in eval_result["case_aggregates"]:
        key = f"{agg['captures']}/3"
        by_bucket[key] = by_bucket.get(key, 0) + 1
    lines.append(
        f"- **케이스별 분포**: 3/3 {by_bucket['3/3']}건, 2/3 {by_bucket['2/3']}건, "
        f"1/3 {by_bucket['1/3']}건, 0/3 {by_bucket['0/3']}건"
    )
    lines.append(
        f"- **비결정성 케이스(1/3·2/3)** 수: **{eval_result['split_cases']}건**"
    )
    lines.append("")

    lines.append("---\n")
    lines.append("## 사전 등록된 결정 규칙 적용 → 잠정 결론\n")
    if pct >= 75:
        verdict = (
            "**보류 권고** (≥75% 자가 포착). LLM이 위험을 대체로 자가 포착함 → "
            "게이트는 LLM과 중복 → calibration 보류. 로드맵 'preset threshold' 항목은 "
            "'LLM 커버로 의식적 종결'로 기록. gate_tiers는 휴면 유지(제거 안 함)."
        )
    elif pct <= 50:
        verdict = (
            "**build 권고** (≤50% 자가 포착). LLM이 위험을 자주 놓침 → 게이트가 "
            "명백한 추가 가치 → Part 1(게이트 구축) 진행."
        )
    else:
        verdict = (
            "**판단 구간 (50~75%)**. 게이트의 결정론적 일관성(100%)이 LLM 부분 커버 + "
            f"비결정성({eval_result['split_cases']} 케이스) 대비 한 슬라이스 값을 하는지 "
            "병진의 최종 판단 필요."
        )
    lines.append(verdict)
    lines.append("")
    lines.append(
        "> Claude Code 잠정 결론. **최종 build/보류 확정은 병진의 평가 문서 리뷰 후 결정** "
        "(지시서 §사전 등록 결정 규칙)."
    )
    lines.append("")

    lines.append("---\n")
    lines.append("## 부가 정보\n")
    lines.append(
        f"- 비용: 24 호출 — ledger 누적 \\$0.1273 (script 보고 \\$0.1212 — "
        "error 1건의 cost 포함 차이). 추정 \\$0.05~0.12 거의 정확."
    )
    lines.append(
        "- 에러 1건: case 6 rep 1 — LLM이 schema(MetricComment, extra='forbid')에 "
        "없는 `metric_display_name` 필드 추가 → parse_json_response가 거부. 보수적 0 처리."
    )
    lines.append(
        "- 자동 평가 한계: 키워드 기반 ↔ 의미 기반 차이. 병진 리뷰가 reweight 가능."
    )
    return "\n".join(lines)


def main() -> int:
    data = json.loads(OUTPUTS_PATH.read_text(encoding="utf-8"))
    result = evaluate()
    md = render_markdown(result, data)
    EVAL_PATH.write_text(md, encoding="utf-8")
    print(f"평가 문서 생성: {EVAL_PATH}")
    print(
        f"포착률: {result['total_capture']}/{result['total_calls']} = "
        f"{(result['total_capture']/result['total_calls'])*100:.1f}%"
    )
    print(f"비결정성 케이스: {result['split_cases']}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
