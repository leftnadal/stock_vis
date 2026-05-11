# API 문서 감사 보고서

- **작성일**: 2026-04-27
- **범위**: Stock-Vis Backend (Django REST Framework) 전체 앱
- **감사 모드**: 읽기 전용 (코드 수정 없음)
- **참조 파일**: `config/urls.py`, 각 앱별 `urls.py`/`views*.py`, `pyproject.toml`, `config/settings.py`

---

## 1. 현재 상태

### 1.1 OpenAPI/Swagger 자동 생성 도구 설치 여부

| 항목 | 결과 | 비고 |
|------|------|------|
| `drf-spectacular` (pyproject.toml 의존성) | ❌ 미설치 | `pyproject.toml` `[tool.poetry.dependencies]`에 없음 |
| `drf-yasg` (pyproject.toml 의존성) | ❌ 미설치 | 동일 |
| `requirements.txt` | ❌ 없음 | Poetry 단일 사용 (`pyproject.toml` only) |
| `INSTALLED_APPS`에 `drf_spectacular` 또는 `drf_yasg` 등록 | ❌ 미등록 | `config/settings.py` 확인 |
| `REST_FRAMEWORK`에 `DEFAULT_SCHEMA_CLASS` 지정 | ❌ 미지정 | DRF 기본 `coreapi.AutoSchema` 사용 (지원 종료 예정) |
| `config/urls.py`에 `/schema/`·`/swagger/`·`/redoc/` 라우트 | ❌ 없음 | OpenAPI 노출 엔드포인트 없음 |
| 코드 내 `@extend_schema` / `swagger_auto_schema` 데코레이터 | ❌ 0건 | 전역 grep 결과 없음 |

**결론**: 현 시점 Stock-Vis 백엔드는 **OpenAPI 스펙을 자동 생성할 수 없는 상태**다.

### 1.2 Swagger/OpenAPI 스펙 생성 가능성

| 시나리오 | 가능 여부 | 근거 |
|---------|----------|------|
| 즉시 `python manage.py spectacular --file schema.yml` 실행 | ❌ 불가 | `drf-spectacular` 미설치, management command 없음 |
| `drf-spectacular` 설치 후 무 데코레이터 자동 추출 | ⚠️ 부분 가능 | DRF `ViewSet`/`GenericAPIView`(serializer_class 지정된 경우)는 자동 추론. 그러나 본 프로젝트는 대부분 `APIView` 직접 상속 + `serializer_class` 미지정 → 응답/요청 스키마 누락 다수 |
| 완전한 OpenAPI 3.0 스펙 산출 | ❌ 불가 | `@extend_schema(request=, responses=)` 명시 작성 필요 |

### 1.3 현재 문서화 수단

- **수동 작성 문서**: `sub_claude_md/api-endpoints.md` (요약 수준), `docs/features/*` (기능별 설계 문서)
- **코드 내 docstring**: 일부 뷰 클래스에 한글 설명 docstring 존재 (예: `users/views.py`, `stocks/views_*.py`)
- **OpenAPI/JSON Schema 산출물**: 없음
- **Postman/Insomnia 컬렉션**: 미발견

---

## 2. 엔드포인트 목록 (앱별)

> `path()` 등록 수 기준. ViewSet은 DefaultRouter 자동 라우팅(`list`/`retrieve`/`create`/`update`/`partial_update`/`destroy`) + `@action` 데코레이터를 합산. `config/urls.py`의 prefix는 `api/v1/<app>/`.

### 2.1 앱별 엔드포인트 집계 표

| 앱 | URL prefix | 정적 path() | ViewSet 자동 라우팅 | `@action` | 총 엔드포인트 (추정) | 주요 뷰 패턴 |
|----|-----------|------------|--------------------|----------|-------------------|--------------|
| **users** | `/api/v1/users/` | 35 | 0 | 0 | **35** | APIView 32 클래스 (jwt_views 5 + views 27) |
| **stocks** | `/api/v1/stocks/` | 39 | 0 | 0 | **39** | APIView 38 클래스 (8 파일 분할) |
| **news** | `/api/v1/news/` | 1 (router) | 2 (ReadOnlyModelViewSet: list, retrieve) | 30 | **32** | NewsViewSet 단일 (ReadOnlyModelViewSet) |
| **macro** | `/api/v1/macro/` | 10 | 0 | 0 | **10** | APIView 10 클래스 |
| **rag_analysis** | `/api/v1/rag/` | 15 | 0 | 0 | **15** | APIView 15 클래스 |
| **serverless** | `/api/v1/serverless/` | 64 | 0 | 0 | **64** | 함수형 `@api_view` 52개 + `views_admin.py` APIView 12개 |
| **thesis** | `/api/v1/thesis/` | 8 (정적) + 3 (router 마운트) | 15 (ModelViewSet 3개 × 5 CRUD) | 2 | **25** | APIView 4 (conversation) + APIView 4 (monitoring) + ViewSet 3 |
| **validation** | `/api/v1/validation/` | 6 | 0 | 0 | **6** | APIView 6 클래스 |
| **chainsight** | `/api/v1/chainsight/` | 7 (정적) + 1 (router 마운트) | 5 (ModelViewSet × 5 CRUD) | 5 | **17** | APIView 7 + WatchlistViewSet |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | 0 | 0 | **2** | 함수 뷰 1 + APIView 1 |
| **api_request** | `/api/v1/` | 6 | 0 | 0 | **6** | 함수형 `admin_views` 6개 |
| **graph_analysis** | (미등록) | 0 | 0 | 0 | **0** | URL 미연결 (모델/서비스만 구현) |
| **portfolio** | (미등록) | 0 | 0 | 0 | **0** | `urls.py` 부재 |
| **합계** | — | 196 | 22 | 37 | **≈ 251** | — |

### 2.2 앱별 상세 엔드포인트

#### 2.2.1 users (35개) — `/api/v1/users/`
- JWT 인증 7: `jwt/signup/`, `jwt/login/`, `jwt/logout/`, `jwt/refresh/`, `jwt/verify/`, `jwt/change-password/`, `jwt/profile/`
- 세션 인증 (legacy) 6: `me/`, ``, `@<user_name>/`, `change_password/`, `login/`, `logout/`
- Favorites 3: `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/`
- Portfolio 9: `portfolio/`, `portfolio/summary/`, `portfolio/table/`, `portfolio/refresh/`, `portfolio/<pk>/`, `portfolio/<pk>/quick-update/`, `portfolio/symbol/<symbol>/`, `portfolio/symbol/<symbol>/refresh/`, `portfolio/symbol/<symbol>/status/`
- Interests 2: `interests/`, `interests/<pk>/`
- Watchlist 8: `watchlist/`, `watchlist/<pk>/`, `watchlist/<pk>/add-stock/`, `watchlist/<pk>/bulk-add/`, `watchlist/<pk>/bulk-remove/`, `watchlist/<pk>/stocks/`, `watchlist/<pk>/stocks/<symbol>/`, `watchlist/<pk>/stocks/<symbol>/remove/`

#### 2.2.2 stocks (39개) — `/api/v1/stocks/`
- 페이지/검색 3: `''`, `stock/<symbol>/`, `search/`
- 상세 데이터 6: `api/chart/<symbol>/`, `api/overview/<symbol>/`, `api/balance-sheet/<symbol>/`, `api/income-statement/<symbol>/`, `api/cashflow/<symbol>/`, `api/sync/<symbol>/`
- MVP 4: `api/mvp/stocks/`, `api/mvp/stock/<symbol>/`, `api/mvp/rag/<symbol>/`, `api/mvp/sectors/`
- 기술 지표 3: `api/indicators/<symbol>/`, `api/signal/<symbol>/`, `api/indicators/compare/`
- 종목 검색 3: `api/search/symbols/`, `api/search/validate/<symbol>/`, `api/search/popular/`
- Market Movers 1: `api/market-movers/`
- Fundamentals 5: `key-metrics`, `ratios`, `dcf`, `rating`, `all`
- Screener 6: 일반/대형주/고배당/섹터/저변동/거래소
- Quotes 5: index, `<symbol>`, batch, major-indices, sector-performance
- EOD 3: `eod/dashboard/`, `eod/signal/<signal_id>/`, `eod/pipeline/status/`

#### 2.2.3 news (32개) — `/api/v1/news/` (NewsViewSet 단일)
- 표준 라우팅 2: `''` (list), `<pk>/` (retrieve)
- `@action` 30 (대표): `stock/<symbol>/`, `stock/<symbol>/sentiment/`, `all/`, `daily-keywords/`, `daily-keywords/generate/`, `keyword-detail/`, `market-feed/`, `interest-options/`, `personalized-feed/`, `news-events/`, `news-events/impact-map/`, `ml-status/`, `ml-shadow-report/`, `ml-weekly-report/`, `ml-lightgbm-readiness/`, `collection-logs/`, `pipeline-health/`, `ml-trend/`, `llm-usage/`, `task-timeline/`, `neo4j-status/`, `ml-rollback-preview/`, `ml-rollback/`, `alerts/`, `alerts/<alert_pk>/resolve/` 등

#### 2.2.4 macro (10개) — `/api/v1/macro/`
- `pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

#### 2.2.5 rag_analysis (15개) — `/api/v1/rag/`
- DataBasket 6: `baskets/`, `baskets/<pk>/`, `baskets/<pk>/add-item/`, `baskets/<pk>/add-stock-data/`, `baskets/<pk>/items/<item_id>/`, `baskets/<pk>/clear/`
- AnalysisSession 4: `sessions/`, `sessions/<pk>/`, `sessions/<pk>/messages/`, `sessions/<pk>/chat/stream/` (SSE)
- Monitoring 5: `monitoring/usage/`, `monitoring/cost/`, `monitoring/cache/`, `monitoring/history/`, `monitoring/pricing/`

#### 2.2.6 serverless (64개) — `/api/v1/serverless/`
- Admin Dashboard 12 (`admin/dashboard/*`)
- Market Movers 4 (`movers`, `movers/<symbol>`, `sync`, `sync-now`)
- 키워드 4 (`keywords/batch`, `keywords/generate-all`, `keywords/generate-screener`, `keywords/<symbol>`)
- Market Breadth 3 (`breadth`, `breadth/history`, `breadth/sync`)
- Sector Heatmap 3 (`heatmap/sectors`, `heatmap/sectors/<sector>/stocks`, `heatmap/sync`)
- Screener Presets 7 (`presets`, `presets/trending`, `presets/shared/<share_code>`, `presets/import/<share_code>`, `presets/<id>`, `presets/<id>/execute`, `presets/<id>/share`)
- Screener Filters 1 (`filters`)
- Advanced Screener 1 (`screener`)
- Screener Alerts 6 (`alerts`, `alerts/history`, `alerts/history/<id>/read`, `alerts/history/<id>/dismiss`, `alerts/<id>`, `alerts/<id>/toggle`)
- Investment Thesis 4 (`thesis/generate`, `thesis/shared/<share_code>`, `thesis/<id>`, `thesis`)
- ETF (Phase 3) 9 (`etf/status`, `etf/sync`, `etf/resolve-url`, `etf/<symbol>/holdings`, `etf/stock/<symbol>/themes`, `etf/stock/<symbol>/peers`, `themes`, `themes/refresh`, `themes/<theme_id>/stocks`)
- LLM Relations (Phase 5) 4 (`llm-relations/extract`, `llm-relations/sync`, `llm-relations/stats`, `llm-relations/<symbol>`)
- Institutional Holdings (Phase 7) 3 (`institutional/sync`, `institutional/<symbol>/peers`, `institutional/<symbol>`)
- Regulatory + Patent (Phase 8) 2 (`regulatory/<symbol>`, `patent-network/<symbol>`)
- Health 1 (`health`)

#### 2.2.7 thesis (25개) — `/api/v1/thesis/`
- Conversation 4: `conversation/start/`, `conversation/respond/`, `conversation/news-issues/`, `conversation/suggest/`
- Monitoring 4: `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<indicator_id>/readings/`, `alerts/`, `alerts/<aid>/read/`
- ThesisViewSet 7: list/retrieve/create/update/partial_update/destroy + `@action` 2개 (라우터 prefix `''`)
- ThesisPremiseViewSet 5 (`<thesis_id>/premises/` 하위 CRUD)
- ThesisIndicatorViewSet 5 (`<thesis_id>/indicators/` 하위 CRUD)

#### 2.2.8 validation (6개) — `/api/v1/validation/`
- `<symbol>/summary/`, `<symbol>/metrics/`, `<symbol>/leader-comparison/`, `<symbol>/presets/`, `<symbol>/peer-preference/`, `<symbol>/llm-filter/`

#### 2.2.9 chainsight (17개) — `/api/v1/chainsight/`
- 마켓 뷰 4: `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`
- 종목 동적 3: `<symbol>/neighbors/`, `<symbol>/graph/`, `<symbol>/suggestions/`
- WatchlistViewSet 10: 5 CRUD + `@action` 5

#### 2.2.10 sec_pipeline (2개) — `/api/v1/sec-pipeline/`
- `admin/dashboard/`, `filing/<symbol>/`

#### 2.2.11 api_request (6개) — `/api/v1/`
- `health/`, `admin/providers/status/`, `admin/providers/rate-limits/`, `admin/providers/cache/`, `admin/providers/test/`, `admin/providers/config/`

### 2.3 누락/미연결 앱

| 앱 | INSTALLED_APPS | urls.py | 상태 |
|----|----|----|----|
| `graph_analysis` | ✅ 등록 | 없음 | 모델/서비스만 구현, API 미공개 (CLAUDE.md 명시) |
| `portfolio` | ✅ 등록 | 없음 | Coach Phase 미공개 |
| `metrics` | ✅ 등록 | 없음 | 내부 서비스 (공유 지표 메타데이터) |

---

## 3. 도입 작업 목록

### 3.1 Phase 1 — drf-spectacular 설치 + 기본 노출 (1 PR, 2시간)

| # | 작업 | 산출물 | 예상 소요 |
|---|------|-------|----------|
| P1-1 | `pyproject.toml`에 `drf-spectacular = "^0.27"` 추가 + `poetry lock`/`install` | `pyproject.toml`, `poetry.lock` | 10분 |
| P1-2 | `INSTALLED_APPS`에 `'drf_spectacular'` 추가 | `config/settings.py` | 5분 |
| P1-3 | `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'` | `config/settings.py` | 5분 |
| P1-4 | `SPECTACULAR_SETTINGS` 추가 (TITLE, VERSION, DESCRIPTION, SERVE_INCLUDE_SCHEMA, SERVERS, TAGS) | `config/settings.py` | 30분 |
| P1-5 | `config/urls.py`에 3개 라우트 추가: `schema/`, `schema/swagger-ui/`, `schema/redoc/` | `config/urls.py` | 10분 |
| P1-6 | `python manage.py spectacular --validate --file schema.yml` 실행 → 워닝 베이스라인 캡처 | `docs/api/schema.yml` (gitignore 또는 산출물) | 30분 |
| P1-7 | `tests/test_schema_generation.py` 추가 — 스키마 생성이 에러 없이 끝나는지 회귀 테스트 | 신규 테스트 1건 | 30분 |

**완료 기준**: `/api/v1/schema/swagger-ui/` 접속 시 251개 엔드포인트가 자동 추론된 (불완전한) 스펙으로 노출됨.

### 3.2 Phase 2 — `@extend_schema` 데코레이터 작성 (분기별 분할)

#### 3.2.1 작업 범위

| 카테고리 | 대상 수 | 데코레이터 작성 난이도 |
|---------|--------|---------------------|
| ViewSet (`ModelViewSet`/`ReadOnlyModelViewSet`) | 5개 클래스 (NewsViewSet, ThesisViewSet, ThesisPremiseViewSet, ThesisIndicatorViewSet, WatchlistViewSet) | 중간 — `@extend_schema_view` + 액션별 |
| `@action` 메서드 | 약 37개 | 중간 — request/response/parameters 명시 |
| APIView 클래스 | 약 130개 | 높음 — `serializer_class` 미지정 다수 → `responses=inline_serializer` 또는 OpenApiExample 직접 작성 |
| 함수형 `@api_view` | 52개 (serverless 전체) | 높음 — `@extend_schema` 데코레이터를 함수에 직접 부착, request body 스펙 수기 작성 필요 |
| **총계** | **약 224개 view 단위** | — |

#### 3.2.2 권장 분할 PR 계획

| PR | 대상 앱 | 추정 view 수 | 우선순위 | 예상 소요 |
|----|--------|------------|---------|----------|
| DOC-PR-1 | `users` (JWT + 세션 + Watchlist + Portfolio) | 32 | 🟢 P0 (외부 클라이언트가 가장 먼저 사용) | 6시간 |
| DOC-PR-2 | `stocks` (38 클래스 8 파일) | 38 | 🟢 P0 (메인 페이지) | 8시간 |
| DOC-PR-3 | `news` (NewsViewSet) | 32 (액션 30 포함) | 🟡 P1 | 5시간 |
| DOC-PR-4 | `macro` + `validation` + `chainsight` | 23 | 🟡 P1 | 5시간 |
| DOC-PR-5 | `rag_analysis` (DataBasket + Session + Monitoring + SSE) | 15 | 🟡 P1 (SSE 응답 스키마 별도 처리) | 4시간 |
| DOC-PR-6 | `thesis` (ViewSet 3 + APIView 8 + 액션 2) | 17 | 🟢 P0 (활성 개발 중) | 5시간 |
| DOC-PR-7 | `serverless` (함수형 52 + Admin 12) | 64 | 🔴 P2 (admin/내부) | 10시간 (가장 큼) |
| DOC-PR-8 | `sec_pipeline` + `api_request` | 8 | 🔴 P2 | 1시간 |
| DOC-PR-9 | tags 정리, `SPECTACULAR_SETTINGS['TAGS']` 일관화, deprecated 표시 (Legacy 세션 인증 등) | — | 🟡 P1 | 2시간 |

**총 예상 소요**: 약 **46시간 (≈ 6 영업일)**

#### 3.2.3 샘플 데코레이터 작성 패턴 (참고)

> 코드 수정 금지 범위이므로 본 보고서에서는 **패턴만 명시**하며, 실제 적용은 별도 PR.

```python
# 패턴 A: APIView (단일 메서드)
@extend_schema(
    summary="포트폴리오 요약 조회",
    tags=["users:portfolio"],
    responses=PortfolioSummarySerializer,
)
class PortfolioSummaryView(APIView): ...

# 패턴 B: ViewSet 액션 (request body 명시)
@extend_schema(
    request=ThesisGenerateRequestSerializer,
    responses={200: ThesisSerializer, 400: OpenApiResponse(description="검증 실패")},
)
@action(detail=False, methods=["post"])
def generate(self, request): ...

# 패턴 C: 함수형 @api_view + 쿼리 파라미터
@extend_schema(
    parameters=[OpenApiParameter("symbol", str, required=True)],
    responses=KeywordResponseSerializer,
)
@api_view(["GET"])
def get_keywords(request, symbol): ...
```

### 3.3 Phase 3 — 사후 품질 보강 (선택, 1주)

| # | 작업 | 비고 |
|---|------|------|
| P3-1 | `OpenApiExample` 주입 — 주요 엔드포인트(스크리너, 가설 생성, RAG 채팅)에 실제 예시 응답 첨부 | 프론트엔드 mock 데이터로도 활용 |
| P3-2 | CI에 `manage.py spectacular --validate --fail-on-warn` 워크플로 추가 | `.github/workflows/api-docs.yml` 신규 |
| P3-3 | `contracts/` OpenAPI 스펙과 자동 생성 결과 diff 체크 (drift 감지) | `qa-architect` 영역 |
| P3-4 | Swagger UI 인증 헤더 (`Bearer <JWT>`) 자동 주입 — `SECURITY` 섹션 추가 | 사용자 테스트 편의 |
| P3-5 | Postman 컬렉션 export (`drf-spectacular-postman-collection`) | 외부 통합 |

### 3.4 위험 요소

| 위험 | 영향 | 완화책 |
|------|------|-------|
| `serverless/views.py` 함수형 뷰 52개의 request body가 코드에서 직접 파싱(`request.data.get(...)`) | 자동 추론 불가 → 데코레이터 작성 부담 큼 | DOC-PR-7을 마지막 PR로 분리, 우선 GET 엔드포인트만 처리 |
| `APIView` 다수가 `serializer_class` 미지정 + 응답을 `Response({'key': value})`로 직접 구성 | 응답 스키마 자동 추출 불가 | `@extend_schema(responses=inline_serializer(name=..., fields=...))` 패턴 강제 |
| `chat/stream/` (SSE) — Server-Sent Events | OpenAPI 3.0 표준에서 SSE 지원 미흡 | 응답을 `OpenApiResponse(description="text/event-stream")`로 명시 + 스트림 페이로드 별도 문서화 |
| Nested router (`thesis/<thesis_id>/premises/`, `<thesis_id>/indicators/`) | URL parameter 추출이 ViewSet 단위에서 이중 (path + lookup) | `@extend_schema(parameters=[...])`로 수동 명시 필요 |
| Legacy 세션 인증 엔드포인트 (`users/login/`, `users/me/` 등 6개) | 신규 클라이언트는 JWT 사용 → 문서 노이즈 | `@extend_schema(deprecated=True)` 표시 |

### 3.5 완료 기준 (Definition of Done)

- [ ] `python manage.py spectacular --validate` 무 워닝
- [ ] `/api/v1/schema/swagger-ui/` 에서 251개 엔드포인트 모두 분류된 태그 아래 노출
- [ ] 각 엔드포인트에 (a) summary 한글, (b) request body 스키마(POST/PUT/PATCH 한정), (c) 200/400/401/404 응답 스키마 명시
- [ ] CI 파이프라인이 스펙 생성 실패 시 빌드 차단
- [ ] `contracts/` 디렉터리(OpenAPI 진실의 소스)와 자동 생성 결과의 일치 검증

---

## 4. 요약

- **현 상태**: OpenAPI/Swagger 자동 생성 도구 미설치, `@extend_schema` 데코레이터 0건. 251개 엔드포인트가 코드 docstring + `sub_claude_md/api-endpoints.md`로만 문서화되어 있음.
- **Phase 1 (즉시 효과)**: drf-spectacular 설치 + 라우트 노출 (2시간) → 자동 추론 기반의 불완전한 스펙 즉시 사용 가능.
- **Phase 2 (전체 데코레이터 작성)**: 약 46시간 (6 영업일), 9개 PR 분할 권장. P0 우선순위는 `users`, `stocks`, `thesis`.
- **최대 위험**: `serverless` 앱 64개 함수형 뷰 — 우선순위를 가장 낮게 두고 별도 PR로 처리.
