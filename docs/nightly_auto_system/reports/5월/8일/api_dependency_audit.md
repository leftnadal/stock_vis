# 외부 API 의존성 감사 보고서

**작성일**: 2026-05-08
**범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis (+ Alpha Vantage·Finnhub·MarketAux 일부)
**조사 대상**: FMP 23개 + Gemini 29개 + 기타 의존성 ~20개 (총 ~70개 .py 파일)
**모드**: 읽기 전용 — 코드 수정 없음

---

## 핵심 결론 (TL;DR)

1. **FMP 클라이언트가 3개로 분산되어 있다** — `api_request/`, `serverless/`, `macro/` — 정책(retry/402/rate-limit)이 통일되어 있지 않다.
2. **Gemini 호출 중 Celery × async 위반 사례는 없다** — 버그 #8(자주 발생하는 버그)은 회피되어 있다. 다만 동기 wrapper 안에서 `asyncio.new_event_loop()`로 우회하는 패턴이 다수 있어, 향후 변경 시 회귀 위험은 존재한다.
3. **가장 위험한 단일 장애점은 Neo4j** — `is_available()` 1회 실패 후 lazy init이 영구 None이 되어 Chain Sight 전체가 빈 배열로 마비된다. retry/circuit 어느 쪽도 없다.
4. **FMP 시장 지수 호출(macro)에 retry 자체가 없다** — 5분 주기 Celery에서 일시 5xx 한 번에 그대로 실패한다.
5. **Graceful Degradation은 부분적으로만 존재** — Redis 캐시 미스는 안전하지만, FMP/Neo4j/Gemini 다운 시 fallback 데이터 소스는 거의 없다.
6. **Circuit Breaker 도입 1순위**: Neo4j → FMP `_make_request` → FRED 순.

---

## 1. 의존성 매트릭스 (서비스 × 외부 API × Fallback)

서비스별로 어떤 외부 API에 의존하고, 장애 시 어떻게 동작하는지 한 번에 보는 매트릭스.

| 서비스 도메인 | FMP | Gemini | FRED | Neo4j | SEC EDGAR | Redis | Fallback / Degradation |
|--------------|-----|--------|------|-------|-----------|-------|------------------------|
| stocks (주가/검색) | ✅ 필수 | – | – | – | – | ✅ 캐시 | DailyPrice DB → 응답 가능 (구형) |
| serverless/Market Movers | ✅ 필수 | – | – | – | – | ✅ 캐시(5분) | ❌ 없음 — 전 세션 빈 페이지 |
| serverless/Screener (Enhanced) | ✅ 필수 | ⚠️ 선택 | – | ⚠️ 부분 | – | ✅ 캐시 | ❌ — limit=N에 N회 key-metrics 호출 |
| serverless/Chain Sight | ✅ peer 보강 | ✅ relation | – | ✅ 핵심 | – | ✅ 캐시 | Neo4j 다운 → `[]` 빈 배열 (사용자: "관련 없음") |
| serverless/AI 키워드 | – | ✅ 필수 | – | – | – | ✅ 캐시 | `FALLBACK_KEYWORDS` 상수 |
| macro/거시 대시보드 | ✅ 지수 | – | ✅ 지표 | – | – | ✅ 캐시(60분) | FRED retry 3회 / FMP retry 0회 |
| news/수집·분석 | ✅ press release | ✅ 분석 | – | ⚠️ 이벤트 | – | ✅ 캐시(60분) | 분석 실패 → 중립 키워드, 수집은 빈 결과 |
| rag_analysis | – | ✅ 필수 | – | – | – | ⚠️ 부분 | `truncate` 압축 폴백, suggestion 빈 배열 |
| thesis (가설 통제실) | ✅ 지표 | ✅ 빌더/요약 | – | – | – | ✅ 캐시 | LLM 실패 → 빈 문자열 (UI 미표시) |
| validation (1차 검증) | ✅ Peer | ✅ LLM 필터 | – | – | – | ✅ 캐시 | LLM 실패 → 검증 페이지 일부 미표시 |
| sec_pipeline | – | ✅ 추출 | – | – | ✅ 필수 | – | edgartools (정규식 실패 시 자동 fallback) |
| chainsight v2 | ✅ 프로파일 | ✅ 관계 | – | ✅ 동기화 | – | ✅ 캐시 | Neo4j 미동기화 시 PG 데이터로 표시 |
| portfolio (Coach) | – | ✅ + Anthropic | – | – | – | – | LLMClient에서 1회 retry, 모델 옵션 |
| marketpulse/briefing | – | ✅ 필수 | – | – | – | – | circuit_breaker 적용됨 (유일) |

> 범례: ✅ = 핵심 사용 / ⚠️ = 부분 사용·선택 / – = 미사용

---

## 2. FMP 상세

### 2.1 클라이언트 구조 (3개 분산)

| 클라이언트 | 위치 | HTTP | retry | 402 | 429 | rate-limit | 비고 |
|-----------|------|------|-------|-----|-----|-----------|------|
| **api_request/FMPClient** | `api_request/providers/fmp/client.py:40` | requests | ✅ exponential 3회 | ✅ `FMPPremiumError` (L247/L293/L339) | ✅ retry | ✅ `request_delay=0.2`, `daily_calls` 카운터 (L104-107) | 기준 구현 |
| **serverless/FMPClient** | `serverless/services/fmp_client.py:24` | httpx | ❌ | ❌ 무시 | ⚠️ raise만 | ⚠️ 캐시(300s)로만 완화 | Market Movers 중심 |
| **macro/FMPClient** | `macro/services/fmp_client.py:19` | requests | ❌ | ❌ raise | ⚠️ raise만 | `request_delay=0.2`만 | 거시 지수 |

**문제점**: 3 클라이언트가 같은 FMP 계정/한도를 공유하지만 서로의 호출량을 모른다. `daily_calls` 카운터(api_request)는 인스턴스별이라 **Thread/Process-unsafe** — 여러 worker가 동시에 호출 시 한도 초과 가능.

### 2.2 파일별 호출 인벤토리 (요약)

| 파일 | 엔드포인트 | 빈도 | retry | 402 | rate-limit |
|------|-----------|------|-------|-----|-----------|
| `api_request/providers/fmp/provider.py` | quote, profile, key-metrics, statements, search | 사용자 + 배치 | ✅ 3회 | ✅ | ✅ |
| `api_request/stock_service.py` | provider 위임 | 사용자/배치 | 위임 | 위임 | 위임 |
| `serverless/services/fmp_client.py` | gainers/losers/most-actives, indices, sp500 | Celery 5분 | ❌ | ❌ | 캐시만 |
| `serverless/services/data_sync.py:79` | gainers/losers/most-actives | Celery 일일 | ❌ raise | ❌ | ❌ |
| `serverless/services/sector_heatmap_service.py:88-99` | gainers (sector) × 11 | Celery 일일 | ❌ | ❌ | ❌ |
| `serverless/services/market_breadth_service.py:70-78` | gainers/losers/most-actives | Celery 일일 | ❌ | ❌ | ❌ |
| `serverless/services/chain_sight_service.py` | stock-peers, company-screener | on-demand | ❌ | ❌ | 캐시(3600s) |
| `serverless/services/enhanced_screener_service.py:92+` | company-screener + key-metrics-ttm × N | on-demand | ❌ | ❌ | 캐시 |
| `macro/services/fmp_client.py:78-126` | quote(batch), sector-perf, calendar, treasury | Celery 5분 | ❌ raise | ❌ | 0.2s |
| `macro/tasks.py:80` | FMPClient 위임 | Celery 5분 | ❌ | ❌ | – |
| `news/providers/fmp.py` | news/stock, general-latest, press-releases | Celery 수집 | ❌ | ❌ | ❌ |
| `stocks/tasks.py:175+` | FMPProvider 위임 + SP500 | Celery (countdown 7s 분산) | ✅ max_retries | ✅ | 부분 |
| `thesis/tasks/eod_pipeline.py:46-151` | key-metrics-ttm, financial-growth, quote | Celery 일일 | ❌ | ✅ (L144-145) | ❌ |
| `validation/services/financial_fetcher.py` | FMP on-demand | 검증 페이지 | ❌ | ✅ | ❌ |

### 2.3 위험 지점 TOP 5 (FMP)

1. **[P0] `serverless/services/data_sync.py:79-81`** — 일시 오류에도 즉시 raise. 일일 Market Movers 동기화가 한 번에 멈춘다. 영향: 메인 대시보드.
2. **[P0] `serverless/services/sector_heatmap_service.py:88-99`** — 11개 섹터 for 루프에서 retry 없이 일부만 누락. 사용자: 섹터 히트맵에 빈 칸.
3. **[P0] `api_request/providers/fmp/client.py:110-112`** — `daily_calls`가 인스턴스 로컬 카운터. 멀티 worker에서 일일 한도 정확히 막지 못해 계정 제재/요금 위험.
4. **[P1] `serverless/services/enhanced_screener_service.py:92+`** — 사용자가 `limit=500`을 보내면 key-metrics-ttm 500회 연쇄 호출. 분당 300회 한도 즉시 위반.
5. **[P1] `macro/services/fmp_client.py:78-126`** — 402/429 구분 없이 단일 raise. DX-Y.NYB 같은 프리미엄 심볼 한 번이 거시 대시보드 전체를 막는다.

### 2.4 누적 호출량 추정

| 호출원 | 일일 호출 (대략) | 위험 |
|--------|-----------------|------|
| Market Movers (3 endpoint) | 3 | 낮음 |
| 섹터 히트맵 | 11 | 낮음 |
| 시장 너비 | 3 | 낮음 |
| 거시 지수/통화/상품 | ~30 | 중 |
| 사용자 스크리너 (on-demand) | 100~1000 | **높음** |
| 뉴스 수집 (전 종목) | 50~500 | **높음** |
| 재무제표 배치 | 500~2000 | **높음** |

10,000/day Starter Plan 한도 — 평상시는 여유, **배치 + 동시 스크리너 사용 시 위반 위험** 존재.

### 2.5 패턴 일관성 점수

- 클라이언트 통합: ❌ (3개 분산)
- 재시도 표준화: ❌ (api_request만 보유)
- 402/429 분류: ❌ (api_request만)
- 전역 rate limiter: ❌ (없음)

---

## 3. Gemini 상세

### 3.1 SDK 사용 현황

- **`google.genai`** (신 SDK): 메인 — rag_analysis, serverless, news, stocks, sec_pipeline, thesis, validation, portfolio
- **`google.generativeai`** (레거시): marketpulse/briefing, thesis 일부
- **Anthropic SDK 병용**: `rag_analysis/services/adaptive_llm_service.py`, `portfolio/llm/client.py`

공통 wrapper는 `portfolio/llm/client.py`(LLMClient: Gemini + Anthropic 통합)와 `marketpulse/briefing/client.py`(circuit_breaker 적용 — 유일)뿐. **나머지는 각자 구현**.

### 3.2 파일별 인벤토리 (요약)

| 파일 | 모델 | sync/async | retry | timeout | JSON검증 | fallback |
|------|------|-----------|-------|---------|----------|----------|
| rag_analysis/llm_service.py | 2.5-flash | async | ✅ 3회 (1/2/4s) | ❌ | ✅ JSONDecodeError | ✅ 폴백 함수 |
| rag_analysis/context_compressor.py | 2.5-flash | async | ❌ | ❌ | ❌ | ✅ truncate (전체) |
| rag_analysis/entity_extractor.py | 2.5-flash | async | ❌ | ❌ | ✅ JSON 시도 | ✅ 규칙 기반 |
| rag_analysis/adaptive_llm_service.py | 2.5-flash + claude | async | ❌ | ❌ | ❌ | ❌ |
| serverless/thesis_builder.py:344 | 2.5-flash | sync | ❌ | ❌ | ⚠️ re.search 4단계 | ✅ fallback_thesis |
| serverless/regulatory_service.py:439 | **2.0-flash-exp** ⚠️ | sync | ❌ | sleep 4s | ⚠️ re.search | ❌ |
| serverless/keyword_generator.py | 2.5-flash | async (sync wrapper, L352-387) | ✅ max=2 | ❌ | ✅ JSON | ✅ FALLBACK_KEYWORDS |
| serverless/keyword_generator_v2.py | 2.5-flash | async (sync wrapper, L383-422) | ❌ | ❌ | ✅ JSON | ❌ |
| serverless/relationship_keyword_enricher.py | 2.5-flash | sync | ❌ | CALL_DELAY=4s | ✅ JSON | ❌ |
| serverless/keyword_service.py | 2.5-flash | sync | ✅ max_retries | ❌ | ✅ JSON | ✅ FALLBACK |
| serverless/llm_relation_extractor.py | 2.5-flash | async | ❌ | ❌ | ✅ JSON | ❌ |
| serverless/csv_url_resolver.py | 2.5-flash | async | ❌ | ❌ | ❌ | ✅ 3단계 폴백 |
| thesis/tasks/summary.py:55-76 | 2.5-flash | sync | ❌ | ❌ | ❌ | ✅ 빈 문자열 |
| news/keyword_extractor.py | 2.5-flash | sync | ❌ | ❌ | ✅ JSON | ✅ FALLBACK |
| news/news_deep_analyzer.py | 2.5-flash | sync | ❌ | RPM_DELAY=4 | ✅ JSON | ❌ |
| stocks/korean_overview_service.py | 2.5-flash | sync | ❌ | RPM_DELAY=4 | ✅ JSON 모드 | ❌ |
| portfolio/llm/client.py | 2.5-flash + sonnet | sync | ✅ 1회 (rate/timeout만) | ❌ | ❌ | ❌ |
| sec_pipeline/extractor.py | 2.5-flash | sync | ❌ | ❌ | ✅ JSON 모드 | ❌ |
| marketpulse/briefing/client.py | 2.5-flash | sync | circuit_breaker | ❌ | ❌ | circuit 의존 |
| validation/services/llm_peer_filter.py | 2.5-flash | sync | ❌ | ❌ | ✅ JSON 모드 | ✅ error 키 반환 |

### 3.3 위험 지점 TOP 5 (Gemini)

1. **[P0] `serverless/services/regulatory_service.py:439`** — 모델이 **`gemini-2.0-flash-exp`** 단일 하드코딩. exp 모델은 안정성/단가/RPM이 다르며 deprecated 위험. 다른 곳은 모두 2.5-flash.
2. **[P0] `serverless/services/thesis_builder.py:341, 344`** — 응답 잘림 회피를 위해 `response_mime_type` 제거 주석. 그 결과 JSON 복구를 `re.search` 4단계로 시도 → 불완전 JSON이 DB에 저장될 수 있다.
3. **[P0] `rag_analysis/services/context_compressor.py:134`** — `gather(..., return_exceptions=True)` 후 일부 실패만으로 **전체 배치를 truncate로 fallback** → 압축률 급감, 토큰 폭증.
4. **[P1] `thesis/tasks/summary.py:55-76`** — LLM 실패 시 빈 문자열 반환 + Celery retry 없음. AISummarySection이 무음으로 사라진다.
5. **[P1] `serverless/keyword_generator*.py:383-420`** — Celery에서 매번 `loop.is_closed()` → `new_event_loop()`. 단일 worker는 안전하나 prefork 풀과의 상호작용에서 회귀 위험.

### 3.4 환각·파싱 위험

- **JSON 사일런트 폴백** 다수 — `llm_service.py:302-308` (suggestions 빈 배열), `thesis_builder.py:472-490` (괄호 자동 보정으로 부분 JSON 저장), `keyword_extractor.py` (중립 키워드).
- **`finish_reason` 검증 없음** — 모든 파일에서 누락. MAX_TOKENS로 잘린 응답을 정상으로 인식.
- **Pydantic 스키마 검증 없음** — 대부분 TypedDict 또는 dict 그대로 사용.
- 사용자 메모리 `feedback_llm_indicator_hallucination`(LLM 지표 환각 방지)은 `thesis/services/indicator_matcher.py`(규칙 기반)로 대응되어 있다.

### 3.5 Celery × async 위반 (버그 #8) 검사

**위반 사례 없음**. 모든 Celery task는 동기 API 사용 또는 `asyncio.run_until_complete()`로 명시적 wrapping. 다만 `keyword_generator*.py`의 매번 `new_event_loop()` 패턴은 **회귀 시 위험**하므로 회귀 테스트가 필요하다.

### 3.6 RPM(15 RPM Free) 보호 패턴

- `time.sleep(4)` / `RPM_DELAY=4` / `CALL_DELAY=4.0` — 5곳에서 분산 적용 (regulatory, news_deep_analyzer, relationship_keyword_enricher, korean_overview, news/keyword_extractor)
- **전역 rate limiter 없음** — 동시 호출 시 sleep만으로는 부족할 수 있음

---

## 4. 기타 의존성

### 4.1 요약 테이블

| 의존성 | 핵심 위치 | 에러처리 | retry | timeout | fallback | 장애 영향 |
|--------|----------|---------|-------|---------|----------|----------|
| **FRED API** | `macro/services/fred_client.py:75-155` | ✅ 401/403/404 vs 5xx 분리 | ✅ 3회 (2/4/6s) | 30s | ❌ | 거시 대시보드 일부 미표시 |
| **Neo4j** | `serverless/services/neo4j_chain_sight_service.py:98-525`, `chainsight/services/neo4j_sync.py:21-91` | ⚠️ try-except → `[]`/`False` | ❌ | acquisition 60s | ✅ `is_available()` 사전 | **Chain Sight 전체 마비** |
| **SEC EDGAR** | `sec_pipeline/collector.py:72-159` | ✅ 0.12s sleep + UA | ❌ | 30~60s | ✅ edgartools 자동 | 10-K 추출 일시 중단 |
| **Redis (캐시)** | `django.core.cache` 전역 | ✅ 자동 우회 | ❌ | 연결 의존 | ✅ DB 직조회 | 성능 저하만 |
| **Redis (Broker)** | `config/celery.py` | ❌ 없음 | ❌ | 기본값 | ❌ | 스케줄 태스크 큐잉 중단 |

### 4.2 의존성별 상세

**FRED (`macro/services/fred_client.py:75-155`)**
- 영구 에러(401/403/404)와 일시 에러(5xx) 분리, 2/4/6초 backoff 3회 — **이 프로젝트에서 가장 잘 짜인 외부 호출**.
- 그러나 `get_inflation_data()`(L299-321)는 13개 시리즈 순차 호출 — 누적 지연 + rate_limiter 대기.
- Fallback 부재로 모든 시리즈 실패 시 대시보드가 빈다.

**Neo4j (`neo4j_chain_sight_service.py`, `chainsight/services/neo4j_sync.py`)**
- 가장 위험한 단일 장애점.
- `get_neo4j_driver()` (`neo4j_driver.py:19-67`) 1회 실패 → `_driver = None` → 이후 호출 모두 빈 배열.
- 연결 풀: `max_connection_pool_size=50`, `connection_acquisition_timeout=60s`.
- 쿼리 retry / timeout 없음 — 일시적 네트워크 끊김도 영구 비활성으로 이어진다.
- **Cascading**: Neo4j 다운 → `chainsight/tasks/sync_tasks.py:98-110` 실패 → PG/Neo4j 데이터 비동기 누적.

**SEC EDGAR (`sec_pipeline/collector.py:72-159`)**
- 0.12초 sleep로 10 req/sec 정책 준수, `User-Agent` 설정, CIK 캐시.
- 정규식 추출 실패 시 edgartools(`L189-215`)로 자동 fallback — 보강된 패턴.
- 단점: 429/520 시 retry 없음, 대량 배치는 sleep만으로 부족.

**Redis 캐시**
- Django 캐시 인터페이스가 graceful: 캐시 미스 → DB 직접 조회. 안전.
- 단, `macro/tasks.py:47-53`처럼 `cache.delete_many` 실패도 무시되므로 구형 데이터가 노출될 가능성은 있음.

**Redis Broker**
- 다운 시 Celery beat 스케줄 큐잉 중단 → 5분 주기 시장 지수, 1시간 거시 갱신 정지.
- HA 구성 없음 (단일 인스턴스).

### 4.3 기타 (Alpha Vantage / Finnhub / MarketAux)

- `users/utils.py`, `news/providers/*` 등에서 부분 사용으로 추정. 본 감사 범위에서 핵심 의존성은 아님.
- Alpha Vantage는 5 calls/분 한도 — 12초 sleep 정책(CLAUDE.md)이 외부 정책 그대로 강제되어 있는지 별도 검증 필요.

---

## 5. Circuit Breaker 후보

| 우선순위 | 의존성 | 위치 | 영향 범위 | 도입 사유 |
|---------|--------|------|----------|----------|
| **P0 (필수)** | Neo4j | `serverless/services/neo4j_chain_sight_service.py:336-398`(`get_related_stocks`) 등 모든 공개 메서드 | Chain Sight 전체 | lazy init 1회 실패 → 영구 None. circuit이 명시적으로 상태를 관리해야 복구 가능 |
| **P0 (필수)** | FMP | `macro/services/fmp_client.py:78-126` (`_make_request`) | 거시 대시보드, 5분 주기 | retry 자체가 없음. 일시 5xx에 그대로 실패 |
| **P0 (필수)** | FMP | `serverless/services/fmp_client.py:51-92`, `data_sync.py:79`, `sector_heatmap_service.py:88-99`, `market_breadth_service.py:70-78` | Market Movers / 섹터 / 너비 — 메인 대시보드 | 단일 raise 패턴이 일일 동기화를 한 번에 멈춘다 |
| **P1 (권장)** | FMP | `serverless/services/enhanced_screener_service.py:92+` | 분당 300회 한도 위반 위험 | 사용자 입력에 비례한 N회 호출에 폭주 차단 필요 |
| **P1 (권장)** | Gemini | `serverless/services/regulatory_service.py:439`, `thesis_builder.py:344`, `thesis/tasks/summary.py:55` | 가설/규제/요약 | retry 없음 + 모델 일관성 위반 — 단일 실패가 사용자 화면에 그대로 노출 |
| **P2 (선택)** | FRED | `macro/services/fred_client.py:75-155` | 거시 지표 시간 주기 | 이미 retry 보유. circuit은 timeout 단축(30→10초)과 함께 도입 시 효과 |
| **P3 (선택)** | SEC EDGAR | `sec_pipeline/collector.py:85-159` | 10-K 비정규 호출 | edgartools fallback 존재. 우선순위 낮음 |

### 5.1 권고 (구현 가이드는 별도 PR 필요 — 본 감사는 진단까지)

1. **공통 circuit_breaker 모듈 단일화** — 현재 `marketpulse/briefing/client.py`에서만 사용 중인 패턴을 외부 호출 전반에 적용.
2. **FMP 클라이언트 통합** — 3개 분산 → 1개 (Redis 기반 토큰 버킷 + 분당/일일 한도 + 402/429 분류 + exponential backoff).
3. **Neo4j 헬스체크 + 자동 재초기화** — `is_available()`이 lazy init 영구 실패를 감지하고 주기적으로 재시도.
4. **Gemini 응답 검증 표준화** — `finish_reason` 체크 + Pydantic 스키마 + `response_mime_type='application/json'` 일관 적용.
5. **사용자 입력 의존 호출에 입력 한도** — Enhanced Screener의 `limit` 상한, RAG 컨텍스트 압축 배치 크기 등.

---

## 부록: 조사된 파일 인벤토리

- **FMP**: 23개 파일 (api_request 4, serverless 11, macro 2, news 2, stocks 4, thesis 2, validation 1, scripts 2)
- **Gemini**: 29개 파일 (rag_analysis 4, serverless 7, thesis 5, news 4, stocks 1, portfolio 1, sec_pipeline 2, marketpulse 1, validation 1, scripts 2, tests 1)
- **기타**: FRED `macro/services/fred_client.py` + `macro/tasks.py`, Neo4j `serverless/services/neo4j_chain_sight_service.py` + `serverless/services/neo4j_driver.py` + `chainsight/services/neo4j_sync.py` + `chainsight/tasks/sync_tasks.py`, SEC `sec_pipeline/collector.py`, Redis `config/celery.py` + `config/settings/*`

본 보고서는 진단까지만 다루며, 코드 변경 사항은 포함하지 않는다. 각 권고의 구현은 별도 작업 지시서로 분리할 것.
