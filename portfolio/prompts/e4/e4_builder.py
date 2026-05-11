"""
E4 프롬프트 조립.

반환 구조: Anthropic Messages API 용 dict.
  {
    "system":   "<Tier 0 + Tier 3 + T2 summary + T2.5 + instructions + examples>",
    "messages": [<Tier 1 history>, ..., {"role": "user", "content": current_msg}],
  }

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

import json

from portfolio.models import ChatSession
from portfolio.prompts.tier0 import build_tier0
from portfolio.schemas import AnalysisContext, UserProfile

from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e4_input_tier25
from .instructions import E4_INSTRUCTIONS
from .tier1_builder import build_tier1_messages
from .tier2_builder import build_tier2_summary
from .tier3_builder import build_tier3_block


def build_e4_prompt(
    context: AnalysisContext,
    session: ChatSession,
    user_profile: UserProfile | None,
    current_user_message: str,
    prompt_version: str = "1.1",
    max_history_turns: int = 15,
) -> dict:
    """
    E4 프롬프트를 Anthropic Messages API 포맷 dict로 조립.

    Returns:
        {"system": str, "messages": list[dict]}
    """
    # === System portion ===
    system_parts: list[str] = [build_tier0(prompt_version=prompt_version)]

    tier3 = build_tier3_block(user_profile)
    if tier3:
        system_parts.append(tier3)

    t2_summary = build_tier2_summary(session)
    if t2_summary:
        system_parts.append(f"## Previous session summary:\n{t2_summary}")

    t25 = build_e4_input_tier25(context)
    system_parts.append(
        "## Current analysis context (Tier 2.5):\n"
        "```json\n"
        + json.dumps(t25, ensure_ascii=False, indent=2, default=str)
        + "\n```"
    )

    system_parts.append(E4_INSTRUCTIONS)

    system_parts.append("## Examples")
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        system_parts.append(f"### Example {i}: {ex['scenario']}")
        system_parts.append(f"User: {ex['user_message']}")
        system_parts.append(
            "Output: "
            + json.dumps(ex["expected_output"], ensure_ascii=False)
        )

    system = "\n\n".join(system_parts)

    # === Messages portion ===
    messages = build_tier1_messages(session, max_turns=max_history_turns)
    messages.append({"role": "user", "content": current_user_message})

    return {"system": system, "messages": messages}
