"""
뉴스 키워드 추출 Celery 태스크 (Phase 2)

매일 오전 8시에 자동으로 뉴스 키워드를 추출합니다.
"""
import logging
from datetime import datetime

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
