# api_request/providers/fmp/processor.py
"""
FMP Data Processor

FMP API 응답을 정규화된 데이터 모델로 변환합니다.
Alpha Vantage와 다른 필드명을 통일된 형식으로 매핑합니다.
"""

import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional

from ..base import (
    NormalizedQuote,
    NormalizedCompanyProfile,
    NormalizedPriceData,
    NormalizedBalanceSheet,
    NormalizedIncomeStatement,
    NormalizedCashFlow,
    NormalizedSearchResult,
    PeriodType,
)

logger = logging.getLogger(__name__)


class FMPProcessor:
    """
    FMP API 응답 데이터 처리기

    FMP API의 응답을 정규화된 데이터 모델로 변환합니다.
    """

    @staticmethod
    def process_quote(symbol: str, data: Dict[str, Any]) -> Optional[NormalizedQuote]:
        """
        FMP 시세 데이터를 정규화

        FMP 필드 -> 정규화 필드 매핑:
        - price -> price
        - open -> open
        - dayHigh -> high
        - dayLow -> low
        - volume -> volume
        - previousClose -> previous_close
        - change -> change
        - changesPercentage -> change_percent
        """
        if not data:
            return None

        try:
            return NormalizedQuote(
                symbol=symbol.upper(),
                price=FMPProcessor._safe_decimal(data.get("price")),
                open=FMPProcessor._safe_decimal(data.get("open")),
                high=FMPProcessor._safe_decimal(data.get("dayHigh")),
                low=FMPProcessor._safe_decimal(data.get("dayLow")),
                volume=FMPProcessor._safe_int(data.get("volume")),
                previous_close=FMPProcessor._safe_decimal(data.get("previousClose")),
                change=FMPProcessor._safe_decimal(data.get("change")),
                change_percent=FMPProcessor._safe_decimal(data.get("changesPercentage")),
                latest_trading_day=FMPProcessor._safe_date(data.get("timestamp")),
                timestamp=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Error processing FMP quote for {symbol}: {e}")
            return None

    @staticmethod
    def process_company_profile(data: Dict[str, Any]) -> Optional[NormalizedCompanyProfile]:
        """
        FMP 회사 프로필을 정규화

        FMP 필드 -> 정규화 필드 매핑:
        - symbol -> symbol
        - companyName -> name
        - description -> description
        - exchange -> exchange
        - currency -> currency
        - country -> country
        - sector -> sector
        - industry -> industry
        - mktCap -> market_cap
        - beta -> beta
        - lastDiv -> dividend_yield (연율화 필요)
        - range -> 52week range (파싱 필요)
        - website -> website
        - ceo -> ceo
        - fullTimeEmployees -> full_time_employees
        - ipoDate -> ipo_date
        """
        if not data:
            return None

        try:
            # 52주 범위 파싱 (예: "142.00-199.62")
            week_range = data.get("range", "")
            low_52, high_52 = None, None
            if week_range and "-" in week_range:
                parts = week_range.split("-")
                if len(parts) == 2:
                    low_52 = FMPProcessor._safe_decimal(parts[0])
                    high_52 = FMPProcessor._safe_decimal(parts[1])

            return NormalizedCompanyProfile(
                symbol=data.get("symbol", "").upper(),
                name=data.get("companyName", ""),
                description=data.get("description"),
                exchange=data.get("exchange") or data.get("exchangeShortName"),
                currency=data.get("currency"),
                country=data.get("country"),
                sector=data.get("sector"),
                industry=data.get("industry"),
                market_cap=FMPProcessor._safe_decimal(data.get("mktCap")),
                beta=FMPProcessor._safe_decimal(data.get("beta")),
                dividend_yield=FMPProcessor._safe_decimal(data.get("lastDiv")),
                high_52week=high_52,
                low_52week=low_52,
                shares_outstanding=FMPProcessor._safe_int(data.get("volAvg")),  # 대략적
                website=data.get("website"),
                ceo=data.get("ceo"),
                full_time_employees=FMPProcessor._safe_int(data.get("fullTimeEmployees")),
                ipo_date=FMPProcessor._safe_date(data.get("ipoDate")),
            )
        except Exception as e:
            logger.error(f"Error processing FMP company profile: {e}")
            return None

    @staticmethod
    def process_historical_prices(
        symbol: str,
        data: List[Dict[str, Any]]
    ) -> List[NormalizedPriceData]:
        """
        FMP 과거 가격 데이터를 정규화

        FMP 필드 -> 정규화 필드 매핑:
        - date -> date
        - open -> open
        - high -> high
        - low -> low
        - close -> close
        - volume -> volume
        - adjClose -> adjusted_close
        """
        if not data:
            return []

        prices = []
        for item in data:
            try:
                price_date = FMPProcessor._safe_date(item.get("date"))
                if not price_date:
                    continue

                # 미래 날짜 필터링
                if price_date > date.today():
                    continue

                # 유효하지 않은 데이터 필터링
                close_price = FMPProcessor._safe_decimal(item.get("close"))
                if not close_price or close_price <= 0:
                    continue

                normalized = NormalizedPriceData(
                    date=price_date,
                    open=FMPProcessor._safe_decimal(item.get("open")),
                    high=FMPProcessor._safe_decimal(item.get("high")),
                    low=FMPProcessor._safe_decimal(item.get("low")),
                    close=close_price,
                    volume=FMPProcessor._safe_int(item.get("volume")) or 0,
                    adjusted_close=FMPProcessor._safe_decimal(item.get("adjClose")),
                )
                prices.append(normalized)

            except Exception as e:
                logger.warning(f"Error processing price data for {symbol}: {e}")
                continue

        # 날짜 기준 정렬 (최신순)
        prices.sort(key=lambda x: x.date, reverse=True)
        return prices

    @staticmethod
    def process_balance_sheet(
        symbol: str,
        data: List[Dict[str, Any]],
        period_type: PeriodType
    ) -> List[NormalizedBalanceSheet]:
        """
        FMP 대차대조표를 정규화

        FMP는 camelCase 필드명 사용
        """
        if not data:
            return []

        balance_sheets = []
        for item in data:
            try:
                fiscal_date = FMPProcessor._safe_date(item.get("date"))
                if not fiscal_date:
                    continue

                normalized = NormalizedBalanceSheet(
                    symbol=symbol.upper(),
                    fiscal_date_ending=fiscal_date,
                    reported_currency=item.get("reportedCurrency", "USD"),
                    period_type=period_type,
                    fiscal_year=FMPProcessor._extract_year(item.get("calendarYear")),

                    # 자산
                    total_assets=FMPProcessor._safe_decimal(item.get("totalAssets")),
                    current_assets=FMPProcessor._safe_decimal(item.get("totalCurrentAssets")),
                    cash_and_equivalents=FMPProcessor._safe_decimal(
                        item.get("cashAndCashEquivalents")
                    ),
                    short_term_investments=FMPProcessor._safe_decimal(
                        item.get("shortTermInvestments")
                    ),
                    inventory=FMPProcessor._safe_decimal(item.get("inventory")),
                    accounts_receivable=FMPProcessor._safe_decimal(
                        item.get("netReceivables")
                    ),
                    non_current_assets=FMPProcessor._safe_decimal(
                        item.get("totalNonCurrentAssets")
                    ),
                    property_plant_equipment=FMPProcessor._safe_decimal(
                        item.get("propertyPlantEquipmentNet")
                    ),
                    goodwill=FMPProcessor._safe_decimal(item.get("goodwill")),
                    intangible_assets=FMPProcessor._safe_decimal(
                        item.get("intangibleAssets")
                    ),

                    # 부채
                    total_liabilities=FMPProcessor._safe_decimal(
                        item.get("totalLiabilities")
                    ),
                    current_liabilities=FMPProcessor._safe_decimal(
                        item.get("totalCurrentLiabilities")
                    ),
                    accounts_payable=FMPProcessor._safe_decimal(
                        item.get("accountPayables")
                    ),
                    short_term_debt=FMPProcessor._safe_decimal(
                        item.get("shortTermDebt")
                    ),
                    long_term_debt=FMPProcessor._safe_decimal(
                        item.get("longTermDebt")
                    ),

                    # 자본
                    total_shareholder_equity=FMPProcessor._safe_decimal(
                        item.get("totalStockholdersEquity")
                    ),
                    retained_earnings=FMPProcessor._safe_decimal(
                        item.get("retainedEarnings")
                    ),
                    common_stock=FMPProcessor._safe_decimal(
                        item.get("commonStock")
                    ),
                    treasury_stock=FMPProcessor._safe_decimal(
                        item.get("treasuryStock")
                    ),
                )
                balance_sheets.append(normalized)

            except Exception as e:
                logger.warning(f"Error processing balance sheet for {symbol}: {e}")
                continue

        return balance_sheets

    @staticmethod
    def process_income_statement(
        symbol: str,
        data: List[Dict[str, Any]],
        period_type: PeriodType
    ) -> List[NormalizedIncomeStatement]:
        """
        FMP 손익계산서를 정규화
        """
        if not data:
            return []

        statements = []
        for item in data:
            try:
                fiscal_date = FMPProcessor._safe_date(item.get("date"))
                if not fiscal_date:
                    continue

                normalized = NormalizedIncomeStatement(
                    symbol=symbol.upper(),
                    fiscal_date_ending=fiscal_date,
                    reported_currency=item.get("reportedCurrency", "USD"),
                    period_type=period_type,
                    fiscal_year=FMPProcessor._extract_year(item.get("calendarYear")),

                    total_revenue=FMPProcessor._safe_decimal(item.get("revenue")),
                    cost_of_revenue=FMPProcessor._safe_decimal(item.get("costOfRevenue")),
                    gross_profit=FMPProcessor._safe_decimal(item.get("grossProfit")),
                    operating_expenses=FMPProcessor._safe_decimal(
                        item.get("operatingExpenses")
                    ),
                    operating_income=FMPProcessor._safe_decimal(
                        item.get("operatingIncome")
                    ),
                    interest_expense=FMPProcessor._safe_decimal(
                        item.get("interestExpense")
                    ),
                    income_before_tax=FMPProcessor._safe_decimal(
                        item.get("incomeBeforeTax")
                    ),
                    income_tax_expense=FMPProcessor._safe_decimal(
                        item.get("incomeTaxExpense")
                    ),
                    net_income=FMPProcessor._safe_decimal(item.get("netIncome")),
                    ebitda=FMPProcessor._safe_decimal(item.get("ebitda")),
                    eps=FMPProcessor._safe_decimal(item.get("eps")),
                    eps_diluted=FMPProcessor._safe_decimal(item.get("epsdiluted")),
                    weighted_avg_shares=FMPProcessor._safe_int(
                        item.get("weightedAverageShsOut")
                    ),
                    weighted_avg_shares_diluted=FMPProcessor._safe_int(
                        item.get("weightedAverageShsOutDil")
                    ),
                )
                statements.append(normalized)

            except Exception as e:
                logger.warning(f"Error processing income statement for {symbol}: {e}")
                continue

        return statements

    @staticmethod
    def process_cash_flow(
        symbol: str,
        data: List[Dict[str, Any]],
        period_type: PeriodType
    ) -> List[NormalizedCashFlow]:
        """
        FMP 현금흐름표를 정규화
        """
        if not data:
            return []

        cash_flows = []
        for item in data:
            try:
                fiscal_date = FMPProcessor._safe_date(item.get("date"))
                if not fiscal_date:
                    continue

                normalized = NormalizedCashFlow(
                    symbol=symbol.upper(),
                    fiscal_date_ending=fiscal_date,
                    reported_currency=item.get("reportedCurrency", "USD"),
                    period_type=period_type,
                    fiscal_year=FMPProcessor._extract_year(item.get("calendarYear")),

                    # 영업활동
                    operating_cash_flow=FMPProcessor._safe_decimal(
                        item.get("operatingCashFlow")
                    ),
                    net_income=FMPProcessor._safe_decimal(item.get("netIncome")),
                    depreciation=FMPProcessor._safe_decimal(
                        item.get("depreciationAndAmortization")
                    ),
                    changes_in_receivables=FMPProcessor._safe_decimal(
                        item.get("changeInReceivables")
                    ),
                    changes_in_inventory=FMPProcessor._safe_decimal(
                        item.get("changeInInventory")
                    ),

                    # 투자활동
                    investing_cash_flow=FMPProcessor._safe_decimal(
                        item.get("netCashUsedForInvestingActivites")
                    ),
                    capital_expenditures=FMPProcessor._safe_decimal(
                        item.get("capitalExpenditure")
                    ),
                    investments=FMPProcessor._safe_decimal(
                        item.get("investmentsInPropertyPlantAndEquipment")
                    ),

                    # 재무활동
                    financing_cash_flow=FMPProcessor._safe_decimal(
                        item.get("netCashUsedProvidedByFinancingActivities")
                    ),
                    dividends_paid=FMPProcessor._safe_decimal(
                        item.get("dividendsPaid")
                    ),
                    stock_repurchased=FMPProcessor._safe_decimal(
                        item.get("commonStockRepurchased")
                    ),
                    debt_repayment=FMPProcessor._safe_decimal(
                        item.get("debtRepayment")
                    ),

                    # 순 현금 변동
                    net_change_in_cash=FMPProcessor._safe_decimal(
                        item.get("netChangeInCash")
                    ),
                    free_cash_flow=FMPProcessor._safe_decimal(
                        item.get("freeCashFlow")
                    ),
                )
                cash_flows.append(normalized)

            except Exception as e:
                logger.warning(f"Error processing cash flow for {symbol}: {e}")
                continue

        return cash_flows

    @staticmethod
    def process_search_results(data: List[Dict[str, Any]]) -> List[NormalizedSearchResult]:
        """
        FMP 검색 결과를 정규화

        FMP 필드:
        - symbol -> symbol
        - name -> name
        - stockExchange / exchangeShortName -> exchange
        - currency -> currency
        """
        if not data:
            return []

        results = []
        for item in data:
            try:
                normalized = NormalizedSearchResult(
                    symbol=item.get("symbol", ""),
                    name=item.get("name", ""),
                    type=item.get("type"),
                    exchange=item.get("stockExchange") or item.get("exchangeShortName"),
                    currency=item.get("currency"),
                    match_score=None,  # FMP는 match score 미제공
                )
                results.append(normalized)
            except Exception as e:
                logger.warning(f"Error processing search result: {e}")
                continue

        return results

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
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        """안전한 int 변환"""
        if value is None or value == "" or value == "None":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_date(value) -> Optional[date]:
        """안전한 date 변환"""
        if value is None or value == "" or value == "None":
            return None
        try:
            # FMP는 YYYY-MM-DD 형식 사용
            if isinstance(value, date):
                return value
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(value).date()
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _extract_year(value) -> Optional[int]:
        """연도 추출"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
