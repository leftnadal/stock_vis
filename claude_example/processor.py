"""
Process and transform Alpha Vantage API data for database storage.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import re

logger = logging.getLogger(__name__)

class AlphaVantageProcessor:
    """
    Process and transform Alpha Vantage API data for storage in database models.
    """
    
    @staticmethod
    def process_stock_quote(symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process real-time stock quote data.
        
        Args:
            symbol (str): Stock symbol
            data (Dict[str, Any]): Alpha Vantage quote data
            
        Returns:
            Dict[str, Any]: Processed stock data ready for database
        """
        # Extract data from the "Global Quote" section
        quote_data = data.get("Global Quote", {})
        
        if not quote_data:
            logger.warning(f"No quote data found for symbol {symbol}")
            return {}
        
        # Transform data for the Stock model
        stock_data = {
            "symbol": symbol,
            "open": Decimal(quote_data.get("02. open", "0")),
            "high": Decimal(quote_data.get("03. high", "0")),
            "low": Decimal(quote_data.get("04. low", "0")),
            "real_time_price": Decimal(quote_data.get("05. price", "0")),
            "volume": Decimal(quote_data.get("06. volume", "0")),
            "previous_close": Decimal(quote_data.get("08. previous close", "0")),
            "change": Decimal(quote_data.get("09. change", "0")),
            "change_percent": Decimal(quote_data.get("10. change percent", "0")),
            "last_updated": datetime.now()
        }
        
        return stock_data
    
    @staticmethod
    def process_company_overview(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process company overview data.
        
        Args:
            data (Dict[str, Any]): Alpha Vantage company overview data
            
        Returns:
            Dict[str, Any]: Processed company data for database
        """
        overview_data = data

        if not overview_data or "Symbol" not in overview_data:
            logger.warning("Invalid company overview data")
            return {}
        
        # Transform data for the Stock model
        stock_data = {
            "symbol": data.get("Symbol"),
            "asset_type": data.get("AssetType"),
            "stock_name": data.get("Name"),
            "description": data.get("Description"),
            "exchange": data.get("Exchange"),
            "currency": data.get("Currency"),
            "industry": data.get("Industry"),
            "sector": data.get("Sector"),
            "address": data.get("Address"),
            "official_site": data.get("OfficialSite"),
            "fiscal_year_end": data.get("FiscalYearEnd"),
            "latest_quarter": data.get("LatestQuarter"),
            "market_capitalization": Decimal(data.get("MarketCapitalization", "0")),
            "ebitda": Decimal(data.get("EBITDA", "0")),
            "per_ratio": Decimal(data.get("PERatio", "0")),
            "peg_ratio": Decimal(data.get("PEGRatio", "0")),
            "book_value": Decimal(data.get("BookValue", "0")),
            "dividend_per_share": Decimal(data.get("DividendPerShare", "0")),
            "dividend_yield": Decimal(data.get("DividendYield", "0")),
            "eps": Decimal(data.get("EPS", "0")),
            "revenue_per_share_ttm": Decimal(data.get("RevenuePerShareTTM", "0")),
            "profit_margin": Decimal(data.get("ProfitMargin", "0")),
            "operation_margin_ttm": Decimal(data.get("OperatingMarginTTM", "0")),
            "return_on_assets_ttm": Decimal(data.get("ReturnOnAssetsTTM", "0")),
            "return_on_equity_ttm": Decimal(data.get("ReturnOnEquityTTM", "0")),
            "revenue_ttm": Decimal(data.get("RevenueTTM", "0")),
            "gross_profit_ttm": Decimal(data.get("GrossProfitTTM", "0")),
            "diluted_eps_ttm": Decimal(data.get("DilutedEPSTTM", "0")),
            "quarterly_earnings_growth_yoy": Decimal(data.get("QuarterlyEarningsGrowthYOY", "0")),
            "quarterly_revenue_growth_yoy": Decimal(data.get("QuarterlyRevenueGrowthYOY", "0")),
            "analyst_target_price": Decimal(data.get("AnalystTargetPrice", "0")),
            "analyst_ratings_strong_buy": Decimal(data.get("AnalystRatingStrongBuy", "0")),
            "analyst_rating_buy": Decimal(data.get("AnalystRatingBuy", "0")),
            "analyst_rating_hold": Decimal(data.get("AnalystRatingHold", "0")),
            "analyst_rating_sell": Decimal(data.get("AnalystRatingSell", "0")),
            "analyst_rating_strong_sell": Decimal(data.get("AnalystRatingStrongSell", "0")),
            "trailing_pe": Decimal(data.get("TrailingPE", "0")),
            "forward_pe": Decimal(data.get("ForwardPE", "0")),
            "price_to_sales_ratio_ttm": Decimal(data.get("PriceToSalesRatioTTM", "0")),
            "price_to_book_ratio": Decimal(data.get("PriceToBookRatio", "0")),
            "ev_to_revenue": Decimal(data.get("EVToRevenue", "0")),
            "ev_to_ebitda": Decimal(data.get("EVToEBITDA", "0")),
            "beta": Decimal(data.get("Beta", "0")),
            "52_week_high": Decimal(data.get("52WeekHigh", "0")),
            "52_week_low": Decimal(data.get("52WeekLow", "0")),
            "50_day_moving_average": Decimal(data.get("50DayMovingAverage", "0")),
            "200_day_moving_average": Decimal(data.get("200DayMovingAverage", "0")),
            "shares_outstanding": Decimal(data.get("SharesOutstanding", "0")),
            "dividend_date": data.get("DividendDate"),
            "ex_dividend_date": data.get("ExDividendDate"),
           "last_updated": datetime.now()
        }
        
        return stock_data
    
    @staticmethod
    def process_historical_prices(symbol: str, time_series: Dict[str, Any], interval: str) -> List[Dict[str, Any]]:
        """
        Process historical daily price data.
        
        Args:
            symbol (str): Stock symbol
            time_series (Dict[str, Any]): Time series price data
            Interval (str): Data interval ('daily' or 'weekly')
            
        Returns:
            List[Dict[str, Any]]: List of processed price data for database
        """
        if not time_series:
            logger.warning(f"No {interval} price data found for symbol {symbol}")
            return []
        
        historical_prices = []
        
        # Process each date's price data
        for date_str, price_data in time_series.items():
            try:
                price_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                processed_data = {
                    "symbol": symbol,
                    "date": price_date,
                    "interval": interval,
                    "open_price": Decimal(price_data.get("1. open", "0")),
                    "high_price": Decimal(price_data.get("2. high", "0")),
                    "low_price": Decimal(price_data.get("3. low", "0")),
                    "close_price": Decimal(price_data.get("4. close", "0")),
                    "volume": int(price_data.get("5. volume", "0")),
                    "currency": "USD"
                }
                
                historical_prices.append(processed_data)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing {interval} price data for {date_str}: {e}")
                continue
        
        return historical_prices
    
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
                    "total_Assets": Decimal(report.get("totalAssets", "0")),
                    "total_Current_Assets": Decimal(report.get("totalCurrentAssets", "0")),
                    "cash_And_Cash_Equivalents_At_Carrying_Value": Decimal(report.get("cashAndCashEquivalentsAtCarryingValue", "0")),
                    "cash_And_Short_Term_Investments": Decimal(report.get("cashAndShortTermInvestments", "0")),
                    "inventory": Decimal(report.get("inventory", "0")),
                    "current_Net_Receivables": Decimal(report.get("currentNetReceivables", "0")),
                    "total_Non_Current_Assets": Decimal(report.get("totalNonCurrentAssets", "0")),
                    "property_Plant_Equipment": Decimal(report.get("propertyPlantEquipment", "0")),
                    "accumulated_Depreciation_Amortization_Ppe": Decimal(report.get("accumulatedDepreciationAmortizationPPE", "0")),
                    "intangible_Assets": Decimal(report.get("intangibleAssets", "0")),
                    "intangible_Assets_Excluding_Goodwill": Decimal(report.get("intangibleAssetsExcludingGoodwill", "0")),
                    "goodwill": Decimal(report.get("goodwill", "0")),
                    "investments": Decimal(report.get("investments", "0")),
                    "long_Term_Investments": Decimal(report.get("longTermInvestments", "0")),
                    "short_Term_Investments": Decimal(report.get("shortTermInvestments", "0")),
                    "other_Current_Assets": Decimal(report.get("otherCurrentAssets", "0")),
                    "other_Non_Current_Assets": Decimal(report.get("otherNonCurrentAssets", "0")),
                    "total_Liabilities": Decimal(report.get("totalLiabilities", "0")),
                    "total_Current_Liabilities": Decimal(report.get("totalCurrentLiabilities", "0")),
                    "current_Accounts_Payable": Decimal(report.get("currentAccountsPayable", "0")),
                    "deferred_Revenue": Decimal(report.get("deferredRevenue", "0")),
                    "current_Debt": Decimal(report.get("currentDebt", "0")),
                    "short_Term_Debt": Decimal(report.get("shortTermDebt", "0")),
                    "total_Non_Current_Liabilities": Decimal(report.get("totalNonCurrentLiabilities", "0")),
                    "capital_Lease_Obligations": Decimal(report.get("capitalLeaseObligations", "0")),
                    "long_Term_Debt": Decimal(report.get("longTermDebt", "0")),
                    "current_Longterm_Debt": Decimal(report.get("currentLongtermDebt", "0")),
                    "longterm_Debt_Noncurrent": Decimal(report.get("longtermDebtNoncurrent", "0")),
                    "short_LongTerm_Debt_Total": Decimal(report.get("shortLongTermDebtTotal", "0")),
                    "other_Current_Liabilities": Decimal(report.get("otherCurrentLiabilities", "0")),
                    "other_Non_Current_Liabilities": Decimal(report.get("otherNonCurrentLiabilities", "0")),
                    "total_Shareholder_Equity": Decimal(report.get("totalShareholderEquity", "0")),
                    "treasury_Stock": Decimal(report.get("treasuryStock", "0")),
                    "retained_Earnings": Decimal(report.get("retainedEarnings", "0")),
                    "common_Stock": Decimal(report.get("commonStock", "0")),
                    "common_Stock_Shares_Outstanding": Decimal(report.get("commonStockSharesOutstanding", "0")),
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
                    "total_Assets": Decimal(report.get("totalAssets", "0")),
                    "total_Current_Assets": Decimal(report.get("totalCurrentAssets", "0")),
                    "cash_And_Cash_Equivalents_At_Carrying_Value": Decimal(report.get("cashAndCashEquivalentsAtCarryingValue", "0")),
                    "cash_And_Short_Term_Investments": Decimal(report.get("cashAndShortTermInvestments", "0")),
                    "inventory": Decimal(report.get("inventory", "0")),
                    "current_Net_Receivables": Decimal(report.get("currentNetReceivables", "0")),
                    "total_Non_Current_Assets": Decimal(report.get("totalNonCurrentAssets", "0")),
                    "property_Plant_Equipment": Decimal(report.get("propertyPlantEquipment", "0")),
                    "accumulated_Depreciation_Amortization_Ppe": Decimal(report.get("accumulatedDepreciationAmortizationPPE", "0")),
                    "intangible_Assets": Decimal(report.get("intangibleAssets", "0")),
                    "intangible_Assets_Excluding_Goodwill": Decimal(report.get("intangibleAssetsExcludingGoodwill", "0")),
                    "goodwill": Decimal(report.get("goodwill", "0")),
                    "investments": Decimal(report.get("investments", "0")),
                    "long_Term_Investments": Decimal(report.get("longTermInvestments", "0")),
                    "short_Term_Investments": Decimal(report.get("shortTermInvestments", "0")),
                    "other_Current_Assets": Decimal(report.get("otherCurrentAssets", "0")),
                    "other_Non_Current_Assets": Decimal(report.get("otherNonCurrentAssets", "0")),
                    "total_Liabilities": Decimal(report.get("totalLiabilities", "0")),
                    "total_Current_Liabilities": Decimal(report.get("totalCurrentLiabilities", "0")),
                    "current_Accounts_Payable": Decimal(report.get("currentAccountsPayable", "0")),
                    "deferred_Revenue": Decimal(report.get("deferredRevenue", "0")),
                    "current_Debt": Decimal(report.get("currentDebt", "0")),
                    "short_Term_Debt": Decimal(report.get("shortTermDebt", "0")),
                    "total_Non_Current_Liabilities": Decimal(report.get("totalNonCurrentLiabilities", "0")),
                    "capital_Lease_Obligations": Decimal(report.get("capitalLeaseObligations", "0")),
                    "long_Term_Debt": Decimal(report.get("longTermDebt", "0")),
                    "current_Longterm_Debt": Decimal(report.get("currentLongtermDebt", "0")),
                    "longterm_Debt_Noncurrent": Decimal(report.get("longtermDebtNoncurrent", "0")),
                    "short_LongTerm_Debt_Total": Decimal(report.get("shortLongTermDebtTotal", "0")),
                    "other_Current_Liabilities": Decimal(report.get("otherCurrentLiabilities", "0")),
                    "other_Non_Current_Liabilities": Decimal(report.get("otherNonCurrentLiabilities", "0")),
                    "total_Shareholder_Equity": Decimal(report.get("totalShareholderEquity", "0")),
                    "treasury_Stock": Decimal(report.get("treasuryStock", "0")),
                    "retained_Earnings": Decimal(report.get("retainedEarnings", "0")),
                    "common_Stock": Decimal(report.get("commonStock", "0")),
                    "common_Stock_Shares_Outstanding": Decimal(report.get("commonStockSharesOutstanding", "0")),
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
                    "gross_Profit": Decimal(report.get("grossProfit", "0")),
                    "total_Revenue": Decimal(report.get("totalRevenue", "0")),
                    "cost_Of_Revenue": Decimal(report.get("costOfRevenue", "0")),
                    "cost_of_GoodsAndServicesSold": Decimal(report.get("costofGoodsAndServicesSold", "0")),
                    "operating_Income": Decimal(report.get("operatingIncome", "0")),
                    "selling_General_And_Administrative": Decimal(report.get("sellingGeneralAndAdministrative", "0")),
                    "research_And_Development": Decimal(report.get("researchAndDevelopment", "0")),
                    "operating_Expenses": Decimal(report.get("operatingExpenses", "0")),
                    "investment_IncomeNet": Decimal(report.get("investmentIncomeNet", "0")),
                    "net_Interest_Income": Decimal(report.get("netInterestIncome", "0")),
                    "interest_Income": Decimal(report.get("interestIncome", "0")),
                    "interest_Expense": Decimal(report.get("interestExpense", "0")),
                    "non_Interest_Income": Decimal(report.get("nonInterestIncome", "0")),
                    "other_Non_Operating_Income": Decimal(report.get("otherNonOperatingIncome", "0")),
                    "depreciation": Decimal(report.get("depreciation", "0")),
                    "depreciation_And_Amortization": Decimal(report.get("depreciationAndAmortization", "0")),
                    "income_Before_Tax": Decimal(report.get("incomeBeforeTax", "0")),
                    "income_Tax_Expense": Decimal(report.get("incomeTaxExpense", "0")),
                    "interest_And_Debt_Expense": Decimal(report.get("interestAndDebtExpense", "0")),
                    "net_Income_From_Continuing_Operations": Decimal(report.get("netIncomeFromContinuingOperations", "0")),
                    "comprehensive_Income_Net_Of_Tax": Decimal(report.get("comprehensiveIncomeNetOfTax", "0")),
                    "ebit": Decimal(report.get("ebit", "0")),
                    "ebitda": Decimal(report.get("ebitda", "0")),
                    "net_Income": Decimal(report.get("netIncome", "0")),
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
                    "gross_Profit": Decimal(report.get("grossProfit", "0")),
                    "total_Revenue": Decimal(report.get("totalRevenue", "0")),
                    "cost_Of_Revenue": Decimal(report.get("costOfRevenue", "0")),
                    "cost_of_GoodsAndServicesSold": Decimal(report.get("costofGoodsAndServicesSold", "0")),
                    "operating_Income": Decimal(report.get("operatingIncome", "0")),
                    "selling_General_And_Administrative": Decimal(report.get("sellingGeneralAndAdministrative", "0")),
                    "research_And_Development": Decimal(report.get("researchAndDevelopment", "0")),
                    "operating_Expenses": Decimal(report.get("operatingExpenses", "0")),
                    "investment_IncomeNet": Decimal(report.get("investmentIncomeNet", "0")),
                    "net_Interest_Income": Decimal(report.get("netInterestIncome", "0")),
                    "interest_Income": Decimal(report.get("interestIncome", "0")),
                    "interest_Expense": Decimal(report.get("interestExpense", "0")),
                    "non_Interest_Income": Decimal(report.get("nonInterestIncome", "0")),
                    "other_Non_Operating_Income": Decimal(report.get("otherNonOperatingIncome", "0")),
                    "depreciation": Decimal(report.get("depreciation", "0")),
                    "depreciation_And_Amortization": Decimal(report.get("depreciationAndAmortization", "0")),
                    "income_Before_Tax": Decimal(report.get("incomeBeforeTax", "0")),
                    "income_Tax_Expense": Decimal(report.get("incomeTaxExpense", "0")),
                    "interest_And_Debt_Expense": Decimal(report.get("interestAndDebtExpense", "0")),
                    "net_Income_From_Continuing_Operations": Decimal(report.get("netIncomeFromContinuingOperations", "0")),
                    "comprehensive_Income_Net_Of_Tax": Decimal(report.get("comprehensive_IncomeNetOfTax", "0")),
                    "ebit": Decimal(report.get("ebit", "0")),
                    "ebitda": Decimal(report.get("ebitda", "0")),
                    "net_Income": Decimal(report.get("netIncome", "0")),
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
                    "operating_Cashflow": Decimal(report.get("operatingCashflow", "0")),
                    "payments_For_Operating_Activities": Decimal(report.get("paymentsForOperatingActivities", "0")),
                    "proceeds_From_Operating_Activities": Decimal(report.get("proceedsFromOperatingActivities", "0")),
                    "change_In_Operating_Liabilities": Decimal(report.get("changeInOperatingLiabilities", "0")),
                    "change_In_Operating_Assets": Decimal(report.get("changeInOperatingAssets", "0")),
                    "depreciation_Depletion_And_Amortization": Decimal(report.get("depreciationDepletionAndAmortization", "0")),
                    "capital_Expenditures": Decimal(report.get("capitalExpenditures", "0")),
                    "change_In_Receivables": Decimal(report.get("changeInReceivables", "0")),
                    "change_In_Inventory": Decimal(report.get("changeInInventory", "0")),
                    "profit_Loss": Decimal(report.get("profitLoss", "0")),
                    "cashflow_From_Investment": Decimal(report.get("cashflowFromInvestment", "0")),
                    "cashflow_From_Financing": Decimal(report.get("cashflowFromFinancing", "0")),
                    "proceeds_From_Repayments_Of_Short_Term_Debt": Decimal(report.get("proceedsFromRepaymentsOfShortTermDebt", "0")),
                    "payments_For_Repurchase_Of_Common_Stock": Decimal(report.get("paymentsForRepurchaseOfCommonStock", "0")),
                    "payments_For_Repurchase_Of_Equity": Decimal(report.get("paymentsForRepurchaseOfEquity", "0")),
                    "payments_For_Repurchase_Of_Preferred_Stock": Decimal(report.get("paymentsForRepurchaseOfPreferredStock", "0")),
                    "dividend_Payout": Decimal(report.get("dividendPayout", "0")),
                    "dividend_Payout_Common_Stock": Decimal(report.get("dividendPayoutCommonStock", "0")),
                    "dividend_Payout_Preferred_Stock": Decimal(report.get("dividendPayoutPreferredStock", "0")),
                    "proceeds_From_Issuance_Of_Common_Stock": Decimal(report.get("proceedsFromIssuanceOfCommonStock", "0")),
                    "proceeds_From_Issuance_Of_Long_Term_Debt_And_Capital_Securities_Net": Decimal(report.get("proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet", "0")),
                    "proceeds_From_Issuance_Of_Preferred_Stock": Decimal(report.get("proceedsFromIssuanceOfPreferredStock", "0")),
                    "proceeds_From_Repurchase_Of_Equity": Decimal(report.get("proceedsFromRepurchaseOfEquity", "0")),
                    "proceeds_From_Sale_Of_Treasury_Stock": Decimal(report.get("proceedsFromSaleOfTreasuryStock", "0")),
                    "change_In_Cash_And_Cash_Equivalents": Decimal(report.get("changeInCashAndCashEquivalents", "0")),
                    "change_In_Exchange_Rate": Decimal(report.get("changeInExchangeRate", "0")),
                    "net_Income": Decimal(report.get("netIncome", "0")),
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
                    "operating_Cashflow": Decimal(report.get("operatingCashflow", "0")),
                    "payments_For_Operating_Activities": Decimal(report.get("paymentsForOperatingActivities", "0")),
                    "proceeds_From_Operating_Activities": Decimal(report.get("proceedsFromOperatingActivities", "0")),
                    "change_In_Operating_Liabilities": Decimal(report.get("changeInOperatingLiabilities", "0")),
                    "change_In_Operating_Assets": Decimal(report.get("changeInOperatingAssets", "0")),
                    "depreciation_Depletion_And_Amortization": Decimal(report.get("depreciationDepletionAndAmortization", "0")),
                    "capital_Expenditures": Decimal(report.get("capitalExpenditures", "0")),
                    "change_In_Receivables": Decimal(report.get("changeInReceivables", "0")),
                    "change_In_Inventory": Decimal(report.get("changeInInventory", "0")),
                    "profit_Loss": Decimal(report.get("profitLoss", "0")),
                    "cashflow_From_Investment": Decimal(report.get("cashflowFromInvestment", "0")),
                    "cashflow_From_Financing": Decimal(report.get("cashflowFromFinancing", "0")),
                    "proceeds_From_Repayments_Of_Short_Term_Debt": Decimal(report.get("proceedsFromRepaymentsOfShortTermDebt", "0")),
                    "payments_For_Repurchase_Of_Common_Stock": Decimal(report.get("paymentsForRepurchaseOfCommonStock", "0")),
                    "payments_For_Repurchase_Of_Equity": Decimal(report.get("paymentsForRepurchaseOfEquity", "0")),
                    "payments_For_Repurchase_Of_Preferred_Stock": Decimal(report.get("paymentsForRepurchaseOfPreferredStock", "0")),
                    "dividend_Payout": Decimal(report.get("dividendPayout", "0")),
                    "dividend_Payout_Common_Stock": Decimal(report.get("dividendPayoutCommonStock", "0")),
                    "dividend_Payout_Preferred_Stock": Decimal(report.get("dividendPayoutPreferredStock", "0")),
                    "proceeds_From_Issuance_Of_Common_Stock": Decimal(report.get("proceedsFromIssuanceOfCommonStock", "0")),
                    "proceeds_From_Issuance_Of_Long_Term_Debt_And_Capital_Securities_Net": Decimal(report.get("proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet", "0")),
                    "proceeds_From_Issuance_Of_Preferred_Stock": Decimal(report.get("proceedsFromIssuanceOfPreferredStock", "0")),
                    "proceeds_From_Repurchase_Of_Equity": Decimal(report.get("proceedsFromRepurchaseOfEquity", "0")),
                    "proceeds_From_Sale_Of_Treasury_Stock": Decimal(report.get("proceedsFromSaleOfTreasuryStock", "0")),
                    "change_In_Cash_And_Cash_Equivalents": Decimal(report.get("changeInCashAndCashEquivalents", "0")),
                    "change_In_Exchange_Rate": Decimal(report.get("changeInExchangeRate", "0")),
                    "net_Income": Decimal(report.get("netIncome", "0")),
                }
                
                reports.append(cash_flow_data)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing cash flow data: {e}")
                continue
        
        return reports