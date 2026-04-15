"""
RelativeMetricCalculator 단위 테스트

테스트 대상:
  - _calc_rev_growth_vs_industry() — 자사 매출 성장률 vs 업종 median
  - calculate_for_symbols() — 배치 계산
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from stocks.models import Stock, SP500Constituent
from metrics.models import (
    CompanyMetricSnapshot, MetricDefinition, IndustryMetricBenchmark,
)
from validation.services.relative_metrics import RelativeMetricCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stock(symbol, sector="Technology", industry="Software"):
    return Stock.objects.get_or_create(
        symbol=symbol,
        defaults={
            'stock_name': f'{symbol} Inc',
            'exchange': 'NASDAQ',
            'sector': sector,
            'industry': industry,
        },
    )[0]


def _make_sp500(symbol):
    return SP500Constituent.objects.get_or_create(
        symbol=symbol,
        defaults={'company_name': f'{symbol} Corp', 'sector': 'Technology', 'is_active': True},
    )[0]


def _make_metric_def(code='revenue_growth_yoy'):
    return MetricDefinition.objects.get_or_create(
        metric_code=code,
        defaults={
            'display_name': code,
            'display_name_en': code,
            'category': 'growth',
            'unit': 'ratio',
            'higher_is_better': True,
            'is_benchmarkable': True,
        },
    )[0]


def _ensure_rev_growth_vs_industry_def():
    """rev_growth_vs_industry MetricDefinition 사전 생성 (FK 제약 충족)."""
    return _make_metric_def('rev_growth_vs_industry')


def _make_snapshot(symbol, fy, code, value):
    md = _make_metric_def(code)
    return CompanyMetricSnapshot.objects.get_or_create(
        symbol_id=symbol,
        fiscal_year=fy,
        metric_code=md,
        defaults={
            'metric_value': Decimal(str(value)),
            'value_status': 'normal',
        },
    )[0]


def _make_industry_benchmark(industry, fy, code, median):
    md = _make_metric_def(code)
    return IndustryMetricBenchmark.objects.get_or_create(
        industry=industry,
        fiscal_year=fy,
        metric_code=md,
        defaults={
            'median_value': Decimal(str(median)),
            'sample_count': 10,
            'benchmark_confidence': 'high',
        },
    )[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCalcRevGrowthVsIndustry:
    def setup_method(self):
        _ensure_rev_growth_vs_industry_def()

    def test_normal_calculation(self):
        """자사 0.15, industry median 0.10 → relative = 0.05."""
        stock = _make_stock("RELN", industry="Cloud Computing")
        _make_snapshot("RELN", 2024, "revenue_growth_yoy", 0.15)
        _make_industry_benchmark("Cloud Computing", 2024, "revenue_growth_yoy", 0.10)

        calc = RelativeMetricCalculator()
        result = calc._calc_rev_growth_vs_industry("RELN")

        assert result is True
        snap = CompanyMetricSnapshot.objects.filter(
            symbol_id="RELN", fiscal_year=2024, metric_code_id="rev_growth_vs_industry",
        ).first()
        assert snap is not None
        assert float(snap.metric_value) == pytest.approx(0.05, abs=0.001)

    def test_negative_relative(self):
        """자사 0.05, industry 0.12 → -0.07."""
        stock = _make_stock("RELN2", industry="Semiconductors")
        _make_snapshot("RELN2", 2024, "revenue_growth_yoy", 0.05)
        _make_industry_benchmark("Semiconductors", 2024, "revenue_growth_yoy", 0.12)

        calc = RelativeMetricCalculator()
        result = calc._calc_rev_growth_vs_industry("RELN2")
        assert result is True
        snap = CompanyMetricSnapshot.objects.filter(
            symbol_id="RELN2", fiscal_year=2024, metric_code_id="rev_growth_vs_industry",
        ).first()
        assert float(snap.metric_value) == pytest.approx(-0.07, abs=0.001)

    def test_no_stock(self):
        """종목이 없으면 False."""
        calc = RelativeMetricCalculator()
        result = calc._calc_rev_growth_vs_industry("NOSTOCK")
        assert result is False

    def test_no_industry(self):
        """industry 없는 종목 → False."""
        _make_stock("NOIND", industry=None)
        calc = RelativeMetricCalculator()
        result = calc._calc_rev_growth_vs_industry("NOIND")
        assert result is False

    def test_no_snapshot(self):
        """revenue_growth_yoy snapshot 없으면 False."""
        _make_stock("NOSNP", industry="Biotech")
        calc = RelativeMetricCalculator()
        result = calc._calc_rev_growth_vs_industry("NOSNP")
        assert result is False

    def test_no_industry_benchmark(self):
        """IndustryMetricBenchmark 없으면 False (업데이트 없음)."""
        _make_stock("NOBCH", industry="Quantum Computing")
        _make_snapshot("NOBCH", 2024, "revenue_growth_yoy", 0.20)
        # industry benchmark 미생성

        calc = RelativeMetricCalculator()
        result = calc._calc_rev_growth_vs_industry("NOBCH")
        assert result is False

    def test_multiple_years(self):
        """여러 연도 데이터 → 각 연도별 relative 계산."""
        stock = _make_stock("RMUL", industry="Cloud SaaS")
        _make_snapshot("RMUL", 2023, "revenue_growth_yoy", 0.20)
        _make_snapshot("RMUL", 2024, "revenue_growth_yoy", 0.15)
        _make_industry_benchmark("Cloud SaaS", 2023, "revenue_growth_yoy", 0.10)
        _make_industry_benchmark("Cloud SaaS", 2024, "revenue_growth_yoy", 0.12)

        calc = RelativeMetricCalculator()
        result = calc._calc_rev_growth_vs_industry("RMUL")
        assert result is True

        snap_2023 = CompanyMetricSnapshot.objects.filter(
            symbol_id="RMUL", fiscal_year=2023, metric_code_id="rev_growth_vs_industry",
        ).first()
        snap_2024 = CompanyMetricSnapshot.objects.filter(
            symbol_id="RMUL", fiscal_year=2024, metric_code_id="rev_growth_vs_industry",
        ).first()
        assert snap_2023 is not None
        assert snap_2024 is not None
        assert float(snap_2023.metric_value) == pytest.approx(0.10, abs=0.001)
        assert float(snap_2024.metric_value) == pytest.approx(0.03, abs=0.001)


@pytest.mark.django_db
class TestCalculateForSymbols:
    def setup_method(self):
        _ensure_rev_growth_vs_industry_def()

    def test_batch_with_explicit_symbols(self):
        """명시적 symbols 리스트로 배치 계산."""
        _make_stock("RBAT1", industry="EV")
        _make_stock("RBAT2", industry="EV")
        _make_snapshot("RBAT1", 2024, "revenue_growth_yoy", 0.25)
        _make_snapshot("RBAT2", 2024, "revenue_growth_yoy", 0.10)
        _make_industry_benchmark("EV", 2024, "revenue_growth_yoy", 0.15)

        calc = RelativeMetricCalculator()
        result = calc.calculate_for_symbols(["RBAT1", "RBAT2"])
        assert result['total'] == 2
        assert result['success'] == 2
        assert result['skip'] == 0
