# API 문서 감사 보고서

- 감사일: 2026-04-24
- 감사 대상: `/Users/byeongjinjeong/Desktop/stock_vis` Django REST Framework 백엔드
- 감사 범위: API 문서 자동화 도구 설치 여부, 앱별 엔드포인트 목록, drf-spectacular 도입 시 필요 작업량
- 성격: **읽기 전용 감사** — 소스 수정 없음
- 전일 대비(4월 22일 보고서): URL 라우팅·views 파일 구조 변경 없음. 수치는 본 감사에서 재확인·정밀화(`urls.py` `path()` 원문 카운트 기준)

---

## 현재 상태

### 1.1 문서 자동화 도구 설치 여부

| 도구 | 상태 | 확인 위치 |
|------|------|-----------|
| `drf-spectacular` | **미설치** | `pyproject.toml` `[tool.poetry.dependencies]` / `[tool.poetry.group.dev.dependencies]` 미포함 |
| `drf-yasg` | **미설치** | 동일 |
| `coreapi` / `coreschema` | 미설치 | 동일 |
| DRF 내장 `SchemaGenerator` 라우팅 | 미구성 | `config/urls.py`에 `get_schema_view` 라우트 없음 |
| `config/settings.py` `SPECTACULAR_SETTINGS` | 없음 | `grep -n "SPECTACULAR\|spectacular\|swagger\|yasg\|openapi"` 0건 |
| `INSTALLED_APPS`의 `drf_spectacular` | 없음 | `config/settings.py:166~` 기준 |

**소스 그렙 결과** (`extend_schema | @swagger_auto_schema | OpenApiParameter | drf_spectacular | drf_yasg`):

- 애플리케이션 소스(`*/views*.py`, `*/serializers*.py`)에 매치 0건
- 매치 파일은 감사 스크립트(`docs/infra/nightly_v3.sh`)·이전 감사 보고서(4월 14/21/22일)·기획 문서(`docs/architecture/autonomous_agent_tasks.md` 등) 뿐 — **구현 코드에는 어떠한 OpenAPI annotation/설정도 존재하지 않음**

### 1.2 현재 문서화 방식

- `config/views.py:api_root` 뷰가 **수동 하드코딩 JSON**으로 주요 엔드포인트 몇 개(`users` JWT 5개 + portfolio 4개 + favorites 1개, `stocks` 7개, `analysis` 2개)만 노출
- `news`, `macro`, `rag_analysis`, `serverless`, `thesis`, `validation`, `chainsight`, `sec_pipeline`, `api_request` 등 **9개 앱이 하드코딩 JSON에서 완전 누락** → 실제 엔드포인트와 괴리 큼
- Swagger UI / ReDoc / OpenAPI JSON·YAML 스펙 **자동 생성 경로 없음**
- `CLAUDE.md`에서 언급되는 `contracts/` 디렉토리는 수기 관리 중(OpenAPI 스펙 + 공유 TS 타입) — 감사 범위 밖이나 자동 생성 도구 도입 시 "단일 소스" 정책 결정 필요

### 1.3 자동 생성 가능 여부

- DRF 표준 패턴(`APIView`, `GenericAPIView`, `ViewSet`, `@api_view`)이 전반적으로 적용되어 있어 **drf-spectacular 설치만으로 최소 품질의 OpenAPI 스펙을 즉시 생성 가능**
- `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`에 `JWTAuthentication` + `SessionAuthentication` 동시 등록 → `SPECTACULAR_SETTINGS["SECURITY"]` 2중 SecurityScheme 노출 정책 결정 필요
- 단, 아래 요인으로 **자동 생성 결과 품질은 낮을 것**:
  1. `serverless/views.py`의 `@api_view` **함수 기반 뷰 52개** → request body·query 파라미터 자동 추론 제약
  2. 다수 뷰가 `Response({...})`에 dict 직접 반환 → response 스키마 명시 부재
  3. `news/api/views.py` 단일 `NewsViewSet` **2,183줄 / `@action` 30개** (일부 `url_path=r'...(?P<name>...)'` 정규식)
  4. `rag_analysis/sessions/<pk>/chat/stream/`는 SSE(`text/event-stream`) 스트리밍 응답
  5. `thesis` UUID 패스 파라미터(`<uuid:thesis_id>`, `<uuid:indicator_id>`, `<uuid:aid>`) — `format: uuid` 명시 권장
- 고품질 스펙까지 가려면 `@extend_schema` 수작업 annotation과 공용 Serializer 신설이 필수

---

## 엔드포인트 목록 (앱별 테이블)

> `path()` 수는 `urls.py`에 등록된 라우트. ViewSet + router 등록의 경우 라우터 자동 확장 기본 CRUD 액션과 `@action` 데코레이터를 합산해 **실효 엔드포인트**를 별도 표기. 카운트 근거는 본 감사에서 `grep -c "path("` / `grep -n "@action"` / `grep -n "@api_view"`로 확인.

### 2.1 앱별 요약

| 앱 (mount path) | urls.py `path()` | ViewSet CRUD / `@action` | 실효 엔드포인트(추정) | 뷰 파일 규모 |
|----------------|-----------------:|:------------------------:|----------------------:|:------------:|
| **stocks** (`/api/v1/stocks/`) | 39 | — | **39** | 9개 분할 뷰 파일 |
| **users** (`/api/v1/users/`) | 35 | — | **35** | `views.py` + `jwt_views.py` |
| **news** (`/api/v1/news/`) | 1 (router) | `NewsViewSet` CRUD(list/retrieve) 2 + `@action` 30 | **약 32** | `news/api/views.py` **2,183줄** 단일 ViewSet |
| **macro** (`/api/v1/macro/`) | 10 | — | **10** | `macro/views.py` |
| **rag_analysis** (`/api/v1/rag/`) | 15 | — | **15** | `rag_analysis/views.py` (SSE 1건 포함) |
| **serverless** (`/api/v1/serverless/`) | 64 | `@api_view` 함수 52 + admin CBV 12 | **64** | `serverless/views.py` **3,405줄** + `views_admin.py` |
| **thesis** (`/api/v1/thesis/`) | 11 + 3 routers(main/premise/indicator) | `ThesisViewSet` CRUD 6 + `@action` 2, `ThesisPremiseViewSet` CRUD 6, `ThesisIndicatorViewSet` CRUD 6 | **약 31** | `thesis/views/` 패키지 |
| **validation** (`/api/v1/validation/`) | 6 | — | **6** | `validation/api/views.py` |
| **chainsight** (`/api/v1/chainsight/`) | 7 + router | `WatchlistViewSet` CRUD 6 + `@action` 5 | **약 18** | `chainsight/api/views.py` + `views/watchlist_views.py` |
| **sec_pipeline** (`/api/v1/sec-pipeline/`) | 2 | — | **2** | `sec_pipeline/views.py` |
| **api_request** (`/api/v1/`) | 6 | — | **6** | `api_request/admin_views.py` |
| **config (루트)** | 3 | — | **3** | `''`(api_root 하드코딩), `health/`, `admin/` |
| **총계** | **약 199 path()** | — | **약 261** | `python manage.py show_urls`로 런타임 재확인 권장 |

### 2.2 앱별 상세 내역

#### stocks (39) — `stocks/urls.py`
- 페이지/검색: `''`(DashboardView), `stock/<symbol>/`, `search/`
- Chart/Overview/재무제표: `api/chart/<symbol>/`, `api/overview/<symbol>/`, `api/balance-sheet/<symbol>/`, `api/income-statement/<symbol>/`, `api/cashflow/<symbol>/`
- Sync: `api/sync/<symbol>/`
- MVP: `api/mvp/stocks/`, `api/mvp/stock/<symbol>/`, `api/mvp/rag/<symbol>/`, `api/mvp/sectors/`
- 기술지표: `api/indicators/<symbol>/`, `api/signal/<symbol>/`, `api/indicators/compare/`
- 심볼 검색: `api/search/symbols/`, `api/search/validate/<symbol>/`, `api/search/popular/`
- Market Movers: `api/market-movers/`
- Fundamentals: `api/fundamentals/{key-metrics|ratios|dcf|rating|all}/<symbol>/` (5)
- Screener: `api/screener/`, `api/screener/{large-cap|high-dividend|low-beta}/`, `api/screener/sector/<sector>/`, `api/screener/exchange/<exchange>/` (6)
- Exchange Quotes: `api/quotes/index/`, `api/quotes/<symbol>/`, `api/quotes/batch/`, `api/quotes/major-indices/`, `api/quotes/sector-performance/` (5)
- EOD: `eod/dashboard/`, `eod/signal/<signal_id>/`, `eod/pipeline/status/`

#### users (35) — `users/urls.py`
- JWT 인증 (7): `jwt/{signup,login,logout,refresh,verify,change-password,profile}/`
- 세션 인증 하위호환 (6): `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/`
- 즐겨찾기 (3): `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/`
- 포트폴리오 (9): `portfolio/`, `portfolio/summary/`, `portfolio/table/`, `portfolio/refresh/`, `portfolio/<pk>/`, `portfolio/<pk>/quick-update/`, `portfolio/symbol/<symbol>/`, `portfolio/symbol/<symbol>/refresh/`, `portfolio/symbol/<symbol>/status/`
- 관심사 (2): `interests/`, `interests/<pk>/`
- 워치리스트 (8): `watchlist/`, `watchlist/<pk>/`, `watchlist/<pk>/add-stock/`, `watchlist/<pk>/bulk-add/`, `watchlist/<pk>/bulk-remove/`, `watchlist/<pk>/stocks/`, `watchlist/<pk>/stocks/<symbol>/`, `watchlist/<pk>/stocks/<symbol>/remove/`

#### news (약 32) — `news/api/urls.py` + `NewsViewSet`
- `DefaultRouter().register(r'', NewsViewSet, basename='news')` — 루트 자체에 등록 → `/` (list), `/<pk>/` (retrieve) 기본 2건
- `@action(detail=False, ...)` **30개** (`news/api/views.py` 전수 조사):
  - `stock/(?P<symbol>[^/.]+)`, `stock/(?P<symbol>[^/.]+)/sentiment`, (이름 없는 기본 3: market / trending / sources / recommendations / task_timeline 등),
  - `all`, `insights`(추정), `daily-keywords`, `daily-keywords/generate`, `keyword-detail`,
  - `market-feed`, `interest-options`, `personalized-feed`,
  - `news-events`, `news-events/impact-map`,
  - `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `ml-trend`,
  - `collection-logs`, `pipeline-health`, `llm-usage`, `task-timeline`, `neo4j-status`,
  - `ml-rollback-preview`, `ml-rollback`,
  - `alerts`, `alerts/(?P<alert_pk>\d+)/resolve`
- **리스크**: 단일 ViewSet 2,183줄 → `@extend_schema_view` 일괄 annotation 필수, 정규식 `url_path`는 `OpenApiParameter`로 명시해야 Swagger UI에서 제대로 표시

#### macro (10) — `macro/urls.py`
- `pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis (15) — `rag_analysis/urls.py`
- DataBasket (6): `baskets/`, `baskets/<pk>/`, `baskets/<pk>/add-item/`, `baskets/<pk>/add-stock-data/`, `baskets/<pk>/items/<item_id>/`, `baskets/<pk>/clear/`
- AnalysisSession (4): `sessions/`, `sessions/<pk>/`, `sessions/<pk>/messages/`, `sessions/<pk>/chat/stream/` (**SSE**)
- Monitoring (5): `monitoring/{usage,cost,cache,history,pricing}/`
- **리스크**: SSE는 OpenAPI 표준에 매끄럽게 매핑되지 않아 `responses.200.content."text/event-stream"` 수동 명세 필요

#### serverless (64) — `serverless/urls.py`
- Admin 대시보드 (12): `admin/dashboard/{overview,stocks,screener,market-pulse,news,system,tasks,actions}`, `admin/dashboard/actions/status/<task_id>/`, `admin/dashboard/news/categories/`, `.../<category_id>/`, `.../sector-options/`
- Market Movers (4): `movers`, `movers/<symbol>`, `sync`, `sync-now`
- Keywords (4): `keywords/batch`, `keywords/generate-all`, `keywords/generate-screener`, `keywords/<symbol>`
- Breadth (3): `breadth`, `breadth/history`, `breadth/sync`
- Heatmap (3): `heatmap/sectors`, `heatmap/sectors/<sector>/stocks`, `heatmap/sync`
- Presets (7): `presets`, `presets/trending`, `presets/shared/<share_code>`, `presets/import/<share_code>`, `presets/<preset_id>`, `presets/<preset_id>/execute`, `presets/<preset_id>/share`
- Filters/Screener (2): `filters`, `screener`
- Alerts (6): `alerts`, `alerts/history`, `alerts/history/<history_id>/read`, `alerts/history/<history_id>/dismiss`, `alerts/<alert_id>`, `alerts/<alert_id>/toggle`
- Thesis legacy (4): `thesis/generate`, `thesis/shared/<share_code>`, `thesis/<thesis_id>`, `thesis`
- ETF / Themes (9, `LEGACY_KEEP_UNTIL_DC2`): `etf/status`, `etf/sync`, `etf/resolve-url`, `etf/<etf_symbol>/holdings`, `etf/stock/<symbol>/themes`, `etf/stock/<symbol>/peers`, `themes`, `themes/refresh`, `themes/<theme_id>/stocks`
- LLM Relations (4): `llm-relations/extract`, `llm-relations/sync`, `llm-relations/stats`, `llm-relations/<symbol>`
- Institutional (3): `institutional/sync`, `institutional/<symbol>/peers`, `institutional/<symbol>`
- Regulatory/Patent (2): `regulatory/<symbol>`, `patent-network/<symbol>`
- Health (1): `health`
- **리스크**:
  - `@api_view` 함수 뷰 52개 → 스키마 자동 추론 불가, **전수 annotation 필수**
  - trailing slash 없는 라우트 다수(`movers`, `health`, `screener`, `themes`, `alerts` 등) vs. 슬래시 있는 라우트(`admin/dashboard/*`) 혼재 → URL 일관성 검토 필요
  - `thesis/*` 4개는 `thesis` 앱과 **이름 중복**(서빙 위치는 `serverless.thesis/*`) — 문서 태그에서 구분 필수, `deprecated=True` 표기 권장

#### thesis (약 31) — `thesis/urls.py`
- Conversation (4): `conversation/start/`, `conversation/respond/`, `conversation/news-issues/`, `conversation/suggest/`
- Monitoring (2): `<uuid:thesis_id>/dashboard/`, `<uuid:thesis_id>/indicators/<uuid:indicator_id>/readings/`
- Alerts (2): `alerts/`, `alerts/<uuid:aid>/read/`
- Router (3)
  - `ThesisViewSet`(`router` 등록, basename='thesis'): CRUD 6 + `@action` 2
  - nested `ThesisPremiseViewSet`(`/<uuid:thesis_id>/premises/` 하위): CRUD 6
  - nested `ThesisIndicatorViewSet`(`/<uuid:thesis_id>/indicators/` 하위): CRUD 6
- **리스크**: `<uuid:...>` path converter → drf-spectacular `OpenApiTypes.UUID` 타입 매핑 확인

#### validation (6) — `validation/api/urls.py`
- `<symbol>/summary/`, `<symbol>/metrics/`, `<symbol>/leader-comparison/`, `<symbol>/presets/`, `<symbol>/peer-preference/`, `<symbol>/llm-filter/`

#### chainsight (약 18) — `chainsight/api/urls.py`
- Market 고정 경로 (4): `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`
- Symbol 동적 경로 (3): `<symbol>/neighbors/`, `<symbol>/graph/`, `<symbol>/suggestions/`
- `WatchlistViewSet` (router): CRUD 6 + `@action` 5 = 11
  - `@action` 5건 확인: `chainsight/views/watchlist_views.py:97,114,131,161,203` (`detail=True, methods=['post']`)

#### sec_pipeline (2) — `sec_pipeline/urls.py`
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request (6) — `api_request/urls.py`
- `health/`(인증 불필요), `admin/providers/{status,rate-limits,cache,test,config}/` (IsAdminUser)

#### config 루트 (3) — `config/urls.py`
- `''` (api_root, **수동 하드코딩 JSON** — 9개 앱 누락)
- `health/` (프로젝트 health check)
- `admin/` (Django admin)

---

## 도입 작업 목록

### 3.1 drf-spectacular 설치 및 기본 설정 — 규모 S, ~0.5일

1. **의존성 추가**
   - `pyproject.toml` `[tool.poetry.dependencies]`에 `drf-spectacular = "^0.27"` 추가
   - `poetry lock && poetry install`
2. **Django settings (`config/settings.py`)**
   - `INSTALLED_APPS`에 `"drf_spectacular"` 추가 (현재 `rest_framework` 바로 아래가 적합)
   - `REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"`
   - `SPECTACULAR_SETTINGS` 신설: `TITLE`, `DESCRIPTION`, `VERSION`, `SERVE_INCLUDE_SCHEMA=False`, `TAGS`(앱별 11개 + 루트), `COMPONENT_SPLIT_REQUEST=True`, `ENUM_NAME_OVERRIDES`, `SECURITY`(Bearer JWT + Session 2중 스키마)
3. **`config/urls.py` 라우팅 3개 추가**
   - `api/schema/` → `SpectacularAPIView`
   - `api/schema/swagger-ui/` → `SpectacularSwaggerView`
   - `api/schema/redoc/` → `SpectacularRedocView`
4. **CI 검증**
   - `python manage.py spectacular --file schema.yml --validate` 를 GitHub Actions lint 단계에 추가 (스키마 drift 감지)
   - `drf_spectacular.generators` 경고 0건 목표로 점진 개선

### 3.2 공용 Serializer 정의 — 규모 M, 2~3일

- 모든 `APIView` / `GenericAPIView` / `ViewSet`에 **request / response Serializer 명시** 필요
- 현재 다수 뷰가 `Response({...})`로 dict를 바로 반환 → 자동 스키마 품질이 낮음
- 공용 응답(pagination, error, JWT 토큰)을 `serializers.Serializer` subclass로 정의해 `@extend_schema(responses={...})`에서 재사용
- 예상 신규 Serializer: Error(400/401/403/404/500) · PaginatedResponse · SyncStatus · JWT Token pair · KeywordBatch · MarketMoverItem · ScreenerFilterMeta 등 약 20~30개

### 3.3 `@extend_schema` annotation 범위

> 품질 2단 산정. 가벼운 annotation = `summary` + `tags`만 부여. 정밀 annotation = `parameters` + `request` + `responses` 전부 부여.

| 앱 | 실효 엔드포인트 | 가벼운(분/개) | 정밀(분/개) | 정밀 작업 시간 |
|----|---------------:|---------------:|------------:|---------------:|
| stocks | 39 | 5 | 20 | **약 13h** |
| users | 35 | 5 | 15 | 약 9h |
| news | 32 | 7 (정규식 url_path) | 25 | 약 13h |
| macro | 10 | 5 | 15 | 약 2.5h |
| rag_analysis | 15 | 7 (SSE 1건) | 25 | 약 6h |
| serverless | 64 | 7 (`@api_view` 특수) | 25 | 약 27h |
| thesis | 31 | 5 | 20 | 약 10h |
| validation | 6 | 5 | 15 | 약 1.5h |
| chainsight | 18 | 5 | 20 | 약 6h |
| sec_pipeline | 2 | 5 | 15 | 약 0.5h |
| api_request | 6 | 5 | 15 | 약 1.5h |
| **합계** | **약 258** | — | — | **약 90h (약 11.5 man-day)** |

> ※ config 루트 3건은 SpectacularSwagger로 대체될 수 있어 별도 산정 제외.

### 3.4 특수 케이스 — 수작업 annotation 필수

1. **`rag_analysis/sessions/<pk>/chat/stream/`** — SSE. `@extend_schema(responses={200: OpenApiResponse(response={"type":"string","format":"binary"}, description="text/event-stream")})` 수작업
2. **`serverless` `@api_view` 함수 52개** — 자동 스키마가 request body·query를 잡지 못함. 각 함수에 `@extend_schema(parameters=[...], request=..., responses=...)` 전수 작업 필요 → **최대 병목**
3. **`news.NewsViewSet`의 `@action` 30개** — `url_path`에 정규식(`(?P<symbol>[^/.]+)`, `alerts/(?P<alert_pk>\d+)/resolve`) 사용. `@extend_schema(parameters=[OpenApiParameter("symbol", OpenApiTypes.STR, OpenApiParameter.PATH)])` 명시 필요
4. **`thesis` UUID path converter** (`<uuid:thesis_id>`, `<uuid:indicator_id>`, `<uuid:aid>`) — `OpenApiTypes.UUID` 매핑 확인 (drf-spectacular는 Django converter를 기본 인식하지만 폴백 확인 필요)
5. **JWT 인증(`users/jwt/*`)** — `simplejwt`는 drf-spectacular 공식 지원. `drf_spectacular.contrib.rest_framework_simplejwt` extension 활성화
6. **Admin 엔드포인트**(`serverless/admin/*` 12, `api_request/admin/*` 5) — `IsAdminUser` 권한 → `tags=["Admin"]` + 별도 SecurityRequirement 부여
7. **Legacy/Deprecated 라우트** — `serverless/thesis/*` 4건, `serverless/etf/*` 9건(주석 `LEGACY_KEEP_UNTIL_DC2`, `LEGACY REMOVED: screener/chain-sight`) → `@extend_schema(deprecated=True)`
8. **`config/views.py:api_root` 수동 JSON** — drf-spectacular 도입 이후 **중복이므로 폐기** 검토(혹은 `/api/schema/swagger-ui/`로 리다이렉트)
9. **이중 `authentication` 정책** — JWT + Session 동시 등록(`config/settings.py:331~339`) → `SPECTACULAR_SETTINGS["SECURITY"]`에 두 스키마 모두 노출할지, JWT만 주 스키마로 표기할지 정책 결정

### 3.5 단계별 로드맵 (1인 기준)

| 단계 | 범위 | 기간 | 산출물 |
|------|------|-----:|--------|
| **P0: 설치·인프라** | drf-spectacular 설치, settings/urls 수정, CI validate | 0.5일 | `/api/schema/swagger-ui/` 접근 가능 |
| **P1: 최소 운영 품질** | 모든 뷰에 가벼운 `@extend_schema(summary, tags)` 부여, 태그 11개 정의, `TAGS_SORTER` 지정 | 3일 | 앱별 정렬된 Swagger UI |
| **P2: 공용 응답 스키마** | Error / PaginatedResponse / JWT SecurityScheme / Pagination extension 정비 | 1일 | 400/401/403/404/500 공통 응답 |
| **P3: 정밀 annotation Tier 1** | stocks, users, validation, macro, chainsight, thesis, sec_pipeline, api_request (약 162개) | 5일 | 정확한 request/response 스키마 |
| **P4: 정밀 annotation Tier 2** | serverless(`@api_view` 52) + news(2,183줄 ViewSet 32) + rag_analysis(SSE 포함) — 병목 | 5일 | 고난도 뷰 annotation 완료 |
| **P5: 배포 + 타입 동기화** | 사내 접근 제어(IsAdminUser로 UI 보호), `contracts/openapi.yaml` 자동 동기화, `openapi-typescript` 로 Next.js 타입 생성 | 0.5일 | drift 감지 + FE 타입 자동 생성 |
| **총 소요** | — | **약 15일 (3주)** | P3/P4 병렬 배정 시 단축 가능 |

### 3.6 선결 사항 / 위험 요소

- **비대 파일 분할 선행 권장**
  - `news/api/views.py` **2,183줄 / `@action` 30**
  - `serverless/views.py` **3,405줄 / `@api_view` 52**
  - 두 파일을 도메인별 하위 모듈로 분할하지 않으면 P4 annotation PR의 리뷰 부담이 극도로 커짐. (docs/architecture/autonomous_agent_tasks.md에도 동일 관측이 있음)
- **URL 일관성 혼재** — serverless의 `/movers`, `/health`, `/screener`, `/themes`, `/alerts`, `/breadth` 등 다수 경로가 trailing slash 없음. 동 앱 admin 경로는 슬래시 있음. OpenAPI 스펙 동작엔 영향 없으나 문서 가독성 저하 + `APPEND_SLASH` 처리 명세 필요
- **`contracts/` 디렉토리와의 이중 관리** — `CLAUDE.md`가 "API 인터페이스 계약(OpenAPI + 공유 타입)"을 contracts에 둔다고 명시. 자동 생성물과 수기 contracts 중 **단일 소스 정책 확정**이 선결. 권장: 자동 생성 → `contracts/openapi.yaml` 동기화(CI drift 검증)
- **JWT + Session 이중 인증** — `DEFAULT_AUTHENTICATION_CLASSES`에 두 클래스 모두 등록. SecurityScheme 2중 노출 정책 결정 필요
- **수동 `api_root` JSON의 괴리** — 9개 앱 누락 + 엔드포인트 이름 rot(예: `/api/v1/analysis/`는 `analysis` 앱이 이미 CLAUDE.md 상 제거 방향) → drf-spectacular 도입과 동시에 **폐기 또는 리다이렉트** 결정 필요
- **Serializer 부재로 인한 자동 스키마 품질 저하** — `Response({...})` dict 직접 반환이 관행화 → 정밀 annotation에 앞서 공용 Serializer 일괄 신설(약 2~3 man-day, 3.2 단계) 필수
- **SPA(Next.js 16) 타입 동기화** — 도입 후 `openapi-typescript` 파이프라인을 구축하면 frontend `authAxios`·TanStack Query 호출부 타입 안정성이 크게 향상

---

## 요약

- **API 자동 문서화 인프라 전무** — drf-spectacular/drf-yasg 미설치, Swagger/OpenAPI 엔드포인트 없음. `config/views.py:api_root`의 수기 JSON만 존재하며 9개 앱(news, macro, rag_analysis, serverless, thesis, validation, chainsight, sec_pipeline, api_request) 누락으로 실제 엔드포인트와 괴리
- **실효 엔드포인트 약 261개** (11개 앱 + 루트 3). stocks 39 / serverless 64 / users 35 / news 약 32 / thesis 약 31 / chainsight 약 18 / rag_analysis 15 / macro 10 / validation 6 / api_request 6 / sec_pipeline 2
- **P0 도입은 0.5일**로 Swagger UI를 띄울 수 있으나, **정밀 문서(스키마 + 공용 Serializer)까지는 약 15일(1인)**의 `@extend_schema` 작업이 필요. 특히 `serverless/views.py`(3,405줄, `@api_view` 52)와 `news/api/views.py`(2,183줄, `@action` 30)가 병목
- **선행 권장 3건**: (1) news/serverless 뷰 파일 도메인 분할, (2) `contracts/` 단일 소스 정책 확정, (3) 공용 Error/Paginated/JWT Serializer 신설 — 이 3가지를 P1 직전에 처리하면 P3/P4 작업량 실질 감소
- **전일(4월 22일) 대비 URL 라우팅 변동 없음** — annotation 작업량·우선순위·리스크 판정 동일. 수치는 본 감사에서 `urls.py` 원문 기준으로 재카운트·정밀화(예: stocks 39, users 35 — 22일 보고서 64/39는 총합 기준 오차로 판단됨)
