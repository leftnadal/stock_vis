"""
뉴스 Celery 태스크

- 뉴스 수집 (Finnhub/Marketaux)
- 일일 감성 분석 집계
- 뉴스 키워드 추출 (Phase 2)
"""
import logging
import time
from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 10,  # 10분 후 재시도
    soft_time_limit=180,  # 3분 소프트 타임아웃
    time_limit=240,  # 4분 하드 타임아웃
)
def extract_daily_news_keywords(self, target_date: str = None, force: bool = False):
    """
    일일 뉴스 키워드 추출 태스크

    Args:
        target_date: 대상 날짜 (문자열 YYYY-MM-DD, 기본값: 오늘)
        force: 기존 키워드 덮어쓰기 여부

    Returns:
        dict: {'date': str, 'status': str, 'keyword_count': int}

    Usage:
        # 수동 실행
        from news.tasks import extract_daily_news_keywords
        result = extract_daily_news_keywords.delay()

        # 특정 날짜
        result = extract_daily_news_keywords.delay(target_date='2025-01-01')
    """
    try:
        # 날짜 변환
        if target_date:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            date_obj = timezone.now().date()

        logger.info(f"Starting news keyword extraction for {date_obj}")

        # 키워드 추출 서비스 호출
        from news.services import NewsKeywordExtractor

        extractor = NewsKeywordExtractor(language='ko')
        keyword_obj = extractor.extract_daily_keywords(
            target_date=date_obj,
            force=force
        )

        result = {
            'date': str(keyword_obj.date),
            'status': keyword_obj.status,
            'keyword_count': keyword_obj.keyword_count,
            'total_news_count': keyword_obj.total_news_count,
        }

        logger.info(f"Completed news keyword extraction: {result}")
        return result

    except Exception as exc:
        logger.exception(f"Failed to extract news keywords: {exc}")
        raise self.retry(exc=exc)


@shared_task
def manual_extract_keywords(date_str: str = None):
    """
    수동 키워드 추출 태스크 (관리자 도구용)

    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD)

    Returns:
        dict: 추출 결과
    """
    logger.info(f"Manual keyword extraction requested: {date_str or 'today'}")
    return extract_daily_news_keywords.delay(target_date=date_str, force=True)


# ============================================================
# 뉴스 수집 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 10,  # 10분 후 재시도
    soft_time_limit=1800,  # 30분 소프트 타임아웃
    time_limit=1860,  # 31분 하드 타임아웃
)
def collect_daily_news(self, symbols=None, days=1):
    """
    일일 종목 뉴스 수집 태스크

    MarketMover 상위 종목 + 시장 뉴스를 Finnhub/Marketaux에서 수집.
    매일 06:00 EST에 실행.

    Args:
        symbols: 수집할 심볼 리스트 (None이면 MarketMover에서 추출)
        days: 수집 기간 (일)

    Returns:
        dict: {'symbols_processed': N, 'total_saved': N, 'total_updated': N, 'errors': N}
    """
    try:
        from news.services.aggregator import NewsAggregatorService

        aggregator = NewsAggregatorService()
        total_saved = 0
        total_updated = 0
        errors = 0

        # 심볼 목록 결정
        if symbols is None:
            symbols = _get_mover_symbols(max_symbols=30)
        logger.info(f"collect_daily_news: {len(symbols)} symbols, days={days}")

        # 종목별 뉴스 수집
        for symbol in symbols:
            try:
                result = aggregator.fetch_and_save_company_news(
                    symbol=symbol,
                    days=days,
                    use_marketaux=False,  # rate limit 보존
                )
                total_saved += result.get('saved', 0)
                total_updated += result.get('updated', 0)
            except Exception as e:
                logger.error(f"collect_daily_news: {symbol} failed: {e}")
                errors += 1

            # Finnhub rate limit (60 calls/min) 고려
            time.sleep(2)

        # 시장 전반 뉴스도 수집
        try:
            market_result = aggregator.fetch_and_save_market_news(
                category='general',
                use_marketaux=False,
            )
            total_saved += market_result.get('saved', 0)
            total_updated += market_result.get('updated', 0)
        except Exception as e:
            logger.error(f"collect_daily_news: market news failed: {e}")
            errors += 1

        result = {
            'symbols_processed': len(symbols),
            'total_saved': total_saved,
            'total_updated': total_updated,
            'errors': errors,
        }
        logger.info(f"collect_daily_news completed: {result}")
        return result

    except Exception as exc:
        logger.exception(f"collect_daily_news failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 5,
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def collect_market_news(self, category='general'):
    """
    시장 전반 뉴스 수집 (Finnhub market news)

    매일 12:00, 18:00 EST에 실행.

    Args:
        category: 뉴스 카테고리 (general, forex, crypto, merger)

    Returns:
        dict: 수집 결과
    """
    try:
        from news.services.aggregator import NewsAggregatorService

        aggregator = NewsAggregatorService()
        result = aggregator.fetch_and_save_market_news(
            category=category,
            use_marketaux=False,
        )
        logger.info(f"collect_market_news completed: {result}")
        return result

    except Exception as exc:
        logger.exception(f"collect_market_news failed: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# 감성 분석 집계 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 5,
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def aggregate_daily_sentiment(self, target_date=None):
    """
    일일 감성 분석 집계 태스크

    뉴스 엔티티의 sentiment_score를 종목별로 집계하여 SentimentHistory에 저장.
    매일 09:00 EST에 실행 (뉴스 수집 후).

    Args:
        target_date: 대상 날짜 (YYYY-MM-DD 문자열, 기본값: 전일)

    Returns:
        dict: {'date': str, 'symbols_aggregated': N, 'created': N, 'updated': N}
    """
    try:
        from news.models import NewsEntity, SentimentHistory
        from django.db.models import Avg, Count, Min, Max

        # 날짜 결정: 기본값은 전일 (전날 수집된 뉴스 집계)
        if target_date:
            date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            date_obj = (timezone.now() - timedelta(days=1)).date()

        logger.info(f"aggregate_daily_sentiment: date={date_obj}")

        # 해당 날짜 뉴스의 종목별 감성 집계
        entity_stats = (
            NewsEntity.objects.filter(
                news__published_at__date=date_obj,
                sentiment_score__isnull=False,
            )
            .values('symbol')
            .annotate(
                avg_score=Avg('sentiment_score'),
                count=Count('id'),
                min_score=Min('sentiment_score'),
                max_score=Max('sentiment_score'),
            )
            .filter(count__gte=1)
        )

        created_count = 0
        updated_count = 0

        for stat in entity_stats:
            symbol = stat['symbol']
            avg_score = stat['avg_score']
            count = stat['count']

            # 긍정/부정/중립 분류
            positive = NewsEntity.objects.filter(
                news__published_at__date=date_obj,
                symbol=symbol,
                sentiment_score__gt=0.1,
            ).count()
            negative = NewsEntity.objects.filter(
                news__published_at__date=date_obj,
                symbol=symbol,
                sentiment_score__lt=-0.1,
            ).count()
            neutral = count - positive - negative

            _, was_created = SentimentHistory.objects.update_or_create(
                symbol=symbol,
                date=date_obj,
                defaults={
                    'avg_sentiment': avg_score,
                    'news_count': count,
                    'positive_count': positive,
                    'negative_count': negative,
                    'neutral_count': neutral,
                },
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1

        result = {
            'date': str(date_obj),
            'symbols_aggregated': created_count + updated_count,
            'created': created_count,
            'updated': updated_count,
        }
        logger.info(f"aggregate_daily_sentiment completed: {result}")
        return result

    except Exception as exc:
        logger.exception(f"aggregate_daily_sentiment failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 10,
    soft_time_limit=3600,
    time_limit=3660,
)
def collect_category_news(self, category_id=None, priority_filter=None):
    """
    카테고리 기반 뉴스 수집 태스크

    Args:
        category_id: 특정 카테고리 ID (None이면 priority_filter 기준 전체)
        priority_filter: 우선순위 필터 ('high', 'medium', 'low')

    Returns:
        dict: {categories_processed, total_symbols, total_saved, total_updated, errors, per_category}
    """
    try:
        from news.models import NewsCollectionCategory
        from news.services.aggregator import NewsAggregatorService

        aggregator = NewsAggregatorService()

        # 카테고리 조회
        if category_id:
            categories = NewsCollectionCategory.objects.filter(
                id=category_id, is_active=True
            )
        elif priority_filter:
            categories = NewsCollectionCategory.objects.filter(
                is_active=True, priority=priority_filter
            )
        else:
            categories = NewsCollectionCategory.objects.filter(is_active=True)

        if not categories.exists():
            logger.info(f"collect_category_news: no categories found (id={category_id}, priority={priority_filter})")
            return {'categories_processed': 0, 'total_symbols': 0, 'total_saved': 0, 'total_updated': 0, 'errors': 0}

        # 카테고리별 심볼 해석 + 전체 dedup
        category_symbol_map = {}
        all_symbols = set()
        for cat in categories:
            symbols = cat.resolve_symbols()
            category_symbol_map[cat.id] = symbols
            all_symbols.update(symbols)

        unique_symbols = sorted(all_symbols)
        logger.info(f"collect_category_news: {categories.count()} categories, {len(unique_symbols)} unique symbols")

        # 심볼별 1회만 수집
        symbol_results = {}
        total_saved = 0
        total_updated = 0
        errors = 0

        for symbol in unique_symbols:
            try:
                result = aggregator.fetch_and_save_company_news(
                    symbol=symbol,
                    days=1,
                    use_marketaux=False,
                )
                saved = result.get('saved', 0)
                updated = result.get('updated', 0)
                symbol_results[symbol] = {'saved': saved, 'updated': updated}
                total_saved += saved
                total_updated += updated
            except Exception as e:
                logger.error(f"collect_category_news: {symbol} failed: {e}")
                symbol_results[symbol] = {'saved': 0, 'updated': 0, 'error': str(e)}
                errors += 1

            time.sleep(2)  # Finnhub 60/min 준수

        # 카테고리별 통계 업데이트
        per_category = {}
        for cat in categories:
            cat_symbols = category_symbol_map.get(cat.id, [])
            cat_saved = sum(
                symbol_results.get(s, {}).get('saved', 0) for s in cat_symbols
            )
            cat.last_collected_at = timezone.now()
            cat.last_article_count = cat_saved
            cat.last_symbol_count = len(cat_symbols)
            cat.total_collections += 1
            cat.last_error = ''
            cat.save(update_fields=[
                'last_collected_at', 'last_article_count',
                'last_symbol_count', 'total_collections', 'last_error',
            ])
            per_category[cat.name] = {
                'symbols': len(cat_symbols),
                'saved': cat_saved,
            }

        result = {
            'categories_processed': categories.count(),
            'total_symbols': len(unique_symbols),
            'total_saved': total_saved,
            'total_updated': total_updated,
            'errors': errors,
            'per_category': per_category,
        }
        logger.info(f"collect_category_news completed: {result}")
        return result

    except Exception as exc:
        # 에러 시 카테고리에 기록
        if category_id:
            try:
                from news.models import NewsCollectionCategory
                cat = NewsCollectionCategory.objects.get(id=category_id)
                cat.last_error = str(exc)[:500]
                cat.save(update_fields=['last_error'])
            except Exception:
                pass
        logger.exception(f"collect_category_news failed: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# News Intelligence Pipeline v3 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 5,
    soft_time_limit=600,  # 10분 소프트 타임아웃
    time_limit=660,  # 11분 하드 타임아웃
)
def classify_news_batch(self, article_ids=None, hours=4):
    """
    뉴스 배치 분류 태스크 (수집 직후 체이닝)

    Engine A(종목 매칭) + Engine B(섹터 분류) + Engine C(5-factor 스코어링)
    적용하여 importance_score, rule_tickers, rule_sectors를 계산합니다.

    Args:
        article_ids: 분류할 뉴스 ID 리스트 (None이면 최근 N시간 미분류 뉴스)
        hours: article_ids가 None일 때 조회 범위 (기본: 4시간)

    Returns:
        dict: {classified: int, skipped: int, errors: int}
    """
    try:
        from news.services.news_classifier import NewsClassifier

        classifier = NewsClassifier()
        result = classifier.classify_batch(article_ids=article_ids, hours=hours)

        logger.info(f"classify_news_batch completed: {result}")
        return result

    except Exception as exc:
        logger.exception(f"classify_news_batch failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 10,
    soft_time_limit=1800,  # 30분 소프트 타임아웃
    time_limit=1860,  # 31분 하드 타임아웃
)
def analyze_news_deep(self, max_articles=50):
    """
    뉴스 LLM 심층 분석 배치 태스크

    당일 누적 기준 상위 15% 뉴스 중 미분석 건을 Gemini 2.5 Flash로
    심층 분석합니다 (Tier A/B/C 프롬프트 분기).

    매 2시간 실행, 4초 간격으로 RPM 준수.

    Args:
        max_articles: 배치당 최대 분석 건수 (기본: 50)

    Returns:
        dict: {analyzed: int, errors: int, skipped: int}
    """
    try:
        from news.services.news_deep_analyzer import NewsDeepAnalyzer

        analyzer = NewsDeepAnalyzer()
        result = analyzer.analyze_batch(max_articles=max_articles)

        logger.info(f"analyze_news_deep completed: {result}")
        return result

    except Exception as exc:
        logger.exception(f"analyze_news_deep failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 10,
    soft_time_limit=600,  # 10분 소프트 타임아웃
    time_limit=660,  # 11분 하드 타임아웃
)
def collect_ml_labels(self, lookback_days=2):
    """
    ML Label 수집 태스크

    DailyPrice 기반 +24h 변동폭 계산. Company News 우선.
    매일 19:00 EST 실행 (장 마감 + 1시간).

    Args:
        lookback_days: 조회 범위 일수 (기본: 2일)

    Returns:
        dict: {processed: int, labeled: int, skipped: int, errors: int}
    """
    try:
        from news.services.ml_label_collector import MLLabelCollector

        collector = MLLabelCollector()
        result = collector.collect_labels(lookback_days=lookback_days)

        logger.info(f"collect_ml_labels completed: {result}")
        return result

    except Exception as exc:
        logger.exception(f"collect_ml_labels failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 5,
    soft_time_limit=600,  # 10분 소프트 타임아웃
    time_limit=660,  # 11분 하드 타임아웃
)
def sync_news_to_neo4j(self, max_articles=100):
    """
    뉴스 LLM 분석 결과를 Neo4j에 동기화하는 태스크

    llm_analyzed=True인 기사 중 Neo4j에 미동기화된 것을 처리합니다.
    LLM 분석 완료 후 또는 스케줄로 실행.

    Args:
        max_articles: 배치당 최대 동기화 건수 (기본: 100)

    Returns:
        dict: {synced: int, skipped: int, errors: int, total_nodes: int, total_rels: int}
    """
    try:
        from news.services.news_neo4j_sync import NewsNeo4jSyncService

        sync_service = NewsNeo4jSyncService()
        if not sync_service.is_available():
            logger.warning("sync_news_to_neo4j: Neo4j not available, skipping")
            return {'synced': 0, 'skipped': 0, 'errors': 0, 'neo4j_unavailable': True}

        result = sync_service.sync_batch(max_articles=max_articles)
        logger.info(f"sync_news_to_neo4j completed: {result}")
        return result

    except Exception as exc:
        logger.exception(f"sync_news_to_neo4j failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=60 * 5,
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def cleanup_expired_news_relationships(self):
    """
    만료된 뉴스 이벤트 관계 정리 태스크

    TTL 기반으로 만료된 Neo4j 관계를 삭제하고,
    고립된 NewsEvent 노드를 정리합니다.

    매일 04:00 EST에 실행.

    Returns:
        dict: {deleted_relationships: int, deleted_nodes: int}
    """
    try:
        from news.services.news_neo4j_sync import NewsNeo4jSyncService

        sync_service = NewsNeo4jSyncService()
        if not sync_service.is_available():
            logger.warning("cleanup_expired_news_relationships: Neo4j not available, skipping")
            return {'deleted_relationships': 0, 'deleted_nodes': 0, 'neo4j_unavailable': True}

        result = sync_service.cleanup_expired_relationships()
        logger.info(f"cleanup_expired_news_relationships completed: {result}")
        return result

    except Exception as exc:
        logger.exception(f"cleanup_expired_news_relationships failed: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# News Intelligence Pipeline v3 - Phase 4: ML 학습 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=60 * 10,
    soft_time_limit=1800,  # 30분 소프트 타임아웃
    time_limit=1860,  # 31분 하드 타임아웃
)
def train_importance_model(self):
    """
    ML 가중치 학습 파이프라인 (주간)

    Logistic Regression으로 Engine C의 β₁~β₅ 가중치를 최적화합니다.
    - Company News 데이터만 사용
    - Time-Series Split 검증
    - Safety Gate 3단계 통과 시 Shadow Mode로 저장
    - Weight Smoothing (0.7 × new + 0.3 × prev) 적용

    매주 일요일 03:00 EST 실행.

    Returns:
        dict: {status, model_version, metrics, safety_gate, weights}
    """
    try:
        from news.services.ml_weight_optimizer import MLWeightOptimizer

        optimizer = MLWeightOptimizer()
        result = optimizer.run_training_pipeline()

        logger.info(f"train_importance_model completed: {result.get('status')}")
        return result

    except Exception as exc:
        logger.exception(f"train_importance_model failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=60 * 5,
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def generate_shadow_report(self, days=7):
    """
    Shadow Mode 비교 리포트 생성

    현재 Shadow/Deployed 모델의 ML 가중치와 수동 가중치를
    비교하여 선별 결과 차이를 분석합니다.

    매주 일요일 03:30 EST 실행 (학습 직후).

    Args:
        days: 비교 기간 (기본: 7일)

    Returns:
        dict: {model_version, comparison}
    """
    try:
        from news.services.ml_weight_optimizer import MLWeightOptimizer
        from news.models import MLModelHistory

        # 최신 shadow 또는 deployed 모델 조회
        latest = MLModelHistory.objects.filter(
            deployment_status__in=['shadow', 'deployed'],
            smoothed_weights__isnull=False,
        ).order_by('-trained_at').first()

        if not latest:
            logger.info("generate_shadow_report: No shadow/deployed model found")
            return {'status': 'no_model'}

        optimizer = MLWeightOptimizer()
        comparison = optimizer.generate_shadow_comparison(
            ml_weights=latest.smoothed_weights,
            days=days,
        )

        # 비교 결과를 모델에 업데이트
        latest.shadow_comparison = comparison
        latest.save(update_fields=['shadow_comparison'])

        result = {
            'model_version': latest.model_version,
            'comparison': comparison,
        }
        logger.info(f"generate_shadow_report completed: {result}")
        return result

    except Exception as exc:
        logger.exception(f"generate_shadow_report failed: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# News Intelligence Pipeline v3 - Phase 5: ML Production 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=60 * 5,
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def check_auto_deploy(self):
    """
    ML 모델 자동 배포 체크

    4주 연속 Safety Gate 통과 + agreement_rate >= 0.70이면
    최신 Shadow 모델을 자동 배포합니다.

    매주 일요일 04:00 EST 실행 (학습 + shadow 리포트 이후).

    Returns:
        dict: {action, reason, model_version?}
    """
    try:
        from news.services.ml_production_manager import MLProductionManager

        manager = MLProductionManager()
        result = manager.check_auto_deploy()

        logger.info(f"check_auto_deploy: {result.get('action')} - {result.get('reason')}")
        return result

    except Exception as exc:
        logger.exception(f"check_auto_deploy failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=60 * 5,
    soft_time_limit=600,  # 10분 소프트 타임아웃
    time_limit=660,  # 11분 하드 타임아웃
)
def generate_weekly_ml_report(self):
    """
    주간 ML 성능 리포트 생성

    모델 상태, 성능 추이, LLM 정확도, 데이터 통계를 종합합니다.

    매주 일요일 04:15 EST 실행 (auto deploy 이후).

    Returns:
        dict: {period, model_status, performance_trend, llm_accuracy, ...}
    """
    try:
        from news.services.ml_production_manager import MLProductionManager

        manager = MLProductionManager()
        report = manager.generate_weekly_report()

        logger.info(f"generate_weekly_ml_report completed")
        return report

    except Exception as exc:
        logger.exception(f"generate_weekly_ml_report failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=60 * 5,
    soft_time_limit=300,  # 5분
    time_limit=360,  # 6분
)
def monitor_ml_performance(self):
    """
    ML 모델 연속 하락 감지 태스크

    3주 연속 F1 하락 시 Rolling Window 축소 권고 +
    Feature Importance 리포트 생성 + 관리자 알림 로깅.

    매주 일요일 04:20 EST 실행 (weekly report 직후).
    """
    try:
        from news.services.ml_production_manager import MLProductionManager

        manager = MLProductionManager()
        result = manager.detect_consecutive_decline(weeks=3)

        if result.get('consecutive_decline'):
            logger.warning(
                f"ML PERFORMANCE ALERT: {result.get('alert_message')}"
            )

        logger.info(f"monitor_ml_performance: {result.get('action_taken', 'none')}")
        return result

    except Exception as exc:
        logger.exception(f"monitor_ml_performance failed: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# News Intelligence Pipeline v3 - Phase 6: LightGBM 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=60 * 10,
    soft_time_limit=1800,  # 30분 소프트 타임아웃
    time_limit=1860,  # 31분 하드 타임아웃
)
def train_lightgbm_model(self):
    """
    LightGBM 학습 파이프라인 (Phase 6)

    전환 조건 확인 후 LightGBM 모델 학습 + A/B 테스트.
    조건 미충족 시 skip합니다.

    매주 일요일 04:30 EST 실행 (주간 리포트 이후).

    Returns:
        dict: {status, model_version?, metrics?, ab_test?}
    """
    try:
        from news.services.ml_weight_optimizer import MLWeightOptimizer

        optimizer = MLWeightOptimizer()
        result = optimizer.run_lightgbm_pipeline()

        logger.info(f"train_lightgbm_model: {result.get('status')}")
        return result

    except Exception as exc:
        logger.exception(f"train_lightgbm_model failed: {exc}")
        raise self.retry(exc=exc)


def _get_mover_symbols(max_symbols=30):
    """MarketMover에서 최근 거래일의 심볼 추출"""
    try:
        from serverless.models import MarketMover

        latest_date = MarketMover.objects.order_by('-date').values_list(
            'date', flat=True
        ).first()
        if not latest_date:
            logger.warning("_get_mover_symbols: no MarketMover data")
            return []

        symbols = list(
            MarketMover.objects.filter(date=latest_date)
            .values_list('symbol', flat=True)
            .distinct()[:max_symbols]
        )
        logger.info(f"_get_mover_symbols: {len(symbols)} symbols from {latest_date}")
        return symbols

    except Exception as e:
        logger.error(f"_get_mover_symbols failed: {e}")
        return []
