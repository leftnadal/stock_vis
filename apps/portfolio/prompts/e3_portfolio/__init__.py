"""Slice 6 E3 portfolio prompt module — Part 1 minimal + Part 2 Step A reinforced."""

from apps.portfolio.prompts.e3_portfolio.builder import (
    FEW_SHOT_EXAMPLES,
    MINIMAL_PROMPT_TEMPLATE,
    PROMPT_VARIABLE_SLOTS,
    REINFORCED_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
    build_e3_portfolio_prompt,
)

# Backward compatibility — Part 1 코드가 PROMPT_TEMPLATE 직접 import 시 minimal 매핑
PROMPT_TEMPLATE = MINIMAL_PROMPT_TEMPLATE

__all__ = [
    "FEW_SHOT_EXAMPLES",
    "MINIMAL_PROMPT_TEMPLATE",
    "PROMPT_TEMPLATE",
    "PROMPT_VARIABLE_SLOTS",
    "REINFORCED_PROMPT_TEMPLATE",
    "SYSTEM_PROMPT",
    "build_e3_portfolio_prompt",
]
