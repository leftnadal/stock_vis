# 외부 API 의존성 장애 대응 감사 보고서

> **감사일**: 2026-04-14
> **범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis, Alpha Vantage, Finnhub, MarketAux, EODHD
> **감사 파일 수**: FMP 18개, Gemini 28개, 기타 67+개

---

## 1. 의존성 매트릭스

### 서비스별 외부 API x Fallback 유무

| 앱 / 서비스 | FMP | Gemini | FRED | Neo4j | SEC EDGAR | Alpha Vantage | Finnhub | MarketAux | Redis |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **stocks** (주가/재무) | O | O | - | - | - | - | - | - | O(캐시) |
| **serverless** (Movers/Screener/ChainSight) | O | O | - | O | - | - | - | - | O(캐시) |
| **macro** (Market Pulse) | O | - | O | - | - | - | - | - | O(캐시) |
| **news** (뉴스 인사이트) | O | O | - | - | - | O | O | O | O(캐시+CB) |
| **thesis** (가설 통제실) | O | O | - | - | - | - | - | - | O(캐시) |
| **rag_analysis** (RAG 분석) | - | O | - | O | - | - | - | - | O(캐시) |
| **validation** (1차 검증) | - | O | - | - | - | - | - | - | - |
| **chainsight** (기업 프로파일) | - | - | - | O | - | - | - | - | - |
| **sec_pipeline** (SEC 파이프라인) | - | O | - | - | O | - | - | - | - |
| **metrics** (지표 메타데이터) | O | - | - | - | - | - | - | - | O(캐시) |

### Fallback 유무 요약

| 외부 의존성 | 호출 파일 수 | Fallback 있음 | Fallback 없음 | Fallback 비율 |
|---|---:|---:|---:|---:|
| FMP | 18 | 12 | 6 | 67% |
| Gemini | 28 | 18 | 10 | 64% |
| FRED | 3 | 2 (기본값 반환) | 1 | 67% |
| Neo4j | 60+ | 60+ (lazy init) | 0 | ~100% |
| SEC EDGAR | 3 | 0 | 3 | 0% |
| Alpha Vantage | 3 | 1 (다음 provider) | 2 | 33% |
| Finnhub | 2 | 1 (다음 provider) | 1 | 50% |
| MarketAux | 2 | 1 (다음 provider) | 1 | 50% |

---

## 2. FMP 상세

### 2.1 핵심 클라이언트 계층

#### `api_request/providers/fmp/client.py` — 평가: EXCELLENT

- **엔드포인트**: 16개 (`/stable/quote`, `/stable/profile`, `/stable/income-statement` 등)
- **에러 핸들링**: 커스텀 예외 계층 구축
  - `FMPClientError` (베이스)
  - `FMPRateLimitError` (429)
  - `FMPAuthError` (401)
  - `FMPPremiumError` (402)
- **재시도**: 지수 백오프 재시도 (transient failure 자동 재시도, terminal error 즉시 전파)
- **Rate Limit**: 요청 간 0.2초 지연 + 일일 10,000건 카운터 추적
- **위험도**: LOW

#### `api_request/providers/fmp/provider.py` — 평가: GOOD

- `FMPRateLimitError` → `RateLimitError`로 변환
- `FMPPremiumError` → `"PREMIUM_ONLY"` 코드 에러 응답 반환
- 호출자가 graceful하게 처리 가능

### 2.2 서비스 계층 상세

| 파일 | 에러 핸들링 | FMPPremiumError (402) | Rate Limit | Fallback | 위험도 |
|---|---|---|---|---|---|
| `api_request/providers/fmp/client.py` | EXCELLENT | **HANDLED** | EXCELLENT (0.2s + daily counter) | N/A (기반 레이어) | LOW |
| `api_request/providers/fmp/provider.py` | GOOD | **HANDLED** (PREMIUM_ONLY 코드) | Via client | YES (에러 응답) | LOW |
| `macro/services/fmp_client.py` | BASIC | **NOT HANDLED** | BASIC (0.5s sleep) | YES (빈 dict/list) | **MEDIUM** |
| `serverless/services/fmp_client.py` | GOOD | **NOT HANDLED** | BASIC (캐시) | YES (캐시 + datahub.io CSV fallback) | MEDIUM |
| `serverless/services/enhanced_screener_service.py` | GOOD | **NOT HANDLED** | GOOD (1h 캐시, 배치 20개 제한) | YES (캐시) | LOW-MEDIUM |
| `serverless/services/market_breadth_service.py` | GOOD | **NOT HANDLED** | BASIC (5분 캐시) | NO | **MEDIUM** |
| `serverless/services/sector_heatmap_service.py` | GOOD | **NOT HANDLED** | BASIC (5분 캐시) | PARTIAL (섹터별 스킵) | MEDIUM |
| `serverless/services/chain_sight_service.py` | GOOD | **NOT HANDLED** | GOOD (1h 캐시) | YES (빈 결과) | LOW-MEDIUM |
| `serverless/services/data_sync.py` | BASIC-GOOD | **NOT HANDLED** | BASIC | PARTIAL (심볼별 스킵) | MEDIUM |
| `serverless/services/filter_engine.py` | GOOD | **NOT HANDLED** | BASIC (캐시) | PARTIAL | MEDIUM |
| `stocks/services/sp500_service.py` | BASIC | **NOT HANDLED** | N/A | NO | **HIGH** |
| `stocks/services/sp500_eod_service.py` | GOOD | **NOT HANDLED** | GOOD (0.3s 쓰로틀) | YES (심볼별 스킵) | LOW-MEDIUM |
| `stocks/services/fmp_fundamentals.py` | GOOD | **NOT HANDLED** | GOOD (10분 캐시) | YES (캐시) | LOW-MEDIUM |
| `news/providers/fmp.py` | GOOD | **NOT HANDLED** | BASIC | YES (빈 리스트) | LOW-MEDIUM |
| `news/services/aggregator.py` | GOOD | N/A | N/A | YES (FMP 없이 계속) | LOW |
| `thesis/tasks/eod_pipeline.py` | GOOD | **HANDLED** | BASIC | YES (None 반환) | LOW |
| `thesis/views/monitoring_views.py` | GOOD | **HANDLED** | BASIC | YES (DB 폴백) | LOW |
| `serverless/tasks.py` | GOOD | **NOT HANDLED** | BASIC | NO (재시도) | MEDIUM |

### 2.3 FMP 핵심 발견사항

**강점**
- 코어 클라이언트(`client.py`)에 커스텀 예외 계층 + 지수 백오프 재시도 구현
- 광범위한 캐싱으로 API 호출 절감 (5분 ~ 24시간 TTL)
- 대부분 서비스에서 에러 시 빈 결과 반환으로 graceful degradation

**취약점**

| # | 취약점 | 영향 파일 수 | 심각도 |
|---|---|---:|---|
| F1 | **FMPPremiumError(402) 미처리** — 12개 파일에서 generic exception으로 흡수 | 12 | HIGH |
| F2 | **Rate limit 처리 불일관** — 코어는 daily counter 추적, macro/fmp_client는 미추적 | 5 | MEDIUM |
| F3 | **Silent failure** — market_breadth, sp500_service 등 빈 결과만 반환, 에러 가시성 없음 | 3 | MEDIUM |
| F4 | **Celery 재시도 시 API 과부하 위험** — serverless/tasks.py retry_delay=300s, 지수 백오프 아님 | 1 | MEDIUM |
| F5 | **캐시 TTL 비일관** — 5분 vs 1시간 vs 24시간, 전략 부재 | 전체 | LOW |

---

## 3. Gemini 상세

### 3.1 호출 현황 요약

- **총 호출 파일**: 28개
- **총 호출 지점**: 40+개
- **사용 모델**: `gemini-2.5-flash`
- **Free Tier 한도**: 15 RPM, 1,500 RPD

### 3.2 서비스별 상세

| 파일 | 용도 | 에러 핸들링 | 429 처리 | JSON 파싱 안전 | Timeout | Sync/Async | Fallback | 위험도 |
|---|---|---|---|---|---|---|---|---|
| `validation/services/llm_peer_filter.py` | NL→필터 변환 | BASIC | **NOT HANDLED** | SAFE | NOT SET | SYNC | YES (에러 dict) | MEDIUM |
| `thesis/views/conversation_views.py` | 뉴스→한국어 이슈 | BASIC | **NOT HANDLED** | SAFE | NOT SET | SYNC | YES (fallback_issues) | LOW |
| `thesis/services/thesis_builder.py` | 자유입력 파싱, 제안 생성 | BASIC | **NOT HANDLED** | SAFE (regex+json.loads) | NOT SET | SYNC | YES (fallback_parse) | MEDIUM |
| `thesis/services/prompt_builder.py` | 프롬프트 빌딩 | UNKNOWN | UNKNOWN | UNKNOWN | NOT SET | SYNC | UNKNOWN | MEDIUM |
| `sec_pipeline/extractor.py` | 10-K 공급망/사업모델 추출 | GOOD | **NOT HANDLED** | GOOD (JSONDecodeError) | NOT SET | SYNC | PARTIAL (re-raise) | MEDIUM |
| `sec_pipeline/intelligence.py` | 파이프라인 헬스 리포트 | BASIC | **NOT HANDLED** | SAFE | NOT SET | SYNC | YES (기본 에러 리포트) | LOW |
| `news/services/keyword_extractor.py` | 일일 키워드 추출 | GOOD | **NOT HANDLED** | GOOD | NOT SET | BOTH | YES (failed 상태 DB 저장) | LOW-MEDIUM |
| `news/services/news_deep_analyzer.py` | 뉴스 심층 분석 (최대 50건) | BASIC | **NOT HANDLED** | UNKNOWN | NOT SET | SYNC | YES (None, 다음 기사로) | MEDIUM |
| `news/services/stock_insights.py` | 키워드 한국어 번역 | UNKNOWN | UNKNOWN | UNKNOWN | NOT SET | UNKNOWN | UNKNOWN | MEDIUM |
| `rag_analysis/services/llm_service.py` | 스트리밍 투자 분석 | **EXCELLENT** | **HANDLED** (3회 백오프 1,2,4s) | N/A (스트리밍) | NOT SET | ASYNC | YES (에러 이벤트) | **LOW** |
| `rag_analysis/services/context_compressor.py` | 문서 압축 | GOOD | **NOT HANDLED** | N/A | NOT SET | ASYNC | YES (truncate fallback) | LOW |
| `rag_analysis/services/entity_extractor.py` | 질문→엔티티 추출 | GOOD | **NOT HANDLED** | EXCELLENT (JSONDecodeError) | NOT SET | ASYNC | YES (regex fallback) | LOW |
| `rag_analysis/services/adaptive_llm_service.py` | 적응적 모델 선택 | GOOD | DEPENDS | UNKNOWN | NOT SET | ASYNC | YES (init 실패 시 None) | MEDIUM |
| `serverless/services/thesis_builder.py` | 스크리너 테제 생성 | BASIC | UNKNOWN | UNKNOWN | NOT SET | SYNC | YES (ValueError raise) | MEDIUM |
| `serverless/services/keyword_generator.py` | 키워드 배치 생성 v1 | GOOD | **NOT HANDLED** | DEPENDS (parser) | NOT SET | ASYNC | YES (빈 리스트) | MEDIUM |
| `serverless/services/keyword_generator_v2.py` | 키워드 배치 생성 v2 | GOOD | **NOT HANDLED** | DEPENDS (parser) | NOT SET | ASYNC | YES (빈 리스트) | MEDIUM |
| `serverless/services/keyword_service.py` | 단일 키워드 생성 | GOOD | PARTIAL (max_retries) | UNKNOWN | NOT SET | SYNC | **EXCELLENT** (FALLBACK_KEYWORDS) | LOW |
| `serverless/services/llm_relation_extractor.py` | 기업 관계 추출 | UNKNOWN | PARTIAL (pre-filter 80% 절감) | SYSTEM PROMPT JSON 정의 | NOT SET | SYNC | YES (에러 ExtractionResult) | LOW-MEDIUM |
| `serverless/services/relationship_keyword_enricher.py` | 관계 키워드 생성 | GOOD | **GOOD** (4초 지연=15RPM) | UNKNOWN | NOT SET | SYNC | PARTIAL | MEDIUM |
| `serverless/services/csv_url_resolver.py` | ETF CSV URL 분석 | UNKNOWN | UNKNOWN | UNKNOWN | NOT SET | SYNC | YES (regex 우선, LLM fallback) | LOW |
| `serverless/services/regulatory_service.py` | 규제 뉴스 스캔 | GOOD | N/A (선택적) | N/A | NOT SET | SYNC | YES (키워드 매칭 우선) | LOW |
| `stocks/services/korean_overview_service.py` | 한국어 기업 개요 생성 | BASIC | **NOT HANDLED** | GOOD | NOT SET | SYNC | PARTIAL (JSON 실패→빈 값, 기타→re-raise) | MEDIUM |

### 3.3 RPM/RPD 소비 추정 (일일)

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
| **총 추정** | **~450/일** | | **OK (1,500 RPD 한도의 30%)** |

> **주의**: Peer 필터가 빈번하게 호출될 경우 RPD 한도 초과 가능

### 3.4 Gemini 핵심 발견사항

**강점**
- `rag_analysis/services/llm_service.py`: 유일하게 EXCELLENT 등급 — 3회 지수 백오프, 스트리밍 에러 이벤트
- 대다수 파일에서 JSON 파싱 try/except 래핑
- RPM 준수 패턴 (4초 지연) 일부 서비스에 적용
- Sync/Async 올바르게 분리 (Celery = Sync, RAG = Async)

**취약점**

| # | 취약점 | 영향 파일 수 | 심각도 |
|---|---|---:|---|
| G1 | **429 Rate Limit 미처리** — 28개 중 12개 파일에서 재시도 없이 즉시 실패 | 12 | **HIGH** |
| G2 | **Timeout 미설정** — 전체 28개 파일 중 0개만 timeout 설정 | 28 | **HIGH** |
| G3 | **JSON 파싱 안전성 불명확** — 4개 파일에서 parser 구현 확인 불가 | 4 | MEDIUM |
| G4 | **Exception 전파** — sec_pipeline/extractor.py, korean_overview_service.py에서 re-raise → 배치 중단 | 2 | MEDIUM |
| G5 | **배치 처리 시 RPD 한도 위험** — korean_overview_service 500건 배치 시 주간 약 500 RPD 소비 | 1 | LOW |

---

## 4. 기타 외부 의존성

### 4.1 FRED API

| 항목 | 평가 |
|---|---|
| **위치** | `macro/services/fred_client.py`, `macro/services/macro_service.py`, `macro/tasks.py` |
| **용도** | 미국 경제 지표 (기준금리, 국채 수익률, CPI, 실업률, VIX, M2) |
| **에러 핸들링** | **GOOD** — permanent(401/403/404) vs transient(500/502/503/504) 구분, 지수 백오프 재시도 (2s,4s,6s, 최대 3회) |
| **Rate Limit** | **HANDLED** — Redis 기반 Token Bucket (100/분, 보수적 설정), 요청 간 0.6초 지연 |
| **Timeout** | 30초 |
| **Fallback** | **PARTIAL** — VIX 기본값 20, Fear & Greed 기본값 50(중립), 개별 시리즈 실패 시 계속 진행 |
| **시스템 영향** | HIGH — Market Pulse 대시보드 일부 섹션 빈 값 |
| **위험도** | **MEDIUM** — Circuit Breaker 패턴 없음 |

### 4.2 Neo4j

| 항목 | 평가 |
|---|---|
| **위치** | `rag_analysis/services/neo4j_driver.py`, `neo4j_service.py`, `chainsight/services/neo4j_sync.py` 외 60+파일 |
| **용도** | 기업 공급망 관계, 경쟁사, 섹터 그래프 DB |
| **에러 핸들링** | **EXCELLENT** — Lazy singleton 초기화, 연결 실패 시 None 반환, 모든 쿼리 try-except 래핑 |
| **쿼리 Timeout** | 2,000ms (2초) 하드코딩 |
| **Connection Pool** | 최대 50 연결, 3,600초 수명 |
| **Fork 안전성** | `force_reset_after_fork()` — SIGSEGV 방지 |
| **Fallback** | **EXCELLENT** — `_empty_relationships()` 메서드, 메타데이터에 `source: 'neo4j' | 'fallback'` 구분 |
| **시스템 영향** | HIGH (graceful degradation) — 그래프 기능 비활성화되나 앱은 정상 |
| **위험도** | **LOW** — AuraDB free tier 간헐적 연결 끊김은 `CELERY_IGNORED_ERRORS`로 처리 중 |

### 4.3 SEC EDGAR

| 항목 | 평가 |
|---|---|
| **위치** | `sec_pipeline/collector.py`, `api_request/sec_edgar_client.py` |
| **용도** | 10-K 연례 보고서 다운로드 및 파싱 (Item 1, 1A, 7, 8) |
| **에러 핸들링** | **BASIC** — `raise_for_status()`, JSON 에러 필드 체크만 있음, **재시도 로직 없음** |
| **Rate Limit** | **HANDLED (수동)** — `time.sleep(0.12)` = 8.3 req/sec (SEC 한도 10 req/sec 이내) |
| **User-Agent** | 설정됨 (`Stock-Vis stockvis@example.com`) |
| **Timeout** | **미설정** — 무한정 블로킹 가능 |
| **Fallback** | **NO** — CIK 조회 실패 시 None 반환, 파이프라인 중단 |
| **위험도** | **MEDIUM** — Timeout 미설정과 재시도 로직 부재가 핵심 문제 |

### 4.4 Redis (캐시)

| 항목 | 평가 |
|---|---|
| **위치** | `config/settings.py`, 67+파일에서 사용 |
| **용도** | 분산 캐싱, Rate Limit 카운터, Circuit Breaker 상태, 그래프 쿼리 캐시 |
| **에러 핸들링** | **GOOD** — rate_limiter에서 Redis 불가 시 synchronous cache fallback |
| **Fallback** | **PARTIAL** — Rate Limiter는 fallback 있음, Circuit Breaker는 Redis 의존 (Redis 장애 시 CB 무력화) |
| **Cache Stampede** | **미보호** — 확률적 조기 만료(PER)나 락 기반 재계산 없음 |
| **시스템 영향** | MEDIUM — Rate limit 비신뢰성, Watchlist 성능 저하, CB 무력화 |
| **위험도** | **MEDIUM** — Redis 장애 시 Circuit Breaker가 작동하지 않아 외부 API 과부하 가능 |

### 4.5 Alpha Vantage

| 항목 | 평가 |
|---|---|
| **위치** | `news/providers/alphavantage.py`, `api_request/alphavantage_client.py` |
| **용도** | NEWS_SENTIMENT 엔드포인트 (주식별 뉴스 + 센티멘트) |
| **에러 핸들링** | BASIC — `raise_for_status()`, Rate Limit Note 감지 |
| **Rate Limit** | BASIC — 5 calls/min, Redis 슬라이딩 윈도우 카운터 |
| **Fallback** | NO (aggregator에서 다음 provider로 전환) |
| **Timeout** | 30초 |
| **위험도** | **MEDIUM** — Free tier 매우 제한적 (5/분, 500/일), Circuit Breaker 없음 |

### 4.6 Finnhub

| 항목 | 평가 |
|---|---|
| **위치** | `news/providers/finnhub.py` |
| **용도** | 기업 뉴스, 마켓 뉴스 카테고리 |
| **에러 핸들링** | BASIC — `raise_for_status()` |
| **Rate Limit** | HANDLED — 60 calls/min, 1초 지연 |
| **Fallback** | NO (aggregator에서 MarketAux로 전환) |
| **위험도** | **LOW** |

### 4.7 MarketAux

| 항목 | 평가 |
|---|---|
| **위치** | `news/providers/marketaux.py` |
| **용도** | 뉴스 + 센티멘트 + 엔티티 (Finnhub 후순위 provider) |
| **에러 핸들링** | BASIC — `raise_for_status()` |
| **Rate Limit** | HANDLED — 2,500 calls/day, 10초 지연 |
| **Fallback** | NO (aggregator 최종 provider) |
| **위험도** | **LOW** — 일일 한도 미추적이 유일한 약점 |

### 4.8 EODHD

| 항목 | 평가 |
|---|---|
| **위치** | `api_request/eodhd_client.py` |
| **용도** | Bulk EOD 가격 데이터 (150,000+ 종목) |
| **에러 핸들링** | BASIC |
| **Rate Limit** | N/A (유료 무제한) |
| **Timeout** | 60초 |
| **위험도** | **LOW** |

### 4.9 뉴스 Circuit Breaker (기존 구현)

| 항목 | 내용 |
|---|---|
| **위치** | `news/services/circuit_breaker.py` |
| **대상** | Finnhub, MarketAux, Alpha Vantage |
| **메커니즘** | Redis 기반 상태: `circuit:{provider}` 키, 5회 연속 실패 → 5분 차단 |
| **평가** | GOOD — 뉴스 provider에만 적용, FMP/Gemini/FRED 미적용 |

---

## 5. Circuit Breaker 도입 후보

### 5.1 현황

현재 Circuit Breaker가 구현된 서비스는 **뉴스 provider 3개 (Finnhub, MarketAux, Alpha Vantage)** 뿐이다.

### 5.2 도입 필요 서비스 (우선순위순)

| 우선순위 | 서비스 | 근거 | 장애 시 영향 | 현재 방어 |
|:---:|---|---|---|---|
| **P0** | **FMP API** | 18개 파일에서 사용, 장애 시 주가/재무/Movers/Screener/ChainSight 전체 영향 | 핵심 기능 대부분 마비 | Rate limit(코어만), 캐싱(일부) |
| **P0** | **Gemini API** | 28개 파일에서 사용, 장애 시 키워드/분석/테제/검증 전체 영향 | AI 기능 전체 마비 | 재시도(1개 파일만), 4초 지연(3개 파일) |
| **P1** | **FRED API** | Market Pulse 핵심 데이터 | 거시경제 대시보드 마비 | 지수 백오프 재시도, 기본값 |
| **P1** | **Redis** (자체) | Rate Limiter + Circuit Breaker의 기반 | Rate Limit 무력화 → 외부 API 과부하 연쇄 장애 | 동기 캐시 fallback |
| **P2** | **SEC EDGAR** | 파이프라인 비정기 실행 | SEC 파이프라인 중단 | 없음 |

### 5.3 권장 Circuit Breaker 스펙

```
[P0] FMP Circuit Breaker
- 위치: api_request/providers/fmp/client.py (단일 진입점)
- 트리거: 5회 연속 5xx 또는 429 에러
- 차단 시간: 60초 (점진 증가: 60→120→300초)
- 반열림: 차단 후 1건 시험 호출
- Fallback: 캐시 데이터 반환, 없으면 503 에러 코드
- 모니터링: circuit_state 변경 시 WARNING 로그

[P0] Gemini Circuit Breaker
- 위치: 공통 래퍼 클래스 (신규 생성 필요)
- 트리거: 3회 연속 429 또는 500 에러
- 차단 시간: 120초 (Gemini Free tier RPM 리셋 대기)
- Fallback: 서비스별 정적 fallback (이미 대부분 구현됨)
- 추가: 일일 RPD 카운터 (1,500 근접 시 예방적 차단)

[P1] Redis Health Monitor
- 주기: 10초마다 PING
- 트리거: 3회 연속 PING 실패
- 액션: 전체 서비스에 "Redis degraded" 플래그 전파
- 효과: Rate Limiter가 in-memory 모드로 전환, CB 상태를 로컬 캐시로 복제
```

### 5.4 장애 전파 경로 (Blast Radius)

```
FMP 장애
  └→ stocks (주가/재무) — 빈 데이터
  └→ serverless (Movers/Screener) — 서비스 불가
  └→ macro (일부 시장 데이터) — 부분 마비
  └→ news (FMP 뉴스) — 다른 provider로 전환
  └→ thesis (EOD 지표) — None 반환, 모니터링 중단
  └→ [2차] 프론트엔드 대부분 빈 화면

Gemini 장애
  └→ thesis (파싱/제안/지표분석) — fallback 텍스트
  └→ serverless (키워드/관계/스크리너 테제) — 빈 키워드
  └→ news (심층분석/키워드) — failed 상태 DB 저장
  └→ rag_analysis (RAG 분석) — 에러 이벤트 스트리밍
  └→ validation (LLM 필터) — 에러 dict 반환
  └→ sec_pipeline (공급망/사업모델) — 파이프라인 중단

Redis 장애
  └→ Rate Limiter 무력화
     └→ FMP/FRED/AV 과도 호출 → API 키 차단 위험
  └→ Circuit Breaker 무력화
     └→ 장애 provider에 계속 호출
  └→ 캐시 미스 급증 → DB 부하 증가
  └→ [2차] 전체 시스템 성능 저하
```

---

## 6. 종합 위험 매트릭스

### 즉시 조치 필요 (HIGH)

| ID | 취약점 | 범위 | 권장 조치 |
|---|---|---|---|
| **H1** | Gemini 429 미처리 (12/28 파일) | Gemini 전체 | 공통 retry 래퍼 도입 (3회, 지수 백오프) |
| **H2** | Gemini Timeout 미설정 (28/28 파일) | Gemini 전체 | 표준 30초 (배치 120초) timeout 설정 |
| **H3** | FMP 402 미처리 (12/18 파일) | FMP 서비스 계층 | 서비스 계층에 FMPPremiumError 분기 추가 |
| **H4** | FMP/Gemini Circuit Breaker 부재 | 핵심 외부 API | 위 5.3 스펙 구현 |

### 조속 조치 필요 (MEDIUM)

| ID | 취약점 | 범위 | 권장 조치 |
|---|---|---|---|
| **M1** | SEC EDGAR Timeout 미설정 | sec_pipeline | 30초 timeout + 3회 재시도 추가 |
| **M2** | Redis 장애 시 CB 무력화 | 전체 시스템 | Redis Health Monitor + 로컬 캐시 fallback |
| **M3** | Cache Stampede 미보호 | Redis 캐시 전체 | 확률적 조기 만료(PER) 또는 락 기반 재계산 |
| **M4** | Gemini JSON 파싱 불명확 (4파일) | keyword_generator 등 | parser 구현 감사 + try/except 래핑 확인 |
| **M5** | 뉴스 provider Rate Limit 수동 sleep | news/providers/ | Redis 기반 비차단 큐로 전환 |
| **M6** | sp500_service.py 에러 핸들링 부재 | stocks/ | try-except + 캐시 fallback 추가 |

### 모니터링 (LOW)

| ID | 취약점 | 범위 | 비고 |
|---|---|---|---|
| **L1** | Gemini RPD 소비 모니터링 | Gemini 전체 | 현재 ~450/1,500 RPD, 여유 있음 |
| **L2** | FMP 캐시 TTL 비일관 | FMP 전체 | 데이터 유형별 전략 수립 |
| **L3** | MarketAux 일일 한도 미추적 | news/ | 2,500/day 카운터 추가 |
| **L4** | EODHD 에러 핸들링 최소 | api_request/ | 유료 서비스로 리스크 낮음 |

---

## 7. 조치 로드맵 제안

```
Phase 1 (즉시) — 방어 강화
├── [H1] Gemini 공통 retry 래퍼 클래스 생성
├── [H2] Gemini 전체 호출에 timeout=30 추가
├── [H3] FMP 서비스 계층 12개 파일에 402 분기 추가
└── [M1] SEC EDGAR timeout + retry 추가

Phase 2 (1~2주) — Circuit Breaker
├── [H4] FMP Circuit Breaker (client.py 단일 진입점)
├── [H4] Gemini Circuit Breaker (공통 래퍼)
├── [M2] Redis Health Monitor
└── [M6] sp500_service.py 에러 핸들링

Phase 3 (3~4주) — 안정성 고도화
├── [M3] Cache Stampede 보호 (PER 패턴)
├── [M4] Gemini JSON parser 감사
├── [M5] 뉴스 provider 비차단 Rate Limiter
└── [L2] FMP 캐시 TTL 전략 표준화
```

---

> **비고**: 본 보고서는 코드 읽기 전용 감사로 작성되었으며, 코드 수정은 포함하지 않습니다.
> 후속 조치는 Phase별로 별도 PR을 생성하여 진행할 것을 권장합니다.
