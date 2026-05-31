"""
Tier 1 (최근 대화 이력) 빌더.

ChatSession.messages 에서 최근 max_turns 개를 시간 오름차순으로 반환.

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from apps.portfolio.models import ChatSession


def build_tier1_messages(session: ChatSession, max_turns: int = 15) -> list[dict]:
    """
    최근 max_turns 메시지를 Anthropic/OpenAI messages 포맷으로 반환.

    Args:
        session: 대화 세션 (Django ORM 인스턴스).
        max_turns: 포함할 최대 턴 수 (user + assistant 합산).

    Returns:
        [{"role": "user"|"assistant", "content": str}, ...] — 시간 오름차순.
    """
    recent = list(session.messages.order_by("-created_at")[:max_turns])
    recent.reverse()  # 시간 오름차순
    return [{"role": m.role, "content": m.content} for m in recent]
