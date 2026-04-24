"""
E4 입력 빌더 — Tier 2.5 전체 직렬화.

E1~E3와 달리 wallet_background 전체 포함.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from portfolio.schemas import AnalysisContext


def build_e4_input_tier25(context: AnalysisContext) -> dict:
    """AnalysisContext 전체를 dict(json-mode)로 반환."""
    return context.model_dump(mode="json")
