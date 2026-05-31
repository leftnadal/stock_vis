"""
Validation 서비스 보완 단위 테스트

기존 test_*.py가 다루지 않는 엣지 케이스, 경계값, 통합 흐름을 보완.

대상 서비스 (validation/services/):
  - preset_generator.py
  - benchmark_calculator.py
  - metric_calculator.py
  - relative_metrics.py
  - interpretation.py

원칙:
  - 외부 의존(DB 모델, 외부 API)은 mock 또는 in-memory factory 사용
  - 순수 함수는 DB 없이 직접 호출
  - 각 테스트는 단일 책임
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.metrics.models import (
    CompanyMetricSnapshot,
    IndustryMetricBenchmark,
    MetricDefinition,
    PeerListCache,
)
from packages.shared.stocks.models import (
    IndustryClassification,
    SP500Constituent,
    Stock,
)
from services.validation.models import PeerPreset
from services.validation.services.benchmark_calculator import (
    SIZE_BUCKETS,
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
# Factories
# ---------------------------------------------------------------------------

def _make_stock(symbol, sector="Technology", industry="Software",
                market_cap=50_000_000_000, pe_ratio=None):
    return Stock.objects.get_or_create(
        symbol=symbol,
        defaults={
            'stock_name': f'{symbol} Inc',
            'exchange': 'NASDAQ',
            'sector': sector,
            'industry': industry,
            'market_capitalization': (
                Decimal(str(market_cap)) if market_cap else None
            ),
            'pe_ratio': Decimal(str(pe_ratio)) if pe_ratio is not None else None,
        },
    )[0]


def _make_sp500(symbol, is_active=True, sector='Technology'):
    return SP500Constituent.objects.get_or_create(
        symbol=symbol,
        defaults={
            'company_name': f'{symbol} Corp',
            'sector': sector,
            'is_active': is_active,
        },
    )[0]


def _make_metric_def(code, higher_is_better=True, is_benchmarkable=True,
                     category='profitability'):
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


def _make_snapshot(symbol, fy, code, value, status='normal'):
    md = _make_metric_def(code)
    return CompanyMetricSnapshot.objects.get_or_create(
        symbol_id=symbol,
        fiscal_year=fy,
        metric_code=md,
        defaults={
            'metric_value': Decimal(str(value)) if value is not None else None,
            'value_status': status,
        },
    )[0]


def _make_industry_benchmark(industry, fy, code, median):
    md = _make_metric_def(code)
    return IndustryMetricBenchmark.objects.get_or_create(
        industry=industry,
        fiscal_year=fy,
        metric_code=md,
        defaults={
            'median_value': Decimal(str(median)) if median is not None else None,
            'sample_count': 10,
            'benchmark_confidence': 'high',
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


def _make_signal(category, signal, score=50.0):
    return SimpleNamespace(category=category, signal=signal, score=score)


# ===========================================================================
# Section 1: PresetGenerator — 통합 흐름 + 배치 보완
# ===========================================================================


@pytest.mark.django_db
class TestPresetGeneratorIntegration:
    """generate_for_symbol() 통합 흐름 + 배치 보완."""

    def test_symbol_uppercased_on_lookup(self):
        """소문자 심볼 입력 → 내부에서 upper() 변환 후 조회."""
        _make_stock("UPCASE", sector="Technology", industry="Software")
        _make_sp500("UPCASE")

        gen = PresetGenerator()
        result = gen.generate_for_symbol("upcase")

        assert result['symbol'] == 'UPCASE'
        assert 'error' not in result

    def test_mid_cap_skips_size_peers_branch(self):
        """mid 사이즈 종목 → size_peers 프리셋 미생성 (mega/large만 대상)."""
        stock = _make_stock(
            "MIDCAP",
            sector="Industrials",
            industry="Machinery",
            market_cap=5_000_000_000,  # mid
        )
        _make_sp500("MIDCAP")
        for i in range(10):
            sym = f"MID{i:02d}"
            _make_stock(sym, sector="Industrials", industry="Machinery",
                        market_cap=4_000_000_000)
            _make_sp500(sym)

        gen = PresetGenerator()
        gen.generate_for_symbol("MIDCAP")

        size_preset = PeerPreset.objects.filter(
            symbol=stock, preset_key='size_peers'
        ).first()
        assert size_preset is None, "mid 사이즈는 size_peers 미생성"

    def test_large_cap_creates_size_peers(self):
        """large 사이즈 + 동일 sector 3개 이상 → size_peers 프리셋 생성."""
        stock = _make_stock(
            "LRGCAP",
            sector="Energy",
            industry="Oil & Gas",
            market_cap=50_000_000_000,  # large
        )
        _make_sp500("LRGCAP")
        for i in range(8):
            sym = f"LRG{i:02d}"
            _make_stock(sym, sector="Energy", industry="Oil & Gas",
                        market_cap=30_000_000_000)
            _make_sp500(sym)

        gen = PresetGenerator()
        gen.generate_for_symbol("LRGCAP")

        size_preset = PeerPreset.objects.filter(
            symbol=stock, preset_key='size_peers'
        ).first()
        assert size_preset is not None
        assert size_preset.generation_method == 'auto_size'

    def test_returns_presets_created_count(self):
        """presets_created가 실제 생성된 프리셋 수와 일치."""
        stock = _make_stock(
            "PCNT",
            sector="Consumer Staples",
            industry="Beverages",
            market_cap=80_000_000_000,
        )
        _make_sp500("PCNT")
        for i in range(10):
            sym = f"BV{i:02d}"
            _make_stock(sym, sector="Consumer Staples", industry="Beverages",
                        market_cap=40_000_000_000)
            _make_sp500(sym)

        gen = PresetGenerator()
        result = gen.generate_for_symbol("PCNT")

        actual_count = PeerPreset.objects.filter(symbol=stock).count()
        assert result['presets_created'] == actual_count

    def test_generate_for_symbols_default_uses_sp500(self):
        """symbols=None → SP500 활성 종목 사용."""
        _make_stock("SP01", sector="Technology", industry="Software")
        _make_sp500("SP01", is_active=True)
        _make_stock("SP02", sector="Technology", industry="Software")
        _make_sp500("SP02", is_active=False)  # 비활성

        gen = PresetGenerator()
        result = gen.generate_for_symbols()

        # 활성 SP500만 카운트
        assert result['total'] == 1

    def test_generate_for_symbols_explicit_list(self):
        """명시적 symbols 리스트 → 그대로 처리."""
        _make_stock("BAT1", sector="Tech", industry="SW")
        _make_stock("BAT2", sector="Tech", industry="SW")

        gen = PresetGenerator()
        result = gen.generate_for_symbols(["BAT1", "BAT2"])
        assert result['total'] == 2

    def test_generate_for_symbols_handles_exceptions(self):
        """generate_for_symbol에서 예외 발생해도 다음 종목 진행."""
        gen = PresetGenerator()
        with patch.object(
            gen, 'generate_for_symbol',
            side_effect=[Exception("boom"), {'symbol': 'X', 'presets_created': 1}],
        ):
            result = gen.generate_for_symbols(["BAD", "GOOD"])
            assert result['total'] == 2
            # success는 예외 종목 제외 1개
            assert result['success'] == 1

    def test_industry_case_insensitive(self):
        """industry 필터는 iexact (대소문자 무시)."""
        stock = _make_stock(
            "CASEI", sector="Tech", industry="software",  # 소문자
            market_cap=50_000_000_000,
        )
        _make_sp500("CASEI")
        for i in range(10):
            sym = f"CI{i:02d}"
            _make_stock(sym, sector="Tech", industry="SOFTWARE",  # 대문자
                        market_cap=40_000_000_000)
            _make_sp500(sym)

        gen = PresetGenerator()
        gen.generate_for_symbol("CASEI")

        preset = PeerPreset.objects.filter(symbol=stock, preset_key='default').first()
        assert preset is not None
        assert preset.peer_count >= 8


# ===========================================================================
# Section 2: BenchmarkCalculator — 경계값 + 폴백 보완
# ===========================================================================


class TestAssignSizeBucketBoundaries:
    """순수 함수: 경계값과 비정상 입력 검증."""

    def test_just_below_mega(self):
        """200B-1 → large."""
        assert assign_size_bucket(199_999_999_999) == 'large'

    def test_just_below_large(self):
        """10B-1 → mid."""
        assert assign_size_bucket(9_999_999_999) == 'mid'

    def test_just_below_mid(self):
        """2B-1 → small."""
        assert assign_size_bucket(1_999_999_999) == 'small'

    def test_zero_market_cap(self):
        """0 → small (가장 낮은 bucket)."""
        assert assign_size_bucket(0) == 'small'

    def test_extremely_large_value(self):
        """천조 단위도 mega로 처리."""
        assert assign_size_bucket(10_000_000_000_000) == 'mega'


class TestGetAdjacentBucketsStructure:
    """get_adjacent_buckets 반환 타입 + SIZE_BUCKETS 일관성."""

    def test_returns_list(self):
        result = get_adjacent_buckets('mid')
        assert isinstance(result, list)

    def test_size_buckets_constant_order(self):
        """SIZE_BUCKETS 순서: small < mid < large < mega."""
        assert SIZE_BUCKETS == ['small', 'mid', 'large', 'mega']

    def test_all_returned_buckets_in_size_buckets(self):
        """모든 반환값이 SIZE_BUCKETS 상수에 포함."""
        for b in ['mega', 'large', 'mid', 'small']:
            for adj in get_adjacent_buckets(b):
                assert adj in SIZE_BUCKETS


class TestDetermineConfidenceBoundaries:
    """_determine_confidence 경계값."""

    def setup_method(self):
        self.calc = BenchmarkCalculator()

    def test_peer_count_exactly_15_industry_size_high(self):
        """peer=15 + industry_size → high (경계)."""
        assert self.calc._determine_confidence(15, 'industry_size') == 'high'

    def test_peer_count_exactly_8_medium(self):
        """peer=8 → medium (경계)."""
        assert self.calc._determine_confidence(8, 'sector') == 'medium'

    def test_peer_count_exactly_4_low(self):
        """peer=4 → low (경계)."""
        assert self.calc._determine_confidence(4, 'industry') == 'low'

    def test_peer_count_3_limited(self):
        """peer=3 → limited."""
        assert self.calc._determine_confidence(3, 'industry') == 'limited'

    def test_peer_count_zero_limited(self):
        """peer=0 → limited (fallback)."""
        assert self.calc._determine_confidence(0, 'sector') == 'limited'


@pytest.mark.django_db
class TestBenchmarkCalculatorFlows:
    """calculate_for_symbol 시나리오 보완."""

    def test_stock_with_no_market_cap_routes_to_mid(self):
        """market_cap=None → assign_size_bucket이 'mid' 반환."""
        stock = _make_stock("NOMC", sector="Tech", industry="SW",
                            market_cap=None)
        _make_sp500("NOMC")
        for i in range(5):
            sym = f"NM{i:02d}"
            _make_stock(sym, sector="Tech", industry="SW",
                        market_cap=5_000_000_000)
            _make_sp500(sym)

        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbol("NOMC")
        assert result['size_bucket'] == 'mid'

    def test_calculate_for_symbols_returns_total_count(self):
        """배치 결과의 total은 입력 개수와 동일."""
        _make_stock("BC1", sector="Tech", industry="SW")
        _make_sp500("BC1")
        _make_stock("BC2", sector="Tech", industry="SW")
        _make_sp500("BC2")

        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbols(["BC1", "BC2"])
        assert result['total'] == 2

    def test_calculate_for_symbols_error_path(self):
        """존재하지 않는 심볼은 errors로 카운트."""
        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbols(["GHOST_SYMBOL_X"])
        assert result['errors'] == 1
        assert result['success'] == 0

    def test_industry_fallback_no_size_match(self):
        """industry 일치 종목은 있지만 인접 size 미달 → industry fallback (basis='industry')."""
        stock = _make_stock(
            "IFB", sector="Healthcare", industry="Pharma",
            market_cap=300_000_000_000,  # mega
        )
        _make_sp500("IFB")
        # 같은 industry, 그러나 small cap (mega/large/mid가 adjacent)
        for i in range(6):
            sym = f"PH{i:02d}"
            _make_stock(sym, sector="Healthcare", industry="Pharma",
                        market_cap=500_000_000)
            _make_sp500(sym)

        calc = BenchmarkCalculator()
        peers, basis = calc._select_peers(stock)
        assert basis == 'industry'


# ===========================================================================
# Section 3: MetricCalculator — 헬퍼/지표 엣지 케이스
# ===========================================================================


class TestSafeHelpersExtra:
    """_safe / _safe_nonzero / _div 추가 엣지 케이스."""

    def test_safe_negative_float(self):
        assert _safe(-3.14) == pytest.approx(-3.14)

    def test_safe_decimal_zero(self):
        """Decimal(0) → 0.0 반환 (실제 0 보존)."""
        assert _safe(Decimal("0")) == 0.0

    def test_safe_string_numeric(self):
        """문자열 숫자 → float 변환."""
        assert _safe("42.5") == pytest.approx(42.5)

    def test_safe_nonzero_negative(self):
        """음수는 통과 (0만 None)."""
        assert _safe_nonzero(-10) == -10.0

    def test_div_negative_numerator(self):
        assert _div(-10, 5) == pytest.approx(-2.0)

    def test_div_decimal_inputs(self):
        assert _div(Decimal("10"), Decimal("4")) == pytest.approx(2.5)


class TestMetricCalculatorBranches:
    """MetricCalculator의 추가 분기 케이스."""

    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_calc_growth_zero_with_strict_threshold(self):
        """이전 값이 |prev|<1이면 missing (분모 안정성)."""
        val, status, reason = self.calc._calc_growth(100, 0.1)
        assert val is None
        assert status == 'missing'

    def test_calc_fcf_growth_no_cf_objects(self):
        """cf가 None이면 missing."""
        val, status, _ = self.calc._calc_fcf_growth(None, _mock_cashflow())
        assert val is None
        assert status == 'missing'

    def test_calc_short_term_debt_pct_normal_ratio(self):
        """short=10, long=40 → 10/50=0.2."""
        bal = _mock_balance(short_term_debt=10, long_term_debt=40)
        val, status, _ = self.calc._calc_short_term_debt_pct(bal)
        assert val == pytest.approx(0.2)
        assert status == 'normal'

    def test_calc_inv_vs_sales_stock_company(self):
        """재고 있는 기업 → inv_growth - rev_growth 정상 반환."""
        bal = _mock_balance(inventory=110)
        inc = _mock_income(total_revenue=110)
        prev_bal = _mock_balance(inventory=100)
        prev_inc = _mock_income(total_revenue=100)

        val, status, _ = self.calc._calc_inv_vs_sales(bal, inc, prev_bal, prev_inc)
        assert val == pytest.approx(0.0, abs=0.001)  # 동일 성장률
        assert status == 'normal'

    def test_calc_dilution_3y_no_change(self):
        """3년 전과 동일 shares → 0% 희석."""
        bal = _mock_balance(common_stock_shares_outstanding=1_000_000_000)
        prev_bal = _mock_balance(common_stock_shares_outstanding=1_000_000_000)
        val, status, _ = self.calc._calc_dilution_3y(bal, prev_bal)
        assert val == pytest.approx(0.0)
        assert status == 'normal'

    def test_calc_shareholder_yield_zero_returns_zero(self):
        """배당/자사주매입/유상증자 모두 0 → yield=0."""
        cf = _mock_cashflow(
            dividend_payout=0,
            payments_for_repurchase_of_common_stock=0,
            proceeds_from_issuance_of_common_stock=0,
        )
        stock = SimpleNamespace(market_capitalization=100_000_000_000)
        val, status, _ = self.calc._calc_shareholder_yield(cf, stock)
        assert val == pytest.approx(0.0)
        assert status == 'normal'

    def test_calc_pe_passes_through(self):
        """Stock.pe_ratio 그대로 반환."""
        stock = SimpleNamespace(pe_ratio=Decimal("18.5"))
        val, status, _ = self.calc._calc_pe(stock)
        assert val == pytest.approx(18.5)
        assert status == 'normal'

    def test_calc_ev_ebitda_zero_ebitda_missing(self):
        """ebitda=0 → missing."""
        stock = SimpleNamespace(market_capitalization=100_000_000_000)
        inc = _mock_income(ebitda=0)
        val, status, _ = self.calc._calc_ev_ebitda(stock, inc)
        assert val is None
        assert status == 'missing'

    def test_calc_cash_runway_break_even_ocf(self):
        """OCF=0 → not_applicable (흑자/break-even 기업)."""
        cf = _mock_cashflow(operating_cashflow=0)
        bal = _mock_balance()
        val, status, _ = self.calc._calc_cash_runway(bal, cf)
        assert status == 'not_applicable'


@pytest.mark.django_db
class TestMetricCalculatorErrorPaths:
    """MetricCalculator의 상위 진입점 오류 처리."""

    def test_calculate_for_symbol_not_found(self):
        """Stock 미존재 → error 반환."""
        calc = MetricCalculator()
        result = calc.calculate_for_symbol("NOEXIST")
        assert result['error'] == 'Stock not found'
        assert result['metrics_saved'] == 0

    def test_calculate_for_symbol_no_financial_data(self):
        """FinancialFetcher가 빈 dict 반환 → 'No financial data' 오류."""
        _make_stock("NOFIN", sector="Tech", industry="SW")
        calc = MetricCalculator()
        with patch.object(calc.fetcher, 'get_financial_data', return_value={}):
            result = calc.calculate_for_symbol("NOFIN")
        assert result['error'] == 'No financial data'

    def test_calculate_for_symbols_default_uses_sp500(self):
        """symbols=None → SP500 활성 종목 자동 조회."""
        _make_stock("MC1", sector="Tech", industry="SW")
        _make_sp500("MC1")

        calc = MetricCalculator()
        with patch.object(calc, 'calculate_for_symbol',
                          return_value={'symbol': 'MC1', 'metrics_saved': 30}):
            result = calc.calculate_for_symbols()
        assert result['total'] == 1
        assert result['success'] == 1


# ===========================================================================
# Section 4: RelativeMetricCalculator — 보완 케이스
# ===========================================================================


@pytest.mark.django_db
class TestRelativeMetricEdgeCases:
    """RelativeMetricCalculator 경계 및 누락 데이터 처리."""

    def setup_method(self):
        _make_metric_def('rev_growth_vs_industry', category='growth')
        _make_metric_def('revenue_growth_yoy', category='growth')

    def test_zero_relative(self):
        """자사 = industry median → relative = 0."""
        _make_stock("RZER", industry="Banking")
        _make_snapshot("RZER", 2024, "revenue_growth_yoy", 0.10)
        _make_industry_benchmark("Banking", 2024, "revenue_growth_yoy", 0.10)

        calc = RelativeMetricCalculator()
        ok = calc._calc_rev_growth_vs_industry("RZER")
        assert ok is True

        snap = CompanyMetricSnapshot.objects.filter(
            symbol_id="RZER", metric_code_id="rev_growth_vs_industry",
        ).first()
        assert float(snap.metric_value) == pytest.approx(0.0)

    def test_industry_median_none_skips_year(self):
        """median_value=None → 해당 연도 스킵 (False 반환)."""
        _make_stock("RNON", industry="Niche")
        _make_snapshot("RNON", 2024, "revenue_growth_yoy", 0.20)
        _make_industry_benchmark("Niche", 2024, "revenue_growth_yoy", None)

        calc = RelativeMetricCalculator()
        ok = calc._calc_rev_growth_vs_industry("RNON")
        # 모든 연도 스킵 → updated=False
        assert ok is False

    def test_update_existing_record(self):
        """기존 rev_growth_vs_industry 레코드 → update_or_create로 갱신."""
        _make_stock("RUPD", industry="Telecom")
        _make_snapshot("RUPD", 2024, "revenue_growth_yoy", 0.05)
        _make_industry_benchmark("Telecom", 2024, "revenue_growth_yoy", 0.08)

        calc = RelativeMetricCalculator()
        # 첫 호출
        calc._calc_rev_growth_vs_industry("RUPD")
        first = CompanyMetricSnapshot.objects.get(
            symbol_id="RUPD", fiscal_year=2024,
            metric_code_id="rev_growth_vs_industry",
        )
        assert float(first.metric_value) == pytest.approx(-0.03, abs=0.001)

        # industry median 변경 후 재호출
        ib = IndustryMetricBenchmark.objects.get(
            industry="Telecom", fiscal_year=2024,
            metric_code_id="revenue_growth_yoy",
        )
        ib.median_value = Decimal("0.02")
        ib.save()

        calc._calc_rev_growth_vs_industry("RUPD")
        updated = CompanyMetricSnapshot.objects.get(
            symbol_id="RUPD", fiscal_year=2024,
            metric_code_id="rev_growth_vs_industry",
        )
        assert float(updated.metric_value) == pytest.approx(0.03, abs=0.001)

    def test_source_detail_records_inputs(self):
        """source_detail에 company_growth와 industry_median 기록."""
        _make_stock("RSRC", industry="Retail")
        _make_snapshot("RSRC", 2024, "revenue_growth_yoy", 0.12)
        _make_industry_benchmark("Retail", 2024, "revenue_growth_yoy", 0.07)

        calc = RelativeMetricCalculator()
        calc._calc_rev_growth_vs_industry("RSRC")

        snap = CompanyMetricSnapshot.objects.get(
            symbol_id="RSRC", fiscal_year=2024,
            metric_code_id="rev_growth_vs_industry",
        )
        assert snap.source_detail['company_growth'] == pytest.approx(0.12)
        assert snap.source_detail['industry_median'] == pytest.approx(0.07)
        assert 'calculated_at' in snap.source_detail

    def test_calculate_for_symbols_handles_exceptions(self):
        """내부 예외도 skip으로 카운트되어 배치가 중단되지 않는다."""
        calc = RelativeMetricCalculator()
        with patch.object(
            calc, '_calc_rev_growth_vs_industry',
            side_effect=[True, Exception("boom"), False],
        ):
            result = calc.calculate_for_symbols(["A", "B", "C"])
        assert result['total'] == 3
        assert result['success'] == 1
        assert result['skip'] == 2  # exception + False

    def test_calculate_for_symbols_default_uses_active_sp500(self):
        """symbols=None → 활성 SP500만 처리."""
        _make_stock("RAC1", industry="Tech")
        _make_sp500("RAC1", is_active=True)
        _make_stock("RAC2", industry="Tech")
        _make_sp500("RAC2", is_active=False)

        calc = RelativeMetricCalculator()
        with patch.object(
            calc, '_calc_rev_growth_vs_industry', return_value=True,
        ):
            result = calc.calculate_for_symbols()
        assert result['total'] == 1


# ===========================================================================
# Section 5: Interpretation — 텍스트 생성 보완
# ===========================================================================


class TestSummaryTextExtra:
    """generate_summary_text 추가 시나리오."""

    def test_empty_signals(self):
        """빈 입력 → 중립 문구."""
        text = generate_summary_text([])
        assert '중립' in text or '없음' in text

    def test_top2_picks_highest_scores(self):
        """green 3개 중 점수 상위 2개가 텍스트에 포함."""
        from services.validation.services.category_signal_calculator import CATEGORY_DISPLAY
        signals = [
            _make_signal('profitability', 'green', score=95),  # 최고
            _make_signal('growth', 'green', score=60),         # 중간
            _make_signal('valuation', 'green', score=85),      # 두번째
        ]
        text = generate_summary_text(signals)
        # 상위 2개: profitability, valuation
        assert CATEGORY_DISPLAY['profitability'] in text
        assert CATEGORY_DISPLAY['valuation'] in text

    def test_single_red_no_심층(self):
        """red 1개만 있고 green 없음 → '심층 분석 권장' 미포함."""
        signals = [
            _make_signal('valuation', 'red', score=10),
        ]
        text = generate_summary_text(signals)
        assert '심층 분석 권장' not in text

    def test_unknown_category_passthrough(self):
        """CATEGORY_DISPLAY에 없는 category명은 원본 그대로 사용."""
        signals = [
            _make_signal('mystery_category', 'green', score=80),
        ]
        text = generate_summary_text(signals)
        assert 'mystery_category' in text


class TestMetricInterpretationExtra:
    """generate_metric_interpretation 보완."""

    def test_percentile_exactly_75_high_branch(self):
        """percentile=75 정확히 → '상위' 브랜치."""
        text = generate_metric_interpretation(
            'roe', True, 75.0, '', 'normal', 'high'
        )
        assert '상위' in text

    def test_percentile_exactly_25_low_branch(self):
        """percentile=25 정확히 → '하위' 브랜치."""
        text = generate_metric_interpretation(
            'roe', True, 25.0, '', 'normal', 'high'
        )
        assert '하위' in text

    def test_confidence_high_no_warning(self):
        """benchmark_confidence='high' → 표본 경고 미포함."""
        text = generate_metric_interpretation(
            'roe', True, 50.0, '', 'normal', 'high'
        )
        assert '표본이 적어' not in text

    def test_no_trend_no_trend_text(self):
        """trend='' → 추세 문구 미포함."""
        text = generate_metric_interpretation(
            'roe', True, 50.0, '', 'normal', 'high'
        )
        assert '개선' not in text
        assert '하락' not in text
        assert '안정적' not in text

    def test_unstable_status_with_high_percentile(self):
        """unstable + 상위 → 두 표현 모두 포함."""
        text = generate_metric_interpretation(
            'interest_coverage', True, 90.0, 'improving', 'unstable', 'high'
        )
        assert '상위' in text
        assert '변동이 크므로' in text


class TestDetermineTrendExtra:
    """determine_trend 추가 경계."""

    def test_all_zeros_stable(self):
        """모두 0 → 0 * 1.05 = 0 = 0 (stable)."""
        assert determine_trend([0.0, 0.0, 0.0]) == 'stable'

    def test_threshold_just_above_improving(self):
        """마지막이 처음 * 1.05 직후 → improving."""
        # 처음=100, 1.05배=105 → 105.01이면 improving
        assert determine_trend([100.0, 100.0, 105.01]) == 'improving'

    def test_threshold_just_below_declining(self):
        """마지막이 처음 * 0.95 직전 → declining."""
        # 100 * 0.95 = 95 → 94.99이면 declining
        assert determine_trend([100.0, 100.0, 94.99]) == 'declining'

    def test_empty_list(self):
        """빈 리스트 → 빈 문자열."""
        assert determine_trend([]) == ''


class TestLeaderSummaryExtra:
    """generate_leader_summary 보완."""

    def test_deduplicates_categories(self):
        """동일 category 중복 → 1번만 노출."""
        adv = [
            {'category': 'profitability', 'metric': 'roe'},
            {'category': 'profitability', 'metric': 'roic'},  # 중복
            {'category': 'growth', 'metric': 'revenue_growth_yoy'},
        ]
        text = generate_leader_summary(adv, [])
        # 수익성이 한 번만 등장
        assert text.count('수익성') == 1

    def test_truncates_to_three_categories(self):
        """3개 초과 category는 표시되지 않음 (dict.fromkeys[:3])."""
        adv = [
            {'category': 'profitability'},
            {'category': 'growth'},
            {'category': 'financial_structure'},
            {'category': 'valuation'},  # 4번째 — 약점 텍스트엔 등장 안 함
        ]
        text = generate_leader_summary(adv, [])
        from services.validation.services.category_signal_calculator import CATEGORY_DISPLAY
        # 처음 3개만 강점에 등장
        adv_section = text.split('강점:')[-1]
        assert CATEGORY_DISPLAY['profitability'] in adv_section
        assert CATEGORY_DISPLAY['valuation'] not in adv_section

    def test_returns_count_total(self):
        """비교 총합 = advantages + disadvantages 길이."""
        adv = [{'category': 'profitability'}] * 3
        disadv = [{'category': 'growth'}] * 2
        text = generate_leader_summary(adv, disadv)
        assert '5개 비교 지표' in text
        assert '3개 우위' in text
