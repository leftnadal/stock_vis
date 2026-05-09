# API 문서 감사 보고서

- 감사일: 2026-05-10
- 대상 브랜치: portfolio
- 감사 범위: Backend 전체 앱의 URL/View/스키마 문서화 상태
- 산출물 위치: `docs/nightly_auto_system/reports/5월/9일/api_docs_audit.md`

---

## 현재 상태

### 요약

| 항목 | 상태 | 비고 |
|------|------|------|
| OpenAPI 라이브러리 설치 | ✅ 설치됨 | `drf-spectacular ^0.29.0`, `drf-spectacular-sidecar ^2026.4.14` |
| INSTALLED_APPS 등록 | ✅ 완료 | `drf_spectacular`, `drf_spectacular_sidecar` |
| DEFAULT_SCHEMA_CLASS 설정 | ✅ 완료 | `drf_spectacular.openapi.AutoSchema` |
| SPECTACULAR_SETTINGS | ✅ 정의됨 | TITLE/VERSION 2.0, ENUM_NAME_OVERRIDES 4개 |
| 스키마 노출 URL | ⚠️ 부분 노출 | `/api/v2/schema/`, `/api/v2/swagger/`, `/api/v2/redoc/` 만 등록 |
| 스키마 prefix 필터 | ⚠️ v2 위주 | `SCHEMA_PATH_PREFIX = r'/api/v[12]'` (v1도 포함되지만 v1은 명시적 데코레이션 없음) |
| DISABLE_ERRORS_AND_WARNINGS | ⚠️ True | "graceful fallback noise 무시" 주석 — v1 endpoint 스키마 정확도가 낮음을 인지 |
| Swagger/ReDoc UI 동작 | ✅ 가능 | sidecar 설치되어 정적 자산 자체 제공 |
| 자동 생성 가능 여부 | 🟡 가능하지만 v1은 부정확 | v1은 대부분 string body fallback, v2(marketpulse)만 정확 |

### `@extend_schema` 사용 현황 (명시적 스키마 데코레이션)

| 모듈 | 파일 | extend_schema 사용 횟수 |
|------|------|------------------------|
| api_request | `api_request/admin_views.py` | 6 |
| rag_analysis | `rag_analysis/views.py` | 3 |
| serverless | `serverless/views.py` | 7 |
| chainsight | `chainsight/api/views.py` | 8 |
| news | `news/api/views.py` | 3 |
| users | `users/views.py` | 3 |
| marketpulse | `marketpulse/api/views/health.py` | 2 |
| marketpulse | `marketpulse/api/views/cards.py` | 2 |
| marketpulse | `marketpulse/api/views/overview.py` | 2 |
| marketpulse | `marketpulse/api/views/i18n.py` | 2 |
| marketpulse | `marketpulse/api/views/news_refresh.py` | 2 |
| **합계** | | **40** |

> 전체 View 클래스 수(152개) 대비 명시적 데코레이션 비율 ≈ **26%**.
> 그 중에서도 `marketpulse`(v2)와 `chainsight`/`api_request`(admin) 위주로 적용되어 있고,
> 사용자 트래픽이 큰 `stocks`(39개 path) / `users`(35개 path) / `serverless`(64개 path)는 거의 미적용.

### 핵심 발견

1. **drf-spectacular는 이미 설치·설정 완료 상태** — 새로 도입할 필요 없음.
2. 운영에 노출된 OpenAPI는 **v2 (`/api/v2/schema/`)** 한 개로 한정되어 있고, **v1은 동일 schema에 같이 잡히지만 ENUM 충돌과 unable to guess serializer 경고가 다수** → `DISABLE_ERRORS_AND_WARNINGS=True` 로 끄고 운영.
3. `config/urls.py:58~68`에 v2 스키마 경로만 등록 — v1 전용 schema URL이 없어서 **API 사용자가 전체 v1 엔드포인트를 한 번에 탐색할 수단이 없음**.
4. `news/api/views.py`의 `NewsViewSet`은 단일 클래스에 `@action` **30개**가 붙어 있어 단순 `@extend_schema(tags=...)`만 추가해도 큰 가독성 개선이 가능.
5. `serverless/views.py`는 함수 기반 뷰(`@api_view` 52개) 위주이며, **request/response serializer가 없는 dict 응답이 대부분**이라 스키마 자동 추론이 사실상 불가능 → `@extend_schema(responses=inline_serializer(...))` 가 필수.

---

## 엔드포인트 목록 (앱별 테이블)

> count는 `urls.py`의 `path()` 항목 수와 ViewSet의 default action(list/retrieve/create/update/destroy) + `@action` 데코레이터 합산 기준.

### 사용자 요청 10개 앱

| 앱 | URL Prefix | path() 수 | ViewSet actions | 실효 엔드포인트(추정) | 주요 View 모듈 | 특이사항 |
|----|------------|----------:|----------------:|----------------------:|---------------|---------|
| **stocks** | `/api/v1/stocks/` | 39 | 0 | **39** | `views.py`, `views_mvp.py`, `views_indicators.py`, `views_search.py`, `views_market_movers.py`, `views_fundamentals.py`, `views_screener.py`, `views_exchange.py`, `views_eod.py` | 전부 APIView 기반. extend_schema 0건. EOD 3개는 admin/debug. |
| **users** | `/api/v1/users/` | 35 | 0 | **35** | `views.py`, `jwt_views.py` | JWT 7개 + 세션 인증 6개 + 즐겨찾기 3개 + 포트폴리오 9개 + 관심사 2개 + Watchlist 8개. extend_schema 3건만. |
| **news** | `/api/v1/news/` | 1(router) | 30 (@action) + 2(default list/retrieve) | **~32** | `news/api/views.py` (NewsViewSet) | 단일 ViewSet에 30 @action — 데코레이션 우선순위 최상. 단 ML/admin 권한 분기 12개 포함. |
| **macro** | `/api/v1/macro/` | 10 | 0 | **10** | `macro/views.py` | Market Pulse 대시보드. extend_schema 0건. |
| **rag_analysis** | `/api/v1/rag/` | 15 | 0 | **15** | `rag_analysis/views.py` | DataBasket 6 + AnalysisSession 4 + Monitoring 5. extend_schema 3건만. SSE 스트리밍 1개 포함. |
| **serverless** | `/api/v1/serverless/` | 64 | 0 | **64** | `serverless/views.py`(@api_view 52), `serverless/views_admin.py` (Admin 12) | 함수 기반 뷰 다수. dict 직접 반환 → 스키마 추론 거의 불가능. extend_schema 7건. |
| **thesis** | `/api/v1/thesis/` | 11(직접) + 3 router | 7+5+5 (ThesisViewSet/premise/indicator) | **~28** | `thesis/views/*.py` | UUID 라우팅 (`<uuid:thesis_id>`). 중첩 라우터 2개. extend_schema 0건. |
| **validation** | `/api/v1/validation/` | 6 | 0 | **6** | `validation/api/views.py` | Peer 비교 + 프리셋 + LLM 필터. extend_schema 0건. |
| **chainsight** | `/api/v1/chainsight/` | 7(직접) + 1 router | 5(default) + 5(@action) | **~17** | `chainsight/api/views.py`, `chainsight/views/watchlist_views.py` | WatchlistViewSet은 ModelViewSet + @action 5개. extend_schema 8건 (가장 잘 문서화됨). |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | 0 | **2** | `sec_pipeline/views.py` | dashboard(HTML) + filing-data API. extend_schema 0건. |

**소계: 약 248개 엔드포인트**

### 추가 발견 앱 (감사 범위 외였지만 동일 schema에 포함됨)

| 앱 | URL Prefix | path() 수 | 실효 엔드포인트 | 비고 |
|----|------------|----------:|----------------:|------|
| api_request | `/api/v1/` (admin/...) | 6 | 6 | extend_schema 6건 (전부 적용 ✓) |
| portfolio | `/api/coach/` | 5 | 5 | Portfolio Coach 슬라이스 (E1/E2/E3/E5/E6) |
| marketpulse | `/api/v2/market-pulse/` | 5 | 5 | extend_schema 10건 (v2 메인, 가장 잘 문서화) |
| config (root/health) | `/`, `/health/` | 2 | 2 | API root + health check |

**총합: 약 266개 엔드포인트**

### 스키마 노출 URL (이미 동작함)

| URL | 용도 |
|-----|------|
| `/api/v2/schema/` | OpenAPI YAML/JSON 스펙 (drf-spectacular) |
| `/api/v2/swagger/` | Swagger UI |
| `/api/v2/redoc/` | ReDoc UI |

> 현재 schema에는 `SCHEMA_PATH_PREFIX = r'/api/v[12]'` 매칭으로 v1 엔드포인트도 포함되지만,
> ENUM 충돌·serializer 누락 경고가 많아 `DISABLE_ERRORS_AND_WARNINGS=True`로 무음 처리 중.

---

## 도입 작업 목록

> 목표: 250개+ 엔드포인트 전체에 대해 **자동 생성 OpenAPI 스키마가 정확히 동작하고**,
> Swagger UI에서 인증·요청·응답 형태를 한눈에 볼 수 있도록 한다.
> 이미 라이브러리는 깔려 있으므로, 작업의 본질은 **데코레이션 보강**과 **응답 직렬화 표준화**.

### 작업 0. 인프라 정리 (반나절, 기존 설정 정비)

| # | 작업 | 위치 | 설명 |
|---|------|------|------|
| 0-1 | v1 schema URL 분리 | `config/urls.py` | `/api/v1/schema/` + `/api/v1/swagger/` 추가하거나, v1·v2 단일 schema로 명확히 합치기 |
| 0-2 | `DISABLE_ERRORS_AND_WARNINGS` 단계적 해제 | `config/settings.py:385` | 데코레이션 보강 후 False로 되돌려야 회귀 감지 가능 |
| 0-3 | CI에 schema 검증 추가 | `.github/workflows/` | `python manage.py spectacular --validate --fail-on-warn` |
| 0-4 | 공통 ENUM 추가 | `config/spectacular_enums.py` | category/status 충돌 추가 발견 시 등록 |

**예상 공수: 0.5일**

### 작업 1. 우선순위 P0 — 핵심 트래픽 앱 데코레이션 (3~5일)

대상: 사용자 트래픽이 직접 닿는 앱 + 외부 통합 영향 큰 앱.

| # | 앱 | 대상 View | 작업량 | 비고 |
|---|----|-----------|-------:|------|
| 1-1 | stocks | 9개 모듈 / 39 endpoint | 1.5일 | symbol path param, 기간 query param 일관 패턴 → 공통 `OpenApiParameter` 헬퍼 정의 후 적용 |
| 1-2 | users | `views.py`, `jwt_views.py` / 35 endpoint | 1일 | JWT 인증 흐름은 보안 측면에서 정확한 스키마 필수. simple-jwt `TokenObtainPairView`는 별도 패치 |
| 1-3 | thesis | ViewSet 3개 + APIView 8개 / ~28 endpoint | 1일 | UUID 패스, 중첩 라우터(`/<uuid:thesis_id>/premises/`) 처리 패턴 확립 |
| 1-4 | rag_analysis | 15 endpoint | 0.5일 | SSE 스트리밍(`ChatStreamView`)은 `@extend_schema(responses=OpenApiTypes.STR)` 등 별도 처리 필요 |
| 1-5 | validation | 6 endpoint | 0.5일 | symbol path + preset/peer-preference 패턴 |

### 작업 2. 우선순위 P1 — 함수 기반 뷰가 많은 앱 (3~4일)

가장 손이 많이 가는 영역. **dict 반환 → serializer 정의** 작업이 병행되어야 함.

| # | 앱 | 대상 View | 작업량 | 핵심 작업 |
|---|----|-----------|-------:|---------|
| 2-1 | serverless | `views.py` (52 @api_view) | 2.5일 | (a) 응답 dict별 inline_serializer 정의 또는 별도 `serializers.py` 도입, (b) `@extend_schema(request=, responses=)` 적용 |
| 2-2 | serverless admin | `views_admin.py` (12 endpoint) | 0.5일 | 이미 일부 extend_schema 있음. 누락분 보강 |
| 2-3 | news | NewsViewSet (@action 30개) | 1일 | tag별 그룹화, ML/admin 분기 endpoint는 description에 권한 명시 |

### 작업 3. 우선순위 P2 — 잔여 앱 + 정합성 (1~2일)

| # | 앱 | 대상 | 작업량 | 비고 |
|---|----|------|-------:|------|
| 3-1 | macro | 10 endpoint | 0.5일 | extend_schema 0건. 응답 구조 단순 → serializer 정의 후 적용 |
| 3-2 | chainsight | 잔여 17 endpoint 중 누락분 | 0.5일 | api/views는 8건 적용됨. WatchlistViewSet 5 @action에 보강 필요 |
| 3-3 | sec_pipeline | 2 endpoint | 0.25일 | 작지만 누락 |
| 3-4 | portfolio | 5 endpoint | 0.5일 | Coach 슬라이스 — 입력/출력 schema가 서비스 contract |
| 3-5 | api_request | 이미 6/6 적용됨 | - | 검증만 |
| 3-6 | marketpulse | 이미 10/10 적용됨 | - | 검증만 |

### 작업 4. 검증 + 배포 (0.5~1일)

| # | 작업 | 결과물 |
|---|------|-------|
| 4-1 | `manage.py spectacular --validate --fail-on-warn` 통과 | 경고 0건 |
| 4-2 | Swagger UI 수동 확인 (10개 대표 endpoint) | 인증/요청/응답 정상 표시 |
| 4-3 | `contracts/` 디렉터리와 schema 일치 확인 | OpenAPI YAML 스냅샷 |
| 4-4 | README/CLAUDE.md 업데이트 | `/api/v1/swagger/`, `/api/v2/swagger/` 링크 명시 |

### 총 예상 공수

| 단계 | 공수 |
|------|------|
| 작업 0 인프라 | 0.5일 |
| 작업 1 P0 | 4~5일 |
| 작업 2 P1 | 3~4일 |
| 작업 3 P2 | 1.5~2일 |
| 작업 4 검증/배포 | 0.5~1일 |
| **총합** | **9.5 ~ 12.5일 (1인 기준)** |

> 병렬화 시 (P0/P1/P2 분리 → 2~3명) **약 1주** 내 완료 가능.

### 권장 진행 순서

1. **인프라 정리(작업 0)** 먼저 — schema 검증을 CI에 묶어두면 보강 작업의 진척이 즉시 가시화됨.
2. **chainsight·api_request·marketpulse·serverless admin**의 extend_schema 패턴을 표준 템플릿으로 추출.
3. P0 → P1 → P2 순서로 적용. 모듈별 PR 분리 (앱당 1 PR 권장).
4. 작업 0-2(`DISABLE_ERRORS_AND_WARNINGS=False`)는 **마지막 PR**에서 활성화 후 머지.

### 참고 — 기존 코드의 좋은 패턴

- `chainsight/api/views.py`의 `@extend_schema(tags=[...], summary=..., parameters=[OpenApiParameter(...)], responses=ChainSightGraphSerializer)` 패턴이 잘 정리되어 있어 **표준 템플릿**으로 활용 가능.
- `marketpulse/api/views/*`의 v2 스키마는 정확하므로 v1 보강 시 동일 컨벤션 적용.
- `config/spectacular_enums.py`의 ENUM_NAME_OVERRIDES 주석이 충돌 해결 가이드를 잘 담고 있음.

---

## 부록: 빠른 참조 명령

```bash
# OpenAPI YAML 덤프
poetry run python manage.py spectacular --file schema.yaml

# 검증 + 경고 시 실패 (CI용)
poetry run python manage.py spectacular --validate --fail-on-warn

# Swagger UI (로컬)
poetry run python manage.py runserver
# http://localhost:8000/api/v2/swagger/  (현재 노출)
# http://localhost:8000/api/v2/redoc/    (현재 노출)
```

## 부록: 검증된 사실 / 미확인 사실

- ✅ 검증됨: `pyproject.toml`에 drf-spectacular 명시, `config/settings.py`에 SPECTACULAR_SETTINGS 정의, `config/urls.py`에 v2 schema 경로 등록.
- ✅ 검증됨: `extend_schema` 사용 횟수 (40건) — `grep -c "extend_schema"` 결과.
- ✅ 검증됨: 각 앱별 `path()` 카운트 — `grep -c "^    path"` 결과.
- ⚠️ 추정: ViewSet의 default action(list/retrieve 등) 개수는 모델/router 설정에서 추정한 값 — 실제 운영 노출은 `python manage.py show_urls` 등으로 별도 확정 권장.
- ⚠️ 추정: 작업 공수는 평균 30~40 endpoint/일 페이스 가정 — 함수 기반 뷰가 많은 serverless는 실측 시 늘어날 수 있음.
