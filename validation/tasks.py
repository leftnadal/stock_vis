"""
1차 검증 배치 파이프라인 Celery 태스크

Task 1: fetch_annual_financials — 재무제표 가용성 확인
Task 2: calculate_derived_metrics — 33개 지표 계산 + value_status 판정
Task 3: calculate_benchmarks — Peer 선정 + Benchmark 계산
Task 3.5: calculate_relative_metrics — rev_growth_vs_industry 계산
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


@shared_task(bind=True, max_retries=1, soft_time_limit=7200, time_limit=7260)
def calculate_benchmarks(self, symbols=None):
    """
    Task 3: Peer 선정 + Benchmark 계산 (peer/industry).
    종목별 peer 선정 → median/p25/p75 계산 → delta 저장 → peer_list_cache 갱신.
    """
    try:
        from validation.services.benchmark_calculator import BenchmarkCalculator
        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbols(symbols)
        logger.info(f"calculate_benchmarks: {result['total']} total, "
                     f"{result['success']} success, {result['errors']} errors")
        return result
    except Exception as exc:
        logger.exception(f"calculate_benchmarks failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=1, soft_time_limit=1800, time_limit=1860)
def calculate_relative_metrics(self, symbols=None):
    """
    Task 3.5: rev_growth_vs_industry 계산.
    Task 3에서 계산된 IndustryMetricBenchmark 참조.
    """
    try:
        from validation.services.relative_metrics import RelativeMetricCalculator
        calc = RelativeMetricCalculator()
        result = calc.calculate_for_symbols(symbols)
        logger.info(f"calculate_relative_metrics: {result}")
        return result
    except Exception as exc:
        logger.exception(f"calculate_relative_metrics failed: {exc}")
        raise self.retry(exc=exc, countdown=300)
