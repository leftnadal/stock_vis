"""Keyword Cache: ContextKeyword 저장/조회 + freshness 정책 (Phase B)"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from thesis.services.builder_events import log_event

logger = logging.getLogger(__name__)

# Source별 TTL
SOURCE_TTL = {
    'news': timedelta(hours=24),
    'eod': timedelta(hours=24),
    'chain': timedelta(days=7),
}


@dataclass
class ContextKeyword:
    """빌더 프롬프트에 주입될 힌트 키워드."""
    text: str           # 8~30자 명사구
    source: str         # "chain" | "eod" | "news"
    role: str = 'theme'  # "support" | "risk" | "signal" | "theme"


def save_keywords(target: str, source: str, keywords: list[ContextKeyword]):
    """
    replace-all: 해당 target+source의 기존 키워드 삭제 후 새로 저장.
    partial append는 캐시 누적 오염 위험이 있으므로 전체 교체.
    """
    from thesis.models import KeywordCache

    KeywordCache.objects.filter(target=target, source=source).delete()
    if not keywords:
        return

    KeywordCache.objects.bulk_create([
        KeywordCache(
            target=target,
            source=source,
            text=kw.text[:200],
            role=kw.role,
        )
        for kw in keywords
    ], ignore_conflicts=True)


def collect_from_cache(target: str, source: str) -> list[ContextKeyword]:
    """
    freshness cutoff 적용 조회.
    TTL 초과 데이터는 반환하지 않음 (stale data 차단).
    """
    from thesis.models import KeywordCache

    ttl = SOURCE_TTL.get(source, timedelta(hours=24))
    cutoff = timezone.now() - ttl

    cached = KeywordCache.objects.filter(
        target=target,
        source=source,
        updated_at__gte=cutoff,
    ).order_by('-updated_at')[:5]

    if not cached.exists():
        log_event('keyword_stale_or_missing', {
            'target': target,
            'source': source,
        })

    return [
        ContextKeyword(text=kw.text, source=kw.source, role=kw.role)
        for kw in cached
    ]
