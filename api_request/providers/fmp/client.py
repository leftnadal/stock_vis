# api_request/providers/fmp/client.py
"""
Financial Modeling Prep (FMP) API Client

FMP API와의 HTTP 통신을 담당합니다.
Rate limiting과 에러 핸들링을 포함합니다.

FMP API 문서: https://site.financialmodelingprep.com/developer/docs
"""

import requests
import logging
import time
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)


class FMPClientError(Exception):
    """FMP Client 에러 기본 클래스"""
    pass


class FMPRateLimitError(FMPClientError):
    """Rate Limit 초과 에러"""
    pass


class FMPAuthError(FMPClientError):
    """인증 에러"""
    pass


class FMPClient:
    """
    Financial Modeling Prep API Client (Starter Plan)

    주요 특징:
    - Starter Plan 사용 (유료)
    - 모든 엔드포인트는 /stable/* 사용
    - Rate Limit: 10 calls/분, 250 calls/일
    - Rate limiting 자동 처리
    - 재시도 로직 포함
    """

    BASE_URL = "https://financialmodelingprep.com"

    def __init__(
        self,
        api_key: str,
        request_delay: float = 0.5,  # FMP는 Alpha Vantage보다 관대
        max_retries: int = 3
    ):
        """
        Args:
            api_key: FMP API 키
            request_delay: 요청 간 대기 시간 (초)
            max_retries: 최대 재시도 횟수
        """
        self.api_key = api_key
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.last_request_time = 0
        self.daily_calls = 0
        self.daily_limit = 250

        if not self.api_key:
            raise ValueError("FMP API Key is required")

    def _get_url(self, endpoint: str) -> str:
        """API URL 생성 (/stable/* 엔드포인트)"""
        return f"{self.BASE_URL}{endpoint}"

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        FMP API 요청 실행

        Args:
            endpoint: API 엔드포인트 (예: "/stable/quote")
            params: 추가 쿼리 파라미터

        Returns:
            API 응답 데이터 (JSON parsed)
        """
        # API 키 추가
        if params is None:
            params = {}
        params["apikey"] = self.api_key

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.debug(f"FMP rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        # 일일 한도 체크
        if self.daily_calls >= self.daily_limit:
            logger.warning(f"FMP daily limit reached ({self.daily_limit} calls)")
            raise FMPRateLimitError("Daily API limit exceeded")

        url = self._get_url(endpoint)
        logger.debug(f"FMP request: {endpoint}")

        # 재시도 로직
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, timeout=30)
                self.last_request_time = time.time()
                self.daily_calls += 1

                # HTTP 에러 체크
                if response.status_code == 401:
                    raise FMPAuthError("Invalid API key")
                elif response.status_code == 403:
                    raise FMPAuthError("API access forbidden")
                elif response.status_code == 429:
                    raise FMPRateLimitError("Rate limit exceeded")
                elif response.status_code != 200:
                    logger.error(f"FMP HTTP error {response.status_code}: {response.text}")
                    response.raise_for_status()

                data = response.json()

                # FMP 에러 응답 체크
                if isinstance(data, dict) and "Error Message" in data:
                    error_msg = data["Error Message"]
                    if "Invalid API KEY" in error_msg:
                        raise FMPAuthError(error_msg)
                    raise FMPClientError(error_msg)

                return data

            except (requests.RequestException, FMPClientError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"FMP request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"FMP request failed after {self.max_retries} attempts: {e}")
                    raise

        raise last_error

    # ============================================================
    # Quote / Price Endpoints
    # ============================================================

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        실시간 시세 조회

        Args:
            symbol: 주식 심볼 (예: "AAPL")

        Returns:
            시세 데이터

        API: GET /stable/quote?symbol={symbol}
        """
        data = self._make_request("/stable/quote", {"symbol": symbol.upper()})
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}

    def get_quote_short(self, symbol: str) -> Dict[str, Any]:
        """
        간단한 시세 조회 (더 적은 데이터)

        API: GET /stable/quote-short?symbol={symbol}
        """
        data = self._make_request("/stable/quote-short", {"symbol": symbol.upper()})
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}

    def get_historical_price(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        과거 일별 가격 데이터 조회

        Args:
            symbol: 주식 심볼
            from_date: 시작일 (YYYY-MM-DD)
            to_date: 종료일 (YYYY-MM-DD)

        Returns:
            일별 가격 리스트

        API: GET /stable/historical-price-eod/full?symbol={symbol}
        """
        params = {"symbol": symbol.upper()}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        data = self._make_request("/stable/historical-price-eod/full", params)

        # /stable/historical-price-eod/full은 리스트로 직접 반환
        if isinstance(data, list):
            return data
        return []

    # ============================================================
    # Company Profile Endpoints
    # ============================================================

    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """
        회사 프로필 조회

        Args:
            symbol: 주식 심볼

        Returns:
            회사 프로필 데이터

        API: GET /stable/profile?symbol={symbol}
        """
        data = self._make_request("/stable/profile", {"symbol": symbol.upper()})
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}

    def get_key_metrics(self, symbol: str, period: str = "annual") -> List[Dict[str, Any]]:
        """
        핵심 재무 지표 조회

        Args:
            symbol: 주식 심볼
            period: "annual" 또는 "quarterly"

        Returns:
            핵심 지표 리스트

        API: GET /stable/key-metrics?symbol={symbol}
        """
        params = {"symbol": symbol.upper(), "period": period}
        data = self._make_request("/stable/key-metrics", params)
        return data if isinstance(data, list) else []

    def get_ratios(self, symbol: str, period: str = "annual") -> List[Dict[str, Any]]:
        """
        재무 비율 조회

        Args:
            symbol: 주식 심볼
            period: "annual" 또는 "quarterly"

        Returns:
            재무 비율 리스트

        API: GET /stable/ratios?symbol={symbol}
        """
        params = {"symbol": symbol.upper(), "period": period}
        data = self._make_request("/stable/ratios", params)
        return data if isinstance(data, list) else []

    # ============================================================
    # Financial Statement Endpoints
    # ============================================================

    def get_income_statement(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        손익계산서 조회

        Args:
            symbol: 주식 심볼
            period: "annual" 또는 "quarterly"
            limit: 반환할 레코드 수

        Returns:
            손익계산서 리스트

        API: GET /stable/income-statement?symbol={symbol}
        """
        params = {"symbol": symbol.upper(), "period": period, "limit": limit}
        data = self._make_request("/stable/income-statement", params)
        return data if isinstance(data, list) else []

    def get_balance_sheet(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        대차대조표 조회

        Args:
            symbol: 주식 심볼
            period: "annual" 또는 "quarterly"
            limit: 반환할 레코드 수

        Returns:
            대차대조표 리스트

        API: GET /stable/balance-sheet-statement?symbol={symbol}
        """
        params = {"symbol": symbol.upper(), "period": period, "limit": limit}
        data = self._make_request("/stable/balance-sheet-statement", params)
        return data if isinstance(data, list) else []

    def get_cash_flow(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        현금흐름표 조회

        Args:
            symbol: 주식 심볼
            period: "annual" 또는 "quarterly"
            limit: 반환할 레코드 수

        Returns:
            현금흐름표 리스트

        API: GET /stable/cash-flow-statement?symbol={symbol}
        """
        params = {"symbol": symbol.upper(), "period": period, "limit": limit}
        data = self._make_request("/stable/cash-flow-statement", params)
        return data if isinstance(data, list) else []

    # ============================================================
    # Search Endpoints
    # ============================================================

    def search_ticker(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        종목 검색

        Args:
            query: 검색어
            limit: 반환할 결과 수

        Returns:
            검색 결과 리스트

        API: GET /stable/search?query={query}
        """
        params = {"query": query, "limit": limit}
        data = self._make_request("/stable/search", params)
        return data if isinstance(data, list) else []

    def search_name(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        회사명으로 검색

        Args:
            query: 검색어
            limit: 반환할 결과 수

        Returns:
            검색 결과 리스트

        API: GET /stable/search-name?query={query}
        """
        params = {"query": query, "limit": limit}
        data = self._make_request("/stable/search-name", params)
        return data if isinstance(data, list) else []

    # ============================================================
    # Sector / Market Endpoints
    # ============================================================

    def get_sector_performance(self) -> List[Dict[str, Any]]:
        """
        섹터 성과 조회

        Returns:
            섹터별 성과 데이터

        API: GET /stable/sector-performance
        """
        data = self._make_request("/stable/sector-performance")
        return data if isinstance(data, list) else []

    def get_stock_list(self) -> List[Dict[str, Any]]:
        """
        전체 상장 종목 리스트

        Returns:
            종목 리스트

        API: GET /stable/stock-list
        """
        data = self._make_request("/stable/stock-list")
        return data if isinstance(data, list) else []

    # ============================================================
    # Utility Methods
    # ============================================================

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """현재 Rate Limit 상태"""
        return {
            "daily_calls": self.daily_calls,
            "daily_limit": self.daily_limit,
            "remaining": self.daily_limit - self.daily_calls,
            "last_request_time": datetime.fromtimestamp(self.last_request_time).isoformat()
            if self.last_request_time else None
        }

    def reset_daily_counter(self) -> None:
        """일일 카운터 리셋 (매일 자정 호출)"""
        self.daily_calls = 0
        logger.info("FMP daily call counter reset")
