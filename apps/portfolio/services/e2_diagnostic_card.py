"""E2 진입점 비즈니스 로직 — AnalysisContext → DiagnosticCard 4요소 (Slice 3).

설계 원칙 (D2.B + Q3.C):
  - default provider = haiku (글쓰기 작업)
  - schema 강제 — JSON only, no markdown fences, extra 키 금지
  - 4요소 균형 — summary / strengths / weaknesses / actions
  - completeness 자동 측정 — schema 통과 = 4요소 채움 + 항목 10자 이상
  - naturalness — 한국어 자연스러운 톤 (E1 패턴 mirror)
  - insight — 단순 수치 나열이 아닌 의미 있는 해석
"""

from __future__ import annotations

from typing import Any

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.llm import E2DiagnosticCard, E2Request, E2Response
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from portfolio.services._prompt_helpers import (
    format_analysis_summary,
    format_holdings_summary,
    format_metrics_to_str,
)

# ============================================================
# 프롬프트
# ============================================================


def build_e2_prompt(request: E2Request) -> str:
    """E2 프롬프트 조립.

    Slice 1 E1 패턴 mirror — schema 강제 + 4요소 명시 + 완성도 강조.
    """
    ctx = request.analysis_context
    holdings = ctx.get("holdings", [])
    holdings_str = format_holdings_summary(holdings)
    analysis_str = format_analysis_summary(ctx)
    metrics_str = format_metrics_to_str(ctx.get("metrics", {}), format="markdown")
    preset_id = ctx.get("preset_id", "unknown")

    return f"""당신은 한국 개인 투자자를 위한 포트폴리오 분석 전문가입니다.

## 프리셋
{preset_id}

## 현재 포트폴리오
{holdings_str}

## 분석 요약
{analysis_str}

## 주요 지표
{metrics_str}

## 작업
위 분석을 바탕으로 진단 카드 4요소를 다음 JSON schema로 생성하세요. JSON 객체만 반환하며, 마크다운 코드 펜스나 추가 설명을 절대 포함하지 마세요.

{{
  "summary": "포트폴리오 요약 1~2문장 (20자 이상 500자 이하)",
  "strengths": ["강점 1 (10자 이상)", "강점 2", ...],
  "weaknesses": ["약점 1 (10자 이상)", "약점 2", ...],
  "actions": ["제안 액션 1 (10자 이상)", "제안 액션 2", ...]
}}

## 규칙
1. 각 리스트(strengths/weaknesses/actions)는 1~5개 항목, 각 항목 10자 이상.
2. 자연스러운 한국어. 단순 수치 나열 금지 — 의미 있는 해석 포함.
3. summary는 핵심을 1~2문장으로 압축.
4. strengths/weaknesses는 분석 데이터 근거 명확.
5. actions는 실행 가능하고 구체적이어야 함.
6. 매수/매도 추천 금지 — 구조적 진단만.
"""


# ============================================================
# 파싱
# ============================================================


def parse_e2_response(raw_content: str, preset_id: str = "unknown") -> E2Response:
    """LLM raw 응답 → E2Response Pydantic 객체.

    parse_json_response가 마크다운 펜스를 사전 제거하고 schema 검증.
    schema 통과 = completeness 자동 통과 (4요소 모두 채움 + 항목 10자 이상).
    """
    card = parse_json_response(E2DiagnosticCard, raw_content)
    return E2Response(card=card, preset_id=preset_id)


# ============================================================
# entry function
# ============================================================


def run_e2(
    request: E2Request,
    *,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """E2 진입점 entry function.

    Args:
        request: E2Request (analysis_context).
        provider: label (default haiku — D2.B, 글쓰기 작업).
        client: LLMClient 의존성 주입 (테스트 모킹용).

    Returns:
        {
            "response":  E2Response.model_dump(),
            "metadata":  LLMResponse.metadata_dict(),
        }
    """
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    prompt = build_e2_prompt(request)

    if client is None:
        client = LLMClient()
    raw = client.complete(prompt=prompt, **PROVIDER_KWARGS[provider])

    preset_id = request.analysis_context.get("preset_id", "unknown")
    parsed = parse_e2_response(raw.text, preset_id=preset_id)
    return {
        "response": parsed.model_dump(),
        "metadata": raw.metadata_dict(),
    }
