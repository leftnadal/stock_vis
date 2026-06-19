# 외부 API 의존성 감사 보고서

> **감사일**: 2026-06-19
> **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis` (모노레포: `apps/`, `services/`, `packages/shared/`, `thesis/`)
> **범위**: FMP(35+ 파일) · Gemini/LLM(29+ 파일) · FRED · Neo4j · SEC EDGAR · Redis
> **방식**: 읽기 전용 정적 코드 감사 (코드 수정 없음). 5개 병렬 조사 그룹 + 직접 grep 검증.
> **신뢰도**: 코드 evidence(file:line) 기반. 일부 line 번호는 조사 시점 기준이며 ±수 라인 오차 가능.

---

## 요약 (Executive Summary)

| 구분 | 핵심 발견 |
|------|----------|
| 🔴 **공통 최대 위험** | **Gemini 호출 전반에 명시적 `timeout` 미설정** (7+ 코어 / 18+ 소비자 파일) → 네트워크 지연 시 무한 대기 가능. Celery 워커 점유 → 큐 정체 연쇄. |
| 🔴 **단일 장애점(SPOF)** | **Redis** = 캐시 + Celery 브로커 겸용 단일 인스턴스(클러스터/Sentinel 없음). 브로커 다운 시 **모든 비동기/스케줄 작업 정지 + 무알림 silent failure**. |
| 🟠 **방어 불일치** | Circuit Breaker는 **13개 지점만** 부분 도입(`get_circuit`). 같은 도메인 내에서도 상위 호출엔 CB, 하위 개별 호출(quote/profile)엔 CB 없음 → CB 무력화. |
| 🟠 **429 처리 편차** | FMP 429 재시도는 `fmp_screener.py`만 완비. Gemini 429 재시도는 `keyword_service.py`·`portfolio/llm`·`llm_service.py` 등 소수만. **대다수 LLM 소비자는 429 미처리.** |
| 🟡 **Silent failure 패턴** | 실패 시 `return []` / `return None`을 광범위 사용 → "데이터 없음"과 "조회 실패"를 사용자가 구분 불가. `news_deep_analyzer`는 실패를 `llm_analysis=None, llm_analyzed=True`로 기록(black-hole). |
| ✅ **양호 영역** | `apps/portfolio/llm/client.py`(에러 분류 + Anthropic fallback + CostGuard), `fred_client.py`(timeout+retry+rate limit), `entity_extractor.py`(JSON 코드펜스 제거 + 규칙 fallback)는 모범 사례. |

---

## 의존성 매트릭스

| 의존성 | 유형 | Timeout | Retry/Backoff | Rate Limit | Circuit Breaker | Fallback / Graceful Degrade | 다운 시 사용자 영향 |
|--------|------|---------|---------------|-----------|-----------------|------------------------------|---------------------|
| **FMP (client.py)** | HTTP REST | ✅ 30s | ✅ 3회, exp `(n+1)*2s` | ✅ `request_delay` 0.2s + 일일한도 | △ 일부 호출처만 | ❌ 캐시 없음, raise 전파 | 종목/재무/시세 전반 |
| **FMP (serverless_client.py)** | HTTP (httpx) | ✅ 30s | 🔴 **없음** | 🔴 **없음** | ❌ | ✅ Django 캐시 + 빈값 | 서버리스 시세/스크리너 |
| **FMP (market_pulse_client.py)** | HTTP REST | ✅ 30s | 🔴 **없음** | 🔴 **없음**(개별요청으로 우회) | ❌ | ✅ 캐시 + `return None` | 거시/지수 대시보드 |
| **Gemini (market_pulse/llm)** | LLM | 🔴 **없음** | △ CB만 | — | ✅ `gemini` | △ CB open → 에러 전파 | 일일 브리핑/뉴스레터 |
| **Gemini (portfolio/llm)** | LLM | 🔴 **없음** | ✅ 1회 + 분류 | — | ❌ | ✅ **Anthropic fallback + CostGuard** | 포트폴리오 분석 |
| **Gemini (rag_analysis)** | LLM | 🔴 **없음** | △ 파일별 편차(0~3회) | — | △ 일부 | △ truncate/규칙 fallback | RAG 투자 분석 전체 |
| **Gemini (thesis)** | LLM | 🔴 **없음** | 🔴 **없음** | — | ✅ `gemini_thesis`만 | ✅ wizard/fallback 파싱 | 가설 빌더 |
| **Gemini (serverless/news/sec)** | LLM | 🔴 **없음** | 🔴 대부분 없음 | △ RPM sleep 일부 | ❌ | △ 파일별 편차 | 키워드/관계/SEC 추출 |
| **FRED** | HTTP REST | ✅ 30s | ✅ 3회 exp `2/4/6s` | ✅ 120/min 매뉴얼 | ❌ | ✅ 기본값(fear=50) + `{error}` | Market Pulse 부분 |
| **Neo4j** | Graph DB | ✅ 60s acquire | △ 1회(호출자 위임) | — | ✅ 5fail→OPEN 60s | ✅ `is_available()` 가드 → `[]` | Chain Sight 그래프 |
| **SEC EDGAR** | HTTP REST | ✅ 60s/30s | 🔴 **없음** | ✅ 0.12s sleep(10/s) | ❌ | △ edgartools fallback | SEC 파이프라인(배치) |
| **Redis 캐시** | In-Memory | pool | 🔴 없음 | — | ❌ | ✅ miss → 재계산 | 응답 지연(2~5s) |
| **Redis 브로커** | Celery MQ | pool | 🔴 없음 | — | ❌ | 🔴 **없음** | **모든 async/beat 정지** |

> 범례: ✅ 완비 / △ 부분·편차 / ❌ 없음(영향 낮음) / 🔴 없음(위험)

---

## FMP 상세

### 1. 코어 클라이언트 — 3종 구현, 방어 수준 제각각

FMP 클라이언트가 **3개 구현으로 분화**되어 있고 각각 방어 수준이 다른 것이 근본 문제다.

| 클라이언트 | HTTP | Timeout | Retry | Rate Limit | 402 처리 | 캐시 |
|-----------|------|---------|-------|-----------|---------|------|
| `client.py` | requests | ✅ 30s | ✅ 3회 exp backoff | ✅ delay+일일한도 | ✅ `FMPPremiumError` 즉시 raise (402 감지, L131-134) | ❌ |
| `serverless_client.py` | httpx | ✅ 30s | 🔴 없음 | 🔴 없음 | 🔴 generic `FMPAPIError`로 뭉뚱그림 | ✅ |
| `market_pulse_client.py` | requests | ✅ 30s | 🔴 없음 | 🔴 없음 | 🔴 미처리(배치→개별 요청 우회) | ✅ |

- **예외 클래스 정의**: `client.py:27/33/39` — `FMPRateLimitError`, `FMPAuthError`, `FMPPremiumError` 정의 존재. 단 **`serverless_client`/`market_pulse_client`는 이를 사용하지 않음**.
- **`client.py` 버그 후보**: `L172 raise last_error` — retry 루프에서 예외 없이 빠져나오면 `last_error` 미초기화 → `UnboundLocalError` 가능. `L143 raise_for_status()`는 위 if-elif에 의해 도달 불가(dead code).
- **`provider.py`**: `FMPClient`를 선택하지만 client.py / serverless_client.py 중 무엇을 쓰는지 호출 경로에 따라 방어 수준이 갈림. FMPPremiumError → `ProviderResponse.error_response(error_code="PREMIUM_ONLY")` 변환은 양호(L233-239).
- **`stock_service.py`**: `FALLBACK_CHAIN[FMP] = []` — **대체 provider 전무**. FMP 실패 시 DB 기존 데이터 재사용 외 복구 경로 없음. DB 저장 시 `IntegrityError`를 warning만 남기고 continue → silent failure(L444-446).

### 2. 소비자 계층 — 핵심 위험 우선순위

| 순위 | 위험 | 위치 | 영향 |
|------|------|------|------|
| **P0** | **402 Premium 배치 미처리** | `fmp_exchange_quotes.py:155-189`, `market_pulse_client.py:146-164` | 콤마 배치 1건 402 → 배치 전체 손실 |
| **P0** | **실패를 `return []`로 무음 처리** | `fmp_fundamentals.py:62-99`(key_metrics/ratios/balance_sheet 전부), `fmp_screener.py` enrich | "데이터 없음" vs "조회 실패" 구분 불가, 자동 재시도 불가 |
| **P0** | **시총 가중 = 500종목 × 개별 quote** | `weight_source.py:55-105`, `fmp_weights.py` | 500콜 순차(100s+), CB 없음, FMP 300/min 압박 |
| **P1** | **`update_financials_with_provider` max_retries 없음** | `tasks.py:551-577` (`rate_limit="6/m"`만, 실패 시 raise 없이 로깅) | 종목별 재무 미업데이트 silent fail |
| **P1** | **CB 부분 도입 / 하위 호출 누락** | `sp500_eod_service.py:138`(CB有) vs `_ensure_stock_exists` profile 조회(CB無), `data_sync.py:75`(상위 CB) vs `_process_item` get_quote(CB無) | 상위 CB OPEN돼도 하위는 계속 실패 |
| **P1** | **거시 대시보드 부분실패 불허** | `macro_service.py:220-259` (FMP 5개 호출 중 1개 실패 → 전체 `{error}`) | 글로벌 시장 대시보드 통째 실패. cf. `market_breadth_service`는 항목별 `[]` 허용(양호) |
| **P2** | **캐시 fallback 불일치** | `fmp_screener`만 429 retry + stale 캐시 fallback. `fmp_fundamentals`/`fmp_exchange_quotes`는 둘 다 없음 | 동작 예측 불가 |
| **P3** | **`.` 심볼 무음 제외** | `tasks.py:164-167` (BRK.B/BF.B 등 skip, info 로그만) | S&P500 3~5종목 누락 |

### 3. Rate Limit 준수 평가

- **`fmp_screener.py:152-237`**: 429 감지 → `Retry-After` 헤더 존중 → exp backoff(최대 30s) → stale 캐시 fallback. **유일하게 완비된 모범 사례.**
- 그 외 다수 소비자: rate limit 슬립이 `countdown`(Celery 큐 지연)에 의존 → 병렬 워커 多 시 분당 300콜 돌파 가능(`tasks.py:191-196`).

---

## Gemini 상세

### 1. 공통 위험: Timeout 전면 부재 (Critical)

**모든 `genai.Client().models.generate_content*()` 호출에 명시적 timeout 없음.** `max_output_tokens`는 설정하나 이는 timeout이 아니다.

| 파일 | Line | 영향 |
|------|------|------|
| `apps/market_pulse/llm/client.py` | 56 | 브리핑 무한 대기 |
| `apps/portfolio/llm/client.py` | 271-275 | 포트폴리오 분석 정지 |
| `services/rag_analysis/services/llm_service.py` | 205-210 | RAG 스트리밍 정지 |
| `services/rag_analysis/services/adaptive_llm_service.py` | 202, 255 | 적응형 분석 정지 |
| `services/rag_analysis/services/context_compressor.py` | 136 | 문서 압축 대기 |
| `services/rag_analysis/services/entity_extractor.py` | 90-94 | 엔티티 추출 정지 |
| `packages/shared/stocks/services/korean_overview_service.py` | 62 | 한글 개요 배치 정지 |
| `thesis/services/prompt_builder.py` | 581/808/977 | 가설 빌더 정지 |
| `services/sec_pipeline/extractor.py` | 70/133 | SEC 추출 정지 |

> Celery 동기 호출(`genai.Client` sync)은 규칙(Bug #8) 준수 측면에선 대부분 OK이나, **timeout 부재 + Celery 워커 = 워커 점유 → 큐 정체** 연쇄 위험.

### 2. Async 금지 규칙(Bug #8) 위반 후보

- **`services/serverless/services/keyword_generator_v2.py:377-413`**: `generate_keywords_sync_v2()`가 Celery에서 `asyncio.run_until_complete()`로 async `genai.aio.*` 호출 → **fork 환경 SIGSEGV 위험(Bug #8/#25)**. 명시적 점검 필요.
- `adaptive_llm_service.py`: `genai.configure()`(구 SDK) + `GenerativeModel().generate_content_async()` 혼용(L88, L183, L202) → async 경로. 호출 컨텍스트(웹/Celery) 확인 필요.

### 3. 429 / 재시도 처리 현황

| 처리 수준 | 파일 |
|-----------|------|
| ✅ **완비**(exp backoff + 분류) | `serverless/services/keyword_service.py:324-330`, `apps/portfolio/llm/client.py:61-94`, `rag_analysis/llm_service.py`(3회 1/2/4s) |
| △ **CB 위임만**(개별 retry 없음) | `market_pulse/llm/client.py:73`, `thesis/services/thesis_builder.py:470`(`gemini_thesis`), `rag_analysis/context_compressor.py` |
| 🔴 **미처리** | `prompt_builder.py`(3개 call_* 전부), `indicator_matcher.py`, `news_deep_analyzer.py`, `keyword_extractor.py`, `sec_pipeline/extractor.py`, `regulatory_service.py`, `llm_relation_extractor.py`, `llm_peer_filter.py`, `thesis/tasks/summary.py`, `conversation_views.py`, `korean_overview_service.py` 등 12+ |

### 4. JSON 파싱 에러 처리

- ✅ **복구 시도(정규식/코드펜스 제거)**: `entity_extractor.py:_clean_json_response`, `keyword_service.py:368-379`, `keyword_extractor.py:356-369`, `llm_relation_extractor.py:_recover_from_partial_json`, `sec_pipeline/intelligence.py:182-197`(fallback 객체).
- 🔴 **복구 없이 raise/None**: `korean_overview_service.py:75`(JSONDecodeError → raise → 배치 중단), `prompt_builder.py`(→None), `sec_pipeline/extractor.py:79`(→error), `llm_peer_filter.py:86`(→error), `news_deep_analyzer.py:251`(→None).

### 5. 장애 전파 — 영향도별

| 영향도 | 기능 | 근거 |
|--------|------|------|
| **고** | 일일 브리핑/뉴스레터 미발송 | `market_pulse/llm` CB open → 에러 전파, 재시도 없음 |
| **고** | RAG 투자 분석 중단 | `rag_analysis/pipeline.py:323-328` LLM 에러 시 재시도 0회, 즉시 종료 |
| **고** | 가설 빌더 중단 | `thesis_builder.py` free_input 파싱 실패 시 wizard fallback은 있으나 LLM 의존 |
| **중** | 뉴스 심층분석 black-hole | `news_deep_analyzer.py:89-90` 실패를 `llm_analysis=None, llm_analyzed=True`로 기록 → 재처리 안 됨 |
| **중** | Celery crash 위험 | `keyword_generator_v2` asyncio.run_until_complete |
| **저** | 지표 추천/한글 변환/규제 그룹 실패 | fallback 또는 원본 유지로 기능 지속 |

### 6. 비용(Cost) 가드

- ✅ **모범**: `apps/portfolio/llm/`은 `CostGuard`(slice cap $1.00 / threshold $4.00) + Gemini→Anthropic fallback. `rag_analysis/cost_tracker.py`는 일/월 한도 계산 보유(단 blocking은 warning 수준).
- 🔴 **공백**: `llm_service.py`/`adaptive_llm_service.py`/`context_compressor.py`는 토큰 추정만, 비용 기록·한도 미흡. 429 무한 재시도 + Anthropic fallback(단가 10×) 조합 시 비용 폭발 경로 존재.

---

## 기타 의존성

### A) FRED API — 양호

- **`packages/shared/api_request/fred_client.py`**: timeout 30s, retry 3회 exp backoff(2/4/6s), rate limiter 120/min, 영구오류(401/403/404) 즉시 raise / 일시오류(5xx) 재시도 분류. **FMP 코어보다 견고.**
- **`macro_service.py`**: `get_fear_greed_index` 실패 시 기본값(value=50, neutral) 반환. 대시보드 메서드는 `{error}` 반환 + 캐시(60~86400s)로 완충. 개별 series는 try/except로 조용히 skip.
- **위험**: macro_service의 글로벌 대시보드는 FMP와 FRED를 한 try 블록에 묶어 **FMP 1건 실패 → FRED 데이터까지 손실**(상기 FMP P1 참조).

### B) Neo4j — 격리 양호

- **Lazy init**(`neo4j_driver.py:20-74`): 연결 실패 시 `driver=None` 반환 → 모든 작업 자동 비활성. pool 50, lifetime 3600s, acquire timeout 60s, init 시 connectivity 검증.
- **CB 적용**(`neo4j_chain_sight_service.py:117/133`): 5 fail → OPEN 60s. `is_available()` 가드로 전 공개 메서드가 `False`/`[]`/`{nodes:[],edges:[]}` 반환.
- **영향 격리**: Neo4j 다운은 **Chain Sight 그래프 뷰만** 영향. watchlist/시세/뉴스 무관. PostgreSQL `StockRelationship` 모델은 잔존(단 쓰기는 Neo4j 필요).
- **약점**: 세션 단위 작업엔 명시적 retry 없음(1회 실패 → catch). 벌크 로드(`neo4j_loader.py`)는 항목별 실패를 0 카운트로 흡수 → 부분 동기화 silent.

### C) SEC EDGAR — 배치 격리, retry 부재

- **`services/sec_pipeline/collector.py`**: HTML 60s / API 30s timeout, **0.12s sleep로 10 req/s 규칙 준수**, User-Agent 헤더(`SEC_HEADERS`) 필수.
- **약점**: collector 레벨 **retry 없음** — 메타데이터/HTML fetch 실패 시 즉시 raise. `collect()`가 catch → `status='failed'`로 정리(L239-244). 1차 regex 실패 시 `edgartools` fallback(L189-215), 둘 다 실패 시 status=failed.
- **영향**: Celery 백그라운드 배치 → 사용자 요청 직접 차단 없음. 단 insider/regulatory 등 SEC 의존 데이터 지연(1일+). rate limit 히트 시 task 재시도는 Celery 설정에 의존.

### D) Redis — **최대 단일 장애점**

- **겸용 구조**(`config/settings.py:491-492, 507-510`): 브로커+백엔드(DB 0) + Django 캐시(DB 1)를 **단일 인스턴스**가 담당. 클러스터/Sentinel 없음.
- **캐시 다운(graceful)**: `BasicCacheService`는 try/except로 get/set 감싸 에러 시 `None` 반환 → miss 취급 → 원본 재계산. **사용자 영향 = 2~5s 지연**(견딜 만함).
- **브로커 다운(치명)**: 🔴 **graceful degradation 없음.** task 큐잉 실패 → Market Pulse/Chain Sight/News 동기화 beat 정지 → 대시보드 stale. **무알림 silent failure** — 모니터링/알림 부재가 가장 큰 운영 리스크.

---

## Circuit Breaker 후보

> 현재 CB 도입 지점(`get_circuit` 13곳): `fmp_sp500_constituents`, `fmp_sp500_eod`, `fmp_etf`, `fmp_news`, `marketaux`, `fmp_market_movers`(data_sync), `gemini`(market_pulse), `gemini_thesis`, `neo4j`(2), rag `context_compressor`/`llm_service`. CB 모듈: `packages/shared/api_request/circuit_breaker.py`.

### 우선순위 1 — 신규 도입 시급 (장애 시 시스템 전체 영향)

| 후보 | 위치 | 근거 |
|------|------|------|
| **Redis 브로커 헬스/알림** | `config/` + 모니터링 | SPOF. CB보다 **헬스체크 + 알림 + 페일패스트**가 우선. 브로커 무알림 정지가 최대 리스크. |
| **시총 가중 / ETF 가중 경로** | `weight_source.py:market_cap_weights`, `fmp_weights.py` | 500종목 순차 호출. `fmp_etf` CB는 있으나 `market_cap_weights`의 개별 quote 루프엔 CB 없음 → 누적 실패 시 전체 거시 지표 차단. |
| **RAG 파이프라인 LLM** | `rag_analysis/pipeline.py`, `adaptive_llm_service.py` | 재시도 0회 + timeout 없음. LLM 장애 시 RAG 분석 전체 정지 + 비용 폭발 경로. |
| **거시 글로벌 대시보드 FMP 묶음** | `macro_service.py:220-259` | 5개 FMP 호출 단일 try → 1건 실패로 전체 실패. 호출별 CB + 부분실패 허용 필요. |

### 우선순위 2 — 기존 CB 보강 (하위 호출 누락)

| 후보 | 위치 | 근거 |
|------|------|------|
| **EOD profile 조회** | `sp500_eod_service.py:_ensure_stock_exists` | 상위 `fmp_sp500_eod` CB 있으나 profile 호출은 CB 미적용. |
| **Market Movers 개별 quote** | `data_sync.py:_process_item` get_quote | 상위 `fmp_market_movers` CB 있으나 종목별 quote는 CB 미적용 → CB 무력화. |
| **CB threshold 재조정** | `fmp_sp500_eod`(threshold=10) | 500종목 기준 10 fail은 반응 지연. 5로 하향 검토. |

### 우선순위 3 — Gemini 소비자 표준화

| 후보 | 위치 | 근거 |
|------|------|------|
| **thesis prompt_builder 3종 call** | `prompt_builder.py:581/808/977` | 가설 빌더 핵심 경로, 429/timeout/CB 전무. `gemini_thesis` CB를 prompt_builder까지 확장. |
| **뉴스 심층분석** | `news_deep_analyzer.py` | black-hole 기록 패턴. CB + 실패 재처리 가능 상태로 변경. |
| **SEC extractor / llm_peer_filter** | `sec_pipeline/extractor.py`, `validation/llm_peer_filter.py` | 재시도·fallback 없이 error 객체만 반환. |

---

## 권장 조치 (우선순위 종합)

### P0 — 즉시
1. **모든 Gemini 호출에 timeout 명시**(권장 30s). 단일 공용 호출 래퍼(`generate_with_circuit` 류)로 일원화하여 복제 방지.
2. **Redis 브로커 헬스체크 + 알림 도입.** 브로커 정지 시 무알림 silent failure 제거가 운영상 최우선.
3. **FMP 402/429 처리 표준화.** `fmp_screener.py` 패턴(429 retry + stale 캐시 fallback)을 `fmp_fundamentals`·`fmp_exchange_quotes`로 확장. `serverless_client`/`market_pulse_client`에 retry + 402 분류 추가.
4. **`keyword_generator_v2` asyncio.run_until_complete 점검**(Bug #8/#25 fork SIGSEGV).

### P1 — 1주
5. **Gemini 429 재시도 표준화** — `keyword_service.py` exp backoff 패턴을 thesis/news/sec/serverless 소비자로 전파.
6. **부분 실패 허용 일관화** — `macro_service` 글로벌 대시보드를 호출별 분리(FMP 1건 실패가 FRED·전체를 죽이지 않게).
7. **CB 하위 호출 누락 보강** — EOD profile, Market Movers quote에 CB 적용.
8. **`update_financials_with_provider`에 `max_retries` 추가**, 실패 시 raise 또는 명시적 status.

### P2 — 2주
9. **Silent failure 제거** — `return []`/`None`을 "데이터 없음 vs 조회 실패" 구분 가능한 형태로(예: sentinel/예외). `news_deep_analyzer` black-hole 기록 수정.
10. **비용 가드 확대** — `portfolio/llm`의 CostGuard 패턴을 rag_analysis 전 경로에 적용, fallback 연쇄 비용 상한.
11. **`client.py:172 last_error` UnboundLocalError 방어**, dead code(`raise_for_status` L143) 정리.

---

## 부록 — 모범 사례 (확산 대상)

| 패턴 | 위치 | 비고 |
|------|------|------|
| 에러 분류 + 멀티 provider fallback + 비용 가드 | `apps/portfolio/llm/client.py` | Gemini→Anthropic, CostGuard 이중 카운터 |
| timeout + retry + rate limiter + 오류 분류 | `packages/shared/api_request/fred_client.py` | 외부 HTTP 클라이언트 표준 템플릿 |
| 429 retry + Retry-After 존중 + stale 캐시 fallback | `packages/shared/stocks/services/fmp_screener.py` | FMP 소비자 표준 템플릿 |
| JSON 코드펜스 제거 + 규칙 기반 fallback | `services/rag_analysis/services/entity_extractor.py` | LLM JSON 파싱 표준 |
| lazy init + is_available 가드 + CB | `services/serverless/services/neo4j_chain_sight_service.py` | 선택적 의존성 격리 표준 |

---

*본 보고서는 읽기 전용 정적 감사 결과이며 코드를 수정하지 않았다. line 번호는 감사 시점 기준 참고값이다.*
