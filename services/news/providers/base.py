"""
뉴스 Provider 베이스 클래스

모든 뉴스 API Provider는 이 클래스를 상속받아 구현
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .url_utils import normalize_news_url


@dataclass
class RawNewsArticle:
    """
    Provider로부터 받은 원본 뉴스 데이터 구조
    """

    url: str
    title: str
    summary: str
    source: str
    published_at: datetime
    image_url: Optional[str] = None
    language: str = "en"
    category: str = "general"

    # Provider 고유 ID
    provider_id: Optional[str] = None
    provider_name: str = ""

    # 감성 분석 (Marketaux 제공)
    sentiment_score: Optional[Decimal] = None
    sentiment_source: str = "none"

    # 연관 엔티티 (종목)
    entities: List[Dict[str, Any]] = None

    # 기타
    is_press_release: bool = False

    def __post_init__(self):
        if self.entities is None:
            self.entities = []


class BaseNewsProvider(ABC):
    """
    뉴스 Provider 추상 베이스 클래스

    모든 뉴스 API Provider는 이 클래스를 상속받아 구현해야 함
    """

    @abstractmethod
    def fetch_company_news(
        self, symbol: str, from_date: datetime, to_date: datetime
    ) -> List[RawNewsArticle]:
        """
        종목별 뉴스 가져오기

        Args:
            symbol: 주식 심볼 (e.g., "AAPL")
            from_date: 시작 날짜
            to_date: 종료 날짜

        Returns:
            List[RawNewsArticle]: 원본 뉴스 데이터 리스트
        """
        pass

    @abstractmethod
    def fetch_market_news(
        self, category: str = "general", limit: int = 50
    ) -> List[RawNewsArticle]:
        """
        일반 시장 뉴스 가져오기

        Args:
            category: 뉴스 카테고리 (general, forex, crypto, merger)
            limit: 가져올 뉴스 개수

        Returns:
            List[RawNewsArticle]: 원본 뉴스 데이터 리스트
        """
        pass

    @abstractmethod
    def get_rate_limit_key(self) -> str:
        """
        Rate limit 체크용 캐시 키 반환

        Returns:
            str: 캐시 키 (e.g., "news_rate_limit:finnhub")
        """
        pass

    @abstractmethod
    def get_rate_limit(self) -> Dict[str, int]:
        """
        Rate limit 정보 반환

        Returns:
            Dict[str, int]: {'calls': 60, 'period': 60} (60 calls per 60 seconds)
        """
        pass

    def normalize_url(self, url: str) -> str:
        """
        URL 정규화 (중복 체크용).

        정규화 규칙의 단일 소스는 `url_utils.normalize_news_url` (S3, provider 공통).
        모든 provider(AV/FMP/finnhub/marketaux)가 이 경로로 동일 규칙 적용.
        """
        return normalize_news_url(url)
