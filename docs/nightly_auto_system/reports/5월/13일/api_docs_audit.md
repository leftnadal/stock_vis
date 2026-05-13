# API 문서 감사 보고서

- **감사일**: 2026-05-13
- **대상**: Stock-Vis 백엔드 (Django + DRF)
- **모드**: 읽기 전용 (코드 수정 없음)
- **감사 범위**: `config/urls.py` 진입점 기준 — 12개 앱 + 루트/admin/schema

---

## 1. 현재 상태

### 1.1 의존성 (pyproject.toml)

| 라이브러리 | 버전 | 비고 |
|----------|------|------|
| `drf-spectacular` | `^0.29.0` | ✅ 설치됨 |
| `drf-spectacular-sidecar` | `^2026.4.14` | ✅ Swagger UI / ReDoc 정적 자원 번들 |
| `djangorestframework-simplejwt` | `^5.5.1` | JWT Bearer 인증 |
| `drf-yasg` | (없음) | — |

→ **OpenAPI 스펙 자동 생성 가능**. drf-spectacular이 이미 의존성 + 설정 + URL에 모두 결선되어 있음.

### 1.2 settings.py 결선 상태

- `REST_FRAMEWORK.DEFAULT_SCHEMA_CLASS = 'drf_spectacular.openapi.AutoSchema'` (config/settings.py:363) — ✅ 글로벌 스키마 클래스 등록 완료.
- `SPECTACULAR_SETTINGS` 블록 존재 (config/settings.py:370~) — ✅
  - `TITLE`: "Stock-Vis Market Pulse v2 API"
  - `VERSION`: "2.0"
  - `SCHEMA_PATH_PREFIX = r'/api/v[12]'` — **v1/v2 모두 포함하도록 정규식 지정됨**
  - `DISABLE_ERRORS_AND_WARNINGS: True` — 명시적 `@extend_schema`가 없는 뷰는 graceful fallback (string body) 처리
  - `ENUM_NAME_OVERRIDES`: thesis enum 충돌 해결용 명시
  - `SWAGGER_UI_DIST/REDOC_DIST: 'SIDECAR'` — 오프라인 가능
  - `COMPONENT_SPLIT_REQUEST: True`

### 1.3 노출된 스키마/UI URL (config/urls.py)

| Path | View | 비고 |
|------|------|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI YAML/JSON 스펙 |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc UI |

> **현재는 `/api/v2/` 네임스페이스로만 노출**. SCHEMA_PATH_PREFIX 정규식은 v1을 포함하므로 스펙 본체에는 v1 endpoint가 같이 들어가지만, UI 경로명은 v2로 명명되어 혼란 여지 있음.

### 1.4 `@extend_schema` 데코레이터 사용 분포 (prod 코드만)

| 파일 | 데코레이터 수 |
|------|---------------|
| `marketpulse/api/views/*.py` (5개 모듈) | 5 (각 1개씩) |
| `chainsight/api/views.py` | 7 |
| `serverless/views.py` | 6 |
| `api_request/admin_views.py` | 5 |
| `news/api/views.py` | 2 |
| `users/views.py` | 2 |
| `rag_analysis/views.py` | 2 |
| **합계 (prod 소스)** | **약 29개** |

→ Market Pulse v2 + Chain Sight + 일부 admin은 명시적 스키마 작성 완료, **나머지 v1 endpoint 대부분은 graceful fallback** 상태.

### 1.5 정리

- ✅ 인프라(의존성/설정/URL)는 완비
- ⚠️ **스키마 품질**은 부분적: prod 뷰 약 111개 클래스 중 약 29개만 `@extend_schema` 명시
- ⚠️ UI 경로명이 v2 중심이라 v1 전용 endpoint가 같은 스펙에 섞여 있음을 외부에서 인지하기 어려움

---

## 2. 전체 엔드포인트 목록 (앱별)

> 집계 기준: `urls.py`의 `path()` 항목 + DRF `ViewSet`의 `@action` 메서드 + 라우터 기본 CRUD. 어림 추정치는 ≈ 표기.

| 앱 (마운트) | path() 수 | ViewSet 추가 | 소계 | `@extend_schema` 적용 | 문서화 상태 |
|------------|-----------|-------------|------|----------------------|------------|
| **users** (`/api/v1/users/`) | 31 | — | 31 | 2 | 🔴 미흡 |
| **stocks** (`/api/v1/stocks/`) | 37 | — | 37 | 0 | 🔴 미흡 |
| **news** (`/api/v1/news/`) | 1 (router) | NewsViewSet `@action` 30 + 기본 CRUD | ≈ 32+ | 2 | 🔴 미흡 |
| **macro** (`/api/v1/macro/`) | 10 | — | 10 | 0 | 🔴 미흡 |
| **rag_analysis** (`/api/v1/rag/`) | 13 | — | 13 | 2 | 🟠 일부 |
| **serverless** (`/api/v1/serverless/`) | 51 | — | 51 | 6 | 🟠 일부 |
| **thesis** (`/api/v1/thesis/`) | 8 + 3 router | ThesisViewSet `@action` 2 + Premise/Indicator nested CRUD | ≈ 20 | 0 | 🔴 미흡 |
| **validation** (`/api/v1/validation/`) | 6 | — | 6 | 0 | 🔴 미흡 |
| **chainsight** (`/api/v1/chainsight/`) | 7 + 1 router | WatchlistViewSet `@action` 5 + CRUD | ≈ 14 | 7 | 🟢 양호 |
| **sec_pipeline** (`/api/v1/sec-pipeline/`) | 2 | — | 2 | 0 | 🔴 미흡 |
| **api_request** (`/api/v1/`) | 6 | — | 6 | 5 | 🟢 양호 |
| **portfolio** (`/api/`) | 5 | — | 5 | 0 | 🔴 미흡 |
| **marketpulse** (`/api/v2/market-pulse/`) | 5 | — | 5 | 5 | 🟢 양호 |
| **config root** | 2 (api_root, health) + 3 (schema/swagger/redoc) | — | 5 | — | — |
| **합계 (추정)** | **약 187** | **약 50** | **약 237** | **약 29** | **약 12% 명시** |

### 2.1 앱별 엔드포인트 세부

#### users (31)
JWT 인증(7) + 세션 호환(6) + 즐겨찾기(3) + 포트폴리오(9) + 관심사(2) + 워치리스트(7)
- `jwt/signup`, `jwt/login`, `jwt/logout`, `jwt/refresh`, `jwt/verify`, `jwt/change-password`, `jwt/profile`
- `me/`, `users`, `@<user_name>/`, `change_password/`, `login/`, `logout/`
- `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/`
- `portfolio/`, `portfolio/summary/`, `portfolio/table/`, `portfolio/refresh/`, `portfolio/<pk>/`, `portfolio/<pk>/quick-update/`, `portfolio/symbol/<symbol>/`, `portfolio/symbol/<symbol>/refresh/`, `portfolio/symbol/<symbol>/status/`
- `interests/`, `interests/<pk>/`
- `watchlist/`, `watchlist/<pk>/`, `watchlist/<pk>/add-stock/`, `watchlist/<pk>/bulk-add/`, `watchlist/<pk>/bulk-remove/`, `watchlist/<pk>/stocks/`, `watchlist/<pk>/stocks/<symbol>/`, `watchlist/<pk>/stocks/<symbol>/remove/`

#### stocks (37)
대시보드 + 종목 상세 + 차트/펀더멘털/스크리너/EOD
- 대시보드(2), 검색(1+3 자동완성), 차트/Overview/BalanceSheet/Income/CashFlow(5)
- 동기화(1), MVP(4), 기술지표(3), 검색(3), Market Movers(1)
- Fundamentals(5: key-metrics/ratios/dcf/rating/all)
- Screener(6: 조건/대형/고배당/섹터/저베타/거래소)
- Exchange(5: index/quote/batch/major-indices/sector-performance)
- EOD(3: dashboard/signal/<id>/pipeline-status)

#### news (≈ 32+)
`NewsViewSet`의 `@action` 30개 (대부분 `detail=False`), 일부 `IsAdminUser` 권한
- 종목별 뉴스, 감성 분석, 일간 키워드 생성/조회, 키워드 상세, market-feed, interest-options, personalized-feed, news-events (impact-map 포함), ml-status / ml-shadow / ml-weekly / ml-lightgbm-readiness / ml-trend, collection-logs, pipeline-health, llm-usage, task-timeline, neo4j-status, ml-rollback-preview / ml-rollback, alerts / alerts-resolve

#### macro (10)
- `pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis (13)
DataBasket(6) + AnalysisSession(4) + Monitoring(5) — 총 13 (단, 일부 view는 1개 path 안에 GET/POST 합쳐짐)
- baskets (list/create, detail, add-item, add-stock-data, items/<id>, clear)
- sessions (list/create, detail, messages, chat/stream SSE)
- monitoring (usage, cost, cache, history, pricing)

#### serverless (51)
가장 큰 앱. 관리자 대시보드 + Market Movers + 키워드 + Market Breadth + Heatmap + Screener Presets/Filters + Advanced Screener + Alerts + Thesis(legacy) + ETF Holdings + LLM Relations + Institutional 13F + Regulatory + Patent + Health
- Admin Dashboard(13), Market Movers(2), Sync(2), Keywords(4), Breadth(3), Heatmap(3), Presets(7), Filters(1), Advanced Screener(1), Alerts(6), Thesis(4), ETF(8), LLM Relations(4), Institutional(3), Regulatory/Patent(2), Health(1)

#### thesis (≈ 20)
- 명시 path 8: conversation/start, conversation/respond, conversation/news-issues, conversation/suggest, dashboard, indicator-readings, alerts (list), alerts/<aid>/read
- ThesisViewSet: 기본 CRUD 5 + `@action` 2 = 7
- ThesisPremiseViewSet (nested): 기본 CRUD 5
- ThesisIndicatorViewSet (nested): 기본 CRUD 5

#### validation (6)
- `<symbol>/summary/`, `<symbol>/metrics/`, `<symbol>/leader-comparison/`, `<symbol>/presets/`, `<symbol>/peer-preference/`, `<symbol>/llm-filter/`

#### chainsight (≈ 14)
- 7 path: seeds, sector/<sector>/graph, signals, trace, <symbol>/neighbors, <symbol>/graph, <symbol>/suggestions
- WatchlistViewSet: CRUD 5 + `@action` 5 (각 detail=True POST)

#### sec_pipeline (2)
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request (6)
- `health/`, `admin/providers/status/`, `rate-limits/`, `cache/`, `test/`, `config/`

#### portfolio (5) — `/api/coach/*`
- coach/e1/garp, coach/e5/adjustment, coach/e2/diagnostic-card, coach/e6/comparison, coach/e3/metric-comment

#### marketpulse v2 (5)
- overview, cards/<card_id>/detail, news/refresh, i18n, health

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
| P1 | `SPECTACULAR_SETTINGS.TITLE/DESCRIPTION/VERSION` 갱신 (현재 "Market Pulse v2"만 언급) | 0.5h | v1+v2 전체를 포괄하도록 |
| P2 | `TAGS` 확장: 앱별 12개 추가 (users, stocks, news, macro, rag, serverless, thesis, validation, chainsight, sec_pipeline, portfolio, marketpulse) | 1h | 그룹핑 가독성 |
| P2 | CI에 `manage.py spectacular --validate --fail-on-warn` 추가 (현재 `DISABLE_ERRORS_AND_WARNINGS=True`이므로 별도 검증 필요) | 1h | 회귀 방지 |
| P3 | OpenAPI 스펙 파일을 `contracts/` 디렉터리에 동기 export (`spectacular --file contracts/openapi.yaml`) | 1h | contracts-driven 정렬 |

### 3.3 `@extend_schema` 적용 범위 — 우선순위별 분류

#### Tier A (외부 공개 / 프론트 직접 호출 / 보안 민감) — **우선 작성**

| 영역 | 대상 | 클래스/액션 수 | 예상 공수 |
|------|------|---------------|----------|
| users (인증/포트폴리오/워치리스트) | 18 클래스 | ≈ 31 endpoint | 6h |
| stocks (대시보드/펀더멘털/스크리너/EOD) | 11 + 5 + 5 + 3 + 6 + 5 + 3 클래스 | ≈ 37 | 8h |
| news (뉴스 + 키워드 + 감성 + 알림) | NewsViewSet 30 action | ≈ 32 | 8h |
| validation (1차 검증) | 6 클래스 | 6 | 2h |
| portfolio (Coach 5 endpoint) | 5 함수형 뷰 | 5 | 2h |
| thesis (가설 통제실 + 라우터) | ≈ 20 | ≈ 20 | 6h |
| **Tier A 소계** | — | **약 131** | **32h** |

#### Tier B (관리자/내부 운영) — **보통**

| 영역 | 대상 | 클래스/액션 수 | 예상 공수 |
|------|------|---------------|----------|
| serverless (admin 13 + 비-admin 38) — 비-admin만 외부 노출 | 38 | 38 | 8h |
| chainsight 잔여(추가 보강) | 5~7 | 5~7 | 2h |
| macro | 10 | 10 | 3h |
| rag_analysis 잔여 | 11 | 11 | 4h |
| sec_pipeline | 2 | 2 | 1h |
| api_request 잔여 | 1 | 1 | 0.5h |
| **Tier B 소계** | — | **약 67** | **18.5h** |

#### Tier C (관리자 전용, 낮음)

| 영역 | 대상 | 예상 공수 |
|------|------|----------|
| serverless admin 13 | 13 | 3h |
| **Tier C 소계** | **13** | **3h** |

### 3.4 데코레이터 작성 시 체크리스트

각 뷰/액션에 대해:
- `summary` (한 줄 요약, 한글 OK — drf-spectacular는 한글 그대로 노출)
- `description` (몇 줄 설명)
- `tags` (앱 기준 그룹)
- `request` (Serializer 또는 inline_serializer)
- `responses`: 200/400/401/403/404의 envelope 형식 일치 확인 (`docs/features/api_envelope/policy.md` 참조)
- `parameters` (path / query parameter — 특히 `<str:symbol>`, `<int:pk>` 명시)
- 페이지네이션 사용 시 `PageNumberPagination` / `LimitOffsetPagination` 명시
- 인증: 기본 `IsAuthenticated`이나 `permission_classes=[AllowAny]`/`IsAdminUser` 액션은 `auth=[]` 또는 별도 명시

### 3.5 총 예상 공수

| 단계 | 공수 (개발자 1인) |
|------|------------------|
| 3.2 인프라 보강 | 4h |
| 3.3 Tier A | 32h |
| 3.3 Tier B | 18.5h |
| 3.3 Tier C | 3h |
| **합계 (Full coverage)** | **약 57.5h (≈ 7~8일)** |
| **Tier A만 + 인프라 보강** (외부 공개 영역) | **약 36h (≈ 4~5일)** |

### 3.6 위험 / 주의 사항

- **인증/권한 표기 누락 위험**: NewsViewSet은 `@action`별로 `permission_classes`가 다름(IsAdminUser ↔ AllowAny ↔ IsAuthenticated). `@extend_schema(auth=[])` 명시가 필요한 액션이 다수 존재.
- **Serializer 미존재 뷰**: 일부 함수형 뷰(serverless, portfolio)는 Serializer 없이 dict 반환 → `inline_serializer` 또는 `OpenApiResponse(response=OpenApiTypes.OBJECT)` 사용해야 함.
- **legacy 경로**: serverless에 LEGACY 표시된 라인 (Chain Sight Phase 3 ETF, Thesis Phase 2.3)은 deprecation 표기(`deprecated=True`) 권장.
- **envelope 정책 일관성**: `docs/features/api_envelope/policy.md` 기준의 응답 envelope가 모든 뷰에 적용되어 있는지 별도 검증 필요(본 감사 범위 밖).
- **현재 `DISABLE_ERRORS_AND_WARNINGS=True`** 상태이므로 스키마에 silent fallback이 들어가도 빌드는 통과함 — Tier 작업과 함께 일부 영역에서만 검증 켜고 점진 확대 권장.

---

## 4. 결론

- **인프라**는 이미 완비되어 있어 신규 도입 비용은 거의 0.
- 실질 작업은 **`@extend_schema` 데코레이터 채우기 (약 200+ endpoint, 그중 명시는 약 29개, 14% 수준)**.
- **외부 공개 영역(Tier A)만 처리해도 4~5일** 이내에 의미 있는 Swagger UI 품질 확보 가능.
- 즉시 권고: ① UI 경로를 v2에서 분리, ② Tier A 우선 진행, ③ CI 검증 추가, ④ contracts/ 디렉터리와 동기화.
