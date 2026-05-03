# API 문서 감사 보고서

- **감사 일자**: 2026-05-03
- **감사 범위**: Stock-Vis Django REST API 전체 (12개 앱 + config 루트)
- **감사자**: Claude (read-only static audit)
- **판단 근거**: `config/urls.py` 진입점 + 앱별 `urls.py` / `views*.py` / ViewSet `@action` 정적 분석
- **목적**: API 자동 문서화 도입(drf-spectacular) 전 현재 상태 측정 + 도입 비용 산정

> ⚠️ 본 보고서는 **현재 코드 상태 (portfolio 브랜치)** 만 분석한 결과이며, 실제 응답 페이로드/스키마는 검증하지 않았습니다.
> 엔드포인트 수는 `path()` 항목 + `@action` 데코레이터로 추정한 값이며, ViewSet의 자동 라우팅 (list/create/retrieve/update/destroy) 5가지를 평균치로 가산했습니다.

---

## 0. 핵심 요약 (Executive Summary)

| 영역 | 현재 상태 | 도입 후 효과 |
|------|----------|-------------|
| **OpenAPI 스펙 자동 생성** | ❌ 미구축 | drf-spectacular 1회 설정으로 `/api/schema/` + Swagger UI 즉시 제공 |
| **엔드포인트 총수 (추정)** | **약 240개** (path 198 + ViewSet action 37 + ViewSet CRUD 추가분) | 전체를 자동 스키마화 가능 |
| **수동 문서화 위치** | `config/views.py:api_root` (JSON 하드코딩, ~8개 엔드포인트만 노출) | 폐기 또는 redirect 처리 |
| **인증 스킴 표시** | ❌ JWT/Session 혼재, 클라이언트가 코드를 읽어야 판별 | `@extend_schema(auth=...)` 1줄로 명시 |
| **요청/응답 예시** | ❌ 0개 | OpenAPI `examples` 블록으로 컴포넌트별 추가 가능 |

**최우선 권고 3건**

1. **drf-spectacular 도입 (1.0일 작업)** — 설정 5줄 + URL 1줄이면 `/api/schema/` 자동 생성. ViewSet 기반 (news, thesis, chainsight)은 별도 데코레이터 없이도 적정 품질 스펙 생성됨.
2. **주요 진입 30개 엔드포인트만 `@extend_schema` 부착 (3.0일 작업)** — 전체 240개 중 외부 의존이 큰 인증 7개 (`users/jwt/*`), 검증 6개 (`validation/*`), 스크리너 12개 (`stocks/api/screener/*`, `serverless/screener`), Thesis 5개에 우선 부착하면 프론트엔드/외부 클라이언트 80% 커버.
3. **`config/views.py:api_root` 하드코딩 JSON 폐기** — Swagger UI로 대체. 현재 `/api/v1/macro/`, `/api/v1/rag/`, `/api/v1/serverless/`, `/api/v1/thesis/`, `/api/v1/validation/`, `/api/v1/chainsight/`, `/api/v1/sec-pipeline/` 등 7개 앱이 `api_root` 응답에 누락되어 있어 잘못된 정보 소스가 됨.

---

## 1. 현재 상태

### 1.1 의존성 점검

| 패키지 | requirements.txt | pyproject.toml | 코드 사용 흔적 |
|--------|------------------|----------------|---------------|
| `drf-spectacular` | ❌ | ❌ | ❌ |
| `drf-yasg` | ❌ | ❌ | ❌ |
| `coreapi` | ❌ | ❌ | ❌ |
| `djangorestframework-simplejwt` | (간접) | ✅ `^5.5.1` | ✅ |
| `djangorestframework` | (간접) | (간접) | ✅ (settings `REST_FRAMEWORK` 존재) |

- `pyproject.toml`은 Poetry로 관리되고 있으며 OpenAPI 스펙 생성 패키지는 미설치.
- `requirements.txt`는 KB(`shared_kb/`) 의존성 4종 (`pinecone`, `sentence-transformers` 등)만 포함 — 백엔드 의존성 소스가 아님.
- 검색 결과 `extend_schema`, `swagger_auto_schema`, `drf_spectacular`, `drf_yasg` 임포트 0건. 즉 **데코레이터 기반 수동 문서화도 0건**.

### 1.2 자동 스펙 생성 가능 여부

- 가능. ViewSet/APIView/`@api_view` 모두 DRF 표준 구조이므로 drf-spectacular의 `SpectacularAPIView` 1개만 등록하면 즉시 스펙 추출 시작.
- 단, **함수형 뷰 (FBV)**가 `serverless/views.py` 24개, `sec_pipeline/views.py` 1개, `api_request/admin_views.py` 6개에 분포 — 이들은 `@extend_schema` 또는 `OpenApiParameter` 명시 없이는 request/response 추정 정확도가 낮음 (DRF Serializer를 사용하지 않는 경우).
- ViewSet 기반 (3개): `news.NewsViewSet` (30 actions), `thesis.ThesisViewSet` + nested 2개, `chainsight.WatchlistViewSet` (5 actions) — 자동 추출 품질 우수.

### 1.3 현재 "문서" 역할을 하는 위치

| 위치 | 역할 | 문제점 |
|------|------|--------|
| `config/views.py:api_root` | JSON 하드코딩 응답 | 7개 앱 누락. 신규 엔드포인트 추가 시 자동 갱신 안 됨 |
| `templates/api_root.html` | 브라우저용 HTML | 정적 HTML이라 빠르게 stale |
| `CLAUDE.md` + `sub_claude_md/api-endpoints.md` | 개발자용 가이드 | 사람이 갱신 — 현재 신뢰도 낮음 |
| `docs/features/*.md` | 기능별 설계 문서 | API 스펙이 아닌 흐름 위주 |

---

## 2. 엔드포인트 목록 (앱별 테이블)

### 2.1 앱별 총수 집계

| # | 앱 | 마운트 prefix | path() 수 | ViewSet/`@action` 추가분 | 추정 총 엔드포인트 |
|---|----|--------------|----------:|------------------------:|-------------------:|
| 1 | `users` | `/api/v1/users/` | 35 | — | **35** |
| 2 | `stocks` | `/api/v1/stocks/` | 39 | — | **39** |
| 3 | `news` | `/api/v1/news/` | 1 (router) | NewsViewSet `@action` 30 + CRUD ~5 | **~35** |
| 4 | `macro` | `/api/v1/macro/` | 10 | — | **10** |
| 5 | `rag_analysis` | `/api/v1/rag/` | 15 | — | **15** |
| 6 | `serverless` | `/api/v1/serverless/` | 64 | — | **64** |
| 7 | `thesis` | `/api/v1/thesis/` | 11 | ThesisViewSet (CRUD+2 actions) + nested premise/indicator (CRUD x2) | **~25** |
| 8 | `validation` | `/api/v1/validation/` | 6 | — | **6** |
| 9 | `chainsight` | `/api/v1/chainsight/` | 7 | WatchlistViewSet (CRUD + 5 actions) | **~17** |
| 10 | `sec_pipeline` | `/api/v1/sec-pipeline/` | 2 | — | **2** |
| 11 | `api_request` | `/api/v1/` | 6 | — | **6** |
| 12 | `portfolio` | `/api/` | 2 | — | **2** |
|   | `config` (루트) | `/` | 2 (api_root, health) | — | **2** |
|   | **합계** | | **200** | **~37 + ViewSet CRUD** | **~258** |

> ViewSet의 자동 생성 라우트 (list, create, retrieve, update, partial_update, destroy)는 path()에는 1개로 등록되지만 실제로는 5~6개의 HTTP method 조합을 노출함.

### 2.2 핵심 앱별 상세

#### users (35 엔드포인트)

| 그룹 | 패턴 | 비고 |
|------|------|------|
| JWT 인증 | `jwt/signup/`, `jwt/login/`, `jwt/logout/`, `jwt/refresh/`, `jwt/verify/`, `jwt/change-password/`, `jwt/profile/` | 7개. SimpleJWT `TokenRefreshView` 포함 |
| 세션 인증 (legacy) | `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/`, `favorites/*` | 7개 + favorites 3개 |
| Portfolio | `portfolio/` 루트 + summary/table/refresh + `<pk>` + `symbol/<symbol>/` 3종 | 9개 |
| 관심사 | `interests/`, `interests/<pk>/` | 2개 |
| Watchlist | `watchlist/` + `<pk>` + 6개 sub-route (add-stock, bulk-add, bulk-remove, stocks, stocks/<symbol>, stocks/<symbol>/remove) | 8개 |

#### stocks (39 엔드포인트)

| 그룹 | 개수 | 비고 |
|------|----:|------|
| Dashboard / Detail / Search | 3 | HTML 템플릿 뷰 1개 (`DashboardView`) 포함 — REST 외 |
| 차트/Overview/재무제표 (BS/IS/CF) | 5 | symbol path 변수 |
| Sync | 1 | `api/sync/<symbol>/` |
| MVP | 4 | RAG 컨텍스트 포함 |
| 기술적 지표 | 3 | Indicator/Signal/Comparison |
| Symbol 검색 | 3 | symbols/validate/popular |
| Market Movers | 1 | `api/market-movers/` |
| Fundamentals | 5 | key-metrics/ratios/dcf/rating/all |
| Screener | 6 | screener/large-cap/high-dividend/sector/low-beta/exchange |
| Quotes | 5 | index/symbol/batch/major-indices/sector-performance |
| EOD Dashboard | 3 | dashboard/signal/<id>/pipeline-status |

#### serverless (64 엔드포인트, 최다)

| 그룹 | 개수 | 비고 |
|------|----:|------|
| Admin Dashboard | 12 | overview/stocks/screener/market-pulse/news/system/tasks + actions/status + news categories 3개 |
| Market Movers | 4 | movers + movers/<symbol> + sync + sync-now |
| Keywords | 4 | batch/generate-all/generate-screener/<symbol> |
| Market Breadth | 3 | breadth/history/sync |
| Sector Heatmap | 3 | sectors/sectors/<sector>/stocks/sync |
| Screener Presets | 7 | presets + trending/shared/import + <id>/execute/share |
| Screener Filters / Advanced | 2 | filters + screener |
| Alerts | 6 | alerts + history + history/<id>/read|dismiss + <id>/toggle |
| Investment Thesis (Phase 2.3) | 4 | generate/<id>/shared/<code>/list |
| Chain Sight ETF | 9 | etf/* + themes/* |
| LLM Relations (Phase 5) | 4 | extract/sync/stats/<symbol> |
| Institutional (Phase 7) | 3 | sync/<symbol>/peers/<symbol> |
| Regulatory + Patent (Phase 8) | 2 | regulatory/<symbol>, patent-network/<symbol> |
| Health | 1 | `health` |

> 함수형 뷰(FBV) 24개 사용 — drf-spectacular 도입 시 `@extend_schema` 부착 필수 영역.

#### news (~35 엔드포인트, ViewSet 기반)

`NewsViewSet`은 `r''` basename으로 등록되어 있고 `@action` 30개 + 표준 CRUD 5개 자동 노출. 주요 action:

| 카테고리 | url_path 예시 |
|----------|--------------|
| 종목별 뉴스 | `stock/<symbol>`, `stock/<symbol>/sentiment` |
| 키워드/검색 | `daily-keywords`, `daily-keywords/generate`, `keyword-detail` |
| 피드 | `market-feed`, `personalized-feed`, `interest-options` |
| 이벤트/임팩트 | `news-events`, `news-events/impact-map` |
| ML 모니터링 | `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `ml-trend`, `ml-rollback-preview`, `ml-rollback` |
| Admin | `collection-logs`, `pipeline-health`, `llm-usage`, `task-timeline`, `neo4j-status`, `alerts`, `alerts/<pk>/resolve` |

> 각 `@action`마다 `permission_classes` 다름 (AllowAny / IsAuthenticated / IsAdminUser 혼재) — Swagger에서 인증 요구 표시 유용.

#### thesis (~25 엔드포인트)

| 그룹 | 패턴 | 개수 |
|------|------|----:|
| Conversation | `conversation/start|respond|news-issues|suggest/` | 4 |
| Monitoring | `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<id>/readings/` | 2 |
| Alerts | `alerts/`, `alerts/<aid>/read/` | 2 |
| ThesisViewSet | CRUD (5) + `@action` 2 | ~7 |
| Premise nested | `<thesis_id>/premises/` CRUD | ~5 |
| Indicator nested | `<thesis_id>/indicators/` CRUD | ~5 |

#### chainsight (~17 엔드포인트)

| 그룹 | 개수 |
|------|----:|
| 마켓 뷰 (seeds, sector graph, signals, trace) | 4 |
| Symbol 기반 (neighbors, graph, suggestions) | 3 |
| WatchlistViewSet CRUD + `@action` 5 (add-stock, remove-stock, refresh-graph, suggest-stocks, accept-suggestion) | ~10 |

#### 기타 소형 앱

- **macro** (10): Market Pulse 종합 + 6개 단일 지표 + 2개 sync
- **rag_analysis** (15): Basket 6 + Session 4 + Monitoring 5
- **validation** (6): symbol별 summary/metrics/leader-comparison/presets/peer-preference/llm-filter
- **sec_pipeline** (2): admin/dashboard + filing/<symbol>
- **api_request** (6): health + admin/providers 5종
- **portfolio** (2): coach/e1/garp + coach/e5/adjustment
- **config 루트** (2): api_root + health_check

---

## 3. 도입 작업 목록

### 3.1 Phase 0: drf-spectacular 설치 + 기본 설정 (예상 0.5일)

| 단계 | 작업 | 산출물 |
|------|------|--------|
| 0-1 | `poetry add drf-spectacular` | `pyproject.toml` 갱신 |
| 0-2 | `INSTALLED_APPS`에 `'drf_spectacular'` 추가 | `config/settings.py:180` 부근 |
| 0-3 | `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'` | `config/settings.py:341` 부근 |
| 0-4 | `SPECTACULAR_SETTINGS` 추가 (TITLE, DESCRIPTION, VERSION, SERVE_INCLUDE_SCHEMA=False, COMPONENT_SPLIT_REQUEST=True) | settings.py |
| 0-5 | `config/urls.py`에 `SpectacularAPIView`, `SpectacularSwaggerView`, `SpectacularRedocView` URL 등록 | `/api/schema/`, `/api/schema/swagger-ui/`, `/api/schema/redoc/` 노출 |
| 0-6 | `config/views.py:api_root` JSON 응답을 `/api/schema/swagger-ui/`로 redirect 처리 또는 안내 |  |
| 0-7 | `python manage.py spectacular --color --file schema.yml` 실행 | 초기 스펙 파일 생성 + warning 점검 |

**예상 결과**: 240개 전체 엔드포인트의 80% 정도가 자동 스키마화. ViewSet/Serializer 사용 영역은 거의 완벽, FBV는 request/response 미상으로 표시됨.

### 3.2 Phase 1: ViewSet 영역 보강 — `@extend_schema` 부착 (예상 1.0일)

| 대상 | 파일 | 작업량 |
|------|------|--------|
| `NewsViewSet` (~35 엔드포인트) | `news/api/views.py` | 각 `@action`마다 1줄씩 `@extend_schema(summary=..., responses=...)` 추가. 30개 |
| `ThesisViewSet` + premise/indicator (~17) | `thesis/views/thesis_views.py`, `thesis/views/conversation_views.py`, `thesis/views/monitoring_views.py` | UUID PK 인자 명시 + `examples` 1~2개 |
| `WatchlistViewSet` (~10) | `chainsight/views/watchlist_views.py` | 5개 `@action`에 `request`, `responses` 명시 |

> 작업 패턴: 신규 코드 추가만. 기존 비즈니스 로직 0줄 수정.

### 3.3 Phase 2: APIView/FBV 보강 (예상 2.0일)

| 영역 | 우선순위 | 엔드포인트 수 | 비고 |
|------|---------|--------------:|------|
| `users/jwt_views.py` (인증 7) | **HIGH** | 7 | TokenObtain/Refresh는 SimpleJWT가 기본 제공하지만 커스텀 응답 명시 필요 |
| `validation/api/views.py` (검증 6) | **HIGH** | 6 | symbol path 변수 + LLM 응답 구조 |
| `stocks/views_screener.py` + `serverless/views` 스크리너 12 | **HIGH** | 12 | 쿼리파라미터 다수 — `OpenApiParameter` 명시 필요 |
| `thesis/views/conversation_views.py` (대화형 4) | **HIGH** | 4 | request body가 자유 형식 — `inline_serializer` 권장 |
| `stocks/views_fundamentals.py` (5), `views_indicators.py` (3), `views_search.py` (3) | MEDIUM | 11 | 비교적 단순한 GET |
| `serverless/views.py` 함수형 (Market Movers + Chain Sight Phase 3/5/7/8) | MEDIUM | 24 | LLM/외부 API 응답이 복잡 — examples 2~3개씩 필요 |
| `serverless/views_admin.py` (Admin 12) | LOW | 12 | 내부 도구 — 최소 summary만 |
| `macro/views.py` (10), `rag_analysis/views.py` (15) | LOW | 25 | Serializer 잘 정의되어 있어 자동 추출만으로도 충분 |
| `api_request/admin_views.py`, `sec_pipeline/views.py`, `portfolio/views.py` | LOW | 10 | 합쳐서 |

### 3.4 Phase 3: 검증 + CI 통합 (예상 0.5일)

| 단계 | 작업 |
|------|------|
| 3-1 | `python manage.py spectacular --validate --fail-on-warn` 실행해서 warning 0 만들기 |
| 3-2 | GitHub Actions 워크플로에 spectacular validate step 추가 (`.github/workflows/`) |
| 3-3 | `frontend/`에서 OpenAPI Codegen 또는 `openapi-typescript` 도입 검토 (선택) |
| 3-4 | `contracts/` 디렉토리에 `schema.yml` 자동 export → `make export-schema` 등 |

### 3.5 총 작업량 산정

| Phase | 작업일 | 누적 |
|-------|------:|----:|
| 0. 설치 + 기본 설정 | 0.5일 | 0.5일 |
| 1. ViewSet 영역 보강 | 1.0일 | 1.5일 |
| 2. APIView/FBV 보강 (HIGH 우선만) | 1.5일 | 3.0일 |
| 2. APIView/FBV 보강 (MEDIUM/LOW까지 전체) | +1.5일 | 4.5일 |
| 3. 검증 + CI 통합 | 0.5일 | 5.0일 |

**최소 진입 비용**: Phase 0 + Phase 1 = **1.5일** → 240개 엔드포인트 중 80% 자동 스키마 + ViewSet 영역 100% 정밀화.
**권장 범위**: Phase 0~2 HIGH + Phase 3 = **3.5일** → 외부 클라이언트 80% 커버리지 달성.
**전체 완성**: **5.0일** → CI 통합 + warning 0.

---

## 4. 부수 발견사항 (참고)

1. **`api_root` 응답이 stale** — `config/views.py:api_root`는 `analysis` 앱을 노출하지만 (`config/urls.py`에 미등록) 실제로는 없는 앱. 반대로 macro/rag/serverless/thesis/validation/chainsight/sec-pipeline 7개 앱은 응답에 누락. drf-spectacular 도입 시 자동으로 해결.

2. **CLAUDE.md의 graph_analysis 앱 표기와 실제 일치** — `/api/v1/graph/`로 마운트되어야 한다고 표기되어 있으나 `config/urls.py`에 등록 없음. 코드(`graph_analysis/views.py`)는 존재하지만 URL 미연결. → 자동 문서에서 "고스트 앱" 식별 가능.

3. **Mount prefix 일관성 부족** — 대부분 `/api/v1/`인데 `portfolio`만 `/api/`로 마운트되어 v1 prefix 없음. `api_request`는 prefix 없이 `/api/v1/health/`, `/api/v1/admin/providers/*`로 직접 들어감. 스키마화 시 명세 그대로 반영됨.

4. **인증 스킴 혼재** — `users/`에 JWT 7개와 세션 7개가 공존, `news/api/views.py`의 `@action`마다 `permission_classes`가 다름. drf-spectacular는 `OpenApiAuthenticationExtension`으로 SimpleJWT를 자동 인식하므로 별도 설정 없이 Bearer 표시 가능.

5. **함수형 뷰 비중** — serverless 24개, sec_pipeline 1개, api_request 6개 = 총 31개. 자동 추출 품질이 떨어지는 영역이며 Phase 2의 핵심 작업 대상.

---

## 5. 결론

- **현재 자동 문서화 인프라 0**. 하지만 DRF 표준 구조라서 **drf-spectacular 도입 마찰 매우 낮음** (1.5일 만에 80% 자동 스키마 가능).
- 추정 엔드포인트 **약 240개** — 직접 카운트한 path 200개 + ViewSet 자동 라우트 추가분.
- 우선순위는 **인증(users/jwt) → 검증(validation) → 스크리너(stocks/serverless) → Thesis 대화형** 순으로 부착 권장.
- `config/views.py:api_root`의 하드코딩 JSON은 폐기 또는 redirect 처리 권장 (현재 7개 앱 누락 + 1개 ghost 앱 표시).
