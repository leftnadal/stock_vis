# API 문서 감사 보고서

**작성일**: 2026-05-10
**대상**: Stock-Vis Backend (Django REST Framework)
**감사 범위**: API 문서화 도구, 엔드포인트 카탈로그, 도입 작업량 추정

---

## 현재 상태

### 1. 문서화 도구 설치 현황

| 도구 | 설치 여부 | 버전 | 비고 |
|------|----------|------|------|
| `drf-spectacular` | ✅ 설치됨 | `^0.29.0` | `pyproject.toml` |
| `drf-spectacular-sidecar` | ✅ 설치됨 | `^2026.4.14` | Swagger UI/ReDoc 정적 자산 |
| `drf-yasg` | ❌ 미설치 | — | 사용 안 함 |

> **결론**: drf-spectacular이 이미 설치되어 있고, **부분적으로 설정/노출까지 완료**된 상태입니다. 추가 설치 작업은 불필요하며, 도입 과제는 "전 영역으로 문서화 범위 확장"입니다.

### 2. 설정/노출 현황

**INSTALLED_APPS** (`config/settings.py:205-206`)
```python
'drf_spectacular',
'drf_spectacular_sidecar',
```

**REST_FRAMEWORK** (`config/settings.py:361`)
```python
'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
```

**SPECTACULAR_SETTINGS** (`config/settings.py:365-413`)
- `TITLE`: "Stock-Vis Market Pulse v2 API"
- `VERSION`: `2.0`
- `SCHEMA_PATH_PREFIX`: `r'/api/v[12]'` → v1, v2 **모두** 스키마 포함
- `DISABLE_ERRORS_AND_WARNINGS`: `True` → v1 endpoint는 graceful fallback (`unable to guess serializer` 무시)
- `ENUM_NAME_OVERRIDES`: 4개 enum collision 해결 (Thesis 카테고리/상태, News 카테고리, SavedPath 상태)
- `SWAGGER_UI_DIST`/`REDOC_DIST`: `SIDECAR` (외부 CDN 의존성 제거)

**노출 URL** (`config/urls.py:58-68`)
| Path | 용도 |
|------|------|
| `GET /api/v2/schema/` | OpenAPI YAML 스펙 |
| `GET /api/v2/swagger/` | Swagger UI |
| `GET /api/v2/redoc/` | ReDoc UI |

> **즉시 동작 가능**: `python manage.py runserver` 후 `/api/v2/swagger/` 접속하면 현재 v1+v2 스펙이 모두 렌더됩니다 (단, 대부분의 v1 endpoint는 fallback으로 흐릿한 스펙).

### 3. `@extend_schema` 데코레이터 적용 현황

| 파일 | `@extend_schema` 적용 수 |
|------|-------------------------|
| `chainsight/api/views.py` | 7 |
| `serverless/views.py` | 6 |
| `api_request/admin_views.py` | 5 |
| `marketpulse/api/views/*.py` (5개) | 5 (각 1개) |
| `rag_analysis/views.py` | 2 |
| `news/api/views.py` | 2 |
| `users/views.py` | 2 |
| **합계** | **29개** |

> 명시적 문서화가 진행된 핵심 영역은 **Market Pulse v2 / Chain Sight / api_request admin / serverless**입니다. 나머지 v1 endpoint(특히 stocks, thesis, validation 등)는 자동 추론에 의존하고 있어 응답 본체가 흐릿하게 노출됩니다.

---

## 엔드포인트 목록 (앱별 테이블)

> 각 `urls.py`의 `path()` 호출 수 + `DefaultRouter` ViewSet의 `@action` 수를 합산한 값입니다.
> ViewSet의 표준 list/retrieve/create/update/destroy 등은 ViewSet 1개당 5경로로 추정.

| # | 앱 (URL prefix) | `urls.py` | path() 수 | ViewSet 액션 (참고) | 추정 endpoint | 문서화 상태 |
|---|-----------------|-----------|----------|----|--------------|----------|
| 1 | stocks (`/api/v1/stocks/`) | `stocks/urls.py` | 39 | — | **39** | 미문서화 (fallback) |
| 2 | users (`/api/v1/users/`) | `users/urls.py` | 35 | — | **35** | 부분 (`@extend_schema` 2개) |
| 3 | news (`/api/v1/news/`) | `news/api/urls.py` | 1 | NewsViewSet 31 actions + 표준 5 | **~36** | 미문서화 (`@extend_schema` 2개) |
| 4 | macro (`/api/v1/macro/`) | `macro/urls.py` | 10 | — | **10** | 미문서화 |
| 5 | rag_analysis (`/api/v1/rag/`) | `rag_analysis/urls.py` | 15 | — | **15** | 부분 (`@extend_schema` 2개) |
| 6 | serverless (`/api/v1/serverless/`) | `serverless/urls.py` | 64 | — | **64** | 부분 (`@extend_schema` 6개) |
| 7 | thesis (`/api/v1/thesis/`) | `thesis/urls.py` | 9 | ThesisViewSet (5+2), Premise (5), Indicator (5) | **~26** | 미문서화 |
| 8 | validation (`/api/v1/validation/`) | `validation/api/urls.py` | 6 | — | **6** | 미문서화 |
| 9 | chainsight (`/api/v1/chainsight/`) | `chainsight/api/urls.py` | 7 | WatchlistViewSet (5+5) | **~17** | 부분 (`@extend_schema` 7개) |
| 10 | sec_pipeline (`/api/v1/sec-pipeline/`) | `sec_pipeline/urls.py` | 2 | — | **2** | 미문서화 |
| 11 | api_request (`/api/v1/`) | `api_request/urls.py` | 6 | — | **6** | ✅ 완료 (`@extend_schema` 5개) |
| 12 | portfolio (`/api/`) | `portfolio/urls.py` | 5 | — | **5** | 미문서화 |
| 13 | marketpulse (`/api/v2/market-pulse/`) | `marketpulse/api/urls.py` | 5 | — | **5** | ✅ 완료 (`@extend_schema` 5개) |
| 14 | config (root) | `config/urls.py` | 2 + 3 | — | **5** | 자동 (root, health, schema/swagger/redoc) |
| | **합계** | | **206** | | **~271** | **약 11% 명시 문서화** (29/271) |

### 사용자 요청 10개 앱만의 합계

| 앱 | 추정 endpoint |
|---|-------------|
| stocks | 39 |
| users | 35 |
| news | ~36 |
| macro | 10 |
| rag_analysis | 15 |
| serverless | 64 |
| thesis | ~26 |
| validation | 6 |
| chainsight | ~17 |
| sec_pipeline | 2 |
| **합계** | **~250** |

---

## 도입 작업 목록

> drf-spectacular은 이미 설치/설정/노출 완료. **남은 일은 v1 endpoint들의 응답 스키마 명시화 + UI 운영 정비**입니다.

### A. 즉시 적용 가능 (작업량 0~0.5일)

| # | 작업 | 파일 | 비고 |
|---|------|------|------|
| A-1 | `/api/v2/swagger/` 접속 동작 확인 | (런타임) | 현재 시점에 이미 동작해야 함 |
| A-2 | v1 별칭 추가: `/api/v1/swagger/`, `/api/v1/schema/` | `config/urls.py` | path-prefix 이미 v1 포함, URL만 추가 |
| A-3 | TITLE/DESCRIPTION을 "Market Pulse v2 한정" → "Stock-Vis 통합" 으로 갱신 | `config/settings.py:366-370` | UI 타이틀 정확화 |
| A-4 | `DISABLE_ERRORS_AND_WARNINGS=True` 일시 해제 후 경고 수집 | `config/settings.py:385` | 어디부터 손볼지 baseline 만들기 |

### B. ViewSet 단위 `@extend_schema_view` 추가 (작업량 ~3~4일)

ViewSet은 1개 클래스에 다수 액션이 모여 있어 `@extend_schema_view(...)` 한 번으로 일괄 정리 가능. 우선순위 높은 영역:

| # | 대상 | 액션 수 | 예상 시간 | 우선순위 |
|---|------|--------|----------|---------|
| B-1 | `news.NewsViewSet` (31 actions) | 31 | 8h | 🔴 높음 (앱 전체가 1개 ViewSet) |
| B-2 | `thesis.ThesisViewSet` + Premise/Indicator | 12 | 4h | 🟡 중간 |
| B-3 | `chainsight.WatchlistViewSet` (5 actions) | 5 | 1h | 🟢 낮음 (이미 7개 명시됨) |

### C. APIView 단위 `@extend_schema` 추가 (작업량 ~5~7일)

| # | 대상 (앱) | APIView 수 (≈path) | 예상 시간 | 우선순위 |
|---|----------|------------|----------|---------|
| C-1 | stocks (39) | 39 | 12h | 🔴 높음 (외부 노출 핵심) |
| C-2 | users (35) | 35 | 10h | 🔴 높음 (인증/포트폴리오) |
| C-3 | serverless (64) — 잔여 58개 | 58 | 14h | 🟡 중간 (이미 6개 적용) |
| C-4 | macro (10) | 10 | 3h | 🟢 낮음 |
| C-5 | rag_analysis (15) — 잔여 13개 | 13 | 4h | 🟡 중간 (LLM 비용/SSE 주의) |
| C-6 | validation (6) | 6 | 2h | 🟢 낮음 |
| C-7 | sec_pipeline (2) | 2 | 0.5h | 🟢 낮음 |
| C-8 | portfolio (5) | 5 | 1.5h | 🟢 낮음 |

### D. Serializer 정비 (작업량 ~2~3일)

`@extend_schema(responses=...)` 를 명시하려면 Serializer가 우선 필요:
- 현재 다수 view가 `Response({...})` dict를 직접 반환 → 응답 Serializer 부재
- inline `serializers.Serializer` 또는 `OpenApiTypes.OBJECT` 로 임시 처리 가능
- 장기적으로 응답 DTO Serializer 표준화 필요 (특히 `stocks/views_*.py`)

| # | 작업 | 비고 |
|---|------|------|
| D-1 | dict 응답 view 식별 (≈100+개) | grep `Response\(\{` |
| D-2 | 응답 DTO Serializer 도입 가이드 작성 | shared_kb 등록 |
| D-3 | 핵심 외부 endpoint 우선 (stocks, marketpulse, validation) | 점진 |

### E. 운영 정비 (작업량 ~0.5~1일)

| # | 작업 | 비고 |
|---|------|------|
| E-1 | CI에 `python manage.py spectacular --validate --fail-on-warn` 추가 | 회귀 차단 |
| E-2 | `frontend/`의 TypeScript 타입을 OpenAPI에서 자동 생성 (`openapi-typescript` 등) | contracts/ 와 정합성 강화 |
| E-3 | 인증 헤더 예시 / `auth=[]` 누락 endpoint 점검 | JWT Bearer 명시 |
| E-4 | Tag 분류 보강: 현재 1개 (`Market Pulse v2`) → 앱별 13개 | 그룹핑 가독성 |

### 예상 총 작업량 요약

| 영역 | 작업량 |
|------|-------|
| A. 즉시 적용 | 0.5일 |
| B. ViewSet `@extend_schema_view` | 3~4일 |
| C. APIView `@extend_schema` | 5~7일 |
| D. Serializer 정비 | 2~3일 |
| E. 운영/CI | 0.5~1일 |
| **총합 (1인 기준)** | **약 11~15.5일** |

> **점진적 도입 권장**: 우선 A → 외부 노출/계약이 중요한 stocks·users·marketpulse → 내부/admin 순으로 적용. CI 회귀 차단(E-1)을 도중에 끼우면 후퇴 방지에 효과적.

---

## 부록: 명시적 `@extend_schema` 적용 파일 (29개)

```
api_request/admin_views.py            5
rag_analysis/views.py                 2
serverless/views.py                   6
chainsight/api/views.py               7
news/api/views.py                     2
users/views.py                        2
marketpulse/api/views/health.py       1
marketpulse/api/views/cards.py        1
marketpulse/api/views/overview.py     1
marketpulse/api/views/i18n.py         1
marketpulse/api/views/news_refresh.py 1
config/settings.py                    (참조 정의)
─────────────────────────────────────────
합계                                   29
```

## 부록: 노출 중인 OpenAPI URL

```
GET  /api/v2/schema/        # OpenAPI YAML
GET  /api/v2/swagger/       # Swagger UI
GET  /api/v2/redoc/         # ReDoc UI
```

`SCHEMA_PATH_PREFIX = r'/api/v[12]'` 설정 덕분에 v1 endpoint도 함께 노출되지만, 대부분 자동 추론 fallback 상태.
