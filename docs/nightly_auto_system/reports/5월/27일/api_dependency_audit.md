# 외부 API 의존성 감사 보고서

- **감사일**: 2026-05-27
- **감사자**: Claude (read-only, no code mutations)
- **대상 브랜치**: slice17 (HEAD `16d2a43`)
- **스코프**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis 외부 의존성 장애 대응 패턴
- **방법**: `grep -rl` 기반 호출 지점 추출 → 파일별 정적 분석 (38 FMP 파일 + 46 Gemini 파일 + 보조 의존성)

---

## 1. 의존성 매트릭스 (서비스별 외부 API × 보호 수단)

| 외부 의존성 | 코어 클라이언트 | Timeout | Retry | Circuit Breaker | Rate Limit | Fallback | 캐시 | 종합 위험도 |
|---|---|---|---|---|---|---|---|---|
| **FMP API** | `api_request/providers/fmp/client.py` | ✅ 30s (코어) / ❌ news·thesis | ✅ 3회 (코어) / ❌ news·thesis·macro | ⚠️ sp500_eod·market_movers만 | ✅ 코어 0.2s sleep | ❌ Alpha Vantage 제거됨 | ⚠️ serverless만 | **HIGH** |
| **Gemini LLM** | `portfolio/llm/client.py` (소수 사용) | ❌ 거의 전부 미설정 | ⚠️ 모듈별 상이 (1~3회) | ⚠️ thesis·rag만 | ❌ news만 4초 간격 준수 | ⚠️ portfolio만 Anthropic 폴백 | ❌ | **HIGH** |
| **FRED API** | `macro/services/fred_client.py` | ✅ 30s | ✅ 3회 지수 (2/4/6s) | ❌ | ✅ 120/min | ✅ 기본값(VIX=20 등) | ✅ TTL 60s~24h | **LOW** |
| **Neo4j** | `rag_analysis/services/neo4j_driver.py` | ⚠️ pool 60s | ❌ | ✅ 5회 임계 / 60s 차단 | N/A | ✅ silent None | ✅ 메모리 | **MEDIUM** |
| **SEC EDGAR** | `sec_pipeline/collector.py` | ✅ 30/60s | ❌ | ❌ | ✅ 0.12s (10 req/s) | ⚠️ edgartools 선택 | ❌ | **MEDIUM** |
| **Redis** | settings 직결 | ⚠️ 암묵적 | ❌ | 자체 상태 저장만 | N/A | ❌ ConnectionError 무처리 | N/A | **HIGH** |

> **핵심 관찰**: 코어 클라이언트(`api_request/providers/fmp/client.py`, `portfolio/llm/client.py`)에는 보호 장치가 있으나, **상위 레이어(tasks·services)가 코어를 우회**해 `genai.Client()`·`requests.get()`을 직접 인스턴스화하는 패턴이 광범위. 즉 "보호된 입구"와 "비보호된 입구"가 공존.

---

## 2. FMP 상세

### 2.1 호출 지점 보호 수준 분포 (38 파일)

| 파일 | 호출 방식 | try/except | 402 처리 | Rate Limit | Retry | Timeout | 위험도 |
|------|-----------|------------|----------|-----------|-------|---------|--------|
| `api_request/providers/fmp/client.py` | 코어 | ✅ 3단계 | ✅ raise `FMPPremiumError` | ✅ 0.2s + daily quota | ✅ 3회 지수 | ✅ 30s | LOW |
| `api_request/providers/fmp/provider.py` | 래퍼 | ✅ | ✅ warn + PREMIUM_ONLY | ✅ raise `RateLimitError` | (코어 위임) | (코어) | LOW |
| `api_request/stock_service.py` | 서비스 | ✅ 부분 | ⚠️ warning만 | ⚠️ `call_with_fallback`만 | (코어) | (코어) | MEDIUM |
| `stocks/services/sp500_eod_service.py` | EOD 배치 | ✅ | ✅ Exception 통합 | ✅ 0.3s + CB | (코어) | (코어) | LOW |
| `stocks/services/sp500_service.py` | 구성종목 | ✅ | ⚠️ Exception 통합 | ✅ CB + 재시도 | (코어) | (코어) | MEDIUM |
| `stocks/tasks.py` | Celery 배치 | ✅ 대부분 | ⚠️ 무시 | ✅ 7s countdown | ✅ Celery retry | (코어) | MEDIUM |
| `serverless/services/fmp_client.py` | 별도 클라이언트 | ✅ | ❌ | ⚠️ 캐시만 | ❌ | ✅ httpx 30s | MEDIUM |
| `serverless/services/data_sync.py` | Market Movers | ✅ | ❌ | ✅ CB + 5s | ✅ Celery 5분 | (코어) | MEDIUM |
| `macro/services/fmp_client.py` | **별도 클라이언트** | ✅ 부분 | ❌ | ⚠️ 0.2s sleep | ❌ | ✅ 30s | **HIGH** |
| `macro/services/macro_service.py` | 지수/환율 | ⚠️ 일부 | ❌ | ❌ | ❌ | (위임) | **HIGH** |
| `news/providers/fmp.py` | 뉴스 수집 | ✅ 빈 리스트 | ❌ | ❌ | ❌ | ❌ | **HIGH** |
| `news/services/aggregator.py` | 뉴스 통합 | ✅ | ❌ | ❌ | ❌ | (위임) | MEDIUM |
| `thesis/tasks/eod_pipeline.py` | **EOD 지표** | ⚠️ 광범위 except | ❌ | ❌ | ❌ | ❌ | **HIGH** |
| `thesis/views/monitoring_views.py` | 사용자 요청 | ⚠️ | ❌ | ❌ | ❌ | (위임) | MEDIUM |
| `stocks/views_search.py` | 검색 | ⚠️ | ❌ | ❌ | ❌ | (위임) | MEDIUM |

### 2.2 핵심 위험 지점 (FMP)

1. **`thesis/tasks/eod_pipeline.py` — 무방어 직접 호출**
   - 400+ 종목 × 10 지표 ≈ 4,000+ call/day (Starter 일일 한도의 40%)
   - 402/429/timeout 전용 처리 없음 → 거래 신호 생성 즉시 중단
2. **`macro/services/fmp_client.py` — 별도 클라이언트가 코어 우회**
   - 지수/환율 11종 동시 조회. retry/CB 없음. 402 미처리.
3. **`news/providers/fmp.py` — silent failure**
   - 모든 예외를 `[]`로 흡수 → 호출자가 장애 인지 불가, 뉴스 누락 가시성 0.
4. **`stocks/tasks.py` — 부분 실패 무시**
   - 가격은 갱신, 재무제표는 실패해도 태스크 성공 → 데이터 일관성 깨짐.
5. **Fallback Provider 부재**
   - `api_request/factory.py`의 `call_with_fallback()`은 Alpha Vantage 경로가 제거되어 FMP 단독 의존.

### 2.3 FMP 장애 시나리오 영향도

| 장애 유형 | 영향 기능 | 심각도 | 자동 복구 |
|---|---|---|---|
| HTTP 5xx | 전 기능 | CRITICAL | 코어 3회 retry 후 raise |
| 402 Premium | thesis 지표·일부 심볼 | HIGH | ❌ 수동 |
| 429 Rate Limit | 배치 | MEDIUM | CB/Celery retry (부분) |
| 응답 지연(>30s) | UI | MEDIUM | timeout 적용지점만 |
| Daily quota 소진 | 전 배치 | CRITICAL | 익일 자정까지 정지 |

---

## 3. Gemini 상세

### 3.1 호출 지점 보호 수준 분포 (46 파일 중 핵심)

| 파일 | 클라이언트 | sync/async | 429 처리 | Timeout | JSON 파싱 | Prompt Sanitize | 위험도 |
|---|---|---|---|---|---|---|---|
| `portfolio/llm/client.py` | **중앙 LLMClient** | sync | ✅ 1회 retry + Anthropic 폴백 | ❌ | ⚠️ 호출자 책임 | ❌ | MEDIUM |
| `thesis/services/prompt_builder.py` | 직접 `genai.Client` | sync | ❌ (CB만) | ❌ | ⚠️ `call_gemini_light`는 raw text | ✅ 길이 500 + 구분자 제거 | HIGH |
| `thesis/services/thesis_builder.py` | 직접 | sync | ⚠️ CB `gemini_thesis` | ❌ | ✅ structured + fallback parse | ⚠️ | MEDIUM |
| `thesis/services/indicator_matcher.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ✅ 길이 500 | MEDIUM |
| `thesis/tasks/summary.py` | 직접 | **sync (✅ #8 회피)** | ⚠️ Celery retry 2회 | ✅ soft 300s | ⚠️ | ❌ | MEDIUM |
| `thesis/views/conversation_views.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | HIGH |
| `news/services/news_deep_analyzer.py` | 직접 | sync | ⚠️ **4s 간격(RPM 준수)** | ❌ | ⚠️ `_parse_response` | ❌ **뉴스 본문 직주입** | **HIGH** |
| `news/services/keyword_extractor.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `news/services/stock_insights.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `rag_analysis/services/llm_service.py` | 직접 | sync (스트리밍) | ✅ **3회 지수(1/2/4s)** | ❌ | ⚠️ | ❌ | MEDIUM |
| `rag_analysis/services/adaptive_llm_service.py` | 직접 | sync | ⚠️ | ❌ | ⚠️ | ❌ | MEDIUM |
| `rag_analysis/services/context_compressor.py` | 직접 | sync | ⚠️ CB `gemini_compress` | ❌ | ⚠️ | ❌ | MEDIUM |
| `rag_analysis/services/entity_extractor.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `sec_pipeline/extractor.py` | Lazy `_get_client()` | sync | ❌ (re-raise) | ❌ | ✅ `JSONDecodeError` 포착 → error dict | (문서만) | MEDIUM |
| `sec_pipeline/intelligence.py` | 직접 | sync | ❌ | ❌ | ⚠️ | (문서만) | MEDIUM |
| `serverless/services/keyword_generator.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `serverless/services/keyword_generator_v2.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `serverless/services/keyword_service.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `serverless/services/thesis_builder.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `serverless/services/llm_relation_extractor.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `serverless/services/relationship_keyword_enricher.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `serverless/services/regulatory_service.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `serverless/services/csv_url_resolver.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `validation/services/llm_peer_filter.py` | 직접 | sync | ❌ | ❌ | ✅ error dict | ⚠️ | MEDIUM |
| `marketpulse/briefing/client.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |
| `stocks/services/korean_overview_service.py` | 직접 | sync | ❌ | ❌ | ⚠️ | ❌ | MEDIUM |

### 3.2 핵심 위험 지점 (Gemini)

1. **명시적 timeout이 거의 전무**
   - `GenerateContentConfig(timeout=...)` 사용처 0건. Celery `soft_time_limit`이 유일한 안전망 → 사용자 동기 요청(conversation_views, RAG)은 무한 대기 가능.
2. **429 처리가 모듈별 천차만별**
   - `rag_analysis/llm_service.py`만 3회 지수 백오프. 나머지 대부분은 일반 Exception으로 흡수 → Free Tier 15 RPM에서 동시 사용자 2~3명이면 분 단위 소진.
3. **사용자 입력 기반 호출의 RPM 제어 부재**
   - `thesis/views/conversation_views.py`, `validation/llm_peer_filter.py`, RAG는 호출 빈도 측정 없음.
4. **Prompt Injection 잠재 위험 (HIGH)**
   - `news/services/news_deep_analyzer.py`: 외부 RSS 뉴스 헤드라인/본문을 프롬프트에 직주입, sanitization 없음.
   - `serverless/services/csv_url_resolver.py`, `relationship_keyword_enricher.py`: 외부 URL/관계 텍스트 직주입.
   - 방어 명시: `thesis/services/indicator_matcher.py`, `prompt_builder._parse_free_input`만 (길이 500 + 구분자 제거).
5. **Fallback 모델 부재**
   - `portfolio/llm/client.py`만 Anthropic 폴백 보유. 나머지는 `gemini-2.5-flash` 고정. Gemini 장애 = 기능 정지.
6. **공통 클라이언트 표준 미정착**
   - 중앙 `LLMClient` 우회한 직접 `genai.Client()` 인스턴스화가 ~25개 모듈에 산재. 정책 변경(타임아웃·재시도) 시 일괄 적용 불가.

### 3.3 Common-Bugs #8 (async LLM in Celery) 준수 현황

- ✅ 검토된 Celery 태스크(`thesis/tasks/summary.py`, `sec_pipeline/tasks.py`, `rag_analysis/tasks.py`, `news/tasks.py`)에서 **async API 미사용 확인**.
- 신규 task 추가 시 `async def generate_content_async`를 사용하지 않도록 PR 체크리스트 강화 필요.

---

## 4. 기타 의존성

### 4.1 FRED API — **LOW**

- `macro/services/fred_client.py`: 지수 백오프 3회 (2/4/6s), 401/403/404 즉시 raise, 5xx/Network는 retry.
- Rate limit 120/min을 `get_rate_limiter("fred")`로 강제.
- TTL 캐시: realtime 60s, daily 1h, monthly 24h.
- Fallback: VIX=20, yield_spread=1.0 등 안전 기본값.
- **잔존 위험**: 모든 지표 동시 실패 시 대시보드가 기본값으로 채워져 사용자가 장애 인지 못함.

### 4.2 Neo4j — **MEDIUM**

- `rag_analysis/services/neo4j_driver.py`: lazy connection, 실패 시 driver=None.
- Circuit Breaker: 5회 실패 → 60s 차단 → HALF_OPEN 복구.
- 29개 try/except로 모든 쿼리 wrap, `is_available()` 사전 체크.
- pool: max_connection_lifetime=3600s, pool_size=50.
- **잔존 위험**:
  - 동기화 태스크(`sync_profiles_to_neo4j` 등)는 실패 시 `neo4j_dirty=True` 유지 → DLQ/재시도 정책 미비.
  - 5회 임계 도달 전까지는 매 호출 timeout 누적 가능.

### 4.3 SEC EDGAR — **MEDIUM**

- `sec_pipeline/collector.py`: 0.12s sleep으로 10 req/s 정책 준수, User-Agent 정확.
- Timeout: 30s(metadata) / 60s(HTML).
- 3단 Fallback: regex → edgartools(선택) → 원문 저장(`status='partial'`).
- **잔존 위험**:
  - Retry 없음 → 일시적 5xx 시 즉시 실패.
  - edgartools 미설치 환경에서는 추출 품질 저하.
  - CIK 조회 실패 시 None → 심볼이 silent하게 누락.

### 4.4 Redis — **HIGH**

- `config/settings.py:499-515`: `django.core.cache.backends.redis.RedisCache` (DB=1), Celery broker/backend(DB=0), Channels Layer.
- **`IGNORE_EXCEPTIONS` 미설정** → Redis 다운 시 `ConnectionError` 전파 → 5xx 즉각 발생.
- Celery 브로커가 Redis 단독 의존 (RabbitMQ/SQS failover 없음) → Redis 다운 = 비동기 파이프라인 전체 정지.
- **잔존 위험**:
  - 캐시 장애 시 graceful degradation 코드 없음.
  - 브로커 장애 시 EOD/주기 배치 누락 — 야간 자동화(`com.stockvis.nightly`)와 결합 시 무인 시간 장애.

### 4.5 Alpha Vantage — **N/A (제거됨)**

- `api_request/factory.py`의 `call_with_fallback()`은 코드는 존재하나 Alpha Vantage 경로가 비활성화됨.
- 실질적 multi-provider failover 없음.

---

## 5. Circuit Breaker 도입 후보 (우선순위)

장애 시 cascade 영향이 크고 현재 보호가 없는 호출 지점:

| 우선 | 후보 지점 | 사유 | 권장 임계값 |
|------|----------|------|-------------|
| **P0** | `thesis/tasks/eod_pipeline.py::_fetch_fmp_value` | 일 4,000+ call, FMP 한도 40% 점유. 장애 시 거래 신호 전체 중단 | 5 failures / 120s recovery |
| **P0** | `macro/services/fmp_client.py::get_batch_quotes` | 11종 동시 조회, 코어 우회, 사용자 대시보드 실시간 영향 | 5 / 60s |
| **P0** | Redis cache 전반 (`django.core.cache`) | Redis 다운 시 5xx 즉시. `IGNORE_EXCEPTIONS=True` + CB 병행 필요 | 자체 + 캐시 bypass 폴백 |
| **P1** | `news/providers/fmp.py::get_stock_news/general_news/press_releases` | silent failure, 뉴스 수집 가시성 0 | 5 / 60s + 메트릭 |
| **P1** | `thesis/views/conversation_views.py` Gemini 호출 | 사용자 동기 요청, 무한 대기 가능 | 5 / 60s + 30s timeout |
| **P1** | `news/services/news_deep_analyzer.py` Gemini 호출 | 매일 50건 배치, 429 누적 시 cascade | 5 / 120s |
| **P1** | `serverless/services/keyword_generator*.py` & `thesis_builder.py` Gemini | 사용자 트리거, RPM 제어 없음 | 5 / 60s + RPM limiter |
| **P2** | `sec_pipeline/collector.py::fetch_filing_html` | 일시 5xx에 즉시 실패, retry 부재 | 3 / 300s + 1회 retry |
| **P2** | `stocks/tasks.py::update_stock_with_provider` 부분 실패 | 데이터 일관성 깨짐, 가시성 부족 | 메트릭 우선, CB는 옵션 |
| **P2** | `chainsight/tasks/sync_tasks.py` Neo4j 동기화 DLQ | 실패 후 `neo4j_dirty` 영구화 | DLQ + 재시도 백오프 |

### 5.1 공통 권장 패턴 (구현 시 참고)

1. **`portfolio/llm/client.py`의 중앙 LLMClient를 표준으로 승격** — 25개 Gemini 직접 호출 모듈을 점진적으로 마이그레이션. 정책(timeout·retry·CB·Anthropic 폴백) 단일 소스화.
2. **모든 Gemini 호출에 명시적 30~60s timeout 강제** — `concurrent.futures.ThreadPoolExecutor + future.result(timeout=...)` 또는 `httpx.Timeout` wrapper.
3. **Redis: `CACHES['default']['OPTIONS']['IGNORE_EXCEPTIONS'] = True` + `DJANGO_REDIS_IGNORE_EXCEPTIONS = True`** 적용 후 캐시 미스로 graceful degradation.
4. **FMP 402/429 처리 통일** — 코어 `FMPPremiumError`/`FMPRateLimitError`를 상위 레이어에서도 명시 except. 현재 `macro/`·`thesis/`·`news/`에서 누락.
5. **Prompt Injection sanitization 유틸 공통화** — `thesis/services/prompt_builder._parse_free_input` 패턴(길이 500 + 구분자 제거 + 시크릿 마스킹)을 `core/security/prompt_sanitize.py`로 추출.
6. **알람/메트릭** — silent failure(`return []`, `return None`) 지점에 Prometheus counter 추가. "조용한 장애"는 CB보다 메트릭이 우선.

---

## 6. 부록: 통계 요약

- **FMP 호출 파일**: 38개 (코어 1 + 코어 우회 별도 클라이언트 2: `serverless/services/fmp_client.py`, `macro/services/fmp_client.py`)
- **Gemini 호출 파일**: 46개 (테스트·스크립트 제외 운영 코드 ~26개)
- **명시적 timeout 보호 Gemini 호출 지점**: **0건** (Celery soft_time_limit 의존만 1건)
- **429 retry/backoff 명시 Gemini 모듈**: 1건 (`rag_analysis/services/llm_service.py`)
- **Anthropic 폴백 보유 모듈**: 1건 (`portfolio/llm/client.py`)
- **FMP 402 명시 처리 모듈**: 2건 (코어 + provider 래퍼). 상위 레이어 미적용.
- **Circuit Breaker 운영 중**: thesis/rag(Gemini), sp500_eod/market_movers(FMP), neo4j_driver — 총 5종.
- **Redis IGNORE_EXCEPTIONS**: ❌ 미설정.

---

## 7. 결론

코어 클라이언트 레벨(`api_request/providers/fmp/client.py`, `portfolio/llm/client.py`, `macro/services/fred_client.py`, `rag_analysis/services/neo4j_driver.py`)은 비교적 견고하다. 그러나 **상위 레이어에서 코어를 우회하는 직접 호출이 광범위**하며, 보호 정책이 모듈별로 일관성 없이 적용되어 있다.

**가장 시급한 3대 위험**:
1. **Gemini 호출 전반의 timeout 부재** — 사용자 요청(`thesis/views/conversation_views.py`)에서 무한 대기 가능.
2. **Redis 장애 시 graceful degradation 부재** — `IGNORE_EXCEPTIONS` 미설정으로 캐시 다운이 즉시 5xx로 전파.
3. **`thesis/tasks/eod_pipeline.py`의 무방어 FMP 호출** — 일일 한도의 40%를 차지하는 핵심 배치가 retry·CB·timeout 모두 부재.

P0 3건을 우선 처리하면 야간 자동화(`com.stockvis.nightly`)의 무인 시간 장애 위험을 크게 낮출 수 있다.
