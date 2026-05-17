# 외부 API 의존성 감사 보고서

- **작성일**: 2026-05-17
- **감사 범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis, Alpha Vantage
- **감사 방식**: 읽기 전용 정적 분석 (코드 수정 없음)
- **대상 파일**: FMP 관련 35개 + Gemini 관련 29개 + 기타 의존성

---

## 의존성 매트릭스 (서비스별 외부 API × fallback 유무 테이블)

| 외부 API | 1차 클라이언트 | 사용 영역 | Retry | Rate Limit 제어 | Fallback / Graceful Degradation | Circuit Breaker | 위험도 |
|---------|-------------|---------|-------|----------------|-----------------------------|-----------------|--------|
| **FMP** (Starter 300/분, 10k/일) | `api_request/providers/fmp/client.py` | stocks, api_request, news/providers/fmp | ✅ 3회 exp backoff | ✅ 일일 카운터 + 0.2s sleep | ✅ 402/429 즉시 차단 (FMPPremiumError) | ❌ 없음 | 🟡 |
| **FMP** (보조) | `serverless/services/fmp_client.py` (httpx) | serverless, chain_sight, screener | ❌ 없음 | ❌ 없음 | ⚠ {"Error Message"} 파싱만 | ❌ | 🔴 |
| **FMP** (보조) | `macro/services/fmp_client.py` | macro 대시보드 | ❌ 없음 | ⚠ 0.2s sleep만 | ❌ 일반 Exception catch | ❌ | 🔴 |
| **Gemini 2.5 Flash** | `genai.Client(...)` 직접 호출 (서비스마다 개별) | rag_analysis, thesis, news, serverless, validation, sec_pipeline, marketpulse, stocks | ⚠ rag_analysis만 3회 backoff | ⚠ news_deep_analyzer만 4s sleep | ⚠ JSON 파싱 ad-hoc 처리 | ⚠ rag_analysis만 적용 | 🔴 |
| **Anthropic** (Sonnet/Haiku) | `portfolio/llm/client.py:LLMClient` (wrapper) | scripts/slice* (Portfolio Coach 평가) | ✅ 1회 + Gemini→Anthropic 폴백 | ✅ LLM_BUDGET_MAX_CALLS | ✅ fallback_from 기록 | ❌ | 🟢 |
| **FRED** (120/분) | `macro/services/fred_client.py` | macro economic indicators | ✅ 3회 exp backoff (2/4/6s) | ✅ RateLimiter | ✅ try-except per series, 로그 후 계속 | ❌ | 🟢 |
| **Neo4j** | `serverless/services/neo4j_chain_sight_service.py` | Chain Sight 온톨로지, Graph Analysis | ✅ tenacity | — | ✅ get_neo4j_driver()=None 시 fallback mode | ✅ failure_threshold=5, recovery=60s | 🟢 |
| **SEC EDGAR** (8.3 req/s) | `sec_pipeline/collector.py` | sec_pipeline 10-K 추출 | ❌ 없음 | ✅ 0.12s sleep + UA 헤더 | ❌ 실패 시 즉시 raise | ❌ | 🔴 |
| **Alpha Vantage** (5/분) | (실사용 미확인) | — | — | — | — | — | ⚪ |
| **Redis** | django.core.cache + Celery broker | 전 서비스 (Cache/Broker/CB state/Channels) | ❌ | ❌ | ❌ 명시적 graceful degradation 없음 | N/A (자기참조) | 🔴 |

> 위험도: 🟢 Well-Handled / 🟡 부분 적용 / 🔴 High Risk / ⚪ N/A

---

## FMP 상세

### 클라이언트 3종 분기 — **표준화되지 않음**

| 클라이언트 | HTTP 라이브러리 | 402 (Premium) | 429 (Rate Limit) | Retry | 일일 카운터 |
|----------|--------------|---------------|------------------|-------|-----------|
| `api_request/providers/fmp/client.py` | requests | ✅ `FMPPremiumError` raise (L128-129) | ✅ `FMPRateLimitError` raise (L132-133) | ✅ 3회, `(attempt+1)*2` 초 (L151-159) | ✅ 사전 차단 (L110-112) |
| `serverless/services/fmp_client.py` | httpx | ❌ 미감지 (raise_for_status만) | ❌ 미감지 | ❌ | ❌ |
| `macro/services/fmp_client.py` | requests | ❌ | ❌ | ❌ | ❌ |

### 핵심 발견
- **버그 #23 (BRK.B 등 `.` 심볼)** 처리는 `api_request/providers/fmp/provider.py` (L247-345)에서만 `FMPPremiumError → PREMIUM_ONLY` 코드로 변환. `macro/fmp_client.py:146-164`의 `get_batch_quotes()`는 개별 try-except로 에러 격리하지만 **로깅 없음** — 조용히 누락.
- **재시도 제외 규칙** (`api_request/providers/fmp/client.py:149-150`): 401, 402, 403, 429는 즉시 재전파. 일반 `requests.RequestException`만 재시도. **올바른 패턴**.
- **호출 빈도 부담**: `refresh-market-pulse-cache` 1분 간격 × 6.5시간 거래시간 = **390회/일**. Starter 10k/일 한도와 다른 작업(EOD/Screener/Movers) 합치면 한도 압박 가능.

### Celery Beat 스케줄 (FMP 의존)
| 태스크 | 빈도 | 시간대 | 호출량 추정 |
|--------|------|--------|------------|
| `update-realtime-prices` | 5분 | 9-16 EST 평일 | ~78회/일 |
| `refresh-market-pulse-cache` | 1분 | 9-16 EST | ~390회/일 |
| `update-market-indices` | 5분 | 9-16 EST | ~78회/일 |
| `sync-sp500-financials` | 1회/일 | 20 EST | 101회 (S&P500/5) |
| `sync-daily-market-movers` | 1회/일 | 07:30 EST | ~50회 |
| `update-daily-prices` | 1회/일 | 17 EST | ~500회 |

> **주의**: Beat 스케줄 실측은 `config/celery.py`가 아닌 **DatabaseScheduler** 기반 (CLAUDE.md 버그 #28). 정확한 등록은 `marketpulse/management/commands/setup_marketpulse_beat.py` 및 `PeriodicTask` 테이블 직접 확인 필요.

---

## Gemini 상세

### 호출 방식 분포 — **일관성 없음**

| 패턴 | 사용처 | 비고 |
|-----|-------|------|
| `genai.Client(api_key=...)` 생성자 인스턴스화 | `serverless/services/thesis_builder.py:56`, `news/services/news_deep_analyzer.py:53`, 등 대부분 | Celery 호환 동기 호출 |
| `genai.configure(...)` 싱글톤 | `rag_analysis/services/adaptive_llm_service.py:91` | 비권장 (전역 상태) |
| `generate_content_async()` 비동기 | `rag_analysis/services/llm_service.py:13`, `entity_extractor.py` | **CLAUDE.md 버그 #8 위반 가능성** — Celery 호출 경로 확인 필요 |
| `portfolio.llm.client.LLMClient` wrapper | **scripts/slice6~8 평가 스크립트에서만 사용**. 운영 서비스에서는 import 없음 | 분류·폴백·비용 가드 보유하지만 미활용 |

### 에러 핸들링

**rag_analysis (가장 완성도 높음)**:
- `llm_service.py:234-250`: `MAX_RETRIES=3`, `RETRY_DELAYS=[1,2,4]` 지수 백오프
- CircuitBreaker 통합 (`rag_analysis/services/context_compressor.py`, `llm_service.py`)
- 429/quota/rate 키워드 매칭 후 재시도, 그 외 즉시 실패

**portfolio/llm/client.py** (wrapper, 평가 전용):
- `_classify_gemini_error()` (L62-96): 메시지 텍스트 기반 분류 — RateLimit / Timeout / Auth / InvalidPrompt
- 1회 재시도 후 **Gemini → Anthropic 폴백** (L177-196)
- 비용 가드 (`LLM_BUDGET_MAX_CALLS`)

**일반 서비스 (thesis, news, serverless, validation, sec_pipeline 등)**:
- 대부분 `try/except Exception` 광역 캐치, **타입 분리 미흡**
- 429, 500, 503 구분 없음 → 일시 장애를 영구 실패로 처리할 위험

### JSON 파싱

| 파일 | 처리 방식 |
|-----|---------|
| `rag_analysis/services/entity_extractor.py:107` | `JSONDecodeError` catch → 기본값 반환 |
| `rag_analysis/services/llm_service.py:320` | `_clean_json_response()` — 마크다운 코드블록 제거 후 파싱 |
| `thesis_builder.py` | 손상 시 괄호 개수 맞춰 수리 시도 (fragile) |
| 기타 다수 | ad-hoc, Pydantic 스키마 검증 사용처 미발견 |

### Timeout — **전반적으로 미설정**
- 모든 Gemini 호출에서 `request_options.timeout` / `generation_config.timeout` 미설정
- SDK 기본값에 의존 → **무한 대기 가능성**
- 특히 Celery worker는 task soft_time_limit이 유일한 안전망

### Rate Limit (Free 15 RPM / Paid Tier 다름)
- `news/services/news_deep_analyzer.py:39`: `RPM_DELAY=4초` 수동 sleep (15 RPM 준수)
- `serverless/services/regulatory_service.py`: 배치 호출 시 `time.sleep(4)`
- 다른 서비스(thesis, validation, sec_pipeline)는 throttle 없음 → **동시 호출 시 429 위험**

### 모델 분포
| 모델 | 사용처 |
|-----|-------|
| `gemini-2.5-flash` | rag_analysis (entity_extractor, context_compressor, llm_service, complexity_classifier 일부), serverless (모든 키워드/관계 생성), thesis, news, sec_pipeline, validation, metrics — **압도적 다수** |
| `gemini-2.5-flash-thinking` | rag_analysis/cost_tracker.py 정의만 (실사용 미확인) |
| `gemini-2.5-pro` | rag_analysis/cost_tracker.py 정의만 |
| `claude-sonnet-4-20250514` | `rag_analysis/services/complexity_classifier.py:115,121` (복잡도 높은 케이스만) |
| `claude-haiku/claude-sonnet` (Anthropic wrapper) | scripts/slice* 평가 전용 |

---

## 기타 의존성

### FRED (`macro/services/fred_client.py`) — 🟢 Well-Handled
- 3회 재시도 + 지수 백오프 (2/4/6초) (L26, L114)
- `api_request.rate_limiter.RateLimiter` 적용 (L70)
- 시리즈별 개별 try-except (L281-282) — **부분 실패 허용**
- Celery beat: 4회/일 (06/12/18/22 EST)

### SEC EDGAR (`sec_pipeline/collector.py`) — 🔴 High Risk
- User-Agent 헤더 필수 — 설정됨 (L30)
- 0.12초 sleep (8.3 req/s, SEC 한도 10/s 준수)
- **재시도 로직 없음** (L84-91) — 단일 네트워크 hiccup으로 파이프라인 정지
- 429/403 명시적 처리 없음

### Neo4j — 🟢 Well-Handled
- `marketpulse/utils/circuit_breaker.py` 적용
- `serverless/services/neo4j_chain_sight_service.py:117-125`: `_run_with_cb()` wrapper
- 설정: `failure_threshold=5`, `recovery_seconds=60`
- Driver=None 시 fallback mode (L109-111) — Chain Sight 외 다른 기능에는 영향 없음
- 6시간마다 health check
- 별도 CB: `news/services/circuit_breaker.py` — Neo4j 외 영역에서도 사용

### Alpha Vantage — ⚪ 실사용 미확인
- 파일 경로 `api_request/providers/alpha_vantage/`는 grep으로 직접 매칭 안 됨
- `.env.example`에 `ALPHA_VANTAGE_API_KEY` 정의만 확인 (CLAUDE.md)
- 운영 의존성 없을 가능성

### Redis — 🔴 단일 장애점 (Single Point of Failure)
- `config/settings.py:477`: Broker `redis://localhost:6379/0`
- `config/settings.py:496`: Cache `redis://localhost:6379/1`
- `config/settings.py:506`: Channels `redis://127.0.0.1:6379`
- **Graceful degradation 미구현**: `cache.get()` 실패 시 별도 try-except 없음
- 영향 범위:
  - Celery Broker 정지 → 모든 비동기 태스크 중단
  - Cache 미스 → 캐시 의존 엔드포인트 응답 지연/실패
  - Circuit Breaker 상태 손실 (CB가 Redis 캐시 기반)
  - Django Channels (WebSocket) 정지
- **권장**: 캐시 호출부 wrapping 또는 stub fallback

---

## Circuit Breaker 후보

### 현재 적용 현황
| 영역 | CB 적용 | 위치 |
|-----|--------|------|
| Neo4j | ✅ | `serverless/services/neo4j_chain_sight_service.py`, `marketpulse/utils/circuit_breaker.py` |
| Gemini (RAG 일부) | ✅ | `rag_analysis/services/llm_service.py`, `context_compressor.py` |
| Gemini (thesis/news/serverless/validation/sec) | ❌ | — |
| FMP | ❌ | retry만 있음 |
| SEC EDGAR | ❌ | retry도 없음 |
| FRED | ❌ | retry만 있음 |

### 도입 우선순위 (장애 시 영향도 × 호출 빈도)

#### 🔥 P0 — 즉시 도입 권장
1. **FMP 통합 Circuit Breaker** (`api_request/providers/fmp/client.py`)
   - **이유**: 매일 ~1000회+ 호출, 다운 시 EOD/Market Pulse/Movers/Screener 동시 정지. 현재 retry는 있으나 연쇄 호출 시 backoff 누적으로 워커 점유.
   - **권장 설정**: `failure_threshold=10`, `recovery=120s`
   - **참고**: `marketpulse/utils/circuit_breaker.py` 패턴 재사용

2. **Gemini 전역 Wrapper + CB** (현재 직접 호출 19개 서비스)
   - **이유**: timeout 미설정 + 429 분기 부재 → 단일 quota 초과로 thesis/news/keyword/validation 동시 정지.
   - **권장**: `portfolio/llm/client.py:LLMClient`를 운영 서비스로 확장 (현재 scripts/slice* 전용)
   - **권장 설정**: `failure_threshold=5`, `recovery=60s`, timeout=30s 기본값

#### ⚠️ P1 — 단기 도입
3. **SEC EDGAR** (`sec_pipeline/collector.py`)
   - **이유**: 재시도조차 없음. 야간 파이프라인 중 SEC가 1회 502 반환 시 전체 종목 추출 실패.
   - **권장**: tenacity로 retry + CB
   - **권장 설정**: `failure_threshold=3`, `recovery=300s`

4. **serverless/macro FMP 클라이언트 통합**
   - **이유**: 동일 외부 의존성에 3종 클라이언트, 그중 2종은 retry/402/429 처리 없음. 표준 클라이언트 1종으로 통합 후 CB 적용.

#### 💡 P2 — 중기 검토
5. **Redis Cache Wrapper**
   - **이유**: 단일 장애점이지만 CB로 해결되지 않음 (CB 자체가 Redis 의존).
   - **대안**: `django-redis`의 `IGNORE_EXCEPTIONS=True` 설정 또는 LocMem fallback layer

6. **FRED Rate Limiter 통합**
   - **이유**: 이미 retry + per-series 격리 있음. CB 효용 낮으나 분당 120 한도 가까이 갈 때 보호 가치 있음.

### CB 도입 시 공통 권장사항
- **상태 저장**: Redis 단일 의존 위험 → `marketpulse/utils/circuit_breaker.py`처럼 Redis 캐시 사용 시 fallback 상태(`get`/`set` 실패 시 CLOSED 가정) 필수
- **메트릭 수집**: CB 상태 변경(CLOSED→OPEN→HALF_OPEN)을 metrics 로그로 영속화 (`metrics/services/`)
- **알림**: OPEN 상태 진입 시 daily_report에 포함 (`metrics/services/daily_report.py:369` 인근에 통합 가능)

---

## 요약: 최우선 조치 5건

| # | 항목 | 영향 범위 | 우선순위 |
|---|------|----------|---------|
| 1 | FMP 클라이언트 3종 → 1종 표준화 (`api_request/providers/fmp/client.py` 기준) | stocks, serverless, macro, news, thesis 전체 | P0 |
| 2 | Gemini 운영 호출 19개 서비스 → 공통 wrapper(`LLMClient`)로 통합 | thesis, news, serverless, validation, sec_pipeline, marketpulse | P0 |
| 3 | Gemini 호출에 timeout 일괄 적용 (현재 0건) | 전체 LLM 경로 | P0 |
| 4 | SEC EDGAR 재시도 + CB 추가 | sec_pipeline 야간 작업 | P1 |
| 5 | Redis cache failure graceful degradation (`IGNORE_EXCEPTIONS`) | 전 서비스 | P1 |

---

## 부록: 감사 메서드

- 정적 grep 기반 — 런타임 동작 미검증
- 테스트 코드(`tests/`) 의도적 제외 — 운영 코드만 대상
- 누락 가능 영역: 외부에서 동적 import되는 코드, `getattr` 동적 분기, scripts/* 1회성 스크립트
- 추가 확인 권장: PeriodicTask 테이블 실측, Sentry/로그에서 실제 429/402 발생 빈도, Celery soft_time_limit 설정값
