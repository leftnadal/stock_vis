# API 문서 감사 보고서

> 생성일: 2026-06-02 · 읽기 전용 감사 (코드 수정 없음)
> 대상: Stock-Vis 백엔드 (Django REST Framework)
> 범위: 운영 코드 (`_dormant/`, `tests/`, `node_modules/` 제외)

---

## 핵심 요약 (TL;DR)

| 항목 | 상태 |
|------|------|
| **drf-spectacular 설치** | ✅ 설치됨 (`^0.29.0` + sidecar `^2026.4.14`) |
| **OpenAPI 스펙 자동 생성** | ✅ 가능 (`/api/v2/schema/` + Swagger + ReDoc 운영 중) |
| **스키마 노출 범위** | ⚠️ `SCHEMA_PATH_PREFIX = /api/v[12]` → v1·v2 모두 포함되나 대부분 graceful fallback |
| **`@extend_schema` 적용** | ⚠️ **35건** (전체 ~250개 엔드포인트 대비 부분 적용) |
| **경고 처리** | ⚠️ `DISABLE_ERRORS_AND_WARNINGS = True` — 미문서화 view는 조용히 string body로 노출 |

**결론**: 문서화 **도입은 이미 완료**되어 있고 인프라(Swagger/ReDoc/schema)는 정상 작동한다.
실제 과제는 "도입"이 아니라 **커버리지 확대** — v1 엔드포인트 대부분이 `@extend_schema` 없이
graceful fallback(부정확한 string body)으로만 노출되고 있어, 정확한 스키마를 점진적으로 채워야 한다.

---

## 현재 상태

### 1. 설치 패키지 (`pyproject.toml`)

```toml
drf-spectacular = "^0.29.0"
drf-spectacular-sidecar = "^2026.4.14"
```

- `drf-yasg` / `coreapi` 등 레거시 문서화 도구는 **사용하지 않음** (충돌 없음)
- 메모리 기록과 일치: 실제 운영 버전은 spectacular 0.29.0 + sidecar 2026.5.1

### 2. 설정 상태

**`config/settings.py`**
- `INSTALLED_APPS`: `drf_spectacular`, `drf_spectacular_sidecar` 등록됨 (L212-213)
- `REST_FRAMEWORK.DEFAULT_SCHEMA_CLASS = 'drf_spectacular.openapi.AutoSchema'` (L370)
- `SPECTACULAR_SETTINGS` 정의됨 (L377-425):

| 키 | 값 | 의미 |
|----|----|----|
| `TITLE` | `Stock-Vis Market Pulse v2 API` | ⚠️ 제목이 v2 한정으로 표기 (실제론 v1도 포함) |
| `VERSION` | `2.0` | |
| `SCHEMA_PATH_PREFIX` | `r'/api/v[12]'` | v1·v2 경로 모두 스키마 대상 |
| `SWAGGER_UI_DIST` / `REDOC_DIST` | `SIDECAR` | 정적 자산 로컬 서빙 (오프라인 가능) |
| `COMPONENT_SPLIT_REQUEST` | `True` | 요청/응답 컴포넌트 분리 |
| `DISABLE_ERRORS_AND_WARNINGS` | `True` | ⚠️ 미추정 serializer 경고 억제 |
| `ENUM_NAME_OVERRIDES` | 4개 enum | category/status 충돌 해결 |

**`config/spectacular_enums.py`** — enum collision 회피용 dotted-path 타깃 존재
**`config/serializers.py`** — 표준 에러 envelope serializer (drf-spectacular용)

### 3. 스펙 노출 엔드포인트 (`config/urls.py` L61-72)

```
GET /api/v2/schema/   → SpectacularAPIView   (OpenAPI 3 YAML/JSON)
    /api/v2/swagger/  → SpectacularSwaggerView
    /api/v2/redoc/    → SpectacularRedocView
```

→ **OpenAPI 스펙 자동 생성·다운로드·UI 탐색 모두 즉시 가능.**

### 4. `@extend_schema` 적용 현황 (운영 코드 35건)

| 파일 | 건수 | 비고 |
|------|------|------|
| `apps/chain_sight/api/views.py` | 7 | 핵심 영역 — 명시적 문서화 |
| `services/serverless/views.py` | 6 | 함수형 view 일부 |
| `apps/portfolio/api/views.py` | 6 | Coach E1~E6 |
| `packages/shared/api_request/admin_views.py` | 5 | Provider Admin |
| `apps/market_pulse/api/views/*` | 5 | v2 카드 5종 (overview/cards/news_refresh/i18n/health) |
| `services/rag_analysis/views.py` | 2 | 부분 |
| `services/news/api/views.py` | 2 | ⚠️ @action 30개 중 2개만 |
| `packages/shared/users/views.py` | 2 | 부분 |

> `config/settings.py`에서 grep된 2건은 **주석**이므로 실집계에서 제외했다.

**미적용(0건) 대규모 영역**: `stocks`(39 path), `macro`(10), `thesis`(~18), `validation`(6),
`sec_pipeline`(2), `iron_trading`(2). 이들은 `DISABLE_ERRORS_AND_WARNINGS=True` 덕분에
경고 없이 graceful fallback으로 노출 — 스키마에 뜨긴 하나 **요청/응답 본문이 부정확**하다.

---

## 엔드포인트 목록 (앱별)

> 집계 단위 = `urls.py`의 URL 패턴(path). ViewSet은 라우터 표준 액션(list/retrieve 등)과
> `@action` 커스텀 액션을 별도 표기. 정확한 노출 URL 수는 라우터 전개분만큼 더 많다.

### 요약 테이블

| # | 앱 (URL prefix) | urls.py 경로 | 모듈 위치 | `@extend_schema` | 문서화 상태 |
|---|----------------|:-----------:|-----------|:---------------:|:----------:|
| 1 | **stocks** (`/api/v1/stocks/`) | 39 | `packages/shared/stocks/` (8 view 파일) | 0 | ❌ |
| 2 | **users** (`/api/v1/users/`) | 35 | `packages/shared/users/` | 2 | ⚠️ |
| 3 | **news** (`/api/v1/news/`) | ViewSet 1개 (list/retrieve) + `@action` 30 | `services/news/api/` | 2 | ❌ |
| 4 | **macro** (`/api/v1/macro/`) | 10 | `apps/market_pulse/` | 0 | ❌ |
| 5 | **rag_analysis** (`/api/v1/rag/`) | 15 | `services/rag_analysis/` | 2 | ⚠️ |
| 6 | **serverless** (`/api/v1/serverless/`) | 64 | `services/serverless/` (+views_admin) | 6 | ⚠️ |
| 7 | **thesis** (`/api/v1/thesis/`) | 8 path + ViewSet 3개(+`@action` 2) | `thesis/` | 0 | ❌ |
| 8 | **validation** (`/api/v1/validation/`) | 6 | `services/validation/api/` | 0 | ❌ |
| 9 | **chainsight** (`/api/v1/chainsight/`) | 7 path + ViewSet 1개(+`@action` 5) | `apps/chain_sight/api/` | 7 | ✅ |
| 10 | **sec_pipeline** (`/api/v1/sec-pipeline/`) | 2 | `services/sec_pipeline/` | 0 | ❌ |
| 11 | api_request (`/api/v1/`) | 6 | `packages/shared/api_request/` | 5 | ✅ |
| 12 | iron_trading (`/api/v1/iron-trading/`) | 2 | `integrations/iron_trading/` | 0 | ❌ |
| 13 | portfolio coach (`/api/v1/coach/`) | 6 | `apps/portfolio/api/` | 6 | ✅ |
| 14 | market_pulse v2 (`/api/v2/market-pulse/`) | 5 | `apps/market_pulse/api/` | 5 | ✅ |
| 15 | config root (`/`) | 2 (api_root, health) | `config/views.py` | 0 | — |

> 사용자가 명시 요청한 10개 앱(stocks, users, news, macro, rag_analysis, serverless,
> thesis, validation, chainsight, sec_pipeline)을 11~15(부수 앱)와 함께 모두 포함했다.

### 상세 — 요청 대상 10개 앱

#### 1. stocks — `/api/v1/stocks/` · 39 path · 문서화 0
- **페이지 뷰(HTML, 2)**: `` 대시보드, `stock/<symbol>/` 상세
- **차트/탭(6)**: `api/chart`, `api/overview`, `api/balance-sheet`, `api/income-statement`, `api/cashflow`, `api/sync`
- **MVP(4)**: `api/mvp/stocks`, `api/mvp/stock/<symbol>`, `api/mvp/rag/<symbol>`, `api/mvp/sectors`
- **지표(3)**: `api/indicators/<symbol>`, `api/signal/<symbol>`, `api/indicators/compare`
- **검색(4)**: `search/`, `api/search/symbols`, `api/search/validate/<symbol>`, `api/search/popular`
- **Market Movers(1)**: `api/market-movers`
- **Fundamentals(5)**: `key-metrics`, `ratios`, `dcf`, `rating`, `all`
- **Screener(6)**: `screener`, `large-cap`, `high-dividend`, `sector/<sector>`, `low-beta`, `exchange/<exchange>`
- **Quotes(5)**: `index`, `<symbol>`, `batch`, `major-indices`, `sector-performance`
- **EOD(3)**: `eod/dashboard`, `eod/signal/<id>`, `eod/pipeline/status`

#### 2. users — `/api/v1/users/` · 35 path · 문서화 2
- **JWT(7)**: signup, login, logout, refresh, verify, change-password, profile
- **세션 레거시(6)**: `me`, ``, `@<user_name>`, change_password, login, logout
- **즐겨찾기(3)** · **포트폴리오(9)** · **관심사(2)** · **Watchlist(8)**

#### 3. news — `/api/v1/news/` · `NewsViewSet`(ReadOnlyModelViewSet) · 문서화 2
- 라우터 표준: list / retrieve
- **`@action` 30개**: stock_news, stock_sentiment, market, trending, all_news, sources,
  daily_keywords, generate_daily_keywords, keyword_detail, insights, market_feed,
  interest_options, personalized_feed, news_events, news_events/impact-map, ml_status 등
- ⚠️ 단일 ViewSet에 액션이 30개 → 가장 큰 단일 미문서화 표면

#### 4. macro — `/api/v1/macro/` · 10 path · 문서화 0
- pulse, fear-greed, interest-rates, inflation, global-markets, calendar, vix, sectors, sync, sync/status
- (실 모듈은 `apps/market_pulse/` — macro entry는 prefix만 유지)

#### 5. rag_analysis — `/api/v1/rag/` · 15 path · 문서화 2
- **DataBasket(6)**: list-create, detail, add-item, add-stock-data, remove-item, clear
- **Session(4)**: list-create, detail, messages, chat/stream(SSE)
- **Monitoring(5)**: usage, cost, cache, history, pricing

#### 6. serverless — `/api/v1/serverless/` · 64 path · 문서화 6
- Admin Dashboard(12), Market Movers(2), Sync(2), Keywords(4), Breadth(3),
  Heatmap(3), Presets(7), Filters(1), Screener(1), Alerts(6), Thesis(4),
  ETF(6), Themes(3), LLM Relations(4), Institutional(3), Regulatory(1),
  Patent(1), Health(1)
- ⚠️ 최대 규모 + 함수형 view 다수 → @extend_schema 작업량 가장 큼

#### 7. thesis — `/api/v1/thesis/` · 8 path + ViewSet 3개 · 문서화 0
- 함수형(8): conversation/{start,respond,news-issues,suggest}, `<id>/dashboard`,
  `<id>/indicators/<id>/readings`, alerts, alerts/`<id>`/read
- ViewSet 3개: `ThesisViewSet`(+`@action` 1), `ThesisPremiseViewSet`(nested),
  `ThesisIndicatorViewSet`(nested, +`@action` 1)

#### 8. validation — `/api/v1/validation/` · 6 path · 문서화 0
- `<symbol>/`: summary, metrics, leader-comparison, presets, peer-preference, llm-filter

#### 9. chainsight — `/api/v1/chainsight/` · 7 path + ViewSet 1개 · 문서화 7 ✅
- 함수형(7): seeds, sector/`<sector>`/graph, signals, trace,
  `<symbol>`/neighbors, `<symbol>`/graph, `<symbol>`/suggestions
- `WatchlistViewSet`(+`@action` 5: archive, resolve, recheck, expand, alternatives)
- **모범 사례** — 핵심 영역으로 지정되어 명시적 문서화 완료

#### 10. sec_pipeline — `/api/v1/sec-pipeline/` · 2 path · 문서화 0
- `admin/dashboard/`, `filing/<symbol>/`

---

## 도입 작업 목록

> ⚠️ **전제 정정**: drf-spectacular는 **이미 설치·설정·운영 중**이다.
> 따라서 작업의 본질은 "도입"이 아니라 **① 노출 범위 정상화 + ② 스키마 커버리지 확대**다.

### Phase 0 — 설정 정합화 (즉시, ~0.5h)

| 작업 | 현재 | 권장 |
|------|------|------|
| `TITLE` 정정 | `Market Pulse v2 API` | v1+v2 전체 반영 (예: `Stock-Vis API`) |
| `DISABLE_ERRORS_AND_WARNINGS` 운영 정책 | `True` (경고 은폐) | 커버리지 작업 기간엔 `False`로 두고 경고를 작업 목록으로 활용 |
| 비-API HTML 뷰 분리 | stocks의 dashboard/stock_detail이 schema에 섞임 | `@extend_schema(exclude=True)` 또는 prefix 조정 |

### Phase 1 — 고가치 영역 우선 (큰 표면부터)

`@extend_schema(request=, responses=)` 추가 대상 — **엔드포인트 수 × 외부 노출도** 기준 우선순위:

| 우선 | 앱 | 작업량(엔드포인트) | 근거 |
|:---:|----|:-----------------:|------|
| P1 | **serverless** | ~64 (그중 6 완료) | 최대 규모, 함수형 view 다수 |
| P1 | **news** | ViewSet 30 action | 단일 파일 집중 → 효율 높음 |
| P2 | **stocks** | 37 (HTML 2 제외) | 외부 소비 많음 (차트/펀더멘털/스크리너) |
| P2 | **users** | 33 (JWT 2 외) | 인증·포트폴리오 — 계약 안정성 중요 |
| P3 | **rag_analysis** | 13 | SSE 스트리밍 endpoint 스키마 주의 |
| P3 | **thesis** | ViewSet 3 + 8 path | nested router 스키마 명시 필요 |
| P4 | **macro / validation / sec_pipeline / iron_trading** | 10/6/2/2 | 소규모, 마무리 단계 |

### Phase 2 — Serializer 정비 (병행)

- 함수형 view(serverless 다수)는 응답 serializer가 없어 `@extend_schema(responses=inline_serializer(...))`
  또는 별도 응답 serializer 정의 필요 → **작업량의 상당 부분이 serializer 신설**
- `config/serializers.py`의 표준 에러 envelope를 공통 `responses={400/401/404: ...}`로 재사용 가능

### Phase 3 — CI 게이트 (선택)

- `python manage.py spectacular --file schema.yml --validate` 를 CI에 추가
- contracts/ 스펙과 자동 생성 스키마 drift 감지 (Contract-Driven Development 정책 연계)

### 예상 작업량 (러프 산정)

| 단위 | 가정 | 산정 |
|------|------|------|
| 함수형 view 1건 | serializer 신설 포함 평균 20분 | — |
| ViewSet action 1건 | `@extend_schema` 평균 10분 | — |
| **전체 미문서화** | ~200 엔드포인트 − 35 완료 = **약 165건** | **40~55시간** (serializer 신설 비중에 좌우) |
| **P1만(serverless+news ~88건)** | 우선 처리 | **20~28시간** |

> 작업량의 최대 변수는 **응답 serializer 부재**다. 함수형 view가 dict를 직접 `Response()`로
> 반환하는 경우 inline_serializer 또는 신규 serializer가 필요하며, 이 부분이 전체 공수의 절반 이상을 차지한다.

---

## 부가 발견 (참고)

1. **TITLE/VERSION 불일치** — 스키마 제목이 "Market Pulse v2"로 한정 표기되나 실제 v1 전 앱이 포함됨. 외부 소비자 혼란 가능.
2. **graceful fallback 은폐** — `DISABLE_ERRORS_AND_WARNINGS=True`로 인해 미문서화 endpoint가
   "문서화된 것처럼" 보이지만 본문은 빈 string. 실제 커버리지를 가린다.
3. **portfolio 빈 라우트** — `apps/portfolio/urls.py`는 빈 urlpatterns(legacy 제거 완료), 실 라우팅은 `coach/` 단일화. include 자체 제거 검토 여지(#65 후속).
4. **iron_trading trailing-slash 중복** — `daily-context`와 `daily-context/` 두 path가 동일 view → 스키마에 중복 노출 가능.
5. **chainsight / api_request / portfolio / market_pulse v2** 는 문서화 모범 사례 — 신규 작업 시 이들 패턴을 템플릿으로 재사용 권장.

---

*감사 방법: `config/urls.py` 진입점 → 13개 `urls.py` 전수 정독 → `@extend_schema`/`@action` grep 집계.
코드 변경 없음. ViewSet 라우터 전개 URL은 패턴 단위로 집계해 실제 노출 URL 수보다 보수적임.*
