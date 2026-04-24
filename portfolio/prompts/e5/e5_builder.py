"""
E5 프롬프트 조립.

E5는 순수 파싱이므로 Tier 1~3, Wallet 배제. 문체 규칙도 불필요하므로
`include_style=False`로 Tier 0 조립.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

import json

from portfolio.prompts.tier0 import build_tier0

from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e5_input
from .instructions import E5_INSTRUCTIONS


def build_e5_prompt(
    user_hint: str,
    current_preset_id: str,
    prompt_version: str = "1.1",
) -> tuple[str, str]:
    """E5 프롬프트 (system, user) 튜플."""
    system_prompt = build_tier0(
        prompt_version=prompt_version,
        include_style=False,  # 자연어 응답 아님 → 문체 규칙 불필요
    )

    parts: list[str] = [E5_INSTRUCTIONS, "## Examples"]
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        parts.append(f"### Example {i}: {ex['scenario']}")
        parts.append(f"User hint: {ex['user_hint']}")
        parts.append(
            "Current preset hint: "
            + json.dumps(ex["current_preset_hint"], ensure_ascii=False)
        )
        parts.append(
            "Output: "
            + json.dumps(ex["expected_output"], ensure_ascii=False)
        )

    input_data = build_e5_input(user_hint, current_preset_id)
    parts.append("## Parse this request:")
    parts.append("Input:\n" + json.dumps(input_data, ensure_ascii=False, indent=2))
    parts.append("Output:")

    return system_prompt, "\n\n".join(parts)
