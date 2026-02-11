"""
FMP (Financial Modeling Prep) API Client

시장 지수, 섹터 성과, 환율, 원자재 데이터 제공
- Starter Plan (유료): 250 calls/일
- 모든 엔드포인트는 /stable/* 사용
"""
import logging
import time
from datetime import datetime, date
from typing import Dict, Any, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class FMPClient:
    """FMP API 클라이언트 (Starter Plan - Stable API)"""

    BASE_URL = "https://financialmodelingprep.com"

    # 주요 지수 심볼
    INDEX_SYMBOLS = {
        # 미국 주요 지수
        '^GSPC': 'S&P 500',
        '^DJI': 'Dow Jones Industrial Average',
        '^IXIC': 'NASDAQ Composite',
        '^RUT': 'Russell 2000',
        '^VIX': 'CBOE Volatility Index',

        # 글로벌 지수
        '^FTSE': 'FTSE 100',
        '^GDAXI': 'DAX',
        '^N225': 'Nikkei 225',
        '^HSI': 'Hang Seng Index',
    }

    # 섹터 ETF 심볼
    SECTOR_ETFS = {
        'XLK': 'Technology',
        'XLF': 'Financials',
        'XLV': 'Healthcare',
        'XLE': 'Energy',
        'XLI': 'Industrials',
        'XLP': 'Consumer Staples',
        'XLY': 'Consumer Discretionary',
        'XLU': 'Utilities',
        'XLRE': 'Real Estate',
        'XLB': 'Materials',
        'XLC': 'Communication Services',
    }

    # 주요 상품
    COMMODITIES = {
        'GCUSD': 'Gold',
        'SIUSD': 'Silver',
        'CLUSD': 'Crude Oil (WTI)',
        'NGUSD': 'Natural Gas',
    }

    # 주요 환율
    FOREX = {
        'EURUSD': 'EUR/USD',
        'USDJPY': 'USD/JPY',
        'GBPUSD': 'GBP/USD',
        'USDCNY': 'USD/CNY',
        'USDKRW': 'USD/KRW',
    }

    def __init__(self, api_key: str = None, request_delay: float = 0.5):
        """
        Args:
            api_key: FMP API 키
            request_delay: 요청 간 대기 시간 (초)
        """
        self.api_key = api_key or getattr(settings, 'FMP_API_KEY', None)
        self.request_delay = request_delay
        self.last_request_time = 0

        if not self.api_key:
            logger.warning("FMP API Key not found. Set FMP_API_KEY in settings.")

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, str] = None
    ) -> Any:
        """
        FMP API 요청

        Args:
            endpoint: API 엔드포인트 (예: /stable/quote)
            params: 쿼리 파라미터

        Returns:
            API 응답 데이터
        """
        if params is None:
            params = {}

        params['apikey'] = self.api_key

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)

        url = f"{self.BASE_URL}{endpoint}"
        logger.info(f"FMP API Request: {endpoint}")

        try:
            response = requests.get(url, params=params, timeout=30)
            self.last_request_time = time.time()

            if response.status_code != 200:
                logger.error(f"FMP API Error {response.status_code}: {response.text}")
                response.raise_for_status()

            data = response.json()

            # FMP 에러 응답 처리
            if isinstance(data, dict) and 'Error Message' in data:
                logger.error(f"FMP API Error: {data['Error Message']}")
                raise ValueError(data['Error Message'])

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"FMP API Request failed: {e}")
            raise

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        실시간 시세 조회

        Args:
            symbol: 심볼 (예: 'AAPL', '^GSPC')

        Returns:
            시세 데이터
        """
        try:
            data = self._make_request("/stable/quote", {"symbol": symbol})
            if data and len(data) > 0:
                return data[0]
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
        return None

    def get_batch_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        복수 심볼 시세 조회

        Args:
            symbols: 심볼 리스트

        Returns:
            시세 리스트
        """
        try:
            symbols_str = ','.join(symbols)
            data = self._make_request("/stable/quote", {"symbol": symbols_str})
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to fetch batch quotes: {e}")
            return []

    def get_market_indices(self) -> Dict[str, Any]:
        """
        주요 시장 지수 조회

        Returns:
            지수별 시세 데이터
        """
        indices = {}
        symbols = list(self.INDEX_SYMBOLS.keys())

        quotes = self.get_batch_quotes(symbols)

        for quote in quotes:
            symbol = quote.get('symbol', '')
            if symbol in self.INDEX_SYMBOLS:
                indices[symbol] = {
                    'name': self.INDEX_SYMBOLS[symbol],
                    'price': quote.get('price'),
                    'change': quote.get('change'),
                    'change_percent': quote.get('changesPercentage'),
                    'previous_close': quote.get('previousClose'),
                    'day_high': quote.get('dayHigh'),
                    'day_low': quote.get('dayLow'),
                    'timestamp': quote.get('timestamp'),
                }

        return indices

    def get_sector_performance(self) -> Dict[str, Any]:
        """
        섹터별 성과 조회 (섹터 ETF 기준)

        Returns:
            섹터별 성과 데이터
        """
        sectors = {}
        symbols = list(self.SECTOR_ETFS.keys())

        quotes = self.get_batch_quotes(symbols)

        for quote in quotes:
            symbol = quote.get('symbol', '')
            if symbol in self.SECTOR_ETFS:
                sectors[symbol] = {
                    'name': self.SECTOR_ETFS[symbol],
                    'price': quote.get('price'),
                    'change_percent': quote.get('changesPercentage'),
                    'ytd_return': quote.get('priceAvg200'),  # 대략적 참고
                }

        # 성과 순으로 정렬
        sorted_sectors = sorted(
            sectors.items(),
            key=lambda x: x[1].get('change_percent') or 0,
            reverse=True
        )

        return {
            'sectors': dict(sorted_sectors),
            'best_performer': sorted_sectors[0] if sorted_sectors else None,
            'worst_performer': sorted_sectors[-1] if sorted_sectors else None,
        }

    def get_sector_historical_performance(self) -> List[Dict[str, Any]]:
        """
        섹터 성과 API (FMP 제공)

        Returns:
            섹터별 성과 리스트
        """
        try:
            data = self._make_request("/stable/sector-performance")
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to fetch sector performance: {e}")
            return []

    def get_commodities(self) -> Dict[str, Any]:
        """
        원자재 시세 조회

        Returns:
            원자재별 시세 데이터
        """
        commodities = {}
        symbols = list(self.COMMODITIES.keys())

        quotes = self.get_batch_quotes(symbols)

        for quote in quotes:
            symbol = quote.get('symbol', '')
            if symbol in self.COMMODITIES:
                commodities[symbol] = {
                    'name': self.COMMODITIES[symbol],
                    'price': quote.get('price'),
                    'change': quote.get('change'),
                    'change_percent': quote.get('changesPercentage'),
                }

        return commodities

    def get_forex_rates(self) -> Dict[str, Any]:
        """
        주요 환율 조회

        Returns:
            환율 데이터
        """
        forex = {}
        symbols = list(self.FOREX.keys())

        quotes = self.get_batch_quotes(symbols)

        for quote in quotes:
            symbol = quote.get('symbol', '')
            if symbol in self.FOREX:
                forex[symbol] = {
                    'name': self.FOREX[symbol],
                    'price': quote.get('price'),
                    'change': quote.get('change'),
                    'change_percent': quote.get('changesPercentage'),
                }

        return forex

    def get_dollar_index(self) -> Optional[Dict[str, Any]]:
        """
        달러 인덱스 (DXY) 조회

        Returns:
            DXY 데이터
        """
        try:
            quote = self.get_quote('DX-Y.NYB')
            if quote:
                return {
                    'value': quote.get('price'),
                    'change': quote.get('change'),
                    'change_percent': quote.get('changesPercentage'),
                    'timestamp': quote.get('timestamp'),
                }
        except Exception as e:
            logger.error(f"Failed to fetch DXY: {e}")
        return None

    def get_economic_calendar(
        self,
        from_date: date = None,
        to_date: date = None
    ) -> List[Dict[str, Any]]:
        """
        경제 캘린더 조회

        Args:
            from_date: 시작일
            to_date: 종료일

        Returns:
            경제 이벤트 리스트
        """
        try:
            params = {}
            if from_date:
                params['from'] = from_date.strftime('%Y-%m-%d')
            if to_date:
                params['to'] = to_date.strftime('%Y-%m-%d')

            data = self._make_request("/stable/economic-calendar", params)

            # 미국 이벤트만 필터링 및 중요도별 정렬
            us_events = [
                event for event in (data or [])
                if event.get('country') == 'US'
            ]

            # 중요도 매핑
            importance_order = {'High': 0, 'Medium': 1, 'Low': 2}
            us_events.sort(
                key=lambda x: (
                    x.get('date', ''),
                    importance_order.get(x.get('impact', 'Low'), 2)
                )
            )

            return us_events

        except Exception as e:
            logger.error(f"Failed to fetch economic calendar: {e}")
            return []

    def get_treasury_rates(self) -> Dict[str, Any]:
        """
        미국 국채 금리 조회

        Returns:
            기간별 국채 금리
        """
        try:
            data = self._make_request("/stable/treasury")
            if data and len(data) > 0:
                latest = data[0]
                return {
                    'date': latest.get('date'),
                    'month1': latest.get('month1'),
                    'month3': latest.get('month3'),
                    'month6': latest.get('month6'),
                    'year1': latest.get('year1'),
                    'year2': latest.get('year2'),
                    'year5': latest.get('year5'),
                    'year10': latest.get('year10'),
                    'year30': latest.get('year30'),
                }
        except Exception as e:
            logger.error(f"Failed to fetch treasury rates: {e}")
        return {}

    def get_market_gainers_losers(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        시장 상승/하락 종목 조회

        Returns:
            상승/하락 종목 리스트
        """
        result = {'gainers': [], 'losers': []}

        try:
            gainers = self._make_request("/stable/biggest-gainers")
            result['gainers'] = gainers[:10] if isinstance(gainers, list) else []
        except Exception as e:
            logger.error(f"Failed to fetch gainers: {e}")

        try:
            losers = self._make_request("/stable/biggest-losers")
            result['losers'] = losers[:10] if isinstance(losers, list) else []
        except Exception as e:
            logger.error(f"Failed to fetch losers: {e}")

        return result

    def get_market_hours(self) -> Dict[str, Any]:
        """
        시장 운영 시간 및 상태 조회

        Returns:
            시장 상태 정보
        """
        try:
            data = self._make_request("/stable/is-the-market-open")
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Failed to fetch market hours: {e}")
            return {}
