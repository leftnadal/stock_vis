"""
거시경제 데이터 API URL 라우팅 — macro v1 호환 진입점.

소속: apps/market_pulse (app 레이어 root).
역할: 옛 macro v1 API(/api/v1/macro/*) URL 경로. PR8b-1(2026-06-01)에서
  app label='marketpulse' 유지하면서 routing은 흡수. v2 API는 `api/urls.py` 별도.
주의: reverse('macro:...') 호환 유지 — namespace 'macro' 변경 금지.
"""
from django.urls import path

from .views import (
    DataSyncView,
    EconomicCalendarView,
    FearGreedIndexView,
    GlobalMarketsView,
    InflationDashboardView,
    InterestRatesView,
    MarketPulseView,
    SectorPerformanceView,
    SyncStatusView,
    VIXView,
)

app_name = 'macro'

urlpatterns = [
    # 전체 대시보드
    path('pulse/', MarketPulseView.as_view(), name='market-pulse'),

    # 개별 섹션
    path('fear-greed/', FearGreedIndexView.as_view(), name='fear-greed'),
    path('interest-rates/', InterestRatesView.as_view(), name='interest-rates'),
    path('inflation/', InflationDashboardView.as_view(), name='inflation'),
    path('global-markets/', GlobalMarketsView.as_view(), name='global-markets'),
    path('calendar/', EconomicCalendarView.as_view(), name='calendar'),

    # 단일 지표
    path('vix/', VIXView.as_view(), name='vix'),
    path('sectors/', SectorPerformanceView.as_view(), name='sectors'),

    # 데이터 동기화
    path('sync/', DataSyncView.as_view(), name='data-sync'),
    path('sync/status/', SyncStatusView.as_view(), name='sync-status'),
]
