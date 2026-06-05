# 외부 API 의존성 감사 보고서

> **작성일**: 2026-06-05
> **유형**: 읽기 전용 정적 감사 (코드 수정 없음)
> **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis 장애 대응 (try/except·retry·fallback·circuit breaker)
> **방법**: 전수 grep(`FMPClient|fmp_client|StockService` 35파일, `generate_content|genai` 29파일) → 파일별 정적 분석
> **주의**: 본 보고서는 정적 코드 분석 기반이며 런타임 동작은 미검증. 라인 번호는 감사 시점 기준.

---

## 요약 (Executive Summary)

| 항목 | 평가 |
|------|------|
| **FMP** | 🟢 중앙 클라이언트(`FMPClient`)에 402/429/401/403 구분 + 재시도 3회 + 지수백오프 완비. 단 **서비스 레이어에서 402/429 구분 처리 거의 소실**(대부분 광범위 `Exception`으로 흡수) |
| **Gemini** | 🟡 호출 지점 분산(14+개), **429 명시 처리 2개 파일뿐**, **timeout 설정 전무**, JSON 파싱 복구는 절반만 구현. 공유 클라이언트 부재가 근본 원인 |
| **FRED** | 🟢 재시도 3회 + 개별 지표 격리 + 캐시 폴백(최대 7일). CB 미적용 |
| **Neo4j** | 🟢 lazy init + `driver=None` graceful degradation + CB(5회/60초). 격리 우수 |
| **SEC EDGAR** | 🟡 User-Agent 헤더 + rate limit(0.12s) 준수 + edgartools 폴백. 배치라 실시간 영향 낮음 |
| **Redis** | 🔴 **단일 장애점(SPOF) 성격**. CB 상태·rate limiter 상태가 모두 Redis에 저장 → Redis 다운 시 **CB 무력화 → 장애 provider로 과다 요청 → 쿼터 소진 연쇄 위험** |

**가장 큰 시스템 리스크**: Redis 장애 → Circuit Breaker 전면 무력화 (아래 Circuit Breaker 후보 §1 참조)

---

## 1. 의존성 매트릭스

서비스 영역 × 외부 API × 장애 대응 메커니즘.

| 서비스 영역 | 외부 API | try/except | retry | fallback | Circuit Breaker | 장애 시 영향 |
|------------|---------|:---------:|:-----:|:--------:|:---------------:|------------|
| `api_request/providers/fmp/client.py` (중앙) | FMP | ✅ 세분화(401/402/403/429) | ✅ 3회+지수백오프 | ❌ | ❌ | 모든 FMP 호출의 기반 |
| `api_request/providers/fmp/provider.py` | FMP | ✅ 402/429/Exception | ❌(client 위임) | ✅ ProviderResponse.error | ❌ | provider 단위 graceful |
| `stocks/tasks.py` | FMP(via Service) | ✅ 광범위 Exception | ✅ Celery 3회 | ❌ | ❌ | 재무제표 동기화 재시도 |
| `stocks/services/sp500_eod_service.py` | FMP | ✅ FMPAPIError | ❌ | ✅ 프로필 빈dict | ✅ CB | S&P500 EOD 동기화 부분손실 |
| `stocks/services/sp500_service.py` | FMP | ✅ CircuitBreakerError | ❌ | ✅ 빈dict | ✅ CB | 구성종목 동기화 실패 |
| `api_request/stock_service.py` | FMP | ✅ 광범위 Exception | ❌ | ✅ 기존 DB 데이터 | ❌ | 종목 가격/재무 부분실패 |
| `api_request/.../market_pulse_client.py` | FMP | ✅ httpx 계열 | ❌ | ❌ | ❌ | 시장지표/섹터/환율 조회실패 |
| `api_request/.../serverless_client.py` | FMP | ✅ requests/ValueError | ❌ | ❌ | ❌ | EOD/프로필/시세 조회실패 |
| `apps/market_pulse/services/macro_service.py` | FMP+FRED | ✅ 광범위 Exception | ❌(FMP)/✅(FRED) | ✅ 캐시+기본값 | ❌ | 대시보드 섹션 누락 |
| `apps/market_pulse/services/news_aggregator.py` | FMP뉴스 | ✅ CB+Exception | ❌ | ✅ 타 provider 계속 | ✅ CB | FMP 뉴스만 누락 |
| `apps/market_pulse/fetchers/fmp_weights.py` | FMP | ✅ | — | — | ✅ CB | 가중치 fetch |
| `services/news/providers/fmp.py` | FMP | ✅ 광범위 Exception | ❌ | ✅ 빈 list | ❌ | 종목/카테고리 뉴스 빈결과 |
| `services/news/services/aggregator.py` | FMP뉴스 | ✅ Exception | ❌ | ✅ 통계 dict | ❌ | 심볼별 뉴스만 영향 |
| `serverless/services/chain_sight_service.py` | FMP | ✅ FMPAPIError | ❌ | ✅ 빈 list | ❌ | 연관종목 빈결과 |
| `serverless/services/data_sync.py` | FMP | ✅ FMPAPIError+CB | ❌ | ✅ 부분실패 허용 | ✅ CB | Market Movers 부분손실 |
| `serverless/services/enhanced_screener_service.py` | FMP | ✅ FMPAPIError(재raise) | ❌ | ✅ 캐시 우선 | ❌ | 스크리너 빈결과 |
| `serverless/services/filter_engine.py` | FMP | ✅ FMPAPIError(재raise) | ❌ | ✅ 캐시 우선 | ❌ | 필터 빈결과 |
| `serverless/services/market_breadth_service.py` | FMP | ✅ FMPAPIError(재raise) | ❌ | ❌ | ❌ | Breadth 계산 실패 raise |
| `serverless/services/sector_heatmap_service.py` | FMP | ✅ 부분 catch | ❌ | ✅ 일부섹터 누락허용 | ❌ | 히트맵 부분생성 |
| `serverless/services/neo4j_chain_sight_service.py` | FMP+Neo4j | ✅ Exception+CB | ❌(CB내부1) | ✅ silent fail | ✅ CB | 그래프 동기화 부분손실 |
| `serverless/views.py` | FMP | ✅ Exception | ❌ | ✅ None 폴백 | ❌ | 지수정보 누락 |
| `thesis/tasks/eod_pipeline.py` | FMP | ✅ **402명시**+Exception | ❌ | ✅ None+skip기록 | ❌ | EOD 지표 부분손실 |
| `thesis/views/monitoring_views.py` | FMP | ✅ **402명시**+Exception | ❌ | ✅ DB readings | ❌ | 히스토리→DB폴백 |
| `users/utils.py` | FMP(Service) | ✅ Exception | ❌ | ✅ partial=True | ❌ | 포트폴리오 부분손실 |
| `stocks/views_search.py` | FMP(Service) | ✅ Exception | ❌ | ✅ 캐시 우선 | ❌ | 검색실패 503 |
| `thesis/services/thesis_builder.py` | Gemini | ✅ Exception | ❌ | ✅ _fallback_parse | ✅ CB | 자유입력 가설 기본값 |
| `thesis/services/prompt_builder.py` | Gemini | ✅ JSONDecodeError+Exc | ❌ | ✅ wizard 폴백 | ❌ | LLM proposal→wizard |
| `thesis/services/indicator_matcher.py` | Gemini | ✅ Exception | ❌ | ✅ 빈 배열 | ❌ | 지표추천 빈결과 |
| `thesis/tasks/summary.py` | Gemini | ✅ Exception | ❌ | ✅ 빈 문자열 | ❌ | ai_summary 미생성 |
| `thesis/views/conversation_views.py` | Gemini | ✅ Exception | ❌ | ✅ 원본 제목 | ❌ | 뉴스이슈 변환실패 |
| `serverless/services/keyword_generator.py` | Gemini(aio) | ✅ Exception | ❌ | ✅ 빈 배열 | ❌ | 키워드 빈결과 |
| `serverless/services/keyword_generator_v2.py` | Gemini(aio) | ✅ Exception | ❌ | ❌ | ❌ | 키워드 task 실패 |
| `serverless/services/keyword_service.py` | Gemini | ✅ Exception+retry | ✅ **429명시** | ✅ FALLBACK_KEYWORDS | ❌ | 기본 키워드 반환 |
| `serverless/services/llm_relation_extractor.py` | Gemini | ✅ Exception | ❌ | ✅ 빈 relations | ❌ | 관계추출 빈결과 |
| `serverless/services/regulatory_service.py` | Gemini(2.0-exp) | ✅ Exception | ❌ | ✅ 빈 배열 | ❌ | 규제그룹 빈결과 |
| `serverless/services/relationship_keyword_enricher.py` | Gemini | ✅ Exception | ❌ | ✅ 빈 배열 | ❌ | 키워드 빈결과 |
| `serverless/services/thesis_builder.py` | Gemini | ✅ Exception | ❌ | ✅ create_fallback_thesis | ❌ | 기본 테제 반환 |
| `serverless/services/csv_url_resolver.py` | Gemini | ✅ Exception | ❌ | ✅ None | ❌ | CSV URL 복구실패 |
| `rag_analysis/services/adaptive_llm_service.py` | Gemini(async stream) | ✅ Exception | ❌ | ❌(init만) | ❌ | RAG 스트리밍 차단 |
| `rag_analysis/services/context_compressor.py` | Gemini(aio) | ✅ CBError+Exception | ❌ | ✅ truncate 폴백 | ✅ CB | 압축 배치 폴백 |
| `rag_analysis/services/entity_extractor.py` | Gemini(aio) | ✅ JSONDecodeError+Exc | ❌ | ✅ 규칙기반 추출 | ❌ | 엔티티 빈결과 |
| `rag_analysis/services/llm_service.py` | Gemini(stream) | ✅ CBError+Exception | ✅ **429명시**+백오프3회 | ❌ | ✅ CB | RAG 스트리밍 차단 |
| `sec_pipeline/extractor.py` | Gemini+SEC | ✅ JSONDecodeError+Exc | ❌ | ❌(raise) | ❌ | 관계추출 배치 중단 |
| `sec_pipeline/intelligence.py` | Gemini | ✅ Exception | ❌ | ✅ 기본값 json | ❌ | 인텔리전스 리포트 폴백 |
| `validation/services/llm_peer_filter.py` | Gemini | ✅ Exception | ❌ | ✅ error dict | ❌ | peer 필터 빈결과 |
| `news/services/keyword_extractor.py` | Gemini | ✅ Exception | ❌ | ✅ 기본 키워드 | ❌ | 일일 키워드 폴백 |
| `news/services/news_deep_analyzer.py` | Gemini | ✅ Exception | ❌ | ❌(스킵) | ❌ | 기사별 분석 스킵 |
| `news/services/stock_insights.py` | Gemini | ✅ Exception | ❌ | ❌(영문 유지) | ❌ | 번역실패 영문 유지 |
| `news/api/views.py` | Gemini | 🔴 **없음** | ❌ | ❌ | ❌ | **API 500 노출** |
| `apps/market_pulse/briefing/client.py` | Gemini(공유) | ✅ CB 위임 | ❌ | ❌ | ✅ CB | Briefing 생성 차단 |
| `apps/portfolio/llm/client.py` | Gemini+Anthropic(공유) | ✅ 에러분류 | ✅ **2회+폴백** | ✅ **반대 provider** | ❌ | 포트폴리오 분석 차단 |
| `stocks/services/korean_overview_service.py` | Gemini | ✅ Exception | ❌ | ❌(raise) | ❌ | 한글개요 배치 중단 |
| `apps/market_pulse + fred_client.py` | FRED | ✅ 세분화 | ✅ 3회+지수백오프 | ✅ 캐시(최대7일)+기본값 | ❌ | 지표 부분누락 |
| `serverless/.../neo4j_chain_sight_service.py` + `rag_analysis/.../neo4j_driver.py` | Neo4j | ✅ 다층 | ❌(CB내부1) | ✅ driver=None graceful | ✅ CB | Chain Sight만 비활성(격리) |
| `sec_pipeline/collector.py` | SEC EDGAR | ✅ 단계별 | ✅ 단계별(3~5회) | ✅ edgartools | ❌ | 10-K 추출 배치 부분손실 |
| `config/settings.py` CACHES + 전역 | Redis | ✅ cache 호출 None반환 | — | ⚠️ Celery→django-db | — | **CB/rate limiter 무력화 위험** |

**범례**: ✅ 구현됨 · ❌ 없음 · ⚠️ 부분/조건부 · 🔴 위험

---

## 2. FMP 상세

### 2.1 중앙 클라이언트 — 🟢 모범 구현

`packages/shared/api_request/providers/fmp/client.py`

- **예외 계층**: `FMPClientError` → `FMPRateLimitError`(429) / `FMPAuthError`(401·403) / `FMPPremiumError`(402) (`client.py:21-42`)
- **HTTP 상태 코드 세분화 처리** (`client.py:129-143`):
  - 401 → `FMPAuthError("Invalid API key")`
  - 402 → `FMPPremiumError` (프리미엄 전용 심볼/엔드포인트)
  - 403 → `FMPAuthError("forbidden")`
  - 429 → `FMPRateLimitError`
- **재시도 로직** (`client.py:122-172`): `max_retries=3`, 지수백오프 `(attempt+1)*2` 초. **재시도 불필요 에러(402/401/429)는 즉시 전파** (`client.py:156-157`) — 올바른 설계
- **Rate limit 자기 방어** (`client.py:103-115`): `request_delay=0.2s`(300/min Starter), 일일 한도 10,000 카운터 + 초과 시 `FMPRateLimitError`
- **timeout**: `requests.get(..., timeout=30)` 명시 (`client.py:124`)
- **FMP 에러 응답 본문 처리** (`client.py:148-152`): `"Error Message"` 키 검사

> **강점**: FMP 레이어는 402/429/timeout/재시도가 모두 갖춰진 모범 사례. CLAUDE.md 버그 #23(402)·#14(필드명)의 산물로 보임.

### 2.2 서비스 레이어 — 🟡 402/429 구분의 소실

중앙 클라이언트가 던지는 세분화된 예외가 **상위 서비스에서 대부분 광범위 `except Exception`으로 흡수**되어, 402(프리미엄)와 429(rate limit)를 구분한 대응이 사라진다.

- **402를 명시 처리하는 곳은 단 3곳**:
  - `providers/fmp/provider.py:233·275·315` — 재무제표 3종에서 `FMPPremiumError` → `PREMIUM_ONLY` 코드 반환
  - `thesis/tasks/eod_pipeline.py:146` — warning 로그 + skip
  - `thesis/views/monitoring_views.py:344` — 빈 리스트/ DB 폴백
- **429를 서비스 레이어에서 별도 처리하는 곳은 사실상 없음**. `FMPRateLimitError`는 `provider.py`에서 `RateLimitError(provider)`로 한 번 변환되지만(`provider.py:85-86` 등), 그 위 호출자들은 광범위 Exception으로 처리.
- **재시도는 중앙 클라이언트 1곳에만** 존재. 서비스/태스크 레이어는 대부분 단발성(1회) 호출.

### 2.3 주의 지점

| 위치 | 이슈 |
|------|------|
| `serverless_client.py:146-147` | `FMPAPIError` 정의는 있으나 일부 경로에서 미사용 (에이전트 관찰) |
| `market_pulse_client.py` | 별도 httpx 기반 클라이언트 — 중앙 `FMPClient`와 **재시도/일일카운터 미공유** (이중 구현) |
| `serverless_client.py` | 별도 requests 기반 클라이언트 — 동일하게 중앙 클라이언트 보호 로직 미공유 |
| `market_breadth_service.py` | catch 후 재raise만 — 폴백 없이 상위로 전파 |

> **권고(설계)**: `market_pulse_client.py`·`serverless_client.py`가 중앙 `FMPClient`의 rate limit/재시도/일일 한도 카운터를 **공유하지 않으므로**, FMP 일일 10,000 한도 계산이 분산되어 실제 소진을 과소 추정할 수 있음.

---

## 3. Gemini 상세

### 3.1 구조적 문제 — 공유 클라이언트 부재

Gemini 호출이 **14개 이상 파일에 분산**되어 있고, 각자 `genai.Client`를 개별 생성한다. FMP처럼 보호 로직을 중앙화한 클라이언트가 없어 품질이 파일마다 들쭉날쭉하다.

- 부분적 공유 클라이언트: `apps/portfolio/llm/client.py`(가장 성숙), `apps/market_pulse/briefing/client.py`(CB만) — 그러나 전 서비스가 사용하지 않음.

### 3.2 429 (Rate Limit) 처리 — 🟡 2개 파일만

| 파일 | 방식 | 백오프 | 재시도 |
|------|------|--------|--------|
| `rag_analysis/services/llm_service.py:251` | `"rate"/"quota"/"429"` 문자열 검사 | 지수 [1,2,4]s | 3회 |
| `serverless/services/keyword_service.py:324` | rate/quota/429 감지 | 있음 | 재시도 |
| `apps/portfolio/llm/client.py:72-77` | `LLMRateLimitError` 예외 분류 | — | 반대 provider 폴백 |
| **나머지 11+개** | ❌ 명시 처리 없음 | — | — |

> Gemini Free 15 RPM 제약 하에서 야간 배치(키워드/관계/엔티티 추출)가 동시 다발하면 429가 빈발할 수 있으나, 대부분 빈 배열 폴백으로 **조용히 데이터 누락**됨(에러는 안 나지만 결과 품질 저하).

### 3.3 Timeout — 🔴 전무

- **조사한 14개 파일 전부 Gemini 호출에 timeout 미설정** (예외: `portfolio/llm/client.py`가 `LLMTimeoutError` 분류만 보유).
- 네트워크 지연 시 **무한 대기 위험**. Celery 태스크의 경우 `soft_time_limit`이 있으면 강제 종료되나, 동기 View 경로(`news/api/views.py` 등)는 워커 점유 위험.

### 3.4 JSON 파싱 — 🟡 절반만 복구 로직 보유

- **강건(regex 복구 포함)**: `keyword_service.py`, `llm_relation_extractor.py`, `relationship_keyword_enricher.py`, `serverless/thesis_builder.py`, `entity_extractor.py`, `keyword_extractor.py`, `stock_insights.py`, `news_deep_analyzer.py`
- **취약/미처리**: `thesis/tasks/summary.py`(평문), `csv_url_resolver.py`(regex만), `adaptive_llm_service.py`, `context_compressor.py`, `sec_pipeline/extractor.py`

### 3.5 핵심 취약점 (P0)

| 위치 | 이슈 | 영향 |
|------|------|------|
| `services/news/api/views.py:812-852` | `_generate_keyword_analysis()` Gemini 호출에 **try/except 없음** | Gemini 장애 시 **API 500 직접 노출** |
| `keyword_generator_v2.py` | `asyncio.run()` 사용 (주석에 SIGSEGV 위험 명시) | Celery fork 환경 크래시 위험 (CLAUDE.md 버그 #8·#25) |
| `adaptive_llm_service.py:233` | 예외 로깅만, 폴백 없음 | RAG 스트리밍 전체 차단 |

### 3.6 성숙 사례 — `apps/portfolio/llm/client.py`

벤치마크로 삼을 만한 패턴:
- `_classify_gemini_error()` / `_classify_anthropic_error()` — RateLimit/Timeout/일반 분류 (`:61-110`)
- 재시도 2회 (RateLimit·Timeout만)
- **provider 폴백**: Gemini ↔ Anthropic 자동 전환 (`:182-187`)
- CostGuard + 호출 카운터 이중 비용 가드
- `LLMResponse` Pydantic으로 cost_usd / latency_ms / fallback_from 추적

> **권고**: 이 클라이언트의 에러 분류 + 폴백 패턴을 공유 LLM 게이트웨이로 승격해 14개 분산 호출을 점진 통합.

---

## 4. 기타 의존성

### 4.1 FRED API — 🟢

- 위치: `packages/shared/api_request/fred_client.py`, `apps/market_pulse/services/macro_service.py`, `apps/market_pulse/tasks/macro.py`
- 재시도 3회 + 지수백오프(2/4/6s), transient(500/502/503/504)만 재시도, 401/403/404 즉시 실패
- **개별 지표 격리**(`fred_client.py:281-322`): 한 지표 실패가 다른 지표 수집을 막지 않음
- 캐시 폴백: realtime 60초 ~ quarterly 7일. 전체 실패 시 기본값(`macro_service.py:77-85`, 예: Fear&Greed 50 반환)
- **갭**: Circuit Breaker 미적용 (FRED 장기 장애 시 매 호출 재시도 비용)

### 4.2 Neo4j — 🟢 격리 우수

- Lazy singleton (`rag_analysis/services/neo4j_driver.py:43-74`): 연결 실패 시 **`driver=None` 반환 + "Application will continue without Neo4j" 로깅** → 앱 미중단
- `is_available()` 가드 + `_run_with_cb()` CircuitBreaker(`neo4j_chain_sight`, threshold=5, recovery=60s)
- 연결 풀: lifetime 3600s, pool 50, acquisition timeout 60s
- **장애 영향 격리**: Chain Sight 그래프 기능만 비활성. 주가/뉴스/거시 데이터 무관. PostgreSQL `StockRelationship`는 독립 동기화 가능. API는 빈 그래프(`{}`) 반환.

### 4.3 SEC EDGAR — 🟡

- `sec_pipeline/collector.py`
- **User-Agent 헤더 필수 준수**: `"Stock-Vis ..."` (SEC 요구사항)
- **Rate limit 준수**: `time.sleep(0.12)` (≈8.3 req/s < SEC 10 req/s 권장)
- 단계별 재시도: 메타 3회, HTML 5회(10초 백오프), 추출 1회
- **폴백**: regex(BeautifulSoup) → edgartools 라이브러리 → `status="partial"/"failed"` 기록 후 RawDocumentStore 저장
- 타임아웃: `requests.get(..., timeout=60)`, 태스크 `soft_time_limit=300s`
- **영향**: 배치 작업이라 실시간 사용자 영향 낮음. 한 종목 실패가 다른 종목 처리를 막지 않음.

### 4.4 Redis — 🔴 시스템 단일 장애점 성격

- 설정: `config/settings.py` — CACHES default `redis://127.0.0.1:6379/1`, Celery broker `/0`
- **cache 호출 자체는 graceful**: `cache.get/set` 실패 시 None/False 반환, DB 재조회로 폴백 (`rag_analysis/services/cache.py:106-114`)
- Celery 결과 백엔드는 django-db 폴백 존재
- **🔴 치명적 의존**: Circuit Breaker 상태(`cb:state:*`, `cb:fail_count:*`)와 rate limiter 상태가 **모두 Redis(Django cache)에 저장**됨 (`circuit_breaker.py:36-38`, `STATE_KEY="cb:state:{name}"`)
  - **Redis 다운 시나리오**: 모든 CB 상태 조회 실패 → CB가 OPEN을 유지하지 못함 → 실제 장애 중인 provider(FMP/Neo4j/Gemini/뉴스)로 **차단 없이 과다 요청** → FMP 일일 쿼터·Gemini RPD 소진 → **Redis 복구 후에도 쿼터 소진으로 장애 연장**

---

## 5. Circuit Breaker 도입/강화 후보

> 이미 `CircuitBreaker`(tenacity 기반, Redis 상태저장)가 존재하며 `news_aggregator`·`sp500_eod_service`·`sp500_service`·`data_sync`·`neo4j_chain_sight_service`·`context_compressor`·`llm_service`·`thesis_builder`·`fmp_weights`에 적용됨. 아래는 **미적용 + 장애 시 시스템 영향이 큰** 지점.

### 우선순위 1 — 🔴 Redis CB 의존성 해소 (구조적 최우선)

- **문제**: CB 자체가 Redis에 의존 → Redis 장애 = CB 전면 무력화 = 연쇄 쿼터 소진
- **후보 조치**: CB 상태에 **프로세스 로컬 메모리 폴백**(Redis 조회 실패 시 in-memory fallback), 또는 Redis 조회 실패를 "OPEN 유지(보수적 차단)"로 해석. rate limiter도 동일.
- **영향 범위**: 전체 외부 API (FMP/Gemini/Neo4j/뉴스)

### 우선순위 2 — 🟡 Gemini 호출 게이트웨이 통합 + CB/timeout

- **대상**: `news/api/views.py`(try/except 무), `keyword_generator(_v2)`, `entity_extractor`, `sec_pipeline/extractor`, `korean_overview_service`, `adaptive_llm_service`
- **이유**: 14개 분산 호출, 429 처리 2곳뿐, timeout 전무. 야간 배치 동시 호출 시 Gemini RPM/RPD 소진 → 광범위 빈결과(조용한 품질 저하)
- **후보 조치**: `apps/portfolio/llm/client.py` 패턴(에러 분류+폴백+timeout)을 공유 게이트웨이로 승격, CB 래핑

### 우선순위 3 — 🟡 FMP 보조 클라이언트 통합

- **대상**: `market_pulse_client.py`, `serverless_client.py` (중앙 `FMPClient`와 별개 구현, 일일 카운터/재시도 미공유)
- **이유**: FMP 일일 10,000 한도가 3개 클라이언트에 분산 추적되어 실제 소진 과소 추정. Market Pulse는 사용자 트래픽 직결.
- **후보 조치**: 중앙 `FMPClient` 단일화 또는 공유 rate limiter

### 우선순위 4 — 🟢 FRED CB 추가

- **대상**: `fred_client.py`
- **이유**: 재시도/캐시 폴백은 우수하나 CB 부재 → FRED 장기 장애 시 매 호출 재시도(3회×지수백오프) 누적 지연
- **후보 조치**: `CircuitBreaker("fred", threshold=3, recovery=60)` 래핑

### 우선순위 5 — 🟢 `news/api/views.py` 최소 방어 (즉시성 높음)

- **대상**: `_generate_keyword_analysis()` (`:812-852`)
- **이유**: try/except 부재로 Gemini 장애가 API 500으로 직접 노출 (사용자 대면)
- **후보 조치**: try/except + 폴백(빈 분석/캐시) 추가. CB 도입 전이라도 최소 방어 필요.

---

## 6. 장애 시나리오별 영향도

| 시나리오 | 즉시 영향 | 연쇄 위험 | 시스템 영향 |
|---------|----------|----------|------------|
| **Redis 완전 다운** | CB 상태 조회 실패 → 차단 해제, 캐시 미스 재계산 | 🔴 장애 provider로 과다요청 → FMP/Gemini 쿼터 소진 → 복구 후에도 장애 연장 | 🔴 광범위 |
| **FMP 429 (rate limit)** | 중앙 클라이언트 즉시 전파, CB 적용처는 차단 | 미적용 서비스(market_pulse_client 등)는 재시도 없이 실패 | 🟡 부분 |
| **FMP 402 (프리미엄 심볼)** | 3곳만 명시 skip, 나머지는 Exception 흡수 | 낮음 (`.` 포함 심볼 배치 제외 정책 존재) | 🟢 국소 |
| **Gemini 429/장애** | 대부분 빈배열 폴백(조용한 누락), `news/views.py`는 500 | 야간 배치 광범위 품질저하 | 🟡 부분(품질) |
| **Neo4j 30분 중단** | CB OPEN → 그래프 연산 차단, 빈 그래프 반환 | 없음 (PostgreSQL 독립) | 🟢 격리 |
| **SEC EDGAR 차단** | 배치 재시도(3~5회), partial 기록 | 없음 (배치) | 🟢 국소 |
| **FRED 간헐 오류** | 지표별 재시도 3회, 캐시 폴백(최대 7일) | 없음 | 🟢 미미 |

---

## 7. 핵심 발견 종합

1. **🔴 Redis가 숨은 SPOF**: cache 자체는 graceful하나, **CB·rate limiter 상태가 Redis에 종속**되어 Redis 장애가 모든 외부 API 보호장치를 동시 무력화 → 쿼터 소진 연쇄. (Circuit Breaker 후보 §1)
2. **🟡 FMP는 클라이언트는 모범, 서비스는 평범**: 중앙 `FMPClient`의 402/429/재시도/timeout이 우수하나 서비스 레이어에서 광범위 Exception으로 흡수되어 세분화 대응 소실. 게다가 보조 클라이언트 2종이 보호 로직을 미공유.
3. **🟡 Gemini는 구조적 분산 문제**: 공유 클라이언트 부재 → 429 처리 2곳, timeout 전무, JSON 복구 절반. `portfolio/llm/client.py`라는 좋은 패턴이 이미 존재하므로 이를 게이트웨이로 승격하는 것이 효율적.
4. **🟢 Neo4j·FRED·SEC는 양호**: graceful degradation·격리·폴백이 적절히 구현됨.
5. **즉시 조치 권고 1건**: `news/api/views.py:812-852` try/except 부재 → API 500 노출 (사용자 대면, 저비용 수정).

---

## 부록 — 조사 메타데이터

- FMP 관련 파일: 35개 (테스트/스크립트 제외 후 분석 대상 약 26개)
- Gemini 관련 파일: 29개 (테스트 제외 후 분석 대상 약 14개 핵심)
- Circuit Breaker 구현: `packages/shared/api_request/circuit_breaker.py`(tenacity+Redis), `services/news/services/circuit_breaker.py`(뉴스 전용)
- CB 적용처(import 확인): `briefing/client.py`, `fmp_weights.py`, `news_aggregator.py`, `sp500_eod_service.py`, `sp500_service.py`, `context_compressor.py`, `llm_service.py`, `data_sync.py`, `neo4j_chain_sight_service.py`, `thesis_builder.py`
- 본 감사는 **정적 분석**이며 라인 번호는 일부 서브에이전트 관찰 기반 — 수정 작업 전 해당 라인 재확인 권장.
