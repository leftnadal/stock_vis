"""Mock UserProfile fixtures."""

from __future__ import annotations

from datetime import datetime, timezone

from portfolio.schemas import UserProfile


def get_aggressive_tech_profile() -> UserProfile:
    """공격적 성향 + Tech 선호 프로필 (Tier 3 있음)."""
    return UserProfile(
        user_id="42",
        last_updated=datetime(2026, 4, 1, tzinfo=timezone.utc),
        investment_style_summary="고성장 테크 선호, 집중 투자 성향.",
        preferred_presets=["garp", "quality_growth", "buffett_quality_value"],
        typical_portfolio_structure={
            "avg_holding_count": 6,
            "dominant_sectors": ["Technology", "Consumer Discretionary"],
        },
        decision_patterns=[
            "PEG가 높아도 고성장 종목은 유지하는 경향",
            "약세장에서는 ROIC 중심으로 회귀",
        ],
        risk_appetite_indicator="aggressive",
        sensitivities=[
            "PEG 지표에 덜 민감",
            "분산보다 집중 투자 선호",
        ],
    )


def get_empty_profile() -> UserProfile:
    """신규 사용자 (Tier 3 비어있음)."""
    return UserProfile(user_id="99")
