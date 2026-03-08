"""
Alpha Vantage News Sentiment Provider

NEWS_SENTIMENT 엔드포인트를 통한 감성 분석 뉴스 수집.
- 종목별 감성 점수 포함
- ticker_sentiment 배열로 다중 종목 매핑
- 5 calls/min 제한 (Redis Token Bucket)
"""

import logging
import time
import requests
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional

from .base import BaseNewsProvider, RawNewsArticle

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Rate Limit 초과"""
    pass


class AlphaVantageNewsProvider(BaseNewsProvider):
    """Alpha Vantage NEWS_SENTIMENT Provider"""

    BASE_URL = "https://www.alphavantage.co"
    RATE_LIMIT_KEY = "av:news_rate_limit"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _acquire_token(self) -> bool:
        """
        Redis Token Bucket — 5 calls/min 보장

        Raises:
            RateLimitExceeded: 분당 5회 초과 시
        """
        from django.core.cache import cache

        key = self.RATE_LIMIT_KEY
        now = time.time()

        # 간단한 sliding window 카운터
        window_key = f"{key}:window"
        count = cache.get(window_key, 0)

        if count >= 5:
            raise RateLimitExceeded("Alpha Vantage 5/min rate limit exceeded")

        cache.set(window_key, count + 1, timeout=60)
        return True

    def fetch_company_news(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[RawNewsArticle]:
        """
        종목별 감성 뉴스 가져오기

        Args:
            symbol: 주식 심볼
            from_date: 시작 날짜
            to_date: 종료 날짜

        Returns:
            List[RawNewsArticle]
        """
        self._acquire_token()
        symbol = symbol.upper()

        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': symbol,
            'time_from': from_date.strftime('%Y%m%dT%H%M'),
            'time_to': to_date.strftime('%Y%m%dT%H%M'),
            'sort': 'RELEVANCE',
            'limit': 50,
            'apikey': self.api_key,
        }

        try:
            resp = requests.get(f"{self.BASE_URL}/query", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"AV NEWS_SENTIMENT failed for {symbol}: {e}")
            return []

        # Rate limit 체크
        if 'Note' in data:
            logger.warning(f"AV rate limited: {data['Note']}")
            raise RateLimitExceeded(data['Note'])

        if 'Error Message' in data:
            logger.error(f"AV API error: {data['Error Message']}")
            return []

        feed = data.get('feed', [])
        articles = []
        for item in feed:
            try:
                article = self._parse_article(item, symbol)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"AV parse error: {e}")
                continue

        logger.info(f"AV NEWS_SENTIMENT {symbol}: {len(articles)} articles")
        return articles

    def fetch_market_news(
        self,
        category: str = 'general',
        limit: int = 50,
    ) -> List[RawNewsArticle]:
        """AV는 시장 뉴스를 직접 지원하지 않음 — 빈 리스트 반환"""
        return []

    def _parse_article(
        self, item: Dict[str, Any], symbol: str
    ) -> Optional[RawNewsArticle]:
        """
        AV NEWS_SENTIMENT 응답 파싱

        필드 매핑:
        - url → url
        - title → title
        - summary → summary
        - time_published → published_at ('YYYYMMDDTHHmmss' 형식)
        - source → source
        - banner_image → image_url
        - overall_sentiment_score → sentiment_score
        - ticker_sentiment[] → entities
        """
        url = item.get('url')
        title = item.get('title')
        if not url or not title:
            return None

        published_at = self._parse_av_date(item.get('time_published', ''))
        if not published_at:
            return None

        # 전체 감성 점수
        sentiment_score = self._safe_decimal(item.get('overall_sentiment_score'))

        # ticker_sentiment에서 entities 추출
        entities = []
        ticker_sentiments = item.get('ticker_sentiment', [])
        for ts in ticker_sentiments:
            ticker = ts.get('ticker', '')
            if not ticker:
                continue
            entities.append({
                'symbol': ticker.upper(),
                'entity_name': ticker.upper(),
                'entity_type': 'equity',
                'source': 'alpha_vantage',
                'match_score': self._safe_decimal(
                    ts.get('relevance_score', '1.0')
                ) or Decimal('1.00000'),
                'sentiment_score': self._safe_decimal(
                    ts.get('ticker_sentiment_score')
                ),
            })

        # 요청 심볼이 entities에 없으면 추가
        if not any(e['symbol'] == symbol.upper() for e in entities):
            entities.insert(0, {
                'symbol': symbol.upper(),
                'entity_name': symbol.upper(),
                'entity_type': 'equity',
                'source': 'alpha_vantage',
                'match_score': Decimal('1.00000'),
                'sentiment_score': sentiment_score,
            })

        return RawNewsArticle(
            url=url,
            title=title,
            summary=item.get('summary', ''),
            source=item.get('source', 'Alpha Vantage'),
            published_at=published_at,
            image_url=item.get('banner_image', ''),
            language='en',
            category='company',
            provider_id=url,  # AV는 별도 ID 없음
            provider_name='alpha_vantage',
            sentiment_score=sentiment_score,
            sentiment_source='alpha_vantage' if sentiment_score is not None else 'none',
            entities=entities,
            is_press_release=False,
        )

    @staticmethod
    def _parse_av_date(date_str: str) -> Optional[datetime]:
        """AV 날짜 형식 파싱: 'YYYYMMDDTHHmmss'"""
        if not date_str:
            return None
        formats = [
            '%Y%m%dT%H%M%S',
            '%Y%m%dT%H%M',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        logger.warning(f"AV unparseable date: {date_str}")
        return None

    @staticmethod
    def _safe_decimal(value) -> Optional[Decimal]:
        """안전한 Decimal 변환"""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def get_rate_limit_key(self) -> str:
        return "news_rate_limit:alpha_vantage"

    def get_rate_limit(self) -> Dict[str, int]:
        return {'calls': 5, 'period': 60}
