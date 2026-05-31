"""
PR-4~5 validation 앱 모델 테스트

검증 범위:
- SP500Constituent: 새 필드 3개 (is_core_universe, universe_source, industry)
- CompanyMetricLatest: FK, unique_together, signal/trend
- CompanyBenchmarkDelta: FK, unique_together, benchmark_type
- CategorySignal: unique_together, score/grade nullable
- ValidationNewsSummary: OneToOne, risk flags
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from packages.shared.metrics.models import MetricDefinition
from packages.shared.stocks.models import SP500Constituent
from services.validation.models import (
    CategorySignal,
    CompanyBenchmarkDelta,
    CompanyMetricLatest,
    ValidationNewsSummary,
)

# ===== PR-4: SP500Constituent 필드 추가 =====

class TestSP500ConstituentNewFields:

    @pytest.mark.django_db
    def test_new_fields_exist(self):
        """is_core_universe, universe_source, industry 필드 존재"""
        field_names = [f.name for f in SP500Constituent._meta.get_fields()]
        for name in ['is_core_universe', 'universe_source', 'industry']:
            assert name in field_names

    @pytest.mark.django_db
    def test_defaults_on_create(self):
        """새 필드 default 값 확인"""
        sp = SP500Constituent.objects.create(
            symbol='TEST', company_name='Test Corp', sector='Technology',
        )
        assert sp.is_core_universe is True
        assert sp.universe_source == 'sp500'
        assert sp.industry == ''

    @pytest.mark.django_db
    def test_manual_universe_source(self):
        sp = SP500Constituent.objects.create(
            symbol='MANUAL', company_name='Manual Corp', sector='Financials',
            universe_source='manual', is_core_universe=False,
            industry='Asset Management',
        )
        assert sp.universe_source == 'manual'
        assert sp.is_core_universe is False
        assert sp.industry == 'Asset Management'

    @pytest.mark.django_db
    def test_existing_data_preserved(self):
        """기존 레코드에 새 필드가 default 값으로 들어감"""
        sp = SP500Constituent.objects.create(
            symbol='OLD', company_name='Old Corp', sector='Healthcare',
        )
        sp.refresh_from_db()
        assert sp.is_core_universe is True
        assert sp.universe_source == 'sp500'


# ===== PR-4: CompanyMetricLatest =====

class TestCompanyMetricLatest:

    @pytest.mark.django_db
    def test_create_metric_latest(self, stock_aapl):
        md = MetricDefinition.objects.get(pk='gross_margin')
        latest = CompanyMetricLatest.objects.create(
            symbol=stock_aapl,
            metric_code=md,
            latest_value=Decimal('0.462000'),
            latest_fiscal_year=2024,
            trend_label='improving',
            trend_slope=Decimal('0.015000'),
            trend_years_used=3,
            signal='green',
            signal_reason='Above threshold',
        )
        assert latest.pk is not None
        assert latest.signal == 'green'
        assert latest.trend_label == 'improving'

    @pytest.mark.django_db
    def test_unique_together(self, stock_aapl):
        """같은 (symbol, metric_code) 중복 불가"""
        md = MetricDefinition.objects.get(pk='roe')
        CompanyMetricLatest.objects.create(
            symbol=stock_aapl, metric_code=md,
            latest_value=Decimal('1.500000'),
        )
        with pytest.raises(IntegrityError):
            CompanyMetricLatest.objects.create(
                symbol=stock_aapl, metric_code=md,
                latest_value=Decimal('1.600000'),
            )

    @pytest.mark.django_db
    def test_warning_flag(self, stock_aapl):
        md = MetricDefinition.objects.get(pk='debt_to_equity')
        latest = CompanyMetricLatest.objects.create(
            symbol=stock_aapl, metric_code=md,
            latest_value=Decimal('3.500000'),
            signal='red',
            warning_flag=True,
            warning_message='Debt ratio exceeds safe threshold',
        )
        assert latest.warning_flag is True
        assert 'Debt' in latest.warning_message

    @pytest.mark.django_db
    def test_nullable_values(self, stock_aapl):
        md = MetricDefinition.objects.get(pk='cash_runway_years')
        latest = CompanyMetricLatest.objects.create(
            symbol=stock_aapl, metric_code=md,
            latest_value=None, latest_fiscal_year=None,
        )
        assert latest.latest_value is None

    @pytest.mark.django_db
    def test_str_representation(self, stock_aapl):
        md = MetricDefinition.objects.get(pk='net_margin')
        latest = CompanyMetricLatest.objects.create(
            symbol=stock_aapl, metric_code=md,
            latest_value=Decimal('0.250000'), signal='green',
        )
        s = str(latest)
        assert 'AAPL' in s
        assert 'net_margin' in s


# ===== PR-4: CompanyBenchmarkDelta =====

class TestCompanyBenchmarkDelta:

    @pytest.mark.django_db
    def test_create_benchmark_delta(self, stock_aapl):
        md = MetricDefinition.objects.get(pk='gross_margin')
        delta = CompanyBenchmarkDelta.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=md,
            company_value=Decimal('0.462000'),
            benchmark_type='peer',
            benchmark_median=Decimal('0.420000'),
            benchmark_p25=Decimal('0.350000'),
            benchmark_p75=Decimal('0.510000'),
            benchmark_confidence='high',
            delta_vs_median=Decimal('0.042000'),
            percentile_rank=Decimal('72.00'),
            relative_signal='above',
        )
        assert delta.benchmark_type == 'peer'
        assert delta.relative_signal == 'above'

    @pytest.mark.django_db
    def test_unique_together(self, stock_aapl):
        """같은 (symbol, fiscal_year, metric_code) 중복 불가"""
        md = MetricDefinition.objects.get(pk='roe')
        CompanyBenchmarkDelta.objects.create(
            symbol=stock_aapl, fiscal_year=2024, metric_code=md,
            benchmark_type='industry',
        )
        with pytest.raises(IntegrityError):
            CompanyBenchmarkDelta.objects.create(
                symbol=stock_aapl, fiscal_year=2024, metric_code=md,
                benchmark_type='peer',
            )

    @pytest.mark.django_db
    def test_industry_benchmark_type(self, stock_aapl):
        md = MetricDefinition.objects.get(pk='operating_margin')
        delta = CompanyBenchmarkDelta.objects.create(
            symbol=stock_aapl, fiscal_year=2024, metric_code=md,
            benchmark_type='industry',
            benchmark_confidence='medium',
            relative_signal='inline',
        )
        assert delta.benchmark_type == 'industry'
        assert delta.benchmark_confidence == 'medium'


# ===== PR-5: CategorySignal =====

class TestCategorySignal:

    @pytest.mark.django_db
    def test_create_category_score(self, stock_aapl):
        cs = CategorySignal.objects.create(
            symbol=stock_aapl,
            category='profitability',
            signal='green',
            signal_reason='All profitability metrics above median',
            contributing_metrics=[
                {'metric': 'gross_margin', 'value': 0.46, 'signal': 'green'},
                {'metric': 'roe', 'value': 1.56, 'signal': 'green'},
            ],
        )
        assert cs.pk is not None
        assert len(cs.contributing_metrics) == 2

    @pytest.mark.django_db
    def test_unique_together(self, stock_aapl):
        """같은 (symbol, category) 중복 불가"""
        CategorySignal.objects.create(
            symbol=stock_aapl, category='growth', signal='yellow',
        )
        with pytest.raises(IntegrityError):
            CategorySignal.objects.create(
                symbol=stock_aapl, category='growth', signal='red',
            )

    @pytest.mark.django_db
    def test_score_nullable(self, stock_aapl):
        """score는 내부 계산용, nullable"""
        cs = CategorySignal.objects.create(
            symbol=stock_aapl, category='financial_structure',
            signal='yellow', score=None,
        )
        assert cs.score is None

    @pytest.mark.django_db
    def test_gray_signal(self, stock_aapl):
        """특수 산업은 gray 신호"""
        cs = CategorySignal.objects.create(
            symbol=stock_aapl, category='financial_structure',
            fiscal_year=2025,
            signal='gray',
            signal_reason='금융업 특성상 일반 해석과 다를 수 있습니다',
            metric_count=6, valid_metric_count=0,
        )
        assert cs.signal == 'gray'
        assert cs.valid_metric_count == 0

    @pytest.mark.django_db
    def test_metric_counts(self, stock_aapl):
        """metric_count, valid_metric_count 필드"""
        cs = CategorySignal.objects.create(
            symbol=stock_aapl, category='cash_flow_quality',
            signal='green',
            score=Decimal('82.50'),
            metric_count=6, valid_metric_count=5,
            signal_reason='5개 지표 중 4개 업종 상위 35%',
        )
        assert cs.metric_count == 6
        assert cs.valid_metric_count == 5

    @pytest.mark.django_db
    def test_all_7_categories(self, stock_aapl):
        """7개 카테고리 모두 생성 가능"""
        categories = [
            'profitability', 'growth', 'financial_structure',
            'cash_flow_quality', 'operational_efficiency',
            'dilution_shareholder', 'valuation',
        ]
        for cat in categories:
            CategorySignal.objects.create(
                symbol=stock_aapl, category=cat, signal='green',
            )
        assert CategorySignal.objects.filter(symbol=stock_aapl).count() == 7


# ===== PR-5: ValidationNewsSummary =====

class TestValidationNewsSummary:

    @pytest.mark.django_db
    def test_create_news_summary(self, stock_aapl):
        ns = ValidationNewsSummary.objects.create(
            symbol=stock_aapl,
            event_count_30d=12,
            event_count_90d=35,
            avg_sentiment_30d=Decimal('0.650'),
            sentiment_trend='improving',
            dominant_event_type='earnings',
            high_importance_count=3,
        )
        assert ns.pk == 'AAPL'
        assert ns.event_count_30d == 12

    @pytest.mark.django_db
    def test_one_to_one(self, stock_aapl):
        """같은 Stock에 두 번 생성 불가"""
        ValidationNewsSummary.objects.create(symbol=stock_aapl)
        with pytest.raises(IntegrityError):
            ValidationNewsSummary.objects.create(symbol=stock_aapl)

    @pytest.mark.django_db
    def test_risk_flags(self, stock_aapl):
        ns = ValidationNewsSummary.objects.create(
            symbol=stock_aapl,
            has_regulatory_risk=True,
            has_exec_change=True,
            has_guidance_cut=False,
        )
        assert ns.has_regulatory_risk is True
        assert ns.has_exec_change is True
        assert ns.has_guidance_cut is False

    @pytest.mark.django_db
    def test_recent_highlights_json(self, stock_aapl):
        ns = ValidationNewsSummary.objects.create(
            symbol=stock_aapl,
            recent_highlights=[
                {'title': 'AAPL beats Q4', 'sentiment': 0.8, 'event_type': 'earnings', 'date': '2024-10-31'},
                {'title': 'FDA approval', 'sentiment': 0.6, 'event_type': 'regulatory', 'date': '2024-11-15'},
            ],
        )
        ns.refresh_from_db()
        assert len(ns.recent_highlights) == 2
        assert ns.recent_highlights[0]['event_type'] == 'earnings'

    @pytest.mark.django_db
    def test_reverse_relation(self, stock_aapl):
        ValidationNewsSummary.objects.create(
            symbol=stock_aapl, event_count_30d=5,
        )
        assert stock_aapl.validation_news_summary.event_count_30d == 5
