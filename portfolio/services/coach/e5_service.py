"""Slice 11 Part 4 — A2 통합 진입점 E5 service (`run_e5_coach`).

기존 production: `portfolio/services/e5_adjustment_parser.py:run_e5` (Slice 1, E5Response).
frontend 보호를 위해 **변경 없음**.

본 service는 Part 1 `CommentaryInputE5` (extraction_targets + time_series_context) +
Part 2 `E5Output` schema 사용. prompt는 `E5PromptBuilder`.

Slice 13 Step 0a #60: gate-tier ADDITIVE 주입 (preset_id + metrics 옵셔널).
"""

from __future__ import annotations

from typing import Any, Optional

from portfolio.llm import LLMClient
from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.commentary_input import CommentaryInputE5
from portfolio.schemas.commentary_output import E5Output
from portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from portfolio.services.coach.prompt_builder import E5PromptBuilder
from portfolio.services.scoring import (
    ScoringEngineBase,
    format_gate_tier_for_prompt,
    get_preset_spec,
)


def run_e5_coach(
    input_data: CommentaryInputE5,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
    max_tokens: int = 2000,
    *,
    preset_id: Optional[str] = None,
    metrics: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """E5 A2 통합 commentary 종단 실행. e1_service.run_e1_coach 패턴 미러."""
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    messages = E5PromptBuilder.build_messages(input_data)
    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]

    # Slice 13 Step 0a #60: gate-tier ADDITIVE 주입 (둘 다 None이면 skip — IDENTICAL 보장).
    gate_tier: str | None = None
    if preset_id is not None and metrics is not None:
        spec = get_preset_spec(preset_id)
        gate_tier = ScoringEngineBase._evaluate_gate_tier(metrics, spec.gate_tiers)
        user_prompt = (
            f"{user_prompt}\n\n{format_gate_tier_for_prompt(preset_id, gate_tier)}"
        )

    if client is None:
        client = LLMClient()
    llm_response = client.complete(
        prompt=user_prompt,
        system=system_prompt,
        max_tokens=max_tokens,
        **PROVIDER_KWARGS[provider],
    )

    output = parse_json_response(E5Output, llm_response.text)

    result: dict[str, Any] = {
        "output": output.model_dump(),
        "llm_metadata": llm_response.metadata_dict(),
    }
    if gate_tier is not None:
        result["gate_tier"] = gate_tier
        result["preset_id"] = preset_id
    return result
