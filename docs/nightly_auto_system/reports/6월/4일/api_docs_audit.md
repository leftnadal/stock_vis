# API 문서 감사 보고서

> 작성일: 2026-06-04 | 모드: **읽기 전용 감사 (코드 무수정)** | 대상: `/Users/byeongjinjeong/Desktop/stock_vis`
> 검증 방법: `urls.py` 정적 분석 + `manage.py spectacular` 실제 스키마 생성 + 스키마 메타데이터 분석

---

## 핵심 결론 (TL;DR)

**API 문서화는 "도입 필요" 상태가 아니라 "이미 도입·운영 중, 품질 개선 단계"이다.**

- ✅ `drf-spectacular 0.29.0` + `drf-spectacular-sidecar` **설치·설정·URL 등록 완료**
- ✅ OpenAPI 스키마 **실제 생성 성공** — 249 paths / 292 operations / 219 KB / **에러 0건**
- ✅ Swagger UI(`/api/v2/swagger/`) · ReDoc(`/api/v2/redoc/`) · Schema(`/api/v2/schema/`) 운영 중
- ⚠️ 단, **품질은 불균일** — 명시적 `@extend_schema` 적용은 일부 영역(13개 파일)에만, 나머지는 graceful fallback(string body)
- ⚠️ `DISABLE_ERRORS_AND_WARNINGS = True`로 **스키마 경고를 의도적으로 숨김** → fallback 누락이 보이지 않음
- ⚠️ `summary` 보유 operation은 292개 중 **12개(4%)**, tag 일관성 결함(`Chain Sight` vs `chainsight` 이중 분류)

➡️ 따라서 본 보고서의 "도입 작업 목록"은 **신규 설치가 아니라 기존 스키마의 정확도·가독성 보강 작업**으로 정의한다.

---

## 현재 상태

### 1. 라이브러리 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | ✅ 설치 (`^0.29.0`) | `pyproject.toml` |
| `drf-spectacular-sidecar` | ✅ 설치 (`^2026.4.14`) | `pyproject.toml` (정적 자산 self-host) |
| `drf-yasg` (대안) | ❌ 미사용 | requirements/pyproject 미검출 |
| `INSTALLED_APPS` 등록 | ✅ | `config/settings.py:212-213` |
| `DEFAULT_SCHEMA_CLASS` | ✅ `drf_spectacular.openapi.AutoSchema` | `config/settings.py:370` |

### 2. Swagger/OpenAPI 자동 생성 가능 여부

**가능 — 실측 검증 완료.**

```
$ python manage.py spectacular --file /tmp/schema_audit.yml
exit: 0   (에러 0건, 경고 출력 없음)
→ 249 paths / 292 operations / 219,629 bytes
```

| 엔드포인트 | 경로 | 비고 |
|-----------|------|------|
| OpenAPI 스키마 | `GET /api/v2/schema/` | `SpectacularAPIView` (`config/urls.py:62`) |
| Swagger UI | `GET /api/v2/swagger/` | `SpectacularSwaggerView` |
| ReDoc | `GET /api/v2/redoc/` | `SpectacularRedocView` |

**`SPECTACULAR_SETTINGS` 주요 구성** (`config/settings.py:377-`):

- `TITLE`: "Stock-Vis Market Pulse v2 API" — ⚠️ **Market Pulse v2 중심 명칭**이나 실제로는 전체 API(249 paths)를 노출 (제목과 범위 불일치)
- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` — v1·v2 모두 스키마에 포함
- `SWAGGER_UI_DIST = 'SIDECAR'` / `REDOC_DIST = 'SIDECAR'` — 정적 자산 self-host (CDN 비의존)
- `COMPONENT_SPLIT_REQUEST = True` — 요청/응답 컴포넌트 분리
- `DISABLE_ERRORS_AND_WARNINGS = True` — ⚠️ **fallback noise 억제용**. 스키마 누락·추론 실패가 콘솔에 안 뜸 → 품질 저하를 조용히 숨기는 리스크
- `ENUM_NAME_OVERRIDES`: 4종 enum collision 수동 해결 (thesis category/status, news category, savedpath status)

### 3. 명시적 `@extend_schema` 적용 현황

전체 292 operation 중 명시적 데코레이터로 정밀 문서화된 view는 **13개 파일에 한정**:

| 영역 | 파일 | `@extend_schema` 적용 |
|------|------|---------------------|
| Provider Admin | `packages/shared/api_request/admin_views.py` | 5곳 (responses 명시) |
| Users | `packages/shared/users/views.py` | 2곳 (operation_id) |
| Chain Sight | `apps/chain_sight/api/views.py` | 7곳 (tags=["Chain Sight"]) |
| Portfolio Coach | `apps/portfolio/api/views.py` | 6곳 (e1~e6) |
| Market Pulse v2 | `apps/market_pulse/api/views/*.py` | 5곳 (health/cards/overview/i18n/news_refresh) |
| RAG | `services/rag_analysis/views.py` | 2곳 (operation_id) |
| Serverless | `services/serverless/views.py` | 6곳 (operation_id, methods 분리) |
| News | `services/news/api/views.py` | 2곳 (parameters/PATH) |

**나머지 ~250 operation은 AutoSchema가 docstring·serializer 추론으로 자동 생성** → 일부는 정확하나, serializer가 없는 함수형 view/수동 Response view는 `string` body fallback으로 노출됨(스키마는 생성되나 응답 구조 불명확).

**품질 지표:**

| 지표 | 값 | 평가 |
|------|-----|------|
| 총 operation 수 | 292 | — |
| `summary` 보유 | 12 (4%) | ⚠️ 매우 낮음 — Swagger 목록 가독성 저하 |
| `operation_id` 명시(extend_schema) | 141 검출 | 자동 생성 ID와 혼재 |
| tag 일관성 | `Chain Sight`(7) + `chainsight`(9) 분리 | ⚠️ 동일 앱 이중 분류 |

---

## 엔드포인트 목록 (앱별 테이블)

> **URL 패턴 수** = `urls.py`의 `path()`/router 등록 단위(라우트), **스키마 operation 수** = HTTP 메서드 단위(GET/POST 분리, ViewSet 확장 포함). ViewSet은 1 router 등록 → 다수 operation으로 확장됨.

| # | 앱 | config prefix | urls.py 경로 | URL 패턴(path) | router(ViewSet) | 스키마 operation* |
|---|-----|--------------|-------------|:-:|:-:|:-:|
| 1 | **stocks** | `/api/v1/stocks/` | `packages/shared/stocks/urls.py` | 39 | 0 | 38 |
| 2 | **users** | `/api/v1/users/` | `packages/shared/users/urls.py` | 35 | 0 | 48 |
| 3 | **serverless** | `/api/v1/serverless/` | `services/serverless/urls.py` | 64 | 0 | 73 |
| 4 | **news** | `/api/v1/news/` | `services/news/api/urls.py` | 1 | 1 (NewsArticleViewSet) | 32 |
| 5 | **thesis** | `/api/v1/thesis/` | `thesis/urls.py` | 11 | 3 (Thesis/Premise/Indicator) | 26 |
| 6 | **rag_analysis** | `/api/v1/rag/` | `services/rag_analysis/urls.py` | 15 | 0 | 20 |
| 7 | **macro (market_pulse v1)** | `/api/v1/macro/` | `apps/market_pulse/urls.py` | 10 | 0 | 10 |
| 8 | **chainsight** | `/api/v1/chainsight/` | `apps/chain_sight/api/urls.py` | 7 | 1 (WatchlistViewSet) | 9 + 7(별도 tag) |
| 9 | **validation** | `/api/v1/validation/` | `services/validation/api/urls.py` | 6 | 0 | 7 |
| 10 | **api_request (Provider Admin)** | `/api/v1/` | `packages/shared/api_request/urls.py` | 6 | 0 | 7 (admin) |
| 11 | **portfolio coach** | `/api/v1/` | `apps/portfolio/api/urls.py` | 6 (coach e1~e6) | 0 | 6 |
| 12 | **market_pulse v2** | `/api/v2/market-pulse/` | `apps/market_pulse/api/urls.py` | 5 | 0 | 5 |
| 13 | **sec_pipeline** | `/api/v1/sec-pipeline/` | `services/sec_pipeline/urls.py` | 2 | 0 | 1 (DRF만) |
| 14 | **iron_trading** | `/api/v1/iron-trading/` | `integrations/iron_trading/urls.py` | 2 | 0 | 2 |
| 15 | **portfolio (legacy)** | `/api/` | `apps/portfolio/urls.py` | 0 (빈 패턴) | 0 | 0 |
| | **합계** | | | **209 path** | **5 router** | **≈292 operation** |

\* 스키마 operation 수는 `manage.py spectacular` 실제 생성 산출물의 tag별 집계 기준.

### 사용자 지정 10개 앱 엔드포인트 수 (요청 항목)

| 앱 | URL 패턴 | 스키마 operation |
|-----|:-:|:-:|
| stocks | 39 | 38 |
| users | 35 | 48 |
| news | 2 (1 path + 1 ViewSet) | 32 |
| macro | 10 | 10 |
| rag_analysis | 15 | 20 |
| serverless | 64 | 73 |
| thesis | 14 (11 path + 3 ViewSet) | 26 |
| validation | 6 | 7 |
| chainsight | 8 (7 path + 1 ViewSet) | 16 |
| sec_pipeline | 2 | 1 |

### 주요 관찰

- **serverless(64 path / 73 op)** 가 최대 규모 — Market Movers + Screener + Chain Sight + 키워드가 단일 앱에 집중. 문서화 우선순위 최상위.
- **users(48 op > 35 path)**, **news(32 op)** 는 ViewSet 확장으로 operation이 path보다 많음.
- **sec_pipeline** 은 2 path 중 `admin/dashboard/`가 순수 Django 함수형 view(템플릿 추정)로 DRF 스키마 1건만 노출.
- **portfolio/urls.py** 는 `urlpatterns = []` 빈 상태 — Slice 13 #65에서 legacy view 제거 후 `config/urls.py:52`의 include만 잔존(향후 제거 검토 대상으로 코드 주석에 명시됨).
- **버전 혼재**: v1(대부분) + v2(market-pulse만). 스키마 제목은 "Market Pulse v2"지만 v1 전체를 포함 → 명칭·범위 불일치.

---

## 도입 작업 목록

> **전제**: 신규 설치 불필요(완료됨). 아래는 **기존 스키마 정확도·가독성 보강** 작업이다. 우선순위 P0(즉시 가치) → P2(선택).

### P0 — 가시성·정확성 기반 정비 (예상 0.5~1일)

| 작업 | 내용 | 근거 |
|------|------|------|
| 경고 가시화 토글 | 개발 환경에서 `DISABLE_ERRORS_AND_WARNINGS = False`로 일시 전환하여 **fallback/추론 실패 목록 추출** → 보강 대상 식별 | `settings.py:397`이 누락을 은폐 중 |
| 스키마 제목 정정 | `TITLE`을 "Stock-Vis API" 등 전체 범위로 수정 (또는 v1/v2 스플릿 문서) | 제목-범위 불일치 |
| tag 일관성 통일 | `Chain Sight` ↔ `chainsight` 단일화, 자동 tag(앱명)와 명시 tag 규칙 정립 | tag 이중 분류 16건 |

### P1 — 핵심 영역 응답 스키마 명시 (예상 2~3일)

`@extend_schema(responses=..., summary=...)` 추가 우선순위 (트래픽·복잡도 기준):

| 순위 | 영역 | 대상 operation | 작업량 |
|:-:|------|:-:|------|
| 1 | **serverless** | ~73 (현재 6곳만 명시) | 함수형 view 다수 → serializer 또는 inline 스키마 정의 필요. 최대 작업량 |
| 2 | **stocks** | ~38 (명시 0곳) | views_*.py 7개 파일 분산 |
| 3 | **users** | ~48 (명시 2곳) | ViewSet 위주라 serializer 재사용 용이 |
| 4 | **rag_analysis** | ~20 (명시 2곳) | LLM 응답 구조 명시 가치 높음 |
| 5 | **thesis** | ~26 (명시 0곳, ViewSet 3개) | ViewSet serializer 연동 시 자동 개선 |

**작업 패턴(파일당)**: 함수형 view → `@extend_schema(responses={200: SomeSerializer})` + `summary` 1줄. ViewSet → `serializer_class` 지정 시 자동 추론, 응답 envelope만 별도 명시.

### P2 — 가독성·운영 (예상 1일, 선택)

| 작업 | 내용 |
|------|------|
| `summary` 일괄 추가 | 292 op 중 12개만 보유 → Swagger 목록 한 줄 설명 보강 (4% → 목표 80%+) |
| 응답 envelope 컴포넌트화 | `custom_exception_handler`의 `{detail, code?, errors?, status_code}` 표준 에러를 공통 컴포넌트로 등록(`docs/features/api_envelope/policy.md` 연계) |
| CI 스키마 검증 | `manage.py spectacular --validate --fail-on-warn`을 CI에 추가하여 회귀 방지(단, P0 fallback 정리 후) |
| 인증 명시 | JWT Bearer security scheme 전역 적용 여부 점검 (현재 description 텍스트로만 언급) |

### 예상 총 작업량

| 단계 | 작업 | 예상 |
|------|------|------|
| P0 | 경고 가시화 + 제목/tag 정비 | 0.5~1일 |
| P1 | 핵심 5개 영역 응답 스키마 명시 (~205 op) | 2~3일 |
| P2 | summary + envelope + CI 게이트 | 1일 |
| **합계** | | **3.5~5일** (1인 기준, 점진 적용 가능) |

> **권장 접근**: 한 번에 전부가 아니라, `settings.py:396` 주석의 기존 방침("정확한 schema가 필요한 view만 점진 추가")을 따르되, **P0(경고 가시화)부터 수행해 누락 목록을 먼저 확보**한 뒤 트래픽 높은 serverless·stocks 순으로 P1을 진행한다.

---

## 부록 — 감사 방법론

- URL 패턴 집계: 각 `urls.py`의 `path()`/`re_path()`/`router.register()` 정적 카운트 + 직접 판독
- operation 집계: `manage.py spectacular` 실제 생성 산출물(`/tmp/schema_audit.yml`, 219 KB)의 `operationId`/`tags` 분석
- `@extend_schema` 현황: `grep -rn "extend_schema" --include="*.py"` (import 제외 38곳, 13개 파일)
- **코드 변경 없음** — 스키마는 임시 파일(`/tmp`)로만 생성, 저장소 무영향
