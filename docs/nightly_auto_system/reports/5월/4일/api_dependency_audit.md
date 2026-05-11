# 외부 API 의존성 감사 보고서

- **감사 일자**: 2026-05-04
- **대상**: Stock-Vis 백엔드 (Django + Celery)
- **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Marketaux / Finnhub / Redis / PostgreSQL
- **모드**: 읽기 전용 (코드 수정 없음)
- **방법**: grep 기반 호출 지점 인벤토리 → 파일별 에러 핸들링·재시도·타임아웃·fallback 패턴 분석

---

## 의존성 매트릭스

| 서비스 / 모듈 | 외부 API | 재시도 | 타임아웃 | Fallback / 캐시 | Circuit Breaker | 종합 위험도 |
|---|---|---|---|---|---|---|
| `api_request/providers/fmp/client.py` | FMP | ✅ 3회 exp backoff | ✅ 30s | ❌ FALLBACK_CHAIN 비어있음 | ❌ | 🟡 중 |
| `api_request/providers/fmp/provider.py` | FMP | (client에 위임) | (client에 위임) | ⚠️ Premium 시 빈 dict 반환 | ❌ | 🟡 중 |
| `serverless/services/fmp_client.py` | FMP | ❌ 없음 | ✅ 30s (httpx) | ✅ Django cache 5min~24h | ❌ | 🟠 고 |
| `serverless/services/data_sync.py` | FMP (간접) | ❌ | (위임) | ⚠️ silent fail (빈 dict/list) | ❌ | 🔴 매우 높음 |
| `macro/services/fmp_client.py` | FMP | ❌ 없음 | ✅ 30s | ⚠️ 부분 캐시 (quote/profile만) | ❌ | 🟠 고 |
| `news/providers/fmp.py` | FMP | ❌ 없음 | ⚠️ 미확인 | ❌ Exception 무시 + 빈 [] | ✅ news 전용 CB | 🟠 고 |
| `stocks/tasks.py` (FMP 동기화) | FMP | (provider 의존) | (provider 의존) | ⚠️ FMPPremiumError 시 skip | ❌ | 🟡 중 |
| `thesis/tasks/eod_pipeline.py` | FMP | (provider 의존) | (provider 의존) | ✅ Premium 시 None 처리 | ❌ | 🟢 낮음 |
| `portfolio/llm/client.py` | Gemini | ✅ Anthropic 폴백 | ❌ max_tokens만 | ✅ Sonnet 자동 전환 | ❌ | 🟢 낮음 |
| `rag_analysis/services/llm_service.py` | Gemini (async) | ✅ 3회 exp backoff | ❌ | ⚠️ 부분 | ❌ | 🟡 중 |
| `rag_analysis/services/context_compressor.py` | Gemini (async) | ❌ | ❌ | ✅ truncate fallback | ❌ | 🟡 중 |
| `thesis/services/prompt_builder.py` | Gemini | ❌ 없음 | ❌ | ⚠️ JSONDecodeError → None | ❌ | 🟠 고 |
| `news/services/keyword_extractor.py` | Gemini | ❌ | ❌ | ✅ 3개 generic 키워드 | ❌ | 🟡 중 |
| `news/services/stock_insights.py` | Gemini | ❌ | ❌ | ⚠️ 부분 | ❌ | 🟡 중 |
| `news/services/news_deep_analyzer.py` | Gemini | ❌ | ❌ | ⚠️ 부분 | ❌ | 🟡 중 |
| `serverless/services/keyword_generator.py` | Gemini (async) | ❌ caller 위임 | ❌ | ✅ Semantic cache 7d | ❌ | 🟠 고 |
| `serverless/services/llm_relation_extractor.py` | Gemini | ❌ | ❌ | ⚠️ 부분 | ❌ | 🟡 중 |
| `serverless/services/csv_url_resolver.py` | Gemini | ❌ | ❌ | ⚠️ 빈 [] 반환 | ❌ | 🟡 중 |
| `serverless/services/regulatory_service.py` | Gemini | ❌ | ❌ | ⚠️ 부분 | ❌ | 🟡 중 |
| `validation/services/llm_peer_filter.py` | Gemini | ❌ | ❌ | ⚠️ 로깅만 | ❌ | 🟠 고 |
| `sec_pipeline/extractor.py` | Gemini | (Celery 위임) | ❌ | ⚠️ {'relationships': []} | ❌ | 🟡 중 |
| `sec_pipeline/intelligence.py` | Gemini | (Celery 위임) | ❌ | ⚠️ 부분 | ❌ | 🟡 중 |
| `stocks/services/korean_overview_service.py` | Gemini | ❌ | ❌ | ⚠️ 부분 | ❌ | 🟡 중 |
| `macro/services/fred_client.py` | FRED | ✅ 3회 exp backoff (2/4/6s) | ✅ | ✅ rate_limiter 통합 | ❌ | 🟢 낮음 |
| `serverless/services/neo4j_chain_sight_service.py` | Neo4j | ❌ 트랜잭션 단발 | (driver 기본) | ✅ `is_available()` → False/[] | ❌ | 🟡 중 |
| `rag_analysis/services/neo4j_driver.py` | Neo4j | ❌ | (driver 기본) | ✅ Lazy Singleton, None 모드 | ❌ | 🟡 중 |
| `sec_pipeline/collector.py` | SEC EDGAR | ❌ 없음 (raise) | ⚠️ 미확인 | ✅ edgartools 폴백 | ❌ | 🟠 고 |
| `news/providers/marketaux.py` | Marketaux | ❌ | ⚠️ 미확인 | ✅ Finnhub로 자동 전환 | ✅ news CB | 🟢 낮음 |
| `news/providers/finnhub.py` | Finnhub | ❌ | ⚠️ 미확인 | ✅ Marketaux로 자동 전환 | ✅ news CB | 🟢 낮음 |
| `config/settings*` (Redis 캐시) | Redis | ❌ | ⚠️ 미설정 | ⚠️ 일부 try/except 우회 | ❌ | 🟡 중 |
| Django ORM (PostgreSQL) | PostgreSQL | ❌ Celery autoretry 미설정 | (드라이버 기본) | ❌ raise | ❌ | 🟠 고 |

**범례**: 🟢 낮음 / 🟡 중 / 🟠 고 / 🔴 매우 높음

---

## FMP 상세 (36개 호출 지점)

### 1) 에러 핸들링 패턴

#### 우수 사례
- **`api_request/providers/fmp/client.py:80-161`** — 구조화된 예외 계층(`FMPClientError → FMPRateLimitError / FMPAuthError / FMPPremiumError`), HTTP 상태 분기(401/402/429), exponential backoff 3회 재시도. **단일 책임 + 명시적 분기로 가장 견고함.**
- **`api_request/providers/fmp/provider.py:247-253, 293-299, 339-345`** — `FMPPremiumError`를 명시적으로 catch → warning 로깅 + `error_response("PREMIUM_ONLY")` 반환 (graceful degradation).
- **`thesis/tasks/eod_pipeline.py:73-75`** — provider에서 raise된 Premium 예외를 None 처리 후 후속 지표 계산을 계속 진행.

#### 위험 사례
- **`serverless/services/data_sync.py:79-81, 131-140`** — `FMPAPIError` 발생 시 `log.warning`만 하고 빈 `dict`/`list` 반환. 호출자는 "성공이지만 데이터 없음"과 "실패"를 구분 불가 → **silent failure**.
- **`news/providers/fmp.py:50-54, 88-92, 123-127`** — bare `Exception` catch 후 `[]` 반환. 원인 추적 불가.
- **`macro/services/fmp_client.py:124-126`** — `RequestException`만 잡고 HTTPError 미처리. 502/503 발생 시 원시 예외가 상위로 전파될 가능성.

### 2) 재시도

| 위치 | 재시도 | 비고 |
|---|---|---|
| `api_request/providers/fmp/client.py:119-161` | ✅ max_retries=3, exp backoff(1/2/4초) | Premium·Auth는 즉시 전파 |
| `serverless/services/fmp_client.py` | ❌ | 캐시는 있지만 단발 호출 |
| `macro/services/fmp_client.py` | ❌ | 단발 호출 |
| `news/providers/fmp.py` | ❌ (news CB가 일부 보호) | |

→ **`api_request` 레이어 외에는 재시도 전무**. Celery 단계에서 task autoretry가 일부 보완하지만, 호출 단위 재시도는 부족.

### 3) Rate Limit 처리 (Starter 300 calls/min, 10,000/day)

- **`api_request/providers/fmp/client.py:100-112`** — `request_delay=0.2s`(분당 300회 강제) + `daily_calls` 카운터로 일일 한도 도달 시 `FMPRateLimitError` raise.
- **`serverless/services/fmp_client.py`** — Rate limit 인식 코드 없음. **캐시 miss 시 동시 다중 호출 위험** (특히 종목 일괄 조회).
- **`news/providers/fmp.py`** — Rate limit 직접 처리 없음.

### 4) FMPPremiumError (402) 처리

- **Raise**: `api_request/providers/fmp/client.py:128-129`
- **Catch & graceful**: provider.py(3개 메서드), thesis/tasks/eod_pipeline.py:73-75, thesis/views/monitoring_views.py:339
- **proactive 필터링 (`.` 포함 심볼 배치 제외)**: 코드상 명시적 whitelist/blacklist 미발견. S&P 500 멤버십 의존(`stocks/services/sp500_service.py`).

### 5) Fallback / 캐싱

- **Provider Fallback**: `api_request/providers/factory.py:66-69` `FALLBACK_CHAIN = {FMP: []}` → **FMP 단독, 대체 provider 없음.**
- **캐시**:
  - `serverless/services/fmp_client.py`: Django cache 5분/1시간/24시간 TTL (적극 활용).
  - `macro/services/fmp_client.py`: quote/profile에만 부분 캐시.
  - `news/providers/fmp.py`: 캐시 없음.
- **Stale fallback**: 캐시 만료 후 원본 호출 실패 시 stale 값 반환 로직 미발견.

### 6) 타임아웃 (모든 주요 경로 30초 명시)

| 위치 | 설정 |
|---|---|
| `api_request/providers/fmp/client.py:121` | `requests.get(..., timeout=30)` |
| `serverless/services/fmp_client.py:44, 363` | `httpx.Client(timeout=30.0)` |
| `macro/services/fmp_client.py:108` | `requests.get(..., timeout=30)` |

→ 일관성은 좋으나, 차등 타임아웃(historical 조회 등에 더 긴 값) 부재.

### 7) FMP 핫스팟 요약

| 순위 | 위치 | 문제 | 영향 |
|---|---|---|---|
| 1 | `serverless/services/data_sync.py:79-140` | silent fail (빈 객체 반환) | EOD/스크리너 데이터 결손 무인지 |
| 2 | `serverless/services/fmp_client.py` 전반 | 재시도·CB 없음, 캐시 miss 시 burst | 일시 장애 시 cascade |
| 3 | `news/providers/fmp.py` | Exception 무시 + 재시도 없음 | 뉴스 fetch 결손 |
| 4 | `macro/services/fmp_client.py:124-126` | HTTPError 미분류 | 502/503 미처리 |
| 5 | 전사 | `FALLBACK_CHAIN` 미구현 (단일 provider 의존) | FMP 장기 장애 시 전체 정지 |

---

## Gemini 상세 (36개 호출 지점)

### 1) SDK 표준화

- 거의 전 모듈이 신 SDK(`from google import genai`, `genai.Client()`) 사용.
- **통합 LLM 클라이언트**: `portfolio/llm/client.py` — Gemini 실패 시 Anthropic Sonnet 자동 전환 (유일한 모델 폴백 구현).
- **모델 고정**: `gemini-2.5-flash` (free tier 기준 15 RPM, 1500 RPD).

### 2) Async/Sync 혼용 (버그 #8 재발 위험)

#### 🔴 핵심 위험 지점
- **`rag_analysis/services/llm_service.py`** — `aio.models.generate_content_stream` 사용 (async).
- **`rag_analysis/services/context_compressor.py`** — `asyncio.gather`로 batch async.
- **`serverless/services/keyword_generator.py`** — `await self.client.aio.models.generate_content()` 호출.
- 이들 async API가 Celery 태스크에서 직접 호출되거나 `asyncio.new_event_loop()`로 래핑되면 fork-safety 문제 + 경쟁 조건 발생 (`sub_claude_md/common-bugs.md` #8 참조).

### 3) 모듈별 핸들링 점수

| 모듈 | 호출 | 에러 핸들링 | 재시도 | 타임아웃 | 점수 |
|---|---|---|---|---|---|
| `portfolio/llm/client.py` | sync | 5종 분류 + 통합 예외 | ✅ Anthropic 폴백 | ❌ | ⭐⭐⭐⭐ |
| `rag_analysis/services/llm_service.py` | async stream | rate/timeout/기타 | ✅ exp backoff 3회 | ❌ | ⭐⭐⭐⭐ |
| `rag_analysis/services/context_compressor.py` | async | try/except + truncate | ❌ | ❌ | ⭐⭐⭐ |
| `thesis/services/prompt_builder.py` | sync | logger | ❌ | ❌ | ⭐⭐⭐ |
| `news/services/keyword_extractor.py` | sync | JSONDecodeError + bare Exception | ❌ | ❌ | ⭐⭐⭐ |
| `serverless/services/keyword_generator.py` | async | 상위 위임 | ❌ | ❌ | ⭐⭐ |
| `validation/services/llm_peer_filter.py` | sync | logger only | ❌ | ❌ | ⭐⭐ |
| `sec_pipeline/extractor.py` | sync | JSONDecodeError → 빈 결과 | (Celery autoretry) | ❌ | ⭐⭐⭐ |

### 4) 429 (Rate Limit) 처리

- **명시적 처리**: `portfolio/llm/client.py:72`(resourceexhausted/quota 키워드), `rag_analysis/services/llm_service.py:217`(rate 키워드).
- **미처리**: `thesis/services/prompt_builder.py`, `serverless/services/keyword_generator.py`, `validation/services/llm_peer_filter.py` — 429 전용 분기 없음.
- **위험**: free tier 15 RPM에서 batch 20개 × 다중 worker → **쉽게 격돌**.

### 5) JSON 파싱

- 표준 패턴: `response.text → json.loads()`. structured output을 사용하더라도 markdown ``` ```json ``` ``` 펜스가 끼는 경우가 있음.
- **펜스 제거 처리 분포**:
  - ✅ `sec_pipeline/extractor.py:237` — `re.search(r'\[.*\]', text, re.DOTALL)` 사용.
  - ❌ `thesis/services/prompt_builder.py:572` — JSONDecodeError → None.
  - ❌ `serverless/services/csv_url_resolver.py:381` — 실패 시 빈 [].
  - ❌ 그 외 다수 — 정제 함수 없음.

### 6) 타임아웃

| 파일 | 타임아웃 | 비고 |
|---|---|---|
| portfolio/llm/client.py | ❌ | `max_output_tokens`만 |
| rag_analysis/llm_service.py | ❌ | async stream인데 timeout 없음 |
| context_compressor.py | ❌ | |
| news/keyword_extractor.py | ❌ | |
| sec_pipeline/extractor.py | ❌ | |

→ **`request_options/timeout`이 전사적으로 부재**. Gemini 기본 타임아웃(약 600초)에 의존 — Celery 태스크의 hang 위험.

### 7) Fallback 사례

- **모델 폴백**: `portfolio/llm/client.py` Gemini → Anthropic Sonnet (유일).
- **압축 폴백**: `rag_analysis/services/context_compressor.py` LLM 실패 → token 추정 truncate.
- **결과 폴백**: `news/services/keyword_extractor.py` LLM 실패 → 3개 generic 키워드.
- **캐시 재사용**: `serverless/services/keyword_generator.py` Semantic Cache (7일 TTL).

### 8) Gemini 핫스팟 요약

| 순위 | 위치 | 문제 | 영향 |
|---|---|---|---|
| 1 | rag_analysis/services + serverless/keyword_generator (async) | Celery fork에서 asyncio loop 수동 생성 | SIGSEGV/경쟁 조건 (버그 #8 재발 위험) |
| 2 | 전사 | request timeout 부재 | 단일 호출 hang → Celery worker 점유 |
| 3 | thesis/prompt_builder, validation/llm_peer_filter, csv_url_resolver | 429 미처리 + 재시도 없음 | free tier 한계 격돌 시 silent skip |
| 4 | 다수 (펜스 제거 미적용) | JSONDecodeError → 빈 결과 | LLM이 정상 응답해도 사후 파싱 실패 |
| 5 | 단일 provider | Anthropic 폴백은 portfolio만 | Gemini 장기 장애 시 다수 모듈 정지 |

---

## 기타 의존성

### FRED API (`macro/services/fred_client.py`)

- **상태**: 🟢 양호.
- **재시도**: 3회 exp backoff (2/4/6초), 영구 오류(401/403/404) 즉시 실패, 일시적(500/502/503/504)만 재시도 (`fred_client.py:98-155`).
- **Rate limit**: 120 req/min 한도 → `rate_limiter.acquire()` 적용 (line 101).
- **부분 실패 격리**: 지표별 try/except로 일부 실패해도 전체 대시보드는 계속 채움.
- **위험**: 전체 대시보드 한 번 실패 시 에러 필드만 반환되는 응답 (line 77-85) — UI 측 처리 필요.

### Neo4j (Chain Sight)

- **드라이버**: `rag_analysis/services/neo4j_driver.py` — Lazy Singleton, 연결 실패 시 `None` 반환 → 호출 측에서 `is_available()` 체크 후 빈 결과 반환 (Graceful).
- **Celery fork 안전성**: `config/celery.py:36-54, 84-99` — `worker_process_init`에서 드라이버 참조 해제 + macOS 환경 `--pool=solo` 강제. 별도 `neo4j` 큐로 격리.
- **트랜잭션 재시도**: ❌ 단발 호출 (실패 시 로그 + False/[]).
- **위험**: SPOF — Neo4j 다운 시 Chain Sight 전체 비활성. `sync_from_postgres()` (line 531)에서 FMP 오류는 무시하고 진행.

### SEC EDGAR (`sec_pipeline/collector.py`)

- **Rate limit**: 10 req/sec → 모든 요청 직전 0.12초 sleep (line 130, 151).
- **User-Agent**: 필수 헤더 설정 (`SEC_HEADERS`, line 29).
- **에러 처리**: 단발 raise (재시도 없음, line 86-91, 154-159).
- **Fallback**: 정규식 추출 실패 시 `edgartools` 라이브러리로 재시도 (line 256-269).
- **위험**: SEC 503/502/403 시 즉시 실패 (Celery autoretry로만 보완).

### Marketaux / Finnhub (뉴스)

- **상태**: 🟢 양호 (provider 페일오버 + circuit breaker 보유).
- **Rate limit**: Marketaux 2,500/day(10초 간격), Finnhub 60/min(1초 간격).
- **Provider 페일오버**: `config/settings.py NEWS_PRIMARY_PROVIDER='finnhub'` → 실패 시 Marketaux 자동 전환.
- **Circuit Breaker**: `news/services/circuit_breaker.py` — Redis 기반, threshold=5, timeout=300초. **현재 유일하게 CB가 구현된 영역**.

### Redis (캐시 + Celery broker)

- **설정**: cache `redis://127.0.0.1:6379/1`, broker/result `redis://localhost:6379/0`.
- **장애 처리**: ⚠️ 약함 — `cache.get()` 호출에 명시적 timeout/fallback 없음. 일부(`macro_service.py:50-73`)만 try/except로 우회.
- **Celery 영향**: broker 장애 시 큐 전체 정지. `CELERY_RESULT_BACKEND`가 redis와 django-db로 중복 정의된 흔적이 있어 검증 필요.

### PostgreSQL

- **연결 관리**: `config/celery.py:84-99` — fork 후 `db.connections.close_all()` (버그 #25 대응).
- **재시도**: ❌ Celery autoretry 미설정 — DB 일시 장애 시 태스크 영구 실패.
- **트랜잭션**: `transaction.atomic()` 사용처는 자동 롤백.
- **위험**: 전체 read/write의 SPOF.

### Alpha Vantage

- 본 코드베이스에서 직접 호출 흔적 미발견 (CLAUDE.md `coding-rules.md`에서만 언급). FMP 단독 의존 상태.

---

## Circuit Breaker 후보

도입 우선순위 = (장애 시 영향 범위) × (현재 핸들링 부실도) × (호출 빈도).

| 우선순위 | 후보 | 근거 | 도입 패턴 |
|---|---|---|---|
| 🔥 P0 | **`serverless/services/fmp_client.py`** | EOD/Screener/Chain Sight의 핵심. 재시도·CB 없음 + 캐시 miss 시 burst. FMP 일시 장애가 곧 서비스 정지로 이어짐. | 키 단위(symbol)별 CB 또는 provider 단위 CB |
| 🔥 P0 | **`api_request/providers/fmp/client.py`** | 모든 stocks·thesis 동기화의 진입점. 재시도는 있으나 장기 장애 시 무한 backoff. | global FMP CB (`news/services/circuit_breaker.py` 패턴 재사용) |
| 🔥 P0 | **Gemini 통합 게이트웨이** (`portfolio/llm/client.py` 확장) | Gemini를 호출하는 모든 모듈(thesis, news, serverless, validation, sec_pipeline)에 timeout·CB 부재. free tier 격돌 시 cascade. | 모든 Gemini 호출을 `portfolio/llm/client.py`로 단일화 후 CB 적용 |
| 🟠 P1 | **`macro/services/fmp_client.py`** | 재시도 없음 + HTTPError 미분류. macro 대시보드 결손. | provider 단위 CB |
| 🟠 P1 | **`news/providers/fmp.py`** | Exception 무시. 이미 news CB 존재하므로 통합만 하면 됨. | 기존 `news/services/circuit_breaker.py` 적용 확대 |
| 🟠 P1 | **`sec_pipeline/collector.py`** | 재시도 없음 + 503/502/403 명시 처리 없음. 10-K 파이프라인 결손. | SEC 단위 CB + tenacity retry |
| 🟡 P2 | **`serverless/services/neo4j_chain_sight_service.py`** | Lazy Singleton + is_available() 패턴이 부분적 graceful. 트랜잭션 단발 실패에 약함. | 트랜잭션 재시도 + 회로 차단 |
| 🟡 P2 | **Redis 캐시 호출 전반** | timeout 미설정. 캐시 hang 시 모든 요청 지연. | client-side timeout (200ms) + try/except 우회 |
| 🟢 P3 | **`serverless/services/keyword_generator.py` 등 async Gemini** | Celery fork-safety 우려는 CB보다 SDK 호출 패턴 정정이 우선. | sync 래퍼로 수렴 후 CB 적용 |
| ⛔ NA | **PostgreSQL** | CB보다 Celery autoretry + connection pool 튜닝이 적합. | retry policy |
| ⛔ NA | **FRED** | 이미 retry + rate_limiter 견고. CB 추가 이득 적음. | (현행 유지) |

### 권장 통합 전략

1. **공통 CB 모듈 추출**: `news/services/circuit_breaker.py`(Redis 기반, threshold=5, timeout=300s)를 공유 모듈(`shared/circuit_breaker.py` 또는 `api_request/circuit_breaker.py`)로 승격.
2. **Gemini 단일 게이트웨이**: 모든 Gemini 호출을 `portfolio/llm/client.py`로 통합, request_options timeout(예: 120s) + CB + Anthropic 폴백 일원화.
3. **FMP 단일 게이트웨이**: `api_request/providers/fmp/client.py`에 CB를 추가하고, `serverless/`·`macro/`·`news/`의 자체 client는 이 게이트웨이를 통해 호출하도록 정리.
4. **Silent failure 제거**: `serverless/services/data_sync.py`의 빈 dict/list 반환을 `None` 또는 명시적 `Result(success=False)`로 교체하여 호출자가 실패를 인지하도록.

---

## 종합 평가

| 카테고리 | 위험도 | 비고 |
|---|---|---|
| FMP 단일 의존 (FALLBACK_CHAIN 비어있음) | 🔴 매우 높음 | 장기 장애 시 EOD/Screener/Chain Sight/Macro 전부 정지 |
| Gemini timeout 부재 | 🔴 매우 높음 | Celery worker hang 가능 |
| Gemini async/Celery 혼용 | 🟠 높음 | 버그 #8 재발 위험 |
| serverless silent failure | 🟠 높음 | 데이터 결손 무인지 |
| Redis 캐시 timeout 부재 | 🟡 중 | 일시 캐시 장애 시 응답 지연 |
| Neo4j SPOF | 🟡 중 | graceful 패턴은 있으나 단일 점 의존 |
| FRED·뉴스 페일오버·Celery DB | 🟢 낮음 | 현행 패턴 양호 |

### 즉시 권장(높은 ROI)
1. Gemini 호출 전반에 `request_options.timeout` 일괄 부여 (120초).
2. JSON 파싱 전 markdown 펜스 정제 helper를 공유 모듈로 도입.
3. `news/services/circuit_breaker.py`를 공용 모듈로 승격 후 FMP·Gemini로 확대.
4. `serverless/services/data_sync.py`의 silent failure 패턴 제거.
5. Celery 태스크에 DB·Gemini 일시 장애를 위한 `autoretry_for` + `retry_backoff` 일괄 적용.

### 중기 권장
- FMP 단일 의존 해소: Alpha Vantage 또는 다른 데이터 provider를 `FALLBACK_CHAIN`에 등록.
- Gemini ↔ Anthropic 통합 게이트웨이를 모든 LLM 호출 경로의 표준으로 강제 (lint 또는 policy).
- Redis health check + cache miss-stale-while-revalidate 패턴 적용.

---

*감사 완료*
