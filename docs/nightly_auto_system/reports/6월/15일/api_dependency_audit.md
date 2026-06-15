# 외부 API 의존성 감사 보고서

> **작성일**: 2026-06-15
> **범위**: 읽기 전용 감사 (코드 수정 없음)
> **대상**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis 의존성의 장애 대응 패턴
> **방법**: 병렬 코드 탐색(3개 에이전트) + 핵심 주장 직접 검증(grep/Read)

---

## 0. 요약 (Executive Summary)

| 항목 | 결과 |
|------|------|
| 조사 파일 수 | FMP 40개 + Gemini 64개 + 기타(FRED/Neo4j/SEC/Redis) |
| Circuit Breaker 도입 | ✅ `packages/shared/api_request/circuit_breaker.py` (threshold=5, recovery=60s) 존재. FMP 4개 + Neo4j 1개 + RAG/briefing LLM 3개에 적용 |
| 가장 큰 단일 장애점(SPOF) | 🔴 **Redis** — Celery broker 겸 캐시 겸 Circuit Breaker 상태 저장소. 다운 시 전체 배치 파이프라인 정지 |
| FMP 장애 대응 | 🟡 클라이언트 계층은 retry+CB 양호. 일일 EOD 가격 동기화는 CB open 시 **데이터 gap** 발생(수동 재실행 필요) |
| Gemini 장애 대응 | 🔴 64개 호출 중 **429(rate limit) 처리는 RAG·briefing 일부(약 3곳)뿐**. 공통 래퍼 부재로 30+ 곳이 직접 `genai.Client` 초기화 |

### ⚠️ 검증으로 교정된 사항 (중요)

초기 탐색 에이전트는 `chain_sight_service`, `enhanced_screener_service`, `sector_heatmap_service`, `weight_source`를 "try/except 없음 → 장애 시 전체 중단/500 에러"로 보고했으나, **직접 코드 확인 결과 대부분 graceful degradation이 구현되어 있어 이 주장은 부정확**했다. 본 보고서는 검증된 사실 기준으로 작성한다. (상세: §FMP 4.1)

---

## 1. 의존성 매트릭스

서비스(소비자)별 외부 API × 장애 대응 수단. (✅ 있음 / 🟡 부분 / ❌ 없음)

| 서비스 / 호출 지점 | 외부 API | try/except | retry | timeout | Circuit Breaker | fallback / graceful degradation |
|---|---|---|---|---|---|---|
| `fmp/client.py::_make_request` | FMP | ✅ | ✅ 3회·지수백오프 | ✅ 30s | — | 402/401/403/429 즉시 raise, 그 외 retry |
| `fmp/provider.py` (공개 메서드) | FMP | ✅ | CB 위임 | 30s | — | `ProviderResponse.error_response()` |
| `fmp/serverless_client.py` | FMP | ✅ | ❌ | ✅ 30s | — | 캐시 우선(5분~24h), 예외는 raise |
| `fmp/market_pulse_client.py::get_quote` | FMP | ✅ | ❌ | ✅ 30s | — | **예외 catch 후 None 반환**(절대 raise 안 함) |
| `stocks/tasks.py::sync_sp500_eod_prices` | FMP | ✅ | ✅ Celery 3회 | 30s | ✅ | 개별 심볼 skip, CB open 시 **gap** |
| `sp500_eod_service.py` | FMP | ✅ | CB | 30s | ✅ `fmp_sp500_eod` | 개별 skip + error 누적 |
| `sp500_service.py::sync_constituents` | FMP | ✅ | CB | 30s | ✅ `fmp_sp500_constituents` | CB open → `{0,0,0,0}` |
| `data_sync.py` (Market Movers) | FMP | ✅ | CB | — | ✅ `fmp_market_movers` | CB open → empty, 계속 |
| `news_aggregator.py` | FMP/Marketaux | ✅ | CB | 30s | ✅ `fmp_news`/`marketaux` | CB open → stats[error], 계속 |
| `chain_sight_service.py` | FMP | ✅ | ❌ | 30s | — | FMPAPIError catch → continue/빈 결과 |
| `enhanced_screener_service.py::screen_enhanced` | FMP | ✅ | ❌ | 30s | — | FMPAPIError catch → `{results:[],error}` |
| `sector_heatmap_service.py` | FMP | ✅ | ❌ | 30s | — | 개별 섹터 continue / **최상위 FMPAPIError는 raise** |
| `weight_source.py::market_cap_weights` | FMP | 🟡 (get_quote 내부) | ❌ | 30s | — | 개별 None→missing→continue, 전종목 실패 시 RuntimeError |
| `keyword_data_collector.py` | FMP | ✅ | ❌ | 🟡 10s | — | 부분 실패 허용, failed 누적 |
| `news/providers/fmp.py` | FMP | ✅ | ❌ | 30s | — | 예외 시 `[]` 반환 |
| `macro_service.py` | FMP/FRED | ✅ | ❌ | 30s | — | 기본값/캐시/`{error}` |
| `thesis/tasks/eod_pipeline.py` | FMP/FRED | ✅ | ❌ | 30s | — | `None`/`(None,None)` → 지표 누락, 계속 |
| `rag_analysis/llm_service.py::generate_stream` | Gemini | ✅ | ✅ 3회·지수백오프 | 🟡 감지만 | ✅ | 429 알림, 에러 yield |
| `rag_analysis/context_compressor.py` | Gemini | ✅ | ❌ | ❌ | ✅ | `fallback_compress()` |
| `rag_analysis/entity_extractor.py` | Gemini | ✅ | ❌ | ❌ | ❌ | `fallback_extraction()` |
| `market_pulse/briefing/client.py` | Gemini | ✅ | ❌ | ❌ | ✅ | 예외 전파 |
| `serverless/keyword_service.py` | Gemini | ✅ | ✅ 2회 | ❌ | ❌ | `FALLBACK_KEYWORDS` |
| `serverless/llm_relation_extractor.py` | Gemini | ✅ | ❌ | ❌ | ❌ | 캐시 활용 + `relations=[]` |
| `news/news_deep_analyzer.py` | Gemini | ✅ | ❌(4s delay) | ❌ | ❌ | `None` 반환, error 증가 |
| `thesis/thesis_builder.py`·`prompt_builder.py` | Gemini | ✅ | ❌ | ❌ | 🟡(builder만) | `None` → 룰 fallback |
| `sec_pipeline/extractor.py` | Gemini | ✅ | ❌ | ❌ | ❌ | `{relations:[]}` / `{}`, 일부 raise |
| `korean_overview_service.py` | Gemini | ✅ | ❌ | ❌ | ❌ | **예외 전파(배치 중단 위험)** |
| `fred_client.py` | FRED | ✅ | ✅ 3회·지수백오프 | ✅ 30s | — | 401/403 raise, 5xx retry |
| `neo4j_chain_sight_service.py` | Neo4j | ✅ | — | ✅ 2000ms | ✅ `neo4j_chain_sight` | 빈 관계 반환, CB open 시 무시 |
| `sec_edgar_client.py` | SEC EDGAR | ✅ | 🟡 429 시 1s 대기 | ✅ 120s | — | edgartools fallback |
| Django cache / Celery broker | Redis | 🟡 | — | — | — | cache miss 시 재계산. **broker 다운 시 전체 정지** |

---

## 2. FMP 상세

### 2.1 클라이언트 계층 (양호)

- **`fmp/client.py::_make_request`** (`packages/shared/api_request/providers/fmp/client.py:85-172`)
  - retry `max_retries=3`, 지수 백오프 `(attempt+1)*2`초, timeout 30s.
  - **즉시 raise(재시도 안 함)**: `FMPPremiumError`(402), `FMPAuthError`(401/403), `FMPRateLimitError`(429) — `:156`.
  - **재시도**: `requests.RequestException`, 일반 `FMPClientError` — `:158`.
- **`rate_limiter.py`** (`packages/shared/api_request/rate_limiter.py:47-57`)
  - FMP Starter 300/min을 0.8 안전마진 적용 **240/min, 8000/day**, request delay 0.25s.
  - Redis 원자적 증가, 실패 시 Django 캐시 fallback (`:129-141`).
- **`market_pulse_client.py::get_quote`** (`:128-144`) — **모든 예외를 catch하고 `None` 반환**. raise하지 않음. (이 동작이 `weight_source` 안전성의 근거)
- **`serverless_client.py::get_sp500_constituents`** (`:325-385`) — FMP 프리미엄 엔드포인트를 **datahub.io CSV로 fallback** (`:356`), 성공 시 24h 캐싱.

### 2.2 FMPPremiumError(402) 처리

- `client.py:156`에서 402는 즉시 raise(재시도 안 함). `provider.py:233-239`는 이를 catch해 에러 응답으로 변환.
- common-bugs.md #23(프리미엄 심볼 402 → `.` 포함 심볼 배치 제외)과 정합. **402 핸들링은 전반적으로 양호.**

### 2.3 Rate Limit 처리

- 클라이언트별 안전마진이 **불일치**: `rate_limiter.py`는 240/min, `client.py`는 0.2s 간격(=300/min). 동시 사용 시 실제 호출률이 300을 초과할 여지 → 점검 권장.

### 2.4 소비자 계층

- **EOD 일일 가격(`sp500_eod_service.py`)**: 개별 심볼 실패는 skip하고 계속(graceful)하나, CB가 open되면 해당 날짜 동기화가 **미완료 상태로 남고 error_symbols만 누적** → 수동 재실행 필요. **데이터 gap이 가장 큰 실질 리스크.**
- **`weight_source.py::market_cap_weights`** (`apps/market_pulse/fetchers/weight_source.py:67-75`): S&P500 ~500종목을 종목당 1 quote로 순회. 개별 try/except는 없지만 `get_quote`가 None을 반환하므로 개별 실패는 `missing`으로 처리되고 continue. **전 종목 실패 시에만 `RuntimeError`(`:75`)**. → FMP 완전 다운 시나리오에서만 상위 전파.
- **`sector_heatmap_service.py`** (`:93-135`): 개별 섹터는 `except Exception → continue`(`:101-103`)로 보호. 다만 루프 바깥에서 `FMPAPIError`가 나면 `raise`(`:130-132`) — 실질 발생 가능성은 낮지만 유일한 비graceful 경로.

### 2.5 장애 시 영향이 큰 FMP 호출 지점 TOP 5

| 순위 | 지점 | 영향 | 현 상태 |
|---|---|---|---|
| 1 | `sync_sp500_eod_prices` / `sp500_eod_service.py` | S&P500 일일 가격 미동기화 → 수익률·기술지표 전면 오류 | CB로 폭주는 막으나 **데이터 gap + 수동 재실행** |
| 2 | `sync_sp500_constituents` / `sp500_service.py` | 종목 유니버스 미갱신 → 신규/제외 종목 누락 | CB open 시 `{0,0,0,0}` 반환(무변경) |
| 3 | `data_sync.py` Market Movers | 메인 대시보드 Movers 카드 공백 | CB → empty, 계속 (graceful) |
| 4 | `weight_source.py` (Concentration) | Market Pulse 섹터 집중도 지표 누락 | FMP 완전 다운 시 RuntimeError, 부분 실패는 graceful |
| 5 | `sector_heatmap_service.py` | 섹터 히트맵 미계산 | 개별 섹터 graceful, 최상위 FMPAPIError만 raise |

---

## 3. Gemini 상세

### 3.1 공통 래퍼 부재 (구조적 문제)

- 30개 이상 파일이 각자 `from google import genai; client = genai.Client(api_key=...)`를 직접 초기화. 중앙 래퍼가 없어 **재시도·timeout·rate limit 정책이 호출지점마다 제각각**.
- 유일한 통합 래퍼는 `apps/portfolio/llm/client.py`(Gemini/Anthropic 통합, 비용 가드·fallback provider)지만 **Portfolio 앱 전용**.

### 3.2 429 (Rate Limit) 처리 — 가장 취약

- Gemini Free 15 RPM / 1500 RPD 하드 제한.
- **429를 실제로 감지·백오프하는 곳은 RAG `llm_service.py`·`adaptive_llm_service.py`와 portfolio `client.py` 정도(약 3곳)**. 나머지 대다수는 429 미처리.
- 배치성 호출(`news_deep_analyzer.py`, `relationship_keyword_enricher.py`)은 `time.sleep(4초)`로 RPM을 우회하지만, 동시 다발 수집 시 순간 RPM을 보장하지 못함.

### 3.3 JSON 파싱 방어 — 비교적 양호

- 다수 호출이 `json.loads` try/except + 마크다운 코드펜스(```` ``` ````) 제거 패턴 보유.
- 약점: 스트리밍 응답(`llm_service.py`)과 구조화 스키마 의존(`briefing/client.py`)은 별도 스키마 검증 없음.

### 3.4 Timeout

- 거의 전 지점에서 명시적 timeout 미설정(SDK 기본값 의존). `llm_service.py`는 rate-limit 감지만 함.

### 3.5 동기 API 사용 (CLAUDE.md 규칙 준수)

- Celery 경로(`thesis/tasks/summary.py`, `news_deep_analyzer`, `keyword_service` 등)는 동기 `genai.Client`/`generate_content` 사용 — common-bugs #8 규칙 준수 확인.

### 3.6 예외 시 배치 중단 위험

- `korean_overview_service.py:36`, `sec_pipeline/extractor.py:152`는 예외를 **상위로 raise** → 배치 루프에서 1건 실패가 나머지 처리를 막을 수 있음.

### 3.7 장애 시 영향이 큰 Gemini 호출 지점 TOP 5

| 순위 | 지점 | 영향 | 현 상태 |
|---|---|---|---|
| 1 | `rag_analysis/llm_service.py::generate_stream` | RAG 투자분석 응답 전면 차단 | CB+429+3회 retry (상대적 양호), timeout 미설정 |
| 2 | `market_pulse/briefing/client.py` | 일일 브리핑 미생성 → FE 비노출 | CB만, 429·retry 없음 |
| 3 | `serverless/llm_relation_extractor.py` | 뉴스 관계 추출 대량 실패 → 그래프 결손 | 캐시·JSON방어 O, 429·retry ❌ |
| 4 | `news/news_deep_analyzer.py` | 심층분석 누락 → 가설 자동제안 품질 저하 | 4s delay만, 429·retry ❌ |
| 5 | `thesis/thesis_builder.py`·`prompt_builder.py` | 가설 자동 구조화 실패 → 사용자 UX 즉시 영향 | 룰 fallback O, 429·CB·retry ❌ |

---

## 4. 기타 의존성

### 4.1 FRED API — 양호

- `fred_client.py:98-155` retry 3회(2/4/6s), timeout 30s, 401/403 raise·5xx retry, rate_limiter 적용(120/min).
- `macro_service.py:63-68`는 실패 시 VIX=20 등 **하드코딩 기본값** 반환 → "마지막 알려진 값/DB 최근값" 사용으로 개선 여지.

### 4.2 Neo4j — 양호 (graceful degradation 모범)

- `neo4j_driver.py` lazy singleton, 초기화 실패 시 `None` 반환.
- `neo4j_chain_sight_service.py:113-143` Circuit Breaker(`neo4j_chain_sight`, threshold=5, recovery=60s) + query timeout 2000ms.
- 다운 시 그래프 조회는 빈 배열 반환 → **기능 저하이지 전체 중단 아님**.
- 약점: 초기화 실패 후 **주기적 재연결 시도 없음**(`reset_connection()` 수동) → 일시 장애 후 자동 회복 안 됨.

### 4.3 SEC EDGAR — 양호

- `sec_edgar_client.py` rate limit 10 req/s(100ms), User-Agent 필수 헤더 설정, 429 시 1s 대기 후 재시도, 다운로드 timeout 120s.
- `collector.py`는 regex 3단계 추출 실패 시 **edgartools fallback**, 그래도 실패면 "partial" 상태로 진행.
- 영향 범위가 Supply Chain 배치에 국한되어 시스템 전체 리스크 낮음.

### 4.4 Redis — 🔴 최대 단일 장애점(SPOF)

- 1개 Redis가 **Celery broker(DB0) + Django 캐시(DB1) + Channel Layer + Circuit Breaker 상태 저장소**를 겸한다(`config/settings.py:491-523`, `circuit_breaker.py:64-76`).
- **다운 시 연쇄 영향**:
  - Celery broker 불가 → EOD 파이프라인·뉴스 수집·매크로 갱신·Neo4j 동기화·Chain Sight 등 **모든 스케줄 작업 정지**.
  - Circuit Breaker 상태 저장 불가 → **FMP/Neo4j 장애 감지 자체가 무력화**(다중 장애 시 graceful degradation도 깨짐).
  - 캐시 miss 강제 → FMP/FRED 분당 할당량 급증 + LLM 호출 비용 폭증.
- cache 사용처는 try/except로 로깅 후 `None` 반환(재계산)하지만, **broker 경로는 fallback 없음**.

---

## 5. Circuit Breaker 후보

### 5.1 이미 적용됨 (현황)

`fmp_sp500_constituents`, `fmp_sp500_eod`, `fmp_market_movers`, `fmp_news`/`marketaux`, `neo4j_chain_sight`, RAG `llm_service`/`context_compressor`, `briefing/client`, `thesis_builder`.

### 5.2 신규 도입 권장 (우선순위)

| 우선순위 | 후보 | 근거 |
|---|---|---|
| **P0** | **Gemini 전역 래퍼 + CB** | 64개 호출 중 CB·429 처리가 3곳뿐. 공통 `GeminiClient` 래퍼에 CB·429 백오프·timeout을 일괄 탑재해 전 호출에 적용 |
| **P0** | **Redis 이중화/감시** | SPOF 해소가 최우선. broker·cache·CB-store 분리 또는 Sentinel/대체 broker(failover) 검토. 최소한 broker 다운 알림 |
| P1 | `weight_source` / `chain_sight_service` FMP 경로 CB | 현재 CB 미적용. FMP 부분 장애 시 호출 폭주 방지 |
| P1 | `llm_relation_extractor` / `news_deep_analyzer` CB+429 | 배치 LLM 호출 다수 실패 시 조기 차단 |
| P2 | Neo4j 주기적 재연결 | CB는 있으나 초기화 실패 후 자동 회복 경로 부재 |
| P2 | `korean_overview_service` / `sec_pipeline/extractor` 배치 resilience | 1건 raise가 배치 전체를 막지 않도록 try/except 누적 패턴으로 통일 |

### 5.3 공통 개선 권장

1. **(P0)** Gemini 중앙 래퍼로 429 백오프·timeout·CB 일괄화 — 현 최대 취약점.
2. **(P0)** Redis SPOF 완화 — broker/cache/CB-store 역할 분리 또는 failover.
3. **(P1)** EOD 가격 동기화 부분 실패 **재시도 큐** — CB open 시 data gap 자동 보정.
4. **(P1)** FMP rate limit 마진 통일(`rate_limiter` 240/min vs `client` 300/min).
5. **(P2)** FRED 기본값 대신 last-known-good(DB 최근값) 사용.
6. **(P2)** LLM 호출 timeout 전역 명시(10~30s).

---

## 부록: 검증 메모

본 보고서 작성 시 초기 탐색 에이전트의 "try/except 없음" 주장을 직접 코드로 재확인하여 다음을 교정함:

- `chain_sight_service.py:199-209` — FMP 호출이 try/except로 감싸짐(FMPAPIError catch 후 continue). **graceful 확인.**
- `enhanced_screener_service.py:136-197` — `screen_enhanced`가 FMPAPIError catch 후 `{results:[], error}` 반환. **500 에러 아님, graceful 확인.**
- `sector_heatmap_service.py:93-135` — 개별 섹터 `except Exception → continue`. 최상위 FMPAPIError만 raise. **대체로 graceful.**
- `weight_source.py:67-75` + `market_pulse_client.py:128-144` — `get_quote`가 예외를 catch하고 None 반환(절대 raise 안 함). 개별 심볼 실패는 graceful, 전 종목 실패 시에만 RuntimeError. **"첫 실패 시 전체 중단" 주장은 오류.**
- `circuit_breaker.py` 존재 및 적용처 확인(threshold=5, recovery=60s).
