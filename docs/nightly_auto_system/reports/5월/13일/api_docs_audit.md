# API 문서 감사 보고서

- **감사일**: 2026-05-13
- **대상**: Stock-Vis 백엔드 (Django 5.1.7 + DRF)
- **모드**: 읽기 전용 (코드 수정 없음)
- **진입점**: `config/urls.py` 기준 — 14개 앱 마운트

---

## 1. 현재 상태

### 1.1 의존성 (pyproject.toml)

| 라이브러리 | 버전 | 상태 |
|----------|------|------|
| `drf-spectacular` | `^0.29.0` | ✅ 설치됨 |
| `drf-spectacular-sidecar` | `^2026.4.14` | ✅ Swagger UI / ReDoc 정적 자산 |
| `djangorestframework-simplejwt` | `^5.5.1` | JWT Bearer 인증 |
| `drf-yasg` | (없음) | — (사용하지 않음) |

→ **OpenAPI 스펙 자동 생성 가능**. drf-spectacular이 의존성·설정·URL에 이미 결선되어 있음.

### 1.2 settings.py 결선 상태

- `REST_FRAMEWORK.DEFAULT_SCHEMA_CLASS = 'drf_spectacular.openapi.AutoSchema'` (config/settings.py:363) — ✅
- `SPECTACULAR_SETTINGS` 블록 (config/settings.py:370~) — ✅
  - `TITLE`: "Stock-Vis Market Pulse v2 API"
  - `VERSION`: "2.0"
  - `SCHEMA_PATH_PREFIX = r'/api/v[12]'` — **v1/v2 모두 매칭**
  - `DISABLE_ERRORS_AND_WARNINGS: True` — 명시 `@extend_schema` 없는 뷰는 graceful fallback
  - `ENUM_NAME_OVERRIDES`: thesis/news/chainsight enum 충돌 회피
  - `SWAGGER_UI_DIST/REDOC_DIST: 'SIDECAR'` — 오프라인 사용 가능
  - `COMPONENT_SPLIT_REQUEST: True`

### 1.3 노출된 스키마/UI URL (config/urls.py)

| Path | View | 비고 |
|------|------|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI YAML/JSON 스펙 |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc UI |

> 스펙 본체는 SCHEMA_PATH_PREFIX 정규식 덕분에 v1+v2 모두 포함하지만, **노출 경로 명칭이 `v2/`로 시작**해 v1 endpoint가 같이 들어 있다는 사실이 외부에서 잘 안 보임.

### 1.4 `@extend_schema` 데코레이터 사용 분포 (prod 코드만)

| 파일 | 데코레이터 수 |
|------|---------------|
| `chainsight/api/views.py` | 7 |
| `serverless/views.py` | 6 |
| `api_request/admin_views.py` | 5 |
| `marketpulse/api/views/*.py` (5개 모듈) | 5 |
| `users/views.py` | 2 |
| `rag_analysis/views.py` | 2 |
| `news/api/views.py` | 2 |
| **합계 (prod)** | **29** |

→ Market Pulse v2 + Chain Sight + 일부 admin은 명시 스키마 작성 완료, **나머지 v1 endpoint는 graceful fallback**.

### 1.5 요약

- ✅ 인프라(의존성/설정/URL)는 완비 — 신규 도입 비용은 사실상 0
- ⚠️ **스키마 품질이 부분적**: prod 뷰 약 240+ endpoint 중 약 29개만 `@extend_schema` 명시 (~12%)
- ⚠️ UI 경로명이 v2 중심이라 v1 전용 endpoint가 같은 스펙에 포함된다는 사실이 가려져 있음

---

## 2. 엔드포인트 목록 (앱별)

> 집계: `urls.py`의 `path()` 항목 + DRF `ViewSet`의 `@action` 메서드 + `DefaultRouter` 기본 CRUD. 어림 추정치는 ≈ 표기.

| 앱 (마운트) | path() | ViewSet 추가 | 소계 | `@extend_schema` | 문서화 상태 |
|------------|--------|-------------|------|-----------------|------------|
| **users** (`/api/v1/users/`) | 35 | — | 35 | 2 | 🔴 미흡 |
| **stocks** (`/api/v1/stocks/`) | 39 | — | 39 | 0 | 🔴 미흡 |
| **news** (`/api/v1/news/`) | 1 (router) | NewsViewSet `@action` 30 + 기본 CRUD 5 | ≈ 35 | 2 | 🔴 미흡 |
| **macro** (`/api/v1/macro/`) | 10 | — | 10 | 0 | 🔴 미흡 |
| **rag_analysis** (`/api/v1/rag/`) | 15 | — | 15 | 2 | 🟠 일부 |
| **serverless** (`/api/v1/serverless/`) | 64 | — | 64 | 6 | 🟠 일부 |
| **thesis** (`/api/v1/thesis/`) | 11 | ThesisViewSet `@action` 2 + Thesis/Premise/Indicator CRUD 15 | ≈ 28 | 0 | 🔴 미흡 |
| **validation** (`/api/v1/validation/`) | 6 | — | 6 | 0 | 🔴 미흡 |
| **chainsight** (`/api/v1/chainsight/`) | 7 | WatchlistViewSet `@action` 5 + CRUD 5 | ≈ 17 | 7 | 🟢 양호 |
| **sec_pipeline** (`/api/v1/sec-pipeline/`) | 2 | — | 2 | 0 | 🔴 미흡 |
| **api_request** (`/api/v1/`) | 6 | — | 6 | 5 | 🟢 양호 |
| **portfolio** (`/api/coach/`) | 5 | — | 5 | 0 | 🔴 미흡 |
| **marketpulse v2** (`/api/v2/market-pulse/`) | 5 | — | 5 | 5 | 🟢 양호 |
| **config root** | 2 (api_root, health) + 3 (schema/swagger/redoc) | — | 5 | — | — |
| **합계 (추정)** | **208** | **약 40** | **약 248** | **29** | **약 12% 명시** |

### 2.1 앱별 엔드포인트 세부

#### users (35 path)
JWT 인증 + 세션 호환 + 즐겨찾기 + 포트폴리오 + 관심사 + 워치리스트
- JWT(7): `jwt/{signup,login,logout,refresh,verify,change-password,profile}/`
- 세션(6): `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/`
- 즐겨찾기(3): `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/`
- 포트폴리오(10): `portfolio/{,summary/,table/,refresh/,<pk>/,<pk>/quick-update/,symbol/<symbol>/,symbol/<symbol>/refresh/,symbol/<symbol>/status/}`
- 관심사(2): `interests/`, `interests/<pk>/`
- 워치리스트(7): `watchlist/{,<pk>/,<pk>/add-stock/,<pk>/bulk-add/,<pk>/bulk-remove/,<pk>/stocks/,<pk>/stocks/<symbol>/,<pk>/stocks/<symbol>/remove/}`

#### stocks (39 path)
- 페이지 뷰(2): `dashboard`, `stock/<symbol>/`
- 검색(1+3 자동완성)
- 차트/Overview/BalanceSheet/Income/CashFlow API(5)
- Sync(1)
- MVP(4): list/detail/rag-context/sectors
- 기술지표(3): indicators/signal/compare
- Market Movers(1)
- Fundamentals(5): key-metrics/ratios/dcf/rating/all
- Screener(6): 일반/large-cap/high-dividend/sector/low-beta/exchange
- Exchange(5): index/quote/batch/major-indices/sector-performance
- EOD(3): dashboard/signal-detail/pipeline-status

#### news (router only + NewsViewSet 30 action)
모든 endpoint는 `NewsViewSet.@action(detail=False)`로 정의. 일부 `permission_classes=[IsAdminUser]`, 일부 `[AllowAny]`, 나머지 기본 `[IsAuthenticated]`.
- 종목별: `stock/<symbol>/`, `stock/<symbol>/sentiment`
- 키워드: `daily-keywords`, `daily-keywords/generate`, `keyword-detail`
- 피드: `market-feed` (AllowAny), `interest-options` (AllowAny), `personalized-feed` (IsAuthenticated)
- 이벤트: `news-events`, `news-events/impact-map`
- ML 운영(admin): `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `ml-trend`, `ml-rollback-preview`, `ml-rollback`
- 수집(admin): `collection-logs`, `pipeline-health`, `llm-usage`, `task-timeline`, `neo4j-status`
- 알림(admin): `alerts`, `alerts/<alert_pk>/resolve`
- 기타: 기본 router CRUD(list/retrieve/create/update/destroy) 5

#### macro (10 path)
`pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis (15 path)
- DataBasket(6): list-create/detail/add-item/add-stock-data/items/<id>/clear
- AnalysisSession(4): list-create/detail/messages/chat-stream (SSE)
- Monitoring(5): usage/cost/cache/history/pricing

#### serverless (64 path)
가장 큰 앱. 외부 노출 + 운영자 대시보드 혼재.
- Admin Dashboard(12): overview, stocks, screener, market-pulse, news, system, tasks, actions, actions/status/<id>, news/categories, news/categories/<id>, news/sector-options
- Market Movers(2) + Sync(2) + Keywords(4)
- Market Breadth(3) + Sector Heatmap(3)
- Screener Presets(7) + Filters(1) + Advanced Screener(1)
- Alerts(6)
- Investment Thesis(4) — legacy 표시
- ETF Holdings(9) — Chain Sight Phase 3, LEGACY_KEEP_UNTIL_DC2
- LLM Relations(4) + Institutional 13F(3) + Regulatory/Patent(2)
- Health(1)

#### thesis (11 path + nested routers)
- Conversation(4): start/respond/news-issues/suggest
- Monitoring(2): `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<indicator_id>/readings/`
- Alerts(2): list, `<aid>/read/`
- Nested premises router → PremiseViewSet (CRUD 5)
- Nested indicators router → IndicatorViewSet (CRUD 5)
- Main router → ThesisViewSet (CRUD 5 + `@action` 2 = 7)

#### validation (6 path)
- `<symbol>/summary/`, `<symbol>/metrics/`, `<symbol>/leader-comparison/`, `<symbol>/presets/`, `<symbol>/peer-preference/`, `<symbol>/llm-filter/`

#### chainsight (7 path + WatchlistViewSet)
- 마켓 뷰: `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`
- 동적: `<symbol>/neighbors/`, `<symbol>/graph/`, `<symbol>/suggestions/`
- WatchlistViewSet: CRUD 5 + `@action(detail=True, methods=['post'])` 5

#### sec_pipeline (2 path)
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request (6 path)
- `health/`, `admin/providers/{status,rate-limits,cache,test,config}/`

#### portfolio (5 path) — `/api/coach/*`
- `e1/garp/`, `e5/adjustment/`, `e2/diagnostic-card/`, `e6/comparison/`, `e3/metric-comment/`

#### marketpulse v2 (5 path) — `/api/v2/market-pulse/*`
- `overview`, `cards/<card_id>/detail`, `news/refresh`, `i18n`, `health`

---

## 3. 문서화 도입(완성) 작업 목록

> 핵심 인프라는 이미 갖춰져 있으므로 **신규 도입이 아니라 "스키마 품질 채우기"가 본질**.

### 3.1 인프라 — 이미 완료된 항목

- [x] `drf-spectacular` 의존성 추가 (pyproject.toml)
- [x] `drf-spectacular-sidecar` 정적 자원
- [x] `REST_FRAMEWORK.DEFAULT_SCHEMA_CLASS` 글로벌 등록
- [x] `SPECTACULAR_SETTINGS` 기본 설정
- [x] `/api/v2/schema/`, `/api/v2/swagger/`, `/api/v2/redoc/` URL 노출
- [x] enum 충돌 회피 (`ENUM_NAME_OVERRIDES`)
- [x] graceful fallback로 빌드 실패 방지 (`DISABLE_ERRORS_AND_WARNINGS`)

### 3.2 인프라 — 보강 권장 사항

| 우선순위 | 작업 | 예상 공수 | 비고 |
|---------|------|----------|------|
| P1 | UI 노출 경로를 v2에서 분리해 글로벌 위치로 이동 (`/api/schema/`, `/api/docs/`, `/api/redoc/`) | 0.5h | 현재 v2 prefix가 명칭 혼동 유발 |
| P1 | `SPECTACULAR_SETTINGS.TITLE/DESCRIPTION/VERSION` 갱신 (현재 "Market Pulse v2"만 언급) | 0.5h | v1+v2 전체 포괄 |
| P2 | `TAGS` 확장: 앱별 13개 추가 (users, stocks, news, macro, rag, serverless, thesis, validation, chainsight, sec_pipeline, portfolio, marketpulse, api_request) | 1h | 그룹핑 가독성 |
| P2 | CI에 `manage.py spectacular --validate --fail-on-warn` 추가 | 1h | 현재 `DISABLE_ERRORS_AND_WARNINGS=True`이므로 별도 검증 필요 |
| P3 | OpenAPI 스펙 파일을 `contracts/` 디렉터리에 동기 export (`spectacular --file contracts/openapi.yaml`) | 1h | contracts-driven 정렬 |

### 3.3 `@extend_schema` 적용 범위 — 우선순위별 분류

#### Tier A (외부 공개 / 프론트 직접 호출 / 보안 민감) — **우선 작성**

| 영역 | 클래스/액션 수 | 예상 공수 |
|------|---------------|----------|
| users (인증/포트폴리오/워치리스트) | ≈ 35 | 7h |
| stocks (대시보드/펀더멘털/스크리너/EOD) | ≈ 39 | 8h |
| news (NewsViewSet `@action` + 기본 CRUD) | ≈ 35 | 8h |
| validation (1차 검증) | 6 | 2h |
| portfolio (Coach 5 endpoint) | 5 | 2h |
| thesis (가설 통제실 + nested routers) | ≈ 28 | 8h |
| **Tier A 소계** | **약 148** | **약 35h** |

#### Tier B (관리자/내부 운영) — **보통**

| 영역 | 클래스/액션 수 | 예상 공수 |
|------|---------------|----------|
| serverless 비-admin (Market Movers/Breadth/Heatmap/Screener/Alerts/ETF/LLM Relations/Institutional 등) | ≈ 52 | 10h |
| chainsight 잔여 보강 (WatchlistViewSet action) | ≈ 10 | 2h |
| macro | 10 | 3h |
| rag_analysis 잔여 | 13 | 4h |
| sec_pipeline | 2 | 1h |
| api_request 잔여 | 1 | 0.5h |
| **Tier B 소계** | **약 88** | **약 20.5h** |

#### Tier C (관리자 전용 dashboard, 낮음)

| 영역 | 대상 | 예상 공수 |
|------|------|----------|
| serverless admin dashboard | 12 | 3h |
| **Tier C 소계** | **12** | **3h** |

### 3.4 데코레이터 작성 시 체크리스트

각 뷰/액션에 대해:
- `summary` (한 줄 요약, 한글 OK)
- `description` (몇 줄 설명)
- `tags` (앱 기준 그룹)
- `request` (Serializer 또는 `inline_serializer`)
- `responses`: 200/400/401/403/404의 envelope 형식 일치 확인 (`docs/features/api_envelope/policy.md`)
- `parameters` (path/query — 특히 `<str:symbol>`, `<int:pk>`, `<uuid:thesis_id>` 명시)
- 페이지네이션 사용 시 `PageNumberPagination`/`LimitOffsetPagination` 명시
- 인증: 기본 `IsAuthenticated`. `permission_classes=[AllowAny]`/`[IsAdminUser]` 액션은 `auth=[]` 또는 별도 명시

### 3.5 총 예상 공수

| 단계 | 공수 (개발자 1인) |
|------|------------------|
| 3.2 인프라 보강 | 4h |
| 3.3 Tier A | 35h |
| 3.3 Tier B | 20.5h |
| 3.3 Tier C | 3h |
| **합계 (Full coverage)** | **약 62.5h (≈ 8일)** |
| **Tier A만 + 인프라 보강** (외부 공개 영역) | **약 39h (≈ 5일)** |

### 3.6 위험 / 주의 사항

- **인증/권한 표기 누락 위험**: NewsViewSet은 `@action`별로 `permission_classes`가 IsAdminUser/AllowAny/IsAuthenticated로 분기됨 — `@extend_schema(auth=[])` 명시 필요한 액션이 다수.
- **Serializer 미존재 뷰**: 일부 함수형 뷰(serverless, portfolio, sec_pipeline)는 Serializer 없이 dict 반환 → `inline_serializer` 또는 `OpenApiResponse(response=OpenApiTypes.OBJECT)` 사용.
- **legacy 경로**: serverless의 LEGACY 표시(ETF Phase 3 `LEGACY_KEEP_UNTIL_DC2`, Investment Thesis Phase 2.3)는 `deprecated=True` 표기 권장.
- **envelope 정책 일관성**: `docs/features/api_envelope/policy.md` 기준의 응답 envelope (`{detail, code?, errors?, status_code}`)가 모든 뷰에 적용되어 있는지 별도 검증 필요 (본 감사 범위 밖).
- **현재 `DISABLE_ERRORS_AND_WARNINGS=True`** 상태이므로 스키마에 silent fallback이 들어가도 빌드 통과 — Tier별 작업 시 일부 영역만 검증 활성화 후 점진 확대 권장.
- **app_name 미설정**: `news/api/urls.py`와 `validation/api/urls.py`, `chainsight/api/urls.py`에 `app_name`이 없음. URL reverse 의존 코드가 있으면 점검 필요.

---

## 4. 결론

- **인프라**는 이미 완비되어 있어 신규 도입 비용 거의 0.
- 실질 작업은 **`@extend_schema` 데코레이터 채우기** — 약 248 endpoint 중 명시는 29개 (≈ 12%).
- **외부 공개 영역(Tier A)만 처리해도 약 5일** 이내에 Swagger UI 품질을 의미 있게 확보 가능.
- 즉시 권고: ① UI 경로를 v2에서 분리, ② Tier A 우선 진행, ③ CI 검증 추가, ④ `contracts/openapi.yaml`과 동기화.
