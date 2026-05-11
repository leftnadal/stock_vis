"""
Chain Sight 시드 폴백 계층 테스트.

2026-04-24 사건(pytest가 운영 Redis를 flush해 seed 캐시 소실) 재발 방지.
- Redis miss 시 SeedSnapshot DB에서 복구되는지
- DB도 없으면 비동기 복구 트리거가 걸리는지
- run_seed_selection이 DB+Redis 둘 다 쓰는지
"""

import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache

from chainsight.api.views import _get_today_seeds
from chainsight.models import SeedSnapshot
from chainsight.services.seed_selection import cache_seed_result
from chainsight.utils import get_market_date


@pytest.fixture
def seed_payload():
    return {
        'sector_summary': [
            {'sector': 'Technology', 'sector_display': 'Technology',
             'pct_change': 1.2, 'seed_count': 2, 'heat_total': 0, 'top_seed': 'NVDA'}
        ],
        'seeds_list': [
            {'symbol': 'NVDA', 'name': 'NVIDIA', 'sector': 'Technology',
             'industry': 'Semi', 'market_cap': 3e12, 'daily_return': 1.5,
             'volume_ratio': 1.2, 'seed_reasons': ['price_top5'],
             'seed_type': 'price', 'signal_count': 1},
            {'symbol': 'AMD', 'name': 'AMD', 'sector': 'Technology',
             'industry': 'Semi', 'market_cap': 2e11, 'daily_return': 0.8,
             'volume_ratio': 1.1, 'seed_reasons': ['price_top5'],
             'seed_type': 'price', 'signal_count': 1},
        ],
    }


@pytest.mark.django_db
class TestCacheSeedResult:
    def test_writes_to_db_and_redis(self, seed_payload):
        market_date = get_market_date()

        cache_seed_result(market_date, seed_payload['sector_summary'], seed_payload['seeds_list'])

        snapshot = SeedSnapshot.objects.get(market_date=market_date)
        assert snapshot.total_seeds == 2
        assert snapshot.sector_count == 1
        assert snapshot.payload['seeds'][0]['symbol'] == 'NVDA'

        cached = cache.get(f'chainsight:seeds:{market_date}')
        assert cached is not None
        parsed = json.loads(cached)
        assert parsed['total_seeds'] == 2

    def test_idempotent_same_day_upsert(self, seed_payload):
        market_date = get_market_date()

        cache_seed_result(market_date, seed_payload['sector_summary'], seed_payload['seeds_list'])
        cache_seed_result(market_date, [], [])

        assert SeedSnapshot.objects.filter(market_date=market_date).count() == 1
        snapshot = SeedSnapshot.objects.get(market_date=market_date)
        assert snapshot.total_seeds == 0


@pytest.mark.django_db
class TestGetTodaySeeds:
    def test_redis_hit_returns_cache(self, seed_payload):
        market_date = get_market_date()
        payload = {
            'date': str(market_date), 'total_seeds': 2,
            'sector_summary': seed_payload['sector_summary'],
            'seeds': seed_payload['seeds_list'],
        }
        cache.set(f'chainsight:seeds:{market_date}', json.dumps(payload), timeout=3600)

        result = _get_today_seeds()

        assert result['total_seeds'] == 2
        assert result['seeds'][0]['symbol'] == 'NVDA'

    def test_redis_miss_falls_back_to_db(self, seed_payload):
        market_date = get_market_date()
        SeedSnapshot.objects.create(
            market_date=market_date,
            payload={
                'date': str(market_date), 'total_seeds': 2,
                'sector_summary': seed_payload['sector_summary'],
                'seeds': seed_payload['seeds_list'],
            },
            total_seeds=2, sector_count=1,
        )

        result = _get_today_seeds()

        assert result['total_seeds'] == 2
        assert result['seeds'][0]['symbol'] == 'NVDA'
        # DB 폴백 시 Redis 재충전 확인
        cached = cache.get(f'chainsight:seeds:{market_date}')
        assert cached is not None

    def test_db_fallback_accepts_recent_past_snapshot(self, seed_payload):
        market_date = get_market_date()
        older_date = market_date - timedelta(days=3)
        SeedSnapshot.objects.create(
            market_date=older_date,
            payload={
                'date': str(older_date), 'total_seeds': 1,
                'sector_summary': [],
                'seeds': [seed_payload['seeds_list'][0]],
            },
            total_seeds=1, sector_count=0,
        )

        result = _get_today_seeds()

        assert result['total_seeds'] == 1

    def test_total_miss_triggers_async_recovery(self):
        market_date = get_market_date()

        with patch('chainsight.tasks.seed_tasks.run_seed_selection.delay') as mock_delay:
            result = _get_today_seeds()

        assert result == {
            'date': str(market_date), 'total_seeds': 0,
            'sector_summary': [], 'seeds': [],
        }
        mock_delay.assert_called_once()

    def test_recovery_lock_prevents_duplicate_triggers(self):
        with patch('chainsight.tasks.seed_tasks.run_seed_selection.delay') as mock_delay:
            _get_today_seeds()
            _get_today_seeds()

        assert mock_delay.call_count == 1
