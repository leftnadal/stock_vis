# 외부 API 의존성 감사 보고서

> **감사 일자**: 2026-06-09
> **범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis 캐시 장애 대응
> **방식**: 읽기 전용 코드 감사 (코드 수정 없음)
> **대상**: FMP 참조 약 36개 파일 + Gemini 참조 약 29개 파일 (테스트/마이그레이션 제외)

---

## 핵심 요약 (Executive Summary)

| 결론 | 상세 |
|------|------|
| **Circuit Breaker 기반은 갖춰짐** | `packages/shared/api_request/circuit_breaker.py` 존재, **13개 호출 지점**에서 사용 중 (FMP 5 + Gemini 4 + Neo4j 2 + 뉴스 2) |
| **클라이언트 계층 불일치가 최대 리스크** | FMP 클라이언트가 **3종**(`client.py`/`market_pulse_client.py`/`serverless_client.py`)으로 분기, retry·rate limit·402 처리 정책이 제각각 |
| **단일 장애점(SPOF) = Redis** | Circuit Breaker 상태가 **Redis 캐시에 저장**됨 → Redis 다운 시 CB가 항상 CLOSED로 동작, 누적 실패 추적 불능 → Neo4j/FMP 장애 격리 실패로 증폭 |
| **Gemini timeout 전무** | 거의 모든 genai 호출에 명시적 timeout 없음 → Celery `soft_time_limit`에만 의존, 동기 뷰 경로는 무한 대기 가능 |
| **402(Premium) 처리 단일 지점** | `client.py`만 `FMPPremiumError` 발생, 소비 측은 `provider.py`와 `thesis/tasks/eod_pipeline.py` **2곳만** 명시 처리 |

---

## 1. 의존성 매트릭스

### 1-1. FMP 클라이언트 계층 (3종 분기)

| 클라이언트 | HTTP 라이브러리 | Timeout | Retry | Rate Limit | 402 처리 | 429 처리 |
|-----------|----------------|---------|-------|-----------|---------|---------|
| `providers/fmp/client.py` | requests | 30s | ✅ 수동 지수백오프 3회(2-4-6s) | ✅ 0.2s sleep + 일일 10k 체크 | ✅ `FMPPremiumError` | ✅ `FMPRateLimitError` |
| `providers/fmp/market_pulse_client.py` | httpx | 30s | ❌ 없음 | ❌ (Django 캐시만) | ❌ 일반 `FMPAPIError` | ❌ (`HTTPStatusError`) |
| `providers/fmp/serverless_client.py` | requests | 30s | ❌ 없음 | ✅ 0.2s sleep (일일 한도 X) | ❌ 일반 `ValueError` | ❌ (`raise_for_status`) |

> ⚠️ **불일치**: 동일 FMP API를 3개 클라이언트가 서로 다른 정책으로 호출. `market_pulse_client.py`는 retry·throttle 둘 다 없어 가장 취약.

### 1-2. 서비스/태스크별 FMP fallback 매트릭스

| 서비스/태스크 | 파일:라인 | 실패 시 동작 | 부분 실패 | Circuit Breaker | Fallback 소스 |
|--------------|----------|-------------|----------|----------------|--------------|
| update_stock_with_provider | `stocks/tasks.py:293` | 로깅 후 진행 | ✅ 3작업 독립 | — | Provider 체인 |
| sync_sp500_constituents | `stocks/services/sp500_service.py:39` | CB open 시 early return(0) | ✅ skip 후 진행 | ✅ `fmp_sp500_constituents`(thr 3/300s) | — |
| sync_sp500_eod_prices | `stocks/services/sp500_eod_service.py:138` | CB open 심볼 skip | ✅ 심볼별 격리 | ✅ `fmp_sp500_eod`(thr 10/120s) | — |
| fmp_fundamentals | `stocks/services/fmp_fundamentals.py:89` | `return []`/`None` | — | — | 캐시 우선 |
| sync (overview/prices) | `stocks/services/stock_sync_service.py:161` | `SyncResult(success=False)` | ✅ 항목별 continue | — | 기존 DB row |
| chain_sight | `serverless/services/chain_sight_service.py:206` | `FMPAPIError` 격리 continue | ✅ 종목별 | — | — |
| data_sync (movers) | `serverless/services/data_sync.py:75` | CB open 시 `[]` | ✅ 3유형 독립 | ✅ `fmp_market_movers`(thr 5/120s) | — |
| enhanced_screener | `serverless/services/enhanced_screener_service.py:190` | 전체 빈 결과 반환 | ⚠️ 최대 20개만 호출 | — | 캐시 |
| market_breadth | `serverless/services/market_breadth_service.py:151` | **raise (태스크 전체 중단)** | ❌ | ❌ | — |
| sector_heatmap | `serverless/services/sector_heatmap_service.py:308` | 섹터별 `None` | ✅ 11섹터 격리 | — | — |
| keyword_data_collector | `serverless/services/keyword_data_collector.py:379` | `None` | ✅ ThreadPool 격리(10s timeout) | — | — |
| eod_pipeline | `thesis/tasks/eod_pipeline.py:146` | `(None,None)` + `null_value` 저장 | ✅ 지표별 | — | — |
| news fmp | `news/providers/fmp.py:52` | `return []` | ✅ 항목별 | — | — |
| fmp_weights (ETF) | `apps/market_pulse/fetchers/fmp_weights.py:64` | CB 위임 | — | ✅ `fmp_etf` | — |
| macro_service (global) | `apps/market_pulse/services/macro_service.py:220` | **명시 catch 없음, 상위 전파** | ❌ | — | — |

### 1-3. Gemini(genai) fallback 매트릭스

| 서비스 | 파일:라인 | 모델 | timeout | 429 처리 | JSON 파싱 복구 | 실패 시 동작 | Circuit Breaker |
|--------|----------|------|---------|---------|--------------|-------------|----------------|
| RAG llm_service | `rag_analysis/services/llm_service.py:199` | 2.5-flash(async) | ❌ | ✅ 지수백오프(1-2-4s) | ✅ fence 제거 | error 이벤트 | ✅ `get_circuit` |
| RAG adaptive_llm | `rag_analysis/services/adaptive_llm_service.py:174` | 2.5-flash/Claude | ❌ | ❌ 1회만 | — | error 이벤트 | — |
| RAG entity_extractor | `rag_analysis/services/entity_extractor.py:110` | 2.5-flash | ❌ | — | ✅ fence 제거 | **규칙기반 fallback** | — |
| RAG context_compressor | `rag_analysis/services/context_compressor.py:133` | 2.5-flash | ❌ | — | — | raise(상위 폴백) | ✅ `get_circuit` |
| keyword_service | `serverless/services/keyword_service.py:324` | 2.5-flash(sync) | ❌ | ✅ `(n+1)*2`s sleep | ✅ 정규식 복구 | `FALLBACK_KEYWORDS` | — |
| keyword_generator_v2 | `serverless/services/keyword_generator_v2.py:402` | 2.5-flash | ❌ | ❌ | ✅ | `None` | — |
| llm_relation_extractor | `serverless/services/llm_relation_extractor.py:434` | 2.5-flash | ❌ | ❌ | ✅ 정규식 복구 | 빈 ExtractionResult | — |
| regulatory_service | `serverless/services/regulatory_service.py:543` | **2.0-flash-exp** | ❌ | ⚠️ 4s 고정 sleep | ✅ | `[]` | — |
| thesis_builder(serverless) | `serverless/services/thesis_builder.py:393` | 2.5-flash | ❌ | ❌ | ✅ 4중 복구 | raise | — |
| thesis indicator_matcher | `thesis/services/indicator_matcher.py:226` | 2.5-flash | ❌ | ❌ | ✅ 정규식 | `return []` | — |
| thesis prompt_builder | `thesis/services/prompt_builder.py:538` | 2.5-flash | ❌ | ❌ | ✅ | `return None` | — |
| thesis_builder(thesis) | `thesis/services/thesis_builder.py:470` | 2.5-flash | ❌ | ❌ 1회 | ✅ | `_fallback_parse()` | ✅ `gemini_thesis`(thr 5/120s) |
| news keyword_extractor | `news/services/keyword_extractor.py:211` | 2.5-flash | ❌ | ❌ | ✅ 정규식 | `FALLBACK_KEYWORDS` | — |
| news_deep_analyzer | `news/services/news_deep_analyzer.py:119` | 2.5-flash | ❌ RPM 4s | ❌ | ✅ | `None` | — |
| stock_insights | `news/services/stock_insights.py:559` | 2.5-flash | ❌ | ❌ | — | 조용히 return | — |
| validation llm_peer_filter | `validation/services/llm_peer_filter.py:56` | 2.5-flash | ❌ | ❌ | structured JSON | `{"error":...}` | — |
| sec extractor | `sec_pipeline/extractor.py:35` | 2.5-flash | ❌ | ❌ | structured JSON | **raise(폴백 없음)** | — |
| sec intelligence | `sec_pipeline/intelligence.py:151` | 2.5-flash | ❌ | ❌ | structured JSON | fallback dict | — |
| portfolio LLMClient | `apps/portfolio/llm/client.py:113` | 2.5-flash+Claude | ❌ | ✅ 1회+provider 전환 | — | **반대 provider 폴백** | — |
| korean_overview | `stocks/services/korean_overview_service.py:36` | 2.5-flash | ❌ RPM 4s | ❌ | structured JSON | **raise(폴백 없음)** | — |
| market_pulse briefing | `apps/market_pulse/briefing/client.py:82` | 2.5-flash(**구 SDK**) | ❌ | ❌ | — | CB 위임 | ✅ `gemini` |

---

## 2. FMP 상세

### 2-1. 클라이언트 코어 (`providers/fmp/client.py`) — 모범 사례
- **status_code 분기 완비** (`client.py:129-139`): 401→`FMPAuthError`, 402→`FMPPremiumError`, 403→`FMPAuthError`, 429→`FMPRateLimitError`.
- **예외 계층** (`client.py:21-42`): `FMPClientError` 기반 4종 정의.
- **수동 지수 백오프** (`client.py:122-170`): max_retries=3, backoff `(attempt+1)*2`초. premium/auth/rate 예외는 **재시도 없이 즉시 전파**.
- **Rate Limit 이중 방어** (`client.py:103-115`): 요청 간 0.2s sleep(=5 req/s ≈ 300/min) + 일일 10,000 calls 하드 체크.

### 2-2. 취약 클라이언트
- **`market_pulse_client.py`**: retry 없음 + rate limit 없음. `_make_request`(`market_pulse_client.py:74-95`)는 모든 HTTP 에러를 단일 `FMPAPIError`로 평탄화 → 402/429 구분 불가. 캐시 TTL(`market_gainers` 5분 등)에만 의존.
- **`serverless_client.py`**: retry 없음. `RequestException`을 그대로 re-raise(`serverless_client.py:124-126`). 402를 `ValueError`로 처리 → 프리미엄 심볼 식별 불가.

### 2-3. 402 (FMPPremiumError) 처리 커버리지
- **발생**: `client.py:131-134` 단일 지점.
- **소비(명시 처리)**: `provider.py`(get_balance_sheet/income/cash_flow 3곳, `PREMIUM_ONLY` 코드 변환) + `thesis/tasks/eod_pipeline.py:146`(`(None,None)` 반환).
- **사각지대**: `market_pulse_client`/`serverless_client` 경로를 타는 모든 호출은 402를 일반 에러로 처리 → 공통버그 #23 재발 위험.

### 2-4. 부분 실패 패턴 (양호)
배치 작업 대부분이 항목/심볼/섹터 단위 try/except로 실패를 격리하고 통계(`stats`/`SyncResult`)로 결과를 보고. **단, caller가 반환값·stats를 검사하지 않으면 silent failure**가 누적됨.

### 2-5. ⚠️ FMP 단일 raise 지점 (태스크 전체 중단)
- `market_breadth_service.py:151`: `FMPAPIError`를 raise → CB 미적용. FMP 장애 시 시장폭 계산 태스크 전체 실패.
- `macro_service.py:220` (global markets): 명시 catch 없이 상위 전파.

---

## 3. Gemini 상세

### 3-1. 공통 강점
- **JSON 파싱 복구는 견고**: 대부분 markdown fence(` ```json `) 제거 + 정규식 복구 + 다중 폴백(thesis_builder 4중). `json.JSONDecodeError` 분리 처리.
- **Celery 동기 API 준수**: 공통버그 #8 대응으로 Celery 경로는 동기 `generate_content` 사용.

### 3-2. 공통 약점
1. **timeout 전무**: 조사 대상 거의 모든 genai 호출이 `GenerateContentConfig`에 timeout 미지정 → SDK 기본값 의존. 동기 뷰(`thesis/views/conversation_views.py`, `validation/llm_peer_filter.py`) 경로는 Gemini 지연 시 **요청 스레드 무한 점유** 가능.
2. **429 처리 비일관**: 4가지 정책 혼재 — (a) 지수백오프(llm_service), (b) `(n+1)*2`s sleep(keyword_service), (c) 고정 4s sleep(regulatory/relationship_enricher), (d) **미처리**(다수). 단일 표준 없음.
3. **실패 시 동작 3분기**: `FALLBACK_KEYWORDS`/규칙기반(우수) vs `return None`(caller 책임) vs `raise`(미처리). **`raise`이면서 폴백 없는 지점**: `sec_pipeline/extractor.py:93`, `korean_overview_service.py:95`.
4. **SDK 혼재**: 신 SDK(`from google import genai`) 다수 vs 구 SDK(`google.generativeai`) — `briefing/client.py`, `thesis/tasks/summary.py`. 에러 타입·재시도 동작 상이.
5. **모델 버전 불일치**: 대부분 `gemini-2.5-flash`이나 `regulatory_service.py:515`만 `gemini-2.0-flash-exp`(실험 모델, 가용성 보장 약함).
6. **asyncio fork 리스크**: `keyword_generator_v2.py:402` `asyncio.get_event_loop()` 사용 — Celery fork 환경에서 deadlock/SIGSEGV 가능(공통버그 #25 인접 영역).

### 3-3. 모범 사례 (`apps/portfolio/llm/client.py`)
- 예외 분류기(`_classify_gemini_error`/`_classify_anthropic_error`)로 RateLimit/Timeout/Auth/InvalidPrompt 명시 매핑.
- RateLimit/Timeout 시 **반대 provider(Gemini↔Claude) 자동 폴백** + `CostGuard` 비용 가드. → 타 서비스가 참고할 표준.

---

## 4. 기타 의존성

### 4-1. FRED API (`packages/shared/api_request/fred_client.py`)
- timeout 30s, max_retries 3, 일시 에러(500/502/503/504) 지수백오프, 분당 120회 rate limiter. **재시도 로직은 양호.**
- ⚠️ 캐시 실패 처리 없음 — Redis 다운 시 매 요청 FRED 직접 호출. fallback 데이터 없음(기본값 50만 반환).
- 영향: `macro_service`의 fear/greed·금리·인플레·GDP 대시보드. 실패 시 `{'error':...}` 또는 기본값.

### 4-2. Neo4j
- **드라이버**(`rag_analysis/services/neo4j_driver.py:20`): lazy singleton, 연결 실패 시 `None` 반환 + 앱 계속 실행(graceful). 단 **한 번 실패하면 재연결 안 함**(`reset_connection` 수동 호출 전까지).
- **Chain Sight 서비스**(`serverless/services/neo4j_chain_sight_service.py:117,133`): CB(`neo4j_chain_sight`, thr 5/60s) + `is_available()` 가드. 미가용 시 `[]`/`{nodes:[],edges:[]}` 반환(graceful).
- ⚠️ **Cypher 쿼리 timeout 없음** — `connection_acquisition_timeout=60`만 존재. 네트워크 지연 시 세션 장기 점유.
- ⚠️ **배치 로더**(`apps/chain_sight/services/neo4j_loader.py:52`): 배치 단위 재시도 없음, 실패 시 배치 전체 손실. 말미 `node_count` 호출도 Neo4j 의존.

### 4-3. SEC EDGAR (`services/sec_pipeline/collector.py`)
- User-Agent 헤더 + 0.12s sleep(10 req/s 준수), timeout 30/15/60s.
- ⚠️ **재시도 로직 없음**, **429 응답 처리 없음**. CIK/메타데이터 조회 실패 시 `RequestException` 상위 전파.
- ✅ 추출 검증 실패 시 edgartools fallback(`collect():256`) — 단 fallback도 외부 호출.
- CIK 캐싱이 클래스 변수만(영속 캐시 아님).

### 4-4. Redis 캐시
- 캐시 헬퍼(`rag_analysis/services/cache.py`): get/set 모두 try/except로 감싸 `None`/`False` 반환 — **개별 호출은 graceful**.
- ❌ **DB fallback 없음**: 캐시 미스/장애 시 원천(API) 재호출만 가능.
- ❌ **SPOF**: 아래 5절 참조.

---

## 5. 연쇄 장애 시나리오 (Redis SPOF 중심)

### 시나리오 A — Redis 다운이 Circuit Breaker를 무력화
`circuit_breaker.py`의 상태(`state`/`fail_count`/`opened_at`)가 **Django 캐시(Redis)에 저장**됨.
```
Redis 다운 → cache.get(state) = 기본값 CLOSED 고정
         → cache.incr(fail_count) 실패 → 누적 카운트 1에서 정체
         → failure_threshold(5) 영원히 도달 못함 → CB OPEN 전환 불가
         → Neo4j/FMP 장애 시 매 호출이 retry×timeout 전부 소진하며 실패
```
**결과**: Redis 장애가 가장 광범위한 증폭 효과. 13개 CB 지점 전부 동시 무력화.

### 시나리오 B — Redis 다운 → FRED/Gemini 직격
캐시 미스 → 매 요청 FRED 30s×3 재시도 또는 Gemini(timeout 無) 직접 호출 → 응답 시간 폭증 → 대시보드/뷰 타임아웃.

### 시나리오 C — SEC 429
재시도·429 처리 부재 → 대량 심볼 수집 중 부분 실패 → 검증 불일치 데이터(partial) 양산.

---

## 6. Circuit Breaker 도입 후보 (우선순위순)

CB는 이미 13개 지점에 적용됨. **미적용 + 장애 영향 큰 지점**을 우선순위로 제시한다.

| 우선순위 | 지점 | 파일:라인 | 근거 |
|---------|------|----------|------|
| 🔴 P0 | **CB 상태 저장소 분리** | `circuit_breaker.py` | Redis SPOF. CB가 Redis 의존 → Redis 다운 시 전 CB 무력화. 로컬 메모리 폴백 or 별도 백엔드 검토 (구조적 최우선) |
| 🔴 P0 | market_breadth FMP | `market_breadth_service.py:151` | 유일하게 raise로 태스크 전체 중단, CB 없음 |
| 🟠 P1 | FRED API 전체 | `fred_client.py` + `macro_service.py:220` | 매크로 대시보드 다수 의존, CB 미적용 + 캐시 폴백 없음 |
| 🟠 P1 | SEC EDGAR | `sec_pipeline/collector.py` | retry/429 처리 전무, CB 없음 |
| 🟠 P1 | Gemini 동기 뷰 경로 | `conversation_views.py`, `llm_peer_filter.py:56`, `korean_overview_service.py:36` | timeout 없음 + CB 없음 → 사용자 요청 스레드 무한 점유 |
| 🟡 P2 | market_pulse_client FMP | `market_pulse_client.py` | retry·throttle 둘 다 없음, 3종 클라이언트 중 최약 |
| 🟡 P2 | Neo4j 배치 로더 | `neo4j_loader.py:52` | 배치 재시도 없음, CB 미적용 (조회 경로는 CB 보호됨) |

### 추가 권고 (CB 외)
1. **FMP 클라이언트 3종 통합** — retry/rate-limit/402 정책을 `client.py` 기준으로 단일화.
2. **Gemini 전역 timeout 표준** — 모든 genai 호출에 명시적 timeout + 429 단일 재시도 정책.
3. **`raise`+폴백 없음 지점 보강** — `sec_pipeline/extractor.py:93`, `korean_overview_service.py:95`.
4. **`portfolio/llm/client.py` 패턴 확산** — provider 자동 폴백 + 비용 가드를 RAG/serverless로 확대.
5. **구 SDK 제거** — `briefing/client.py`, `thesis/tasks/summary.py`를 신 `google.genai`로 통일.

---

## 부록: 감사 대상 파일 인덱스

**FMP (36)**: `providers/fmp/{client,provider,market_pulse_client,serverless_client}.py`, `stocks/{tasks.py,views.py,services/*}`, `serverless/services/*`, `news/providers/fmp.py`, `apps/market_pulse/{services,fetchers}/*`, `thesis/tasks/eod_pipeline.py`, `chain_sight/{services,tasks}/*` 등.

**Gemini (29)**: `rag_analysis/services/*`, `serverless/services/{keyword*,llm_relation*,thesis_builder,regulatory*,relationship*}.py`, `thesis/{services,tasks,views}/*`, `news/services/*`, `validation/services/llm_peer_filter.py`, `sec_pipeline/{extractor,intelligence}.py`, `apps/portfolio/{llm,services}/*`, `apps/market_pulse/briefing/*`, `stocks/services/korean_overview_service.py` 등.

**기타**: `fred_client.py`, `neo4j_driver.py`, `neo4j_chain_sight_service.py`, `neo4j_loader.py`, `sec_pipeline/collector.py`, `rag_analysis/services/cache.py`, `circuit_breaker.py`.
