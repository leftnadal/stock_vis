# 외부 API 의존성 감사 보고서

> **작성일**: 2026-06-03
> **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis 장애 대응 전수 조사
> **성격**: 읽기 전용 감사 (코드 미수정)
> **조사 규모**: FMP 호출 36개 파일, Gemini 호출 46개 파일 + 기타 4개 의존성
> **검증 방식**: 핵심 클라이언트 레이어 직접 정독 + 병렬 탐색 에이전트 3건. 일부 line 번호는 탐색 에이전트 보고 기준이며 별도 표기.

---

## 핵심 요약 (Executive Summary)

| 등급 | 발견 | 영향 |
|------|------|------|
| 🔴 **CRITICAL** | **Redis가 단일 장애점(SPOF)** — 캐시·Celery 브로커·CB 상태·WebSocket 4역할 겸직, cache 예외 graceful degradation 없음 | Redis 다운 시 캐시 의존 요청 500/타임아웃 + Circuit Breaker 자체 동작 불능 |
| 🔴 **HIGH** | **중앙 레이어 우회 raw FMP 호출 5건** — `FMPClient`/`get_circuit` 미경유, rate limit·재시도·CB 없음 | 다중 루프/병렬 실행 시 429 누적 → 데이터 갭, 사용자 요청 시 500 노출 |
| 🟠 **MEDIUM** | **Gemini 직접 호출 36개 중 JSON 파싱/응답 접근 방어 누락 3건** | LLM 응답 변형 시 `JSONDecodeError`/`AttributeError`로 task 실패 |
| 🟢 **양호** | FMP 중앙 `FMPClient`, RAG `LLMServiceLite`, Portfolio `LLMClient`, FRED `FREDClient`, SEC `collector` | 재시도·예외계층·폴백·rate limit 모두 구현 |

**가장 시급한 결론**: Circuit Breaker 인프라(`packages/shared/api_request/circuit_breaker.py`)는 잘 만들어져 있고 일부 경로에 적용되어 있으나, **(1) CB가 의존하는 Redis가 graceful degradation 없는 SPOF이고, (2) 중앙 레이어를 우회하는 raw 호출이 CB 보호망 밖에 다수 존재**한다. CB 확산보다 Redis 격리/우회 호출 통합이 선행되어야 한다.

---

## 1. 의존성 매트릭스 (서비스별 외부 API × fallback 유무)

| 의존성 | 중앙 레이어 | 대표 호출 지점 | 재시도 | Rate Limit | Circuit Breaker | Fallback / Graceful Degradation | 위험도 |
|--------|------------|---------------|--------|-----------|-----------------|----------------------------------|--------|
| **FMP (중앙)** | `FMPClient` / `FMPProvider` | `providers/fmp/client.py:85` | ✅ 3회 exp backoff | ✅ 0.2s delay + 일일 10k | △ (호출처에서 `get_circuit` 선택 적용) | ✅ 402/429 예외계층 → `error_response` | 🟢 낮음 |
| **FMP (raw 우회)** | ❌ 없음 | `quote_enricher.py:57`, `neo4j_loader.py`*, `sensitivity_tasks.py`* | ❌ | ❌ | ❌ | △ 빈 결과/None 반환 | 🔴 높음 |
| **Gemini (RAG)** | `LLMServiceLite` | `rag_analysis/services/llm_service.py:199` | ✅ 3회 + CB | n/a | ✅ `get_circuit("gemini_rag")` | ✅ CB OPEN 시 사용자 메시지 | 🟢 낮음 |
| **Gemini (Portfolio)** | `LLMClient` | `apps/portfolio/llm/client.py:131` | ✅ 1회 + 반대 provider 폴백 | n/a | ❌ | ✅ Gemini↔Anthropic 폴백 + CostGuard | 🟢 낮음 |
| **Gemini (Market Pulse)** | 직접 + CB | `apps/market_pulse/briefing/client.py:72`* | ✅ (CB) | n/a | ✅ `get_circuit("gemini")` | △ | 🟢 낮음 |
| **Gemini (기타 직접)** | ❌ 분산 | `indicator_matcher.py`*, `news/api/views.py`*, `llm_peer_filter.py`* | ❌ 대부분 없음 | n/a | ❌ | △ 일부 try/except | 🟠 중간 |
| **FRED** | `FREDClient` | `macro_service.py:57`* | ✅ 3회 exp backoff | ✅ 120/분 | ❌ | △ 지표별 부분 실패 허용, 캐시 폴백 없음 | 🟡 중간 |
| **Neo4j** | `Neo4jChainSightService` | `neo4j_chain_sight_service.py:108`* | △ (CB) | n/a | ✅ `get_circuit` + pool | ✅ `is_available()` False 시 빈 결과 | 🔴 높음(메타) |
| **SEC EDGAR** | `SECFilingCollector` | `sec_pipeline/collector.py:72`* | ❌ 즉시 raise | ✅ 0.12s (10/s) + UA | ❌ | ✅ edgartools 폴백 + partial status | 🟡 낮음 |
| **Redis** | Django cache | `config/settings.py:502` | ❌ | n/a | n/a | ❌ **없음** | 🔴 매우 높음 |

> `*` = 탐색 에이전트 보고 기준 line 번호 (핵심 클라이언트 외 파일은 직접 정독하지 않음). FMP/Gemini 중앙 레이어, `circuit_breaker.py`, `quote_enricher.py`, `config/settings.py`는 직접 확인.

---

## 2. FMP 상세

### 2.1 중앙 레이어 — 🟢 견고 (직접 확인)

**`packages/shared/api_request/providers/fmp/client.py`**
- `_make_request()` (L85–172): rate limiting(`request_delay=0.2s`, L107–110) + 일일 한도(`daily_limit=10000`, L113–115) + 재시도 3회 exponential backoff(L122–170) + `timeout=30`(L124)
- HTTP 상태 분기 완비: 401→`FMPAuthError`, **402→`FMPPremiumError`**, 403→`FMPAuthError`, 429→`FMPRateLimitError` (L129–138)
- 재시도 불필요 에러(`FMPPremiumError`/`FMPAuthError`/`FMPRateLimitError`)는 즉시 전파, 일시 에러만 재시도 (L156–170)

**`packages/shared/api_request/providers/fmp/provider.py`**
- 모든 메서드가 `FMPPremiumError`→`PREMIUM_ONLY`(L233–239), `FMPRateLimitError`→`RateLimitError`(L240–241), 기타→`error_response`로 일관 변환. **공통 버그 #23(402)/#14(필드명) 방어 패턴 정착.**

**Circuit Breaker 적용 모범 사례** (에이전트 확인):
- `packages/shared/stocks/services/sp500_service.py` — `get_circuit("fmp_sp500_constituents", failure_threshold=3, recovery_seconds=300)` + CB OPEN 시 빈 결과 폴백
- `apps/market_pulse/fetchers/fmp_weights.py` — `get_circuit("fmp_etf")` + `cb.call(...)`

### 2.2 raw 우회 호출 — 🔴 장애 취약 지점

중앙 `FMPClient`/`get_circuit`을 거치지 않고 `requests`/`httpx`로 `financialmodelingprep.com`을 직접 때리는 지점. **CB 보호망 밖**.

| # | 파일:라인 | 방식 | rate limit | 재시도 | fallback | CB | 위험도 | 비고 |
|---|----------|------|-----------|--------|----------|-----|--------|------|
| 1 | `apps/chain_sight/services/neo4j_loader.py:140–155`* (`fetch_fmp_peers`) | raw `requests.get` | ❌ | ❌ | ❌ 빈 `[]` | ❌ | **CRITICAL** | `collect_all_peers()` 루프 호출, `sleep(0.3)`만으로 300/분 보호 불가 |
| 2 | `apps/chain_sight/tasks/sensitivity_tasks.py:71–103`* (`_fetch_geo_revenue`) | raw `requests.get` | ❌ | ❌ | ❌ 빈 `{}` | ❌ | **CRITICAL** | Celery task 동시 실행 시 429 누적, `sleep(0.25)` 무의미 |
| 3 | `services/serverless/services/quote_enricher.py:57–74` (`_fetch_single_quote`) | `httpx` 직접 | ❌ | ❌ | △ 60s 캐시(만료시 소멸) | ❌ | **HIGH** | `ThreadPoolExecutor` 병렬(최대 50 배치) → 429 폭증, `raise_for_status()` 후 `None` (**직접 확인**) |
| 4 | `packages/shared/stocks/views.py:404`* (`_get_fmp_chart_data`) | `httpx` 직접 | ❌ | ❌ | ❌ `None` | ❌ | MEDIUM | API 뷰 직결 → 429 시 사용자에 HTTP 500 노출 |
| 5 | `packages/shared/stocks/services/stock_sync_service.py:318–323`* | `httpx` 직접 | ❌ | ❌ | ❌ | ❌ | MEDIUM | batch sync 루프 내 호출, rate limit 누적 |

**공통 문제**: `except Exception`으로 429를 구분하지 않고 흡수 → 일시적 rate limit과 영구 실패를 동일 취급, 백오프 후 재시도 기회 상실. 실패가 조용히 빈 데이터로 흡수되어 **silent data gap** 발생.

---

## 3. Gemini 상세

### 3.1 중앙 wrapper — 🟢 견고 (직접 확인)

**`services/rag_analysis/services/llm_service.py` (`LLMServiceLite`)**
- `get_circuit("gemini_rag", failure_threshold=5, recovery_seconds=60, retry_attempts=1)` async CB (L199–210)
- `MAX_RETRIES=3`, `RETRY_DELAYS=[1,2,4]` + 429/rate/quota 문자열 매칭 재시도 (L247–268)
- `CircuitBreakerError` 시 사용자 친화 메시지 + 재시도 중단 (L238–245)
- 프롬프트 인젝션 방어(닫는 태그 escape, L181–193) — 공통 버그 P0 #3
- JSON 파싱은 `ResponseParser`에서 `json.JSONDecodeError` 전부 try/except (L339–345, L385–387)

**`apps/portfolio/llm/client.py` (`LLMClient`)**
- `_classify_gemini_error`/`_classify_anthropic_error`로 RateLimit/Timeout/Auth/InvalidPrompt 통합 예외 계층 매핑 (L61–110)
- 1회 재시도 + **반대 provider 폴백**(Gemini↔Anthropic, L180–188) — 단일 provider 장애에 강함
- `CostGuard` 비용 가드 + `cost_ledger` append-only 기록 (L164–211)
- ⚠️ **Circuit Breaker 미적용** — 폴백으로 보완하나, 양 provider 동시 장애 시 보호 부재

**기타 CB 적용 양호**: `apps/market_pulse/briefing/client.py:72`*(`get_circuit("gemini")`), `services/rag_analysis/services/context_compressor.py:133`*(`get_circuit("gemini_compress")` async)

### 3.2 직접 호출 + 방어 누락 — 🟠 장애 취약 지점 (에이전트 보고)

총 36개 파일이 `genai.Client`를 직접 생성. 대부분 try/except는 있으나 아래는 방어 공백:

| 파일:라인 | 문제 | 심각도 |
|----------|------|--------|
| `thesis/services/indicator_matcher.py:236–240`* | regex 추출 후 `json.loads(json_match.group())`에 **try/except 없음** → `JSONDecodeError` 미처리 | **HIGH** |
| `services/news/api/views.py:852`* | `return response.text.strip()` — genai 에러 시 **속성 접근 try/except 없음** → `AttributeError` | **HIGH** |
| `services/validation/services/llm_peer_filter.py:79–86`* | `return json.loads(text)` — genai 호출·파싱 **둘 다 try/except 없음** | **HIGH** |
| `thesis/tasks/summary.py:66–76`* | Celery task 내 동기 호출(버그 #8 회피는 OK), CB 없음 + 실패 시 빈 문자열, 재시도 없음 | MEDIUM |

**공통 개선 포인트** (에이전트 관찰):
- **429/quota 상세 분류 부재** — 대부분 `except Exception` 단일 처리, 재시도 없이 None/빈값
- **timeout 미설정** — `genai.Client` 기본값 의존, `request_options={"timeout": N}` 미지정 (briefing/client, context_compressor, news_deep_analyzer 등)
- **마크다운 코드펜스 정제 비표준** — `entity_extractor._clean_json_response()`처럼 잘 된 곳도 있으나 대부분 누락 → LLM이 ` ```json ` 감싸면 파싱 실패
- **Celery 동기 호출 규칙(버그 #8)** — `thesis/tasks/summary.py`는 동기 API 사용으로 규칙 준수 ✅

---

## 4. 기타 의존성

### 4.1 FRED API — 🟡 중간 (에이전트 보고)
- **`packages/shared/api_request/fred_client.py`** `_make_request()`: 3회 지수 백오프(2/4/6s), `timeout=30`, 분당 120회 rate limiter, permanent(401/403/404) 즉시 raise vs transient(5xx) 재시도 구분 — **견고**
- ⚠️ **캐시 폴백 없음**: `macro_service.py:51`* 캐시 미스 시 즉시 FRED 호출, stale 캐시 재사용 로직 없음. FRED 장애 → 거시경제 대시보드 전체 error
- ⚠️ **Circuit Breaker 미적용**
- 영향 범위: Market Pulse 거시경제 기능 한정 (FRED 가용성 높아 위험 낮음)

### 4.2 Neo4j — 🔴 높음 (메타 위험, 에이전트 보고)
- **`Neo4jChainSightService`**: `is_available()` 사전 체크 + `_run_with_cb()` CB wrap + connection pool(`max_pool_size=50`, `acquisition_timeout=60s`) + lazy singleton. 미가용 시 빈 결과 폴백 — **앱은 계속 동작** ✅
- ⚠️ **`neo4j.exceptions.ServiceUnavailable` 구체 처리 없음** — `except Exception` 일반 캐치, CB 누적 후 OPEN에 의존
- 🔴 **메타 위험**: CB 상태가 Redis에 저장(§4.4) → **Redis 장애 시 CB가 Neo4j 실패를 추적 불가** → Neo4j 장애를 즉시 차단 못 함 → 요청이 timeout으로 누적

### 4.3 SEC EDGAR — 🟡 낮음 (에이전트 보고)
- **`sec_pipeline/collector.py`**: User-Agent 지정(L30)*, rate limit 0.12s(10 req/s) 준수, timeout 30/60/15s 분리 ✅
- ⚠️ **재시도 없음** — 모든 요청 즉시 raise, 호출자 책임
- ✅ **폴백 우수**: regex 추출 실패 → edgartools 폴백 → partial status 반환, 예외 throw 안 함
- 영향: 10-K 파이프라인 단독 기능, 시스템 격리됨

### 4.4 Redis — 🔴 매우 높음 (SPOF, 직접+에이전트 확인)

**`config/settings.py` 직접 확인**:
- `CACHES` BACKEND = `django.core.cache.backends.redis.RedisCache` (L502)
- `CELERY_BROKER_URL` = `redis://localhost:6379/0` (브로커)
- `CHANNEL_LAYERS` = `channels_redis.core.RedisChannelLayer` (L511)
- → **Redis가 캐시 + Celery 브로커 + Circuit Breaker 상태 + WebSocket 4역할 겸직**

**graceful degradation 부재**:
- `macro_service.py:51`* 등 `cache.get()` 직접 호출 — Redis `ConnectionError` 전파, try/except 없음 → 요청 500/타임아웃
- 🔴 **Circuit Breaker 자기모순** (`circuit_breaker.py` 직접 확인):
  - `get_state()`는 `cache.get(..., CLOSED)` 기본값으로 Redis 장애 시 항상 CLOSED 반환 (L64) → **장애 차단 기능 무력화**
  - `_set_open()`/`_set_closed()`/`_record_failure()`의 `cache.set()`/`cache.incr()`는 **예외 미처리** (L73–81, L154–164) → Redis 장애 시 CB 상태 갱신 불가
  - **결론: CB가 보호하려는 바로 그 인프라(Redis)가 죽으면 CB 전체가 동작 불능** — 모든 CB 보호 경로(Gemini RAG, Neo4j, FMP sp500/etf)가 동시에 무방비

**장애 시나리오 영향**:
- Redis 단독: 캐시 의존 요청 전부 실패 + Celery 큐 정지 + WebSocket 중단 + 모든 CB 무력화
- Redis + Neo4j 동시: CB 추적 불가 → Neo4j 요청 timeout 누적 → 리소스 고갈

---

## 5. Circuit Breaker 도입/보강 후보

> 인프라(`get_circuit`)는 이미 존재. 우선순위는 **(A) 기존 CB가 죽지 않게 하는 것** > **(B) 보호망 밖 호출을 안으로 넣는 것** > **(C) 신규 적용**.

### 우선순위 0 — CB 인프라 자체 강건화 (🔴 최우선)
1. **`circuit_breaker.py` Redis 예외 격리**: `cache.set`/`incr`/`delete`를 try/except로 감싸 Redis 장애 시 in-memory 폴백 또는 무시. 현재는 Redis 죽으면 CB가 silent하게 CLOSED 고정 → 보호 무력화.
2. **Redis SPOF 완화**: cache 연산 공통 래퍼(예외 흡수 + LocMemCache 폴백), 또는 캐시용/브로커용 Redis 인스턴스 분리.

### 우선순위 1 — 보호망 밖 raw FMP 호출 통합 (🔴 높음)
3. `apps/chain_sight/services/neo4j_loader.py:fetch_fmp_peers`* → 중앙 `FMPClient` + `get_circuit("fmp_peers")`
4. `apps/chain_sight/tasks/sensitivity_tasks.py:_fetch_geo_revenue`* → `FMPClient._make_request` 위임 + CB
5. `services/serverless/services/quote_enricher.py:_fetch_single_quote` → CB + 재시도 (병렬 50배치라 429 폭증 위험 최고)
6. `packages/shared/stocks/views.py:_get_fmp_chart_data`*, `stock_sync_service.py`* → 중앙 위임

### 우선순위 2 — Gemini 직접 호출 방어 + CB (🟠 중간)
7. `indicator_matcher.py`*, `news/api/views.py`*, `llm_peer_filter.py`* → `json.loads`/`response.text`에 try/except + 마크다운 펜스 정제 표준화
8. 직접 `genai.Client` 호출 36건의 공통 wrapper화 검토 (`LLMServiceLite`/`LLMClient`로 흡수) + `request_options` timeout 표준 적용

### 우선순위 3 — 신규 CB 적용 (🟡)
9. **FRED** `FREDClient` → `get_circuit("fred")` + stale 캐시 폴백
10. **Neo4j** `ServiceUnavailable` 명시 캐치 + driver timeout 명시 (현재 CB는 적용되어 있으나 Redis 의존 메타위험 잔존 → 우선순위 0 선결 필요)

---

## 부록: 조사 신뢰도 표기

| 구분 | 직접 정독 | 에이전트 보고(미정독) |
|------|----------|---------------------|
| FMP | `client.py`, `provider.py`, `quote_enricher.py` | raw 우회 4건, sp500/fmp_weights CB |
| Gemini | `llm_service.py`, `portfolio/llm/client.py` | 직접 호출 34개 파일 |
| 인프라 | `circuit_breaker.py`, `config/settings.py`(CACHES) | — |
| 기타 | — | FRED, Neo4j, SEC EDGAR 전부 |

`*` 표기 line 번호는 에이전트 보고 기준이므로, 수정 착수 전 해당 파일 직접 확인 권장.
