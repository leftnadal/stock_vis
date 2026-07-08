"""MP2-DEEPEN — 촉발 심화 additive 계약 테스트.

- _regime_card: next_stage·next_stage_closest·margins additive(기존 계산 재사용, 신규 0)
- _anomaly_section fired: evidence(inputs 서브셋) + paired_news_title/url additive
- 기존 계약 필드·형태 불변
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone as django_timezone
from rest_framework.test import APIClient

from apps.market_pulse.models.anomaly import AnomalySignalLog
from apps.market_pulse.models.news import MarketPulseNews
from apps.market_pulse.models.regime import RegimeSnapshot

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='dp', email='dp@e.com', password='pw')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestRegimeNextStageAdditive:
    def test_regime_card_has_next_stage_keys(self, auth_client):
        today = django_timezone.localdate()
        RegimeSnapshot.objects.create(
            date=today, snapshot_time=django_timezone.now(),
            regime=RegimeSnapshot.Regime.LATE_BULL,
            status=RegimeSnapshot.Status.OK,
            coverage=0.9, headline='h', fired_rules=[],
            inputs={}, previous_regime='', hysteresis_streak=1,
        )
        r = auth_client.get(reverse('marketpulse_api_v2:overview'))
        regime = r.json()['cards']['regime']
        # additive 전조 필드 존재(값은 None/[] 가능 — 신규 계산 아님, 노출만)
        for k in ('next_stage', 'next_stage_closest', 'margins'):
            assert k in regime
        # 기존 계약 필드 불변
        for k in ('regime', 'status', 'coverage', 'headline', 'stance_copy', 'stance_ok'):
            assert k in regime


@pytest.mark.django_db
class TestAnomalyEvidenceAdditive:
    def test_fired_has_evidence_and_news_link(self, auth_client):
        now = django_timezone.now()
        news = MarketPulseNews.objects.create(
            category=MarketPulseNews.Category.SECTOR,
            source=MarketPulseNews.Source.FMP_GENERAL,
            title='Utilities surge on rate bets',
            url='https://e.com/util', url_hash='h-util',
            published_at=now,
        )
        AnomalySignalLog.objects.create(
            rule_id=AnomalySignalLog.RuleId.R12 if hasattr(AnomalySignalLog.RuleId, 'R12') else 'R12',
            triggered_at=now, mode=AnomalySignalLog.Mode.ANOMALY,
            headline='dispersion_spike 발동', body='섹터 분산 급등',
            threshold={'cross_dispersion': 1.5},
            inputs={
                'rule_actual': 1.58, 'top10_weight': 0.32, 'vix_change_pct': 4.1,
                'max_abs_sector_z': 2.1, 'sector_extreme_symbol': 'XLU',
            },
            paired_news=news,
        )
        r = auth_client.get(reverse('marketpulse_api_v2:overview'))
        anomaly = r.json()['anomaly']
        assert anomaly['mode'] == AnomalySignalLog.Mode.ANOMALY
        assert len(anomaly['fired']) >= 1
        f = anomaly['fired'][0]
        # 기존 계약 불변
        for k in ('rule_id', 'headline', 'threshold', 'actual', 'paired_news_id'):
            assert k in f
        # additive: evidence 서브셋
        ev = f['evidence']
        assert ev['top10_weight'] == 0.32
        assert ev['vix_change_pct'] == 4.1
        assert ev['sector_extreme_symbol'] == 'XLU'
        # additive: 뉴스 링크
        assert f['paired_news_title'] == 'Utilities surge on rate bets'
        assert f['paired_news_url'] == 'https://e.com/util'

    def test_calm_when_no_anomaly(self, auth_client):
        r = auth_client.get(reverse('marketpulse_api_v2:overview'))
        assert r.json()['anomaly']['mode'] == AnomalySignalLog.Mode.CALM
        assert r.json()['anomaly']['fired'] == []
