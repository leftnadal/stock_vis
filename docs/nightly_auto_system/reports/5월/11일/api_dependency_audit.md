# 외부 API 의존성 감사 보고서

**작성일**: 2026-05-11
**범위**: FMP (38개 파일), Gemini (40개 파일), FRED, Neo4j, SEC EDGAR, Redis
**조사 방식**: 읽기 전용 (코드 수정 없음)
**작성자**: nightly_auto_system 감사 파이프라인

---

## Executive Summary

| 의존성 | 도입 위치 수 | 회복 성숙도 | Circuit Breaker | 주요 위험 |
|--------|-------------|------------|-----------------|---------|
| FMP    | 38 파일 / 80+ 호출점 | ★★☆☆☆ | 부분 (2곳) | 402/429 처리 산재, ThreadPool 병렬화 시 rate limit 우회 |
| Gemini | 40 파일 / 60+ 호출점 | ★★★☆☆ | ✗ | Celery 내 async 호출 잔존 (Bug #8), 명시적 timeout 부재 |
| FRED   | 4 파일 | ★★★★☆ | ✗ | 장애 시 기본값(VIX=20)이 사용자에게 거짓 신호 |
| Neo4j  | 30+ 파일 | ★★★☆☆ | ✗ | PostgreSQL 폴백 미구현, 다운 시 Chain Sight 전체 공란 |
| SEC EDGAR | 11 파일 | ★★☆☆☆ | ✗ | 429 재시도 1회 한정, 10-K 다운 시 supply chain 정지 |
| Redis  | 캐시 인프라 | ★★★★☆ | N/A | 다운 시 메모리 폴백 (비영구) → 분산 일관성 깨짐 |

**P0 (즉시 조치 필요)**: FMP ThreadPoolExecutor 동시성 제한, Gemini Celery 내 async 호출 제거, Neo4j 폴백 경로 설계
**P1 (다음 sprint)**: Circuit Breaker 표준화, 429/402 처리 정책 단일화, Gemini timeout 30초 적용
**P2 (개선 큐)**: TTL 정책 통일, FRED 폴백값 → 명시적 stale 표시, SEC EDGAR exponential backoff

---

## 1. 의존성 매트릭스

### 1.1 서비스 × 외부 API 의존도

| 서비스/도메인 | FMP | Gemini | FRED | Neo4j | SEC EDGAR | Redis | Fallback |
|--------------|-----|--------|------|-------|-----------|-------|----------|
| stocks (시세, 재무) | ◉ | ○ | - | - | - | △ | ✗ |
| serverless/data_sync (Market Movers) | ◉ | - | - | - | - | ◉ | △ Circuit Breaker |
| serverless/screener | ◉ | ○ | - | △ | - | ◉ | △ 빈 결과 반환 |
| serverless/keyword_data_collector | ◉ | ◉ | - | - | - | ◉ | ✗ |
| serverless/chain_sight (LLM/ETF) | ◉ | ◉ | - | ◉ | △ | ◉ | △ 빈 데이터 |
| macro/Market Pulse | △ | - | ◉ | - | - | ◉ | ◎ 기본값 반환 |
| news/Intelligence Pipeline v3 | △ | ◉ | - | △ | - | ◉ | △ 부분 |
| rag_analysis (RAG 분석) | - | ◉ | - | ◉ | - | ◉ | △ truncate 폴백 |
| thesis/Builder + 관제실 | ◉ | ◉ | - | - | - | ◉ | △ create_fallback_thesis |
| sec_pipeline | - | ◉ | - | - | ◉ | △ | ✗ |
| validation/Peer 비교 | △ | ◉ | - | - | - | ◉ | △ |
| chainsight (v2 프로파일) | △ | △ | - | ◉ | △ | ◉ | ✗ |

범례: ◉ 핵심 의존, ○ 일반 사용, △ 보조적 사용, - 무관, ✓ 양호, ✗ 미흡

### 1.2 사용자 차단 경로 (P0 영향) 매핑

| 사용자 동선 | 핵심 의존성 | 다운 시 결과 |
|------------|-------------|-------------|
| 종목 상세 → 재무제표 탭 | FMP balance-sheet | 페이지 로드 실패 (402 BRK.B 등) |
| 메인 → Market Movers | FMP gainers/losers | 공란 또는 stale (>24h) |
| 메인 → Market Pulse | FRED + FMP quote | VIX=20 거짓 기본값 |
| 종목 → Chain Sight | Neo4j + FMP | Cypher fail → 빈 그래프 |
| 가설 빌더 → 대화 | Gemini | 폴백 키워드 3개로 강등 |
| 1차 검증 → LLM Peer 필터 | Gemini | 에러 응답, UI 차단 |

---

## 2. FMP 상세

### 2.1 호출 계층 (2계층 구조)

```
[Layer 1 - 기본 클라이언트]
  api_request/providers/fmp/client.py  ← exponential backoff, 0.2s throttle, FMPPremiumError raise
  api_request/providers/fmp/provider.py ← FMPPremiumError catch, ProviderResponse 추상화

[Layer 2 - 도메인 서비스]
  serverless/services/fmp_client.py    ← httpx 기반 (별도 구현), Circuit Breaker 호출
  stocks/services/sp500_service.py     ← CircuitBreakerError wrap
  serverless/services/data_sync.py     ← CircuitBreakerError + FMPAPIError 분리
  + 20+ 도메인 서비스 (catch 패턴 불일치)
```

**문제**: Layer 1과 Layer 2의 HTTP 클라이언트가 분리되어 있어 (`requests` vs `httpx`) 재시도/throttle 정책이 이중화됨.

### 2.2 에러 핸들링 매트릭스

| 위치 | 에러 catch | 재시도 | 캐시 | FMPPremiumError 처리 |
|------|-----------|--------|------|---------------------|
| `api_request/providers/fmp/client.py:119-161` | HTTPError, RequestException | 3회 exponential | ✗ | `:128-129` 즉시 raise |
| `api_request/providers/fmp/provider.py:247-253` | FMPPremiumError | ✗ | ✗ | `error_code='PREMIUM_ONLY'` 반환 |
| `serverless/services/fmp_client.py` | generic → FMPAPIError | ✗ | TTL 60s~5m | ✗ (raise만) |
| `serverless/services/data_sync.py:74-90` | CircuitBreakerError + FMPAPIError | ✗ | ✓ 5분 | 무음 무시 |
| `serverless/services/keyword_data_collector.py:153` | per-symbol try/except | ✗ | ✓ 1시간 msgpack | ✗ 처리 없음 |
| `serverless/services/sector_heatmap_service.py` | FMPAPIError generic | ✗ | ✓ 5분 | 부분 실패 → 빈 dict |
| `serverless/services/filter_engine.py` | FMPAPIError | ✗ | ✓ 5분 | 빈 리스트 반환 |
| `serverless/services/chain_sight_service.py` | FMPAPIError 로깅만 | ✗ | ✓ 1시간 | 부분 성공 (원본 누락 위험) |
| `stocks/services/sp500_service.py:38-43` | CircuitBreakerError | ✗ | ✗ | ✗ |
| `serverless/tasks.py:17-21,57-60` | FMPAPIError → `self.retry` | Celery max_retries=3, 5분 | ✗ | ✗ |
| `thesis/tasks/eod_pipeline.py:64,75` | Exception generic | ✗ | ✗ | ✗ |
| `macro/services/fmp_client.py` | partial | ✗ | △ quote만 | ✗ |
| `news/providers/fmp.py` | generic | ✗ | ✗ | ✗ |

### 2.3 Rate Limit (FMP Starter 300/min, 10,000/day)

| 패턴 | 위치 | 효과 | 위험 |
|------|------|------|------|
| 고정 sleep 0.2s | `client.py:104-107` | 단일 워커에서 300/min 준수 | 멀티 워커 누적 시 초과 |
| httpx timeout 30s | `serverless/services/fmp_client.py:44` | 적응형 무 | 네트워크 지연 시 무한 누적 |
| **ThreadPoolExecutor(10)** | `keyword_data_collector.py:153` | 병렬 20종목 ~4초 | **🚨 0.2s 딜레이 미적용, 429 위험 즉시 발생** |
| Circuit Breaker | `sp500_service.py`, `data_sync.py` | 장애 전파 차단 | 복구 120-300초 동안 기능 다운 |
| 캐시 TTL | 산재 (60s~24h) | API 호출 감소 | **🚨 정책 통일 없음** |

### 2.4 FMPPremiumError (402) — common-bugs.md #23

- **Raise 지점**: `client.py:129` (HTTP 402 또는 premium subscription 메시지 감지 시)
- **명시적 catch**: `provider.py:247-253` 단 1곳
- **무음 무시**: `data_sync.py`, 나머지 20+ 서비스 → 사용자 페이지에서 "데이터 없음"으로만 표시
- **`.` 포함 심볼 (BRK.B, BF.B 등)**: client.py에서 사전 차단 로직 부재 (감지 후 raise)
- **결과**: 사용자가 BRK.B 재무제표 클릭 → 빈 페이지 → 혼동

### 2.5 장애 영향 범위

**동기 경로 (사용자 차단)**
- `GET /stocks/{symbol}/fundamentals/` → balance-sheet 호출 실패 → 페이지 로드 실패
- 회사 프로필, 스크리너 필터 즉시 영향

**비동기 경로 (조용한 데이터 누락)**
- 매일 18:00 ET Celery Beat → `sync_daily_market_movers` 429 → 다음 날 공란
- Market Movers, 섹터 히트맵, Market Breadth → 사용자가 "왜 데이터가 어제 거지?" 인식 못 함

### 2.6 Top 5 FMP 위험 스팟

| # | 위험 | 위치 | 영향 | 우선순위 |
|---|------|------|------|---------|
| 1 | ThreadPoolExecutor가 0.2s throttle 우회 | `keyword_data_collector.py:153` | 429 → 키워드 데이터 누락 | P0 |
| 2 | 402 처리 정책 불일치 (catch vs 무시) | provider.py / data_sync.py / 기타 | 사용자 혼동, 사일런트 페일 | P0 |
| 3 | api_request 계층 캐시 부재 | `stock_service.py`, `provider.py` | 매번 외부 호출, 일일 한도 빠르게 소진 | P1 |
| 4 | TTL 불일치 (60초~86400초) | 전역 | 일부 데이터 1일 stale | P2 |
| 5 | Celery retry 5분 고정 | `serverless/tasks.py:20` | 429 후 5분 후 재시도 → 추가 429 | P1 |

---

## 3. Gemini 상세

### 3.1 sync vs async 분포 (Bug #8 위반 점검)

| 분류 | 위치 | 환경 | 안전성 |
|------|------|------|--------|
| **async (Celery 외부)** | `rag_analysis/services/llm_service.py:182` (streaming) | WebSocket | ✓ 안전 |
|  | `rag_analysis/services/adaptive_llm_service.py:247,304` | 사용자 요청 | ✓ 안전 |
|  | `serverless/services/keyword_generator.py:247`, `keyword_generator_v2.py:269,304` | 사용자 요청 | ✓ 안전 |
| **🚨 async (Celery 내부)** | `rag_analysis/services/context_compressor.py:134,281` | Celery | ✗ **Bug #8 위반** |
|  | `rag_analysis/services/entity_extractor.py:87` | Celery | ✗ **Bug #8 위반** |
| **sync (Celery 안전)** | `serverless/services/thesis_builder.py:344`, `keyword_service.py:279`, `llm_relation_extractor.py:384`, `relationship_keyword_enricher.py:230` | Celery | ✓ |
|  | `thesis/services/prompt_builder.py:578`, `indicator_matcher.py:226`, `thesis/tasks/summary.py:67` | mixed | ✓ |
|  | `news/services/news_deep_analyzer.py`, `stocks/services/korean_overview_service.py:63` | Celery 배치 | ✓ |
|  | `sec_pipeline/extractor.py:68`, `validation/services/llm_peer_filter.py:79`, `portfolio/llm/client.py:225` | mixed | ✓ |

### 3.2 Rate Limit (Free Tier 15 RPM, 1500 RPD)

| 패턴 | 위치 | 평가 |
|------|------|------|
| 429 감지 + exponential backoff (1s/2s/4s) | `rag_analysis/services/llm_service.py:217-232` | ✓ 정석 |
| 429 감지 + 동적 sleep `(시도+1)*2s` | `serverless/services/keyword_service.py:318-330` | ✓ 양호 |
| 고정 sleep 4s (배치) | `llm_relation_extractor.py:366`, `news_deep_analyzer.py:98`, `relationship_keyword_enricher.py:154`, `korean_overview_service.py:26` | △ 정적, 429 시 인식 X |
| 동시성 5개 제한 | `context_compressor.py` | ✓ |
| 비용 가드 (`_budget_max`) | `portfolio/llm/client.py` | ✓ 유일 |

### 3.3 응답 검증 / JSON 파싱

| 위치 | 검증 | JSON 파싱 |
|------|------|-----------|
| `llm_service.py:190` | `if chunk.text:` ✓ | try/except → 빈 리스트 |
| `keyword_service.py:297` | `hasattr` ✓ | 정규식 `"([^"]+)"` 복구 |
| `thesis_builder.py:369-489` | ✓ | `re.DOTALL` 코드블록 제거 + **잘린 JSON 괄호 수리** (위험) |
| `indicator_matcher.py:226` | △ | `re.search(r'\[.*\]', text, re.DOTALL)` |
| `entity_extractor.py:93,108-113` | ✗ `response.text.strip()` (None 체크 없음) | _fallback_extraction() |
| `csv_url_resolver.py:392` | ✗ | - |
| `conversation_views.py:270,280` | ✓ | json.loads 실패 → fallback_issues() |
| `llm_relation_extractor.py` | ✓ | `_recover_from_partial_json` 정규식 재추출 |

### 3.4 Timeout 설정

| 위치 | timeout | 평가 |
|------|---------|------|
| `csv_url_resolver.py` (httpx) | 30s | ✓ |
| 그 외 (대부분) | **없음 (SDK 기본)** | ✗ 무한 대기 위험 |

### 3.5 모델 선택 / 폴백

```
LLMService (Flash) → 실패 시 스트리밍 중단
ThesisBuilder (Flash) → create_fallback_thesis()
ContextCompressor (Flash) → truncate 폴백
EntityExtractor (Flash) → 정규식 추출
Portfolio (Flash) → Anthropic Sonnet (provider 폴백 유일)
```

### 3.6 장애 영향

**사용자 차단 경로**: 가설 빌더 대화 (`conversation_views.py:270`), LLM Peer 필터 (`validation/llm_peer_filter.py:79`), 투자 테제 생성
**조용한 실패 경로**: 관계 추출(`llm_relation_extractor.py`) → 빈 관계 반환, 뉴스 심층 분석 → `llm_analyzed=False`로만 표시

---

## 4. 기타 의존성

### 4.1 FRED API (macro 도메인)

- **재시도**: `macro/services/fred_client.py:25-26,98-155` — 500/502/503/504 3회 exponential (2s/4s/6s), 401/403/404 즉시 raise
- **Rate Limit**: `api_request/rate_limiter.py:48-49` — 100/min (공식 120 중 안전 마진), 0.6s 간격
- **Graceful Degradation**: `macro_service.py:56-85` — 장애 시 **VIX=20, 스프레드=1.0 기본값 반환** (사용자에게 정상 신호처럼 보임 — 거짓 안심 위험)
- **캐시**: 섹션별 TTL 차등 (실시간 60s, 월간 86400s), 성공만 캐시
- **Celery 재시도**: `macro/tasks.py:14-60` — `countdown=60 * (2 ** retries)` 지수 백오프

**문제**: VIX=20 기본값이 Market Pulse 화면에서 정상 데이터처럼 표시됨. stale/fallback 표시 필요.

### 4.2 Neo4j

- **연결**: `rag_analysis/services/neo4j_driver.py:19-68` — Lazy singleton, 실패 시 None 반환 (앱 중단 X), 풀 최대 50, 획득 timeout 60s
- **Fork 안전성**: `:88-98` `force_reset_after_fork()`, `config/celery.py:36-55` neo4j queue solo pool 격리 (#25 macOS SIGSEGV 대응)
- **쿼리 timeout**: `neo4j_service.py:30,118` 모든 쿼리 2초 timeout
- **캐시**: `neo4j_chain_sight_service.py:73` 5분, `supply_chain_service.py:48` 30일
- **Graceful Degradation**: `neo4j_service.py:57-86` 빈 `_empty_relationships` 반환

**🚨 문제**: PostgreSQL `StockRelationship` 테이블이 존재하지만 Neo4j 다운 시 자동 폴백 미구현. Chain Sight 그래프 완전 공란.

### 4.3 SEC EDGAR

- **Rate Limit**: `api_request/sec_edgar_client.py:99,118-124` — 10 req/sec (100ms 대기)
- **User-Agent**: `:102,108-110` 필수 헤더 (위반 시 차단)
- **429 재시도**: `:162-166` **1회만** (1초 대기) — 부족
- **에러**: 404 → SECEdgarError, Timeout/RequestException 즉시 예외
- **CIK 캐싱**: `:114,200-217` 로컬 dict
- **HTML 파싱**: `:358-390` BeautifulSoup 실패 시 정규식 폴백

**문제**: 10-K 다운로드 실패 시 supply_chain_service.py:98-109에서 에러 반환 → SEC Pipeline 정지. exponential backoff (2s/4s/8s) 필요.

### 4.4 Redis

- **설정**: `config/settings.py:490-495` Django 캐시 DB 1, `config/celery.py:474-475` Celery DB 0 (분리)
- **TTL 차등**: `api_request/cache/decorators.py:20-31` 실시간 300s ~ 7일
- **폴백**: `rate_limiter.py:125-139` Redis 실패 → Django LocMem 메모리 폴백 (비영구)
- **무효화**: `cache/decorators.py:169-183` django_redis SCAN, 미사용 시 경고
- **싱글톤**: `rate_limiter.py:254-270` Provider별 RateLimiter 재사용
- **테스트 격리**: `config/settings_test.py` LocMemCache (#27 운영 Redis flush 대응)

**문제**: Redis 다운 시 메모리 폴백은 분산 워커 간 일관성 깨짐. 캐시 hit rate 모니터링 미흡.

---

## 5. Circuit Breaker 후보

### 5.1 현재 적용 위치 (2곳)

- `stocks/services/sp500_service.py:38-43` — `CircuitBreakerError` wrap (FMP S&P 500 수집)
- `serverless/services/data_sync.py:74-86` — CircuitBreakerError + FMPAPIError 분리 (Market Movers 동기화)

### 5.2 P0 후보 (메인 페이지 차단 + 외부 의존)

| 우선순위 | 호출 지점 | 사유 | 적용 효과 |
|---------|----------|------|----------|
| **P0-1** | `keyword_data_collector.py` FMP ThreadPool | 병렬 호출 → 429 폭발 → 전체 키워드 파이프라인 정지 | 5회 연속 실패 시 1시간 차단 + 캐시된 데이터 사용 |
| **P0-2** | `news/providers/fmp.py` + `news/services/aggregator.py` | 뉴스 수집 실패 → Intelligence Pipeline v3 stale | 차단 시 cached news만 노출 |
| **P0-3** | Gemini → `validation/services/llm_peer_filter.py:79` | 사용자 요청 동기 경로, 429 시 즉시 차단 | 30초 차단 + "AI 필터 일시 중단" UI |
| **P0-4** | Gemini → `thesis/views/conversation_views.py:270` | 가설 빌더 핵심 UX | 차단 시 폴백 흐름 안내 |
| **P0-5** | Neo4j → `serverless/services/neo4j_chain_sight_service.py` | Chain Sight 전체 의존 | 차단 시 PostgreSQL StockRelationship 폴백 |

### 5.3 P1 후보 (백그라운드 + 데이터 손실 위험)

| 우선순위 | 호출 지점 | 사유 |
|---------|----------|------|
| P1-1 | `serverless/services/chain_sight_service.py` FMP | 차단 시 기존 캐시 1시간 연장 |
| P1-2 | `serverless/services/llm_relation_extractor.py` Gemini | 배치 작업 폭발 방지 |
| P1-3 | SEC EDGAR (`sec_pipeline/collector.py`) | 10-K 다운로드 누적 실패 시 차단 |
| P1-4 | `macro/services/fred_client.py` | VIX=20 거짓 폴백 대신 명시적 차단 |
| P1-5 | `serverless/services/sector_heatmap_service.py` FMP | 메인 페이지 보조 |

### 5.4 표준화 권장

현재 `CircuitBreakerError`만 정의되어 있고 정책이 호출자마다 다름. 통일된 정책 예시:
- 임계치: 5회 연속 실패 OR 30초 내 10회 실패
- 차단 기간: P0 = 30초, P1 = 5분, P2 = 30분
- Half-open 시도: 1회 성공 시 복귀
- 알림: P0 차단은 즉시 Slack/로그 알림

---

## 6. 즉시 조치 권고 (PR 분리 가능 단위)

1. **PR-1 (P0)**: Bug #8 위반 제거 — `context_compressor.py:134,281`, `entity_extractor.py:87` async → sync 마이그레이션
2. **PR-2 (P0)**: `keyword_data_collector.py:153` ThreadPoolExecutor에 Semaphore(5) 또는 순차 처리 적용
3. **PR-3 (P0)**: Gemini 클라이언트 전역 timeout 30초 (단일 helper 함수 도입)
4. **PR-4 (P1)**: FMP 402 처리 정책 단일화 — 통합 래퍼 + 차단 심볼 목록 영속화
5. **PR-5 (P1)**: Neo4j → PostgreSQL StockRelationship 자동 폴백 (Chain Sight 서비스)
6. **PR-6 (P1)**: Circuit Breaker 표준화 (5개 P0 후보부터)
7. **PR-7 (P2)**: SEC EDGAR exponential backoff (2s/4s/8s, 3회)
8. **PR-8 (P2)**: FRED 폴백 시 `data_source=fallback` 플래그 → UI에서 "지표 일시 사용 불가" 표시

---

## 7. 모니터링 권고 (코드 수정 없이 가능)

```yaml
즉시 도입 가능 (로그 기반):
  - FMP 응답 코드별 일일 카운터 (402, 429, 5xx)
  - Gemini 429 발생 빈도 + 영향 작업
  - Neo4j _empty_relationships 반환 빈도
  - Circuit Breaker open 이벤트 카운터
  - 캐시 hit rate (Django Redis stats)

알림 임계치:
  - FMP daily call > 8,000 (limit 10,000의 80%)
  - FMP per-minute > 250 (limit 300의 83%)
  - Gemini RPM > 12 (limit 15의 80%)
  - Circuit Breaker open > 5분 지속
  - Neo4j connection failure > 3회/시간
```

---

## 부록 A. 조사 통계

- FMP 호출 파일: 38개 (테스트 제외 23개 핵심)
- Gemini 호출 파일: 40개 (테스트 제외 28개 핵심)
- 검토한 코드 라인: 약 4,500 라인 (3개 병렬 Explore 에이전트 종합)
- 발견된 common-bugs.md 위반: Bug #8 (Celery async LLM) — 2개 파일 잔존
- Circuit Breaker 적용 현황: 2/80+ 호출점 (커버리지 2.5%)

## 부록 B. 참조 문서

- `CLAUDE.md` — 코딩 규칙 및 common-bugs 색인
- `sub_claude_md/coding-rules.md` — Backend 코딩 규칙
- `sub_claude_md/common-bugs.md` — #8 (async LLM), #15 (캐시 키), #23 (FMP 402), #25 (Celery macOS), #27 (Redis flush)
- `DECISIONS.md` — 아키텍처 결정 단일 소스
- `docs/nightly_auto_system/reports/5월/11일/performance_audit.md` — 동일 일자 성능 감사
- `docs/nightly_auto_system/reports/5월/11일/security_audit.md` — 동일 일자 보안 감사
