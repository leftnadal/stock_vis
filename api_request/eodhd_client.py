"""
EODHD Historical Data API Client

EODHD (EOD Historical Data) provides:
- Bulk EOD price data for 150,000+ stocks globally
- US coverage: 5,000+ stocks (NYSE, NASDAQ, AMEX)
- Format: CSV (GZIP compressed) or JSON
- Update: Daily at market close
- Cost: $19.99/month Basic Plan (unlimited requests, no rate limits)

Main use case for Stock-Vis:
- Daily bulk download of US stock prices for correlation analysis
- Graph ontology data collection (5,000 stocks daily)
"""
import requests
import logging
import csv
import gzip
import io
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from config.settings import os

logger = logging.getLogger(__name__)


class EODHDClient:
    """
    EODHD Historical Data API Client

    Main use case: Bulk EOD price data for graph correlation analysis
    """
    BASE_URL = "https://eodhistoricaldata.com/api"

    # US 거래소 코드
    US_EXCHANGES = ['US', 'NASDAQ', 'NYSE', 'AMEX']

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize EODHD client

        Args:
            api_key: EODHD API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv('EODHD_API_KEY')

        if not self.api_key:
            raise ValueError("EODHD API Key not found. Set EODHD_API_KEY environment variable.")

        logger.info("EODHD client initialized")

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        fmt: str = 'json'
    ) -> Any:
        """
        Make HTTP request to EODHD API

        Args:
            endpoint: API endpoint path (e.g., '/eod/AAPL.US')
            params: Query parameters
            fmt: Response format ('json' or 'csv')

        Returns:
            API response (dict for JSON, text for CSV)
        """
        if params is None:
            params = {}

        # Add API key and format
        params['api_token'] = self.api_key
        params['fmt'] = fmt

        url = f"{self.BASE_URL}{endpoint}"

        try:
            logger.info(f"Making EODHD request: {endpoint}")
            response = requests.get(url, params=params, timeout=60)

            # Check HTTP status
            if response.status_code != 200:
                logger.error(f"EODHD error {response.status_code}: {response.text}")
                response.raise_for_status()

            # Return parsed response
            if fmt == 'json':
                data = response.json()

                # Check for API error in response
                if isinstance(data, dict) and data.get('error'):
                    error_msg = data.get('error', 'Unknown error')
                    logger.error(f"EODHD API error: {error_msg}")
                    raise ValueError(f"EODHD API error: {error_msg}")

                return data
            else:
                # Return CSV text
                return response.text

        except requests.exceptions.Timeout:
            logger.error(f"EODHD request timeout: {endpoint}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"EODHD request failed: {e}")
            raise

    def get_eod_data(
        self,
        symbol: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        period: str = 'd'
    ) -> List[Dict[str, Any]]:
        """
        Get End-of-Day price data for a single symbol

        Args:
            symbol: Stock symbol with exchange (e.g., 'AAPL.US')
            from_date: Start date (default: 3 months ago)
            to_date: End date (default: today)
            period: 'd' (daily), 'w' (weekly), 'm' (monthly)

        Returns:
            List of price records
        """
        if not symbol.endswith(('.US', '.NASDAQ', '.NYSE', '.AMEX')):
            symbol = f"{symbol}.US"

        params = {'period': period}

        if from_date:
            params['from'] = from_date.strftime('%Y-%m-%d')

        if to_date:
            params['to'] = to_date.strftime('%Y-%m-%d')

        endpoint = f"/eod/{symbol}"

        try:
            data = self._make_request(endpoint, params, fmt='json')

            if not isinstance(data, list):
                logger.warning(f"Unexpected response format for {symbol}")
                return []

            return data

        except Exception as e:
            logger.error(f"Failed to fetch EOD data for {symbol}: {e}")
            return []

    def get_bulk_eod_data(
        self,
        exchange: str = 'US',
        date: Optional[date] = None,
        symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get bulk EOD data for entire exchange (primary method for graph analysis)

        This is the main method for Stock-Vis graph ontology:
        - Downloads 5,000+ US stocks in one request
        - CSV format (GZIP compressed) for efficiency
        - Typically completes in 30-60 seconds

        Args:
            exchange: Exchange code ('US', 'NASDAQ', 'NYSE', 'AMEX')
            date: Target date (default: latest market day)
            symbols: Optional filter for specific symbols

        Returns:
            List of price records: [
                {
                    'symbol': 'AAPL',
                    'date': '2026-01-09',
                    'open': 150.25,
                    'high': 152.50,
                    'low': 149.80,
                    'close': 151.75,
                    'adjusted_close': 151.75,
                    'volume': 50000000
                },
                ...
            ]
        """
        if exchange not in self.US_EXCHANGES:
            logger.warning(f"Unknown exchange: {exchange}. Using 'US' instead.")
            exchange = 'US'

        params = {}

        if date:
            params['date'] = date.strftime('%Y-%m-%d')

        if symbols:
            # Filter specific symbols (comma-separated)
            params['symbols'] = ','.join(symbols)

        endpoint = f"/eod-bulk-last-day/{exchange}"

        try:
            # Get CSV data
            csv_text = self._make_request(endpoint, params, fmt='csv')

            # Parse CSV
            results = []
            csv_reader = csv.DictReader(io.StringIO(csv_text))

            for row in csv_reader:
                try:
                    results.append({
                        'symbol': row['Code'],
                        'date': row['Date'],
                        'open': float(row['Open']) if row['Open'] else None,
                        'high': float(row['High']) if row['High'] else None,
                        'low': float(row['Low']) if row['Low'] else None,
                        'close': float(row['Close']) if row['Close'] else None,
                        'adjusted_close': float(row['Adjusted_close']) if row['Adjusted_close'] else None,
                        'volume': int(float(row['Volume'])) if row['Volume'] else 0,
                    })
                except (ValueError, KeyError) as e:
                    # Skip malformed rows
                    logger.debug(f"Skipping row for {row.get('Code', 'unknown')}: {e}")
                    continue

            logger.info(f"Fetched bulk EOD data: {len(results)} stocks from {exchange}")
            return results

        except Exception as e:
            logger.error(f"Failed to fetch bulk EOD data for {exchange}: {e}")
            return []

    def get_fundamentals(
        self,
        symbol: str,
        filter_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get fundamental data for a symbol

        Args:
            symbol: Stock symbol with exchange (e.g., 'AAPL.US')
            filter_keys: Optional list of specific data keys to retrieve
                        (e.g., ['General', 'Highlights', 'Valuation'])

        Returns:
            Fundamental data dictionary
        """
        if not symbol.endswith(('.US', '.NASDAQ', '.NYSE', '.AMEX')):
            symbol = f"{symbol}.US"

        params = {}

        if filter_keys:
            params['filter'] = '::'.join(filter_keys)

        endpoint = f"/fundamentals/{symbol}"

        try:
            data = self._make_request(endpoint, params, fmt='json')
            return data

        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
            return {}

    def search_symbols(
        self,
        query: str,
        exchange: str = 'US',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for stock symbols

        Args:
            query: Search query (company name or symbol)
            exchange: Exchange code
            limit: Max results

        Returns:
            List of matching symbols
        """
        endpoint = "/search/{query}"

        try:
            # Note: EODHD search is limited, consider using Alpha Vantage for search
            logger.warning("EODHD search is limited. Consider Alpha Vantage SYMBOL_SEARCH.")
            return []

        except Exception as e:
            logger.error(f"Failed to search symbols: {e}")
            return []

    def get_exchange_symbols(self, exchange: str = 'US') -> List[Dict[str, Any]]:
        """
        Get all available symbols for an exchange

        Args:
            exchange: Exchange code ('US', 'NASDAQ', 'NYSE', 'AMEX')

        Returns:
            List of symbol info: [
                {
                    'Code': 'AAPL',
                    'Name': 'Apple Inc.',
                    'Country': 'USA',
                    'Exchange': 'NASDAQ',
                    'Currency': 'USD',
                    'Type': 'Common Stock'
                },
                ...
            ]
        """
        endpoint = f"/exchange-symbol-list/{exchange}"
        params = {'fmt': 'json'}

        try:
            data = self._make_request(endpoint, params, fmt='json')

            if isinstance(data, list):
                logger.info(f"Fetched {len(data)} symbols for {exchange}")
                return data
            else:
                logger.warning(f"Unexpected response format for exchange symbols")
                return []

        except Exception as e:
            logger.error(f"Failed to fetch exchange symbols for {exchange}: {e}")
            return []

    def is_market_open(self) -> bool:
        """
        Check if US market is currently open

        Returns:
            True if market is open
        """
        # Simple heuristic: US market hours 9:30 AM - 4:00 PM ET
        # TODO: Use EODHD market status API for accurate data
        now = datetime.now()

        # Check if weekday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Check market hours (simplified, does not account for holidays)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now <= market_close
