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
        from services.news.tasks import extract_daily_news_keywords
        result = extract_daily_news_keywords.delay()

        # 특정 날짜
        result = extract_daily_news_keywords.delay(target_date='2025-01-01')
    """
    try:
        # 날짜 변환
        if target_date:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            date_obj = timezone.localdate()

        logger.info(f"Starting news keyword extraction for {date_obj}")

        # 키워드 추출 서비스 호출
        from services.news.services import NewsKeywordExtractor

        extractor = NewsKeywordExtractor(language="ko")
        keyword_obj = extractor.extract_daily_keywords(
            target_date=date_obj, force=force
        )

        result = {
            "date": str(keyword_obj.date),
            "status": keyword_obj.status,
            "keyword_count": keyword_obj.keyword_count,
            "total_news_count": keyword_obj.total_news_count,
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
    _start = time.time()
    _result = {"saved": 0, "skipped": 0, "errors": 0}
    _symbols_tried = 0
    try:
        from services.news.services.aggregator import NewsAggregatorService

        aggregator = NewsAggregatorService()
        total_saved = 0
        total_updated = 0
        errors = 0

        # 심볼 목록 결정
        if symbols is None:
            symbols = _get_mover_symbols(max_symbols=20)
        logger.info(f"collect_daily_news: {len(symbols)} symbols, days={days}")

        # 종목별 뉴스 수집
        for symbol in symbols:
            try:
                result = aggregator.fetch_and_save_company_news(
                    symbol=symbol,
                    days=days,
                    use_marketaux=True,  # Basic plan (2,500/day)
                )
                total_saved += result.get("saved", 0)
                total_updated += result.get("updated", 0)
            except Exception as e:
                logger.error(f"collect_daily_news: {symbol} failed: {e}")
                errors += 1

            # Finnhub rate limit (60 calls/min) 고려
            time.sleep(2)

        # 시장 전반 뉴스도 수집
        try:
            market_result = aggregator.fetch_and_save_market_news(
                category="general",
                use_marketaux=True,  # Basic plan (2,500/day)
            )
            total_saved += market_result.get("saved", 0)
            total_updated += market_result.get("updated", 0)
        except Exception as e:
            logger.error(f"collect_daily_news: market news failed: {e}")
            errors += 1

        result = {
            "symbols_processed": len(symbols),
            "total_saved": total_saved,
            "total_updated": total_updated,
            "errors": errors,
        }
        logger.info(f"collect_daily_news completed: {result}")
        _result = {"saved": total_saved, "skipped": total_updated, "errors": errors}
        _symbols_tried = len(symbols)
        return result

    except Exception as exc:
        _result["errors"] = _result.get("errors", 0) + 1
        logger.exception(f"collect_daily_news failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        _log_collection(
            "collect_daily_news",
            "finnhub_marketaux",
            _symbols_tried,
            _result,
            duration=time.time() - _start,
        )


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60 * 5,
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def collect_market_news(self, category="general"):
    """
    시장 전반 뉴스 수집 (Finnhub + Marketaux)

    매일 12:00, 18:00 EST에 실행.

    Args:
        category: 뉴스 카테고리 (general, forex, crypto, merger)

    Returns:
        dict: 수집 결과
    """
    _start = time.time()
    _result = {"saved": 0, "skipped": 0, "errors": 0}
    try:
        from services.news.services.aggregator import NewsAggregatorService

        aggregator = NewsAggregatorService()
        result = aggregator.fetch_and_save_market_news(
            category=category,
            use_marketaux=True,  # Basic plan (2,500/day)
        )
        logger.info(f"collect_market_news completed: {result}")
        _result = {
            "saved": result.get("saved", 0),
            "skipped": result.get("updated", 0),
            "errors": result.get("errors", 0),
        }
        return result

    except Exception as exc:
        _result["errors"] = _result.get("errors", 0) + 1
        logger.exception(f"collect_market_news failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        _log_collection(
            "collect_market_news",
            "finnhub_marketaux",
            0,
            _result,
            duration=time.time() - _start,
        )


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
        from django.db.models import Avg, Count, Max, Min

        from services.news.models import NewsEntity, SentimentHistory

        # 날짜 결정: 기본값은 전일 (전날 수집된 뉴스 집계)
        if target_date:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            date_obj = (timezone.now() - timedelta(days=1)).date()

        logger.info(f"aggregate_daily_sentiment: date={date_obj}")

        # 해당 날짜 뉴스의 종목별 감성 집계
        entity_stats = (
            NewsEntity.objects.filter(
                news__published_at__date=date_obj,
                sentiment_score__isnull=False,
            )
            .values("symbol")
            .annotate(
                avg_score=Avg("sentiment_score"),
                count=Count("id"),
                min_score=Min("sentiment_score"),
                max_score=Max("sentiment_score"),
            )
            .filter(count__gte=1)
        )

        created_count = 0
        updated_count = 0

        for stat in entity_stats:
            symbol = stat["symbol"]
            avg_score = stat["avg_score"]
            count = stat["count"]

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
                    "avg_sentiment": avg_score,
                    "news_count": count,
                    "positive_count": positive,
                    "negative_count": negative,
                    "neutral_count": neutral,
                },
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1

        result = {
            "date": str(date_obj),
            "symbols_aggregated": created_count + updated_count,
            "created": created_count,
            "updated": updated_count,
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
    _start = time.time()
    _result = {"saved": 0, "skipped": 0, "errors": 0}
    _symbols_tried = 0
    try:
        from services.news.models import NewsCollectionCategory
        from services.news.services.aggregator import NewsAggregatorService

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
            logger.info(
                f"collect_category_news: no categories found (id={category_id}, priority={priority_filter})"
            )
            return {
                "categories_processed": 0,
                "total_symbols": 0,
                "total_saved": 0,
                "total_updated": 0,
                "errors": 0,
            }

        # 카테고리별 심볼 해석 + 전체 dedup
        category_symbol_map = {}
        all_symbols = set()
        for cat in categories:
            symbols = cat.resolve_symbols()
            category_symbol_map[cat.id] = symbols
            all_symbols.update(symbols)

        unique_symbols = sorted(all_symbols)
        logger.info(
            f"collect_category_news: {categories.count()} categories, {len(unique_symbols)} unique symbols"
        )

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
                    use_marketaux=True,  # Basic plan (2,500/day)
                )
                saved = result.get("saved", 0)
                updated = result.get("updated", 0)
                symbol_results[symbol] = {"saved": saved, "updated": updated}
                total_saved += saved
                total_updated += updated
            except Exception as e:
                logger.error(f"collect_category_news: {symbol} failed: {e}")
                symbol_results[symbol] = {"saved": 0, "updated": 0, "error": str(e)}
                errors += 1

            time.sleep(2)  # Finnhub 60/min 준수

        # 카테고리별 통계 업데이트
        per_category = {}
        for cat in categories:
            cat_symbols = category_symbol_map.get(cat.id, [])
            cat_saved = sum(
                symbol_results.get(s, {}).get("saved", 0) for s in cat_symbols
            )
            cat.last_collected_at = timezone.now()
            cat.last_article_count = cat_saved
            cat.last_symbol_count = len(cat_symbols)
            cat.total_collections += 1
            cat.last_error = ""
            cat.save(
                update_fields=[
                    "last_collected_at",
                    "last_article_count",
                    "last_symbol_count",
                    "total_collections",
                    "last_error",
                ]
            )
            per_category[cat.name] = {
                "symbols": len(cat_symbols),
                "saved": cat_saved,
            }

        result = {
            "categories_processed": categories.count(),
            "total_symbols": len(unique_symbols),
            "total_saved": total_saved,
            "total_updated": total_updated,
            "errors": errors,
            "per_category": per_category,
        }
        logger.info(f"collect_category_news completed: {result}")
        _result = {"saved": total_saved, "skipped": total_updated, "errors": errors}
        _symbols_tried = len(unique_symbols)
        return result

    except Exception as exc:
        _result["errors"] = _result.get("errors", 0) + 1
        # 에러 시 카테고리에 기록
        if category_id:
            try:
                from services.news.models import NewsCollectionCategory

                cat = NewsCollectionCategory.objects.get(id=category_id)
                cat.last_error = str(exc)[:500]
                cat.save(update_fields=["last_error"])
            except Exception:
                pass
        logger.exception(f"collect_category_news failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        _log_collection(
            "collect_category_news",
            "finnhub_marketaux",
            _symbols_tried,
            _result,
            duration=time.time() - _start,
        )


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
    _start = time.time()
    _result = {"saved": 0, "skipped": 0, "errors": 0}
    try:
        from services.news.services.news_classifier import NewsClassifier

        classifier = NewsClassifier()
        result = classifier.classify_batch(article_ids=article_ids, hours=hours)

        logger.info(f"classify_news_batch completed: {result}")
        _result = {
            "saved": result.get("classified", 0),
            "skipped": result.get("skipped", 0),
            "errors": result.get("errors", 0),
        }
        return result

    except Exception as exc:
        _result["errors"] = _result.get("errors", 0) + 1
        logger.exception(f"classify_news_batch failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        _log_collection(
            "classify_news_batch", "internal", 0, _result, duration=time.time() - _start
        )


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
    _start = time.time()
    _result = {"saved": 0, "skipped": 0, "errors": 0}
    try:
        from services.news.services.news_deep_analyzer import NewsDeepAnalyzer

        analyzer = NewsDeepAnalyzer()
        result = analyzer.analyze_batch(max_articles=max_articles)

        logger.info(f"analyze_news_deep completed: {result}")
        _result = {
            "saved": result.get("analyzed", 0),
            "skipped": result.get("skipped", 0),
            "errors": result.get("errors", 0),
        }
        return result

    except Exception as exc:
        _result["errors"] = _result.get("errors", 0) + 1
        logger.exception(f"analyze_news_deep failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        _log_collection(
            "analyze_news_deep", "gemini", 0, _result, duration=time.time() - _start
        )


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
        from services.news.services.ml_label_collector import MLLabelCollector

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
    _start = time.time()
    _result = {"saved": 0, "skipped": 0, "errors": 0}
    try:
        from services.news.services.news_neo4j_sync import NewsNeo4jSyncService

        sync_service = NewsNeo4jSyncService()
        if not sync_service.is_available():
            logger.warning("sync_news_to_neo4j: Neo4j not available, skipping")
            return {"synced": 0, "skipped": 0, "errors": 0, "neo4j_unavailable": True}

        result = sync_service.sync_batch(max_articles=max_articles)
        logger.info(f"sync_news_to_neo4j completed: {result}")
        _result = {
            "saved": result.get("synced", 0),
            "skipped": result.get("skipped", 0),
            "errors": result.get("errors", 0),
        }
        return result

    except Exception as exc:
        _result["errors"] = _result.get("errors", 0) + 1
        logger.exception(f"sync_news_to_neo4j failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        _log_collection(
            "sync_news_to_neo4j", "neo4j", 0, _result, duration=time.time() - _start
        )


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
        from services.news.services.news_neo4j_sync import NewsNeo4jSyncService

        sync_service = NewsNeo4jSyncService()
        if not sync_service.is_available():
            logger.warning(
                "cleanup_expired_news_relationships: Neo4j not available, skipping"
            )
            return {
                "deleted_relationships": 0,
                "deleted_nodes": 0,
                "neo4j_unavailable": True,
            }

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
        from services.news.services.ml_weight_optimizer import MLWeightOptimizer

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
        from services.news.models import MLModelHistory
        from services.news.services.ml_weight_optimizer import MLWeightOptimizer

        # 최신 shadow 또는 deployed 모델 조회
        latest = (
            MLModelHistory.objects.filter(
                deployment_status__in=["shadow", "deployed"],
                smoothed_weights__isnull=False,
            )
            .order_by("-trained_at")
            .first()
        )

        if not latest:
            logger.info("generate_shadow_report: No shadow/deployed model found")
            return {"status": "no_model"}

        optimizer = MLWeightOptimizer()
        comparison = optimizer.generate_shadow_comparison(
            ml_weights=latest.smoothed_weights,
            days=days,
        )

        # 비교 결과를 모델에 업데이트
        latest.shadow_comparison = comparison
        latest.save(update_fields=["shadow_comparison"])

        result = {
            "model_version": latest.model_version,
            "comparison": comparison,
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
        from services.news.services.ml_production_manager import MLProductionManager

        manager = MLProductionManager()
        result = manager.check_auto_deploy()

        logger.info(
            f"check_auto_deploy: {result.get('action')} - {result.get('reason')}"
        )
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
        from services.news.services.ml_production_manager import MLProductionManager

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
        from services.news.services.ml_production_manager import MLProductionManager

        manager = MLProductionManager()
        result = manager.detect_consecutive_decline(weeks=3)

        if result.get("consecutive_decline"):
            logger.warning(f"ML PERFORMANCE ALERT: {result.get('alert_message')}")

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
        from services.news.services.ml_weight_optimizer import MLWeightOptimizer

        optimizer = MLWeightOptimizer()
        result = optimizer.run_lightgbm_pipeline()

        logger.info(f"train_lightgbm_model: {result.get('status')}")
        return result

    except Exception as exc:
        logger.exception(f"train_lightgbm_model failed: {exc}")
        raise self.retry(exc=exc)


# ============================================================
# FMP 대량 뉴스 수집 태스크 (Phase 1)
# ============================================================


@shared_task(
    bind=True,
    rate_limit="100/m",
    max_retries=2,
    soft_time_limit=600,
    time_limit=660,
)
def collect_sp500_news_fmp_batch(self, symbols: list):
    """
    배치 단위 FMP 뉴스 수집

    rate_limit='100/m'으로 Celery 레벨에서 FMP 300/min 한도 내 제어.

    Args:
        symbols: 수집할 심볼 리스트

    Returns:
        dict: {saved, updated, errors}
    """
    from services.news.services.aggregator import NewsAggregatorService
    from services.news.services.circuit_breaker import CircuitBreaker

    breaker = CircuitBreaker("fmp")
    if breaker.is_open():
        logger.warning("FMP Circuit OPEN, skipping batch")
        return {"skipped": True, "reason": "circuit_open"}

    aggregator = NewsAggregatorService()
    results = {"saved": 0, "updated": 0, "errors": 0, "symbols": len(symbols)}
    start_time = time.time()

    for symbol in symbols:
        try:
            result = aggregator.fetch_and_save_company_news_fmp(symbol)
            results["saved"] += result.get("saved", 0)
            results["updated"] += result.get("updated", 0)
            breaker.record_success()
        except Exception as e:
            logger.error(f"FMP news {symbol}: {e}")
            results["errors"] += 1
            breaker.record_failure()

    duration = time.time() - start_time
    _log_collection(
        "collect_sp500_news_fmp_batch", "fmp", len(symbols), results, duration
    )
    return results


@shared_task
def collect_sp500_news_fmp_orchestrator():
    """
    S&P 500 FMP 뉴스 수집 orchestrator

    chord로 6개 배치를 병렬 실행합니다.
    """
    from celery import chord

    from packages.shared.stocks.models import SP500Constituent

    sp500 = list(
        SP500Constituent.objects.filter(is_active=True)
        .order_by("symbol")
        .values_list("symbol", flat=True)
    )

    if not sp500:
        logger.warning("collect_sp500_news_fmp_orchestrator: no SP500 constituents")
        return {"error": "no_sp500_data"}

    batch_size = 84  # 503 / 6 ≈ 84
    batches = [sp500[i : i + batch_size] for i in range(0, len(sp500), batch_size)]

    logger.info(
        f"collect_sp500_news_fmp_orchestrator: {len(sp500)} symbols in {len(batches)} batches"
    )

    chord(collect_sp500_news_fmp_batch.s(batch) for batch in batches)(
        collect_sp500_news_fmp_done.si()
    )

    return {"dispatched": len(batches), "total_symbols": len(sp500)}


@shared_task
def collect_sp500_news_fmp_done():
    """chord 완료 콜백"""
    logger.info("collect_sp500_news_fmp: all batches completed")
    return {"status": "all_batches_done"}


@shared_task(
    bind=True,
    max_retries=2,
    soft_time_limit=600,
    time_limit=660,
)
def collect_press_releases_fmp(self, max_symbols=50):
    """
    FMP 보도자료 수집 (시가총액 상위 종목)

    1회/일 실행.

    Args:
        max_symbols: 수집할 최대 종목 수 (기본: 50)

    Returns:
        dict: {saved, updated, errors}
    """
    from services.news.services.aggregator import NewsAggregatorService
    from services.news.services.circuit_breaker import CircuitBreaker
    from packages.shared.stocks.models import SP500Constituent

    breaker = CircuitBreaker("fmp")
    if breaker.is_open():
        logger.warning("FMP Circuit OPEN, skipping press releases")
        return {"skipped": True, "reason": "circuit_open"}

    # 시가총액 상위 종목
    symbols = list(
        SP500Constituent.objects.filter(is_active=True)
        .order_by("-market_cap")
        .values_list("symbol", flat=True)[:max_symbols]
    )

    aggregator = NewsAggregatorService()
    results = {"saved": 0, "updated": 0, "errors": 0}
    start_time = time.time()

    for symbol in symbols:
        try:
            result = aggregator.fetch_and_save_press_releases(symbol)
            results["saved"] += result.get("saved", 0)
            results["updated"] += result.get("updated", 0)
            breaker.record_success()
        except Exception as e:
            logger.error(f"FMP press release {symbol}: {e}")
            results["errors"] += 1
            breaker.record_failure()

    duration = time.time() - start_time
    _log_collection(
        "collect_press_releases_fmp", "fmp", len(symbols), results, duration
    )
    logger.info(f"collect_press_releases_fmp completed: {results}")
    return results


@shared_task(
    bind=True,
    max_retries=2,
    soft_time_limit=300,
    time_limit=360,
)
def collect_general_news_fmp(self):
    """FMP 일반 시장 뉴스 수집"""
    from services.news.services.aggregator import NewsAggregatorService
    from services.news.services.circuit_breaker import CircuitBreaker

    breaker = CircuitBreaker("fmp")
    if breaker.is_open():
        logger.warning("FMP Circuit OPEN, skipping general news")
        return {"skipped": True, "reason": "circuit_open"}

    start_time = time.time()
    aggregator = NewsAggregatorService()

    try:
        result = aggregator.fetch_and_save_general_news_fmp(limit=50)
        breaker.record_success()
    except Exception as e:
        logger.error(f"FMP general news failed: {e}")
        breaker.record_failure()
        result = {"saved": 0, "error": str(e)}

    duration = time.time() - start_time
    _log_collection("collect_general_news_fmp", "fmp", 0, result, duration)
    logger.info(f"collect_general_news_fmp completed: {result}")
    return result


# ============================================================
# 데이터 보존 태스크 (Phase 4)
# ============================================================


@shared_task
def archive_old_articles():
    """6개월 이상 기사 → soft delete (is_archived=True)"""
    from services.news.models import NewsArticle

    cutoff = timezone.now() - timedelta(days=180)
    count = NewsArticle.objects.filter(
        published_at__lt=cutoff,
        is_archived=False,
    ).update(is_archived=True)

    logger.info(f"Archived {count} old articles")
    return {"archived": count}


# ============================================================
# Phase C: 파이프라인 알림 체크 태스크
# ============================================================


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def check_pipeline_alerts(self):
    """
    파이프라인 이상 징후 감지 + AlertLog 생성 (30분마다 실행)

    7개 트리거 체크:
    1. 태스크 연속 실패 (HIGH)
    2. ML F1 급락 (HIGH)
    3. 키워드 추출 실패 (MEDIUM)
    4. LLM 에러율 급등 (MEDIUM)
    5. Neo4j 연결 실패 (HIGH)
    6. 수집량 급감 (MEDIUM)
    7. 미분류 뉴스 누적 (LOW)

    Returns:
        dict: {alerts_created: int, checks_run: int}
    """
    import pytz
    from django.db.models import Sum

    from services.news.models import (
        AlertLog,
        DailyNewsKeyword,
        MLModelHistory,
        NewsArticle,
        NewsCollectionLog,
    )

    KST = pytz.timezone("Asia/Seoul")
    now = timezone.now()
    alerts_created = 0

    def _create_alert_if_new(trigger_type, severity, message, context=None):
        """같은 trigger_type + context(task_name)로 미해결 알림이 없을 때만 생성"""
        nonlocal alerts_created
        existing = AlertLog.objects.filter(
            trigger_type=trigger_type,
            is_resolved=False,
        )
        if context and "task_name" in context:
            existing = existing.filter(context__task_name=context["task_name"])
        if not existing.exists():
            AlertLog.objects.create(
                trigger_type=trigger_type,
                severity=severity,
                message=message,
                context=context,
            )
            alerts_created += 1
            logger.warning(
                f"check_pipeline_alerts: [{severity}] {trigger_type} — {message}"
            )

    # ── 1. 태스크 연속 실패 (HIGH) ──────────────────────────────
    task_names = list(
        NewsCollectionLog.objects.values_list("task_name", flat=True).distinct()
    )
    for task_name in task_names:
        recent_logs = list(
            NewsCollectionLog.objects.filter(task_name=task_name).order_by(
                "-executed_at"
            )[:3]
        )
        if len(recent_logs) == 3 and all(log.errors > 0 for log in recent_logs):
            _create_alert_if_new(
                trigger_type=AlertLog.TriggerType.CONSECUTIVE_TASK_FAILURE,
                severity=AlertLog.Severity.HIGH,
                message=f"{task_name} 태스크가 3회 연속 실패했습니다.",
                context={"task_name": task_name, "error_count": 3},
            )

    # ── 2. ML F1 급락 (HIGH) ──────────────────────────────────────
    try:
        recent_models = list(MLModelHistory.objects.order_by("-trained_at")[:2])
        if len(recent_models) == 2:
            latest, previous = recent_models[0], recent_models[1]
            f1_diff = latest.f1_score - previous.f1_score
            if f1_diff < -0.05:
                _create_alert_if_new(
                    trigger_type=AlertLog.TriggerType.ML_F1_DECLINE,
                    severity=AlertLog.Severity.HIGH,
                    message=(
                        f"ML F1 점수가 급락했습니다: "
                        f"{previous.f1_score:.3f} → {latest.f1_score:.3f} "
                        f"(변화: {f1_diff:.3f})"
                    ),
                    context={
                        "previous_version": previous.model_version,
                        "previous_f1": previous.f1_score,
                        "latest_version": latest.model_version,
                        "latest_f1": latest.f1_score,
                        "f1_change": round(f1_diff, 4),
                    },
                )
    except Exception as e:
        logger.error(f"check_pipeline_alerts: ML F1 체크 실패 — {e}")

    # ── 3. 키워드 추출 실패 (MEDIUM) ─────────────────────────────
    try:
        cutoff_24h = now - timedelta(hours=24)
        failed_keywords = DailyNewsKeyword.objects.filter(
            status="failed",
            created_at__gte=cutoff_24h,
        ).exists()
        if failed_keywords:
            _create_alert_if_new(
                trigger_type=AlertLog.TriggerType.KEYWORD_EXTRACTION_FAILURE,
                severity=AlertLog.Severity.MEDIUM,
                message="최근 24시간 내 키워드 추출 실패가 발생했습니다.",
                context={"window_hours": 24},
            )
    except Exception as e:
        logger.error(f"check_pipeline_alerts: 키워드 추출 체크 실패 — {e}")

    # ── 4. LLM 에러율 급등 (MEDIUM) ──────────────────────────────
    try:
        cutoff_24h = now - timedelta(hours=24)
        llm_logs = NewsCollectionLog.objects.filter(
            task_name="analyze_news_deep",
            executed_at__gte=cutoff_24h,
        ).aggregate(
            total_new=Sum("articles_new"),
            total_errors=Sum("errors"),
        )
        total_new = llm_logs["total_new"] or 0
        total_errors = llm_logs["total_errors"] or 0
        denominator = total_new + total_errors
        if denominator > 0:
            error_rate = total_errors / denominator
            if error_rate > 0.2:
                _create_alert_if_new(
                    trigger_type=AlertLog.TriggerType.LLM_ERROR_SPIKE,
                    severity=AlertLog.Severity.MEDIUM,
                    message=(
                        f"LLM 심층 분석 에러율이 {error_rate:.1%}로 임계값(20%)을 초과했습니다. "
                        f"(성공: {total_new}, 에러: {total_errors})"
                    ),
                    context={
                        "error_rate": round(error_rate, 4),
                        "total_new": total_new,
                        "total_errors": total_errors,
                        "window_hours": 24,
                    },
                )
    except Exception as e:
        logger.error(f"check_pipeline_alerts: LLM 에러율 체크 실패 — {e}")

    # ── 5. Neo4j 연결 실패 (HIGH) ─────────────────────────────────
    try:
        neo4j_log = (
            NewsCollectionLog.objects.filter(task_name="sync_news_to_neo4j")
            .order_by("-executed_at")
            .first()
        )

        if neo4j_log and neo4j_log.errors > 0:
            _create_alert_if_new(
                trigger_type=AlertLog.TriggerType.NEO4J_UNAVAILABLE,
                severity=AlertLog.Severity.HIGH,
                message=(
                    f"Neo4j 동기화 태스크에서 에러가 발생했습니다. "
                    f"마지막 실행: {neo4j_log.executed_at.isoformat()}, "
                    f"에러 수: {neo4j_log.errors}"
                ),
                context={
                    "task_name": "sync_news_to_neo4j",
                    "errors": neo4j_log.errors,
                    "executed_at": neo4j_log.executed_at.isoformat(),
                },
            )
    except Exception as e:
        logger.error(f"check_pipeline_alerts: Neo4j 체크 실패 — {e}")

    # ── 6. 수집량 급감 (MEDIUM) ───────────────────────────────────
    try:
        # 최근 5 평일의 일별 수집량 계산 (KST 기준)
        collection_task_names = [
            "collect_daily_news",
            "collect_market_news",
            "collect_category_news",
            "collect_sp500_news_fmp_batch",
            "collect_press_releases_fmp",
            "collect_general_news_fmp",
        ]

        # 오늘 KST 자정 계산
        now_kst = now.astimezone(KST)
        kst_today_midnight = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)

        # 최근 10일(평일 5일 확보용) 데이터 집계
        lookback_days = 10
        cutoff_lookback = (
            kst_today_midnight - timedelta(days=lookback_days)
        ).astimezone(pytz.utc)

        daily_aggregated = {}
        lookback_qs = (
            NewsCollectionLog.objects.filter(
                task_name__in=collection_task_names,
                executed_at__gte=cutoff_lookback,
            )
            .values("executed_at")
            .annotate(articles_sum=Sum("articles_new"))
        )
        for row in lookback_qs:
            # KST 날짜로 변환
            kst_date = row["executed_at"].astimezone(KST).date()
            # 평일만 (weekday 0=월 ~ 4=금)
            if kst_date.weekday() < 5:
                daily_aggregated[kst_date] = daily_aggregated.get(kst_date, 0) + (
                    row["articles_sum"] or 0
                )

        # 오늘 제외, 최근 평일 5일
        today_date = now_kst.date()
        past_weekdays = sorted(
            [d for d in daily_aggregated.keys() if d < today_date], reverse=True
        )[:5]

        if len(past_weekdays) >= 3:
            avg_collection = sum(daily_aggregated[d] for d in past_weekdays) / len(
                past_weekdays
            )

            # 오늘 수집량
            today_start_utc = kst_today_midnight.astimezone(pytz.utc)
            today_collected = (
                NewsCollectionLog.objects.filter(
                    task_name__in=collection_task_names,
                    executed_at__gte=today_start_utc,
                ).aggregate(total=Sum("articles_new"))["total"]
                or 0
            )

            if avg_collection > 0 and today_collected < avg_collection * 0.5:
                _create_alert_if_new(
                    trigger_type=AlertLog.TriggerType.COLLECTION_DROP,
                    severity=AlertLog.Severity.MEDIUM,
                    message=(
                        f"오늘 뉴스 수집량({today_collected}건)이 "
                        f"최근 평일 평균({avg_collection:.0f}건)의 50% 미만입니다."
                    ),
                    context={
                        "today_collected": today_collected,
                        "avg_collection": round(avg_collection, 1),
                        "past_weekdays_used": len(past_weekdays),
                        "today_date": str(today_date),
                    },
                )
    except Exception as e:
        logger.error(f"check_pipeline_alerts: 수집량 급감 체크 실패 — {e}")

    # ── 7. 미분류 뉴스 누적 (LOW) ─────────────────────────────────
    try:
        unclassified_count = NewsArticle.objects.filter(
            importance_score__isnull=True
        ).count()
        if unclassified_count > 500:
            _create_alert_if_new(
                trigger_type=AlertLog.TriggerType.UNCLASSIFIED_BACKLOG,
                severity=AlertLog.Severity.LOW,
                message=(
                    f"미분류 뉴스가 {unclassified_count}건 누적되었습니다. "
                    f"(임계값: 500건)"
                ),
                context={"unclassified_count": unclassified_count},
            )
    except Exception as e:
        logger.error(f"check_pipeline_alerts: 미분류 뉴스 체크 실패 — {e}")

    result = {
        "alerts_created": alerts_created,
        "checks_run": 7,
    }
    logger.info(f"check_pipeline_alerts completed: {result}")
    return result


# ============================================================
# 헬퍼 함수
# ============================================================


def _log_collection(task_name, provider, symbols_tried, results, duration=0):
    """뉴스 수집 로그 기록"""
    try:
        from services.news.models import NewsCollectionLog

        NewsCollectionLog.objects.create(
            task_name=task_name,
            provider=provider,
            symbols_tried=symbols_tried,
            articles_new=results.get("saved", 0),
            articles_dup=results.get("skipped", results.get("updated", 0)),
            errors=results.get("errors", 0),
            duration_sec=duration,
        )
    except Exception as e:
        logger.error(f"_log_collection failed: {e}")


def _get_tier1_symbols(max_symbols=25):
    """Tier 1 심볼 목록: Watchlist + Top Movers"""
    symbols = set()

    # Top Movers
    mover_symbols = _get_mover_symbols(max_symbols=15)
    symbols.update(mover_symbols)

    # Watchlist 인기 종목 (남은 슬롯 채움)
    if len(symbols) < max_symbols:
        try:
            from django.db.models import Count

            from packages.shared.users.models import WatchlistItem

            popular = list(
                WatchlistItem.objects.values("symbol")
                .annotate(count=Count("id"))
                .order_by("-count")
                .values_list("symbol", flat=True)[: max_symbols - len(symbols)]
            )
            symbols.update(popular)
        except Exception:
            pass

    return list(symbols)[:max_symbols]


def _get_mover_symbols(max_symbols=30):
    """MarketMover에서 최근 거래일의 심볼 추출"""
    try:
        from services.serverless.models import MarketMover

        latest_date = (
            MarketMover.objects.order_by("-date").values_list("date", flat=True).first()
        )
        if not latest_date:
            logger.warning("_get_mover_symbols: no MarketMover data")
            return []

        symbols = list(
            MarketMover.objects.filter(date=latest_date)
            .values_list("symbol", flat=True)
            .distinct()[:max_symbols]
        )
        logger.info(f"_get_mover_symbols: {len(symbols)} symbols from {latest_date}")
        return symbols

    except Exception as e:
        logger.error(f"_get_mover_symbols failed: {e}")
        return []
