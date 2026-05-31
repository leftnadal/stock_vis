"""
E1 최종 프롬프트 조립.

Returns (system_prompt, user_message) 튜플.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

import json

from portfolio.prompts.tier0 import build_tier0
from portfolio.schemas import AnalysisContext

from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e1_input
from .instructions import E1_INSTRUCTIONS


def build_e1_prompt(
    context: AnalysisContext,
    prompt_version: str = "1.1",
) -> tuple[str, str]:
    """
    E1 프롬프트 조립.

    Returns:
        (system_prompt, user_message) — LLM Messages API 용.
    """
    system_prompt = build_tier0(prompt_version=prompt_version)

    parts: list[str] = [E1_INSTRUCTIONS, "## Examples"]
    for i, (example_input, example_output) in enumerate(FEW_SHOT_EXAMPLES, 1):
        parts.append(f"### Example {i}")
        parts.append(f"Input:\n{example_input}")
        parts.append(f"Output:\n{example_output}")

    input_data = build_e1_input(context)
    parts.append("## Now analyze this portfolio:")
    parts.append(
        "Input:\n" + json.dumps(input_data, ensure_ascii=False, indent=2, default=str)
    )
    parts.append("Output:")

    user_message = "\n\n".join(parts)
    return system_prompt, user_message
