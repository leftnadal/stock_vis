"""
API cache key builders (PR-I/J).

소속: apps/market_pulse/api (app 레이어 REST API 캐시).
역할: overview / card / health 응답의 Redis 캐시 키 표준화.
  is_finalized 토글에 맞춰 cache invalidate가 동기화되도록 키 패턴 일관 유지.
주의: 키 패턴 변경 시 tasks/finalize.py의 cache 무효화 코드도 함께 갱신.
"""

from __future__ import annotations

from datetime import datetime

from django.core.cache import cache
from django.utils import timezone as django_timezone

GLOBAL_OVERVIEW_TTL_SEC = 300
USER_OVERVIEW_TTL_SEC = 60
GLOBAL_CARD_TTL_SEC = 300
GLOBAL_BRIEF_CARD_TTL_SEC = 1800
I18N_TTL_SEC = 86400
HEALTH_TTL_SEC = 10


def _bucket(seconds: int, now: datetime | None = None) -> str:
    now = now or django_timezone.now()
    return str(int(now.timestamp()) // seconds)


def overview_global_key() -> str:
    return f"mp:global:overview:{_bucket(GLOBAL_OVERVIEW_TTL_SEC)}"


def overview_user_key(user_id) -> str:
    return f"mp:user:{user_id}:overview:{_bucket(USER_OVERVIEW_TTL_SEC)}"


def card_detail_key(card_id: str, *, brief: bool = False) -> str:
    ttl = GLOBAL_BRIEF_CARD_TTL_SEC if brief else GLOBAL_CARD_TTL_SEC
    return f"mp:global:card:{card_id}:{_bucket(ttl)}"


def card_detail_ttl(card_id: str) -> int:
    return GLOBAL_BRIEF_CARD_TTL_SEC if card_id == "brief" else GLOBAL_CARD_TTL_SEC


def i18n_key(locale: str = "ko") -> str:
    return f"mp:global:i18n:{locale}:{_bucket(I18N_TTL_SEC)}"


def health_key() -> str:
    return f"mp:global:health:{_bucket(HEALTH_TTL_SEC)}"


def invalidate_all() -> None:
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("mp:*")  # type: ignore[attr-defined]
    else:
        cache.clear()
