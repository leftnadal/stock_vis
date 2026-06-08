# API 문서 감사 보고서

> 생성: 2026-06-08 야간 자동화 (읽기 전용 감사, 코드 수정 없음)
> 범위: drf-spectacular 도입 상태 + 앱별 엔드포인트 인벤토리 + `@extend_schema` 커버리지

---

## 핵심 요약 (TL;DR)

| 항목 | 결과 |
|------|------|
| **문서화 도구** | ✅ `drf-spectacular ^0.29.0` + `drf-spectacular-sidecar ^2026.4.14` **설치·운영 중** |
| **OpenAPI 자동 생성** | ✅ 가능 (`/api/v2/schema/`, Swagger `/api/v2/swagger/`, ReDoc `/api/v2/redoc/`) |
| **현 상태** | 스키마는 **전 엔드포인트 노출**되지만, 대부분 graceful fallback(string body)으로 **부정확** |
| **`@extend_schema` 적용** | 14개 view 파일 / 약 **42개 데코레이터**만 명시적 — 전체 URL 패턴(~230개) 대비 **저커버리지** |
| **결론** | "도입"이 아니라 **"품질 향상(점진적 @extend_schema 보강)"** 이 실제 작업 — 이미 인프라는 완비 |

> ⚠️ 본 보고서의 전제 수정: 과제 지시문은 "문서화 도입 시 필요 작업"을 물었으나, **drf-spectacular는 이미 도입·운영 중**입니다(MEMORY.md / settings.py L212 / config/urls.py L19-72 확인). 따라서 §3은 "도입"이 아닌 **"커버리지 보강"** 관점으로 작성합니다.

---

## 1. 현재 상태

### 1.1 패키지 설치 여부

| 패키지 | 버전 (pyproject.toml) | 상태 |
|--------|----------------------|------|
| `drf-spectacular` | `^0.29.0` | ✅ 설치 (poetry.lock 확인) |
| `drf-spectacular-sidecar` | `^2026.4.14` | ✅ 설치 (Swagger/ReDoc 정적 자산) |
| `drf-yasg` | 없음 | ❌ 미사용 |

### 1.2 설정 (config/settings.py)

- **INSTALLED_APPS** (L212-213): `drf_spectacular`, `drf_spectacular_sidecar` 등록됨
- **REST_FRAMEWORK** (L370): `'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'`
- **SPECTACULAR_SETTINGS** (L377-425):
  - `TITLE`: "Stock-Vis Market Pulse v2 API" (※ Market Pulse 중심으로 명명 — 전사 API 명명 아님)
  - `VERSION`: 2.0
  - `SCHEMA_PATH_PREFIX`: `r'/api/v[12]'` → v1·v2 모두 스키마 포함
  - `SWAGGER_UI_DIST` / `REDOC_DIST`: `'SIDECAR'` (오프라인 자산)
  - `ENUM_NAME_OVERRIDES`: enum 충돌 4건 수동 해결 (ThesisPremiseCategory, NewsCategory, SavedPathStatus, ThesisStatus)
  - **`DISABLE_ERRORS_AND_WARNINGS': True`** ← ⚠️ **주목**: 스키마 생성 경고/에러를 전부 숨김. 부정확한 fallback이 조용히 통과되는 구조

### 1.3 OpenAPI / Swagger 자동 생성 가능 여부

✅ **가능** — config/urls.py L61-72에 3개 엔드포인트 마운트:

| 경로 | 뷰 | 용도 |
|------|----|----|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 스펙 (YAML/JSON) |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc |

### 1.4 현재 문서 품질의 한계 (settings.py 주석 L393-396 자인)

> "핵심 영역(marketpulse, chainsight, api_request admin)은 명시적 @extend_schema로 정상 처리됨. 나머지 v1 endpoint는 schema에서 graceful fallback (string body)로 노출."

즉, 스키마는 **생성되지만** 대부분 v1 엔드포인트의 request/response body가 `string`으로 추정되어 **계약 문서로서 부정확**합니다.

---

## 2. 엔드포인트 목록 (앱별)

> 집계 기준: `urls.py`의 `path()` 패턴 수. ViewSet은 router 자동 생성 라우트 + `@action`을 별도 표기.
> 디렉토리는 모노레포 구조(`packages/shared/`, `apps/`, `services/`) — CLAUDE.md의 평면 앱명과 매핑.

| 앱 (URL prefix) | 소스 위치 | URL 패턴 수 | `@extend_schema` 적용 | 커버리지 |
|-----------------|----------|:----------:|:---------------------:|:--------:|
| **stocks** (`/api/v1/stocks/`) | `packages/shared/stocks/` | **39** (8개 view 모듈) | 0 | 🔴 0% |
| **users** (`/api/v1/users/`) | `packages/shared/users/` | **35** | 2 | 🔴 ~6% |
| **news** (`/api/v1/news/`) | `services/news/api/` | ReadOnlyModelViewSet 1개 + **`@action` 30개** | 2 | 🔴 ~7% |
| **macro** (`/api/v1/macro/`) | `apps/market_pulse/` (v1 호환) | **10** | 0 | 🔴 0% |
| **macro v2** (`/api/v2/market-pulse/`) | `apps/market_pulse/api/` | **5** | 5 | 🟢 100% |
| **rag_analysis** (`/api/v1/rag/`) | `services/rag_analysis/` | **15** | 2 | 🔴 ~13% |
| **serverless** (`/api/v1/serverless/`) | `services/serverless/` | **64** | 6 | 🔴 ~9% |
| **thesis** (`/api/v1/thesis/`) | `thesis/` | **8** + ModelViewSet 3개 (+ `@action` 2) | 0 | 🔴 0% |
| **validation** (`/api/v1/validation/`) | `services/validation/api/` | **6** (APIView) | 0 | 🔴 0% |
| **chainsight** (`/api/v1/chainsight/`) | `apps/chain_sight/api/` | **7** + WatchlistViewSet (`@action` 5) | 7 | 🟢 ~높음 |
| **sec_pipeline** (`/api/v1/sec-pipeline/`) | `services/sec_pipeline/` | **2** (APIView 1 + func 1) | 0 | 🔴 0% |
| *(참고)* api_request admin | `packages/shared/api_request/` | (Provider Admin) | 5 | 🟢 |
| *(참고)* portfolio API | `apps/portfolio/api/` | (Coach DRF) | 6 | 🟢 |
| *(참고)* iron_trading | `integrations/iron_trading/` | read-only 외부 봇 | 0 | 🔴 |

**합계(요청 10개 앱 기준)**: 약 **191개 URL 패턴** + ViewSet 자동 라우트
(stocks 39 + users 35 + news 30 + macro 10+5 + rag 15 + serverless 64 + thesis 8 + validation 6 + chainsight 7 + sec 2)

### 2.1 앱별 엔드포인트 상세

#### stocks (39) — `packages/shared/stocks/urls.py`
- 페이지 뷰: dashboard, stock_detail, search (3)
- 차트/탭 데이터: chart, overview, balance-sheet, income-statement, cashflow (5)
- 동기화: sync (1)
- MVP: stocks, stock-detail, rag-context, sectors (4)
- 기술지표: indicators, signal, compare (3)
- 검색: symbols, validate, popular (3)
- Market Movers: 1
- Fundamentals: key-metrics, ratios, dcf, rating, all (5)
- Screener: screener, large-cap, high-dividend, sector, low-beta, exchange (6)
- Quotes: index, symbol, batch, major-indices, sector-performance (5)
- EOD Dashboard: dashboard, signal-detail, pipeline-status (3)

#### users (35) — `packages/shared/users/urls.py`
- JWT 인증: signup, login, logout, refresh, verify, change-password, profile (7)
- 세션 인증(레거시): me, users, public_user, change_password, login, logout (6)
- 즐겨찾기: list, add, remove (3)
- 포트폴리오: list, summary, table, refresh, detail, quick-update, by-symbol, symbol-refresh, status (9)
- 관심사: list, detail (2)
- Watchlist: list, detail, add-stock, bulk-add, bulk-remove, stocks, item-update, item-remove (8)

#### news — `services/news/api/views.py` `NewsViewSet(ReadOnlyModelViewSet)`
- 단일 라우터(root 등록) + **`@action` 30개** (stock, all, daily-keywords, keyword-detail, news-events, impact-map 등)
- 실질 엔드포인트 = 30+ (list/retrieve 기본 + custom action)

#### macro (10 v1 + 5 v2)
- v1(`apps/market_pulse/urls.py`): pulse, fear-greed, interest-rates, inflation, global-markets, calendar, vix, sectors, sync, sync-status (10)
- v2(`apps/market_pulse/api/urls.py`): overview, cards/{id}/detail, news/refresh, i18n, health (5) — **전부 @extend_schema 적용**

#### rag_analysis (15) — `services/rag_analysis/urls.py`
- DataBasket: list-create, detail, add-item, add-stock-data, remove-item, clear (6)
- AnalysisSession: list-create, detail, messages, chat-stream(SSE) (4)
- Monitoring: usage, cost, cache, history, pricing (5)

#### serverless (64) — `services/serverless/urls.py`
- Admin Dashboard (12): overview, stocks, screener, market-pulse, news, system, tasks, actions, action-status, news-categories(+detail), sector-options
- Market Movers (4), Keywords (4), Breadth (3), Heatmap (3)
- Presets (7), Filters (1), Advanced Screener (1)
- Alerts (6), Investment Thesis (4)
- Chain Sight 레거시: ETF (9), LLM-relations (4), Institutional (3), Regulatory/Patent (2)
- Health (1)

#### thesis (8 + ViewSet 3) — `thesis/urls.py`
- Conversation: start, respond, news-issues, suggest (4)
- Monitoring: dashboard, indicator-readings (2)
- Alerts: list, read (2)
- ModelViewSet 3종: `ThesisViewSet`(+@action 2), `ThesisPremiseViewSet`(nested), `ThesisIndicatorViewSet`(nested)

#### validation (6) — `services/validation/api/urls.py` (전부 `APIView`)
- {symbol}/summary, metrics, leader-comparison, presets, peer-preference, llm-filter

#### chainsight (7 + WatchlistViewSet) — `apps/chain_sight/api/urls.py`
- seeds, sector-graph, signals, trace, neighbors, graph, suggestions (7)
- `WatchlistViewSet`(@action 5)

#### sec_pipeline (2) — `services/sec_pipeline/urls.py`
- admin/dashboard (func view), filing/{symbol} (`FilingDataView` APIView)

---

## 3. 커버리지 보강 작업 목록

> ⚠️ "도입"은 이미 완료. 실제 필요 작업은 **부정확한 fallback 스키마 → 명시적 `@extend_schema`로 정확화**.

### 3.1 인프라 (이미 완료 — 추가 작업 불필요)
- [x] `drf-spectacular` + sidecar 설치
- [x] INSTALLED_APPS 등록
- [x] schema/swagger/redoc URL 마운트
- [x] ENUM_NAME_OVERRIDES 충돌 해결
- [ ] *(선택)* `TITLE`을 "Market Pulse v2" → 전사 API 명칭으로 변경 검토
- [ ] *(선택)* `DISABLE_ERRORS_AND_WARNINGS: True` → 보강 작업 중에는 `False`로 두어 fallback 경고 가시화 권장

### 3.2 `@extend_schema` 보강 범위 (우선순위)

| 우선순위 | 대상 앱 | 미적용 추정 엔드포인트 | 근거 |
|:------:|--------|:--------------------:|------|
| 🥇 P1 | **stocks** | ~39 | 프론트 핵심 소비, 0% 커버리지 |
| 🥇 P1 | **users** | ~33 | 인증/포트폴리오 계약, 보안 민감 |
| 🥈 P2 | **serverless** | ~58 | 최대 표면적(64), Admin+Chain Sight 혼재 |
| 🥈 P2 | **news** | ~28 | `@action` 30개 중 2개만 |
| 🥉 P3 | **rag_analysis** | ~13 | SSE 스트림 등 비표준 응답 명시 필요 |
| 🥉 P3 | **thesis** | ~10 | ViewSet 3종 + nested |
| 🥉 P3 | **validation** | 6 | APIView 6, 소규모 |
| 🥉 P3 | **macro v1** | 10 | v2는 완료, v1 미적용 |
| ✅ 완료 | macro v2, chainsight, portfolio, api_request | — | 이미 적용 |
| ⏭ 보류 | sec_pipeline (2), iron_trading | — | 표면적 작음 / 외부 read-only |

### 3.3 데코레이터 작업 패턴 (참고)

```python
# APIView (stocks/users/validation 등)
@extend_schema(
    responses={200: SomeSerializer},
    parameters=[OpenApiParameter("symbol", str, OpenApiParameter.PATH)],
    tags=["Stocks"],
)
def get(self, request, symbol): ...

# ViewSet @action (news/thesis/chainsight)
@extend_schema(responses={200: NewsArticleSerializer(many=True)})
@action(detail=False, methods=["get"])
def daily_keywords(self, request): ...
```

> 주의: 다수 v1 view가 **Serializer 없이 dict를 직접 Response()** 하는 패턴으로 추정 →
> 정확한 스키마를 위해 `@extend_schema(responses=inline_serializer(...))` 또는 응답용 Serializer 신설 필요.
> 이 부분이 작업량의 대부분을 차지함 (단순 데코레이터 추가가 아니라 **응답 계약 정의** 작업).

### 3.4 예상 작업량 (개략)

| 구간 | 대상 | 추정 |
|------|------|-----|
| P1 (stocks+users) | ~72 엔드포인트 | 응답 Serializer 정의 동반 시 **3~5일** |
| P2 (serverless+news) | ~86 엔드포인트 | **4~6일** (레거시·func view 혼재로 변동 큼) |
| P3 (rag/thesis/validation/macro v1) | ~39 엔드포인트 | **2~3일** |
| **합계** | ~197 엔드포인트 | **약 9~14일** (1인 기준, 응답 계약 정의 포함) |

> 단순 태그/요약만 다는 경량 작업이면 **3~4일**로 단축 가능하나, 계약 문서로서 가치(request/response body 정확성)를 확보하려면 Serializer 정의가 병목.

---

## 4. 권고 사항

1. **인프라 재구축 불필요** — drf-spectacular 운영 중. "도입"이 아닌 **점진적 커버리지 보강**으로 과제 재정의.
2. **`TITLE` 정정** — "Market Pulse v2 API"는 전사 스키마 명칭으로 부적절. 전체 API를 대표하도록 변경 검토.
3. **`DISABLE_ERRORS_AND_WARNINGS` 임시 해제** — 보강 작업 시 fallback 경고를 가시화해 누락 엔드포인트 식별.
4. **응답 Serializer 정의가 진짜 비용** — dict 직접 반환 view가 다수라, 데코레이터보다 응답 계약 정의가 작업량의 핵심.
5. **P1(stocks/users)부터** — 프론트 소비량·보안 민감도가 가장 높은 영역 우선.

---

*감사 종료. 본 보고서는 읽기 전용 — 코드/설정 변경 없음.*
