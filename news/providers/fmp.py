"""
FMP News Provider

FMP API를 통한 뉴스 수집 Provider.
- stock-news: 종목별 뉴스
- general-news: 일반 시장 뉴스
- press-releases: 보도자료
"""

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional

from .base import BaseNewsProvider, RawNewsArticle

logger = logging.getLogger(__name__)


class FMPNewsProvider(BaseNewsProvider):
    """FMP News Provider — FMPClient 위임 패턴"""

    def __init__(self, fmp_client):
        """
        Args:
            fmp_client: FMPClient 인스턴스
        """
        self.client = fmp_client

    def fetch_company_news(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        limit: int = 50,
    ) -> List[RawNewsArticle]:
        """
        종목별 뉴스 가져오기

        Args:
            symbol: 주식 심볼
            from_date: 시작 날짜
            to_date: 종료 날짜
            limit: 가져올 뉴스 수

        Returns:
            List[RawNewsArticle]
        """
        symbol = symbol.upper()
        try:
            raw = self.client.get_stock_news(symbol, limit=limit)
        except Exception as e:
            logger.error(f"FMP stock-news failed for {symbol}: {e}")
            return []

        articles = []
        for item in raw:
            try:
                article = self._parse_article(item, symbol=symbol)
                if article is None:
                    continue
                # 날짜 필터
                if article.published_at < from_date or article.published_at > to_date:
                    continue
                articles.append(article)
            except Exception as e:
                logger.warning(f"FMP parse error: {e}")
                continue

        logger.info(f"FMP stock-news {symbol}: {len(articles)} articles (from {len(raw)} raw)")
        return articles

    def fetch_market_news(
        self,
        category: str = 'general',
        limit: int = 50,
    ) -> List[RawNewsArticle]:
        """
        일반 시장 뉴스 가져오기

        Args:
            category: 뉴스 카테고리 (general만 지원)
            limit: 가져올 뉴스 수

        Returns:
            List[RawNewsArticle]
        """
        try:
            raw = self.client.get_general_news(limit=limit)
        except Exception as e:
            logger.error(f"FMP general-news failed: {e}")
            return []

        articles = []
        for item in raw:
            try:
                article = self._parse_article(item)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"FMP general-news parse error: {e}")
                continue

        logger.info(f"FMP general-news: {len(articles)} articles")
        return articles

    def fetch_press_releases(
        self,
        symbol: str,
        limit: int = 20,
    ) -> List[RawNewsArticle]:
        """
        보도자료 가져오기

        Args:
            symbol: 주식 심볼
            limit: 가져올 보도자료 수

        Returns:
            List[RawNewsArticle]
        """
        symbol = symbol.upper()
        try:
            raw = self.client.get_press_releases(symbol, limit=limit)
        except Exception as e:
            logger.error(f"FMP press-releases failed for {symbol}: {e}")
            return []

        articles = []
        for item in raw:
            try:
                article = self._parse_press_release(item, symbol=symbol)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"FMP press-release parse error: {e}")
                continue

        logger.info(f"FMP press-releases {symbol}: {len(articles)} articles")
        return articles

    def _parse_article(
        self, item: Dict[str, Any], symbol: Optional[str] = None
    ) -> Optional[RawNewsArticle]:
        """
        FMP 뉴스 응답을 RawNewsArticle로 변환

        FMP stable API 필드 매핑:
        - url → url
        - title → title
        - text → summary
        - publishedDate → published_at
        - site → source
        - image → image_url
        - symbol → entities
        """
        url = item.get('url')
        title = item.get('title')
        if not url or not title:
            return None

        published_at = self._parse_date(item.get('publishedDate', ''))
        if not published_at:
            return None

        # 심볼 결정: 기사에 symbol 필드가 있으면 사용, 없으면 파라미터 사용
        article_symbol = item.get('symbol', '') or (symbol or '')
        article_symbol = article_symbol.upper()

        entities = []
        if article_symbol:
            entities.append({
                'symbol': article_symbol,
                'entity_name': article_symbol,
                'entity_type': 'equity',
                'source': 'fmp',
                'match_score': Decimal('1.00000'),
            })

        return RawNewsArticle(
            url=url,
            title=title,
            summary=item.get('text', '')[:2000],  # 요약 길이 제한
            source=item.get('site', 'FMP'),
            published_at=published_at,
            image_url=item.get('image', ''),
            language='en',
            category='company' if article_symbol else 'general',
            provider_id=str(url),  # FMP는 별도 ID 없음, URL 사용
            provider_name='fmp',
            sentiment_score=self._safe_decimal(item.get('sentiment')),
            sentiment_source='fmp' if item.get('sentiment') is not None else 'none',
            entities=entities,
            is_press_release=False,
        )

    def _parse_press_release(
        self, item: Dict[str, Any], symbol: str
    ) -> Optional[RawNewsArticle]:
        """보도자료를 RawNewsArticle로 변환"""
        url = item.get('url')
        title = item.get('title')
        if not url or not title:
            return None

        published_at = self._parse_date(item.get('date', ''))
        if not published_at:
            return None

        entities = [{
            'symbol': symbol.upper(),
            'entity_name': symbol.upper(),
            'entity_type': 'equity',
            'source': 'fmp',
            'match_score': Decimal('1.00000'),
        }]

        return RawNewsArticle(
            url=url,
            title=title,
            summary=item.get('text', '')[:2000],
            source='Press Release',
            published_at=published_at,
            image_url='',
            language='en',
            category='press_release',
            provider_id=str(url),
            provider_name='fmp',
            sentiment_score=None,
            sentiment_source='none',
            entities=entities,
            is_press_release=True,
        )

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """FMP 날짜 문자열 파싱 (여러 포맷 지원)"""
        if not date_str:
            return None
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        logger.warning(f"FMP unparseable date: {date_str}")
        return None

    @staticmethod
    def _safe_decimal(value) -> Optional[Decimal]:
        """안전한 Decimal 변환"""
        if value is None:
            return None
        try:
            d = Decimal(str(value))
            return max(Decimal('-1.000'), min(Decimal('1.000'), d))
        except (InvalidOperation, ValueError):
            return None

    def get_rate_limit_key(self) -> str:
        return "news_rate_limit:fmp"

    def get_rate_limit(self) -> Dict[str, int]:
        return {'calls': 300, 'period': 60}
