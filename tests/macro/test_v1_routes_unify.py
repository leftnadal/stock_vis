"""
MP-UNIFY-1 회귀 — v1 macro 라우트 축소(10→3) 못박기.

의도: 무소비 개별 엔드포인트 7종(fear-greed/interest-rates/inflation/
  global-markets/calendar/vix/sectors) 제거 후에도 실소비 3종
  (pulse/sync/sync-status)은 그대로 resolve됨을 보장. 제거분이 되살아나면 RED.
근거: MP-UNIFY-S0 무소비 판정 + STEP 0 재실측(프론트 직접호출 0·테스트 0).
"""
import pytest
from django.urls import NoReverseMatch, reverse


# 존치(실소비) — reverse 성공해야 한다
SURVIVING = [
    ('macro:market-pulse', '/api/v1/macro/pulse/'),
    ('macro:data-sync', '/api/v1/macro/sync/'),
    ('macro:sync-status', '/api/v1/macro/sync/status/'),
]

# 제거(무소비) — reverse 실패(NoReverseMatch)해야 한다
REMOVED = [
    'macro:fear-greed',
    'macro:interest-rates',
    'macro:inflation',
    'macro:global-markets',
    'macro:calendar',
    'macro:vix',
    'macro:sectors',
]


@pytest.mark.parametrize('name,path', SURVIVING)
def test_surviving_routes_resolve(name, path):
    assert reverse(name) == path


@pytest.mark.parametrize('name', REMOVED)
def test_removed_routes_gone(name):
    with pytest.raises(NoReverseMatch):
        reverse(name)


def test_pulse_view_and_service_untouched():
    """pulse 진입점·serializer·집계 메서드 보존 (IDENTICAL 구조 보증)."""
    from apps.market_pulse.views import (
        DataSyncView,
        MarketPulseView,
        SyncStatusView,
    )
    from apps.market_pulse.serializers import MarketPulseResponseSerializer
    from apps.market_pulse.services.macro_service import MacroEconomicService

    # pulse 집계는 개별 섹션 서비스 메서드를 여전히 보유(로직 존치)
    for method in (
        'get_market_pulse_dashboard',
        'get_fear_greed_index',
        'get_interest_rates_dashboard',
        'get_inflation_dashboard',
        'get_global_markets_dashboard',
        'get_economic_calendar',
    ):
        assert hasattr(MacroEconomicService, method), method

    # pulse 응답 serializer 필드 계약 불변
    fields = set(MarketPulseResponseSerializer().get_fields().keys())
    assert fields == {
        'fear_greed', 'interest_rates', 'economy',
        'global_markets', 'calendar', 'last_updated',
    }


def test_removed_view_classes_absent():
    """제거된 개별 뷰 클래스는 더 이상 import 불가."""
    import apps.market_pulse.views as v

    for cls in (
        'FearGreedIndexView', 'InterestRatesView', 'InflationDashboardView',
        'GlobalMarketsView', 'EconomicCalendarView', 'VIXView',
        'SectorPerformanceView',
    ):
        assert not hasattr(v, cls), cls
