# 외부 API 의존성 감사 보고서

> **작성일**: 2026-05-30
> **유형**: 읽기 전용 감사 (코드 수정 없음)
> **범위**: FMP / Gemini / FRED / Neo4j / SEC EDGAR / Redis / Finnhub / Marketaux
> **목적**: 외부 API 장애 시 전체 시스템 영향(blast radius) 평가 + Circuit Breaker 도입 후보 식별

---

## Executive Summary

| 항목 | 평가 |
|------|------|
| **전체 장애 복원력** | ⚠️ **중간 (5/10)** — 핵심 클라이언트는 견고하나, 호출처 fallback 불균형 |
| **최우선 SPOF** | 🔴 **Redis** (캐시 + Circuit Breaker 상태 저장소 겸용 → 다운 시 CB까지 동반 마비) |
| **최대 데이터 손실 위험** | 🔴 **FMP 야간 EOD 파이프라인** (19:30~21:00, S&P500 400+ 종목 누락 가능) |
| **가장 광범위한 코드 취약** | 🟠 **Gemini 429 미처리 18개 파일** (트래픽 급증 시 연쇄 실패) |
| **잘 된 점** | ✅ `marketpulse/utils/circuit_breaker.py` (tenacity 기반 CB + 지수 백오프) 존재, FMP 핵심 클라이언트 4종 예외 분류 견고 |

**핵심 인사이트 3가지**
1. **Circuit Breaker가 Redis에 의존** — CB 상태(`cb:state:*`, `cb:fail_count:*`)를 Django 캐시(=Redis)에 저장한다. Redis가 죽으면 CB 자체가 예외를 던져, 보호 장치가 오히려 추가 장애점이 된다.
2. **클라이언트는 견고, 호출처는 취약** — FMP 클라이언트(`packages/shared/.../fmp/client.py`)는 402/401/403/429를 분류하지만, 일부 호출처(`update_financials_with_provider`, `MarketBreadthService`)는 이를 개별 처리하지 않고 전파하거나 삼켜버린다.
3. **LLM 에러 핸들링이 파일마다 제각각** — 견고한 `rag_analysis/llm_service.py`(429 재시도 + JSON 복구 + CB)부터 무방비 `korean_overview_service.py`(JSON 파싱 예외 전파)까지 편차가 크다. 공통 LLM 래퍼 부재.

---

## 의존성 매트릭스

| 의존성 | 유형 | 1차 클라이언트 위치 | 에러 핸들링 | Timeout | Retry/Backoff | Circuit Breaker | Fallback / Graceful Degradation | SPOF | Blast Radius |
|--------|------|---------------------|------------|---------|---------------|-----------------|-------------------------------|------|--------------|
| **FMP** | 외부 API | `packages/shared/api_request/providers/fmp/client.py` | ✅ 4종 예외 분류 | ✅ 30s | ✅ max 3, 지수백오프 | ⚠️ 호출처 일부만 | ⚠️ 호출처별 편차 큼 | 🔴 **YES** | 🔴 CRITICAL (주가·재무 전부) |
| **FMP (macro)** | 외부 API | `macro/services/fmp_client.py` | ⚠️ RequestException만 | ✅ 30s | ❌ 없음 | ❌ | ⚠️ 메서드별 try/except → 빈값 | — | HIGH |
| **FMP (serverless)** | 외부 API | `serverless/services/fmp_client.py` | ✅ FMPAPIError | ✅ 30s (httpx) | ❌ 없음 | ⚠️ 호출처 | ⚠️ 캐시 우선 | — | HIGH |
| **Gemini** | LLM | 19개 파일 직접 생성 (공통 래퍼 없음) | ⚠️ 파일별 편차 | ❌ 거의 없음 | ⚠️ 5/23 파일만 | ⚠️ 3/23 파일만 | ⚠️ 파일별 편차 | 🟠 부분 | HIGH (분석·키워드·뉴스) |
| **FRED** | 외부 API | `macro/services/fred_client.py` | ✅ transient/permanent 분류 | ✅ 30s | ✅ max 3, 지수백오프 | ❌ | ✅ 기본값(VIX=20 등) | NO | MODERATE |
| **Neo4j** | Graph DB | `rag_analysis/services/neo4j_driver.py`, `chainsight/graph/repository.py` | ✅ lazy init + None | ✅ 2s (RAG) / 60s acquire | ⚠️ PID 재초기화 | ✅ `neo4j_chain_sight_service.py` | ✅ 빈 데이터 반환 + `neo4j_dirty` 큐잉 | 🟠 부분 | HIGH (ChainSight·그래프 마비) |
| **SEC EDGAR** | 외부 API | `sec_pipeline/collector.py` | ✅ requests 예외 raise | ✅ 15/30/60s | ❌ 클라이언트 레벨 없음 | ❌ | ✅ regex→edgartools 폴백, partial 반환 | NO | MODERATE |
| **Redis** | 캐시 + CB 저장소 | `config/settings.py:500` | 🔴 **처리 없음** | — | — | — | 🔴 **없음 (IGNORE_EXCEPTIONS 미설정)** | 🔴 **YES** | 🔴 CRITICAL |
| **Finnhub** | 외부 API (뉴스) | `news/providers/finnhub.py` | ✅ raise_for_status | 🔴 **없음** | ❌ | ⚠️ aggregator | ✅ aggregator에서 빈 리스트 | NO | LOW |
| **Marketaux** | 외부 API (뉴스) | `news/providers/marketaux.py` | ✅ except→빈 리스트 | 🔴 **없음** | ❌ | ⚠️ aggregator | ✅ 빈 리스트 | NO | LOW |
| **PostgreSQL** | 주 DB | Django ORM | 기본값 | 미확인 | ❌ | ❌ | ❌ | PARTIAL | CRITICAL |

> 범례: ✅ 양호 / ⚠️ 부분·불균형 / 🔴 결함·부재 / 🟠 조건부 SPOF

---

## FMP 상세

### 클라이언트 계층 (양호)

3개의 독립 FMP 클라이언트가 존재하며 견고함에 차이가 있다.

| 클라이언트 | 예외 분류 | Retry | Rate Limit | 평가 |
|-----------|----------|-------|-----------|------|
| `packages/shared/api_request/providers/fmp/client.py` | ✅ `FMPAuthError`(401/403), `FMPPremiumError`(402), `FMPRateLimitError`(429/일일한도) | ✅ max 3, 지수백오프 `(attempt+1)*2` | ✅ `request_delay=0.2` + 일일 10,000 카운터 | **9/10 가장 견고** |
| `serverless/services/fmp_client.py` | ✅ `FMPAPIError`로 통합 (httpx) | ❌ | ⚠️ 캐시(60s~24h)로 호출량 감소 | 7/10 |
| `macro/services/fmp_client.py` | ⚠️ `RequestException`만, 402/429 미구분 | ❌ | ⚠️ `request_delay=0.2`만 | 6/10 |

**핵심 코드** — `packages/shared/api_request/providers/fmp/client.py:129-157`:
```python
if response.status_code == 401:   raise FMPAuthError("Invalid API key")
elif response.status_code == 402: raise FMPPremiumError(f"Premium-only ...: {endpoint}")
elif response.status_code == 403: raise FMPAuthError("API access forbidden")
elif response.status_code == 429: raise FMPRateLimitError("Rate limit exceeded")
...
except (FMPPremiumError, FMPAuthError, FMPRateLimitError):
    raise  # 재시도 불필요 에러는 즉시 전파 (양호)
```

### 호출처 계층 (불균형 — 위험 집중)

| 호출처 | 위치 | 예외 개별 처리 | Fallback | 배치 격리 | 위험도 |
|--------|------|--------------|----------|----------|--------|
| `update_financials_with_provider` | `packages/shared/stocks/tasks.py:550-577` | ❌ generic except, **return 없음** | ❌ 종목 영구 누락 | N/A | 🔴 매우높음 |
| `sync_sp500_eod_prices` / `_sync_single_symbol` | `packages/shared/stocks/services/sp500_eod_service.py:128-153` | ⚠️ FMPAPIError→Exception 재포장 | ⚠️ 종목 스킵 | ✅ continue | 🔴 매우높음 |
| `MarketBreadthService.calculate_daily_breadth` | `serverless/services/market_breadth_service.py:68-140` | ❌ 1개 실패→전체 raise | ❌ 캐시·전일값 없음 | N/A | 🔴 높음 |
| `sync_daily_market_movers` | `serverless/services/data_sync.py:73-114` | ✅ CB + FMPAPIError 분리 | ✅ 빈 리스트 | ✅ continue | 🟢 양호(모범) |
| `_fetch_fmp_value` (thesis EOD) | `thesis/tasks/eod_pipeline.py:81-154` | ✅ FMPPremiumError 처리 | ✅ None 반환 | N/A | 🟢 양호 |
| `SectorHeatmapService` | `serverless/services/sector_heatmap_service.py:70-132` | ⚠️ 로깅만 | ⚠️ 섹터 누락 후 진행 | ✅ continue | 🟠 중간 |
| `FilterEngine` / `EnhancedScreenerService` | `serverless/services/filter_engine.py`, `enhanced_screener_service.py` | ⚠️ 통합 반환 | ✅ 빈 결과 | N/A | 🟠 rate 제어 없음 |

### 야간 EOD 파이프라인 FMP 의존도 (최대 위험)

```
19:30  sync_sp500_eod_prices      → 503종목 × 1 call  🔴 FMP 다운 시 400+ 누락 (DailyPrice)
20:00  update_sp500_change_percent → DailyPrice 의존 (상위 누락 시 부정확)
20:00  sync_sp500_financials       → update_financials_with_provider ×101  🔴 종목 영구 누락
20:00  market_breadth / sector_heatmap → 🔴 fallback 없음, 전체 실패 시 하루 데이터 손실
18:00~ run_eod_pipeline (thesis)   → 🟢 부분 실패 허용 (None 반환)
```

**FMP 전체 다운 시나리오 (19:30)**: DailyPrice ~400종목 누락 → 익일 모든 지표 계산 부정확. `sync_sp500_eod_prices`는 `FMPAPIError`를 `Exception`으로 재포장(`sp500_eod_service.py:152`)해 CB 임계치(10) 도달 전 50+ 추가 호출이 발생한다.

### FMP 주요 결함 요약

1. 🔴 **`update_financials_with_provider`**: `except Exception` 후 return 없음 → 429/402 구분 없이 종목 누락. Celery `self.retry()` 미연결.
2. 🔴 **`MarketBreadthService`**: gainers/losers/actives 3개 중 1개 실패로 전체 raise, 전일값·캐시 fallback 없음.
3. 🟠 **`FilterEngine`/`SectorHeatmapService`**: 루프 내 명시적 호출 간격 제어 없음 → 429 유발 가능.
4. 🟠 **`macro/services/fmp_client.py`**: 402/429 미구분, retry 없음.

---

## Gemini 상세

> 25개 파일 중 LLM 실제 호출 ~19개 파일. **공통 래퍼가 없어** 각자 `genai.Client`를 직접 생성하며 에러 핸들링이 제각각.

### 견고도 분류

| 등급 | 파일 | 429 재시도 | JSON 파싱 복구 | CB | Fallback |
|------|------|-----------|--------------|-----|----------|
| 🟢 **견고** | `rag_analysis/services/llm_service.py` | ✅ 지수백오프(1/2/4s) `:248-264` | ✅ 마크다운 제거 `:334` | ✅ | ✅ |
| 🟢 견고 | `serverless/services/thesis_builder.py` | ❌ | ✅ 4단계 JSON 복구 `:421-504` | ✅ | ✅ `:587-635` |
| 🟢 견고 | `serverless/services/keyword_service.py` | ✅ `:317-327` | ✅ `:356-366` | — | ✅ |
| 🟡 중간 | `entity_extractor.py`, `regulatory_service.py`, `llm_peer_filter.py`, `relationship_keyword_enricher.py` | ❌ | ✅ 부분 | ⚠️ | ✅ 빈값 |
| 🔴 **취약** | `rag_analysis/services/adaptive_llm_service.py` | ❌ | ❌ 스트리밍 직접 누적 | ⚠️ | ❌ |
| 🔴 취약 | `serverless/services/keyword_generator_v2.py` | ❌ | ⚠️ | ❌ | ⚠️ |
| 🔴 취약 | `packages/shared/stocks/services/korean_overview_service.py` | ❌ | ❌ `json.loads(response.text)` 예외 전파 `:75` | ❌ | ❌ |
| 🔴 취약 | `marketpulse/briefing/client.py` | ⚠️ CB만 | ❌ `response.text` 직접 | ✅ | ❌ |
| 🔴 취약 | `thesis/tasks/summary.py` | ❌ | ❌ | ❌ | ⚠️ 빈 문자열 |

### 주요 결함

1. 🔴 **429(rate limit) 미처리 광범위 (~18개 파일)** — Gemini Free 15 RPM 한도 초과 시 즉시 예외. 모범은 `llm_service.py:248-264`:
   ```python
   if 'rate' in error_str or 'quota' in error_str or '429' in error_str:
       if attempt < retries - 1:
           delay = self.RETRY_DELAYS[min(attempt, ...)]  # 1, 2, 4초
           await asyncio.sleep(delay); continue
   ```

2. 🔴 **Celery에서 async 호출 의심 (Bug #8 위반 후보)** — `serverless/services/keyword_generator_v2.py:411-422`가 Celery 컨텍스트에서 `loop.run_until_complete(...)`로 async generate를 호출. CLAUDE.md 규칙 "Celery에서는 동기 API만" 위반 가능. **→ 코드 정밀 확인 권장.**

3. 🔴 **JSON 파싱 무방비** — `korean_overview_service.py:75`는 `json.loads(response.text)`를 try/except 없이 호출, LLM이 마크다운 펜스(` ```json `)를 붙이면 즉시 크래시.

4. 🟠 **Timeout 부재** — 대부분 파일이 LLM 호출 timeout 미설정. Gemini가 hang하면 Celery 워커가 무기한 점유될 수 있다.

5. 🟠 **모델 혼재** — 대부분 `gemini-2.5-flash`, 단 `regulatory_service.py`만 `gemini-2.0-flash-exp`(실험판), `portfolio/llm/client.py`는 Claude. 일관성 점검 필요.

---

## 기타 의존성

### Redis 🔴 (최우선 SPOF)

**설정** `config/settings.py:500-505`:
```python
CACHES = {'default': {
    'BACKEND': 'django.core.cache.backends.redis.RedisCache',
    'LOCATION': 'redis://127.0.0.1:6379/1',
}}
```

- 🔴 **`IGNORE_EXCEPTIONS` 미설정** → Redis 다운 시 `cache.get/set`이 그대로 예외를 던진다. Django RedisCache 기본값은 예외 전파.
- 🔴 **CB 동반 마비** — `marketpulse/utils/circuit_breaker.py`는 상태를 `cache.get/set`(=Redis)에 저장(`:58, 67-69`). **Redis가 죽으면 Circuit Breaker 자체가 예외를 던져** 보호 장치가 추가 장애점으로 전환된다. (캐시 미스 graceful degradation의 대전제가 깨짐)
- 🔴 **단일 인스턴스** — `127.0.0.1:6379`, failover 없음. Channels(WebSocket), Celery broker로도 사용 추정.
- 영향: `macro/services/macro_service.py`의 `cache.get`(`:51` 등)은 try/except 없이 호출 → Redis 다운 시 `/api/macro/*` 500.

**Blast Radius: CRITICAL** — 캐시 + CB 상태 + (추정)Celery broker + Channels를 한 인스턴스가 담당.

### Neo4j 🟠 (조건부 SPOF)

- ✅ **Lazy init + None 폴백** `rag_analysis/services/neo4j_driver.py:41-68` — 연결 실패 시 None 반환, 앱은 계속 기동.
- ✅ **CB 적용** `serverless/services/neo4j_chain_sight_service.py:56-142` (`_run_with_cb`, threshold=5/recovery=60).
- ✅ **RAG 2초 timeout** + 실패 시 `_empty_relationships()` 반환 → 그래프 없이 DB 검색으로 degrade.
- ✅ **`neo4j_dirty` 큐잉 패턴** — `sec_pipeline` 모델 `neo4j_dirty` 플래그 + `chainsight/services/neo4j_sync.py:sync_dirty_relations()`(배치 100, 부분 성공 시 성공분만 dirty=False). 일시 장애를 백로그로 흡수.
- ⚠️ 단점: 그래프 기능(ChainSight 프로필/관계)은 Neo4j 없으면 **대체 불가**. 다만 핵심 분석은 계속 동작.

**Blast Radius: HIGH (기능 한정)** — 그래프 의존 화면만 마비, 코어는 생존.

### FRED 🟢 (모범)

- ✅ `macro/services/fred_client.py` — transient(500/502/503/504) 자동 재시도 + permanent(401/403/404) 즉시 raise, 지수백오프(2/4/6s), timeout 30s, 분당 120회 rate limiter.
- ✅ 개별 지표 실패 격리 + 기본값 폴백(VIX=20, spread=1.0).
- ✅ `macro/tasks.py:update_economic_indicators` (`bind=True, max_retries=3`).

**Blast Radius: MODERATE** — 매크로 대시보드만. SPOF 아님.

### SEC EDGAR 🟡

- ✅ User-Agent 헤더 필수(`collector.py:29-32`), rate limit 0.12s sleep(SEC 10 req/s 준수), timeout 15/30/60s 단계별.
- ✅ regex 3단계 → edgartools 라이브러리 폴백 → partial 반환.
- 🔴 **클라이언트 레벨 retry 없음** — timeout/5xx 시 즉시 실패, Celery 태스크 재시도에만 의존.
- ✅ 심볼별 독립 처리 → 배치 부분 성공.

**Blast Radius: MODERATE** — SEC 수집 지연, 기존 문서는 계속 분석 가능. SPOF 아님.

### Finnhub / Marketaux 🟢 (LOW)

- ✅ `news/services/aggregator.py`가 provider별 try/except → 빈 리스트 격리, 상호 폴백.
- 🔴 **두 클라이언트 모두 `requests.get` timeout 미지정** → 응답 지연 시 hang 위험.

**Blast Radius: LOW** — 뉴스 수집만, 다중 provider 폴백.

---

## Circuit Breaker 후보

> 기존 자산: `marketpulse/utils/circuit_breaker.py` (tenacity 기반, 상태 Redis 저장, `get_circuit(name, failure_threshold, recovery_seconds, retry_attempts)` 레지스트리). 별도로 `news/services/circuit_breaker.py`도 존재.
> **선결 과제**: CB가 Redis에 의존하므로, Redis graceful degradation을 먼저 해결하지 않으면 CB 확대가 무의미.

### 우선순위 후보 (장애 시 blast radius 큰 호출 지점)

| 순위 | 호출 지점 | 현재 상태 | 권장 CB 설정 | 근거 |
|------|----------|----------|-------------|------|
| **P0** | **Redis 캐시 계층 자체** | 🔴 무방비 | CB 아님 — `IGNORE_EXCEPTIONS: True` + 인메모리 폴백 우선 | 모든 CB의 저장소. 최우선. |
| **P0** | `update_financials_with_provider` (FMP) | ❌ CB 없음 | `get_circuit("fmp_financials", threshold=5, recovery=300)` + `self.retry` | 야간 재무 영구 누락 |
| **P0** | `MarketBreadthService` (FMP ×3) | ❌ raise 전파 | API별 CB + 전일값 폴백 | 1개 실패→전체 손실 |
| **P1** | `sync_sp500_eod_prices` (FMP) | ⚠️ CB 있으나 재포장 결함 | 기존 CB 유지 + FMPAPIError 재포장 제거 | 400+ 종목 누락 |
| **P1** | Gemini 호출 전반 | ⚠️ 3/19만 CB | 공통 LLM 래퍼 + CB 내장 | 429 연쇄 실패 |
| **P2** | `SectorHeatmapService`, `FilterEngine`, `EnhancedScreener` (FMP) | ❌ rate 제어 없음 | CB + 루프 내 sleep(0.2s) | 429 유발 |
| **P2** | Finnhub / Marketaux | ⚠️ aggregator 격리만 | timeout 명시 + CB | hang 방지 |
| **✅ 적용됨** | `sync_daily_market_movers`, `neo4j_chain_sight_service`, `marketpulse/news_aggregator`, `briefing/client` | CB 적용 | 모범 사례 | — |

### 권장 조치 (감사 결과 — 구현은 별도 승인 후)

**P0 (즉시)**
1. `CACHES['default']['OPTIONS'] = {'IGNORE_EXCEPTIONS': True}` 추가 + Redis 다운 대비 인메모리 폴백 검토. **CB-Redis 의존 고리부터 끊기.**
2. `update_financials_with_provider`: `FMPRateLimitError → self.retry(countdown=300)`, `FMPPremiumError → skip/return`, `FMPAuthError → raise` 분기.
3. `MarketBreadthService`: 3개 API 각각 try/except + 전일값/캐시 폴백, 최소 1개 성공 시 진행.

**P1 (단기)**
4. `sync_sp500_eod_prices`: `FMPAPIError`를 `Exception`으로 재포장하지 말고 stats 기록 후 return (`sp500_eod_service.py:152`).
5. 공통 Gemini 래퍼(`shared/llm_client.py`) 도입 — 429 지수백오프 + 마크다운/JSON 복구 + timeout + CB 내장. `llm_service.py` 패턴을 표준으로.
6. `keyword_generator_v2.py` Celery async 호출(Bug #8) 정밀 확인 및 동기화.

**P2 (중기)**
7. 모든 외부 `requests.get`에 timeout 명시 (Finnhub/Marketaux).
8. FMP 배치 루프에 일관된 rate limit 제어 적용.
9. Neo4j read-replica / SEC 클라이언트 레벨 retry 검토.

---

## 부록: 조사 방법 및 한계

- **방법**: `grep`으로 FMP(~35 파일)·Gemini(~29 파일) 호출처 식별 → 핵심 클라이언트 직접 정독 + 병렬 read-only 에이전트 3종(Gemini 호출처 / FMP 호출처 / 기타 의존성)으로 호출처 전수 조사 → CB·캐시 설정 직접 검증.
- **직접 검증 완료**: FMP 클라이언트 3종, `circuit_breaker.py`, `config/settings.py` CACHES.
- **한계**: 일부 호출처 라인 번호는 에이전트 인용 기반으로, 구현 착수 전 재확인 권장. 특히 ▲`keyword_generator_v2.py`의 Celery async 호출 ▲`update_financials_with_provider`의 return 누락 ▲Celery beat 스케줄 실제 시각은 코드 정밀 확인 필요.
- **수정 사항 없음**: 본 감사는 읽기 전용. 모든 권장 조치는 별도 승인 후 진행.
