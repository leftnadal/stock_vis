# 외부 API 의존성 감사 보고서

> **작성일**: 2026-05-29
> **범위**: FMP, Gemini, FRED, Neo4j, SEC EDGAR, Redis 외부 의존성의 장애 대응 패턴
> **성격**: 읽기 전용 감사 (코드 수정 없음)
> **방법**: 핵심 클라이언트 직접 정독 + 호출 지점 약 60개 파일 전수 조사

---

## 0. 요약 (Executive Summary)

| 의존성 | 호출 지점 수 | 장애 대응 성숙도 | 종합 판정 |
|--------|------------|----------------|----------|
| **FMP** | ~23 파일 | 중간 (코어 클라이언트는 우수, 호출부 불균일) | ⚠️ 호출부 표준화 필요 |
| **Gemini** | ~25 파일 | 낮음~중간 (CB/timeout 적용 2~3곳뿐) | ⚠️ timeout·429 표준화 시급 |
| **FRED** | macro/services | 우수 (timeout+retry+에러 분류) | ✅ 안정적 |
| **Neo4j** | serverless/rag_analysis | 우수 (완전 graceful degradation) | ✅ 안정적 |
| **SEC EDGAR** | sec_pipeline | 중간 (rate limit 준수, retry 없음) | ⚠️ 가능 |
| **Redis** | 전역 캐시 + CB 백엔드 | **취약 (SPOF)** | 🔴 단일 장애점 |

### 핵심 발견 3가지

1. **🔴 Redis는 숨은 단일 장애점(SPOF)이다.**
   `config/settings.py:499-504`는 Django **native** `RedisCache` 백엔드를 쓴다(`django-redis`가 아님). native 백엔드는 `IGNORE_EXCEPTIONS` 옵션을 지원하지 않으므로 Redis가 죽으면 `cache.get/set` 호출이 곧장 예외를 던진다. 더 나쁜 점은 **두 Circuit Breaker 구현이 모두 상태를 Redis에 저장**한다는 것 — Redis 장애 시 장애 방어 장치인 CB 자체가 작동 불능이 된다(복합 위험).

2. **⚠️ Circuit Breaker 구현이 2개로 분기되어 있고 적용이 산발적이다.**
   `marketpulse/utils/circuit_breaker.py`(tenacity 기반, HALF_OPEN 지원)와 `news/services/circuit_breaker.py`(단순 INCR 기반)가 별도로 존재한다. Gemini 호출 25곳 중 CB 적용은 3곳(`gemini_rag`, `gemini_compress`, `gemini_thesis`)뿐이다.

3. **⚠️ Gemini 호출에 HTTP timeout이 사실상 전무하다.**
   `google.genai` SDK는 명시적 timeout을 지정하지 않으면 무한 대기에 가깝다. 조사한 호출 25곳 중 `http_options(timeout=...)`를 설정한 곳은 발견되지 않았다. Celery 워커/Django 요청이 응답 지연 시 누적 점유될 위험.

---

## 1. 의존성 매트릭스 (서비스별 외부 API × fallback 유무)

| 서비스/모듈 | 외부 API | try/except | retry | timeout | fallback | CB | 장애 시 영향 |
|------------|---------|:---:|:---:|:---:|:---:|:---:|------------|
| `api_request/providers/fmp/client.py` (코어) | FMP | ✅ 세분화 | ✅ 3회 백오프 | ✅ 30s | ❌ | ❌ | 예외 전파 |
| `api_request/stock_service.py` | FMP | ✅ | ❌ | (코어) | ✅ DB 기존값 | ❌ | 부분 진행 |
| `serverless/services/fmp_client.py` | FMP(httpx) | ✅ | ❌ | ⚠️ 미확인 | ❌ | ❌ | 예외 전파 |
| `serverless/services/data_sync.py` | FMP | ✅ | ❌ | (코어) | ✅ 빈 리스트 | ✅ | 부분 실패 허용 |
| `serverless/services/chain_sight_service.py` | FMP | ⚠️ continue | ❌ | (코어) | ⚠️ 종목 스킵 | ❌ | 부분 실패 허용 |
| `serverless/services/enhanced_screener_service.py` | FMP | ✅ raise | ❌ | (코어) | ❌ | ❌ | **전체 스크리너 중단** |
| `serverless/services/market_breadth_service.py` | FMP | ✅ raise/None | ❌ | (코어) | ❌ | ❌ | **전체 계산 중단** |
| `stocks/services/sp500_service.py` | FMP | ✅ | ❌ | (코어) | ✅ 빈 결과 | ✅ thr=3/300s | 동기화 스킵 |
| `stocks/services/sp500_eod_service.py` | FMP | ✅ | ❌ | (코어) | ⚠️ 심볼 스킵 | ✅ thr=10 | 부분 실패 |
| `stocks/tasks.py` | FMP | (위임) | ✅ countdown | (코어) | ❌ | ❌ | 심볼별 독립 |
| `serverless/tasks.py` | FMP | ✅ | ✅ Celery 3회/300s | (코어) | ❌ | ❌ | retry 후 실패 |
| `macro/services/macro_service.py` | FMP/FRED | ✅ | (하위) | (하위) | ✅ 기본값 | ❌ | graceful(기본값) |
| `macro/services/fred_client.py` | FRED | ✅ 분류 | ✅ 3회 백오프 | ✅ 30s | ⚠️ 지표 누락 | ❌ | 부분 누락 |
| `news/providers/fmp.py` | FMP | ✅ | ❌ | (코어) | ✅ 빈 리스트 | ❌ | 뉴스 누락(침묵) |
| `news/services/aggregator.py` | FMP/Finnhub/Marketaux | ✅ | ❌ | (하위) | ✅ 멀티 provider | (news CB) | 부분 실패 허용 |
| `marketpulse/services/news_aggregator.py` | FMP/Marketaux | ✅ | ❌ | (하위) | ⚠️ stats 기록 | ✅ fmp_news | 부분 실패 허용 |
| `marketpulse/fetchers/fmp_weights.py` | FMP | ✅ | (CB 내부) | ⚠️ | ❌ | ✅ | 예외 전파 |
| `thesis/tasks/eod_pipeline.py` | FMP | ✅ Premium/Client | ❌ | (코어) | ✅ (None,None) | ❌ | 지표 None |
| `rag_analysis/services/llm_service.py` | Gemini | ✅ | ✅ [1,2,4] | ❌ | ✅ error 이벤트 | ✅ gemini_rag | graceful |
| `rag_analysis/services/context_compressor.py` | Gemini | ✅ | (CB) | ❌ | ✅ truncate | ✅ gemini_compress | graceful |
| `rag_analysis/services/adaptive_llm_service.py` | Gemini | ✅ | ❌ | ❌ | ✅ 빈 yield | ❌ | 빈 응답 |
| `rag_analysis/services/entity_extractor.py` | Gemini | ✅ | ❌ | ❌ | ✅ fallback 추출 | ❌ | graceful |
| `serverless/services/thesis_builder.py` | Gemini | ✅ JSON수리 | ❌ | ❌ | ✅ fallback thesis | ❌ | graceful |
| `serverless/services/keyword_generator(_v2).py` | Gemini | ⚠️ | ❌ | ❌ | ✅/❌ | ❌ | 혼재 |
| `serverless/services/keyword_service.py` | Gemini | ✅ | ⚠️ 검사만 | ❌ | ✅ FALLBACK dict | ❌ | graceful |
| `serverless/services/llm_relation_extractor.py` | Gemini | ✅ | ❌ | ❌ | ✅ 빈 리스트 | ❌ | graceful |
| `serverless/services/relationship_keyword_enricher.py` | Gemini | ✅ | ❌ | ❌ | ⚠️ regex | ❌ | 부분 |
| `serverless/services/csv_url_resolver.py` | Gemini | (regex) | ❌ | ❌ | ✅ pattern | ❌ | graceful |
| `thesis/services/thesis_builder.py` | Gemini | ✅ | ❌ | ❌ | ✅ _fallback_parse | ✅ gemini_thesis/120s | graceful |
| `thesis/services/prompt_builder.py` | Gemini | ✅ | ❌ | ❌ | ⚠️ None 반환 | ❌ | **None 전파 위험** |
| `thesis/services/indicator_matcher.py` | Gemini | ✅ | ❌ | ❌ | ✅ 빈 리스트 | ❌ | graceful |
| `thesis/tasks/summary.py` | Gemini | (텍스트) | ❌ | ❌ | ✅ 빈 문자열 | ❌ | graceful |
| `thesis/views/conversation_views.py` | Gemini | ✅ | ❌ | ❌ | ✅ fallback_issues | ❌ | graceful |
| `stocks/services/korean_overview_service.py` | Gemini | ✅ | ❌ | ❌ | ❌ 예외 전파 | ❌ | 예외 전파 |
| `news/api/views.py` (keyword 분석) | Gemini | ❌ | ❌ | ❌ | ⚠️ null | ❌ | **JSON 무방비** |
| `news/services/keyword_extractor.py` | Gemini | ✅ regex 복구 | ❌ | ❌ | ✅ FALLBACK | ❌ | Celery 블로킹 |
| `news/services/news_deep_analyzer.py` | Gemini | ✅ | ❌ | ❌ | ✅ None | ❌ | **배치 장기 블로킹** |
| `news/services/stock_insights.py` | Gemini | ✅ regex 복구 | ❌ | ❌ | ✅ 진행 | ❌ | 부분 |
| `sec_pipeline/intelligence.py` | Gemini | ✅ | ❌ | ❌ | ✅ 기본 dict | ❌ | graceful |
| `sec_pipeline/extractor.py` | Gemini | ✅ | ❌ | ❌ | ✅ 빈 dict | ❌ | graceful |
| `validation/services/llm_peer_filter.py` | Gemini | ✅ | ❌ | ❌ | ✅ error dict | ❌ | graceful |
| `marketpulse/briefing/client.py` | Gemini | ⚠️ text만 | (CB) | ❌ | ❌ | ✅ gemini | 예외 전파 |
| `portfolio/llm/client.py` | Gemini+Anthropic | ✅ 분류 | ✅ 1회+폴백 | ❌ | ✅ 반대 provider | ❌ | **가장 견고** |
| `sec_pipeline/collector.py` | SEC EDGAR | ✅ | ❌ | ✅ 30/60s | ✅ edgartools | ❌ | 부분 중단 |
| `serverless/services/neo4j_chain_sight_service.py` | Neo4j | ✅ is_available | ❌ | ✅ 2s | ✅ 빈 데이터 | ✅ | **완전 graceful** |
| 전역 캐시 (`django.core.cache`) | Redis | ⚠️ 산발 | ❌ | ❌ 기본 | ⚠️ rate_limiter만 | (CB가 의존) | 🔴 **SPOF** |

> 범례: ✅ 적절 / ⚠️ 부분·주의 / ❌ 없음 / (코어)=하위 클라이언트가 처리 / (하위)=provider가 처리

---

## 2. FMP 상세

### 2.1 코어 클라이언트 — 우수 (`api_request/providers/fmp/client.py`)

`_make_request`(`client.py:80-161`)는 모범적이다:

- **상태코드 세분화**: 401→`FMPAuthError`, 402→`FMPPremiumError`, 403→`FMPAuthError`, 429→`FMPRateLimitError` (`client.py:126-133`)
- **재시도 정책**: 재시도 불필요 에러(Premium/Auth/RateLimit)는 즉시 전파, 네트워크 에러만 exponential backoff 3회 (`client.py:149-159`)
- **rate limiting**: `request_delay=0.2초` 자동 sleep + `daily_limit=10000` 카운터 (`client.py:101-112`)
- **timeout**: 30초 고정 (`client.py:121`)

> ⚠️ 단, `daily_calls` 카운터는 **프로세스 메모리 기반**이라 워커별로 독립적이다. 다중 Celery 워커 환경에서 실제 일일 호출량은 `워커 수 × 10000`까지 누적 가능 → 한도 보호가 환상일 수 있음.

### 2.2 별도 클라이언트 — `serverless/services/fmp_client.py` (httpx)

코어와 별개의 FMP 클라이언트가 존재한다. `httpx.Client.get`(`fmp_client.py:73`) 사용. **429 상태를 명시적으로 처리하지 않고** `raise_for_status()` → 모든 에러가 `FMPAPIError`로 일괄 처리된다. timeout 명시 미확인. 코어 클라이언트의 세분화 로직을 재사용하지 못하는 중복 구현.

### 2.3 전체 파이프라인 중단 위험 (CRITICAL)

| 위치 | 문제 | 영향 |
|------|------|------|
| `serverless/services/market_breadth_service.py:139-141` | `FMPAPIError` raise로 전체 중단 | 시장 폭 지표 일일 동기화 전면 실패 |
| `serverless/services/enhanced_screener_service.py:183-190` | `FMPAPIError` 관통 | 펀더멘탈 스크리너 전체 조회 불가 |
| `stocks/services/sp500_eod_service.py:139-140` | `FMPAPIError` raise | EOD 가격 동기화 섹터 단위 중단 |

### 2.4 침묵 실패 위험 (HIGH)

- `news/providers/fmp.py:52-54` — 예외 catch 후 `[]` 반환: **"API 장애로 뉴스 못 가져옴"과 "실제 뉴스 없음"을 구분 불가**.
- `serverless/services/data_sync.py:87` — 실패 시 `errors += 1`만 기록 후 continue, 원인 미분류.
- `thesis/tasks/eod_pipeline.py:144-149` — `FMPPremiumError`/`FMPClientError`를 `(None, None)`으로 흡수: 지표값 None이 데이터 부재인지 장애인지 모호.

### 2.5 FMPPremiumError(402) 처리 현황

코어에서 `FMPPremiumError`로 분류는 되지만, 호출부에서 **개별 처리하는 곳은 `thesis/tasks/eod_pipeline.py:144`뿐**이다. CLAUDE.md 버그 #23(`.` 포함 심볼 배치 제외)이 적용된 위치를 추가 검증 권장.

---

## 3. Gemini 상세

### 3.1 모범 사례 (참조 기준)

- **`rag_analysis/services/llm_service.py`** — `get_circuit('gemini_rag')` + RETRY_DELAYS[1,2,4] + 429/quota 문자열 매칭 재시도 + `CircuitBreakerError` 시 사용자 친화 메시지(`llm_service.py:236-243`). prompt injection 방어(닫는 태그 escape, `llm_service.py:178-192`)까지 포함.
- **`portfolio/llm/client.py`** — Gemini+Anthropic **듀얼 provider**. 예외 분류기(`client.py:62-80`) + RateLimit/Timeout만 1회 재시도 + 반대 provider 자동 폴백 + 비용 가드. 전 호출부 중 가장 견고.

### 3.2 공통 결함

| 결함 | 영향 범위 | 심각도 |
|------|----------|:---:|
| **HTTP timeout 전무** | 조사한 25곳 전부 `http_options(timeout)` 미설정 | 🔴 |
| **429 재시도 부재** | `llm_service.py`/`portfolio` 제외 거의 전부 | 🟡 |
| **Circuit Breaker 미적용** | 25곳 중 22곳 미적용 | 🟡 |

### 3.3 JSON 파싱 무방비 / None 전파 (HIGH)

| 위치 | 문제 |
|------|------|
| `news/api/views.py:817` 부근 | `response.text.strip()` 직접 반환, JSON 파싱·검증 없음 → FE 파싱 오류 유발 |
| `thesis/services/prompt_builder.py:588, 984` | 파싱 실패 시 `None` 반환 → 호출자가 dict처럼 쓰면 `NoneType` 에러 |
| `marketpulse/briefing/client.py:59` 부근 | `response.text` 존재만 확인, JSON 파싱 생략 |
| `stocks/services/korean_overview_service.py` | `json.loads` 성공 가정, 실패 시 예외 전파 |

> 다수 파일은 코드펜스 제거 + `json.loads` try/except + regex 복구를 갖춰 양호하나(`keyword_extractor.py`, `entity_extractor.py`, `sec_pipeline/*`), 위 4곳은 무방비.

### 3.4 Celery 워커 장기 블로킹 (HIGH)

- `news/services/news_deep_analyzer.py:82-103` — Celery 배치가 기사 50개를 루프 돌며 매 반복 동기 `generate_content()` 호출 + RPM 지연. **최악 약 50×4초 = 200초 워커 점유**. timeout이 없어 한 건이 hang하면 전체 배치가 무한 정지.
- `news/services/keyword_extractor.py:130` — Celery 태스크 내 동기 호출(버그 #8 패턴은 아니나 장기 점유).

> CLAUDE.md 버그 #8("Celery에서 async LLM 호출 금지")의 명백한 위반은 발견되지 않았다(대부분 동기 API 사용). 단, `serverless/services/keyword_generator_v2.py:383-422`의 Celery sync wrapper에서 `run_until_complete()` 사용은 워커가 이미 event loop 컨텍스트일 경우 충돌 가능성 → 검증 권장.

---

## 4. 기타 의존성

### 4.1 FRED API — ✅ 안정적

`macro/services/fred_client.py`: timeout 30초(`:103`) + 3회 exponential backoff(2/4/6초, `:120-121`) + **에러 분류**(Permanent 401/403/404 vs Transient 500-504, `:106-128`) + rate limiter(100/min). 단일 지표 실패 시 해당 지표만 누락하고 전체 응답은 200 반환(부분 graceful). 가장 정교한 클라이언트 중 하나.

### 4.2 Neo4j — ✅ 안정적 (완전 graceful degradation)

`rag_analysis/services/neo4j_driver.py:19-67`의 lazy singleton이 연결 실패 시 `_driver=None`으로 두고 앱은 계속 실행. `serverless/services/neo4j_chain_sight_service.py`의 모든 쿼리 메서드가 `is_available()` 선검사 후 안전 기본값 반환:

- `get_related_stocks()` → `[]` (`:372-373`)
- `get_n_depth_graph()` → `{"nodes": [], "edges": []}` (`:472`)
- `sync_from_postgres()` → `{'synced': 0, 'failed': 0}` (`:589`)

QUERY_TIMEOUT 2초(`neo4j_service.py:30`) + CB 적용. **Neo4j가 죽어도 그래프 기능만 비활성화되고 나머지 서비스는 정상.**

### 4.3 SEC EDGAR — ⚠️ 부분 중단 가능

`sec_pipeline/collector.py`: rate limit 0.12초 sleep(10 req/sec 준수, `:83,130,151`) + User-Agent 헤더(`:29-32`) + timeout 30/60초(`:86,154`). **단, 재시도 로직이 없다** — `raise_for_status()` 즉시 전파(`:87,155`). 섹션 추출 실패 시 edgartools 폴백 시도(`:189-215`)는 있으나, 메타데이터·HTML fetch 실패는 즉시 파이프라인 중단. SEC 일시 장애에 취약.

### 4.4 Redis — 🔴 단일 장애점 (SPOF)

**확정 사실** (`config/settings.py:499-504`):
```python
CACHES = {'default': {
    'BACKEND': 'django.core.cache.backends.redis.RedisCache',   # Django native (NOT django-redis)
    'LOCATION': 'redis://127.0.0.1:6379/1',
}}
```

- Django **native** RedisCache 백엔드 → `IGNORE_EXCEPTIONS` 옵션 미지원. Redis 다운 시 `cache.get/set`이 **예외를 던진다**.
- **복합 위험**: 두 Circuit Breaker(`marketpulse/utils/circuit_breaker.py:36-84`, `news/services/circuit_breaker.py`) 모두 상태를 `django.core.cache`(=Redis)에 저장. **Redis가 죽으면 장애 방어 장치인 CB 자체가 예외를 던지거나 무력화**된다.
  - 단, `news/services/circuit_breaker.py`는 `record_failure/success`를 try/except로 감싸 캐시 예외를 삼킴(`:47-48,54-55`) → CB가 항상 CLOSED로 동작(차단 불가).
- graceful fallback이 구현된 곳은 `api_request/rate_limiter.py:133-139`(Django 캐시 폴백)뿐. `macro/views.py`의 sync 등 다수 `cache.set` 호출은 무방비.
- `CHANNEL_LAYERS`(`settings.py:508-515`)와 Celery broker도 동일 Redis 인스턴스 의존 → WebSocket·비동기 태스크 전면 영향.

> **Redis = 캐시 + Celery 브로커 + Channels + CB 상태저장소 = 4중 SPOF.** 가장 시급한 개선 대상.

---

## 5. Circuit Breaker 후보 (도입/확대 우선순위)

### 5.1 현재 CB 적용 현황

| 이름 | 위치 | 임계/복구 |
|------|------|----------|
| `gemini_rag` | rag_analysis/llm_service.py | 5회 / 60s |
| `gemini_compress` | rag_analysis/context_compressor.py | 5회 / 60s |
| `gemini_thesis` | thesis/services/thesis_builder.py | 5회 / 120s |
| `fmp_news` | marketpulse/services/news_aggregator.py | (기본) |
| (sp500) | stocks/services/sp500_service.py | 3회 / 300s |
| (eod) | stocks/services/sp500_eod_service.py | 10회 |
| neo4j | serverless/neo4j_chain_sight_service.py | (적용) |

### 5.2 신규/확대 후보 (장애 시 영향 큰 순)

| 우선 | 대상 | 이유 |
|:---:|------|------|
| **P0** | **Redis 자체 (CB 백엔드 이전 또는 IGNORE_EXCEPTIONS 대체)** | CB가 Redis에 의존 → Redis 장애 시 전 시스템 cascade. CB 상태를 메모리/DB 폴백으로 이중화하거나 `django-redis` + `IGNORE_EXCEPTIONS=True`로 전환 검토 |
| **P0** | `serverless/enhanced_screener_service.py`, `market_breadth_service.py` | FMP 장애 시 전체 기능 중단. CB로 빠른 실패 + 캐시 폴백 |
| **P1** | Gemini 호출 통합 (코어 wrapper 단일화) | 25곳 중 22곳 CB·timeout 부재. 단일 `genai` 래퍼로 CB+timeout+429 재시도 일원화 |
| **P1** | `serverless/services/fmp_client.py` (httpx 중복 클라이언트) | 코어 클라이언트로 통합하거나 동일 에러 분류 적용 |
| **P2** | SEC EDGAR (`sec_pipeline/collector.py`) | 재시도 부재 + SEC 일시 장애 취약. CB + 백오프 재시도 |
| **P2** | 두 CB 구현 통합 | `marketpulse/utils`(tenacity, HALF_OPEN 지원)로 일원화, `news/services` 단순 구현 폐기 |

---

## 6. 권고 요약 (우선순위)

**P0 (시스템 전면 영향)**
1. Redis SPOF 완화 — `django-redis` + `IGNORE_EXCEPTIONS=True` 전환 또는 CB 상태 저장소를 메모리/DB로 이중화.
2. FMP 전체 중단 지점(screener, market_breadth)에 CB + 캐시 폴백 추가.
3. `news/api/views.py:817`·`thesis/prompt_builder.py:588,984` JSON/None 처리 보강.

**P1 (운영 안정성)**
4. Gemini 호출 단일 래퍼화 → timeout(30s) + 429 재시도 + CB 일괄 적용.
5. `news_deep_analyzer.py` Celery 배치 timeout·부분 실패 격리.
6. FMP 클라이언트 이중 구현(`serverless/fmp_client.py`) 통합.

**P2 (기술 부채)**
7. CB 구현 2종 통합(`marketpulse/utils`로 표준화).
8. SEC EDGAR 재시도 로직 추가.
9. FMP `daily_calls` 카운터의 워커별 분산 문제(공유 카운터로 이전) 검토.

---

### 부록: 검증된 근거 위치

- 코어 FMP 에러 분류: `api_request/providers/fmp/client.py:126-159`
- 코어 Gemini CB+재시도: `rag_analysis/services/llm_service.py:198-272`
- CB 구현 A (tenacity/HALF_OPEN): `marketpulse/utils/circuit_breaker.py:34-159`
- CB 구현 B (단순 INCR, 예외 삼킴): `news/services/circuit_breaker.py:33-55`
- Redis native 백엔드: `config/settings.py:499-504`
- Neo4j graceful: `serverless/services/neo4j_chain_sight_service.py:372-589`
- FRED 에러 분류: `macro/services/fred_client.py:103-128`
- SEC EDGAR rate limit/timeout: `sec_pipeline/collector.py:83-155`
- portfolio 듀얼 provider 폴백: `portfolio/llm/client.py:62-80`
