# API 문서 감사 보고서

- 생성일: 2026-05-24
- 대상 브랜치: `security/c2-backend-deps` (직전 검토 분기 `slice14` 기준 변화 없음 — 보안 의존성 비파괴 업그레이드만 적용)
- 작성 방식: 읽기 전용 (코드 수정 없음)
- 범위: Django/DRF 백엔드 전체 URL 라우팅 + `drf-spectacular` 도입 상태

---

## 현재 상태

### 1) 도구 설치 상태

| 항목 | 상태 | 위치 / 비고 |
|------|------|-------------|
| `drf-spectacular` | OK (`^0.29.0`) | `pyproject.toml:39` |
| `drf-spectacular-sidecar` | OK (`^2026.4.14`) | `pyproject.toml:40` |
| `INSTALLED_APPS` 등록 | OK (`drf_spectacular`, `drf_spectacular_sidecar`) | `config/settings.py:205-206` |
| `DEFAULT_SCHEMA_CLASS` | OK (`drf_spectacular.openapi.AutoSchema`) | `config/settings.py:363` |
| `SPECTACULAR_SETTINGS` | OK (TITLE=`Stock-Vis Market Pulse v2 API`, VERSION=`2.0`) | `config/settings.py:370-418` |
| `SCHEMA_PATH_PREFIX` | `r'/api/v[12]'` — v1/v2 모두 수집 | `config/settings.py:382` |
| `DISABLE_ERRORS_AND_WARNINGS` | `True` (graceful fallback 정책) | `config/settings.py:390` |
| `ENUM_NAME_OVERRIDES` | thesis/news/chainsight enum 4건 | `config/settings.py:394-417` |
| `requirements.txt` | spectacular 키워드 부재 | Poetry export 미반영 (Docker 빌드 영향 시 확인 필요) |
| `drf-yasg` | 미설치 | spectacular 단독 정책 (의도된 선택) |
| Swagger/OpenAPI 스펙 자동 생성 | **가능 (v2 경로만 노출)** | `config/urls.py:62-72` |

### 2) Swagger / OpenAPI 노출 경로

| 경로 | 뷰 | 비고 |
|------|----|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 spec |
| `/api/v2/swagger/` | `SpectacularSwaggerView` (sidecar) | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` (sidecar) | ReDoc |

핵심 제약:
- v1 schema URL 미노출. `SCHEMA_PATH_PREFIX` 정규식은 v1/v2 모두 캡처하지만, 외부에서 사용 가능한 schema URL은 v2 네임스페이스 안에만 존재.
- `SERVE_INCLUDE_SCHEMA = False` — UI 안에 spec 다운로드 링크 비포함.
- `DISABLE_ERRORS_AND_WARNINGS = True` — 명시 데코레이터 없는 view는 string body로 무성공 통과 → schema 정확도가 사실상 v2 marketpulse + chainsight + admin에 한정됨.

### 3) `@extend_schema` 명시 적용 현황 (코드 베이스 전수 grep)

| 파일 | `@extend_schema` 횟수 |
|------|-----------------------|
| `api_request/admin_views.py` | 5 |
| `chainsight/api/views.py` | 7 |
| `config/settings.py` | 2 (`SPECTACULAR_SETTINGS` 내부 참조) |
| `marketpulse/api/views/cards.py` | 1 |
| `marketpulse/api/views/health.py` | 1 |
| `marketpulse/api/views/i18n.py` | 1 |
| `marketpulse/api/views/news_refresh.py` | 1 |
| `marketpulse/api/views/overview.py` | 1 |
| `news/api/views.py` | 2 |
| `rag_analysis/views.py` | 2 |
| `serverless/views.py` | 6 |
| `users/views.py` | 2 |
| **합계** | **31** (12개 파일) |

> 직전 5/23 감사 대비: 동일 (코드 변화 없음). C-2 보안 의존성 PR은 spectacular 적용 view를 변경하지 않음.

---

## 엔드포인트 목록 (앱별 테이블)

### 마운트 포인트 (`config/urls.py`)

| Prefix | include 대상 | 비고 |
|--------|---------------|------|
| `/api/v1/users/` | `users.urls` | JWT + 세션 + favorites + portfolio + interests + watchlist |
| `/api/v1/stocks/` | `stocks.urls` | dashboard/detail + MVP + 펀더멘털 + 스크리너 + 시세 + EOD |
| `/api/v1/news/` | `news.api.urls` | `NewsViewSet` (DRF DefaultRouter) |
| `/api/v1/macro/` | `macro.urls` | Market Pulse v1 (거시경제) |
| `/api/v1/rag/` | `rag_analysis.urls` | DataBasket + Session + Monitoring |
| `/api/v1/serverless/` | `serverless.urls` | Admin + Movers + Breadth + Heatmap + Presets + Filters + Alerts + ETF + LLM + Institutional + Regulatory + Patent |
| `/api/v1/thesis/` | `thesis.urls` | 가설 통제실 (ViewSet + nested router + conversation/alerts) |
| `/api/v1/validation/` | `validation.api.urls` | 1차 검증 |
| `/api/v1/chainsight/` | `chainsight.api.urls` | Chain Sight v2 + Watchlist |
| `/api/v1/sec-pipeline/` | `sec_pipeline.urls` | SEC 10-K 대시보드 + Filing |
| `/api/v1/` | `api_request.urls` | Provider admin (status/rate-limit/cache/test/config) |
| `/api/` | `portfolio.urls` | **빈 모듈** (`urlpatterns = []`, #65 legacy 제거 완료) |
| `/api/v1/` | `portfolio.api.urls` (namespace `portfolio_api`) | Coach E1~E6 |
| `/api/v2/market-pulse/` | `marketpulse.api.urls` | Market Pulse v2 |
| `/api/v2/{schema,swagger,redoc}/` | `drf_spectacular.views.*` | OpenAPI 노출 (v2 only) |
| `/`, `/health/`, `/admin/` | `config.views` / Django admin | 루트/헬스/관리자 |

### 앱별 엔드포인트 집계

> 카운트 기준: 각 `urls.py`의 `path(...)` 라인 수 (실측). DRF `router.register()`는 별도 표기.

| 앱 | `path()` 수 | DRF router | 명시 데코레이터 | 비고 |
|----|-------------|------------|------------------|------|
| **users** | 35 | 0 | 2 / ≈33 | JWT 7 + 세션 6 + favorites 3 + portfolio 9 + interests 2 + watchlist 8 |
| **stocks** | 39 | 0 | **0 / 43+** | dashboard/detail 3 + MVP 4 + indicators 3 + search 3 + market-movers 1 + 펀더멘털 5 + 스크리너 6 + 시세 5 + EOD 3 + sync/chart 등 (8 파일) |
| **news** | 1 (include) | 1 ViewSet (`NewsViewSet`) | 2 (액션 데코) | `@action` 30회 — 기본 5 + custom action 다수 |
| **macro** | 10 | 0 | **0 / 10** | pulse, fear-greed, interest-rates, inflation, global-markets, calendar, vix, sectors, sync, sync/status |
| **rag_analysis** | 15 | 0 | 2 / 15 | DataBasket 6 + Session 4 + Monitoring 5 |
| **serverless** | 64 | 0 | 6 / ≈105 | Admin 12 + Movers 4 + Sync 2 + Keywords 4 + Breadth 3 + Heatmap 3 + Presets 7 + Filters 1 + Screener 1 + Alerts 6 + Thesis 4 + ETF 9 + LLM 4 + Institutional 3 + Regulatory/Patent 2 + Health 1 |
| **thesis** | 11 | 3 routers (root + nested `premise` + nested `indicator`) | **0 / 20+** | conversation 4 + dashboard 2 + alerts 2 + ViewSet 액션 (`@action` 5회) |
| **validation** | 6 | 0 | **0 / 6** | symbol별 summary/metrics/leader/presets/peer-preference/llm-filter |
| **chainsight** | 7 | 1 router (`WatchlistViewSet`, `@action` 5회) | 7 / 10 | seeds/sector/signals/trace + neighbors/graph/suggestions + watchlist |
| **sec_pipeline** | 2 | 0 | **0 / 2** | admin/dashboard + filing/<symbol> |
| **api_request** | 6 | 0 | 5 / 6 (≈ **83%**) | health + admin/providers/{status,rate-limits,cache,test,config} |
| **portfolio** (`portfolio.urls`) | 0 | 0 | — | 빈 모듈 |
| **portfolio_api** (`portfolio.api.urls`) | 6 | 0 | **0 / 6** | coach/e1 ~ coach/e6 (DRF function-based) |
| **marketpulse v2** (`marketpulse.api.urls`) | 5 | 0 | 5 / ≈25 (helper 포함) | overview / cards/<id>/detail / news/refresh / i18n / health |
| **config (root)** | 3 | — | — | `/`, `/health/`, `/admin/` |
| **drf-spectacular** | 3 | — | — | `/api/v2/schema|swagger|redoc/` |
| **graph_analysis** | — | — | — | `urls.py` 미존재 — `views.py`는 존재하나 `config/urls.py` 미연결 (CLAUDE.md 표기와 일치, API 미구현) |

**총 명시 엔드포인트 추정**: `path()` 라인 직접 카운트 **≈ 210건** + DRF router 자동 생성 (`NewsViewSet`, `ThesisViewSet` + nested 2개, `WatchlistViewSet` → 약 20~30건 추가). **합계 ≈ 230~240**.

> 변화: 5/23 보고서와 동일. C-2 보안 의존성 분기에서 URL 라우팅 변경 0건 확인.

---

## 도입 작업 목록

### Step 0 — 인프라 (완료)

| 작업 | 상태 |
|------|------|
| `drf-spectacular` + sidecar 설치 (Poetry) | OK |
| `INSTALLED_APPS` 등록 | OK |
| `DEFAULT_SCHEMA_CLASS` 지정 | OK |
| `SPECTACULAR_SETTINGS` 정의 + enum override | OK (v2 기준 메타데이터) |
| Swagger/ReDoc URL 노출 | OK (**v2만**) |

### Step 1 — v1 schema 노출 분리 (소)

| 작업 | 작업량 | 비고 |
|------|--------|------|
| `/api/v1/schema/`, `/api/v1/swagger/`, `/api/v1/redoc/` 추가 | `config/urls.py` 3 라인 + name 충돌 회피 | 또는 `/api/schema/` 단일화 (현 `SCHEMA_PATH_PREFIX`가 v1/v2 모두 캡처하므로 spec 한 개로 통합 가능) |
| `SPECTACULAR_SETTINGS.TITLE/DESCRIPTION` 일반화 | 텍스트 수정 | `"Market Pulse v2"` → `"Stock-Vis API (v1+v2)"`. v1을 1급 시민으로 노출하는 정책 결정 선행 필요 |
| `requirements.txt` 동기화 | 옵션 | Docker 빌드가 Poetry export를 사용하면 불필요 |

### Step 2 — `@extend_schema` 데코레이터 추가 범위 (대)

> **선결 조건**: `DISABLE_ERRORS_AND_WARNINGS = True` 유지 여부.
> - 유지 = 점진 도입 가능 (현 정책, 권장)
> - 해제 = 전수 마이그레이션 후 한 번에 강제 → 빌드 차단 가능성

#### 우선순위 A — 외부 노출/계약 핵심 (약 70 view)

| 영역 | 뷰 수 | 현재 명시 | 필요 작업 |
|------|-------|-----------|-----------|
| `marketpulse/api` (v2) | ≈ 25 (cards 7 + overview 11 + news 1 + i18n 1 + health 4 + helper 1) | 5 | 약 20 view에 `@extend_schema(responses=...)` 추가 |
| `chainsight/api` | 10 | 7 | 3 view 보강 (`SignalFeedView`, watchlist `@action` 일부) |
| `portfolio/api` (Coach E1~E6) | 6 함수 + serializer 부재 | 0 | **6 → 6 전수**. function-based DRF view → `@extend_schema` + `inline_serializer` 또는 신규 serializer 작성 |
| `validation/api` | 6 | 0 | 6 view 추가 (peer preset / LLM filter 응답 구조 필요) |
| `news/api` (`NewsViewSet`) | 2 + `@action` 30 | 2 | 액션별 `@extend_schema` 보강 (`@extend_schema_view` 권장) |
| `api_request` | 6 | 5 | 잔여 1 보강 |

#### 우선순위 B — 내부/관리/대량 (약 140 view)

| 영역 | 뷰 수 | 현재 명시 | 필요 작업 |
|------|-------|-----------|-----------|
| `stocks/views*` (8 파일) | 43 | 0 | **43 전수 추가**. 가장 비용 큼. MVP/Indicators/Fundamentals/Screener/Exchange/EOD 6개 도메인. 도메인별 PR 분할 권장 |
| `serverless/views.py` | ≈ 53 (함수형 단일 파일, `def` 53개) | 6 | ≈ 47 추가. Admin/Movers/Breadth/Heatmap/Presets/Alerts/ETF/LLM/Institutional 도메인별 분할 필요 |
| `serverless/views_admin.py` | 12 | 0 | 12 view 추가 (admin 응답 표준화) |
| `users/views.py` | ≈ 27 | 2 | 약 25 추가. Portfolio/Watchlist serializer 일부 재활용 가능 |
| `users/jwt_views.py` | 6 | 0 | 6 추가. simplejwt 표준 응답 + 커스텀 |
| `macro/views.py` | 10 | 0 | 10 추가. Market Pulse v1 → v2 deprecate 정책 결정 선행 필요 (작업량 회수 가능성 검토) |
| `thesis/views/*` (3 파일) | ≈ 20 | 0 | ViewSet 3 + APIView 11 — viewset은 액션별 `@extend_schema_view` 권장 |
| `rag_analysis/views.py` | 15 | 2 | 13 추가 |
| `sec_pipeline/views.py` | 2 | 0 | 2 추가 |

#### Step 2 총 작업량 추정

| 항목 | 수치 |
|------|------|
| 총 뷰/함수 수 | **약 270** |
| 현재 `@extend_schema` 적용 | **31** (12 파일, 5/23 동일) |
| **신규 추가 필요** | **약 230** |
| serializer 신규 작성 필요 | **80~120 추정** — Coach E1~E6, serverless, Portfolio 도메인 대부분 dict 반환 → `inline_serializer` 또는 dataclass 기반 serializer 신규 작성 |

### Step 3 — 품질 관문 (선택)

| 작업 | 작업량 | 비고 |
|------|--------|------|
| `DISABLE_ERRORS_AND_WARNINGS = False` 전환 | 1 PR | warning 0건 달성 후 |
| CI에 `manage.py spectacular --validate --fail-on-warn` 추가 | 1 PR | regression 차단 게이트 |
| `contracts/openapi/` 에 schema export 자동화 | 1 PR + Beat/CI 통합 | CLAUDE.md "Contract-Driven Development" 정책과 정합 |
| Postman/Insomnia collection 자동 생성 | 옵션 | spectacular 정착 이후 |

### Step 4 — 운영/문서

| 작업 | 작업량 |
|------|--------|
| 인증 정책 명시 (`SPECTACULAR_SETTINGS.AUTHENTICATION_WHITELIST` + JWT Bearer 명시) | 소 |
| API 변경 로그 자동화 (schema diff) | 중 |
| README/`sub_claude_md/api-endpoints.md`에 Swagger 링크 안내 | 소 |

---

## 작업량 종합 요약

| Step | 항목 | 추정 작업량 | 우선순위 |
|------|------|-------------|----------|
| 0 | 인프라 셋업 | 완료 | — |
| 1 | v1 schema URL 노출 + TITLE 일반화 | 1~2시간 | High (현재 v1 spec 미노출) |
| 2-A | 외부 노출 70 view 데코레이터 + serializer | 1~2주 (PR 5~6개) | High |
| 2-B | 내부/대량 140 view 데코레이터 + serializer | 3~5주 (PR 10+개) | Medium (현 정책 유지 시 점진 가능) |
| 3 | CI/품질 관문 | 1주 (전수 마이그레이션 후) | Medium |
| 4 | 운영/문서 | 2~3일 | Low |

**결론**:
- 인프라/도구는 모두 갖춰져 있고 v2 marketpulse + chainsight + admin은 신뢰 가능한 schema를 제공.
- 가장 큰 부채: `stocks` (43) + `serverless/views.py` (≈53 함수) + `serverless/views_admin.py` (12) + `users` (33) + `thesis` (20) + `macro` (10) — 합 ≈ 180 view에서 명시 데코레이터 0~매우 적음.
- 빠른 회수: **Step 1** + **Step 2-A** 적용 시 1~2주 안에 "외부 계약 영역만 정확한 OpenAPI 보장" 상태 도달.
- 전수 적용 시 약 4~7주 (serializer 신규 작성 비용 포함).
- 5/23 ↔ 5/24 변화: C-2 보안 의존성 분기에서 URL 라우팅·view·spectacular 적용 view 모두 변경 0건. 작업 추정은 그대로 유효.

---

## 부록: 참조 위치

- `config/urls.py:19-23` — spectacular import
- `config/urls.py:37-59` — `/api/v1/*` include 마운트
- `config/urls.py:62-72` — schema/swagger/redoc URL (v2 only)
- `config/settings.py:205-206` — INSTALLED_APPS 등록
- `config/settings.py:363` — DEFAULT_SCHEMA_CLASS
- `config/settings.py:370-418` — SPECTACULAR_SETTINGS
- `config/settings.py:382` — `SCHEMA_PATH_PREFIX = r'/api/v[12]'`
- `config/settings.py:390` — `DISABLE_ERRORS_AND_WARNINGS = True`
- `config/settings.py:394-417` — `ENUM_NAME_OVERRIDES` (thesis/news/chainsight)
- `config/spectacular_enums.py` — enum override 보조 모듈
- `pyproject.toml:39-40` — `drf-spectacular ^0.29.0`, sidecar `^2026.4.14`
- `portfolio/urls.py` — 빈 모듈 (#65로 legacy 5건 제거 완료)
- `graph_analysis/` — `urls.py` 미존재 (CLAUDE.md 상태와 일치, API 미구현)
- 직전 보고서: `docs/nightly_auto_system/reports/5월/23일/api_docs_audit.md`
