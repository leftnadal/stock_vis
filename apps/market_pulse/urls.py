"""
거시경제 데이터 API URL 라우팅 — macro v1 호환 진입점.

소속: apps/market_pulse (app 레이어 root).
역할: 옛 macro v1 API(/api/v1/macro/*) URL 경로. PR8b-1(2026-06-01)에서
  app label='marketpulse' 유지하면서 routing은 흡수. v2 API는 `api/urls.py` 별도.
주의: reverse('macro:...') 호환 유지 — namespace 'macro' 변경 금지.
  MP-UNIFY-1(2026-07-29): 무소비 개별 섹션·단일지표 라우트 7종 제거
  (fear-greed/interest-rates/inflation/global-markets/calendar/vix/sectors).
  개별 섹션 로직은 pulse 집계(MacroEconomicService) 경유로 존치. 실소비 3종만 유지.
"""
from django.urls import path

from .views import (
    DataSyncView,
    MarketPulseView,
    SyncStatusView,
)

app_name = 'macro'

urlpatterns = [
    # 전체 대시보드 (개별 섹션은 이 집계 응답 안에서 유지)
    path('pulse/', MarketPulseView.as_view(), name='market-pulse'),

    # 데이터 동기화
    path('sync/', DataSyncView.as_view(), name='data-sync'),
    path('sync/status/', SyncStatusView.as_view(), name='sync-status'),
]
