# API 문서 감사 보고서

> 생성일: 2026-05-31 · 모드: 읽기 전용 (코드 수정 없음)
> 대상: 모노레포 마이그레이션 진행 중 코드베이스 (apps/, packages/shared/ 구조)

---

## 현재 상태

### 문서화 패키지 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| **drf-spectacular** | ✅ 설치됨 (`^0.29.0`) | `pyproject.toml` |
| **drf-spectacular-sidecar** | ✅ 설치됨 (`^2026.4.14`) | `pyproject.toml` (Swagger UI 정적 자산 번들) |
| **drf-yasg** | ❌ 미설치 | (drf-spectacular로 일원화됨) |
| **djangorestframework-simplejwt** | ✅ `^5.5.1` | JWT 인증 |

> 결론: 문서화 인프라는 **이미 도입 완료** 상태. 신규 설치 작업 불필요.

### OpenAPI 스펙 자동 생성 가능 여부 — ✅ 가능 (운영 중)

`config/urls.py`에 3개 엔드포인트가 등록되어 있어 즉시 스펙 조회 가능:

| URL | 뷰 | 역할 |
|-----|-----|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 스펙 (YAML/JSON) |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc |

**핵심 설정** (`config/settings.py` L370~391):

```python
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',  # L370
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Stock-Vis Market Pulse v2 API',
    'VERSION': '2.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SCHEMA_PATH_PREFIX': r'/api/v[12]',   # ⭐ v1 + v2 모두 스펙 포함
    'TAGS': [...],
}
```

> **중요 발견**: `SCHEMA_PATH_PREFIX = r'/api/v[12]'` 설정으로 **v1·v2 모든 엔드포인트가 자동 스펙 생성 대상**입니다.
> 따라서 "도입"은 끝났고, 남은 작업은 **자동 생성된 스펙의 품질을 높이는 것**(설명·요청/응답 스키마·예시 명시)으로 한정됩니다.

### 기존 `@extend_schema` 적용 현황 (코드 파일 기준, 설정 파일 제외)

| 파일 | 적용 수 |
|------|--------|
| `apps/chain_sight/api/views.py` | 7 |
| `apps/portfolio/api/views.py` | 6 |
| `serverless/views.py` | 6 |
| `packages/shared/api_request/admin_views.py` | 5 |
| `apps/market_pulse/api/views/*.py` (5개 파일) | 5 |
| `news/api/views.py` | 2 |
| `rag_analysis/views.py` | 2 |
| `packages/shared/users/views.py` | 2 |
| **합계** | **≈ 35** |

> 전체 엔드포인트(아래 표 합계 약 250+개) 대비 데코레이터 명시 적용률은 **약 14%** 수준. 나머지는 AutoSchema의 기본 추론에 의존.

---

## 엔드포인트 목록 (앱별 테이블)

> 각 `urls.py`를 직접 읽어 집계. ViewSet은 기본 CRUD + `@action` 커스텀 라우트를 포함하므로 실제 노출 경로 수는 명시 `path()` 수보다 많습니다.

| 앱 | URL prefix | urls.py 경로 | 엔드포인트 수 | 비고 |
|----|-----------|-------------|--------------|------|
| **users** | `/api/v1/users/` | `packages/shared/users/urls.py` | **35** | JWT 7 + 세션 6 + 즐겨찾기 3 + 포트폴리오 9 + 관심사 2 + Watchlist 8 |
| **stocks** | `/api/v1/stocks/` | `packages/shared/stocks/urls.py` | **39** | 9개 views_*.py 분할 (chart/overview/재무3종/sync/mvp 4/indicators 3/search 3/movers/fundamentals 5/screener 6/quotes 5/eod 3) |
| **news** | `/api/v1/news/` | `news/api/urls.py` | **~32** | `NewsViewSet` 1개 (DefaultRouter, basename=news) — 기본 CRUD + **`@action` 30개** |
| **macro** | `/api/v1/macro/` | `macro/urls.py` | **10** | pulse / fear-greed / interest-rates / inflation / global-markets / calendar / vix / sectors / sync / sync-status |
| **rag_analysis** | `/api/v1/rag/` | `rag_analysis/urls.py` | **15** | DataBasket 6 + AnalysisSession 4 (SSE 스트리밍 포함) + Monitoring 5 |
| **serverless** | `/api/v1/serverless/` | `serverless/urls.py` | **~64** | Admin Dashboard 12 + Movers 2 + Sync 2 + Keywords 4 + Breadth 3 + Heatmap 3 + Presets 7 + Filters 1 + Screener 1 + Alerts 6 + Thesis 4 + ETF 9 + LLM-relations 4 + Institutional 3 + Regulatory/Patent 2 + Health 1 |
| **thesis** | `/api/v1/thesis/` | `thesis/urls.py` | **~26** | 명시 path 8 (conversation 4 + dashboard + readings + alerts 2) + `ThesisViewSet`(CRUD+`@action`2) + nested `ThesisPremiseViewSet` + nested `ThesisIndicatorViewSet` |
| **validation** | `/api/v1/validation/` | `validation/api/urls.py` | **6** | summary / metrics / leader-comparison / presets / peer-preference / llm-filter (모두 `<symbol>` 기반) |
| **chainsight** | `/api/v1/chainsight/` | `apps/chain_sight/api/urls.py` | **~18** | 명시 path 7 (seeds/sector-graph/signals/trace/neighbors/graph/suggestions) + `WatchlistViewSet`(CRUD+`@action`5) |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | `sec_pipeline/urls.py` | **2** | admin/dashboard (함수형) + `FilingDataView` |
| **api_request** | `/api/v1/` | `packages/shared/api_request/urls.py` | **6** | health + Provider Admin 5 (status/rate-limits/cache/test/config) |
| **portfolio (순수 view)** | `/api/` | `apps/portfolio/urls.py` | **0** | `#65`로 legacy 5건 제거, 현재 빈 urlpatterns (include만 유지) |
| **portfolio_api (coach)** | `/api/v1/coach/` | `apps/portfolio/api/urls.py` | **6** | E1~E6 함수형 뷰 (`@extend_schema` 6개 적용 완료) |
| **market_pulse v2** | `/api/v2/market-pulse/` | `apps/market_pulse/api/urls.py` | **5** | overview / cards-detail / news-refresh / i18n / health (`@extend_schema` 적용 완료) |
| **iron_trading** | `/api/v1/iron-trading/` | `integrations/iron_trading/urls.py` | **1** | `DailyContextView` (trailing-slash 2개 path = 동일 뷰) |
| **config (루트)** | `/` | `config/urls.py` | **2** | api_root + health_check (문서 3종은 별도) |
| **graph_analysis** | — | `services/_dormant/graph_analysis/views.py` | **0** | 휴면(dormant), URL 미라우팅 — CLAUDE.md상 API 미구현 |
| **합계 (추정)** | | | **약 250~270** | ViewSet 자동 라우트 포함 추정치 |

### 집계 주의사항
- **news**: `grep -c '@action' news/api/views.py` = **30**. 기본 list/retrieve 포함 시 ~32개. 단일 ViewSet에 액션이 과밀하므로 태그 분리 권장.
- **serverless**: 함수 기반 뷰(`@api_view` 추정) 다수 — drf-spectacular는 함수형 뷰의 요청/응답 추론이 약하므로 `@extend_schema` 우선 보강 대상.
- **thesis / chainsight**: nested router + ViewSet 구조라 실제 노출 경로 수는 명시 path보다 많음.

---

## 도입 작업 목록

> 인프라는 이미 갖춰져 있으므로(설치·설정·UI 운영 중), 실제 작업은 **(1) 스펙 범위 확정 → (2) 스키마 품질 보강 → (3) 검증** 3단계입니다.

### 1단계: drf-spectacular 설치 + 설정 — ✅ 완료 (작업 불필요)

- [x] `drf-spectacular` + `sidecar` 설치 (`pyproject.toml`)
- [x] `DEFAULT_SCHEMA_CLASS = AutoSchema` 등록
- [x] `SPECTACULAR_SETTINGS` 정의 (TITLE/VERSION/PATH_PREFIX 등)
- [x] schema/swagger/redoc URL 라우팅 (`config/urls.py`)
- [x] `SCHEMA_PATH_PREFIX = r'/api/v[12]'` — v1·v2 전체 포함

**잔여 점검 항목 (선택)**:
- TITLE이 `'Stock-Vis Market Pulse v2 API'`로 v2 한정 명칭 → 전체 API 통합 문서라면 `'Stock-Vis API'`로 확장 검토 (단순 메타데이터, 기능 영향 없음)
- `config/spectacular_enums.py` 존재 → enum 네이밍 충돌(`*Enum` warnings) 관리 중인 것으로 추정. `python manage.py spectacular --validate`로 warning 수 확인 권장

### 2단계: `@extend_schema` 데코레이터 보강 범위

현재 적용률 ≈ 14% (35/250+). 우선순위 기준 보강 대상:

| 우선순위 | 대상 | 사유 | 예상 규모 |
|---------|------|------|----------|
| **P0 (높음)** | `serverless/views.py` 함수형 뷰 ~58개 (적용 6 외) | 함수형 뷰는 AutoSchema 추론 약함 → 요청 파라미터/응답 누락 多 | ~58개 데코레이터 |
| **P0** | `news/api/views.py` NewsViewSet `@action` 28개 (적용 2 외) | 단일 ViewSet 과밀, url_path 정규식 액션 다수 → summary/tags 수동 지정 필요 | ~28개 |
| **P1 (중간)** | `packages/shared/stocks/views_*.py` 39개 (적용 0) | 클래스 기반이라 추론은 되나 `<symbol>` 파라미터·응답 직렬화 명시 필요 | ~39개 |
| **P1** | `packages/shared/users/views.py` (적용 2 외 33개) | JWT/포트폴리오/Watchlist — 인증 흐름 문서화 가치 높음 | ~33개 |
| **P2 (낮음)** | `rag_analysis` 15, `macro` 10, `validation` 6, `thesis` 26, `chainsight` 18 | 일부 적용됨, 점진 보강 | ~70개 |

> **데코레이터 작성 내용**: 각 뷰에 `summary`, `description`, `parameters`(path/query), `request`/`responses`(Serializer 연결), `tags`(앱별 그룹핑), `examples`.

### 3단계: 예상 작업량

| 작업 | 규모 | 예상 공수 |
|------|------|----------|
| 스펙 범위/메타데이터 확정 + warning 정리 | 설정 1~2건 | 0.5일 |
| P0 보강 (serverless + news, ~86개) | 함수/액션 86개 | 3~4일 |
| P1 보강 (stocks + users, ~72개) | 클래스/함수 72개 | 2~3일 |
| P2 보강 (나머지 ~70개) | 점진 | 2~3일 |
| `--validate` 검증 + Swagger UI 수동 확인 | 전체 | 0.5일 |
| **총계** | **~230개 뷰 보강** | **약 8~11일 (1인 기준)** |

### 권장 접근

1. **즉시 활용 가능**: 현재도 `/api/v2/swagger/`에서 v1·v2 전체 스펙 조회 가능 (품질만 낮음). 신규 작업 없이 프론트엔드 참조용으로 사용 가능.
2. **점진 보강**: 신규 PR마다 해당 뷰에 `@extend_schema` 추가하는 규칙을 PR 체크리스트에 편입 (한 번에 230개 보강보다 지속 가능).
3. **P0 우선**: 함수형 뷰가 밀집한 `serverless`부터 보강 시 스펙 정확도 개선 효과가 가장 큼.
4. **태그 정비**: `SPECTACULAR_SETTINGS['TAGS']`에 앱별 태그를 추가해 Swagger UI에서 250+ 엔드포인트를 앱 단위로 그룹핑.

---

## 요약

- ✅ **문서화 인프라 도입 완료** — drf-spectacular + sidecar 설치/설정/UI 모두 운영 중. **설치 작업 불필요**.
- ✅ **v1·v2 전체 자동 스펙 생성 가능** — `SCHEMA_PATH_PREFIX = r'/api/v[12]'`.
- ⚠️ **스키마 품질은 미흡** — `@extend_schema` 적용률 약 14% (35/250+). 함수형 뷰(serverless) + 과밀 ViewSet(news)에서 추론 정확도 낮음.
- 📌 **남은 작업의 본질** = "도입"이 아니라 **"자동 스펙의 품질 보강"** (약 230개 뷰, 8~11일). 점진적 PR 편입 방식 권장.
