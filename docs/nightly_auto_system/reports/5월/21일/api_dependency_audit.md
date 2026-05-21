# 외부 API 의존성 감사 보고서

작성일: 2026-05-21
범위: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis, Alpha Vantage(잔재)
방법: 정적 코드 분석 (코드 미수정, 읽기 전용)
직전 보고서: `docs/nightly_auto_system/reports/5월/20일/api_dependency_audit.md`

---

## 요약

### Δ since 5/20
- 신규 커밋 9건(`3e3ad6b ~ 22d1e99`) 모두 slice13 Portfolio Coach API endpoint 추출 — **FMP/Gemini/Neo4j 인프라 미변경**.
- 5/19 적용된 P0 보안 패치 3건은 본 감사 범위(FMP/Gemini)와 직접 관련 있음:
  - `keyword_generator` Celery async→sync (`b05b214`) → common-bugs #8 준수 (확인됨, L271 주석)
  - LLM prompt injection 차단 (`71b2d2f`) → `rag_analysis/services/llm_service.py:178–192`에 escape 패턴 적용 (확인됨)
  - Watchlist IDOR (`e8abb7b`) → FMP/Gemini 관련 아님
- 따라서 본 보고서는 5/20 매트릭스를 **재검증 후 갱신**한 것이며, 위험도 Top 5 변동 없음.

### 호출 지점 통계
- **FMP 클라이언트**: 3종 병존 — `api_request/providers/fmp/client.py` (메인, 강건), `serverless/services/fmp_client.py`, `macro/services/fmp_client.py`
- **FMP 사용 파일**: 35개 + `news/providers/fmp.py` (메인 위임)
- **Gemini 호출 지점**: 약 24개 활성 코드 + 테스트 모킹 다수
- **CircuitBreaker 적용**: 17개 파일 (marketpulse.utils 13 + news 자체 4)
- **CircuitBreaker 인프라**: 2종 병존 — `marketpulse/utils/circuit_breaker.py` (tenacity 기반, 정식), `news/services/circuit_breaker.py` (Redis 카운터, 경량)

### 위험도 Top 5 (변동 없음)
1. **`macro/services/fmp_client.py`** — 재시도/캐시/402 처리 없음. Market Pulse 화면 전 호출이 의존.
2. **`serverless/services/fmp_client.py`** — Chain Sight/Market Movers/Screener/Sector Heatmap 등 운영 트래픽 다수. 재시도 0회, FMPPremiumError 미존재(httpx HTTPStatusError 일반 처리).
3. **`sec_pipeline/extractor.py` Gemini 2개소** — `JSONDecodeError`만 명시 캐치, 그 외 `raise` → Celery 태스크 전체 실패 위험.
4. **`news/services/news_deep_analyzer.py`** — Tier C 호출(max_tokens=6000). 단일 `try/except → return None`. 동시 다발 호출 시 429 보호 없음.
5. **`thesis/services/prompt_builder.py` Gemini 3개소** — CB 미적용, 재시도 없음. EOD 야간 자동화 파이프라인에 포함.

---

## 의존성 매트릭스 (서비스 × 외부 API × 안전장치)

| 서비스/모듈 | FMP | Gemini | FRED | Neo4j | SEC | Redis(cache) | 자체 캐시 | 재시도 | Circuit Breaker |
|---|---|---|---|---|---|---|---|---|---|
| `api_request/providers/fmp/client.py` (FMP 메인) | ✓ | - | - | - | - | - | 일일카운터 | 3회+expb | ✗ |
| `serverless/services/fmp_client.py` | ✓ | - | - | - | - | ✓ (5m~24h) | 동일 | ✗ | ✗ |
| `macro/services/fmp_client.py` | ✓ | - | - | - | - | ✗ | rate-limit sleep | ✗ | ✗ |
| `macro/services/fred_client.py` | - | - | ✓ | - | - | - | rate-limiter | 3회+expb | ✗ |
| `news/providers/fmp.py` (위임) | ✓ (메인) | - | - | - | - | - | - | (메인 위임) | ✗ |
| `rag_analysis/services/llm_service.py` | - | ✓ | - | - | - | (CB state) | - | 3회+expb | ✓ `gemini_rag` |
| `rag_analysis/services/context_compressor.py` | - | ✓ | - | - | - | (CB state) | - | (CB) | ✓ |
| `thesis/services/thesis_builder.py` | - | ✓ | - | - | - | (CB state) | - | (CB) | ✓ `gemini_thesis` |
| `thesis/services/prompt_builder.py` | - | ✓ (3개소) | - | - | - | - | - | ✗ | ✗ |
| `thesis/services/indicator_matcher.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `thesis/tasks/summary.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `thesis/views/conversation_views.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `thesis/tasks/eod_pipeline.py` | ✓ (메인) | - | - | - | - | - | - | (메인) | ✗ |
| `thesis/views/monitoring_views.py` | ✓ (메인) | - | - | - | - | - | - | (메인) | ✗ |
| `marketpulse/briefing/client.py` | - | ✓ | - | - | - | (CB state) | - | (CB) | ✓ `gemini` |
| `marketpulse/services/news_aggregator.py` | ✓ (메인) | - | - | - | - | (CB state) | - | (메인) | ✓ |
| `marketpulse/fetchers/fmp_weights.py` | ✓ | - | - | - | - | (CB state) | - | (CB) | ✓ |
| `serverless/services/keyword_generator.py` | - | ✓ (sync 강제) | - | - | - | - | - | ✗ | ✗ |
| `serverless/services/keyword_service.py` | - | ✓ | - | - | - | ✓ | - | ✗ | ✗ |
| `serverless/services/llm_relation_extractor.py` | - | ✓ | - | - | - | ✓ | - | ✗ | ✗ |
| `serverless/services/relationship_keyword_enricher.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `serverless/services/regulatory_service.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `serverless/services/csv_url_resolver.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `serverless/services/thesis_builder.py` (구버전) | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `serverless/services/data_sync.py` | ✓ | - | - | - | - | - | - | (CB) | ✓ |
| `serverless/services/sector_heatmap_service.py` | ✓ | - | - | - | - | ✓ | - | ✗ | ✗ |
| `serverless/services/filter_engine.py` | ✓ | - | - | - | - | ✓ | - | ✗ | ✗ |
| `serverless/services/keyword_data_collector.py` | ✓ | - | - | - | - | - | - | ✗ | ✗ |
| `serverless/services/chain_sight_service.py` | ✓ | - | - | - | - | - | - | ✗ | ✗ |
| `serverless/services/cusip_mapper.py` | ✓ | - | - | - | - | - | - | ✗ | ✗ |
| `serverless/services/enhanced_screener_service.py` | ✓ | - | - | - | - | ✓ | - | ✗ | ✗ |
| `serverless/services/market_breadth_service.py` | ✓ | - | - | - | - | ✓ | - | ✗ | ✗ |
| `serverless/services/neo4j_chain_sight_service.py` | ✓ | - | - | ✓ | - | ✓ | 5m | (CB) | ✓ `neo4j_chain_sight` |
| `news/services/news_deep_analyzer.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `news/services/stock_insights.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `news/services/keyword_extractor.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `news/services/aggregator.py` | ✓ (메인) | - | - | - | - | - | - | (메인) | (news 자체 CB) |
| `news/api/views.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `news/tasks.py` | (위임) | - | - | - | - | - | - | (위임) | (news 자체 CB) |
| `validation/services/llm_peer_filter.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `sec_pipeline/extractor.py` | - | ✓ (2개소) | - | - | - | - | - | ✗ | ✗ |
| `sec_pipeline/intelligence.py` | - | ✓ | - | - | - | - | - | ✗ | ✗ |
| `sec_pipeline/collector.py` | - | - | - | - | ✓ | - | CIK class cache | ✗ (sleep 0.12) | ✗ |
| `portfolio/llm/client.py` | - | ✓ + Anthropic | - | - | - | - | - | 1회+폴백 | ✗ (자체 budget guard) |
| `stocks/tasks.py` | ✓ (메인) | - | - | - | - | - | - | (메인) | ✗ |
| `stocks/services/sp500_eod_service.py` | (DB) | - | - | - | - | - | - | (CB) | ✓ |
| `stocks/services/sp500_service.py` | ✓ | - | - | - | - | - | - | (CB) | ✓ |
| `stocks/services/fmp_screener.py` | ✓ | - | - | - | - | - | - | 429 retry | ✗ |

---

## FMP 상세

### 1) 메인 클라이언트 — `api_request/providers/fmp/client.py`

**예외 계층** (L20–L37): `FMPClientError`(베이스) → `FMPRateLimitError`/`FMPAuthError`/`FMPPremiumError`.

**`_make_request` (L80–L161) 에러 핸들링 (양호)**:
- 401 → `FMPAuthError` (L127)
- 402 → `FMPPremiumError(f"Premium-only symbol/endpoint (402): {endpoint}")` (L128–L129)
- 403 → `FMPAuthError` (L130–L131)
- 429 → `FMPRateLimitError` (L132–L133)
- `{"Error Message": ...}` 응답: "Invalid API KEY" → `FMPAuthError`, 그 외 → `FMPClientError` (L141–L145)
- `FMPPremiumError/FMPAuthError/FMPRateLimitError`는 **재시도 없이 즉시 전파** (L149)
- 그 외 `RequestException/FMPClientError`만 3회 재시도 + exponential backoff `(attempt+1)*2`초 (L153–L159)

**Rate Limit**:
- `request_delay=0.2` sleep 강제 (L57, L104–L107) — Starter Plan 300/min = 5 RPS
- `daily_calls` 카운터 + `daily_limit=10000` (L70–L71, L110)
- `reset_daily_counter()` 메서드 존재 (L488) — **외부 호출자에서 자정 호출 필요** (자동 등록 안 됨, 확인 필요)

**Timeout**: `requests.get(..., timeout=30)` (L121)

**Provider 계층 (`provider.py`) FMPPremiumError 핸들링 일관성 결함**:
- `except FMPPremiumError` 명시 캐치: `get_balance_sheet` L247, `get_income_statement` L293, `get_cash_flow` L339 → `error_code="PREMIUM_ONLY"`
- 비캐치(일반 `Exception`으로 흡수): `get_quote` L88, `get_company_profile` L125, `get_daily_prices` L171, `get_weekly_prices` L210, `search_symbols` L383, `get_sector_performance` L418 → `error_code="API_ERROR"`로 폴백되어 원인 손실

### 2) 중복 클라이언트 — `serverless/services/fmp_client.py`

**구조**: 별도 `FMPClient` 클래스 (이름 충돌!), 단일 `FMPAPIError` 예외, httpx 사용.

**`_make_request` (L51–L92) 에러 핸들링 (취약)**:
- `httpx.HTTPStatusError` → `FMPAPIError(f"HTTP {code}: {text}")`로 변환 (L84–L86) — **402도 단순 문자열로 묻힘**
- 401/402/429 코드별 분기 없음 (`FMPPremiumError` 미존재)
- 재시도 없음
- `try/except Exception → raise FMPAPIError(...)`로 모든 예외 흡수 (L90–L92) — 원인 추적 어려움

**캐시 (그나마 보호 장치)**:
- `cache.get/cache.set`을 모든 메서드에서 사용
- TTL: 5분(gainers/losers/actives/sector_stocks/industry_stocks) ~ 24시간(profile/peers/sp500)
- 캐시 장애 시 폴백 없음 — Redis 예외가 그대로 노출

**Rate Limit**: 명시적 sleep 없음, httpx 기본 동작에만 의존 → 300/min 초과 위험 (병렬 호출 다수일 때)

**Timeout**: 30초 (`httpx.Client(timeout=30.0)`)

**의존 호출자**: `serverless/views.py`, `serverless/tasks.py`, `chain_sight_service.py`, `sector_heatmap_service.py`, `market_breadth_service.py`, `filter_engine.py`, `keyword_data_collector.py`, `cusip_mapper.py`, `enhanced_screener_service.py`, `neo4j_chain_sight_service.py`, `data_sync.py` — **운영 사용 빈도 가장 높음**.

### 3) 중복 클라이언트 — `macro/services/fmp_client.py`

**구조**: 또 다른 `FMPClient` (이름 3중 충돌), `ValueError`/`HTTPError`로 에러 전파, requests 사용.

**`_make_request` (L78–L126) 에러 핸들링 (가장 취약)**:
- 200 외 모든 코드 → `response.raise_for_status()` (L113) — 402도 일반 HTTPError로만 잡힘
- `{"Error Message": "..."}` 응답 → `ValueError` raise (L120)
- 재시도 없음
- 각 메서드(`get_quote` L138–L144 등) 단위로 `try/except Exception → return None/{}/[]` 패턴 — 호출자가 실패 원인 판별 불가

**Rate Limit**: `request_delay=0.2` sleep (L101–L102) — 메인 클라이언트와 동일 방식이나 단일 인스턴스 재사용 보장 안 됨 (요청마다 새 인스턴스 가능)

**캐시 없음**: 모든 호출이 매번 외부 요청 → Market Pulse 화면 1회 로드에 다수 호출 동반

**Timeout**: 30초

**의존 호출자**: `macro/services/macro_service.py` (Market Pulse 전체)

**특기**: `get_batch_quotes` L146–L162는 콤마 배치 → 402 에러 회피용 개별 호출로 우회 (L150 주석). 의도된 보호 동작.

### 4) FMP News 위임 — `news/providers/fmp.py`

**구조**: `FMPNewsProvider`는 메인 `FMPClient` 인스턴스를 주입받아 위임 (L23). 자체 통신 없음.

**에러 핸들링**:
- `fetch_company_news/fetch_market_news/fetch_press_releases` 모두 `try/except Exception → return []` (L52, L91, L126)
- 메인 클라이언트의 `FMPPremiumError/FMPAuthError`를 **일반 예외로 흡수 → 원인 손실**

**Rate limit 노출**: `get_rate_limit()` → `{'calls': 300, 'period': 60}` (L268)

### 5) 부수 FMP 모듈 — `stocks/services/fmp_screener.py`

**429 처리 명시**: `Retry-After` 헤더 기반 재시도 (`fmp_screener.py:158–172`). FMP 모듈 중 유일하게 429 코드별 분기.

**Timeout**: 15초

**한계**: 자체 모듈에 갇혀 있어 다른 FMP 호출자에 패턴 전파 안 됨.

---

## Gemini 상세

### 호출 지점 분류

**CircuitBreaker 적용 (강건) — 4건**:
| 파일 | CB 이름 | 추가 특성 |
|---|---|---|
| `rag_analysis/services/llm_service.py:204` | `gemini_rag` (failure=5, recovery=60) | 외부 retry 3회 + CB retry 1회 중복 방지, prompt-injection escape(L178–L192), 429 키워드 매칭 retry(L249–L264) |
| `rag_analysis/services/context_compressor.py` | (동일 CB 사용) | 배치 문서 압축 |
| `thesis/services/thesis_builder.py:459` | `gemini_thesis` (failure=5, recovery=120) | CB OPEN 시 `_fallback_parse(text)` 정규식 폴백 |
| `marketpulse/briefing/client.py:67` | `gemini` (기본 설정) | 동기 + CB 단일 wrap |

**CB 미적용 — 20+건 (주요 위치)**:
- `sec_pipeline/extractor.py:68,128` — 10-K 추출 (Track A 공급망, Track B 사업모델). `JSONDecodeError` 캐치 → `{'error': ...}` 반환, **그 외 예외는 `raise`** (L89–L91, L143–L145). Celery 태스크에서 호출 시 작업 전체 실패 유발.
- `sec_pipeline/intelligence.py:162` — 동일 패턴
- `news/services/news_deep_analyzer.py:125` — Tier C 분석 max_tokens 6000. `except Exception → return None`
- `news/services/stock_insights.py:554` — 한국어 키워드 번역. `except → log warning`
- `news/services/keyword_extractor.py:190`
- `news/api/views.py:817`
- `thesis/services/prompt_builder.py:578,805,974` — 3개소 (EOD 야간 자동화)
- `thesis/services/indicator_matcher.py:226`
- `thesis/tasks/summary.py:67` — Celery 직접 호출
- `thesis/views/conversation_views.py:270`
- `serverless/services/keyword_generator.py:247,256` — async/sync 모두 (Celery는 sync만, L271 주석으로 명시)
- `serverless/services/keyword_service.py:279`
- `serverless/services/llm_relation_extractor.py:384`
- `serverless/services/relationship_keyword_enricher.py:230`
- `serverless/services/regulatory_service.py:439`
- `serverless/services/csv_url_resolver.py:381`
- `serverless/services/thesis_builder.py:359` — 구버전 가설 빌더 (deprecate 후보)
- `validation/services/llm_peer_filter.py:79` — 자연어 → 필터. `except → {'error': str(e)}`

### 429 (Rate Limit) 처리

- **명시적 retry/backoff**:
  - `rag_analysis/services/llm_service.py:248–264` — error 문자열에 `'rate'`/`'quota'`/`'429'` 포함 시 `RETRY_DELAYS=[1,2,4]`초 재시도
  - `portfolio/llm/client.py` — `_classify_gemini_error`(L62–L80)로 `ratelimit/resourceexhausted/quota` 키워드 매칭 → `LLMRateLimitError` 분류 → 1회 재시도 + Anthropic 폴백 (L156–L168)
  - `serverless/services/keyword_service.py:318` — `'rate'/'quota'/'429'` 키워드 매칭 코드 존재 (확인됨)
- **나머지 ~20건**: 429를 일반 `Exception`으로 흡수 → 사용자에게 일반 에러로 노출

### JSON 파싱 에러 처리

- 명시적 `json.JSONDecodeError` 캐치: `sec_pipeline/extractor.py:86,140`, `rag_analysis/services/llm_service.py` 응답 파싱부
- `response_mime_type='application/json'` 강제: extractor, intelligence, llm_peer_filter 등 (LLM이 JSON 강제 모드)
- 정규식 `\{.*\}` 매칭 후 파싱: `thesis_builder.py:475` (`_fallback_parse`)
- 나머지 다수는 `except Exception` 흡수

### Timeout 설정

- Gemini SDK 호출에 **명시적 timeout 없음** — `google.genai.Client` 기본값 의존
- HTTP 레벨 timeout 부재 → 무한 행걸림 가능성 존재 (특히 streaming 호출에서)
- **위험**: `rag_analysis/services/llm_service.py`의 `aio.models.generate_content_stream` 호출은 stream chunk 도착 지연 시 호출자가 영원히 대기

### Celery 동기/비동기 (common-bugs #8)

- `serverless/services/keyword_generator.py` — `_call_llm` (async, L246) / `_call_llm_sync` (sync, L254) 분리. Celery 경로는 sync 전용. 5/19 `b05b214` 패치로 강제됨.
- `rag_analysis/services/llm_service.py` — `aio.models.generate_content_stream` 사용 (async). Celery 직접 호출 없음 (View → async stream으로 추정).
- `marketpulse/briefing/client.py` — `_generate_sync` 명시 (Bug #8 주석)
- `thesis/services/thesis_builder.py:462` — sync 호출 (Celery 안전)
- `thesis/tasks/summary.py:67` — Celery에서 sync 호출 (안전)
- 테스트로 sync 강제 검증: `tests/unit/serverless/test_keyword_generator_sync.py:71` — `aio.models` 미호출 검증

### Prompt Injection 방어 (5/19 P0 패치)

- `rag_analysis/services/llm_service.py:178–192` — `</context_data>`, `</user_question>` 닫는 태그 escape, 신뢰 경계 명시 (security audit P0 #3)
- `thesis/services/prompt_builder.py` — 동일 패턴 적용 추정 (`71b2d2f` 커밋 메시지에 thesis 명시)
- **갭**: 다른 호출 지점(sec_pipeline, news, serverless, validation 등)에는 동일 가드 없음. 사용자 입력이 LLM 프롬프트에 직접 인터폴레이트되는 경로 추가 점검 필요.

---

## 기타 의존성

### FRED API — `macro/services/fred_client.py`

**상태**: 양호. 메인 FMP 클라이언트와 동급
- `TRANSIENT_STATUS_CODES = {500, 502, 503, 504}` 명시 (L26)
- 401/403/404 → 즉시 `raise_for_status` (L106–L111)
- transient 코드는 `(attempt+1)*2`초 backoff로 3회 재시도 (L114–L128)
- `api_request.rate_limiter.get_rate_limiter("fred")` 사용 (L15, L70) — 분당 120회 보호
- Timeout 30초
- CB 미적용이나 자체 retry로 보강

### Neo4j

**Driver**: `rag_analysis/services/neo4j_driver.get_neo4j_driver()` 단일 진입점
- `connection_acquisition_timeout` 설정에서 로드 (L54)
- 모든 쿼리에 `QUERY_TIMEOUT` 적용 (`rag_analysis/services/neo4j_service.py:118,163,210,273,280,346,382,412`)

**CB 적용**: `serverless/services/neo4j_chain_sight_service.py:108–120`
- `is_available()`에서 driver None 체크 + CB(`neo4j_chain_sight`, failure=5, recovery=60) 상태 확인
- CB OPEN 시 silent failure 방지 (주석 L114)
- Driver None일 때 "fallback mode" 경고 후 통과 (L111) — 호출자 측 검증 필요

**기타 호출자**: `chainsight/tasks/*.py`, `news/services/news_neo4j_sync.py`, `serverless/services/data_sync.py`, `chainsight/services/neo4j_loader.py` — CB 미적용 (대부분 단일 sync 호출)

### SEC EDGAR — `sec_pipeline/collector.py`

- **Rate limit**: `time.sleep(0.12)` (L83) — SEC 권장 10 req/s 준수
- **User-Agent**: 명시 (L30 — `Stock-Vis stockvis@example.com`)
- **재시도**: 없음 — `RequestException`은 그대로 `raise` (L89–L91)
- **CIK 캐시**: 클래스 레벨 dict `_cik_cache` (L43) — 프로세스 재시작 시 휘발
- **Timeout**: 30초

**위험**: 단일 timeout/network 실패에 SEC 파이프라인 1회 실행 전체가 죽음. EDGAR 일시 장애 시 외부 의존성 캐스케이드. Celery `autoretry_for=(RequestException,)` 설정으로 자동 재시도 가능한지 `sec_pipeline/tasks.py` 확인 필요.

### Redis (캐시)

**의존 파일**: 30+ 모듈에서 `from django.core.cache import cache`

**Graceful degradation 현황**:
- 대부분 `cache.get(...)` → None이면 fetch → `cache.set` 순서 (정상)
- 그러나 `cache.set/cache.get` 자체가 RedisError를 raise하면 try/except 없는 곳 다수
- 명시적 try/except 캐시 보호: `news/services/circuit_breaker.py:35–48` (CB 내부 보호), `marketpulse/utils/circuit_breaker.py` 내부 정도

**구조적 위험**: **CircuitBreaker 자체가 Redis 캐시에 의존** (`marketpulse/utils/circuit_breaker.py`에서 `cb:state:{name}` 키를 Django cache에 저장). Redis 장애 → CircuitBreaker 무력화 → 추가 cascading failure.

**테스트 격리**: `config/settings_test.py:24`에서 LocMemCache 사용 (common-bugs #27 — pytest가 운영 Redis flush 방지)

### Alpha Vantage (잔재)

- 활성 운영 코드 없음 (`api_request/providers/alphavantage/` 디렉토리 부재)
- 잔재: `tests/conftest.py`, `news/models.py`, `news/migrations/0005_*.py`, `api_request/__init__.py`에 식별자만 존재
- 결론: 실제 호출 경로 없음. CLAUDE.md의 "Alpha Vantage 5 calls/분" 코딩 룰은 현시점 운영 코드 미적용 (역사 잔재)

---

## Circuit Breaker 도입 후보 (우선순위)

### P0 — 즉시 검토 (시스템 전체 캐스케이드 위험)

**1. `macro/services/fmp_client.py` 전체**
- 영향: Market Pulse 페이지 모든 호출 (지수/섹터/원자재/환율/treasury/economic_calendar)
- 현 상태: 재시도 0, 캐시 0, 402 미처리, 단일 인스턴스 보장 안 됨
- 권장 패턴: 메인 `FMPClient`로 통합 OR `get_circuit('fmp_macro', failure=5, recovery=120).call(...)` 래핑 + 5분 캐시 레이어 추가
- 예상 효과: 5분 캐시만으로도 Market Pulse Rate-limit 충돌 80% 감소 (페이지 새로고침 패턴 기준)

**2. `serverless/services/fmp_client.py` 전체**
- 영향: Chain Sight, Market Movers, Screener, Sector Heatmap 등 운영 트래픽 다수
- 현 상태: 캐시 OK / 재시도 0 / 402 미처리 / FMPPremiumError 없음
- 권장 패턴: `_make_request`에 `get_circuit('fmp_serverless').call(...)` + 메인 클라이언트의 예외 계층(`FMPClientError/FMPRateLimitError/FMPPremiumError/FMPAuthError`)으로 통일

**3. `sec_pipeline/extractor.py:68,128` Gemini 호출**
- 영향: 10-K 파이프라인 Celery 작업 전체 실패 유발 가능
- 현 상태: `JSONDecodeError`만 처리, 그 외 `raise`
- 권장 패턴: `get_circuit('gemini_sec', failure=10, recovery=300).call(...)` + 비-JSON 예외도 partial result로 폴백 → 다음 단락 진행 가능

### P1 — 단기 (사용자 영향 직접)

**4. `news/services/news_deep_analyzer.py:125` Gemini Tier C**
- 영향: 뉴스 인텔리전스 파이프라인. max_tokens=6000으로 호출당 비용/시간 큼
- 현 상태: 단일 except → None. 429 폭주 보호 없음
- 권장 패턴: 기존 `marketpulse.utils.circuit_breaker` 재사용 (CB 이름 `gemini_news_deep`, failure=5, recovery=300)

**5. `thesis/services/prompt_builder.py:578/805/974` Gemini 3개소**
- 영향: EOD 파이프라인 야간 자동 호출 (memory `project_p0_security_patches_2026-05-20` 참조)
- 현 상태: 모두 CB 미적용
- 권장 패턴: 단일 CB(`gemini_thesis_prompt`) + JSON 강제 + fallback (regex 파싱)

**6. `thesis/tasks/summary.py:67` Gemini in Celery**
- 영향: Celery 야간 태스크
- 권장 패턴: 기존 `gemini_thesis` CB와 통합 (별도 이름 불필요)

### P2 — 중기 (자체 폴백 있으나 보강)

**7. `validation/services/llm_peer_filter.py:79`**
- 현재 `{'error': str(e)}` 폴백은 UX 측면에서 명확하나, 429 폭주 시 사용자가 같은 입력으로 재시도하면 또 호출됨
- 권장: CB OPEN 시 "잠시 후 다시 시도하세요" 문구 + 클라이언트 측 backoff hint

**8. `portfolio/llm/client.py`**
- 이미 1회 retry + Gemini↔Anthropic 폴백 + 비용 가드 보유 (강건)
- 한 provider가 지속 실패 시 매 호출마다 폴백 시도로 2배 호출
- 권장: CB 추가는 선택 (현재 폴백 메커니즘으로 충분 가능). 둘 다 죽었을 때 CostGuard로 차단되긴 함.

### P3 — 인프라

**9. CircuitBreaker 구현체 통합**
- `news/services/circuit_breaker.py` (Redis 카운터 단순) vs `marketpulse/utils/circuit_breaker.py` (tenacity + HALF_OPEN 상태 머신)
- 권장: news 모듈 → marketpulse 버전으로 통합 (네이밍만 다른 동일 개념)

**10. CircuitBreaker의 Redis 의존성 해소**
- Redis 장애 = CB 무력화 → cascading
- 권장: in-process fallback (Redis 실패 시 메모리 카운터) 또는 Redis HA 보장

**11. FMP 클라이언트 3종 통합**
- 운영 위험도 가장 큰 부채. `serverless/services/fmp_client.py`와 `macro/services/fmp_client.py`를 `api_request/providers/fmp/client.py`에 위임하는 형태로 단계 통합
- 캐싱 레이어는 wrapper로 분리

---

## 권장 액션 아이템 (코드 미수정, 후속 작업 제안)

### 단기 (1주)
- [ ] `macro/services/fmp_client.py`에 단순 5분 캐시 + retry 1회 추가 (~10줄 변경, Market Pulse 안정성 대폭 향상)
- [ ] Gemini 호출 지점 표준 헬퍼 함수 도입 검토: `marketpulse.utils.gemini_call(name, prompt, config, fallback)` 같은 wrap 함수로 CB 누락 위험 감소
- [ ] FMP 클라이언트 3종 통합 로드맵 문서화 (단계별 deprecation 계획)

### 중기 (1개월)
- [ ] `sec_pipeline/tasks.py` Celery 작업에 `autoretry_for=(Exception,)` + `retry_backoff=True` 설정 확인. 누락 시 추가
- [ ] Gemini 호출 카운터 메트릭: 호출 수/실패율/CB OPEN 회수를 Daily report에 포함 (memory `project_operations_infra_2026-05` 참조)
- [ ] Redis 장애 시뮬레이션 테스트: CB가 Redis 의존인지 검증 + 메모리 폴백 적용 여부 결정
- [ ] Prompt injection 가드 확산: rag_analysis 패턴을 sec_pipeline, news, serverless, validation의 사용자 입력 경로에 일관 적용

### 장기
- [ ] CircuitBreaker 구현체 단일화 (`news/services/circuit_breaker.py` deprecate)
- [ ] FMPPremiumError 처리 일관성 — `provider.py`는 재무제표 3종만 캐치. `get_quote/get_company_profile/get_daily_prices/search_symbols/get_sector_performance`도 동일 핸들링 추가
- [ ] Gemini 호출 timeout 명시화 (현재 SDK 기본값 의존, 무한 행걸림 가능)
- [ ] FMP `reset_daily_counter()` 자동 호출 보장 (Celery beat에 자정 태스크 등록)

---

## 부록 A: CircuitBreaker 적용 현황 비교

| 영역 | 적용 | 미적용 | 비고 |
|---|---|---|---|
| Gemini | 4 (rag×2, thesis_builder, marketpulse briefing) | 20+ | sec_pipeline·news·thesis prompt·serverless·validation 누락 |
| FMP | 5 (sp500×2, data_sync, news_aggregator, fmp_weights) | 30+ | 운영 빈도 가장 높은 serverless/macro 클라이언트 미적용 |
| Neo4j | 1 (neo4j_chain_sight) | 미확인 (chainsight/tasks/ 등) | driver None 시 silent skip |
| SEC | 0 | 1 (sec_pipeline/collector.py) | rate-limit sleep만 존재 |
| FRED | 0 | 1 (fred_client.py) | 자체 retry+rate-limiter로 보강 |

## 부록 B: 매트릭스 변화 추적 (5/20 → 5/21)

| 항목 | 5/20 | 5/21 | Δ |
|---|---|---|---|
| FMP 클라이언트 수 | 3 | 3 | - |
| FMP 사용 파일 | 35 | 35 | - |
| Gemini 호출 지점 (활성) | ~24 | ~24 | - |
| CB 적용 모듈 | 17 | 17 | - |
| FMPPremiumError 일관성 결함 | 6개 메서드 | 6개 메서드 | - |
| Prompt injection 가드 적용 모듈 | 1 (rag) | 1 (rag) + thesis(추정) | thesis 적용 확인 필요 |

**결론**: slice13 작업은 외부 API 의존성 레이어를 건드리지 않았으므로 직전 보고서 권고가 그대로 유효함. P0 #1~#3 우선순위로 후속 작업 진입 권장.
