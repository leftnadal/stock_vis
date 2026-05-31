"""
Tier 3 (사용자 프로필) 빌더.

UserProfile(Pydantic)을 프롬프트 블록 문자열로 변환.
신규 사용자(profile=None 또는 investment_style_summary 빈 문자열)이면 None.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from portfolio.schemas import UserProfile


def build_tier3_block(profile: UserProfile | None) -> str | None:
    """UserProfile → 프롬프트 삽입용 텍스트 블록."""
    if profile is None:
        return None
    if not profile.investment_style_summary:
        return None

    lines = [
        "## User Profile (Use for tone/focus adjustment only, do NOT quote directly):",
        "",
        f"- Investment style: {profile.investment_style_summary}",
    ]
    if profile.preferred_presets:
        lines.append(f"- Preferred presets: {', '.join(profile.preferred_presets)}")
    lines.append(f"- Risk appetite: {profile.risk_appetite_indicator}")
    if profile.decision_patterns:
        lines.append(f"- Notable patterns: {', '.join(profile.decision_patterns[:3])}")
    if profile.sensitivities:
        lines.append(f"- Sensitivities: {', '.join(profile.sensitivities[:3])}")

    return "\n".join(lines)
