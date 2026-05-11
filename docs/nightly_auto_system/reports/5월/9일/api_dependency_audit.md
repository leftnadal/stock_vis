# 외부 API 의존성 감사 보고서

**작성일**: 2026-05-09
**범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis / PostgreSQL / Finnhub / MarketAux
**조사 방법**: 읽기 전용 정적 분석 (38 FMP 파일, 38 Gemini 파일, 기타 클라이언트 레이어)
**비고**: 본 감사는 코드 수정을 동반하지 않는 진단 보고서이다.

---

## 1. 의존성 매트릭스 (요약)

| 의존성 | Timeout | Retry | Rate Limit | Fallback | 격리 (Circuit/None 처리) | 종합 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| **FMP (api_request 레이어)** | ✅ 30s | ✅ 지수백오프 ×3 | ✅ Redis 분산 + in-mem | ⚠️ 빈 chain | ⚠️ 부분 (FMPPremiumError) | 🟢 견고 |
| **FMP (macro/serverless 레이어)** | ✅ 30s | ❌ | ⚠️ 비균일 | ❌ | ❌ | 🔴 취약 |
| **Gemini (portfolio.llm)** | ❌ | ✅ 1회+Anthropic 폴백 | ⚠️ 폴백 후만 | ✅ Anthropic | ⚠️ CB 미적용 | 🟡 중간 |
| **Gemini (marketpulse.briefing)** | ❌ | ⚠️ CB 의존 | ⚠️ | ⚠️ | ✅ CB(`get_circuit('gemini')`) | 🟡 중간 |
| **Gemini (rag_analysis.*, serverless.*)** | ❌ | ❌ (대부분) | ❌ | ❌ (일부 regex) | ❌ | 🔴 취약 |
| **FRED API** | ✅ 30s | ✅ ×3 백오프 | ✅ 100/min | ✅ 부분성공 | ✅ try/except 단계별 | 🟢 견고 |
| **Neo4j** | ✅ 2s | ❌ | N/A | ✅ 빈 dict | ✅ Lazy init + None | 🟢 안전 |
| **SEC EDGAR** | ✅ 30/120s | ⚠️ 429 1회 | ✅ 0.12s sleep | ⚠️ edgartools | ❌ IP rotation 없음 | 🟡 위험 |
| **Redis (캐시)** | 내재 | ❌ | N/A | ✅ Django cache | ⚠️ rate limiter만 | 🟡 부분 |
| **Redis (Celery broker)** | 내재 | ❌ | N/A | ❌ | ❌ | 🔴 SPOF |
| **PostgreSQL** | 풀 기본 | ✅ Django 자동 | N/A | ❌ | ✅ Fork safety | 🟢 안전 |
| **Finnhub / MarketAux** | ❓ | ❓ | ⚠️ 설정만 | ⚠️ 선언만 | ❓ | 🟡 미상 |

범례: 🟢 견고 / 🟡 부분 또는 위험 / 🔴 취약

---

## 2. FMP 상세

### 2.1 두 개의 클라이언트 레이어 — 비대칭 견고성

Stock-Vis의 FMP 호출은 **품질이 다른 두 세계**로 양분되어 있다.

| 레이어 | 견고성 |
|---|---|
| `api_request/providers/fmp/client.py` | ✅ 지수백오프 ×3, 402 분리(`FMPPremiumError`), Redis 분산 rate limiter |
| `macro/services/fmp_client.py`, `serverless/services/fmp_client.py` | ❌ 재시도 없음, 402 미분리, rate limiter 비균일 |

**근거**:
- `api_request/providers/fmp/client.py:119-159` — try/except + `2 ** attempt` 백오프, 402는 즉시 raise (재시도 무의미).
- `api_request/providers/fmp/client.py:126-129` — `FMPPremiumError` 분기.
- `macro/services/fmp_client.py:124-126` — `except RequestException: raise` (재시도 없음).
- `serverless/services/fmp_client.py:71-92` — 모든 HTTP 에러를 generic `FMPAPIError`로 매핑, 402와 429 미구분.
- `api_request/providers/factory.py:67-69` — `FALLBACK_CHAIN = {ProviderType.FMP: []}` (Alpha Vantage 제거 후 대체 provider 부재 → SPOF).

### 2.2 핵심 위험 5건

| # | 위치 | 시나리오 | 영향 |
|---|---|---|---|
| 1 | `macro/services/fmp_client.py:124-126` | 일시적 Connection reset / DNS 지연 → 즉시 실패 전파 | `/marketpulse`, `/macro` 화면 500 |
| 2 | `serverless/services/fmp_client.py:71-92` + `:111-119` | 캐시 만료(5분) 직후 동시 다발 요청 → thundering herd → 429 → 빈 응답 | `/market-movers` 등 시장 모멘텀 마비, 5분 이상 정체 가능 |
| 3 | `stocks/tasks.py:147-150` | `.` 포함 심볼만 사전 제외하지만 402 catch 경로 명시 부족 | `sync_sp500_financials` 일부 종목 silent skip |
| 4 | `api_request/stock_service.py:215-232` | quote 실패를 `except Exception: pass`로 무시 | 종목 시세 NULL 저장, 사용자가 "가격 없음" 경험 |
| 5 | `users/utils.py`, `stocks/views_search.py` | 사용자 액션 동기 호출 시 timeout 대기 | 검색·watchlist 응답 지연 |

### 2.3 Rate Limit 전략의 분산

세 곳에서 서로 다른 정책을 사용 → 충돌 가능.

- `api_request/rate_limiter.py:141-171` — Redis 원자적 카운터, FMP 300/min × 80% = 240/min.
- `api_request/providers/fmp/client.py` — in-memory `0.2s sleep` + `daily_calls` 추적.
- `macro/services/fmp_client.py:98-102` — `0.2s sleep`만.
- `serverless/services/fmp_client.py` — sleep 없음 (사후 429 감지에만 의존).

여러 Celery 워커가 동시 실행되면 분산 카운터(`api_request/rate_limiter.py`)만 정확하고, 나머지는 워커 단위 in-memory이므로 합산 시 한도 초과 가능.

---

## 3. Gemini 상세

### 3.1 호출 위치별 핵심 결함

| 호출자 | 429 | JSON 파싱 | Timeout | Sync/Async | 빈 응답 | Fallback |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `portfolio/llm/client.py:214-251` | ✅ 1회+Anthropic | ✅ `getattr` 가드 | ❌ | sync | ✅ "" | ✅ Anthropic |
| `marketpulse/briefing/client.py:47-68` | ⚠️ CB만 | ⚠️ getattr | ❌ | sync | ⚠️ '' | ⚠️ CB(`get_circuit('gemini')`) |
| `rag_analysis/services/llm_service.py:128-241` | ✅ asyncio.sleep 백오프 | ✅ JSONDecodeError | ❌ | **async** | ✅ yield error | ❌ |
| `rag_analysis/services/adaptive_llm_service.py:176-242` | ❌ | ❌ | ❌ | **async** | ⚠️ logger | ❌ |
| `serverless/services/keyword_generator.py:224-260` | ❌ | ❌ ValueError raise | ❌ | **async** | ✅ candidates | ❌ |
| `rag_analysis/services/entity_extractor.py:66-134` | ❌ | ✅ JSONDecodeError | ❌ | **async** | ✅ regex | ✅ |
| `rag_analysis/services/context_compressor.py` | ⚠️ logger | ❌ | ❌ | async | ⚠️ logger | ❌ |
| `serverless/services/csv_url_resolver.py` | ❌ | ❌ | ❌ | async | ❌ | ❌ |

### 3.2 핵심 위험 5건

1. **Free tier 429 무방비** — `serverless/services/keyword_generator.py:247-260`
   `await self.client.aio.models.generate_content(...)` 단순 호출, 백오프 없음. Market Movers 20-30종목 배치에서 15 RPM 한도 충돌 시 `keyword_generation_pipeline` 체인 전체 실패.

2. **Celery 내 async 호출 (Bug #8 재현)** — `serverless/tasks.py:93-148` → `serverless/services/keyword_generator_v2.py`
   `@shared_task`에서 async 메서드(`generate_keywords_for_movers`, `aio.models.generate_content`)에 진입하는 경로가 다시 도입됨. Celery 워커 이벤트 루프와 충돌하면 RuntimeError 또는 "Event loop is closed".

3. **JSON 파싱 → 전체 배치 실패** — `serverless/services/keyword_generator.py:260`
   `ValueError("No text found...")` 발생 시 부분 복구 없이 raise → 배치 전체 실패. `rag_analysis/services/llm_service.py:302-304`는 빈 리스트 반환으로 데이터 손실은 발생하나 배치는 진행.

4. **Timeout 미설정** — `portfolio/llm/client.py:222`, `marketpulse/briefing/client.py:53`, `rag_analysis/services/llm_service.py:182-186`
   `genai.Client(api_key=...)` 인스턴스에 `request_options.timeout` 미명시. Gemini 무응답 시 Celery `soft_time_limit(300s)`까지 워커 hang.

5. **Fallback 재귀 실패** — `portfolio/llm/client.py:158-167`
   Gemini 실패 → Anthropic 폴백 1회만 시도, Anthropic도 실패 시 raise. `rag_analysis/services/adaptive_llm_service.py:154-163`은 폴백 자체가 없음.

### 3.3 Sync/Async 위반 의심 위치

| 태스크 | 파일 | 호출 | 위험 |
|---|---|---|---|
| `collect_keyword_data` | `serverless/tasks.py:93` | `KeywordGeneratorService.generate_keywords_for_movers()` (async) | 🔴 HIGH |
| `keyword_generation_pipeline` | `serverless/tasks.py:202` | async 체인 혼입 | 🔴 HIGH |
| RAG entity extraction | `rag_analysis/services/entity_extractor.py:66` | `await ... aio.models.generate_content(...)` | 🟡 MEDIUM (REST 경유 시 안전) |

`common-bugs.md #8` 문서화 이후에도 serverless 신규 코드에 async 메서드가 추가됨 → 재검증 필요.

---

## 4. 기타 의존성

### 4.1 FRED API — 가장 정교한 재시도 (참고 사례)

`macro/services/fred_client.py:75-156`
- Transient(5xx): 3회 + 지수백오프(2s, 4s, 6s).
- Permanent(401/403/404): 즉시 raise.
- `get_rate_limiter("fred")` 통합 — 100/min.
- 메서드별 단계 try/except로 부분 데이터 반환 가능 (`:281-282`, `:319-320`).

**평가**: Stock-Vis 내 외부 의존성 중 가장 견고. **다른 클라이언트가 따라야 할 모범**.

### 4.2 Neo4j — Lazy + None 폴백

`rag_analysis/services/neo4j_driver.py:19-67`, `rag_analysis/services/neo4j_service.py:57-86`
- Lazy init: 첫 호출 시 연결, 실패 시 `_driver = None`.
- `if self.driver is None: return {빈 dict}` 패턴 (`neo4j_service.py:227-244`).
- 모든 쿼리 2초 timeout.
- Fork safety: `config/celery.py:84-101` — `force_reset_after_fork()`로 macOS SIGSEGV 방지.
- 전용 큐 `neo4j` + solo pool 사용.

**평가**: Neo4j 다운 → Chain Sight 그래프 비활성, 나머지 앱 정상.

### 4.3 SEC EDGAR — 위험 상존

`sec_pipeline/collector.py:28-32`, `api_request/sec_edgar_client.py:98-179`
- User-Agent 의무 충족 ✅ (`Stock-Vis stockvis@example.com`).
- 0.12s sleep로 10 req/sec 준수.
- 429 발생 시 1초 대기 후 1회 재시도만.
- HTML 파서 3단계 fallback (다중 정규식 → ToC 제거 → edgartools).

**위험**: IP 차단 시 회피 메커니즘 없음. 단일 User-Agent + 단일 IP. 장기 운영 시 SEC가 봇 트래픽으로 분류하면 전체 SEC 파이프라인 정지.

### 4.4 Redis

| 용도 | 다운 시 영향 | 처리 |
|---|---|---|
| Rate limiting (`api_request/rate_limiter.py:125-139`) | 카운터 미추적 → 무제한 호출 | ✅ Django LocMemCache 폴백 |
| API 응답 캐시 (`api_request/cache/decorators.py`) | 캐시 미스 → DB/API 직접 호출 | ✅ 자연스러운 graceful |
| 그래프 캐시 (`rag_analysis/services/cache.py`) | 미스 → Neo4j 직접 쿼리 | ✅ |
| **Celery broker** | **모든 비동기 태스크 큐 적재 불가** | ❌ **미커버** |

**결론**: 캐시는 graceful, **broker는 SPOF**.

### 4.5 PostgreSQL — Fork Safety 적용 완료

`config/celery.py:84-101`, `:12-14`
- `worker_process_init` → `db.connections.close_all()` + Neo4j 드라이버 reset.
- macOS: `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`, `PGGSSENCMODE=disable`.
- Bug #25 대응 완료.

### 4.6 Finnhub / MarketAux

`config/settings.py`에 `NEWS_PRIMARY_PROVIDER='finnhub'`, `NEWS_FALLBACK_PROVIDER='marketaux'` 선언 존재. 코드 레벨에서 fallback 분기를 명확히 확인 불가 → **불명확**.

---

## 5. Circuit Breaker 후보 (우선순위)

호출 빈도 × 장애 영향 × 구현 복잡도 기준.

| 우선순위 | 대상 | 트리거 | 폴스루 | 점수 |
|:-:|---|---|---|:-:|
| **P0** | `serverless/services/fmp_client.py` | 429 ×3 또는 5xx ×3 | 캐시 우선, 만료 시 빈 데이터 | 90 |
| **P0** | `macro/services/fmp_client.py` | 5xx ×3 | 마지막 성공값 캐시 | 85 |
| **P0** | Celery Redis broker | ping 실패 | 헬스 엔드포인트로 노출, 알림 | 85 |
| **P1** | `portfolio/llm/client.py` Gemini | 429 ×2 / Timeout | Anthropic 우회 + CB 60s | 78 |
| **P1** | `serverless/services/keyword_generator*.py` Gemini | 429 ×3 | 30분 backoff + 동기 fallback | 75 |
| **P1** | `stocks/tasks.py` FMP 배치 | 402/429 ×3 per symbol | 부분 성공으로 진행 | 72 |
| **P1** | `api_request/stock_service.py` | quote 5xx ×3 | DB 마지막 가격 사용, NULL 금지 | 68 |
| **P2** | `sec_pipeline/collector.py` | 429 ×3 또는 차단 의심 | edgartools 라이브러리만 | 60 |
| **P2** | FRED (이미 견고) | 추가 보강만 | timeout 60s 확대 | 50 |
| **P3** | `news/providers/fmp.py` | 빈 응답 ×N | 빈 배열 (현 상태 유지) | 40 |

### 5.1 즉시 권장 조치 (코드 수정 별도 PR로)

1. **Celery broker 헬스체크** — `/api/v1/health/celery` 추가, ping 실패 시 503.
2. **macro/serverless FMP 클라이언트에 `FMPPremiumError` 도입** — 402 재시도 낭비 차단.
3. **Gemini 호출 timeout 명시** — `genai.Client(... , http_options={'timeout': 30.0})`.
4. **Celery 태스크 내 async LLM 호출 재검증** — `serverless/tasks.py:93, 202` 사슬 추적.
5. **FMP fallback chain 비어있음** (`api_request/providers/factory.py:67-69`) — Alpha Vantage 제거 후 대체 정의 또는 의식적 SPOF 결정 문서화.

---

## 6. 부록 — 코드 인용 인덱스

### FMP
- `api_request/providers/fmp/client.py:119-159` — 견고한 retry/백오프 (모범)
- `api_request/providers/fmp/client.py:126-129` — `FMPPremiumError` 분리
- `api_request/providers/factory.py:67-69` — 빈 fallback chain
- `macro/services/fmp_client.py:124-126` — 재시도 없는 raise
- `serverless/services/fmp_client.py:71-92` — 402/429 미분리
- `serverless/services/fmp_client.py:111-119` — 5분 캐시 + thundering herd 위험
- `stocks/tasks.py:147-150` — `.` 심볼 사전 제외
- `api_request/stock_service.py:215-232` — quote silent fail
- `api_request/rate_limiter.py:141-171` — Redis 분산 rate limiter

### Gemini
- `portfolio/llm/client.py:214-251` — Gemini + Anthropic 폴백
- `portfolio/llm/client.py:222` — timeout 미설정
- `marketpulse/briefing/client.py:47-68` — CB(`get_circuit('gemini')`) 활용
- `rag_analysis/services/llm_service.py:128-241` — asyncio 백오프 + JSONDecodeError 처리
- `rag_analysis/services/llm_service.py:302-304` — 빈 리스트 fallback (데이터 손실)
- `rag_analysis/services/adaptive_llm_service.py:154-165` — 폴백 부재, yield error만
- `serverless/services/keyword_generator.py:247-260` — 백오프 없음, ValueError raise
- `rag_analysis/services/entity_extractor.py:66-134` — regex 폴백 (모범)
- `serverless/tasks.py:93-148, 202` — Celery 내 async 호출 의심 사슬

### 기타
- `macro/services/fred_client.py:75-156, 281-282, 319-320` — FRED 재시도 + 부분성공 (모범)
- `rag_analysis/services/neo4j_driver.py:19-67` — Lazy init
- `rag_analysis/services/neo4j_service.py:57-86, 227-244` — None 폴백
- `sec_pipeline/collector.py:28-32, 161-293` — User-Agent + 3단계 추출
- `api_request/sec_edgar_client.py:98-179` — 429 1회 재시도
- `api_request/rate_limiter.py:125-139` — Redis → Django cache 폴백
- `config/celery.py:12-14, 37-54, 84-101` — macOS env, neo4j 큐, fork safety
- `config/views.py:85-105` — 헬스 체크 (DB + Cache, **broker 미포함**)

---

## 7. 결론

- **FMP**: api_request 레이어는 견고하나 macro/serverless 레이어는 취약. 두 구현체 통합 또는 후자 보강 필요.
- **Gemini**: portfolio.llm과 marketpulse.briefing은 부분 보호, RAG/serverless의 async 호출은 무방비. timeout과 429 백오프 표준화 시급.
- **FRED, Neo4j, PostgreSQL**: 견고. 추가 작업 불필요.
- **SEC EDGAR**: 단기 안정, 장기 IP 차단 위험.
- **Redis broker**: 단일 장애점 (SPOF) — 가장 중요한 미해결 의존성.

P0 3건(serverless FMP, macro FMP, Celery broker)에 Circuit Breaker 적용이 가장 높은 ROI. Bug #8 재현 의심 경로(`serverless/tasks.py` ↔ async LLM)는 별도 추적 PR로 격리 검증 권장.
