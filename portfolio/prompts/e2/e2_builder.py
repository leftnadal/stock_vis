"""
E2 프롬프트 조립.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

import json

from portfolio.prompts.tier0 import build_tier0
from portfolio.schemas import AnalysisContext

from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e2_input
from .instructions import E2_INSTRUCTIONS


def build_e2_prompt(
    context: AnalysisContext,
    prompt_version: str = "1.1",
) -> tuple[str, str]:
    """E2 프롬프트를 (system, user) 튜플로 반환."""
    system_prompt = build_tier0(prompt_version=prompt_version)

    parts: list[str] = [E2_INSTRUCTIONS, "## Examples"]
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        parts.append(f"### Example {i}: {example['scenario']}")
        parts.append(f"Input:\n{example['input']}")
        parts.append(f"Output:\n{example['output']}")

    input_data = build_e2_input(context)
    parts.append("## Now generate diagnostic cards for this portfolio:")
    parts.append(
        "Input:\n"
        + json.dumps(input_data, ensure_ascii=False, indent=2, default=str)
    )
    parts.append("Output:")

    return system_prompt, "\n\n".join(parts)
