"""
validation 서비스 보강 단위 테스트

기존 test_preset_generator.py / test_benchmark_calculator.py /
test_metric_calculator.py / test_relative_metrics.py /
test_interpretation.py 가 다루지 않은 edge case + 분기 보강.

대상:
  - PresetGenerator (preset_generator.py)
  - BenchmarkCalculator (benchmark_calculator.py)
  - MetricCalculator (metric_calculator.py)
  - RelativeMetricCalculator (relative_metrics.py)
  - interpretation 모듈 (interpretation.py)
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from stocks.models import Stock, SP500Constituent, IndustryClassification
from validation.models import PeerPreset
from validation.services import (
    benchmark_calculator as bc_mod,
    preset_generator as pg_mod,
)
from validation.services.benchmark_calculator import (
    BenchmarkCalculator,
    assign_size_bucket,
    get_adjacent_buckets,
    SIZE_BUCKETS,
)
from validation.services.interpretation import (
    determine_trend,
    generate_leader_summary,
    generate_metric_interpretation,
    generate_summary_text,
)
from validation.services.metric_calculator import (
    MetricCalculator,
    _div,
    _safe,
    _safe_nonzero,
)
from validation.services.preset_generator import PresetGenerator
from validation.services.relative_metrics import RelativeMetricCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stock(symbol="AAPL", sector="Technology",
                industry="Consumer Electronics", market_cap=3_000_000_000_000):
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


def _make_sp500(symbol, sector="Technology", is_active=True):
    return SP500Constituent.objects.get_or_create(
        symbol=symbol,
        defaults={
            'company_name': f'{symbol} Corp',
            'sector': sector,
            'is_active': is_active,
        },
    )[0]


def _make_signal(category, signal, score=50):
    """CategorySignal mock."""
    return SimpleNamespace(category=category, signal=signal, score=score)


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


# ---------------------------------------------------------------------------
# PresetGenerator 보강
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPresetGeneratorBatch:
    def test_generate_for_symbols_with_explicit_list(self):
        """명시적 symbols 리스트가 주어지면 그대로 사용."""
        _make_stock("AAA", market_cap=5_000_000_000)
        gen = PresetGenerator()
        r = gen.generate_for_symbols(["AAA"])
        assert r['total'] == 1
        # peer가 없어 0건이어도 정상 종료
        assert r['success'] in (0, 1)

    def test_generate_for_symbols_default_uses_sp500(self):
        """symbols=None → SP500 활성 종목 사용."""
        _make_stock("BBB", market_cap=5_000_000_000)
        _make_sp500("BBB")
        gen = PresetGenerator()
        r = gen.generate_for_symbols()
        assert r['total'] >= 1

    def test_generate_for_symbols_swallows_exception(self):
        """generate_for_symbol에서 예외 발생해도 카운트만 처리."""
        gen = PresetGenerator()
        with patch.object(gen, 'generate_for_symbol', side_effect=RuntimeError("boom")):
            r = gen.generate_for_symbols(["NOPE"])
        assert r['total'] == 1
        assert r['success'] == 0


@pytest.mark.django_db
class TestPresetCalcConfidence:
    def test_confidence_full_score_when_many_peers(self):
        stock = _make_stock("CFG", market_cap=5_000_000_000)
        gen = PresetGenerator()
        assert gen._calc_confidence(20, stock) == pytest.approx(1.0)

    def test_confidence_minus_010_when_peer_count_below_10(self):
        stock = _make_stock("CFG2", market_cap=5_000_000_000)
        gen = PresetGenerator()
        # 5 <= peer_count < 10
        assert gen._calc_confidence(7, stock) == pytest.approx(0.9)

    def test_confidence_minus_030_when_peer_count_below_5(self):
        stock = _make_stock("CFG3", market_cap=5_000_000_000)
        gen = PresetGenerator()
        assert gen._calc_confidence(3, stock) == pytest.approx(0.7)

    def test_confidence_special_industry_penalty(self):
        stock = _make_stock("CFG4", industry="Banks", market_cap=5_000_000_000)
        IndustryClassification.objects.get_or_create(
            industry="Banks",
            defaults={'handling_mode': 'special'},
        )
        gen = PresetGenerator()
        # peer_count 20 → 1.0, - 0.15 = 0.85
        assert gen._calc_confidence(20, stock) == pytest.approx(0.85)

    def test_confidence_floor_zero(self):
        """패널티 누적해도 0 이하로 떨어지지 않음."""
        stock = _make_stock("CFG5", industry="Banks", market_cap=5_000_000_000)
        IndustryClassification.objects.get_or_create(
            industry="Banks", defaults={'handling_mode': 'special'}
        )
        gen = PresetGenerator()
        # peer<5(-0.3) + special(-0.15) = 0.55
        v = gen._calc_confidence(1, stock)
        assert 0.0 <= v <= 1.0


@pytest.mark.django_db
class TestPresetFilterBySizeBuckets:
    def test_filter_by_size_mega(self):
        _make_stock("M1", market_cap=300_000_000_000)
        gen = PresetGenerator()
        qs = gen._filter_by_size(Stock.objects.all(), ['mega'])
        assert qs.filter(symbol='M1').exists()

    def test_filter_by_size_mid_excludes_large(self):
        _make_stock("MID", market_cap=5_000_000_000)
        _make_stock("LRG", market_cap=50_000_000_000)
        gen = PresetGenerator()
        qs = gen._filter_by_size(Stock.objects.all(), ['mid'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert 'MID' in symbols
        assert 'LRG' not in symbols

    def test_filter_by_size_small_only(self):
        _make_stock("S1", market_cap=500_000_000)
        _make_stock("MID2", market_cap=5_000_000_000)
        gen = PresetGenerator()
        qs = gen._filter_by_size(Stock.objects.all(), ['small'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert 'S1' in symbols
        assert 'MID2' not in symbols

    def test_filter_by_size_unknown_bucket_returns_all(self):
        """알 수 없는 bucket → 빈 Q() → 모든 종목 통과 (현 구현 동작)."""
        _make_stock("ANY", market_cap=5_000_000_000)
        gen = PresetGenerator()
        before = Stock.objects.all().count()
        qs = gen._filter_by_size(Stock.objects.all(), ['unknown'])
        assert qs.count() == before


@pytest.mark.django_db
class TestPresetSizePeersGuards:
    def test_size_peers_skipped_when_no_sector(self):
        stock = _make_stock("NS1", sector="", market_cap=300_000_000_000)
        gen = PresetGenerator()
        n = gen._generate_size_peers(stock, Stock.objects.all(), 'mega')
        assert n == 0

    def test_size_peers_returns_zero_when_under_min(self):
        """peer < 3이면 size_peers 생성 안 함."""
        stock = _make_stock("NS2", market_cap=300_000_000_000)
        # 자기 자신만 있음 → peer 0
        gen = PresetGenerator()
        base = Stock.objects.exclude(symbol='NS2')
        n = gen._generate_size_peers(stock, base, 'mega')
        assert n == 0


# ---------------------------------------------------------------------------
# BenchmarkCalculator 보강
# ---------------------------------------------------------------------------

class TestSizeBucketPureFunc:
    def test_assign_size_bucket_none(self):
        assert assign_size_bucket(None) == 'mid'

    def test_assign_size_bucket_mega_exact_boundary(self):
        assert assign_size_bucket(200_000_000_000) == 'mega'

    def test_assign_size_bucket_large_just_below_mega(self):
        assert assign_size_bucket(199_999_999_999) == 'large'

    def test_assign_size_bucket_small(self):
        assert assign_size_bucket(1_000_000_000) == 'small'

    def test_get_adjacent_buckets_mid(self):
        adj = get_adjacent_buckets('mid')
        assert 'small' in adj and 'mid' in adj and 'large' in adj

    def test_get_adjacent_buckets_small_no_underflow(self):
        adj = get_adjacent_buckets('small')
        assert adj[0] == 'small'
        assert 'mid' in adj

    def test_get_adjacent_buckets_unknown_defaults_to_mid(self):
        adj = get_adjacent_buckets('xyz')
        # unknown → idx=2 (large) → ['mid','large','mega']
        assert 'large' in adj

    def test_size_buckets_order(self):
        assert SIZE_BUCKETS == ['small', 'mid', 'large', 'mega']


@pytest.mark.django_db
class TestBenchmarkCalcGuards:
    def test_calculate_for_symbol_stock_missing(self):
        calc = BenchmarkCalculator()
        r = calc.calculate_for_symbol("NOEXIST")
        assert r['error'] == 'Stock not found'

    def test_determine_confidence_levels(self):
        calc = BenchmarkCalculator()
        assert calc._determine_confidence(20, 'industry_size') == 'high'
        assert calc._determine_confidence(10, 'industry') == 'medium'
        assert calc._determine_confidence(5, 'sector') == 'low'
        assert calc._determine_confidence(2, 'sector') == 'limited'

    def test_determine_confidence_not_high_for_non_industry_size(self):
        """basis가 industry_size가 아니면 high가 아님."""
        calc = BenchmarkCalculator()
        assert calc._determine_confidence(20, 'sector') == 'medium'

    def test_calculate_for_symbols_handles_exception(self):
        calc = BenchmarkCalculator()
        with patch.object(calc, 'calculate_for_symbol', side_effect=ValueError("nope")):
            r = calc.calculate_for_symbols(['X'])
        assert r['errors'] == 1
        assert r['success'] == 0

    def test_calculate_for_symbols_with_error_dict(self):
        calc = BenchmarkCalculator()
        with patch.object(calc, 'calculate_for_symbol',
                          return_value={'error': 'Stock not found'}):
            r = calc.calculate_for_symbols(['ZZZ'])
        assert r['errors'] == 1
        assert r['error_details'][0]['symbol'] == 'ZZZ'


# ---------------------------------------------------------------------------
# MetricCalculator 보강
# ---------------------------------------------------------------------------

class TestSafeHelpersBoundary:
    def test_safe_decimal_input(self):
        assert _safe(Decimal("12.5")) == 12.5

    def test_safe_zero_preserved(self):
        assert _safe(0) == 0

    def test_safe_handles_non_numeric_string(self):
        assert _safe("abc") is None

    def test_safe_nonzero_returns_none_for_zero(self):
        assert _safe_nonzero(0) is None

    def test_safe_nonzero_returns_none_for_none(self):
        assert _safe_nonzero(None) is None

    def test_div_none_numerator(self):
        assert _div(None, 5) is None

    def test_div_zero_denominator(self):
        assert _div(5, 0) is None

    def test_div_normal(self):
        assert _div(10, 4) == 2.5


class TestMetricCalcFunctions:
    def setup_method(self):
        self.mc = MetricCalculator()

    def test_calc_ratio_normal(self):
        v, status, _ = self.mc._calc_ratio(10, 2)
        assert v == 5.0
        assert status == 'normal'

    def test_calc_ratio_zero_denominator_missing(self):
        v, status, reason = self.mc._calc_ratio(10, 0)
        assert v is None
        assert status == 'missing'
        assert reason

    def test_calc_growth_normal_positive(self):
        v, status, _ = self.mc._calc_growth(110, 100)
        assert v == pytest.approx(0.1)
        assert status == 'normal'

    def test_calc_growth_small_prev_missing(self):
        v, status, _ = self.mc._calc_growth(100, 0.5)
        assert v is None
        assert status == 'missing'

    def test_calc_growth_negative_prev_uses_abs(self):
        v, _, _ = self.mc._calc_growth(50, -100)
        # (50 - (-100)) / 100 = 1.5
        assert v == pytest.approx(1.5)

    def test_calc_roic_default_tax_rate_when_missing_tax(self):
        inc = _mock_income(income_tax_expense=None, income_before_tax=None)
        bal = _mock_balance()
        v, status, _ = self.mc._calc_roic(inc, bal)
        assert status == 'normal'
        # NOPAT = op_income * (1 - 0.21); invested = equity + long_debt
        expected = (25_000_000_000 * 0.79) / (150_000_000_000 + 50_000_000_000)
        assert v == pytest.approx(expected)

    def test_calc_roic_tax_rate_clamped_at_one(self):
        """tax_expense > income_before_tax 이면 tax_rate = 1 → NOPAT=0."""
        inc = _mock_income(income_tax_expense=100, income_before_tax=50)
        bal = _mock_balance()
        v, status, _ = self.mc._calc_roic(inc, bal)
        assert status == 'normal'
        assert v == pytest.approx(0.0)

    def test_calc_roic_invested_capital_zero_missing(self):
        inc = _mock_income()
        bal = _mock_balance(total_shareholder_equity=0, long_term_debt=0)
        v, status, _ = self.mc._calc_roic(inc, bal)
        assert v is None
        assert status == 'missing'

    def test_calc_debt_to_equity_no_equity(self):
        bal = _mock_balance(total_shareholder_equity=0)
        v, status, _ = self.mc._calc_debt_to_equity(bal)
        assert v is None
        assert status == 'missing'

    def test_calc_interest_coverage_no_debt(self):
        inc = _mock_income(interest_expense=0)
        bal = _mock_balance(short_term_debt=0, long_term_debt=0)
        v, status, _ = self.mc._calc_interest_coverage(inc, bal, None)
        assert v is None
        assert status == 'not_applicable'

    def test_calc_interest_coverage_unstable_flip(self):
        # 조건: 부호반전 + abs(val) > abs(prev_val) * 10 (strictly greater)
        inc = _mock_income(operating_income=20, interest_expense=1)   # ratio=20 양수
        prev = _mock_income(operating_income=-1, interest_expense=1)  # ratio=-1 음수
        bal = _mock_balance(short_term_debt=100, long_term_debt=0)
        v, status, _ = self.mc._calc_interest_coverage(inc, bal, prev)
        assert v == pytest.approx(20)
        assert status == 'unstable'

    def test_calc_interest_coverage_normal_when_flip_small(self):
        """부호반전이어도 변동폭이 10배 이하면 normal."""
        inc = _mock_income(operating_income=5, interest_expense=1)
        prev = _mock_income(operating_income=-1, interest_expense=1)
        bal = _mock_balance(short_term_debt=100, long_term_debt=0)
        v, status, _ = self.mc._calc_interest_coverage(inc, bal, prev)
        assert v == pytest.approx(5)
        assert status == 'normal'

    def test_calc_cash_runway_profitable_not_applicable(self):
        cf = _mock_cashflow(operating_cashflow=100)  # 흑자
        bal = _mock_balance()
        v, status, _ = self.mc._calc_cash_runway(bal, cf)
        assert v is None
        assert status == 'not_applicable'

    def test_calc_cash_runway_negative_ocf_normal(self):
        cf = _mock_cashflow(operating_cashflow=-100)
        bal = _mock_balance(cash_and_cash_equivalents_at_carrying_value=500)
        v, status, _ = self.mc._calc_cash_runway(bal, cf)
        assert status == 'normal'
        assert v == pytest.approx(5.0)

    def test_calc_inventory_days_service_not_applicable(self):
        bal = _mock_balance(inventory=0)
        inc = _mock_income()
        v, status, _ = self.mc._calc_inventory_days(bal, inc)
        assert status == 'not_applicable'

    def test_calc_inv_vs_sales_no_prev_data(self):
        bal = _mock_balance(inventory=100)
        inc = _mock_income()
        v, status, _ = self.mc._calc_inv_vs_sales(bal, inc, None, None)
        assert v is None
        assert status == 'missing'

    def test_calc_dilution_3y_no_history(self):
        bal = _mock_balance(common_stock_shares_outstanding=1_000_000_000)
        v, status, _ = self.mc._calc_dilution_3y(bal, None)
        assert v is None
        assert status == 'missing'

    def test_calc_pe_uses_stock_field(self):
        stock = SimpleNamespace(pe_ratio=Decimal("18.5"))
        v, status, _ = self.mc._calc_pe(stock)
        assert v == pytest.approx(18.5)
        assert status == 'normal'

    def test_calc_pe_missing(self):
        stock = SimpleNamespace(pe_ratio=None)
        v, status, _ = self.mc._calc_pe(stock)
        assert v is None
        assert status == 'missing'

    def test_calc_fcf_yield_normal(self):
        cf = _mock_cashflow(operating_cashflow=100, capital_expenditures=-20)
        stock = SimpleNamespace(market_capitalization=Decimal("400"))
        v, status, _ = self.mc._calc_fcf_yield(cf, stock)
        # FCF = 100 - 20 = 80, yield = 80/400 = 0.2
        assert v == pytest.approx(0.2)
        assert status == 'normal'

    def test_calc_shareholder_yield_includes_buyback_minus_issuance(self):
        cf = _mock_cashflow(
            dividend_payout=-10,
            payments_for_repurchase_of_common_stock=-20,
            proceeds_from_issuance_of_common_stock=5,
        )
        stock = SimpleNamespace(market_capitalization=Decimal("1000"))
        v, status, _ = self.mc._calc_shareholder_yield(cf, stock)
        assert status == 'normal'
        # (10 + 20 - 5) / 1000 = 0.025
        assert v == pytest.approx(0.025)


@pytest.mark.django_db
class TestMetricCalculateForSymbolGuards:
    def test_calculate_for_symbol_no_stock(self):
        mc = MetricCalculator()
        r = mc.calculate_for_symbol("ZZZZZZ")
        assert r['error'] == 'Stock not found'
        assert r['metrics_saved'] == 0

    def test_calculate_for_symbol_no_financials(self):
        _make_stock("NOFIN", market_cap=5_000_000_000)
        mc = MetricCalculator()
        with patch.object(mc.fetcher, 'get_financial_data', return_value={}):
            r = mc.calculate_for_symbol("NOFIN")
        assert r['error'] == 'No financial data'

    def test_calculate_for_symbols_swallows_exception(self):
        mc = MetricCalculator()
        with patch.object(mc, 'calculate_for_symbol', side_effect=RuntimeError("x")):
            r = mc.calculate_for_symbols(["X"])
        assert r['errors'] == 1


# ---------------------------------------------------------------------------
# RelativeMetrics 보강
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRelativeMetricsGuards:
    def test_stock_with_no_industry_returns_false(self):
        _make_stock("NOIND", industry="")
        rm = RelativeMetricCalculator()
        assert rm._calc_rev_growth_vs_industry("NOIND") is False

    def test_no_company_snapshot_returns_false(self):
        _make_stock("EMP", industry="Software")
        rm = RelativeMetricCalculator()
        assert rm._calc_rev_growth_vs_industry("EMP") is False

    def test_calculate_for_symbols_empty(self):
        rm = RelativeMetricCalculator()
        r = rm.calculate_for_symbols([])
        assert r == {'total': 0, 'success': 0, 'skip': 0}

    def test_calculate_for_symbols_swallows_exception(self):
        rm = RelativeMetricCalculator()
        with patch.object(
            rm, '_calc_rev_growth_vs_industry', side_effect=RuntimeError("x")
        ):
            r = rm.calculate_for_symbols(['A'])
        assert r['skip'] == 1
        assert r['success'] == 0

    def test_calculate_for_symbols_counts_success(self):
        rm = RelativeMetricCalculator()
        with patch.object(rm, '_calc_rev_growth_vs_industry', return_value=True):
            r = rm.calculate_for_symbols(['A', 'B'])
        assert r['total'] == 2
        assert r['success'] == 2
        assert r['skip'] == 0

    def test_calculate_for_symbols_counts_skip_on_false(self):
        rm = RelativeMetricCalculator()
        with patch.object(rm, '_calc_rev_growth_vs_industry', return_value=False):
            r = rm.calculate_for_symbols(['A', 'B'])
        assert r['skip'] == 2
        assert r['success'] == 0


# ---------------------------------------------------------------------------
# interpretation 보강
# ---------------------------------------------------------------------------

class TestInterpretSummary:
    def test_summary_only_gray_returns_neutral(self):
        """green/red 없이 gray만 있으면 중립 메시지 반환."""
        signals = [_make_signal('profitability', 'gray')]
        text = generate_summary_text(signals)
        assert "중립" in text

    def test_summary_green_plus_gray_mentions_gray(self):
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('growth', 'gray'),
        ]
        text = generate_summary_text(signals)
        # gray 카테고리는 "1개 카테고리 해석 제한" 형식
        assert "해석 제한" in text

    def test_summary_one_green_one_red(self):
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('growth', 'red', 20),
        ]
        text = generate_summary_text(signals)
        assert "강점" in text
        assert "주의" in text

    def test_summary_two_red_recommends_deep_analysis(self):
        signals = [
            _make_signal('profitability', 'red'),
            _make_signal('growth', 'red'),
        ]
        text = generate_summary_text(signals)
        assert "심층 분석" in text

    def test_summary_all_neutral_yellow(self):
        signals = [
            _make_signal('profitability', 'yellow'),
            _make_signal('growth', 'yellow'),
        ]
        text = generate_summary_text(signals)
        assert "뚜렷한 강점" in text or "중립" in text

    def test_summary_five_greens_all_good(self):
        signals = [_make_signal(f'c{i}', 'green', 80) for i in range(5)]
        text = generate_summary_text(signals)
        assert "양호" in text

    def test_summary_two_greens_uses_top_2_by_score(self):
        signals = [
            _make_signal('profitability', 'green', 50),
            _make_signal('growth', 'green', 90),
            _make_signal('valuation', 'green', 70),
        ]
        text = generate_summary_text(signals)
        # 점수 상위 2개(90, 70)는 growth + valuation
        assert "성장성" in text or "밸류에이션" in text


class TestInterpretMetric:
    def test_not_applicable_with_custom_reason(self):
        text = generate_metric_interpretation(
            metric_code='inventory_turnover_days',
            higher_is_better=False,
            percentile_rank=None,
            trend='',
            value_status='not_applicable',
            benchmark_confidence='high',
            not_applicable_reason='서비스 기업',
        )
        assert text == '서비스 기업'

    def test_not_applicable_without_reason_default(self):
        text = generate_metric_interpretation(
            metric_code='x', higher_is_better=True, percentile_rank=None,
            trend='', value_status='not_applicable', benchmark_confidence='high',
        )
        assert "해당 없음" in text

    def test_missing_status(self):
        text = generate_metric_interpretation(
            metric_code='x', higher_is_better=True, percentile_rank=10,
            trend='', value_status='missing', benchmark_confidence='high',
        )
        assert "제공되지" in text

    def test_low_confidence_warning(self):
        text = generate_metric_interpretation(
            metric_code='x', higher_is_better=True, percentile_rank=50,
            trend='', value_status='normal', benchmark_confidence='low',
        )
        assert "표본이 적어" in text

    def test_unstable_warning(self):
        text = generate_metric_interpretation(
            metric_code='x', higher_is_better=True, percentile_rank=50,
            trend='', value_status='unstable', benchmark_confidence='high',
        )
        assert "변동" in text

    def test_higher_is_better_direction(self):
        text = generate_metric_interpretation(
            metric_code='roe', higher_is_better=True, percentile_rank=90,
            trend='improving', value_status='normal', benchmark_confidence='high',
        )
        assert "높을수록" in text

    def test_lower_is_better_direction(self):
        text = generate_metric_interpretation(
            metric_code='debt_to_equity', higher_is_better=False,
            percentile_rank=10, trend='declining',
            value_status='normal', benchmark_confidence='high',
        )
        assert "낮을수록" in text

    def test_middle_percentile_says_median(self):
        text = generate_metric_interpretation(
            metric_code='x', higher_is_better=True, percentile_rank=50,
            trend='stable', value_status='normal', benchmark_confidence='high',
        )
        assert "중앙값" in text


class TestDetermineTrendBoundaries:
    def test_below_three_values_returns_empty(self):
        assert determine_trend([1.0, 2.0]) == ''

    def test_improving_above_5_percent(self):
        # 100 → 110 (10% 상승) → improving
        assert determine_trend([100.0, 105.0, 110.0]) == 'improving'

    def test_declining_below_5_percent(self):
        # 100 → 90 → declining
        assert determine_trend([100.0, 95.0, 90.0]) == 'declining'

    def test_stable_within_band(self):
        # 100 → 100 → 100 → stable
        assert determine_trend([100.0, 100.0, 100.0]) == 'stable'

    def test_stable_at_exact_5_percent_boundary(self):
        """recent[-1] == start*1.05 → improving 조건 (>) 미충족 → stable."""
        assert determine_trend([100.0, 100.0, 105.0]) == 'stable'

    def test_uses_only_last_three(self):
        # 앞에 큰 값 있어도 최근 3개만 본다
        assert determine_trend([1.0, 1.0, 100.0, 100.0, 100.0]) == 'stable'


class TestLeaderSummaryBranches:
    def test_empty_returns_no_data(self):
        assert generate_leader_summary([], []) == "비교 데이터 부족."

    def test_only_advantages(self):
        adv = [{'category': 'profitability'}, {'category': 'growth'}]
        text = generate_leader_summary(adv, [])
        assert "2개 우위" in text
        assert "강점" in text

    def test_only_disadvantages(self):
        dis = [{'category': 'financial_structure'}]
        text = generate_leader_summary([], dis)
        assert "약점" in text

    def test_dedupe_categories(self):
        """같은 category 중복은 한 번만."""
        adv = [
            {'category': 'profitability'},
            {'category': 'profitability'},
            {'category': 'growth'},
        ]
        text = generate_leader_summary(adv, [])
        # 수익성과 성장성이 각각 한 번만 등장
        assert text.count("수익성") == 1
        assert "성장성" in text
