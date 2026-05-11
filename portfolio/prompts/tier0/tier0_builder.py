"""
Tier 0 시스템 프롬프트 조립 함수.

5개 섹션(identity, role_boundaries, terminology, style_rules, output_rules)
을 조립해 최종 시스템 프롬프트를 반환한다.

Version: 1.1 (2026-04-24)
"""

from .identity import COACH_IDENTITY
from .output_rules import OUTPUT_RULES
from .role_boundaries import ROLE_BOUNDARIES
from .style_rules import STYLE_RULES
from .terminology import TERMINOLOGY_DEFINITIONS


def build_tier0(
    prompt_version: str = "1.1",
    include_style: bool = True,
    include_output_rules: bool = True,
) -> str:
    """
    Assemble the Tier 0 system prompt.

    Args:
        prompt_version: Version tag stored with AnalysisRun for reproducibility.
        include_style: If False, omit STYLE_RULES. Rare — mainly for E5
            parsing where natural-language style is irrelevant.
        include_output_rules: If False, omit OUTPUT_RULES. Rare — debugging.

    Returns:
        Full system prompt string ready to pass to an LLM.
    """
    header = f"# Stock-Vis Coach System Prompt (prompt_version={prompt_version})"
    sections: list[str] = [
        header,
        COACH_IDENTITY,
        ROLE_BOUNDARIES,
        TERMINOLOGY_DEFINITIONS,  # Always included — PV3 is mandatory.
    ]
    if include_style:
        sections.append(STYLE_RULES)
    if include_output_rules:
        sections.append(OUTPUT_RULES)

    return "\n\n".join(sections)
