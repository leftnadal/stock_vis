# API 문서 감사 보고서

- **감사일**: 2026-05-27
- **감사 범위**: Backend 전체 (Django REST Framework + drf-spectacular)
- **모드**: 읽기 전용 (코드 수정 없음)

---

## 현재 상태

### OpenAPI 도구 설치 현황

| 항목 | 상태 | 비고 |
|------|------|------|
| **drf-spectacular** | ✅ 설치 (^0.29.0) | `pyproject.toml` 명시 |
| **drf-spectacular-sidecar** | ✅ 설치 (^2026.4.14) | Swagger/ReDoc 정적 자산 |
| **drf-yasg** | ❌ 미설치 | (불필요) |
| `DEFAULT_SCHEMA_CLASS` | ✅ `drf_spectacular.openapi.AutoSchema` | `config/settings.py:369` |
| `SPECTACULAR_SETTINGS` | ✅ 활성 | `config/settings.py:376–` |

### 스펙 제공 엔드포인트 (`config/urls.py:62–73`)

| URL | 역할 |
|-----|------|
| `GET /api/v2/schema/` | OpenAPI JSON/YAML 스펙 |
| `GET /api/v2/swagger/` | Swagger UI |
| `GET /api/v2/redoc/` | ReDoc UI |

### SPECTACULAR_SETTINGS 요약

- **Title**: `Stock-Vis Market Pulse v2 API` (v2 중심으로 초기 설정됨)
- **VERSION**: `2.0`
- **SCHEMA_PATH_PREFIX**: `r'/api/v[12]'` → v1·v2 양쪽 스캔
- **DISABLE_ERRORS_AND_WARNINGS**: `True` — graceful fallback (string body) 허용, 경고 무시
- **TAGS**: `Market Pulse v2` 1건만 명시 (나머지 자동 분류)
- **COMPONENT_SPLIT_REQUEST**: `True` — request/response schema 분리
- **ENUM_NAME_OVERRIDES**: `config/spectacular_enums.py`에서 enum 충돌 해소

### `@extend_schema` 데코레이터 적용 현황 (37건/13개 파일)

| 파일 | 적용 수 | 비고 |
|------|---:|------|
| `chainsight/api/views.py` | 7 | Phase 5 LLM relations 등 |
| `serverless/views.py` | 6 | Market Movers, ETF, Chain Sight Phase 7~8 |
| `portfolio/api/views.py` | 6 | Coach E1~E6 (6 endpoint 전부) |
| `api_request/admin_views.py` | 5 | Provider admin API 전부 |
| `users/views.py` | 2 | 일부만 |
| `rag_analysis/views.py` | 2 | DataBasket 일부 |
| `news/api/views.py` | 2 | NewsViewSet 일부 |
| `marketpulse/api/views/*.py` | 5 | overview/cards/news_refresh/i18n/health 각 1 (v2 전부) |
| `config/settings.py` | 2 | (enum override 등 메타) |
| **합계** | **37** | |

### 평가

- ✅ **인프라는 완비**: drf-spectacular 운영 중, 스펙 endpoint 노출 중, sidecar로 UI 즉시 서빙
- ⚠️ **핵심 영역만 명시 스키마**: Market Pulse v2 (5/5), Coach API (6/6), Provider Admin (5/5)은 완료
- ❌ **대다수 v1 endpoint는 fallback**: `DISABLE_ERRORS_AND_WARNINGS=True`로 경고 무시 중. 응답이 string body로 노출되어 클라이언트 타입 생성 불가
- 📌 **방침 메모(settings.py:393~395)**: "정확한 schema가 필요한 view만 점진적으로 `@extend_schema(responses=...)` 추가"

---

## 엔드포인트 목록 (앱별)

> 집계 기준: 각 `urls.py`의 `path(...)` 등록 수. `DefaultRouter`로 등록된 ViewSet은 단일 entry로 표시 (실제 action 수는 별도).

| 앱 | URL prefix | `path()` 수 | ViewSet 라우터 | `@extend_schema` 적용 | 비고 |
|----|------------|---:|---:|---:|------|
| **users** | `/api/v1/users/` | 35 | 0 | 2 | JWT + 세션 인증 + Portfolio + Favorites + Watchlist + Interests |
| **stocks** | `/api/v1/stocks/` | 39 | 0 | 0 | MVP/Indicators/Search/Movers/Fundamentals/Screener/Exchange/EOD |
| **news** | `/api/v1/news/` | 1 | NewsViewSet (router) | 2 | Action 다수 (ViewSet 내부) |
| **macro** | `/api/v1/macro/` | 10 | 0 | 0 | Market Pulse + 개별 섹션 + 동기화 |
| **rag_analysis** | `/api/v1/rag/` | 15 | 0 | 2 | DataBasket + AnalysisSession + Monitoring |
| **serverless** | `/api/v1/serverless/` | 64 | 0 | 6 | Admin/Movers/Breadth/Heatmap/Presets/Alerts/Thesis/ETF/LLM relations/Institutional/Regulatory |
| **thesis** | `/api/v1/thesis/` | 11 | 3 (Thesis + Premise + Indicator) | 0 | Conversation + Dashboard + Alerts + nested ViewSet |
| **validation** | `/api/v1/validation/` | 6 | 0 | 0 | Summary/Metrics/Leader/Presets/Peer pref/LLM filter |
| **chainsight** | `/api/v1/chainsight/` | 7 | 1 (Watchlist) | 7 | Seeds/Sector graph/Signals/Trace/Neighbors/Graph/Suggestions |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | 0 | 0 | Admin dashboard + Filing data |
| **iron_trading** | `/api/v1/iron-trading/` | 2 | 0 | 0 | Daily context (trailing slash 양쪽) |
| **api_request** | `/api/v1/` (admin) | 6 | 0 | 5 | Provider admin (health + 5 admin) |
| **portfolio (legacy)** | `/api/` | 0 | 0 | 0 | Slice 13 #65에서 전수 제거, include만 잔존 |
| **portfolio.api (Coach)** | `/api/v1/coach/` | 6 | 0 | 6 | E1~E6 단일화 (`portfolio/api/views.py`) |
| **marketpulse v2** | `/api/v2/market-pulse/` | 5 | 0 | 5 | overview / cards / news/refresh / i18n / health |
| **config root** | `/` | 4 | 0 | 0 | api_root + health + schema/swagger/redoc |
| **합계** | — | **213** | **4 router** | **37** | — |

### 커버리지 요약

| 커버리지 등급 | 정의 | 해당 앱 |
|--------------|------|---------|
| 🟢 **완료** | 전 endpoint에 `@extend_schema` | marketpulse v2, portfolio.api (Coach), api_request, chainsight |
| 🟡 **부분** | 일부만 적용 | users(2/35), rag_analysis(2/15), serverless(6/64), news(2/?) |
| 🔴 **미적용** | 0건 | stocks(39), macro(10), thesis(11+3router), validation(6), sec_pipeline(2), iron_trading(2) |

- **숫자상 커버리지**: 37 / 213 ≈ **17.4%** (router 내부 action 제외 시 기준)
- **핵심 신규 영역(v2 + Coach)은 사실상 100%**, 레거시 v1 영역이 미적용 다수

---

## 도입 작업 목록

### Phase 0 — 인프라 (✅ 완료, 신규 작업 없음)

- [x] drf-spectacular + sidecar 설치
- [x] `DEFAULT_SCHEMA_CLASS` 등록
- [x] `SPECTACULAR_SETTINGS` 정의 + ENUM_NAME_OVERRIDES
- [x] `/api/v2/schema/`, `/swagger/`, `/redoc/` URL 노출
- [x] EXCEPTION_HANDLER 표준 (api_envelope policy)

### Phase 1 — 메타 정비 (소규모, ~1h)

| 작업 | 위치 | 예상 비용 |
|------|------|---:|
| `TITLE`/`DESCRIPTION`을 "Market Pulse v2"에서 전체 플랫폼으로 격상 | `config/settings.py:377` | 5분 |
| `TAGS`에 앱별 항목 추가 (users/stocks/macro/news/rag/serverless/thesis/validation/chainsight/sec_pipeline) | 동일 | 15분 |
| `DISABLE_ERRORS_AND_WARNINGS=True` 일시 해제 후 스펙 빌드 → 경고 목록 dump → 우선순위 도출 | dev 환경 | 30분 |
| `SCHEMA_PATH_PREFIX` 그대로 유지 (v1·v2 양립 검증됨) | — | 0분 |

### Phase 2 — `@extend_schema` 적용 우선순위

> 외부 클라이언트(프론트엔드, iron_trading 봇, 운영 admin)가 직접 호출하는 영역을 우선.

| 우선순위 | 앱 | 미적용 endpoint 수 | 적용 난이도 | 비고 |
|---:|----|---:|------|------|
| **P0** | **stocks** | 39 | 中 | 프론트엔드 종목 상세/차트/검색 핵심. 단 다수가 read-only GET이라 `OpenApiTypes` + `inline_serializer`로 빠른 적용 가능 |
| **P0** | **macro** | 10 | 易 | Market Pulse v1 (v2 마이그레이션 전 호환층). 응답 구조 단순 |
| **P0** | **thesis** | 11 + 3 router | 中 | UUID path param + ViewSet nested. ViewSet은 `@extend_schema_view`로 일괄 처리 |
| **P1** | **validation** | 6 | 易 | Symbol 기반 6개 — 1h 내 완료 가능 |
| **P1** | **users (잔여)** | 33 | 中 | Portfolio/Watchlist/Favorites/Interests — request/response serializer 다수 |
| **P1** | **rag_analysis (잔여)** | 13 | 中 | DataBasket/Session/Monitoring. SSE chat-stream은 `OpenApiTypes.STR` fallback 명시 |
| **P2** | **serverless (잔여)** | 58 | 高 | 함수형 view 다수 + 응답 비정형 — Pydantic→serializer 마이그레이션 동반 검토 |
| **P2** | **sec_pipeline** | 2 | 易 | Filing data + dashboard |
| **P2** | **iron_trading** | 2 | 易 | 외부 봇 read-only — 계약 고정 필요성 高 |
| **P3** | **news (router)** | ViewSet action ~7 | 中 | `@extend_schema_view`로 일괄 |

### 작업량 추정

| 단위 | 예상 시간 |
|------|---:|
| `@extend_schema` 단순 GET endpoint (응답만) | 5~10분/건 |
| `@extend_schema` POST + request serializer | 10~20분/건 |
| ViewSet 전체 `@extend_schema_view` | 30~60분/ViewSet |
| 응답 구조 추출 (현재 dict 반환 → `inline_serializer`) | 10~30분/건 |

**총량**:
- P0 (stocks+macro+thesis): 약 **8~12시간**
- P1 (validation+users잔여+rag잔여): 약 **6~10시간**
- P2 (serverless+sec+iron): 약 **10~15시간** (serverless가 대부분)
- P3 (news router): 약 **1~2시간**
- **합계**: 약 **25~40시간** (1주 풀타임 또는 2~3주 분산)

### Phase 3 — 운영 정착 (선택)

- [ ] CI에 `python manage.py spectacular --validate --fail-on-warn` 추가
- [ ] `DISABLE_ERRORS_AND_WARNINGS=False`로 전환 + 경고 0 유지
- [ ] OpenAPI JSON을 `contracts/openapi.json`으로 정기 export → `frontend/src/lib/api/__generated__/` 타입 생성 파이프라인 (Slice 15 Step 0 codegen 파이프라인과 연동 — `project_slice15_step0` 메모리 참조)
- [ ] PR 템플릿에 "신규 endpoint 시 `@extend_schema` 필수" 체크박스 추가

---

## 부속 발견사항

1. **Legacy `portfolio/urls.py`는 빈 상태** (`urlpatterns: list = []`) — Slice 13 #65에서 정리됨. `config/urls.py:53`에서 include만 잔존하므로 향후 제거 후보.
2. **`iron_trading/urls.py`는 trailing-slash 양쪽 등록** — 스펙에서는 한 쪽만 노출되도록 `@extend_schema(operation_id=...)` 명시 권장.
3. **`thesis/urls.py`의 nested router** (`<uuid:thesis_id>/premises/`, `<uuid:thesis_id>/indicators/`)는 drf-spectacular 자동 추론이 부정확할 수 있음 — `@extend_schema_view` + `parameters=[OpenApiParameter('thesis_id', ...)]` 명시 필요.
4. **`serverless` 함수형 view 64개**는 `@api_view` 데코레이터 기반일 가능성 高 — 스키마 추출 시 `@extend_schema` 직접 부착 가능하나, 응답 구조가 dict 반환이라 `inline_serializer` 또는 신규 `*Response` serializer 정의 필요.
5. **`SCHEMA_PATH_PREFIX = r'/api/v[12]'`**는 `/api/coach/` (legacy 비어있음)와 `/admin/` 등 비-API 경로를 자동 제외하므로 적절.

---

## 결론

- **인프라**: 완비 ✅ — 추가 설치 작업 없음
- **현재 커버리지**: 37/213 (≈17%), 단 신규 영역(Market Pulse v2, Coach API)은 100%
- **우선 작업**: P0 3개 앱 (stocks/macro/thesis) — 약 8~12시간
- **전체 도입 비용**: 25~40시간 (분할 가능, 슬라이스별 부분 적용 가능)
- **권장 진행 방식**: 부채 #도입형으로 단일 슬라이스화 대신, 각 슬라이스에 영향받는 endpoint만 점진 적용 + Phase 3 CI 게이트로 신규 추가 강제
