# 외부 API 의존성 감사 보고서

생성일: 2026-05-20
범위: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis
방식: read-only 정적 분석

---

## 0. 요약 (Executive Summary)

- **FMP 클라이언트 파편화**: `api_request/providers/fmp/client.py`, `serverless/services/fmp_client.py`, `macro/services/fmp_client.py` 세 개의 독립 구현체가 병존한다. 각각 `requests` / `httpx` 라이브러리가 다르고, 402/429 처리 로직이 불일치하여 동일 장애 상황에서 앱마다 다른 동작을 한다.
- **keyword_generator의 async Celery 호출**: `serverless/services/keyword_generator.py:374`의 `generate_keywords_sync`는 Celery 태스크에서 `asyncio.get_event_loop()` + `loop.run_until_complete()`로 `async` LLM을 호출한다. 이는 common-bugs #8 위반이며 macOS fork 환경에서 SIGSEGV 유발 위험이 있다.
- **Gemini 429 재시도가 지수 백오프를 사용하지 않는 모듈 다수**: `sec_pipeline/extractor.py`, `validation/services/llm_peer_filter.py`, `news/services/keyword_extractor.py`에는 429 전용 retry 로직이 없고 예외를 호출자에게 즉시 전파하거나 단순 `Exception` 처리로 누락된다.
- **FMP `macro/services/fmp_client.py`에서 402/429 미처리**: `response.raise_for_status()` 이후 예외 타입이 `requests.exceptions.HTTPError`로 wrap되어 올라온다. 소비자가 `FMPPremiumError`를 기대하면 catch 실패한다.
- **야간 자동화(Celery Beat)에서 Neo4j 장애 시 silent pass 가능성**: `Neo4jChainSightService.is_available()`이 `False`를 반환해도 태스크는 정상 완료로 처리되어 Neo4j 장애가 모니터링에 노출되지 않는다.

즉시 조치 권고:
1. `serverless/services/keyword_generator.py`의 `generate_keywords_sync`를 `asyncio.run()`으로 교체하거나 동기 Gemini API(`client.models.generate_content`)로 재작성한다.
2. `macro/services/fmp_client.py`에 402/429 전용 예외 분기를 추가한다.

---

## 1. 의존성 매트릭스

| 서비스/모듈 | FMP | Gemini | FRED | Neo4j | SEC EDGAR | Redis | 에러 핸들링 | Fallback |
|---|---|---|---|---|---|---|---|---|
| api_request/providers/fmp/ | O | | | | | | FMPClientError 계층 | ProviderResponse.error |
| serverless/services/fmp_client | O | | | | | O | FMPAPIError (httpx) | raise / cached |
| macro/services/fmp_client | O | | | | | | requests.HTTPError | return None / [] |
| news/providers/fmp | O | | | | | | Exception → [] | [] (silent) |
| stocks/services/sp500_eod_service | O | | | | | | CB + FMPAPIError | stats.errors++ |
| serverless/services/data_sync | O | | | | | | CB + FMPAPIError | partial success |
| thesis/tasks/eod_pipeline | O | | FRED | | | | FMPPremiumError + ClientError | None, None |
| serverless/services/keyword_generator | | Gemini | | | | | Exception → [] | [] |
| serverless/services/keyword_generator_v2 | | Gemini | | | | | Exception → [] | [] |
| news/services/keyword_extractor | | Gemini | | | | | Exception → FALLBACK_KEYWORDS | fallback list |
| validation/services/llm_peer_filter | | Gemini | | | | | Exception → {error: str} | error dict |
| sec_pipeline/extractor | | Gemini | | | | | json.JSONDecodeError / raise | {} or raise |
| rag_analysis/services/llm_service | | Gemini | | | | O | CB + rate retry | error event |
| marketpulse/briefing/client | | Gemini | | | | O | CB | raise |
| portfolio/llm/client | | Gemini(+Anthropic) | | | | | LLMRateLimitError→폴백 | Anthropic fallback |
| thesis/services/thesis_builder | | Gemini | | | | | CB + Exception | fallback 없음 |
| macro/services/fred_client | | | FRED | | | | requests.HTTPError | raise |
| serverless/services/neo4j_chain_sight_service | | | | Neo4j | | O | CB | return None / False |
| sec_pipeline/collector | | | | | SEC EDGAR | | requests.HTTPError | edgartools fallback |
| rag_analysis (cache layer) | | | | | | O | - | cache miss → generate |

---

## 2. FMP 상세

### 2.1 클라이언트 계층

**api_request/providers/fmp/client.py** (기준 구현체)

- HTTPS, `requests` 라이브러리, `timeout=30` (라인 121).
- `request_delay=0.2`초 (라인 57), `last_request_time` 기반 단순 rate limit. 인스턴스 재생성 시 카운터 리셋 → 여러 인스턴스가 동시에 생성되면 실질적 rate limit 효과 없음.
- `daily_calls` 카운터가 인스턴스 변수 (라인 69). Celery worker가 인스턴스를 매 태스크마다 생성하면 일일 한도 추적이 무의미하다.
- 402 → `FMPPremiumError` 즉시 raise (라인 129), 재시도 없음 (라인 149의 `raise`).
- 429 → `FMPRateLimitError` 즉시 raise (라인 133), 재시도 없음.
- 401/403 → `FMPAuthError` 즉시 raise.
- 기타 예외 (`requests.RequestException`) → 최대 3회 exponential backoff (2s, 4s) 재시도 (라인 153~158).

**serverless/services/fmp_client.py** (Market Movers용)

- `httpx.Client(timeout=30.0)` (라인 44). `requests`가 아닌 `httpx`.
- `_make_request`에서 `response.raise_for_status()` 직접 호출 (라인 74). 402/429를 별도 분기 없이 `FMPAPIError`로 wrap (라인 84~88).
- **402 전용 `FMPPremiumError`가 존재하지 않는다.** 소비자가 `FMPPremiumError`를 catch하면 전혀 잡히지 않는다.
- 429도 `FMPAPIError`로 퉁쳐지므로 retry 없이 호출자에게 전파.
- 캐시: `get_market_gainers` → 키 `fmp:market_gainers`, TTL 300초 (라인 112~118). `get_quote` → `fmp:quote:{symbol}`, TTL 60초 (라인 174~190). `get_company_profile` → `fmp:profile:{symbol}`, TTL 86400초 (라인 265~266). 캐시 키 패턴은 내부 일관성 있음.

**macro/services/fmp_client.py** (Market Pulse용)

- `requests`, `timeout=30` (라인 108). rate limit: 인스턴스 수준 `last_request_time` (라인 100~102).
- `response.status_code != 200` → `response.raise_for_status()` (라인 111~113). 402/429를 별도 처리하지 않는다.
- `get_quote()`는 `try/except Exception` → `return None` (라인 141~143). 단일 심볼 실패 시 silent skip.
- `get_batch_quotes()`는 심볼별 개별 호출 (라인 160~163). 한 심볼에서 402가 나도 나머지는 계속 진행.

### 2.2 소비자별 fallback 패턴

| 모듈 | 호출 함수 | 예외 처리 | 실패 시 동작 |
|---|---|---|---|
| news/providers/fmp.py:51 | `get_stock_news` | `except Exception → return []` | 빈 리스트 반환 (silent skip) |
| news/providers/fmp.py:88 | `get_general_news` | `except Exception → return []` | 빈 리스트 반환 |
| stocks/services/sp500_eod_service.py:133 | `get_historical_ohlcv` via CB | `CircuitBreakerError → skip`, `FMPAPIError → raise` | CB 발동 시 해당 심볼 skip |
| serverless/services/data_sync.py:74 | `get_market_gainers/losers/actives` via CB | `CircuitBreakerError → partial`, `FMPAPIError → retry` | CB open → 해당 타입 0건 |
| thesis/tasks/eod_pipeline.py:104 | `get_quote`, `key_metrics` etc. | `FMPPremiumError → None,None`, `FMPClientError → None,None`, `Exception → None,None` | 지표 값 없음으로 처리 |
| serverless/services/chain_sight_service.py:205 | `get_company_profile` | `FMPAPIError → continue` | 해당 심볼 스킵 |

### 2.3 발견된 취약점

**P1: serverless/fmp_client.py에서 402/429 미분기 (중요)**

`serverless/services/fmp_client.py:84`에서 `httpx.HTTPStatusError`를 잡아 `FMPAPIError`로 wrap한다. 402나 429를 소비자에서 `FMPPremiumError` / `FMPRateLimitError`로 구분해 처리하는 코드가 있으면 catch 실패한다. `data_sync.py`에서 `FMPAPIError`만 잡으므로 현재는 우연히 작동하지만, common-bugs #23 패턴(`.` 포함 심볼 배치 제외)이 이 클라이언트를 통하면 적용되지 않는다.

**P2: macro/fmp_client.py의 rate limit 인스턴스 독립성**

`macro/services/fmp_client.py`의 rate limiter는 인스턴스 변수(`last_request_time`)이다. Celery worker가 태스크마다 `FMPClient()`를 새로 생성하면 rate limit이 전혀 적용되지 않아 burst 호출 → 429 폭주 가능성이 있다.

**P3: daily_calls 카운터의 프로세스 분리 문제**

`api_request/providers/fmp/client.py:69`의 `daily_calls`는 프로세스 메모리에만 존재한다. Celery worker 4개가 각자 10,000호출 카운터를 갖는다 → 실제 일일 한도 10,000을 초과해도 차단되지 않는다. Redis에 atomic incr로 공유 카운터를 둬야 한다.

**P4: SP500 구성 종목 CSV를 datahub.io에서 직접 fetching**

`serverless/services/fmp_client.py:361`에서 `https://datahub.io/core/s-and-p-500-companies/r/constituents.csv`를 직접 다운로드한다. datahub.io가 불안정하거나 URL이 변경되면 `FMPAPIError`가 발생하고, 야간 자동화에서 S&P 500 구성 종목 갱신이 중단된다. 캐시는 86400초(24시간)로 1회 실패 후 다음 날까지 캐시 없이 재시도가 반복된다.

---

## 3. Gemini 상세

### 3.1 클라이언트 패턴

프로젝트에서 Gemini를 호출하는 방법은 세 가지로 분류된다:

**패턴 A: genai.Client 동기 (Celery 안전)**

```
client = genai.Client(api_key=...)
response = client.models.generate_content(model=..., contents=..., config=...)
```

사용처: `news/services/keyword_extractor.py:190`, `validation/services/llm_peer_filter.py:79`, `sec_pipeline/extractor.py:68`, `marketpulse/briefing/client.py:53`, `portfolio/llm/client.py:229`, `thesis/services/thesis_builder.py` (CircuitBreaker 경유).

**패턴 B: genai.Client 비동기 (Django views에서만 안전)**

```
response = await self.client.aio.models.generate_content_stream(...)
```

사용처: `rag_analysis/services/llm_service.py:195` (Django async view 전용, CircuitBreaker acall 경유).

**패턴 C: async + asyncio.get_event_loop().run_until_complete (위험)**

```
# serverless/services/keyword_generator.py:247
response = await self.client.aio.models.generate_content(...)
# serverless/services/keyword_generator.py:374-380
loop = asyncio.get_event_loop()
if loop.is_closed():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
results = loop.run_until_complete(...)
```

Celery 태스크(`serverless/tasks.py`)에서 `generate_keywords_sync`를 호출한다. common-bugs #8 위반이다. macOS fork 환경에서 Obj-C 런타임 충돌, Python 3.10+ 이후의 deprecation(`get_event_loop()` 경고) 문제가 있다. `keyword_generator_v2.py:409`에도 동일 패턴이 존재한다.

**429 / quota 처리 현황:**

- `rag_analysis/services/llm_service.py:234`: 문자열 검색(`'rate' in error_str or 'quota' in error_str or '429' in error_str`)으로 판단 후 지수 백오프(1s, 2s, 4s) 재시도. CircuitBreaker와 이중 보호.
- `portfolio/llm/client.py:62-80`: `_classify_gemini_error()`로 예외 클래스명 + 메시지 기반 분류 → `LLMRateLimitError` 발생 → 1회 재시도 후 fallback(Anthropic).
- `marketpulse/briefing/client.py:68`: CircuitBreaker `get_circuit('gemini')`로 wrap. CB 파라미터는 기본값(`failure_threshold=5, recovery_seconds=60, retry_attempts=3`).
- `news/services/keyword_extractor.py:152`: `except Exception → status='failed', keywords=FALLBACK_KEYWORDS`. 429 여부를 구분하지 않고 모든 예외에 FALLBACK_KEYWORDS를 반환한다.
- `sec_pipeline/extractor.py:89`: `except Exception → raise`. 429 발생 시 태스크 전체가 실패한다.
- `validation/services/llm_peer_filter.py:88`: `except Exception → return {'error': str(e)}`. 소비자가 에러 딕셔너리를 확인하면 처리되지만, 재시도 없음.

**JSON 파싱 실패 처리:**

- `sec_pipeline/extractor.py:86`: `json.JSONDecodeError → return {'relationships': [], 'error': ...}`. 별도 분기 있음.
- `news/services/keyword_extractor.py:313`: `json.JSONDecodeError → 정규식 부분 복구 → 실패 시 FALLBACK_KEYWORDS`.
- `validation/services/llm_peer_filter.py:86`: `json.loads()` 실패 시 예외가 외부 try/except로 전달돼 `{'error': str(e)}` 반환.

**timeout 설정:**

어떤 Gemini 클라이언트도 명시적 `timeout` 파라미터를 `GenerateContentConfig`에 전달하지 않는다. google-genai SDK 기본 timeout에 의존한다. 네트워크 장애 또는 모델 응답 지연 시 worker가 무기한 대기할 수 있다.

### 3.2 모듈별 패턴

**rag_analysis 그룹**

`llm_service.py`는 `CircuitBreaker('gemini_rag')` + 지수 백오프 retry + streaming async. 가장 완성도 높은 구현이다. `rag_analysis/tasks.py:409`는 `asyncio.new_event_loop()` 패턴을 사용하지만 `try/finally: loop.close()`로 정리하며, `CacheWarmer`만 호출하므로 직접적인 LLM 호출은 아니다.

**thesis 그룹**

`thesis/services/thesis_builder.py`는 `CircuitBreaker`를 통해 Gemini를 호출한다. `marketpulse/utils/circuit_breaker.py`의 CB 구현체가 공유된다. CB가 OPEN이면 `CircuitBreakerError`를 raise하며, thesis_builder에서 이를 잡아 fallback을 반환한다.

**news 그룹**

`news/services/keyword_extractor.py`는 동기 API를 올바르게 사용하지만, 429 전용 재시도 없이 FALLBACK_KEYWORDS로 즉시 대체한다. 야간 자동화에서 Gemini quota 초과 시 FALLBACK_KEYWORDS 3개만 저장되고 경보 없이 조용히 통과한다.

**serverless 그룹**

`serverless/services/keyword_generator.py`가 패턴 C(async + event_loop)를 사용한다. `keyword_service.py`, `llm_relation_extractor.py`는 별도 Gemini 클라이언트를 직접 생성하며 각각 독자적인 에러 처리를 갖는다. `llm_relation_extractor.py:229`: `except Exception → ExtractionResult(relations=[], error=str(e))` — 빈 결과로 graceful degradation.

**portfolio 그룹**

`portfolio/llm/client.py`가 가장 정교한 구현: `_classify_gemini_error()`, `_classify_anthropic_error()`, 1회 재시도 + Anthropic 폴백, 비용 가드(`LLM_BUDGET_MAX_CALLS`). Gemini 장애 시 자동으로 Anthropic Sonnet/Haiku로 전환한다.

**validation 그룹**

`validation/services/llm_peer_filter.py`는 단발 호출(재시도 없음), 에러 시 `{'error': str(e)}` 반환. 야간 자동화에 포함되면 조용히 빈 peer 결과를 반환한다.

**sec_pipeline 그룹**

`sec_pipeline/extractor.py`의 `extract_supply_chain()`은 `json.JSONDecodeError`는 잡지만 `Exception`은 `raise`한다. 즉 네트워크 오류, 429, timeout은 호출자에게 전파되어 Celery 태스크 실패로 이어진다.

### 3.3 발견된 취약점

**P1: keyword_generator.py의 async Celery 호출 (critical)**

`serverless/services/keyword_generator.py:374-380`에서 `asyncio.get_event_loop()`를 사용해 async LLM을 Celery 태스크 내에서 실행한다. Python 3.10+ 환경에서 `DeprecationWarning`, macOS fork 환경에서 SIGSEGV 유발 가능. `asyncio.run()`으로 교체하거나 동기 API로 전환해야 한다. `keyword_generator_v2.py:409`도 동일 패턴.

**P2: Gemini timeout 미설정**

모든 Gemini 호출 모듈에서 SDK 레벨 timeout을 명시하지 않는다. gemini-2.5-flash가 복잡한 쿼리에서 30~60초 이상 지연되면 Celery worker가 차단된다.

**P3: sec_pipeline/extractor.py에서 429 시 Celery 태스크 전체 실패**

`extract_supply_chain()`과 `extract_business_model()`은 `json.JSONDecodeError` 외 예외를 `raise`한다. 야간 S&P 500 배치 처리 중 Gemini quota 소진 시 해당 태스크 이후 모든 심볼이 처리되지 않는다.

**P4: news/keyword_extractor.py에서 429 구분 없이 FALLBACK_KEYWORDS 저장**

모든 Gemini 오류(인증, quota, timeout, JSON 파싱)가 동일한 FALLBACK_KEYWORDS 3개로 처리된다. 야간 자동화에서 quota 초과가 발생해도 `status='failed'`로 DB에 기록될 뿐 경보가 없다. 다음 날 키워드가 의미 없는 fallback으로 채워진다.

---

## 4. 기타 의존성

### 4.1 FRED

**파일**: `macro/services/fred_client.py`

- `requests`, `timeout=30`, rate limiter: `api_request.rate_limiter.get_rate_limiter("fred")` 사용. 분당 120회 제한.
- Transient 에러(500~504): 최대 3회 재시도, linear backoff 2s/4s/6s (라인 119~128).
- Permanent 에러(401/403/404): 즉시 `raise_for_status()` (라인 106~111).
- `requests.exceptions.RequestException`: 최대 3회 재시도 후 `raise` (라인 138~153).
- `get_vix()`, `get_interest_rates()` 등 개별 메서드는 `try/except Exception → return {}` 또는 `return None` (라인 274, 396). 단일 지표 실패가 전체 macro 수집을 중단시키지 않는다.
- `thesis/tasks/eod_pipeline.py:192`에서 `except Exception → return None, None` — FRED 실패 시 지표 값 없음.
- 전반적으로 방어 코딩이 잘 되어 있다. **FRED는 저위험.**

### 4.2 Neo4j

**파일**: `serverless/services/neo4j_chain_sight_service.py`

- 드라이버 초기화: `get_neo4j_driver()` lazy init (라인 109). 드라이버 없으면 `is_available() → False`.
- CircuitBreaker: `get_circuit('neo4j_chain_sight', failure_threshold=5, recovery_seconds=60)` (라인 117~121).
- `_run_with_cb()` 헬퍼: CB 내부에서 호출, `CircuitBreakerError → return None` (라인 141~143).
- `is_available()` 반환 False 시 대부분 메서드가 `return False` 또는 `return []`로 silent skip.
- **문제**: Neo4j CB가 OPEN 상태일 때 태스크가 정상 완료 처리되므로, 야간 자동화 보고서에 "성공"으로 기록되고 Neo4j 장애가 장시간 숨겨진다. `serverless/tasks.py`의 관련 태스크들은 `except Exception → raise`로 Celery retry를 유발하지 않고 CB에만 의존한다.
- CB 상태는 Redis에 저장된다(`cache.set`). Redis 장애 시 CB 상태도 초기화된다 → 폭발적 재시도 가능.

### 4.3 SEC EDGAR

**파일**: `sec_pipeline/collector.py`

- `requests`, `timeout=30` (라인 86), `timeout=60` (라인 154, HTML 다운로드용).
- Rate limit: `time.sleep(0.12)` (라인 83, 130, 151). SEC 정책(10 req/sec) 준수.
- `get_filing_metadata()`: `requests.exceptions.RequestException → raise` (라인 89). 소비자(`collect()`)에서 별도 처리 없이 `None` 반환 경로로 fallback.
- `fetch_filing_html()`: `requests.exceptions.RequestException → raise`.
- 검증 실패 시 `edgartools` 라이브러리로 fallback (라인 189~215). edgartools 미설치 시 `ImportError → None` (라인 211).
- `User-Agent` 헤더 설정 (`'Stock-Vis stockvis@example.com'`, 라인 30). SEC EDGAR 필수 요건 충족.
- **전반적으로 안전하나**, 네트워크 오류 시 `raise`하므로 소비자 측 retry가 필요하다.

### 4.4 Redis (캐시 장애 시 graceful degradation)

Redis는 Django cache backend로 사용된다. 현재 확인된 세 가지 사용처:

1. **FMP 캐시** (`serverless/services/fmp_client.py`): `cache.get()` 실패 시 캐시 miss로 처리, 재호출. 에러 처리 없음 — Redis 연결 실패 시 `django.core.cache.backends.base.CacheKeyWarning` 또는 `ConnectionError`가 발생할 수 있다. 래핑 코드가 없어 `cache.get()` 예외가 `_make_request()` 호출 이전에 전파된다.
2. **CircuitBreaker 상태 저장** (`marketpulse/utils/circuit_breaker.py`): CB 상태를 `cache.get/set`으로 관리. Redis 장애 시 `cache.get()` → `None` 반환(기본 동작) → CB 상태가 `CircuitState.CLOSED`로 인식 → 보호 기능 상실.
3. **RAG 분석 캐시** (`rag_analysis/services/cache.py`): `cache.get/set` 직접 호출. `try/except` 없이 사용하는 구간이 다수 존재한다.

**Redis 장애 시 이중 위험**: CB 상태가 날아가므로 모든 외부 API(Gemini, Neo4j)에 대한 보호막이 동시에 사라진다.

---

## 5. Circuit Breaker 도입 후보

| 우선순위 | 호출 지점 | 장애 영향 | 현재 보호 | 권고 |
|---|---|---|---|---|
| 1순위 | `sec_pipeline/extractor.py`의 Gemini 호출 | 배치 전체 중단 | 없음 | CB + 최대 3회 retry 추가 |
| 1순위 | `macro/services/fmp_client.py` 전체 | Market Pulse 완전 중단 | 없음 | CB('fmp_macro') 도입 |
| 2순위 | `news/services/keyword_extractor.py`의 Gemini | 야간 키워드 fallback 자동 저장 (무경보) | fallback만 | CB + 429 전용 retry + 경보 |
| 2순위 | `thesis/tasks/eod_pipeline.py`의 FMP 반복 호출 | 야간 지표 fetch 무결성 | FMPPremiumError 처리 있음 | 공유 CB ('fmp_thesis') 도입으로 burst 차단 |
| 3순위 | `serverless/services/neo4j_chain_sight_service.py` | 이미 CB 있으나 silent pass | CB(OPEN=silent) | OPEN 시 Celery retry 1회 발생하도록 변경 |
| 3순위 | Redis cache layer | CB 상태 소실 → 전체 보호막 무력화 | 없음 | Redis 연결 실패 시 LocMemCache fallback 설정 |

---

## 6. 권고사항 (우선순위 정렬)

**P0 (즉시):**

- `serverless/services/keyword_generator.py:374` 및 `keyword_generator_v2.py:409`의 `asyncio.get_event_loop()` + `loop.run_until_complete()` 패턴을 `asyncio.run()`으로 교체하거나 `async _call_llm()`을 `client.models.generate_content()` 동기 호출로 변환한다. Celery worker가 현재 패턴으로 macOS에서 SIGSEGV를 발생시킬 수 있다.
- `macro/services/fmp_client.py`에서 `response.status_code == 402` → `FMPPremiumError`, `response.status_code == 429` → `FMPRateLimitError` 분기를 `raise_for_status()` 이전에 추가한다.

**P1 (단기, 1주 이내):**

- `sec_pipeline/extractor.py`의 `extract_supply_chain()`, `extract_business_model()`에 Gemini 429/timeout 전용 3회 retry(지수 백오프)를 추가한다. 현재 배치 처리 중 quota 소진 시 태스크가 즉시 실패한다.
- `news/services/keyword_extractor.py`의 `_call_llm()`에 429 구분 retry를 추가한다. 현재는 429와 JSON 파싱 오류가 동일한 FALLBACK_KEYWORDS로 처리된다.
- `api_request/providers/fmp/client.py`의 `daily_calls` 카운터를 Redis atomic counter로 이전한다. 현재 인스턴스 독립 카운터는 다중 worker 환경에서 일일 한도 추적이 불가능하다.
- 모든 Gemini `GenerateContentConfig`에 `timeout` 파라미터를 명시한다(권장: 60초). 현재 SDK 기본값에 의존하여 worker 블로킹 위험이 있다.

**P2 (중기, 2~4주 이내):**

- `serverless/services/data_sync.py`가 사용하는 `serverless/services/fmp_client.py`에 `FMPPremiumError` 분기를 추가해 `.` 포함 심볼 배치에서 common-bugs #23 패턴이 적용되도록 한다.
- `marketpulse/utils/circuit_breaker.py`의 CB 상태 저장에 Redis 장애 시 in-memory fallback을 추가한다. 현재 Redis 다운 시 모든 CB가 CLOSED 상태로 리셋된다.
- `serverless/services/fmp_client.py`의 `get_sp500_constituents()`에서 datahub.io CSV 의존성을 제거하고 FMP `/stable/sp500-constituent` 엔드포인트 가용 여부를 주기적으로 확인하거나, 로컬 seed 파일로 fallback하는 구조를 도입한다.
- Neo4j CB가 OPEN인 경우 Celery 태스크가 silent pass로 완료되는 문제를 해결한다. CB OPEN 시 최소 `logger.error` + Celery `self.retry(countdown=300)` 1회를 발생시켜 모니터링에 노출한다.

---

## 부록 A. 조사한 파일 목록

**FMP 측 (8개 직접 Read)**
- `api_request/providers/fmp/client.py`
- `api_request/providers/fmp/provider.py`
- `serverless/services/fmp_client.py`
- `macro/services/fmp_client.py`
- `news/providers/fmp.py`
- `stocks/services/sp500_eod_service.py` (소비자)
- `serverless/services/data_sync.py` (소비자)
- `thesis/tasks/eod_pipeline.py` (소비자, 일부)

**Gemini 측 (9개 직접 Read)**
- `rag_analysis/services/llm_service.py`
- `portfolio/llm/client.py`
- `news/services/keyword_extractor.py`
- `serverless/services/keyword_generator.py`
- `sec_pipeline/extractor.py`
- `validation/services/llm_peer_filter.py`
- `marketpulse/briefing/client.py`
- `thesis/services/thesis_builder.py` (일부)
- `rag_analysis/tasks.py` (일부)

**기타 (5개 직접 Read)**
- `macro/services/fred_client.py` (FRED)
- `serverless/services/neo4j_chain_sight_service.py` (Neo4j, 일부)
- `sec_pipeline/collector.py` (SEC EDGAR)
- `marketpulse/utils/circuit_breaker.py` (공통 CB)
- `serverless/services/llm_relation_extractor.py` (Gemini 소비자, 일부)

**Grep 조사 파일** (패턴 검색으로 확인)
- `serverless/tasks.py` (except 패턴, async 패턴)
- `serverless/services/chain_sight_service.py` (FMPAPIError 처리 패턴)
- `rag_analysis/services/cache.py` (Redis cache 패턴)
