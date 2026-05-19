"""Slice 11 Part 4 — A2 통합 진입점 E2 service (`run_e2_coach`).

기존 `portfolio/services/e2_diagnostic_card.py:run_e2`는 Slice 3 production endpoint
(E2Response.card 4요소 카드). frontend 보호를 위해 **변경 없음**.

본 service는 Part 1 `CommentaryInputE2` + Part 2 `E2Output` schema를 사용하는
A2 통합 진입점 신규 service. prompt 생성은 Part 4 `E2PromptBuilder`.
"""

from __future__ import annotations

from typing import Any

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.commentary_input import CommentaryInputE2
from portfolio.schemas.commentary_output import E2Output
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from portfolio.services.coach.prompt_builder import E2PromptBuilder


def run_e2_coach(
    input_data: CommentaryInputE2,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
    max_tokens: int = 2000,
) -> dict[str, Any]:
    """E2 A2 통합 commentary 종단 실행. e1_service.run_e1_coach 패턴 미러."""
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    messages = E2PromptBuilder.build_messages(input_data)
    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]

    if client is None:
        client = LLMClient()
    llm_response = client.complete(
        prompt=user_prompt,
        system=system_prompt,
        max_tokens=max_tokens,
        **PROVIDER_KWARGS[provider],
    )

    output = parse_json_response(E2Output, llm_response.text)

    return {
        "output": output.model_dump(),
        "llm_metadata": llm_response.metadata_dict(),
    }
