# API 문서 감사 보고서

- **감사 대상**: `/Users/byeongjinjeong/Desktop/stock_vis`
- **감사 일자**: 2026-06-18
- **모드**: 읽기 전용 (코드 수정 없음)
- **감사 방법**: `config/urls.py` 진입점 + 14개 `urls.py` + ViewSet 액션 + `config/settings.py` 정적 분석

> ⚠️ **핵심 결론 (선요약)**: drf-spectacular는 이미 **설치·설정·부분 적용**된 상태입니다. "도입"이 아니라 **"커버리지 확대"**가 실제 작업입니다. v1 대다수 엔드포인트는 현재 `DISABLE_ERRORS_AND_WARNINGS=True` + graceful fallback(string body)으로 스키마에 노출되며, 정확한 요청/응답 스키마가 없는 상태입니다.

---

## 현재 상태

### 1. 패키지 설치 여부 (✅ 설치 완료)

`pyproject.toml` 기준:

| 패키지 | 버전 제약 | 비고 |
|--------|----------|------|
| `drf-spectacular` | `^0.29.0` | OpenAPI 3 스펙 자동 생성 |
| `drf-spectacular-sidecar` | `^2026.4.14` | Swagger/ReDoc 정적 에셋 번들 |
| `djangorestframework-simplejwt` | `^5.5.1` | JWT 인증 (스키마 보안 스킴 연동) |

> `drf-yasg`는 미설치 (drf-spectacular로 단일화됨).

### 2. 스펙 자동 생성 가능 여부 (✅ 가능 — 이미 라우팅됨)

`config/urls.py`에 3개 엔드포인트가 등록되어 있습니다:

| 경로 | 뷰 | 용도 |
|------|-----|------|
| `/api/v2/schema/` | `SpectacularAPIView` (name=`schema-v2`) | OpenAPI YAML/JSON |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc UI |

### 3. 스키마 설정 상태 (`config/settings.py`)

```python
REST_FRAMEWORK = {
    ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Stock-Vis Market Pulse v2 API',
    'VERSION': '2.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_DIST': 'SIDECAR',  # 사이드카 에셋
    'REDOC_DIST': 'SIDECAR',
    'SCHEMA_PATH_PREFIX': r'/api/v[12]',   # v1·v2 모두 스캔
    'TAGS': [{'name': 'Market Pulse v2', ...}],
    'DISABLE_ERRORS_AND_WARNINGS': True,   # ⚠️ 경고 억제 (커버리지 누수의 원천)
    'ENUM_NAME_OVERRIDES': { ... },
}
```

**현재 설정의 함의 / 부채**:
- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` → v1·v2 경로를 모두 스캔하므로 **전체 API가 이미 스펙에 포함**됨. 단 `@extend_schema`가 없는 뷰는 직렬화기 추론 실패 시 string body로 fallback.
- `DISABLE_ERRORS_AND_WARNINGS=True` → "unable to guess serializer" 류 경고가 침묵됨. 운영 영향은 0이지만, **어느 뷰가 부정확한 스키마인지 빌드 시점에 드러나지 않음** (커버리지 확대의 가시성 저해).
- `TITLE`/`DESCRIPTION`/`TAGS`가 **Market Pulse v2 전용 문구**로 고정 → 전체 API 문서로 확장하려면 메타데이터 일반화 필요.
- `EXCEPTION_HANDLER`로 에러 envelope 표준화(`{detail, code?, errors?, status_code}`) 적용됨 → 4xx/5xx 응답 스키마를 공통 컴포넌트로 문서화할 토대가 있음.

### 4. 기존 `@extend_schema` 적용 현황 (부분 적용 — 14개 파일)

| 파일 | `extend_schema` 출현 | 커버리지 평가 |
|------|:---:|------|
| `apps/market_pulse/api/views/overview.py` | 2 | ✅ 완전 |
| `apps/market_pulse/api/views/cards.py` | 2 | ✅ 완전 |
| `apps/market_pulse/api/views/news_refresh.py` | 2 | ✅ 완전 |
| `apps/market_pulse/api/views/i18n.py` | 2 | ✅ 완전 |
| `apps/market_pulse/api/views/health.py` | 2 | ✅ 완전 |
| `apps/chain_sight/api/views.py` | 8 | ✅ 대부분 (9 APIView) |
| `apps/chain_sight/api/event_views.py` | 3 | ✅ 완전 (2 APIView) |
| `apps/portfolio/api/views.py` | 7 | ✅ 완전 (e1~e6) |
| `services/serverless/views.py` | 7 | ⚠️ 최소 (~64개 중 7) |
| `services/news/api/views.py` | 3 | ⚠️ 최소 (~32개 중 3) |
| `services/rag_analysis/views.py` | 3 | ⚠️ 최소 (15개 중 3) |
| `packages/shared/users/views.py` | 3 | ⚠️ 최소 (~35개 중 3) |
| `config/settings.py` | (설정) | — |
| `config/spectacular_enums.py` | (enum override) | — |

**판정**: Market Pulse v2 + Chain Sight + Portfolio Coach는 명시적 스키마 적용 완료. 나머지 v1 핵심 앱(stocks·users·news·serverless·rag·thesis·validation·macro·sec_pipeline)은 **거의 미적용** 상태로 자동 추론에 의존.

---

## 엔드포인트 목록 (앱별 테이블)

> 집계 기준: `path()` 패턴 1건 = 1행. ViewSet은 라우터 자동 생성 액션(list/retrieve/create/update/destroy) + `@action` 커스텀 액션을 **operation 수**로 환산해 병기. 수치는 정적 분석 추정치이며 ±2 오차 가능.

### 사용자 지정 우선 앱

| 앱 | URL prefix | 엔드포인트(추정) | 라우팅 방식 | 스키마 커버리지 |
|----|-----------|:---:|------|------|
| **stocks** | `/api/v1/stocks/` | **39** | APIView (path) | ❌ 미적용 |
| **users** | `/api/v1/users/` | **35** | APIView (path) | ⚠️ 3건만 |
| **news** | `/api/v1/news/` | **~32** | `NewsViewSet`(ReadOnly) + `@action` 30 | ⚠️ 3건만 |
| **macro** | `/api/v1/macro/` | **10** | APIView (path) | ❌ 미적용 |
| **rag_analysis** | `/api/v1/rag/` | **15** | APIView (path) | ⚠️ 3건만 |
| **serverless** | `/api/v1/serverless/` | **~64** | FBV(`@api_view`) + admin CBV | ⚠️ 7건만 |
| **thesis** | `/api/v1/thesis/` | **~28** | APIView 8 + ViewSet 3 (nested router) | ❌ 미적용 |
| **validation** | `/api/v1/validation/` | **6** | APIView (path) | ❌ 미적용 |
| **chainsight** | `/api/v1/chainsight/` | **~20** | APIView 9+2 + `WatchlistViewSet`(ModelViewSet+5 action) | ✅ 적용됨 |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | **2** | FBV + APIView | ❌ 미적용 |

### 그 외 앱 (참고)

| 앱 | URL prefix | 엔드포인트(추정) | 비고 |
|----|-----------|:---:|------|
| market_pulse v2 | `/api/v2/market-pulse/` | 5 | ✅ 스키마 완전 적용 |
| portfolio (coach) | `/api/v1/coach/` | 6 | e1~e6, ✅ 적용 |
| portfolio (legacy) | `/api/` | 0 | `urlpatterns=[]` (빈 상태, #65로 view 전부 제거) |
| api_request (provider admin) | `/api/v1/` | 6 | IsAdminUser 권한 |
| iron_trading | `/api/v1/iron-trading/` | 1 | `daily-context` (trailing-slash 2패턴, 동일 뷰) |
| **합계 (전체)** | — | **약 269** | v1 ~259 + v2 ~10 |

### 앱별 상세 (사용자 지정 10개 앱)

**stocks (39)** — dashboard/stock_detail/search 페이지 3 + chart·overview·balance-sheet·income-statement·cashflow·sync 6 + mvp 4 + indicators 3 + search 3 + market-movers 1 + fundamentals 5 + screener 6 + quotes 5 + eod 3.

**users (35)** — JWT 인증 7 + 세션 인증(레거시) 6 + favorites 3 + portfolio 9 + interests 2 + watchlist 8.

**news (~32)** — `NewsViewSet`(ReadOnlyModelViewSet: list+retrieve 2) + `@action` 30 (stock별 뉴스, daily-keywords, news-events, impact-map 등). 라우터 `r""` 등록.

**macro (10)** — pulse/fear-greed/interest-rates/inflation/global-markets/calendar/vix/sectors/sync/sync-status. (`app_name='macro'` 호환 유지, app label은 marketpulse).

**rag_analysis (15)** — DataBasket 6 + AnalysisSession 4 (chat/stream SSE 포함) + monitoring 5.

**serverless (~64)** — admin dashboard 12 + market-movers 2 + sync 2 + keywords 4 + breadth 3 + heatmap 3 + presets 7 + filters 1 + screener 1 + alerts 6 + thesis 4 + etf 9 + llm-relations 4 + institutional 3 + regulatory/patent 2 + health 1. (대부분 함수형 `@api_view`).

**thesis (~28)** — conversation APIView 4 + monitoring 2 + alerts 2 + `ThesisViewSet`(ModelViewSet 6+action 1) + `ThesisPremiseViewSet`(nested, ~6) + `ThesisIndicatorViewSet`(nested, 6+action 1). UUID PK 기반 nested router.

**validation (6)** — symbol별 summary/metrics/leader-comparison/presets/peer-preference/llm-filter.

**chainsight (~20)** — events 2 + seeds/sector-graph/signals/trace 4 + symbol별 neighbors/graph/suggestions 3 + `WatchlistViewSet`(ModelViewSet 6 + `@action` 5 = 11). 이미 `@extend_schema` 적용됨.

**sec_pipeline (2)** — admin/dashboard (FBV) + filing/`<symbol>` (APIView).

---

## 도입 작업 목록

> 재차 강조: 설치/설정/UI 라우팅은 **이미 완료**. 작업의 본질은 ① 메타데이터 일반화 ② v1 핵심 앱 스키마 커버리지 확대 ③ 경고 가시화.

### A. 설정/인프라 (소규모 — 0.5d)

1. **스키마 메타데이터 일반화** (`config/settings.py` SPECTACULAR_SETTINGS)
   - `TITLE`/`DESCRIPTION`을 "Market Pulse v2" → "Stock-Vis API" 전체 범위로 변경
   - `TAGS`에 앱별 태그 추가 (stocks/users/news/macro/rag/serverless/thesis/validation/chainsight/sec) — Swagger 그룹핑 가독성
2. **경고 가시화 옵션 검토**
   - `DISABLE_ERRORS_AND_WARNINGS=True` 유지하되, **CI에서만** `python manage.py spectacular --fail-on-warn`로 신규 추론 실패를 가시화 (커버리지 회귀 방지)
3. **공통 컴포넌트 정의**
   - `EXCEPTION_HANDLER` envelope(`{detail, code?, errors?, status_code}`)를 재사용 가능한 `OpenApiResponse` 컴포넌트로 1회 정의 → 모든 뷰 4xx/5xx에 참조

### B. `@extend_schema` 데코레이터 추가 범위 (대규모 — 본 작업의 80%)

> 적용 단위: APIView는 메서드별(get/post/...), ViewSet은 액션별. `responses=`(직렬화기 또는 인라인) + `request=`(POST/PUT) + `parameters=`(path/query) + `tags=` 명시.

| 우선순위 | 앱 | 대상 operation(추정) | 근거 |
|:---:|----|:---:|------|
| 🔴 P1 | **users** | ~35 | 인증·포트폴리오·워치리스트 — 외부/FE 소비 핵심, 현재 3건만 |
| 🔴 P1 | **stocks** | ~39 | 주가·재무·스크리너 — 데이터 소비 핵심, 0건 |
| 🟠 P2 | **serverless** | ~64 | 최다 엔드포인트, FBV라 `@extend_schema` 개별 부착 비용 큼 |
| 🟠 P2 | **news** | ~32 | `@action` 30개 각각 응답 스키마 정의 필요 |
| 🟡 P3 | **rag_analysis** | ~15 | SSE 스트리밍(chat/stream)은 스키마 표현 특수 처리 |
| 🟡 P3 | **thesis** | ~28 | nested router + UUID PK, ViewSet 스키마화 |
| 🟢 P4 | **validation** | 6 | 소규모, symbol path param 명시 |
| 🟢 P4 | **macro** | 10 | 소규모 |
| 🟢 P4 | **sec_pipeline** | 2 | 소규모 |
| ✅ 완료 | chainsight / market_pulse v2 / portfolio | — | 이미 적용 — 검증만 |

**FBV(serverless) 특이사항**: 함수형 뷰 ~50개는 `@extend_schema`를 함수 데코레이터로 직접 부착 가능하나, 직렬화기가 없는 dict 응답이 많아 **인라인 `inline_serializer` 또는 `OpenApiResponse` 수동 정의**가 필요 → 단위 비용이 CBV보다 높음.

### C. 직렬화기 정비 (병행 필요)

- 다수 v1 뷰가 `Response(dict)` 형태로 직렬화기 없이 응답 → 스키마 추론 불가. 정확한 문서화를 위해 **응답 전용 직렬화기 신설** 또는 `inline_serializer` 사용이 선행 조건.

### 예상 작업량 (러프 추정)

| 구간 | 범위 | 예상 |
|------|------|:---:|
| A. 설정/인프라 | 메타데이터 + CI 게이트 + 공통 envelope | **0.5d** |
| B-P1 | users + stocks (~74 op) | **2~3d** |
| B-P2 | serverless + news (~96 op, FBV 비용↑) | **3~4d** |
| B-P3 | rag + thesis (~43 op, SSE·nested 특수) | **2~3d** |
| B-P4 | validation + macro + sec (~18 op) | **1d** |
| C. 직렬화기 정비 | 응답 직렬화기/인라인 (B와 중첩) | **2~3d** |
| 검증 | 스키마 빌드 + Swagger 육안 + CI 게이트 | **1d** |
| **합계** | 전체 v1 커버리지 완성 | **약 11~15일 (1인 기준)** |

> **권장 접근**: 전면 일괄보다 **P1(users·stocks)부터 점진 적용** + CI `--fail-on-warn` 게이트로 회귀 방지. SPECTACULAR_SETTINGS 주석에도 "정확한 schema 필요한 view만 점진적 추가" 방침이 이미 명시됨 — 그 방침을 우선순위 테이블로 구체화한 것이 본 작업 목록.

---

## 부록: 감사 한계

- 본 보고서는 **정적 분석 추정치**로, 실제 operation 수는 `python manage.py spectacular --file schema.yml` 생성 후 `paths` 카운트로 확정해야 정확함 (읽기 전용 제약으로 미실행).
- ViewSet 액션 수는 `@action` 데코레이터 grep 기준이며, 라우터가 생성하는 표준 CRUD 액션은 권한/메서드 제한에 따라 실제 노출 수가 달라질 수 있음.
- `services/_dormant/graph_analysis/`는 휴면(dormant) 처리되어 라우팅 미등록 → 집계 제외.
