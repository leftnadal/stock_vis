# API 문서 감사 보고서

- **작성일**: 2026-04-28
- **범위**: Stock-Vis Backend (Django REST Framework) 전체 앱
- **감사 모드**: 읽기 전용 (코드 수정 없음)
- **참조 파일**: `config/urls.py`, 각 앱별 `urls.py`/`views*.py`, `pyproject.toml`, `config/settings.py`

---

## 현재 상태

### 1. OpenAPI/Swagger 자동 생성 도구 설치 여부

| 항목 | 결과 | 비고 |
|------|------|------|
| `drf-spectacular` (`pyproject.toml`) | ❌ 미설치 | `[tool.poetry.dependencies]`에 없음 |
| `drf-yasg` (`pyproject.toml`) | ❌ 미설치 | 동일 |
| `requirements.txt` | ❌ 없음 | Poetry 단일 사용 |
| `INSTALLED_APPS`에 `drf_spectacular` / `drf_yasg` 등록 | ❌ 미등록 | `config/settings.py:176-206` |
| `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS']` 지정 | ❌ 미지정 | `config/settings.py:338-346` — DRF 기본값(곧 deprecate) |
| `config/urls.py` 내 `/schema/`·`/swagger/`·`/redoc/` 라우트 | ❌ 없음 | `config/urls.py:22-44` |
| 코드 내 `@extend_schema` / `swagger_auto_schema` 데코레이터 | ❌ 0건 | 21개 view 파일 grep 결과 모두 0 |

**결론**: 현 시점 Stock-Vis 백엔드는 **OpenAPI 스펙을 자동 생성할 수 없는 상태**다.

### 2. Swagger/OpenAPI 스펙 생성 가능성

| 시나리오 | 가능 여부 | 근거 |
|---------|---------|------|
| 즉시 `python manage.py spectacular --file schema.yml` 실행 | ❌ 불가 | `drf-spectacular` 미설치 |
| `drf-spectacular` 설치 후 무 데코레이터 자동 추출 | ⚠️ 부분 가능 | DRF `ViewSet`/`GenericAPIView`(serializer 지정된 경우)는 자동 추론. 본 프로젝트는 다수가 `APIView` 직접 상속 + serializer 미지정 → 응답/요청 스키마 누락 다수 |
| 완전한 OpenAPI 3.0 스펙 산출 | ❌ 불가 | `@extend_schema(request=, responses=)` 명시 작성 필요 |

### 3. 현재 문서화 수단

- **수동 작성 문서**: `sub_claude_md/api-endpoints.md` (요약), `docs/features/*` (기능별)
- **코드 내 docstring**: 일부 view 클래스에 한글 docstring (예: `serverless/views.py`, `stocks/views_*.py`)
- **OpenAPI/JSON Schema 산출물**: 없음
- **Postman/Insomnia 컬렉션**: 미발견

---

## 엔드포인트 목록 (앱별 테이블)

> URL prefix는 `config/urls.py:22-44` 기준. ViewSet은 DefaultRouter에 의해 자동 생성되는 표준 액션(list/create/retrieve/update/partial_update/destroy) + `@action` 데코레이터 액션을 모두 합산.

### 3.1 앱별 엔드포인트 수 집계

| # | 앱 | URL Prefix | URL 패턴 수 | 비고 |
|---|-----|-----------|------------|------|
| 1 | `users` | `/api/v1/users/` | **35** | JWT 7 + 세션 6 + Favorites 3 + Portfolio 9 + Interests 2 + Watchlist 8 |
| 2 | `stocks` | `/api/v1/stocks/` | **39** | views.py + views_mvp/indicators/search/market_movers/fundamentals/screener/exchange/eod 8개 분리 |
| 3 | `news` | `/api/v1/news/` | **30+** | 단일 `NewsViewSet` + `@action` 30개 (router 기본 list/retrieve 추가 가능) |
| 4 | `macro` | `/api/v1/macro/` | **10** | Market Pulse v1 (pulse, fear-greed, rates, inflation, global, calendar, vix, sectors, sync x2) |
| 5 | `rag_analysis` | `/api/v1/rag/` | **15** | DataBasket 6 + Session 4 + Monitoring 5 |
| 6 | `serverless` | `/api/v1/serverless/` | **64** | Admin 12 + Movers 8 + Breadth 3 + Heatmap 3 + Presets 7 + Filters/Screener 2 + Alerts 6 + Thesis(legacy) 4 + ETF 9 + LLM Relations 4 + Institutional 3 + Regulatory/Patent 2 + Health 1 |
| 7 | `thesis` | `/api/v1/thesis/` | **28** | Conversation 4 + Monitoring 2 + Alerts 2 + Premise nested 6 + Indicator nested 7 + Thesis main 7 |
| 8 | `validation` | `/api/v1/validation/` | **6** | summary, metrics, leader-comparison, presets, peer-preference, llm-filter |
| 9 | `chainsight` | `/api/v1/chainsight/` | **18** | 정적 4 + 동적 3 + Watchlist ModelViewSet 11 (기본 6 + @action 5) |
| 10 | `sec_pipeline` | `/api/v1/sec-pipeline/` | **2** | dashboard, filing/<symbol> |
| 11 | `api_request` | `/api/v1/` | **6** | health + admin/providers/* x5 |
| - | (root) | `/` | 2 | api-root, health-check |
| **합계** | | | **약 255** | |

### 3.2 앱별 상세 엔드포인트

#### users (`/api/v1/users/`) — 35
**JWT 인증 (`users/jwt_views.py`)**
- `POST jwt/signup/`, `POST jwt/login/`, `POST jwt/logout/`, `POST jwt/refresh/`, `GET jwt/verify/`, `POST jwt/change-password/`, `PUT jwt/profile/`

**세션 인증 (`users/views.py`)**
- `GET/PUT me/`, `GET/POST ''`, `GET @<user_name>/`, `POST change_password/`, `POST login/`, `POST logout/`

**Favorites**
- `GET favorites/`, `POST favorites/add/<int:stock_id>/`, `DELETE favorites/remove/<int:stock_id>/`

**Portfolio**
- `GET/POST portfolio/`, `GET portfolio/summary/`, `GET portfolio/table/`, `POST portfolio/refresh/`, `GET/PUT/DELETE portfolio/<int:pk>/`, `PATCH portfolio/<pk>/quick-update/`, `GET portfolio/symbol/<symbol>/`, `POST portfolio/symbol/<symbol>/refresh/`, `GET portfolio/symbol/<symbol>/status/`

**Interests / Watchlist**
- `GET/POST interests/`, `DELETE interests/<pk>/`
- `GET/POST watchlist/`, `GET/PUT/DELETE watchlist/<pk>/`, `POST watchlist/<pk>/add-stock/`, `POST watchlist/<pk>/bulk-add/`, `POST watchlist/<pk>/bulk-remove/`, `GET watchlist/<pk>/stocks/`, `PATCH watchlist/<pk>/stocks/<symbol>/`, `DELETE watchlist/<pk>/stocks/<symbol>/remove/`

#### stocks (`/api/v1/stocks/`) — 39
- 메인 페이지: `''` (Dashboard), `stock/<symbol>/` (Detail), `search/`
- API tabs: `api/chart/<symbol>/`, `api/overview/<symbol>/`, `api/balance-sheet/<symbol>/`, `api/income-statement/<symbol>/`, `api/cashflow/<symbol>/`, `api/sync/<symbol>/`
- MVP: `api/mvp/stocks/`, `api/mvp/stock/<symbol>/`, `api/mvp/rag/<symbol>/`, `api/mvp/sectors/`
- 기술적 지표: `api/indicators/<symbol>/`, `api/signal/<symbol>/`, `api/indicators/compare/`
- 검색: `api/search/symbols/`, `api/search/validate/<symbol>/`, `api/search/popular/`
- Market Movers: `api/market-movers/`
- Fundamentals: `api/fundamentals/key-metrics/<symbol>/`, `ratios/`, `dcf/`, `rating/`, `all/`
- Screener: `api/screener/`, `large-cap/`, `high-dividend/`, `sector/<sector>/`, `low-beta/`, `exchange/<exchange>/`
- Quotes: `api/quotes/index/`, `<symbol>/`, `batch/`, `major-indices/`, `sector-performance/`
- EOD Dashboard: `eod/dashboard/`, `eod/signal/<id>/`, `eod/pipeline/status/`

#### news (`/api/v1/news/`) — 30+ (`NewsViewSet` 단일)
**`@action` 30개**: `stock/<symbol>` (list+sentiment), `daily-keywords` (GET/POST), `keyword-detail`, `market-feed`, `interest-options`, `personalized-feed`, `news-events`, `news-events/impact-map`, `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `collection-logs`, `pipeline-health`, `ml-trend`, `llm-usage`, `task-timeline`, `neo4j-status`, `ml-rollback-preview`, `ml-rollback`, `alerts` (list+resolve), 외 다수.

(추가로 ViewSet 기반 액션이 등록되면 list/retrieve가 함께 노출될 수 있음)

#### macro (`/api/v1/macro/`) — 10
`pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### rag_analysis (`/api/v1/rag/`) — 15
- DataBasket: `baskets/`, `baskets/<pk>/`, `baskets/<pk>/add-item/`, `baskets/<pk>/add-stock-data/`, `baskets/<pk>/items/<item_id>/`, `baskets/<pk>/clear/`
- Session: `sessions/`, `sessions/<pk>/`, `sessions/<pk>/messages/`, `sessions/<pk>/chat/stream/` (SSE)
- Monitoring: `monitoring/usage/`, `cost/`, `cache/`, `history/`, `pricing/`

#### serverless (`/api/v1/serverless/`) — 64
- **Admin Dashboard** (12): `admin/dashboard/{overview,stocks,screener,market-pulse,news,system,tasks,actions}/`, `actions/status/<task_id>/`, `news/categories/`, `news/categories/<id>/`, `news/sector-options/`
- **Market Movers** (8): `movers`, `movers/<symbol>`, `sync`, `sync-now`, `keywords/{batch,generate-all,generate-screener}`, `keywords/<symbol>`
- **Market Breadth** (3): `breadth`, `breadth/history`, `breadth/sync`
- **Sector Heatmap** (3): `heatmap/sectors`, `heatmap/sectors/<sector>/stocks`, `heatmap/sync`
- **Screener** (8): `presets`, `presets/trending`, `presets/shared/<code>`, `presets/import/<code>`, `presets/<id>`, `presets/<id>/execute`, `presets/<id>/share`, `filters`, `screener`
- **Alerts** (6): `alerts`, `alerts/history`, `alerts/history/<id>/{read,dismiss}`, `alerts/<id>`, `alerts/<id>/toggle`
- **Investment Thesis (legacy)** (4): `thesis/generate`, `thesis/shared/<code>`, `thesis/<id>`, `thesis`
- **Chain Sight ETF** (9): `etf/{status,sync,resolve-url}`, `etf/<symbol>/holdings`, `etf/stock/<symbol>/{themes,peers}`, `themes`, `themes/refresh`, `themes/<id>/stocks`
- **LLM Relations** (4): `llm-relations/{extract,sync,stats}`, `llm-relations/<symbol>`
- **Institutional 13F** (3): `institutional/sync`, `institutional/<symbol>/peers`, `institutional/<symbol>`
- **Regulatory + Patent** (2): `regulatory/<symbol>`, `patent-network/<symbol>`
- **Health** (1): `health`

#### thesis (`/api/v1/thesis/`) — 28
- Conversation (4): `conversation/{start,respond,news-issues,suggest}/`
- Monitoring (2): `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<indicator_id>/readings/`
- Alerts (2): `alerts/`, `alerts/<aid>/read/`
- Premise nested router (`<thesis_id>/premises/`): list/create/retrieve/update/partial_update/destroy = 6
- Indicator nested router (`<thesis_id>/indicators/`): 6 + `@action` 1 = 7
- Main `ThesisViewSet`: 6 + `@action` 1 = 7

#### validation (`/api/v1/validation/`) — 6
`<symbol>/{summary,metrics,leader-comparison,presets,peer-preference,llm-filter}/`

#### chainsight (`/api/v1/chainsight/`) — 18
- 정적 (4): `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`
- 동적 (3): `<symbol>/{neighbors,graph,suggestions}/`
- `WatchlistViewSet` (11): ModelViewSet 기본 6 + `@action` 5

#### sec_pipeline (`/api/v1/sec-pipeline/`) — 2
- `admin/dashboard/`, `filing/<symbol>/`

#### api_request (`/api/v1/`) — 6
- `health/`, `admin/providers/{status,rate-limits,cache,test,config}/`

#### Root — 2
- `''` (api_root), `health/`

---

## 도입 작업 목록

### 1. drf-spectacular 설치 + 설정 (Tier 1, ~0.5d)

| 단계 | 작업 | 대상 파일 | 예상 라인 |
|------|------|----------|----------|
| 1.1 | `pyproject.toml`에 `drf-spectacular = "^0.27.0"` 추가 | `pyproject.toml` | +1 |
| 1.2 | `poetry lock && poetry install` | (CI/로컬) | - |
| 1.3 | `INSTALLED_APPS`에 `'drf_spectacular'` 추가 | `config/settings.py:176` | +1 |
| 1.4 | `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'` | `config/settings.py:338` | +1 |
| 1.5 | `SPECTACULAR_SETTINGS` (TITLE, VERSION, DESCRIPTION, SERVE_INCLUDE_SCHEMA 등) | `config/settings.py` | +20 |
| 1.6 | `/api/schema/`, `/api/schema/swagger-ui/`, `/api/schema/redoc/` 라우트 추가 | `config/urls.py` | +3 |
| 1.7 | `python manage.py spectacular --file schema.yml --validate` 실행 검증 | (1차 베이스라인) | - |

> 효과: 자동 추출만으로 ViewSet/GenericAPIView 기반 엔드포인트(`thesis`, `chainsight WatchlistViewSet`, `news NewsViewSet`)는 50~70% 자동 문서화됨.

### 2. ViewSet/APIView별 `@extend_schema` 작업 범위

#### 2.1 우선순위 분류

| 우선순위 | 대상 | 엔드포인트 수 | 이유 |
|---------|------|---------------|------|
| **P0 (필수)** | `users` (JWT, Portfolio, Watchlist) | 35 | 외부 사용자가 가장 많이 호출 + JWT 응답 스키마는 정확해야 클라이언트 생성 가능 |
| **P0** | `stocks` (Quote/Chart/Fundamentals) | 39 | 메인 화면 의존, `<symbol>` 경로 파라미터 다수 |
| **P0** | `news NewsViewSet` | 30+ | 30개 `@action` 메서드 → 자동 추론 정확도 낮음, 명시 필수 |
| **P1** | `serverless` (Admin/Screener/Alerts) | 64 | 양 많음, 함수형 view + DRF `@api_view` 데코레이터 미사용 다수 → serializer 명시 필요 |
| **P1** | `thesis` | 28 | Nested router 구조 + `<uuid>` 파라미터, 기본 ModelViewSet은 자동 추론 가능 |
| **P2** | `rag_analysis`, `chainsight`, `validation`, `macro` | 49 | 내부 사용 위주, 자동 추론 + 최소 데코레이터로 충분 |
| **P2** | `sec_pipeline`, `api_request`, `root` | 10 | 관리자/헬스체크용, 우선순위 낮음 |

#### 2.2 데코레이터 작업 패턴

**APIView 기반 (대부분의 view)**
```python
@extend_schema(
    tags=['stocks'],
    parameters=[OpenApiParameter('symbol', str, OpenApiParameter.PATH)],
    responses={200: StockOverviewSerializer, 404: ErrorSerializer},
)
class StockOverviewAPIView(APIView):
    def get(self, request, symbol): ...
```

**ViewSet (`@action`)**
```python
@extend_schema(
    request=DailyKeywordRequestSerializer,
    responses={200: DailyKeywordResponseSerializer},
)
@action(detail=False, methods=['post'], url_path='daily-keywords/generate')
def generate_daily_keywords(self, request): ...
```

**함수형 view (serverless)**
```python
@extend_schema(
    methods=['GET'],
    parameters=[...],
    responses={200: MarketMoversSerializer},
)
@api_view(['GET'])
def market_movers_api(request): ...
```

#### 2.3 Serializer 분리 부담

| 앱 | 기존 Serializer | 추가 작성 필요 (응답 스키마) |
|----|----------------|------------------------------|
| users | 다수 (`UserSerializer`, `PortfolioSerializer`) | 소량 (~5) |
| stocks | 일부 | 多 (Overview/Chart/MVP/Fundamentals 응답 dict 형태) — 약 15 |
| news | 일부 | 多 (`@action` 30개 응답 형태 다양) — 약 25 |
| serverless | 거의 없음 (raw dict 반환 다수) | 매우 多 — 약 30 |
| thesis | 충실 | 소량 (~3) |
| chainsight, rag, validation, macro | 일부 | 약 10 |

> serverless는 함수형 view가 raw `Response({...})` 형태로 dict를 반환하는 패턴이 많아 Serializer 신규 작성 부담이 가장 크다.

### 3. 예상 작업량

| 작업 항목 | 예상 시간 | 산출물 |
|---------|----------|--------|
| Tier 1: 설치 + 기본 설정 + 자동 추출 베이스라인 | **0.5d** | `schema.yml` 1차 (불완전) |
| Tier 2: P0 (users, stocks, news) `@extend_schema` + Serializer 보강 | **2.5d** | 약 100개 엔드포인트 정확 문서화 |
| Tier 3: P1 (serverless, thesis) — Serializer 신규 작성 포함 | **3.5d** | 약 92개 |
| Tier 4: P2 (rag, chainsight, validation, macro, sec_pipeline) | **1.5d** | 약 49개 |
| Tier 5: CI 통합 (`spectacular --validate` 게이트), 프론트 타입 자동 생성 | **0.5d** | `contracts/openapi.yml`, `frontend/src/types/api.ts` |
| **총합** | **약 8.5d (1.5~2주)** | OpenAPI 3.0 + Swagger UI + Redoc + TypeScript 타입 |

### 4. 단계별 권장 마일스톤

1. **M1 (1일)**: 설치 + Swagger UI 노출 + 자동 추출 (불완전 스펙 OK)
2. **M2 (3일)**: P0 데코레이터 작업 + JWT/Portfolio/Stock 코어 정확 문서화
3. **M3 (4일)**: P1 + serverless Serializer 신설
4. **M4 (1일)**: P2 정리 + CI 통합 + `contracts/` 동기화

### 5. 위험 / 주의사항

- `serverless/views.py`(76개 함수형 뷰)는 `@api_view` 적용 여부 혼재 → 일부는 plain Django view로 등록되어 있어 DRF 스키마 추론 대상에서 제외됨. 사전 점검 필요.
- `news/api/views.py`의 `NewsViewSet`은 단일 클래스에 30+ `@action`이 집중되어 있어, 데코레이터 누락 시 자동 추출만으로는 응답 스키마 추론이 불가능.
- `thesis`, `chainsight`의 nested router (`<uuid>/premises/`, `<uuid>/indicators/`)는 `OpenApiParameter` 명시가 없으면 path 파라미터를 누락시킬 가능성 → 명시적 `@extend_schema_view` 권장.
- `rag_analysis/views.py`의 `ChatStreamView`는 SSE(Server-Sent Events) 응답 → drf-spectacular는 SSE를 표준 OpenAPI로 표현하지 못함. `@extend_schema(responses=OpenApiTypes.STR, description="SSE stream")`로 우회 필요.
- 기존 `frontend/` 타입 정의(`contracts/shared-types.ts`)와 자동 생성 타입의 정합성 검증 필요 — 자동 생성으로 대체하면 수동 타입 제거 가능.

---

## 부록: 검증 명령

```bash
# 의존성 미설치 확인
poetry show drf-spectacular  # → not found
poetry show drf-yasg          # → not found

# 어노테이션 0건 확인
grep -rE "@extend_schema|@swagger_auto_schema" \
  stocks/ users/ news/ macro/ rag_analysis/ \
  serverless/ thesis/ validation/ chainsight/ sec_pipeline/ \
  --include="*.py" | wc -l   # → 0

# OpenAPI 라우트 부재 확인
grep -E "schema|swagger|redoc" config/urls.py   # → 0건
```
