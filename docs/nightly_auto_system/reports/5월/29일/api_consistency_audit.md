# API 응답 일관성 감사 보고서

- 작성일: 2026-05-29
- 대상: 전체 백엔드 view 파일 (35개 발견, 실제 코드 보유 28개)
- 방식: 읽기 전용 정적 분석 (코드 미수정)
- 분석 범위: `Response()` 반환 형식, HTTP 상태 코드, 에러 응답 형식, 페이지네이션
- **선행 정책 존재**: `docs/features/api_envelope/policy.md` (2026-05-12 수립, 직전 `5월/5일` 감사 P1 #14의 결정) — 본 감사는 사실상 **정책 대비 이행 재감사**

---

## 요약

### 핵심 결론

**2026-05-12에 "응답 envelope 폐기 + DRF 평탄 통일" 정책이 수립되었으나, 이행이 부분적으로만 완료된 상태다.** 전역 인프라(PR-0)는 적용됐지만, 개별 view 마이그레이션(PR-A~G)이 미완이라 **3종의 응답 규약이 여전히 공존**한다.

| 영역 | 정책 목표 | 현재 상태 | 판정 |
|------|----------|----------|------|
| **전역 EXCEPTION_HANDLER** | `{detail, code?, errors?, status_code}` 통일 | `config/exception_handler.py` 등록 완료 (`settings.py:372`) | ✅ 완료 (PR-0) |
| **성공 응답 평탄화** | `serializer.data`/dict 직접 반환, `{success,data,meta}` 폐기 | stocks 3개 파일(exchange/fundamentals/screener)에 wrapping 잔존 | ⚠️ 미완 |
| **에러 응답 통일** | `raise` 기반 → 핸들러가 `{detail,code}` 변환 | 수동 `Response({'error':...})` 다수 잔존 — 핸들러 우회 | ⚠️ 미완 |
| **에러를 4xx/5xx로** | HTTP 상태 코드로 에러 표현 | `serverless/views.py`는 에러를 HTTP 200 본문에 실음 (47개 뷰) | ❌ 위반 |
| **페이지네이션** | ViewSet 단위 `PageNumberPagination` | DRF 페이지네이터 거의 미사용, 수동 `Paginator` 2곳뿐 | ⚠️ 미완 |

### 가장 시급한 4가지

1. **`serverless/views.py` (47개 함수 뷰)**: 4xx/5xx를 **단 한 번도 사용하지 않음**. 모든 에러를 `{'error': str(e)}`로 **HTTP 200**에 실어 반환. 클라이언트가 status code로 에러를 분기할 수 없음. (정책 PR-B~F 미이행)
2. **에러 키 3종 혼재**: `{'error':}` (대다수 수동 반환) / `{'detail':}` (DRF 예외 + watchlist_views + rag_analysis) / `error_body` 커스텀 (iron_trading) — 한 파일 안에서도 혼합.
3. **`status` 하드코딩 3개 파일**: `iron_trading/views.py` (전부 bare int), `sec_pipeline/views.py` (200/202), `marketpulse/api/views/cards.py:73` (`status=404`). 나머지는 `status.HTTP_*` 상수.
4. **페이지네이션 부재**: 전역 `DEFAULT_PAGINATION_CLASS` 미설정. `rag_analysis` 리스트 3종·`news` 관리자 로그 2종·`users` admin user 목록이 무제한 쿼리셋 전체 반환 — DoS/페이로드 표면.

### 응답 규약 진영 분포

| 진영 | 형태 | 해당 파일 |
|------|------|----------|
| **A. WRAP (`success/data/meta`)** | `{"success": True, "data": ..., "meta": ...}` | stocks: views_exchange, views_fundamentals, views_screener (정책상 폐기 대상) |
| **B. 평탄 직접 반환** | `serializer.data` 또는 도메인 dict | 그 외 거의 전부 (stocks 나머지 6, thesis, news, rag, macro, users, validation, chainsight, serverless 등) |
| **C. ENVELOPE (`_meta`)** | `{"_meta": {...}, "data"/도메인키: ...}` | marketpulse/api/views/* 5개 (정책상 v2 예외 인정) |

→ 정책 목표는 **B로 통일**(C는 marketpulse v2만 예외 인정). A 진영(stocks 3파일)이 잔존 위반.

---

## 앱별 응답 패턴 매트릭스

| 앱 / 파일 | 성공 래핑 | status 표현 | 201/204 사용 | 에러 키 | 페이지네이션 |
|-----------|----------|------------|-------------|---------|-------------|
| **stocks/views.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ (POST도 200) | `{'error'}` (str/중첩/dict 혼재) + 검색은 `{'message'}` | `StockListAPIView`만 `PageNumberPagination` ✅, 나머지 `[:N]` 슬라이싱 |
| **stocks/views_eod.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ | `{'error'}` str | `[:50]`/`[:7]` 슬라이싱 |
| **stocks/views_exchange.py** | **WRAP(A)** ⚠️ | `status.HTTP_*` ✅ | ❌ | `{'error'}` str | 없음 (외부 API 통째) |
| **stocks/views_fundamentals.py** | **WRAP(A)** ⚠️ | `status.HTTP_*` ✅ | ❌ | `{'error'}` str | `limit` 클램프(≤40) |
| **stocks/views_indicators.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ | `{'error'}` str | `[:50]` 슬라이싱 |
| **stocks/views_market_movers.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ | `{'error'}` str | `limit` 1~20 |
| **stocks/views_mvp.py** | 평탄(`data` 키만) | `status.HTTP_*` ✅ | ❌ | 에러 분기 없음(404만) | `SectorListView` 무상한 distinct ⚠️ |
| **stocks/views_screener.py** | **WRAP(A)** ⚠️ | `status.HTTP_*` ✅ | ❌ | `{'error'}` str/dict | **limit 최대 1000** 무페이징 ⚠️ |
| **stocks/views_search.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ | `{'error'}` + `{'valid':False}` | `[:10]`/15 고정 |
| **serverless/views.py** | 평탄(B) | 201만 사용, **4xx/5xx 전무** ❌ | 201 3곳 | **`{'error'}`를 HTTP 200에** ❌ | 수동 offset 일부, list 통째 |
| **serverless/views_admin.py** | 평탄(B) | `status.HTTP_*` ✅ | 201/204 ✅ | `{'error'}` str | 없음 (categories 통째) |
| **chainsight/api/views.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ | `{'error'}` str | `SignalFeedView`만 수동 페이징 |
| **chainsight/views/watchlist_views.py** | 평탄(`.data`) | `status.HTTP_*` ✅ | 201 ✅ | **`{'detail'}`** (유일하게 detail) | ViewSet 기본(전역 의존) |
| **validation/api/views.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ | `{'error'}`(+message) | 없음 (`peers`만 `[:50]`) |
| **sec_pipeline/views.py** | 평탄(B) | **숫자 하드코딩** (200/202) ⚠️ | ❌ | 에러 키 없음 | 해당 없음 (단건) |
| **thesis/views/conversation_views.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ (POST도 200) | `{'error'}` | `[:12]` 고정 |
| **thesis/views/monitoring_views.py** | 평탄(B) | status 미지정(200) | ❌ | `get_object_or_404`→`{'detail'}` | `[:50]` 고정 |
| **thesis/views/thesis_views.py** | 평탄(B) | `status.HTTP_*` ✅ | close는 200 (ViewSet create는 기본 201) | `{'error'}` + DRF 404 | ViewSet 기본(전역 의존) |
| **news/api/views.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ (generate/rollback/resolve 200) | `{'error'}` + `ValidationError` | ViewSet은 `PageNumberPagination`(20) ✅ / @action은 우회 |
| **news/views.py** | — (스텁) | — | — | — | — |
| **portfolio/api/views.py** | 평탄(`output`/`llm_metadata`) | `status.HTTP_*` ✅ (429/502/500 매핑 정교) | 명시 200 | `{'error'}` (+scope/type) | 해당 없음 (단건 분석) |
| **portfolio/views.py** | — (빈 모듈) | — | — | — | — |
| **rag_analysis/views.py** | 평탄(B) | `status.HTTP_*` ✅ | **201/204 사용** ✅ (가장 RESTful) | **DRF 예외 raise → `{'detail'}`** | 수동 `Paginator` 1곳, 나머지 3종 통째 ⚠️ |
| **macro/views.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ | `{'error'}` 전면 | 없음 (외부 API 고정 크기) |
| **marketpulse/api/views/cards.py** | **ENVELOPE(C)** `_meta`+`data` | **`status=404` 하드코딩** ⚠️ | ❌ | `{'error'}` | `[:30]` 고정 |
| **marketpulse/api/views/health.py** | ENVELOPE(C) `_meta` | status 미지정 | ❌ | IsAdminUser→DRF 403 | 해당 없음 |
| **marketpulse/api/views/i18n.py** | ENVELOPE(C) `_meta` | status 미지정 | ❌ | `_meta.warning` soft | 해당 없음 |
| **marketpulse/api/views/news_refresh.py** | ENVELOPE(C) `_meta` | status 미지정(POST도 200) | ❌ | 없음 | `REFRESH_LIMIT=6` 고정 |
| **marketpulse/api/views/overview.py** | ENVELOPE(C) `_meta` | status 미지정 | ❌ | `_meta.status` soft | 고정 크기 |
| **users/views.py** | 평탄(B) + `{results,pagination}` | `status.HTTP_*` ✅ (201/204/207) | **201/204 사용** ✅ | `{'error'}`/`{'message'}`/raw `serializer.errors` 혼재 | Watchlist 2곳 수동 `Paginator` / admin user·portfolio 무페이징 ⚠️ |
| **users/jwt_views.py** | 평탄(`{user,tokens,message}`) | `status.HTTP_*` ✅ | 201 ✅ (signup) | `{'error'}` 일관 | 해당 없음 |
| **iron_trading/views.py** | 평탄(B) | **숫자 하드코딩** (400/404/503/200) ⚠️ | ❌ | **`error_body()` 커스텀** | 서비스 내부 `limit` |
| **config/views.py** | `JsonResponse` (비DRF) | `JsonResponse` 기본 200 | — | 에러 없음(health) | 해당 없음 |
| **api_request/admin_views.py** | 평탄(B) | `status.HTTP_*` ✅ | ❌ | `{'error': str(e)}` 일관 | 없음 (status dict) |
| **metrics/views.py** | — (빈 스텁) | — | — | — | — |
| **graph_analysis/views.py** | — (빈 스텁, API 미구현) | — | — | — | — |

> 빈 파일: `news/views.py`(render import만), `portfolio/views.py`(legacy 제거 빈 모듈), `metrics/views.py`·`graph_analysis/views.py`(빈 스텁), `chainsight/views.py`·`validation/views.py`(26바이트 스텁 — 실제 코드는 `chainsight/views/watchlist_views.py`·`validation/api/views.py`).

---

## HTTP 상태 코드 일관성

### 1. `status.HTTP_*` 상수 vs 숫자 하드코딩

| 방식 | 파일 |
|------|------|
| **상수 사용 (정상)** | 대다수 — stocks 전체, serverless_admin, chainsight, validation, thesis, news, portfolio, rag, macro, users, jwt, admin_views |
| **숫자 하드코딩 (위반)** | `iron_trading/views.py` (`status=400/404/503/200` 전부 bare int), `sec_pipeline/views.py` (`status=200/202`), `marketpulse/api/views/cards.py:73` (`status=404`) |
| **status 미사용** | `config/views.py` (`JsonResponse`, `status` import만 하고 미사용), marketpulse health/i18n/news_refresh/overview (기본 200) |

→ 하드코딩 3개 파일은 단순 치환으로 정리 가능 (저위험).

### 2. 201 CREATED 일관성

생성/리소스 추가 엔드포인트의 상태 코드가 **파일마다 제각각**:

| 파일 | POST 생성 시 코드 | 판정 |
|------|------------------|------|
| `rag_analysis/views.py` | **201** (4곳) + 삭제 **204** (3곳) | ✅ 모범 |
| `users/views.py` | **201** (signup/portfolio/watchlist/item) + 204 delete + 207 multi | ✅ 모범 |
| `users/jwt_views.py` | **201** (signup) | ✅ |
| `chainsight/.../watchlist_views.py` | **201** (create) | ✅ |
| `serverless/views_admin.py` | 카테고리 생성 **201**, 그러나 `AdminActionView.post`는 생성인데 **200** | ⚠️ 동일 파일 내 불일치 |
| `serverless/views.py` | 201 3곳 (`:921/1221/1525`) | 부분 |
| `news/api/views.py` | generate/rollback/resolve 전부 **200** | ⚠️ |
| `marketpulse/news_refresh.py` | 생성성 POST인데 **200** | ⚠️ |
| `thesis/views/thesis_views.py` | close 액션 **200** (ViewSet create는 DRF 기본 201) | 부분 |
| stocks (POST 3개) | 전부 **200** | ⚠️ (단 조회/동기화 트리거라 의미상 허용 여지) |

### 3. 동일 의미 상황의 코드 불일치

| 상황 | 코드 처리 | 발생 위치 |
|------|----------|----------|
| 외부(FMP) 데이터 없음 | **503** vs **404** 혼용 | exchange는 503, fundamentals/screener/views.py 차트는 404 |
| 비즈니스 상태(데이터 부족) | **422/404**(정상화 완료) vs **200 본문 error**(잔존) | validation은 422/404로 정상화, 그러나 `insufficient_peers`/`no_leader`/LLM parse는 여전히 200 |
| 일반 에러 | **4xx/5xx** vs **200 본문 `{'error'}`** | 대다수는 4xx/5xx, `serverless/views.py` 전체·chainsight `ChainSightTraceView`·serverless `get_keywords`는 200 |

### 4. 에러를 HTTP 200에 싣는 안티패턴 (정책 명백 위반)

| 위치 | 증거 |
|------|------|
| `serverless/views.py` (47뷰) | 4xx/5xx 전무. `{'error': str(e)}`를 status 인자 없이 반환 (`:623`, `:2005/2012/2019`, `:2113`). not-found도 200 빈 배열(`get_keywords :281`) |
| `chainsight/api/views.py` `ChainSightTraceView` | 경로 못 찾음/예외를 200 `{"found": False, "error": ...}`로 (`:213`, `:235`) |
| `validation/api/views.py` | `insufficient_peers`(`:328`), `no_leader`(`:340`), LLM parse 에러(`:544`)를 200으로 |

---

## 에러 응답 형식

### 형식 3종 + α 혼재

| 형식 | 사용처 | 비고 |
|------|--------|------|
| **`{'error': ...}`** (커스텀) | 가장 우세 — stocks 전체, serverless 양쪽, chainsight/api, validation, macro, thesis(일부), news(명시 반환), portfolio, users(일부), jwt, admin_views, marketpulse/cards | `error` **값 타입이 불일치**: str / 중첩 객체 `{code,message,details}`(views.py Overview·RateLimit) / dict(screener·users `serializer.errors`) |
| **`{'detail': ...}`** (DRF 표준) | `chainsight/.../watchlist_views.py`(유일하게 명시적), `rag_analysis`(예외 raise 전면), `get_object_or_404`/권한거부/throttle 자동 응답 | **정책이 지향하는 표준** |
| **`{'message': ...}`** | 에러 아닌 **성공/안내**에 주로 사용 (rag 삭제완료, news 성공) — 단 stocks 검색은 에러를 `message`로 반환(`views.py:184/192`) | 의미 혼선 |
| **`error_body()` 커스텀** | `iron_trading/views.py` (서비스 정의 별도 shape) | 4번째 형식 |

### 전역 핸들러 적용 범위의 함정

`config/exception_handler.py:custom_exception_handler`가 등록되어 있으나(`settings.py:372`), **`raise`된 DRF 예외에만 적용**된다. 즉:

- **raise 경로** (`raise NotFound/ValidationError/PermissionDenied`, `get_object_or_404`) → 핸들러가 `{detail, code, errors?, status_code}`로 표준화 ✅
- **수동 반환 경로** (`return Response({'error':...}, status=4xx)`) → **핸들러를 우회** → `{'error':}` 그대로 나감 ❌

결과적으로 클라이언트는 **같은 앱 내에서도 코드 경로에 따라 최소 3가지 에러 형태**(`{detail,code,status_code}` / `{error}` / `serializer.errors` field dict)를 받는다. 정책 PR-A~G의 핵심이 바로 이 수동 반환을 `raise`로 전환하는 것인데, 미이행.

### 모범 사례

- **`rag_analysis/views.py`**: 도메인 예외 클래스(`CacheError`, `StatsError` 등 `APIException` 서브클래스)를 `raise`하여 핸들러가 `code`까지 자동 부여 — 정책이 의도한 정확한 패턴.
- **`portfolio/api/views.py`**: 도메인 예외(LLMBudgetExceeded/LLMError)를 429/502에 매핑 — 상태 코드 시맨틱이 가장 정교.

---

## 페이지네이션 현황

### 전역 설정

`config/settings.py:354-373` `REST_FRAMEWORK`:
- `DEFAULT_PAGINATION_CLASS`: **미설정** ❌
- `PAGE_SIZE`: **미설정** ❌

→ 전역 기본 페이지네이션이 없으므로, `pagination_class`를 명시하지 않은 모든 ViewSet의 list 액션은 **무페이징 전체 반환**이 된다 (thesis ViewSet 3종이 여기 해당 — 전역 설정 의존인데 설정이 없음 = 실질 무페이징).

### 적용 현황

| 구분 | 위치 |
|------|------|
| **DRF `PageNumberPagination` (정식)** | `stocks/views.py:StockListAPIView`(page_size 50/max 200), `news/api/views.py:NewsViewSet`(page_size 20) — **단 2곳** |
| **수동 `django.core.paginator.Paginator`** | `users/views.py` Watchlist 2곳(`{results,pagination}` 커스텀 형태), `rag_analysis/views.py:UsageHistoryView` |
| **수동 offset/슬라이싱** | serverless(`execute_preset`/`advanced_screener` page_size≤100), chainsight `SignalFeedView`(자체 `has_next`) |
| **`[:N]` 고정 캡** | 대부분의 @action·조회 뷰 (방어는 되나 `count/next/previous` 메타 없음) |

### 무페이징 전체 반환 — 실위험 지점

| 위험도 | 위치 | 증거 |
|--------|------|------|
| 높음 | `stocks/views_screener.py` | limit 최대 **1000건** 단일 응답 (5개 뷰 전부, `:261` 등) |
| 높음 | `rag_analysis/views.py` | `DataBasketListCreateView`(`:52`), `AnalysisSessionListCreateView`(`:379`), `SessionMessagesView`(`:440`) — `.filter()`/`.all()` 전체 직렬화 (사용자별 누적) |
| 높음 | `news/api/views.py` | `collection_logs`(`:1371` `list(qs.values())` 전체), `task_timeline`(`:1923` cutoff 내 전 로그) — 관리자용이나 누적 폭증 |
| 중간 | `users/views.py` | `Users.get`(`:92` `User.objects.all()` admin), portfolio list 전체(`:264`/`:404`), `UserFavorites`(`:193`), `UserInterest`(`:975`) |
| 중간 | `thesis` ViewSet 3종 | 전역 `DEFAULT_PAGINATION_CLASS` 미설정 → 무페이징 |
| 낮음 | `serverless/views_admin.py` categories(`:475`), `serverless` themes(`:2225`)/ETF(`:1877`), `validation` 카탈로그, `stocks/views_mvp.py` SectorListView(`:195` 무상한 distinct) | 집합 크기가 본질적으로 작음 |

---

## 권고사항

> 본 프로젝트는 이미 **2026-05-12 정책(`docs/features/api_envelope/policy.md`)**으로 목표 상태와 PR 분할(PR-0~G)을 정의해 두었다. 따라서 신규 권고보다 **기존 정책의 미이행분 완수**가 핵심이다.

### P0 — 즉시 (보안/계약 위반)

1. **`serverless/views.py` 에러를 4xx/5xx로 전환** (정책 PR-B~F).
   현재 47개 함수 뷰가 모든 에러를 HTTP 200 `{'error': str(e)}`로 반환 → 클라이언트가 성공/실패를 구분 불가. `serverless/exceptions.py`의 `APIException` 서브클래스(정책 §3.2에 이미 설계됨)를 `raise`로 전환. **가장 큰 단일 위반 + FE `screenerService.ts` 동시 수정 필요.**

2. **무페이징 고위험 4곳에 페이지네이션 적용**.
   `screener`(최대 1000), `rag_analysis` 리스트 3종, `news` 관리자 로그 2종. 사용자/시간 누적으로 폭증하는 쿼리셋. 전역 `DEFAULT_PAGINATION_CLASS = PageNumberPagination` + `PAGE_SIZE` 설정 검토(단, WRAP 잔존 엔드포인트의 응답 형태 변경 영향 확인 필요).

### P1 — 단기 (일관성)

3. **stocks WRAP 3파일 평탄화** (정책 PR — A진영 제거).
   `views_exchange.py`·`views_fundamentals.py`·`views_screener.py`의 `{success, data, meta}` → 평탄 반환. 정책상 폐기 대상이며, 이 3파일이 마지막 WRAP 잔존지. FE 호출자(해당 응답 unwrap 로직) 동시 수정.

4. **수동 `Response({'error':...})` → `raise` 전환**.
   핸들러 우회 경로를 제거해 에러 형태를 `{detail, code, status_code}`로 단일화. `rag_analysis`/`portfolio`의 도메인 예외 패턴을 다른 앱에 확산. `iron_trading`의 `error_body` 커스텀도 표준 핸들러로 흡수.

5. **status 하드코딩 3파일 상수화**.
   `iron_trading/views.py`, `sec_pipeline/views.py`, `marketpulse/api/views/cards.py:73` → `status.HTTP_*`. 저위험 단순 치환.

### P2 — 중기 (정합)

6. **생성 엔드포인트 201/204 통일**.
   `news`(generate/rollback/resolve), `serverless_admin:AdminActionView`, `marketpulse:news_refresh`, `thesis:close` 등 생성/삭제 POST의 코드를 `rag_analysis`/`users` 모범 사례에 맞춰 정렬.

7. **외부 데이터 없음 코드 통일**.
   exchange(503) vs fundamentals/screener(404) → 정책에 503/404 기준 명시 후 정렬.

8. **계약 테스트 추가** (정책 §8, PR-G).
   `tests/contracts/test_response_envelope.py`로 에러 envelope·페이지네이션 형태를 회귀 방지. 미이행 상태이므로 추가 시 향후 드리프트 차단.

### 명시적 예외 (변경 불필요)

- `marketpulse/api/views/*`의 `_meta` envelope(C진영): 정책 §9에서 **v2 API contract로 명시적 예외 인정**. 단 `cards.py:73` status 하드코딩은 별개로 수정 권고.
- SSE 스트림 이벤트 페이로드(`rag_analysis` PIPELINE_ERROR/STREAM_ERROR): HTTP 200 + 이벤트 내부 에러로 정책 미적용 대상.
- 빈 스텁(`metrics`, `graph_analysis`): API 미구현이므로 해당 없음.

---

## 부록 — 정책 이행 체크리스트 (PR 기준)

| PR | 내용 | 상태 |
|----|------|------|
| PR-0 | EXCEPTION_HANDLER 등록 + APIException 서브클래스 + ErrorSerializer | ✅ 핸들러 등록 확인 (`settings.py:372`, `config/exception_handler.py`) |
| PR-A | rag_analysis 36건 + ragService interceptor 제거 | ✅(부분) rag_analysis는 도메인 예외 raise 패턴 정착 확인 / FE 미확인 |
| PR-B~F | serverless/views.py 117건 분할 마이그레이션 | ❌ **미이행** (에러 여전히 HTTP 200) |
| PR-G | serverless/views_admin.py + 계약 테스트 | ❌ 계약 테스트 부재 |
| (정책 외) | stocks WRAP 3파일 평탄화 | ❌ WRAP 잔존 |

> 참고: 본 보고서는 정적 분석 기반이며 런타임 응답을 직접 캡처하지 않았다. 라인 번호는 분석 시점 코드 기준으로, 정확한 수정 전 재확인 권장.
