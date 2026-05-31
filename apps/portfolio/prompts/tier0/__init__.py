"""Tier 0 system prompt — assembled from 5 sections."""

from .identity import COACH_IDENTITY
from .output_rules import OUTPUT_RULES
from .role_boundaries import ROLE_BOUNDARIES
from .style_rules import STYLE_RULES
from .terminology import TERMINOLOGY_DEFINITIONS
from .tier0_builder import build_tier0

__all__ = [
    "build_tier0",
    "COACH_IDENTITY",
    "ROLE_BOUNDARIES",
    "TERMINOLOGY_DEFINITIONS",
    "STYLE_RULES",
    "OUTPUT_RULES",
]
