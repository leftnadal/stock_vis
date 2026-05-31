"""Slice 12 Step 0b — #59 E3 action measurability micro-matrix (4 케이스).

E3 진입점 × 2 모델 (haiku, sonnet) × 2 반복 = 4 케이스.
portfolio_a2 fixture로 E3 prompt + LLM 호출 + schema validate + actionability 분석.

목적:
  - Slice 11 Part 5 E3 NG ratio 50% (2/4) → 운영 기준 < 30% 목표
  - prompt 보강 효과 검증

측정:
  - actual input_tokens, output_tokens, cost, latency
  - schema_fitting_pass (Slice 12 #58 보강 효과로 100% 예상)
  - action_items 개수 + 각 priority/category
  - 자동 NG 판정 (구체성 + 측정가능성 휴리스틱)

Output:
  - docs/portfolio/coach/slice12/step0b_59_micro_matrix.json
  - docs/portfolio/coach/slice12/step0b_59_micro_matrix.md
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import anthropic
from dotenv import load_dotenv

load_dotenv()

OUT_JSON = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice12" / "step0b_59_micro_matrix.json"
OUT_MD = REPO_ROOT / "docs" / "portfolio" / "coach" / "slice12" / "step0b_59_micro_matrix.md"

# 금지 패턴 (단독 사용 시 NG 신호)
FORBIDDEN_SINGLE_PATTERNS = ["모니터링 필요", "검토하세요", "주시하세요"]
# 측정 가능성 키워드 (수치/비율/기간)
MEASURABLE_KEYWORDS = [
    re.compile(r"\d+\.?\d*\s*%"),       # 25%, 0.5%
    re.compile(r"\d+\.?\d*\s*→\s*\d+"),  # 25% → 15%
    re.compile(r"\d+개"),                # 3개, 5개
    re.compile(r"\d+주|\d+분기|\d+개월|\d+년|당분기|현재 분기|다음 리밸런싱"),  # 시간
    re.compile(r"HHI\s*\d+\.?\d*"),     # HHI 0.21
    re.compile(r"비중\s*\d"),            # 비중 20
]


def _action_specificity_check(action: dict, holdings_tickers: list[str]) -> dict:
    """단일 action_item의 구체성/측정 가능성 휴리스틱 평가."""
    desc = action.get("description", "")
    title = action.get("title", "")
    blob = f"{title} {desc}"

    # 구체성: ticker 인용 또는 정량 지표 또는 비율 인용
    has_ticker = any(t.upper() in blob for t in holdings_tickers)
    has_quant = any(p.search(blob) for p in MEASURABLE_KEYWORDS)
    specificity_ok = has_ticker or has_quant

    # 측정 가능성: 수치/기한 키워드
    measurability_ok = has_quant

    # 금지 패턴 단독 (수치 없이 사용)
    has_forbidden_single = False
    for pat in FORBIDDEN_SINGLE_PATTERNS:
        if pat in blob and not has_quant:
            has_forbidden_single = True
            break

    # NG 판정 (3 조건 중 2개 이상 미달)
    score = sum([specificity_ok, measurability_ok, not has_forbidden_single])
    actionability = "OK" if score >= 2 else "NG"

    return {
        "title": title,
        "description": desc[:120],
        "priority": action.get("priority"),
        "category": action.get("category"),
        "has_ticker": has_ticker,
        "has_quant": has_quant,
        "has_forbidden_single": has_forbidden_single,
        "score": score,
        "actionability": actionability,
    }


def _aggregate_case_actionability(actions: list[dict], tickers: list[str]) -> dict:
    """case 단위 actionability: 모든 action_items가 OK면 OK, 하나라도 NG면 NG."""
    if not actions:
        return {"case_actionability": "NG", "reason": "no action_items", "per_action": []}
    per_action = [_action_specificity_check(a, tickers) for a in actions]
    has_ng = any(p["actionability"] == "NG" for p in per_action)
    return {
        "case_actionability": "NG" if has_ng else "OK",
        "ng_count": sum(1 for p in per_action if p["actionability"] == "NG"),
        "ok_count": sum(1 for p in per_action if p["actionability"] == "OK"),
        "per_action": per_action,
    }


def _run_case(model: str, repeat: int, client: anthropic.Anthropic) -> dict:
    """단일 E3 케이스 실행 + actionability 분석."""
    from apps.portfolio.llm.parsers import parse_json_response
    from apps.portfolio.schemas.commentary_output import E3Output
    from apps.portfolio.services.coach.prompt_builder import E3PromptBuilder
    from apps.portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input

    inp = load_portfolio_a2_input("e3")
    holdings_tickers = [h.ticker for h in inp.holdings]
    messages = E3PromptBuilder.build_messages(inp)
    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]
    anth_messages = [{"role": "user", "content": user_prompt}]

    t0 = time.time()
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=system_prompt,
        messages=anth_messages,
    )
    latency_ms = int((time.time() - t0) * 1000)
    actual = int(response.usage.input_tokens)
    out_tok = int(response.usage.output_tokens)
    response_text = "".join(b.text for b in response.content if hasattr(b, "text"))

    if "haiku" in model:
        in_rate, out_rate = 0.80e-6, 4.0e-6
    else:
        in_rate, out_rate = 3.0e-6, 15.0e-6
    cost = actual * in_rate + out_tok * out_rate

    fitting_pass = False
    fitting_error = ""
    parsed_actions = []
    try:
        result = parse_json_response(E3Output, response_text)
        fitting_pass = True
        parsed_actions = [a.model_dump() for a in result.action_items]
    except Exception as e:  # noqa: BLE001
        fitting_error = f"{type(e).__name__}: {str(e)[:200]}"

    actn = _aggregate_case_actionability(parsed_actions, holdings_tickers) if fitting_pass else {
        "case_actionability": "NG",
        "reason": "schema fitting failed",
        "per_action": [],
    }

    return {
        "model": model,
        "model_short": "haiku" if "haiku" in model else "sonnet",
        "repeat": repeat,
        "input_tokens": actual,
        "output_tokens": out_tok,
        "latency_ms": latency_ms,
        "cost_usd": round(cost, 6),
        "schema_fitting_pass": fitting_pass,
        "schema_fitting_error": fitting_error,
        "n_action_items": len(parsed_actions),
        "actionability_analysis": actn,
        "response_text": response_text,
    }


def main() -> int:
    print("=" * 70)
    print("Slice 12 Step 0b — #59 E3 action measurability micro-matrix")
    print("=" * 70)

    client = anthropic.Anthropic()
    cases = []
    total_cost = 0.0

    for repeat in (1, 2):
        for model in ("claude-haiku-4-5", "claude-sonnet-4-5"):
            tag = f"e3/{model[7:13]}/#{repeat}"
            print(f"\n--- {tag} ---")
            try:
                r = _run_case(model, repeat, client)
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL: {type(e).__name__}: {e}")
                cases.append({
                    "model": model, "repeat": repeat,
                    "error": f"{type(e).__name__}: {e}",
                })
                continue
            cases.append(r)
            total_cost += r["cost_usd"]
            print(f"  fitting: {r['schema_fitting_pass']}")
            print(f"  n_action_items: {r['n_action_items']}")
            print(f"  actionability: {r['actionability_analysis']['case_actionability']}")
            print(f"  ng/ok per action: {r['actionability_analysis'].get('ng_count', '-')}"
                  f"/{r['actionability_analysis'].get('ok_count', '-')}")
            print(f"  cost: ${r['cost_usd']:.5f}, latency: {r['latency_ms']}ms")

    # NG ratio
    fitting_pass = [c for c in cases if c.get("schema_fitting_pass")]
    ng_cases = [c for c in fitting_pass if c["actionability_analysis"]["case_actionability"] == "NG"]
    ng_ratio = len(ng_cases) / len(fitting_pass) * 100 if fitting_pass else 100.0

    summary = {
        "n_cases": len(cases),
        "n_fitting_pass": len(fitting_pass),
        "n_ng": len(ng_cases),
        "ng_ratio_pct": round(ng_ratio, 2),
        "total_cost_usd": round(total_cost, 6),
        "slice11_part5_e3_ng_ratio_pct": 50.0,  # baseline
        "target_ng_ratio_pct": 30.0,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"summary": summary, "cases": cases}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # MD
    lines = [
        "# Slice 12 Step 0b — #59 E3 micro-matrix (4 케이스)",
        "",
        "## §1. Summary",
        "",
        f"- 케이스 실행: **{summary['n_cases']}/4**",
        f"- schema fitting PASS: **{summary['n_fitting_pass']}/{summary['n_cases']}**",
        f"- NG case 수: **{summary['n_ng']}/{summary['n_fitting_pass']}**",
        f"- **NG ratio: {summary['ng_ratio_pct']}%** (Slice 11 Part 5 baseline 50% → 목표 < 30%)",
        f"- 총 비용: ${summary['total_cost_usd']:.4f}",
        "",
        "## §2. 케이스별 분석",
        "",
        "| # | model | rep | fit | n_items | NG/OK actions | case actn | cost | latency |",
        "| - | ----- | --- | --- | ------- | ------------- | --------- | ---- | ------- |",
    ]
    for i, c in enumerate(cases, 1):
        if c.get("error"):
            lines.append(f"| {i} | {c.get('model','?')} | #{c.get('repeat','?')} | ERR | - | - | - | - | - |")
            continue
        actn = c["actionability_analysis"]
        lines.append(
            f"| {i} | {c['model_short']} | #{c['repeat']} | "
            f"{'P' if c['schema_fitting_pass'] else 'F'} | "
            f"{c['n_action_items']} | "
            f"{actn.get('ng_count','-')}/{actn.get('ok_count','-')} | "
            f"{actn['case_actionability']} | "
            f"${c['cost_usd']:.5f} | {c['latency_ms']}ms |"
        )

    lines += [
        "",
        "## §3. action_items 상세 (NG 판정 근거)",
        "",
    ]
    for i, c in enumerate(cases, 1):
        if c.get("error") or not c.get("schema_fitting_pass"):
            continue
        lines.append(f"### Case {i} — {c['model_short']}/#{c['repeat']}")
        lines.append("")
        for j, p in enumerate(c["actionability_analysis"]["per_action"], 1):
            lines.append(
                f"- action #{j} [{p['actionability']}] **{p['title']}** "
                f"(priority={p['priority']}, ticker={p['has_ticker']}, "
                f"quant={p['has_quant']}, forbid_single={p['has_forbidden_single']})"
            )
            lines.append(f"  - desc: {p['description']}")
        lines.append("")

    lines += [
        "",
        "## §4. #59 판정",
        "",
    ]
    if ng_ratio < 30:
        lines.append(f"- **#59 close** (NG ratio {ng_ratio:.1f}% < 30% 운영 기준)")
    elif ng_ratio < 50:
        lines.append(f"- **#59 keep_open** (개선 있으나 운영 기준 미달: 50%→{ng_ratio:.1f}%)")
    else:
        lines.append(f"- **#59 escalate** (NG ratio {ng_ratio:.1f}% 보강 효과 없음)")
    lines.append("")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"종료: {len(cases)}/4 cases, NG ratio {ng_ratio:.1f}%, 총 비용 ${total_cost:.4f}")
    print(f"→ {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"→ {OUT_MD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
