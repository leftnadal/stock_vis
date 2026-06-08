# 외부 API 의존성 감사 보고서

> **작성일**: 2026-06-08
> **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis / 뉴스 API(Finnhub·Marketaux) 장애 대응
> **유형**: 읽기 전용 감사 (코드 수정 없음)
> **방법**: 정적 코드 분석 (호출 지점 전수 + 에러 핸들링 패턴 추적)

---

## 0. 요약 (Executive Summary)

| 항목 | 상태 |
|------|------|
| **이미 존재하는 방어 인프라** | `packages/shared/api_request/circuit_breaker.py` (tenacity 기반 CircuitBreaker + 재시도) — FMP·LLM·News·Neo4j 일부 경로에 적용 |
| **가장 큰 구멍** | **Gemini LLM 호출 ~20개 파일에서 429(rate limit) 미처리** + **모든 LLM 호출에 timeout 미설정** |
| **숨은 SPOF** | CircuitBreaker 상태를 **Redis(`django.core.cache`)에 저장** → Redis 장애 시 CB 계층 자체가 동작 불능 |
| **모범 사례** | Neo4j (Lazy 싱글톤 + 빈 데이터 fallback), FRED (exponential backoff + 상태코드 분류), 뉴스 API (CB + 빈 리스트) |
| **레거시 정리 대상** | Alpha Vantage (enum만 잔존, 실호출 없음) |

**핵심 권고 3가지 (우선순위 순)**:
1. **LLM 호출에 공통 timeout + 429 백오프 래퍼 도입** — 현재 야간 파이프라인이 Gemini 429/무응답에 무방비.
2. **CircuitBreaker의 Redis 의존성 graceful 처리** — Redis 장애가 CB를 통해 전체 파이프라인으로 전파되지 않도록.
3. **FMP 메인 경로(provider/stock_service/tasks)에 CB 미적용** — sp500/movers 경로는 CB 있으나 단건 종목 갱신 경로는 Celery retry만 존재.

---

## 1. 의존성 매트릭스

서비스(호출 지점)별 외부 API 의존성과 방어 수단 요약. 기호: ✅ 충분 / ⚠️ 부분 / ❌ 없음 / N/A 해당없음

| 서비스 / 호출 지점 | 외부 API | 에러 catch | Fallback | 재시도 | Timeout | Circuit Breaker | 장애 영향 |
|---|---|---|---|---|---|---|---|
| `api_request/providers/fmp/client.py` | FMP | ✅ (402/429/401/403 분류) | ❌ (예외 전파) | ✅ 3회 backoff | ✅ 30s | ❌ | 단건 호출 실패 전파 |
| `api_request/providers/fmp/provider.py` | FMP | ✅ | ⚠️ error_response | ❌ | (client) | ❌ | 부분 실패 |
| `api_request/stock_service.py` | FMP | ✅ success 체크 | ✅ fallback chain | ✅ task 3회 | (client) | ❌ | 부분 갱신 허용 |
| `stocks/tasks.py` (단건 종목/재무) | FMP | ✅ continue | ⚠️ 부분누적 | ✅ max_retries=3 | (client) | ❌ | 부분 실패 |
| `stocks/services/sp500_service.py` | FMP | ✅ | ✅ 빈 dict | (CB) | (client) | ✅ | graceful skip |
| `stocks/services/sp500_eod_service.py` | FMP | ✅ | ⚠️ 최소 Stock 생성 | (CB) | (client) | ✅ | 부분 실패 |
| `serverless/services/data_sync.py` (Movers) | FMP | ✅ | ✅ 빈 리스트 | (CB) | (client) | ✅ | 부분 실패 |
| `market_pulse/fetchers/fmp_weights.py` | FMP | ✅ | ⚠️ | (CB) | (client) | ✅ | graceful |
| `news/providers/fmp.py` + `aggregator.py` | FMP/Finnhub/Marketaux | ✅ | ✅ 빈 리스트 + provider 폴백 | ❌ | ✅ | ✅(tasks) | graceful |
| `market_pulse/services/macro_service.py` | FRED + FMP | ✅ | ✅ 기본값(50/neutral) | (client) | (client) | ❌ | graceful degradation |
| `rag_analysis/services/llm_service.py` | Gemini | ✅ | ✅ 에러 yield | ✅ 3회 + 429 backoff | ❌ | ✅ | graceful |
| `rag_analysis/services/context_compressor.py` | Gemini | ✅ | ✅ truncate | (CB) | ❌ | ✅ | graceful |
| `rag_analysis/services/entity_extractor.py` | Gemini | ✅ JSONDecode | ✅ regex 규칙 | ❌ | ❌ | ❌ | graceful |
| `thesis/services/thesis_builder.py` | Gemini | ✅ JSONDecode | ✅ 규칙 파서 | (CB) | ❌ | ✅ | graceful |
| `thesis/services/prompt_builder.py` | Gemini | ✅ JSONDecode | ✅ None | ❌ | ❌ | ❌ | graceful |
| `thesis/services/indicator_matcher.py` | Gemini | ✅ JSONDecode | ✅ 빈 리스트 | ❌ | ❌ | ❌ | graceful |
| `thesis/tasks/summary.py` (Celery) | Gemini | ✅ | ✅ 빈 문자열 | ❌ | ❌ | ❌ | graceful |
| `serverless/services/keyword_generator.py` | Gemini | ✅ | ✅ 폴백 키워드 | ❌ | ❌ | ❌ | graceful |
| `serverless/services/keyword_generator_v2.py` | Gemini | ✅ | ✅ 빈 리스트 | ❌ | ❌ | ❌ | graceful |
| `serverless/services/keyword_service.py` (Celery) | Gemini | ✅ JSONDecode | ✅ 폴백 키워드 | ✅ 2회 + 429 backoff | ❌ | ❌ | graceful |
| `serverless/services/llm_relation_extractor.py` | Gemini | ✅ JSONDecode | ✅ 빈 관계 | ❌ | ❌ | ❌ | graceful |
| `serverless/services/regulatory_service.py` | Gemini | ✅ JSONDecode | ✅ 빈 배열 | ❌ | ❌ | ❌ | graceful |
| `serverless/services/csv_url_resolver.py` | Gemini | ✅ | ✅ None | ❌ | ❌ | ❌ | graceful |
| `news/services/news_deep_analyzer.py` (Celery) | Gemini | ✅ JSONDecode | ✅ None | ❌ | ❌ | ❌ | graceful |
| `news/services/keyword_extractor.py` (Celery) | Gemini | ✅ JSONDecode | ✅ FALLBACK_KEYWORDS | ❌ | ❌ | ❌ | graceful |
| `news/services/stock_insights.py` | Gemini | ✅ JSONDecode | ⚠️ 원본 유지 | ❌ | ❌ | ❌ | graceful |
| `sec_pipeline/extractor.py` | Gemini | ✅ JSONDecode | ✅ error/빈값 | ❌ | ❌ | ❌ | graceful |
| `sec_pipeline/intelligence.py` | Gemini | ✅ JSONDecode | ✅ 기본 JSON | ❌ | ❌ | ❌ | graceful |
| `validation/services/llm_peer_filter.py` | Gemini | ✅ | ✅ {"error":...} | ❌ | ❌ | ❌ | graceful |
| `portfolio/llm/client.py` | Gemini(+Anthropic) | ✅ 분류 | ✅ 반대 provider 폴백 | ✅ 1회 | ❌ | ❌ | graceful |
| `market_pulse/briefing/client.py` (Celery) | Gemini | ❌ (전파) | ❌ | (CB) | ❌ | ✅ | CB로 격리 |
| `stocks/services/korean_overview_service.py` | Gemini | ✅ JSONDecode | ❌ (예외 전파) | ❌ | ❌ | ❌ | **호출자로 전파** |
| `sec_pipeline/collector.py` | SEC EDGAR | ✅ | ✅ edgartools 폴백 | ✅ Celery backoff | ✅ 15~60s | ❌ | graceful |
| `rag_analysis/services/neo4j_*.py` | Neo4j | ✅ | ✅✅ 빈 데이터 | ⚠️ retry=1 | ✅ 2s | ✅ | graceful |
| `serverless/services/neo4j_chain_sight_service.py` | Neo4j | ✅ | ✅ 빈 데이터 | (CB) | ✅ | ✅ | graceful |
| 전 앱 `cache.get/set` | Redis | ✅ (대부분) | ⚠️ 암묵적 None | N/A | N/A | N/A | 성능 저하 |

---

## 2. FMP 상세

### 2.1 클라이언트 계층 — `providers/fmp/client.py` (모범)

`FMPClient._make_request()`는 방어가 잘 갖춰져 있음:

- **상태코드 분류** (L129-143): 401→`FMPAuthError`, 402→`FMPPremiumError`, 403→`FMPAuthError`, 429→`FMPRateLimitError`, 그 외 비-200→`raise_for_status()`
- **재시도** (L122-170): `max_retries=3`, exponential backoff `(attempt+1)*2`초. 단, `FMPPremiumError`/`FMPAuthError`/`FMPRateLimitError`는 **재시도 없이 즉시 전파** (L156-157) — 올바른 설계.
- **Rate limit** (L103-115): `request_delay=0.2s` 간격 강제 + 일일 카운터 10,000 도달 시 `FMPRateLimitError`.
- **Timeout** (L124): 30초 고정.
- **FMP "Error Message" dict 응답** (L148-152) 처리.

> ⚠️ **주의**: 일일 카운터(`self.daily_calls`)는 **인스턴스 메모리**에 저장. 워커가 매 태스크마다 새 클라이언트를 만들면 카운터가 공유되지 않아 일일 한도 보호가 사실상 무력화됨. 또한 분당 300 calls(Starter) 제한에 대한 **슬라이딩 윈도우 카운터는 없음** — `request_delay=0.2s`(=최대 300/분)로 간접 방어할 뿐, 병렬 워커가 동시에 호출하면 초과 가능.

### 2.2 변형 클라이언트 — 이원화 문제

- `serverless_client.py`: **httpx 기반** 별도 구현. 예외를 모두 `FMPAPIError`로 통일 전파, **재시도 없음**.
- `market_pulse_client.py`: **requests 기반** 또 다른 구현. `request_delay=0.2`, 재시도 없음.

> ⚠️ **3개의 서로 다른 FMP 클라이언트 구현 공존** (`client.py` requests / `serverless_client.py` httpx / `market_pulse_client.py` requests). 402/429 처리 로직이 제각각 → 일관성 위험. 통합 클라이언트 권고.

### 2.3 서비스/태스크 계층

- `stock_service.py`: `call_with_fallback()`로 provider 체인 폴백. 프로필 실패 시 **기존 Stock 객체 반환**(L219), 가격/재무는 부분 갱신 허용 → graceful.
- `stocks/tasks.py`:
  - `update_stock_with_provider`: `max_retries=3, countdown=60`
  - `sync_sp500_constituents` / `sync_sp500_eod_prices`: `max_retries=3, countdown=300*(retries+1)`
  - 개별 종목 실패는 `try/except → log → continue`로 격리.
- **CB 적용**: sp500/sp500_eod/data_sync(Movers)/fmp_weights는 `get_circuit("fmp_*")` 사용. **단건 종목 갱신 경로(update_stock_with_provider)에는 CB 없음** — Celery retry에만 의존.

### 2.4 402(Premium) 처리

- `client.py`에서 `FMPPremiumError` 명확히 분류, 재시도 안 함 (CLAUDE.md 버그 #23 정책 일치).
- `chain_sight_service.py`는 402/`FMPAPIError`를 catch 후 `warning log + continue` → 부분 실패. 대량의 프리미엄 심볼이 배치에 섞이면 **로그 폭증 + 부분 누락**이 조용히 발생.

### 2.5 FMP 약점 정리

| # | 약점 | 위치 | 영향 |
|---|------|------|------|
| F1 | 분당 300 슬라이딩 윈도우 없음 (delay만) | `client.py` | 병렬 워커 시 429 가능 |
| F2 | 일일 카운터가 인스턴스 메모리 (공유 안 됨) | `client.py:75` | 일일 한도 보호 무력 |
| F3 | 3개 클라이언트 구현 이원화 | fmp/* | 402/429 처리 불일치 |
| F4 | 단건 종목 갱신 경로 CB 미적용 | `tasks.py` | FMP 장애 시 retry 폭주 |
| F5 | serverless/market_pulse 클라이언트 재시도 없음 | 두 파일 | 일시 장애에 취약 |

---

## 3. Gemini 상세

### 3.1 전반 패턴

- **클라이언트 생성**: 거의 모든 파일이 동기 `genai.Client(api_key)` 사용 — Celery 컨텍스트에서 async 호출 금지(버그 #8) 정책 준수 ✅.
- **API 키 출처**: `GOOGLE_AI_API_KEY` → `GEMINI_API_KEY` 폴백 (대부분).
- **JSON 파싱 방어**: 23개 중 **13개 파일**이 `json.JSONDecodeError` try/except + regex 복구 보유 ✅. 양호.

### 3.2 🔴 최대 구멍: 429(Rate Limit) 미처리

429를 **명시적으로 처리하는 파일은 단 3개**:
- `rag_analysis/llm_service.py` (L251-260): "rate"/"quota"/"429" 문자열 매칭 + 지수 백오프 [1,2,4]초
- `serverless/keyword_service.py` (L324-329): 동일 패턴 + 2초 백오프
- `portfolio/llm/client.py` (L61-77, 180): 예외 클래스 분류 + 반대 provider 폴백

**나머지 ~20개 파일은 429를 일반 `Exception`으로만 잡거나, 잡아도 백오프 없이 즉시 fallback**. Gemini Free 티어(15 RPM)를 쓰는 야간 배치(news_deep_analyzer, keyword_extractor, sec_pipeline, llm_relation_extractor 등)가 동시에 돌면 429가 쏟아지고, 백오프 없이 전부 빈 결과로 떨어짐 → **데이터 채움률 저하가 조용히 발생**.

### 3.3 🔴 timeout 전무

**23개 파일 전부 genai 호출에 timeout/`request_options` 미설정.** Gemini가 응답을 지연하거나 무응답이면:
- CB가 있는 4개(llm_service, context_compressor, thesis_builder, briefing)는 그나마 격리되나, CB는 **실패 횟수 기반**이지 시간 초과를 감지하지 못함 → **무응답 시 워커 스레드가 무한정 블록**될 수 있음.
- 나머지 19개는 무방비.

> google-genai SDK는 `http_options={'timeout': ...}` (밀리초) 설정 가능. 공통 헬퍼에서 강제 권고.

### 3.4 예외 전파(graceful 아님) 파일

대부분 graceful(빈값/None/규칙 폴백)이나 아래는 **예외를 호출자로 전파**:
- `stocks/services/korean_overview_service.py` (L96-97)
- `market_pulse/briefing/client.py` (CB로 감싸지만 catch 없음 — CB OPEN 시 `CircuitBreakerError` 전파)

### 3.5 Gemini 약점 정리

| # | 약점 | 영향 | 범위 |
|---|------|------|------|
| G1 | 429 백오프 미처리 | 야간 배치 데이터 채움률 저하 | ~20개 파일 |
| G2 | timeout 전무 | 무응답 시 워커 블록 | 23개 전부 |
| G3 | 429 감지가 문자열 매칭 (`"rate"/"quota"/"429"`) | SDK 예외 타입 변경 시 깨짐 | 처리하는 3개 파일 |
| G4 | 재시도 로직 파일마다 제각각 | 유지보수/일관성 | 전반 |

---

## 4. 기타 의존성

### 4.1 FRED (`fred_client.py`, `macro_service.py`) — 🟡 양호

- `_make_request()`: 3회 재시도 + exponential backoff(2/4/6s), 401/403/404 즉시 실패, 5xx 재시도, 30s timeout, 분당 100 rate limiter.
- `macro_service.py`: 메서드별 try/except → Fear&Greed 실패 시 기본값(value=50, neutral) 반환. **앱 중단 없음**.
- 약점: 전역 timeout 없이 메서드별 개별 처리. CB 미적용.

### 4.2 Neo4j — 🟢 모범 사례

- `neo4j_driver.py`: **Lazy 싱글톤**, 첫 호출 실패 시 `None` 저장. 이후 모든 쿼리가 `if driver is None → 빈 데이터` 반환.
- `neo4j_service.py`: `QUERY_TIMEOUT=2000ms`, `_empty_relationships()` 완벽 폴백.
- `neo4j_chain_sight_service.py`: CB(5회 실패→60s 차단) + `is_available()` 체크.
- **Neo4j 다운 → 그래프 기능만 빈 데이터, 나머지 앱 정상**. 이상적.
- 약점: CB 재시도 `retry_attempts=1` (기본 3 아님) — 일시 네트워크 글리치에 다소 민감.

### 4.3 SEC EDGAR (`sec_pipeline/collector.py`) — 🟡 양호

- Rate limit 준수: 요청 간 `0.12s` sleep (10 req/sec 규정 준수).
- `User-Agent` 헤더 설정 (SEC 필수 요건).
- 15~60s timeout, `RequestException` catch + logging.
- **edgartools 폴백** (선택적 의존성) + 섹션 검증 실패 시 폴백.
- Celery task `tasks.py`: exponential backoff(2^attempts) 재시도.
- 약점: CB 미적용 (Celery retry로 대체).

### 4.4 Redis 캐시 — 🟢 낮음, 단 ⚠️ 숨은 SPOF

- `rag_analysis/services/cache.py`: 모든 `cache.get/set`이 try/except → 실패 시 None/False 반환. **Redis 다운 → 성능 저하만, 기능 정상**. 테스트로 검증됨(`test_get_error_returns_none`).
- ⚠️ **그러나 `CircuitBreaker`가 상태를 `django.core.cache`(=Redis)에 저장** (`circuit_breaker.py:64-75`, `cache.get/set/incr/add`). 이 호출들은 **try/except로 감싸여 있지 않음**.
  - **Redis 장애 시**: `get_state()`의 `cache.get`이 `ConnectionError`를 던지면 → CB로 보호하던 **FMP/LLM/Neo4j/News 경로 전체가 예외 전파**로 동시 실패. 즉 Redis가 "graceful degradation을 담당하는 계층"의 SPOF가 됨.
  - 일반 앱 캐시는 graceful하나, **CB 메타데이터 경로는 graceful하지 않음** — 이 비대칭이 핵심 리스크.

### 4.5 뉴스 API (Finnhub / Marketaux) — 🟢 낮음

- 각 provider rate limit(Finnhub 1s, Marketaux 10s), 200 외 상태/`"error"` 필드 검증, 실패 시 `return []`.
- `aggregator.py`: provider별 독립 실패 → 다음 provider 시도. CB는 `news/tasks.py`에서 적용.

### 4.6 Alpha Vantage — ⚪ 레거시

- `news/models.py`의 `SENTIMENT_SOURCE_CHOICES` enum에만 잔존. **실제 호출 코드 없음**(Marketaux+FMP로 대체). 정리 후보.

---

## 5. Circuit Breaker 후보

### 5.1 현재 CB 적용 현황

`packages/shared/api_request/circuit_breaker.py` (tenacity 기반, Redis 백엔드) — `get_circuit(name, failure_threshold=5, recovery_seconds=60, retry_attempts=3)`.

**적용된 곳**: FMP(sp500_service, sp500_eod_service, data_sync/Movers, fmp_weights) · LLM(thesis_builder, context_compressor, llm_service, briefing/client) · News(news_aggregator, news/tasks) · Neo4j(neo4j_chain_sight_service).

### 5.2 도입 후보 (장애 시 전체 영향 큰 순)

| 우선순위 | 대상 | 현재 상태 | 근거 |
|---|---|---|---|
| **P0** | **Gemini 야간 배치 LLM 전반** (news_deep_analyzer, keyword_extractor, llm_relation_extractor, sec_pipeline/extractor·intelligence, regulatory_service, keyword_generator(v1/v2)) | 429/timeout 무방비 | 야간 파이프라인 동시 실행 시 429 폭주. **공통 LLM 래퍼(CB + timeout + 429 backoff)** 로 일괄 적용 권고 |
| **P0** | **CircuitBreaker의 Redis 접근 자체** | `cache.get/set`이 try/except 없음 | Redis 장애 시 CB가 보호 대상 전체를 동반 실패시킴. `get_state`/`_record_*`에 try/except 추가 → Redis 불가 시 **CLOSED로 fail-open** 권고 |
| **P1** | **FMP 단건 종목 갱신** (`stocks/tasks.py:update_stock_with_provider`, `update_financials_with_provider`) | Celery retry만 | FMP 장애 시 수백 종목 태스크가 각각 retry 폭주 → 큐 적체. `get_circuit("fmp_stock_update")` 권고 |
| **P1** | **FMP 클라이언트 분당 한도** | delay만, 슬라이딩 윈도우 없음 | 분산 워커 동시 호출 시 429. 공유(Redis) 토큰버킷 권고 |
| **P2** | **FRED 호출** | 재시도 O, CB X | FRED 장애 시 macro 대시 메서드별 재시도 누적. CB로 빠른 fail + 기본값 |
| **P2** | **SEC EDGAR** | Celery retry O, CB X | 대량 10-K 수집 시 SEC 차단되면 retry 폭주. CB 권고 |
| **P3** | **Neo4j CB retry_attempts 상향** | retry=1 | 일시 글리치 민감도 완화 (1→3) |

### 5.3 CB 인프라 개선 제안 (구현 아님, 감사 의견)

1. **CB 상태 저장소의 fail-open 처리**: Redis 접근 실패를 CB가 흡수하여 `CLOSED`로 동작(=원호출 시도)하도록 → Redis가 graceful degradation의 SPOF가 되지 않게.
2. **timeout 기반 실패 감지**: 현재 CB는 예외 횟수만 카운트. LLM 무응답은 timeout이 없으면 영원히 감지 안 됨 → 공통 LLM 호출에 timeout 필수.
3. **429 감지를 문자열 매칭 → 예외 타입 기반**으로 통일.

---

## 부록: 조사 대상 파일 수

- FMP 호출 관련: 35개 파일 식별 (클라이언트 3 + provider/service/tasks + serverless 8 + news 2 + macro 1 등)
- Gemini 호출 관련: 23개 핵심 서비스 파일 (+ scripts/tests 다수)
- 기타: FRED 2, Neo4j 3+, SEC 2, Redis(cache) 전역, 뉴스 provider 3

> 본 보고서는 정적 분석 기반이며 코드를 수정하지 않았습니다. 라인 번호는 감사 시점(2026-06-08) 기준.
