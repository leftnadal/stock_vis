# API 문서 감사 보고서

- **감사 일자**: 2026-05-11
- **감사 범위**: Backend Django REST API (`config/urls.py` 기반)
- **목적**: API 문서화 현황 파악 및 Swagger/OpenAPI 도입 잔여 작업 산정

---

## 현재 상태

### 1) 문서화 도구 설치 현황

| 항목 | 상태 | 비고 |
|------|------|------|
| `drf-spectacular` | **설치됨** (`^0.29.0`) | `pyproject.toml`의 `[tool.poetry.dependencies]`에 등록 |
| `drf-spectacular-sidecar` | **설치됨** (`^2026.4.14`) | Swagger UI / ReDoc 정적 자산 (SIDECAR 사용) |
| `drf-yasg` | 미설치 | drf-spectacular와 양자택일 — 이미 spectacular 선택됨 |

### 2) Django 설정 등록 현황

`config/settings.py:205-206`
```python
'drf_spectacular',
'drf_spectacular_sidecar',
```

`config/settings.py:363`
```python
REST_FRAMEWORK = {
    ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

`config/settings.py:367-` SPECTACULAR_SETTINGS 주요 옵션
- `TITLE`: "Stock-Vis Market Pulse v2 API"
- `VERSION`: `2.0`
- `SCHEMA_PATH_PREFIX`: `r'/api/v[12]'` (v1, v2 모두 매칭)
- `SWAGGER_UI_DIST` / `REDOC_DIST`: `SIDECAR` (오프라인 자산)
- `DISABLE_ERRORS_AND_WARNINGS`: **`True`** (스키마 추론 실패 시 graceful fallback — v1 다수 엔드포인트는 string body로 노출됨)
- `COMPONENT_SPLIT_REQUEST`: `True`
- `ENUM_NAME_OVERRIDES`: thesis/news/chainsight enum 충돌 해결 명시

### 3) Swagger / OpenAPI 노출 URL (`config/urls.py:58-68`)

| URL | 역할 |
|------|------|
| `GET /api/v2/schema/` | OpenAPI 3.x JSON/YAML 스키마 |
| `GET /api/v2/swagger/` | Swagger UI |
| `GET /api/v2/redoc/` | ReDoc UI |

> 결론: **자동 스키마 생성 인프라는 이미 작동 중**. 단 `DISABLE_ERRORS_AND_WARNINGS=True`로 v1 엔드포인트 다수가 정확한 응답 스키마 없이 noise만 억제된 상태로 노출됨. 도입 작업 = 신규 설치가 아니라 **명시적 `@extend_schema` 데코레이터 커버리지 확대**가 핵심.

### 4) 현재 `@extend_schema` 사용 현황

전체 코드베이스 grep 결과 **31개** 데코레이터 사용 중. 파일별 분포:

| 위치 | 데코레이터 수 |
|------|--------------|
| `marketpulse/api/views/*.py` (5개 파일) | 5+ (각 view에 1개씩) |
| `api_request/admin_views.py` | 5 |
| `chainsight/api/views.py` | 7 |
| `serverless/views.py` | 6 |
| `rag_analysis/views.py` | 2 |
| `news/api/views.py` | 2 |
| `users/views.py` | 2 |
| 기타 | 잔여 |

> 정확한 스키마가 명시된 영역: **Market Pulse v2 + api_request admin + chainsight 일부**. 그 외 영역은 `AutoSchema` fallback에 의존.

---

## 엔드포인트 목록 (앱별)

### A) `config/urls.py` 라우팅 매트릭스

| Prefix | 앱 | urls.py 경로 |
|--------|----|-------------|
| `/api/v1/users/` | users | `users/urls.py` |
| `/api/v1/stocks/` | stocks | `stocks/urls.py` |
| `/api/v1/news/` | news | `news/api/urls.py` |
| `/api/v1/macro/` | macro | `macro/urls.py` |
| `/api/v1/rag/` | rag_analysis | `rag_analysis/urls.py` |
| `/api/v1/serverless/` | serverless | `serverless/urls.py` |
| `/api/v1/thesis/` | thesis | `thesis/urls.py` |
| `/api/v1/validation/` | validation | `validation/api/urls.py` |
| `/api/v1/chainsight/` | chainsight | `chainsight/api/urls.py` |
| `/api/v1/sec-pipeline/` | sec_pipeline | `sec_pipeline/urls.py` |
| `/api/v1/` (admin) | api_request | `api_request/urls.py` |
| `/api/` (portfolio) | portfolio | `portfolio/urls.py` |
| `/api/v2/market-pulse/` | marketpulse | `marketpulse/api/urls.py` |
| `/` (root/health) | config | `config/urls.py` |
| `/admin/` | Django admin | (내장) |
| `/api/v2/schema/`, `/swagger/`, `/redoc/` | drf-spectacular | (내장) |

### B) 앱별 엔드포인트 수 집계

| 앱 | `path()` 수 | ViewSet `@action` 수 | 비고 |
|----|-----------|-------------------|------|
| **stocks** | 39 | 0 | 14개 views_*.py 분할 (mvp, indicators, search, market_movers, fundamentals, screener, exchange, eod 등) |
| **users** | 35 | 0 | JWT 인증 7개 + 세션 인증 6개 + Favorites 3개 + Portfolio 9개 + Interests 2개 + Watchlist 8개 |
| **news** | 1 | **30** | `NewsViewSet`(ReadOnlyModelViewSet) + 30개 `@action` (stock/<symbol>, sentiment, daily-keywords, market-feed, ml-status, pipeline-health 등) |
| **macro** | 10 | 0 | Market Pulse v1 (pulse, fear-greed, interest-rates, inflation, global-markets, calendar, vix, sectors, sync, sync/status) |
| **rag_analysis** | 15 | 0 | DataBasket 6 + AnalysisSession 4 + Monitoring 5 |
| **serverless** | 64 | 0 | Admin Dashboard 12 + Market Movers 6 + Breadth 3 + Heatmap 3 + Screener Presets 7 + Filters 1 + Advanced Screener 1 + Alerts 6 + Thesis 4 + ETF 9 + LLM Relations 4 + Institutional 3 + Regulatory/Patent 2 + Health 1 (Chain Sight legacy 일부 제거 흔적 포함) |
| **thesis** | 11 | **~14** | Conversation 4 + Monitoring 2 + Alerts 2 + Nested Premise/Indicator routers + Main `ThesisViewSet`(2 @action). 총 라우팅 시 ~25 |
| **validation** | 6 | 0 | `<symbol>/summary`, `/metrics`, `/leader-comparison`, `/presets`, `/peer-preference`, `/llm-filter` |
| **chainsight** | 7 | **5** | Seeds, Sector graph, Signals, Trace, Neighbors, Graph, Suggestions + `WatchlistViewSet`(5 @action) |
| **sec_pipeline** | 2 | 0 | `admin/dashboard/`, `filing/<symbol>/` |
| **api_request** | 6 | 0 | health + Provider admin 5 (status, rate-limits, cache, test, config) |
| **portfolio** | 5 | 0 | coach/e1/garp, e5/adjustment, e2/diagnostic-card, e6/comparison, e3/metric-comment |
| **marketpulse (v2)** | 5 | 0 | overview, cards/<id>/detail, news/refresh, i18n, health — **v2 영역 명시적 스키마 완비** |
| **config (root)** | 2 | 0 | `/`, `/health/` |
| **합계** | **약 208 path** | **약 49 action** | **총 ≈ 257 엔드포인트** |

### C) ViewSet 별도 분해 (라우터로 자동 생성되는 엔드포인트 포함)

| ViewSet | 자동 생성 엔드포인트 |
|---------|-------------------|
| `NewsViewSet` (news, ReadOnlyModelViewSet) | `GET /` (list), `GET /<id>/` (retrieve), + 30 @action |
| `ThesisViewSet` (thesis) | list/retrieve/create/update/destroy + 2 @action |
| `ThesisPremiseViewSet` (nested) | list/retrieve/create/update/destroy |
| `ThesisIndicatorViewSet` (nested) | list/retrieve/create/update/destroy |
| `WatchlistViewSet` (chainsight) | list/retrieve/create/update/destroy + 5 @action |

> ViewSet의 표준 메서드(list/retrieve/create 등) 포함 시 총 엔드포인트는 **300개 내외**로 추정.

---

## 도입 작업 목록

> 결론: drf-spectacular는 이미 설치/노출되어 있다. 잔여 작업은 **(1) 스키마 정확도 향상**과 **(2) 운영 정책 정리** 두 갈래.

### Phase 1 — 인프라 점검 (이미 90% 완료)

| 작업 | 상태 | 코멘트 |
|------|------|--------|
| `drf-spectacular` 설치 | 완료 | `^0.29.0` |
| `drf-spectacular-sidecar` 설치 | 완료 | offline 자산 |
| `INSTALLED_APPS` 등록 | 완료 | `config/settings.py:205-206` |
| `DEFAULT_SCHEMA_CLASS` 설정 | 완료 | `config/settings.py:363` |
| `SPECTACULAR_SETTINGS` 정의 | 완료 | TITLE, VERSION, ENUM_NAME_OVERRIDES 포함 |
| Swagger/ReDoc URL 노출 | 완료 | `/api/v2/swagger/`, `/api/v2/redoc/` |
| **잔여**: 검증 명령 추가 | **미완료** | `python manage.py spectacular --validate` 정기 실행 권장 |
| **잔여**: CI 게이트 추가 | **미완료** | 스키마 회귀 검출용 (GitHub Actions) |

### Phase 2 — `@extend_schema` 커버리지 확대 (핵심 작업)

현재 31개 데코레이터로 v2 + 일부 v1만 커버. **v1 본체에 명시 스키마 추가 필요**.

#### 우선순위 A (외부 노출, 프론트 직접 호출, 가장 시급)

| 앱 | 대상 view 파일 | 예상 데코레이터 수 | 작업량 |
|----|--------------|------------------|------|
| stocks | views.py, views_mvp.py, views_indicators.py, views_search.py, views_market_movers.py, views_fundamentals.py, views_screener.py, views_exchange.py, views_eod.py (9파일) | ~39 (path 1개당 1개) | **중** (응답 직렬화 클래스 부족 — 신규 Serializer 작성 필요한 곳 다수) |
| users | views.py, jwt_views.py | ~35 | **중** (JWT 응답은 simplejwt가 이미 스키마 제공) |
| validation | api/views.py | ~6 | **소** |
| portfolio | views.py | ~5 | **소** |
| macro | views.py | ~10 | **소** (응답 dict가 단순) |

#### 우선순위 B (관리자/내부용, 후순위로 가능)

| 앱 | 대상 view | 예상 데코레이터 수 | 작업량 |
|----|---------|------------------|------|
| serverless | views.py + views_admin.py | ~64 | **대** (가장 무거움, function-based view 다수) |
| news | api/views.py | ~32 (list/retrieve + 30 action) | **대** (NewsViewSet 단일 거대 클래스, action별 response_serializer 명시 필요) |
| thesis | views/*.py | ~25 | **중** (ViewSet 3개 + APIView 8개) |
| chainsight | api/views.py + views/watchlist_views.py | ~12 | **소-중** (이미 7개 적용됨) |
| rag_analysis | views.py | ~15 (현재 2) | **중** (DataBasket/Session 직렬화 보강 필요) |
| sec_pipeline | views.py | ~2 | **소** |
| api_request | admin_views.py | 이미 5/6 완료 | **소** (잔여 1개) |

#### 작업량 산정 (러프 추정)

| 영역 | 엔드포인트 수 | 데코레이터 작성 시간 (개당 5–15분) | Serializer 신규 작성 시간 | 합계 (man-day) |
|------|------------|--------------------------------|----------------------|--------------|
| 우선순위 A (stocks/users/validation/portfolio/macro) | ~95 | 8–24h | 6–12h (Response Serializer 30~40개 신규) | **2–4 일** |
| 우선순위 B (serverless/news/thesis/chainsight/rag/sec/api_request) | ~150 | 12–37h | 8–16h | **3–6 일** |
| `DISABLE_ERRORS_AND_WARNINGS=False` 전환 + warning 해소 | — | 2–4h | — | **0.5 일** |
| 스키마 회귀 CI 게이트 추가 | — | 1–2h | — | **0.25 일** |
| **합계** | **~245 endpoint** | — | — | **약 6–11 man-day** |

### Phase 3 — 운영 정책

- [ ] `DISABLE_ERRORS_AND_WARNINGS=True` 단계적 해제 (커버리지 80% 이상 도달 시)
- [ ] `python manage.py spectacular --file schema.yml --validate` CI 단계 추가
- [ ] 스키마 diff를 PR에 노출 (예: `redocly diff` 또는 `openapi-diff`)
- [ ] 인증 스키마 보강: `JWT Bearer` security scheme 명시 (현재 fallback 가능성)
- [ ] `SCHEMA_PATH_PREFIX`를 `/api/v[12]`에서 전체 API 포함으로 확장 검토 (`/api/(portfolio|coach)` 등 portfolio 앱은 prefix 밖)
- [ ] tagging 전략 수립 (현재 `Market Pulse v2` 단일 TAG만 정의)

### Phase 4 — 누락된 라우팅 점검 (감사 중 발견)

| 이슈 | 위치 | 조치 |
|------|------|------|
| `portfolio` 앱이 `/api/`로 마운트되어 `SCHEMA_PATH_PREFIX=/api/v[12]`에서 **누락** | `config/urls.py:52` | `/api/v1/portfolio/`로 이전 또는 prefix regex 확장 |
| `serverless` 일부 path가 trailing-slash 없음 (`movers`, `breadth`, `screener` 등) — 다른 앱은 trailing-slash 사용 | `serverless/urls.py` | 일관성 정책 결정 (Swagger UI에서 그대로 노출됨, 기능상 문제 없음) |
| Chain Sight legacy URL 제거 흔적 (주석만 남음) | `serverless/urls.py:85,106-108` | 정리 |
| stocks 앱 내부 `eod/`, `api/` 혼재 prefix | `stocks/urls.py` | 외부 노출 명세상 일관성 확인 필요 |

---

## 요약

1. **자동 스키마 인프라는 이미 작동** — `/api/v2/swagger/`, `/api/v2/redoc/`에서 즉시 접근 가능.
2. **하지만 v1 엔드포인트 대부분이 graceful fallback** 상태 — 응답 본문이 string으로 표시됨. 운영용 문서로 쓰려면 명시 데코레이터 추가가 필수.
3. **잔여 작업량**: 총 약 245개 엔드포인트에 `@extend_schema` 적용 + Serializer 30~40개 신규 작성 → **약 6–11 man-day**.
4. **우선순위**: stocks/users/validation/portfolio/macro (프론트 직접 호출) → serverless/news/thesis (관리/대시보드) → chainsight/rag (이미 부분 완료) → sec_pipeline/api_request (마무리).
5. **운영 정책**: `DISABLE_ERRORS_AND_WARNINGS` 단계적 해제, CI 스키마 게이트 추가, portfolio 앱 prefix 정리.
