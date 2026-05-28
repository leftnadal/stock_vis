# 외부 API 의존성 감사 보고서

- 감사일: 2026-05-28
- 범위: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis (캐시)
- 모드: 읽기 전용 (코드 수정 없음)
- 산출물: 의존성 매트릭스 + provider별 상세 + Circuit Breaker 후보

---

## 0. 요약 (Executive)

| 항목 | 상태 |
|------|------|
| FMP 클라이언트 구현체 수 | **3종 중복** (`api_request`, `serverless`, `macro`) — 표준화 안 됨 |
| Gemini Client 직접 호출 지점 | 약 **29 파일** (전부 `genai.Client(api_key=...)` 직접 인스턴스화) |
| Circuit Breaker 커버리지 | FMP 5종, Gemini 3종, Neo4j 1종 — **나머지 약 20개 호출 지점 무방어** |
| 402 (FMPPremium) 처리 | `api_request/providers/fmp` 전용. 다른 2개 클라이언트는 미처리 |
| 429 (Rate limit) 일관성 | provider별 처리 패턴 상이 (raise/log/retry 혼용) |
| JSON 파싱 실패 처리 | 일부만 `json.JSONDecodeError` 처리 + 정규식 복구. 다수 `except Exception` 단일 catch |
| Timeout 설정 | FMP `requests/httpx timeout=30`. Gemini SDK 호출에는 **명시적 timeout 없음** |

핵심 리스크 3건:
1. **FMP 클라이언트 3종이 분기되어 있어** 장애 대응 패턴(retry/CB/402)이 일관되지 않음
2. **Gemini 호출 다수에 CB·timeout 부재** — 단일 장애가 EOD 파이프라인 전체 지연 가능
3. **Redis 장애 시 graceful degradation 없음** — `circuit_breaker`, `cache`, `rate_limiter`가 모두 Redis 의존 (LocMemCache는 test에서만)

---

## 1. 의존성 매트릭스

### 서비스 × 외부 API × 방어 패턴

| 서비스 / 모듈 | FMP | Gemini | FRED | Neo4j | SEC | Redis(cache) | Retry | CB | Fallback |
|--------------|-----|--------|------|-------|-----|--------------|-------|----|----|
| `api_request/providers/fmp/client.py` | ✓ | – | – | – | – | – | 3회 exp | – | 402→`PREMIUM_ONLY` 응답 |
| `api_request/providers/fmp/provider.py` | ✓ (래퍼) | – | – | – | – | – | – | – | 402→error_response |
| `api_request/sec_edgar_client.py` | – | – | – | – | ✓ | – | (확인 필요) | – | – |
| `api_request/rate_limiter.py` | ✓(FMP/FRED RateLimiter) | – | ✓ | – | – | ✓ (counter store) | – | – | Django 캐시 fallback |
| `serverless/services/fmp_client.py` | ✓ (별도 구현) | – | – | – | – | ✓ (TTL 60s~24h) | – | 호출자 측 | – |
| `serverless/services/data_sync.py` | ✓ | – | – | – | – | – | – | `fmp_market_movers` (5/120s) | CB open → 빈 리스트 |
| `serverless/services/keyword_service.py` | – | ✓ (sync) | – | – | – | – | 429 시 2/4/6s 백오프 | – | – |
| `serverless/services/keyword_generator.py` | – | ✓ (sync+async) | – | – | – | – | – | – | – |
| `serverless/services/keyword_generator_v2.py` | – | ✓ (async) | – | – | – | – | – | – | – |
| `serverless/services/thesis_builder.py` | – | ✓ (sync) | – | – | – | – | – | – | – |
| `serverless/services/llm_relation_extractor.py` | – | ✓ (sync) | – | – | – | – | – | – | JSON 정규식 복구 |
| `serverless/services/regulatory_service.py` | – | ✓ (lazy init) | – | – | – | – | – | – | – |
| `serverless/services/relationship_keyword_enricher.py` | – | ✓ | – | – | – | – | – | – | – |
| `serverless/services/csv_url_resolver.py` | – | ✓ (lazy) | – | – | – | – | – | – | LLM 실패 → None |
| `serverless/services/neo4j_chain_sight_service.py` | – | – | – | ✓ | – | – | – | `neo4j_cb` (CB 헬퍼) | driver None → False |
| `serverless/services/institutional_holdings_service.py` | – | – | – | – | – | – | (402 표기 grep) | – | – |
| `serverless/services/cusip_mapper.py` | ✓ | – | – | – | – | – | (402 표기 grep) | – | – |
| `stocks/services/sp500_service.py` | ✓ (datahub CSV) | – | – | – | – | – | – | `fmp_sp500_constituents` (3/300s) | – |
| `stocks/services/sp500_eod_service.py` | ✓ | – | – | – | – | – | – | `fmp_sp500_eod` (10/120s) | – |
| `stocks/services/korean_overview_service.py` | – | ✓ (sync) | – | – | – | – | – | – | – |
| `stocks/tasks.py` | ✓ (via service) | – | – | – | – | – | Celery 3 retry | (provider 내부) | `.` 심볼 사전 제외 |
| `macro/services/fmp_client.py` | ✓ (별도 구현) | – | – | – | – | – | – | – | 호출자 측 `except Exception` |
| `macro/services/fred_client.py` | – | – | ✓ | – | – | – | 3회 (500/502/503/504) | – | 401/403/404 즉시 raise |
| `macro/services/macro_service.py` | ✓ (via fmp_client) | – | ✓ | – | – | ✓ (TTL realtime/daily/monthly) | – | – | cache fallback |
| `news/providers/fmp.py` | ✓ (FMPClient 위임) | – | – | – | – | – | – | – | parse 실패 시 빈 리스트 |
| `news/tasks.py` | ✓ | – | – | – | – | – | Celery retry | `news.services.circuit_breaker.CircuitBreaker('fmp')` (5/300s) | open→batch skip |
| `news/services/keyword_extractor.py` | – | ✓ (sync) | – | – | – | – | – | – | – |
| `news/services/news_deep_analyzer.py` | – | ✓ (sync) | – | – | – | – | – | – | `_analyze_single`→None |
| `news/services/stock_insights.py` | – | ✓ (sync) | – | – | – | – | – | – | – |
| `news/api/views.py` | – | ✓ (inline) | – | – | – | – | – | – | parse 실패 → 예외 |
| `marketpulse/briefing/client.py` | – | ✓ (sync) | – | – | – | – | tenacity 3회 (CB 내부) | `gemini` (5/60s) | CB open → 예외 전파 |
| `marketpulse/fetchers/fmp_weights.py` | ✓ | – | – | – | – | – | tenacity (CB 내부) | `fmp_etf` | – |
| `marketpulse/services/news_aggregator.py` | ✓ (FMP+Marketaux) | – | – | – | – | – | tenacity (CB 내부) | `fmp_news`, `marketaux` | provider_unavailable 표기 |
| `marketpulse/utils/circuit_breaker.py` | – | – | – | – | – | ✓ (state store) | tenacity 3회 | (자체) | – |
| `rag_analysis/services/llm_service.py` | – | ✓ (async stream) | – | – | – | – | 3회 (1/2/4s) | `gemini_rag` (5/60s, retry_attempts=1) | CB open → 에러 메시지 yield |
| `rag_analysis/services/context_compressor.py` | – | ✓ (async) | – | – | – | – | – | `gemini_compress` (5/60s) | – |
| `rag_analysis/services/adaptive_llm_service.py` | – | ✓ (legacy `genai.configure`) | – | – | – | – | – | – | – |
| `rag_analysis/services/entity_extractor.py` | – | ✓ (async) | – | – | – | – | – | – | – |
| `thesis/services/thesis_builder.py` | – | ✓ (sync) | – | – | – | – | – | `gemini_thesis` (5/120s) | CB open → `_fallback_parse` |
| `thesis/services/prompt_builder.py` | – | ✓ (sync, 3곳) | – | – | – | – | – | – | None 반환 |
| `thesis/services/indicator_matcher.py` | – | ✓ (sync) | – | – | – | – | – | – | – |
| `thesis/tasks/summary.py` | – | ✓ (sync) | – | – | – | – | – | – | – |
| `thesis/tasks/eod_pipeline.py` | ✓ (`FMPPremiumError` import) | – | – | – | – | – | – | – | – |
| `thesis/views/monitoring_views.py` | ✓ | – | – | – | – | – | – | – | – |
| `thesis/views/conversation_views.py` | – | ✓ (inline) | – | – | – | – | – | – | except → exception log |
| `validation/services/llm_peer_filter.py` | – | ✓ (sync) | – | – | – | – | – | – | `{'error': str}` 반환 |
| `sec_pipeline/extractor.py` | – | ✓ (lazy, sync) | – | – | – | – | – | – | JSONDecodeError → 빈 dict; 그 외 raise |
| `sec_pipeline/intelligence.py` | – | ✓ (sync) | – | – | – | – | – | – | – |
| `portfolio/llm/client.py` | – | ✓ + Anthropic | – | – | – | – | 1회 (RateLimit/Timeout만) | – | gemini→anthropic fallback, 예외 분류 (`_classify_gemini_error`) |

> **읽는 법**: ✓ = 호출함, – = 무관/없음, CB 컬럼은 회로 이름과 (failure_threshold/recovery_seconds).
> 정확한 카운트가 아닌 코드 경로 기준 매핑이므로, 일부 간접 호출은 매트릭스에서 누락될 수 있습니다.

### 핵심 결손 패턴

1. FMP 클라이언트 **3종 분기** — 각자 다른 에러/retry/CB 패턴
2. Gemini 호출의 ~70%가 단순 `try/except Exception` 만으로 보호
3. Redis 자체가 `cache`/`circuit_breaker`/`rate_limiter` 모두의 백엔드 — Redis 다운 시 fallback이 LocMemCache로 자동 전환되지 않음

---

## 2. FMP 상세

### 2.1 구현체 매핑

| 위치 | HTTP 라이브러리 | 에러 클래스 | Retry | CB | 일일 카운터 |
|------|--------------|------------|-------|----|----|
| `api_request/providers/fmp/client.py` | `requests` | FMPClientError, FMPRateLimitError, FMPAuthError, **FMPPremiumError** | 3회 exp backoff `(attempt+1)*2` | – | 인메모리 (`self.daily_calls`), 클라이언트 재기동 시 리셋 |
| `serverless/services/fmp_client.py` | `httpx.Client(timeout=30)` | `FMPAPIError` 단일 | – | 호출자 측 (data_sync) | – |
| `macro/services/fmp_client.py` | `requests` | (자체 클래스 없음 → `requests.exceptions`+`ValueError`) | – | – | – |
| `news/providers/fmp.py` | (FMPClient 위임) | – | – | (호출 wrap) | – |

**문제**: 동일 외부 API에 대해 3개의 클라이언트가 존재하고 각각 다른 에러 모델/방어 패턴을 사용. 운영에서 FMP 장애 시 어느 경로가 어떻게 실패하는지 예측 어려움.

### 2.2 HTTP 상태 코드 처리 매트릭스

| Status | `api_request/.../client.py` | `serverless/.../fmp_client.py` | `macro/.../fmp_client.py` |
|--------|----------------------------|--------------------------------|---------------------------|
| 401 | `FMPAuthError` | `FMPAPIError` (HTTP 에러) | raise_for_status |
| 402 | **`FMPPremiumError`** ✓ | `FMPAPIError` (HTTP 에러) | raise_for_status |
| 403 | `FMPAuthError` | `FMPAPIError` | raise_for_status |
| 429 | `FMPRateLimitError` (즉시 raise, 재시도 X) | `FMPAPIError` | raise_for_status |
| 5xx | retry × 3 (exponential) | `FMPAPIError` (no retry) | raise_for_status (no retry) |
| `{"Error Message": ...}` | parse + 분기 | `FMPAPIError` | `ValueError` |

> KB 버그 #23 (FMP 402 즉시 실패 + `.` 심볼 배치 제외) 패턴은 `api_request` 경로에만 적용되어 있음. `serverless` / `macro` 경로에서 BRK.B 같은 심볼 호출 시 동작 미정.

### 2.3 Rate Limit 처리

- 권장: `api_request/rate_limiter.py` 의 `RateLimiter("fmp")` — Redis incr 기반, 안전 마진 80% (240/min, 8000/day).
- 실제 사용처:
  - `api_request/providers/fmp/client.py`: **자체 `request_delay=0.2s`만 사용**. RateLimiter는 사용 안 함.
  - `serverless/services/fmp_client.py`: rate limiting 없음 (cache TTL만)
  - `macro/services/fmp_client.py`: `request_delay=0.2s` 자체 처리
  - `macro/services/fred_client.py`: `get_rate_limiter("fred")` 사용 ✓
- **공통 RateLimiter가 FMP에 전혀 적용되지 않음** — 단일 인스턴스가 빠르게 호출해도 분산 환경 보호 없음.

### 2.4 Circuit Breaker 커버리지

| CB 이름 | 위치 | failure_threshold | recovery_seconds | 비고 |
|--------|------|-------------------|------------------|------|
| `fmp_market_movers` | `serverless/services/data_sync.py:74` | 5 | 120 | CB open → 빈 리스트로 진행 |
| `fmp_sp500_constituents` | `stocks/services/sp500_service.py:38` | 3 | 300 | – |
| `fmp_sp500_eod` | `stocks/services/sp500_eod_service.py:131` | 10 | 120 | – |
| `fmp_etf` | `marketpulse/fetchers/fmp_weights.py:48` | (기본 5) | (기본 60) | tenacity 3회 |
| `fmp_news` | `marketpulse/services/news_aggregator.py:106` | (기본 5) | (기본 60) | – |
| `news.services.circuit_breaker.CircuitBreaker('fmp')` | `news/tasks.py:926,1012,1056` | 5 | 300 | 별도 구현 (marketpulse.utils.CB 아님) |

> ⚠️ `news/tasks.py`는 `news.services.circuit_breaker`의 **간이 CB** 사용. `marketpulse.utils.circuit_breaker`(HALF_OPEN 지원 + tenacity)와 다른 두 구현이 공존.

### 2.5 결손 지점 (FMP 호출 있음 + CB 없음)

- `serverless/services/keyword_data_collector.py`
- `serverless/services/sector_heatmap_service.py`
- `serverless/services/chain_sight_service.py`
- `serverless/services/cusip_mapper.py`
- `serverless/services/filter_engine.py`
- `serverless/services/market_breadth_service.py`
- `serverless/services/enhanced_screener_service.py`
- `macro/services/macro_service.py`
- `macro/services/fmp_client.py` 전체 (지수/섹터/원자재/환율 등 시장 데이터 일괄)
- `stocks/services/sp500_service.py` 외 FMP 호출 메서드 (S&P EOD만 CB 적용)

→ 시장 시간(09:30~16:00 EST) 동시 호출 시 FMP 장애 시 위 경로 전부 cascading 가능.

---

## 3. Gemini 상세

### 3.1 클라이언트 초기화 패턴 (3종 공존)

| 패턴 | 파일 수 | 예시 |
|------|--------|------|
| `genai.Client(api_key=...)` 인스턴스 멤버 | ~13 | `rag_analysis/llm_service.py:64`, `news/services/news_deep_analyzer.py:53`, `serverless/services/keyword_service.py:75` |
| `genai.Client(api_key=...)` 함수 내 inline 생성 | ~10 | `thesis/services/prompt_builder.py:558,781,959`, `validation/services/llm_peer_filter.py:72`, `marketpulse/briefing/client.py:44` |
| Lazy init (`self._client is None` 패턴) | 2 | `sec_pipeline/extractor.py:24-31`, `serverless/services/regulatory_service.py:90`, `serverless/services/csv_url_resolver.py:157` |
| Legacy `genai.configure(api_key=...)` + `GenerativeModel` | 1 | `rag_analysis/services/adaptive_llm_service.py:91` |
| `google.generativeai as genai_module` 별도 import | 1 | `marketpulse/briefing/client.py:40` |

**문제**: 신/구 SDK 혼재(`google.genai` vs `google.generativeai`), inline 생성 다발 — 키 누락/네트워크 장애 시 동일한 실패 처리 보장 불가.

### 3.2 에러 처리 패턴 분류

| 패턴 | 파일 수 | 예시 |
|------|--------|------|
| `except Exception as e: logger.error(...) → 폴백/None` | 다수 | `news_deep_analyzer.py:146-148`, `csv_url_resolver.py:407-409`, `llm_peer_filter.py:88-90` |
| `except Exception → raise` (전파) | 일부 | `sec_pipeline/extractor.py:89-91, 143-145`, `llm_relation_extractor.py:415` |
| `if 'rate' in error.lower() → retry` | 2 | `keyword_service.py:317-322`, `rag_analysis/llm_service.py:248-260` |
| CB + tenacity 사용 | 5 | `rag_analysis/llm_service.py`(CB), `context_compressor.py`(CB), `thesis_builder.py`(CB), `briefing/client.py`(CB), `rag_analysis/adaptive_llm_service.py` 일부 |
| 통합 예외 매핑 (`_classify_gemini_error`) | 1 | `portfolio/llm/client.py:62-80` + Anthropic fallback |

### 3.3 JSON 응답 파싱

`response_mime_type='application/json'` 설정 여부:

| 사용 | 파일 |
|------|------|
| ✓ | `sec_pipeline/extractor.py`, `validation/services/llm_peer_filter.py`, `serverless/services/llm_relation_extractor.py` (외 일부), `thesis/services/prompt_builder.py` |
| ✗ (텍스트로 받아서 정규식 / replace 후 parse) | `serverless/services/keyword_service.py:344-369`, `thesis/services/thesis_builder.py:475-479`, `news/services/news_deep_analyzer.py` |

`JSONDecodeError` 명시적 catch:
- 처리: `sec_pipeline/extractor.py:86,140`, `llm_relation_extractor.py:448` (정규식 복구), `prompt_builder.py:590`
- 미처리(generic Exception에 합쳐짐): 대다수

### 3.4 Timeout

- Gemini SDK 호출 전반에 **명시적 timeout 설정 없음** (`max_output_tokens`만 지정).
- `marketpulse/briefing/client.py`는 latency 측정용 `time.time()` 기록뿐.
- Gemini 응답 지연 시 Celery worker 점유 가능 — `CELERY_WORKER_MAX_TASKS_PER_CHILD=100`만으로는 단일 작업 행 위험.

### 3.5 429 처리

| 위치 | 처리 |
|------|------|
| `serverless/services/keyword_service.py:317-322` | `'rate' in err / 'quota' / '429'` 문자열 매칭 → 2/4/6초 백오프 |
| `rag_analysis/services/llm_service.py:248-260` | 동일 패턴 + `RETRY_DELAYS=[1,2,4]` |
| `portfolio/llm/client.py:_classify_gemini_error` | 클래스명/메시지 기반 분류 → `LLMRateLimitError` |
| 그 외 다수 | 처리 없음 — `generic Exception`으로 흡수 |

→ Gemini Free Tier 한도(15 RPM/1500 RPD) 도달 시 응답 패턴이 일관되지 않음.

### 3.6 Circuit Breaker 커버리지 (Gemini)

| CB 이름 | 위치 | failure_threshold | recovery_seconds |
|--------|------|-------------------|------------------|
| `gemini_rag` | `rag_analysis/services/llm_service.py:198` | 5 | 60 |
| `gemini_compress` | `rag_analysis/services/context_compressor.py:136,288` | 5 | 60 |
| `gemini_thesis` | `thesis/services/thesis_builder.py:459` | 5 | 120 |
| `gemini` | `marketpulse/briefing/client.py:67` | (기본 5) | (기본 60) |

→ 위 4종 외 모든 Gemini 호출은 CB 미적용. 특히 EOD/NIGHTLY 파이프라인에서 사용되는 `serverless/services/keyword_service.py`, `keyword_generator.py`, `llm_relation_extractor.py`, `regulatory_service.py`, `csv_url_resolver.py`, `news/services/news_deep_analyzer.py`, `sec_pipeline/extractor.py`, `validation/services/llm_peer_filter.py`, `thesis/services/prompt_builder.py` (3곳), `thesis/services/indicator_matcher.py`, `thesis/tasks/summary.py`, `stocks/services/korean_overview_service.py` 가 무방어.

---

## 4. 기타 의존성

### 4.1 FRED API (`macro/services/fred_client.py`)

- ✓ `get_rate_limiter("fred")` 사용 (100/min, 안전 마진)
- ✓ 401/403/404 즉시 raise
- ✓ 500/502/503/504 transient retry (3회, 2/4/6s)
- ✗ CB 없음 — 다만 사용 빈도가 낮고 무료 티어 한도가 여유로워 우선순위 낮음
- ✗ 호출자(`macro_service.py`)는 cache TTL로 부분 보호

### 4.2 Neo4j

- ✓ `serverless/services/neo4j_chain_sight_service.py`: CB(`neo4j_cb`) + `_run_with_cb` 헬퍼
- ✓ `is_available()` 가 CB 상태까지 확인하여 silent failure 차단
- ✓ `get_neo4j_driver()` None 시 fallback mode (logger.warning)
- ⚠ `chainsight/tasks/` (별도 경로) — 본 grep 범위 외, 추가 확인 필요
- ⚠ 운영 메모: 1573 노드/12695 관계 (project_operations_infra_2026-05)

### 4.3 SEC EDGAR (`api_request/sec_edgar_client.py`)

- 자체 rate limit 0.1s 간격 (10 req/s)
- 사용자-에이전트 요구 사항 처리 (확인 필요)
- 별도 에러 클래스 `SECEdgarError`
- ✗ CB 없음 — 무료, 잘 실패하지 않으나 회사 정보 수집 차단 가능

### 4.4 Redis (캐시 백엔드)

- `config/settings.py:499`: `django.core.cache.backends.redis.RedisCache` (`redis://127.0.0.1:6379/1`)
- Redis 의존 구조:
  - `marketpulse/utils/circuit_breaker.py` — CB 상태/카운터 저장 (`cache.get/set/incr/add`)
  - `news/services/circuit_breaker.py` — 별도 구현, 동일 캐시 사용
  - `api_request/rate_limiter.py` — 카운터(`cache._cache.get_client().pipeline().incr().expire()`)
  - `serverless/services/fmp_client.py`, `macro/services/macro_service.py` — TTL 캐시
- **Redis 다운 시 영향**:
  - CB 상태 유실 → 모든 호출이 일단 시도됨 → cascading 가능
  - Rate limiter는 일부 `cache._cache.get_client()` 접근 실패 시 Django 캐시 fallback(`cache.set`) 처리 (rate_limiter.py:133)
  - 그러나 fallback 자체도 `cache` 호출이므로 백엔드가 Redis면 동시 실패
- `settings_test.py`에서만 LocMemCache 격리. 운영 fallback 없음.

---

## 5. Circuit Breaker 도입 후보

장애 시 전체 시스템 영향이 큰 호출 지점을 우선순위별로 식별.

### 우선순위 1 (Critical — 단일 장애 → 파이프라인 중단)

| # | 위치 | 사유 | 권장 CB 이름 | 권장 임계 |
|---|------|------|--------------|---------|
| 1 | `serverless/services/keyword_service.py:_call_llm_sync` | 키워드 생성 핵심, Celery 매일 호출, 429 백오프 6초 후 raise | `gemini_keyword` | 5/120s |
| 2 | `serverless/services/keyword_generator.py` / `keyword_generator_v2.py` | 키워드 v2 파이프라인 | `gemini_keyword_v2` | 5/120s |
| 3 | `serverless/services/llm_relation_extractor.py` | Chain Sight LLM Relations, 무방어 | `gemini_relation` | 5/120s |
| 4 | `news/services/news_deep_analyzer.py` | News Intelligence v3 Tier A/B/C, batch 처리 시 cascade | `gemini_news_deep` | 5/120s |
| 5 | `sec_pipeline/extractor.py` (supply_chain + business_model) | SEC 10-K 추출, raise 전파로 작업 실패 | `gemini_sec` | 5/120s |
| 6 | `macro/services/fmp_client.py` 전체 | Market Pulse / 메인 페이지 사용, CB 전혀 없음 | `fmp_market_pulse` | 5/120s |

### 우선순위 2 (High — 사용자 경험 직접 영향)

| # | 위치 | 사유 |
|---|------|------|
| 7 | `thesis/services/prompt_builder.py` (3 곳) | Thesis 대화형 빌더, 사용자 입력 즉시 응답 |
| 8 | `thesis/services/indicator_matcher.py` | 지표 매칭 |
| 9 | `thesis/views/conversation_views.py:228-280` | 뉴스→가설 변환 |
| 10 | `validation/services/llm_peer_filter.py` | Peer 필터 LLM, 1차 검증 핵심 |
| 11 | `news/api/views.py:801` | inline Gemini 호출, view 핸들러에서 직접 |
| 12 | `serverless/services/fmp_client.py` | get_quote/historical/profile 등 핵심 — `data_sync` 외 경로는 무방어 |

### 우선순위 3 (Medium — 백그라운드 작업)

| # | 위치 | 사유 |
|---|------|------|
| 13 | `serverless/services/regulatory_service.py` | Regulatory, lazy init |
| 14 | `serverless/services/relationship_keyword_enricher.py` | enrichment |
| 15 | `serverless/services/csv_url_resolver.py` | ETF CSV URL 추출, None fallback 존재 |
| 16 | `stocks/services/korean_overview_service.py` | 한국어 overview |
| 17 | `thesis/tasks/summary.py` | 일일 요약 task |
| 18 | `sec_pipeline/intelligence.py` | SEC intelligence |

### 추가 권장 사항 (CB 외 개선)

1. **FMP 클라이언트 통합** — 3종 구현을 `api_request/providers/fmp/client.py` (FMPPremiumError 보유)로 통일하고 `serverless`, `macro` 호출처에서 import 변경.
2. **공통 Gemini wrapper 도입** — `portfolio/llm/client.py` 의 `_classify_gemini_error` 패턴을 공유 모듈(`shared/llm_client.py` 등)로 추출해 모든 호출에서 timeout/CB/예외 분류 일관화.
3. **Redis HA / LocMemCache fallback** — Redis 다운 시 `CACHES['default']` 자동 LocMemCache로 degrade 하는 wrapper.
4. **Rate limiter를 FMP `api_request/providers/fmp/client.py`에 적용** (현재 자체 0.2s 슬립만 사용 → 분산 환경 보호 부재).
5. **Gemini 호출에 timeout 명시** — SDK 차원의 timeout 옵션(가능하다면)을 통일 적용. 가능치 않다면 호출 wrapper에서 `concurrent.futures.ThreadPoolExecutor` + timeout.
6. **CB 구현 통일** — `marketpulse.utils.circuit_breaker` (HALF_OPEN + tenacity)와 `news.services.circuit_breaker` (간이) 중 전자로 일원화.

---

## 부록 A. 참고 파일 인덱스

- FMP 클라이언트: `api_request/providers/fmp/client.py:80`, `serverless/services/fmp_client.py:51`, `macro/services/fmp_client.py:78`
- Gemini 호출 진입점 (대표): `rag_analysis/services/llm_service.py:198-244`, `serverless/services/keyword_service.py:264-330`, `marketpulse/briefing/client.py:47-68`, `portfolio/llm/client.py:240-277`
- CB 코어: `marketpulse/utils/circuit_breaker.py:39-159`, `news/services/circuit_breaker.py:13-74`
- Rate limiter: `api_request/rate_limiter.py:60-230`
- 캐시 설정: `config/settings.py:499-504` (Redis), `config/settings_test.py:27` (LocMem)

## 부록 B. 감사 범위 외 / 후속 확인 필요

- `chainsight/tasks/` 전수 (이번 grep 범위 밖)
- `sec_pipeline/intelligence.py` 의 LLM 호출 흐름 상세
- Anthropic 클라이언트(`portfolio/llm/client.py`)는 Gemini fallback 역할이므로 본 감사에서 보조 처리
- 다른 외부 API: marketaux, finnhub, USPTO (`uspto_client.py`) — `news/providers/`, `serverless/services/uspto_client.py` 에 분포
