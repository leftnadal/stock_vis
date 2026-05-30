"""
Task 1: 재무제표 데이터 존재 확인 + 필요 시 FMP API 수집

기존 DB(IncomeStatement, BalanceSheet, CashFlowStatement)에 데이터가 있으면 스킵.
없으면 기존 stocks/tasks.py의 update_financials_with_provider를 호출하여 수집.
"""

import logging

from packages.shared.stocks.models import (
    BalanceSheet,
    CashFlowStatement,
    IncomeStatement,
    SP500Constituent,
)

logger = logging.getLogger(__name__)

MIN_YEARS_REQUIRED = 3  # 최소 3년 데이터 필요


class FinancialFetcher:
    """재무제표 가용성 확인 및 수집 트리거"""

    def check_and_fetch(self, symbols: list[str] = None) -> dict:
        """
        S&P 500 종목들의 재무제표 존재 확인.
        Returns: {'total': int, 'ready': int, 'missing': list, 'insufficient': list}
        """
        if symbols is None:
            symbols = list(
                SP500Constituent.objects.filter(is_active=True)
                .values_list('symbol', flat=True)
            )

        ready = []
        missing = []
        insufficient = []

        for symbol in symbols:
            inc_count = IncomeStatement.objects.filter(
                stock_id=symbol, period_type='annual'
            ).count()
            bal_count = BalanceSheet.objects.filter(
                stock_id=symbol, period_type='annual'
            ).count()
            cf_count = CashFlowStatement.objects.filter(
                stock_id=symbol, period_type='annual'
            ).count()

            min_count = min(inc_count, bal_count, cf_count)
            if min_count == 0:
                missing.append(symbol)
            elif min_count < MIN_YEARS_REQUIRED:
                insufficient.append(symbol)
            else:
                ready.append(symbol)

        return {
            'total': len(symbols),
            'ready': len(ready),
            'missing': missing,
            'insufficient': insufficient,
            'ready_symbols': ready,
        }

    def get_financial_data(self, symbol: str, years: int = 5) -> dict:
        """
        단일 종목의 연간 재무제표를 dict로 반환.
        Returns: {fiscal_year: {'income': {...}, 'balance': {...}, 'cashflow': {...}}}
        """
        symbol = symbol.upper()

        incomes = {
            i.fiscal_year: i
            for i in IncomeStatement.objects.filter(
                stock_id=symbol, period_type='annual'
            ).order_by('-fiscal_year')[:years]
        }
        balances = {
            b.fiscal_year: b
            for b in BalanceSheet.objects.filter(
                stock_id=symbol, period_type='annual'
            ).order_by('-fiscal_year')[:years]
        }
        cashflows = {
            c.fiscal_year: c
            for c in CashFlowStatement.objects.filter(
                stock_id=symbol, period_type='annual'
            ).order_by('-fiscal_year')[:years]
        }

        fiscal_years = sorted(
            set(incomes.keys()) & set(balances.keys()) & set(cashflows.keys()),
            reverse=True,
        )[:years]

        result = {}
        for fy in fiscal_years:
            result[fy] = {
                'income': incomes[fy],
                'balance': balances[fy],
                'cashflow': cashflows[fy],
            }

        return result
