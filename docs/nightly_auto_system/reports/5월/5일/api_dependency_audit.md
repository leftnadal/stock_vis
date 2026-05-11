# 외부 API 의존성 감사 보고서

**작성일**: 2026-05-05
**범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis, Finnhub, Marketaux
**감사 모드**: 읽기 전용 (코드 수정 없음)
**조사 파일 수**: FMP 30개 + Gemini 36개 + 기타 의존성 약 15개

---

## 1. 의존성 매트릭스 (서비스별 외부 API × Fallback 유무)

| 의존성 | Retry | Cache | Fallback | Timeout | Rate Limit 인지 | 장애 시 영향 | 종합 위험도 |
|--------|:-----:|:-----:|:--------:|:-------:|:--------------:|:------------|:----------:|
| **FMP** (`api_request/providers/fmp/`) | ✓ (3회 지수백오프) | 부분 (serverless만) | ✗ (호출자 위임) | 30s 고정 | ✓ 0.2초 delay (300/min) | 주가/재무 수집 전면 중단 | **HIGH** |
| **FMP** (`serverless/services/fmp_client.py`) | ✗ | ✓ (1m~24h TTL) | 빈 결과 | 미명시 | 부분 인지 | Market Movers/Screener 일부 마비 | MED |
| **FMP** (`macro/services/fmp_client.py`) | ✗ | ✗ | 빈 리스트 | **미명시** | ✗ | Macro 지수 갱신 실패 | HIGH |
| **Gemini** (rag_analysis) | ✓ (지수백오프, 429만) | ✗ | 동기 폴백 (truncate) | **미명시** | ✗ | RAG 분석 중단 | HIGH |
| **Gemini** (thesis/serverless/news) | 부분 (4초 sleep) | 부분 (semantic) | 폴백 키워드/None | **미명시** | 부분 (4s 하드코딩) | 가설/뉴스 분석 중단 | HIGH |
| **Gemini** (`adaptive_llm_service.py`) | ✗ | ✗ | ✗ | 미명시 | ✗ | **레거시 SDK** Celery 비호환 | **CRITICAL** |
| **FRED** (`macro/services/fred_client.py`) | ✓ (3회 지수백오프) | ✓ (TTL 차등) | 기본값 (VIX=20 등) | 30s | ✓ RateLimiter 100/min | 거시경제 대시보드 부분 마비 | MED |
| **Neo4j** (`rag_analysis/services/neo4j_*`) | ✗ | ✓ (lazy fallback) | 빈 응답 (`_meta.source='fallback'`) | 2s 쿼리 | N/A | Chain Sight 그래프 빈 응답 (앱 살아있음) | LOW-MED |
| **SEC EDGAR** (`sec_pipeline/collector.py`) | ✓ (Celery 3~5회) | ✗ | edgartools 폴백 | 30s/60s | ✓ 0.12s sleep | 10-K 수집 중단 → 공급망 분석 불가 | HIGH |
| **Redis** (cache) | ✗ | N/A | Django 기본 캐시 (locmem) | N/A | N/A | 캐시 미스 → API 호출 폭주 | HIGH |
| **Redis** (Celery broker) | ✗ | N/A | ✗ | N/A | N/A | 모든 비동기 태스크 중단 | **CRITICAL** |
| **Finnhub** (`news/providers/finnhub.py`) | ✗ | ✗ | Marketaux 폴백 | **미명시** | ✓ 1.0s delay | 뉴스 부분 누락 | MED |
| **Marketaux** (`news/providers/marketaux.py`) | ✗ | ✗ | ✗ (최후 선택) | **미명시** | ✓ 10s delay | Finnhub 동시 실패 시 뉴스 전면 마비 | HIGH |
| **Alpha Vantage** | (코드 잔존) | - | - | - | 12s delay 명시 | 사용처 축소됨 | LOW |

> **CRITICAL 2개**: `adaptive_llm_service.py` 레거시 비동기 SDK, Redis broker 단일 장애점.

---

## 2. FMP 상세

### 2.1 클라이언트 핵심 (`api_request/providers/fmp/client.py`)

| 항목 | 값 / 위치 |
|------|----------|
| HTTP 라이브러리 | `requests` (라인 11) |
| Timeout | 30초 (라인 121) |
| Retry | 지수 백오프, max_retries=3 (라인 58, 119-159) — 첫 실패 후 2/4/6초 |
| Rate Limit | request_delay=0.2초, daily_calls=10,000 (라인 57, 70-71) |
| 상태코드 | 401→`FMPAuthError`, **402→`FMPPremiumError`** (라인 35-37, 128-129), 403→`FMPAuthError`, **429→`FMPRateLimitError`** (라인 132-133) |
| 즉시 전파 (재시도 X) | FMPPremiumError, FMPAuthError, FMPRateLimitError (라인 149-150) |

### 2.2 호출 지점 매핑 (주요 28곳)

| 파일:라인 | 메서드 | try/except | retry | fallback | 캐시 |
|----------|--------|:----------:|:-----:|:--------:|:----:|
| `api_request/providers/fmp/provider.py:59-94` | get_quote | ✓ | ✗ | ✗ | ✗ |
| `api_request/providers/fmp/provider.py:218-262` | get_balance_sheet | ✓ (PremiumError) | ✗ | ✗ | ✗ |
| `api_request/providers/fmp/provider.py:264-308` | get_income_statement | ✓ (PremiumError) | ✗ | ✗ | ✗ |
| `api_request/providers/fmp/provider.py:310-354` | get_cash_flow | ✓ (PremiumError) | ✗ | ✗ | ✗ |
| `api_request/stock_service.py:58-69` | get_quote (wrapper) | ✗ | ✗ | ✓ (call_with_fallback) | ✗ |
| `api_request/stock_service.py:185-268` | update_stock_data | ✓ | ✗ | ✗ (기존 DB 사용) | cache.delete |
| `api_request/stock_service.py:321-377` | update_financial_statements | ✓ | ✗ | **✗** | ✗ |
| `stocks/tasks.py:147-150, 216` | sync_sp500_financials | ✓ | ✓ (max_retries=3) | ✗ | cache.delete |
| `stocks/tasks.py:272-339` | update_stock_with_provider | ✓ | ✓ (countdown=60) | ✗ | cache.delete |
| `stocks/tasks.py:509-536` | update_financials_with_provider | ✓ | ✗ (rate_limit='6/m') | ✗ | ✗ |
| `serverless/services/fmp_client.py:94-267` | (Market Movers 등 6종) | ✓ | ✗ | ✗ | ✓ (5m~24h) |
| `macro/services/fmp_client.py:108-164` | get_quote / batch_quotes | ✓ | ✗ | 빈 리스트 | ✗ |
| `news/providers/fmp.py:50-140` | fetch_company_news 외 | ✓ | ✗ | ✓ ([] 반환) | ✗ |
| `serverless/services/market_breadth_service.py:70-144` | calculate_daily_breadth | ✓ | ✗ | ✗ | ✗ |
| `thesis/tasks/eod_pipeline.py:25-81` | _fetch_fmp_value | ✓ (PremiumError 73L) | ✗ | ✓ (None 반환) | ✗ |

### 2.3 위험 요소

#### HIGH

- **H-FMP-1**: `api_request/providers/fmp/client.py:132-133` — **429를 즉시 raise**. retry 루프에서 라인 149에서 re-raise 되어 백오프 적용 안 됨. Rate limit 폭증 시 후속 작업 동시 실패.
- **H-FMP-2**: Celery worker가 `update_stock_with_provider`를 동시 실행하면 client.request_delay(0.2초)만으로 300 calls/min을 초과. `rate_limit='6/m'`은 `update_financials_with_provider`(L509)에만 적용됨. 다른 태스크는 동시성 제어 없음.
- **H-FMP-3**: `api_request/stock_service.py:321-377` (update_financial_statements) — FMPPremiumError/FMPRateLimitError 발생 시 **fallback provider 부재**. DB 우회 경로 없음.
- **H-FMP-4**: `stocks/tasks.py:177-180`, `230-233` — `apply_async()` 호출이 try-except 미보호. 심볼 조회 실패 시 전체 배치가 스케줄되지 않음.

#### MEDIUM

- **M-FMP-1**: 클라이언트 인스턴스 3개 분산 — `api_request/providers/fmp/client.py`(requests) / `serverless/services/fmp_client.py`(httpx) / `macro/services/fmp_client.py`(requests). Timeout/retry 정책 불일치.
- **M-FMP-2**: `macro/services/fmp_client.py:108` — **timeout 명시 없음** (기본값 None = 무한 대기 가능).
- **M-FMP-3**: `macro/services/fmp_client.py:146-164` — 콤마 batch quote가 402 → 빈 리스트. 개별 호출 fallback 없으면 macro 갱신 실패.
- **M-FMP-4**: 캐시 무효화 부분적 — `stocks/tasks.py:330-332`는 quote/overview/chart만, 재무제표 캐시 키는 누락.

#### LOW

- **L-FMP-1**: `X-RateLimit-Remaining` 헤더 미파싱. proactive 감지 불가.
- **L-FMP-2**: `api_request/providers/fmp/client.py:70` — daily_calls 카운터가 **프로세스 로컬**, 멀티 워커 환경에서 부정확.
- **L-FMP-3**: 실패 심볼 블랙리스트 부재. CUSIP Mapper 등에서 동일 심볼 반복 402 호출.

### 2.4 Premium(402) / "." 심볼 처리 현황

| 위치 | 처리 |
|------|------|
| `stocks/tasks.py:147-150, 216` | `[s for s in all_symbols if '.' not in s]` 사전 필터링 ✓ |
| `api_request/providers/fmp/provider.py:247, 293, 339` | try/except로 PREMIUM_ONLY 응답 변환 ✓ |
| `thesis/tasks/eod_pipeline.py:73-75` | FMPPremiumError 캐치 후 None 반환 ✓ |
| **누락** | `serverless/services/fmp_client.py`, `macro/services/fmp_client.py`는 PremiumError 패턴 미적용 |

---

## 3. Gemini 상세

### 3.1 호출 지점 매핑 (주요 19곳)

| 파일:라인 | 모델 | sync? | 429 처리 | timeout | JSON 검증 |
|----------|------|:-----:|:-------:|:-------:|:--------:|
| `rag_analysis/services/llm_service.py:62, 182` | gemini-2.5-flash | ✗ (`aio.models.generate_content_stream`) | ✓ 지수백오프 (217-232) | ✗ | structured |
| `rag_analysis/services/adaptive_llm_service.py:90-91` | (미명시) | ✗ (**레거시 `genai.configure`**) | ✗ | ✗ | ✗ |
| `rag_analysis/services/context_compressor.py:51, 88-108` | gemini-2.5-flash | ✓ + asyncio.gather(max=5) | ✗ | ✗ | ✓ (152-154 fallback truncate) |
| `rag_analysis/services/entity_extractor.py:64, 87` | gemini-2.5-flash | ✓ | ✗ | ✗ | ✓ (107-113 fallback) |
| `thesis/services/prompt_builder.py:542, 562` | gemini-2.5-flash | ✓ | ✗ | ✗ | ✓ structured (574-576) |
| `thesis/services/indicator_matcher.py:197, 226` | gemini-2.5-flash | ✓ | ✗ | ✗ | regex 추출 (237-241) |
| `thesis/services/thesis_builder.py:56, 114` | gemini-2.5-flash | ✓ (Celery) | ✗ | ✗ | structured |
| `thesis/views/conversation_views.py:228, 270` | gemini-2.5-flash | ✓ | ✗ | ✗ | structured |
| `serverless/services/keyword_generator.py:60, 115` | gemini-2.5-flash | ✗ (asyncio batch 20) | ✗ | ✗ | ✓ (semantic cache 7일) |
| `serverless/services/keyword_generator_v2.py:64` | gemini-2.5-flash | ✓ | ✗ | ✗ | structured |
| `serverless/services/llm_relation_extractor.py:153, 161, 221-226` | gemini-2.5-flash | ✓ | ✗ | ✗ | ExtractionResult(error) |
| `serverless/services/relationship_keyword_enricher.py:54, 91` | gemini-2.5-flash | ✓ + sleep(4.0) | 4s 고정 | ✗ | ✗ |
| `serverless/services/regulatory_service.py:88` | gemini-2.5-flash | ✓ (lazy) | ✗ | ✗ | structured |
| `news/services/news_deep_analyzer.py:39, 53, 98, 125` | gemini-2.5-flash | ✓ + sleep(4) | 4s 고정 | **✗** | ✓ (146 None) |
| `news/services/keyword_extractor.py:61, 152-154` | gemini-2.5-flash | ✓ | ✗ | ✗ | ✓ (FALLBACK_KEYWORDS) |
| `sec_pipeline/intelligence.py:155, 162` | gemini-2.5-flash | ✓ | ✗ | **✗** | structured |
| `sec_pipeline/extractor.py:31, 68` | gemini-2.5-flash | ✓ (lazy) | ✗ | ✗ | structured |
| `validation/services/llm_peer_filter.py:72, 79, 86` | gemini-2.5-flash | ✓ | ✗ | ✗ | json.loads + {error} |
| `stocks/services/korean_overview_service.py:35, 139` | gemini-2.5-flash | ✓ + sleep(4) | 4s 고정 | ✗ | structured |

### 3.2 위험 요소

#### CRITICAL

- **C-GEM-1**: `rag_analysis/services/adaptive_llm_service.py:90-91` — **레거시 `google.generativeai` SDK + `generate_content_async()`** 사용. CLAUDE.md `common-bugs.md` Bug #8(Celery에서 async LLM 호출 금지)에 정면 위반. Celery worker에서 호출 시 즉시 실패 가능.

#### HIGH

- **H-GEM-1**: **모든 19개 Gemini 호출 지점에 timeout 미설정**. 응답 없는 API에서 무한 대기 위험. 특히 `news_deep_analyzer.py:125`, `sec_pipeline/intelligence.py:162`는 긴 컨텍스트 → 응답 시간 길어 위험 가중.
- **H-GEM-2**: `rag_analysis/services/llm_service.py:182` — `aio.models.generate_content_stream()` 비동기 스트리밍 호출. Django 동기 뷰/Celery에서 호출 시 asyncio 이벤트 루프 부재로 중단 위험.
- **H-GEM-3**: 19개 중 **단 1개(llm_service.py:217-232)만 429 retry 구현**. 나머지는 429 발생 시 즉시 raise → 일시적 quota 초과로 RAG/뉴스/가설 파이프라인 동시 실패 가능.

#### MEDIUM

- **M-GEM-1**: `llm_service.py:217` — `if 'rate' in error_str or '429':` 문자열 매칭. SDK 메시지 형식 변경 시 미감지. `google.genai.errors.*` 정규 클래스 사용 권장.
- **M-GEM-2**: Rate Limit 정책 일관성 없음 — 4초 고정 sleep(3개 파일) vs 동적 백오프(1개) vs 무처리(15개).
- **M-GEM-3**: 공통 클라이언트 모듈 부재 — 19곳에서 `genai.Client(api_key=...)` 중복 초기화. API 키 노출/누락 위험.
- **M-GEM-4**: `entity_extractor.py:115-134` 마크다운 제거 로직이 `\`\`\`json...\`\`\`` 외 형식 미처리. Gemini 응답 형식 변경 시 파싱 실패.
- **M-GEM-5**: `llm_relation_extractor.py:161` 캐시(1시간) 유효성 검증 없음. 동일 source_id 반복 호출 시 stale 결과 사용.

#### LOW

- **L-GEM-1**: `relationship_keyword_enricher.py:54` 등 `time.sleep(4.0)` 하드코딩. 상수화 필요.
- **L-GEM-2**: `context_compressor.py:84` API 키 없을 때 자동 fallback. 무지각적 성능 저하.

### 3.3 응답 파싱 패턴 분석

- **표준 추출**: 모든 파일이 `response.text` 사용. legacy `candidates[0].content.parts[0].text` 없음. ✓
- **Structured Output 도입**: prompt_builder, thesis_builder, entity_extractor, conversation_views, sec_pipeline 등 다수에서 `response_mime_type="application/json"` + `response_schema` 사용. 환각 방지에 효과적.
- **Pydantic 검증**: 없음. 수동 dict 검증 또는 try/except.
- **공통 폴백 전략**: `_fallback_extraction()`, `_fallback_compress()`, `FALLBACK_KEYWORDS` 등 명명 일관됨.

---

## 4. 기타 의존성 상세

### 4.1 FRED API (`macro/services/fred_client.py`)

| 항목 | 값 |
|------|-----|
| Rate Limit | RateLimiter("fred"), 100/min (Free 120 × 0.83) |
| Timeout | 30초 (line 103) |
| Retry | 3회 지수백오프 (2/4/6s), `_make_request()` line 75-155 |
| Permanent 에러 | 401/403/404 즉시 raise (line 106-111) |
| Transient 에러 | 500/502/503/504 재시도 (line 114-128) |
| Cache | macro_service.py line 51-73, TTL 차등 (60s~604800s) |
| Fallback | 캐시 미스 시 기본값 (VIX=20, spread=1.0) |

**위험**: MEDIUM — retry/cache는 잘 구현되었으나 RateLimiter `acquire()`에 timeout 미설정 (차단형).

### 4.2 Neo4j

| 항목 | 위치 |
|------|------|
| Driver | `rag_analysis/services/neo4j_driver.py:19-67` (lazy init) |
| Pool | max_connection_lifetime=3600s, pool_size=50, acquisition_timeout=60s |
| Lazy Init | 첫 호출 시 시도, 실패 시 None 반환 + 재연결 차단 (line 36-38) |
| 쿼리 timeout | 2초 (line 30, neo4j_service.py) |
| Fallback | `_empty_relationships()` + `_meta.source='fallback'` 마킹 |
| Sync 안전성 | `chainsight/services/neo4j_sync.py:22-54` 개별 관계 실패 무시, dirty flag 유지 |
| Fork Safety | `config/celery.py:83-114` 워커 fork 후 driver 참조 None 처리 (close 호출 X, SIGSEGV 방지) |
| Queue 격리 | celery.py:37-55, neo4j 큐 분리 + macOS solo pool |

**위험**: LOW-MED — graceful degradation 우수. Chain Sight는 빈 응답으로 우회, PG 데이터는 유지.

### 4.3 SEC EDGAR (`sec_pipeline/collector.py`)

| 항목 | 값 |
|------|-----|
| Rate Limit | 0.12s sleep (10 req/sec, line 151) |
| User-Agent | 필수, line 28-31 명시 |
| Timeout | 30s (metadata, line 85-87), 60s (HTML, line 154-155) |
| Retry | Celery `tasks.py:22-51` — metadata 3회, HTML 5회, extract 1회, 모두 지수백오프 |
| 404 처리 | 즉시 실패 (재시도 없음) |
| **429 명시 처리** | **없음** — `raise_for_status()` 후 Celery autoretry로 위임 |
| Fallback | `tasks.py:78-85` — edgartools 라이브러리 폴백, 둘 다 실패 시 status='partial' |
| Cache | 없음 (매번 신규 조회) |

**위험**: HIGH — 429 명시 처리 부재, edgartools는 선택적 의존성.

### 4.4 Redis

| 용도 | 위치 |
|------|------|
| Cache decorator | `api_request/cache/decorators.py:20-31` (TTL 정의), line 71 (키 패턴) |
| Rate Limiter | `api_request/rate_limiter.py:125-139` |
| Graceful Degradation | redis 실패 시 Django 기본 캐시 백엔드(locmem)로 폴백, line 125-139 try/except |
| Celery broker | 별도 fallback 없음 |

**위험**:
- 캐시 백엔드 다운: HIGH — 캐시 미스 → 외부 API 호출 폭주 → FMP/Gemini rate limit 연쇄 초과
- Celery broker 다운: **CRITICAL** — `task.delay()` ConnectionError, 모든 비동기 태스크(EOD, sync, RAG) 중단

### 4.5 Finnhub / Marketaux

| 항목 | Finnhub | Marketaux |
|------|---------|-----------|
| 위치 | `news/providers/finnhub.py` | `news/providers/marketaux.py` |
| Rate Limit | request_delay=1.0s (60/min), line 54-60 | request_delay=10s, line 56-62 |
| Retry | ✗ | ✗ |
| Timeout | **미명시** | **미명시** |
| Fallback | Marketaux (config/settings.py:110-111) | **없음 (최후 선택)** |

**위험**: 둘 다 동시 실패 시 뉴스 기능 전면 마비. timeout 미설정으로 무한 대기 가능.

---

## 5. Circuit Breaker 도입 후보

장애 시 시스템 영향이 크고 **재시도 폭증으로 인한 연쇄 장애** 가능성이 있는 호출 지점.

### 5.1 1순위 (CRITICAL — 즉시 도입 필요)

| 후보 | 이유 | 권장 패턴 |
|------|------|----------|
| **FMP `client.py` 429 응답** (`api_request/providers/fmp/client.py:132-133`) | Rate limit 초과 시 모든 Celery 워커가 동시에 retry → 폭증. 일정 실패율 초과 시 차단 후 일정 시간 후 재개. | open/half-open/closed 상태머신, 60초 단위 |
| **Gemini 호출 전반** (timeout 부재 19곳) | 429/timeout 시 RAG·thesis·news 전체 파이프라인 동시 호출 → quota 즉시 소진. | 글로벌 Gemini circuit breaker (단일 인스턴스) |
| **Redis Celery broker** | broker 다운 시 모든 task.delay() 실패. 재시도 폭증으로 worker fork 압박. | 외부 헬스체크 + 빠른 실패 |

### 5.2 2순위 (HIGH)

| 후보 | 이유 |
|------|------|
| **SEC EDGAR collector** | 10-K 수집 실패율이 30% 넘으면 일시 차단 후 재개. 429 명시 처리 부재 보완. |
| **Marketaux `news/providers/marketaux.py`** | Finnhub 폴백 후 최후 선택지. 실패 시 즉시 차단하고 캐시된 뉴스만 노출. |
| **`adaptive_llm_service.py`** | 레거시 SDK + Celery 비호환. 호출 자체를 차단(circuit always open) → CRITICAL 정상화 전 sync 마이그레이션 강제. |
| **`macro/services/fmp_client.py`** | timeout 미설정 + retry 부재. 호출 풀 자체가 hang 상태로 전이. |

### 5.3 3순위 (MED)

| 후보 | 이유 |
|------|------|
| **FRED `_make_request`** | 이미 retry 잘 구현됨. acquire timeout만 추가하면 충분. |
| **Finnhub** | Marketaux 폴백 동작 중이면 큰 문제 없음. 모니터링 우선. |
| **Neo4j 쿼리** | graceful degradation 우수 (빈 응답). 빈 응답 누적률만 모니터링. |

### 5.4 권장 구현 전략

1. **공통 라이브러리**: `pybreaker` 또는 자체 Redis 기반 카운터.
2. **상태 저장소**: Redis (멀티 워커 공유).
3. **임계치 (예시)**: 실패율 50%/30초 → open, 60초 후 half-open 1회 시도.
4. **메트릭**: `circuit_breaker_state{provider="fmp"}` Prometheus 노출.
5. **단일 책임**: provider별 1개 인스턴스, 호출 site에서 데코레이터로 적용.

---

## 6. 즉시 조치 권장 사항 (Top 10)

| 순위 | 식별자 | 조치 | 영향 범위 |
|:----:|--------|------|----------|
| 1 | C-GEM-1 | `adaptive_llm_service.py` 신 SDK 동기 API로 마이그레이션 | RAG 파이프라인 |
| 2 | H-GEM-1 | 모든 Gemini 호출에 `request_options={"timeout": 30}` 추가 (19곳) | 전체 LLM |
| 3 | H-FMP-1 | FMP client 429를 retry 가능 에러로 분류 (지수 백오프) | FMP 안정성 |
| 4 | C-Redis | Celery broker 헬스체크 + alerting (Sentry/Slack) | 모든 비동기 |
| 5 | H-FMP-2 | 모든 FMP Celery 태스크에 `rate_limit` 명시 또는 동시성 제한 | 주가/재무 sync |
| 6 | H-FMP-3 | `update_financial_statements`에 graceful skip + 다음 주기 retry | 재무 갱신 |
| 7 | H-GEM-3 | Gemini 429 처리 공통 데코레이터 작성 + 18개 호출에 적용 | 전체 LLM |
| 8 | H-Marketaux | Finnhub/Marketaux에 `timeout=30s` 추가 | 뉴스 수집 |
| 9 | H-SEC | SEC EDGAR 429 명시 처리 + 응답 헤더 기반 sleep | 10-K 수집 |
| 10 | M-FMP-1 | FMP 클라이언트 3개 → 1개 통합 | 유지보수성 |

---

## 7. 통계 요약

- **조사 파일**: FMP 30개 / Gemini 36개 / 기타 약 15개 (총 ~80개)
- **CRITICAL 위험**: 2건 (Celery 비동기 LLM, Redis broker)
- **HIGH 위험**: 12건
- **MEDIUM 위험**: 14건
- **LOW 위험**: 7건
- **timeout 미설정 호출 지점**: 약 25개 (FMP 1개, Gemini 19개, Finnhub/Marketaux 2개, macro FMP 1개 등)
- **fallback 없는 외부 호출**: 약 8개 (Marketaux, update_financial_statements, adaptive_llm_service 등)
- **단일 통합 클라이언트로 통합 가능한 중복 인스턴스**: 22개 (Gemini 19, FMP 3)

---

**작성자**: Claude Code (read-only audit)
**참고**: `sub_claude_md/common-bugs.md` Bug #8/14/15/19/23, `CLAUDE.md` Harness Protocol
