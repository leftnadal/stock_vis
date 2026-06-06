# API 문서 감사 보고서

> 생성일: 2026-06-06 (야간 자동 시스템 / 읽기 전용)
> 대상: Stock-Vis Backend (Django REST Framework)
> 범위: 전체 `urls.py` 라우팅 + 문서화 도구 설치/설정 상태

---

## 현재 상태

### 결론 (1줄)

**drf-spectacular가 이미 설치·설정·운영 중이다.** "도입"이 아니라 **"커버리지 확대(@extend_schema 점진 적용)"**가 실제 과제다.

### 문서화 도구 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | ✅ 설치 (`^0.29.0`) | `pyproject.toml` + `poetry.lock` |
| `drf-spectacular-sidecar` | ✅ 설치 (`^2026.4.14`) | Swagger/ReDoc 정적 자산 번들 |
| `drf-yasg` | ❌ 미사용 | (spectacular로 단일화) |
| INSTALLED_APPS 등록 | ✅ | `config/settings.py:212-213` |
| `DEFAULT_SCHEMA_CLASS` | ✅ `drf_spectacular.openapi.AutoSchema` | `config/settings.py:370` |

### OpenAPI 스펙 자동 생성 가능 여부 — ✅ 가능 (운영 중)

`config/urls.py:62-72`에 3개 엔드포인트가 이미 노출되어 있다:

| 경로 | 역할 |
|------|------|
| `/api/v2/schema/` | OpenAPI 3 스펙 (YAML/JSON) |
| `/api/v2/swagger/` | Swagger UI |
| `/api/v2/redoc/` | ReDoc |

**SPECTACULAR_SETTINGS 핵심** (`config/settings.py:377-`):
- `TITLE`: "Stock-Vis Market Pulse v2 API"
- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` → **`/api/v1/*` + `/api/v2/*` 전 경로가 스펙 대상**
- `DISABLE_ERRORS_AND_WARNINGS = True` → 스키마 생성 경고를 의도적으로 억제
- `SWAGGER_UI_DIST / REDOC_DIST = 'SIDECAR'` → 오프라인 정적 자산
- `ENUM_NAME_OVERRIDES` → thesis/news/chainsight enum collision 수동 해결

### 핵심 갭 (도구는 있으나 품질이 부분적)

설정 주석(`settings.py:393-396`)이 현 상태를 정확히 자백한다:

> "핵심 영역(marketpulse, chainsight, api_request admin)은 명시적 @extend_schema로 정상 처리됨. 나머지 v1 endpoint는 schema에서 **graceful fallback (string body)**로 노출. 정확한 schema가 필요한 view만 점진적으로 @extend_schema(responses=...) 추가."

→ 즉 스펙은 **전 경로가 나오지만**, `@extend_schema`가 없는 v1 뷰는 요청/응답 본문이 `string`으로 뭉개져 **문서 가치가 낮다**. `DISABLE_ERRORS_AND_WARNINGS=True`가 이 부정확성을 침묵시키고 있어 **품질 저하가 보이지 않는 위험**이 있다.

### @extend_schema 적용 현황 (실제 코드 파일)

| 파일 | 등장 횟수(import 포함) | 비고 |
|------|------|------|
| `apps/chain_sight/api/views.py` | 8 | 핵심 영역 (정상) |
| `apps/portfolio/api/views.py` | 7 | coach E1~E6 |
| `services/serverless/views.py` | 7 | 부분 |
| `packages/shared/api_request/admin_views.py` | 6 | 핵심 영역 (정상) |
| `services/news/api/views.py` | 4 | 부분 (액션 30개 대비 낮음) |
| `apps/market_pulse/api/views/*` | 13 (5파일 합) | 핵심 영역 (정상) |
| `services/rag_analysis/views.py` | 3 | 부분 |
| `packages/shared/users/views.py` | 3 | 부분 |
| `packages/shared/stocks/views*.py` | **0** | ⚠️ 39 경로 전부 미적용 |
| `services/validation/api/views.py` | **0** | ⚠️ 미적용 |
| `services/sec_pipeline/views.py` | **0** | ⚠️ 미적용 |
| `integrations/iron_trading/views.py` | **0** | ⚠️ 미적용 |

---

## 엔드포인트 목록 (앱별 테이블)

> 집계 기준: `urls.py`에 등록된 **URL 패턴(path) 수**. ViewSet(DefaultRouter)은 자동 생성 라우트를 별도 추정으로 표기.

### 앱별 요약

| # | 앱 | 마운트 prefix | URL 패턴 수 | 스타일 | @extend_schema |
|---|-----|--------------|:---:|--------|:---:|
| 1 | **users** | `/api/v1/users/` | 35 | APIView | 부분 (3) |
| 2 | **stocks** | `/api/v1/stocks/` | 39 | APIView | ❌ 0 |
| 3 | **news** | `/api/v1/news/` | 2 + 30 액션 | ReadOnlyModelViewSet | 부분 (4) |
| 4 | **macro** (market_pulse v1) | `/api/v1/macro/` | 10 | APIView | ❌ 0 |
| 5 | **market_pulse v2** | `/api/v2/market-pulse/` | 5 | APIView | ✅ 13 |
| 6 | **rag_analysis** | `/api/v1/rag/` | 14 | APIView | 부분 (3) |
| 7 | **serverless** | `/api/v1/serverless/` | 64 | FBV + APIView | 부분 (7) |
| 8 | **thesis** | `/api/v1/thesis/` | 8 + ViewSet 3종 | ModelViewSet ×3 | ❌ 0 |
| 9 | **validation** | `/api/v1/validation/` | 6 | APIView | ❌ 0 |
| 10 | **chainsight** | `/api/v1/chainsight/` | 7 + WatchlistViewSet | ModelViewSet | ✅ 8 |
| 11 | **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | FBV + APIView | ❌ 0 |
| — | api_request (provider admin) | `/api/v1/` | 6 | FBV | ✅ 6 |
| — | iron_trading | `/api/v1/iron-trading/` | 2 (실 1) | APIView | ❌ 0 |
| — | portfolio (legacy) | `/api/` | 0 (빈 상태) | — | — |
| — | portfolio coach API | `/api/v1/coach/` | 6 | FBV | ✅ 7 |

**명시 URL 패턴 합계: 약 206개** (ViewSet 자동 생성 라우트 별도)

### 요청된 10개 앱 상세

#### 1. stocks (`/api/v1/stocks/`) — 39개
`packages/shared/stocks/urls.py` (뷰 9개 모듈 분리)
- 페이지/검색: dashboard, stock_detail, search (3)
- 탭 데이터 API: chart, overview, balance-sheet, income-statement, cashflow (5)
- 동기화: sync (1)
- MVP: stocks, stock detail, rag-context, sectors (4)
- 기술지표: indicators, signal, indicators/compare (3)
- 종목검색: search/symbols, validate, popular (3)
- Market Movers: market-movers (1)
- Fundamentals: key-metrics, ratios, dcf, rating, all (5)
- Screener: screener, large-cap, high-dividend, sector, low-beta, exchange (6)
- Quotes: index, symbol, batch, major-indices, sector-performance (5)
- EOD: dashboard, signal detail, pipeline/status (3)

#### 2. users (`/api/v1/users/`) — 35개
`packages/shared/users/urls.py`
- JWT: signup, login, logout, refresh, verify, change-password, profile (7)
- 세션 인증(레거시): me, users, public_user, change_password, login, logout (6)
- 즐겨찾기: list, add, remove (3)
- 포트폴리오: list, summary, table, refresh, detail, quick-update, by-symbol, refresh(symbol), status (9)
- 관심사: list, detail (2)
- Watchlist: list, detail, add-stock, bulk-add, bulk-remove, stocks, item-update, item-remove (8)

#### 3. news (`/api/v1/news/`) — ReadOnlyModelViewSet + 30 @action
`services/news/api/urls.py` — `DefaultRouter` + `NewsViewSet(ReadOnlyModelViewSet)`
- 기본 라우트: list, retrieve (2)
- `@action` 30개: stock, stock/sentiment, market, trending, all, sources, daily-keywords, daily-keywords/generate, keyword-detail, insights, news-events, news-events/impact-map, recommendations 외 17개
- ⚠️ **단일 앱 최대 액션 밀도** — 문서화 우선순위 높음

#### 4. macro (`/api/v1/macro/`) — 10개
`apps/market_pulse/urls.py` (v1 호환 진입점, namespace='macro' 보존)
- pulse, fear-greed, interest-rates, inflation, global-markets, calendar, vix, sectors, sync, sync/status

#### 5. rag_analysis (`/api/v1/rag/`) — 14개
`services/rag_analysis/urls.py`
- DataBasket: list-create, detail, add-item, add-stock-data, remove-item, clear (6)
- AnalysisSession: list-create, detail, messages, chat/stream(SSE) (4)
- Monitoring: usage, cost, cache, history, pricing (5) → 합 14 (DataBasket 6 + Session 4 + Monitoring 5 = 15 중 chat/stream 포함 정정: 실제 14)

#### 6. serverless (`/api/v1/serverless/`) — 64개 (최대)
`services/serverless/urls.py` (FBV 다수 + Admin APIView)
- Admin Dashboard: 12 / Market Movers: 4 / Keywords: 4 / Breadth: 3 / Heatmap: 3
- Presets: 7 / Filters: 1 / Advanced Screener: 1 / Alerts: 6 / Thesis: 4
- ETF Holdings: 6 / Themes: 3 / LLM Relations: 4 / Institutional: 3 / Regulatory+Patent: 2 / Health: 1
- ⚠️ legacy 제거 흔적(CS-0-0): Chain Sight Stock + Neo4j Graph 8개 URL 제거됨

#### 7. thesis (`/api/v1/thesis/`) — 8 패턴 + ViewSet 3종
`thesis/urls.py` (`DefaultRouter` nested)
- 명시 path: conversation/start, respond, news-issues, suggest, dashboard, readings, alerts, alerts/read (8)
- `ThesisViewSet(ModelViewSet)` + @action 2개 (close, auto)
- `ThesisPremiseViewSet(ModelViewSet)` (nested under `<thesis_id>/premises/`)
- `ThesisIndicatorViewSet(ModelViewSet)` (nested under `<thesis_id>/indicators/`)
- → operation 단위 환산 시 약 26~28개

#### 8. validation (`/api/v1/validation/`) — 6개
`services/validation/api/urls.py` (전부 `<symbol>` 기반 APIView)
- summary, metrics, leader-comparison, presets, peer-preference, llm-filter

#### 9. chainsight (`/api/v1/chainsight/`) — 7 패턴 + WatchlistViewSet
`apps/chain_sight/api/urls.py`
- 명시 path: seeds, sector graph, signals, trace, neighbors, graph, suggestions (7)
- `WatchlistViewSet(ModelViewSet)` + @action 5개 (archive, resolve, recheck, expand, alternatives)
- ✅ @extend_schema 적용된 핵심 영역

#### 10. sec_pipeline (`/api/v1/sec-pipeline/`) — 2개
`services/sec_pipeline/urls.py`
- admin/dashboard (FBV), filing/`<symbol>` (APIView)

---

## 도입 작업 목록

> ⚠️ **재확인**: "도입"이 아니라 **"커버리지 확대"**다. drf-spectacular는 설치·설정 완료, Swagger/ReDoc 운영 중.

### 작업 1 — 설치/설정 (완료, 작업 불필요)
- [x] drf-spectacular + sidecar 설치
- [x] INSTALLED_APPS / DEFAULT_SCHEMA_CLASS 등록
- [x] schema/swagger/redoc URL 노출
- [x] SCHEMA_PATH_PREFIX로 v1/v2 전 경로 포함

### 작업 2 — @extend_schema 커버리지 확대 (실제 과제)

graceful fallback(`string` body)로 뭉개진 v1 뷰에 `@extend_schema(request=, responses=, parameters=)` 추가.

| 우선순위 | 앱 | 미적용 규모 | 권장 작업량 | 사유 |
|:---:|-----|:---:|:---:|------|
| **P1** | stocks | 39 경로 (0 적용) | 2~3일 | 외부/프론트 사용 빈도 최상, serializer 다수 |
| **P1** | news | 30 액션 (4 적용) | 2일 | 액션 밀도 최고, FE 의존 큼 |
| **P2** | thesis | ViewSet 3종 (0 적용) | 1.5일 | ModelViewSet → serializer 재사용 용이 |
| **P2** | rag_analysis | 14 (3 적용) | 1일 | SSE(chat/stream) 스키마 수동 명시 필요 |
| **P2** | serverless | 64 (7 적용) | 3~4일 | FBV 다수 → `@extend_schema` FBV 데코레이션 필요, 규모 큼 |
| **P3** | macro v1 | 10 (0) | 0.5일 | v2로 대체 진행 중 → 투자 가치 낮음 |
| **P3** | validation | 6 (0) | 0.5일 | symbol 파라미터 단순 |
| **P3** | users | 35 (3) | 1.5일 | JWT 뷰는 simplejwt 기본 스키마 활용 가능 |
| **P3** | sec_pipeline | 2 (0) | 0.2일 | 소규모 |

**총 추정 작업량: 약 13~16일** (1인 기준, 점진 적용)

### 작업 3 — 품질 가드 (권장 신규)

1. **`DISABLE_ERRORS_AND_WARNINGS=True` 재검토**
   - 현재 스키마 생성 경고를 전면 억제 → 부정확한 fallback이 보이지 않음
   - 권장: CI에서만 `--fail-on-warn`으로 `manage.py spectacular --validate` 실행해 신규 미적용 뷰 감지

2. **CI 스펙 검증 추가**
   - `python manage.py spectacular --file schema.yml --validate` → 스펙 깨짐 조기 탐지

3. **TITLE/DESCRIPTION 갱신**
   - 현재 "Market Pulse v2 API"로 한정 표기 → 실제는 전 앱 포함. 전체 플랫폼 명칭으로 수정 권장

### 권장 진행 순서
1. (즉시) CI 검증 + DISABLE_ERRORS_AND_WARNINGS 재검토 — 0.5일
2. (P1) stocks + news — FE 의존도 최상
3. (P2) thesis / rag / serverless
4. (P3) 나머지 + 메타데이터 정리

---

## 부록: 발견 메모

- **구조 재편 반영**: CLAUDE.md의 앱 경로(`stocks/`, `users/` 등)와 실제 디렉터리(`packages/shared/`, `apps/`, `services/`, `integrations/`)가 불일치 → CLAUDE.md 아키텍처 표 갱신 권장(문서 부채)
- **legacy 제거 흔적**: serverless에 Chain Sight Stock + Neo4j Graph 8개 URL 제거(CS-0-0), ETF Holdings는 `LEGACY_KEEP_UNTIL_DC2` 표기 → chainsight 앱으로 재구축 진행 중
- **portfolio (legacy) urls.py 빈 상태**: `#65` 후속으로 include 자체 제거 검토 대상 → 데드 라우팅
- **iron_trading**: trailing-slash 중복(2 path, 실 1 endpoint) — read-only 외부 봇용
