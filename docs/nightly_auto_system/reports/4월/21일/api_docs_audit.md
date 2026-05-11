# API 문서 감사 보고서

- 감사일: 2026-04-21
- 감사 대상: `/Users/byeongjinjeong/Desktop/stock_vis` Django REST Framework 백엔드
- 감사 범위: API 문서화 도구 설치 여부, 전체 엔드포인트 목록, drf-spectacular 도입 시 예상 작업량
- 성격: **읽기 전용 감사** — 소스 수정 없음

---

## 현재 상태

### 1.1 문서 자동화 도구 설치 여부

| 도구 | 상태 | 확인 위치 |
|------|------|-----------|
| `drf-spectacular` | **미설치** | `pyproject.toml` [tool.poetry.dependencies] / [tool.poetry.group.dev.dependencies] 미포함 |
| `drf-yasg` | **미설치** | 동일 |
| `coreapi` / `coreschema` | 미설치 | 동일 |
| REST framework 내장 스키마(`SchemaGenerator`) 사용 | 미구성 | `config/urls.py`에 `get_schema_view` 라우팅 없음 |

**코드 그렙 결과** (프로젝트 내 `*.py` 대상):

- 검색 패턴: `drf.spectacular|drf.yasg|SPECTACULAR|SWAGGER|OpenAPI|swagger|redoc|drf_spectacular|drf_yasg` (대소문자 무시)
- 결과: **0개 파일 매치** (프로젝트 어디에도 관련 import/설정이 없음)

### 1.2 현재 문서화 방식

- `config/views.py:12-70` `api_root` 뷰가 **수동 하드코딩 JSON** 형식으로 주요 엔드포인트 몇 개만 나열 (users / stocks / analysis 일부). serverless, thesis, chainsight, validation, sec_pipeline, rag_analysis 등 **대부분의 앱이 누락**된 상태로 실제 엔드포인트와 괴리가 큼.
- Swagger UI, ReDoc, OpenAPI JSON/YAML 스펙 **자동 생성 경로 없음**.
- `contracts/` 디렉토리에 OpenAPI 스펙이 존재한다면(CLAUDE.md 언급) 수기 관리 중일 가능성이 높음(감사 범위 밖, 별도 확인 필요).

### 1.3 자동 생성 가능 여부 판단

- DRF 기반 View/ViewSet이 표준 패턴(`APIView`, `GenericAPIView`, `ViewSet`, `@api_view`)으로 작성되어 있어, **drf-spectacular 설치만으로 최소 스펙 자동 생성 가능**.
- 단, 다수의 뷰가 `@api_view` 함수 기반이거나 커스텀 응답 구조를 사용하므로 **자동 생성 결과는 제목·파라미터·응답 스키마가 부정확**할 것으로 예상. 고품질 문서를 위해서는 `@extend_schema` 수작업 annotation이 필수.

---

## 엔드포인트 목록 (앱별 테이블)

> `path()` 개수는 `urls.py`에 등록된 라우트 수. ViewSet + router 등록의 경우 라우터가 자동 확장하는 CRUD 액션과 `@action` 데코레이터 개수를 합산해 **실효 엔드포인트 수**로 별도 집계.

### 2.1 앱별 요약

| 앱 (mount path) | urls.py `path()` 등록 수 | ViewSet 자동 확장 / `@action` | 실효 엔드포인트(추정) | 비고 |
|----------------|-------------------------:|:-----------------------------:|----------------------:|------|
| **stocks** (`/api/v1/stocks/`) | 64 | — | **64** | 대시보드/차트/검색/기술지표/펀더멘털/스크리너/거래소 시세/EOD 대시보드 |
| **users** (`/api/v1/users/`) | 39 | — | **39** | JWT 인증 7 + 세션 인증 6 + 즐겨찾기 3 + 포트폴리오 9 + 관심사 2 + 워치리스트 9 + 기타 3 |
| **news** (`/api/v1/news/`) | 1 (router) | NewsViewSet에 `@action` 30개 | **30+** | 단일 ViewSet이 stock_news / sentiment / market / trending / all / sources / daily-keywords / insights / market-feed / personalized-feed / news-events / ml-status / ml-shadow-report / ml-weekly-report / ml-lightgbm-readiness / recommendations / collection-logs / pipeline-health / ml-trend / llm-usage / task-timeline / neo4j-status / ml-rollback(-preview) / alerts / alerts/resolve 등을 담당. **단일 파일 2,183줄로 비대** |
| **macro** (`/api/v1/macro/`) | 10 | — | **10** | Market Pulse(fear-greed, rates, inflation, global, calendar, vix, sectors) + sync |
| **rag_analysis** (`/api/v1/rag/`) | 15 | — | **15** | DataBasket 6 + AnalysisSession 4(포함 SSE chat/stream) + Monitoring 5 |
| **serverless** (`/api/v1/serverless/`) | 64 | `@api_view` 함수 52개 + admin CBV 12개 | **64** | Admin 대시보드 12 + Market Movers/Keywords 8 + Breadth 3 + Heatmap 3 + Presets 7 + Filters 1 + Screener 1 + Alerts 6 + Thesis(legacy) 4 + ETF 8 + LLM Relations 4 + Institutional 3 + Regulatory/Patent 2 + Health 1. **views.py 3,405줄** |
| **thesis** (`/api/v1/thesis/`) | 11 + 3개 router(main/premise/indicator) | ThesisViewSet 기본 CRUD 6 + `@action` 2, Premise/Indicator ViewSet 기본 CRUD 각 6 | **~31** | Conversation 4 + Dashboard/Readings 2 + Alerts 2 + Thesis ViewSet 8 + Premise 6 + Indicator 6 + 기타 3 |
| **validation** (`/api/v1/validation/`) | 6 | — | **6** | summary / metrics / leader-comparison / presets / peer-preference / llm-filter (모두 `<symbol>` 하위) |
| **chainsight** (`/api/v1/chainsight/`) | 7 + router | WatchlistViewSet 기본 CRUD 6 + `@action` 5 | **~18** | Market(seeds/signals/trace) + Sector/Neighbor 그래프 + Graph/Suggestions + Watchlist 전체 |
| **sec_pipeline** (`/api/v1/sec-pipeline/`) | 2 | — | **2** | admin dashboard + filing/<symbol>/ |
| **api_request** (`/api/v1/`) | 6 | — | **6** | health + provider status/rate-limits/cache/test/config (IsAdminUser) |
| **config (루트)** | 3 | — | **3** | `/`, `/health/`, `/admin/` |
| **총계** | — | — | **약 290** | 정확한 라우터 확장 수는 런타임에서 `python manage.py show_urls` 실행 필요 |

### 2.2 주요 상세 내역

#### stocks (64개) — `stocks/urls.py`
- 페이지/검색: `''` DashboardView, `stock/<symbol>/`, `search/`
- Chart/Overview/재무제표: `api/chart/`, `api/overview/`, `api/balance-sheet/`, `api/income-statement/`, `api/cashflow/`
- Sync: `api/sync/<symbol>/`
- MVP: `api/mvp/stocks/`, `api/mvp/stock/<symbol>/`, `api/mvp/rag/<symbol>/`, `api/mvp/sectors/`
- 기술적 지표: `api/indicators/<symbol>/`, `api/signal/<symbol>/`, `api/indicators/compare/`
- 심볼 검색: `api/search/symbols/`, `api/search/validate/<symbol>/`, `api/search/popular/`
- Market Movers: `api/market-movers/`
- Fundamentals: `api/fundamentals/{key-metrics|ratios|dcf|rating|all}/<symbol>/`
- Screener: `api/screener/`, `api/screener/{large-cap|high-dividend|low-beta}/`, `api/screener/sector/<sector>/`, `api/screener/exchange/<exchange>/`
- Exchange: `api/quotes/index/`, `api/quotes/<symbol>/`, `api/quotes/batch/`, `api/quotes/major-indices/`, `api/quotes/sector-performance/`
- EOD: `eod/dashboard/`, `eod/signal/<signal_id>/`, `eod/pipeline/status/`

#### users (39개) — `users/urls.py`
- JWT 인증: `jwt/{signup,login,logout,refresh,verify,change-password,profile}/`
- 세션 인증(하위 호환): `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/`
- 즐겨찾기: `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/`
- 포트폴리오: `portfolio/`, `portfolio/summary/`, `portfolio/table/`, `portfolio/refresh/`, `portfolio/<pk>/`, `portfolio/<pk>/quick-update/`, `portfolio/symbol/<symbol>/`, `portfolio/symbol/<symbol>/refresh/`, `portfolio/symbol/<symbol>/status/`
- 관심사: `interests/`, `interests/<pk>/`
- 워치리스트: `watchlist/`, `watchlist/<pk>/`, `watchlist/<pk>/add-stock/`, `watchlist/<pk>/bulk-add/`, `watchlist/<pk>/bulk-remove/`, `watchlist/<pk>/stocks/`, `watchlist/<pk>/stocks/<symbol>/`, `watchlist/<pk>/stocks/<symbol>/remove/`

#### news (30+개) — `news/api/urls.py` + `NewsViewSet` `@action`
- router 기본 + `stock_news`, `stock_sentiment`, `market`, `trending`, `all_news`, `sources`, `daily_keywords`, `generate_daily_keywords`, `keyword_detail`, `insights`, `market_feed`, `interest_options`, `personalized_feed`, `news_events`, `news_events_impact_map`, `ml_status`, `ml_shadow_report`, `ml_weekly_report`, `ml_lightgbm_readiness`, `recommendations`, `collection_logs`, `pipeline_health`, `ml_trend`, `llm_usage`, `task_timeline`, `neo4j_status`, `ml_rollback_preview`, `ml_rollback`, `alerts`, `alerts_resolve`
- **리스크**: 단일 ViewSet이 2,183줄로 지나치게 비대 → 문서화 시 일괄 `@extend_schema_view`로 정리 필요

#### macro (10개) — `macro/urls.py`
- `pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis (15개) — `rag_analysis/urls.py`
- DataBasket: `baskets/`, `baskets/<pk>/`, `baskets/<pk>/add-item/`, `baskets/<pk>/add-stock-data/`, `baskets/<pk>/items/<item_id>/`, `baskets/<pk>/clear/`
- AnalysisSession: `sessions/`, `sessions/<pk>/`, `sessions/<pk>/messages/`, `sessions/<pk>/chat/stream/` (**SSE**)
- Monitoring: `monitoring/{usage,cost,cache,history,pricing}/`
- **리스크**: SSE chat/stream은 OpenAPI 표준에 매끄럽게 맞지 않음 → 수동 annotation 필요

#### serverless (64개) — `serverless/urls.py`
- Admin 대시보드: `admin/dashboard/{overview,stocks,screener,market-pulse,news,system,tasks,actions}`, `admin/dashboard/actions/status/<task_id>/`, `admin/dashboard/news/categories/`, `.../<category_id>/`, `.../sector-options/`
- Market Movers: `movers`, `movers/<symbol>`, `sync`, `sync-now`
- Keywords: `keywords/batch`, `keywords/generate-all`, `keywords/generate-screener`, `keywords/<symbol>`
- Breadth: `breadth`, `breadth/history`, `breadth/sync`
- Heatmap: `heatmap/sectors`, `heatmap/sectors/<sector>/stocks`, `heatmap/sync`
- Presets: `presets`, `presets/trending`, `presets/shared/<share_code>`, `presets/import/<share_code>`, `presets/<preset_id>`, `presets/<preset_id>/execute`, `presets/<preset_id>/share`
- Filters/Screener: `filters`, `screener`
- Alerts: `alerts`, `alerts/history`, `alerts/history/<history_id>/read`, `alerts/history/<history_id>/dismiss`, `alerts/<alert_id>`, `alerts/<alert_id>/toggle`
- Thesis(legacy): `thesis/generate`, `thesis/shared/<share_code>`, `thesis/<thesis_id>`, `thesis`
- ETF: `etf/status`, `etf/sync`, `etf/resolve-url`, `etf/<etf_symbol>/holdings`, `etf/stock/<symbol>/themes`, `etf/stock/<symbol>/peers`, `themes`, `themes/refresh`, `themes/<theme_id>/stocks`
- LLM Relations: `llm-relations/extract`, `llm-relations/sync`, `llm-relations/stats`, `llm-relations/<symbol>`
- Institutional: `institutional/sync`, `institutional/<symbol>/peers`, `institutional/<symbol>`
- Regulatory/Patent: `regulatory/<symbol>`, `patent-network/<symbol>`
- Health: `health`
- **리스크**: `@api_view` 함수 기반 → drf-spectacular 자동 스키마가 파라미터/응답을 잡기 어려움. path 끝에 trailing slash 없는 라우트 혼재.

#### thesis (31개 추정) — `thesis/urls.py`
- Conversation: `conversation/start/`, `conversation/respond/`, `conversation/news-issues/`, `conversation/suggest/`
- Monitoring: `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<indicator_id>/readings/`
- Alerts: `alerts/`, `alerts/<aid>/read/`
- ViewSet: `ThesisViewSet`(기본 CRUD 6 + `@action` 2), nested `ThesisPremiseViewSet`(기본 6), nested `ThesisIndicatorViewSet`(기본 6)

#### validation (6개) — `validation/api/urls.py`
- `<symbol>/{summary,metrics,leader-comparison,presets,peer-preference,llm-filter}/`

#### chainsight (18개 추정) — `chainsight/api/urls.py`
- Market: `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`
- Symbol 기반: `<symbol>/neighbors/`, `<symbol>/graph/`, `<symbol>/suggestions/`
- WatchlistViewSet(기본 CRUD 6 + `@action` 5) → `watchlist/...`

#### sec_pipeline (2개) — `sec_pipeline/urls.py`
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request (6개) — `api_request/urls.py`
- `health/`, `admin/providers/{status,rate-limits,cache,test,config}/`

#### config 루트 (3개) — `config/urls.py`
- `''` (api_root, 수동 하드코딩 JSON 응답), `health/`, `admin/`

---

## 도입 작업 목록

### 3.1 drf-spectacular 설치 및 기본 설정 (S, ~0.5일)

1. **의존성 추가**
   - `pyproject.toml`의 `[tool.poetry.dependencies]`에 `drf-spectacular = "^0.27"` 추가
   - `poetry lock && poetry install`
2. **Django settings 수정** (`config/settings/*.py`)
   - `INSTALLED_APPS`에 `"drf_spectacular"` 추가
   - `REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"`
   - `SPECTACULAR_SETTINGS` 블록 추가: `TITLE`, `DESCRIPTION`, `VERSION`, `SERVE_INCLUDE_SCHEMA=False`, `TAGS`(앱별), `COMPONENT_SPLIT_REQUEST=True`, `ENUM_NAME_OVERRIDES`
3. **config/urls.py 라우팅 3개 추가**
   - `api/schema/` → `SpectacularAPIView`
   - `api/schema/swagger-ui/` → `SpectacularSwaggerView`
   - `api/schema/redoc/` → `SpectacularRedocView`
4. **CI 검증** — `python manage.py spectacular --file schema.yml --validate` 스크립트를 GitHub Actions에 추가 (lint 단계 권장)

### 3.2 기본 Serializer 갱신 (M, 2~3일)

- 모든 `APIView`/`GenericAPIView`/`ViewSet`에 **request 및 response Serializer 명시화**가 필요.
- 현재 다수 뷰가 딕셔너리를 직접 `Response(...)`에 넘기고 있어 자동 스키마 품질이 낮음.
- 최소한 자주 쓰이는 공용 응답(pagination, error)에 대해 `serializers.Serializer` subclass 정의 권장.

### 3.3 `@extend_schema` annotation 범위 (대) — 예상 작업량

> "가벼운 annotation(요약만)"과 "정밀 annotation(parameters/request/responses 전부)"로 분리하여 산정.

| 앱 | 실효 엔드포인트 | 가벼운 annotation(분) | 정밀 annotation(분) | 정밀 작업 총 시간 |
|----|---------------:|---------------------:|---------------------:|------------------:|
| stocks | 64 | 5 | 20 | **약 21시간** |
| users | 39 | 5 | 15 | 약 10시간 |
| news | 30+ | 7 | 25 | 약 13시간 |
| macro | 10 | 5 | 15 | 약 2.5시간 |
| rag_analysis | 15 | 7 (SSE 주의) | 25 | 약 6시간 |
| serverless | 64 | 7 (`@api_view` 특수) | 25 | 약 27시간 |
| thesis | 31 | 5 | 20 | 약 10시간 |
| validation | 6 | 5 | 15 | 약 1.5시간 |
| chainsight | 18 | 5 | 20 | 약 6시간 |
| sec_pipeline | 2 | 5 | 15 | 약 0.5시간 |
| api_request | 6 | 5 | 15 | 약 1.5시간 |
| **합계** | **약 285** | — | — | **약 99시간 (약 12.5 man-day)** |

### 3.4 특수 케이스 수작업 annotation 필요 항목

1. **rag_analysis `sessions/<pk>/chat/stream/`** — SSE(Server-Sent Events) 스트리밍. OpenAPI `text/event-stream` 응답 명세 수동 작성 필요.
2. **serverless `@api_view` 함수 52개** — 자동 스키마가 request body/query를 잡기 어려움. 각 함수에 `@extend_schema(parameters=[...], request=..., responses=...)` 수동 필수.
3. **news `NewsViewSet`의 30+ @action** — url_path에 정규식 사용(`(?P<symbol>[^/.]+)`). `@extend_schema(parameters=[OpenApiParameter("symbol", ...)])` 수동 지정.
4. **thesis UUID path parameter** (`<uuid:thesis_id>`, `<uuid:indicator_id>`, `<uuid:aid>`) — 스키마에서 format을 uuid로 명시 권장.
5. **JWT 인증 엔드포인트(users/jwt/*)** — `simplejwt`의 `TokenObtainPairView`는 drf-spectacular이 공식 지원. `SPECTACULAR_SETTINGS["SECURITY"]`에 `Bearer` 등록.
6. **Admin 엔드포인트(serverless admin/*, api_request admin/*)** — `IsAdminUser` 권한 태그링(`tags=["Admin"]`) + `deprecated=False` 명시.
7. **legacy/deprecated 엔드포인트(serverless `thesis/*`)** — `@extend_schema(deprecated=True)` 표시.
8. **config `api_root` 수동 하드코딩 응답** — drf-spectacular이 생성하는 스키마와 중복되므로 **폐기 검토** 권장.

### 3.5 단계별 로드맵 제안

| 단계 | 범위 | 예상 기간 | 산출물 |
|------|------|----------|--------|
| **P0: 설치·인프라** | drf-spectacular 설치, settings, urls 3개, CI validate | 0.5일 | `/api/schema/swagger-ui/` 접속 가능 |
| **P1: 최소 운영 품질** | 모든 뷰에 가벼운 `@extend_schema(summary=..., tags=...)` 부여, tags 11개 정의, `TAGS_SORTER` 지정 | 3일 | 앱별 분류된 Swagger UI |
| **P2: 공용 응답 스키마** | ErrorSerializer, PaginatedResponseSerializer, JWT SecurityScheme 정리 | 1일 | 400/401/403/404/500 공통 응답 |
| **P3: 정밀 annotation (Tier 1)** | stocks, users, validation, macro, chainsight, thesis, sec_pipeline, api_request (약 176개) | 5일 | 정확한 request/response 스키마 |
| **P4: 정밀 annotation (Tier 2)** | serverless(`@api_view` 52개) + news(비대 ViewSet 30+) + rag_analysis(SSE 포함) | 5일 | 난이도 높은 뷰 완료 |
| **P5: 문서 배포** | 사내 접근 제어(IsAdminUser), contracts/ 디렉토리와 동기화 검증, README 보강 | 0.5일 | `contracts/openapi.yaml` 자동 생성 + drift 감지 |
| **총 소요** | — | **약 15일 (3주)** | 1인 기준, 병렬 작업 시 단축 가능 |

### 3.6 선결 사항 / 위험 요소

- **news/api/views.py(2,183줄)**, **serverless/views.py(3,405줄)** 두 파일이 극단적으로 비대 → annotation 추가 시 리뷰 부담 큼. 파일 분할 리팩터링을 선행하면 문서화 난이도 하락.
- **URL 명명 혼재**: 일부 경로는 trailing slash 없음(`/movers`, `/health`, `/screener`), 일부는 있음(`/pulse/`). drf-spectacular 자동 스키마에는 영향 없으나 문서 가독성 저하.
- **contracts/ 디렉토리(CLAUDE.md 언급)**와 자동 생성 스펙의 **2중 관리 위험** — 단일 소스를 OpenAPI 생성물로 통일할지, contracts를 상위 스펙으로 둘지 정책 결정 필요.
- **JWT + 세션 2중 인증** 구조(users 앱) — 스키마에서 두 SecurityScheme 모두 노출할지 정리 필요.
- **SPA 프론트엔드(Next.js)와의 타입 동기화** — 도입 후 `openapi-typescript` 등으로 TS 타입 자동 생성 파이프라인 구축하면 frontend 구현 안전성 크게 개선.

---

## 요약

- **현재 API 자동 문서화 인프라 전무** — drf-spectacular / drf-yasg 미설치, Swagger/OpenAPI 엔드포인트 없음. `config/views.py:api_root`에 손으로 쓴 안내 JSON만 존재하며 실제 엔드포인트와 괴리.
- **실효 엔드포인트 약 290개**(11개 앱, 컨픽 루트 3개 별도). stocks 64, serverless 64, users 39, news 30+, thesis 31, chainsight 18, rag_analysis 15, macro 10, validation 6, api_request 6, sec_pipeline 2.
- **drf-spectacular 도입 자체는 0.5일 (P0)** 로 Swagger UI를 띄울 수 있으나, **정밀 문서까지 목표 시 약 15일(1인)** 의 `@extend_schema` annotation 작업이 필요. 특히 serverless `@api_view` 함수군과 news `NewsViewSet` 비대 파일이 병목.
- 단계별 로드맵(P0~P5)에 따라 스프린트 단위로 점진 도입 권장. 선행 과제로 news/serverless 뷰 파일 분할 리팩터링을 배치하면 P4 부담이 크게 줄어듦.
