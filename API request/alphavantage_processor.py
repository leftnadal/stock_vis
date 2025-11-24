"""
Alpha vantage API 데이터를 데이터베이스로 보내기 위해 변환 프로세서
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

logger = logging.getLogger(__name__)

class AlphaVantageProcessor:
    """
    Alpha vantage API 데이터를 데이터베이스로 보내기 위해 변환 프로세서
    """
    @staticmethod
    def process_stock_quote(symbol: str, data: Dict[str, Any])-> Dict[str, Any]:
        """
        실시간 주식 가격을 변환
        """
        #global quote data
        quote_data = data.get("Global Quote", {})

        if not quote_data:
            logger.warning(f"No quote found for symbol {symbol}")
            return {}
        
        # Transform data for the stock model
        stock_data = {
            "symbol": symbol,
            "open_price": _safe_decimal(quote_data.get("02. open", "0")),
            "high_price": _safe_decimal(quote_data.get("03. high", "0")),
            "low_price": _safe_decimal(quote_data.get("04. low", "0")),
            "real_time_price": _safe_decimal(quote_data.get("05. price", "0")),
            "volume": int(quote_data.get("06. volume", "0")),
            "previous_close": _safe_decimal(quote_data.get("08. previous close", "0")),
            "change": _safe_decimal(quote_data.get("09. change", "0")),
            "change_percent": quote_data.get("10. change percent", "0"),
            "last_updated": datetime.now()
        }

        return stock_data

    @staticmethod
    def process_company_overview(data:Dict[str, Any])-> Dict[str, Any]:
        """
        회사 기본정보에 대한 database process(심볼, 주식 이름, 거래소, 화폐, 섹터, overview, 마지막 업데이트일

        Args:
            data (Dict[str, Any]): Alpha Vantage company overview data
            
        Returns:
            Dict[str, Any]: Processed company data for database
        """
        overview_data = data

        if not overview_data or "Symbol" not in data:
            logger.warning("Invalid company overviews data")
            return {}
        
        # Transform data for the stock model
        stock_data = {
            "symbol": overview_data.get("Symbol"),
            "asset_type": overview_data.get("AssetType"),
            "stock_name": overview_data.get("Name"),
            "description": overview_data.get("Description"),
            "exchange": overview_data.get("Exchange"),
            "currency": overview_data.get("Currency"),
            "industry": overview_data.get("Industry"),
            "sector": overview_data.get("Sector"),
            "address": overview_data.get("Address"),
            "official_site": overview_data.get("OfficialSite"),
            "fiscal_year_end": overview_data.get("FiscalYearEnd"),
            "latest_quarter": _safe_date(overview_data.get("LatestQuarter")),
            "market_capitalization": Decimal(overview_data.get("MarketCapitalization", "0")),
            #재무 데이터
            "ebitda": _safe_decimal(overview_data.get("EBITDA", "0")),
            "pe_ratio": _safe_decimal(overview_data.get("PERatio", "0")),
            "peg_ratio": _safe_decimal(overview_data.get("PEGRatio", "0")),
            "book_value": _safe_decimal(overview_data.get("BookValue", "0")),
            "dividend_per_share": _safe_decimal(overview_data.get("DividendPerShare", "0")),
            "dividend_yield": _safe_decimal(overview_data.get("DividendYield", "0")),
            "eps": _safe_decimal(overview_data.get("EPS", "0")),
            "revenue_per_share_ttm": _safe_decimal(overview_data.get("RevenuePerShareTTM", "0")),
            "profit_margin": _safe_decimal(overview_data.get("ProfitMargin", "0")),
            "operating_margin_ttm": _safe_decimal(overview_data.get("OperatingMarginTTM", "0")),
            "return_on_assets_ttm": _safe_decimal(overview_data.get("ReturnOnAssetsTTM", "0")),
            "return_on_equity_ttm": _safe_decimal(overview_data.get("ReturnOnEquityTTM", "0")),
            "revenue_ttm": _safe_decimal(overview_data.get("RevenueTTM", "0")),
            "gross_profit_ttm": _safe_decimal(overview_data.get("GrossProfitTTM", "0")),
            "diluted_eps_ttm": _safe_decimal(overview_data.get("DilutedEPSTTM", "0")),
            "quarterly_earnings_growth_yoy": _safe_decimal(overview_data.get("QuarterlyEarningsGrowthYOY", "0")),
            "quarterly_revenue_growth_yoy": _safe_decimal(overview_data.get("QuarterlyRevenueGrowthYOY", "0")),

            # 분석정보
            "analyst_target_price": _safe_decimal(overview_data.get("AnalystTargetPrice", "0")),
            "analyst_rating_strong_buy": _safe_decimal(overview_data.get("AnalystRatingStrongBuy", "0")),
            "analyst_rating_buy": _safe_decimal(overview_data.get("AnalystRatingBuy", "0")),
            "analyst_rating_hold": _safe_decimal(overview_data.get("AnalystRatingHold", "0")),
            "analyst_rating_sell": _safe_decimal(overview_data.get("AnalystRatingSell", "0")),
            "analyst_rating_strong_sell": _safe_decimal(overview_data.get("AnalystRatingStrongSell", "0")),

            # 기술적 지표
            "trailing_pe": _safe_decimal(overview_data.get("TrailingPE", "0")),
            "forward_pe": _safe_decimal(overview_data.get("ForwardPE", "0")),
            "price_to_sales_ratio_ttm": _safe_decimal(overview_data.get("PriceToSalesRatioTTM", "0")),
            "price_to_book_ratio": _safe_decimal(overview_data.get("PriceToBookRatio", "0")),
            "ev_to_revenue": _safe_decimal(overview_data.get("EVToRevenue", "0")),
            "ev_to_ebitda": _safe_decimal(overview_data.get("EVToEBITDA", "0")),
            "beta": _safe_decimal(overview_data.get("Beta", "0")),
            "week_52_high": _safe_decimal(overview_data.get("52WeekHigh", "0")),
            "week_52_low": _safe_decimal(overview_data.get("52WeekLow", "0")),
            "day_50_moving_average": _safe_decimal(overview_data.get("50DayMovingAverage", "0")),
            "day_200_moving_average": _safe_decimal(overview_data.get("200DayMovingAverage", "0")),
            "shares_outstanding": _safe_decimal(overview_data.get("SharesOutstanding", "0")),

            # 배당정보
            "dividend_date": _safe_date(overview_data.get("DividendDate")),
            "ex_dividend_date": _safe_date(overview_data.get("ExDividendDate")),
            "last_updated": datetime.now(),
        }

        return stock_data
    
    @staticmethod
    def process_historical_prices(symbol: str, time_series: Dict[str, Any], data_type: str) -> List[Dict[str, Any]]:
        """
        과거 가격 데이터 처리 (일간/주간 공통)
        - Alpha Vantage API에서 받은 시계열 데이터를 DB 모델에 맞게 변환
        """
        if not time_series:
            logger.warning(f"No time series data for {symbol}")
            return []
        
        processed_data = []

        for date_str, price_data in time_series.items():
            try:
                #날짜 파싱
                price_date = datetime.strptime(date_str,"%Y-%m-%d").date()

                # 가격데이터 변환
                price_entry = {
                    "stock_symbol": symbol,
                    "currency": "USD",  # 기본값
                    "date": price_date,
                    "open_price": _safe_decimal(price_data.get("1. open", "0")),
                    "high_price": _safe_decimal(price_data.get("2. high", "0")),
                    "low_price": _safe_decimal(price_data.get("3. low", "0")),
                    "close_price": _safe_decimal(price_data.get("4. close", "0")),
                    "volume": _safe_int(price_data.get("5. volume", "0")),
                }

                # 주간 데이터의 경우 추가 필드
                if data_type == "weekly":
                    # 실제로는 주의 시작일과 종료일을 계산해야 하지만
                    # 간단히 해당 날짜를 사용 (추후 개선 가능)
                    price_entry.update({
                        "week_start_date": price_date,
                        "week_end_date": price_date,
                        "average_volume": _safe_int(price_data.get("5. volume", "0")),
                    })
                
                processed_data.append(price_entry)

            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Error processing price data for {symbol} on {date_str}: {e}")
                continue

        return processed_data

    @staticmethod
    def process_daily_historical_prices(symbol: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process daily historical prices
        
        Args:
            symbol (str): Stock symbol
            data (Dict[str, Any]): Alpha Vantage historical price data
            
        Returns:
            List[Dict[str, Any]]: List of processed price data for database
        """
        time_series = data.get("Time Series (Daily)", {})
        return AlphaVantageProcessor.process_historical_prices(symbol, time_series, "daily")
    
    @staticmethod
    def process_weekly_historical_prices(symbol: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process weekly historical prices
        
        Args:
            symbol (str): Stock symbol
            data (Dict[str, Any]): Alpha Vantage historical price data
            
        Returns:
            List[Dict[str, Any]]: List of processed price data for database
        """
        time_series = data.get("Weekly Time Series", {})
        return AlphaVantageProcessor.process_historical_prices(symbol, time_series, "weekly")

    
    @staticmethod
    def process_balance_sheet(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process balance sheet data from Alpha Vantage.
        
        Args:
            data (Dict[str, Any]): Alpha Vantage balance sheet data
            
        Returns:
            List[Dict[str, Any]]: List of processed balance sheet data for database
        """
        if not data or "symbol" not in data or "annualReports" not in data:
            logger.warning("Invalid balance sheet data")
            return []
        
        symbol = data.get("symbol")
        reports = []
        
        # Process annual reports
        for report in data.get("annualReports", []):
            try:
                fiscal_date = datetime.strptime(report.get("fiscalDateEnding", ""), "%Y-%m-%d").date()
                
                # 대문자와 언더스코어가 섞인 필드명에 맞게 조정
                balance_sheet_data = {
                    "stock_symbol": symbol,
                    "reported_date": fiscal_date,
                    "period_type": "annual",
                    "fiscal_year": fiscal_date.year,
                    "currency": "USD",  # Default currency assumption
                    "total_assets": _safe_decimal(report.get("totalAssets", "0")),
                    "total_current_assets": _safe_decimal(report.get("totalCurrentAssets", "0")),
                    "cash_and_cash_equivalents_at_carrying_value": _safe_decimal(report.get("cashAndCashEquivalentsAtCarryingValue", "0")),
                    "cash_and_short_term_investments": _safe_decimal(report.get("cashAndShortTermInvestments", "0")),
                    "inventory": _safe_decimal(report.get("inventory", "0")),
                    "current_net_receivables": _safe_decimal(report.get("currentNetReceivables", "0")),
                    "total_non_current_assets": _safe_decimal(report.get("totalNonCurrentAssets", "0")),
                    "property_plant_equipment": _safe_decimal(report.get("propertyPlantEquipment", "0")),
                    "accumulated_depreciation_amortization_ppe": _safe_decimal(report.get("accumulatedDepreciationAmortizationPPE", "0")),
                    "intangible_assets": _safe_decimal(report.get("intangibleAssets", "0")),
                    "intangible_assets_excluding_goodwill": _safe_decimal(report.get("intangibleAssetsExcludingGoodwill", "0")),
                    "goodwill": _safe_decimal(report.get("goodwill", "0")),
                    "investments": _safe_decimal(report.get("investments", "0")),
                    "long_term_investments": _safe_decimal(report.get("longTermInvestments", "0")),
                    "short_term_investments": _safe_decimal(report.get("shortTermInvestments", "0")),
                    "other_current_assets": _safe_decimal(report.get("otherCurrentAssets", "0")),
                    "other_non_current_assets": _safe_decimal(report.get("otherNonCurrentAssets", "0")),
                    "total_liabilities": _safe_decimal(report.get("totalLiabilities", "0")),
                    "total_current_liabilities": _safe_decimal(report.get("totalCurrentLiabilities", "0")),
                    "current_accounts_payable": _safe_decimal(report.get("currentAccountsPayable", "0")),
                    "deferred_revenue": _safe_decimal(report.get("deferredRevenue", "0")),
                    "current_debt": _safe_decimal(report.get("currentDebt", "0")),
                    "short_term_debt": _safe_decimal(report.get("shortTermDebt", "0")),
                    "total_non_current_liabilities": _safe_decimal(report.get("totalNonCurrentLiabilities", "0")),
                    "capital_lease_obligations": _safe_decimal(report.get("capitalLeaseObligations", "0")),
                    "long_term_debt": _safe_decimal(report.get("longTermDebt", "0")),
                    "current_longterm_debt": _safe_decimal(report.get("currentLongtermDebt", "0")),
                    "longterm_debt_noncurrent": _safe_decimal(report.get("longtermDebtNoncurrent", "0")),
                    "short_longterm_debt_total": _safe_decimal(report.get("shortLongTermDebtTotal", "0")),
                    "other_current_liabilities": _safe_decimal(report.get("otherCurrentLiabilities", "0")),
                    "other_non_current_liabilities": _safe_decimal(report.get("otherNonCurrentLiabilities", "0")),
                    "total_shareholder_equity": _safe_decimal(report.get("totalShareholderEquity", "0")),
                    "treasury_stock": _safe_decimal(report.get("treasuryStock", "0")),
                    "retained_earnings": _safe_decimal(report.get("retainedEarnings", "0")),
                    "common_stock": _safe_decimal(report.get("commonStock", "0")),
                    "common_stock_shares_outstanding": _safe_decimal(report.get("commonStockSharesOutstanding", "0")),
                }
                
                reports.append(balance_sheet_data)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing balance sheet data: {e}")
                continue
        
        # Process quarterly reports if available
        for report in data.get("quarterlyReports", []):
            try:
                fiscal_date = datetime.strptime(report.get("fiscalDateEnding", ""), "%Y-%m-%d").date()
                
                balance_sheet_data = {
                    "stock_symbol": symbol,
                    "reported_date": fiscal_date,
                    "period_type": "quarter",
                    "fiscal_year": fiscal_date.year,
                    "fiscal_quarter": (fiscal_date.month - 1) // 3 + 1,  # Estimate quarter from month
                    "currency": "USD",  # Default currency assumption
                    "total_assets": _safe_decimal(report.get("totalAssets", "0")),
                    "total_current_assets": _safe_decimal(report.get("totalCurrentAssets", "0")),
                    "cash_and_cash_equivalents_at_carrying_value": _safe_decimal(report.get("cashAndCashEquivalentsAtCarryingValue", "0")),
                    "cash_and_short_term_investments": _safe_decimal(report.get("cashAndShortTermInvestments", "0")),
                    "inventory": _safe_decimal(report.get("inventory", "0")),
                    "current_net_receivables": _safe_decimal(report.get("currentNetReceivables", "0")),
                    "total_non_current_assets": _safe_decimal(report.get("totalNonCurrentAssets", "0")),
                    "property_plant_equipment": _safe_decimal(report.get("propertyPlantEquipment", "0")),
                    "accumulated_depreciation_amortization_ppe": _safe_decimal(report.get("accumulatedDepreciationAmortizationPPE", "0")),
                    "intangible_assets": _safe_decimal(report.get("intangibleAssets", "0")),
                    "intangible_assets_excluding_goodwill": _safe_decimal(report.get("intangibleAssetsExcludingGoodwill", "0")),
                    "goodwill": _safe_decimal(report.get("goodwill", "0")),
                    "investments": _safe_decimal(report.get("investments", "0")),
                    "long_term_investments": _safe_decimal(report.get("longTermInvestments", "0")),
                    "short_term_investments": _safe_decimal(report.get("shortTermInvestments", "0")),
                    "other_current_assets": _safe_decimal(report.get("otherCurrentAssets", "0")),
                    "other_non_current_assets": _safe_decimal(report.get("otherNonCurrentAssets", "0")),
                    "total_liabilities": _safe_decimal(report.get("totalLiabilities", "0")),
                    "total_current_liabilities": _safe_decimal(report.get("totalCurrentLiabilities", "0")),
                    "current_accounts_payable": _safe_decimal(report.get("currentAccountsPayable", "0")),
                    "deferred_revenue": _safe_decimal(report.get("deferredRevenue", "0")),
                    "current_debt": _safe_decimal(report.get("currentDebt", "0")),
                    "short_term_debt": _safe_decimal(report.get("shortTermDebt", "0")),
                    "total_non_current_liabilities": _safe_decimal(report.get("totalNonCurrentLiabilities", "0")),
                    "capital_lease_obligations": _safe_decimal(report.get("capitalLeaseObligations", "0")),
                    "long_term_debt": _safe_decimal(report.get("longTermDebt", "0")),
                    "current_longterm_debt": _safe_decimal(report.get("currentLongtermDebt", "0")),
                    "longterm_debt_noncurrent": _safe_decimal(report.get("longtermDebtNoncurrent", "0")),
                    "short_longterm_debt_total": _safe_decimal(report.get("shortLongTermDebtTotal", "0")),
                    "other_current_liabilities": _safe_decimal(report.get("otherCurrentLiabilities", "0")),
                    "other_non_current_liabilities": _safe_decimal(report.get("otherNonCurrentLiabilities", "0")),
                    "total_shareholder_equity": _safe_decimal(report.get("totalShareholderEquity", "0")),
                    "treasury_stock": _safe_decimal(report.get("treasuryStock", "0")),
                    "retained_earnings": _safe_decimal(report.get("retainedEarnings", "0")),
                    "common_stock": _safe_decimal(report.get("commonStock", "0")),
                    "common_stock_shares_outstanding": _safe_decimal(report.get("commonStockSharesOutstanding", "0")),
                }
                
                reports.append(balance_sheet_data)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing balance sheet data: {e}")
                continue
        
        return reports
    
    @staticmethod
    def process_income_statement(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process income statement data from Alpha Vantage.
        
        Args:
            data (Dict[str, Any]): Alpha Vantage income statement data
            
        Returns:
            List[Dict[str, Any]]: List of processed income statement data for database
        """
        if not data or "symbol" not in data or "annualReports" not in data:
            logger.warning("Invalid income statement data")
            return []
        
        symbol = data.get("symbol")
        reports = []
        
        # Process annual reports
        for report in data.get("annualReports", []):
            try:
                fiscal_date = datetime.strptime(report.get("fiscalDateEnding", ""), "%Y-%m-%d").date()
                
                income_data = {
                    "stock_symbol": symbol,
                    "reported_date": fiscal_date,
                    "period_type": "annual",
                    "fiscal_year": fiscal_date.year,
                    "currency": "USD",  # Default currency assumption
                    "gross_profit": _safe_decimal(report.get("grossProfit", "0")),
                    "total_revenue": _safe_decimal(report.get("totalRevenue", "0")),
                    "cost_of_revenue": _safe_decimal(report.get("costOfRevenue", "0")),
                    "cost_of_goods_and_services_sold": _safe_decimal(report.get("costofGoodsAndServicesSold", "0")),
                    "operating_income": _safe_decimal(report.get("operatingIncome", "0")),
                    "selling_general_and_administrative": _safe_decimal(report.get("sellingGeneralAndAdministrative", "0")),
                    "research_and_development": _safe_decimal(report.get("researchAndDevelopment", "0")),
                    "operating_expenses": _safe_decimal(report.get("operatingExpenses", "0")),
                    "investment_income_net": _safe_decimal(report.get("investmentIncomeNet", "0")),
                    "net_interest_income": _safe_decimal(report.get("netInterestIncome", "0")),
                    "interest_income": _safe_decimal(report.get("interestIncome", "0")),
                    "interest_expense": _safe_decimal(report.get("interestExpense", "0")),
                    "non_interest_income": _safe_decimal(report.get("nonInterestIncome", "0")),
                    "other_non_operating_income": _safe_decimal(report.get("otherNonOperatingIncome", "0")),
                    "depreciation": _safe_decimal(report.get("depreciation", "0")),
                    "depreciation_and_amortization": _safe_decimal(report.get("depreciationAndAmortization", "0")),
                    "income_before_tax": _safe_decimal(report.get("incomeBeforeTax", "0")),
                    "income_tax_expense": _safe_decimal(report.get("incomeTaxExpense", "0")),
                    "interest_and_debt_expense": _safe_decimal(report.get("interestAndDebtExpense", "0")),
                    "net_income_from_continuing_operations": _safe_decimal(report.get("netIncomeFromContinuingOperations", "0")),
                    "comprehensive_income_net_of_tax": _safe_decimal(report.get("comprehensiveIncomeNetOfTax", "0")),
                    "ebit": _safe_decimal(report.get("ebit", "0")),
                    "ebitda": _safe_decimal(report.get("ebitda", "0")),
                    "net_income": _safe_decimal(report.get("netIncome", "0")),
            }               
                reports.append(income_data)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing income statement data: {e}")
                continue
        
        # Process quarterly reports if available
        for report in data.get("quarterlyReports", []):
            try:
                fiscal_date = datetime.strptime(report.get("fiscalDateEnding", ""), "%Y-%m-%d").date()
                
                income_data = {
                    "stock_symbol": symbol,
                    "reported_date": fiscal_date,
                    "period_type": "quarter",
                    "fiscal_year": fiscal_date.year,
                    "fiscal_quarter": (fiscal_date.month - 1) // 3 + 1,  # Estimate quarter from month
                    "currency": "USD",  # Default currency assumption
                    "gross_profit": _safe_decimal(report.get("grossProfit", "0")),
                    "total_revenue": _safe_decimal(report.get("totalRevenue", "0")),
                    "cost_of_revenue": _safe_decimal(report.get("costOfRevenue", "0")),
                    "cost_of_goods_and_services_sold": _safe_decimal(report.get("costofGoodsAndServicesSold", "0")),
                    "operating_income": _safe_decimal(report.get("operatingIncome", "0")),
                    "selling_general_and_administrative": _safe_decimal(report.get("sellingGeneralAndAdministrative", "0")),
                    "research_and_development": _safe_decimal(report.get("researchAndDevelopment", "0")),
                    "operating_expenses": _safe_decimal(report.get("operatingExpenses", "0")),
                    "investment_income_net": _safe_decimal(report.get("investmentIncomeNet", "0")),
                    "net_interest_income": _safe_decimal(report.get("netInterestIncome", "0")),
                    "interest_income": _safe_decimal(report.get("interestIncome", "0")),
                    "interest_expense": _safe_decimal(report.get("interestExpense", "0")),
                    "non_interest_income": _safe_decimal(report.get("nonInterestIncome", "0")),
                    "other_non_operating_income": _safe_decimal(report.get("otherNonOperatingIncome", "0")),
                    "depreciation": _safe_decimal(report.get("depreciation", "0")),
                    "depreciation_and_amortization": _safe_decimal(report.get("depreciationAndAmortization", "0")),
                    "income_before_tax": _safe_decimal(report.get("incomeBeforeTax", "0")),
                    "income_tax_expense": _safe_decimal(report.get("incomeTaxExpense", "0")),
                    "interest_and_debt_expense": _safe_decimal(report.get("interestAndDebtExpense", "0")),
                    "net_income_from_continuing_operations": _safe_decimal(report.get("netIncomeFromContinuingOperations", "0")),
                    "comprehensive_income_net_of_tax": _safe_decimal(report.get("comprehensive_IncomeNetOfTax", "0")),
                    "ebit": _safe_decimal(report.get("ebit", "0")),
                    "ebitda": _safe_decimal(report.get("ebitda", "0")),
                    "net_income": _safe_decimal(report.get("netIncome", "0")),
                }
                
                reports.append(income_data)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing income statement data: {e}")
                continue
        
        return reports
    
    @staticmethod
    def process_cash_flow(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process cash flow data from Alpha Vantage.
        
        Args:
            data (Dict[str, Any]): Alpha Vantage cash flow data
            
        Returns:
            List[Dict[str, Any]]: List of processed cash flow data for database
        """
        if not data or "symbol" not in data or "annualReports" not in data:
            logger.warning("Invalid cash flow data")
            return []
        
        symbol = data.get("symbol")
        reports = []
        
        # Process annual reports
        for report in data.get("annualReports", []):
            try:
                fiscal_date = datetime.strptime(report.get("fiscalDateEnding", ""), "%Y-%m-%d").date()
                
                cash_flow_data = {
                    "stock_symbol": symbol,
                    "reported_date": fiscal_date,
                    "period_type": "annual",
                    "fiscal_year": fiscal_date.year,
                    "currency": "USD",  # Default currency assumption
                    "operating_cashflow": _safe_decimal(report.get("operatingCashflow", "0")),
                    "payments_for_operating_activities": _safe_decimal(report.get("paymentsForOperatingActivities", "0")),
                    "proceeds_from_operating_activities": _safe_decimal(report.get("proceedsFromOperatingActivities", "0")),
                    "change_in_operating_liabilities": _safe_decimal(report.get("changeInOperatingLiabilities", "0")),
                    "change_in_operating_assets": _safe_decimal(report.get("changeInOperatingAssets", "0")),
                    "depreciation_depletion_and_amortization": _safe_decimal(report.get("depreciationDepletionAndAmortization", "0")),
                    "capital_expenditures": _safe_decimal(report.get("capitalExpenditures", "0")),
                    "change_in_receivables": _safe_decimal(report.get("changeInReceivables", "0")),
                    "change_in_inventory": _safe_decimal(report.get("changeInInventory", "0")),
                    "profit_loss": _safe_decimal(report.get("profitLoss", "0")),
                    "cashflow_from_investment": _safe_decimal(report.get("cashflowFromInvestment", "0")),
                    "cashflow_from_financing": _safe_decimal(report.get("cashflowFromFinancing", "0")),
                    "proceeds_from_repayments_of_short_term_debt": _safe_decimal(report.get("proceedsFromRepaymentsOfShortTermDebt", "0")),
                    "payments_for_repurchase_of_common_stock": _safe_decimal(report.get("paymentsForRepurchaseOfCommonStock", "0")),
                    "payments_for_repurchase_of_equity": _safe_decimal(report.get("paymentsForRepurchaseOfEquity", "0")),
                    "payments_for_repurchase_of_preferred_stock": _safe_decimal(report.get("paymentsForRepurchaseOfPreferredStock", "0")),
                    "dividend_payout": _safe_decimal(report.get("dividendPayout", "0")),
                    "dividend_payout_common_stock": _safe_decimal(report.get("dividendPayoutCommonStock", "0")),
                    "dividend_payout_preferred_stock": _safe_decimal(report.get("dividendPayoutPreferredStock", "0")),
                    "proceeds_from_issuance_of_common_stock": _safe_decimal(report.get("proceedsFromIssuanceOfCommonStock", "0")),
                    "proceeds_from_issuance_of_long_term_debt_and_capital_securities_net": _safe_decimal(report.get("proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet", "0")),
                    "proceeds_from_issuance_of_preferred_stock": _safe_decimal(report.get("proceedsFromIssuanceOfPreferredStock", "0")),
                    "proceeds_from_repurchase_of_equity": _safe_decimal(report.get("proceedsFromRepurchaseOfEquity", "0")),
                    "proceeds_from_sale_of_treasury_stock": _safe_decimal(report.get("proceedsFromSaleOfTreasuryStock", "0")),
                    "change_in_cash_and_cash_equivalents": _safe_decimal(report.get("changeInCashAndCashEquivalents", "0")),
                    "change_in_exchange_rate": _safe_decimal(report.get("changeInExchangeRate", "0")),
                    "net_income": _safe_decimal(report.get("netIncome", "0")),
            }
                
                reports.append(cash_flow_data)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing cash flow data: {e}")
                continue
        
        # Process quarterly reports if available
        for report in data.get("quarterlyReports", []):
            try:
                fiscal_date = datetime.strptime(report.get("fiscalDateEnding", ""), "%Y-%m-%d").date()
                
                cash_flow_data = {
                    "stock_symbol": symbol,
                    "reported_date": fiscal_date,
                    "period_type": "quarter",
                    "fiscal_year": fiscal_date.year,
                    "fiscal_quarter": (fiscal_date.month - 1) // 3 + 1,  # Estimate quarter from month
                    "currency": "USD",  # Default currency assumption
                    "operating_cashflow": _safe_decimal(report.get("operatingCashflow", "0")),
                    "payments_for_operating_activities": _safe_decimal(report.get("paymentsForOperatingActivities", "0")),
                    "proceeds_from_operating_activities": _safe_decimal(report.get("proceedsFromOperatingActivities", "0")),
                    "change_in_operating_liabilities": _safe_decimal(report.get("changeInOperatingLiabilities", "0")),
                    "change_in_operating_assets": _safe_decimal(report.get("changeInOperatingAssets", "0")),
                    "depreciation_depletion_and_amortization": _safe_decimal(report.get("depreciationDepletionAndAmortization", "0")),
                    "capital_expenditures": _safe_decimal(report.get("capitalExpenditures", "0")),
                    "change_in_receivables": _safe_decimal(report.get("changeInReceivables", "0")),
                    "change_in_inventory": _safe_decimal(report.get("changeInInventory", "0")),
                    "profit_loss": _safe_decimal(report.get("profitLoss", "0")),
                    "cashflow_from_investment": _safe_decimal(report.get("cashflowFromInvestment", "0")),
                    "cashflow_from_financing": _safe_decimal(report.get("cashflowFromFinancing", "0")),
                    "proceeds_from_repayments_of_short_term_debt": _safe_decimal(report.get("proceedsFromRepaymentsOfShortTermDebt", "0")),
                    "payments_for_repurchase_of_common_stock": _safe_decimal(report.get("paymentsForRepurchaseOfCommonStock", "0")),
                    "payments_for_repurchase_of_equity": _safe_decimal(report.get("paymentsForRepurchaseOfEquity", "0")),
                    "payments_for_repurchase_of_preferred_stock": _safe_decimal(report.get("paymentsForRepurchaseOfPreferredStock", "0")),
                    "dividend_payout": _safe_decimal(report.get("dividendPayout", "0")),
                    "dividend_payout_common_stock": _safe_decimal(report.get("dividendPayoutCommonStock", "0")),
                    "dividend_payout_preferred_stock": _safe_decimal(report.get("dividendPayoutPreferredStock", "0")),
                    "proceeds_from_issuance_of_common_stock": _safe_decimal(report.get("proceedsFromIssuanceOfCommonStock", "0")),
                    "proceeds_from_issuance_of_long_term_debt_and_capital_securities_net": _safe_decimal(report.get("proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet", "0")),
                    "proceeds_from_issuance_of_preferred_stock": _safe_decimal(report.get("proceedsFromIssuanceOfPreferredStock", "0")),
                    "proceeds_from_repurchase_of_equity": _safe_decimal(report.get("proceedsFromRepurchaseOfEquity", "0")),
                    "proceeds_from_sale_of_treasury_stock": _safe_decimal(report.get("proceedsFromSaleOfTreasuryStock", "0")),
                    "change_in_cash_and_cash_equivalents": _safe_decimal(report.get("changeInCashAndCashEquivalents", "0")),
                    "change_in_exchange_rate": _safe_decimal(report.get("changeInExchangeRate", "0")),
                    "net_income": _safe_decimal(report.get("netIncome", "0")),
                }
                
                reports.append(cash_flow_data)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing cash flow data: {e}")
                continue
        
        return reports
    
def _safe_decimal(value: Any) -> Decimal:
    """
    ## 안전한 Decimal 변환
    # - None이나 'None', '-', 빈 문자열 등 처리
    # - 잘못된 형식의 문자열도 안전하게 처리
    """
    if not value or value in ['None', '-', '', 'N/A']:
        return Decimal('0')
    
    try:
        # 문자열에서 %나 쉼표 제거
        if isinstance(value, str):
            # %나 $, 쉼표 제거
            cleaned_value = re.sub(r'[,%$]', '', str(value)).strip()
            if not cleaned_value:
                return Decimal('0')
            return Decimal(cleaned_value)
        else:
            return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation) as e:
        logger.warning(f"Error converting to Decimal: {value}, error: {e}")
        return Decimal('0')


def _safe_int(value: Any) -> int:
    """
    ## 안전한 int 변환
    # - BigIntegerField나 IntegerField를 위한 안전한 변환
    """
    if not value or value in ['None', '-', '', 'N/A']:
        return 0
    
    try:
        # 문자열에서 쉼표나 소수점 처리
        if isinstance(value, str):
            cleaned_value = re.sub(r'[,]', '', str(value)).strip()
            if not cleaned_value:
                return 0
            # 소수점이 있으면 float으로 먼저 변환 후 int
            return int(float(cleaned_value))
        else:
            return int(float(str(value)))
    except (ValueError, TypeError) as e:
        logger.warning(f"Error converting to int: {value}, error: {e}")
        return 0


def _safe_date(value: Any) -> Optional[datetime]:
    """
    ## 안전한 날짜 변환
    # - 다양한 날짜 형식 처리
    """
    if not value or value in ['None', '-', '', 'N/A']:
        return None
    
    try:
        if isinstance(value, str):
            # 일반적인 날짜 형식들 시도
            date_formats = [
                "%Y-%m-%d",
                "%m/%d/%Y", 
                "%d/%m/%Y",
                "%Y.%m.%d",
                "%Y%m%d"
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue
            
            # 모든 형식이 실패하면 None 반환
            logger.warning(f"Could not parse date: {value}")
            return None
    except Exception as e:
        logger.warning(f"Error converting to date: {value}, error: {e}")
        return None