"""Slice 11 Part 4 — A2 통합 진입점 E6 service (`run_e6_coach`).

기존 production: `portfolio/services/e6_comparison.py:run_e6` (Slice 4, E6ComparisonResponse).
frontend 보호를 위해 **변경 없음**.

본 service는 Part 1 `CommentaryInputE6` (analysis_results) + Part 2 `E6Output` schema 사용.
prompt는 `E6PromptBuilder`.
"""

from __future__ import annotations

from typing import Any

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.commentary_input import CommentaryInputE6
from portfolio.schemas.commentary_output import E6Output
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from portfolio.services.coach.prompt_builder import E6PromptBuilder


def run_e6_coach(
    input_data: CommentaryInputE6,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
    max_tokens: int = 2000,
) -> dict[str, Any]:
    """E6 A2 통합 commentary 종단 실행. e1_service.run_e1_coach 패턴 미러."""
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    messages = E6PromptBuilder.build_messages(input_data)
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

    output = parse_json_response(E6Output, llm_response.text)

    return {
        "output": output.model_dump(),
        "llm_metadata": llm_response.metadata_dict(),
    }
