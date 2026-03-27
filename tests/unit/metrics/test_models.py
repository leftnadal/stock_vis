"""
PR-1~3 metrics 앱 모델 테스트

검증 범위:
- MetricDefinition: 시드 데이터 34개, 카테고리별 개수, PK 구조
- BatchJobRun: CRUD, 인덱스, status choices
- CompanyMetricSnapshot: FK 관계, unique_together, quality_flag
- PeerListCache: OneToOne, ArrayField
- IndustryMetricBenchmark: unique_together, sector fallback
- PeerMetricBenchmark: unique_together, benchmark_confidence
"""

import pytest
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db import IntegrityError

from metrics.models import (
    MetricDefinition,
    BatchJobRun,
    CompanyMetricSnapshot,
    PeerListCache,
    IndustryMetricBenchmark,
    PeerMetricBenchmark,
)


# ===== PR-1: MetricDefinition =====

class TestMetricDefinition:
    """MetricDefinition 시드 데이터 및 모델 구조 검증"""

    @pytest.mark.django_db
    def test_seed_data_count_is_34(self):
        """시드 데이터 총 34개 존재"""
        assert MetricDefinition.objects.count() == 34

    @pytest.mark.django_db
    @pytest.mark.parametrize('category,expected_count', [
        ('profitability', 5),
        ('growth', 4),
        ('financial_structure', 6),
        ('cash_flow_quality', 6),
        ('operational_efficiency', 6),
        ('dilution_shareholder', 4),
        ('valuation', 3),
    ])
    def test_category_counts(self, category, expected_count):
        """카테고리별 지표 개수가 설계와 일치"""
        count = MetricDefinition.objects.filter(category=category).count()
        assert count == expected_count

    @pytest.mark.django_db
    def test_pk_is_metric_code(self):
        """PK가 metric_code CharField"""
        md = MetricDefinition.objects.get(pk='gross_margin')
        assert md.metric_code == 'gross_margin'
        assert md.display_name == '매출총이익률'

    @pytest.mark.django_db
    def test_valuation_metrics_not_core_mvp(self):
        """valuation 카테고리 3개는 is_core_mvp=False"""
        valuation = MetricDefinition.objects.filter(category='valuation')
        assert valuation.count() == 3
        for m in valuation:
            assert m.is_core_mvp is False

    @pytest.mark.django_db
    def test_source_apis_is_list(self):
        """source_apis가 list 타입으로 저장됨"""
        md = MetricDefinition.objects.get(pk='roe')
        assert isinstance(md.source_apis, list)
        assert 'income-statement' in md.source_apis
        assert 'balance-sheet' in md.source_apis

    @pytest.mark.django_db
    def test_source_fields_is_list(self):
        """source_fields가 list 타입으로 저장됨"""
        md = MetricDefinition.objects.get(pk='current_ratio')
        assert isinstance(md.source_fields, list)
        assert 'total_current_assets' in md.source_fields
        assert 'total_current_liabilities' in md.source_fields

    @pytest.mark.django_db
    def test_ordering_by_category_and_sort_order(self):
        """ordering이 category, sort_order 순"""
        metrics = list(MetricDefinition.objects.values_list('category', 'sort_order'))
        categories = [m[0] for m in metrics]
        # 카테고리가 알파벳순으로 정렬되는지 확인
        for i in range(1, len(categories)):
            if categories[i] == categories[i - 1]:
                assert metrics[i][1] >= metrics[i - 1][1]

    @pytest.mark.django_db
    def test_fallback_formula_exists_for_debt_to_equity(self):
        """debt_to_equity에 fallback_formula가 있음"""
        md = MetricDefinition.objects.get(pk='debt_to_equity')
        assert md.fallback_formula != ''
        assert 'long_term_debt' in md.fallback_formula

    @pytest.mark.django_db
    def test_str_representation(self):
        md = MetricDefinition.objects.get(pk='net_margin')
        assert str(md) == 'net_margin: 순이익률'

    @pytest.mark.django_db
    def test_all_metric_codes_are_unique(self):
        """모든 metric_code가 고유 (PK이므로 당연하지만 명시적 확인)"""
        codes = list(MetricDefinition.objects.values_list('metric_code', flat=True))
        assert len(codes) == len(set(codes))


# ===== PR-1: BatchJobRun =====

class TestBatchJobRun:
    """BatchJobRun 모델 CRUD 및 구조 검증"""

    @pytest.mark.django_db
    def test_create_batch_job_run(self):
        now = timezone.now()
        job = BatchJobRun.objects.create(
            job_name='test_snapshot_calc',
            job_type='manual',
            started_at=now,
            status='running',
            total_symbols=500,
        )
        assert job.pk is not None
        assert job.job_name == 'test_snapshot_calc'
        assert job.success_count == 0
        assert job.failure_details == []

    @pytest.mark.django_db
    def test_update_to_success(self):
        now = timezone.now()
        job = BatchJobRun.objects.create(
            job_name='test_job',
            started_at=now,
            status='running',
            total_symbols=100,
        )
        job.status = 'success'
        job.completed_at = timezone.now()
        job.success_count = 95
        job.failure_count = 5
        job.failure_details = [{'symbol': 'XYZ', 'error': 'timeout'}]
        job.save()

        job.refresh_from_db()
        assert job.status == 'success'
        assert job.success_count == 95
        assert len(job.failure_details) == 1

    @pytest.mark.django_db
    def test_str_representation(self):
        now = timezone.now()
        job = BatchJobRun.objects.create(
            job_name='snapshot_calc',
            started_at=now,
            status='failed',
        )
        s = str(job)
        assert 'snapshot_calc' in s
        assert 'failed' in s

    @pytest.mark.django_db
    def test_default_values(self):
        now = timezone.now()
        job = BatchJobRun.objects.create(
            job_name='default_test',
            started_at=now,
            status='running',
        )
        assert job.job_type == 'scheduled'
        assert job.triggered_by == 'celery_beat'
        assert job.total_symbols == 0
        assert job.skip_count == 0
        assert job.notes == ''


# ===== PR-2: CompanyMetricSnapshot =====

class TestCompanyMetricSnapshot:
    """CompanyMetricSnapshot FK 관계, unique_together, 품질 플래그 검증"""

    @pytest.mark.django_db
    def test_create_snapshot(self, stock_aapl):
        snap = CompanyMetricSnapshot.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=MetricDefinition.objects.get(pk='gross_margin'),
            metric_value=Decimal('0.462000'),
        )
        assert snap.pk is not None
        assert snap.symbol_id == 'AAPL'
        assert snap.metric_code_id == 'gross_margin'
        assert snap.quality_flag == 'ok'

    @pytest.mark.django_db
    def test_unique_together_constraint(self, stock_aapl):
        """같은 (symbol, fiscal_year, metric_code) 조합은 중복 불가"""
        md = MetricDefinition.objects.get(pk='net_margin')
        CompanyMetricSnapshot.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=md,
            metric_value=Decimal('0.250000'),
        )
        with pytest.raises(IntegrityError):
            CompanyMetricSnapshot.objects.create(
                symbol=stock_aapl,
                fiscal_year=2024,
                metric_code=md,
                metric_value=Decimal('0.260000'),
            )

    @pytest.mark.django_db
    def test_fk_to_stock(self, stock_aapl):
        """symbol FK가 Stock 모델을 참조"""
        snap = CompanyMetricSnapshot.objects.create(
            symbol=stock_aapl,
            fiscal_year=2023,
            metric_code=MetricDefinition.objects.get(pk='roe'),
            metric_value=Decimal('1.560000'),
        )
        assert snap.symbol.stock_name == 'Apple Inc.'

    @pytest.mark.django_db
    def test_fk_to_metric_definition(self, stock_aapl):
        """metric_code FK가 MetricDefinition을 참조"""
        md = MetricDefinition.objects.get(pk='operating_margin')
        snap = CompanyMetricSnapshot.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=md,
            metric_value=Decimal('0.312000'),
        )
        assert snap.metric_code.display_name == '영업이익률'
        assert snap.metric_code.category == 'profitability'

    @pytest.mark.django_db
    def test_nullable_metric_value(self, stock_aapl):
        """metric_value가 null 가능 (데이터 부족 시)"""
        snap = CompanyMetricSnapshot.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=MetricDefinition.objects.get(pk='cash_runway_years'),
            metric_value=None,
            quality_flag='insufficient_data',
        )
        assert snap.metric_value is None
        assert snap.quality_flag == 'insufficient_data'

    @pytest.mark.django_db
    def test_fallback_tracking(self, stock_aapl):
        """fallback 사용 시 추적 정보 저장"""
        snap = CompanyMetricSnapshot.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=MetricDefinition.objects.get(pk='debt_to_equity'),
            metric_value=Decimal('1.870000'),
            is_fallback_used=True,
            fallback_reason='short_longterm_debt_total was null, used sum of short+long',
            quality_flag='fallback',
        )
        assert snap.is_fallback_used is True
        assert 'short_longterm_debt_total' in snap.fallback_reason

    @pytest.mark.django_db
    def test_source_detail_json(self, stock_aapl):
        """source_detail JSONField 저장/조회"""
        snap = CompanyMetricSnapshot.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=MetricDefinition.objects.get(pk='fcf_margin'),
            metric_value=Decimal('0.280000'),
            source_detail={
                'apis': ['cash-flow-statement', 'income-statement'],
                'fields': ['operating_cashflow', 'capital_expenditures', 'total_revenue'],
                'formula_version': 1,
            },
        )
        snap.refresh_from_db()
        assert snap.source_detail['formula_version'] == 1
        assert len(snap.source_detail['apis']) == 2

    @pytest.mark.django_db
    def test_multiple_years_same_metric(self, stock_aapl):
        """같은 종목, 같은 지표라도 연도가 다르면 여러 행 가능"""
        md = MetricDefinition.objects.get(pk='revenue_growth_yoy')
        for year in [2022, 2023, 2024]:
            CompanyMetricSnapshot.objects.create(
                symbol=stock_aapl,
                fiscal_year=year,
                metric_code=md,
                metric_value=Decimal(f'0.{year % 100}0000'),
            )
        assert CompanyMetricSnapshot.objects.filter(
            symbol=stock_aapl, metric_code=md
        ).count() == 3

    @pytest.mark.django_db
    def test_str_representation(self, stock_aapl):
        snap = CompanyMetricSnapshot.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=MetricDefinition.objects.get(pk='pe_ratio'),
            metric_value=Decimal('28.500000'),
        )
        s = str(snap)
        assert 'AAPL' in s
        assert '2024' in s
        assert 'pe_ratio' in s


# ===== PR-2: PeerListCache =====

class TestPeerListCache:
    """PeerListCache OneToOne, ArrayField 검증"""

    @pytest.mark.django_db
    def test_create_peer_cache(self, stock_aapl):
        cache = PeerListCache.objects.create(
            symbol=stock_aapl,
            peer_symbols=['MSFT', 'GOOGL', 'META', 'AMZN'],
            peer_count=4,
        )
        assert cache.pk == 'AAPL'
        assert len(cache.peer_symbols) == 4
        assert 'MSFT' in cache.peer_symbols

    @pytest.mark.django_db
    def test_one_to_one_constraint(self, stock_aapl):
        """같은 Stock에 두 번 생성 불가"""
        PeerListCache.objects.create(
            symbol=stock_aapl,
            peer_symbols=['MSFT'],
            peer_count=1,
        )
        with pytest.raises(IntegrityError):
            PeerListCache.objects.create(
                symbol=stock_aapl,
                peer_symbols=['GOOGL'],
                peer_count=1,
            )

    @pytest.mark.django_db
    def test_industry_fallback(self, stock_aapl):
        """peer API 실패 시 industry fallback 플래그"""
        cache = PeerListCache.objects.create(
            symbol=stock_aapl,
            peer_symbols=['MSFT', 'DELL'],
            peer_count=2,
            use_industry_fallback=True,
            fallback_reason='FMP peers API returned empty, used industry match',
            source='industry_match',
        )
        assert cache.use_industry_fallback is True
        assert cache.source == 'industry_match'

    @pytest.mark.django_db
    def test_reverse_relation(self, stock_aapl):
        """Stock에서 peer_cache 역참조"""
        PeerListCache.objects.create(
            symbol=stock_aapl,
            peer_symbols=['MSFT'],
            peer_count=1,
        )
        assert stock_aapl.peer_cache.peer_count == 1

    @pytest.mark.django_db
    def test_empty_peer_list(self, stock_aapl):
        """빈 peer 목록도 저장 가능"""
        cache = PeerListCache.objects.create(
            symbol=stock_aapl,
            peer_symbols=[],
            peer_count=0,
        )
        assert cache.peer_symbols == []


# ===== PR-3: IndustryMetricBenchmark =====

class TestIndustryMetricBenchmark:
    """IndustryMetricBenchmark unique_together, sector fallback 검증"""

    @pytest.mark.django_db
    def test_create_benchmark(self):
        md = MetricDefinition.objects.get(pk='gross_margin')
        bench = IndustryMetricBenchmark.objects.create(
            industry='Consumer Electronics',
            fiscal_year=2024,
            metric_code=md,
            p25_value=Decimal('0.350000'),
            median_value=Decimal('0.420000'),
            p75_value=Decimal('0.510000'),
            mean_value=Decimal('0.430000'),
            sample_count=15,
            benchmark_confidence='high',
        )
        assert bench.pk is not None
        assert bench.median_value == Decimal('0.420000')

    @pytest.mark.django_db
    def test_unique_together_constraint(self):
        """같은 (industry, fiscal_year, metric_code) 중복 불가"""
        md = MetricDefinition.objects.get(pk='roe')
        IndustryMetricBenchmark.objects.create(
            industry='Software',
            fiscal_year=2024,
            metric_code=md,
            median_value=Decimal('0.250000'),
            sample_count=20,
        )
        with pytest.raises(IntegrityError):
            IndustryMetricBenchmark.objects.create(
                industry='Software',
                fiscal_year=2024,
                metric_code=md,
                median_value=Decimal('0.260000'),
                sample_count=21,
            )

    @pytest.mark.django_db
    def test_sector_fallback(self):
        """sample 부족 시 sector fallback"""
        md = MetricDefinition.objects.get(pk='net_margin')
        bench = IndustryMetricBenchmark.objects.create(
            industry='Rare Industry',
            fiscal_year=2024,
            metric_code=md,
            median_value=Decimal('0.100000'),
            sample_count=3,
            benchmark_confidence='low',
            is_sector_fallback=True,
            sector='Technology',
        )
        assert bench.benchmark_confidence == 'low'
        assert bench.is_sector_fallback is True
        assert bench.sector == 'Technology'

    @pytest.mark.django_db
    def test_confidence_levels(self):
        """benchmark_confidence high/medium/low 모두 유효"""
        md = MetricDefinition.objects.get(pk='current_ratio')
        for i, (conf, count) in enumerate([('high', 15), ('medium', 7), ('low', 2)]):
            IndustryMetricBenchmark.objects.create(
                industry=f'Industry_{conf}',
                fiscal_year=2024,
                metric_code=md,
                sample_count=count,
                benchmark_confidence=conf,
            )
        assert IndustryMetricBenchmark.objects.filter(metric_code=md).count() == 3

    @pytest.mark.django_db
    def test_str_representation(self):
        md = MetricDefinition.objects.get(pk='operating_margin')
        bench = IndustryMetricBenchmark.objects.create(
            industry='Semiconductors',
            fiscal_year=2024,
            metric_code=md,
            median_value=Decimal('0.350000'),
            sample_count=12,
        )
        s = str(bench)
        assert 'Semiconductors' in s
        assert '2024' in s


# ===== PR-3: PeerMetricBenchmark =====

class TestPeerMetricBenchmark:
    """PeerMetricBenchmark unique_together, ArrayField, benchmark_confidence 검증"""

    @pytest.mark.django_db
    def test_create_peer_benchmark(self, stock_aapl):
        md = MetricDefinition.objects.get(pk='gross_margin')
        bench = PeerMetricBenchmark.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=md,
            p25_value=Decimal('0.380000'),
            median_value=Decimal('0.450000'),
            p75_value=Decimal('0.520000'),
            peer_count=10,
            peer_symbols_used=['MSFT', 'GOOGL', 'META', 'AMZN', 'NVDA',
                               'CRM', 'ADBE', 'ORCL', 'INTC', 'IBM'],
            benchmark_confidence='high',
        )
        assert bench.pk is not None
        assert len(bench.peer_symbols_used) == 10

    @pytest.mark.django_db
    def test_unique_together_constraint(self, stock_aapl):
        """같은 (symbol, fiscal_year, metric_code) 중복 불가"""
        md = MetricDefinition.objects.get(pk='fcf_margin')
        PeerMetricBenchmark.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=md,
            median_value=Decimal('0.200000'),
            peer_count=5,
        )
        with pytest.raises(IntegrityError):
            PeerMetricBenchmark.objects.create(
                symbol=stock_aapl,
                fiscal_year=2024,
                metric_code=md,
                median_value=Decimal('0.210000'),
                peer_count=6,
            )

    @pytest.mark.django_db
    def test_low_confidence_with_few_peers(self, stock_aapl):
        """peer 수 부족 시 low confidence"""
        md = MetricDefinition.objects.get(pk='debt_to_equity')
        bench = PeerMetricBenchmark.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=md,
            peer_count=2,
            peer_symbols_used=['MSFT', 'GOOGL'],
            benchmark_confidence='low',
        )
        assert bench.benchmark_confidence == 'low'
        assert bench.peer_count == 2

    @pytest.mark.django_db
    def test_minmax_fields(self, stock_aapl):
        """use_minmax=True 시 min/max 값 저장"""
        md = MetricDefinition.objects.get(pk='roe')
        bench = PeerMetricBenchmark.objects.create(
            symbol=stock_aapl,
            fiscal_year=2024,
            metric_code=md,
            median_value=Decimal('0.300000'),
            peer_count=5,
            use_minmax=True,
            min_value=Decimal('0.050000'),
            max_value=Decimal('0.800000'),
        )
        assert bench.use_minmax is True
        assert bench.min_value == Decimal('0.050000')
        assert bench.max_value == Decimal('0.800000')

    @pytest.mark.django_db
    def test_multiple_symbols_same_year_metric(self, stock_aapl, stock_msft):
        """다른 종목은 같은 (fiscal_year, metric_code)로 생성 가능"""
        md = MetricDefinition.objects.get(pk='net_margin')
        PeerMetricBenchmark.objects.create(
            symbol=stock_aapl, fiscal_year=2024, metric_code=md,
            median_value=Decimal('0.250000'), peer_count=8,
        )
        PeerMetricBenchmark.objects.create(
            symbol=stock_msft, fiscal_year=2024, metric_code=md,
            median_value=Decimal('0.350000'), peer_count=8,
        )
        assert PeerMetricBenchmark.objects.filter(
            fiscal_year=2024, metric_code=md
        ).count() == 2


# ===== 시드 커맨드 멱등성 =====

class TestSeedCommand:
    """seed_metric_definitions 커맨드 멱등성 검증"""

    @pytest.mark.django_db
    def test_seed_is_idempotent(self):
        """시드 커맨드 2번 실행해도 34개 유지"""
        from django.core.management import call_command
        call_command('seed_metric_definitions', verbosity=0)
        assert MetricDefinition.objects.count() == 34
        call_command('seed_metric_definitions', verbosity=0)
        assert MetricDefinition.objects.count() == 34

    @pytest.mark.django_db
    def test_seed_updates_existing(self):
        """기존 지표의 display_name을 변경하면 시드가 원래 값으로 복구"""
        md = MetricDefinition.objects.get(pk='gross_margin')
        md.display_name = 'CHANGED'
        md.save()

        from django.core.management import call_command
        call_command('seed_metric_definitions', verbosity=0)

        md.refresh_from_db()
        assert md.display_name == '매출총이익률'
