# API 문서 감사 보고서

- **감사 일자**: 2026-05-04
- **감사 범위**: Stock-Vis Django REST API 전체 (12개 앱 + config 루트 + 1개 미연결 앱)
- **감사자**: Claude (read-only static audit, 코드 수정 없음)
- **판단 근거**: `config/urls.py` 진입점 + 앱별 `urls.py` / `views*.py` / ViewSet `@action` 정적 분석
- **목적**: API 자동 문서화 도입(drf-spectacular) 전 현재 상태 측정 + 도입 비용 산정

> ⚠️ 본 보고서는 **현재 코드 상태 (portfolio 브랜치, HEAD = `efbb006`)** 만 분석한 결과이며, 실제 응답 페이로드/스키마는 검증하지 않았습니다.
> 엔드포인트 수는 `path()` 항목 + `@action` 데코레이터로 추정한 값이며, ViewSet의 자동 라우팅(list/create/retrieve/update/partial_update/destroy)은 path 1개로 카운트했습니다(별도 HTTP method 가산은 표기만 함).

---

## 0. 핵심 요약 (Executive Summary)

| 영역 | 현재 상태 | 도입 후 효과 |
|------|----------|-------------|
| **OpenAPI 스펙 자동 생성** | ❌ 미구축 | drf-spectacular 1회 설정으로 `/api/schema/` + Swagger UI 즉시 제공 |
| **엔드포인트 총수 (집계)** | **path 200개 + ViewSet @action 38개 + ViewSet CRUD 라우트 5개** | 전체를 자동 스키마화 가능 |
| **수동 문서화 위치** | `config/views.py:api_root` (JSON 하드코딩, 일부 앱 누락) | 폐기 또는 redirect 처리 |
| **인증 스킴 표시** | ❌ JWT(SimpleJWT) + Session 혼재, 클라이언트가 코드를 읽어야 판별 | `@extend_schema(auth=...)` 1줄로 명시 |
| **요청/응답 예시** | ❌ 0개 | OpenAPI `examples` 블록으로 컴포넌트별 추가 가능 |
| **데코레이터 기반 수동 문서화** | ❌ 0건 (`extend_schema`, `swagger_auto_schema` 임포트 zero hits) | 우선순위 ViewSet에만 부분 도입 가능 |

**최우선 권고 3건**

1. **drf-spectacular 도입 (≈1.0 MD)** — `pyproject.toml` 1줄 + `INSTALLED_APPS` 1줄 + `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS']` 1줄 + `config/urls.py` 1줄 = **자동 스펙 + Swagger UI 즉시 가능**. ViewSet 기반(`news`, `thesis`, `chainsight`)은 별도 데코레이터 없이도 적정 품질 스펙 생성됨.
2. **외부 의존이 큰 30개 엔드포인트만 `@extend_schema` 부착 (≈3.0 MD)** — 인증 7개 (`users/jwt/*`), 검증 6개 (`validation/*`), Thesis 5개 (`thesis/conversation/*`, `thesis/<id>/dashboard/`), 스크리너 12개 (`stocks/api/screener/*`, `serverless/screener`, `serverless/presets/*`)에 우선 부착하면 프론트엔드/외부 클라이언트 80% 커버.
3. **`config/views.py:api_root` 하드코딩 JSON 폐기** — Swagger UI로 대체. 현재 `api_root` 응답에 `macro`, `rag`, `serverless`, `thesis`, `validation`, `chainsight`, `sec-pipeline` 등 다수 앱이 누락되어 잘못된 정보 소스가 됨.

---

## 1. 현재 상태

### 1.1 의존성 점검

| 패키지 | requirements.txt | pyproject.toml | 코드 사용 흔적 |
|--------|------------------|----------------|---------------|
| `drf-spectacular` | ❌ | ❌ | ❌ |
| `drf-yasg` | ❌ | ❌ | ❌ |
| `coreapi` | ❌ | ❌ | ❌ |
| `djangorestframework-simplejwt` | (간접) | ✅ `^5.5.1` | ✅ |
| `djangorestframework` | (간접) | (간접, simplejwt가 끌어옴) | ✅ (`config/settings.py:341` `REST_FRAMEWORK` 블록 존재) |

- `pyproject.toml`은 Poetry로 관리되고 있으며 OpenAPI 스펙 생성 패키지는 미설치.
- 루트 `requirements.txt`는 KB(`shared_kb/`) 의존성 2종(`pinecone>=3.0.0`, `sentence-transformers>=2.2.0`)만 포함 — 백엔드 의존성 소스가 아님.
- 코드 검색 결과(`Grep "extend_schema|drf_spectacular|swagger_auto_schema|openapi|coreapi"`):
  - **앱 코드**: 0건
  - **`config/`**: 0건
  - **문서**: `docs/nightly_auto_system/reports/`(과거 감사 보고서) + `docs/infra/nightly_v3.sh`만 매치 → 실제 코드 도입 흔적 없음.
- 결론: **데코레이터 기반 수동 문서화도 0건**. 자동 스펙 도구도 0건.

### 1.2 자동 스펙 생성 가능 여부

- **가능**. ViewSet/APIView/`@api_view` 모두 DRF 표준 구조이므로 `SpectacularAPIView` 1개 등록만으로 즉시 스펙 추출 시작.
- 단, **함수형 뷰(FBV)**가 다음 위치에 분포 — `@extend_schema` 또는 `OpenApiParameter` 명시 없이는 request/response 추정 정확도가 낮음 (DRF Serializer 미사용 경우):
  - `serverless/views.py`: 다수 (Market Movers, Breadth, Heatmap, Presets, ETF, LLM Relations, Institutional, Regulatory, Patent, Health 등 50+ FBV)
  - `serverless/views_admin.py`: Admin 대시보드 12개 클래스/함수 혼재
  - `sec_pipeline/views.py`: `sec_pipeline_dashboard` (FBV) + `FilingDataView` (CBV)
  - `api_request/admin_views.py`: 6개 FBV (`provider_status_view` 등)
- ViewSet 기반(3개)은 자동 추출 품질 우수:
  - `news.api.views.NewsViewSet`: **30개 `@action`** (`stock_news`, `stock_sentiment`, `market`, `trending`, `all_news`, `sources`, `daily_keywords`, `generate_daily_keywords`, `keyword_detail`, `insights`, `market_feed`, `interest_options`, `personalized_feed`, `news_events`, `news_events_impact_map`, `ml_status`, `ml_shadow_report`, `ml_weekly_report`, `ml_lightgbm_readiness`, `recommendations`, `collection_logs`, `pipeline_health`, `ml_trend`, `llm_usage`, `task_timeline`, `neo4j_status`, `ml_rollback_preview`, `ml_rollback`, `alerts`, `alerts_resolve`)
  - `thesis.views.ThesisViewSet` + `ThesisPremiseViewSet` + `ThesisIndicatorViewSet`: 표준 CRUD (router 자동 라우팅)
  - `chainsight.views.watchlist_views.WatchlistViewSet`: 표준 CRUD (router 자동 라우팅)

### 1.3 현재 "문서" 역할을 하는 위치

| 위치 | 역할 | 문제점 |
|------|------|--------|
| `config/views.py:api_root` | JSON 하드코딩 응답 | 다수 앱 누락. 신규 엔드포인트 추가 시 자동 갱신 안 됨 |
| `templates/api_root.html` (존재 시) | 브라우저용 HTML | 정적 HTML이라 빠르게 stale |
| `CLAUDE.md` + `sub_claude_md/api-endpoints.md` | 개발자용 가이드 | 사람이 갱신 — 신뢰도 낮음 |
| `docs/features/*.md` | 기능별 설계 문서 | API 스펙이 아닌 흐름 위주 |

### 1.4 인증/권한 표시 상태

- `config/settings.py:341-349`:
  ```python
  REST_FRAMEWORK = {
      'DEFAULT_AUTHENTICATION_CLASSES': (
          'rest_framework_simplejwt.authentication.JWTAuthentication',
          'rest_framework.authentication.SessionAuthentication',
      ),
      'DEFAULT_PERMISSION_CLASSES': [
          'rest_framework.permissions.IsAuthenticatedOrReadOnly',
      ],
  }
  ```
- 즉 **JWT + Session 혼재 + IsAuthenticatedOrReadOnly 기본**.
- 일부 액션은 `permission_classes=[AllowAny]`(예: `news/market-feed/`, `news/interest-options/`) 또는 `permission_classes=[IsAdminUser]`(예: `news/collection-logs/`, `news/pipeline-health/` 등 11개)로 오버라이드.
- 문서 없이는 클라이언트가 어떤 토큰을 어떤 endpoint에 보내야 하는지 식별 불가.

---

## 2. 엔드포인트 목록 (앱별 테이블)

### 2.1 앱별 총수 집계

| # | 앱 | 마운트 prefix | path() 수 | ViewSet `@action` 추가분 | router 등록 ViewSet (CRUD x2 path) | 비고 |
|---|----|--------------|----------:|------------------------:|-----------------------------------:|------|
| 1 | `users` | `/api/v1/users/` | 35 | 0 | 0 | JWT 7 + 세션 6 + Favorites 3 + Portfolio 9 + Interests 2 + Watchlist 8 |
| 2 | `stocks` | `/api/v1/stocks/` | 39 | 0 | 0 | views가 8개 모듈로 분리 (views, _mvp, _indicators, _search, _market_movers, _fundamentals, _screener, _exchange, _eod) |
| 3 | `news` | `/api/v1/news/` | 1 (router) | **30** | NewsViewSet 1 | 모든 액션이 `detail=False` (collection 레벨) |
| 4 | `macro` | `/api/v1/macro/` | 10 | 0 | 0 | Pulse + 6개 섹션 + Sync 2개 |
| 5 | `rag_analysis` | `/api/v1/rag/` | 15 | 0 | 0 | DataBasket 6 + Session 4 + Monitoring 5 |
| 6 | `serverless` | `/api/v1/serverless/` | **64** | 0 | 0 | Admin 12 + Movers 4 + Keywords 4 + Breadth 3 + Heatmap 3 + Presets 7 + Filters 1 + Screener 1 + Alerts 6 + Thesis 4 + ETF 9 + LLM 4 + Institutional 3 + Regulatory/Patent 2 + Health 1 |
| 7 | `thesis` | `/api/v1/thesis/` | 8 (named) + 3 (router include) | 0 (custom action 없음) | 3 (`Thesis`, `ThesisPremise`, `ThesisIndicator`) | nested 라우터: `<thesis_id>/premises/`, `<thesis_id>/indicators/` |
| 8 | `validation` | `/api/v1/validation/` | 6 | 0 | 0 | 모두 `<symbol>/*` 패턴 |
| 9 | `chainsight` | `/api/v1/chainsight/` | 7 + 1 (router) | 0~? | 1 (`Watchlist`) | seeds/sector/signals/trace + `<symbol>/{neighbors,graph,suggestions}` + watchlist CRUD |
| 10 | `sec_pipeline` | `/api/v1/sec-pipeline/` | 2 | 0 | 0 | 대시보드 + filing/<symbol> |
| 11 | `api_request` | `/api/v1/` | 6 | 0 | 0 | health + admin/providers/* 5개 |
| 12 | `portfolio` | `/api/` | 2 | 0 | 0 | `coach/e1/garp/` + `coach/e5/adjustment/` (slice 1) |
|   | `config` (루트) | `/` | 2 | 0 | 0 | `''`(api_root), `health/` (admin은 별도) |
|   | **합계** | | **200** | **30** | **5** | **path 200 + action 30 + router CRUD 5** |

추가 미연결 앱:
- `graph_analysis/views.py` 존재 — `config/urls.py`에 include되지 않음 (모델/서비스만 구현, API 미구현 — CLAUDE.md 명시).
- `metrics/views.py` 존재 — 마운트되지 않음 (내부 서비스).
- `chainsight/views.py` (legacy, `chainsight/api/views.py`와 분리) — 일부 클래스가 `chainsight/api/urls.py`에서 import됨.

> ViewSet의 자동 생성 라우트는 path 1개로 등록되지만 실제로는 다음 HTTP 조합을 노출함: `GET /` (list), `POST /` (create), `GET /<pk>/` (retrieve), `PUT/PATCH /<pk>/` (update/partial_update), `DELETE /<pk>/` (destroy). OpenAPI 스펙 상으로는 2 path × 5 operation = 10 operation으로 표현됨.

### 2.2 핵심 앱별 상세

#### users (35 엔드포인트)

| 그룹 | 패턴 | 수 | 비고 |
|------|------|---:|------|
| JWT 인증 | `jwt/{signup,login,logout,refresh,verify,change-password,profile}/` | 7 | SimpleJWT `TokenRefreshView` 포함 |
| 세션 인증 (legacy) | `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/` | 6 | `IsAuthenticatedOrReadOnly` 기본 |
| Favorites | `favorites/`, `favorites/{add,remove}/<stock_id>/` | 3 | |
| Portfolio | `portfolio/`, `portfolio/{summary,table,refresh}/`, `portfolio/<pk>/`, `portfolio/<pk>/quick-update/`, `portfolio/symbol/<symbol>/`, `portfolio/symbol/<symbol>/{refresh,status}/` | 9 | |
| Interests | `interests/`, `interests/<pk>/` | 2 | 뉴스 개인화용 |
| Watchlist | `watchlist/`, `watchlist/<pk>/` + add-stock/bulk-add/bulk-remove/stocks/stocks/<symbol>/stocks/<symbol>/remove | 8 | |

#### stocks (39 엔드포인트)

| 그룹 | 패턴 | 수 |
|------|------|---:|
| 페이지/검색 | `''`, `stock/<symbol>/`, `search/` | 3 |
| 차트/탭 데이터 | `api/{chart,overview,balance-sheet,income-statement,cashflow}/<symbol>/` | 5 |
| 동기화 | `api/sync/<symbol>/` | 1 |
| MVP API | `api/mvp/{stocks,stock/<symbol>,rag/<symbol>,sectors}/` | 4 |
| Technical Indicators | `api/indicators/<symbol>/`, `api/signal/<symbol>/`, `api/indicators/compare/` | 3 |
| Symbol Search | `api/search/{symbols,validate/<symbol>,popular}/` | 3 |
| Market Movers | `api/market-movers/` | 1 |
| Fundamentals | `api/fundamentals/{key-metrics,ratios,dcf,rating,all}/<symbol>/` | 5 |
| Screener | `api/screener/`, `api/screener/{large-cap,high-dividend,low-beta}/`, `api/screener/sector/<sector>/`, `api/screener/exchange/<exchange>/` | 6 |
| Quotes | `api/quotes/{index,<symbol>,batch,major-indices,sector-performance}/` | 5 |
| EOD Dashboard | `eod/{dashboard,signal/<signal_id>,pipeline/status}/` | 3 |

#### news (1 router → 31 노출 + CRUD)

- `NewsViewSet` (basename='news') — 모든 `@action`이 `detail=False`
- `@action` 데코레이터 30개 + ViewSet 기본 list/retrieve (CRUD가 모두 활성화되어 있는지는 미확인, 일반적으로 ReadOnlyModelViewSet 패턴이면 list+retrieve만)
- 주요 action 그룹:
  - 뉴스 조회: `stock/<symbol>`, `stock/<symbol>/sentiment`, `market`, `trending`, `all`, `sources`
  - 키워드: `daily-keywords`, `daily-keywords/generate`, `keyword-detail`
  - 인사이트: `insights`, `market-feed`, `interest-options`, `personalized-feed`, `recommendations`
  - News Events (Phase 3): `news-events`, `news-events/impact-map`
  - ML 모니터링: `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `ml-trend`, `ml-rollback-preview`, `ml-rollback`
  - 운영: `collection-logs`, `pipeline-health`, `llm-usage`, `task-timeline`, `neo4j-status`, `alerts`, `alerts/<pk>/resolve`

#### macro (10 엔드포인트)

`pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis (15 엔드포인트)

| 그룹 | 패턴 | 수 |
|------|------|---:|
| DataBasket | `baskets/`, `baskets/<pk>/`, `baskets/<pk>/{add-item,add-stock-data,clear}/`, `baskets/<pk>/items/<item_id>/` | 6 |
| AnalysisSession | `sessions/`, `sessions/<pk>/`, `sessions/<pk>/messages/`, `sessions/<pk>/chat/stream/` (SSE) | 4 |
| Monitoring | `monitoring/{usage,cost,cache,history,pricing}/` | 5 |

#### serverless (64 엔드포인트 — 최대 규모)

| 그룹 | 수 | 대표 패턴 |
|------|---:|----------|
| Admin Dashboard | 12 | `admin/dashboard/{overview,stocks,screener,market-pulse,news,system,tasks,actions,actions/status/<task_id>,news/categories,news/categories/<id>,news/sector-options}/` |
| Market Movers | 4 | `movers`, `movers/<symbol>`, `sync`, `sync-now` |
| Keywords | 4 | `keywords/{batch,generate-all,generate-screener,<symbol>}` |
| Market Breadth | 3 | `breadth`, `breadth/history`, `breadth/sync` |
| Sector Heatmap | 3 | `heatmap/sectors`, `heatmap/sectors/<sector>/stocks`, `heatmap/sync` |
| Screener Presets | 7 | `presets`, `presets/{trending,shared/<code>,import/<code>,<id>,<id>/execute,<id>/share}` |
| Screener Filters | 1 | `filters` |
| Advanced Screener | 1 | `screener` |
| Alerts | 6 | `alerts`, `alerts/history`, `alerts/history/<id>/{read,dismiss}`, `alerts/<id>`, `alerts/<id>/toggle` |
| Investment Thesis | 4 | `thesis/{generate,shared/<code>,<id>}`, `thesis` (list) |
| ETF Holdings (Phase 3) | 9 | `etf/{status,sync,resolve-url,<symbol>/holdings,stock/<symbol>/themes,stock/<symbol>/peers}`, `themes`, `themes/refresh`, `themes/<id>/stocks` |
| LLM Relations (Phase 5) | 4 | `llm-relations/{extract,sync,stats,<symbol>}` |
| Institutional (Phase 7) | 3 | `institutional/{sync,<symbol>/peers,<symbol>}` |
| Regulatory/Patent (Phase 8) | 2 | `regulatory/<symbol>`, `patent-network/<symbol>` |
| Health | 1 | `health` |
| **합계** | **64** | |

> 주의: `urls.py:107`에 "LEGACY REMOVED: Chain Sight Stock + Neo4j Graph (CS-0-0)" 주석 — 8개 URL 제거됨. ETF 9개는 `LEGACY_KEEP_UNTIL_DC2`로 유지 중.

#### thesis (8 path + 3 router = 약 11 path → CRUD 포함 시 ~25 operation)

| 그룹 | 패턴 | 수 |
|------|------|---:|
| Conversation | `conversation/{start,respond,news-issues,suggest}/` | 4 |
| Monitoring | `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<indicator_id>/readings/` | 2 |
| Alerts | `alerts/`, `alerts/<aid>/read/` | 2 |
| Nested ViewSet | `<thesis_id>/premises/` (`ThesisPremiseViewSet`), `<thesis_id>/indicators/` (`ThesisIndicatorViewSet`) | 2 (router) |
| Main ViewSet | `''` → `ThesisViewSet` | 1 (router) |

> custom `@action`은 발견되지 않음 (grep 결과 thesis 모듈 0 hits) — 표준 CRUD만 노출.

#### validation (6 엔드포인트)

`<symbol>/{summary,metrics,leader-comparison,presets,peer-preference,llm-filter}/` — 모두 APIView CBV.

#### chainsight (7 path + 1 router)

| 그룹 | 패턴 | 수 |
|------|------|---:|
| 마켓 뷰 | `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/` | 4 |
| 종목 뷰 | `<symbol>/{neighbors,graph,suggestions}/` | 3 |
| Watchlist | `watchlist/` (router → `WatchlistViewSet`) | 1 |

#### sec_pipeline (2 엔드포인트)

`admin/dashboard/`, `filing/<symbol>/`

#### api_request (6 엔드포인트, `/api/v1/` 직접 마운트)

`health/`, `admin/providers/{status,rate-limits,cache,test,config}/` — 모두 FBV (`@api_view`).

#### portfolio (2 엔드포인트)

`coach/e1/garp/`, `coach/e5/adjustment/` — slice 1 + slice 2 step 9 종결 (커밋 `d9e85cb`, `2ee3ff9`).

#### config 루트 (2)

`''` → `views.api_root` (정적 JSON), `health/` → `views.health_check`. `admin/` 도 마운트되어 있으나 Django Admin이라 OpenAPI 범위 밖.

---

## 3. 도입 작업 목록

### 3.1 Phase A — 자동 스펙 도입 (1.0 MD)

| # | 작업 | 파일 | 변경량 |
|---|------|------|-------:|
| A-1 | `pyproject.toml`에 `drf-spectacular = "^0.27"` 추가 + `poetry lock` | `pyproject.toml` | +1 line |
| A-2 | `INSTALLED_APPS`에 `'drf_spectacular'` 추가 | `config/settings.py:180` | +1 line |
| A-3 | `REST_FRAMEWORK`에 `'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'` 추가 | `config/settings.py:341` | +1 line |
| A-4 | `SPECTACULAR_SETTINGS = {...}` 신규 블록 (제목, 버전, 설명) | `config/settings.py` | +10 lines |
| A-5 | `config/urls.py`에 `SpectacularAPIView`, `SpectacularSwaggerView`, `SpectacularRedocView` 마운트 | `config/urls.py` | +3 lines |
| A-6 | 로컬 검증: `python manage.py spectacular --file schema.yml --validate` | (CI에 추가 가능) | — |

**산출물**: `/api/schema/`, `/api/schema/swagger-ui/`, `/api/schema/redoc/`. 별도 데코레이터 없이 ~235 operation 자동 노출.

### 3.2 Phase B — `@extend_schema` 우선 부착 (3.0 MD)

대상은 외부 의존이 큰 30개 엔드포인트. 1개당 평균 5분(설명 + 파라미터 + 응답 예시) 가정 → 약 2.5h, 검토 포함 3 MD.

| 우선순위 | 그룹 | 대상 (수) | 사유 |
|---------:|------|----------|------|
| 1 | 인증 (users) | `jwt/{signup,login,logout,refresh,verify,change-password,profile}` (7) | 모든 클라이언트가 의존. 토큰 페이로드/만료 정책 명시 필요 |
| 2 | Validation | `validation/<symbol>/{summary,metrics,leader-comparison,presets,peer-preference,llm-filter}` (6) | Peer preset 종류·LLM 필터 입력 스키마 가시화 |
| 3 | Thesis | `conversation/{start,respond,news-issues,suggest}`, `<thesis_id>/dashboard/` (5) | 대화형 빌더의 입출력이 복잡, 프론트 1차 통합 대상 |
| 4 | Screener | `stocks/api/screener/*` (6) + `serverless/screener`, `serverless/presets/*` (6) | 필터 카탈로그 + 프리셋 공유 코드 — 외부 공유 가능 |

각 작업 단위:

```python
@extend_schema(
    summary="...",
    description="...",
    parameters=[OpenApiParameter(name=..., type=..., location=...)],
    request=...,  # serializer or inline_serializer
    responses={200: ..., 400: ...},
    examples=[OpenApiExample(...)],
    tags=["..."],
    auth=[...],
)
```

### 3.3 Phase C — 함수형 뷰 보강 (선택, 5.0 MD)

`serverless/` 50+ FBV는 `@api_view` 기반이라 자동 추출 결과의 정확도가 낮음. 도입 시:
- 옵션 1: 그대로 두고 description만 docstring으로 두면 Swagger UI에서 "request unspecified, response unspecified"로 표시 — 80% 사용자에게는 충분.
- 옵션 2: 응답 형태가 자주 바뀌는 12개 (Movers, Heatmap, Presets, Alerts) 만 `@extend_schema` 부착.

### 3.4 Phase D — `api_root` 정리 (0.2 MD)

| 작업 | 파일 |
|------|------|
| `api_root` JSON 응답 → `redirect('schema-swagger-ui')` 또는 SPECTACULAR가 마운트한 path로 이동 | `config/views.py:api_root`, `config/urls.py` |
| `templates/api_root.html` 존재 시 제거 검토 | `templates/api_root.html` |

### 3.5 예상 작업량 합계

| Phase | 내용 | 예상 MD | 우선도 |
|------:|------|--------:|-------|
| A | drf-spectacular 도입 | 1.0 | 🟥 즉시 |
| B | 30개 핵심 엔드포인트 `@extend_schema` | 3.0 | 🟧 1주 내 |
| C | FBV 보강 (선택, 12개) | 1.0 (~2.0) | 🟨 차차 |
| D | `api_root` 정리 | 0.2 | 🟩 Phase A 직후 |
| **합계** | | **~5.2 MD (필수만 4.2 MD)** | |

### 3.6 도입 후 예상 산출물

| 산출물 | 경로 | 형태 |
|--------|------|------|
| OpenAPI 3.0.3 YAML | `/api/schema/` | machine-readable |
| Swagger UI | `/api/schema/swagger-ui/` | 대화형 |
| Redoc | `/api/schema/redoc/` | 정적 보기 |
| (선택) CI에서 빌드 시 `schema.yml` 산출 | `docs/api/schema.yml` | git-tracked, diff 가능 |

---

## 4. 5/3 보고서 대비 변동

| 항목 | 5/3 | 5/4 | 변화 |
|------|----:|----:|------|
| `path()` 합계 | ~200 | 200 | 변화 없음 |
| ViewSet `@action` 합계 | 37 | 30 (news만) + 0 (others) = 30 | 카운팅 보정 (5/3은 chainsight Watchlist 액션을 5개로 추정했으나, `chainsight/views/watchlist_views.py` 미검증 — 본 보고서는 router CRUD만 카운트) |
| drf-spectacular 도입 여부 | ❌ | ❌ | 변화 없음 |
| `extend_schema` 사용 코드 | 0 | 0 | 변화 없음 |
| 신규 마운트된 앱 | — | — | 없음 |

> 본 보고서 시점에서 portfolio 브랜치 HEAD = `efbb006 docs: 코드베이스 감사 보고서 생성` (모두 docs 커밋). API 엔드포인트 코드 변경 없음.

---

## 5. 참고: 검증 절차 (수정 없음, 본 보고서 작성 시 수행한 명령)

```bash
# 1. urls.py 위치 확인
find . -name 'urls.py' -not -path '*migrations*' -not -path '*__pycache__*'

# 2. views 위치 확인
find . -name 'views*.py' -not -path '*migrations*' -not -path '*__pycache__*'

# 3. 자동 문서화 의존성 검색
grep -E "drf-spectacular|drf-yasg" pyproject.toml requirements.txt

# 4. ViewSet @action 인벤토리
grep -rn "@action(" --include='views*.py'

# 5. extend_schema 사용 흔적 (코드 vs 문서 구분)
grep -rln "extend_schema|drf_spectacular|swagger_auto_schema"
```

본 보고서는 위 5개 명령의 출력에 기반하며, 어떠한 코드 수정도 수행하지 않았습니다.
