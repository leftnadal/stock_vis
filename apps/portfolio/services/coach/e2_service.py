"""Slice 11 Part 4 — A2 통합 진입점 E2 service (`run_e2_coach`).

기존 `portfolio/services/e2_diagnostic_card.py:run_e2`는 Slice 3 production endpoint
(E2Response.card 4요소 카드). frontend 보호를 위해 **변경 없음**.

본 service는 Part 1 `CommentaryInputE2` + Part 2 `E2Output` schema를 사용하는
A2 통합 진입점 신규 service. prompt 생성은 Part 4 `E2PromptBuilder`.

Slice 13 Step 0a #60: gate-tier ADDITIVE 주입 (preset_id + metrics 옵셔널).
"""

from __future__ import annotations

from typing import Any, Optional

from apps.portfolio.llm import LLMClient
from apps.portfolio.llm.parsers import parse_json_response
from apps.portfolio.schemas.commentary_input import CommentaryInputE2
from apps.portfolio.schemas.commentary_output import E2Output
from apps.portfolio.services._llm_kwargs import PROVIDER_KWARGS, ProviderLabel
from apps.portfolio.services.coach.prompt_builder import E2PromptBuilder
from apps.portfolio.services.scoring import (
    ScoringEngineBase,
    format_gate_tier_for_prompt,
    get_preset_spec,
)


def run_e2_coach(
    input_data: CommentaryInputE2,
    provider: ProviderLabel = "haiku",
    client: LLMClient | None = None,
    max_tokens: int = 2000,
    *,
    preset_id: Optional[str] = None,
    metrics: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """E2 A2 통합 commentary 종단 실행. e1_service.run_e1_coach 패턴 미러."""
    if provider not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {provider!r}. Valid: {sorted(PROVIDER_KWARGS)}"
        )

    messages = E2PromptBuilder.build_messages(input_data)
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
        entry_point="e2",
        **PROVIDER_KWARGS[provider],
    )

    output = parse_json_response(E2Output, llm_response.text)

    result: dict[str, Any] = {
        "output": output.model_dump(),
        "llm_metadata": llm_response.metadata_dict(),
    }
    if gate_tier is not None:
        result["gate_tier"] = gate_tier
        result["preset_id"] = preset_id
    return result
