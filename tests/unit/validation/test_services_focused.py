"""
validation 서비스 단위 테스트 — focused (신규 작성)

대상:
  - preset_generator.py — PresetGenerator
  - benchmark_calculator.py — BenchmarkCalculator + assign_size_bucket + get_adjacent_buckets
  - metric_calculator.py — _safe/_div + MetricCalculator
  - relative_metrics.py — RelativeMetricCalculator
  - interpretation.py — 해석 텍스트 함수

기존 테스트(test_preset_generator.py 등)와 클래스 이름이 겹치지 않도록
"Focused" 접미사로 분리. 각 서비스당 최소 6개 이상.
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.metrics.models import (
    CompanyMetricSnapshot,
    IndustryMetricBenchmark,
    MetricDefinition,
)
from packages.shared.stocks.models import (
    IndustryClassification,
    SP500Constituent,
    Stock,
)
from services.validation.models import PeerPreset
from services.validation.services.benchmark_calculator import (
    BenchmarkCalculator,
    assign_size_bucket,
    get_adjacent_buckets,
)
from services.validation.services.interpretation import (
    determine_trend,
    generate_leader_summary,
    generate_metric_interpretation,
    generate_summary_text,
)
from services.validation.services.metric_calculator import (
    MetricCalculator,
    _div,
    _safe,
    _safe_nonzero,
)
from services.validation.services.preset_generator import PresetGenerator
from services.validation.services.relative_metrics import RelativeMetricCalculator

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_stock(symbol, sector="Technology", industry="Software",
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


def _make_sp500(symbol, is_active=True):
    return SP500Constituent.objects.get_or_create(
        symbol=symbol,
        defaults={
            'company_name': f'{symbol} Corp',
            'sector': 'Technology',
            'is_active': is_active,
        },
    )[0]


def _make_metric_def(code, category='profitability', higher_is_better=True,
                     is_benchmarkable=True):
    return MetricDefinition.objects.get_or_create(
        metric_code=code,
        defaults={
            'display_name': code,
            'display_name_en': code,
            'category': category,
            'unit': 'ratio',
            'higher_is_better': higher_is_better,
            'is_benchmarkable': is_benchmarkable,
        },
    )[0]


def _make_snapshot(symbol, fy, metric_code, value, status='normal'):
    md = _make_metric_def(metric_code)
    return CompanyMetricSnapshot.objects.update_or_create(
        symbol_id=symbol,
        fiscal_year=fy,
        metric_code=md,
        defaults={
            'metric_value': Decimal(str(value)) if value is not None else None,
            'value_status': status,
        },
    )[0]


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


# ===========================================================================
# preset_generator — PresetGenerator (focused)
# ===========================================================================


@pytest.mark.django_db
class TestPresetFilterBySizeFocused:
    """PresetGenerator._filter_by_size 의 bucket 분기 확인."""

    def test_mega_bucket_returns_only_mega(self):
        _make_stock("MEG1", market_cap=300_000_000_000)
        _make_stock("LRG1", market_cap=50_000_000_000)
        _make_stock("MID1", market_cap=5_000_000_000)

        qs = Stock.objects.all()
        gen = PresetGenerator()
        result = gen._filter_by_size(qs, ['mega'])
        syms = set(result.values_list('symbol', flat=True))

        assert "MEG1" in syms
        assert "LRG1" not in syms
        assert "MID1" not in syms

    def test_large_bucket_excludes_mega_and_mid(self):
        _make_stock("MEG2", market_cap=300_000_000_000)
        _make_stock("LRG2", market_cap=50_000_000_000)
        _make_stock("MID2", market_cap=5_000_000_000)

        gen = PresetGenerator()
        result = gen._filter_by_size(Stock.objects.all(), ['large'])
        syms = set(result.values_list('symbol', flat=True))

        assert "LRG2" in syms
        assert "MEG2" not in syms
        assert "MID2" not in syms

    def test_small_bucket_lt_2b(self):
        _make_stock("SML1", market_cap=500_000_000)
        _make_stock("MID3", market_cap=5_000_000_000)

        gen = PresetGenerator()
        result = gen._filter_by_size(Stock.objects.all(), ['small'])
        syms = set(result.values_list('symbol', flat=True))

        assert "SML1" in syms
        assert "MID3" not in syms

    def test_multiple_buckets_union(self):
        _make_stock("M1", market_cap=300_000_000_000)
        _make_stock("L1", market_cap=50_000_000_000)
        _make_stock("S1", market_cap=500_000_000)

        gen = PresetGenerator()
        result = gen._filter_by_size(Stock.objects.all(), ['mega', 'small'])
        syms = set(result.values_list('symbol', flat=True))

        assert "M1" in syms and "S1" in syms
        assert "L1" not in syms


@pytest.mark.django_db
class TestPresetCalcConfidenceFocused:
    """confidence_score 계산 — special 산업 패널티 및 peer_count 분기."""

    def test_confidence_full_with_many_peers(self):
        stock = _make_stock("CF1")
        gen = PresetGenerator()
        score = gen._calc_confidence(20, stock)
        assert score == 1.0

    def test_confidence_drop_with_mid_peers(self):
        stock = _make_stock("CF2")
        gen = PresetGenerator()
        # 5~9 peer → -0.1
        score = gen._calc_confidence(7, stock)
        assert score == pytest.approx(0.9)

    def test_confidence_drop_with_few_peers(self):
        stock = _make_stock("CF3")
        gen = PresetGenerator()
        # < 5 peer → -0.3
        score = gen._calc_confidence(3, stock)
        assert score == pytest.approx(0.7)

    def test_confidence_special_industry_penalty(self):
        stock = _make_stock("CF4", industry="Banks")
        IndustryClassification.objects.get_or_create(
            industry="Banks",
            defaults={'handling_mode': 'special', 'sector': 'Financial Services'},
        )
        gen = PresetGenerator()
        # 20 peer → 1.0 - 0.15 = 0.85
        score = gen._calc_confidence(20, stock)
        assert score == pytest.approx(0.85)

    def test_confidence_clamped_to_zero_floor(self):
        stock = _make_stock("CF5", industry="Banks")
        IndustryClassification.objects.get_or_create(
            industry="Banks",
            defaults={'handling_mode': 'special', 'sector': 'Financial Services'},
        )
        gen = PresetGenerator()
        # 3 peer + special → 1 - 0.3 - 0.15 = 0.55
        score = gen._calc_confidence(3, stock)
        assert score == pytest.approx(0.55)


@pytest.mark.django_db
class TestPresetGenerateForSymbolFocused:
    """generate_for_symbol 전반 동작."""

    def test_stock_not_found_returns_error_dict(self):
        gen = PresetGenerator()
        result = gen.generate_for_symbol("DOES_NOT_EXIST")
        assert result['error'] == 'Stock not found'
        assert result['symbol'] == 'DOES_NOT_EXIST'

    def test_symbol_is_uppercased(self):
        gen = PresetGenerator()
        result = gen.generate_for_symbol("ghost_lowercase")
        # Stock 없으므로 error 경로지만 symbol 자체는 upper로
        assert result['symbol'] == 'GHOST_LOWERCASE'

    def test_no_sector_no_industry_returns_zero_presets(self):
        """sector/industry 둘 다 없으면 어떤 프리셋도 생성되지 않음."""
        stock = _make_stock("NOSEC", sector=None, industry=None)
        gen = PresetGenerator()
        result = gen.generate_for_symbol("NOSEC")
        # presets_created 0 (단, error 없이 정상 반환)
        assert 'error' not in result
        assert result.get('presets_created', 0) == 0


# ===========================================================================
# benchmark_calculator — focused
# ===========================================================================


class TestAssignSizeBucketBoundaryFocused:
    """assign_size_bucket — 경계 값 동작."""

    def test_exactly_200b_is_mega(self):
        assert assign_size_bucket(200_000_000_000) == 'mega'

    def test_just_below_200b_is_large(self):
        assert assign_size_bucket(199_999_999_999) == 'large'

    def test_exactly_10b_is_large(self):
        assert assign_size_bucket(10_000_000_000) == 'large'

    def test_just_below_10b_is_mid(self):
        assert assign_size_bucket(9_999_999_999) == 'mid'

    def test_exactly_2b_is_mid(self):
        assert assign_size_bucket(2_000_000_000) == 'mid'

    def test_just_below_2b_is_small(self):
        assert assign_size_bucket(1_999_999_999) == 'small'

    def test_negative_market_cap_falls_to_small(self):
        # 음수는 small (< 2B)로 분류
        assert assign_size_bucket(-1_000_000) == 'small'

    def test_zero_market_cap_falls_to_small(self):
        assert assign_size_bucket(0) == 'small'


class TestGetAdjacentBucketsFocused:
    """get_adjacent_buckets — 인접 bucket 슬라이딩 윈도우."""

    def test_mega_returns_self_and_large(self):
        adj = get_adjacent_buckets('mega')
        assert 'mega' in adj
        assert 'large' in adj
        assert 'small' not in adj

    def test_small_returns_self_and_mid(self):
        adj = get_adjacent_buckets('small')
        assert 'small' in adj
        assert 'mid' in adj
        assert 'mega' not in adj

    def test_mid_returns_three(self):
        adj = get_adjacent_buckets('mid')
        assert set(adj) == {'small', 'mid', 'large'}

    def test_unknown_bucket_defaults_to_mid_window(self):
        # idx default = 2 → ['mid', 'large', 'mega']
        adj = get_adjacent_buckets('unknown_bucket_label')
        assert 'mid' in adj


@pytest.mark.django_db
class TestBenchmarkDetermineConfidenceFocused:
    def setup_method(self):
        self.calc = BenchmarkCalculator()

    def test_high_requires_industry_size_basis(self):
        # peer 20 이지만 sector basis면 high가 아닌 medium
        assert self.calc._determine_confidence(20, 'sector') == 'medium'

    def test_high_with_industry_size_and_15_peers(self):
        assert self.calc._determine_confidence(15, 'industry_size') == 'high'

    def test_medium_at_boundary_8(self):
        assert self.calc._determine_confidence(8, 'industry_size') == 'medium'

    def test_low_at_boundary_4(self):
        assert self.calc._determine_confidence(4, 'industry_size') == 'low'

    def test_limited_below_4(self):
        assert self.calc._determine_confidence(3, 'industry_size') == 'limited'

    def test_zero_peer_limited(self):
        assert self.calc._determine_confidence(0, 'sector') == 'limited'


@pytest.mark.django_db
class TestBenchmarkSymbolNotFoundFocused:
    def test_returns_error_when_stock_missing(self):
        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbol("MISSING_SYMBOL_XYZ")
        assert result['error'] == 'Stock not found'

    def test_symbol_uppercased_in_lookup(self):
        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbol("lower_ghost")
        assert result['symbol'] == 'LOWER_GHOST'


@pytest.mark.django_db
class TestBenchmarkAvailableYearsFocused:
    def test_returns_recent_5_years(self):
        _make_stock("AVY1")
        for fy in [2018, 2019, 2020, 2021, 2022, 2023, 2024]:
            _make_snapshot("AVY1", fy, 'gross_margin', 0.4)

        calc = BenchmarkCalculator()
        years = calc._get_available_years("AVY1")

        assert len(years) == 5
        assert years[0] == 2024  # 최신순
        assert years[-1] == 2020

    def test_no_snapshots_returns_empty(self):
        _make_stock("AVY2")
        calc = BenchmarkCalculator()
        years = calc._get_available_years("AVY2")
        assert years == []


# ===========================================================================
# metric_calculator — focused
# ===========================================================================


class TestSafeHelpersExtraFocused:
    """_safe/_safe_nonzero/_div — 보강 케이스."""

    def test_safe_with_negative_float(self):
        assert _safe(-3.14) == pytest.approx(-3.14)

    def test_safe_with_bool_true_returns_one(self):
        # bool은 int 서브클래스라 float 변환 가능
        assert _safe(True) == 1.0

    def test_safe_nonzero_negative_returns_value(self):
        assert _safe_nonzero(-100) == -100.0

    def test_div_negative_denominator(self):
        assert _div(10, -2) == pytest.approx(-5.0)

    def test_div_negative_numerator(self):
        assert _div(-10, 2) == pytest.approx(-5.0)

    def test_div_decimal_inputs(self):
        assert _div(Decimal("9"), Decimal("3")) == pytest.approx(3.0)


class TestMetricRoicFocused:
    def test_zero_invested_capital_returns_missing(self):
        calc = MetricCalculator()
        inc = _mock_income(operating_income=25_000_000_000)
        bal = _mock_balance(total_shareholder_equity=0, long_term_debt=0)
        val, status, _ = calc._calc_roic(inc, bal)
        # equity가 0이면 _safe(0)==0.0, 그러나 invested_capital==0 분기
        # equity가 None 처리되어 missing
        assert status == 'missing'

    def test_roic_uses_default_tax_rate_when_no_tax_data(self):
        calc = MetricCalculator()
        inc = _mock_income(
            operating_income=10_000_000_000,
            income_tax_expense=None,
            income_before_tax=None,
        )
        bal = _mock_balance(total_shareholder_equity=50_000_000_000, long_term_debt=0)
        val, status, _ = calc._calc_roic(inc, bal)
        # NOPAT = 10B × (1 - 0.21) = 7.9B, IC = 50B → 0.158
        assert status == 'normal'
        assert val == pytest.approx(0.158, rel=1e-3)


class TestMetricNetDebtEbitdaFocused:
    def test_normal(self):
        calc = MetricCalculator()
        inc = _mock_income(ebitda=10_000_000_000)
        bal = _mock_balance(
            short_term_debt=5_000_000_000,
            long_term_debt=15_000_000_000,
            cash_and_cash_equivalents_at_carrying_value=4_000_000_000,
        )
        val, status, _ = calc._calc_net_debt_ebitda(bal, inc)
        # (5 + 15 - 4) / 10 = 1.6
        assert status == 'normal'
        assert val == pytest.approx(1.6)

    def test_zero_ebitda_returns_missing(self):
        calc = MetricCalculator()
        inc = _mock_income(ebitda=0)
        bal = _mock_balance()
        val, status, _ = calc._calc_net_debt_ebitda(bal, inc)
        assert status == 'missing'

    def test_net_cash_position_yields_negative(self):
        calc = MetricCalculator()
        inc = _mock_income(ebitda=10_000_000_000)
        bal = _mock_balance(
            short_term_debt=1_000_000_000,
            long_term_debt=2_000_000_000,
            cash_and_cash_equivalents_at_carrying_value=50_000_000_000,
        )
        val, status, _ = calc._calc_net_debt_ebitda(bal, inc)
        # 순현금 → 음수
        assert val < 0


class TestMetricCashRunwayFocused:
    def test_positive_ocf_is_not_applicable(self):
        calc = MetricCalculator()
        bal = _mock_balance()
        cf = _mock_cashflow(operating_cashflow=10_000_000_000)
        val, status, _ = calc._calc_cash_runway(bal, cf)
        assert status == 'not_applicable'

    def test_negative_ocf_normal_runway(self):
        calc = MetricCalculator()
        bal = _mock_balance(cash_and_cash_equivalents_at_carrying_value=12_000_000_000)
        cf = _mock_cashflow(operating_cashflow=-4_000_000_000)
        val, status, _ = calc._calc_cash_runway(bal, cf)
        assert status == 'normal'
        assert val == pytest.approx(3.0)  # 12B / 4B = 3년

    def test_missing_ocf_returns_missing(self):
        calc = MetricCalculator()
        bal = _mock_balance()
        cf = _mock_cashflow(operating_cashflow=None)
        val, status, _ = calc._calc_cash_runway(bal, cf)
        assert status == 'missing'


class TestMetricShortTermDebtPctFocused:
    def test_normal_split(self):
        calc = MetricCalculator()
        bal = _mock_balance(short_term_debt=2_500_000_000, long_term_debt=7_500_000_000)
        val, status, _ = calc._calc_short_term_debt_pct(bal)
        assert status == 'normal'
        assert val == pytest.approx(0.25)

    def test_no_debt_returns_missing(self):
        calc = MetricCalculator()
        bal = _mock_balance(short_term_debt=0, long_term_debt=0)
        val, status, _ = calc._calc_short_term_debt_pct(bal)
        assert status == 'missing'


class TestMetricCapexToOcfFocused:
    def test_normal_capex_ratio(self):
        calc = MetricCalculator()
        cf = _mock_cashflow(
            operating_cashflow=20_000_000_000,
            capital_expenditures=-5_000_000_000,
        )
        val, status, _ = calc._calc_capex_to_ocf(cf)
        assert status == 'normal'
        assert val == pytest.approx(0.25)

    def test_uses_abs_for_capex(self):
        calc = MetricCalculator()
        cf = _mock_cashflow(
            operating_cashflow=10_000_000_000,
            capital_expenditures=4_000_000_000,  # 양수로 들어와도 abs
        )
        val, status, _ = calc._calc_capex_to_ocf(cf)
        assert val == pytest.approx(0.4)


class TestMetricAccrualsFocused:
    def test_normal_accruals(self):
        calc = MetricCalculator()
        inc = _mock_income(net_income=20_000_000_000)
        cf = _mock_cashflow(operating_cashflow=15_000_000_000)
        bal = _mock_balance(total_assets=100_000_000_000)
        val, status, _ = calc._calc_accruals(inc, cf, bal)
        # (20 - 15) / 100 = 0.05
        assert status == 'normal'
        assert val == pytest.approx(0.05)

    def test_missing_when_assets_none(self):
        calc = MetricCalculator()
        inc = _mock_income(net_income=20_000_000_000)
        cf = _mock_cashflow(operating_cashflow=15_000_000_000)
        bal = _mock_balance(total_assets=None)
        val, status, _ = calc._calc_accruals(inc, cf, bal)
        assert status == 'missing'


class TestMetricFcfConversionFocused:
    def test_normal_conversion(self):
        calc = MetricCalculator()
        inc = _mock_income(net_income=10_000_000_000)
        cf = _mock_cashflow(
            operating_cashflow=12_000_000_000,
            capital_expenditures=-2_000_000_000,
        )
        val, status, _ = calc._calc_fcf_conversion(cf, inc)
        # FCF = 12 - 2 = 10, /NI 10 = 1.0
        assert status == 'normal'
        assert val == pytest.approx(1.0)

    def test_zero_net_income_returns_missing(self):
        calc = MetricCalculator()
        inc = _mock_income(net_income=0)
        cf = _mock_cashflow()
        val, status, _ = calc._calc_fcf_conversion(cf, inc)
        assert status == 'missing'


class TestMetricDilutionFocused:
    def test_normal_dilution_3y(self):
        calc = MetricCalculator()
        bal = _mock_balance(common_stock_shares_outstanding=1_100_000_000)
        prev = _mock_balance(common_stock_shares_outstanding=1_000_000_000)
        val, status, _ = calc._calc_dilution_3y(bal, prev)
        # (1.1B - 1.0B) / 1.0B = 0.1
        assert status == 'normal'
        assert val == pytest.approx(0.1)

    def test_no_prev_returns_missing(self):
        calc = MetricCalculator()
        bal = _mock_balance(common_stock_shares_outstanding=1_000_000_000)
        val, status, _ = calc._calc_dilution_3y(bal, None)
        assert status == 'missing'

    def test_share_buyback_negative_dilution(self):
        calc = MetricCalculator()
        bal = _mock_balance(common_stock_shares_outstanding=900_000_000)
        prev = _mock_balance(common_stock_shares_outstanding=1_000_000_000)
        val, status, _ = calc._calc_dilution_3y(bal, prev)
        assert val < 0  # 자사주매입 효과


class TestMetricShareholderYieldFocused:
    def test_normal_yield(self):
        calc = MetricCalculator()
        stock = SimpleNamespace(market_capitalization=Decimal("100000000000"))
        cf = _mock_cashflow(
            dividend_payout=-2_000_000_000,
            payments_for_repurchase_of_common_stock=-3_000_000_000,
            proceeds_from_issuance_of_common_stock=1_000_000_000,
        )
        val, status, _ = calc._calc_shareholder_yield(cf, stock)
        # (2 + 3 - 1) / 100 = 0.04
        assert status == 'normal'
        assert val == pytest.approx(0.04)

    def test_missing_when_no_mcap(self):
        calc = MetricCalculator()
        stock = SimpleNamespace(market_capitalization=None)
        cf = _mock_cashflow()
        val, status, _ = calc._calc_shareholder_yield(cf, stock)
        assert status == 'missing'


class TestMetricValuationFocused:
    def test_pe_passthrough(self):
        calc = MetricCalculator()
        stock = SimpleNamespace(pe_ratio=Decimal("18.5"))
        val, status, _ = calc._calc_pe(stock)
        assert status == 'normal'
        assert val == pytest.approx(18.5)

    def test_pe_missing(self):
        calc = MetricCalculator()
        stock = SimpleNamespace(pe_ratio=None)
        val, status, _ = calc._calc_pe(stock)
        assert status == 'missing'

    def test_ev_ebitda_normal(self):
        calc = MetricCalculator()
        stock = SimpleNamespace(market_capitalization=Decimal("100000000000"))
        inc = _mock_income(ebitda=10_000_000_000)
        val, status, _ = calc._calc_ev_ebitda(stock, inc)
        assert status == 'normal'
        assert val == pytest.approx(10.0)

    def test_ev_ebitda_zero_ebitda_missing(self):
        calc = MetricCalculator()
        stock = SimpleNamespace(market_capitalization=Decimal("100000000000"))
        inc = _mock_income(ebitda=0)
        val, status, _ = calc._calc_ev_ebitda(stock, inc)
        assert status == 'missing'

    def test_fcf_yield_normal(self):
        calc = MetricCalculator()
        stock = SimpleNamespace(market_capitalization=Decimal("100000000000"))
        cf = _mock_cashflow(
            operating_cashflow=15_000_000_000,
            capital_expenditures=-5_000_000_000,
        )
        val, status, _ = calc._calc_fcf_yield(cf, stock)
        # FCF = 10B, / mcap 100B = 0.1
        assert status == 'normal'
        assert val == pytest.approx(0.1)


@pytest.mark.django_db
class TestMetricCalculatorBatchFocused:
    def test_calculate_for_symbol_stock_not_found(self):
        calc = MetricCalculator()
        result = calc.calculate_for_symbol("UNREAL_XYZ")
        assert result['error'] == 'Stock not found'

    def test_calculate_for_symbol_no_financials_returns_error(self):
        _make_stock("NOFIN")
        calc = MetricCalculator()
        with patch.object(calc.fetcher, 'get_financial_data', return_value={}):
            result = calc.calculate_for_symbol("NOFIN")
        assert result['error'] == 'No financial data'


# ===========================================================================
# relative_metrics — focused
# ===========================================================================


@pytest.mark.django_db
class TestRelativeMetricsFocused:
    def test_no_stock_returns_false(self):
        calc = RelativeMetricCalculator()
        assert calc._calc_rev_growth_vs_industry("NOTHERE") is False

    def test_no_industry_returns_false(self):
        _make_stock("NOIND", industry=None)
        calc = RelativeMetricCalculator()
        assert calc._calc_rev_growth_vs_industry("NOIND") is False

    def test_no_company_snapshot_returns_false(self):
        _make_stock("REL1", industry="Software")
        calc = RelativeMetricCalculator()
        assert calc._calc_rev_growth_vs_industry("REL1") is False

    def test_no_industry_benchmark_skipped(self):
        _make_stock("REL2", industry="Software")
        _make_snapshot("REL2", 2024, 'revenue_growth_yoy', 0.15)
        # IndustryMetricBenchmark 없음
        calc = RelativeMetricCalculator()
        # snapshot이 있어도 industry benchmark가 없으면 updated_at은 False로 남음
        result = calc._calc_rev_growth_vs_industry("REL2")
        assert result is False

    def test_positive_relative_growth_persisted(self):
        _make_stock("REL3", industry="Software")
        _make_snapshot("REL3", 2024, 'revenue_growth_yoy', 0.20)
        # rev_growth_vs_industry MetricDefinition도 미리 생성 (FK 제약)
        _make_metric_def('rev_growth_vs_industry', category='growth')
        md = _make_metric_def('revenue_growth_yoy', category='growth')
        IndustryMetricBenchmark.objects.create(
            industry="Software",
            fiscal_year=2024,
            metric_code=md,
            p25_value=Decimal("0.05"),
            median_value=Decimal("0.10"),
            p75_value=Decimal("0.15"),
            sample_count=20,
            benchmark_confidence='high',
        )

        calc = RelativeMetricCalculator()
        assert calc._calc_rev_growth_vs_industry("REL3") is True

        # rev_growth_vs_industry snapshot 생성 확인
        snap = CompanyMetricSnapshot.objects.filter(
            symbol_id="REL3", fiscal_year=2024,
            metric_code_id='rev_growth_vs_industry',
        ).first()
        assert snap is not None
        assert float(snap.metric_value) == pytest.approx(0.10)  # 0.20 - 0.10

    def test_batch_with_empty_symbol_list(self):
        calc = RelativeMetricCalculator()
        result = calc.calculate_for_symbols(symbols=[])
        assert result['total'] == 0
        assert result['success'] == 0
        assert result['skip'] == 0

    def test_batch_handles_individual_failure(self):
        calc = RelativeMetricCalculator()
        # 한 종목은 존재하지 않음 → skip
        result = calc.calculate_for_symbols(symbols=["NONEXISTENT_AAA"])
        assert result['total'] == 1
        assert result['skip'] == 1


# ===========================================================================
# interpretation — focused
# ===========================================================================


class TestInterpretationSummaryFocused:
    @staticmethod
    def _sig(category, signal, score=50.0):
        return SimpleNamespace(category=category, signal=signal, score=score)

    def test_empty_signals_neutral_message(self):
        text = generate_summary_text([])
        assert '중립' in text or '없음' in text

    def test_mixed_yellow_only_no_strong_message(self):
        sigs = [self._sig('profitability', 'yellow', 50)]
        text = generate_summary_text(sigs)
        # green/red 없음 → 중립 메시지
        assert text  # 비어있지 않음

    def test_top_2_greens_ordered_by_score(self):
        sigs = [
            self._sig('profitability', 'green', 60),
            self._sig('growth', 'green', 90),
            self._sig('valuation', 'green', 70),
        ]
        text = generate_summary_text(sigs)
        # 가장 높은 점수 카테고리(성장성)가 먼저
        assert '성장성' in text


class TestInterpretationMetricFocused:
    def test_missing_status_returns_no_data_msg(self):
        text = generate_metric_interpretation(
            metric_code='gross_margin', higher_is_better=True,
            percentile_rank=None, trend='',
            value_status='missing', benchmark_confidence='high',
        )
        assert '데이터가 제공되지 않' in text

    def test_not_applicable_with_custom_reason(self):
        text = generate_metric_interpretation(
            metric_code='cash_runway_years', higher_is_better=False,
            percentile_rank=None, trend='',
            value_status='not_applicable', benchmark_confidence='medium',
            not_applicable_reason='흑자 기업',
        )
        assert '흑자 기업' in text

    def test_not_applicable_no_reason_falls_back(self):
        text = generate_metric_interpretation(
            metric_code='x', higher_is_better=False,
            percentile_rank=None, trend='',
            value_status='not_applicable', benchmark_confidence='medium',
        )
        assert '해당 없음' in text

    def test_high_percentile_with_improving_trend(self):
        text = generate_metric_interpretation(
            metric_code='roe', higher_is_better=True,
            percentile_rank=92.0, trend='improving',
            value_status='normal', benchmark_confidence='high',
        )
        assert '상위' in text
        assert '개선' in text

    def test_unstable_warning_appended(self):
        text = generate_metric_interpretation(
            metric_code='interest_coverage', higher_is_better=True,
            percentile_rank=50.0, trend='',
            value_status='unstable', benchmark_confidence='medium',
        )
        assert '변동' in text

    def test_limited_confidence_warns(self):
        text = generate_metric_interpretation(
            metric_code='gm', higher_is_better=True,
            percentile_rank=50.0, trend='',
            value_status='normal', benchmark_confidence='limited',
        )
        assert '표본' in text or '주의' in text

    def test_lower_is_better_direction_text(self):
        text = generate_metric_interpretation(
            metric_code='debt_to_equity', higher_is_better=False,
            percentile_rank=50.0, trend='stable',
            value_status='normal', benchmark_confidence='high',
        )
        assert '낮을수록' in text


class TestDetermineTrendBoundaryFocused:
    def test_exactly_5_percent_up_not_improving(self):
        # 임계값은 strictly greater than (× 1.05)
        # 100 → 105 정확히 5%면 improving이 아님
        assert determine_trend([100.0, 102.0, 105.0]) == 'stable'

    def test_just_above_5_percent_improving(self):
        assert determine_trend([100.0, 103.0, 106.0]) == 'improving'

    def test_just_below_5_percent_down_declining(self):
        assert determine_trend([100.0, 97.0, 94.0]) == 'declining'

    def test_uses_only_last_three_values(self):
        # 처음 4개 무시, 마지막 3개로만 판정
        history = [200.0, 180.0, 100.0, 110.0, 120.0]
        # 마지막 3개: 100 → 120 → improving
        assert determine_trend(history) == 'improving'


class TestLeaderSummaryFocused:
    def test_empty_returns_no_data_message(self):
        text = generate_leader_summary([], [])
        assert '부족' in text

    def test_advantages_count_in_text(self):
        adv = [{'category': 'profitability'}, {'category': 'growth'}]
        dis = [{'category': 'valuation'}]
        text = generate_leader_summary(adv, dis)
        # "3개 비교 지표 중 2개 우위" 형태
        assert '3개' in text
        assert '2개' in text

    def test_de_dupes_categories(self):
        adv = [
            {'category': 'profitability'},
            {'category': 'profitability'},
            {'category': 'growth'},
        ]
        text = generate_leader_summary(adv, [])
        # 수익성, 성장성 — 중복 제거되어 두 번 등장하지 않아야 함
        assert text.count('수익성') == 1
        assert '성장성' in text
