# API 문서 감사 보고서

**감사 일자**: 2026-05-28
**감사 범위**: stock_vis 백엔드 전 앱 (urls.py + views*.py + 의존성)
**모드**: 읽기 전용 (코드 수정 없음)
**대상 디렉터리**: `/Users/byeongjinjeong/Desktop/stock_vis`

---

## 현재 상태

### 1) OpenAPI 도구 설치 여부

| 도구 | 설치 여부 | 버전 |
|------|---------|------|
| **drf-spectacular** | ✅ 설치 | `^0.29.0` (`pyproject.toml`) |
| **drf-spectacular-sidecar** | ✅ 설치 | `^2026.4.14` (`pyproject.toml`) |
| drf-yasg | ❌ 미사용 | — |

→ `pyproject.toml` 직접 grep으로 확인. `requirements.txt`에는 명시되어 있지 않음(poetry → requirements 추출 시 파생). **Swagger/OpenAPI 스펙 자동 생성 인프라는 이미 구축되어 있음.**

### 2) Swagger / Redoc 서빙 경로 (config/urls.py)

| URL | View | 비고 |
|-----|------|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 JSON/YAML |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | Redoc UI |

→ `name='schema-v2'`로 등록. 라우트는 `v2`지만 `SCHEMA_PATH_PREFIX = r'/api/v[12]'` 설정으로 **v1 + v2 둘 다 스펙에 노출**됨 (`config/settings.py:388`).

### 3) SPECTACULAR_SETTINGS 핵심 옵션 (`config/settings.py:376-` 이하)

- `TITLE`: "Stock-Vis Market Pulse v2 API" (현재 타이틀은 Market Pulse 중심으로 좁게 잡혀 있음 — 전사 통합 시 변경 필요)
- `VERSION`: `2.0`
- `SCHEMA_PATH_PREFIX`: `r'/api/v[12]'` (v1, v2 모두 캡처)
- `DISABLE_ERRORS_AND_WARNINGS`: **`True`** — "unable to guess serializer" 등 v1 다수 view의 graceful fallback 경고를 무시 중. **스펙 품질 저하의 핵심 원인.**
- `ENUM_NAME_OVERRIDES`: thesis/news/chainsight enum 충돌 해소 일부 정의
- `COMPONENT_SPLIT_REQUEST`: True
- Sidecar 정적 자원 사용 (`SWAGGER_UI_DIST = 'SIDECAR'`)

### 4) `@extend_schema` 데코레이터 적용 현황

전수 grep 결과: **총 59 instances**. 앱별 분포:

| 위치 | extend_schema 수 |
|------|------------------|
| `chainsight/api/views.py` | 8 |
| `serverless/views.py` | 7 |
| `portfolio/api/views.py` | 7 (E1~E6 + 보조) |
| `api_request/admin_views.py` | 6 |
| `users/views.py` | 3 |
| `rag_analysis/views.py` | 3 |
| `news/api/views.py` | 3 |
| `marketpulse/api/views/*.py` | 각 2 × 5 파일 = 10 |
| 나머지 (stocks/, macro/, thesis/, validation/, sec_pipeline/, iron_trading/, graph_analysis/, metrics/, serverless/views_admin.py) | **0** |

### 5) 결론

- 인프라는 100% 갖춰져 있다. 별도 라이브러리 설치/세팅 작업 불필요.
- 그러나 **stocks/users/thesis/validation 등 핵심 앱은 데코레이터 0건**. 자동 추론에만 의지하면 스펙은 그려지지만 `request_body`, `responses`, `parameters`, `description`가 빈 깡통이거나 부정확하다.
- `DISABLE_ERRORS_AND_WARNINGS = True`가 켜져 있어 **품질 저하가 보이지 않는 상태로 누적**됨. 도입 1단계는 이 플래그를 끄고 경고를 정량화하는 것.

---

## 엔드포인트 목록 (앱별)

> 각 `urls.py`를 직접 읽고 `path(...)` 항목을 카운트. ViewSet은 router 등록 시 자동 생성되는 CRUD 5종(list/retrieve/create/update/destroy)을 별도 표시.

| 앱 | URL prefix | 직접 path() | ViewSet 자동생성(추정) | 합계(추정) | 데코레이터 적용률 |
|----|-----------|------------:|----------------------:|----------:|------------------|
| **stocks** | `/api/v1/stocks/` | **39** | 0 | 39 | 0 / 39 (0%) |
| **users** | `/api/v1/users/` | **35** (JWT 7 + 세션 6 + 즐겨찾기 3 + 포트폴리오 9 + 관심사 2 + Watchlist 8) | 0 | 35 | 3 / 35 (8%) |
| **news** | `/api/v1/news/` | **0 직접** | `NewsViewSet` router (CRUD + @action 추정 3) ≈ 8 | ~8 | 3 / ~8 (38%) |
| **macro** | `/api/v1/macro/` | **10** | 0 | 10 | 0 / 10 (0%) |
| **rag_analysis** | `/api/v1/rag/` | **15** | 0 | 15 | 3 / 15 (20%) |
| **serverless** | `/api/v1/serverless/` | **63** (admin 12 + movers/sync/keywords 8 + breadth 3 + heatmap 3 + presets 7 + filters 1 + screener 1 + alerts 6 + thesis 4 + ETF 8 + LLM-relations 4 + 기관 3 + 규제 1 + 특허 1 + health 1) | 0 | 63 | 7 / 63 (11%) |
| **thesis** | `/api/v1/thesis/` | **8** (conversation 4 + dashboard/indicator-readings 2 + alerts 2) | router 3개 (메인 + 중첩 premise + 중첩 indicator) × 5 ≈ 15 | ~23 | 0 / ~23 (0%) |
| **validation** | `/api/v1/validation/` | **6** | 0 | 6 | 0 / 6 (0%) |
| **chainsight** | `/api/v1/chainsight/` | **7** | `WatchlistViewSet` 5 ≈ 5 | ~12 | 8 / ~12 (67%) |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | **2** | 0 | 2 | 0 / 2 (0%) |
| iron_trading | `/api/v1/iron-trading/` | 2 (사실상 동일 view, slash 허용용) | 0 | 2 | 0 / 2 |
| api_request | `/api/v1/health/, /api/v1/admin/providers/*` | 6 | 0 | 6 | 6 / 6 (100%) |
| portfolio (legacy) | `/api/coach/*` | 0 (빈 urlpatterns, Slice 13 #65 정리) | — | 0 | — |
| portfolio.api | `/api/v1/coach/eN/` | 6 (E1~E6) | 0 | 6 | 7 / 6 (이상치 — 보조 decorator 포함) |
| marketpulse | `/api/v2/market-pulse/` | 5 (overview, cards detail, news refresh, i18n, health) | 0 | 5 | 10 / 5 (200% — view당 2개씩) |
| **합계** | | **~204** 직접 + ~28 ViewSet 자동 | — | **~232** | 약 **47 / 232 ≈ 20%** |

### 요청 시 명시된 10개 앱만 집계

| 앱 | 합계(추정) | extend_schema 적용 |
|----|----------:|------------------:|
| stocks | 39 | 0 |
| users | 35 | 3 |
| news | ~8 | 3 |
| macro | 10 | 0 |
| rag_analysis | 15 | 3 |
| serverless | 63 | 7 |
| thesis | ~23 | 0 |
| validation | 6 | 0 |
| chainsight | ~12 | 8 |
| sec_pipeline | 2 | 0 |
| **소계** | **~213** | **24 (11.3%)** |

→ **요청 10개 앱 기준 적용률 약 11%**. 전체(marketpulse, api_request, portfolio.api 포함) 기준으로도 20% 내외.

### Path 카운트 메모

- `users/urls.py`: JWT TokenRefreshView는 외부 패키지 view라 자체 카운트에는 포함하지만 데코레이터 작업 대상에서는 제외해야 함.
- `serverless/urls.py`: `LEGACY_KEEP_UNTIL_DC2`로 마킹된 ETF 그룹(8개)이 포함됨 — 폐기 예정이면 작업 대상에서 빼는 것이 맞음.
- `chainsight/api/urls.py`: `router.urls`를 `+`로 이어붙이는 패턴이라 Swagger 그룹핑이 자동으로 잡히는 동안에도 ViewSet `@action`이 있는지는 별도 확인 필요.
- `iron_trading/urls.py`: 동일 view를 trailing slash 양쪽 모두 매핑 — 스펙상 1개로 합쳐서 노출하려면 명시적 path 정리가 좋다.
- `portfolio/urls.py`: 빈 urlpatterns지만 config에서 여전히 `include`됨. 도입 시 cleanup 권장 (#65 후속 TODO에 명시).

---

## 도입 작업 목록

> 가정: 인프라(설치/세팅)는 이미 끝났고 **품질을 올리는 데코레이터 작업이 핵심**이라는 전제.

### Phase 0 — 가시성 회복 (반나절)

| # | 작업 | 산출물 | 예상 공수 |
|---|------|--------|----------|
| 0-1 | `SPECTACULAR_SETTINGS['DISABLE_ERRORS_AND_WARNINGS']` 일시 해제 → `python manage.py spectacular --file schema.yml` 실행 → 경고/에러 전수 캡처 | `schema_warnings_baseline.txt` | 1h |
| 0-2 | `SPECTACULAR_SETTINGS['TITLE']`/`DESCRIPTION`을 전사 통합 명칭으로 갱신(Market Pulse 한정 표현 → "Stock-Vis API") | settings.py 수정 1줄 | 0.2h |
| 0-3 | 누락된 enum 충돌 ENUM_NAME_OVERRIDES 추가 (validation, sec_pipeline, serverless에서 collision 가능성 점검) | settings.py | 0.5h |
| 0-4 | Swagger v1/v2 그룹 분리 검토 (`/api/v1/schema/` 별도 endpoint 신설 여부 결정) | 결정 문서 | 0.3h |

### Phase 1 — 외부 노출 / 결제 라인 우선 (1.5일)

> 인증·결제·외부 봇 연동 라인부터 스펙 완성. 클라이언트와의 계약 가치가 가장 높은 영역.

| 앱 | 대상 view 수 | 우선순위 근거 | 예상 공수 |
|----|-------------:|-------------|----------|
| **users (JWT 7 + Watchlist 8 + 포트폴리오 9)** | 24 | JWT/포트폴리오는 외부 클라이언트 1차 진입점 | 0.6일 |
| **iron_trading (2)** | 2 | 외부 봇 read-only 계약. 스펙 부재 시 봇 측에서 추측 코딩 | 0.1일 |
| **marketpulse (5)** | 5 | 이미 적용 완료 — 패턴 reference로 활용 | 0일 |
| **api_request (6)** | 6 | 이미 적용 완료 | 0일 |

→ **Phase 1 결과**: 인증·외부 봇·MarketPulse·Provider Admin이 모두 스펙 완성 상태. Phase 2 작업의 reference 패턴 확보.

### Phase 2 — 코어 도메인 (4~5일)

| 앱 | 대상 view 수 | 작업 내용 | 예상 공수 |
|----|-------------:|---------|----------|
| **stocks** | 39 | Symbol path param 타입(`OpenApiParameter`), DailyPrice/Fundamental serializer 매칭, MVP/RAG 응답 schema | 1.5일 |
| **thesis** | ~23 | ViewSet 3개 + nested router + 대화형 endpoint. Serializer는 이미 있으므로 `@extend_schema_view` 패턴으로 일괄 처리 가능 | 1일 |
| **rag_analysis** | 15 | SSE 스트리밍 view 별도 처리(`OpenApiResponse(response={'description': 'text/event-stream'})`) | 0.7일 |
| **validation** | 6 | symbol+preset 파라미터 명세 + Peer 비교 응답 schema | 0.3일 |
| **chainsight** | ~12 | 7건 추가(나머지는 적용 완료) + WatchlistViewSet @action 점검 | 0.3일 |
| **macro** | 10 | dashboard 응답 + sync trigger 응답 | 0.4일 |
| **news** | ~8 | NewsViewSet @action 식별 (`@action` 별 `@extend_schema` 필요) | 0.3일 |
| **sec_pipeline** | 2 | filing 응답 schema | 0.1일 |

### Phase 3 — 자동화 / 운영 (2일)

| 앱 | 대상 view 수 | 작업 내용 | 예상 공수 |
|----|-------------:|---------|----------|
| **serverless** | 63 | admin dashboard 12개는 내부 한정 → `@extend_schema(exclude=True)` 검토. 나머지 56개 중 LEGACY (ETF 8) 제외 시 ~48개. Phase 2.3 thesis/alerts/regulatory/patent는 응답 schema 작성 | 1.5일 |
| **portfolio.api** | 6 | E1~E6 — Pydantic↔spectacular bridge가 이미 있음 (`config/spectacular_enums.py` 참고). 보강만 | 0.3일 |
| 폐기 라인 정리 | — | `portfolio/urls.py` 빈 include 제거, ETF LEGACY 표기된 8개 endpoint 정책 결정 | 0.2일 |

### 총 작업량 예상

| 단계 | 예상 공수 |
|------|----------|
| Phase 0 (가시성) | 0.5일 |
| Phase 1 (외부 노출) | 1일 |
| Phase 2 (코어 도메인) | 5일 |
| Phase 3 (자동화 + 폐기 정리) | 2일 |
| **합계** | **약 8.5일 (1인 풀타임 기준)** |

→ Backend 1명이 8~9일 풀타임, 또는 @backend + @qa 협업으로 **약 5~6일**에 종료 가능.

### 작업 패턴 권장

1. **`@extend_schema_view`로 ViewSet 일괄 처리** — thesis/chainsight WatchlistViewSet/news NewsViewSet 같은 라우터 등록 view는 view 클래스 위에 `@extend_schema_view(list=..., retrieve=..., create=...)` 한 줄로 묶는다.
2. **Serializer-first** — 응답 schema는 가능한 한 기존 Serializer를 `OpenApiResponse(response=SomeSerializer)`로 재사용. 없는 경우만 inline serializer 생성.
3. **공통 에러 envelope 명세** — `config/exception_handler.py`에 표준 envelope(`{detail, code, errors, status_code}`)가 있으므로, 공통 `@extend_schema(responses={400: ErrorEnvelopeSerializer, 401: ..., 403: ...})` 패턴을 정의해 reuse한다 (`config/spectacular_enums.py`에 묶어두면 좋다).
4. **DISABLE_ERRORS_AND_WARNINGS는 Phase 0 직후 끄고 유지** — CI에 `spectacular --validate` 게이트를 추가하면 PR 단위로 스펙 회귀를 차단할 수 있다.
5. **`@extend_schema(exclude=True)` 활용** — admin/internal endpoint(serverless admin dashboard 12개, api_request admin 6개)는 외부 스펙에서 제외해 외부 클라이언트 노출면을 줄인다.

### 리스크 / 결정 필요

- **R1. v1/v2 스펙 분리 여부**: 현재 단일 스펙(`/api/v2/schema/`)에 v1+v2가 섞여 있음. 외부 SDK 발급 시 혼란 가능. → Phase 0-4에서 결정.
- **R2. LEGACY endpoint(ETF 8개, portfolio/urls.py 빈 include)**: 스펙에 노출할지 폐기할지 정책 확정 필요.
- **R3. SSE 스트리밍 endpoint(`rag_analysis/sessions/<pk>/chat/stream/`)**: OpenAPI 3.0은 SSE를 1급으로 표현 못 함. `text/event-stream` description만 명시하는 관례 채택 권장.
- **R4. `iron_trading` trailing-slash 중복**: 동일 view 2개 path가 스펙에 별도 endpoint로 노출됨. 정리 권장.

---

## 부록 — 감사 근거 명령/파일

- 의존성: `pyproject.toml` grep `drf-spectacular` → 2개 매치
- 라우팅 진입점: `config/urls.py:19-23, 28-74`
- Spectacular 설정: `config/settings.py:369-` (`DEFAULT_SCHEMA_CLASS`), `config/settings.py:376-` (`SPECTACULAR_SETTINGS`)
- 데코레이터 전수: `extend_schema` rg 결과 59건, 앱별 분포는 위 표 참조
- views 모듈: 20개 파일에서 194 occurrences (class View / class APIView / class ViewSet / @api_view / def *_api / def *_view)

> 본 보고서는 코드 수정 없이 read-only로 작성됨. 실행 단계 진입 시 Phase 0-1 결과(`schema_warnings_baseline.txt`)를 먼저 확보한 뒤 Phase 1 착수 권장.
