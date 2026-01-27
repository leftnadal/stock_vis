# api_request/stock_service.py
"""
Stock Service - Provider 추상화를 활용한 통합 서비스

Provider Factory를 통해 Feature Flag 기반으로 Alpha Vantage 또는 FMP를 선택합니다.
Fallback 기능을 지원하여 주 provider 실패 시 대체 provider를 자동 사용합니다.

Usage:
    from api_request.stock_service import StockService

    service = StockService()
    quote = service.get_quote('AAPL')  # ProviderResponse 반환
    service.update_stock_data('AAPL')   # DB에 저장 후 Stock 반환
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.db.utils import IntegrityError
from django.conf import settings

from stocks.models import Stock, BalanceSheet, IncomeStatement, CashFlowStatement, DailyPrice, WeeklyPrice

from .providers.base import (
    ProviderResponse,
    NormalizedQuote,
    NormalizedCompanyProfile,
    NormalizedPriceData,
    NormalizedBalanceSheet,
    NormalizedIncomeStatement,
    NormalizedCashFlow,
    NormalizedSearchResult,
    PeriodType,
    OutputSize,
)
from .providers.factory import (
    ProviderFactory,
    EndpointType,
    call_with_fallback,
)

logger = logging.getLogger(__name__)


class StockService:
    """
    Provider 추상화를 활용한 통합 Stock 서비스

    기존 AlphaVantageService와 호환되면서
    FMP Fallback 및 Feature Flag 기능을 지원합니다.
    """

    def __init__(self):
        """Initialize Stock Service"""
        self._factory = ProviderFactory

    # ============================================================
    # Provider Direct Access (ProviderResponse 반환)
    # ============================================================

    def get_quote(self, symbol: str) -> ProviderResponse[NormalizedQuote]:
        """
        실시간 시세 조회 (Provider 직접 호출)

        Args:
            symbol: 주식 심볼

        Returns:
            ProviderResponse[NormalizedQuote]
        """
        symbol = symbol.upper().strip()
        return call_with_fallback(EndpointType.QUOTE, 'get_quote', symbol)

    def get_company_profile(self, symbol: str) -> ProviderResponse[NormalizedCompanyProfile]:
        """
        회사 프로필 조회 (Provider 직접 호출)

        Args:
            symbol: 주식 심볼

        Returns:
            ProviderResponse[NormalizedCompanyProfile]
        """
        symbol = symbol.upper().strip()
        return call_with_fallback(EndpointType.PROFILE, 'get_company_profile', symbol)

    def get_daily_prices(
        self,
        symbol: str,
        output_size: OutputSize = OutputSize.COMPACT
    ) -> ProviderResponse[List[NormalizedPriceData]]:
        """
        일별 가격 데이터 조회 (Provider 직접 호출)

        Args:
            symbol: 주식 심볼
            output_size: COMPACT (100일) or FULL (20년)

        Returns:
            ProviderResponse[List[NormalizedPriceData]]
        """
        symbol = symbol.upper().strip()
        return call_with_fallback(EndpointType.DAILY_PRICES, 'get_daily_prices', symbol, output_size)

    def get_weekly_prices(self, symbol: str) -> ProviderResponse[List[NormalizedPriceData]]:
        """
        주별 가격 데이터 조회 (Provider 직접 호출)

        Args:
            symbol: 주식 심볼

        Returns:
            ProviderResponse[List[NormalizedPriceData]]
        """
        symbol = symbol.upper().strip()
        return call_with_fallback(EndpointType.WEEKLY_PRICES, 'get_weekly_prices', symbol)

    def get_balance_sheet(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedBalanceSheet]]:
        """
        대차대조표 조회 (Provider 직접 호출)

        Args:
            symbol: 주식 심볼
            period: ANNUAL or QUARTERLY

        Returns:
            ProviderResponse[List[NormalizedBalanceSheet]]
        """
        symbol = symbol.upper().strip()
        return call_with_fallback(EndpointType.BALANCE_SHEET, 'get_balance_sheet', symbol, period)

    def get_income_statement(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedIncomeStatement]]:
        """
        손익계산서 조회 (Provider 직접 호출)

        Args:
            symbol: 주식 심볼
            period: ANNUAL or QUARTERLY

        Returns:
            ProviderResponse[List[NormalizedIncomeStatement]]
        """
        symbol = symbol.upper().strip()
        return call_with_fallback(EndpointType.INCOME_STATEMENT, 'get_income_statement', symbol, period)

    def get_cash_flow(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedCashFlow]]:
        """
        현금흐름표 조회 (Provider 직접 호출)

        Args:
            symbol: 주식 심볼
            period: ANNUAL or QUARTERLY

        Returns:
            ProviderResponse[List[NormalizedCashFlow]]
        """
        symbol = symbol.upper().strip()
        return call_with_fallback(EndpointType.CASH_FLOW, 'get_cash_flow', symbol, period)

    def search_symbols(self, keywords: str) -> ProviderResponse[List[NormalizedSearchResult]]:
        """
        종목 검색 (Provider 직접 호출)

        Args:
            keywords: 검색 키워드

        Returns:
            ProviderResponse[List[NormalizedSearchResult]]
        """
        return call_with_fallback(EndpointType.SEARCH, 'search_symbols', keywords)

    # ============================================================
    # DB 저장 메서드 (기존 AlphaVantageService 호환)
    # ============================================================

    def update_stock_data(self, symbol: str) -> Stock:
        """
        주식 기본 정보 및 실시간 가격을 DB에 업데이트

        기존 AlphaVantageService.update_stock_data()와 호환

        Args:
            symbol: 주식 심볼

        Returns:
            Stock: 업데이트된 Stock 객체
        """
        symbol = symbol.upper().strip()

        try:
            # 1. 회사 프로필 조회
            logger.info(f"Fetching company profile for {symbol}")
            profile_response = self.get_company_profile(symbol)

            if not profile_response.success:
                # 기존 데이터가 있으면 반환
                try:
                    stock = Stock.objects.get(symbol=symbol)
                    logger.warning(f"Could not fetch profile for {symbol}, using existing data")
                    return stock
                except Stock.DoesNotExist:
                    logger.error(f"Could not fetch profile for {symbol} and stock does not exist")
                    raise ValueError(f"Could not fetch stock data for {symbol}: {profile_response.error}")

            profile = profile_response.data

            # 2. 실시간 시세 조회
            quote_data = {}
            try:
                logger.info(f"Fetching real-time quote for {symbol}")
                quote_response = self.get_quote(symbol)

                if quote_response.success:
                    quote = quote_response.data
                    quote_data = {
                        'real_time_price': quote.price,
                        'previous_close': quote.previous_close,
                        'open_price': quote.open,
                        'high_price': quote.high,
                        'low_price': quote.low,
                        'volume': quote.volume,
                        'change': quote.change,
                        'change_percent': f"{quote.change_percent:.2f}%" if quote.change_percent else None,
                    }
            except Exception as e:
                logger.warning(f"Error fetching quote for {symbol}: {e}")

            # 3. DB 저장
            with transaction.atomic():
                stock_data = {
                    'stock_name': profile.name,
                    'sector': profile.sector,
                    'industry': profile.industry,
                    'market_capitalization': profile.market_cap,
                    'pe_ratio': profile.pe_ratio,
                    'eps': profile.eps,
                    'beta': profile.beta,
                    'dividend_yield': profile.dividend_yield,
                    'exchange': profile.exchange,
                    'asset_type': 'Common Stock',
                    'description': profile.description,
                    **quote_data,
                }

                # None 값 필터링
                stock_data = {k: v for k, v in stock_data.items() if v is not None}

                stock, created = Stock.objects.update_or_create(
                    symbol=symbol,
                    defaults=stock_data
                )

                if created:
                    logger.info(f"Created new stock: {symbol}")
                else:
                    logger.info(f"Updated existing stock: {symbol}")

                return stock

        except Exception as e:
            logger.error(f"Error updating stock data for {symbol}: {e}")
            raise

    def update_historical_prices(self, stock: Union[Stock, str], days: int = 100) -> Dict[str, int]:
        """
        가격 데이터(일간, 주간)를 DB에 업데이트

        기존 AlphaVantageService.update_historical_prices()와 호환

        Args:
            stock: Stock 객체 또는 심볼 문자열
            days: 가져올 일수 (참고용, 실제로는 COMPACT/FULL로 결정)

        Returns:
            Dict[str, int]: 저장된 레코드 수
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

        logger.info(f"Updating historical prices for {symbol}")

        results = {
            'daily_prices': 0,
            'weekly_prices': 0,
        }

        try:
            # 1. 일별 데이터
            output_size = OutputSize.FULL if days > 100 else OutputSize.COMPACT
            daily_response = self.get_daily_prices(symbol, output_size)

            if daily_response.success and daily_response.data:
                results['daily_prices'] = self._save_daily_prices(stock_obj, daily_response.data)
                logger.info(f"Updated {results['daily_prices']} daily records for {symbol}")

            # 2. 주별 데이터
            weekly_response = self.get_weekly_prices(symbol)

            if weekly_response.success and weekly_response.data:
                results['weekly_prices'] = self._save_weekly_prices(stock_obj, weekly_response.data)
                logger.info(f"Updated {results['weekly_prices']} weekly records for {symbol}")

        except Exception as e:
            logger.error(f"Error updating historical prices for {symbol}: {e}")
            raise

        return results

    def update_financial_statements(self, stock: Union[Stock, str]) -> Dict[str, int]:
        """
        재무제표(대차대조표, 손익계산서, 현금흐름표)를 DB에 업데이트

        기존 AlphaVantageService.update_financial_statements()와 호환

        Args:
            stock: Stock 객체 또는 심볼 문자열

        Returns:
            Dict[str, int]: 저장된 레코드 수
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
            # 연간 + 분기 데이터 모두 가져오기
            for period in [PeriodType.ANNUAL, PeriodType.QUARTERLY]:
                # 1. 대차대조표
                balance_response = self.get_balance_sheet(symbol, period)
                if balance_response.success and balance_response.data:
                    count = self._save_balance_sheets(stock_obj, balance_response.data, period)
                    results['balance_sheets'] += count

                # 2. 손익계산서
                income_response = self.get_income_statement(symbol, period)
                if income_response.success and income_response.data:
                    count = self._save_income_statements(stock_obj, income_response.data, period)
                    results['income_statements'] += count

                # 3. 현금흐름표
                cash_flow_response = self.get_cash_flow(symbol, period)
                if cash_flow_response.success and cash_flow_response.data:
                    count = self._save_cash_flows(stock_obj, cash_flow_response.data, period)
                    results['cash_flows'] += count

            logger.info(f"Updated financial statements for {symbol}: {results}")

        except Exception as e:
            logger.error(f"Error updating financial statements for {symbol}: {e}")
            raise

        return results

    # ============================================================
    # Private 저장 헬퍼 메서드
    # ============================================================

    def _save_daily_prices(self, stock: Stock, prices: List[NormalizedPriceData]) -> int:
        """일별 가격 데이터를 DB에 저장"""
        saved_count = 0

        with transaction.atomic():
            for price in prices:
                try:
                    _, created = DailyPrice.objects.update_or_create(
                        stock=stock,
                        date=price.date,
                        defaults={
                            'open_price': price.open,
                            'high_price': price.high,
                            'low_price': price.low,
                            'close_price': price.close,
                            'volume': price.volume,
                        }
                    )
                    if created:
                        saved_count += 1
                except IntegrityError as e:
                    logger.warning(f"Duplicate daily price for {stock.symbol} on {price.date}: {e}")
                except Exception as e:
                    logger.error(f"Error saving daily price for {stock.symbol}: {e}")

        return saved_count

    def _save_weekly_prices(self, stock: Stock, prices: List[NormalizedPriceData]) -> int:
        """주별 가격 데이터를 DB에 저장"""
        saved_count = 0

        with transaction.atomic():
            for price in prices:
                try:
                    _, created = WeeklyPrice.objects.update_or_create(
                        stock=stock,
                        date=price.date,
                        defaults={
                            'open_price': price.open,
                            'high_price': price.high,
                            'low_price': price.low,
                            'close_price': price.close,
                            'volume': price.volume,
                        }
                    )
                    if created:
                        saved_count += 1
                except IntegrityError as e:
                    logger.warning(f"Duplicate weekly price for {stock.symbol} on {price.date}: {e}")
                except Exception as e:
                    logger.error(f"Error saving weekly price for {stock.symbol}: {e}")

        return saved_count

    def _save_balance_sheets(
        self,
        stock: Stock,
        sheets: List[NormalizedBalanceSheet],
        period: PeriodType
    ) -> int:
        """대차대조표 데이터를 DB에 저장"""
        saved_count = 0
        period_type = 'annual' if period == PeriodType.ANNUAL else 'quarterly'

        with transaction.atomic():
            for sheet in sheets:
                try:
                    fiscal_date = sheet.fiscal_date_ending
                    fiscal_year = fiscal_date.year
                    fiscal_quarter = ((fiscal_date.month - 1) // 3) + 1 if period_type == 'quarterly' else None

                    defaults = {
                        'fiscal_date_ending': fiscal_date,
                        'reported_currency': sheet.reported_currency,
                        'total_assets': sheet.total_assets,
                        'total_current_assets': sheet.current_assets,
                        'cash_and_cash_equivalents': sheet.cash_and_equivalents,
                        'short_term_investments': sheet.short_term_investments,
                        'inventory': sheet.inventory,
                        'current_net_receivables': sheet.accounts_receivable,
                        'total_non_current_assets': sheet.non_current_assets,
                        'property_plant_equipment': sheet.property_plant_equipment,
                        'goodwill': sheet.goodwill,
                        'intangible_assets': sheet.intangible_assets,
                        'total_liabilities': sheet.total_liabilities,
                        'total_current_liabilities': sheet.current_liabilities,
                        'accounts_payable': sheet.accounts_payable,
                        'short_term_debt': sheet.short_term_debt,
                        'long_term_debt': sheet.long_term_debt,
                        'total_shareholder_equity': sheet.total_shareholder_equity,
                        'retained_earnings': sheet.retained_earnings,
                        'common_stock': sheet.common_stock,
                        'treasury_stock': sheet.treasury_stock,
                    }

                    # None 값 필터링
                    defaults = {k: v for k, v in defaults.items() if v is not None}

                    _, created = BalanceSheet.objects.update_or_create(
                        stock=stock,
                        period_type=period_type,
                        fiscal_year=fiscal_year,
                        fiscal_quarter=fiscal_quarter,
                        defaults=defaults
                    )
                    if created:
                        saved_count += 1
                except IntegrityError as e:
                    logger.warning(f"Duplicate balance sheet for {stock.symbol}: {e}")
                except Exception as e:
                    logger.error(f"Error saving balance sheet for {stock.symbol}: {e}")

        return saved_count

    def _save_income_statements(
        self,
        stock: Stock,
        statements: List[NormalizedIncomeStatement],
        period: PeriodType
    ) -> int:
        """손익계산서 데이터를 DB에 저장"""
        saved_count = 0
        period_type = 'annual' if period == PeriodType.ANNUAL else 'quarterly'

        with transaction.atomic():
            for stmt in statements:
                try:
                    fiscal_date = stmt.fiscal_date_ending
                    fiscal_year = fiscal_date.year
                    fiscal_quarter = ((fiscal_date.month - 1) // 3) + 1 if period_type == 'quarterly' else None

                    defaults = {
                        'fiscal_date_ending': fiscal_date,
                        'reported_currency': stmt.reported_currency,
                        'total_revenue': stmt.total_revenue,
                        'cost_of_revenue': stmt.cost_of_revenue,
                        'gross_profit': stmt.gross_profit,
                        'operating_expenses': stmt.operating_expenses,
                        'operating_income': stmt.operating_income,
                        'interest_expense': stmt.interest_expense,
                        'income_before_tax': stmt.income_before_tax,
                        'income_tax_expense': stmt.income_tax_expense,
                        'net_income': stmt.net_income,
                        'ebitda': stmt.ebitda,
                    }

                    # None 값 필터링
                    defaults = {k: v for k, v in defaults.items() if v is not None}

                    _, created = IncomeStatement.objects.update_or_create(
                        stock=stock,
                        period_type=period_type,
                        fiscal_year=fiscal_year,
                        fiscal_quarter=fiscal_quarter,
                        defaults=defaults
                    )
                    if created:
                        saved_count += 1
                except IntegrityError as e:
                    logger.warning(f"Duplicate income statement for {stock.symbol}: {e}")
                except Exception as e:
                    logger.error(f"Error saving income statement for {stock.symbol}: {e}")

        return saved_count

    def _save_cash_flows(
        self,
        stock: Stock,
        flows: List[NormalizedCashFlow],
        period: PeriodType
    ) -> int:
        """현금흐름표 데이터를 DB에 저장"""
        saved_count = 0
        period_type = 'annual' if period == PeriodType.ANNUAL else 'quarterly'

        with transaction.atomic():
            for flow in flows:
                try:
                    fiscal_date = flow.fiscal_date_ending
                    fiscal_year = fiscal_date.year
                    fiscal_quarter = ((fiscal_date.month - 1) // 3) + 1 if period_type == 'quarterly' else None

                    defaults = {
                        'fiscal_date_ending': fiscal_date,
                        'reported_currency': flow.reported_currency,
                        'operating_cashflow': flow.operating_cash_flow,
                        'net_income': flow.net_income,
                        'depreciation_amortization': flow.depreciation,
                        'cashflow_from_investment': flow.investing_cash_flow,
                        'capital_expenditures': flow.capital_expenditures,
                        'cashflow_from_financing': flow.financing_cash_flow,
                        'dividend_payout': flow.dividends_paid,
                        'change_in_cash': flow.net_change_in_cash,
                    }

                    # None 값 필터링
                    defaults = {k: v for k, v in defaults.items() if v is not None}

                    _, created = CashFlowStatement.objects.update_or_create(
                        stock=stock,
                        period_type=period_type,
                        fiscal_year=fiscal_year,
                        fiscal_quarter=fiscal_quarter,
                        defaults=defaults
                    )
                    if created:
                        saved_count += 1
                except IntegrityError as e:
                    logger.warning(f"Duplicate cash flow for {stock.symbol}: {e}")
                except Exception as e:
                    logger.error(f"Error saving cash flow for {stock.symbol}: {e}")

        return saved_count

    # ============================================================
    # 유틸리티 메서드
    # ============================================================

    def update_previous_close(self, symbol: str, force: bool = False) -> Dict[str, Any]:
        """
        전일 종가로 주식 가격 업데이트

        기존 AlphaVantageService.update_previous_close()와 호환

        Args:
            symbol: 주식 심볼
            force: True면 캐시 무시하고 강제 업데이트

        Returns:
            Dict with status info
        """
        from django.utils import timezone

        symbol = symbol.upper().strip()

        try:
            stock, created = Stock.objects.get_or_create(
                symbol=symbol,
                defaults={'stock_name': symbol}
            )

            # 오늘 이미 업데이트했는지 확인
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            if not force and stock.last_api_call and stock.last_api_call >= today_start:
                logger.info(f"Already fetched {symbol} today at {stock.last_api_call}")
                return {
                    'status': 'cached',
                    'symbol': symbol,
                    'price': float(stock.real_time_price or 0),
                    'message': f'Already fetched today at {stock.last_api_call}'
                }

            # 일별 가격 데이터 조회
            daily_response = self.get_daily_prices(symbol, OutputSize.COMPACT)

            if not daily_response.success or not daily_response.data:
                return {
                    'status': 'error',
                    'symbol': symbol,
                    'message': daily_response.error or 'No daily data available'
                }

            # 최신 가격 추출
            prices = sorted(daily_response.data, key=lambda x: x.date, reverse=True)
            if not prices:
                return {
                    'status': 'error',
                    'symbol': symbol,
                    'message': 'No price data available'
                }

            latest = prices[0]

            # 변동 계산
            if len(prices) > 1:
                prev = prices[1]
                change = float(latest.close - prev.close) if latest.close and prev.close else 0
                change_percent = (change / float(prev.close) * 100) if prev.close else 0
            else:
                change = 0
                change_percent = 0

            # Stock 업데이트
            stock.real_time_price = latest.close
            stock.previous_close = latest.close
            stock.open_price = latest.open
            stock.high_price = latest.high
            stock.low_price = latest.low
            stock.volume = latest.volume
            stock.change = Decimal(str(change))
            stock.change_percent = f"{change_percent:.2f}%"
            stock.last_api_call = now
            stock.save()

            # DailyPrice에도 저장
            try:
                DailyPrice.objects.update_or_create(
                    stock=stock,
                    date=latest.date,
                    defaults={
                        'open_price': latest.open,
                        'high_price': latest.high,
                        'low_price': latest.low,
                        'close_price': latest.close,
                        'volume': latest.volume,
                    }
                )
            except Exception as e:
                logger.warning(f"Could not save DailyPrice for {symbol}: {e}")

            logger.info(f"Updated {symbol} with close price ${latest.close} from {latest.date}")

            return {
                'status': 'updated',
                'symbol': symbol,
                'date': str(latest.date),
                'price': float(latest.close) if latest.close else 0,
                'change': change,
                'change_percent': change_percent,
                'volume': latest.volume,
                'message': f'Updated with close price from {latest.date}'
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
        주식 요약 정보 조회

        기존 AlphaVantageService.get_stock_summary()와 호환
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

    def get_provider_info(self) -> Dict[str, Any]:
        """
        현재 Provider 설정 정보 조회
        """
        return {
            'providers': getattr(settings, 'STOCK_PROVIDERS', {}),
            'fallback_enabled': getattr(settings, 'PROVIDER_FALLBACK_ENABLED', True),
            'cache_ttl': getattr(settings, 'PROVIDER_CACHE_TTL', {}),
        }


# 편의를 위한 싱글톤 인스턴스
_stock_service_instance = None

def get_stock_service() -> StockService:
    """
    StockService 싱글톤 인스턴스 반환

    Usage:
        from api_request.stock_service import get_stock_service

        service = get_stock_service()
        quote = service.get_quote('AAPL')
    """
    global _stock_service_instance
    if _stock_service_instance is None:
        _stock_service_instance = StockService()
    return _stock_service_instance
