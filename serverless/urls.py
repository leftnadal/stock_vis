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

    # 키워드 (순서 중요: 구체적인 경로가 먼저)
    path('keywords/batch', views.get_batch_keywords, name='batch-keywords'),
    path('keywords/generate-all', views.trigger_keyword_generation, name='generate-keywords'),
    path('keywords/generate-screener', views.generate_screener_keywords, name='generate-screener-keywords'),
    path('keywords/<str:symbol>', views.get_keywords, name='get-keywords'),

    # 헬스체크
    path('health', views.health_check, name='health-check'),
]
