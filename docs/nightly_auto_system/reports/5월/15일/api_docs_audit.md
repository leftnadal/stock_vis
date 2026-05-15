# API 문서 감사 보고서

> 생성일: 2026-05-15
> 대상: Stock-Vis Backend (Django REST Framework)
> 감사 모드: **읽기 전용** (코드 수정 없음)
> 비교 기준: 직전 보고서 (`5월/14일/api_docs_audit.md`)

---

## 현재 상태

### 1. 라이브러리 설치 — **이미 도입 완료** ✓

| 항목 | 상태 | 위치 |
|------|------|------|
| `drf-spectacular` (^0.29.0) | ✅ 설치됨 | `pyproject.toml:38` |
| `drf-spectacular-sidecar` (^2026.4.14) | ✅ 설치됨 | `pyproject.toml:39` |
| `INSTALLED_APPS` 등록 (`drf_spectacular`, `drf_spectacular_sidecar`) | ✅ 적용됨 | `config/settings.py:205-206` |
| `DEFAULT_SCHEMA_CLASS = AutoSchema` | ✅ 적용됨 | `config/settings.py:363` |
| `SPECTACULAR_SETTINGS` 블록 | ✅ 적용됨 | `config/settings.py:370-418` |
| `EXCEPTION_HANDLER` (응답 envelope 표준화) | ✅ 적용됨 | `config/settings.py:366` |
| `drf-yasg` | ❌ 미사용 | - |

> 변동 없음: 14일 대비 라이브러리 / 설정 라인 위치 변경 없음. `requirements.txt`는 임베딩 의존성만 가지며,
> Django/DRF 의존성은 전부 `pyproject.toml` Poetry 그룹에서 관리됨.

### 2. Swagger / ReDoc 엔드포인트 — **이미 노출됨**

| URL | 역할 | 위치 |
|-----|------|------|
| `GET /api/v2/schema/` | OpenAPI 3 스펙 (JSON/YAML) | `config/urls.py:58` |
| `GET /api/v2/swagger/` | Swagger UI (sidecar) | `config/urls.py:59-63` |
| `GET /api/v2/redoc/` | ReDoc UI (sidecar) | `config/urls.py:64-68` |

- `SWAGGER_UI_DIST: SIDECAR`, `SWAGGER_UI_FAVICON_HREF: SIDECAR`, `REDOC_DIST: SIDECAR` (CDN 없이 동작)
- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` → v1/v2 모두 스캔 대상
- `COMPONENT_SPLIT_REQUEST = True` (request/response 스키마 분리)

### 3. 운영 정책 — `DISABLE_ERRORS_AND_WARNINGS = True` (변동 없음)

`config/settings.py:390`에 여전히 `DISABLE_ERRORS_AND_WARNINGS: True` 설정이 유지되고 있다.
이로 인해 schema build 시 `unable to guess serializer` 등 경고가 graceful fallback 처리되며,
**v1 대부분의 응답 본체는 `string`으로 노출**된 상태가 그대로다.

> **결론: 인프라는 100% 갖춰져 있으며, 부족한 것은 ViewSet/APIView별 명시적 `@extend_schema` 데코레이터다.**
> 직전 24시간 동안 추가된 `@extend_schema`는 0건이며, 진척 없음.

### 4. `@extend_schema` 데코레이터 적용 현황 (소스코드 기준)

| 파일 | `@extend_schema` 횟수 | 비고 |
|------|----------------------|------|
| `marketpulse/api/views/cards.py` | 1 | ✅ 완전 |
| `marketpulse/api/views/overview.py` | 1 | ✅ 완전 |
| `marketpulse/api/views/news_refresh.py` | 1 | ✅ 완전 |
| `marketpulse/api/views/i18n.py` | 1 | ✅ 완전 |
| `marketpulse/api/views/health.py` | 1 | ✅ 완전 |
| `chainsight/api/views.py` | 7 | ✅ 7개 APIView 전부 |
| `serverless/views.py` | 6 | ⚠️ ~76개 함수 뷰 중 6개 (`movers`, `presets` GET/POST, `alerts` GET/POST, `thesis_list`) |
| `api_request/admin_views.py` | 5 | ✅ 6개 중 5개 (`health_check_view`만 미적용) |
| `users/views.py` | 2 | ⚠️ 25+ class 중 `portfolio_list`, `watchlist_list` 2개 |
| `news/api/views.py` | 2 | ⚠️ ViewSet 1 + `@action` 30개 중 2개 |
| `rag_analysis/views.py` | 2 | ⚠️ 15개 View 중 2개 |
| **합계** | **29 / ~289 endpoint (~10%)** | |

**전혀 미적용된 앱**: `stocks/` (39 path), `macro/` (10 path), `thesis/` (11 path + 3 ViewSet),
`validation/` (6 path), `sec_pipeline/` (2 path), `portfolio/` (5 path).

### 5. `ENUM_NAME_OVERRIDES` — 충돌 해결 완료 (변동 없음)

`config/settings.py:394-417`에 4개 enum이 등록되어 스키마 충돌 해소됨:
- `ThesisPremiseCategoryEnum` (6 choices)
- `NewsCategoryEnum` (6 choices, `config/spectacular_enums.py`에 dotted-path target도 존재)
- `SavedPathStatusEnum` (4 choices)
- `ThesisStatusEnum` (4 choices)

---

## 엔드포인트 목록 (앱별)

> URL 카운트는 각 `urls.py`의 `path(...)` 라인 + Router 등록 ViewSet 합산.
> ViewSet은 list/create/retrieve/update/destroy 5개 표준 액션 + `@action` 추가분으로 계산.

| 앱 | mount prefix | `path()` 수 | ViewSet | `@action` | 실질 endpoint (추정) | `@extend_schema` 적용 |
|----|-------------|------------|---------|----------|----------------------|---------------------|
| **stocks** | `/api/v1/stocks/` | 39 | 0 | 0 | ~39 | 0 / 39 (0%) |
| **users** | `/api/v1/users/` | 35 | 0 | 0 | ~35 | 2 / 35 (~6%) |
| **news** | `/api/v1/news/` | 1 (router) | 1 (`NewsViewSet`) | 30 | ~30 (`@action` 중심) | 2 / 30 (~7%) |
| **macro** | `/api/v1/macro/` | 10 | 0 | 0 | ~10 | 0 / 10 (0%) |
| **rag_analysis** | `/api/v1/rag/` | 15 | 0 | 0 | ~15 | 2 / 15 (~13%) |
| **serverless** | `/api/v1/serverless/` | 64 | 0 | 0 | ~76 (다중 메소드 분기 포함) | 6 / 76 (~8%) |
| **thesis** | `/api/v1/thesis/` | 11 | 3 (`Thesis` / `Premise` / `Indicator`) | 2 | ~25 (router + nested + 표준 액션) | 0 / 25 (0%) |
| **validation** | `/api/v1/validation/` | 6 | 0 | 0 | ~6 (`peer-preference`는 POST/DELETE 분기) | 0 / 6 (0%) |
| **chainsight** | `/api/v1/chainsight/` | 7 | 1 (`WatchlistViewSet`) | 5 | ~17 (7 + 5 표준 + 5 `@action`) | 7 / 17 (~41%) |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | 0 | 0 | ~2 | 0 / 2 (0%) |
| **api_request** | `/api/v1/` | 6 | 0 | 0 | ~6 | 5 / 6 (~83%) |
| **portfolio** | `/api/coach/...` | 5 | 0 | 0 | ~5 | 0 / 5 (0%) |
| **marketpulse** | `/api/v2/market-pulse/` | 5 | 0 | 0 | ~5 | 5 / 5 ✅ (100%) |
| **합계** | | **206 path** | **4 ViewSet** | **37 @action** | **약 289 endpoint** | **29 / 289 (~10%)** |

### 앱별 주요 엔드포인트 (요약)

#### stocks (39) — `/api/v1/stocks/`
- 페이지: `dashboard`, `stock/<symbol>`, `search/`
- 데이터 API: `api/chart`, `api/overview`, `api/balance-sheet`, `api/income-statement`, `api/cashflow`, `api/sync`
- MVP: `api/mvp/stocks`, `api/mvp/stock/<symbol>`, `api/mvp/rag/<symbol>`, `api/mvp/sectors`
- 기술지표: `api/indicators/<symbol>`, `api/signal/<symbol>`, `api/indicators/compare`
- 종목 검색: `api/search/symbols`, `api/search/validate/<symbol>`, `api/search/popular`
- Market Movers: `api/market-movers`
- Fundamentals: `key-metrics`, `ratios`, `dcf`, `rating`, `all` (각 `<symbol>` 기반)
- Screener: `screener`, `large-cap`, `high-dividend`, `sector/<sector>`, `low-beta`, `exchange/<exchange>`
- Quotes: `index`, `<symbol>`, `batch`, `major-indices`, `sector-performance`
- EOD: `dashboard`, `signal/<signal_id>`, `pipeline/status`

#### users (35) — `/api/v1/users/`
- JWT: `signup`, `login`, `logout`, `refresh`, `verify`, `change-password`, `profile` (7)
- 세션: `me`, `''` (Users), `@<user_name>`, `change_password`, `login`, `logout` (6)
- Favorites: `favorites`, `add/<stock_id>`, `remove/<stock_id>` (3)
- Portfolio: list/summary/table/refresh/detail/quick-update/by-symbol/refresh/status (9)
- Interests: list-create, detail (2)
- Watchlist: list/detail/add-stock/bulk-add/bulk-remove/stocks/item-update/item-remove (8)

#### news (~30) — `/api/v1/news/` (NewsViewSet의 `@action` 중심)
- `stock_news`, `stock_sentiment`, `market`, `trending`, `all_news`, `sources`
- `daily_keywords`, `generate_daily_keywords`, `keyword_detail`, `insights`
- `market_feed`, `interest_options`, `personalized_feed`, `news_events` 등 30개 `@action`

#### macro (10) — `/api/v1/macro/`
- `pulse`, `fear-greed`, `interest-rates`, `inflation`, `global-markets`, `calendar`
- `vix`, `sectors`, `sync`, `sync/status`

#### rag_analysis (15) — `/api/v1/rag/`
- DataBasket: `baskets`, `<pk>`, `add-item`, `add-stock-data`, `items/<item_id>`, `clear` (6)
- AnalysisSession: `sessions`, `<pk>`, `messages`, `chat/stream` (SSE) (4)
- Monitoring: `usage`, `cost`, `cache`, `history`, `pricing` (5)

#### serverless (~76) — `/api/v1/serverless/`
- Admin Dashboard: 12 view (overview/stocks/screener/market-pulse/news/system/tasks/actions + 부속)
- Market Movers: 4 (`movers`, `<symbol>`, `sync`, `sync-now`)
- 키워드: 4 (`batch`, `generate-all`, `generate-screener`, `<symbol>`)
- Market Breadth: 3
- Sector Heatmap: 3
- Screener Presets: 7 (presets/trending/shared/import/detail/execute/share)
- Filters: 1, Advanced Screener: 1
- Alerts: 6 (alerts/history/history-read/history-dismiss/detail/toggle)
- Investment Thesis: 4
- ETF Holdings: 9 (status/sync/resolve-url/holdings/themes/peers/list/refresh/<theme>/stocks)
- LLM Relations: 4, Institutional (13F): 3, Regulatory/Patent: 2, Health: 1

#### thesis (~25) — `/api/v1/thesis/`
- Conversation: `start`, `respond`, `news-issues`, `suggest` (4)
- Monitoring: `<thesis_id>/dashboard`, `<thesis_id>/indicators/<indicator_id>/readings` (2)
- Alerts: `alerts/`, `alerts/<aid>/read/` (2)
- `ThesisViewSet` (CRUD + `close` action): 5 + 1
- `ThesisPremiseViewSet` (nested `<thesis_id>/premises/`): 5 표준
- `ThesisIndicatorViewSet` (nested + `auto` action): 5 + 1

#### validation (6) — `/api/v1/validation/`
- `<symbol>/summary`, `metrics`, `leader-comparison`, `presets`, `peer-preference` (POST/DELETE), `llm-filter`

#### chainsight (~17) — `/api/v1/chainsight/`
- 마켓 뷰: `seeds`, `sector/<sector>/graph`, `signals`, `trace` (4)
- 동적 뷰: `<symbol>/neighbors`, `<symbol>/graph`, `<symbol>/suggestions` (3)
- `WatchlistViewSet` (router `watchlist`): 5 표준 + 5 `@action`

#### sec_pipeline (2) — `/api/v1/sec-pipeline/`
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request (6) — `/api/v1/`
- `health/`, `admin/providers/{status, rate-limits, cache, test, config}/`

#### portfolio (5) — Portfolio Coach, `/api/coach/...`
- `coach/e1/garp/`, `coach/e2/diagnostic-card/`, `coach/e3/metric-comment/`, `coach/e5/adjustment/`, `coach/e6/comparison/`

#### marketpulse (5) — Market Pulse v2, `/api/v2/market-pulse/` ✅ 완전 문서화
- `overview`, `cards/<card_id>/detail`, `news/refresh`, `i18n`, `health`

---

## 도입 작업 목록

> 인프라는 이미 완비됨. 남은 작업은 **데코레이터 추가 + 운영 정책 변경** 두 가지.

### 0순위 — 설정 정리 (즉시 가능, 0.5일)

| 작업 | 위치 | 변경 |
|------|------|------|
| `DISABLE_ERRORS_AND_WARNINGS` 비활성 (단계적) | `config/settings.py:390` | `True → False` (운영 시 점진 적용) |
| `TAGS` 확장 (현재 1개만 등록) | `config/settings.py:383-385` | 앱별 13개 태그 추가 |
| `SCHEMA_PATH_PREFIX` 검증 | `config/settings.py:382` | v1/v2 모두 정상 스캔 확인 |

`DISABLE_ERRORS_AND_WARNINGS = True`를 끄면 schema build 시 graceful fallback이 사라져
`@extend_schema`가 없는 view에서 경고가 노출됨 — 이를 작업 trigger로 활용 가능.

### 1순위 — 핵심 사용자 경로 (우선 완료, 약 3~5일)

| 앱 | View 수 | 작업량 | 우선 이유 |
|----|--------|-------|---------|
| **users** (JWT / Portfolio / Watchlist) | 33개 추가 (현 2/35) | 1.5일 | 인증 + 핵심 사용자 데이터 |
| **stocks** (Chart / Overview / Fundamentals / Screener) | 39개 추가 (현 0/39) | 2일 | 가장 트래픽 많은 도메인 |
| **macro** | 10개 추가 | 0.5일 | 외부 노출 가능성 |
| **validation** | 6개 추가 | 0.5일 | POST/DELETE 분기 명시 필요 |
| **portfolio** | 5개 추가 | 0.5일 | 함수 뷰, 간단 |

각 View에 다음 표준 데코레이터를 추가:

```python
@extend_schema(
    tags=['Stocks'],
    summary='차트 데이터 조회',
    parameters=[
        OpenApiParameter('symbol', OpenApiTypes.STR, OpenApiParameter.PATH),
        OpenApiParameter('period', OpenApiTypes.STR, OpenApiParameter.QUERY,
                         description='1M/3M/1Y/5Y', default='1M'),
    ],
    responses={200: StockChartSerializer, 404: OpenApiTypes.OBJECT},
)
```

→ 응답 Serializer가 명시 안 된 View가 다수이므로 **간이 Response Serializer 작성 동시 진행** 필요.

### 2순위 — 함수 뷰 / 복합 ViewSet (작업 비중 큼, 약 5~7일)

| 앱 | 작업량 | 비고 |
|----|--------|------|
| **serverless** | 70개 함수 뷰 데코레이팅 | 3일 (현 6개 → 70 추가, GET/POST 분기 처리) |
| **news** ViewSet `@action` | 28개 추가 | 1.5일 (`@action` 위에 `@extend_schema` 적용) |
| **rag_analysis** | 13개 추가 | 1일 (SSE 스트리밍 `chat/stream` 별도 처리) |
| **thesis** | 11 path + 3 ViewSet | 1.5일 (nested router + `@action` 다수) |
| **chainsight** `WatchlistViewSet` | 5 액션 추가 | 0.5일 |

### 3순위 — 내부 어드민 영역 (필수성 낮음, 약 1~2일)

| 앱 | 작업량 | 비고 |
|----|--------|------|
| **serverless** admin/ | 12개 view | 0.5일 |
| **sec_pipeline** admin/dashboard | 2개 | 0.5일 |
| **api_request** admin | `health_check_view`만 잔여 | 0.1일 |

### 작업 패턴 — `@extend_schema` 표준 적용 형태

**APIView 클래스**:
```python
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

@extend_schema(
    tags=['Validation'],
    summary='피어 그룹 비교 요약',
    description='symbol의 1차 검증 결과를 카테고리별로 요약',
    parameters=[OpenApiParameter('symbol', OpenApiTypes.STR, OpenApiParameter.PATH)],
    responses={200: ValidationSummarySerializer},
)
class ValidationSummaryView(APIView):
    ...
```

**ViewSet 다중 메소드**:
```python
@extend_schema_view(
    list=extend_schema(tags=['Thesis'], summary='가설 목록'),
    create=extend_schema(tags=['Thesis'], summary='가설 생성'),
    close=extend_schema(tags=['Thesis'], summary='가설 마감'),
)
class ThesisViewSet(viewsets.ModelViewSet):
    ...
```

**함수 뷰 (multi-method `@api_view(['GET','POST'])`)**:
```python
@extend_schema(methods=['GET'], operation_id='presets_list', responses={...})
@extend_schema(methods=['POST'], operation_id='presets_create', request=..., responses={...})
@api_view(['GET', 'POST'])
def screener_presets_api(request):
    ...
```

### 예상 총 작업량

| 영역 | 작업일 |
|------|-------|
| 0순위 설정 정리 | 0.5일 |
| 1순위 핵심 사용자 경로 (~93 view) | 4.5~5일 |
| 2순위 함수 뷰 + 복합 ViewSet (~127 endpoint) | 5~7일 |
| 3순위 어드민 (~20 view) | 1일 |
| Serializer 정리 (응답 본체 명시 필요한 View) | 2~3일 |
| 검증 / 리뷰 (Swagger UI 수동 확인 + `python manage.py spectacular --validate` CI 통합) | 1일 |
| **총합** | **14~17 person-day** (약 3주, 단일 작업자 기준) |

> 인프라가 이미 완성되어 있어 **신규 도입 작업은 0**. 점진적으로 `@extend_schema`만 채우면 됨.
> 우선순위는 외부 노출 가능성이 높은 v1 stocks / users / macro / validation부터 시작 권장.

### 권장 단계적 롤아웃

1. **Phase A (1주차)** — 1순위 도메인 완료, `DISABLE_ERRORS_AND_WARNINGS=False`로 전환
2. **Phase B (2주차)** — serverless 함수 뷰 70개 (작업 비중 가장 큼)
3. **Phase C (3주차)** — news / rag / thesis ViewSet + 어드민 영역
4. **검증** — `python manage.py spectacular --file schema.yml --validate`를 CI에 통합

### 즉시 효과 (이미 활성화됨)

설정과 노출이 이미 완료되어 있어 **지금도 `/api/v2/swagger/`에 접속하면 모든 v1/v2 엔드포인트가
graceful fallback 모드로 노출**된다. 데코레이터 추가는 응답 정확도를 끌어올리는 작업.

---

## 14일 대비 변경점

| 항목 | 14일 | 15일 | 변동 |
|------|------|------|------|
| 라이브러리/설정 | 완비 | 완비 | 없음 |
| 노출된 Swagger/ReDoc | 3개 | 3개 | 없음 |
| 소스 `@extend_schema` 합계 | 29 | 29 | 0 추가 |
| 총 endpoint 추정 | ~289 | ~289 | 변경 없음 |
| `DISABLE_ERRORS_AND_WARNINGS` | True | True | 유지 |
| `ENUM_NAME_OVERRIDES` 등록 | 4 | 4 | 동일 |

> 24시간 동안 문서화 작업 진척 없음. 새로 추가된 URL 패턴도 발견되지 않음.

---

## 부록 — 참조 위치

- 설정: `config/settings.py:205-206, 363, 366, 370-418`
- URL 노출: `config/urls.py:19-23, 57-68`
- 추가 enum 헬퍼: `config/spectacular_enums.py`
- 모범 사례: `marketpulse/api/views/*.py` (Phase 1 PR-I/J 산출물)
- 함수 뷰 패턴: `serverless/views.py:43, 868-869, 1175-1176, 1743` (`@extend_schema(methods=[...])` 사용)
- ViewSet `@action` 위치: `news/api/views.py` (30), `chainsight/views/watchlist_views.py` (5), `thesis/views/thesis_views.py` (2)
