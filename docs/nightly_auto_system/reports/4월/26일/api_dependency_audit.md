# 외부 API 의존성 감사 보고서

- 작성일: 2026-04-26
- 범위: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis 장애 대응 패턴
- 모드: **읽기 전용**, 코드 수정 없음
- 감사 대상 파일 수: FMP 36개, Gemini 33개

---

## TL;DR (핵심 결론)

1. **FMP 클라이언트가 3개로 분기**되어 있고 각각 독립된 에러 클래스, request_delay, retry 정책을 가진다 — 일관성 부재가 가장 큰 위험.
2. **Provider Factory의 `FALLBACK_CHAIN[FMP] = []`** — FMP 장애 시 자동 폴백 없음. 모든 stock API는 단일 의존이다.
3. **Circuit Breaker는 `news/tasks.py`에서만 FMP에 적용** — 나머지 30+ FMP 호출 지점(EOD 파이프라인, 재무제표 동기화, Market Movers, Chain Sight, Screener, Sector Heatmap 등)에는 미적용.
4. **Gemini 호출 18개 중 14개가 client를 인스턴스 메서드 또는 함수 내에서 직접 생성** — 캐싱·재시도·실패 격리 부재. 공통 클라이언트 부재.
5. **Gemini 429/quota 처리는 텍스트 매칭 기반 (`'rate' in error_msg`)** — `google.api_core.exceptions.ResourceExhausted` 같은 정형 예외 사용 안 함. 메시지 변경 시 silent fail 위험.
6. **JSON 파싱 실패는 4개 패턴**: try/except + 폴백, 정규식 복구, 빈 dict 반환, 예외 전파(통일 안 됨).
7. **Neo4j는 lazy singleton + `is_available()`로 graceful degradation 지원** — 하지만 chainsight `Neo4jGraphRepository`는 별도 driver 사용으로 이중화.
8. **Redis 장애 graceful degradation 없음** — `cache.get()` 실패 시 단순 None 반환에만 의존, 캐시 fallback이 cascade로 외부 API 부하 증폭 가능.

---

## 의존성 매트릭스

서비스/태스크 × 외부 API × 보호 메커니즘 (재시도 / Fallback Provider / Circuit Breaker / 캐시 / Graceful)

| 서비스/엔트리포인트 | FMP | Gemini | FRED | Neo4j | SEC EDGAR | Redis | Retry | Fallback | Circuit | Graceful |
|---|---|---|---|---|---|---|---|---|---|---|
| `api_request/providers/fmp/client.py` | ✅ 직접 | – | – | – | – | – | ✅ 3회 expo | ❌ | ❌ | 부분 |
| `api_request/stock_service.py` (`StockService`) | ✅ via factory | – | – | – | – | – | ✅ 클라이언트 | ❌ FALLBACK_CHAIN 비어있음 | ❌ | ✅ ProviderResponse |
| `macro/services/fmp_client.py` | ✅ 직접 | – | – | – | – | – | ❌ | ❌ | ❌ | 부분 (개별 try) |
| `macro/services/fred_client.py` | – | – | ✅ | – | – | – | ✅ 3회 expo (transient) | ❌ | ❌ | 호출자별 try |
| `macro/services/macro_service.py` | ✅ via FMPClient | – | ✅ via FREDClient | – | – | ✅ 캐시 | 위임 | ❌ | ❌ | 부분 |
| `serverless/services/fmp_client.py` | ✅ httpx 직접 | – | – | – | – | ✅ TTL 캐시 | ❌ | ❌ | ❌ | 캐시 의존 |
| `serverless/services/data_sync.py` (Market Movers) | ✅ | – | – | – | – | – | 위임 | ❌ | ❌ | 종목별 try |
| `serverless/services/chain_sight_service.py` | ✅ | – | – | – | – | ✅ 1h | 위임 | ❌ | ❌ | 부분 |
| `serverless/services/sector_heatmap_service.py` | ✅ | – | – | – | – | ✅ 5m | 위임 | ❌ | ❌ | 섹터별 continue |
| `serverless/services/enhanced_screener_service.py` | ✅ | – | – | – | – | ✅ | 위임 | ❌ | ❌ | 부분 |
| `serverless/services/market_breadth_service.py` | ✅ | – | – | – | – | ✅ | 위임 | ❌ | ❌ | 부분 |
| `serverless/services/filter_engine.py` | ✅ | – | – | – | – | – | 위임 | ❌ | ❌ | 부분 |
| `serverless/services/keyword_service.py` | – | ✅ direct | – | – | – | – | ✅ 텍스트 기반 | ❌ | ❌ | 예외 전파 |
| `serverless/services/keyword_generator.py` | – | ✅ async direct | – | – | – | ✅ semantic | ❌ | ❌ | ❌ | 부분 |
| `serverless/services/keyword_generator_v2.py` | – | ✅ async direct | – | – | – | ✅ | ❌ | ❌ | ❌ | 부분 |
| `serverless/services/llm_relation_extractor.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | JSON 정규식 복구 |
| `serverless/services/relationship_keyword_enricher.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `serverless/services/csv_url_resolver.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `serverless/services/regulatory_service.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `serverless/services/neo4j_chain_sight_service.py` | – | – | – | ✅ via lazy driver | – | ✅ 5m | ❌ | ❌ | ❌ | ✅ is_available() 체크 |
| `serverless/services/cusip_mapper.py` | ✅ | – | – | – | – | ✅ | 위임 | ❌ | ❌ | 부분 |
| `news/services/aggregator.py` | ✅ via FMPClient | – | – | – | – | – | 위임 | ❌ Provider별 catch | ❌ | ✅ FMP 옵션 |
| `news/services/stock_insights.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `news/services/news_deep_analyzer.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | None 반환 |
| `news/services/keyword_extractor.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `news/api/views.py` (자유 텍스트 LLM) | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `news/tasks.py` collect_*_fmp_* | ✅ | – | – | – | – | ✅ | 위임 | ❌ | ✅ **유일 적용** | ✅ skip |
| `rag_analysis/services/llm_service.py` (LLMServiceLite) | – | ✅ async stream | – | – | – | – | ✅ 3회 expo (텍스트 매칭) | ❌ | ❌ | ✅ error 이벤트 |
| `rag_analysis/services/adaptive_llm_service.py` | – | ✅ + Anthropic | – | – | – | – | ❌ | ✅ Provider 선택 | ❌ | 부분 |
| `rag_analysis/services/entity_extractor.py` | – | ✅ async direct | – | – | – | – | ❌ | ✅ rule-based fallback | ❌ | ✅ |
| `rag_analysis/services/context_compressor.py` | – | ✅ async direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `validation/services/llm_peer_filter.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | error dict 반환 |
| `thesis/services/thesis_builder.py` (`_parse_free_input`) | – | ✅ direct | – | – | – | – | ❌ | ✅ `_fallback_parse` | ❌ | ✅ |
| `thesis/services/prompt_builder.py` (3 곳) | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | None 반환 |
| `thesis/services/indicator_matcher.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `thesis/views/conversation_views.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `thesis/views/monitoring_views.py` | ✅ via FMPClient | – | – | – | – | ✅ | ✅ 클라이언트 | ❌ | ❌ | ✅ 502 응답 |
| `thesis/tasks/eod_pipeline.py` (Indicator readings) | ✅ | – | ✅ | – | – | – | ✅ 클라이언트 | ❌ | ❌ | ✅ None 반환 |
| `stocks/tasks.py` (sync_sp500_*) | ✅ via StockService | – | – | – | – | ✅ | ✅ Celery retry | ❌ | ❌ | ✅ countdown 분산 |
| `stocks/services/sp500_service.py` | ✅ | – | – | – | – | ✅ | 위임 | ❌ | ❌ | 부분 |
| `stocks/services/sp500_eod_service.py` | ✅ | – | – | – | – | – | 위임 | ❌ | ❌ | 부분 |
| `stocks/services/fmp_screener.py` | ✅ httpx 직접 | – | – | – | – | ✅ | ✅ **429 retry-after** | ❌ | ❌ | 부분 |
| `stocks/services/fmp_fundamentals.py` | ✅ httpx 직접 (timeout=10s) | – | – | – | – | ✅ | ❌ | ❌ | ❌ | None 반환 |
| `stocks/services/fmp_market_movers.py` | ✅ httpx 직접 | – | – | – | – | ✅ | ❌ | ❌ | ❌ | 부분 |
| `stocks/services/fmp_exchange_quotes.py` | ✅ httpx 직접 | – | – | – | – | ✅ | ❌ | ❌ | ❌ | 부분 |
| `stocks/services/korean_overview_service.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `chainsight/graph/repository.py` | – | – | – | ✅ PID-based driver | – | – | ❌ | ❌ | ❌ | ✅ GraphConnectionError |
| `chainsight/api/views.py` | – | – | – | ✅ via repository | – | ✅ | ❌ | ❌ | ❌ | ✅ 503 응답 |
| `chainsight/views/watchlist_views.py` | – | – | – | ✅ | – | – | ❌ | ❌ | ❌ | ✅ except Graph* |
| `chainsight/tasks/sync_tasks.py` | – | – | – | ✅ neo4j_dirty 플래그 | – | – | ✅ Celery | ❌ | ❌ | ✅ 플래그 패턴 |
| `sec_pipeline/collector.py` | – | – | – | – | ✅ requests | – | ❌ (raise) | ❌ | ❌ | None / raise |
| `sec_pipeline/extractor.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | error dict |
| `sec_pipeline/intelligence.py` | – | ✅ direct | – | – | – | – | ❌ | ❌ | ❌ | 부분 |
| `shared_kb/ontology_kb.py` | – | – | – | ✅ direct driver | – | – | ❌ | ❌ | ❌ | 부분 |
| `users/cache_utils.py`, `stocks/cache_utils.py` | – | – | – | – | – | ✅ Redis | ❌ | ❌ | ❌ | None 반환 |

---

## FMP 상세

### 1. 클라이언트 3종 (중복 구현)

| 클라이언트 | 위치 | 라인 | HTTP 라이브러리 | request_delay | 재시도 | 에러 클래스 |
|---|---|---|---|---|---|---|
| Stock provider | `api_request/providers/fmp/client.py` | 491 | `requests` (sync) | 0.2s | 3회 expo | `FMPClientError`, `FMPRateLimitError`, `FMPAuthError`, `FMPPremiumError` |
| Macro/Market Pulse | `macro/services/fmp_client.py` | 477 | `requests` (sync) | 0.5s | **없음** | `ValueError` (raw) |
| Market Movers/Chain Sight | `serverless/services/fmp_client.py` | 421 | `httpx.Client` | 없음 | **없음** | `FMPAPIError` |

**위험도**: 🔴 **HIGH** — 같은 FMP API를 호출하는 3개의 별도 클라이언트가 존재. rate limit이 계정 단위로 합산되지만 클라이언트끼리 서로의 카운터를 모른다.

- `api_request/providers/fmp/client.py:110-112` — daily_limit 체크 (10000) — **로컬 인스턴스 카운터**, 분산 환경 미지원, 프로세스 재시작 시 리셋.
- `macro/services/fmp_client.py:108` — `requests.get(timeout=30)`, 재시도 없음. transient 5xx 발생 시 즉시 실패.
- `serverless/services/fmp_client.py:84-92` — `HTTPStatusError` / `RequestError` / `Exception` 모두 `FMPAPIError`로 단일화. 402 (Premium)도 일반 실패로 묶임.

### 2. Provider Fallback 체인 부재

`api_request/providers/factory.py:67-69`:
```
FALLBACK_CHAIN: Dict[ProviderType, List[ProviderType]] = {
    ProviderType.FMP: [],
}
```
- Alpha Vantage 제거 후 빈 배열로 남음. `call_with_fallback()`가 호출되어도 폴백 provider가 없어 단일 실패점.
- **영향 범위**: `StockService` 전 메서드 → `update_stock_data`, `update_historical_prices`, `update_financial_statements` → S&P 500 일일 동기화 + 재무제표 배치 + 가격 업데이트.

### 3. FMPPremiumError (402) 처리

✅ `api_request/providers/fmp/client.py:128-129` — 402 즉시 raise.
✅ `api_request/providers/fmp/provider.py` — balance_sheet/income/cash_flow 3곳에서 catch + `PREMIUM_ONLY` 응답으로 graceful.
✅ `stocks/tasks.py:147-150` — `'.' in symbol` 사전 필터링.
❌ `serverless/services/fmp_client.py` (`FMPClient` v2) — 402를 별도로 구분하지 않음. 모든 HTTP 에러가 `FMPAPIError`로 통합.
❌ `macro/services/fmp_client.py` — 402 구분 없음. `raise_for_status()` → `HTTPError` raw로 전파.

### 4. Rate Limit 처리

| 위치 | 분당 한도 | 일일 한도 | 사전 대기 | 429 처리 |
|---|---|---|---|---|
| `api_request/.../client.py` | (라이브러리 인지) | 10000 (로컬 카운트) | 0.2s | `FMPRateLimitError` raise, **재시도 안 함** |
| `macro/.../fmp_client.py` | 없음 | 없음 | 0.5s | 없음 |
| `serverless/.../fmp_client.py` | 없음 | 없음 | 없음 | `FMPAPIError`로 묶임 |
| `stocks/services/fmp_screener.py:158-180` | – | – | – | ✅ **`Retry-After` 헤더 파싱 + sleep** (가장 모범적) |
| `api_request/rate_limiter.py:42-44` | **10/min, 250/day** ⚠️ | – | – | Redis 분산 카운터 |

**위험도**: 🔴 **HIGH** — `api_request/rate_limiter.py`의 FMP 한도가 **`10/min, 250/day`**로 잘못 설정되어 있다 (Starter Plan은 300/min, 10000/day). 실제 호출에서는 클라이언트 자체 카운터가 우선 적용되지만, `RateLimiter`를 거치는 호출 (`macro/services/fred_client.py:70`처럼)은 과도하게 throttling될 수 있다. **검증 필요**: FMP 클라이언트가 RateLimiter를 사용하는지 확인.

### 5. Circuit Breaker 적용 현황

| 영역 | Circuit Breaker | 출처 |
|---|---|---|
| `news/tasks.py` 3개 태스크 (`collect_sp500_news_fmp_batch`, `collect_press_releases_fmp`, `collect_general_news_fmp`) | ✅ | `news/services/circuit_breaker.py` |
| 모든 다른 FMP 호출 (~30+ 지점) | ❌ | – |

`news/services/circuit_breaker.py`는 Redis 기반 (threshold=5, timeout=300s). 단순하고 잘 짜였으나 **news 모듈 외에서는 import 되지 않음**.

### 6. 호출 빈도 추정 (1일 기준)

| 작업 | 호출 수 | Beat 스케줄 |
|---|---|---|
| `sync_sp500_financials` (재무제표) | ~101 종목 × 3개 statement = **303** | 평일 20:00 |
| `update_stock_with_provider` (개별 호출) | 변동적 | on-demand |
| EOD 가격 동기화 | ~503 종목 × 1 historical = **503** | 평일 EOD |
| Market Movers | 3 endpoints + 60 종목 × 3 (quote/historical/profile) = **183** | 매일 07:30 |
| Sector Heatmap | 11 섹터 × (quote + 종목 리스트) ≈ **22+** | 매일 |
| Chain Sight 분석 | on-demand × profile + screener | 사용자 트리거 |
| News (FMP) | ~503 종목 (chord 6 batch) = **503** | 일 1회 |
| EOD Indicator Pipeline | active thesis × 지표(quote) | 매일 18:00 ET |

**일일 합산**: 1500~2500 calls 추정 → Starter Plan 10000/일의 15~25% 사용. **정상 운용 시 여유 있음**, 하지만 **재시도 폭주 시 단일 종목당 30+회 호출 가능 (Celery max_retries=3 × 클라이언트 재시도 3 × 호환되지 않는 카운터)**.

### 7. FMP 장애 시 영향 범위 (cascading)

```
FMP 장애
├── stocks: S&P 500 가격/재무제표 동기화 중단 → DailyPrice/BalanceSheet stale
│   └── thesis EOD pipeline: 가격 기반 지표 실패 → score 계산 누락
├── serverless: Market Movers/Screener/Chain Sight 응답 503
│   └── 메인 페이지 EOD Dashboard 14개 시그널 중 다수 결손
├── macro: Market Pulse 지수/섹터/원자재/환율 업데이트 실패
├── news: 뉴스 수집 + 보도자료 누락 (Circuit Breaker로 격리됨 — 유일)
└── thesis: monitoring_views FMP 호출 502 응답
```

**복구 시간**: 3개 클라이언트 카운터가 분산 동기화되지 않아 **장애 복구 후에도 일부 클라이언트가 여전히 daily_limit 도달 상태로 인식 가능 (프로세스 재시작 전까지)**.

---

## Gemini 상세

### 1. 클라이언트 생성 패턴

| 패턴 | 빈도 | 예시 |
|---|---|---|
| 모듈/함수 내 `genai.Client(api_key=...)` 인스턴스화 | **14개** | `validation/services/llm_peer_filter.py:72`, `news/api/views.py:786`, `thesis/services/prompt_builder.py:542,765,943`, `thesis/services/thesis_builder.py:431`, `thesis/services/indicator_matcher.py:197`, `thesis/views/conversation_views.py:228`, `sec_pipeline/intelligence.py:155`, `news/services/stock_insights.py:542` |
| 클래스 `__init__`에서 한 번만 생성 | **8개** | `keyword_generator*.py`, `keyword_service.py`, `news_deep_analyzer.py`, `llm_relation_extractor.py`, `relationship_keyword_enricher.py`, `keyword_extractor.py`, `korean_overview_service.py`, `csv_url_resolver.py` |
| Lazy 인스턴스화 (`_get_client` / `_genai`) | **2개** | `sec_pipeline/extractor.py:24-32`, `serverless/services/regulatory_service.py:90` |
| Async (`aio.models.generate_content`) | **5개** | `rag_analysis/services/llm_service.py:182`, `rag_analysis/services/entity_extractor.py:87`, `rag_analysis/services/context_compressor.py:134,281`, `keyword_generator*.py` (async) |
| 구식 SDK (`genai.GenerativeModel`) | **1개** | `rag_analysis/services/adaptive_llm_service.py:189` — google-generativeai 구버전 사용 |

**위험도**: 🟠 **MEDIUM** — 매 함수 호출마다 새 client 생성하는 14개 지점은 connection 재사용 효율 저하 + Celery fork 환경에서 의도치 않은 누수 가능.

### 2. 429 / Rate Limit 처리

| 패턴 | 적용 | 위치 |
|---|---|---|
| 텍스트 매칭 (`'rate' in error_str or 'quota' in error_str or '429' in error_str`) + 재시도 | 2 | `rag_analysis/services/llm_service.py:217`, `serverless/services/keyword_service.py:318` |
| 정형 예외 (`google.api_core.exceptions.ResourceExhausted`) | **0** ❌ | – |
| 재시도 없음 (예외 그대로 전파 또는 None 반환) | 16+ | 나머지 모두 |

**위험도**: 🔴 **HIGH** — Google SDK 버전이 변경되어 에러 메시지가 영문에서 정형 코드로 바뀌면 텍스트 매칭이 silent fail. 또한 429 외 503/500 transient에 대한 별도 처리 없음.

### 3. 응답 JSON 파싱 패턴

| 패턴 | 빈도 | 사례 |
|---|---|---|
| `response.text` → `json.loads()` 단순 | 8 | `sec_pipeline/extractor.py:75`, `validation/services/llm_peer_filter.py:86` |
| `response_mime_type='application/json'` 강제 + `json.loads()` | 4 | `llm_relation_extractor.py:398`, `csv_url_resolver.py`, `thesis/.../prompt_builder.py:557` |
| 정규식 추출 (`re.search(r'\{.*\}')`) + `json.loads()` | 3 | `thesis/services/thesis_builder.py:468`, `news_deep_analyzer.py` 일부, `entity_extractor.py:115` 마크다운 제거 |
| 파싱 실패 시 정규식 복구 | **1** ✅ | `serverless/services/llm_relation_extractor.py:455-478` (가장 모범적, 부분 응답 복구) |
| `JSONDecodeError` catch + 폴백 | 5 | `entity_extractor.py:107`, `extractor.py:86`, `prompt_builder.py:574` |
| catch 없음 (예외 전파) | 4 | `keyword_service.py`, `keyword_generator*.py` 일부 |

### 4. Timeout 설정

`google-genai` SDK는 명시적 timeout 파라미터를 받지 않고 transport-level 기본값(약 60s) 사용. **모든 Gemini 호출에 timeout 명시 없음** — 장기 hang 위험.

특히 `rag_analysis/services/llm_service.py:182`의 streaming 호출은 토큰별 yield되므로 timeout 미설정이 더 위험할 수 있음.

### 5. 호출 빈도 추정 (1일 기준)

| 작업 | 호출 수 | 비고 |
|---|---|---|
| Market Movers 키워드 (gainers/losers/actives × 20개) | **60** | 매일 |
| News Deep Analyzer (Tier A/B/C) | 변동 (수십~수백) | 매일 |
| News keyword extractor | 변동 | 수집 시 |
| Stock insights (요청별) | on-demand | 사용자 트리거 |
| Chain Sight LLM relations | 변동 | 배치 |
| RAG analysis (사용자 질문) | on-demand | 사용자별 |
| Thesis builder (자유 입력 파싱) | on-demand | 사용자별 |
| Indicator matcher | 가설 빌더당 1~3회 | 사용자별 |
| Validation LLM peer filter | on-demand | 사용자별 |
| SEC pipeline extractor (10-K) | 503 종목 × 2 (supply chain + business model) | 분기 1회 |

**Free tier (15 RPM, 1500 RPD) 한참 초과** — 유료 결제 가정. 비용 통제 미비.

### 6. 면책 조항 / Disclaimer

✅ `rag_analysis/services/llm_service.py:44-50` — DISCLAIMER 시스템 프롬프트 강제 포함.
❌ 다른 17개 호출 지점 — 면책 조항 없음. 사용자 표시되는 응답은 RAG 외 thesis_builder, conversation_views 등도 있음.

### 7. Gemini 장애 시 영향 범위

```
Gemini 장애
├── thesis_builder: 가설 자유 입력 파싱 실패 → _fallback_parse 동작 (제한적)
├── thesis prompt_builder (3 호출 지점) → JSON 응답 None 반환 → 가설 카드 없이 화면 표시 (UX 저하)
├── indicator_matcher → 추천 지표 추출 실패 → 빈 리스트
├── rag_analysis → "API 오류" 메시지 (graceful)
├── news_deep_analyzer → 분석 누락, 다음 기사로 진행
├── keyword_service / keyword_generator → 키워드 누락 → Market Movers 화면 키워드 빈 칸
├── llm_relation_extractor → Chain Sight 관계 누락
├── sec_pipeline → 10-K 추출 실패 → 데이터 누락 (분기당 1회 영향)
├── validation/llm_peer_filter → "could not parse" error 응답
└── chainsight regulatory_service → 규제 분석 누락
```

**격리 정도**: 호출자별 try/except가 대부분이어서 **상위 시스템 다운 없이 부분 실패에 그침** (FMP보다 안전). 다만 **반복 실패 시 로깅 폭주 + 비용 누출** (재시도 없음에도 호출은 계속됨).

---

## 기타 의존성

### FRED API

- 단일 클라이언트: `macro/services/fred_client.py` (445라인)
- 재시도: ✅ 3회 expo backoff, transient 5xx만 재시도, 401/403/404 즉시 raise
- Rate Limiter: ✅ Redis 분산 (`api_request/rate_limiter.py`, 100/min — 안전 마진)
- 호출 지점: `macro/services/macro_service.py`, `thesis/tasks/eod_pipeline.py:_fetch_fred_value`, `serverless/services/keyword_data_collector.py`
- Graceful: 호출자에서 try/except 후 None 반환 — EOD pipeline에서 indicator별 실패 격리 ✅
- **위험도**: 🟢 **LOW** — 가장 모범적인 클라이언트.

### Neo4j

- Driver 2개 공존:
  - `rag_analysis/services/neo4j_driver.py` — global lazy singleton, `is_available()`로 graceful (`Neo4jChainSightService` 사용)
  - `chainsight/graph/repository.py:Neo4jGraphRepository` — PID 기반 lazy + GraphConnectionError 정형 예외 (`chainsight` API 사용)
  - `shared_kb/ontology_kb.py` — 별도 driver 인스턴스
- Fork 안전: ✅ `force_reset_after_fork()` + `_pid` 체크
- Graceful: ✅ Neo4j 다운 시 503 응답 (chainsight) 또는 None 반환 (serverless)
- 동기화 패턴: `chainsight/tasks/sync_tasks.py` — `neo4j_dirty=True` 플래그 → 별도 워커가 처리 → 멱등 성공
- **위험도**: 🟡 **MEDIUM** — driver가 3곳에서 따로 관리되어 connection pool 분산. ontology_kb는 Celery fork 안전성 미확인. **검증 필요**.

### SEC EDGAR

- 위치: `sec_pipeline/collector.py`
- Rate Limit: ✅ `time.sleep(0.12)` (10 req/sec 준수, SEC 정책)
- User-Agent: ✅ 명시
- 재시도: ❌ 없음 (`raise_for_status()` 즉시 raise)
- 캐시: ✅ CIK 캐시 (클래스 레벨 dict — 프로세스 단위, fork 후 재사용)
- 폴백: ✅ `extract_sections_fallback`에서 `edgartools` 라이브러리 시도 (선택 의존성)
- **위험도**: 🟡 **MEDIUM** — SEC EDGAR 일시 장애 시 즉시 raise → Celery 태스크 재시도에 의존. retry-after 헤더 무시.

### Redis

- 백엔드: `RedisCache` (`redis://127.0.0.1:6379/1`) + Celery broker (`/0`) + Channels Redis Layer (포트 6379)
- 캐시 호출 빈도: 50개 파일에서 `cache.get/set` 233회
- **장애 시 graceful degradation 부재**: `cache.get()` 실패 시 일반적으로 None 반환되므로 코드는 cache miss와 구분 못 함 → **외부 API 호출 폭주 가능성**.
- Rate Limiter (`api_request/rate_limiter.py:131-137`): Redis 실패 시 Django LocMemCache fallback — 분산 환경에서는 카운터가 워커별로 따로 동작 → 실질적으로 limit 무력화.
- Circuit Breaker (`news/services/circuit_breaker.py`): Redis 장애 시 `is_open()`이 항상 False (`cache.get(self.key) is None`) → **Circuit Breaker 자체가 비활성화** (페일 오픈).
- **위험도**: 🔴 **HIGH** — Redis 장애가 다음 cascade 유발: 캐시 무효화 → API 폭주 → Rate Limiter 무력화 → 외부 API daily limit 도달 → 장애 확산.

---

## Circuit Breaker 도입 후보 (우선순위)

### 🔴 우선순위 1 — 즉시 도입 권장

#### 1.1 FMP — `serverless` 도메인
- **대상**: `serverless/services/fmp_client.py` 또는 그 호출자 (`data_sync.py`, `chain_sight_service.py`, `sector_heatmap_service.py`, `enhanced_screener_service.py`, `market_breadth_service.py`, `filter_engine.py`)
- **이유**: 메인 페이지 EOD Dashboard, Market Movers, Screener가 단일 FMP에 의존. 503 cascade 시 사용자 경험 직격타.
- **권장 패턴**: 기존 `news/services/circuit_breaker.py` 재활용. 단일 `'fmp'` 키 또는 엔드포인트별 키 (`fmp:gainers`, `fmp:profile` 등).

#### 1.2 FMP — Stock 동기화 + EOD Pipeline
- **대상**: `api_request/providers/fmp/client.py`, `thesis/tasks/eod_pipeline.py:_fetch_fmp_value`
- **이유**: 야간 배치가 FMP 장애와 만나면 1일 단위 데이터 결손 → score 계산 0으로 처리됨 (alarm 폭주).
- **권장 패턴**: Provider 레벨 Circuit Breaker — `call_with_fallback` 호출 전 체크.

#### 1.3 Gemini — 비용 제어 + 장애 격리
- **대상**: 모든 18개 호출 지점에 단일 `'gemini'` Circuit Breaker
- **이유**: 정형 예외 미사용 + 재시도 없는 16개 지점 → 429 cascade 시 비용 폭주.
- **권장 위치**: 공통 LLM 헬퍼 (`rag_analysis/services/llm_service.py`처럼) 신설 후 모든 호출이 위임.

### 🟠 우선순위 2 — 분기 내 도입

#### 2.1 Redis-아닌 fallback Circuit Breaker
- **이유**: 현재 Circuit Breaker가 Redis 장애 시 무력화. **로컬 메모리 secondary state**로 페일 클로즈로 전환.
- **참고**: `api_request/rate_limiter.py:131-137`이 비슷한 fallback을 시도 (불완전).

#### 2.2 SEC EDGAR
- **이유**: SEC 장애 시 분기 단위 데이터 누락. 빈도는 낮지만 1회 실패가 큰 영향.
- **권장**: threshold=3, timeout=600s.

### 🟡 우선순위 3 — 모니터링 후 결정

- **FRED**: 가장 안정적 + 재시도 견고. 현 시점에서는 불필요.
- **Neo4j**: `is_available()` 체크가 이미 페일 패스트. 추가 Circuit Breaker는 redundant.
- **Marketaux/Finnhub** (news Provider): 이미 별도 Circuit Breaker 적용 (`news/tasks.py` 인근).

---

## 보너스: 빠른 윈 (코드 변경 없이 가능한 개선 아이디어)

이 항목은 감사 결과로부터의 **권고**이며, 실제 변경은 별도 PR로 진행해야 함.

1. **`api_request/rate_limiter.py:42-45` FMP 한도 수정 검증** — `10/min, 250/day`가 의도된 값인지 확인 (코멘트는 "더 관대"라고 적힘) → Starter Plan 실제 한도(`300/min, 10000/day`)와 일치하도록 정렬 검토.
2. **Gemini Disclaimer 일원화** — 모든 user-facing LLM 응답에 disclaimer 미포함 위험 → 공통 system prompt 헬퍼 도입.
3. **3개 FMP 클라이언트 통합 → 중장기 리팩토링 candidate** — 단기적으로는 `api_request/providers/fmp/client.py`를 정본으로 정하고 다른 두 곳은 thin wrapper로 전환.
4. **`google.api_core.exceptions.ResourceExhausted` 사용 검토** — 텍스트 매칭에서 정형 예외로 전환.
5. **Gemini timeout 명시** — `genai.types.HttpOptions(timeout=...)` 또는 클라이언트 옵션으로 60s 명시.
6. **`stocks/services/fmp_screener.py:158-180`의 Retry-After 처리 패턴을 다른 FMP 클라이언트로 확산.**

---

## 부록: 감사 메서드

- 사용 도구: `Grep`, `Read` (Bash 사용 최소)
- 주요 검색 패턴:
  - `FMPClient|fmp_client|get_stock_service|StockService`
  - `generate_content|genai`
  - `FMPAPIError|except.*FMP|FMPRateLimitError|FMPAuthError`
  - `429|RATE_LIMIT|rate_limit|RateLimitError|RESOURCE_EXHAUSTED`
  - `circuit.*breaker|CircuitBreaker|tenacity|backoff\.`
  - `timeout=\d+|requests\.get.*timeout`
- 검토한 핵심 파일:
  - `api_request/providers/fmp/{client,provider,factory}.py`
  - `macro/services/{fmp_client,fred_client,macro_service}.py`
  - `serverless/services/{fmp_client,data_sync,chain_sight_service,sector_heatmap_service,neo4j_chain_sight_service,llm_relation_extractor,keyword_service}.py`
  - `news/services/{aggregator,circuit_breaker,news_deep_analyzer}.py`, `news/tasks.py`, `news/providers/fmp.py`
  - `rag_analysis/services/{llm_service,entity_extractor,adaptive_llm_service,neo4j_driver}.py`
  - `thesis/{tasks/eod_pipeline,services/prompt_builder,services/thesis_builder,views/monitoring_views}.py`
  - `validation/services/llm_peer_filter.py`, `sec_pipeline/{collector,extractor,intelligence}.py`
  - `chainsight/graph/{repository,exceptions}.py`, `chainsight/api/views.py`
  - `config/settings.py`, `api_request/rate_limiter.py`
- 코드 수정 없음. 본 보고서는 정적 분석 결과만을 반영.
