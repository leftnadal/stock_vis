# API 문서 감사 보고서

- **감사 일자**: 2026-05-02
- **대상**: Stock-Vis Django REST Framework 백엔드
- **모드**: 읽기 전용 (코드 수정 없음)
- **방법**: `pyproject.toml`/`requirements.txt` 의존성 확인 + 13개 `urls.py` 정적 분석 + ViewSet `@action` 그렙

---

## 현재 상태

### 1. 자동 문서화 라이브러리 — **미설치**

| 라이브러리 | 설치 여부 | 출처 |
|-----------|----------|------|
| `drf-spectacular` | ❌ 없음 | `pyproject.toml`, `requirements.txt` 모두 미참조 |
| `drf-yasg` | ❌ 없음 | `pyproject.toml`, `requirements.txt` 모두 미참조 |
| `coreapi` (deprecated) | ❌ 없음 | — |

전체 `*.py` 파일 그렙 결과 `spectacular | drf_yasg | swagger | openapi | extend_schema` 키워드가 **0건** 검출됨.

### 2. Swagger/OpenAPI 스펙 자동 생성 — **불가능**

- `config/settings.py`의 `INSTALLED_APPS`에 OpenAPI 관련 앱 없음.
- `REST_FRAMEWORK` 딕셔너리에 `DEFAULT_SCHEMA_CLASS` 미설정 → DRF 기본 `coreapi.AutoSchema`만 가용 (deprecated, OpenAPI 3.0 미지원).
- `SPECTACULAR_SETTINGS`/`SWAGGER_SETTINGS` 둘 다 미정의.
- 즉, **Swagger UI/ReDoc/OpenAPI JSON 엔드포인트 어떤 것도 노출되지 않음**.

### 3. 수동 문서화 — **부분적**

- `config/views.py`의 `api_root` 뷰가 일부 엔드포인트(users, stocks, analysis)를 JSON으로 하드코딩하여 노출 중.
  - 그러나 `analysis` 앱은 `INSTALLED_APPS`에 없고 `config/urls.py`에도 매핑 없음 → **stale 문서**.
  - news, macro, rag, serverless, thesis, validation, chainsight, sec_pipeline, portfolio, api_request는 root 뷰에서 누락.
- `docs/` 디렉토리에 기능별 마크다운(`docs/sec_pipeline/`, `docs/chain_sight/`, `docs/thesis_control/` 등)이 존재하나 **API 스펙 형식이 아님** (설계/구현 노트 위주).

---

## 엔드포인트 목록 (앱별)

### 집계 결과 (총 **약 224개** path)

| 앱 | URL 프리픽스 | 엔드포인트 수 | 비고 |
|----|-------------|--------------|------|
| `users` | `/api/v1/users/` | **35** | JWT 7 + 세션 6 + 즐겨찾기 3 + 포트폴리오 9 + 관심사 2 + Watchlist 8 |
| `stocks` | `/api/v1/stocks/` | **39** | dashboard/detail/search 3 + chart/financials 6 + sync 1 + MVP 4 + indicators 3 + search-api 3 + market-movers 1 + fundamentals 5 + screener 6 + quotes 5 + EOD 3 |
| `news` | `/api/v1/news/` | **~32** | `NewsViewSet` (ReadOnly: list/retrieve 2) + `@action` 30개 (드러남: 30) |
| `macro` | `/api/v1/macro/` | **10** | pulse/fear-greed/interest-rates/inflation/global-markets/calendar/vix/sectors/sync/sync-status |
| `rag_analysis` | `/api/v1/rag/` | **15** | DataBasket 6 + AnalysisSession 4 + Monitoring 5 |
| `serverless` | `/api/v1/serverless/` | **66** | Admin 12 + Movers/Sync/Keywords 10 + Breadth 3 + Heatmap 3 + Presets 7 + Filters 1 + Screener 1 + Alerts 6 + Thesis 4 + ETF 9 + LLM Relations 4 + Institutional 3 + Regulatory/Patent 2 + Health 1 |
| `thesis` | `/api/v1/thesis/` | **~28** | Conversation 4 + Monitoring 4 + ThesisViewSet (CRUD 6 + @action 2) + nested premises (CRUD 6) + nested indicators (CRUD 6) |
| `validation` | `/api/v1/validation/` | **6** | summary/metrics/leader-comparison/presets/peer-preference/llm-filter |
| `chainsight` | `/api/v1/chainsight/` | **~19** | seeds/sector-graph/signals/trace 4 + neighbors/graph/suggestions 3 + WatchlistViewSet (CRUD 6 + @action 5) |
| `sec_pipeline` | `/api/v1/sec-pipeline/` | **2** | admin/dashboard + filing |
| `api_request` | `/api/v1/` | **6** | health + Provider Admin 5 |
| `portfolio` | `/api/` | **2** | coach/e1/garp + coach/e5/adjustment |
| `config` (root) | `/` | **2** | api_root + health_check |
| `graph_analysis` | — | **0** | 모델/서비스 구현, **URL 미등록** (CLAUDE.md 명시) |

> **근거**: 각 `urls.py` 정적 분석 + `Grep "@action"`로 ViewSet 액션 카운트.
> - `news/api/views.py`: `@action` 30건 + ReadOnlyModelViewSet의 `list`/`retrieve` 자동 제공.
> - `thesis/views/thesis_views.py`: `@action` 2건 (ThesisViewSet에 위치).
> - `chainsight/views/watchlist_views.py`: `@action` 5건 (WatchlistViewSet에 위치).

### 상세 엔드포인트

#### `users` (35) — `/api/v1/users/`
JWT 7개: `jwt/signup`, `jwt/login`, `jwt/logout`, `jwt/refresh`, `jwt/verify`, `jwt/change-password`, `jwt/profile`
세션 인증 6개: `me`, `''`, `@<user_name>`, `change_password`, `login`, `logout`
즐겨찾기 3개: `favorites`, `favorites/add/<id>`, `favorites/remove/<id>`
포트폴리오 9개: `portfolio`, `portfolio/summary`, `portfolio/table`, `portfolio/refresh`, `portfolio/<pk>`, `portfolio/<pk>/quick-update`, `portfolio/symbol/<symbol>`, `portfolio/symbol/<symbol>/refresh`, `portfolio/symbol/<symbol>/status`
관심사 2개: `interests`, `interests/<pk>`
Watchlist 8개: `watchlist`, `watchlist/<pk>`, `watchlist/<pk>/add-stock`, `watchlist/<pk>/bulk-add`, `watchlist/<pk>/bulk-remove`, `watchlist/<pk>/stocks`, `watchlist/<pk>/stocks/<symbol>`, `watchlist/<pk>/stocks/<symbol>/remove`

#### `stocks` (39) — `/api/v1/stocks/`
페이지/검색 3, 차트/재무 6, 동기화 1, MVP 4, 기술지표 3, 종목검색 3, market-movers 1, fundamentals 5, screener 6, quotes 5, EOD 3.

#### `news` (~32) — `/api/v1/news/`
`NewsViewSet`(ReadOnly) router 등록. `@action` 30개 + list/retrieve.
주요 액션: `stock/<symbol>`, `stock/<symbol>/sentiment`, `daily-keywords`, `daily-keywords/generate`, `keyword-detail`, `market-feed`, `interest-options`, `personalized-feed`, `news-events`, `news-events/impact-map`, `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `collection-logs`, `pipeline-health`, `ml-trend`, `llm-usage`, `task-timeline`, `neo4j-status`, `ml-rollback-preview`, `ml-rollback`, `alerts`, `alerts/<alert_pk>/resolve` 등.

#### `macro` (10) — `/api/v1/macro/`
`pulse`, `fear-greed`, `interest-rates`, `inflation`, `global-markets`, `calendar`, `vix`, `sectors`, `sync`, `sync/status`.

#### `rag_analysis` (15) — `/api/v1/rag/`
DataBasket 6: `baskets`, `baskets/<pk>`, `baskets/<pk>/add-item`, `baskets/<pk>/add-stock-data`, `baskets/<pk>/items/<item_id>`, `baskets/<pk>/clear`
AnalysisSession 4: `sessions`, `sessions/<pk>`, `sessions/<pk>/messages`, `sessions/<pk>/chat/stream` (SSE)
Monitoring 5: `monitoring/usage|cost|cache|history|pricing`

#### `serverless` (66) — `/api/v1/serverless/`
가장 큰 앱. Admin Dashboard 12, Market Movers 4, Sync 2, Keywords 4, Market Breadth 3, Sector Heatmap 3, Screener Presets 7, Filters 1, Advanced Screener 1, Alerts 6, Investment Thesis 4, ETF Holdings 9, LLM Relations 4, Institutional 3, Regulatory/Patent 2, Health 1.

#### `thesis` (~28) — `/api/v1/thesis/`
Conversation 4: `conversation/start|respond|news-issues|suggest`
Monitoring 4: `<thesis_id>/dashboard`, `<thesis_id>/indicators/<id>/readings`, `alerts`, `alerts/<aid>/read`
ThesisViewSet (router 등록, CRUD 6 + @action 2 = 8)
Nested premises (router 등록, CRUD 6)
Nested indicators (router 등록, CRUD 6)

#### `validation` (6) — `/api/v1/validation/`
`<symbol>/summary`, `<symbol>/metrics`, `<symbol>/leader-comparison`, `<symbol>/presets`, `<symbol>/peer-preference`, `<symbol>/llm-filter`.

#### `chainsight` (~19) — `/api/v1/chainsight/`
고정 4개: `seeds`, `sector/<sector>/graph`, `signals`, `trace`
동적 3개: `<symbol>/neighbors`, `<symbol>/graph`, `<symbol>/suggestions`
WatchlistViewSet: CRUD 6 + @action 5 (총 11) = `watchlist/...`

#### `sec_pipeline` (2) — `/api/v1/sec-pipeline/`
`admin/dashboard`, `filing/<symbol>`

#### `api_request` (6) — `/api/v1/`
`health`, `admin/providers/{status, rate-limits, cache, test, config}`

#### `portfolio` (2) — `/api/`
`coach/e1/garp`, `coach/e5/adjustment` (Slice 1: E1+GARP, Slice 2: E5)

#### Root (2)
`/` (api_root), `/health/`

---

## 도입 작업 목록

### 권장 라이브러리: **drf-spectacular**

> 이유: OpenAPI 3.0 네이티브, DRF 공식 권장(2024+), Django 5.x/Python 3.12 호환, Swagger UI + ReDoc 동시 노출, `@extend_schema` 데코레이터로 타입/예시 강력 지원. `drf-yasg`는 OpenAPI 2.0 한정 + 유지보수 정체.

### 작업 1: 설치 및 기본 설정 (예상 0.5d)

1. **의존성 추가** (`pyproject.toml`)
   - `drf-spectacular = "^0.27.0"`
   - `poetry lock && poetry install`
2. **`config/settings.py` 수정**
   - `INSTALLED_APPS += ['drf_spectacular']`
   - `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'`
   - `SPECTACULAR_SETTINGS = {'TITLE': 'Stock-Vis API', 'VERSION': '1.0.0', 'DESCRIPTION': 'AI 기반 투자 분석 플랫폼', 'SCHEMA_PATH_PREFIX': '/api/v1/', ...}`
3. **`config/urls.py` 수정**
   - `/api/schema/` (OpenAPI JSON), `/api/schema/swagger-ui/`, `/api/schema/redoc/` 3개 엔드포인트 추가.
   - `SpectacularAPIView`, `SpectacularSwaggerView`, `SpectacularRedocView` import.
4. **빌드 검증**: `python manage.py spectacular --file schema.yml --validate` 통과 확인.

### 작업 2: ViewSet/APIView별 `@extend_schema` 데코레이터 추가 범위 (예상 5–8d)

> **현황**: `class .*(ViewSet|APIView|View)` 그렙 결과 — 23개 파일에 **141개 클래스**.

| 앱 | 클래스 수 | 우선순위 | 비고 |
|----|----------|---------|------|
| `users` | 32 (views.py 27 + jwt_views.py 5) | **High** | 외부 노출, JWT 보안 스키마 명시 필요 |
| `stocks` | 31 (views.py 9 + 7개 분리 파일 22) | **High** | 가장 많이 호출되는 공개 API |
| `news` | 1 (NewsViewSet, 단 `@action` 30개) | **High** | 액션마다 `@extend_schema` 필수 (URL 다양) |
| `macro` | 10 | Medium | 단순 GET 위주 |
| `rag_analysis` | 15 | **High** | SSE 스트림(`ChatStreamView`)은 별도 응답 타입 명시 |
| `serverless` | 13 (admin 12 + views.py 함수형 다수) | Medium | **함수 기반 뷰가 많아 `@api_view` 변환 또는 `@extend_schema_view` 적용 필요** |
| `thesis` | 11 (3 ViewSet + 8 APIView) | **High** | nested router 스키마 충돌 주의 |
| `validation` | 6 | Medium | 모두 GET, 비교적 단순 |
| `chainsight` | 8 (api/views.py 7 + watchlist 1) | Medium | WatchlistViewSet `@action` 5개 별도 처리 |
| `sec_pipeline` | 1 | Low | 단일 ClassView |
| `api_request` | 6 (admin) | Low | IsAdminUser 권한 — 관리자 한정 |
| `portfolio` | 2 (함수형) | Low | `@api_view` 형태로 가정 |

#### 함수형 뷰 처리 규칙
- `serverless/views.py`(105개 `def`)는 함수형. 각각 `@extend_schema(...)` 데코레이터 또는 `@extend_schema_view`로 묶어 처리.
- `portfolio/views.py`도 함수형으로 추정됨 — 동일 처리.

#### 작업량 추정
- ClassView/ViewSet 1개당 평균 10–15분 (request/response 시리얼라이저, 파라미터, 예시 1건).
- `@action`이 있는 ViewSet은 액션마다 별도 데코레이터 필요 (news 30건, watchlist 5건, thesis 2건).
- **총 데코레이터 부착 지점**: 약 **180개** (141 클래스 + 37 액션 + 일부 함수형).
- 1인 풀타임 기준 **5–8일** (드래프트). 시리얼라이저 정합성 체크/수정 포함 시 +2–3일.

### 작업 3: 시리얼라이저 정합성 점검 (예상 2d)

- `@extend_schema(request=..., responses=...)` 정확도를 위해 모든 응답에 `serializer_class` 또는 명시적 응답 시리얼라이저 필요.
- 함수형 뷰 다수가 dict 직접 반환 → `inline_serializer` 또는 별도 시리얼라이저 정의 필요.
- 우선순위: news/serverless/thesis (현재 응답 구조 가장 복잡).

### 작업 4: CI 통합 + Lock-in (예상 1d)

- `python manage.py spectacular --file contracts/openapi.yml` 실행을 GitHub Actions에 추가.
- `contracts/openapi.yml` 기준으로 PR diff 검토 → API 변경 시 PR에서 스펙 변경 가시화.
- 프론트엔드 타입 자동 생성 후보: `openapi-typescript` (`contracts/shared-types.ts`와 정합).

### 작업 5: 인증 스키마 + 보안 표시 (예상 0.5d)

- JWT Bearer 토큰 스키마 등록: `SPECTACULAR_SETTINGS['AUTHENTICATION_WHITELIST']`에 `JWTAuthentication` 추가.
- `IsAdminUser` 권한 뷰는 별도 태그 분리 (예: `tags=['admin']`).
- 공개 엔드포인트(`AllowAny`)는 `security=[]`로 명시적 표시.

### 총 예상 작업량

| Phase | 작업 | 예상 |
|-------|------|------|
| 1 | 라이브러리 설치/설정 + Swagger UI 노출 | **0.5d** |
| 2 | ViewSet/APIView `@extend_schema` 부착 (180+ 지점) | **5–8d** |
| 3 | 시리얼라이저 정합성 점검 + inline 작성 | **2d** |
| 4 | CI 통합 + 스펙 lock-in | **1d** |
| 5 | 인증/태그/보안 스키마 정리 | **0.5d** |
| **합계** | — | **9–12 영업일 (1인 풀타임)** |

#### 단계적 도입 권장
1. **Phase 1** (0.5d): 설치만 — 미주석 상태로도 자동 스키마 생성 가능. 일단 Swagger UI 가용화.
2. **Phase 2** (1주): High 우선순위 4개 앱(users/stocks/news/rag_analysis)부터 `@extend_schema`.
3. **Phase 3** (1주): 나머지 앱 + 시리얼라이저 정합성 + CI 통합.

---

## 부속 권고 (감사 외)

1. **`config/views.py`의 `api_root` JSON 응답 정리**: `analysis` 앱 등 stale 항목 제거 또는 자동 생성된 OpenAPI로 대체.
2. **`graph_analysis` 앱**: URL 미등록인데 `INSTALLED_APPS`에는 포함됨 — 의도된 상태인지 확인 필요(CLAUDE.md상 보류 표시는 일치).
3. **`stocks/urls.py`**: `dashboard`, `stock_detail`은 HTML 템플릿 뷰로 추정 → OpenAPI 스코프에서 제외하도록 `extend_schema(exclude=True)` 또는 별도 분리 권장.
4. **`/api/v1/api/v1/` 중복 회피** (CLAUDE.md 버그 #19): OpenAPI 노출 시 `SCHEMA_PATH_PREFIX`로 명시적 정규화하여 프론트엔드 자동 생성 시 재발 방지.

---

**작성**: Claude Opus 4.7 (1M)
**근거 파일**: 13× `urls.py` + `pyproject.toml` + `requirements.txt` + `config/settings.py` + 23× `views*.py` 정적 그렙 결과.
