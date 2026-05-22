# API 문서 감사 보고서

생성일: 2026-05-22
대상 branch: slice14
대상 프로젝트: stock_vis (Django REST Framework)
모드: 읽기 전용 (코드 수정 없음)

---

## 현재 상태

### 1. 문서화 도구 설치 여부

| 항목 | 상태 | 위치 / 버전 |
|------|------|------------|
| `drf-spectacular` | ✅ **설치됨** | `pyproject.toml:38` — `^0.29.0` |
| `drf-spectacular-sidecar` | ✅ **설치됨** | `pyproject.toml:39` — `^2026.4.14` (Swagger UI / ReDoc 정적 자산) |
| `drf-yasg` | ❌ 미설치 | — |
| `INSTALLED_APPS` 등록 | ✅ 완료 | `config/settings.py` (`drf_spectacular`, `drf_spectacular_sidecar`) |
| `DEFAULT_SCHEMA_CLASS` | ✅ 설정 | `drf_spectacular.openapi.AutoSchema` |
| `SPECTACULAR_SETTINGS` 블록 | ✅ 설정 | `config/settings.py` (TITLE, DESCRIPTION, VERSION, ENUM 오버라이드, 사이드카 등) |

### 2. Swagger / OpenAPI 스펙 자동 생성 가능 여부

**현재 노출 경로** (`config/urls.py:62-72`):

| URL | 역할 |
|-----|------|
| `/api/v2/schema/` | OpenAPI JSON 스펙 |
| `/api/v2/swagger/` | Swagger UI |
| `/api/v2/redoc/` | ReDoc UI |

- ✅ **자동 생성 가능** — drf-spectacular가 정상 설정됨
- ⚠️ **TITLE/DESCRIPTION이 Market Pulse v2에 한정** — 실제 스펙은 `SCHEMA_PATH_PREFIX = r'/api/v[12]'` 로 v1까지 매칭되지만, 메타데이터는 v2 한정 문구
- ⚠️ **경고 억제** — `DISABLE_ERRORS_AND_WARNINGS: True` 로 설정되어 있어, 미문서화 view는 graceful fallback (string body)로 노출됨

### 3. 명시적 `@extend_schema` 데코레이터 현황

| 파일 | `@extend_schema` 데코레이터 개수 | 비고 |
|------|-----|------|
| `chainsight/api/views.py` | **7** | Chain Sight v2 그래프 탐색 |
| `serverless/views.py` | **6** | Market Movers / Screener 일부 |
| `api_request/admin_views.py` | **5** | Provider admin (status/rate-limits 등) |
| `marketpulse/api/views/{overview,cards,news_refresh,i18n,health}.py` | **5** (각 1) | Market Pulse v2 — OpenAPI 1차 타깃 |
| `news/api/views.py` | **2** | `@extend_schema_view` 클래스 1 + 메서드 1 |
| `users/views.py` | **2** | 미흡 |
| `rag_analysis/views.py` | **2** | 미흡 |
| `thesis/views/*.py` | **0** | 전무 |
| `stocks/views_*.py` | **0** | 9개 파일 모두 미적용 |
| `macro/views.py` | **0** | 미적용 |
| `validation/api/views.py` | **0** | 미적용 |
| `sec_pipeline/views.py` | **0** | 미적용 |
| `portfolio/api/views.py` | **0** | 미적용 |
| `chainsight/views/watchlist_views.py` | **0** | Watchlist ViewSet 미문서화 |

**전체 합계: 29건 `@extend_schema` 데코레이터 / 12개 파일**

뷰 클래스 정의 + 함수형 뷰 합계는 200+ 진입점이며, **명시 적용률은 ~10-15%** (나머지는 graceful fallback).

> ⚠️ 어제(05-21) 보고서는 `extend_schema` 키워드 자체(import + 메서드 호출 포함)를 단순 카운트한 영향으로 news 32건 등 과대 집계가 있었음. 본 보고서는 `@extend_schema` 데코레이터 라인만 정확히 집계.

---

## 엔드포인트 목록 (앱별)

> 정확한 경로 수는 `urls.py` 내 `path(...)` 정의 기준이며, `ViewSet`의 자동 라우터 + `@action`은 별도로 합산.

### 앱별 명시 URL 패턴 (오늘 측정값)

| # | 앱 | URL prefix | 명시 `path()` | 추가 ViewSet/@action | 합계 (추정) | 비고 |
|---|----|----|----|----|----|----|
| 1 | **stocks** | `/api/v1/stocks/` | **39** | — | 39 | 9개 sub-view 모듈 (dashboard/MVP/indicators/search/movers/fundamentals/screener/exchange/EOD) |
| 2 | **users** | `/api/v1/users/` | **35** | — | 35 | JWT + legacy session + favorites + portfolio + interests + watchlist |
| 3 | **news** | `/api/v1/news/` | **1** (router) | NewsViewSet (CRUD 6 + **30 @action**) | ~37 | views.py 2200줄+ — 최대 ViewSet |
| 4 | **macro** | `/api/v1/macro/` | **10** | — | 10 | pulse/fear-greed/rates/inflation/markets/calendar/vix/sectors/sync x2 |
| 5 | **rag_analysis** | `/api/v1/rag/` | **15** | — | 15 | DataBasket + Session + Monitoring |
| 6 | **serverless** | `/api/v1/serverless/` | **64** | — | 64 | 최대 URL 파일. Admin/Movers/Breadth/Heatmap/Presets/Filters/Screener/Alerts/Thesis/ETF/LLM/Institutional/Regulatory/Health |
| 7 | **thesis** | `/api/v1/thesis/` | **11** | ThesisViewSet (6 CRUD + 2 @action) + PremiseViewSet (6) + IndicatorViewSet (6) | ~31 | Conversation 4 + Monitoring 2 + Alerts 2 + nested routers |
| 8 | **validation** | `/api/v1/validation/` | **6** | — | 6 | 모두 `<symbol>/` prefix |
| 9 | **chainsight** | `/api/v1/chainsight/` | **7** | WatchlistViewSet (CRUD 6 + **5 @action**) | ~18 | seeds/sector/signals/trace/neighbors/graph/suggestions + watchlist |
| 10 | **sec_pipeline** | `/api/v1/sec-pipeline/` | **2** | — | 2 | admin/dashboard + filing/<symbol>/ |
| 11 | **marketpulse** | `/api/v2/market-pulse/` | **5** | — | 5 | overview/cards/news/i18n/health (✅ OpenAPI 1차 타깃) |
| 12 | **api_request** | `/api/v1/` | **6** | — | 6 | Provider admin (status/rate-limits/cache/test/config) + health |
| 13 | **portfolio (legacy)** | `/api/` | **0** | — | 0 | Slice 13 #65에서 legacy 전수 제거 완료 |
| 14 | **portfolio (DRF)** | `/api/v1/` | **6** | — | 6 | coach/e1~e6 통합 endpoint (Slice 13 결과) |
| — | **graph_analysis** | — | — | — | 0 | views.py만 존재, urls.py 미등록 (대상 외) |
| — | **config (root)** | `/` | 2 | — | 2 | `api_root`, `health/` |
| — | **admin** | `/admin/` | 1 | — | 1 | Django admin |
| — | **schema** | `/api/v2/{schema,swagger,redoc}/` | 3 | — | 3 | drf-spectacular 자체 |

### 명시 URL 합계

```
stocks         39
users          35
news            1  (+ ~36 ViewSet actions)
macro          10
rag_analysis   15
serverless     64
thesis         11  (+ ~20 ViewSet actions)
validation      6
chainsight      7  (+ ~11 ViewSet actions)
sec_pipeline    2
marketpulse     5
api_request     6
portfolio       6
─────────────────
명시 URL 합계  207
ViewSet 자동   ~67
─────────────────
실제 노출 추정 ~274 endpoints
```

### 사용자 요청 10개 앱별 핵심 카운트 (요약)

| 앱 | 엔드포인트 (명시 + ViewSet) |
|----|----|
| stocks | **39** |
| users | **35** |
| news | **~37** (router 1 + ViewSet CRUD 6 + @action 30) |
| macro | **10** |
| rag_analysis | **15** |
| serverless | **64** |
| thesis | **~31** (path 11 + 3 ViewSet 18 + 2 @action) |
| validation | **6** |
| chainsight | **~18** (path 7 + Watchlist 11) |
| sec_pipeline | **2** |
| **합계** | **~257** |

### App별 `@extend_schema` 적용률

| 앱 | extend_schema | 추정 endpoint | 적용률 |
|----|----|----|----|
| marketpulse | 5 | 5 | **100%** ✅ |
| api_request | 5 | 6 | **~83%** ✅ |
| chainsight (api만) | 7 | 18 | **~39%** 🟡 |
| serverless | 6 | 64 | **~9%** 🔴 |
| users | 2 | 35 | **~6%** 🔴 |
| rag_analysis | 2 | 15 | **~13%** 🔴 |
| news | 2 | 37 | **~5%** 🔴 (단, `@extend_schema_view`로 ViewSet 일괄 적용 가능) |
| thesis | 0 | 31 | **0%** 🔴 |
| stocks | 0 | 39 | **0%** 🔴 |
| macro | 0 | 10 | **0%** 🔴 |
| validation | 0 | 6 | **0%** 🔴 |
| sec_pipeline | 0 | 2 | **0%** 🔴 |
| portfolio | 0 | 6 | **0%** 🔴 |

---

## 도입 작업 목록

### Phase 0 — 기반 확립 (이미 완료)

| 항목 | 상태 |
|-----|------|
| `drf-spectacular` + sidecar 설치 | ✅ |
| `INSTALLED_APPS` 등록 | ✅ |
| `DEFAULT_SCHEMA_CLASS` 지정 | ✅ |
| `/api/v2/schema/` `/swagger/` `/redoc/` 라우팅 | ✅ |
| `ENUM_NAME_OVERRIDES` (collision 해결) | ✅ |
| 표준 에러 envelope serializer (`config.serializers`) | ✅ |

**→ 추가 설치/설정 작업 없음. 인프라는 갖춰져 있음.**

### Phase 1 — 메타데이터 일반화 (소량 작업)

| # | 작업 | 파일 | 예상 시간 |
|---|------|------|----------|
| 1 | `SPECTACULAR_SETTINGS.TITLE` 를 "Market Pulse v2" 에서 "Stock-Vis API" 로 일반화 | `config/settings.py` (TITLE 라인) | 5분 |
| 2 | `DESCRIPTION` 도 전체 API 커버리지 반영 | `config/settings.py` | 5분 |
| 3 | `VERSION` 명명 정책 결정 (v1 + v2 혼재) | `config/settings.py` | 10분 |
| 4 | (선택) v1 전용 별도 schema endpoint 분리 (`/api/v1/schema/` 추가) | `config/urls.py` | 15분 |
| 5 | `DISABLE_ERRORS_AND_WARNINGS` 를 일시 False 전환 후 미문서화 view 목록 확보 → 다시 True 복귀 | 운영 | 30분 |

**→ Phase 1 총 약 1시간**

### Phase 2 — `@extend_schema` 데코레이터 추가 (대량 작업)

미적용 view 클래스/함수 수 기준 추산. 257개 대상 endpoint 중 **약 230개가 미문서화 상태**.

#### 우선순위 1: 사용자 노출 핵심 (P0)

| 앱 | view 파일 | 미적용 endpoint | 예상 시간 |
|----|----|----|----|
| stocks | views.py + views_eod/screener/fundamentals/indicators/search/movers/exchange/mvp (9 files) | 39 | 6~8시간 |
| users | views.py + jwt_views.py + favorite/portfolio/watchlist | 33 | 4~5시간 |
| thesis | views/{thesis,conversation,monitoring,premise,indicator,alert}_views.py | 31 | 4~5시간 |
| **소계** | | **103** | **14~18시간** |

#### 우선순위 2: 내부/분석 API (P1)

| 앱 | view 파일 | 미적용 endpoint | 예상 시간 |
|----|----|----|----|
| serverless | views.py + views_admin.py (Movers/Breadth/Heatmap/Alerts/ETF/LLM/Institutional/Regulatory) | ~58 | 8~10시간 |
| rag_analysis | views.py | 13 | 2시간 |
| chainsight | api/views.py 잔여 + watchlist 전수 | 11 | 1.5시간 |
| validation | api/views.py | 6 | 1시간 |
| macro | views.py | 10 | 1.5시간 |
| **소계** | | **98** | **14~16시간** |

#### 우선순위 3: 관리자/기타 (P2)

| 앱 | view 파일 | 미적용 endpoint | 예상 시간 |
|----|----|----|----|
| sec_pipeline | views.py | 2 | 30분 |
| portfolio | api/views.py | 6 | 1시간 |
| api_request | admin_views.py 잔여 | 1 | 15분 |
| news (잔여) | api/views.py — `@extend_schema_view` 패턴으로 ViewSet 36개 일괄 적용 | ~34 | 2~3시간 |
| **소계** | | **43** | **4~5시간** |

### Phase 3 — Serializer / Response Model 정의

대부분 endpoint가 **dict 반환 (`Response({...})`) 패턴**이라, 정확한 스키마를 위해서는 `inline_serializer` 또는 별도 `*ResponseSerializer` 클래스 필요.

- 예: `stocks/views_fundamentals.py:KeyMetricsView` 는 dict 반환 → `KeyMetricsResponseSerializer` 추가 필요
- 추가 작업: **~150개 inline_serializer 또는 30~50개 공용 ResponseSerializer**
- 예상 시간: **8~12시간**

### Phase 4 — CI / 검증

| 작업 | 예상 시간 |
|-----|----------|
| `python manage.py spectacular --validate` CI 게이트 추가 | 30분 |
| `schema.yml` 산출물 git tracking 또는 artifact 업로드 | 30분 |
| Swagger UI 인증 (JWT) 동작 확인 + `securitySchemes` 검증 | 30분 |
| README/CLAUDE.md 에 문서 URL 안내 추가 | 15분 |

**→ Phase 4 총 ~2시간**

### 총 예상 작업량

| Phase | 작업 | 시간 |
|------|------|------|
| Phase 0 | 인프라 셋업 | ✅ 완료 |
| Phase 1 | 메타데이터 일반화 | ~1h |
| Phase 2 (P0) | stocks/users/thesis `@extend_schema` | 14~18h |
| Phase 2 (P1) | serverless/rag/chainsight/validation/macro | 14~16h |
| Phase 2 (P2) | sec_pipeline/portfolio/api_request/news 잔여 | 4~5h |
| Phase 3 | Response serializer 정의 | 8~12h |
| Phase 4 | CI/검증/문서화 | 2h |
| **총합** | | **~43~54시간 (5~7 영업일)** |

---

## 권고사항

1. **즉시 가능한 가치**: 설치+설정이 이미 끝나 있으므로, `SPECTACULAR_SETTINGS.TITLE`/`DESCRIPTION`만 일반화하면 **오늘 당장 `/api/v2/swagger/` 에서 전체 API 일부가 보임**. (단, `@extend_schema` 미적용 view는 string body로 fallback)
2. **`DISABLE_ERRORS_AND_WARNINGS=True` 의 양면성**: 운영 영향 0이라 깔끔하지만, 어떤 view가 graceful fallback 중인지 보이지 않음 → 작업 초기에는 일시적으로 False로 전환하여 **미문서화 view 목록을 spectacular 워닝으로 확보**한 후 다시 True로 되돌리는 패턴 권장.
3. **`@extend_schema_view` 패턴 활용**: `news/api/views.py:52` 가 이 패턴을 사용 중. ViewSet이 큰 앱(news, thesis, chainsight watchlist)은 클래스 1개에 모든 @action을 일괄 문서화하면 적용 비용이 크게 감소.
4. **marketpulse + api_request 를 모범 사례로 활용**: 각각 100%, 83% 적용률 — 패턴(operation_id, tags, responses, parameters)을 다른 앱에 복제하면 학습 비용 절감.
5. **Slice 단위 도입**: 한 번에 전체 도입 대신, slice 14+ 에서 **앱 1개 = sub-task 1개** 단위로 끊어서 작업하면 PR 리뷰가 용이.
6. **graph_analysis 앱**: `views.py`는 있지만 `urls.py` 미등록 — 문서화 대상에서 자동 제외됨. 추후 API 노출 시 함께 처리.
7. **어제 보고서 대비 차이**:
   - thesis path 8 → **11** (conversation `news-issues` + `suggest` + indicator-readings 등 추가)
   - serverless path 67 → **64** (일부 정리)
   - portfolio legacy 2 → **0** (Slice 13 #65 결과)
   - `@extend_schema` 데코레이터 집계 방식 정정: 어제 66건 → **오늘 29건** (어제는 import/inner call 포함 과대 집계, 오늘은 데코레이터 라인만 정확 집계)

---

## 부록 — 참조 파일

- 설정: `config/settings.py` (`drf_spectacular` 블록 + `SPECTACULAR_SETTINGS` + `ENUM_NAME_OVERRIDES`)
- 라우팅: `config/urls.py:19-23, 61-72`
- 모범 사례:
  - `marketpulse/api/views/{overview,cards,news_refresh,i18n,health}.py` (각 1건 @extend_schema, 100% 적용)
  - `api_request/admin_views.py` (5건, 83% 적용)
  - `news/api/views.py:52` (`@extend_schema_view` 클래스 일괄 적용 패턴)
- Enum 충돌 해결 패턴: `config/spectacular_enums.py` + `SPECTACULAR_SETTINGS.ENUM_NAME_OVERRIDES`
- 에러 envelope: `config/serializers.py`, `config/exception_handler.py`
