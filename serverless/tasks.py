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
