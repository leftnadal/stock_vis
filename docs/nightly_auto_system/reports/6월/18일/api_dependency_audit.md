# 외부 API 의존성 감사 보고서

> **감사 유형**: 읽기 전용 (코드 수정 없음)
> **대상 프로젝트**: `/Users/byeongjinjeong/Desktop/stock_vis` (모노레포: `packages/shared/`, `apps/`, `services/`, `thesis/`)
> **감사 일자**: 2026-06-18
> **범위**: FMP·Gemini 호출 전수 + FRED·Neo4j·SEC EDGAR·Redis 장애 영향 + Circuit Breaker 후보 식별
> **방법**: 핵심 클라이언트 직접 정독 + 병렬 Explore 에이전트 3종(FMP/Gemini/기타) 전수 조사 + grep 교차 검증

## 핵심 결론 (TL;DR)

1. **FMP**는 클라이언트 2종이 공존하며 품질이 갈린다. 구버전 `requests` 기반 `client.py`는 retry/402/rate-limit 처리 완비, Market Movers용 `httpx` 기반 `serverless_client.py`는 **retry·402 처리 없음**(캐시만 있음).
2. **FMP 장애 시 일부 대시보드는 통째로 다운**된다 — `weight_source.market_cap_weights()`(RuntimeError raise)와 `market_breadth_service`(try/except 부재)가 대표 사례. 반면 뉴스/스크리너 등은 빈 결과로 degrade.
3. **Gemini는 에러 catch율은 높으나(28/29) timeout이 전역 0건**이고, JSON 파싱 시 `JSONDecodeError` 미처리 + 마크다운 펜스 미제거 구간이 다수. Celery async 금지(버그 #8) 위반은 **없음**(준수 확인).
4. **Circuit Breaker 인프라는 이미 존재**(`packages/shared/api_request/circuit_breaker.py`)하고 6개+ 서비스가 채택했으나, **가장 위험한 호출 지점들(market_breadth, weight_source, Gemini 분산 호출 21곳)에는 미적용**. 추가 + 중복 CB 통합이 우선 과제.
5. 기타 의존성 중 **SEC EDGAR만 치명(Critical)** — 예외를 호출자에게 전파하고 자체 fallback이 없다. FRED·Neo4j·Redis는 graceful degradation 구현됨(부분 장애).

> ⚠️ **신뢰도 주석**: 본 보고서의 `file:line`은 직접 정독한 `client.py`/`serverless_client.py`/설정 파일을 제외하면 Explore 에이전트 보고에 기반하며, 라인 번호는 ±수 라인 오차가 있을 수 있다. 패턴/유무 판정은 grep 교차 검증으로 확정했다. 수정 작업 전 해당 라인 재확인 권장.

---

## 의존성 매트릭스 (서비스별 외부 API × fallback 유무)

| 서비스 / 진입점 | 의존 API | 에러 catch | retry | 캐시 | fallback 동작 | 장애 시 결과 |
|---|---|---|---|---|---|---|
| `weight_source` (concentration 대시보드) | FMP quote | ✅ | ❌ | ❌ | **RuntimeError raise** | 🔴 **대시보드 전체 다운** |
| `market_breadth_service` (공포지수) | FMP gainers/losers/actives | ❌ **없음** | task 3회 | ❌ | 없음 | 🔴 **태스크 fail** |
| `sector_heatmap_service` | FMP 섹터/스크리너 | 부분(loop raise) | ❌ | ❌ | 부분 섹터 누락 | 🟠 부분 누락 |
| `sp500_service.sync_constituents` | FMP / datahub CSV | ✅ CB | task 3회 | ✅ CB | CB open → `{}` | 🟠 동기화 전면 skip |
| `sp500_eod_service` | FMP historical | ✅ (심볼별) | ❌(심볼) | ❌ | error_symbols 집계 | 🟠 부분 동기화 |
| `stock_service.update_stock_data` | FMP profile+quote | ✅ | task 3회 | delete only | DB 재사용 + quote swallow | 🟠 가격 공란 |
| `data_sync.sync_daily_movers` | FMP (serverless_client) | ✅ CB | ❌ | ✅ CB | 타입별 `[]` | 🟢 degrade |
| `enhanced_screener` / `chain_sight` / `filter_engine` | FMP | ✅ | ❌ | ✅ 1h | `[]` / `_empty_result()` | 🟢 degrade |
| `news/providers/fmp` + `aggregator` | FMP news | ✅ | ❌ | ❌ | `[]` swallow | 🟢 degrade |
| `views_search` (검색/시세 API) | FMP search/quote | ✅ | ❌ | ✅ 5~10m | HTTP 503/404 | 🟠 엔드포인트 실패 |
| Market Pulse briefing | Gemini 2.5-flash | ✅ CB | CB+Celery | ❌ | retry | 🟢 degrade |
| Portfolio LLM | Gemini 2.5-flash | ✅ 구체분류 | 수동 2회 | ❌ | fallback provider | 🟢 degrade |
| RAG `llm_service` / `context_compressor` | Gemini (async) | ✅ CB | asyncio backoff | ✅ 1h | error yield / raise | 🟢 degrade |
| `thesis_builder` (BE 양쪽) | Gemini | ✅ CB/수동 | ❌/CB | ❌ | `_fallback_parse` / raise | 🟠 일부 raise |
| `validation/llm_peer_filter` | Gemini | ✅ | ❌ | ❌ | `{"error":...}` (JSON 미처리) | 🟠 파싱 깨짐 |
| `korean_overview_service` | Gemini | ✅ | ❌ | ❌ | **raise** (JSON 미처리) | 🟠 요약 실패 |
| `macro_service` | **FRED** + FMP | ✅ | FRED 3회 | ✅ 60s~24h | 기본값(예: F&G 50) | 🟢 degrade |
| Chain Sight / RAG graph | **Neo4j** | ✅ | dirty-sync 2회 | ✅ 1h | driver=None → 빈 결과 | 🟢 degrade(자동 재동기화) |
| `sec_pipeline.collector` | **SEC EDGAR** | ✅(전파) | ❌ | ❌ | **raise to caller** | 🔴 수집 중단 |
| 전역 캐시/브로커 | **Redis** | 호출처별 상이 | broker 자동재연결 | - | try/except 있는 곳만 graceful | 🟠 일부 500 위험 |

범례: 🔴 치명(전체/태스크 다운) · 🟠 부분(기능/엔드포인트 실패) · 🟢 경미(graceful degrade)

---

## FMP 상세

### 클라이언트 이원화 — 품질 격차가 핵심 리스크

| 항목 | `providers/fmp/client.py` (requests) | `providers/fmp/serverless_client.py` (httpx) |
|---|---|---|
| 용도 | 일반 주가/재무/검색/뉴스 | Market Movers (gainers/losers/actives) |
| 예외 클래스 | `FMPClientError`/`RateLimitError`/`AuthError`/`PremiumError` 4종 | `FMPAPIError` 1종 |
| retry | ✅ `max_retries=3` + exponential backoff (`_make_request:122-170`) | ❌ **없음** |
| rate limit | ✅ `request_delay=0.2s` + `daily_calls` 카운터(10,000/day) | ❌ 없음 |
| 402 처리 | ✅ `FMPPremiumError` 즉시 전파 (`client.py:131-134`) | ❌ HTTP 402가 `HTTPStatusError`로 뭉뚱그려짐 (`serverless_client.py:87-89`) |
| 429 처리 | ✅ `FMPRateLimitError` raise (재시도 제외) (`client.py:137-138`) | ❌ 일반 status 에러로 처리 |
| timeout | ✅ 30s | ✅ 30s |
| 캐시 | ❌ (상위 레이어 책임) | ✅ 메서드별 `cache.set` 60s~24h |

> **핵심 위험**: Market Movers 경로는 retry가 전혀 없어 FMP 순간 장애(타임아웃 1회)에도 즉시 `FMPAPIError`. 캐시 TTL(5분) 만료 시점에 장애가 겹치면 그대로 노출. 두 클라이언트의 에러 시맨틱이 달라 상위 호출처가 일관된 처리를 하기 어렵다.

### 402(Premium) 처리 — 부분적

- **명시 처리**: `provider.py`의 재무제표 3종(`get_balance_sheet`/`get_income_statement`/`get_cash_flow`) → `PREMIUM_ONLY` error_response. `thesis/tasks/eod_pipeline._fetch_fmp_value` → `None`.
- **미처리(약 20곳)**: `search_symbols`, `get_quote`, `get_company_profile` 등은 402가 raw 전파/`FMPClientError`로 떨어짐. CLAUDE.md 버그 #23(`.` 포함 심볼 배치 제외)은 일부 경로에만 적용.

### 위험도 Top 5 (FMP)

| 순위 | 지점 | 근거(file:line) | 장애 시나리오 |
|---|---|---|---|
| 1 | `apps/market_pulse/fetchers/weight_source.market_cap_weights` | `weight_source.py:~75` `if not caps: raise RuntimeError` | 시총 0 확보 → RuntimeError, 호출처 미처리 → **concentration 대시보드 전체 다운** |
| 2 | `services/serverless/services/market_breadth_service.calculate_daily_breadth` | `market_breadth_service.py:~74-76` try/except 부재 | gainers/losers 호출 실패 → 예외 전파 → 공포지수 태스크 fail |
| 3 | `packages/shared/stocks/services/sp500_service.sync_constituents` | `sp500_service.py:~43-46` CB open 시 `{}` 반환 | CB(threshold 3) open → 구성종목 동기화 skip → 후속 EOD가 빈 심볼셋으로 동작 |
| 4 | `packages/shared/stocks/services/sp500_eod_service.sync_eod_prices` | `sp500_eod_service.py:~102-109` 심볼별 swallow | 부분 종가만 저장 → 차트/지표 결측 (데이터 불일치) |
| 5 | `packages/shared/api_request/stock_service.update_stock_data` | `stock_service.py:~254-255` quote 실패 `logger.warning` swallow | profile은 갱신, real-time price/change 공란 → 포트폴리오 "—" 표시 |

### FMP 권장 조치
- **P0**: ① `weight_source`에 stale-cache fallback 또는 빈 비중 방어, ② `market_breadth_service`에 try/except + 캐시 fallback.
- **P1**: `serverless_client.py`에 retry + 402/429 분기 이식(또는 `client.py`로 통합), 미처리 20곳 402 표준화.
- **P2**: `market_breadth`/`sector_heatmap`에 CB 적용, EOD 심볼별 retry.

---

## Gemini 상세

> 모델은 전 호출 지점 `gemini-2.5-flash` 단일. 호출 29개(동기 22 / 비동기 7).

### 종합 지표

| 지표 | 수치 | 판정 |
|---|---|---|
| 에러 try/except 보유 | 28/29 | 🟢 양호 |
| `JSONDecodeError` 명시 처리 | 약 11/29 | 🟠 절반 미처리 |
| **timeout 설정** | **0/29** | 🔴 전무 (grep 교차검증: `http_options`/`request_options`/`timeout` 0건) |
| 429/quota 명시 감지 | 3/29 (CB 경유 포함) | 🔴 대부분 광범위 `except Exception` |
| 공유 클라이언트 사용 | 사실상 1곳(market_pulse) | 🔴 나머지 매 호출 `genai.Client()` 신규 생성 |
| Celery async 금지(#8) 위반 | 0건 | 🟢 준수 (`keyword_generator`는 `_call_llm_sync` 분리 확인) |

### 주요 패턴
- **모범(CB 통합)**: `apps/market_pulse/llm/client.py`(`get_circuit("gemini")`), `rag_analysis/llm_service.py`(CB + `asyncio.sleep(1/2/4s)`), `context_compressor.py`(CB acall), `thesis/services/thesis_builder.py`(수동 CB).
- **모범(구체적 에러 분류)**: `apps/portfolio/llm/client.py` — `_classify_gemini_error()`로 RateLimitError 분류 + fallback provider 전환 + 수동 2회 retry.
- **취약(retry 없음)**: 29곳 중 약 21곳은 try/except만 있고 재시도 없음 → 즉시 fallback 또는 raise.

### JSON 파싱 취약점 Top 5

| 순위 | 지점 | 문제 |
|---|---|---|
| 1 | `services/validation/services/llm_peer_filter.py:~86` | `json.loads(text)` — `JSONDecodeError` 미처리 (mime=application/json에도) → 필터 중단 |
| 2 | `packages/shared/stocks/services/korean_overview_service.py:~75` | `json.loads(response.text)` 미처리 + **raise**(fallback 없음) → S&P500 한글 요약 실패 |
| 3 | `services/serverless/services/thesis_builder.py:~118` | 파싱 실패 시 raise(fallback 없음) → 테제 생성 중단 |
| 4 | `thesis/services/thesis_builder.py:~486` & `serverless/.../thesis_builder.py:~490` | `re.search(r'\{.*\}')`만 사용 — ` ```json ` 마크다운 펜스 미제거 → 파싱 실패율↑ |
| 5 | 전 프로젝트 | **timeout 미설정** — 느린 응답/장기 생성 시 무한 대기 |

> 모범 비교: `rag_analysis/entity_extractor.py`는 `_clean_json_response()`로 펜스 제거 + `JSONDecodeError` 명시 처리. 이 패턴을 표준화해 위 4번을 해소 가능.

### Gemini 권장 조치
- **P0**: JSON 파싱 3곳(`llm_peer_filter`, `korean_overview_service`, `serverless thesis_builder`)에 `JSONDecodeError` catch + fallback. 펜스 제거 유틸(`_clean_json_response`) 공용화.
- **P1**: `genai.Client` 호출에 timeout 부여(신 SDK `http_options`/타임아웃), 공유 클라이언트 풀(`packages/shared/llm/`) 도입으로 분산 생성 27곳 통합.
- **P2**: CB 미적용 21곳을 공유 CB로 흡수, 429 감지 표준화.

---

## 기타 의존성

| 의존성 | 영향도 | 호출 지점(file) | 근거 / 복구 특성 |
|---|---|---|---|
| **FRED** | 🟢 부분 | `apps/market_pulse/services/macro_service.py`, `packages/shared/api_request/fred_client.py` | retry 3회(500/502/503/504 backoff) + Redis 캐시(60s~24h) + 기본값(F&G=50). 매크로 섹션만 영향, 앱 생존. |
| **Neo4j** | 🟢 부분 | `rag_analysis/services/neo4j_driver.py`(lazy singleton), `neo4j_service.py`, `apps/chain_sight/services/neo4j_sync.py` | 연결 실패 → `driver=None` → 빈 결과(HTTP 200, `_meta.source=fallback`). **dirty flag** 패턴으로 복구 후 자동 재동기화(Celery 2회 retry). 그래프 기능만 비활성. |
| **SEC EDGAR** | 🔴 **치명** | `services/sec_pipeline/collector.py` | User-Agent 헤더 + `time.sleep(0.12)`(10req/s) + timeout(15~60s)는 준수하나, Submissions/HTML 실패를 **`raise`로 호출자 전파**하고 자체 retry/fallback 없음. caller 미처리 시 10-K 수집 태스크 중단(기존 DB는 보존). edgartools fallback은 추출 단계만 해당. |
| **Redis** | 🟠 부분 | `config/settings.py:491`(broker `/0`), `:507-512`(`RedisCache` `/1`), `:518-523`(channels) | **`IGNORE_EXCEPTIONS` 설정 없음**(grep 0건) → 캐시 장애 graceful 여부는 **각 호출처 try/except에 전적으로 의존**. `cache.py`류는 try/except 보유(None 반환), `macro_service.py`의 직접 `cache.get()`은 미감싸 → Redis down 시 **500 위험**. Celery broker down은 자동 재연결(앱 생존, 신규 큐잉만 중단). |

### 기타 의존성 권장 조치
- **SEC EDGAR(P1)**: `collector` 내부에 transient(timeout/5xx) retry + backoff 추가, 또는 호출 태스크(`sec_pipeline.tasks`)의 Celery retry 정책 명문화.
- **Redis(P1)**: `RedisCache` 옵션에 `IGNORE_EXCEPTIONS: True`(django-redis) 도입 검토 → 캐시 장애가 비즈니스 로직 500으로 번지지 않게. 단, 적용 전 캐시-as-source-of-truth 경로(seed snapshot 등) 부작용 확인 필요.
- **Neo4j/FRED**: 현 패턴 양호. 모니터링(연결 상태, dirty 큐 적체)만 보강.

---

## Circuit Breaker 후보

### 현황: 인프라는 있으나 적용 불균형

- **공유 구현**: `packages/shared/api_request/circuit_breaker.py` (`get_circuit`, `CircuitBreakerError`).
- **중복 구현**: `services/news/services/circuit_breaker.py` — 별도 CB가 따로 존재(**drift 위험**, 하네스 규약상 단일 출처 위배 소지).
- **이미 채택**: `sp500_service`, `sp500_eod_service`, `data_sync`(FMP movers), `thesis_builder`, `rag_analysis/llm_service`·`context_compressor`, `neo4j_chain_sight_service`, `market_pulse` Gemini.

### 신규 도입 우선순위 (장애 시 전체 영향 + 현재 무방비)

| 우선 | 대상 호출 지점 | 사유 | 기대 효과 |
|---|---|---|---|
| **CB-1** | `market_breadth_service` (FMP movers) | try/except 자체가 없어 매 실패가 태스크 fail. movers는 `data_sync`와 동일 소스 | 연쇄 실패 차단 + 마지막 캐시 노출 |
| **CB-2** | `weight_source.market_cap_weights` (FMP quote ×500) | 500콜 중 임계 실패 시 RuntimeError로 대시보드 다운. 호출량 최대 | open 시 stale 비중 반환으로 대시보드 생존 |
| **CB-3** | `serverless_client.py` (Market Movers httpx) | retry조차 없는 클라이언트 — CB로 빠른 차단 + 캐시 유지 | 순간 장애 흡수 |
| **CB-4** | Gemini 분산 호출 21곳 (CB 미적용) | 특히 `llm_peer_filter`/`korean_overview`/`news_deep_analyzer` 등 동기 호출 | 429 폭주 시 공용 CB로 일괄 차단 |
| **CB-5** | `sec_pipeline.collector` (SEC EDGAR) | 유일한 Critical 의존성, retry/CB 모두 부재 | 10-K 수집 연쇄 실패 격리 |

### CB 거버넌스 권고
1. **단일 출처 통합**: `services/news/services/circuit_breaker.py`를 `packages/shared/api_request/circuit_breaker.py`로 흡수해 중복 제거(하네스 §10 drift 방지 규약).
2. **외부 의존성별 네이밍 표준화**: `get_circuit("fmp")`, `get_circuit("fmp_movers")`, `get_circuit("gemini")`, `get_circuit("sec")`, `get_circuit("neo4j")` 등 키 규약 정립 → 모니터링 일원화.
3. **CB + stale-cache 조합 원칙**: CB open 상태에서 빈 결과 대신 **마지막 성공 캐시**를 반환하도록 묶으면, 🔴 호출 지점들을 🟢로 강등 가능.

---

## 부록: 감사 커버리지 및 한계

- **직접 정독(고신뢰)**: `providers/fmp/client.py`, `providers/fmp/serverless_client.py`, `config/settings.py`(Redis/Celery), CB/Redis/timeout grep.
- **Explore 에이전트 보고(중신뢰, 라인 ±오차)**: 나머지 FMP 서비스 레이어 33지점, Gemini 29지점, FRED/Neo4j/SEC 호출부.
- **미수행**: 런타임 동작 검증(실제 장애 주입 테스트), 프런트엔드의 에러 표시 UX, Celery 재시도 실측. 본 보고서는 정적 코드 감사이며 동적 검증은 별도 필요.
- **사전 파악 grep 결과**: FMP 관련 파일 약 38개, Gemini 관련 파일 약 45개(테스트 포함) 식별 → 비테스트 운영 코드 중심으로 감사.
