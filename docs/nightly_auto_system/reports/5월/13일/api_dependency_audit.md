# 외부 API 의존성 감사 보고서

**감사 일자**: 2026-05-13
**감사 범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis / Finnhub / Marketaux
**감사 방식**: 읽기 전용 정적 분석 (코드 미수정)
**대상 파일 수**: FMP 35 / Gemini 29 / 기타 10 (총 ~74개)

---

## 의존성 매트릭스 (서비스별 외부 API × fallback 유무)

| 서비스 / 앱 | FMP | Gemini | FRED | Neo4j | SEC | Redis | Finnhub | Marketaux | Fallback 등급 |
|---|---|---|---|---|---|---|---|---|---|
| `stocks/` (tasks, services, views) | ✅ 핵심 | – | – | – | – | ⚠️ 무보호 5건 | – | – | **C** (FMP 단독, Redis 무보호) |
| `stocks/views_search.py` | ✅ | – | – | – | – | – | – | – | C |
| `serverless/` (chain_sight, screener, keyword) | ✅ 핵심 | ✅ 핵심 | – | ✅ 핵심 | – | ✅ CB | – | – | **B** (Neo4j CB 우수) |
| `macro/` (FRED + FMP) | ✅ 보조 | – | ✅ 핵심 | – | – | ✅ try/except | – | – | **A** (예외 시 default dict) |
| `news/` (providers, services, api) | ✅ | ✅ (분석) | – | – | – | ⚠️ 무보호 5건 | ✅ | ✅ | **C** (Redis 무보호, timeout 누락) |
| `rag_analysis/` | – | ✅ 핵심 (async) | – | ✅ (간접) | – | – | – | – | B |
| `thesis/` (tasks, services) | ✅ (EOD) | ✅ 핵심 (sync) | – | – | – | – | – | – | B |
| `portfolio/` (LLM) | – | ✅ (LLMClient) | – | – | – | – | – | – | **A** (Pydantic+CostGuard+Anthropic FB) |
| `sec_pipeline/` | – | ✅ (extractor) | – | – | ✅ 핵심 | – | – | – | **C** (SEC 재시도/CB 없음) |
| `validation/services/llm_peer_filter.py` | – | ✅ | – | – | – | – | – | – | C (재시도 없음) |
| `marketpulse/briefing/` | – | ✅ (CB) | – | – | – | ✅ try/except | – | – | A |
| `chainsight/` | – | – | – | ✅ | – | ✅ CB | – | – | A |

**범례**: A = graceful degradation 보장 / B = 부분 보호 / C = 단일 실패점 위험

---

## FMP 상세

### 핵심 클라이언트 (3개 병존 — 통일 부재)

| 파일 | 용도 | 에러 핸들링 | Retry | 0.2s 슬립 | 402 처리 | Fallback |
|---|---|---|---|---|---|---|
| `api_request/providers/fmp/client.py:1-492` | 표준 클라이언트 | FMPAuthError/PremiumError/RateLimitError/ClientError 분리 | 수동 3회 지수 백오프 (line 119-159) | ✅ (line 107) | ✅ FMPPremiumError (line 129) | ❌ (provider 위임) |
| `serverless/services/fmp_client.py:24-250` | 서버리스용 (httpx) | FMPAPIError 단일 | ❌ | ❌ | ❌ (raise_for_status에 흡수) | ❌ |
| `macro/services/fmp_client.py:78-165` | macro 전용 | RequestException + 'Error Message' → ValueError | ❌ | ✅ (line 101-102) | ❌ (FMPPremiumError 미존재) | get_quote→None 반환 |

**문제 1 — 3개 클라이언트 병존**: 동일 외부 API에 대해 에러 분류 정책이 3가지로 갈라져 있다. `FMPPremiumError`는 `api_request/`에만 존재하고 `serverless/`·`macro/`는 같은 402를 일반 4xx로 취급.

**문제 2 — Fallback chain 완전 비어 있음**: `api_request/providers/factory.py:67-69`
```python
FALLBACK_CHAIN: Dict[ProviderType, List[ProviderType]] = {
    ProviderType.FMP: [],
}
```
Alpha Vantage 제거 후 FMP 단독. FMP 장애 = 전체 가격/재무/검색 API 다운. `call_with_fallback` 이름과 달리 실제 대체 경로 없음.

### 호출 지점별 처리

| 위치 | 에러 핸들링 | 402 처리 | Fallback | Timeout |
|---|---|---|---|---|
| `api_request/providers/fmp/provider.py:31-353` | FMPPremiumError 캐치 후 `error_response("PREMIUM_ONLY")` (line 247, 293, 339) | ✅ 조용한 skip | ProviderResponse.success=False | 30s |
| `api_request/stock_service.py:1-775` | response.success 체크 후 로그+계속 (line 231-232, 315-317, 373-375) | 간접 (provider 위임) | ❌ 부분 성공 허용 | 30s |
| `stocks/tasks.py:1-728` | Celery max_retries=3 + countdown 60-300s | ❌ 명시 없음 | call_with_fallback (실제 빈 체인) | soft 1800s/hard 1860s |
| `stocks/services/sp500_service.py:25-106` | CircuitBreakerError 캐치 후 zero stats 반환 | CB가 402도 일반 실패로 흡수 | ✅ 데이터 stale | 30s |
| `stocks/services/sp500_eod_service.py:26-200` | CB + FMPAPIError 분리 캐치 | ❌ CB가 흡수 | error_symbols 누적 후 계속 | 30s |
| `serverless/services/data_sync.py:1-150` | CB + FMPAPIError 캐치 | ❌ | 부분 성공 허용 | 30s |
| `serverless/services/chain_sight_service.py` | 일반 Exception 캐치 | ❌ | ETF holdings 없을 시 빈 리스트 | 30s |
| `macro/services/macro_service.py:22-100` | Generic Exception → default dict (Fear&Greed=50) (line 77-85) | 간접 | ✅ 우수 (항상 응답) | 30s |
| `news/providers/fmp.py:20-140` | Generic Exception → 빈 리스트 (line 54, 92, 127) | 간접 | ✅ graceful | 30s |
| `thesis/tasks/eod_pipeline.py:80-150` | FMPPremiumError 명시 캐치 (line 144) | ✅ 경고+None 반환 | ✅ 지표 누락으로 계속 | 30s |

### Rate Limit 처리 현황 (FMP Starter: 300/min, 10,000/day)

- ✅ `api_request/providers/fmp/client.py:107`: time.sleep(0.2s) per request → 약 300/min 한계 근접
- ✅ `api_request/providers/fmp/client.py:110`: 일일 카운터 (10,000 한계 체크)
- ✅ Celery `update_financials_with_provider`: rate_limit='6/m' (line 509)
- ✅ `stocks/tasks.py:179`: countdown 7s 간격으로 101 심볼 분산 (~12분)
- ⚠️ `serverless/services/fmp_client.py`: **자체 throttling 없음** — 호출자가 책임
- ⚠️ 분산 환경에서 워커가 여러 개 뜨면 단일 슬립이 의미 없음 (전역 토큰 버킷 부재)

### 버그 #23 — `.` 심볼 제외 처리

- ✅ `stocks/tasks.py:146-150`에서 BRK.B, BF.B 등 필터링 확인
- ⚠️ 다만 `update_financials_with_provider` 단일 심볼 호출 시 사전 필터 없음 — 호출자가 책임

### 검증된 위험

1. **단일 실패점**: FMP 장애 = 가격/재무/EOD/Screener/Chain Sight/News 동시 다운
2. **402 처리 비대칭**: 같은 응답을 다르게 해석하는 클라이언트 3개
3. **Rate limit 분산 환경 미고려**: 워커 N개 × 0.2s = 60N req/s 가능
4. **Timeout 균일 30s**: 느린 응답 시 워커 큐 적체 (특히 batch task)

---

## Gemini 상세

### 핵심 클라이언트 (단일화 부재 — 30+ 파일 독립 인스턴스화)

**모범 사례 1개 / 위험 다수**

| 파일 | Sync/Async | 429 처리 | JSON 안전 | Retry | Timeout | Cost |
|---|---|---|---|---|---|---|
| `portfolio/llm/client.py:99-298` | ✅ SYNC | ✅ 명시 (line 72) | ✅ Pydantic LLMResponse | ✅ 1회+Anthropic FB | Default | ✅ CostGuard |
| `rag_analysis/services/llm_service.py:22-259` | ❌ ASYNC | ✅ "rate\|quota\|429" 매칭 + 지수 3회 (RETRY_DELAYS=[1,2,4]) | ✅ ResponseParser+JSONDecodeError | ✅ 수동 백오프 | Default | ✅ usage_metadata |
| `rag_analysis/services/adaptive_llm_service.py:86-176` | ❌ ASYNC | ❌ | ❌ (스트리밍) | ❌ | Default | △ |
| `rag_analysis/services/entity_extractor.py:54-113` | ❌ ASYNC | ❌ | ⚠️ raw json.loads (line 98) | ❌ (fallback 함수만) | Default | ❌ |
| `rag_analysis/services/context_compressor.py:43-79` | ❌ ASYNC | ✅ CB 흡수 | ❌ (텍스트) | ✅ CB tenacity 3회 | Default | ❌ |
| `serverless/services/keyword_generator.py` | ❌ ASYNC | ❌ | KeywordResponseParser | ❌ | Default | △ |
| `serverless/services/keyword_generator_v2.py` | ❌ ASYNC | ❌ | EnhancedKeywordResponseParser | ❌ | Default | △ |
| `serverless/services/llm_relation_extractor.py` | – | ❌ | ⚠️ json.loads | ❌ | Default | △ 월$5 한도 |
| `news/services/keyword_extractor.py:25-80` | ✅ SYNC | ❌ | ⚠️ | ❌ (FALLBACK_KEYWORDS) | Default | ❌ |
| `news/services/news_deep_analyzer.py` | (미상세) | ❌ | ⚠️ | ❌ | Default | ❌ |
| `news/services/stock_insights.py` | ✅ SYNC | (LLM 직호출 없음) | – | – | – | – |
| `thesis/tasks/summary.py:55-77` | ✅ SYNC ✅ 버그#8 준수 | ❌ | response.text만 | ✅ Celery max_retries=2 + 300s | soft 300s/hard 420s | ❌ |
| `thesis/services/thesis_builder.py` | (미확정) | ❌ | (미상세) | ❌ | Default | ❌ |
| `thesis/services/indicator_matcher.py` | (미상세) | ❌ | (미상세) | ❌ | Default | ❌ |
| `sec_pipeline/extractor.py:18-92` | ✅ SYNC | ❌ | ⚠️ raw json.loads (line 75) | ❌ | Default | ❌ |
| `portfolio/services/e1_garp.py` | ✅ SYNC (LLMClient 위임) | ✅ | ✅ Pydantic | ✅ | Default | ✅ |
| `portfolio/services/e3_portfolio_service.py` | ✅ SYNC (LLMClient 위임) | ✅ | ✅ Pydantic | ✅ | Default | ✅ |
| `portfolio/services/e5_adjustment_parser.py` | ✅ SYNC (위임) | ✅ | ✅ | ✅ | Default | ✅ |
| `validation/services/llm_peer_filter.py:56-80` | ✅ SYNC | ❌ | ✅ response_mime_type='application/json' | ❌ | Default | ❌ |
| `marketpulse/briefing/client.py:39-69` | ✅ SYNC | ✅ CB 흡수 | usage_metadata만 | ✅ CB tenacity 3회 지수 | Default | ✅ 토큰 카운트 |
| `stocks/services/korean_overview_service.py:21-80` | ✅ SYNC | ⚠️ RPM_DELAY=4s 하드코딩 | ⚠️ raw json.loads (line 76) | ❌ | Default | ❌ |

### 발견된 패턴

1. **공유 클라이언트 부재**: 각 서비스마다 `genai.Client()` 독립 인스턴스화 — 풀링/중복 제거 없음
2. **`portfolio/llm/client.py`가 유일한 모범 사례**: Anthropic fallback + CostGuard + Pydantic
3. **버그 #8 (Celery에서 async 금지) 위험**:
   - ✅ 준수: `thesis/tasks/summary.py:55-77` (sync), `portfolio/*`, `validation/*`, `marketpulse/*`
   - ⚠️ 위험: `rag_analysis/services/entity_extractor.py`, `adaptive_llm_service.py`, `context_compressor.py`, `serverless/services/keyword_generator*.py` — async 함수가 Celery 태스크에서 호출되는지 확인 필요
4. **429 명시 처리는 4개 파일만** (총 21개 중): `portfolio/llm/client.py`, `rag_analysis/services/llm_service.py`, `marketpulse/briefing/client.py`, `stocks/services/korean_overview_service.py`(하드 슬립)
5. **JSON 파싱 위험**: `sec_pipeline/extractor.py:75`, `rag_analysis/services/entity_extractor.py:98`, `stocks/services/korean_overview_service.py:76` 등 raw `json.loads` — Gemini 응답에 markdown 감싸기, 트레일링 콤마 등 발생 시 크래시
6. **Timeout 누락**: `request_options` 명시한 곳 0개 — SDK default(약 30s) 의존
7. **Free tier (15 RPM) 한도**: `korean_overview_service`의 4s 하드 슬립 외에는 전역 토큰 버킷 없음. 다수 서비스가 동시 호출 시 429 폭증 가능

### 비용 추적 분산

- `portfolio/llm/cost_guard.py` (Pydantic 기반)
- `rag_analysis/services/cost_tracker.py` (별도)
- 나머지 서비스는 추적 없음
- 통합 비용 한도 부재 → 한 서비스의 폭주가 전체 일일 1500 RPD 한도 소진 가능

---

## 기타 의존성

### FRED (Federal Reserve)

| 항목 | 평가 |
|---|---|
| 위치 | `macro/services/fred_client.py:99-155` |
| 에러 핸들링 | ✅ 우수 — 500/502/503/504 재시도, 401/403/404 즉시 실패 |
| Retry | ✅ 3회 지수 백오프 (2s, 4s, 6s) |
| Rate limit | ✅ `self.rate_limiter.acquire()` (line 70-101), FRED 한도 120/min 대응 |
| Fallback | ✅ `macro_service.py:77-85` default 반환 (VIX=20, spread=1.0) |
| Timeout | 30s (line 103) |
| Circuit Breaker | ❌ |

**평가**: 외부 API 의존성 중 가장 안정적. 다만 CB 부재 — FRED 장기 다운 시 매 요청마다 30s 대기 후 fallback.

### Neo4j

| 항목 | 평가 |
|---|---|
| 위치 | `rag_analysis/services/neo4j_driver.py:49-67`, `serverless/services/neo4j_chain_sight_service.py:109-199`, `chainsight/tasks/sync_tasks.py:28-88` |
| 에러 핸들링 | ✅ 우수 — driver init 실패 시 None 반환, `is_available()` 체크 |
| Circuit Breaker | ✅ failure_threshold=5, recovery=60s (`neo4j_chain_sight_service.py:117-126`) |
| Fallback | ✅ Graph 없이 앱 계속 동작 |
| Timeout | ✅ acquisition 60s, lifetime 3600s |
| Pooling | ✅ max_connection_pool_size=50 + `force_reset_after_fork()` |

**평가**: 모범 사례. 다른 외부 API도 이 패턴을 모델로 삼아야 한다.

### SEC EDGAR

| 항목 | 평가 |
|---|---|
| 위치 | `sec_pipeline/collector.py:84-91, 130-143, 153-159` |
| 에러 핸들링 | ⚠️ 기본 try/except, raise_for_status 즉시 실패 |
| Retry | ❌ 없음 |
| Rate limit | ✅ time.sleep(0.12s) (SEC 가이드 10/s 준수) |
| Fallback | △ CIK 조회만 클래스 캐시(`_cik_cache`); filing HTML은 raise |
| Timeout | submissions 30s / CIK 15s / filing 60s |
| Circuit Breaker | ❌ |

**위험**: 단일 SEC 호출 실패가 전체 파이프라인 실패로 직결. 재시도 없음.

### Redis

**무보호 cache.get 확인 완료 (10건)**:

`stocks/views.py`:
- line 261, 493, 632, 706, 778 — 모두 try/except 없음

`news/api/views.py`:
- line 87, 136, 270, 331, 403 — 모두 try/except 없음

**예상 영향**: Redis 다운 시 `cache.get()` → `ConnectionError` 발생 → 500 에러. 호출 지점이 핵심 차트/뉴스 엔드포인트라 사용자 가시성 높음.

**보호된 위치**:
- `marketpulse/api/views/health.py:40-44` (try/except)
- `news/services/circuit_breaker.py:35, 47, 50-64` (try/except)
- `serverless/services/neo4j_chain_sight_service.py:54` (CB 상태 저장, 실패 시 우회 가능)

**검증 명령**: `grep -n "cache.get" stocks/views.py news/api/views.py | wc -l → 10건`

### Finnhub / Marketaux

| 항목 | Finnhub | Marketaux |
|---|---|---|
| 위치 | `news/providers/finnhub.py:39-170` | `news/providers/marketaux.py:41-181` |
| 에러 핸들링 | ✅ Exception → [] 반환 | ✅ Exception → [] 반환 |
| Retry | ❌ | ❌ |
| Rate limit | ✅ 1s sleep (60/min) | ✅ 10s sleep (2500/day) |
| Fallback | ✅ 빈 리스트 | ✅ 빈 리스트 |
| **Timeout** | ❌ **`requests.get` 누락** (line 67) | ❌ **`requests.get` 누락** (line 69) |
| Circuit Breaker | ❌ | ❌ |

**위험 (검증됨)**: `news/providers/finnhub.py:67`의 `requests.get(url, params=params)`에 timeout 파라미터 없음 → 응답이 안 오면 영구 대기. 동일 패턴 marketaux에도 존재.

### Alpha Vantage

`api_request/providers/factory.py:66` 주석 — "Alpha Vantage 제거 후 FMP 단독". 사실상 미사용.

---

## Circuit Breaker 후보

### 도입 우선순위 (장애 시 시스템 영향도 × 현재 보호 수준)

| 순위 | 대상 | 사유 | 현재 보호 | 영향 범위 |
|---|---|---|---|---|
| 🔴 **1** | **FMP (전체)** | 단일 실패점, fallback chain 비어 있음, 모든 가격/재무 의존 | 부분 (sp500 CB만) | 가격/재무/EOD/Screener/Chain Sight/News (전사) |
| 🔴 **2** | **Redis (stocks/views, news/api/views)** | 10개 엔드포인트가 무보호 cache.get | 없음 | 차트, 뉴스 메인 페이지 |
| 🔴 **3** | **Gemini (전체)** | 21개 호출 지점 분산, 429 처리 4개만, 비용 추적 분산 | 부분 (portfolio, marketpulse, rag/llm_service만) | RAG/Screener/News/Thesis/SEC/Validation |
| 🟡 **4** | **SEC EDGAR** | 재시도 없음, 단일 실패가 10-K 파이프라인 전체 실패로 직결 | 없음 | sec_pipeline 전용 |
| 🟡 **5** | **Finnhub / Marketaux** | timeout 누락으로 영구 대기 가능 | 없음 (빈 리스트만) | News 보조 |
| 🟢 6 | FRED | 이미 retry+rate_limit 있음, CB만 추가하면 완성 | 부분 | macro 대시보드 |
| ✅ 7 | Neo4j | 이미 CB 도입 — 모범 사례 | 완료 | – |

### 구체 제안 (이 보고서는 분석만 — 코드 수정 없음)

1. **FMP 통합 CB**: `api_request/providers/fmp/client.py`에 CB 도입 + `serverless/`·`macro/`의 별도 클라이언트를 단일 클라이언트로 통합. 402 분류 정책 일원화.
2. **Redis 통합 helper**: `safe_cache_get(key, default=None)` 형태로 try/except 단일화. `stocks/views.py`·`news/api/views.py`의 10건을 마이그레이션.
3. **Gemini 통합 클라이언트**: `portfolio/llm/client.py` 패턴을 전사 표준으로 격상 (CostGuard + Anthropic fallback + 429 분류 + Pydantic 응답).
4. **SEC EDGAR retry+CB**: `sec_pipeline/collector.py`에 tenacity 적용 (3회 지수 백오프) + CB.
5. **Finnhub/Marketaux**: 두 줄 수정 — `requests.get(..., timeout=10)` 추가 후 CB.

### 통합 관측 지표 (모니터링 후보)

- Circuit Breaker 상태 (open/half-open/closed) 별 게이지
- 외부 API 별 응답 시간 p95/p99 히스토그램
- 429/402/5xx 응답률
- Redis 연결 실패율
- Gemini 토큰 사용량 (전사 합산 vs 일일 한도)

---

## 부록 — 검증 명령

본 보고서의 핵심 주장은 다음 명령으로 재확인 가능:

```bash
# FMP fallback chain이 비어 있음
grep -A 2 'FALLBACK_CHAIN' api_request/providers/factory.py
# → ProviderType.FMP: []

# Redis 무보호 cache.get 위치
grep -n 'cache.get' stocks/views.py news/api/views.py
# → 10건, 모두 직전에 try/except 없음

# Finnhub/Marketaux timeout 누락
grep -n 'requests.get' news/providers/finnhub.py news/providers/marketaux.py
# → timeout 파라미터 없음

# FMP 클라이언트 3개 병존
ls api_request/providers/fmp/client.py serverless/services/fmp_client.py macro/services/fmp_client.py

# Gemini 호출 지점 (29개 비-테스트 파일)
grep -rl 'generate_content\|genai' --include='*.py' . | grep -v __pycache__ | grep -v tests/ | grep -v scripts/ | wc -l
```

---

**감사 종료 — 코드 수정 없음. 권고 사항은 별도 PR로 진행 권장.**
