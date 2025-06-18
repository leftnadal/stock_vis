"""
Service for saving Alpha Vantage data to the database.

처리해야 할일
1. balancesheet, incomestatement, cashflow 세부내용 업데이트
"""
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from stocks.models import Stock, HistoricalPrice, BalanceSheet, IncomeStatement, CashFlowStatement
from .client import AlphaVantageClient
from .processor import AlphaVantageProcessor

logger = logging.getLogger(__name__)

class AlphaVantageService:
    """
    Service for fetching and storing Alpha Vantage stock data.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Alpha Vantage service.
        
        Args:
            api_key (str): Alpha Vantage API key
        """
        self.client = AlphaVantageClient(api_key)
        self.processor = AlphaVantageProcessor()
    
    def update_stock_data(self, symbol: str, force_update: bool = False) -> Stock:
        """
        Update or create stock data for a specific symbol.
        
        Args:
            symbol (str): Stock symbol
            force_update (bool): Force update even if recent data exists
            
        Returns:
            Stock: Updated or created stock instance
        """
        # Standardize symbol format
        symbol = symbol.upper().strip()
        
        # Fetch company overview for detailed information
        logger.info(f"Fetching company overview for {symbol}")
        overview_data = self.client.get_company_overview(symbol)
        stock_data = self.processor.process_company_overview(overview_data)
        
        # If we couldn't get company data, check if we already have this stock
        if not stock_data:
            try:
                stock = Stock.objects.get(symbol=symbol)
                logger.warning(f"Could not fetch overview for {symbol}, using existing data")
            except Stock.DoesNotExist:
                logger.error(f"Could not fetch overview for {symbol} and stock does not exist")
                raise ValueError(f"Could not fetch stock data for {symbol}")
        else:
            # Get real-time quote data to update price
            try:
                quote_data = self.client.get_stock_quote(symbol)
                price_data = self.processor.process_stock_quote(symbol, quote_data)
                
                # Merge price data with stock data
                if price_data:
                    stock_data.update({k: v for k, v in price_data.items() if k != 'symbol'})
            except Exception as e:
                logger.error(f"Error fetching quote data for {symbol}: {e}")
                # Continue with other available data
            
            # Try to get existing stock or create new one
            try:
                with transaction.atomic():
                    stock, created = Stock.objects.update_or_create(
                        symbol=symbol,
                        defaults=stock_data
                    )
                    
                    if created:
                        logger.info(f"Created new stock: {symbol}")
                    else:
                        logger.info(f"Updated existing stock: {symbol}")
            except Exception as e:
                logger.error(f"Error saving stock data for {symbol}: {e}")
                raise
                
        return stock
    
    def update_historical_prices(self, stock: Union[Stock, str], days: int = 100) -> int:
        """
        Update historical price data for a stock.
        
        Args:
            stock (Union[Stock, str]): Stock instance or symbol
            days (int): Number of days of data to fetch (100 or 'full' for 20+ years)
            
        Returns:
            int: Number of price records updated or created
        """
        # Get stock object if symbol provided
        if isinstance(stock, str):
            try:
                stock = Stock.objects.get(symbol=stock.upper().strip())
            except Stock.DoesNotExist:
                logger.error(f"Stock {stock} does not exist")
                raise ValueError(f"Stock {stock} does not exist")
        
        symbol = stock.symbol
        outputsize = "compact" if days <= 100 else "full"
        
        # Fetch historical price data
        logger.info(f"Fetching historical prices for {symbol}")
        try:
            price_data = self.client.get_daily_stock_data(symbol, outputsize)
            price_records = self.processor.process_historical_prices(symbol, price_data)
            
            if not price_records:
                logger.warning(f"No historical price data found for {symbol}")
                return 0
            
            # Save price records to database
            count = 0
            with transaction.atomic():
                for record in price_records:
                    # Check if we already have this date's data
                    try:
                        # Try to update existing record
                        price_obj, created = HistoricalPrice.objects.update_or_create(
                            stock=stock,
                            date=record['date'],
                            defaults={
                                'open_price': record['open_price'],
                                'high_price': record['high_price'],
                                'low_price': record['low_price'],
                                'close_price': record['close_price'],
                                'volume': record['volume'],
                                'currency': record['currency']
                            }
                        )
                        count += 1
                    except Exception as e:
                        logger.error(f"Error saving price data for {symbol} on {record['date']}: {e}")
                        continue
            
            logger.info(f"Updated {count} historical price records for {symbol}")
            return count
            
        except Exception as e:
            logger.error(f"Error fetching historical price data for {symbol}: {e}")
            raise
    
    def update_financial_statements(self, stock: Union[Stock, str]) -> Dict[str, int]:
        """
        Update financial statement data for a stock (balance sheet, income statement, cash flow).
        
        Args:
            stock (Union[Stock, str]): Stock instance or symbol
            
        Returns:
            Dict[str, int]: Number of records updated for each statement type
        """
        # Get stock object if symbol provided
        if isinstance(stock, str):
            try:
                stock = Stock.objects.get(symbol=stock.upper().strip())
            except Stock.DoesNotExist:
                logger.error(f"Stock {stock} does not exist")
                raise ValueError(f"Stock {stock} does not exist")
        
        symbol = stock.symbol
        results = {
            'balance_sheet': 0,
            'income_statement': 0,
            'cash_flow': 0
        }
        
        # Update balance sheet data
        try:
            logger.info(f"Fetching balance sheet data for {symbol}")
            balance_sheet_data = self.client.get_balance_sheet(symbol)
            balance_sheets = self.processor.process_balance_sheet(balance_sheet_data)
            
            count = 0
            with transaction.atomic():
                for data in balance_sheets:
                    try:
                        # Find existing statement or create new one
                        statement, created = BalanceSheet.objects.update_or_create(
                            stock=stock,
                            reported_date=data['reported_date'],
                            period_type=data['period_type'],
                            defaults={
                                'fidcal_date_ending': data['reported_date'],
                                'fiscal_year': data['fiscal_year'],
                                'fiscal_quarter': data.get('fiscal_quarter'),
                                'currency': data['currency'],
                                'total_Assets': data['total_Assets'],
                                'total_Current_Assets': data['total_Current_Assets'],
                                'cash_And_Cash_Equivalents_At_Carrying_Value': data['cash_And_Cash_Equivalents_At_Carrying_Value'],
                                'cash_And_Short_Term_Investments': data['cash_And_Short_Term_Investments'],
                                'inventory': data['inventory'],
                                'current_Net_Receivables': data['current_Net_Receivables'],
                                'total_Non_Current_Assets': data['total_Non_Current_Assets'],
                                'property_Plant_Equipment': data['property_Plant_Equipment'],
                                'accumulated_Depreciation_Amortization_Ppe': data['accumulated_Depreciation_Amortization_Ppe'],
                                'intangible_Assets': data['intangible_Assets'],
                                'intangible_Assets_Excluding_Goodwill': data['intangible_Assets_Excluding_Goodwill'],
                                'goodwill': data['goodwill'],
                                'investments': data['investments'],
                                'long_Term_Investments': data['long_Term_Investments'],
                                'short_Term_Investments': data['short_Term_Investments'],
                                'other_Current_Assets': data['other_Current_Assets'],
                                'other_Non_Current_Assets': data['other_Non_Current_Assets'],
                                'total_Liabilities': data['total_Liabilities'],
                                'total_Current_Liabilities': data['total_Current_Liabilities'],
                                'current_Accounts_Payable': data['current_Accounts_Payable'],
                                'deferred_Revenue': data['deferred_Revenue'],
                                'current_Debt': data['current_Debt'],
                                'short_Term_Debt': data['short_Term_Debt'],
                                'total_Non_Current_Liabilities': data['total_Non_Current_Liabilities'],
                                'capital_Lease_Obligations': data['capital_Lease_Obligations'],
                                'long_Term_Debt': data['long_Term_Debt'],
                                'current_Longterm_Debt': data['current_Longterm_Debt'],
                                'longterm_Debt_Noncurrent': data['longterm_Debt_Noncurrent'],
                                'short_LongTerm_Debt_Total': data['short_LongTerm_Debt_Total'],
                                'other_Current_Liabilities': data['other_Current_Liabilities'],
                                'other_Non_Current_Liabilities': data['other_Non_Current_Liabilities'],
                                'total_Shareholder_Equity': data['total_Shareholder_Equity'],
                                'treasury_Stock': data['treasury_Stock'],
                                'retained_Earnings': data['retained_Earnings'],
                                'common_Stock': data['common_Stock'],
                                'common_Stock_Shares_Outstanding': data['common_Stock_Shares_Outstanding']
                            }
                        )
                        count += 1
                    except Exception as e:
                        logger.error(f"Error saving balance sheet for {symbol} on {data['reported_date']}: {e}")
                        continue
            
            results['balance_sheet'] = count
            logger.info(f"Updated {count} balance sheet records for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching balance sheet data for {symbol}: {e}")
        
        # Update income statement data
        try:
            logger.info(f"Fetching income statement data for {symbol}")
            income_statement_data = self.client.get_income_statement(symbol)
            income_statements = self.processor.process_income_statement(income_statement_data)
            
            count = 0
            with transaction.atomic():
                for data in income_statements:
                    try:
                        # Find existing statement or create new one
                        statement, created = IncomeStatement.objects.update_or_create(
                            stock=stock,
                            reported_date=data['reported_date'],
                            period_type=data['period_type'],
                            defaults={
                                'fidcal_date_ending': data['reported_date'],
                                'fiscal_year': data['fiscal_year'],
                                'fiscal_quarter': data.get('fiscal_quarter'),
                                'currency': data['currency'],
                                'total_revenue': data['total_revenue'],
                                'cost_of_revenue': data['cost_of_revenue'],
                                'gross_profit': data['gross_profit'],
                                'operating_expenses': data['operating_expenses'],
                                'selling_General_And_Administrative': data['selling_General_And_Administrative'],
                                'research_and_development': data['research_and_development'],
                                'operating_income': data['operating_income'],
                                'net_income': data['net_income'],
                                'ebitda': data['ebitda']
                            }
                        )
                        count += 1
                    except Exception as e:
                        logger.error(f"Error saving income statement for {symbol} on {data['reported_date']}: {e}")
                        continue
            
            results['income_statement'] = count
            logger.info(f"Updated {count} income statement records for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching income statement data for {symbol}: {e}")
        
        # Update cash flow data
        try:
            logger.info(f"Fetching cash flow data for {symbol}")
            cash_flow_data = self.client.get_cash_flow(symbol)
            cash_flows = self.processor.process_cash_flow(cash_flow_data)
            
            count = 0
            with transaction.atomic():
                for data in cash_flows:
                    try:
                        # Find existing statement or create new one
                        statement, created = CashFlowStatement.objects.update_or_create(
                            stock=stock,
                            reported_date=data['reported_date'],
                            period_type=data['period_type'],
                            defaults={
                                'fidcal_date_ending': data['reported_date'],
                                'fiscal_year': data['fiscal_year'],
                                'fiscal_quarter': data.get('fiscal_quarter'),
                                'currency': data['currency'],
                                'operating_cashflow': data['operating_cashflow'],
                                'capital_expenditures': data['capital_expenditures'],
                                'cashflow_from_investment': data['cashflow_from_investment'],
                                'cashflow_from_financing': data['cashflow_from_financing'],
                                'net_income': data['net_income'],
                                'change_in_cash_and_cash_equivalents': data['change_in_cash_and_cash_equivalents'],
                                'dividend_payout': data['dividend_payout']
                            }
                        )
                        count += 1
                    except Exception as e:
                        logger.error(f"Error saving cash flow for {symbol} on {data['reported_date']}: {e}")
                        continue
            
            results['cash_flow'] = count
            logger.info(f"Updated {count} cash flow records for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching cash flow data for {symbol}: {e}")
        
        return results
    
    def update_all_stock_data(self, symbol: str) -> Dict[str, Any]:
        """
        Update all data for a specific stock (overview, prices, financials).
        
        Args:
            symbol (str): Stock symbol
            
        Returns:
            Dict[str, Any]: Summary of updates
        """
        symbol = symbol.upper().strip()
        results = {
            'stock': False,
            'prices': 0,
            'financials': {
                'balance_sheet': 0,
                'income_statement': 0,
                'cash_flow': 0
            }
        }
        
        try:
            # Update basic stock data
            stock = self.update_stock_data(symbol)
            results['stock'] = True
            
            # Update historical prices
            prices_count = self.update_historical_prices(stock)
            results['prices'] = prices_count
            
            # Update financial statements
            financials = self.update_financial_statements(stock)
            results['financials'] = financials
            
            logger.info(f"Completed full data update for {symbol}")
            return results
        except Exception as e:
            logger.error(f"Error updating data for {symbol}: {e}")
            raise