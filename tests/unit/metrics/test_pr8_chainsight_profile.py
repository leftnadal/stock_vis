"""
PR-8 chainsight 프로파일/뉴스 모델 테스트

검증 범위:
- CompanyRevenueStructure: OneToOne, JSONField(segments/geographic/customers)
- CompanyChainProfile: OneToOne, 집약 필드, ArrayField(theme_tags)
- ChainNewsEvent: FK, unique_together(source+source_id), self FK, ArrayField
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.chain_sight.models import (
    ChainNewsEvent,
    CompanyChainProfile,
    CompanyRevenueStructure,
)


class TestCompanyRevenueStructure:

    @pytest.mark.django_db
    def test_create_revenue_structure(self, stock_aapl):
        rs = CompanyRevenueStructure.objects.create(
            symbol=stock_aapl,
            segments=[
                {'name': 'iPhone', 'revenue_pct': 52, 'trend': 'stable'},
                {'name': 'Services', 'revenue_pct': 22, 'trend': 'growing'},
                {'name': 'Mac', 'revenue_pct': 10, 'trend': 'stable'},
            ],
            geographic_revenue=[
                {'region': 'Americas', 'pct': 42},
                {'region': 'Europe', 'pct': 25},
                {'region': 'Greater China', 'pct': 19},
            ],
            major_customers=[],
            customer_concentration_risk='low',
            business_model_type='b2c',
            commodity_exposures=[
                {'commodity': 'rare_earth', 'exposure': 'medium', 'context': 'electronics'},
            ],
            extraction_method='fmp_api',
            extraction_confidence=Decimal('0.85'),
        )
        assert rs.pk == 'AAPL'
        assert len(rs.segments) == 3
        assert rs.business_model_type == 'b2c'

    @pytest.mark.django_db
    def test_one_to_one(self, stock_aapl):
        CompanyRevenueStructure.objects.create(symbol=stock_aapl)
        with pytest.raises(IntegrityError):
            CompanyRevenueStructure.objects.create(symbol=stock_aapl)

    @pytest.mark.django_db
    def test_json_fields_queryable(self, stock_aapl):
        CompanyRevenueStructure.objects.create(
            symbol=stock_aapl,
            segments=[{'name': 'Cloud', 'revenue_pct': 60}],
        )
        rs = CompanyRevenueStructure.objects.get(symbol=stock_aapl)
        assert rs.segments[0]['name'] == 'Cloud'

    @pytest.mark.django_db
    def test_b2b_with_major_customers(self, stock_msft):
        rs = CompanyRevenueStructure.objects.create(
            symbol=stock_msft,
            business_model_type='b2b',
            major_customers=[
                {'customer': 'US Government', 'revenue_pct': 8},
            ],
            customer_concentration_risk='medium',
        )
        assert len(rs.major_customers) == 1
        assert rs.customer_concentration_risk == 'medium'

    @pytest.mark.django_db
    def test_reverse_relation(self, stock_aapl):
        CompanyRevenueStructure.objects.create(
            symbol=stock_aapl, business_model_type='mixed',
        )
        assert stock_aapl.revenue_structure.business_model_type == 'mixed'

    @pytest.mark.django_db
    def test_str_representation(self, stock_aapl):
        rs = CompanyRevenueStructure.objects.create(
            symbol=stock_aapl,
            segments=[{'name': 'A'}, {'name': 'B'}],
        )
        assert 'AAPL' in str(rs)
        assert '2 segments' in str(rs)


class TestCompanyChainProfile:

    @pytest.mark.django_db
    def test_create_chain_profile(self, stock_aapl):
        profile = CompanyChainProfile.objects.create(
            symbol=stock_aapl,
            rate_sensitivity='low',
            forex_sensitivity='medium',
            commodity_sensitivity='low',
            regulation_type='none',
            beta=Decimal('1.2500'),
            growth_stage='mature',
            revenue_cagr_3y=Decimal('0.0800'),
            capital_type='shareholder_first',
            net_cash_position=65000000000,
            smart_money_signal='bullish',
            top_segment='iPhone',
            top_segment_pct=Decimal('52.00'),
            china_revenue_pct=Decimal('19.00'),
            customer_concentration_risk='low',
            business_model_type='b2c',
            primary_narrative='AI Infrastructure Leader',
            theme_tags=['ai_infrastructure', 'services_pivot'],
            narrative_sentiment='positive',
            score_profitability=Decimal('88.00'),
            score_growth=Decimal('72.00'),
            score_financial_structure=Decimal('65.00'),
            overall_grade='A',
            profile_completeness=Decimal('0.92'),
        )
        assert profile.pk == 'AAPL'
        assert profile.overall_grade == 'A'
        assert len(profile.theme_tags) == 2

    @pytest.mark.django_db
    def test_one_to_one(self, stock_aapl):
        CompanyChainProfile.objects.create(symbol=stock_aapl)
        with pytest.raises(IntegrityError):
            CompanyChainProfile.objects.create(symbol=stock_aapl)

    @pytest.mark.django_db
    def test_empty_profile(self, stock_aapl):
        """모든 필드 빈 상태로 생성 가능 (점진적 채움)"""
        profile = CompanyChainProfile.objects.create(symbol=stock_aapl)
        assert profile.growth_stage == ''
        assert profile.overall_grade == ''
        assert profile.profile_completeness is None

    @pytest.mark.django_db
    def test_theme_tags_arrayfield(self, stock_aapl):
        CompanyChainProfile.objects.create(
            symbol=stock_aapl,
            theme_tags=['ev_battery', 'china_risk', 'dividend_growth'],
        )
        result = CompanyChainProfile.objects.filter(
            theme_tags__contains=['china_risk']
        )
        assert result.count() == 1

    @pytest.mark.django_db
    def test_reverse_relation(self, stock_aapl):
        CompanyChainProfile.objects.create(
            symbol=stock_aapl, overall_grade='B+',
        )
        assert stock_aapl.chain_profile.overall_grade == 'B+'

    @pytest.mark.django_db
    def test_str_representation(self, stock_aapl):
        profile = CompanyChainProfile.objects.create(
            symbol=stock_aapl, growth_stage='mature', overall_grade='A',
        )
        s = str(profile)
        assert 'AAPL' in s
        assert 'mature' in s


class TestChainNewsEvent:

    @pytest.mark.django_db
    def test_create_news_event(self, stock_aapl):
        ev = ChainNewsEvent.objects.create(
            symbol=stock_aapl,
            source='marketaux',
            source_id='mktaux-12345',
            title='Apple announces new AI chip partnership',
            summary='Apple partners with TSMC for next-gen AI processors.',
            url='https://example.com/article/12345',
            published_at=timezone.now(),
            sentiment_score=Decimal('0.750'),
            sentiment_label='positive',
            event_type='partnership',
            event_importance='high',
            co_mentioned_symbols=['TSMC', 'NVDA'],
        )
        assert ev.pk is not None
        assert ev.source == 'marketaux'
        assert len(ev.co_mentioned_symbols) == 2

    @pytest.mark.django_db
    def test_unique_together_source_source_id(self, stock_aapl):
        """같은 (source, source_id) 중복 불가"""
        ChainNewsEvent.objects.create(
            symbol=stock_aapl, source='finnhub', source_id='fh-001',
            title='Test', published_at=timezone.now(),
        )
        with pytest.raises(IntegrityError):
            ChainNewsEvent.objects.create(
                symbol=stock_aapl, source='finnhub', source_id='fh-001',
                title='Duplicate', published_at=timezone.now(),
            )

    @pytest.mark.django_db
    def test_different_source_same_id(self, stock_aapl):
        """다른 source이면 같은 source_id 허용"""
        now = timezone.now()
        ChainNewsEvent.objects.create(
            symbol=stock_aapl, source='marketaux', source_id='shared-001',
            title='Article A', published_at=now,
        )
        ChainNewsEvent.objects.create(
            symbol=stock_aapl, source='finnhub', source_id='shared-001',
            title='Article B', published_at=now,
        )
        assert ChainNewsEvent.objects.filter(source_id='shared-001').count() == 2

    @pytest.mark.django_db
    def test_self_fk_duplicate(self, stock_aapl):
        """self FK로 중복 뉴스 연결"""
        now = timezone.now()
        original = ChainNewsEvent.objects.create(
            symbol=stock_aapl, source='marketaux', source_id='orig-001',
            title='Original article', published_at=now,
        )
        dup = ChainNewsEvent.objects.create(
            symbol=stock_aapl, source='eodhd', source_id='dup-001',
            title='Same article different source', published_at=now,
            is_duplicate=True,
            duplicate_of=original,
        )
        assert dup.is_duplicate is True
        assert dup.duplicate_of == original
        assert original.duplicates.count() == 1

    @pytest.mark.django_db
    def test_on_delete_protect(self, stock_aapl):
        """Stock 삭제 시 PROTECT"""
        ChainNewsEvent.objects.create(
            symbol=stock_aapl, source='finnhub', source_id='protect-001',
            title='Protected', published_at=timezone.now(),
        )
        from django.db.models import ProtectedError
        with pytest.raises(ProtectedError):
            stock_aapl.delete()

    @pytest.mark.django_db
    def test_co_mentioned_symbols_query(self, stock_aapl):
        """co_mentioned_symbols ArrayField __overlap 쿼리"""
        now = timezone.now()
        ChainNewsEvent.objects.create(
            symbol=stock_aapl, source='marketaux', source_id='co-001',
            title='Article 1', published_at=now,
            co_mentioned_symbols=['NVDA', 'TSMC'],
        )
        ChainNewsEvent.objects.create(
            symbol=stock_aapl, source='marketaux', source_id='co-002',
            title='Article 2', published_at=now,
            co_mentioned_symbols=['GOOGL', 'META'],
        )
        nvda_related = ChainNewsEvent.objects.filter(
            co_mentioned_symbols__overlap=['NVDA']
        )
        assert nvda_related.count() == 1

    @pytest.mark.django_db
    def test_multiple_events_per_symbol(self, stock_aapl):
        """같은 종목에 여러 뉴스 이벤트"""
        now = timezone.now()
        for i in range(5):
            ChainNewsEvent.objects.create(
                symbol=stock_aapl, source='marketaux', source_id=f'multi-{i}',
                title=f'Article {i}', published_at=now,
            )
        assert stock_aapl.chain_news_events.count() == 5

    @pytest.mark.django_db
    def test_str_representation(self, stock_aapl):
        ev = ChainNewsEvent.objects.create(
            symbol=stock_aapl, source='finnhub', source_id='str-001',
            title='A very long title that should be truncated in str output',
            published_at=timezone.now(),
        )
        s = str(ev)
        assert 'AAPL' in s
        assert 'finnhub' in s
