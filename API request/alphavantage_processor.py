"""
Alpha vantage API 데이터를 데이터베이스로 보내기 위해 변환 프로세서
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
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
            "official_Site": overview_data.get("OfficialSite"),
            "fiscal_Year_End": overview_data.get("FiscalYearEnd"),
            "latest_Quarter": overview_data.get("LatestQuarter"),
            "market_Capitalization": Decimal(overview_data.get("MarketCapitalization", "0")),
            "ebitda": Decimal(overview_data.get("EBITDA", "0")),
            "pe_Ratio": Decimal(overview_data.get("PERatio", "0")),
            "peg_Ratio": Decimal(overview_data.get("PEGRatio", "0")),
            "book_Value": Decimal(overview_data.get("BookValue", "0")),
            "dividend_Per_Share": Decimal(overview_data.get("DividendPerShare", "0")),
            "dividend_Yield": Decimal(overview_data.get("DividendYield", "0")),
            "eps": Decimal(overview_data.get("EPS", "0")),
            "revenue_Per_Share_Ttm": Decimal(overview_data.get("RevenuePerShareTTM", "0")),
            "profit_Margin": Decimal(overview_data.get("ProfitMargin", "0")),
            "operating_Margin_Ttm": Decimal(overview_data.get("OperatingMarginTTM", "0")),
            "return_On_Assets_Ttm": Decimal(overview_data.get("ReturnOnAssetsTTM", "0")),
            "return_On_Equity_Ttm": Decimal(overview_data.get("ReturnOnEquityTTM", "0")),
            "revenue_Ttm": Decimal(overview_data.get("RevenueTTM", "0")),
            "gross_Profit_Ttm": Decimal(overview_data.get("GrossProfitTTM", "0")),
            "diluted_Eps_Ttm": Decimal(overview_data.get("DilutedEPSTTM", "0")),
            "quarterly_Earnings_Growth_Yoy": Decimal(overview_data.get("QuarterlyEarningsGrowthYOY", "0")),
            "quarterly_Revenue_Growth_Yoy": Decimal(overview_data.get("QuarterlyRevenueGrowthYOY", "0")),
            "analyst_Target_Price": Decimal(overview_data.get("AnalystTargetPrice", "0")),
            "analyst_Rating_Strong_Buy": Decimal(overview_data.get("AnalystRatingStrongBuy", "0")),
            "analyst_Rating_Buy": Decimal(overview_data.get("AnalystRatingBuy", "0")),
            "analyst_Rating_Hold": Decimal(overview_data.get("AnalystRatingHold", "0")),
            "analyst_Rating_Sell": Decimal(overview_data.get("AnalystRatingSell", "0")),
            "analyst_Rating_Strong_Sell": Decimal(overview_data.get("AnalystRatingStrongSell", "0")),
            "trailing_Pe": Decimal(overview_data.get("TrailingPE", "0")),
            "forward_Pe": Decimal(overview_data.get("ForwardPE", "0")),
            "price_To_Sales_Ratio_Ttm": Decimal(overview_data.get("PriceToSalesRatioTTM", "0")),
            "price_To_Book_Ratio": Decimal(overview_data.get("PriceToBookRatio", "0")),
            "ev_To_Revenue": Decimal(overview_data.get("EVToRevenue", "0")),
            "ev_To_Ebitda": Decimal(overview_data.get("EVToEBITDA", "0")),
            "beta": Decimal(overview_data.get("Beta", "0")),
            "52_Week_High": Decimal(overview_data.get("52WeekHigh", "0")),
            "52_Week_Low": Decimal(overview_data.get("52WeekLow", "0")),
            "50_Day_Moving_Average": Decimal(overview_data.get("50DayMovingAverage", "0")),
            "200_Day_Moving_Average": Decimal(overview_data.get("200DayMovingAverage", "0")),
            "shares_Outstanding": Decimal(overview_data.get("SharesOutstanding", "0")),
            "dividend_Date": overview_data.get("DividendDate"),
            "ex_Dividend_Date": overview_data.get("ExDividendDate"),
            "last_Updated": datetime.now(),
        }

        return stock_data
    
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
                    "cost_of_Goods_And_Services_Sold": Decimal(report.get("costofGoodsAndServicesSold", "0")),
                    "operating_Income": Decimal(report.get("operatingIncome", "0")),
                    "selling_General_And_Administrative": Decimal(report.get("sellingGeneralAndAdministrative", "0")),
                    "research_And_Development": Decimal(report.get("researchAndDevelopment", "0")),
                    "operating_Expenses": Decimal(report.get("operatingExpenses", "0")),
                    "investment_Income_Net": Decimal(report.get("investmentIncomeNet", "0")),
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