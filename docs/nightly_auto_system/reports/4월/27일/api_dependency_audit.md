# 외부 API 의존성 감사 보고서

- 일자: 2026-04-27
- 범위: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis (+ Alpha Vantage 잔존 여부)
- 모드: **읽기 전용 감사** (코드 수정 없음)
- 분석 방식: grep 전수 + 핵심 호출 지점 직접 코드 확인

> 본 보고서의 라인 번호는 감사 시점(`feature/chainsight-graph-v2` 브랜치)을 기준으로 합니다. 일부 보조 위치는 ±몇 줄 오차가 있을 수 있으니 인용 시 검증하세요.

---

## 의존성 매트릭스

| 의존성 | 호출 클라이언트(들) | Retry/Backoff | Rate Limit 처리 | Circuit Breaker | 캐시 사용 | Fallback 패턴 | 단일 장애 시 영향 범위 |
|---|---|---|---|---|---|---|---|
| FMP (가격/재무/뉴스) | **3개 분리 구현** (api_request, macro, serverless) | api_request만 3회 exponential, 나머지 부재 | client별 0.2~0.5s sleep, 글로벌 미존재 | ❌ | 일부(serverless), 비표준 TTL | silent `{}` / `[]` 또는 None | 가격·재무·Movers·SP500·News·Korean Overview 동기화 모두 |
| Gemini (LLM) | `google-generativeai` 직접 호출 + `LLMServiceLite` 래퍼 | LLMServiceLite·briefing만 재시도, 나머지 직접 호출 | 일부 task에 `time.sleep(4)` (15 RPM) | ✅ marketpulse만 (`get_circuit('gemini')`) | semantic cache(keyword), Redis(relations) | 기본 None / 빈 리스트 / 사전정의 fallback | 가설 빌더 동기 응답, RAG, 뉴스 분석, SEC 추출 |
| FRED | `macro/services/fred_client.py` | 3회 + transient(5xx) 분기 | 별도 rate limiter 사용 | ❌ | macro에서 짧은 TTL | 개별 지표 raise, 다른 지표는 진행 | Market Pulse 거시 지표, Beat 4회/일 |
| Neo4j | `rag_analysis/services/neo4j_driver.py` 싱글톤 + `serverless/services/neo4j_chain_sight_service.py` | 기본 driver retry만, 명시 재시도 없음 | N/A | ❌ | 5분 TTL on chain_sight | `is_available()=False` 시 빈 결과, Postgres 보존 | Chain Sight 그래프 화면 전체 |
| SEC EDGAR | `sec_pipeline/collector.py` | 부재 (선제적 sleep 0.12s만) | 0.12s sleep, User-Agent 헤더 명시 | ❌ | CIK 캐시(prosess in-mem) | edgartools 라이브러리 fallback, partial status | 10-K Supply Chain / Business Model 추출 |
| Redis | Django cache + Celery broker + Channels | N/A | N/A | N/A | 본인 자체 | **부재** (LocMem 폴백 없음) | 전체 Celery, 캐시, WebSocket SPOF |
| Alpha Vantage | **사용 중단** (잔존 흔적: news 모델/migration) | - | - | - | - | - | 영향 없음 |

---

## FMP 상세

### 1) 클라이언트가 3개로 분리되어 있다 — 가장 큰 구조적 위험

| 클라이언트 | 위치 | Retry | Delay | 캐시 | 예외 클래스 |
|---|---|---|---|---|---|
| **A. api_request** | `api_request/providers/fmp/client.py:40-491` | 3회 exp(2s×n) | 0.2s | 없음 | `FMPClientError`, `FMPRateLimitError`, `FMPAuthError`, `FMPPremiumError(402)` |
| **B. macro** | `macro/services/fmp_client.py` | 없음 | 0.5s | 호출자 측 cache.get/set | 자체 처리 후 raise |
| **C. serverless** | `serverless/services/fmp_client.py` | 없음 | 없음(캐시 우선) | Redis(5분~24h) | 단일 `FMPAPIError` |

**위험**: 세 클라이언트가 각각 카운터/딜레이를 관리하기 때문에 동시 실행 시 분당 호출의 **합산 추적이 불가**합니다. 구체적으로 EOD 슬롯(18:00~18:30)에 SP500 동기화·재무제표·Movers·News·Korean Overview·Chain Sight·Validation이 동시에 깨어나면, 각 클라이언트가 본인의 0.2/0.5초 딜레이만 지키고 글로벌 합은 Starter Plan의 300/min을 넘길 수 있습니다.

**권장(보고용)**: A를 표준 클라이언트로 단일화하고 B/C는 thin wrapper로 줄이거나, Redis 기반 글로벌 토큰 버킷을 도입합니다.

### 2) Silent Failure — `serverless/services/data_sync.py:128-151`

```python
try:
    quote = self.fmp.get_quote(symbol)
except FMPAPIError as e:
    logger.warning(...); quote = {}            # ❶
try:
    historical = self.fmp.get_historical_ohlcv(symbol, days=20)
except FMPAPIError as e:
    logger.warning(...); historical = []        # ❷
try:
    profile = self.fmp.get_company_profile(symbol)
    sector = profile.get('sector'); industry = profile.get('industry')
except FMPAPIError as e:
    logger.warning(...); profile = {}; sector = None; industry = None  # ❸
```

세 호출 중 어느 하나가 실패해도 빈 dict/list로 진행한 뒤 RVOL·trend_strength·sector_alpha·etf_sync·volatility 계산까지 그대로 통과합니다. 결과적으로 **실패한 종목은 0/null 지표로 DB에 저장**되며, Movers 대시보드에서 "값은 있는데 의미 없는 행"이 됩니다. 로그 외에는 알 길이 없습니다.

### 3) FMPPremiumError(402) 처리 비대칭

- ✅ 잘 처리: `thesis/tasks/eod_pipeline.py` `_fetch_fmp_value`에서 명시적 `except FMPPremiumError`. None 반환 후 정상 진행.
- ⚠️ 무차별 catch: `stocks/tasks.py`의 `update_financials_with_provider`/`update_stock_with_provider`는 `except Exception` 한 번으로 처리 → 402도 일반 실패와 동급으로 흡수. 결과적으로 BRK.B 같은 dot 심볼은 매번 호출되고 매번 실패합니다(쿼터만 소모).
- ❌ 미처리: `serverless/services/data_sync.py`는 `FMPAPIError` 단일 예외로 흡수해 402와 일시 장애를 구분 못함.

### 4) Celery 재시도 정책 일관성 없음

| 태스크 | retry 설정 | 평가 |
|---|---|---|
| `serverless/tasks.py` `sync_daily_market_movers` | `max_retries=3`, 300s 지연 | 적절 |
| `stocks/tasks.py` `update_financials_with_provider` | `rate_limit='6/m'` 만 | **재시도 없음** — 첫 실패 시 종목 손실 |
| `stocks/tasks.py` `update_stock_with_provider` | `max_retries=3` | 적절 |
| `validation/tasks.py` `fetch_annual_financials` | `max_retries=1` | 보수적, 재무는 재실행 비용 큼 |

`rate_limit='6/m'`는 Celery가 워커 큐 진입 속도만 제한할 뿐, FMP 5xx/Timeout에 대한 재시도와는 무관합니다. **이 위치는 자주 실패하면서 자동 회복이 없는 가장 큰 구멍**입니다.

### 5) FMP 위험 지점 Top 5

1. `serverless/services/data_sync.py:128-151` — Silent failure로 잘못된 0/null 데이터가 Movers 화면에 노출.
2. **3중 클라이언트** — 글로벌 rate limiting 부재, 분당 한도 초과 위험.
3. `stocks/tasks.py:update_financials_with_provider` — Celery 재시도 미설정. 일시 장애 시 종목 단위 손실.
4. `stocks/tasks.py` `except Exception` 광범위 catch — 402/인증/일시장애 미구분, 쿼터만 소모.
5. 캐시 TTL 비표준 — `serverless`(5분~24h), `stocks/services/fmp_fundamentals.py`(600s), `macro`(1분~7일) 혼재로 동일 심볼 중복 호출 가능.

### 6) FMP 강점

- `api_request/providers/fmp/client.py`의 예외 분류 + 재시도 정책은 견고함.
- Provider 추상화(`api_request/providers/fmp/provider.py`)가 fallback provider 전환 통로를 열어둠.
- `thesis/tasks/eod_pipeline.py`의 `FMPPremiumError` 명시 처리는 모범 사례.
- Celery `rate_limit`로 분당 호출 분산은 어느 정도 작동.

---

## Gemini 상세

### 1) 호출 인벤토리(주요 지점)

| 위치 | 모델 | 호출 형태 | 429 처리 | JSON 파싱 안전성 | Celery 컨텍스트 | 사용자 동기 |
|---|---|---|---|---|---|---|
| `rag_analysis/services/llm_service.py` (`LLMServiceLite`) | gemini-2.5-flash | async stream | ✅ exp backoff [1,2,4]s × 3 | ✅ | 아님 | 아님 |
| `rag_analysis/services/adaptive_llm_service.py` | 동적 | async (`generate_content_async`) | ❌ | ⚠️ | 아님 | 아님 |
| `thesis/services/prompt_builder.py` `call_gemini`/`call_gemini_light`/`call_gemini_suggestions` | gemini-2.5-flash | sync | ❌ | 일부만 `JSONDecodeError` catch | 아님 | **Yes** (서비스 측 호출) |
| `thesis/views/conversation_views.py:168` `process_llm_turn` | (위 빌더 경유) | sync | ❌ | ⚠️ | 아님 | **Yes — POST 응답 동기 대기** |
| `news/services/news_deep_analyzer.py` | gemini-2.5-flash | sync | ❌ | `_parse_response` 의존 | Beat에서 호출 | 아님 |
| `news/services/keyword_extractor.py` | gemini-2.5-flash | sync | ❌ | ✅ + `FALLBACK_KEYWORDS` | Celery | 아님 |
| `validation/services/llm_peer_filter.py` | gemini-2.5-flash | sync | ❌ | ✅ | 아님 | Yes (필터 응답 대기) |
| `sec_pipeline/extractor.py` | gemini-2.5-flash | sync | ❌ | ✅(`{}` fallback) | 파이프라인 | 아님 |
| `serverless/services/llm_relation_extractor.py` | gemini-2.5-flash | sync | ❌ | ✅ + Redis 캐시 | Celery(neo4j 큐) | 아님 |
| `serverless/services/keyword_generator(_v2).py` | gemini-2.5-flash | sync/async 혼재 | ❌ | ⚠️ | Celery | 아님 |
| `serverless/services/thesis_builder.py` | gemini-2.5-flash | sync | ❌ | ⚠️ | Celery | 아님 |
| `marketpulse/briefing/client.py` `_generate_sync` | gemini-2.5-flash | sync | **Circuit Breaker + tenacity 3회** | ✅(`getattr(response,'text','')`) | Celery | 아님 |
| `marketpulse/tasks/briefing.py` | (위 client 경유) | sync | task `autoretry_for` 추가 | ✅ | Celery | 아님 |

> Celery 컨텍스트 호출은 모두 sync API를 쓰고 있어 Bug #8(Celery에서 async LLM)은 회피된 상태로 보입니다.

### 2) 사용자 동기 호출 — 가장 위험한 위치

`thesis/views/conversation_views.py:147-173`의 `ConversationRespondView.post`는 LLM 모드일 때 **`process_llm_turn(...)`을 그대로 await 없이 동기 호출**하고 그 결과를 즉시 Response로 반환합니다.

- 한 번의 `prompt_builder.call_gemini` 호출이 `gemini-2.5-flash` 응답을 기다리는 동안 **Gunicorn/uvicorn 워커 슬롯 1개가 점유**됩니다.
- 안에 backoff/재시도가 없으므로 429/일시 장애 시 즉시 5xx로 사용자에게 노출.
- 다중 사용자 + 가설 빌더 동시 사용 시 워커 고갈 가능. Validation 화면(`llm_peer_filter`)도 같은 패턴.

### 3) `response.text` 직접 접근의 위험

여러 호출처에서 `response.text` 또는 `response.text.strip()`을 그대로 쓰고 있습니다(예: `sec_pipeline/extractor.py`, `rag_analysis/services/entity_extractor.py`, `news/services/news_deep_analyzer.py`). google-genai SDK의 `.text`는 내부적으로 `candidates[0].content.parts[0].text`를 프록시하므로, 안전 정책으로 인한 빈 candidates 반환 시 AttributeError/IndexError로 깨질 수 있습니다.

대조: `marketpulse/briefing/client.py:75`는 `getattr(response, 'text', '') or ''`로 방어되어 있어 모범 사례.

### 4) Rate-limit 설계의 비대칭

- `news/services/news_deep_analyzer.py`는 `time.sleep(self.RPM_DELAY)`(약 4초)로 15 RPM Free 한도를 단순 준수.
- 그러나 다른 동기 sync 호출(가설 빌더, LLM Peer Filter, Keyword Extractor)은 **글로벌 RPM 인지 없이 각자 호출**. Beat가 동시에 여러 LLM 태스크를 깨우면 분당 한도를 분산 초과 가능.
- 유일한 Circuit Breaker는 `marketpulse/utils/circuit_breaker.py`(Redis 백업, tenacity exp 1/2/4s, threshold=5, recovery=60s) — `get_circuit('gemini')` 단일 인스턴스가 marketpulse 브리핑에만 적용되어 있습니다.

### 5) Gemini 위험 지점 Top 5

1. **`thesis/views/conversation_views.py` 동기 LLM 호출** — 사용자 응답 지연/5xx, 워커 고갈. (HIGH)
2. **`adaptive_llm_service.py` 429 미처리** — RAG 스트림이 일시 한도에서 즉시 실패. (HIGH)
3. **다수 호출처의 `response.text` 직접 접근** — safety filter/empty candidates 시 `AttributeError`. (MEDIUM)
4. **글로벌 RPM 트래커 부재** — 다중 sync 호출 충돌 시 분당 한도 분산 초과. (MEDIUM)
5. **`sec_pipeline/extractor.py`/`thesis/prompt_builder.py`의 None fallback** — 호출자가 None 체크를 빠뜨리면 빈 결과가 사용자에게 그대로 노출. (MEDIUM)

### 6) Gemini 강점

- `LLMServiceLite`의 retry/토큰 기록/복잡도 기반 모델 설정.
- `marketpulse/briefing/client.py` + Circuit Breaker 통합 — **이 패턴을 다른 모듈로 확장할 수 있는 기준**.
- Structured Output(JSON 스키마)을 적극 사용해 파싱 안정성 확보(`thesis/prompt_builder.py`).
- `serverless/services/llm_relation_extractor.py`의 Redis 캐시(1시간 TTL) — 호출량 80% 감소 효과.

---

## 기타 의존성

### FRED (`macro/services/fred_client.py`)

- 통합 `_make_request` 안에 3회 재시도, **transient(500/502/503/504)와 permanent(401/403/404) 분기** 명시. 30초 timeout, 별도 `get_rate_limiter("fred")` 사용.
- `macro/tasks.py`의 `update_economic_indicators`는 지표별 try/except로 격리 — 하나가 실패해도 나머지는 진행.
- Beat: 매일 4회 호출(06/12/18/22 EST 부근).
- 위험: 부분 실패 시 대시보드에 stale + fresh 지표가 섞일 수 있으나, Circuit Breaker 도입 우선순위는 **Medium**.

### Neo4j

- `rag_analysis/services/neo4j_driver.py`: lazy singleton + `_connection_attempted` 플래그. 연결 실패 시 None 반환 → 호출 측이 `is_available()`로 스킵.
- `serverless/services/neo4j_chain_sight_service.py`: 모든 메서드에서 `is_available()` 가드 → 빈 결과 반환. 5분 TTL Redis 캐시 병행.
- Postgres 측에는 `StockRelationship` 등 보조 테이블이 있어 부분 graceful degradation은 가능.
- `config/celery.py`에 `neo4j` 큐 분리 + fork 후 connection close 처리(macOS Bug #25 대응).
- 위험: GDS/유사도 같은 무거운 쿼리에서 timeout 정책 미명시. 명시 재시도 없음.
- Circuit Breaker 도입 우선순위 **High** — 화면 전체가 의존.

### SEC EDGAR (`sec_pipeline/collector.py`)

- `User-Agent: 'Stock-Vis stockvis@example.com'` 헤더 명시(SEC 정책 준수). 모든 요청 전 `time.sleep(0.12)`로 10 req/sec 선제 준수.
- 30s/60s timeout 분리. `raise_for_status()` 사용.
- HTML 추출 실패 시 `edgartools` 라이브러리 fallback, 일부 항목만 추출되면 `status='partial'`로 마킹.
- 위험: 명시적 429/403 재시도 없음. 대량 배치(예: SP500 일괄) 시 SEC가 일시 차단 가능. Circuit Breaker 우선순위 **Medium**.

### Redis

- `config/settings.py`에서 broker/result/cache(371+ 호출)/Channels 모두 Redis. **단일 장애점**.
- 캐시 미스 시 즉시 외부 API로 흐르므로, Redis 장애 = (1) Celery 큐 정지 (2) 캐시 폭주 동시 발생.
- LocMemCache 폴백 없음. pytest는 `settings_test.py`에서 LocMem으로 격리(common-bugs.md #27).
- Circuit Breaker 우선순위 **High** — 단, 진정한 해법은 폴백 캐시/브로커 이중화 쪽.

### Alpha Vantage

- 전수 검색 결과 활성 코드 없음. `news` 앱 모델/마이그레이션에 흔적만 존재(과거 잔재).
- 행동 항목: 모델 필드/마이그레이션 정리는 별건 리팩토링 후보로만 기록.

---

## Circuit Breaker 후보 (우선순위 순)

| 순위 | 대상 | 이유 | 권장 패턴 |
|---|---|---|---|
| 1 | **Gemini 동기 호출 전반** (`thesis`, `validation`, `news`, `sec_pipeline`, `serverless`) | 분당 한도 충돌 + safety filter 응답 + 429 빈발. 사용자 동기 경로 포함. | `marketpulse/utils/circuit_breaker.py:get_circuit('gemini')` 재사용. 호출 모듈별 sub-name(`gemini:thesis`, `gemini:rag`, `gemini:sec`)으로 격리 |
| 2 | **FMP 클라이언트 통합 + CB** | 3중 분리로 글로벌 rate를 추적할 수 없음. silent failure가 데이터 품질에 직접 영향. | A 클라이언트로 통합 후 `get_circuit('fmp:starter')`. 캐시 TTL 표준화 + Premium/Auth 예외 명시 처리 |
| 3 | **Neo4j 쿼리 보호** | Chain Sight 화면 전체가 의존. is_available은 있으나 일시 장애 누적 시 무한 시도. | `get_circuit('neo4j:chainsight')` + 무거운 GDS는 timeout 명시 |
| 4 | **Redis (캐시) 폴백** | 캐시 + 브로커 + WebSocket SPOF. 다운 시 외부 API 호출 폭주. | LocMemCache 보조 backend, hot-path는 in-memory caching, 캐시 미스 시 동시성 제어(thundering herd 방지) |
| 5 | **SEC EDGAR** | 선제 sleep으로 양호하나 대량 배치 시 429 가능. | `get_circuit('sec:edgar')` + 429/403 명시 backoff |
| 6 | **FRED** | 자체 retry/transient 분기 양호. 추가 CB는 효용 낮음. | 현 상태 유지. 지표별 부분 실패 알림(Slack 등) 정도 |

### 즉시 효과가 큰 보강 후보 (CB 외)

- `serverless/services/data_sync.py:128-151`의 silent fallback을 **명시적 None + DB-level 필터**로 교체.
- `stocks/tasks.py:update_financials_with_provider`에 `autoretry_for=(FMPClientError, requests.RequestException)` + `retry_backoff=True` 추가.
- `response.text` 직접 접근 위치(11+곳)에 공통 헬퍼(`safe_response_text(resp) -> str`) 적용.
- `thesis/views/conversation_views.py`의 동기 LLM 경로를 Celery 큐 + 폴링/스트리밍으로 분리(브라우저 워커 고갈 방지).
- FMP 클라이언트 단일화 + 글로벌 토큰 버킷(Redis Lua) 도입.

---

## 부록 — 검증 출처

- FMP 클라이언트 본체: `api_request/providers/fmp/client.py:40-491` (예외 정의 L20-37, `_make_request` L80-161)
- Silent failure: `serverless/services/data_sync.py:128-151`
- Circuit Breaker 구현: `marketpulse/utils/circuit_breaker.py:62-216`
- Gemini Briefing CB 적용 사례: `marketpulse/briefing/client.py:88-93`
- 사용자 동기 LLM 경로: `thesis/views/conversation_views.py:147-173`
- 추가 호출 인벤토리는 grep 결과(FMP 37파일, Gemini 35파일) 기반.

