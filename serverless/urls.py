"""
Serverless App URLs

Market Movers, Market Breadth, Screener Presets, Sector Heatmap, Alerts
"""
from django.urls import path
from serverless import views


app_name = 'serverless'

urlpatterns = [
    # ========================================
    # Market Movers
    # ========================================
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

    # ========================================
    # Market Breadth (시장 건강도)
    # ========================================
    path('breadth', views.market_breadth_api, name='market-breadth'),
    path('breadth/history', views.market_breadth_history, name='market-breadth-history'),
    path('breadth/sync', views.trigger_breadth_sync, name='trigger-breadth-sync'),

    # ========================================
    # Sector Heatmap (섹터 히트맵)
    # ========================================
    path('heatmap/sectors', views.sector_heatmap_api, name='sector-heatmap'),
    path('heatmap/sectors/<str:sector>/stocks', views.sector_stocks_api, name='sector-stocks'),
    path('heatmap/sync', views.trigger_heatmap_sync, name='trigger-heatmap-sync'),

    # ========================================
    # Screener Presets (프리셋)
    # ========================================
    path('presets', views.screener_presets_api, name='screener-presets'),
    path('presets/trending', views.trending_presets, name='trending-presets'),
    path('presets/shared/<str:share_code>', views.get_shared_preset, name='get-shared-preset'),
    path('presets/import/<str:share_code>', views.import_preset, name='import-preset'),
    path('presets/<int:preset_id>', views.screener_preset_detail, name='screener-preset-detail'),
    path('presets/<int:preset_id>/execute', views.execute_preset, name='execute-preset'),
    path('presets/<int:preset_id>/share', views.share_preset, name='share-preset'),

    # ========================================
    # Screener Filters (필터 메타데이터)
    # ========================================
    path('filters', views.screener_filters_api, name='screener-filters'),

    # ========================================
    # Advanced Screener (고급 스크리너)
    # ========================================
    path('screener', views.advanced_screener_api, name='advanced-screener'),

    # ========================================
    # Screener Alerts (알림 시스템 - Phase 1)
    # ========================================
    path('alerts', views.screener_alerts_api, name='screener-alerts'),
    path('alerts/history', views.alert_history_api, name='alert-history'),
    path('alerts/history/<int:history_id>/read', views.mark_alert_read, name='mark-alert-read'),
    path('alerts/history/<int:history_id>/dismiss', views.dismiss_alert, name='dismiss-alert'),
    path('alerts/<int:alert_id>', views.screener_alert_detail, name='screener-alert-detail'),
    path('alerts/<int:alert_id>/toggle', views.toggle_alert, name='toggle-alert'),

    # ========================================
    # Health Check
    # ========================================
    path('health', views.health_check, name='health-check'),
]
