# Market Movers 키워드 데이터 수집 사용 가이드

## 개요

Market Movers TOP 20 종목의 키워드를 생성하기 위해 Overview, News 등의 컨텍스트 데이터를 병렬 수집합니다.

---

## 자동 실행 (Celery Beat)

### 1. 스케줄 설정

```python
# config/celery.py
CELERYBEAT_SCHEDULE = {
    'keyword-generation-pipeline': {
        'task': 'serverless.tasks.keyword_generation_pipeline',
        'schedule': crontab(hour=8, minute=0),  # 매일 08:00 EST
        'kwargs': {'mover_type': 'gainers'},
    }
}
```

### 2. 실행 확인

```bash
# Celery Beat 로그 확인
tail -f celerybeat.log

# 또는 Celery Flower (모니터링 도구)
celery -A config flower
```

---

## 수동 실행

### 1. Django Shell에서 실행

```python
from serverless.tasks import keyword_generation_pipeline

# 오늘 Gainers
result = keyword_generation_pipeline.delay()

# 특정 날짜 Losers
result = keyword_generation_pipeline.delay(
    movers_date='2026-01-07',
    mover_type='losers'
)

# 결과 조회
result.get()
```

### 2. 개별 태스크 실행

```python
from serverless.tasks import (
    collect_keyword_data,
    generate_keywords_batch,
    save_keywords
)

# Step 1: 데이터 수집
collection_result = collect_keyword_data.delay(
    movers_date='2026-01-07',
    mover_type='gainers'
).get()

# Step 2: 키워드 생성
keywords_result = generate_keywords_batch.delay(collection_result).get()

# Step 3: 저장
save_result = save_keywords.delay(keywords_result).get()
```

### 3. 동기 방식 테스트 (스크립트)

```python
from datetime import date
from serverless.services.keyword_data_collector import collect_keyword_data_sync

symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
target_date = date.today()

result = collect_keyword_data_sync(symbols, target_date)

print(f"성공: {len(result['successful'])}")
print(f"실패: {len(result['failed'])}")
print(f"소요 시간: {result['duration_ms'] / 1000:.2f}초")
```

---

## Redis 캐시 관리

### 1. 캐시 조회

```python
from serverless.services.keyword_data_collector import KeywordDataCollector

collector = KeywordDataCollector()

# 단일 종목
context = collector.get_cached_context('2026-01-07', 'AAPL')

# 배치 조회
contexts = collector.get_batch_contexts(
    '2026-01-07',
    ['AAPL', 'MSFT', 'GOOGL']
)
```

### 2. 캐시 삭제

```python
# 단일 종목
collector.delete_cached_context('2026-01-07', 'AAPL')

# 전체 삭제 (Django Shell)
from django.core.cache import cache
cache.delete_pattern('keyword_context:*')
```

### 3. 캐시 통계

```python
from django_redis import get_redis_connection

redis_conn = get_redis_connection("default")

# 전체 키 개수
keys = redis_conn.keys('keyword_context:*')
print(f"캐시된 키 개수: {len(keys)}")

# 특정 날짜의 캐시
keys = redis_conn.keys('keyword_context:2026-01-07:*')
print(f"2026-01-07 캐시: {len(keys)}개")
```

---

## 토큰 추정

### 1. 배치 토큰 추정

```python
from serverless.services.keyword_data_collector import estimate_batch_tokens

# Redis에서 컨텍스트 조회
contexts = collector.get_batch_contexts('2026-01-07', symbols)

# 토큰 추정
tokens = estimate_batch_tokens(contexts)

print(f"입력 토큰: {tokens['total_input_tokens']:,}")
print(f"출력 토큰: {tokens['estimated_output_tokens']:,}")
print(f"총 토큰: {tokens['total_input_tokens'] + tokens['estimated_output_tokens']:,}")
```

### 2. 비용 추정

```python
# Gemini 2.5 Flash 가격 (2026년 1월 기준)
INPUT_COST_PER_1M = 0.30  # $0.30 / 1M tokens
OUTPUT_COST_PER_1M = 1.20  # $1.20 / 1M tokens

input_cost = (tokens['total_input_tokens'] / 1_000_000) * INPUT_COST_PER_1M
output_cost = (tokens['estimated_output_tokens'] / 1_000_000) * OUTPUT_COST_PER_1M
total_cost = input_cost + output_cost

print(f"예상 비용: ${total_cost:.6f}")
```

---

## 로그 확인

### 1. 구조화된 로그

```json
{
  "timestamp": "2026-01-24T10:00:00",
  "logger": "serverless.services.keyword_data_collector",
  "level": "INFO",
  "message": "keyword_data_collection_batch",
  "extra": {
    "status": "completed",
    "successful": 18,
    "failed": 2,
    "cache_hits": 5,
    "api_calls": 13,
    "duration_ms": 240000
  }
}
```

### 2. 로그 필터링

```bash
# 성공한 종목만
grep '"status": "success"' stocks.log | jq .extra.symbol

# 실패한 종목
grep '"status": "failed"' stocks.log | jq '{symbol: .extra.symbol, error: .extra.error}'

# API 호출 시간
grep 'keyword_data_collection' stocks.log | jq '.extra.duration_ms'
```

---

## 문제 해결

### 1. Rate Limit 초과

**증상**: `RateLimitExceeded: per_minute` 에러

**원인**: Alpha Vantage 5 calls/분 초과

**해결**:
```python
# MAX_WORKERS 조정 (5 → 3)
collector = KeywordDataCollector()
collector.MAX_WORKERS = 3
```

### 2. 타임아웃

**증상**: `SoftTimeLimitExceeded` 에러

**원인**: 5분 내에 20개 종목 처리 실패

**해결**:
```python
# Celery 태스크 타임아웃 증가
@shared_task(
    soft_time_limit=600,  # 10분
    time_limit=720,  # 12분
)
```

### 3. 캐시 누락

**증상**: `No cached context for AAPL on 2026-01-07`

**원인**: Redis 캐시 만료 (TTL 1시간)

**해결**:
```python
# TTL 증가
collector.CACHE_TTL = 7200  # 2시간
```

### 4. API 에러

**증상**: `Alpha vantage error: Invalid API call`

**원인**: Alpha Vantage API 키 오류

**확인**:
```bash
# .env 파일 확인
cat .env | grep ALPHA_VANTAGE_API_KEY

# Django Settings 확인
python manage.py shell
>>> from django.conf import settings
>>> settings.ALPHA_VANTAGE_API_KEY
```

---

## 모니터링 메트릭

### 1. Prometheus 메트릭

```prometheus
# API 성공률
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

### 2. Grafana 대시보드

**패널 구성**:
1. API 호출 성공률 (Time Series)
2. 평균 소요 시간 (Gauge)
3. 캐시 히트율 (Stat)
4. 실패 종목 리스트 (Table)

---

## 성능 최적화

### 1. 병렬 처리 최적화

```python
# 현재: ThreadPoolExecutor (max_workers=5)
# - Alpha Vantage Rate Limit: 5 calls/분
# - 20개 종목: ~4분

# 개선: asyncio + httpx
# - 비동기 I/O로 대기 시간 최소화
# - 20개 종목: ~2분 (예상)
```

### 2. 캐싱 최적화

```python
# 현재: msgpack 압축
# - 압축률: ~70%

# 개선: zstd 압축
# - 압축률: ~80%
# - 압축 속도: msgpack 대비 20% 빠름
```

### 3. 배치 크기 조정

```python
# 현재: 20개 종목 1개 요청
# - 입력: 7,200 토큰
# - 출력: 6,000 토큰
# - 비용: $0.009

# 개선: 10개 종목 × 2개 요청
# - 입력: 4,200 토큰 × 2 = 8,400 토큰
# - 출력: 3,000 토큰 × 2 = 6,000 토큰
# - 비용: $0.010 (약간 증가하지만 안정성 향상)
```

---

## 다음 단계

1. **Phase 1**: Overview API만 사용 (Alpha Vantage) ✅
2. **Phase 2**: News API 추가 (MarketAux, Finnhub)
3. **Phase 3**: 실시간 모니터링 대시보드 (Grafana)
4. **Phase 4**: ML 기반 키워드 품질 평가

---

**작성일**: 2026-01-24
**작성자**: @infra
**버전**: 1.0
