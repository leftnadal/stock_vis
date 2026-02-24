"""
Serverless App URLs

Market Movers, Market Breadth, Screener Presets, Sector Heatmap, Alerts, Admin Dashboard
"""
from django.urls import path
from serverless import views
from serverless.views_admin import (
    AdminOverviewView, AdminStocksView, AdminScreenerView,
    AdminMarketPulseView, AdminNewsView, AdminSystemView, AdminTaskLogsView,
    AdminActionView, AdminTaskStatusView,
    AdminNewsCategoryView, AdminNewsCategoryDetailView, AdminNewsSectorOptionsView,
)


app_name = 'serverless'

urlpatterns = [
    # ========================================
    # Admin Dashboard
    # ========================================
    path('admin/dashboard/overview/', AdminOverviewView.as_view(), name='admin-overview'),
    path('admin/dashboard/stocks/', AdminStocksView.as_view(), name='admin-stocks'),
    path('admin/dashboard/screener/', AdminScreenerView.as_view(), name='admin-screener'),
    path('admin/dashboard/market-pulse/', AdminMarketPulseView.as_view(), name='admin-market-pulse'),
    path('admin/dashboard/news/', AdminNewsView.as_view(), name='admin-news'),
    path('admin/dashboard/system/', AdminSystemView.as_view(), name='admin-system'),
    path('admin/dashboard/tasks/', AdminTaskLogsView.as_view(), name='admin-tasks'),
    path('admin/dashboard/actions/', AdminActionView.as_view(), name='admin-actions'),
    path('admin/dashboard/actions/status/<str:task_id>/', AdminTaskStatusView.as_view(), name='admin-task-status'),
    path('admin/dashboard/news/categories/', AdminNewsCategoryView.as_view(), name='admin-news-categories'),
    path('admin/dashboard/news/categories/<int:category_id>/', AdminNewsCategoryDetailView.as_view(), name='admin-news-category-detail'),
    path('admin/dashboard/news/sector-options/', AdminNewsSectorOptionsView.as_view(), name='admin-news-sector-options'),

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
    path('screener/chain-sight', views.chain_sight_api, name='chain-sight'),

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
    # Investment Thesis (Phase 2.3)
    # ========================================
    path('thesis/generate', views.generate_thesis, name='generate-thesis'),
    path('thesis/shared/<str:share_code>', views.get_shared_thesis, name='get-shared-thesis'),
    path('thesis/<int:thesis_id>', views.get_thesis, name='get-thesis'),
    path('thesis', views.list_theses, name='list-theses'),

    # ========================================
    # Chain Sight Stock (개별 종목 탐험)
    # ========================================
    path('chain-sight/stock/<str:symbol>', views.chain_sight_stock_api, name='chain-sight-stock'),
    path('chain-sight/stock/<str:symbol>/category/<str:category_id>', views.chain_sight_category_api, name='chain-sight-category'),
    path('chain-sight/stock/<str:symbol>/sync', views.chain_sight_sync_api, name='chain-sight-sync'),
    path('chain-sight/stock/<str:symbol>/track', views.chain_sight_track_api, name='chain-sight-track'),

    # ========================================
    # Chain Sight Neo4j Graph (온톨로지 그래프)
    # ========================================
    path('chain-sight/graph/stats', views.chain_sight_neo4j_stats_api, name='chain-sight-graph-stats'),
    path('chain-sight/graph/<str:symbol>', views.chain_sight_graph_api, name='chain-sight-graph'),
    path('chain-sight/graph/<str:symbol>/sync', views.chain_sight_neo4j_sync_api, name='chain-sight-graph-sync'),

    # ========================================
    # Chain Sight Phase 3: ETF Holdings
    # ========================================
    path('etf/status', views.etf_collection_status, name='etf-status'),
    path('etf/sync', views.trigger_etf_holdings_sync, name='etf-sync'),
    path('etf/resolve-url', views.resolve_etf_csv_url, name='etf-resolve-url'),
    path('etf/<str:etf_symbol>/holdings', views.etf_holdings_api, name='etf-holdings'),
    path('etf/stock/<str:symbol>/themes', views.stock_themes_api, name='stock-themes'),
    path('etf/stock/<str:symbol>/peers', views.etf_peers_api, name='etf-peers'),
    path('themes', views.theme_list_api, name='themes'),
    path('themes/refresh', views.refresh_theme_matches_api, name='themes-refresh'),
    path('themes/<str:theme_id>/stocks', views.theme_stocks_api, name='theme-stocks'),

    # ========================================
    # Chain Sight Phase 5: LLM Relation Extraction
    # ========================================
    path('llm-relations/extract', views.extract_relations_from_news_api, name='llm-relations-extract'),
    path('llm-relations/sync', views.sync_llm_relations_api, name='llm-relations-sync'),
    path('llm-relations/stats', views.llm_relations_stats_api, name='llm-relations-stats'),
    path('llm-relations/<str:symbol>', views.get_llm_relations_api, name='llm-relations-get'),

    # ========================================
    # Chain Sight Phase 7: Institutional Holdings (SEC 13F)
    # ========================================
    path('institutional/sync', views.institutional_sync_api, name='institutional-sync'),
    path('institutional/<str:symbol>/peers', views.institutional_peers_api, name='institutional-peers'),
    path('institutional/<str:symbol>', views.institutional_holdings_api, name='institutional-holdings'),

    # ========================================
    # Chain Sight Phase 8: Regulatory + Patent Network
    # ========================================
    path('regulatory/<str:symbol>', views.get_regulatory_relations_api, name='regulatory-get'),
    path('patent-network/<str:symbol>', views.get_patent_relations_api, name='patent-network-get'),

    # ========================================
    # Health Check
    # ========================================
    path('health', views.health_check, name='health-check'),
]
