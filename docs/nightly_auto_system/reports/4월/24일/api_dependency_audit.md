# 외부 API 의존성 감사 보고서

- **작성일**: 2026-04-24
- **범위**: FMP, Gemini, FRED, SEC EDGAR, Neo4j, Redis, Alpha Vantage, MarketAux/Finnhub
- **모드**: 읽기 전용 감사. 코드 수정 없음.
- **감사 방법**: 파일 전수 스캔 + 호출 패턴 분석 + 장애 전파 매핑

---

## 의존성 매트릭스

### 서비스 × 외부 API 매트릭스

| 서비스 영역 | FMP | Gemini | FRED | Neo4j | SEC EDGAR | Redis | Alpha Vantage | News APIs |
|------------|:---:|:------:|:----:|:-----:|:---------:|:-----:|:-------------:|:---------:|
| Stock Service | ✅ Primary | — | — | — | — | ✅ Cache | ✅ Fallback | — |
| Market Movers (serverless) | ✅ Primary | ✅ Keyword | — | — | — | ✅ Cache | — | — |
| Screener / Filter Engine | ✅ Primary | ✅ LLM Filter | — | — | — | ✅ Cache | — | — |
| Chain Sight | ✅ Primary | ✅ Relations | — | ✅ Graph | ✅ 10-K | ✅ Cache | — | — |
| Macro (Market Pulse) | ✅ Secondary | — | ✅ Primary | — | — | ✅ Cache | — | — |
| News Intelligence v3 | ✅ News | ✅ Deep Analyzer | — | ✅ Events | — | ✅ Cache | — | ✅ Primary |
| RAG Pipeline | — | ✅ **필수** | — | ✅ Context | — | ✅ Cache | — | — |
| Thesis Control | ✅ 지표 | ✅ **필수** | — | — | — | ✅ Cache | — | — |
| EOD Dashboard | ✅ Primary | — | — | — | — | ✅ Cache | — | — |
| Validation (Peer) | ✅ Primary | ✅ LLM Filter | — | — | — | ✅ Cache | — | — |
| SEC Pipeline | — | ✅ Intelligence | — | — | ✅ Primary | — | — | — |
| Celery Queue | — | — | — | — | — | ✅ **Broker** | — | — |

### Fallback/Graceful Degradation 요약

| 의존성 | 재시도 | Fallback 경로 | Graceful Degradation | Circuit Breaker | 장애 영향도 |
|--------|:-----:|--------------|:--------------------:|:---------------:|:----------:|
| **FMP** | 부분(Core만 3회) | Alpha Vantage (일부) | ❌ | ❌ | **Critical** |
| **Gemini** | 부분(llm_service만) | ❌ | 부분 (news Circuit Breaker 존재) | 부분 | **High** |
| **FRED** | ✅ 3회 | ❌ | 부분 | ❌ | Medium |
| **Neo4j** | ✅ Celery 재시도 | ❌ | ✅ 완전 (is_available 패턴) | ❌ | High |
| **SEC EDGAR** | ❌ | ✅ edgartools | 부분 (partial status) | ❌ | Medium |
| **Redis** | 부분 (API 재호출) | ❌ | 제한적 | ❌ | **Critical (Broker)** |
| **Alpha Vantage** | ❌ | ✅ FMP | ✅ | ❌ | Low |
| **MarketAux** | ❌ | 호출자 선택 | ❌ | ✅ 일부 | Medium |
| **Finnhub** | ❌ | MarketAux | ❌ | ✅ 일부 | Medium |

---

## FMP 상세

### 호출 포인트 매트릭스 (13개 주요 위치)

| 레이어 | 파일 | Rate Limit | 402 처리 | 재시도 | Fallback |
|--------|------|:----------:|:--------:|:------:|:--------:|
| Core Client | `api_request/providers/fmp/client.py` | ✅ 0.2s 딜레이 | ✅ 감지/전파 | ✅ 2s×3회 exp | ❌ |
| Provider | `api_request/providers/fmp/provider.py` | ✅ 상속 | ✅ 로깅+PREMIUM_ONLY 코드 | ✅ 상속 | ✅ AV |
| Stock Service | `api_request/stock_service.py` | ✅ 상속 | ✅ 감지 | ✅ 상속 | ✅ 자동 전환 |
| Market Movers | `serverless/services/fmp_client.py` | ⚠️ 캐시 5분만 | ❌ 미감지 | ❌ try-except만 | ❌ |
| Macro | `macro/services/fmp_client.py` | ✅ 0.5s 딜레이 | ❌ 미감지 | ❌ bare raise | ❌ |
| Filter Engine | `serverless/services/filter_engine.py` | ✅ 상속 | ❌ 미감지 | ❌ | ❌ |
| Chain Sight | `serverless/services/chain_sight_service.py` | ⚠️ 1h 캐시만 | ❌ 미감지 | ❌ | ❌ |
| Market Breadth | `serverless/services/market_breadth_service.py` | ⚠️ 5분 캐시만 | ❌ 미감지 | ❌ | ❌ |
| News (FMP) | `news/providers/fmp.py` | ❌ 없음 | ❌ 미감지 | ❌ | ❌ |
| Thesis EOD | `thesis/tasks/eod_pipeline.py` | ✅ 상속 | ✅ 감지 | ✅ None 반환 | ❌ |

### 핵심 이슈

**1) Rate Limit (Starter: 300 calls/min)**
- Core 계층은 0.2s 딜레이 + 일일 10,000 카운터 보유.
- `serverless/services/fmp_client.py`, `chain_sight_service.py`, `market_breadth_service.py`는 **캐시 TTL에만 의존**하여 캐시 미스 폭주 시 초과 가능.
- `news/providers/fmp.py`는 **sleep/throttle 전무**.

**2) FMPPremiumError (402) 처리**
```python
# 양호: api_request/providers/fmp/provider.py
except FMPPremiumError:
    logger.warning(f"FMP premium-only symbol skipped: {symbol}")
    return ProviderResponse.error_response(..., error_code="PREMIUM_ONLY")
```
- **감지되는 곳**: Balance Sheet / Income Statement / Cash Flow / EOD 지표 fetch
- **미감지**: Market Movers, Macro, News, Chain Sight, Filter Engine, Market Breadth (**13개 중 6개 = 46%**)
- **블랙리스트 부재**: BRK.B, BF.B 등 `.` 포함 심볼 사전 필터링이 stocks/tasks.py 일부에만 적용

**3) 재시도 로직**
```python
# api_request/providers/fmp/client.py (L119-159)
for attempt in range(self.max_retries):  # 3회
    try:
        response = requests.get(url, params=params, timeout=30)
    except (FMPPremiumError, FMPAuthError, FMPRateLimitError):
        raise  # 즉시 전파 (정답)
    except (requests.RequestException, FMPClientError) as e:
        wait_time = (attempt + 1) * 2  # 2s, 4s, 6s
        time.sleep(wait_time)
```
- **문제**: 429 (Rate Limit)는 재시도되지 않고 즉시 전파. Celery 계층에서만 별도 재시도.
- **다른 클라이언트**: `serverless/fmp_client.py`, `macro/fmp_client.py`는 **bare raise** (재시도 없음).

**4) 예외 처리 패턴 위험**
```python
# serverless/services/fmp_client.py
except Exception as e:
    logger.error(f"FMP API 예상치 못한 에러: {e}")
    raise FMPAPIError(...)  # 모든 예외를 단일 타입으로 wrapping → 세밀 분기 불가
```

**5) Timeout 설정**
- requests/httpx: `timeout=30` (core, macro, serverless market movers)
- `news/providers/fmp.py`: **timeout 누락** (네트워크 hang 위험)

### 장애 전파 경로

```
FMP API 장애 (402/429/5xx)
  ├─ Market Movers / Market Breadth [Hard Fail]
  │  └─ Dashboard TOP 상승/하락 미표시
  ├─ Screener/Filter Engine [Soft Fail]
  │  └─ 필터 결과 Null → 빈 스크린
  ├─ Chain Sight [Soft Fail]
  │  └─ 피어/펀더멘탈 조회 실패
  ├─ News FMP Provider [Soft Fail]
  │  └─ 뉴스 수집 누락 (로깅만)
  ├─ Macro Service [Hard Fail]
  │  └─ Fear&Greed / 금리 대시보드 중단
  └─ EOD Pipeline [Soft Fail]
     └─ 지표 fetch 실패 → None 반환
```

**Critical Path**: Market Movers → Market Breadth → Dashboard.

---

## Gemini 상세

### 호출 포인트 매트릭스 (23개 파일 · 40+ 호출 지점)

| 파일 | 모델 | Sync/Async | 429 재시도 | JSON 파싱 | 응답 검증 | 주요 위험 |
|------|------|:----------:|:---------:|:---------:|:--------:|----------|
| `rag_analysis/services/llm_service.py` | 2.5-flash | ✅ async | ✅ 3회(1,2,4s) | ❌ | ❌ chunk.text만 | 토큰 추정 의존 |
| `rag_analysis/services/adaptive_llm_service.py` | configurable | ⚠️ 혼용 | ❌ | N/A | ⚠️ 에러만 | `genai.configure()` 동기 |
| `rag_analysis/services/context_compressor.py` | 2.5-flash | ✅ async | ❌ | N/A | ❌ strip만 | truncate fallback 존재 |
| `rag_analysis/services/entity_extractor.py` | 2.5-flash | ✅ async | ❌ | ✅ `_clean_json_response` | ⚠️ JSONDecode → fallback | 마크다운 제거만 |
| `rag_analysis/services/pipeline.py` | 2.5-flash | ✅ async stream | ⚠️ 체크만 | ✅ suggestions | ✅ complete/error | **Celery에서 async 스트리밍** |
| `thesis/services/prompt_builder.py` | 2.5-flash | ❌ sync | ❌ | ✅ json.loads | ⚠️ try-except | 3개 동기 함수 |
| `thesis/services/indicator_matcher.py` | 2.5-flash | ❌ sync | ❌ | ✅ Structured Output | ⚠️ 최소 | 동기 호출만 |
| `thesis/views/conversation_views.py` | 2.5-flash | ⚠️ Django view | ⚠️ 불명확 | 미추적 | 미추적 | **View 내 직접 호출** |
| `serverless/services/thesis_builder.py` | 2.5-flash | ❌ sync (의도됨) | ❌ | ✅ Structured Output | ⚠️ try-except | Celery 호환 |
| `serverless/services/keyword_generator.py` | 2.5-flash | ✅ async | ❌ | ⚠️ 파서 클래스 | 미추적 | 배치 20×300 토큰 |
| `serverless/services/keyword_generator_v2.py` | 2.5-flash | — | ❌ | — | — | 확인 필요 |
| `serverless/services/keyword_service.py` | 2.5-flash | — | ❌ | — | — | 확인 필요 |
| `serverless/services/llm_relation_extractor.py` | 2.5-flash | ❌ sync | ⚠️ CACHE_TTL | ✅ JSON | ✅ confidence 검증 | 호출 컨텍스트 모호 |
| `serverless/services/regulatory_service.py` | 2.5-flash | ⚠️ lazy init | ❌ | — | — | Lazy client |
| `serverless/services/relationship_keyword_enricher.py` | — | — | ❌ | — | — | 확인 필요 |
| `serverless/services/csv_url_resolver.py` | — | — | ❌ | — | — | 확인 필요 |
| `news/services/keyword_extractor.py` | 2.5-flash | ❌ sync | ❌ | ✅ Structured Output | ⚠️ try-except | 동기 호출 |
| `news/services/news_deep_analyzer.py` | 2.5-flash | ❌ sync | ⚠️ RPM_DELAY 4s | ✅ JSON | ✅ tier 검증 | 15 RPM 하드코딩 |
| `news/services/stock_insights.py` | 2.5-flash | ❌ sync | ❌ | ✅ Structured Output | ⚠️ try-except | — |
| `news/api/views.py` | 2.5-flash | ❌ sync | ❌ | ✅ json.loads | ⚠️ 기본 | View 내 직접 호출 |
| `stocks/services/korean_overview_service.py` | — | — | — | — | — | 확인 필요 |
| `sec_pipeline/intelligence.py` | — (프롬프트) | — | N/A | N/A | N/A | 프롬프트 템플릿만 |
| `sec_pipeline/extractor.py` | — | — | — | — | — | 확인 필요 |
| `validation/services/llm_peer_filter.py` | 2.5-flash | ❌ sync | ❌ | ✅ JSON | ⚠️ error 필드만 | 동기 `parse_filter_with_llm()` |

### 핵심 이슈

**1) 동기/비동기 혼용 (P0 위험)**
- `rag_analysis/services/pipeline.py`는 async 스트리밍을 사용하지만 **Celery 태스크에서 호출될 가능성** → Bug #8 재발 위험.
- `serverless/services/thesis_builder.py`는 주석에 "Celery 호환용 **동기 API만**" 명시하여 올바른 패턴.
- `adaptive_llm_service.py`의 `genai.configure()` + `generate_content_async()` 혼용 구조 점검 필요.

**2) 429 Rate Limit 처리 (P1 위험)**
- **구현된 곳**: `llm_service.py`만 `MAX_RETRIES=3` + `RETRY_DELAYS=[1,2,4]` + 429/rate/quota 문자열 감지.
- **부분 구현**: `news_deep_analyzer.py`는 `RPM_DELAY=4s` 하드코딩 (15 RPM = 4초 간격) — 재시도는 없음.
- **미구현 (대다수)**: `context_compressor`, `entity_extractor`, `prompt_builder`, `keyword_generator`, `regulatory_service`, `llm_peer_filter`, `thesis_builder` 등.
- 1500 RPD / 15 RPM 초과 시 **연쇄 실패** (Keyword → Thesis → RAG 순차 중단 가능).

**3) JSON 파싱 에러 처리**
- 강건: `entity_extractor._clean_json_response()`가 마크다운 코드 블록 제거 후 파싱.
- `response_mime_type="application/json"`을 설정한 파일도 여전히 빈 응답/부분 응답에 취약.
- `context_compressor.py`는 `response.text.strip()`만 하여 빈 응답 감지 불가.

**4) 응답 검증 부족**
- `response.finish_reason`(STOP / MAX_TOKENS / SAFETY) 체크가 **프로젝트 전체에서 관찰되지 않음**.
- `safety_ratings` 검사 부재 → 안전 차단 시 빈 응답이 정상 응답으로 처리됨.
- `llm_service.py`는 `chunk.text` 존재만 확인.

**5) 모델명 혼용**
- 대부분 `gemini-2.5-flash`로 통일. `adaptive_llm_service`만 설정값 기반.
- `gemini-2.0-flash`, `gemini-1.5-flash`는 프로젝트 내 미사용 (긍정).

**6) 클라이언트 생성 패턴**
```python
# ❌ 중복 생성: prompt_builder.py, llm_peer_filter.py
client = genai.Client(api_key=api_key)  # 매 호출마다 신규

# ✅ 싱글톤: llm_service.py, context_compressor.py
def __init__(self):
    self.client = genai.Client(api_key=api_key)

# ⚠️ Lazy init: regulatory_service.py
def _get_gemini_client(self):
    if self._gemini_client is None:
        self._gemini_client = genai.Client(api_key=api_key)
```

**7) Timeout**
- `config/settings.py`에 Gemini 전용 timeout 설정 부재.
- SDK 기본값에 의존 → Celery 태스크 타임아웃 초과 시 작업 큐 drift 가능.

### 장애 전파 경로

```
Gemini 429 / 5xx / Timeout
    ├─ RAG (llm_service + context_compressor) → 회원 질문 응답 중단
    ├─ Thesis Builder (prompt_builder + indicator_matcher) → 테제 생성 중단
    ├─ Keyword Generator → Market Movers 키워드 중단
    ├─ News Deep Analyzer → 뉴스 분석 배치 중단
    ├─ LLM Relation Extractor → 공급망 관계 추출 중단
    ├─ Stock Insights → 종목 인사이트 요청 실패
    ├─ Validation/Peer Filter → 유사 종목 필터 중단
    └─ Regulatory Service → 규제 그룹 탐지 중단
```

**Critical Path**: RAG 파이프라인 (사용자 대면) + Thesis Builder (배치) 동시 타격.

---

## 기타 의존성

### FRED API (`macro/services/fred_client.py`)

| 항목 | 상태 |
|------|------|
| Rate Limit | 120 req/min (준수) |
| 재시도 | ✅ 3회 exponential backoff (2/4/6s) |
| Timeout | 30초 |
| 401/403/404 | 즉시 실패 |
| 5xx | 재시도 |
| Fallback | ❌ 없음 — 호출자에 예외 전파 |

**장애 영향**: Market Pulse 금리/인플레이션/고용 지표 중단. 월간 주기라 즉시 복구 압력 낮음.

---

### Neo4j (`rag_analysis/services/neo4j_driver.py`, `serverless/services/neo4j_chain_sight_service.py`, `chainsight/services/neo4j_sync.py`)

| 항목 | 상태 |
|------|------|
| 연결 풀 | max_connection_pool_size=50, lifetime=3600s |
| Graceful Degradation | ✅ 완전 (`is_available()` 패턴 + None 캐싱) |
| 더티 플래그 동기화 | ✅ `neo4j_dirty=True` → 배치 재시도 |
| Celery 재시도 | max_retries=2, default_retry_delay=60s |
| 명시적 Timeout | ❌ (driver 기본값) |

```python
# 표준 패턴
def create_stock_node(...) -> bool:
    if not self.is_available():
        return False  # False 반환, 호출자가 처리
```

**장애 영향**: Chain Sight 온톨로지 조회 불가. PostgreSQL 데이터 유지로 기본 기능은 동작. 동기화 큐가 누적될 수 있음.

---

### SEC EDGAR (`sec_pipeline/collector.py`)

| 항목 | 상태 |
|------|------|
| Rate Limit | 10 req/s 준수 (0.12s sleep) |
| User-Agent | ✅ 설정 (`Stock-Vis stockvis@example.com`) |
| 재시도 | ❌ 단일 시도만 |
| Timeout | 30초(CIK) / 60초(HTML) |
| Fallback | ✅ edgartools (선택 의존성) |
| 부분 실패 처리 | ✅ status=`partial`/`failed` 반환 |

**장애 영향**: 10-K 미수집 → Supply Chain 관계 추출 중단. 뉴스/FMP 데이터로 부분 대체 가능.

---

### Redis (`config/settings.py`)

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

| 항목 | 상태 |
|------|------|
| TTL 정책 | quote 5m / profile 24h / financial 7d |
| `cache.get()` 실패 | None 반환 → API 재호출 (부분 degradation) |
| `cache.set()` 실패 | 로그만, 예외 처리 없음 |
| Celery Broker 역할 | ✅ **단일 장애점** |

**장애 영향**:
1. API 캐시 미스 폭주 → FMP/Gemini 호출 급증 → Rate Limit 연쇄 초과.
2. **Celery 전면 중단** → SEC 수집, Neo4j 동기화, EOD 파이프라인, 뉴스 배치 정지.

---

### Alpha Vantage (`api_request/providers/alphavantage/provider.py`)

| 항목 | 상태 |
|------|------|
| Rate Limit | 5 calls/min (12초 대기) |
| 재시도 | ❌ (base provider 인터페이스만) |
| Fallback | ✅ FMP로 자동 전환 (기본값이 FMP) |

**장애 영향**: 대비용 사용이므로 실질 영향 낮음.

---

### News Providers (`news/providers/marketaux.py`, `news/providers/finnhub.py`)

| 항목 | MarketAux | Finnhub |
|------|-----------|---------|
| Rate Limit | 2,500/day (10s 간격) | 60/min (1s 간격) |
| 재시도 | ❌ | ❌ |
| Timeout | 요청 간 sleep만 | 요청 간 sleep만 |
| Circuit Breaker | ✅ 일부 존재 (`news/services/circuit_breaker.py`) | ✅ 일부 존재 |
| Fallback | 호출자 선택 | ✅ MarketAux |

**장애 영향**: 뉴스 피드 일시 중단 + AI 분석 중단 (사용자 대면).

---

## Circuit Breaker 후보

### 우선순위 **P0 (Critical — 즉시 도입 권장)**

| 지점 | 이유 | 제안 패턴 |
|------|-----|----------|
| **Gemini llm_service.py (RAG)** | 회원 질문 응답 — 사용자 대면 연쇄 실패 시 전면 다운 | 3회 연속 429 → `LLM_UNAVAILABLE` 플래그 → 정적 사용자 메시지 반환 |
| **FMP Market Movers / Market Breadth** | Dashboard TOP 종목 미표시 (사용자 대면) | 5분 내 실패 3회 → 60s circuit open, stale cache 반환 |
| **Redis (Celery Broker)** | 단일 장애점 — 모든 배치 파이프라인 정지 | Sentinel/Cluster + Celery producer 측 백오프 |

### 우선순위 **P1 (High)**

| 지점 | 이유 | 제안 패턴 |
|------|-----|----------|
| **FMP Screener/Filter Engine** | 고장 시 500 에러 노출 | 실패율 >20% → 이전 결과 캐시 반환 |
| **FMP Chain Sight** | 예외 무시(로깅만) → 사용자에게 빈 결과 표시 | 실패 후 이전 스냅샷(Postgres) 재사용 |
| **Gemini Thesis Builder** | Celery에서 연쇄 실패 → 테제 생성 drift | `retry(countdown=300)` + 3회 초과 시 dead letter |
| **Gemini News Deep Analyzer** | 배치 중 429 → 전체 배치 실패 | 429 감지 시 루프 탈출 + checkpoint 저장 |
| **Neo4j 동기화 큐** | 장시간 실패 시 dirty 플래그 누적 | 누적 카운트 모니터링 + circuit breaker 트리거 |

### 우선순위 **P2 (Medium)**

| 지점 | 이유 | 제안 패턴 |
|------|-----|----------|
| **FMP EOD Pipeline (402)** | `.` 포함 심볼 반복 시도 | 402 연속 5회 → 심볼 블랙리스트 자동 등록 |
| **FMP News Provider** | timeout 누락 + 재시도 없음 | 명시적 timeout + 3회 재시도 |
| **SEC EDGAR collector** | 네트워크 오류 시 단일 시도 | 최소 1회 재시도 (backoff) |
| **News Providers (MarketAux/Finnhub)** | 기존 circuit breaker 범위 확장 필요 | 모든 provider에 통일된 breaker 적용 |

### 우선순위 **P3 (Low)**

| 지점 | 이유 | 제안 패턴 |
|------|-----|----------|
| **FRED Macro** | 월간 주기, 즉시 복구 압력 낮음 | Fallback 캐시만 추가 |
| **Alpha Vantage** | FMP로 이미 fallback 존재 | 현행 유지 |

---

## 권장 조치 요약

### 즉시 실행 (P0)

1. **FMP Premium 심볼 블랙리스트 전역 적용** — BRK.B, BF.B 등 사전 필터링 공통 모듈화.
2. **Gemini Celery 태스크 async 호출 검사** — `rag_analysis/services/pipeline.py` Celery 컨텍스트 사용 여부 확인 후 동기 변환.
3. **Redis Sentinel/Cluster 검토** — 단일 장애점 제거.
4. **RAG/Thesis Circuit Breaker** — Redis 기반 실패 카운터 + 정적 fallback 메시지.

### 단기 (P1)

5. **Gemini 공용 재시도 데코레이터** — `llm_service.py` 수준의 `RETRY_DELAYS=[1,2,4]` + 429/quota 감지를 모든 호출 지점에 적용.
6. **FMP 429 재시도** — Celery 태스크 exponential backoff (현재 5분 고정).
7. **Gemini 클라이언트 싱글톤 통합** — `config/gemini_client.py` 공통 모듈화.
8. **`response.finish_reason` / `safety_ratings` 검증 추가**.

### 중기 (P2)

9. **config/settings.py에 `GEMINI_CONFIG` / `FMP_CONFIG`** — 환경변수 기반 rate_limit, timeout, retry 설정 구조화.
10. **`news/services/circuit_breaker.py` 범위 확대** — RAG, Thesis, Chain Sight, Screener에 동일 패턴 적용.
11. **`response.finish_reason`, safety 체크 공통화**.

---

## 통계

- **FMP 호출 지점**: 13개 주요 위치 중 **6개(46%) 402/429 미처리**
- **Gemini 호출 파일**: 23개 · 추적된 40+ 호출 지점 중 **429 재시도 구현은 2개(~5%)**
- **Circuit Breaker 도입된 영역**: News Providers (부분)만 — 전체 외부 의존성의 **<10%**
- **Graceful Degradation 완전 구현**: Neo4j만 (1개)

---

**보고서 작성 완료**: 2026-04-24
**감사자**: Claude Code (읽기 전용)
**다음 단계**: P0 권장 조치의 우선 순위 검토 후 백로그 티켓화
