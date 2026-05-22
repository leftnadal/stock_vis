# 외부 API 의존성 감사 보고서

- **프로젝트**: stock_vis
- **조사 일자**: 2026-05-22
- **조사 범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis 외부 API 호출 전수
- **조사 방식**: 읽기 전용 코드 분석 (수정 금지)

---

## 의존성 매트릭스

| 서비스 | 주요 호출 지점 | Fallback/캐시 | Rate Limit 처리 | Circuit Breaker | 미흡 점 |
|--------|--------------|--------------|----------------|-----------------|--------|
| **FMP (Starter)** | `api_request/providers/fmp/`, `stocks/services/`, `serverless/services/fmp_client.py`, `news/providers/fmp.py`, `macro/services/fmp_client.py` | ✓ 캐시 일부 / 기본값 | ✓ 일부 (3회 재시도) | ✗ 미도입 | 402 Premium 처리 누락 영역 + CB 필요 |
| **Gemini 2.5 Flash** | `rag_analysis/services/`, `serverless/services/`, `thesis/services/`, `news/services/`, `stocks/services/korean_overview_service.py` | ⚠️ RAG만 CB | ⚠️ RAG만 429 재시도 | ⚠️ `gemini_rag`만 적용 | sync 호출군 429/timeout 전무 |
| **FRED API** | `macro/services/fred_client.py` | ✗ 기본값만 | ✓ Rate Limiter + 3회 재시도 | ✗ 미도입 | 실패 시 빈 결과 / CB 없음 |
| **Neo4j** | `serverless/services/neo4j_chain_sight_service.py`, `rag_analysis/services/neo4j_*`, `chainsight/tasks/` | ⚠️ Chain Sight만 fallback | ✗ 없음 | ⚠️ `neo4j_chain_sight`만 | Query timeout / Pool 관리 미흡 |
| **SEC EDGAR** | `sec_pipeline/collector.py` | ✗ 없음 | ✓ 0.12s 수동 대기 | ✗ 없음 | 재시도 / timeout 부족 |
| **Redis 캐시** | 전역 `django.core.cache` | ✗ Cascading 위험 | – | ✗ 미도입 | 캐시 장애 시 모든 API 동시 호출 |

---

## FMP 상세

### 1. 핵심 클라이언트 비교

| 파일 | 호출 메서드 | 에러 처리 | Retry | 402 처리 | 캐시 |
|------|-----------|---------|-------|---------|------|
| `api_request/providers/fmp/client.py:119-161` | `_make_request()` | ✓ 401/402/429 분기 | ✓ 지수 백오프 (2s/4s/6s) | ✓ `FMPPremiumError` raise | ✗ |
| `api_request/providers/fmp/provider.py:59-94` | `get_quote()` 등 | ✓ 4가지 에러 분류 | ✓ 상위 전파 | ✓ `PREMIUM_ONLY` 응답코드 | ✗ |
| `macro/services/fmp_client.py:78-126` | `_make_request()` | ⚠️ 기본 `except Exception` | ✗ 없음 | ✗ 없음 | ✗ |
| `serverless/services/fmp_client.py:51-92` | `_make_request()` | ✓ httpx 예외 분류 | ✗ 없음 | ✗ 없음 | ✓ Redis 300–3600s |
| `news/providers/fmp.py:30-72` | `fetch_company_news()` | ✓ try/except 로깅 | ✗ 없음 | ✗ 없음 | ✗ |

### 2. 호출 경로별 상세

#### Path 1 — Stock Quote / Price (api_request)
- 진입: `api_request/providers/fmp/provider.py:59-84`
- 처리:
  - `FMPRateLimitError(429)` → `RateLimitError` 상위 전파
  - `FMPPremiumError(402)` → `ProviderResponse.error_response(..., "PREMIUM_ONLY")`
  - 일반 `Exception` → `API_ERROR` 응답
- 라인: 86-88, 123-125, 169-170, 208-209, 254-255, 301-302, 346-347
- 평가: ✅ 가장 정돈된 영역. 단 CB 없음 → 연속 402/429 시 cascade.

#### Path 2 — Macro / Market Data (매 시간 갱신)
- 파일: `macro/services/fmp_client.py:78-126`, `get_batch_quotes()` 146-164
- 패턴:
  ```python
  try:
      data = self._make_request(...)
      ...
  except Exception as e:
      logger.error(...)
  return None
  ```
- ❌ 재시도 없음 / ❌ 402 분기 없음 / ❌ 429 분기 없음
- 실패 시 화면 = empty market data
- 라인: 139-144, 161-163, 206-222, 264-287

#### Path 3 — Serverless (Market Movers, Screener)
- 파일: `serverless/services/fmp_client.py:94-137, 117-191`
- 처리: `raise_for_status()` 후 httpx 예외 → `FMPAPIError`
- ✓ Redis 캐시 (5분: gainers/losers/actives, 24시간: profile/peers)
- ❌ 재시도 / ❌ 402 / ❌ 429 명시 처리 없음
- 라인: 71-92, 117-119, 134-136, 151-153, 180-191

#### Path 4 — News
- 파일: `news/providers/fmp.py:30-72`
- 모든 `Exception` 동일 처리 → `[]` 반환
- ❌ 402 / 429 / network 구분 없음
- 라인: 50-54, 88-92, 124-127

### 3. Rate Limit (Starter: 300/min, 10000/day)

| 구현 위치 | 처리 방식 | 한계 |
|----------|---------|------|
| `api_request/providers/fmp/client.py:100-112` | `request_delay=0.2s` + `daily_calls` 수동 카운터 | 카운터 수동 리셋 필요 |
| `macro/services/fmp_client.py:99-102` | 요청 전 0.2s 대기 | 기본만 처리 |
| `serverless/services/fmp_client.py:44` | `httpx.Client(timeout=30.0)` | 429 응답 처리 전무 |
| `news/providers/fmp.py:268-269` | 메타데이터만 노출, 구현 없음 | ❌ |

### 4. FMPPremiumError(402) 처리 현황

| 파일 | 상태 |
|------|------|
| `api_request/providers/fmp/client.py:128-129` | ✓ 즉시 raise |
| `api_request/providers/fmp/provider.py:247-253, 293-299, 339-345` | ✓ `PREMIUM_ONLY` 응답 |
| `macro/services/fmp_client.py` | ❌ |
| `serverless/services/fmp_client.py` | ❌ |
| `news/providers/fmp.py` | ❌ |
| `stocks/tasks.py:150` | ⚠️ `.` 포함 심볼 사전 필터 (부분 회피) |

---

## Gemini 상세

### 1. 호출 지점 매트릭스

| 파일 | 모드 | 에러 처리 | Circuit Breaker | Timeout |
|------|------|---------|-----------------|---------|
| `rag_analysis/services/llm_service.py:205` | async stream | ✓ 429 재시도 + CB | ✓ `gemini_rag` | ✗ |
| `serverless/services/thesis_builder.py:359` | sync (Celery) | ⚠️ `ValueError` 위주 | ✗ | ✗ |
| `serverless/services/keyword_generator_v2.py:269` | async | ⚠️ 기본 except | ✗ | ✗ |
| `serverless/services/keyword_service.py:279` | sync | ⚠️ 기본 except | ✗ | ✗ |
| `serverless/services/llm_relation_extractor.py:384` | sync | ⚠️ 기본 except | ✗ | ✗ |
| `serverless/services/regulatory_service.py:439` | sync | ⚠️ 기본 except | ✗ | ✗ |
| `news/services/keyword_extractor.py:190` | sync | ⚠️ 기본 except | ✗ | ✗ |
| `news/services/news_deep_analyzer.py:125` | sync | ⚠️ 기본 except | ✗ | ✗ |
| `stocks/services/korean_overview_service.py:63` | sync | ⚠️ 기본 except | ✗ | ✗ |

### 2. RAG 영역 (모범 사례)

`rag_analysis/services/llm_service.py:136-272`

```python
cb = get_circuit('gemini_rag', failure_threshold=5, recovery_seconds=60, retry_attempts=1)
stream = await cb.acall(self.client.aio.models.generate_content_stream, ...)
```

- ✓ 429/quota/rate 키워드 감지 → 1s/2s/4s 백오프 (`MAX_RETRIES=3`)
- ✓ `CircuitBreakerError` 처리 → 사용자 메시지 노출 (`L175-272`)
- ✓ Prompt injection escape (`L180-191`)
- ❌ `config`에 timeout 없음 (API 기본값 의존)
- ❌ JSON 파싱 예외 분리 처리 없음

### 3. Non-RAG sync 영역 (위험 지점)

#### ThesisBuilder (`serverless/services/thesis_builder.py:337-395`)
```python
try:
    response_text = self._call_llm_sync(system_prompt, user_prompt)
    thesis_data = self._parse_response(response_text)
    if not thesis_data:
        raise ValueError("LLM 응답 파싱 실패")
except Exception as e:
    logger.exception(...)
    raise
```
- ❌ 429 별도 처리 없음 → 일반 Exception 상위 전파
- ❌ Timeout 미설정 / ❌ CB 없음
- ⚠️ 응답 텍스트 추출이 하드코딩(`L388-392`) → `AttributeError` 위험
- ⚠️ `json.loads()` (`L449`) 실패 시 ValueError → 로그만

#### Keyword / News / Regulatory / Korean Overview
- 공통 패턴: `client.models.generate_content(...)` 직접 호출
- ❌ 429 미식별 / ❌ retry 없음 / ❌ timeout 없음 / ❌ CB 없음
- Celery sync 호출 → 429 누적 시 worker block (common-bug #8 동일 구조)

### 4. Gemini 종합 미흡점

| 항목 | 상태 |
|------|------|
| 429 Rate Limit | ⚠️ RAG만 처리 |
| Timeout | ❌ 전무 |
| Circuit Breaker | ⚠️ RAG만 |
| JSON 파싱 분리 | ❌ 미처리 |
| Sync/Async 정합 | ⚠️ 혼재 (Celery sync 호출이 다수) |
| Prompt Injection | ✓ 기본 escape, ⚠️ tag 조작 여지 |

---

## 기타 의존성

### FRED API (`macro/services/fred_client.py:62-160`)
- Rate Limit: 분당 120회 (여유)
- 처리:
  - 401/403/404 → 즉시 `raise_for_status()`
  - 500/502/503/504 → 2s/4s/6s 재시도 (`max_retries=3`)
  - `RequestException` → 동일 백오프
- 평가: ✓ 재시도 양호 / ❌ CB 없음 / ❌ Fallback 없음 (실패 시 exception 전파)

### Neo4j
- `serverless/services/neo4j_chain_sight_service.py:128-141` — `gemini_rag`와 동일 패턴의 CB(`neo4j_chain_sight`, threshold=10, recovery=120s, retry=1). CB open 시 `{"nodes": [], "relationships": []}` fallback.
- `rag_analysis/services/neo4j_driver.py` — driver는 lazy connect, 실패 복구 미흡
- 미흡:
  - Query timeout 미설정 → 장시간 쿼리가 worker 점유
  - Connection pool 명시 설정 없음 → 부하 급증 시 saturation
  - chainsight/tasks/ 등 CB 미적용 호출 잔존

### SEC EDGAR (`sec_pipeline/collector.py:72-100`)
```python
time.sleep(0.12)
resp = requests.get(url, headers=SEC_HEADERS, timeout=30)
resp.raise_for_status()
```
- ✓ Rate Limit 수동 대기
- ❌ 재시도 없음 / ❌ CB 없음 / ⚠️ timeout=30 고정 (대형 파일 부족)

### Redis 캐시
- 전역 `django.core.cache` 사용. 명시적 fallback 없음.
- 캐시 장애 → 모든 API 동시 호출(cascading) 위험
- TTL 분포 비균질(FMP serverless 300–3600s, FMP api_request 0, Gemini 미사용, FRED 미사용)
- 캐시 무효화 = TTL 의존, 명시적 invalidate 없음

---

## Circuit Breaker 후보

### 기존 도입 현황

| Circuit | 위치 | Threshold | Recovery | 비고 |
|---------|------|-----------|----------|------|
| `gemini_rag` | RAG LLMServiceLite | 5 | 60s | 사용자 메시지 노출 |
| `neo4j_chain_sight` | Neo4j Chain Sight | 10 | 120s | 빈 결과 fallback |

### P0 — 긴급 (1~2주)

#### P0-1. FMP API Circuit Breaker
- 대상: `api_request/providers/fmp/provider.py` 최상위, `macro/services/fmp_client.py`, `serverless/services/fmp_client.py`, `news/providers/fmp.py`
- 권장: `failure_threshold=10`, `recovery_seconds=120`, `retry_attempts=1`
- 근거:
  - 402 Premium 시 무한 재시도 → Celery queue 누적
  - 429 시 재시도 중복으로 부하 증폭
  - 매시간 market data 갱신 실패 = 메인 페이지 empty

#### P0-2. Gemini Non-RAG Circuit Breaker
- 대상: `thesis_builder.py`, `keyword_generator_v2.py`, `keyword_service.py`, `llm_relation_extractor.py`, `regulatory_service.py`, `news/services/keyword_extractor.py`, `news_deep_analyzer.py`, `stocks/services/korean_overview_service.py`
- 권장: `failure_threshold=5`, `recovery_seconds=60`, `retry_attempts=1`
- 추가: 429 감지용 sync 백오프 wrapper 동시 도입 (common-bug #8 패턴)
- 근거:
  - Celery sync 호출 시 timeout 부재 + 429 미식별 → worker block
  - 8개 서비스 동일 패턴 → 공용 wrapper 1회 작성으로 일괄 보호

### P1 — 높음 (2~4주)

#### P1-1. FRED API Circuit Breaker
- 권장: `failure_threshold=5`, `recovery_seconds=180`, `retry_attempts=0`(내부 3회와 중복 방지)
- 근거: transient 에러 시 3회 재시도 × 다회 요청 = 부하 증폭

#### P1-2. Neo4j 전역 Query Timeout + CB 확장
- 권장: query timeout=5s, pool min/max 명시, CB `failure_threshold=10`
- 대상: `rag_analysis/services/neo4j_*`, `chainsight/tasks/`

### P2 — 중간 (1개월)

#### P2-1. SEC EDGAR retry + CB
- 권장: 2s/4s 재시도 + `failure_threshold=5`, `recovery=300s`, timeout 60s 상향

#### P2-2. Redis 캐시 graceful degradation
- 캐시 fail 시 기본값 반환 + 호출 thundering herd 차단 (single-flight lock)

---

## 권장 조치 요약

### 즉시 (1~2주)
1. FMP CB 도입 (`provider.py`/`macro`/`serverless`/`news` 4지점)
2. Gemini sync 호출 공용 wrapper (429 감지 + CB + timeout)
3. SEC EDGAR timeout 30 → 60s 상향

### 단기 (2~4주)
4. Gemini config에 명시 timeout (기본 10s)
5. FRED CB 도입
6. 외부 API 호출 로깅 표준화 (`[API] [STATUS] [ENDPOINT]`)

### 장기 (1개월+)
7. Circuit 상태 모니터링 대시보드
8. FMP/FRED/Gemini 대체 provider chain
9. Celery LLM task soft/hard timeout 통일 (300s / 600s)

---

## 가장 위험한 시나리오

1. **FMP rate limit 폭주** → quote 요청 queue 1시간+ 적체 → 메인 대시보드 empty
2. **Gemini 429 폭주** → sync 호출군 worker block → news/keyword/thesis 동시 정지
3. **Neo4j 연결 실패** → Chain Sight 외 CB 미적용 영역 전체 fail
4. **Redis down** → 모든 API 동시 호출 → CPU spike + 외부 quota 즉시 소진

## 부수 발견 (보안)

- `macro/services/fred_client.py:95` 로그에 API key 포함 URL 노출 가능성 → `logger.error(f"FRED {endpoint} failed")` 형태로 수정 권장
- Prompt Injection: RAG/ThesisBuilder 기본 escape 적용. tag 조작 회피 위해 sanitize 강화 검토

---

**보고서 작성**: 2026-05-22 (읽기 전용 감사, 코드 수정 없음)
