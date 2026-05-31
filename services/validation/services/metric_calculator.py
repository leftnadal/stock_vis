"""
Task 2: 33개 지표 계산 + value_status 판정 + CompanyMetricLatest 갱신

기존 재무제표(IncomeStatement, BalanceSheet, CashFlowStatement)에서 읽어
CompanyMetricSnapshot에 (symbol, fiscal_year, metric_code) 단위로 저장.
rev_growth_vs_industry는 Task 3.5에서 별도 계산.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.utils import timezone

from packages.shared.metrics.models import CompanyMetricSnapshot
from packages.shared.stocks.models import SP500Constituent, Stock
from services.validation.models import CompanyMetricLatest
from services.validation.services.financial_fetcher import FinancialFetcher

logger = logging.getLogger(__name__)


def _safe(val) -> Optional[float]:
    """DB 필드 값을 안전하게 float로 변환"""
    if val is None:
        return None
    try:
        f = float(val)
        return f if f != 0 or val == 0 else None  # 실제 0과 None 구분
    except (ValueError, TypeError, InvalidOperation):
        return None


def _safe_nonzero(val) -> Optional[float]:
    """분모용: None이거나 0이면 None 반환"""
    f = _safe(val)
    if f is None or f == 0:
        return None
    return f


def _div(numerator, denominator) -> Optional[float]:
    """안전한 나눗셈. 분자/분모 중 하나라도 None이면 None."""
    n = _safe(numerator)
    d = _safe_nonzero(denominator)
    if n is None or d is None:
        return None
    return n / d


class MetricCalculator:
    """33개 지표 계산 엔진"""

    def __init__(self):
        self.fetcher = FinancialFetcher()

    def calculate_for_symbol(self, symbol: str) -> dict:
        """
        단일 종목의 전체 연도에 대해 33개 지표 계산.
        Returns: {'symbol': str, 'metrics_saved': int, 'latest_updated': int, 'errors': list}
        """
        symbol = symbol.upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return {"symbol": symbol, "metrics_saved": 0, "error": "Stock not found"}

        financials = self.fetcher.get_financial_data(symbol, years=5)
        if not financials:
            return {"symbol": symbol, "metrics_saved": 0, "error": "No financial data"}

        fiscal_years = sorted(financials.keys(), reverse=True)
        metrics_saved = 0
        errors = []

        for fy in fiscal_years:
            data = financials[fy]
            inc = data["income"]
            bal = data["balance"]
            cf = data["cashflow"]

            # 이전 연도 데이터 (YoY 계산용)
            prev_data = financials.get(fy - 1)
            prev_inc = prev_data["income"] if prev_data else None
            prev_bal = prev_data["balance"] if prev_data else None
            prev_cf = prev_data["cashflow"] if prev_data else None

            # 3년 전 데이터 (희석률/CAGR용)
            data_3y = financials.get(fy - 3)
            prev_bal_3y = data_3y["balance"] if data_3y else None

            calculated = self._calculate_all_metrics(
                inc, bal, cf, prev_inc, prev_bal, prev_cf, prev_bal_3y, stock
            )

            for metric_code, (
                value,
                value_status,
                exclusion_reason,
            ) in calculated.items():
                try:
                    dec_val = (
                        Decimal(str(round(value, 6))) if value is not None else None
                    )
                    CompanyMetricSnapshot.objects.update_or_create(
                        symbol=stock,
                        fiscal_year=fy,
                        metric_code_id=metric_code,
                        defaults={
                            "metric_value": dec_val,
                            "value_status": value_status,
                            "exclusion_reason": exclusion_reason,
                            "source_detail": {
                                "calculated_at": timezone.now().isoformat()
                            },
                        },
                    )
                    metrics_saved += 1
                except Exception as e:
                    errors.append(f"{metric_code}@{fy}: {e}")

        # CompanyMetricLatest 갱신 (최신 연도 기준)
        latest_fy = fiscal_years[0] if fiscal_years else None
        latest_updated = 0
        if latest_fy:
            latest_updated = self._update_latest(stock, latest_fy)

        return {
            "symbol": symbol,
            "fiscal_years": fiscal_years,
            "metrics_saved": metrics_saved,
            "latest_updated": latest_updated,
            "errors": errors[:10],
        }

    def calculate_for_symbols(self, symbols: list[str] = None) -> dict:
        """배치 계산. symbols=None이면 S&P 500 전체."""
        if symbols is None:
            symbols = list(
                SP500Constituent.objects.filter(is_active=True).values_list(
                    "symbol", flat=True
                )
            )

        total = len(symbols)
        success = 0
        fail = 0
        error_details = []

        for i, symbol in enumerate(symbols):
            try:
                result = self.calculate_for_symbol(symbol)
                if result.get("error"):
                    fail += 1
                    error_details.append({"symbol": symbol, "error": result["error"]})
                else:
                    success += 1
            except Exception as e:
                fail += 1
                error_details.append({"symbol": symbol, "error": str(e)})
                logger.error(f"[{i + 1}/{total}] calc failed {symbol}: {e}")

            if (i + 1) % 50 == 0:
                logger.info(
                    f"Calc progress: {i + 1}/{total} (success={success}, errors={fail})"
                )

        return {
            "total": total,
            "success": success,
            "errors": fail,
            "error_details": error_details[:20],
        }

    def _calculate_all_metrics(
        self, inc, bal, cf, prev_inc, prev_bal, prev_cf, prev_bal_3y, stock
    ):
        """
        33개 지표 계산. rev_growth_vs_industry는 제외 (Task 3.5).
        Returns: {metric_code: (value, value_status, exclusion_reason)}
        """
        results = {}

        # ── profitability (5) ──
        results["gross_margin"] = self._calc_ratio(inc.gross_profit, inc.total_revenue)
        results["operating_margin"] = self._calc_ratio(
            inc.operating_income, inc.total_revenue
        )
        results["net_margin"] = self._calc_ratio(inc.net_income, inc.total_revenue)
        results["roe"] = self._calc_ratio(inc.net_income, bal.total_shareholder_equity)
        results["roic"] = self._calc_roic(inc, bal)

        # ── growth (3, rev_growth_vs_industry 제외) ──
        results["revenue_growth_yoy"] = self._calc_growth(
            _safe(inc.total_revenue),
            _safe(prev_inc.total_revenue) if prev_inc else None,
        )
        results["operating_income_growth"] = self._calc_growth(
            _safe(inc.operating_income),
            _safe(prev_inc.operating_income) if prev_inc else None,
        )
        results["fcf_growth_yoy"] = self._calc_fcf_growth(cf, prev_cf)

        # ── financial_structure (6) ──
        results["debt_to_equity"] = self._calc_debt_to_equity(bal)
        results["current_ratio"] = self._calc_ratio(
            bal.total_current_assets, bal.total_current_liabilities
        )
        results["interest_coverage"] = self._calc_interest_coverage(inc, bal, prev_inc)
        results["net_debt_to_ebitda"] = self._calc_net_debt_ebitda(bal, inc)
        results["cash_runway_years"] = self._calc_cash_runway(bal, cf)
        results["short_term_debt_pct"] = self._calc_short_term_debt_pct(bal)

        # ── cash_flow_quality (6) ──
        results["fcf_margin"] = self._calc_fcf_margin(cf, inc)
        results["ocf_to_net_income"] = self._calc_ratio(
            cf.operating_cashflow, inc.net_income
        )
        results["capex_to_ocf"] = self._calc_capex_to_ocf(cf)
        results["accruals_ratio"] = self._calc_accruals(inc, cf, bal)
        results["fcf_conversion"] = self._calc_fcf_conversion(cf, inc)
        results["cash_from_ops_trend"] = self._calc_ocf_trend_placeholder()

        # ── operational_efficiency (6) ──
        results["dso"] = self._calc_dso(bal, inc)
        results["ar_to_revenue"] = self._calc_ratio(
            bal.current_net_receivables, inc.total_revenue
        )
        results["inventory_turnover_days"] = self._calc_inventory_days(bal, inc)
        results["inventory_vs_sales_growth"] = self._calc_inv_vs_sales(
            bal, inc, prev_bal, prev_inc
        )
        results["sga_to_revenue"] = self._calc_ratio(
            inc.selling_general_and_administrative, inc.total_revenue
        )
        results["asset_turnover"] = self._calc_ratio(
            inc.total_revenue, bal.total_assets
        )

        # ── dilution_shareholder (4) ──
        results["dilution_3y_cum"] = self._calc_dilution_3y(bal, prev_bal_3y)
        results["sbc_to_revenue"] = (None, "missing", "SBC 전용 필드 미제공")
        results["buyback_offsets_sbc"] = (None, "missing", "SBC 데이터 필요")
        results["net_shareholder_yield"] = self._calc_shareholder_yield(cf, stock)

        # ── valuation (3) ──
        results["pe_ratio"] = self._calc_pe(stock)
        results["ev_to_ebitda"] = self._calc_ev_ebitda(stock, inc)
        results["fcf_yield"] = self._calc_fcf_yield(cf, stock)

        return results

    # ── 계산 헬퍼 ──

    def _calc_ratio(self, numerator, denominator) -> tuple:
        val = _div(numerator, denominator)
        if val is None:
            return (None, "missing", "분모 0 또는 데이터 없음")
        return (val, "normal", "")

    def _calc_roic(self, inc, bal) -> tuple:
        op_income = _safe(inc.operating_income)
        tax_expense = _safe(inc.income_tax_expense)
        income_before_tax = _safe(inc.income_before_tax)
        equity = _safe(inc.net_income)  # placeholder
        equity = _safe(bal.total_shareholder_equity)
        long_debt = _safe(bal.long_term_debt) or 0

        if op_income is None or equity is None:
            return (None, "missing", "")

        tax_rate = 0.21  # 기본 법인세율
        if tax_expense is not None and income_before_tax and income_before_tax != 0:
            tax_rate = max(0, min(1, tax_expense / income_before_tax))

        invested_capital = equity + long_debt
        if invested_capital == 0:
            return (None, "missing", "투하자본 0")

        nopat = op_income * (1 - tax_rate)
        return (nopat / invested_capital, "normal", "")

    def _calc_growth(self, current, prev) -> tuple:
        if current is None or prev is None:
            return (None, "missing", "전년도 데이터 없음")
        if abs(prev) < 1:  # 분모가 너무 작으면
            return (None, "missing", "전년도 값이 0에 가까움")
        return ((current - prev) / abs(prev), "normal", "")

    def _calc_fcf_growth(self, cf, prev_cf) -> tuple:
        if not cf or not prev_cf:
            return (None, "missing", "전년도 데이터 없음")
        fcf_now = (_safe(cf.operating_cashflow) or 0) - abs(
            _safe(cf.capital_expenditures) or 0
        )
        fcf_prev = (_safe(prev_cf.operating_cashflow) or 0) - abs(
            _safe(prev_cf.capital_expenditures) or 0
        )
        if abs(fcf_prev) < 1:
            return (None, "missing", "전년도 FCF가 0에 가까움")
        return ((fcf_now - fcf_prev) / abs(fcf_prev), "normal", "")

    def _calc_debt_to_equity(self, bal) -> tuple:
        equity = _safe_nonzero(bal.total_shareholder_equity)
        if equity is None:
            return (None, "missing", "자기자본 0 또는 없음")
        short = _safe(bal.short_term_debt) or 0
        long = _safe(bal.long_term_debt) or 0
        total_debt = short + long
        return (total_debt / equity, "normal", "")

    def _calc_interest_coverage(self, inc, bal, prev_inc) -> tuple:
        # not_applicable: 무차입
        short = _safe(bal.short_term_debt) or 0
        long = _safe(bal.long_term_debt) or 0
        if short + long == 0:
            return (None, "not_applicable", "무차입 기업")

        interest = _safe(inc.interest_expense)
        if interest is None:
            return (None, "missing", "이자비용 데이터 미제공")
        if interest == 0:
            return (None, "not_applicable", "이자비용 없음")

        op_income = _safe(inc.operating_income)
        if op_income is None:
            return (None, "missing", "")

        val = op_income / interest

        # unstable 판정: 부호 반전 + 10배 변동
        if prev_inc:
            prev_interest = _safe(prev_inc.interest_expense)
            prev_op = _safe(prev_inc.operating_income)
            if prev_interest and prev_interest != 0 and prev_op is not None:
                prev_val = prev_op / prev_interest
                if (
                    prev_val != 0
                    and ((val > 0) != (prev_val > 0))
                    and abs(val) > abs(prev_val) * 10
                ):
                    return (val, "unstable", "값 변동 과대")

        return (val, "normal", "")

    def _calc_net_debt_ebitda(self, bal, inc) -> tuple:
        ebitda = _safe_nonzero(inc.ebitda)
        if ebitda is None:
            return (None, "missing", "EBITDA 0 또는 없음")
        short = _safe(bal.short_term_debt) or 0
        long = _safe(bal.long_term_debt) or 0
        cash = _safe(bal.cash_and_cash_equivalents_at_carrying_value) or 0
        net_debt = short + long - cash
        return (net_debt / ebitda, "normal", "")

    def _calc_cash_runway(self, bal, cf) -> tuple:
        ocf = _safe(cf.operating_cashflow)
        if ocf is None:
            return (None, "missing", "")
        if ocf >= 0:
            return (None, "not_applicable", "흑자 기업")
        cash = _safe(bal.cash_and_cash_equivalents_at_carrying_value)
        if cash is None:
            return (None, "missing", "")
        return (cash / abs(ocf), "normal", "")

    def _calc_short_term_debt_pct(self, bal) -> tuple:
        short = _safe(bal.short_term_debt) or 0
        long = _safe(bal.long_term_debt) or 0
        total = short + long
        if total == 0:
            return (None, "missing", "총 부채 0")
        return (short / total, "normal", "")

    def _calc_fcf_margin(self, cf, inc) -> tuple:
        revenue = _safe_nonzero(inc.total_revenue)
        if revenue is None:
            return (None, "missing", "")
        ocf = _safe(cf.operating_cashflow) or 0
        capex = abs(_safe(cf.capital_expenditures) or 0)
        return ((ocf - capex) / revenue, "normal", "")

    def _calc_capex_to_ocf(self, cf) -> tuple:
        ocf = _safe_nonzero(cf.operating_cashflow)
        if ocf is None:
            return (None, "missing", "")
        capex = abs(_safe(cf.capital_expenditures) or 0)
        return (capex / ocf, "normal", "")

    def _calc_accruals(self, inc, cf, bal) -> tuple:
        ni = _safe(inc.net_income)
        ocf = _safe(cf.operating_cashflow)
        assets = _safe_nonzero(bal.total_assets)
        if ni is None or ocf is None or assets is None:
            return (None, "missing", "")
        return ((ni - ocf) / assets, "normal", "")

    def _calc_fcf_conversion(self, cf, inc) -> tuple:
        ni = _safe_nonzero(inc.net_income)
        if ni is None:
            return (None, "missing", "")
        ocf = _safe(cf.operating_cashflow) or 0
        capex = abs(_safe(cf.capital_expenditures) or 0)
        fcf = ocf - capex
        return (fcf / ni, "normal", "")

    def _calc_ocf_trend_placeholder(self) -> tuple:
        # 3년 CAGR은 multi-year 데이터 필요 — 별도 로직 필요
        return (None, "missing", "3년 추세 계산 미구현 (Phase 2)")

    def _calc_dso(self, bal, inc) -> tuple:
        ar = _safe(bal.current_net_receivables)
        rev = _safe_nonzero(inc.total_revenue)
        if ar is None or rev is None:
            return (None, "missing", "")
        return ((ar / rev) * 365, "normal", "")

    def _calc_inventory_days(self, bal, inc) -> tuple:
        inv = _safe(bal.inventory)
        if inv is None or inv == 0:
            return (None, "not_applicable", "서비스 기업 (재고 없음)")
        cogs = _safe_nonzero(inc.cost_of_revenue)
        if cogs is None:
            return (None, "missing", "")
        return ((inv / cogs) * 365, "normal", "")

    def _calc_inv_vs_sales(self, bal, inc, prev_bal, prev_inc) -> tuple:
        inv = _safe(bal.inventory)
        if inv is None or inv == 0:
            return (None, "not_applicable", "서비스 기업 (재고 없음)")
        if not prev_bal or not prev_inc:
            return (None, "missing", "전년도 데이터 없음")
        prev_inv = _safe(prev_bal.inventory)
        prev_rev = _safe_nonzero(prev_inc.total_revenue)
        rev = _safe(inc.total_revenue)
        if prev_inv is None or prev_rev is None or rev is None or prev_inv == 0:
            return (None, "missing", "")
        inv_growth = (inv - prev_inv) / abs(prev_inv)
        rev_growth = (rev - float(prev_rev)) / abs(float(prev_rev))
        return (inv_growth - rev_growth, "normal", "")

    def _calc_dilution_3y(self, bal, prev_bal_3y) -> tuple:
        shares_now = _safe(bal.common_stock_shares_outstanding)
        if shares_now is None:
            return (None, "missing", "")
        if prev_bal_3y is None:
            return (None, "missing", "3년 전 데이터 없음")
        shares_3y = _safe_nonzero(prev_bal_3y.common_stock_shares_outstanding)
        if shares_3y is None:
            return (None, "missing", "")
        return ((shares_now - shares_3y) / shares_3y, "normal", "")

    def _calc_shareholder_yield(self, cf, stock) -> tuple:
        mcap = _safe_nonzero(stock.market_capitalization)
        if mcap is None:
            return (None, "missing", "")
        div = abs(_safe(cf.dividend_payout) or 0)
        buyback = abs(_safe(cf.payments_for_repurchase_of_common_stock) or 0)
        issuance = abs(_safe(cf.proceeds_from_issuance_of_common_stock) or 0)
        return ((div + buyback - issuance) / mcap, "normal", "")

    def _calc_pe(self, stock) -> tuple:
        pe = _safe(stock.pe_ratio)
        if pe is None:
            return (None, "missing", "")
        return (pe, "normal", "")

    def _calc_ev_ebitda(self, stock, inc) -> tuple:
        ebitda = _safe_nonzero(inc.ebitda)
        mcap = _safe(stock.market_capitalization)
        if ebitda is None or mcap is None:
            return (None, "missing", "")
        # 간이 EV = market_cap (debt/cash 조정은 Phase 2)
        return (mcap / ebitda, "normal", "")

    def _calc_fcf_yield(self, cf, stock) -> tuple:
        mcap = _safe_nonzero(stock.market_capitalization)
        if mcap is None:
            return (None, "missing", "")
        ocf = _safe(cf.operating_cashflow) or 0
        capex = abs(_safe(cf.capital_expenditures) or 0)
        fcf = ocf - capex
        return (fcf / mcap, "normal", "")

    def _update_latest(self, stock, fiscal_year: int) -> int:
        """최신 연도 snapshot을 CompanyMetricLatest에 반영"""
        snapshots = CompanyMetricSnapshot.objects.filter(
            symbol=stock, fiscal_year=fiscal_year
        )
        updated = 0
        for snap in snapshots:
            CompanyMetricLatest.objects.update_or_create(
                symbol=stock,
                metric_code=snap.metric_code,
                defaults={
                    "latest_value": snap.metric_value,
                    "latest_fiscal_year": fiscal_year,
                    "computed_at": timezone.now(),
                },
            )
            updated += 1
        return updated
