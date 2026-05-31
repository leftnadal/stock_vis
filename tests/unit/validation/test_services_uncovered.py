"""
validation/services 미커버 영역 단위 테스트

기존 테스트가 다루지 않는 메서드/분기에 대한 추가 커버리지.

테스트 대상:
  - PresetGenerator._generate_quality_top — 우량주 비교 프리셋 (sector >= 25 + 지표 분포)
  - PresetGenerator._generate_lifecycle — 성장단계 프리셋 (혈액형: 고성장/안정형/저성장)
  - PresetGenerator._generate_thematic — DNA 매칭 (cross-sector / same-sector)
  - BenchmarkCalculator.calculate_for_symbols — 배치 + 예외 경로
  - BenchmarkCalculator._filter_by_size — size bucket 필터
  - BenchmarkCalculator._get_available_years — fiscal_year 목록 조회
  - BenchmarkCalculator._calculate_industry_benchmarks — industry 전체 통계
  - MetricCalculator._calc_ocf_trend_placeholder — Phase 2 미구현
  - MetricCalculator._update_latest — CompanyMetricLatest 갱신
  - MetricCalculator.calculate_for_symbols — 배치 진행
  - RelativeMetricCalculator.calculate_for_symbols — 기본/예외 분기
  - interpretation.generate_summary_text — green+red 결합, 경계
  - interpretation.generate_metric_interpretation — None percentile, 결합
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
    PeerMetricBenchmark,
)
from packages.shared.stocks.models import SP500Constituent, Stock
from services.validation.models import CompanyBenchmarkDelta, CompanyMetricLatest, PeerPreset
from services.validation.services.benchmark_calculator import BenchmarkCalculator
from services.validation.services.interpretation import (
    generate_metric_interpretation,
    generate_summary_text,
)
from services.validation.services.metric_calculator import MetricCalculator
from services.validation.services.preset_generator import PresetGenerator
from services.validation.services.relative_metrics import RelativeMetricCalculator

# ---------------------------------------------------------------------------
# Helpers
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


def _make_signal(category, signal, score=50.0):
    return SimpleNamespace(category=category, signal=signal, score=score)


# ---------------------------------------------------------------------------
# Tests: PresetGenerator._generate_quality_top
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateQualityTop:
    def test_no_sector_returns_zero(self):
        """sector 없는 종목 → 0."""
        stock = _make_stock("QT_NS", sector=None, industry=None)
        gen = PresetGenerator()
        count = gen._generate_quality_top(stock, Stock.objects.none())
        assert count == 0

    def test_insufficient_sector_peers(self):
        """sector peer < 25 → 0."""
        stock = _make_stock("QT_LP", sector="Energy", industry="Oil")
        for i in range(5):
            sym = f"QTLP{i:02d}"
            _make_stock(sym, sector="Energy", industry="Oil")

        gen = PresetGenerator()
        base_qs = Stock.objects.filter(sector__iexact="Energy").exclude(symbol="QT_LP")
        count = gen._generate_quality_top(stock, base_qs)
        assert count == 0

    def test_no_snapshot_returns_zero(self):
        """sector peer >= 25지만 본인 snapshot 없음 → 0."""
        stock = _make_stock("QT_NSN", sector="Healthcare", industry="Biotech")
        for i in range(30):
            sym = f"QTNSN{i:02d}"
            _make_stock(sym, sector="Healthcare", industry=f"Biotech{i % 3}")

        gen = PresetGenerator()
        base_qs = Stock.objects.filter(sector__iexact="Healthcare").exclude(symbol="QT_NSN")
        count = gen._generate_quality_top(stock, base_qs)
        # 본인 snapshot 없으므로 latest_fy 결정 불가 → 0
        assert count == 0

    def test_creates_preset_when_quality_high(self):
        """sector >= 25 + 본인+peer snapshot 다수 → 우량주 프리셋 생성."""
        stock = _make_stock("QT_OK", sector="Industrials", industry="Aerospace")
        # 본인 quality 지표 (상위)
        _make_snapshot("QT_OK", 2024, "roic", 0.35)
        _make_snapshot("QT_OK", 2024, "operating_margin", 0.30)
        _make_snapshot("QT_OK", 2024, "fcf_margin", 0.25)

        # sector peer 30개 — 본인이 상위가 되도록 낮은 값으로 분포
        for i in range(30):
            sym = f"QTOK{i:02d}"
            _make_stock(sym, sector="Industrials", industry=f"Sub{i % 4}")
            # 일부는 매우 낮은 값 (본인이 상위 percentile에 들도록)
            base = 0.05 + (i * 0.005)
            _make_snapshot(sym, 2024, "roic", base)
            _make_snapshot(sym, 2024, "operating_margin", base)
            _make_snapshot(sym, 2024, "fcf_margin", base)

        gen = PresetGenerator()
        base_qs = Stock.objects.filter(sector__iexact="Industrials").exclude(symbol="QT_OK")
        count = gen._generate_quality_top(stock, base_qs)
        assert count == 1
        preset = PeerPreset.objects.get(symbol=stock, preset_key='quality_top')
        assert preset.generation_method == 'auto_quality'


# ---------------------------------------------------------------------------
# Tests: PresetGenerator._generate_lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateLifecycle:
    def test_no_sector_returns_zero(self):
        stock = _make_stock("LC_NS", sector=None, industry=None)
        gen = PresetGenerator()
        count = gen._generate_lifecycle(stock, Stock.objects.none())
        assert count == 0

    def test_insufficient_sector_peers(self):
        """sector peer < 25 → 0."""
        stock = _make_stock("LC_LP", sector="Utilities", industry="Electric")
        for i in range(5):
            _make_stock(f"LCLP{i:02d}", sector="Utilities", industry="Electric")

        gen = PresetGenerator()
        base_qs = Stock.objects.filter(sector__iexact="Utilities").exclude(symbol="LC_LP")
        count = gen._generate_lifecycle(stock, base_qs)
        assert count == 0

    def test_no_snapshot_returns_zero(self):
        """sector >= 25 but 본인 fiscal_year 없음 → 0."""
        stock = _make_stock("LC_NSN", sector="Materials", industry="Chemicals")
        for i in range(28):
            _make_stock(f"LCNSN{i:02d}", sector="Materials", industry="Chemicals")

        gen = PresetGenerator()
        base_qs = Stock.objects.filter(sector__iexact="Materials").exclude(symbol="LC_NSN")
        count = gen._generate_lifecycle(stock, base_qs)
        assert count == 0

    def test_high_growth_group_creates_preset(self):
        """본인 성장률이 P75 이상 → 고성장 그룹."""
        stock = _make_stock("LC_HG", sector="Communication", industry="Streaming")
        # 본인은 매우 높은 성장
        _make_snapshot("LC_HG", 2024, "revenue_growth_yoy", 0.50)

        # sector peer 30개 — 다양한 성장률 분포
        for i in range(30):
            sym = f"LCHG{i:02d}"
            _make_stock(sym, sector="Communication", industry=f"Sub{i % 3}")
            # 0.05 ~ 0.35 분포
            growth = 0.05 + (i * 0.01)
            _make_snapshot(sym, 2024, "revenue_growth_yoy", growth)

        gen = PresetGenerator()
        base_qs = Stock.objects.filter(sector__iexact="Communication").exclude(symbol="LC_HG")
        count = gen._generate_lifecycle(stock, base_qs)
        assert count == 1
        preset = PeerPreset.objects.get(symbol=stock, preset_key='lifecycle')
        assert preset.generation_method == 'auto_lifecycle'
        assert '고성장' in preset.logic_summary

    def test_stable_group_creates_preset(self):
        """본인 성장률이 P25~P75 사이 → 안정형 그룹."""
        stock = _make_stock("LC_ST", sector="Financials", industry="Bank2")
        # 본인은 중간 성장
        _make_snapshot("LC_ST", 2024, "revenue_growth_yoy", 0.18)

        for i in range(30):
            sym = f"LCST{i:02d}"
            _make_stock(sym, sector="Financials", industry=f"Sub{i % 4}")
            growth = 0.05 + (i * 0.012)
            _make_snapshot(sym, 2024, "revenue_growth_yoy", growth)

        gen = PresetGenerator()
        base_qs = Stock.objects.filter(sector__iexact="Financials").exclude(symbol="LC_ST")
        count = gen._generate_lifecycle(stock, base_qs)
        assert count == 1
        preset = PeerPreset.objects.get(symbol=stock, preset_key='lifecycle')
        assert '안정형' in preset.logic_summary


# ---------------------------------------------------------------------------
# Tests: PresetGenerator._generate_thematic (DNA 존재 분기)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGenerateThematicWithDNA:
    def test_creates_preset_when_dna_matches(self):
        """본인 + 다른 종목 5개 이상이 같은 stage+capital_type → 프리셋 생성."""
        from apps.chain_sight.models import CompanyCapitalDNA, CompanyGrowthStage

        stock = _make_stock("DNA_OK", sector="Technology", industry="Cloud")
        CompanyGrowthStage.objects.create(symbol_id="DNA_OK", stage='accelerating')
        CompanyCapitalDNA.objects.create(symbol_id="DNA_OK", capital_type='heavy_investor')

        # 같은 DNA를 가진 다른 섹터 종목 6개 (cross-sector)
        for i in range(6):
            sym = f"DNAOK{i:02d}"
            sec = "Healthcare" if i % 2 == 0 else "Energy"
            _make_stock(sym, sector=sec, industry="VariousIndustry")
            CompanyGrowthStage.objects.create(symbol_id=sym, stage='accelerating')
            CompanyCapitalDNA.objects.create(symbol_id=sym, capital_type='heavy_investor')

        gen = PresetGenerator()
        count = gen._generate_thematic(stock, Stock.objects.none())
        assert count == 1
        preset = PeerPreset.objects.get(symbol=stock, preset_key='thematic')
        assert preset.generation_method == 'curated'
        # cross_sector 보너스 적용 확인
        assert preset.peer_count >= 5

    def test_no_growth_stage_returns_zero(self):
        """CompanyGrowthStage 없으면 0."""
        from apps.chain_sight.models import CompanyCapitalDNA

        stock = _make_stock("DNA_NGS", sector="Technology", industry="Cloud")
        CompanyCapitalDNA.objects.create(symbol_id="DNA_NGS", capital_type='balanced')

        gen = PresetGenerator()
        count = gen._generate_thematic(stock, Stock.objects.none())
        assert count == 0

    def test_no_capital_dna_returns_zero(self):
        """CompanyCapitalDNA 없으면 0."""
        from apps.chain_sight.models import CompanyGrowthStage

        stock = _make_stock("DNA_NCD", sector="Technology", industry="Cloud")
        CompanyGrowthStage.objects.create(symbol_id="DNA_NCD", stage='mature')

        gen = PresetGenerator()
        count = gen._generate_thematic(stock, Stock.objects.none())
        assert count == 0

    def test_insufficient_dna_peers_returns_zero(self):
        """같은 DNA peer < 5 → 0."""
        from apps.chain_sight.models import CompanyCapitalDNA, CompanyGrowthStage

        stock = _make_stock("DNA_LP", sector="Technology", industry="Niche")
        CompanyGrowthStage.objects.create(symbol_id="DNA_LP", stage='turnaround')
        CompanyCapitalDNA.objects.create(symbol_id="DNA_LP", capital_type='cash_hoarder')

        # 같은 DNA peer 2개만 (5 미만)
        for i in range(2):
            sym = f"DNALP{i:02d}"
            _make_stock(sym, sector="Healthcare", industry=f"H{i}")
            CompanyGrowthStage.objects.create(symbol_id=sym, stage='turnaround')
            CompanyCapitalDNA.objects.create(symbol_id=sym, capital_type='cash_hoarder')

        gen = PresetGenerator()
        count = gen._generate_thematic(stock, Stock.objects.none())
        assert count == 0


# ---------------------------------------------------------------------------
# Tests: BenchmarkCalculator.calculate_for_symbols (배치)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBenchmarkCalculateForSymbolsBatch:
    def test_explicit_symbols_success_path(self):
        """명시적 symbols 리스트 + peer 충분 → success 카운트 증가."""
        stock = _make_stock("BBA1", sector="Industrials", industry="MachX",
                            market_cap=80_000_000_000)
        _make_sp500("BBA1")
        for i in range(10):
            sym = f"BBAP{i:02d}"
            _make_stock(sym, sector="Industrials", industry="MachX",
                        market_cap=60_000_000_000)
            _make_sp500(sym)

        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbols(["BBA1"])
        assert result['total'] == 1
        assert result['success'] == 1
        assert result['errors'] == 0

    def test_nonexistent_symbol_counts_as_error(self):
        """존재하지 않는 종목 → errors += 1."""
        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbols(["NONEXIST_BBA"])
        assert result['total'] == 1
        assert result['success'] == 0
        assert result['errors'] == 1
        assert any(e['symbol'] == 'NONEXIST_BBA' for e in result['error_details'])

    def test_uses_default_sp500_when_none(self):
        """symbols=None → SP500Constituent.is_active=True 전체."""
        _make_sp500("BBADF1")
        _make_sp500("BBADF2", is_active=False)  # 비활성은 제외
        _make_stock("BBADF1", sector="Tech", industry="SW", market_cap=10_000_000_000)

        calc = BenchmarkCalculator()
        # active만 처리해야 하므로 total=1
        result = calc.calculate_for_symbols(None)
        # 활성 SP500만 카운트되는지 확인
        active_count = SP500Constituent.objects.filter(is_active=True).count()
        assert result['total'] == active_count

    def test_exception_caught_and_logged(self):
        """calculate_for_symbol에서 예외 → errors 카운트."""
        calc = BenchmarkCalculator()
        with patch.object(calc, 'calculate_for_symbol',
                          side_effect=Exception("DB error")):
            result = calc.calculate_for_symbols(["BBAEXC1", "BBAEXC2"])
        assert result['total'] == 2
        assert result['success'] == 0
        assert result['errors'] == 2


# ---------------------------------------------------------------------------
# Tests: BenchmarkCalculator._filter_by_size
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBenchmarkFilterBySize:
    def setup_method(self):
        self.calc = BenchmarkCalculator()
        _make_stock("BFSZ_M", market_cap=300_000_000_000)
        _make_stock("BFSZ_L", market_cap=50_000_000_000)
        _make_stock("BFSZ_D", market_cap=5_000_000_000)
        _make_stock("BFSZ_S", market_cap=500_000_000)

    def test_mega_only_filter(self):
        qs = self.calc._filter_by_size(Stock.objects.all(), ['mega'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert 'BFSZ_M' in symbols
        assert 'BFSZ_L' not in symbols

    def test_adjacent_buckets_filter(self):
        """[mid, large, mega] 합집합."""
        qs = self.calc._filter_by_size(Stock.objects.all(), ['mid', 'large', 'mega'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert {'BFSZ_M', 'BFSZ_L', 'BFSZ_D'}.issubset(symbols)
        assert 'BFSZ_S' not in symbols

    def test_small_only_filter(self):
        """small bucket만 → small cap 종목만."""
        qs = self.calc._filter_by_size(Stock.objects.all(), ['small'])
        symbols = set(qs.values_list('symbol', flat=True))
        assert 'BFSZ_S' in symbols
        assert 'BFSZ_D' not in symbols
        assert 'BFSZ_L' not in symbols


# ---------------------------------------------------------------------------
# Tests: BenchmarkCalculator._get_available_years
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetAvailableYears:
    def test_no_snapshots_returns_empty(self):
        """snapshot 없음 → 빈 리스트."""
        _make_stock("BAY_NS", sector="Tech", industry="SW")
        calc = BenchmarkCalculator()
        years = calc._get_available_years("BAY_NS")
        assert years == []

    def test_returns_distinct_years_descending(self):
        """여러 metric_code의 같은 해 → distinct 1개로."""
        _make_stock("BAY_DS", sector="Tech", industry="SW")
        _make_snapshot("BAY_DS", 2022, "roe", 0.10)
        _make_snapshot("BAY_DS", 2023, "roe", 0.15)
        _make_snapshot("BAY_DS", 2024, "roe", 0.20)
        # 같은 연도 다른 metric (distinct 처리되어야)
        _make_snapshot("BAY_DS", 2024, "operating_margin", 0.25)

        calc = BenchmarkCalculator()
        years = calc._get_available_years("BAY_DS")
        assert years == [2024, 2023, 2022]

    def test_max_5_years(self):
        """5년 초과 → 최근 5년만."""
        _make_stock("BAY_M5", sector="Tech", industry="SW")
        for fy in range(2018, 2025):
            _make_snapshot("BAY_M5", fy, "roe", 0.10)

        calc = BenchmarkCalculator()
        years = calc._get_available_years("BAY_M5")
        assert len(years) == 5
        assert years == [2024, 2023, 2022, 2021, 2020]


# ---------------------------------------------------------------------------
# Tests: BenchmarkCalculator._calculate_industry_benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCalculateIndustryBenchmarks:
    def test_insufficient_industry_symbols(self):
        """industry 종목 < 2 → 0."""
        _make_stock("IB_LP", industry="UltraNiche")
        _make_sp500("IB_LP")

        calc = BenchmarkCalculator()
        count = calc._calculate_industry_benchmarks("UltraNiche", [2024])
        assert count == 0

    def test_normal_industry_benchmark_created(self):
        """industry 종목 5개 + 모두 metric 값 있음 → benchmark 생성."""
        _make_metric_def("roa", higher_is_better=True, is_benchmarkable=True)
        for i in range(5):
            sym = f"IBOK{i:02d}"
            _make_stock(sym, industry="WidgetMfg")
            _make_sp500(sym)
            _make_snapshot(sym, 2024, "roa", 0.05 + i * 0.01)

        calc = BenchmarkCalculator()
        count = calc._calculate_industry_benchmarks("WidgetMfg", [2024])
        assert count >= 1

        bench = IndustryMetricBenchmark.objects.filter(
            industry="WidgetMfg", fiscal_year=2024, metric_code_id="roa"
        ).first()
        assert bench is not None
        assert bench.sample_count == 5
        # high confidence: count >= 10? sample_count=5 → medium
        assert bench.benchmark_confidence in ('medium', 'high')

    def test_low_sample_returns_zero_for_metric(self):
        """sample < 2 인 metric → 해당 metric은 skip."""
        _make_metric_def("custom_low", is_benchmarkable=True)
        # industry 종목 3개지만 metric 데이터는 1개만
        for i in range(3):
            sym = f"IBLOW{i:02d}"
            _make_stock(sym, industry="LowSampleIndustry")
            _make_sp500(sym)
        # 1개 종목만 snapshot
        _make_snapshot("IBLOW00", 2024, "custom_low", 0.10)

        calc = BenchmarkCalculator()
        count = calc._calculate_industry_benchmarks("LowSampleIndustry", [2024])
        # custom_low metric은 sample < 2 라 skip되지만, 다른 benchmarkable 지표가 있을 수 있음
        # custom_low로 IndustryMetricBenchmark 만들어지지 않아야 함
        bench = IndustryMetricBenchmark.objects.filter(
            industry="LowSampleIndustry", fiscal_year=2024, metric_code_id="custom_low"
        ).first()
        assert bench is None


# ---------------------------------------------------------------------------
# Tests: MetricCalculator._calc_ocf_trend_placeholder
# ---------------------------------------------------------------------------


class TestOcfTrendPlaceholder:
    def setup_method(self):
        self.calc = MetricCalculator.__new__(MetricCalculator)

    def test_returns_missing_with_phase2_message(self):
        """3년 추세 미구현 → (None, 'missing', 'Phase 2 메시지')."""
        val, status, reason = self.calc._calc_ocf_trend_placeholder()
        assert val is None
        assert status == 'missing'
        assert 'Phase 2' in reason

    def test_no_args_required(self):
        """파라미터 없이 호출 가능."""
        result = self.calc._calc_ocf_trend_placeholder()
        assert isinstance(result, tuple)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Tests: MetricCalculator._update_latest
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUpdateLatest:
    def test_creates_latest_for_new_symbol(self):
        """기존 CompanyMetricLatest 없는 경우 → 새로 생성."""
        stock = _make_stock("UL_NEW", sector="Tech", industry="SW")
        _make_snapshot("UL_NEW", 2024, "roe", 0.18)
        _make_snapshot("UL_NEW", 2024, "fcf_margin", 0.22)

        calc = MetricCalculator()
        updated = calc._update_latest(stock, 2024)
        assert updated == 2

        roe_latest = CompanyMetricLatest.objects.get(symbol=stock, metric_code_id="roe")
        assert float(roe_latest.latest_value) == pytest.approx(0.18)
        assert roe_latest.latest_fiscal_year == 2024

    def test_updates_existing_latest(self):
        """기존 CompanyMetricLatest 있는 경우 → 갱신."""
        stock = _make_stock("UL_UPD", sector="Tech", industry="SW")
        md = _make_metric_def("roe")
        # 기존 데이터
        CompanyMetricLatest.objects.create(
            symbol=stock, metric_code=md,
            latest_value=Decimal("0.10"), latest_fiscal_year=2023,
        )
        # 새 snapshot
        _make_snapshot("UL_UPD", 2024, "roe", 0.20)

        calc = MetricCalculator()
        calc._update_latest(stock, 2024)

        latest = CompanyMetricLatest.objects.get(symbol=stock, metric_code_id="roe")
        assert latest.latest_fiscal_year == 2024
        assert float(latest.latest_value) == pytest.approx(0.20)

    def test_no_snapshots_for_year_returns_zero(self):
        """해당 fiscal_year의 snapshot 없음 → 0."""
        stock = _make_stock("UL_ZERO", sector="Tech", industry="SW")
        calc = MetricCalculator()
        updated = calc._update_latest(stock, 2024)
        assert updated == 0


# ---------------------------------------------------------------------------
# Tests: MetricCalculator.calculate_for_symbols (배치)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMetricCalculateForSymbolsBatch:
    def test_explicit_symbols_with_errors(self):
        """일부는 not found → fail / 일부는 성공."""
        calc = MetricCalculator()
        # 두 개 다 존재하지 않음 → 모두 fail
        result = calc.calculate_for_symbols(["NXMC1", "NXMC2"])
        assert result['total'] == 2
        assert result['success'] == 0

    def test_uses_default_sp500_when_none(self):
        """symbols=None → SP500 활성 전체."""
        _make_sp500("MCDF1")
        _make_sp500("MCDF2", is_active=False)
        # 활성 SP500 종목만 처리되는지

        calc = MetricCalculator()
        with patch.object(calc, 'calculate_for_symbol',
                          return_value={'symbol': 'X', 'error': 'Stock not found'}):
            result = calc.calculate_for_symbols(None)
        active_count = SP500Constituent.objects.filter(is_active=True).count()
        assert result['total'] == active_count


# ---------------------------------------------------------------------------
# Tests: RelativeMetricCalculator.calculate_for_symbols (확장)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRelativeCalculateForSymbolsExtended:
    def test_uses_default_sp500_when_none(self):
        """symbols=None → SP500 활성 전체."""
        _make_sp500("RXDF1")
        _make_sp500("RXDF2", is_active=False)

        calc = RelativeMetricCalculator()
        result = calc.calculate_for_symbols(None)
        active_count = SP500Constituent.objects.filter(is_active=True).count()
        assert result['total'] == active_count
        # 모두 stock 없거나 industry 없으므로 skip
        assert result['skip'] == active_count

    def test_exception_counted_as_skip(self):
        """_calc_rev_growth_vs_industry 예외 → skip."""
        calc = RelativeMetricCalculator()
        with patch.object(calc, '_calc_rev_growth_vs_industry',
                          side_effect=Exception("oops")):
            result = calc.calculate_for_symbols(["RXEX1", "RXEX2"])
        assert result['total'] == 2
        assert result['success'] == 0
        assert result['skip'] == 2

    def test_mixed_success_and_skip(self):
        """일부 성공 / 일부 industry 없음 → mixed."""
        _make_metric_def('rev_growth_vs_industry')
        # 성공 케이스
        _make_stock("RXMS1", industry="Cloud SaaS")
        _make_snapshot("RXMS1", 2024, "revenue_growth_yoy", 0.20)
        IndustryMetricBenchmark.objects.create(
            industry="Cloud SaaS", fiscal_year=2024,
            metric_code=_make_metric_def("revenue_growth_yoy"),
            median_value=Decimal("0.10"), sample_count=10,
            benchmark_confidence='high',
        )
        # skip 케이스 (industry 없음)
        _make_stock("RXMS2", industry=None)

        calc = RelativeMetricCalculator()
        result = calc.calculate_for_symbols(["RXMS1", "RXMS2"])
        assert result['total'] == 2
        assert result['success'] == 1
        assert result['skip'] == 1


# ---------------------------------------------------------------------------
# Tests: interpretation.generate_summary_text (추가 분기)
# ---------------------------------------------------------------------------


class TestGenerateSummaryTextEdgeCases:
    def test_green_red_combined(self):
        """green 1 + red 1 → 강점 + 주의 둘 다 포함."""
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('valuation', 'red', 20),
        ]
        text = generate_summary_text(signals)
        assert '강점' in text
        assert '주의 필요' in text

    def test_four_greens_no_overall_summary(self):
        """green 4개 (5 미만) → '전반적으로 양호' 미포함."""
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('growth', 'green', 75),
            _make_signal('financial_structure', 'green', 70),
            _make_signal('cash_flow_quality', 'green', 65),
        ]
        text = generate_summary_text(signals)
        assert '전반적으로 양호' not in text
        assert '높은' in text

    def test_five_greens_with_red_uses_overall_branch(self):
        """green >= 5 + red 1 → '전반적으로 양호' 분기 진입 (red part 결합)."""
        signals = [
            _make_signal('profitability', 'green', 80),
            _make_signal('growth', 'green', 75),
            _make_signal('financial_structure', 'green', 70),
            _make_signal('cash_flow_quality', 'green', 65),
            _make_signal('operational_efficiency', 'green', 60),
            _make_signal('valuation', 'red', 20),
        ]
        text = generate_summary_text(signals)
        assert '전반적으로 양호' in text
        assert '주의 필요' in text


# ---------------------------------------------------------------------------
# Tests: interpretation.generate_metric_interpretation (추가 분기)
# ---------------------------------------------------------------------------


class TestGenerateMetricInterpretationEdgeCases:
    def test_none_percentile_skips_position(self):
        """percentile_rank=None → 위치 부분 미포함."""
        text = generate_metric_interpretation(
            'roe', True, None, '', 'normal', 'high'
        )
        assert '상위' not in text
        assert '하위' not in text
        assert '중앙값' not in text
        # 방향성은 항상 포함
        assert '높을수록' in text

    def test_combined_trend_and_low_confidence(self):
        """improving + limited 신뢰도 → 추세 + 표본 경고."""
        text = generate_metric_interpretation(
            'roe', True, 80.0, 'improving', 'normal', 'limited'
        )
        assert '개선' in text
        assert '표본이 적어' in text

    def test_unstable_value_status_with_trend(self):
        """unstable + improving 동시 → 둘 다 표시."""
        text = generate_metric_interpretation(
            'interest_coverage', True, 60.0, 'improving', 'unstable', 'high'
        )
        assert '개선' in text
        assert '변동이 크므로' in text
