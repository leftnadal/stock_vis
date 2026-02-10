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

    # 주간 데이터 업데이트 (주말)
    'update-weekly-prices': {
        'task': 'stocks.tasks.update_weekly_prices',
        'schedule': crontab(hour=0, minute=0, day_of_week=6),
    },

    # 재무제표 업데이트 (월 1일)
    'update-financial-statements': {
        'task': 'stocks.tasks.update_financial_statements',
        'schedule': crontab(hour=2, minute=0, day_of_month=1),
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
    # Market Movers 키워드 생성 태스크
    # ============================================================

    # 키워드 생성 파이프라인 (매일 오전 8시 - Market Movers 동기화 30분 후)
    'keyword-generation-pipeline': {
        'task': 'serverless.tasks.keyword_generation_pipeline',
        'schedule': crontab(hour=8, minute=0),  # 08:00 EST
        'kwargs': {'mover_type': 'gainers'},  # Gainers만 우선 처리
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # ============================================================
    # News 키워드 추출 태스크 (Phase 2)
    # ============================================================

    # 일일 뉴스 키워드 추출 (매일 오전 8시 - 뉴스 수집 후)
    'extract-daily-news-keywords': {
        'task': 'news.tasks.extract_daily_news_keywords',
        'schedule': crontab(hour=8, minute=0),  # 08:00 EST
        'options': {'expires': 3600}  # 1시간 후 만료
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

}

# 테스트 태스크 (선택적)
@app.task(bind=True)
def debug_task(self):
    """Celery 동작 확인용 테스트 태스크"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'