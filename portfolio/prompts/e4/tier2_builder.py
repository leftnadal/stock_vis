"""
Tier 2 (세션 요약) 빌더.

MVP: ChatSession.session_summary 필드가 이미 채워져 있으면 그대로 반환.
세션 요약 생성 로직 자체는 별도 배치 (Phase 2 E8에서 공식화).

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from portfolio.models import ChatSession


def build_tier2_summary(session: ChatSession) -> str | None:
    """session_summary가 비어있지 않으면 반환, 아니면 None."""
    if session.session_summary:
        return session.session_summary
    return None
