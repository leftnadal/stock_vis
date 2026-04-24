# API 문서 감사 보고서

- 감사일: 2026-04-24
- 감사 대상: `/Users/byeongjinjeong/Desktop/stock_vis` Django REST Framework 백엔드
- 감사 범위: 문서 자동화 도구 설치 여부 · 앱별 엔드포인트 목록 · drf-spectacular 도입 시 작업량
- 성격: **읽기 전용 감사** (코드 수정 없음)
- 카운트 근거: `urls.py`의 `path()` 원문 카운트 + `@action`/`@api_view` 전수 조사 (직접 검증)

---

## 현재 상태

### 1.1 API 문서 자동화 도구 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | **미설치** | `pyproject.toml` `[tool.poetry.dependencies]` / dev group 모두 없음, `poetry.lock`에도 없음 |
| `drf-yasg` | **미설치** | 동일 |
| `coreapi` / `coreschema` / `openapi-*` | 미설치 | 동일 |
| `config/settings.py`의 `INSTALLED_APPS`에 `drf_spectacular` | **없음** | `config/settings.py:166~195` |
| `REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"]` | **미지정** | `config/settings.py:332~340`에 지정 없음 (DRF 기본 `AutoSchema`) |
| `SPECTACULAR_SETTINGS` 블록 | **없음** | `grep SPECTACULAR` 0건 |
| `config/urls.py`의 schema/swagger/redoc 라우트 | **없음** | `config/urls.py:22~44` 확인, 관련 라우팅 전무 |
| `extend_schema` / `swagger_auto_schema` 데코레이터 | **0건** | 애플리케이션 `*.py` 전수 grep 0건 (매칭은 감사 스크립트/기존 감사 문서에만 존재) |

**결론**: OpenAPI/Swagger 자동 생성 인프라가 **전무**하다. 어떤 형태로도 기계가 읽을 수 있는 API 스펙이 존재하지 않는다.

### 1.2 현재 문서화 방식

- `config/views.py:api_root` 뷰가 **수동 하드코딩 JSON**으로 일부 엔드포인트만 노출.
  - 포함: `users` JWT/포트폴리오/즐겨찾기 일부, `stocks` 일부, `analysis`(사실상 제거된 앱)
  - **누락 앱 9개**: `news`, `macro`, `rag_analysis`, `serverless`, `thesis`, `validation`, `chainsight`, `sec_pipeline`, `api_request`
  - → 실제 엔드포인트와 큰 괴리. 운영 문서로 신뢰할 수 없음.
- Swagger UI / ReDoc / OpenAPI JSON·YAML **자동 생성 경로 없음**.
- `CLAUDE.md`가 언급하는 `contracts/` 디렉토리는 수기 관리(OpenAPI 스펙 + 공유 TS 타입) — 본 감사 범위 밖이나 자동 생성 도구 도입 시 **단일 소스 정책** 결정 필요.

### 1.3 자동 생성 가능성

- DRF 표준 패턴(`APIView`, `GenericAPIView`, `ViewSet`, `@api_view`) 전반 사용 → drf-spectacular 설치만으로 **최소 품질의 OpenAPI 스펙은 즉시 생성 가능**.
- `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`에 `JWTAuthentication` + `SessionAuthentication` 동시 등록 → `SPECTACULAR_SETTINGS["SECURITY"]`에서 2중 스키마 노출 정책을 결정해야 함.
- 다만 자동 추론 품질이 낮을 것으로 예상되는 요인:
  1. `serverless/views.py`의 `@api_view` **함수 기반 뷰 52개** → request body/query 자동 추론 제약
  2. 대부분의 뷰가 `Response({...})`로 dict 직접 반환 → response schema 부재
  3. `news/api/views.py` 단일 `NewsViewSet` **2,183줄 / `@action` 30개**, 일부가 정규식 `url_path`
  4. `rag_analysis/sessions/<pk>/chat/stream/`는 SSE (`text/event-stream`) 스트리밍
  5. `thesis`의 `<uuid:...>` path converter → `OpenApiTypes.UUID` 매핑 검증 필요

→ **정밀 스펙**을 원할 경우 `@extend_schema` 수작업 annotation과 공용 Serializer 신설이 필수.

---

## 엔드포인트 목록 (앱별 테이블)

> `urls.py`의 `path()`는 **파일당 라우트 수**. ViewSet + router 등록의 경우 **실효 엔드포인트**는 router가 자동 확장하는 CRUD 액션(ModelViewSet 6개) + `@action` 데코레이터 수를 합산해 별도 표기.
> 카운트는 본 감사에서 직접 검증:
> - `path()` 수: `grep -c "^\s*path(" <file>`
> - `@action` 수: `grep -c "@action" <file>`
> - `@api_view` 수: `grep -c "@api_view" <file>`

### 2.1 앱별 요약

| 앱 (mount path) | `path()` | ViewSet CRUD/`@action` | 실효 엔드포인트(추정) | 주요 뷰 파일 |
|----------------|---------:|:-----------------------|----------------------:|:-------------|
| **stocks** (`/api/v1/stocks/`) | 39 | — | **39** | `stocks/views*.py` (9개 분할) |
| **users** (`/api/v1/users/`) | 35 | — | **35** | `users/views.py`, `users/jwt_views.py` |
| **news** (`/api/v1/news/`) | 1 (router) | `NewsViewSet`: CRUD(list/retrieve) 2 + `@action` 30 | **32** | `news/api/views.py` (**2,183줄**) |
| **macro** (`/api/v1/macro/`) | 10 | — | **10** | `macro/views.py` |
| **rag_analysis** (`/api/v1/rag/`) | 15 | — | **15** | `rag_analysis/views.py` (SSE 1건 포함) |
| **serverless** (`/api/v1/serverless/`) | 64 | `@api_view` 52 (views.py) + admin CBV 12 (views_admin.py) | **64** | `serverless/views.py` (**3,405줄**) + `views_admin.py` (694줄) |
| **thesis** (`/api/v1/thesis/`) | 11 (+ nested router 3개) | `ThesisViewSet` 6 CRUD + 1 `@action`, `ThesisPremiseViewSet` 6 CRUD, `ThesisIndicatorViewSet` 6 CRUD + 1 `@action` | **약 28** (APIView 8 + ThesisVS 7 + PremiseVS 6 + IndicatorVS 7) | `thesis/views/` 패키지 |
| **validation** (`/api/v1/validation/`) | 6 | — | **6** | `validation/api/views.py` |
| **chainsight** (`/api/v1/chainsight/`) | 7 (+ router) | `WatchlistViewSet` 6 CRUD + 5 `@action` | **18** (고정 7 + Watchlist 11) | `chainsight/api/views.py` + `views/watchlist_views.py` |
| **sec_pipeline** (`/api/v1/sec-pipeline/`) | 2 | — | **2** | `sec_pipeline/views.py` |
| **api_request** (`/api/v1/`) | 6 | — | **6** | `api_request/admin_views.py` |
| **config (루트)** | 3 (직접 뷰) + 11 (include) | — | **3** | `config/views.py:api_root`, `health_check`, `admin/` |
| **총계** | **199 (path())** | — | **약 258** | 11개 앱 + 루트 |

### 2.2 앱별 상세 내역

#### stocks (39) — `stocks/urls.py`
- 페이지/검색 (3): `''`(DashboardView), `stock/<symbol>/`, `search/`
- Chart/Overview/재무제표 (5): `api/chart/<symbol>/`, `api/overview/<symbol>/`, `api/balance-sheet/<symbol>/`, `api/income-statement/<symbol>/`, `api/cashflow/<symbol>/`
- Sync (1): `api/sync/<symbol>/`
- MVP (4): `api/mvp/stocks/`, `api/mvp/stock/<symbol>/`, `api/mvp/rag/<symbol>/`, `api/mvp/sectors/`
- 기술지표 (3): `api/indicators/<symbol>/`, `api/signal/<symbol>/`, `api/indicators/compare/`
- 심볼 검색 (3): `api/search/symbols/`, `api/search/validate/<symbol>/`, `api/search/popular/`
- Market Movers (1): `api/market-movers/`
- Fundamentals (5): `api/fundamentals/{key-metrics|ratios|dcf|rating|all}/<symbol>/`
- Screener (6): `api/screener/`, `api/screener/{large-cap|high-dividend|low-beta}/`, `api/screener/sector/<sector>/`, `api/screener/exchange/<exchange>/`
- Exchange Quotes (5): `api/quotes/{index,<symbol>,batch,major-indices,sector-performance}/`
- EOD (3): `eod/dashboard/`, `eod/signal/<signal_id>/`, `eod/pipeline/status/`

#### users (35) — `users/urls.py`
- JWT 인증 (7): `jwt/{signup,login,logout,refresh,verify,change-password,profile}/`
- 세션 인증 하위호환 (6): `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/`
- 즐겨찾기 (3): `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/`
- 포트폴리오 (9): `portfolio/`, `portfolio/summary/`, `portfolio/table/`, `portfolio/refresh/`, `portfolio/<pk>/`, `portfolio/<pk>/quick-update/`, `portfolio/symbol/<symbol>/`, `portfolio/symbol/<symbol>/refresh/`, `portfolio/symbol/<symbol>/status/`
- 관심사 (2): `interests/`, `interests/<pk>/`
- 워치리스트 (8): `watchlist/`, `watchlist/<pk>/`, `watchlist/<pk>/add-stock/`, `watchlist/<pk>/bulk-add/`, `watchlist/<pk>/bulk-remove/`, `watchlist/<pk>/stocks/`, `watchlist/<pk>/stocks/<symbol>/`, `watchlist/<pk>/stocks/<symbol>/remove/`

#### news (약 32) — `news/api/urls.py` + `NewsViewSet`
- `DefaultRouter().register(r'', NewsViewSet, basename='news')` — 루트에 등록 → `/` (list), `/<pk>/` (retrieve) 기본 2건
- `@action` **30개** (전수 grep 결과: 2,183줄 단일 파일)
  - 심볼 기반: `stock/(?P<symbol>[^/.]+)`, `stock/(?P<symbol>[^/.]+)/sentiment`
  - 피드/메타: `market`, `trending`, `sources`, `all`, `recommendations`, `market-feed`, `interest-options`, `personalized-feed`, `insights`, `daily-keywords`, `daily-keywords/generate`, `keyword-detail`
  - 이벤트/맵: `news-events`, `news-events/impact-map`
  - ML/모니터링: `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `ml-trend`, `ml-rollback-preview`, `ml-rollback`
  - 파이프라인: `collection-logs`, `pipeline-health`, `llm-usage`, `task-timeline`, `neo4j-status`
  - 알림: `alerts`, `alerts/(?P<alert_pk>\d+)/resolve`
- **리스크**: 단일 ViewSet 2,183줄 → `@extend_schema_view` 일괄 annotation 필수. 정규식 `url_path`는 `OpenApiParameter`로 명시해야 Swagger UI에서 제대로 렌더링됨.

#### macro (10) — `macro/urls.py`
- `pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis (15) — `rag_analysis/urls.py`
- DataBasket (6): `baskets/`, `baskets/<pk>/`, `baskets/<pk>/add-item/`, `baskets/<pk>/add-stock-data/`, `baskets/<pk>/items/<item_id>/`, `baskets/<pk>/clear/`
- AnalysisSession (4): `sessions/`, `sessions/<pk>/`, `sessions/<pk>/messages/`, **`sessions/<pk>/chat/stream/` (SSE)**
- Monitoring (5): `monitoring/{usage,cost,cache,history,pricing}/`
- **리스크**: SSE(`text/event-stream`)는 OpenAPI 표준 매핑이 매끄럽지 않음 → `@extend_schema(responses={200: OpenApiResponse(response={"type":"string","format":"binary"}, description="text/event-stream")})` 수작업 필수.

#### serverless (64) — `serverless/urls.py`
- Admin 대시보드 (12): `admin/dashboard/{overview,stocks,screener,market-pulse,news,system,tasks,actions}`, `admin/dashboard/actions/status/<task_id>/`, `admin/dashboard/news/categories/`, `.../<category_id>/`, `.../sector-options/`
- Market Movers (4): `movers`, `movers/<symbol>`, `sync`, `sync-now`
- Keywords (4): `keywords/batch`, `keywords/generate-all`, `keywords/generate-screener`, `keywords/<symbol>`
- Breadth (3): `breadth`, `breadth/history`, `breadth/sync`
- Heatmap (3): `heatmap/sectors`, `heatmap/sectors/<sector>/stocks`, `heatmap/sync`
- Presets (7): `presets`, `presets/trending`, `presets/shared/<share_code>`, `presets/import/<share_code>`, `presets/<preset_id>`, `presets/<preset_id>/execute`, `presets/<preset_id>/share`
- Filters/Screener (2): `filters`, `screener`
- Alerts (6): `alerts`, `alerts/history`, `alerts/history/<history_id>/read`, `alerts/history/<history_id>/dismiss`, `alerts/<alert_id>`, `alerts/<alert_id>/toggle`
- Thesis legacy (4): `thesis/generate`, `thesis/shared/<share_code>`, `thesis/<thesis_id>`, `thesis` — **서빙 위치는 `serverless.thesis/*`로 `thesis` 앱과 이름 충돌**
- ETF/Themes (9, 주석: `LEGACY_KEEP_UNTIL_DC2`): `etf/status`, `etf/sync`, `etf/resolve-url`, `etf/<etf_symbol>/holdings`, `etf/stock/<symbol>/themes`, `etf/stock/<symbol>/peers`, `themes`, `themes/refresh`, `themes/<theme_id>/stocks`
- LLM Relations (4): `llm-relations/extract`, `llm-relations/sync`, `llm-relations/stats`, `llm-relations/<symbol>`
- Institutional (3): `institutional/sync`, `institutional/<symbol>/peers`, `institutional/<symbol>`
- Regulatory/Patent (2): `regulatory/<symbol>`, `patent-network/<symbol>`
- Health (1): `health`
- **리스크**:
  - `@api_view` 함수 뷰 52개 → 스키마 자동 추론 제약. 전수 annotation 필요 (**최대 병목**)
  - trailing slash 없는 라우트 다수(`movers`, `health`, `screener`, `themes`, `alerts`, `breadth`) vs. 슬래시 있는 라우트(`admin/dashboard/*`) 혼재
  - `thesis/*` 4건은 `thesis` 앱과 이름 중복 → 문서 태그 구분 + `deprecated=True` 표기 권장

#### thesis (약 28) — `thesis/urls.py` (`path()` 11 + 3 router)
- APIView 직접 경로 (8): `conversation/{start,respond,news-issues,suggest}/`, `<uuid:thesis_id>/dashboard/`, `<uuid:thesis_id>/indicators/<uuid:indicator_id>/readings/`, `alerts/`, `alerts/<uuid:aid>/read/`
- 메인 router `ThesisViewSet` (basename='thesis'): ModelViewSet 6 CRUD + `@action` 1 = **7**
- Nested router `ThesisPremiseViewSet` (`<uuid:thesis_id>/premises/`): ModelViewSet 6 CRUD = **6**
- Nested router `ThesisIndicatorViewSet` (`<uuid:thesis_id>/indicators/`): ModelViewSet 6 CRUD + `@action` 1 = **7**
- **리스크**: `<uuid:...>` path converter → drf-spectacular `OpenApiTypes.UUID` 매핑 확인 필요

#### validation (6) — `validation/api/urls.py`
- `<symbol>/{summary,metrics,leader-comparison,presets,peer-preference,llm-filter}/`

#### chainsight (약 18) — `chainsight/api/urls.py`
- 고정 경로 (4): `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`
- 동적 심볼 경로 (3): `<symbol>/{neighbors,graph,suggestions}/`
- `WatchlistViewSet` (router, basename='watchlist'): ModelViewSet 6 CRUD + `@action` 5 (모두 `detail=True, methods=['post']`) = **11**

#### sec_pipeline (2) — `sec_pipeline/urls.py`
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request (6) — `api_request/urls.py`
- `health/` (인증 불필요), `admin/providers/{status,rate-limits,cache,test,config}/` (IsAdminUser)

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
   - `INSTALLED_APPS`에 `"drf_spectacular"` 추가 (`rest_framework` 바로 아래가 적합)
   - `REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"`
   - `SPECTACULAR_SETTINGS` 신설: `TITLE`, `DESCRIPTION`, `VERSION`, `SERVE_INCLUDE_SCHEMA=False`, `TAGS`(앱별 11개 + 루트), `COMPONENT_SPLIT_REQUEST=True`, `ENUM_NAME_OVERRIDES`, `SECURITY`(Bearer JWT + Session 이중 스키마)
3. **`config/urls.py` 라우팅 3개 추가**
   - `api/schema/` → `SpectacularAPIView`
   - `api/schema/swagger-ui/` → `SpectacularSwaggerView`
   - `api/schema/redoc/` → `SpectacularRedocView`
4. **CI 검증**
   - `python manage.py spectacular --file schema.yml --validate` 를 GitHub Actions에 추가 (drift 감지)
   - `drf_spectacular.generators` 경고 0건을 점진 목표로 설정

### 3.2 공용 Serializer 정의 — 규모 M, 2~3일

- 모든 `APIView`/`GenericAPIView`/`ViewSet`에 **request/response Serializer 명시** 필요
- 현재 다수 뷰가 `Response({...})`로 dict를 직접 반환 → 자동 스키마 품질이 낮음
- 공용 응답(pagination, error, JWT 토큰)을 `serializers.Serializer` subclass로 정의하여 `@extend_schema(responses={...})`에서 재사용
- 예상 신규 Serializer (약 20~30개):
  - Error 응답(400/401/403/404/500)
  - `PaginatedResponse<T>`
  - `SyncStatus`, `TaskStatus`, `HealthCheck`
  - `JWTTokenPair`, `JWTVerify`
  - `KeywordBatch`, `MarketMoverItem`, `ScreenerFilterMeta`
  - `ChainSightNode`, `ChainSightEdge`
  - `ThesisDashboardPayload`, `IndicatorReading`

### 3.3 `@extend_schema` annotation 작업량

> 2단 품질 기준.
> - **가벼운 annotation** = `summary` + `tags`만 부여 (자동 추론 보완)
> - **정밀 annotation** = `parameters` + `request` + `responses` 전부 명시

| 앱 | 실효 엔드포인트 | 정밀 annotation (분/개) | 정밀 작업 시간 |
|----|----------------:|------------------------:|---------------:|
| stocks | 39 | 20 | 약 13h |
| users | 35 | 15 | 약 9h |
| news | 32 | 25 (정규식 url_path + ViewSet 단일파일) | 약 13h |
| macro | 10 | 15 | 약 2.5h |
| rag_analysis | 15 | 25 (SSE 1건 포함) | 약 6h |
| serverless | 64 | 25 (`@api_view` 특수) | 약 27h |
| thesis | 28 | 20 (UUID path converter) | 약 9h |
| validation | 6 | 15 | 약 1.5h |
| chainsight | 18 | 20 | 약 6h |
| sec_pipeline | 2 | 15 | 약 0.5h |
| api_request | 6 | 15 | 약 1.5h |
| **합계** | **약 255** | — | **약 89h (~11 man-day)** |

> config 루트 3건은 SpectacularSwaggerView로 대체 가능하므로 산정 제외.

### 3.4 특수 케이스 — 수작업 annotation 필수

1. **`rag_analysis/sessions/<pk>/chat/stream/` (SSE)** — `@extend_schema(responses={200: OpenApiResponse(response={"type":"string","format":"binary"}, description="text/event-stream")})`
2. **`serverless` `@api_view` 함수 52개** — 자동 추론 한계로 전수 `@extend_schema(parameters=..., request=..., responses=...)` 필수 → **최대 병목**
3. **`news.NewsViewSet` `@action` 30개** — 정규식 `url_path`(`(?P<symbol>[^/.]+)`, `alerts/(?P<alert_pk>\d+)/resolve`)는 `OpenApiParameter("symbol", OpenApiTypes.STR, OpenApiParameter.PATH)` 명시 필요
4. **`thesis` UUID path converter** (`<uuid:thesis_id>`, `<uuid:indicator_id>`, `<uuid:aid>`) — `OpenApiTypes.UUID` 매핑 검증
5. **JWT 인증 (`users/jwt/*`)** — `drf_spectacular.contrib.rest_framework_simplejwt` 공식 extension 활성화
6. **Admin 엔드포인트** (`serverless/admin/*` 12개, `api_request/admin/*` 5개) — `IsAdminUser` → `tags=["Admin"]` + 별도 SecurityRequirement
7. **Legacy/Deprecated 라우트** — `serverless/thesis/*` 4개, `serverless/etf/*` 9개 (`LEGACY_KEEP_UNTIL_DC2`) → `@extend_schema(deprecated=True)`
8. **`config/views.py:api_root` 수동 JSON** — drf-spectacular 도입 시 **중복이므로 폐기** 또는 `/api/schema/swagger-ui/`로 리다이렉트
9. **이중 authentication 정책** — `JWTAuthentication` + `SessionAuthentication` 동시 등록 → 두 SecurityScheme 동시 노출 vs. JWT 단일화 정책 결정 필요

### 3.5 단계별 로드맵 (1인 기준)

| 단계 | 범위 | 기간 | 산출물 |
|------|------|-----:|--------|
| **P0: 설치·인프라** | drf-spectacular 설치, settings/urls 수정, CI validate | 0.5일 | `/api/schema/swagger-ui/` 접근 가능 |
| **P1: 최소 운영 품질** | 모든 뷰에 가벼운 `@extend_schema(summary, tags)` 부여, 태그 11개 정의, `TAGS_SORTER` 지정 | 3일 | 앱별 정렬된 Swagger UI |
| **P2: 공용 응답 스키마** | Error/Paginated/JWT SecurityScheme/Pagination extension 정비 | 1일 | 400/401/403/404/500 공통 응답 |
| **P3: 정밀 annotation Tier 1** | stocks, users, validation, macro, chainsight, thesis, sec_pipeline, api_request (약 150개) | 5일 | request/response 정확 스펙 |
| **P4: 정밀 annotation Tier 2** | serverless(`@api_view` 52) + news(단일 파일 `@action` 30) + rag_analysis(SSE 포함) — 병목 | 5일 | 고난도 뷰 annotation 완료 |
| **P5: 배포 + 타입 동기화** | Swagger UI 접근 제어(IsAdminUser), `contracts/openapi.yaml` 자동 동기화, `openapi-typescript`로 Next.js 타입 생성 | 0.5일 | drift 감지 + FE 타입 자동 생성 |
| **총 소요** | — | **약 15일 (3주)** | P3/P4 병렬화 시 단축 가능 |

### 3.6 선결 사항 / 위험 요소

- **비대 파일 분할 선행 권장**
  - `news/api/views.py` **2,183줄 / `@action` 30**
  - `serverless/views.py` **3,405줄 / `@api_view` 52**
  - 두 파일을 도메인별 하위 모듈로 분할하지 않으면 P4 annotation PR의 리뷰 부담이 과도해짐
- **URL 일관성 혼재** — serverless의 `/movers`, `/health`, `/screener`, `/themes`, `/alerts`, `/breadth` 등은 trailing slash 없음. 같은 앱 admin 경로는 슬래시 있음. OpenAPI 동작엔 영향 없으나 가독성 저하
- **`contracts/` vs 자동 생성 이중 관리** — `CLAUDE.md`가 "API 인터페이스 계약"을 `contracts/`에 두도록 명시 → **단일 소스 정책 확정** 필수. 권장: 자동 생성 → `contracts/openapi.yaml` 동기화(CI drift 검증)
- **JWT + Session 이중 인증** — `DEFAULT_AUTHENTICATION_CLASSES`에 둘 다 등록. SecurityScheme 2중 노출 vs. JWT 단일화 결정 필요
- **수동 `api_root` JSON의 괴리** — 9개 앱 누락 + 이미 제거 방향인 `analysis` 언급. drf-spectacular 도입과 동시에 **폐기 또는 리다이렉트**
- **Serializer 부재로 인한 자동 스키마 품질 저하** — `Response({...})` dict 직접 반환이 관행 → 정밀 annotation에 앞서 공용 Serializer 일괄 신설 (3.2 단계)
- **SPA(Next.js 16) 타입 동기화** — 도입 후 `openapi-typescript` 파이프라인 구축 시 frontend `authAxios` · TanStack Query 타입 안정성 향상

---

## 요약

- **API 자동 문서화 인프라 전무** — drf-spectacular/drf-yasg 미설치, `SPECTACULAR_SETTINGS` 없음, `extend_schema`/`swagger_auto_schema` 소스 0건. `config/views.py:api_root`의 수기 JSON만 존재하며 9개 앱(news, macro, rag_analysis, serverless, thesis, validation, chainsight, sec_pipeline, api_request) 누락
- **실효 엔드포인트 약 258개** (11개 앱 + 루트 3). `urls.py` 원문 `path()` 합계는 **199** — 차이는 router가 자동 확장하는 ModelViewSet CRUD와 `@action`에서 발생
  - 상세: stocks 39 / serverless 64 / users 35 / news 32 / thesis 28 / chainsight 18 / rag_analysis 15 / macro 10 / validation 6 / api_request 6 / sec_pipeline 2 / 루트 3
- **P0 도입은 0.5일**로 Swagger UI 기동 가능. **정밀 문서(스키마 + 공용 Serializer)까지는 약 15일 (1인)** 의 `@extend_schema` 작업 필요. 특히 `serverless/views.py`(3,405줄, `@api_view` 52)와 `news/api/views.py`(2,183줄, `@action` 30)가 병목
- **선행 권장 3건**: (1) news/serverless 뷰 파일 도메인 분할, (2) `contracts/` 단일 소스 정책 확정, (3) 공용 Error/Paginated/JWT Serializer 신설 — 이 3가지를 P1 직전에 처리하면 P3/P4 작업량 실질 감소
- **4월 22일 감사 대비 변동 없음** — URL 라우팅·views 파일 구조 그대로. 카운트는 본 감사에서 `path()`/`@action`/`@api_view` 원문 기준으로 직접 재검증
