"""Slice 11 Part 4 — A2 통합 진입점 E3 service (`run_e3_coach`).

기존 production: `portfolio/services/e3_portfolio_service.py:run_e3_portfolio` (Slice 6 Part 2,
E3PortfolioCommentary schema). frontend 보호를 위해 **변경 없음**.

본 service는 Part 1 `CommentaryInputE3` + Part 2 `E3Output` schema 사용. prompt는 `E3PromptBuilder`.

Slice 12 Part 3: preset scoring 결과를 prompt context에 주입 (후방 호환).
  - preset_id + metrics 전달 시 ScoringEngine.score() 호출
  - 결과를 user_prompt 뒤에 append (E3Output schema 무변경)
  - 둘 다 None이면 기존 동작 (IDENTICAL 보장)
"""

from __future__ import annotations

from typing import Any, Optional

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.commentary_input import CommentaryInputE3
from portfolio.schemas.commentary_output import E3Output
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from portfolio.services.coach.prompt_builder import E3PromptBuilder
from portfolio.services.scoring import (
    format_scores_for_prompt,
    get_scorer,
    resolve_category,
)


def run_e3_coach(
    input_data: CommentaryInputE3,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
    max_tokens: int = 2000,
    *,
    preset_id: Optional[str] = None,
    metrics: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """E3 A2 통합 commentary 종단 실행. e1_service.run_e1_coach 패턴 미러.

    Slice 12 Part 3 신규 (후방 호환):
        preset_id: 12 preset 중 하나 (선택).
        metrics: 정규화된 지표 dict (선택).
        둘 다 전달되면 ScoringEngine 호출 → prompt에 scores context 주입.
        둘 중 하나 None이면 기존 동작 (IDENTICAL 보장).
    """
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    messages = E3PromptBuilder.build_messages(input_data)
    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]

    # Slice 12 Part 3: preset score 주입 (후방 호환 — 둘 다 None이면 skip)
    scores: dict[str, float] | None = None
    if preset_id is not None and metrics is not None:
        category = resolve_category(preset_id)
        scorer = get_scorer(category)
        scores = scorer.score(metrics)
        scores_block = format_scores_for_prompt(scores)
        user_prompt = (
            f"{user_prompt}\n\n## Preset Scores ({preset_id})\n{scores_block}"
        )

    if client is None:
        client = LLMClient()
    llm_response = client.complete(
        prompt=user_prompt,
        system=system_prompt,
        max_tokens=max_tokens,
        **PROVIDER_KWARGS[provider],
    )

    output = parse_json_response(E3Output, llm_response.text)

    result: dict[str, Any] = {
        "output": output.model_dump(),
        "llm_metadata": llm_response.metadata_dict(),
    }
    if scores is not None:
        result["scores"] = scores
        result["preset_id"] = preset_id
    return result
