"""
UserProfile — Tier 3 사용자 성향 프로필.
D3 Decision 집계로 배치 생성. 신규 사용자는 대부분 비어있음.

설계 근거: coach-llm-design-v1.md §4-6, §7
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserProfile(BaseModel):
    """사용자의 장기 성향 요약. Coach 응답 기조 설정용."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., description="User ID (문자열 표현).")
    last_updated: datetime | None = Field(
        None,
        description="프로필 최종 갱신 시각. 신규 사용자는 None.",
    )
    investment_style_summary: str = Field(
        "",
        description="자연어 요약 1~2문장. 예: '고성장 테크 선호, 집중 투자 성향'.",
    )
    preferred_presets: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="자주 사용한 프리셋 ID (top 3).",
    )
    typical_portfolio_structure: dict = Field(
        default_factory=dict,
        description=(
            "통상 Portfolio 구조. "
            "예: {'avg_holding_count': 8, 'dominant_sectors': ['Technology']}."
        ),
    )
    decision_patterns: list[str] = Field(
        default_factory=list,
        max_length=5,
        description=(
            "D3 Decision에서 추출한 패턴 2~5개. 예: '약세장에서 방어적 조정 선호'."
        ),
    )
    risk_appetite_indicator: str = Field(
        "unknown",
        description="'aggressive' | 'moderate' | 'conservative' | 'unknown'.",
    )
    sensitivities: list[str] = Field(
        default_factory=list,
        max_length=5,
        description=(
            "주목할 민감도 포인트 2~5개. 예: 'PEG 지표에 덜 민감', '분산 투자 선호'."
        ),
    )

    # Example (신규 사용자):
    # UserProfile(user_id="42", last_updated=None, investment_style_summary="",
    #             preferred_presets=[], typical_portfolio_structure={},
    #             decision_patterns=[], risk_appetite_indicator="unknown",
    #             sensitivities=[])
