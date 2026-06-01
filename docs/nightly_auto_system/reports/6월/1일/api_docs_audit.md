# API 문서 감사 보고서

> 작성일: 2026-06-01 · 모드: **읽기 전용 감사 (코드 수정 없음)**
> 대상: Stock-Vis Django REST Framework 백엔드
> 디렉토리 기준: `packages/shared/`, `apps/`, `services/`, `thesis/`, `integrations/` (서비스 리모델링 후 구조)

---

## 핵심 결론 (TL;DR)

1. **drf-spectacular는 이미 설치·운영 중**이다 (`0.29.0` + sidecar). Swagger / ReDoc / OpenAPI 스펙 엔드포인트가 살아 있다. → **"도입"이 아니라 "커버리지 확대"가 과제다.**
2. 현재 `@extend_schema` 데코레이터는 **총 37개**만 적용되어 있고, **Market Pulse v2 / Chain Sight / api_request admin** 등 일부 영역에 집중되어 있다.
3. 설정에 `DISABLE_ERRORS_AND_WARNINGS = True`가 걸려 있어, 데코레이터가 없는 v1 엔드포인트는 **graceful fallback (string body)** 로 스펙에 노출된다 → 스키마는 생성되지만 **요청/응답 구조가 부정확**하다.
4. 미커버 핵심 앱: **stocks, macro(market_pulse v1), thesis, validation, sec_pipeline** (모두 `@extend_schema` 0개).

---

## 1. 현재 상태

### 1-1. 문서화 패키지 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | ✅ 설치됨 `^0.29.0` | `pyproject.toml:38`, `poetry.lock:1073` |
| `drf-spectacular-sidecar` | ✅ 설치됨 `^2026.4.14` | `pyproject.toml:39`, `poetry.lock:1096` |
| `drf-yasg` | ❌ 미사용 | 검색 결과 없음 |

→ **drf-spectacular 단일 스택**. drf-yasg와의 혼용 없음 (정상).

### 1-2. Swagger / OpenAPI 자동 생성 가능 여부

✅ **가능하며 이미 라우팅되어 있음** (`config/urls.py:61-72`)

| 경로 | 뷰 | 용도 |
|------|-----|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 스펙 (YAML/JSON) |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc UI |

### 1-3. SPECTACULAR_SETTINGS 현황 (`config/settings.py:377`)

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'Stock-Vis Market Pulse v2 API',          # ⚠️ 제목이 v2 전용으로 한정됨
    'VERSION': '2.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_DIST': 'SIDECAR',                        # 오프라인 sidecar 사용
    'REDOC_DIST': 'SIDECAR',
    'SCHEMA_PATH_PREFIX': r'/api/v[12]',                # v1 + v2 모두 스캔 대상
    'DISABLE_ERRORS_AND_WARNINGS': True,                # ⚠️ fallback noise 억제
    'ENUM_NAME_OVERRIDES': { ... },                     # enum collision 해결 (thesis/news 등)
}
```

**주목할 설정 2가지:**
- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` → v1/v2 **모든** 엔드포인트가 스펙에 포함된다. 즉 데코레이터가 없어도 스펙에는 뜨지만 본체가 부정확.
- `DISABLE_ERRORS_AND_WARNINGS = True` → "unable to guess serializer" 류 경고가 **숨겨진다**. 커버리지 미흡을 정량 추적하기 어려운 상태. (설정 주석에도 "핵심 영역만 명시적 처리, 나머지는 graceful fallback" 명시)

### 1-4. `@extend_schema` 적용 현황 (총 37개)

| 파일 | 데코레이터 수 | 비고 |
|------|:---:|------|
| `apps/chain_sight/api/views.py` | 7 | ✅ 잘 커버됨 |
| `services/serverless/views.py` | 6 | 부분 (64 엔드포인트 중 6) |
| `packages/shared/api_request/admin_views.py` | 5 | Provider Admin |
| `apps/market_pulse/api/views/*.py` (v2, 5파일) | 각 1~ | ✅ v2 핵심 |
| `packages/shared/users/views.py` | 2 | 부분 (35 중 2) |
| `services/rag_analysis/views.py` | 2 | 부분 (15 중 2) |
| `services/news/api/views.py` | 2 | 부분 (32 중 2) |
| `apps/portfolio/api/views.py` | 적용됨 | coach e1~e6 |
| **`packages/shared/stocks/views*.py` (9파일)** | **0** | ❌ 전무 |
| **`apps/market_pulse/views.py` (macro v1)** | **0** | ❌ 전무 |
| **`thesis/views/thesis_views.py`** | **0** | ❌ 전무 |
| **`services/validation/api/views.py`** | **0** | ❌ 전무 |
| **`services/sec_pipeline/views.py`** | **0** | ❌ 전무 |

---

## 2. 엔드포인트 목록 (앱별)

> URL 패턴 수 기준. ViewSet은 라우터 자동 생성 경로(list/retrieve/create/update/destroy) + `@action` 커스텀 경로를 합산. `config/urls.py` 마운트 prefix 표기.

### 2-1. 앱별 집계 (사용자 지정 10개 앱)

| 앱 | 마운트 prefix | 엔드포인트 수 | 뷰 형태 | `@extend_schema` 커버 | 커버리지 |
|----|--------------|:---:|--------|:---:|:---:|
| **stocks** | `/api/v1/stocks/` | **39** (HTML 페이지 2 포함, API 37) | APIView (9 views_*.py 분할) | 0 | 🔴 0% |
| **users** | `/api/v1/users/` | **35** | APIView + JWT | 2 | 🟡 ~6% |
| **news** | `/api/v1/news/` | **~32** (ViewSet list/retrieve 2 + @action 30) | ReadOnlyModelViewSet | 2 | 🟡 낮음 |
| **macro** (market_pulse v1) | `/api/v1/macro/` | **10** | APIView | 0 | 🔴 0% |
| **rag_analysis** | `/api/v1/rag/` | **15** | APIView | 2 | 🟡 ~13% |
| **serverless** | `/api/v1/serverless/` | **64** | 함수형 뷰 + Admin APIView | 6 | 🟡 ~9% |
| **thesis** | `/api/v1/thesis/` | **11 명시 + ViewSet 3종** | ModelViewSet ×3 (router) | 0 | 🔴 0% |
| **validation** | `/api/v1/validation/` | **6** | APIView | 0 | 🔴 0% |
| **chainsight** | `/api/v1/chainsight/` | **7 + WatchlistViewSet (6+5)** | APIView + ModelViewSet | 7 | 🟢 양호 |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | **2** | 함수형 + APIView | 0 | 🔴 0% |

> ⚠️ `CLAUDE.md`의 앱 표(stocks/, users/ 최상위)와 **실제 디렉토리(packages/shared/stocks/ 등)** 가 다름. 서비스 리모델링 진행 중이라 문서-구조 불일치 존재 → 문서 갱신 권장.

### 2-2. 참고: 감사 범위 밖이지만 스펙에 포함되는 추가 경로

| 앱 | 마운트 prefix | 엔드포인트 수 |
|----|--------------|:---:|
| api_request (Provider Admin) | `/api/v1/` | 6 |
| portfolio coach (DRF) | `/api/v1/coach/` | 6 (e1~e6) |
| market_pulse v2 | `/api/v2/market-pulse/` | 5 |
| iron_trading (외부 봇 read-only) | `/api/v1/iron-trading/` | 2 |

### 2-3. 주요 엔드포인트 상세 (앱별 발췌)

**stocks** (`packages/shared/stocks/urls.py`) — 9개 views 파일로 분할
- 페이지: `` (대시보드), `stock/<symbol>/` (상세) — HTML 뷰
- 차트/탭: `api/chart|overview|balance-sheet|income-statement|cashflow/<symbol>/`
- 동기화: `api/sync/<symbol>/`
- MVP: `api/mvp/stocks|stock|rag|sectors/`
- 지표: `api/indicators|signal/<symbol>/`, `api/indicators/compare/`
- 검색: `api/search/symbols|validate|popular/`
- Market Movers: `api/market-movers/`
- Fundamentals: `api/fundamentals/key-metrics|ratios|dcf|rating|all/<symbol>/`
- Screener: `api/screener/` 외 6종 (large-cap, high-dividend, sector, low-beta, exchange)
- Quotes: `api/quotes/index|<symbol>|batch|major-indices|sector-performance/`
- EOD: `eod/dashboard/`, `eod/signal/<id>/`, `eod/pipeline/status/`

**users** (`packages/shared/users/urls.py`)
- JWT: `jwt/signup|login|logout|refresh|verify|change-password|profile/`
- 세션 인증(레거시): `me/`, `login/`, `logout/`, `change_password/` 등
- 즐겨찾기: `favorites/`, `favorites/add|remove/<id>/`
- 포트폴리오: `portfolio/` 외 9종
- 관심사/Watchlist: `interests/`, `watchlist/` 외 8종

**news** (`services/news/api/urls.py`) — `NewsViewSet` (ReadOnlyModelViewSet, router 등록)
- 기본: list `/`, retrieve `/<pk>/`
- @action 30개: `stock/<symbol>`, `stock-sentiment`, `market`, `trending`, `all`, `sources`, `daily-keywords`, `daily-keywords/generate`, `keyword-detail`, `insights`, `market-feed`, `interest-options`, `personalized-feed`, `news-events`, `news-events/impact-map`, `ml-status`, `ml-shadow-report` 등

**macro** (`apps/market_pulse/urls.py`)
- `pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

**rag_analysis** (`services/rag_analysis/urls.py`)
- DataBasket: `baskets/` 외 6종
- AnalysisSession: `sessions/` 외 3종 (chat/stream SSE 포함)
- Monitoring: `monitoring/usage|cost|cache|history|pricing/`

**serverless** (`services/serverless/urls.py`) — 64개, 최대 규모
- Admin Dashboard 12종, Market Movers/Keywords 8종, Market Breadth 3종, Sector Heatmap 3종, Screener Presets 8종, Alerts 7종, Thesis 4종, ETF Holdings 9종, LLM Relations 4종, Institutional 3종, Regulatory/Patent 2종, Health 1종

**thesis** (`thesis/urls.py`) — DRF router 기반
- 명시 path 11개: `conversation/start|respond|news-issues|suggest/`, `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<id>/readings/`, `alerts/`, `alerts/<aid>/read/`
- Nested router: `<thesis_id>/premises/` (`ThesisPremiseViewSet`, ModelViewSet)
- Nested router: `<thesis_id>/indicators/` (`ThesisIndicatorViewSet`, ModelViewSet + @action)
- Main router: `ThesisViewSet` (ModelViewSet + @action 1)

**validation** (`services/validation/api/urls.py`)
- `<symbol>/summary|metrics|leader-comparison|presets|peer-preference|llm-filter/`

**chainsight** (`apps/chain_sight/api/urls.py`)
- `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`, `<symbol>/neighbors|graph|suggestions/`
- `WatchlistViewSet` (ModelViewSet 6 routes + @action 5)

**sec_pipeline** (`services/sec_pipeline/urls.py`)
- `admin/dashboard/`, `filing/<symbol>/`

---

## 3. 도입 작업 목록

> 패키지/URL은 이미 갖춰져 있으므로, 본 섹션은 **"문서화 도입"이 아닌 "스키마 커버리지 확대 + 정합화"** 작업이다.

### 3-1. 기반 정비 (선행, 소규모)

| # | 작업 | 대상 파일 | 예상량 |
|---|------|----------|:---:|
| B-1 | `TITLE`/`DESCRIPTION`을 v2 전용 → 전체 API로 일반화 | `config/settings.py:378` | 5분 |
| B-2 | `TAGS`에 앱별 그룹(Stocks, Users, News, Macro, RAG, Serverless, Thesis, Validation, ChainSight, SEC) 추가 | `config/settings.py` | 30분 |
| B-3 | `DISABLE_ERRORS_AND_WARNINGS`를 임시 `False`로 켜고 경고 수 측정 → 커버리지 baseline 확보 (감사용, 운영 복원) | `config/settings.py:397` | 15분 |
| B-4 | 스펙 생성 검증: `python manage.py spectacular --file /tmp/schema.yaml` 무오류 확인 | (커맨드) | 5분 |

### 3-2. 데코레이터 추가 범위 (앱별)

각 APIView/ViewSet에 `@extend_schema(responses=..., request=..., summary=..., tags=[...])` 추가. **Serializer가 이미 있는 앱은 빠르게, 없는 앱(함수형/dict 응답)은 inline serializer 또는 `OpenApiResponse` 정의 필요.**

| 우선순위 | 앱 | 미커버 엔드포인트 | 난이도 | 비고 |
|:---:|----|:---:|:---:|------|
| 🔴 P1 | **stocks** | ~37 | 중 | 9개 views 파일, Serializer 일부 존재. HTML 페이지 2개는 스키마 제외(`exclude`) |
| 🔴 P1 | **serverless** | ~58 | 높음 | 함수형 뷰 다수 → dict 응답, inline serializer 필요. 최대 공수 |
| 🔴 P1 | **thesis** | ViewSet 3종 + 11 path | 중 | ModelViewSet은 serializer 연결되어 자동 추론 유리. action만 보강 |
| 🟡 P2 | **users** | ~33 | 중 | JWT 뷰는 simplejwt 기본, 커스텀 뷰 위주 보강 |
| 🟡 P2 | **news** | ~30 action | 중 | ReadOnlyModelViewSet, action 응답 dict 위주 |
| 🟡 P2 | **macro** | 10 | 낮음 | APIView 소수, dict 응답 |
| 🟡 P2 | **rag_analysis** | ~13 | 중 | SSE(ChatStream)는 `@extend_schema(exclude)` 또는 별도 처리 |
| 🟢 P3 | **validation** | 6 | 낮음 | 소규모, symbol path param 문서화 |
| 🟢 P3 | **sec_pipeline** | 2 | 낮음 | 소규모 |
| ✅ — | **chainsight** | 0 (7 완료) | — | WatchlistViewSet action 5개만 점검 |

### 3-3. 공통 처리 항목 (주의 필요)

| 항목 | 대상 | 처리 |
|------|------|------|
| **SSE 스트리밍** | `rag_analysis: sessions/<pk>/chat/stream/` | `@extend_schema(exclude=True)` 또는 text/event-stream 명시 |
| **HTML 페이지 뷰** | `stocks: ''`, `stock/<symbol>/` | `@extend_schema(exclude=True)` (API 아님) |
| **함수형 뷰 다수** | serverless 58개 | `@extend_schema` + `inline_serializer` 또는 응답 직렬화기 신설 |
| **path param 문서화** | `<symbol>`, `<uuid:thesis_id>` 등 | `@extend_schema(parameters=[OpenApiParameter(...)])` |
| **레거시 세션 인증 뷰** | users `me/`, `login/` 등 | 폐기 예정이면 `exclude`, 유지면 문서화 |

### 3-4. 예상 작업량 총괄

| 구간 | 작업 | 예상 공수 |
|------|------|:---:|
| 기반 정비 (B-1~B-4) | 설정 일반화 + baseline 측정 | **~1시간** |
| P1 (stocks/serverless/thesis) | ~106 엔드포인트, 함수형 뷰 serializer 신설 포함 | **3~4일** |
| P2 (users/news/macro/rag) | ~86 엔드포인트 | **2~3일** |
| P3 (validation/sec_pipeline) | ~8 엔드포인트 | **0.5일** |
| QA/검증 | 스펙 무오류 + Swagger UI 수동 확인 + `DISABLE_ERRORS_AND_WARNINGS` 복원 | **0.5일** |
| **합계** | 전체 ~290+ 엔드포인트 | **약 6~8 작업일** |

> 단계적 접근 권장: **P1 stocks 1개 앱을 파일럿**으로 먼저 완료해 패턴(inline serializer, tags, exclude 규칙)을 확정한 뒤 나머지에 적용하면 공수 압축 가능.

---

## 부록 A. 감사 방법 (재현용)

```bash
# urls.py / views.py 인벤토리
find . -name 'urls.py' -not -path '*migrations*' -not -path '*__pycache__*'
find . -name 'views*.py' -not -path '*migrations*' -not -path '*__pycache__*'

# 패키지 설치 확인
grep -n "drf-spectacular\|drf-yasg" pyproject.toml poetry.lock

# extend_schema 커버리지
grep -rn "@extend_schema" --include="*.py" . | grep -v migrations | wc -l

# 앱별 path 카운트
grep -c 'path(' <urls.py>
```

## 부록 B. 발견된 부수 이슈 (감사 범위 외, 참고)

1. **문서-구조 불일치**: `CLAUDE.md` 앱 표는 `stocks/`, `users/` 최상위 기준이나 실제는 `packages/shared/`, `apps/`, `services/` 로 이전됨. 리모델링 완료 시 `CLAUDE.md` 갱신 필요.
2. **`apps/portfolio/urls.py` path 카운트 0**: `path(` 매칭이 0이나 coach 라우팅은 `apps/portfolio/api/urls.py`에 별도 존재 — 순수 Django view 경로 패턴 확인 권장.
3. **SCHEMA 버전 명**: `VERSION='2.0'`, `TITLE`이 "Market Pulse v2"로 한정 → v1 다수 엔드포인트가 한 스펙에 섞여 있어 사용자 혼란 소지.

---

*본 보고서는 읽기 전용 감사이며 어떠한 소스 코드도 수정하지 않았습니다.*
