# 야간 자동화 시스템 커버리지 분석

생성일: 2026-04-18
분석 대상: `/Users/byeongjinjeong/Desktop/stock_vis` 코드베이스
야간 시스템 경로: `~/stock-vis-nightly/`

---

## 1. 코드베이스 전체 맵

### Python 백엔드

| 항목 | 수치 |
|------|------|
| 전체 .py 파일 (migrations, __pycache__ 제외) | 554개 |
| 소스 .py 파일 (tests/ 제외) | 432개 |
| 소스 총 라인 수 | 107,649줄 |
| 테스트 .py 파일 | 121개 |
| 테스트 함수 수 (def test_) | 2,005개 |

### TypeScript 프론트엔드

| 항목 | 수치 |
|------|------|
| 전체 .ts/.tsx 파일 (node_modules, .next 제외) | 326개 |
| 총 라인 수 | 51,800줄 |
| 테스트 파일 수 (frontend/__tests__/) | 12개 |
| 테스트 케이스 수 (it/test 함수) | 44개 |

### Django 앱별 Python 파일 현황

| 앱 | .py 줄 수 | .py 파일 수 | 주요 서브모듈 |
|----|-----------|-------------|--------------|
| stocks | 12,916 | 46 | services/17, views/9, tasks/1, consumers/1 |
| serverless | 28,059 | 54 | services/40, views/2, tasks/1 |
| rag_analysis | 14,610 | 44 | services/22, views/1, tasks/1, signals/1 |
| news | 12,706 | 35 | services/18, views/2, tasks/1 |
| thesis | 8,655 | 49 | services/21, views/3, tasks/1 |
| api_request | 7,052 | 21 | providers/fmp+av, clients, rate_limiter |
| chainsight | 4,336 | 44 | services/4, tasks/8, views/1 |
| sec_pipeline | 3,797 | 31 | collector, extractor, normalizer, tasks/1 |
| validation | 3,442 | 28 | services/10, views/2, tasks/1 |
| macro | 3,502 | 16 | services/4, views/1, tasks/1 |
| users | 2,820 | 12 | views/1, tasks/1, serializers, jwt_views |
| graph_analysis | 1,270 | 9 | services/2, models, views |
| metrics | 1,055 | 15 | services/2, models/4, views/1 |
| config | 1,938 | 11 | celery, settings, views |

### 프론트엔드 컴포넌트별 현황

| 디렉토리 | .ts/.tsx 줄 수 | 파일 수 |
|----------|----------------|---------|
| components/admin | 3,847 | 25 |
| components/news | 4,168 | 24 |
| components/thesis | 2,751 | 41 |
| components/screener | 2,744 | 12 |
| components/chainsight | 2,082 | 14 |
| components/portfolio | 1,541 | 6 |
| components/rag | 1,546 | 12 |
| components/eod | 1,259 | 12 |
| components/common | 1,330 | 6 |
| components/validation | 972 | 9 |
| components/watchlist | 941 | 5 |
| components/market-pulse | 1,064 | 5 |
| components/financial | 787 | 4 |
| components/macro | 747 | 5 |
| components/stock | 1,102 | 2 |
| components/layout | 419 | 3 |
| components/strategy | 349 | 1 |
| components/charts | 288 | 1 |
| components/keywords | 241 | 2 |
| components/stocks | 214 | 2 |
| components/auth | 48 | 1 |
| components/market | 134 | 1 |

---

## 2. 야간 시스템 커버 매트릭스

야간 시스템 구성:
- **Tier 1** (매일 실행): TS 컴파일 에러 수정, 깨진 테스트 수정, FE 타입 안전성, Dead code 정리
- **Tier 2 BE** (테스트 작성): validation, sec_pipeline, users, rag_analysis
- **Tier 2 FE** (테스트 작성): thesis 컴포넌트, validation+chainsight 컴포넌트
- **Tier 3** (감사 보고서): API 성능, 보안, FMP/Gemini 장애대응, 데이터 무결성, Beat 스케줄, API 문서, 카탈로그 동기화

### 백엔드 앱별 커버 매트릭스

| 앱 | .py 줄 수 | Tier1 Dead code 대상 | Tier2 테스트 작성 | Tier3 감사 대상 | 현재 테스트 수 | 커버 안 되는 영역 |
|----|-----------|---------------------|------------------|----------------|---------------|-----------------|
| stocks | 12,916 | N | N | 성능(N+1)/보안/FMP/무결성 | 124 (unit) + 별도 | tasks.py, consumers.py, signals 없음 |
| serverless | 28,059 | N | N | 성능/보안/FMP/무결성/카탈로그 | 410 (tests/) | 40개 서비스 파일 중 대부분 Tier2 미포함 |
| rag_analysis | 14,610 | N | Y (35개 목표) | 보안/Gemini | 83 (unit, Neo4j-free만) | 18개 서비스 중 4개만 테스트 (Neo4j 의존 14개 사각지대) |
| news | 12,706 | N | N | 보안/FMP/무결성 | 141 (unit) + 600 (tests/) | tasks.py, signals 없음, ML 파이프라인 |
| thesis | 8,655 | Y (Dead code) | N | 카탈로그 동기화 | 134 (unit) | tasks/eod_pipeline.py, views/ 3개 |
| api_request | 7,052 | N | N | FMP/보안 | 12 (sec_edgar만) | fmp/client.py, fmp/processor.py, rate_limiter.py |
| chainsight | 4,336 | Y (Dead code) | N (FE만) | 무결성/보안 | 0 (별도 unit 없음) | tasks/ 8개 파일, services/ 4개 |
| sec_pipeline | 3,797 | Y (Dead code) | Y (30개 목표) | 무결성/보안 | 90 (unit) | signals.py |
| validation | 3,442 | Y (Dead code) | Y (40개 목표) | 성능/보안 | 106 (unit) | tasks.py |
| macro | 3,502 | N | N | Beat 스케줄 | 31 (unit) | services/ 4개 파일 (FRED 호출 포함) |
| users | 2,820 | N | Y (25개 목표) | 보안 | 55 (unit) + 27 (tests/) | tasks.py (캐시 무효화) |
| graph_analysis | 1,270 | N | N | N | 0 | 전체 미커버 (services/2, views/1) |
| metrics | 1,055 | N | N | N | 116 (unit) | views.py, services/ |
| config | 1,938 | N | N | Beat 스케줄 | 0 | tasks.py, views.py |

범례: Y = 대상 포함, N = 대상 아님

### 프론트엔드 컴포넌트별 커버 매트릭스

| 컴포넌트 디렉토리 | .ts/.tsx 줄 수 | Tier1 TS 컴파일 | Tier2 테스트 작성 | 현재 테스트 수 | 갭 |
|-----------------|----------------|----------------|-----------------|---------------|-----|
| components/thesis | 2,751 | Y (전체 대상) | Y (15개 목표) | 5개 파일 / 테스트 있음 | dashboard 일부만, builder/alerts/close/indicators 미커버 |
| components/validation | 972 | Y | Y (18개 목표, chainsight와 공유) | 3개 파일 | MetricCard, PeerContextBar, SignalSummaryCard만 |
| components/chainsight | 2,082 | Y | Y (18개 목표, validation과 공유) | 3개 파일 | GraphCanvas, NodeDetailPanel, RelationCardPanel만 |
| components/admin | 3,847 | Y | N | 0 | 전체 미커버 |
| components/news | 4,168 | Y | N | 0 | 전체 미커버 |
| components/screener | 2,744 | Y | N | 0 | 전체 미커버 |
| components/portfolio | 1,541 | Y | N | 0 | 전체 미커버 |
| components/rag | 1,546 | Y | N | 0 | 전체 미커버 |
| components/eod | 1,259 | Y | N | 0 | 전체 미커버 |
| components/common | 1,330 | Y | N | 0 | 전체 미커버 |
| components/watchlist | 941 | Y | N | 0 | 전체 미커버 |
| components/market-pulse | 1,064 | Y | N | 0 | 전체 미커버 |
| components/financial | 787 | Y | N | 0 | 전체 미커버 |
| components/macro | 747 | Y | N | 0 | 전체 미커버 |
| components/stock | 1,102 | Y | N | 0 | 전체 미커버 |
| components/layout | 419 | Y | N | 0 | 전체 미커버 |
| components/strategy | 349 | Y | N | 0 | 전체 미커버 |
| components/charts | 288 | Y | N | 0 | 전체 미커버 |
| components/keywords | 241 | Y | N | 0 | 전체 미커버 |
| components/stocks | 214 | Y | N | 0 | 전체 미커버 |
| components/auth | 48 | Y | N | 0 | 전체 미커버 |
| components/market | 134 | Y | N | 0 | 전체 미커버 |

---

## 3. 갭 분석

### 3-1. Tier 1 갭: pytest/tsc에 포함되지 않는 코드 영역

**Dead code 정리 대상 (Tier 1 작업 8)**: validation, chainsight, sec_pipeline, thesis, macro
- stocks, serverless, rag_analysis, news, api_request, users, graph_analysis, metrics, config는 Dead code 스캔 대상에서 제외됨

**FE 타입 안전성 (Tier 1 작업 7)**: `npx tsc --noEmit` 전체 실행이므로 모든 프론트엔드 파일이 컴파일 검증 대상
- 단, TS 에러가 0이 되더라도 런타임 동작 오류는 탐지 불가

**깨진 테스트 수정 (Tier 1 작업 2)**: 특정 테스트 파일 2개(news, serverless)만 명시적 대상
- 다른 앱의 새로운 테스트 실패는 `pytest tests/ -x -q` regression으로만 탐지

### 3-2. Tier 2 갭: 테스트 0개인데 Tier 2 대상에도 없는 앱

| 앱 | 현재 테스트 상태 | Tier2 포함 여부 | 우선순위 |
|----|----------------|----------------|---------|
| graph_analysis | 0개 (tests.py 빈 파일) | 미포함 | HIGH - 서비스 2개, 상관관계 계산 로직 |
| chainsight (BE) | 0개 (별도 unit 없음, tests.py 빈 파일) | 미포함 (FE만 포함) | HIGH - tasks 8개 파일, Neo4j 동기화 |
| config | 0개 | 미포함 | MED - celery.py beat 설정, tasks.py |
| api_request (심층) | 12개 (sec_edgar만) | 미포함 | HIGH - fmp/client.py, rate_limiter.py (핵심 로직) |
| metrics (BE) | 116개 있으나 views/services 미커버 | 미포함 | LOW - 규모 소형 |

**완전 테스트 커버리지가 없는 파일 유형 (모든 앱에서)**:
- `tasks.py` 파일: stocks, config, macro, news, rag_analysis, serverless, thesis(eod_pipeline), users, validation
  - 유일 예외: `tests/unit/macro/test_tasks.py` 존재
- `signals.py` 파일: rag_analysis/signals.py, sec_pipeline/signals.py
- `consumers.py`: stocks/consumers.py (WebSocket 컨슈머)

### 3-3. Tier 3 갭: 감사 대상에서 빠진 파일

**성능 감사(작업15) 대상 뷰 파일 17개 중 누락**:
- `thesis/views/thesis_views.py`, `thesis/views/conversation_views.py`, `thesis/views/monitoring_views.py`
- `metrics/views.py`
- `api_request/admin_views.py`

**성능 감사 모델 인덱스 검사 대상 누락**:
- `thesis/models/` (6개 파일), `validation/models` (미확인), `chainsight/models/` (10개 파일), `macro/models` (미확인)

**보안 감사(작업16) Gemini 프롬프트 인젝션 검사 대상 29개 중 누락 예상**:
- `validation/services/` 하위 10개 파일
- `chainsight/` 내 Gemini 호출 여부 미확인

**데이터 무결성 감사(작업14)** 언급된 7개 파일에서 누락:
- `thesis/models/` (6개 파일) — CASCADE FK 존재 가능
- `validation/models` — 미포함
- `chainsight/models/` — 10개 파일 있으나 SET_NULL/CASCADE 미언급

**Beat 스케줄 감사(작업6)** 커버 범위:
- `config/celery.py`만 분석 대상
- 앱별 `tasks.py` 내 `apply_async` / `delay` 호출로 동적 스케줄링되는 케이스 미탐지

**API 문서 감사(작업20) 엔드포인트 목록 언급 앱 10개 외 누락**:
- `api_request/urls.py` (어드민/관리용 엔드포인트)
- `chainsight/api/urls.py` (체인사이트 API)

**카탈로그 동기화 감사(작업10)**:
- `thesis/services/indicator_scorer.py`의 점수 계산 로직 vs 카탈로그 일치 여부 미검사
- `thesis/services/keyword_collectors/` 3개 파일의 키워드-지표 매핑 미검사

### 3-4. 요일별 심층 분석에서 한번도 언급되지 않는 앱/모듈

야간 시스템 v2 설계 문서(`/Users/byeongjinjeong/Desktop/stock_vis/docs/infra/` — v2 파일 없음, v3 버전 존재)의 요일별 분석과 별개로, 현재 4개 스크립트에서 **단 한번도 명시적으로 언급되지 않는** 앱:

| 앱/모듈 | 4개 스크립트 내 언급 | 이유 |
|--------|--------------------|----|
| graph_analysis | 없음 | API 미구현, 사실상 휴면 상태 |
| api_request (심층) | 없음 | 인프라 레이어로 취급, 직접 테스트 미포함 |
| config/tasks.py | 없음 | 모니터링 태스크, 별도 관리 |
| stocks/consumers.py | 없음 | WebSocket, pytest로 테스트 어려움 |
| antigravity/ | 없음 | 프로젝트 외부 앱 |
| shared_kb/ | 없음 | 야간 시스템 범위 외 |
| scripts/ | 없음 | 수동 유틸리티 |

---

## 4. 커버리지 점수

### 4-1. Python 백엔드 커버리지

#### 파일 단위 커버리지

| 구분 | 수치 |
|------|------|
| 전체 소스 .py 파일 (tests 제외) | 432개 |
| 야간 시스템이 **직접 테스트 작성 대상**으로 지정한 앱 파일 수 | ~145개 (validation 28 + sec_pipeline 31 + users 12 + rag_analysis 44개 중 Neo4j-free ~4개 = 79개) |
| Tier 3 감사가 **읽는** 파일 수 (뷰 17 + 모델 7 + LLM 29 + FMP 35 + 기타) | ~88개 |
| 기존 테스트가 존재하는 앱 파일 수 (stocks, news, serverless, thesis, macro, metrics, rag_analysis, sec_pipeline, validation, users, api_request/providers) | ~280개 |
| **야간 시스템이 커버하는 파일 수 (추정)** | **~240개** |
| **파일 단위 커버리지** | **약 56%** |

#### 앱 단위 커버리지

| 구분 | 수치 |
|------|------|
| 전체 주요 앱 수 | 14개 (stocks, users, news, macro, graph_analysis, rag_analysis, serverless, thesis, metrics, validation, chainsight, sec_pipeline, api_request, config) |
| 야간 시스템이 최소 1개 Tier에서 **의미있게 커버**하는 앱 | 11개 (graph_analysis, config 제외) |
| **앱 단위 커버리지** | **79% (11/14)** |

### 4-2. TypeScript 프론트엔드 커버리지

| 구분 | 수치 |
|------|------|
| 전체 FE 소스 파일 수 (node_modules, .next 제외) | 326개 |
| Tier 1 TS 컴파일 대상 (전체) | 326개 |
| Tier 2 FE 테스트 작성 대상 컴포넌트 수 | 11개 (thesis 5 + validation 3 + chainsight 3) |
| 전체 컴포넌트 파일 수 | ~160개 |
| **컴포넌트 테스트 커버리지** | **7% (11/160)** |

### 4-3. 종합 커버리지

| 측면 | 커버리지 |
|------|---------|
| BE 앱 단위 (야간 시스템 언급 기준) | 79% (11/14) |
| BE 파일 단위 (테스트 존재 기준) | 약 56% |
| BE 테스트 함수 (2,005개 / 소스 432파일) | 2,005개 — 앱당 평균 143개 |
| FE 컴파일 검증 (tsc --noEmit) | 100% (전체 파일) |
| FE 컴포넌트 테스트 (vitest) | 7% (11/160) |
| **종합 커버리지 (가중 평균)** | **약 47%** |

---

## 5. 핵심 사각지대 요약

### Critical (야간 시스템이 전혀 닿지 않는 영역)

1. **graph_analysis 앱 전체** — services/correlation_calculator.py, services/anomaly_detector.py, views.py 모두 테스트 0개, Tier3 감사 미포함
2. **chainsight BE tasks 8개 파일** — Neo4j 동기화, 프로파일 생성, 관계 디스커버리 등 핵심 비동기 파이프라인 무테스트
3. **stocks/consumers.py** — WebSocket 실시간 주가 스트리밍 컨슈머 무테스트
4. **rag_analysis 18개 서비스 중 14개 (Neo4j 의존)** — pipeline.py, pipeline_v2.py, neo4j_service.py, semantic_cache.py 등 RAG 핵심 로직

### High (Tier 2/3에서 부분 커버하나 심각한 갭)

5. **api_request/providers/fmp/ 핵심 파일** — fmp/client.py (FMP API 호출 진입점), fmp/processor.py, rate_limiter.py가 Tier2 대상에서 제외 (tests/api_request/에 12개 tests있으나 sec_edgar만 커버)
6. **모든 앱의 tasks.py** — Celery 태스크 (비동기 파이프라인)는 9개 앱에 존재하나 macro의 test_tasks.py 1개 외 전부 미커버
7. **FE 컴포넌트 admin/news/screener/portfolio/rag/eod** — 총 약 17,000줄 규모의 컴포넌트가 Tier2 테스트 대상에서 완전히 누락

### Medium (Tier3 감사에서 부분 커버하나 개선 필요)

8. **thesis/views/ 3개 파일** — Tier3 성능/보안 감사의 17개 뷰 파일 목록에서 누락
9. **chainsight/models/ 10개 파일** — 데이터 무결성 감사에서 SET_NULL/CASCADE 분석 대상 미포함
10. **validation/tasks.py, signals/ 파일들** — Tier2에서 서비스만 테스트, 태스크/시그널 미포함
