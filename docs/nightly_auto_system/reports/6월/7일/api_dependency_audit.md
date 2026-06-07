# 외부 API 의존성 감사 보고서

> 작성일: 2026-06-07 · 읽기 전용 감사(코드 수정 없음) · 대상: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis
> 조사 방식: 영역별 5개 에이전트 병렬 정적 분석, 모든 판정은 `파일:라인` 근거 기반
> 프로젝트 구조 주의: 모노레포로 재편됨 — `packages/shared/`, `apps/`, `services/`, `thesis/` 로 분산

---

## 요약 (Executive Summary)

| 의존성 | 장애 대응 성숙도 | 한 줄 요약 |
|--------|:---:|------|
| **FMP** | 🟡 부분적 | 클라이언트 3벌 공존, 장애 대응 정책 제각각. 사용자 동기 경로(`views_search`)에 CB·캐시 폴백 전무 |
| **Gemini** | 🟡 부분적 | 모델명 통일됐으나 **timeout 0건**, 429 미처리 다수, SDK 미스매치 2건(런타임 실패 가능) |
| **FRED** | 🟢 양호 | 앱+Celery 2중 retry, 단 429 미재시도 + 캐시 미스 시 DB 폴백 없음 |
| **Neo4j** | 🟢 우수 | lazy driver + `is_available()` + CircuitBreaker로 죽지 않고 degrade (드라이버 3종 혼재가 흠) |
| **SEC EDGAR** | 🟡 보통 | sleep 0.12s 페이싱 + 차등 retry, 단 **429/Retry-After 미준수** |
| **Redis** | 🔴 취약 | `IGNORE_EXCEPTIONS` 미설정 → 캐시 장애가 곧 요청 실패. **단일 장애점**(캐시+broker+Channels+CB 상태+RateLimiter 동시 마비) |

**최우선 리스크 3건**
1. 🔴 **Redis 단일 장애점 + graceful degradation 없음** — Redis 다운 시 시스템 광범위 마비, CircuitBreaker 상태조차 Redis에 의존 → "Redis 장애 → CB 무력화 → 외부 API 무방비 호출" 연쇄
2. 🔴 **Gemini SDK 미스매치 2건** — `thesis/tasks/summary.py:65-67`, `apps/market_pulse/briefing/client.py:50-55` 가 구 SDK `google.generativeai`에서 `.Client()` 호출 → 런타임 `AttributeError` 가능, 에러를 빈 문자열로 삼켜 조용히 실패
3. 🔴 **FMP 사용자 동기 경로 무방비** — `views_search.py` 검색/검증이 CB·stale 캐시 폴백 없이 FMP 직결 → 캐시 만료 + FMP 장애 겹치면 500/503

---

## 1. 의존성 매트릭스 (서비스별 외부 API × fallback 유무)

| 서비스 / 모듈 | 외부 API | retry | rate limit | 에러 핸들링 | fallback | 사용자 영향 |
|---|---|:---:|:---:|:---:|:---:|---|
| `api_request/providers/fmp/client.py` (정식) | FMP | ✅ 3회 | 🟡 delay만 | 🟡 | ❌ | (위임) |
| `api_request/providers/fmp/serverless_client.py` | FMP | ❌ | ❌ | ✅ | 🟡 캐시 | (위임) |
| `api_request/providers/fmp/market_pulse_client.py` | FMP | ❌ | 🟡 delay만 | 🟡 은폐 | ❌ | (위임) |
| `stocks/views_search.py` | FMP | ❌ | ❌ | ✅ | ❌ | 🔴 **500/503/404** |
| `serverless/enhanced_screener_service.py` | FMP | ❌ | ❌ | ✅ | ❌ | 🟡 빈 결과 |
| `serverless/filter_engine.py` | FMP | ❌ | ❌ | ✅ | ❌ | 🟡 빈 결과 |
| `serverless/market_breadth_service.py` | FMP | ❌ | ❌ | ✅ | 🟡 고정값 | 🟡 None |
| `serverless/data_sync.py` | FMP | 🟡 CB | ❌ | ✅ | ❌ | (배치) |
| `serverless/sector_heatmap_service.py` | FMP | ❌ | ❌ | ✅ | 🟡 추정값 | 🟢 빈 섹터 |
| `serverless/chain_sight_service.py` | FMP | ❌ | ❌ | ✅ | 🟡 | 🟢 빈 결과 |
| `serverless/keyword_data_collector.py` | FMP | ❌ | ❌ | ✅ | ✅ 다단계 | 🟢 |
| `market_pulse/macro_service.py` | FMP+FRED | ❌ | ❌ | ✅ | ❌ | 🟢 error키 |
| `market_pulse/news_aggregator.py` | FMP+Marketaux | 🟡 CB | ❌ | ✅ | ✅ Marketaux | 🟢 |
| `news/services/aggregator.py` | FMP+Finnhub+Marketaux | ❌ | ❌ | ✅ | ✅ 주력Finnhub | 🟢 |
| `stocks/tasks.py` | FMP(위임) | 🟡 비일관 | 🟡 | ✅ | ✅ AV교차 | (배치) |
| `thesis/tasks/eod_pipeline.py` | FMP | ❌ retry무력 | 🟡 | ✅ | 🟡 null기록 | (배치) |
| `rag_analysis/llm_service.py` | Gemini | ✅ 3회+CB | ✅ 429 | ✅ | ✅ | 🟢 (모범) |
| `rag_analysis/adaptive_llm_service.py` | Gemini | ❌ | ❌ | ✅ | 🟡 | 🟢 error yield |
| `rag_analysis/context_compressor.py` | Gemini | ❌ | ❌ | ✅ | ✅ truncate | 🟢 |
| `rag_analysis/entity_extractor.py` | Gemini | ❌ | ❌ | ✅ | ✅ 규칙기반 | 🟢 |
| `thesis/services/thesis_builder.py` | Gemini | 🟡 CB | ❌ | ✅ | ✅ 위저드 | 🟢 |
| `thesis/services/prompt_builder.py` | Gemini | ❌ | ❌ | ✅ | 🟡 호출측 | 🟢 None |
| `thesis/tasks/summary.py` | Gemini | ❌ 무력 | ❌ | 🔴 SDK오류 | 🟡 빈문자열 | 🔴 영구 실패 가능 |
| `thesis/views/conversation_views.py` | Gemini | ❌ | ❌ | ✅ | ✅ 제목기반 | 🟢 |
| `serverless/keyword_service.py` | Gemini | ✅ retry | ✅ 429 | ✅ | ✅ | 🟢 (모범) |
| `serverless/keyword_generator_v2.py` | Gemini | ❌ | ❌ | ✅ | 🟡 | 🔴 async+fork위험 |
| `serverless/llm_relation_extractor.py` | Gemini | ❌ | 🟡 선제sleep | ✅ | 🟡 캐시 | 🟢 |
| `serverless/regulatory_service.py` | Gemini | ❌ | 🟡 선제sleep | ✅ | 🟡 | 🔴 구모델명 |
| `serverless/thesis_builder.py` | Gemini | ❌ | ❌ | ✅ | ✅ 4단계파싱 | 🟢 |
| `news/services/keyword_extractor.py` | Gemini | ❌ | ❌ | ✅ | ✅ 정적 | 🟢 |
| `news/services/news_deep_analyzer.py` | Gemini | ❌ | 🟡 선제sleep | ✅ | ❌ | 🟢 None |
| `news/services/stock_insights.py` | Gemini | ❌ | ❌ | ✅ | ✅ 무변환 | 🟢 |
| `sec_pipeline/intelligence.py` | Gemini | ❌ | ❌ | ✅ | 🔴 critical박제 | 🟡 |
| `sec_pipeline/extractor.py` | Gemini | ❌ | ❌ | ✅ | 🟡 빈값/raise | (배치) |
| `validation/llm_peer_filter.py` | Gemini | ❌ | ❌ | ✅ | ❌ error dict | 🟡 trust경계 |
| `portfolio/llm/client.py` | Gemini+Claude | ✅ 1회+교차 | ✅ 429 | ✅ | ✅ provider전환 | 🟢 (모범) |
| `market_pulse/briefing/client.py` | Gemini | ✅ tenacity | 🟡 무차별 | 🔴 SDK오류 | CB | 🟡 |
| `sec_pipeline/collector.py` | SEC EDGAR | 🟡 차등 | 🟡 sleep만 | ✅ | 🟡 edgartools | (배치) |
| `api_request/fred_client.py` | FRED | ✅ 3회 | ✅ limiter | ✅ | 🟡 | 🟢 neutral |
| `serverless/neo4j_chain_sight_service.py` | Neo4j | 🟡 CB | N/A | ✅ | ✅ 빈결과 | 🟢 |
| `chain_sight/graph/repository.py` | Neo4j | ❌ | N/A | ✅ | 🔴 raise | (배치) |

범례: ✅ 있음 · 🟡 부분적 · ❌ 없음 · 🔴 위험

---

## 2. FMP 상세

### 2.1 핵심 발견: 동일 이름 `FMPClient` 3벌 공존

같은 `FMPClient` 클래스가 **서로 다른 장애 대응 정책**으로 3벌 존재한다 — 가장 중요한 구조적 결함.

| 클라이언트 | 라이브러리 | timeout | retry | rate limit | 402(FMPPremiumError) | 캐싱 |
|---|---|:---:|:---:|:---:|:---:|:---:|
| `client.py` (정식) | requests | 30s | ✅ 3회 | 🟡 delay+일한도 | ✅ | ❌ |
| `serverless_client.py` | httpx | 30s | ❌ | ❌ | ❌ | ✅ Django cache |
| `market_pulse_client.py` | requests | 30s | ❌ | 🟡 delay만 | ❌ | ❌ |

에러 타입도 갈림: `FMPAPIError`(serverless) vs `FMPClientError`/`FMPPremiumError`(정식) → 핸들링 패턴 이원화.

### 2.2 취약점 (심각도 순)

**High**
- **분당 300-call 보호 부재 (전 클라이언트)**: 슬라이딩 윈도우 카운터 없음. `client.py`는 0.2초 고정 delay(`client.py:107-110`)로 단일 스레드에서만 5 req/s 보장 — **멀티 워커/Celery 동시 실행 시 분당 300 초과 가능**. `serverless_client.py`는 delay조차 없어 캐시 미스 폭주 시 무방비.
- **`views_search.py` 사용자 직격 500/503**: 유일한 사용자 동기 경로인데 CB·캐시 폴백 둘 다 없음.
  - `SymbolSearchView` 실패 시 503(`views_search.py:51-54`) / 500 + 내부 예외 메시지 노출(`views_search.py:83-87`)
  - `SymbolValidateView` 실패 시 404(`views_search.py:115-119`) / 500(`views_search.py:142-146`)
  - 캐시는 읽지만(`views_search.py:39-42, 106-107`) **API 실패 시 stale 캐시로 폴백 안 함** → 캐시 만료 + FMP 장애 겹치면 검색/검증 완전 정지
- **`market_pulse_client.py` 에러 은폐 (silent failure)**: 모든 예외를 빈 값으로 변환 — `get_quote→None`(`:142-144`), `get_treasury_rates→{}`(`:438-440`), `get_economic_calendar→[]`(`:412-414`). rate limit/네트워크 장애와 "데이터 없음"이 구분 불가 → 부분 시장 데이터가 정상처럼 표시될 위험.
- **serverless/market_pulse에 retry 전무**: 일시적 네트워크 오류 복원력 없음. `client.py`만 retry 보유.

**Medium**
- **402 처리 불일치**: `FMPPremiumError`가 `client.py`에만 정의/발생(`client.py:39-42, 131-134`). `provider.py`는 재무 3종(balance/income/cash_flow)에만 catch(`:233-239` 등) — quote/profile/price 경로의 402는 일반 `API_ERROR`로 뭉개짐(`provider.py:87-91`).
- **JSONDecodeError 미처리 (전 클라이언트)**: `response.json()` 실패 미포착. `client.py`에선 retry except(`:158`)에 안 걸려 3회 모두 즉시 실패.
- **`serverless_client.py` 리소스 정리를 `__del__`에 의존**(`:49-52`): GC 타이밍 비결정적, context manager 미사용으로 연결 누수 가능.

**Low**
- **선형 backoff (지수 아님)**: `client.py:161` 주석은 "Exponential"이나 실제는 `(attempt+1)*2` = 2,4초 선형. 라벨-구현 불일치.

### 2.3 횡단 관찰
- **CircuitBreaker 적용 일관성 부재**: CB 있음 — `sp500_service`, `sp500_eod_service`(부분), `data_sync`(movers만), `news_aggregator`. CB 없음 — `filter_engine`, `enhanced_screener_service`, `market_breadth_service`, `sector_heatmap_service`, `macro_service`, **`views_search`**(가장 큰 갭).
- **`_make_request` 직접 호출이 CB 우회**: `filter_engine:272`, `enhanced_screener_service:238/287`, `chain_sight_service:498/558` — 보호 없는 raw 호출.
- **stale 캐시 폴백 없음 (전 서비스)**: "정상 응답만 캐시 → 만료 시 재호출". FMP 장애 + 캐시 만료 겹치면 캐시 무력.
- **`self.retry` 누락으로 retry 무력화**: `eod_pipeline.py` 3개 태스크와 `tasks.py:update_financials_with_provider`는 `max_retries` 선언만 있고 실제 `self.retry()` 호출 코드 없음 → 1회 실패로 종료. `update_financials`는 except에서 로깅만 하고 삼킴(`tasks.py:575-576`) → 재무제표 fetch 실패가 조용히 사라짐.

### 2.4 모범 폴백 사례
- `keyword_data_collector.py`: overview 실패 → news만 → Marketaux→Finnhub 폴백 → `_empty_context` (다단계)
- `stocks/tasks.py`: `use_fallback=True`로 Alpha Vantage↔FMP 교차 폴백
- `news/services/aggregator.py`: 주력 Finnhub+Marketaux, FMP는 보조 — FMP 장애가 뉴스 수집 안 막음

---

## 3. Gemini 상세

### 3.1 핵심 위험 지점

| 위험 | 파일:라인 | 내용 |
|---|---|---|
| 🔴 **SDK 미스매치 (런타임 실패 가능)** | `thesis/tasks/summary.py:65-67` | 구 SDK `import google.generativeai as genai_module` 후 `genai_module.Client()` 호출. 구 SDK엔 `.Client()` 없음 → `AttributeError` → except가 빈 문자열 반환 → `failed+=1`로 조용히 누락. **AI 요약이 영구 빈 문자열일 수 있음** |
| 🔴 **SDK 미스매치 #2** | `market_pulse/briefing/client.py:50-55` | 동일 패턴 — 다른 11개 파일은 신 SDK `from google import genai`인데 이 파일만 구 SDK `.Client()` 호출. 일일 브리핑 태스크 런타임 실패 가능 |
| 🔴 **구버전 모델명** | `serverless/regulatory_service.py:515` | `gemini-2.0-flash-exp` — 다른 15개는 전부 `gemini-2.5-flash`. exp 모델 폐기 위험 |
| 🔴 **async-only + fork 위험** | `serverless/keyword_generator_v2.py:407` | Celery에서 `loop.run_until_complete` 래퍼 — Bug #25(fork+asyncio SIGSEGV) 재현 우려. v1은 이 문제로 sync 전환했으나 v2 미적용 |
| 🟡 **timeout 전무 (전 파일)** | 모든 파일 | LLM 호출에 timeout 인자 0건. 네트워크 행(hang) 시 무한 대기. Celery 배치(news/korean)에서 워커 점유 위험 |
| 🟡 **429 미처리 (다수)** | 아래 표 | Gemini Free 15 RPM에서 배치 시 연쇄 실패 |

### 3.2 CLAUDE.md Bug #8 (Celery=동기) 준수 현황
- 대부분 **동기 API** 사용 — 준수 양호.
- async는 RAG 스트리밍(뷰)용으로만: `llm_service`, `adaptive_llm_service`, `context_compressor`, `entity_extractor` — Celery 아님, 적합.
- **예외 (위험)**: `keyword_generator_v2.py` 가 async-only인데 Celery에서 `run_until_complete`로 강제 동기화 → fork 안전성 위배.

### 3.3 429 처리 현황
- **제대로 된 429 대응 3곳뿐**:
  - `rag_analysis/llm_service.py:251-268` — `"rate"/"quota"/"429"` 감지 + 지수백오프 `[1,2,4]` + CircuitBreaker
  - `serverless/keyword_service.py:324-330` — 429 감지 + `(attempt+1)*2`초 대기, max_retries=2
  - `portfolio/llm/client.py:71-77` — `_classify_gemini_error`로 `LLMRateLimitError` 분류 → 1회 재시도 → 교차 provider fallback
- **선제 sleep만 (반응형 아님)**: `news_deep_analyzer.py:99`, `korean_overview_service.py:140`, `llm_relation_extractor.py:370`, `relationship_keyword_enricher.py:157`, `regulatory_service.py` — `time.sleep(4)` 페이싱. **429 실제 발생 시 그대로 실패**.
- **나머지 다수**: 429를 일반 `except`로 뭉갬.

### 3.4 JSON 파싱 견고성
- **모범 (복구 로직 있음)**: `keyword_service.py:354-385`(잘린 JSON 정규식 복구), `serverless/thesis_builder.py:417-440`(4단계 추출 ```json→```→{}→전체), `llm_relation_extractor.py:468-493`(부분 JSON 복구), `keyword_extractor.py:315-372`(부분 복구→정적 fallback)
- **취약 (raw loads, 검증 의존)**: `conversation_views.py:283`(markdown 미제거 직접 `json.loads`), `korean_overview_service.py:75`(단독 loads, JSONDecode 분기 없이 광범위 except 의존), `intelligence.py:180`/`llm_peer_filter.py:86`(`response_mime_type=json`에만 베팅)

### 3.5 특이 위험
- **`llm_peer_filter.py` trust boundary**: LLM 출력 dict를 검증 없이 `execute_peer_filter`의 ORM 필터(`metric_code_id=code` 등)에 직접 주입(`:251`). 잘못된 LLM 출력이 쿼리 오류/예외 유발 가능.
- **`intelligence.py` critical 박제**: LLM/파싱 실패 시 `health_score=0, severity="critical"` 더미 리포트를 실제 DB 저장(`:200-214`) → 운영 대시보드에 거짓 critical 경보.

### 3.6 모범 사례 (참고)
- `portfolio/llm/client.py`: 예외 분류 → 통합 예외 계층 → RateLimit/Timeout만 선별 재시도 + **교차 provider(Gemini↔Claude) fallback** + 비용 가드. 가장 견고.
- `rag_analysis/llm_service.py`: CircuitBreaker + retry + 429 지수백오프.
- `serverless/keyword_service.py`: 429 + 잘린 JSON 복구 + 정적 fallback.

---

## 4. 기타 의존성

### 4.1 FRED (`packages/shared/api_request/fred_client.py`) — 🟢 양호
- **timeout**: `requests.get(..., timeout=30)`(`:103`). 단 모듈마다 `FREDClient()` 신규 생성 — Session/pool 재사용 없음.
- **retry**: 앱 레벨 3회 + 백오프 `(attempt+1)*2`(`:120,141,147`), Celery `update_economic_indicators` 3회 + 지수 backoff(`market_pulse/tasks/macro.py:66`).
- **취약**: **429가 transient 집합에 없음**(`:26`) → 429 시 즉시 raise, 재시도 안 함. 분당 100 RateLimiter로 사전 차단하나 Redis 장애 시 무력화 가능.
- **degradation 한계**: 캐시 미스 + FRED 실패 시 **DB(`EconomicIndicator`) 폴백 없음** → neutral 기본값(value=50, label='중립')(`macro_service.py:83-91`) 또는 error dict 반환. 즉 Redis 캐시 정상일 때만 stale 서빙 가능.

### 4.2 Neo4j — 🟢 우수 (단 드라이버 3종 혼재)
- **`rag_analysis/services/neo4j_driver.py`** (Chain Sight/serverless): lazy singleton, 연결 실패 시 **None 반환하고 앱 계속**(`:70-74`). pool `connection_acquisition_timeout=60`(`:53-61`). fork 안전 `force_reset_after_fork()`(`:108-119`, SIGSEGV 방지).
- **`serverless/neo4j_chain_sight_service.py`**: 모든 public 메서드 진입부 `if not self.is_available(): return []/{}` 패턴 → **Neo4j 다운 시 Chain Sight 죽지 않고 빈 결과/실패 플래그**. **CircuitBreaker 통합**(임계 5회/복구 60s, `:68-69`, `_run_with_cb()`).
- **`chain_sight/graph/repository.py`** (SEC sync): PID 기반 lazy init(fork 안전, `:48-67`). 단 연결 실패 시 `GraphConnectionError` raise(`:66`) — **graceful 아님, 예외 전파**. 호출부(`sec_pipeline/tasks.py:529-531`)에서 잡아 raise.
- **버그 #21 대응 확인**: supply_chain_service는 Neo4j 미가용 시 `return 0`(`:370-372`), 개별 관계 실패 `continue`(`:412-414`) → Chain Sight 수집/조회 중단 안 됨.
- **숨은 의존성**: CircuitBreaker가 상태를 **Redis 캐시에 저장**(`circuit_breaker.py:64,73-74`) → Redis 죽으면 CB 추적도 마비.

### 4.3 SEC EDGAR (`services/sec_pipeline/collector.py`) — 🟡 보통
- **User-Agent 필수 헤더** 포함(`:29-32`). timeout: submissions 30s/ticker 15s/HTML 60s(`:86,132,154`). 단 Session 재사용 없음.
- **rate limit**: 호출 전 `time.sleep(0.12)` 고정(`:83,130,151`) ~8.3 req/s — SEC 10 req/s 이하. CIK 클래스 캐시(`:43,127-128`)로 중복 절감.
- **취약**: **429/`Retry-After` 전용 처리 전무**(grep 0건). 동시 워커 다수면 합산 req/s 10 초과 가능, 그때 429는 `raise_for_status()`로 즉시 실패(`:87,155`). 즉시 재시도가 throttling 악화 우려.
- **retry**: 차등 — `collect_and_extract` 3회 + `soft_time_limit=300`(`tasks.py:22`), HTML 다운로드 5회 + 10s 백오프(`:70-72`). edgartools fallback(`:189-215`, regex 추출 실패 시에만).

### 4.4 Redis — 🔴 가장 취약 (단일 장애점)
- **설정**: 단일 인스턴스, 센티넬/폴백 없음. 캐시 `RedisCache redis://127.0.0.1:6379/1`(`settings.py:500-505`), Celery broker `redis://localhost:6379/0`(`:484-485`), Channels(`:509-516`).
- **🔴 graceful degradation 없음**: Django 내장 `RedisCache` 사용 + **`OPTIONS`에 `IGNORE_EXCEPTIONS` 미설정**(grep 0건) → Redis 다운 시 `cache.get`/`cache.set`이 `ConnectionError`를 그대로 전파.
- **DB 직접 조회 폴백 경로 없음**: 캐시 장애 시 macro_service 등은 각자 try/except로 잡아 neutral/error 디그레이드 — 데이터가 아니라 에러 디그레이드.
- **rate_limiter 폴백 무의미**: Redis 직접 접근 실패 시 Django cache로 fallback하나(`rate_limiter.py:135-141`) 그 cache 자체가 Redis → 동일 장애 시 무의미(allow 쪽으로 흐를 위험).
- **연쇄 영향**: Redis 다운 시 ① 캐시 ② Celery broker(태스크 디스패치 불가) ③ Channels(WebSocket) ④ **CircuitBreaker 상태** ⑤ RateLimiter 동시 마비. **"Redis 장애 → CB 무력화 → 외부 API 무방비 호출"** 연쇄 가능.

---

## 5. Circuit Breaker 후보

> 기준: 장애 시 전체 시스템 영향이 크거나, 사용자 동기 경로이거나, 현재 보호 장치가 전무한 호출 지점.

| 우선순위 | 대상 | 현재 상태 | 도입 효과 |
|:---:|---|---|---|
| **P0** | `stocks/views_search.py` (FMP 검색/검증) | CB·retry·캐시폴백 모두 없음, 사용자 동기 직격 | 500/503 폭주 차단 + stale 캐시 폴백 연계 |
| **P0** | `serverless/enhanced_screener_service.py` (FMP 1차 스크리너) | CB 없음, 단일 의존 | 스크리너 전체 무력화 방지 |
| **P0** | `serverless/filter_engine.py` (FMP 스크리너) | CB 없음, 단일 의존 | 동일 |
| **P1** | `market_pulse/macro_service.py` (FMP+FRED 다중 호출) | CB 없음, 메서드별 try만 | 거시 대시보드 부분 장애 격리 |
| **P1** | `serverless/market_breadth_service.py` (FMP movers 3종) | CB 없음, 예외 전파 | breadth 계산 보호 |
| **P1** | `serverless/sector_heatmap_service.py` (FMP 다중) | CB 없음 | 섹터 히트맵 보호 |
| **P2** | Gemini 배치 경로 (`prompt_builder`, `conversation_views`, `serverless/thesis_builder`, `news_deep_analyzer`) | 429 미처리, CB 없음 | `llm_service.py`의 `gemini_rag` CB 패턴 확산 |
| **P2** | `sec_pipeline/collector.py` (SEC EDGAR) | sleep만, 429 미준수 | 429 throttling 시 자동 차단 + Retry-After 준수 |

**선행 조건 (CB 자체의 취약점)**: 현재 CircuitBreaker가 상태를 Redis에 저장하므로(`circuit_breaker.py:64,73-74`), Redis 장애 시 CB가 무력화된다. CB 확산 전에 **(a) Redis `IGNORE_EXCEPTIONS=True` 설정 + (b) CB 상태의 로컬 메모리 폴백**을 먼저 갖춰야 CB 확산의 효과가 보장된다.

---

## 부록: 권고 우선순위 (감사 의견, 코드 변경 없음)

1. **🔴 즉시 검증** — `thesis/tasks/summary.py:65-67`, `market_pulse/briefing/client.py:50-55` SDK 미스매치. 신 SDK(`from google import genai; genai.Client()`)로 통일 필요. 현재 런타임 실패 + 조용한 누락 가능.
2. **🔴 즉시** — Redis `CACHES['default']['OPTIONS']`에 `IGNORE_EXCEPTIONS=True`(django-redis) 또는 동등 처리 + CB 상태 로컬 폴백. 단일 장애점 완화.
3. **🔴 높음** — `views_search.py`에 stale 캐시 폴백 + CB 도입 (사용자 직격 경로).
4. **🟡 높음** — `regulatory_service.py:515` 모델명 `gemini-2.0-flash-exp`→`gemini-2.5-flash`, `keyword_generator_v2.py` sync 버전 추가(Bug #25 회피).
5. **🟡 중간** — FMP 분당 300 슬라이딩 윈도우 카운터 도입(멀티 워커 환경), Gemini Celery 경로 timeout 추가, 429 미처리 경로에 `keyword_service.py`/`llm_service.py` 패턴 확산.
6. **🟡 중간** — SEC EDGAR 429/`Retry-After` 준수 + Session 재사용.
7. **🟢 낮음** — `client.py:161` 선형 backoff 라벨-구현 정합, `news_deep_analyzer.py:251` 데드 except 절 정리.

---

*본 보고서는 정적 분석 기반 읽기 전용 감사로, 런타임 동작(특히 SDK 미스매치 2건)은 실제 실행 검증이 필요하다.*
