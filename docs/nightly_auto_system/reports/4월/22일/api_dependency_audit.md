# 외부 API 의존성 감사 보고서

**작성일**: 2026-04-22
**범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis
**조사 방법**: 정적 분석 (코드 수정 없음) — 읽기 전용 감사
**근거 파일 수**: FMP 19개 호출 지점 / Gemini 23개 서비스 / 기타 4종 의존성

---

## 0. 요약 (Executive Summary)

**총평**: 외부 의존성별 에러 핸들링 품질 편차가 매우 크다. `api_request/providers/fmp/client.py`와 `rag_analysis/services/llm_service.py`처럼 모범 구현이 있는 반면, `stocks/services/fmp_fundamentals.py`, `serverless/services/llm_relation_extractor.py`, `validation/services/llm_peer_filter.py` 등은 **retry·timeout·circuit breaker·rate limit 제어가 모두 결여**되어 있다.

**Top 5 위험 지점**:

| 순위 | 지점 | 유형 | 핵심 결함 |
|------|------|------|----------|
| 1 | `api_request/rate_limiter.py` 전체 | Dead Code | 선언만 돼 있고 FMP 호출 19개 지점 모두 우회 |
| 2 | `stocks/services/fmp_fundamentals.py` 4개 메서드 | FMP | retry 없음 + 402 미분류 + silent fail (`return []`) |
| 3 | Gemini 호출 23곳 중 timeout 설정 `0개` | Gemini | Celery 태스크가 무한 hang 가능 |
| 4 | Gemini 429 (`ResourceExhausted`) 명시 처리 부재 | Gemini | Free tier 15 RPM 초과 시 전체 실패 |
| 5 | Celery worker가 FMP 전용 큐 없이 동시 호출 | FMP | 최악 `worker 8 × 300/min = 2,400/min`로 공식 한도 초과 가능 |

**Circuit Breaker 우선 도입 후보**: Gemini 전체 경로 (news/services/circuit_breaker.py 패턴 확장), FMP `stocks/services/fmp_fundamentals.py` 및 `serverless/services/fmp_client.py`.

---

## 1. 의존성 매트릭스

서비스(사용자 기능) × 외부 API × fallback 유무. `⚠️`는 부분 fallback (stale cache / 기본값 / 빈 응답), `✅`는 명확한 fallback, `❌`는 fallback 없음(= 사용자 노출 장애).

| 사용자 기능 / 엔드포인트 | FMP | Gemini | FRED | Neo4j | SEC | Redis | 비고 |
|-------------------------|:---:|:------:|:----:|:-----:|:---:|:-----:|------|
| **Stocks — Quote** (`stocks/views.py:223~240`) | ⚠️ DB→FMP fallback | — | — | — | — | ✅ miss→원본 | DB 미동기화 + FMP down → 500 |
| **Stocks — Fundamentals** (`stocks/views.py:429~435`) | ❌ `return []` silent | — | — | — | — | ⚠️ 10분 TTL만 | 캐시 miss + FMP down → "데이터 없음" |
| **Stocks — Korean Overview** (`korean_overview_service.py:63`) | — | ❌ retry 없음 | — | — | — | — | Celery 배치, deferred 영향 |
| **Screener / Enhanced** (`serverless/services/enhanced_screener_service.py`) | ❌ 1차+2차 호출 모두 no retry | ❌ thesis 생성 실패 | — | — | — | ⚠️ 5분 캐시 | 캐시 miss → Screener 불가 |
| **Market Movers** (`serverless/services/fmp_client.py:117~151`) | ⚠️ 재포장 `FMPAPIError` | ❌ 키워드 생성 실패 | — | — | — | ⚠️ 5분 캐시 | 캐시 miss → fallback 키워드 표시 |
| **Chain Sight Graph** (`chainsight/api/views.py:63~135`) | — | — | — | ✅ 빈 그래프 | — | — | `center=None` 반환 |
| **Chain Sight Relations (배치)** (`serverless/services/llm_relation_extractor.py`) | — | ⚠️ 1시간 캐시 | — | ⚠️ dirty 플래그 | — | — | Celery, deferred |
| **Thesis Control — 대화형 빌더** (`thesis/views/conversation_views.py:270`, `prompt_builder.py:519,745,929`) | — | ❌ `return None`, 사용자 차단 | — | — | — | — | Critical path — fallback 없음 |
| **Thesis — Suggest** (`prompt_builder.py:929`) | — | ⚠️ fallback_start 경로 | — | — | — | — | 뉴스 기반 제안 비활성화 |
| **Thesis — Monitoring (EOD)** (`thesis/tasks/eod_pipeline.py`) | ⚠️ FMP partial | — | ⚠️ 기본값 | — | — | ✅ | 배치, deferred |
| **Macro — Market Pulse** (`macro/views.py:35~85`) | ⚠️ VIX/쿼트 | — | ⚠️ default 50 (Fear&Greed) | — | — | ✅ miss→API | 일부 필드 None |
| **Macro — Interest Rates** (`macro/views.py:98~145`) | — | — | ❌ 500 반환 | — | — | ✅ | fallback 없음 |
| **RAG 분석** (`rag_analysis/services/llm_service.py`) | — | ✅ retry 3회 + streaming | — | ✅ 드라이버 null 체크 | — | ⚠️ | 유일한 모범 Gemini 구현 |
| **News — 수집/분석** (`news/providers/fmp.py`, `news_deep_analyzer.py:125`) | ❌ `except Exception: return []` | ⚠️ `RPM_DELAY=4s`, llm_analyzed 플래그 | — | ⚠️ dirty | — | ⚠️ | News Intelligence v3 |
| **News — 심층 분석 (신호)** (`rag_analysis/signals.py:26~58`) | — | — | — | ⚠️ 드라이버 None skip | — | ⚠️ Redis down→dispatch=True | debounce 우회 허용 |
| **Validation — LLM Peer Filter** (`validation/services/llm_peer_filter.py:71~90`) | — | ❌ retry 없음 | — | — | — | — | 실패 시 `{'error': ...}` 구조 반환 |
| **SEC Pipeline** (`sec_pipeline/collector.py`, `tasks.py`) | — | ❌ `extractor.py:68` retry 없음 | — | ⚠️ sync_dirty | ✅ 3~5 retry + User-Agent | — | 배치 전용 |

**결론**:
- 사용자 동기 경로에서 **완전한 fallback**을 가진 기능은 Chain Sight Graph(빈 그래프) 1개뿐.
- 나머지는 모두 "silent fail → 빈 데이터 표시" 또는 "500 에러"로 귀결.
- 캐시(Redis)는 대부분 graceful하나 **TTL이 5~10분**으로 짧아 장기 장애에는 방어력 부족.

---

## 2. FMP 상세 (`300 calls/min Starter`)

### 2.1 요약

- **호출 지점 19개**, 3개 독립 구현(`api_request`, `serverless`, `macro`).
- 네이티브 클라이언트(`api_request/providers/fmp/client.py:119~161`)는 retry 3회 + 402/429/401 구분 + exponential backoff까지 갖춘 **모범 구현**이나, **호출자(`provider.py:88`)가 `except Exception`으로 무차별 catch**하여 정보 손실.
- `stocks/services/fmp_*.py`, `serverless/services/fmp_client.py`, `news/providers/fmp.py`는 retry 없음 + silent fail.
- `api_request/rate_limiter.py`는 FMP 키 선언(`10/min, 250/day` — 공식 `300/min, 10,000/day`와 **불일치**)돼 있지만 **호출 0건 (Dead Code)**.

### 2.2 호출 지점 전수

| 파일:라인 | 엔드포인트 | retry | 402 분류 | rate_limiter | 비고 |
|-----------|----------|:-----:|:--------:|:------------:|------|
| `api_request/providers/fmp/client.py:179` | `/stable/quote` | ✅ 3회 | ✅ | ❌ | 네이티브 |
| `api_request/providers/fmp/client.py:189` | `/stable/quote-short` | ✅ 3회 | ✅ | ❌ | 네이티브 |
| `api_request/providers/fmp/client.py:220` | `/stable/historical-price-eod/full` | ✅ 3회 | ✅ | ❌ | 네이티브 |
| `stocks/services/fmp_fundamentals.py:61` | `/stable/key-metrics` | ❌ | ❌ | ❌ | `return []` |
| `stocks/services/fmp_fundamentals.py:122` | `/stable/ratios` | ❌ | ❌ | ❌ | `return []` |
| `stocks/services/fmp_fundamentals.py:181` | `/stable/discounted-cash-flow` | ❌ | ❌ | ❌ | `return []` |
| `stocks/services/fmp_fundamentals.py:237` | `/stable/rating` | ❌ | ❌ | ❌ | `return []` |
| `stocks/services/fmp_exchange_quotes.py:96` | `/stable/quote` | ❌ | ❌ | ❌ | `return None` |
| `stocks/services/fmp_exchange_quotes.py:159` | `/stable/quote` (batch) | ❌ | ❌ | ❌ | `return []` |
| `serverless/services/fmp_client.py:117` | `/stable/biggest-gainers` | ❌ | ❌ | ❌ | `FMPAPIError` raise |
| `serverless/services/fmp_client.py:134` | `/stable/biggest-losers` | ❌ | ❌ | ❌ | `FMPAPIError` raise |
| `serverless/services/fmp_client.py:151` | `/stable/most-actives` | ❌ | ❌ | ❌ | `FMPAPIError` raise |
| `serverless/services/fmp_client.py:180` | `/stable/quote` | ❌ | ❌ | ❌ | `FMPAPIError` raise |
| `serverless/services/fmp_client.py:220` | `/stable/historical-price-eod/full` | ❌ | ❌ | ❌ | `FMPAPIError` raise |
| `serverless/services/fmp_client.py:257` | `/stable/profile` | ❌ | ❌ | ❌ | `FMPAPIError` raise |
| `serverless/services/fmp_client.py:285` | `/stable/stock-peers` | ❌ | ❌ | ❌ | `FMPAPIError` raise |
| `serverless/services/fmp_client.py:314` | `/stable/company-screener` | ❌ | ❌ | ❌ | `FMPAPIError` raise |
| `serverless/services/fmp_client.py:363` | `datahub.io/core/s-and-p-500` | ❌ | N/A | ❌ | 캐시 우선 |
| `macro/services/fmp_client.py:139` | `/stable/quote` | ❌ | ❌ | ❌ | 수동 `time.sleep(0.5)` |

### 2.3 Rate Limit 구현 현황

| 방식 | 위치 | 상태 |
|------|------|------|
| `api_request/rate_limiter.py` 선언 `fmp: 10/min, 250/day` | 모든 호출 | ❌ **Dead Code** (0건 사용), 공식 한도(`300/min, 10k/day`)와도 불일치 |
| 수동 `time.sleep(0.2)` | `providers/fmp/client.py:107` | ✅ |
| 수동 `time.sleep(0.3)` | `sp500_eod_service.py:111` | ✅ |
| 수동 `time.sleep(0.5)` | `macro/services/fmp_client.py:102` | ✅ |
| 수동 rate limit 없음 | `stocks/services/fmp_fundamentals.py`, `fmp_exchange_quotes.py` | ❌ |
| Celery 큐 격리 / `rate_limit` 데코레이터 | — | ❌ 없음 |

**리스크**: worker 8 × 평균 300/min = 최악 2,400/min → **공식 한도 초과 가능**.

### 2.4 에러 핸들링 대표 패턴

**모범** (`api_request/providers/fmp/client.py:119~161`):
```python
for attempt in range(self.max_retries):
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 402: raise FMPPremiumError
        elif resp.status_code == 429: raise FMPRateLimitError
        ...
    except (FMPPremiumError, FMPAuthError, FMPRateLimitError):
        raise  # 재시도 불가 → 즉시 전파
    except (requests.RequestException, FMPClientError) as e:
        if attempt < max_retries - 1:
            time.sleep((attempt + 1) * 2)  # 2s, 4s
```

**안티패턴** (`stocks/services/fmp_fundamentals.py:59~91`):
```python
try:
    resp = client.get(...); resp.raise_for_status()
    return resp.json()
except httpx.HTTPStatusError:  # 402 포함 → 구분 없음
    return []
except Exception:
    return []  # silent fail
```

**최악** (`news/providers/fmp.py:50~54`):
```python
try:
    raw = self.client.get_stock_news(...)
except Exception as e:
    logger.error(...)
    return []
```

### 2.5 장애 영향 상세

- **Critical Path 차단**: Quote (DB 미존재 종목), Fundamentals (10분 캐시 miss), Screener Enhanced 2차 호출 (심볼당 1회).
- **Deferred**: `stocks/tasks.py`의 sp500_financial_sync (countdown=2초로만 분산), `sp500_eod_service` (실패 심볼 skip, 자동 재보정 없음).
- **Silent Failure**: 사용자는 "데이터 없음"과 "API 장애"를 구분할 수 없음 — 대시보드 알람 없음.

### 2.6 개선 필요 지점 (우선순위)

| 순위 | 지점 | 개선안 |
|------|------|--------|
| 1 | `stocks/services/fmp_*.py` 모든 호출 | retry 2회 + 402 `FMPPremiumError` 분류 + 예외 전파 |
| 2 | `api_request/rate_limiter.py` | 실제 데코레이터 적용, 공식 한도로 값 보정 (`300/min, 10k/day`) |
| 3 | `news/providers/fmp.py` | `except Exception` 제거, 구체 예외 처리 |
| 4 | Celery queue 분리 | FMP 전용 queue `max_concurrency=1` 추가 (common-bugs #23 확장) |
| 5 | Circuit Breaker | `serverless/services/fmp_client.py`, `stocks/services/fmp_fundamentals.py`에 `circuit_breaker.py` 패턴 적용 |

---

## 3. Gemini 상세 (`2.5-flash`, Free 15 RPM / 1500 RPD)

### 3.1 요약

- **호출 지점 23개 서비스**, 동기/비동기 혼재, **timeout 설정 0건**.
- **429 (`ResourceExhausted`) 명시 처리 0건** — 모든 호출이 generic `Exception`으로 흡수.
- **Circuit Breaker 미적용**: `news/services/circuit_breaker.py`는 FMP/Alpha Vantage 전용.
- **Idempotency 부분적**: `news_deep_analyzer.llm_analyzed` 플래그, `llm_relation_extractor` 1시간 캐시만 존재.
- **모범** (`rag_analysis/services/llm_service.py`): retry 3회 + 지수 백오프 `[1,2,4]` + streaming.
- **심각**: `validation/services/llm_peer_filter.py:71~90`, `serverless/services/llm_relation_extractor.py`, `csv_url_resolver.py` — retry·timeout 모두 없음.

### 3.2 호출 지점 전수 (23개)

| 파일:라인 | 프롬프트 용도 | 동기/async | Celery | max_tokens | retry | timeout |
|-----------|-------------|:---------:|:------:|:----------:|:-----:|:-------:|
| `thesis/services/prompt_builder.py:519` | Structured JSON | 동기 | ❌ | 2000 | ❌ | ❌ |
| `thesis/services/prompt_builder.py:745` | 경량 | 동기 | ❌ | 500 | ❌ | ❌ |
| `thesis/services/prompt_builder.py:929` | Suggestion | 동기 | ❌ | 2000 | ❌ | ❌ |
| `thesis/views/conversation_views.py:270` | 뉴스→이슈 변환 | 동기 | ❌ | 1000 | ❌ | ❌ |
| `thesis/services/indicator_matcher.py` | 지표 매칭 | 동기 | ❌ | - | 최소 | ❌ |
| `serverless/services/keyword_generator.py:247` | 배치 키워드 | async | ✅ (asyncio 래퍼, Bug #8 위험) | 8000 | ❌ | ❌ |
| `serverless/services/keyword_generator_v2.py:269,304` | 배치/단일 키워드 | async | ✅ | 8000/2000 | ❌ | ❌ |
| `serverless/services/keyword_service.py:118` | 단일 키워드 | 동기 | ✅ | - | ✅ 2회 + fallback_keywords | ❌ |
| `serverless/services/thesis_builder.py` | 투자 테제 | 동기 | ✅ | - | ❌ | ❌ |
| `serverless/services/csv_url_resolver.py` | CSV URL 추정 | 동기 (naked `genai.Client`) | ❌ | - | ❌ | ❌ |
| `serverless/services/llm_relation_extractor.py` | 기업 관계 | 동기 | ✅ | - | ❌ | ❌ (1시간 캐시만) |
| `serverless/services/relationship_keyword_enricher.py` | 관계 키워드 | 동기 | ✅ | - | RPM_DELAY=4s | ❌ |
| `serverless/services/regulatory_service.py` | 규제 카테고리 | 동기 | ❌ | - | - | ❌ |
| `news/services/keyword_extractor.py` | 일일 뉴스 키워드 | 동기 | ✅ | 6000 | ✅ fallback | ❌ |
| `news/services/news_deep_analyzer.py:125` | Tier별 분석 | 동기 | ✅ | 2000~6000 | RPM_DELAY=4s | ❌ |
| `news/services/stock_insights.py` | 종목 인사이트 | 동기 | ✅ | - | ❌ | ❌ |
| `news/api/views.py` | NewsAggregator | - | ❌ | - | - | ❌ |
| `rag_analysis/services/llm_service.py` | 투자 분석 | async stream | ❌ | - | ✅ 3회 `[1,2,4]` | ❌ |
| `rag_analysis/services/adaptive_llm_service.py` | 복잡도 기반 | async stream | ❌ | - | ✅ | ❌ |
| `rag_analysis/services/entity_extractor.py:87` | 엔티티 추출 | async | ❌ | 200 | ✅ fallback_extraction | ❌ |
| `rag_analysis/services/context_compressor.py:93` | 문서 요약 | async 병렬(5) | ❌ | 100 | ✅ truncate fallback | ❌ |
| `sec_pipeline/extractor.py:68` | Track A/B 추출 | 동기 | ✅ | - | ❌ | ❌ |
| `sec_pipeline/intelligence.py` | 파이프라인 헬스 | 동기 | ❌ | - | - | ❌ |
| `stocks/services/korean_overview_service.py:63` | 한글 기업 개요 | 동기 | ✅ | - | RPM_DELAY=4s | ❌ |
| `validation/services/llm_peer_filter.py:79` | 필터 파싱 | 동기 | ❌ | - | ❌ | ❌ |

### 3.3 에러 핸들링 등급

**A급** (retry + fallback):
- `rag_analysis/services/llm_service.py` (3회 `[1,2,4]`)
- `serverless/services/keyword_service.py` (2회 + `FALLBACK_KEYWORDS`)
- `rag_analysis/services/entity_extractor.py` (fallback_extraction)
- `rag_analysis/services/context_compressor.py` (truncate fallback)

**B급** (try/except + null):
- `thesis/services/prompt_builder.py` (JSON parse error → `return None`, 호출자가 처리)
- `news/services/news_deep_analyzer.py` (timeout도 None)

**C급** (try/except만):
- `validation/services/llm_peer_filter.py` (`{'error': str(e)}` 구조로만 반환)
- `thesis/services/indicator_matcher.py`

**D급** (naked 호출):
- `serverless/services/csv_url_resolver.py`, `serverless/services/llm_relation_extractor.py` — Celery 컨텍스트에서 에러 발생 시 Celery retry에만 의존

### 3.4 특수 위험 — Celery async hang (common-bugs #8 재발 위험)

`serverless/services/keyword_generator.py:379~385`:
```python
loop = asyncio.get_event_loop()
if loop.is_closed():
    loop = asyncio.new_event_loop()
results = loop.run_until_complete(...)
```
- Celery worker의 이벤트 루프 상태가 불명확 → hang 가능.
- `keyword_generator_v2.py`도 동일 패턴.
- 규칙: "Celery에서는 **동기 API만** 사용 (`genai.Client` sync)" (CLAUDE.md). **두 파일은 async API를 Celery에서 돌리는 중** → 규칙 위반.

### 3.5 장애 영향

- **Critical (사용자 동기 차단)**: `POST /conversation/start/`, `POST /conversation/suggest/` (대화형 가설 빌더).
- **High (배치)**: Market Movers 키워드, 뉴스 심층 분석, 자동 테제 빌더 — 대시보드 fallback 키워드로 축소 동작.
- **Medium (fallback 있음)**: RAG, entity 추출, context 압축, peer 필터.

### 3.6 개선 필요 지점

| 순위 | 지점 | 개선안 |
|------|------|--------|
| 1 | 모든 Gemini 호출 | `timeout=httpx.Timeout(30.0, connect=10.0)` 일괄 부여 |
| 2 | 23개 call site | `except genai.error.ResourceExhausted` 분기 + 60초 backoff |
| 3 | Gemini Circuit Breaker | `news/services/circuit_breaker.py` 확장, 임계값 5회 연속 5xx/timeout → 5분 차단 |
| 4 | `keyword_generator*.py` | async 제거하고 동기 genai.Client로 전환 (Bug #8 방지) |
| 5 | Idempotency 토큰 | Celery LLM 호출에 `request_id` 캐시 키 추가 |

---

## 4. 기타 의존성

### 4.1 FRED API

| 파일:라인 | 역할 | 에러/Fallback |
|-----------|------|---------------|
| `macro/services/fred_client.py:99~155` | 핵심 클라이언트 | ✅ rate_limiter.acquire() + 3회 retry + 지수 백오프 (2/4/6s) + 500/502/503/504 분류 |
| `macro/services/macro_service.py:77~85` | Fear & Greed | ✅ 기본값 50 반환 |
| `macro/services/macro_service.py:143~145` | Interest Rates | ❌ `{'error': str(e)}` → view 500 |
| `macro/services/macro_service.py:319` | 파싱 실패 | ⚠️ None 반환 |
| `macro/views.py:98~145` | Interest Rates 뷰 | ❌ 500 반환 — fallback 없음 |
| `macro/tasks.py:37~44` | Celery 동기화 (6/12/18/22시) | ✅ 재시도 후 실패 시 로그만 |

**장애 시**: Market Pulse의 Fear&Greed는 중립값 표시로 graceful, Interest Rates 탭은 500 에러 노출. Inflation / Global Markets는 부분 데이터로 동작.

### 4.2 Neo4j

| 파일:라인 | 역할 | 패턴 |
|-----------|------|------|
| `rag_analysis/services/neo4j_driver.py:19~67` | Lazy Singleton + 50 pool + TTL 3600s | ✅ 연결 실패 시 None 캐시 후 재시도 안 함 |
| `config/celery.py:83~101` | Fork 안전성 | ✅ worker_process_init에서 드라이버 참조 해제 (macOS SIGSEGV 방지, Bug #25) |
| `config/celery.py:36~55` | `neo4j` queue 격리 (18개 태스크) | ✅ solo pool에서 실행 |
| `rag_analysis/services/neo4j_service.py:56~86` | Read fallback | ✅ `_empty_relationships(symbol, 'neo4j_unavailable')` |
| `rag_analysis/tasks.py:47~55` | Celery 태스크 | ✅ `driver is None` → `'skipped'` 반환 (재시도 안 함) |
| `chainsight/api/views.py:63,109` | 사용자 동기 경로 | ⚠️ 빈 그래프 (`center=None`) 반환 — 404 느낌 |
| `chainsight/tasks/neo4j_dirty_sync_tasks.py` | double write (PostgreSQL dirty 플래그) | ✅ 매주 일요일 04:30 UTC 재동기 |
| `rag_analysis/signals.py:26~58` | Redis debounce | ⚠️ Redis down → dispatch=True로 강제 진행 |

**장애 시**: 실시간 Chain Sight 그래프만 빈 데이터, PostgreSQL mirror 유지로 검색/목록은 정상. dirty 플래그로 복구 후 자동 동기.

### 4.3 SEC EDGAR

| 파일:라인 | 역할 | 준수 사항 |
|-----------|------|-----------|
| `api_request/sec_edgar_client.py:102` | User-Agent `Stock-Vis/1.0 (contact@stockvis.com)` | ✅ |
| `api_request/sec_edgar_client.py:99,118~124` | Rate limit 100ms 간격 | ✅ |
| `sec_pipeline/collector.py:83,130` | 수동 `time.sleep(0.12)` | ✅ |
| `api_request/sec_edgar_client.py:138~166` | 3회 retry + 429 시 1s 대기 | ✅ |
| `sec_pipeline/tasks.py:49~111` | Celery retry (메타 3회 60s, HTML 5회 10s) | ✅ |
| `sec_pipeline/collector.py:190~250` | `extract_sections`: regex 3단계 + edgartools fallback | ✅ |
| `sec_pipeline/validators.py` | FAIL / PARTIAL / SUCCESS 상태 분류 | ✅ |

**장애 시**: 사용자 실시간 뷰 영향 없음 (배치 전용). 수집 실패 → 다음 월 재시도. IP 차단 위험 없음.

### 4.4 Redis (캐시 + Celery broker)

| 파일:라인 | 역할 | Miss 동작 |
|-----------|------|-----------|
| `config/settings.py:414~419` | `default` cache → Redis DB 1 | ❌ 직접 연결 실패 시 Django `cache.get()` 예외 |
| `config/settings.py:398` | Celery broker → Redis DB 0 | ❌ Broker down → `delay()` 즉시 실패 |
| `config/settings.py:423~430` | WebSocket channel layer (DB 0) | ❌ 실시간 알림 중단 |
| `macro/views.py:50~85` | cache miss → 원본 서비스 호출 | ✅ graceful |
| `stocks/cache_utils.py:118~241` | `secure_cache_get/set` + `@secure_cached_api` | ✅ cache 실패 시 None 반환 |
| `rag_analysis/signals.py:29~31` | debounce 캐시 실패 | ✅ dispatch=True로 통과 (sync 누락 방지) |

**장애 시**:
- **캐시 DB 1**: 응답 지연 + 원본 재계산 (graceful).
- **Broker DB 0**: 모든 Celery 작업 발행 불가 — 배치 업데이트 전면 중단.
- **Result Backend**: `django-db`로 설정돼 있어 PostgreSQL에 저장 (broker와 별개) → 영향 없음.

---

## 5. Circuit Breaker 도입 후보

### 5.1 기존 구현 현황

`news/services/circuit_breaker.py` 존재. 적용 대상: **FMP, Alpha Vantage 뉴스 provider만**. 다른 경로에는 미적용.

### 5.2 우선 도입 후보

| 우선순위 | 대상 | 근거 | 파급 효과 |
|--------|------|------|-----------|
| **P0** | **Gemini 전체 경로** (23개 호출) | timeout 0건 + 429 처리 0건 → 장기 hang + 캐스케이딩 실패 | 대화형 가설 빌더, 뉴스 분석, 키워드 생성, RAG 모두 보호 |
| **P0** | `stocks/services/fmp_fundamentals.py` 4 메서드 | 캐시 10분 만료 후 silent fail이 사용자 Critical Path를 차단 | Fundamentals, Screener Enhanced 2차 호출 보호 |
| **P1** | `serverless/services/fmp_client.py` 9 메서드 | Market Movers, Chain Sight DNA의 5분 캐시 miss 지점 | Market Movers 페이지 보호 |
| **P1** | `serverless/services/keyword_generator.py`, `keyword_generator_v2.py` | async Celery 조합 (Bug #8 재발 위험) | keyword 배치 파이프라인 보호 |
| **P2** | `macro/services/fred_client.py` | 이미 retry 있으나 circuit breaker로 Interest Rates 뷰 500 방지 | Market Pulse 뷰 보호 |
| **P2** | `sec_pipeline/extractor.py:68` Gemini 호출 | Celery retry에만 의존, 재시도 폭주 가능 | SEC 파이프라인 재시도 비용 절감 |

### 5.3 적용 설계 권고

- **임계값**: 5회 연속 실패 (5xx, timeout, 429) → 5분 OPEN.
- **HALF_OPEN**: 1회 탐색 호출 성공 시 CLOSED 복귀.
- **Fallback 정책**:
  - Gemini: stale JSON 캐시 (1시간 연장) → 최종 fallback으로 고정 메시지/기본 키워드.
  - FMP: PostgreSQL 최신 DailyPrice/Metric 반환 + 프론트에 `stale_since` 표시.
- **관측**: Circuit state를 Redis에 기록 후 `thesis/views/monitoring_views.py` 또는 신규 `/admin/circuit-breaker-status` 엔드포인트로 노출.

### 5.4 Rate Limiter 통합 재설계 (보너스 권고)

- `api_request/rate_limiter.py`의 FMP 한도를 공식 값(`300/min, 10k/day`)으로 보정하고 **모든 FMP 클라이언트가 경유하도록 통일** (현재 3개 독립 구현 → 공통 decorator).
- Celery FMP 전용 큐 + `max_concurrency=1` 또는 `rate_limit='300/m'` 태스크 옵션 적용.
- Gemini Free 15 RPM을 Redis 기반 글로벌 카운터로 강제.

---

## 부록: 참고 버그 번호 (common-bugs.md)

- **Bug #8** — Celery async LLM 호출 금지. `keyword_generator*.py` 2 파일 규칙 위반 중.
- **Bug #23** — FMP 402 `FMPPremiumError` 즉시 실패 + `.` 심볼 제외. `stocks/services/fmp_*.py`는 이 패턴 미적용.
- **Bug #25** — Celery macOS SIGSEGV. Neo4j 드라이버 fork 안전성 이미 적용됨.

---

**감사 종료**. 총 19개 FMP 호출, 23개 Gemini 호출, 4종 기타 의존성 검토 완료. 다음 단계 권고: Circuit Breaker 도입 계획 수립 + Rate Limiter 통합 설계 → DECISIONS.md 결정 추가.
