# API 문서 감사 보고서

**감사 일자**: 2026-05-19
**대상 프로젝트**: stock_vis (Django REST Framework)
**감사 범위**: Backend API URL 라우팅 + OpenAPI 자동 생성 인프라
**모드**: 읽기 전용 (코드 수정 없음)

---

## 현재 상태

### 1. OpenAPI 생성 도구 설치 여부

| 패키지 | 설치 여부 | 버전 | 출처 |
|--------|----------|------|------|
| `drf-spectacular` | **설치됨** | `^0.29.0` | `pyproject.toml` |
| `drf-spectacular-sidecar` | **설치됨** | `^2026.4.14` | `pyproject.toml` (Swagger UI 정적 자산) |
| `drf-yasg` | 미설치 | - | (드프-스펙태큘러로 대체) |

### 2. Swagger / OpenAPI 스펙 자동 생성 가능 여부

**부분 가능 (v2 전용)**

- **활성화된 엔드포인트** (`config/urls.py:58~68`):
  - `GET /api/v2/schema/` — OpenAPI 3 JSON 스펙
  - `GET /api/v2/swagger/` — Swagger UI
  - `GET /api/v2/redoc/` — ReDoc UI

- **DRF 전역 설정** (`config/settings.py:363`):
  ```python
  'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'
  ```
  → 모든 ViewSet/APIView는 AutoSchema로 자동 추론된다.

- **SPECTACULAR_SETTINGS** (`config/settings.py:370~418`):
  - `TITLE`: "Stock-Vis **Market Pulse v2** API" → **v2 전용으로 라벨링됨**
  - `SCHEMA_PATH_PREFIX`: `r'/api/v[12]'` → 정규식이 v1+v2를 모두 포함하므로 **v1 엔드포인트도 schema에 노출**
  - `DISABLE_ERRORS_AND_WARNINGS: True` → `'unable to guess serializer'` 등 graceful fallback noise를 무시 (v1 일부는 string body로 폴백)
  - `TAGS`에 `'Market Pulse v2'`만 정의됨 → 그 외 앱들은 그루핑 미흡

### 3. `@extend_schema` 데코레이터 적용 현황

| 파일 | `@extend_schema` 카운트 |
|------|------------------------|
| `marketpulse/api/views/*.py` (5개 파일) | 5 (각 파일 1개씩) |
| `chainsight/api/views.py` | 7 |
| `serverless/views.py` | 6 |
| `api_request/admin_views.py` | 5 |
| `news/api/views.py` | 2 |
| `rag_analysis/views.py` | 2 |
| `users/views.py` | 2 |
| **합계** | **~29개** (전체 ~250+ 엔드포인트 중) |

- stocks/, macro/, validation/, thesis/, sec_pipeline/, portfolio/ 앱은 **`@extend_schema` 0개** → schema에 string fallback으로만 노출됨.

### 결론

- **인프라**: 이미 `drf-spectacular`가 설치/설정되어 있다 → 신규 도입 불필요.
- **현실**: Market Pulse v2 5개 엔드포인트만 production-grade 스펙. 나머지 v1 ~200+ 엔드포인트는 `DISABLE_ERRORS_AND_WARNINGS=True` 뒤에 숨겨진 fallback 상태.
- **공식 문서로 활용 가능?** ❌ 현 상태로는 곤란 (v1 응답 스키마가 불완전).

---

## 엔드포인트 목록 (앱별 테이블)

### 라우팅 트리 요약

| Prefix | 라우팅 모듈 | 비고 |
|--------|------------|------|
| `/api/v1/users/` | `users.urls` | JWT + 세션 인증 + Portfolio + Watchlist + Interest |
| `/api/v1/stocks/` | `stocks.urls` | Stock detail / Chart / Fundamentals / Screener / Indicators / EOD |
| `/api/v1/news/` | `news.api.urls` | NewsViewSet (Router + 30개 @action) |
| `/api/v1/macro/` | `macro.urls` | Market Pulse v1, Fear & Greed, VIX 등 |
| `/api/v1/rag/` | `rag_analysis.urls` | DataBasket + AnalysisSession + Monitoring |
| `/api/v1/serverless/` | `serverless.urls` | Market Movers + Screener + Alerts + Chain Sight Phase 3/5/7/8 |
| `/api/v1/thesis/` | `thesis.urls` | Thesis CRUD (Router) + Conversation + Dashboard + Alerts |
| `/api/v1/validation/` | `validation.api.urls` | 1차 검증 (Peer 비교, Preset, LLM filter) |
| `/api/v1/chainsight/` | `chainsight.api.urls` | Chain Sight v2 그래프 + Watchlist ViewSet |
| `/api/v1/sec-pipeline/` | `sec_pipeline.urls` | SEC EDGAR 파이프라인 |
| `/api/v1/` | `api_request.urls` | Provider Admin (health, providers/*) |
| `/api/` | `portfolio.urls` | Portfolio Coach E1~E6 |
| `/api/v2/market-pulse/` | `marketpulse.api.urls` | Market Pulse v2 (drf-spectacular 완전 적용) |
| `/api/v2/{schema,swagger,redoc}/` | `drf_spectacular.views` | OpenAPI UI |

### 앱별 엔드포인트 수

| # | 앱 | URL 패턴 수 | ViewSet @action | `@extend_schema` 적용 | 비고 |
|---|----|------------|----------------|---------------------|------|
| 1 | **stocks** | 39 | 0 | **0** | 가장 많은 엔드포인트. views_*.py 8개 파일로 분할 (search/market_movers/fundamentals/screener/exchange/eod/indicators/mvp) |
| 2 | **users** | 35 | 0 | 2 | JWT 7 + 세션 인증 + Portfolio 10 + Favorites 3 + Interest 2 + Watchlist 8 |
| 3 | **news** | 1 (Router) | 30 | 2 | NewsViewSet 단일. 실질 엔드포인트: list/retrieve + @action 30개 ≈ 32개 |
| 4 | **macro** | 10 | 0 | 0 | Market Pulse v1 (deprecated 예정?) + 개별 지표 + Sync |
| 5 | **rag_analysis** | 15 | 0 | 2 | DataBasket 6 + AnalysisSession 4 + Monitoring 5 |
| 6 | **serverless** | 64 | 0 | 6 | **두 번째로 큰 모듈**. Admin Dashboard 11 + Market Movers 5 + Screener 12 + Alerts 6 + Thesis 4 + Chain Sight Phase 3/5/7/8 = 19 + Breadth 3 + Heatmap 3 + Health 1 |
| 7 | **thesis** | 11 (+ 3 Router) | 2 | 0 | ThesisViewSet/PremiseViewSet/IndicatorViewSet CRUD + 2 @action + Conversation 4 + Dashboard 2 + Alerts 2. 실질 ≈ 25 |
| 8 | **validation** | 6 | 0 | 0 | symbol 단위 6개 (summary, metrics, leader-comparison, presets, peer-preference, llm-filter) |
| 9 | **chainsight** | 7 (+ Router) | 5 | 7 | Graph 4 + Symbol-based 3 + WatchlistViewSet (create + 5 actions ≈ 6) ≈ 13 |
| 10 | **sec_pipeline** | 2 | 0 | 0 | dashboard + filing/<symbol> |
| 11 | portfolio | 5 | 0 | 0 | Coach E1/E2/E3/E5/E6 |
| 12 | marketpulse (v2) | 5 | 0 | 5 | ✅ 완전 문서화 (overview, cards/detail, news/refresh, i18n, health) |
| 13 | api_request | 6 | 0 | 5 | health 1 + Provider Admin 5 |

### 총합 (요청한 10개 앱)

| 앱 | 실질 엔드포인트 (path + action) |
|----|-------------------------------|
| stocks | **39** |
| users | **35** |
| news | **~32** (1 path + 30 @action + ReadOnlyModelViewSet list/retrieve) |
| macro | **10** |
| rag_analysis | **15** |
| serverless | **64** |
| thesis | **~25** (11 path + 3 ViewSet CRUD + 2 @action) |
| validation | **6** |
| chainsight | **~13** (7 path + WatchlistViewSet ≈ 6) |
| sec_pipeline | **2** |
| **소계** | **~241** |
| (참고) portfolio | 5 |
| (참고) marketpulse v2 | 5 |
| (참고) api_request | 6 |
| **전체** | **~257** |

### 흥미로운 발견

- **serverless 앱이 64개로 가장 비대** — Market Movers, Screener, Chain Sight Phase 3/5/7/8, Alerts, Thesis가 단일 앱에 혼재. 향후 분할 필요성 검토.
- **news 앱**의 30개 @action 중 절반 이상이 `IsAdminUser` 권한 (ML 운영용) → 공개 문서에서 분리하는 것이 좋다.
- **chainsight/api/views.py**에 `@extend_schema` 7개 적용 — v1 중 상대적으로 잘 문서화된 영역.
- **thesis/views/thesis_views.py**에 `@action` 2개뿐인데 ViewSet 3개가 등록되어 있어 router-driven URL이 ~15개 추가 생성됨 (라우팅 카운트에 안 잡힘).

---

## 도입 작업 목록

### 전제: 신규 설치 불필요

`drf-spectacular` + `drf-spectacular-sidecar`는 이미 `pyproject.toml`에 등록되어 있고 `INSTALLED_APPS`(`config/settings.py:205~206`), `DEFAULT_SCHEMA_CLASS`(line 363), `SPECTACULAR_SETTINGS`(line 370~418)에 모두 설정 완료. **Phase 1은 "v1 문서 품질 향상"이 핵심이다.**

### Phase 1: 즉시 가능한 정비 (반나절 ~ 1일)

| # | 작업 | 대상 파일 | 예상 시간 |
|---|------|----------|----------|
| 1 | `SPECTACULAR_SETTINGS.TITLE`을 "Stock-Vis v1 + v2 API"로 변경 (v2 전용 문구 제거) | `config/settings.py:371` | 5분 |
| 2 | `SPECTACULAR_SETTINGS.DESCRIPTION` 갱신 — v1/v2 분리, JWT/세션 인증 정책 명시 | `config/settings.py:372~375` | 15분 |
| 3 | `TAGS` 배열에 앱별 태그 13개 추가 (stocks/users/news/macro/rag/serverless/thesis/validation/chainsight/sec/portfolio/api_request/marketpulse) | `config/settings.py:383~385` | 30분 |
| 4 | `/api/v1/schema/`, `/api/v1/swagger/`, `/api/v1/redoc/` 라우팅 추가 (현재는 v2만 노출) | `config/urls.py:58~68` | 10분 |
| 5 | `DISABLE_ERRORS_AND_WARNINGS`를 일시적으로 `False`로 돌려 실제 warning 목록 캡처 → 우선순위 도출 | `config/settings.py:390` | 30분 |
| **소계** | | | **약 1.5시간** |

### Phase 2: 핵심 API `@extend_schema` 일괄 적용 (3~5일)

우선순위는 **외부 노출 가능성 + 사용 빈도 + 응답 스키마 복잡도** 기준.

| 우선순위 | 앱 | 대상 View 수 | 응답 모델 | 예상 작업 |
|---------|----|------|----------|----------|
| P0 | stocks | 39 (8개 views 파일) | Serializer 사용 일관성 검증 필요 | 1.5일 |
| P0 | users | 35 (JWT + Portfolio + Watchlist) | 인증 응답 + 자체 Serializer | 1일 |
| P1 | serverless | 64 (특히 Admin Dashboard 11 + Screener 12 + Chain Sight 19) | function-based view 多 → `extend_schema` 호출 까다로움 | 1.5~2일 |
| P1 | thesis | ~25 (3 ViewSet) | uuid 파라미터 + nested router | 0.5일 |
| P2 | news | 30 @action | ML 운영용은 `exclude=True` 처리 후 공개 부분만 | 0.5일 |
| P2 | rag_analysis | 15 (DataBasket/Session/Monitoring) | SSE 스트리밍 endpoint는 `responses=OpenApiTypes.BINARY` | 0.5일 |
| P3 | macro | 10 | function-based + 응답 dict | 0.5일 |
| P3 | validation | 6 | symbol-scoped, 단순 | 0.5일 |
| P3 | chainsight | 13 → 이미 7개 적용. 나머지만 | Watchlist ViewSet 6 + 누락분 | 0.5일 |
| P4 | sec_pipeline | 2 | 단순 | 1시간 |
| **합계** | | **~241** | | **약 7~8일** |

### Phase 3: 응답 스키마 표준화 (1~2일)

- **에러 응답 envelope**: `config/exception_handler.py`가 이미 `{detail, code?, errors?, status_code}` 형식을 반환 (`settings.py:365~366` 주석). 이를 `OpenApiResponse`로 명시적 등록 → 모든 endpoint의 4xx/5xx 응답 스키마 통일.
- **공통 Serializer 추출**: `stocks/users/serverless`에 중복되는 응답 패턴 (예: `{"results": [...], "count": N}`) → 공용 `PaginatedResponseSerializer` 도입 검토.
- **공통 enum**: `SPECTACULAR_SETTINGS.ENUM_NAME_OVERRIDES`에 이미 4개 등록됨. 추가 식별 필요 (e.g. AlertSeverity, ScreenerOperator, RAG ModelChoice).

### Phase 4: CI 검증 (반나절)

- `python manage.py spectacular --file schema.yml --validate` 명령을 CI에 추가.
- PR에서 schema diff 자동 코멘트 (선택).
- `DISABLE_ERRORS_AND_WARNINGS: False`로 복귀 + 누락 warning은 fail 처리.

### 총 예상 작업량

| Phase | 작업 | 예상 |
|-------|------|------|
| Phase 1 | 즉시 정비 (설정 + UI 라우팅) | **1.5시간** |
| Phase 2 | `@extend_schema` 일괄 적용 | **7~8일** |
| Phase 3 | 응답 스키마 표준화 | **1~2일** |
| Phase 4 | CI 통합 | **반나절** |
| **합계** | **9~11일 (개발자 1인 기준)** |

### 권장 진입 순서

1. **Phase 1 즉시 실행** — 비용 1.5시간, 효과: v1 endpoint도 Swagger UI에서 확인 가능 (string fallback이라도 일단 노출).
2. **Phase 2 P0 (stocks + users)** — 가장 외부 노출도 높은 영역. Frontend 팀과의 contract 동기화 효과 큼.
3. **Phase 3 응답 envelope 표준화** — Phase 2 P0 완료 후 진행해야 손이 두 번 가지 않음.
4. **Phase 2 P1~P4** + Phase 4 CI — 점진적 적용.

---

## 부록: 참고 파일

| 경로 | 역할 |
|------|------|
| `config/urls.py:19~68` | drf-spectacular 라우팅 (v2만) |
| `config/settings.py:205~206, 363, 370~418` | spectacular 설정 본체 |
| `config/spectacular_enums.py` | enum 헬퍼 (참조용) |
| `config/exception_handler.py` | 에러 envelope 표준 |
| `marketpulse/api/views/*.py` | `@extend_schema` 모범 사례 (5개 view 완전 문서화) |
| `chainsight/api/views.py` | v1에서 가장 잘 문서화된 사례 (7개 endpoint) |

---

**감사 종료**
