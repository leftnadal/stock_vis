"""
FMP API Fundamentals Service

Financial Modeling Prep API를 사용하여 기업의 핵심 재무 데이터를 조회합니다.
- Key Metrics: 핵심 재무 지표
- Ratios: 재무 비율
- DCF: Discounted Cash Flow 분석
- Rating: 투자 등급

캐싱을 통해 API 호출을 최소화하고 성능을 최적화합니다.
"""
import httpx
from django.conf import settings
from django.core.cache import cache
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FMPFundamentalsService:
    """FMP API Fundamentals 서비스 (Starter Plan - Stable API)"""

    BASE_URL = "https://financialmodelingprep.com"
    CACHE_TTL = 600  # 10분

    def __init__(self):
        self.api_key = settings.FMP_API_KEY
        if not self.api_key:
            logger.warning("FMP_API_KEY가 설정되지 않았습니다.")

    def get_key_metrics(self, symbol: str, period: str = 'annual', limit: int = 5) -> list[dict]:
        """
        핵심 재무 지표 조회

        Args:
            symbol: 종목 심볼 (예: AAPL)
            period: 'annual' (연간) 또는 'quarter' (분기)
            limit: 반환할 기간 수 (최대 40개)

        Returns:
            핵심 지표 리스트 (P/E, P/B, ROE, ROA, Debt/Equity 등)
        """
        symbol = symbol.upper()
        cache_key = f"fmp:key_metrics:{symbol}:{period}"

        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached[:limit]

        # API 호출
        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/stable/key-metrics",
                    params={
                        "symbol": symbol,
                        "apikey": self.api_key,
                        "period": period,
                        "limit": limit
                    }
                )
                response.raise_for_status()
                data = response.json()

            # 데이터 검증
            if not isinstance(data, list):
                logger.error(f"FMP API 응답 형식 오류: /stable/key-metrics?symbol={symbol}")
                return []

            # 캐시 저장
            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: key-metrics/{symbol}, {len(data)}개 기간")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (key-metrics/{symbol}): {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error(f"FMP API 타임아웃 (key-metrics/{symbol})")
            return []
        except Exception as e:
            logger.error(f"FMP API 오류 (key-metrics/{symbol}): {e}")
            return []

    def get_ratios(self, symbol: str, period: str = 'annual', limit: int = 5) -> list[dict]:
        """
        재무 비율 조회

        Args:
            symbol: 종목 심볼
            period: 'annual' (연간) 또는 'quarter' (분기)
            limit: 반환할 기간 수 (최대 40개)

        Returns:
            재무 비율 리스트 (유동비율, 당좌비율, 부채비율 등)
        """
        symbol = symbol.upper()
        cache_key = f"fmp:ratios:{symbol}:{period}"

        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached[:limit]

        # API 호출
        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/stable/ratios",
                    params={
                        "symbol": symbol,
                        "apikey": self.api_key,
                        "period": period,
                        "limit": limit
                    }
                )
                response.raise_for_status()
                data = response.json()

            # 데이터 검증
            if not isinstance(data, list):
                logger.error(f"FMP API 응답 형식 오류: /stable/ratios?symbol={symbol}")
                return []

            # 캐시 저장
            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: ratios/{symbol}, {len(data)}개 기간")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (ratios/{symbol}): {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error(f"FMP API 타임아웃 (ratios/{symbol})")
            return []
        except Exception as e:
            logger.error(f"FMP API 오류 (ratios/{symbol}): {e}")
            return []

    def get_dcf(self, symbol: str) -> Optional[dict]:
        """
        DCF (Discounted Cash Flow) 분석 조회

        Args:
            symbol: 종목 심볼

        Returns:
            DCF 분석 결과 (적정 주가, 현재가 대비 할인/프리미엄 등)
        """
        symbol = symbol.upper()
        cache_key = f"fmp:dcf:{symbol}"

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
                response = client.get(
                    f"{self.BASE_URL}/stable/discounted-cash-flow",
                    params={"symbol": symbol, "apikey": self.api_key}
                )
                response.raise_for_status()
                data = response.json()

            # 데이터 검증 (단일 객체 또는 리스트)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            elif not isinstance(data, dict):
                logger.error(f"FMP API 응답 형식 오류: /stable/discounted-cash-flow?symbol={symbol}")
                return None

            # 캐시 저장
            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: dcf/{symbol}")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (dcf/{symbol}): {e.response.status_code}")
            return None
        except httpx.TimeoutException:
            logger.error(f"FMP API 타임아웃 (dcf/{symbol})")
            return None
        except Exception as e:
            logger.error(f"FMP API 오류 (dcf/{symbol}): {e}")
            return None

    def get_rating(self, symbol: str) -> Optional[dict]:
        """
        투자 등급 조회

        Args:
            symbol: 종목 심볼

        Returns:
            투자 등급 정보 (Buy/Sell/Hold 등급, 점수)
        """
        symbol = symbol.upper()
        cache_key = f"fmp:rating:{symbol}"

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
                response = client.get(
                    f"{self.BASE_URL}/stable/rating",
                    params={"symbol": symbol, "apikey": self.api_key}
                )
                response.raise_for_status()
                data = response.json()

            # 데이터 검증 (단일 객체 또는 리스트)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            elif not isinstance(data, dict):
                logger.error(f"FMP API 응답 형식 오류: /stable/rating?symbol={symbol}")
                return None

            # 캐시 저장
            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: rating/{symbol}")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (rating/{symbol}): {e.response.status_code}")
            return None
        except httpx.TimeoutException:
            logger.error(f"FMP API 타임아웃 (rating/{symbol})")
            return None
        except Exception as e:
            logger.error(f"FMP API 오류 (rating/{symbol}): {e}")
            return None

    def get_balance_sheet(self, symbol: str, period: str = 'annual', limit: int = 5) -> list[dict]:
        """
        대차대조표 조회

        Args:
            symbol: 종목 심볼
            period: 'annual' (연간) 또는 'quarter' (분기)
            limit: 반환할 기간 수

        Returns:
            대차대조표 리스트
        """
        symbol = symbol.upper()
        cache_key = f"fmp:balance_sheet:{symbol}:{period}"

        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached[:limit]

        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/stable/balance-sheet-statement",
                    params={
                        "symbol": symbol,
                        "apikey": self.api_key,
                        "period": period,
                        "limit": limit
                    }
                )
                response.raise_for_status()
                data = response.json()

            if not isinstance(data, list):
                logger.error(f"FMP API 응답 형식 오류: /stable/balance-sheet-statement?symbol={symbol}")
                return []

            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: balance-sheet-statement/{symbol}, {len(data)}개 기간")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (balance-sheet-statement/{symbol}): {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error(f"FMP API 타임아웃 (balance-sheet-statement/{symbol})")
            return []
        except Exception as e:
            logger.error(f"FMP API 오류 (balance-sheet-statement/{symbol}): {e}")
            return []

    def get_income_statement(self, symbol: str, period: str = 'annual', limit: int = 5) -> list[dict]:
        """
        손익계산서 조회

        Args:
            symbol: 종목 심볼
            period: 'annual' (연간) 또는 'quarter' (분기)
            limit: 반환할 기간 수

        Returns:
            손익계산서 리스트
        """
        symbol = symbol.upper()
        cache_key = f"fmp:income_statement:{symbol}:{period}"

        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached[:limit]

        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/stable/income-statement",
                    params={
                        "symbol": symbol,
                        "apikey": self.api_key,
                        "period": period,
                        "limit": limit
                    }
                )
                response.raise_for_status()
                data = response.json()

            if not isinstance(data, list):
                logger.error(f"FMP API 응답 형식 오류: /stable/income-statement?symbol={symbol}")
                return []

            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: income-statement/{symbol}, {len(data)}개 기간")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (income-statement/{symbol}): {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error(f"FMP API 타임아웃 (income-statement/{symbol})")
            return []
        except Exception as e:
            logger.error(f"FMP API 오류 (income-statement/{symbol}): {e}")
            return []

    def get_cash_flow_statement(self, symbol: str, period: str = 'annual', limit: int = 5) -> list[dict]:
        """
        현금흐름표 조회

        Args:
            symbol: 종목 심볼
            period: 'annual' (연간) 또는 'quarter' (분기)
            limit: 반환할 기간 수

        Returns:
            현금흐름표 리스트
        """
        symbol = symbol.upper()
        cache_key = f"fmp:cash_flow:{symbol}:{period}"

        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached[:limit]

        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.BASE_URL}/stable/cash-flow-statement",
                    params={
                        "symbol": symbol,
                        "apikey": self.api_key,
                        "period": period,
                        "limit": limit
                    }
                )
                response.raise_for_status()
                data = response.json()

            if not isinstance(data, list):
                logger.error(f"FMP API 응답 형식 오류: /stable/cash-flow-statement?symbol={symbol}")
                return []

            cache.set(cache_key, data, self.CACHE_TTL)
            logger.info(f"FMP API 호출 성공: cash-flow-statement/{symbol}, {len(data)}개 기간")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 오류 (cash-flow-statement/{symbol}): {e.response.status_code}")
            return []
        except httpx.TimeoutException:
            logger.error(f"FMP API 타임아웃 (cash-flow-statement/{symbol})")
            return []
        except Exception as e:
            logger.error(f"FMP API 오류 (cash-flow-statement/{symbol}): {e}")
            return []

    def get_all_fundamentals(self, symbol: str, period: str = 'annual') -> dict:
        """
        전체 펀더멘털 데이터 조회 (한 번에)

        Args:
            symbol: 종목 심볼
            period: 'annual' (연간) 또는 'quarter' (분기)

        Returns:
            {
                'key_metrics': [...],
                'ratios': [...],
                'dcf': {...},
                'rating': {...}
            }
        """
        return {
            "key_metrics": self.get_key_metrics(symbol, period),
            "ratios": self.get_ratios(symbol, period),
            "dcf": self.get_dcf(symbol),
            "rating": self.get_rating(symbol),
        }
