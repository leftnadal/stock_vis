# 외부 API 의존성 감사 보고서

- **감사 일자**: 2026-05-03
- **감사 범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis
- **감사자**: Claude (read-only static audit)
- **판단 근거**: `api_request/`, `serverless/`, `macro/`, `stocks/`, `news/`, `thesis/`, `rag_analysis/`, `validation/`, `sec_pipeline/` 디렉토리 정적 분석
- **목적**: 야간 자동화 파이프라인의 외부 API 장애 대응 점검 + Circuit Breaker 도입 후보 식별

> ⚠️ 본 보고서는 **현재 코드 상태 (portfolio 브랜치)** 만 분석한 결과이며, 운영 환경 로그/메트릭은 포함하지 않습니다.

---

## 0. 핵심 요약 (Executive Summary)

| 영역 | 상태 | 핵심 리스크 |
|------|-----|-----------|
| **FMP** | ⚠️ 클라이언트 3종 분산 | 단일 provider 의존 + Premium error 분기 미통일 |
| **Gemini** | ⚠️ 재시도 패턴 비일관 | 29개 호출지 중 2개만 429 재시도 구현 |
| **FRED** | ✅ 양호 | rate_limiter + 5xx 재시도 통합 |
| **Neo4j** | ✅ 양호 | lazy singleton + graceful fallback 잘 구축됨 |
| **SEC EDGAR** | ⚠️ User-Agent placeholder | 실제 차단 위험 |
| **Redis** | ⚠️ 캐시 미스 핸들링 부분 | rate_limiter는 fallback OK, 일반 cache는 의존성 강함 |
| **Circuit Breaker** | ⚠️ 부분 구현 | `news/services/circuit_breaker.py`만 존재, 사용처는 news/tasks 3곳뿐 |

**최우선 조치 권고 3건**
1. **FMP CircuitBreaker 확장** — 현재 `news/tasks.py`에서만 활용. `stocks/services/sp500_eod_service.py`, `serverless/tasks.py`, `thesis/tasks/eod_pipeline.py`로 확장하면 야간 EOD 파이프라인이 cascading failure를 피할 수 있음
2. **Gemini 호출 wrapper 통합** — 재시도/백오프 로직이 `rag_analysis/services/llm_service.py`(async, 1,2,4초)와 `serverless/services/keyword_service.py`(sync, 2,4,6초)에만 존재. 나머지 27개 호출지는 단일 시도. 공통 `gemini_call_with_retry()` 유틸 도입 권장
3. **FMPClient 단일화** — `api_request/providers/fmp/client.py`(견고) ↔ `serverless/services/fmp_client.py`(중간) ↔ `macro/services/fmp_client.py`(취약) 3종이 병존. `FMPPremiumError`/`FMPRateLimitError` 분기 누락된 구현체에서 402 응답을 일반 에러로 처리하면 batch 전체 실패 위험

---

## 1. 의존성 매트릭스 (서비스별 외부 API × Fallback 유무)

| 서비스 / 호출지점 | FMP | Gemini | FRED | Neo4j | SEC | Redis | 장애 시 대체 동작 |
|------------------|:---:|:------:|:----:|:-----:|:---:|:-----:|------------------|
| `stocks/services/sp500_eod_service.py` | ✅ | — | — | — | — | — | ❌ 단일 종목 실패 시 다음 종목 진행, 전체 retry 없음 |
| `stocks/tasks.py:aggregate_weekly_prices` | DB only | — | — | — | — | — | DailyPrice 기반 집계라 외부 의존 없음 |
| `serverless/tasks.py:sync_daily_market_movers` | ✅ | — | — | — | — | — | ⚠️ Celery `max_retries=3, retry_delay=300s` 적용 |
| `serverless/services/keyword_service.py` (Market Movers 키워드) | — | ✅ sync | — | — | — | 캐시 사용 | 429 재시도 구현 (2/4/6초), 그 외 raise |
| `serverless/services/keyword_generator.py` (Market Movers 배치) | — | ✅ async | — | — | — | — | ❌ 단일 시도, 실패 시 빈 list |
| `serverless/services/keyword_generator_v2.py` | — | ✅ async | — | — | — | — | ❌ 단일 시도 |
| `serverless/services/llm_relation_extractor.py` | — | ✅ sync | — | — | — | TTL 1h | ❌ 재시도 없음, raise |
| `serverless/services/regulatory_service.py` | — | ✅ sync | — | — | ✅ | — | ❌ JSON 파싱 실패 시 빈 list |
| `serverless/services/csv_url_resolver.py` | — | ✅ sync | — | — | — | TTL 24h | ❌ 단일 시도 |
| `serverless/services/relationship_keyword_enricher.py` | — | ✅ sync | — | — | — | — | ❌ 단일 시도 |
| `serverless/services/chain_sight_service.py` | ✅ | — | — | ✅ | — | 캐시 사용 | Neo4j는 None fallback OK, FMP 에러는 `FMPAPIError` catch |
| `serverless/services/neo4j_chain_sight_service.py` | — | — | — | ✅ | — | TTL 5m | ✅ `is_available()` 체크, driver=None 시 graceful skip |
| `serverless/services/market_breadth_service.py` | ✅ | — | — | — | — | — | `FMPAPIError` catch + 빈 결과 반환 |
| `serverless/services/sector_heatmap_service.py` | ✅ | — | — | — | — | — | `FMPAPIError` catch |
| `serverless/services/enhanced_screener_service.py` | ✅ | — | — | — | — | — | `FMPAPIError` catch |
| `serverless/services/filter_engine.py` | ✅ | — | — | — | — | — | `FMPAPIError` catch |
| `serverless/services/data_sync.py` (Market Movers 동기화) | ✅ | — | — | — | — | — | `FMPAPIError` 4지점에서 catch |
| `macro/services/fmp_client.py` | ✅ | — | — | — | — | — | ⚠️ Premium error 분기 없음, 일반 ValueError |
| `macro/services/fred_client.py` | — | — | ✅ | — | — | — | ✅ 5xx 재시도 (3회), 401/403/404 즉시 raise |
| `macro/services/macro_service.py` | ✅ | — | ✅ | — | — | — | 두 client 중 하나 실패 시 부분 데이터 반환 |
| `news/providers/fmp.py` | ✅ | — | — | — | — | — | bare `except Exception` → 빈 list |
| `news/services/news_deep_analyzer.py` | — | ✅ sync | — | — | — | — | ❌ 단일 시도, `time.sleep(4)` RPM 준수 |
| `news/services/keyword_extractor.py` | — | ✅ sync | — | — | — | — | ❌ 단일 시도 |
| `news/services/stock_insights.py` | — | ✅ sync | — | — | — | — | ❌ 단일 시도 |
| `news/tasks.py:collect_sp500_news_fmp_batch` | ✅ | — | — | — | — | — | ✅ **CircuitBreaker('fmp') 사용** (5회 실패 시 5분 차단) |
| `rag_analysis/services/llm_service.py` (RAG 메인) | — | ✅ async | — | — | — | — | ✅ 429 감지 후 1/2/4초 재시도 |
| `rag_analysis/services/context_compressor.py` | — | ✅ async | — | — | — | — | ❌ 단일 시도 |
| `rag_analysis/services/entity_extractor.py` | — | ✅ async | — | — | — | — | ❌ 단일 시도 |
| `rag_analysis/services/adaptive_llm_service.py` | — | ✅ async (`generate_content_async`) | — | — | — | — | 별도 wrapper |
| `rag_analysis/services/neo4j_service.py` | — | — | — | ✅ | — | — | ✅ `driver is None` 시 빈 결과 + meta source='fallback' |
| `thesis/services/thesis_builder.py` | — | ✅ sync | — | — | — | 캐시 사용 | ❌ 단일 시도, 빈 list 반환 |
| `thesis/services/prompt_builder.py` | — | ✅ sync (3개 호출지) | — | — | — | — | ❌ 단일 시도, JSON 파싱 실패 시 None |
| `thesis/services/indicator_matcher.py` | — | ✅ sync | — | — | — | — | ❌ 단일 시도 |
| `thesis/tasks/eod_pipeline.py` | ✅ (`_fetch_fmp_value`) | — | ✅ (`_fetch_fred_value`) | — | — | — | None 반환만, 재시도 없음 — **태스크 자체 retry 없음** |
| `thesis/views/monitoring_views.py` | ✅ | — | — | — | — | — | `FMPPremiumError`+`FMPClientError` catch |
| `validation/services/llm_peer_filter.py` | — | ✅ sync | — | — | — | — | ❌ 단일 시도 |
| `sec_pipeline/extractor.py` (Gemini Track A/B) | — | ✅ sync (lazy) | — | — | — | — | ❌ 단일 시도, raise |
| `sec_pipeline/collector.py` | — | — | — | — | ✅ | — | ❌ 재시도 없음, `User-Agent placeholder` |
| `chainsight/tasks/*` | ✅ (FMP) | — | — | ✅ (Neo4j) | — | — | — |

**범례**: ✅=직접 의존, —=무관, ❌=실패 시 재시도/대체 없음

---

## 2. FMP 상세

### 2.1 FMP 클라이언트 3종 병존 — 일관성 문제

| 클라이언트 | 위치 | 에러 분기 | 재시도 | Rate Limiter |
|-----------|------|----------|--------|-------------|
| **A: 강건판** | `api_request/providers/fmp/client.py` | `FMPClientError`, `FMPRateLimitError`, `FMPAuthError`, `FMPPremiumError` | ✅ max_retries=3, exp backoff (2/4/6s), Auth/Premium/RateLimit은 즉시 raise | ✅ 자체 (`request_delay=0.2`, `daily_limit=10000`) |
| **B: 중간판** | `serverless/services/fmp_client.py` | 단일 `FMPAPIError` (httpx 기반 + Django cache 캐싱) | ❌ 재시도 없음 | ❌ 별도 없음 |
| **C: 단순판** | `macro/services/fmp_client.py` | `requests.RequestException` raise + `Error Message`는 ValueError | ❌ 재시도 없음 (개별 메서드에서 try/except로 None 반환) | ❌ `request_delay=0.5`만 자체 |

#### 위험 시나리오

1. **402 Premium Error 처리 불일치**
   - A 클라이언트는 `FMPPremiumError`로 분기 → `provider.py`에서 `error_code='PREMIUM_ONLY'` 처리 → 다음 심볼로 진행 ([api_request/providers/fmp/provider.py:247](api_request/providers/fmp/provider.py:247))
   - B 클라이언트는 모든 비-200을 `FMPAPIError`로 묶음 → S&P 500 대량 동기화 시 첫 402(예: BRK.B, BF.B 등 `.` 포함 심볼) 만나면 Celery `self.retry()` 발동 → **불필요한 재시도 폭주**
   - **버그 #23 (`common-bugs.md`) 미적용 영역 존재**: serverless/macro의 클라이언트가 402를 영구 실패로 인식하지 않음

2. **단일 Provider 의존 — Fallback 사실상 비활성**
   - `api_request/providers/factory.py:67` `FALLBACK_CHAIN = { ProviderType.FMP: [], }` 빈 리스트
   - Alpha Vantage 제거 후 FMP 단독, FMP 5분 다운 = 전 화면 가격/재무 데이터 마비
   - `call_with_fallback()` 함수는 존재하지만 fallback이 빈 리스트라 효과 없음

3. **Rate Limit 추적 분산**
   - `api_request/rate_limiter.py`에 fmp 240/min, 8000/day 정의 → 그러나 **A/B/C 클라이언트 모두 RateLimiter 사용 안 함**
   - 각 클라이언트는 자체 `request_delay`만 보유 → Celery worker가 여러 큐에서 병렬로 FMP를 때리면 **300/min 한도 초과 가능**
   - Worker 4개 × `delay 0.2s` = **이론상 1200 req/min** (한도 4배)

4. **`get_batch_quotes` 비효율**
   - `macro/services/fmp_client.py:146` 콤마 구분 배치가 402를 던져서 개별 호출로 처리 → 25개 심볼 × 0.5s = 12.5초 (지수+섹터+원자재+환율 매번)

### 2.2 FMP 호출지점별 에러 핸들링 매트릭스

| 호출지점 | Premium(402) | RateLimit(429) | Daily Limit | Network Error | Celery Retry |
|---------|:------------:|:--------------:|:-----------:|:-------------:|:------------:|
| `api_request/providers/fmp/provider.py` | ✅ 분기 | ✅ raise | ✅ | ✅ exp backoff | — |
| `serverless/tasks.py:sync_daily_market_movers` | ⚠️ 합쳐짐 | ⚠️ 합쳐짐 | ❌ | ✅ retry 3회 5분 간격 | ✅ |
| `stocks/services/sp500_eod_service.py` | ⚠️ 합쳐짐 | ⚠️ 합쳐짐 | ❌ | ❌ Exception wrap | ❌ |
| `thesis/tasks/eod_pipeline.py:_fetch_fmp_value` | ✅ 분기 (별도 catch) | ⚠️ FMPClientError로 합쳐짐 | ❌ | ❌ Exception → None | ❌ |
| `news/tasks.py:collect_sp500_news_fmp_batch` | ⚠️ 합쳐짐 (CircuitBreaker로 보완) | ⚠️ 합쳐짐 (CB 보완) | ❌ | ✅ CB 5회/5분 차단 | — |
| `news/providers/fmp.py` | bare except | bare except | bare except | bare except | — |
| `macro/services/fmp_client.py` | ❌ 미분기 | ❌ 미분기 | ❌ | ✅ raise | — |

### 2.3 FMP 핵심 발견사항

- **FMPPremiumError를 분기 처리하는 곳: 3 곳뿐** (`provider.py`, `eod_pipeline.py`, `monitoring_views.py`)
- **FMPRateLimitError를 분기 처리하는 곳: 1곳뿐** (`provider.py`)
- **CircuitBreaker 사용: `news/tasks.py`의 3개 함수만** (`collect_sp500_news_fmp_batch` 등)
- **5월 EOD 파이프라인 (thesis/tasks/eod_pipeline.py)** → `update_indicator_readings`은 `FMPPremiumError`만 분기, **외부 API가 5분 다운되면 모든 indicator의 raw_value=None** → 이후 `calculate_scores` 단계가 빈 데이터로 진행 위험

---

## 3. Gemini 상세

### 3.1 호출 패턴 분류 (29개 파일 + 4개 테스트)

#### 3.1.1 동기/비동기 분포

| 패턴 | 호출지점 수 | 위험도 |
|-----|:----------:|:-----:|
| `client.models.generate_content` (sync) | 14곳 | ✅ 권장 |
| `client.aio.models.generate_content` (async) | 6곳 | ⚠️ Celery 호출 시 위험 (`common-bugs.md` #8) |
| `model.generate_content_async` (구 SDK) | 1곳 (`adaptive_llm_service.py`) | ⚠️ |

#### 3.1.2 async 호출이 Celery에서 사용되는 위험 지점

| 파일 | Celery 사용 | 동기화 wrapper |
|-----|:----------:|---------------|
| `serverless/services/keyword_generator.py` | ⚠️ Yes | `generate_keywords_sync` (asyncio.get_event_loop() 패턴) |
| `serverless/services/keyword_generator_v2.py` | ⚠️ Yes | 동일 패턴 |
| `rag_analysis/services/llm_service.py` | API view (Django Channels)에서만 사용 | — |
| `rag_analysis/services/context_compressor.py` | RAG 분석 태스크 | wrapper 검토 필요 |
| `rag_analysis/services/entity_extractor.py` | RAG 분석 태스크 | wrapper 검토 필요 |

> 버그 #8 (`common-bugs.md`): "Celery에서는 동기 API만 사용". 위 wrapper는 `loop.run_until_complete`로 우회하지만, Celery worker fork + asyncio 결합은 macOS에서 SIGSEGV 위험 (#25).

### 3.2 재시도/백오프 패턴

| 호출지점 | 429 감지 | 재시도 | 백오프 | 비고 |
|---------|:--------:|:-----:|:------:|------|
| `rag_analysis/services/llm_service.py` | ✅ `'rate'/'quota'/'429'` 키워드 매칭 | 3회 | [1, 2, 4]초 | RAG 메인 — 가장 견고 |
| `serverless/services/keyword_service.py` | ✅ 동일 키워드 매칭 | max_retries 동적 | (n+1)*2초 | Market Movers 키워드 — 견고 |
| `news/services/news_deep_analyzer.py` | ❌ | ❌ | `time.sleep(4)` (15 RPM 준수) | Tier C까지 단일 시도 |
| `sec_pipeline/extractor.py` | ❌ | ❌ | — | JSON 에러는 빈 dict, 일반 에러는 raise |
| 나머지 25개 호출지 | ❌ | ❌ | — | 단일 시도, 실패 시 None/빈 list |

### 3.3 JSON 파싱 / 응답 검증 패턴

| 패턴 | 호출지점 | 안전성 |
|-----|---------|:------:|
| `response_mime_type='application/json'` + `json.loads(response.text)` | sec_pipeline/extractor.py, validation/llm_peer_filter.py, prompt_builder.py | ✅ 가장 안전 |
| `response.text` → `re.search(r'\[.*\]')` → `json.loads` | regulatory_service.py | ⚠️ 잘린 JSON에 약함 |
| `response.text` → 코드블록 제거 → `json.loads` + 잘린 JSON 복구 | keyword_service.py | ✅ 견고 |
| 평문 텍스트 yield (스트리밍) | rag_analysis/services/llm_service.py | — (스트리밍 특성) |

### 3.4 Timeout / API Key 관리

- **Gemini SDK 호출에는 timeout 설정 없음** (SDK 기본값 의존, 일부 환경에서 무한 대기 위험)
- API key 폴백: `GOOGLE_AI_API_KEY` → `GEMINI_API_KEY` (대부분 호출지에 일관)
- **Gemini Free Tier 한도: 15 RPM, 1500 RPD** (`CLAUDE.md`) — 야간 배치가 동시에 여러 큐에서 호출하면 RPM 초과 가능
  - 예: `update_indicator_readings` (sync) + `news_deep_analyzer` (4초 sleep) + `llm_relation_extractor` 동시 실행 시

### 3.5 Gemini 핵심 발견사항

- **재시도 로직이 2개 호출지에만 존재** → 한 번의 transient 에러로 Tier C 뉴스 분석 등이 통째로 누락
- **client 인스턴스화 패턴 분산**: 매 호출마다 `genai.Client(api_key=...)` 생성. `sec_pipeline/extractor.py`만 lazy singleton (Celery fork 안전)
- **`thinking_budget=0`** 일관 적용 (비용 절감 목적)
- **모델 분포**: 대부분 `gemini-2.5-flash`, `regulatory_service.py`만 `gemini-2.0-flash-exp` (실험판)

---

## 4. 기타 의존성

### 4.1 FRED API ([macro/services/fred_client.py](macro/services/fred_client.py))

| 항목 | 상태 |
|-----|:----:|
| Rate Limiter 통합 | ✅ `get_rate_limiter("fred")` 사용 (100/min) |
| Transient 에러 (5xx) 재시도 | ✅ max_retries=3, exp backoff (2/4/6s) |
| Permanent 에러 (401/403/404) | ✅ 즉시 raise |
| Timeout | ✅ 30초 |
| 영향 범위 | macro Market Pulse, 거시지표, EOD pipeline `_fetch_fred_value` |

**평가**: ✅ 잘 설계됨. FRED 무료 한도(120/min) 내에서 안정적

### 4.2 Neo4j ([rag_analysis/services/neo4j_driver.py](rag_analysis/services/neo4j_driver.py))

| 항목 | 상태 |
|-----|:----:|
| Lazy singleton | ✅ 첫 호출 시 연결, 실패 시 None 반환 후 캐시 |
| Graceful Degradation | ✅ `driver is None` 시 빈 결과 + `_meta.source='fallback'` |
| Fork 안전 | ✅ `force_reset_after_fork()` (close 없이 None) |
| Query Timeout | ✅ 2000ms (`Neo4jServiceLite.QUERY_TIMEOUT`) |
| Connection Pool | ✅ `max_connection_lifetime=3600`, `pool_size=50` |
| 영향 범위 | Chain Sight 그래프 시각화, RAG 분석, news_neo4j_sync |

**평가**: ✅ 의존성 관리의 모범 사례. 다른 외부 API들도 이 패턴을 따라야 함.

### 4.3 SEC EDGAR ([sec_pipeline/collector.py](sec_pipeline/collector.py))

| 항목 | 상태 |
|-----|:----:|
| User-Agent | ⚠️ `'Stock-Vis stockvis@example.com'` placeholder — SEC 정책 위반 가능 |
| Rate Limit | ✅ 0.12초 sleep (10 req/sec) |
| 재시도 | ❌ 없음, `requests.exceptions.RequestException` 즉시 raise |
| Timeout | ✅ 30초 (submissions), 15초 (CIK) |
| CIK 캐시 | ✅ 클래스 레벨 dict (프로세스 단위) |
| Fallback | ❌ 실패 시 None 반환만 |

**핵심 위험**: 실제 운영 이메일이 아닌 `stockvis@example.com` 사용 시 SEC가 **장기적으로 차단**할 수 있음. SEC 가이드라인은 운영자 실제 이메일 요구.

### 4.4 Redis (Cache + Rate Limiter)

| 사용처 | 의존성 강도 | Fallback |
|-------|:----------:|---------|
| `api_request/rate_limiter.py` | 강 | ✅ Django Cache fallback (`AttributeError` 예외) |
| `news/services/circuit_breaker.py` | 강 | ❌ 캐시 실패 시 `record_failure` 실패만 로깅 |
| `serverless/services/fmp_client.py` (캐싱) | 중 | ❌ 캐시 미스 시 매번 API 재호출 |
| `serverless/services/keyword_data_collector.py` | 중 | — |
| Chain Sight 시드 (`SeedSnapshot` DB 영속화) | 약 | ✅ DB로 fallback (#27) |
| Beat schedule (DatabaseScheduler) | 강 | DB 영속화 |

**위험**:
- Redis 다운 → CircuitBreaker `is_open()` 항상 False 반환 → 차단 동작 안 함
- Rate Limiter는 Django LocMemCache로 fallback되지만 분산 환경에서 정확하지 않음

---

## 5. Circuit Breaker 후보

### 5.1 현재 상태

- **구현됨**: `news/services/circuit_breaker.py` (threshold=5, timeout=300s)
- **사용처**: `news/tasks.py`의 3개 태스크 (`collect_sp500_news_fmp_batch` 등)에서 `'fmp'` provider만
- **테스트**: `tests/unit/news/test_circuit_breaker.py` 존재
- **격차**: stocks, serverless, thesis, validation 영역에는 도입 안 됨

### 5.2 도입 우선순위

| 우선순위 | 호출지점 | provider | 근거 |
|:-------:|---------|:--------:|------|
| **P0 (긴급)** | `stocks/services/sp500_eod_service.py:sync_eod_prices` | fmp | S&P 500 503종목 × FMP profile + historical 호출. FMP 다운 시 503 × 2 = 1006회 무의미 호출 발생. 야간 핵심 파이프라인 |
| **P0** | `thesis/tasks/eod_pipeline.py:update_indicator_readings` | fmp + fred | 모든 indicator의 raw_value를 가져옴. FMP 다운 시 score 계산이 빈 데이터로 진행 |
| **P0** | `serverless/tasks.py:sync_daily_market_movers` | fmp | 매일 7:30 자동 실행. FMP 다운 시 Celery `retry 3회 × 5분` = 15분 동안 차단 효과 미미 |
| **P1 (권장)** | `serverless/services/keyword_service.py` (Market Movers 키워드) | gemini | 429 재시도는 있으나 Gemini 5분 장애 시 누적 비용 증가 |
| **P1** | `serverless/services/llm_relation_extractor.py` | gemini | 뉴스/SEC 배치 처리, 비용 민감 ($5/월 예산) |
| **P1** | `news/services/news_deep_analyzer.py` | gemini | Tier A/B/C 일일 50개. 4초 RPM 제한 + 단일 시도라 누적 실패 시 분석 결과 지속 누락 |
| **P2 (관찰)** | `sec_pipeline/collector.py` | sec_edgar | User-Agent 차단 시 즉시 감지 필요. 도메인별 차단 가능성 |
| **P2** | `validation/services/llm_peer_filter.py` | gemini | 사용자 트리거. 실패 시 사용자가 retry 가능 |
| **P3** | `macro/services/fmp_client.py` | fmp | 거시지표 — 일일 1회 정도, 누락 시 영향 작음 |
| **N/A** | Neo4j 모든 호출 | neo4j | 이미 graceful degradation 완비 |
| **N/A** | FRED 모든 호출 | fred | 이미 5xx 재시도 + graceful 부분 fallback |

### 5.3 통합 권고

#### A. CircuitBreaker 위치 이동
현재 `news/services/circuit_breaker.py`는 `news/` 도메인에 묶여 있음. 다른 앱이 사용하려면 `news`를 import해야 함 (도메인 경계 위반).
**제안**: `api_request/circuit_breaker.py` 또는 `shared_kb/` 인근으로 이동 → 모든 앱에서 공용 사용.

#### B. Provider별 통합 wrapper
```
api_request/
  fmp_safe_call.py  — FMPClient + RateLimiter + CircuitBreaker 단일 래퍼
  gemini_safe_call.py — genai.Client + 재시도 + CircuitBreaker 단일 래퍼
```
이를 통해 FMP 클라이언트 3종 분산 문제도 점진적 해소.

#### C. 모니터링 추가
- `serverless/services/admin_status_service.py`의 `_get_rate_limits()`에 CircuitBreaker 상태 추가
- Prometheus/CloudWatch 메트릭으로 circuit open 횟수 추적

#### D. Threshold/Timeout 조정 권장
- FMP: threshold=5 그대로, timeout=600s (10분, 일시적 글리치 흡수)
- Gemini: threshold=10 (재시도 로직과 중복 방지), timeout=300s
- SEC EDGAR: threshold=3 (User-Agent 차단 신호 빠르게), timeout=3600s (1시간)

---

## 6. 추가 발견 (참고)

### 6.1 Celery 태스크 retry 정책 일관성 부족

| 영역 | max_retries | retry_delay | 비고 |
|-----|:-----------:|-------------|------|
| `serverless/tasks.py` Market Movers | 3 | 5분 | ✅ 양호 |
| `news/tasks.py` 대부분 | 2 | 5~10분 | ✅ 양호 |
| `validation/tasks.py` | 1 | 5분 | ⚠️ 적음 |
| `sec_pipeline/tasks.py` | 1~5 (다양) | 60s exp backoff | 일부 5회까지 |
| `thesis/tasks/eod_pipeline.py` | **0** | — | ❌ 외부 API 의존 태스크인데 retry 없음 |
| `stocks/tasks.py` | shared_task만 (retry 없음) | — | aggregation only라 OK |

> `thesis/tasks/eod_pipeline.py`는 외부 API 의존도가 가장 높은데 Celery retry가 없음. 후속 step (`calculate_scores`)이 빈 데이터로 진행하지 않도록 재검토 필요.

### 6.2 캐시 키 일관성 이슈 가능

`common-bugs.md` #15 "캐시 키 불일치"가 이미 발견됨. 본 감사에서 추가로 발견:
- `serverless/services/fmp_client.py`의 캐시 키는 `'fmp:'` prefix
- `news/services/circuit_breaker.py`의 키는 `'circuit:fmp'`
- Rate limiter 키는 `'rate_limit:fmp:per_minute'`
모두 다른 namespace이며 운영 시 디버깅 시 혼동 가능 → 통합 prefix 가이드 필요.

### 6.3 단일 Provider Lock-in

FMP가 사실상 유일한 시장 데이터 공급자. Alpha Vantage 제거(`api_request/providers/factory.py:66` 주석)는 비용 절감이지만 **Disaster Recovery 관점에서는 위험**. Polygon.io / IEX Cloud 등 secondary provider를 fallback으로 두는 것을 검토할 만함.

### 6.4 FMPClient 중복으로 인한 Bug fix 산발

버그 #14 (FMP Key Metrics 필드명) 같은 수정이 발생하면 **3곳 모두 수정**해야 함. 현재 `api_request/providers/fmp/processor.py`만 정확하게 처리하고, 다른 클라이언트는 `quote.get('changesPercentage')` 같은 필드를 직접 다룸 — 필드명 변경 시 다중 장애 발생 위험.

---

## 7. 결론

본 감사는 다음 3가지 우선 조치를 권고한다:

1. **CircuitBreaker 일반화 + 핵심 야간 파이프라인 적용** (P0)
   - `api_request/circuit_breaker.py`로 이동
   - `sp500_eod_service`, `eod_pipeline`, `sync_daily_market_movers`에 즉시 적용

2. **Gemini 호출 통합 wrapper 도입** (P1)
   - `gemini_safe_call(prompt, max_retries=3, timeout=60)` 단일 진입점
   - 429 재시도 로직 단일화 (현재 2곳 → 전 호출지)

3. **FMPClient 단일화 로드맵** (P2)
   - 1단계: serverless/macro의 클라이언트가 `api_request/providers/fmp/client.py`를 위임
   - 2단계: 캐싱 레이어 분리 (FMPClient → CachedFMPClient 데코레이터)
   - 3단계: secondary provider 추가 검토

> 본 감사는 **읽기 전용**이며 코드 수정은 수행하지 않았다. 위 권고는 별도 PR/플랜으로 진행할 것을 제안한다.
