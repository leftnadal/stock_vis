"""
FMP API Exchange Quotes Service

Financial Modeling Prep API를 사용하여 실시간 시세 정보를 조회합니다.
- Index Quotes: 주요 지수 시세 (S&P 500, NASDAQ, Dow Jones 등)
- Stock Quote: 개별 종목 실시간 시세
- Batch Quotes: 여러 종목 일괄 조회

캐싱을 통해 API 호출을 최소화하고 성능을 최적화합니다.
"""
import httpx
from django.conf import settings
from django.core.cache import cache
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FMPExchangeQuotesService:
    """FMP API Exchange Quotes 서비스 (Stable API 사용)"""

    BASE_URL = "https://financialmodelingprep.com/stable"
    LEGACY_URL = "https://financialmodelingprep.com/api/v3"  # 일부 엔드포인트용
    CACHE_TTL = 60  # 1분 (실시간 데이터이므로 짧게)

    def __init__(self):
        self.api_key = settings.FMP_API_KEY
        if not self.api_key:
            logger.warning("FMP_API_KEY가 설정되지 않았습니다.")

    def get_index_quotes(self) -> list[dict]:
        """
        주요 지수 시세 조회

        Returns:
            주요 지수 리스트 (^GSPC, ^DJI, ^IXIC 등)
            각 지수: symbol, name, price, change, changesPercentage
        """
        cache_key = "fmp:quotes:index"

        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached

        # API 호출
        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/quotes/index",
                    params={"apikey": self.api_key}
                )
                response.raise_for_status()
                data = response.json()

            # 데이터 검증
            if not isinstance(data, list):
                logger.error("FMP API 응답 형식 오류: quotes/index")
                return []

            # 캐시 저장
            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: quotes/index, {len(data)}개 지수")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (quotes/index): {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error("FMP API 타임아웃 (quotes/index)")
            return []
        except Exception as e:
            logger.error(f"FMP API 오류 (quotes/index): {e}")
            return []

    def get_quote(self, symbol: str) -> Optional[dict]:
        """
        개별 종목 실시간 시세 조회 (Stable API 사용)

        Args:
            symbol: 종목 심볼 (예: AAPL)

        Returns:
            종목 시세 정보 (price, change, volume, marketCap, pe 등)
        """
        symbol = symbol.upper()
        cache_key = f"fmp:quote:{symbol}"

        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached

        # API 호출
        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return None

        try:
            with httpx.Client(timeout=10.0) as client:
                # Stable API 사용 (쿼리 파라미터로 symbol 전달)
                response = client.get(
                    f"{self.BASE_URL}/quote",
                    params={"symbol": symbol, "apikey": self.api_key}
                )
                response.raise_for_status()
                data = response.json()

            # 데이터 검증 (리스트 형태로 반환되므로 첫 번째 요소 추출)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            elif not isinstance(data, dict):
                logger.error(f"FMP API 응답 형식 오류: quote/{symbol}")
                return None

            # 캐시 저장
            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: quote/{symbol}")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (quote/{symbol}): {e.response.status_code}")
            return None
        except httpx.TimeoutException:
            logger.error(f"FMP API 타임아웃 (quote/{symbol})")
            return None
        except Exception as e:
            logger.error(f"FMP API 오류 (quote/{symbol}): {e}")
            return None

    def get_batch_quotes(self, symbols: list[str]) -> list[dict]:
        """
        여러 종목 일괄 시세 조회 (Stable API 사용)

        Args:
            symbols: 종목 심볼 리스트 (예: ['AAPL', 'MSFT', 'GOOGL'])

        Returns:
            종목 시세 리스트
        """
        if not symbols:
            return []

        # 심볼 대문자 변환 및 중복 제거
        symbols = list(set([s.upper() for s in symbols]))
        symbols_str = ",".join(symbols)

        cache_key = f"fmp:quotes:batch:{hash(symbols_str)}"

        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached

        # API 호출
        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                # Stable API 사용 (쿼리 파라미터로 symbol 전달)
                response = client.get(
                    f"{self.BASE_URL}/quote",
                    params={"symbol": symbols_str, "apikey": self.api_key}
                )
                response.raise_for_status()
                data = response.json()

            # 데이터 검증
            if not isinstance(data, list):
                logger.error("FMP API 응답 형식 오류: batch quotes")
                return []

            # 캐시 저장
            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: batch quotes, {len(symbols)}개 종목")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (batch quotes): {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error("FMP API 타임아웃 (batch quotes)")
            return []
        except Exception as e:
            logger.error(f"FMP API 오류 (batch quotes): {e}")
            return []

    def get_major_indices(self) -> dict:
        """
        주요 지수 (S&P 500, NASDAQ, Dow Jones) 조회

        Returns:
            {
                'sp500': {...},
                'nasdaq': {...},
                'dow_jones': {...}
            }
        """
        indices = self.get_index_quotes()

        # 주요 지수 필터링
        result = {}
        symbol_map = {
            "^GSPC": "sp500",
            "^IXIC": "nasdaq",
            "^DJI": "dow_jones"
        }

        for index in indices:
            symbol = index.get("symbol")
            if symbol in symbol_map:
                result[symbol_map[symbol]] = index

        return result

    def get_sector_performance(self) -> list[dict]:
        """
        섹터 ETF 시세 조회 (섹터별 성과 확인용)

        Returns:
            섹터 ETF 리스트 (XLK, XLF, XLV, XLE 등)
        """
        sector_etfs = [
            "XLK",  # Technology
            "XLF",  # Financials
            "XLV",  # Healthcare
            "XLE",  # Energy
            "XLI",  # Industrials
            "XLP",  # Consumer Staples
            "XLY",  # Consumer Discretionary
            "XLU",  # Utilities
            "XLRE", # Real Estate
            "XLB",  # Materials
            "XLC",  # Communication Services
        ]

        return self.get_batch_quotes(sector_etfs)
