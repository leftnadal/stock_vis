"""
1차 검증 배치 파이프라인 Celery 태스크

Task 1: fetch_annual_financials — 재무제표 가용성 확인
Task 2: calculate_derived_metrics — 33개 지표 계산 + value_status 판정
Task 3: calculate_benchmarks — Peer 선정 + Benchmark 계산
Task 3.5: calculate_relative_metrics — rev_growth_vs_industry 계산
Task 4: calculate_category_signals — 카테고리별 신호등 계산
Task 5: update_peer_list_caches — confidence 재검증
Task 6: log_batch_run — 배치 실행 로그
Orchestrator: run_weekly_validation_batch — 전체 파이프라인 chain
"""

import logging
import time
from celery import shared_task, chain
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def fetch_annual_financials(self, symbols=None):
    """Task 1: 재무제표 가용성 확인."""
    try:
        from validation.services.financial_fetcher import FinancialFetcher
        fetcher = FinancialFetcher()
        result = fetcher.check_and_fetch(symbols)
        logger.info(f"Task 1: {result['total']} total, {result['ready']} ready, {len(result['missing'])} missing")
        return result
    except Exception as exc:
        logger.exception(f"fetch_annual_financials failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=1, soft_time_limit=7200, time_limit=7260)
def calculate_derived_metrics(self, prev_result=None, symbols=None):
    """Task 2: 33개 지표 계산 + value_status 판정."""
    try:
        from validation.services.metric_calculator import MetricCalculator
        calculator = MetricCalculator()
        result = calculator.calculate_for_symbols(symbols)
        logger.info(f"Task 2: {result['total']} total, {result['success']} success, {result['errors']} errors")
        return result
    except Exception as exc:
        logger.exception(f"calculate_derived_metrics failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=1, soft_time_limit=7200, time_limit=7260)
def calculate_benchmarks(self, prev_result=None, symbols=None):
    """Task 3: Peer 선정 + Benchmark 계산."""
    try:
        from validation.services.benchmark_calculator import BenchmarkCalculator
        calc = BenchmarkCalculator()
        result = calc.calculate_for_symbols(symbols)
        logger.info(f"Task 3: {result['total']} total, {result['success']} success, {result['errors']} errors")
        return result
    except Exception as exc:
        logger.exception(f"calculate_benchmarks failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=1, soft_time_limit=1800, time_limit=1860)
def calculate_relative_metrics(self, prev_result=None, symbols=None):
    """Task 3.5: rev_growth_vs_industry 계산."""
    try:
        from validation.services.relative_metrics import RelativeMetricCalculator
        calc = RelativeMetricCalculator()
        result = calc.calculate_for_symbols(symbols)
        logger.info(f"Task 3.5: {result}")
        return result
    except Exception as exc:
        logger.exception(f"calculate_relative_metrics failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=1, soft_time_limit=3600, time_limit=3660)
def calculate_category_signals(self, prev_result=None, symbols=None):
    """Task 4: 카테고리별 신호등 계산 (green/yellow/red/gray)."""
    try:
        from validation.services.category_signal_calculator import CategorySignalCalculator
        calc = CategorySignalCalculator()
        result = calc.calculate_for_symbols(symbols)
        logger.info(f"Task 4: {result['total']} total, {result['success']} success, {result['errors']} errors")
        return result
    except Exception as exc:
        logger.exception(f"calculate_category_signals failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=1, soft_time_limit=600, time_limit=660)
def update_peer_list_caches(self, prev_result=None):
    """Task 5: peer_list_cache confidence 재검증 (Task 3에서 이미 갱신, 여기서는 확인만)."""
    try:
        from metrics.models import PeerListCache
        total = PeerListCache.objects.count()
        logger.info(f"Task 5: peer_list_cache {total}건 확인 완료")
        return {'total': total}
    except Exception as exc:
        logger.exception(f"update_peer_list_caches failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=0, soft_time_limit=60, time_limit=120)
def log_batch_run(self, prev_result=None, universe='sp500', start_time=None):
    """Task 6: BatchJobRun에 실행 결과 기록."""
    try:
        from metrics.models import BatchJobRun
        from stocks.models import SP500Constituent

        total_symbols = SP500Constituent.objects.filter(is_active=True).count()
        elapsed = None
        if start_time:
            elapsed = time.time() - start_time

        from metrics.models import CompanyMetricSnapshot
        from validation.models import CategorySignal
        snapshot_count = CompanyMetricSnapshot.objects.count()
        signal_count = CategorySignal.objects.count()

        job = BatchJobRun.objects.create(
            job_name='weekly_validation_batch',
            job_type='scheduled',
            started_at=timezone.now(),
            completed_at=timezone.now(),
            status='success',
            total_symbols=total_symbols,
            success_count=total_symbols,
            triggered_by='celery_beat',
            notes=f'universe={universe}, snapshots={snapshot_count}, signals={signal_count}',
        )
        logger.info(f"Task 6: batch run logged (id={job.pk})")
        return {'job_id': job.pk}
    except Exception as exc:
        logger.exception(f"log_batch_run failed: {exc}")
        return {'error': str(exc)}


@shared_task(bind=True, max_retries=0, soft_time_limit=14400, time_limit=14460)
def run_weekly_validation_batch(self, universe='sp500'):
    """
    오케스트레이터: 주간 배치 파이프라인.
    Task 1 → 2 → 3 → 3.5 → 4 → 5 → 6 순차 실행.
    """
    logger.info(f"Starting weekly validation batch (universe={universe})")
    start = time.time()

    pipeline = chain(
        fetch_annual_financials.s(),
        calculate_derived_metrics.s(),
        calculate_benchmarks.s(),
        calculate_relative_metrics.s(),
        calculate_category_signals.s(),
        update_peer_list_caches.s(),
        log_batch_run.s(universe=universe, start_time=start),
    )
    pipeline.apply_async()
    logger.info("Weekly validation batch pipeline dispatched")
    return {'status': 'dispatched', 'universe': universe}
