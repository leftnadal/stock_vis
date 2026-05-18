"""Slice 11 Part 3 — A2 통합 진입점 E1 service (`run_e1_coach`).

기존 `portfolio/services/e1_garp.py:run_e1_garp`는 Slice 1 production endpoint
(OneLineDiagnosis schema). frontend 보호를 위해 **변경 없음**.

본 service는 Part 1 `CommentaryInputE1` + Part 2 `E1Output` schema를 사용하는
**A2 통합 시연용 신규 service**. prompt 생성은 Part 3 `E1PromptBuilder`.

설계:
  - 외부 시그니처: `run_e1_coach(input_data, provider="haiku", client=None) -> dict`
  - 내부: `E1PromptBuilder.build_messages()` → LLMClient.complete() → E1Output validate
  - 응답: `{"output": E1Output dict, "llm_metadata": {...}}`
"""

from __future__ import annotations

from typing import Any

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.commentary_input import CommentaryInputE1
from portfolio.schemas.commentary_output import E1Output
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from portfolio.services.coach.prompt_builder import E1PromptBuilder


def run_e1_coach(
    input_data: CommentaryInputE1,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
    max_tokens: int = 2000,
) -> dict[str, Any]:
    """E1 A2 통합 commentary 종단 실행.

    Args:
        input_data: `CommentaryInputE1` 인스턴스 (Part 1 schema).
        provider: PROVIDER_KWARGS 등록 라벨 (default "haiku").
        client: LLMClient 의존성 주입 (테스트용). None이면 신규 생성.
        max_tokens: 응답 최대 토큰.

    Returns:
        {
            "output": E1Output.model_dump() dict,
            "llm_metadata": {provider, model, latency_ms, input/output_tokens,
                             cost_usd, fallback_from},
        }

    Raises:
        ValueError: 미등록 provider label.
        pydantic.ValidationError: LLM 응답이 `E1Output` schema validate 실패 (#41 재오픈 트리거).
    """
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    # 1. Prompt 생성 (Part 3 builder)
    messages = E1PromptBuilder.build_messages(input_data)
    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]

    # 2. LLM 호출 — LLMClient는 system을 별도 인자로 받음
    if client is None:
        client = LLMClient()
    llm_response = client.complete(
        prompt=user_prompt,
        system=system_prompt,
        max_tokens=max_tokens,
        **PROVIDER_KWARGS[provider],
    )

    # 3. 응답 → E1Output validate (#41 재오픈 트리거 지점)
    output = parse_json_response(E1Output, llm_response.text)

    return {
        "output": output.model_dump(),
        "llm_metadata": llm_response.metadata_dict(),
    }
