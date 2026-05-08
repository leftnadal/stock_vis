# API 문서 감사 보고서

- 감사 일자: 2026-05-08
- 대상 브랜치: portfolio
- 대상 디렉토리: `/Users/byeongjinjeong/Desktop/stock_vis`
- 모드: 읽기 전용 (코드 변경 없음)

> **주요 변경 (vs 5월 7일 보고서)**: `drf-spectacular`가 설치·등록되어 **자동 OpenAPI 스펙 생성이 가능한 상태**로 전환됨. 단, Swagger UI 노출은 `/api/v2/`에 한정. v1 엔드포인트는 SCHEMA_PATH_PREFIX 매칭으로 스펙엔 포함되나 `@extend_schema`가 없는 view는 graceful fallback(string body)으로 노출.

---

## 현재 상태

### OpenAPI/Swagger 문서화 도구 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | ✅ 설치 (^0.29.0) | `pyproject.toml:38` |
| `drf-spectacular-sidecar` | ✅ 설치 (^2026.4.14) | `pyproject.toml:39` (정적 자산 SIDECAR) |
| `drf-yasg` | ❌ 미설치 | grep 0건 |
| `INSTALLED_APPS` 등록 | ✅ 등록 | `config/settings.py:205-206` (`drf_spectacular`, `drf_spectacular_sidecar`) |
| `DEFAULT_SCHEMA_CLASS` | ✅ 설정 | `config/settings.py:361` (`drf_spectacular.openapi.AutoSchema`) |
| `SPECTACULAR_SETTINGS` | ✅ 설정 | `config/settings.py:365-413` (TITLE: Market Pulse v2 중심) |
| 자동 스펙 엔드포인트 | ⚠️ v2만 노출 | `config/urls.py:58-68` (`/api/v2/schema/`, `/api/v2/swagger/`, `/api/v2/redoc/`) |
| SCHEMA_PATH_PREFIX | `/api/v[12]` | v1·v2 둘 다 스펙 포함 (`config/settings.py:377`) |
| 경고 억제 플래그 | `DISABLE_ERRORS_AND_WARNINGS: True` | v1 미문서화 view는 graceful fallback (`config/settings.py:385`) |

### `@extend_schema` 적용 현황 (코드 base 기준)

총 **31 회** 사용, 분포 12개 파일:

| 파일 | 횟수 | 비고 |
|------|----:|------|
| `chainsight/api/views.py` | 7 | 클래스 단위 데코레이션 (Chain Sight 명시 7개 거의 전부) |
| `serverless/views.py` | 6 | `movers`, `presets`(GET/POST), `alerts`(GET/POST), `thesis_list` |
| `api_request/admin_views.py` | 5 | Provider Admin 5개 모두 적용 |
| `marketpulse/api/views/*.py` | 5 | overview / cards / news_refresh / i18n / health 각 1회 |
| `rag_analysis/views.py` | 2 | `baskets list`, `sessions list` operation_id만 |
| `news/api/views.py` | 2 | (전체 32 중 2 — 30개 `@action` 미적용) |
| `users/views.py` | 2 | (전체 35 중 2) |
| `config/settings.py` | 2 | 주석 |

> **추정 자동 인식률**: ViewSet/APIView+Serializer 기반은 데코레이터 없이도 파라미터/응답 일부가 추론됨. 그러나 `@action` 메서드, SSE, 비표준 dict 응답은 graceful fallback으로 string body 처리됨 → 정확도 부족.

### 결론

- **자동 OpenAPI 스펙 생성 인프라는 갖춰져 있다.** 다만 현재 SPECTACULAR_SETTINGS는 Market Pulse v2를 1차 대상으로 설계되어 있고, v1은 graceful fallback에 의존하는 부분 적용 상태다.
- 추가로 필요한 작업은 ❶ v1 Swagger UI 별도 노출(또는 통합), ❷ `@action`·SSE 등 부정확한 영역의 `@extend_schema` 보강, ❸ TAGS 분류 확장이다.
- DRF ViewSet/APIView 기반이라 점진적 보강에 유리.

---

## 엔드포인트 목록 (앱별 테이블)

### 집계 요약

| 앱 | URL 프리픽스 | 패턴 수 | `@extend_schema` 적용 | 비고 |
|----|--------------|--------:|:--------------------:|------|
| stocks | `/api/v1/stocks/` | 39 | 0 | APIView 기반, ViewSet 없음 |
| users | `/api/v1/users/` | 35 | 2 | JWT 7 + 세션 6 + Favorites 3 + Portfolio 9 + Interests 2 + Watchlist 8 |
| news | `/api/v1/news/` | 32 | 2 | `NewsViewSet` (ReadOnlyModelViewSet) — 표준 2 + `@action` 30 |
| macro | `/api/v1/macro/` | 10 | 0 | Pulse + 개별 지표 + 동기화 |
| rag_analysis | `/api/v1/rag/` | 15 | 2 | DataBasket 6 + Session 4 + Monitoring 5 |
| serverless | `/api/v1/serverless/` | 64 | 6 | Admin 12 + Movers/Keywords 8 + Breadth 3 + Heatmap 3 + Presets 7 + Filter 2 + Alerts 6 + Thesis(legacy) 4 + ETF/LLM/Institutional/Regulatory/Patent 18 + Health 1 |
| thesis | `/api/v1/thesis/` | 26 | 0 | Conversation 4 + Monitoring 2 + Alert 2 + 3개 ViewSet (Thesis 6 + Premise 6 + Indicator 6) |
| validation | `/api/v1/validation/` | 6 | 0 | Symbol 기반 6개 |
| chainsight | `/api/v1/chainsight/` | 16 | 7 | 명시 7 (모두 데코) + `WatchlistViewSet` 9 (표준 4 + `@action` 5) |
| sec_pipeline | `/api/v1/sec-pipeline/` | 2 | 0 | Dashboard + Filing |
| api_request | `/api/v1/` | 6 | 5 | Provider Admin 5(전부 데코) + Health 1 |
| portfolio | `/api/` | **5** | 0 | Coach E1/GARP, E5/Adjustment, E2/Diagnostic, E6/Comparison, **E3/Metric-Comment (신규)** |
| marketpulse v2 | `/api/v2/market-pulse/` | **5** | 5 | overview / cards/<id>/detail / news/refresh / i18n / health (전부 데코) |
| v2 schema | `/api/v2/` | **3** | n/a | `schema/`, `swagger/`, `redoc/` (drf-spectacular 노출) |
| config (root) | `/` | 3 | 0 | `/`, `/health/`, `/admin/` |
| **합계** | | **267** | **29\*** | (config root 3 포함) |

\* 31회 중 `config/settings.py` 주석 2개 제외한 실 적용 29건. ViewSet 라우터의 표준 액션(list/create/retrieve/update/partial_update/destroy)과 `@action` 데코레이터를 합산.

> **변경분 (5월 7일 대비)**: portfolio +3 (E2/E6/E3 신규), marketpulse v2 +5 (신규 앱), v2 schema +3 (Swagger UI 노출). 합계 256 → **267**.

---

### stocks (39개) — `/api/v1/stocks/`

| 그룹 | 경로 | View 클래스 |
|------|------|-------------|
| Web | `''`, `stock/<symbol>/`, `search/` | `DashboardView`, `StockDetailView`, `StockSearchAPIView` |
| API tab | `api/chart/<symbol>/`, `api/overview/<symbol>/`, `api/balance-sheet/<symbol>/`, `api/income-statement/<symbol>/`, `api/cashflow/<symbol>/` | `Stock*APIView` 5개 |
| Sync | `api/sync/<symbol>/` | `StockSyncAPIView` |
| MVP | `api/mvp/stocks/`, `api/mvp/stock/<symbol>/`, `api/mvp/rag/<symbol>/`, `api/mvp/sectors/` | 4개 |
| Indicator | `api/indicators/<symbol>/`, `api/signal/<symbol>/`, `api/indicators/compare/` | 3개 |
| Search | `api/search/symbols/`, `api/search/validate/<symbol>/`, `api/search/popular/` | 3개 |
| Movers | `api/market-movers/` | 1개 |
| Fundamental | `api/fundamentals/{key-metrics, ratios, dcf, rating, all}/<symbol>/` | 5개 |
| Screener | `api/screener/{,, large-cap/, high-dividend/, sector/<>, low-beta/, exchange/<>}` | 6개 |
| Quote | `api/quotes/{index/, <symbol>/, batch/, major-indices/, sector-performance/}` | 5개 |
| EOD | `eod/dashboard/`, `eod/signal/<signal_id>/`, `eod/pipeline/status/` | 3개 |

### users (35개) — `/api/v1/users/`

| 그룹 | 경로 |
|------|------|
| JWT | `jwt/{signup, login, logout, refresh, verify, change-password, profile}/` |
| Session | `me/`, `''`, `@<user_name>/`, `change_password/`, `login/`, `logout/` |
| Favorites | `favorites/`, `favorites/add/<stock_id>/`, `favorites/remove/<stock_id>/` |
| Portfolio | `portfolio/`, `portfolio/summary/`, `portfolio/table/`, `portfolio/refresh/`, `portfolio/<pk>/`, `portfolio/<pk>/quick-update/`, `portfolio/symbol/<symbol>/`, `portfolio/symbol/<symbol>/refresh/`, `portfolio/symbol/<symbol>/status/` |
| Interests | `interests/`, `interests/<pk>/` |
| Watchlist | `watchlist/`, `watchlist/<pk>/`, `watchlist/<pk>/{add-stock, bulk-add, bulk-remove, stocks}/`, `watchlist/<pk>/stocks/<symbol>/`, `watchlist/<pk>/stocks/<symbol>/remove/` |

### news (32개) — `/api/v1/news/`

- `NewsViewSet(ReadOnlyModelViewSet)` 표준: `GET /` (list), `GET /<pk>/` (retrieve) — 2개
- 커스텀 `@action` 30개 (`@action\(` grep 30건):

| 카테고리 | url_path |
|----------|----------|
| Stock 관련 | `stock/<symbol>`, `stock/<symbol>/sentiment` |
| 키워드 | `daily-keywords`, `daily-keywords/generate`, `keyword-detail` |
| 사용자 피드 | `market-feed`, `interest-options`, `personalized-feed` |
| News Events | `news-events`, `news-events/impact-map` |
| ML 모니터링 | `ml-status`, `ml-shadow-report`, `ml-weekly-report`, `ml-lightgbm-readiness`, `ml-trend`, `ml-rollback-preview`, `ml-rollback` |
| 운영 모니터링 | `collection-logs`, `pipeline-health`, `llm-usage`, `task-timeline`, `neo4j-status`, `alerts`, `alerts/<alert_pk>/resolve` |
| 기타 (default) | 6개 추가 액션 |

### macro (10개) — `/api/v1/macro/`

`pulse/`, `fear-greed/`, `interest-rates/`, `inflation/`, `global-markets/`, `calendar/`, `vix/`, `sectors/`, `sync/`, `sync/status/`

### rag_analysis (15개) — `/api/v1/rag/`

| 그룹 | 경로 |
|------|------|
| DataBasket | `baskets/`, `baskets/<pk>/`, `baskets/<pk>/add-item/`, `baskets/<pk>/add-stock-data/`, `baskets/<pk>/items/<item_id>/`, `baskets/<pk>/clear/` |
| Session | `sessions/`, `sessions/<pk>/`, `sessions/<pk>/messages/`, `sessions/<pk>/chat/stream/` (SSE) |
| Monitoring | `monitoring/usage/`, `monitoring/cost/`, `monitoring/cache/`, `monitoring/history/`, `monitoring/pricing/` |

### serverless (64개) — `/api/v1/serverless/`

| 카테고리 | 개수 | `@extend_schema` |
|---------|----:|:----:|
| Admin Dashboard | 12 | 0 |
| Market Movers | 2 | 1 (`movers`) |
| Sync | 2 | 0 |
| Keywords | 4 | 0 |
| Market Breadth | 3 | 0 |
| Sector Heatmap | 3 | 0 |
| Screener Presets | 7 | 2 (GET/POST) |
| Screener Filters/Adv | 2 | 0 |
| Screener Alerts | 6 | 2 (GET/POST) |
| Investment Thesis (legacy) | 4 | 1 (list) |
| Chain Sight ETF | 9 | 0 |
| LLM Relations | 4 | 0 |
| Institutional 13F | 3 | 0 |
| Regulatory + Patent | 2 | 0 |
| Health | 1 | 0 |

### thesis (26개) — `/api/v1/thesis/`

| 그룹 | 경로/액션 |
|------|----------|
| Conversation | `conversation/{start, respond, news-issues, suggest}/` |
| Monitoring | `<thesis_id>/dashboard/`, `<thesis_id>/indicators/<indicator_id>/readings/` |
| Alerts | `alerts/`, `alerts/<aid>/read/` |
| `ThesisViewSet` (`http_method_names=['get','post','patch']`) | 표준 4 + `@action` 2 = 6 |
| `ThesisPremiseViewSet` (nested) | 표준 6 |
| `ThesisIndicatorViewSet` (nested) | 표준 6 |

### validation (6개) — `/api/v1/validation/`

`<symbol>/{summary, metrics, leader-comparison, presets, peer-preference, llm-filter}/`

### chainsight (16개) — `/api/v1/chainsight/`

| 그룹 | 경로 | `@extend_schema` |
|------|------|:----:|
| 명시 경로 (7) | `seeds/`, `sector/<sector>/graph/`, `signals/`, `trace/`, `<symbol>/{neighbors, graph, suggestions}/` | 7 (전부) |
| `WatchlistViewSet` (`http_method_names=['get','post','delete']`) | 표준 4 (list/create/retrieve/destroy) + `@action` 5 = 9 | 0 |

### sec_pipeline (2개) — `/api/v1/sec-pipeline/`

`admin/dashboard/`, `filing/<symbol>/`

### api_request (6개) — `/api/v1/`

`health/`, `admin/providers/{status, rate-limits, cache, test, config}/` (admin 5개 모두 데코)

### portfolio (5개) — `/api/`

`coach/e1/garp/`, `coach/e5/adjustment/`, `coach/e2/diagnostic-card/`, `coach/e6/comparison/`, `coach/e3/metric-comment/`

> **신규 추가 (5월 7일 → 8일)**: E3/Metric-Comment (commit `72875c7` slice5 Step 3).

### marketpulse v2 (5개) — `/api/v2/market-pulse/`

`overview`, `cards/<card_id>/detail`, `news/refresh`, `i18n`, `health` — 전부 `@extend_schema` 적용 + `Market Pulse v2` 단일 태그.

### v2 schema (3개) — `/api/v2/`

`schema/` (OpenAPI YAML), `swagger/` (Swagger UI), `redoc/` (ReDoc) — drf-spectacular 자동 제공.

### config root (3개)

`/` (api_root), `/health/`, `/admin/`

---

## 도입 작업 목록

> **현재 Step 1 완료 상태**. 남은 작업은 v1 적용 확장 + 운영 보강.

### Step 1. 설치 + 기본 설정 (완료 ✅)

- `drf-spectacular = "^0.29.0"`, `drf-spectacular-sidecar = "^2026.4.14"` 추가됨
- `INSTALLED_APPS`, `DEFAULT_SCHEMA_CLASS`, `SPECTACULAR_SETTINGS` 모두 설정 완료
- `/api/v2/schema|swagger|redoc/` 경로 노출됨

### Step 2. 1차 스펙 검증 + 경고 분석 (S, ½일)

- 명령: `python manage.py spectacular --file /tmp/openapi.yml --validate`
- 현재 `DISABLE_ERRORS_AND_WARNINGS=True`로 경고가 무시됨 → **임시로 False로 토글하여 W001/W002 목록 수집** 후 우선순위화
- 적용된 `ENUM_NAME_OVERRIDES` 4건 외 추가 충돌 가능 enum 식별

### Step 3. v1 Swagger UI 노출 결정 (S, 0.1일)

현재 `/api/v2/swagger/`만 존재. 두 가지 선택지:

| 옵션 | 장점 | 단점 |
|------|------|------|
| A. `/api/v1/swagger/` 별도 노출 (스펙도 v1 only) | 버전 분리 명확 | 스펙 2개 유지 부담 |
| B. 단일 `/api/swagger/`에 v1+v2 통합 (현재 SCHEMA_PATH_PREFIX 그대로) | 통합 뷰 | TAGS 분류 필수 |

권장: **B + TAGS 14개로 그룹** (Step 5 참조).

### Step 4. `@extend_schema` 데코레이터 추가 (M~L)

총 **267개** 엔드포인트 중 우선순위:

| 우선순위 | 대상 | 개수 | 이유 | 예상 시간 |
|---------|------|----:|------|----------|
| P0 | `@action` 메서드 (news 30 + thesis 2 + chainsight 5) | 37 | 라우터 자동 검출 한계, request/response 명시 필수 | 2~3일 |
| P0 | SSE/스트리밍 (`rag_analysis/sessions/<pk>/chat/stream/`) | 1 | 비표준 응답, 수동 명시 필수 | 0.5일 |
| P0 | EOD/sync admin (`stocks/eod/*` 3, `*/sync/*` 다수) | ~8 | dict 응답 + 실행 트리거 부수효과 | 0.5일 |
| P1 | symbol 파라미터 사용 APIView (stocks 24 + validation 6 + chainsight 명시는 완료) | ~30 | `OpenApiParameter('symbol', ..., description='upper-case symbol')` 일관 적용 | 1.5일 |
| P1 | JWT/인증 엔드포인트 (users JWT 7) | 7 | 보안 스킴 명시(`security=[{'jwtAuth': []}]`), 401 응답 스키마 | 0.5일 |
| P1 | 운영 admin 잔여 (serverless admin 12 + sec_pipeline admin 1) | 13 | `IsAdminUser` 권한 표기 | 1일 |
| P1 | thesis ViewSet 3개 (Thesis/Premise/Indicator) | 18 | 중첩 라우터 + 비표준 액션 응답 명세 | 1일 |
| P2 | portfolio coach 5 + macro 10 + 일반 ListCreate (rag, validation 등) | ~70 | Serializer 추론 + 응답 examples 보강 | 2~3일 |
| P3 | Legacy/제거 예정 (serverless thesis 4, ETF Phase 3 등) | ~13 | `@extend_schema(exclude=True)` 또는 deprecation 표기 | 0.5일 |

**합계 예상**: P0~P2 핵심 작업 **9~11일** (1.5~2주, 1인 기준).

### Step 5. 태그/그룹/네임스페이스 정리 (S, 1일)

현재 TAGS는 `Market Pulse v2` 1개. v1 통합 노출 시 14개로 확장 권장:

```
['Stocks', 'Users/Auth', 'Users/Watchlist', 'Users/Portfolio',
 'News', 'Macro', 'RAG', 'Serverless/Admin', 'Serverless/Movers',
 'Serverless/Screener', 'Thesis', 'Validation', 'ChainSight',
 'SEC Pipeline', 'Provider Admin', 'Portfolio Coach', 'Market Pulse v2']
```

- `serverless`(64개)는 단일 태그가 너무 비대 → 카테고리별 4~5 태그로 세분 권장.
- `chainsight/api/views.py`는 이미 `tags=['Chain Sight']`로 통일되어 있음 → 표준 모범 사례.

### Step 6. CI/배포 통합 (S, ½일)

- `python manage.py spectacular --file contracts/openapi.yml --validate` 를 pre-commit 또는 CI에 추가
- CLAUDE.md `Contract-Driven Development` 절과 연결: 생성된 `openapi.yml`을 `contracts/`의 진실의 소스로 채택
- `ENUM_NAME_OVERRIDES`는 신규 모델 choices 추가 시 동기화 누락 위험 → CI에서 `--validate` 실패로 잡히도록 설정

### Step 7. 운영/보안 (S, 0.5일)

- 운영 환경에서 Swagger/Redoc UI 노출 정책 결정 (예: `IsAdminUser` 또는 IP 화이트리스트)
- `SPECTACULAR_SETTINGS['SERVE_PERMISSIONS']` 설정 (현재 미지정 → 기본 `AllowAny`)
- `DISABLE_ERRORS_AND_WARNINGS: True` 운영 사용은 의도된 상태이지만 CI에서는 False로 토글하여 회귀 감지 권장

---

### 종합 예상 작업량 (남은 분)

| 단계 | 작업 | 인일(man-day) |
|------|------|-------------:|
| Step 1 | 설치 + 기본 설정 | **완료** ✅ |
| Step 2 | 1차 스펙 + 경고 분석 | 0.5 |
| Step 3 | v1 Swagger UI 노출 결정 | 0.1 |
| Step 4 | `@extend_schema` 데코레이터 추가 (P0~P2) | 9~11 |
| Step 5 | 태그/그룹 정리 | 1 |
| Step 6 | CI/contracts 통합 | 0.5 |
| Step 7 | 운영/보안 | 0.5 |
| **잔여 합계** | | **11.6~13.6 인일 (약 2~2.5주)** |

### 리스크 / 주의사항

1. **`DISABLE_ERRORS_AND_WARNINGS=True`**가 설정되어 v1 영역의 추론 실패가 silent — Step 4 진행 중 회귀를 잡으려면 **CI 한정**으로 False 토글 권장.
2. **`@action` 메서드 (news 30 + thesis 2 + chainsight 5)**: 자동 추론으로 응답 스키마가 부정확할 가능성이 높다 → P0.
3. **SSE 스트리밍** (`rag_analysis/sessions/<pk>/chat/stream/`)는 `@extend_schema(responses=OpenApiTypes.STR)` 또는 별도 명시.
4. **Legacy 경로 (Chain Sight Phase 3 ETF, serverless thesis)**는 문서화 시 혼란 야기 가능 → `exclude=True` 또는 deprecation 표기.
5. **`/api/` (portfolio) vs `/api/v1/` vs `/api/v2/` 혼재** — `SCHEMA_PATH_PREFIX=/api/v[12]`는 `portfolio`(`/api/`)를 **누락**시킴 → portfolio 5개는 현재 스펙에 포함 안 됨. 별도 prefix 추가 또는 portfolio URL을 `/api/v1/portfolio/`로 정렬 필요.
6. **Symbol upper 규칙** (`symbol.upper()`): OpenAPI에는 표현되지 않는 비즈니스 규칙 → 설명(description) 또는 examples로 보완.
7. **인증 스킴 혼재**: `SimpleJWT` + 세션(쿠키) 동시 사용 → `SECURITY` 정의 시 두 스킴 모두 등록.
8. **`ENUM_NAME_OVERRIDES` 동기화**: 모델 choices 변경 시 settings.py도 업데이트 필요. CI에서 sanity check 권장.

---

## 부록: 데이터 산출 방법

| 항목 | 방법 |
|------|------|
| 의존성 | `pyproject.toml` 직접 read |
| `INSTALLED_APPS`, REST_FRAMEWORK, SPECTACULAR | `config/settings.py` 직접 read (line 200~415) |
| 엔드포인트 | 14개 `urls.py` 수동 read + 라우터 표준 액션 + `@action` grep |
| ViewSet 베이스 | `class .*ViewSet` grep, `http_method_names` grep으로 액션 수 산정 |
| `@extend_schema` 적용 횟수 | `Grep "@extend_schema"` 31건, `config/settings.py` 주석 2건 제외 → 29건 적용 |

> 본 보고서는 코드 변경 없이 정적 분석만으로 작성되었음.
