"""
validation/services 확장 단위 테스트

기존 test_preset_generator.py, test_metric_calculator.py가 커버하지 않는
미테스트 헬퍼/메서드에 대한 추가 커버리지.

테스트 대상:
  - MetricCalculator 미테스트 헬퍼 12개
      _calc_net_debt_ebitda, _calc_cash_runway, _calc_short_term_debt_pct,
      _calc_capex_to_ocf, _calc_accruals, _calc_fcf_conversion,
      _calc_fcf_growth, _calc_dilution_3y, _calc_shareholder_yield,
      _calc_pe, _calc_ev_ebitda, _calc_fcf_yield, _calc_inv_vs_sales
  - PresetGenerator 미테스트 경로
      _filter_by_size (bucket 조합), _generate_size_peers,
      _generate_thematic (DNA 미존재 분기), generate_for_symbols 배치
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from stocks.models import Stock, SP500Constituent
from validation.services.metric_calculator import MetricCalculator
from validation.services.preset_generator import PresetGenerator


# ---------------------------------------------------------------------------
# Helpers (공용)
# ---------------------------------------------------------------------------

def _mock_income(**kwargs):
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


def _mock_stock(market_cap=1_000_000_000_000, pe_ratio=25.0):
    return SimpleNamespace(
        market_capitalization=Decimal(str(market_cap)) if market_cap else None,
        pe_ratio=Decimal(str(pe_ratio)) if pe_ratio is not None else None,
    )


def _make_real_stock(symbol, sector="Technology", industry="Software",
                     market_cap=50_000_000_000):
    return Stock.objects.get_or_create(
        symbol=symbol,
        defaults={
            'stock_name': f'{symbol} Inc',
            'exchange': 'NASDAQ',
            'sector': sector,
            'industry': industry,
            'market_capitalization': Decimal(str(market_cap)) if market_cap else None,
        },
    )[0]


def _make_sp500(symbol):
    return SP500Constituent.objects.get_or_create(
        symbol=symbol,
        defaults={
            'company_name': f'{symbol} Corp',
            'sector': 'Technology',
            'is_active': True,
        },
    )[0]


# ---------------------------------------------------------------------------
# Tests: _calc_net_debt_ebitda
# ---------------------------------------------------------------------------


class TestCalcNetDebtEbitda:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        """short=10+long=40-cash=20, ebitda=30 → (10+40-20)/30 = 1.0."""
        bal = _mock_balance(short_term_debt=10, long_term_debt=40,
                            cash_and_cash_equivalents_at_carrying_value=20)
        inc = _mock_income(ebitda=30)
        val, status, _ = self.calc._calc_net_debt_ebitda(bal, inc)
        assert val == pytest.approx(1.0)
        assert status == 'normal'

    def test_zero_ebitda(self):
        """ebitda=0 → missing."""
        bal = _mock_balance()
        inc = _mock_income(ebitda=0)
        val, status, _ = self.calc._calc_net_debt_ebitda(bal, inc)
        assert val is None
        assert status == 'missing'

    def test_net_cash_negative_net_debt(self):
        """현금 > 부채 → 음수 net debt (현금 순자산)."""
        bal = _mock_balance(short_term_debt=5, long_term_debt=5,
                            cash_and_cash_equivalents_at_carrying_value=50)
        inc = _mock_income(ebitda=10)
        val, status, _ = self.calc._calc_net_debt_ebitda(bal, inc)
        # (5 + 5 - 50) / 10 = -4.0
        assert val == pytest.approx(-4.0)
        assert status == 'normal'


# ---------------------------------------------------------------------------
# Tests: _calc_cash_runway
# ---------------------------------------------------------------------------


class TestCalcCashRunway:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_positive_ocf_not_applicable(self):
        """흑자 기업(OCF >= 0) → not_applicable."""
        cf = _mock_cashflow(operating_cashflow=10_000_000)
        bal = _mock_balance()
        val, status, _ = self.calc._calc_cash_runway(bal, cf)
        assert val is None
        assert status == 'not_applicable'

    def test_negative_ocf_normal(self):
        """적자 기업(OCF<0) + cash 존재 → runway = cash / |ocf|."""
        cf = _mock_cashflow(operating_cashflow=-10)
        bal = _mock_balance(cash_and_cash_equivalents_at_carrying_value=40)
        val, status, _ = self.calc._calc_cash_runway(bal, cf)
        assert val == pytest.approx(4.0)
        assert status == 'normal'

    def test_missing_cash(self):
        """OCF<0 + cash=None → missing."""
        cf = _mock_cashflow(operating_cashflow=-10)
        bal = _mock_balance(cash_and_cash_equivalents_at_carrying_value=None)
        val, status, _ = self.calc._calc_cash_runway(bal, cf)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_short_term_debt_pct
# ---------------------------------------------------------------------------


class TestCalcShortTermDebtPct:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        """short=20, long=80 → 20/100 = 0.2."""
        bal = _mock_balance(short_term_debt=20, long_term_debt=80)
        val, status, _ = self.calc._calc_short_term_debt_pct(bal)
        assert val == pytest.approx(0.2)
        assert status == 'normal'

    def test_no_debt(self):
        """총 부채 0 → missing."""
        bal = _mock_balance(short_term_debt=0, long_term_debt=0)
        val, status, _ = self.calc._calc_short_term_debt_pct(bal)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_capex_to_ocf
# ---------------------------------------------------------------------------


class TestCalcCapexToOcf:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        """|capex=8| / ocf=40 → 0.2."""
        cf = _mock_cashflow(operating_cashflow=40, capital_expenditures=-8)
        val, status, _ = self.calc._calc_capex_to_ocf(cf)
        assert val == pytest.approx(0.2)
        assert status == 'normal'

    def test_zero_ocf(self):
        cf = _mock_cashflow(operating_cashflow=0)
        val, status, _ = self.calc._calc_capex_to_ocf(cf)
        assert val is None
        assert status == 'missing'

    def test_positive_capex_abs(self):
        """capex가 양수로 들어와도 abs()로 처리."""
        cf = _mock_cashflow(operating_cashflow=40, capital_expenditures=8)
        val, _, _ = self.calc._calc_capex_to_ocf(cf)
        assert val == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# Tests: _calc_accruals
# ---------------------------------------------------------------------------


class TestCalcAccruals:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        """(NI=20 - OCF=35) / Assets=300 = -0.05."""
        inc = _mock_income(net_income=20)
        cf = _mock_cashflow(operating_cashflow=35)
        bal = _mock_balance(total_assets=300)
        val, status, _ = self.calc._calc_accruals(inc, cf, bal)
        assert val == pytest.approx(-0.05)
        assert status == 'normal'

    def test_missing_total_assets(self):
        inc = _mock_income()
        cf = _mock_cashflow()
        bal = _mock_balance(total_assets=0)
        val, status, _ = self.calc._calc_accruals(inc, cf, bal)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_fcf_conversion
# ---------------------------------------------------------------------------


class TestCalcFcfConversion:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        """FCF=(35-8)=27, NI=20 → 1.35."""
        cf = _mock_cashflow(operating_cashflow=35, capital_expenditures=-8)
        inc = _mock_income(net_income=20)
        val, status, _ = self.calc._calc_fcf_conversion(cf, inc)
        assert val == pytest.approx(1.35)
        assert status == 'normal'

    def test_zero_net_income(self):
        cf = _mock_cashflow()
        inc = _mock_income(net_income=0)
        val, status, _ = self.calc._calc_fcf_conversion(cf, inc)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_fcf_growth
# ---------------------------------------------------------------------------


class TestCalcFcfGrowth:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        """현재 FCF=30, 전년도 FCF=20 → 0.5."""
        cf = _mock_cashflow(operating_cashflow=40, capital_expenditures=-10)
        prev_cf = _mock_cashflow(operating_cashflow=30, capital_expenditures=-10)
        val, status, _ = self.calc._calc_fcf_growth(cf, prev_cf)
        assert val == pytest.approx(0.5)
        assert status == 'normal'

    def test_no_prev(self):
        cf = _mock_cashflow()
        val, status, _ = self.calc._calc_fcf_growth(cf, None)
        assert val is None
        assert status == 'missing'

    def test_zero_prev_fcf(self):
        """전년도 FCF가 0에 가까우면 missing."""
        cf = _mock_cashflow(operating_cashflow=10, capital_expenditures=-5)
        prev_cf = _mock_cashflow(operating_cashflow=5, capital_expenditures=-5)
        # prev FCF = 0 → missing
        val, status, _ = self.calc._calc_fcf_growth(cf, prev_cf)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_dilution_3y
# ---------------------------------------------------------------------------


class TestCalcDilution3y:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal_dilution(self):
        """발행주식 1.1B 대비 3년 전 1.0B → 10% 희석."""
        bal = _mock_balance(common_stock_shares_outstanding=1_100_000_000)
        prev_bal = _mock_balance(common_stock_shares_outstanding=1_000_000_000)
        val, status, _ = self.calc._calc_dilution_3y(bal, prev_bal)
        assert val == pytest.approx(0.1)
        assert status == 'normal'

    def test_buyback_negative(self):
        """자사주 매입으로 발행주식 감소 → 음수."""
        bal = _mock_balance(common_stock_shares_outstanding=900_000_000)
        prev_bal = _mock_balance(common_stock_shares_outstanding=1_000_000_000)
        val, _, _ = self.calc._calc_dilution_3y(bal, prev_bal)
        assert val == pytest.approx(-0.1)

    def test_no_prev_3y(self):
        bal = _mock_balance()
        val, status, _ = self.calc._calc_dilution_3y(bal, None)
        assert val is None
        assert status == 'missing'

    def test_missing_shares_now(self):
        bal = _mock_balance(common_stock_shares_outstanding=None)
        prev_bal = _mock_balance()
        val, status, _ = self.calc._calc_dilution_3y(bal, prev_bal)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_shareholder_yield
# ---------------------------------------------------------------------------


class TestCalcShareholderYield:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal_positive_yield(self):
        """배당 5 + 자사주 10 - 발행 1 = 14 / mcap 100 = 0.14."""
        cf = _mock_cashflow(
            dividend_payout=-5,
            payments_for_repurchase_of_common_stock=-10,
            proceeds_from_issuance_of_common_stock=1,
        )
        stock = _mock_stock(market_cap=100)
        val, status, _ = self.calc._calc_shareholder_yield(cf, stock)
        assert val == pytest.approx(0.14)
        assert status == 'normal'

    def test_zero_market_cap(self):
        cf = _mock_cashflow()
        stock = _mock_stock(market_cap=0)
        val, status, _ = self.calc._calc_shareholder_yield(cf, stock)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_pe
# ---------------------------------------------------------------------------


class TestCalcPe:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        stock = _mock_stock(pe_ratio=25.5)
        val, status, _ = self.calc._calc_pe(stock)
        assert val == pytest.approx(25.5)
        assert status == 'normal'

    def test_missing(self):
        stock = _mock_stock(pe_ratio=None)
        val, status, _ = self.calc._calc_pe(stock)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_ev_ebitda
# ---------------------------------------------------------------------------


class TestCalcEvEbitda:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        """mcap=300B / ebitda=30B = 10."""
        stock = _mock_stock(market_cap=300_000_000_000)
        inc = _mock_income(ebitda=30_000_000_000)
        val, status, _ = self.calc._calc_ev_ebitda(stock, inc)
        assert val == pytest.approx(10.0)
        assert status == 'normal'

    def test_zero_ebitda(self):
        stock = _mock_stock(market_cap=100_000_000_000)
        inc = _mock_income(ebitda=0)
        val, status, _ = self.calc._calc_ev_ebitda(stock, inc)
        assert val is None
        assert status == 'missing'

    def test_missing_mcap(self):
        stock = _mock_stock(market_cap=None)
        inc = _mock_income()
        val, status, _ = self.calc._calc_ev_ebitda(stock, inc)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_fcf_yield
# ---------------------------------------------------------------------------


class TestCalcFcfYield:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal(self):
        """FCF=27 / mcap=100 = 0.27."""
        cf = _mock_cashflow(operating_cashflow=35, capital_expenditures=-8)
        stock = _mock_stock(market_cap=100)
        val, status, _ = self.calc._calc_fcf_yield(cf, stock)
        assert val == pytest.approx(0.27)
        assert status == 'normal'

    def test_zero_mcap(self):
        cf = _mock_cashflow()
        stock = _mock_stock(market_cap=0)
        val, status, _ = self.calc._calc_fcf_yield(cf, stock)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: _calc_inv_vs_sales
# ---------------------------------------------------------------------------


class TestCalcInvVsSales:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_normal_inv_above_sales(self):
        """재고 +20%, 매출 +10% → +10%p."""
        bal = _mock_balance(inventory=120)
        inc = _mock_income(total_revenue=110)
        prev_bal = _mock_balance(inventory=100)
        prev_inc = _mock_income(total_revenue=100)
        val, status, _ = self.calc._calc_inv_vs_sales(bal, inc, prev_bal, prev_inc)
        assert val == pytest.approx(0.1, abs=0.001)
        assert status == 'normal'

    def test_service_company_no_inventory(self):
        """재고=0 → not_applicable."""
        bal = _mock_balance(inventory=0)
        inc = _mock_income()
        val, status, _ = self.calc._calc_inv_vs_sales(bal, inc, None, None)
        assert val is None
        assert status == 'not_applicable'

    def test_missing_prev(self):
        bal = _mock_balance(inventory=100)
        inc = _mock_income()
        val, status, _ = self.calc._calc_inv_vs_sales(bal, inc, None, None)
        assert val is None
        assert status == 'missing'


# ---------------------------------------------------------------------------
# Tests: PresetGenerator._filter_by_size
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFilterBySize:
    def setup_method(self):
        self.gen = PresetGenerator()
        # 각 bucket별 종목 생성
        _make_real_stock("MEGA1", market_cap=300_000_000_000)
        _make_real_stock("LRG1", market_cap=50_000_000_000)
        _make_real_stock("MID1", market_cap=5_000_000_000)
        _make_real_stock("SML1", market_cap=500_000_000)

    def test_mega_only(self):
        qs = self.gen._filter_by_size(Stock.objects.all(), ['mega'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert 'MEGA1' in symbols
        assert 'LRG1' not in symbols

    def test_large_only(self):
        qs = self.gen._filter_by_size(Stock.objects.all(), ['large'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert 'LRG1' in symbols
        assert 'MEGA1' not in symbols

    def test_mid_only(self):
        qs = self.gen._filter_by_size(Stock.objects.all(), ['mid'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert 'MID1' in symbols
        assert 'SML1' not in symbols

    def test_small_only(self):
        qs = self.gen._filter_by_size(Stock.objects.all(), ['small'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert 'SML1' in symbols
        assert 'MID1' not in symbols

    def test_multiple_buckets(self):
        """[mid, large] 합집합."""
        qs = self.gen._filter_by_size(Stock.objects.all(), ['mid', 'large'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert 'LRG1' in symbols and 'MID1' in symbols
        assert 'MEGA1' not in symbols and 'SML1' not in symbols


# ---------------------------------------------------------------------------
# Tests: PresetGenerator._generate_size_peers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateSizePeers:
    def test_mega_with_enough_peers(self):
        """mega bucket + 같은 sector mega peer 3개 이상 → 프리셋 생성."""
        stock = _make_real_stock("SZP1", sector="Technology", industry="SW",
                                 market_cap=300_000_000_000)
        for i in range(5):
            sym = f"BIG{i:02d}"
            _make_real_stock(sym, sector="Technology", industry="SW",
                             market_cap=250_000_000_000)
            _make_sp500(sym)

        gen = PresetGenerator()
        base_qs = Stock.objects.exclude(symbol="SZP1")
        count = gen._generate_size_peers(stock, base_qs, 'mega')
        assert count == 1

        from validation.models import PeerPreset
        preset = PeerPreset.objects.get(symbol=stock, preset_key='size_peers')
        assert preset.generation_method == 'auto_size'
        assert preset.peer_count >= 3

    def test_insufficient_peers_skipped(self):
        """peer < 3이면 생성 안 함."""
        stock = _make_real_stock("SZP2", sector="Materials", industry="Steel",
                                 market_cap=300_000_000_000)
        _make_real_stock("SOLO", sector="Materials", industry="Steel",
                         market_cap=250_000_000_000)

        gen = PresetGenerator()
        base_qs = Stock.objects.exclude(symbol="SZP2")
        count = gen._generate_size_peers(stock, base_qs, 'mega')
        assert count == 0

    def test_no_sector_skipped(self):
        """sector 없으면 생성 안 함."""
        stock = _make_real_stock("SZP3", sector=None, industry=None,
                                 market_cap=300_000_000_000)
        gen = PresetGenerator()
        count = gen._generate_size_peers(stock, Stock.objects.none(), 'mega')
        assert count == 0


# ---------------------------------------------------------------------------
# Tests: PresetGenerator._generate_thematic
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateThematic:
    def test_no_dna_returns_zero(self):
        """Chain Sight 프로파일이 없으면 생성 안 함."""
        stock = _make_real_stock("TMT1", sector="Technology", industry="SW")
        gen = PresetGenerator()
        count = gen._generate_thematic(stock, Stock.objects.none())
        assert count == 0


# ---------------------------------------------------------------------------
# Tests: PresetGenerator.generate_for_symbols (배치)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateForSymbolsBatch:
    def test_explicit_symbols(self):
        """명시적 symbols 리스트 → 그만큼만 처리."""
        stock = _make_real_stock("BAT1", sector="Technology", industry="SW",
                                 market_cap=50_000_000_000)
        _make_sp500("BAT1")
        # peer 10개 생성 (default preset 생성 가능하도록)
        for i in range(10):
            sym = f"PERBAT{i:02d}"
            _make_real_stock(sym, sector="Technology", industry="SW",
                             market_cap=40_000_000_000)
            _make_sp500(sym)

        gen = PresetGenerator()
        result = gen.generate_for_symbols(["BAT1"])
        assert result['total'] == 1
        assert result['success'] == 1

    def test_nonexistent_symbol_counts_as_fail(self):
        """존재하지 않는 심볼 → error로 success 증가 안 함."""
        gen = PresetGenerator()
        result = gen.generate_for_symbols(["NONEXIST_BAT"])
        assert result['total'] == 1
        assert result['success'] == 0


# ---------------------------------------------------------------------------
# Tests: MetricCalculator.calculate_for_symbol (통합)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCalculateForSymbolIntegration:
    def test_stock_not_found(self):
        """존재하지 않는 종목 → error 반환."""
        calc = MetricCalculator()
        result = calc.calculate_for_symbol("NOTEXIST_MC")
        assert result['error'] == 'Stock not found'

    def test_no_financial_data(self):
        """재무제표 없는 종목 → 'No financial data' error."""
        _make_real_stock("NOFIN_MC", sector="Tech", industry="SW",
                         market_cap=10_000_000_000)
        calc = MetricCalculator()
        # fetcher가 빈 dict를 반환하도록 mock
        with patch.object(calc.fetcher, 'get_financial_data', return_value={}):
            result = calc.calculate_for_symbol("NOFIN_MC")
        assert result['error'] == 'No financial data'

    def test_symbol_uppercased_on_calculate(self):
        """소문자 심볼 → upper() 변환되어 조회 (없으므로 Stock not found)."""
        calc = MetricCalculator()
        result = calc.calculate_for_symbol("xyz_missing")
        # 어차피 없어서 error이지만, symbol은 upper로 반환되어야 함
        assert result['symbol'] == 'XYZ_MISSING'
