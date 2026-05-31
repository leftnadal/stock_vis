"""E3 (지표 코멘트, 한 줄 자연어) entry function — Slice 5.

Core+Supporting 지표 5단계 level_tag → 자연어 한 줄 코멘트로 변환.

핵심 원칙:
- 분석 엔진 의존성 회피 — 산출된 MetricResult만 받음 (정량 재계산 없음)
- D2.B 가설 적용 — default provider = haiku (글쓰기 5번째 외삽)
- E3 스켈레톤 (`portfolio/prompts/e3/`)의 build_e3_prompt가 (system, user) tuple
  반환 → 본 service에서 concat으로 단일 prompt 처리 (백로그 #19로 영구 처리는
  Slice 6+, LLMClient.complete system 인자 추가 시 wrapper 제거)
"""

from __future__ import annotations

from typing import Any

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.prompts.e3.e3_builder import build_e3_prompt as _raw_build_e3_prompt
from portfolio.schemas import AnalysisContext
from portfolio.schemas.llm import E3Request
from portfolio.schemas.llm_outputs import MetricComments
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel

# ============================================================
# 프롬프트 wrapper — (system, user) tuple → single prompt
# ============================================================


def build_e3_prompt(context: AnalysisContext, *, prompt_version: str = "1.1") -> str:
    """E3 prompt 단일 str wrapper.

    raw build_e3_prompt가 (system, user) tuple 반환 → concat으로 단일 str.
    백로그 #19 (LLMClient.complete system 인자 추가) 처리 시 wrapper 제거 + 직접 분리 전달.
    """
    system, user = _raw_build_e3_prompt(context, prompt_version=prompt_version)
    return f"{system}\n\n{user}"


# ============================================================
# 파싱
# ============================================================


def parse_e3_response(text: str) -> MetricComments:
    """LLM raw text → MetricComments.

    parse_json_response가 마크다운 펜스 사후 제거 + Pydantic 검증을 처리.
    """
    return parse_json_response(MetricComments, text)


# ============================================================
# entry function
# ============================================================


def run_e3(
    request: E3Request,
    *,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """E3 진입점 entry function.

    Args:
        request: E3Request — analysis_context (preset_id + holdings + metric_results).
        provider: label (default haiku — 글쓰기 가설 5번째 외삽).
        client: LLMClient 의존성 주입 (테스트 모킹용).

    Returns:
        {
            "response": MetricComments.model_dump(),
            "metadata": LLMResponse.metadata_dict(),
        }
    """
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    context = AnalysisContext.model_validate(request.analysis_context)
    prompt = build_e3_prompt(context)

    if client is None:
        client = LLMClient()
    raw = client.complete(prompt=prompt, **PROVIDER_KWARGS[provider])

    parsed = parse_e3_response(raw.text)
    return {
        "response": parsed.model_dump(),
        "metadata": raw.metadata_dict(),
    }
