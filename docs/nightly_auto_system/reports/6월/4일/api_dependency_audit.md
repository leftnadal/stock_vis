# 외부 API 의존성 감사 보고서

> **작성일**: 2026-06-04
> **범위**: FMP / Gemini / FRED / SEC EDGAR / Neo4j / Redis 장애 대응
> **모드**: 읽기 전용 감사 (코드 수정 없음)
> **방법**: 인프라 공유 계층 직접 정독 + 호출부 56(Gemini)·34(FMP) 파일 병렬 정밀 조사

---

## 0. 핵심 요약 (Executive Summary)

| 우선순위 | 발견 | 영향 |
|---------|------|------|
| 🔴 **P0** | **Redis 캐시가 `django.core.cache.backends.redis.RedisCache`(네이티브) + `OPTIONS` 없음** → `IGNORE_EXCEPTIONS` 미지원 | Redis 장애 시 `cache.get/set` 전부 예외 전파. **CircuitBreaker·RateLimiter·모든 캐시 의존 서비스가 동시 붕괴** |
| 🔴 **P0** | **CircuitBreaker 상태가 동일한 Redis(`cache`)에 저장** | Redis 다운 = 회복 메커니즘 자체가 다운. 장애 격리 불가능 |
| 🟠 **P1** | **Gemini 호출부 22곳 중 21곳(95%)이 CircuitBreaker 미적용**, 86%가 timeout 미설정, 91%가 명시적 429 처리 없음 | Gemini 지연/장애 시 워커 스레드 점유 + 무한 대기 위험 |
| 🟠 **P1** | **FMP 클라이언트 2종(full requests / serverless httpx) 혼재** — serverless는 402/429 미구분 | serverless 경로(serverless/, sp500, data_sync)에서 Premium/RateLimit 오분류 → CB 오작동 |
| 🟠 **P1** | **FMP 소비처 21곳 중 5곳만 CB 적용** | screener·heatmap·breadth·fundamentals 등 사용자 직격 경로 무방비 |
| 🟢 양호 | FRED·SEC EDGAR 클라이언트는 재시도+TRANSIENT 분리+429 처리 견고 | — |
| 🟢 양호 | Neo4j는 PID-lazy 드라이버 + 소비처 `GraphConnectionError` graceful 처리 | — |

**한 줄 결론**: 회복 인프라(CircuitBreaker)는 잘 설계되었으나, **(1) Redis 단일 장애점이 그 인프라를 무력화**하고, **(2) CB가 LLM/FMP 호출부에 산발적으로만 적용**되어 커버리지가 낮다. Circuit Breaker 자체보다 **Redis 캐시의 graceful degradation 부재가 최상위 리스크**다.

---

## 1. 의존성 매트릭스 (서비스 × 외부 API × fallback)

> Fallback 범례: ✅ 명시적 fallback(캐시/기본값/빈배열) · ⚠️ 부분 fallback · ❌ 예외 전파(복구 없음) · CB=CircuitBreaker 적용

| 서비스 / 모듈 | 외부 의존성 | 클라이언트 | CB | 재시도 | Fallback | 비고 |
|---|---|---|---|---|---|---|
| `stocks/services/sp500_eod_service` | FMP | serverless httpx | ✅ `fmp_sp500_eod`(th=10) | 클라 없음 | ❌ FMPAPIError raise | **EOD 전종목 동기화** — 실패 시 DailyPrice 미적재 |
| `stocks/services/sp500_service` | FMP | serverless httpx | ✅ `fmp_sp500`(th=3) | — | ✅ 빈 dict | datahub CSV 폴백 내장 |
| `stocks/services/stock_sync_service` | FMP | httpx 직접 | ❌ | ❌ | ⚠️ 부분 실패 | `raise_for_status()` 노출 |
| `stocks/services/fmp_fundamentals` | FMP | httpx 직접 | ❌ | ❌ | ✅ 빈 배열 | — |
| `stocks/services/fmp_market_movers` | FMP | httpx 직접 | ❌ | ❌ | ✅ 빈 배열 | — |
| `stocks/services/fmp_screener` | FMP | httpx 직접 | ❌ | ✅ 3회 backoff | ✅ **만료 캐시 반환**(429) | 오래된 데이터 제공 가능 |
| `stocks/services/fmp_exchange_quotes` | FMP | httpx 직접 | ❌ | ❌ | ✅ None/[] | — |
| `serverless/services/data_sync` | FMP | serverless httpx | ✅ `fmp_market_movers`(th=5) | — | ⚠️ 종목별 부분 실패 허용 | Market Movers 일배치 |
| `serverless/services/enhanced_screener_service` | FMP | serverless httpx | ❌ | ❌ | ✅ 빈 배열 | 사용자 검색 직격 |
| `serverless/services/sector_heatmap_service` | FMP | serverless httpx | ❌ | ❌ | ⚠️ 섹터별 부분 실패 | 히트맵 불완전 가능 |
| `serverless/services/market_breadth_service` | FMP | serverless httpx | ❌ | ❌ | ⚠️ **강제 중립값** | 신호 왜곡 위험 |
| `serverless/services/chain_sight_service` | FMP | serverless httpx | ❌ | ❌ | ✅ 빈 배열 | — |
| `serverless/services/cusip_mapper` | FMP | serverless httpx(lazy) | ❌ | ❌ | ✅ None(hardcode 우선) | — |
| `market_pulse/services/macro_service` | FMP+FRED | market_pulse_client(requests) | ❌ | 클라 내장 | ⚠️ error key | — |
| `market_pulse/services/news_aggregator` | FMP+MarketAux | full client(requests) | ✅ `fmp_news`,`marketaux` | — | ⚠️ provider=None 건너뜀 | — |
| `market_pulse/fetchers/fmp_weights` | FMP | requests 직접 | ✅ `fmp_etf` | — | CB 위임 | — |
| `news/providers/fmp` + `aggregator` | FMP | full client 위임 | ❌ | — | ✅ 빈 배열 | — |
| `thesis/tasks/eod_pipeline` | FMP | full client(requests) | ❌ | ❌ | ⚠️ (None,None) | — |
| `rag_analysis/services/llm_service` | Gemini | genai.Client(aio) | ✅ `gemini_rag` | ✅ 수동 backoff | ✅ 사용자 에러 메시지 | **모범 사례** |
| `rag_analysis/services/context_compressor` | Gemini | genai.Client | ✅ `gemini_rag_*` | — | ✅ `_fallback_compress` | **모범 사례** |
| `rag_analysis/services/entity_extractor` | Gemini | genai.Client | ❌ | ❌ | ✅ `_fallback_extraction` | JSONDecodeError 분리 |
| `rag_analysis/services/adaptive_llm_service` | Gemini | **구SDK** `configure`+`GenerativeModel` | ❌ | ❌ | ⚠️ | SDK 혼용 부채 |
| `market_pulse/briefing/client` | Gemini | genai.Client | ✅ `gemini` | — | ❌ CB 외 처리 없음 | 호출부에 try 없음 |
| `thesis/services/thesis_builder` | Gemini | genai.Client | ✅ `gemini_thesis` | ❌ | ✅ `_fallback_parse` | **모범 사례** |
| `thesis/services/prompt_builder`(4곳) | Gemini | genai.Client | ❌ | ❌ | ⚠️ None | timeout/429 없음 |
| `thesis/services/indicator_matcher` | Gemini | genai.Client | ❌ | ❌ | ✅ 빈 리스트 | regex 폴백 |
| `thesis/views/conversation_views` | Gemini | genai.Client | ❌ | ❌ | ✅ `_fallback_issues` | — |
| `thesis/tasks/summary` | Gemini | genai.Client | ❌ | ❌ | ✅ 빈 문자열 | — |
| `serverless/services/keyword_service` | Gemini | genai.Client | ❌ | ✅ **429 backoff** | ✅ fallback kw | LLM 중 유일 자체 429 재시도 |
| `serverless/services/keyword_generator(_v2)` | Gemini | genai.Client | ❌ | ❌ | ✅ 빈 배열 | — |
| `serverless/services/llm_relation_extractor` | Gemini | genai.Client | ❌ | ❌ | ✅ 빈 결과 | regex 복구 |
| `serverless/services/regulatory_service` | Gemini+SEC | genai.Client(lazy) | ❌ | ❌ | ✅ 빈 배열 | — |
| `serverless/services/relationship_keyword_enricher` | Gemini | genai.Client | ❌ | ❌ | ✅ 빈 배열 | regex 폴백 |
| `serverless/services/thesis_builder` | Gemini | genai.Client | ❌ | ❌ | ⚠️ 주로 전파 | — |
| `serverless/services/csv_url_resolver` | Gemini | genai.Client | ❌ | ❌ | ✅ None | — |
| `news/services/keyword_extractor` | Gemini | genai.Client | ❌ | ❌ | ✅ FALLBACK_KEYWORDS | — |
| `news/services/news_deep_analyzer` | Gemini | genai.Client | ❌ | ❌ | ✅ None(skip) | — |
| `news/services/stock_insights` | Gemini | genai.Client | ❌ | ❌ | ⚠️ **silent warning** | 불완전 응답 위험 |
| `sec_pipeline/intelligence` | Gemini | genai.Client | ❌ | ❌ | ✅ 구조화 fallback dict | — |
| `sec_pipeline/extractor` | Gemini | genai.Client | ❌ | ❌ | ✅ 빈 dict | JSONDecodeError 분리 |
| `stocks/services/korean_overview_service` | Gemini | genai.Client | ❌ | ❌ | ❌ **예외 전파** | LLM 중 최악 |
| `validation/services/llm_peer_filter` | Gemini | genai.Client | ❌ | ❌ | ✅ error dict | — |
| `chain_sight/graph/repository` + 소비처 | Neo4j | neo4j 드라이버 | n/a | n/a | ✅ `GraphConnectionError` 처리 | PID-lazy, 양호 |
| `sec_pipeline/collector` + `sec_edgar_client` | SEC EDGAR | requests Session | n/a | ✅ 429 재귀 + TRANSIENT | ✅ SECEdgarError | 양호 |
| `api_request/fred_client` | FRED | requests | n/a | ✅ TRANSIENT 분리 | ✅ 지표별 빈 dict | 양호 |
| **`config CACHES`(전역)** | **Redis** | django native RedisCache | n/a | n/a | ❌ **IGNORE_EXCEPTIONS 없음** | **전역 단일 장애점** |

---

## 2. FMP 상세

### 2.1 클라이언트 이원화 — 일관성 부채

| 항목 | full client (`providers/fmp/client.py`) | serverless client (`providers/fmp/serverless_client.py`) |
|---|---|---|
| HTTP 라이브러리 | `requests` | `httpx.Client` |
| 예외 체계 | `FMPClientError` → `FMPRateLimitError`/`FMPAuthError`/`FMPPremiumError` | `FMPAPIError` **단일** |
| **402 (Premium)** | ✅ 구분(client.py:131-134) | ❌ **구분 없음** (HTTPStatusError로 일괄) |
| **429 (RateLimit)** | ✅ 구분 + 재전파(client.py:137-138) | ❌ **구분 없음** |
| 재시도 | ✅ 3회 exponential backoff (client.py:160-165) | ❌ **없음** |
| Rate limiting | ✅ 자체 delay + 일일 카운터(client.py:103-115) | ❌ 없음(캐시에만 의존) |
| 캐시 | 없음(decorator/소비처 책임) | ✅ 메서드별 내장 |

**문제**: serverless client는 `sp500_*`, `data_sync`, `chain_sight`, `enhanced_screener`, `heatmap`, `breadth` 등 **핵심 경로 다수**가 사용한다. 여기서 402/429가 일반 `FMPAPIError`로 뭉개지면:
- CircuitBreaker가 "premium 심볼이라 영구 실패"와 "일시적 rate limit"을 구분 못 해 동일하게 카운트 → **부적절한 OPEN**.
- 공통 버그 #23(`FMPPremiumError` 즉시 실패 + `.` 심볼 제외) 정책이 serverless 경로에서는 **적용 불가**.

### 2.2 CircuitBreaker 적용 현황 (FMP)

✅ 적용(5): `sp500_service`(th=3/rec=300), `sp500_eod_service`(th=10/rec=120), `data_sync`(th=5/rec=120), `fmp_weights`(`fmp_etf`), `news_aggregator`(`fmp_news`)

❌ 미적용(사용자/배치 직격): `fmp_screener`, `sector_heatmap_service`, `market_breadth_service`, `fmp_fundamentals`, `fmp_market_movers`, `fmp_exchange_quotes`, `chain_sight_service`, `enhanced_screener_service`, `cusip_mapper`, `macro_service`, `stock_sync_service`, `eod_pipeline`

### 2.3 Rate Limit 처리

- 중앙 `rate_limiter.py`: FMP 240/min·8000/day(80% 안전마진), Redis pipeline 원자적 incr, **Redis 실패 시 Django 캐시 fallback 구비**(rate_limiter.py:135-141). 단 fallback도 결국 동일 Redis 백엔드라 실효성 의문(§4 참조).
- 그러나 **이 RateLimiter를 실제로 쓰는 FMP 경로는 거의 없음** — full client는 자체 delay, serverless는 무방비. FRED만 RateLimiter를 정식 사용.

### 2.4 FMP 장애 시 영향 큰 호출부 TOP 5

1. **`sp500_eod_service.py:137-193` (EOD 전종목 동기화)** — CB 있으나 `FMPAPIError` 시 `raise`. fallback 없음 → 실패 시 DailyPrice 미적재 → 모든 기술적 분석/EOD 대시보드 연쇄 붕괴. **영향 CRITICAL**.
2. **`data_sync.py:56-115` (Market Movers 일배치)** — CB(th=5) 적용. 종목별 부분 실패 허용이라 일부 지표(RVOL/Trend/SectorAlpha) 불완전 가능.
3. **`fmp_screener.py:152-237` (Enhanced 스크리너)** — 사용자 검색 직격, CB 없음. 429 시 **만료 캐시 반환** → 오래된 결과를 사용자에게 노출.
4. **`sector_heatmap_service.py` (섹터 히트맵)** — CB 없음, 섹터별 부분 실패 → 히트맵 누락 섹터 발생.
5. **`market_breadth_service.py` (시장 건강도)** — CB 없음, 실패 시 **강제 중립값(advancing=declining=2000)** 주입 → 시장 신호 왜곡(항상 중립).

---

## 3. Gemini 상세

### 3.1 SDK 혼용

- 대다수: 신 SDK `from google import genai` + `genai.Client(api_key=...)`.
- 예외: `rag_analysis/services/adaptive_llm_service.py:88,183` 만 **구 SDK** `genai.configure()` + `GenerativeModel`. → SDK 일관성 부채(유지보수·에러 타입 상이).

### 3.2 회복 패턴 3계층 (실측)

| 등급 | 파일 | 특징 |
|---|---|---|
| **A (모범)** | `rag_analysis/llm_service`, `rag_analysis/context_compressor`, `thesis/services/thesis_builder` | CB + fallback + (llm_service는) 수동 429 backoff까지 |
| **B (부분)** | `keyword_service` | CB 없으나 자체 429 backoff + fallback |
| **C (취약)** | 나머지 ~16곳 | CB·timeout·429 모두 없음, broad `except Exception` 후 fallback 또는 전파 |

### 3.3 공통 취약점 (22개 호출부 집계)

| 취약점 | 비율 | 심각도 |
|---|---|---|
| **429/quota 명시적 처리 없음** | 20/22 (91%) | 🔴 |
| **timeout 미설정** (`http_options`/`request_options` 없음) | 19/22 (86%) | 🔴 |
| **CircuitBreaker 미적용** | 21/22 (95%) | 🔴 |
| 재시도 로직 부재 | 20/22 (91%) | 🟠 |
| broad `except Exception` (타입 미구분) | 16/22 (73%) | 🟡 |
| JSON 파싱 try/except 미분리 | 8/22 (36%) | 🟡 |
| graceful degradation 부재(예외 전파) | 3/22 (14%) | 🟡 |

> **timeout 부재가 86%**라는 점이 가장 위험. genai 호출은 동기 블로킹이며, 응답 지연 시 **Celery 워커/요청 스레드를 무한 점유**한다(특히 solo pool macOS 환경). CB가 timeout을 대체하지 못한다(CB는 실패 횟수만 셈, 단일 호출 행에는 무력).

### 3.4 Gemini 오류처리 취약 파일 TOP 5

1. **`stocks/services/korean_overview_service.py:95-97`** — broad except 후 **즉시 raise**. fallback·재시도·429 감지 전무. LLM 호출부 중 유일하게 graceful degradation 없음.
2. **`news/services/stock_insights.py:634-635`** — 실패 시 warning 로그만, **silent failure**로 불완전 응답 제공.
3. **`thesis/services/prompt_builder.py:764-818`(call_gemini_light)** — `response.text` 직접 사용(JSON 보장 없음), timeout/429 없음.
4. **`serverless/services/thesis_builder.py:_call_llm_sync`** — try 없이 예외 전파, 응답 추출 시 AttributeError 위험.
5. **`market_pulse/briefing/client.py:60-73`** — CB(`gemini`)는 있으나 `_generate_sync` 내부 try 없음 + timeout 없음.

---

## 4. 기타 의존성

### 4.1 Redis — 🔴 최상위 단일 장애점

```python
# config/settings.py:500-505
CACHES = {
  'default': {
    'BACKEND': 'django.core.cache.backends.redis.RedisCache',  # Django 네이티브
    'LOCATION': 'redis://127.0.0.1:6379/1',
    # ← OPTIONS 없음 → IGNORE_EXCEPTIONS 불가
  }
}
```

- Django **네이티브** `RedisCache`는 `django_redis`의 `IGNORE_EXCEPTIONS` 옵션을 **지원하지 않는다**. 따라서 Redis 다운 시 `cache.get/set/incr`가 `ConnectionError`를 그대로 던진다.
- **연쇄 영향**:
  1. `CircuitBreaker`가 상태를 `cache`에 저장(circuit_breaker.py:64-81) → **Redis 다운 = CB 자체가 예외 → 장애 격리 불가**.
  2. `RateLimiter`도 `cache` 기반(rate_limiter.py) → fallback도 동일 Redis라 무력.
  3. serverless FMP client·market_movers 등 **캐시를 호출 경로에 직접 넣은 서비스 전부 즉시 실패**.
  4. Celery broker/result(`redis://...:6379/0`)·Channels layer도 Redis → **비동기/WebSocket 동시 마비**.
- **결론**: "Circuit Breaker 후보"를 논하기 전에, **Redis가 모든 회복 메커니즘의 공통 의존성**이라는 구조적 문제를 먼저 해결해야 한다.

### 4.2 FRED — 🟢 양호

`fred_client.py`: TRANSIENT(500/502/503/504) 재시도 vs Permanent(401/403/404) 즉시 raise 분리, 3회 backoff(2/4/6s), RateLimiter 정식 사용, 지표 수집 메서드는 시리즈별 try/except로 부분 실패 허용(빈 dict 반환). **개선 불필요**.

### 4.3 SEC EDGAR — 🟢 양호

`sec_edgar_client.py`: 429 시 1초 대기 후 **재귀 재시도**(sec_edgar_client.py:165-169), Timeout/RequestException → `SECEdgarError` 변환, rate limit 0.1s 준수, HTML 파싱 실패 시 regex fallback. `collector.py`도 0.12s sleep + RequestException 처리. **단, 429 재귀에 깊이 제한이 없어** 지속적 429 시 스택 증가 가능(경미).

### 4.4 Neo4j — 🟢 대체로 양호

- `repository.py`: PID 기반 lazy 드라이버(Celery prefork fork 안전, 공통 버그 #25 대응), 연결 실패→`GraphConnectionError`, 쿼리 실패→`GraphQueryError`로 변환(repository.py:164-172).
- 소비처: `chain_sight/api/views.py:522,728` 및 `watchlist_views.py` 4곳이 `GraphConnectionError`/`GraphQueryError`를 catch하여 graceful 처리. `health_check()` 제공.
- **개선점**: 재시도 없음(연결 실패 시 즉시 실패), 쓰기 태스크(`sync_tasks`, `relation_tasks`)의 GraphError 처리 여부는 본 감사 범위 밖 — 후속 점검 권장.

---

## 5. Circuit Breaker 후보 (우선순위순)

> 현 CircuitBreaker(`packages/shared/api_request/circuit_breaker.py`)는 tenacity 기반·Redis 상태저장·`get_circuit()` 레지스트리로 잘 설계됨. 문제는 **커버리지**와 **Redis 의존**이다.

### 🔴 P0 — 구조 선결 (CB 적용 이전)

1. **Redis 캐시 graceful degradation 도입**
   - `django-redis` 백엔드로 전환 후 `OPTIONS={'IGNORE_EXCEPTIONS': True}` + `DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS=True`, 또는 CB/RateLimiter 상태를 별도 in-memory + Redis 이중화.
   - **근거**: 이 조치 없이는 CB가 Redis 장애를 막지 못함(CB가 Redis에 의존).

### 🟠 P1 — Gemini (LLM은 가장 느리고 비쌈)

2. **`korean_overview_service`** — 유일하게 fallback 없이 전파. CB + fallback 최우선.
3. **`prompt_builder`(4 호출)·`indicator_matcher`·`conversation_views`** — 사용자 대화/가설 빌더 경로, CB 없음.
4. **모든 genai 호출에 timeout 표준화** — `http_options=types.HttpOptions(timeout=...)` 공통 적용(86% 미설정). CB보다 우선순위 높음(행 방지).
5. **adaptive_llm_service 구SDK → 신SDK 통일** 후 CB 적용.

### 🟠 P1 — FMP

6. **`fmp_screener`·`sector_heatmap_service`·`market_breadth_service`** — 사용자 직격 + 신호 왜곡(강제 중립값) 위험, CB 없음.
7. **serverless client에 402/429 구분 추가** — CB가 영구 실패(402)와 일시 실패(429)를 구분하도록.

### 🟢 P2 — 견고화

8. **`sp500_eod_service`** — CB는 있으나 실패 시 raise. 부분 적재 또는 전일 데이터 폴백 검토.
9. SEC EDGAR 429 재귀에 최대 재시도 횟수 도입(스택 증가 방지).

---

## 부록 A. 조사 커버리지

- **직접 정독**: `fmp/client.py`, `fmp/serverless_client.py`, `circuit_breaker.py`, `rate_limiter.py`, `cache/decorators.py`, `fred_client.py`, `sec_edgar_client.py`, `chain_sight/graph/repository.py`, `config/settings.py`(CACHES/CELERY/CHANNELS), `thesis_builder.py`, `briefing/client.py`, `rag/llm_service.py`.
- **병렬 정밀 조사**: Gemini 호출부 22파일 + FMP 소비처 21파일(파일:라인 근거 기반).
- **확인 한계**: 본 보고서는 정적 코드 감사. 실제 장애 주입(chaos) 테스트는 수행하지 않음. Celery 태스크 래퍼(`*/tasks.py`)의 `autoretry_for`/`max_retries` 설정은 표본만 확인 — 전수 점검은 후속 과제.
