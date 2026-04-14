"""
MetricCalculator 단위 테스트

테스트 대상:
  - _safe(), _safe_nonzero(), _div() — 안전 변환 헬퍼
  - _calc_ratio() — 비율 계산
  - _calc_roic() — ROIC 계산 (세율 추정 포함)
  - _calc_growth() — YoY 성장률
  - _calc_debt_to_equity() — 부채비율
  - _calc_interest_coverage() — 이자보상배율
  - _calc_fcf_margin() — FCF 마진
  - _calc_dso() — 매출채권 회전일수
  - _calc_inventory_days() — 재고자산 회전일수
  - calculate_for_symbol() — 통합 플로우
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace

import pytest

from validation.services.metric_calculator import (
    _safe, _safe_nonzero, _div, MetricCalculator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_income(**kwargs):
    """IncomeStatement mock. kwargs로 필요한 필드만 설정."""
    defaults = {
        'total_revenue': 100_000_000_000,
        'cost_of_revenue': 60_000_000_000,
        'gross_profit': 40_000_000_000,
        'operating_income': 25_000_000_000,
        'net_income': 20_000_000_000,
        'ebitda': 30_000_000_000,
        'interest_expense': 1_000_000_000,
        'income_tax_expense': 5_000_000_000,
        'income_before_tax': 24_000_000_000,
        'selling_general_and_administrative': 10_000_000_000,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _mock_balance(**kwargs):
    defaults = {
        'total_assets': 300_000_000_000,
        'total_current_assets': 80_000_000_000,
        'total_current_liabilities': 60_000_000_000,
        'total_shareholder_equity': 150_000_000_000,
        'long_term_debt': 50_000_000_000,
        'short_term_debt': 10_000_000_000,
        'cash_and_cash_equivalents_at_carrying_value': 30_000_000_000,
        'current_net_receivables': 20_000_000_000,
        'inventory': 5_000_000_000,
        'common_stock_shares_outstanding': 1_000_000_000,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _mock_cashflow(**kwargs):
    defaults = {
        'operating_cashflow': 35_000_000_000,
        'capital_expenditures': -8_000_000_000,
        'dividend_payout': -5_000_000_000,
        'payments_for_repurchase_of_common_stock': -10_000_000_000,
        'proceeds_from_issuance_of_common_stock': 1_000_000_000,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Tests: 안전 변환 헬퍼 (순수 함수, DB 불필요)
# ---------------------------------------------------------------------------


class TestSafeHelpers:
    def test_safe_normal(self):
        assert _safe(100) == 100.0

    def test_safe_decimal(self):
        assert _safe(Decimal("3.14")) == pytest.approx(3.14)

    def test_safe_none(self):
        assert _safe(None) is None

    def test_safe_string_invalid(self):
        assert _safe("abc") is None

    def test_safe_zero(self):
        """실제 0은 0으로 반환."""
        assert _safe(0) == 0.0

    def test_safe_nonzero_normal(self):
        assert _safe_nonzero(100) == 100.0

    def test_safe_nonzero_zero_returns_none(self):
        assert _safe_nonzero(0) is None

    def test_safe_nonzero_none(self):
        assert _safe_nonzero(None) is None

    def test_div_normal(self):
        assert _div(10, 5) == pytest.approx(2.0)

    def test_div_zero_denominator(self):
        assert _div(10, 0) is None

    def test_div_none_numerator(self):
        assert _div(None, 5) is None

    def test_div_none_denominator(self):
        assert _div(10, None) is None


# ---------------------------------------------------------------------------
# Tests: 개별 지표 계산 메서드
# ---------------------------------------------------------------------------


class TestCalcRatio:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal_ratio(self):
        val, status, reason = self.calc._calc_ratio(40, 100)
        assert val == pytest.approx(0.4)
        assert status == 'normal'

    def test_zero_denominator(self):
        val, status, reason = self.calc._calc_ratio(40, 0)
        assert val is None
        assert status == 'missing'

    def test_none_values(self):
        val, status, _ = self.calc._calc_ratio(None, 100)
        assert val is None


class TestCalcRoic:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal_roic(self):
        inc = _mock_income()
        bal = _mock_balance()
        val, status, _ = self.calc._calc_roic(inc, bal)
        assert val is not None
        assert status == 'normal'
        # ROIC = NOPAT / Invested Capital
        # tax_rate = 5B / 24B = ~0.2083
        # NOPAT = 25B * (1 - 0.2083) = ~19.79B
        # IC = 150B + 50B = 200B
        # ROIC = ~0.0989
        assert val == pytest.approx(0.0989, abs=0.01)

    def test_roic_missing_operating_income(self):
        inc = _mock_income(operating_income=None)
        bal = _mock_balance()
        val, status, _ = self.calc._calc_roic(inc, bal)
        assert val is None
        assert status == 'missing'

    def test_roic_zero_invested_capital(self):
        inc = _mock_income()
        bal = _mock_balance(total_shareholder_equity=0, long_term_debt=0)
        val, status, _ = self.calc._calc_roic(inc, bal)
        assert val is None
        assert status == 'missing'

    def test_roic_default_tax_rate(self):
        """income_before_tax=0 → 기본 세율 0.21 사용."""
        inc = _mock_income(income_before_tax=0)
        bal = _mock_balance()
        val, status, _ = self.calc._calc_roic(inc, bal)
        assert val is not None
        # NOPAT = 25B * (1 - 0.21) = 19.75B
        # IC = 200B → 0.09875
        assert val == pytest.approx(0.09875, abs=0.001)


class TestCalcGrowth:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal_growth(self):
        val, status, _ = self.calc._calc_growth(120, 100)
        assert val == pytest.approx(0.2)
        assert status == 'normal'

    def test_negative_growth(self):
        val, status, _ = self.calc._calc_growth(80, 100)
        assert val == pytest.approx(-0.2)

    def test_missing_prev(self):
        val, status, _ = self.calc._calc_growth(100, None)
        assert val is None
        assert status == 'missing'

    def test_zero_prev(self):
        """전년도 값이 0에 가까우면 missing."""
        val, status, _ = self.calc._calc_growth(100, 0.5)
        assert val is None


class TestCalcDebtToEquity:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        bal = _mock_balance(short_term_debt=10, long_term_debt=40,
                            total_shareholder_equity=100)
        val, status, _ = self.calc._calc_debt_to_equity(bal)
        assert val == pytest.approx(0.5)
        assert status == 'normal'

    def test_zero_equity(self):
        bal = _mock_balance(total_shareholder_equity=0)
        val, status, _ = self.calc._calc_debt_to_equity(bal)
        assert val is None
        assert status == 'missing'


class TestCalcInterestCoverage:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        inc = _mock_income(operating_income=50, interest_expense=10)
        bal = _mock_balance(short_term_debt=10, long_term_debt=40)
        val, status, _ = self.calc._calc_interest_coverage(inc, bal, None)
        assert val == pytest.approx(5.0)
        assert status == 'normal'

    def test_no_debt(self):
        """무차입 → not_applicable."""
        inc = _mock_income()
        bal = _mock_balance(short_term_debt=0, long_term_debt=0)
        val, status, _ = self.calc._calc_interest_coverage(inc, bal, None)
        assert status == 'not_applicable'

    def test_zero_interest(self):
        inc = _mock_income(interest_expense=0)
        bal = _mock_balance(short_term_debt=10, long_term_debt=40)
        val, status, _ = self.calc._calc_interest_coverage(inc, bal, None)
        assert status == 'not_applicable'

    def test_unstable_detection(self):
        """부호 반전 + 10배 변동 → unstable."""
        inc = _mock_income(operating_income=100, interest_expense=10)
        bal = _mock_balance(short_term_debt=10, long_term_debt=40)
        prev_inc = _mock_income(operating_income=-5, interest_expense=10)
        val, status, _ = self.calc._calc_interest_coverage(inc, bal, prev_inc)
        # current: 100/10=10, prev: -5/10=-0.5
        # sign flip + |10| > |-0.5|*10 → unstable
        assert status == 'unstable'


class TestCalcFcfMargin:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        cf = _mock_cashflow(operating_cashflow=35, capital_expenditures=-8)
        inc = _mock_income(total_revenue=100)
        val, status, _ = self.calc._calc_fcf_margin(cf, inc)
        # FCF = 35 - 8 = 27, margin = 27/100
        assert val == pytest.approx(0.27)

    def test_zero_revenue(self):
        cf = _mock_cashflow()
        inc = _mock_income(total_revenue=0)
        val, status, _ = self.calc._calc_fcf_margin(cf, inc)
        assert val is None
        assert status == 'missing'


class TestCalcDso:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        bal = _mock_balance(current_net_receivables=20)
        inc = _mock_income(total_revenue=365)
        val, status, _ = self.calc._calc_dso(bal, inc)
        assert val == pytest.approx(20.0)
        assert status == 'normal'

    def test_missing_ar(self):
        bal = _mock_balance(current_net_receivables=None)
        inc = _mock_income(total_revenue=100)
        val, status, _ = self.calc._calc_dso(bal, inc)
        assert val is None


class TestCalcInventoryDays:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        bal = _mock_balance(inventory=10)
        inc = _mock_income(cost_of_revenue=365)
        val, status, _ = self.calc._calc_inventory_days(bal, inc)
        assert val == pytest.approx(10.0)

    def test_no_inventory(self):
        """재고 없는 서비스 기업 → not_applicable."""
        bal = _mock_balance(inventory=None)
        inc = _mock_income()
        val, status, _ = self.calc._calc_inventory_days(bal, inc)
        assert status == 'not_applicable'

    def test_zero_inventory(self):
        bal = _mock_balance(inventory=0)
        inc = _mock_income()
        val, status, _ = self.calc._calc_inventory_days(bal, inc)
        assert status == 'not_applicable'
