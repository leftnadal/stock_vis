"""PR-A2 누락 필드 추가 검증 (저위험 스키마 확장).

운영 데이터 영향 없음 (default/null로 추가). 후속 PR(B/D/E/O)이 실제 입력.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone


@pytest.mark.django_db
class TestMarketPulseNewsFieldExtension:
    """MarketPulseNews 저위험 필드 추가 검증."""

    def _make_news(self, **overrides):
        from marketpulse.models import MarketPulseNews
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
        from marketpulse.models import MarketPulseNews
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
        assert n.is_exposed is True
        assert n.first_exposed_at is not None
        assert n.expires_at is None  # NULL 전환 (영구 보존)

    def test_paired_with_anomaly_toggles(self):
        n = self._make_news(url_hash='d' * 64)
        assert n.paired_with_anomaly is False
        n.paired_with_anomaly = True
        n.save(update_fields=['paired_with_anomaly'])
        n.refresh_from_db()
        assert n.paired_with_anomaly is True


@pytest.mark.django_db
class TestBriefingLogFieldExtension:
    """BriefingLog 저위험 필드 추가 검증."""

    def test_cost_usd_nullable(self):
        from marketpulse.models import BriefingLog
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash',
        )
        assert b.cost_usd is None
        assert b.error_message == ''

    def test_cost_usd_decimal_precision(self):
        from marketpulse.models import BriefingLog
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-v2',
            cost_usd=Decimal('0.0123'),
        )
        assert b.cost_usd == Decimal('0.0123')

    def test_error_message_for_failed_status(self):
        from marketpulse.models import BriefingLog
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-v3',
            status=BriefingLog.Status.FAILED,
            error_message='timeout after 30s',
        )
        assert b.status == BriefingLog.Status.FAILED
        assert 'timeout' in b.error_message
