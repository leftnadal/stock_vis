"""
Financial Statements Fallback Service

재무제표 데이터를 다중 소스에서 가져오는 fallback 체인:
1. FMP API (Primary)
2. Alpha Vantage API (Secondary)
3. yfinance (Tertiary)

모든 소스의 데이터를 통일된 형식으로 변환합니다.
"""
import logging
import math
from typing import List, Dict, Any, Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)


class FinancialStatementsFallbackService:
    """재무제표 다중 소스 fallback 서비스"""

    CACHE_TTL = 600  # 10분

    def __init__(self):
        self._fmp_service = None
        self._av_client = None
        self._yf = None

    @property
    def fmp_service(self):
        """FMP 서비스 lazy loading"""
        if self._fmp_service is None:
            try:
                from .fmp_fundamentals import FMPFundamentalsService
                self._fmp_service = FMPFundamentalsService()
            except Exception as e:
                logger.warning(f"FMP service init failed: {e}")
        return self._fmp_service

    @property
    def av_client(self):
        """Alpha Vantage client lazy loading"""
        if self._av_client is None:
            try:
                from api_request.alphavantage_client import AlphaVantageClient
                self._av_client = AlphaVantageClient()
            except Exception as e:
                logger.warning(f"Alpha Vantage client init failed: {e}")
        return self._av_client

    @property
    def yf(self):
        """yfinance lazy loading"""
        if self._yf is None:
            try:
                import yfinance
                self._yf = yfinance
            except ImportError:
                logger.warning("yfinance not installed")
        return self._yf

    # ==================== Balance Sheet ====================

    def get_balance_sheet(self, symbol: str, period: str = 'annual', limit: int = 5) -> tuple[List[Dict], str]:
        """
        대차대조표 조회 (fallback chain)

        Returns:
            tuple: (data_list, source_name)
        """
        symbol = symbol.upper()

        # 1. FMP API 시도
        data = self._try_fmp_balance_sheet(symbol, period, limit)
        if data:
            return data, 'fmp'

        # 2. Alpha Vantage 시도
        data = self._try_av_balance_sheet(symbol, period, limit)
        if data:
            return data, 'alphavantage'

        # 3. yfinance 시도
        data = self._try_yf_balance_sheet(symbol, period, limit)
        if data:
            return data, 'yfinance'

        return [], 'empty'

    def _try_fmp_balance_sheet(self, symbol: str, period: str, limit: int) -> List[Dict]:
        """FMP에서 대차대조표 조회"""
        if not self.fmp_service:
            return []
        try:
            fmp_period = 'quarter' if period == 'quarterly' else 'annual'
            data = self.fmp_service.get_balance_sheet(symbol, fmp_period, limit)
            if data:
                return self._transform_fmp_balance_sheet(data)
        except Exception as e:
            logger.debug(f"FMP balance sheet failed for {symbol}: {e}")
        return []

    def _try_av_balance_sheet(self, symbol: str, period: str, limit: int) -> List[Dict]:
        """Alpha Vantage에서 대차대조표 조회"""
        if not self.av_client:
            return []
        try:
            response = self.av_client.get_balance_sheet(symbol)
            key = 'quarterlyReports' if period == 'quarterly' else 'annualReports'
            data = response.get(key, [])[:limit]
            if data:
                return self._transform_av_balance_sheet(data, period)
        except Exception as e:
            logger.debug(f"Alpha Vantage balance sheet failed for {symbol}: {e}")
        return []

    def _try_yf_balance_sheet(self, symbol: str, period: str, limit: int) -> List[Dict]:
        """yfinance에서 대차대조표 조회"""
        if not self.yf:
            return []
        try:
            ticker = self.yf.Ticker(symbol)
            if period == 'quarterly':
                df = ticker.quarterly_balance_sheet
            else:
                df = ticker.balance_sheet

            if df is not None and not df.empty:
                return self._transform_yf_balance_sheet(df, period, limit)
        except Exception as e:
            logger.debug(f"yfinance balance sheet failed for {symbol}: {e}")
        return []

    # ==================== Income Statement ====================

    def get_income_statement(self, symbol: str, period: str = 'annual', limit: int = 5) -> tuple[List[Dict], str]:
        """손익계산서 조회 (fallback chain)"""
        symbol = symbol.upper()

        # 1. FMP API 시도
        data = self._try_fmp_income_statement(symbol, period, limit)
        if data:
            return data, 'fmp'

        # 2. Alpha Vantage 시도
        data = self._try_av_income_statement(symbol, period, limit)
        if data:
            return data, 'alphavantage'

        # 3. yfinance 시도
        data = self._try_yf_income_statement(symbol, period, limit)
        if data:
            return data, 'yfinance'

        return [], 'empty'

    def _try_fmp_income_statement(self, symbol: str, period: str, limit: int) -> List[Dict]:
        """FMP에서 손익계산서 조회"""
        if not self.fmp_service:
            return []
        try:
            fmp_period = 'quarter' if period == 'quarterly' else 'annual'
            data = self.fmp_service.get_income_statement(symbol, fmp_period, limit)
            if data:
                return self._transform_fmp_income_statement(data)
        except Exception as e:
            logger.debug(f"FMP income statement failed for {symbol}: {e}")
        return []

    def _try_av_income_statement(self, symbol: str, period: str, limit: int) -> List[Dict]:
        """Alpha Vantage에서 손익계산서 조회"""
        if not self.av_client:
            return []
        try:
            response = self.av_client.get_income_statement(symbol)
            key = 'quarterlyReports' if period == 'quarterly' else 'annualReports'
            data = response.get(key, [])[:limit]
            if data:
                return self._transform_av_income_statement(data, period)
        except Exception as e:
            logger.debug(f"Alpha Vantage income statement failed for {symbol}: {e}")
        return []

    def _try_yf_income_statement(self, symbol: str, period: str, limit: int) -> List[Dict]:
        """yfinance에서 손익계산서 조회"""
        if not self.yf:
            return []
        try:
            ticker = self.yf.Ticker(symbol)
            if period == 'quarterly':
                df = ticker.quarterly_income_stmt
            else:
                df = ticker.income_stmt

            if df is not None and not df.empty:
                return self._transform_yf_income_statement(df, period, limit)
        except Exception as e:
            logger.debug(f"yfinance income statement failed for {symbol}: {e}")
        return []

    # ==================== Cash Flow Statement ====================

    def get_cash_flow(self, symbol: str, period: str = 'annual', limit: int = 5) -> tuple[List[Dict], str]:
        """현금흐름표 조회 (fallback chain)"""
        symbol = symbol.upper()

        # 1. FMP API 시도
        data = self._try_fmp_cash_flow(symbol, period, limit)
        if data:
            return data, 'fmp'

        # 2. Alpha Vantage 시도
        data = self._try_av_cash_flow(symbol, period, limit)
        if data:
            return data, 'alphavantage'

        # 3. yfinance 시도
        data = self._try_yf_cash_flow(symbol, period, limit)
        if data:
            return data, 'yfinance'

        return [], 'empty'

    def _try_fmp_cash_flow(self, symbol: str, period: str, limit: int) -> List[Dict]:
        """FMP에서 현금흐름표 조회"""
        if not self.fmp_service:
            return []
        try:
            fmp_period = 'quarter' if period == 'quarterly' else 'annual'
            data = self.fmp_service.get_cash_flow_statement(symbol, fmp_period, limit)
            if data:
                return self._transform_fmp_cash_flow(data)
        except Exception as e:
            logger.debug(f"FMP cash flow failed for {symbol}: {e}")
        return []

    def _try_av_cash_flow(self, symbol: str, period: str, limit: int) -> List[Dict]:
        """Alpha Vantage에서 현금흐름표 조회"""
        if not self.av_client:
            return []
        try:
            response = self.av_client.get_cash_flow(symbol)
            key = 'quarterlyReports' if period == 'quarterly' else 'annualReports'
            data = response.get(key, [])[:limit]
            if data:
                return self._transform_av_cash_flow(data, period)
        except Exception as e:
            logger.debug(f"Alpha Vantage cash flow failed for {symbol}: {e}")
        return []

    def _try_yf_cash_flow(self, symbol: str, period: str, limit: int) -> List[Dict]:
        """yfinance에서 현금흐름표 조회"""
        if not self.yf:
            return []
        try:
            ticker = self.yf.Ticker(symbol)
            if period == 'quarterly':
                df = ticker.quarterly_cashflow
            else:
                df = ticker.cashflow

            if df is not None and not df.empty:
                return self._transform_yf_cash_flow(df, period, limit)
        except Exception as e:
            logger.debug(f"yfinance cash flow failed for {symbol}: {e}")
        return []

    # ==================== Data Transformers ====================

    def _safe_float(self, value) -> Optional[float]:
        """안전한 float 변환 (NaN/Inf 값 처리 포함)"""
        if value is None or value == 'None' or value == '':
            return None
        try:
            result = float(value)
            # NaN/Inf 값은 JSON 직렬화가 불가능하므로 None으로 반환
            if math.isnan(result) or math.isinf(result):
                return None
            return result
        except (ValueError, TypeError):
            return None

    def _extract_year_quarter(self, date_str: str, period: str) -> tuple:
        """날짜에서 연도와 분기 추출"""
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
            year = dt.year
            quarter = (dt.month - 1) // 3 + 1 if period == 'quarterly' else None
            return year, quarter
        except:
            return None, None

    # --- FMP Transformers ---

    def _transform_fmp_balance_sheet(self, data: List[Dict]) -> List[Dict]:
        """FMP 대차대조표 변환"""
        result = []
        for item in data:
            year, quarter = self._extract_year_quarter(
                item.get('date', ''),
                'quarter' if item.get('period', '').startswith('Q') else 'annual'
            )
            result.append({
                'fiscal_date_ending': item.get('date'),
                'fiscal_year': year,
                'fiscal_quarter': quarter,
                'period_type': 'quarter' if item.get('period', '').startswith('Q') else 'annual',
                'currency': item.get('reportedCurrency', 'USD'),
                'total_assets': self._safe_float(item.get('totalAssets')),
                'total_current_assets': self._safe_float(item.get('totalCurrentAssets')),
                'cash_and_cash_equivalents': self._safe_float(item.get('cashAndCashEquivalents')),
                'short_term_investments': self._safe_float(item.get('shortTermInvestments')),
                'net_receivables': self._safe_float(item.get('netReceivables')),
                'inventory': self._safe_float(item.get('inventory')),
                'total_non_current_assets': self._safe_float(item.get('totalNonCurrentAssets')),
                'property_plant_equipment': self._safe_float(item.get('propertyPlantEquipmentNet')),
                'goodwill': self._safe_float(item.get('goodwill')),
                'intangible_assets': self._safe_float(item.get('intangibleAssets')),
                'long_term_investments': self._safe_float(item.get('longTermInvestments')),
                'total_liabilities': self._safe_float(item.get('totalLiabilities')),
                'total_current_liabilities': self._safe_float(item.get('totalCurrentLiabilities')),
                'short_term_debt': self._safe_float(item.get('shortTermDebt')),
                'accounts_payable': self._safe_float(item.get('accountPayables')),
                'total_non_current_liabilities': self._safe_float(item.get('totalNonCurrentLiabilities')),
                'long_term_debt': self._safe_float(item.get('longTermDebt')),
                'total_shareholder_equity': self._safe_float(item.get('totalStockholdersEquity')),
                'retained_earnings': self._safe_float(item.get('retainedEarnings')),
                'common_stock': self._safe_float(item.get('commonStock')),
                '_source': 'fmp'
            })
        return result

    def _transform_fmp_income_statement(self, data: List[Dict]) -> List[Dict]:
        """FMP 손익계산서 변환"""
        result = []
        for item in data:
            year, quarter = self._extract_year_quarter(
                item.get('date', ''),
                'quarter' if item.get('period', '').startswith('Q') else 'annual'
            )
            result.append({
                'fiscal_date_ending': item.get('date'),
                'fiscal_year': year,
                'fiscal_quarter': quarter,
                'period_type': 'quarter' if item.get('period', '').startswith('Q') else 'annual',
                'currency': item.get('reportedCurrency', 'USD'),
                'total_revenue': self._safe_float(item.get('revenue')),
                'cost_of_revenue': self._safe_float(item.get('costOfRevenue')),
                'gross_profit': self._safe_float(item.get('grossProfit')),
                'operating_expenses': self._safe_float(item.get('operatingExpenses')),
                'research_and_development': self._safe_float(item.get('researchAndDevelopmentExpenses')),
                'selling_general_administrative': self._safe_float(item.get('sellingGeneralAndAdministrativeExpenses')),
                'operating_income': self._safe_float(item.get('operatingIncome')),
                'interest_expense': self._safe_float(item.get('interestExpense')),
                'income_before_tax': self._safe_float(item.get('incomeBeforeTax')),
                'income_tax_expense': self._safe_float(item.get('incomeTaxExpense')),
                'net_income': self._safe_float(item.get('netIncome')),
                'eps': self._safe_float(item.get('eps')),
                'eps_diluted': self._safe_float(item.get('epsdiluted')),
                'ebitda': self._safe_float(item.get('ebitda')),
                '_source': 'fmp'
            })
        return result

    def _transform_fmp_cash_flow(self, data: List[Dict]) -> List[Dict]:
        """FMP 현금흐름표 변환"""
        result = []
        for item in data:
            year, quarter = self._extract_year_quarter(
                item.get('date', ''),
                'quarter' if item.get('period', '').startswith('Q') else 'annual'
            )
            result.append({
                'fiscal_date_ending': item.get('date'),
                'fiscal_year': year,
                'fiscal_quarter': quarter,
                'period_type': 'quarter' if item.get('period', '').startswith('Q') else 'annual',
                'currency': item.get('reportedCurrency', 'USD'),
                'operating_cash_flow': self._safe_float(item.get('operatingCashFlow')),
                'net_income': self._safe_float(item.get('netIncome')),
                'depreciation_and_amortization': self._safe_float(item.get('depreciationAndAmortization')),
                'stock_based_compensation': self._safe_float(item.get('stockBasedCompensation')),
                'change_in_working_capital': self._safe_float(item.get('changeInWorkingCapital')),
                'investing_cash_flow': self._safe_float(item.get('netCashUsedForInvestingActivites')),
                'capital_expenditure': self._safe_float(item.get('capitalExpenditure')),
                'financing_cash_flow': self._safe_float(item.get('netCashUsedProvidedByFinancingActivities')),
                'dividends_paid': self._safe_float(item.get('dividendsPaid')),
                'net_change_in_cash': self._safe_float(item.get('netChangeInCash')),
                'free_cash_flow': self._safe_float(item.get('freeCashFlow')),
                '_source': 'fmp'
            })
        return result

    # --- Alpha Vantage Transformers ---

    def _transform_av_balance_sheet(self, data: List[Dict], period: str) -> List[Dict]:
        """Alpha Vantage 대차대조표 변환"""
        result = []
        for item in data:
            year, quarter = self._extract_year_quarter(item.get('fiscalDateEnding', ''), period)
            result.append({
                'fiscal_date_ending': item.get('fiscalDateEnding'),
                'fiscal_year': year,
                'fiscal_quarter': quarter,
                'period_type': 'quarter' if period == 'quarterly' else 'annual',
                'currency': item.get('reportedCurrency', 'USD'),
                'total_assets': self._safe_float(item.get('totalAssets')),
                'total_current_assets': self._safe_float(item.get('totalCurrentAssets')),
                'cash_and_cash_equivalents': self._safe_float(item.get('cashAndCashEquivalentsAtCarryingValue')),
                'short_term_investments': self._safe_float(item.get('shortTermInvestments')),
                'net_receivables': self._safe_float(item.get('currentNetReceivables')),
                'inventory': self._safe_float(item.get('inventory')),
                'total_non_current_assets': self._safe_float(item.get('totalNonCurrentAssets')),
                'property_plant_equipment': self._safe_float(item.get('propertyPlantEquipment')),
                'goodwill': self._safe_float(item.get('goodwill')),
                'intangible_assets': self._safe_float(item.get('intangibleAssets')),
                'long_term_investments': self._safe_float(item.get('longTermInvestments')),
                'total_liabilities': self._safe_float(item.get('totalLiabilities')),
                'total_current_liabilities': self._safe_float(item.get('totalCurrentLiabilities')),
                'short_term_debt': self._safe_float(item.get('shortTermDebt')),
                'accounts_payable': self._safe_float(item.get('currentAccountsPayable')),
                'total_non_current_liabilities': self._safe_float(item.get('totalNonCurrentLiabilities')),
                'long_term_debt': self._safe_float(item.get('longTermDebt')),
                'total_shareholder_equity': self._safe_float(item.get('totalShareholderEquity')),
                'retained_earnings': self._safe_float(item.get('retainedEarnings')),
                'common_stock': self._safe_float(item.get('commonStock')),
                '_source': 'alphavantage'
            })
        return result

    def _transform_av_income_statement(self, data: List[Dict], period: str) -> List[Dict]:
        """Alpha Vantage 손익계산서 변환"""
        result = []
        for item in data:
            year, quarter = self._extract_year_quarter(item.get('fiscalDateEnding', ''), period)
            result.append({
                'fiscal_date_ending': item.get('fiscalDateEnding'),
                'fiscal_year': year,
                'fiscal_quarter': quarter,
                'period_type': 'quarter' if period == 'quarterly' else 'annual',
                'currency': item.get('reportedCurrency', 'USD'),
                'total_revenue': self._safe_float(item.get('totalRevenue')),
                'cost_of_revenue': self._safe_float(item.get('costOfRevenue')),
                'gross_profit': self._safe_float(item.get('grossProfit')),
                'operating_expenses': self._safe_float(item.get('operatingExpenses')),
                'research_and_development': self._safe_float(item.get('researchAndDevelopment')),
                'selling_general_administrative': self._safe_float(item.get('sellingGeneralAndAdministrative')),
                'operating_income': self._safe_float(item.get('operatingIncome')),
                'interest_expense': self._safe_float(item.get('interestExpense')),
                'income_before_tax': self._safe_float(item.get('incomeBeforeTax')),
                'income_tax_expense': self._safe_float(item.get('incomeTaxExpense')),
                'net_income': self._safe_float(item.get('netIncome')),
                'eps': self._safe_float(item.get('reportedEPS')),
                'eps_diluted': self._safe_float(item.get('reportedEPS')),  # AV doesn't separate
                'ebitda': self._safe_float(item.get('ebitda')),
                '_source': 'alphavantage'
            })
        return result

    def _transform_av_cash_flow(self, data: List[Dict], period: str) -> List[Dict]:
        """Alpha Vantage 현금흐름표 변환"""
        result = []
        for item in data:
            year, quarter = self._extract_year_quarter(item.get('fiscalDateEnding', ''), period)
            result.append({
                'fiscal_date_ending': item.get('fiscalDateEnding'),
                'fiscal_year': year,
                'fiscal_quarter': quarter,
                'period_type': 'quarter' if period == 'quarterly' else 'annual',
                'currency': item.get('reportedCurrency', 'USD'),
                'operating_cash_flow': self._safe_float(item.get('operatingCashflow')),
                'net_income': self._safe_float(item.get('netIncome')),
                'depreciation_and_amortization': self._safe_float(item.get('depreciationDepletionAndAmortization')),
                'stock_based_compensation': self._safe_float(item.get('stockBasedCompensation')),
                'change_in_working_capital': self._safe_float(item.get('changeInOperatingLiabilities')),
                'investing_cash_flow': self._safe_float(item.get('cashflowFromInvestment')),
                'capital_expenditure': self._safe_float(item.get('capitalExpenditures')),
                'financing_cash_flow': self._safe_float(item.get('cashflowFromFinancing')),
                'dividends_paid': self._safe_float(item.get('dividendPayout')),
                'net_change_in_cash': self._safe_float(item.get('changeInCashAndCashEquivalents')),
                'free_cash_flow': None,  # Calculate if needed
                '_source': 'alphavantage'
            })
        return result

    # --- yfinance Transformers ---

    def _transform_yf_balance_sheet(self, df, period: str, limit: int) -> List[Dict]:
        """yfinance 대차대조표 변환"""
        result = []
        columns = list(df.columns)[:limit]

        for col in columns:
            try:
                date_str = col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)[:10]
                year, quarter = self._extract_year_quarter(date_str, period)

                def get_val(keys):
                    for key in keys:
                        if key in df.index:
                            val = df.loc[key, col]
                            return self._safe_float(val)
                    return None

                result.append({
                    'fiscal_date_ending': date_str,
                    'fiscal_year': year,
                    'fiscal_quarter': quarter,
                    'period_type': 'quarter' if period == 'quarterly' else 'annual',
                    'currency': 'USD',
                    'total_assets': get_val(['Total Assets']),
                    'total_current_assets': get_val(['Current Assets', 'Total Current Assets']),
                    'cash_and_cash_equivalents': get_val(['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments']),
                    'short_term_investments': get_val(['Other Short Term Investments']),
                    'net_receivables': get_val(['Receivables', 'Net Receivables']),
                    'inventory': get_val(['Inventory']),
                    'total_non_current_assets': get_val(['Total Non Current Assets']),
                    'property_plant_equipment': get_val(['Net PPE', 'Property Plant And Equipment Net']),
                    'goodwill': get_val(['Goodwill']),
                    'intangible_assets': get_val(['Intangible Assets']),
                    'long_term_investments': get_val(['Long Term Investments', 'Investments And Advances']),
                    'total_liabilities': get_val(['Total Liabilities Net Minority Interest', 'Total Liabilities']),
                    'total_current_liabilities': get_val(['Current Liabilities', 'Total Current Liabilities']),
                    'short_term_debt': get_val(['Current Debt', 'Short Term Debt']),
                    'accounts_payable': get_val(['Accounts Payable', 'Payables']),
                    'total_non_current_liabilities': get_val(['Total Non Current Liabilities Net Minority Interest']),
                    'long_term_debt': get_val(['Long Term Debt']),
                    'total_shareholder_equity': get_val(['Total Equity Gross Minority Interest', 'Stockholders Equity']),
                    'retained_earnings': get_val(['Retained Earnings']),
                    'common_stock': get_val(['Common Stock', 'Common Stock Equity']),
                    '_source': 'yfinance'
                })
            except Exception as e:
                logger.debug(f"yfinance balance sheet column parse error: {e}")
                continue

        return result

    def _transform_yf_income_statement(self, df, period: str, limit: int) -> List[Dict]:
        """yfinance 손익계산서 변환"""
        result = []
        columns = list(df.columns)[:limit]

        for col in columns:
            try:
                date_str = col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)[:10]
                year, quarter = self._extract_year_quarter(date_str, period)

                def get_val(keys):
                    for key in keys:
                        if key in df.index:
                            val = df.loc[key, col]
                            return self._safe_float(val)
                    return None

                result.append({
                    'fiscal_date_ending': date_str,
                    'fiscal_year': year,
                    'fiscal_quarter': quarter,
                    'period_type': 'quarter' if period == 'quarterly' else 'annual',
                    'currency': 'USD',
                    'total_revenue': get_val(['Total Revenue', 'Operating Revenue']),
                    'cost_of_revenue': get_val(['Cost Of Revenue']),
                    'gross_profit': get_val(['Gross Profit']),
                    'operating_expenses': get_val(['Operating Expense', 'Total Operating Expenses']),
                    'research_and_development': get_val(['Research And Development']),
                    'selling_general_administrative': get_val(['Selling General And Administration']),
                    'operating_income': get_val(['Operating Income']),
                    'interest_expense': get_val(['Interest Expense']),
                    'income_before_tax': get_val(['Pretax Income']),
                    'income_tax_expense': get_val(['Tax Provision']),
                    'net_income': get_val(['Net Income', 'Net Income Common Stockholders']),
                    'eps': get_val(['Basic EPS']),
                    'eps_diluted': get_val(['Diluted EPS']),
                    'ebitda': get_val(['EBITDA']),
                    '_source': 'yfinance'
                })
            except Exception as e:
                logger.debug(f"yfinance income statement column parse error: {e}")
                continue

        return result

    def _transform_yf_cash_flow(self, df, period: str, limit: int) -> List[Dict]:
        """yfinance 현금흐름표 변환"""
        result = []
        columns = list(df.columns)[:limit]

        for col in columns:
            try:
                date_str = col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)[:10]
                year, quarter = self._extract_year_quarter(date_str, period)

                def get_val(keys):
                    for key in keys:
                        if key in df.index:
                            val = df.loc[key, col]
                            return self._safe_float(val)
                    return None

                result.append({
                    'fiscal_date_ending': date_str,
                    'fiscal_year': year,
                    'fiscal_quarter': quarter,
                    'period_type': 'quarter' if period == 'quarterly' else 'annual',
                    'currency': 'USD',
                    'operating_cash_flow': get_val(['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities']),
                    'net_income': get_val(['Net Income']),
                    'depreciation_and_amortization': get_val(['Depreciation And Amortization']),
                    'stock_based_compensation': get_val(['Stock Based Compensation']),
                    'change_in_working_capital': get_val(['Change In Working Capital']),
                    'investing_cash_flow': get_val(['Investing Cash Flow', 'Cash Flow From Continuing Investing Activities']),
                    'capital_expenditure': get_val(['Capital Expenditure']),
                    'financing_cash_flow': get_val(['Financing Cash Flow', 'Cash Flow From Continuing Financing Activities']),
                    'dividends_paid': get_val(['Common Stock Dividend Paid', 'Cash Dividends Paid']),
                    'net_change_in_cash': get_val(['Changes In Cash', 'Change In Cash Supplemental As Reported']),
                    'free_cash_flow': get_val(['Free Cash Flow']),
                    '_source': 'yfinance'
                })
            except Exception as e:
                logger.debug(f"yfinance cash flow column parse error: {e}")
                continue

        return result
