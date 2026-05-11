# 외부 API 의존성 감사 보고서

- 일자: 2026-05-06
- 범위: Stock-Vis 백엔드 전체 (`backend/`, `serverless/`, `api_request/`, `macro/`, `news/`, `rag_analysis/`, `thesis/`, `chainsight/`, `sec_pipeline/`, `validation/`, `serverless/`)
- 성격: 읽기 전용 코드 정적 감사. 코드 수정 없음.
- 조사 대상: FMP(36개 파일), Gemini(36개 파일), FRED, SEC EDGAR, Neo4j, Redis

---

## 1. 의존성 매트릭스

서비스별 외부 API 사용 + fallback/우회 가능 여부.

| 서비스/도메인 | FMP | Gemini | FRED | SEC EDGAR | Neo4j | Redis (cache) | Redis (broker) | 다운 시 사용자 영향 |
|---|---|---|---|---|---|---|---|---|
| 종목 시세/검색 (`stocks/`, `api_request/`) | 필수 | - | - | - | - | 보조 | 보조 | FMP 다운 → 시세/프로필/재무제표 페이지 빈 결과 |
| Market Pulse (`macro/`) | 보조 | - | 필수 | - | - | 필수 | 보조 | FRED 다운 → 기본값(VIX 20, 공포/탐욕 50) **graceful** |
| Market Movers / Screener / Chain Sight v1 (`serverless/`) | 필수 | 보조(키워드) | - | - | 보조 | 필수 | 필수 | FMP 다운 → 핵심 페이지 빈 결과/500 |
| News 수집·분석 (`news/`) | 보조 | 필수 | - | - | 보조 | 보조 | 필수 | Gemini 다운 → 분석 보류, 수집은 정상 |
| RAG 분석 (`rag_analysis/`) | - | 필수 | - | - | - | 보조 | 필수 | Gemini 다운 → RAG 응답 불가, fallback truncate |
| Thesis Control (`thesis/`) | 보조(EOD) | 필수(빌더) | - | - | - | 보조 | 필수 | Gemini 다운 → 가설 빌더 마비, 관제실은 정상 |
| Chain Sight v2 (`chainsight/`) | 보조 | 보조 | - | - | 필수 | 보조 | 필수 | Neo4j 다운 → Graph View 500 |
| SEC Pipeline (`sec_pipeline/`) | - | 필수(추출) | - | 필수 | - | - | 필수 | SEC ban → 10-K 수집 중단 / Gemini 다운 → 분석 누락 |
| 1차 검증 (`validation/`) | - | 필수(필터) | - | - | - | - | 필수 | Gemini 다운 → LLM 필터 무력화, 정량 필터는 정상 |
| 인증/Watchlist (`users/`) | 보조 | - | - | - | - | - | - | 영향 없음 |

> "보조" = 호출은 있지만 graceful degradation 또는 캐시 우회 가능. "필수" = 다운 시 해당 페이지/태스크 즉시 마비.

---

## 2. FMP 상세

### 2.1 베이스 클라이언트 (`api_request/providers/fmp/client.py`)

- timeout=30s, request_delay=0.2s, max_retries=3 (지수 백오프 ×2)
- 에러 분기: 401→`FMPAuthError`, 402→`FMPPremiumError`, 403→`FMPAuthError`, 429→`FMPRateLimitError`
- `FMPPremiumError`/`FMPAuthError`/`FMPRateLimitError`는 재시도하지 않고 즉시 raise (네트워크/일반 에러만 재시도)
- 일일 한도(10,000) 자체 카운터 — **인스턴스별** 카운터라 멀티 워커 환경에서는 정확하지 않음 (한도 초과 가능)

### 2.2 Provider 레이어 (`api_request/providers/fmp/provider.py`)

- `get_balance_sheet`/`get_income_statement`/`get_cash_flow`만 `FMPPremiumError`를 catch해 `PREMIUM_ONLY` 응답 반환
- 나머지(`get_quote`, `get_company_profile`, `get_daily_prices`, `search_symbols`, `get_sector_performance`, `get_weekly_prices`)는 **402를 catch하지 않음** → 일반 `Exception`으로 빠지면서 `API_ERROR`로 묻힘. premium-only 상장폐지/특수 심볼 호출 시 로그 추적 어려움

### 2.3 별개 FMP 클라이언트 중복 (구조적 문제)

| 클라이언트 | 라이브러리 | 에러 클래스 | 비고 |
|---|---|---|---|
| `api_request/providers/fmp/client.py` | requests | `FMPClientError`/`Auth`/`RateLimit`/`Premium` | 정식 베이스 |
| `serverless/services/fmp_client.py` | httpx | `FMPAPIError` (단일) | Market Movers/Screener 등 serverless 전용 |
| `macro/services/fmp_client.py` | requests | 일반 `Exception` | macro 전용, 에러 처리 가장 약함 |

→ 동일 API에 대해 **3개 구현, 3개 에러 처리 정책**. 베이스 클라이언트의 402/429 핸들링이 macro/serverless 쪽에서 누락됨.

### 2.4 소비자 레이어 패턴 요약

| 파일 | Premium 처리 | RateLimit 처리 | Celery retry | 위험도 |
|---|---|---|---|---|
| `stocks/tasks.py` | × | × | `self.retry(countdown=60~300s, max_retries=3)` | MEDIUM |
| `serverless/tasks.py` (Market Movers) | × | × | `self.retry, max_retries=3, 5분 간격` | MEDIUM |
| `serverless/services/data_sync.py` | × | × | raise → 호출자(Celery)가 재시도 가정 | **HIGH** |
| `serverless/services/market_breadth_service.py` | × | × | raise만, 호출자 책임 불명확 | **HIGH** |
| `serverless/services/sector_heatmap_service.py` | × | × | ETF quote 1개 실패 시 전체 fail | **HIGH** |
| `serverless/services/enhanced_screener_service.py` | × | × | FMPAPIError → 빈 결과 | LOW |
| `serverless/services/chain_sight_service.py` | × | × | `_empty_result()` | LOW |
| `thesis/tasks/eod_pipeline.py` | ○ | × | `bind=True, max_retries=2` | MEDIUM |
| `news/providers/fmp.py` | × | × | Exception → `[]` | LOW |
| `macro/services/fmp_client.py` | × | × | Exception → None/[] (자체) | MEDIUM |
| `users/utils.py` `ensure_complete_stock_data` | × | × | 결과 dict에 누적 | MEDIUM |

### 2.5 발견된 위험

1. **PremiumError 처리 불균일** — Provider 레이어에서 3개 메서드만 catch. 다른 메서드는 402를 일반 에러로 묻어 디버깅 어려움.
2. **RateLimit(429)에 대한 Celery 자동 재시도 없음** — `FMPRateLimitError`를 명시적으로 catch해 `self.retry(countdown=long_delay)`로 변환하는 태스크 **0개 확인**. 일반 Exception으로 잡혀 같은 backoff(60~300s) 적용 → Starter Plan 300/min 한도 회복 충분하지만 명시적 정책 없음.
3. **데이터 소스 레이어가 raise** — `data_sync.py`/`market_breadth_service.py`는 Celery 태스크가 wrap하지 않으면 unhandled. `MarketBreadth` 등 동기 호출 경로(API 응답)에서 직접 부르면 사용자에게 500 노출.
4. **일일 카운터 부정확** — `FMPClient.daily_calls`가 인스턴스별 in-memory. Celery 워커가 8개면 8배 한도 초과 가능. Redis 기반 분산 카운터 부재.
5. **timeout=30s 일률** — historical-price-eod (대용량) 응답 지연 시 30s 부족 가능.

---

## 3. Gemini 상세

### 3.1 클라이언트 분포

- 공통 래퍼: `portfolio/llm/client.py` (`LLMClient`) — Gemini + Anthropic 이중 지원, Gemini 429 시 Anthropic 폴백, `LLM_BUDGET_MAX_CALLS` 비용 가드
- **그러나 25개 파일이 직접 `genai.Client(api_key=...)` 인스턴스화** — 공통 래퍼 미사용 → 정책 적용 불가능

### 3.2 429 (Rate Limit) 처리

| 파일 | 429 처리 | 비고 |
|---|---|---|
| `portfolio/llm/client.py` | ○ (재시도+Anthropic 폴백) | 표준 패턴 |
| `rag_analysis/services/llm_service.py` | ○ (지수 백오프 1s/2s/4s, 3회) | async |
| `news/services/news_deep_analyzer.py` | △ (수동 `time.sleep(RPM_DELAY=4s)`) | 사전 대기만, 429 자체 처리 없음 |
| `news/services/keyword_extractor.py` | × | 폴백 키워드 반환만 |
| `sec_pipeline/extractor.py` | × | catch-all → `{'error': ...}` |
| `validation/services/llm_peer_filter.py` | × | catch-all → `{'error': ...}` |
| `serverless/services/keyword_generator*.py` | × | 폴백 결과 |
| `thesis/services/*.py` | × | 호출자에 전파 |

→ Free Tier(15 RPM) 환경에서 동시 태스크 다수 실행 시 429 빈발 가능. 5개 파일만 명시 대응.

### 3.3 JSON 파싱 처리

- `response_mime_type='application/json'`을 명시한 호출은 약 3곳(`sec_pipeline/extractor.py`, `validation/services/llm_peer_filter.py`, `stocks/services/korean_overview_service.py`)
- 나머지는 텍스트 응답을 정규식/`json.loads`로 후처리 — **모델이 코드펜스/주석 추가 시 파싱 실패** 위험
- 폴백 패턴: `_fallback_extraction()`(엔티티), `_fallback_compress()`(truncate), `FALLBACK_KEYWORDS`(키워드) — 품질 저하 큼

### 3.4 timeout 설정

- LLM 호출 자체에 명시 timeout **0건** — Google GenAI SDK 기본값(공식 문서상 60s 또는 무제한 청크 스트리밍) 의존
- Celery 태스크 레벨에서만 간접 가드:
  - `news/tasks.py`: `soft_time_limit=180s`, `time_limit=240s`
  - `serverless/tasks.py`: `default_retry_delay=300s`
- → Gemini 응답 행 시 worker 슬롯 점유 → 다른 태스크 starvation 가능

### 3.5 thinking_budget

- 거의 모든 호출에 `ThinkingConfig(thinking_budget=0)` 명시 — Free Tier 호환성 확보 (good)

### 3.6 위험 요약

| 위험군 | 파일 | 이유 |
|---|---|---|
| HIGH | `sec_pipeline/intelligence.py`, `sec_pipeline/extractor.py` | 폴백 약함, Celery 재시도 의존, 10-K 1건 = 토큰 큼 |
| HIGH | `news/services/keyword_extractor.py`, `news_deep_analyzer.py` | 429 미처리, 수동 sleep만 |
| MEDIUM | `rag_analysis/services/*` | 백오프는 있으나 Anthropic 폴백 없음 |
| MEDIUM | `thesis/services/thesis_builder.py` | 빌더 핵심, 폴백 부재 → 사용자 직접 영향 |
| LOW | `portfolio/llm/client.py` | 재시도 + 폴백 + 비용 가드 모두 |
| LOW | `validation/services/llm_peer_filter.py` | 정량 필터로 대체 가능 |

### 3.7 발견된 구조적 문제

1. **공통 래퍼 미사용** — `portfolio/llm/client.py`의 정책(재시도+Anthropic 폴백+예산)이 **전체의 ~10%에만 적용**.
2. **429와 일반 에러 구분 없음** — Celery `max_retries`가 모두 동일 backoff로 처리 → 429에는 너무 짧고, 일반 에러에는 너무 김.
3. **timeout 무방비** — SDK 기본값에 의존, 명시 0건.
4. **JSON 강제 부족** — `response_mime_type` 3곳만 사용. 나머지는 LLM 자유 출력 후 파싱.
5. **토큰 한도 사전 검증 없음** — 입력 길이 절단 로직(예: `_fallback_compress`) 일부만 존재. 1.5M 컨텍스트 호출 시 막대한 비용/지연.

---

## 4. 기타 의존성

### 4.1 FRED (`macro/services/fred_client.py`, `macro_service.py`)

- 3회 재시도 (지수 백오프 2/4/6s), transient(5xx)만 재시도
- 각 지표별 try/except 격리 (개별 실패가 전체 대시보드 망치지 않음)
- 캐시 미스 + FRED 다운 시 **기본값 반환** (VIX=20, 공포/탐욕=50, spread=1.0)
- → **graceful degradation 우수**. 위험도 LOW.

### 4.2 SEC EDGAR (`sec_pipeline/collector.py`)

- rate limit 0.12s 대기 (10 req/sec) 명시 준수
- User-Agent 헤더 필수 (`Stock-Vis stockvis@example.com`)
- timeout 30/60s
- 섹션 추출 1차 실패 시 `edgartools` fallback (선택적 의존성)
- 둘 다 실패 시 `status='failed', sections={}` 반환 → 태스크 계속
- **위험**: 부정확한 동시 실행/멀티 워커 시 0.12s 대기가 인스턴스별이라 **글로벌 10/sec 초과 가능 → IP ban 위험**

### 4.3 Neo4j (`chainsight/services/neo4j_sync.py`, `chainsight/api/views.py`, `serverless/services/neo4j_chain_sight_service.py`)

- `GraphConnectionError`/`GraphQueryError` 명시
- `chainsight/api/views.py`의 Graph View 엔드포인트는 예외를 catch하지 않아 **다운 시 HTTP 500** 그대로 노출
- `neo4j_dirty=True` 플래그 → Celery `sync_dirty_relations()` 주기 동기화. 실패 시 dirty 유지 → 다음 주기 재시도. 백그라운드는 자가 회복.
- `celery -Q neo4j --pool=solo` 별도 큐 (fork 회피) — 워커 다운 시 dirty 누적
- **위험도 HIGH**: API 즉시 500, fallback 없음.

### 4.4 Redis

- 용도 3가지 통합:
  1. Celery broker: `redis://localhost:6379/0`
  2. Celery result backend: `redis://localhost:6379/0`
  3. Cache: `redis://127.0.0.1:6379/1` (default), 일부는 LocMem(test)
- 캐시 미스 fallback: `cache.get()` None 시 재계산 (대부분 정상)
- **broker 다운 시**: Celery 태스크 enqueue 불가 → 모든 백그라운드 처리(EOD 파이프라인, 뉴스 수집, RAG 분석, Chain Sight sync) 마비
- **Beat 다운**: `DatabaseScheduler` (django-celery-beat) → DB는 살아있어도 워커가 broker에 못 붙으면 무의미
- **위험도 CRITICAL**: 단일 인스턴스 + failover 없음. `redis://localhost`는 docker-compose/단독 호스트 가정.

### 4.5 Alpha Vantage / Marketaux / Finnhub

- `api_request/providers/alpha_vantage/`: 코드 존재하나 `stock_service.py`의 fallback 체인에서만 사용. 5 calls/min 제한은 클라이언트 레벨 sleep 12s. 영향 작음.
- Marketaux/Finnhub: `news/providers/`. 키 없으면 skip. 다운 시 다른 뉴스 소스로 대체 가능.

---

## 5. Circuit Breaker 도입 후보

| 순위 | 의존성 | 후보 등급 | 근거 |
|---|---|---|---|
| 1 | **Redis (broker)** | CRITICAL | 단일 의존, failover 없음, 다운=전체 자동화 정지. 클라이언트 측 reconnection backoff + dead-letter queue(실패 시 DB 큐) 검토 |
| 2 | **Neo4j** | HIGH | API 페이지 즉시 500. `GraphConnectionError` catch → 빈 그래프 + `degraded=true` 플래그 응답으로 변환 권장 |
| 3 | **Gemini** | HIGH | 25개 파일이 공통 래퍼 미사용 → 글로벌 차단(consecutive 429) 신호를 받을 곳이 없음. `LLMClient`로 강제 통일 + 글로벌 breaker (5분간 차단) 추가 |
| 4 | **FMP (serverless 경로)** | HIGH | 분당 300 한도, 멀티 워커에서 인스턴스별 카운터로 추적 불가. Redis 기반 분산 토큰 버킷 + breaker 권장 |
| 5 | **SEC EDGAR** | MEDIUM | rate limit 위반 시 IP ban 위험. 멀티 워커 분산 limiter + ban 감지 시 1시간 차단 권장 |
| 6 | **FMP (consumer fallback)** | MEDIUM | 이미 부분적 fallback. 통합 `FMPCircuitBreaker` 도입 시 Anthropic처럼 다른 provider(Alpha Vantage)로 폴백 가능 |
| 7 | **FRED** | LOW | 이미 graceful. circuit breaker 없어도 ok |

---

## 6. 핵심 액션 아이템 (우선순위순)

> 본 보고서는 코드 수정 없는 감사. 아래는 후속 PR에서 다룰 권고 사항.

1. **Redis 단일점 장애 해소** — Sentinel 또는 Cluster, 클라이언트 reconnection backoff, broker 다운 감지 시 task buffer
2. **Neo4j API 응답 정상화** — `chainsight/api/views.py` 예외 catch → `{"degraded": true, "nodes": [], "edges": []}` 반환 (HTTP 200) 또는 503 + Retry-After
3. **Gemini 호출 통합** — 25개 파일을 `portfolio/llm/client.py`로 마이그레이션, 글로벌 breaker + timeout 명시 추가
4. **FMP 분산 rate limiter** — Redis 기반 토큰 버킷으로 멀티 워커 한도 정확화. 일일 카운터도 Redis 영속화
5. **`response_mime_type='application/json'` 강제 적용** — JSON 기대 호출 전부에 적용 (LLMClient에서 일괄 처리)
6. **Celery 429/Premium 분기 정책** — `FMPRateLimitError`/Gemini 429는 긴 backoff(60~300s+ jitter), 일반 에러는 짧은 backoff
7. **SEC EDGAR 분산 limiter** — 멀티 워커 0.12s 대기 보장, ban 감지 시 1시간 차단
8. **공통 timeout 정책** — Gemini 호출에 명시 timeout(예: 60s), `genai.Client` 옵션 통일

---

## 7. 부록: 발견된 상태 (재확인 필요 없는 사실)

- `api_request/providers/fmp/client.py`의 daily counter는 인스턴스별 in-memory
- `portfolio/llm/client.py`의 Anthropic 폴백은 `LLMClient`를 import하는 호출자에만 적용
- `chainsight/api/views.py`에는 Neo4j 예외 catch가 없음 → 500 노출
- `CELERY_BROKER_URL`/`CACHES` 모두 `localhost:6379` 단일 인스턴스 (docker/단독 호스트 가정)
- `news/services/news_deep_analyzer.py`의 `RPM_DELAY=4s`는 단일 워커 가정 → 멀티 워커에서 효과 없음
- 1차 검증의 LLM 필터(`validation/services/llm_peer_filter.py`)는 `{'error': ...}` 반환 → 정량 필터는 정상 동작 (graceful)
- FRED 클라이언트는 5xx만 재시도, 4xx는 즉시 raise (good)
