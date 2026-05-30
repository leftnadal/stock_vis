# API 문서 감사 보고서

> 작성일: 2026-05-30
> 작성자: 야간 자동 감사 (읽기 전용 — 코드 변경 없음)
> 대상: Stock-Vis Backend (Django REST Framework, 모노레포 구조)
> 범위: OpenAPI/Swagger 자동 문서화 현황 및 보강 작업 산정

---

## 현재 상태

### 1. API 문서화 도구 — **이미 설치 + 운영 중** ✅

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | ✅ **설치** `^0.29.0` (lock: 0.29.0) | `pyproject.toml`, `poetry.lock:1073` |
| `drf-spectacular-sidecar` | ✅ **설치** `^2026.4.14` (lock: 2026.5.1) | `pyproject.toml`, `poetry.lock:1096` |
| INSTALLED_APPS 등록 | ✅ | `config/settings.py:212-213` (`drf_spectacular`, `drf_spectacular_sidecar`) |
| `DEFAULT_SCHEMA_CLASS` | ✅ | `config/settings.py:370` = `drf_spectacular.openapi.AutoSchema` |
| `SPECTACULAR_SETTINGS` 블록 | ✅ | `config/settings.py:377` (TITLE/VERSION + `ENUM_NAME_OVERRIDES` 등) |
| 보조 모듈 | ✅ | `config/serializers.py` (표준 에러 envelope), `config/spectacular_enums.py` (enum 충돌 해결) |

> **결론**: OpenAPI 스펙은 **현재도 자동 생성 가능**한 상태입니다. 본 감사의 결론은 "도입"이 아니라 **"도입된 문서화의 완성/보강"** 으로 방향이 바뀝니다.

### 2. 스키마 노출 엔드포인트 — **v2 경로에만 존재**

`config/urls.py:61-72` 기준:

| URL | View | name |
|-----|------|------|
| `/api/v2/schema/` | `SpectacularAPIView` | `schema-v2` |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | `swagger-v2` |
| `/api/v2/redoc/` | `SpectacularRedocView` | `redoc-v2` |

- 주석상 도입 동기는 "**Market Pulse v2 OpenAPI 자동 생성**"(`settings.py:376`, `urls.py:61`).
- 다만 `config/spectacular_enums.py`가 **여러 모델(NewsCategory 등)의 동일 필드명 enum 충돌**을 해결한다는 사실은, 스키마 생성 대상이 v2뿐 아니라 **v1 레거시 앱 모델까지 포함**됨을 의미합니다. → `SCHEMA_PATH_PREFIX`가 v1/v2를 모두 포괄하도록 설정되었을 가능성이 높습니다(프로젝트 메모리상 `r'/api/v[12]'`).

> ⚠️ **메모리 정합성**: `MEMORY.md`의 "drf-spectacular 0.29.0 + sidecar 운영 중" 기록은 **코드와 일치**합니다(✅). 단, 메모리에 적힌 노출 경로 `/api/v2/schema/`는 맞으나, 메모리의 다른 항목 `/api/v2/schema/` 외에 "v1" 스키마 전용 노출 URL은 코드에 **없음**(스키마 자체는 v1을 포함하지만, 별도 v1 Swagger UI 진입점 부재).

### 3. View 아키텍처 (문서화 품질에 직접 영향)

| 유형 | 분포 | 문서화 시사점 |
|------|------|--------------|
| `APIView` 직접 상속 (대다수) | macro 10, rag 18, users 다수, serverless 12(admin) 등 | `Response(dict)` 직접 반환이 많아 **자동 응답 스키마가 비거나 부정확** → `@extend_schema(responses=)` 수동 명시 필요 |
| `generics.ListAPIView` | `stocks.StockListAPIView` 등 소수 | serializer 보유, 자동 추론 양호 |
| `viewsets.*` (Router 사용) | `news.NewsViewSet`(ReadOnly), `thesis.ThesisViewSet`/`ThesisPremiseViewSet`/`ThesisIndicatorViewSet`, `chainsight.WatchlistViewSet` | 라우터가 CRUD 액션 자동 생성, 자동 추론 비교적 양호하나 `@action` 커스텀 메서드는 보강 필요 |
| 함수형 뷰 (`@api_view`) | serverless 대부분, portfolio coach(e1~e6), api_request | 데코레이터 기반 스키마 명시 권장 |
| `TemplateView`/`DetailView` (HTML) | `stocks.DashboardView`, `stocks.StockDetailView`, `sec_pipeline.dashboard` | API 아님 → 스키마 제외 대상 |

### 4. `@extend_schema` 실제 적용 현황 — **37건 / 11개 코드 파일** (점진 적용 중)

| 파일 | 데코 수 | 영역 |
|------|:--:|------|
| `chainsight/api/views.py` | 7 | ✅ 핵심 — 그래프 탐색 전건 |
| `serverless/views.py` | 6 | 일부 (전체 64개 중) |
| `portfolio/api/views.py` | 6 | ✅ coach e1~e6 전건 |
| `packages/shared/api_request/admin_views.py` | 5 | ✅ Provider Admin 전건 |
| `marketpulse/api/views/*` (5파일) | 5 | ✅ v2 전건 (overview/cards/health/i18n/news_refresh) |
| `news/api/views.py` | 2 | ViewSet |
| `rag_analysis/views.py` | 2 | 일부 (전체 18개 중) |
| `packages/shared/users/views.py` | 2 | 일부 (전체 35개 중) |
| **합계** | **37** | |

> **운영 정책 (코드에 명시됨)** — `SPECTACULAR_SETTINGS` 주석(`config/settings.py`):
> - `SCHEMA_PATH_PREFIX = r'/api/v[12]'` → **v1 + v2 엔드포인트 모두 스키마에 포함**.
> - `DISABLE_ERRORS_AND_WARNINGS = True` → "unable to guess serializer" 류 noise 억제.
> - 명시된 전략: **"핵심 영역(marketpulse, chainsight, api_request admin)은 `@extend_schema`로 정상 처리. 나머지 v1 endpoint는 graceful fallback(string body)로 노출. 정확한 schema가 필요한 view만 점진적으로 `@extend_schema(responses=...)` 추가."**
> - `ENUM_NAME_OVERRIDES`: ThesisPremiseCategory/NewsCategory/SavedPathStatus/ThesisStatus 등 enum 충돌 사전 해결.

> 📌 **본 감사는 4월부터 매일 야간 자동 수행되는 반복 작업**입니다 (`docs/nightly_auto_system/reports/{월}/{일}/api_docs_audit.md`, 4/14~5/29 시리즈 존재). 따라서 "신규 도입"이 아니라 **기존 점진 적용의 진행률 추적**이 본 보고서의 역할입니다.

---

## 엔드포인트 목록 (앱별 테이블)

> 라우팅 기준점: `config/urls.py`. 앱 구조가 모노레포로 이전되어 실제 경로는 `packages/shared/*`, `*/api/*` 형태임.

### config/urls.py 마운트 맵

| Prefix | include 대상 | 비고 |
|--------|-------------|------|
| `/api/v1/users/` | `packages.shared.users.urls` | |
| `/api/v1/stocks/` | `packages.shared.stocks.urls` | HTML 페이지 2개 포함 |
| `/api/v1/news/` | `news.api.urls` | ViewSet 라우터 |
| `/api/v1/macro/` | `macro.urls` | |
| `/api/v1/rag/` | `rag_analysis.urls` | |
| `/api/v1/serverless/` | `serverless.urls` | 최다 |
| `/api/v1/thesis/` | `thesis.urls` | ViewSet 3 + APIView 8 |
| `/api/v1/validation/` | `validation.api.urls` | |
| `/api/v1/chainsight/` | `chainsight.api.urls` | ViewSet 1 + APIView 7 |
| `/api/v1/sec-pipeline/` | `sec_pipeline.urls` | ⚠️ 경로는 `sec-pipeline`(CLAUDE.md엔 `/api/v1/sec/`로 표기 — 문서 불일치) |
| `/api/v1/` | `packages.shared.api_request.urls` | Provider Admin |
| `/api/` | `portfolio.urls` | **빈 urlpatterns** (legacy 제거됨) |
| `/api/v1/` | `portfolio.api.urls` | coach e1~e6 |
| `/api/v2/market-pulse/` | `marketpulse.api.urls` | v2 |

### 사용자 지정 10개 앱

#### stocks (`/api/v1/stocks/`) — API 37 (+ HTML 2)
검색 1 · 차트/탭 데이터 6 · 동기화 1 · MVP 4 · 기술지표 3 · 종목검색 3 · Market Movers 1 · Fundamentals 5 · Screener 6 · Quotes 5 · EOD 3
(HTML 페이지: `""` Dashboard, `stock/<symbol>/` Detail — 스키마 제외)

#### users (`/api/v1/users/`) — 35
JWT 7 (signup/login/logout/refresh/verify/change-password/profile) · 세션인증 6 · 즐겨찾기 3 · 포트폴리오 9 · 관심사 2 · Watchlist 8

#### news (`/api/v1/news/`) — ViewSet (ReadOnly: list + retrieve, + `@action`)
`NewsViewSet` (DefaultRouter `''` 등록)

#### macro (`/api/v1/macro/`) — 10
pulse · fear-greed · interest-rates · inflation · global-markets · calendar · vix · sectors · sync · sync/status

#### rag_analysis (`/api/v1/rag/`) — 15
DataBasket 6 · AnalysisSession 4 (chat/stream SSE 포함) · Monitoring 5

#### serverless (`/api/v1/serverless/`) — 64
Admin Dashboard 12 · Market Movers 2 · 동기화 2 · 키워드 4 · Breadth 3 · Heatmap 3 · Screener Presets 7 · Filters 1 · Advanced Screener 1 · Alerts 6 · Investment Thesis 4 · ETF Holdings 9 · LLM Relations 4 · Institutional 3 · Regulatory/Patent 2 · Health 1
(대부분 함수형 `@api_view`, admin은 APIView 12)

#### thesis (`/api/v1/thesis/`) — APIView 8 + ViewSet 3그룹
APIView: conversation/start·respond·news-issues·suggest (4) · `<id>/dashboard/` · `<id>/indicators/<iid>/readings/` · alerts/ · alerts/`<aid>`/read/ (총 8)
ViewSet (router): `ThesisViewSet`('') + nested `ThesisPremiseViewSet` + `ThesisIndicatorViewSet` → 각 CRUD 액션 자동 생성

#### validation (`/api/v1/validation/`) — 6
`<symbol>/` summary · metrics · leader-comparison · presets · peer-preference · llm-filter

#### chainsight (`/api/v1/chainsight/`) — APIView 7 + ViewSet 1
seeds · sector/`<sector>`/graph · signals · trace · `<symbol>`/neighbors · `<symbol>`/graph · `<symbol>`/suggestions (7) + `WatchlistViewSet`(router `watchlist`)

#### sec_pipeline (`/api/v1/sec-pipeline/`) — API 1 (+ admin HTML 1)
`filing/<symbol>/` (`FilingDataView` APIView) · `admin/dashboard/` (함수형 HTML 뷰 — 스키마 제외)

### 앱별 집계

| 앱 | API 엔드포인트 | View 유형 | 지정 대상 |
|----|:--:|------|:--:|
| stocks | 37 (+HTML 2) | APIView/generics | ✅ |
| users | 35 | APIView | ✅ |
| news | ViewSet (≈2+) | ReadOnlyModelViewSet | ✅ |
| macro | 10 | APIView | ✅ |
| rag_analysis | 15 | APIView | ✅ |
| serverless | 64 | 함수형 + APIView(admin 12) | ✅ |
| thesis | 8 + ViewSet×3 | APIView + ViewSet | ✅ |
| validation | 6 | APIView | ✅ |
| chainsight | 7 + ViewSet×1 | APIView + ViewSet | ✅ |
| sec_pipeline | 1 (+HTML 1) | APIView | ✅ |
| **소계 (지정 10앱)** | **≈183 + ViewSet 4그룹** | | |

### 그 외 등록 앱 (참고)

| 마운트 | 엔드포인트 | 비고 |
|--------|:--:|------|
| `packages.shared.api_request` (`/api/v1/`) | 6 | health + Provider Admin 5 (함수형) |
| `portfolio.api` (`/api/v1/`) | 6 | coach e1~e6 (함수형) |
| `portfolio` (`/api/`) | 0 | 빈 urlpatterns (legacy 전부 제거) |
| `integrations.iron_trading` (`/api/v1/iron-trading/`) | 1 | daily-context (+ trailing-slash 중복 등록) |
| `marketpulse.api` (`/api/v2/market-pulse/`) | 5 | overview · cards/`<id>`/detail · news/refresh · i18n · health |
| (스키마) `/api/v2/` | 3 | schema · swagger · redoc |

> **전체 합계 (스키마/HTML 제외, ViewSet 액션 별도)**: **약 200개 API 엔드포인트** + ViewSet 4그룹의 CRUD 액션.

---

## 도입(보강) 작업 목록

> 도구는 이미 설치·작동 중이며, 현재 정책은 **"핵심만 명시 + 나머지 graceful fallback"** 입니다.
> 따라서 아래는 "필수 도입"이 아니라 **품질을 한 단계 올리려는 경우의 선택적 보강** 로드맵입니다.
> (현 정책 유지가 합리적이라면 Phase 0~1만으로 충분합니다.)

### Phase 0: 현황 검증 (0.5일) — 권장
1. `python manage.py spectacular --file schema.yml --validate` 실행 → 현재 fallback(string body)로 노출되는 엔드포인트 목록 식별.
2. `SCHEMA_PATH_PREFIX = r'/api/v[12]'`가 의도대로 v1+v2를 포함하는지 생성 결과로 확인 (현재 설정상 포함됨).

### Phase 1: 스키마 진입점 정비 (0.5일) — 권장
- 현재 Swagger/Redoc UI가 `schema-v2` 이름으로만 노출됨. 스키마 본체는 v1도 포함하므로, UI 타이틀/설명이 "Market Pulse v2"로 한정되어 **v1 API가 같은 문서에 있음을 개발자가 인지하기 어려움**. → 타이틀을 전사 API로 일반화하거나 v1 전용 진입점 추가 검토.

### Phase 2: `@extend_schema` 보강 (선택 — 정책 전환 시에만)

> 현재 37건 적용(핵심 영역 완료). 나머지는 fallback 상태. **"전수 명시"로 정책을 바꿀 경우에만** 아래 작업이 발생합니다.
> dict 직접 반환 APIView가 다수라 자동 응답 스키마가 부실하므로, 분류별 보강:

| 분류 | 대상(개략) | 작업 | 난이도 |
|------|-----------|------|:--:|
| **A. ViewSet (자동 추론 양호)** | news, thesis×3, chainsight watchlist | `@extend_schema_view`로 list/retrieve/`@action` summary 보강 | 낮음 |
| **B. generics + serializer 보유** | stocks 일부 | summary/태그만 | 낮음 |
| **C. 단일 GET·dict 반환 APIView** | macro 10, validation 6, chainsight 7, sec 1, rag 조회계 | `responses=`(inline_serializer/OpenApiResponse) + `parameters`(symbol path) 명시 | 중간 |
| **D. 멀티메서드·동기화·SSE·비동기** | users watchlist/portfolio, rag chat/stream(SSE), stocks sync(GET/POST), serverless 트리거류 | 메서드별 request/response 분리, 202/task 스키마 수동 | 높음 |
| **E. 함수형 뷰(@api_view)** | serverless 50+, coach 6, api_request 11 | 각 함수에 `@extend_schema` 부착 (request/response/parameters) | 높음(개수多) |

**작업량 산정** (Phase 2는 "전수 명시" 정책 전환을 가정한 상한치)

| 구간 | 내용 | 예상 |
|------|------|------|
| Phase 0 | validate 베이스라인 + prefix 검증 | 0.5일 |
| Phase 1 | v1 스키마 진입점/타이틀 정비 | 0.5일 |
| Phase 2-A/B | ViewSet/generics summary 보강 (~50 액션) | 1.0일 |
| Phase 2-C | 조회 APIView 응답 스키마 명시 (~40개) | 2.0일 |
| Phase 2-D | 멀티메서드/SSE/비동기 (~20개) | 1.5일 |
| Phase 2-E | 함수형 뷰 보강 (serverless 64 중심, ~70개) | 2.5일 |
| Phase 3 | 응답 전용 Serializer/inline 공통화 + 에러 envelope 연결 | 1.0일 |
| QA | `--validate` 경고 0 목표 + 프런트 타입 정합 | 0.5일 |
| **필수 (Phase 0~1, 현 정책 유지)** | | **약 1일** |
| **전수 보강 시 (Phase 0~3 합)** | | **약 9.5일 (2주)** |

### 권장 전략
1. **즉시 가치**: 도구가 이미 작동하므로 Phase 0 validate만으로 "어디가 빈 스키마인지" 지도를 얻음 → 보강 우선순위 결정.
2. **우선순위**: 프런트 사용 빈도 순 = `thesis`/`validation`/`chainsight` → `stocks`/`users` → `serverless`(함수형 다수라 비용 큼, 후순위) → 나머지.
3. **표준 패턴 정립**: dict 반환 뷰가 핵심 부채. 응답 전용 Serializer(또는 `inline_serializer`) 작성을 코딩 규칙화 → 자동 추론 품질 + 응답 일관성 동반 상승. `config/serializers.py`의 에러 envelope를 공통 `responses`에 연결.
4. **CI 게이트**: `spectacular --validate`를 nightly/CI에 추가 → 스펙↔구현 드리프트 차단 (CLAUDE.md Contract-Driven Development 원칙과 정합).

---

## 부록: 발견된 부수 이슈 (감사 범위 외 — 참고용)

1. **문서 경로 불일치**: CLAUDE.md는 SEC 앱을 `/api/v1/sec/*`로 표기하나 실제 마운트는 `/api/v1/sec-pipeline/`. CLAUDE.md `chainsight`/`sec_pipeline` 엔드포인트 표기 갱신 권장.
2. **iron_trading trailing-slash 중복**: `daily-context`와 `daily-context/`가 동일 뷰로 2회 등록(`integrations/iron_trading/urls.py:8-10`) — 스키마에서 중복 path로 노출될 수 있음.
3. **portfolio.urls 빈 include**: `config/urls.py:52`가 빈 urlpatterns를 include — 정리 후보(#65 후속으로 명시됨).

---

## 부록: 감사 방법 (재현)
- 의존성: `pyproject.toml` + `poetry.lock` grep (`drf-spectacular` 확인)
- 설정: `config/settings.py` INSTALLED_APPS(212), REST_FRAMEWORK(355), SPECTACULAR_SETTINGS(377)
- 라우팅: `config/urls.py` + 마운트된 14개 urls.py 전수 read
- View 유형: `views*.py` `^class ...(...)` 정의 grep

> 본 보고서는 **읽기 전용 감사**이며 코드 변경을 일절 수행하지 않았습니다.
> (초기 1차 작성본은 `stocks/urls.py` 등 구(舊) 경로 가정으로 오류가 있어, 실제 `config/urls.py` 마운트 기준으로 전면 재작성함.)
