# API 문서 감사 보고서

- **감사 대상**: `/Users/byeongjinjeong/Desktop/stock_vis`
- **감사일**: 2026-06-19
- **유형**: 읽기 전용 (코드 수정 없음)
- **방법**: `config/urls.py` 라우팅 + 각 앱 `urls.py` 패턴 + ViewSet 액션 + `@extend_schema` 사용 현황 정적 분석

---

## 현재 상태

### 문서화 도구 설치 — ✅ 이미 도입됨

`drf-spectacular`이 **이미 설치 및 운영 중**이다. (재도입 불필요, 커버리지 확장만 필요)

| 항목 | 상태 | 근거 |
|------|------|------|
| `drf-spectacular` | ✅ 설치 | `pyproject.toml`: `drf-spectacular = "^0.29.0"` |
| `drf-spectacular-sidecar` | ✅ 설치 | `pyproject.toml`: `^2026.4.14` (Swagger/ReDoc 정적 자산) |
| `INSTALLED_APPS` 등록 | ✅ | `config/settings.py:212-213` |
| `DEFAULT_SCHEMA_CLASS` | ✅ | `settings.py:377` = `drf_spectacular.openapi.AutoSchema` |
| `SPECTACULAR_SETTINGS` | ✅ | `settings.py:384-432` |
| `drf-yasg` | ❌ 미설치 | (spectacular와 택일 — 정상) |

### OpenAPI 스펙 자동 생성 — ✅ 가능

루트 `config/urls.py`에 3개 엔드포인트가 마운트되어 있다:

| 경로 | 뷰 | 용도 |
|------|-----|------|
| `/api/v2/schema/` | `SpectacularAPIView` | OpenAPI 3 스펙 (YAML/JSON) |
| `/api/v2/swagger/` | `SpectacularSwaggerView` | Swagger UI |
| `/api/v2/redoc/` | `SpectacularRedocView` | ReDoc |

`SCHEMA_PATH_PREFIX = r'/api/v[12]'` → **v1·v2 경로 모두** 스펙에 포함된다.

### ⚠️ 핵심 리스크 — "생성은 되지만 품질이 낮다"

`SPECTACULAR_SETTINGS`에 다음이 설정되어 있다 (`settings.py:404`):

```python
'DISABLE_ERRORS_AND_WARNINGS': True,
```

주석(`settings.py:400-403`)이 명시하듯, 이는 의도된 결정이다:
> 핵심 영역(marketpulse, chainsight, api_request admin)만 명시적 `@extend_schema`로 정상 처리.
> 나머지 v1 endpoint는 schema에서 **graceful fallback (string body)** 로 노출.

즉 **스펙은 생성되지만**, `@extend_schema` 데코레이터가 없는 엔드포인트는 요청/응답 본문이 빈 string으로 떨어져 **문서로서 실용성이 낮다**. 경고가 꺼져 있어 이 누락이 빌드 시 드러나지 않는다.

### `@extend_schema` 적용 현황 (실제 데코레이터 37건 / 13개 파일)

| 앱 / 영역 | 데코레이터 수 | 커버리지 평가 |
|-----------|--------------|--------------|
| `apps/portfolio/api` (coach) | 6 | ✅ 완전 (6/6) |
| `apps/market_pulse/api` (v2: overview/cards/news_refresh/i18n/health) | 5 | ✅ 완전 (5/5) |
| `apps/chain_sight/api` (views + event_views) | 9 | 🟡 부분 (주요 뷰 위주) |
| `packages/shared/api_request` (admin) | 5 | ✅ 거의 완전 (5/6) |
| `services/serverless` | 6 | 🔴 희박 (6/64) |
| `services/news/api` | 2 | 🔴 희박 (2/32) |
| `packages/shared/users` | 2 | 🔴 희박 (2/35) |
| `services/rag_analysis` | 2 | 🔴 희박 (2/15) |
| `packages/shared/stocks` | 0 | ❌ 전무 (0/39) |
| `apps/market_pulse` (macro v1) | 0 | ❌ 전무 (0/10) |
| `thesis` | 0 | ❌ 전무 (0/28) |
| `services/validation/api` | 0 | ❌ 전무 (0/6) |
| `services/sec_pipeline` | 0 | ❌ 전무 (0/2) |

> `config/settings.py`의 매칭 2건은 주석/`ENUM_NAME_OVERRIDES` 참조이며 실제 데코레이터가 아니므로 제외.

---

## 엔드포인트 목록 (앱별)

> 모노레포 구조. CLAUDE.md의 앱 경로(`stocks/`, `macro/` 등)와 실제 디렉토리(`packages/shared/`, `apps/`, `services/`)가 다름. 아래는 실제 `urls.py` 기준.
> ViewSet은 표준 CRUD 액션 + `@action` 커스텀 액션을 합산. HTML 페이지 뷰 포함분은 비고에 표기.

### 요청된 10개 앱

| 앱 | URL Prefix | 소스 `urls.py` | 엔드포인트 수 | 비고 |
|----|-----------|---------------|:---:|------|
| **stocks** | `/api/v1/stocks/` | `packages/shared/stocks/urls.py` | **39** | HTML 페이지 뷰 2건(dashboard, stock_detail) 포함. 9개 views_*.py 모듈 분산 |
| **users** | `/api/v1/users/` | `packages/shared/users/urls.py` | **35** | JWT 7 + 세션 6 + 즐겨찾기 3 + 포트폴리오 9 + 관심사 2 + Watchlist 8 |
| **news** | `/api/v1/news/` | `services/news/api/urls.py` | **32** | `NewsViewSet`(ReadOnly: list+retrieve) + `@action` 30건 |
| **macro** | `/api/v1/macro/` | `apps/market_pulse/urls.py` | **10** | macro v1 호환 경로 (namespace `macro` 유지) |
| **rag_analysis** | `/api/v1/rag/` | `services/rag_analysis/urls.py` | **15** | DataBasket 6 + Session 4 + Monitoring 5 |
| **serverless** | `/api/v1/serverless/` | `services/serverless/urls.py` | **64** | 최대 앱. Admin 12 + Movers/키워드 8 + Breadth 3 + Heatmap 3 + Presets 7 + Screener 3 + Alerts 6 + Thesis 4 + ETF 9 + LLM-rel 4 + Institutional 3 + Reg/Patent 2 |
| **thesis** | `/api/v1/thesis/` | `thesis/urls.py` | **28** | 명시 8 + ThesisViewSet 7 + Premise 6 + Indicator 7 (3개 nested router) |
| **validation** | `/api/v1/validation/` | `services/validation/api/urls.py` | **6** | symbol별 summary/metrics/leader/presets/peer-preference/llm-filter |
| **chainsight** | `/api/v1/chainsight/` | `apps/chain_sight/api/urls.py` | **20** | 명시 9 + `WatchlistViewSet`(CRUD 6 + `@action` 5) |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | `services/sec_pipeline/urls.py` | **2** | dashboard + filing-data |
| | | **소계** | **251** | |

### 그 외 라우팅 (참고 — 요청 목록 외)

| 영역 | URL Prefix | 소스 | 엔드포인트 수 | 비고 |
|------|-----------|------|:---:|------|
| api_request (Provider Admin) | `/api/v1/` | `packages/shared/api_request/urls.py` | 6 | health + admin providers 5 |
| portfolio coach (DRF) | `/api/v1/coach/` | `apps/portfolio/api/urls.py` | 6 | e1~e6 |
| portfolio (legacy) | `/api/` | `apps/portfolio/urls.py` | 0 | **빈 urlpatterns** (Slice 13 #65에서 legacy 5건 제거) |
| market_pulse v2 | `/api/v2/market-pulse/` | `apps/market_pulse/api/urls.py` | 5 | overview/card-detail/news-refresh/i18n/health |
| iron_trading | `/api/v1/iron-trading/` | `integrations/iron_trading/urls.py` | 1 | daily-context (slash 유무 2 path, 동일 뷰) |
| schema/swagger/redoc | `/api/v2/` | `config/urls.py` | 3 | 문서화 엔드포인트 |
| root + health | `/`, `/health/` | `config/urls.py` | 2 | |
| | | **소계** | **23** | |

> `services/_dormant/graph_analysis/views.py` 존재하나 `config/urls.py`에 미마운트 (휴면) → 집계 제외.

### 총계

- **요청 10개 앱**: 약 **251 엔드포인트**
- **전체 (마운트된 라우팅)**: 약 **274 엔드포인트**

> ViewSet 표준 액션을 개별 HTTP 메서드로 환산하면 수치는 더 커진다. 위는 라우팅 경로(액션) 기준 보수적 집계.

---

## 도입 작업 목록

> 도구는 이미 도입 완료. 실제 과제는 **"커버리지 확장 + 품질 게이트 복원"**.

### 1. drf-spectacular 설치 + 설정 — ✅ 완료 (잔여 권고만)

설치·마운트는 끝났다. 남은 권고:

- **(권고) `DISABLE_ERRORS_AND_WARNINGS` 단계적 해제** — 현재 `True`라 누락이 은폐됨. 앱별로 `@extend_schema` 보강이 끝나는 대로 `False`로 전환해 CI에서 누락을 잡도록. 즉시 전체 해제는 경고 폭증 → 점진 전환 권장.
- **(권고) 스펙 스냅샷 CI 검증** — `manage.py spectacular --file schema.yml --validate`를 CI에 추가해 회귀 차단.
- **(선택) `/api/v1/schema/` 별칭** — 현재 문서 엔드포인트가 `v2` prefix뿐이라 "v1 API 문서"를 찾는 소비자가 혼동할 수 있음. (스펙 자체는 `SCHEMA_PATH_PREFIX`로 v1 포함.)

### 2. ViewSet/APIView별 `@extend_schema` 추가 범위

전체 약 274개 중 **데코레이터 보유 ~37건**, **미보유 ~237건**. 우선순위:

| 우선순위 | 대상 앱 | 미문서 추정 | 사유 |
|:---:|---------|:---:|------|
| 🔴 P1 | serverless | ~58 | 최다 엔드포인트, 함수형 뷰 다수 → 응답 스키마 수동 명세 필요 |
| 🔴 P1 | stocks | 39 | 데코레이터 전무. 외부/프론트 소비 핵심 (차트·재무·시세) |
| 🔴 P1 | users | 33 | 인증·포트폴리오·Watchlist, 보안 민감 → 요청/응답 명세 가치 큼 |
| 🟡 P2 | news | 30 | `@action` 30건, 대부분 `responses` 미지정 |
| 🟡 P2 | thesis | 28 | ViewSet 3종 + nested router, 데코레이터 전무 |
| 🟡 P2 | rag_analysis | 13 | SSE 스트리밍(`chat/stream`)은 별도 명세 주의 |
| 🟢 P3 | chainsight | ~11 | 주요 뷰 일부 완료, Watchlist 액션 보강 |
| 🟢 P3 | macro(v1) | 10 | v2로 대체 진행 중이면 우선순위 하향 가능 |
| 🟢 P3 | validation | 6 | symbol 파라미터 + 응답 명세 |
| 🟢 P3 | sec_pipeline | 2 | 소규모 |
| ✅ 완료 | portfolio coach / market_pulse v2 / api_request | — | 유지보수만 |

각 추가 시 권장 명세 항목: `summary`, `tags`(앱별 그룹핑), `parameters`(path `symbol` 등), `request`(serializer 또는 inline), `responses`(상태코드별 serializer/`OpenApiResponse`), `examples`.

> 함수형 뷰(serverless 다수)는 serializer가 없어 `inline_serializer` 또는 `OpenApiResponse` 수동 작성이 필요 → APIView/ViewSet보다 건당 공수가 큼.

### 3. 예상 작업량

가정: 클래스형 뷰 평균 10~15분/건, 함수형(스키마 수기) 20~30분/건, 공통 컴포넌트(serializer 정비·tags 체계·enum) 별도.

| 구간 | 범위 | 추정 공수 |
|------|------|----------|
| 기반 정비 | tags 체계 + 공통 `OpenApiResponse`/에러 envelope 스키마 + enum 정리 | 0.5~1일 |
| P1 (serverless·stocks·users, ~130건) | 함수형 다수 → 건당 공수 큼 | 4~6일 |
| P2 (news·thesis·rag, ~71건) | ViewSet/action 위주 | 2~3일 |
| P3 (chainsight·macro·validation·sec, ~29건) | 소규모 | 1~1.5일 |
| 마감 | `DISABLE_ERRORS_AND_WARNINGS=False` 전환 + CI 스펙 검증 + 잔여 경고 해소 | 1일 |
| **합계** | 전 앱 명시 문서화 | **약 8.5~12.5일 (1인 기준)** |

**단계적 권장**: 전부 한 번에 하지 말 것. ① P1 3개 앱만 먼저 명시 → ② 해당 앱 한정으로 경고 게이트 켜기 → ③ P2·P3 순차 확장. 외부 노출/프론트 소비 빈도가 높은 stocks·users·serverless를 최우선.

---

## 요약

1. **도구는 이미 도입됨** — `drf-spectacular` 0.29.0 + sidecar, `/api/v2/{schema,swagger,redoc}/` 운영 중. 재설치 불필요.
2. **스펙은 생성되나 커버리지가 낮다** — 약 274개 엔드포인트 중 명시적 `@extend_schema`는 ~37건(13.5%). 나머지는 graceful fallback(string body)으로 품질 낮음.
3. **`DISABLE_ERRORS_AND_WARNINGS=True`가 누락을 은폐** — 핵심 게이트가 꺼져 있어 미문서 엔드포인트가 빌드에서 드러나지 않음.
4. **전무 앱 5개(stocks·macro·thesis·validation·sec_pipeline)**, 희박 앱 4개(serverless·news·users·rag). 완료 앱은 portfolio coach·market_pulse v2·api_request.
5. **실제 과제 = 커버리지 확장(P1: stocks·users·serverless 우선) + 경고 게이트 단계적 복원**. 전 앱 명시화 추정 8.5~12.5일(1인).
