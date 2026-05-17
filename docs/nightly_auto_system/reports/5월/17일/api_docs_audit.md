# API 문서 감사 보고서

> 작성일: 2026-05-17 (야간 자동 감사 시스템)
> 모드: **읽기 전용** — 코드/설정 변경 없음
> 대상: `/Users/byeongjinjeong/Desktop/stock_vis`

---

## 현재 상태

### TL;DR

| 항목 | 상태 |
|------|------|
| **drf-spectacular 설치** | ✅ `^0.29.0` (pyproject.toml line 38) |
| **drf-spectacular-sidecar** | ✅ `^2026.4.14` (line 39) — Swagger UI/ReDoc 정적 자산 |
| **drf-yasg** | ❌ 미사용 (의도된 선택, drf-spectacular와 충돌하므로 도입 금지) |
| **`INSTALLED_APPS` 등록** | ✅ `config/settings.py:205-206` |
| **`DEFAULT_SCHEMA_CLASS`** | ✅ `drf_spectacular.openapi.AutoSchema` (line 363) |
| **`SPECTACULAR_SETTINGS` 정의** | ✅ line 370-418 |
| **Schema/Swagger/ReDoc URL 노출** | ✅ `config/urls.py:57-68` |
| **자동 스펙 생성** | ✅ **즉시 가능** (`/api/v2/schema/`, `/api/v2/swagger/`, `/api/v2/redoc/`) |
| **`@extend_schema` 명시적 데코레이션** | 🟡 31회 (12개 파일) — 부분 적용 |
| **`DISABLE_ERRORS_AND_WARNINGS`** | ⚠️ `True` (line 390) — 미데코레이션 view는 graceful fallback (string body)로 노출 |

### 핵심 사실

- **이미 운영 중**: Market Pulse v2(PR-I/J)를 위해 drf-spectacular가 도입 완료된 상태. `TITLE: 'Stock-Vis Market Pulse v2 API'`, `VERSION: '2.0'`로 설정되어 있음.
- **현재 SCHEMA_PATH_PREFIX**: `r'/api/v[12]'` — v1 + v2 모두 스펙에 포함됨.
- **현재 한계**: `DISABLE_ERRORS_AND_WARNINGS = True`로 설정되어 있어, `@extend_schema`가 없는 view는 "unable to guess serializer" 경고를 silently 무시하고 string body로 fallback. 결과적으로 **스펙은 생성되지만 타입 정확도가 낮음**.
- **부분 적용 영역** (이미 `@extend_schema` 사용 중): marketpulse, chainsight(api), api_request(admin), serverless, rag_analysis, users, news.
- **미적용 영역** (스펙 fallback만 제공): stocks, macro, thesis, validation, sec_pipeline, portfolio, config.

### Enum Collision 처리

`config/settings.py:394-417`에 `ENUM_NAME_OVERRIDES`로 4개 collision 처리 완료:
- `ThesisPremiseCategoryEnum` (6 choices)
- `NewsCategoryEnum` (6 choices)
- `SavedPathStatusEnum` (4 choices)
- `ThesisStatusEnum` (4 choices)

별도 모듈 `config/spectacular_enums.py`도 존재 (dotted-path target용).

---

## 엔드포인트 목록 (앱별 테이블)

> 집계 방법: 각 앱 `urls.py`의 `path(...)` 항목 수 + DRF Router 자동 생성 endpoint(ModelViewSet=7개, ReadOnlyModelViewSet=2개, 추가 `@action` 별도) 추정.

### 요약 테이블

| 앱 | 마운트 prefix | urls.py 파일 | 명시 path 수 | Router 자동 endpoint | ViewSet/APIView 수 | `@extend_schema` 적용 | 비고 |
|----|---------------|--------------|-------------|---------------------|-------------------|----------------------|------|
| **stocks** | `/api/v1/stocks/` | `stocks/urls.py` | 39 | 0 | 28 (9 views_*.py 파일) | ❌ 0 | 2개는 HTML page (DashboardView, StockDetailView) |
| **users** | `/api/v1/users/` | `users/urls.py` | 35 | 0 | 28 (views.py 22 + jwt_views.py 6) | 🟡 2 | JWT 인증 7 + 사용자/포트폴리오/Watchlist |
| **news** | `/api/v1/news/` | `news/api/urls.py` | 1 (router) | ~2-5 | 1 (`NewsViewSet`, ReadOnly) | 🟡 2 | ReadOnly + `@action` 가능 |
| **macro** | `/api/v1/macro/` | `macro/urls.py` | 10 | 0 | 10 | ❌ 0 | Market Pulse v1 (legacy) |
| **rag_analysis** | `/api/v1/rag/` | `rag_analysis/urls.py` | 15 | 0 | 15 | 🟡 2 | DataBasket + Session + Monitoring |
| **serverless** | `/api/v1/serverless/` | `serverless/urls.py` | ~64 | 0 | 12 admin View + 80+ FBV | 🟡 6 | FBV(@api_view) 대량 — Market Movers, Screener, Chain Sight v1, 알림 |
| **thesis** | `/api/v1/thesis/` | `thesis/urls.py` | 8 explicit + 3 router | ~21 (3 ModelViewSet) | 11 (ViewSet 3 + View 8) | ❌ 0 | Nested router (premises, indicators) |
| **validation** | `/api/v1/validation/` | `validation/api/urls.py` | 6 | 0 | 6 | ❌ 0 | 1차 검증 (Peer/Preset/LLM filter) |
| **chainsight** | `/api/v1/chainsight/` | `chainsight/api/urls.py` | 7 explicit + 1 router | ~7 (1 ModelViewSet) | 8 (View 7 + ViewSet 1) | ✅ 7 | Chain Sight v2 — 가장 잘 문서화됨 |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | `sec_pipeline/urls.py` | 2 | 0 | 2 (FBV 1 + APIView 1) | ❌ 0 | SEC 10-K dashboard + filing detail |
| **api_request** | `/api/v1/` | `api_request/urls.py` | 6 | 0 | 6 (admin APIView) | 🟡 5 | Provider Admin (IsAdminUser) |
| **portfolio** | `/api/coach/` | `portfolio/urls.py` | 5 | 0 | 5 (FBV) | ❌ 0 | Portfolio Coach (E1~E6) |
| **marketpulse** | `/api/v2/market-pulse/` | `marketpulse/api/urls.py` | 5 | 0 | 5 | ✅ 5 | v2 — drf-spectacular 도입 동기 |
| **config (root)** | `/` | `config/urls.py` | 2 (api-root, health) + admin | 0 | 2 (FBV) | ❌ 0 | 헬스 체크 |

### 총계 (추정)

| 항목 | 수치 |
|------|------|
| 총 URL path 수 (router 자동 endpoint 포함) | **~225~245** |
| 총 view class / FBV 수 | **~140~155** |
| `@extend_schema` 적용 view 수 | **~29~31** (전체의 ~20%) |
| 미적용 view 수 | **~110~125** (전체의 ~80%) |

### 앱별 view 상세

#### stocks (28 views, 9 파일)

```
stocks/views.py:               13 (Dashboard*, StockDetail*, StockSearch, Chart, Overview, Balance, Income, Cashflow, Sync 등)
stocks/views_mvp.py:           4  (MVP List/Detail/RAG/Sectors)
stocks/views_fundamentals.py:  5  (KeyMetrics, Ratios, DCF, Rating, AllFundamentals)
stocks/views_indicators.py:    3  (TechnicalIndicator, IndicatorSignal, IndicatorComparison)
stocks/views_search.py:        3  (SymbolSearch, SymbolValidate, PopularSymbols)
stocks/views_market_movers.py: 1  (MarketMovers)
stocks/views_screener.py:      6  (Screener, LargeCap, HighDividend, Sector, LowBeta, Exchange)
stocks/views_exchange.py:      5  (IndexQuotes, StockQuote, BatchQuotes, MajorIndices, SectorPerformance)
stocks/views_eod.py:           3  (EODDashboard, EODSignalDetail, EODPipelineStatus)
```

#### users (28 views, 2 파일)

```
users/views.py:      22 (Me, Users, PublicUser, Portfolio*, Watchlist*, UserInterest*, AddFavorite 등)
users/jwt_views.py:  6  (CustomTokenObtainPair, JWTSignUp, JWTLogout, JWTVerify, ChangePasswordJWT, ProfileUpdate)
```

#### serverless (12 admin APIView + 다수 FBV)

```
serverless/views_admin.py:  12  (AdminOverview, AdminStocks, AdminScreener, AdminMarketPulse,
                                 AdminNews, AdminSystem, AdminTaskLogs, AdminAction, AdminTaskStatus,
                                 AdminNewsCategory*, AdminNewsSectorOptions)
serverless/views.py:        ~80개의 @api_view FBV (Market Movers, Breadth, Heatmap, Presets, Alerts,
                                                    Thesis, ETF, LLM Relations, Institutional, Patent)
```

#### thesis (11 views, 3 파일)

```
thesis/views/thesis_views.py:      3 (ThesisViewSet, ThesisPremiseViewSet, ThesisIndicatorViewSet)
thesis/views/conversation_views.py: 4 (ConversationStart, ConversationRespond, NewsIssues, SuggestTheses)
thesis/views/monitoring_views.py:  4 (Dashboard, AlertList, AlertRead, IndicatorReadings)
```

#### validation (6 views)
`ValidationSummary, ValidationMetrics, LeaderComparison, PresetList, PeerPreference, LLMPeerFilter`

#### chainsight (8 views, 가장 잘 문서화됨)
`ChainSightGraph, ChainSightSuggestion, ChainSightTrace, SeedList, SectorGraph, NeighborGraph, SignalFeed, WatchlistViewSet`

#### macro (10 views)
`MarketPulse, FearGreedIndex, InterestRates, InflationDashboard, GlobalMarkets, EconomicCalendar, VIX, SectorPerformance, DataSync, SyncStatus`

#### rag_analysis (15 views)
`DataBasket* (6), AnalysisSession* (4), Monitoring* (5)`

#### marketpulse v2 (5 views, 모두 문서화됨)
`OverviewView, CardDetailView, NewsRefreshView, I18nView, HealthView`

#### sec_pipeline (2 views)
`sec_pipeline_dashboard (FBV), FilingDataView`

#### api_request (6 admin views, 5개 문서화)
`ProviderStatus, RateLimitStatus, CacheManagement, ProviderTest, ProviderConfig, HealthCheck`

#### portfolio (5 FBV)
`coach_e1_garp, coach_e5_adjustment, coach_e2_diagnostic_card, coach_e6_comparison, coach_e3_metric_comment`

---

## 도입 작업 목록

### 좋은 소식: 인프라는 이미 100% 준비됨

drf-spectacular는 이미 설치/설정/URL 노출까지 완료. **추가 설치/설정 0건**. 남은 작업은 **순수 데코레이션 + 시리얼라이저 정의 + 검증**.

### Phase 0 — 현 상태 ground truth 확보 (1~2시간)

| # | 작업 | 산출물 |
|---|------|--------|
| 0-1 | `python manage.py spectacular --file /tmp/openapi.yaml --validate --fail-on-warn` 실행 (현재는 `DISABLE_ERRORS_AND_WARNINGS=True`이므로 임시로 끄고 실측) | warning/error 카운트, fallback view 목록 |
| 0-2 | `/api/v2/schema/`, `/api/v2/swagger/`, `/api/v2/redoc/` 브라우저 접속 → 어떤 view가 string body fallback인지 시각적으로 확인 | 스크린샷 + view 식별 |
| 0-3 | 응답 envelope 표준(`config/exception_handler.py` + `config/serializers.py.ErrorEnvelopeSerializer`)이 spec에 정상 노출되는지 확인 | 결과 메모 |

### Phase 1 — 핵심 영역 우선 (high-traffic, public API)

> 목표: **사용자/프론트엔드가 가장 자주 부딪히는 view부터**.
> `@extend_schema(request=..., responses=..., parameters=..., tags=...)` + 필요 시 ad-hoc `inline_serializer` 또는 dedicated serializer 추가.

| 우선순위 | 앱 | view 수 | 예상 시간 | 비고 |
|---------|------|---------|----------|------|
| 🔴 P1 | **stocks** | 28 | 6~8시간 | 최대 endpoint 수. response 구조 매우 다양(차트, OHLCV, 재무, screener) → serializer 분리 필요 |
| 🔴 P1 | **users** (JWT 우선) | 6 (jwt_views) | 1~2시간 | 인증은 OpenAPI security scheme + 명시 필수 |
| 🔴 P1 | **thesis** | 11 | 3~4시간 | ModelViewSet 3개 + custom action 다수 (대시보드, 지표 readings) |
| 🟡 P2 | **users** (나머지) | 22 | 4~5시간 | Watchlist/Portfolio (CRUD ModelSerializer 활용 가능) |
| 🟡 P2 | **validation** | 6 | 1~2시간 | 단순 query → response 매핑. peer preset/LLM filter 위주 |
| 🟡 P2 | **macro** | 10 | 2~3시간 | Market Pulse v1 (v2와 응답 키 차이 명시 필요) |

**Phase 1 소계: ~17~24시간 (대략 2~3일)**

### Phase 2 — 보조 영역

| 우선순위 | 앱 | view 수 | 예상 시간 | 비고 |
|---------|------|---------|----------|------|
| 🟢 P3 | **rag_analysis** | 15 (이미 2개 적용) | 3~4시간 | SSE stream view (`ChatStreamView`)는 별도 처리 (`@extend_schema(responses=OpenApiTypes.STR)`) |
| 🟢 P3 | **serverless** (admin) | 12 (관리자 전용) | 2~3시간 | IsAdminUser → security 명시 |
| 🟢 P3 | **serverless** (FBV) | ~80 (6개 적용) | 8~12시간 | 가장 노동집약적. `@api_view` 데코 위에 `@extend_schema` 추가. 일부는 LEGACY_KEEP_UNTIL_DC2 (제거 예정) → 제외 가능 |
| 🟢 P3 | **chainsight** | 8 (7개 적용) | 0.5시간 | `WatchlistViewSet` 1개만 추가 작업 |
| 🟢 P3 | **news** ViewSet | 1 | 1시간 | `@action` 메서드까지 |
| 🟢 P3 | **marketpulse v2** | 5 (모두 적용) | 0시간 | 완료 |
| 🟢 P3 | **sec_pipeline** | 2 | 1시간 | dashboard는 admin |
| 🟢 P3 | **portfolio** (Coach) | 5 FBV | 1~2시간 | E1~E6 응답 schema 명세화 |
| 🟢 P3 | **api_request** | 1 (HealthCheck만) | 0.5시간 | 5개는 적용 완료 |

**Phase 2 소계: ~17~24시간**

### Phase 3 — 마감 + 거버넌스 (4~6시간)

| # | 작업 | 산출물 |
|---|------|--------|
| 3-1 | `DISABLE_ERRORS_AND_WARNINGS = False`로 전환하고 `--fail-on-warn` 통과 | 클린 빌드 |
| 3-2 | OpenAPI security scheme 정의 (`SecurityScheme: bearerAuth`) + `@extend_schema(auth=[...])` 일관 적용 | JWT Bearer 명세 |
| 3-3 | 응답 envelope (`{detail, code?, errors?, status_code}`)을 `ErrorEnvelopeSerializer`로 모든 4xx/5xx에 명시 (`config/serializers.py:9` 이미 정의됨) | 표준화된 에러 응답 |
| 3-4 | `SCHEMA_PATH_PREFIX` 재검토 (현재 v1+v2 통합 → v1/v2 분리 spec도 고려) | 멀티 schema 라우팅 |
| 3-5 | CI에 `python manage.py spectacular --validate --fail-on-warn` step 추가 (qa-architect 협업) | regression 방지 |
| 3-6 | 프론트엔드 타입 생성 파이프라인 (`openapi-typescript`) 검토 — `contracts/shared-types.ts`와 동기화 정책 | 타입 단일 소스 |
| 3-7 | `README.md` / `sub_claude_md/api-endpoints.md`에 Swagger/ReDoc URL + 인증 방법 명시 | 개발자 가이드 |

### 예상 총 작업량 표

| 단계 | 작업량 | 누적 |
|------|--------|------|
| Phase 0 (ground truth) | 1~2시간 | 1~2시간 |
| Phase 1 (핵심 영역) | 17~24시간 | 18~26시간 |
| Phase 2 (보조 영역) | 17~24시간 | 35~50시간 |
| Phase 3 (마감/거버넌스) | 4~6시간 | **39~56시간** |

**= 1~1.5인주 (full-time equivalent)**, 또는 백엔드 엔지니어 1명이 partial하게 2~3주.

### 권장 도입 순서

```
0. spectacular CLI로 현 상태 측정 (1h)
   ↓
1. settings.py 손대지 않고 stocks/users(JWT)/thesis @extend_schema 적용 → P1
   ↓
2. /api/v2/swagger/ 사용자 시연 → 도입 가치 확인
   ↓
3. P2/P3 진행 (계약-주도 개발 문화 정착)
   ↓
4. DISABLE_ERRORS_AND_WARNINGS=False + CI gate
```

### 비용/리스크 메모

- **장점**: 인프라 비용 0(이미 설치됨), 신규 의존성 0, frontend 타입 생성 가능, contract 단일 소스.
- **리스크**:
  - `DISABLE_ERRORS_AND_WARNINGS=False`로 전환 시 즉시 빌드 깨질 가능성(약 80% view fallback 상태). → Phase 3까지 `True` 유지 필수.
  - SSE stream view(`rag_analysis.ChatStreamView`)는 일반 schema 표현이 어려움 → `OpenApiTypes.STR` + description 텍스트로 우회.
  - 일부 FBV(`serverless/views.py`)는 `request.GET` + dict 응답 패턴 → 시리얼라이저 부재로 inline 정의 비용 큼.
- **부채 연결**: `DECISIONS.md` 응답 envelope 표준화(`#14 P0, 2026-05-12`)와 동시 진행 시 시너지. KB `LESSON` 후보: "drf-spectacular 도입은 단계 분리 + `DISABLE_ERRORS_AND_WARNINGS` 가드 필수".

---

## 부록 — 명령 모음 (실행 시 참고)

```bash
# 현재 스펙 덤프 (warning 무시 모드 — 현재 settings)
python manage.py spectacular --file /tmp/openapi.yaml

# 엄격 모드 (Phase 3 검증용 — 지금은 깨짐)
python manage.py spectacular --file /tmp/openapi.yaml --validate --fail-on-warn

# Swagger UI / ReDoc
open http://localhost:8000/api/v2/swagger/
open http://localhost:8000/api/v2/redoc/

# 프론트엔드 타입 생성 (도입 후)
npx openapi-typescript /tmp/openapi.yaml -o frontend/src/types/openapi.ts
```

---

**감사 결론**: drf-spectacular 인프라는 완비됨. 코드 변경 없이 즉시 `/api/v2/swagger/`에 접속하면 모든 v1+v2 endpoint가 노출(부분적으로는 graceful fallback). 추가 가치는 view별 `@extend_schema` 데코레이션 + 시리얼라이저 정의에서 발생하며, **전체 약 1~1.5인주** 규모. 인프라 P1 우선순위로 진행 권장.
