import os
from celery import Celery
from celery.schedules import crontab

# Django 설정 모듈을 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Celery 앱 생성
app = Celery('stock_vis')

# Django 설정 파일에서 Celery 설정 가져오기
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django 앱에서 태스크 자동 발견
app.autodiscover_tasks()

# 정기 태스크 스케줄 설정
app.conf.beat_schedule = {
    # ============================================================
    # Stocks 태스크
    # ============================================================

    # 실시간 주가 업데이트 (시장 개장 시간, 5분마다)
    'update-realtime-prices': {
        'task': 'stocks.tasks.update_realtime_prices',
        'schedule': crontab(minute='*/5', hour='9-16', day_of_week='1-5'),
        'kwargs': {'priority': 'high'}
    },

    # 일일 종가 업데이트 (시장 마감 후)
    'update-daily-prices': {
        'task': 'stocks.tasks.update_daily_prices',
        'schedule': crontab(hour=17, minute=0, day_of_week='1-5'),
    },

    # 주간 데이터 집계 — DailyPrice → WeeklyPrice (API 호출 없음, 토요일 01:00)
    'aggregate-weekly-prices': {
        'task': 'stocks.tasks.aggregate_weekly_prices',
        'schedule': crontab(hour=1, minute=0, day_of_week=6),
        'options': {'expires': 3600}
    },

    # S&P 500 재무제표 순환 배치 (FMP, 101개/일, 5일에 전체 1회전, 평일 20:00)
    'sync-sp500-financials': {
        'task': 'stocks.tasks.sync_sp500_financials',
        'schedule': crontab(hour=20, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # 포트폴리오 가치 계산 (시장 개장 시간, 10분마다)
    'calculate-portfolio-values': {
        'task': 'users.tasks.calculate_portfolio_values',
        'schedule': crontab(minute='*/10', hour='9-16', day_of_week='1-5'),
    },

    # ============================================================
    # Macro (거시경제) 태스크
    # ============================================================

    # 거시경제 지표 업데이트 (매시간 - FRED API)
    'update-economic-indicators': {
        'task': 'macro.tasks.update_economic_indicators',
        'schedule': crontab(minute=0),  # 매시 정각
    },

    # 시장 지수 업데이트 (시장 시간 중 5분마다 - FMP API)
    'update-market-indices': {
        'task': 'macro.tasks.update_market_indices',
        'schedule': crontab(minute='*/5', hour='9-16', day_of_week='1-5'),
    },

    # 경제 캘린더 업데이트 (매일 새벽 1시)
    'update-economic-calendar': {
        'task': 'macro.tasks.update_economic_calendar',
        'schedule': crontab(hour=1, minute=0),
    },

    # Market Pulse 캐시 갱신 (시장 시간 중 1분마다)
    'refresh-market-pulse-cache': {
        'task': 'macro.tasks.refresh_market_pulse_cache',
        'schedule': crontab(minute='*', hour='9-16', day_of_week='1-5'),
    },

    # 오래된 데이터 정리 (매주 일요일 새벽 3시)
    'cleanup-old-macro-data': {
        'task': 'macro.tasks.cleanup_old_data',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },

    # ============================================================
    # RAG Analysis 태스크
    # ============================================================

    # Neo4j 헬스체크 (5분마다)
    'neo4j-health-check': {
        'task': 'rag_analysis.tasks.health_check_neo4j',
        'schedule': crontab(minute='*/5'),
    },

    # ============================================================
    # Semantic Cache 태스크
    # ============================================================

    # 만료된 캐시 정리 (매일 새벽 4시)
    'cleanup-expired-semantic-cache': {
        'task': 'rag_analysis.tasks.cleanup_expired_semantic_cache',
        'schedule': crontab(hour=4, minute=0),
    },

    # 캐시 워밍 (매주 일요일 새벽 4시 30분)
    'warm-semantic-cache': {
        'task': 'rag_analysis.tasks.warm_semantic_cache',
        'schedule': crontab(hour=4, minute=30, day_of_week=0),
        'kwargs': {'limit': 100}
    },

    # 캐시 통계 조회 (매시간, 모니터링용)
    'semantic-cache-stats': {
        'task': 'rag_analysis.tasks.get_semantic_cache_stats',
        'schedule': crontab(minute=0),
    },

    # ============================================================
    # Market Movers 동기화 + 키워드 생성 태스크
    # ============================================================

    # Market Movers 동기화 (매일 07:30 EST, 시장 개장 전)
    'sync-daily-market-movers': {
        'task': 'serverless.tasks.sync_daily_market_movers',
        'schedule': crontab(hour=7, minute=30, day_of_week='1-5'),
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # 키워드 생성 파이프라인 (매일 오전 8시 - Market Movers 동기화 30분 후)
    'keyword-generation-pipeline': {
        'task': 'serverless.tasks.keyword_generation_pipeline',
        'schedule': crontab(hour=8, minute=0),  # 08:00 EST
        'kwargs': {'mover_type': 'gainers'},  # Gainers만 우선 처리
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # ============================================================
    # News 수집 + 감성 분석 + 키워드 추출 태스크
    # ============================================================

    # 일일 종목 뉴스 수집 (매일 06:00 EST, Market Movers 수집 전)
    'collect-daily-news': {
        'task': 'news.tasks.collect_daily_news',
        'schedule': crontab(hour=6, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # 시장 뉴스 수집 (매일 12:00 EST)
    'collect-market-news-noon': {
        'task': 'news.tasks.collect_market_news',
        'schedule': crontab(hour=12, minute=0, day_of_week='1-5'),
        'options': {'expires': 600}  # 10분 후 만료
    },

    # 시장 뉴스 수집 (매일 18:00 EST)
    'collect-market-news-evening': {
        'task': 'news.tasks.collect_market_news',
        'schedule': crontab(hour=18, minute=0, day_of_week='1-5'),
        'options': {'expires': 600}  # 10분 후 만료
    },

    # 일일 감성 분석 집계 (매일 09:00 EST, 뉴스 수집 후)
    'aggregate-daily-sentiment': {
        'task': 'news.tasks.aggregate_daily_sentiment',
        'schedule': crontab(hour=9, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # 일일 뉴스 키워드 추출 (매일 오전 8시 - 뉴스 수집 후)
    'extract-daily-news-keywords': {
        'task': 'news.tasks.extract_daily_news_keywords',
        'schedule': crontab(hour=8, minute=0),  # 08:00 EST
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # 카테고리 뉴스 수집 - High (2회/일: 06:30 + 17:00 EST, 평일)
    'collect-category-news-high-morning': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=6, minute=30, day_of_week='1-5'),
        'kwargs': {'priority_filter': 'high'},
        'options': {'expires': 3600}
    },
    'collect-category-news-high-evening': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=17, minute=0, day_of_week='1-5'),
        'kwargs': {'priority_filter': 'high'},
        'options': {'expires': 3600}
    },

    # 카테고리 뉴스 수집 - Medium (1회/일: 07:00 EST, 평일)
    'collect-category-news-medium': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=7, minute=0, day_of_week='1-5'),
        'kwargs': {'priority_filter': 'medium'},
        'options': {'expires': 3600}
    },

    # 카테고리 뉴스 수집 - Low (주 1회: 월요일 07:30 EST)
    'collect-category-news-low': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=7, minute=30, day_of_week=1),
        'kwargs': {'priority_filter': 'low'},
        'options': {'expires': 3600}
    },

    # ============================================================
    # News Intelligence Pipeline v3 태스크
    # ============================================================

    # 뉴스 분류 배치 (매 2시간, 평일, 수집 후 분류)
    'classify-news-batch-morning': {
        'task': 'news.tasks.classify_news_batch',
        'schedule': crontab(hour='8,10,12,14,16,18', minute=15, day_of_week='1-5'),
        'kwargs': {'hours': 3},
        'options': {'expires': 3600}
    },

    # LLM 심층 분석 배치 (매 2시간, 평일, 분류 후 분석)
    'analyze-news-deep-batch': {
        'task': 'news.tasks.analyze_news_deep',
        'schedule': crontab(hour='8,10,12,14,16,18', minute=30, day_of_week='1-5'),
        'kwargs': {'max_articles': 50},
        'options': {'expires': 3600}
    },

    # ML Label 수집 (매일 19:00 EST, 장 마감 + 1시간)
    'collect-ml-labels': {
        'task': 'news.tasks.collect_ml_labels',
        'schedule': crontab(hour=19, minute=0, day_of_week='1-5'),
        'kwargs': {'lookback_days': 2},
        'options': {'expires': 3600}
    },

    # Neo4j 뉴스 이벤트 동기화 (매 2시간, 평일, LLM 분석 후)
    'sync-news-to-neo4j': {
        'task': 'news.tasks.sync_news_to_neo4j',
        'schedule': crontab(hour='8,10,12,14,16,18', minute=45, day_of_week='1-5'),
        'kwargs': {'max_articles': 100},
        'options': {'expires': 3600}
    },

    # 만료된 뉴스 이벤트 관계 정리 (매일 04:00 EST)
    'cleanup-expired-news-relationships': {
        'task': 'news.tasks.cleanup_expired_news_relationships',
        'schedule': crontab(hour=4, minute=0),
        'options': {'expires': 3600}
    },

    # ML 가중치 학습 (매주 일요일 03:00 EST)
    'train-importance-model': {
        'task': 'news.tasks.train_importance_model',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
        'options': {'expires': 7200}  # 2시간 후 만료
    },

    # Shadow Mode 비교 리포트 (매주 일요일 03:30 EST, 학습 직후)
    'generate-shadow-report': {
        'task': 'news.tasks.generate_shadow_report',
        'schedule': crontab(hour=3, minute=30, day_of_week=0),
        'kwargs': {'days': 7},
        'options': {'expires': 3600}
    },

    # ML 자동 배포 체크 (매주 일요일 04:00 EST, Shadow 리포트 이후)
    'check-auto-deploy': {
        'task': 'news.tasks.check_auto_deploy',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
        'options': {'expires': 3600}
    },

    # 주간 ML 성능 리포트 (매주 일요일 04:15 EST, auto deploy 이후)
    'generate-weekly-ml-report': {
        'task': 'news.tasks.generate_weekly_ml_report',
        'schedule': crontab(hour=4, minute=15, day_of_week=0),
        'options': {'expires': 3600}
    },

    # ML 성능 모니터링 (매주 일요일 04:20 EST, 주간 리포트 직후)
    'monitor-ml-performance': {
        'task': 'news.tasks.monitor_ml_performance',
        'schedule': crontab(hour=4, minute=20, day_of_week=0),
        'options': {'expires': 3600}
    },

    # LightGBM 학습 (매주 일요일 04:30 EST, 조건 충족 시만 실행)
    'train-lightgbm-model': {
        'task': 'news.tasks.train_lightgbm_model',
        'schedule': crontab(hour=4, minute=30, day_of_week=0),
        'options': {'expires': 7200}  # 2시간 후 만료
    },

    # ============================================================
    # ETF Holdings 자동 수집 태스크
    # ============================================================

    # ETF Holdings 자동 수집 (매주 월요일 06:00 EST)
    # 실패 시 이메일 알림 발송: goid545@naver.com, jinie545@gmail.com
    'sync-etf-holdings': {
        'task': 'serverless.tasks.sync_etf_holdings',
        'schedule': crontab(hour=6, minute=0, day_of_week=1),  # 월요일 06:00 EST
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # ============================================================
    # Supply Chain (Phase 4) 태스크
    # ============================================================

    # 공급망 배치 동기화 (매월 15일 03:00 EST)
    # S&P 500 상위 100개 종목의 공급사/고객사 관계를 SEC 10-K에서 추출
    'sync-supply-chain-batch': {
        'task': 'serverless.tasks.sync_supply_chain_batch',
        'schedule': crontab(hour=3, minute=0, day_of_month=15),
        'options': {'expires': 86400}  # 24시간 후 만료
    },

    # ============================================================
    # Screener 태스크 (Market Breadth, Sector Heatmap, Alerts)
    # ============================================================

    # Market Breadth 일일 계산 (장 마감 후 16:30 ET)
    'calculate-market-breadth': {
        'task': 'serverless.tasks.calculate_daily_market_breadth',
        'schedule': crontab(hour=16, minute=30, day_of_week='1-5'),
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # Sector Heatmap 일일 계산 (장 마감 후 16:35 ET)
    'calculate-sector-heatmap': {
        'task': 'serverless.tasks.calculate_daily_sector_heatmap',
        'schedule': crontab(hour=16, minute=35, day_of_week='1-5'),
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # Screener Alerts 체크 (시장 시간 중 15분마다)
    'check-screener-alerts': {
        'task': 'serverless.tasks.check_screener_alerts',
        'schedule': crontab(minute='*/15', hour='9-16', day_of_week='1-5'),
        'options': {'expires': 600}  # 10분 후 만료
    },

    # ============================================================
    # S&P 500 동기화 태스크
    # ============================================================

    # S&P 500 구성 종목 동기화 (매월 1일 02:00 ET)
    'sync-sp500-constituents': {
        'task': 'stocks.tasks.sync_sp500_constituents',
        'schedule': crontab(hour=2, minute=0, day_of_month=1),
        'options': {'expires': 86400}  # 24시간 후 만료
    },

    # S&P 500 EOD 가격 동기화 (매일 18:00 ET, Mon-Fri, 장 마감 + 2시간)
    'sync-sp500-eod-prices': {
        'task': 'stocks.tasks.sync_sp500_eod_prices',
        'schedule': crontab(hour=18, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # ============================================================
    # Chain Sight Phase 6: News Relation Matcher
    # ============================================================

    # 뉴스에서 관계 키워드 자동 추출 (매일 09:00 EST, 뉴스 수집 후)
    'extract-news-relations': {
        'task': 'serverless.tasks.extract_news_relations',
        'schedule': crontab(hour=9, minute=0),
        'args': (24,),  # 최근 24시간
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # ============================================================
    # Chain Sight Phase 6D: Relationship Keyword Enrichment
    # ============================================================

    # 관계 키워드 Enrichment (매일 05:30 EST, Gemini Free Tier)
    'enrich-relationship-keywords': {
        'task': 'serverless.tasks.enrich_relationship_keywords',
        'schedule': crontab(hour=5, minute=30),
        'kwargs': {'limit': 100},
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # ============================================================
    # Chain Sight Phase 7: Institutional Holdings (SEC 13F)
    # ============================================================

    # 기관 보유 현황 동기화 (매월 16일 04:00 EST, 태스크 내에서 분기 체크)
    'sync-institutional-holdings': {
        'task': 'serverless.tasks.sync_institutional_holdings',
        'schedule': crontab(hour=4, minute=0, day_of_month=16),
        'options': {'expires': 86400}  # 24시간 후 만료
    },

    # ============================================================
    # Chain Sight Phase 8: Regulatory + Patent Network
    # ============================================================

    # 규제 관계 스캔 (매주 월요일 04:00 EST)
    'scan-regulatory-relationships': {
        'task': 'serverless.tasks.scan_regulatory_relationships',
        'schedule': crontab(hour=4, minute=0, day_of_week=1),
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # 특허 네트워크 빌드 (매월 1일 04:30 EST)
    'build-patent-network': {
        'task': 'serverless.tasks.build_patent_network',
        'schedule': crontab(hour=4, minute=30, day_of_month=1),
        'options': {'expires': 86400}  # 24시간 후 만료
    },

}

# 테스트 태스크 (선택적)
@app.task(bind=True)
def debug_task(self):
    """Celery 동작 확인용 테스트 태스크"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'