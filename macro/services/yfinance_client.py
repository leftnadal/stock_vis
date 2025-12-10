"""
Yahoo Finance API Client (yfinance wrapper)

FMP API 대체용 - 무료로 시장 지수, 섹터 ETF, 환율, 원자재 데이터 제공
"""
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class YFinanceClient:
    """Yahoo Finance 클라이언트 (yfinance 라이브러리 사용)"""

    # 주요 지수 심볼
    INDEX_SYMBOLS = {
        '^GSPC': 'S&P 500',
        '^DJI': 'Dow Jones Industrial Average',
        '^IXIC': 'NASDAQ Composite',
        '^RUT': 'Russell 2000',
        '^VIX': 'CBOE Volatility Index',
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

    # 원자재 ETF/선물
    COMMODITIES = {
        'GC=F': 'Gold',
        'SI=F': 'Silver',
        'CL=F': 'Crude Oil (WTI)',
        'NG=F': 'Natural Gas',
    }

    # 환율
    FOREX = {
        'EURUSD=X': 'EUR/USD',
        'JPY=X': 'USD/JPY',
        'GBPUSD=X': 'GBP/USD',
        'CNY=X': 'USD/CNY',
        'KRW=X': 'USD/KRW',
    }

    def __init__(self):
        """초기화"""
        try:
            import yfinance as yf
            self.yf = yf
            self._available = True
        except ImportError:
            logger.warning("yfinance not installed. Install with: pip install yfinance")
            self._available = False
            self.yf = None

    def _get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        단일 심볼 시세 조회

        Args:
            symbol: 심볼 (예: '^GSPC')

        Returns:
            시세 데이터
        """
        if not self._available:
            return None

        try:
            ticker = self.yf.Ticker(symbol)
            info = ticker.fast_info

            return {
                'symbol': symbol,
                'price': getattr(info, 'last_price', None),
                'previous_close': getattr(info, 'previous_close', None),
                'change': (getattr(info, 'last_price', 0) or 0) - (getattr(info, 'previous_close', 0) or 0),
                'change_percent': self._calc_change_percent(
                    getattr(info, 'last_price', 0),
                    getattr(info, 'previous_close', 0)
                ),
                'day_high': getattr(info, 'day_high', None),
                'day_low': getattr(info, 'day_low', None),
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            return None

    def _calc_change_percent(self, current: float, previous: float) -> Optional[float]:
        """변화율 계산"""
        if not current or not previous:
            return None
        try:
            return round(((current - previous) / previous) * 100, 2)
        except (ZeroDivisionError, TypeError):
            return None

    def get_batch_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        복수 심볼 시세 조회 (더 빠름)

        Args:
            symbols: 심볼 리스트

        Returns:
            심볼별 시세 딕셔너리
        """
        if not self._available:
            return {}

        results = {}
        try:
            # yfinance의 download로 배치 조회
            tickers = self.yf.Tickers(' '.join(symbols))

            for symbol in symbols:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker:
                        info = ticker.fast_info
                        results[symbol] = {
                            'symbol': symbol,
                            'price': getattr(info, 'last_price', None),
                            'previous_close': getattr(info, 'previous_close', None),
                            'change': (getattr(info, 'last_price', 0) or 0) - (getattr(info, 'previous_close', 0) or 0),
                            'change_percent': self._calc_change_percent(
                                getattr(info, 'last_price', 0),
                                getattr(info, 'previous_close', 0)
                            ),
                            'day_high': getattr(info, 'day_high', None),
                            'day_low': getattr(info, 'day_low', None),
                            'timestamp': datetime.now().isoformat(),
                        }
                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed batch quote fetch: {e}")

        return results

    def get_market_indices(self) -> Dict[str, Any]:
        """
        주요 시장 지수 조회

        Returns:
            지수별 시세 데이터
        """
        indices = {}
        quotes = self.get_batch_quotes(list(self.INDEX_SYMBOLS.keys()))

        for symbol, quote in quotes.items():
            if quote and quote.get('price'):
                indices[symbol] = {
                    'name': self.INDEX_SYMBOLS.get(symbol, symbol),
                    'price': quote.get('price'),
                    'change': quote.get('change'),
                    'change_percent': quote.get('change_percent'),
                    'previous_close': quote.get('previous_close'),
                    'day_high': quote.get('day_high'),
                    'day_low': quote.get('day_low'),
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
        quotes = self.get_batch_quotes(list(self.SECTOR_ETFS.keys()))

        for symbol, quote in quotes.items():
            if quote and quote.get('price'):
                sectors[symbol] = {
                    'name': self.SECTOR_ETFS.get(symbol, symbol),
                    'price': quote.get('price'),
                    'change_percent': quote.get('change_percent'),
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

    def get_commodities(self) -> Dict[str, Any]:
        """
        원자재 시세 조회

        Returns:
            원자재별 시세 데이터
        """
        commodities = {}
        quotes = self.get_batch_quotes(list(self.COMMODITIES.keys()))

        for symbol, quote in quotes.items():
            if quote and quote.get('price'):
                commodities[symbol] = {
                    'name': self.COMMODITIES.get(symbol, symbol),
                    'price': quote.get('price'),
                    'change': quote.get('change'),
                    'change_percent': quote.get('change_percent'),
                }

        return commodities

    def get_forex_rates(self) -> Dict[str, Any]:
        """
        주요 환율 조회

        Returns:
            환율 데이터
        """
        forex = {}
        quotes = self.get_batch_quotes(list(self.FOREX.keys()))

        for symbol, quote in quotes.items():
            if quote and quote.get('price'):
                forex[symbol] = {
                    'name': self.FOREX.get(symbol, symbol),
                    'price': quote.get('price'),
                    'change': quote.get('change'),
                    'change_percent': quote.get('change_percent'),
                }

        return forex

    def get_dollar_index(self) -> Optional[Dict[str, Any]]:
        """
        달러 인덱스 (DXY) 조회

        Returns:
            DXY 데이터
        """
        quote = self._get_quote('DX-Y.NYB')
        if quote and quote.get('price'):
            return {
                'value': quote.get('price'),
                'change': quote.get('change'),
                'change_percent': quote.get('change_percent'),
                'timestamp': quote.get('timestamp'),
            }
        return None

    def is_available(self) -> bool:
        """yfinance 사용 가능 여부"""
        return self._available
