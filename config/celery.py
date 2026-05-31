import logging
import os
import platform

from celery import Celery
from celery.schedules import crontab
from celery.signals import (
    task_failure,
    task_retry,
    worker_process_init,
    worker_shutdown,
)

# macOS fork 안전성:
# 1. Objective-C 런타임 fork safety 체크 비활성화 (SIGSEGV 방지)
# 2. libpq GSS/Kerberos 암호화 비활성화 (fork 후 XPC 크래시 방지)
# 3. macOS에서는 solo pool 강제 (fork 자체를 제거하여 C 확장 크래시 원천 차단)
if platform.system() == 'Darwin':
    os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')
    os.environ.setdefault('PGGSSENCMODE', 'disable')

IS_MACOS = platform.system() == 'Darwin'

# Django 설정 모듈을 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Celery 앱 생성
app = Celery('stock_vis')

# Django 설정 파일에서 Celery 설정 가져오기
app.config_from_object('django.conf:settings', namespace='CELERY')

# macOS: solo pool 강제 — fork를 사용하지 않아 모든 C 확장 크래시 방지
# (PyTorch, scikit-learn/OpenMP, libpq/GSS 등)
# 프로덕션 Linux에서는 prefork가 기본값으로 유지됨
if IS_MACOS:
    app.conf.worker_pool = 'solo'

# Django 앱에서 태스크 자동 발견
app.autodiscover_tasks()

# Neo4j 태스크 → neo4j 큐로 격리 (--pool=solo 워커에서 처리, SIGSEGV 방지)
app.conf.task_routes = {
    'services.rag_analysis.tasks.health_check_neo4j': {'queue': 'neo4j'},
    'services.rag_analysis.tasks.cleanup_expired_semantic_cache': {'queue': 'neo4j'},
    'services.rag_analysis.tasks.warm_semantic_cache': {'queue': 'neo4j'},
    'services.rag_analysis.tasks.get_semantic_cache_stats': {'queue': 'neo4j'},
    'services.rag_analysis.tasks.sync_stock_to_neo4j': {'queue': 'neo4j'},
    'services.rag_analysis.tasks.delete_stock_from_neo4j': {'queue': 'neo4j'},
    'services.rag_analysis.tasks.batch_sync_stocks_to_neo4j': {'queue': 'neo4j'},
    'services.rag_analysis.tasks.invalidate_graph_cache': {'queue': 'neo4j'},
    'news.tasks.sync_news_to_neo4j': {'queue': 'neo4j'},
    'news.tasks.cleanup_expired_news_relationships': {'queue': 'neo4j'},
    'serverless.tasks.enrich_relationship_keywords': {'queue': 'neo4j'},
    # Chain Sight Neo4j 동기화
    'apps.chain_sight.tasks.sync_tasks.sync_profiles_to_neo4j': {'queue': 'neo4j'},
    'apps.chain_sight.tasks.sync_tasks.sync_relations_to_neo4j': {'queue': 'neo4j'},
    'chainsight-neo4j-dirty-sync': {'queue': 'neo4j'},
    # SEC Pipeline Neo4j 동기화
    'services.sec_pipeline.tasks.sync_dirty_to_neo4j': {'queue': 'neo4j'},
}

# ============================================================
# Celery Error Monitoring — 시그널 핸들러
# ============================================================
error_monitor_logger = logging.getLogger('celery.error_monitor')


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, **kw):
    error_monitor_logger.error(
        f"[TASK FAILURE] {sender.name} | task_id={task_id} | "
        f"{type(exception).__name__}: {str(exception)[:200]}"
    )


@task_retry.connect
def handle_task_retry(sender=None, request=None, reason=None, **kwargs):
    error_monitor_logger.warning(
        f"[TASK RETRY] {sender.name} | task_id={request.id} | "
        f"retries={request.retries} | reason={str(reason)[:200]}"
    )


# ============================================================
# Neo4j Fork Safety — SIGSEGV 방지
# ============================================================

@worker_process_init.connect
def reset_connections_after_fork(**kwargs):
    """
    Fork된 워커 프로세스에서:
    1. Django DB 연결을 강제 닫기 (부모의 libpq 소켓 상속 → GSS 크래시 방지)
    2. Neo4j 드라이버 참조를 안전하게 해제
    """
    # Django DB 연결 닫기 — 워커가 새 연결을 만들도록 강제
    from django import db
    db.connections.close_all()

    # Neo4j 드라이버 해제
    try:
        from services.rag_analysis.services.neo4j_driver import force_reset_after_fork
        from services.rag_analysis.services.neo4j_service import reset_neo4j_service
        force_reset_after_fork()
        reset_neo4j_service()
    except ImportError:
        pass


@worker_shutdown.connect
def close_neo4j_on_shutdown(**kwargs):
    """
    메인 워커 프로세스 종료 시 Neo4j 드라이버 정리.
    atexit 대신 사용 (fork 자식에 복사되지 않음).
    """
    try:
        from services.rag_analysis.services.neo4j_driver import close_neo4j_driver
        close_neo4j_driver()
    except ImportError:
        pass


# ============================================================
# beat_schedule — 주의: 이 dict는 런타임에 무시됨
# ============================================================
# config/settings.py의 `CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'`
# 설정 때문에 Celery Beat는 DB의 `django_celery_beat.PeriodicTask` 테이블을 진실의 소스로 사용한다.
# 아래 dict는 "원래 설계된 스케줄의 선언적 reference"로만 존재한다.
#
# 스케줄 추가/변경 방법:
#   1) Django admin → Periodic Tasks (/admin/django_celery_beat/periodictask/)
#   2) 또는 shell에서 PeriodicTask.objects.create(...)
#
# Drift 관리: config dict와 DB `PeriodicTask`가 어긋나면 dict의 태스크는 실행되지 않는다.
# 2026-04-24 복구: 누락 상태였던 두 태스크를 DB에 등록 완료 (수동 실행으로 동작 확인).
#   - chainsight-heat-score-daily (NY 07:00, 시드 선정 전)
#   - sec-seed-relations-to-chainsight (NY 12:00, 시드 선정 전)
# Drift 재발 방지 체크는 `python manage.py shell`에서
# `set(PeriodicTask.objects.values_list('name', flat=True)) vs config dict 키` diff로 수동 진행.
# ============================================================
app.conf.beat_schedule = {
    # ============================================================
    # Stocks 태스크
    # ============================================================

    # 실시간 주가 업데이트 (시장 개장 시간, 5분마다) — FMP Provider
    'update-realtime-prices': {
        'task': 'packages.shared.stocks.tasks.update_realtime_with_provider',
        'schedule': crontab(minute='*/5', hour='9-16', day_of_week='1-5'),
    },

    # 일일 종가 업데이트 (시장 마감 후) — FMP Provider
    'update-daily-prices': {
        'task': 'packages.shared.stocks.tasks.update_realtime_with_provider',
        'schedule': crontab(hour=17, minute=0, day_of_week='1-5'),
    },

    # 주간 데이터 집계 — DailyPrice → WeeklyPrice (API 호출 없음, 토요일 01:00)
    'aggregate-weekly-prices': {
        'task': 'packages.shared.stocks.tasks.aggregate_weekly_prices',
        'schedule': crontab(hour=1, minute=0, day_of_week=6),
        'options': {'expires': 3600}
    },

    # S&P 500 재무제표 순환 배치 (FMP, 101개/일, 5일에 전체 1회전, 평일 20:00)
    'sync-sp500-financials': {
        'task': 'packages.shared.stocks.tasks.sync_sp500_financials',
        'schedule': crontab(hour=20, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # 포트폴리오 가치 계산 (시장 개장 시간, 10분마다)
    'calculate-portfolio-values': {
        'task': 'packages.shared.users.tasks.calculate_portfolio_values',
        'schedule': crontab(minute='*/10', hour='9-16', day_of_week='1-5'),
    },

    # ============================================================
    # Macro (거시경제) 태스크
    # ============================================================

    # 거시경제 지표 업데이트 (4회/일, 평일 - FRED API)
    'update-economic-indicators': {
        'task': 'macro.tasks.update_economic_indicators',
        'schedule': crontab(minute=0, hour='6,12,18,22', day_of_week='1-5'),
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

    # Neo4j 헬스체크 (6시간마다, 이전 5분 → SIGSEGV 워커 소모 방지)
    'neo4j-health-check': {
        'task': 'services.rag_analysis.tasks.health_check_neo4j',
        'schedule': crontab(minute=0, hour='*/6'),
        'options': {'queue': 'neo4j'},
    },

    # Semantic Cache 태스크 — 제거됨 (미초기화 상태, 향후 폐기 예정)
    # cleanup-expired-semantic-cache, warm-semantic-cache, semantic-cache-stats

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

    # 일일 종목 뉴스 수집 (2회/일: 06:00 + 14:30 EST, 평일)
    'collect-daily-news-morning': {
        'task': 'news.tasks.collect_daily_news',
        'schedule': crontab(hour=6, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}
    },
    'collect-daily-news-afternoon': {
        'task': 'news.tasks.collect_daily_news',
        'schedule': crontab(hour=14, minute=30, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # 시장 뉴스 수집 (4회/일: 08:00, 12:00, 15:00, 18:00 EST)
    'collect-market-news-morning': {
        'task': 'news.tasks.collect_market_news',
        'schedule': crontab(hour=8, minute=0, day_of_week='1-5'),
        'options': {'expires': 600}
    },
    'collect-market-news-noon': {
        'task': 'news.tasks.collect_market_news',
        'schedule': crontab(hour=12, minute=0, day_of_week='1-5'),
        'options': {'expires': 600}
    },
    'collect-market-news-afternoon': {
        'task': 'news.tasks.collect_market_news',
        'schedule': crontab(hour=15, minute=0, day_of_week='1-5'),
        'options': {'expires': 600}
    },
    'collect-market-news-evening': {
        'task': 'news.tasks.collect_market_news',
        'schedule': crontab(hour=18, minute=0, day_of_week='1-5'),
        'options': {'expires': 600}
    },

    # 일일 감성 분석 집계 (매일 09:00 EST, 뉴스 수집 후)
    'aggregate-daily-sentiment': {
        'task': 'news.tasks.aggregate_daily_sentiment',
        'schedule': crontab(hour=9, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # 일일 뉴스 키워드 추출 (미국장 마감 후 — 16:45 EST = KST 06:45)
    # 16:30 EST에 analyze-news-deep-batch(hour='...,16,...', minute=30)와 Gemini 동시 호출 충돌
    # → Gemini 15 RPM 2배 초과 위험. 15분 분산하여 회피 (audit P0 #8, 2026-04-26)
    'extract-daily-news-keywords': {
        'task': 'news.tasks.extract_daily_news_keywords',
        'schedule': crontab(hour=16, minute=45),  # 16:45 EST (analyze-deep와 15분 간격)
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # 카테고리 뉴스 수집 - High (3회/일: 06:30 + 13:00 + 17:00 EST, 평일)
    'collect-category-news-high-morning': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=6, minute=30, day_of_week='1-5'),
        'kwargs': {'priority_filter': 'high'},
        'options': {'expires': 3600}
    },
    'collect-category-news-high-midday': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=13, minute=0, day_of_week='1-5'),
        'kwargs': {'priority_filter': 'high'},
        'options': {'expires': 3600}
    },
    'collect-category-news-high-evening': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=17, minute=0, day_of_week='1-5'),
        'kwargs': {'priority_filter': 'high'},
        'options': {'expires': 3600}
    },

    # 카테고리 뉴스 수집 - Medium (2회/일: 07:00 + 14:00 EST, 평일)
    'collect-category-news-medium-morning': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=7, minute=0, day_of_week='1-5'),
        'kwargs': {'priority_filter': 'medium'},
        'options': {'expires': 3600}
    },
    'collect-category-news-medium-afternoon': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=14, minute=0, day_of_week='1-5'),
        'kwargs': {'priority_filter': 'medium'},
        'options': {'expires': 3600}
    },

    # 카테고리 뉴스 수집 - Low (매일 1회: 07:30 EST, 평일)
    'collect-category-news-low': {
        'task': 'news.tasks.collect_category_news',
        'schedule': crontab(hour=7, minute=30, day_of_week='1-5'),
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
        'options': {'expires': 3600, 'queue': 'neo4j'}
    },

    # 만료된 뉴스 이벤트 관계 정리 (매일 04:00 EST)
    'cleanup-expired-news-relationships': {
        'task': 'news.tasks.cleanup_expired_news_relationships',
        'schedule': crontab(hour=4, minute=0),
        'options': {'expires': 3600, 'queue': 'neo4j'}
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

    # 파이프라인 알림 체크 (30분마다, 7개 트리거 감지)
    'check-pipeline-alerts': {
        'task': 'news.tasks.check_pipeline_alerts',
        'schedule': crontab(minute='*/30'),
        'options': {'expires': 1500}  # 25분 후 만료 (다음 실행 전)
    },

    # ============================================================
    # FMP 대량 뉴스 수집 태스크 (S&P 500 전체)
    # ============================================================

    # FMP S&P 500 News — orchestrator (하루 5회, 평일)
    'collect-sp500-news-fmp-0615': {
        'task': 'news.tasks.collect_sp500_news_fmp_orchestrator',
        'schedule': crontab(hour=6, minute=15, day_of_week='1-5'),
        'options': {'expires': 3600}
    },
    'collect-sp500-news-fmp-1015': {
        'task': 'news.tasks.collect_sp500_news_fmp_orchestrator',
        'schedule': crontab(hour=10, minute=15, day_of_week='1-5'),
        'options': {'expires': 3600}
    },
    'collect-sp500-news-fmp-1315': {
        'task': 'news.tasks.collect_sp500_news_fmp_orchestrator',
        'schedule': crontab(hour=13, minute=15, day_of_week='1-5'),
        'options': {'expires': 3600}
    },
    'collect-sp500-news-fmp-1515': {
        'task': 'news.tasks.collect_sp500_news_fmp_orchestrator',
        'schedule': crontab(hour=15, minute=15, day_of_week='1-5'),
        'options': {'expires': 3600}
    },
    'collect-sp500-news-fmp-1715': {
        'task': 'news.tasks.collect_sp500_news_fmp_orchestrator',
        'schedule': crontab(hour=17, minute=15, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # FMP Press Releases (1회/일)
    'collect-press-releases-fmp': {
        'task': 'news.tasks.collect_press_releases_fmp',
        'schedule': crontab(hour=7, minute=45, day_of_week='1-5'),
        'kwargs': {'max_symbols': 50},
        'options': {'expires': 3600}
    },

    # FMP General News (3회/일)
    'collect-general-news-fmp-morning': {
        'task': 'news.tasks.collect_general_news_fmp',
        'schedule': crontab(hour=6, minute=45, day_of_week='1-5'),
        'options': {'expires': 600}
    },
    'collect-general-news-fmp-noon': {
        'task': 'news.tasks.collect_general_news_fmp',
        'schedule': crontab(hour=12, minute=30, day_of_week='1-5'),
        'options': {'expires': 600}
    },
    'collect-general-news-fmp-evening': {
        'task': 'news.tasks.collect_general_news_fmp',
        'schedule': crontab(hour=17, minute=45, day_of_week='1-5'),
        'options': {'expires': 600}
    },

    # ============================================================
    # 데이터 보존 (아카이브) 태스크
    # ============================================================

    # 6개월 이상 기사 아카이브 (매월 1일 02:30 EST)
    'archive-old-articles': {
        'task': 'news.tasks.archive_old_articles',
        'schedule': crontab(hour=2, minute=30, day_of_month=1),
        'options': {'expires': 3600}
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
        'task': 'packages.shared.stocks.tasks.sync_sp500_constituents',
        'schedule': crontab(hour=2, minute=0, day_of_month=1),
        'options': {'expires': 86400}  # 24시간 후 만료
    },

    # S&P 500 EOD 가격 동기화 (매일 18:00 ET, Mon-Fri, 장 마감 + 2시간)
    'sync-sp500-eod-prices': {
        'task': 'packages.shared.stocks.tasks.sync_sp500_eod_prices',
        'schedule': crontab(hour=18, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}  # 1시간 후 만료
    },

    # DailyPrice → Stock.change_percent 일괄 계산 (EOD sync 직후, API 호출 없음)
    'update-sp500-change-percent': {
        'task': 'update-sp500-change-percent',
        'schedule': crontab(hour=18, minute=30, day_of_week='1-5'),
        'options': {'expires': 1800}
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
        'options': {'expires': 3600, 'queue': 'neo4j'}
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

    # ============================================================
    # EOD Dashboard Pipeline 태스크
    # ============================================================

    # EOD 시그널 파이프라인 (매일 18:30 ET, 장 마감 + 2.5시간, EOD 가격 동기화 이후)
    'run-eod-pipeline': {
        'task': 'packages.shared.stocks.tasks.run_eod_pipeline',
        'schedule': crontab(hour=18, minute=30, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # 시그널 정확도 소급 계산 (매일 19:00 ET, 파이프라인 이후)
    'backfill-signal-accuracy': {
        'task': 'packages.shared.stocks.tasks.backfill_signal_accuracy',
        'schedule': crontab(hour=19, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # S&P 500 한글 기업 개요 갱신 (매월 1일 03:00 EST)
    'refresh-korean-overviews-monthly': {
        'task': 'packages.shared.stocks.tasks.bulk_generate_korean_overviews',
        'schedule': crontab(hour=3, minute=0, day_of_month=1),
        'options': {'expires': 86400}
    },

    # ============================================================
    # Thesis Control EOD Pipeline (수학 모델 v2.3.2, Section 7)
    # ============================================================

    # 지표 데이터 수집 (매일 18:00 ET, 장 마감 후)
    'thesis-update-readings': {
        'task': 'thesis.tasks.eod_pipeline.update_indicator_readings',
        'schedule': crontab(hour=18, minute=0, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # 스코어 계산 (매일 18:15 ET, 데이터 수집 완료 후)
    'thesis-calculate-scores': {
        'task': 'thesis.tasks.eod_pipeline.calculate_scores',
        'schedule': crontab(hour=18, minute=15, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # 스냅샷 생성 + 알림 (매일 18:30 ET, 스코어 계산 완료 후)
    'thesis-create-snapshots': {
        'task': 'thesis.tasks.eod_pipeline.create_snapshots_and_alerts',
        'schedule': crontab(hour=18, minute=30, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # AI 요약 생성 (매일 18:35 ET, snapshot 직후 — audit P0 #15)
    'thesis-generate-summaries': {
        'task': 'thesis.tasks.summary.generate_thesis_summaries',
        'schedule': crontab(hour=18, minute=35, day_of_week='1-5'),
        'options': {'expires': 3600}
    },

    # ============================================================
    # Chain Sight — Tier A 프로파일 + 관계 파이프라인
    # ============================================================

    # Tier A 통합 프로파일 (매주 토요일 02:00 EST)
    # GrowthStage + CapitalDNA + SensitivityProfile + InsiderSignal
    'chainsight-all-profiles': {
        'task': 'apps.chain_sight.tasks.profile_tasks.calculate_all_profiles',
        'schedule': crontab(hour=2, minute=0, day_of_week=6),
        'options': {'expires': 7200}
    },

    # 뉴스 CoMention 추출 (매일 10:00 EST, 뉴스 분류 후)
    'chainsight-co-mentions': {
        'task': 'apps.chain_sight.tasks.relation_tasks.extract_co_mentions',
        'schedule': crontab(hour=10, minute=0),
        'kwargs': {'days_back': 7},
        'options': {'expires': 3600}
    },

    # PriceCoMovement 계산 (매주 토요일 03:00 EST, 프로파일 후)
    'chainsight-price-co-movement': {
        'task': 'apps.chain_sight.tasks.relation_tasks.calculate_price_co_movement',
        'schedule': crontab(hour=3, minute=0, day_of_week=6),
        'options': {'expires': 7200}
    },

    # RelationConfidence 갱신 (매일 11:00 EST, CoMention 후)
    'chainsight-relation-confidence': {
        'task': 'apps.chain_sight.tasks.relation_tasks.update_relation_confidence',
        'schedule': crontab(hour=11, minute=0),
        'options': {'expires': 3600}
    },

    # Stale 관계 감쇠 (매주 토요일 04:00 EST)
    'chainsight-stale-decay': {
        'task': 'apps.chain_sight.tasks.relation_tasks.check_stale_and_decay',
        'schedule': crontab(hour=4, minute=0, day_of_week=6),
        'options': {'expires': 600}
    },

    # ChainProfile 집계 (매주 토요일 04:30 EST, 프로파일+관계 완료 후)
    'chainsight-aggregate-profiles': {
        'task': 'apps.chain_sight.tasks.sync_tasks.aggregate_chain_profiles',
        'schedule': crontab(hour=4, minute=30, day_of_week=6),
        'options': {'expires': 3600}
    },

    # Neo4j 프로파일 동기화 (매일 12:00 EST, 관계 갱신 후)
    'chainsight-sync-profiles-neo4j': {
        'task': 'apps.chain_sight.tasks.sync_tasks.sync_profiles_to_neo4j',
        'schedule': crontab(hour=12, minute=0),
        'options': {'expires': 3600}
    },

    # Neo4j 관계 동기화 (매일 12:30 EST, 프로파일 동기화 후)
    'chainsight-sync-relations-neo4j': {
        'task': 'apps.chain_sight.tasks.sync_tasks.sync_relations_to_neo4j',
        'schedule': crontab(hour=12, minute=30),
        'options': {'expires': 3600}
    },

    # Heat Score 배치 (매일 07:00 UTC, 시드 선정 전)
    'chainsight-heat-score-daily': {
        'task': 'chainsight-heat-score-daily',
        'schedule': crontab(hour=7, minute=0),
        'options': {'expires': 1800}
    },

    # 시드 선정 (매일 13:00 UTC, 관계 동기화 후)
    'chainsight-seed-selection': {
        'task': 'chainsight-seed-selection',
        'schedule': crontab(hour=13, minute=0),
        'options': {'expires': 3600}
    },

    # Neo4j dirty 동기화 (매주 일요일 04:30 UTC)
    'chainsight-neo4j-dirty-sync': {
        'task': 'chainsight-neo4j-dirty-sync',
        'schedule': crontab(hour=4, minute=30, day_of_week=0),
        'options': {'expires': 3600, 'queue': 'neo4j'}
    },

    # ============================================================
    # Validation — 1차 검증 주간 배치
    # ============================================================

    # 주간 검증 배치 (매주 토요일 05:00 EST, Chain Sight 후)
    'validation-weekly-batch': {
        'task': 'services.validation.tasks.run_weekly_validation_batch',
        'schedule': crontab(hour=5, minute=0, day_of_week=6),
        'options': {'expires': 14400}
    },

    # ============================================================
    # SEC Pipeline — Neo4j 동기화 + 신규 filing 감지
    # ============================================================

    # SEC dirty evidence → Neo4j 동기화 (5분마다)
    'sec-sync-dirty-neo4j': {
        'task': 'services.sec_pipeline.tasks.sync_dirty_to_neo4j',
        'schedule': crontab(minute='*/5'),
        'options': {'expires': 240}
    },

    # SEC → Chain Sight RelationConfidence 연결 (매일 12:00 EST)
    'sec-seed-relations-to-chainsight': {
        'task': 'sec-seed-relations-to-chainsight',
        'schedule': crontab(hour=12, minute=0),
        'options': {'expires': 1800}
    },

    # SEC 신규 10-K filing 감지 (매월 1일 06:00 EST)
    'sec-check-new-filings': {
        'task': 'services.sec_pipeline.tasks.check_new_filings',
        'schedule': crontab(hour=6, minute=0, day_of_month=1),
        'options': {'expires': 3600}
    },

    # ============================================================
    # Celery 에러 모니터링
    # ============================================================

    # 일일 에러 요약 이메일 (매일 07:00 EST, 전날 에러 집계)
    'celery-error-digest': {
        'task': 'config.tasks.send_celery_error_digest',
        'schedule': crontab(hour=7, minute=0),
    },

    # TaskResult 정리 (매주 일요일 05:00 EST)
    # SUCCESS: 30일 보관, FAILURE: 90일 보관
    'cleanup-task-results': {
        'task': 'config.tasks.cleanup_old_task_results',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),
    },
}

# 테스트 태스크 (선택적)
@app.task(bind=True)
def debug_task(self):
    """Celery 동작 확인용 테스트 태스크"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'