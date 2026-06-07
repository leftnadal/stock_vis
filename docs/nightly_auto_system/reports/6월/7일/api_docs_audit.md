# API 문서 감사 보고서

> 생성일: 2026-06-07 · 모드: 읽기 전용 (코드 수정 없음)
> 대상 브랜치: main · 범위: Django REST Framework 백엔드 전체 URLconf

---

## 현재 상태

### 1. 문서화 도구 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| **drf-spectacular** | ✅ 설치됨 (`^0.29.0`) | `pyproject.toml`, `poetry.lock` |
| **drf-spectacular-sidecar** | ✅ 설치됨 (`^2026.4.14`) | `pyproject.toml` (Swagger/ReDoc 정적 자산) |
| drf-yasg | ❌ 미설치 | (대체 도구 — 사용 안 함) |
| **자동 스키마 생성** | ✅ 가능 + 운영 중 | `config/urls.py:62-72` |

**결론**: 도구는 이미 도입·운영 중이다. 본 감사는 "신규 도입"이 아니라 **"커버리지 확대"** 관점에서 접근한다.

### 2. OpenAPI 스펙 자동 생성 가능 여부 — ✅ 가능 (운영 중)

`config/settings.py:212-213`에 앱 등록, `config/urls.py`에 엔드포인트 3종 노출:

| 경로 | 역할 |
|------|------|
| `GET /api/v2/schema/` | OpenAPI 3.x JSON/YAML 스펙 (`SpectacularAPIView`) |
| `GET /api/v2/swagger/` | Swagger UI (`SpectacularSwaggerView`) |
| `GET /api/v2/redoc/` | ReDoc (`SpectacularRedocView`) |

**핵심 설정** (`config/settings.py:370-397`):
- `DEFAULT_SCHEMA_CLASS = 'drf_spectacular.openapi.AutoSchema'` — DRF 전역 스키마 클래스 연결됨
- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` — **v1·v2 모두 스키마에 포함되도록 설정됨**
- `TITLE = 'Stock-Vis Market Pulse v2 API'`, `VERSION = '2.0'` — 제목/버전이 Market Pulse v2 중심으로 고정되어 있음 (전체 API를 대표하지 못함 → 개선 포인트)
- `DISABLE_ERRORS_AND_WARNINGS = True` — **명시적 `@extend_schema`가 없는 v1 엔드포인트는 graceful fallback(string body)으로 노출되며, 경고를 끔.** 즉 스펙은 "생성"되나 v1 다수는 **타입 없는 빈 스키마** 상태.

### 3. 현재 `@extend_schema` 적용 현황

소스 코드(`docs/` 제외)에서 `@extend_schema` 데코레이터 **35건**이 12개 파일에 분포:

| 파일 | 데코레이터 수 | 비고 |
|------|--------------|------|
| `apps/chain_sight/api/views.py` | 7 | Chain Sight 그래프 |
| `apps/portfolio/api/views.py` | 6 | Coach E1~E6 |
| `services/serverless/views.py` | 6 | Market Movers 등 일부 |
| `packages/shared/api_request/admin_views.py` | 5 | Provider Admin |
| `apps/market_pulse/api/views/*.py` (5파일) | 5 | v2 카드/overview/health/i18n/news |
| `services/rag_analysis/views.py` | 2 | DataBasket 일부 |
| `services/news/api/views.py` | 2 | NewsViewSet 일부 |
| `packages/shared/users/views.py` | 2 | 일부 |

> **편중 구조**: 신규 작성된 v2 계열(market_pulse, chainsight, portfolio coach, api_request admin)은 문서화가 되어 있으나, **레거시 v1 핵심(stocks 39, users 35, macro 10, serverless 64, news 32)은 거의 미문서화**.

---

## 엔드포인트 목록 (앱별 테이블)

> 집계 기준: `path()` 패턴 1건 = 1 엔드포인트. ViewSet(router) 등록은 list/detail 라우트 + `@action`을 개별 합산. trailing-slash 중복(iron_trading)은 1건으로 집계.

| # | 앱 | URL Prefix | urls.py 경로 | 엔드포인트 수 | `@extend_schema` | 문서화 |
|---|----|-----------|-------------|:---:|:---:|:---:|
| 1 | **stocks** | `/api/v1/stocks/` | `packages/shared/stocks/urls.py` | 39¹ | 0 | ❌ |
| 2 | **users** | `/api/v1/users/` | `packages/shared/users/urls.py` | 35 | 2 | 🔸 부분 |
| 3 | **news** | `/api/v1/news/` | `services/news/api/urls.py` | 32² | 2 | 🔸 부분 |
| 4 | **macro** | `/api/v1/macro/` | `apps/market_pulse/urls.py` | 10 | 0 | ❌ |
| 5 | **market_pulse v2** | `/api/v2/market-pulse/` | `apps/market_pulse/api/urls.py` | 5 | 5 | ✅ 완전 |
| 6 | **rag_analysis** | `/api/v1/rag/` | `services/rag_analysis/urls.py` | 15 | 2 | 🔸 부분 |
| 7 | **serverless** | `/api/v1/serverless/` | `services/serverless/urls.py` | 64 | 6 | 🔸 부분 |
| 8 | **thesis** | `/api/v1/thesis/` | `thesis/urls.py` | 16³ | 0 | ❌ |
| 9 | **validation** | `/api/v1/validation/` | `services/validation/api/urls.py` | 6 | 0 | ❌ |
| 10 | **chainsight** | `/api/v1/chainsight/` | `apps/chain_sight/api/urls.py` | 14⁴ | 7 | ✅ 대부분 |
| 11 | **sec_pipeline** | `/api/v1/sec-pipeline/` | `services/sec_pipeline/urls.py` | 2 | 0 | ❌ |
| 12 | **api_request** (admin) | `/api/v1/` | `packages/shared/api_request/urls.py` | 6 | 5 | ✅ 대부분 |
| 13 | **portfolio (coach)** | `/api/v1/coach/` | `apps/portfolio/api/urls.py` | 6 | 6 | ✅ 완전 |
| 14 | **iron_trading** | `/api/v1/iron-trading/` | `integrations/iron_trading/urls.py` | 1 | 0 | ❌ |
| — | (schema/swagger/redoc) | `/api/v2/{schema,swagger,redoc}/` | `config/urls.py` | 3 | — | (인프라) |
| | **합계** | | | **≈ 251** | **35** | **~14%** |

**주석**
- ¹ stocks 39건 중 `DashboardView`(`""`), `StockDetailView`(`stock/<symbol>/`) 2건은 HTML 페이지 렌더링 뷰(API 아님). 순수 API ≈ 37건.
- ² news는 `NewsViewSet(ReadOnlyModelViewSet)` — 기본 list/retrieve 2건 + `@action` 30건 = 32건.
- ³ thesis 16건 내역: 명시 `path()` 8건(conversation×4, dashboard, readings, alerts×2) + ViewSet 3종(`ThesisViewSet` 2라우트+1액션, `ThesisPremiseViewSet` 2라우트, `ThesisIndicatorViewSet` 2라우트+1액션) ≈ 8건.
- ⁴ chainsight 14건 내역: 명시 `path()` 7건 + `WatchlistViewSet(ModelViewSet)` 2라우트 + `@action` 5건 = 14건.

> **요청 목록(stocks, users, news, macro, rag_analysis, serverless, thesis, validation, chainsight, sec_pipeline) 10개 앱 소계**: 39+35+32+10+15+64+16+6+14+2 = **233 엔드포인트**.

### 커버리지 요약

- **완전/대부분 문서화** (✅): market_pulse v2, chainsight, portfolio coach, api_request admin — **합계 31 엔드포인트**
- **부분 문서화** (🔸): users, news, rag_analysis, serverless — 대표 엔드포인트만 `@extend_schema`, 나머지 fallback
- **미문서화** (❌): **stocks(39), macro(10), thesis(16), validation(6), sec_pipeline(2), iron_trading(1)** — 합계 74 엔드포인트가 타입 없는 스키마

전체 약 251개 중 명시적 문서화 ~35건 → **실질 커버리지 약 14%**.

---

## 도입(확대) 작업 목록

> 도구는 이미 설치·운영 중이므로 "설치"가 아닌 **"커버리지 확대 + 메타데이터 정비"**가 실제 과제다.

### A. 설정 정비 (소규모, 0.5일)

1. **`SPECTACULAR_SETTINGS` 메타 일반화** (`config/settings.py:377-397`)
   - `TITLE`을 `'Stock-Vis Market Pulse v2 API'` → `'Stock-Vis Platform API'`로 변경, `VERSION` 재정의
   - `TAGS`에 앱별 그룹(`Stocks`, `Users`, `News`, `RAG`, `Serverless`, `Thesis`, `Validation`, `Chain Sight`, `SEC` 등) 추가 → Swagger UI 가독성
2. **`DISABLE_ERRORS_AND_WARNINGS` 일시 해제 후 경고 수집**
   - `python manage.py spectacular --file /tmp/schema.yml --validate` 실행하여 fallback 경고 목록 확보 (작업 우선순위 산정용). **운영 설정은 그대로 유지**, 측정용 1회 실행만.

### B. `@extend_schema` 데코레이터 확대 (핵심, 가장 큰 작업량)

미문서화/부분 문서화 엔드포인트에 `@extend_schema(responses=..., parameters=..., tags=...)` 추가. ViewSet은 `@extend_schema_view`로 액션별 일괄 지정.

| 우선순위 | 대상 앱 | 미문서 엔드포인트 | 예상 데코레이터 | 비고 |
|:---:|------|:---:|:---:|------|
| **P1** | stocks | ~37 | ~37 | 트래픽 핵심, Serializer 다수 존재 → 연결 용이 |
| **P1** | serverless | ~58 | ~58 | 함수형 뷰(FBV) 다수 → 수동 `responses` 정의 필요(난이도↑) |
| **P2** | news | ~30 | ~30 | `@action` 30건, 응답 형태 제각각 |
| **P2** | users | ~33 | ~33 | 인증/포트폴리오/watchlist — Serializer 보유 |
| **P2** | rag_analysis | ~13 | ~13 | SSE 스트리밍(`chat/stream`)은 OpenAPI 표현 제약 → 주석 보강 |
| **P3** | thesis | 16 | 16 | ViewSet 3종 — `@extend_schema_view` 권장 |
| **P3** | macro | 10 | 10 | 응답 구조 단순 |
| **P3** | validation | 6 | 6 | Serializer 정비 동반 필요 |
| **P3** | sec_pipeline | 2 | 2 | 소규모 |
| **P3** | iron_trading | 1 | 1 | read-only 단일 |
| | **합계** | **~206** | **~206** | |

### C. Serializer 인벤토리 점검 (B의 선행)

- `@extend_schema(responses=SomeSerializer)`가 가장 정확. FBV(serverless 다수)나 raw `Response(dict)` 반환 뷰는 **응답 Serializer가 없어** `inline_serializer` 또는 `OpenApiResponse(response={...})` 수동 작성 필요.
- 작업 전 앱별 Serializer 보유 여부 조사 → 보유 앱(stocks/users/rag)은 빠르게, 미보유 앱(serverless FBV)은 별도 공수.

### D. 검증 자동화 (선택, 0.5일)

- CI에 `spectacular --validate --fail-on-warn` 게이트 추가 → 신규 엔드포인트 무문서 머지 차단 (현재 `DISABLE_ERRORS_AND_WARNINGS=True`로 무력화 상태이므로, 전환 시 게이트로 회귀 방지).

### 예상 작업량 총괄

| 단계 | 작업 | 예상 공수 |
|------|------|:---:|
| A | 설정 메타 정비 + 경고 측정 | 0.5일 |
| C | Serializer 인벤토리 조사 | 0.5일 |
| B-P1 | stocks + serverless (~95건) | 3~4일 |
| B-P2 | news + users + rag (~76건) | 2~3일 |
| B-P3 | thesis/macro/validation/sec/iron (~35건) | 1~1.5일 |
| D | CI 검증 게이트 | 0.5일 |
| | **합계** | **약 8~10일** (1인 기준) |

> **권장 접근**: 한 번에 전체를 하지 말고 **앱 단위 점진 적용**(기존 `DISABLE_ERRORS_AND_WARNINGS=True` 유지하며 P1→P3 순). 트래픽 핵심인 **stocks·serverless 우선**이 ROI 최대.

---

## 부록: 감사 방법

```bash
# 1) urls.py 인벤토리
find . -name 'urls.py' -not -path '*migrations*' -not -path '*__pycache__*' -not -path '*node_modules*'
# → 16개 urls.py (config 포함)

# 2) 문서화 도구 설치 확인
grep -iE 'spectacular|yasg' pyproject.toml
# → drf-spectacular ^0.29.0, drf-spectacular-sidecar ^2026.4.14

# 3) @extend_schema 적용 현황 (소스 한정)
grep -rn '^\s*@extend_schema' --include='*.py' .
# → 35건 / 12파일
```

**한계**: 본 집계는 `path()` 정적 분석 기반이다. ViewSet router의 정확한 라우트 수는 `python manage.py show_urls`(django-extensions) 또는 `urlpatterns` 런타임 전개로 ±5% 오차 가능. 본 보고서는 코드 미실행(읽기 전용) 원칙에 따라 정적 카운트만 제시한다.
