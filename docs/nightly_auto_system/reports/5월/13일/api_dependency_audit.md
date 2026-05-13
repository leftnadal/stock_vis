# 외부 API 의존성 감사 보고서

**감사일**: 2026-05-13
**범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis (캐시), Marketaux, Finnhub, USPTO, yfinance, Anthropic
**기준**: 코드 읽기 전용 정적 감사 (실행 검증 없음)

---

## 의존성 매트릭스 (서비스별 외부 API × 폴백/CB 유무)

| 호출 위치 | 외부 API | 클라이언트 | Retry | Rate-limit | Circuit Breaker | Fallback | 402/429 처리 | 캐시 |
|----|----|----|----|----|----|----|----|----|
| `api_request/providers/fmp/client.py` | FMP | requests | 3회 + exp backoff | 0.2s sleep, daily 10k | ✗ | ✗ | ✅ FMPPremiumError/FMPRateLimitError/FMPAuthError 분리 | ✗ |
| `api_request/providers/fmp/provider.py` | FMP | `FMPClient` 래퍼 | (client 위임) | (client 위임) | ✗ | ✗ | ✅ 402→`PREMIUM_ONLY`, 429→`RateLimitError` | ✗ |
| `serverless/services/fmp_client.py` | FMP | **httpx** | ✗ | ✗ | ✗ | ✗ | ⚠ 402 별도 분기 없음 (status_code → `FMPAPIError`) | ✅ 5min~24h |
| `macro/services/fmp_client.py` | FMP | requests | ✗ | 0.2s sleep | ✗ | ✗ | ⚠ 모두 ValueError/RequestException으로 묶음 | ✗ |
| `marketpulse/fetchers/fmp_weights.py` | FMP (ETF holdings) | requests | (CB의 tenacity 위임, 3회) | ✗ | ✅ `fmp_etf` | ✗ | ⚠ `raise_for_status` 그대로 | ✗ |
| `stocks/tasks.py::sync_sp500_financials` | FMP (재무) | `StockService` | task retry 3회 | `countdown=i*7s` | ✗ | ✗ | ⚠ `.` 심볼은 사전 제외 | ✗ |
| `stocks/services/sp500_eod_service.py` | FMP (OHLCV) | `serverless.fmp_client.FMPClient` | (CB의 tenacity 3회) | 0.2s sleep | ✅ `fmp_sp500_eod` (th=10/120s) | ✗ | ⚠ FMPAPIError로 묶임 | ✗ |
| `stocks/services/sp500_service.py` | FMP (constituents) | `serverless.fmp_client.FMPClient` | (CB 위임) | ✗ | ✅ `fmp_sp500_constituents` (th=3/300s) | datahub.io CSV | ⚠ | ✅ 24h |
| `stocks/services/financial_statements_fallback.py` | FMP → yfinance | `FMPFundamentalsService` | ✗ | ✗ | ✗ | ✅ **yfinance 백업** | ✗ | ✅ 10min |
| `stocks/services/fmp_fundamentals.py`, `fmp_screener.py`, `fmp_market_movers.py`, `fmp_exchange_quotes.py` | FMP | requests | ✗ | ✗ | ✗ | ✗ | ⚠ | 부분적 |
| `serverless/services/data_sync.py::sync_daily_movers` | FMP | `serverless.fmp_client.FMPClient` | (CB 위임) | ✗ | ✅ `fmp_market_movers` (th=5/120s) | ✗ | ⚠ | ✗ |
| `serverless/services/enhanced_screener_service.py` | FMP | `serverless.fmp_client.FMPClient` | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| `serverless/services/market_breadth_service.py` | FMP | `serverless.fmp_client.FMPClient` | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| `news/services/aggregator.py` → `news/providers/fmp.py` | FMP (news) | `FMPClient` 위임 | ✗ | ✗ | ✗ (CB는 task 레벨) | ✗ | ⚠ | ✗ |
| `news/tasks.py::collect_*_fmp` | FMP (news) | aggregator | task retry 2회 | `rate_limit='100/m'` | ✅ `news.services.circuit_breaker.CircuitBreaker('fmp')` (별도 모듈) | ✗ | ⚠ | ✗ |
| `marketpulse/services/news_aggregator.py` | FMP / Marketaux (news) | provider | (CB 위임) | ✗ | ✅ `fmp_news`, `marketaux` | ✗ | ⚠ | ✗ |
| `marketpulse/briefing/client.py` | **Gemini** (브리핑) | `genai.Client` 동기 | (CB 위임) | ✗ | ✅ `gemini` | ✗ | ⚠ generic exception | ✗ |
| `rag_analysis/services/llm_service.py` | Gemini (streaming) | `genai.Client.aio` | 3회 + exp `[1,2,4]s` | ✗ | ✅ `gemini_rag` (th=5/60s) | ✗ | ✅ 429/quota/rate 키워드 매칭 → 재시도 | ✗ |
| `rag_analysis/services/context_compressor.py` | Gemini (압축) | `genai.Client` | (CB 위임) | ✗ | ✅ `gemini_compress` | ✗ | ⚠ | ✗ |
| `rag_analysis/services/adaptive_llm_service.py` | Gemini (구 SDK) | `google.generativeai` configure | ✗ | ✗ | ✗ | ✗ | ⚠ generic | ✗ |
| `thesis/services/thesis_builder.py::_parse_free_input` | Gemini (가설 파싱) | `genai.Client` | (CB 위임) | ✗ | ✅ `gemini_thesis` (th=5/120s) | ✅ `_fallback_parse` 규칙 기반 | ⚠ | ✗ |
| `thesis/services/prompt_builder.py` (3곳) | Gemini (전제/시간/규모 추출) | `genai.Client` | ✗ | ✗ | ✗ | ✗ (반환 None) | ⚠ generic | ✗ |
| `thesis/services/indicator_matcher.py::match_indicators_for_llm` | Gemini | `genai.Client` | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| `thesis/tasks/eod_pipeline.py::_fetch_fmp_value` | FMP (key-metrics-ttm) | `api_request.FMPClient` | (client 3회) | (client 0.2s) | ✗ | ✗ | ✅ FMPPremiumError 분기 | ✗ |
| `news/services/news_deep_analyzer.py::_analyze_single` | Gemini (Tier A/B/C, 최대 6k tokens) | `genai.Client` | ✗ | ✗ | ✗ | ✗ | ⚠ bare except → None | ✗ |
| `news/services/keyword_extractor.py::_call_llm` | Gemini (Daily 키워드) | `genai.Client` | ✗ | ✗ | ✗ | ✗ | ⚠ generic | ✗ |
| `news/services/stock_insights.py` (한글 번역) | Gemini | `genai.Client` | ✗ | ✗ | ✗ | ✅ 실패 시 영문 유지 | ⚠ | ✗ |
| `serverless/services/keyword_service.py::_call_llm_sync` | Gemini | `genai.Client` 동기 | ✅ `max_retries` 인자, 429/quota/rate → exp `(i+1)*2` | ✗ | ✗ | ✗ | ✅ 키워드 매칭 | ✗ |
| `serverless/services/keyword_generator.py` / `keyword_generator_v2.py` | Gemini (async) | `genai.Client.aio` | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| `serverless/services/llm_relation_extractor.py` | Gemini | `genai.Client` | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| `serverless/services/relationship_keyword_enricher.py` | Gemini | `genai.Client` | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| `serverless/services/csv_url_resolver.py` | Gemini | `genai.Client` | ✗ | ✗ | ✗ | ✅ 룰 기반 fallback | ⚠ | ✗ |
| `serverless/services/thesis_builder.py` | Gemini | `genai.Client` | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| `validation/services/llm_peer_filter.py::parse_filter_with_llm` | Gemini (JSON 모드) | `genai.Client` | ✗ | ✗ | ✗ | ✅ `{'error': str(e)}` | ⚠ generic | ✗ |
| `stocks/services/korean_overview_service.py` | Gemini (한글 개요) | `genai.Client` | task retry 2회 + `default_retry_delay=300` | ✗ | ✗ | ✗ | ⚠ | ✗ (DB 저장) |
| `sec_pipeline/intelligence.py` | Gemini (파이프라인 리포트) | `genai.Client` | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| `portfolio/llm/client.py` | Gemini | `genai.Client` | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| `serverless/services/neo4j_chain_sight_service.py` | **Neo4j** | `rag_analysis.neo4j_driver` 싱글톤 | (CB의 tenacity 1회) | ✗ | ✅ `neo4j_chain_sight` (헬퍼 `_run_with_cb`) + `is_available()` | ✅ Driver=None → return None | n/a | n/a |
| `chainsight/graph/repository.py` | Neo4j | 자체 PID-aware lazy | ✗ | ✗ | ✗ | ⚠ `GraphConnectionError` raise | n/a | n/a |
| `shared_kb/ontology_kb.py` | Neo4j | 자체 `GraphDatabase.driver` | ✗ | ✗ | ✗ | ✗ | n/a | n/a |
| `macro/services/fred_client.py` | **FRED** | requests | ✅ 3회 + transient(5xx) 분리 | ✅ `RateLimiter('fred')` | ✗ | ✗ | n/a (401/403/404 즉시 raise) | (호출자 캐시) |
| `sec_pipeline/collector.py` | **SEC EDGAR** | requests | ✗ (raise_for_status) | ✅ `time.sleep(0.12)` per call | ✗ | ✅ edgartools 옵션 fallback | n/a | ✅ 클래스 CIK 캐시 |
| `serverless/services/uspto_client.py` | USPTO | requests | ✗ | (timeout=30만) | ✗ | ✗ | n/a | ✗ |
| `news/providers/marketaux.py` | Marketaux | requests | (marketpulse CB 경유 시 위임) | ✗ | ✅ marketpulse만 `marketaux` | ✗ | ⚠ | ✗ |
| `news/providers/finnhub.py` | Finnhub | requests | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| Redis (캐시 백엔드) | redis://127.0.0.1:6379/1 | django-redis | ✗ | n/a | n/a (CB가 Redis 의존) | ❌ **graceful degradation 없음** | n/a | n/a |
| Anthropic (옵션) | Claude | `AsyncAnthropic` (`adaptive_llm_service.py`) | ✗ | ✗ | ✗ | ✗ | ⚠ | ✗ |
| yfinance (재무 fallback) | Yahoo | yfinance lib | (라이브러리 내부) | ✗ | ✗ | ✓ **FMP의 fallback** | n/a | ✅ 10min |

> 범례: ✅ 명시적 처리 / ⚠ generic try-except / ✗ 미적용 / n/a 해당 없음

호출 통계 요약: FMP 클라이언트 import 기준 **약 83곳**, Gemini 사용 모듈 **약 19곳**, Neo4j 드라이버 **3개 별도**, Redis-기반 CB 키 **8종**(`fmp_news`, `fmp_etf`, `fmp_sp500_eod`, `fmp_sp500_constituents`, `fmp_market_movers`, `marketaux`, `gemini`, `gemini_rag`, `gemini_thesis`, `gemini_compress`, `neo4j_chain_sight`, news.services.CircuitBreaker('fmp')).

---

## FMP 상세

### 1. 클라이언트 분포 — **3개 중복 + 1개 위임**

| 파일 | 라이브러리 | 예외 체계 | 특이사항 |
|---|---|---|---|
| `api_request/providers/fmp/client.py` (492 lines) | `requests` | `FMPClientError`/`FMPRateLimitError`/`FMPAuthError`/**`FMPPremiumError`** | 일일 한도 10k 트래킹, exp backoff 3회, **유일하게 402 분리** |
| `serverless/services/fmp_client.py` (422 lines) | `httpx.Client` | `FMPAPIError` 단일 | 캐시 내장(5min~24h), Market Movers/Quote/Profile/Peers/Screener/SP500 CSV |
| `macro/services/fmp_client.py` (478 lines) | `requests` | 예외 `ValueError` + `RequestException` | 지수/섹터 ETF/원자재/환율, **재시도/CB 모두 없음** |
| `news/providers/fmp.py` (269 lines) | 위임(`FMPClient`) | generic | stock-news / general-news / press-releases |

**문제**: 세 클라이언트가 동일 도메인을 각자 다루고, 402(`FMPPremiumError`) 처리가 `api_request` 계열에만 있음. `serverless`·`macro` 호출 경로에서 프리미엄 심볼이 들어오면 `FMPAPIError("HTTP 402: …")` 또는 `ValueError`로 묶여 **재시도와 retry-skip 분기가 불가능**.

### 2. Rate-limit 처리

- **권장 가드**: 0.2s sleep (`api_request`, `macro`) — Starter 300/min 한도(5 req/s)와 정확히 일치.
- **`serverless/fmp_client.py`는 sleep 없음** → 단일 사용자 호출은 OK이나, Celery 병렬 batch에서 분당 한도 초과 위험.
- 일일 한도(10k) 트래킹은 `api_request` 클라이언트만 자체 카운터 보유. **나머지 클라이언트는 모름** → 운영 중 동일 키 사용 시 카운터 분산.
- `stocks/tasks.py::sync_sp500_financials`는 `countdown=i*7s`로 분산 (101 × 7s = 12분), `bulk_sync_sp500_financials`는 2s 간격. Celery rate_limit 데코레이터는 `update_financials_with_provider`에 `6/m`. **CB 미적용** — 장애 시 503 종목 모두 throw → 100 errors 후에야 retry.

### 3. 에러 핸들링 매트릭스

| 경로 | 401/403 | 402 (Premium) | 429 | 5xx | 네트워크 |
|---|---|---|---|---|---|
| `api_request/.../client.py` | `FMPAuthError` 즉시 raise | `FMPPremiumError` 즉시 raise | `FMPRateLimitError` 즉시 raise | `raise_for_status` → exp backoff 3회 | exp backoff 3회 |
| `api_request/.../provider.py` (래퍼) | error_response | `PREMIUM_ONLY` 코드 | `RateLimitError` | API_ERROR | API_ERROR |
| `serverless/fmp_client.py` | `FMPAPIError(HTTP 401)` | **`FMPAPIError(HTTP 402)`** — 분리 안 됨 | `FMPAPIError(HTTP 429)` | 동일 | 동일 |
| `macro/fmp_client.py` | `RequestException` | `RequestException` | `RequestException` | `RequestException` | `RequestException` |
| `news/tasks::collect_*_fmp` | breaker만 카운트 | breaker만 카운트 | breaker만 카운트 | breaker만 카운트 | breaker만 카운트 |
| `stocks/services/financial_statements_fallback.py` | `logger.debug` + 빈 list → **yfinance fallback** | (동일) | (동일) | (동일) | (동일) |

### 4. Fallback

| 도메인 | Primary | Fallback | 자동 전환 |
|---|---|---|---|
| 재무제표 | FMP | **yfinance** (`financial_statements_fallback.py`) | ✅ |
| SP500 constituents | FMP `/stable/sp500-constituent` | **datahub.io CSV** (`serverless/fmp_client.py::get_sp500_constituents`) | ✅ (애초 datahub만 사용) |
| SEC filings | FMP `sec-filings` Pro 전용 | **SEC EDGAR 직접** (`sec_pipeline/collector.py`) | ✅ (애초 SEC만) |
| 시세/뉴스/key-metrics | FMP | ✗ | n/a |

**갭**: 시세(`quote`), 회사 프로필, 재무 비율 등의 **단일 의존성**. FMP 장애 시 `update_stock_data`, `update_historical_prices`, EOD 파이프라인, Market Movers, Chain Sight 시드 등 전반이 마비.

### 5. FMPPremiumError 처리 위치

- ✅ `api_request/providers/fmp/provider.py` (balance/income/cashflow)
- ✅ `thesis/tasks/eod_pipeline.py::_fetch_fmp_value`
- ✅ `thesis/views/monitoring_views.py`
- ❌ `serverless/*`, `macro/*`, `stocks/services/fmp_*.py`, `news/*` — 분기 없음. 운영적으로 `.` 포함 심볼(BRK.B, BF.B 등)을 사전 필터링하는 우회만 존재(`stocks/tasks.py`).

---

## Gemini 상세

### 1. 호출 패턴 — **4가지 공존** (혼란)

| 패턴 | SDK | 사용처 | 비고 |
|---|---|---|---|
| `genai.Client(api_key).models.generate_content(...)` 동기 | `google.genai` 신규 | 대다수(thesis, news, serverless, validation, sec_pipeline, stocks, portfolio, marketpulse) | Bug #8 권장 |
| `genai.Client().aio.models.generate_content_stream(...)` 비동기 | `google.genai` | `rag_analysis/llm_service.py`, `serverless/keyword_generator*` | RAG 스트리밍 |
| `google.generativeai.configure(...) + GenerativeModel(...).generate_content_async` | **구 SDK** | `rag_analysis/adaptive_llm_service.py` | 마이그레이션 누락 — 신/구 SDK 혼용 |
| `cb.call(client.models.generate_content, ...)` | 신 SDK + CB | marketpulse 브리핑, thesis_builder._parse_free_input | CB 적용 |

> `rag_analysis/adaptive_llm_service.py:90` — `import google.generativeai as genai`는 다른 모든 모듈과 다른 SDK입니다. Bug #8 ("Celery에서 async LLM 호출 금지 → 동기 API만")의 위험을 다시 들여올 수 있음.

### 2. 429 / rate-limit 처리

| 위치 | 처리 |
|---|---|
| `rag_analysis/services/llm_service.py` | `'rate' in err or 'quota' in err or '429' in err` → 키워드 매칭 후 exp `[1,2,4]s` 재시도, 최종 실패 시 user-facing 에러 메시지 |
| `serverless/services/keyword_service.py::_call_llm_sync` | 동일 키워드 매칭, exp `(i+1)*2`초 재시도 |
| 그 외 16곳 | **재시도 없음**. 단발 호출 후 generic except → `logger.error` + return None |

### 3. JSON 파싱 에러 처리

- 다수 위치에서 `re.search(r'\{.*\}', text, re.DOTALL)` + `json.loads` → 실패 시 `_fallback_parse` 또는 None.
- ⚠ **응답 토큰 잘림** 케이스 대응:
  - `serverless/services/keyword_service.py::_parse_keywords`는 잘린 JSON 복구 패턴 보유.
  - 그 외 모듈은 단순 `JSONDecodeError` → fallback 없이 None 반환.
- ⚠ `response.text` 접근 전 `hasattr` 가드는 ~50% 모듈만.

### 4. Timeout 설정

- 신 SDK `genai.Client`는 HTTP timeout 명시 미설정 (라이브러리 기본). RAG 스트리밍은 무제한 wait 가능.
- `marketpulse/briefing/client.py`는 `latency_ms` 측정만 (timeout 자체는 없음).
- Celery `soft_time_limit`/`time_limit`로 간접 제어 — `bulk_generate_korean_overviews`는 7200s, `run_eod_pipeline`은 600s. **개별 Gemini 호출 timeout은 없음.**

### 5. CircuitBreaker 적용/미적용

| 적용 (4개) | 미적용 (16개+) |
|---|---|
| `gemini` (marketpulse 브리핑) | `news/services/news_deep_analyzer.py` ★ 일 5천 건 분석 |
| `gemini_rag` (RAG 스트리밍) | `news/services/keyword_extractor.py` ★ 일 1회 50건 |
| `gemini_thesis` (가설 자유 입력 파싱) | `news/services/stock_insights.py` |
| `gemini_compress` (컨텍스트 압축) | `serverless/services/keyword_service.py`, `keyword_generator*`, `llm_relation_extractor`, `relationship_keyword_enricher`, `csv_url_resolver`, `thesis_builder` |
| | `thesis/services/prompt_builder.py` (3곳), `indicator_matcher.py` |
| | `validation/services/llm_peer_filter.py` |
| | `stocks/services/korean_overview_service.py` ★ 월 1회 503건 배치 |
| | `sec_pipeline/intelligence.py`, `portfolio/llm/client.py` |
| | `rag_analysis/adaptive_llm_service.py` ★ 구 SDK |

★ = 대량 배치 또는 사용자 직접 노출 → CB 부재가 가장 위험.

---

## 기타 의존성

### FRED — **잘 처리됨**

- 단일 클라이언트 `macro/services/fred_client.py`.
- ✅ 재시도 3회, transient(500/502/503/504) 분리, permanent(401/403/404)는 즉시 raise.
- ✅ `RateLimiter('fred')` 사용 (api_request.rate_limiter).
- `timeout=30` 명시.
- ⚠ CB 미적용 (FRED는 무료 + 안정적이라 우선순위는 낮음).
- ⚠ 호출자(`MacroEconomicService.get_fear_greed_index`)는 실패 시 VIX=20, spread=1.0 **하드코딩 기본값**으로 대체 → 사용자에게 "중립"으로 표시되어 silent 실패 위험.

### Neo4j — **분산된 3개 드라이버 + 부분 CB**

| 드라이버 | 위치 | Fork 안전 | CB |
|---|---|---|---|
| RAG/Chain Sight 공유 싱글톤 | `rag_analysis/services/neo4j_driver.py` | ✅ `force_reset_after_fork()` 제공 | ✗ (호출자 측에서만) |
| Chainsight | `chainsight/graph/repository.py` | ✅ PID-aware lazy | ✗ |
| KB | `shared_kb/ontology_kb.py` | ✗ | ✗ |

- `serverless/services/neo4j_chain_sight_service.py`만 `_run_with_cb` 헬퍼로 누적 실패 추적 (`neo4j_chain_sight` CB) + `is_available()` 사전 차단.
- `chainsight/graph/repository.py`는 연결 실패 시 `GraphConnectionError` raise. CB 미적용.
- **Neo4j 다운 시**: silent degradation (`Driver is None` → `is_available()` False → 기능 비활성). 사용자에게 명시적 안내 없음.
- ⚠ **세 드라이버가 별도 connection pool** — 동시 사용 시 max_connection_pool_size(기본 50) × 3 = 150 connection.

### SEC EDGAR — **얇은 처리**

- `sec_pipeline/collector.py`, `api_request/sec_edgar_client.py`.
- ✅ Rate-limit: `time.sleep(0.12)` per call (10 req/sec 정책 준수).
- ✅ User-Agent 헤더 포함 — 단 **`'Stock-Vis stockvis@example.com'`은 실제 연락처가 아님** → SEC 정책상 차단 위험 (이건 정책 위반에 가깝지만 본 감사 범위 밖, 보안 audit에서도 다룰 만함).
- ✅ Ticker→CIK 클래스 레벨 캐시 (영구).
- ✗ 재시도 없음 (`requests.get` 실패 시 즉시 raise/예외 전파).
- ✗ CB 없음.
- ✗ 다운/지연 시 fallback 없음 (`edgartools`는 옵션 의존성, ImportError 시 None).

### Redis (캐시) — **graceful degradation 없음**

- 운영: `redis://127.0.0.1:6379/1` (django-redis).
- 테스트: settings_test.py LocMemCache 분리 (Bug #27 대응) ✅.
- 25+ 서비스가 `cache.get/set` 사용. **모두 `try/except` 없음** — Redis 다운 시 `RedisError` 그대로 throw → API 500.
- 더 큰 문제: **CB의 상태 저장소가 Redis**. Redis 다운 → CB 자체가 동작 불능 → cascading failure.
- ✅ FMP 1차 시도 → datahub CSV fallback 등 일부는 캐시 미스로 자동 처리 가능.

### Marketaux / Finnhub / USPTO / yfinance / Anthropic — **경량**

- Marketaux: marketpulse 경유 시 CB 보호, news/aggregator 직접 호출은 미보호.
- Finnhub: `news/providers/finnhub.py`만 — CB/재시도 없음.
- USPTO: `serverless/services/uspto_client.py` — timeout만, 재시도/CB 없음.
- yfinance: `stocks/services/financial_statements_fallback.py`에서 FMP의 폴백으로만 사용. yfinance 자체 장애 시 → 빈 결과.
- Anthropic: `rag_analysis/adaptive_llm_service.py`에서 선택적 — 실패 시 CONFIG 누락 메시지.

---

## Circuit Breaker 후보

> 우선순위 = (장애 시 영향 범위) × (호출 빈도) × (현재 보호 부재)
> 이미 CB가 적용된 호출은 제외.

### P0 — **즉시 도입 권장**

1. **`stocks/tasks.py::sync_sp500_financials` 및 `update_financials_with_provider`** (FMP)
   - 영향: S&P 500 전종목 재무제표 일일 배치 (101 종목/일). FMP 장애 시 101 retry × 3 = 303 실패 후에야 멈춤.
   - 권장: `fmp_financials` CB (failure_threshold=10, recovery=300s). 401/403/402는 CB 카운터에서 제외 (permanent).

2. **`news/services/news_deep_analyzer.py::_analyze_single`** (Gemini Tier A/B/C)
   - 영향: 일 수천 건 뉴스 분석, Tier C는 6k token. Gemini 429 시 한 article 실패하면 다음으로 진행하되 cascade로 비용 폭증.
   - 권장: `gemini_news_analyzer` CB + 토큰 quota 별도 추적.

3. **`stocks/services/korean_overview_service.py`** (Gemini, 월 1회 503건 배치)
   - 영향: `bulk_generate_korean_overviews`는 timeout 7200s. 중간 Gemini 429 시 남은 시간 계속 실패.
   - 권장: `gemini_overview` CB (th=5/120s).

4. **`api_request/providers/fmp/provider.py`** (StockService 메인 경로)
   - 영향: `update_stock_with_provider`가 사용자 watchlist, 포트폴리오 업데이트 등 거의 모든 경로의 진입점. 장애 시 모든 사용자 영향.
   - 권장: 메서드별 CB (`fmp_quote`, `fmp_profile`, `fmp_prices`, `fmp_financials`). 또는 통합 `fmp_provider` CB + per-endpoint 카운터.

### P1 — **다음 분기**

5. **`serverless/services/fmp_client.py` 전체** (Market Movers/Screener/Chain Sight)
   - 영향: `enhanced_screener_service`, `market_breadth_service`, `chain_sight_service` 등 6+ 사용처. `fmp_market_movers` 한 곳만 보호됨.
   - 권장: 클라이언트 레벨 CB 데코레이터 (`fmp_serverless`) 도입.

6. **`thesis/services/prompt_builder.py` 3곳 + `indicator_matcher.py::match_indicators_for_llm`** (Gemini)
   - 영향: 가설 빌더 대화형 흐름의 핵심. 실패 시 fallback 없이 None → 사용자 입력 무시.
   - 권장: `gemini_thesis_prompt` CB + `_fallback_parse` 통합.

7. **`validation/services/llm_peer_filter.py::parse_filter_with_llm`** (Gemini JSON 모드)
   - 영향: 1차 검증 LLM 대화형 필터. 사용자가 자연어 → 필터로 변환 못하면 UX 단절.
   - 권장: `gemini_validation` CB. 이미 `{'error': ...}` fallback이 있어 통합 쉬움.

8. **`macro/services/fmp_client.py`** (지수/섹터/원자재/환율)
   - 영향: Market Pulse 대시보드. 재시도 0회, CB 0개 → 단일 실패가 그대로 노출.
   - 권장: `macro/services/fred_client.py`처럼 재시도부터 + `fmp_macro` CB.

9. **Redis 자체** (graceful degradation)
   - CB가 Redis에 의존하므로 Redis 다운 = 모든 CB 불능. 대안:
     - CB 상태 저장소를 in-memory fallback으로 (프로세스 로컬 dict + Redis sync)
     - 캐시 호출부에 `cache_or_default(key, default)` 헬퍼 도입 (RedisError → default 반환).

### P2 — **장기 정비**

10. **`chainsight/graph/repository.py`, `shared_kb/ontology_kb.py`** (Neo4j)
    - `serverless/services/neo4j_chain_sight_service.py`의 `_run_with_cb` 패턴을 통일.
    - 권장: 공통 `Neo4jCircuitBreakerMixin` 또는 모든 Neo4j 호출이 `neo4j_chain_sight_service`를 경유하도록 리팩토링.

11. **`sec_pipeline/collector.py`** (SEC EDGAR)
    - SEC는 안정적이지만 IP 차단/User-Agent 정책 변경 위험. `sec_edgar` CB + User-Agent 실제 연락처로 수정 권장.

12. **News providers (`finnhub`, `marketaux` 직접 호출)**
    - marketpulse 경유 시만 보호 → 모든 `news/providers/*.py`가 통합 CB를 거치도록.

### CB 도입 시 공통 가이드 (이미 코드에 패턴 존재)

- 표준 모듈: `marketpulse/utils/circuit_breaker.py::get_circuit` (tenacity 기반, async/sync 모두 지원). `news/services/circuit_breaker.py`는 레거시 — **단일화 권장**.
- 임계값 가이드:
  - 대량 배치(SP500 전수): `failure_threshold=10, recovery_seconds=120~300`
  - 사용자 경로(quote/profile): `failure_threshold=5, recovery_seconds=60`
  - LLM 비용 위험: `failure_threshold=3, recovery_seconds=300` (비용 폭증 즉시 차단)
- Permanent 에러는 CB 카운터 제외 (401/403/402 — `retry_exceptions`에서 제외하거나 cb 호출 밖에서 처리).
- CB 상태 모니터링: `cache.get('cb:state:{name}')` → Prometheus/대시보드 노출 권장.

---

## 요약: 단일 장애점 (SPOF)

| 외부 의존 | SPOF 등급 | 핵심 영향 |
|---|---|---|
| FMP | 🔴 HIGH | 시세/재무/뉴스/스크리너/Movers 전반. yfinance 폴백은 재무에만. |
| Gemini | 🔴 HIGH | RAG/가설 빌더/뉴스 분석/한글 개요/Validation/Chain Sight LLM. 4 CB 보호 vs 16+ 미보호. |
| Redis | 🟠 MID | 캐시 + **CB 상태 저장소**. 다운 시 CB 자체 불능 → cascading failure. |
| Neo4j | 🟡 LOW | Chain Sight/Graph만. `is_available()` silent degradation 처리됨. |
| FRED | 🟢 OK | 재시도/rate-limit 잘 처리. Macro 대시보드만. |
| SEC EDGAR | 🟢 OK | 비동기 백그라운드. User-Agent 정책 위반 잠재 위험. |

**가장 시급한 조치 3가지**:
1. `stocks/tasks.py` FMP 배치에 `fmp_financials` CB 도입.
2. `news/services/news_deep_analyzer.py`에 `gemini_news_analyzer` CB + 토큰 quota 가드.
3. Redis 호출부에 `RedisError` graceful fallback 헬퍼 도입 (CB 자체의 가용성 확보).
