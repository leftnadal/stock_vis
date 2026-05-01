# 외부 API 의존성 감사 보고서

- **대상 프로젝트**: Stock-Vis (`/Users/byeongjinjeong/Desktop/stock_vis`)
- **감사일**: 2026-05-01
- **모드**: Read-only (코드 수정 없음)
- **감사 범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis, Alpha Vantage
- **자료 수집**: `grep`/`Read` 기반 정적 분석 — 런타임 행동은 미관측

---

## 0. 요약 (TL;DR)

| 영역 | 핵심 발견 | 우선 조치 |
|---|---|---|
| **FMP** | 3개 `FMPClient` 구현이 공존 — 에러 처리·rate limit·캐시 정책이 모두 다름. Circuit Breaker는 `news/tasks.py` 3곳에서만 사용 | 클라이언트 통합 + 호출지점 전반 Circuit Breaker 적용 |
| **Gemini** | 22개+ 호출 사이트에 **timeout=None**(무한 대기) 일관 누락. async API를 Celery에서 호출(BUG#8)하는 파일 6개 | 모든 호출에 `timeout` 설정 + Celery 호출지점 sync로 통일 |
| **Neo4j** | 읽기는 graceful(`get_neo4j_driver()` → None fallback) 잘 됨. Celery 쓰기 태스크 12개+는 차단 시 무한 retry 폭주 | Neo4j 헬스체크 → 작업 큐잉 게이트 |
| **Redis** | 단일 인스턴스로 **broker + cache + circuit breaker state + WebSocket** 전부 의존. SPOF | 모니터링 + 단계적 HA(Sentinel) |
| **FRED** | retry(3회)·timeout(30s)·rate limiter 모두 갖춤. graceful degradation 우수 | 현재 안정적 — 변경 불필요 |
| **SEC EDGAR** | User-Agent 준수, 100ms 간격, 429 재귀 retry. 5xx 즉시 raise(retry 없음) | 5xx 백오프 retry 보강 |
| **Alpha Vantage** | 코드는 남아있으나 활성 호출 없음(dead code) | 제거 후보 |

**Top 3 Circuit Breaker 도입 후보 (장애 시 시스템 영향 최대)**:
1. **FMP** — `news/tasks.py` 외 32개+ 호출지점이 직접 노출 → 단일 FMP 장애가 EOD 파이프라인·screener·chain sight·news 전반을 동시에 덮친다.
2. **Gemini** — 22개+ 호출지점·timeout 미설정·6개 async/Celery 위반 → 단일 LLM 장애가 Celery 워커를 수십 분 단위로 점유한다.
3. **Neo4j (Celery 쓰기 큐)** — `neo4j` 큐 12개+ 태스크가 retry exponential backoff로 큐 폭주를 유발한다.

---

## 1. 의존성 매트릭스

| 의존성 | 호출지점 수 | 주요 위치 | Auth | Rate Limit 핸들링 | Retry | Timeout | Premium/402 | Fallback / Graceful | 통합 Circuit Breaker | 위험도 |
|---|---|---|---|---|---|---|---|---|---|---|
| **FMP** | 32 (운영) + 7 (스크립트/테스트) | `api_request/providers/fmp/`, `serverless/services/`, `macro/services/`, `news/providers/`, `stocks/`, `thesis/tasks/` | `FMP_API_KEY` | **클라이언트별 상이** (0.2s~0.5s sleep, 일일 한도 체크는 1개만) | **불균등** (1개 클라이언트만 3회 backoff) | 30s (모든 클라이언트 동일) | **`FMPPremiumError` 처리 — `api_request/providers/fmp/`만** | Fallback chain 비활성(`FALLBACK_CHAIN[FMP]=[]`), `news/tasks.py`만 Breaker 사용 | 부분 (3/32) | **HIGH** |
| **Gemini** | 22+ (서비스) | `thesis/services/`, `serverless/services/`, `news/services/`, `rag_analysis/services/`, `sec_pipeline/`, `validation/services/`, `portfolio/llm/`, `stocks/services/korean_overview_service.py` | `GEMINI_API_KEY` | 정적 4s sleep(6 파일), 백오프(2 파일), 없음(나머지) | **불균등** (2 파일만 exponential) | **0개 파일이 timeout 설정** | N/A | 일부 graceful (None 반환), 일부 cascade(re-raise) | **없음** | **HIGH** |
| **FRED** | 8~12 (macro/services/macro_service.py 경유) + EOD 파이프라인(`thesis/tasks/eod_pipeline.py`) | `macro/services/fred_client.py`, `macro/tasks.py` | `FRED_API_KEY` | `RateLimiter("fred")` 모듈 사용, 120/min | 3회 backoff (2s/4s/6s), 401/403/404 즉시 fail | 30s | N/A | **태스크 단위 try/except + `continue`로 부분 실패 허용** | 없음 | **MED-LOW** |
| **Neo4j** | 12+ Celery + 다수 read | `serverless/services/neo4j_chain_sight_service.py`, `chainsight/tasks/*.py`, `news/tasks.py`, `sec_pipeline/tasks.py`, `rag_analysis/tasks.py`, `rag_analysis/services/neo4j_driver.py` | `NEO4J_URI/USERNAME/PASSWORD` | N/A (DB 연결) | **읽기**: 없음(드라이버 None 시 빈 fallback) / **쓰기**: Celery 태스크 기본 retry 폭주 | read query 2000ms (`Neo4jServiceLite`), pool acquire 60s | N/A | 읽기 graceful, 쓰기 cascade | 없음 | **HIGH** |
| **SEC EDGAR** | 1 (`api_request/sec_edgar_client.py`) → `serverless/tasks.py`, `sec_pipeline/collector.py` | `api_request/sec_edgar_client.py` | User-Agent 헤더만 | 100ms 간격 enforce (10/sec) | 429만 재귀 retry(1s 대기), 5xx는 즉시 `SECEdgarError` raise | 30s (10-K 다운로드는 120s) | N/A | 호출 측에서 `try/except SECEdgarError → continue` | 없음 | **MED** |
| **Redis** | 전역(`config/settings.py`) | Celery broker(DB 0), cache(DB 1), Channels layer | 비밀번호 없음(localhost) | N/A | 없음 | 캐시: 없음, broker: Celery 기본 5s | N/A | 캐시 미스 시 재계산(safe), broker 다운 시 **모든 작업 정지** | N/A | **HIGH (SPOF)** |
| **Alpha Vantage** | 0 (활성) | 코드만 잔존 (`api_request/alphavantage_*`, `news/providers/alphavantage.py`) | `ALPHA_VANTAGE_API_KEY` | (미사용) | (미사용) | (미사용) | N/A | dead code | N/A | **NONE (dead)** |

> **주**: 호출지점 수는 `grep "FMPClient\|FMPProvider\|FMPNewsProvider"` 결과로, 테스트/스크립트 제외. Gemini는 `grep "generate_content\|genai"` 36 파일 중 운영 서비스 22+개를 별도 식별.

---

## 2. FMP 상세

### 2.1 클라이언트 3개 공존 (구조 부채)

| 클라이언트 | 위치 | 라이브러리 | 에러 클래스 | 재시도 | Rate Limiting | 일일 한도 | Premium(402) | 캐시 |
|---|---|---|---|---|---|---|---|---|
| **표준 (권장)** | `api_request/providers/fmp/client.py` | `requests` | `FMPClientError`, `FMPRateLimitError`, `FMPAuthError`, **`FMPPremiumError`** | 3회 (2s/4s/6s) | 0.2s sleep | **10000/day 체크 후 raise** | ✅ 즉시 raise(`get_balance_sheet`/`income_statement`/`cash_flow`에서 캐치) | 없음 |
| **Market Movers** | `serverless/services/fmp_client.py` | `httpx` | `FMPAPIError` 단일 | **없음** | 없음 | 없음 | ❌ | **Django cache(60s~24h)** |
| **Macro** | `macro/services/fmp_client.py` | `requests` | `ValueError` 또는 `RequestException` 직통 | **없음** | 0.5s sleep | 없음 | ❌ | 없음 |

→ 표준 클라이언트 외 두 구현은 **402(프리미엄 심볼)·429(분당 한도)·500(일시 장애) 처리가 모두 미흡**하다. 동일 키를 공유하므로 한 클라이언트의 누락이 다른 흐름의 한도를 잠식할 수 있다.

### 2.2 호출지점 분포 (운영 코드 32개)

| 분류 | 파일 | 지점 |
|---|---|---|
| Provider 추상화 (표준) | `api_request/providers/fmp/provider.py`, `api_request/stock_service.py` | `call_with_fallback` 경유 (단, FMP fallback chain 비어있음) |
| EOD 파이프라인 (Celery) | `thesis/tasks/eod_pipeline.py:25-81` (`_fetch_fmp_value`) | 표준 클라이언트 사용, `FMPPremiumError`/`FMPClientError`/`Exception` 3단 처리 |
| Market Movers (Celery + view) | `serverless/services/data_sync.py:14, 49` (`MarketMoversSync`) | `serverless/services/fmp_client.py` 사용, `FMPAPIError`만 처리, 개별 종목 실패 시 `continue` |
| Screener / Chain Sight / Sector Heatmap | `serverless/services/enhanced_screener_service.py`, `chain_sight_service.py`, `sector_heatmap_service.py`, `filter_engine.py`, `market_breadth_service.py`, `cusip_mapper.py`, `keyword_data_collector.py`, `neo4j_chain_sight_service.py` | 모두 `serverless` 클라이언트 — 재시도/Premium 미처리 |
| News (Celery) | `news/services/aggregator.py`, `news/providers/fmp.py`, `news/tasks.py:923-1074` | **표준 클라이언트** + **`CircuitBreaker('fmp')`** |
| Macro Pulse (Celery + view) | `macro/services/macro_service.py:35`, `macro/services/fmp_client.py` | `macro` 클라이언트 — 재시도 없음 |
| S&P 500 EOD (Celery) | `stocks/tasks.py:124-`, `stocks/services/sp500_eod_service.py`, `stocks/services/sp500_service.py` | 표준 클라이언트, `.` 포함 심볼 사전 제외 (BUG#23 대응 흔적) |
| Diagnostic | `thesis/views/monitoring_views.py:308`, `serverless/views.py:687` | 사용자 요청 동기 호출 → **API 장애 시 그대로 5xx 노출** |
| 기타 | `api_request/__init__.py`, `users/utils.py`, `stocks/views_search.py` | 보조 |

### 2.3 에러 핸들링 패턴 별 평가

| 패턴 | 위치 | 평가 |
|---|---|---|
| `FMPPremiumError` 즉시 처리(BUG#23 학습) | `api_request/providers/fmp/provider.py:247-253, 293-299, 339-345`, `thesis/tasks/eod_pipeline.py:73-75`, `stocks/tasks.py:148-150` (`.` 심볼 선별 제외) | ✅ 베스트 — 다른 호출지점에 횡전개 필요 |
| `CircuitBreaker('fmp')` open 시 skip | `news/tasks.py:926-929, 1012-1015, 1056-1059` (3 태스크) | ✅ 좋음. **단, 32개 호출지점 중 3개에만 적용** |
| 일반 `Exception` 광범위 캐치 → `continue` | `serverless/services/data_sync.py:91-95, 131-149`, EOD 파이프라인 | ⚠ Premium·Auth·Rate Limit 구분 없이 동일 처리 — 키 만료를 일시 장애로 오인 |
| 에러를 그대로 사용자에게 노출 | `thesis/views/monitoring_views.py`, `serverless/views.py`, `stocks/views_search.py` | 🔴 동기 view에서 FMP 호출 → 외부 장애 = 즉시 5xx |
| Fallback chain 미작동 | `api_request/providers/factory.py:67-69` (`FALLBACK_CHAIN[FMP] = []`) | 🔴 `call_with_fallback`이 사실상 단일 provider 호출에 그침. Alpha Vantage 제거(주석 66) 이후 대체 미구축 |

### 2.4 Rate Limit 안전 마진

| 클라이언트 | 분당 호출가능량 (이론) | 동시 사용 시 실제 마진 |
|---|---|---|
| `api_request/providers/fmp/` | 0.2s 간격 → 분당 ~300 | Starter 한도 정확히 사용 |
| `serverless/services/` | 간격 없음 | 짧은 burst 시 **429 가능** — `_make_request`가 그대로 raise → cache miss 폭주 |
| `macro/services/` | 0.5s 간격 → 분당 ~120 | 안전 |

→ **여러 Celery 워커가 동시에 다른 클라이언트로 호출하면 분당 300을 쉽게 초과**한다. (예: `sync_sp500_financials` + `sync_daily_movers` + `update_macro_data` 동시 실행) 통합 토큰 버킷이 없다.

### 2.5 위험 시나리오

1. **FMP 분당 한도 초과** → `serverless` 클라이언트는 그대로 `FMPAPIError` raise → Market Movers / Screener / Chain Sight 동시 빈 응답 → 메인 페이지 EOD 대시보드 부분 결손.
2. **FMP API 다운(5xx)** → 표준 클라이언트는 3회 재시도 후 raise → EOD 파이프라인 retry policy(`@shared_task`만, max_retries 미명시) 무한 retry 위험.
3. **API 키 만료(401/403)** → 표준은 `FMPAuthError` 즉시 raise이나, `serverless`/`macro` 클라이언트는 일반 에러로 처리 → 장애 분류 모니터링 어려움.
4. **Premium 심볼(BRK.B, BF.B 등)** → 표준 클라이언트만 보호. `serverless`/`macro` 클라이언트로 호출되면 **402 그대로 통과**, 호출 측에서 일반 `Exception`으로 잡혀 통계 왜곡.

---

## 3. Gemini 상세

### 3.1 호출 인벤토리

(서브에이전트 조사 결과 확인 — `Read` 검증은 주요 파일 표본만 수행)

#### CRITICAL — Async API + Celery 컨텍스트 (BUG#8 위반 가능)

| 파일 | 모델 | 호출 형태 | timeout | 재시도 | 429 처리 | 비고 |
|---|---|---|---|---|---|---|
| `serverless/services/keyword_generator.py` | gemini-2.5-flash | `aio.models.generate_content` (async) | ❌ | ❌ | ❌ | sync_wrapper 경유 호출 의심 |
| `serverless/services/keyword_generator_v2.py` | gemini-2.5-flash | async | ❌ | ❌ | ❌ | 동일 |
| `rag_analysis/services/context_compressor.py` | gemini-2.5-flash | async | ❌ | ❌ | ❌ | 예외 re-raise (cascade) |
| `rag_analysis/services/entity_extractor.py` | gemini-2.5-flash | async | ❌ | ❌ | ❌ | JSON 파싱 fallback 약함 |
| `rag_analysis/services/adaptive_llm_service.py` | gemini-2.5-flash + Anthropic | async | ❌ | ❌ | ❌ | 멀티 프로바이더지만 retry 없음 |
| `rag_analysis/services/llm_service.py` | gemini-2.5-flash | async | ❌ | ✅ (1/2/4s) | ✅ (rate/quota 키워드 매칭) | 22개 중 **유일하게 retry+429 동시** |

#### HIGH — Sync 호출이지만 timeout/재시도 부족

| 파일 | 모델 | retry | 429 핸들링 | timeout | 호출 컨텍스트 |
|---|---|---|---|---|---|
| `thesis/services/prompt_builder.py` | 2.5-flash | ❌ | ❌ | ❌ | 사용자 요청(view) |
| `thesis/services/thesis_builder.py` | 2.5-flash | ❌ | ❌ | ❌ | 사용자 요청(view) |
| `thesis/services/indicator_matcher.py` | 2.5-flash | ❌ | ❌ | ❌ | view + Celery |
| `thesis/views/conversation_views.py` | 2.5-flash | ❌ | ❌ | ❌ | view (직접 사용자 노출) |
| `serverless/services/llm_relation_extractor.py` | 2.5-flash | ❌ | 정적 4s sleep | ❌ | Celery |
| `serverless/services/relationship_keyword_enricher.py` | 2.5-flash | ❌ | 정적 4s sleep | ❌ | Celery |
| `news/services/news_deep_analyzer.py` | 2.5-flash | ❌ | 정적 4s sleep | ❌ | Celery |
| `news/services/keyword_extractor.py` | 2.5-flash | ❌ | ❌ | ❌ | Celery |
| `news/services/stock_insights.py` | 2.5-flash | ❌ | ❌ | ❌ | view |
| `sec_pipeline/intelligence.py` | 2.5-flash | ❌ | ❌ | ❌ | Celery (error dict fallback) |
| `sec_pipeline/extractor.py` | 2.5-flash | ❌ | ❌ | ❌ | Celery (re-raise) |
| `stocks/services/korean_overview_service.py` | 2.5-flash | ❌ | 정적 4s sleep | ❌ | Celery (re-raise) |
| `validation/services/llm_peer_filter.py` | 2.5-flash | ❌ | ❌ | ❌ | view |

#### MEDIUM — 비교적 양호

| 파일 | 평가 |
|---|---|
| `serverless/services/keyword_service.py` | retry+exponential backoff(2/4/6s) 보유 — 표준 후보 |
| `portfolio/llm/client.py` | retry + Anthropic fallback 보유 — 통합 wrapper |
| `serverless/services/csv_url_resolver.py` | LLM이 fallback 위치(패턴 우선) — 안전 |
| `news/api/views.py` | LLM 실패 시 `analysis=null` 반환 — graceful |

#### OUTLIER

| 파일 | 이슈 |
|---|---|
| `serverless/services/regulatory_service.py` | 모델 버전 `gemini-2.0-flash-exp` (다른 곳은 2.5-flash) — 일관성 부재 |

### 3.2 Cross-cutting 결함

1. **Timeout 0개** — 22개 파일 어디에도 `client.models.generate_content(..., request_options={'timeout': N})` 명시 없음. Gemini 응답이 멈추면 Celery 워커가 무한 점유된다 (Bug 케이스: macOS fork + Obj-C 다발 시).
2. **429 백오프 표준 부재** — 정적 4s sleep은 Free tier 15 RPM에는 맞지만 Paid tier·동시 워커 환경에서는 무력.
3. **Async/Sync 경계 위반** — KB 트러블슈팅 #8과 정면 충돌. 6개 파일이 `aio` 인터페이스 사용. Celery 태스크에서 직접 호출되는지 추가 확인 필요.
4. **JSON 파싱 fallback 분산** — 일부는 `response_mime_type='application/json'` + schema, 일부는 regex fallback, 일부는 그냥 `json.loads` 후 raise.
5. **모델 버전 미디지정 표준** — `2.5-flash` 다수, `2.0-flash-exp` 1개. 향후 retire 시 일제 작업 필요.

### 3.3 위험 시나리오

| 시나리오 | 영향 |
|---|---|
| Gemini 일시 지연(>30s) | 22개 호출지점 모두 무한 대기. Celery worker concurrency = N이라면 N개 작업 멈춘 후 큐 적체 |
| Gemini 429 대량 발생 | 정적 sleep만 가진 서비스는 재호출 즉시 재실패 — quota 도달까지 폭주 |
| 응답 JSON 파싱 실패 | 파일별로 다른 행동(빈 dict, None, exception) — 다운스트림 일관성 깨짐 |
| `gemini-2.5-flash` 모델 retire | grep 기반 일괄 변경 필요. 1개 outlier(2.0-exp) 별도 처리 |

---

## 4. 기타 의존성

### 4.1 FRED API — `macro/services/fred_client.py`

- **품질**: ★★★★★ (감사 대상 중 가장 견고)
- **재시도**: 3회, 2s/4s/6s 점증
- **분류 처리**: 401/403/404 즉시 fail, 5xx만 재시도 (`TRANSIENT_STATUS_CODES = {500, 502, 503, 504}`)
- **Rate Limiter**: `api_request/rate_limiter.get_rate_limiter("fred")` 모듈로 통합
- **Timeout**: 30초
- **Graceful**: `macro/tasks.py`의 `update_economic_indicators()`가 시리즈별 try/except + `continue`로 부분 실패 허용
- **EOD 파이프라인 위험점**: `thesis/tasks/eod_pipeline.py:121-123`에서 `except Exception` 단일 절로 잡고 `(None, None)` 반환 → indicator 단위 silent failure만 노출. FRED 인증 만료 시 알림이 늦을 수 있음.

### 4.2 Neo4j — `rag_analysis/services/neo4j_driver.py` 외

- **드라이버 패턴**: `get_neo4j_driver()` lazy singleton. 연결 실패 시 `None` 반환 → 호출 측에서 `if driver is None: return _empty()` 패턴 광범위 적용 (좋음)
- **읽기 graceful**: `Neo4jServiceLite.QUERY_TIMEOUT = 2000ms`
- **쓰기 cascade 위험**: `chainsight/tasks/sync_tasks.py`, `chainsight/tasks/neo4j_dirty_sync_tasks.py`, `news/tasks.py`(sync_news_to_neo4j), `sec_pipeline/tasks.py`(sync_dirty_to_neo4j) 등이 Neo4j 다운 시 raise → Celery 기본 retry로 큐 폭주
- **신호**: `synced_to_neo4j` 대신 **`neo4j_dirty` 플래그 패턴** 도입은 올바른 방향(KB DECISION) — 단, 작업 큐잉 직전 헬스체크가 없어 다운 중에도 enqueue됨
- **Fork 안전**: macOS 환경 변수(`OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`) + `solo` 풀 정책 (BUG#25) 적용 흔적은 신뢰성 보강

### 4.3 SEC EDGAR — `api_request/sec_edgar_client.py`

- **User-Agent 준수**: `Stock-Vis/1.0 (contact@stockvis.com)` (line 102)
- **Rate Limit**: 100ms 간격 강제 (`RATE_LIMIT_INTERVAL = 0.1`, line 99)
- **Retry 한계**: 429만 재귀 retry(1초 대기), 5xx는 즉시 `SECEdgarError` raise → 호출 측에서 try/except로 다음 회사로 진행
- **Timeout**: 30초(기본) / 120초(10-K 다운로드)
- **Failure mode**: 월 1회 배치 — SEC 다운 시 **해당 월 배치 전체 미수집**, 부분 진척 저장 없음
- **개선여지**: 5xx에 대한 backoff retry(현재 단일 실패가 한 회사 누락) — 단, SEC EDGAR가 99.9%+ uptime이라 우선순위는 낮음

### 4.4 Redis — `config/settings.py`

- **삼중 의존**: Celery broker(DB 0) + Django cache(DB 1) + Channels WebSocket layer
- **Circuit Breaker state도 Redis**: `news/services/circuit_breaker.py`가 `django.core.cache.cache` 사용 — Redis 다운 시 circuit state 유실로 **재기동 직후 복구된 외부 API에 burst 요청 폭주 위험**
- **인증 미설정**: localhost 가정. 프로덕션 노출 시 즉시 보안 이슈
- **장애 영향**:
  - 캐시 다운 → 모든 호출 재계산(slow but safe)
  - Broker 다운 → **모든 Celery 태스크 큐잉 불가** (EOD 파이프라인, 뉴스 수집, Neo4j sync 전부 정지)
  - WebSocket layer 다운 → 실시간 알림 silently fail

### 4.5 Alpha Vantage — Dead Code

- `api_request/providers/factory.py:66-69` 주석에 "Alpha Vantage 제거 후 FMP 단독" 명시
- `news/providers/alphavantage.py`, `api_request/alphavantage_*.py` 등 잔존
- **활성 import/호출 없음** → 삭제 후보. (이번 감사에서는 read-only 정책으로 제거 미실행)

---

## 5. Circuit Breaker 도입 후보 (우선순위 순)

기존: `news/services/circuit_breaker.py`(Redis 기반, threshold=5, timeout=300s) — `news/tasks.py` 3개 태스크에만 적용.

### Tier 1 (필수)

| # | 후보 | 도입 위치 | 적용 이유 | 예상 효과 |
|---|---|---|---|---|
| 1 | **FMP 통합 Breaker** | `api_request/providers/fmp/client.py._make_request` 또는 `call_with_fallback` 진입부 | 32개+ 호출지점 일제 보호. 현재 `news/tasks.py` 외에는 무방비 | API 한도 초과·5xx 시 5분간 자동 차단 → SP500 EOD/Movers/Screener 동시 보호 |
| 2 | **Gemini 통합 Breaker** | `portfolio/llm/client.py`(또는 신규 `shared/llm_client.py`)에서 wrapping | 22개+ 호출지점이 직접 SDK 호출. Breaker + timeout(30s) + 재시도 동시 도입 가능 | Gemini 장애 시 Celery 워커 점유 폭증 방지 |
| 3 | **Neo4j 쓰기 Breaker** | `chainsight/tasks/`, `sec_pipeline/tasks.py`, `news/tasks.py:sync_*_to_neo4j` enqueue 직전 | 쓰기 태스크가 retry 폭주로 큐 overload 유발 | Neo4j 다운 시 신규 sync 태스크 enqueue 차단 (`neo4j_dirty` 플래그는 그대로 유지) |

### Tier 2 (권장)

| # | 후보 | 도입 위치 | 적용 이유 |
|---|---|---|---|
| 4 | **SEC EDGAR Breaker** | `api_request/sec_edgar_client._make_request` | 월 1회 배치이지만 5xx 시 전체 배치 손실 — Breaker로 다음 시도 일찍 결정 |
| 5 | **FRED Breaker (선택)** | `macro/services/fred_client.FREDClient._make_request` | 이미 견고하지만, 다중 시리즈 동시 5xx 발생 시 30초×시리즈수 지연 발생 → Breaker로 빠른 fail-fast |

### Tier 3 (구조 개선)

| # | 후보 | 적용 |
|---|---|---|
| 6 | **Redis Breaker state externalize** | `news/services/circuit_breaker.py`가 Redis 자신을 의존하는 모순 해소. 메모리 fallback(프로세스 단위) 또는 DB 테이블 백업 검토 |
| 7 | **FMP 클라이언트 통합** | 3개 구현 → 1개 표준(`api_request/providers/fmp/`)으로 수렴. `serverless`/`macro`는 파사드만 유지 |
| 8 | **Gemini timeout 일괄 정책** | 신규 환경변수 `GEMINI_REQUEST_TIMEOUT=30`을 헬퍼에서 강제 |

### Circuit Breaker 적용 패턴 제안 (참고)

기존 `news/services/circuit_breaker.py`의 인터페이스가 단순하므로, 호출지점별로 다음 표준 패턴을 채택하면 32~22개 일괄 보호 가능:

```python
# pseudo — 실제 구현은 후속 PR에서
breaker = CircuitBreaker('fmp', threshold=5, timeout=300)
if breaker.is_open():
    return graceful_fallback()  # 빈 list / cached value
try:
    result = client.call(...)
    breaker.record_success()
    return result
except (FMPRateLimitError, FMPClientError, requests.RequestException) as e:
    breaker.record_failure()
    raise  # 또는 graceful_fallback()
```

(주의: `FMPPremiumError`/`FMPAuthError`는 Breaker 카운트에서 제외 — 일시 장애가 아닌 영속적 에러)

---

## 6. 보고서 외 부수 관찰

1. **`PROGRESS.md`/`DECISIONS.md` 미반영 결정 후보**:
   - "FMP fallback chain은 단일 provider 운영(`FALLBACK_CHAIN[FMP] = []`)" — DECISION 기록 추천
   - "Circuit Breaker는 Redis 기반 단일 모듈로 통일" — Tier 3 채택 시 DECISION 기록 추천
2. **테스트 커버리지 갭**: `tests/unit/news/test_circuit_breaker.py`는 있으나, 다른 호출지점에서 Breaker가 빠진 회귀를 막는 통합 테스트는 미관측.
3. **모니터링 후보 메트릭**: `circuit:fmp:failures`, `circuit:gemini:failures`(신규), Celery `neo4j` 큐 길이, FMP `daily_calls` (현재 클라이언트 인스턴스 메모리에만 존재 → Redis로 이전 권장).

---

## 7. 결론

- **현 상태**: FRED는 안정적, FMP는 표준 클라이언트 한정으로 양호하나 **호출지점·클라이언트 일관성이 낮다**, Gemini는 **timeout 부재가 시스템 전체의 가장 큰 단일 위험**.
- **장애 시 전파 가능성이 가장 높은 3대 의존성**: FMP(분당 한도/네트워크 일시 장애) → Gemini(무한 hang) → Neo4j(쓰기 retry 폭주). 모두 **Circuit Breaker 부재 또는 부분 적용** 상태.
- **즉시 효과 큰 단일 변경**: 모든 Gemini 호출에 `timeout=30` 명시 + Celery 호출지점에 통합 Breaker 적용. (이번 보고서는 read-only 모드로 변경은 미실행)
