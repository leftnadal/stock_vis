"""
BenchmarkCalculator 단위 테스트

테스트 대상:
  - assign_size_bucket() — 시가총액 → size bucket 매핑
  - get_adjacent_buckets() — 인접 bucket 반환
  - BenchmarkCalculator._determine_confidence() — peer 수 + basis 기반 신뢰도
  - BenchmarkCalculator._select_peers() — peer 선정 알고리즘
  - BenchmarkCalculator.calculate_for_symbol() — 전체 플로우
  - BenchmarkCalculator._calculate_benchmarks_for_year() — benchmark 통계 계산
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.metrics.models import (
    CompanyMetricSnapshot,
    MetricDefinition,
    PeerListCache,
)
from packages.shared.stocks.models import SP500Constituent, Stock
from services.validation.models import CompanyBenchmarkDelta
from services.validation.services.benchmark_calculator import (
    BenchmarkCalculator,
    assign_size_bucket,
    get_adjacent_buckets,
)

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


def _make_metric_def(code, higher_is_better=True, is_benchmarkable=True):
    return MetricDefinition.objects.get_or_create(
        metric_code=code,
        defaults={
            'display_name': code,
            'display_name_en': code,
            'category': 'profitability',
            'unit': 'ratio',
            'higher_is_better': higher_is_better,
            'is_benchmarkable': is_benchmarkable,
        },
    )[0]


def _make_snapshot(symbol, fy, metric_code, value, status='normal'):
    md = _make_metric_def(metric_code)
    return CompanyMetricSnapshot.objects.get_or_create(
        symbol_id=symbol,
        fiscal_year=fy,
        metric_code=md,
        defaults={
            'metric_value': Decimal(str(value)) if value is not None else None,
            'value_status': status,
        },
    )[0]


# ---------------------------------------------------------------------------
# Tests: assign_size_bucket (순수 함수)
# ---------------------------------------------------------------------------


class TestAssignSizeBucket:
    def test_mega_cap(self):
        assert assign_size_bucket(300_000_000_000) == 'mega'

    def test_large_cap(self):
        assert assign_size_bucket(50_000_000_000) == 'large'

    def test_mid_cap(self):
        assert assign_size_bucket(5_000_000_000) == 'mid'

    def test_small_cap(self):
        assert assign_size_bucket(500_000_000) == 'small'

    def test_none_defaults_to_mid(self):
        assert assign_size_bucket(None) == 'mid'

    def test_boundary_mega(self):
        """200B 정확히 → mega."""
        assert assign_size_bucket(200_000_000_000) == 'mega'

    def test_boundary_large(self):
        """10B 정확히 → large."""
        assert assign_size_bucket(10_000_000_000) == 'large'

    def test_boundary_mid(self):
        """2B 정확히 → mid."""
        assert assign_size_bucket(2_000_000_000) == 'mid'


# ---------------------------------------------------------------------------
# Tests: get_adjacent_buckets (순수 함수)
# ---------------------------------------------------------------------------


class TestGetAdjacentBuckets:
    def test_mega_adjacent(self):
        """mega → [large, mega]."""
        result = get_adjacent_buckets('mega')
        assert 'mega' in result
        assert 'large' in result
        assert len(result) == 2

    def test_large_adjacent(self):
        """large → [mid, large, mega]."""
        result = get_adjacent_buckets('large')
        assert set(result) == {'mid', 'large', 'mega'}

    def test_mid_adjacent(self):
        """mid → [small, mid, large]."""
        result = get_adjacent_buckets('mid')
        assert set(result) == {'small', 'mid', 'large'}

    def test_small_adjacent(self):
        """small → [small, mid]."""
        result = get_adjacent_buckets('small')
        assert 'small' in result
        assert 'mid' in result
        assert len(result) == 2

    def test_unknown_defaults_to_mid_index(self):
        """알 수 없는 bucket → index=2 (large) 기준 인접."""
        result = get_adjacent_buckets('unknown')
        # SIZE_BUCKETS[2] = 'large', adjacent = [1:5] = ['mid', 'large', 'mega']
        assert set(result) == {'mid', 'large', 'mega'}


# ---------------------------------------------------------------------------
# Tests: _determine_confidence
# ---------------------------------------------------------------------------


class TestDetermineConfidence:
    def setup_method(self):
        self.calc = BenchmarkCalculator()

    def test_high_confidence(self):
        assert self.calc._determine_confidence(20, 'industry_size') == 'high'

    def test_medium_confidence(self):
        assert self.calc._determine_confidence(10, 'industry') == 'medium'

    def test_low_confidence(self):
        assert self.calc._determine_confidence(5, 'sector') == 'low'

    def test_limited_confidence(self):
        assert self.calc._determine_confidence(3, 'sector') == 'limited'

    def test_high_requires_industry_size(self):
        """peer >= 15 but basis != industry_size → medium."""
        assert self.calc._determine_confidence(20, 'sector') == 'medium'


@pytest.mark.django_db
class TestSelectPeers:
    def test_industry_size_match(self):
        """같은 industry + 인접 size >= 8 → industry_size."""
        stock = _make_stock("BSEL", sector="Technology", industry="Cloud",
                            market_cap=50_000_000_000)
        _make_sp500("BSEL")
        for i in range(10):
            sym = f"CLD{i:02d}"
            _make_stock(sym, sector="Technology", industry="Cloud",
                        market_cap=40_000_000_000)
            _make_sp500(sym)

        calc = BenchmarkCalculator()
        peers, basis = calc._select_peers(stock)
        assert basis == 'industry_size'
        assert peers.count() >= 8

    def test_fallback_to_sector(self):
        """industry peer 부족 → sector fallback."""
        stock = _make_stock("BFBS", sector="Materials", industry="Rare Earth",
                            market_cap=15_000_000_000)
        _make_sp500("BFBS")
        # 같은 sector 다른 industry
        for i in range(5):
            sym = f"MAT{i:02d}"
            _make_stock(sym, sector="Materials", industry="Chemicals",
                        market_cap=15_000_000_000)
            _make_sp500(sym)

        calc = BenchmarkCalculator()
        peers, basis = calc._select_peers(stock)
        assert basis == 'sector'


@pytest.mark.django_db
class TestCalculateForSymbol:
    def test_stock_not_found(self):
        """존재하지 않는 종목 → error."""
        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbol("NONEXIST")
        assert result['error'] == 'Stock not found'

    def test_full_flow(self):
        """peer 존재 + snapshot 데이터 → benchmark 계산 완료."""
        stock = _make_stock("BFUL", sector="Industrials", industry="Aerospace",
                            market_cap=80_000_000_000)
        _make_sp500("BFUL")
        md = _make_metric_def("roe", higher_is_better=True)
        _make_snapshot("BFUL", 2024, "roe", 0.15)

        for i in range(10):
            sym = f"AERO{i:02d}"
            _make_stock(sym, sector="Industrials", industry="Aerospace",
                        market_cap=60_000_000_000)
            _make_sp500(sym)
            _make_snapshot(sym, 2024, "roe", 0.10 + i * 0.01)

        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbol("BFUL")

        assert 'error' not in result
        assert result['peer_count'] >= 8
        assert result['metrics_calculated'] >= 1

        # PeerListCache 생성 확인
        cache = PeerListCache.objects.filter(symbol=stock).first()
        assert cache is not None
        assert cache.peer_count >= 8
