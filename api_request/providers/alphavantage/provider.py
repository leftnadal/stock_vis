# api_request/providers/alphavantage/provider.py
"""
Alpha Vantage Provider

기존 alphavantage_client.py와 alphavantage_processor.py를 활용하여
StockDataProvider 인터페이스를 구현합니다.
"""

import logging
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date

from ..base import (
    StockDataProvider,
    ProviderResponse,
    ProviderError,
    RateLimitError,
    DataNotFoundError,
    PeriodType,
    OutputSize,
    NormalizedQuote,
    NormalizedCompanyProfile,
    NormalizedPriceData,
    NormalizedBalanceSheet,
    NormalizedIncomeStatement,
    NormalizedCashFlow,
    NormalizedSearchResult,
)

# 기존 Alpha Vantage 모듈 임포트
import sys
import os
# api_request 디렉토리를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


class AlphaVantageProvider(StockDataProvider):
    """
    Alpha Vantage API Provider

    기존 alphavantage_client.py를 래핑하여 통일된 인터페이스 제공
    """

    PROVIDER_NAME = "alpha_vantage"
    RATE_LIMIT_CALLS = 5  # 분당 5회
    RATE_LIMIT_DAILY = 500  # 일일 500회 (무료)
    REQUEST_DELAY = 12.0  # 12초 대기

    def __init__(self, api_key: str):
        super().__init__(api_key)
        # 기존 클라이언트 사용
        from alphavantage_client import AlphaVantageClient
        self._client = AlphaVantageClient(api_key=api_key)

    def get_quote(self, symbol: str) -> ProviderResponse[NormalizedQuote]:
        """실시간 시세 조회"""
        try:
            symbol = symbol.upper()
            raw_data = self._client.get_stock_quote(symbol)

            quote_data = raw_data.get("Global Quote", {})
            if not quote_data:
                return ProviderResponse.error_response(
                    error=f"No quote data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            normalized = NormalizedQuote(
                symbol=symbol,
                price=self._safe_decimal(quote_data.get("05. price")),
                open=self._safe_decimal(quote_data.get("02. open")),
                high=self._safe_decimal(quote_data.get("03. high")),
                low=self._safe_decimal(quote_data.get("04. low")),
                volume=self._safe_int(quote_data.get("06. volume")),
                previous_close=self._safe_decimal(quote_data.get("08. previous close")),
                change=self._safe_decimal(quote_data.get("09. change")),
                change_percent=self._parse_percent(quote_data.get("10. change percent")),
                latest_trading_day=self._safe_date(quote_data.get("07. latest trading day")),
            )

            return ProviderResponse.success_response(
                data=normalized,
                provider=self.PROVIDER_NAME
            )

        except ValueError as e:
            if "API call frequency" in str(e) or "rate limit" in str(e).lower():
                raise RateLimitError(self.PROVIDER_NAME)
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )
        except Exception as e:
            logger.error(f"Alpha Vantage get_quote error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="UNKNOWN_ERROR"
            )

    def get_company_profile(self, symbol: str) -> ProviderResponse[NormalizedCompanyProfile]:
        """회사 프로필 조회"""
        try:
            symbol = symbol.upper()
            raw_data = self._client.get_company_overview(symbol)

            if not raw_data or "Symbol" not in raw_data:
                return ProviderResponse.error_response(
                    error=f"No company profile found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            normalized = NormalizedCompanyProfile(
                symbol=symbol,
                name=raw_data.get("Name", ""),
                description=raw_data.get("Description"),
                exchange=raw_data.get("Exchange"),
                currency=raw_data.get("Currency"),
                country=raw_data.get("Country"),
                sector=raw_data.get("Sector"),
                industry=raw_data.get("Industry"),
                market_cap=self._safe_decimal(raw_data.get("MarketCapitalization")),
                pe_ratio=self._safe_decimal(raw_data.get("PERatio")),
                beta=self._safe_decimal(raw_data.get("Beta")),
                dividend_yield=self._safe_decimal(raw_data.get("DividendYield")),
                eps=self._safe_decimal(raw_data.get("EPS")),
                high_52week=self._safe_decimal(raw_data.get("52WeekHigh")),
                low_52week=self._safe_decimal(raw_data.get("52WeekLow")),
                moving_avg_50=self._safe_decimal(raw_data.get("50DayMovingAverage")),
                moving_avg_200=self._safe_decimal(raw_data.get("200DayMovingAverage")),
                shares_outstanding=self._safe_int(raw_data.get("SharesOutstanding")),
                website=raw_data.get("OfficialSite"),
            )

            return ProviderResponse.success_response(
                data=normalized,
                provider=self.PROVIDER_NAME
            )

        except Exception as e:
            logger.error(f"Alpha Vantage get_company_profile error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_daily_prices(
        self,
        symbol: str,
        output_size: OutputSize = OutputSize.COMPACT
    ) -> ProviderResponse[List[NormalizedPriceData]]:
        """일별 가격 데이터 조회"""
        try:
            symbol = symbol.upper()
            size = "full" if output_size == OutputSize.FULL else "compact"
            raw_data = self._client.get_daily_stock_data(symbol, outputsize=size)

            time_series = raw_data.get("Time Series (Daily)", {})
            if not time_series:
                return ProviderResponse.error_response(
                    error=f"No daily price data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            prices = []
            for date_str, price_data in time_series.items():
                try:
                    price_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                    # 주말 필터링
                    if price_date.weekday() >= 5:
                        continue

                    # 미래 날짜 필터링
                    if price_date > date.today():
                        continue

                    normalized = NormalizedPriceData(
                        date=price_date,
                        open=self._safe_decimal(price_data.get("1. open")),
                        high=self._safe_decimal(price_data.get("2. high")),
                        low=self._safe_decimal(price_data.get("3. low")),
                        close=self._safe_decimal(price_data.get("4. close")),
                        volume=self._safe_int(price_data.get("5. volume")),
                    )
                    prices.append(normalized)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing price for {date_str}: {e}")
                    continue

            # 날짜 기준 정렬 (최신순)
            prices.sort(key=lambda x: x.date, reverse=True)

            return ProviderResponse.success_response(
                data=prices,
                provider=self.PROVIDER_NAME,
                meta={"count": len(prices)}
            )

        except Exception as e:
            logger.error(f"Alpha Vantage get_daily_prices error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_weekly_prices(self, symbol: str) -> ProviderResponse[List[NormalizedPriceData]]:
        """주별 가격 데이터 조회"""
        try:
            symbol = symbol.upper()
            raw_data = self._client.get_weekly_stock_data(symbol)

            time_series = raw_data.get("Weekly Time Series", {})
            if not time_series:
                return ProviderResponse.error_response(
                    error=f"No weekly price data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            prices = []
            for date_str, price_data in time_series.items():
                try:
                    price_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                    normalized = NormalizedPriceData(
                        date=price_date,
                        open=self._safe_decimal(price_data.get("1. open")),
                        high=self._safe_decimal(price_data.get("2. high")),
                        low=self._safe_decimal(price_data.get("3. low")),
                        close=self._safe_decimal(price_data.get("4. close")),
                        volume=self._safe_int(price_data.get("5. volume")),
                    )
                    prices.append(normalized)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing weekly price for {date_str}: {e}")
                    continue

            prices.sort(key=lambda x: x.date, reverse=True)

            return ProviderResponse.success_response(
                data=prices,
                provider=self.PROVIDER_NAME,
                meta={"count": len(prices)}
            )

        except Exception as e:
            logger.error(f"Alpha Vantage get_weekly_prices error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_balance_sheet(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedBalanceSheet]]:
        """대차대조표 조회"""
        try:
            symbol = symbol.upper()
            raw_data = self._client.get_balance_sheet(symbol)

            key = "annualReports" if period == PeriodType.ANNUAL else "quarterlyReports"
            reports = raw_data.get(key, [])

            if not reports:
                return ProviderResponse.error_response(
                    error=f"No balance sheet data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            balance_sheets = []
            for report in reports:
                try:
                    fiscal_date = self._safe_date(report.get("fiscalDateEnding"))
                    if not fiscal_date:
                        continue

                    normalized = NormalizedBalanceSheet(
                        symbol=symbol,
                        fiscal_date_ending=fiscal_date,
                        reported_currency=report.get("reportedCurrency", "USD"),
                        period_type=period,
                        total_assets=self._safe_decimal(report.get("totalAssets")),
                        current_assets=self._safe_decimal(report.get("totalCurrentAssets")),
                        cash_and_equivalents=self._safe_decimal(report.get("cashAndCashEquivalentsAtCarryingValue")),
                        short_term_investments=self._safe_decimal(report.get("shortTermInvestments")),
                        inventory=self._safe_decimal(report.get("inventory")),
                        accounts_receivable=self._safe_decimal(report.get("currentNetReceivables")),
                        non_current_assets=self._safe_decimal(report.get("totalNonCurrentAssets")),
                        property_plant_equipment=self._safe_decimal(report.get("propertyPlantEquipment")),
                        goodwill=self._safe_decimal(report.get("goodwill")),
                        intangible_assets=self._safe_decimal(report.get("intangibleAssets")),
                        total_liabilities=self._safe_decimal(report.get("totalLiabilities")),
                        current_liabilities=self._safe_decimal(report.get("totalCurrentLiabilities")),
                        accounts_payable=self._safe_decimal(report.get("accountsPayable")),
                        short_term_debt=self._safe_decimal(report.get("shortTermDebt")),
                        long_term_debt=self._safe_decimal(report.get("longTermDebt")),
                        total_shareholder_equity=self._safe_decimal(report.get("totalShareholderEquity")),
                        retained_earnings=self._safe_decimal(report.get("retainedEarnings")),
                        common_stock=self._safe_decimal(report.get("commonStock")),
                        treasury_stock=self._safe_decimal(report.get("treasuryStock")),
                    )
                    balance_sheets.append(normalized)
                except Exception as e:
                    logger.warning(f"Error parsing balance sheet: {e}")
                    continue

            return ProviderResponse.success_response(
                data=balance_sheets,
                provider=self.PROVIDER_NAME,
                meta={"count": len(balance_sheets), "period": period.value}
            )

        except Exception as e:
            logger.error(f"Alpha Vantage get_balance_sheet error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_income_statement(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedIncomeStatement]]:
        """손익계산서 조회"""
        try:
            symbol = symbol.upper()
            raw_data = self._client.get_income_statement(symbol)

            key = "annualReports" if period == PeriodType.ANNUAL else "quarterlyReports"
            reports = raw_data.get(key, [])

            if not reports:
                return ProviderResponse.error_response(
                    error=f"No income statement data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            statements = []
            for report in reports:
                try:
                    fiscal_date = self._safe_date(report.get("fiscalDateEnding"))
                    if not fiscal_date:
                        continue

                    normalized = NormalizedIncomeStatement(
                        symbol=symbol,
                        fiscal_date_ending=fiscal_date,
                        reported_currency=report.get("reportedCurrency", "USD"),
                        period_type=period,
                        total_revenue=self._safe_decimal(report.get("totalRevenue")),
                        cost_of_revenue=self._safe_decimal(report.get("costOfRevenue")),
                        gross_profit=self._safe_decimal(report.get("grossProfit")),
                        operating_expenses=self._safe_decimal(report.get("operatingExpenses")),
                        operating_income=self._safe_decimal(report.get("operatingIncome")),
                        interest_expense=self._safe_decimal(report.get("interestExpense")),
                        income_before_tax=self._safe_decimal(report.get("incomeBeforeTax")),
                        income_tax_expense=self._safe_decimal(report.get("incomeTaxExpense")),
                        net_income=self._safe_decimal(report.get("netIncome")),
                        ebitda=self._safe_decimal(report.get("ebitda")),
                    )
                    statements.append(normalized)
                except Exception as e:
                    logger.warning(f"Error parsing income statement: {e}")
                    continue

            return ProviderResponse.success_response(
                data=statements,
                provider=self.PROVIDER_NAME,
                meta={"count": len(statements), "period": period.value}
            )

        except Exception as e:
            logger.error(f"Alpha Vantage get_income_statement error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_cash_flow(
        self,
        symbol: str,
        period: PeriodType = PeriodType.ANNUAL
    ) -> ProviderResponse[List[NormalizedCashFlow]]:
        """현금흐름표 조회"""
        try:
            symbol = symbol.upper()
            raw_data = self._client.get_cash_flow(symbol)

            key = "annualReports" if period == PeriodType.ANNUAL else "quarterlyReports"
            reports = raw_data.get(key, [])

            if not reports:
                return ProviderResponse.error_response(
                    error=f"No cash flow data found for {symbol}",
                    provider=self.PROVIDER_NAME,
                    error_code="DATA_NOT_FOUND"
                )

            cash_flows = []
            for report in reports:
                try:
                    fiscal_date = self._safe_date(report.get("fiscalDateEnding"))
                    if not fiscal_date:
                        continue

                    normalized = NormalizedCashFlow(
                        symbol=symbol,
                        fiscal_date_ending=fiscal_date,
                        reported_currency=report.get("reportedCurrency", "USD"),
                        period_type=period,
                        operating_cash_flow=self._safe_decimal(report.get("operatingCashflow")),
                        net_income=self._safe_decimal(report.get("netIncome")),
                        depreciation=self._safe_decimal(report.get("depreciationDepletionAndAmortization")),
                        investing_cash_flow=self._safe_decimal(report.get("cashflowFromInvestment")),
                        capital_expenditures=self._safe_decimal(report.get("capitalExpenditures")),
                        financing_cash_flow=self._safe_decimal(report.get("cashflowFromFinancing")),
                        dividends_paid=self._safe_decimal(report.get("dividendPayout")),
                        net_change_in_cash=self._safe_decimal(report.get("changeInCashAndCashEquivalents")),
                    )
                    cash_flows.append(normalized)
                except Exception as e:
                    logger.warning(f"Error parsing cash flow: {e}")
                    continue

            return ProviderResponse.success_response(
                data=cash_flows,
                provider=self.PROVIDER_NAME,
                meta={"count": len(cash_flows), "period": period.value}
            )

        except Exception as e:
            logger.error(f"Alpha Vantage get_cash_flow error for {symbol}: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def search_symbols(self, keywords: str) -> ProviderResponse[List[NormalizedSearchResult]]:
        """종목 검색"""
        try:
            raw_results = self._client.search_stocks(keywords)

            if not raw_results:
                return ProviderResponse.success_response(
                    data=[],
                    provider=self.PROVIDER_NAME,
                    meta={"count": 0}
                )

            results = []
            for match in raw_results:
                normalized = NormalizedSearchResult(
                    symbol=match.get("1. symbol", ""),
                    name=match.get("2. name", ""),
                    type=match.get("3. type"),
                    exchange=match.get("4. region"),
                    currency=match.get("8. currency"),
                    match_score=float(match.get("9. matchScore", 0)) if match.get("9. matchScore") else None,
                )
                results.append(normalized)

            return ProviderResponse.success_response(
                data=results,
                provider=self.PROVIDER_NAME,
                meta={"count": len(results)}
            )

        except Exception as e:
            logger.error(f"Alpha Vantage search_symbols error for '{keywords}': {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    def get_sector_performance(self) -> ProviderResponse:
        """섹터 성과 조회"""
        try:
            raw_data = self._client.get_sector_performance()

            return ProviderResponse.success_response(
                data=raw_data,
                provider=self.PROVIDER_NAME
            )

        except Exception as e:
            logger.error(f"Alpha Vantage get_sector_performance error: {e}")
            return ProviderResponse.error_response(
                error=str(e),
                provider=self.PROVIDER_NAME,
                error_code="API_ERROR"
            )

    # ============================================================
    # 유틸리티 메서드
    # ============================================================

    @staticmethod
    def _safe_decimal(value) -> Optional[Decimal]:
        """안전한 Decimal 변환"""
        if value is None or value == "" or value == "None":
            return None
        try:
            return Decimal(str(value))
        except:
            return None

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        """안전한 int 변환"""
        if value is None or value == "" or value == "None":
            return None
        try:
            return int(float(value))
        except:
            return None

    @staticmethod
    def _safe_date(value) -> Optional[date]:
        """안전한 date 변환"""
        if value is None or value == "" or value == "None":
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except:
            return None

    @staticmethod
    def _parse_percent(value) -> Optional[Decimal]:
        """퍼센트 문자열 파싱 (예: "1.25%" -> 1.25)"""
        if value is None or value == "":
            return None
        try:
            clean = str(value).replace("%", "").strip()
            return Decimal(clean)
        except:
            return None
