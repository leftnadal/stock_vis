# 외부 API 의존성 감사 보고서

> **감사일**: 2026-04-21
> **감사자**: Claude (읽기 전용 감사)
> **기준 브랜치**: `portfolio` (커밋 `054fe3f` 기준)
> **직전 감사**: `docs/architecture/api_dependency_audit.md` (2026-04-14)
> **감사 파일 수**: FMP 호출 28개 (src), Gemini 호출 24개 (src), 기타 외부 의존성 67+개
> **변경 요약**: chainsight Phase 6~7 API 7개 추가 (신규 외부 의존성 없음), SEC EDGAR timeout 해결, FMP/Gemini Circuit Breaker 여전히 미도입

---

## 0. 직전 감사 대비 변경사항 (2026-04-14 → 2026-04-21)

| 영역 | 변경 내용 | 리스크 영향 |
|---|---|---|
| **chainsight Phase 6** | `chainsight/services/recheck_service.py`, `expand_service.py`, `alternatives_service.py`, `views/watchlist_views.py` 신규 추가 | Neo4j + Postgres만 사용 (외부 API 호출 **없음**) — 신규 리스크 없음 |
| **chainsight Phase 7** | `chainsight/models/saved_path.py`, `serializers/path_watchlist.py`, 마이그레이션 0006 추가 | 로컬 DB만 사용 — 신규 리스크 없음 |
| **SEC EDGAR** | `sec_pipeline/collector.py:86` — `requests.get(url, headers=SEC_HEADERS, timeout=30)` 적용 확인 | 직전 감사 **M1 해결됨** (Timeout 미설정) |
| **portfolio 설계 문서** | `docs/portfolio/*` 추가 (미구현) | 현재 코드에 영향 없음 |
| **FMP/Gemini Circuit Breaker** | 변경 없음 | 직전 **H4 미해결** |
| **Gemini 공통 retry 래퍼** | 변경 없음 | 직전 **H1 미해결** |
| **Gemini timeout 설정** | 변경 없음 | 직전 **H2 미해결** |
| **FMP 402 서비스 계층 분기** | 변경 없음 | 직전 **H3 미해결** |

**결론**: 지난 1주일 간 핵심 외부 API 장애 방어 취약점(Circuit Breaker, Gemini retry/timeout, FMP 402 서비스 계층)은 개선되지 않음. 신규 기능(chainsight Phase 6~7)은 외부 API에 의존하지 않아 신규 의존성 리스크는 발생하지 않음.

---

## 1. 의존성 매트릭스

### 1.1 서비스별 외부 API × Fallback 유무

| 앱 / 서비스 | FMP | Gemini | FRED | Neo4j | SEC EDGAR | Alpha Vantage | Finnhub | MarketAux | Redis |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **stocks** (주가/재무) | O | O | - | - | - | - | - | - | O(캐시) |
| **serverless** (Movers/Screener/ChainSight DNA) | O | O | - | O | - | - | - | - | O(캐시) |
| **macro** (Market Pulse) | O | - | O | - | - | - | - | - | O(캐시) |
| **news** (뉴스 인사이트) | O | O | - | - | - | O | O | O | O(캐시+CB) |
| **thesis** (가설 통제실) | O | O | - | - | - | - | - | - | O(캐시) |
| **rag_analysis** (RAG 분석) | - | O | - | O | - | - | - | - | O(캐시) |
| **validation** (1차 검증) | - | O | - | - | - | - | - | - | - |
| **chainsight v2** (기업 프로파일 + Phase 6~7) | - | - | - | O | - | - | - | - | - |
| **sec_pipeline** (SEC 파이프라인) | - | O | - | - | O | - | - | - | - |
| **metrics** (지표 메타데이터) | O | - | - | - | - | - | - | - | O(캐시) |

> *chainsight v2 Phase 6~7* (SavedPath/Recheck/Expand/Alternatives)은 Neo4j 그래프 조회 + 로컬 Postgres만 사용.

### 1.2 Fallback 유무 요약 (2026-04-21 기준)

| 외부 의존성 | 호출 파일 수 (src) | Fallback 있음 | Fallback 없음 | Fallback 비율 |
|---|---:|---:|---:|---:|
| FMP | 28 | 19 | 9 | 68% |
| Gemini | 24 | 16 | 8 | 67% |
| FRED | 3 | 2 (기본값 반환) | 1 | 67% |
| Neo4j | 60+ | 60+ (lazy init) | 0 | ~100% |
| SEC EDGAR | 3 | 0 | 3 | 0% |
| Alpha Vantage | 3 | 1 (aggregator 다음 provider 전환) | 2 | 33% |
| Finnhub | 2 | 1 (aggregator 다음 provider 전환) | 1 | 50% |
| MarketAux | 2 | 1 (aggregator 최종 provider — fallback 없음) | 1 | 50% |

> 파일 수가 직전 감사 대비 늘어난 이유: 테스트/스크립트 제외 후 `grep -rl` 기준 src 트리 전체를 재집계 (28 vs 18). 로직 변경이 아닌 집계 기준 정리.

---

## 2. FMP 상세

### 2.1 핵심 클라이언트 계층 (재검증)

#### `api_request/providers/fmp/client.py` — 평가: **EXCELLENT** (변동 없음)
- **엔드포인트**: 16개 (`/stable/*` 전용)
- **예외 계층**: `FMPClientError`/`FMPRateLimitError`/`FMPAuthError`/`FMPPremiumError` (L20-37)
- **Rate Limit**: 요청 간 `request_delay=0.2s` (L104-107) + 일일 `daily_limit=10000` 카운터 (L110-112)
- **재시도**: 지수 백오프 `wait_time = (attempt + 1) * 2` (L151-159), terminal error는 즉시 전파 (L149)
- **Timeout**: `requests.get(..., timeout=30)` (L121)
- **위험도**: **LOW**

#### `api_request/providers/fmp/provider.py` — 평가: **GOOD** (변동 없음)
- `FMPRateLimitError` → `RateLimitError`로 변환 (L86-87, 123-124, 169-170, 208-209, 254-255, 300-301, 346-347)
- `FMPPremiumError` → `"PREMIUM_ONLY"` 코드 에러 응답 반환 (L247-253, 293-299, 339-345) — **3개 재무제표 엔드포인트에서만 처리**
- `get_quote`/`get_company_profile`/`get_daily_prices`/`search_symbols`/`get_sector_performance`에는 402 분기 **없음** (일반 `Exception` 흡수)

### 2.2 서비스 계층 상세 (28개 파일)

| 파일 | 에러 핸들링 | FMPPremiumError (402) | Rate Limit | Fallback | 위험도 |
|---|---|---|---|---|---|
| `api_request/providers/fmp/client.py` | EXCELLENT | **HANDLED** | EXCELLENT (0.2s + daily counter) | N/A (기반) | LOW |
| `api_request/providers/fmp/provider.py` | GOOD | **PARTIAL** (3/9 메서드) | Via client | YES (에러 응답) | LOW-MEDIUM |
| `api_request/stock_service.py` | GOOD | **NOT HANDLED** | Via provider | YES (다음 provider) | LOW |
| `macro/services/fmp_client.py` | BASIC | **NOT HANDLED** | BASIC (0.5s sleep) | PARTIAL (None/빈 dict) | **MEDIUM** |
| `macro/services/macro_service.py` | BASIC | **NOT HANDLED** | Via client | YES (빈 dict) | MEDIUM |
| `serverless/services/fmp_client.py` | GOOD | **NOT HANDLED** | BASIC (캐시 5분~24시간) | YES (캐시 + datahub.io CSV) | MEDIUM |
| `serverless/services/enhanced_screener_service.py` | GOOD | **NOT HANDLED** | GOOD (1h 캐시, 배치 20개 제한) | YES (캐시) | LOW-MEDIUM |
| `serverless/services/market_breadth_service.py` | GOOD | **NOT HANDLED** | BASIC (5분 캐시) | NO (빈 결과만) | **MEDIUM** |
| `serverless/services/sector_heatmap_service.py` | GOOD | **NOT HANDLED** | BASIC (5분 캐시) | PARTIAL (섹터별 스킵) | MEDIUM |
| `serverless/services/chain_sight_service.py` | GOOD | **NOT HANDLED** | GOOD (1h 캐시) | YES (빈 결과) | LOW-MEDIUM |
| `serverless/services/data_sync.py` | BASIC-GOOD | **NOT HANDLED** | BASIC | PARTIAL (심볼별 스킵) | MEDIUM |
| `serverless/services/filter_engine.py` | GOOD | **NOT HANDLED** | BASIC (캐시) | PARTIAL | MEDIUM |
| `serverless/services/keyword_data_collector.py` | GOOD | **NOT HANDLED** | BASIC | PARTIAL | MEDIUM |
| `serverless/services/cusip_mapper.py` | BASIC | **NOT HANDLED** | BASIC | PARTIAL | MEDIUM |
| `serverless/services/neo4j_chain_sight_service.py` | GOOD | **NOT HANDLED** | Via service | YES (empty) | LOW |
| `stocks/tasks.py` | GOOD | **NOT HANDLED** | Via provider | YES (재시도) | MEDIUM |
| `stocks/services/sp500_service.py` | BASIC | **NOT HANDLED** | N/A | NO | **HIGH** |
| `stocks/services/sp500_eod_service.py` | GOOD | **NOT HANDLED** | GOOD (0.3s 쓰로틀) | YES (심볼별 스킵) | LOW-MEDIUM |
| `stocks/services/fmp_fundamentals.py` | GOOD | **NOT HANDLED** | GOOD (10분 캐시) | YES (캐시) | LOW-MEDIUM |
| `news/providers/fmp.py` | GOOD | **NOT HANDLED** | BASIC | YES (빈 리스트) | LOW-MEDIUM |
| `news/services/aggregator.py` | GOOD | N/A (provider 경유) | N/A | YES (FMP 없이 계속) | LOW |
| `thesis/tasks/eod_pipeline.py` | GOOD | **HANDLED** | BASIC | YES (None 반환) | LOW |
| `thesis/views/monitoring_views.py` | GOOD | **HANDLED** | BASIC | YES (DB 폴백) | LOW |
| `serverless/tasks.py` | GOOD | **NOT HANDLED** | BASIC | NO (재시도) | MEDIUM |
| `serverless/views.py` | GOOD | Via service | N/A | YES | LOW |
| `users/utils.py` | BASIC | **NOT HANDLED** | N/A | YES | LOW |
| `api_request/__init__.py` | N/A (re-export) | N/A | N/A | N/A | LOW |

### 2.3 FMP 핵심 발견사항 (재검증 요약)

**강점** (직전 감사와 동일)
- 코어 클라이언트(`client.py`)의 커스텀 예외 계층 + 지수 백오프 재시도
- 광범위한 캐싱 (5분 ~ 24시간 TTL)
- 대부분 서비스에서 에러 시 빈 결과 반환 → graceful degradation

**취약점** (미해결 4건)

| # | 취약점 | 영향 파일 수 | 심각도 | 상태 |
|---|---|---:|---|---|
| F1 | **FMPPremiumError(402) 미처리** — 14개 파일에서 generic exception으로 흡수 | 14 | HIGH | 미해결 |
| F2 | **Rate limit 처리 불일관** — 코어는 daily counter, macro/fmp_client는 미추적 | 5 | MEDIUM | 미해결 |
| F3 | **Silent failure** — market_breadth, sp500_service 등 빈 결과만 반환 | 3 | MEDIUM | 미해결 |
| F4 | **Celery 재시도 시 API 과부하 위험** — `serverless/tasks.py` retry_delay=300s, 지수 아님 | 1 | MEDIUM | 미해결 |
| F5 | **캐시 TTL 비일관** — 5분 vs 1시간 vs 24시간 전략 부재 | 전체 | LOW | 미해결 |

---

## 3. Gemini 상세

### 3.1 호출 현황 요약 (2026-04-21)

- **총 호출 파일** (src): 24개 (테스트/스크립트 제외 기준)
- **총 `genai.Client(...)` 지점**: 40+개 (thesis/services 내 다수 포함 — `indicator_matcher`, `prompt_builder` 3곳, `thesis_builder`, `conversation_views`)
- **사용 모델**: `gemini-2.5-flash`
- **Free Tier 한도**: 15 RPM, 1,500 RPD

### 3.2 서비스별 상세

| 파일 | 용도 | 에러 핸들링 | 429 처리 | JSON 파싱 안전 | Timeout | Sync/Async | Fallback | 위험도 |
|---|---|---|---|---|---|---|---|---|
| `validation/services/llm_peer_filter.py` | NL→필터 변환 | BASIC | **NOT HANDLED** | SAFE (L86 `json.loads`) | **NOT SET** | SYNC | YES (에러 dict L89) | MEDIUM |
| `thesis/views/conversation_views.py` | 뉴스→한국어 이슈 | BASIC | **NOT HANDLED** | SAFE | **NOT SET** | SYNC | YES (`_fallback_issues` L226) | LOW |
| `thesis/services/thesis_builder.py` | 자유입력 파싱 | BASIC | **NOT HANDLED** | SAFE (regex+`json.loads`) | **NOT SET** | SYNC | YES (`_fallback_parse` L429) | MEDIUM |
| `thesis/services/prompt_builder.py` | 빌더 대화 3회 분리 호출 (L542, L765, L943) | BASIC | **NOT HANDLED** | DEPENDS | **NOT SET** | SYNC | PARTIAL (None 반환) | MEDIUM |
| `thesis/services/indicator_matcher.py` | 전제→지표 매칭 | BASIC | **NOT HANDLED** | DEPENDS | **NOT SET** | SYNC | YES ([] 반환) | LOW-MEDIUM |
| `sec_pipeline/extractor.py` | 10-K 공급망/사업모델 추출 | GOOD | **NOT HANDLED** | GOOD (`JSONDecodeError`) | **NOT SET** | SYNC | PARTIAL (re-raise) | MEDIUM |
| `sec_pipeline/intelligence.py` | 파이프라인 헬스 리포트 | BASIC | **NOT HANDLED** | SAFE | **NOT SET** | SYNC | YES (기본 에러 리포트) | LOW |
| `news/services/keyword_extractor.py` | 일일 키워드 추출 | GOOD | **NOT HANDLED** | GOOD | **NOT SET** | BOTH | YES (failed DB 상태) | LOW-MEDIUM |
| `news/services/news_deep_analyzer.py` | 뉴스 심층 분석 (최대 50건) | BASIC | **NOT HANDLED** | UNKNOWN | **NOT SET** | SYNC | YES (None, 다음 기사로) | MEDIUM |
| `news/services/stock_insights.py` | 키워드 한국어 번역 | BASIC | **NOT HANDLED** | UNKNOWN | **NOT SET** | SYNC | PARTIAL | MEDIUM |
| `news/api/views.py` | 뉴스 키워드 생성 View | BASIC | **NOT HANDLED** | UNKNOWN | **NOT SET** | SYNC | YES (에러 response) | MEDIUM |
| `rag_analysis/services/llm_service.py` | 스트리밍 투자 분석 | **EXCELLENT** | **HANDLED** (L35 지수 백오프 `[1, 2, 4]`) | N/A (스트리밍) | **NOT SET** | ASYNC | YES (에러 이벤트) | **LOW** |
| `rag_analysis/services/context_compressor.py` | 문서 압축 | GOOD | **NOT HANDLED** | N/A | **NOT SET** | ASYNC | YES (truncate fallback) | LOW |
| `rag_analysis/services/entity_extractor.py` | 질문→엔티티 추출 | GOOD | **NOT HANDLED** | EXCELLENT (`JSONDecodeError`) | **NOT SET** | ASYNC | YES (regex fallback) | LOW |
| `rag_analysis/services/adaptive_llm_service.py` | 적응적 모델 선택 | GOOD | DEPENDS | UNKNOWN | **NOT SET** | ASYNC | YES (init 실패 시 None) | MEDIUM |
| `serverless/services/thesis_builder.py` | 스크리너 테제 생성 | BASIC | UNKNOWN | UNKNOWN | **NOT SET** | SYNC | YES (`ValueError` raise) | MEDIUM |
| `serverless/services/keyword_generator.py` | 키워드 배치 생성 v1 | GOOD | **NOT HANDLED** | DEPENDS (parser) | **NOT SET** | ASYNC | YES (빈 리스트) | MEDIUM |
| `serverless/services/keyword_generator_v2.py` | 키워드 배치 생성 v2 | GOOD | **NOT HANDLED** | DEPENDS (parser) | **NOT SET** | ASYNC | YES (빈 리스트) | MEDIUM |
| `serverless/services/keyword_service.py` | 단일 키워드 생성 | GOOD | PARTIAL (max_retries) | UNKNOWN | **NOT SET** | SYNC | **EXCELLENT** (FALLBACK_KEYWORDS) | LOW |
| `serverless/services/llm_relation_extractor.py` | 기업 관계 추출 | UNKNOWN | PARTIAL (pre-filter 80% 절감) | SYSTEM PROMPT JSON 정의 | **NOT SET** | SYNC | YES (에러 ExtractionResult) | LOW-MEDIUM |
| `serverless/services/relationship_keyword_enricher.py` | 관계 키워드 생성 | GOOD | **GOOD** (4초 지연=15RPM) | UNKNOWN | **NOT SET** | SYNC | PARTIAL | MEDIUM |
| `serverless/services/csv_url_resolver.py` | ETF CSV URL 분석 | UNKNOWN | UNKNOWN | UNKNOWN | **NOT SET** | SYNC | YES (regex 우선, LLM fallback) | LOW |
| `serverless/services/regulatory_service.py` | 규제 뉴스 스캔 | GOOD | N/A (선택적) | N/A | **NOT SET** | SYNC | YES (키워드 매칭 우선) | LOW |
| `stocks/services/korean_overview_service.py` | 한국어 기업 개요 생성 | BASIC | **NOT HANDLED** | GOOD | **NOT SET** | SYNC | PARTIAL (JSON→빈 값, 기타→re-raise) | MEDIUM |

### 3.3 RPM/RPD 소비 추정 (변동 없음)

| 서비스 | 일일 호출 | 빈도 | RPD 한도 내 |
|---|---:|---|---|
| 뉴스 키워드 추출 | ~1 | 일일 | OK |
| 뉴스 심층 분석 (50건 배치, 4초 간격) | ~50 | 일일 | OK |
| 한국어 개요 배치 (500종목, 주간) | ~71/일 | 주간 | OK |
| Market Movers 키워드 (3배치) | ~3 | 일일 | OK |
| Peer 필터 (온디맨드) | 가변 | 요청 시 | **주의** |
| 관계 키워드 (100건 배치) | ~100 | 일일 | OK |
| 관계 추출 | ~20 | 일일 | OK |
| SEC 파이프라인 | ~10 | 비정기 | OK |
| thesis 빌더 (대화형) | 가변 | 요청 시 | **주의** |
| **총 추정** | **~450/일 + 가변** | | **OK (1,500 RPD의 30%)** |

### 3.4 Gemini 핵심 발견사항

**강점** (직전 감사와 동일)
- `rag_analysis/services/llm_service.py`: 유일한 EXCELLENT 등급 — 3회 지수 백오프 `[1, 2, 4]`, 스트리밍 에러 이벤트
- 대다수 파일에서 JSON 파싱 try/except 래핑
- `relationship_keyword_enricher` — 4초 지연으로 15 RPM 준수

**취약점** (미해결 5건)

| # | 취약점 | 영향 파일 수 | 심각도 | 상태 |
|---|---|---:|---|---|
| G1 | **429 Rate Limit 미처리** — 24개 중 19개 파일이 재시도 없이 즉시 실패 | 19 | **HIGH** | 미해결 |
| G2 | **Timeout 미설정** — 24개 중 0개만 timeout 설정 (`rag_analysis`만 스트리밍) | 24 | **HIGH** | 미해결 |
| G3 | **JSON 파싱 안전성 불명확** — 4개 파일에서 parser 구현 확인 불가 | 4 | MEDIUM | 미해결 |
| G4 | **Exception 전파** — `sec_pipeline/extractor.py`, `korean_overview_service.py`에서 re-raise → 배치 중단 | 2 | MEDIUM | 미해결 |
| G5 | **배치 처리 시 RPD 한도 위험** — `korean_overview_service` 500건 배치 시 주간 ~500 RPD | 1 | LOW | 미해결 |

**신규 관찰**: `thesis/services/prompt_builder.py`는 직전 감사에서 UNKNOWN 상태였으나 이번 재검증 결과 **3개 지점(L542, L765, L943)** 모두 `genai.Client(...)` 직접 호출 → 공통 retry/timeout 래퍼 없음. Gemini 전체 Timeout 미설정 수치를 실질 24 이상으로 유지.

---

## 4. 기타 외부 의존성

### 4.1 FRED API (변동 없음)

| 항목 | 평가 |
|---|---|
| **위치** | `macro/services/fred_client.py`, `macro/services/macro_service.py`, `macro/tasks.py` |
| **용도** | 미국 경제 지표 (기준금리, 국채 수익률, CPI, 실업률, VIX, M2) |
| **에러 핸들링** | GOOD — permanent(401/403/404) vs transient(500/502/503/504), 지수 백오프 재시도 (2s,4s,6s, 최대 3회) |
| **Rate Limit** | HANDLED — Redis 기반 Token Bucket (100/분), 요청 간 0.6초 지연 |
| **Timeout** | 30초 |
| **Fallback** | PARTIAL — VIX 기본값 20, Fear & Greed 기본값 50, 개별 시리즈 실패 시 계속 |
| **위험도** | **MEDIUM** — Circuit Breaker 없음 |

### 4.2 Neo4j (재검증: 강점 확인)

| 항목 | 평가 |
|---|---|
| **위치** | `rag_analysis/services/neo4j_driver.py`, `chainsight/services/neo4j_sync.py`, `chainsight/services/neo4j_loader.py`, `chainsight/graph/schema.py`, `serverless/services/neo4j_*` 등 60+파일 |
| **용도** | 기업 공급망 관계, 경쟁사, 섹터, 테마, SavedPath snapshot 등 그래프 데이터 |
| **에러 핸들링** | EXCELLENT — Lazy singleton 초기화 (L19-67), 연결 실패 시 `None` 반환 (L66), 모든 쿼리 try-except 래핑 |
| **쿼리 Timeout** | 2,000ms (2초) 하드코딩 |
| **Connection Pool** | 최대 50 연결, 3,600초 수명 (settings 기준) |
| **Fork 안전성** | `force_reset_after_fork()` — SIGSEGV 방지 |
| **Fallback** | EXCELLENT — `_empty_relationships()` 메서드, 메타데이터에 `source: 'neo4j' \| 'fallback'` 구분 |
| **시스템 영향** | HIGH (graceful degradation) — 그래프 기능 비활성화되나 앱은 정상 |
| **위험도** | **LOW** — AuraDB free tier 간헐적 연결 끊김은 `CELERY_IGNORED_ERRORS`로 처리 |

> **신규 관찰** (Phase 6~7): `chainsight/services/recheck_service.py`의 `_fetch_current_snapshot`은 `get_graph_repository()` 경유하여 Neo4j 쿼리 수행 → 기존 lazy init 패턴 위에 구축되어 Neo4j 장애 시에도 상위 수준에서 계속 동작.

### 4.3 SEC EDGAR (2026-04-21 변경: Timeout 추가됨)

| 항목 | 평가 |
|---|---|
| **위치** | `sec_pipeline/collector.py`, `api_request/sec_edgar_client.py` |
| **용도** | 10-K 연례 보고서 다운로드 (Item 1, 1A, 7, 8) |
| **에러 핸들링** | BASIC — `raise_for_status()`, JSON 에러 필드 체크 — **재시도 로직은 여전히 없음** |
| **Rate Limit** | HANDLED (수동) — `time.sleep(0.12)` = 8.3 req/sec (SEC 한도 10 req/sec 이내) |
| **User-Agent** | 설정됨 (`Stock-Vis stockvis@example.com`) |
| **Timeout** | **30초 설정됨** (`collector.py:86`) — 직전 감사 M1 지적 해결 |
| **Fallback** | NO — CIK 조회 실패 시 `None` 반환, 파이프라인 중단 |
| **위험도** | **MEDIUM → LOW-MEDIUM** (Timeout 해결로 한 단계 완화) — 재시도 부재가 남은 핵심 약점 |

### 4.4 Redis (캐시/Rate Limiter/CB 상태)

| 항목 | 평가 |
|---|---|
| **위치** | `config/settings.py`, 67+파일 |
| **용도** | 분산 캐싱, Rate Limit 카운터, Circuit Breaker 상태, 그래프 쿼리 캐시 |
| **에러 핸들링** | GOOD — rate_limiter에서 Redis 불가 시 synchronous cache fallback |
| **Fallback** | PARTIAL — Rate Limiter는 fallback 있음, Circuit Breaker는 Redis 의존 (**Redis 장애 시 CB 무력화**) |
| **Cache Stampede** | 미보호 — 확률적 조기 만료(PER)나 락 기반 재계산 없음 |
| **시스템 영향** | MEDIUM — Rate limit 비신뢰성, Watchlist 성능 저하, CB 무력화 |
| **위험도** | **MEDIUM** — Redis 장애 시 CB가 작동하지 않아 외부 API 과부하 가능 |

### 4.5 Alpha Vantage / Finnhub / MarketAux (변동 없음)

| Provider | 용도 | Rate Limit | Circuit Breaker | Fallback | 위험도 |
|---|---|---|:---:|---|---|
| Alpha Vantage | NEWS_SENTIMENT | 5/분, 500/일 (Redis 슬라이딩 윈도우) | **YES** (`news/services/circuit_breaker.py`) | aggregator 다음 provider | MEDIUM |
| Finnhub | 기업/마켓 뉴스 | 60/분 (1초 지연) | **YES** | aggregator → MarketAux | LOW |
| MarketAux | 뉴스 + 센티멘트 | 2,500/일 (10초 지연, 일일 미추적) | **YES** | NO (aggregator 최종) | LOW |

### 4.6 EODHD (변동 없음)

- Bulk EOD 가격 (150,000+ 종목), 유료 무제한 → 위험도 LOW

### 4.7 뉴스 Circuit Breaker 기존 구현 (재검증)

`news/services/circuit_breaker.py` (75줄):
- **대상**: Finnhub, MarketAux, Alpha Vantage
- **기본값**: `threshold=5`, `timeout=300s`
- **상태 키**: `circuit:{provider}`, 실패 카운터 `circuit:{provider}:failures`
- **동작**: 5회 연속 실패 → 5분 차단, 성공 시 카운터 리셋
- **평가**: GOOD — 뉴스 provider에만 적용, **FMP/Gemini/FRED 미적용** (구조상 재사용 가능한 기반 존재)

---

## 5. Circuit Breaker 도입 후보

### 5.1 현황

Circuit Breaker 구현은 **뉴스 provider 3개(Finnhub/MarketAux/Alpha Vantage)**에만 적용되어 있음. FMP(28 파일), Gemini(24 파일), FRED(3 파일)는 여전히 미적용.

### 5.2 도입 필요 서비스 (우선순위순, 변동 없음)

| 우선순위 | 서비스 | 근거 | 장애 시 영향 | 현재 방어 |
|:---:|---|---|---|---|
| **P0** | **FMP API** | 28개 파일에서 사용, 장애 시 주가/재무/Movers/Screener/ChainSight/Market Pulse 일부/Thesis EOD 전체 영향 | 핵심 기능 대부분 마비 | Rate limit (코어만), 캐싱 일부 |
| **P0** | **Gemini API** | 24개 파일에서 사용, 장애 시 키워드/분석/테제/빌더/검증/RAG 전체 영향 | AI 기능 전체 마비 | 재시도 1개 파일만, 4초 지연 1개 파일 |
| **P1** | **FRED API** | Market Pulse 핵심 데이터 | 거시경제 대시보드 마비 | 지수 백오프 재시도, 기본값 |
| **P1** | **Redis** (자체) | Rate Limiter + CB 기반 | Rate Limit 무력화 → 외부 API 연쇄 과부하 | 동기 캐시 fallback |
| **P2** | **SEC EDGAR** | 파이프라인 비정기 실행 | SEC 파이프라인 중단 | 없음 (재시도 부재) |

### 5.3 권장 Circuit Breaker 스펙 (재활용 가능 구조)

```
news/services/circuit_breaker.py의 CircuitBreaker 클래스는 provider_name만 받아 동작하므로
일반화하여 "fmp", "gemini", "fred", "sec_edgar"로 확장 가능.

[P0] FMP Circuit Breaker
- 위치: api_request/providers/fmp/client.py (단일 진입점 _make_request 래핑)
- 트리거: 5회 연속 5xx 또는 429 에러 (402는 정상 신호로 분리, CB에 카운트하지 않음)
- 차단 시간: 60초 (점진 증가: 60→120→300초 — 현 CircuitBreaker는 고정 timeout이므로 확장 필요)
- 반열림(Half-Open): 차단 해제 후 1건 시험 호출
- Fallback: 캐시 데이터 반환, 없으면 503 에러 코드
- 모니터링: circuit_state 변경 시 CRITICAL 로그

[P0] Gemini Circuit Breaker
- 위치: 공통 래퍼 클래스 신규 생성 (예: config/llm/gemini_client.py)
- 트리거: 3회 연속 429/500 에러
- 차단 시간: 120초 (Gemini Free tier RPM 리셋 대기)
- Fallback: 서비스별 정적 fallback (대부분 이미 구현)
- 추가: 일일 RPD 카운터 (1,500 근접 시 예방 차단)
- 공통 래퍼에 timeout=30s, 재시도 [1, 2, 4]s 백오프 기본 적용 (H1/H2 동시 해결)

[P1] Redis Health Monitor
- 주기: 10초마다 PING
- 트리거: 3회 연속 PING 실패
- 액션: 전체 서비스에 "Redis degraded" 플래그 전파
- 효과: Rate Limiter → in-memory 모드, CB 상태 → 로컬 캐시 복제
```

### 5.4 장애 전파 경로 (Blast Radius, 최신 반영)

```
FMP 장애
  └→ stocks (주가/재무) — 빈 데이터
  └→ serverless (Movers/Screener/ChainSight DNA) — 서비스 불가
  └→ macro (일부 시장 데이터 — 지수/섹터 ETF) — 부분 마비
  └→ news (FMP 뉴스) — aggregator가 다른 provider로 전환
  └→ thesis (EOD 지표) — None 반환, 모니터링 중단
  └→ metrics (FMP 기반 지표 메타 수집) — 배치 중단
  └→ [2차] 프론트엔드 대부분 빈 화면

Gemini 장애
  └→ thesis (파싱/제안/지표매칭/prompt_builder 3곳) — fallback 텍스트
  └→ serverless (키워드/관계/스크리너 테제/CSV URL 분석) — 빈 키워드
  └→ news (심층분석/키워드/한국어 번역/api views) — failed 상태 DB 저장
  └→ rag_analysis (RAG 분석/문서 압축/엔티티 추출) — 에러 이벤트 스트리밍
  └→ validation (LLM 필터) — 에러 dict 반환
  └→ sec_pipeline (공급망/사업모델 추출/헬스리포트) — 파이프라인 중단
  └→ stocks (한국어 overview) — 배치 중단 시 re-raise

Redis 장애
  └→ Rate Limiter 무력화 → FMP/FRED/AV 과도 호출 → API 키 차단 위험
  └→ Circuit Breaker 무력화 → 장애 provider에 계속 호출
  └→ 캐시 미스 급증 → DB 부하 증가
  └→ [2차] 전체 시스템 성능 저하

Neo4j 장애 (graceful degradation 설계됨)
  └→ chainsight (v2 프로파일/관계/Phase 6~7 SavedPath) — 빈 결과
  └→ rag_analysis (그래프 기반 분석) — fallback 소스
  └→ serverless (neo4j_chain_sight_service) — empty 관계
  └→ 앱은 정상 동작
```

---

## 6. 종합 위험 매트릭스 (2026-04-21)

### 6.1 직전 감사 대비 상태 변화

| ID | 취약점 | 2026-04-14 | 2026-04-21 | 상태 |
|---|---|---|---|---|
| H1 | Gemini 429 미처리 (19/24 파일) | HIGH | HIGH | 미해결 |
| H2 | Gemini Timeout 미설정 (24/24) | HIGH | HIGH | 미해결 |
| H3 | FMP 402 서비스 계층 분기 부재 (14/28) | HIGH | HIGH | 미해결 |
| H4 | FMP/Gemini Circuit Breaker 부재 | HIGH | HIGH | 미해결 |
| M1 | SEC EDGAR Timeout 미설정 | MEDIUM | **해결됨** (30초 설정) | ✅ 해결 |
| M2 | Redis 장애 시 CB 무력화 | MEDIUM | MEDIUM | 미해결 |
| M3 | Cache Stampede 미보호 | MEDIUM | MEDIUM | 미해결 |
| M4 | Gemini JSON 파싱 불명확 (4파일) | MEDIUM | MEDIUM | 미해결 |
| M5 | 뉴스 provider Rate Limit 수동 sleep | MEDIUM | MEDIUM | 미해결 |
| M6 | `sp500_service.py` 에러 핸들링 부재 | MEDIUM | MEDIUM | 미해결 |

### 6.2 즉시 조치 필요 (HIGH — 1주일 간 변동 없음)

| ID | 취약점 | 범위 | 권장 조치 |
|---|---|---|---|
| H1 | Gemini 429 미처리 (19/24) | Gemini 전체 | 공통 retry 래퍼 (3회, 지수 백오프 `[1,2,4]`) — `rag_analysis/services/llm_service.py` 패턴 차용 |
| H2 | Gemini Timeout 미설정 (24/24) | Gemini 전체 | 표준 30초 (배치 120초) — 공통 래퍼에 통합 |
| H3 | FMP 402 미처리 (14/28) | FMP 서비스 계층 | 각 서비스 `except FMPPremiumError` 분기 추가 + `.` 포함 심볼 배치 제외 |
| H4 | FMP/Gemini Circuit Breaker 부재 | 핵심 외부 API | 기존 `news/services/circuit_breaker.py` 일반화 후 적용 |

### 6.3 조속 조치 필요 (MEDIUM)

| ID | 취약점 | 범위 | 권장 조치 |
|---|---|---|---|
| M2 | Redis 장애 시 CB 무력화 | 전체 시스템 | Redis Health Monitor + 로컬 캐시 fallback |
| M3 | Cache Stampede 미보호 | Redis 캐시 전체 | 확률적 조기 만료(PER) 또는 락 기반 재계산 |
| M4 | Gemini JSON 파싱 불명확 (4파일) | keyword_generator, csv_url_resolver 등 | parser 구현 감사 + try/except 래핑 |
| M5 | 뉴스 provider Rate Limit 수동 sleep | `news/providers/` | Redis 기반 비차단 큐 전환 |
| M6 | `sp500_service.py` 에러 핸들링 부재 | `stocks/` | try-except + 캐시 fallback |
| **M7** | **SEC EDGAR 재시도 로직 부재** | `sec_pipeline/collector.py` | 3회 지수 백오프 추가 (Timeout만 해결된 상태) |

### 6.4 모니터링 (LOW)

| ID | 취약점 | 범위 | 비고 |
|---|---|---|---|
| L1 | Gemini RPD 소비 모니터링 | Gemini 전체 | 현재 ~450/1,500 RPD, 여유 있음 (thesis 빌더 사용량 증가 주시) |
| L2 | FMP 캐시 TTL 비일관 | FMP 전체 | 데이터 유형별 전략 수립 |
| L3 | MarketAux 일일 한도 미추적 | `news/` | 2,500/day 카운터 추가 |
| L4 | EODHD 에러 핸들링 최소 | `api_request/` | 유료 서비스로 리스크 낮음 |

---

## 7. 조치 로드맵 (2026-04-21 갱신)

```
Phase 1 (즉시) — 방어 강화
├── [H1] Gemini 공통 retry 래퍼 클래스 (rag_analysis/llm_service 패턴 차용)
├── [H2] Gemini 전체 호출 timeout=30 적용 (래퍼 내장)
├── [H3] FMP 서비스 계층 14개 파일 402 분기 추가
└── [M7] SEC EDGAR 재시도 로직 추가 (Timeout은 해결됨)

Phase 2 (1~2주) — Circuit Breaker
├── [H4] news/circuit_breaker.py를 shared/circuit_breaker.py로 승격
├── [H4] FMP Circuit Breaker (client._make_request 래핑)
├── [H4] Gemini Circuit Breaker (Phase 1 래퍼에 통합)
├── [M2] Redis Health Monitor
└── [M6] sp500_service.py 에러 핸들링

Phase 3 (3~4주) — 안정성 고도화
├── [M3] Cache Stampede 보호 (PER 패턴)
├── [M4] Gemini JSON parser 감사 (keyword_generator 등)
├── [M5] 뉴스 provider 비차단 Rate Limiter
├── [L2] FMP 캐시 TTL 전략 표준화
└── [L3] MarketAux 일일 한도 카운터
```

---

## 8. 감사 방법론 부록

### 8.1 조사 대상 파일 식별

```bash
# FMP 호출 (src 트리, 테스트/스크립트 제외): 28개
grep -rl 'FMPClient\|fmp_client\|get_stock_service\|StockService' \
  --include='*.py' . | grep -v tests | grep -v scripts

# Gemini 호출 (src 트리, 테스트/스크립트 제외): 24개
grep -rl 'generate_content\|genai' \
  --include='*.py' . | grep -v tests | grep -v scripts
```

### 8.2 주요 라인 레퍼런스

- `api_request/providers/fmp/client.py:20-37` — 커스텀 예외 계층
- `api_request/providers/fmp/client.py:104-112` — Rate limit + daily counter
- `api_request/providers/fmp/client.py:121` — timeout=30 확인
- `api_request/providers/fmp/client.py:128-129` — 402 `FMPPremiumError` 발생
- `api_request/providers/fmp/provider.py:247-253, 293-299, 339-345` — 402 분기 (3/9 메서드)
- `macro/services/fmp_client.py:107-126` — BASIC 에러 핸들링
- `serverless/services/fmp_client.py:71-92` — 해당 클라이언트 에러 핸들링
- `news/services/circuit_breaker.py:13-74` — Redis 기반 CircuitBreaker 클래스
- `rag_analysis/services/llm_service.py:32-35` — Gemini 유일한 재시도 구현
- `rag_analysis/services/neo4j_driver.py:19-67` — Neo4j lazy init 패턴
- `sec_pipeline/collector.py:86` — SEC EDGAR timeout=30 (2026-04-21 기준 해결됨 확인)
- `thesis/services/prompt_builder.py:542, 765, 943` — Gemini 3개 지점 (timeout/retry 없음)
- `thesis/services/thesis_builder.py:431, 458` — Gemini fallback_parse 분기
- `thesis/services/indicator_matcher.py:197, 226` — Gemini 지표 매칭
- `validation/services/llm_peer_filter.py:72-90` — Gemini 에러 dict fallback

### 8.3 범위 제한

- **코드 수정 없음**: 본 감사는 읽기 전용
- **런타임 테스트 없음**: 실제 API 호출/장애 재현 미수행
- **Gemini `generate_content`와 `genai` 임포트는 동일 모듈에서 중복 카운트되지 않도록 파일 단위 집계**

---

> **비고**: 직전 1주일(2026-04-14~21) 동안 `chainsight` Phase 6~7이 대규모 추가되었으나 외부 API 신규 의존성은 없어 감사 매트릭스에 영향 없음. SEC EDGAR Timeout은 해결되었지만 Circuit Breaker 및 Gemini retry/timeout 공통화는 여전히 미착수 상태. Phase 1 조치가 지연될수록 H1~H4 취약점의 누적 리스크는 선형 증가한다.
