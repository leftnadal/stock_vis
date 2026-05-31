"""E6 (조정 후 비교 해설) entry function — Slice 4.

E5 결과(adjustments)와 원본 AnalysisContext를 입력으로 받아 비교 해설
자연어를 생성한다.

핵심 원칙:
- 정량 *재계산 없음*. LLM이 자체 추론하여 자연어 비교만 수행.
- 분석 엔진 의존성 회피 (Phase 2에서 재계산 엔진 별도 슬라이스 추가 예정).
- D2.B 가설 적용 — default provider = haiku (글쓰기 차원).
"""

from __future__ import annotations

from typing import Any

from apps.portfolio.llm import LLMClient
from apps.portfolio.llm.parsers import parse_json_response
from apps.portfolio.schemas.llm import AdjustmentItem, E6Request
from apps.portfolio.schemas.llm_outputs import E6ComparisonResponse
from apps.portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from apps.portfolio.services._prompt_helpers import (
    format_analysis_summary,
    format_holdings_summary,
)

# ============================================================
# 어댑터 helpers
# ============================================================


_ACTION_VERBS: dict[str, str] = {
    "increase": "확대",
    "decrease": "축소",
    "add": "신규 진입",
    "remove": "제외",
    "info_only": "참고",
}


def _format_adjustments_block(adjustments: list[AdjustmentItem]) -> str:
    """AdjustmentItem 리스트 → prompt에 들어갈 자연어 블록.

    예:
      - TSLA: 축소, 비중 변화 -10%
      - JNJ: 신규 진입, 목표 비중 15%
    """
    if not adjustments:
        return "- (조정 사항 없음)"

    lines: list[str] = []
    for adj in adjustments:
        verb = _ACTION_VERBS.get(adj.action, adj.action)
        weight_parts: list[str] = []
        if adj.delta_weight is not None:
            weight_parts.append(f"비중 변화 {adj.delta_weight:+.0%}")
        if adj.target_weight is not None:
            weight_parts.append(f"목표 비중 {adj.target_weight:.0%}")
        weight_str = ", ".join(weight_parts) if weight_parts else "비중 미명시"
        lines.append(f"- {adj.ticker}: {verb}, {weight_str}")
    return "\n".join(lines)


# ============================================================
# 프롬프트
# ============================================================


def build_e6_prompt(request: E6Request) -> str:
    """E6 prompt 조립.

    구조:
      1. 역할 + 작업 정의 (정량 재계산 금지)
      2. 원본 포트폴리오 요약 (holdings + 분석 요약)
      3. 조정 명령 리스트 + 사용자 발화 (있으면)
      4. JSON schema 출력 명세 (E6ComparisonResponse 미러)
    """
    ctx = request.analysis_context
    holdings = ctx.get("holdings", []) or []
    holdings_str = format_holdings_summary(holdings) if holdings else "(보유 종목 없음)"
    analysis_one_liner = format_analysis_summary(ctx, max_chars=200)
    preset_id = ctx.get("preset_id", "unknown")
    adjustments_block = _format_adjustments_block(request.adjustments)
    user_intent_block = (
        f'\n사용자 발화: "{request.user_intent}"' if request.user_intent else ""
    )

    return f"""당신은 한국 개인 투자자를 위한 포트폴리오 비교 코치입니다. 사용자가 원본 포트폴리오에 다음 조정을 적용하려 합니다. 당신의 역할은 *정량 재계산 없이* 변경 전후를 자연어로 비교 해설하는 것입니다.

## 프리셋
{preset_id}

## 원본 포트폴리오
보유: {holdings_str}
요약: {analysis_one_liner}

## 조정 명령
{adjustments_block}{user_intent_block}

## 출력 요구
다음 JSON schema로만 응답하세요. JSON 객체만 반환하며, 마크다운 코드 펜스나 추가 설명을 절대 포함하지 마세요.

{{
  "headline": "비교 한 줄 요약 (10~120자)",
  "before_summary": "조정 전 포트폴리오 핵심 특징 (20~400자)",
  "after_summary": "조정 후 예상 포트폴리오 핵심 특징 (20~400자)",
  "key_changes": [
    {{"aspect": "allocation|risk|expected_return|diversification|other", "description": "변경 사항 한 문장 (10~300자)"}}
  ],
  "risk_assessment": "위험 변화 해설 (20~300자)",
  "closing_remarks": "마무리 해설 (10~300자)"
}}

## 규칙
1. key_changes는 1~5개. aspect는 5종(allocation/risk/expected_return/diversification/other) 중 선택.
2. 자연스러운 한국어. 단순 수치 나열 금지 — 의미 있는 해석 포함.
3. 정량 재계산 금지 — 사용자에게 "예상", "추정" 등의 표현 사용.
4. 매수/매도 추천 금지. 구조적 비교 해설만.
5. 사용자가 적용하려는 조정의 합리성을 한쪽으로 단정하지 말 것.
"""


# ============================================================
# 파싱
# ============================================================


def parse_e6_response(text: str) -> E6ComparisonResponse:
    """LLM raw text → E6ComparisonResponse.

    parse_json_response가 마크다운 펜스 사후 제거 + Pydantic 검증을 처리.
    """
    return parse_json_response(E6ComparisonResponse, text)


# ============================================================
# entry function
# ============================================================


def run_e6(
    request: E6Request,
    *,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """E6 진입점 entry function.

    Args:
        request: E6Request — analysis_context + adjustments + (선택) user_intent.
        provider: label (default haiku — D2.B 글쓰기 가설).
        client: LLMClient 의존성 주입 (테스트 모킹용).

    Returns:
        {
            "response": E6ComparisonResponse.model_dump(),
            "metadata": LLMResponse.metadata_dict(),
        }
    """
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    prompt = build_e6_prompt(request)

    if client is None:
        client = LLMClient()
    raw = client.complete(prompt=prompt, **PROVIDER_KWARGS[provider])

    parsed = parse_e6_response(raw.text)
    return {
        "response": parsed.model_dump(),
        "metadata": raw.metadata_dict(),
    }
