# 외부 API 의존성 감사 보고서

- 작성일: 2026-05-14
- 작업 형태: **읽기 전용 감사 (코드 미변경)**
- 대상: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis, Anthropic, Alpha Vantage
- 조사 범위: 64+ 파일 (FMP 호출 23 + Gemini 호출 23 + 기타 의존성)
- 핵심 결론
  1. **FMP 클라이언트가 3개로 분기**되어 에러 핸들링이 일관되지 않음 (Premium/RateLimit 처리 누락 다수)
  2. **Gemini 23개 호출 지점 중 단 1곳만 재시도 구현** (`serverless/services/keyword_service.py`)
  3. **Circuit Breaker 인프라는 이미 존재**(`marketpulse/utils/circuit_breaker.py`)하나, **marketpulse Briefing 1곳에서만 사용 중**
  4. SEC EDGAR / Redis / 대부분의 Gemini 경로가 무방비 — 장애 시 사용자/태스크 전면 중단 위험

---

## 의존성 매트릭스 (서비스별 외부 API × fallback 유무)

| 의존성 | 호출 지점 수 | 통합 클라이언트 | 재시도 표준화 | Timeout 명시 | Fallback 표준 | Circuit Breaker | 보호 등급 |
|--------|-------------|---------------|-------------|-------------|--------------|----------------|----------|
| **FMP** | 23 caller | ✗ (3개 분기) | 부분 (1개 클라만 retry) | ✓ 30s | ✗ 불일치 | ✗ | **C** (낮음) |
| **Gemini** | 23 caller | ✗ (각자 `genai.Client`) | ✗ (1/23) | ✗ | ✗ 불일치 | ✓ marketpulse 1곳만 | **D** (취약) |
| **FRED** | 1 client (`macro/services/fred_client.py`) | ✓ 단일 | ✓ 3회 + 지수 백오프 | ✓ 30s | ✓ 빈 dict | ✗ | **B** (양호) |
| **Neo4j** | 3 client (rag_analysis, chainsight, graph_analysis) | 부분 (rag_analysis는 lazy singleton) | ✗ | ✓ 2s query / 60s connect | ✓ empty data | ✗ | **B** (양호) |
| **SEC EDGAR** | 1 client (`api_request/sec_edgar_client.py`) + collector | ✓ 단일 | 부분 (429만 1회) | ✓ 30~120s | ✗ (raise) | ✗ | **C** (낮음) |
| **Redis** | django.core.cache 전역 | ✓ Django backend | ✗ | ✗ | 부분 (rate_limiter만 fallback) | ✗ | **C** (낮음) |
| **Anthropic** | 1 client (`portfolio/llm/client.py`) | ✓ 단일 | ✓ 1회 + 폴백 to Gemini | ✗ (SDK default) | ✓ Gemini 폴백 + CostGuard | ✗ | **B** (양호) |
| **Alpha Vantage** | 제거됨 (마이그레이션 완료) | - | - | - | - | - | N/A |

> **등급 기준**
> A: retry + timeout + fallback + circuit 모두 보유
> B: 3/4 보유, 단일 클라이언트 통합
> C: 2/4 보유, 일부 누락
> D: 1/4 이하, 다중 분기 + 표준 없음

---

## FMP 상세

### 클라이언트 분기 현황

| # | 파일 | 라이브러리 | 에러 계층 | 재시도 | 캐시 | Premium(402) | Rate Limit(429) | Daily 카운터 |
|---|------|----------|---------|-------|------|--------------|-----------------|------------|
| 1 | `api_request/providers/fmp/client.py` | `requests` | `FMPClientError`/`FMPAuthError`/`FMPRateLimitError`/`FMPPremiumError` | ✓ 3회 + exp backoff | ✗ | ✓ 즉시 raise | ✓ 명시 클래스 | ✓ 10000/일 |
| 2 | `serverless/services/fmp_client.py` | `httpx` | `FMPAPIError` 단일 | ✗ | ✓ Django cache (5분~24시간) | ✗ (HTTP에러로 흡수) | ✗ (HTTP에러로 흡수) | ✗ |
| 3 | `macro/services/fmp_client.py` | `requests` | `ValueError` 변환 | ✗ | ✗ | ✗ | ✗ | ✗ |

> 동일한 외부 API에 대해 **3가지 에러 계층(FMPClientError vs FMPAPIError vs ValueError)** 공존 → caller 측에서 어떤 예외를 잡을지 일관성 부재.

### Caller 측 패턴 (호출 지점 23개 요약)

| 파일 | 사용 클라이언트 | Premium 처리 | RateLimit 처리 | Fallback | 부분실패 허용 |
|------|---------------|-------------|----------------|----------|-------------|
| `stocks/tasks.py` | serverless | ✗ | ✗ | DB 캐시 | ✓ |
| `stocks/services/sp500_service.py` | serverless | ✗ | ✗ | 빈 결과 | ✓ |
| `stocks/services/sp500_eod_service.py` | serverless | ✗ | ✗ | Celery retry | ✓ |
| `stocks/views_search.py` | api_request | ✗ | ✗ | 빈 결과 | ✓ |
| `api_request/providers/fmp/provider.py` | api_request | ✓ | ✓ | RateLimitError 전파 | ✓ |
| `api_request/stock_service.py` | api_request | ✗ | ✗ | `call_with_fallback` | 부분 |
| `serverless/tasks.py` | serverless | ✗ | ✗ | Celery retry | ✓ |
| `serverless/services/data_sync.py` | serverless | ✗ | ✗ | 빈 데이터 | ✓ |
| `serverless/services/sector_heatmap_service.py` | serverless | ✗ | ✗ | 빈 결과 | ✓ |
| `serverless/services/filter_engine.py` | serverless | ✗ | ✗ | 캐시/빈 결과 | ✓ |
| `serverless/services/enhanced_screener_service.py` | serverless | ✗ | ✗ | 캐시 | ✓ |
| `serverless/services/market_breadth_service.py` | serverless | ✗ | ✗ | 빈 데이터 | ✓ |
| `serverless/services/cusip_mapper.py` | serverless | ✗ | ✗ | DB 조회 | ✓ |
| `serverless/services/chain_sight_service.py` | serverless | ✗ | ✗ | 빈 결과 | ✓ |
| `serverless/services/keyword_data_collector.py` | serverless | ✗ | ✗ | 캐시 | ✓ |
| `serverless/services/neo4j_chain_sight_service.py` | serverless | ✗ | ✗ | Neo4j 우회 | ✓ |
| `serverless/views.py` | serverless | ✗ | ✗ | 캐시/빈 결과 | ✓ |
| `news/providers/fmp.py` | serverless | ✗ | ✗ | 빈 뉴스 | ✓ |
| `news/services/aggregator.py` | serverless | ✗ | ✗ | 다중 공급자 | ✓ |
| `macro/services/macro_service.py` | macro | ✗ | ✗ (ValueError) | 기본값 | ✓ |
| `thesis/tasks/eod_pipeline.py` | api_request | ✓ | ✗ | 부분 처리 | ✓ |
| `thesis/views/monitoring_views.py` | api_request | ✓ | ✗ | 폴백 | ✓ |
| `marketpulse/services/news_aggregator.py` | 혼합 | ✗ | ✗ | 다중 공급자 | ✓ |

### FMP 안티패턴 (5개)

1. **클라이언트 3분기**: 동일 API에 대해 `FMPClient`/`FMPClient`/`FMPClient` 이름이 같으면서 다른 모듈에 공존 — caller가 import 경로에 따라 다른 동작.
2. **Premium(402) 명시 처리 누락 (20/23 caller)**: `thesis/`와 `api_request/provider.py` 외 모든 caller가 `FMPPremiumError`를 별도 처리하지 않음. `.` 포함 심볼(BRK.B, BF.B 등)은 [common-bugs.md #23] 정책에 따라 사전 제외해야 하지만 caller 다수가 누락.
3. **Rate Limit(429) 대응 누락 (serverless 전체)**: 429 응답 처리 없음. Starter Plan 300 calls/min을 caller 측에서 보장하지 못함 — 동시 Celery 워커가 다중 호출 시 침해 가능.
4. **Fallback 일관성 부재**: 캐시 → 빈 결과 → 기본값 → 재시도 우선순위가 파일마다 다름. 실시간 조회 경로(views)는 fallback 자체가 없는 곳도 존재.
5. **Daily 한도 인식 분기**: `api_request` 클라이언트만 `daily_calls` 카운터 보유. `serverless`/`macro`는 일일 한도 침해 시 무방비.

### FMP 클라이언트 통일 평가

- `serverless` 클라이언트가 httpx + Django 캐시 통합으로 가장 견고하지만, `api_request` 클라이언트의 에러 계층(`FMPPremiumError`/`FMPRateLimitError`)이 더 정교.
- **권고**: `serverless`의 캐시 전략 + `api_request`의 에러 계층을 결합한 **단일 `FMPClient`로 통합**. 마이그레이션 비용 ≈ 2~3일, 안정성 이득 큼.
- 통합 전까지 차선책: 모든 serverless caller 측에 최소한 `try/except FMPAPIError`를 추가하고, response status_code 402/429를 Inner `FMPAPIError.upstream_status`로 노출.

---

## Gemini 상세

### 호출 지점별 패턴 (23개 파일 표)

| 파일 | 클라이언트 인스턴스화 | 재시도 | timeout | JSON 파싱 | fallback | circuit |
|------|------------------|-------|--------|----------|---------|---------|
| `thesis/services/prompt_builder.py` | 매 호출마다 직접 | ✗ | ✗ | try/json + except | None 반환 | ✗ |
| `thesis/services/indicator_matcher.py` | 매 호출마다 직접 | ✗ | ✗ | regex + json | 키워드 매칭 | ✗ |
| `thesis/services/thesis_builder.py` | __init__ | ✗ | ✗ | json + except | ValueError raise | ✗ |
| `thesis/tasks/summary.py` | 직접 | ✗ | Celery soft 300s | 광범위 try | 빈 문자열 | ✗ |
| `thesis/views/conversation_views.py` | 직접 (2회) | ✗ | ✗ | json + except | 제목 기반 폴백 | ✗ |
| `serverless/services/thesis_builder.py` | __init__ | ✗ | ✗ | json + except | ValueError raise | ✗ |
| `serverless/services/keyword_generator.py` | __init__ | ✗ | ✗ | parser 메서드 | 기본 키워드 배열 | ✗ |
| `serverless/services/keyword_generator_v2.py` | __init__ | ✗ | ✗ | parser 메서드 | 빈 배열 | ✗ |
| `serverless/services/keyword_service.py` | __init__ | **✓ 2회 (429/quota)** | ✗ | regex + json | FALLBACK_KEYWORDS | ✗ |
| `serverless/services/regulatory_service.py` | Lazy init | ✗ | ✗ | (키워드 매칭만) | None | ✗ |
| `serverless/services/llm_relation_extractor.py` | __init__ | ✗ | ✗ | json + except | 빈 relations | 부분 (Redis 1h TTL 캐시) |
| `serverless/services/relationship_keyword_enricher.py` | __init__ | ✗ | ✗ | json | fallback 메서드 | ✗ |
| `serverless/services/csv_url_resolver.py` | Lazy 조건부 | ✗ | ✗ | (없음) | regex 매칭 | ✗ |
| `news/services/keyword_extractor.py` | __init__ | ✗ | ✗ | json + except | FALLBACK_KEYWORDS | ✗ |
| `news/services/news_deep_analyzer.py` | __init__ | ✗ | RPM_DELAY=4s | json | None | ✗ |
| `news/services/stock_insights.py` | (간접) | N/A | N/A | N/A | 캐시 폴백 | ✗ |
| `news/api/views.py` | (간접) | ✗ | ✗ | N/A | 빈 데이터 | ✗ |
| `rag_analysis/services/llm_service.py` | __init__ | ✓ 3회 (rate 감지) | ✗ | (stream) | 에러 yield | ✗ |
| `rag_analysis/services/adaptive_llm_service.py` | `_init_client()` | ✗ | ✗ | (없음) | genai=None 처리 | ✗ |
| `rag_analysis/services/context_compressor.py` | __init__ 조건부 | ✗ | ✗ | (없음) | truncate 폴백 | ✗ |
| `rag_analysis/services/entity_extractor.py` | __init__ 조건부 | ✗ | ✗ | json + except | 규칙 기반 폴백 | ✗ |
| `sec_pipeline/extractor.py` | Lazy `_get_client` | ✗ | ✗ | json + except | ValueError raise | ✗ |
| `validation/services/llm_peer_filter.py` | 직접 | ✗ | ✗ | json + except | error dict | ✗ |
| `stocks/services/korean_overview_service.py` | __init__ | ✗ | ✗ | json + except | ValueError raise | ✗ |
| `marketpulse/briefing/client.py` | `_build_client()` | (CB 내부) | ✗ | ✗ | CB 폴백 | **✓ `get_circuit('gemini')`** |
| `portfolio/llm/client.py` | per-call | ✓ 1회 + Anthropic 폴백 | ✗ | ✗ | LLMResponse 폴백 | ✗ |

### Gemini 안티패턴 (6개)

1. **클라이언트 인스턴스화 비일관**: 매 호출 직접(`thesis/prompt_builder`, `validation/llm_peer_filter`), `__init__` 1회(대부분), Lazy(`regulatory_service`, `sec_pipeline/extractor`), 조건부(`rag_analysis/context_compressor`) — 4가지 패턴 혼재. 공유 클라이언트 부재.
2. **재시도 미흡 (1/23만 구현)**: `keyword_service.py`만 429/quota 감지 시 2회 지수 백오프. `rag_analysis/llm_service.py`는 스트리밍 경로에서 3회. 나머지 21개는 무재시도 → 일시적 429에 즉시 사용자 영향.
3. **Timeout 부재**: 명시적 timeout 설정이 거의 없음 (Celery soft_limit과 RPM_DELAY 외). Gemini API 기본 동작에 의존 → 장기 무응답 가능성.
4. **JSON 파싱 패턴 분산**: `json.loads` 직접 / regex + json / parser 메서드 / 파싱 자체 없음 — 동일 응답이 caller마다 다르게 해석. 파싱 실패 시 행동(raise vs 빈 반환)도 불일치.
5. **Fallback 정책 비표준**: FALLBACK_KEYWORDS, 빈 배열, None, ValueError raise, 제목 기반, 규칙 기반, 캐시 — 7가지 fallback 전략 혼재. 사용자 UX 일관성 결여.
6. **Circuit Breaker는 marketpulse 1곳만**: 인프라(`marketpulse/utils/circuit_breaker.py`) 존재 — Redis 기반 OPEN/HALF_OPEN/CLOSED, tenacity 통합. 그런데 22개 caller가 미사용.

### 기존 Circuit Breaker 인프라 활용 가능성

`marketpulse/utils/circuit_breaker.py:132`의 `get_circuit(name, failure_threshold, recovery_seconds, retry_attempts)`는 이미 production-ready:

- Redis 기반 분산 상태 (Celery 워커 간 공유 가능)
- `tenacity` 통합 (`Retrying`, `wait_exponential`, `stop_after_attempt`)
- HALF_OPEN 상태로 자가 회복 시도
- `name`별 등록부(`_REGISTRY`)로 재사용 보장

→ 코드 미변경 권고지만, **재구현 불필요**. 향후 도입 시 `get_circuit('gemini')`, `get_circuit('fmp')`, `get_circuit('sec_edgar')`만 추가하면 됨.

---

## 기타 의존성

### FRED API (보호 등급 **B**)

- 위치: `macro/services/fred_client.py` 단일
- 재시도: 3회 + 지수 백오프 (2s/4s/6s)
- Timeout: 30s 고정
- Rate Limiter: `get_rate_limiter("fred")` (분당 100회)
- Transient(500-504) vs Permanent(401-403, 404) 구분 처리
- 데이터 빈 값('.', None) 파싱 처리

→ 외부 의존성 중 **가장 견고**. Circuit breaker는 옵션 (현재 보호 충분).

### Neo4j (보호 등급 **B**)

- 위치: `rag_analysis/services/neo4j_driver.py`(Lazy Singleton) + `chainsight/services/neo4j_sync.py`
- 인스턴스화: 첫 사용 시 초기화, 실패 시 `None` 반환 + `_connection_attempted` 플래그로 재시도 차단
- Timeout: 2000ms (쿼리), 60s (연결)
- Pool: `max_connection_lifetime=3600`, `pool_size=50`
- Fork 안전성: `force_reset_after_fork()` (Celery macOS [common-bugs.md #25] 대응)
- Fallback: 모든 쿼리에서 empty data 반환 (`Neo4jServiceLite`가 None 드라이버 대응)

→ Lazy + per-query fallback 패턴이 양호. 다만 **재시도가 드라이버 connection pool 수준**에만 있고 caller 레벨 retry는 없음.

### SEC EDGAR (보호 등급 **C**)

- 위치: `api_request/sec_edgar_client.py` + `sec_pipeline/collector.py`
- 재시도: 429에만 1회 + 1s sleep — **부족** (일반 5xx에는 retry 없음)
- Timeout: 30~120s (문서 크기별)
- User-Agent: 필수 (`Stock-Vis/1.0`) — 위반 시 SEC 차단
- Rate Limit: 0.1s 간격 = 10 req/sec (명시적)
- Fallback: 404/4xx → `SECEdgarError` raise (caller가 처리)

→ caller(특히 `sec_pipeline/intelligence.py`)에서 raise를 받으면 **10-K 파싱 전체 중단**. Supply Chain extraction의 단일 장애점.

### Redis (보호 등급 **C**)

- 설정: `redis://127.0.0.1:6379/1` (`django.core.cache.backends.redis.RedisCache`)
- 재시도/Timeout/Circuit: ✗ 없음
- Fallback: `api_request/rate_limiter.py`만 메모리 캐시 폴백 (나머지는 캐시 미스 → 직호출)

**Redis 장애 영향**:
- 모든 캐시 미스 → FMP/Gemini API 직호출 폭증 (Daily 한도 위협)
- Channels WebSocket layer 의존 — 채널 메시지 송수신 불가
- Circuit Breaker 자체가 Redis 기반 — Redis 장애 시 CB도 동작 불가 (메타 의존성 문제)

### Anthropic API (보호 등급 **B**)

- 위치: `portfolio/llm/client.py` 단일
- 재시도: 1회 + Gemini로 자동 폴백 (`LLMRateLimitError`/`LLMTimeoutError` 한정)
- 비용 가드: `CostGuard.get_instance()` + `LLM_BUDGET_MAX_CALLS`
- 에러 분류: `_classify_anthropic_error()` (RateLimitError/APITimeoutError/AuthenticationError 매핑)
- Timeout: SDK 기본값 의존 — 명시 없음

→ Portfolio Coach 전용 사용. 폴백이 Gemini로 일방향 — Gemini도 동시 장애 시 fallback 없음.

### Alpha Vantage

- **제거 완료** (마이그레이션 보고서: `docs/migration/alpha-vantage-usage-report.md`)
- 현재 FMP 단독 사용 — 12초 대기 패턴 잔존 흔적 없음

---

## Circuit Breaker 후보 (우선순위)

### 1순위 — `Gemini` (광범위, 보호 없음)

- **이유**: 23개 caller 중 22개가 무재시도/무CB. 429 quota 도달 시 모든 LLM 기능 동시 실패.
- **대상 caller (장애 영향 큰 순)**:
  1. `serverless/services/keyword_service.py` (S&P 500 키워드 생성 — Market Movers 의존)
  2. `serverless/services/llm_relation_extractor.py` (Chain Sight 관계 추출 — 이미 캐시 보호 부분)
  3. `news/services/news_deep_analyzer.py` (News Intelligence Pipeline)
  4. `thesis/services/thesis_builder.py` (가설 빌더 대화 흐름)
  5. `rag_analysis/services/llm_service.py` (RAG 응답 스트리밍)
- **권고 설정**: `get_circuit('gemini', failure_threshold=5, recovery_seconds=120, retry_attempts=2)`

### 2순위 — `FMP` (광범위, 일일 한도 위험)

- **이유**: 23개 caller, 클라이언트 3분기, Daily 한도(10000) 침해 시 모든 데이터 동기화 중단.
- **대상 caller (장애 영향 큰 순)**:
  1. `serverless/tasks.py` (`sync_daily_market_movers` + `calculate_daily_market_breadth`) — 매일/30분
  2. `stocks/services/sp500_eod_service.py` (S&P 500 500개 종목 일일 동기화)
  3. `serverless/services/sector_heatmap_service.py` (대시보드 직결)
  4. `stocks/tasks.py` (`sync_sp500_constituents`)
  5. `marketpulse/services/news_aggregator.py` (뉴스 집계)
- **권고 설정**: `get_circuit('fmp', failure_threshold=10, recovery_seconds=300, retry_attempts=3)` — 일일 한도와 분리된 별도 한도 카운터 병행 필요.

### 3순위 — `SEC EDGAR` (단일 장애점, 보호 없음)

- **이유**: 10-K 파싱 caller가 즉시 raise를 받음. Supply Chain extraction 전체 중단.
- **대상**: `sec_pipeline/collector.py`, `sec_pipeline/extractor.py`, `sec_pipeline/intelligence.py`
- **권고 설정**: `get_circuit('sec_edgar', failure_threshold=2, recovery_seconds=300, retry_attempts=2)` + 캐시 fallback

### 4순위 — `Redis` (메타 의존성, 부분 보호)

- **이유**: 모든 캐시/CB/WebSocket의 기반. 장애 시 API 호출 폭증.
- **현재 보호**: rate_limiter 메모리 폴백만
- **권고**: CB로 보호하는 것보다 **circuit_breaker.py 자체의 Redis 의존성을 분리**하는 것이 우선 (in-memory fallback 추가). Redis 장애를 CB로 잡으면 자기참조 문제 발생.

### 비후보 (보호 충분)

- **FRED**: 자체 retry + rate_limiter 보유
- **Neo4j**: Lazy + per-query fallback이 사실상 CB 역할
- **Anthropic**: Gemini 폴백 + CostGuard로 충분
- **Alpha Vantage**: 제거됨

---

## 부록 — 권고 요약 (코드 미변경, 후속 작업 제안)

1. **FMP 클라이언트 통합 (slice 우선순위 P0)**: `serverless` 캐시 전략 + `api_request` 에러 계층 결합, 단일 모듈로 마이그레이션. 마이그레이션 비용 2~3일.
2. **Gemini 공유 클라이언트 + 표준 retry 데코레이터 (slice 우선순위 P0)**: `@with_gemini_retry(attempts=3, backoff='exp')` 데코레이터 신설, 23개 caller에 점진 적용.
3. **Circuit Breaker 도입 (slice 우선순위 P1)**: `marketpulse/utils/circuit_breaker.py` 재사용. `gemini`/`fmp`/`sec_edgar` 3개 회로 추가.
4. **Fallback 정책 표준화 (slice 우선순위 P1)**: 필수 데이터(키워드, 시세) → 캐시 → 기본값; 선택 데이터(LLM 추론) → None or 부분 결과. 매뉴얼 문서화.
5. **Redis 자기참조 해결 (slice 우선순위 P2)**: Circuit Breaker의 in-memory fallback 추가, Redis 장애 시에도 CB 동작 보장.
6. **모니터링 보강 (slice 우선순위 P2)**: 각 의존성별 health check endpoint를 `metrics/services/`에 추가. 실패율/회복시간 추적.

---

> 본 보고서는 읽기 전용 감사 결과이며, 모든 변경은 별도 PR을 통해 진행할 것을 권고함.
> 관련 KB: `shared_kb/search "FMP"`, `shared_kb/search "Gemini" --type troubleshoot`
> 관련 버그: common-bugs.md #8 (Celery async), #14 (FMP 필드명), #23 (FMP Premium 402), #25 (Celery macOS)
