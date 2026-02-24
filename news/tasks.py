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
