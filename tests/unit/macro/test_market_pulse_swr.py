"""
MP2-SUBPAGES HOTFIX-1 — get_market_pulse_dashboard SWR 캐시 정책 회귀.

검증(외부 API 무호출 — _compute_market_pulse_dashboard 모킹):
  ① fresh 히트 → 캐시 반환 + 백그라운드 갱신 enqueue 없음
  ② fresh 미스 + stale 존재 → stale 즉시 반환 + delay 1회 + 락 dedup(2연속 호출도 delay 1회)
  ③ 최초 콜드(둘 다 미스) → 라이브 계산 1회 + fresh/stale 양 키 저장
  ④ 계산 실패 + 경합 stale → 500 대신 stale 폴백
  ⑤ 계산 실패 + stale 없음 → 재발생(뷰 500 경로 유지)
근거: D-SUBPAGES-SWR — 장외(KST) 콜드 캐시 + ET-장중-한정 워밍 → 요청 스레드 28s 라이브
  집계 대기가 증상. stale 즉시 응답 + 백그라운드 1회 갱신으로 해소(외부 호출 무증가).
"""
from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.market_pulse.services.macro_service import MacroEconomicService

FULL = MacroEconomicService.FULL_CACHE_KEY
STALE = MacroEconomicService.STALE_CACHE_KEY
LOCK = MacroEconomicService.REFRESH_LOCK_KEY

FRESH_PAYLOAD = {'last_updated': '2026-08-31T00:00:00+00:00', 'fear_greed': {'value': 50}}
STALE_PAYLOAD = {'last_updated': '2026-08-30T00:00:00+00:00', 'fear_greed': {'value': 42}}

DELAY_PATH = 'apps.market_pulse.tasks.macro.refresh_market_pulse_cache.delay'
COMPUTE = 'apps.market_pulse.services.macro_service.MacroEconomicService._compute_market_pulse_dashboard'


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_fresh_hit_returns_cache_no_enqueue():
    """① fresh 히트 → 캐시 그대로 반환, 라이브 계산·enqueue 없음."""
    cache.set(FULL, FRESH_PAYLOAD, 60)
    with patch(DELAY_PATH) as delay, patch(COMPUTE) as compute:
        out = MacroEconomicService().get_market_pulse_dashboard()
    assert out == FRESH_PAYLOAD
    compute.assert_not_called()
    delay.assert_not_called()


def test_stale_return_enqueues_once_with_lock_dedup():
    """② fresh 미스 + stale 존재 → stale 즉시 반환, 2연속 호출에도 enqueue 정확히 1회(락 dedup)."""
    cache.set(STALE, STALE_PAYLOAD, 86400)
    with patch(DELAY_PATH) as delay, patch(COMPUTE) as compute:
        out1 = MacroEconomicService().get_market_pulse_dashboard()
        out2 = MacroEconomicService().get_market_pulse_dashboard()
    assert out1 == STALE_PAYLOAD
    assert out2 == STALE_PAYLOAD
    compute.assert_not_called()        # 요청 스레드 라이브 집계 없음(28s 회피)
    delay.assert_called_once()         # 락 dedup — 백그라운드 갱신 1회만
    assert cache.get(LOCK) is not None  # 갱신 락 점유 중


def test_first_cold_computes_and_stores_both_keys():
    """③ 최초 콜드(fresh·stale 둘 다 미스) → 라이브 계산 1회 + fresh/stale 양 키 저장."""
    with patch(DELAY_PATH) as delay, \
            patch(COMPUTE, return_value=FRESH_PAYLOAD) as compute:
        out = MacroEconomicService().get_market_pulse_dashboard()
    assert out == FRESH_PAYLOAD
    compute.assert_called_once()
    assert cache.get(FULL) == FRESH_PAYLOAD
    assert cache.get(STALE) == FRESH_PAYLOAD
    delay.assert_not_called()          # 콜드 계산은 스스로 처리 — 재-enqueue 없음


def test_compute_failure_falls_back_to_racing_stale():
    """④ 계산 실패 + (경합으로 채워진) stale → 500 대신 stale 폴백."""
    reads = {'stale': 0}
    real_get = cache.get

    def racey_get(key, *args, **kwargs):
        if key == STALE:
            reads['stale'] += 1
            # 1st(결정 시점) None → 계산 진입 / 2nd(except 재조회) stale 폴백
            return None if reads['stale'] == 1 else STALE_PAYLOAD
        return real_get(key, *args, **kwargs)

    with patch('apps.market_pulse.services.macro_service.cache.get', side_effect=racey_get), \
            patch(COMPUTE, side_effect=RuntimeError('FMP 402')):
        out = MacroEconomicService().get_market_pulse_dashboard()
    assert out == STALE_PAYLOAD


def test_compute_failure_no_stale_reraises():
    """⑤ 계산 실패 + stale 없음 → 재발생(뷰 500 경로 유지)."""
    with patch(COMPUTE, side_effect=RuntimeError('FRED down')):
        with pytest.raises(RuntimeError):
            MacroEconomicService().get_market_pulse_dashboard()


def test_force_refresh_recomputes_and_clears_lock():
    """워밍 태스크 경로: force_refresh → 캐시 무시 재계산 + 양 키 갱신 + 락 해제(무한 재-enqueue 차단)."""
    cache.set(FULL, {'stale': 'old'}, 60)
    cache.add(LOCK, '1', 120)
    with patch(DELAY_PATH) as delay, \
            patch(COMPUTE, return_value=FRESH_PAYLOAD) as compute:
        out = MacroEconomicService().get_market_pulse_dashboard(force_refresh=True)
    assert out == FRESH_PAYLOAD
    compute.assert_called_once()
    assert cache.get(FULL) == FRESH_PAYLOAD
    assert cache.get(STALE) == FRESH_PAYLOAD
    assert cache.get(LOCK) is None     # 락 해제 — 다음 미스가 갱신 재-enqueue 가능
    delay.assert_not_called()          # force 경로는 스스로 계산 — enqueue 없음
