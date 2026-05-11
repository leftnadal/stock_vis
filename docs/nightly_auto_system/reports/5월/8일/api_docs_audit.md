# API 문서 감사 보고서

- 감사일: 2026-05-09
- 감사자: 자동 감사 (읽기 전용)
- 대상: stock_vis 백엔드 (Django 5.1.7 + DRF) 전체 URL 라우팅
- 비고: 코드 미수정. 실제 등록된 `urls.py` / `views*.py` 만 정적 분석.

---

## 현재 상태

### 1.1 OpenAPI 도구 설치 현황

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` 설치 | **설치됨** (`^0.29.0`) | `pyproject.toml:38` |
| `drf-spectacular-sidecar` 설치 | **설치됨** (`^2026.4.14`) | `pyproject.toml:39` |
| `drf-yasg` | 미설치 | `pyproject.toml` 전체 검색 0건 |
| `INSTALLED_APPS` 등록 | **등록됨** | `config/settings.py:205-206` (`drf_spectacular`, `drf_spectacular_sidecar`) |
| `DEFAULT_SCHEMA_CLASS` | **설정됨** | `config/settings.py:361` (`drf_spectacular.openapi.AutoSchema`) |
| `SPECTACULAR_SETTINGS` | **설정됨** | `config/settings.py:365-413` |
| Schema endpoint | `/api/v2/schema/` | `config/urls.py:58` |
| Swagger UI endpoint | `/api/v2/swagger/` | `config/urls.py:59-63` |
| ReDoc endpoint | `/api/v2/redoc/` | `config/urls.py:64-68` |

### 1.2 자동 생성 가능 여부 — 결론: **부분적 가능, 실용적 미흡**

**바로 가능한 것**
- Swagger UI / ReDoc 페이지가 이미 호스팅됨 (`/api/v2/swagger/`, `/api/v2/redoc/`)
- `SCHEMA_PATH_PREFIX: r'/api/v[12]'` 로 `/api/v1/*` + `/api/v2/*` 모두 스키마에 포함됨
- ENUM 충돌 회피 처리 완료 (4개 enum 명시 매핑) — `config/spectacular_enums.py`
- Sidecar 정적 자산 사용으로 CDN 의존성 없음

**구조적 한계 (실용성 저해)**
- `'DISABLE_ERRORS_AND_WARNINGS': True` (`config/settings.py:385`) — drf-spectacular가 추론 실패한 view를 **조용히 string body로 graceful fallback** 처리. 즉 v1 대부분의 endpoint는 `request body / response body = string` 으로만 표현되어 실질적으로 사용 불가능한 스키마.
- 명시적 `@extend_schema` 사용 view는 **5개 앱 / 약 26개 view** 만 (전체의 약 13%)
  - `marketpulse/api/views/*.py` (5개 view 모두 처리됨)
  - `chainsight/api/views.py` (7건)
  - `serverless/views.py` (6건 — 함수 뷰 일부)
  - `api_request/admin_views.py` (5건)
  - `rag_analysis/views.py` (2건)
  - `news/api/views.py` (2건)
  - `users/views.py` (2건)
- 핵심 v1 영역(`stocks/`, `users/jwt_*`, `macro/`, `thesis/`, `validation/`, `sec_pipeline/`, `portfolio/`)에는 `@extend_schema` 0건
- 응답 시리얼라이저가 정의되지 않은 `Response({...})` 직접 반환이 대부분 → AutoSchema가 추론 불가

### 1.3 인증/권한 기본값
- `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` (`config/settings.py:353-355`)
- 인증: `JWTAuthentication` + `SessionAuthentication`
- 스키마에는 `SECURITY` 정의가 명시되지 않음 → JWT Bearer 표시는 view별 `@extend_schema(security=...)` 없이는 불완전

---

## 엔드포인트 목록 (앱별 테이블)

> 동적 path 파라미터 (`<str:symbol>`, `<int:pk>`, `<uuid:thesis_id>`)는 1개로 카운트.
> DRF `DefaultRouter`로 등록된 ViewSet은 표준 6개 액션(list/create/retrieve/update/partial_update/destroy)을 1세트로 카운트하되 `@action` 메서드는 별도 카운트.

### 2.1 앱별 엔드포인트 요약

| # | 앱 | URL 파일 | 등록 path 수 | ViewSet 수 | 함수 뷰 수 | `@extend_schema` 적용 | 문서화율 |
|---|----|----|------:|------:|------:|------:|------:|
| 1 | **stocks** | `stocks/urls.py` | 38 | 0 | 0 (전부 CBV) | 0 | 0% |
| 2 | **users** | `users/urls.py` | 30 | 0 | 0 | 2 (`views.py`) | ~7% |
| 3 | **news** | `news/api/urls.py` | router (1 ViewSet) | 1 (`NewsViewSet`) | 0 | 2 | 부분 |
| 4 | **macro** | `macro/urls.py` | 9 | 0 | 0 | 0 | 0% |
| 5 | **rag_analysis** | `rag_analysis/urls.py` | 14 | 0 | 0 | 2 | ~14% |
| 6 | **serverless** | `serverless/urls.py` | 51 | 0 | 52 (`@api_view`) + 12 (admin CBV) | 6 | ~12% |
| 7 | **thesis** | `thesis/urls.py` | 8 + 3 routers | 3 (`Thesis/Premise/Indicator`) | 0 | 0 | 0% |
| 8 | **validation** | `validation/api/urls.py` | 6 | 0 | 0 | 0 | 0% |
| 9 | **chainsight** | `chainsight/api/urls.py` | 7 + 1 router | 1 (`Watchlist`) | 0 | 7 | ~70% |
| 10 | **sec_pipeline** | `sec_pipeline/urls.py` | 2 | 0 | 1 (`@api_view` 1) | 0 | 0% |
| 11 | **api_request** | `api_request/urls.py` | 6 | 0 | 6 | 5 | ~83% |
| 12 | **portfolio** | `portfolio/urls.py` | 5 | 0 | 5 (`@api_view`) | 0 | 0% |
| 13 | **marketpulse** (v2) | `marketpulse/api/urls.py` | 5 | 0 | 0 | 5 | **100%** |
| 14 | **config (root)** | `config/urls.py` | 2 (root + health) | 0 | 0 | 0 | 0% |
| **합계** | | | **약 184 path** | **5 ViewSet** | **76 함수 뷰** | **약 31 view** | **~13%** |

> ViewSet 액션 포함 시 추정 총 endpoint 수: **약 200~210개**
> (NewsViewSet/ThesisViewSet/Premise/Indicator/Watchlist 각각 5~7 액션 × 5 = 약 25~30 endpoint 추가)

### 2.2 엔드포인트 상세 (CLAUDE.md 명시 앱)

#### stocks/ (38)
- `GET /` (DashboardView)
- `GET /stock/<symbol>/` (StockDetailView)
- `GET /search/` (StockSearchAPIView)
- `GET /api/chart/<symbol>/`
- `GET /api/overview/<symbol>/`
- `GET /api/balance-sheet/<symbol>/`
- `GET /api/income-statement/<symbol>/`
- `GET /api/cashflow/<symbol>/`
- `GET|POST /api/sync/<symbol>/`
- `GET /api/mvp/stocks/`, `/api/mvp/stock/<symbol>/`, `/api/mvp/rag/<symbol>/`, `/api/mvp/sectors/` (4)
- `GET /api/indicators/<symbol>/`, `/api/signal/<symbol>/`, `/api/indicators/compare/` (3)
- `GET /api/search/symbols/`, `/api/search/validate/<symbol>/`, `/api/search/popular/` (3)
- `GET /api/market-movers/`
- `GET /api/fundamentals/{key-metrics,ratios,dcf,rating,all}/<symbol>/` (5)
- `GET /api/screener/`, `/api/screener/{large-cap,high-dividend,low-beta}/`, `/api/screener/sector/<sector>/`, `/api/screener/exchange/<exchange>/` (6)
- `GET /api/quotes/index/`, `/api/quotes/<symbol>/`, `/api/quotes/batch/`, `/api/quotes/major-indices/`, `/api/quotes/sector-performance/` (5)
- `GET /eod/dashboard/`, `/eod/signal/<signal_id>/`, `/eod/pipeline/status/` (3)

#### users/ (30)
- JWT: `signup/`, `login/`, `logout/`, `refresh/`, `verify/`, `change-password/`, `profile/` (7)
- 세션 인증: `me/`, `''`(Users), `@<user_name>/`, `change_password/`, `login/`, `logout/` (6)
- Favorites: `favorites/`, `favorites/add/<id>/`, `favorites/remove/<id>/` (3)
- Portfolio: `portfolio/`, `summary/`, `table/`, `refresh/`, `<pk>/`, `<pk>/quick-update/`, `symbol/<symbol>/`, `symbol/<symbol>/refresh/`, `symbol/<symbol>/status/` (9)
- Interests: `interests/`, `interests/<pk>/` (2)
- Watchlist: `watchlist/`, `watchlist/<pk>/`, `<pk>/add-stock/`, `<pk>/bulk-add/`, `<pk>/bulk-remove/`, `<pk>/stocks/`, `<pk>/stocks/<symbol>/`, `<pk>/stocks/<symbol>/remove/` (8)

> 단, `users/jwt/refresh/` 는 `simplejwt`의 `TokenRefreshView`라 drf-spectacular가 자동 인식 가능

#### news/ (router 기반)
- `NewsViewSet` 단일 → 표준 액션 + `@action` 메서드. 자세한 액션 수는 `news/api/views.py` 추가 분석 필요.

#### macro/ (9)
- `pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis/ (14)
- DataBasket: `baskets/`, `baskets/<pk>/`, `<pk>/add-item/`, `<pk>/add-stock-data/`, `<pk>/items/<item_id>/`, `<pk>/clear/` (6)
- Session: `sessions/`, `sessions/<pk>/`, `<pk>/messages/`, `<pk>/chat/stream/` (4)
- Monitoring: `monitoring/{usage,cost,cache,history,pricing}/` (5)

#### serverless/ (51 + admin)
- Admin Dashboard: `admin/dashboard/{overview,stocks,screener,market-pulse,news,system,tasks,actions}/` + `actions/status/<task_id>/` + news 카테고리 3개 (총 11)
- Movers: `movers`, `movers/<symbol>`, `sync`, `sync-now` (4)
- Keywords: `keywords/batch`, `keywords/generate-all`, `keywords/generate-screener`, `keywords/<symbol>` (4)
- Breadth: `breadth`, `breadth/history`, `breadth/sync` (3)
- Heatmap: `heatmap/sectors`, `heatmap/sectors/<sector>/stocks`, `heatmap/sync` (3)
- Presets: `presets`, `trending`, `shared/<code>`, `import/<code>`, `<id>`, `<id>/execute`, `<id>/share` (7)
- Filters/Screener: `filters`, `screener` (2)
- Alerts: `alerts`, `history`, `history/<id>/read`, `history/<id>/dismiss`, `<id>`, `<id>/toggle` (6)
- Thesis: `generate`, `shared/<code>`, `<id>`, `''`(list) (4)
- ETF: `etf/{status,sync,resolve-url}`, `etf/<symbol>/holdings`, `etf/stock/<symbol>/{themes,peers}`, `themes`, `themes/refresh`, `themes/<id>/stocks` (9)
- LLM relations: `llm-relations/{extract,sync,stats,<symbol>}` (4)
- Institutional: `institutional/sync`, `institutional/<symbol>/peers`, `institutional/<symbol>` (3)
- Regulatory/Patent: `regulatory/<symbol>`, `patent-network/<symbol>` (2)
- Health: `health`

#### thesis/ (8 explicit + 3 router 합)
- Conversation: `conversation/start/`, `conversation/respond/`, `conversation/news-issues/`, `conversation/suggest/` (4)
- Monitoring: `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<indicator_id>/readings/` (2)
- Alerts: `alerts/`, `alerts/<aid>/read/` (2)
- Routers: `Thesis`, `Premise`, `Indicator` ViewSet (각 5~7 액션)

#### validation/ (6)
- `<symbol>/{summary,metrics,leader-comparison,presets,peer-preference,llm-filter}/`

#### chainsight/ (7 + watchlist router)
- `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`, `<symbol>/{neighbors,graph,suggestions}/` (7)
- `watchlist/` ViewSet
- 7개 view에 `@extend_schema` 적용됨 → **본 앱이 가장 많이 문서화되어 있음**

#### sec_pipeline/ (2)
- `admin/dashboard/` (function), `filing/<symbol>/` (CBV)

#### portfolio/ (5)
- `coach/{e1/garp,e5/adjustment,e2/diagnostic-card,e6/comparison,e3/metric-comment}/`
- 모두 `@api_view` 기반, schema 미작성

#### marketpulse v2 (5) — **유일하게 100% 문서화 완료된 앱**
- `overview`, `cards/<card_id>/detail`, `news/refresh`, `i18n`, `health`

#### api_request/ (6)
- `health/`, `admin/providers/{status,rate-limits,cache,test,config}/`
- 5/6 문서화됨 (health 제외)

---

## 도입 작업 목록

### 3.1 인프라 정비 (Phase A — 1~2 PR)

| 항목 | 현재 | 목표 | 작업량 |
|------|------|------|--------|
| `DISABLE_ERRORS_AND_WARNINGS` | `True` | `False` (개발), 단계적 fix | settings 1줄 + 회귀 분석 |
| `SPECTACULAR_SETTINGS.SECURITY` 정의 | 없음 | JWT Bearer 글로벌 추가 | settings 추가 |
| `SPECTACULAR_SETTINGS.SERVERS` | 없음 | dev / staging / prod URL | settings 추가 |
| `TAGS` 카테고리 | 1개 (Market Pulse v2) | 14개 앱별 태그 정의 | settings 정리 |
| v1/v2 schema 분리 | 단일 schema | `/api/v1/schema/` + `/api/v2/schema/` | `urls.py` + 별도 `SPECTACULAR_SETTINGS_V1` 패턴 검토 |
| CI 검증 | 없음 | `python manage.py spectacular --validate --fail-on-warn` | GitHub Actions 1 step |

### 3.2 ViewSet/APIView별 `@extend_schema` 추가 범위

> 산정 기준: 함수 뷰 1개 = 1 schema 작성, ViewSet 1개 = list/retrieve/create/update/destroy + 추가 `@action` 별 schema (평균 5~7 schema/ViewSet)

| 앱 | 미문서화 view | 우선순위 | 예상 schema 수 | 예상 시간 (시간 기준) |
|----|------:|----|------:|----:|
| **stocks** | 38 (CBV) | **P0** (frontend 핵심) | ~38 | 12~16h |
| **users** | 28 | **P0** (인증/포트폴리오) | ~30 | 10~12h |
| **macro** | 9 | P1 | ~9 | 3~4h |
| **thesis** | 8 + 3 ViewSet | **P0** (Phase 3 진행 중) | ~25 | 8~10h |
| **validation** | 6 | P1 | ~6 | 2~3h |
| **chainsight** | router 1 + 일부 액션 | P2 (주요 GET은 완료) | ~5 | 2h |
| **rag_analysis** | 12 | P1 (스트리밍 SSE 별도) | ~14 | 5~6h |
| **serverless (movers/breadth/heatmap/...)** | 약 45 | P1 | ~50 | 16~20h |
| **serverless (admin)** | 12 | P2 | ~12 | 4~5h |
| **portfolio** | 5 | P1 (Slice 5 진행) | ~5 | 2~3h |
| **sec_pipeline** | 2 | P2 | ~2 | 1h |
| **news (ViewSet)** | actions 일부 | P2 | ~3 | 1~2h |
| **api_request (health)** | 1 | P3 | 1 | 0.5h |
| **합계** | **약 170 view** | | **약 200 schema** | **~70~85h (약 9~11 인일)** |

### 3.3 부수 작업 (Quality of Life)

1. **응답 Serializer 정형화** — 현재 `Response({"key": value, ...})` 직접 반환 패턴 다수.
   - drf-spectacular는 명시 serializer를 가장 정확히 추론.
   - `inline_serializer()` 또는 별도 Response Serializer 정의 필요.
   - 영향 범위: stocks 38, serverless 50+, macro 9 등 **약 100 view**.
   - 추정 시간: 20~30h (대부분은 한번에 처리 가능, dictionary 구조만 옮기면 됨).

2. **에러 응답 표준화** — 현재 view마다 에러 포맷 상이.
   - `OpenApiResponse(response=ErrorSerializer, examples=[...])` 표준 패턴 도입 검토.
   - 추정 시간: 4~6h (1회 정의 후 재사용).

3. **`@extend_schema` examples** — 실제 응답 예시 첨부.
   - 핵심 endpoint (stocks, users, thesis) 만 우선 → 4~6h.

### 3.4 추정 총 작업량 종합

| 단계 | 범위 | 시간 | PR 수 |
|------|------|----:|----:|
| Phase A: 인프라 정비 | settings, schema split, CI | 6~8h | 1~2 |
| Phase B: P0 (stocks/users/thesis) | 약 95 schema | 30~38h | 4~6 |
| Phase C: P1 (macro/serverless main/rag/portfolio/validation) | 약 85 schema | 28~36h | 5~7 |
| Phase D: P2/P3 (admin/news/sec/health) | 약 18 schema | 6~8h | 2~3 |
| Phase E: Serializer 정형화 + examples | 횡단 | 24~36h | 3~5 |
| **합계** | **약 200 schema** | **94~126h (~13~17 인일)** | **15~23 PR** |

### 3.5 권장 도입 순서

1. **Phase A 인프라 PR (즉시 가능)** — `DISABLE_ERRORS_AND_WARNINGS=False` 로 문제 수면 위로, JWT security 정의, 앱별 TAGS, CI validate step.
2. **Phase B P0 우선 (frontend 의존도)** — `stocks/`, `users/`, `thesis/` 가 frontend가 가장 많이 호출하는 영역. 신규 frontend PR이 contracts 기반 작업할 때 schema가 진실의 소스가 되도록.
3. **Phase E를 Phase B/C와 병행** — Serializer 정형화는 schema 작성과 동시에 진행하면 효율적.
4. **Phase C/D는 백로그 형태로 점진적 처리** — 새 endpoint 추가 시 `@extend_schema` 의무화 (PR Completion Checklist 항목 추가 권장).

---

## 부록: 핵심 파일 인덱스

| 파일 | 역할 |
|------|------|
| `pyproject.toml:38-39` | drf-spectacular 의존성 |
| `config/settings.py:205-206` | INSTALLED_APPS 등록 |
| `config/settings.py:348-362` | REST_FRAMEWORK + DEFAULT_SCHEMA_CLASS |
| `config/settings.py:365-413` | SPECTACULAR_SETTINGS |
| `config/spectacular_enums.py` | ENUM 충돌 회피용 명시 enum |
| `config/urls.py:58-68` | schema/swagger/redoc URL 등록 |
| `marketpulse/api/views/*.py` | `@extend_schema` 모범 사례 (5/5) |
| `chainsight/api/views.py` | `@extend_schema` 적용 7건 (참고용) |
| `api_request/admin_views.py` | function view에 `@extend_schema` 적용 5건 |

---

## 결론 한 줄

> **drf-spectacular은 이미 설치/연결되어 있으나 `DISABLE_ERRORS_AND_WARNINGS=True` + `@extend_schema` 적용률 ~13%로 인해 v1 영역의 자동 생성 스키마는 실용적으로 사용 불가. 약 200개 schema 작성 (~13~17 인일, 15~23 PR) 작업이 필요하며, frontend 핵심 영역인 stocks/users/thesis P0 부터 점진 도입을 권장한다.**
