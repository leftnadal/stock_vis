"""
E1 + GARP 종단 실행 서비스.

view에서 HTTP 코드를 분리. 비즈니스 로직만 담당:
  1. Mock fixture로 AnalysisContext 로드
  2. D-2 빌더로 E1 프롬프트 조립 (system, user 튜플 → 단일 prompt 합침)
  3. LLMClient.complete() 호출
  4. 응답 schema 파싱 (OneLineDiagnosis)
  5. {diagnosis, llm_metadata} dict 반환

§5.3 의존성 주입 필수 — Mock 테스트 핵심.
"""

from __future__ import annotations

from apps.portfolio.llm import LLMClient
from apps.portfolio.llm.parsers import parse_json_response
from apps.portfolio.prompts.e1.e1_builder import build_e1_prompt
from apps.portfolio.schemas.llm import LLMResponse
from apps.portfolio.schemas.llm_outputs import OneLineDiagnosis

# Slice 1 Decision (validation_report §5): winner = haiku.
# Free tier 환경에서 gemini는 RateLimit 즉시 폴백 → 진입점 default는 haiku.
# Slice 3 Step 2 — _llm_kwargs.py 공유 모듈 흡수 (백로그 #3).
from apps.portfolio.services._llm_kwargs import (  # noqa: F401
    PROVIDER_KWARGS,
    ProviderLabel,
)
from apps.portfolio.tests.fixtures.sample_analysis_context import get_context_garp_tech


def run_e1_garp(
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
) -> dict:
    """
    E1 한 줄 진단 + GARP 프리셋 종단 실행.

    Args:
        provider: "gemini" (기본) 또는 "anthropic".
        client: LLMClient 호환 인스턴스 (의존성 주입). None이면 기본 LLMClient 생성.

    Returns:
        {
            "diagnosis":    {"headline": "...", "summary": "..."},
            "llm_metadata": {provider, model, latency_ms, input/output_tokens,
                             cost_usd, fallback_from},
        }
    """
    # 1. Mock fixture 로드 (slice 1은 스코어링 엔진 우회)
    context = get_context_garp_tech()

    # 2. 프롬프트 빌드 (D-2 builder는 (system, user) 튜플 반환)
    system_prompt, user_message = build_e1_prompt(context)
    prompt = f"{system_prompt}\n\n{user_message}"

    # 3. LLM 호출 (의존성 주입). label → (provider, model) 매핑.
    if client is None:
        client = LLMClient()
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )
    llm_response: LLMResponse = client.complete(
        prompt=prompt, **PROVIDER_KWARGS[provider]
    )

    # 4. schema 파싱 (마크다운 펜스 사전 제거 — LLM이 ```json``` 감싸는 경향)
    diagnosis = parse_json_response(OneLineDiagnosis, llm_response.text)

    # 5. 응답 dict 구성
    return {
        "diagnosis": diagnosis.model_dump(),
        "llm_metadata": llm_response.metadata_dict(),
    }
