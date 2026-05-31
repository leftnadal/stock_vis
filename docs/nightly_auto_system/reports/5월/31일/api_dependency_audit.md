# 외부 API 의존성 감사 보고서

> **작성일**: 2026-05-31
> **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis 외부 의존성의 장애 대응(에러 핸들링, retry, fallback, circuit breaker)
> **방식**: 읽기 전용 정적 분석 (코드 수정 없음)
> **핵심 결론**: 데이터 수집 핵심 경로(SP500 / Market Movers / 거시 / Neo4j)는 **Circuit Breaker가 이미 도입**되어 견고함. 그러나 **(1) FMP 클라이언트 이중 구현**, **(2) Gemini 호출 14개 파일 분산 + 429/timeout 미처리**, **(3) Redis 장애 시 API 폭증 위험**이 3대 리스크.

---

## 0. 아키텍처 핵심 발견 (Executive Summary)

| 발견 | 내용 | 영향 |
|------|------|------|
| **이중 FMP 클라이언트** | `packages/shared/.../fmp/client.py`(프로덕션급, 402/429/401/403 구분 + exponential backoff) vs `serverless/`·`macro/`·`news/`의 3개 별도 클라이언트(단순 단일 에러, retry 없음) | 일관성 없는 에러 처리, 신규 코드가 어느 쪽을 쓰는지 모호 |
| **Circuit Breaker 이미 부분 도입** | `apps.market_pulse.utils.circuit_breaker.get_circuit()`가 단일 소스. FMP 5곳 + Neo4j + Gemini 4곳에 적용 | 핵심 수집 경로는 cascade 방어됨 → **이번 감사의 가장 긍정적 발견** |
| **이중 Circuit Breaker 구현** | `apps.market_pulse.utils.circuit_breaker`(주력, get_circuit 팩토리) vs `news/services/circuit_breaker.py`(news 전용 별도 클래스) | 두 구현 공존, 표준화 필요 |
| **Gemini 공통 래퍼 부재** | 14개 파일이 각자 `genai` 직접 호출. 429 재시도는 2개 파일만, timeout은 **전 파일 미설정** | LLM 장애 시 광범위 부분 실패 |
| **Redis graceful degradation 부분적** | `cache.get/set`은 try/except로 감싸 앱은 안 죽음. 단 캐시 미스 시 외부 API 폭증 → rate limit 연쇄 위험 | Redis 다운이 FMP/FRED rate limit 장애로 전이 가능 |
| **Alpha Vantage 미사용** | 코드 내 active 호출 없음, 마이그레이션 문서만 잔존 | 의존성 제거됨 (positive) |

---

## 1. 의존성 매트릭스

### 1.1 외부 API × 장애 대응 종합

| 의존성 | 클라이언트 위치 | 에러 분류 | Retry | Timeout | Circuit Breaker | Fallback | 종합 |
|--------|----------------|-----------|-------|---------|-----------------|----------|------|
| **FMP (정식)** | `packages/shared/api_request/providers/fmp/client.py` | ✅ 402/429/401/403 구분 | ✅ 3회 exp backoff(2/4/6s) | ✅ 30s | △ 호출처별 | provider→ProviderResponse | 🟢 우수 |
| **FMP (serverless)** | `serverless/services/fmp_client.py` | ❌ 단일 `FMPAPIError` | ❌ 없음 | ✅ httpx 기본 | ✅ (호출처) | 빈 리스트 | 🟡 보통 |
| **FMP (macro)** | `macro/services/fmp_client.py` | ❌ `raise_for_status`만 | ❌ 없음 | ✅ 30s | ❌ | None 반환(부분) | 🟡 보통 |
| **FMP (news)** | `news/providers/fmp.py` | ❌ generic | ❌ 없음 | (위임) | ❌ | 빈 리스트 | 🟡 보통 |
| **Gemini (정식 래퍼)** | `apps/portfolio/llm/client.py` | ✅ RateLimit/Timeout 분류 | ✅ 1회+provider fallback | ❌ 미설정 | ❌ | Anthropic으로 전환 | 🟢 우수 |
| **Gemini (RAG)** | `rag_analysis/services/llm_service.py` | △ 문자열 매칭 | ✅ 3회(rate/quota만) | ❌ | ✅ `gemini` | 사용자 메시지 | 🟢 양호 |
| **Gemini (나머지 12개)** | thesis/serverless/news/validation/sec | ❌ 대부분 generic | ❌ 대부분 없음 | ❌ **전무** | △ thesis만 | None/[]/error dict 혼재 | 🔴 취약 |
| **FRED** | `macro/services/fred_client.py` | ✅ Transient/Permanent 구분 | ✅ 3회 exp backoff | ✅ 30s | ❌ | 기본값(VIX=20 등) | 🟢 우수 |
| **Neo4j** | `rag_analysis/services/neo4j_driver.py` + `serverless/.../neo4j_chain_sight_service.py` | ✅ lazy init + CB | △ CB 단위 | N/A | ✅ `neo4j` CB | PostgreSQL fallback | 🟢 우수 |
| **SEC EDGAR** | `sec_pipeline/collector.py` | ✅ rate limit 준수 | ✅ Celery 3~5회 | ✅ 15~60s | ❌ | edgartools 라이브러리 | 🟢 우수 |
| **Redis** | `config/settings.py` (CACHES) | △ try/except 산발 | ❌ | N/A | ❌ | 캐시 미스 처리 | 🟡 주의 |
| **Alpha Vantage** | (미사용) | — | — | — | — | — | ⚪ N/A |

### 1.2 서비스별 외부 의존성 × fallback 유무

| 서비스/태스크 | 의존 API | fallback 전략 | Celery retry |
|---------------|----------|---------------|--------------|
| `sp500_service.sync` | FMP | CB open → 빈 결과 반환 | max_retries=3, countdown 300·600·900s |
| `sp500_eod_service` | FMP | CB(threshold=10) → 종목 skip | (상위 태스크) |
| `data_sync.MarketMoversSync` | FMP | CB(threshold=5) → 타입별 빈 리스트 | — |
| `sector_heatmap_service` | FMP | CB(섹터별) → None, skip | — |
| `market_breadth_service` | FMP | ❌ FMPAPIError 그대로 전파 | — |
| `enhanced_screener_service` | FMP | 빈 결과 반환 | — |
| `macro_service` | FRED/FMP | 기본값(VIX=20, spread=1.0) | max_retries=3 (tasks) |
| `neo4j_chain_sight_service` | Neo4j | `is_available()` 가드 → 빈 그래프 + PostgreSQL | — |
| `thesis/eod_pipeline._fetch_fmp_value` | FMP | FMPPremiumError catch → (None,None) | — |
| `news/aggregator` | FMP/Finnhub/Marketaux | provider 선택적, init 실패해도 타 provider | — |
| `sec_pipeline.collect_and_extract` | SEC EDGAR | edgartools fallback | max_retries 3~5 단계별 |
| `rag_analysis` LLM | Gemini + Neo4j | CB + 캐시 + truncate | — |

---

## 2. FMP 상세

### 2.1 정식 클라이언트 — `packages/shared/api_request/providers/fmp/client.py` 🟢

가장 견고한 구현. **이것이 표준이 되어야 함.**

- **에러 계층** (L21-42): `FMPClientError` → `FMPRateLimitError`/`FMPAuthError`/`FMPPremiumError(402)`
- **Rate limit** (L103-115): `request_delay=0.2s` 강제 + 일일 10,000 카운터 → 초과 시 `FMPRateLimitError`
- **Retry** (L120-172): `max_retries=3`, exponential backoff(2/4/6s). **단 402/401/403/429는 즉시 전파**(재시도 무의미하므로 올바름)
- **Timeout** (L124): `timeout=30`
- **200 OK 위장 에러** (L148-152): `"Error Message"` 키 검사 → `Invalid API KEY`면 `FMPAuthError`

**Provider 레이어** (`provider.py`): `FMPPremiumError` → `error_code="PREMIUM_ONLY"` 응답, `FMPRateLimitError` → 상위 `RateLimitError`로 변환(L85-86 등 8곳).

> ⚠️ **부채**: `factory.py`의 `FALLBACK_CHAIN[ProviderType.FMP] = []` — FMP 실패 시 대체 provider 없음. 단일 공급자 의존.

### 2.2 별도 클라이언트 3종 — 🟡 기술 부채

| 파일 | 에러 처리 | 핵심 문제 |
|------|-----------|-----------|
| `serverless/services/fmp_client.py` | `httpx.HTTPStatusError`/`RequestError` → 단일 `FMPAPIError` | **402/429 미구분**, retry 없음 |
| `macro/services/fmp_client.py` | `response.raise_for_status()` + `ValueError` | 상태코드 검사 없음, retry 없음, `get_quote`만 None 반환 |
| `news/providers/fmp.py` | `except Exception → return []` | 모든 예외 동일 처리, 로깅만 |

**리스크**: 동일한 FMP 장애가 호출 경로에 따라 ① 즉시 전파, ② 빈 리스트, ③ None으로 제각각 처리됨. 신규 개발자가 어느 클라이언트를 써야 하는지 불명확.

### 2.3 Circuit Breaker 적용 현황 (FMP) 🟢

`apps.market_pulse.utils.circuit_breaker.get_circuit()` 기반:

| 호출처 | CB 이름 | threshold / recovery |
|--------|---------|---------------------|
| `sp500_service.py:39` | `fmp_sp500_constituents` | 3 / 300s |
| `sp500_eod_service.py:138` | `fmp_sp500_eod` | 10 / 120s |
| `data_sync.py:74` | `fmp_market_movers` | 5 / 120s |
| `sector_heatmap_service.py:127` | `fmp_sector_{name}` | 5 / 120s |
| `fmp_weights.py:53` | `fmp_etf` | 기본값 |
| `news_aggregator.py:105` | `fmp_news` | 기본값 |

> **공백**: `market_breadth_service`, `enhanced_screener_service`, `chain_sight_service`, `keyword_data_collector`, `thesis/eod_pipeline`는 CB 미적용 — FMP 직접 호출.

---

## 3. Gemini 상세

### 3.1 async/sync 규칙 (Bug #8) — ✅ 위반 없음

- `rag_analysis/*`: `client.aio.models.*` (async 컨텍스트에서만) — 올바름
- `thesis/`, `serverless/`, `news/`, `validation/`, `apps/`: 모두 sync `client.models.generate_content()` — Celery 안전
- `apps/market_pulse/briefing/client.py:48` `_generate_sync()` — 주석에 `Bug #8: 동기 호출만 사용` 명시
- **결론**: Celery에서 async LLM 호출 위반 0건.

### 3.2 429 / retry 처리 — 🔴 2/14 파일만 구현

| 패턴 | 파일 | 방식 |
|------|------|------|
| ✅ 재시도 | `rag_analysis/services/llm_service.py:245-264` | 문자열 매칭(`rate`/`quota`/`429`) + `RETRY_DELAYS=[1,2,4]`, 3회 |
| ✅ 재시도+전환 | `apps/portfolio/llm/client.py:61-187` | `_classify_gemini_error` → `LLMRateLimitError` → 1회 재시도 후 **Anthropic으로 provider fallback** |
| ❌ 미처리 | 나머지 12개 (thesis_builder, prompt_builder, entity_extractor, keyword_*, news_*, validation, sec_pipeline 등) | generic `except Exception` → None/[]/error dict |

### 3.3 JSON 파싱 견고성 — △ 혼재

- ✅ **마크다운 코드블록 제거**: `entity_extractor.py:115-134` `_clean_json_response()` (```json 제거) — **모범 사례, 횡전개 권장**
- ✅ **구조화 출력**: `validation/services/llm_peer_filter.py:79` `response_mime_type='application/json'` — 가장 안전
- △ **정규식 추출**: `thesis_builder.py:486` `re.search(r'\{.*\}', ...)` — 코드블록 정리 없음
- ❌ **파싱 방어 없음**: 다수 파일이 `json.loads` 직접 호출 또는 `_parse_response` 내부 불투명

### 3.4 Timeout — 🔴 전 파일 미설정

**14개 파일 모두 `generate_content`에 명시적 timeout 없음.** Google `genai` SDK 기본 동작에 의존. 동시 부하 시 워커 점유 → cascade 위험. **가장 시급한 공통 결함.**

### 3.5 Circuit Breaker 적용 (Gemini)

| 호출처 | CB 이름 |
|--------|---------|
| `llm_service.py:198` | (RAG 분석) |
| `context_compressor.py:136,288` | `gemini_compress` (5/60s) |
| `thesis_builder.py:470` | `gemini_thesis` (5/120s) |
| `briefing/client.py:72` | `gemini` |

---

## 4. 기타 의존성

### 4.1 FRED — `macro/services/fred_client.py` 🟢
- Transient(500/502/503/504) 재시도 vs Permanent(401/403/404) 즉시 raise 구분 (L98-153)
- 3회 exponential backoff, timeout 30s
- `MacroEconomicService`: 실패 시 기본값(VIX=20, spread=1.0) — degradation 우수
- Celery `update_economic_indicators`: max_retries=3, `countdown=60*(2**retries)`

### 4.2 Neo4j — `neo4j_driver.py` + `neo4j_chain_sight_service.py` 🟢
- **Lazy init** (L20-68): 연결 실패해도 앱 안 죽음, `None` 반환 후 `"continue without Neo4j"`
- **Fork 안전** (L102-113): C 확장 SIGSEGV 방지 (Bug #25 관련)
- **CB + is_available() 가드**: 모든 public 메서드가 미가용 시 빈 결과(`{"nodes":[],"edges":[]}`)
- **PostgreSQL fallback**: `StockRelationship` 모델로 대체 (L575-692)
- **degradation 최상**: Neo4j 완전 다운에도 핵심 기능 유지

### 4.3 SEC EDGAR — `sec_pipeline/collector.py` 🟢
- User-Agent 헤더 필수 준수 (L29-32)
- **Rate limit**: `time.sleep(0.12)` (~8.3 req/s, SEC 10/s 이하)
- Timeout 15~60s 단계별
- edgartools fallback (L189-215)
- Celery 단계별 retry: 메타 3회 / HTML 5회 / 추출 1회

### 4.4 Redis — `config/settings.py` 🟡 **주의**
- 캐시 + Celery broker/backend 모두 Redis (`localhost:6379`, db 0/1)
- `@cached_provider_call`, `rag_analysis/services/cache.py`: `cache.get/set`을 try/except로 감싸 → **예외가 앱을 죽이지 않음**
- **리스크**: Redis 다운 시 캐시 미스로 **매 요청 외부 API 직접 호출** → FMP/FRED rate limit 도달 → 2차 장애 전이. Celery broker까지 Redis라 Redis 다운 = 전체 비동기 파이프라인 중단.

### 4.5 Alpha Vantage — ⚪ 미사용
- active 호출 코드 없음. `docs/migration/*`에 이력만. 의존성 제거 완료.

---

## 5. Circuit Breaker 도입 후보 (우선순위)

장애 시 전체 시스템 영향이 큰 미적용 호출 지점:

### 🔴 P1 — 즉시 도입 권장
| 후보 | 위치 | 사유 |
|------|------|------|
| **Gemini 공통 호출 래퍼** | 14개 분산 파일 통합 | 429 재시도 2/14, timeout 0/14. 단일 래퍼(`apps/portfolio/llm/client.py` 확장)로 retry+timeout+CB+JSON정리 표준화 |
| **Redis 장애 → API 폭증 차단** | `cached_provider_call` 데코레이터 | Redis 다운 시 외부 API rate limit 2차 장애 방지 (캐시 미스 시 호출 throttle 또는 stale-while-error) |

### 🟡 P2 — 도입 검토
| 후보 | 위치 | 사유 |
|------|------|------|
| `market_breadth_service` | FMP 3-call(gainers/losers/actives) | 현재 FMPAPIError 그대로 전파 → 메인 페이지 영향. CB + 빈 결과 fallback |
| `thesis/eod_pipeline._fetch_fmp_value` | FMP 지표값 수집 | EOD 배치 핵심, CB 미적용 |
| `chain_sight_service` FMP 호출 | 4곳 | 혼합 처리, CB 표준화 |
| `sec_pipeline` SEC 호출 | collector | retry는 있으나 CB 없음 — 대량 수집 시 SEC 차단 누적 방어 |
| FRED | `fred_client` | retry 우수하나 CB 없음 — FRED 장기 장애 시 매 호출 30s×3 대기 누적 |

### 🟢 P3 — 표준화(구조 부채)
| 항목 | 조치 |
|------|------|
| **FMP 클라이언트 단일화** | serverless/macro/news 3종 → `packages/shared` 정식 클라이언트로 통합 (402/429 일관 처리) |
| **Circuit Breaker 단일화** | `news/services/circuit_breaker.py` → `apps.market_pulse.utils.circuit_breaker`로 통합 |
| **Gemini fallback 정책 통일** | None/[]/error dict 혼재 → 단일 규약(예외 전파 or sentinel) |

---

## 6. 권장 조치 요약 (감사 결론)

| 우선순위 | 조치 | 근거 |
|----------|------|------|
| **P1** | 모든 Gemini `generate_content`에 timeout 부여 (전 14파일) | 현재 0/14, cascade 위험 최대 |
| **P1** | Gemini 공통 래퍼 도입 (429 retry + timeout + JSON 정리 + CB) | `entity_extractor._clean_json_response` + `portfolio/llm/client` 패턴 횡전개 |
| **P1** | Redis 장애 시 외부 API throttle/stale fallback | 캐시 미스 폭증 → rate limit 2차 장애 차단 |
| **P2** | `market_breadth`, `thesis/eod_pipeline`, `chain_sight`에 CB 적용 | 핵심 경로 CB 공백 |
| **P3** | FMP 클라이언트 4종 → 1종 단일화 | 402/429 처리 일관성 |
| **P3** | Circuit Breaker 2종 → 1종 단일화 | 구현 중복 제거 |

> **총평**: 데이터 수집 핵심 경로(SP500/Movers/거시/Neo4j/SEC)는 Circuit Breaker·retry·fallback이 잘 갖춰진 🟢 상태. 리스크는 **Gemini 호출의 분산·timeout 부재**와 **Redis 장애의 2차 전이**, 그리고 **FMP 클라이언트 이중화**에 집중됨. 신규 기능 추가 전 Gemini 공통 래퍼 정립이 가장 높은 ROI.

---

*본 보고서는 정적 코드 분석 기반이며, 런타임 부하/실제 장애 주입 테스트는 포함하지 않음. 라인 번호는 2026-05-31 기준 HEAD(`f80b7dd`) 시점.*
