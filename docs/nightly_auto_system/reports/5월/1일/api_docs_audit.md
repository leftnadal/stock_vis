# API 문서 감사 보고서

- **감사 일자**: 2026-05-01
- **대상**: Stock-Vis Backend (Django REST Framework)
- **모드**: 읽기 전용 (코드 수정 없음)
- **방법**: `pyproject.toml` / `requirements.txt` / `config/settings.py` / 각 앱 `urls.py` 정적 분석

---

## 현재 상태

### 1.1 패키지 설치 여부

| 도구 | 설치 여부 | 비고 |
|------|----------|------|
| **drf-spectacular** | ❌ 미설치 | `pyproject.toml` `[tool.poetry.dependencies]`에 항목 없음 |
| **drf-yasg** | ❌ 미설치 | 동일 |
| **coreapi** (DRF 내장 schema) | ❌ 미사용 | `DEFAULT_SCHEMA_CLASS` 설정 없음 |

**근거**:
- `pyproject.toml` (line 9-37): `djangorestframework-simplejwt`만 존재. spectacular/yasg 의존성 부재.
- `requirements.txt`: Pinecone/sentence-transformers만 정의. DRF 문서화 도구 없음.
- `grep -i 'spectacular|yasg|swagger|openapi'` on `*.toml` → 0 matches.

### 1.2 Django 설정 상태

`config/settings.py`:

| 항목 | 상태 |
|------|------|
| `INSTALLED_APPS` (line 180-209) | `drf_spectacular`, `drf_yasg` 없음 |
| `REST_FRAMEWORK` (line 341-349) | `DEFAULT_SCHEMA_CLASS` 미설정 — 자동 OpenAPI 스펙 생성 불가 |
| `SPECTACULAR_SETTINGS` | 정의 없음 |

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

→ DRF 기본 `coreapi` schema도 활성화되지 않음.

### 1.3 URL 라우팅 상태

`config/urls.py`: Swagger UI / ReDoc / `/schema/` 엔드포인트 **부재**. API 문서 노출 경로 없음.

### 1.4 코드 내 문서화 데코레이터

| 데코레이터 | 사용 횟수 | 결과 |
|-----------|----------|------|
| `@extend_schema` (drf-spectacular) | **0** | 코드 전반에 미적용 |
| `@swagger_auto_schema` (drf-yasg) | **0** | 코드 전반에 미적용 |
| `@action` (DRF ViewSet) | 약 37회 | 라우팅 용도(문서화 아님). spectacular 도입 시 자동 인식 가능. |

### 1.5 보조 문서

수동 작성 OpenAPI 스펙은 일부 영역에 존재 (서비스 전체가 아닌 특정 기능에 한정):
- `contracts/sec-pipeline-api.yaml`
- `contracts/validation-api.yaml`
- `contracts/chainsight-api.yaml`

> Contract-Driven Development (CLAUDE.md `Harness Protocol` 섹션) 정책에 따른 수동 스펙. 자동 생성과 분리되어 있어 동기화 부담 존재.

### 1.6 결론

| 항목 | 결론 |
|------|------|
| Swagger/OpenAPI **자동 생성** 가능 여부 | ❌ **불가능** |
| 수동 문서 일부 존재 | ✅ `contracts/*.yaml` 3개 (sec-pipeline, validation, chainsight) |
| 즉시 사용 가능한 API 탐색 UI | ❌ 없음 (Swagger UI / ReDoc 모두 미설치) |

---

## 엔드포인트 목록 (앱별 테이블)

> 카운트 기준
> - **path 개수**: 각 `urls.py` 파일의 `path()` 호출 횟수 (직접 등록).
> - **router 자동 생성 endpoint**: ViewSet 등록 시 DRF Router가 생성하는 path 개수 (list/retrieve/create/update/destroy + `@action`).
> - **추정 엔드포인트 합계**: 직접 등록 + router 자동 생성 (실제 HTTP 메서드 분기 제외).

### 2.1 마운트 포인트 (`config/urls.py`)

| Prefix | 인클루드 | 비고 |
|--------|----------|------|
| `/` | `views.api_root` | 루트 페이지 |
| `/health/` | `views.health_check` | 헬스체크 |
| `/admin/` | `admin.site.urls` | Django admin |
| `/api/v1/users/` | `users.urls` | |
| `/api/v1/stocks/` | `stocks.urls` | |
| `/api/v1/news/` | `news.api.urls` | |
| `/api/v1/macro/` | `macro.urls` | |
| `/api/v1/rag/` | `rag_analysis.urls` | |
| `/api/v1/serverless/` | `serverless.urls` | Market Movers + Chain Sight v1 |
| `/api/v1/thesis/` | `thesis.urls` | |
| `/api/v1/validation/` | `validation.api.urls` | |
| `/api/v1/chainsight/` | `chainsight.api.urls` | Chain Sight v2 |
| `/api/v1/sec-pipeline/` | `sec_pipeline.urls` | |
| `/api/v1/` | `api_request.urls` | Provider Admin API |
| `/api/` | `portfolio.urls` | Portfolio Coach (slice 1) |

### 2.2 앱별 엔드포인트 집계

| 앱 | URL Prefix | path() 개수 | ViewSet 라우터 | @action 개수 | 추정 엔드포인트 | 주요 기능 |
|----|-----------|------------|--------------|-------------|---------------|----------|
| **stocks** | `/api/v1/stocks/` | 39 | 0 | 0 | **39** | 차트, 재무제표, 펀더멘털, 스크리너, 검색, EOD 대시보드, 기술지표 |
| **users** | `/api/v1/users/` | 35 | 0 | 0 | **35** | JWT 인증, Portfolio, Watchlist, Favorites, Interests |
| **news** | `/api/v1/news/` | 1 (router) | NewsViewSet (ReadOnlyModelViewSet) | 30 | **32** (list/retrieve + 30 action) | 뉴스 조회, 감성 분석, 키워드, ML 모니터링, 알림 |
| **macro** | `/api/v1/macro/` | 10 | 0 | 0 | **10** | Market Pulse, Fear&Greed, 금리, 인플레이션, VIX, 섹터 |
| **rag_analysis** | `/api/v1/rag/` | 15 | 0 | 0 | **15** | DataBasket, AnalysisSession, SSE 채팅, 모니터링/비용/캐시 |
| **serverless** | `/api/v1/serverless/` | 64 | 0 | 0 | **64** | Market Movers, Breadth, Heatmap, Screener, Alerts, Thesis, ETF, LLM Relations, Institutional, Regulatory, Patent |
| **thesis** | `/api/v1/thesis/` | 11 + 3 routers | ThesisViewSet, ThesisPremiseViewSet, ThesisIndicatorViewSet (모두 ModelViewSet) | 2 (Thesis only) | **약 31** (11 explicit + 3×6 ViewSet + 2 action) | 가설 통제실: 대화형 빌더, 대시보드, 프리미스/인디케이터, 알림 |
| **validation** | `/api/v1/validation/` | 6 | 0 | 0 | **6** | Peer 비교, 메트릭, 리더 비교, 프리셋, LLM 필터 |
| **chainsight** | `/api/v1/chainsight/` | 7 + 1 router | WatchlistViewSet (ModelViewSet) | 5 | **약 18** (7 explicit + 6 ViewSet + 5 action) | 그래프, 제안, 트레이스, 시그널, 섹터/이웃 그래프, 워치리스트 |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | 0 | 0 | **2** | SEC 파이프라인 대시보드, Filing 데이터 |
| **api_request** | `/api/v1/` | 6 | 0 | 0 | **6** | Provider 헬스/상태, Rate limit, 캐시, 테스트, 설정 |
| **portfolio** | `/api/` | 2 | 0 | 0 | **2** | E1/GARP, E5 조정 (Coach slice 1) |
| **config (root)** | `/` | 2 | 0 | 0 | **2** | API root, health check |

**전체 합계 (추정)**: 직접 path 213개 + ViewSet 자동 생성/액션 약 49개 = **약 262개 엔드포인트**

> 주: ModelViewSet은 list/create/retrieve/update/partial_update/destroy → 6개 endpoint를 자동 생성. 실제 HTTP method 분기까지 카운트하면 더 늘어남 (각 path당 GET/POST/PUT/DELETE 분기 가능).

### 2.3 graph_analysis (등록되지 않음)

- `INSTALLED_APPS`에 `graph_analysis` 포함 (`config/settings.py` line 192).
- `graph_analysis/views.py` 파일 존재.
- **하지만** `graph_analysis/urls.py` 부재 + `config/urls.py`에 `include` 없음.
- 결론: 모델/서비스만 구현, REST API **미공개**. CLAUDE.md "Graph Analysis (모델/서비스 완료, API 미구현)" 기재와 일치.

### 2.4 주요 ViewSet/Router 상세

| 앱 | ViewSet | 베이스 클래스 | 자동 라우팅 | @action 수 | 비고 |
|----|---------|------------|-----------|-----------|------|
| news | `NewsViewSet` | `ReadOnlyModelViewSet` | list, retrieve | 30 | 가장 많은 @action 보유. ML/뉴스 분석 대부분 여기 |
| thesis | `ThesisViewSet` | `ModelViewSet` | full CRUD (6) | 2 | |
| thesis | `ThesisPremiseViewSet` | `ModelViewSet` | full CRUD (6) | 0 | nested under thesis_id |
| thesis | `ThesisIndicatorViewSet` | `ModelViewSet` | full CRUD (6) | 0 | nested under thesis_id |
| chainsight | `WatchlistViewSet` | `ModelViewSet` | full CRUD (6) | 5 | |

### 2.5 함수 기반 뷰가 가장 많은 앱

`serverless/views.py`에 `@api_view` 데코레이터 **52개** 존재. 함수 기반 뷰가 다수 → spectacular 도입 시 함수마다 별도 `@extend_schema` 필요.

---

## 도입 작업 목록

### 3.1 추천 도구: **drf-spectacular**

**선정 사유**:
- DRF OpenAPI 3.0 자동 생성 도구 중 사실상의 표준 (drf-yasg는 2023년 이후 업데이트 정체).
- Django 5.x / DRF 3.14+ 호환성 확보 (현재 `pyproject.toml`은 Django 5.1.7).
- ViewSet + `@action` 자동 인식, 함수 기반 뷰는 `@extend_schema` 데코레이터로 보강.

### 3.2 작업 단계

#### Step 1: 설치 및 기본 설정 (예상 1~2시간)

| 작업 | 파일 | 변경 내용 |
|------|------|----------|
| 패키지 추가 | `pyproject.toml` | `drf-spectacular = "^0.27.0"` 추가 → `poetry lock --no-update && poetry install` |
| INSTALLED_APPS 등록 | `config/settings.py` (line 180-209) | `'drf_spectacular'` 추가 |
| DEFAULT_SCHEMA_CLASS 설정 | `config/settings.py` (line 341-349) | `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'` |
| SPECTACULAR_SETTINGS | `config/settings.py` (신규) | TITLE, DESCRIPTION, VERSION, SERVE_INCLUDE_SCHEMA 등 정의 |
| URL 라우팅 추가 | `config/urls.py` | `/api/schema/`, `/api/schema/swagger-ui/`, `/api/schema/redoc/` |

#### Step 2: 자동 추출 검증 (예상 1시간)

`python manage.py spectacular --file schema.yml`로 1차 OpenAPI 스펙 생성 → 누락/오류 식별.

예상 누락 항목:
- 함수 기반 뷰 52개 (`serverless/views.py`) — request/response 스키마 자동 추론 약함
- `@api_view` + 자체 `Response()` 직렬화 — Serializer 미사용 케이스
- SSE/스트리밍 엔드포인트 (`rag_analysis.ChatStreamView`) — 표준 OpenAPI에서 표현 어려움

#### Step 3: 데코레이터 보강 (예상 8~12시간)

각 뷰에 `@extend_schema` 추가. 작업량은 다음 우선순위로 분할 권장:

| 우선순위 | 범위 | 데코레이터 추가 대상 수 | 예상 시간 |
|---------|------|---------------------|----------|
| **P0 (필수)** | 함수 기반 뷰 (Serializer 추론 약함) | 52 (serverless) + 6 (api_request) + 2 (portfolio) + 1 (sec_pipeline) = **약 61** | 4~6시간 |
| **P1 (중요)** | 인증/권한 분기 ViewSet (`@action`) | 30 (news) + 5 (chainsight) + 2 (thesis) = **37** | 2~3시간 |
| **P2 (보강)** | APIView 클래스 (Serializer 사용 多) | 약 90개 클래스 (users, stocks, macro, rag_analysis, validation, thesis, chainsight 등) | 자동 추출이 비교적 잘 되므로 **2~3시간** (예외 케이스만 보강) |

#### Step 4: contracts/ 와 자동 생성 스펙 동기화 (예상 2~4시간)

기존 `contracts/sec-pipeline-api.yaml` / `validation-api.yaml` / `chainsight-api.yaml`은 수동 작성.
- 자동 생성 OpenAPI와 diff → 불일치 식별.
- CLAUDE.md `Contract-Driven Development` 원칙: "스펙과 구현이 불일치하면 구현 쪽을 수정" → 자동 생성된 스펙이 진실의 소스로 승격되는지 정책 결정 필요.

#### Step 5: CI/CD 통합 (예상 1시간)

- `python manage.py spectacular --validate --fail-on-warn` → pre-commit hook 또는 GitHub Actions에 추가.
- 스펙 파일을 repo에 커밋 (선택).

### 3.3 작업량 합계

| 단계 | 예상 시간 |
|------|----------|
| Step 1: 설치/설정 | 1~2시간 |
| Step 2: 검증 | 1시간 |
| Step 3: 데코레이터 보강 | 8~12시간 |
| Step 4: contracts 동기화 | 2~4시간 |
| Step 5: CI 통합 | 1시간 |
| **합계** | **13~20시간** (약 2~3일 작업) |

### 3.4 우선순위 권고 (점진 도입)

| Phase | 산출물 | 가치 |
|-------|--------|------|
| Phase A (Step 1+2, 약 3시간) | Swagger UI 노출 + 자동 추출 OpenAPI 스펙 (불완전) | API 탐색 UI 즉시 확보. 기존 ViewSet은 거의 자동 문서화됨. |
| Phase B (Step 3 P0, 약 5시간) | 함수 기반 뷰 보강 (serverless 등) | 가장 큰 갭(serverless 64 paths) 해소 |
| Phase C (Step 3 P1+P2, 약 5시간) | @action / APIView 보강 | 정확도 향상, request/response 스키마 명세화 |
| Phase D (Step 4+5, 약 5시간) | contracts 동기화 + CI 통합 | 장기 유지보수 안정화 |

### 3.5 위험/주의사항

1. **`@api_view` 함수 기반 뷰의 Serializer 추론 한계**: serverless 앱이 핵심 위험 영역. `@extend_schema(request=..., responses=...)` 명시 필수.
2. **SSE/스트리밍 엔드포인트** (`rag_analysis.ChatStreamView`, `chainsight` SSE 가능성): OpenAPI 표준이 SSE를 잘 표현하지 못함. `responses={(200, 'text/event-stream'): OpenApiTypes.STR}` 등 우회 명시 필요.
3. **하위 라우터(nested) 표현**: thesis의 `<uuid:thesis_id>/premises/`, `<uuid:thesis_id>/indicators/`는 path parameter가 ViewSet에서 직접 파싱되지 않음 → `@extend_schema(parameters=[OpenApiParameter('thesis_id', ...)])` 필요.
4. **인증 분기 응답 코드**: 권한 클래스가 동적으로 변경되는 케이스(`@action(permission_classes=[...])` in `news/api/views.py`)가 30곳 있음 → 응답 401/403 명시.
5. **Provider Admin API의 비공개성**: `api_request/admin/*` 경로는 IsAdminUser 한정. Swagger UI 공개 여부 정책 결정 필요 (`SPECTACULAR_SETTINGS['SERVE_PERMISSIONS']`).

---

## 부록 A. 참고 통계

| 항목 | 값 |
|------|----|
| 전체 `path()` 호출 수 | 213 (urls.py 13개 합계) |
| 추정 엔드포인트 총합 (router 자동 생성 포함) | 약 262 |
| 함수 기반 뷰(`@api_view`) 수 | 52 (serverless 단독) |
| ViewSet 클래스 수 | 5 (NewsViewSet, ThesisViewSet, ThesisPremiseViewSet, ThesisIndicatorViewSet, WatchlistViewSet) |
| ViewSet `@action` 메서드 수 | 약 37 (news 30 + chainsight 5 + thesis 2) |
| APIView/Generic 클래스 수 | 약 118 (전체 `views*.py` 기준) |
| 자동 OpenAPI 스펙 생성 가능 여부 | ❌ |
| 수동 OpenAPI 스펙 (`contracts/`) | 3개 (sec-pipeline, validation, chainsight) |
