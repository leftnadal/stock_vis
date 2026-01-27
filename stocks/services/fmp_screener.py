"""
FMP API Stock Screener Service

Financial Modeling Prep API를 사용하여 조건별 종목 검색을 수행합니다.
- 시가총액, 베타, 거래량, 섹터, 거래소 등 다양한 필터 지원
- 가격 범위, 배당률, P/E 비율 등 추가 필터 지원

캐싱을 통해 API 호출을 최소화하고 성능을 최적화합니다.
"""
import httpx
import time
from django.conf import settings
from django.core.cache import cache
from typing import Optional
import logging

from serverless.services.quote_enricher import QuoteEnricher

logger = logging.getLogger(__name__)


class FMPScreenerService:
    """FMP API Stock Screener 서비스"""

    BASE_URL = "https://financialmodelingprep.com/stable"
    CACHE_TTL = 300  # 5분
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # 초

    def __init__(self):
        self.api_key = settings.FMP_API_KEY
        if not self.api_key:
            logger.warning("FMP_API_KEY가 설정되지 않았습니다.")

    def screen_stocks(
        self,
        market_cap_more_than: Optional[int] = None,
        market_cap_lower_than: Optional[int] = None,
        price_more_than: Optional[float] = None,
        price_lower_than: Optional[float] = None,
        beta_more_than: Optional[float] = None,
        beta_lower_than: Optional[float] = None,
        volume_more_than: Optional[int] = None,
        volume_lower_than: Optional[int] = None,
        dividend_more_than: Optional[float] = None,
        dividend_lower_than: Optional[float] = None,
        is_etf: Optional[bool] = None,
        is_actively_trading: Optional[bool] = True,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 100
    ) -> list[dict]:
        """
        조건별 종목 검색

        Args:
            market_cap_more_than: 최소 시가총액
            market_cap_lower_than: 최대 시가총액
            price_more_than: 최소 주가
            price_lower_than: 최대 주가
            beta_more_than: 최소 베타
            beta_lower_than: 최대 베타
            volume_more_than: 최소 거래량
            volume_lower_than: 최대 거래량
            dividend_more_than: 최소 배당률 (%)
            dividend_lower_than: 최대 배당률 (%)
            is_etf: ETF 여부
            is_actively_trading: 활성 거래 종목만 (기본값: True)
            sector: 섹터 필터 (예: Technology, Healthcare)
            industry: 산업 필터
            exchange: 거래소 필터 (NYSE, NASDAQ, AMEX 등)
            limit: 반환할 종목 수 (최대 1000개)

        Returns:
            종목 리스트 (symbol, name, price, marketCap, sector 등)
        """
        # 캐시 키 생성 (파라미터 기반)
        cache_params = {
            "mkt_cap_more": market_cap_more_than,
            "mkt_cap_less": market_cap_lower_than,
            "price_more": price_more_than,
            "price_less": price_lower_than,
            "beta_more": beta_more_than,
            "beta_less": beta_lower_than,
            "vol_more": volume_more_than,
            "vol_less": volume_lower_than,
            "div_more": dividend_more_than,
            "div_less": dividend_lower_than,
            "is_etf": is_etf,
            "is_active": is_actively_trading,
            "sector": sector,
            "industry": industry,
            "exchange": exchange,
            "limit": limit,
        }
        cache_key = f"fmp:screener:{hash(frozenset(cache_params.items()))}"

        # 캐시 확인
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return cached

        # API 호출
        if not self.api_key:
            logger.error("FMP API 호출 실패: API 키가 없습니다.")
            return []

        # API 파라미터 구성 (None이 아닌 값만)
        params = {"apikey": self.api_key}

        if market_cap_more_than is not None:
            params["marketCapMoreThan"] = market_cap_more_than
        if market_cap_lower_than is not None:
            params["marketCapLowerThan"] = market_cap_lower_than
        if price_more_than is not None:
            params["priceMoreThan"] = price_more_than
        if price_lower_than is not None:
            params["priceLowerThan"] = price_lower_than
        if beta_more_than is not None:
            params["betaMoreThan"] = beta_more_than
        if beta_lower_than is not None:
            params["betaLowerThan"] = beta_lower_than
        if volume_more_than is not None:
            params["volumeMoreThan"] = volume_more_than
        if volume_lower_than is not None:
            params["volumeLowerThan"] = volume_lower_than
        if dividend_more_than is not None:
            params["dividendMoreThan"] = dividend_more_than
        if dividend_lower_than is not None:
            params["dividendLowerThan"] = dividend_lower_than
        if is_etf is not None:
            params["isEtf"] = str(is_etf).lower()
        if is_actively_trading is not None:
            params["isActivelyTrading"] = str(is_actively_trading).lower()
        if sector:
            params["sector"] = sector
        if industry:
            params["industry"] = industry
        if exchange:
            params["exchange"] = exchange
        if limit:
            params["limit"] = limit

        # Retry 로직을 포함한 API 호출
        data = self._make_api_request_with_retry(params, cache_key)
        return data if data is not None else []

    def _make_api_request_with_retry(
        self,
        params: dict,
        cache_key: str
    ) -> Optional[list]:
        """
        Exponential Backoff을 적용한 API 요청

        429 Rate Limit 에러 시 재시도
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                with httpx.Client(timeout=15.0) as client:
                    response = client.get(
                        f"{self.BASE_URL}/company-screener",
                        params=params
                    )

                    # 429 Rate Limit 처리
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', self.RETRY_BASE_DELAY * (2 ** attempt)))
                        logger.warning(
                            f"FMP Rate Limit 도달 (429), {retry_after}초 후 재시도 ({attempt + 1}/{self.MAX_RETRIES})"
                        )

                        # 마지막 시도가 아니면 대기 후 재시도
                        if attempt < self.MAX_RETRIES - 1:
                            time.sleep(min(retry_after, 30))  # 최대 30초 대기
                            continue

                        # 캐시된 데이터 반환 시도 (Graceful Degradation)
                        cached = cache.get(cache_key)
                        if cached:
                            logger.info("Rate Limit으로 인해 만료된 캐시 반환")
                            return cached
                        return None

                    response.raise_for_status()
                    data = response.json()

                # 데이터 검증
                if not isinstance(data, list):
                    logger.error("FMP API 응답 형식 오류: company-screener")
                    return None

                # 캐시 저장
                cache.set(cache_key, data, self.CACHE_TTL)
                logger.info(f"FMP API 호출 성공: company-screener, {len(data)}개 종목")

                return data

            except httpx.HTTPStatusError as e:
                logger.error(f"FMP API HTTP 오류 (company-screener): {e.response.status_code}")

                # 5xx 서버 에러는 재시도
                if e.response.status_code >= 500 and attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"서버 에러, {delay}초 후 재시도 ({attempt + 1}/{self.MAX_RETRIES})")
                    time.sleep(delay)
                    continue

                return None

            except httpx.TimeoutException:
                logger.error(f"FMP API 타임아웃 (company-screener), 시도 {attempt + 1}/{self.MAX_RETRIES}")

                # 타임아웃도 재시도
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    time.sleep(delay)
                    continue

                return None

            except Exception as e:
                logger.error(f"FMP API 오류 (company-screener): {e}")
                return None

        return None

    def get_large_cap_stocks(self, limit: int = 50) -> list[dict]:
        """
        대형주 검색 (시가총액 100억 달러 이상)

        Args:
            limit: 반환할 종목 수

        Returns:
            대형주 리스트
        """
        return self.screen_stocks(
            market_cap_more_than=10_000_000_000,  # $10B+
            is_actively_trading=True,
            limit=limit
        )

    def get_high_dividend_stocks(self, min_dividend: float = 3.0, limit: int = 50) -> list[dict]:
        """
        고배당주 검색

        Args:
            min_dividend: 최소 배당률 (%, 기본값: 3.0)
            limit: 반환할 종목 수

        Returns:
            고배당주 리스트
        """
        return self.screen_stocks(
            dividend_more_than=min_dividend,
            is_actively_trading=True,
            limit=limit
        )

    def get_sector_stocks(self, sector: str, limit: int = 100) -> list[dict]:
        """
        특정 섹터 종목 검색

        Args:
            sector: 섹터명 (예: Technology, Healthcare, Financials)
            limit: 반환할 종목 수

        Returns:
            해당 섹터 종목 리스트
        """
        return self.screen_stocks(
            sector=sector,
            is_actively_trading=True,
            limit=limit
        )

    def get_low_beta_stocks(self, max_beta: float = 0.8, limit: int = 50) -> list[dict]:
        """
        저변동성 종목 검색 (베타 < 0.8)

        Args:
            max_beta: 최대 베타 (기본값: 0.8)
            limit: 반환할 종목 수

        Returns:
            저변동성 종목 리스트
        """
        return self.screen_stocks(
            beta_lower_than=max_beta,
            is_actively_trading=True,
            limit=limit
        )

    def get_exchange_stocks(self, exchange: str, limit: int = 100) -> list[dict]:
        """
        특정 거래소 종목 검색

        Args:
            exchange: 거래소 코드 (NYSE, NASDAQ, AMEX 등)
            limit: 반환할 종목 수

        Returns:
            해당 거래소 종목 리스트
        """
        return self.screen_stocks(
            exchange=exchange.upper(),
            is_actively_trading=True,
            limit=limit
        )

    def enrich_with_quotes(self, stocks: list[dict]) -> list[dict]:
        """
        스크리너 결과에 시세 정보(변동률 등)를 추가

        Args:
            stocks: company-screener 결과 리스트

        Returns:
            quote 정보가 추가된 종목 리스트
        """
        enricher = QuoteEnricher(api_key=self.api_key)
        return enricher.enrich_stocks(stocks)
