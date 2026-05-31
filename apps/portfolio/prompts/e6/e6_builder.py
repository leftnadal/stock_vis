"""
E6 프롬프트 조립.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

import json

from portfolio.prompts.tier0 import build_tier0
from portfolio.schemas import AnalysisContext

from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e6_input
from .instructions import E6_INSTRUCTIONS


def build_e6_prompt(
    original_context: AnalysisContext,
    adjusted_context: AnalysisContext,
    applied_overrides: list[dict],
    prompt_version: str = "1.1",
) -> tuple[str, str]:
    """E6 프롬프트 (system, user) 튜플."""
    system_prompt = build_tier0(prompt_version=prompt_version)

    parts: list[str] = [E6_INSTRUCTIONS, "## Examples"]
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        parts.append(f"### Example {i}: {ex['scenario']}")
        parts.append("Input: " + json.dumps(ex["input"], ensure_ascii=False))
        parts.append("Output: " + json.dumps(ex["expected_output"], ensure_ascii=False))

    input_data = build_e6_input(original_context, adjusted_context, applied_overrides)
    parts.append("## Compare these two analyses:")
    parts.append(
        "Input:\n" + json.dumps(input_data, ensure_ascii=False, indent=2, default=str)
    )
    parts.append("Output:")

    return system_prompt, "\n\n".join(parts)
