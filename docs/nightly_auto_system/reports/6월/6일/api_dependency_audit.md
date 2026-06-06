# 외부 API 의존성 감사 보고서

> **감사 일자**: 2026-06-06
> **유형**: 읽기 전용 정적 코드 감사 (코드 수정 없음)
> **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis / 뉴스 프로바이더(Finnhub·Marketaux)의 장애 대응(에러 핸들링·재시도·폴백·Circuit Breaker)
> **방법**: `packages/shared/`, `apps/`, `services/`, `thesis/` 전수 grep + 핵심 파일 직접 정독 + 병렬 서브에이전트 4건
> **대상 규모**: FMP 호출 파일 34, Gemini 호출 파일 80(다수는 모델/마이그레이션 잔여 참조), 기타 의존성 6종

---

## 0. 핵심 결론 (Executive Summary)

| # | 발견 | 심각도 | 영향 |
|---|------|--------|------|
| **F1** | **FMP 클라이언트가 3개로 분기, 에러 핸들링이 제각각** | 🔴 높음 | 402/429/retry 처리 일관성 없음 |
| **F2** | **Circuit Breaker가 Redis(django cache)에 강결합** — Redis 다운 시 CB 자체가 예외 전파 | 🔴 높음 | 회복 메커니즘이 단일 장애점에 의존 |
| **F3** | **Circuit Breaker 구현이 2벌 중복** (shared/tenacity vs news/자체) | 🟡 중간 | 동작·임계값 불일치, 유지보수 부담 |
| **F4** | **모든 Gemini 호출에 request timeout 미설정** | 🟡 중간 | 행(hang) 시 Celery 워커 점유·무한 대기 |
| **F5** | **429 재시도가 일부 경로에만 존재** (rag llm_service, portfolio client, keyword_service만) | 🟡 중간 | serverless/news/sec_pipeline 대량 호출은 429 즉시 실패 |
| **F6** | **Redis 캐시 장애 시 graceful degradation 없음** — `cache.get/set` 예외 전파 | 🔴 높음 | 캐시 다운이 CB 무력화 + API 응답 실패로 전이 |
| **F7** | **핵심 FMPClient(client.py)의 일일 카운터가 in-memory** — 프로세스/워커마다 독립, 공유 안 됨 | 🟢 낮음 | 일일 10,000 한도 추적 부정확 |

> **요약**: 시스템은 "방어선이 있되 고르지 않다." Market Pulse·RAG·S&P500 동기화 경로는 Circuit Breaker + 재시도 + 폴백을 갖춰 성숙하다. 반면 **serverless 키워드/관계추출, news 분석, sec_pipeline, validation의 Gemini 호출**과 **serverless/market_pulse용 FMP 클라이언트 2종**은 보호가 얇다. 가장 구조적인 위험은 **F2/F6 — 회복 인프라(CB)와 캐시가 모두 Redis 단일점에 묶여 있어, Redis 장애가 곧 전 방어선 동시 붕괴**라는 점이다.

---

## 1. 의존성 매트릭스

서비스 클러스터별 × 외부 API × 방어 수단. (✓=구현, △=부분, ✗=없음)

| 서비스 클러스터 | 외부 API | try/except | 재시도 | Circuit Breaker | Fallback | Timeout | 캐시 |
|----------------|----------|:--:|:--:|:--:|:--:|:--:|:--:|
| **stocks 동기화/펀더멘털** (`stocks/tasks.py`, `views_fundamentals`) | FMP (client.py) | ✓ | ✓ (클라이언트 3회 + Celery 3회) | ✗ | △ (Provider 추상화→yfinance) | ✓ 30s | △ |
| **S&P500 구성/EOD** (`sp500_service`, `sp500_eod_service`) | FMP (serverless_client) | ✓ | ✓ (CB 내장) | ✓ `fmp_sp500`/`fmp_sp500_eod` | ✓ (skip/빈결과) | ✓ 30s | △ |
| **재무제표 폴백** (`financial_statements_fallback`) | FMP→yfinance | ✓ | ✗ | ✗ | ✓ (yfinance 체인) | ✓ 30s | ✗ |
| **Market Movers/Screener** (`serverless/services/*`) | FMP (serverless_client) | ✓ | △ (Celery만) | △ (`fmp_market_movers`만) | ✓ (빈결과/continue) | ✓ 30s | ✓ |
| **market_breadth** (`market_breadth_service`) | FMP | ✗ | ✗ | ✗ | ✗ | ✓ 30s | ✗ |
| **Market Pulse 지수/섹터/환율** (`macro_service`, `market_pulse_client`) | FMP (market_pulse_client) | ✓ | ✗ | △ (`fmp_etf`) | ✓ (기본값 VIX=20 등) | ✓ 30s | ✓ |
| **Market Pulse 뉴스** (`news_aggregator`) | FMP+Marketaux | ✓ | ✓ (CB) | ✓ `fmp_news`/`marketaux` | ✓ (멀티소스) | △ | ✓ |
| **Market Pulse 브리핑** (`briefing/client`) | Gemini | ✓ | ✓ (CB) | ✓ `gemini` | ✗ (CB 예외 전파) | ✗ | ✗ |
| **RAG 분석** (`rag_analysis/services/*`) | Gemini | ✓ | ✓ (llm_service 429 백오프 + CB) | ✓ (llm/compressor) | ✓ (규칙기반/truncate) | ✗ | ✗ |
| **Portfolio 코치** (`portfolio/llm/client`) | Gemini(+Anthropic) | ✓ | ✓ (1회+폴백) | ✗ | ✓ (provider 전환) | ✗ | ✗ |
| **serverless 키워드/관계** (`keyword_*`, `llm_relation_extractor`, `regulatory`, `thesis_builder`) | Gemini | △ | △ (`keyword_service`만 429) | ✗ | ✓ (빈리스트/폴백테제) | ✗ | △ |
| **news 분석** (`keyword_extractor`, `news_deep_analyzer`, `stock_insights`) | Gemini | ✓ | ✗ | ✗ | ✓ (FALLBACK_KEYWORDS/None) | ✗ | ✗ |
| **SEC Pipeline 추출** (`sec_pipeline/extractor`, `intelligence`) | Gemini | ✓ | ✗ | ✗ | ✓ (에러 dict/기본값) | ✗ | ✗ |
| **Validation Peer 필터** (`llm_peer_filter`) | Gemini | ✓ | ✗ | ✗ | ✓ (error dict) | ✗ | ✗ |
| **한국어 개요** (`korean_overview_service`) | Gemini | ✓ | ✗ | ✗ | ✗ (예외 전파) | ✗ | ✗ |
| **Thesis 빌더** (`thesis/services/thesis_builder`) | Gemini | ✓ | ✓ (CB) | ✓ `gemini_thesis` | ✓ (폴백테제) | ✗ | ✗ |
| **거시 금리** (`macro_service` ← `fred_client`) | FRED | ✓ | ✓ (3회 지수백오프) | ✗ | ✓ (캐시/기본값) | ✓ 30s | ✓ |
| **Chain Sight/관계 그래프** (`neo4j_*`, `neo4j_driver`) | Neo4j | ✓ | ✗ | △ (`neo4j_chain_sight`) | ✓ (driver None→빈데이터) | ✓ 2s(쿼리) | ✗ |
| **SEC 공시 수집** (`sec_edgar_client`, `collector`) | SEC EDGAR | ✓ | △ (429 재귀, depth 무제한) | ✗ | ✗ (예외 전파) | ✓ 30/120s | ✗ |
| **뉴스 통합** (`news/services/aggregator`) | Finnhub+Marketaux | ✓ | ✗ | ✓ (news 자체 CB) | ✓ (멀티소스/빈리스트) | ✗ | ✓ |
| **전 영역 캐시** | Redis | ✗ | ✗ | n/a | ✗ (예외 전파) | n/a | n/a |

> Alpha Vantage: **미사용**(코드상 활성 호출 없음). 과거 Provider 추상화 흔적만 존재.

---

## 2. FMP 상세

### 2.1 클라이언트가 3벌로 분기 (F1)

| 클라이언트 | 위치 | HTTP 라이브러리 | 402 처리 | 429 처리 | 재시도 | 일일 카운터 | 에러 타입 |
|-----------|------|:--:|:--:|:--:|:--:|:--:|------|
| **정식 FMPClient** | `packages/shared/api_request/providers/fmp/client.py:85` | requests | ✓ `FMPPremiumError` (`:131`) | ✓ `FMPRateLimitError` (`:137`) | ✓ 3회 지수백오프 (`:160`) | ✓ in-memory (`:113`) | 4종 세분화 |
| **serverless FMPClient** | `packages/shared/api_request/providers/fmp/serverless_client.py:25` | httpx | ✗ (generic `FMPAPIError`) | ✗ | ✗ | ✗ | 1종 (`FMPAPIError`) |
| **market_pulse FMPClient** | `packages/shared/api_request/providers/fmp/market_pulse_client.py` | requests | ✗ | ✗ | ✗ | ✗ | `ValueError`/raise |

- **정식 client.py**는 모범적이다: `401→FMPAuthError`, `402→FMPPremiumError`, `403→FMPAuthError`, `429→FMPRateLimitError`, 그 외 `raise_for_status()`, 본문 `"Error Message"` 키 검사, 재시도 제외 예외(402/401/429) 즉시 전파, `RequestException`/`FMPClientError`만 지수백오프 재시도, `timeout=30`. (`client.py:128-172`)
- **serverless_client.py**는 `raise_for_status()` 한 줄로 모든 4xx/5xx를 동일 `FMPAPIError`로 뭉갠다 → **402 프리미엄 심볼과 429 레이트리밋을 구분 불가**. 재시도·요청 간 delay 없음. 다만 호출부가 Circuit Breaker로 감싸 재시도·차단을 외부에서 보완(`sp500_*`, `data_sync`).
- **market_pulse_client.py**는 `request_delay`(0.2s) rate limiting은 있으나 재시도/402/429 분기 없음. 호출부(`get_quote` 등)가 `try/except Exception → None` 반환으로 graceful degradation. (`market_pulse_client.py:127-145`)

> **권고**: serverless_client / market_pulse_client를 정식 client.py로 통합하거나, 최소한 402/429 분기를 이식. CB로 보완되는 경로는 우선순위 낮음, **`market_breadth_service`처럼 CB도 없는 경로가 최우선**.

### 2.2 402 (FMPPremiumError) 처리 현황

| 처리함 | 위치 |
|--------|------|
| ✓ 정식 client.py에서 발생 | `client.py:131` |
| ✓ 명시적 catch + skip | `thesis/tasks/eod_pipeline.py:146` (`FMPPremiumError`→경고+None) |
| ✓ 암시적(catch-all) | `thesis/views/monitoring_views.py` |
| ✗ **나머지 전부** | serverless/market_pulse 경로는 402를 일반 에러로 처리 |

- 알려진 대응(공통버그 #23): `.` 포함 심볼(BRK.B 등)을 배치에서 제외 — 이는 **호출부 책임**이며 클라이언트 레벨 강제는 없음. 신규 호출 추가 시 누락 위험.

### 2.3 Rate Limit 처리

- 정식 client.py: `request_delay=0.2s`(300/min 대응) + 일일 카운터 10,000 + `429→FMPRateLimitError`. **단, 카운터는 인스턴스 in-memory**(`client.py:75,113`) → 멀티 워커/프로세스에서 합산 안 됨, 재시작 시 리셋. **분산 환경에서 일일 한도 추적은 사실상 부정확** (F7).
- market_pulse_client: delay만, 카운터 없음.
- serverless_client: delay·카운터 모두 없음 (CB·캐시에 의존).

### 2.4 주목할 단일 위험점

- **`services/serverless/services/market_breadth_service.py`**: `get_market_gainers/losers/actives`를 **try/except 없이** 직접 호출. FMP 장애 시 예외가 그대로 상위로 전파 → 해당 뷰/태스크 즉시 실패. (🔴 FMP 경로 중 유일하게 방어 0)

---

## 3. Gemini 상세

### 3.1 성숙도 양극화

**성숙 (재시도+폴백+CB):**
- `rag_analysis/services/llm_service.py:247-276` — 응답 본문 `"rate"/"quota"/"429"` 문자열 매칭으로 429 식별 → `RETRY_DELAYS` 지수백오프 + `get_circuit` CB. JSON 파싱은 `ResponseParser`.
- `apps/portfolio/llm/client.py:61-94,176-236` — `_classify_gemini_error`로 `ratelimit/resourceexhausted` 매핑 → 1회 재시도 후 **Anthropic 폴백**. 파서 `parsers.py:38-70`이 마크다운 펜스 제거→`raw_decode`→공백흡수 3계층.
- `thesis/services/thesis_builder.py:470` — `gemini_thesis` CB + 폴백 테제(`create_fallback_thesis`).
- `rag_analysis/services/context_compressor.py:133,287` — CB + truncate 폴백.
- `rag_analysis/services/entity_extractor.py:110-116` — 실패 시 규칙기반 `_fallback_extraction`.

**얇음 (429 무대응 / CB 없음):**

| 파일 | try/except | 429 | JSON 파싱 복구 | timeout | 폴백 |
|------|:--:|:--:|:--:|:--:|------|
| `serverless/services/keyword_generator.py` `_v2.py` | ✓ | ✗ | ✗ | ✗ | 빈리스트/None |
| `serverless/services/keyword_service.py:282` | ✓ | ✓ (문자열매칭+지수백오프, max=2) | ✓ (정규식 복구) | ✗ | FALLBACK_KEYWORDS |
| `serverless/services/llm_relation_extractor.py:374` | ✓ | ✗ | ✓ (정규식) | ✗ | 빈 ExtractionResult+error |
| `serverless/services/regulatory_service.py:512` | ✓ | ✗ | △ | ✗ | 빈리스트 |
| `serverless/services/relationship_keyword_enricher.py` | ✓ | ✗ (고정 4s대기) | ✓ | ✗ | 빈리스트 |
| `news/services/keyword_extractor.py:211` | ✓ | ✗ | ✗ | ✗ | FALLBACK_KEYWORDS |
| `news/services/news_deep_analyzer.py:125` | ✓ | ✗ (고정 4s대기) | ✓ (regex) | ✗ | None |
| `validation/services/llm_peer_filter.py:56` | ✓ | ✗ | ✓ (`response_mime_type=json`) | ✗ | error dict |
| `sec_pipeline/extractor.py:90,147` | ✓ | ✗ | ✓ (`JSONDecodeError`) | ✗ | 에러 dict |
| `sec_pipeline/intelligence.py:159` | ✓ | ✗ | ✓ | ✗ | 기본값 |
| `stocks/services/korean_overview_service.py:61` | ✓ | ✗ | △ | ✗ | **예외 전파** |
| `market_pulse/briefing/client.py:58` | ✓ | ✓(CB) | ✗ | ✗ | **CB 예외 전파** |

### 3.2 공통 약점

- **timeout 전무 (F4)**: 조사한 **모든** Gemini 호출이 SDK 기본 timeout에 의존. `genai.Client` 기본은 사실상 무제한에 가까워, Gemini 응답 지연/행 시 **동기 Celery 태스크가 워커 슬롯을 무한 점유**할 수 있다. 특히 `sec_pipeline`, `news`, `serverless` 배치는 대량·장시간 작업이라 위험이 누적.
- **429 처리 산발 (F5)**: 표준화된 백오프가 `llm_service`/`portfolio client`/`keyword_service` 3곳에만. 나머지는 429를 generic Exception으로 받아 즉시 폴백(빈결과)으로 떨어짐 → **조용한 품질 저하**(키워드 0개, 분석 누락)가 장애 신호 없이 발생.
- **고정 sleep을 rate-limit 대용으로 사용**: `relationship_keyword_enricher`/`news_deep_analyzer`의 4초 고정 대기는 15 RPM 회피용일 뿐, 429 발생 시 재시도가 아니다.
- **동기/비동기 혼재**: Celery 경로(`briefing`, `sec_pipeline`, `keyword_service`)는 동기 `genai.Client` 사용으로 공통버그 #8 준수 ✓. 단 `keyword_generator_v2`는 asyncio 이벤트루프 직접 생성 흔적이 있어 Celery 호환성 점검 필요.

---

## 4. 기타 의존성

### 4.1 FRED (`packages/shared/api_request/fred_client.py`)
- **가장 견고한 클라이언트 중 하나.** Transient(5xx)→지수백오프 3회, Permanent(401/403/404)→즉시 raise, `RateLimiter` 적용, timeout 30s, 시리즈별 부분 실패 허용. 상위 `macro_service`는 캐시 hit 우선 + 실패 시 기본값. CB 없음(재시도로 충분).

### 4.2 Neo4j (`rag_analysis/services/neo4j_driver.py`, `neo4j_service.py`)
- **Lazy singleton + None 폴백**이 잘 설계됨: 첫 연결 실패 시 `_connection_attempted=True`로 캐시, 이후 즉시 None 반환 → "Neo4j 없이 계속 진행". 모든 public 메서드가 `driver is None → 빈데이터`. 쿼리 timeout 2s, 풀 설정 존재, fork 후 `force_reset_after_fork()`로 SIGSEGV 방지(#25).
- 한계: 재시도 없음, failover 불가(단일 드라이버), CB는 `neo4j_chain_sight_service`에만.

### 4.3 SEC EDGAR (`packages/shared/api_request/sec_edgar_client.py`, `sec_pipeline/collector.py`)
- Rate limit 0.1s 강제(10 req/s 준수), User-Agent 필수 헤더, timeout 30s(다운로드 120s), `requests.Session` 재사용(유일).
- **위험**: 429 응답 시 `1초 대기 후 재귀 호출`인데 **depth 제한이 없다**(`sec_edgar_client.py:165-169`) → SEC가 지속적으로 429를 주면 무한 재귀/스택 위험(낮음~중간). collector는 실패 시 폴백 없이 예외 전파 → `_fail_result`.

### 4.4 Redis (`config/settings.py` CACHES)
- `django.core.cache.backends.redis.RedisCache`, `redis://127.0.0.1:6379/1`.
- **graceful degradation 없음 (F6)**: 코드 전반의 `cache.get()/set()`이 try/except로 감싸지지 않아 **Redis 다운 시 예외가 호출 경로로 전파**. macro_service 등 "캐시 우선" 패턴은 캐시 조회 자체가 실패하면 무력.
- **치명적 결합 (F2)**: Circuit Breaker(`circuit_breaker.py`)가 상태/카운터를 **django cache(Redis)에 저장**. `get_state()`의 `cache.get`이 Redis 장애 시 예외 → **CB가 보호는커녕 추가 장애 지점이 됨**. 즉 Redis 장애 = (캐시 폴백 붕괴) + (전 CB 동시 무력화)가 연쇄.

### 4.5 Finnhub / Marketaux (`news/providers/`)
- 둘 다 rate limit(1s / 10s) + `raise_for_status` + `"error"` 필드 검사 + 실패 시 빈리스트. `aggregator`가 멀티소스로 한쪽 실패 흡수. **단 명시적 timeout 없음**(requests 기본).

---

## 5. Circuit Breaker 분석 및 도입 후보

### 5.1 현황 — CB는 이미 존재하나 분열되어 있다

- **구현 A (정식)**: `packages/shared/api_request/circuit_breaker.py` — tenacity 기반(`stop_after_attempt`+`wait_exponential`), **상태를 django cache(Redis)에 저장**, `get_circuit(name, threshold, recovery, attempts)` 레지스트리. `call`/`acall`(sync/async) 제공. CLOSED/OPEN/HALF_OPEN 정상 구현.
- **구현 B (중복, F3)**: `services/news/services/circuit_breaker.py` — news 프로바이더 전용 자체 Redis 카운터 방식. 임계값·동작이 A와 별개.

**보호 중인 호출(named circuits):**
`fmp_sp500`, `fmp_sp500_eod`, `fmp_market_movers`, `fmp_etf`, `fmp_news`, `marketaux`, `gemini`(briefing), `gemini_thesis`, RAG `llm_service`/`context_compressor` 회로, `neo4j_chain_sight`.

### 5.2 CB 자체의 구조적 약점

1. **Redis 강결합(F2/재기재)**: CB 상태가 Redis에. Redis 장애 시 `cache.get` 예외 → CB가 보호 못 하고 같이 죽음. → **CB 내부 `cache` 접근을 try/except로 감싸 "Redis 불가 시 CLOSED로 폴백(=호출 통과)" 또는 "OPEN으로 폴백(=빠른 실패)"** 정책 필요.
2. **이중 구현(F3)**: A/B 통합 필요. news를 구현 A로 이관.
3. **레지스트리 in-memory**: `_REGISTRY`는 프로세스 로컬이나 상태는 Redis 공유라 동작엔 무해. 단 임계값을 호출부마다 다르게 넘기면 같은 name에 첫 등록값만 적용되는 함정 존재(`get_circuit`이 기존 인스턴스 재사용).

### 5.3 도입/확대 우선순위 (장애 시 전체 영향 큰 순)

| 순위 | 대상 | 현재 | 사유 |
|:--:|------|------|------|
| **P0** | **Redis 캐시 접근 격리** (CB·macro·serverless 전반의 `cache.get/set`) | 무방어 | F2+F6 연쇄 차단. CB 신뢰성의 전제조건. **CB 확대보다 먼저** |
| **P0** | `market_breadth_service` FMP 호출 | 방어 0 | FMP 경로 중 유일하게 try/except·CB·폴백 전무 |
| **P1** | **정식 FMPClient(client.py) 경로** — stocks 동기화/펀더멘털 | 자체 재시도만, CB 없음 | 가장 광범위하게 쓰이는 FMP 진입점. 펀더멘털/가격 전체에 영향 |
| **P1** | serverless/news/sec_pipeline의 Gemini 대량 호출 | CB 없음, 429 무대응 | 배치 다건. 429 폭주 시 조용한 대량 실패. 공유 `gemini_<domain>` 회로로 묶기 |
| **P2** | SEC EDGAR 429 재귀 → CB+depth 제한 | depth 무제한 재귀 | 무한 재귀 차단 + 백오프 표준화 |
| **P2** | Gemini 호출 전반 timeout 부여 | 없음 | CB와 별개로 워커 행 방지 (request_options/timeout) |
| **P3** | Neo4j 드라이버 CB 일원화 | 부분 | 이미 None 폴백 견고, 우선순위 낮음 |

### 5.4 비-CB 보강 권고 (낮은 비용·높은 효과)

- **Gemini timeout 일괄 설정** (F4): 동기 호출에 `request_options={"timeout": N}` 부여 — CB 도입보다 적은 변경으로 워커 점유 위험 제거.
- **FMP 클라이언트 통합** (F1): serverless/market_pulse → 정식 client.py로 수렴, 402/429 분기 확보.
- **429 백오프 표준 헬퍼**: `llm_service`의 패턴을 공용 데코레이터로 추출해 serverless/news/sec_pipeline에 적용.
- **일일 한도 카운터를 Redis 공유로** (F7): in-memory → 분산 정확도 확보(선택).

---

## 6. 부록 — 근거 파일 인덱스

- FMP 클라이언트: `packages/shared/api_request/providers/fmp/{client,serverless_client,market_pulse_client,provider}.py`
- Circuit Breaker: `packages/shared/api_request/circuit_breaker.py`, `services/news/services/circuit_breaker.py`
- FMP 소비자 주요: `packages/shared/stocks/{tasks.py,services/sp500_*,services/financial_statements_fallback.py}`, `services/serverless/services/{market_breadth,data_sync,chain_sight,sector_heatmap,enhanced_screener}_service.py`, `thesis/tasks/eod_pipeline.py`
- Gemini 성숙 경로: `services/rag_analysis/services/{llm_service,context_compressor,entity_extractor}.py`, `apps/portfolio/llm/{client,parsers}.py`, `thesis/services/thesis_builder.py`
- Gemini 얇은 경로: `services/serverless/services/{keyword_generator*,keyword_service,llm_relation_extractor,regulatory_service}.py`, `services/news/services/{keyword_extractor,news_deep_analyzer}.py`, `services/sec_pipeline/{extractor,intelligence}.py`, `services/validation/services/llm_peer_filter.py`, `packages/shared/stocks/services/korean_overview_service.py`
- 기타 의존성: `packages/shared/api_request/{fred_client,sec_edgar_client}.py`, `services/rag_analysis/services/neo4j_{driver,service}.py`, `services/sec_pipeline/collector.py`, `services/news/providers/{finnhub,marketaux}.py`, `config/settings.py`

> **면책**: 본 보고서는 정적 코드 분석 기반이며 런타임 실측(장애 주입 테스트)은 포함하지 않는다. 라인 번호는 감사 시점(2026-06-06) 기준이며 코드 변경 시 달라질 수 있다.
