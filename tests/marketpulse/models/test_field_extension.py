"""PR-A2 필드 변경 검증 (중/고위험 스키마 변경 포함).

중위험: is_exposed → shown_on_layer0, first_exposed_at → shown_at, inputs_summary → prompt_inputs
고위험: matched_symbols/matched_keywords → entities (dict), content → body + body_sections
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone


@pytest.mark.django_db
class TestMarketPulseNewsFieldExtension:
    """MarketPulseNews 저위험 + 중위험 + 고위험 필드 변경 검증."""

    def _make_news(self, **overrides):
        from apps.market_pulse.models import MarketPulseNews
        defaults = {
            'category': MarketPulseNews.Category.MACRO,
            'source': MarketPulseNews.Source.FMP_GENERAL,
            'title': 't',
            'url': 'https://example.com/a',
            'url_hash': 'h' * 64,
            'published_at': timezone.now(),
        }
        defaults.update(overrides)
        return MarketPulseNews.objects.create(**defaults)

    def test_default_values_for_added_fields(self):
        n = self._make_news(url_hash='a' * 64)
        assert n.category_confidence == 0.0
        assert n.relevance_score == 0.0
        assert n.sentiment_score is None
        assert n.summary_ko == ''
        assert n.paired_with_anomaly is False
        assert n.expires_at is None

    def test_sentiment_score_can_be_negative(self):
        n = self._make_news(url_hash='b' * 64, sentiment_score=-0.7)
        assert n.sentiment_score == -0.7

    def test_expires_at_indexed_for_purge(self):
        from apps.market_pulse.models import MarketPulseNews
        field = MarketPulseNews._meta.get_field('expires_at')
        assert field.db_index is True
        assert field.null is True

    def test_mark_exposed_clears_expires_at(self):
        """D5 TTL 정책: shown_on_layer0=True 시 expires_at NULL(영구)."""
        future = timezone.now() + timedelta(days=90)
        n = self._make_news(url_hash='c' * 64, expires_at=future)
        assert n.expires_at == future
        n.mark_exposed()
        n.refresh_from_db()
        assert n.shown_on_layer0 is True
        assert n.shown_at is not None
        assert n.expires_at is None  # NULL 전환 (영구 보존)

    def test_paired_with_anomaly_toggles(self):
        n = self._make_news(url_hash='d' * 64)
        assert n.paired_with_anomaly is False
        n.paired_with_anomaly = True
        n.save(update_fields=['paired_with_anomaly'])
        n.refresh_from_db()
        assert n.paired_with_anomaly is True

    # ─── 중위험: is_exposed → shown_on_layer0 ───────────────────────────

    def test_shown_on_layer0_default_false(self):
        n = self._make_news(url_hash='e' * 64)
        assert n.shown_on_layer0 is False
        assert n.shown_at is None

    def test_mark_exposed_sets_shown_on_layer0(self):
        n = self._make_news(url_hash='f' * 64)
        assert n.shown_on_layer0 is False
        n.mark_exposed()
        n.refresh_from_db()
        assert n.shown_on_layer0 is True
        assert n.shown_at is not None

    def test_mark_exposed_idempotent(self):
        """두 번 호출해도 shown_at이 바뀌지 않음."""
        n = self._make_news(url_hash='g' * 64)
        n.mark_exposed()
        n.refresh_from_db()
        first_shown_at = n.shown_at
        n.mark_exposed()
        n.refresh_from_db()
        assert n.shown_at == first_shown_at

    # ─── 고위험: entities 구조 검증 ──────────────────────────────────────

    def test_entities_default_is_empty_dict(self):
        n = self._make_news(url_hash='h' * 64)
        assert n.entities == {}

    def test_entities_tickers_sectors_topics(self):
        ent = {'tickers': ['AAPL', 'NVDA'], 'sectors': [], 'topics': ['inflation']}
        n = self._make_news(url_hash='i' * 64, entities=ent)
        assert n.entities['tickers'] == ['AAPL', 'NVDA']
        assert n.entities['sectors'] == []
        assert n.entities['topics'] == ['inflation']

    def test_entities_setdefault_append_pattern(self):
        """entities.setdefault 패턴으로 tickers 추가."""
        n = self._make_news(url_hash='j' * 64, entities={'tickers': [], 'sectors': [], 'topics': []})
        n.entities.setdefault('tickers', []).append('TSLA')
        n.save(update_fields=['entities'])
        n.refresh_from_db()
        assert 'TSLA' in n.entities['tickers']

    def test_entities_field_present_no_old_fields(self):
        """matched_symbols/matched_keywords 필드 존재하지 않음."""
        from apps.market_pulse.models import MarketPulseNews
        field_names = [f.name for f in MarketPulseNews._meta.get_fields()]
        assert 'entities' in field_names
        assert 'matched_symbols' not in field_names
        assert 'matched_keywords' not in field_names


@pytest.mark.django_db
class TestBriefingLogFieldExtension:
    """BriefingLog 저위험 + 중위험 + 고위험 필드 변경 검증."""

    def test_cost_usd_nullable(self):
        from apps.market_pulse.models import BriefingLog
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash',
        )
        assert b.cost_usd is None
        assert b.error_message == ''

    def test_cost_usd_decimal_precision(self):
        from apps.market_pulse.models import BriefingLog
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-v2',
            cost_usd=Decimal('0.0123'),
        )
        assert b.cost_usd == Decimal('0.0123')

    def test_error_message_for_failed_status(self):
        from apps.market_pulse.models import BriefingLog
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-v3',
            status=BriefingLog.Status.FAILED,
            error_message='timeout after 30s',
        )
        assert b.status == BriefingLog.Status.FAILED
        assert 'timeout' in b.error_message

    # ─── 중위험: inputs_summary → prompt_inputs ──────────────────────────

    def test_prompt_inputs_default_empty_dict(self):
        from apps.market_pulse.models import BriefingLog
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-pi',
        )
        assert b.prompt_inputs == {}

    def test_prompt_inputs_stores_context(self):
        from apps.market_pulse.models import BriefingLog
        ctx = {'regime': 'BULL_EXPANSION', 'breadth': {'advance': 300}}
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-pi2',
            prompt_inputs=ctx,
        )
        assert b.prompt_inputs['regime'] == 'BULL_EXPANSION'

    # ─── 고위험: body/body_sections 검증 ────────────────────────────────

    def test_body_default_empty_string(self):
        from apps.market_pulse.models import BriefingLog
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-bd',
        )
        assert b.body == ''
        assert b.body_sections == []

    def test_body_stores_full_text(self):
        from apps.market_pulse.models import BriefingLog
        text = '시장 강세 흐름이 지속되고 있습니다.' * 10
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-bd2',
            body=text,
        )
        assert b.body == text

    def test_body_sections_stores_list(self):
        from apps.market_pulse.models import BriefingLog
        sections = [{'title': '요약', 'content': '강세'}, {'title': '리스크', 'content': '변동성'}]
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-bd3',
            body_sections=sections,
        )
        assert len(b.body_sections) == 2
        assert b.body_sections[0]['title'] == '요약'

    def test_old_content_field_absent(self):
        """content 필드 존재하지 않음."""
        from apps.market_pulse.models import BriefingLog
        field_names = [f.name for f in BriefingLog._meta.get_fields()]
        assert 'body' in field_names
        assert 'body_sections' in field_names
        assert 'content' not in field_names
