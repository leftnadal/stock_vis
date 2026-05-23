# 외부 API 의존성 감사 보고서

- 작성일: 2026-05-23
- 대상 브랜치: slice14
- 범위: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis

---

## 1. 의존성 매트릭스

| 서비스 / 모듈 | 외부 API | retry | rate limit | fallback | cache | timeout | 비고 |
|---|---|---|---|---|---|---|---|
| `api_request/providers/fmp/client.py` (정식 FMPClient) | FMP | exp backoff 3회 | 0.2s/req, daily 10k 카운터 | 없음 | 없음 | 30s | 402 → `FMPPremiumError`, 401/403 → `FMPAuthError`, 429 → `FMPRateLimitError` |
| `serverless/services/fmp_client.py` (Market Movers) | FMP | 없음 | 없음 (httpx 단발) | 없음 | django cache (60s~24h) | 30s | 에러 핸들링은 `FMPAPIError` 단일 |
| `macro/services/fmp_client.py` | FMP | 없음 | 0.2s sleep만 | 호출부에서 None | 없음 | 30s | 402 미구분, requests 예외만 처리 |
| `news/providers/fmp.py` | FMP | 위임 (FMPClient에 의존) | 위임 | 빈 리스트 반환 | 없음 | 위임 | except 광범위 → 빈 결과 |
| `macro/services/fred_client.py` | FRED | exp backoff 3회 (transient 5xx만) | `RateLimiter("fred")` (api_request.rate_limiter) | 없음 | 없음 | 30s | 우수 — TRANSIENT_STATUS_CODES 분리 |
| `api_request/sec_edgar_client.py` | SEC EDGAR | 429 recursion(무한 가능) | 10 req/s, User-Agent | 없음 | CIK 메모리 캐시 | 30s | 재귀 retry는 무한 루프 위험 |
| `rag_analysis/services/neo4j_driver.py` | Neo4j | 없음 | n/a | **있음** (lazy + None 반환) | singleton driver | 60s 풀 획득 | graceful — Neo4j down 시 앱 살아있음 |
| `rag_analysis/services/llm_service.py` | Gemini | exp backoff 3회 | n/a | n/a | n/a | 미설정 | `marketpulse.utils.circuit_breaker` 사용 |
| `serverless/services/keyword_generator.py` | Gemini | 없음 | n/a | n/a | n/a | 미설정 | async + sync 양버전 공존 (#8 준수) |
| `serverless/services/keyword_generator_v2.py` | Gemini | 없음 | n/a | n/a | n/a | 미설정 | **async-only**, Celery 태스크에서는 `loop.run_until_complete` 사용 (#8 risk) |
| `serverless/services/llm_relation_extractor.py` | Gemini | except Exception 광범위 | n/a | n/a | redis | 미설정 | sync API 사용 |
| `thesis/services/thesis_builder.py` | Gemini | tenacity 위임 | n/a | `_fallback_parse` | n/a | 미설정 | `get_circuit('gemini_thesis')` — **Circuit Breaker O** |
| `thesis/views/conversation_views.py` | Gemini | 직접 호출 | n/a | n/a | n/a | 미설정 | 동기 view 내부 |
| `validation/services/llm_peer_filter.py` | Gemini | 없음 | n/a | error dict | n/a | 미설정 | 단발 sync 호출 |
| `news/services/news_deep_analyzer.py` | Gemini | 없음 | n/a | n/a | n/a | 미설정 | sync, 단일 except |
| `sec_pipeline/extractor.py` | Gemini | 없음 | n/a | n/a | n/a | 미설정 | JSON parse 분기, 재시도 없음 |
| `rag_analysis/services/entity_extractor.py` | Gemini | n/a | n/a | n/a | n/a | n/a | async (aio.models) |
| `marketpulse/utils/circuit_breaker.py` | shared | tenacity + redis 상태 | n/a | n/a | redis | n/a | **유일한 진짜 CB** 구현 |
| `news/services/circuit_breaker.py` | news provider별 | redis 카운터 | n/a | n/a | redis | n/a | 단순 fail count, half-open 없음 |

---

## 2. FMP 상세

### 2.1 호출 위치 분포
세 개의 **별도 FMP 클라이언트** 가 공존:

1. **정식**: `api_request/providers/fmp/client.py` — 가장 완전 (재시도/402/429/401 분기)
   - 사용처: `api_request/providers/fmp/provider.py`, `api_request/stock_service.py`, `stocks/tasks.py`, `stocks/views_search.py`, `stocks/services/sp500_*`, `thesis/tasks/eod_pipeline.py`, `thesis/views/monitoring_views.py`
2. **serverless**: `serverless/services/fmp_client.py` — httpx, 재시도 없음, 캐시 강함
   - 사용처: `serverless/tasks.py`, Market Movers, `chain_sight_service`, `enhanced_screener_service`, `keyword_data_collector`, `cusip_mapper`, `market_breadth_service`, `sector_heatmap_service`, `serverless/views.py`
3. **macro**: `macro/services/fmp_client.py` — requests, 재시도 없음, 402 미구분
   - 사용처: `macro/services/macro_service.py`, `macro/management/commands/sync_marketpulse_v2_*`

### 2.2 에러 핸들링 패턴 분류
- **A. 완전 분리 (FMPPremium/Auth/RateLimit)** — `api_request/providers/fmp/client.py:126-145`. `provider.py:247,293,339`에서 `FMPPremiumError` 명시 처리 ✅
- **B. 단일 FMPAPIError** — `serverless/services/fmp_client.py:84-92`. 402도 일반 HTTPStatusError로 들어옴
- **C. requests.exceptions만 처리** — `macro/services/fmp_client.py:124-126`. 402 거르지 못함

### 2.3 Rate limit / 402 처리
- `client.py`: 매 호출 `time.sleep(0.2)` + `daily_calls` 카운터 (max 10000) → 다중 워커 환경에서 카운터 무의미 (프로세스 로컬)
- `serverless/fmp_client.py`: 캐시로 호출 분산하지만 rate limit 자체 게이트 없음
- `macro/fmp_client.py`: 0.2s sleep만, 카운터 없음
- ✅ Redis 기반 글로벌 rate limiter `api_request/rate_limiter.py:RateLimiter`가 존재하지만 **FRED 외에는 활용 안 함**

### 2.4 발견된 리스크
| 우선순위 | 항목 | 위치 |
|---|---|---|
| **P0** | 클라이언트 3중화로 402/429 처리 불일치 → 야간 배치 한 곳에서 402 폭발 시 다른 경로는 일반 HTTP error로 silent skip | 3개 fmp_client.py |
| **P0** | daily call 카운터가 프로세스 로컬 → Celery worker N개 + beat에서 진짜 10k 한도 보호 못함 | `client.py:70-71,110-112` |
| **P1** | `serverless/fmp_client.py`/`macro/fmp_client.py` 재시도 0회 → 일시적 5xx도 즉시 실패 | 위 두 파일 |
| **P1** | `news/providers/fmp.py:fetch_company_news`의 `except Exception → return []`은 회로 차단 신호 손실 | `:52-54` |
| **P2** | `requests.get(timeout=30)` 일률 30초 → 동기 chain에서 cascade 차단 위험 | 전 클라이언트 |

---

## 3. Gemini 상세

### 3.1 호출 위치 분포 (sync vs async)
- **Async (`client.aio.models.generate_content`)**:
  `rag_analysis/services/llm_service.py:205`, `context_compressor.py:138,290`, `entity_extractor.py:87`, `serverless/services/keyword_generator.py:247`, `keyword_generator_v2.py:269,304`
- **Sync (`client.models.generate_content`)**:
  `serverless/services/keyword_generator.py:256` (`_call_llm_sync`), `llm_relation_extractor.py:384`, `keyword_service.py`, `regulatory_service.py`, `relationship_keyword_enricher.py`, `thesis_builder.py`, `csv_url_resolver.py`, `keyword_generator.py`, `thesis/services/thesis_builder.py:462`, `validation/services/llm_peer_filter.py:79`, `news/services/news_deep_analyzer.py:125`, `sec_pipeline/extractor.py:68,128`, `stocks/services/korean_overview_service.py`

### 3.2 429 / JSON 파싱 / timeout
- **429 핸들링 명시 없음** — 모든 호출이 `except Exception` 로 뭉뚱그림. Gemini SDK 내부 retry에만 의존
- **timeout 설정 없음** — `genai.Client` 기본값 그대로 (장애 시 무한 대기 가능성)
- **JSON 파싱** — `response_mime_type='application/json'` 설정한 호출에도 `json.JSONDecodeError` 별도 처리는 `sec_pipeline/extractor.py:86,140`만 명시. 그 외는 일반 `except Exception` 흡수

### 3.3 동기/async 혼용 여부
- ✅ `keyword_generator.py`는 sync/async 두 버전 분리 (`#8` 규칙 준수)
- ⚠ `keyword_generator_v2.py`는 **async only** + `serverless/services/keyword_generator_v2.py:414`에서 `loop.run_until_complete` 우회 → Celery 워커에서 macOS fork 시 SIGSEGV 재발 위험 (common-bugs #25)
- ⚠ `rag_analysis/tasks.py:413,483`에서도 동일 패턴 (`run_until_complete`) — 다만 `--pool=solo` 환경 가정

### 3.4 발견된 리스크
| 우선순위 | 항목 | 위치 |
|---|---|---|
| **P0** | timeout 미설정 + retry 없음 → Gemini API hang 시 worker 영구 점유 | sec_pipeline, llm_peer_filter, news_deep_analyzer 등 ~10곳 |
| **P0** | CB 적용된 호출은 thesis_builder/llm_service/context_compressor 3곳뿐. 나머지 ~10 호출처는 CB 미적용 | 위 표 |
| **P1** | `keyword_generator_v2.py`에서 `loop.run_until_complete` Celery 호출 — macOS prefork 환경에서 #25 재발 가능 | `keyword_generator_v2.py:414` + `rag_analysis/tasks.py:413,483` |
| **P1** | `validation/services/llm_peer_filter.py:88` `except Exception → error dict` — 429/500 구분 불가, 사용자 요청 즉시 실패만 됨 | `:71-90` |
| **P2** | Gemini Free quota (15 RPM / 1500 RPD) 글로벌 카운터 없음 → 야간 배치 중 quota 폭발 시 cascading | 전체 |

---

## 4. 기타 의존성

### 4.1 FRED
✅ **가장 우수**. `macro/services/fred_client.py:114-117`에서 TRANSIENT_STATUS_CODES(500/502/503/504) 분리 재시도. `RateLimiter("fred")` 글로벌 게이트. 401/403/404 즉시 raise.
- 리스크: rate limiter는 Redis 기반이지만, Redis 다운 시 fallback 검증 필요 (별도 확인 권고)

### 4.2 Neo4j
✅ `rag_analysis/services/neo4j_driver.py`는 **lazy singleton + 실패 시 None 반환** 패턴. 앱은 죽지 않음.
- 리스크: Neo4j-의존 view/task가 `driver is None` 체크 누락 시 AttributeError. 일관성 검증 필요

### 4.3 SEC EDGAR
- ✅ 10 req/s rate limit, User-Agent 헤더, 30s timeout
- ⚠ **재귀 retry 무한 위험** — `sec_edgar_client.py:162-166`의 429 처리는 `return self._make_request(...)` 무한 재귀. depth 카운터 없음 → SEC가 지속 429 반환 시 RecursionError까지 폭주

### 4.4 Redis
- `marketpulse/utils/circuit_breaker.py`는 Redis(`django.core.cache`)를 신뢰. **Redis 다운 시 CB 자체가 작동 불가**
- `cache.get(...)` 실패 시 fallback 없음 — 각 서비스가 cache 응답을 그냥 신뢰
- `serverless/services/fmp_client.py` 캐시 의존도 매우 높음 (60s~24h) → Redis 장애 시 FMP 호출량 폭증 → rate limit 즉시 hit

---

## 5. Circuit Breaker 도입 후보 (우선순위순)

| 우선순위 | 위치 | 영향도 | 현재 핸들링 | 권고 |
|---|---|---|---|---|
| **P0** | `sec_pipeline/extractor.py:68,128` (Gemini supply chain/BM 추출) | 10-K 야간 배치, 다수 종목 직렬 | except Exception, 재시도 0 | `get_circuit('gemini_sec', failure_threshold=5)` 적용 |
| **P0** | `serverless/services/llm_relation_extractor.py:384` | 뉴스 배치마다 호출, 비용 직접 | except Exception | `get_circuit('gemini_relation')` |
| **P0** | `serverless/services/fmp_client.py` Market Movers/Screener | 메인 페이지 EOD 시그널 직격 | 캐시만 의존 | provider 단위 CB + redis 글로벌 rate limiter |
| **P0** | `api_request/sec_edgar_client.py:_make_request` 429 재귀 | 10-K collector 전체 hang | 무한 재귀 | depth limit + tenacity 도입 |
| **P1** | `news/services/news_deep_analyzer.py:125` | 뉴스 분석 파이프라인 | except Exception | `get_circuit('gemini_news')` |
| **P1** | `validation/services/llm_peer_filter.py:79` | 사용자 요청 동기 view | error dict | timeout 명시 + CB 적용 |
| **P1** | `macro/services/fmp_client.py` | Market Pulse 일일 sync | requests 예외만 | 정식 `FMPClient`로 통합 또는 retry 추가 |
| **P2** | `stocks/services/korean_overview_service.py` Gemini | 사용자 비동기 (Celery) | n/a | timeout + CB |
| **P2** | Redis 자체 — `cache.get` 실패 시 noop | 전 시스템 fallback 미비 | 없음 | `try/except RedisError` wrapper 또는 LocMem fallback |

---

## 6. 종합 권고 (Top 5 액션 아이템)

1. **FMP 클라이언트 3중화 통합** — `api_request/providers/fmp/client.py`의 `FMPPremiumError/RateLimit/Auth` 분리 패턴을 single source로 채택. `serverless/services/fmp_client.py`와 `macro/services/fmp_client.py`는 위임 wrapper로 전환. daily 카운터를 **Redis 기반 글로벌**로 이동.
2. **Gemini 호출 전체 timeout + CB 표준화** — `thesis_builder.py:459` (`get_circuit('gemini_thesis')`) 패턴을 sec_pipeline/llm_relation_extractor/news_deep_analyzer/llm_peer_filter/korean_overview_service 등 9곳에 일괄 적용. `genai.Client` 호출 시 request_options로 timeout 명시.
3. **SEC EDGAR 429 재귀 → 유한 retry** — `sec_edgar_client.py:166`의 무한 재귀를 `for attempt in range(3)` + exponential backoff으로 교체. 영향: 10-K collector 전체 hang 방지.
4. **Celery에서 `loop.run_until_complete` 잔존 코드 정리** — `keyword_generator_v2.py:414`와 `rag_analysis/tasks.py:413,483` 두 곳은 macOS prefork 환경에서 #25 재발 위험. `_sync` 메서드 추가 또는 `--pool=solo` 강제 문서화.
5. **Redis 장애 시 graceful degradation** — `marketpulse/utils/circuit_breaker.py`와 `serverless/services/fmp_client.py`의 cache 접근부에 `try/except RedisError` 추가. Redis 장애가 곧 시스템 장애가 되는 단일 실패점 제거.

---

### 부록: 우수 사례 (보존)
- **FRED Client** (`macro/services/fred_client.py`): transient/permanent 분리 + 글로벌 rate limiter
- **Neo4j Lazy Singleton** (`rag_analysis/services/neo4j_driver.py`): 외부 의존성 down에도 앱 alive
- **Thesis Builder Gemini CB** (`thesis/services/thesis_builder.py:459`): CB + fallback parser 패턴 — 다른 LLM 호출처의 표준 모델
