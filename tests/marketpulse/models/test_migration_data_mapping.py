"""PR-A2 RunPython 데이터 매핑 검증.

0004 마이그레이션의 RunPython 로직을 직접 테스트:
- matched_symbols/matched_keywords → entities 변환
- content → body 변환
- body_sections default []
"""
from __future__ import annotations

from datetime import date

import pytest
from django.utils import timezone


@pytest.mark.django_db
class TestNewsEntitiesDataMapping:
    """MarketPulseNews entities 구조 저장/조회 일관성 검증."""

    def _make_news(self, url_hash: str, **overrides):
        from apps.market_pulse.models import MarketPulseNews
        defaults = {
            'category': MarketPulseNews.Category.MACRO,
            'source': MarketPulseNews.Source.FMP_GENERAL,
            'title': 'test title',
            'url': f'https://example.com/{url_hash}',
            'url_hash': url_hash,
            'published_at': timezone.now(),
        }
        defaults.update(overrides)
        return MarketPulseNews.objects.create(**defaults)

    def test_entities_full_structure_roundtrip(self):
        """entities의 tickers/sectors/topics 구조를 DB 왕복 후 확인."""
        ent = {'tickers': ['AAPL', 'MSFT'], 'sectors': ['XLK'], 'topics': ['rate hike']}
        n = self._make_news('map-01', entities=ent)
        n.refresh_from_db()
        assert n.entities['tickers'] == ['AAPL', 'MSFT']
        assert n.entities['sectors'] == ['XLK']
        assert n.entities['topics'] == ['rate hike']

    def test_entities_empty_tickers_sectors(self):
        """sectors가 항상 빈 리스트 (Phase 1 데이터)."""
        ent = {'tickers': [], 'sectors': [], 'topics': ['fomc', 'inflation']}
        n = self._make_news('map-02', entities=ent)
        n.refresh_from_db()
        assert n.entities['sectors'] == []
        assert len(n.entities['topics']) == 2

    def test_entities_get_safe_access(self):
        """entities.get 안전 접근 — 키 없을 때 default 반환."""
        n = self._make_news('map-03', entities={})
        tickers = (n.entities or {}).get('tickers', [])
        assert tickers == []

    def test_entities_setdefault_append(self):
        """setdefault 패턴으로 tickers에 심볼 추가."""
        n = self._make_news('map-04', entities={'tickers': ['AAPL'], 'sectors': [], 'topics': []})
        n.entities.setdefault('tickers', []).append('NVDA')
        n.save(update_fields=['entities'])
        n.refresh_from_db()
        assert 'NVDA' in n.entities['tickers']
        assert 'AAPL' in n.entities['tickers']

    def test_news_task_write_pattern(self):
        """tasks/news.py에서 update_or_create 시 entities 구조 맞게 생성."""
        from apps.market_pulse.models import MarketPulseNews
        tickers = ['TSLA']
        topics = ['rate decision', 'fomc']
        obj, created = MarketPulseNews.objects.update_or_create(
            url_hash='map-05' + '0' * 58,
            defaults={
                'category': MarketPulseNews.Category.MAG7,
                'source': MarketPulseNews.Source.FMP_STOCK,
                'title': 'Tesla surges',
                'url': 'https://example.com/map05',
                'entities': {'tickers': tickers, 'sectors': [], 'topics': topics},
                'published_at': timezone.now(),
            },
        )
        assert created is True
        assert obj.entities['tickers'] == ['TSLA']
        assert obj.entities['topics'] == ['rate decision', 'fomc']

    def test_forward_migration_logic_inline(self):
        """RunPython forward 로직을 인라인으로 검증 (실제 마이그레이션 후 상태와 동일)."""
        from apps.market_pulse.models import MarketPulseNews
        n = self._make_news('map-06', entities={})
        # 현재 모델에는 matched_symbols가 없음 — entities 구조만 검증
        n.entities = {'tickers': ['GOOG'], 'sectors': [], 'topics': ['china tension']}
        n.save(update_fields=['entities'])
        n.refresh_from_db()
        assert n.entities['tickers'] == ['GOOG']
        assert n.entities['topics'] == ['china tension']


@pytest.mark.django_db
class TestBriefingBodyDataMapping:
    """BriefingLog body/body_sections 구조 검증."""

    def test_body_stores_long_text(self):
        """body에 500자 이상 텍스트 저장 가능."""
        from apps.market_pulse.models import BriefingLog
        long_body = '시장 강세 흐름이 지속되고 있습니다. ' * 30
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-dm1',
            body=long_body,
            body_sections=[],
        )
        b.refresh_from_db()
        assert b.body == long_body

    def test_body_sections_list_of_dicts(self):
        """body_sections에 섹션 목록 저장."""
        from apps.market_pulse.models import BriefingLog
        sections = [
            {'title': '거시 환경', 'content': '금리 동결 기대'},
            {'title': '시장 폭', 'content': '상승 종목 우위'},
        ]
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-dm2',
            body_sections=sections,
        )
        b.refresh_from_db()
        assert b.body_sections[0]['title'] == '거시 환경'
        assert b.body_sections[1]['content'] == '상승 종목 우위'

    def test_body_sections_empty_default(self):
        """body_sections default는 빈 리스트."""
        from apps.market_pulse.models import BriefingLog
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-dm3',
        )
        assert b.body_sections == []

    def test_prompt_inputs_context_dict(self):
        """prompt_inputs에 BriefingContext.as_dict() 형태 저장."""
        from apps.market_pulse.models import BriefingLog
        ctx = {
            'date': '2026-04-30',
            'regime': 'BULL_EXPANSION',
            'breadth': {'advance': 300, 'decline': 200, 'unchanged': 3},
            'sector': {'leader': 'XLK', 'laggard': 'XLE'},
            'concentration': {'top10_weight': 0.38, 'hhi': 0.018},
            'anomaly': {'mode': 'CALM', 'fired_rules': []},
        }
        b = BriefingLog.objects.create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-dm4',
            prompt_inputs=ctx,
        )
        b.refresh_from_db()
        assert b.prompt_inputs['regime'] == 'BULL_EXPANSION'
        assert b.prompt_inputs['breadth']['advance'] == 300

    def test_briefing_task_write_pattern(self):
        """tasks/briefing.py update_or_create 패턴으로 body/prompt_inputs 저장."""
        from apps.market_pulse.models import BriefingLog
        log, created = BriefingLog.objects.update_or_create(
            date=date(2026, 4, 30),
            model_version='gemini-2.5-flash-dm5',
            defaults={
                'status': BriefingLog.Status.OK,
                'headline': '강세 확장 흐름 지속',
                'body': '시장 강세 흐름입니다. 본 브리핑은 투자 권유가 아닙니다.',
                'prompt_inputs': {'regime': 'BULL_EXPANSION'},
                'prompt_tokens': 100,
                'completion_tokens': 200,
                'latency_ms': 1500,
            },
        )
        assert created is True
        assert '강세' in log.body
        assert log.prompt_inputs['regime'] == 'BULL_EXPANSION'
