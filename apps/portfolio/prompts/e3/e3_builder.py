"""
E3 프롬프트 조립.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from apps.portfolio.prompts.tier0 import build_tier0
from apps.portfolio.schemas import AnalysisContext
from apps.portfolio.services._prompt_helpers import format_metrics_to_str

from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e3_input
from .instructions import E3_INSTRUCTIONS


def build_e3_prompt(
    context: AnalysisContext,
    prompt_version: str = "1.1",
) -> tuple[str, str]:
    """E3 프롬프트 (system, user) 튜플."""
    system_prompt = build_tier0(prompt_version=prompt_version)

    parts: list[str] = [E3_INSTRUCTIONS, "## Examples"]
    for i, (example_input, example_output) in enumerate(FEW_SHOT_EXAMPLES, 1):
        parts.append(f"### Example {i}")
        parts.append(f"Input:\n{example_input}")
        parts.append(f"Output:\n{example_output}")

    input_data = build_e3_input(context)
    parts.append("## Now generate per-metric commentary:")
    parts.append("Input:\n" + format_metrics_to_str(input_data, format="json"))
    parts.append("Output:")

    return system_prompt, "\n\n".join(parts)
