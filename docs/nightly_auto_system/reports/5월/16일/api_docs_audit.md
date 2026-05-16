# API 문서 감사 보고서

- 감사 일자: 2026-05-16
- 대상 브랜치: `slice8`
- 작업 모드: 읽기 전용 (코드/설정 변경 없음)
- 근거 파일: `pyproject.toml`, `config/settings.py`, `config/urls.py`, 각 앱의 `urls.py`

---

## 1. 현재 상태

### 1.1 의존성 — 이미 설치 완료

| 패키지 | 버전 | 위치 |
|---|---|---|
| `drf-spectacular` | `^0.29.0` | `pyproject.toml:38` |
| `drf-spectacular-sidecar` | `^2026.4.14` | `pyproject.toml:39` |

> Swagger/OpenAPI 자동 생성을 위한 **모든 패키지는 이미 설치/잠금되어 있다**. 신규 의존성 추가 작업은 불필요.

### 1.2 Django 설정 — Market Pulse v2 중심으로 부분 적용

- `INSTALLED_APPS`에 등록됨 (`config/settings.py:205-206`)
  - `drf_spectacular`
  - `drf_spectacular_sidecar`
- `REST_FRAMEWORK.DEFAULT_SCHEMA_CLASS` = `'drf_spectacular.openapi.AutoSchema'` (`settings.py:363`)
- `SPECTACULAR_SETTINGS` 정의됨 (`settings.py:370-`)
  - `TITLE`: "Stock-Vis Market Pulse v2 API" → **v2 전용 타이틀**
  - `SCHEMA_PATH_PREFIX`: `r'/api/v[12]'` → v1/v2 모두 노출 가능하도록 정규식 설정
  - `DISABLE_ERRORS_AND_WARNINGS`: **`True`** → graceful fallback에 의존, v1 endpoint는 schema가 string body로 노출됨
  - `ENUM_NAME_OVERRIDES`: thesis/news/chainsight enum 충돌 해소
- 공개 엔드포인트 (`config/urls.py:57-68`)
  - `/api/v2/schema/` (OpenAPI JSON/YAML)
  - `/api/v2/swagger/` (Swagger UI)
  - `/api/v2/redoc/` (ReDoc)
  - **주의**: 경로가 `/api/v2/`로 prefix되어 있지만 `SCHEMA_PATH_PREFIX`는 v1까지 포함하므로 실제 노출 범위는 v1+v2 전체.

### 1.3 @extend_schema 적용 현황

| 분류 | 파일 수 | 데코레이터 횟수 |
|---|---:|---:|
| `@extend_schema` 사용 파일 | 12 | 31 |
| `class …View(Set)` 정의 파일 | 17 | 111 (클래스) |

> 약 **80개 ViewSet/APIView가 명시적 `@extend_schema` 없이** AutoSchema 추론만으로 노출되고 있다. `DISABLE_ERRORS_AND_WARNINGS=True` 때문에 spec 생성은 깨지지 않지만, 요청/응답 본문은 `string` 또는 빈 schema로 떨어진다.

### 1.4 자동 생성 가능 여부 — 결론

| 항목 | 상태 |
|---|---|
| 패키지 설치 | ✅ 완료 |
| Settings 등록 | ✅ 완료 |
| Schema/Swagger/ReDoc 라우팅 | ✅ 완료 (`/api/v2/swagger/` 진입 시 동작) |
| v2 (marketpulse) endpoint schema | ✅ `@extend_schema` 적용됨 |
| v1 endpoint schema 품질 | ⚠️ 대부분 graceful fallback (string body) |
| 정식 운영용 문서로 사용 가능 여부 | ❌ v1 영역이 미흡, 추가 작업 필요 |

---

## 2. 엔드포인트 목록 (앱별)

> 카운트는 `urls.py`의 `path()` 항목 + `DefaultRouter`로 자동 생성되는 표준 6개 action(`list`, `create`, `retrieve`, `update`, `partial_update`, `destroy`) + 명시된 `@action`을 합산해 추정한 값이다. router 자동 action은 ★로 표기.

### 2.1 전체 요약 테이블

| 앱 (prefix) | 명시 path | router 자동/추가 | 합계 (추정) | `@extend_schema` | 파일 |
|---|---:|---:|---:|---:|---|
| **users** (`/api/v1/users/`) | 35 | 0 | 35 | 2 | `users/urls.py` |
| **stocks** (`/api/v1/stocks/`) | 39 | 0 | 39 | 0 | `stocks/urls.py` (8 views 모듈) |
| **news** (`/api/v1/news/`) | 0 | 6+ ★ | 6+ | 2 | `news/api/urls.py` (router 1) |
| **macro** (`/api/v1/macro/`) | 10 | 0 | 10 | 0 | `macro/urls.py` |
| **rag_analysis** (`/api/v1/rag/`) | 15 | 0 | 15 | 2 | `rag_analysis/urls.py` |
| **serverless** (`/api/v1/serverless/`) | 64 | 0 | 64 | 6 | `serverless/urls.py` |
| **thesis** (`/api/v1/thesis/`) | 8 | ~18 ★ (3 router) | ~26 | 0 | `thesis/urls.py` |
| **validation** (`/api/v1/validation/`) | 6 | 0 | 6 | 0 | `validation/api/urls.py` |
| **chainsight** (`/api/v1/chainsight/`) | 7 | ~6 ★ (1 router) | ~13 | 7 | `chainsight/api/urls.py` |
| **sec_pipeline** (`/api/v1/sec-pipeline/`) | 2 | 0 | 2 | 0 | `sec_pipeline/urls.py` |
| **api_request** (`/api/v1/`) | 6 | 0 | 6 | 5 | `api_request/urls.py` |
| **portfolio** (`/api/`) | 5 | 0 | 5 | 0 | `portfolio/urls.py` |
| **marketpulse v2** (`/api/v2/market-pulse/`) | 5 | 0 | 5 | 5 | `marketpulse/api/urls.py` |
| **config root** (`/`) | 2 (root, health) | 0 | 2 | 2 | `config/urls.py` |
| **합계** | **204** | **~30** | **~234** | **31** | — |

### 2.2 앱별 상세

#### users — 35 (`users/urls.py`)
- JWT 인증: 7 — `jwt/{signup,login,logout,refresh,verify,change-password,profile}/`
- 세션 인증 (호환): 6 — `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/`
- 즐겨찾기: 3 — `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/`
- 포트폴리오: 9 — `portfolio/`, `summary/`, `table/`, `refresh/`, `<pk>/`, `<pk>/quick-update/`, `symbol/<symbol>/`, `symbol/<symbol>/refresh/`, `symbol/<symbol>/status/`
- 관심사: 2 — `interests/`, `interests/<pk>/`
- 워치리스트: 8 — `watchlist/`, `<pk>/`, `<pk>/add-stock/`, `<pk>/bulk-add/`, `<pk>/bulk-remove/`, `<pk>/stocks/`, `<pk>/stocks/<symbol>/`, `<pk>/stocks/<symbol>/remove/`

#### stocks — 39 (`stocks/urls.py`, 8개 views 모듈)
- 메인 페이지: 3 (`dashboard`, `stock_detail`, `search`)
- 탭 데이터: 6 (`chart`, `overview`, `balance-sheet`, `income-statement`, `cashflow`, `sync`)
- MVP: 4 (`mvp/stocks/`, `mvp/stock/<symbol>/`, `mvp/rag/<symbol>/`, `mvp/sectors/`)
- 기술적 지표: 3 (`indicators/<symbol>/`, `signal/<symbol>/`, `indicators/compare/`)
- 검색: 3 (`search/symbols/`, `search/validate/<symbol>/`, `search/popular/`)
- Market Movers: 1
- Fundamentals: 5 (`key-metrics`, `ratios`, `dcf`, `rating`, `all`)
- Screener: 6 (`/`, `large-cap`, `high-dividend`, `sector/<sector>`, `low-beta`, `exchange/<exchange>`)
- Exchange Quotes: 5 (`index`, `<symbol>`, `batch`, `major-indices`, `sector-performance`)
- EOD Dashboard: 3 (`dashboard`, `signal/<id>`, `pipeline/status`)

#### news — 6+ (`news/api/urls.py`)
- `NewsViewSet` 1개 (router 자동: list, create, retrieve, update, partial_update, destroy)
- 추가 `@action` 개수는 views 본문 확인 필요(본 감사 범위 외).

#### macro — 10 (`macro/urls.py`)
- `pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis — 15 (`rag_analysis/urls.py`)
- DataBasket: 6 (`baskets/`, `<pk>/`, `<pk>/add-item/`, `<pk>/add-stock-data/`, `<pk>/items/<item_id>/`, `<pk>/clear/`)
- AnalysisSession: 4 (`sessions/`, `<pk>/`, `<pk>/messages/`, `<pk>/chat/stream/`)
- Monitoring: 5 (`usage`, `cost`, `cache`, `history`, `pricing`)

#### serverless — 64 (`serverless/urls.py`)
- Admin Dashboard: 12
- Market Movers: 4 (`movers`, `movers/<symbol>`, `sync`, `sync-now`)
- Keywords: 4
- Market Breadth: 3
- Sector Heatmap: 3
- Screener Presets: 7
- Screener Filters: 1
- Advanced Screener: 1
- Alerts: 6
- Investment Thesis: 4
- ETF Holdings (Phase 3): 9
- LLM Relations (Phase 5): 4
- Institutional Holdings (Phase 7): 3
- Regulatory: 1
- Patent Network: 1
- Health: 1

> `serverless/views.py`에 `@function-based view` 52건 + 명시 클래스 다수 → 단일 앱이지만 endpoint 수가 가장 많다.

#### thesis — ~26 (`thesis/urls.py`)
- 명시 path: 8 (`conversation/start/`, `conversation/respond/`, `conversation/news-issues/`, `conversation/suggest/`, `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<indicator_id>/readings/`, `alerts/`, `alerts/<aid>/read/`)
- 3 routers: `ThesisViewSet`, `ThesisPremiseViewSet`, `ThesisIndicatorViewSet` (각각 router 자동 ~6개 = ~18)

#### validation — 6 (`validation/api/urls.py`)
- `<symbol>/summary/`, `<symbol>/metrics/`, `<symbol>/leader-comparison/`, `<symbol>/presets/`, `<symbol>/peer-preference/`, `<symbol>/llm-filter/`

#### chainsight — ~13 (`chainsight/api/urls.py`)
- 명시 path: 7 (`seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`, `<symbol>/neighbors/`, `<symbol>/graph/`, `<symbol>/suggestions/`)
- 1 router: `WatchlistViewSet` (~6)

#### sec_pipeline — 2 (`sec_pipeline/urls.py`)
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request — 6 (`api_request/urls.py`) — Provider Admin
- `health/` + 5 admin (`providers/status`, `providers/rate-limits`, `providers/cache`, `providers/test`, `providers/config`)

#### portfolio (Portfolio Coach) — 5 (`portfolio/urls.py`)
- `coach/e1/garp/`, `coach/e2/diagnostic-card/`, `coach/e3/metric-comment/`, `coach/e5/adjustment/`, `coach/e6/comparison/`
- 함수형 뷰 5개 (`portfolio/views.py`)

#### marketpulse v2 — 5 (`marketpulse/api/urls.py`)
- `overview`, `cards/<card_id>/detail`, `news/refresh`, `i18n`, `health`
- **이 앱은 모든 view에 `@extend_schema` 적용됨** (5/5)

#### config root — 2 (`config/urls.py`)
- `/` (`api_root`), `/health/` (`health_check`) — 둘 다 `@extend_schema` 데코레이터 미적용 추정 (별도 확인 필요)

---

## 3. 도입 작업 목록

### 3.1 Step 1 — 설정 정비 (0.5 day)

| 작업 | 위치 | 비고 |
|---|---|---|
| `SPECTACULAR_SETTINGS.TITLE` 갱신 | `config/settings.py:371` | "Market Pulse v2" → "Stock-Vis API" (v1 + v2 통합 타이틀) |
| `SPECTACULAR_SETTINGS.DESCRIPTION` 갱신 | `config/settings.py:372` | v1 영역 (stocks/users/news/thesis/…) 설명 추가 |
| `DISABLE_ERRORS_AND_WARNINGS` 검토 | `config/settings.py:390` | 점진 정상화 후 `False`로 복귀 |
| `TAGS` 확장 | `config/settings.py:383` | 앱별 태그 14개 추가 (Users, Stocks, News, Macro, RAG, Serverless, Thesis, Validation, ChainSight, SEC, Portfolio, MarketPulse v2, Admin, Health) |
| 라우팅 추가 (선택) | `config/urls.py:58-68` | `/api/v1/{schema,swagger,redoc}/`도 추가해 v1 전용 문서 노출 가능 |
| `apivirtual` 권한 검토 | `SpectacularSwaggerView` | 현재 default permission `IsAuthenticated` → schema 페이지 접근에 인증 필요 여부 결정 |

### 3.2 Step 2 — `@extend_schema` 적용 (8–12 day)

**규모**: 약 80개 ViewSet/APIView + 함수형 뷰 60개 ≒ **140개 endpoint에 데코레이터 추가** 필요.

| 앱 | view 클래스 | `@extend_schema` 적용됨 | 신규 작업 endpoint | 우선순위 |
|---|---:|---:|---:|---|
| users | 18 | 2 | 16 | High (인증/포트폴리오 — 외부 노출) |
| stocks | 36 (8 모듈) | 0 | 36 | High (메인 도메인) |
| serverless | 12 클래스 + 52 함수 | 6 | 58 | High (가장 큰 앱) |
| thesis | 다수 ViewSet | 0 | ~26 | High (운영 중인 핵심 기능) |
| chainsight | 7 | 7 | 0 | ✅ 완료 |
| marketpulse v2 | 5 | 5 | 0 | ✅ 완료 |
| macro | 10 | 0 | 10 | Medium |
| rag_analysis | 15 | 2 | 13 | Medium |
| validation | 6 | 0 | 6 | Medium |
| api_request | (함수형) | 5 | 1 | Low (admin only) |
| news | 1 + actions | 2 | ~4 | Medium |
| sec_pipeline | 1 + 함수 1 | 0 | 2 | Low |
| portfolio | (함수형 5) | 0 | 5 | Low (Slice 작업 중) |
| **합계** | **~120** | **31** | **~140** | — |

**작업 단위 추정**
- ViewSet 1개: 평균 30~60 LOC schema (request/response serializer 매핑) → 약 0.5h
- 함수형 view 1개: 약 0.3h
- 총 작업량: `(120 × 0.5h) + (60 × 0.3h) ≒ 78시간` ≒ 1인 기준 **약 10일** (8h/day)
- 직렬화기(Serializer) 이미 존재하는 비율에 따라 단축 가능 (현재 stocks/users/rag_analysis는 Serializer 다수 보유)

**선결 조건**
- Serializer 누락 ViewSet은 inline schema 작성 또는 dict 응답을 `OpenApiTypes.OBJECT`로 우회 — 우회는 spec 품질 저하 요인. **Serializer 보강을 먼저 권장**.
- 에러 envelope (`config.exception_handler.custom_exception_handler`, `settings.py:366`)에 맞춘 공통 error response 컴포넌트 정의 필요.

### 3.3 Step 3 — 검증 및 CI 통합 (1 day)

| 작업 | 비고 |
|---|---|
| `python manage.py spectacular --validate` 통과 | 현재는 `DISABLE_ERRORS_AND_WARNINGS=True`로 우회 중 |
| `--fail-on-warn` 옵션을 CI에 통합 | 회귀 방지 |
| Swagger UI 화면 캡처 + ReDoc snapshot 테스트 추가 (선택) | `tests/test_openapi.py` 신설 |
| Contract 동기화 | `contracts/` 디렉토리에 spec dump → frontend 타입 생성 파이프라인 연결 검토 |

### 3.4 Step 4 — 산출물 정착 (0.5 day)

- `docs/api/openapi.yaml` 자동 export (Celery beat 또는 makefile)
- `frontend/lib/api/types.ts` 자동 생성 (`openapi-typescript` 등 도입 여부 결정 → 별도 의사결정 필요)
- README 갱신 — `/api/v2/swagger/` 진입 경로 안내

### 3.5 종합 작업량

| 단계 | 인일 | 비고 |
|---|---:|---|
| Step 1: 설정 정비 | 0.5 | 단독 가능 |
| Step 2: `@extend_schema` 적용 | 10 | 앱별 병렬화 가능 (backend 멀티에이전트 4분할 시 ~2.5일) |
| Step 3: 검증 + CI | 1 | qa-architect 에이전트 협업 |
| Step 4: 산출물 정착 | 0.5 | infra 에이전트 협업 |
| **합계** | **~12 인일** | 병렬화 시 ~4 인일까지 단축 가능 |

---

## 4. 핵심 발견 사항

1. **`drf-spectacular`는 이미 설치/설정/라우팅까지 완료**되어 있다. "도입"이 아니라 "전면 적용"이 정확한 표현.
2. v2 (marketpulse) 영역은 schema 품질이 양호하나, **v1 약 200개 endpoint는 `DISABLE_ERRORS_AND_WARNINGS=True`로 graceful fallback에 의존** 중. 외부 공개용 문서로 사용하기엔 한계.
3. 가장 큰 작업 부담은 `serverless` 앱 (64 endpoint, 함수형 52개 포함) — 단일 앱이 전체 작업량의 약 40%.
4. `thesis` 앱은 router 기반 자동 action이 많아 `@extend_schema_view`로 일괄 처리하면 효율적.
5. Schema가 그럴듯하게 자동 생성되더라도, **`POST` body의 request serializer를 누락한 ViewSet은 `null` request로 표시**되므로 Serializer 보강이 선결 작업.

---

## 5. 권고 진행 순서

1. (Step 1) 설정 정비 + 태그/타이틀 통합 → v1/v2 동시 노출.
2. (Step 2-High) `serverless` + `stocks` + `users` + `thesis` 4개 앱을 backend 에이전트 병렬로 처리.
3. (Step 2-Medium) `macro`, `rag_analysis`, `validation`, `news` 후속 처리.
4. (Step 3) `DISABLE_ERRORS_AND_WARNINGS=False`로 전환 후 CI에서 회귀 차단.
5. (Step 4) `contracts/` 자동 export + frontend 타입 생성 검토.

> **본 보고서는 읽기 전용 감사**이며, 코드/설정/문서 어떤 파일도 수정하지 않았다.
