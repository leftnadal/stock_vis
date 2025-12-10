"""
alphavantage의 data를 받아서 database로 저장하는 service
"""

import logging
from typing import Dict, Any, List, Union
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.db.utils import IntegrityError

from alphavantage_client import AlphaVantageClient
from alphavantage_processor import AlphaVantageProcessor
from stocks.models import Stock, BalanceSheet, IncomeStatement, CashFlowStatement, DailyPrice, WeeklyPrice

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

        try:
            # Fetch company overview 
            logger.info(f"Fetching company overview for {symbol}")
            overview_data = self.client.get_company_overview(symbol)
            processed_overview_data = self.processor.process_company_overview(overview_data)
        
            # company data 받을수 없을 때, 이미 이 데이터가 있는지 확인.
            if not processed_overview_data:
                try:
                    # 이미 있는 데이터를 받음.
                    stock = Stock.objects.get(symbol=symbol)
                    logger.warning(f"Could not fetch overview for {symbol}, using existing data")
                    return stock
                except Stock.DoesNotExist:
                    logger.error(f"Could not fetch overview for {symbol} and stock does not exist")
                    raise ValueError(f"Could not fetch stock data for {symbol}")
            
            # Get real-time quote data to update price
            try:
                logger.info(f"Fetching real-time quote for {symbol}")
                quote_data = self.client.get_stock_quote(symbol)
                processed_quote_data = self.processor.process_stock_quote(symbol, quote_data)

                # Merge price data with stock data
                if processed_quote_data:
                    # 중복 키 제거 (symbol은 이미 overview에 있음)
                    price_updates = {k: v for k, v in processed_quote_data.items() if k != 'symbol'}
                    processed_overview_data.update(price_updates)
                    
            except Exception as e:
                logger.error(f"Error fetching quote data for {symbol}: {e}")
                # 실시간 가격 조회 실패해도 기본 정보는 저장

            # Try to get existing stock or create new one
            with transaction.atomic():
                stock, created = Stock.objects.update_or_create(
                    symbol=symbol, 
                    defaults=processed_overview_data
                )

                if created:
                    logger.info(f"Created new stock: {symbol}")
                else:
                    logger.info(f"Updated existing stock: {symbol}")

                return stock

        except Exception as e:
            logger.error(f"Error saving stock data for {symbol}: {e}")
            raise

    
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

        try:
            ## 1. 일일 데이터 업데이트
            logger.info(f"Fetching daily data for {symbol}")
            daily_data = self.client.get_daily_stock_data(symbol, outputsize="compact")
            processed_daily = self.processor.process_daily_historical_prices(symbol, daily_data)
            
            if processed_daily:
                results['daily'] = self._save_daily_prices(stock_obj, processed_daily)
                logger.info(f"Updated {results['daily']} daily records for {symbol}")

            ## 2. 주간 데이터 업데이트  
            logger.info(f"Fetching weekly data for {symbol}")
            weekly_data = self.client.get_weekly_stock_data(symbol)
            processed_weekly = self.processor.process_weekly_historical_prices(symbol, weekly_data)
            
            if processed_weekly:
                results['weekly'] = self._save_weekly_prices(stock_obj, processed_weekly)
                logger.info(f"Updated {results['weekly']} weekly records for {symbol}")

        except Exception as e:
            logger.error(f"Error updating historical prices for {symbol}: {e}")
            raise

        return results
    
    def update_financial_statements(self, stock: Union[Stock, str]) -> Dict[str, int]:
        """
        ## Update financial statement data (Balance Sheet, Income Statement, Cash Flow)
        # - 재무제표 데이터를 일괄 업데이트
        # - 연간 및 분기 데이터 모두 처리
        
        Args:
            stock: Stock object or symbol string
            
        Returns:
            Dict containing count of updated records for each statement type
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
    
        logger.info(f"Updating financial statements for {symbol}")
        
        results = {
            'balance_sheets': 0,
            'income_statements': 0, 
            'cash_flows': 0,
        }

        try:
            ## 1. 대차대조표 업데이트
            logger.info(f"Fetching balance sheet for {symbol}")
            balance_sheet_data = self.client.get_balance_sheet(symbol)
            processed_balance = self.processor.process_balance_sheet(balance_sheet_data)
            
            if processed_balance:
                results['balance_sheets'] = self._save_balance_sheets(stock_obj, processed_balance)

            ## 2. 손익계산서 업데이트
            logger.info(f"Fetching income statement for {symbol}")
            income_data = self.client.get_income_statement(symbol)
            processed_income = self.processor.process_income_statement(income_data)
            
            if processed_income:
                results['income_statements'] = self._save_income_statements(stock_obj, processed_income)

            ## 3. 현금흐름표 업데이트  
            logger.info(f"Fetching cash flow for {symbol}")
            cash_flow_data = self.client.get_cash_flow(symbol)
            processed_cash_flow = self.processor.process_cash_flow(cash_flow_data)
            
            if processed_cash_flow:
                results['cash_flows'] = self._save_cash_flows(stock_obj, processed_cash_flow)

            logger.info(f"Updated financial statements for {symbol}: {results}")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error updating financial statements for {symbol}: {e}\nTraceback:\n{error_details}")
            raise

        return results
    
    def _save_daily_prices(self, stock: Stock, price_data: List[Dict[str, Any]]) -> int:
        """
        ## 일일 가격 데이터를 배치로 저장
        # - 중복 데이터 방지
        # - 트랜잭션 처리로 데이터 일관성 보장
        """
        saved_count = 0
        
        with transaction.atomic():
            for price_record in price_data:
                try:
                    # stock_symbol 키를 제거하고 실제 stock 객체 사용
                    price_record.pop('stock_symbol', None)
                    
                    daily_price, created = DailyPrice.objects.update_or_create(
                        stock=stock,
                        date=price_record['date'],
                        defaults=price_record
                    )
                    
                    if created:
                        saved_count += 1
                        
                except IntegrityError as e:
                    logger.warning(f"Duplicate daily price data for {stock.symbol} on {price_record.get('date')}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error saving daily price for {stock.symbol}: {e}")
                    continue
        
        return saved_count
        
    def _save_weekly_prices(self, stock: Stock, price_data: List[Dict[str, Any]]) -> int:    
        """
        ## 주간 가격 데이터를 배치로 저장
        # - 중복 데이터 방지
        # - 트랜잭션 처리로 데이터 일관성 보장
        """
        saved_count = 0

        with transaction.atomic():
            for price_record in price_data:
                try:
                    price_record.pop("stock_symbol", None)

                    weekly_price, created = WeeklyPrice.objects.update_or_create(stock=stock, date=price_record['date'], defaults=price_record)

                    if created:
                        saved_count += 1

                except IntegrityError as e:
                    logger.warning(f"Duplicate weekly price data for {stock.symbol} on {price_record.get('date')}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error saving weekly price for {stock.symbol}: {e}")
                    continue

        return saved_count

    def _save_balance_sheets(self, stock: Stock, balance_data: List[Dict[str, Any]]) -> int:
        """대차대조표 데이터를 배치로 저장"""
        saved_count = 0
        
        with transaction.atomic():
            for balance_record in balance_data:
                try:
                    balance_record.pop('stock_symbol', None)
                    
                    balance_sheet, created = BalanceSheet.objects.update_or_create(
                        stock=stock,
                        period_type=balance_record['period_type'],
                        fiscal_year=balance_record['fiscal_year'],
                        fiscal_quarter=balance_record.get('fiscal_quarter'),
                        defaults=balance_record
                    )
                    
                    if created:
                        saved_count += 1
                        
                except IntegrityError as e:
                    logger.warning(f"Duplicate balance sheet data for {stock.symbol}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error saving balance sheet for {stock.symbol}: {e}")
                    continue
        
        return saved_count

    def _save_income_statements(self, stock: Stock, income_data: List[Dict[str, Any]]) -> int:
        """손익계산서 데이터를 배치로 저장"""
        saved_count = 0
        
        with transaction.atomic():
            for income_record in income_data:
                try:
                    income_record.pop('stock_symbol', None)
                    
                    income_statement, created = IncomeStatement.objects.update_or_create(
                        stock=stock,
                        period_type=income_record['period_type'],
                        fiscal_year=income_record['fiscal_year'],
                        fiscal_quarter=income_record.get('fiscal_quarter'),
                        defaults=income_record
                    )
                    
                    if created:
                        saved_count += 1
                        
                except IntegrityError as e:
                    logger.warning(f"Duplicate income statement data for {stock.symbol}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error saving income statement for {stock.symbol}: {e}")
                    continue
        
        return saved_count

    def _save_cash_flows(self, stock: Stock, cash_flow_data: List[Dict[str, Any]]) -> int:
        """현금흐름표 데이터를 배치로 저장"""
        saved_count = 0
        
        with transaction.atomic():
            for cash_record in cash_flow_data:
                try:
                    cash_record.pop('stock_symbol', None)
                    
                    cash_flow, created = CashFlowStatement.objects.update_or_create(
                        stock=stock,
                        period_type=cash_record['period_type'],
                        fiscal_year=cash_record['fiscal_year'],
                        fiscal_quarter=cash_record.get('fiscal_quarter'),
                        defaults=cash_record
                    )
                    
                    if created:
                        saved_count += 1
                        
                except IntegrityError as e:
                    logger.warning(f"Duplicate cash flow data for {stock.symbol}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error saving cash flow for {stock.symbol}: {e}")
                    continue
        
        return saved_count
    
    def update_previous_close(self, symbol: str, force: bool = False) -> Dict[str, Any]:
        """
        Update stock with previous day's closing price from daily data.
        Only makes API call if not called today (unless force=True).

        Args:
            symbol: Stock symbol
            force: Force API call even if already called today

        Returns:
            Dict with update status and data
        """
        from django.utils import timezone
        from datetime import datetime, timedelta

        symbol = symbol.upper().strip()

        try:
            # Get or create stock
            stock, created = Stock.objects.get_or_create(
                symbol=symbol,
                defaults={'stock_name': symbol}
            )

            # Check if we already called API today
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            if not force and stock.last_api_call and stock.last_api_call >= today_start:
                logger.info(f"Already fetched {symbol} today at {stock.last_api_call}")
                return {
                    'status': 'cached',
                    'symbol': symbol,
                    'price': float(stock.real_time_price),
                    'message': f'Already fetched today at {stock.last_api_call}'
                }

            # Fetch daily data (only compact = last 100 days)
            logger.info(f"Fetching daily data for {symbol}")
            daily_data = self.client.get_daily_stock_data(symbol, outputsize="compact")

            if not daily_data or 'Time Series (Daily)' not in daily_data:
                logger.error(f"No daily data received for {symbol}")
                return {
                    'status': 'error',
                    'symbol': symbol,
                    'message': 'No daily data available'
                }

            time_series = daily_data['Time Series (Daily)']
            dates = sorted(time_series.keys(), reverse=True)

            if not dates:
                return {
                    'status': 'error',
                    'symbol': symbol,
                    'message': 'No price data available'
                }

            # Get the latest trading day (usually yesterday)
            latest_date = dates[0]
            latest_data = time_series[latest_date]

            # Extract price data
            close_price = float(latest_data['4. close'])
            open_price = float(latest_data['1. open'])
            high_price = float(latest_data['2. high'])
            low_price = float(latest_data['3. low'])
            volume = int(latest_data['5. volume'])

            # Calculate change from previous day if available
            if len(dates) > 1:
                prev_date = dates[1]
                prev_close = float(time_series[prev_date]['4. close'])
                change = close_price - prev_close
                change_percent = (change / prev_close * 100) if prev_close > 0 else 0
            else:
                change = 0
                change_percent = 0

            # Update stock with previous day's close as current price
            stock.real_time_price = close_price
            stock.previous_close = close_price  # Same as close for end of day
            stock.open_price = open_price
            stock.high_price = high_price
            stock.low_price = low_price
            stock.volume = volume
            stock.change = change
            stock.change_percent = f"{change_percent:.2f}%"
            stock.last_api_call = now  # Mark API call time
            stock.save()

            # Also save to DailyPrice table
            try:
                DailyPrice.objects.update_or_create(
                    stock=stock,
                    date=datetime.strptime(latest_date, '%Y-%m-%d').date(),
                    defaults={
                        'open_price': open_price,
                        'high_price': high_price,
                        'low_price': low_price,
                        'close_price': close_price,
                        'volume': volume
                    }
                )
            except Exception as e:
                logger.warning(f"Could not save DailyPrice for {symbol}: {e}")

            logger.info(f"Updated {symbol} with close price ${close_price:.2f} from {latest_date}")

            return {
                'status': 'updated',
                'symbol': symbol,
                'date': latest_date,
                'price': close_price,
                'change': change,
                'change_percent': change_percent,
                'volume': volume,
                'message': f'Updated with close price from {latest_date}'
            }

        except Exception as e:
            logger.error(f"Error updating previous close for {symbol}: {e}")
            return {
                'status': 'error',
                'symbol': symbol,
                'message': str(e)
            }

    def get_stock_summary(self, symbol: str) -> Dict[str, Any]:
        """
        ## 주식 요약 정보 조회
        # - 디버깅 및 모니터링용 메서드
        """
        try:
            stock = Stock.objects.get(symbol=symbol.upper())
            
            daily_count = DailyPrice.objects.filter(stock=stock).count()
            weekly_count = WeeklyPrice.objects.filter(stock=stock).count()
            balance_count = BalanceSheet.objects.filter(stock=stock).count()
            income_count = IncomeStatement.objects.filter(stock=stock).count()
            cash_flow_count = CashFlowStatement.objects.filter(stock=stock).count()
            
            return {
                'symbol': stock.symbol,
                'name': stock.stock_name,
                'sector': stock.sector,
                'current_price': float(stock.real_time_price or 0),
                'market_cap': float(stock.market_capitalization or 0),
                'data_counts': {
                    'daily_prices': daily_count,
                    'weekly_prices': weekly_count,
                    'balance_sheets': balance_count,
                    'income_statements': income_count,
                    'cash_flows': cash_flow_count,
                },
                'last_updated': stock.last_updated.isoformat() if stock.last_updated else None,
            }
            
        except Stock.DoesNotExist:
            return {'error': f'Stock {symbol} not found'}
        except Exception as e:
            return {'error': str(e)}