"""Slice 11 Part 4 — A2 통합 진입점 E4 service (`run_e4_coach`).

E4 production endpoint은 별도로 존재하지 않는다 — A2 통합 진입점에서 신규.
Part 1 `CommentaryInputE4` + Part 2 `E4Output` (base만) schema 사용.
"""

from __future__ import annotations

from typing import Any

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.commentary_input import CommentaryInputE4
from portfolio.schemas.commentary_output import E4Output
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from portfolio.services.coach.prompt_builder import E4PromptBuilder


def run_e4_coach(
    input_data: CommentaryInputE4,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
    max_tokens: int = 2000,
) -> dict[str, Any]:
    """E4 대화 Q&A 종단 실행. e1_service.run_e1_coach 패턴 미러."""
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    messages = E4PromptBuilder.build_messages(input_data)
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

    output = parse_json_response(E4Output, llm_response.text)

    return {
        "output": output.model_dump(),
        "llm_metadata": llm_response.metadata_dict(),
    }
