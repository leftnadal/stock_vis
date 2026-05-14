# API 문서 감사 보고서

> 생성일: 2026-05-14
> 대상: Stock-Vis Backend (Django REST Framework)
> 감사 모드: **읽기 전용** (코드 수정 없음)

---

## 현재 상태

### 1. 라이브러리 설치 — **이미 도입 완료** ✓

| 항목 | 상태 | 위치 |
|------|------|------|
| `drf-spectacular` (^0.29.0) | ✅ 설치됨 | `pyproject.toml:38` |
| `drf-spectacular-sidecar` (^2026.4.14) | ✅ 설치됨 | `pyproject.toml:39` |
| `INSTALLED_APPS` 등록 | ✅ 적용됨 | `config/settings.py:205-206` |
| `DEFAULT_SCHEMA_CLASS = AutoSchema` | ✅ 적용됨 | `config/settings.py:361` |
| `SPECTACULAR_SETTINGS` 블록 | ✅ 적용됨 | `config/settings.py:365-413` |
| `drf-yasg` | ❌ 미사용 | - |

### 2. Swagger / ReDoc 엔드포인트 — **이미 노출됨**

| URL | 역할 | 위치 |
|-----|------|------|
| `GET /api/v2/schema/` | OpenAPI 3 스펙 (JSON/YAML) | `config/urls.py:58` |
| `GET /api/v2/swagger/` | Swagger UI | `config/urls.py:60-63` |
| `GET /api/v2/redoc/` | ReDoc UI | `config/urls.py:64-67` |

- 사이드카(`SWAGGER_UI_DIST: SIDECAR`)로 정적 자산 번들링 완료 — CDN 없이 동작
- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` 로 v1/v2 모두 포함하여 스캔 중
- `COMPONENT_SPLIT_REQUEST = True` (request/response 스키마 분리)

### 3. 현재 운영 정책 — `DISABLE_ERRORS_AND_WARNINGS = True`

`config/settings.py:385`에 `DISABLE_ERRORS_AND_WARNINGS: True`가 설정되어 있어,
**Schema 생성 시 발생하는 `unable to guess serializer` 같은 경고를 묻고 graceful fallback**으로
처리하는 상태. 즉 자동 스펙은 **생성되지만 v1 대부분은 응답 본체가 `string`으로 노출**됨.

> **결론: 인프라는 100% 갖춰져 있으며, 부족한 것은 ViewSet/APIView별 명시적 `@extend_schema` 데코레이터다.**

### 4. `@extend_schema` 데코레이터 적용 현황

| 파일 | `@extend_schema` 횟수 | 비고 |
|------|----------------------|------|
| `marketpulse/api/views/cards.py` | 1 | ✅ 완전 |
| `marketpulse/api/views/overview.py` | 1 | ✅ 완전 |
| `marketpulse/api/views/news_refresh.py` | 1 | ✅ 완전 |
| `marketpulse/api/views/i18n.py` | 1 | ✅ 완전 |
| `marketpulse/api/views/health.py` | 1 | ✅ 완전 |
| `chainsight/api/views.py` | 7 | ✅ 모든 View 커버 |
| `serverless/views.py` | 6 | ⚠️ 76개 중 6개만 (~8%) |
| `api_request/admin_views.py` | 5 | ✅ 6개 중 5개 (~83%) |
| `users/views.py` | 2 | ⚠️ 27개 View 중 2개 (~7%) |
| `news/api/views.py` | 2 | ⚠️ ViewSet + 30 @action 중 2개 |
| `rag_analysis/views.py` | 2 | ⚠️ 15개 View 중 2개 (~13%) |
| **합계** | **31개 / 12개 파일** | |

**미적용 영역**: `stocks/` 전체 (39 path), `macro/` (10 path), `thesis/` (11 path + 3 ViewSet), `validation/` (6 path), `sec_pipeline/` (2 path), `portfolio/` (5 path)

### 5. ENUM_NAME_OVERRIDES — 충돌 해결 완료

`config/settings.py:389-412`에 4개 enum이 등록되어 스키마 충돌 해소됨:
- `ThesisPremiseCategoryEnum` (6 choices)
- `NewsCategoryEnum` (6 choices, `config/spectacular_enums.py`에 dotted-path target도 존재)
- `SavedPathStatusEnum` (4 choices)
- `ThesisStatusEnum` (4 choices)

---

## 엔드포인트 목록 (앱별)

> URL 패턴 카운트는 `path(...)` 라인 + Router 등록 ViewSet을 합산한 추정치
> ViewSet은 list/create/retrieve/update/destroy의 5개 표준 + `@action` 추가분

| 앱 | mount prefix | `path()` 수 | ViewSet | `@action` | 실질 엔드포인트 (추정) | `@extend_schema` 적용 |
|----|-------------|------------|---------|----------|----------------------|---------------------|
| **stocks** | `/api/v1/stocks/` | 39 | 0 | 0 | ~39 | 0 / 39 |
| **users** | `/api/v1/users/` | 35 | 0 | 0 | ~35 | 2 / 35 |
| **news** | `/api/v1/news/` | 1 (router) | 1 (NewsViewSet) | 30 | ~30 (@action 중심) | 2 / 30 |
| **macro** | `/api/v1/macro/` | 10 | 0 | 0 | ~10 | 0 / 10 |
| **rag_analysis** | `/api/v1/rag/` | 15 | 0 | 0 | ~15 | 2 / 15 |
| **serverless** | `/api/v1/serverless/` | 64 | 0 | 0 | ~76 (함수 뷰 76개 / 일부 path 중복 다중 메소드) | 6 / 76 |
| **thesis** | `/api/v1/thesis/` | 11 | 3 (Thesis/Premise/Indicator) | 2 | ~25 (router + nested + 표준 액션) | 0 / 25 |
| **validation** | `/api/v1/validation/` | 6 | 0 | 0 | ~6 (peer-preference는 POST/DELETE 분기) | 0 / 6 |
| **chainsight** | `/api/v1/chainsight/` | 7 | 1 (WatchlistViewSet) | 5 | ~17 (7 + 5 std + 5 @action) | 7 / 17 |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | 0 | 0 | ~2 | 0 / 2 |
| **api_request** | `/api/v1/` | 6 | 0 | 0 | ~6 | 5 / 6 |
| **portfolio** | `/api/coach/...` | 5 | 0 | 0 | ~5 | 0 / 5 |
| **marketpulse** | `/api/v2/market-pulse/` | 5 | 0 | 0 | ~5 | 5 / 5 ✅ |
| **합계** | | **206 path** | **4 ViewSet** | **37 @action** | **약 289 endpoint** | **29 / 289 (~10%)** |

### 앱별 주요 엔드포인트 발췌

#### stocks (39개)
- 페이지: `dashboard`, `stock_detail`, `stock_search`
- 데이터 API: `chart`, `overview`, `balance-sheet`, `income-statement`, `cashflow`, `sync`
- MVP: `stocks` list, `stock detail`, `rag context`, `sectors`
- 기술지표: `indicators`, `signal`, `indicators/compare`
- 종목 검색: `search/symbols`, `validate`, `popular`
- Market Movers: `market-movers`
- Fundamentals: `key-metrics`, `ratios`, `dcf`, `rating`, `all`
- Screener: `screener`, `large-cap`, `high-dividend`, `sector`, `low-beta`, `exchange`
- Quotes: `index`, `<symbol>`, `batch`, `major-indices`, `sector-performance`
- EOD: `dashboard`, `signal/<id>`, `pipeline/status`

#### users (35개)
- JWT: `signup`, `login`, `logout`, `refresh`, `verify`, `change-password`, `profile` (7)
- 세션: `me`, `users`, `public_user`, `login`, `logout`, `change_password` (6)
- Favorites: `favorites`, `add`, `remove` (3)
- Portfolio: 9개 (list/summary/table/refresh/detail/by-symbol 등)
- Interests: 2개
- Watchlist: 9개 (list/detail/bulk/items)

#### news (~30개 — ViewSet `@action` 중심)
- `stock_news`, `stock_sentiment`, `market`, `trending`, `all_news`, `sources`
- `daily_keywords`, `generate_daily_keywords`, `keyword_detail`, `insights`
- `market_feed`, `interest_options`, `personalized_feed`, `news_events` 등

#### macro (10개)
- `pulse`, `fear-greed`, `interest-rates`, `inflation`, `global-markets`, `calendar`, `vix`, `sectors`, `sync`, `sync/status`

#### rag_analysis (15개)
- DataBasket: `baskets`, `detail`, `add-item`, `add-stock-data`, `remove-item`, `clear` (6)
- AnalysisSession: `sessions`, `detail`, `messages`, `chat/stream` (4)
- Monitoring: `usage`, `cost`, `cache`, `history`, `pricing` (5)

#### serverless (~76 함수 뷰)
- Admin Dashboard: 12 view
- Market Movers: 4 (`movers`, `detail`, `sync`, `sync-now`)
- 키워드: 4 (`get`, `batch`, `generate-all`, `generate-screener`)
- Market Breadth: 3
- Sector Heatmap: 3
- Screener Presets: 7
- Filters: 1
- Advanced Screener: 1
- Alerts: 6
- Thesis: 4
- ETF Holdings: 7
- LLM Relations: 4
- Institutional (13F): 3
- Regulatory/Patent: 2
- Health: 1

#### thesis (router + nested)
- Conversation: `start`, `respond`, `news-issues`, `suggest` (4)
- Monitoring: `dashboard`, `indicator-readings` (2)
- Alerts: `alert-list`, `alert-read` (2)
- `ThesisViewSet` (CRUD + `close` action): list/create/retrieve/update + close (5)
- `ThesisPremiseViewSet` (nested under `<uuid:thesis_id>/premises/`): 5 표준 액션
- `ThesisIndicatorViewSet` (nested + `auto` action): 5 + 1

#### validation (6개)
- `summary`, `metrics`, `leader-comparison`, `presets`, `peer-preference` (POST/DELETE), `llm-filter`

#### chainsight (7 + WatchlistViewSet)
- 마켓: `seeds`, `sector/graph`, `signals`, `trace` (4)
- 동적: `neighbors`, `graph`, `suggestions` (3)
- WatchlistViewSet: 5 표준 + 5 @action

#### sec_pipeline (2개)
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request (6개)
- `health/`, `admin/providers/{status, rate-limits, cache, test, config}/`

#### portfolio (5개) — Portfolio Coach
- `coach/e1/garp/`, `coach/e5/adjustment/`, `coach/e2/diagnostic-card/`, `coach/e6/comparison/`, `coach/e3/metric-comment/`

#### marketpulse (5개) — Market Pulse v2 (이미 완전 문서화 ✅)
- `overview`, `cards/<id>/detail`, `news/refresh`, `i18n`, `health`

---

## 도입 작업 목록

> 인프라는 이미 완비됨. 남은 작업은 **데코레이터 추가 + 운영 정책 변경** 두 가지.

### 0순위 — 설정 정리 (즉시 가능, 0.5일)

| 작업 | 위치 | 변경 |
|------|------|------|
| `DISABLE_ERRORS_AND_WARNINGS` 비활성 (단계적) | `config/settings.py:385` | `True → False` (운영 점진적용) |
| `TAGS` 확장 (현재 1개만 등록) | `config/settings.py:378-380` | 앱별 13개 태그 추가 |
| `SCHEMA_PATH_PREFIX` 검증 | `config/settings.py:377` | v1/v2 모두 정상 스캔 확인 |

`DISABLE_ERRORS_AND_WARNINGS = True`를 끄면 schema 빌드 시 graceful fallback이 사라져
`@extend_schema`가 없는 view에서 경고가 표시됨 — 이를 작업 trigger로 활용 가능.

### 1순위 — 핵심 사용자 경로 (우선 완료, 약 3~5일)

| 앱 | View 수 | 작업량 | 우선 이유 |
|----|--------|-------|---------|
| **users** (JWT/Portfolio/Watchlist) | 27 → 25개 추가 | 1.5일 | 인증 + 핵심 사용자 데이터 |
| **stocks** (Chart/Overview/Fundamentals/Screener) | 39 → 39개 추가 | 2일 | 가장 트래픽 많은 도메인 |
| **macro** | 10 → 10개 추가 | 0.5일 | 외부 노출 가능성 |
| **validation** | 6 → 6개 추가 | 0.5일 | POST/DELETE 분기 명시 필요 |
| **portfolio** | 5 → 5개 추가 | 0.5일 | 함수 뷰, 간단 |

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

→ Serializer가 명시 안 된 View가 다수이므로 **간이 Response Serializer 작성 동시 진행** 필요.

### 2순위 — 함수 뷰 중심 영역 (작업 비중 큼, 약 5~7일)

| 앱 | 작업량 | 비고 |
|----|--------|------|
| **serverless** | 70개 함수 뷰 데코레이팅 | 3일 (현재 6개만 → 70개 추가, GET/POST 분기 처리) |
| **news** ViewSet `@action` | 28개 추가 | 1.5일 (`@action` 위에 `@extend_schema` 적용) |
| **rag_analysis** | 13개 추가 | 1일 (SSE 스트리밍 `chat/stream` 별도 처리) |
| **thesis** | 11 path + 3 ViewSet | 1.5일 (nested router + `@action` 다수) |
| **chainsight** WatchlistViewSet | 5 액션 추가 | 0.5일 |

### 3순위 — 내부 어드민 영역 (필수성 낮음, 약 1~2일)

| 앱 | 작업량 | 비고 |
|----|--------|------|
| **serverless admin/** | 12개 view | 0.5일 |
| **sec_pipeline** admin/dashboard | 2개 | 0.5일 |
| **api_request** admin (5개 완료, 1개 잔여) | health_check만 | 0.1일 |

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
| 1순위 핵심 사용자 경로 (85 view) | 4.5일 |
| 2순위 함수 뷰 + 복합 ViewSet (127 endpoint) | 7일 |
| 3순위 어드민 (20 view) | 1일 |
| Serializer 정리 (응답 본체 명시 필요한 View) | 2~3일 |
| 검증/리뷰 (Swagger UI 수동 확인) | 1일 |
| **총합** | **16~17 person-day** (약 3주, 단일 작업자 기준) |

> 인프라가 이미 완성되어 있어 **신규 도입 작업은 0**. 점진적으로 `@extend_schema`만 채우면 됨.
> 우선순위는 외부 노출 가능성이 높은 v1 stocks/users/macro/validation부터 시작 권장.

### 권장 단계적 롤아웃

1. **Phase A (1주차)** — 1순위 도메인 완료, `DISABLE_ERRORS_AND_WARNINGS=False`로 전환
2. **Phase B (2주차)** — serverless 함수 뷰 70개 (이 영역이 가장 큼)
3. **Phase C (3주차)** — news/rag/thesis ViewSet + 어드민 영역
4. **검증** — `python manage.py spectacular --file schema.yml --validate` 으로 CI 통합

### 보너스 — `@extend_schema` 도입 안 한 영역에서도 활용 가능한 즉시 효과

설정과 노출이 이미 끝났으므로 **지금 당장 `/api/v2/swagger/`에 접속하면 모든 v1/v2 엔드포인트가
graceful fallback 모드로라도 노출됨**. 데코레이터 추가는 응답 정확도를 높이는 작업.

---

## 부록 — 참조 위치

- 설정: `config/settings.py:205-206, 361, 365-413`
- URL 노출: `config/urls.py:19-23, 57-68`
- 추가 enum 헬퍼: `config/spectacular_enums.py`
- 모범 사례: `marketpulse/api/views/*.py` (Phase 1 PR-I/J 산출물)
- 함수 뷰 패턴: `serverless/views.py` (`@extend_schema(methods=[...])` 사용)
