# API 문서 감사 보고서

**감사 일시**: 2026-05-06
**감사 대상**: `/Users/byeongjinjeong/Desktop/stock_vis`
**감사자**: Claude (자동 감사 시스템)
**감사 범위**: 백엔드 API 문서화 현황 및 도입 작업 범위 평가

---

## 현재 상태

### 1. API 문서화 도구 설치 여부

| 도구 | 설치 여부 | 비고 |
|------|----------|------|
| **drf-spectacular** | ❌ 미설치 | `pyproject.toml`, `poetry.lock` 양쪽 모두 없음 |
| **drf-yasg** | ❌ 미설치 | `pyproject.toml`, `poetry.lock` 양쪽 모두 없음 |
| **djangorestframework** | ✅ 설치 (3.16.1) | `simplejwt`의 transitive dependency |

`pyproject.toml`은 명시적으로 DRF를 선언하지 않고 `djangorestframework-simplejwt = "^5.5.1"`을 통해 간접 의존만 한다. 따라서 **OpenAPI/Swagger 스펙을 자동 생성할 수 있는 수단이 전혀 없다**.

### 2. DRF 설정 (`config/settings.py:341-349`)

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}
```

- `DEFAULT_SCHEMA_CLASS` **미설정** → DRF 기본값 (`AutoSchema`)만 동작, OpenAPI 3.x 스펙 미생성
- `SPECTACULAR_SETTINGS` **미존재** → drf-spectacular 활성화 시 추가 필요

### 3. 코드 레벨 스키마 데코레이터

| 패턴 | 검출 횟수 | 비고 |
|------|----------|------|
| `extend_schema` / `drf_spectacular` | **0건** | 단 한 곳도 사용되지 않음 |
| `drf_yasg` / `swagger_auto_schema` | **0건** | 단 한 곳도 사용되지 않음 |
| `@api_view` | 54건 (`config/views.py`, `serverless/views.py`) | drf 기본 데코레이터, 스키마 정보 부족 |

> 결론: **현재 자동 생성 가능한 OpenAPI 스펙이 0%**. 클라이언트는 `frontend/lib/api/*` 코드와 backend `views.py`를 직접 읽어야 계약을 알 수 있다.

### 4. 대안적 문서화 흔적

- `config/views.py:api_root`: 일부 엔드포인트를 JSON으로 하드코딩 나열 (수기 관리, drift 위험 큼)
- `contracts/` 디렉터리: `CLAUDE.md`에 "API 변경 시 OpenAPI 스펙 먼저 갱신"이라는 규칙이 있으나 **실제 OpenAPI 파일은 자동 생성되지 않고 수기 작성에 의존**

---

## 엔드포인트 목록 (앱별 테이블)

### 4-1. 앱별 엔드포인트 수 집계

| # | 앱 | URL 파일 | URL 패턴 수 | 주요 View 클래스 / 함수 | 비고 |
|---|----|---------|-----:|------------------------|------|
| 1 | **stocks** | `stocks/urls.py` | **39** | 39 path × `*View.as_view()` | views가 8개 파일로 분리 (views, views_mvp, views_indicators, views_search, views_market_movers, views_fundamentals, views_screener, views_exchange, views_eod) |
| 2 | **users** | `users/urls.py` | **35** | JWT 7 + 세션 6 + Favorites 3 + Portfolio 9 + Interests 2 + Watchlist 8 | JWT/세션 인증 이중 노출 |
| 3 | **news** | `news/api/urls.py` | **1 router + ~30 actions** | `NewsViewSet` (ReadOnlyModelViewSet) + 30개 `@action` | 하나의 ViewSet에 30개 이상 액션 집중 (admin/ml/alerts 포함) |
| 4 | **macro** | `macro/urls.py` | **9** | MarketPulse, FearGreed, InterestRates, Inflation, GlobalMarkets, Calendar, VIX, Sectors, DataSync, SyncStatus | 평탄한 구조 |
| 5 | **rag_analysis** | `rag_analysis/urls.py` | **16** | DataBasket 6 + Session 4 + Monitoring 5 | SSE Chat 스트림 1건 (`ChatStreamView`) |
| 6 | **serverless** | `serverless/urls.py` | **64** | Admin Dashboard 12 + Movers 8 + Breadth 3 + Heatmap 3 + Presets 7 + Filters 1 + Screener 1 + Alerts 6 + Thesis 4 + ETF 9 + LLM Relations 4 + Institutional 3 + Regulatory/Patent 2 + Health 1 | 대부분 함수형 view (`@api_view`) |
| 7 | **thesis** | `thesis/urls.py` | **8 + 3 ViewSets (~28)** | ThesisViewSet, ThesisPremiseViewSet, ThesisIndicatorViewSet + 4 conversation + 2 monitoring + 2 alerts | nested router 사용 |
| 8 | **validation** | `validation/api/urls.py` | **6** | Summary, Metrics, LeaderComparison, Presets, PeerPreference, LLMFilter | 모두 `<symbol>` prefix |
| 9 | **chainsight** | `chainsight/api/urls.py` | **7 + 1 ViewSet (~18)** | ChainSightGraph, Suggestion, Trace, Seeds, SectorGraph, Neighbor, Signal + WatchlistViewSet (CRUD + 5 actions) | |
| 10 | **sec_pipeline** | `sec_pipeline/urls.py` | **2** | sec_pipeline_dashboard, FilingDataView | 가장 작음 |
| 11 | **api_request** | `api_request/urls.py` | **6** | Provider Status, RateLimits, Cache, Test, Config + Health | Admin 전용 (IsAdminUser) |
| 12 | **portfolio** | `portfolio/urls.py` | **2** | coach_e1_garp, coach_e5_adjustment | 함수형 view |
| 13 | **config (root)** | `config/urls.py` | **2** | api_root, health_check | + admin |
| | **합계** | | **약 220~230개** | — | ViewSet 액션을 펼치면 **230+** |

### 4-2. View 정의 단위 통계

| 정의 단위 | 개수 | 출처 |
|----------|-----:|------|
| `class *View` / `*ViewSet` | **111** | 17개 view 파일 |
| `def view(request, ...)` (FBV) | **57** | 4개 view 파일 (대부분 `serverless/views.py`에 52개) |
| **총 view 단위** | **168** | — |

### 4-3. 라우팅 패턴 특징

| 패턴 | 사용처 | 영향 |
|------|--------|------|
| `DefaultRouter` (DRF ViewSet) | news, thesis, chainsight | OpenAPI 자동 생성 친화적 |
| `path()` + `as_view()` (CBV) | stocks, users, macro, rag_analysis, validation, sec_pipeline, api_request | drf-spectacular와 호환되나 `@extend_schema` 보강 권장 |
| `path()` + 함수형 `@api_view` | serverless (대부분), portfolio, config | **자동 스키마 생성 시 정보가 가장 빈약** — 명시적 데코레이션 필수 |
| Nested router | thesis (`<thesis_id>/premises/`, `<thesis_id>/indicators/`) | 경로 파라미터 스키마 매핑 주의 |
| URL prefix 누락 | `serverless/urls.py` (`movers`, `breadth` 등 trailing slash 없음) | 일관성 감소, OpenAPI tags 분류 모호 |

### 4-4. 인증/권한 분포 (스폿 체크)

- **AllowAny**: news `market-feed`, `interest-options`, api_request `health/`, config `health-check`
- **IsAuthenticated**: news `personalized-feed`, 대부분의 users/portfolio
- **IsAdminUser**: api_request `admin/providers/*`, news 의 admin/ml-* 액션 다수, serverless `admin/dashboard/*`
- **IsAuthenticatedOrReadOnly** (DRF 기본): 명시되지 않은 모든 엔드포인트

> 권한 정책이 **앱마다 명시 방식이 다르다** (decorator vs ViewSet 속성 vs 기본값) → OpenAPI `security` 필드가 일관적으로 추출되지 않을 위험.

---

## 도입 작업 목록

### 5-1. 권장 도구: **drf-spectacular**

drf-yasg는 OpenAPI 2.0(Swagger) 기반이고 사실상 유지보수 모드. drf-spectacular는 OpenAPI 3.0.3 + DRF 공식 권장이며 `@extend_schema`로 세분 제어 가능.

### 5-2. Phase 1 — 기본 인프라 구축 (예상 0.5~1일)

| 단계 | 작업 | 영향 파일 |
|-----|------|----------|
| 1.1 | `poetry add drf-spectacular` | `pyproject.toml`, `poetry.lock` |
| 1.2 | `INSTALLED_APPS`에 `'drf_spectacular'` 추가 | `config/settings.py` |
| 1.3 | `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'` | `config/settings.py:341` |
| 1.4 | `SPECTACULAR_SETTINGS` 블록 추가 (TITLE, VERSION, DESCRIPTION, SERVE_INCLUDE_SCHEMA, COMPONENT_SPLIT_REQUEST, TAGS) | `config/settings.py` |
| 1.5 | URL 라우트 추가 (`/api/schema/`, `/api/schema/swagger-ui/`, `/api/schema/redoc/`) | `config/urls.py` |
| 1.6 | CI에서 `python manage.py spectacular --validate --fail-on-warn` 실행 | `.github/workflows/*.yml` (선택) |

→ 이 시점부터 **모든 ViewSet/APIView가 자동으로 기본 스키마 노출**. 단, 함수형 `@api_view`와 복잡한 응답은 빈약.

### 5-3. Phase 2 — `@extend_schema` 보강 (예상 작업량)

| 영역 | 우선순위 | 대상 view 단위 수 | 예상 시간(중간 추정) | 근거 |
|------|--------|------:|------:|------|
| **stocks** (CBV 39개) | 🔴 High | 39 | 8h | 프론트 핵심, request_serializer/response 스펙 명세 필요 |
| **users** (JWT/Portfolio/Watchlist) | 🔴 High | ~35 | 8h | 인증·권한 차이가 커서 `auth=`, `parameters=` 명시 필요 |
| **news** (`NewsViewSet` 30+ actions) | 🔴 High | 30+ | 10h | 단일 ViewSet에 액션 집중, 각 `@action`마다 `@extend_schema_view` + `@extend_schema` 필요 |
| **serverless** (FBV 52개) | 🔴 High | 52 | 12h | 함수형 view라 `@extend_schema(request=..., responses=..., methods=[...])` 명시 필수, 스펙 추출 빈약 |
| **thesis** (3 ViewSet + 4 explicit) | 🟡 Mid | ~14 | 4h | nested URL 파라미터 (`<uuid:thesis_id>`) 매핑 |
| **rag_analysis** (16) | 🟡 Mid | 16 | 4h | SSE 스트림 (`ChatStreamView`) → `@extend_schema(responses={200: OpenApiTypes.STR})` 별도 처리 |
| **macro** (9) | 🟢 Low | 9 | 2h | 응답 구조 단순 |
| **chainsight** (~14) | 🟡 Mid | ~14 | 4h | `WatchlistViewSet` actions + 그래프 구조 응답 명시 |
| **validation** (6) | 🟢 Low | 6 | 2h | symbol 단일 파라미터 |
| **sec_pipeline** (2), **api_request** (6), **portfolio** (2), **config** (2) | 🟢 Low | 12 | 2h | 소규모 |
| **합계** | | **~230 view 단위** | **약 56h (7~8 working days)** | 1인 작업 기준, Serializer 재사용도 따라 가변 |

### 5-4. Phase 3 — Serializer/Response 정합성 (작업량 추가)

`@extend_schema(responses=...)`에서 사용할 `*Serializer` 정의가 **현재 일부 view에서 미존재**할 가능성이 있음 — 확인 필요. dict 직접 반환 패턴이 많을 경우 `inline_serializer` 또는 신규 Serializer 작성으로 +20~30%.

| 작업 | 예상 시간 |
|------|---------:|
| 응답 dict가 그대로 반환되는 view 식별 + 응답용 ReadOnly Serializer 추가 | 8~16h |
| 에러 응답 표준 (`ErrorSerializer`) 정의 + 모든 view에 `responses={400: ErrorSerializer, ...}` 적용 | 4h |
| `OpenApiExample` 으로 실제 샘플 응답 추가 (선택) | 8h |

### 5-5. Phase 4 — 검증 / 운영화

| 작업 | 산출물 |
|------|--------|
| `python manage.py spectacular --color --file schema.yaml` 로 정적 스펙 추출 후 `contracts/openapi.yaml` 갱신 | `contracts/` 동기화 |
| 프론트엔드 타입 자동 생성 (`openapi-typescript` 또는 `orval`) → `frontend/contracts/api-types.d.ts` | TS strict 모드 호환 |
| Swagger UI를 `/api/docs/`에서 인증 가드(`IsAdminUser`) 뒤로 보호 | 프로덕션 노출 정책 |
| `pre-commit` 훅에 `spectacular --validate` 추가 | 스펙-구현 drift 차단 |
| `SPECTACULAR_SETTINGS['SCHEMA_PATH_PREFIX']` 으로 `/api/v1/` prefix 정규화 | 깔끔한 path |

### 5-6. 도입 시 예상 리스크

| 리스크 | 완화책 |
|--------|--------|
| 함수형 `@api_view` 다수 (serverless 52건) → 스키마 추론 실패 | `@extend_schema` 필수, 우선순위 높게 처리 |
| `NewsViewSet` 단일 클래스에 30+ 액션 → 응답 스키마가 `@action`별로 모두 다름 | `@extend_schema_view` 로 액션별 스키마 일괄 명시 |
| `ChatStreamView` (SSE) → OpenAPI 표현 부재 | `responses={200: OpenApiTypes.STR}` + `description="text/event-stream"` 명시 |
| `permission_classes`가 액션별로 다름 (news ml-* admin) | `@extend_schema(auth=[...])` 또는 ViewSet level `get_permissions` 점검 |
| `<uuid:thesis_id>` 등 path converter | spectacular는 자동 인식하지만 nested router의 `(thesis_id, indicator_id)` 두 파라미터 케이스 검증 필요 |
| `contracts/openapi.yaml`이 이미 수기로 존재할 가능성 (CLAUDE.md 규칙) | 자동 생성 결과로 덮어쓸지 병합할지 정책 결정 |

### 5-7. 총 예상 작업량 요약

| Phase | 작업 | 예상 시간 |
|-------|------|---------:|
| Phase 1 | 인프라 구축 | **4~8h** |
| Phase 2 | `@extend_schema` 보강 (230 view) | **56h** |
| Phase 3 | Serializer/Response 정합 | **20~30h** |
| Phase 4 | 검증/운영화 (CI, 프론트 타입 생성) | **8~12h** |
| **합계** | — | **88~106h (약 11~13 working days, 1인 기준)** |

---

## 부록 A — 주요 발견 요약

1. **현재 상태**: drf-spectacular/drf-yasg **미설치**, `@extend_schema` **0건**, `DEFAULT_SCHEMA_CLASS` **미설정** → OpenAPI 자동 생성 불가능.
2. **수기 문서화 흔적**: `config/views.py:api_root` 의 JSON 응답이 일부 엔드포인트를 하드코딩 나열 (drift 위험).
3. **계약 정책**: `CLAUDE.md`는 `contracts/` 디렉터리에 OpenAPI 스펙을 두라고 명시하지만 **자동 생성 메커니즘이 없어 사실상 수기 갱신 책임**.
4. **규모**: 12개 앱, **220~230개 URL 패턴**, **168개 view 정의 단위** (CBV 111 + FBV 57). 그 중 `serverless/views.py` 52개 함수형 view + `news/api/views.py` `NewsViewSet`의 30+ 액션이 가장 큰 부담.
5. **권장 액션**: drf-spectacular 도입 → 1주일 내 기본 스키마 노출 가능, 전체 보강은 약 11~13 working days.

## 부록 B — 감사 방법론 한계

- 본 감사는 URL 패턴과 view 정의 수를 **정적 분석으로** 카운트했음. 실제 호출되는 메서드(GET/POST/PUT/DELETE) 단위로 펼치면 OpenAPI operation 수는 더 늘어날 수 있음 (예: ModelViewSet 1개 = 6 operations).
- ViewSet의 `@action` 액션은 `@action` 데코레이터 검출 결과에 의존했으며 dynamic registration은 누락 가능.
- `frontend/lib/api/*` 코드와의 정합성은 본 보고서 범위 외.

---

**감사 종료**: 코드 수정 없음. 본 문서는 읽기 전용 산출물로, `docs/nightly_auto_system/reports/5월/5일/api_docs_audit.md`에 저장됨.
