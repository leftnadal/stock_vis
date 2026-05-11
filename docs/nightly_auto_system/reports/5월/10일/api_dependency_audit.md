# 외부 API 의존성 감사 보고서

- **생성일**: 2026-05-10
- **감사 범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis, 뉴스(Finnhub/Marketaux) 외
- **방식**: 코드 정적 분석 (read-only). 코드 수정 없음.
- **사전 grep**: FMP 의존 38 파일, Gemini 의존 38 파일 확인.

---

## 1. 의존성 매트릭스

장애 시 영향 범위 / Retry / Rate Limit / Circuit Breaker / Fallback 보유 여부 요약.

| 서비스 (호출 지점) | 외부 API | Retry | RateLimit | Timeout | CB | Fallback | 위험도 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `api_request/providers/fmp/client.py` | FMP | ✅ (3회, 지수 backoff) | ✅ (0.2s + daily) | ✅ 30s | ❌ | 호출자 위임 | M |
| `api_request/providers/fmp/provider.py` | FMP | (위임) | (위임) | (위임) | ❌ | error_response 반환 | L |
| `serverless/services/fmp_client.py` | FMP | ❌ | ❌ | ✅ 30s | ❌ | 캐시만 | **H** |
| `macro/services/fmp_client.py` | FMP | ❌ | ✅ (0.2s) | ✅ 30s | ❌ | None/[] 반환 (defensive) | L |
| `news/providers/fmp.py` → `news/services/aggregator.py` | FMP | (위임) | (위임) | (위임) | ✅ `fmp_news` | 빈 결과 | L |
| `stocks/services/sp500_service.py` | FMP | ❌ | ❌ | (위임) | ❌ | datahub.io CSV (제한적) | **H** |
| `stocks/services/sp500_eod_service.py` | FMP | ❌ | ✅ (0.3s/심볼) | (위임) | ❌ | 심볼별 누락 허용 | **H** |
| `serverless/services/data_sync.py` | FMP | ❌ | ❌ | (위임) | ❌ | 없음 (전체 실패) | **H** |
| `serverless/services/sector_heatmap_service.py` | FMP | ❌ | ❌ | (위임) | ❌ | 섹터별 누락 허용 | M |
| `serverless/services/enhanced_screener_service.py` | FMP | ❌ | ❌ | (위임) | ❌ | 빈 list | M |
| `serverless/services/filter_engine.py` | FMP (`_make_request` 직접) | ❌ | ❌ | (위임) | ❌ | 부분 결과 | M |
| `serverless/services/keyword_data_collector.py` | FMP (10 thread) | ❌ | (병렬 10) | (위임) | ❌ | 심볼별 누락 | M |
| `thesis/tasks/eod_pipeline.py` | FMP | ❌ | ❌ | (위임) | ❌ | 지표별 skip + 402 처리 ✅ | L |
| `marketpulse/services/news_aggregator.py` | FMP | (위임) | (위임) | (위임) | ❌ | 빈 뉴스 | L |
| `rag_analysis/services/llm_service.py` | Gemini (async stream) | ✅ (1,2,4s) | ✅ 429 감지 | ❌ | ❌ | JSON fail → empty list | M |
| `rag_analysis/services/context_compressor.py` | Gemini (async, 5 병렬) | ❌ | ❌ | ❌ | ❌ | API 키 없음 → truncate | **H** |
| `rag_analysis/services/entity_extractor.py` | Gemini (async, JSON 모드) | ❌ | ❌ | ❌ | ❌ | regex 룰베이스 | M |
| `portfolio/llm/client.py` | Gemini + Anthropic | ✅ (1회 fallback) | ✅ (CostGuard) | ✅ 묵시 | ❌ (CostGuard만) | provider 교차 fallback ✅ | L |
| `marketpulse/briefing/client.py` | Gemini (sync) | ✅ (tenacity) | ✅ | ✅ | ✅ failure_threshold=5 | CB open → error | L |
| `serverless/services/thesis_builder.py` | Gemini (sync) | ❌ | ❌ | ❌ | ❌ | JSON 잘림 시 None | **H** |
| `serverless/services/keyword_generator_v2.py` | Gemini (sync→async wrap) | ❌ | ❌ | ❌ | ❌ | 없음 (event loop 충돌 위험) | **H** |
| `serverless/services/keyword_generator.py` | Gemini | ✅ (수동 sleep 2/4/6) | ✅ | ❌ | ❌ | 빈 결과 | M |
| `serverless/services/keyword_service.py` | Gemini | ✅ (수동 sleep) | ✅ | ❌ | ❌ | 빈 결과 | M |
| `serverless/services/regulatory_service.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 없음 | M |
| `serverless/services/relationship_keyword_enricher.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 없음 | M |
| `serverless/services/llm_relation_extractor.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 없음 | M |
| `serverless/services/csv_url_resolver.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 없음 | L |
| `news/services/news_deep_analyzer.py` | Gemini | ❌ | ✅ (RPM_DELAY=4s) | ❌ | ❌ | 룰 기반 | M |
| `news/services/keyword_extractor.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 빈 키워드 | L |
| `news/services/stock_insights.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 빈 인사이트 | M |
| `thesis/services/thesis_builder.py` | Gemini | ❌ | ❌ | ❌ | ❌ | regex JSON 추출 취약 | **H** |
| `thesis/services/prompt_builder.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 없음 | M |
| `thesis/services/indicator_matcher.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 없음 | M |
| `thesis/tasks/summary.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 없음 | M |
| `thesis/views/conversation_views.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 없음 | M |
| `sec_pipeline/intelligence.py` | Gemini (JSON 모드) | ❌ | ❌ | ❌ | ❌ | 없음 (Exception → log) | M |
| `sec_pipeline/extractor.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 없음 | M |
| `validation/services/llm_peer_filter.py` | Gemini (JSON 모드) | ❌ | ❌ | ❌ | ❌ | 룰베이스 | L |
| `stocks/services/korean_overview_service.py` | Gemini | ❌ | ❌ | ❌ | ❌ | 영어 원본 | L |
| `macro/services/fred_client.py` | FRED | ✅ (3회, 5xx만) | ✅ (rate_limiter) | ✅ | ❌ | 빈 dict 반환 | M |
| `macro/services/macro_service.py` | FRED+FMP | (위임) | (위임) | (위임) | ❌ | 캐시 + default {value:50} | M |
| `rag_analysis/services/neo4j_driver.py` | Neo4j | ❌ | N/A | ✅ (max_pool=50) | ❌ | `None` (lazy init) | **H** |
| `serverless/services/neo4j_chain_sight_service.py` | Neo4j | ❌ | N/A | ❌ | ❌ | `is_available()` → []/False | **H** |
| `chainsight/tasks/*` | Neo4j | (위임) | N/A | (위임) | ❌ | 별도 `neo4j` 큐 격리 | M |
| `sec_pipeline/collector.py` | SEC EDGAR | ❌ | ✅ (0.12s, 8.3 req/s) | ✅ 60s | ❌ | edgartools (선택) | **H** |
| 전체 (`from django.core.cache import cache`) | Redis | N/A | N/A | N/A | ❌ | silent miss → API 폭주 | M (광범위) |
| `config/celery.py` (broker) | Redis | N/A | N/A | N/A | ❌ | 없음 | M |
| `news/providers/finnhub.py` | Finnhub | ❌ | ✅ (1s) | (위임) | ✅ (CB) | raise | L |
| `news/providers/marketaux.py` | Marketaux | ❌ | ✅ (10s) | (위임) | ✅ (CB) | raise | L |

> 표기: H=High, M=Medium, L=Low. "(위임)"은 하위 클라이언트로 위임됨. ✅/❌는 명시적 구현 여부.

---

## 2. FMP 상세

### 2.1 핵심 클라이언트 4종 비교

| 클라이언트 | Retry | Rate Limit | Timeout | 402 처리 | 평가 |
|---|:-:|:-:|:-:|:-:|---|
| `api_request/providers/fmp/client.py` (`client.py:121,149-150,154`) | ✅ 3회 지수 backoff | ✅ 0.2s + daily 추적 | ✅ 30s | ✅ 즉시 raise (FMPPremiumError) | **양호** |
| `api_request/providers/fmp/provider.py:86-94,247-252` | (위임) | (위임) | (위임) | ✅ PREMIUM_ONLY 코드 변환 | **양호** |
| `serverless/services/fmp_client.py:51-92,74` | ❌ `raise_for_status` 즉시 | ❌ 없음 | ✅ 30s | ❌ 일반 Exception | **취약** |
| `macro/services/fmp_client.py:72,98-102,108` | ❌ | ✅ 0.2s | ✅ 30s | ❌ raise | **양호** (defensive 메서드) |

**핵심 발견**:
- `api_request/providers/fmp/client.py:126-133`은 401/402/403/429를 코드로 분리 처리하고, 402/401/429는 재시도하지 않음(`client.py:149-150`). FMPPremiumError, FMPAuthError, FMPRateLimitError로 구분(`client.py:20-37`).
- `serverless/services/fmp_client.py`는 위 클라이언트와 별개로 httpx 기반 사본이 존재. **재시도와 rate limit 모두 없음** → 동시성 높은 작업에서 429 위험.
- `api_request/providers/factory.py:68`의 `FALLBACK_CHAIN`이 비어 있음 → FMP 장애 시 대체 provider 없음.

### 2.2 호출 지점별 위험도

#### HIGH

- **`stocks/services/sp500_service.py:37-41`** — `get_sp500_constituents()` 실패 시 빈 결과 반환만, datahub.io fallback도 FMPAPIError로 전파(`provider.py:361-367`). FMP 장애 → S&P 500 동기화 전체 실패.
- **`stocks/services/sp500_eod_service.py:131-133, 90-111`** — 500개 심볼 루프, 심볼별 try/except는 있으나 `FMPClient` 초기화 실패 시 전체 실패. 0.3s 슬립은 200 RPM 기준이라 Starter 한도(300)에선 안전하지만 Circuit Breaker 부재.
- **`serverless/services/data_sync.py:75-77`** — Market Movers (gainers/losers/actives) 3개 API 동시 호출, 하나 실패 시 `service.fetch_data()`에서 raise → **전체 sync 실패**.

#### MEDIUM

- **`serverless/services/sector_heatmap_service.py:264-310, 313-314`** — 11개 섹터 ETF + gainers/losers, 섹터별 try/except로 부분 누락 허용.
- **`serverless/services/filter_engine.py:258, 484, 544`** — `fmp_client._make_request()` **private method 직접 호출**. provider 계층의 재시도/에러 분류 우회.
- **`serverless/services/enhanced_screener_service.py:227, 274, 544`** — 동일한 private 호출 + 대용량 페이징 시 호출 폭증 가능.
- **`serverless/services/keyword_data_collector.py:80, 322`** — ThreadPoolExecutor 10 워커 병렬, rate는 안전(120/min)하지만 누적 에러에 대한 차단 없음.

#### LOW

- **`thesis/tasks/eod_pipeline.py:144-151`** — `FMPPremiumError`/`FMPClientError` 분기 처리, 지표별 skip 허용 (양호).
- **`news/services/aggregator.py:106-107, 130, 148-149`** — `get_circuit('fmp_news')` 적용 (**유일한 FMP-CB 사례**).

### 2.3 공통 취약점

| 취약점 | 영향 | 예시 |
|---|---|---|
| **CB 부재 (FMP 호출 거의 전부)** | 장애 전파 | data_sync, sp500_eod, sector_heatmap, enhanced_screener, filter_engine |
| **`serverless/services/fmp_client.py` 재시도/RL 누락** | 5xx 시 즉시 실패, 동시성에서 429 | 모든 serverless 호출 |
| **private `_make_request` 직접 호출** | provider 보호 우회 | filter_engine, enhanced_screener |
| **`FALLBACK_CHAIN` 비어 있음** | FMP=단일 장애점 | `api_request/providers/factory.py:68` |
| **402 처리 불균일** | 어떤 곳은 skip, 어떤 곳은 raise | thesis/tasks/eod_pipeline.py(skip) vs serverless(raise) |
| **대량 루프(500 심볼)에서 누적 에러 차단 없음** | rate 한도 도달 가속 | sp500_eod_service |

### 2.4 양호한 패턴

- `api_request/providers/fmp/client.py`: 30s timeout + 지수 backoff + 401/402/429 분류 + daily 호출 추적.
- `news/services/aggregator.py`: Circuit Breaker (`fmp_news`) 적용.
- `macro/services/fmp_client.py`: 모든 메서드가 Exception을 잡고 `None`/`[]` 반환 (defensive).
- `thesis/tasks/eod_pipeline.py`: `FMPPremiumError` 명시 처리 + 지표 누락 허용.

---

## 3. Gemini 상세

### 3.1 핵심 LLM 서비스 비교

| 서비스 | 모드 | 429 | JSON 파싱 | Timeout | CB | Fallback |
|---|---|:-:|:-:|:-:|:-:|---|
| `rag_analysis/services/llm_service.py:182-186, 217-232, 276-308` | async stream | ✅ 지수 1/2/4s | ✅ JSONDecodeError + regex | ❌ | ❌ | empty list |
| `rag_analysis/services/context_compressor.py:83-138` | async, 5 병렬 gather | ❌ | ❌ (text 직접) | ❌ | ❌ | API 키 없음 시 truncate |
| `rag_analysis/services/entity_extractor.py:87-178` | async JSON 모드 | ❌ | ✅ TypedDict | ❌ | ❌ | regex 룰베이스 ✅ |
| `portfolio/llm/client.py:62-80, 149-167, 233-276` | sync | ✅ 1회 + provider fallback | ✅ getattr | ✅ 묵시 | (CostGuard) | Gemini ↔ Anthropic 교차 ✅ |
| `marketpulse/briefing/client.py:67-68` | sync | ✅ tenacity | (text only) | ✅ | ✅ failure_threshold=5, recovery=60s | CircuitBreakerError |

### 3.2 호출 지점 위험 분류

#### HIGH (즉시 조치)

- **`serverless/services/keyword_generator_v2.py:383-422`** — `asyncio.get_event_loop() + run_until_complete()` 패턴. Celery worker가 이미 event loop를 가질 경우 `RuntimeError: This event loop is already running` 발생 → **CLAUDE.md 코딩 규칙(Bug #8) 위반 위험**.
- **`serverless/services/thesis_builder.py:344-348, 472-483`** — 동기 `client.models.generate_content()` 사용은 OK이나, JSON 파싱이 ` ```json `, ` ``` `, `{...}` 3단계 regex로만 구성. 마지막 단계는 잘린/중첩 JSON 매칭 가능. timeout 미설정.
- **`thesis/services/thesis_builder.py`** — `_parse_response`가 동일한 regex 기반. 재시도/timeout 모두 없음.
- **`rag_analysis/services/context_compressor.py:98, 134-138`** — `gather(..., return_exceptions=True)` 사용 후 type check만, 429 재시도 없음. 5 병렬 → 15 RPM Free 한도 단숨에 소진 가능.

#### MEDIUM

- **`news/services/news_deep_analyzer.py:125-134, 228-246`** — `re.search(r'\{[\s\S]*\}', raw)`는 첫 `{`부터 마지막 `}`까지 greedy 매칭 → 중첩 JSON 오매칭 가능. `RPM_DELAY=4s` 적용은 양호.
- **`sec_pipeline/intelligence.py:162-183`** — `response_mime_type='application/json'` 강제하지만 generic Exception만 처리, 429 감지 없음.
- **`rag_analysis/services/entity_extractor.py:87-114`** — JSONDecodeError 처리는 있으나 429 분기 없음.
- **`serverless/services/keyword_service.py:118` / `keyword_generator.py:264-330`** — 수동 `time.sleep(2,4,6)` 재시도. tenacity 미사용.

#### LOW

- **`portfolio/llm/client.py:149-167`** — provider 교차 fallback (Gemini↔Anthropic) + CostGuard 적용. **모범 사례**.
- **`marketpulse/briefing/client.py:67-68`** — Circuit Breaker + tenacity 조합. **모범 사례**.
- **`validation/services/llm_peer_filter.py:86-90`** — 실패 시 룰 기반 폴백 명확.

### 3.3 공통 취약점

| 취약점 | 위치 |
|---|---|
| **429 재시도 없음** | context_compressor, entity_extractor, news_deep_analyzer, sec_pipeline/intelligence, regulatory_service, relationship_keyword_enricher, llm_relation_extractor, thesis/services/* |
| **Timeout 미설정** | rag_analysis/* 전체, serverless/services/thesis_builder, serverless/services/keyword_*, thesis/services/*, sec_pipeline/* |
| **JSON 파싱 regex 취약** | serverless/services/thesis_builder.py:472, news_deep_analyzer.py:228, thesis/services/thesis_builder.py |
| **응답 schema 검증 부재** | 거의 모든 곳 (`hasattr(response, 'text')`만 체크) |
| **Cost Guard 미적용** | portfolio 외 전부 → 무제한 호출 위험 |
| **동기/비동기 혼용** | keyword_generator_v2.py:409-412 (Celery에서 `get_event_loop()`) |

### 3.4 Celery 컨텍스트 위반 의심

- `serverless/services/keyword_generator_v2.py:383-422`의 `asyncio.get_event_loop()` 패턴은 CLAUDE.md "Celery에서 동기 API만" 규칙을 우회하려는 시도로 보이며, worker 환경에 따라 RuntimeError 발생 가능. **`asyncio.run()` 또는 동기 API 직접 호출이 안전**.

---

## 4. 기타 의존성

### 4.1 FRED API (`macro/services/fred_client.py`)

**위험도: MEDIUM**

- **Retry**: `_make_request()`에서 500/502/503/504만 3회 지수 backoff (2/4/6s) — `fred_client.py:114-128`.
- **즉시 실패**: 401/403/404 — `fred_client.py:106-111`.
- **Rate Limiter**: `api_request.rate_limiter.get_rate_limiter("fred")` 사용 — `fred_client.py:70, 101`.
- **Defensive 메서드**: `get_interest_rates`, `get_inflation_data`, `get_employment_data`, `get_vix` 모두 개별 try/except로 빈 dict 반환 — `fred_client.py:273-282, 295-322, 334-372, 374-404`.
- **장애 시**: `macro_service.py:79-85`의 Fear & Greed → default `{value:50, rule_key:'neutral'}` 반환.

### 4.2 Neo4j (`rag_analysis/services/neo4j_driver.py` + `serverless/services/neo4j_chain_sight_service.py`)

**위험도: HIGH**

- **Lazy singleton**: 연결 실패 시 `None` 반환, Django 앱 살아 있음 — `neo4j_driver.py:42-67`.
- **`is_available()` 가드**: 모든 메서드 — `neo4j_chain_sight_service.py:132-133, 163-164, 227-229`.
- **세션 단위 try/except 부재**: `session.run()`이 naked로 호출되는 지점 다수 — `neo4j_chain_sight_service.py:136-154, 166-172, 236-262` — connection drop 중 session leak 가능.
- **Pool 관리**: `max_connection_pool_size=50` 설정만 있음, leak 모니터링 없음 — `neo4j_driver.py:49-55`.
- **Celery 격리**: `neo4j` 큐 + solo pool로 macOS fork 안전 확보 — `config/celery.py:36-54`.
- **장애 시**: 그래프 API가 빈 배열 반환 → **정상 동작처럼 보이는 silent failure**.

### 4.3 SEC EDGAR (`sec_pipeline/collector.py`)

**위험도: MEDIUM-HIGH**

- **Rate limiting**: 0.12s sleep (≈8.3 req/s, 공식 권장 10 req/s 준수) — `collector.py:83, 130, 151`.
- **Timeout**: 60s — `collector.py:154, 132`.
- **Retry**: **없음**. `requests.get()` 실패 → 즉시 raise.
- **Fallback**: `edgartools` 라이브러리 — `collector.py:189-215, 254-271`. ImportError 시 fallback 불가능.
- **장애 시**: 403(User-Agent 차단)이나 일시 maintenance에 자동 복구 없음. Celery `max_retries=3` 의존.

### 4.4 Redis (캐시 + Celery broker)

**위험도: MEDIUM** (영향 범위는 광범위)

- **Silent miss**: `cache.get() → None` 시 모든 호출 지점이 API 재호출 → **Cascade 시 외부 API rate limit 도달**.
- **Celery broker**: `config/settings.py:472-473` — Redis down 시 task queue 정지.
- **TTL 전략**: provider 캐시 5분~7일, macro 60s~24h, neo4j 그래프 5분 — `api_request/cache/decorators.py`, `macro_service.py:91-194`, `neo4j_chain_sight_service.py`.
- **"성공만 캐시" 정책**: `api_request/cache/decorators.py:117-121` — `result.success`만 저장.
- **CB 미적용**: 모든 `cache.get()/set()` 호출이 raw. CircuitBreaker 구현(`marketpulse/utils/circuit_breaker.py`, `news/services/circuit_breaker.py`)은 존재하지만 캐시 호출에 적용 안 됨.

### 4.5 뉴스 API (Finnhub, Marketaux)

**위험도: LOW-MEDIUM**

- **Rate limiting**: Finnhub 1s, Marketaux 10s — `news/providers/finnhub.py:54-60, marketaux.py:55-62`.
- **Retry 없음**: 503/timeout 즉시 raise — `finnhub.py:71-82, marketaux.py:71-85`.
- **CB 적용**: `news/services/aggregator.py`가 `get_circuit()` 사용.
- **Celery task**: `news/tasks.py:96-150` — `max_retries=2`, soft_time_limit=1800s.
- **격리됨**: News는 critical path 아님 (Market Pulse/Portfolio 영향 없음).

### 4.6 보조 의존성

- **yfinance**: `stocks/services/financial_statements_fallback.py:38-46` — ImportError 허용, FMP 실패 시 사용. **위험도: LOW**.
- **edgartools**: `sec_pipeline/collector.py:190-215` — 선택적, 미설치 시 fallback 비활성. **위험도: LOW** (보조).

---

## 5. Circuit Breaker 후보

### 5.1 현재 CB 적용 현황

| 적용됨 | 위치 |
|---|---|
| ✅ `news/services/aggregator.py` | `fmp_news` CB |
| ✅ `news/providers/finnhub.py`, `marketaux.py` | 뉴스 provider CB |
| ✅ `marketpulse/briefing/client.py:67-68` | Gemini briefing CB (failure_threshold=5, recovery=60s) |
| ✅ 인프라: `marketpulse/utils/circuit_breaker.py`, `news/services/circuit_breaker.py` (Redis 기반 상태 저장) | 재사용 가능한 구현체 존재 |

### 5.2 도입 우선순위

#### P0 (즉시 — 단일 장애점, 광범위 영향)

| 순위 | 대상 | 이유 | 제안 키 |
|---|---|---|---|
| 1 | **`serverless/services/data_sync.py` (FMP Market Movers)** | 3개 API 동시 호출, 하나 실패=전체 실패. 매일 실행되는 Celery 태스크. | `fmp_market_movers` |
| 2 | **`stocks/services/sp500_eod_service.py` (FMP)** | 500 심볼 루프, 누적 에러 차단 없음. EOD Dashboard 의존. | `fmp_sp500_eod` |
| 3 | **`stocks/services/sp500_service.py` (FMP)** | S&P 500 구성 동기화 단일 진입점. fallback 제한적. | `fmp_sp500_constituents` |
| 4 | **`rag_analysis/services/llm_service.py` (Gemini)** | RAG 사용자 응답 직접 의존, CRITICAL 경로. | `gemini_rag` |
| 5 | **`rag_analysis/services/context_compressor.py` (Gemini)** | 5 병렬 gather → 429 즉발, 재시도 없음. | `gemini_compress` |
| 6 | **`thesis/tasks/summary.py` + `thesis/services/thesis_builder.py` (Gemini)** | 일일 thesis 갱신 배치, JSON 파싱 fragile. | `gemini_thesis` |
| 7 | **`serverless/services/neo4j_chain_sight_service.py` (Neo4j)** | session-level exception 누락 + silent empty 반환 → 장애 위장. | `neo4j_chain_sight` |

#### P1 (단기)

| 순위 | 대상 | 이유 | 제안 키 |
|---|---|---|---|
| 8 | `serverless/services/sector_heatmap_service.py` (FMP) | 11개 섹터 + Market Pulse 의존 | `fmp_sector_etf` |
| 9 | `serverless/services/enhanced_screener_service.py` (FMP) | 대량 페이징, private method 호출 | `fmp_screener` |
| 10 | `serverless/services/filter_engine.py` (FMP) | private method, 재시도 없음 | `fmp_filter` |
| 11 | `serverless/services/keyword_generator_v2.py` (Gemini) | event loop 충돌 위험 + 일일 배치 | `gemini_kw_v2` |
| 12 | `news/services/news_deep_analyzer.py` (Gemini) | 뉴스 분석 배치, JSON regex 취약 | `gemini_news_deep` |
| 13 | `sec_pipeline/intelligence.py` + `extractor.py` (Gemini) | SEC 파이프라인 핵심, retry 부재 | `gemini_sec` |
| 14 | `sec_pipeline/collector.py` (SEC EDGAR) | 403/timeout 자동 복구 없음 | `sec_edgar` |
| 15 | `macro/services/fred_client.py` (FRED) | 5xx만 3회, transient 외 미보호 | `fred_api` |

#### P2 (중기 — 시스템 안정성)

| 순위 | 대상 | 이유 |
|---|---|---|
| 16 | `cache.get()` 전반 (Redis) | silent miss → cascade. 광범위 적용 부담은 크지만 핵심 대시보드(`macro_service.py`)부터 우선. |
| 17 | `serverless/services/fmp_client.py` 자체 | 재시도/RL 부재 → 신규 사용처가 늘면 위험 증가. CB 추가 또는 `api_request/providers/fmp/client.py`로 통합. |
| 18 | `thesis/services/*` Gemini 호출 전체 | timeout/429/CB 모두 부재. |

### 5.3 공통 권고 (CB와 함께 적용)

1. **Timeout 강제** — `client.models.generate_content(..., request_options={'timeout': 30})` 모든 Gemini 호출에 추가.
2. **JSON 파싱 표준화** — regex 기반 추출(`thesis_builder.py:472`, `news_deep_analyzer.py:228`)을 `response_mime_type='application/json'` + Pydantic 검증으로 통합.
3. **Provider Fallback Chain** — `api_request/providers/factory.py:68`의 `FALLBACK_CHAIN` 채우기 (FMP→AlphaVantage/Finnhub).
4. **Private 메서드 호출 제거** — `filter_engine.py:258`, `enhanced_screener_service.py:227,274`의 `_make_request` 직접 호출을 public 메서드로 교체 (provider 보호 우회 방지).
5. **Celery 컨텍스트 점검** — `keyword_generator_v2.py:383-422`의 `asyncio.get_event_loop()` 패턴 재검토.

---

## 6. 핵심 결론

1. **FMP는 단일 장애점 상태**. `api_request/providers/fmp/client.py`는 양호하나, `serverless/services/fmp_client.py`는 재시도/RL 모두 없음. CB는 `news/aggregator`만 보유. `FALLBACK_CHAIN` 비어 있음.
2. **Gemini는 portfolio/marketpulse만 모범 사례**. 나머지 25+ 호출 지점은 timeout/429/CB 모두 부재. `thesis_builder` 계열의 JSON regex 파싱이 가장 취약.
3. **Neo4j는 silent failure**가 가장 위험. `is_available()` 가드 덕분에 예외는 안 나지만, 빈 결과가 정상으로 보임 → 모니터링 필요.
4. **Redis silent miss**는 cascade 위험. Celery broker로도 사용되어 down 시 task 적체.
5. **SEC EDGAR**는 retry가 없어 403/maintenance에 취약. edgartools fallback이 선택적이라 보장되지 않음.
6. **즉시 도입 권고 CB 7개**: `fmp_market_movers`, `fmp_sp500_eod`, `fmp_sp500_constituents`, `gemini_rag`, `gemini_compress`, `gemini_thesis`, `neo4j_chain_sight`.
