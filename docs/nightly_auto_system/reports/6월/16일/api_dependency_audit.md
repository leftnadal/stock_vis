# 외부 API 의존성 감사 보고서

> **작성일**: 2026-06-16
> **유형**: 읽기 전용 감사 (코드 수정 없음)
> **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis 장애 대응 패턴
> **방법**: FMP 호출 ~39개 파일 + Gemini 호출 ~48개 파일 전수 조사 (grep `FMPClient|fmp_client|get_stock_service|StockService`, `generate_content|genai`)
>
> ⚠️ 일부 라인 번호는 탐색 시점 기준이며 ±몇 줄 오차 가능. 패턴/구조 결론은 다중 파일 교차 확인됨.

---

## 의존성 매트릭스

서비스별 외부 API × 장애 방어(Circuit Breaker / fallback / 재시도) 현황.

| 의존성 | 주요 호출 지점 | 장애 영향 범위 | Circuit Breaker | Fallback | 재시도 | Timeout |
|--------|---------------|---------------|:---------------:|:--------:|:------:|:-------:|
| **FMP (코어 클라이언트)** | `api_request/providers/fmp/client.py` | — (공통 인프라) | ❌ (호출자 책임) | ❌ | ✅ 3회 exp backoff | ✅ 30s |
| **FMP — Market Movers** | `serverless/.../data_sync.py` | 단일 (무버스 카드) | ✅ `fmp_market_movers` (5/120s) | ✅ 부분실패 허용 | (CB) | 30s |
| **FMP — S&P500 constituents** | `stocks/services/sp500_service.py` | 단일 (S&P 동기화) | ✅ `fmp_sp500_constituents` (3/300s) | ✅ 빈결과 | (CB) | 30s |
| **FMP — S&P500 EOD** | `stocks/services/sp500_eod_service.py` | 단일 (EOD 가격) | ✅ `fmp_sp500_eod` (10/120s) | ✅ 종목 스킵 | (CB) | 30s |
| **FMP — News** | `market_pulse/.../news_aggregator.py` | 단일 (뉴스) | ✅ `fmp_news` | ✅ 다중소스(Finnhub/Marketaux) | (CB) | 30s |
| **FMP — Screener / Filter** | `serverless/.../filter_engine.py` | 단일 (스크리너) | ❌ | ✅ 캐시 우선 | (코어 3회) | 30s |
| **FMP — Market Breadth** | `serverless/.../market_breadth_service.py` | 단일 (시장 건강도) | ❌ | ❌ | (코어 3회) | 30s |
| **FMP — Sector Heatmap** | `serverless/.../sector_heatmap_service.py` | 단일 (히트맵) | ❌ | ⚠️ 섹터별 continue | (코어 3회) | 30s |
| **FMP — Chain Sight** | `serverless/.../chain_sight_service.py` | 단일 (체인사이트) | ❌ | ✅ 캐시 1h + 부분실패 | (코어 3회) | 30s |
| **FMP — Macro 대시보드** | `market_pulse/.../macro_service.py` | 단일 (글로벌 마켓) | ❌ | ❌ (에러 응답) | (코어 3회) | 30s |
| **FMP — 재무 동기화 태스크** | `stocks/tasks.py` | 배치 | ❌ | ✅ DB 캐시값 | ⚠️ task별 상이 | 30s |
| **Gemini — Thesis Builder** | `thesis/services/thesis_builder.py` | 단일 (가설 빌더) | ✅ `gemini_thesis` (일부 경로) | ✅ rule fallback | (CB) | ❌ |
| **Gemini — Market Pulse 브리핑** | `market_pulse/briefing/client.py` | 단일 (브리핑) | ✅ `gemini` | ⚠️ task retry 3회 | (CB) | ❌ |
| **Gemini — RAG 압축** | `rag_analysis/.../context_compressor.py` | 단일 (RAG) | ✅ `acall()` | ✅ fallback_compress | (CB) | ❌ |
| **Gemini — RAG 엔티티/스트림** | `rag_analysis/.../entity_extractor.py`, `llm_service.py` | 단일 (RAG) | ❌ | ✅ rule 추출 | ⚠️ async retry 3 | ❌ |
| **Gemini — Keyword 생성** | `serverless/.../keyword_service.py`, `keyword_generator*.py` | 단일 (키워드) | ❌ | ✅ FALLBACK_KEYWORDS | ❌ (선언만) | ❌ |
| **Gemini — LLM Relation** | `serverless/.../llm_relation_extractor.py` | 단일 (관계 추출) | ❌ | ❌ | ❌ | ❌ |
| **Gemini — Peer Filter** | `validation/.../llm_peer_filter.py` | 단일 (검증 필터) | ❌ | ⚠️ except만 | ❌ | ❌ |
| **Gemini — SEC 추출** | `sec_pipeline/extractor.py`, `intelligence.py` | 단일 (SEC 분석) | ❌ | ⚠️ JSON 검증 | ❌ | ❌ |
| **Gemini — Korean Overview** | `stocks/services/korean_overview_service.py` | 단일 (한글 요약) | ❌ | ⚠️ except만 | ❌ (RPM 4s) | ❌ |
| **Gemini — Portfolio LLM** | `portfolio/llm/client.py` | 단일 (포트폴리오) | ❌ | ✅ 1회 재시도+분류 | ✅ exp(1회) | ❌ |
| **FRED API** | `api_request/fred_client.py`, `macro_service.py` | 단일 (거시 카드) | ❌ | ✅ 캐시 + 기본값 | ✅ 3회 exp | ✅ 30s |
| **Neo4j** | `serverless/.../neo4j_chain_sight_service.py`, `rag_analysis/.../neo4j_driver.py` | 단일 (그래프) | ✅ (5/60s) + lazy init | ✅ 빈결과 + 캐시 | (CB) | ✅ 60s pool |
| **SEC EDGAR** | `sec_pipeline/collector.py` | 단일 (10-K 섹션) | ❌ | ✅ regex→edgartools | ❌ 예외 전파 | ✅ 30/60s |
| **Redis (캐시)** | `cache_decorators.py`, 전 서비스 | 성능 저하 | — | ✅ miss→원본 호출 | ✅ | — |
| **Redis (Celery 브로커)** | `config/settings.py` BROKER_URL | **전체 (큐 정지)** | ❌ | ❌ **없음** | — | — |
| **Redis (CB 상태저장)** | `circuit_breaker.py` cache.get/set | 광역 (CB 무력화) | — | ❌ Redis 필수 | — | — |

**범례**: ✅ 구현됨 · ⚠️ 부분/암시적 · ❌ 없음 · (CB) Circuit Breaker가 재시도 대행

---

## FMP 상세

### 코어 클라이언트 (`packages/shared/api_request/providers/fmp/client.py`)

가장 견고하게 설계됨. HTTP 상태 코드별 예외 분리가 명확하다.

| 항목 | 구현 | 근거 |
|------|------|------|
| 401/403 | `FMPAuthError` (즉시 전파, 재시도 X) | client.py:129–136, 156 |
| **402 (프리미엄)** | `FMPPremiumError` (즉시 전파, 재시도 X) | client.py:131–134, 156 |
| 429 (rate limit) | `FMPRateLimitError` (즉시 전파) | client.py:137–138, 156 |
| 응답 본문 "Error Message" | `Invalid API KEY` → AuthError, 그 외 → `FMPClientError` | client.py:148–152 |
| 재시도 | `requests.RequestException`/`FMPClientError`만 최대 3회 exp backoff (2·4·6s) | client.py:158–170 |
| 분당 rate limit | `request_delay=0.2s` 자동 sleep (300/min Starter 대응) | client.py:104–110 |
| 일일 한도 | `daily_calls >= 10000` → `FMPRateLimitError` | client.py:113–115 |
| timeout | `requests.get(timeout=30)` | client.py:124 |

> **설계 정합성**: 402/401/429를 재시도 대상에서 제외(즉시 전파)한 것은 CLAUDE.md 버그 #23(FMP 402 즉시 실패) 정책과 일치. **코어 자체는 fallback이 없음** — fallback은 호출자 책임 구조.

### 파생 클라이언트
- **`serverless_client.py`**: `httpx` 기반, `FMPAPIError`로 일괄 래핑. Redis 캐시 계층(quote 1m / movers 5m / historical 1h / profile 24h). S&P500 구성원은 datahub.io CSV로 대체(FMP Professional 미지원 회피).
- **`market_pulse_client.py`**: "Error Message" → `ValueError`로 호출자에 위임. gainers/losers 독립 try-except로 부분 실패 허용.
- **`provider.py`** (추상화): `FMPPremiumError` 캐치 후 로그 + `ProviderResponse.error_response()` 반환. **fallback_chain은 비어 있음** (대체 Provider 미연결).
- **`stock_service.py`**: 프로필 조회 실패 시 **DB에 저장된 기존 Stock 데이터 반환**(stock_service.py:214–230) — 유일하게 의미 있는 데이터 fallback.

### 배치/태스크 레이어 (`stocks/tasks.py`)
| 태스크 | 재시도 | 비고 |
|--------|--------|------|
| `update_stock_with_provider` | ✅ `self.retry` (60s × (retries+1)), max_retries=3 | 양호 |
| `run_eod_pipeline` | ✅ `self.retry(countdown=120×)`, max_retries=2 | 양호 |
| **`update_financials_with_provider`** | ❌ **max_retries 없음, except 로그만** | ⚠️ 실패 시 즉시 소실 |
| `sync_sp500_financials` | ❌ (스케줄링만, 7s 간격 분산) | rate limit 보호용 분산은 있음 |

### FMP 위험 지점 요약
| 위험도 | 파일 | 문제 |
|:------:|------|------|
| 🔴 HIGH | `serverless/.../filter_engine.py` | FMP 호출에 try/except·CB 없음 → 402/429 시 스크리너 전체 실패 |
| 🔴 HIGH | `serverless/.../market_breadth_service.py` | gainers/losers/actives 직접 호출, CB·fallback 없음 |
| 🔴 HIGH | `stocks/tasks.py` `update_financials_with_provider` | Celery retry 미설정 → 일시 장애 = 영구 누락 |
| 🟠 MED | `serverless/.../sector_heatmap_service.py` | Exception만 캐치, fallback 없음 |
| 🟠 MED | `market_pulse/.../macro_service.py` | Exception → 전체 에러 응답 (섹션별 부분 반환 없음) |

---

## Gemini 상세

### 전반 평가
- ✅ **동기 API 규칙(버그 #8) 대체로 준수**: Celery에서 호출되는 경로(`thesis_builder`, `keyword_service`, `extractor`, `briefing` 등)는 `client.models.generate_content` 동기 호출.
- ⚠️ **async 함수 잔존**: `keyword_generator.py`/`keyword_generator_v2.py`(`async def`), `rag_analysis/llm_service.py`·`adaptive_llm_service.py`(`generate_stream` async). 현재 웹 API용으로 보이나, **Celery 태스크에서 호출되면 버그 #8 재발 위험** → 호출 경로 확인 필요.
- ❌ **Circuit Breaker 적용 3곳뿐**: `thesis_builder`(`gemini_thesis`, 일부 경로만), `briefing/client`(`gemini`), `context_compressor`(`acall`). 나머지 다수는 직접 호출.
- ❌ **Timeout 전무**: 모든 Gemini 호출에 `request_options`/timeout 미설정 → SDK 기본값 의존. 응답 지연 시 워커 점유.
- ⚠️ **RPM 준수 방식 불완전**: `relationship_keyword_enricher`/`korean_overview_service`/`news_deep_analyzer`가 `time.sleep(4s)`(=15 RPM)로 직렬 제어. 단, 배치를 병렬화하면 무효 → 429 위험.
- ❌ **Safety block 미감지**: `response.prompt_feedback.block_reason` 확인하는 곳 없음. 안전필터 차단 응답이 빈 텍스트로 통과 가능.

### 호출 처리 패턴별 분류

**우수 (Structured Output + CB + fallback)**
- `thesis_builder.py:538–598` — `response_mime_type=application/json` + `get_circuit('gemini_thesis')` + rule fallback.
- `entity_extractor.py:69–137` — markdown fence 제거(`_clean_json_response`) → `json.loads` → `JSONDecodeError` 캐치 → rule 추출 fallback. **JSON 파싱 모범 사례.**
- `context_compressor.py:97–141` — `asyncio.gather(return_exceptions=True)` + CB `acall` + `_fallback_compress`.
- `portfolio/llm/client.py:61–125` — `_classify_gemini_error`로 RateLimit/Timeout/Auth/InvalidPrompt 분류 후 RateLimit/Timeout만 1회 재시도 + 비용 가드(`LLM_BUDGET_MAX_CALLS`).

**미흡 (except만 / fallback·CB 없음)**
- `llm_relation_extractor.py` — `JSONDecodeError` 캐치하나 CB·재시도·fallback 없음.
- `llm_peer_filter.py:56–90` — 함수 호출마다 `genai.Client()` 신규 생성(비효율) + except만.
- `keyword_service.py` — `max_retries=2` **선언만, 실제 재시도 루프 없음**. FALLBACK_KEYWORDS는 있음.
- `thesis/tasks/summary.py:55–77` — Celery 태스크 내 동기 호출은 OK이나 generic except만, RPM 대기·CB 없음.

### JSON 파싱 / 빈 응답 처리
- **빈/None 응답 fallback 있음**: `thesis_builder`, `context_compressor`, `entity_extractor`, `keyword_service`, `news/keyword_extractor` 모두 빈 응답 시 fallback 데이터 반환 → 양호.
- **Markdown fence 제거 편차**: `entity_extractor`는 제거 로직 있음, `keyword_service` 등은 `response.text` 직접 `json.loads` → 모델이 ```json 펜스를 붙이면 파싱 실패 가능.

### 클라이언트 생성 일관성
공통 래퍼 부재. 각 서비스가 제각각 `genai.Client()` 생성(lazy init / `__init__` / 함수 레벨 혼재). `portfolio/llm/client.py`의 `LLMClient`(Gemini+Anthropic 통합)가 가장 발전된 형태이나 portfolio 전용. **표준 래퍼 1개로 통일 시 CB·timeout·RPM·safety 검사를 한 곳에서 강제 가능.**

---

## 기타 의존성

### FRED API — 가장 탄력적 ✅
- `fred_client.py:98–156` — max_retries=3, exp backoff(2/4/6s), 5xx만 재시도·401/403/404 즉시 실패.
- `rate_limiter.py` — 100 req/min(안전 마진) + 호출 간 0.6s.
- `macro_service.py:56–91` — `cache.get` → FRED → `cache.set`(TTL 60s~7d), 실패 시 **기본값 반환**(VIX=20, spread=1.0). 예외 전파 안 함.
- timeout 30s. **재시도+rate limit+캐시+기본값 4중 방어**.

### Neo4j — Circuit Breaker 격리 ✅
- `neo4j_driver.py:20–74` — lazy init, 연결 실패 시 `_driver=None`(앱은 계속). `force_reset_after_fork`로 Celery fork 안전.
- `neo4j_chain_sight_service.py:67–143` — `is_available()`(driver None 또는 CB OPEN 체크) + `_run_with_cb`로 모든 쿼리 wrap. CB 5회 실패/60s 복구.
- 비가용 시 `[]`/`{}` 반환 + 캐시 fallback(5m). **Neo4j 다운 ≠ API 다운** — 격리 양호.
- 드라이버 풀: lifetime 3600s, pool 50, timeout 60s. `with session()` 명시적 close.

### SEC EDGAR — rate limit 준수, 재시도 약함 ⚠️
- `collector.py` — `time.sleep(0.12)`(10 req/s 제한 준수), User-Agent 헤더 필수, timeout 30/60s.
- 3단계 섹션 추출(regex 3패턴 → 가장 긴 것) 실패 시 **edgartools fallback**(선택적 의존성) → 최악 `partial`/`failed` 상태 반환.
- **`RequestException`은 캐치 후 재발생(raise)** — 자체 재시도 없음, 상위 Celery 레이어에 위임. rate limit/네트워크 오류 시 태스크 단위 실패.

### Redis — 부분적으로 단일 실패점 ⚠️
| 용도 | 장애 시 | 평가 |
|------|---------|------|
| 캐시 | `cache.get`=None → 원본 API 재호출 | ✅ graceful (성능만 저하) |
| Rate Limiter | pipeline 실패 → `cache.get/set` fallback, 예외 전파 안 함 | ✅ 부분 |
| **Circuit Breaker 상태** | CB state를 `cache.get/set`(Redis)에 저장 | ⚠️ **Redis 다운 시 CB 상태 조회 불안정 → CB 자체 무력화 가능** |
| **Celery 브로커** | `BROKER_URL=redis://...:6379/0`, fallback 없음 | 🔴 **Redis 다운 = 신규 태스크 큐잉 전면 정지** |
| Celery 결과 | `RESULT_BACKEND=django-db`(PostgreSQL) | ✅ Redis 회피 (양호) |

---

## Circuit Breaker 후보

장애 시 영향 범위·호출 빈도·현재 방어 공백 기준 우선순위.

### 🔴 1순위 — 즉시 도입 권장
1. **`serverless/.../filter_engine.py` (Screener)**
   - 사용자 직접 노출 스크리너. FMP 직접 호출에 try/except·CB 전무.
   - 402/429 1회로 스크리너 전체 500. → `get_circuit("fmp_screener", 5, 120)`.
2. **`serverless/.../market_breadth_service.py` (Market Breadth)**
   - gainers/losers/actives 연속 호출, 누적 실패 방어 없음. EOD 대시보드 핵심 지표.
3. **`stocks/tasks.py::update_financials_with_provider`**
   - CB 이전에 **Celery `max_retries` 부터** 부재 → 일시 장애가 영구 데이터 누락. retry + (선택)CB.

### 🟠 2순위 — Gemini 광역 공백
4. **Gemini 공통 래퍼 + CB 통합**
   - `keyword_service` / `llm_relation_extractor` / `llm_peer_filter` / `korean_overview_service` / `sec_pipeline/extractor` — CB·timeout 없음.
   - 개별 도입보다 **표준 `GeminiClientWrapper`(CB + timeout + RPM RateLimiter + safety block 검사)** 1개로 통일 권장. 15 RPM 한도라 한 서비스 폭주가 다른 서비스 429 유발 → 공유 CB의 가치 큼.

### 🟡 3순위 — 안정성 보강
5. **SEC EDGAR `collector.py`** — 자체 재시도(현재 raise만) 또는 CB로 SEC 5xx/rate-limit 시 백오프.
6. **`macro_service.py` (FMP 글로벌 마켓)** — 섹션별 부분 반환 + CB로 전체 에러 응답 방지.

### 인프라 레벨 (CB 외 대응)
7. **Celery 브로커 Redis 단일 실패점** — CB로 해결 불가. RabbitMQ/PostgreSQL 브로커 이중화 또는 Redis HA(Sentinel) 검토.
8. **Circuit Breaker 상태저장의 Redis 의존** — Redis 다운 시 모든 CB가 함께 무력화되는 순환 의존. 인메모리 1차 + Redis 2차 하이브리드 상태저장 검토.

---

## 종합 결론

**강점**
- FMP 코어 클라이언트의 HTTP 상태 코드별 예외 분리(402/401/429 즉시 전파, 나머지 exp backoff)는 견고.
- FRED(4중 방어)·Neo4j(CB 격리)는 graceful degradation 모범.
- Gemini 동기 API 규칙(버그 #8)·빈 응답 fallback은 대체로 준수.

**핵심 공백 (우선순위순)**
1. 🔴 FMP Screener/Market Breadth/재무 태스크 — CB·재시도 공백, 단일 호출 실패가 기능 전체 다운으로 직결.
2. 🔴 Celery 브로커 Redis 단일 실패점 + CB 상태저장의 Redis 순환 의존.
3. 🟠 Gemini 호출의 분산된 방어(CB 3곳뿐, timeout 0곳, RPM 직렬 sleep) — 표준 래퍼로 통일 필요.
4. 🟡 SEC EDGAR 자체 재시도 부재, Gemini safety block 미감지.

> 본 보고서는 읽기 전용 감사이며 어떤 코드도 수정하지 않았습니다.
