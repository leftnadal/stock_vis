# API 문서 감사 보고서

- 생성일: 2026-05-23
- 대상 브랜치: slice14
- 작성 방식: 읽기 전용 (코드 수정 없음)
- 범위: Django/DRF 백엔드 전체 URL 라우팅 + drf-spectacular 도입 상태

---

## 현재 상태

### 1) 도구 설치 상태

| 항목 | 상태 | 위치 / 비고 |
|------|------|-------------|
| `drf-spectacular` | ✅ 설치됨 (`^0.29.0`) | `pyproject.toml` |
| `drf-spectacular-sidecar` | ✅ 설치됨 (`^2026.4.14`) | `pyproject.toml` (Swagger UI / ReDoc 정적 자산) |
| `INSTALLED_APPS` 등록 | ✅ 등록 완료 | `config/settings.py:205-206` |
| `DEFAULT_SCHEMA_CLASS` | ✅ 설정 완료 | `config/settings.py:363` → `drf_spectacular.openapi.AutoSchema` |
| `SPECTACULAR_SETTINGS` | ✅ 정의됨 | `config/settings.py:370-` (TITLE/DESC/VERSION 2.0) |
| `requirements.txt` | ⚠️ 미반영 | Poetry-only 관리. requirements.txt에는 spectacular 키워드 없음 |
| `drf-yasg` | ❌ 미설치 | (의도된 선택 — spectacular 단독) |

### 2) Swagger / OpenAPI 노출 상태

`config/urls.py:62-72`에 **v2 한정**으로만 3개 엔드포인트 노출:

| 경로 | 뷰 | 비고 |
|------|----|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 spec (JSON/YAML) |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc |

핵심 제약:

- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` 로 v1/v2 모두 캡처는 하지만, **schema URL 자체가 v2 네임스페이스 안에 있음**. 별도 v1 schema URL은 노출되지 않음.
- `SERVE_INCLUDE_SCHEMA = False` — Swagger UI 안에 스펙 다운로드 링크 비포함.
- `DISABLE_ERRORS_AND_WARNINGS = True` (`settings.py:390`) — graceful fallback noise 무시 정책. 즉 **명시 데코레이터 없는 view는 string body로 무성공 통과** (정확한 schema 미보장).
- `ENUM_NAME_OVERRIDES` 일부 정의됨 (`ThesisPremiseCategoryEnum` 등) — collision 회피용.

### 3) `@extend_schema` 명시 적용 현황

| 파일 | extend_schema 횟수 | 뷰 클래스/함수 수 | 명시 비율 |
|------|---------------------|--------------------|------------|
| `marketpulse/api/views/cards.py` | 2 | 7 | 28% |
| `marketpulse/api/views/health.py` | 2 | 4 | 50% |
| `marketpulse/api/views/i18n.py` | 2 | 1 | (스키마 데코만, helper 포함) |
| `marketpulse/api/views/news_refresh.py` | 2 | 1 | — |
| `marketpulse/api/views/overview.py` | 2 | 11 | 18% |
| `api_request/admin_views.py` | 6 | 6 | **100%** |
| `chainsight/api/views.py` | 8 | 10 | 80% |
| `serverless/views.py` | 7 | 105 | **<7%** |
| `rag_analysis/views.py` | 3 | 15 | 20% |
| `users/views.py` | 3 | 27 | 11% |
| `news/api/views.py` | 3 | 2 (ViewSet) | (액션 단위) |
| `portfolio/api/views.py` | 0 | 12 | **0%** |
| `stocks/views*.py` (8개 파일) | 0 | 43 | **0%** |
| `macro/views.py` | 0 | 11 | **0%** |
| `validation/api/views.py` | 0 | 6 | **0%** |
| `sec_pipeline/views.py` | 0 | 2 | 0% |
| `thesis/views/*.py` | 0 | 20 | **0%** |

**요약**:
- 명시 데코레이터 완비 영역: `api_request`(100%), `chainsight/api`(80%), `marketpulse v2` 일부.
- 거의 비어 있는 영역: `stocks`(43개), `serverless`(~100개), `portfolio/api`, `macro`, `thesis`, `validation`.
- 정책적 보호막 (`DISABLE_ERRORS_AND_WARNINGS = True`) 덕에 빌드는 통과하지만, **schema 정확도/응답 모델/예시는 사실상 v2 marketpulse + chainsight + admin만 신뢰 가능**.

---

## 엔드포인트 목록 (앱별 테이블)

### 마운트 포인트 (config/urls.py)

| Prefix | include 대상 | 비고 |
|--------|---------------|------|
| `/api/v1/users/` | `users.urls` | JWT + 세션 + portfolio + watchlist |
| `/api/v1/stocks/` | `stocks.urls` | 차트/펀더멘털/스크리너/EOD |
| `/api/v1/news/` | `news.api.urls` | NewsViewSet (DRF router) |
| `/api/v1/macro/` | `macro.urls` | Market Pulse v1 (거시) |
| `/api/v1/rag/` | `rag_analysis.urls` | DataBasket/Session/Monitoring |
| `/api/v1/serverless/` | `serverless.urls` | Movers/Breadth/Heatmap/Screener/Alerts/ETF/LLM/Institutional |
| `/api/v1/thesis/` | `thesis.urls` | 가설 통제실 (ViewSet + nested router) |
| `/api/v1/validation/` | `validation.api.urls` | 1차 검증 |
| `/api/v1/chainsight/` | `chainsight.api.urls` | Chain Sight v2 |
| `/api/v1/sec-pipeline/` | `sec_pipeline.urls` | SEC 10-K |
| `/api/v1/` | `api_request.urls` | Provider admin |
| `/api/` | `portfolio.urls` | (현재 빈 모듈, `urlpatterns = []`) |
| `/api/v1/` | `portfolio.api.urls` (`portfolio_api`) | Coach E1~E6 |
| `/api/v2/market-pulse/` | `marketpulse.api.urls` | Market Pulse v2 |
| `/api/v2/{schema,swagger,redoc}/` | drf-spectacular | OpenAPI 노출 (v2 only) |
| `/`, `/health/`, `/admin/` | config.views / Django admin | 루트/헬스/관리자 |

### 앱별 엔드포인트 집계

> 카운트 기준: 각 `urls.py` 의 `path(...)` 라인 수. DRF `router.register()` 는 별도 표기. 정확한 라인은 해당 `urls.py` 참조.

| 앱 | 명시 path 수 | DRF router | 비고 |
|----|--------------|------------|------|
| **users** | 35 | 0 | JWT 7 + 세션 6 + favorites 3 + portfolio 9 + interests 2 + watchlist 8 |
| **stocks** | 39 | 0 | dashboard/detail 페이지 3 + MVP 4 + 펀더멘털 5 + 스크리너 6 + 시세 5 + EOD 3 + 기타 |
| **news** | 1 (include) | 1 ViewSet (`NewsViewSet` → 기본 5 + custom actions, `views.py` 라우트 액션 2건) | DefaultRouter 기반 |
| **macro** | 10 | 0 | pulse, fear-greed, interest-rates, inflation, global-markets, calendar, vix, sectors, sync, sync/status |
| **rag_analysis** | 15 | 0 | DataBasket 6 + Session 4 + Monitoring 5 |
| **serverless** | 64 | 0 | Admin 12 + Movers 4 + Keywords 4 + Breadth 3 + Heatmap 3 + Presets 7 + Filters 1 + Screener 1 + Alerts 6 + Thesis 4 + ETF 9 + LLM 4 + Institutional 3 + Regulatory/Patent 2 + Health 1 |
| **thesis** | 8 | 3 routers (`ThesisViewSet` root + nested `premise` + nested `indicator`) | conversation 4 + dashboard 2 + alerts 2 + ViewSet 액션들 |
| **validation** | 6 | 0 | symbol별 summary/metrics/leader/presets/peer-preference/llm-filter |
| **chainsight** | 7 | 1 router (`WatchlistViewSet`) | seeds/sector/signals/trace + neighbors/graph/suggestions |
| **sec_pipeline** | 2 | 0 | admin/dashboard + filing/<symbol> |
| **api_request** | 6 | 0 | health + admin/providers/* (status/rate-limits/cache/test/config) |
| **portfolio** (`portfolio.urls`) | 0 | 0 | 빈 모듈 (legacy 5건 #65로 제거 완료) |
| **portfolio_api** (`portfolio.api.urls`) | 6 | 0 | coach/e1 ~ coach/e6 |
| **marketpulse v2** (`marketpulse.api.urls`) | 5 | 0 | overview / cards/<id>/detail / news/refresh / i18n / health |
| **config** (root) | 3 | — | `/`, `/health/`, `/admin/` |
| **drf-spectacular** | 3 | — | `/api/v2/schema|swagger|redoc/` |
| **graph_analysis** | — | — | `urls.py` 미존재, `views.py`만 1개. config/urls.py 미연결 (CLAUDE.md 표기와 일치) |

**총 명시 엔드포인트 추정**: ≈ **210건** (path 라인 직접 카운트) + DRF router 자동 생성 (NewsViewSet, ThesisViewSet/premise/indicator, WatchlistViewSet → 약 20~30건 추가). **합 ≈ 230~240**.

---

## 도입 작업 목록

### Step 0 — 필수 인프라 (이미 완료된 항목 ✅)

| 작업 | 상태 |
|------|------|
| `drf-spectacular` 설치 (pyproject) | ✅ 완료 |
| `INSTALLED_APPS` 등록 | ✅ 완료 |
| `DEFAULT_SCHEMA_CLASS` 지정 | ✅ 완료 |
| `SPECTACULAR_SETTINGS` 정의 | ✅ 완료 (v2 기준) |
| Swagger/ReDoc URL 노출 | ✅ v2만 노출 |

### Step 1 — v1 schema 노출 분리 (소)

| 작업 | 작업량 | 비고 |
|------|--------|------|
| `/api/v1/schema/`, `/api/v1/swagger/`, `/api/v1/redoc/` 추가 | 1 PR (config/urls.py 한 줄씩) | 또는 통합 `/api/schema/` 단일화 (path prefix regex 그대로 v1/v2 모두 캡처 가능) |
| `SPECTACULAR_SETTINGS.TITLE/DESCRIPTION` 일반화 ("Market Pulse v2" → "Stock-Vis API v1+v2") | 소 (텍스트 수정) | v1을 1급 시민으로 노출하는 결정 필요 |
| `requirements.txt` 동기화 | 옵션 (Poetry 단독이면 불필요) | 도커 빌드가 Poetry export 쓰면 불필요 |

### Step 2 — 데코레이터 추가 범위 (대)

> **선결 조건**: `DISABLE_ERRORS_AND_WARNINGS = True` 유지 여부 결정.
> - 유지 = 점진적 도입 가능 (현 정책)
> - 해제 = 한 번에 전체 schema 정확도 강제 → 빌드 차단 가능성 (PR 단위 마이그레이션 권장)

#### 우선순위 A (외부 노출/계약 핵심) — 약 70 view

| 영역 | 뷰 수 | 현재 명시 | 필요 작업 |
|------|-------|-----------|-----------|
| `marketpulse/api` (v2) | 25 (cards 7 + overview 11 + news 1 + i18n 1 + health 4 + helper 1) | 10 | 15 view에 `@extend_schema(responses=...)` 추가. 이미 일부 적용. |
| `chainsight/api` | 10 | 8 | 2 view 보강 (`SignalFeedView`, watchlist actions) |
| `portfolio/api` (Coach E1~E6) | 12 | 0 | **0 → 12 전수 추가**. 요청/응답 serializer 필요. 현재 다수 `@api_view` 함수 형태 → `@extend_schema` 데코로 응답 정의. |
| `validation/api` | 6 | 0 | 6 view 추가 (peer preset/LLM filter 응답 구조 필요) |
| `news/api` (NewsViewSet) | 2 + 액션 | 3 | 액션별 `@extend_schema` 보강 |
| `api_request` | 6 | 6 | ✅ 완료 |

#### 우선순위 B (내부/관리/대량) — 약 140 view

| 영역 | 뷰 수 | 현재 명시 | 필요 작업 |
|------|-------|-----------|-----------|
| `stocks/views*` (8 파일) | 43 | 0 | **0 → 43 전수**. 가장 비용 큼. MVP/Indicators/Fundamentals/Screener/Exchange/EOD 6개 도메인. 도메인별 PR 분할 권장. |
| `serverless/views.py` | ≈ 105 (함수형, 단일 파일) | 7 | **≈ 98 추가**. 단일 파일 메가-뷰. Admin 12 + Movers/Breadth/Heatmap/Presets/Alerts/ETF/LLM/Institutional 도메인별 분할 필요. |
| `serverless/views_admin.py` | 12 | 0 | 12 view 추가 (admin 응답 표준화) |
| `users/views.py` | 27 (+jwt 6) | 3 | 24+ view 추가. Portfolio/Watchlist serializer 활용 가능 (이미 존재) |
| `users/jwt_views.py` | 6 | 0 | 6 view 추가. simplejwt 표준 응답 + 커스텀 응답 |
| `macro/views.py` | 11 | 0 | 11 view 추가. Market Pulse v1 — v2로 deprecate 예정인지 결정 필요 (작업량 회수 가능) |
| `thesis/views/*` (3 파일) | 20 | 0 | ViewSet 3 + APIView 11 — viewset은 action별 `@extend_schema_view` 권장 |
| `rag_analysis/views.py` | 15 | 3 | 12 view 추가 |
| `sec_pipeline/views.py` | 2 | 0 | 2 view 추가 |

#### Step 2 총 작업량 추정

| 항목 | 수치 |
|------|------|
| 총 뷰/함수 수 | **약 270** |
| 현재 `@extend_schema` 적용 | **약 38** |
| **신규 추가 필요** | **약 230** |
| serializer 추가 필요 (응답 모델 부재) | 약 80~120 추정 (Coach E1~E6, serverless, Portfolio Coach 도메인은 대부분 dict 반환 → `inline_serializer` 또는 dataclass 기반 serializer 신규 작성) |

### Step 3 — 품질 관문 (선택)

| 작업 | 작업량 | 비고 |
|------|--------|------|
| `DISABLE_ERRORS_AND_WARNINGS = False` 전환 | 1 PR + 전수 마이그레이션 후 | warning 0건 달성 후 |
| CI에 `manage.py spectacular --validate --fail-on-warn` 추가 | 1 PR | regression 차단 |
| `contracts/openapi/` 디렉토리에 schema export 자동화 | 1 PR + Beat/CI 통합 | CLAUDE.md "Contract-Driven Development" 정책과 정합 |
| Postman/Insomnia collection 자동 생성 | 옵션 | spectacular 후 |

### Step 4 — 운영/문서

| 작업 | 작업량 |
|------|--------|
| 인증 정책 명시 (`SPECTACULAR_SETTINGS.AUTHENTICATION_WHITELIST` + JWT Bearer 명시) | 소 |
| API 변경 로그 자동화 (schema diff) | 중 |
| README/docs에 Swagger 링크 안내 | 소 |

---

## 작업량 종합 요약

| Step | 항목 | 추정 작업량 | 우선순위 |
|------|------|-------------|----------|
| 0 | 인프라 셋업 | ✅ 완료 | — |
| 1 | v1 schema URL 노출 | 1~2시간 (config/urls.py + 텍스트) | High (현재 v1 spec 미노출) |
| 2-A | 외부 노출 핵심 70 view 데코레이터 + serializer | 1~2주 (PR 5~6개로 분할) | High |
| 2-B | 내부/대량 140 view 데코레이터 + serializer | 3~5주 (PR 10+개) | Medium (`DISABLE_ERRORS_AND_WARNINGS=True` 유지 시 점진 가능) |
| 3 | CI/품질 관문 | 1주 (전수 마이그레이션 후) | Medium |
| 4 | 운영/문서 | 2~3일 | Low |

**결론**:
- 인프라/도구는 갖춰져 있으며 v2 marketpulse + chainsight + admin은 신뢰 가능한 schema 제공.
- 가장 큰 부채는 `stocks` (43) + `serverless/views.py` (≈105) + `users` (33) + `thesis` (20) — 합 200+ view에서 명시 데코레이터 0~매우 적음.
- 빠른 회수: **Step 1** (v1 schema URL 노출) + **Step 2-A** (외부 노출 70 view 우선) 적용 시 1~2주 안에 "외부 계약 영역만 정확한 OpenAPI 보장" 상태 도달.
- 전수 적용은 약 4~7주, serializer 신규 작성 비용 포함.

---

## 부록: 참조 위치

- `config/urls.py:19-23` — spectacular import
- `config/urls.py:62-72` — schema/swagger/redoc URL (v2 only)
- `config/settings.py:205-206` — INSTALLED_APPS 등록
- `config/settings.py:363` — DEFAULT_SCHEMA_CLASS
- `config/settings.py:370-` — SPECTACULAR_SETTINGS
- `config/settings.py:390` — DISABLE_ERRORS_AND_WARNINGS=True
- `pyproject.toml` — drf-spectacular ^0.29.0, sidecar ^2026.4.14
- `portfolio/urls.py` — 빈 모듈 (#65로 legacy 5건 제거 완료)
- `graph_analysis/` — urls.py 미존재 (CLAUDE.md 상태와 일치, API 미구현)
