"""
PR-7 chainsight 신호 모델 테스트

검증 범위:
- CompanyInsiderSignal: OneToOne, insider/institution/short 필드
- CompanyNarrativeTag: OneToOne, ArrayField(theme_tags), LLM choices
- CompanyEventReaction: FK, unique_together(symbol+event_type)
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.chain_sight.models import (
    CompanyEventReaction,
    CompanyInsiderSignal,
    CompanyNarrativeTag,
)


class TestCompanyInsiderSignal:

    @pytest.mark.django_db
    def test_create_insider_signal(self, stock_aapl):
        sig = CompanyInsiderSignal.objects.create(
            symbol=stock_aapl,
            insider_buy_count_90d=5,
            insider_sell_count_90d=2,
            insider_net_amount_90d=3500000,
            insider_signal='buy',
            institutional_ownership_pct=Decimal('72.50'),
            institutional_change_qoq=Decimal('0.0150'),
            top_holder_action='accumulating',
            short_interest_pct=Decimal('1.20'),
            short_interest_change='decreasing',
            days_to_cover=Decimal('2.30'),
            smart_money_signal='bullish',
            data_freshness=date(2026, 3, 25),
        )
        assert sig.pk == 'AAPL'
        assert sig.smart_money_signal == 'bullish'
        assert sig.insider_net_amount_90d == 3500000

    @pytest.mark.django_db
    def test_one_to_one(self, stock_aapl):
        CompanyInsiderSignal.objects.create(symbol=stock_aapl)
        with pytest.raises(IntegrityError):
            CompanyInsiderSignal.objects.create(symbol=stock_aapl)

    @pytest.mark.django_db
    def test_bearish_signal(self, stock_msft):
        sig = CompanyInsiderSignal.objects.create(
            symbol=stock_msft,
            insider_signal='strong_sell',
            smart_money_signal='bearish',
            short_interest_pct=Decimal('8.50'),
            short_interest_change='increasing',
            days_to_cover=Decimal('6.80'),
        )
        assert sig.insider_signal == 'strong_sell'
        assert sig.short_interest_change == 'increasing'

    @pytest.mark.django_db
    def test_reverse_relation(self, stock_aapl):
        CompanyInsiderSignal.objects.create(
            symbol=stock_aapl, smart_money_signal='neutral',
        )
        assert stock_aapl.insider_signal.smart_money_signal == 'neutral'

    @pytest.mark.django_db
    def test_str_representation(self, stock_aapl):
        sig = CompanyInsiderSignal.objects.create(
            symbol=stock_aapl, smart_money_signal='bullish',
        )
        assert 'AAPL' in str(sig)
        assert 'bullish' in str(sig)


class TestCompanyNarrativeTag:

    @pytest.mark.django_db
    def test_create_narrative_tag(self, stock_aapl):
        tag = CompanyNarrativeTag.objects.create(
            symbol=stock_aapl,
            primary_narrative='AI Infrastructure Leader',
            secondary_narrative='Services Growth',
            narrative_strength='strong',
            narrative_sentiment='positive',
            theme_tags=['ai_infrastructure', 'services_pivot', 'china_risk'],
            avg_sentiment_30d=Decimal('0.720'),
            sentiment_trend='improving',
            news_frequency_30d=45,
            analyst_consensus='buy',
            analyst_target_vs_price=Decimal('1.1500'),
            analyst_revision_trend='upgrading',
            generated_by='llm_batch',
        )
        assert tag.pk == 'AAPL'
        assert len(tag.theme_tags) == 3
        assert 'ai_infrastructure' in tag.theme_tags

    @pytest.mark.django_db
    def test_one_to_one(self, stock_aapl):
        CompanyNarrativeTag.objects.create(symbol=stock_aapl)
        with pytest.raises(IntegrityError):
            CompanyNarrativeTag.objects.create(symbol=stock_aapl)

    @pytest.mark.django_db
    def test_theme_tags_arrayfield_query(self, stock_aapl, stock_msft):
        """ArrayField __contains 네이티브 쿼리"""
        CompanyNarrativeTag.objects.create(
            symbol=stock_aapl,
            theme_tags=['ai_infrastructure', 'china_risk'],
        )
        CompanyNarrativeTag.objects.create(
            symbol=stock_msft,
            theme_tags=['cloud_computing', 'ai_infrastructure'],
        )
        ai_stocks = CompanyNarrativeTag.objects.filter(
            theme_tags__contains=['ai_infrastructure']
        )
        assert ai_stocks.count() == 2

    @pytest.mark.django_db
    def test_empty_theme_tags(self, stock_aapl):
        tag = CompanyNarrativeTag.objects.create(
            symbol=stock_aapl, theme_tags=[],
        )
        assert tag.theme_tags == []

    @pytest.mark.django_db
    def test_all_generated_by_choices(self, stock_aapl):
        for method in ['llm_batch', 'rule_based', 'manual']:
            CompanyNarrativeTag.objects.filter(symbol=stock_aapl).delete()
            tag = CompanyNarrativeTag.objects.create(
                symbol=stock_aapl, generated_by=method,
            )
            assert tag.generated_by == method

    @pytest.mark.django_db
    def test_str_representation(self, stock_aapl):
        tag = CompanyNarrativeTag.objects.create(
            symbol=stock_aapl, primary_narrative='AI Leader',
        )
        assert 'AAPL' in str(tag)
        assert 'AI Leader' in str(tag)


class TestCompanyEventReaction:

    @pytest.mark.django_db
    def test_create_event_reaction(self, stock_aapl):
        er = CompanyEventReaction.objects.create(
            symbol=stock_aapl,
            event_type='rate_hike',
            sample_count=12,
            avg_return_1d=Decimal('-0.0180'),
            avg_return_5d=Decimal('-0.0250'),
            hit_rate_negative=Decimal('75.00'),
            avg_abnormal_return=Decimal('-0.0120'),
            reaction_grade='moderate_negative',
            confidence='high',
        )
        assert er.pk is not None
        assert er.event_type == 'rate_hike'
        assert er.reaction_grade == 'moderate_negative'

    @pytest.mark.django_db
    def test_unique_together(self, stock_aapl):
        """같은 (symbol, event_type) 중복 불가"""
        CompanyEventReaction.objects.create(
            symbol=stock_aapl, event_type='china_tariff',
        )
        with pytest.raises(IntegrityError):
            CompanyEventReaction.objects.create(
                symbol=stock_aapl, event_type='china_tariff',
            )

    @pytest.mark.django_db
    def test_different_event_types_same_symbol(self, stock_aapl):
        """같은 종목, 다른 이벤트 타입은 가능"""
        for et in ['rate_hike', 'china_tariff', 'tech_selloff']:
            CompanyEventReaction.objects.create(
                symbol=stock_aapl, event_type=et, sample_count=5,
            )
        assert CompanyEventReaction.objects.filter(symbol=stock_aapl).count() == 3

    @pytest.mark.django_db
    def test_same_event_different_symbols(self, stock_aapl, stock_msft):
        """같은 이벤트, 다른 종목은 가능"""
        for stock in [stock_aapl, stock_msft]:
            CompanyEventReaction.objects.create(
                symbol=stock, event_type='rate_hike',
            )
        assert CompanyEventReaction.objects.filter(event_type='rate_hike').count() == 2

    @pytest.mark.django_db
    def test_all_reaction_grades(self, stock_aapl):
        grades = ['high_negative', 'moderate_negative', 'neutral', 'moderate_positive', 'high_positive']
        for i, grade in enumerate(grades):
            CompanyEventReaction.objects.create(
                symbol=stock_aapl, event_type=f'event_{i}',
                reaction_grade=grade,
            )
        assert CompanyEventReaction.objects.filter(symbol=stock_aapl).count() == 5
