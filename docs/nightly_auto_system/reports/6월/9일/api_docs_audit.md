# API 문서 감사 보고서

> 생성일: 2026-06-09 (야간 자동 감사 시스템)
> 모드: **읽기 전용** — 코드 수정 없음
> 범위: Django REST Framework 엔드포인트 전체 + OpenAPI 문서화 상태

---

## 현재 상태

### 1. 문서화 라이브러리 설치 여부

| 항목 | 상태 | 근거 |
|------|------|------|
| **drf-spectacular** | ✅ 설치됨 (`0.29.0`) | `pyproject.toml`, `poetry.lock` |
| **drf-spectacular-sidecar** | ✅ 설치됨 (`2026.5.1`) | Swagger/ReDoc 정적 자산 |
| drf-yasg | ❌ 미설치 | — |
| INSTALLED_APPS 등록 | ✅ 등록됨 | `config/settings.py:212-213` |

> **결론: drf-spectacular은 이미 도입·운영 중**입니다. "도입"이 아니라 **"전 영역 확장(@extend_schema 보강)"**이 실제 과제입니다.

### 2. OpenAPI 스펙 자동 생성 가능 여부

✅ **가능 — 이미 활성화됨.** `config/urls.py:62-72`에 3개 엔드포인트 노출:

| 엔드포인트 | 용도 |
|-----------|------|
| `GET /api/v2/schema/` | OpenAPI 3.0 스펙 (YAML/JSON) |
| `GET /api/v2/swagger/` | Swagger UI |
| `GET /api/v2/redoc/` | ReDoc |

### 3. 설정 현황 (`config/settings.py:370-413`)

```python
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    ...
}
SPECTACULAR_SETTINGS = {
    'TITLE': 'Stock-Vis Market Pulse v2 API',
    'VERSION': '2.0',
    'SCHEMA_PATH_PREFIX': r'/api/v[12]',     # v1 + v2 모두 스캔
    'SWAGGER_UI_DIST': 'SIDECAR',            # 오프라인 자산
    'DISABLE_ERRORS_AND_WARNINGS': True,     # ⚠️ 핵심 이슈 (아래)
    'ENUM_NAME_OVERRIDES': { ... },          # enum collision 해결
}
```

#### ⚠️ 핵심 발견: `DISABLE_ERRORS_AND_WARNINGS: True`

현재 설정은 스키마 생성 시 "unable to guess serializer" 등의 경고를 **전부 억제**합니다. 주석(`settings.py:393-396`)에 명시된 의도:

> "핵심 영역(marketpulse, chainsight, api_request admin)은 명시적 @extend_schema로 정상 처리. 나머지 v1 endpoint는 schema에서 **graceful fallback(string body)**로 노출. 정확한 schema가 필요한 view만 점진적으로 @extend_schema 추가."

**의미**: 현재 스키마는 생성되지만, `@extend_schema`가 없는 대다수 v1 엔드포인트는 **request/response 본문이 `string`(빈 껍데기)으로 노출**됩니다. 즉 *"문서는 존재하나 내용은 부정확"*한 상태입니다.

---

## 엔드포인트 목록 (앱별)

> 집계 기준: `urls.py`의 `path()` 수. ViewSet(router 등록)은 자동 생성되는 CRUD 액션 + `@action`을 합산하여 추정.

### 요청 대상 앱 (지시서 명시 10개)

| 앱 | URL prefix | urls.py 파일 | 엔드포인트 수 | @extend_schema 적용 |
|----|-----------|------------|:---:|:---:|
| **stocks** | `/api/v1/stocks/` | `packages/shared/stocks/urls.py` | **39** | ❌ 0 (8개 view 파일 모두 미적용) |
| **users** | `/api/v1/users/` | `packages/shared/users/urls.py` | **35** | ⚠️ 3 (부분) |
| **news** | `/api/v1/news/` | `services/news/api/urls.py` | **~32** (ReadOnlyModelViewSet 2 + `@action` 30) | ⚠️ 3 (부분) |
| **macro** | `/api/v1/macro/` | `apps/market_pulse/urls.py` | **10** | ❌ 0 (v1 레거시 경로) |
| **rag_analysis** | `/api/v1/rag/` | `services/rag_analysis/urls.py` | **15** | ⚠️ 3 (부분) |
| **serverless** | `/api/v1/serverless/` | `services/serverless/urls.py` | **64** | ⚠️ 7+6 (admin 6 / 일반 7) |
| **thesis** | `/api/v1/thesis/` | `thesis/urls.py` | **~28** (explicit 8 + ViewSet 3종 ~20) | ❌ 0 |
| **validation** | `/api/v1/validation/` | `services/validation/api/urls.py` | **6** | ❌ 0 |
| **chainsight** | `/api/v1/chainsight/` | `apps/chain_sight/api/urls.py` | **~18** (path 7 + WatchlistViewSet 11) | ✅ 8 (양호) |
| **sec_pipeline** | `/api/v1/sec-pipeline/` | `services/sec_pipeline/urls.py` | **2** | ❌ 0 |

### 추가 발견 앱 (지시서 외, config/urls.py에 마운트됨)

| 앱 | URL prefix | urls.py 파일 | 엔드포인트 수 | @extend_schema |
|----|-----------|------------|:---:|:---:|
| api_request (Provider Admin) | `/api/v1/` | `packages/shared/api_request/urls.py` | 6 | ✅ 6 (admin_views) |
| portfolio (Coach DRF) | `/api/v1/coach/` | `apps/portfolio/api/urls.py` | 6 (E1~E6) | ✅ 7 |
| portfolio (legacy) | `/api/` | `apps/portfolio/urls.py` | 0 (빈 패턴, 호환용) | — |
| market_pulse v2 | `/api/v2/market-pulse/` | `apps/market_pulse/api/urls.py` | 5 | ✅ 10 (전체) |
| iron_trading | `/api/v1/iron-trading/` | `integrations/iron_trading/urls.py` | 1 (+trailing-slash 중복) | ❌ 0 |
| 루트/헬스 | `/` | `config/urls.py` | 2 (`api_root`, `health`) | — |

### 집계 요약

| 구분 | 수치 |
|------|------|
| **총 엔드포인트 (추정)** | **약 270개** |
| @extend_schema 적용 view (총 호출 수) | **35개** (12개 파일) |
| **추정 문서화 커버리지** | **약 13%** |

#### @extend_schema 적용 파일 분포 (35개 호출)

```
8  apps/chain_sight/api/views.py          ✅
7  services/serverless/views.py           ⚠️ (일반 7 / 64개 중)
7  apps/portfolio/api/views.py            ✅
6  packages/shared/api_request/admin_views.py  ✅
3  services/rag_analysis/views.py         ⚠️ (3 / 15개 중)
3  services/news/api/views.py             ⚠️ (3 / 32개 중)
3  packages/shared/users/views.py         ⚠️ (3 / 35개 중)
2  apps/market_pulse/api/views/overview.py     ✅
2  apps/market_pulse/api/views/news_refresh.py ✅
2  apps/market_pulse/api/views/i18n.py         ✅
2  apps/market_pulse/api/views/health.py       ✅
2  apps/market_pulse/api/views/cards.py        ✅
```

> **관찰**: `@extend_schema`는 **신규 v2 영역(market_pulse v2, chainsight, portfolio coach, api_request admin)에 집중**되어 있고, **레거시 v1 대량 엔드포인트(stocks 39, users 35, serverless 64, thesis 28, news 32)는 거의 미적용**입니다. 즉, 문서 품질이 "신규=양호 / 레거시=빈 껍데기"로 양극화돼 있습니다.

---

## 도입 작업 목록

> 라이브러리는 이미 설치·설정 완료이므로, 실제 과제는 **(A) 경고 가시화 → (B) 미적용 view에 `@extend_schema` 보강 → (C) 검증 자동화** 3단계입니다.

### Phase A — 진단 가시화 (저비용, 0.5일)

| # | 작업 | 상세 | 수정 파일 |
|---|------|------|----------|
| A-1 | 경고 일시 활성화 후 스캔 | `DISABLE_ERRORS_AND_WARNINGS`를 임시로 `False`로 두고 `python manage.py spectacular --file schema.yml` 실행 → 미문서화 view 전수 목록 확보 | `config/settings.py:397` (임시) |
| A-2 | fallback view 인벤토리 | "unable to guess serializer" 경고 목록 = 보강 대상 우선순위표 | (보고서 산출물) |

> ⚠️ A-1은 **운영 영향 0** (스키마 생성 시점에만 경고 출력). 단, CI에서 `--fail-on-warn` 사용 시 빌드가 깨질 수 있으므로 로컬 진단으로 한정.

### Phase B — `@extend_schema` 보강 (대량, 핵심)

작업량은 view 수에 비례. 우선순위는 **외부 노출도 + FE 의존도** 기준.

| 우선순위 | 앱 | 미적용 endpoint(추정) | 작업 형태 | 예상 공수 |
|:---:|----|:---:|------|:---:|
| **P0** | stocks | 39 | APIView 36개 × `@extend_schema(responses=Serializer)`. Serializer 미존재 view는 `inline_serializer` 또는 `OpenApiResponse` 작성 | 2.5일 |
| **P0** | users | 32 | JWT/portfolio/watchlist. simplejwt view는 기존 spectacular 확장 활용 | 1.5일 |
| **P1** | serverless | ~50 (64-14) | 함수형 뷰(`@api_view`) 다수 → `@extend_schema`를 함수에 직접 부착 | 2.5일 |
| **P1** | thesis | ~28 | ViewSet 3종 + APIView 8. ViewSet은 `@extend_schema_view`로 액션별 일괄 적용 | 1.5일 |
| **P1** | news | ~30 | `@action` 30개 각각 `@extend_schema` (이미 3개 적용 패턴 복제) | 2일 |
| **P2** | rag_analysis | 12 | SSE 스트리밍(`chat/stream`)은 `OpenApiResponse`로 별도 명시 | 1일 |
| **P2** | macro (v1) | 10 | 레거시 경로 — 폐기 예정이면 skip 가능 | 0.5일 |
| **P2** | validation | 6 | symbol path 파라미터 `OpenApiParameter` 명시 | 0.5일 |
| **P3** | chainsight | ~10 (18-8) | WatchlistViewSet `@action` 5개 보강 | 0.5일 |
| **P3** | sec_pipeline | 2 | 소량 | 0.25일 |
| **P3** | iron_trading | 1 | 외부 봇 read-only 계약 — 정확한 스키마 권장 | 0.25일 |

**Phase B 합계: 약 13~14 작업일** (1인 기준, 순수 데코레이터 작업. Serializer 신규 작성 필요 시 추가)

#### 보강 작업의 기술적 분기점

1. **Serializer 존재 view** → `@extend_schema(responses=XxxSerializer)` 한 줄. (간단)
2. **Serializer 없는 dict 응답 view** (stocks/serverless 다수) → `inline_serializer(...)` 또는 `OpenApiResponse(response=OpenApiTypes.OBJECT, examples=[...])` 직접 작성. (공수↑)
3. **함수형 뷰(`@api_view`)** (serverless 대부분) → 함수에 `@extend_schema` 직접 부착 가능. 단 request 파라미터는 `OpenApiParameter`로 수동 기술.
4. **ViewSet** → `@extend_schema_view(list=..., retrieve=...)`로 클래스 레벨 일괄 적용 권장.
5. **path 파라미터 `<str:symbol>`** → 대부분 `OpenApiParameter('symbol', location=PATH)` 명시 필요 (현재 description 누락).

### Phase C — 검증 자동화 (0.5일)

| # | 작업 | 상세 |
|---|------|------|
| C-1 | CI 스키마 검증 | `manage.py spectacular --validate --fail-on-warn`을 nightly CI에 추가 → 신규 미문서화 view 회귀 차단 |
| C-2 | TITLE/DESCRIPTION 갱신 | 현재 `'Stock-Vis Market Pulse v2 API'`는 전체 범위와 불일치 → `'Stock-Vis API'`로 일반화, TAGS에 앱별 그룹 추가 |
| C-3 | 커버리지 트래킹 | `@extend_schema` 적용률을 nightly 리포트에 지표로 추가 (현재 ~13% → 목표 설정) |

---

## 종합 결론

1. **라이브러리 도입은 불필요** — drf-spectacular 0.29.0 + sidecar 2026.5.1이 이미 설치·설정·운영 중. Swagger/ReDoc도 `/api/v2/swagger/`, `/api/v2/redoc/`에서 접근 가능.

2. **실제 문제는 "커버리지 양극화"** — 신규 v2 영역(chainsight, market_pulse v2, portfolio coach, api_request)은 `@extend_schema` 적용 양호하나, **레거시 v1 대량 엔드포인트(stocks·users·serverless·thesis·news 합산 ~190개)는 거의 미적용**. `DISABLE_ERRORS_AND_WARNINGS: True`로 이 사실이 가려져 있음.

3. **권장 실행 순서**: Phase A(진단, 0.5일) → Phase B P0~P1(FE 핵심 의존 앱부터, ~8일) → Phase C(검증 자동화, 0.5일). **전체 약 14~15 작업일**.

4. **즉시 가능한 저비용 개선**: Phase A-1 진단 스캔 + C-2 TITLE 일반화는 반나절 내 완료 가능하며, 현재 "Market Pulse v2 API"로 잘못 표기된 문서 타이틀을 바로잡는 효과.

---

*본 보고서는 읽기 전용 감사로, 어떤 소스 코드도 수정하지 않았습니다.*
