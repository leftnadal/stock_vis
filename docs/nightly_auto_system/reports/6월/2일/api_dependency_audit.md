# 외부 API 의존성 감사 보고서

> **작성일**: 2026-06-02
> **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis 장애 대응 패턴
> **성격**: 읽기 전용 감사 (코드 수정 없음)
> **방법**: 핵심 클라이언트(FMPClient, LLMServiceLite, CircuitBreaker)는 직접 정독, 약 60개 소비처는 병렬 탐색으로 조사 후 핵심 주장 재검증

---

## 요약 (Executive Summary)

| 항목 | 상태 |
|------|------|
| **공통 Circuit Breaker 인프라** | ✅ 존재 (`packages/shared/api_request/circuit_breaker.py`, Redis 기반, tenacity retry 내장) |
| **CB 실제 적용 범위** | ⚠️ 부분적 — 약 10개 지점만 적용, 50+ 소비처 대부분 미적용 |
| **FMP 코어 클라이언트** | ✅ 견고 (402/401/429/`Error Message` 분기 + exponential backoff retry) |
| **Gemini 코어(RAG)** | ✅ 견고 (CB + 429 재시도 + 신뢰경계 escape) |
| **Gemini 소비처 다수** | 🔴 JSON 파싱·429·timeout 처리 일관성 부족 |
| **Redis** | 🔴 **최대 SPOF** — Django 내장 RedisCache는 `IGNORE_EXCEPTIONS` 미지원 → 장애 시 예외 전파, 게다가 CB 상태/Channels/캐시가 단일 인스턴스(`redis://127.0.0.1:6379`)에 집중 |
| **Neo4j** | 🟠 graceful degradation 있음, 단 첫 연결 실패 후 영구 None (자동 재연결 없음) |
| **SEC EDGAR** | 🟠 429 시 재귀 재시도 루프 + fallback 없음 |
| **FRED** | 🟡 retry 있음, fallback은 하드코딩 기본값(VIX=20 등) silent |

**핵심 결론**: 인프라(CircuitBreaker)는 이미 잘 만들어져 있으나 **적용이 산발적**이다. 가장 큰 단일 위험은 외부 API가 아니라 **Redis 자체**다 — CB 상태·캐시·WebSocket 레이어가 모두 한 인스턴스에 묶여 있어 Redis가 죽으면 보호 장치(CB)까지 동시에 무력화된다.

---

## 의존성 매트릭스

서비스/기능별 외부 API 의존성과 보호 장치 유무.

| 기능 영역 | 주 의존성 | 호출 추상화 | 에러핸들링 | Retry | Fallback | Circuit Breaker | 장애 시 영향 |
|-----------|----------|------------|-----------|-------|----------|----------------|-------------|
| 시세/재무 동기화 (`stocks/tasks.py`) | FMP | StockService→Factory | ✅ generic | Celery max_retries=3 | 이전 DB 상태 유지 | ❌ | 종목 데이터 갱신 지연 |
| S&P500 구성종목 (`sp500_service.py`) | FMP | FMPClient | ✅ | CB retry | 빈 dict | ✅ `fmp_sp500_constituents` | EOD 파이프라인 시드 결손 |
| S&P500 EOD (`sp500_eod_service.py`) | FMP | FMPClient | ✅ FMPAPIError | CB retry, max_retries=3 | 최소정보 Stock 생성 | ✅ `fmp_sp500_eod`(10,120s) | EOD 대시보드 부분 결손 |
| Market Movers (`data_sync.py`) | FMP | FMPClient | ✅ FMPAPIError | CB retry | 빈 리스트/dict | ✅ `fmp_market_movers`(5,120s) | Movers 위젯 빈 데이터 |
| ETF 가중치 (`fmp_weights.py`) | FMP | requests 직접 | ⚠️ raise_for_status만 | CB retry | ❌ | ✅ `fmp_etf` | Market Pulse 가중치 실패 |
| 뉴스 수집 (`news_aggregator.py`) | FMP/Finnhub/Marketaux | provider별 | ✅ generic | CB retry | 다음 provider→빈 리스트 | ✅ `fmp_news`,`marketaux` | 뉴스 피드 부분 기능 |
| 스크리너 필터 (`filter_engine.py`) | FMP | FMPClient | 🔴 **try/except 없음** | ❌ | ❌ | ❌ | **스크리너 전체 다운** |
| Enhanced 스크리너 (`enhanced_screener_service.py`) | FMP (2단계) | FMPClient | ⚠️ generic | ❌ | 부분결과만 | ❌ | 필터 결과 불완전 |
| Market Breadth (`market_breadth_service.py`) | FMP | FMPClient | ⚠️ FMPAPIError | ❌ | ❌ | ❌ | Breadth 지표 결손 |
| 종목검색 (`views_search.py`) | FMP | StockService | ✅ generic | ❌ | 캐시 폴백(5~10분) | ❌ | 검색 일시 실패 |
| RAG 분석 (`llm_service.py`) | Gemini | genai aio | ✅ | 429 재시도+CB | 에러 이벤트 yield | ✅ `gemini_rag`(5,60s) | RAG 응답 차단 안내 |
| 테제 빌더 (`thesis_builder.py`) | Gemini | genai 동기 | ✅ | CB | fallback_parse | ✅ `gemini_thesis`(5,120s) | 가설 제안 기본값 |
| 컨텍스트 압축 (`context_compressor.py`) | Gemini | genai aio | ✅ CBError | CB | 원문 유지 | ✅ (2개 circuit) | 압축 생략 |
| 시장 브리핑 (`briefing/client.py`) | Gemini | genai 동기 | ✅ generic | CB | — | ✅ `gemini` | 브리핑 결손 |
| 키워드 생성 (`keyword_generator_v2.py`) | Gemini | genai aio | ⚠️ generic | ❌ | 기본 키워드 | 🔴 **미적용**(서브조사 오인) | 키워드 품질 저하 |
| 한국어 개요 (`korean_overview_service.py`) | Gemini | genai 동기 | 🔴 약함 | ❌ | ❌ | ❌ | overview 500 위험 |
| LLM 관계추출 (`llm_relation_extractor.py`) | Gemini | genai 동기 | ⚠️ generic | ❌ | 캐시만 | ❌ | Chain Sight 관계 결손 |
| 뉴스 심층분석 (`news_deep_analyzer.py`) | Gemini | genai 동기 | ⚠️ generic | ❌ | ❌ | ❌ | 분석 결손 |
| Peer 필터 (`llm_peer_filter.py`) | Gemini | genai 동기 | ⚠️ generic | ❌ | error dict | ❌ | 검증 필터 결손 |
| SEC 인텔리전스 (`sec_pipeline/`) | Gemini + SEC EDGAR | genai 동기 / requests | ✅ JSON+fallback | SEC 429 재귀 | dict 기본값 | ❌ | 공급망 추출 실패 |
| 거시경제 (`macro_service.py`) | FRED + FMP | FREDClient | ✅ | FRED 3회 backoff | **하드코딩 기본값** | ❌ | 지표 silent stale |
| Chain Sight 그래프 | Neo4j | neo4j driver | ✅ is_available | CB retry | PostgreSQL/빈 | ✅ (2개 circuit) | 그래프 빈 데이터 |
| 캐시/CB상태/WebSocket | Redis | django cache / channels | ⚠️ 부분 try/except | ❌ | LocMem(rate limiter만) | — | **전역 cascading** |

---

## FMP 상세

### 코어 클라이언트 — `packages/shared/api_request/providers/fmp/client.py` ✅ 견고

가장 잘 작성된 부분. `_make_request()` (`client.py:85-172`)가 다음을 모두 처리:

- **HTTP 상태 분기** (`client.py:129-143`): 401→`FMPAuthError`, **402→`FMPPremiumError`**, 403→`FMPAuthError`, 429→`FMPRateLimitError`, 그 외 비200→`raise_for_status()`
- **FMP JSON 에러 응답** (`client.py:148-152`): `"Error Message"` 키 감지, `"Invalid API KEY"`→`FMPAuthError`
- **재시도 전략** (`client.py:156-170`): 재시도 불필요 에러(402/401/429)는 즉시 전파, 네트워크/일반 에러만 exponential backoff(2/4/6초)로 최대 3회
- **Rate limit**: 요청 간 `request_delay=0.2s` sleep(`client.py:107-110`) + 일일 한도 10,000 카운터(`client.py:113-115`)
- **timeout**: `requests.get(..., timeout=30)` 명시

> 단, 일일 카운터(`daily_calls`)와 `last_request_time`은 **프로세스 메모리 내 인스턴스 상태**다. Celery 워커가 여러 프로세스/노드로 뜨면 각자 카운터를 갖는다 → 분산 환경에서 300/min·10,000/day 보장이 깨질 수 있다. (정보용 — 현재 실측 장애 보고는 없음)

### Provider 계층 — `fmp/provider.py` ✅ 일관

각 메서드가 `FMPPremiumError`→`PREMIUM_ONLY` 에러응답, `FMPRateLimitError`→`RateLimitError` 전파, 그 외→`API_ERROR` 에러응답으로 일관 변환(`provider.py:233-246` 등). `ProviderResponse` 패턴으로 예외가 호출자까지 raw로 새지 않음.

### 취약 지점 (FMP 소비처)

병렬 조사 + 재검증 결과, **에러핸들링이 부실한 FMP 소비처 Top 5**:

| 순위 | 위치 | 문제 | 영향 |
|------|------|------|------|
| 🔴 1 | `services/serverless/services/filter_engine.py` | FMP 호출에 try/except·CB·fallback **전무** | 스크리너 필터 전체 다운 |
| 🔴 2 | `apps/market_pulse/fetchers/fmp_weights.py:30-48` | requests 직접, `raise_for_status()`만(파싱 ValueError 미처리). CB는 있으나 fallback 없음 | ETF 가중치 산출 실패 |
| 🔴 3 | `services/serverless/services/enhanced_screener_service.py` | 2단계 호출 중 실패 시 부분결과만, 캐시 없음 | 필터 결과 불일치 |
| 🟠 4 | `thesis/tasks/eod_pipeline.py:46-154` | 예외 catch 후 `None` 반환(silent), CB 미적용 | 지표 누락→스코어 불완전 |
| 🟠 5 | `services/serverless/services/market_breadth_service.py:72-95` | `FMPAPIError` 잡지만 fallback 없이 전파 | Breadth 지표 결손 |

> ⚠️ 일부 file:line은 병렬 서브에이전트 보고값으로, 실제 수정 착수 전 해당 라인 재확인 권장. `filter_engine.py`/`enhanced_screener_service.py`는 정확한 라인 미확정.

---

## Gemini 상세

### 코어(RAG) — `services/rag_analysis/services/llm_service.py` ✅ 모범 사례

`LLMServiceLite.generate_stream()` (`llm_service.py:132-276`)가 갖춘 것:

- **Circuit Breaker** (`llm_service.py:199-210`): `get_circuit("gemini_rag", failure_threshold=5, recovery_seconds=60, retry_attempts=1)` + `cb.acall(...)`. CB OPEN 시 사용자 친화 메시지 yield 후 중단(`llm_service.py:238-245`)
- **429/quota 재시도** (`llm_service.py:251-268`): 에러 문자열에 `rate`/`quota`/`429` 포함 시 `RETRY_DELAYS=[1,2,4]` 백오프 재시도
- **신뢰 경계 방어** (`llm_service.py:179-193`): context/question의 닫는 태그 escape — prompt injection 차단(보안감사 P0 #3)
- **thinking_budget=0** 설정으로 비용 통제

### Gemini 소비처 — 일관성 부족

CB가 적용된 Gemini 호출 지점(재검증 완료):
- `llm_service.py` → `gemini_rag`
- `thesis_builder.py:470` → `gemini_thesis`
- `context_compressor.py:133, 287` → 2개 circuit
- `briefing/client.py:72` → `gemini`

**CB 미적용** (서브에이전트가 적용으로 오인했으나 grep 재검증 결과 미적용): `keyword_generator_v2.py` — `get_circuit` 호출 없음.

#### 취약 지점 Top 5 (Gemini)

| 순위 | 패턴 | 영향 범위 | 대표 위치 |
|------|------|-----------|----------|
| 🔴 1 | **`json.loads()` 무방비** — 형식 깨지면 500 | 다수 소비처 | `korean_overview_service.py` (response.text 직접 파싱), `llm_relation_extractor.py` |
| 🔴 2 | **429 재시도 없음** — rate limit 시 즉시 실패 | RAG/thesis/portfolio 외 대부분 | `keyword_service.py`, `news_deep_analyzer.py`, `llm_peer_filter.py` |
| 🟠 3 | **timeout 미설정** — 응답 지연 시 무한 대기 가능 | 동기 호출 전반 | `korean_overview_service.py` 등 |
| 🟠 4 | **빈 응답 처리 불일치** — `if not response.text` 누락 | 약 15개 | `news_deep_analyzer.py` |
| 🟡 5 | **CB 미적용** — 장애 cascade | 동기 호출 다수 | `korean_overview_service.py`, `llm_relation_extractor.py`, `news_deep_analyzer.py` |

#### 모범 구현(참고): `apps/portfolio/llm/client.py`
429/timeout/auth 예외 분류(`client.py:61-94`) + 1회 재시도 + provider fallback(`client.py:180`). 다른 소비처가 따라야 할 패턴.

#### CLAUDE.md 버그 #8(Celery async LLM 호출 금지) 점검
- 동기 호출 지점들은 준수 ✅
- 단, `adaptive_llm_service.py`, `entity_extractor.py`, `context_compressor.py`는 `async def`/aio 기반 — **Celery task에서 직접 호출 시 위반 위험**. 현재 호출 경로가 async view/ASGI 한정인지 확인 필요(잠재 리스크로 기록).

---

## 기타 의존성

### FRED API 🟡
- **위치**: `packages/shared/api_request/fred_client.py:75-156`, `apps/market_pulse/services/macro_service.py`, `apps/market_pulse/tasks/macro.py`
- **retry**: transient(500/502/503/504) 3회 exponential backoff(2/4/6초), permanent(401/403/404) 즉시 raise
- **fallback**: ❌ 외부 storage 없음 → `macro_service.py:77-85`에서 **하드코딩 기본값(VIX=20, spread=1.0)** 반환. 호출은 성공처럼 보이는 **silent stale**
- **캐시**: `macro:*` (60s~7일 TTL). 캐시 미스 시 직접 호출 → thundering herd 가능
- **영향**: FRED 다운 → 모든 거시지표가 그럴듯한 기본값으로 대체되어 **오탐 위험**(장애가 안 보임)

### Neo4j 🟠
- **위치**: `services/rag_analysis/services/neo4j_driver.py:20-74`, `services/serverless/services/neo4j_chain_sight_service.py:108-515`
- **graceful degradation**: ✅ `is_available()` (`neo4j_chain_sight_service.py:113-125`)가 driver None 또는 CB OPEN 시 False → 모든 public 메서드가 빈 결과 반환. Neo4j 없어도 PostgreSQL로 기본 동작
- **CB**: 적용됨 (`neo4j_chain_sight_service.py:117, 133`)
- **약점**: `neo4j_driver.py` 초기화 실패 시 `_driver=None` 고정 → **자동 재연결 없음**. Neo4j가 늦게 복구돼도 앱 재시작 전까지 영구 None
- **영향**: 관련 종목/공급망/테마 매칭 빈 데이터. 복구에 앱 재시작 필요

### SEC EDGAR 🟠
- **위치**: `packages/shared/api_request/sec_edgar_client.py:132-182`, `services/sec_pipeline/collector.py:72-374`
- **rate limit**: 10 req/sec(0.1초 간격) 준수
- **429 처리**: 1초 sleep 후 **재귀 재시도** — 백오프·상한 없는 루프 → SEC 장기 throttle 시 long-tail latency
- **fallback**: ❌ 없음. `RequestException`→`SECEdgarError` raise, 소비처 미흡 처리
- **캐시**: 응답 캐시 없음(RawDocumentStore DB로 중복 다운로드만 방지)
- **영향**: 10-K 다운로드 실패 → 공급망 관계 추출 불가(그래프 부분 누락)

### Redis 🔴 (최대 단일 장애점)
- **설정**: `config/settings.py:500-505` — Django **내장** `django.core.cache.backends.redis.RedisCache`, `redis://127.0.0.1:6379/1`. `OPTIONS`에 `IGNORE_EXCEPTIONS` 없음(애초에 내장 백엔드는 미지원)
- **집중도**: 같은 Redis 인스턴스(6379)에 **① 캐시 ② Circuit Breaker 상태(`cb:*`) ③ Channels WebSocket 레이어(`settings.py:509-516`) ④ rate limiter**가 모두 의존
- **장애 처리 편차**:
  - RAG 캐시(`rag_analysis/services/cache.py`)·news CB는 try/except로 감싸 graceful ✅
  - 그러나 Django 내장 RedisCache는 연결 실패 시 **예외를 그대로 raise** → try/except 없는 `cache.get/set` 경로는 즉시 500
  - **치명적 역설**: CB 상태가 Redis에만 저장 → Redis 다운 시 모든 CB가 CLOSED로 리셋 → **보호 장치가 장애와 함께 사라짐** → 외부 API로 cascading
- **영향**: 캐시 미스 폭주(thundering herd) + CB 무력화 + WebSocket 끊김 동시 발생

---

## Circuit Breaker 후보 (장애 영향도 우선순위)

이미 `CircuitBreaker` 인프라가 존재하므로, **신규 개발이 아니라 적용 확대**가 과제다.

### 즉시 적용 권장 (P0 — 장애 시 전체 기능 다운)
1. **`filter_engine.py` (FMP 스크리너)** — try/except조차 없음. CB + 캐시 fallback 필수. 단일 호출 실패가 스크리너 전체를 죽임
2. **Redis 의존 구조 분리** — 코드 CB가 아니라 인프라 결정. (a) 캐시 백엔드를 `django-redis`로 교체해 `IGNORE_EXCEPTIONS=True` 활성화, (b) CB 상태를 캐시와 다른 Redis DB/인스턴스로 분리, (c) Sentinel/Cluster 검토. **CB 상태가 캐시와 운명을 같이하지 않게** 하는 것이 핵심

### 단기 (P1 — 부분 기능 손상)
3. **`korean_overview_service.py` (Gemini)** — JSON 파싱 무방비 + CB 없음. overview는 사용자 직접 노출 경로
4. **`market_breadth_service.py` / `enhanced_screener_service.py` (FMP)** — CB + 이전 값 캐시 재사용
5. **SEC EDGAR 429 재귀 루프** — CB 또는 `max_retries` 상한 + exponential backoff로 무한 루프 차단

### 정책 (P2 — 일관성)
6. **Gemini 동기 소비처 공통 래퍼** — `get_circuit("gemini_*")` + 429 백오프 + `json.loads` try/except + 빈 응답 가드를 묶은 헬퍼로 통일. 현재 `llm_service.py`/`portfolio/llm/client.py` 패턴을 표준으로 승격
7. **Neo4j 자동 재연결** — `is_available()`에서 driver None일 때 lazy `reset_connection()` 1회 시도

### CB 적용 현황 (재검증 완료)

| 보호됨 ✅ | circuit 이름 (threshold, recovery) |
|----------|-----------------------------------|
| `sp500_service.py` | `fmp_sp500_constituents` |
| `sp500_eod_service.py` | `fmp_sp500_eod` (10, 120s) |
| `data_sync.py` | `fmp_market_movers` (5, 120s) |
| `news_aggregator.py` | `fmp_news`, `marketaux` |
| `fmp_weights.py` | `fmp_etf` |
| `llm_service.py` (RAG) | `gemini_rag` (5, 60s) |
| `thesis_builder.py` | `gemini_thesis` (5, 120s) |
| `context_compressor.py` | 2개 circuit |
| `briefing/client.py` | `gemini` |
| `neo4j_chain_sight_service.py` | 2개 circuit |

| 미보호 ❌ (대표) |
|------------------|
| `filter_engine.py`, `enhanced_screener_service.py`, `market_breadth_service.py` (FMP) |
| `korean_overview_service.py`, `keyword_generator_v2.py`, `llm_relation_extractor.py`, `news_deep_analyzer.py`, `llm_peer_filter.py` (Gemini) |
| `sec_edgar_client.py` / `collector.py` (SEC) |
| `fred_client.py` (FRED) |
| `stocks/tasks.py`, `views_search.py` (FMP, 캐시 폴백만 존재) |

> 별도 구현 주의: `services/news/services/circuit_breaker.py`는 공통 모듈과 **다른 별도 CB 구현**이다(news/tasks.py에서 사용). 장기적으로 `packages/shared/api_request/circuit_breaker.py`로 통합 검토 권장.

---

## 부록: 조사 신뢰도 메모

- **직접 정독·검증**: `fmp/client.py`, `fmp/provider.py`, `stock_service.py`, `circuit_breaker.py`, `rag_analysis/llm_service.py`, `config/settings.py`(CACHES/Channels), 전체 `get_circuit()` 호출 grep
- **병렬 서브에이전트 조사(일부 file:line 미정밀)**: 나머지 FMP/Gemini/기타 소비처. 실제 수정 착수 전 해당 라인 재확인 필요
- **정정 사항**: `keyword_generator_v2.py`의 CB 적용 보고는 grep 재검증 결과 **오인**으로 확인(미적용)
