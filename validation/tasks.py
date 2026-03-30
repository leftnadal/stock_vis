"""
1차 검증 배치 파이프라인 Celery 태스크

Task 1: fetch_annual_financials — 재무제표 가용성 확인
Task 2: calculate_derived_metrics — 33개 지표 계산 + value_status 판정
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def fetch_annual_financials(self, symbols=None):
    """
    Task 1: 재무제표 가용성 확인.
    기존 DB에 데이터가 있으면 스킵, 없으면 리포트.
    """
    try:
        from validation.services.financial_fetcher import FinancialFetcher
        fetcher = FinancialFetcher()
        result = fetcher.check_and_fetch(symbols)
        logger.info(f"fetch_annual_financials: {result['total']} total, "
                     f"{result['ready']} ready, {len(result['missing'])} missing")
        return result
    except Exception as exc:
        logger.exception(f"fetch_annual_financials failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=1, soft_time_limit=7200, time_limit=7260)
def calculate_derived_metrics(self, symbols=None):
    """
    Task 2: 33개 지표 계산 + value_status 판정 + CompanyMetricLatest 갱신.
    종목별 독립 실행 (한 종목 실패해도 나머지 계속).
    """
    try:
        from validation.services.metric_calculator import MetricCalculator
        calculator = MetricCalculator()
        result = calculator.calculate_for_symbols(symbols)
        logger.info(f"calculate_derived_metrics: {result['total']} total, "
                     f"{result['success']} success, {result['errors']} errors")
        return result
    except Exception as exc:
        logger.exception(f"calculate_derived_metrics failed: {exc}")
        raise self.retry(exc=exc, countdown=300)
