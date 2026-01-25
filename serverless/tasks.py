"""
Market Movers Celery 태스크

매일 오전 7:30에 자동으로 Market Movers 데이터를 동기화합니다.
"""
import logging
from celery import shared_task
from django.utils import timezone

from serverless.services.data_sync import MarketMoversSync
from serverless.services.fmp_client import FMPAPIError


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 5,  # 5분 후 재시도
)
def sync_daily_market_movers(self, target_date=None):
    """
    일일 Market Movers 동기화 태스크

    Args:
        target_date: 대상 날짜 (문자열, 기본값: 오늘)

    Returns:
        dict: {'gainers': int, 'losers': int, 'actives': int, 'errors': int}

    Usage:
        # 수동 실행
        from serverless.tasks import sync_daily_market_movers
        result = sync_daily_market_movers.delay()

        # 특정 날짜
        result = sync_daily_market_movers.delay(target_date='2025-01-01')
    """
    try:
        # 날짜 변환
        if target_date:
            from datetime import datetime
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()

        logger.info(f"🚀 Celery Task 시작: sync_daily_market_movers (date={target_date})")

        # 동기화 실행
        sync = MarketMoversSync()
        result = sync.sync_daily_movers(target_date=target_date)

        logger.info(f"✅ Celery Task 완료: {result}")
        return result

    except FMPAPIError as exc:
        # FMP API 에러 - 재시도
        logger.error(f"❌ FMP API 에러: {exc}")
        raise self.retry(exc=exc)

    except Exception as exc:
        # 기타 에러
        logger.exception(f"❌ 예상치 못한 에러: {exc}")
        raise


@shared_task
def manual_sync_market_movers(date_str: str = None):
    """
    수동 동기화 태스크 (관리자 도구용)

    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD)

    Returns:
        dict: 동기화 결과
    """
    logger.info(f"📋 수동 동기화 요청: {date_str or 'today'}")
    return sync_daily_market_movers.delay(target_date=date_str)


# ============================================================
# Market Movers 키워드 생성 태스크
# ============================================================

@shared_task(
    bind=True,
    max_retries=2,
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def collect_keyword_data(self, movers_date: str, mover_type: str = 'gainers'):
    """
    키워드 생성용 데이터 수집 (병렬)

    Args:
        movers_date: Market Movers 날짜 (YYYY-MM-DD)
        mover_type: 'gainers', 'losers', 'actives'

    Returns:
        {
            'date': '2026-01-07',
            'mover_type': 'gainers',
            'successful': ['AAPL', 'MSFT', ...],
            'failed': [('GOOGL', 'error'), ...],
            'cache_hits': 5,
            'api_calls': 15,
            'duration_ms': 240000
        }
    """
    from datetime import datetime
    from serverless.models import MarketMover
    from serverless.services.keyword_data_collector import KeywordDataCollector

    try:
        # 날짜 변환
        target_date = datetime.strptime(movers_date, '%Y-%m-%d').date()

        logger.info("keyword_data_collection_task", extra={
            "status": "started",
            "date": movers_date,
            "mover_type": mover_type,
        })

        # MarketMover에서 종목 리스트 조회
        movers = MarketMover.objects.filter(
            date=target_date,
            mover_type=mover_type
        ).order_by('rank')[:20]  # TOP 20

        symbols = [m.symbol for m in movers]

        if not symbols:
            logger.warning(f"No movers found for {movers_date} ({mover_type})")
            return {
                'date': movers_date,
                'mover_type': mover_type,
                'successful': [],
                'failed': [],
                'cache_hits': 0,
                'api_calls': 0,
                'duration_ms': 0,
            }

        # 데이터 수집 (병렬)
        collector = KeywordDataCollector()
        result = collector.collect_batch(symbols, target_date)

        logger.info("keyword_data_collection_task", extra={
            "status": "completed",
            "successful": len(result['successful']),
            "failed": len(result['failed']),
            "cache_hits": result['cache_hits'],
            "api_calls": result['api_calls'],
            "duration_ms": result['duration_ms'],
        })

        return {
            'date': movers_date,
            'mover_type': mover_type,
            'successful': result['successful'],
            'failed': result['failed'],
            'cache_hits': result['cache_hits'],
            'api_calls': result['api_calls'],
            'duration_ms': result['duration_ms'],
        }

    except Exception as exc:
        logger.exception(f"❌ 키워드 데이터 수집 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
)
def generate_keywords_batch(self, collection_result: dict):
    """
    키워드 배치 생성 (LLM 호출)

    Args:
        collection_result: collect_keyword_data의 결과

    Returns:
        {
            'date': '2026-01-07',
            'keywords': {
                'AAPL': [...],
                'MSFT': [...]
            },
            'llm_tokens': {
                'input': 7200,
                'output': 6000,
                'cost_usd': 0.009
            }
        }
    """
    from serverless.services.keyword_service import KeywordGenerationService
    from datetime import datetime

    try:
        date_str = collection_result['date']
        mover_type = collection_result.get('mover_type', 'gainers')
        successful_symbols = collection_result['successful']

        if not successful_symbols:
            logger.warning("No successful symbols to generate keywords")
            return {
                'date': date_str,
                'keywords': {},
                'llm_tokens': {'input': 0, 'output': 0, 'cost_usd': 0.0}
            }

        logger.info("keyword_generation_task", extra={
            "status": "started",
            "date": date_str,
            "num_stocks": len(successful_symbols),
        })

        # 날짜 변환
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # LLM 키워드 생성 (배치)
        # Note: 현재는 기본 정보만 사용, 향후 contexts 활용 예정
        service = KeywordGenerationService()
        keywords_result = service.batch_generate(
            date=target_date,
            mover_type=mover_type,
            limit=len(successful_symbols)
        )

        # batch_generate는 {'success', 'failed', 'skipped'} 반환하고 직접 DB 저장
        logger.info("keyword_generation_task", extra={
            "status": "completed",
            "success": keywords_result['success'],
            "failed": keywords_result['failed'],
            "skipped": keywords_result['skipped'],
        })

        return {
            'date': date_str,
            'mover_type': mover_type,
            'success': keywords_result['success'],
            'failed': keywords_result['failed'],
            'skipped': keywords_result['skipped'],
        }

    except Exception as exc:
        logger.exception(f"❌ 키워드 생성 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task
def save_keywords(generation_result: dict):
    """
    키워드 생성 완료 처리

    Note: batch_generate가 이미 DB에 저장하므로,
          이 태스크는 Redis 캐시 정리만 수행합니다.

    Args:
        generation_result: generate_keywords_batch의 결과

    Returns:
        {
            'date': '2026-01-07',
            'mover_type': 'gainers',
            'success': 18,
            'failed': 2,
            'skipped': 0
        }
    """
    from serverless.services.keyword_data_collector import KeywordDataCollector
    from serverless.models import StockKeyword

    try:
        date_str = generation_result['date']
        mover_type = generation_result.get('mover_type', 'gainers')

        logger.info("keyword_save_task", extra={
            "status": "started",
            "date": date_str,
            "mover_type": mover_type,
        })

        # Redis 캐시 삭제 (생성 완료된 종목)
        from datetime import datetime
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        completed_symbols = StockKeyword.objects.filter(
            date=target_date,
            status='completed'
        ).values_list('symbol', flat=True)

        collector = KeywordDataCollector()
        for symbol in completed_symbols:
            collector.delete_cached_context(date_str, symbol)

        logger.info("keyword_save_task", extra={
            "status": "completed",
            "cache_cleared": len(completed_symbols),
        })

        return {
            'date': date_str,
            'mover_type': mover_type,
            'success': generation_result.get('success', 0),
            'failed': generation_result.get('failed', 0),
            'skipped': generation_result.get('skipped', 0),
            'cache_cleared': len(completed_symbols),
        }

    except Exception as exc:
        logger.exception(f"❌ 키워드 저장 완료 처리 실패: {exc}")
        raise


@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=600,  # 10분 소프트 타임아웃
    time_limit=660,  # 11분 하드 타임아웃
)
def generate_screener_keywords_task(self, stocks: list):
    """
    스크리너 종목들의 키워드 생성

    Args:
        stocks: 종목 리스트
            [
                {"symbol": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "change_percent": 2.5},
                ...
            ]

    Returns:
        {
            'success': 18,
            'failed': 2,
            'results': {
                'AAPL': ['키워드1', '키워드2', '키워드3'],
                ...
            }
        }
    """
    from serverless.services.keyword_service import KeywordGenerationService
    from serverless.models import StockKeyword
    from datetime import timedelta

    try:
        logger.info(f"🚀 스크리너 키워드 생성 시작: {len(stocks)}개 종목")

        service = KeywordGenerationService()
        today = timezone.now().date()

        results = {'success': 0, 'failed': 0, 'results': {}}

        for stock in stocks:
            symbol = stock.get('symbol', '').upper()
            company_name = stock.get('company_name', symbol)
            sector = stock.get('sector')
            industry = stock.get('industry')
            change_percent = stock.get('change_percent', 0)

            if not symbol:
                continue

            # 이미 생성된 키워드 확인
            existing = StockKeyword.objects.filter(
                symbol=symbol,
                date=today,
                status='completed'
            ).first()

            if existing:
                results['results'][symbol] = existing.keywords
                results['success'] += 1
                logger.debug(f"  ⏭️ {symbol}: 이미 생성됨 (캐시 사용)")
                continue

            # 키워드 생성 (mover_type='screener'로 구분)
            result = service.generate_keyword(
                symbol=symbol,
                company_name=company_name,
                date=today,
                mover_type='screener',  # 스크리너 전용 타입
                change_percent=float(change_percent) if change_percent else 0,
                sector=sector,
                industry=industry
            )

            # DB 저장
            StockKeyword.objects.update_or_create(
                symbol=symbol,
                date=today,
                defaults={
                    'company_name': company_name,
                    'keywords': result['keywords'],
                    'status': result['status'],
                    'error_message': result['error_message'],
                    'llm_model': 'gemini-2.5-flash',
                    'generation_time_ms': result['metadata'].get('generation_time_ms'),
                    'prompt_tokens': result['metadata'].get('prompt_tokens'),
                    'completion_tokens': result['metadata'].get('completion_tokens'),
                    'expires_at': timezone.now() + timedelta(days=7),
                }
            )

            if result['status'] == 'completed':
                logger.info(f"  ✅ {symbol}: {result['keywords']}")
                results['results'][symbol] = result['keywords']
                results['success'] += 1
            else:
                logger.warning(f"  ⚠️ {symbol}: {result['error_message']}")
                results['results'][symbol] = result['keywords']  # fallback 키워드
                results['failed'] += 1

        logger.info(f"✅ 스크리너 키워드 생성 완료: success={results['success']}, failed={results['failed']}")

        return results

    except Exception as exc:
        logger.exception(f"❌ 스크리너 키워드 생성 실패: {exc}")
        raise self.retry(exc=exc)


@shared_task
def keyword_generation_pipeline(movers_date: str = None, mover_type: str = 'gainers'):
    """
    키워드 생성 파이프라인 (체이닝)

    Args:
        movers_date: 날짜 문자열 (YYYY-MM-DD, 기본값: 오늘)
        mover_type: 'gainers', 'losers', 'actives'

    Usage:
        from serverless.tasks import keyword_generation_pipeline
        result = keyword_generation_pipeline.delay()
    """
    from celery import chain

    if not movers_date:
        movers_date = timezone.now().strftime('%Y-%m-%d')

    logger.info(f"🚀 키워드 생성 파이프라인 시작: {movers_date} ({mover_type})")

    # 태스크 체인
    pipeline = chain(
        collect_keyword_data.si(movers_date, mover_type),
        generate_keywords_batch.s(),
        save_keywords.s(),
    )

    return pipeline.apply_async()
