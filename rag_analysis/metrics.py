"""
Prometheus Metrics for RAG Analysis

Stock-Vis AI 분석 시스템의 성능 모니터링 메트릭입니다.

Metrics:
    - analysis_requests_total: 총 분석 요청 수
    - analysis_latency_seconds: 분석 응답 시간
    - cache_hit_rate: 캐시 히트율
    - token_usage: 토큰 사용량
    - cost_usd: 비용 (USD)
"""

import logging
from functools import wraps
from time import time
from typing import Optional, Callable
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Prometheus 클라이언트가 설치된 경우에만 메트릭 생성
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary

    # =============================================================
    # Analysis Request Metrics
    # =============================================================

    ANALYSIS_REQUESTS = Counter(
        'stockvis_analysis_requests_total',
        'Total number of analysis requests',
        ['status', 'cache_hit', 'model']
    )

    ANALYSIS_LATENCY = Histogram(
        'stockvis_analysis_latency_seconds',
        'Analysis request latency in seconds',
        ['phase'],
        buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 15.0, 30.0]
    )

    ANALYSIS_LATENCY_SUMMARY = Summary(
        'stockvis_analysis_latency_summary',
        'Analysis latency summary with quantiles',
        ['phase']
    )

    # =============================================================
    # Cache Metrics
    # =============================================================

    CACHE_OPERATIONS = Counter(
        'stockvis_cache_operations_total',
        'Total cache operations',
        ['operation', 'result']  # operation: check/store, result: hit/miss/success/failure
    )

    CACHE_HIT_RATE = Gauge(
        'stockvis_cache_hit_rate',
        'Cache hit rate (rolling window)',
    )

    CACHE_ENTRIES = Gauge(
        'stockvis_cache_entries',
        'Number of cache entries',
        ['status']  # active, expired
    )

    CACHE_SIMILARITY_SCORE = Histogram(
        'stockvis_cache_similarity_score',
        'Semantic similarity scores for cache hits',
        buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
    )

    # =============================================================
    # Token Usage Metrics
    # =============================================================

    TOKEN_USAGE = Histogram(
        'stockvis_token_usage',
        'Token usage per request',
        ['type', 'model'],  # type: input/output, model: sonnet/haiku/gemini
        buckets=[50, 100, 200, 500, 1000, 2000, 5000, 10000]
    )

    TOKEN_TOTAL = Counter(
        'stockvis_tokens_total',
        'Total tokens used',
        ['type', 'model']
    )

    # =============================================================
    # Cost Metrics
    # =============================================================

    COST_USD = Counter(
        'stockvis_cost_usd_total',
        'Total cost in USD',
        ['model', 'cached']
    )

    COST_PER_REQUEST = Histogram(
        'stockvis_cost_per_request_usd',
        'Cost per request in USD',
        ['model'],
        buckets=[0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05]
    )

    COST_SAVED = Counter(
        'stockvis_cost_saved_usd_total',
        'Total cost saved by caching in USD',
    )

    # =============================================================
    # Pipeline Stage Metrics
    # =============================================================

    PIPELINE_STAGE_DURATION = Histogram(
        'stockvis_pipeline_stage_duration_seconds',
        'Duration of each pipeline stage',
        ['stage'],
        buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
    )

    PIPELINE_ERRORS = Counter(
        'stockvis_pipeline_errors_total',
        'Total pipeline errors',
        ['stage', 'error_type']
    )

    # =============================================================
    # Entity Extraction Metrics
    # =============================================================

    ENTITIES_EXTRACTED = Histogram(
        'stockvis_entities_extracted',
        'Number of entities extracted per request',
        ['entity_type'],  # stocks, metrics, concepts
        buckets=[0, 1, 2, 3, 5, 10]
    )

    # =============================================================
    # Search Metrics
    # =============================================================

    SEARCH_RESULTS = Histogram(
        'stockvis_search_results',
        'Number of search results',
        ['search_type'],  # vector, bm25, hybrid
        buckets=[0, 5, 10, 15, 20, 50]
    )

    RERANK_SCORE = Histogram(
        'stockvis_rerank_score',
        'Top document rerank score',
        buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0]
    )

    # =============================================================
    # Compression Metrics
    # =============================================================

    COMPRESSION_RATIO = Histogram(
        'stockvis_compression_ratio',
        'Context compression ratio',
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    )

    TOKENS_SAVED_BY_COMPRESSION = Counter(
        'stockvis_tokens_saved_by_compression_total',
        'Total tokens saved by compression',
    )

    _METRICS_AVAILABLE = True
    logger.info("Prometheus metrics initialized successfully")

except ImportError:
    _METRICS_AVAILABLE = False
    logger.warning("prometheus_client not installed - metrics disabled")

    # Dummy classes for graceful degradation
    class DummyMetric:
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass
        def dec(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass

    ANALYSIS_REQUESTS = DummyMetric()
    ANALYSIS_LATENCY = DummyMetric()
    ANALYSIS_LATENCY_SUMMARY = DummyMetric()
    CACHE_OPERATIONS = DummyMetric()
    CACHE_HIT_RATE = DummyMetric()
    CACHE_ENTRIES = DummyMetric()
    CACHE_SIMILARITY_SCORE = DummyMetric()
    TOKEN_USAGE = DummyMetric()
    TOKEN_TOTAL = DummyMetric()
    COST_USD = DummyMetric()
    COST_PER_REQUEST = DummyMetric()
    COST_SAVED = DummyMetric()
    PIPELINE_STAGE_DURATION = DummyMetric()
    PIPELINE_ERRORS = DummyMetric()
    ENTITIES_EXTRACTED = DummyMetric()
    SEARCH_RESULTS = DummyMetric()
    RERANK_SCORE = DummyMetric()
    COMPRESSION_RATIO = DummyMetric()
    TOKENS_SAVED_BY_COMPRESSION = DummyMetric()


def is_metrics_available() -> bool:
    """Prometheus 메트릭 사용 가능 여부"""
    return _METRICS_AVAILABLE


# =============================================================
# Helper Functions
# =============================================================

def record_analysis_request(
    status: str,
    cache_hit: bool,
    model: str,
    latency_seconds: float
):
    """분석 요청 기록"""
    ANALYSIS_REQUESTS.labels(
        status=status,
        cache_hit=str(cache_hit).lower(),
        model=model
    ).inc()

    ANALYSIS_LATENCY.labels(phase='total').observe(latency_seconds)
    ANALYSIS_LATENCY_SUMMARY.labels(phase='total').observe(latency_seconds)


def record_cache_operation(
    operation: str,
    result: str,
    similarity_score: Optional[float] = None
):
    """캐시 작업 기록"""
    CACHE_OPERATIONS.labels(operation=operation, result=result).inc()

    if similarity_score is not None and result == 'hit':
        CACHE_SIMILARITY_SCORE.observe(similarity_score)


def record_token_usage(
    input_tokens: int,
    output_tokens: int,
    model: str
):
    """토큰 사용량 기록"""
    TOKEN_USAGE.labels(type='input', model=model).observe(input_tokens)
    TOKEN_USAGE.labels(type='output', model=model).observe(output_tokens)

    TOKEN_TOTAL.labels(type='input', model=model).inc(input_tokens)
    TOKEN_TOTAL.labels(type='output', model=model).inc(output_tokens)


def record_cost(
    cost_usd: float,
    model: str,
    cached: bool = False
):
    """비용 기록"""
    COST_USD.labels(model=model, cached=str(cached).lower()).inc(cost_usd)
    COST_PER_REQUEST.labels(model=model).observe(cost_usd)


def record_cost_saved(cost_usd: float):
    """캐시로 절감된 비용 기록"""
    COST_SAVED.inc(cost_usd)


def record_pipeline_stage(stage: str, duration_seconds: float):
    """파이프라인 단계 기록"""
    PIPELINE_STAGE_DURATION.labels(stage=stage).observe(duration_seconds)


def record_pipeline_error(stage: str, error_type: str):
    """파이프라인 에러 기록"""
    PIPELINE_ERRORS.labels(stage=stage, error_type=error_type).inc()


def record_entities(stocks: int, metrics: int, concepts: int):
    """추출된 엔티티 기록"""
    ENTITIES_EXTRACTED.labels(entity_type='stocks').observe(stocks)
    ENTITIES_EXTRACTED.labels(entity_type='metrics').observe(metrics)
    ENTITIES_EXTRACTED.labels(entity_type='concepts').observe(concepts)


def record_search_results(search_type: str, count: int):
    """검색 결과 기록"""
    SEARCH_RESULTS.labels(search_type=search_type).observe(count)


def record_rerank_score(score: float):
    """Rerank 점수 기록"""
    RERANK_SCORE.observe(score)


def record_compression(original_tokens: int, compressed_tokens: int):
    """압축 결과 기록"""
    if original_tokens > 0:
        ratio = compressed_tokens / original_tokens
        COMPRESSION_RATIO.observe(ratio)

        tokens_saved = original_tokens - compressed_tokens
        if tokens_saved > 0:
            TOKENS_SAVED_BY_COMPRESSION.inc(tokens_saved)


def update_cache_stats(active_entries: int, expired_entries: int, hit_rate: float):
    """캐시 통계 업데이트"""
    CACHE_ENTRIES.labels(status='active').set(active_entries)
    CACHE_ENTRIES.labels(status='expired').set(expired_entries)
    CACHE_HIT_RATE.set(hit_rate)


# =============================================================
# Decorators
# =============================================================

def track_latency(phase: str):
    """함수 실행 시간 추적 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time() - start
                ANALYSIS_LATENCY.labels(phase=phase).observe(duration)
                PIPELINE_STAGE_DURATION.labels(stage=phase).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time() - start
                ANALYSIS_LATENCY.labels(phase=phase).observe(duration)
                PIPELINE_STAGE_DURATION.labels(stage=phase).observe(duration)

        # Check if function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


@contextmanager
def track_stage(stage: str):
    """파이프라인 단계 추적 컨텍스트 매니저"""
    start = time()
    try:
        yield
    except Exception as e:
        record_pipeline_error(stage, type(e).__name__)
        raise
    finally:
        duration = time() - start
        record_pipeline_stage(stage, duration)


# =============================================================
# Metrics Exporter for Views
# =============================================================

def get_metrics_summary() -> dict:
    """현재 메트릭 요약 반환 (API용)"""
    if not _METRICS_AVAILABLE:
        return {'status': 'metrics_unavailable'}

    # Note: 실제 값을 가져오려면 prometheus_client의 REGISTRY를 사용해야 함
    # 여기서는 간단한 구조만 반환
    return {
        'status': 'available',
        'metrics': [
            'stockvis_analysis_requests_total',
            'stockvis_analysis_latency_seconds',
            'stockvis_cache_hit_rate',
            'stockvis_token_usage',
            'stockvis_cost_usd_total',
            'stockvis_pipeline_stage_duration_seconds',
        ]
    }
