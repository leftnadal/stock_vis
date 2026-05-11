# API 문서 감사 보고서

**작성일**: 2026-04-26
**감사 범위**: Stock-Vis 백엔드 전 앱 (12개 URLConf)
**감사 방식**: 읽기 전용 (코드 수정 없음)
**근거 파일**: `config/urls.py`, `*/urls.py`, `*/views*.py`, `pyproject.toml`, `config/settings.py`

---

## 1. 현재 상태

### 1.1 API 문서화 도구 설치 여부

| 도구 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | ❌ 미설치 | `pyproject.toml` 의존성 목록에 없음 |
| `drf-yasg` | ❌ 미설치 | `pyproject.toml` 의존성 목록에 없음 |
| OpenAPI/Swagger UI 라우트 | ❌ 미구성 | `config/urls.py`에 schema/swagger 엔드포인트 없음 |
| `INSTALLED_APPS` 등록 | ❌ 없음 | `config/settings.py:155-184` 에 spectacular/yasg 부재 |
| `REST_FRAMEWORK` 스키마 클래스 | ❌ 미설정 | `config/settings.py:321-329` 에 `DEFAULT_SCHEMA_CLASS` 없음 |
| `@extend_schema` / `@swagger_auto_schema` | ❌ 사용처 0건 | 전체 `views*.py` grep 결과 0개 |

### 1.2 결론

- **자동 OpenAPI/Swagger 스펙 생성 불가능**한 상태.
- 현재 외부에서 API 명세를 보려면 `urls.py`와 view 클래스 docstring을 직접 읽어야 함.
- DRF 기본 `coreapi` 스키마 생성기도 활성화되어 있지 않음 (`DEFAULT_SCHEMA_CLASS` 미정의).
- `contracts/` 디렉터리 (수기 OpenAPI 스펙)가 운영 단일 소스로 사용 중인 것으로 추정됨.

### 1.3 인증/권한 관련 메모

- `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`: JWT + Session
- `DEFAULT_PERMISSION_CLASSES`: `IsAuthenticatedOrReadOnly`
- 일부 ViewSet `@action`에서 개별 `permission_classes` 오버라이드 (예: `news/api/views.py` 의 `IsAdminUser`, `AllowAny`, `IsAuthenticated`)
- 문서화 시 권한 매트릭스 별도 정리 필요.

---

## 2. 엔드포인트 목록 (앱별)

### 2.1 앱별 요약 테이블

`urls.py`의 `path()` 등록 수 + ViewSet `@action` 수를 합산. `DefaultRouter` 등록 ViewSet은 list/retrieve/create/update/partial_update/destroy 자동 라우트도 포함하여 추정.

| # | 앱 | URLConf | `path()` 수 | ViewSet | `@action` 수 | 추정 엔드포인트 합계 |
|---|----|---------|-------------|---------|--------------|---------------------|
| 1 | `stocks` | `stocks/urls.py` | 39 | 없음 (모두 APIView) | 0 | **39** |
| 2 | `users` | `users/urls.py` | 35 | 없음 (APIView + JWT views) | 0 | **35** |
| 3 | `news` | `news/api/urls.py` | 1 (router root) | `NewsViewSet` (ReadOnlyModelViewSet) | 30 | **32** (list+retrieve+30 actions) |
| 4 | `macro` | `macro/urls.py` | 10 | 없음 | 0 | **10** |
| 5 | `rag_analysis` | `rag_analysis/urls.py` | 15 | 없음 | 0 | **15** |
| 6 | `serverless` | `serverless/urls.py` | 64 | 없음 (FBV `@api_view` 다수) | — | **64** |
| 7 | `thesis` | `thesis/urls.py` | 11 (path) + router 3 ViewSets | `ThesisViewSet`, `ThesisPremiseViewSet`, `ThesisIndicatorViewSet` (모두 ModelViewSet) | 2 | **31** (3×6 + 2 actions + 11 paths) |
| 8 | `validation` | `validation/api/urls.py` | 6 | 없음 | 0 | **6** |
| 9 | `chainsight` | `chainsight/api/urls.py` | 7 (path) + `WatchlistViewSet` router | `WatchlistViewSet` (ModelViewSet) | 5 | **18** (7 + 6 router + 5 actions) |
| 10 | `sec_pipeline` | `sec_pipeline/urls.py` | 2 | 없음 | 0 | **2** |
| 11 | `api_request` | `api_request/urls.py` | 6 | 없음 (FBV) | 0 | **6** |
| 12 | `config` (root) | `config/urls.py` | 2 (`/`, `/health/`) | — | 0 | **2** |

> **추정 총 엔드포인트 ≈ 260개** (모든 ViewSet 자동 라우트 포함, HTTP 메서드별 중복은 별도)

### 2.2 앱별 상세

#### stocks (39개)
- 페이지/대시보드: `/`, `stock/<symbol>/`, `search/`
- 차트/탭 데이터: `api/chart`, `api/overview`, `api/balance-sheet`, `api/income-statement`, `api/cashflow`
- 동기화: `api/sync/<symbol>/`
- MVP API: `api/mvp/stocks/`, `api/mvp/stock/<symbol>/`, `api/mvp/rag/<symbol>/`, `api/mvp/sectors/`
- 기술적 지표: `api/indicators/<symbol>/`, `api/signal/<symbol>/`, `api/indicators/compare/`
- 종목 검색: `api/search/symbols/`, `api/search/validate/<symbol>/`, `api/search/popular/`
- Market Movers: `api/market-movers/`
- Fundamentals: `api/fundamentals/key-metrics`, `ratios`, `dcf`, `rating`, `all`
- Stock Screener: `api/screener/`, `large-cap/`, `high-dividend/`, `sector/<sector>/`, `low-beta/`, `exchange/<exchange>/`
- Exchange Quotes: `api/quotes/index/`, `<symbol>/`, `batch/`, `major-indices/`, `sector-performance/`
- EOD Dashboard (admin): `eod/dashboard/`, `eod/signal/<signal_id>/`, `eod/pipeline/status/`

#### users (35개)
- JWT 인증: `jwt/signup`, `jwt/login`, `jwt/logout`, `jwt/refresh`, `jwt/verify`, `jwt/change-password`, `jwt/profile`
- 세션 인증 (레거시): `me/`, `/`, `@<user_name>/`, `change_password/`, `login/`, `logout/`
- 즐겨찾기: `favorites/`, `favorites/add/<stock_id>`, `favorites/remove/<stock_id>`
- 포트폴리오: `portfolio/`, `summary`, `table`, `refresh`, `<pk>`, `<pk>/quick-update`, `symbol/<symbol>`, `symbol/<symbol>/refresh`, `symbol/<symbol>/status`
- 관심사: `interests/`, `interests/<pk>/`
- Watchlist: `watchlist/`, `<pk>/`, `<pk>/add-stock/`, `<pk>/bulk-add/`, `<pk>/bulk-remove/`, `<pk>/stocks/`, `<pk>/stocks/<symbol>/`, `<pk>/stocks/<symbol>/remove/`

#### news (32개)
`NewsViewSet` (ReadOnlyModelViewSet): 기본 `list`, `retrieve` + 30개의 `@action` (전체 `news/api/views.py` 라인 54~2149).

주요 액션 카테고리:
- 종목별 뉴스: `stock/<symbol>`, `stock/<symbol>/sentiment`, `daily-keywords`, `daily-keywords/generate`, `keyword-detail`
- 마켓 피드: `all`, `market-feed`, `interest-options`, `personalized-feed`
- News Events: `news-events`, `news-events/impact-map`
- ML 모니터링: `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `ml-trend`, `ml-rollback-preview`, `ml-rollback`
- 운영 (Admin): `collection-logs`, `pipeline-health`, `llm-usage`, `task-timeline`, `neo4j-status`, `alerts`, `alerts/<alert_pk>/resolve`

#### macro (10개)
`pulse`, `fear-greed`, `interest-rates`, `inflation`, `global-markets`, `calendar`, `vix`, `sectors`, `sync`, `sync/status`

#### rag_analysis (15개)
- DataBasket: `baskets/`, `baskets/<pk>/`, `add-item`, `add-stock-data`, `items/<item_id>`, `clear`
- AnalysisSession: `sessions/`, `sessions/<pk>/`, `messages/`, `chat/stream/`
- Monitoring: `monitoring/usage`, `cost`, `cache`, `history`, `pricing`

#### serverless (64개)
대분류:
- Admin Dashboard (12): `admin/dashboard/{overview, stocks, screener, market-pulse, news, system, tasks, actions, actions/status/<task_id>, news/categories, news/categories/<category_id>, news/sector-options}`
- Market Movers (4): `movers`, `movers/<symbol>`, `sync`, `sync-now`
- 키워드 (4): `keywords/batch`, `keywords/generate-all`, `keywords/generate-screener`, `keywords/<symbol>`
- Market Breadth (3): `breadth`, `breadth/history`, `breadth/sync`
- Sector Heatmap (3): `heatmap/sectors`, `heatmap/sectors/<sector>/stocks`, `heatmap/sync`
- Screener Presets (7): `presets`, `trending`, `shared/<share_code>`, `import/<share_code>`, `<preset_id>`, `<preset_id>/execute`, `<preset_id>/share`
- Screener Filters/Advanced (2): `filters`, `screener`
- Screener Alerts (6): `alerts`, `history`, `history/<id>/read`, `history/<id>/dismiss`, `<alert_id>`, `<alert_id>/toggle`
- Investment Thesis (4): `thesis/generate`, `thesis/shared/<share_code>`, `thesis/<thesis_id>`, `thesis`
- Chain Sight ETF (9): `etf/status`, `sync`, `resolve-url`, `<etf_symbol>/holdings`, `stock/<symbol>/themes`, `stock/<symbol>/peers`, `themes`, `themes/refresh`, `themes/<theme_id>/stocks`
- LLM Relations (4): `extract`, `sync`, `stats`, `<symbol>`
- Institutional (3): `sync`, `<symbol>/peers`, `<symbol>`
- Regulatory + Patent (2): `regulatory/<symbol>`, `patent-network/<symbol>`
- Health (1): `health`

> 비고: `serverless/views.py` 는 `@api_view` FBV 33개 + `views_admin.py` 12 클래스. 일부 엔드포인트는 GET/POST/PATCH/DELETE 다중 메서드를 단일 path에 매핑.

#### thesis (31개 추정)
- 명시적 path (11): `conversation/start`, `conversation/respond`, `conversation/news-issues`, `conversation/suggest`, `<thesis_id>/dashboard`, `<thesis_id>/indicators/<indicator_id>/readings`, `alerts/`, `alerts/<aid>/read`
- ViewSet 자동 라우트 (3 × 6 = 18):
  - `ThesisViewSet` (ModelViewSet) → list, retrieve, create, update, partial_update, destroy
  - `ThesisPremiseViewSet` (ModelViewSet, nested under `<thesis_id>/premises/`)
  - `ThesisIndicatorViewSet` (ModelViewSet, nested under `<thesis_id>/indicators/`)
- ViewSet `@action` (2): `thesis_views.py` 라인 63 (`detail=True` POST), 237 (`detail=False` POST)

#### validation (6개)
`<symbol>/{summary, metrics, leader-comparison, presets, peer-preference, llm-filter}`

#### chainsight (18개 추정)
- 명시적 path (7): `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`, `<symbol>/neighbors/`, `<symbol>/graph/`, `<symbol>/suggestions/`
- `WatchlistViewSet` (ModelViewSet) 자동 라우트 (6) + `@action` 5개

#### sec_pipeline (2개)
`admin/dashboard/`, `filing/<symbol>/`

#### api_request (6개)
`health/`, `admin/providers/{status, rate-limits, cache, test, config}/`

#### config (root) (2개)
- `/` (`api_root`)
- `/health/` (`health_check`)

### 2.3 사용자가 요청한 앱 외 추가 앱

CLAUDE.md 에서 언급된 앱 목록과 실제 등록 현황 비교:

| 앱 | URLConf 등록 | 비고 |
|----|--------------|------|
| `analysis` | ❌ 없음 | `config/urls.py` 미등록. 별도 URLConf 없음 — 기능이 stocks/views_indicators 에 흡수된 것으로 보임 |
| `graph_analysis` | ❌ 없음 | INSTALLED_APPS 등록되지만 URL 미연결 (CLAUDE.md `⏳ 미구현` 표기와 일치) |
| `metrics` | ❌ 없음 | 내부 서비스 (CLAUDE.md 명시) |
| `portfolio` | ❌ 없음 | INSTALLED_APPS 등록되지만 URL 미연결 (Phase 2 작업 중일 가능성) |

---

## 3. 도입 작업 목록

### 3.1 권장 도구 선택

**`drf-spectacular`** 선호. 근거:
- DRF 공식 권장. OpenAPI 3.0 호환.
- ViewSet/APIView/FBV(`@api_view`) 모두 지원.
- `@extend_schema` 데코레이터로 점진적 보강 가능.
- `drf-yasg` 는 OpenAPI 2.0 (Swagger 2) 기반이며 유지보수 둔화.
- `contracts/shared-types.ts` 와 OpenAPI 스펙을 자동 동기화하는 외부 도구 (`openapi-typescript`) 호환성 우수.

### 3.2 단계별 작업 항목

#### Phase A — 도구 설치 및 기본 활성화 (예상 0.5일)
1. `pyproject.toml` 의존성 추가: `drf-spectacular = "^0.27.0"`
2. `INSTALLED_APPS` 에 `drf_spectacular` 등록
3. `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'` 추가
4. `SPECTACULAR_SETTINGS` 정의 (TITLE, DESCRIPTION, VERSION, SERVE_INCLUDE_SCHEMA, SERVERS)
5. `config/urls.py` 에 라우트 3개 추가:
   - `api/schema/` (SpectacularAPIView)
   - `api/schema/swagger-ui/` (SpectacularSwaggerView)
   - `api/schema/redoc/` (SpectacularRedocView)
6. 권한 결정: 운영 환경에서는 인증된 관리자 또는 사내망 한정 권장.

#### Phase B — 기본 자동 추출 검증 (예상 0.5일)
- `python manage.py spectacular --file schema.yml --validate` 실행하여 경고 수집
- 다음 확인 필요:
  - JWT 인증 스키마 (`SimpleJWT`) 자동 인식 (`AUTHENTICATION_WHITELIST` 설정 필요할 수 있음)
  - Nested router (thesis premises/indicators) 경로 정확성
  - FBV `@api_view` (serverless 다수) 의 request/response 추출 한계
  - `<uuid:thesis_id>` 등 path converter 매핑 정상

#### Phase C — `@extend_schema` 데코레이터 보강 (예상 4~6일)

추정 보강 범위:

| 분류 | 대상 수 | 보강 난이도 | 예상 시간 |
|------|---------|-------------|-----------|
| FBV (`@api_view`) | serverless 33개 + 그 외 일부 | 高 (request/response 직접 명시 필요) | 2일 |
| APIView (DRF Class) | 약 60개+ (stocks, users, macro, rag_analysis 등) | 中 (Serializer 클래스 명시 + 응답 예제) | 1.5일 |
| ViewSet (`@action`) | 30개 (news 30 + thesis 2 + chainsight 5 = 37) | 中 (action별 query/response 정의) | 1일 |
| ModelViewSet 기본 액션 | 5 ViewSet × ~6 = 30 | 低 (Serializer 자동 추출) | 0.5일 |
| 권한/인증 매트릭스 정리 | 전체 | 中 | 0.5일 |
| 태그/그룹화 | 12 앱 | 低 | 0.5일 |

**총 예상 작업량: 약 5~7일 (1인 풀타임 기준)**

#### Phase D — `contracts/` 와의 통합 (예상 1~2일)
- DECISIONS.md 의 contract-first 원칙 (`contracts/` 가 진실의 소스) 과 충돌 가능.
- 옵션 1: 자동 추출된 OpenAPI 를 `contracts/` 와 비교하는 CI 검증 스크립트 추가.
- 옵션 2: `contracts/openapi.yaml` 을 사람이 작성하고, `drf-spectacular` 는 보조 (실제 구현 검증용)로 사용.
- 권장: 옵션 1 (자동화 + 진실의 소스 유지). 불일치 시 PR 차단.

#### Phase E — 프론트엔드 타입 자동 생성 (선택, 1일)
- `openapi-typescript` 또는 `orval` 도입.
- `frontend/lib/api/types.ts` 자동 생성 파이프라인 구축.
- `npm run gen:api` 등 스크립트 추가.

### 3.3 주요 리스크 / 고려 사항

1. **FBV가 serverless 앱에 33개 — 자동 추출 한계**
   - `@api_view(['GET', 'POST'])` 와 같이 다중 메서드 단일 함수 케이스가 많음 (서버리스 라우터 특성).
   - `@extend_schema(methods=['GET'], ...)` 로 메서드별로 분리해 작성해야 함.
   - 일부는 그대로 두고 OpenAPI 에서 "manual" 표기 권장.

2. **`urls.py` 라우팅 패턴이 일관되지 않음**
   - 일부는 trailing slash 있음, 일부는 없음 (예: `serverless` 의 `movers` vs `movers/` 부재).
   - OpenAPI 스펙에서는 정확히 일치해야 하므로 사전 일관화 검토 필요. (코드 변경은 별도 PR 권장.)

3. **CLAUDE.md 의 API path 와 실제 path 불일치**
   - CLAUDE.md: `/api/v1/graph/*` 명시 → 실제로는 등록 안 됨.
   - CLAUDE.md: `analysis` 앱 `/api/v1/analysis/*` 명시 → 실제로는 미등록.
   - 도큐먼트 도입 작업 시 이런 불일치를 함께 정리 필요 (예: CLAUDE.md 또는 sub_claude_md 업데이트).

4. **권한 매트릭스 누락 위험**
   - `news/api/views.py` 의 30개 `@action` 은 `permission_classes` 가 액션별로 다름 (`AllowAny`, `IsAuthenticated`, `IsAdminUser`).
   - `@extend_schema(security=[...])` 로 명시 보강 필요.

5. **`SPECTACULAR_SETTINGS.SERVE_PUBLIC` 운영 노출 결정**
   - 현재 인증 키 (Gemini, FMP) 등이 환경 변수에 의존 — 스키마 자체는 비밀이 아님.
   - 그러나 내부 admin 엔드포인트(`/admin/providers/*`, `/admin/dashboard/*`) 노출은 보안 검토 필요.

### 3.4 우선순위 권고

| 우선순위 | 항목 | 근거 |
|----------|------|------|
| P0 | Phase A (설치+기본 라우트) | 0.5일로 자동 스키마 80% 추출 가능 |
| P0 | 내부 개발용 Swagger UI 노출 | 프론트/백 협업 즉시 개선 |
| P1 | Phase B 검증 + nested router 점검 | thesis nested 라우트가 누락될 위험 |
| P1 | news ViewSet 30 action 권한/응답 어노테이션 | 가장 큰 ViewSet, 최우선 보강 |
| P2 | serverless FBV 33개 보강 | 가장 시간 소모, 단계적 진행 |
| P2 | contracts/ 와의 CI 일치 검증 | DECISIONS.md 정책과 정합 |
| P3 | openapi-typescript 프론트 타입 자동 생성 | DX 개선 |

---

## 4. 즉시 활용 가능한 개선 (도구 도입 없이도)

도구 도입 전에라도 가능:
1. **각 ViewSet/APIView 의 `__doc__` 정비** — `drf-spectacular` 도입 시 자동 description 으로 흡수됨.
2. **`urls.py` 의 `name=` 패턴 일관화** — 현재 일부는 `chainsight-graph`, 일부는 `chainsight_graph` 등 일관성 미흡.
3. **CLAUDE.md 의 API 경로 표 (`/api/v1/{stocks,users,...}/*`) 실제 라우팅과 일치하도록 갱신** — `analysis`, `graph` 등 미등록 앱 표기 수정.
4. **`contracts/openapi.yaml` 존재 여부 확인 및 최신성 점검** — DECISIONS.md 의 contract-first 원칙이 실제로 지켜지고 있는지 별도 감사 권장 (이 보고서 범위 외).

---

## 5. 부록: 감사 근거 데이터

### 5.1 의존성 (`pyproject.toml`)
- DRF 관련: `djangorestframework-simplejwt = "^5.5.1"` 만 존재.
- `djangorestframework` 자체는 simplejwt 의 transitive dep 으로 설치됨.
- 문서화 도구: 없음.

### 5.2 `path()` 카운트 (raw)
```
stocks/urls.py        : 39
users/urls.py         : 35
news/api/urls.py      :  1 (router only, 32 endpoints with actions)
macro/urls.py         : 10
rag_analysis/urls.py  : 15
serverless/urls.py    : 64
thesis/urls.py        : 11 (+ 3 ViewSets)
validation/api/urls.py:  6
chainsight/api/urls.py:  7 (+ 1 ViewSet)
sec_pipeline/urls.py  :  2
api_request/urls.py   :  6
config/urls.py        :  2 (root + health, app includes 제외)
```

### 5.3 ViewSet 인벤토리
- `news.api.views.NewsViewSet` (ReadOnlyModelViewSet) — 30 `@action`
- `thesis.views.thesis_views.ThesisViewSet` (ModelViewSet) — 1 detail action, 1 list action
- `thesis.views.thesis_views.ThesisPremiseViewSet` (ModelViewSet)
- `thesis.views.thesis_views.ThesisIndicatorViewSet` (ModelViewSet)
- `chainsight.views.watchlist_views.WatchlistViewSet` (ModelViewSet) — 5 `@action`

### 5.4 APIView 인벤토리 (count by file)
```
validation/api/views.py     : 6
sec_pipeline/views.py       : 1
users/views.py              : 18
macro/views.py              : 10
stocks/views.py             : 11
stocks/views_mvp.py         : 4
stocks/views_fundamentals.py: 5
stocks/views_search.py      : 3
stocks/views_indicators.py  : 3
stocks/views_eod.py         : 3
stocks/views_market_movers.py:1
stocks/views_screener.py    : 6
stocks/views_exchange.py    : 5
chainsight/api/views.py     : 7
rag_analysis/views.py       : 15
serverless/views_admin.py   : 12
thesis/views/conversation_views.py:4
thesis/views/monitoring_views.py:4
                       총   : 118 클래스
```

### 5.5 `@api_view` (FBV) 카운트
```
serverless/views.py : 33
api_request/admin_views.py : 6 (별도 admin 모듈)
                  소계  : 39
```

---

**보고서 끝.**
