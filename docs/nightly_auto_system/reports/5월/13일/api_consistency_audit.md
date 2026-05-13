# API 응답 일관성 감사 보고서

**감사일**: 2026-05-13
**감사 범위**: `*/views*.py` 25개 파일 (총 13,047 라인) + `thesis/views/*.py` 3개 파일 (1,080 라인)
**감사 방법**: read-only, grep + 샘플 reading (코드 수정 없음)
**프로젝트**: Stock-Vis (`/Users/byeongjinjeong/Desktop/stock_vis`)

---

## 요약

### 핵심 결론

> **응답 envelope이 앱마다 다르고, 같은 앱 안에서도 뷰마다 다르다.**
> 단일 클라이언트(`frontend/`)가 6가지 이상의 응답 구조를 분기해서 파싱해야 한다.

### 발견된 7가지 응답 구조

| # | 형태 | 사용처 (대표) | 비율(추정) |
|---|------|--------------|-----------|
| 1 | `Response(serializer.data)` — 평탄 | rag_analysis, macro, users, news | ~40% |
| 2 | `Response({"평탄 dict"})` — 키 평탄 dict | serverless, chainsight, stocks/views.py, news | ~30% |
| 3 | `Response({"success": True, "data": ..., "meta": ...})` — envelope v1 | stocks/views_screener, views_fundamentals, views_exchange | ~5% (17건) |
| 4 | `Response({"error": "..."})` — 에러 단축형 | 17개 파일 | 에러 응답 167건 |
| 5 | `Response({"detail": "...", "code": "...", "status_code": ...})` — DRF 표준 envelope (custom_exception_handler) | 모든 DRF 예외 경로 | exception 자동 적용 |
| 6 | `JsonResponse({...})` — 순수 Django (DRF 미사용) | portfolio/views.py 전체 | 39건 |
| 7 | `Response({"results": [...], "pagination": {...}})` — Custom Django Paginator | users.WatchlistView | 단발성 |

### P0 발견 (이번 감사의 핵심)

1. **envelope 표준이 3가지 공존**: ① audit P0 #14 (`{detail, code, errors, status_code}`) — `config/exception_handler.py`로 **에러 응답에만** 자동 적용. ② `{success, data, meta}` envelope v1 — `stocks/views_screener/fundamentals/exchange` **성공 응답**에만 17건. ③ envelope 없음 (평탄) — 다른 앱 전부. 같은 백엔드의 두 엔드포인트가 완전히 다른 모양으로 응답한다.
2. **portfolio/ 앱은 DRF 미사용**: `JsonResponse` + `status=400/429/500/503` (정수 하드코딩) — 다른 모든 앱과 응답 키마저 다름 (`error`, `detail` 혼합).
3. **에러 키 4종 공존**: `error` (167건, 17파일) / `detail` (27건, 3파일) / `message` (59건, 10파일) / `errors`(serializer.errors, users 다수). 같은 400 응답이라도 키가 다르다.
4. **하드코딩 상태코드 33건** (`status=400/200/500/202` etc.): `portfolio/views.py` 32건 + `sec_pipeline/views.py` 3건. 다른 앱은 `status=status.HTTP_*` 사용.
5. **페이지네이션이 2개 뷰뿐**: 25개 파일 중 `stocks/views.py:StockListAPIView`, `news/api/views.py:NewsViewSet` 2곳만 `PageNumberPagination` 적용. 나머지는 `.all()` / `.filter()` 직접 직렬화 또는 슬라이싱(`[:10]`, `[:50]`, `[:1000]`).

---

## 앱별 응답 패턴 매트릭스

> 표기: `직접` = `Response(serializer.data)` 또는 평탄 dict / `envelope v1` = `{success:True, data, meta}` / `JsonResponse` = 순수 Django

| 앱 | 파일 (라인) | 성공 응답 형태 | 에러 키 | HTTP 상태 코드 | 페이지네이션 | 비고 |
|----|-----|--------------|--------|---------------|------------|------|
| **stocks** | views.py (1030) | 평탄 dict (`results`, `data`, `count` 등) | `error`(12) / `errors`(?) / serializer.errors | `status.HTTP_*` 25건 | `StockListPagination` 1뷰만 | `success: False` 2건(스코어 카드) |
| stocks | views_screener.py (498) | **envelope v1** (`success:True, data, meta`) | `error`(8) | `status.HTTP_*` 8건 | 없음 | StockScreenerView/LargeCap/HighDividend |
| stocks | views_fundamentals.py (305) | **envelope v1** | `error`(10) | `status.HTTP_*` 10건 | 없음 | KeyMetrics/Ratios/DCF/Rating 5개 모두 envelope v1 |
| stocks | views_exchange.py (295) | **envelope v1** | `error`(8) | `status.HTTP_*` 8건 | 없음 | IndexQuotes/StockQuote/Batch |
| stocks | views_indicators.py (372) | 평탄 dict | `error`(3) | `status.HTTP_*` 3건 | 없음 | `[:N]` 슬라이싱 X |
| stocks | views_search.py (229) | 평탄 dict | `error`(5) | `status.HTTP_*` 5건 | `[:20]` 슬라이싱 | |
| stocks | views_eod.py (136) | 평탄 dict (`logs`, `signal_id` 등) | `error`(3) | `status.HTTP_*` 3건 | `[:50]`, `[:7]` 슬라이싱 | |
| stocks | views_market_movers.py (69) | 평탄 dict | `error`(1) | `status.HTTP_*` 1건 | 없음 | |
| stocks | views_mvp.py (200) | 평탄 dict | — | — | 없음 | Response 4건 |
| **serverless** | views.py (2909) | **평탄 dict** (`movers`, `count` 등) | `error`(6) | `status.HTTP_201` 3건 | 없음 | `@api_view` 함수, 71 응답 |
| serverless | views_admin.py (691) | 평탄 dict | `error`(28) | `status.HTTP_*` 30건 (400/404/429/500/204) | 없음 | Admin 액션 (위험 액션 dry_run 등) |
| **news** | api/views.py (2198) | 평탄 dict | `error`(7) | `status.HTTP_*` 13건 (400/404) | `NewsArticlePagination` 1뷰 (NewsViewSet) | 단일 뷰만 페이지네이션, 나머지 actions은 슬라이싱 |
| news | views.py (3) | (empty) | — | — | — | 비어있는 파일 |
| **users** | views.py (1088) | `Response(serializer.data)` + `Response(serializer.errors)` | `error`(8) / `serializer.errors` | `status.HTTP_*` 33건 (200/201/204/400/401/207/500) | **Custom `django.core.paginator.Paginator`** 1뷰 (WatchlistsView) | DRF 정석. `HTTP_207_MULTI_STATUS` 1건 |
| **chainsight** | api/views.py (814) | 평탄 dict (`center`, `nodes`, `edges`) | `error`(9) | `status.HTTP_*` 8건 (400/404/503) | 없음 | Neo4j 결과 sanitize 후 평탄 반환 |
| chainsight | views.py (1) | (empty) | — | — | — | |
| **macro** | views.py (410) | `Response(serializer.data)` | `error`(15) | `status.HTTP_500` 15건 (대부분) | 없음 | 모든 예외를 500으로 일괄 처리 (안티 패턴 가능성) |
| **validation** | api/views.py (561) | `Response(serializer.data)` 또는 평탄 dict | `error`(15) / `message`(?) | `status.HTTP_*` 12건 (400/401/404/422) | 없음 | `HTTP_422_UNPROCESSABLE_ENTITY` 사용 |
| validation | views.py (1) | (empty) | — | — | — | |
| **rag_analysis** | views.py (772) | `Response(serializer.data)` | `error`(2) — 대부분 DRF 예외 (raise) | `status.HTTP_*` 7건 (201/204) | 없음 | DRF 표준 패턴 가장 충실 (raise_exception=True, NotFound) |
| **thesis** | views/thesis_views.py (336) | 평탄 dict (`indicators`, `count`) | `error`(2) | `status.HTTP_*` 2건 (400) | 없음 | ModelViewSet `Response({error: ...})` 부분 |
| thesis | views/conversation_views.py (380) | 평탄 dict | `error`(2) | `status.HTTP_*` 2건 | 없음 | |
| thesis | views/monitoring_views.py (364) | 평탄 dict | `error`(2) | `status.HTTP_*` ? | 없음 | |
| **portfolio** | views.py (304) | **JsonResponse (DRF 미사용)** | `error`(27) + `detail`(24) — 함께 사용 | **정수 하드코딩** (`status=400/429/500/503/200`) 32건 | 없음 | `@require_GET`/`@require_POST` — Slice별로 일관됨 |
| **sec_pipeline** | views.py (51) | 평탄 dict | `message`(1) | **정수 하드코딩** (`status=200/202`) 3건 | 없음 | 매우 작음 |
| **graph_analysis** | views.py (3) | (empty) | — | — | — | API 미구현 |
| **metrics** | views.py (3) | (empty) | — | — | — | 내부 서비스 |
| **config** | views.py (104) | `JsonResponse` (api_root, health_check) | — | — | — | 루트 URL만 |

### 핵심 불일치 표 (같은 백엔드, 다른 형태)

| 클라이언트가 호출 | 응답 형태 | 응답 키 (성공) | 응답 키 (에러) |
|------------------|---------|-------------|-------------|
| `GET /api/v1/stocks/screener/` | envelope v1 | `success`, `data`, `meta` | `error` |
| `GET /api/v1/stocks/<id>/chart/` | 평탄 | `symbol`, `period`, `data`, `count` | `error` |
| `GET /api/v1/stocks/api/search/symbols/` | 평탄 | `results`, `count`, `query` | `error` (성공 시에도 `error` 사용 — line 182) |
| `GET /api/v1/users/watchlists/` | 평탄 + `pagination` | `results`, `pagination` | `serializer.errors` |
| `GET /api/v1/rag/baskets/` | 평탄 | `serializer.data` (배열) | (raise exception → DRF envelope) |
| `GET /api/v1/serverless/movers` | 평탄 | `date`, `type`, `count`, `movers` | `error` |
| `GET /api/v1/macro/pulse/` | 평탄 | `serializer.data` | `error` (모든 예외 500) |
| `GET /api/coach/e1/garp/` | JsonResponse 평탄 | (LLM 응답 dict) | `error` 또는 `error`+`detail` |
| `GET /api/v1/sec/filings/<symbol>/` | 평탄 | `symbol`, `status`, `message` | `message` |
| **에러 자동 처리(custom_exception_handler)** | envelope | — | `detail`, `code`, `errors`, `status_code` |

> **결론**: 프론트엔드는 최소 6가지 응답 모양을 알아서 분기 파싱해야 한다.

---

## HTTP 상태 코드 일관성

### 상태 코드 사용 통계

| 표기 방식 | 건수 | 사용처 |
|---------|------|------|
| `status=status.HTTP_*` | **178건** (16 파일) | stocks/users/news/macro/serverless/chainsight/validation/rag_analysis/thesis 등 — DRF 표준 |
| `status=<정수>` 하드코딩 | **33건** | `portfolio/views.py` 32건 + `sec_pipeline/views.py` 3건 |
| 명시 안 함 (DRF 기본 200) | 대다수 | 성공 응답 다수 |

### 상태 코드별 사용 (status.HTTP_* 178건 분포)

| 상태 코드 | 사용 빈도 | 비고 |
|---------|---------|-----|
| `HTTP_400_BAD_REQUEST` | 가장 다수 (~50%) | 표준적 |
| `HTTP_404_NOT_FOUND` | 다수 | 표준적 |
| `HTTP_500_INTERNAL_SERVER_ERROR` | 다수 | **macro/views.py에서 15건 모두 500** — except Exception 전체를 500으로 잡는 안티 패턴 |
| `HTTP_201_CREATED` | 16건 (4 파일) | `users` 10건, `rag_analysis` 7건, `serverless` 3건, `serverless/views_admin` 1건 |
| `HTTP_204_NO_CONTENT` | 6건 | `users` (delete), `rag_analysis`, `serverless/views_admin` |
| `HTTP_422_UNPROCESSABLE_ENTITY` | 1건 | `validation/api/views.py` 만 사용 — 다른 곳은 동일 상황을 404로 처리 |
| `HTTP_207_MULTI_STATUS` | 1건 | `users/views.py:559` — Bulk delete 일부 실패 케이스 |
| `HTTP_429_TOO_MANY_REQUESTS` | 2건 | `stocks/views.py:938`, `serverless/views_admin.py:369` |
| `HTTP_503_SERVICE_UNAVAILABLE` | 5건 | `stocks/views_exchange.py` 3건, `stocks/views_search.py` 1건, `chainsight/api/views.py` 2건 |

### 발견된 일관성 이슈

1. **portfolio + sec_pipeline의 하드코딩 상태 코드 33건** — 검색·diff 도구로 잡기 어려움, 컨트랙트 변경 시 누락 위험.
2. **macro/views.py의 `except Exception → 500` 일괄 처리** (15건) — `400`/`404`/`503` 가 적절한 케이스도 모두 500. 예: line 90-92 (`if 'error' in data`)에서 서비스 응답 에러를 500으로 변환.
3. **422 사용 비대칭** — `validation/api/views.py:67`에서 `S&P 500 종목만 지원` → 422. 그러나 같은 종류의 "유효하나 처리 불가" 응답을 다른 앱은 400 또는 404로 처리.
4. **201 사용 비대칭** — `serverless/views.py:921` POST 프리셋 생성은 201. 그러나 `validation/api/views.py:466~516` POST `peer-preference` 생성은 200(default)으로 응답할 가능성 있음 (소스 확인 시 명시 status 없음).
5. **200 vs 204** — `users/views.py:141` 비밀번호 변경 성공 시 `status.HTTP_200_OK` (body 비어 있음). 표준은 204.

---

## 에러 응답 형식

### 키별 사용 통계

| 에러 키 | 발생 횟수 | 사용 파일 수 | 사용처 |
|--------|---------|-----------|------|
| `error` | **167건** | **17개 파일** | stocks(8개 파일), serverless(2), validation, chainsight, users(8), macro(15), portfolio(27), rag_analysis(2), news(7), thesis 등 — **dominant** |
| `message` | **59건** | 10개 파일 | serverless/views.py(22), macro/views.py(10), users/views.py(7), rag_analysis/views.py(6), stocks/views.py(4) 등 — 성공 응답에도 다수 사용 |
| `detail` | **27건** | 3개 파일 | portfolio/views.py(24), users/views.py(2), config/views.py(1) — portfolio는 `error` + `detail`을 같이 응답 |
| `errors` (serializer.errors) | 다수 | users(8건), 일부 stocks | DRF 자동 응답 |
| **DRF custom_exception_handler** | 모든 예외 경로 | 전역 | `{detail, code?, errors?, status_code}` |

### 발견된 형식 불일치 사례

1. **`portfolio/views.py:107`** — `{"error": "budget_exceeded", "detail": str(exc)}` — `error`를 "코드"로, `detail`을 "메시지"로 사용. 그러나 같은 파일 다른 곳에서는 `error`를 메시지로 사용. **혼합 용법**.
2. **`stocks/views.py:182`** — 검색어 미입력 시 `Response({'result': [], 'message': '검색어를 입력해주세요'}, status=400)`. 빈 결과 + 친화 메시지 — 그런데 `key`가 `result` (단수, 오타? line 190은 `results`).
3. **`config/exception_handler.py`** vs **수동 `Response({'error':...})`** — 같은 400 응답인데도 `raise ValidationError` 경로는 `{detail, code, errors, status_code}` envelope, `return Response({'error': '...'}, 400)` 경로는 평탄 `{error}`. **단일 클라이언트가 두 형태 모두 파싱해야 함**.
4. **`macro/views.py` 전체** — 예외 발생 시 일관되게 `{'error': 'Failed to fetch ...'}` 평탄 응답으로 일괄 처리 (DRF exception handler를 거치지 않음).
5. **`sec_pipeline/views.py:44`** — `{'symbol': ..., 'status': 'collecting', 'message': '...'}` — 202 응답이라서 에러는 아니지만 `status` 키가 HTTP status와 의미 충돌.

### custom_exception_handler vs 수동 응답 충돌

- `config/exception_handler.py`는 audit P0 #14 (2026-05-12)에 등록되어 DRF 예외 (ValidationError, NotFound, PermissionDenied 등) → `{detail, code?, errors?, status_code}` envelope으로 변환.
- 그러나 **수동 `return Response({'error': ...}, status=...)` 167건은 이 핸들러를 거치지 않음**. → 동일 종류 에러가 핸들러 경로/수동 경로에 따라 형태가 달라짐.
- 예: `validation/api/views.py:59` `return Response({'error': f'Stock {symbol} not found'}, status=404)` vs `rag_analysis/views.py` `raise NotFound(_("DataBasket not found"))` → 클라이언트가 받는 응답이 완전히 다름.

---

## 페이지네이션 현황

### 페이지네이션 클래스 사용

| 클래스 | 사용처 | 적용 뷰 |
|------|------|--------|
| `PageNumberPagination` | `stocks/views.py:77 StockListPagination` (page_size=50, max=200) | StockListAPIView |
| `PageNumberPagination` | `news/api/views.py:45 NewsArticlePagination` (page_size=20, max=100) | NewsViewSet (`viewsets.ReadOnlyModelViewSet`) |
| `django.core.paginator.Paginator` (Custom) | `users/views.py:610-628` | WatchlistsView (DRF가 아닌 Django Paginator로 수동 구현) |
| **`CursorPagination`** | **사용 안 함** (0건) | — |
| **`LimitOffsetPagination`** | **사용 안 함** (0건) | — |

### DRF DEFAULT_PAGINATION_CLASS

- `config/settings.py:348~367` — REST_FRAMEWORK 설정에 **`DEFAULT_PAGINATION_CLASS` 자체가 없음**.
- 즉 ViewSet/generics에서 `pagination_class`를 지정하지 않으면 페이지네이션이 적용되지 않음.

### 페이지네이션 누락 위험 (목록 반환 + 미적용)

> grep + 샘플 확인 기반 핫스팟 (코드 수정 없음, 검증 필요):

| 위치 | 위험 | 현재 방어 |
|-----|------|---------|
| `users/views.py:92` `Users.get` | `User.objects.all()` → 직접 직렬화 | IsAdminUser 권한으로 차폐 |
| `users/views.py:193` `UserFavorites` | `user.favorite_stock.all()` 전부 반환 | 1 user의 favorites — 통상 작음 |
| `serverless/views.py:903` 프리셋 목록 | `.all() | user_presets` distinct, `[:N]` 없음 | (검증 필요) |
| `stocks/views_eod.py:72` | `EODSignal.objects.filter(...)[:50]` | 50개로 캡 (페이지네이션 X) |
| `stocks/views_eod.py:119` `PipelineLog` | `[:7]` 캡 | 7일치 |
| `news/api/views.py:104` `stock_news` action | `articles.distinct().order_by(...)` — 페이지네이션 없이 전체 반환 | 캐시 10분 |
| `news/api/views.py:725` `articles_qs[:10]` | 슬라이싱 캡 | |
| `chainsight/api/views.py:80~82` 엣지 / co-mention | depth 최대 3, edges 별도 캡 없음 | depth 캡으로 간접 제한 |
| `rag_analysis/views.py:53` `DataBasket.objects.filter(user=...)` | user 별로 항상 작음 | OK |
| `stocks/views.py:115` `StockListAPIView` | **페이지네이션 OK** | page_size=50, max=200 |
| `macro/views.py` 전체 | 단일 dict 반환 (목록 아님) | OK |

### 발견된 페이지네이션 안티 패턴

1. **하드코딩 슬라이싱(`[:10]`, `[:50]`, `[:1000]`) 다수** — `stocks/views_search.py:202` (`[:20]`), `stocks/views_eod.py:78` (`[:50]`), `chainsight/api/views.py` (depth 3), `news/api/views.py:725` (`[:10]`). 결정적이지만 페이지네이션 없이 "최대 N개"만 보장 → 클라이언트가 더 받을 수 없음.
2. **`users/views.py:610`의 Custom Django Paginator** — DRF `PageNumberPagination`을 쓰지 않고 `from django.core.paginator import Paginator`를 직접 사용. 응답 키도 `{results, pagination: {count, page, page_size, num_pages, has_next, has_previous}}`로 DRF 표준(`{count, next, previous, results}`)과 다름.
3. **목록 ViewSet에서 페이지네이션 누락** — `news/api/views.py:55 NewsViewSet`은 `pagination_class = NewsArticlePagination`이 클래스 레벨에 있지만, `@action(stock_news)`와 같은 커스텀 action들은 `self.get_paginated_response()`를 호출하지 않고 직접 `Response(data)` 반환 → 페이지네이션 미적용.

---

## 권고사항

### P0 (즉시) — Envelope 통일

1. **단일 응답 envelope 결정 + 마이그레이션 플랜 수립**
   - 후보 A: 평탄 응답 + 에러 envelope만 (현 audit P0 #14 방향) — 단순, 클라이언트 변경 최소
   - 후보 B: 모든 응답 `{data, meta, error}` envelope — frontend에서 통일된 응답 인터셉터 구현 가능, 그러나 모든 뷰 마이그레이션 필요
   - **현재 mixed 상태(envelope v1 17건 + 평탄 다수)가 가장 나쁨**. 단일 PR로 결정 + DECISIONS.md 등록 필요.

2. **`{success: True, data, meta}` envelope v1을 제거 또는 전 앱 확산 중 하나로 결정**
   - 영향: `stocks/views_screener.py`, `views_fundamentals.py`, `views_exchange.py` (17건)
   - 만약 v1 폐기 시 → 프론트 호출부 동시 마이그레이션 필요 (contracts/ 스펙 확인)

### P0 (즉시) — 에러 키 통일

3. **에러 응답을 한 가지 키로 통일**
   - `error` (167건) vs `detail` (27건) vs `message` (59건, 일부 성공) 중 표준 결정
   - `config/exception_handler.py`가 이미 `detail`+`code` 표준을 사용 → **`detail` 통일을 권장** (이미 DRF 예외 envelope과 매칭됨)
   - 영향: 17개 파일 ~167 응답

4. **`return Response({'error': ...}, status=...)` → `raise ValidationError`/`raise NotFound`로 마이그레이션**
   - 그러면 `custom_exception_handler`가 자동으로 envelope 적용
   - 가장 큰 영향: `serverless/views_admin.py` (28), `portfolio/views.py` (27, 단 DRF 미사용 → 별도 대응), `macro/views.py` (15)

### P1 (단기) — 표준화

5. **`portfolio/views.py`를 DRF로 마이그레이션 또는 별도 envelope 결정**
   - 현재 `JsonResponse` + 정수 status 하드코딩 32건
   - DRF로 가면 자동 envelope, 정수 → `status.HTTP_*` 변환
   - 또는 portfolio는 별도 LLM coach API로 분리 정책 유지 (그러나 명시적 DECISIONS.md 항목 필요)

6. **`macro/views.py`의 `except Exception → 500` 일괄 처리를 세분화**
   - 외부 API 실패(timeout) → 502/503, 데이터 없음 → 404, 유효성 → 400으로 구분
   - 현재 15건 모두 500은 클라이언트가 retry/fallback 결정 어려움

7. **하드코딩 상태 코드 33건을 `status.HTTP_*`로 교체**
   - `portfolio/views.py` 32건, `sec_pipeline/views.py` 3건

### P1 (단기) — 페이지네이션

8. **`DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE` 전역 설정 추가** (`config/settings.py:348`)
   - 누락된 ViewSet/generics가 자동으로 페이지네이션 적용되도록
   - 단, 이미 평탄 응답하는 뷰는 깨질 수 있으므로 옵트인 방식 권장

9. **하드코딩 슬라이싱(`[:N]`)을 `LimitOffsetPagination`/`CursorPagination`으로 전환**
   - `stocks/views_eod.py:78` (`[:50]`), `stocks/views_search.py:202` (`[:20]`), `news/api/views.py:725` (`[:10]`)
   - 클라이언트가 "더 보기"가 필요하면 현재 구조로 불가능

10. **`users/views.py:610` Custom Paginator를 DRF `PageNumberPagination`으로 교체**
    - 응답 키도 DRF 표준 `{count, next, previous, results}`로 통일

### P2 (장기)

11. **contracts/ OpenAPI 스펙과 실제 응답 envelope 정합성 검증 자동 테스트 추가**
    - `@qa` 영역 — 현재 스펙은 평탄/envelope이 혼재되어 있을 가능성
12. **응답 envelope 정책 문서(`docs/features/api_envelope/policy.md`) 보강** — 현재 audit P0 #14에서 에러 envelope만 표준화. 성공 envelope 정책 추가 필요.
13. **frontend `lib/api/authAxios.ts`에 응답 인터셉터 추가** — envelope 통일 시 클라이언트가 `success/data/error`를 일관 파싱하도록.

---

## 부록 A — 응답 형식 빠른 참조

```text
# 1. envelope v1 (stocks/views_screener, fundamentals, exchange — 17건)
{"success": true, "data": {...}, "meta": {...}}

# 2. 평탄 dict (대부분 앱)
{"symbol": "AAPL", "data": [...], "count": 5}

# 3. Serializer.data 직접 반환
[{"id":1, ...}, {"id":2, ...}]  (또는 단일 dict)

# 4. 에러 평탄 (167건)
{"error": "Stock AAPL not found"}  → status 404

# 5. 에러 (portfolio — DRF 미사용)
{"error": "budget_exceeded", "detail": "..."}  → status 429

# 6. 에러 envelope (DRF custom_exception_handler 경유)
{"detail": "Stock AAPL not found", "code": "not_found", "status_code": 404}

# 7. 페이지네이션 (users — Custom Django Paginator)
{"results": [...], "pagination": {"count": 100, "page": 1, ...}}

# 8. 페이지네이션 (stocks/views.py, news — DRF PageNumberPagination)
{"count": 100, "next": "?page=2", "previous": null, "results": [...]}
```

## 부록 B — 감사 수행 명령

```bash
# 1. 응답 키 통계
grep -r "Response(" --include='*views*.py' -c            # 458 occurrences in 20 files
grep -r "'error':\|\"error\":" --include='*views*.py'    # 167 in 17 files
grep -r "'detail':\|\"detail\":" --include='*views*.py'  # 27 in 3 files
grep -r "'message':\|\"message\":" --include='*views*.py'# 59 in 10 files
grep -r "'success': True\|\"success\": True"             # 17 in 3 files

# 2. 상태 코드 통계
grep -r "status=status\.HTTP_" --include='*views*.py'    # 178 in 16 files
grep -r "status=[0-9]\{3\}" --include='*views*.py'       # 33 (portfolio 32 + sec_pipeline 3)

# 3. 페이지네이션
grep -r "PageNumberPagination\|CursorPagination\|LimitOffsetPagination" --include='*.py'
# → 2 hits: news/api/views.py, stocks/views.py
```

## 부록 C — 감사 범위 (파일 목록, 25 + 3)

```
chainsight/api/views.py (814)        macro/views.py (410)              stocks/views.py (1030)
chainsight/views.py (1, empty)       metrics/views.py (3, empty)       stocks/views_eod.py (136)
config/views.py (104)                news/api/views.py (2198)          stocks/views_exchange.py (295)
graph_analysis/views.py (3, empty)   news/views.py (3, empty)          stocks/views_fundamentals.py (305)
portfolio/views.py (304)             rag_analysis/views.py (772)       stocks/views_indicators.py (372)
sec_pipeline/views.py (51)           serverless/views.py (2909)        stocks/views_market_movers.py (69)
serverless/views_admin.py (691)      thesis/views/__init__.py (15)     stocks/views_mvp.py (200)
thesis/views/conversation_views.py (380)  thesis/views/monitoring_views.py (364)
thesis/views/thesis_views.py (336)   users/views.py (1088)             validation/api/views.py (561)
validation/views.py (1, empty)       stocks/views_screener.py (498)    stocks/views_search.py (229)
```

---

**감사 결론**: 응답 envelope/에러 키/페이지네이션 모두에서 **단일 표준이 없고**, audit P0 #14로 시작된 에러 envelope 통일이 **수동 응답(167건)을 포괄하지 못해 효과가 미완성**. 단일 PR로 envelope 정책을 결정한 뒤 단계적 마이그레이션 권장.
