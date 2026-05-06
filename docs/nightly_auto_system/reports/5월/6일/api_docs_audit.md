# API 문서 감사 보고서

- 감사 일자: 2026-05-07
- 대상 브랜치: portfolio
- 대상 디렉토리: `/Users/byeongjinjeong/Desktop/stock_vis`
- 모드: 읽기 전용 (코드 변경 없음)

---

## 현재 상태

### OpenAPI/Swagger 문서화 도구 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | ❌ 미설치 | `pyproject.toml`, `requirements.txt`, `poetry.lock` 검색 결과 0건 |
| `drf-yasg` | ❌ 미설치 | 동일 |
| `INSTALLED_APPS` 등록 | ❌ 없음 | `config/settings.py` 내 `drf_spectacular`, `drf_yasg`, `swagger` 키워드 없음 |
| `SPECTACULAR_SETTINGS` | ❌ 없음 | `config/settings.py` 내 관련 설정 없음 |
| 자동 스펙 엔드포인트 | ❌ 없음 | `config/urls.py`에 `/schema/`, `/swagger/`, `/redoc/` 미등록 |
| 수동 OpenAPI YAML/JSON | ⚠️ 미확인 | `contracts/` 디렉토리는 CLAUDE.md에 언급되나 실파일은 별도 감사 필요 |

### 주요 의존성 (관련만 발췌, `pyproject.toml`)

```
django = "^5.1.7"
djangorestframework-simplejwt = "^5.5.1"
django-cors-headers = "^4.9.0"
```

> `djangorestframework` 자체는 명시적으로 선언되어 있지 않으나 SimpleJWT 종속성으로 설치되며, ViewSet/Router 사용 흔적이 다수 확인됨.

### 결론

- **현재 시스템은 자동 OpenAPI/Swagger 문서를 생성하지 않는다.**
- API 문서 자동화를 위해서는 `drf-spectacular` 또는 `drf-yasg` 신규 도입이 필요하다.
- DRF ViewSet/APIView 기반 구조이므로 `drf-spectacular`(현재 권장)이 자연스럽게 호환된다.

---

## 엔드포인트 목록 (앱별 테이블)

### 집계 요약

| 앱 | URL 프리픽스 | 패턴 수 | 비고 |
|----|--------------|--------:|------|
| stocks | `/api/v1/stocks/` | 39 | APIView 기반, ViewSet 없음 |
| users | `/api/v1/users/` | 35 | JWT 7 + 세션 6 + Favorites 3 + Portfolio 9 + Interests 2 + Watchlist 8 |
| news | `/api/v1/news/` | 32 | `NewsViewSet` (ReadOnlyModelViewSet) — 표준 2 + `@action` 30 |
| macro | `/api/v1/macro/` | 10 | Pulse + 개별 지표 + 동기화 |
| rag_analysis | `/api/v1/rag/` | 15 | DataBasket 6 + Session 4 + Monitoring 5 |
| serverless | `/api/v1/serverless/` | 64 | Admin 12 + Movers/Keywords 8 + Breadth 3 + Heatmap 3 + Presets 7 + Screener/Filter 2 + Alerts 6 + Thesis(legacy) 4 + ETF/LLM/Institutional/Regulatory/Patent 18 + Health 1 |
| thesis | `/api/v1/thesis/` | 26 | Conversation 4 + Monitoring 2 + Alert 2 + 3개 ViewSet (Thesis 6 + Premise 6 + Indicator 6) |
| validation | `/api/v1/validation/` | 6 | Symbol 기반 6개 |
| chainsight | `/api/v1/chainsight/` | 16 | 명시 7 + `WatchlistViewSet` 9 (표준 4 + `@action` 5) |
| sec_pipeline | `/api/v1/sec-pipeline/` | 2 | Dashboard + Filing |
| api_request | `/api/v1/` | 6 | Provider Admin 5 + Health 1 |
| portfolio | `/api/` | 2 | Coach E1/GARP, E5/Adjustment |
| config (root) | `/` | 3 | `/`, `/health/`, `/admin/` |
| **합계** | | **256** | (config root 3 포함) |

> ViewSet은 라우터가 다수 URL을 자동 생성한다. 본 보고서에서는 라우터 표준 액션(list/create/retrieve/update/partial_update/destroy)과 `@action` 데코레이터를 합산했다.

---

### stocks (39개) — `/api/v1/stocks/`

| Method 상위 | 경로 | View 클래스 |
|------|------|-------------|
| Web | `''` | `DashboardView` |
| Web | `stock/<symbol>/` | `StockDetailView` |
| Web | `search/` | `StockSearchAPIView` |
| API | `api/chart/<symbol>/` | `StockChartDataAPIView` |
| API | `api/overview/<symbol>/` | `StockOverviewAPIView` |
| API | `api/balance-sheet/<symbol>/` | `StockBalanceSheetAPIView` |
| API | `api/income-statement/<symbol>/` | `StockIncomeStatementAPIView` |
| API | `api/cashflow/<symbol>/` | `StockCashFlowAPIView` |
| API | `api/sync/<symbol>/` | `StockSyncAPIView` |
| MVP | `api/mvp/stocks/` | `StockMVPListView` |
| MVP | `api/mvp/stock/<symbol>/` | `StockMVPDetailView` |
| MVP | `api/mvp/rag/<symbol>/` | `StockRAGContextView` |
| MVP | `api/mvp/sectors/` | `SectorListView` |
| Indicator | `api/indicators/<symbol>/` | `TechnicalIndicatorView` |
| Indicator | `api/signal/<symbol>/` | `IndicatorSignalView` |
| Indicator | `api/indicators/compare/` | `IndicatorComparisonView` |
| Search | `api/search/symbols/` | `SymbolSearchView` |
| Search | `api/search/validate/<symbol>/` | `SymbolValidateView` |
| Search | `api/search/popular/` | `PopularSymbolsView` |
| Movers | `api/market-movers/` | `MarketMoversView` |
| Fundamental | `api/fundamentals/key-metrics/<symbol>/` | `KeyMetricsView` |
| Fundamental | `api/fundamentals/ratios/<symbol>/` | `RatiosView` |
| Fundamental | `api/fundamentals/dcf/<symbol>/` | `DCFView` |
| Fundamental | `api/fundamentals/rating/<symbol>/` | `RatingView` |
| Fundamental | `api/fundamentals/all/<symbol>/` | `AllFundamentalsView` |
| Screener | `api/screener/` | `StockScreenerView` |
| Screener | `api/screener/large-cap/` | `LargeCapStocksView` |
| Screener | `api/screener/high-dividend/` | `HighDividendStocksView` |
| Screener | `api/screener/sector/<sector>/` | `SectorStocksView` |
| Screener | `api/screener/low-beta/` | `LowBetaStocksView` |
| Screener | `api/screener/exchange/<exchange>/` | `ExchangeStocksView` |
| Quote | `api/quotes/index/` | `IndexQuotesView` |
| Quote | `api/quotes/<symbol>/` | `StockQuoteView` |
| Quote | `api/quotes/batch/` | `BatchQuotesView` |
| Quote | `api/quotes/major-indices/` | `MajorIndicesView` |
| Quote | `api/quotes/sector-performance/` | `SectorPerformanceView` |
| EOD | `eod/dashboard/` | `EODDashboardView` |
| EOD | `eod/signal/<signal_id>/` | `EODSignalDetailView` |
| EOD | `eod/pipeline/status/` | `EODPipelineStatusView` |

### users (35개) — `/api/v1/users/`

| 그룹 | 경로 |
|------|------|
| JWT | `jwt/signup/`, `jwt/login/`, `jwt/logout/`, `jwt/refresh/`, `jwt/verify/`, `jwt/change-password/`, `jwt/profile/` |
| Session | `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/` |
| Favorites | `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/` |
| Portfolio | `portfolio/`, `portfolio/summary/`, `portfolio/table/`, `portfolio/refresh/`, `portfolio/<pk>/`, `portfolio/<pk>/quick-update/`, `portfolio/symbol/<symbol>/`, `portfolio/symbol/<symbol>/refresh/`, `portfolio/symbol/<symbol>/status/` |
| Interests | `interests/`, `interests/<pk>/` |
| Watchlist | `watchlist/`, `watchlist/<pk>/`, `watchlist/<pk>/add-stock/`, `watchlist/<pk>/bulk-add/`, `watchlist/<pk>/bulk-remove/`, `watchlist/<pk>/stocks/`, `watchlist/<pk>/stocks/<symbol>/`, `watchlist/<pk>/stocks/<symbol>/remove/` |

### news (32개) — `/api/v1/news/`

- `NewsViewSet(ReadOnlyModelViewSet)` 표준: `GET /` (list), `GET /<pk>/` (retrieve) — 2개
- 커스텀 `@action` (30개, 일부만 발췌):

| 카테고리 | url_path |
|----------|----------|
| Stock | `stock/<symbol>`, `stock/<symbol>/sentiment` |
| 키워드 | `daily-keywords`, `daily-keywords/generate`, `keyword-detail` |
| 사용자 피드 | `market-feed`, `interest-options`, `personalized-feed` |
| News Events | `news-events`, `news-events/impact-map` |
| ML 모니터링 | `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `ml-trend`, `ml-rollback-preview`, `ml-rollback` |
| 운영 모니터링 | `collection-logs`, `pipeline-health`, `llm-usage`, `task-timeline`, `neo4j-status`, `alerts`, `alerts/<alert_pk>/resolve` |
| 기타 (default url_path) | line 219, 288, 350, 440, 816, 1244 — 총 6개 |

### macro (10개) — `/api/v1/macro/`

`pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

### rag_analysis (15개) — `/api/v1/rag/`

| 그룹 | 경로 |
|------|------|
| DataBasket | `baskets/`, `baskets/<pk>/`, `baskets/<pk>/add-item/`, `baskets/<pk>/add-stock-data/`, `baskets/<pk>/items/<item_id>/`, `baskets/<pk>/clear/` |
| Session | `sessions/`, `sessions/<pk>/`, `sessions/<pk>/messages/`, `sessions/<pk>/chat/stream/` (SSE) |
| Monitoring | `monitoring/usage/`, `monitoring/cost/`, `monitoring/cache/`, `monitoring/history/`, `monitoring/pricing/` |

### serverless (64개) — `/api/v1/serverless/`

| 카테고리 | 개수 | 비고 |
|---------|----:|------|
| Admin Dashboard | 12 | overview/stocks/screener/market-pulse/news/system/tasks/actions/task-status/news-categories(+detail/sector-options) |
| Market Movers | 2 | `movers`, `movers/<symbol>` |
| Sync | 2 | `sync`, `sync-now` |
| Keywords | 4 | batch / generate-all / generate-screener / `<symbol>` |
| Market Breadth | 3 | `breadth`, `breadth/history`, `breadth/sync` |
| Sector Heatmap | 3 | `heatmap/sectors`, `<sector>/stocks`, `heatmap/sync` |
| Screener Presets | 7 | list / trending / shared / import / detail / execute / share |
| Screener Filters/Adv | 2 | `filters`, `screener` |
| Screener Alerts | 6 | alerts(+history, history mark/dismiss, detail, toggle) |
| Investment Thesis (legacy) | 4 | generate / shared / `<id>` / list |
| Chain Sight ETF | 9 | status, sync, resolve-url, holdings, themes, peers, theme list/refresh/stocks |
| LLM Relations | 4 | extract / sync / stats / `<symbol>` |
| Institutional 13F | 3 | sync / peers / holdings |
| Regulatory + Patent | 2 | `regulatory/<symbol>`, `patent-network/<symbol>` |
| Health | 1 | `health` |

> 주의: 일부 경로는 `LEGACY_KEEP_UNTIL_DC2` 또는 `LEGACY REMOVED` 주석 존재. Chain Sight Phase 3은 `chainsight/` 앱으로 이전 진행 중.

### thesis (26개) — `/api/v1/thesis/`

| 그룹 | 경로/액션 |
|------|----------|
| Conversation | `conversation/start/`, `conversation/respond/`, `conversation/news-issues/`, `conversation/suggest/` |
| Monitoring | `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<indicator_id>/readings/` |
| Alerts | `alerts/`, `alerts/<aid>/read/` |
| `ThesisViewSet` (ModelViewSet, PUT/DELETE 제외) | list/create/retrieve/partial_update + 2 `@action` = 6 |
| `ThesisPremiseViewSet` (nested under `<thesis_id>/premises/`) | list/create/retrieve/update/partial_update/destroy = 6 |
| `ThesisIndicatorViewSet` (nested under `<thesis_id>/indicators/`) | 6 (동일) |

### validation (6개) — `/api/v1/validation/`

`<symbol>/summary/`, `<symbol>/metrics/`, `<symbol>/leader-comparison/`, `<symbol>/presets/`, `<symbol>/peer-preference/`, `<symbol>/llm-filter/`

### chainsight (16개) — `/api/v1/chainsight/`

| 그룹 | 경로 |
|------|------|
| 명시 경로 (7) | `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`, `<symbol>/neighbors/`, `<symbol>/graph/`, `<symbol>/suggestions/` |
| `WatchlistViewSet` (GET/POST/DELETE 제한) | `watchlist/` (list/create), `watchlist/<pk>/` (retrieve/destroy) + `@action` 5개 = 9 |

### sec_pipeline (2개) — `/api/v1/sec-pipeline/`

`admin/dashboard/`, `filing/<symbol>/`

### api_request (6개) — `/api/v1/`

`health/`, `admin/providers/status/`, `admin/providers/rate-limits/`, `admin/providers/cache/`, `admin/providers/test/`, `admin/providers/config/`

### portfolio (2개) — `/api/`

`coach/e1/garp/`, `coach/e5/adjustment/`

### config root (3개)

`/` (api_root), `/health/`, `/admin/`

---

## 도입 작업 목록

### Step 1. drf-spectacular 설치 + 기본 설정 (S, ½일)

**예상 변경 파일**: 4개

1. `pyproject.toml` — `drf-spectacular = "^0.27.x"` 추가, `poetry lock && poetry install`
2. `config/settings.py`
   - `INSTALLED_APPS`에 `'drf_spectacular'` 추가
   - `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'`
   - `SPECTACULAR_SETTINGS = {'TITLE': 'Stock-Vis API', 'VERSION': '1.0.0', 'DESCRIPTION': '...', 'SERVE_INCLUDE_SCHEMA': False, ...}`
3. `config/urls.py`
   - `from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView`
   - 3개 path 추가: `api/schema/`, `api/schema/swagger-ui/`, `api/schema/redoc/`
4. `requirements.txt` (KB용) — 필요 시 동기화

**검증**: `python manage.py spectacular --file schema.yml --validate` 통과 확인

### Step 2. ViewSet/APIView 자동 인식 검증 (S, ½일)

drf-spectacular는 별도 데코레이터 없이도 ViewSet/APIView/Serializer를 분석하여 기본 스펙을 생성한다. **첫 단계에서 데코레이터 없이도 약 60~70%의 엔드포인트가 자동 문서화될 것으로 추정.**

- `python manage.py spectacular --file schema.yml`로 1차 생성
- 경고(W001/W002) 목록 확인 → 우선순위 결정

### Step 3. `@extend_schema` 데코레이터 추가 (M~L, 작업량 분포)

총 **256개** 엔드포인트 중, 데코레이터 명시 작업이 강하게 권장되는 항목 분류:

| 우선순위 | 대상 | 개수 | 이유 | 예상 시간 |
|---------|------|----:|------|----------|
| P0 | `@action` 메서드 (news 30 + thesis 2 + chainsight 5) | 37 | 라우터 자동 검출 한계, request/response 명시 필수 | 2~3일 |
| P0 | SSE/스트리밍 (`rag_analysis/sessions/<pk>/chat/stream/`) | 1 | 비표준 응답, 수동 명시 필수 | 0.5일 |
| P1 | symbol 파라미터 사용 APIView (stocks 24 + validation 6 + chainsight 명시 5 등) | ~40 | `@extend_schema(parameters=[OpenApiParameter('symbol', ...)])` 일관 적용 | 2일 |
| P1 | JWT/인증 엔드포인트 (users JWT 7) | 7 | 보안 스킴 명시(`security=[{'jwtAuth': []}]`), 401 응답 스키마 | 0.5일 |
| P1 | Admin 전용 (serverless admin 12 + sec_pipeline admin 1 + api_request admin 5) | 18 | `IsAdminUser` 권한 표기, 운영용 vs 사용자용 그룹 분리 | 1일 |
| P2 | 일반 ListCreate/RetrieveUpdateDestroy (users 잔여, rag_analysis, validation, portfolio 등) | ~80 | Serializer 추론으로 대부분 자동 처리, 응답 예시(`examples`)만 보강 | 2~3일 |
| P3 | Legacy/제거 예정 (serverless thesis 4, ETF Phase 3 등) | ~13 | 문서화 보류 또는 `@extend_schema(exclude=True)` 처리 | 0.5일 |

**합계 예상**: P0~P2 핵심 작업 7~10일 (1주~1.5주, 1인 기준).

### Step 4. 태그/그룹/네임스페이스 정리 (S, 1일)

- `SPECTACULAR_SETTINGS`의 `TAGS` 또는 `@extend_schema(tags=['Stocks'])` 적용
- 권장 태그: `Stocks`, `Users`, `News`, `Macro`, `RAG`, `Serverless/Admin`, `Serverless/Movers`, `Thesis`, `Validation`, `ChainSight`, `SEC`, `Provider Admin`, `Portfolio Coach`, `Health`
- `serverless`(64개)는 단일 태그가 너무 비대 → 카테고리별 4~5 태그로 세분 권장

### Step 5. CI/배포 통합 (S, ½일)

- `python manage.py spectacular --file contracts/openapi.yml --validate` 를 pre-commit 또는 CI에 추가
- CLAUDE.md `Contract-Driven Development` 절과 연결: 생성된 `openapi.yml`을 `contracts/`의 진실의 소스로 채택
- `frontend/`의 타입 자동 생성 도입 시 `openapi-typescript` 등 별도 검토(본 보고서 범위 외)

### Step 6. 문서 페이지 보안/운영 (S, 0.5일)

- 운영 환경에서 Swagger/Redoc UI 노출 정책 결정 (예: `IsAdminUser` 또는 IP 화이트리스트)
- `SPECTACULAR_SETTINGS['SERVE_PERMISSIONS']` 설정

---

### 종합 예상 작업량

| 단계 | 작업 | 인일(man-day) |
|------|------|-------------:|
| Step 1 | 설치 + 기본 설정 | 0.5 |
| Step 2 | 1차 스펙 생성 + 경고 분석 | 0.5 |
| Step 3 | `@extend_schema` 데코레이터 추가 (P0~P2) | 7~10 |
| Step 4 | 태그/그룹 정리 | 1 |
| Step 5 | CI/contracts 통합 | 0.5 |
| Step 6 | 운영/보안 | 0.5 |
| **합계** | | **10~13 인일 (1인 기준 약 2~2.5주)** |

### 리스크 / 주의사항

1. **ViewSet의 `@action` 우선 처리 필수**: news 앱 30개 액션은 자동 추론으로 응답 스키마가 부정확할 가능성이 높다 → P0.
2. **SSE 스트리밍 엔드포인트** (`rag_analysis/sessions/<pk>/chat/stream/`)는 `@extend_schema(responses=...)` 수동 명시.
3. **Legacy 경로 (Chain Sight Phase 3, serverless thesis)** 는 문서화 시 혼란 야기 가능 → `exclude=True` 또는 deprecation 표기.
4. **`config/urls.py`의 `/api/v1/` (api_request)와 `/api/` (portfolio) 혼재** — 스펙에 그대로 노출되므로 정리 권고 (감사 범위 외, 별도 이슈 권장).
5. **Symbol upper 규칙** (`symbol.upper()`): OpenAPI에는 표현되지 않는 비즈니스 규칙 → 설명(description) 또는 examples로 보완.
6. **인증 스킴 혼재**: `SimpleJWT` + 세션(쿠키) 동시 사용 → `SECURITY` 정의 시 두 스킴 모두 등록.

---

## 부록: 데이터 산출 방법

| 항목 | 방법 |
|------|------|
| 의존성 | `pyproject.toml`, `requirements.txt`, `poetry.lock` 직접 grep |
| 엔드포인트 | 13개 `urls.py`(앱별 + config + chainsight/api/urls.py + news/api/urls.py + validation/api/urls.py) 수동 read + 라우터 표준 액션 + `@action` grep 합산 |
| ViewSet 베이스 | `class .*ViewSet` grep으로 `ModelViewSet`/`ReadOnlyModelViewSet` 확인 후 표준 액션 수 결정 |
| `http_method_names` | `ThesisViewSet`(4 표준), `WatchlistViewSet`(4 표준) 제한 반영 |

> 본 보고서는 코드 변경 없이 정적 분석만으로 작성되었음.
