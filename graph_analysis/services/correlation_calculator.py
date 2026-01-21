"""
Correlation Calculator Service

Calculates correlation matrices for stock price movements using NetworkX and pandas
"""
import logging
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

import pandas as pd
import networkx as nx

from django.db import transaction
from django.utils import timezone

from stocks.models import Stock, DailyPrice
from users.models import Watchlist
from graph_analysis.models import (
    CorrelationMatrix,
    CorrelationEdge,
    PriceCache,
    GraphMetadata,
)

logger = logging.getLogger(__name__)


class CorrelationCalculator:
    """
    Calculate correlation matrices for watchlist stocks

    Uses 3-month rolling window (90 days) for correlation calculation
    Stores results in PostgreSQL and creates NetworkX graph representation
    """

    DEFAULT_PERIOD_DAYS = 90  # 3 months
    MIN_DATA_POINTS = 20  # Minimum data points required for correlation

    def __init__(self, watchlist: Watchlist, period_days: int = DEFAULT_PERIOD_DAYS):
        """
        Initialize calculator

        Args:
            watchlist: User's watchlist to analyze
            period_days: Number of days for correlation window (default: 90)
        """
        self.watchlist = watchlist
        self.period_days = period_days
        self.calculation_date = date.today()

    def calculate_correlation_matrix(self) -> Optional[CorrelationMatrix]:
        """
        Calculate correlation matrix for the watchlist

        Returns:
            CorrelationMatrix model instance if successful, None otherwise
        """
        start_time = time.time()

        try:
            # Get stocks from watchlist
            stocks = self._get_watchlist_stocks()

            if len(stocks) < 2:
                logger.warning(f"Watchlist {self.watchlist.name} has less than 2 stocks")
                return None

            # Fetch price data
            price_data = self._fetch_price_data(stocks)

            if not price_data:
                logger.error(f"No price data available for watchlist {self.watchlist.name}")
                return None

            # Build price DataFrame
            price_df = self._build_price_dataframe(price_data)

            if price_df.empty or len(price_df) < self.MIN_DATA_POINTS:
                logger.error(
                    f"Insufficient data points ({len(price_df)}) for correlation calculation. "
                    f"Minimum required: {self.MIN_DATA_POINTS}"
                )
                return None

            # Calculate correlation matrix
            corr_matrix = self._calculate_correlations(price_df)

            if corr_matrix is None:
                return None

            # Save to database
            correlation_matrix = self._save_correlation_matrix(corr_matrix, len(stocks))

            # Save individual edges
            self._save_correlation_edges(corr_matrix, stocks)

            # Record metadata
            calculation_time_ms = int((time.time() - start_time) * 1000)
            self._record_metadata(
                stock_count=len(stocks),
                edge_count=len(stocks) * (len(stocks) - 1) // 2,
                calculation_time_ms=calculation_time_ms,
                status='completed'
            )

            logger.info(
                f"Correlation matrix calculated for {self.watchlist.name}: "
                f"{len(stocks)} stocks, {calculation_time_ms}ms"
            )

            return correlation_matrix

        except Exception as e:
            logger.error(f"Failed to calculate correlation matrix for {self.watchlist.name}: {e}")
            self._record_metadata(
                stock_count=0,
                edge_count=0,
                status='failed',
                error_message=str(e)
            )
            return None

    def _get_watchlist_stocks(self) -> List[Stock]:
        """Get all stocks in the watchlist"""
        return [
            item.stock
            for item in self.watchlist.items.select_related('stock').all()
        ]

    def _fetch_price_data(self, stocks: List[Stock]) -> Dict[str, List[Dict]]:
        """
        Fetch historical price data for stocks

        Args:
            stocks: List of Stock objects

        Returns:
            Dict mapping symbol to list of price records
        """
        end_date = self.calculation_date
        start_date = end_date - timedelta(days=self.period_days)

        price_data = {}

        for stock in stocks:
            # Try to get from cache first
            cached_prices = self._get_cached_prices(stock, end_date)

            if cached_prices:
                price_data[stock.symbol] = cached_prices
                continue

            # Fetch from database
            prices = DailyPrice.objects.filter(
                stock=stock,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date').values('date', 'close')

            price_list = list(prices)

            if price_list:
                price_data[stock.symbol] = price_list

                # Cache for future use
                self._cache_prices(stock, price_list, end_date)

        return price_data

    def _get_cached_prices(self, stock: Stock, target_date: date) -> Optional[List[Dict]]:
        """Get prices from cache if available and fresh"""
        try:
            cache = PriceCache.objects.filter(
                stock=stock,
                date=target_date
            ).first()

            if cache:
                return cache.prices

        except Exception as e:
            logger.debug(f"Cache miss for {stock.symbol}: {e}")

        return None

    def _cache_prices(self, stock: Stock, prices: List[Dict], target_date: date):
        """Save prices to cache"""
        try:
            # Convert date objects to strings for JSON serialization
            prices_json = [
                {'date': p['date'].isoformat() if isinstance(p['date'], date) else p['date'], 'close': float(p['close'])}
                for p in prices
            ]

            PriceCache.objects.update_or_create(
                stock=stock,
                date=target_date,
                defaults={
                    'prices': prices_json,
                    'period_days': self.period_days
                }
            )
        except Exception as e:
            logger.warning(f"Failed to cache prices for {stock.symbol}: {e}")

    def _build_price_dataframe(self, price_data: Dict[str, List[Dict]]) -> pd.DataFrame:
        """
        Build pandas DataFrame from price data

        Args:
            price_data: Dict mapping symbol to price records

        Returns:
            DataFrame with dates as index and symbols as columns
        """
        # Convert to DataFrame format
        dfs = []

        for symbol, prices in price_data.items():
            df = pd.DataFrame(prices)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.rename(columns={'close': symbol})
            dfs.append(df[[symbol]])

        if not dfs:
            return pd.DataFrame()

        # Merge all stock DataFrames
        result = pd.concat(dfs, axis=1)

        # Forward fill missing values (market holidays)
        result = result.fillna(method='ffill')

        # Drop rows with any remaining NaN
        result = result.dropna()

        return result

    def _calculate_correlations(self, price_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Calculate correlation matrix using Pearson correlation

        Args:
            price_df: DataFrame with stock prices

        Returns:
            Correlation matrix DataFrame
        """
        try:
            # Calculate daily returns
            returns = price_df.pct_change().dropna()

            if len(returns) < self.MIN_DATA_POINTS:
                logger.error(f"Insufficient return data points: {len(returns)}")
                return None

            # Calculate correlation matrix
            corr_matrix = returns.corr(method='pearson')

            return corr_matrix

        except Exception as e:
            logger.error(f"Failed to calculate correlations: {e}")
            return None

    @transaction.atomic
    def _save_correlation_matrix(
        self,
        corr_matrix: pd.DataFrame,
        stock_count: int
    ) -> CorrelationMatrix:
        """Save correlation matrix to database"""

        # Convert to nested dict for JSON storage
        matrix_data = {}
        for i, row_symbol in enumerate(corr_matrix.index):
            matrix_data[row_symbol] = {}
            for j, col_symbol in enumerate(corr_matrix.columns):
                value = corr_matrix.iloc[i, j]
                # Handle NaN values
                if pd.isna(value):
                    matrix_data[row_symbol][col_symbol] = None
                else:
                    matrix_data[row_symbol][col_symbol] = round(float(value), 4)

        # Create or update matrix
        correlation_matrix, created = CorrelationMatrix.objects.update_or_create(
            watchlist=self.watchlist,
            date=self.calculation_date,
            defaults={
                'matrix_data': matrix_data,
                'stock_count': stock_count,
                'calculation_period': self.period_days,
            }
        )

        logger.info(
            f"{'Created' if created else 'Updated'} correlation matrix for "
            f"{self.watchlist.name} on {self.calculation_date}"
        )

        return correlation_matrix

    @transaction.atomic
    def _save_correlation_edges(
        self,
        corr_matrix: pd.DataFrame,
        stocks: List[Stock]
    ):
        """Save individual correlation edges to database"""

        # Create stock lookup
        stock_lookup = {stock.symbol: stock for stock in stocks}

        # Get previous day's edges for change detection
        previous_date = self.calculation_date - timedelta(days=1)
        previous_edges = {
            (edge.stock_a.symbol, edge.stock_b.symbol): edge.correlation
            for edge in CorrelationEdge.objects.filter(
                watchlist=self.watchlist,
                date=previous_date
            ).select_related('stock_a', 'stock_b')
        }

        edges_to_create = []

        # Iterate through correlation matrix (upper triangle only)
        for i, symbol_a in enumerate(corr_matrix.index):
            for j, symbol_b in enumerate(corr_matrix.columns):
                if i >= j:  # Skip diagonal and lower triangle
                    continue

                stock_a = stock_lookup.get(symbol_a)
                stock_b = stock_lookup.get(symbol_b)

                if not stock_a or not stock_b:
                    continue

                correlation = corr_matrix.iloc[i, j]

                if pd.isna(correlation):
                    continue

                # Get previous correlation
                prev_corr = previous_edges.get((symbol_a, symbol_b))
                correlation_change = 0

                if prev_corr is not None:
                    correlation_change = float(correlation) - float(prev_corr)

                # Check for anomaly (±0.2 change threshold)
                is_anomaly = abs(correlation_change) >= 0.2

                edge = CorrelationEdge(
                    watchlist=self.watchlist,
                    stock_a=stock_a,
                    stock_b=stock_b,
                    date=self.calculation_date,
                    correlation=Decimal(str(round(float(correlation), 4))),
                    previous_correlation=Decimal(str(round(float(prev_corr), 4))) if prev_corr else None,
                    correlation_change=Decimal(str(round(correlation_change, 4))),
                    is_anomaly=is_anomaly,
                )

                edges_to_create.append(edge)

        # Bulk create edges
        if edges_to_create:
            CorrelationEdge.objects.bulk_create(
                edges_to_create,
                ignore_conflicts=True
            )

            logger.info(f"Created {len(edges_to_create)} correlation edges")

    def _record_metadata(
        self,
        stock_count: int,
        edge_count: int,
        status: str,
        calculation_time_ms: int = 0,
        error_message: str = ''
    ):
        """Record metadata about the calculation"""
        GraphMetadata.objects.update_or_create(
            watchlist=self.watchlist,
            date=self.calculation_date,
            defaults={
                'stock_count': stock_count,
                'edge_count': edge_count,
                'anomaly_count': 0,  # Will be updated by anomaly detector
                'calculation_time_ms': calculation_time_ms,
                'status': status,
                'error_message': error_message,
            }
        )

    def build_network_graph(self) -> Optional[nx.Graph]:
        """
        Build NetworkX graph from correlation matrix

        Returns:
            NetworkX Graph object
        """
        try:
            # Get latest correlation matrix
            matrix = CorrelationMatrix.objects.filter(
                watchlist=self.watchlist,
                date=self.calculation_date
            ).first()

            if not matrix:
                logger.warning(f"No correlation matrix found for {self.watchlist.name}")
                return None

            # Create graph
            G = nx.Graph()

            # Add nodes (stocks)
            for symbol in matrix.matrix_data.keys():
                G.add_node(symbol)

            # Add edges (correlations)
            for symbol_a, correlations in matrix.matrix_data.items():
                for symbol_b, correlation in correlations.items():
                    if symbol_a >= symbol_b:  # Skip diagonal and duplicates
                        continue

                    if correlation is not None and abs(correlation) >= 0.2:  # Only add meaningful correlations
                        G.add_edge(
                            symbol_a,
                            symbol_b,
                            weight=abs(correlation),
                            correlation=correlation
                        )

            logger.info(
                f"Built NetworkX graph: {G.number_of_nodes()} nodes, "
                f"{G.number_of_edges()} edges"
            )

            return G

        except Exception as e:
            logger.error(f"Failed to build network graph: {e}")
            return None
