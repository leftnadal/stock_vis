# API 문서 감사 보고서

> 생성일: 2026-06-03 · 모드: **읽기 전용 감사** (코드 수정 없음)
> 대상: `/Users/byeongjinjeong/Desktop/stock_vis`
> 감사 범위: `config/urls.py` 및 include된 전체 앱 `urls.py` (15개 파일)

---

## ⚠️ 핵심 발견 (요약)

| 항목 | 상태 |
|------|------|
| **drf-spectacular** | ✅ **이미 설치 + 설정 완료** (`^0.29.0` + sidecar `^2026.4.14`) |
| **drf-yasg** | ❌ 미사용 (spectacular로 단일화됨) |
| **OpenAPI 스펙 자동 생성** | ✅ 가능 — `/api/v2/schema/` (Swagger·ReDoc 포함) |
| **DEFAULT_SCHEMA_CLASS** | ✅ `drf_spectacular.openapi.AutoSchema` 전역 적용 |
| **실제 과제** | "도입"이 아니라 **`@extend_schema` 커버리지 확장**. 현재 약 271개 엔드포인트 중 명시적 스키마 데코레이터는 약 47곳(13개 파일)에만 적용 — 나머지는 graceful fallback(string body)으로만 노출 |

> **본 보고서는 task가 가정한 "문서화 미도입 상태"가 아님을 정정한다.** 인프라는 이미 구축되어 있고, 남은 작업은 v1 엔드포인트의 정확한 request/response 스키마 명시이다. 따라서 §3은 "도입"이 아니라 "**커버리지 개선 작업**"으로 재구성했다.

---

## 1. 현재 상태

### 1.1 설치된 문서화 패키지

`pyproject.toml`:
```toml
drf-spectacular = "^0.29.0"            # pyproject.toml:38
drf-spectacular-sidecar = "^2026.4.14" # pyproject.toml:39 (Swagger/ReDoc 정적 자산 self-host)
```
- `poetry.lock`에 `drf-spectacular` 잠금 확인 (line 1073)
- `requirements.txt`는 비어 있음 — 의존성은 **Poetry 단독 관리**
- `drf-yasg` / `drf_yasg`: 코드·의존성 모두 **부재** (spectacular로 통일됨)

### 1.2 스펙 자동 생성 엔드포인트 (`config/urls.py:61-72`)

| 경로 | 뷰 | 용도 |
|------|----|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 스펙(YAML/JSON) 자동 생성 |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc UI |

### 1.3 전역 설정

**`config/settings.py:370`**
```python
'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'
```

**`SPECTACULAR_SETTINGS`** (`config/settings.py`) 주요 항목:
- `TITLE`: "Stock-Vis Market Pulse v2 API" — **현재 타이틀이 v2 중심으로 좁게 설정됨** (전체 플랫폼 API를 포괄하지 못함)
- `VERSION`: "2.0"
- `SCHEMA_PATH_PREFIX`: `r'/api/v[12]'` → v1·v2 모두 스키마에 포함
- `SWAGGER_UI_DIST` / `REDOC_DIST`: `'SIDECAR'` (오프라인 자산)
- `COMPONENT_SPLIT_REQUEST`: True
- **`DISABLE_ERRORS_AND_WARNINGS`: True** ← 핵심. 스키마 추론 실패 시 경고를 죽이고 graceful fallback(string body)으로 노출. 즉 **미문서화 엔드포인트도 스펙에는 나타나지만, request/response 본문이 부정확**하게 표시됨.
- `ENUM_NAME_OVERRIDES`: thesis/news/chainsight의 enum collision 4건 수동 해결

> 설정 주석에 명시된 정책: *"핵심 영역(marketpulse, chainsight, api_request admin)은 명시적 @extend_schema로 정상 처리. 나머지 v1 endpoint는 graceful fallback. 정확한 schema가 필요한 view만 점진적으로 추가."* → **의도된 점진적 문서화 전략**이 이미 채택되어 있음.

### 1.4 `@extend_schema` 적용 현황 (명시적 문서화)

데코레이터가 적용된 파일은 **13개**, 데코레이터 총 약 **47곳**:

| 파일 | extend_schema 수 |
|------|:---:|
| `apps/chain_sight/api/views.py` | 8 |
| `services/serverless/views.py` | 7 |
| `apps/portfolio/api/views.py` | 7 |
| `packages/shared/api_request/admin_views.py` | 6 |
| `apps/market_pulse/api/views/*` (5개 파일) | 각 2 (계 10) |
| `services/rag_analysis/views.py` | 3 |
| `services/news/api/views.py` | 3 |
| `packages/shared/users/views.py` | 3 |

**미적용(graceful fallback) 영역**: `stocks/*` 전체(39개), `macro`(10개), `validation`(6개), `sec_pipeline`(2개), `iron_trading`, `thesis`의 대부분, `serverless`의 대부분 등 — 전체의 약 80%.

---

## 2. 엔드포인트 목록 (앱별)

> 집계 기준: `path()` 1건 = 1엔드포인트. DefaultRouter 등록 ViewSet은 **표준 라우트(list/retrieve/create/update/partial_update/destroy) + `@action` 커스텀 라우트**로 전개하여 추정. trailing-slash 중복 라우트는 1건으로 합산.

| # | 앱 / 그룹 | URL prefix | 엔드포인트 수 | urls.py 경로 | 비고 |
|---|-----------|-----------|:---:|------|------|
| 1 | **stocks** | `/api/v1/stocks/` | **39** | `packages/shared/stocks/urls.py` | 8개 view 모듈 분할(chart·overview·재무3종·MVP·indicators·search·movers·fundamentals·screener·quotes·EOD). @extend_schema 0 |
| 2 | **users** | `/api/v1/users/` | **35** | `packages/shared/users/urls.py` | JWT 7 + 세션 6 + 즐겨찾기 3 + 포트폴리오 9 + 관심사 2 + Watchlist 8. @extend_schema 3 |
| 3 | **serverless** | `/api/v1/serverless/` | **~64** | `services/serverless/urls.py` | Admin Dashboard 12 + Movers 4 + 키워드 4 + Breadth 3 + Heatmap 3 + Presets 7 + Screener/Filters 2 + Alerts 6 + Thesis 4 + ETF 6 + Themes 3 + LLM-relations 4 + Institutional 3 + Regulatory/Patent 2 + Health 1. 함수형 view 대다수 |
| 4 | **news** | `/api/v1/news/` | **~31** | `services/news/api/urls.py` | `NewsViewSet`(DefaultRouter, prefix `r""`) — `@action` 커스텀 **30개**(detail=False) + 기본 list. @extend_schema 3 |
| 5 | **thesis** | `/api/v1/thesis/` | **~28** | `thesis/urls.py` | 함수형/APIView 8(conversation 4 + monitoring 2 + alerts 2) + `ThesisViewSet`(6+2 action) + `PremiseViewSet`(nested, 6) + `IndicatorViewSet`(nested, 6) |
| 6 | **chainsight** | `/api/v1/chainsight/` | **~18** | `apps/chain_sight/api/urls.py` | APIView 7(seeds·sector-graph·signals·trace·neighbors·graph·suggestions) + `WatchlistViewSet`(6 + action 5 = 11). @extend_schema 8 |
| 7 | **rag_analysis** | `/api/v1/rag/` | **15** | `services/rag_analysis/urls.py` | DataBasket 6 + AnalysisSession 4(SSE 스트리밍 포함) + Monitoring 5. @extend_schema 3 |
| 8 | **macro** (market_pulse v1) | `/api/v1/macro/` | **10** | `apps/market_pulse/urls.py` | pulse·fear-greed·interest-rates·inflation·global-markets·calendar·vix·sectors·sync·sync-status. @extend_schema 0 |
| 9 | **validation** | `/api/v1/validation/` | **6** | `services/validation/api/urls.py` | summary·metrics·leader-comparison·presets·peer-preference·llm-filter (전부 `<symbol>` 기반). @extend_schema 0 |
| 10 | **portfolio (coach)** | `/api/v1/coach/` | **6** | `apps/portfolio/api/urls.py` | coach e1~e6 (DRF 함수형). `apps/portfolio/urls.py`는 빈 패턴(legacy 제거 완료). @extend_schema 7 |
| 11 | **api_request (provider admin)** | `/api/v1/` | **6** | `packages/shared/api_request/urls.py` | health + admin/providers 5(status·rate-limits·cache·test·config). @extend_schema 6 (전수 적용) |
| 12 | **market_pulse v2** | `/api/v2/market-pulse/` | **5** | `apps/market_pulse/api/urls.py` | overview·cards/detail·news/refresh·i18n·health. @extend_schema 10 (전수 적용) |
| 13 | **sec_pipeline** | `/api/v1/sec-pipeline/` | **2** | `services/sec_pipeline/urls.py` | admin/dashboard + filing/`<symbol>`. @extend_schema 0 |
| 14 | **iron_trading** | `/api/v1/iron-trading/` | **1** | `integrations/iron_trading/urls.py` | daily-context (trailing-slash 2 라우트 = 1 엔드포인트). 외부 봇 read-only |
| 15 | **config (root)** | `/` | **5** | `config/urls.py` | api_root·health + schema·swagger·redoc 3 |
| - | **graph_analysis** | — | **0 (휴면)** | `services/_dormant/graph_analysis/views.py` | `_dormant/` 이동 — URL 미등록 (API 미구현) |
| | **합계** | | **≈ 271** | | |

> **구조 참고**: CLAUDE.md의 앱 경로 설명(루트 평면 배치)과 실제 트리가 다름. 현재는 `apps/`(chain_sight·portfolio·market_pulse), `services/`(rag_analysis·serverless·news·sec_pipeline·validation·_dormant), `packages/shared/`(stocks·users·api_request·metrics), 루트(`thesis`), `integrations/`(iron_trading)로 **모노레포식 재편**되어 있다.

### 2.1 task 지정 10개 앱 집계

| 앱 | 엔드포인트 수 | @extend_schema |
|----|:---:|:---:|
| stocks | 39 | 0 |
| users | 35 | 3 |
| news | ~31 | 3 |
| macro (market_pulse v1) | 10 | 0 |
| rag_analysis | 15 | 3 |
| serverless | ~64 | 7 |
| thesis | ~28 | 0 (router 기반) |
| validation | 6 | 0 |
| chainsight | 18 | 8 |
| sec_pipeline | 2 | 0 |
| **소계** | **≈ 248** | **24** |

---

## 3. 커버리지 개선 작업 목록

> **정정**: drf-spectacular는 이미 설치·설정·서빙 중이므로 "설치/설정"은 **불필요**. 아래는 **정확한 스키마 노출을 위한 점진적 작업**이다.

### 3.1 (이미 완료된 항목 — 작업 불요)
- [x] drf-spectacular + sidecar 설치 (`pyproject.toml`)
- [x] `DEFAULT_SCHEMA_CLASS` 전역 설정
- [x] `/api/v2/schema/` `/swagger/` `/redoc/` URL 등록
- [x] `SPECTACULAR_SETTINGS` 기본 구성 + enum collision 4건 처리
- [x] 핵심 4영역 전수 문서화: market_pulse v2(5/5), api_request admin(6/6), chainsight(8), portfolio coach(7)

### 3.2 설정 개선 (소규모, 1차 권장)
| 작업 | 대상 | 예상 |
|------|------|:---:|
| `TITLE`/`DESCRIPTION`을 플랫폼 전체로 확장 (현재 "Market Pulse v2"로 협소) | `config/settings.py` SPECTACULAR_SETTINGS | 0.5h |
| `TAGS`에 앱별 그룹(stocks·users·rag·thesis·validation 등) 추가 → Swagger 그룹핑 | 동일 | 1h |
| 점진 문서화 중 임시로 `DISABLE_ERRORS_AND_WARNINGS=False`로 켜고 누락 경고 수집 → 우선순위 산출 | 동일(검증용, 운영 토글 유지) | 0.5h |

### 3.3 `@extend_schema` 추가 범위 (본 작업의 대부분)

graceful fallback 상태인 **약 224개 엔드포인트**가 대상. ROI 순 우선순위:

| 우선순위 | 앱 | 미문서화 수(추정) | 권장 데코레이터 | 비고 |
|:---:|----|:---:|------|------|
| **P1** | **users** | ~32 | `@extend_schema(request=, responses=)` + 시리얼라이저 명시 | JWT/포트폴리오/Watchlist — 외부·FE 계약 핵심 |
| **P1** | **stocks** | 39 | 응답 스키마 + `OpenApiParameter`(symbol path, period query) | 8개 view 모듈, FE 의존도 최상 |
| **P2** | **rag_analysis** | ~12 | responses + SSE(`ChatStreamView`)는 text/event-stream 명시 | 스트리밍 응답 특수 처리 필요 |
| **P2** | **thesis** | ~28 | `@extend_schema_view`로 ViewSet 액션별 + nested router 파라미터 | ViewSet·nested router라 액션 단위 분해 필요 |
| **P2** | **serverless** | ~57 | 함수형 view → `@extend_schema(responses=)` 개별 | 양 많음(64). Admin/공개 분리하여 단계 적용 |
| **P3** | **news** | ~28 | `@extend_schema_view` + 30개 `@action` 개별 응답 | ViewSet 액션 30개, url_path 정규식 파라미터 다수 |
| **P3** | **validation** | 6 | responses + symbol path param | 소규모, 빠른 완수 가능 |
| **P3** | **macro** | 10 | responses | 소규모 |
| **P3** | **sec_pipeline** | 2 | responses + filing symbol param | 소규모 |
| **P3** | **chainsight 잔여** | ~10 | WatchlistViewSet 액션 5건 등 | 일부만 적용됨(8) |

### 3.4 예상 작업량 (요약)

| 구간 | 엔드포인트 | 예상 시간 |
|------|:---:|:---:|
| 설정 개선 (§3.2) | — | ~2h |
| P1 (users·stocks) | ~71 | 8~12h (시리얼라이저 정의 필요분 포함) |
| P2 (rag·thesis·serverless) | ~97 | 12~18h |
| P3 (news·validation·macro·sec·chainsight 잔여) | ~56 | 6~10h |
| **합계** | **~224** | **약 28~42h** (1인 기준 4~6일) |

**작업 가속 요인**:
- 다수 view가 이미 DRF Serializer를 보유 → `responses=XxxSerializer`만 연결하면 자동 추론
- `@extend_schema_view`로 ViewSet 일괄 처리 가능(thesis·news·chainsight)
- 함수형 view(serverless·portfolio)는 inline serializer 또는 `OpenApiResponse` 명시 필요(추론 불가) → 가장 손이 많이 감

**리스크**:
- `DISABLE_ERRORS_AND_WARNINGS=True` 상태에서는 스키마가 **조용히 부정확**할 수 있음 — FE가 fallback string body를 신뢰하면 계약 불일치 위험. 점진 작업 중 경고를 주기적으로 켜서 검증 권장.
- `contracts/` (하네스 계약 폴더)와 spectacular 스펙의 **이중 소스** 가능성 — 둘의 정합성 별도 확인 필요(본 감사 범위 밖).

---

## 부록 A. 감사 방법

```bash
# 1. urls.py 전수 탐색
find . -name 'urls.py' -not -path '*migrations*' -not -path '*__pycache__*' -not -path '*/node_modules/*'

# 2. 문서화 패키지 확인
grep -iEn 'spectacular|yasg|swagger|openapi' pyproject.toml poetry.lock

# 3. 전역 설정
grep -n 'DEFAULT_SCHEMA_CLASS' config/settings.py        # :370
sed -n '/SPECTACULAR_SETTINGS/,/^}/p' config/settings.py

# 4. @extend_schema 커버리지
grep -rl 'extend_schema' --include=*.py .                # 13 files
```

## 부록 B. 미확정/주의 사항
- `news`(30 action)·`thesis`(3 ViewSet)·`chainsight`(WatchlistViewSet) 엔드포인트 수는 라우터 전개 **추정치**. 정확한 수는 `python manage.py spectacular --file schema.yml` 생성 후 path 카운트로 확정 가능(본 감사는 읽기 전용이라 미실행).
- `serverless` 64건은 admin 전용(인증 필요)과 공개 API가 혼재 — 문서 분리(TAG 또는 별도 스키마) 검토 권장.
