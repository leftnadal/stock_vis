"""
alphavantage의 data를 받아서 database로 저장하는 service
"""

import logging
from typing import Dict, Any, List, Union
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction

from alphavantage_client import AlphaVantageClient
from alphavantage_processor import AlphaVantageProcessor
from stocks.models import Stock, HistoricalPrice, BalanceSheet, IncomeStatement, CashFlowStatement

logger = logging.getLogger(__name__)

class AlphaVantageService:
    """
    alphavantage의 정보를 fetching해서 저장하는 service
    """

    def __init__(self, api_key:str):
        """
        Initialize Alpha Vantage Service
        Args:
            api_key (str): Alpha Vantage API key
        """
        self.client = AlphaVantageClient(api_key)
        self.processor = AlphaVantageProcessor()

    def update_stock_data(self, symbol:str) -> Stock:
        """
        Update or create stock data for a specific symbol.
        
        Args:
            symbol (str): Stock symbol

        Returns:
            Stock: Updated or created stock instance
        """
        # Standardize symbol format
        symbol = symbol.upper().strip()

        # Fetch company overview 
        logger.info(f"Fetching company overview for {symbol}")
        overview_data = self.client.get_company_overview(symbol)
        processor_overview_data = self.processor.process_company_overview(overview_data)
    
        # company data 받을수 없을 때, 이미 이 데이터가 있는지 확인.
        if not processor_overview_data:
            try:
                # 이미 있는 데이터를 받음.
                stock = Stock.objects.get(symbol=symbol)
                logger.warning(f"Could not fetch overview for {symbol}, using existing data")
            except Stock.DoesNotExist:
                logger.error(f"Could not fetch overview for {symbol} and stock does not exist")
                raise ValueError(f"Could not fetch stock data for {symbol}")
        else:
            # Get real-time quote data to update price
            try:
                quote_data = self.client.get_stock_quote(symbol)
                processor_quote_data = self.processor.process_stock_quote(symbol, quote_data)

                # Merge price data with stock data
                if processor_quote_data:
                    processor_overview_data.update({k: v for k, v in processor_quote_data.items() if k != 'symbol'})
            except Exception as e:
                logger.error({f"Error fetching quote data for {symbol}"})

            # Try to get existing stock or create new one
            try:
                with transaction.atomic():
                    stock, created = Stock.objects.update_or_create(symbol=symbol, defaults=processor_overview_data)

                    if created:
                        logger.info(f"Created new stock: {symbol}")

                    else:
                        logger.info(f"Updated existing stock: {symbol}")

            except Exception as e:
                logger.error(f"Error saving stock data for {symbol}: {e}")
                raise
        return stock
    
    def update_historical_prices(self, stock:Union[Stock, str], days: int = 100) -> Dict[str, int]:
        """
        Update historical price data for daily, weekly, and monthly timeframes.
        
        Args:
            stock: Stock object or symbol string
            days: Number of days of historical data to fetch
            
        Returns:
            Dict containing count of updated records for each timeframe
        """
        # Normalize stock input
        if isinstance(stock, str):
            symbol = stock.upper().strip()
            try:
                stock_obj = Stock.objects.get(symbol=symbol)
            except Stock.DoesNotExist:
                logger.error(f"Stock {symbol} not found")
                raise ValueError(f"Stock {symbol} not found")
        else:
            stock_obj = stock
            symbol = stock_obj.symbol
    
        logger.info(f"Updating historical prices for {symbol} ({days} days)")
        
        #Initialize counters
        results = {
            'daily' : 0,
            'weekly' : 0,
        }

        
        
