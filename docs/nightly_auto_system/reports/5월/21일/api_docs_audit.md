# API 문서 감사 보고서

생성일: 2026-05-21
대상 branch: slice13
대상 프로젝트: stock_vis (Django REST Framework)

---

## 현재 상태

### 1. 문서화 도구 설치 여부

| 항목 | 상태 | 위치 / 버전 |
|------|------|------------|
| `drf-spectacular` | ✅ **설치됨** | `pyproject.toml:38` — `^0.29.0` |
| `drf-spectacular-sidecar` | ✅ **설치됨** | `pyproject.toml:39` — `^2026.4.14` (Swagger UI / ReDoc 정적 자산) |
| `drf-yasg` | ❌ 미설치 | — |
| `INSTALLED_APPS` 등록 | ✅ 완료 | `config/settings.py:205-206` |
| `DEFAULT_SCHEMA_CLASS` | ✅ 설정 | `config/settings.py:363` → `drf_spectacular.openapi.AutoSchema` |
| `SPECTACULAR_SETTINGS` 블록 | ✅ 설정 | `config/settings.py:370-418` |

### 2. Swagger / OpenAPI 스펙 자동 생성 가능 여부

**현재 노출 경로** (`config/urls.py:62-72`):

| URL | 역할 |
|-----|------|
| `/api/v2/schema/` | OpenAPI JSON 스펙 |
| `/api/v2/swagger/` | Swagger UI |
| `/api/v2/redoc/` | ReDoc UI |

- ✅ **자동 생성 가능** — drf-spectacular가 정상 설정됨
- ⚠️ **부분적 범위** — `SCHEMA_PATH_PREFIX = r'/api/v[12]'` 로 v1/v2 모두 매칭되지만, 실제 스키마 품질은 view 단의 `@extend_schema` 적용 여부에 따라 달라짐
- ⚠️ **경고 억제** — `DISABLE_ERRORS_AND_WARNINGS: True` 로 설정되어 있어, 미문서화 view는 graceful fallback (string body)로 노출됨 (settings.py:386-390 주석 참조)

### 3. 명시적 `@extend_schema` 데코레이터 현황

view 파일에서 `@extend_schema` 사용 횟수 (총 **66건 / 12개 파일**):

| 파일 | 횟수 | 비고 |
|------|-----|------|
| `news/api/views.py` | 32 | News ViewSet — 가장 잘 문서화됨 |
| `chainsight/api/views.py` | 7 | Chain Sight v2 그래프 탐색 |
| `serverless/views.py` | 6 | Market Movers / Screener 일부만 |
| `chainsight/views/watchlist_views.py` | 5 | Watchlist ViewSet 액션 |
| `api_request/admin_views.py` | 5 | Provider admin |
| `users/views.py` | 2 | 미흡 (35개 endpoint 中 2건) |
| `rag_analysis/views.py` | 2 | 미흡 (15개 endpoint 中 2건) |
| `thesis/views/thesis_views.py` | 2 | 미흡 |
| `marketpulse/api/views/*.py` | 4 | overview/cards/news_refresh/i18n/health 각 1건 (총 4) |

뷰 **클래스 정의 총 116개**, 함수형 뷰까지 합치면 200+ 진입점.
**`@extend_schema` 명시 적용률은 추정 20~25%** (나머지는 graceful fallback).

---

## 엔드포인트 목록 (앱별)

> 정확한 경로 수는 `urls.py` 정의 기준이며, `ViewSet`의 자동 라우터 + `@action`은 별도 계산.

| # | 앱 | URL prefix | 명시 URL 패턴 | 추가 ViewSet/@action | 합계 (추정) | 비고 |
|---|----|----|----|----|----|----|
| 1 | **stocks** | `/api/v1/stocks/` | 39 | — | **39** | 9개 sub-view 모듈 (dashboard/MVP/indicators/search/movers/fundamentals/screener/exchange/EOD) |
| 2 | **users** | `/api/v1/users/` | 35 | — | **35** | JWT 7 + legacy session 7 + favorites 3 + portfolio 9 + interests 2 + watchlist 7 |
| 3 | **news** | `/api/v1/news/` | 1 (router only) | `NewsViewSet` (CRUD 6 + **30 @action**) | **~36** | 가장 큰 ViewSet (views.py 2200줄+) |
| 4 | **macro** | `/api/v1/macro/` | 10 | — | **10** | pulse/fear-greed/rates/inflation/markets/calendar/vix/sectors/sync x2 |
| 5 | **rag_analysis** | `/api/v1/rag/` | 15 | — | **15** | DataBasket 6 + Session 4 + Monitoring 5 |
| 6 | **serverless** | `/api/v1/serverless/` | 67 | — | **67** | 가장 큰 URL 파일. Admin 12 + Movers 6 + Breadth 3 + Heatmap 3 + Presets 7 + Filters 1 + Screener 1 + Alerts 6 + Thesis 4 + ETF 9 + LLM 4 + Institutional 3 + Regulatory 2 + Health 1 |
| 7 | **thesis** | `/api/v1/thesis/` | 8 (명시) | `ThesisViewSet` (6+2 @action) + Premise ViewSet (6) + Indicator ViewSet (6) | **~28** | Conversation 4 + Dashboard 2 + Alerts 2 + nested routers |
| 8 | **validation** | `/api/v1/validation/` | 6 | — | **6** | 모두 `<symbol>/` prefix |
| 9 | **chainsight** | `/api/v1/chainsight/` | 7 | `WatchlistViewSet` (6 CRUD + 5 @action = 11) | **~18** | seeds/sector/signals/trace/neighbors/graph/suggestions + watchlist |
| 10 | **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | — | **2** | admin/dashboard + filing/<symbol>/ |
| 11 | **marketpulse** | `/api/v2/market-pulse/` | 5 | — | **5** | overview/cards/news/i18n/health (✅ OpenAPI 1차 타깃) |
| 12 | **api_request** | `/api/v1/` | 6 | — | **6** | Provider admin (status/rate-limits/cache/test/config) + health |
| 13 | **portfolio** | `/api/` + `/api/v1/` | 2 (legacy) + 6 (DRF) | — | **8** | Slice 13 결과 — coach/e1~e6 통합 endpoint |
| — | **graph_analysis** | — | — | — | **0** | views.py만 존재, urls.py 미등록 |
| — | **config** (root) | `/` | 2 | — | **2** | `api_root`, `health/` |
| — | **admin** | `/admin/` | 1 | — | **1** | Django admin |
| — | **schema** | `/api/v2/{schema,swagger,redoc}/` | 3 | — | **3** | drf-spectacular 자체 |

### 앱별 명시 URL 총합

```
stocks         39
users          35
news            1  (+ ~30 ViewSet actions)
macro          10
rag_analysis   15
serverless     67
thesis          8  (+ ~20 ViewSet actions)
validation      6
chainsight      7  (+ ~11 ViewSet actions)
sec_pipeline    2
marketpulse     5
api_request     6
portfolio       8
─────────────────
명시 URL 합계   209
ViewSet 자동    ~61
─────────────────
실제 노출 추정  ~270 endpoints
```

### App별 명시 `@extend_schema` 적용률

| 앱 | extend_schema | 추정 endpoint | 적용률 |
|----|----|----|----|
| news | 32 | 36 | **~89%** ✅ |
| marketpulse | 4 | 5 | **~80%** ✅ |
| chainsight (api+watchlist) | 12 | 18 | **~67%** 🟡 |
| api_request | 5 | 6 | **~83%** ✅ |
| serverless | 6 | 67 | **~9%** 🔴 |
| users | 2 | 35 | **~6%** 🔴 |
| rag_analysis | 2 | 15 | **~13%** 🔴 |
| thesis | 2 | 28 | **~7%** 🔴 |
| stocks | 0 | 39 | **0%** 🔴 |
| macro | 0 | 10 | **0%** 🔴 |
| validation | 0 | 6 | **0%** 🔴 |
| sec_pipeline | 0 | 2 | **0%** 🔴 |
| portfolio | 0 | 8 | **0%** 🔴 |

---

## 도입 작업 목록

### Phase 0 — 기반 확립 (이미 완료)

| 항목 | 상태 |
|-----|------|
| `drf-spectacular` + sidecar 설치 | ✅ |
| `INSTALLED_APPS` 등록 | ✅ |
| `DEFAULT_SCHEMA_CLASS` 지정 | ✅ |
| `/api/v2/schema/` `/swagger/` `/redoc/` 라우팅 | ✅ |
| ENUM_NAME_OVERRIDES (collision 해결) | ✅ |
| 표준 에러 envelope serializer (`config.serializers`) | ✅ |

**→ 추가 설치/설정 작업 없음. 인프라는 갖춰져 있음.**

### Phase 1 — 스펙 노출 범위 확장 (소량 작업)

| # | 작업 | 파일 | 예상 시간 |
|---|------|------|----------|
| 1 | `SPECTACULAR_SETTINGS.TITLE` 를 "Market Pulse v2" 에서 "Stock-Vis API" 로 일반화 | `config/settings.py:371` | 5분 |
| 2 | `DESCRIPTION` 도 전체 API 커버리지 반영 | `config/settings.py:372-375` | 5분 |
| 3 | `SCHEMA_PATH_PREFIX` 가 이미 `/api/v[12]` 라 v1도 잡힘 — 확인만 | — | 5분 |
| 4 | (선택) v1 전용 별도 schema endpoint 분리 (`/api/v1/schema/` 추가) | `config/urls.py` | 15분 |
| 5 | `DISABLE_ERRORS_AND_WARNINGS` 를 점진적으로 False 전환할지 결정 | `config/settings.py:390` | — |

**→ Phase 1 총 30~40분**

### Phase 2 — `@extend_schema` 데코레이터 추가 (대량 작업)

미적용 view 클래스 수와 함수형 view 수를 기준으로 작업량 추산.

#### 우선순위 1: 외부 노출 핵심 API (P0)

| 앱 | view 파일 | 미적용 endpoint | 예상 시간 |
|----|----|----|----|
| stocks | views.py + views_eod/screener/fundamentals/etc (9 files) | 39 | 6~8시간 |
| users | views.py + jwt_views.py | 35 | 4~5시간 |
| thesis | views/*.py (premise/indicator/thesis/dashboard/conversation/alert) | 26 | 4시간 |
| **소계** | | **100** | **14~17시간** |

#### 우선순위 2: 내부/분석 API (P1)

| 앱 | view 파일 | 미적용 endpoint | 예상 시간 |
|----|----|----|----|
| serverless | views.py (Movers/Breadth/Heatmap/Alerts/ETF/...) + views_admin.py | ~60 | 8~10시간 |
| rag_analysis | views.py | 13 | 2시간 |
| chainsight | api/views.py 일부 + watchlist 일부 | 6 | 1시간 |
| validation | views.py | 6 | 1시간 |
| macro | views.py | 10 | 1.5시간 |
| **소계** | | **95** | **13.5~15.5시간** |

#### 우선순위 3: 관리자/기타 (P2)

| 앱 | view 파일 | 미적용 endpoint | 예상 시간 |
|----|----|----|----|
| sec_pipeline | views.py | 2 | 30분 |
| portfolio | views.py + api/views.py | 8 | 1.5시간 |
| api_request | admin_views.py | 1 | 15분 |
| news (잔여) | api/views.py | 4 | 30분 |
| **소계** | | **15** | **3시간** |

### Phase 3 — Serializer / Response Model 정의

대부분 endpoint가 **dict 반환 (Response({...}))** 패턴이라, 정확한 스키마를 위해서는 `inline_serializer` 또는 별도 `*ResponseSerializer` 클래스 필요.

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
| Phase 1 | 설정 정리 | 0.5h |
| Phase 2 (P0) | stocks/users/thesis `@extend_schema` | 14~17h |
| Phase 2 (P1) | serverless/rag/chainsight/validation/macro | 13~15h |
| Phase 2 (P2) | sec_pipeline/portfolio/api_request/news 잔여 | 3h |
| Phase 3 | Response serializer 정의 | 8~12h |
| Phase 4 | CI/검증/문서화 | 2h |
| **총합** | | **~40~50시간 (5~7 영업일)** |

---

## 권고사항

1. **즉시 가능한 가치**: 설치+설정이 이미 끝나 있으므로, `SPECTACULAR_SETTINGS.TITLE`/`DESCRIPTION`만 일반화하면 **오늘 당장 `/api/v2/swagger/` 에서 전체 API 일부가 보임**. (단, `@extend_schema` 미적용 view는 string body로 fallback)
2. **DISABLE_ERRORS_AND_WARNINGS=True 의 양면성**: 운영 영향 0이라 깔끔하지만, 어떤 view가 graceful fallback 중인지 보이지 않음 → 작업 초기에는 일시적으로 False로 전환하여 **미문서화 view 목록을 spectacular 워닝으로 확보**한 후 다시 True로 되돌리는 패턴 권장.
3. **News 앱을 모범 사례로 활용**: 32건 `@extend_schema` 가 이미 적용된 `news/api/views.py` 의 패턴 (operation_id, tags, responses, parameters)을 다른 앱에 복제하면 학습 비용 절감.
4. **Slice 단위 도입**: 한 번에 전체 도입 대신, slice 14+ 에서 **앱 1개 = sub-task 1개** 단위로 끊어서 작업하면 PR 리뷰가 용이.
5. **graph_analysis 앱**: `views.py`는 있지만 `urls.py` 미등록 — 문서화 대상에서 자동 제외됨. 추후 API 노출 시 함께 처리.

---

## 부록 — 참조 파일

- 설정: `config/settings.py:205-206, 363, 370-418`
- 라우팅: `config/urls.py:19-23, 61-72`
- 모범 사례: `news/api/views.py` (32x `@extend_schema`)
- Enum 충돌 해결 패턴: `config/spectacular_enums.py` + `SPECTACULAR_SETTINGS.ENUM_NAME_OVERRIDES`
- 에러 envelope: `config/serializers.py`, `config/exception_handler.py`
