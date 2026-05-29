# API 문서 감사 보고서

> 생성일: 2026-05-29 · 읽기 전용 감사 (코드 변경 없음)
> 대상: `/Users/byeongjinjeong/Desktop/stock_vis`

---

## 현재 상태

### 결론 요약

**drf-spectacular가 이미 설치·설정·운영 중이며, OpenAPI 3 스펙 자동 생성이 정상 작동한다.**
별도의 "도입"이 아니라 **커버리지 확장**이 실제 과제다.

### 문서화 라이브러리 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| drf-spectacular | ✅ 설치 (`^0.29.0`) | `pyproject.toml`, `poetry.lock` |
| drf-spectacular-sidecar | ✅ 설치 (`2026.5.1`) | Swagger UI / ReDoc 정적 자산 self-host |
| drf-yasg | ❌ 미사용 | — |
| coreapi / 기타 | ❌ 미사용 | — |

### 설정 상태 (`config/settings.py`)

- `INSTALLED_APPS`에 `drf_spectacular`, `drf_spectacular_sidecar` 등록 (L211~212)
- `REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'` (L369)
- `SPECTACULAR_SETTINGS` 정의 (L376~424)
  - `TITLE`: "Stock-Vis Market Pulse v2 API", `VERSION`: 2.0
  - `SCHEMA_PATH_PREFIX = r'/api/v[12]'` — v1·v2 모두 스캔
  - `SWAGGER_UI_DIST / REDOC_DIST = 'SIDECAR'` (오프라인 자산)
  - `COMPONENT_SPLIT_REQUEST = True`
  - `ENUM_NAME_OVERRIDES` 4종 — enum 이름 충돌 해소 (thesis/news/chainsight)
  - ⚠️ `DISABLE_ERRORS_AND_WARNINGS = True` — schema 생성 경고를 **전부 억제** (커버리지 공백을 침묵시키는 양날의 검)

### 노출 엔드포인트 (`config/urls.py` L62~73)

| 경로 | 뷰 |
|------|----|
| `/api/v2/schema/` | `SpectacularAPIView` (OpenAPI YAML) |
| `/api/v2/swagger/` | `SpectacularSwaggerView` |
| `/api/v2/redoc/` | `SpectacularRedocView` |

### Swagger/OpenAPI 스펙 자동 생성 가능 여부: ✅ **가능 (실측 검증 완료)**

```
$ python manage.py spectacular --file /tmp/schema_test.yml
EXIT=0  (에러 없음)
```

| 지표 | 값 |
|------|-----|
| 생성된 `operationId` 수 | **292** |
| 등록된 path 항목 수 | **249** |
| 스펙 파일 크기 | 9,650 줄 (YAML) |

> 스펙은 정상 생성되나, `DISABLE_ERRORS_AND_WARNINGS=True`로 인해 serializer 추론 실패("unable to guess serializer")가 경고 없이 **string body fallback**으로 노출됨. 즉 **path는 잡히지만 요청/응답 스키마 품질이 낮은 엔드포인트가 다수 존재**한다(아래 도입 작업 목록 참조).

---

## 엔드포인트 목록 (앱별 테이블)

### 사용자 지정 10개 앱

| 앱 | URL prefix | 라우팅 방식 | 엔드포인트 수 | @extend_schema 적용 |
|----|-----------|------------|:---:|:---:|
| **stocks** | `/api/v1/stocks/` | path 수동 (9개 views 모듈) | **39** | ❌ 0 |
| **users** | `/api/v1/users/` | path 수동 (JWT+세션+포트폴리오+워치리스트) | **35** | ⚠️ 일부 (jwt_views 2건) |
| **news** | `/api/v1/news/` | DRF Router (`NewsViewSet`) | 표준 CRUD + **@action 30건** | ⚠️ 일부 (2건) |
| **macro** | `/api/v1/macro/` | path 수동 | **10** | ❌ 0 |
| **rag_analysis** | `/api/v1/rag/` | path 수동 (Basket/Session/Monitoring) | **15** | ⚠️ 일부 (2건) |
| **serverless** | `/api/v1/serverless/` | path 수동 (FBV 다수) | **64** | ⚠️ 일부 (6건) |
| **thesis** | `/api/v1/thesis/` | DRF Router ×3 (nested) + path 8 | 8 + ViewSet 3종(+@action 2) | ❌ 0 |
| **validation** | `/api/v1/validation/` | path 수동 | **6** | ❌ 0 |
| **chainsight** | `/api/v1/chainsight/` | path 7 + Router(`WatchlistViewSet` @action 5) | **7 + ViewSet 1종** | ✅ 7건 |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | path 수동 | **2** | ❌ 0 |

#### 앱별 상세

**stocks (39)** — dashboard/detail 페이지(2), search(1), 탭 데이터 API(chart/overview/balance-sheet/income/cashflow 5), sync(1), MVP(4), indicators(3), search(3), market-movers(1), fundamentals(5), screener(6), quotes(5), EOD(3)

**users (35)** — JWT 인증(7: signup/login/logout/refresh/verify/change-password/profile), 세션 인증 레거시(6), favorites(3), portfolio(9), interests(2), watchlist(8)

**news (Router)** — `NewsViewSet` 단일 등록(`basename='news'`). 표준 list/retrieve + **custom @action 30건** → 실 endpoint 30여 개. 동적 라우팅이라 정확 수는 router 등록 기준.

**macro (10)** — pulse, fear-greed, interest-rates, inflation, global-markets, calendar, vix, sectors, sync, sync/status

**rag_analysis (15)** — DataBasket(6), AnalysisSession(4: 목록/상세/messages/chat-stream SSE), Monitoring(5: usage/cost/cache/history/pricing)

**serverless (64)** — Admin Dashboard(12), Market Movers(2), Sync(2), Keywords(4), Breadth(3), Heatmap(3), Presets(7), Filters(1), Screener(1), Alerts(6), Thesis(4), ETF Holdings(9), LLM Relations(4), Institutional(3), Regulatory/Patent(2), Health(1)

**thesis** — 고정 path 8(conversation 4, dashboard/readings 2, alerts 2) + DRF Router 3종(`ThesisViewSet`+@action 2, `ThesisPremiseViewSet` nested, `ThesisIndicatorViewSet` nested)

**validation (6)** — `<symbol>/`의 summary/metrics/leader-comparison/presets/peer-preference/llm-filter

**chainsight (7 + ViewSet)** — seeds/sector-graph/signals/trace/neighbors/graph/suggestions 7개 + `WatchlistViewSet`(@action 5). **유일하게 @extend_schema 커버리지가 높은 앱**

**sec_pipeline (2)** — admin/dashboard, filing/`<symbol>`

### 그 외 등록 앱 (감사 범위 보완)

| 앱 | URL prefix | 엔드포인트 수 | @extend_schema |
|----|-----------|:---:|:---:|
| api_request | `/api/v1/` (admin) | 6 | ✅ 5 |
| portfolio (legacy) | `/api/` | 0 (빈 urlpatterns, `portfolio.api`로 단일화) | — |
| portfolio_api | `/api/v1/coach/` | 6 (e1~e6) | ✅ 6 |
| marketpulse | `/api/v2/market-pulse/` | 5 (overview/cards/news-refresh/i18n/health) | ✅ 5 (전건) |
| iron_trading | `/api/v1/iron-trading/` | 1 (daily-context, slash variant 포함 2) | ❌ 0 |
| config(root) | `/`, `/health/` | 2 | ❌ 0 |

### @extend_schema 적용 현황 (전수 grep)

총 **13개 파일**에서 사용. 데코레이터 발생 수:

| 파일 | 건수 |
|------|:---:|
| chainsight/api/views.py | 7 |
| portfolio/api/views.py | 6 |
| serverless/views.py | 6 |
| api_request/admin_views.py | 5 |
| marketpulse/api/views/*.py (5파일) | 각 1 (총 5) |
| news/api/views.py | 2 |
| rag_analysis/views.py | 2 |
| users/views.py | 2 |
| config/settings.py | 2 (enum override 참조) |

> **커버리지 공백**: stocks(39), macro(10), validation(6), thesis(전체), sec_pipeline(2)은 `@extend_schema` 0건. 가장 endpoint가 많은 stocks·serverless·users·news가 부분/무적용 상태.

---

## 도입 작업 목록

> 라이브러리·설정·UI는 이미 갖춰져 있으므로, 실제 과제는 **"신규 도입"이 아니라 "스키마 품질 보강"**이다. 우선순위 순으로 정리한다.

### 0. (선결) 경고 가시화 — 진단 기반 마련

- **현황**: `DISABLE_ERRORS_AND_WARNINGS = True`로 모든 schema 경고가 억제됨 → 어느 endpoint가 fallback인지 알 수 없음
- **작업**: (일시적) 플래그를 끄거나 `python manage.py spectacular --validate`로 경고 목록 수집 → 보강 대상 정량화
- **예상량**: 0.5d (진단/리포트만, 코드 변경 최소)

### 1. ViewSet/APIView별 `@extend_schema` 추가 범위

drf-spectacular는 serializer 기반 endpoint는 자동 추론하지만, 본 프로젝트는 **수동 `Response()` 반환 + 비표준 serializer 패턴이 다수**여서 명시 데코레이터 없이는 string fallback이 된다.

| 우선순위 | 앱 | 대상 | 작업 성격 | 예상 endpoint |
|:---:|----|------|----------|:---:|
| 🔴 P1 | stocks | 9개 views 모듈 전체 | `@extend_schema(responses=)` 신규 | ~39 |
| 🔴 P1 | serverless | FBV 58건 (chainsight 미적용분) | FBV는 `@extend_schema` 직접 부착 | ~58 |
| 🔴 P1 | news | `NewsViewSet` @action 30건 | action별 response serializer 명시 | ~30 |
| 🟡 P2 | users | 세션 레거시 + portfolio/watchlist | 보강(JWT 2건 외) | ~33 |
| 🟡 P2 | thesis | ViewSet 3종 + path 8 | response serializer 명시 | ~15 |
| 🟡 P2 | rag_analysis | Basket/Session 보강 (SSE chat-stream 주의) | 13건 보강 | ~13 |
| 🟢 P3 | macro | 10건 | response 명시 | ~10 |
| 🟢 P3 | validation | 6건 | response 명시 | ~6 |
| 🟢 P3 | sec_pipeline | 2건 | response 명시 | ~2 |

**기법 가이드**
- APIView/ViewSet: 클래스에 `@extend_schema_view(...)` 또는 메서드별 `@extend_schema`
- FBV(serverless 다수): 함수에 직접 `@extend_schema(...)`
- ViewSet `@action`: 각 action 메서드에 `@extend_schema`
- 공통 응답 envelope(`{detail, code, errors, status_code}`)는 이미 `config/serializers.py`에 존재 → 에러 응답 스키마 재사용 가능

### 2. 구조적 개선 (선택)

- **URL 버전 정합**: 현재 `SCHEMA_PATH_PREFIX = /api/v[12]`로 v1+v2 혼재. 문서 타이틀은 "Market Pulse v2"인데 실제론 v1 endpoint가 대다수 → 타이틀/설명 일반화 검토
- **태그 정리**: 현재 `TAGS`에 "Market Pulse v2" 1개만 정의 → 앱별 태그(stocks/users/news…) 추가 시 Swagger UI 그룹핑 개선
- **인증 스키마 명시**: JWT Bearer 전역 적용은 되어 있으나, 공개 endpoint(health, search 등)는 `@extend_schema(auth=[])` 명시 권장

### 3. 예상 작업량 종합

| 구간 | 범위 | 예상 |
|------|------|:---:|
| 진단 (작업 0) | 경고 수집 + 대상 확정 | 0.5d |
| P1 (stocks/serverless/news) | ~127 endpoint | 3~4d |
| P2 (users/thesis/rag) | ~61 endpoint | 2~3d |
| P3 (macro/validation/sec) | ~18 endpoint | 0.5~1d |
| 구조 개선 (작업 2) | 태그/타이틀/auth | 0.5d |
| **합계** | **~250 endpoint** | **약 7~9 man-day** |

> 단, **기능은 이미 동작 중**이므로 점진 보강이 가능하다. `SPECTACULAR_SETTINGS` 주석에 명시된 정책("정확한 schema가 필요한 view만 점진적으로 @extend_schema 추가")과 일치한다. 프론트엔드 codegen(메모리상 Slice 15 codegen 파이프라인 존재)이 의존하는 endpoint부터 P1 우선 보강을 권장한다.

---

## 부록: 검증 명령

```bash
# 스키마 생성 (실측 EXIT=0, 292 operationId)
python manage.py spectacular --file schema.yml

# 경고 가시화 (작업 0)
python manage.py spectacular --validate --fail-on-warn

# 런타임 확인
/api/v2/schema/   # OpenAPI YAML
/api/v2/swagger/  # Swagger UI
/api/v2/redoc/    # ReDoc
```
