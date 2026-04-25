# 외부 API 의존성 감사 보고서

- 작성일: 2026-04-25
- 작성자: nightly auto-system / Claude Code
- 범위: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis 의존 코드 (Python)
- 모드: 읽기 전용 (코드 수정 없음)
- 사전 grep:
  - `FMPClient|fmp_client|get_stock_service|StockService` 매치 36개 파일
  - `generate_content|genai\.` 매치 33개 파일

---

## 의존성 매트릭스

서비스/도메인 × 외부 의존 × fallback/캐시 매트릭스. ✓ 있음, △ 부분, ✗ 없음.

| 도메인 | FMP | Gemini | FRED | Neo4j | SEC | Redis(캐시) | Redis(broker) | Fallback 전략 |
|---|---|---|---|---|---|---|---|---|
| stocks (가격, 재무, 검색) | ✓ 핵심 | ✓ Korean overview | – | – | – | △ delete only | ✓ tasks | provider chain 빈 리스트 (`FALLBACK_CHAIN[FMP]=[]`) |
| api_request/providers | ✓ 단일 진입점 | – | – | – | – | – | – | provider abstraction은 있으나 등록된 fallback provider 없음 |
| macro (지표/Pulse) | ✓ 자체 fmp_client | – | ✓ 자체 fred_client | – | – | ✓ TTL 60s~7d | ✓ beat 호출 | 캐시 hit 시만 graceful, 미스 시 즉시 raise |
| serverless (Movers/Screener/Chain Sight) | ✓ 자체 fmp_client (httpx) | ✓ 다수 (배치) | – | ✓ neo4j_chain_sight_service | – | ✓ 5m~24h | ✓ tasks | 캐시 hit 외 fallback 없음, stampede 방지 lock 없음 |
| news (수집/분석) | ✓ providers/fmp.py | ✓ keyword/insights/deep | – | ✓ news ↔ Neo4j | – | ✓ articles/sentiment | ✓ beat | provider 실패 시 빈 리스트 + 로그 |
| rag_analysis | – | ✓ llm_service / adaptive | – | ✓ neo4j_driver lazy singleton | – | △ entity cache | ✓ neo4j queue | Neo4j None 반환 → API 200 유지 |
| thesis (관제실/EOD) | ✓ eod_pipeline + monitoring | ✓ thesis_builder/conversation/indicator_matcher | – | – | – | – | ✓ beat | indicator별 null_value 기록(격리) |
| validation | – | ✓ llm_peer_filter (structured output) | – | – | – | – | – | LLM 실패 시 사용자 메시지 |
| sec_pipeline | – | ✓ extractor/intelligence | – | ✓ dirty sync | ✓ collector | – | ✓ beat | edgartools 라이브러리 fallback (선택) |
| chainsight | ✓ stocks 의존 | △ relation enricher | – | ✓ tasks (queue=neo4j) | △ via sec_pipeline | – | ✓ neo4j queue | neo4j_dirty 플래그 + 재동기화 task |

요약 메시지:
- **FMP, Gemini, Redis는 단일 장애점(SPOF)**. 어느 하나가 죽으면 일부 또는 전체 서비스가 5xx로 빠진다.
- **Neo4j와 SEC EDGAR는 graceful degradation 설계**가 부분적으로 들어가 있다 (Neo4j: `is_available()` False 시 빈 결과; SEC: edgartools fallback 옵션).
- **FRED는 캐시 TTL이 길어 단기 장애에 강하지만, 캐시 미스가 겹치면 곧바로 외부 호출 의존**.

---

## FMP 상세

### 호출 진입점 분포 (FMP 클라이언트 3종 공존)

| 클라이언트 | 위치 | request_delay | retry/backoff | 에러 클래스 | 일일 한도 추적 |
|---|---|---|---|---|---|
| **`FMPClient`** | `api_request/providers/fmp/client.py` | 0.2s | max_retries=3, `(attempt+1)*2s` linear backoff | FMPRateLimitError / FMPAuthError / FMPPremiumError / FMPClientError | ✓ daily_calls / daily_limit=10000 |
| **`macro/services/fmp_client.py`** | macro 전용 (지수, 환율, 섹터, 캘린더) | 0.5s | requests 예외 raw | 별도 클래스 없음 | ✗ |
| **`serverless/services/fmp_client.py`** | Movers/Screener/Chain Sight | httpx, timeout=30s | – | FMPAPIError 단일 | ✗ (캐시 5m~24h) |
| `news/providers/fmp.py` | wraps `FMPClient` | – | – | Exception 포괄 | – |

> 같은 외부 API에 대해 3가지 클라이언트가 분기되어 있어, 에러 클래스/Rate-limit 카운터가 통일되지 않는다. `macro/`와 `serverless/`는 402/429를 일반 예외와 구분하지 않는다.

### 에러 핸들링 매트릭스 (대표 호출 지점)

| 호출 위치 | 429 처리 | 402 (Premium) | Celery retry | Fallback | 캐시 | 비고 |
|---|---|---|---|---|---|---|
| `api_request/providers/fmp/provider.py` | ✓ raise → `RateLimitError` | ✓ → `error_code=PREMIUM_ONLY` | – | ProviderResponse만 (chain 빈 리스트) | ✗ | 정석 |
| `stocks/tasks.py` (sp500 sync, financials) | △ 일부 task에서 `self.retry(...)` | △ FMPPremiumError 캐치하지만 일부만 | ✓ max_retries=3, countdown 분산 | ✗ | △ `cache.delete()` 위주 | bug #23 대응 들어가 있음 |
| `thesis/tasks/eod_pipeline.py` | △ FMPClientError catch | ✓ FMPPremiumError → null_value | ✓ | ✗ | ✗ | 가설 단위 격리 |
| `serverless/tasks.py` (movers) | △ delay 재시도 | ✗ | ✓ 5min delay | ✗ | ✓ TTL 5~30분 | 동시 실행 시 위험 |
| `macro/services/fmp_client.py` | ✗ raw `RequestException` | ✗ | – | ✗ | ✓ macro_service 캐시 60s~7d | 401과 429 구분 불가 |
| `serverless/services/fmp_client.py` | ✗ FMPAPIError 일원화 | ✗ | – | ✗ | ✓ httpx + 캐시 | stampede 방지 lock 없음 |
| `news/providers/fmp.py` | ✗ Exception → 빈 리스트 | ✗ | – | ✗ | – | 실패 silent화 |
| `users/utils.py`, `stocks/views_search.py` | – | – | – | ✗ | – | 사용자 요청 경로 (직접 5xx 가능) |

### Rate Limit (Starter Plan: 300/min, 10000/day) 충돌 가능성

- **EOD price sync** (`stocks/services/sp500_eod_service.py` + `stocks/tasks.py`): S&P500 ~503 종목 × `get_quote()`. 0.2s delay에서 약 100s 소요 → 정상 시 분당 ~300에 근접한 burst 발생 가능.
- **Daily financials** (`stocks/tasks.py` `sync_sp500_financials`): countdown=`i*7`s 분산. 동일 큐에 worker 2개 이상이면 분산 효과 약화.
- **Market Movers** (`serverless/services/data_sync.py`): gainers/losers/actives + 종목별 sector/profile 추가 호출. 아침 시간에 EOD/뉴스 배치와 시간이 겹칠 위험.
- **Thesis EOD pipeline** (`thesis/tasks/eod_pipeline.py`): active thesis × indicator 수만큼 FMP 호출, 동일 시간대 EOD/movers와 경합.
- **Cache stampede** (`serverless/services/fmp_client.py`): `cache.get` → miss → `cache.set` 패턴에 distributed lock 없음. 5분 TTL 만료 직후 worker가 동시 호출하면 분당 한도에 일시적으로 가까워질 수 있음.
- **Retry burst**: `FMPClient`의 backoff는 linear (`(attempt+1)*2`), Celery `self.retry`와 합쳐지면 동일 심볼에 대해 3~6번 호출이 한꺼번에 누적될 수 있다.

### 위험 지점 Top 5 (FMP)

1. **`FMPProvider`의 fallback 체인 비어 있음** (`api_request/providers/factory.py`의 `FALLBACK_CHAIN[FMP]=[]`). FMP가 죽으면 `call_with_fallback`도 즉시 실패. provider abstraction의 의미가 약하다.
2. **`macro/services/fmp_client.py`가 401/402/429를 구분하지 않음.** raw `requests.exceptions.RequestException` 위주라 운영 중 원인 파악이 느려진다. `macro` 캐시 의존도가 높아서 캐시 만료 시 한번에 새로고침 부하 발생.
3. **`serverless/services/fmp_client.py`의 캐시 stampede.** TTL 만료 직후 동시에 같은 endpoint를 부르는 worker가 다수면 분당 한도 + 비용 부담. distributed lock(`cache.add(lock_key, 1, ttl)`) 패턴이 없다.
4. **Celery 재시도 + 클라이언트 재시도 중첩.** 동일 호출이 최대 3 × 3 = 9회까지 폭발 가능. backoff가 짧아 burst 우려.
5. **사용자 경로의 직접 호출** (`users/utils.py`, `stocks/views_search.py`, `news/providers/fmp.py`). 캐시/큐 보호 없이 동기 호출이라 FMP 장애가 곧 사용자 5xx로 직결.

---

## Gemini 상세

### 모델 / 호출 패턴

| 항목 | 분포 |
|---|---|
| 사용 모델 | 대부분 `gemini-2.5-flash`, `adaptive_llm_service`만 `gemini-1.5-pro` 조건부 사용. `adaptive_llm_service` 내부에 Anthropic Claude 호출 경로도 있음 |
| 호출 방식 | `genai.Client(...).models.generate_content(...)` 동기 6개, `client.aio.models.generate_content(...)` 비동기/스트림 13개 |
| `response_mime_type='application/json'` (structured output) | `validation/services/llm_peer_filter.py` 등 소수만 적용. 다수 파일은 raw text 파싱 |
| 재시도 / 429 처리 | `rag_analysis/services/llm_service.py`만 `[1, 2, 4]s` 백오프 + 3회 재시도. **나머지는 사실상 처리 없음** |
| timeout | 어디에도 명시 설정 없음 (SDK 기본값) |
| 캐시 | `serverless/services/llm_relation_extractor.py` 1h Redis 캐시. 그 외 거의 없음 |

### 동기/비동기 위반 (CLAUDE.md bug #8) 의심 지점

- `serverless/services/keyword_generator.py`, `keyword_generator_v2.py`: `async def` 함수 다수. Celery 태스크에서 호출되므로 호출부 (`serverless/tasks.py`)가 `asyncio.run()`로 감싸는지 확인 필요. (이 보고서에서는 호출부까지 정밀 검증하지 못했음 — 후속 점검 권장)
- `rag_analysis/services/entity_extractor.py`: `async def extract()`. RAG 비동기 파이프라인 안에서는 정상이지만 Celery에서 직접 호출 시 위험.

### JSON 파싱 안전성

- **잘 처리됨**: `serverless/services/thesis_builder.py` (코드 블록 추출 → 객체 추출 → 괄호 자동 보정 4단계), `rag_analysis/services/llm_service.py` (`<suggestions>`/`<basket-action>` 태그 + ResponseParser).
- **취약**: 다수 파일이 단순 `json.loads(content)` + `except: return None/[]`. `response_mime_type` 미설정이라 응답이 잘리거나 중간에 설명 텍스트가 섞여 있을 때 무음 실패.

### Rate Limit (Free 15 RPM / 1500 RPD 기준 시) 부담

| 서비스 | 위치 | 호출 빈도 (추정) | 비고 |
|---|---|---|---|
| Movers 키워드 | `serverless/services/keyword_generator*.py` | 일 1회 + 사용자 트리거 | Top-N 종목 배치 |
| 뉴스 키워드/딥분석 | `news/services/keyword_extractor.py`, `news_deep_analyzer.py` | 시간/일 단위 배치 + 사용자 트리거 | Pipeline v3에서 양 큼 |
| 관계 추출 | `serverless/services/llm_relation_extractor.py` | 종목/뉴스 배치 | 1h 캐시 있음 |
| 가설 빌더 | `thesis/services/thesis_builder.py`, `serverless/services/thesis_builder.py` | 사용자 요청 시 | 대화형 |
| SEC 인텔리전스 | `sec_pipeline/intelligence.py` | 10-K filing 단위 | 분기적 |
| 인디케이터 매처 | `thesis/services/indicator_matcher.py` | 가설 생성/수정 시 | 사용자 트리거 |
| Korean overview | `stocks/services/korean_overview_service.py` | 종목 단위 lazy | 캐시화 가능 |

운영 환경이 유료 키 가정이라면 RPM/RPD 자체보다는 **공통 backoff/JSON-safe 파서**가 현실적인 위험. Free 키 운영이라면 1500 RPD를 며칠 내에 소진할 가능성이 크다.

### 위험 지점 Top 5 (Gemini)

1. **429/RESOURCE_EXHAUSTED 처리 부재** — `rag_analysis/llm_service.py` 외 다수 파일이 첫 실패에서 즉시 빈 결과 또는 raise. 한 번 정원 초과 시 카스케이드 실패 가능.
2. **timeout 없음** — Gemini SDK 호출이 무한 대기로 잡힐 경우 Celery worker가 잠겨 후속 task가 밀린다.
3. **JSON 파싱 fallback 부재** — `thesis_builder.py`/`llm_service.py` 외 대부분이 “파싱 실패 = None”. 사용자에게는 빈 결과지만 silent 데이터 손실.
4. **structured output 미사용** — `response_mime_type='application/json'` + `response_schema`가 거의 없어, 모델이 설명을 덧붙이면 깨짐.
5. **중복 모듈 (thesis_builder, keyword_generator)** — `serverless/`와 `thesis/`에 같은 이름 파일이 있어 어느 경로가 운영 트래픽인지, 어디에 패치해야 하는지 혼선이 발생할 수 있다.

---

## 기타 의존성

### FRED (`macro/services/fred_client.py`, `macro_service.py`)

- raw HTTP, `requests` 직접 호출. 분당 120회 정책.
- **재시도**: 5xx에 대해 3회 + 지수 백오프(2/4/6s). 401/403/404는 즉시 실패.
- **timeout**: 30초.
- **rate limiter**: `get_rate_limiter("fred")` 호출 — 구현체가 `api_request/rate_limiter`(또는 유사 위치) 어딘가에 있어야 의미를 가짐. 미구현/미주입 시 무방비.
- **캐시 TTL**: realtime 60s, daily 3600s, monthly 86400s, quarterly 7d. **단기 장애에는 강함.**
- **Beat**: `update-economic-indicators` 일 4회, `refresh-market-pulse-cache` 시장시간 매분.
- 위험: API 키 미설정 시 경고만 띄우고 호출 시도 (401 폭발). 캐시 동시 만료 시 갱신 부하.

### Neo4j

- **Driver**: `rag_analysis/services/neo4j_driver.py`의 lazy singleton. `_connection_attempted` 플래그로 첫 연결 실패 후 재시도 안 함. 재기동 없이 회복 안 되는 문제 잠재.
- **Pool**: `max_connection_pool_size=50`, `max_connection_lifetime=3600s`, `connection_acquisition_timeout=60s`.
- **세션**: `with driver.session()` 컨텍스트 매니저 사용. MERGE 위주 idempotent 쿼리.
- **Graceful degradation**: `is_available()` False면 `get_related_stocks()/get_n_depth_graph()` 빈 결과. API 200 유지.
- **Queue 격리**: `config/celery.py`의 `task_routes`에서 `rag_analysis.tasks.*`, `chainsight.tasks.sync_tasks.*`, `news.tasks.sync_news_to_neo4j`, `sec_pipeline.tasks.sync_dirty_to_neo4j`를 `queue='neo4j'`로 라우팅. macOS에서는 `--pool=solo` 사용 (bug #25 대응).
- **데이터 일관성 위험**: PG ↔ Neo4j 사이의 `neo4j_dirty` 플래그 패턴이 표준 — 다만 동기화 task가 실패한 경우 dirty가 남아 있는지 정기 점검이 필요.

### SEC EDGAR (`sec_pipeline/collector.py`, `extractor.py`)

- **User-Agent**: `Stock-Vis stockvis@example.com` (필수). 미설정 시 403.
- **Rate limit**: 0.12s sleep (~10 req/s).
- **재시도**: **task-level 재시도가 없음.** `response.raise_for_status()`로 즉시 실패.
- **timeout**: submissions 30s, HTML 60s.
- **추출 단계**: regex → BeautifulSoup → edgartools fallback. 검증 실패(`validate_extracted_sections`) 시 fallback 재시도. 최종 status는 success/partial/failed.
- 위험: 일시적 네트워크 오류에 무방비. edgartools 미설치 환경에서 partial 비율 증가.

### Redis

- **CACHES default**: `django.core.cache.backends.redis.RedisCache` → `redis://127.0.0.1:6379/1`. **fallback 없음** (locmem 백업 미설정).
- **Celery broker**: `redis://localhost:6379/0`.
- **Celery result backend**: 설정에서 한 번 Redis로 잡았다가 다시 `django-db`로 덮어씀 → 최종 PostgreSQL.
- **Session**: 명시적 `SESSION_ENGINE` 없음 → DB 세션. JWT 인증 위주이므로 **Redis 다운이 로그아웃을 유발하지는 않음**.
- 위험: 캐시/브로커가 같은 인스턴스 → SPOF. 캐시 hit으로 가려져 있던 모든 의존이 한꺼번에 외부 API로 폭발.

### 기타 발견

- `config/celery.py`에서 macOS fork 안전성 대응(`OBJC_DISABLE_INITIALIZE_FORK_SAFETY`, solo pool, fork 후 `db.connections.close_all()`)이 들어 있어 SIGSEGV 회귀는 어느 정도 막혀 있음 (bug #25).
- DatabaseScheduler 사용 (bug #28). 이 감사에서는 실제 PeriodicTask DB 상태까지는 검증하지 않음 — 별도 cron 점검 권장.

---

## Circuit Breaker 후보

“장애 시 영향 면이 넓고, 재시도/큐 폭발 위험이 있는 호출 지점”을 우선순위로 나열.

| 우선순위 | 호출 지점 | 차단/완화 권장 패턴 |
|---|---|---|
| **P0** | `api_request/providers/fmp/client.FMPClient._make_request` (모든 FMP 트래픽이 통과) | 클라이언트 단일 진입에서 circuit breaker (consecutive failure N → open, half-open ping 후 close). Rate-limit 카운터(daily_calls)도 단일 인스턴스에서만 의미 있으므로 Redis 기반 분산 카운터 함께 검토 |
| **P0** | `serverless/services/fmp_client.py` (Movers/Screener/Chain Sight 핵심) | 동일 패턴 + cache stampede 방지(`cache.add` 락) |
| **P0** | Redis 캐시 백엔드 자체 | locmem fallback 추가 또는 `django-redis` `IGNORE_EXCEPTIONS=True` 옵션 검토 (캐시 다운이 5xx로 빠지지 않게) |
| **P1** | `macro/services/fmp_client.py` + `fred_client.py` (Market Pulse 핵심) | 401/402/429 분리 + breaker. macro는 캐시 TTL이 길어 breaker open 동안 stale-while-error 정책 적용이 효과 큼 |
| **P1** | Gemini 호출 (`serverless/services/keyword_*`, `news/services/*`, `thesis/services/thesis_builder.py`, `rag_analysis/services/llm_service.py`) | 공통 wrapper에 timeout/backoff/breaker. `response_mime_type=application/json` + 공통 ResponseParser 강제 |
| **P1** | `serverless/services/neo4j_chain_sight_service` 및 `rag_analysis/services/neo4j_driver` | 첫 연결 실패 시 영구 None 캐시 → backoff 재연결 루프로 교체. breaker는 이미 `is_available()` 형태로 부분 구현 |
| **P2** | `sec_pipeline/collector.py` | task-level 재시도 (max_retries=3, exponential backoff) + breaker. 리스크는 SEC가 IP 차단 가능하다는 점이라 backoff가 보수적이어야 함 |
| **P2** | `news/providers/fmp.py`, `news/services/aggregator.py` | provider 단위 breaker. 실패 silent 처리 대신 metric 노출 |
| **P3** | `validation/services/llm_peer_filter.py` (사용자 동기 경로) | 짧은 timeout + 즉시 fallback (지표 기반 default peer set) |

### 공통 권장 (보고서 차원)

- **단일 LLM 호출 wrapper 도입**: timeout, 429 backoff, structured output, JSON 파서, 캐시 키, 메트릭을 한 곳에서 강제. 현재 `rag_analysis/llm_service.py`의 패턴이 가장 가까움 — 이를 공유 모듈로 승격 검토.
- **단일 FMP 클라이언트로 통합**: `macro/`, `serverless/`의 자체 FMP 클라이언트를 `api_request/providers/fmp/FMPClient`로 흡수 (별도 라이브 작업 PR 필요).
- **Cache stampede 방지**: `cache.add(lock_key, 1, lock_ttl)` 또는 redis-lock 패턴을 stampede 위험 엔드포인트에 적용.
- **Redis ignore_exceptions**: 캐시 자체가 SPOF가 되지 않도록 `django-redis`의 graceful 옵션 또는 locmem 보조 캐시 검토.
- **Beat schedule 점검 절차**: bug #28 재발 방지를 위해 `PeriodicTask` DB 검증 스크립트를 야간 자동화에 포함.

---

## 부록: 사전 grep 결과 요약

- FMP/StockService 관련 36개 파일: api_request, stocks, serverless, macro, news, thesis, users, scripts, tests 분포.
- Gemini(`generate_content`/`genai.`) 관련 33개 파일: serverless, news, rag_analysis, thesis, validation, sec_pipeline, stocks, tests 분포.
- 본 보고서는 각 영역에서 대표 파일을 우선 검증한 결과이며, 상세 패치 시에는 호출부 (특히 `*/tasks.py`)까지 추가 점검이 필요하다.
