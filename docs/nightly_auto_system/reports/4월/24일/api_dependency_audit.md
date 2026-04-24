# 외부 API 의존성 감사 보고서

- **작성일**: 2026-04-24
- **범위**: FMP, Gemini, FRED, SEC EDGAR, Neo4j, Redis
- **모드**: 읽기 전용. 코드 수정 없음.
- **조사 파일 수**: FMP 계열 35개, Gemini 계열 22개, 기타(FRED/SEC/Neo4j/Redis) 약 15개

---

## 1. 의존성 매트릭스

서비스 도메인별로 외부 API 호출의 존재 여부, 에러 처리, Fallback, 장애 시 사용자 영향을 정리.

| 도메인 (앱) | FMP | Gemini | FRED | SEC EDGAR | Neo4j | Redis(cache) | Fallback 존재 | 장애 시 사용자 영향 |
|---|---|---|---|---|---|---|---|---|
| `stocks/` (tasks, services) | ✅ (핵심) | ❌ | ❌ | ❌ | ❌ | ✅ | 부분(yfinance 폴백 1곳) | 재무제표/가격 업데이트 실패 → EOD 파이프라인 중단 |
| `stocks/services/korean_overview_service.py` | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | 기업 개요 조회 실패 시 에러 전파 |
| `serverless/` (screener, chain sight) | ✅ (독립 client) | ✅ (다수) | ❌ | ✅ | ✅ | ✅ | ❌ | Screener/Chain Sight 카드 빈 응답 |
| `macro/` (market pulse) | ✅ (독립 client) | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | Market Pulse 대시보드 공백 |
| `news/` (providers, services) | ✅ | ✅ | ❌ | ❌ | ❌(간접) | ✅ | 부분(Circuit Breaker 존재) | 뉴스 피드 빈 응답 / 인사이트 실패 |
| `rag_analysis/` (LLM 서비스) | ❌ | ✅ (핵심) | ❌ | ❌ | ✅ | ✅ | 부분(PostgreSQL 폴백) | 분석 응답 실패 또는 부분 결과 |
| `thesis/` (가설 통제실) | ✅ (EOD) | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | 가설 빌더 대화 중단, 지표 매칭 실패 |
| `validation/` (1차 검증) | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | Peer LLM 필터 실패 시 기본 Peer 반환(소프트 폴백) |
| `chainsight/` (기업 프로파일) | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 부분(neo4j_dirty 플래그) | Neo4j 다운 시 동기화 스킵, PG만으로 부분 동작 |
| `sec_pipeline/` (10-K) | ❌ | ✅ | ❌ | ✅ (핵심) | ❌ | ✅ | ❌ | 10-K 공급망/사업모델 수집 실패 |

**요약 관찰**:
- `stocks/`, `serverless/`, `macro/`는 **각자 FMP 클라이언트를 독립 구현**(3종) → 에러 처리 불일치.
- `rag_analysis/`, `thesis/`, `serverless/`, `news/`, `sec_pipeline/`, `validation/`의 LLM 호출은 **중앙 LLM 서비스 통합 미완**. 대부분 `genai.Client`를 직접 생성.
- 전역 Circuit Breaker는 `news/services/circuit_breaker.py` **1곳에만 구현**되어 있고 FMP/AlphaVantage 일부에만 적용. Gemini 미적용.

---

## 2. FMP 상세

### 2.1 클라이언트 중앙 집중화 부재

동일 FMP API를 호출하는 클라이언트가 **3개 공존**:

| 클라이언트 | 위치 | 특이사항 |
|---|---|---|
| 정규 클라이언트 | `api_request/providers/fmp/client.py` | 401/402/403/429 분기, 지수 백오프, `FMPPremiumError`/`FMPRateLimitError` 정의 |
| serverless 전용 | `serverless/services/fmp_client.py` | `HTTPStatusError` → `FMPAPIError`로 일괄 래핑. 402/429 구분 없음 |
| macro 전용 | `macro/services/fmp_client.py` | 자체 Rate Limiter 내장, 하지만 402 처리 없음 |

**영향**: serverless/macro 경로에서는
- `.` 포함 심볼 필터링이 일관되지 않아 402가 반복 발생
- 429를 일반 예외로 처리 → 재시도 로직 미작동
- Rate Limit 상태가 3개 클라이언트 간 공유되지 않아 멀티프로세스 Celery에서 race condition 가능

### 2.2 파일별 에러 핸들링 요약

| 파일 | try/except | 재시도 | Fallback | Rate Limit | 402 처리 | 타임아웃 | 영향 |
|---|---|---|---|---|---|---|---|
| `api_request/providers/fmp/client.py` | ✅ | ✅ 지수 백오프 | ❌ | ✅ 내부 sleep | ✅ 즉시 raise | 30초 | 상위 레이어로 전파 |
| `api_request/providers/fmp/provider.py` | ✅ | ❌ | ❌ | ❌ | ✅ (balance/income/cash만) | 30초 | `error_response` 반환 |
| `api_request/stock_service.py` (팩토리) | ✅ | ❌ | ✅ Provider 전환 | ❌ | ❌ | 30초 | `error_response` |
| `stocks/tasks.py::update_financials_with_provider` | ❌ | Celery retry만 | ❌ | ❌ | ❌ | 30초 | 전체 태스크 실패 |
| `stocks/services/sp500_service.py::sync_constituents` | ❌ | ❌ | ❌ | ❌ | 부분(`.` 심볼 스킵 로직만) | 30초 | 빈 응답/무조치 |
| `stocks/services/financial_statements_fallback.py` | ✅ | ❌ | ✅ FMP→yfinance | ❌ | ❌ | - | 빈 결과 가능 |
| `stocks/services/fmp_screener.py` | ✅ | ❌ | ❌ | ✅(stocks rate_limiter) | ❌ | 30초 | 빈 응답 |
| `stocks/services/fmp_market_movers.py` | ✅ | ❌ | ❌ | ✅ | ❌ | 30초 | 빈 응답 |
| `stocks/services/rate_limiter.py` | ✅ | - | - | ✅ Redis 분산 | - | - | 캐시 장애 시 sleep 폴백 |
| `serverless/services/fmp_client.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | `FMPAPIError` raise |
| `serverless/services/data_sync.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | 로그 + 스킵 |
| `serverless/services/chain_sight_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | 부분 데이터 |
| `serverless/services/enhanced_screener_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | 빈 리스트 |
| `serverless/services/sector_heatmap_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | 빈 응답 |
| `serverless/services/market_breadth_service.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | 빈 응답 |
| `serverless/services/keyword_data_collector.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | 로그 |
| `serverless/services/cusip_mapper.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | None 반환 |
| `serverless/services/quote_enricher.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | 부분 데이터 |
| `macro/services/fmp_client.py` | ✅ | ❌ | ❌ | ✅ 내부 | ❌ | 30초 | Exception raise |
| `macro/services/macro_service.py` | ✅ | ❌ | ❌ | - | - | - | 에러 전파 |
| `news/providers/fmp.py` | ✅ | ✅ tenacity | ❌ | ✅ (Circuit Breaker 경로) | ❌ | 30초 | Circuit open 시 스킵 |
| `news/services/aggregator.py` | ✅ | ❌ | ✅ 다른 프로바이더 | - | - | - | 다른 소스로 대체 |
| `thesis/tasks/eod_pipeline.py` | ✅ | Celery retry | ❌ | ❌ | ❌ | 30초 | 파이프라인 재시도 |
| `users/utils.py` | ✅ | ❌ | ❌ | ❌ | ❌ | 30초 | 에러 메시지 반환 |

### 2.3 FMP 핵심 약점 5개

1. **클라이언트 3종 분산** — 에러 시맨틱/Rate Limit/402 처리가 서로 다름. serverless/macro 계층의 호출은 402를 일반 `FMPAPIError`로 일괄 래핑해 원래 상태 코드가 손실됨.
2. **402 Premium 처리 비일관** — `api_request/providers/fmp/provider.py`의 financial statements 3메서드에만 `FMPPremiumError` 분기가 있고 그 외 엔드포인트(프로필, 스크리너, ETF holdings 등)는 402를 에러로만 카운트.
3. **`.` 포함 심볼 필터링 산발적** — `SP500Service.sync_constituents()`만 `.` 스킵 로직을 가짐. 다른 배치 경로(screener, chain sight)는 필터링 없이 402를 반복 유발.
4. **Tasks 레이어의 try/except 부재** — `stocks/tasks.py::update_financials_with_provider`, `update_stock_with_provider`는 FMP 호출을 직접 수행하면서 자체 에러 처리를 하지 않아, 일시적 429/502에서도 태스크 전체가 실패하고 Celery `max_retries=3`를 그대로 소진.
5. **Rate Limiter 이중화** — `api_request/rate_limiter.py`(Redis 분산)와 `api_request/providers/fmp/client.py`의 내부 `time.sleep()`, `macro/services/fmp_client.py`의 자체 limiter가 병존. 분산 락이 공유되지 않아 실제 **5 calls/min**(Free) 또는 **300 calls/min**(Starter) 기준을 넘을 수 있음.

### 2.4 상세 권장사항 (구현은 본 감사 범위 외)

- `api_request/providers/fmp/client.py`를 유일한 HTTP 레이어로 승격하고, serverless/macro는 이를 import하여 사용.
- `FMPPremiumError` 분기를 Provider의 모든 메서드 + serverless/macro 클라이언트에 일괄 추가.
- `stocks/tasks.py`에 `FMPPremiumError`/`FMPRateLimitError`별 Celery retry 정책(429 → countdown=60, 402 → retry 안 함) 적용.

---

## 3. Gemini 상세

### 3.1 호출 지점 22개 — 중앙 서비스 통합 미완

대부분의 파일이 `genai.Client` 또는 `GenerativeModel`을 **직접 생성**. 단일 래퍼(예: `rag_analysis/services/llm_service.py`)는 존재하지만 다른 앱은 이를 재사용하지 않음.

### 3.2 파일별 요약

| 파일 | 모델 | 429 감지 | 재시도 | JSON 파싱 | 응답 빈 검증 | 타임아웃 | 영향 |
|---|---|---|---|---|---|---|---|
| `rag_analysis/services/llm_service.py` | 2.5 flash | ✅ 명시 | ✅ 3회 지수 | ✅ ```json``` 제거 | ✅ | 기본 | 폴백 후 전파 |
| `rag_analysis/services/adaptive_llm_service.py` | 제공자별 | ❌ generic | ❌ | - | ✅ | 기본 | 에러 전파 |
| `rag_analysis/services/entity_extractor.py` | 2.5 flash | ❌ | ❌ | ✅ `_clean_json_response` | 부분 | 기본 | 빈 엔티티 |
| `rag_analysis/services/context_compressor.py` | 2.5 flash | ❌ | ❌ | - | 부분 | 기본 | `asyncio.gather(..., return_exceptions=True)`로 실패 흡수 |
| `serverless/services/thesis_builder.py` | 2.5 flash | ❌ | ❌ | ✅ regex | 부분 | 기본 | 제안 생성 실패 |
| `serverless/services/prompt_builder.py` | 2.5 flash | ❌ | ❌ | ✅ regex | 부분 | 기본 | 실패 |
| `serverless/services/keyword_generator.py` / `_v2.py` | 2.5 flash | ❌ | ❌ | ✅ | ❌ | 기본 | 부분 결과로 DB 기록 (나머지 NIL) |
| `serverless/services/keyword_service.py` | 2.5 flash | ❌ | ❌ | ✅ | ❌ | 기본 | 로그만 |
| `serverless/services/llm_relation_extractor.py` | 2.5 flash | ❌ | ❌ | ✅ | 부분 | 기본 | 배치 전체 스킵 가능 |
| `serverless/services/regulatory_service.py` | 2.5 flash | ❌ | ❌ | ❌ | ❌ | 기본 | lazy init 실패 시 None |
| `serverless/services/relationship_keyword_enricher.py` | 2.5 flash | ❌ | ❌ | ✅ | ❌ | 기본 | 부분 실패 후 진행 |
| `serverless/services/csv_url_resolver.py` | 2.5 flash | ❌ | ❌ | ✅ | ❌ | 기본 | None |
| `news/services/keyword_extractor.py` | 2.5 flash | ❌ | ❌ | ✅ | ❌ | 기본 | 빈 키워드 |
| `news/services/news_deep_analyzer.py` | 2.5 flash | ❌ | ❌ | ✅ | 부분 | 기본 | 분석 실패 |
| `news/services/stock_insights.py` | 2.5 flash | ❌ | ❌ | ✅ | 부분 | 기본 | 인사이트 공백 |
| `news/api/views.py` | 2.5 flash | ❌ | ❌ | - | 부분 | 기본 | API 500 가능 |
| `thesis/services/thesis_builder.py` | 2.5 flash | ❌ | ❌ | ✅ regex | 부분 | 기본 | 대화 응답 지연/실패 |
| `thesis/services/prompt_builder.py` | 2.5 flash | ❌ | ❌ | ✅ regex | 부분 | 기본 | - |
| `thesis/services/indicator_matcher.py` | 2.5 flash | ❌ | ❌ | ✅ | 부분 | 기본 | 매칭 실패 |
| `thesis/views/conversation_views.py` | 2.5 flash | ❌ | ❌ | - | 부분 | 기본 | - |
| `sec_pipeline/intelligence.py` / `extractor.py` | 2.5 flash | ❌ | ❌ | ✅ | 부분 | 기본 | 10-K 파싱 실패 |
| `validation/services/llm_peer_filter.py` | 2.5 flash | ❌ | ❌ | ✅ | 부분 | 기본 | 기본 Peer로 폴백(소프트) |
| `stocks/services/korean_overview_service.py` | 2.5 flash | ❌ | ❌ | - | ❌ | 기본 | 에러 전파 |

### 3.3 Gemini 핵심 약점 4개

1. **429 Rate Limit 구분 부재** — `rag_analysis/services/llm_service.py` 1곳만 429를 감지해 지수 백오프. 나머지 21개는 모든 예외를 `Exception`으로 일괄 catch → 1500 RPD 초과 시 `bare except`가 재시도 없이 실패를 삼킴.
2. **JSON 파싱 유틸 중복** — `_clean_json_response`/`regex ```json``` 제거` 로직이 최소 6개 파일에 중복. 파싱 실패 시 기본값 반환 패턴이 일관되지 않음(어떤 곳은 `{}`, 어떤 곳은 raise).
3. **Celery 배경 작업의 부분 실패 누적** — `keyword_generator`, `relationship_keyword_enricher`, `regulatory_service`는 배치 루프 내부에서 `try/except Exception: log; continue` 패턴을 사용 → 성공한 항목만 DB에 커밋되고 나머지는 **영구 누락**(NIL). 재실행 트리거가 없음.
4. **타임아웃 명시 부재** — 거의 모든 호출이 SDK 기본값에 의존. 긴 컨텍스트(RAG Phase 3) 응답이 90~120초 이상 소요될 때 상위 API가 먼저 타임아웃될 가능성.

### 3.4 CLAUDE.md 규칙 준수 현황

- **"Celery에서 async LLM 호출 금지"**: `rag_analysis/services/context_compressor.py`는 `asyncio.gather`를 사용하지만 Django ORM 컨텍스트에서만 호출 → Celery 태스크 내부 호출 여부는 `rag_analysis/tasks.py`를 재확인 필요. 본 감사에서는 파일 목록만 확인했으며 규칙 위반 여부는 미확정.

---

## 4. 기타 의존성

### 4.1 FRED (`macro/`)
- `macro/services/fred_client.py`: 5XX transient 감지, 지수 백오프 3회. 4XX는 즉시 예외 전파.
- `macro/services/macro_service.py`: 특정 지표 실패 시 다른 지표는 계속 수집. **Fallback 없음** — 장애가 길어지면 Market Pulse 대시보드 공백.
- **장애 시나리오**: FRED 전체 다운 → Market Pulse 지표 중 FRED 의존 카드(금리, 실업률 등) 빈 응답.

### 4.2 SEC EDGAR (`sec_pipeline/`, `api_request/sec_edgar_client.py`)
- `sec_edgar_client.py`: User-Agent 강제, 10req/sec 제한 준수, 0.1초 간격 내부 sleep.
- `sec_pipeline/collector.py`: 개별 10-K 수집 실패 시 로그 후 다음으로 진행.
- `sec_pipeline/exceptions.py`: `SECRateLimitError`, `SECFilingNotFoundError` 정의.
- **장애 시나리오**: SEC 502/503 반복 시 재시도 3회 후 태스크 실패, 해당 분기 10-K만 미수집. Chain Sight 공급망 카드는 **이전 분기 데이터로 대체**(DB에 남아있음).

### 4.3 Neo4j (`rag_analysis/services/neo4j_*`, `chainsight/tasks/`, `serverless/services/neo4j_chain_sight_service.py`)
- `rag_analysis/services/neo4j_driver.py`: Lazy init, `verify_connectivity()` 실패 시 `None` 반환.
- `chainsight/tasks/sync_tasks.py`: `neo4j_dirty` 플래그 기반. Neo4j 다운 시 PostgreSQL만 업데이트하고 dirty 플래그 설정 → 복구 후 재동기화.
- **장애 시나리오**: Neo4j 전체 다운 → Chain Sight 그래프 탐색/경로 API 실패. 기업 프로파일 기본 데이터(PG)만 조회 가능. 단기 degraded mode 동작함.
- **잠재 위험**: 쿼리 타임아웃 기본 60초 → 프론트엔드가 먼저 타임아웃, 사용자 경험 악화.

### 4.4 Redis / Django cache
- `config/settings.py`: `django_redis.cache.RedisCache` 사용.
- `api_request/cache/decorators.py`: `cache.get` 실패 시 백엔드 API 직접 호출(자동 폴백).
- `stocks/cache_utils.py`: 동일 패턴.
- **장애 시나리오**: Redis 다운 → 캐시 미스 폭주 → FMP/Gemini 호출 급증 → Rate Limit 초과 → 2차 장애. **Redis 장애는 Gemini/FMP 장애로 전이될 수 있음.**
- **추가 위험**: `stocks/services/rate_limiter.py`도 Redis에 의존. Redis 다운 시 Rate Limiter 자체가 무력화되어 외부 API 호출이 무제한으로 발생할 수 있음.

### 4.5 Circuit Breaker 현황
- **존재**: `news/services/circuit_breaker.py`. Redis 기반, provider별 격리. FMP, Alpha Vantage의 news 프로바이더에만 적용.
- **부재**: Gemini, Neo4j, FRED, SEC EDGAR, 그리고 news 이외의 FMP 호출 경로(stocks, serverless, macro).

---

## 5. Circuit Breaker 후보

우선순위는 "장애 시 사용자 노출 + 전이 위험 + 재시도 무용성" 기준.

### 🔴 최우선 (즉시 도입 권장)

| # | 지점 | 이유 |
|---|---|---|
| 1 | **Gemini 호출 전반** (중앙 래퍼에 적용) | 429 미구분 + JSON 파싱 실패 + Celery 배치 부분 실패. RAG/키워드/관계/가설 대화 전체가 Cascading. 재시도가 429 상황을 악화시킬 수 있음. |
| 2 | **`api_request/providers/fmp/client.py`** | 재시도 로직은 있으나 402는 재시도 무용. 401/403/402 즉시 open 상태로 전환하고 TTL 동안 호출 차단. |
| 3 | **`serverless/services/fmp_client.py`, `macro/services/fmp_client.py`** | 독립 클라이언트. 402/429 무구분 → 장애 시 호출량 증폭. |
| 4 | **`stocks/services/rate_limiter.py` → Redis 의존** | Redis 다운 시 외부 API 무제한 호출 위험. Redis 장애 시 fail-closed(안전 실패) 폴백 필요. |

### 🟠 높음

| # | 지점 | 이유 |
|---|---|---|
| 5 | `rag_analysis/services/neo4j_service.py` 쿼리 | Neo4j 타임아웃 60초 → 프론트 UX 저하. Circuit open 시 PG 전용 응답. |
| 6 | `serverless/services/llm_relation_extractor.py` | 배치 전체 실패 시 전 뉴스에 관계 미추출. Circuit open → 규칙 기반 대체 or 큐 이동. |
| 7 | `thesis/services/thesis_builder.py`, `thesis/services/indicator_matcher.py` | 대화형 API 응답 지연 → 사용자 이탈. 실패 시 "지표 직접 선택" UX로 전환. |
| 8 | `macro/services/fred_client.py` | FRED 반복 장애 시 Market Pulse 카드 공백. 직전 캐시 재사용 권장. |

### 🟡 중간

| # | 지점 | 이유 |
|---|---|---|
| 9 | `sec_pipeline/collector.py` | 배경 작업이라 즉각 영향은 낮으나 rate limit 위반 시 IP 차단 위험. |
| 10 | `news/services/keyword_extractor.py`, `stock_insights.py` | Gemini 전역 Circuit Breaker로 흡수 가능. |
| 11 | `serverless/services/regulatory_service.py` | lazy init 실패 시 영구 미동작. 헬스 체크 필요. |

---

## 6. 종합 평가

| 항목 | 상태 | 비고 |
|---|---|---|
| 외부 API 에러 핸들링 일관성 | ⚠️ 부분적 | FMP 클라이언트 3종, Gemini 래퍼 미통합 |
| 재시도 정책 | ⚠️ 불일치 | 일부만 지수 백오프, 대부분 Celery `max_retries=3`에만 의존 |
| Rate Limit 준수 | ⚠️ 위험 | Redis 의존 + 이중화 → 멀티프로세스에서 초과 가능 |
| Fallback / Graceful Degradation | ⚠️ 부족 | `financial_statements_fallback`(yfinance), `chainsight neo4j_dirty`, `news/circuit_breaker`만 존재 |
| Circuit Breaker 도입률 | ❌ 낮음 | news/FMP 일부에만 존재, Gemini/Neo4j/FRED/SEC 미적용 |
| 모니터링 | ❓ 미확인 | 본 감사 범위 외 (별도 관측성 감사 필요) |

**핵심 위험 Top 3**
1. **Redis 장애 → FMP/Gemini 호출 폭주** (Rate Limiter + 캐시 모두 Redis 의존) — **가장 전이 위험 큰 단일 실패 지점**.
2. **Gemini 429/JSON 파싱 실패 → RAG·뉴스·가설·키워드 Cascading 부분 실패** (22개 지점에서 개별 처리).
3. **FMP 클라이언트 3종 분산 → 402/429 처리 불일치** (Starter 300 calls/min 기준도 보장되지 않음).

**즉시 검토 권고**
- Gemini 중앙 래퍼를 `rag_analysis/services/llm_service.py` 수준으로 승격 후 22개 호출 지점을 migration.
- FMP 클라이언트 단일화(`api_request/providers/fmp/client.py`).
- Redis 장애 시 Rate Limiter fail-closed 정책 정의.
- Circuit Breaker를 Gemini/Neo4j/FRED/SEC/FMP 전 경로로 확장 (기존 `news/services/circuit_breaker.py` 재사용).

---

*본 보고서는 읽기 전용 감사이며 코드 변경을 포함하지 않습니다. 실제 개선 작업은 별도 plan/implementation 세션에서 진행 권장.*
