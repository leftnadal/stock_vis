# API 문서 감사 보고서

> 생성일: 2026-06-05
> 대상: Stock-Vis Backend (Django REST Framework)
> 모드: **읽기 전용 감사** (코드 변경 없음)
> 감사자: nightly_auto_system

---

## 요약 (TL;DR)

- **drf-spectacular 0.29.0 + sidecar 이미 설치·설정 완료**. 신규 도입 작업은 불필요하며, **기존 자산 위에 커버리지를 확장**하는 작업이 핵심.
- OpenAPI 스키마 자동 생성 **가능** (`/api/v2/schema/`), Swagger UI(`/api/v2/swagger/`), ReDoc(`/api/v2/redoc/`) 모두 라이브.
- 전체 **약 268개** REST 엔드포인트 중 `@extend_schema` 명시 문서화는 **약 35개 뷰(≈13%)** 에 그침.
- 나머지 v1 엔드포인트는 `DISABLE_ERRORS_AND_WARNINGS=True` 정책으로 **graceful fallback(string body)** 노출 → 스키마에 나타나지만 **요청/응답 형태가 부정확**.
- 우선 보강 대상: **stocks(39), serverless(64), news(32), thesis(28)** — 엔드포인트 수가 많고 문서화율이 0%에 가까운 4개 앱.

---

## 현재 상태

### 1. 문서화 도구 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| drf-spectacular | ✅ 설치 (`^0.29.0`) | `pyproject.toml` |
| drf-spectacular-sidecar | ✅ 설치 (`^2026.4.14`) | `pyproject.toml` (Swagger/ReDoc 정적 자산) |
| drf-yasg | ❌ 미사용 | — |
| INSTALLED_APPS 등록 | ✅ | `config/settings.py:212-213` (`drf_spectacular`, `drf_spectacular_sidecar`) |
| DEFAULT_SCHEMA_CLASS | ✅ | `config/settings.py:370` → `drf_spectacular.openapi.AutoSchema` |
| SPECTACULAR_SETTINGS | ✅ | `config/settings.py:377-425` |

→ **requirements.txt는 없음**(Poetry 기반). 의존성은 `pyproject.toml`이 단일 소스.

### 2. Swagger / OpenAPI 스펙 자동 생성 가능 여부

**가능.** `config/urls.py:61-72`에 3개 엔드포인트 라이브:

| 경로 | 뷰 | 용도 |
|------|-----|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 스펙(YAML/JSON) |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc |

### 3. 현재 SPECTACULAR_SETTINGS 핵심 (config/settings.py:377-425)

- `TITLE`: "Stock-Vis Market Pulse v2 API" — **타이틀이 Market Pulse v2 한정**으로 좁게 설정됨. 전체 API 문서로 확장 시 갱신 필요.
- `VERSION`: "2.0"
- `SCHEMA_PATH_PREFIX`: `r'/api/v[12]'` — v1·v2 경로 모두 스캔 대상에 포함됨 (전체 노출 의도는 이미 반영).
- `SERVE_INCLUDE_SCHEMA`: False
- `COMPONENT_SPLIT_REQUEST`: True
- `SWAGGER_UI_DIST`/`REDOC_DIST`: SIDECAR (오프라인 정적 자산)
- ⚠️ **`DISABLE_ERRORS_AND_WARNINGS`: True** — "unable to guess serializer" 등 fallback noise를 의도적으로 무음 처리. 핵심 영역(marketpulse, chainsight, api_request admin)만 `@extend_schema`로 정상화하고, 나머지는 string body fallback으로 노출하는 **점진적 전략**이 이미 명문화됨 (settings.py:393-397 주석).
- `ENUM_NAME_OVERRIDES`: 4개 enum 충돌 해결 (thesis category/status, news category, chainsight SavedPath status).
- `config/spectacular_enums.py`, `config/serializers.py`(에러 envelope) 보조 모듈 존재.

> **결론**: "도입"이 아니라 **"커버리지 확장 + 타이틀 정정"** 단계. 인프라는 완비됨.

---

## 엔드포인트 목록 (앱별 테이블)

> 라우팅 진입점: `config/urls.py`. 디렉터리 구조는 CLAUDE.md 기준(`packages/shared/`, `apps/`, `services/`)과 일치.
> 엔드포인트 수는 URL 패턴 + ViewSet 자동 생성 라우트(list/retrieve/create/update/destroy/@action) 합산 추정치.

| 앱 (URL prefix) | urls.py 위치 | 엔드포인트 수 | `@extend_schema` 적용 뷰 | 문서화율 |
|------|------|:---:|:---:|:---:|
| **stocks** (`/api/v1/stocks/`) | `packages/shared/stocks/urls.py` | 39 | 0 | ❌ 0% |
| **users** (`/api/v1/users/`) | `packages/shared/users/urls.py` | 35 | 2 | 🔴 ~6% |
| **news** (`/api/v1/news/`) | `services/news/api/urls.py` | ~32 (list+retrieve + @action 30) | 2 | 🔴 ~6% |
| **macro** (`/api/v1/macro/`) | `apps/market_pulse/urls.py` | 10 | 0 | ❌ 0% |
| **market_pulse v2** (`/api/v2/market-pulse/`) | `apps/market_pulse/api/urls.py` | 5 | 5 | ✅ 100% |
| **rag_analysis** (`/api/v1/rag/`) | `services/rag_analysis/urls.py` | 15 | 2 | 🔴 ~13% |
| **serverless** (`/api/v1/serverless/`) | `services/serverless/urls.py` | 64 | 6 | 🔴 ~9% |
| **thesis** (`/api/v1/thesis/`) | `thesis/urls.py` | ~28 (3 ViewSet + 8 path) | 0 (뷰 2 @action) | ❌ ~0% |
| **validation** (`/api/v1/validation/`) | `services/validation/api/urls.py` | 6 | 0 | ❌ 0% |
| **chainsight** (`/api/v1/chainsight/`) | `apps/chain_sight/api/urls.py` | ~13 (7 path + Watchlist ViewSet 6) | 7 | 🟡 ~54% |
| **sec_pipeline** (`/api/v1/sec-pipeline/`) | `services/sec_pipeline/urls.py` | 2 | 0 | ❌ 0% |
| **api_request** (`/api/v1/`) | `packages/shared/api_request/urls.py` | 6 | 5 | ✅ ~83% |
| **portfolio coach** (`/api/v1/coach/`) | `apps/portfolio/api/urls.py` | 6 | 6 | ✅ 100% |
| **iron_trading** (`/api/v1/iron-trading/`) | `integrations/iron_trading/urls.py` | 2 (1 unique) | 0 | ❌ 0% |
| **config** (`/`, `/api/v2/schema/` 등) | `config/urls.py` | 5 (root/health/schema/swagger/redoc) | — | — |
| **합계** | | **≈ 268** | **≈ 35 뷰** | **≈ 13%** |

### 앱별 상세

#### stocks (39) — `packages/shared/stocks/urls.py`
- 페이지/검색: `` (dashboard), `stock/<symbol>/`, `search/`
- 탭 데이터 API: chart / overview / balance-sheet / income-statement / cashflow (`api/<tab>/<symbol>/`)
- 동기화: `api/sync/<symbol>/`
- MVP: `api/mvp/stocks/`, `api/mvp/stock/<symbol>/`, `api/mvp/rag/<symbol>/`, `api/mvp/sectors/`
- 기술지표: `api/indicators/<symbol>/`, `api/signal/<symbol>/`, `api/indicators/compare/`
- 검색: `api/search/symbols/`, `api/search/validate/<symbol>/`, `api/search/popular/`
- Market Movers: `api/market-movers/`
- Fundamentals: key-metrics / ratios / dcf / rating / all (`api/fundamentals/*/<symbol>/`)
- Screener: `api/screener/` + large-cap / high-dividend / sector / low-beta / exchange
- Quotes: index / `<symbol>` / batch / major-indices / sector-performance (`api/quotes/*`)
- EOD: `eod/dashboard/`, `eod/signal/<signal_id>/`, `eod/pipeline/status/`
- 뷰 파일이 9개로 분할(`views_*.py`) — `@extend_schema` 0건. **최대 보강 우선순위.**

#### users (35) — `packages/shared/users/urls.py`
- JWT 7종(signup/login/logout/refresh/verify/change-password/profile)
- 세션 인증(레거시) 6종(me/users/public_user/change_password/login/logout)
- 즐겨찾기 3종
- 포트폴리오 9종(`portfolio/*`, symbol 기반 포함)
- 관심사 2종, Watchlist 8종

#### news (~32) — `services/news/api/views.py` (`NewsViewSet`, ReadOnlyModelViewSet)
- 루트 `r""` 등록 → list + retrieve 자동 생성
- **@action 30개** (모두 detail=False): `stock/<symbol>`, `stock/<symbol>/sentiment`, `all`, `daily-keywords`, `daily-keywords/generate`(POST), `keyword-detail`, `news-events`, `news-events/impact-map` 등
- DefaultRouter 사용 → 라우트 자동 생성. `@extend_schema` 2건만.

#### serverless (64) — `services/serverless/urls.py` (함수 기반 뷰 다수)
- Admin Dashboard 12 / Market Movers 2 / Sync 2 / Keywords 4 / Breadth 3 / Heatmap 3
- Presets 7 / Filters 1 / Advanced Screener 1 / Alerts 6 / Thesis 4
- Chain Sight ETF 9 / LLM Relations 4 / Institutional 3 / Regulatory 1 / Patent 1 / Health 1
- **가장 엔드포인트가 많은 앱**. 함수 기반 뷰라 `@extend_schema` 데코레이터를 함수마다 부착해야 함.

#### thesis (~28) — `thesis/urls.py` (ViewSet 3개 + nested router)
- `ThesisViewSet`(ModelViewSet, +@action 1) / `ThesisPremiseViewSet`(ModelViewSet) / `ThesisIndicatorViewSet`(ModelViewSet, +@action 1)
- nested: `<thesis_id>/premises/`, `<thesis_id>/indicators/`
- 명시 path: conversation start/respond/news-issues/suggest, dashboard, readings, alerts list/read
- ENUM override는 이미 설정됨(category/status)이나 **뷰 `@extend_schema` 0건.**

#### market_pulse v2 (5) — `apps/market_pulse/api/views/*.py` ✅
- overview / cards/<card_id>/detail / news/refresh / i18n / health — **각 뷰 100% `@extend_schema`.** (현재 SPECTACULAR_SETTINGS TITLE이 이 앱 기준)

#### chainsight (~13) — `apps/chain_sight/api/views.py` 🟡
- seeds / sector graph / signals / trace / neighbors / graph / suggestions (7) + WatchlistViewSet(6)
- `@extend_schema` 7건 — 절반 이상 커버.

#### api_request (6) ✅ / portfolio coach (6) ✅
- 둘 다 거의/완전 문서화 완료.

#### validation (6) / sec_pipeline (2) / macro v1 (10) / iron_trading (2)
- `@extend_schema` 0건. 엔드포인트 수가 적어 보강 비용은 낮음.

---

## 도입(확장) 작업 목록

> 도구는 이미 도입 완료 상태이므로, 실제 작업은 **(A) 전역 설정 정정 + (B) 앱별 `@extend_schema` 커버리지 확장** 두 갈래.

### A. 전역 설정 정정 (저비용 / 즉시 효과)

| # | 작업 | 위치 | 비고 |
|---|------|------|------|
| A-1 | `TITLE`을 "Stock-Vis Market Pulse v2 API" → 전체 API명으로 변경 | `config/settings.py:378` | 전체 문서 의도 반영 |
| A-2 | `DESCRIPTION`/`TAGS`를 앱 단위로 확장(현재 Market Pulse v2 1개 태그만) | `config/settings.py:379-392` | 앱별 그룹핑 가독성 |
| A-3 | (선택) `DISABLE_ERRORS_AND_WARNINGS` 일시 해제 후 `spectacularcheck`로 fallback 경고 목록 확보 → 보강 우선순위 산정 | settings.py:397 | **읽기 전용 진단용**, 운영 영구 변경 아님 |

> A-3은 `python manage.py spectacular --file /tmp/schema.yml --validate` 실행 시 경고가 표면화되어 미문서화 뷰를 정량 식별 가능.

### B. 앱별 `@extend_schema` 데코레이터 추가 범위

권장 우선순위(엔드포인트 수 × 문서화율 갭 기준):

| 우선 | 앱 | 미문서화 추정 | 작업 형태 | 예상 작업량 |
|:---:|------|:---:|------|:---:|
| 1 | **serverless** | ~58 | 함수 기반 뷰마다 `@extend_schema(responses=…, summary=…)` | 大 (2~3일) |
| 2 | **stocks** | 39 | 9개 `views_*.py` 클래스 뷰에 부착 + Serializer 명시 | 大 (2일) |
| 3 | **news** | ~30 | ViewSet `@action`별 + `@extend_schema_view` | 中 (1~1.5일) |
| 4 | **thesis** | ~28 | ViewSet 3종 `@extend_schema_view` + path 뷰 | 中 (1일) |
| 5 | **users** | ~33 | JWT/세션/포트폴리오/watchlist | 中 (1일) |
| 6 | **rag_analysis** | ~13 | DataBasket/Session/Monitoring 뷰 (SSE stream 주의) | 小 (0.5일) |
| 7 | **macro v1** | 10 | 클래스 뷰 10종 | 小 (0.5일) |
| 8 | **chainsight** | ~6 | 잔여 WatchlistViewSet 등 | 小 (0.3일) |
| 9 | **validation / sec_pipeline / iron_trading** | 10 | 합산 소량 | 小 (0.3일) |

### 작업 단위별 체크리스트 (각 뷰 공통)

- [ ] `@extend_schema(summary, description, responses, parameters)` 부착
- [ ] 응답 Serializer 명시 (현재 다수 뷰가 raw dict 반환 → inline serializer 또는 `OpenApiResponse` 필요)
- [ ] path 파라미터(`<str:symbol>` 등)에 `OpenApiParameter` 설명 부여
- [ ] ViewSet은 `@extend_schema_view`로 list/retrieve/create/... 일괄 처리
- [ ] 함수 기반 뷰(serverless)는 `@api_view` + `@extend_schema` 조합 확인
- [ ] enum 충돌 발생 시 `ENUM_NAME_OVERRIDES`(settings.py:401) 추가

### 예상 총 작업량

- **전역 설정(A)**: 0.5일 (저위험)
- **앱별 커버리지(B) 전량**: 약 **8~10 영업일** (1인 기준)
- **MVP 범위**(serverless·stocks·news·thesis 4개 앱 = 전체 엔드포인트의 ~60%): 약 **5~6 영업일**

---

## 리스크 / 주의사항

1. **응답 envelope 표준화 연동**: `config/exception_handler.custom_exception_handler` + `config/serializers.py`(에러 envelope `{detail, code?, errors?, status_code}`)가 이미 존재. 문서화 시 정상 응답뿐 아니라 **에러 응답 스키마도 `@extend_schema(responses={400: ErrorSerializer})`로 일관 반영** 필요.
2. **raw dict 반환 뷰 다수**: 상당수 v1 뷰가 Serializer 없이 dict를 반환 → spectacular가 형태를 추론 불가(현재 string fallback). 정확한 스키마를 위해 **응답 Serializer 신설 또는 inline 정의 작업이 동반**됨 (단순 데코레이터 추가보다 비용 큼).
3. **SSE 스트리밍 뷰**(`rag_analysis/ChatStreamView`): OpenAPI 표현이 제한적 → `@extend_schema(responses=OpenApiTypes.STR)` 또는 문서 주석으로 별도 처리.
4. **레거시/중복 경로**: `apps/portfolio/urls.py`는 빈 urlpatterns(주석상 `portfolio.api.urls`로 단일화), `iron_trading`의 trailing-slash 중복 path 등 — 문서에서 중복 노출 방지 검토.
5. **`DISABLE_ERRORS_AND_WARNINGS=True` 영구 유지 시 회귀 감지 불가**: 커버리지 확장 후에는 CI에서 `--validate`로 경고 0 게이트를 거는 방안 권장(단, 이는 별도 인프라 결정 사항).

---

## 부록: 검증에 사용한 명령 (읽기 전용)

```bash
# urls.py / views 파일 탐색
find . -name 'urls.py' -not -path '*migrations*' -not -path '*__pycache__*'
find . -name 'views*.py' -not -path '*migrations*' -not -path '*__pycache__*'

# 문서화 도구 설치 확인
grep -iE 'spectacular|yasg' pyproject.toml

# @extend_schema 적용 분포
grep -rn '@extend_schema' --include='*.py' . | grep -v node_modules

# (권장 후속, 읽기 전용) 미문서화 뷰 정량 식별
python manage.py spectacular --file /tmp/schema.yml --validate
```

> 본 보고서는 코드 변경 없이 정적 분석만 수행함. `@extend_schema` 부착 건수는 데코레이터 출현 횟수 기준이며, ViewSet 자동 생성 라우트는 단일 데코레이터가 복수 엔드포인트를 커버할 수 있어 실제 문서화율은 표기치보다 다소 높을 수 있음.
