"""
NewsEntity → StockNews 물질화 sync (NEWSFIX-SYNC-BE · D-NEWSMATCH-FIX-PATH-V2 ⑵).

문제: EOD News Enricher(`packages/shared/stocks/services/eod_news_enricher.py`)는
`StockNews`(`stocks_stock_news`)를 4단계 매칭으로 읽는데, 이 테이블에 데이터를 채우는
파이프라인이 없어 전건 profile 폴백(실뉴스 매칭 0). 실뉴스는 `NewsEntity`(587k행)에 실재.

해법(V2 ⑵): news 앱이 최근 30일 `NewsEntity`(+`NewsArticle`)를 `StockNews`로 **주기 물질화**한다.
enricher·pipeline은 **무접촉** — 기본 StockNewsSource(=현행 StockNews 쿼리)가 채워진
테이블을 자연히 읽어 실뉴스를 매칭하게 된다.

경계: news(app) → packages.shared.stocks.models 는 **단방향 경계 허용**(app→shared).
      StockNews **쓰기만**·스키마 무변(마이그레이션 0).

멱등성: 창(window) 단위 replace(삭제+bulk_create)를 단일 트랜잭션으로 수행 →
      재실행 시 동일 최종 상태(StockNews는 이 sync가 유일 writer).
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone as djtz

logger = logging.getLogger(__name__)

# sentiment_score(Decimal, -1.0~1.0) → enricher가 읽는 문자열 라벨.
# enricher._normalize_sentiment가 positive/negative/neutral을 소비한다.
# 임계 ±0.15: 약한 스코어는 neutral 처리(과잉 방향 부여 회피).
_SENT_POS = Decimal("0.15")
_SENT_NEG = Decimal("-0.15")

# StockNews.url = URLField(max_length=500) vs NewsArticle.url = URLField(max_length=2000)
_URL_MAX = 500


def _sentiment_label(score) -> str:
    """NewsEntity.sentiment_score(Decimal|None) → 'positive'|'negative'|'neutral'|''."""
    if score is None:
        return ""
    if score >= _SENT_POS:
        return "positive"
    if score <= _SENT_NEG:
        return "negative"
    return "neutral"


def sync_news_entities_to_stock_news(window_days: int = 30, now=None) -> dict:
    """
    최근 window_days 일의 NewsEntity(+NewsArticle)를 StockNews로 물질화한다(멱등 windowed replace).

    Args:
        window_days: 물질화 창(일). 기본 30 = enricher 최장 창(symbol_30d) 커버.
        now: 기준 시각(테스트 주입용). 기본 timezone.now().

    Returns:
        dict: {window_days, cutoff, deleted, created, symbols}
    """
    # import는 함수 안에서(모듈 로드 순환·경계 명확화)
    from packages.shared.stocks.models import StockNews
    from services.news.models import NewsEntity

    now = now or djtz.now()
    cutoff = now - timedelta(days=window_days)

    qs = (
        NewsEntity.objects.filter(
            news__published_at__gte=cutoff,
            news__published_at__lte=now,
        )
        .exclude(symbol="")
        .select_related("news")
        .order_by("news__published_at")
    )

    rows: list = []
    for ent in qs.iterator(chunk_size=2000):
        art = ent.news
        if art is None or art.published_at is None:
            continue
        rows.append(
            StockNews(
                stock=None,  # symbol 매칭으로 충분(FK 조회 비용 회피)
                symbol=(ent.symbol or "").upper(),  # enricher는 upper 심볼로 조회
                headline=art.title or "",
                summary=art.summary or "",
                source=art.source or "",
                url=(art.url or "")[:_URL_MAX],
                published_at=art.published_at,
                sector="",  # 원천(NewsEntity/NewsArticle)에 sector 없음 — enricher 매칭 미사용
                industry=ent.industry or "",
                sentiment=_sentiment_label(ent.sentiment_score),
            )
        )

    with transaction.atomic():
        deleted, _ = StockNews.objects.filter(
            published_at__gte=cutoff,
            published_at__lte=now,
        ).delete()
        StockNews.objects.bulk_create(rows, batch_size=1000)

    symbols = len({r.symbol for r in rows})
    result = {
        "window_days": window_days,
        "cutoff": cutoff.isoformat(),
        "deleted": deleted,
        "created": len(rows),
        "symbols": symbols,
    }
    logger.info(
        "[stock_news_sync] 물질화 완료: deleted=%s created=%s symbols=%s (window=%sd, cutoff=%s)",
        deleted, len(rows), symbols, window_days, cutoff.isoformat(),
    )
    return result
