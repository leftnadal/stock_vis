"""
Serverless App URLs
"""
from django.urls import path
from serverless import views


app_name = 'serverless'

urlpatterns = [
    # Market Movers
    path('movers', views.market_movers_api, name='market-movers'),
    path('movers/<str:symbol>', views.market_mover_detail, name='market-mover-detail'),

    # 동기화
    path('sync', views.trigger_sync, name='trigger-sync'),
    path('sync-now', views.sync_now, name='sync-now'),

    # 헬스체크
    path('health', views.health_check, name='health-check'),
]
