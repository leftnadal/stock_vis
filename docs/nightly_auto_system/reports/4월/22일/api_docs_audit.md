# API 문서 감사 보고서

- 감사일: 2026-04-22
- 감사 대상: `/Users/byeongjinjeong/Desktop/stock_vis` Django REST Framework 백엔드
- 감사 범위: API 문서화 도구 설치 여부, 전체 엔드포인트 목록, drf-spectacular 도입 시 예상 작업량
- 성격: **읽기 전용 감사** — 소스 수정 없음
- 전일 대비 변동: URL 라우팅 변경 없음(4월 21일 보고서 기준 동일 상태 유지)

---

## 현재 상태

### 1.1 문서 자동화 도구 설치 여부

| 도구 | 상태 | 확인 위치 |
|------|------|-----------|
| `drf-spectacular` | **미설치** | `pyproject.toml` `[tool.poetry.dependencies]` / `[tool.poetry.group.dev.dependencies]` 미포함 |
| `drf-yasg` | **미설치** | 동일 |
| `coreapi` / `coreschema` | 미설치 | 동일 |
| REST framework 내장 스키마(`SchemaGenerator`) 라우팅 | 미구성 | `config/urls.py`에 `get_schema_view` 라우트 없음 |

**코드 그렙 결과** (프로젝트 내 `*.py` 대상):

- 패턴 `extend_schema|@swagger_auto_schema|OpenApiParameter|drf_spectacular`
- 매치된 파일: `docs/infra/nightly_v3.sh` 1건(감사 스크립트 본문), 이전 감사 보고서 2건, `docs/architecture/autonomous_agent_tasks.md` 1건
- **애플리케이션 소스(`*/views*.py`, `*/serializers*.py`) 매치 0건** — 프로젝트 어디에도 annotation/설정이 전혀 없다.

### 1.2 현재 문서화 방식

- `config/views.py`의 `api_root` 뷰가 **수동 하드코딩 JSON**으로 주요 엔드포인트 몇 개(users / stocks / analysis 일부)만 나열. `serverless`, `thesis`, `chainsight`, `validation`, `sec_pipeline`, `rag_analysis`, `macro`, `news`, `api_request` 등 **대부분의 앱이 누락**되어 실제 엔드포인트와 괴리가 크다.
- Swagger UI, ReDoc, OpenAPI JSON/YAML 스펙 **자동 생성 경로 없음**.
- `contracts/` 디렉토리(`CLAUDE.md`에서 "API 인터페이스 계약(OpenAPI + 공유 타입)"로 언급)는 **수기 관리 중**일 가능성이 높음 — 감사 범위 밖이지만 자동 생성 도구 도입 시 이중 관리 정리 필요.

### 1.3 자동 생성 가능 여부

- DRF 표준 패턴(`APIView`, `GenericAPIView`, `ViewSet`, `@api_view`)이 전반적으로 적용되어 있어 **drf-spectacular 설치만으로 "최소" 스펙 자동 생성 가능**.
- 단, 다음 요인들로 **자동 생성 결과는 품질이 낮을 것**으로 예상:
  1. `@api_view` 함수 기반 뷰가 다수(serverless 중심) → request body/query 파라미터 자동 추론 어려움
  2. 다수 뷰가 `Response({...})`에 dict를 직접 넣어 응답 스키마가 명시적이지 않음
  3. `NewsViewSet` 2,183줄 단일 파일의 30개 `@action`이 정규식 url_path 사용
  4. `rag_analysis/sessions/<pk>/chat/stream/`은 SSE(`text/event-stream`) 스트리밍
- 따라서 "고품질 OpenAPI 스펙"까지 가려면 `@extend_schema` 수작업 annotation이 필수.

---

## 엔드포인트 목록 (앱별 테이블)

> `path()` 개수는 `urls.py`에 등록된 라우트 수. ViewSet + router 등록의 경우 라우터가 자동 확장하는 기본 CRUD 액션과 `@action` 데코레이터 개수를 합산한 **실효 엔드포인트 수**를 추가로 표기한다.

### 2.1 앱별 요약

| 앱 (mount path) | urls.py `path()` 등록 수 | ViewSet 자동 확장 / `@action` | 실효 엔드포인트(추정) | 비고 |
|----------------|-------------------------:|:-----------------------------:|----------------------:|------|
| **stocks** (`/api/v1/stocks/`) | 64 | — | **64** | 대시보드/차트/검색/기술지표/펀더멘털/스크리너/거래소 시세/EOD 대시보드 |
| **users** (`/api/v1/users/`) | 39 | — | **39** | JWT 인증 7 + 세션 인증 6 + 즐겨찾기 3 + 포트폴리오 9 + 관심사 2 + 워치리스트 9 + 기타 3 |
| **news** (`/api/v1/news/`) | 1 (router) | `NewsViewSet` `@action` **30개** | **30+** | 단일 ViewSet이 stock_news / sentiment / trending / all / sources / daily-keywords / insights / market-feed / personalized-feed / news-events / ml-status / ml-shadow-report / ml-weekly-report / ml-lightgbm-readiness / recommendations / collection-logs / pipeline-health / ml-trend / llm-usage / task-timeline / neo4j-status / ml-rollback(-preview) / alerts / alerts-resolve 등 전담. **단일 파일 2,183줄** |
| **macro** (`/api/v1/macro/`) | 10 | — | **10** | Market Pulse(fear-greed, rates, inflation, global, calendar, vix, sectors) + sync 2 |
| **rag_analysis** (`/api/v1/rag/`) | 15 | — | **15** | DataBasket 6 + AnalysisSession 4(포함 SSE chat/stream) + Monitoring 5 |
| **serverless** (`/api/v1/serverless/`) | 64 | `@api_view` 함수 52 + admin CBV 12 | **64** | Admin 대시보드 12 + Market Movers/Keywords 8 + Breadth 3 + Heatmap 3 + Presets 7 + Filters 1 + Screener 1 + Alerts 6 + Thesis(legacy) 4 + ETF 9 + LLM Relations 4 + Institutional 3 + Regulatory/Patent 2 + Health 1. **views.py 3,405줄** |
| **thesis** (`/api/v1/thesis/`) | 11 + 3 router(main/premise/indicator) | `ThesisViewSet` CRUD 6 + `@action` 2, Premise/Indicator ViewSet CRUD 각 6 | **약 31** | Conversation 4 + Dashboard/Readings 2 + Alerts 2 + Thesis ViewSet 8 + Premise 6 + Indicator 6 + 기타 3 |
| **validation** (`/api/v1/validation/`) | 6 | — | **6** | summary / metrics / leader-comparison / presets / peer-preference / llm-filter (모두 `<symbol>` 하위) |
| **chainsight** (`/api/v1/chainsight/`) | 7 + router | `WatchlistViewSet` CRUD 6 + `@action` 5 | **약 18** | Market(seeds/signals/trace) + Sector/Neighbor 그래프 + Graph/Suggestions + Watchlist 전체 |
| **sec_pipeline** (`/api/v1/sec-pipeline/`) | 2 | — | **2** | admin dashboard + filing/`<symbol>`/ |
| **api_request** (`/api/v1/`) | 6 | — | **6** | health + provider status/rate-limits/cache/test/config (IsAdminUser) |
| **config (루트)** | 3 | — | **3** | `/`(api_root 하드코딩), `/health/`, `/admin/` |
| **총계** | — | — | **약 290** | 정확한 라우터 확장 수는 `python manage.py show_urls` 등 런타임에서 재확인 권장 |

### 2.2 앱별 상세 내역

#### stocks (64) — `stocks/urls.py`
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

#### users (39) — `users/urls.py`
- JWT 인증: `jwt/{signup,login,logout,refresh,verify,change-password,profile}/`
- 세션 인증(하위 호환): `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/`
- 즐겨찾기: `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/`
- 포트폴리오: `portfolio/`, `portfolio/summary/`, `portfolio/table/`, `portfolio/refresh/`, `portfolio/<pk>/`, `portfolio/<pk>/quick-update/`, `portfolio/symbol/<symbol>/`, `portfolio/symbol/<symbol>/refresh/`, `portfolio/symbol/<symbol>/status/`
- 관심사: `interests/`, `interests/<pk>/`
- 워치리스트: `watchlist/`, `watchlist/<pk>/`, `watchlist/<pk>/add-stock/`, `watchlist/<pk>/bulk-add/`, `watchlist/<pk>/bulk-remove/`, `watchlist/<pk>/stocks/`, `watchlist/<pk>/stocks/<symbol>/`, `watchlist/<pk>/stocks/<symbol>/remove/`

#### news (30+) — `news/api/urls.py` + `NewsViewSet`
- router 기본 CRUD + `@action` 30개 (`grep -c '@action'` 결과)
- 대표 액션: stock_news / stock_sentiment / market / trending / all_news / sources / daily_keywords / generate_daily_keywords / keyword_detail / insights / market_feed / interest_options / personalized_feed / news_events / news_events_impact_map / ml_status / ml_shadow_report / ml_weekly_report / ml_lightgbm_readiness / recommendations / collection_logs / pipeline_health / ml_trend / llm_usage / task_timeline / neo4j_status / ml_rollback_preview / ml_rollback / alerts / alerts_resolve
- **리스크**: 단일 ViewSet 2,183줄 → 문서화 시 `@extend_schema_view` 일괄 지정이 필수지만 리뷰 부담 크다

#### macro (10) — `macro/urls.py`
- `pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis (15) — `rag_analysis/urls.py`
- DataBasket: `baskets/`, `baskets/<pk>/`, `baskets/<pk>/add-item/`, `baskets/<pk>/add-stock-data/`, `baskets/<pk>/items/<item_id>/`, `baskets/<pk>/clear/`
- AnalysisSession: `sessions/`, `sessions/<pk>/`, `sessions/<pk>/messages/`, `sessions/<pk>/chat/stream/` (**SSE**)
- Monitoring: `monitoring/{usage,cost,cache,history,pricing}/`
- **리스크**: SSE(`text/event-stream`)는 OpenAPI 표준에 매끄럽게 매핑되지 않아 수동 annotation 필요

#### serverless (64) — `serverless/urls.py`
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
- **리스크**: `@api_view` 함수 기반 → 자동 스키마가 파라미터/응답을 잡기 어렵다. trailing slash 없는 라우트 다수(`movers`, `health`, `screener`, `themes` 등)로 URL 일관성 낮음.

#### thesis (약 31) — `thesis/urls.py`
- Conversation: `conversation/start/`, `conversation/respond/`, `conversation/news-issues/`, `conversation/suggest/`
- Monitoring: `<uuid:thesis_id>/dashboard/`, `<uuid:thesis_id>/indicators/<uuid:indicator_id>/readings/`
- Alerts: `alerts/`, `alerts/<uuid:aid>/read/`
- ViewSet: `ThesisViewSet`(기본 CRUD 6 + `@action` 2) + nested `ThesisPremiseViewSet`(CRUD 6) + nested `ThesisIndicatorViewSet`(CRUD 6)

#### validation (6) — `validation/api/urls.py`
- `<symbol>/{summary,metrics,leader-comparison,presets,peer-preference,llm-filter}/`

#### chainsight (약 18) — `chainsight/api/urls.py`
- Market: `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`
- Symbol 기반: `<symbol>/neighbors/`, `<symbol>/graph/`, `<symbol>/suggestions/`
- `WatchlistViewSet` (기본 CRUD 6 + `@action` 5) → `watchlist/...`

#### sec_pipeline (2) — `sec_pipeline/urls.py`
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request (6) — `api_request/urls.py`
- `health/`, `admin/providers/{status,rate-limits,cache,test,config}/`

#### config 루트 (3) — `config/urls.py`
- `''` (api_root, 수동 하드코딩 JSON), `health/`, `admin/`

---

## 도입 작업 목록

### 3.1 drf-spectacular 설치 및 기본 설정 (S, ~0.5일)

1. **의존성 추가**
   - `pyproject.toml` `[tool.poetry.dependencies]`에 `drf-spectacular = "^0.27"` 추가
   - `poetry lock && poetry install`
2. **Django settings 수정** (`config/settings.py`)
   - `INSTALLED_APPS`에 `"drf_spectacular"` 추가
   - `REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"`
   - `SPECTACULAR_SETTINGS` 블록 신설: `TITLE`, `DESCRIPTION`, `VERSION`, `SERVE_INCLUDE_SCHEMA=False`, `TAGS`(앱별), `COMPONENT_SPLIT_REQUEST=True`, `ENUM_NAME_OVERRIDES`
3. **`config/urls.py` 라우팅 3개 추가**
   - `api/schema/` → `SpectacularAPIView`
   - `api/schema/swagger-ui/` → `SpectacularSwaggerView`
   - `api/schema/redoc/` → `SpectacularRedocView`
4. **CI 검증** — `python manage.py spectacular --file schema.yml --validate` 를 GitHub Actions lint 단계에 추가 (scheme drift 검지)

### 3.2 공용 Serializer 정의 (M, 2~3일)

- 모든 `APIView`/`GenericAPIView`/`ViewSet`에 **request/response Serializer 명시** 필요
- 현재 다수 뷰가 `Response({...})`에 dict를 바로 넣고 있어 자동 스키마 품질이 낮음
- 공용 응답(pagination, error, JWT 토큰)을 `serializers.Serializer` subclass로 정의해 `@extend_schema(responses={...})`에서 재사용

### 3.3 `@extend_schema` annotation 범위

> 두 가지 품질 기준으로 산정. 가벼운 annotation = `summary`/`tags`만 기재. 정밀 annotation = `parameters`/`request`/`responses` 전부 기재.

| 앱 | 실효 엔드포인트 | 엔드포인트당 가벼운(분) | 엔드포인트당 정밀(분) | 정밀 작업 총 시간 |
|----|---------------:|------------------------:|----------------------:|------------------:|
| stocks | 64 | 5 | 20 | **약 21h** |
| users | 39 | 5 | 15 | 약 10h |
| news | 30+ | 7 | 25 | 약 13h |
| macro | 10 | 5 | 15 | 약 2.5h |
| rag_analysis | 15 | 7 (SSE 주의) | 25 | 약 6h |
| serverless | 64 | 7 (`@api_view` 특수) | 25 | 약 27h |
| thesis | 31 | 5 | 20 | 약 10h |
| validation | 6 | 5 | 15 | 약 1.5h |
| chainsight | 18 | 5 | 20 | 약 6h |
| sec_pipeline | 2 | 5 | 15 | 약 0.5h |
| api_request | 6 | 5 | 15 | 약 1.5h |
| **합계** | **약 285** | — | — | **약 99h (약 12.5 man-day)** |

### 3.4 특수 케이스 — 수작업 annotation 필수 항목

1. **`rag_analysis/sessions/<pk>/chat/stream/`** — SSE 스트리밍. OpenAPI `responses.200.content."text/event-stream"` 명세 수작업.
2. **serverless `@api_view` 함수 52개** — 자동 스키마가 request body/query를 못 잡음. 각 함수에 `@extend_schema(parameters=[...], request=..., responses=...)` 수작업.
3. **news `NewsViewSet`의 30 `@action`** — `url_path`에 정규식 사용. `@extend_schema(parameters=[OpenApiParameter("symbol", ...)])` 명시 필요.
4. **thesis UUID path parameter** (`<uuid:thesis_id>`, `<uuid:indicator_id>`, `<uuid:aid>`) — 스키마 `format: uuid` 명시 권장.
5. **JWT 인증 엔드포인트(`users/jwt/*`)** — `simplejwt`는 drf-spectacular 공식 지원. `SPECTACULAR_SETTINGS["SECURITY"]`에 `Bearer` 스키마 등록.
6. **Admin 엔드포인트(serverless `admin/*`, api_request `admin/*`)** — `IsAdminUser` 권한 → `tags=["Admin"]` + 별도 Security requirement.
7. **Legacy 엔드포인트(serverless `thesis/*`, 주석상 `LEGACY_KEEP_UNTIL_DC2` 표시된 ETF 경로)** — `@extend_schema(deprecated=True)` 부여.
8. **`config/views.py:api_root` 수동 JSON** — drf-spectacular 도입 이후 **중복이므로 폐기** 검토 권장 (혹은 `/api/schema/swagger-ui/` 리다이렉트로 대체).

### 3.5 단계별 로드맵

| 단계 | 범위 | 예상 기간 | 산출물 |
|------|------|----------|--------|
| **P0: 설치·인프라** | drf-spectacular 설치, settings, urls 3개, CI validate | 0.5일 | `/api/schema/swagger-ui/` 접속 가능 |
| **P1: 최소 운영 품질** | 모든 뷰에 가벼운 `@extend_schema(summary=..., tags=...)` 부여, 태그 11개 정의, `TAGS_SORTER` 지정 | 3일 | 앱별 분류된 Swagger UI |
| **P2: 공용 응답 스키마** | Error/PaginatedResponse/JWT SecurityScheme 정비 | 1일 | 400/401/403/404/500 공통 응답 |
| **P3: 정밀 annotation Tier 1** | stocks, users, validation, macro, chainsight, thesis, sec_pipeline, api_request (약 176개) | 5일 | 정확한 request/response 스키마 |
| **P4: 정밀 annotation Tier 2** | serverless(`@api_view` 52) + news(비대 ViewSet 30+) + rag_analysis(SSE 포함) | 5일 | 난이도 높은 뷰 완료 |
| **P5: 문서 배포 및 TS 동기화** | 사내 접근 제어(IsAdminUser), `contracts/openapi.yaml` 자동 동기화, `openapi-typescript`로 프론트 타입 생성 | 0.5일 | drift 감지 + Next.js 타입 자동 생성 |
| **총 소요** | — | **약 15일 (3주)** | 1인 기준, P3/P4 병렬 시 단축 가능 |

### 3.6 선결 사항 / 위험 요소

- **비대 파일 분할 리팩터링 선행 권장**
  - `news/api/views.py` **2,183줄 / `@action` 30**
  - `serverless/views.py` **3,405줄 / `@api_view` 52**
  - 두 파일을 도메인별 하위 모듈로 쪼개지 않으면 P4 annotation PR의 리뷰 부담이 극도로 커진다.
- **URL 일관성 혼재** — serverless의 다수 경로는 trailing slash 없음(`/movers`, `/health`, `/screener`, `/themes`), 나머지는 있음(`/pulse/`, `/fear-greed/`). 자동 스키마 동작엔 영향 없으나 문서 가독성 저하 + APPEND_SLASH 예외 처리 주의.
- **`contracts/` 디렉토리와의 이중 관리 위험** — `CLAUDE.md`가 "API 인터페이스 계약(OpenAPI + 공유 타입)"을 contracts에 둔다고 명시. 자동 생성물과 수기 contracts 중 **단일 소스 확정**이 선결 과제. 권장안: 자동 생성 → contracts 동기화(CI drift 검증) 방향.
- **JWT + 세션 2중 인증** (`users` 앱) — `DEFAULT_AUTHENTICATION_CLASSES`에 JWT + Session 둘 다 등록되어 있음. 스키마에서 두 SecurityScheme 모두 노출할지 정책 결정 필요.
- **SPA 프론트엔드(Next.js 16)와의 타입 동기화** — 도입 후 `openapi-typescript` 파이프라인을 구축하면 frontend의 `authAxios` 호출부 타입 안정성이 크게 향상된다.
- **프리미엄 Serializer 부재** — `Response({...})` dict 직접 반환이 관행화되어 있어 정밀 annotation 시 **Serializer 일괄 신설 비용**(약 2~3 man-day)이 3.2 단계에서 별도 발생.

---

## 요약

- **API 자동 문서화 인프라 전무** — drf-spectacular / drf-yasg 미설치, Swagger/OpenAPI 엔드포인트 없음. `config/views.py:api_root`의 수기 JSON만 존재하며 실제 엔드포인트와 괴리.
- **실효 엔드포인트 약 290개** (11개 앱 + 루트 3). stocks 64 / serverless 64 / users 39 / news 30+ / thesis 약 31 / chainsight 약 18 / rag_analysis 15 / macro 10 / validation 6 / api_request 6 / sec_pipeline 2.
- **drf-spectacular 도입 자체(P0)는 0.5일**로 Swagger UI를 띄울 수 있으나, **정밀 문서까지 달성하려면 약 15일(1인)**의 `@extend_schema` 작업과 공용 Serializer 정의가 필요. 특히 `serverless/views.py`(3,405줄, `@api_view` 52개)와 `news/api/views.py`(2,183줄, `@action` 30개)가 병목.
- **선행 작업 권장**: (1) news/serverless 뷰 파일 분할 리팩터링, (2) `contracts/` 디렉토리와의 단일 소스 정책 확정, (3) 공용 Error/Paginated/JWT Serializer 정의 — 이 3가지를 P1 직전에 처리하면 P3/P4 작업량이 크게 감소.
- **전일(4월 21일) 대비 URL 변동 없음** — annotation 작업량·우선순위·리스크 판정 모두 동일.
