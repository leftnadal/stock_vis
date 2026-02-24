"""
FMP API 클라이언트

Market Movers 데이터를 FMP API로부터 가져오는 클라이언트.
httpx를 사용하여 동기 HTTP 요청을 수행합니다.

KB 참고: FMP API Market Movers 구현 패턴
"""
import logging
from typing import List, Dict, Optional
import httpx
from django.conf import settings
from django.core.cache import cache


logger = logging.getLogger(__name__)


class FMPAPIError(Exception):
    """FMP API 에러"""
    pass


class FMPClient:
    """
    FMP API 클라이언트 (Starter Plan)

    Usage:
        client = FMPClient()
        gainers = client.get_market_gainers()

    Note:
        - FMP Starter Plan 사용 (유료)
        - 모든 엔드포인트는 /stable/* 사용
        - Rate Limit: 300 calls/분, 10,000 calls/일
    """
    BASE_URL = "https://financialmodelingprep.com"  # /stable/* 엔드포인트 전용

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.FMP_API_KEY
        if not self.api_key:
            raise ValueError("FMP_API_KEY is required")

        self.client = httpx.Client(timeout=30.0)

    def __del__(self):
        """리소스 정리"""
        if hasattr(self, 'client'):
            self.client.close()

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        FMP API 요청 헬퍼

        Args:
            endpoint: API 엔드포인트 (예: /stable/biggest-gainers)
            params: 추가 쿼리 파라미터

        Returns:
            API 응답 (JSON)

        Raises:
            FMPAPIError: API 호출 실패 시
        """
        url = f"{self.BASE_URL}{endpoint}"

        request_params = {'apikey': self.api_key}
        if params:
            request_params.update(params)

        try:
            logger.debug(f"FMP API 요청: {endpoint}")
            response = self.client.get(url, params=request_params)
            response.raise_for_status()

            data = response.json()

            # FMP API는 에러 시에도 200을 반환하고 {"Error Message": "..."} 형태로 응답
            if isinstance(data, dict) and 'Error Message' in data:
                raise FMPAPIError(f"FMP API Error: {data['Error Message']}")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 에러: {e.response.status_code} - {endpoint}")
            raise FMPAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"FMP API 요청 에러: {e} - {endpoint}")
            raise FMPAPIError(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"FMP API 예상치 못한 에러: {e} - {endpoint}")
            raise FMPAPIError(f"Unexpected error: {str(e)}")

    def get_market_gainers(self) -> List[Dict]:
        """
        상승 TOP 종목 (Gainers)

        Returns:
            [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "change": 5.25,
                    "price": 150.00,
                    "changesPercentage": 3.5,
                    "exchange": "NASDAQ"
                },
                ...
            ]
        """
        cache_key = 'fmp:market_gainers'
        cached = cache.get(cache_key)
        if cached:
            logger.debug("FMP 캐시 HIT: market_gainers")
            return cached

        data = self._make_request('/stable/biggest-gainers')
        cache.set(cache_key, data, 300)  # 5분 캐시
        return data

    def get_market_losers(self) -> List[Dict]:
        """
        하락 TOP 종목 (Losers)

        Returns:
            상승 TOP과 동일한 구조
        """
        cache_key = 'fmp:market_losers'
        cached = cache.get(cache_key)
        if cached:
            logger.debug("FMP 캐시 HIT: market_losers")
            return cached

        data = self._make_request('/stable/biggest-losers')
        cache.set(cache_key, data, 300)  # 5분 캐시
        return data

    def get_market_actives(self) -> List[Dict]:
        """
        거래량 TOP 종목 (Actives)

        Returns:
            상승 TOP과 동일한 구조
        """
        cache_key = 'fmp:market_actives'
        cached = cache.get(cache_key)
        if cached:
            logger.debug("FMP 캐시 HIT: market_actives")
            return cached

        data = self._make_request('/stable/most-actives')
        cache.set(cache_key, data, 300)  # 5분 캐시
        return data

    def get_quote(self, symbol: str) -> Dict:
        """
        실시간 시세 (OHLC 포함)

        Args:
            symbol: 종목 심볼 (예: AAPL)

        Returns:
            {
                "symbol": "AAPL",
                "price": 150.00,
                "volume": 100000000,
                "open": 148.50,
                "dayHigh": 151.00,
                "dayLow": 148.00,
                "previousClose": 147.00,
                ...
            }
        """
        cache_key = f'fmp:quote:{symbol.upper()}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"FMP 캐시 HIT: quote:{symbol}")
            return cached

        data = self._make_request(
            '/stable/quote',
            params={'symbol': symbol.upper()}
        )

        # /stable/quote는 리스트로 반환
        if not data or len(data) == 0:
            raise FMPAPIError(f"No quote data for {symbol}")

        quote = data[0]
        cache.set(cache_key, quote, 60)  # 1분 캐시
        return quote

    def get_historical_ohlcv(self, symbol: str, days: int = 20) -> List[Dict]:
        """
        히스토리 OHLCV 데이터

        Args:
            symbol: 종목 심볼
            days: 조회 일수 (기본 20일)

        Returns:
            [
                {
                    "date": "2025-01-05",
                    "open": 148.50,
                    "high": 151.00,
                    "low": 148.00,
                    "close": 150.00,
                    "volume": 100000000
                },
                ...
            ]
        """
        cache_key = f'fmp:historical:{symbol.upper()}:{days}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"FMP 캐시 HIT: historical:{symbol}:{days}")
            return cached

        data = self._make_request(
            '/stable/historical-price-eod/full',
            params={'symbol': symbol.upper()}
        )

        # /stable/historical-price-eod/full은 리스트로 직접 반환
        if not isinstance(data, list):
            raise FMPAPIError(f"Unexpected response format for {symbol}")

        # 최근 N일만 반환
        historical = data[:days] if len(data) > days else data
        cache.set(cache_key, historical, 3600)  # 1시간 캐시
        return historical

    def get_company_profile(self, symbol: str) -> Dict:
        """
        기업 프로필 (섹터 정보 포함)

        Args:
            symbol: 종목 심볼

        Returns:
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                ...
            }
        """
        cache_key = f'fmp:profile:{symbol.upper()}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"FMP 캐시 HIT: profile:{symbol}")
            return cached

        data = self._make_request(
            '/stable/profile',
            params={'symbol': symbol.upper()}
        )

        # /stable/profile은 리스트로 반환
        if not data or len(data) == 0:
            raise FMPAPIError(f"No profile data for {symbol}")

        profile = data[0]
        cache.set(cache_key, profile, 86400)  # 24시간 캐시 (섹터는 자주 변하지 않음)
        return profile

    def get_stock_peers(self, symbol: str) -> List[Dict]:
        """
        종목의 피어(경쟁사) 목록 조회

        Args:
            symbol: 종목 심볼

        Returns:
            피어 종목 리스트 (예: [{"symbol": "MSFT", "companyName": "...", ...}])
        """
        cache_key = f'fmp:peers:{symbol.upper()}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"FMP 캐시 HIT: peers:{symbol}")
            return cached

        data = self._make_request(
            '/stable/stock-peers',
            params={'symbol': symbol.upper()}
        )

        if not isinstance(data, list):
            logger.warning(f"No peers data for {symbol}")
            return []

        cache.set(cache_key, data, 86400)  # 24시간 캐시
        return data

    def get_sector_stocks(self, sector: str, limit: int = 50) -> List[Dict]:
        """
        특정 섹터의 종목 조회

        Args:
            sector: 섹터 이름 (예: "Technology")
            limit: 최대 반환 개수

        Returns:
            종목 리스트
        """
        cache_key = f'fmp:sector_stocks:{sector}:{limit}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"FMP 캐시 HIT: sector_stocks:{sector}")
            return cached

        data = self._make_request(
            '/stable/company-screener',
            params={
                'sector': sector,
                'limit': limit,
                'isEtf': 'false',
                'isFund': 'false',
            }
        )

        if not isinstance(data, list):
            return []

        cache.set(cache_key, data, 300)  # 5분 캐시
        return data

    def get_sp500_constituents(self) -> List[Dict]:
        """
        S&P 500 구성 종목 조회

        datahub.io의 S&P 500 CSV를 사용합니다.
        (FMP /stable/sp500-constituent는 Professional Plan 이상 필요)

        Returns:
            [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "sector": "Technology",
                    "subSector": "Consumer Electronics",
                    "headQuarter": "Cupertino, California",
                    "dateFirstAdded": "1982-11-30",
                    "cik": "0000320193",
                    "founded": "1976",
                },
                ...
            ]
        """
        import csv
        from io import StringIO

        cache_key = 'fmp:sp500_constituents'
        cached = cache.get(cache_key)
        if cached:
            logger.debug("SP500 cache HIT: sp500_constituents")
            return cached

        url = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
        try:
            response = self.client.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"SP500 CSV 다운로드 실패: {e}")
            raise FMPAPIError(f"Failed to fetch SP500 constituents: {e}")

        reader = csv.DictReader(StringIO(response.text))
        data = []
        for row in reader:
            data.append({
                'symbol': row.get('Symbol', '').strip(),
                'name': row.get('Security', ''),
                'sector': row.get('GICS Sector', ''),
                'subSector': row.get('GICS Sub-Industry', ''),
                'headQuarter': row.get('Headquarters Location', ''),
                'dateFirstAdded': row.get('Date added', ''),
                'cik': row.get('CIK', ''),
                'founded': row.get('Founded', ''),
            })

        if not data:
            raise FMPAPIError("SP500 CSV is empty")

        logger.info(f"SP500 구성 종목 {len(data)}개 로드 완료 (datahub.io)")
        cache.set(cache_key, data, 86400)  # 24시간 캐시
        return data

    def get_industry_stocks(self, industry: str, limit: int = 30) -> List[Dict]:
        """
        특정 산업의 종목 조회

        Args:
            industry: 산업 이름 (예: "Semiconductors")
            limit: 최대 반환 개수

        Returns:
            종목 리스트
        """
        cache_key = f'fmp:industry_stocks:{industry}:{limit}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"FMP 캐시 HIT: industry_stocks:{industry}")
            return cached

        data = self._make_request(
            '/stable/company-screener',
            params={
                'industry': industry,
                'limit': limit,
                'isEtf': 'false',
                'isFund': 'false',
            }
        )

        if not isinstance(data, list):
            return []

        cache.set(cache_key, data, 300)  # 5분 캐시
        return data
