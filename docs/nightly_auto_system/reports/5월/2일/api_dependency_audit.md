# 외부 API 의존성 감사 보고서

- **작성일**: 2026-05-02
- **대상 브랜치**: portfolio
- **감사 범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis (캐시) 의존성 전체
- **방식**: 정적 코드 분석 (읽기 전용, 수정 없음)
- **목적**: 외부 API 장애 시 시스템 영향 평가, Circuit Breaker 도입 후보 식별

---

## 0. Executive Summary

| 항목 | 값 |
|------|-----|
| FMP 호출 모듈 | 36개 파일 (실제 클라이언트 4종 분산) |
| Gemini 호출 모듈 | 36개 파일 (LLMServiceLite 외 16개 직접 호출 지점) |
| 활용 중인 CircuitBreaker | 1종, 3개 호출처에만 적용 (`news/tasks.py`만) |
| 정의된 RateLimiter | 3종 (`api_request/`, `stocks/services/`, 클라이언트 내부) — 통합 미적용 |
| Critical 위험 | 5건 (아래 Critical 표 참조) |

### Critical 위험 요약

| # | 위치 | 문제 | 영향 |
|---|------|------|------|
| C1 | `api_request/sec_edgar_client.py:166` | 429 시 무한 재귀 (`return self._make_request(...)`) | 스택 오버플로 / 무한 대기 |
| C2 | `serverless/services/fmp_client.py`, `macro/services/fmp_client.py` | 402(Premium) 분기 부재 → 일반 에러로 처리 | Premium 심볼 만나면 모든 후속 호출 실패 |
| C3 | `stocks/services/rate_limiter.py:25-27` | FMP 무료 티어 잔재 (10/min, 250/day) — Starter 300/min 미반영 | 부정확한 throttling, 호출 제한 |
| C4 | FMP/Gemini 클라이언트 분산 (4종/16+개) | 인스턴스별 독립 카운터, 분산 환경에서 합산 불가 | 실제 호출량이 한도 추적치보다 높음 |
| C5 | Gemini 호출 다수 — 429/quota 분기 단 1곳만 (`rag_analysis/services/llm_service.py`) | 다른 16개 호출처는 단순 except → None 반환 | Gemini quota 소진 시 silent failure 연쇄 |

---

## 1. 의존성 매트릭스

서비스별 외부 API 사용 + 핵심 fallback 보유 여부.

| 모듈 | FMP | Gemini | FRED | Neo4j | SEC | Redis(캐시) | Fallback/Graceful Degrade |
|------|:---:|:------:|:----:|:-----:|:---:|:-----------:|---------------------------|
| `api_request/providers/fmp/` | ✅ Core | — | — | — | — | — | FMPPremiumError 분기 + 재시도 3회 |
| `api_request/sec_edgar_client.py` | — | — | — | — | ✅ | — | 429 시 무한 재귀 (위험 C1) |
| `stocks/services/fmp_*.py` (5개) | ✅ httpx 인라인 | — | — | — | — | TTL 캐시 | 빈 리스트 silent (분기 약함) |
| `stocks/services/sp500_eod_service.py` | ✅ | — | — | — | — | — | except → 0 반환 |
| `stocks/tasks.py` | ✅ | — | — | — | — | — | `.` 심볼 사전 제외, 그 외 raw exception |
| `serverless/services/fmp_client.py` | ✅ httpx | — | — | — | — | 5분 TTL | FMPAPIError 단일 catch |
| `serverless/services/data_sync.py` | ✅ | — | — | — | — | — | FMPAPIError + Celery retry 3회 |
| `serverless/services/keyword_*.py` (3개) | — | ✅ | — | — | — | semantic | except → fallback 키워드 |
| `serverless/services/llm_relation_extractor.py` | — | ✅ | — | — | — | 1H 캐시 | except → empty result |
| `serverless/services/chain_sight_service.py` | ✅ | — | — | (간접) | — | — | except → 빈 dict |
| `serverless/services/regulatory_service.py` | — | ✅ Lazy | — | — | — | — | except → 기본값 반환 |
| `serverless/services/neo4j_chain_sight_service.py` | — | — | — | ✅ | — | — | None/빈 결과 |
| `news/services/aggregator.py` | ✅ | — | — | — | — | — | provider별 try/except |
| `news/services/news_deep_analyzer.py` | — | ✅ Sleep 4s | — | — | — | — | except → None |
| `news/services/keyword_extractor.py` | — | ✅ | — | — | — | — | except → 기본 키워드 |
| `news/services/stock_insights.py` | — | ✅ | — | — | — | — | except → 빈 결과 |
| `news/api/views.py` | — | ✅ | — | — | — | 1H 캐시 | except → 500 |
| `news/tasks.py` | ✅ via aggregator | — | — | — | — | — | **CircuitBreaker('fmp') 적용 ✅** |
| `macro/services/fmp_client.py` | ✅ | — | — | — | — | — | except → None/[] (premium 분기 없음) |
| `macro/services/fred_client.py` | — | — | ✅ | — | — | — | 401/403/404 즉시 raise, 5xx 재시도 3회 |
| `macro/services/macro_service.py` | ✅ | — | ✅ | — | — | TTL | per-call try/except |
| `macro/tasks.py` | ✅ via service | — | ✅ | — | — | — | exponential backoff retry 3회 |
| `thesis/tasks/eod_pipeline.py` | ✅ | — | ✅ | — | — | — | FMPPremiumError 분기, FMPClientError catch |
| `thesis/services/thesis_builder.py` | — | ✅ | — | — | — | — | except → 기본 응답 |
| `thesis/services/indicator_matcher.py` | — | ✅ | — | — | — | — | except → 빈 결과 |
| `thesis/services/prompt_builder.py` (3 호출) | — | ✅ | — | — | — | — | except → 빈 dict |
| `thesis/views/conversation_views.py` | — | ✅ | — | — | — | — | except → 500 |
| `validation/services/llm_peer_filter.py` | — | ✅ | — | — | — | — | except → {'error': str(e)} |
| `chainsight/graph/repository.py` | — | — | — | ✅ PID-fork-safe | — | — | GraphConnectionError raise |
| `chainsight/services/neo4j_sync.py` | — | — | — | ✅ | — | — | retry + neo4j_dirty 플래그 |
| `chainsight/tasks/*.py` | — | — | — | ✅ | — | — | dirty re-sync 패턴 |
| `chainsight/services/seed_selection.py` | — | — | — | — | — | TTL + DB fallback | LocMemCache → DB SeedSnapshot |
| `sec_pipeline/collector.py` | — | — | — | — | ✅ 별도 구현 | — | requests.RequestException raise |
| `sec_pipeline/extractor.py` | — | ✅ Lazy | — | — | — | — | JSONDecodeError 분기 + raise |
| `sec_pipeline/intelligence.py` | — | ✅ | — | — | — | — | except → severity=critical 기본값 |
| `sec_pipeline/tasks.py` | — | — | — | (간접) | ✅ | — | retry 3/5회 + exp backoff |
| `rag_analysis/services/llm_service.py` | — | ✅ Async | — | — | — | — | **rate/quota/429 분기 + 백오프** ✅ |
| `rag_analysis/services/adaptive_llm_service.py` | — | ✅ Old SDK | — | — | — | — | except → error event |
| `rag_analysis/services/neo4j_driver.py` | — | — | — | ✅ Lazy singleton | — | — | **연결 실패 시 None 반환 + graceful** ✅ |
| `rag_analysis/services/neo4j_service.py` | — | — | — | ✅ | — | — | QUERY_TIMEOUT 적용 |
| `users/cache_utils.py`, `stocks/cache_utils.py` | — | — | — | — | — | ✅ | get/set 직접, fallback 없음 |
| `api_request/cache/decorators.py` | — | — | — | — | — | ✅ | 데코레이터 — except 처리 미흡 |

범례:
- ✅ Core: 직접 사용, 핵심 의존
- ✅ Lazy: lazy-init 패턴
- (간접): 다른 서비스 통해 사용
- — : 사용 안 함

---

## 2. FMP 상세

### 2.1 클라이언트 4종 분산

FMP 호출은 단일 클라이언트가 아닌 **4개의 독립 구현**으로 흩어져 있다. 각자 별도의 rate-limit 카운터, 에러 분기, retry 정책을 갖는다.

| 클라이언트 | 위치 | HTTP 라이브러리 | 에러 분기 | 재시도 | RateLimiter |
|-----------|------|----------------|----------|--------|-------------|
| **FMPClient (정식)** | `api_request/providers/fmp/client.py` | requests | 401/402/403/429 모두 분기 | 3회 + exp backoff | 인스턴스 내부 카운터 |
| **FMPClient (serverless)** | `serverless/services/fmp_client.py` | httpx | HTTPStatusError만 | ❌ | ❌ |
| **FMPClient (macro)** | `macro/services/fmp_client.py` | requests | 일반 raise_for_status | ❌ | 0.5s sleep만 |
| **인라인 httpx** | `stocks/services/fmp_*.py` (5개 파일) | httpx | 401 분기 없음 | ❌ | ❌ |

#### 2.1.1 정식 FMPClient (`api_request/providers/fmp/client.py`)
- HTTP 401 → `FMPAuthError` (재시도 X)
- HTTP 402 → `FMPPremiumError` (재시도 X) ← Premium 심볼 즉시 실패
- HTTP 403 → `FMPAuthError`
- HTTP 429 → `FMPRateLimitError`
- 기타 5xx → `requests.RequestException` 캐치 후 3회 재시도 (2s, 4s, 6s)
- `daily_calls` 인스턴스 카운터 (분산 환경에서 합산 불가)

#### 2.1.2 serverless FMPClient
- 모든 HTTP 에러를 `FMPAPIError`로 wrap
- **402 분기 부재** — Premium 심볼 만나면 일반 에러로 처리
- 재시도 없음 → Celery 태스크에서 retry 3회로 보강 (`serverless/tasks.py:60`)
- 5분 TTL 캐시 사용

#### 2.1.3 macro FMPClient
- 0.5초 간격 sleep만 적용
- HTTP status 분기 없음, `raise_for_status()`만
- **재시도 없음** — 일시 장애 시 즉시 실패
- `macro/tasks.py`의 `update_economic_indicators`는 exponential backoff retry 3회로 부분 보강

#### 2.1.4 인라인 httpx (`stocks/services/fmp_*.py`)
대상: `fmp_fundamentals.py`, `fmp_screener.py`, `fmp_market_movers.py`, `fmp_exchange_quotes.py`, `stock_sync_service.py`
- timeout 10~15초
- HTTPStatusError, TimeoutException 분기 — 둘 다 빈 리스트 반환 (silent failure)
- **401/402/429 모두 동일 처리** — 인증/권한/한도 구분 불가
- API key 없을 시 빈 리스트 반환 (조용히 실패)

### 2.2 Rate Limiter 분산 (3종)

| 정의 위치 | FMP 한도 | 비고 |
|----------|----------|------|
| `api_request/rate_limiter.py:43` | 240/min, 8000/day | Starter 300/min × 0.8 마진 — Redis 기반, 정확 |
| `stocks/services/rate_limiter.py:25` | **10/min, 250/day** | **무료 티어 잔재 (Critical C3) — Starter 미반영** |
| 각 클라이언트 내부 | per-instance sleep | 분산 환경에서 합산 불가 |

`api_request/rate_limiter.py`의 정식 RateLimiter는 FMP 정식 클라이언트와 **연결되어 있지 않다** (`get_rate_limiter("fmp")` 호출 부재). 결과적으로 Redis 기반 분산 카운터는 거의 사용되지 않으며, 각 클라이언트는 자기 자신의 로컬 sleep에만 의존한다.

### 2.3 FMPPremiumError(402) 처리 현황

`FMPPremiumError`를 import하는 파일은 단 4개:

| 파일 | 처리 방식 |
|------|----------|
| `api_request/providers/fmp/client.py` | 정의 위치 |
| `api_request/providers/fmp/provider.py` | balance_sheet/income/cash_flow 각각 catch → `error_code="PREMIUM_ONLY"` 반환 |
| `thesis/views/monitoring_views.py` | 모니터링 응답 분기 |
| `thesis/tasks/eod_pipeline.py:73` | catch → return None |

**커버리지 누락**:
- `stocks/tasks.py:147` `sync_sp500_financials`는 `'.' in symbol`을 사전 필터링하지만, FMP가 새 심볼을 Premium으로 분류 시 raw exception 발생
- `serverless/services/fmp_client.py`는 402를 `FMPAPIError`로 wrap → batch 전체 retry 발생
- `stocks/services/fmp_*.py`는 402가 `httpx.HTTPStatusError`로 일반 처리됨

### 2.4 호출 패턴별 분류

| 카테고리 | 위치 | 빈도 | 위험도 |
|----------|------|------|--------|
| **고빈도 배치** | `stocks/tasks.py` (`sync_sp500_financials`, batch 101 × 5일) | 일 ~500회 | 중 (FMPPremiumError 단순 처리) |
| **고빈도 배치** | `news/tasks.py` (FMP 뉴스 6배치 chord) | 일 ~6 × 84개 = 504회 | **저 (CircuitBreaker 적용)** |
| **고빈도 동기** | `serverless/tasks.py` (`sync_daily_market_movers`) | 일 1회 + 키워드 수집 | 중 |
| **저빈도 동기** | `macro/tasks.py` (`update_market_indices`, 5분마다) | 일 ~100회 | 중 (재시도 없음, Premium 분기 없음) |
| **요청 시점** | `stocks/services/fmp_*.py` (사용자 트리거) | 가변 | **고 (silent failure, 401/402 동일 처리)** |
| **EOD 파이프라인** | `thesis/tasks/eod_pipeline.py` | 일 1회 | 저 (3-task 분리, FMPPremium 분기) |

---

## 3. Gemini 상세

### 3.1 클라이언트 SDK 일관성

`genai.Client` (신 SDK) 사용처: 17개 파일 (대다수)
`google.generativeai` (구 SDK, `genai.configure() + GenerativeModel`) 사용처: **1개**
- `rag_analysis/services/adaptive_llm_service.py:90` — 구 SDK 사용

**문제**: 새 SDK는 동기/비동기 분리(`client.aio`), 토큰 추적, 스트리밍이 통합. 구 SDK는 별도 코드 경로 → 향후 SDK deprecation 시 한 곳만 깨지는 silent regression 위험.

### 3.2 Gemini 호출 지점 — 에러 핸들링 분류

#### Tier 1: Rate-limit/Quota 분기 보유 (1개)
- `rag_analysis/services/llm_service.py:217` `LLMServiceLite.generate_stream`
  - `'rate'/'quota'/'429'` 문자열 매칭으로 분기
  - 백오프 [1, 2, 4]초, 3회 재시도
  - 최종 실패 시 `{'type': 'error'}` event 방출

#### Tier 2: 단순 except → None/빈 결과 (15개)
대상: `news/services/news_deep_analyzer.py`, `news/services/keyword_extractor.py`, `news/services/stock_insights.py`, `news/api/views.py:786`, `serverless/services/llm_relation_extractor.py`, `serverless/services/keyword_generator.py`, `serverless/services/keyword_generator_v2.py`, `serverless/services/keyword_service.py`, `serverless/services/csv_url_resolver.py`, `serverless/services/regulatory_service.py`, `serverless/services/relationship_keyword_enricher.py`, `serverless/services/thesis_builder.py`, `thesis/services/thesis_builder.py:431`, `thesis/services/indicator_matcher.py:197`, `thesis/services/prompt_builder.py` (3 호출), `thesis/views/conversation_views.py:228`, `validation/services/llm_peer_filter.py:79`, `stocks/services/korean_overview_service.py`

**공통 패턴**:
```python
try:
    response = client.models.generate_content(...)
    return parsed_result
except Exception as e:
    logger.error(f"LLM call failed: {e}")
    return None  # 또는 빈 dict / fallback 키워드
```

→ 429 rate limit과 일시 네트워크 오류 구분 불가, 재시도 없음

#### Tier 3: 수동 fallback dict (1개)
- `sec_pipeline/intelligence.py:171` — except 시 `severity='critical'` 기본 응답

#### Tier 4: 재시도 + raise (1개)
- `sec_pipeline/extractor.py:91` — JSONDecodeError 분기 + 그 외는 raise (Celery retry로 처리)

### 3.3 RPM 제한 처리

Gemini 무료 티어 15 RPM 가정으로 **수동 sleep**을 거는 곳:

| 위치 | sleep 간격 | 비고 |
|------|----------|------|
| `news/services/news_deep_analyzer.py:39` | `RPM_DELAY = 4` 초 | 배치 분석마다 |
| `serverless/services/llm_relation_extractor.py:366` | `time.sleep(4)` | 배치 처리마다 |

**문제**:
- Tier 1 1000 RPM 유료 plan으로 업그레이드 시 비효율
- 분산 처리 시 합산 RPM이 한도를 초과할 수 있음 (예: Celery worker 3개 × 15 RPM = 45 RPM)
- `time.sleep`은 Celery worker를 점유 → throughput 저하

### 3.4 응답 파싱 패턴

| 패턴 | 사용처 | 안정성 |
|------|--------|--------|
| `response_mime_type='application/json'` + `json.loads` | `llm_relation_extractor.py`, `sec_pipeline/extractor.py`, `sec_pipeline/intelligence.py`, `validation/llm_peer_filter.py`, `serverless/csv_url_resolver.py` | 높음 — Gemini가 JSON 강제 |
| 정규식 + `json.loads` (코드블록 제거) | `news/services/news_deep_analyzer.py:228`, `rag_analysis/services/llm_service.py` (suggestions 태그) | 중간 |
| 부분 응답 정규식 복구 | `serverless/services/llm_relation_extractor.py:455` `_recover_from_partial_json` | 좋은 fallback |
| 단순 `json.loads` | `validation/services/llm_peer_filter.py:86` | 낮음 — 실패 시 `{'error': ...}` |

### 3.5 Timeout 설정

Gemini SDK 자체 timeout은 **명시적으로 설정된 곳이 없다**. SDK 기본값에 의존 (대부분 60s).
- `rag_analysis/services/neo4j_service.py:118`처럼 Neo4j 쿼리에 `QUERY_TIMEOUT`은 적용되어 있으나, Gemini 호출에는 없음
- 결과: Gemini API 응답 지연 시 Celery worker가 무기한 대기할 수 있음 (`soft_time_limit`만으로 cut-off)

### 3.6 클라이언트 인스턴스 관리

대부분 `__init__`에서 `genai.Client(api_key=api_key)`를 즉시 생성. **싱글톤 미적용**.
- `serverless/services/regulatory_service.py:90` — Lazy initialization (좋음)
- `sec_pipeline/extractor.py:31` — Lazy initialization (Celery fork 안전)
- 기타 — 매 인스턴스 생성마다 새 client → 연결 풀 비효율

---

## 4. 기타 의존성

### 4.1 FRED API (`macro/services/fred_client.py`)

**상태: 양호**

- 공유 `RateLimiter` (`api_request/rate_limiter.py:get_rate_limiter("fred")`) 사용 → Redis 분산 카운터
- HTTP 분기:
  - 401/403/404 → 즉시 raise (영구 에러)
  - 500/502/503/504 → 3회 재시도 (2s, 4s, 6s)
- 한도: 100/min (실제 120/min 중 안전 마진)
- 호출 빈도: `update_economic_indicators` 매시간 7개 시리즈 ≈ 168 calls/day → 한도 충분

**잠재 위험**:
- `_make_request` 내 `requests.exceptions.RequestException` 캐치 시 `RequestException`이 Connection/SSL 등 전체를 포함 → 일시 DNS 오류와 진짜 영구 오류 구분 어려움
- Connection timeout이 30s로 길어 worker 점유 시간 김

### 4.2 Neo4j

3가지 패턴 공존:

| 위치 | 패턴 | 장애 시 동작 |
|------|------|------------|
| `rag_analysis/services/neo4j_driver.py` | Lazy Singleton + 연결 실패 시 None | **앱은 계속 실행 (graceful)** |
| `chainsight/graph/repository.py` | PID 기반 fork-safe driver | `GraphConnectionError` raise |
| `rag_analysis/services/neo4j_service.py` | `QUERY_TIMEOUT` 명시 | 쿼리 타임아웃 시 raise |

**좋은 패턴**:
- `force_reset_after_fork()` (`rag_analysis/services/neo4j_driver.py:102`) — Celery fork 후 부모 driver 참조만 해제 (close 호출 금지) → SIGSEGV 방지
- PID 기반 driver 재생성 (`chainsight/graph/repository.py:38`)

**잠재 위험**:
- `chainsight/services/neo4j_loader.py:123` — `requests.get(url, params=params, timeout=10)`: Neo4j HTTP API 호출에 retry 없음 (단발 다운로드라 영향 작음)
- `chainsight/tasks/neo4j_dirty_sync_tasks.py` — `neo4j_dirty=True` 플래그 패턴은 좋음 (실패 시 다음 sync에서 재처리)

### 4.3 SEC EDGAR

2개 클라이언트 분산:

| 위치 | 용도 | Critical |
|------|------|---------|
| `api_request/sec_edgar_client.py` | 13F holdings, 8K filings, 10K | **C1: 429 시 무한 재귀 (line 166)** |
| `sec_pipeline/collector.py` | SEC pipeline 전용 (10K) | 0.12s sleep, 단순 raise |

#### Critical C1 상세 (`api_request/sec_edgar_client.py:160-166`)
```python
elif response.status_code == 429:
    # Rate limited - wait and retry
    logger.warning("SEC EDGAR rate limited, waiting 1 second...")
    time.sleep(1)
    return self._make_request(url, params, headers, timeout)  # ← 무한 재귀
```
- 재귀 한도 없음 → SEC가 지속 429 시 RecursionError 또는 영구 점유
- 1초 sleep은 SEC 한도(10 req/s) 회복에 부족할 수 있음

**개선 제안 (참고)**: 재시도 카운터 + exponential backoff + 최대 시도 횟수.

#### sec_pipeline/collector.py
- `time.sleep(0.12)` 단발 — 정확한 10 req/s
- HTTP 에러 시 `requests.exceptions.RequestException` raise → Celery `collect_and_extract` task에서 max_retries=3 + 60s exp backoff로 보강
- 분산 환경에서 동시 호출 시 합산 rate가 SEC 한도 초과 가능 (예: worker 3개 동시 = 30 req/s)

### 4.4 Redis (캐시)

대부분 코드는 `django.core.cache`의 `cache.get/set/delete`를 직접 호출. **Redis 다운 시 graceful degrade 패턴 부족**.

#### 좋은 사례 (try/except 처리)
- `news/services/circuit_breaker.py` — record_failure/record_success 모두 try/except (예외 시 로그만)
- `api_request/rate_limiter.py:133` — Redis client 직접 접근 실패 시 Django cache fallback
- `chainsight/services/seed_selection.py:422` — 캐시 + DB SeedSnapshot 영속화 (3단 폴백, 운영용 학습된 패턴)

#### 위험한 사례 (graceful degrade 부재)
- `users/cache_utils.py`, `stocks/cache_utils.py` — `cache.get` 직접
- `api_request/cache/decorators.py` — 데코레이터 내부 `cache.get_or_set`
- `serverless/services/enhanced_screener_service.py`, `market_breadth_service.py`, `sector_heatmap_service.py` — 5분~1시간 TTL 캐시. **캐시 미스 시 일제히 FMP 직접 호출 → cascade 가능**
- `rag_analysis/services/cache.py` — semantic cache, Redis 다운 시 LLM 호출 폭증 가능

#### Redis 의존도 정리
| 의존도 | 사용처 | 영향 |
|--------|--------|------|
| **Critical** | RateLimiter (FMP/FRED 카운터), CircuitBreaker, semantic cache | Redis 다운 → 카운터/breaker 동작 불가 |
| **High** | Screener, Market Movers 캐시 (5~10분 TTL) | 캐시 미스 시 FMP 호출량 폭증 |
| **Medium** | 사용자별 캐시 (`users/cache_utils.py`) | 응답 지연 |
| **Low** | DRF 응답 캐시 | 단순 응답 지연 |

---

## 5. Circuit Breaker 후보

### 5.1 현재 구현 현황

`news/services/circuit_breaker.py:13` `CircuitBreaker` 클래스가 유일.
- threshold 5회, timeout 300s
- Redis 기반 (`circuit:{provider}` 키)
- 적용 호출처: 단 3곳 (`news/tasks.py:924, 1009, 1056` — 모두 FMP 뉴스 수집)

### 5.2 도입 후보 (우선순위 순)

#### P0: FMP 일반 호출 (현재 부분 적용)
| 호출처 | 현재 상태 | 영향 |
|--------|----------|------|
| `stocks/tasks.py:sync_sp500_financials` | breaker 없음, FMP 장애 시 batch 101개 모두 재시도 | 일 502 calls/일 폭증 가능 |
| `serverless/tasks.py:sync_daily_market_movers` | retry 3회만 | Market Movers 페이지 전면 영향 |
| `macro/tasks.py:update_market_indices` (5분마다) | retry 3회만 | Market Pulse 대시보드 staleness |
| `serverless/services/chain_sight_service.py` (요청 시점) | breaker 없음 | 페이지 응답 시간 폭증 |
| `stocks/services/fmp_*.py` (5개, 사용자 트리거) | breaker 없음, silent | 사용자 화면 빈 데이터 |

**제안**: `news/services/circuit_breaker.py`의 `CircuitBreaker('fmp')`를 공유 모듈로 승격 → 위 모든 호출처에 적용.

#### P0: SEC EDGAR (Critical C1과 함께)
- 위치: `api_request/sec_edgar_client.py`, `sec_pipeline/collector.py`
- 영향: SEC 다운 시 `sec_pipeline/tasks.py:collect_and_extract`가 retry 무한 시도 가능
- 제안: 5회 실패 시 5분 차단

#### P1: Gemini API
| 호출처 | 영향 |
|--------|------|
| 16개 동기 호출 지점 (Tier 2) | quota 소진 시 모두 silent failure → 키워드/분석 결과 누락 |
| `news/services/news_deep_analyzer.py:analyze_batch` | 50개 기사마다 4초 대기, quota 시 50회 연속 실패 |
| `serverless/services/llm_relation_extractor.py:extract_batch` | 동일 패턴 |

**제안**: provider="gemini" CircuitBreaker, threshold=10, timeout=60s. 백오프 retry와 조합.

#### P1: FRED API
- 현재 retry 3회로 처리, 한도 충분
- 다만 FRED 장애 시 `update_economic_indicators` 7개 시리즈 모두 실패 → breaker 유용
- 우선순위는 낮음 (호출량 낮음)

#### P2: Neo4j
- 이미 `rag_analysis/services/neo4j_driver.py`가 graceful degrade 패턴 구현
- `chainsight/graph/repository.py`도 `neo4j_dirty` 플래그로 재처리 보장
- breaker 도입 시 마이그레이션 비용 > 이득

### 5.3 설계 제안 요약 (Reference)

```
provider          threshold  timeout   적용 위치
─────────────────────────────────────────────────────────────
fmp               5          300s      모든 FMP 호출처 (현재 news만 적용 → 전체)
gemini            10         60s       16개 LLM 호출 지점
sec_edgar         5          300s      api_request/sec_edgar_client.py
                                       sec_pipeline/collector.py
fred              10         180s      macro/services/fred_client.py
```

---

## 6. 부수 발견사항

### 6.1 일관성 문제 (정보용)

| 문제 | 위치 | 영향 |
|------|------|------|
| FMP 클라이언트 4종 분산 | api_request, serverless, macro, stocks | 유지보수 부담, 정책 불일치 |
| RateLimiter 3종 (각자 한도) | api_request, stocks, 클라이언트 내부 | 분산 환경 카운터 불일치 |
| Gemini SDK 신/구 혼재 | rag_analysis만 구 SDK | deprecation 시 silent break |
| SEC EDGAR 클라이언트 2종 | api_request, sec_pipeline | rate-limit 합산 위험 |
| Gemini timeout 미설정 | 17개 파일 모두 | worker 무기한 점유 가능 |

### 6.2 모니터링/관측성 부재

- FMP/Gemini/Neo4j 호출 메트릭(레이턴시, 실패율, 한도 사용률) 수집 지점 부재
- `api_request/rate_limiter.py:get_status()`는 정의되어 있으나 노출 엔드포인트만 있고 알림/대시보드 미연결
- `news/services/circuit_breaker.py:get_status()` 동일

### 6.3 Auto-Sync 위험

`sync_sp500_financials` (일 502 calls)와 `update_market_indices` (5분마다)는 동일 FMP 한도(8000/day)를 공유하나, 카운터가 분리되어 합산 추적 불가. Peak 시점 한도 초과 시 일부 태스크가 silent fail 후 다음날까지 대기.

---

## 7. 결론 및 권장 우선순위

### Critical (즉시 조치 권장)
1. **C1**: `api_request/sec_edgar_client.py:166` 무한 재귀 — retry 카운터 + 최대 시도 추가
2. **C2**: `serverless/services/fmp_client.py`, `macro/services/fmp_client.py`에 `FMPPremiumError(402)` 분기 추가
3. **C3**: `stocks/services/rate_limiter.py:25` Starter 한도(300/min, 10000/day)로 갱신

### High (1~2주 내)
4. **CircuitBreaker 공유화**: `news/services/circuit_breaker.py`를 `api_request/circuit_breaker.py`로 이동, FMP 모든 호출처에 적용
5. **Gemini quota 분기**: `rag_analysis/services/llm_service.py`의 429 핸들링을 공유 헬퍼로 추출, Tier 2 호출처(15개)에 적용
6. **Gemini timeout 명시**: 모든 `client.models.generate_content` 호출에 `timeout` 파라미터 추가 (기본 30s 권장)

### Medium (1개월 내)
7. **FMP 클라이언트 통합**: 4종 → 1종 (`api_request/providers/fmp/client.py` 단일화)
8. **RateLimiter 통합**: `stocks/services/rate_limiter.py` 제거, `api_request/rate_limiter.py`로 통합 + 모든 클라이언트 연결
9. **Redis 다운 대비**: Critical 캐시 사용처(Screener, Market Movers)에 stale-while-revalidate 또는 in-memory fallback

### Low (관찰 후 결정)
10. Gemini SDK 통일: `rag_analysis/services/adaptive_llm_service.py`를 신 SDK로 마이그레이션
11. SEC EDGAR 클라이언트 2종 통합
12. 호출 메트릭 수집 (Prometheus + Grafana)

---

## 부록: 참조한 핵심 파일

- `api_request/providers/fmp/client.py` (FMP 정식 클라이언트, 492줄)
- `api_request/providers/fmp/provider.py` (FMP Provider 어댑터)
- `api_request/rate_limiter.py` (FMP/FRED 공유 RateLimiter)
- `api_request/sec_edgar_client.py` (SEC EDGAR 정식 클라이언트, **C1 위치**)
- `serverless/services/fmp_client.py` (httpx 기반 별도 클라이언트)
- `macro/services/fmp_client.py` (Market Pulse용 클라이언트)
- `macro/services/fred_client.py` (FRED 클라이언트)
- `stocks/services/rate_limiter.py` (**C3 위치**)
- `stocks/services/fmp_fundamentals.py` 등 5개 인라인 httpx 파일
- `stocks/tasks.py` (sync_sp500_financials, 일 502 calls)
- `serverless/tasks.py` (Market Movers 동기화)
- `news/tasks.py` (CircuitBreaker 적용 사례)
- `news/services/circuit_breaker.py` (현재 유일한 breaker)
- `rag_analysis/services/llm_service.py` (Tier 1: 429 분기 보유)
- `rag_analysis/services/adaptive_llm_service.py` (구 SDK 사용)
- `rag_analysis/services/neo4j_driver.py` (Lazy graceful pattern)
- `chainsight/graph/repository.py` (PID fork-safe driver)
- `sec_pipeline/collector.py` (SEC 별도 구현)
- `sec_pipeline/extractor.py`, `sec_pipeline/intelligence.py` (Gemini 호출)
- `news/services/news_deep_analyzer.py` (Tier 2 LLM 패턴 + 4s sleep)
- `serverless/services/llm_relation_extractor.py` (Tier 2 + 4s sleep + 정규식 fallback)
- `validation/services/llm_peer_filter.py` (Tier 2 LLM 호출)
- `thesis/tasks/eod_pipeline.py` (FMPPremiumError 모범 처리)
