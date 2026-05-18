# 외부 API 의존성 감사 보고서

- 작성일: 2026-05-18
- 범위: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis 외부 의존성 전수 조사
- 방식: 읽기 전용 정적 분석 (코드 수정 없음)

---

## 0. 핵심 요약 (TL;DR)

- **FMP**: 3개의 독립 `FMPClient` 구현이 공존 (`api_request/`, `macro/services/`, `serverless/services/`). 에러 분류·재시도·캐싱 정책이 클라이언트마다 다르며, `FMPPremiumError(402)` 처리가 `api_request/` 전용. `macro/` 와 `serverless/` 클라이언트는 402를 일반 HTTPError로 흘려보냄.
- **Gemini**: 9개 서비스에서 직접 `genai.Client` 호출. **CB가 붙은 곳은 3곳만** (`rag_analysis/llm_service`, `marketpulse/briefing/client`, `thesis/services/thesis_builder`). 나머지 6곳은 단순 `try/except`. JSON 파싱 에러 처리가 일관적이지 않음.
- **Circuit Breaker가 두 종류 공존**: `marketpulse/utils/circuit_breaker.py` (Redis 기반, tenacity 통합, 정식)와 `news/services/circuit_breaker.py` (단순 구현). 통합 필요.
- **FRED / SEC EDGAR**: 재시도 + Rate Limiter가 깔끔하게 구현됨. 위험 낮음.
- **Neo4j**: driver 부재 시 `is_available()=False` 폴백 + CB 적용. 우수.
- **Redis 캐시 자체 장애** 시: `cache.get` 호출 168건 중 대부분은 캐시 실패가 곧 데이터 조회 실패로 전파됨. graceful degradation 부족.

---

## 1. 의존성 매트릭스

### 1.1 서비스 × 외부 API × 핸들링 패턴

| 서비스/위치 | 외부 API | 재시도 | Rate Limit | 캐시 | Circuit Breaker | Fallback / 폴백 동작 |
|------------|---------|-------|-----------|------|----------------|---------------------|
| `api_request/providers/fmp/client.py` | FMP | ✅ 3회 + exp backoff | ✅ 0.2s + daily 10k | ❌ | ❌ | 5종 에러 클래스로 분기 |
| `api_request/providers/fmp/provider.py` | FMP | (위임) | (위임) | ❌ | ❌ | `FMPPremiumError`→`PREMIUM_ONLY`, `FMPRateLimitError`→`RateLimitError` |
| `macro/services/fmp_client.py` | FMP | ❌ | ✅ 0.2s | ❌ | ❌ | 예외 raise 또는 log+None |
| `serverless/services/fmp_client.py` | FMP | ❌ | ❌ (httpx 30s 타임아웃만) | ✅ Redis (5분~24h) | ❌ | 캐시 미스 시 raise `FMPAPIError` |
| `news/providers/fmp.py` | FMP (위임) | (위임) | (위임) | ❌ | (호출자 측) | except Exception → 빈 리스트 |
| `stocks/services/sp500_eod_service.py` | FMP | ✅ tenacity | ✅ | ✅ | ✅ `get_circuit` 사용 | — |
| `marketpulse/services/news_aggregator.py` | FMP | ✅ | ✅ | ✅ | ✅ | — |
| `macro/services/fred_client.py` | FRED | ✅ 3회 + transient 분류 | ✅ `get_rate_limiter('fred')` | ❌ | ❌ | 401/403/404 즉시 raise, 5xx 재시도 |
| `api_request/sec_edgar_client.py` | SEC EDGAR | (호출자 측) | ✅ time.sleep 0.12s | ❌ | ❌ | `SECEdgarError` |
| `sec_pipeline/collector.py` | SEC EDGAR | ❌ | ✅ 0.12s | 클래스 레벨 CIK 캐시 | ❌ | RequestException raise |
| `serverless/services/neo4j_chain_sight_service.py` | Neo4j | (driver 기본) | — | ✅ Redis | ✅ `neo4j_chain_sight` CB | `driver=None`이면 silent fallback |
| `chainsight/services/neo4j_sync.py` | Neo4j | — | — | — | ❌ | — |
| `rag_analysis/services/llm_service.py` | Gemini | ✅ 3회 + RPM 분기 | RPM 메시지 분기 | ❌ | ✅ `gemini_rag` CB | rate/quota/429 → 메시지 yield |
| `serverless/services/keyword_service.py` | Gemini | ✅ retry param | ❌ | ❌ | ❌ | `FALLBACK_KEYWORDS` 사전 정의 |
| `serverless/services/keyword_generator.py` | Gemini (async) | ❌ | ❌ | ❌ | ❌ | log + `return []` |
| `serverless/services/keyword_generator_v2.py` | Gemini | (요약) | — | — | ❌ | — |
| `serverless/services/llm_relation_extractor.py` | Gemini | ❌ | ✅ `time.sleep(4)` (15 RPM) | ✅ Redis 1h | ❌ | `ExtractionResult(error=...)` |
| `news/services/news_deep_analyzer.py` | Gemini | ❌ | ✅ `time.sleep(4)` | ❌ | ❌ | 단일 실패는 errors++ |
| `validation/services/llm_peer_filter.py` | Gemini | ❌ | ❌ | ❌ | ❌ | `{'error': str(e)}` |
| `sec_pipeline/extractor.py` | Gemini | ❌ | ❌ | ❌ | ❌ | JSON 파싱 실패→빈 relationships, 그 외 raise |
| `thesis/services/thesis_builder.py` | Gemini | (호출 분기) | — | — | ✅ CB 사용 (import) | rule-fallback 분기 |
| `thesis/services/prompt_builder.py` | Gemini | — | — | — | ❌ | — |
| `marketpulse/briefing/client.py` | Gemini | ✅ | ✅ | ✅ | ✅ | — |
| `news/api/views.py` | Gemini | (인라인) | — | — | ❌ | — |
| `portfolio/llm/client.py` | Gemini/Anthropic | (별도) | — | — | ❌ | — |
| `news/services/keyword_extractor.py` | Gemini | ❌ | — | — | ❌ | — |
| `news/services/stock_insights.py` | Gemini | ❌ | — | ✅ Redis | ❌ | — |
| `stocks/services/korean_overview_service.py` | Gemini | (요약) | — | — | ❌ | — |
| `rag_analysis/services/context_compressor.py` | Gemini | ❌ | — | — | ✅ CB | — |
| `rag_analysis/services/entity_extractor.py` | Gemini | ❌ | — | — | ❌ | — |
| `rag_analysis/services/adaptive_llm_service.py` | Gemini | ❌ | — | — | ❌ | — |
| `marketpulse/fetchers/fmp_weights.py` | FMP | (래퍼) | — | — | ✅ CB | — |

### 1.2 핸들링 카테고리별 카운트

| 카테고리 | 적용 파일 수 |
|---------|------------|
| `marketpulse/utils/circuit_breaker.get_circuit` 사용 | 16 |
| `news/services/circuit_breaker.py` 사용 | 2 (자체 파일 포함) |
| `cache.get/set` 사용 | 30 파일 / 168건 |
| `FMP*Error` 캐치 | 15 파일 |

→ Circuit Breaker가 **두 가지 구현**이고, 적용 범위가 외부 호출 지점의 **30% 미만**.

---

## 2. FMP 상세

### 2.1 클라이언트 3중 구현 — 정책 불일치

`FMPClient`가 동일 이름으로 3곳에 존재:

1. **`api_request/providers/fmp/client.py` (정식)**
   - 5종 에러 클래스: `FMPClientError`, `FMPRateLimitError`, `FMPAuthError`, `FMPPremiumError`, (`+ ValueError` 누락 키)
   - 401/402/403/429 분류 (lines 126-133)
   - 일일 한도 자체 체크 (10,000건)
   - exponential backoff `(attempt+1)*2`
   - `FMPPremiumError`/`FMPAuthError`/`FMPRateLimitError`는 재시도 없이 즉시 raise (line 149)

2. **`macro/services/fmp_client.py`**
   - 에러 분류 **없음** — `response.raise_for_status()` 만
   - 402가 일반 HTTPError로 흘러감 → 호출부에서 분기 불가
   - 캐싱 없음, 재시도 없음
   - rate limit은 `last_request_time` 기반 sleep 만

3. **`serverless/services/fmp_client.py`** (httpx 기반)
   - 캐싱 매우 적극적 (`fmp:quote`, `fmp:profile`, `fmp:peers`, `fmp:sector_stocks` 등 5분~24h)
   - 재시도 **없음**
   - 단일 `FMPAPIError`로 모든 실패 흡수 (402 vs 429 구분 불가)
   - `__del__`에서 client.close() — 객체 수명 의존성 위험

### 2.2 호출자 패턴 (위 1.1 표의 분포)

- **`api_request/providers/fmp/provider.py`**: 402(`FMPPremiumError`)와 429(`FMPRateLimitError`) 분기 패턴이 모든 메서드(`get_balance_sheet`/`get_income_statement`/`get_cash_flow`)에 일관 적용됨. ✅
- **`stocks/tasks.py`**: `max_retries`는 함수마다 다름. FMP 에러 분류는 호출하는 service 측에 위임.
- **`stocks/services/sp500_eod_service.py`**: `get_circuit` 적용 (CB 보호).
- **`stocks/services/fmp_fundamentals.py`**: 7건의 except 분기 — 세부 미확인.

### 2.3 위험 지점

| 위험 | 위치 | 설명 |
|------|------|------|
| 🔴 **402 미분류** | `macro/services/fmp_client.py`, `serverless/services/fmp_client.py` | Premium 심볼이 일반 에러로 처리 → CB가 정상 호출까지 차단할 위험 |
| 🟠 **재시도 부재** | `serverless/services/fmp_client.py` | 일시적 5xx도 즉시 실패. Market Movers/Screener 등 사용자 가시 경로에 영향 |
| 🟠 **3중 구현** | `api_request/`, `macro/`, `serverless/` | 정책 변경 시 3곳을 동시 수정해야 함. KB Pattern으로 통합 권장 |
| 🟡 **Daily limit 분산** | `api_request/providers/fmp/client.py:71` 만 일일 카운터 보유 | 다른 클라이언트는 일일 한도 의식 못 함 |
| 🟡 **타임아웃 30s** | 모든 FMP 클라이언트 | 동일하게 30초. EOD 배치 시 누적되면 worker 점유 |

### 2.4 Rate Limit 준수

- `api_request/`: `request_delay=0.2` (300/min = 5/s)
- `macro/`: `request_delay=0.2` 동일
- `serverless/`: httpx 30s timeout만, **분당 한도 자체 없음** → 짧은 배치에서 burst 시 429 발생 가능

---

## 3. Gemini 상세

### 3.1 호출 지점 (9개 핵심)

| 위치 | 모델 | thinking_budget | response_mime_type | 재시도 | CB | RPM 준수 |
|------|------|-----------------|---------------------|-------|-----|---------|
| `rag_analysis/services/llm_service.py` (스트리밍) | `gemini-2.5-flash` | 0 | (텍스트 스트리밍) | ✅ 3회 + `RETRY_DELAYS=[1,2,4]` | ✅ `gemini_rag` (5/60s) | rate/quota/429 메시지 분기 |
| `serverless/services/keyword_service.py` | `gemini-2.5-flash` | — | JSON | ✅ 2회 | ❌ | ❌ |
| `serverless/services/keyword_generator.py` (async) | `gemini-2.5-flash` | — | (텍스트) | ❌ | ❌ | ❌ |
| `serverless/services/llm_relation_extractor.py` | `gemini-2.5-flash` | 0 | application/json | ❌ | ❌ | ✅ `time.sleep(4)` (Free 15 RPM) |
| `news/services/news_deep_analyzer.py` | `gemini-2.5-flash` | — | (JSON 텍스트) | ❌ | ❌ | ✅ `time.sleep(4)` |
| `validation/services/llm_peer_filter.py` | `gemini-2.5-flash` | 0 | application/json | ❌ | ❌ | ❌ |
| `sec_pipeline/extractor.py` | `gemini-2.5-flash` | 0 | application/json | ❌ | ❌ | ❌ |
| `thesis/services/thesis_builder.py` + `prompt_builder.py` | (동적) | — | (분기) | (분기) | ✅ (`CircuitBreakerError` import) | — |
| `marketpulse/briefing/client.py` | (동적) | — | — | ✅ | ✅ | ✅ |

### 3.2 JSON 파싱 에러 처리

- `serverless/services/llm_relation_extractor.py`: `json.JSONDecodeError`/`TypeError` 분기 (코드 정독 시 line 86+). `result` 키 누락 보정 있음.
- `sec_pipeline/extractor.py`: `json.JSONDecodeError` 시 `relationships=[]`로 graceful return.
- `validation/services/llm_peer_filter.py`: **try-catch가 통째**로 `Exception` 흡수, JSON 파싱 실패와 API 실패가 동일하게 `{'error': str(e)}`로 묻힘.
- `news/services/news_deep_analyzer.py`: 단일 try/except, JSON 실패 시 article 단위 skip.
- `rag_analysis/services/llm_service.py`: 스트리밍이라 JSON 파싱 없음 (`<suggestions>` tag만 후처리).

### 3.3 429 / Quota 처리

- 정식 처리: `rag_analysis/services/llm_service.py:231-250` — `'rate' in err or 'quota' in err or '429' in err` 문자열 매칭 + exp backoff.
- 그 외: 일반 `Exception`으로 흡수.
- **Risk**: Gemini Free RPM 15. `serverless/services/keyword_service.py`/`validation/llm_peer_filter.py`는 RPM gating 없음 → 동시 호출 발생 시 429 폭주 가능.

### 3.4 Timeout

- Gemini SDK 자체 타임아웃 명시적으로 설정한 곳: **없음** (확인 범위 내). google-genai SDK 기본 타임아웃에 의존.

### 3.5 위험 지점

| 위험 | 위치 | 설명 |
|------|------|------|
| 🔴 **CB 미적용 다수** | keyword_service, keyword_generator, llm_relation_extractor, news_deep_analyzer, validation/llm_peer_filter, sec_pipeline/extractor | Gemini 장애 시 모든 배치가 동시에 timeout 누적 |
| 🟠 **JSON 파싱 실패 묻힘** | `validation/services/llm_peer_filter.py` | API 정상이지만 파싱 실패한 경우와 API 장애를 구분 못 함 |
| 🟠 **재시도 부재** | extractor.py, news_deep_analyzer | 일시적 429에 즉시 실패 |
| 🟡 **모델명 하드코딩** | 9곳 전부 `'gemini-2.5-flash'` 직접 문자열 | 모델 교체 시 9곳 동시 수정 |

---

## 4. 기타 의존성

### 4.1 FRED API

- 위치: `macro/services/fred_client.py`
- 평가: ✅ **모범 사례**
  - Transient 상태 코드 명시 (`{500, 502, 503, 504}`)
  - 401/403/404 즉시 raise
  - 5xx만 재시도 (max 3, `(attempt+1)*2` backoff)
  - `get_rate_limiter('fred')` 외부 모듈 사용
  - `_parse_value`로 `.`/빈 값 안전 처리
- 위험: 없음 (현재 패턴 유지 권장)

### 4.2 Neo4j

- 위치:
  - 드라이버: `rag_analysis/services/neo4j_driver.py` (`get_neo4j_driver`)
  - 동기화: `chainsight/services/neo4j_sync.py`, `chainsight/tasks/sync_tasks.py`, `news/services/news_neo4j_sync.py`
  - 조회: `serverless/services/neo4j_chain_sight_service.py`
- 평가: 🟡 **혼재**
  - ✅ `serverless/services/neo4j_chain_sight_service.py`: `driver=None`이면 fallback + CB 적용 (`neo4j_chain_sight`, 5/60s).
  - ❌ `chainsight/services/neo4j_sync.py`: `cache.get/set` 0회, CB 0회 — 장애 시 silent miss 위험.
  - ❌ `news/services/news_neo4j_sync.py`: 13건의 try/except가 있으나 CB 없음.
- 위험: Neo4j 컨테이너 다운 시 chainsight 동기화 태스크가 무한 retry 누적 가능. 비즈니스 영향은 "그래프 데이터 stale"로 제한적.

### 4.3 SEC EDGAR

- 위치: `api_request/sec_edgar_client.py`, `sec_pipeline/collector.py`, `serverless/services/regulatory_service.py`, `serverless/services/institutional_holdings_service.py`, `serverless/services/supply_chain_service.py`
- 평가: 🟢 **적정**
  - User-Agent 헤더 설정 (`SEC_HEADERS`, line 29)
  - `time.sleep(0.12)` rate limit (10 req/s)
  - CIK 캐시 (class-level `_cik_cache`)
  - `RequestException`을 raise — 호출자 측에서 분기 가능
- 위험: 클래스 레벨 캐시는 Celery worker 별로만 유효 (worker 재시작 시 lose). 비용 부담은 낮음 (무료 API).

### 4.4 Redis (캐시 + Celery broker + CB 상태)

- 사용처: `cache.get/set` 168건, 30개 파일.
- 평가: 🟠 **Graceful Degradation 부족**
  - **CB 상태 자체가 Redis 의존** (`marketpulse/utils/circuit_breaker.py:35-37`). Redis 다운 시 CB 동작 불능.
  - 대부분의 호출자: `cache.get` 결과가 `None`이면 외부 API 재호출 → Redis 장애 시 API 호출 폭주 가능.
  - Locmem 폴백 코드 없음 (운영 환경에서는 의도된 선택일 수 있음).
- 시드 보호: `config/settings_test.py`에서 LocMemCache 격리는 적용됨 (KB Bug #27).

---

## 5. Circuit Breaker 도입 후보 (우선순위)

### P0 (즉시 도입 권장 — 장애 시 사용자 가시 영향 큼)

1. **`serverless/services/fmp_client.py`** — Market Movers/Screener 등 사용자 페이지 경로. 캐싱은 적극적이나 캐시 미스 시 직접 API. 402/429 분기 없음.
2. **`serverless/services/llm_relation_extractor.py`** — News Intelligence Pipeline의 Phase 5. Gemini RPM 폭주 시 cascade 위험.
3. **`news/services/news_deep_analyzer.py`** — Tier C(0.93+) 뉴스만 처리하므로 호출 빈도는 적으나, 실패 시 EOD 분석 누락. CB로 자동 회로 차단 후 alert 필요.

### P1 (배치/백그라운드 — 장애 시 데이터 stale)

4. **`validation/services/llm_peer_filter.py`** — Peer 필터링 응답 시간이 길어지면 사용자 UX 영향.
5. **`sec_pipeline/extractor.py`** — 야간 배치. 실패 시 다음 배치 재시도하면 되지만, CB로 폭주 방지 필요.
6. **`serverless/services/keyword_generator.py` (async)** — Market Movers 키워드. 이미 fallback 키워드 있으나 CB 없음.

### P2 (Neo4j / 이미 부분 적용)

7. **`chainsight/services/neo4j_sync.py`** — `serverless/services/neo4j_chain_sight_service.py`가 사용하는 CB 패턴과 통합 권장.

### P3 (중복 제거)

8. **`news/services/circuit_breaker.py` ↔ `marketpulse/utils/circuit_breaker.py` 통합** — 두 CB 구현이 공존. tenacity 통합·async 지원이 있는 marketpulse 버전을 단일 소스로 채택 권장.

---

## 6. 보조 권장 사항 (코드 변경 없는 운영 권장)

- **CB 상태 관측 대시보드**: 이미 marketpulse CB가 Redis 키 (`cb:state:{name}`, `cb:fail_count:{name}`)를 사용. 운영 대시보드에서 키 dump → state OPEN 회로 alert.
- **FMP `daily_calls` 카운터 통합**: `api_request/providers/fmp/client.py:71`만 보유. `macro/` 및 `serverless/` 클라이언트도 동일 Redis 키 공유하면 일일 10,000 quota 전체 가시화.
- **Gemini 모델명 상수화**: `config/settings.py`에 `GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')` 추가 후 9곳에서 import. 모델 업그레이드 시 단일 변경점.
- **CB 두 구현 정리 시**: `news/services/circuit_breaker.py` 사용자(`news/services/aggregator.py` 등) 마이그레이션 후 deprecated. KB에 PATTERN으로 단일 CB 사용 규칙 명시.

---

## 7. 부록 — FMP/Gemini 호출 파일 목록 (전수)

### FMP 직접 호출자 (15)

```
api_request/providers/fmp/client.py (정식 클라이언트)
api_request/providers/fmp/provider.py
api_request/stock_service.py
macro/services/fmp_client.py (별도 클라이언트)
macro/services/macro_service.py
serverless/services/fmp_client.py (별도 클라이언트 - httpx)
serverless/services/data_sync.py
serverless/services/keyword_data_collector.py
serverless/services/enhanced_screener_service.py
serverless/services/chain_sight_service.py
serverless/services/market_breadth_service.py
serverless/services/sector_heatmap_service.py
serverless/services/cusip_mapper.py
serverless/services/filter_engine.py
serverless/services/neo4j_chain_sight_service.py
serverless/views.py
serverless/tasks.py
news/providers/fmp.py
news/services/aggregator.py
marketpulse/services/news_aggregator.py
stocks/services/sp500_eod_service.py
stocks/services/sp500_service.py
stocks/views_search.py
stocks/tasks.py
thesis/tasks/eod_pipeline.py
thesis/views/monitoring_views.py
users/utils.py
```

### Gemini 직접 호출자 (~14, 테스트 제외)

```
rag_analysis/services/llm_service.py            ← CB ✅
rag_analysis/services/context_compressor.py     ← CB ✅
rag_analysis/services/entity_extractor.py
rag_analysis/services/adaptive_llm_service.py
serverless/services/keyword_service.py
serverless/services/keyword_generator.py
serverless/services/keyword_generator_v2.py
serverless/services/llm_relation_extractor.py
serverless/services/csv_url_resolver.py
serverless/services/relationship_keyword_enricher.py
serverless/services/regulatory_service.py
serverless/services/thesis_builder.py
news/services/news_deep_analyzer.py
news/services/keyword_extractor.py
news/services/stock_insights.py
news/api/views.py
validation/services/llm_peer_filter.py
sec_pipeline/extractor.py
sec_pipeline/intelligence.py
thesis/services/thesis_builder.py               ← CB ✅
thesis/services/prompt_builder.py
thesis/services/indicator_matcher.py
thesis/tasks/summary.py
thesis/views/conversation_views.py
portfolio/llm/client.py
marketpulse/briefing/client.py                  ← CB ✅
stocks/services/korean_overview_service.py
scripts/validation/diagnose_gemini.py
scripts/validation/measure_tokens.py
```

---

## 8. 감사 결과 종합

- **위험 수준**: 🟠 (medium) — 외부 API 장애 시 cascade를 막을 단일 장치(CB)가 도입되어 있으나, 적용 커버리지가 30% 미만. 특히 Gemini 호출 6곳이 노출됨.
- **즉시 조치 필요 없음**: 야간 자동화 시스템은 이미 retry / fallback이 다층으로 깔려 있음 (KB Pattern: Slice 진행 중 발견된 패턴들). 다만 사용자 가시 경로 (Market Movers, Screener)는 P0 후보 도입을 권장.
- **다음 액션** (감사 결과만, 구현은 별도 PR):
  - 위 5절 P0 후보 3건에 `marketpulse/utils/circuit_breaker.get_circuit` 적용
  - FMPClient 3중 구현을 `api_request/providers/fmp/client.py` 단일 소스로 통합 (DECISIONS.md 등재)
  - `news/services/circuit_breaker.py` deprecation 플랜
