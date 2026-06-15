# API 문서 감사 보고서

> 생성일: 2026-06-15 · 모드: 읽기 전용 (코드 무수정) · 대상: `/Users/byeongjinjeong/Desktop/stock_vis`
> 검증 방법: 정적 `urls.py`/`views.py` 분석 + `manage.py spectacular` 실제 스키마 생성(EXIT=0, 251 path)

---

## 핵심 결론 (요약)

| 항목 | 상태 |
|------|------|
| drf-spectacular 설치 | ✅ **설치 완료** (`^0.29.0` + sidecar `^2026.4.14`) |
| OpenAPI 스펙 자동 생성 | ✅ **작동 확인** — `spectacular` 명령 EXIT=0, 251개 path 생성, 오류 0 |
| Swagger UI / ReDoc | ✅ **노출 중** (`/api/v2/swagger/`, `/api/v2/redoc/`, `/api/v2/schema/`) |
| 스키마 커버리지 (path prefix) | ✅ `/api/v[12]` 전체 — v1·v2 모두 포함 |
| `@extend_schema` 명시 적용 | ⚠️ **부분** — 37개 데코레이터 / 13개 파일 (핵심 영역만) |
| 나머지 v1 엔드포인트 | ⚠️ graceful fallback (string body) — 정확한 request/response 스키마 없음 |

> **중요 정정**: 본 감사의 사전 가정("drf-spectacular 또는 drf-yasg 도입 필요")과 달리,
> **drf-spectacular는 이미 설치·설정·작동 중**입니다. 따라서 남은 작업은 "도입"이 아니라
> **"커버리지 확대 + 스키마 품질 개선"** 입니다. drf-yasg는 미설치(불필요).

---

## 현재 상태

### 1) 의존성 (pyproject.toml)

```toml
drf-spectacular = "^0.29.0"
drf-spectacular-sidecar = "^2026.4.14"   # Swagger UI / ReDoc 정적 자산
```
- `requirements.txt`: spectacular 관련 핀 없음 (Poetry가 1차 소스).
- **drf-yasg / coreapi: 미설치** — 신규 도입 불필요.

### 2) 설정 (config/settings.py)

```python
INSTALLED_APPS = [ ... 'drf_spectacular', 'drf_spectacular_sidecar', ... ]   # L212-213

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',           # L377
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
}

SPECTACULAR_SETTINGS = {                                                     # L384-
    'TITLE': 'Stock-Vis Market Pulse v2 API',
    'VERSION': '2.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_DIST': 'SIDECAR',  'REDOC_DIST': 'SIDECAR',
    'SCHEMA_PATH_PREFIX': r'/api/v[12]',   # v1·v2 동시 노출
    'DISABLE_ERRORS_AND_WARNINGS': True,   # ⚠️ fallback noise 무시 (아래 리스크 참조)
    'ENUM_NAME_OVERRIDES': { ... },        # enum collision 수동 해소
}
```

### 3) 라우팅 (config/urls.py)

```python
path('api/v2/schema/',  SpectacularAPIView.as_view(),      name='schema-v2')
path('api/v2/swagger/', SpectacularSwaggerView.as_view(url_name='schema-v2'))
path('api/v2/redoc/',   SpectacularRedocView.as_view(url_name='schema-v2'))
```

### 4) 자동 생성 실증

```
$ python manage.py spectacular --file /tmp/schema_audit.yaml
EXIT=0   ·   스키마 path 251개   ·   파일 217KB   ·   stderr 비어 있음
```
- `DISABLE_ERRORS_AND_WARNINGS=True` 덕분에 'unable to guess serializer' 류 경고가
  **억제된 채로** 통과 → 빌드는 성공하나 **품질 경고가 숨겨지는** 구조.

### 5) `@extend_schema` 명시 커버리지 (파일별)

| 파일 | 데코레이터 수 |
|------|:---:|
| `apps/chain_sight/api/views.py` | 8 |
| `apps/portfolio/api/views.py` | 7 |
| `services/serverless/views.py` | 7 |
| `packages/shared/api_request/admin_views.py` | 6 |
| `apps/chain_sight/api/event_views.py` | 3 |
| `packages/shared/users/views.py` | 3 |
| `services/news/api/views.py` | 3 |
| `services/rag_analysis/views.py` | 3 |
| `apps/market_pulse/api/views/{cards,health,i18n,news_refresh,overview}.py` | 각 2 (합 10*) |
| **합계** | **37 데코레이터 / 13 파일** |

> *market_pulse api 5개 파일은 import 1 + 데코레이터 1씩(=파일당 grep 2). 실 데코레이터는 파일당 1개.
> 명시 스키마가 **전혀 없는** 앱: **stocks, thesis, validation, macro, sec_pipeline, iron_trading** → 전부 fallback 노출.

---

## 엔드포인트 목록 (앱별 테이블)

> 라우트(path) 기준 집계. ViewSet은 router 자동 생성 액션(list/create/retrieve/update/partial_update/destroy + `@action`) 포함하여 **스키마 operation 수**로 표기.
> "명시 스키마"는 해당 앱 view에 `@extend_schema`가 적용됐는지 여부.

### 요청된 10개 앱

| 앱 | URL prefix | 스키마 operation 수 | 명시 `@extend_schema` | 라우팅 형태 |
|----|-----------|:---:|:---:|------|
| **stocks** | `/api/v1/stocks/` | 37 | ❌ 없음 | 함수형 path 39개 중 2개는 HTML view(dashboard/detail) → 스키마 제외 |
| **users** | `/api/v1/users/` | 35 | ✅ 3 (일부) | JWT 7 + 세션 6 + favorites 3 + portfolio 9 + interests 2 + watchlist 8 |
| **news** | `/api/v1/news/` | 32 | ✅ 3 (일부) | `DefaultRouter` + `NewsViewSet` (`@action` ~29개) |
| **macro** | `/api/v1/macro/` | 10 | ❌ 없음 | 함수형 path 10개 (pulse/fear-greed/rates/inflation/global/calendar/vix/sectors/sync×2) |
| **rag_analysis** | `/api/v1/rag/` | 15 | ✅ 3 (일부) | DataBasket 6 + Session 4 + Monitoring 5 |
| **serverless** | `/api/v1/serverless/` | 64 | ✅ 7 (일부) | Admin 11 + Movers/keywords 9 + breadth 3 + heatmap 3 + presets 8 + screener/alerts 9 + thesis 4 + etf 8 + llm-relations 4 + institutional 3 + regulatory/patent 2 + health 1 |
| **thesis** | `/api/v1/thesis/` | 16 | ❌ 없음 | router(ThesisViewSet CRUD+action) + nested premise/indicator ViewSet + conversation 4 + dashboard/readings 2 + alerts 2 |
| **validation** | `/api/v1/validation/` | 6 | ❌ 없음 | `<symbol>/` 하위 summary/metrics/leader-comparison/presets/peer-preference/llm-filter |
| **chainsight** | `/api/v1/chainsight/` | 16 | ✅ 11 (높음) | events 2 + seeds/sector/signals/trace 4 + neighbors/graph/suggestions 3 + WatchlistViewSet(CRUD + `@action` 5) |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | 1 | ❌ 없음 | filing/`<symbol>` (APIView) 노출 / admin/dashboard 함수뷰는 스키마 제외 |

### 그 외 노출 앱 (참고)

| 앱 | URL prefix | 스키마 operation 수 | 명시 `@extend_schema` | 비고 |
|----|-----------|:---:|:---:|------|
| portfolio coach | `/api/v1/coach/` | 6 | ✅ 7 (완전) | E1~E6 함수형 view |
| market-pulse v2 | `/api/v2/market-pulse/` | 5 | ✅ 5 (완전) | overview/card-detail/news-refresh/i18n/health — **유일하게 완전 문서화** |
| api_request admin | `/api/v1/admin/providers/` | 5 | ✅ 6 (완전) | provider status/rate-limits/cache/test/config |
| iron-trading | `/api/v1/iron-trading/` | 2 | ❌ 없음 | daily-context (slash 유무 2개) |
| health/root | `/api/v1/health/`, `/` | 1+ | ❌ 없음 | 함수형 health_check |

**스키마 총계: 251 operation** (생성 검증치). 주요 비중: serverless(64) > stocks(37) > users(35) > news(32).

---

## 도입 작업 목록

> drf-spectacular는 **이미 도입 완료** 상태이므로, 아래는 **(A) 즉시 가능한 운영 개선**과
> **(B) 스키마 품질(정확도) 확대** 두 갈래로 구분한다. "설치/설정" 단계는 불필요.

### A. 인프라 — 이미 완료 (추가 작업 없음)

- [x] drf-spectacular + sidecar 설치 (pyproject)
- [x] `DEFAULT_SCHEMA_CLASS = AutoSchema` 설정
- [x] `SPECTACULAR_SETTINGS` (TITLE/VERSION/PATH_PREFIX/SIDECAR)
- [x] schema / swagger / redoc URL 노출
- [x] enum collision 수동 해소(`ENUM_NAME_OVERRIDES`)
- [x] 스키마 생성 정상 동작(EXIT=0)

### B. 스키마 품질 확대 (= 실제 남은 작업)

명시 스키마가 없어 **string body fallback**으로만 노출되는 앱에 `@extend_schema(request=..., responses=...)`를 점진 추가.

| 우선순위 | 대상 앱 | operation 수 | 현재 | 작업 내용 | 난이도 |
|:---:|------|:---:|:---:|------|:---:|
| P1 | **stocks** | 37 | fallback | 함수형/APIView 37개에 serializer 연결 + `@extend_schema(responses=...)` | 높음(분량 큼) |
| P1 | **serverless** | 64 | 부분(7/64) | 함수형 view 다수 — request param/response 스키마화. 57개 미적용 | 높음(최대 분량) |
| P2 | **users** | 35 | 부분(3/35) | JWT/포트폴리오/watchlist serializer 매핑 | 중 |
| P2 | **news** | 32 | 부분(3/32) | `NewsViewSet` `@action`별 응답 스키마 | 중 |
| P2 | **thesis** | 16 | 없음 | ModelViewSet은 serializer 자동 추론 가능 — 검증 위주 | 중(자동추론 유리) |
| P3 | **macro** | 10 | 없음 | 대시보드 응답 스키마 | 낮음 |
| P3 | **rag_analysis** | 15 | 부분(3/15) | DataBasket/Session 응답 | 낮음 |
| P3 | **validation** | 6 | 없음 | `<symbol>` 응답 6종 | 낮음 |
| P3 | **sec_pipeline** | 1 | 없음 | filing 응답 1종 | 낮음 |

**예상 작업량 (스키마 데코레이터 적용 기준)**
- 미적용/부분 operation ≈ **251 − 37(완전·부분 적용분) ≈ 200여 operation**.
- 단순 응답(P3 4개 앱, ~32 op): 1~2일.
- 중간(users/news/thesis/macro, ~93 op): 3~5일.
- 대형(stocks 37 + serverless 57 미적용, ~94 op): 5~8일 (serializer 신규 정의 동반 시 증가).
- **총합 추정: 약 9~15 작업일** (전수 정밀화 기준). 단, ModelViewSet 계열은 자동 추론으로 비용 절감 가능.

### C. 운영 리스크 / 권고 (선택)

1. **`DISABLE_ERRORS_AND_WARNINGS=True` 리스크** — 'unable to guess serializer' 경고가 숨겨져
   품질 저하가 무성(無聲)으로 누적됨. 권고: CI에서 임시로 `--fail-on-warn` 또는 경고 활성화 버전을
   별도 잡으로 돌려 미적용 endpoint를 가시화(현 운영 스키마는 그대로 유지).
2. **TITLE/DESCRIPTION이 "Market Pulse v2" 한정** — 실제 스키마는 v1 전체(251 op)를 포함하므로
   문서 제목/설명이 범위를 과소 표현. 전사 API 문서로 쓰려면 메타데이터 갱신 권고.
3. **TAGS 미정의** — `Market Pulse v2` 단일 태그만 등록. Swagger UI에서 앱별 그룹핑이 안 되어
   251개가 평면 나열. `@extend_schema(tags=[...])` 또는 `TAGS` 확장으로 앱별 분류 권고.
4. **HTML view 혼재** — `stocks` dashboard/detail은 TemplateView 성격. 스키마에서 자동 제외되나,
   API/페이지 라우팅이 한 `urls.py`에 섞여 있어 분리 정리 시 가독성 향상.

---

## 부록 — 검증 명령 (재현용, 읽기 전용)

```bash
# urls/views 인벤토리
find . -name 'urls.py'  -not -path '*migrations*' -not -path '*__pycache__*' -not -path '*node_modules*'
find . -name 'views*.py' -not -path '*migrations*' -not -path '*__pycache__*' -not -path '*node_modules*'

# 의존성 확인
grep -iE 'spectacular|yasg|swagger|openapi' pyproject.toml

# 스키마 자동 생성 (산출물만, 코드 무변경)
python manage.py spectacular --file /tmp/schema_audit.yaml
grep -E "^  /" /tmp/schema_audit.yaml | wc -l        # 251

# @extend_schema 실제 적용 수
grep -rn '@extend_schema' --include='*.py' apps packages services thesis integrations | wc -l   # 37
```
