# API 문서 감사 보고서

> 작성일: 2026-05-18
> 범위: Stock-Vis Django 백엔드 전체 API
> 모드: 읽기 전용 (코드 수정 없음)

---

## 현재 상태

### 1. OpenAPI/Swagger 인프라

| 항목 | 상태 | 비고 |
|------|------|------|
| **drf-spectacular** | ✅ 설치됨 (`^0.29.0`) | `pyproject.toml` |
| **drf-spectacular-sidecar** | ✅ 설치됨 (`^2026.4.14`) | Swagger UI / ReDoc 정적 자산 |
| **INSTALLED_APPS 등록** | ✅ 완료 | `config/settings.py:205-206` |
| **DEFAULT_SCHEMA_CLASS** | ✅ 설정됨 | `drf_spectacular.openapi.AutoSchema` (settings.py:363) |
| **SPECTACULAR_SETTINGS** | ✅ 설정됨 | settings.py:370~418 |
| **drf-yasg** | ❌ 미사용 | drf-spectacular로 일원화 |

### 2. Schema 엔드포인트 (현재 노출 범위)

`config/urls.py`에 다음 3개 경로가 등록되어 있음:

```python
path('api/v2/schema/', SpectacularAPIView.as_view(), name='schema-v2'),
path('api/v2/swagger/', SpectacularSwaggerView.as_view(...), name='swagger-v2'),
path('api/v2/redoc/', SpectacularRedocView.as_view(...), name='redoc-v2'),
```

- `SCHEMA_PATH_PREFIX = r'/api/v[12]'` → v1 + v2 모두 schema 대상에 포함
- `DISABLE_ERRORS_AND_WARNINGS = True` → 미설정 view는 graceful fallback (string body)
- 현재 자동 생성 가능: **Market Pulse v2** 위주 + 일부 v1 (chainsight, api_request admin, marketpulse 등)
- **결론**: 인프라는 갖춰져 있으나 **v1 핵심 도메인이 모두 graceful fallback**으로 노출되어 실용성 낮음

### 3. `@extend_schema` 적용 현황 (자세한 스키마 보유 view)

총 **31건** 적용됨 (12개 파일):

| 파일 | 적용 수 | 상태 |
|------|---------|------|
| `chainsight/api/views.py` | 8 | 잘 적용됨 |
| `serverless/views.py` | 6 (53 view 중) | 부분 적용 (11%) |
| `api_request/admin_views.py` | 6 | 잘 적용됨 |
| `marketpulse/api/views/*.py` (5개) | 5 (각 1) | 잘 적용됨 (v2 우선) |
| `users/views.py` | 2 (28 view 중) | 거의 미적용 (7%) |
| `rag_analysis/views.py` | 2 (16 view 중) | 거의 미적용 (12%) |
| `news/api/views.py` | 2 (32 action 중) | 거의 미적용 |
| **`stocks/views*.py` (8개 파일)** | **0** | **전혀 미적용** |
| **`macro/views.py`** | **0** | **전혀 미적용** |
| **`thesis/views/`** | **0** | **전혀 미적용** |
| **`validation/api/views.py`** | **0** | **전혀 미적용** |
| **`sec_pipeline/views.py`** | **0** | **전혀 미적용** |
| **`portfolio/views.py`** | **0** | **전혀 미적용** |

---

## 엔드포인트 목록 (앱별 테이블)

> `path(...)` 직접 등록 개수 + ViewSet `@action` 개수 합산. ViewSet 표준 CRUD는 추가로 카운트.

| 앱 | URL prefix | path() | ViewSet 등록 | @action | View 클래스/함수 | 비고 |
|----|-----------|--------|-------------|---------|-----------------|------|
| **stocks** | `/api/v1/stocks/` | 39 | - | - | 42 (8개 views*.py) | 도메인 핵심. 대시보드/검색/지표/펀더멘털/스크리너/시세/EOD |
| **users** | `/api/v1/users/` | 35 | - | - | 28 + JWT views | 인증 + 즐겨찾기 + Portfolio + Watchlist + Interest |
| **news** | `/api/v1/news/` | 1 (router) | `NewsViewSet` | 30 | 2 | ViewSet 1개 + 30 custom action |
| **macro** | `/api/v1/macro/` | 10 | - | - | 10 | Market Pulse v1 (구버전) |
| **rag_analysis** | `/api/v1/rag/` | 15 | - | - | 16 | DataBasket + AnalysisSession + Monitoring |
| **serverless** | `/api/v1/serverless/` | 64 | - | - | 53 + 12 admin | Market Movers + Screener + Alerts + Thesis + ETF + LLM Relations + Institutional + Regulatory |
| **thesis** | `/api/v1/thesis/` | 11 | 3 ViewSet | 2 | 11 | ThesisViewSet + Premise/Indicator nested + Conversation + Dashboard + Alerts |
| **validation** | `/api/v1/validation/` | 6 | - | - | 6 | Peer 비교 (summary/metrics/leader/presets/peer-preference/llm-filter) |
| **chainsight** | `/api/v1/chainsight/` | 7 | `WatchlistViewSet` (5 action) | 5 | 10 | 그래프 탐색 + Watchlist |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | 2 | - | - | 1 + 1 fn | Filing + Dashboard |
| **api_request** | `/api/v1/` | 6 | - | - | 6 fn | Provider Admin API |
| **portfolio** | `/api/coach/` | 5 | - | - | 5 fn | Coach E1/E2/E3/E5/E6 (LLM) |
| **marketpulse_v2** | `/api/v2/market-pulse/` | 5 | - | - | 5 | OpenAPI 적용 완료 |

### 앱별 엔드포인트 합산

| 앱 | 총 엔드포인트 (대략) | @extend_schema 적용 비율 |
|----|--------------------|----------------------|
| stocks | **39** | 0% |
| users | **35** | ~5% |
| news | **30** (ViewSet actions) | ~7% |
| macro | **10** | 0% |
| rag_analysis | **15** | ~13% |
| serverless | **64** | ~9% |
| thesis | **~20** (path 11 + ViewSet 표준 CRUD + action 2) | 0% |
| validation | **6** | 0% |
| chainsight | **~12** (path 7 + Watchlist CRUD 5) | ~67% |
| sec_pipeline | **2** | 0% |
| api_request | **6** | 100% |
| portfolio | **5** | 0% |
| marketpulse_v2 | **5** | 100% |
| **합계** | **~249** | **~12% 가중 평균** |

> 정확한 OpenAPI 스펙 카운트는 `python manage.py spectacular --file schema.yml --validate` 실행 시 산출 가능 (이번 감사는 정적 분석만 수행).

---

## 도입 작업 목록

### Phase A — 인프라 마무리 (½일, ~4h)

1. **v1 schema 엔드포인트 노출**
   - `config/urls.py`에 `/api/v1/schema/`, `/api/v1/swagger/`, `/api/v1/redoc/` 추가
   - 또는 `/api/schema/` 단일 통합 엔드포인트로 변경
2. **`SCHEMA_PATH_PREFIX` 검증**
   - 현재 `r'/api/v[12]'` → `/api/coach/`, `/api/v1/` 둘 다 포함되는지 확인
3. **`DISABLE_ERRORS_AND_WARNINGS` 임시 해제 후 경고 수집**
   - 어떤 view가 graceful fallback인지 목록화 → 우선순위 결정

**작업량**: 0.5일

### Phase B — 핵심 도메인 `@extend_schema` 추가 (3~4일, ~24h)

우선순위 (사용 빈도 + 외부 의존성 기준):

| 우선순위 | 앱 | view 수 | 예상 작업 | 시간 |
|---------|-----|--------|----------|------|
| P0 | **users (JWT + Portfolio + Watchlist)** | 28 | 응답 schema, error code, 인증 명시 | 6h |
| P0 | **stocks** (8 files, 42 view) | 42 | symbol path param, 응답 schema, 가격/지표 enum | 8h |
| P1 | **thesis** (ViewSet 3개 + path 11) | ~20 | nested router 응답 + Conversation request/response | 4h |
| P1 | **rag_analysis** (16 view) | 16 | DataBasket/Session schema + SSE stream 별도 처리 | 3h |
| P1 | **serverless** 잔여 47건 | 47 | Market Movers/Screener/Alerts/ETF/LLM Relations | 3h |
| P2 | **news ViewSet** 30 action | 30 | `@extend_schema_view` + 30개 action 응답 명세 | 2h |
| P2 | macro, validation, sec_pipeline, portfolio | 23 | 단순 view 위주, 빠르게 처리 | 2h |

**작업량**: 3~4일 (28h)

### Phase C — 공통 컴포넌트 정비 (1일, ~6h)

1. **에러 envelope serializer 등록**
   - 현재 `config.exception_handler.custom_exception_handler` 사용 중 (settings.py:366)
   - `{detail, code, errors, status_code}` Serializer 정의 → `OpenApiResponse` 표준 등록
   - 모든 4xx/5xx 응답에 일괄 적용
2. **인증 스키마 명세**
   - JWT Bearer (simplejwt) → `SECURITY` 설정 자동 적용 확인
3. **공통 path/query 파라미터**
   - `symbol`, `<int:pk>`, `period`, `limit/offset` → `OpenApiParameter` 재사용 헬퍼 작성
4. **`ENUM_NAME_OVERRIDES` 보강**
   - 현재 4개만 등록됨 → 신규 enum (예: news category, screener filter) 충돌 시 추가

**작업량**: 1일 (6h)

### Phase D — CI 통합 + 문서화 (½일, ~4h)

1. **`manage.py spectacular --validate`** → CI 단계에 추가
2. **schema diff 검출** → contracts/ 디렉토리와 자동 동기화 검토
3. **README 업데이트**: Swagger UI 접근 방법, 인증 토큰 사용법
4. **`contracts/` 스펙과 spectacular 산출물 일치 검증**

**작업량**: 0.5일 (4h)

---

## 총 작업량 추정

| Phase | 작업 | 시간 |
|-------|------|------|
| A | 인프라 마무리 | 4h |
| B | 핵심 도메인 `@extend_schema` 적용 | 28h |
| C | 공통 컴포넌트 정비 | 6h |
| D | CI 통합 + 문서화 | 4h |
| **합계** | | **42h (~5~6 일)** |

### 단계적 도입 권고

- **MVP (2일)**: Phase A + Phase B 중 P0 (users + stocks) → v1 schema endpoint + 핵심 도메인 schema
- **확장 (3~4일)**: Phase B 잔여 + Phase C → 전체 도메인 + 에러 envelope
- **완성 (½일)**: Phase D → CI 통합

### 리스크 요소

1. **`serverless/views.py` 함수 기반 view (53개)** → `@extend_schema` 보다 `@api_view` 데코레이터 위에 추가 필요. 응답 schema 정의 비용 큼.
2. **`news/api/views.py` ViewSet 30 action** → `@extend_schema_view`로 일괄 처리 필요, action별 응답이 다양함.
3. **SSE 엔드포인트 (`rag_analysis/sessions/.../chat/stream/`)** → drf-spectacular는 streaming response 표현 한계. `responses=OpenApiResponse(...)` + 별도 README 명세 필요.
4. **`thesis` nested router (premises, indicators)** → `<uuid:thesis_id>` path 캡처 → `OpenApiParameter(location=PATH)` 명시 필요.
5. **`/api/coach/` prefix** → `SCHEMA_PATH_PREFIX = r'/api/v[12]'` 정규식에 미포함. portfolio coach 5개 endpoint가 schema에서 누락될 수 있음 → 정규식 보강 필요.

---

## 빠른 검증 커맨드

```bash
# 1. schema 생성 가능 여부 확인
python manage.py spectacular --file /tmp/schema.yml --validate

# 2. 경고 확인 (graceful fallback 잡기)
python manage.py spectacular --fail-on-warn --file /tmp/schema.yml
# → DISABLE_ERRORS_AND_WARNINGS 잠시 False로 변경 후 실행

# 3. Swagger UI 접근
# 개발 서버 기동 후 → http://localhost:8000/api/v2/swagger/
# (v1은 현재 endpoint 미등록 — Phase A 작업 필요)

# 4. 적용 누락 view 검출
grep -L "@extend_schema" stocks/views*.py thesis/views/*.py macro/views.py
```
