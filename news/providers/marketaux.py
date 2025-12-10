"""
Marketaux 뉴스 API Provider

- Free Tier: 100 calls/day, 3 articles/request
- 내장 감성 분석 + 엔티티 하이라이트
- 필터링 기능 강력
"""

import requests
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
from decimal import Decimal

from .base import BaseNewsProvider, RawNewsArticle

logger = logging.getLogger(__name__)


class MarketauxNewsProvider(BaseNewsProvider):
    """Marketaux 뉴스 API Provider"""

    BASE_URL = "https://api.marketaux.com/v1"

    def __init__(self, api_key: str, request_delay: float = 900.0):
        """
        Args:
            api_key: Marketaux API 키
            request_delay: 요청 간 대기 시간 (초)
                         100 calls/day = 86400초 / 100 = 864초 (약 15분)
                         안전하게 900초(15분) 설정
        """
        self.api_key = api_key
        self.request_delay = request_delay
        self.last_request_time = 0

        if not self.api_key:
            raise ValueError("Marketaux API Key not found")

    def _make_request(self, endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Marketaux API 요청 (rate limiting 포함)

        Args:
            endpoint: API 엔드포인트 (e.g., "/news/all")
            params: 쿼리 파라미터

        Returns:
            Dict[str, Any]: API 응답
        """
        # API key 추가
        params['api_token'] = self.api_key

        # Rate limiting (100 calls/day - 15분 간격)
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            logger.info(f"Marketaux rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        # Make request
        url = f"{self.BASE_URL}{endpoint}"
        logger.info(f"Making request to Marketaux: {url} with params: {params}")

        response = requests.get(url, params=params)
        self.last_request_time = time.time()

        # Check for errors
        if response.status_code != 200:
            logger.error(f"Error {response.status_code} from Marketaux: {response.text}")
            response.raise_for_status()

        data = response.json()

        # Check for API error
        if 'error' in data:
            error_message = data['error']
            logger.error(f"Marketaux API error: {error_message}")
            raise ValueError(f"Marketaux API error: {error_message}")

        return data

    def fetch_company_news(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[RawNewsArticle]:
        """
        종목별 뉴스 가져오기 (엔티티 필터링)

        Args:
            symbol: 주식 심볼
            from_date: 시작 날짜
            to_date: 종료 날짜

        Returns:
            List[RawNewsArticle]: 뉴스 리스트 (최대 3개)
        """
        params = {
            'symbols': symbol.upper(),
            'filter_entities': 'true',
            'language': 'en',
            'published_after': from_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'published_before': to_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'limit': 3  # Free tier: 3 articles/request
        }

        try:
            data = self._make_request('/news/all', params)

            # Marketaux 응답 구조: {"data": [...], "meta": {...}}
            articles_data = data.get('data', [])

            articles = []
            for item in articles_data:
                try:
                    article = self._parse_article(item)
                    articles.append(article)
                except Exception as e:
                    logger.error(f"Failed to parse Marketaux article: {e}, item: {item}")
                    continue

            logger.info(f"Fetched {len(articles)} company news for {symbol} from Marketaux")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch company news from Marketaux: {e}")
            return []

    def fetch_market_news(
        self,
        category: str = 'general',
        limit: int = 3
    ) -> List[RawNewsArticle]:
        """
        일반 시장 뉴스 가져오기

        Args:
            category: 뉴스 카테고리 (Marketaux는 industries 필터 사용)
            limit: 가져올 뉴스 개수 (최대 3)

        Returns:
            List[RawNewsArticle]: 뉴스 리스트
        """
        params = {
            'language': 'en',
            'limit': min(limit, 3)  # Free tier: 3 articles/request
        }

        # 카테고리별 필터링 (Marketaux는 industries 파라미터 사용)
        # 예: 'Technology', 'Financial', 'Energy' 등
        # 현재는 단순하게 처리
        if category != 'general':
            params['industries'] = category

        try:
            data = self._make_request('/news/all', params)

            articles_data = data.get('data', [])

            articles = []
            for item in articles_data:
                try:
                    article = self._parse_article(item, category=category)
                    articles.append(article)
                except Exception as e:
                    logger.error(f"Failed to parse Marketaux article: {e}, item: {item}")
                    continue

            logger.info(f"Fetched {len(articles)} market news for category '{category}' from Marketaux")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch market news from Marketaux: {e}")
            return []

    def _parse_article(
        self,
        item: Dict[str, Any],
        category: str = 'general'
    ) -> RawNewsArticle:
        """
        Marketaux API 응답을 RawNewsArticle로 변환

        Args:
            item: Marketaux API 응답 아이템
            category: 카테고리

        Returns:
            RawNewsArticle: 파싱된 뉴스 데이터
        """
        # Marketaux 응답 구조:
        # {
        #   "uuid": "...",
        #   "title": "...",
        #   "description": "...",
        #   "url": "https://...",
        #   "image_url": "https://...",
        #   "published_at": "2023-01-01T00:00:00.000000Z",
        #   "source": "Bloomberg",
        #   "entities": [
        #     {
        #       "symbol": "AAPL",
        #       "name": "Apple Inc.",
        #       "exchange": "NASDAQ",
        #       "exchange_long": "NASDAQ",
        #       "country": "us",
        #       "type": "equity",
        #       "industry": "Technology",
        #       "match_score": 0.98765,
        #       "sentiment_score": 0.456,
        #       "highlights": [
        #         {
        #           "highlight": "Apple announced strong earnings",
        #           "sentiment": 0.8,
        #           "highlighted_in": "main_text"
        #         }
        #       ]
        #     }
        #   ]
        # }

        # 엔티티 파싱
        entities = []
        for entity_data in item.get('entities', []):
            entity = {
                'symbol': entity_data.get('symbol', '').upper(),
                'entity_name': entity_data.get('name', ''),
                'entity_type': entity_data.get('type', 'equity'),
                'exchange': entity_data.get('exchange', ''),
                'country': entity_data.get('country', ''),
                'industry': entity_data.get('industry', ''),
                'match_score': Decimal(str(entity_data.get('match_score', 1.0))),
                'sentiment_score': self._safe_decimal(entity_data.get('sentiment_score')),
                'source': 'marketaux',
                'highlights': []
            }

            # 하이라이트 파싱
            for highlight_data in entity_data.get('highlights', []):
                highlight = {
                    'text': highlight_data.get('highlight', ''),
                    'sentiment': self._safe_decimal(highlight_data.get('sentiment')),
                    'location': 'title' if highlight_data.get('highlighted_in') == 'title' else 'main_text'
                }
                entity['highlights'].append(highlight)

            entities.append(entity)

        # 전체 기사 감성 점수 (첫 번째 엔티티의 감성 점수 사용)
        sentiment_score = None
        if entities and entities[0].get('sentiment_score') is not None:
            sentiment_score = entities[0]['sentiment_score']

        # 발행 일시 파싱
        published_at_str = item.get('published_at', '')
        try:
            # ISO 8601 형식: "2023-01-01T00:00:00.000000Z"
            published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Failed to parse published_at: {published_at_str}, error: {e}")
            published_at = datetime.now()

        return RawNewsArticle(
            url=self.normalize_url(item.get('url', '')),
            title=item.get('title', ''),
            summary=item.get('description', ''),
            source=item.get('source', 'Unknown'),
            published_at=published_at,
            image_url=item.get('image_url', ''),
            language=item.get('language', 'en'),
            category=category,
            provider_id=item.get('uuid', ''),
            provider_name='marketaux',
            sentiment_score=sentiment_score,
            sentiment_source='marketaux' if sentiment_score is not None else 'none',
            entities=entities,
            is_press_release=False
        )

    def _safe_decimal(self, value) -> Decimal:
        """
        안전하게 Decimal 변환

        Args:
            value: 변환할 값

        Returns:
            Decimal or None
        """
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def get_rate_limit_key(self) -> str:
        """Rate limit 캐시 키"""
        return "news_rate_limit:marketaux"

    def get_rate_limit(self) -> Dict[str, int]:
        """Rate limit 정보: 100 calls per day"""
        return {'calls': 100, 'period': 86400}  # 86400초 = 24시간
