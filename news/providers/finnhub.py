"""
Finnhub 뉴스 API Provider

- Free Tier: 60 calls/min
- Company News: 1년 히스토리
- Market News: 일반, forex, crypto, merger
"""

import requests
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from decimal import Decimal

from .base import BaseNewsProvider, RawNewsArticle

logger = logging.getLogger(__name__)


class FinnhubNewsProvider(BaseNewsProvider):
    """Finnhub 뉴스 API Provider"""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str, request_delay: float = 1.0):
        """
        Args:
            api_key: Finnhub API 키
            request_delay: 요청 간 대기 시간 (초) - 60 calls/min = 1초 간격
        """
        self.api_key = api_key
        self.request_delay = request_delay
        self.last_request_time = 0

        if not self.api_key:
            raise ValueError("Finnhub API Key not found")

    def _make_request(self, endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Finnhub API 요청 (rate limiting 포함)

        Args:
            endpoint: API 엔드포인트 (e.g., "/company-news")
            params: 쿼리 파라미터

        Returns:
            Dict[str, Any]: API 응답
        """
        # API key 추가
        params['token'] = self.api_key

        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            logger.info(f"Finnhub rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        # Make request
        url = f"{self.BASE_URL}{endpoint}"
        logger.info(f"Making request to Finnhub: {url} with params: {params}")

        response = requests.get(url, params=params)
        self.last_request_time = time.time()

        # Check for errors
        if response.status_code != 200:
            logger.error(f"Error {response.status_code} from Finnhub: {response.text}")
            response.raise_for_status()

        data = response.json()

        # Check for API error
        if isinstance(data, dict) and 'error' in data:
            error_message = data['error']
            logger.error(f"Finnhub API error: {error_message}")
            raise ValueError(f"Finnhub API error: {error_message}")

        return data

    def fetch_company_news(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[RawNewsArticle]:
        """
        종목별 뉴스 가져오기

        Args:
            symbol: 주식 심볼
            from_date: 시작 날짜
            to_date: 종료 날짜

        Returns:
            List[RawNewsArticle]: 뉴스 리스트
        """
        params = {
            'symbol': symbol.upper(),
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d')
        }

        try:
            data = self._make_request('/company-news', params)

            # Finnhub는 리스트 형태로 반환
            if not isinstance(data, list):
                logger.warning(f"Unexpected Finnhub response format: {type(data)}")
                return []

            articles = []
            for item in data:
                try:
                    article = self._parse_article(item, symbol=symbol)
                    articles.append(article)
                except Exception as e:
                    logger.error(f"Failed to parse Finnhub article: {e}, item: {item}")
                    continue

            logger.info(f"Fetched {len(articles)} company news for {symbol} from Finnhub")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch company news from Finnhub: {e}")
            return []

    def fetch_market_news(
        self,
        category: str = 'general',
        limit: int = 50
    ) -> List[RawNewsArticle]:
        """
        일반 시장 뉴스 가져오기

        Args:
            category: 뉴스 카테고리 (general, forex, crypto, merger)
            limit: 가져올 뉴스 개수 (Finnhub는 무시, 최대 50개 반환)

        Returns:
            List[RawNewsArticle]: 뉴스 리스트
        """
        params = {'category': category}

        try:
            data = self._make_request('/news', params)

            if not isinstance(data, list):
                logger.warning(f"Unexpected Finnhub response format: {type(data)}")
                return []

            articles = []
            for item in data[:limit]:  # limit 적용
                try:
                    article = self._parse_article(item, category=category)
                    articles.append(article)
                except Exception as e:
                    logger.error(f"Failed to parse Finnhub article: {e}, item: {item}")
                    continue

            logger.info(f"Fetched {len(articles)} market news for category '{category}' from Finnhub")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch market news from Finnhub: {e}")
            return []

    def _parse_article(
        self,
        item: Dict[str, Any],
        symbol: str = None,
        category: str = 'general'
    ) -> RawNewsArticle:
        """
        Finnhub API 응답을 RawNewsArticle로 변환

        Args:
            item: Finnhub API 응답 아이템
            symbol: 종목 심볼 (company news인 경우)
            category: 카테고리 (market news인 경우)

        Returns:
            RawNewsArticle: 파싱된 뉴스 데이터
        """
        # Finnhub 응답 구조:
        # {
        #   "category": "company news",
        #   "datetime": 1605543180,
        #   "headline": "...",
        #   "id": 123456,
        #   "image": "https://...",
        #   "related": "AAPL",
        #   "source": "Yahoo",
        #   "summary": "...",
        #   "url": "https://..."
        # }

        entities = []

        # related 필드에서 실제 관련 종목 추출 (Finnhub API가 제공하는 실제 관련 종목)
        # related는 쉼표로 구분된 심볼 문자열일 수 있음 (e.g., "AAPL,MSFT,GOOG")
        related = item.get('related', '')
        if related:
            for sym in related.split(','):
                sym = sym.strip().upper()
                if sym:
                    entities.append({
                        'symbol': sym,
                        'entity_name': '',  # Finnhub는 엔티티명 미제공
                        'entity_type': 'equity',
                        'source': 'finnhub',
                        'match_score': Decimal('1.00000')
                    })

        return RawNewsArticle(
            url=self.normalize_url(item.get('url', '')),
            title=item.get('headline', ''),
            summary=item.get('summary', ''),
            source=item.get('source', 'Unknown'),
            published_at=datetime.fromtimestamp(item.get('datetime', 0), tz=timezone.utc),
            image_url=item.get('image', ''),
            language='en',
            category=item.get('category', category),
            provider_id=str(item.get('id', '')),
            provider_name='finnhub',
            sentiment_score=None,  # Finnhub는 감성 분석 미제공
            sentiment_source='none',
            entities=entities,
            is_press_release=False
        )

    def get_rate_limit_key(self) -> str:
        """Rate limit 캐시 키"""
        return "news_rate_limit:finnhub"

    def get_rate_limit(self) -> Dict[str, int]:
        """Rate limit 정보: 60 calls per minute"""
        return {'calls': 60, 'period': 60}
