# API 문서 감사 보고서

> 생성일: 2026-06-16 · 읽기 전용 감사 (코드 미변경)
> 대상: `config/urls.py` 마운트 기준 전체 백엔드 REST 엔드포인트

---

## 현재 상태

### 문서화 도구 설치 — ✅ 완료 (이미 도입됨)

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | ✅ 설치 | `pyproject.toml`: `drf-spectacular = "^0.29.0"` |
| `drf-spectacular-sidecar` | ✅ 설치 | `pyproject.toml`: `^2026.4.14` (실제 운영 `2026.5.1`) |
| `drf-yasg` | ❌ 미사용 | (spectacular로 단일화) |
| `DEFAULT_SCHEMA_CLASS` | ✅ 설정 | `settings.py:377` `drf_spectacular.openapi.AutoSchema` |
| `SPECTACULAR_SETTINGS` | ✅ 설정 | `settings.py:384~432` |

### Swagger / OpenAPI 자동 생성 — ✅ 가능 (운영 중)

`config/urls.py:62~72`에 3개 엔드포인트가 이미 마운트되어 있음:

| URL | 뷰 | 용도 |
|-----|----|----|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 스펙 (YAML) |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc |

**핵심 설정 (`settings.py`)**
- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` → `/api/v1/*`, `/api/v2/*` 모두 스펙에 포함
- `DISABLE_ERRORS_AND_WARNINGS = True` → 스키마 추론 실패(`unable to guess serializer`)를 **graceful fallback(string body)** 로 처리하여 노이즈 억제
- `COMPONENT_SPLIT_REQUEST = True`, `SWAGGER_UI_DIST = 'SIDECAR'` (오프라인 정적 자산)
- `ENUM_NAME_OVERRIDES` 4종 (thesis category/status, news category, savedpath status) — enum collision 해결

> **결론**: 문서화 도구는 "도입 필요"가 아니라 **이미 도입·운영 중**. 남은 과제는 *커버리지 확대* — `@extend_schema` 미적용 뷰가 스펙에서 빈약하게(타입 없는 string body) 노출되는 문제 해소.

---

## 엔드포인트 목록 (앱별 테이블)

> 카운트는 `urls.py`의 `path()` 패턴 기준. ViewSet은 라우터 자동 생성분을 별도 표기.
> `@extend_schema`는 해당 앱 뷰 코드의 데코레이터 적용 건수 (docs/settings 제외).

| 앱 | URL Prefix | 엔드포인트 수 | `@extend_schema` 적용 | 커버리지 |
|----|-----------|:---:|:---:|:---:|
| **stocks** | `/api/v1/stocks/` | 39 (HTML 페이지 2 포함) | 0 | 🔴 0% |
| **users** | `/api/v1/users/` | 35 | 2 | 🟡 ~6% |
| **news** | `/api/v1/news/` | 32 (ReadOnly ViewSet 2 + @action 30) | 2 | 🔴 ~6% |
| **macro** (market_pulse v1) | `/api/v1/macro/` | 10 | 0 | 🔴 0% |
| **market_pulse v2** | `/api/v2/market-pulse/` | 5 | 5 | 🟢 100% |
| **rag_analysis** | `/api/v1/rag/` | 15 | 2 | 🔴 ~13% |
| **serverless** | `/api/v1/serverless/` | 64 | 6 | 🔴 ~9% |
| **thesis** | `/api/v1/thesis/` | 8 명시 + ViewSet 3종(CRUD + @action 2) | 0 | 🔴 0% |
| **validation** | `/api/v1/validation/` | 6 | 0 | 🔴 0% |
| **chainsight** | `/api/v1/chainsight/` | 9 명시 + WatchlistViewSet(CRUD + @action 5) | 9 (views 7 + event_views 2) | 🟡 부분 |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | 0 | 🔴 0% |
| **iron_trading** | `/api/v1/iron-trading/` | 1 (path 2, 동일 뷰) | 0 | 🔴 0% |
| **api_request** (Provider Admin) | `/api/v1/` | 6 | 5 | 🟢 ~83% |
| **portfolio** (Coach) | `/api/v1/coach/` | 6 (e1~e6) | 6 | 🟢 100% |

**합계 (명시 path 기준)**: 약 **238개** REST 엔드포인트 (ViewSet 자동 생성분 별도)

### 앱별 상세

**stocks** (39) — 대시보드/상세는 HTML 페이지(`DashboardView`, `StockDetailView`), 나머지는 JSON API. 영역: chart/overview/balance-sheet/income/cashflow/sync, MVP(4), indicators(3), search(3), market-movers(1), fundamentals(5), screener(6), quotes(5), eod(3).

**users** (35) — JWT 인증(7), 세션 호환(7), favorites(3), portfolio(9), interests(2), watchlist(8).

**news** (32) — `NewsViewSet(ReadOnlyModelViewSet)` = list/retrieve(2) + `@action` 30개 (stock_news, sentiment, market, trending, all_news, sources, daily_keywords, keyword_detail, insights, news_events, impact_map, recommendations 등). **앱 중 @action 밀도 최고** — 스키마화 우선순위 높음.

**serverless** (64) — 최대 규모. Admin Dashboard(12), Market Movers(8), Breadth(3), Heatmap(3), Presets(7), Filters(1), Advanced Screener(1), Alerts(6), Thesis(4), ETF Holdings(9), LLM Relations(4), Institutional(3), Regulatory/Patent(2), Health(1). 함수형 뷰(FBV) 다수.

**thesis** — 명시 path 8(conversation 4 + monitoring 2 + alerts 2) + `ThesisViewSet`/`ThesisPremiseViewSet`/`ThesisIndicatorViewSet`(모두 `ModelViewSet`) + `@action` 2종(close, auto). 중첩 라우터(premise/indicator) 사용.

**chainsight** — 명시 9(events 2, seeds, sector graph, signals, trace, neighbors, graph, suggestions) + `WatchlistViewSet(ModelViewSet)` + `@action` 5종. `@extend_schema` 9건으로 명시 뷰는 대체로 커버됨.

---

## 도입 작업 목록

> 도구는 이미 도입 완료 → 실제 과제는 **`@extend_schema` 커버리지 확대**.

### 현재 커버리지 요약

- 코드 내 `@extend_schema` 적용 파일: 14개, 총 **37건** (docs/settings 제외)
- 잘 된 영역: market_pulse v2(100%), portfolio coach(100%), api_request admin(~83%), chainsight 명시 뷰
- **0% 영역 (우선 대상)**: stocks, macro, thesis, validation, sec_pipeline, iron_trading

### 작업 1 — 도구 설정 (불필요, 완료됨)

drf-spectacular 설치·설정·URL 마운트 전부 완료. **추가 작업 없음.**
단, 선택적 개선 여지:
- `DISABLE_ERRORS_AND_WARNINGS = True` → 일시적으로 `False`로 돌려 `manage.py spectacular --validate`로 경고 목록 확보 후 우선순위 산정 (운영 설정은 유지).

### 작업 2 — `@extend_schema` 추가 범위

우선순위별 (외부 노출도 + 미적용 규모 기준):

| 우선순위 | 앱 | 미적용 추정 | 비고 |
|:---:|----|:---:|----|
| **P1** | serverless | ~58 | 최대 규모, FBV 다수 — `@extend_schema(responses=...)` 개별 부착 |
| **P1** | news | ~30 (@action) | ViewSet `@action`별 `@extend_schema` + serializer 명시 |
| **P2** | stocks | 39 | symbol path param + 응답 serializer 정의 필요 (다수 dict 응답) |
| **P2** | thesis | ViewSet 3 + 8 | `@extend_schema_view`로 ViewSet CRUD 일괄 |
| **P3** | rag_analysis | ~13 | DataBasket/Session CRUD |
| **P3** | macro | 10 | 대시보드 응답 구조 명시 |
| **P3** | users | ~33 | JWT는 simplejwt 기본 스키마 활용 가능 |
| **P4** | validation, sec_pipeline, iron_trading | 6/2/1 | 소규모, 빠른 완료 가능 |

### 작업 3 — 예상 작업량

전제: 미적용 엔드포인트 약 **200개**. dict 응답이 많아 응답 serializer(또는 `inline_serializer`) 신규 정의가 병목.

| 단계 | 내용 | 예상 |
|------|------|:---:|
| 응답 스키마 표준화 | dict 응답 → `inline_serializer`/`OpenApiResponse` 패턴 정립 (envelope 정책 `docs/features/api_envelope/policy.md` 반영) | 0.5일 |
| P1 (serverless+news, ~88건) | FBV/@action 데코레이터 + serializer | 3~4일 |
| P2 (stocks+thesis, ~50건) | path param + ViewSet 일괄 | 2~3일 |
| P3 (rag+macro+users, ~56건) | CRUD/대시보드 | 2일 |
| P4 (소규모 3앱, ~9건) | 빠른 마감 | 0.5일 |
| 검증 | `spectacular --validate` 무경고 + Swagger UI 육안 확인 | 0.5일 |
| **합계** | | **약 8~10일 (1인 기준)** |

### 권장 접근

1. **점진적 확대** — 설정 주석(`settings.py:400~403`)이 명시한 정책 그대로: "정확한 schema가 필요한 view만 점진적으로 추가". 신규/변경 API는 PR 시 `@extend_schema` 필수화(컨트랙트 우선 원칙과 정합).
2. **ViewSet 우선** — news(@action 30) / thesis·chainsight(ModelViewSet)는 `@extend_schema_view`로 묶어 적은 작업으로 큰 커버리지 확보.
3. **외부 소비자 API 최우선** — `iron_trading`(외부 봇 read-only), `serverless`, `news`처럼 프론트/외부가 실제 의존하는 엔드포인트부터.

---

## 부록: 수집 근거

- 도구 설치: `pyproject.toml` (`drf-spectacular`, `drf-spectacular-sidecar`)
- 스키마 URL: `config/urls.py:62~72`
- 설정: `config/settings.py:377` (schema class), `:384~432` (SPECTACULAR_SETTINGS)
- `@extend_schema` 코드 분포 (37건): chain_sight/api/views.py(7), serverless/views.py(6), portfolio/api/views.py(6), api_request/admin_views.py(5), market_pulse/api/views/*(5), rag_analysis/views.py(2), news/api/views.py(2), users/views.py(2), chain_sight/api/event_views.py(2)
- 0% 앱: stocks, macro(market_pulse/views.py), thesis, validation, sec_pipeline, iron_trading
