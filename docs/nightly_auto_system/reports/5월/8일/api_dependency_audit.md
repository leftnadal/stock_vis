# 외부 API 의존성 감사 보고서

**작성일**: 2026-05-08
**범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis
**조사 대상**: 약 80개 파일 (FMP 29개·Gemini 27개·기타 ~24개)

---

## 1. 의존성 매트릭스

| 서비스/기능 | 외부 API | 호출 위치 | try/except | Retry | Fallback | Rate Limit | 위험도 |
|---|---|---|---|---|---|---|---|
| 핵심 FMP 클라이언트 | FMP | api_request/providers/fmp/client.py | ✓ (402/429 분리) | ✓ (max_retries=3, exp backoff) | ✗ | ✓ (0.2s delay) | 낮음 |
| Stock 자동 동기화 | FMP | stocks/tasks.py | ✓ (부분) | ✓ (max_retries=3) | ✗ | ✓ (7s countdown) | 중간 |
| S&P500 EOD 가격 동기화 | FMP | stocks/tasks.py | ✓ | ✓ (max_retries=3) | ✗ | ✗ | 중간 |
| S&P500 재무제표 동기화 | FMP | stocks/tasks.py (update_financials_with_provider) | ✓ (부분) | ✗ (rate_limit='6/m') | ✗ | ✗ | 높음 |
| Thesis EOD 지표 fetch | FMP | thesis/tasks/eod_pipeline.py | ✓ (FMPPremiumError, FMPClientError) | ✗ | ✗ | ✗ | 높음 |
| Market Movers 동기화 | FMP | serverless/services/fmp_client.py | ✓ | ✗ | ✓ (Cache hit) | ✓ (5분 캐시) | 중간 |
| Chain Sight DNA | FMP | serverless/services/chain_sight_service.py | ✓ | ✗ | ✓ (Cache) | ✓ (1h 캐시) | 중간 |
| Market Pulse 지수/섹터 | FMP | macro/services/fmp_client.py | ✓ | ✗ | ✓ (None 반환) | ✓ (0.2s delay) | 중간 |
| 키워드 생성 (Celery) | Gemini | serverless/services/keyword_generator.py | ✓ | ✗ | ✗ | ✗ | **치명적** |
| 키워드 생성 v2 (Celery) | Gemini | serverless/services/keyword_generator_v2.py | ✓ | ✗ | ✗ | ✗ | **치명적** |
| RAG LLM 스트리밍 | Gemini | rag_analysis/services/llm_service.py | ✓ (rate/quota 분기) | ✓ (max_retries=3) | ✗ | ✗ | 중간 |
| RAG 엔티티 추출 | Gemini | rag_analysis/services/entity_extractor.py | ✓ | ✗ | ✓ (fallback_extraction) | ✗ | 낮음 |
| Thesis 빌더 (LLM) | Gemini | serverless/services/thesis_builder.py | ✓ | ✗ | ✗ | ✗ | 높음 |
| Thesis 대화 (LLM) | Gemini | thesis/views/conversation_views.py | ✓ (부분) | ✗ | ✗ | ✗ | 높음 |
| LLM Peer 필터 | Gemini | validation/services/llm_peer_filter.py | ✓ | ✗ | ✓ (error dict 반환) | ✗ | 낮음 |
| Portfolio Coach | Gemini+Anthropic | portfolio/llm/client.py | ✓ (분류체계) | ✓ (1회 retry + fallback) | ✓ (provider 교차) | ✓ (Budget Guard) | 낮음 |
| FRED 거시지표 | FRED | macro/services/fred_client.py | ✓ | ✓ (max_retries=3, transient) | ✗ | ✓ (RateLimiter) | 낮음 |
| Thesis FRED 지표 | FRED | thesis/tasks/eod_pipeline.py | ✓ | ✗ | ✗ | ✗ | 중간 |
| Neo4j 그래프 쓰기 | Neo4j | serverless/services/neo4j_chain_sight_service.py | ✓ | ✗ | ✓ (is_available() 확인) | ✗ | 낮음 |
| RAG Neo4j 쿼리 | Neo4j | rag_analysis/services/neo4j_service.py | ✓ (QUERY_TIMEOUT) | ✗ | ✗ | ✗ | 중간 |
| Semantic Cache | Neo4j | rag_analysis/services/semantic_cache.py | ✓ | ✗ | ✗ | ✗ | 중간 |
| SEC 10-K 다운로드 | SEC EDGAR | api_request/sec_edgar_client.py | ✓ | ✓ (429 재귀 1회) | ✗ | ✓ (0.1s/req) | 중간 |
| Redis 캐시 레이어 | Redis | api_request/cache/decorators.py | ✗ (암묵적) | ✗ | ✗ | - | 높음 |
| Redis Rate Limiter | Redis | api_request/rate_limiter.py | ✓ (fallback) | ✗ | ✓ (Django 캐시) | - | 낮음 |
| News Circuit Breaker | Redis | news/services/circuit_breaker.py | ✓ | ✗ | ✓ (CircuitBreaker) | ✗ | 낮음 |
| Market Pulse Circuit Breaker | Redis | marketpulse/utils/circuit_breaker.py | ✓ (tenacity) | ✓ (retry_attempts=3) | ✗ | ✗ | 낮음 |

---

## 2. FMP 상세

### 2.1 핵심 클라이언트 분석

`api_request/providers/fmp/client.py`는 프로젝트의 표준 FMP 클라이언트로 가장 잘 구현되어 있습니다.

**장점**:
- 402 (`FMPPremiumError`), 429 (`FMPRateLimitError`), 401/403 (`FMPAuthError`) 를 각각 별도 예외로 분리
- `FMPPremiumError`/`FMPAuthError`는 재시도 없이 즉시 전파 (`api_request/providers/fmp/client.py:149`)
- 일반 네트워크 오류는 max_retries=3, exponential backoff (2s, 4s) 처리 (`client.py:153-156`)
- `request_delay=0.2s` 로 rate limit 자체 적용, 일일 10,000 카운터 추적 (`client.py:110-112`)

**한계**:
- 일일 카운터는 인스턴스별 메모리 변수 → Celery 워커 다수 기동 시 공유 안 됨 (분산 카운팅 미적용)
- `macro/services/fmp_client.py`, `serverless/services/fmp_client.py` 2개의 독립 FMP 클라이언트가 별도 존재 → **삼중 관리**

### 2.2 호출 지점별 패턴

**api_request/providers/fmp/provider.py** (표준 Provider 래퍼)
- `FMPPremiumError`, `FMPRateLimitError` 각각 분리 처리 (provider.py:86, 123, 169, 208, 247, 254 등)
- 성공 응답만 캐시 (`cached_provider_call` 데코레이터)

**thesis/tasks/eod_pipeline.py** (EOD 파이프라인)
- `FMPPremiumError` → `None, None` 반환 (eod_pipeline.py:144)
- `FMPClientError` → 로그 후 `None, None` 반환 (eod_pipeline.py:147)
- Retry 로직 없음 — 단일 호출 실패 시 해당 지표 값 null로 기록

**stocks/tasks.py** (Stock 자동 동기화)
- `update_stock_with_provider`: 각 단계(stock_data/prices/financials) 개별 try/except, 실패 시 부분 성공 허용 (tasks.py:302-327)
- `update_financials_with_provider`: `@shared_task(rate_limit='6/m')` — Celery 레벨 rate limit. 예외 발생 시 except 없이 로그만 (`tasks.py:535-536`)
- `sync_sp500_constituents`, `sync_sp500_eod_prices`: `max_retries=3` + exponential countdown (tasks.py:418, 445)

**macro/services/fmp_client.py** (Market Pulse 전용)
- retry 없음, 각 메서드에서 `except Exception as e: logger.error(...); return None/{}` 패턴
- `FMPPremiumError` 미처리 → 402 발생 시 일반 Exception으로 처리

**serverless/services/fmp_client.py** (Market Movers 전용)
- httpx 사용 (나머지는 requests), `FMPAPIError` 자체 예외
- 402 처리 없음: `response.raise_for_status()` → `httpx.HTTPStatusError` → `FMPAPIError` 로 변환
- 캐시 우선 (5분 TTL), miss 시 API 호출

### 2.3 발견된 위험

**위험 1: FMP 클라이언트 삼중 분열** (`api_request/providers/fmp/client.py`, `macro/services/fmp_client.py`, `serverless/services/fmp_client.py`)
- 각 클라이언트가 독립 구현 → 동일 버그 3곳에서 따로 수정해야 함
- `macro/services/fmp_client.py`는 402 처리 없음, retry 없음

**위험 2: update_financials_with_provider 실패 무소음**
- `stocks/tasks.py:535` — FMPClientError 포함 모든 예외 로그만 기록, Celery retry 없음
- 재무제표 업데이트 실패가 무음으로 사라짐

**위험 3: Thesis EOD 파이프라인 retry 부재**
- `thesis/tasks/eod_pipeline.py`의 `_fetch_fmp_value()`는 FMP 호출당 retry 없음
- 일시적 503 발생 시 해당 날짜 지표 영구 null 기록

**위험 4: Celery 분산 환경에서 일일 카운터 불일치**
- `FMPClient.daily_calls`가 인스턴스 메모리 변수 → 워커 N개 기동 시 각각 독립 카운팅
- 실제로는 N × 10,000 호출 가능 (의도치 않은 초과)

---

## 3. Gemini 상세

### 3.1 핵심 클라이언트 분석

**rag_analysis/services/llm_service.py (`LLMServiceLite`)**
- `generate_stream()`: async 스트리밍, `max_retries=3`, `RETRY_DELAYS=[1,2,4]`
- rate/quota/429 문자열 감지 → 지수 백오프 후 재시도 (llm_service.py:217-225)
- 기타 예외 → `{'type': 'error', 'message': ...}` yield (graceful degradation)
- timeout 설정 없음 (`types.GenerateContentConfig`에 timeout 미포함)

**portfolio/llm/client.py (`LLMClient`)**
- 가장 완성도 높은 구현: 예외 분류 체계 (`_classify_gemini_error`), 1회 retry + provider 폴백 (Gemini ↔ Anthropic)
- `LLMBudgetExceededError` 비용 가드 (인스턴스별 호출 카운터 + 글로벌 CostGuard)
- timeout 설정 없음

**thesis/services/prompt_builder.py / thesis/services/thesis_builder.py**
- 동기 API (`client.models.generate_content`) 사용 → Celery 호환 (버그 #8 준수)
- `response_mime_type="application/json"` 지정 → JSON 파싱 안전
- `json.JSONDecodeError` catch (prompt_builder.py:590, thesis_builder.py는 regex fallback)

**serverless/services/keyword_generator.py / keyword_generator_v2.py**
- **async def + `aio.models.generate_content` 사용** — Celery 태스크에서 호출 가능성 존재
- `asyncio.get_event_loop()` + `loop.run_until_complete()` 패턴으로 동기 래퍼 존재 (keyword_generator.py:374-377)
- retry 없음, timeout 없음

### 3.2 호출 지점별 패턴

| 파일 | 동기/비동기 | 429 처리 | JSON 파싱 에러 | timeout | retry |
|---|---|---|---|---|---|
| rag_analysis/services/llm_service.py | async | ✓ (문자열 감지) | ✓ | ✗ | ✓ (3회) |
| rag_analysis/services/entity_extractor.py | async | ✗ | ✓ (fallback) | ✗ | ✗ |
| portfolio/llm/client.py | 동기 | ✓ (예외 분류) | N/A | ✗ | ✓ (1회+폴백) |
| serverless/services/thesis_builder.py | 동기 | ✗ | ✓ (regex) | ✗ | ✗ |
| serverless/services/keyword_generator.py | async+loop | ✗ | ✓ | ✗ | ✗ |
| serverless/services/keyword_generator_v2.py | async+loop | ✗ | ✓ | ✗ | ✗ |
| thesis/services/prompt_builder.py | 동기 | ✗ | ✓ | ✗ | ✗ |
| thesis/views/conversation_views.py | 동기 | ✗ | ✗ | ✗ | ✗ |
| news/services/news_deep_analyzer.py | 동기 | ✗ | 미확인 | ✗ | ✗ |
| validation/services/llm_peer_filter.py | 동기 | ✗ | ✓ (error dict) | ✗ | ✗ |

### 3.3 발견된 위험

**위험 1: keyword_generator.py/v2 — Celery에서 asyncio.get_event_loop() 사용**
- `asyncio.get_event_loop()`는 Celery 워커 환경에서 이미 실행 중인 루프가 없으면 `DeprecationWarning` + Python 3.10+ 에러 발생 가능
- `loop.run_until_complete()` 중 이벤트 루프 충돌 위험 (버그 #8 변형)

**위험 2: 대부분의 Gemini 호출에 timeout 미설정**
- Gemini API가 응답 지연 시 Celery soft_time_limit 소진까지 블로킹
- `GenerateContentConfig`에 `request_options=types.RequestOptions(timeout=60)` 미설정

**위험 3: thesis/views/conversation_views.py — 429 및 JSON 파싱 에러 처리 부재**
- 동기 호출이지만 rate limit 예외가 상위로 전파될 경우 HTTP 500 응답

**위험 4: Gemini Free Tier 한도 (15 RPM) 무시**
- 대부분 호출에서 429 이후 재시도 딜레이가 1-4초 수준 → 15 RPM 초과 시 연속 실패 가능
- `RateLimiter`에 Gemini 항목 없음

---

## 4. 기타 의존성

### 4.1 FRED API

**파일**: `macro/services/fred_client.py`, `thesis/tasks/eod_pipeline.py`

`FREDClient._make_request()`:
- 500/502/503/504 → transient으로 분류, max_retries=3, 2s/4s/6s backoff (fred_client.py:114-128)
- 401/403/404 → 즉시 raise (permanent error)
- `get_rate_limiter("fred")` 사용: 분당 100회 제한, 0.6s delay

**`thesis/tasks/eod_pipeline.py`의 `_fetch_fred_value()`**:
- `except Exception` 로 전체를 잡고 `None, None` 반환 — silent failure
- `FREDClient`의 내부 retry는 작동하지만, 키 미설정 시 `None` 반환 후 조용히 실패

**위험**: FRED API 키 없을 때 (`FRED_API_KEY` 미설정) 로그 warning만 발생하고 모든 FRED 의존 지표가 null 처리됨.

### 4.2 Neo4j

**드라이버 초기화** (`rag_analysis/services/neo4j_driver.py`):
- Lazy Singleton: 첫 호출 시 연결 시도, 실패 시 `None` 반환 (앱 사망 없음)
- fork 후 안전한 참조 해제 (`force_reset_after_fork()`) — macOS Celery 버그 대응 완료
- `_connection_attempted` 플래그로 재시도 방지 → 한 번 실패하면 재연결 불가 (주의)

**Neo4jChainSightService** (`serverless/services/neo4j_chain_sight_service.py`):
- 모든 메서드에서 `is_available()` 확인 후 `False` 반환 — graceful degradation
- 각 쿼리 try/except, 실패 시 `False`/`[]` 반환

**rag_analysis/services/neo4j_service.py**:
- 쿼리에 `QUERY_TIMEOUT` 적용 (timeout 설정 확인)
- transaction rollback은 `with session.begin_transaction()` 미사용, 단순 `session.run()` → 자동 롤백 없음

**semantic_cache.py**:
- Neo4j 연결 실패 시 cache miss로 처리 — 기능 저하 없음
- 만료된 캐시 정리 로직 존재

**위험**: `_connection_attempted=True` 이후 Neo4j가 복구되어도 드라이버 재연결 불가. 수동 `reset_connection()` 호출 필요.

### 4.3 SEC EDGAR

**파일**: `api_request/sec_edgar_client.py`

- User-Agent 헤더 설정: `"Stock-Vis/1.0 (contact@stockvis.com)"` (edgar_client.py:108)
- Rate limit 0.1s 간격 (10 req/s) 자체 적용 (edgar_client.py:99-124)
- 429 → `time.sleep(1)` 후 재귀 호출 1회 (edgar_client.py:165-166)
- 403 차단: `SECEdgarError` raise — 상위로 전파, fallback 없음
- 10-K 다운로드 timeout=120s, 13F timeout=60s

**위험**:
- 429 재귀 호출이 중첩되면 무한 재귀 가능 (현실적으로는 1회이나 코드 구조상 취약)
- 403 차단 발생 시 파이프라인 전체 중단 — IP 차단 대응 없음
- CIK 캐시가 인스턴스 메모리 → 인스턴스 재생성 시 매번 전체 JSON 재다운로드

### 4.4 Redis 캐시

**api_request/cache/decorators.py**:
- `cache.get(cache_key)` 실패 (Redis down) 시 예외 전파 가능 → `cached_provider_call` 데코레이터 내부에 try/except 없음
- Redis 미사용 또는 접근 실패 시 `invalidate_provider_cache()` 조용히 실패 (try/except 있음)

**api_request/rate_limiter.py**:
- Redis 직접 접근 실패 시 Django 캐시 fallback (rate_limiter.py:133-138) — graceful

**news/services/circuit_breaker.py**:
- 모든 Redis 접근에 try/except — 서킷 브레이커 자체 장애 시 차단 없음 (열린 상태 유지)

**위험**: `cached_provider_call` 데코레이터는 Redis 장애 시 예외를 잡지 않음 → Redis down = 전체 캐시 레이어 붕괴 → FMP 호출 폭증.

---

## 5. Circuit Breaker 도입 후보

### 우선순위 1 — 치명적 (즉시 도입 권장)

**후보 1: keyword_generator.py / keyword_generator_v2.py (Celery + Gemini)**
- 위치: `serverless/services/keyword_generator.py`, `serverless/services/keyword_generator_v2.py`
- 문제: async 루프 + retry 없음 + Gemini 429 처리 없음
- 영향 범위: Market Movers 키워드 생성 (매일 실행). 실패 시 Celery 워커 블로킹, 이후 태스크 지연
- 권장: Circuit Breaker + 동기 API 전환 (`client.models.generate_content`) + 429 retry

**후보 2: redis 캐시 데코레이터 (cached_provider_call)**
- 위치: `api_request/cache/decorators.py:92-125`
- 문제: Redis 장애 시 예외 전파 → FMP 호출 폭증 → 일일 10,000 한도 소진
- 영향 범위: 전체 FMP 캐싱 레이어 (quote, profile, financial statements 등)
- 권장: try/except로 cache.get 래핑, Redis 장애 시 캐시 miss로 처리하되 FMP 호출 throttle 적용

### 우선순위 2 — 높음

**후보 3: thesis/tasks/eod_pipeline.py (Thesis EOD 파이프라인)**
- 위치: `thesis/tasks/eod_pipeline.py`의 `_fetch_fmp_value()`, `_fetch_fred_value()`
- 문제: 지표별 retry 없음 → 일시 503 = 당일 지표 영구 null
- 영향 범위: Thesis 관제실 전체 스코어링 신뢰도
- 권장: 지표 fetcher에 1-2회 retry 추가 (exponential backoff 1s-2s)

**후보 4: update_financials_with_provider (재무제표 Celery 태스크)**
- 위치: `stocks/tasks.py:510-536`
- 문제: 예외 시 로그만, Celery retry 없음
- 영향 범위: S&P 500 재무제표 데이터 공백
- 권장: `bind=True, max_retries=2` + `raise self.retry(exc=e, countdown=120)` 추가

**후보 5: SEC EDGAR 429 재귀 호출**
- 위치: `api_request/sec_edgar_client.py:165-166`
- 문제: 재귀 횟수 제한 없음
- 권장: 재귀 대신 루프 기반 retry (max 3회)

### 우선순위 3 — 중간

**후보 6: thesis/views/conversation_views.py (Thesis LLM 대화)**
- 429/timeout 처리 없음 → HTTP 500 응답
- 권장: LLM 예외 catch + HTTP 429 응답 반환

**후보 7: neo4j_driver.py 재연결 불가**
- `_connection_attempted=True` 이후 재연결 없음
- 권장: 주기적 헬스 체크 + 자동 재연결 로직 (e.g., Celery Beat 5분마다)

---

## 6. 종합 권장사항

### 액션 아이템 (우선순위 순)

| 번호 | 항목 | 위치 | 담당 | 긴급도 |
|---|---|---|---|---|
| A1 | keyword_generator.py/v2 — 동기 API 전환 + retry 추가 | serverless/services/ | @infra | 즉시 |
| A2 | cached_provider_call — Redis 장애 시 graceful fallback 추가 | api_request/cache/decorators.py | @backend | 즉시 |
| A3 | update_financials_with_provider — Celery retry 복구 | stocks/tasks.py | @infra | 1주 내 |
| A4 | EOD 파이프라인 fetcher — 1-2회 retry 추가 | thesis/tasks/eod_pipeline.py | @infra | 1주 내 |
| A5 | FMP 클라이언트 통합 — macro/serverless FMP 클라이언트를 api_request 표준으로 교체 | macro/, serverless/ | @backend | 2주 내 |
| A6 | Gemini timeout 설정 — 모든 GenerateContentConfig에 RequestOptions(timeout=60) 추가 | 전체 Gemini 호출 | @backend | 2주 내 |
| A7 | SEC EDGAR 재귀 retry → 루프 retry 변환 | api_request/sec_edgar_client.py:165 | @backend | 2주 내 |
| A8 | Neo4j 재연결 자동화 — Celery Beat 헬스 체크 + reset_connection() 연동 | rag_analysis/services/ | @infra | 1개월 내 |
| A9 | Gemini RateLimiter 추가 — rate_limiter.py에 "gemini" 프로바이더 항목 추가 | api_request/rate_limiter.py | @backend | 1개월 내 |
| A10 | FMP 일일 카운터 Redis 공유 — 분산 환경 카운팅을 Redis INCR로 전환 | api_request/providers/fmp/client.py | @backend | 1개월 내 |

### 현황 요약

- **잘 구현된 영역**: `api_request/providers/fmp/client.py` (표준 예외 계층), `portfolio/llm/client.py` (폴백+비용 가드), `macro/services/fred_client.py` (transient retry), `rag_analysis/services/neo4j_driver.py` (lazy singleton + fork 대응)
- **즉시 위험 영역**: keyword_generator asyncio 패턴 (버그 #8 변형), cached_provider_call Redis 의존성
- **구조적 기술 부채**: FMP 클라이언트 삼중 분열 (api_request/macro/serverless), Circuit Breaker가 news/marketpulse에만 존재 (serverless/thesis/stocks에 미적용)
- **Circuit Breaker 현황**: `news/services/circuit_breaker.py`와 `marketpulse/utils/circuit_breaker.py` 2개 독립 구현 존재. 핵심 파이프라인 (EOD, Thesis, S&P500 재무제표)에는 미적용.
