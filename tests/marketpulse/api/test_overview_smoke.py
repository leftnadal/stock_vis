"""Smoke tests for marketpulse.api.views (PR-I/J)."""
from __future__ import annotations

from datetime import date as date_cls
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from macro.models.indicators import MarketIndex, MarketIndexPrice
from marketpulse.models.briefing import BriefingLog
from marketpulse.models.news import MarketPulseNews
from marketpulse.models.regime import RegimeSnapshot
from marketpulse.models.snapshot import (
    BreadthSnapshot,
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='ov', email='ov@e.com', password='pw')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(db):
    user = User.objects.create_superuser(username='adm', email='a@e.com', password='pw')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def populated(db):
    today = date_cls(2026, 4, 27)
    spy, _ = MarketIndex.objects.update_or_create(
        symbol='SPY',
        defaults={'name': 'SPY', 'sector_group': 'BENCHMARK', 'category': 'us_equity'},
    )
    MarketIndexPrice.objects.update_or_create(
        index=spy, date=today,
        defaults={'close': Decimal('500'), 'volume': 1000},
    )
    MarketIndexPrice.objects.update_or_create(
        index=spy, date=today - timedelta(days=1),
        defaults={'close': Decimal('490'), 'volume': 1000},
    )

    xlk, _ = MarketIndex.objects.update_or_create(
        symbol='XLK',
        defaults={'name': 'XLK', 'sector_group': 'TECH', 'category': 'sector'},
    )

    RegimeSnapshot.objects.create(
        date=today, snapshot_time=today,
        regime=RegimeSnapshot.Regime.BULL_EXPANSION,
        status=RegimeSnapshot.Status.OK,
        coverage=0.9, headline='strong', fired_rules=[],
        previous_regime='', hysteresis_streak=1,
    )
    BreadthSnapshot.objects.create(
        date=today, snapshot_time=today, universe='SPY',
        advance_count=320, decline_count=180, unchanged_count=3,
        total_count=503, new_high_52w=20, new_low_52w=5,
        ad_line=140, ad_line_change=140,
    )
    ConcentrationSnapshot.objects.create(
        date=today, snapshot_time=today, universe='SPY',
        top5_weight=Decimal('0.27'),
        top10_weight=Decimal('0.38'),
        hhi=Decimal('0.018'),
        top_holdings=[{'symbol': 'NVDA', 'weight': 0.07}],
    )
    SectorFlowSnapshot.objects.create(
        date=today, snapshot_time=today, market_index=xlk,
        rel_strength=Decimal('2.0'), momentum_1d=Decimal('1.0'),
        cross_dispersion=Decimal('0.8'), rotation_index=Decimal('1.5'),
        rank_in_universe=1,
    )
    BriefingLog.objects.create(
        date=today, model_version='gemini-2.5-flash',
        status=BriefingLog.Status.OK,
        headline='headline', body='content ' * 30,
    )
    MarketPulseNews.objects.create(
        category=MarketPulseNews.Category.MACRO,
        source=MarketPulseNews.Source.FMP_GENERAL,
        title='Fed signals',
        url='https://e.com/n1', url_hash='hash-n1',
        published_at=today,
    )
    return today


class TestOverview:
    def test_unauthenticated_401(self, db):
        client = APIClient()
        r = client.get(reverse('marketpulse_api_v2:overview'))
        assert r.status_code == 401

    def test_200_response_structure(self, auth_client, populated):
        r = auth_client.get(reverse('marketpulse_api_v2:overview'))
        assert r.status_code == 200
        data = r.json()
        for key in ('_meta', 'ticker_bar', 'news', 'anomaly', 'cards'):
            assert key in data

    def test_cache_hit_on_second(self, auth_client, populated):
        first = auth_client.get(reverse('marketpulse_api_v2:overview'))
        second = auth_client.get(reverse('marketpulse_api_v2:overview'))
        assert first.json()['_meta']['cache'] == 'MISS'
        assert second.json()['_meta']['cache'] == 'HIT'

    def test_insufficient_data_when_empty(self, auth_client, db):
        r = auth_client.get(reverse('marketpulse_api_v2:overview'))
        assert r.json()['_meta']['status'] == 'INSUFFICIENT_DATA'


class TestCardDetail:
    @pytest.mark.parametrize('cid', ['regime', 'breadth', 'sector', 'flow', 'brief'])
    def test_each_card_200(self, auth_client, populated, cid):
        r = auth_client.get(
            reverse('marketpulse_api_v2:card-detail', kwargs={'card_id': cid}),
        )
        assert r.status_code == 200
        body = r.json()
        assert body['data'].get('available') is True

    def test_unknown_card_404(self, auth_client):
        r = auth_client.get(
            reverse('marketpulse_api_v2:card-detail', kwargs={'card_id': 'nope'}),
        )
        assert r.status_code == 404


class TestI18n:
    def test_ko_labels(self, auth_client):
        r = auth_client.get(reverse('marketpulse_api_v2:i18n'))
        body = r.json()
        assert body['_meta']['locale'] == 'ko'
        assert 'card.regime' in body['labels']
        assert body['labels']['regime.BULL_EXPANSION'] == '강세 확장'


class TestHealth:
    def test_admin_only(self, auth_client):
        r = auth_client.get(reverse('marketpulse_api_v2:health'))
        assert r.status_code == 403

    def test_admin_200(self, admin_client, populated):
        r = admin_client.get(reverse('marketpulse_api_v2:health'))
        assert r.status_code == 200
        assert r.json()['probes']['db']['ok'] is True


class TestSchema:
    def test_schema_json(self, db):
        client = APIClient()
        r = client.get('/api/v2/schema/?format=json')
        assert r.status_code == 200
        body = r.json()
        assert body['openapi'].startswith('3.')
