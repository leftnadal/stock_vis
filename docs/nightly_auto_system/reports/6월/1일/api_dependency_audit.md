# 외부 API 의존성 감사 보고서

> **작성일**: 2026-06-01
> **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis 장애 대응
> **성격**: 읽기 전용 감사 (코드 미수정)
> **방법**: 핵심 클라이언트(`fmp/client.py`, `circuit_breaker.py`, `settings.py`, `portfolio/llm/client.py`)는 직접 정독, 호출 지점 패턴(약 64개 파일)은 서브에이전트 전수 스캔. 라인 번호는 스캔 시점 기준이며 일부는 근사치일 수 있음.

---

## 🔴 가장 중요한 발견 (Executive Summary)

| # | 발견 | 위험 |
|---|------|------|
| **F1** | **Circuit Breaker가 Django cache(=Redis)에 상태를 저장** (`circuit_breaker.py:9,64,73`) | Redis 장애 시 CB 자체가 동작 불능 → 보호 장치가 가장 필요한 순간에 무력화 |
| **F2** | **`CACHES`에 `IGNORE_EXCEPTIONS` 미설정** (`settings.py:500-505`) | Redis 다운 시 `cache.get/set`이 예외를 던져 view·task·CB가 연쇄적으로 500 |
| **F3** | **Redis가 단일 장애점(SPOF)**: 캐시 + Celery broker + result backend + channel layer + CB 상태 (전부 `localhost:6379`) | Redis 한 대 다운 = 캐시 + 모든 백그라운드 작업 + WebSocket + CB 동시 정지 |
| **F4** | **공통 LLM 래퍼(`portfolio/llm/client.py`)가 portfolio 앱에만 적용** | 나머지 ~24개 LLM 호출 지점이 각자 genai.Client 직접 호출, 429 재시도 부재(약 72%) |
| **F5** | **`fmp_fundamentals.py`의 silent-pass + 캐시 중독** | 402/429를 구분 없이 `return []`로 삼키고 빈 결과를 캐시 → TTL까지 빈 데이터 고착 |

---

## 1. 의존성 매트릭스 (서비스별 외부 API × fallback 유무)

| 의존성 | 기저 클라이언트 | 에러 분류 | Retry/Backoff | Circuit Breaker | Fallback | 장애 시 영향 범위 | 심각도 |
|--------|----------------|----------|---------------|-----------------|----------|------------------|--------|
| **FMP** (재무/시세) | `providers/fmp/client.py` | ✅ 4종(401/402/429/Auth) | ✅ 3회 exp backoff | △ 일부 서비스만 | △ 지점별 상이 | 종목/재무/스크리너/EOD | **높음** |
| **Gemini** (LLM) | 각자 직접 호출 (래퍼 미통일) | △ portfolio만 분류 | ✗ 대부분 없음 | △ briefing/rag만 | △ 지점별 상이 | 키워드/뉴스/RAG/테제/SEC | **높음** |
| **FRED** (거시) | `api_request/fred_client.py` | ✅ 4xx즉시/5xx재시도 | ✅ 3회 exp backoff | ✗ 없음 | △ 빈 객체/기본값 | Market Pulse 거시 섹션 | 중간 |
| **Neo4j** (그래프) | `rag_analysis/.../neo4j_driver.py` | ✅ lazy + 가용성 체크 | △ CB 내부 1~3회 | ✅ threshold=5 | ✅ Postgres 미러 | Chain Sight 그래프 기능 | **높음** |
| **SEC EDGAR** | `sec_pipeline/collector.py` | ✅ RequestException | ✗ collector 자체 무재시도 (Celery만) | ✗ 없음 | △ regex→edgartools | 10-K 공급망/사업모델 | 중간 |
| **Redis 캐시** | Django `RedisCache` | ✗ IGNORE_EXCEPTIONS 미설정 | ✗ 없음 | ✗ (오히려 CB가 Redis 의존) | ✗ 없음 (예외 전파) | 캐시 + CB 상태 | **높음** |
| **Redis Broker** | Celery | ✗ 연결 실패 시 작업 거부 | ✗ 없음 | ✗ 없음 | result는 django-db | 모든 Celery 태스크 | **매우 높음** |

> 범례: ✅ 적절 / △ 부분적·지점별 상이 / ✗ 없음

---

## 2. FMP 상세

### 2.1 기저 클라이언트 — 견고함 ✅
`packages/shared/api_request/providers/fmp/client.py` (직접 정독, 499줄)

- **에러 클래스 4종**: `FMPClientError`, `FMPRateLimitError`(429), `FMPAuthError`(401/403), `FMPPremiumError`(402) — `client.py:21-42`
- **HTTP 상태 분기**: 401/402/403/429 명시 처리 — `client.py:129-143`
- **재시도**: 재시도 불필요 에러(402/Auth/429)는 즉시 전파, 그 외는 3회 exponential backoff — `client.py:156-170`
- **Rate limit**: `request_delay=0.2s`(Starter 300/min 대응) + 일일 한도 10,000 카운터 — `client.py:104-115`
- **timeout**: 30초 고정 — `client.py:124`
- **FMP 본문 에러**(`"Error Message"`) 처리 — `client.py:148-152`

> 기저 클라이언트 수준의 장애 대응은 **모범적**. 문제는 전적으로 **호출 계층**에 있음.

### 2.2 호출 계층 위험 지점

#### 🔴 CRITICAL: `stocks/services/fmp_fundamentals.py` — silent-pass + 캐시 중독
- `get_key_metrics/get_ratios/get_dcf/get_rating/get_balance_sheet/get_income_statement/get_cash_flow_statement` 전부 동일 안티패턴: `except httpx.HTTPStatusError: return []` (대략 `:62-99`, `:154-164`)
- **402(Premium) vs 429(RateLimit) 미구분** → 호출자는 실패 원인을 알 수 없음
- 실패 시 빈 결과를 캐시에 저장 → **다음 요청도 TTL까지 빈 데이터 반환(캐시 중독)**

#### 🔴 CRITICAL: `stocks/tasks.py` — retry 없는 Celery 태스크
- `update_financials_with_provider` (`tasks.py:550` 부근): `@shared_task(rate_limit="6/m")` 만 있고 **`max_retries` 없음** → 일시적 네트워크 오류도 즉시 실패, `except`는 로그만
- `bulk_generate_korean_overview` (`:790` 부근): `max_retries=1` (권장 3)

#### 🟠 HIGH: `providers/fmp/provider.py` — FMPPremiumError 처리 비일관
- 재무제표 메서드(`get_balance_sheet:233`, `get_income_statement:275`, `get_cash_flow:315`)는 `FMPPremiumError` 명시 catch ✅
- **`get_quote`, `get_daily_prices`, `get_company_profile`는 미처리** → 402가 RateLimitError로 오분류될 수 있음

#### 🟠 HIGH: `stocks/services/sp500_eod_service.py` — CB threshold 과도 + 부분 데이터
- `failure_threshold=10` (`:138` 부근) → 누적 429를 10회까지 허용
- CB open 시 skip 처리하나 idempotent existing-check와 겹쳐 **실패 종목이 "skipped"로 둔갑** → DailyPrice 누락 가능

#### 🟡 부분 성공 은폐
- `update_stock_with_provider` (`tasks.py:322-350`): 3단계를 개별 try/except로 처리 후 항상 success 문자열 반환 → 호출자가 부분 실패를 감지 못함

### 2.3 FMP 양호 사례 (템플릿)
- `stocks/views.py` StockOverview/ChartData: DB → FMP sync → FMP direct 3단 fallback + 명시적 예외
- `stocks/services/sp500_service.py`: `failure_threshold=3, recovery=300` + idempotent 기본 dict 반환

---

## 3. Gemini 상세

### 3.1 래퍼 분산 — 통일 안 됨 (핵심 문제 F4)

| 래퍼 | 위치 | 평가 |
|------|------|------|
| **LLMClient** | `apps/portfolio/llm/client.py` | ✅ **best-in-class**: 에러 분류(`_classify_gemini_error`), 1회 retry(RateLimit/Timeout), **교차 프로바이더 fallback**(Gemini↔Anthropic), 비용 가드/ledger. **단, portfolio 앱에만 사용** |
| **LLMServiceLite** | `rag_analysis/services/llm_service.py` | ✅ 스트리밍, 429 문자열 감지 + `RETRY_DELAYS=[1,2,4]`, CB 연동 |
| **AdaptiveLLMService** | `rag_analysis/services/adaptive_llm_service.py` | ⚠️ broad except만, retry/timeout 없음, lazy init 실패 가능 |
| (래퍼 없음) | thesis/serverless/news/sec/validation 다수 | ✗ 각자 `genai.Client` 직접 호출 |

### 3.2 공통 갭

#### 🔴 429 재시도 부재 — 호출 지점 약 72%
- 429 감지·재시도가 있는 곳: `keyword_service.py`(`:122` max_retries), `llm_service.py`(스트리밍 `:251`) 정도
- 미처리 대표: `thesis/services/indicator_matcher.py`(`:226` 부근 호출, 429 핸들링 없음), `thesis/tasks/summary.py`, `serverless/keyword_generator(_v2).py`, `news/news_deep_analyzer.py`, `sec_pipeline/extractor.py`, `validation/llm_peer_filter.py`
- **결과**: Gemini Free 15 RPM 초과 시 즉시 실패, 야간 배치에서 연쇄 실패 가능

#### 🟡 timeout 부재
- genai SDK `generate_content`에 timeout 미설정이 일반적 → **행(hang) 시 Celery 워커 무한 점유**
- CB로 감싼 `market_pulse/briefing/client.py`(`get_circuit("gemini")`) 외엔 보호 장치 없음

#### 🟡 broad except 예외 삼킴 / 파싱-API 에러 미구분
- `indicator_matcher.py:252-254`, `thesis/tasks/summary.py:74-76`(빈 문자열 반환), `korean_overview_service.py:96` 등: `except Exception` 으로 429/auth/파싱 실패를 동일 취급 → 운영 진단 곤란
- JSON 파싱 실패와 API 실패를 같은 레벨에서 처리 → "빈 응답"과 "포맷 깨짐" 구분 불가

#### 🟡 SDK 혼재
- `thesis/tasks/summary.py`는 구 SDK(`google.generativeai`), 나머지는 신 SDK(`google.genai`) → 유지보수 부담

### 3.3 Gemini 양호 사례 (템플릿)
- `keyword_service.py`: max_retries + `FALLBACK_KEYWORDS` 정적 폴백
- `entity_extractor.py`: API 실패 시 정규식 기반 `_fallback_extraction`
- `portfolio/llm/client.py`: 교차 프로바이더 fallback + 비용 ledger

---

## 4. 기타 의존성

### 4.1 FRED (`packages/shared/api_request/fred_client.py`)
- ✅ 4xx(401/403/404) 즉시 raise, 5xx transient 3회 exp backoff (`:98-155`)
- ✅ `get_rate_limiter("fred")`(120/min), 시리즈별 개별 try/except 격리
- ✗ **Circuit Breaker 없음**, 완전 장애 시 fallback은 빈 객체/기본값(`macro_service.py:78-85`)
- 영향: 거시 대시보드 섹션 공백 (FMP 시장 데이터와 분리되어 부분 영향)

### 4.2 Neo4j
- ✅ `neo4j_driver.py` lazy init, 실패 시 None 반환하고 "앱은 계속 실행"(`:72`)
- ✅ `neo4j_chain_sight_service.py` `is_available()`로 모든 작업 전 가용성 + CB(OPEN) 체크, threshold=5/recovery=60
- ✅ **Postgres `StockRelationship` 미러 존재** → Neo4j 다운 시 그래프 전용 기능만 불가, 기본 관계 데이터 유지
- ⚠️ 드라이버 init이 사실상 1회 → 일시적 네트워크 단절이 영구 disable로 굳을 수 있음
- ✅ 전용 `neo4j` 큐 + solo pool + `MAX_TASKS_PER_CHILD=100`로 SIGSEGV 방지

### 4.3 SEC EDGAR (`services/sec_pipeline/collector.py`)
- ✅ User-Agent 헤더, `raise_for_status` + RequestException catch
- ✅ rate limit 준수 `time.sleep(0.12)`(10 req/s), timeout 15/30/60s 단계별
- ✅ 섹션 추출 regex → edgartools fallback (`:254-271`)
- ✗ **collector 자체 무재시도** — transient 오류는 Celery task(`tasks.py` `max_retries=3~5`)에만 의존
- 영향: 개별 10-K 수집 실패 → 공급망/사업모델 누락 (fallback 품질 낮음)

### 4.4 Redis — 시스템 단일 장애점 (F1/F2/F3)
- **용도 집중**: 캐시(`db1`) + Celery broker(`db0`) + channel layer + **CB 상태 저장소** — 전부 `localhost:6379`
- ✗ `CACHES`에 `IGNORE_EXCEPTIONS`/`SOCKET_*` 옵션 없음 (`settings.py:500-505`) → Redis 오류가 `cache.get/set` 호출 전부를 예외로 전파
- ✗ **CB가 `django.core.cache`(=Redis)에 상태 기록** (`circuit_breaker.py:9,64-81`) → Redis 장애 시 `get_state()`가 예외 → CB가 보호는커녕 추가 예외원
- result backend는 `django-db`로 분리(`settings.py:493`)되어 결과 저장만은 생존
- 영향: **Redis 다운 = 캐시 미스(성능) + 모든 Celery 정지(기능) + WebSocket 단절 + CB 무력화** 동시 발생

---

## 5. Circuit Breaker 후보 (장애 시 전체 영향이 큰 지점)

### 우선순위 1 — 신규 CB 도입 시급
| 후보 | 근거 | 권장 |
|------|------|------|
| **Gemini 전역** | LLM 호출 ~24곳 중 429 재시도 72% 부재, timeout 없음, 워커 hang | 공통 래퍼(`portfolio/llm/client.py`)를 `packages/shared/llm/`로 승격 후 CB+timeout 일괄 적용 |
| **FRED** | CB 전무, 완전 장애 시 무방비 재시도 | `get_circuit("fred")` 적용 |
| **SEC EDGAR** | collector 무재시도 + CB 없음, 야간 배치 영향 | `get_circuit("sec_edgar")` + collector 레벨 transient 재시도 |

### 우선순위 2 — 기존 CB 보강
| 후보 | 문제 | 권장 |
|------|------|------|
| **FMP fundamentals** | silent-pass `return []`, CB 미적용, 캐시 중독 | 402/429 분류 후 CB 적용 + 실패 시 캐시 저장 금지 |
| **FMP EOD (sp500_eod)** | `failure_threshold=10` 과도 | 3~5로 하향 |
| **CB 상태 저장소** | Redis 의존으로 자기모순 (F1) | CB 상태를 in-memory 또는 별도 백엔드로 분리 검토 |

### 우선순위 3 — 인프라 레벨
| 후보 | 문제 | 권장 |
|------|------|------|
| **Redis graceful degradation** | F2 | `CACHES`에 `OPTIONS.IGNORE_EXCEPTIONS=True` + `SOCKET_CONNECT_TIMEOUT` 추가 |
| **Redis SPOF** | F3 | broker/cache/channel 인스턴스 분리 또는 Sentinel/Cluster 검토, health check 엔드포인트 |

---

## 6. 권장 조치 요약 (우선순위순)

1. **[인프라/즉시]** `CACHES`에 `IGNORE_EXCEPTIONS=True` 추가 — Redis 일시 장애가 전체 view를 죽이지 않도록 (F2)
2. **[설계/시급]** CB 상태 저장을 Redis에서 분리 — 보호 장치의 자기참조 제거 (F1)
3. **[LLM/시급]** 공통 LLM 래퍼를 공유 패키지로 승격하고 24개 직접 호출 지점 마이그레이션 (429 재시도 + timeout + 분류 통일) (F4)
4. **[FMP/시급]** `fmp_fundamentals.py`의 402/429 분류 + 실패 시 캐시 저장 금지, `update_financials_with_provider`에 `max_retries=3` 추가 (F5)
5. **[CB 확대]** Gemini 전역 / FRED / SEC EDGAR에 CB 도입, sp500_eod threshold 하향
6. **[Redis SPOF]** broker/cache 인스턴스 분리 + health check (F3)

---

*본 보고서는 읽기 전용 감사 결과이며 코드 변경을 수행하지 않았습니다. 라인 번호는 2026-06-01 스캔 기준입니다.*
