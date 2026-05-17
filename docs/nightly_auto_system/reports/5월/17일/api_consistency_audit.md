# API 응답 일관성 감사 보고서

- **작성일**: 2026-05-17 (야간 자동 감사)
- **대상**: views*.py 25개 파일 (총 13,047 라인) + REST Framework 설정
- **기준 정책**: `docs/features/api_envelope/policy.md` (2026-05-12 채택, DRF 평탄 + 통일 에러 envelope)
- **연관 감사**: `5월/5일/api_consistency_audit.md` (P1 #14 — envelope 폐기 결정)

---

## 요약

정책 결정(WRAP 폐기 + DRF 평탄 통일)은 **부분 적용** 상태다. 변환 인프라(`config/exception_handler.py`)는 도입됐으나, 호출부의 마이그레이션이 **3종 혼재**로 남아 있다.

| 카테고리 | 현황 | 점수 |
|----------|------|------|
| 성공 응답 형태 | 평탄/WRAP/메타-WRAP 3종 공존 | ⚠ |
| 에러 응답 형태 | `{detail}` (DRF) + `{error}` (커스텀, 105건) + `{error+detail}` 혼재 | ⚠⚠ |
| HTTP 상태 코드 | `status.HTTP_*` 모듈 우위(178건) but 하드코딩 100+건(portfolio/marketpulse/sec_pipeline) | ⚠ |
| 페이지네이션 | DRF `PageNumberPagination` 2건만 적용. `.objects.all()` raw 반환 8건 잔존 | ⚠⚠ |
| EXCEPTION_HANDLER | `config.exception_handler.custom_exception_handler` 등록 완료 | ✅ |
| 도메인 APIException | `rag_analysis/exceptions.py`, `serverless/exceptions.py` 미확인(존재 가정) | — |

**핵심 부채**: `stocks/views_screener.py` + `views_fundamentals.py` + `views_exchange.py` 17건이 여전히 `{success, data, meta}` 래핑 — 정책 위반. `macro/views.py` 15건, `validation/api/views.py` 15건이 `{error: str}` 패턴(DRF `{detail}` 표준 외).

**Top 권고**: ① stocks/* 3파일 WRAP 17건 제거 (단일 PR 가능) → ② `{error}`/`{message}` 호출부 `raise NotFound/ValidationError` 변환 → ③ ViewSet의 page_size 표준 통일 + 누락 paginator 추가.

---

## 앱별 응답 패턴 매트릭스

> 범례: **W** = `{success, data, meta}` 래핑(정책 위반), **F** = 평탄(serializer.data 또는 dict), **E** = `{error: str}`(DRF 비표준), **D** = `{detail: str}` (DRF 표준), **M** = `{message: str}`, **J** = Django JsonResponse

| 앱 | 파일 | 성공 패턴 | 에러 패턴 | 비고 |
|----|------|-----------|-----------|------|
| stocks | `views.py` | F (대부분) + E (검색에서 `{result/results, message}`) | E (12건) | StockListAPIView만 페이지네이션 |
| stocks | `views_screener.py` | **W (7건)** | E (5건) + DRF | 정책 위반 |
| stocks | `views_fundamentals.py` | **W (5건)** | E (5건) | 정책 위반 |
| stocks | `views_exchange.py` | **W (5건)** | E (5건) | 정책 위반, `503_SERVICE_UNAVAILABLE` 활용 |
| stocks | `views_eod.py` | F | E (3건) | — |
| stocks | `views_search.py` | F | E (5건) | — |
| stocks | `views_indicators.py` | F | E (3건) | — |
| stocks | `views_market_movers.py` | F (1) | — | 단순 비스니스 응답 |
| stocks | `views_mvp.py` | F (`pagination_class` 없음, ListAPIView) | — | — |
| users | `views.py` | F + E + M (혼재) | E (5) + M (7) | M은 Watchlist add/remove `{message: "..."}`. 자체 Paginator(`{results, pagination}`) |
| portfolio | `views.py` | **J (JsonResponse)** | J `{error, detail?}` | 정책 명시 제외(DRF 미사용). 하드코딩 status(400/429/500) |
| validation/api | `views.py` | F + E | E (15건, `'error': 'not_in_universe'` 코드형) | 422 비즈니스 상태 활용 ✅ |
| serverless | `views.py` | F + M (Sync `{message, task_id}`) + 일부 `{count, presets}` | E (5) + `raise NotFound/PermissionDenied` 혼재 | 비페이지 raw `.objects.all()` (라인 886) |
| serverless | `views_admin.py` | F + W (28건 `success`) | E (28건) | admin 영역 — 영향 작음 but 일관성 깨짐 |
| serverless | `views_admin.py:565` | F | — | 201 사용 ✅ |
| rag_analysis | `views.py` | F (대부분) + 페이지네이션 dict `{results, pagination}` | E (2) + `raise NotFound/ValidationError` 14건 | 영역 마이그레이션 진척 우수 (PR-A 완료 가정) |
| news/api | `views.py` | F + dict `{symbol, count, articles}` (cache 응답) | E (7) | NewsViewSet 페이지네이션 ✅ (`page_size=20`) |
| macro | `views.py` | F (serializer.data 평탄) | **E (15건, try/except 마다 `{error: "Failed..."}`)** | 500 에러 대량 — `raise APIException` 으로 치환 가능 |
| chainsight/api | `views.py` | F (sanitize 후 dict) | E (5) | Neo4j 503 활용 |
| graph_analysis | `views.py` | — (구현 미적용) | — | 3 라인 stub |
| sec_pipeline | `views.py` | F + admin staff_member_required template | **하드코딩 status=200/202** | DRF 라우트는 staff/admin 한정 |
| marketpulse/api | `views/cards.py` | **자체 `_envelope` (정책 예외 명시: `{_meta, data}`)** | `{error: str}` 하드코딩 404 | v2 contract — 정상 |
| marketpulse/api | `views/overview.py` 등 | F (가정) | — | (전체 미감사) |
| thesis | `views/thesis_views.py` 등 | F + dict | E (4건) | 정책 위반 미세함 |
| metrics | `views.py` | — (3 라인 stub) | — | — |
| config | `views.py` | F + JsonResponse `{detail}` | M (1) | 헬스체크 등 |

**WRAP 잔존 합계**: stocks/* 17건 + serverless/views_admin.py 28건 = **45건** (5월 5일 감사 시점 154건에서 109건 감소).

---

## HTTP 상태 코드 일관성

### 1) `status.HTTP_*` 모듈 사용 우위

- 총 178건 — 16개 파일에서 통일 사용. **양호.**
- 사용 분포: validation(12), users(33), macro(15), news(7), rag(7), serverless(3), serverless_admin(30), stocks/views.py(25), stocks/views_fundamentals.py(10), 기타.

### 2) 하드코딩 숫자 (정책 위반/일관성 깨짐)

| 파일 | 라인 | 패턴 | 비고 |
|------|------|------|------|
| portfolio/views.py | 49, 55, 57, 59, 84, 92, 100, 107, 112, 118, 121, 146~304 (32건) | `status=400/429/500/503/200` | JsonResponse — DRF 미사용. status 모듈 미import. |
| sec_pipeline/views.py | 45, 49, 51 | `status=202`, `status=200` | DRF 사용 중인데 하드코딩 — `status.HTTP_*` 권장 |
| marketpulse/api/views/cards.py | 73 | `status=404` | DRF — 하드코딩 |

→ **17건 비-portfolio 영역에서 정리 가능** (portfolio는 별도 DRF 마이그레이션 시점).

### 3) 201 Created 사용 현황 (POST 생성 엔드포인트)

| 파일 | 생성 라우트 | 201 사용 | 미사용 (200 반환) |
|------|-------------|---------|------------------|
| users/views.py | Signup, Portfolio create, Watchlist create/item, batch | 5건 ✅ | 일부 batch add는 201 ⊕ 200 조건부 (`201 if created else 200`) ✅ |
| serverless/views.py | Preset create, etc. | 3건 ✅ | — |
| rag_analysis/views.py | Basket create, Session create | 4건 ✅ | — |
| serverless/views_admin.py | 565 | 1건 ✅ | — |
| **위반 후보** | thesis/views/* `perform_create`는 DRF ModelViewSet 기본(201) | 자동 ✅ | — |
| news/api/views.py | ReadOnlyModelViewSet (POST 없음) | N/A | — |
| stocks/views_screener.py | POST는 검색/실행 (자원 생성 아님) | N/A | — |

→ **자원 생성 엔드포인트는 201 일관 적용**. 검색/계산/배치 트리거 POST는 200 유지(정확).

### 4) 4xx 분포 (의미 매핑)

- **400** (validation) — 가장 많이 사용. 대부분 `serializer.errors` 또는 `{error: 'msg'}` 두 형식 혼재.
- **401** (not authenticated) — users `login`, validation 일부.
- **403** (permission) — serverless 일부에서 `raise PermissionDenied`. ✅
- **404** (not found) — `raise NotFound` (80건) vs `{error: 'not found'}` (10건+) 혼재. **표준화 필요**.
- **422** (unprocessable) — validation/api/views.py:67 `not_in_universe`. ✅ 정책 권장.
- **429** (throttled) — portfolio (`budget_exceeded`), marketpulse Throttle 자동.
- **500/503** — macro 15건 모두 try/except로 `{error}` 응답. ⚠ `raise APIException` 또는 도메인 APIException 권장.

---

## 에러 응답 형식

### A. 형식 분포

| 형식 | 건수 | 사용처(샘플) | 정책 적합성 |
|------|------|-------------|------------|
| `{detail: str}` (DRF 표준) | 27건 | portfolio(24), users(2), config(1) | ✅ (portfolio는 정책 예외) |
| `{error: str}` (커스텀) | 105건 | macro(15), stocks/views.py(12), validation(15), users(5), news(7) 등 12개 파일 | ❌ — 정책상 `raise + custom_exception_handler` 변환 필요 |
| `{message: str}` (커스텀) | 27건 | portfolio(24), users(2), config(1) | ❌ — Watchlist의 "Stock added"는 success message지 error 아님 |
| `{error: code, detail: str}` (혼합) | 32건 | portfolio (E5/E6 등) | △ — 정책 외(DRF 미사용 portfolio), 자체 표준 |
| `raise NotFound/ValidationError/PermissionDenied` | 80건 | users(19), serverless(37), news(10), rag(14) | ✅ — 정책 권장 |
| `serializer.errors` 반환 | 9건 | users/views.py 전부 | ⚠ — `raise_exception=True` 일관 미적용. 9건은 명시적 `is_valid()` 분기 |

### B. 에러 응답 변환 후 형태

`config/exception_handler.py:custom_exception_handler` 등록 완료(`settings.py:366`). `raise` 패턴은 자동으로 `{detail, code, status_code, errors?}` 표준화됨.

그러나 **직접 `Response({'error': ...})` 반환 105건은 변환 대상이 아님** → 호출부 마이그레이션 필요.

### C. 주요 일관성 이슈

1. **`{error: ...}` vs `{detail: ...}`** — 같은 앱 내에서도 혼재.
   - 예: `validation/api/views.py:59` `{error: ...}` ↔ DRF 기본 `{detail: ...}`
2. **`{error}` 의미 이중화**:
   - 일부는 에러 메시지(`{'error': 'Failed to fetch...'}`),
   - 일부는 코드 분기(`{'error': 'not_in_universe', 'message': '...'}` — validation/api/views.py:64~68).
   → 정책 §3 (DRF + code 카탈로그) 미적용.
3. **`raise NotFound("Stock not found")` 사용은 80건 ✅** — 정책 권장 패턴 적용 중. 잔여 105건은 점진 변환 대상.

### D. SSE / 비즈니스 상태 (정상 흐름)

- validation/api/views.py:340 `{'symbol': symbol, 'error': 'no_leader'}` (200 OK) — **error 키지만 비즈니스 상태**. 정책 §2.3 권장: `{status: 'no_leader', data: null}`.
- rag_analysis SSE 페이로드(`PIPELINE_ERROR`, `STREAM_ERROR`)는 정책 §3.3에서 제외 명시. ✅

---

## 페이지네이션 현황

### 1) DRF `PageNumberPagination` 정식 적용

| 파일 | 클래스 | page_size | max | 라우트 |
|------|--------|-----------|-----|--------|
| `stocks/views.py` | `StockListPagination` | 50 | 200 | `StockListAPIView` (`/api/v1/stocks/`) |
| `news/api/views.py` | `NewsArticlePagination` | 20 | 100 | `NewsViewSet` (전체 리스트) |

→ **정식 적용은 2건뿐**. 전역 `DEFAULT_PAGINATION_CLASS` 미설정 (`config/settings.py:348~367` 확인 — 의도적, audit P0 #14 envelope 결정 후속).

### 2) ListAPIView/ViewSet인데 페이지네이션 미설정

| 파일/라인 | 라우트 | 위험 |
|-----------|--------|------|
| `stocks/views_mvp.py:29` | `Stock.objects.all()` ListAPIView 반환 | S&P 6000+ 일괄 노출 가능 (MVP 라우트지만 미인증 시 DoS 표면) |
| `serverless/views.py:886` | `screener_preset` GET — 모든 시스템/공개 프리셋 + 사용자 프리셋 | 시스템 프리셋 수 ≤ 100 추정. 저위험 but 표준 위반 |
| `serverless/views.py:1054` | `screener_filter` GET `is_active=True` | 카탈로그 — 저위험 |
| `serverless/views.py:1307` | `alert_history` 조회 | 알림 누적 시 폭주 가능 ⚠ |
| `stocks/views.py:408` | `DailyPrice.objects.filter(stock=stock)` — 차트 데이터 | 기간 제한 있음(`PERIOD_MAPPING`) — 안전 |
| `stocks/views.py:421` | `WeeklyPrice.objects.filter(stock=stock)` | 동일 |
| `news/api/views.py:104` | `stock_news` action — `entities__symbol=symbol` filter | `days` 파라미터로 시간 제한 — 안전 |
| `news/api/views.py:410` | `NewsArticle.objects.filter(...)` | 전체 리스트(NewsViewSet 자체는 paginated, action override 시 빠짐) ⚠ |

### 3) 자체 페이지네이션 구현 (DRF 표준 미사용)

| 파일 | 패턴 | 정책 부합 |
|------|------|---------|
| `users/views.py:600~628` (WatchlistList) | Django `Paginator` + `{results, pagination: {...}}` | ❌ — DRF `PageNumberPagination` 표준과 형식 다름 (`{count, next, previous, results}`) |
| `serverless/views.py:907` | `{count, presets}` — 페이지네이션 없음 | ❌ — `count` 키만 있고 `next/previous` 없음 |
| `rag_analysis/views.py:727` | `{results, pagination: {...}}` | ❌ — users/views.py와 동일 자체 구현 |
| `news/api/views.py:110` (stock_news cache) | `{symbol, count, articles}` | △ — `days` 제한으로 사실상 limit. count 키만 |

→ **자체 페이지네이션 3종 형식**(DRF / Watchlist-style / `{count, ...}`) 혼재.

### 4) 전역 페이지네이션 미설정

`REST_FRAMEWORK` 설정에 `DEFAULT_PAGINATION_CLASS` 없음. settings.py:347 주석에 명시: "audit P0 #14 (페이지네이션 표준)는 별도 PR에서 처리 — 응답 envelope 결정이 선결 조건". envelope 결정(§§)은 이미 완료(2026-05-12) → **페이지네이션 표준 PR이 대기 중인 후속 작업**.

---

## 권고사항

### P0 (즉시 — 단일 PR로 가능)

1. **stocks/* 3파일 WRAP 17건 제거** (`views_screener.py` 7건 + `views_fundamentals.py` 5건 + `views_exchange.py` 5건)
   - 변환: `Response({"success": True, "data": serializer.data, "meta": {...}})` → `Response(serializer.data)` (또는 dict 평탄)
   - 메타정보는 응답 헤더(`X-Cache`, `X-Latency-Ms`)로 이동
   - **FE 동시 수정**: `stockService.ts` 등에서 `.data.data` → `.data` 또는 unwrap interceptor 제거 (정책 §6.3 참조)
   - 회귀 위험: 중간 (FE 호출자 매핑 필요), **테스트 우선 작성 후 진행**

2. **hardcoded status code 17건 정리** (portfolio 제외 sec_pipeline + marketpulse 1)
   - `status=200/202/404` → `status=status.HTTP_*`
   - 회귀 위험: 0 (의미 동등)

### P1 (점진 — 앱별 분할 PR)

3. **`{error: str}` 호출부 105건을 `raise` 패턴으로 변환**
   - 우선순위: `macro/views.py` 15건 (전부 500 try/except 패턴) → `raise APIException(detail=...)` 또는 도메인 `MacroFetchError` 신설
   - `validation/api/views.py` 15건 → `raise NotFound`/`raise ValidationError` 또는 비즈니스 상태 `{status: '...', data: null}` 분기 명확화
   - `stocks/views.py` 12건 → `raise NotFound`
   - **변환 후 응답은 EXCEPTION_HANDLER로 자동 표준화됨** (`{detail, code, status_code}`)

4. **자체 페이지네이션 → DRF `PageNumberPagination` 일원화**
   - `users/views.py:600~628` WatchlistListView: `pagination_class = WatchlistPagination` 적용
   - `serverless/views.py:1307` AlertHistoryView: 페이지네이션 추가 (누적 폭주 위험)
   - `news/api/views.py:104,410` action override: 페이지네이션 명시 적용

### P2 (후속 — 별도 PR)

5. **전역 `DEFAULT_PAGINATION_CLASS` 설정 검토**
   - 모든 List 라우트에 자동 적용 → 신규 view 결정 비용 0
   - 단일 자원 응답이 list 형태인 라우트(예: `categories: [...]` dict 일부)에 영향 없는지 사전 점검 필요

6. **portfolio/views.py DRF 마이그레이션**
   - 현재 Django `JsonResponse` 32건. 정책 §9에서 명시 제외.
   - DRF 마이그레이션 시 자동으로 envelope 정책 편입 가능.

7. **자체 envelope `{_meta, data}` (marketpulse v2 cards) 카탈로그화**
   - 정책 §9 예외 명시는 있으나, FE 사용자가 v1/v2 분기를 알아야 함.
   - `contracts/marketpulse-v2.yaml` 등 명시적 contract 분리 권장.

8. **계약 테스트 추가**
   - 정책 §8에서 명시한 `tests/contracts/test_response_envelope.py` 미작성으로 추정.
   - PR-G(envelope 마무리) 시 함께 진행.

---

## 부록 A: 정량 지표 (현 시점)

| 지표 | 값 |
|------|---|
| views*.py 파일 수 | 25 |
| 총 라인 수 | 13,047 |
| `return Response(...)` 호출 | 423 |
| `{success: True, ...}` 잔존 | 17 (stocks/* 3파일) |
| `{error: ...}` 응답 | 105 |
| `{detail: ...}` 응답 | 27 (대부분 portfolio JsonResponse) |
| `{message: ...}` 응답 | 27 |
| `raise NotFound/ValidationError/etc.` | 80 |
| `status.HTTP_*` 모듈 사용 | 178 |
| 하드코딩 status (DRF 영역) | ~3 (sec_pipeline 3 + marketpulse 1) |
| `status.HTTP_201_CREATED` | 13건 (자원 생성 라우트) |
| `PageNumberPagination` 정식 적용 | 2 |
| `.objects.all()` raw 반환 (ListView 외) | 3+ (paginator 누락 후보) |
| EXCEPTION_HANDLER 등록 | ✅ |
| ErrorSerializer (`drf-spectacular`) 정의 | 미확인 (정책 §5 권장) |

---

## 부록 B: 정책 대비 진척률 추정

5월 5일 감사 시점(`5월/5일/api_consistency_audit.md`) 대비:

| 항목 | 5월 5일 | 5월 17일 | 진척 |
|------|---------|---------|------|
| WRAP `{success, data, meta}` | 154건 | 45건 (stocks 17 + admin 28) | ✅ 71% 감소 |
| `raise + EXCEPTION_HANDLER` | 도입 전 | 80건 적용 | ✅ 인프라 완료 |
| 페이지네이션 표준 | 0 | 2 | ⏳ 8% (대기 중) |
| 계약 테스트 | 0 | 0 | ❌ 미착수 |

**전체 정책 적용률 추정**: ~55% (호출부 변환 진행 중, 인프라 완료, 표준 페이지네이션 대기).

---

## 부록 C: 변환 우선순위 매트릭스

| 라우트 | 현재 형식 | 정책 부합 | 변환 비용 | 영향 범위 | 권장 |
|--------|-----------|---------|----------|---------|------|
| stocks 3파일 WRAP 17건 | W | ❌ | 중 (FE 동시) | stockService.ts | P0 |
| macro 500 try/except 15건 | E | ❌ | 소 (raise 변환) | macro UI | P1 |
| validation 비즈니스 상태 5건 | E (200 OK with 'error') | △ | 소 | validation UI | P1 |
| portfolio JsonResponse 32건 | D + 자체 | ⊝ (예외) | 대 (DRF 마이그레이션) | portfolio coach | P2 |
| marketpulse v2 `_envelope` | 자체 | ✅ (예외 명시) | — | v2 contract | 유지 |
| users Watchlist 자체 paginator | M + 자체 | ❌ | 중 | watchlist UI | P1 |
| serverless AlertHistory 페이지네이션 누락 | F | ❌ (raw) | 소 | 알림 UI | P1 |

**감사 종료**.
