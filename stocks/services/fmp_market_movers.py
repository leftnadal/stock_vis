"""
FMP API Market Movers Service

Financial Modeling Prep API를 사용하여 시장 주도 종목(상승/하락/거래량 TOP)을 조회합니다.
캐싱을 통해 API 호출을 최소화하고 성능을 최적화합니다.
"""
import httpx
from django.conf import settings
from django.core.cache import cache
from typing import Literal
import logging

logger = logging.getLogger(__name__)


class FMPMarketMoversService:
    """FMP API Market Movers 서비스 (Stable API 사용)"""

    BASE_URL = "https://financialmodelingprep.com/stable"
    CACHE_TTL = 300  # 5분

    # 새 Stable API 엔드포인트 매핑
    ENDPOINT_MAP = {
        'gainers': 'biggest-gainers',
        'losers': 'biggest-losers',
        'actives': 'most-actives',
    }

    def __init__(self):
        self.api_key = settings.FMP_API_KEY
        if not self.api_key:
            logger.warning("FMP_API_KEY가 설정되지 않았습니다.")

    def get_market_movers(
        self,
        mover_type: Literal['gainers', 'losers', 'actives'],
        limit: int = 10
    ) -> list[dict]:
        """
        시장 주도 종목 조회 (동기)

        Args:
            mover_type: 'gainers' (상승), 'losers' (하락), 'actives' (거래량)
            limit: 반환할 종목 수 (최대 20개)

        Returns:
            종목 리스트 (symbol, name, price, change, changesPercentage 등)
        """
        cache_key = f"fmp:market_movers:{mover_type}"

        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached[:limit]

        # API 호출
        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return []

        endpoint = self.ENDPOINT_MAP.get(mover_type, mover_type)

        try:
            with httpx.Client(timeout=10.0) as client:
                # FMP Stable API 엔드포인트 사용
                response = client.get(
                    f"{self.BASE_URL}/{endpoint}",
                    params={"apikey": self.api_key}
                )
                response.raise_for_status()
                data = response.json()

            # 데이터 검증
            if not isinstance(data, list):
                logger.error(f"FMP API 응답 형식 오류: {mover_type}")
                return []

            # 캐시 저장
            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: {mover_type}, {len(data)}개 종목")

            return data[:limit]

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 ({mover_type}): {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error(f"FMP API 타임아웃 ({mover_type})")
            return []
        except Exception as e:
            logger.error(f"FMP API 오류 ({mover_type}): {e}")
            return []

    def get_all_movers(self, limit: int = 10) -> dict:
        """
        상승/하락/거래량 TOP 전체 조회

        Args:
            limit: 각 카테고리별 종목 수 (최대 20개)

        Returns:
            {
                'gainers': [...],
                'losers': [...],
                'actives': [...],
                'cached_at': ISO timestamp
            }
        """
        from datetime import datetime

        return {
            "gainers": self.get_market_movers('gainers', limit),
            "losers": self.get_market_movers('losers', limit),
            "actives": self.get_market_movers('actives', limit),
            "cached_at": datetime.now().isoformat(),
        }
