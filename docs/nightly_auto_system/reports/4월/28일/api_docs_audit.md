# API 문서 감사 보고서

> **감사 일자**: 2026-04-28
> **대상**: Stock-Vis Backend (Django 5.1.7 + DRF)
> **모드**: 읽기 전용 (코드 수정 없음)
> **분석 기준**: `config/urls.py`에 등록된 13개 URLConf + `pyproject.toml` / `requirements.txt`

---

## 현재 상태

### 1. OpenAPI/Swagger 도구 설치 여부

| 항목 | 결과 |
|------|------|
| **drf-spectacular** | ❌ **미설치** |
| **drf-yasg** | ❌ **미설치** |
| **pyproject.toml dependencies** | django, DRF, simple-jwt, channels, celery 등 (스키마 도구 없음) |
| **requirements.txt** | (스키마 도구 없음) |
| **poetry.lock** | spectacular/yasg 매치 0건 |
| **설치 인지 흔적** | `marketpulse/api/views/schema.py:7`에 `"drf-spectacular 도입은 별도 PR"` 주석으로 도입 의지만 남아있음 |

### 2. Swagger/OpenAPI 스펙 자동 생성 가능 여부

**결론: 자동 생성 불가능**. 단, 부분적인 수동 스펙은 존재.

- **자동 생성**: 불가 (DRF 기본 `coreapi` 스키마는 deprecated, 활성화 안 됨)
- **수동 스펙**: `contracts/marketpulse-v2-api.yaml` 1개만 작성됨 → `/api/v2/market-pulse/schema` 엔드포인트(`marketpulse/api/views/schema.py`)에서 정적 YAML/JSON으로 서빙
  - 즉 Market Pulse v2(6개 엔드포인트)에 대해서만 수동 스펙 존재
  - v1 API(전체 약 250+ 개)는 스펙 0건
- **`extend_schema` / `swagger_auto_schema` 데코레이터 사용 흔적**: 0건 (`@api_view`만 검출됨 — DRF 기본 데코레이터로 스키마와 무관)
- **타입 힌트/Serializer 기반**: Serializer는 풍부하게 정의되어 있어 drf-spectacular 도입 시 즉시 자동 추론 가능

### 3. 현재 API 문서화 자산

| 자산 | 위치 | 비고 |
|------|------|------|
| OpenAPI YAML (수동) | `contracts/marketpulse-v2-api.yaml` | Market Pulse v2 전용 |
| API 엔드포인트 목록 (사람용) | `sub_claude_md/api-endpoints.md` | 정합성 미검증 |
| API 계약 (frontend 공유) | `contracts/shared-types.ts` (CLAUDE.md 언급) | 타입 일부만 포함 |
| 스키마 서빙 엔드포인트 | `GET /api/v2/market-pulse/schema?format=yaml\|json` | 정적 파일 응답 |

---

## 엔드포인트 목록 (앱별)

### 전체 라우팅 (`config/urls.py`)

```
/                                  → views.api_root
/health/                           → views.health_check
/admin/                            → Django admin
/api/v1/users/                     → users.urls
/api/v1/stocks/                    → stocks.urls
/api/v1/news/                      → news.api.urls
/api/v1/macro/                     → macro.urls
/api/v1/rag/                       → rag_analysis.urls
/api/v1/serverless/                → serverless.urls
/api/v1/thesis/                    → thesis.urls
/api/v1/validation/                → validation.api.urls
/api/v1/chainsight/                → chainsight.api.urls
/api/v1/sec-pipeline/              → sec_pipeline.urls
/api/v1/                           → api_request.urls (Provider Admin)
/api/v2/market-pulse/              → marketpulse.api.urls
```

### 앱별 엔드포인트 수

| # | 앱 | 마운트 경로 | 엔드포인트 수 | View 파일 수 | 주요 영역 |
|---|----|-------------|---------------|--------------|-----------|
| 1 | **users** | `/api/v1/users/` | **35** | 1 (`views.py`) + `jwt_views.py` | JWT 인증(7) + 세션(6) + 즐겨찾기(3) + 포트폴리오(9) + 관심사(2) + Watchlist(8) |
| 2 | **stocks** | `/api/v1/stocks/` | **39** | 9개 (views_*.py) | 메인(3) + 차트/재무(5) + sync(1) + MVP(4) + 지표(3) + 검색(3) + movers(1) + fundamentals(5) + screener(6) + quotes(5) + EOD(3) |
| 3 | **news** | `/api/v1/news/` | **~36** | 1 (`api/views.py`, NewsViewSet) | DefaultRouter base actions(6) + `@action` 30개 (sentiment, daily-keywords, ml-status, pipeline-health, alerts 등) |
| 4 | **macro** | `/api/v1/macro/` | **10** | 1 (`views.py`) | pulse, fear-greed, interest-rates, inflation, global-markets, calendar, vix, sectors, sync(2) |
| 5 | **rag_analysis** | `/api/v1/rag/` | **15** | 1 (`views.py`) | DataBasket(6) + AnalysisSession(4) + Monitoring(5) |
| 6 | **serverless** | `/api/v1/serverless/` | **64** | 2 (`views.py`, `views_admin.py`) | Admin Dashboard(12) + Movers(8) + Breadth(3) + Heatmap(3) + Presets(7) + Filters(1) + Advanced Screener(1) + Alerts(6) + Thesis(4) + ETF Holdings(9) + LLM Relations(4) + Institutional(3) + Regulatory/Patent(2) + Health(1) |
| 7 | **thesis** | `/api/v1/thesis/` | **~26** | `views/` 패키지 (3개 ViewSet + 컨버세이션 뷰들) | Conversation(4) + ThesisViewSet(5: list/create/retrieve/patch + close) + Monitoring(2) + Alerts(2) + Premise nested(6) + Indicator nested(6 + suggest 1) |
| 8 | **validation** | `/api/v1/validation/` | **6** | 1 (`api/views.py`) | summary, metrics, leader-comparison, presets, peer-preference, llm-filter (모두 symbol scoped) |
| 9 | **chainsight** | `/api/v1/chainsight/` | **~18** | `api/views.py` + `views/watchlist_views.py` | 마켓 뷰(4) + 동적(3) + WatchlistViewSet(6 base + 5 @action = 11) |
| 10 | **sec_pipeline** | `/api/v1/sec-pipeline/` | **2** | 1 (`views.py`) | admin/dashboard, filing/<symbol> |
| 11 | **api_request** | `/api/v1/` | **6** | `admin_views.py` | health, providers/status, rate-limits, cache, test, config (Provider Admin) |
| 12 | **marketpulse v2** | `/api/v2/market-pulse/` | **6** | `api/views/` 패키지 (각 1개) | overview, cards/{id}/detail, news/refresh, i18n, health, schema |
| 13 | **config (root)** | `/` | **2** | `config/views.py` | api_root, health |

### 합계

- **총 엔드포인트 (URL 패턴 기준)**: **약 265개**
- **앱 수**: 12개 (config 루트 포함 13개)
- **View 클래스/함수 수 (대략)**:
  - APIView/ViewSet 클래스: ~80개
  - `@api_view` 함수형 뷰 (serverless): 64개
  - `@action` 데코레이터: ~40개

### 인증/권한 분포 (관찰)

| 패턴 | 위치 |
|------|------|
| JWT 인증 (전역 default) | `config/settings.py:339-345` (`IsAuthenticatedOrReadOnly`) |
| `IsAuthenticated` 명시 | thesis ViewSet, watchlist 등 |
| `IsAdminUser` | `api_request/admin_views.py`, `serverless/views.py` (admin/dashboard, ml-rollback, alerts 등) |
| `AllowAny` | `marketpulse/api/views/schema.py`, news ViewSet 일부 (`market-feed`, `interest-options`) |
| Throttle scopes | `market_pulse_user`, `market_pulse_user_hour`, `market_pulse_llm` (마켓 펄스 v2만 명시 적용) |

---

## 도입 작업 목록

### Phase 1 — 기본 설치 + 자동 스펙 가동 (소: 0.5~1일)

| 단계 | 작업 | 산출물 | 예상 시간 |
|------|------|--------|-----------|
| 1.1 | `poetry add drf-spectacular` (또는 `^0.27`) | `pyproject.toml` + `poetry.lock` | 0.1일 |
| 1.2 | `INSTALLED_APPS`에 `'drf_spectacular'` 추가 (`config/settings.py:176`) | settings.py 수정 | 0.05일 |
| 1.3 | `REST_FRAMEWORK`에 `DEFAULT_SCHEMA_CLASS = 'drf_spectacular.openapi.AutoSchema'` 추가 | settings.py:338 블록 | 0.05일 |
| 1.4 | `SPECTACULAR_SETTINGS` dict 정의 (TITLE, DESCRIPTION, VERSION, SERVERS, TAGS, SCHEMA_PATH_PREFIX 등) | settings.py | 0.2일 |
| 1.5 | `config/urls.py`에 3개 라우트 추가: `schema/`, `schema/swagger-ui/`, `schema/redoc/` | urls.py | 0.05일 |
| 1.6 | `python manage.py spectacular --file schema.yml` 검증 → 워닝 카탈로그 생성 | schema.yml + 경고 목록 | 0.2일 |
| 1.7 | 기존 `marketpulse/api/views/schema.py`(수동 YAML)와의 충돌 정리 (계속 유지 vs 통합) | DECISIONS.md 1줄 | 0.1일 |

**Phase 1 산출물**: 자동 생성된 OpenAPI 3.0 스펙 + Swagger UI 접속 가능. 약 70~80% 정확도 (Serializer 자동 추론).

### Phase 2 — 추론 한계 보강 (`@extend_schema`) (중: 3~5일)

drf-spectacular 자동 추론이 약한 곳에 데코레이터 추가. 우선순위 매핑:

| 우선순위 | 대상 | 예상 작업량 |
|----------|------|-------------|
| **P0 (필수)** | `@api_view` 함수형 뷰 (serverless 64개) — Serializer 추론 거의 안 됨 | 64개 × 평균 10분 = 약 11시간 |
| **P0** | URL `<symbol>` / `<int:pk>` path param 타입 명시 (`OpenApiParameter`) | 대부분 자동 추론, 일부 보정 약 30개 × 5분 = 2.5시간 |
| **P1** | NewsViewSet의 30개 `@action` (custom url_path, multiple permission) | 30개 × 10분 = 5시간 |
| **P1** | thesis/chainsight nested router (`<uuid:thesis_id>`) — path param 가독성 | 약 15개 × 5분 = 1.25시간 |
| **P2** | `request_body` Serializer가 명시되지 않은 POST 엔드포인트 (서버리스 admin actions, change-password 등) | 약 25개 × 10분 = 4시간 |
| **P2** | Response 다중 status code (200/202/400/404/409 등) 정의 | 핵심 엔드포인트 30개 × 15분 = 7.5시간 |
| **P3** | `tags` 분류 (앱별 그룹핑) — 도구가 자동 분류 못 하는 경우 보강 | 약 1시간 |
| **P3** | examples 추가 (재무 데이터, 가설 페이로드 등) | 50개 × 10분 = 8시간 |

**Phase 2 합계**: 약 **40시간 (5인일)** — 단, P0/P1만 우선 처리하면 약 20시간(2.5인일).

### Phase 3 — 일관성 / 운영 (소: 1~2일)

| 단계 | 작업 | 산출물 |
|------|------|--------|
| 3.1 | CI 파이프라인에 `manage.py spectacular --validate --fail-on-warn` 추가 | `.github/workflows/*.yml` |
| 3.2 | `contracts/marketpulse-v2-api.yaml`과 자동 생성 스펙 diff 검증 — 합치 또는 폐기 결정 | DECISIONS.md |
| 3.3 | `contracts/shared-types.ts` 자동 생성 파이프라인 (e.g. `openapi-typescript`) | npm 스크립트 |
| 3.4 | 프론트엔드 API 클라이언트 자동 생성 검토 (선택) | `lib/api/generated/` |
| 3.5 | API versioning 정책 명시 (현재 v1/v2 혼재) | docs/architecture/ |

### 종합 작업량

| 시나리오 | 작업량 | 효과 |
|----------|--------|------|
| **최소 도입** (Phase 1만) | **0.5~1일** | Swagger UI 즉시 사용 가능, 70% 정확도 |
| **권장 도입** (Phase 1 + Phase 2 P0/P1) | **약 4~5일** | 핵심 엔드포인트 95% 정확, frontend 신뢰 가능 |
| **완전 도입** (Phase 1+2+3) | **약 8~10일** | CI 검증 + 프론트엔드 타입 자동 생성 |

### 위험 / 주의사항

1. **`@api_view` 함수 무더기 (serverless 64개)**: drf-spectacular가 Serializer를 추론하지 못해 응답 스키마가 비어있게 됨. → 각 함수에 `@extend_schema(request=..., responses=...)` 필수
2. **수동 YAML과의 dual source**: `contracts/marketpulse-v2-api.yaml`이 자동 스펙과 어긋나면 진실의 소스가 모호해짐. Phase 1.7에서 단일 소스로 정리해야 함
3. **legacy 엔드포인트**: `serverless/urls.py`에 `# LEGACY REMOVED` 주석으로 이미 제거된 라우트 메모가 다수 → 스펙 생성 후 deprecated 마킹 필요한 라우트(`etf/*`의 `LEGACY_KEEP_UNTIL_DC2`) 식별 필요
4. **인증 차이가 큼**: 기본 `IsAuthenticatedOrReadOnly` + 개별 `IsAdminUser`/`AllowAny` 혼재 → `SPECTACULAR_SETTINGS`에 SecurityScheme 정의해야 Swagger UI에서 JWT 토큰 입력 가능
5. **Throttle 표기**: 마켓 펄스 v2의 throttle scope 3종은 자동 스펙에 반영 안 됨 → 수동 명시 필요
6. **DRF default 충돌**: 현재 `REST_FRAMEWORK`에 `DEFAULT_SCHEMA_CLASS` 누락 — drf-spectacular 설치 시 명시 추가 필수

### 빠른 시작 권장 순서

1. **Day 1**: Phase 1.1~1.6 — Swagger UI 가동 + 자동 스펙 검증 (워닝 목록 확보)
2. **Day 2~3**: Phase 2 P0 (serverless 64개에 `@extend_schema` 일괄 추가)
3. **Day 4**: Phase 2 P1 (NewsViewSet 30개 `@action`)
4. **Day 5**: Phase 1.7 + 3.1 (수동 YAML 정리 + CI 검증)

---

## 부록: 분석 근거 파일

- `pyproject.toml` (line 9~37): 의존성 목록
- `config/settings.py` (line 176~206, 338~353): INSTALLED_APPS, REST_FRAMEWORK
- `config/urls.py` (전체): 13개 마운트 포인트
- 각 앱 `urls.py`: 13개 파일 (`api_request`, `chainsight/api`, `macro`, `marketpulse/api`, `news/api`, `rag_analysis`, `sec_pipeline`, `serverless`, `stocks`, `thesis`, `users`, `validation/api`, `config`)
- `marketpulse/api/views/schema.py` (line 7): drf-spectacular 도입 인지 흔적
- `serverless/views.py`: `@api_view` 64개 (스키마 추론 한계 영역)
- `news/api/views.py`: NewsViewSet의 `@action` 30개
