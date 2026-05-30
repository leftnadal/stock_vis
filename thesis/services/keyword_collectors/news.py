"""News Keyword Collector: 뉴스 기사 → ContextKeyword 변환 (Phase B, PR-9)

규칙 기반 — 추가 LLM 호출 없음.
NewsArticle의 title + sentiment_score를 키워드로 변환.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from thesis.services.builder_events import log_event
from thesis.services.keyword_cache import ContextKeyword, save_keywords

logger = logging.getLogger(__name__)


def _sentiment_to_role(score) -> str:
    """sentiment_score → role 매핑."""
    if score is None:
        return 'theme'
    score = float(score)
    if score > 0.2:
        return 'support'
    elif score < -0.2:
        return 'risk'
    return 'theme'


def extract_news_keywords(target: str) -> list[ContextKeyword]:
    """
    최근 7일 뉴스에서 target 관련 키워드 추출.
    NewsEntity.symbol 또는 entity_name으로 매칭.
    """
    from news.models import NewsArticle

    cutoff = timezone.now() - timedelta(days=7)

    articles = (
        NewsArticle.objects.filter(
            entities__entity_name__icontains=target,
            published_at__gte=cutoff,
        )
        .distinct()
        .order_by('-published_at')[:5]
    )

    keywords = []
    for article in articles:
        role = _sentiment_to_role(article.sentiment_score)
        # 8~30자 명사구 규칙: title 앞 30자
        text = article.title[:30].strip()
        if len(text) < 8:
            text = article.title[:50].strip()
        if text:
            keywords.append(ContextKeyword(text=text, source='news', role=role))

    return keywords[:5]


def collect_news_keywords(target: str):
    """뉴스 키워드 추출 + KeywordCache 저장."""
    try:
        keywords = extract_news_keywords(target)
        save_keywords(target, 'news', keywords)
        log_event('keyword_extracted', {
            'source': 'news',
            'target': target,
            'count': len(keywords),
            'roles': [kw.role for kw in keywords],
        })
    except Exception as e:
        log_event('keyword_extraction_failed', {
            'source': 'news',
            'target': target,
            'error': str(e),
        })
        logger.exception(f"News keyword extraction failed for {target}: {e}")
