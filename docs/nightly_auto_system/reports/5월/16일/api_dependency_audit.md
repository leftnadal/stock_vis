# 외부 API 의존성 감사 보고서

- **감사 일시**: 2026-05-16
- **감사 대상 커밋**: `d0f36a4` (slice8)
- **감사 범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis
- **모드**: 읽기 전용 (코드 수정 없음)
- **방법**: Grep 전수 조사 + 3개 영역 병렬 Explore Agent 심층 분석
- **분석 파일 수**: FMP 호출 18개 / Gemini 호출 25개 / 기타 의존성 약 12개 (총 ~55개)

---

## 의존성 매트릭스

서비스별 외부 API 호출 분포 및 폴백/완화 장치 유무.

| 서비스(앱) | FMP | Gemini | FRED | Neo4j | SEC | Redis | 폴백 유무 | 비고 |
|------------|----|--------|------|-------|-----|-------|----------|------|
| stocks | ✅ (sp500, tasks, korean_overview) | ✅ (korean_overview) | – | – | – | ✅ (cache) | 부분 (CircuitBreaker) | 일일 가격 동기화 핵심 |
| api_request | ✅ (FMPClient 기반) | – | – | – | – | ✅ (rate_limiter) | call_with_fallback 체인 | 모든 FMP 호출의 1차 진입점 |
| serverless | ✅ (data_sync, screener, chain_sight, market_breadth, sector_heatmap, cusip, filter_engine, fmp_client) | ✅ (keyword, thesis_builder, llm_relation, regulatory, csv_resolver) | – | ✅ (neo4j_chain_sight) | – | ✅ (cache 5분) | 부분 (CircuitBreaker, 캐시) | 가장 의존성 밀집 영역 |
| macro | ✅ (fmp_client) | – | ✅ (fred_client) | – | – | ✅ (60s~7d) | ✅ (기본값 50, 캐시) | FRED 재시도 잘 구현 |
| news | ✅ (fmp.py, aggregator) | ✅ (keyword_extractor, deep_analyzer, api/views) | – | – | – | – | 부분 (다중 소스) | Finnhub/Marketaux 폴백 |
| thesis | ✅ (eod_pipeline, monitoring) | ✅ (prompt_builder, indicator_matcher, conversation, summary) | – | – | – | – | 부분 (None 반환) | FMPPremiumError 처리 ✅ |
| rag_analysis | – | ✅ (llm_service, context_compressor, entity, adaptive) | – | – | – | – | ✅ (CB + 폴백) | 가장 견고한 LLM 처리 |
| portfolio | – | ✅ (llm/client) | – | – | – | – | ✅ (Provider 전환) | 1회 재시도 구현 |
| marketpulse | ✅ (news_aggregator) | ✅ (briefing/client) | – | – | – | – | ❌ (briefing 폴백 없음) | 브리핑 실패 시 사용자 노출 |
| sec_pipeline | – | ✅ (extractor, intelligence) | – | – | ✅ (collector) | – | ❌ (extractor 폴백 없음) | edgartools 선택 의존성 |
| validation | – | ✅ (llm_peer_filter) | – | – | – | – | ✅ (에러 반환) | 선택 기능 |
| chainsight | – | – | – | ✅ (tasks 다수) | – | – | 부분 | Neo4j 큐 격리 |

### 처리 비율 요약 (FMP 18 / Gemini 25 기준)

| 항목 | FMP 처리율 | Gemini 처리율 |
|------|-----------|--------------|
| 명시적 예외 분류 | 9/18 (50%) | 4/25 (16%) |
| Retry 로직 | 4/18 (22%) | 3/25 (12%) |
| Fallback 데이터/응답 | 6/18 (33%) | 13/25 (52%) |
| Timeout 명시 | 미확인 (기본 30s) | **0/25 (0%)** ⚠️ |
| Premium/Rate 분류 | 5/18 (28%) | 1/25 (4%) |
| 캐싱 | 2/18 (11%) | 0/25 (직접 없음) |
| CircuitBreaker | 3/18 (17%) | 2/25 (8%) |

---

## FMP 상세

### 호출 분포 (18개 파일에서 확인)

**계층별 분류**
- 클라이언트 레이어 (3): `api_request/providers/fmp/client.py`, `macro/services/fmp_client.py`, `serverless/services/fmp_client.py`
- Provider 레이어 (1): `api_request/providers/fmp/provider.py`
- 비즈니스 로직 (14): stocks, serverless, macro, news, thesis 전반

**주요 호출 엔드포인트**
- 가격/시세: `/stable/quote`, `/stable/quote-short`, `/stable/historical-price-eod/full`
- 재무: `/stable/balance-sheet-statement`, `/stable/income-statement`, `/stable/cash-flow-statement`
- 지표: `/stable/key-metrics(-ttm)`, `/stable/ratios`, `/stable/financial-growth`
- 시장: `/stable/biggest-gainers|losers`, `/stable/most-actives`
- 매크로: `/stable/sector-performance`, `/stable/economic-calendar`, `/stable/treasury`
- 뉴스: `/stable/news/stock`, `/stable/news/general-latest`, `/stable/news/press-releases`

### FMPPremiumError (402) 처리

**처리하는 파일 (5건)**
1. `api_request/providers/fmp/provider.py` — balance_sheet/income_statement/cash_flow 3곳. 로깅 후 `ProviderResponse(error=...)` 반환
2. `thesis/tasks/eod_pipeline.py::_fetch_fmp_value` — None 반환
3. `thesis/views/monitoring_views.py` — 기본값 사용

**처리하지 않는 파일 (13건)**
대부분 `except Exception`으로 일괄 처리되어 402가 일시 오류처럼 보임. Celery 재시도 트리거 가능성 있음.

> 위험: 402는 구조적 오류(특정 심볼이 Starter 플랜에서 영원히 접근 불가)이므로 재시도가 의미 없음. CLAUDE.md 버그 #23 정책(즉시 실패 + `.` 포함 심볼 배치 제외)이 18개 호출 지점 중 5곳에만 적용됨.

### Rate Limit (300 calls/min, 10k calls/day)

| 파일 | 간격 처리 | 평가 |
|------|----------|------|
| `api_request/providers/fmp/client.py` | `time.sleep(0.2)` (5 req/s) | ✅ 안전 |
| `macro/services/fmp_client.py` | `time.sleep(0.2)` | ✅ 안전 |
| `serverless/services/fmp_client.py` | httpx 응답 캐시 (5분) | ✅ 우회 |
| `stocks/services/sp500_eod_service.py` | `time.sleep(0.3)` (3.3 req/s) | ✅ 안전 |
| `serverless/services/data_sync.py` | **간격 없음** | ⚠️ 위험 |
| `macro/services/macro_service.py::get_all_market_quotes` | 26개 심볼 개별 호출 | ⚠️ 위험 |

> `data_sync.py`는 종목당 quote+historical+profile 3 콜 × 배치 20+종목 → 60+ 콜이 sleep 없이 발사. CircuitBreaker(threshold=5)만 의존.

### Retry / Fallback

**Retry 보유 (4)**
- `client.py` (max_retries=3, exponential 2/4/6초)
- `serverless/tasks.py::sync_daily_market_movers` (Celery max_retries=3, delay 300초)
- `serverless/tasks.py::keyword_data_collection` (max_retries=2)
- `serverless/tasks.py::generate_keywords_batch` (max_retries=1)

**Fallback 보유 (6)**
- `api_request/stock_service.py::call_with_fallback` (Provider chain — 현재 FMP만)
- `sp500_eod_service.py` (target_date 없으면 최근값)
- `sp500_service.py` (CB 오픈 시 빈 리스트, 구성 동기화 스킵)
- `macro_service.py` (Exception 캐치 → 기본값 50/빈 dict)
- `news/services/aggregator.py` (Finnhub/Marketaux 폴백)
- `data_sync.py` (개별 종목 실패 시 다음 종목 계속)

**부재 (12)**: 대부분 `except Exception → log → return None|{}` 패턴. Silent failure.

### CircuitBreaker 적용 현황

| 파일 | 임계 | 복구 |
|------|------|------|
| `serverless/services/data_sync.py` | 5회 | – |
| `stocks/services/sp500_eod_service.py` | 10회 | – |
| `stocks/services/sp500_service.py` | 3회 | – |

> 임계가 파일별로 제각각(3/5/10). 일관된 정책 없음.

### FMP 장애 시 가장 위험한 5개 지점

| 순위 | 위치 | 영향 | 발생 확률 |
|------|------|------|----------|
| 1 | `api_request/stock_service.py::update_stock_data` | 종목 상세/포트폴리오 가격/PE/배당 표시 불가, 캐시 없음 | 높음 (매 조회) |
| 2 | `serverless/services/data_sync.py::sync_daily_movers` | Market Pulse 종목 랭킹 미업데이트, **rate limit 미처리** | 중간 |
| 3 | `stocks/services/sp500_eod_service.py::sync_eod_prices` | 500 종목 일일 가격, 기술분석 차트 끊김 | 중간 |
| 4 | `macro/services/macro_service.py` 전체 | 금리/VIX/섹터/환율 → Market Pulse 섹션 누락 | 낮음 (캐시 보호) |
| 5 | `thesis/tasks/eod_pipeline.py::_fetch_fmp_value` | 가설 지표 계산 불완전, Alert 오판정 | 중간 |

---

## Gemini 상세

### 호출 패턴 (25개 파일 전수)

- **모델**: 25개 모두 `gemini-2.5-flash` 단일
- **동기/비동기 분포**:
  - Sync (Celery 적합): 19개
  - Async: 5개 (`rag_analysis/` 4개 + `serverless/keyword_generator_v2.py`)
- **버그 #8(Celery에서 async LLM 금지) 위반**: 확인된 사례 없음 ✅
  - `thesis/tasks/summary.py` (Celery) → 동기 호출 확인
  - `rag_analysis/` async는 모두 ASGI/뷰 컨텍스트

### Timeout — 전수 결함 ⚠️

**25개 파일 모두 `timeout` 명시 없음 (0%)**

google-genai SDK는 grpc deadline 또는 `request_options={'timeout': ...}` 미설정 시 무한 대기 가능. 다음 지점은 사용자 체감 위험이 큼:

- `rag_analysis/services/llm_service.py` — 스트리밍 응답 중 hang → 클라이언트 무한 대기
- `thesis/views/conversation_views.py` — 가설 대화창에서 사용자 입력 후 hang
- `news/services/news_deep_analyzer.py` — 배치 처리 중 1개가 hang → 전체 지연
- `marketpulse/briefing/client.py` — 시장 브리핑 hang → 메인 페이지 영향

### 429 (Rate Limit) 처리

| 처리 ✅ | 미처리 ❌ |
|---------|-----------|
| `portfolio/llm/client.py` (1회 재시도+폴백) | thesis 4개 파일 (prompt/indicator/summary/conversation) |
| `rag_analysis/services/llm_service.py` (3회 재시도) | news 3개 파일 |
| `rag_analysis/services/context_compressor.py` (CB) | sec_pipeline 2개 파일 |
| (3/25 = 12%) | serverless 5개 파일, stocks/validation/marketpulse 등 |

> Gemini Free 15 RPM 한도에서 25개 호출 지점 중 22개가 429 미처리. 동시 사용자 증가 시 폭발적 실패 가능.

### JSON 파싱 폴백

**견고함 ✅ (13개)**: 정규식 복구 + JSONDecodeError 캐치 + 기본값
- `news/keyword_extractor.py` — `FALLBACK_KEYWORDS` 상수 폴백
- `thesis/services/indicator_matcher.py` — 키워드 매칭 폴백
- `rag_analysis/services/entity_extractor.py` — 규칙 기반 추출 폴백
- `serverless/services/csv_url_resolver.py` — 기본 전략 폴백

**취약 ⚠️ (4개)**
- `sec_pipeline/extractor.py:75-76` — `re.search() → json.loads()` 직접, 예외 없음
- `serverless/services/thesis_builder.py` — 파싱 실패 시 폴백 부재
- `serverless/services/regulatory_service.py` — JSON 파싱 로직 미정의
- `rag_analysis/services/adaptive_llm_service.py` — `json.loads()` 미사용 / 검증 없음

**파싱 자체 없음 (4개)**: marketpulse/briefing, thesis/summary, serverless/keyword_generator_v2, serverless/regulatory_service

### Gemini 장애 시 가장 위험한 5개 지점

| 순위 | 위치 | 이유 |
|------|------|------|
| 1 | `portfolio/llm/client.py` | 전체 LLM 호출 허브 → 비용 추정/가설 생성 모두 중단 |
| 2 | `rag_analysis/services/llm_service.py` | RAG 스트리밍 응답 (timeout 부재로 hang 위험) |
| 3 | `thesis/services/prompt_builder.py` | 가설 빌더 핵심 (call_gemini), retry/timeout 모두 없음 |
| 4 | `serverless/services/thesis_builder.py` | EOD 테제 자동 생성 배치, fallback 없음 |
| 5 | `marketpulse/briefing/client.py` | 메인 페이지 브리핑, fallback 없음, timeout 없음 |

### Gemini 종합 결함 순위

1. **Timeout 0% — P0 위험**
2. **429 처리 12% — P0 위험** (Free tier 15 RPM 한도 고려 시 가장 빈번한 실패)
3. **Retry 12% — P1 위험**
4. **JSON 파싱 폴백 부재 4건 — P1**

---

## 기타 의존성

### FRED API (위험도: MEDIUM)

- **호출**: `macro/services/fred_client.py::FREDClient`
- **데이터**: DGS10/2/30, FEDFUNDS, CPIAUCSL, CPILFESL, PCEPI, UNRATE, PAYEMS, VIXCLS, GDPC1 등 15+ 시리즈
- **에러 처리**: max_retries=3, 지수 백오프 (2/4/6초), 401/403/404 즉시 raise, 5xx 재시도
- **Rate**: `get_rate_limiter("fred")` (분당 100, 0.6초 간격)
- **캐싱**: realtime 60s / daily 3600s / monthly 86400s / quarterly 604800s
- **장애 영향**: Market Pulse 대시보드 (fear_greed, interest_rates, inflation, global_markets). `get_fear_greed_index()`만 기본값(50) 폴백, 대부분은 `{'error': str(e)}` 반환 → UI 처리 의존
- **평가**: 4개 의존성 중 가장 견고. 다만 `get_interest_rates_dashboard` 류 고수준 API의 fail-open 정책 미흡.

### Neo4j (위험도: HIGH)

- **호출**: `serverless/services/neo4j_chain_sight_service.py::Neo4jChainSightService`, 기타 chainsight/tasks/
- **드라이버**: `get_neo4j_driver()` (singleton from `rag_analysis.services.neo4j_driver`)
- **격리**: Celery `neo4j` 큐 (`config/celery.py:36-55`), fork pool 사용
- **에러 처리**: CircuitBreaker (임계 5회, 복구 60초), `_run_with_cb()` 헬퍼로 래핑, 드라이버 None일 때 graceful skip (False/[])
- **캐싱**: `get_n_depth_graph()` 결과 5분 (`cache.set(cache_key, graph_data, 300)`)
- **장애 영향**: Chain Sight 전체 (관계 조회, 그래프 시각화, 프로필 동기화) 중단. PostgreSQL에 원본 데이터는 있으나 그래프 탐색 불가.
- **위험 근거**: 핵심 기능 중단 + CB 임계까지 누적 지연(5회 × 평균 응답 시간) + 동기화 태스크 실패 시 PG/Neo 데이터 스큐

### SEC EDGAR (위험도: MEDIUM-HIGH)

- **호출**: `sec_pipeline/collector.py::SECFilingCollector`
- **엔드포인트**:
  - `https://data.sec.gov/submissions/CIK{}.json`
  - `https://www.sec.gov/files/company_tickers.json`
  - `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}`
- **Rate**: SEC 공식 10 req/s → `time.sleep(0.12)` (라인 83, 130, 151)
- **에러 처리**: `requests.exceptions.RequestException` catch, User-Agent 필수, **`raise_for_status()`로 4xx/5xx 모두 raise (폴백 없음)**
- **캐싱**: CIK 클래스 레벨 dict 캐시, 섹션 추출은 메모리 후 DB 저장
- **폴백**: regex 추출 실패 시 `extract_sections_fallback()` → edgartools (**선택적 의존성**)
- **장애 영향**: 10-K 파이프라인 정지. edgartools 미설치 환경에서는 폴백도 동작 안 함.
- **위험 근거**: 폴백이 선택적 의존성에 의존, 메타데이터 호출 실패 시 즉시 반환(`238-239`)

### Redis (위험도: HIGH — SPOF)

- **역할 3중**:
  - Django cache backend (`redis://127.0.0.1:6379/1`)
  - Celery broker (`redis://localhost:6379/0`)
  - Rate limiter 카운터 (`api_request/rate_limiter.py:108,137`)
- **사용처**: macro_service, neo4j_chain_sight (그래프 캐시), api_request/cache/decorators, 전반
- **Celery result backend**: Django DB로 분리 ✅ (이중 설정 후 DB 우선 — `config/celery.py:478,486`)
- **에러 처리**: rate_limiter는 Redis 실패 시 `logger.debug` fallback (counter 증가 실패 → 카운팅 우회), Django cache는 명시적 try/except 없음
- **테스트 격리**: CLAUDE.md 버그 #27 — `config/settings_test.py`에 LocMemCache 분리 필요 (conftest.py 가드 확인 필요)
- **장애 영향 다층**:
  1. 캐시 미스 → 모든 요청이 외부 API 직접 호출 → FMP/Gemini 할당량 초과 (cascade)
  2. Rate limiter 우회 → 외부 API 호출 폭증 → 차단 위험
  3. Celery broker DOWN → 모든 비동기 작업 중단 (EOD, news, chain_sight, thesis)
- **위험 근거**: SPOF + cascade effect. Redis 1개 장애가 FMP/Gemini 동시 차단으로 전파.

### 위험도 랭킹

1. **Redis (HIGH)** — SPOF + cascade. 단일 장애가 다른 모든 외부 API 차단으로 확산.
2. **Neo4j (HIGH)** — Chain Sight 완전 중단, PG 폴백 미흡.
3. **SEC EDGAR (MEDIUM-HIGH)** — 폴백이 선택적 의존성에 의존.
4. **FRED (MEDIUM)** — 재시도/캐싱 견고하나 고수준 API fail-open 정책 부재.

---

## Circuit Breaker 후보

현재 CircuitBreaker 적용 현황 (3건만):
- `serverless/services/data_sync.py` (FMP, threshold=5)
- `stocks/services/sp500_eod_service.py` (FMP, threshold=10)
- `stocks/services/sp500_service.py` (FMP, threshold=3)
- `marketpulse/briefing/client.py` (Gemini, CB 보유)
- `rag_analysis/services/context_compressor.py` (Gemini, CB 보유)

### 신규 도입 우선순위

| 순위 | 후보 지점 | 근거 | 권장 정책 |
|------|----------|------|----------|
| **P0-1** | `portfolio/llm/client.py` | 모든 LLM 호출의 단일 허브, 장애 시 시스템 전반 영향, timeout 미설정 | threshold=5, recovery=60s, 폴백: 캐시된 마지막 응답 |
| **P0-2** | `api_request/providers/fmp/client.py` | 모든 FMP 진입점, 18개 호출 지점이 의존, 캐시 없음 | threshold=10, recovery=120s, 폴백: DB 마지막 값 |
| **P0-3** | `rag_analysis/services/llm_service.py` | 스트리밍 응답 hang 위험, 사용자 실시간 노출 | threshold=3, recovery=30s, 폴백: 정중한 에러 메시지 + 부분 응답 |
| **P1-4** | `thesis/services/prompt_builder.py` | 가설 빌더 핵심, retry/timeout/CB 모두 부재 | threshold=5, 폴백: None + UI 재시도 버튼 |
| **P1-5** | `serverless/services/thesis_builder.py` | EOD 배치, 1건 실패로 배치 중단 위험 | threshold=10, 폴백: 해당 종목 스킵 |
| **P1-6** | `macro/services/fred_client.py` 호출자 | Market Pulse 의존, FRED 자체는 견고하나 호출자 측 fail-open 미흡 | threshold=5, 폴백: 캐시 stale 값 허용 |
| **P1-7** | `sec_pipeline/collector.py` | 10-K 파이프라인, edgartools 선택 의존성 폴백 | threshold=5, recovery=300s, 폴백: 배치 다음날 재시도 |
| **P2-8** | `news/services/news_deep_analyzer.py` | RPM 준수하나 개별 timeout 부재로 hang 시 배치 지연 | threshold=10, 폴백: 해당 뉴스 스킵 |
| **P2-9** | `serverless/services/keyword_generator_v2.py` | 배치 20개 중 1개 실패로 전체 롤백 위험 | threshold=5, 폴백: 부분 결과 커밋 |
| **P2-10** | `marketpulse/briefing/client.py` 폴백 강화 | CB는 있으나 폴백 없음 — 사용자 메인 페이지 노출 | 캐시 stale + 정적 메시지 추가 |

### CircuitBreaker 정책 일관화 권장

현재 임계가 3/5/10으로 제각각. 다음 표로 표준화 검토:

| 호출 유형 | threshold | recovery | 폴백 |
|-----------|----------|----------|------|
| 사용자 실시간 응답 | 3 | 30s | 정중한 에러 + 캐시 |
| 백그라운드 배치 | 10 | 300s | 해당 항목 스킵 |
| 핵심 동기화 (EOD) | 5 | 120s | 다음 회차 재시도 |

---

## 종합 결론 및 권장 조치

### P0 (즉시)

1. **Gemini timeout 25개 호출 전수 추가** — google-genai SDK의 `request_options` 또는 grpc deadline. 0% → 100%.
2. **Gemini 429 retry 22개 미처리 지점에 tenacity 적용** — `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=30))`
3. **FMP `serverless/services/data_sync.py` rate limiting 추가** — 종목 루프에 `time.sleep(0.2)` 또는 토큰 버킷
4. **FMPPremiumError(402) 사전 필터 적용** — 13개 미처리 지점에 `.` 포함 심볼 + 알려진 프리미엄 심볼 제외 (CLAUDE.md 버그 #23)
5. **`portfolio/llm/client.py`에 CircuitBreaker 추가** — LLM 허브 보호

### P1 (1주 내)

1. **JSON 파싱 폴백 강화** — `sec_pipeline/extractor.py`, `serverless/services/thesis_builder.py`, `serverless/services/regulatory_service.py`
2. **CircuitBreaker 정책 일관화** — threshold 3/5/10 표준화
3. **Redis 캐시 graceful degradation 강화** — rate_limiter 외 영역도 fallback 추가
4. **`marketpulse/briefing/client.py` 폴백 추가** — 메인 페이지 영향 차단
5. **Celery task exponential backoff 적용** — 현재 default_retry_delay 고정값 사용

### P2 (장기)

1. **Redis HA 구성 (Sentinel/Cluster)** — SPOF 해소
2. **Neo4j Circuit Breaker 튜닝** — 임계 낮추기 (5→3), 복구 시간 (60s→30s)
3. **edgartools 필수 의존성 전환** — SEC 폴백 보장
4. **FMP Starter → Professional 검토** — 프리미엄 심볼 지원
5. **모니터링 대시보드** — API 호출량, 에러율, 캐시 hit rate, CB 상태

### 핵심 메트릭 종합 (한 줄 요약)

> **Gemini timeout 0%**, **Gemini 429 처리 12%**, **FMP Premium 처리 28%**, **CircuitBreaker 5/55 호출 지점**, **Redis SPOF 미해소** — 외부 API 장애 시 cascade failure 가능성 높음.

---

**감사 종료**: 2026-05-16
**다음 권장 점검**: P0 조치 완료 후 재감사 (timeout/retry 적용률 95% 이상 목표)
