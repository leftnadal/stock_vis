"""Slice 6 Part 1 Step 1 + Part 2 Step A — E3 portfolio prompt builder.

지시서 §2.4 변수 슬롯 7종:
  {preset_id}, {preset_intent}, {holdings_summary},
  {sector_concentration}, {diversification_score},
  {risk_concentration_score}, {core_metrics_summary}

Two modes:
  - **minimal** (Part 1, analysis_context=None): 변수 슬롯만 치환. input ~750 tokens.
  - **reinforced** (Part 2 Step A, analysis_context=dict): system + schema + AnalysisContext
    JSON dump + few-shot 4. input 4,000~6,000 tokens (Slice 5 e3 mirror).

reinforced 모드는 #β2 후속 검증용 — estimator 외삽 능력 확인.
"""

from __future__ import annotations

import json
from typing import Any


# 변수 슬롯 7종 (지시서 §2.4)
PROMPT_VARIABLE_SLOTS: tuple[str, ...] = (
    "preset_id",
    "preset_intent",
    "holdings_summary",
    "sector_concentration",
    "diversification_score",
    "risk_concentration_score",
    "core_metrics_summary",
)


# ============================================================
# Few-shot 4종 (Part 2 Step A — V1/V2/V3/V5 mirror, V4는 test set 다양성 확보)
# ============================================================

FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    # Example 1 — concentrated_balanced (V1 mirror, GARP partial alignment)
    {
        "name": "concentrated_balanced",
        "input": (
            "preset_id=garp / preset_intent=합리적 가격 성장 / "
            "holdings=MSFT(30%), NVDA(20%), AAPL(15%), GOOG(20%), META(15%) / "
            "sector_concentration=Tech 50% / diversification_score=0.35 / "
            "risk_concentration_score=0.45 / "
            "core_metrics: PEG=1.8, EPS_growth=15%, ROIC=18%, revenue_growth=14%, "
            "PE=22, ROE=24%, FCF_yield=3.8%"
        ),
        "output": (
            '{"holistic_assessment":"GARP 관점에서 Tech 5종 집중 포트폴리오로 '
            '성장 모멘텀은 양호하나 단일 섹터 50% 집중이 시장 사이클 노출도를 '
            '확대시키는 구조입니다. PEG 1.8과 EPS 성장 15% 조합은 합리적 가격 '
            '성장 의도와 부합하지만 분산 측면에서 보완 여지가 있습니다.",'
            '"diversification_comment":"분산 점수 0.35는 5종목 집중도 기준 '
            '중간 수준이며 단일 섹터 의존도가 분산 효과를 제한합니다.",'
            '"sector_balance_comment":"Tech 50%로 단일 섹터 비중이 권장 30~40% '
            '상한을 넘어서 섹터 사이클 리스크가 증가합니다.",'
            '"risk_concentration_comment":"집중 리스크 0.45는 변동성 확대 '
            '가능성을 시사하며 GARP 전략의 안정성 기대치 대비 다소 높은 편입니다.",'
            '"preset_alignment":"partial","confidence":4}'
        ),
    },
    # Example 2 — concentrated_misfit (V2 mirror, GARP misalignment)
    {
        "name": "concentrated_misfit",
        "input": (
            "preset_id=garp / preset_intent=합리적 가격 성장 / "
            "holdings=TSLA(40%), PLTR(20%), SHOP(20%), DDOG(10%), SNOW(10%) / "
            "sector_concentration=Tech 80% / diversification_score=0.15 / "
            "risk_concentration_score=0.80 / "
            "core_metrics: PEG=3.2 (well above 1.5), EPS_growth=4% (well below 10%), "
            "ROIC=6% (well below 15%), PE=65 (extreme), ROE=8%, FCF_yield=0.5%"
        ),
        "output": (
            '{"holistic_assessment":"GARP 의도와 크게 어긋난 구성입니다. '
            'PEG 3.2 및 PE 65는 합리적 가격 기준을 크게 상회하고 EPS 성장 4%로 '
            '성장성도 미흡합니다. Tech 80% 극단 집중과 분산 0.15는 GARP의 안정적 '
            '성장 의도와 정면 충돌하는 high-beta growth-at-any-price 패턴을 보입니다.",'
            '"diversification_comment":"분산 점수 0.15는 매우 낮으며 단일 섹터 80% '
            '집중도가 분산 효과를 사실상 무력화합니다.",'
            '"sector_balance_comment":"Tech 80% 극단 집중으로 섹터 균형이 완전히 '
            '무너진 상태이며 단일 섹터 cycle에 portfolio 운명이 종속됩니다.",'
            '"risk_concentration_comment":"집중 리스크 0.80은 변동성 위험이 매우 '
            '높음을 의미하며 GARP의 합리적 위험 수용 의도와 부합하지 않습니다.",'
            '"preset_alignment":"misaligned","confidence":5}'
        ),
    },
    # Example 3 — concentrated_factor (V3 mirror, quality_factor partial)
    {
        "name": "concentrated_factor",
        "input": (
            "preset_id=quality_factor / preset_intent=자본 효율성 + 수익성 quality / "
            "holdings=MSFT(15%), AAPL(12%), GOOG(10%), JNJ(12%), UNH(10%), "
            "PFE(8%), V(8%), MA(7%), ABT(10%), TMO(8%) / "
            "sector_concentration=Tech 52% + Healthcare 48% / "
            "diversification_score=0.25 / risk_concentration_score=0.40 / "
            "core_metrics: ROIC=22%, gross_margin=58%, earnings_quality=0.85, "
            "FCF_yield=4.5%, EPS_stability_5y=0.92, debt_to_equity=0.35, ROA=12%"
        ),
        "output": (
            '{"holistic_assessment":"Quality Factor 의도에 부합하는 고 ROIC + 안정 '
            '이익 종목 10개 구성입니다. 그러나 Tech와 Healthcare 2 섹터에 100% '
            '편중되어 quality factor의 cross-sector 분산 의도와는 부분적으로만 '
            '일치합니다. 수익성 지표(ROIC 22%, gross margin 58%)는 매우 강합니다.",'
            '"diversification_comment":"분산 점수 0.25는 10종목 보유 기준 중간 '
            '하위이며 2 섹터 집중이 분산 효과를 제한합니다.",'
            '"sector_balance_comment":"Tech 52% + Healthcare 48%로 2 섹터 100% '
            '집중되어 quality factor 전반에 대한 cross-sector 노출이 부족합니다.",'
            '"risk_concentration_comment":"집중 리스크 0.40은 중간 수준이며 quality '
            'factor의 낮은 변동성 특성과 부분적으로 부합합니다.",'
            '"preset_alignment":"partial","confidence":4}'
        ),
    },
    # Example 4 — concentrated_income (V5 mirror, dividend_growth aligned)
    {
        "name": "concentrated_income",
        "input": (
            "preset_id=dividend_growth / preset_intent=배당 성장 + 안정 수익 / "
            "holdings=KO(25%), PG(18%), PEP(15%), JNJ(12%), MMM(10%), MO(10%), CL(10%) / "
            "sector_concentration=Consumer Staples 78% / "
            "diversification_score=0.30 / risk_concentration_score=0.35 / "
            "core_metrics: dividend_yield=3.8%, dividend_growth_5y=7.2%, "
            "payout_ratio=62%, EPS_growth=4.5%, ROIC=15%, FCF_coverage=1.8x, "
            "consecutive_dividend_years=25"
        ),
        "output": (
            '{"holistic_assessment":"Dividend Growth 의도와 정합하는 7종 안정 '
            '배당주 portfolio입니다. dividend_yield 3.8% + 5년 성장률 7.2% + '
            '25년 연속 배당 + payout 62% 조합은 배당 안정성과 성장 여력을 모두 '
            '갖춘 이상적 구성입니다. Consumer Staples 78% 편중은 방어적 segment '
            '의도와 일치합니다.",'
            '"diversification_comment":"분산 점수 0.30은 안정 배당 portfolio로서 '
            '적절한 수준이며 7종 보유로 개별 종목 위험이 분산됩니다.",'
            '"sector_balance_comment":"Consumer Staples 78%는 방어적 배당 의도와 '
            '일치하며 배당 안정성을 강화하는 의도적 편중입니다.",'
            '"risk_concentration_comment":"집중 리스크 0.35는 양호한 수준이며 '
            '배당 안정성과 변동성 통제 측면에서 균형이 좋습니다.",'
            '"preset_alignment":"aligned","confidence":5}'
        ),
    },
]


# ============================================================
# System prompt (Part 2 Step A — reinforced 모드)
# ============================================================

SYSTEM_PROMPT = """당신은 한국 개인 투자자를 위한 portfolio 단위 진단 전문가 LLM입니다.

# 역할 정의

당신의 임무는 concentrated portfolio (5~10 holdings, 1~2 섹터 60%+ 집중)의 자연어 진단 \
코멘트를 생성하는 것입니다. 분석 엔진이 사전 산출한 portfolio-level 지표 \
(diversification_score, sector_concentration, risk_concentration_score)와 종목 단위 \
Core 7종 raw 데이터를 받아, 6 필드 JSON 자연어 코멘트로 변환합니다.

## 핵심 제약 (반드시 준수)

1. **정량 재계산 금지**: 분석 엔진이 산출한 점수/비율을 다시 계산하지 마세요. 자연어 평가만 수행합니다.
2. **출력은 JSON only**: 마크다운 펜스, 설명, 사족 일체 금지. 순수 JSON 객체 하나만 출력합니다.
3. **한국어**: 모든 자연어 필드는 한국어로 작성합니다.
4. **preset 의도 우선**: holdings/지표 평가는 항상 preset의 투자 의도와 정합성을 기준으로 합니다.

# 출력 Schema (E3PortfolioCommentary, Pydantic 6 필드)

```json
{
  "holistic_assessment": "포트폴리오 전체 평가 2~3문장. preset 의도 + 핵심 강점/약점 종합. (한국어 30~300자)",
  "diversification_comment": "diversification_score 해석 + 분산 정도 평가 한 줄. (한국어 20~200자)",
  "sector_balance_comment": "sector_concentration 해석 + 섹터 균형 평가 한 줄. (한국어 20~200자)",
  "risk_concentration_comment": "risk_concentration_score 해석 + 집중 리스크 평가 한 줄. (한국어 20~200자)",
  "preset_alignment": "preset 의도와 portfolio의 정합성 (3종 중 1개):\\n  - aligned: 의도와 명확히 일치 (강점이 의도 부합)\\n  - partial: 부분 일치 (일부 강점 일부 어긋남)\\n  - misaligned: 의도와 명백히 충돌 (핵심 지표가 의도 반대 방향)",
  "confidence": "LLM이 평가에 대해 갖는 자신도 (1=낮음, 5=확실). 데이터 충분성과 평가 명확도 기반."
}
```

## 길이 제약

- holistic_assessment: **30~300자** (2~3문장 권장)
- 나머지 3개 comment 필드: **20~200자 각각** (한 줄~한 문단)
- preset_alignment: Literal **aligned | partial | misaligned** 중 정확히 1개
- confidence: int **1~5**

## 평가 기준

| 차원 | 평가 포인트 |
|---|---|
| holistic | preset 의도 + 핵심 지표 강도 + 분산/집중 trade-off |
| diversification | diversification_score 0.0~1.0 (0.4+ = 양호, 0.2~0.4 = 중간, <0.2 = 낮음) |
| sector_balance | sector 60%+ = 의도적 편중 vs 위험 — preset 정합성으로 판단 |
| risk_concentration | risk_concentration_score 0.0~1.0 (0.3- = 양호, 0.3~0.5 = 중간, 0.5+ = 높음) |
| preset_alignment | 핵심 Core 지표가 preset 의도 방향과 일치? |

이제 example 4개를 학습한 후 마지막 portfolio commentary를 생성하세요."""


# ============================================================
# Template (minimal — Part 1)
# ============================================================

MINIMAL_PROMPT_TEMPLATE = """당신은 한국 개인 투자자를 위한 portfolio 단위 진단 전문가입니다.

분석 엔진이 사전 산출한 portfolio-level 지표(분산/섹터/리스크 집중)와 Core 7종 종목 지표를 받아,
6 필드 JSON 자연어 코멘트를 생성합니다. 정량 재계산 없이 자연어 평가만 수행하세요.

## 출력 schema (필수)

```json
{{
  "holistic_assessment": "포트폴리오 전체 평가 2~3문장 (30~300자)",
  "diversification_comment": "분산 정도 한 줄 평가 (20~200자)",
  "sector_balance_comment": "섹터 균형 평가 (20~200자)",
  "risk_concentration_comment": "집중 리스크 평가 (20~200자)",
  "preset_alignment": "aligned | partial | misaligned",
  "confidence": 1~5
}}
```

## Examples

### Example 1 (partial alignment)
Input: {example1_input}
Output: {example1_output}

### Example 2 (aligned)
Input: {example2_input}
Output: {example2_output}

## Now generate portfolio commentary

preset_id: {preset_id}
preset_intent: {preset_intent}
holdings_summary: {holdings_summary}
sector_concentration: {sector_concentration}
diversification_score: {diversification_score}
risk_concentration_score: {risk_concentration_score}
core_metrics_summary: {core_metrics_summary}

Output (JSON only):"""


# ============================================================
# Template (reinforced — Part 2 Step A)
# ============================================================

REINFORCED_PROMPT_TEMPLATE = """{system_prompt}

# Few-shot Examples (4종 — 5 카테고리 cover)

## Example 1 — {example1_name}
Input: {example1_input}
Output: {example1_output}

## Example 2 — {example2_name}
Input: {example2_input}
Output: {example2_output}

## Example 3 — {example3_name}
Input: {example3_input}
Output: {example3_output}

## Example 4 — {example4_name}
Input: {example4_input}
Output: {example4_output}

# AnalysisContext (분석엔진 사전 산출, 정량 재계산 없음)

```json
{analysis_context_dump}
```

# Now generate portfolio commentary

preset_id: {preset_id}
preset_intent: {preset_intent}
holdings_summary: {holdings_summary}
sector_concentration: {sector_concentration}
diversification_score: {diversification_score}
risk_concentration_score: {risk_concentration_score}
core_metrics_summary: {core_metrics_summary}

Output (JSON only):"""


# ============================================================
# Builder
# ============================================================


def build_e3_portfolio_prompt(
    *,
    preset_id: str,
    preset_intent: str,
    holdings_summary: str,
    sector_concentration: str,
    diversification_score: float,
    risk_concentration_score: float,
    core_metrics_summary: str,
    analysis_context: dict[str, Any] | None = None,
) -> str:
    """E3 portfolio prompt 단일 str — minimal 또는 reinforced 모드.

    Args:
        preset_id: preset 식별자 (garp/buffett_quality_value/...).
        preset_intent: preset 의도 자연어 (예: "합리적 가격 성장").
        holdings_summary: 보유 종목 평탄화 요약.
        sector_concentration: 섹터 집중도 (분석엔진 산출).
        diversification_score: 분산 점수 0.0~1.0 (분석엔진).
        risk_concentration_score: 집중 리스크 점수 0.0~1.0 (분석엔진).
        core_metrics_summary: Core 7종 raw 평탄화.
        analysis_context: dict | None.
            None (default) = minimal 모드 (Part 1, input ~750 tokens).
            dict = reinforced 모드 (Part 2 Step A, input 4,000~6,000 tokens):
                system prompt + schema 명세 + AnalysisContext JSON dump + few-shot 4.

    Returns:
        prompt str.
    """
    if analysis_context is None:
        # ===== minimal 모드 (Part 1 backward compatible) =====
        return MINIMAL_PROMPT_TEMPLATE.format(
            example1_input=FEW_SHOT_EXAMPLES[0]["input"],
            example1_output=FEW_SHOT_EXAMPLES[0]["output"],
            example2_input=FEW_SHOT_EXAMPLES[3]["input"],  # V5 (aligned)
            example2_output=FEW_SHOT_EXAMPLES[3]["output"],
            preset_id=preset_id,
            preset_intent=preset_intent,
            holdings_summary=holdings_summary,
            sector_concentration=sector_concentration,
            diversification_score=f"{diversification_score:.2f}",
            risk_concentration_score=f"{risk_concentration_score:.2f}",
            core_metrics_summary=core_metrics_summary,
        )

    # ===== reinforced 모드 (Part 2 Step A) =====
    context_dump = json.dumps(analysis_context, ensure_ascii=False, indent=2, default=str)
    return REINFORCED_PROMPT_TEMPLATE.format(
        system_prompt=SYSTEM_PROMPT,
        example1_name=FEW_SHOT_EXAMPLES[0]["name"],
        example1_input=FEW_SHOT_EXAMPLES[0]["input"],
        example1_output=FEW_SHOT_EXAMPLES[0]["output"],
        example2_name=FEW_SHOT_EXAMPLES[1]["name"],
        example2_input=FEW_SHOT_EXAMPLES[1]["input"],
        example2_output=FEW_SHOT_EXAMPLES[1]["output"],
        example3_name=FEW_SHOT_EXAMPLES[2]["name"],
        example3_input=FEW_SHOT_EXAMPLES[2]["input"],
        example3_output=FEW_SHOT_EXAMPLES[2]["output"],
        example4_name=FEW_SHOT_EXAMPLES[3]["name"],
        example4_input=FEW_SHOT_EXAMPLES[3]["input"],
        example4_output=FEW_SHOT_EXAMPLES[3]["output"],
        analysis_context_dump=context_dump,
        preset_id=preset_id,
        preset_intent=preset_intent,
        holdings_summary=holdings_summary,
        sector_concentration=sector_concentration,
        diversification_score=f"{diversification_score:.2f}",
        risk_concentration_score=f"{risk_concentration_score:.2f}",
        core_metrics_summary=core_metrics_summary,
    )
