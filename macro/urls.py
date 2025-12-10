"""
거시경제 데이터 API URL 라우팅
"""
from django.urls import path
from .views import (
    MarketPulseView,
    FearGreedIndexView,
    InterestRatesView,
    InflationDashboardView,
    GlobalMarketsView,
    EconomicCalendarView,
    VIXView,
    SectorPerformanceView,
    DataSyncView,
    SyncStatusView,
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
