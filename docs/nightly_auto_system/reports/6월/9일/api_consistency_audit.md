# API 응답 일관성 감사 보고서

- **감사일**: 2026-06-09
- **유형**: 읽기 전용 (코드 미수정)
- **범위**: 전체 DRF `views*.py` 28개 + 전역 `REST_FRAMEWORK` 설정 + `config/exception_handler.py`
- **기준 정책**: [`docs/features/api_envelope/policy.md`](../../../../features/api_envelope/policy.md) (2026-05-12 제정, "envelope 폐기 + DRF 평탄 통일")
- **직전 감사**: `docs/nightly_auto_system/reports/5월/5일/api_consistency_audit.md` (P1 #14 envelope 단일화의 근거)

---

## 요약

2026-05-12 정책은 **성공 응답을 `serializer.data`/평탄 dict로 통일**하고 `{success, data, meta}` wrapping을 폐기하며, **에러는 `{detail, code?, errors?, status_code}` 단일 표준**으로 수렴시키기로 결정했다. 전역 `EXCEPTION_HANDLER`(`config/exception_handler.py`)가 `raise` 기반 예외를 이 표준 envelope로 변환하는 인프라는 **정착**되어 있다.

그러나 이번 감사에서 **정책과 현행 구현 간 미완료 마이그레이션 3개 클러스터**를 확인했다.

| 심각도 | 발견 | 영향 |
|--------|------|------|
| 🔴 P1 | **WRAP 잔존**: `views_exchange.py` / `views_fundamentals.py` / `views_screener.py` 3개 파일이 폐기 대상인 `{'success': True, 'data': ..., 'meta': ...}` 래핑을 여전히 사용 | 동일 stocks 앱 내 응답 스키마 이중화. FE가 `.data` 언래핑 분기를 유지해야 함 |
| 🟡 P2 | **에러 키 혼재**: view 직접 반환 시 `{'error': str}`(주류) vs `{'detail': str}`(watchlist) vs `{'error': {code, message}}`(iron_trading) vs `{'error', 'message'}`(validation). 단, `raise` 경로는 전부 표준 `{detail, code}` | 클라이언트 에러 파싱 분기 비표준화. status code 우선 분기로 완화되나 body 계약 불일치 |
| 🟡 P2 | **하드코딩 상태 코드**: `iron_trading/views.py`(400/404/503/200), `sec_pipeline/views.py`(202/200), `market_pulse/api/views/cards.py:84`(404)가 `status.HTTP_*` 모듈 대신 정수 리터럴 사용 | 가독성·grep 추적성 저하. 기능 영향은 없음 |
| 🟢 P3 | **페이지네이션 산발**: 전역 `DEFAULT_PAGINATION_CLASS` 미설정(정책상 의도된 ViewSet 단위 적용). 다만 메타 응답 형식이 `{count,next,previous,results}`(DRF 표준) / `{results, pagination:{...}}`(users, rag) / 수동 offset slicing(news, serverless)으로 3종 혼재 | 목록 API 클라이언트 페이지네이션 처리 비일관 |

**전반 평가**: 에러 변환 인프라와 성공 응답 평탄화 방향성은 정착했으나, **WRAP 3파일 잔존**이 가장 시급한 미완료 부채다. 정책 §1이 "wrapping 사용은 6개 파일뿐"이라 했는데 현재 최소 3개가 남아 있어 마이그레이션이 절반만 완료된 상태로 추정된다.

---

## 앱별 응답 패턴 매트릭스

| 앱 / 파일 | 성공 래핑 | 에러 키 | 상태코드 표기 | 페이지네이션 |
|-----------|-----------|---------|---------------|--------------|
| **stocks** `views.py` | 평탄 (`serializer.data`, dict) | `{error}` + 중첩 `{error:{code,message,details}}` (L654) | `status.HTTP_*` ✅ | `StockListPagination` (PageNumber, page_size=50) ✅ |
| **stocks** `views_eod.py` | 평탄 dict | `{error}` | `status.HTTP_*` ✅ | 고정 `[:50]` slicing |
| **stocks** `views_exchange.py` | 🔴 **WRAP** `{success, data, meta}` (L71~) | `{error}` | `status.HTTP_*` (503 등) ✅ | 없음 |
| **stocks** `views_fundamentals.py` | 🔴 **WRAP** `{success, data, meta}` (L92~) | `{error}` | `status.HTTP_*` ✅ | limit 파라미터 |
| **stocks** `views_indicators.py` | 평탄 dict | `{error}` | `status.HTTP_*` ✅ | 없음 |
| **stocks** `views_market_movers.py` | 평탄 `serializer.data` | `{error}` | `status.HTTP_*` ✅ | 없음 |
| **stocks** `views_mvp.py` | 평탄 dict (`{mode,count,data}`) | 에러 응답 없음 | 명시 없음(200) | 고정 `[:20]` slicing |
| **stocks** `views_screener.py` | 🔴 **WRAP** `{success, data, meta}` (L98~) | `{error}` (+ `{error: serializer.errors}`) | `status.HTTP_*` ✅ | limit 파라미터 |
| **stocks** `views_search.py` | 평탄 (`{count, results}`) | `{error}` | `status.HTTP_*` ✅ | 고정 `[:10]` slicing |
| **metrics** `views.py` | (빈 파일) | — | — | — |
| **users** `views.py` | 평탄 (`serializer.data`, 다수 커스텀 dict) | `{error}` / `{message}` / DRF `raise`(detail) 혼재 | `status.HTTP_*` (201/204/207 포함) ✅ | Django `Paginator` → `{results, pagination:{...}}` |
| **users** `jwt_views.py` | 평탄 (`{user, tokens, message}`) | `{error}` | `status.HTTP_*` ✅ | 없음 |
| **api_request** `admin_views.py` | 평탄 dict | `{error}` | `status.HTTP_*` ✅ | 없음 |
| **chain_sight** `api/views.py` | 평탄 dict (`_sanitize_neo4j`) | `{error}` | `status.HTTP_*` (404/400/503) ✅ | 수동 page/page_size (SignalFeed만) |
| **chain_sight** `watchlist_views.py` | 평탄 `serializer.data` | 🟡 `{detail}` (DRF 관례) | `status.HTTP_*` (201/400/503) ✅ | ViewSet 기본(설정상 미적용) |
| **market_pulse** `views.py` | 평탄 `serializer.data`/dict | `{error}` | `status.HTTP_*` ✅ | 없음 |
| **market_pulse** `api/views/cards.py` | 🟡 `_envelope` `{_meta, data}` (정책 예외) | `{error}` | 🟡 숫자 `404` (L84) | 없음 |
| **market_pulse** `api/views/health.py` | `{_meta, probes, last_runs}` (정책 예외) | 없음 | 200 | 없음 |
| **market_pulse** `api/views/i18n.py` | `{_meta, labels}` (정책 예외) | 없음 (warning in _meta) | 200 | 없음 |
| **market_pulse** `api/views/news_refresh.py` | `{_meta, items}` (정책 예외) | 없음 | 200 | 고정 limit=6 |
| **market_pulse** `api/views/overview.py` | `{_meta, ticker_bar, news, cards}` (정책 예외) | 없음 (status_reason in _meta) | 200 | 없음 |
| **portfolio** `api/views.py` | 평탄 `serializer.data` | `{error}` + extra(`scope`,`type`) | `status.HTTP_*` (429/502/500) ✅ | 없음 |
| **portfolio** `views.py` | (빈 파일, deprecated) | — | — | — |
| **news** `api/views.py` | 평탄 (`{symbol, count, data}`) | `{error}` + DRF `ValidationError`/`NotFound` | `status.HTTP_*` ✅ | `NewsArticlePagination`(PageNumber, 20) 선언 + 수동 offset slicing 병존 |
| **news** `views.py` | (빈 파일) | — | — | — |
| **rag_analysis** `views.py` | 평탄 `serializer.data`/dict | DRF `raise`(detail) + 커스텀 예외(`BasketFull` 등) | `status.HTTP_*` (201/204/400/401/404) ✅ | Django `Paginator` → `{..., pagination:{...}}` |
| **sec_pipeline** `views.py` | 평탄 dict | None 체크 후 202 | 🟡 숫자 `202`/`200` | 없음 |
| **serverless** `views.py` | 평탄 dict | `{error}` + DRF `ValidationError`/`NotFound` + 커스텀(`SyncFailed`) | `status.HTTP_*` (201/400/404/429/500) ✅ | 수동 offset/limit → `{next, previous}` 포함 |
| **serverless** `views_admin.py` | 평탄 dict | `{error}` (+`requires_confirm`) | `status.HTTP_*` (201/204/400/429) ✅ | 없음 |
| **validation** `api/views.py` | 평탄 dict | 🟡 `{error}` + `{error, message}` 혼재 | `status.HTTP_*` (404/400/401/**422**) ✅ | 없음 |
| **validation** `views.py` | (빈 파일) | — | — | — |
| **graph_analysis** `_dormant/views.py` | (빈 파일, 휴면) | — | — | — |
| **thesis** `conversation_views.py` | 평탄 (`result`, `{issues}`) | `{error}` | `status.HTTP_400` ✅ | 없음 |
| **thesis** `monitoring_views.py` | 평탄 구조화 dict | exception handler 위임 | 200 기본 | 🟡 hardcoded `[:50]` limit |
| **thesis** `thesis_views.py` | 평탄 (`{status, thesis_id}`) + ViewSet | `{error}` | `status.HTTP_400` ✅ | ViewSet 기본 |
| **config** `views.py` | 🟡 `JsonResponse` (DRF 아님) | — | 200 | — (API root/health 전용) |
| **iron_trading** `views.py` | `error_body` 래퍼 / 평탄 payload | 🟡 중첩 `{error:{code, message, retry_after_seconds}}` | 🟡 숫자 `400/404/503/200` | — |

> 범례: ✅ 정책 부합 · 🟡 비표준/경미 불일치 · 🔴 정책 위반(시급)

---

## HTTP 상태 코드 일관성

### 모듈 사용 (`status.HTTP_*`) — 양호

전체 28개 파일 중 **대다수가 `status.HTTP_*` 상수를 일관 사용**한다. 생성(201)·삭제(204)·검증실패(400)·인증(401)·미존재(404)·레이트(429)·서버오류(500)가 모듈 상수로 표기된다. 일부 앱은 도메인 상황에 맞는 정교한 코드까지 사용:

- **users** `views.py`: `HTTP_207_MULTI_STATUS`(L580, 배치 부분 성공), `HTTP_204_NO_CONTENT`(삭제)
- **portfolio** `api/views.py`: `HTTP_429_TOO_MANY_REQUESTS`(LLM 예산 초과), `HTTP_502_BAD_GATEWAY`(LLM 호출 실패)
- **validation** `api/views.py`: `HTTP_422_UNPROCESSABLE_ENTITY`(L85, S&P500 비대상 — 비즈니스 상태)

### 하드코딩 숫자 리터럴 — 🟡 비표준 3곳

| 파일 | 위치 | 코드 |
|------|------|------|
| `integrations/iron_trading/views.py` | L36/41/43/50 | `status=400`, `404`, `503`, `200` |
| `services/sec_pipeline/views.py` | L43~55 | `status=202`, `status=200` |
| `apps/market_pulse/api/views/cards.py` | L84 | `status=404` |

→ 기능상 동일하나, 코드 일관성·grep 추적성 측면에서 `status.HTTP_*`로 통일 권장.

### 201 사용 시점 불일치 — 🟡 경미

POST 생성 성공 시 201을 명시하는 곳(`rag_analysis`, `serverless`, `serverless_admin`, `users`, `stocks`, `watchlist`)과, POST이면서도 상태 미지정으로 200 반환하는 곳(`news/api/views.py` L666~의 트리거성 POST)이 혼재. 단 트리거성/멱등성 POST는 200/202가 합당할 수 있어 일률 강제는 부적절.

---

## 에러 응답 형식

### 두 경로의 분리

이 코드베이스의 에러 응답은 **두 경로**로 나뉘며, 둘의 표준화 수준이 다르다.

**(A) `raise` 경로 — 표준화 완료 ✅**

`config/exception_handler.py:custom_exception_handler`(`REST_FRAMEWORK.EXCEPTION_HANDLER` 등록)가 모든 DRF 예외를 단일 envelope로 변환:

```json
{ "detail": "...", "code": "...", "errors": {...}, "status_code": 404 }
```

- `ValidationError` → `{detail: "Validation failed.", code, errors: {field-level}}`
- `NotFound`/`PermissionDenied`/커스텀 `APIException` → `{detail, code}`
- `raise` 기반인 `rag_analysis`, `serverless`, `news/api`(`ValidationError`/`NotFound`), `validation` 일부가 이 경로를 탄다 → **일관됨**.

**(B) `Response({...}, status=...)` 직접 반환 경로 — 🟡 키 혼재**

view가 직접 에러 dict를 만드는 경우, 핸들러를 우회하므로 표준 envelope가 적용되지 않고 키가 제각각:

| 에러 키 형태 | 사용처 |
|--------------|--------|
| `{'error': str}` (주류) | stocks 전반, market_pulse, portfolio, chain_sight/api, serverless_admin, thesis, jwt_views, admin_views, news/api 일부 |
| `{'detail': str}` (DRF 관례 일치) | `chain_sight/watchlist_views.py` 전체 |
| `{'error': str, 'message': str}` | `validation/api/views.py` L71/L82 |
| `{'error': {'code', 'message', 'retry_after_seconds'}}` (중첩) | `iron_trading/views.py` (`error_body()`) |
| `{'error': {'code', 'message', 'details'}}` (중첩) | `stocks/views.py` L654 (`StockNotFoundError.to_response()`) |
| `{'message': str}` | `users/views.py` L219/L249 |

→ **정책 §2.2의 표준은 `{detail, code?, errors?, status_code}`**(키 = `detail`)인데, view 직접 반환 경로의 주류는 `{error}`다. 즉 **`raise` 경로(detail)와 `Response` 직접 경로(error)가 서로 다른 키를 노출**하여, 클라이언트가 두 키를 모두 파싱해야 하는 이중 계약이 존재한다.

> **완화 요인**: 정책 §1의 설계 의도는 "클라이언트는 status code 우선 분기 + body `code` 보강". status code는 두 경로 모두 정확하므로 치명적 장애는 아니나, body 계약은 비표준이다.

---

## 페이지네이션 현황

### 전역 설정

`config/settings.py`의 `REST_FRAMEWORK`에 **`DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` 미설정**. 이는 정책 §1 결정("페이지네이션은 ViewSet 단위 적용, 전역 미적용")과 **의도적으로 일치**한다.

```python
# config/settings.py:355~374 (발췌)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (JWT, Session),
    'DEFAULT_PERMISSION_CLASSES': [IsAuthenticated],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
    # DEFAULT_PAGINATION_CLASS 없음 / PAGE_SIZE 없음
}
```

### 구현 형식 3종 혼재 — 🟡

| 형식 | 사용처 | 응답 스키마 |
|------|--------|-------------|
| DRF `PageNumberPagination` (표준) | `stocks/views.py`(`StockListPagination`), `news/api/views.py`(`NewsArticlePagination`) | `{count, next, previous, results}` |
| Django `Paginator` 수동 | `users/views.py`, `rag_analysis/views.py` | `{results, pagination: {current_page, total_pages, has_next, ...}}` |
| 수동 offset/limit slicing | `serverless/views.py`(`{next, previous}`), `news/api`(offset slicing) | 라우트별 상이 |

→ 정책 §2.1의 목록 표준은 DRF `{count, next, previous, results}`. `users`/`rag_analysis`의 `{results, pagination:{...}}` 형식은 표준과 키가 다르다.

### 페이지네이션 부재 목록 — 잠재 부하 위험 🟡

목록을 반환하면서 **페이지네이션 없이 전량 반환 또는 고정 slicing**하는 곳:

- `stocks/views_eod.py` `[:50]`, `views_mvp.py` `[:20]`, `views_search.py` `[:10]` — 고정 상한이라 폭주 위험은 낮음
- `chain_sight/watchlist_views.py` 목록(ViewSet, 페이지네이션 설정 부재) — **상한 없이 `.filter()` 전량 반환 가능**
- `thesis/monitoring_views.py` L238 `[:50]` hardcoded, L62 `list(thesis.indicators.filter(...))` — 상한 의존
- `serverless/views_admin.py` 목록 `.all()` 전량 직렬화 — **상한 없음**
- `validation/api/views.py` `.filter()`/`.all()` 전량 — **상한 없음**

→ 데이터 증가 시 응답 크기·메모리 부하 가능. 무상한 `.all()`/`.filter()` 라우트는 페이지네이션 또는 명시적 상한 도입 검토 권장.

---

## 권고사항

### 🔴 P1 — WRAP 잔존 3파일 마이그레이션 (정책 위반)

`views_exchange.py` / `views_fundamentals.py` / `views_screener.py`의 `{'success': True, 'data': ..., 'meta': ...}` 래핑을 정책 §1대로 **평탄 `serializer.data` 또는 평탄 dict로 전환**. `meta`가 필수면 응답 헤더(`X-Request-Id` 등)로 분리. FE `screenerService.ts` 언래핑 로직과 동반 수정 필요(정책 적용 범위에 명시됨).

- **검증 포인트**: 마이그레이션 전 FE가 `.data`를 언래핑하는지 grep으로 의존성 확인 후, 동일 PR에서 BE+FE 동시 전환(이중 진실 회피).

### 🟡 P2 — view 직접 반환 에러 키 `error → detail` 통일

`Response({...}, status=...)` 직접 반환 경로의 `{'error': str}`를 표준 `{'detail': str, 'code': ...}`로 정렬. 가장 일관적인 방향은 **view 직접 에러 dict를 `raise APIException(detail, code)` 으로 전환**하여 단일 `exception_handler` 경로로 수렴시키는 것. 최소한 키만이라도 `detail`로 통일.

- 우선 대상: `validation/api/views.py`(`{error, message}` 혼재), `iron_trading`(외부 계약이라 schema_version 명시되어 있으면 별도 취급 가능 — 외부 consumer 영향 확인 필요).

### 🟡 P2 — 하드코딩 상태 코드 → `status.HTTP_*`

`iron_trading/views.py`, `sec_pipeline/views.py`, `cards.py:84`의 정수 리터럴을 모듈 상수로 교체. (기능 무영향, 추적성 개선)

### 🟡 P3 — 페이지네이션 형식 통일 + 무상한 목록 보강

- `users`/`rag_analysis`의 `{results, pagination:{...}}`를 DRF 표준 `{count, next, previous, results}`로 정렬 검토.
- 무상한 `.all()`/`.filter()` 목록(`serverless_admin`, `validation/api`, `watchlist` list)에 `pagination_class` 또는 명시적 상한 도입.

### ✅ 유지 — 정책 예외 항목

- `market_pulse/api/views/*`의 `_envelope`/`{_meta, ...}` 구조는 정책 §0에서 **명시적 예외**로 인정된 항목 → 변경 불필요.
- `config/views.py`의 `JsonResponse`는 API root/health 전용 비-DRF 라우트 → 현행 유지 무방.
- `raise` 기반 에러 경로 및 전역 `EXCEPTION_HANDLER` 인프라 → 표준 정착 완료, 유지.

---

## 부록 — 감사 메타

- **분석 대상**: `views*.py` 28개 (빈 파일 5개: `metrics`, `news/views.py`, `validation/views.py`, `graph_analysis(_dormant)`, `portfolio/views.py` 제외 시 실질 23개)
- **방법**: 4개 병렬 read-only 에이전트로 파일별 `Response()` 패턴(래핑/상태코드/에러키/페이지네이션) 추출 후 2026-05-12 정책과 대조
- **코드 변경**: 없음 (읽기 전용)
- **후속 트리거**: P1 WRAP 마이그레이션은 BE+FE 동반 PR 필요 — 별도 슬라이스 권장
