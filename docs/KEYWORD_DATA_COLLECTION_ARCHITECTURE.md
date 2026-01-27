# Market Movers 키워드 생성 데이터 수집 아키텍처

## 개요

Market Movers TOP 20 종목의 키워드를 생성하기 위해 다음 데이터를 수집합니다:
- **Overview API** (Alpha Vantage): 기업 개요, 섹터, PER, EPS 등
- **News API** (MarketAux): 최신 뉴스 (선택)
- **News API** (Finnhub): 최신 뉴스 (선택)

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                  Celery Beat (매일 07:30 ET)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              sync_daily_market_movers (Task 1)                  │
│  - FMP API: Gainers/Losers/Actives TOP 20                       │
│  - 5개 지표 계산                                                 │
│  - PostgreSQL 저장                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          collect_keyword_data (Task 2) - 병렬 처리              │
│                                                                  │
│  ThreadPoolExecutor (max_workers=5)                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Worker 1: AAPL → Overview API                           │  │
│  │  Worker 2: MSFT → Overview API                           │  │
│  │  Worker 3: GOOGL → Overview API                          │  │
│  │  Worker 4: TSLA → Overview API                           │  │
│  │  Worker 5: NVDA → Overview API                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Rate Limiting:                                                 │
│  - Alpha Vantage: 5 calls/분 (12초 간격) ✓                     │
│  - MarketAux: 100 calls/일 (Optional)                          │
│  - Finnhub: 60 calls/분 (Optional)                             │
│                                                                  │
│  타임아웃:                                                       │
│  - API 호출: 10초                                                │
│  - 재시도: 2회 (exponential backoff)                            │
│  - 전체 파이프라인: 5분                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               Redis 임시 캐싱 (휘발성)                           │
│                                                                  │
│  Cache Key: keyword_context:{date}:{symbol}                     │
│  TTL: 1시간                                                      │
│  Compression: msgpack                                            │
│                                                                  │
│  Example:                                                        │
│  keyword_context:2026-01-07:AAPL → {                            │
│    "symbol": "AAPL",                                             │
│    "overview": {...},                                            │
│    "news": [...]                                                 │
│  }                                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│       generate_keywords_batch (Task 3) - LLM 호출               │
│                                                                  │
│  Gemini 2.5 Flash 배치 처리:                                    │
│  - 20개 종목을 1개 요청으로 처리 (토큰 절약)                     │
│  - Input: ~7,200 토큰 (1,200 프롬프트 + 6,000 데이터)          │
│  - Output: ~6,000 토큰 (종목당 300 토큰)                        │
│  - 비용: ~$0.009 (vs 개별 처리 $0.033)                         │
│  - 절약: 73%                                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         save_keywords (Task 4) - PostgreSQL 저장                │
│                                                                  │
│  StockKeyword 모델:                                              │
│  - symbol, date, keywords (JSON)                                │
│  - 중복 방지: unique_together (symbol, date)                    │
│  - Redis 캐시 삭제                                               │
└─────────────────────────────────────────────────────────────────┘
```

## 병렬 처리 전략

### 1. ThreadPoolExecutor 설정

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Alpha Vantage Rate Limit: 5 calls/분 = 12초 간격
# max_workers=5면 이론상 60초에 5개 처리 가능
# 실제로는 12초 간격 대기로 인해 1분에 5개 처리

max_workers = 5  # Alpha Vantage Rate Limit에 맞춤
timeout_per_call = 10  # 10초 API 타임아웃
```

### 2. 처리 시간 추정

| 작업 | 시간 | 비고 |
|------|------|------|
| Overview API × 20 | ~4분 | 12초 간격 × 20 = 240초 |
| Redis 캐싱 | ~1초 | msgpack 압축 |
| LLM 배치 호출 | ~5초 | Gemini 2.5 Flash |
| PostgreSQL 저장 | ~1초 | Bulk insert |
| **전체** | **~5분** | **병렬 처리 최적화** |

### 3. Rate Limiting 준수

```python
# Alpha Vantage: 기존 RateLimiter 재사용
from api_request.rate_limiter import get_rate_limiter

limiter = get_rate_limiter("alpha_vantage")
limiter.acquire()  # 12초 간격 자동 대기
```

## Redis 캐싱 전략

### 1. 캐시 키 구조

```python
# 키 포맷
CACHE_KEY_TEMPLATE = "keyword_context:{date}:{symbol}"

# 예시
"keyword_context:2026-01-07:AAPL"
"keyword_context:2026-01-07:MSFT"
```

### 2. 데이터 압축 (msgpack)

```python
import msgpack
from django.core.cache import cache

def set_keyword_context(date: str, symbol: str, data: dict):
    """키워드 컨텍스트 저장 (압축)"""
    cache_key = f"keyword_context:{date}:{symbol}"
    compressed = msgpack.packb(data, use_bin_type=True)
    cache.set(cache_key, compressed, timeout=3600)  # 1시간 TTL

def get_keyword_context(date: str, symbol: str) -> dict:
    """키워드 컨텍스트 조회 (압축 해제)"""
    cache_key = f"keyword_context:{date}:{symbol}"
    compressed = cache.get(cache_key)
    if compressed:
        return msgpack.unpackb(compressed, raw=False)
    return None
```

### 3. TTL 관리

- **TTL**: 1시간 (3600초)
- **이유**: 키워드 생성 후 더 이상 필요 없음 (휘발성)
- **수동 삭제**: 키워드 저장 후 명시적으로 삭제 가능

## Celery 태스크 체이닝

### 1. 태스크 체인 구조

```python
from celery import chain, group
from serverless.tasks import (
    sync_daily_market_movers,
    collect_keyword_data,
    generate_keywords_batch,
    save_keywords
)

# 태스크 체인
result = chain(
    # Task 1: Market Movers 동기화
    sync_daily_market_movers.si(target_date='2026-01-07'),

    # Task 2: 키워드 데이터 수집 (병렬)
    collect_keyword_data.s(),  # Task 1의 결과 (date, symbols) 받음

    # Task 3: 키워드 생성 (LLM 배치)
    generate_keywords_batch.s(),  # Task 2의 결과 (Redis 키 리스트) 받음

    # Task 4: 키워드 저장
    save_keywords.s(),  # Task 3의 결과 (키워드 딕셔너리) 받음
).apply_async()
```

### 2. 에러 핸들링

```python
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

class CallbackTask(Task):
    """에러 핸들링 콜백"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """태스크 실패 시"""
        logger.error(
            "keyword_pipeline_failure",
            extra={
                "task": self.name,
                "task_id": task_id,
                "error": str(exc),
                "args": args,
            }
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """재시도 시"""
        logger.warning(
            "keyword_pipeline_retry",
            extra={
                "task": self.name,
                "task_id": task_id,
                "retry_count": self.request.retries,
                "error": str(exc),
            }
        )

    def on_success(self, retval, task_id, args, kwargs):
        """성공 시"""
        logger.info(
            "keyword_pipeline_success",
            extra={
                "task": self.name,
                "task_id": task_id,
                "duration_ms": retval.get('duration_ms', 0),
            }
        )
```

## 로깅 시스템

### 1. 구조화된 로깅

```python
import logging
import time

logger = logging.getLogger(__name__)

# Phase 1: Overview API 수집 시작
logger.info("keyword_data_collection", extra={
    "phase": "overview",
    "symbol": "AAPL",
    "status": "started",
    "timestamp": time.time(),
})

# Phase 2: API 호출 성공
logger.info("keyword_data_collection", extra={
    "phase": "overview",
    "symbol": "AAPL",
    "status": "success",
    "duration_ms": 1234,
    "api": "alpha_vantage",
    "cache_hit": False,
})

# Phase 3: API 호출 실패
logger.error("keyword_data_collection", extra={
    "phase": "overview",
    "symbol": "AAPL",
    "status": "failed",
    "error": "HTTPError 429",
    "retry_count": 1,
})
```

### 2. 메트릭 포인트

| 메트릭 | 타입 | 라벨 | 설명 |
|--------|------|------|------|
| `keyword_data_collection_duration_seconds` | Histogram | phase, status | 단계별 소요 시간 |
| `keyword_api_calls_total` | Counter | api, status | API 호출 횟수 |
| `keyword_cache_operations_total` | Counter | operation, status | 캐시 작업 횟수 |
| `keyword_pipeline_failures_total` | Counter | task, error_type | 파이프라인 실패 횟수 |

### 3. 전체 파이프라인 로깅

```python
def log_pipeline_summary(result: dict):
    """파이프라인 완료 후 요약 로깅"""
    logger.info("keyword_pipeline_summary", extra={
        "total_stocks": result['total_stocks'],
        "successful": result['successful'],
        "failed": result['failed'],
        "total_duration_ms": result['duration_ms'],
        "api_calls": {
            "alpha_vantage": result['api_calls']['alpha_vantage'],
            "marketaux": result['api_calls'].get('marketaux', 0),
            "finnhub": result['api_calls'].get('finnhub', 0),
        },
        "cache_hits": result['cache_hits'],
        "llm_tokens": {
            "input": result['llm_tokens']['input'],
            "output": result['llm_tokens']['output'],
            "cost_usd": result['llm_tokens']['cost_usd'],
        },
    })
```

## 타임아웃 및 재시도

### 1. API 호출 타임아웃

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),  # 최대 2회 재시도 (총 3회 시도)
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 2초, 4초, 8초
    reraise=True
)
def fetch_overview_with_retry(symbol: str) -> dict:
    """
    Overview API 호출 (재시도 포함)

    타임아웃: 10초
    재시도: 2회 (exponential backoff)
    """
    client = httpx.Client(timeout=10.0)

    try:
        # Rate Limiting
        limiter = get_rate_limiter("alpha_vantage")
        limiter.acquire()

        # API 호출
        response = client.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "OVERVIEW",
                "symbol": symbol,
                "apikey": settings.ALPHA_VANTAGE_API_KEY,
            }
        )
        response.raise_for_status()
        return response.json()

    finally:
        client.close()
```

### 2. 전체 파이프라인 타임아웃

```python
@shared_task(
    bind=True,
    max_retries=1,
    soft_time_limit=300,  # 5분 소프트 타임아웃
    time_limit=360,  # 6분 하드 타임아웃
)
def collect_keyword_data(self, movers_data: dict):
    """
    키워드 데이터 수집 (병렬)

    타임아웃:
    - 소프트: 5분 (SoftTimeLimitExceeded 예외)
    - 하드: 6분 (강제 종료)
    """
    try:
        # 병렬 처리 로직
        ...
    except SoftTimeLimitExceeded:
        logger.error("keyword_data_collection_timeout")
        raise
```

## 모니터링 대시보드

### 1. 실시간 메트릭 (Prometheus)

```prometheus
# API 호출 성공률
sum(rate(keyword_api_calls_total{status="success"}[5m])) by (api)
/ sum(rate(keyword_api_calls_total[5m])) by (api)

# 평균 소요 시간
histogram_quantile(0.95,
  sum(rate(keyword_data_collection_duration_seconds_bucket[5m])) by (le, phase)
)

# 캐시 히트율
sum(rate(keyword_cache_operations_total{operation="get", status="hit"}[5m]))
/ sum(rate(keyword_cache_operations_total{operation="get"}[5m]))
```

### 2. 알림 규칙

```yaml
# API 성공률 80% 미만
- alert: KeywordAPILowSuccessRate
  expr: |
    sum(rate(keyword_api_calls_total{status="success"}[5m])) by (api)
    / sum(rate(keyword_api_calls_total[5m])) by (api) < 0.8
  for: 5m
  annotations:
    summary: "Keyword API 성공률 낮음: {{ $labels.api }}"

# 파이프라인 소요 시간 5분 초과
- alert: KeywordPipelineSlow
  expr: |
    histogram_quantile(0.95,
      sum(rate(keyword_data_collection_duration_seconds_bucket[5m]))
    ) > 300
  for: 2m
  annotations:
    summary: "Keyword 파이프라인 소요 시간 초과"
```

## 비용 최적화

### 1. 배치 vs 개별 처리 비교

| 방식 | Input 토큰 | Output 토큰 | 비용 (USD) |
|------|-----------|------------|-----------|
| **배치 (20개)** | 7,200 | 6,000 | $0.009 |
| 개별 (20개) | 26,000 | 6,000 | $0.033 |
| **절약** | 18,800 | 0 | **$0.024 (73%)** |

### 2. API 호출 최소화

- **캐싱**: Overview 데이터 24시간 캐시
- **조건부 호출**: 이미 캐시된 데이터는 건너뛰기
- **배치 처리**: 1개 LLM 요청으로 20개 종목 처리

## 장애 복구 전략

### 1. 부분 실패 허용

```python
# 20개 종목 중 일부 실패해도 나머지는 진행
successful_symbols = []
failed_symbols = []

for symbol in symbols:
    try:
        data = fetch_overview(symbol)
        successful_symbols.append(symbol)
    except Exception as e:
        logger.error(f"Failed to fetch {symbol}: {e}")
        failed_symbols.append(symbol)

# 성공한 종목만으로 키워드 생성
if successful_symbols:
    generate_keywords(successful_symbols)

# 실패 종목은 다음 실행 시 재시도
```

### 2. 수동 재실행

```python
# Django Admin 또는 Management Command
python manage.py collect_keyword_data --date 2026-01-07 --symbols AAPL,MSFT
```

## 다음 단계

1. **Phase 1**: Overview API만 사용 (Alpha Vantage)
2. **Phase 2**: News API 추가 (MarketAux, Finnhub) - 선택적
3. **Phase 3**: 실시간 모니터링 대시보드 (Grafana)
4. **Phase 4**: ML 기반 키워드 품질 평가

---

**작성일**: 2026-01-24
**작성자**: @infra
**버전**: 1.0
