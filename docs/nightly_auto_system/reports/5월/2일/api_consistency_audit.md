# API 응답 일관성 감사 보고서

- **감사 일자**: 2026-05-02
- **감사 대상**: Stock-Vis Django REST Framework 백엔드
- **감사 범위**: `**/views*.py` (25개) + `thesis/views/*_views.py` (3개) = **28개 파일, 약 14,475 LOC**
- **감사 모드**: 읽기 전용 (코드 수정 없음)
- **감사 도구**: ripgrep, Read
- **이전 감사 대비**: 5/1 보고서(`5월/1일/api_consistency_audit.md`) 이후 `views*.py` 신규 커밋 0건 — **구조적 변동 없음**, 본 감사는 5/1 기준선 재확인 + 정량 갱신

---

## 요약

응답 형식의 4종 envelope(인라인 dict / helper / 직접 반환 / `JsonResponse`)가 동시에 살아 있고, 단일 앱 내에서도 성공·에러 키가 혼재한다. **DEFAULT_PAGINATION_CLASS 미설정 + 페이지네이션 클래스 사용 0회**라는 구조적 결함은 5/1 보고서 이래 그대로 유지되고 있다.

### 핵심 발견 (Top 5)

| # | 발견 | 영향도 | 위치 |
|---|------|--------|------|
| 1 | **DEFAULT_PAGINATION_CLASS 미설정**, 전체 백엔드에서 `paginate_queryset` / `pagination_class` / `*Pagination` import 0회 | 🔴 Critical | `config/settings.py:341-349` + 모든 `views*.py` |
| 2 | **`StockListAPIView`, `NewsViewSet`** 등 list 엔드포인트가 `Stock.objects.all()` / `NewsArticle.objects.all()` 풀 쿼리셋을 직렬화 | 🔴 Critical | `stocks/views.py:75-105`, `news/api/views.py:42-46` |
| 3 | **응답 envelope 4종 공존**: serverless 인라인 `{success, data}` (63회) / rag_analysis `create_success_response()` helper (36회) / 직접 반환(다수) / portfolio `JsonResponse`(12회) | 🟡 High | 앱별 |
| 4 | **에러 키 명칭 무원칙 혼용**: `error` 208회 vs `message` 112회 vs `detail` 9회. DRF 기본 `detail`을 사용하는 곳은 portfolio/users/config 일부뿐 | 🟡 High | 앱별 |
| 5 | **하드코딩 status 숫자 15회**(portfolio:11, sec_pipeline:3, serverless:1) — 그 외는 `status.HTTP_*` 252회로 우세 | 🟢 Medium | `portfolio/views.py`, `sec_pipeline/views.py:37-44`, `serverless/views.py:1` |

### 일관성 점수 (10점 만점)

| 영역 | 점수 | 메모 |
|------|------|------|
| 응답 envelope 표준화 | **3/10** | 4종 공존, 동일 앱 내 혼재 |
| HTTP 상태 코드 표기 | **9/10** | `status.HTTP_*` 252회로 우세, 일부 하드코딩 |
| 201 / 204 사용 일관성 | **5/10** | POST/create 정의 28개 중 201은 14개만 사용(50%) |
| 에러 응답 키 통일 | **2/10** | `error` / `message` / `detail` 무원칙 혼용 |
| 페이지네이션 | **0/10** | 글로벌·로컬 모두 0건 |

---

## 앱별 응답 패턴 매트릭스

> 표기: 🟢 일관됨 · 🟡 부분 일관 · 🔴 혼재 · ❌ 미적용

| 앱/파일 | LOC | 스택 | 성공 envelope | 에러 형식 | 페이지네이션 | 상태 코드 표기 | 비고 |
|---------|-----|------|---------------|-----------|--------------|----------------|------|
| **portfolio/views.py** | 115 | Django pure (`JsonResponse`) | 직접 dict (`{response, metadata}`) 🟢 | `{error, detail}` 🟢 | N/A | **하드코딩 숫자(11회)** 🔴 | DRF 미사용. `error`를 코드(`invalid_provider`), `detail`을 메시지로 분리한 유일한 모듈 |
| **users/views.py** | 1,080 | DRF APIView | 직접 / `{message}` / `serializer.data` 🔴 | `{error}` / `{message}` / `serializer.errors` 직접노출(9회) 혼용 🔴 | 없음 | `status.HTTP_*` (33회) | 동일 view 내 `error`와 `message` 키 혼재 (변종 E) |
| **stocks/views.py** | 1,020 | DRF APIView + `ListAPIView` | 직접 / `{results, count, query}` / 자체 `{results, pagination:{...}}` 수동 dict 🔴 | `{error}` 단순 + nested `{error: {code, message, details}}`(L586) 혼재 | **❌ ListAPIView도 페이지네이션 없음** | `status.HTTP_*` (25회) | `StockListAPIView` 풀쿼리셋 |
| stocks/views_screener.py | 498 | DRF APIView | `{success, data, count}` (큰따옴표 7회) 🟢 | `{error}` 단순 🟡 | 없음 | `status.HTTP_*` (8회) | 성공/에러 envelope 비대칭 |
| stocks/views_fundamentals.py | 305 | DRF APIView | `{success, data}` (큰따옴표 5회) 🟢 | `{error}` 단순 🟡 | 없음 | `status.HTTP_*` (10회) | 성공만 envelope |
| stocks/views_exchange.py | 295 | DRF APIView | `{success, data}` (큰따옴표 5회) 🟢 | `{error}` 단순 🟡 | 없음 | `status.HTTP_*` (8회) | 성공만 envelope |
| stocks/views_indicators.py | 372 | DRF APIView | 직접 (`indicators_data`, `signal_data`) 🟢 | `{error}` 단순 | 없음 | `status.HTTP_*` (3회) | envelope 미사용 |
| stocks/views_eod.py | 136 | DRF APIView | 직접 (`snapshot.json_data`) 🟢 | `{error}` 단순 | 없음 | `status.HTTP_*` (3회) | envelope 미사용 |
| stocks/views_search.py | 229 | DRF APIView | 직접 / `{results, count, query}` / `{result, message}`(오타: `result` 단수) 🟡 | `{error}` 단순, 일부 `{valid, error}` | 없음 | `status.HTTP_*` (5회) | L172의 `'result'`는 다른 곳의 `'results'`와 키 명칭 불일치 |
| stocks/views_market_movers.py | 69 | DRF APIView | 직접 (`serializer.data`) 🟢 | `{error}` 단순 | 없음 | `status.HTTP_*` (1회) | envelope 미사용 |
| stocks/views_mvp.py | 200 | DRF APIView | `{mode, count, data}` 🟡 | (에러 처리 미흡) | `[:20]` 하드 슬라이스 | `status.HTTP_*` (1회) | 자체 envelope 변형 |
| **serverless/views.py** | 3,405 | DRF `@api_view` | `{success: True, data}` (62회) 🟢 | `{success: False, error: {code, message}}` (54회) 🟢 | 없음 | `status.HTTP_*` (56회) + 하드 `status=200` (1회) | **인라인 envelope를 가장 충실히 적용** |
| serverless/views_admin.py | 694 | DRF APIView | 직접 (`data`) 🟢 | `{error}` 단순 🔴 | 없음 | `status.HTTP_*` (30회) | views.py와 envelope 패턴 불일치 |
| **rag_analysis/views.py** | 864 | DRF APIView | `create_success_response(data)` → `{success, data, meta:{request_id, timestamp}}` (36회) 🟢 | `create_error_response(code, message)` → `{success: False, error:{code, message}, meta}` 🟢 | 없음 | `status.HTTP_*` (25회) | **자체 helper 38개 호출, request_id/timestamp 추적 가능** |
| **chainsight/api/views.py** | 804 | DRF APIView | 직접 (`{symbol, categories}`, sanitize_neo4j 결과) 🟢 | `{error}` 단순(5회) + `{symbol, error: 'not_in_universe', message}`(변종 F) 🟡 | 없음 | `status.HTTP_*` (8회) | `error`를 enum 코드와 메시지 두 의미로 동시 사용 |
| chainsight/views.py | 1 | placeholder | — | — | — | — | URL 미연결 |
| **news/api/views.py** | 2,183 | DRF `ReadOnlyModelViewSet` + `@action` | 직접 (`data`, `serializer.data`) 🟢 | `{error}` 단순(7회) | **❌ ViewSet에서도 미적용** | `status.HTTP_*` (7회) | `NewsArticle.objects.all().prefetch_related('entities')` 풀 반환 |
| news/views.py | 3 | placeholder | — | — | — | — | |
| **macro/views.py** | 410 | DRF APIView | 직접 (`serializer.data`) 🟢 | `{error}` 단순(15회) 🟢 | 없음 | `status.HTTP_*` (15회) | envelope 미사용, 가장 단순한 일관성 |
| **validation/api/views.py** | 558 | DRF APIView | 직접 / `{message, ...}` 🟡 | `{error}` 단순 | 없음 | `status.HTTP_*` (11회) | |
| validation/views.py | 1 | placeholder | — | — | — | — | |
| **thesis/views/thesis_views.py** | 333 | DRF `ModelViewSet` (3개) | 직접 (`{indicators, count}`, `{status, thesis_id}`) 🟢 | `{error}` 단순 (한국어 메시지) 🟡 | **❌ ModelViewSet `list()`에 미적용** | `status.HTTP_*` (2회) | |
| thesis/views/conversation_views.py | 380 | DRF APIView | 직접 (`result`, `{issues}`) 🟢 | `{error}` 단순 (한국어) 🟡 | 없음 | `status.HTTP_*` (2회) | |
| thesis/views/monitoring_views.py | 364 | DRF APIView | 직접 (`{thesis, ...}`, `{alerts, unread_count}`) 🟢 | (에러 처리 미흡) | 없음 | (status 명시 거의 없음) | |
| **sec_pipeline/views.py** | 46 | DRF APIView + Admin view | 직접 (`{symbol, status, message}`) 🟢 | (구분된 에러 형식 없음) | N/A | **하드코딩 `status=200/202`(3회)** 🔴 | 비동기 트리거 패턴 |
| **config/views.py** | 104 | Django `JsonResponse` | 직접 (`{message, version, endpoints, ...}`) 🟡 | (에러 처리 미흡) | N/A | (사용 안 함) | API root + health check |
| metrics/views.py | 3 | placeholder | — | — | — | — | |
| graph_analysis/views.py | 3 | placeholder | — | — | — | — | CLAUDE.md에 "API 미구현" 명시 |

### Envelope 패턴 분포 (정량)

| 패턴 | 사용처 | 출현 횟수 | 형식 |
|------|--------|-----------|------|
| **Inline `{'success': True, 'data': ...}`** | `serverless/views.py`, `serverless/views_admin.py` | **63회** (작은따옴표) | 인라인 dict 리터럴 |
| **Inline `"success": True`** | `stocks/views_fundamentals.py` (5), `stocks/views_screener.py` (7), `stocks/views_exchange.py` (5), `rag_analysis/views.py` (1, helper 본체) | **18회** (큰따옴표) | 동일 envelope, 인용부호만 다름 |
| **Helper `create_success_response()` / `create_error_response()`** | `rag_analysis/views.py` 단독 | **36회** | `{success, data/error, meta:{request_id, timestamp}}` |
| **`{'success': False, 'error': {...}}`** | `serverless/views.py`(54), `stocks/views.py`(2) | **56회** | 코드+메시지 nested |
| **직접 반환 (no envelope)** | 나머지 19+ 파일 (`macro`, `news`, `users`, `chainsight`, `thesis`, `stocks/views_indicators.py` 등) | 압도적 다수 | `Response(serializer.data)` 또는 인라인 dict |
| **`JsonResponse` (DRF 미사용)** | `portfolio/views.py`(11), `config/views.py`(2) | **13회** | Django pure |

> **3개의 서로 다른 envelope helper/스타일이 공존**한다 — ① `serverless` 인라인 dict, ② `rag_analysis` helper(`create_success_response`/`create_error_response`만 정의된 단일 모듈), ③ `portfolio` `JsonResponse`. 공통 모듈로 승격된 helper는 **없음**(`shared/responses.py` 또는 유사 파일 부재 확인).

---

## HTTP 상태 코드 일관성

### 1. 상태 코드 표기 방식

| 표기 방식 | 출현 | 분포 |
|-----------|------|------|
| `status=status.HTTP_*` (DRF 모듈) | **252회** | 19개 파일 (thesis 4 포함) |
| `status=<숫자>` (하드코딩) | **15회** | `portfolio/views.py`(11), `sec_pipeline/views.py`(3), `serverless/views.py`(1) |
| 명시 없음 (200 기본) | 다수 | 모든 성공 응답 |

#### 하드코딩 숫자 사용 위치 상세

```
portfolio/views.py  (DRF 미사용으로 from rest_framework import status 부재)
  L43  status=400   (invalid_provider)
  L49  status=503   (LLMBudgetExceededError - GET /coach/e1/garp)
  L51  status=500   (LLMError)
  L53  status=200   (success)
  L78  status=400   (invalid_provider - POST /coach/e5/adjustment)
  L86  status=400   (json parse error)
  L94  status=400   (E5Request validation)
  L101 status=429   (budget_exceeded)        ← 다른 모듈은 503 사용 (불일치)
  L106 status=500   (llm_invocation_failed)
  L112 status=500   (llm_response_schema_mismatch)
  L115 status=200   (success)

sec_pipeline/views.py
  L40  status=202   (collection triggered)   ← HTTP_202_ACCEPTED 미사용
  L44  status=200   (filing available)
  L46  status=200   (default fallback)

serverless/views.py
  (1회, 회의록 형식의 response 내부)
```

> portfolio는 DRF가 아닌 Django `JsonResponse` 기반이라 `from rest_framework import status` 임포트가 부재한 결과. 의도된 결정이라면 `DECISIONS.md`에 명시 필요.

### 2. 상태 코드별 사용 현황

| 상태 코드 | 출현 | 주 사용 위치 | 일관성 |
|-----------|------|--------------|--------|
| **200 OK** | 다수(기본) | 거의 모든 GET | 🟢 |
| **201 Created** | **14회** | `users`(6), `serverless`(3), `serverless_admin`(1), `rag_analysis`(4) | 🔴 POST/create 28개 중 절반만 사용 |
| **202 Accepted** | 1회 | `sec_pipeline/views.py:40` (하드코딩) | 🟡 비동기 패턴 표준 부재 |
| **204 No Content** | **8회** | `users`(4), `serverless_admin`(1), `rag_analysis`(3) | 🟡 DELETE 일부만 사용 |
| **400 Bad Request** | 매우 많음 | 거의 모든 앱 | 🟢 |
| **401 Unauthorized** | 다수 | `users`, `serverless`, `validation` 등 | 🟢 |
| **403 Forbidden** | `serverless` 내부 | `{error: {code: 'FORBIDDEN'}}` | 🟡 다른 앱은 401로 대체 |
| **404 Not Found** | 다수 | `get_object_or_404` 자동 + 명시적 `HTTP_404_NOT_FOUND` 혼재 | 🟢 |
| **429 Too Many Requests** | 1회 | `portfolio/views.py:101` (하드코딩, budget exceeded) | 🔴 동일 의미를 `serverless`/`users`는 `503`으로 처리 |
| **500 Internal Server Error** | 다수 | 거의 모든 try/except | 🟢 |
| **503 Service Unavailable** | 다수 | `chainsight`, `stocks`, `portfolio`(외부 API 실패) | 🟢 |

#### 주요 불일치

- **201 vs 200 (생성 시)**: `users.PortfolioListCreate`·`users.WatchlistCreate`(L631)는 201, 그러나 `users.AddFavorite`·`stocks/views_screener.py` preset 생성 등은 200 — **표준 부재**
- **삭제 시 200 vs 204**: `users.WatchlistDetailItemAPIView.delete`는 204, 그러나 `users.UserViewLogoutAPIView`는 200 + `{ok: ...}`
- **Budget/Rate-limit 의미 충돌**: `portfolio` 429 vs `serverless`/`users` 503

### 3. POST/CREATE 메서드 통계

```
def post(...) / def create(...) 정의:  28회 (8개 파일, thesis 3 포함)
HTTP_201_CREATED 사용:                  14회 (4개 파일)
→ 약 50% 의 POST/create 가 200 반환
```

---

## 에러 응답 형식

### 1. 에러 키 명칭 통계

| 키 | 출현 | 사용 파일 수 | 의미 |
|----|------|--------------|------|
| **`error`** (작은따옴표 + 큰따옴표 합산) | **208회** | 17개 | 가장 일반적인 커스텀 키 |
| **`message`** (양쪽 따옴표 합산) | **112회** | 11개 | envelope 내부 메시지 + 단순 텍스트 |
| **`detail`** (양쪽 따옴표 합산) | **9회** | 4개 (`portfolio`:6, `users`:2, `config`:1) | DRF 표준 키 — **거의 사용되지 않음** |
| **`serializer.errors` 직접 노출** | **9회** | 1개 (`users/views.py`) | DRF ValidationError 원본 그대로 |

> DRF 자체가 던지는 `NotFound`·`ParseError`·`ValidationError` 응답은 `{detail: "..."}` 형식이지만, 본 백엔드의 **커스텀 응답 95% 이상이 `error` 키를 선호**한다. 즉 동일 엔드포인트에서 정상 처리는 `{error: ...}`, DRF 자동 처리는 `{detail: ...}`로 갈리며 클라이언트가 두 키를 모두 읽어야 한다.

### 2. 에러 형식 변종 (총 6종)

#### 변종 A — 단순 문자열 (가장 흔함, `stocks`/`users`/`chainsight`/`macro`/`thesis`/`validation`)

```python
return Response({'error': '...'}, status=status.HTTP_400_BAD_REQUEST)
```

#### 변종 B — 코드+메시지 nested (`serverless/views.py` 54회 표준)

```python
return Response({
    'success': False,
    'error': {'code': 'NOT_FOUND', 'message': f"Preset not found: {preset_id}"}
}, status=status.HTTP_404_NOT_FOUND)
```

#### 변종 C — Helper로 캡슐화 (`rag_analysis/views.py`)

```python
return Response(
    create_error_response("INVALID_INPUT", str(serializer.errors)),
    status=status.HTTP_400_BAD_REQUEST
)
# → {success: False, error: {code, message}, meta: {request_id, timestamp}}
```

#### 변종 D — 상세 details 추가 (`stocks/views.py:586-596`)

```python
return Response({
    'error': {
        'code': 'OVERVIEW_ERROR',
        'message': '...',
        'details': {'symbol': symbol, 'original_error': str(e), 'can_retry': True}
    }
}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

#### 변종 E — `message` 키 단독 (`users/views.py:207-208`)

```python
return Response(
    {"message": "This stock is already in your favorites"},
    status=status.HTTP_400_BAD_REQUEST
)
```

> `users/views.py`는 동일 400 응답을 `error` 키와 `message` 키 둘 다 사용한다. 클라이언트는 두 키를 모두 파싱해야 한다.

#### 변종 F — `error: <코드 문자열>` (`chainsight/api/views.py`)

```python
return Response({
    'symbol': symbol,
    'error': 'not_in_universe',
    'message': '현재 S&P 500 종목만 지원합니다.',
})
```

> `error`가 **에러 코드 enum**으로 사용되어, 변종 A·D의 `error: <메시지>` 와 의미가 충돌한다. 동일 키 이름이 모듈에 따라 "메시지" 또는 "코드"로 해석되는 구조.

#### 변종 G — `{error, detail}` 분리 (`portfolio/views.py` 단독)

```python
return JsonResponse(
    {"error": "invalid_provider", "detail": f"{provider!r} not in {list(_VALID_PROVIDERS)}"},
    status=400,
)
```

> `error`=코드, `detail`=메시지로 깔끔히 분리된 유일한 모듈. 다만 portfolio만 이 패턴을 사용.

### 3. `serializer.errors` 직접 노출 (보안/UX)

`users/views.py`에 9건 — `Response(serializer.errors, status=400)` 형식으로 DRF 검증 에러 원본을 그대로 노출한다. 다른 앱(`rag_analysis`)은 `create_error_response("INVALID_INPUT", str(serializer.errors))`로 envelope에 흡수. 형식 불일치.

---

## 페이지네이션 현황

### 1. DRF 글로벌 설정 (변경 없음)

```python
# config/settings.py:341-349 (현재 상태)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    # ❌ DEFAULT_PAGINATION_CLASS 미설정
    # ❌ PAGE_SIZE 미설정
    # ❌ EXCEPTION_HANDLER 미설정
    # ❌ DEFAULT_RENDERER_CLASSES 미설정
}
```

### 2. 페이지네이션 사용 검색 결과

```
검색어:   PageNumberPagination | LimitOffsetPagination | CursorPagination
         | paginate_queryset | pagination_class
대상:    전체 코드베이스 (.py)
결과:   ❌ 0건
```

> **백엔드 어디에도 DRF 페이지네이션 클래스를 import 하거나 사용하지 않는다.** 5/1 보고서 이후 변동 없음.

### 3. 페이지네이션 없이 풀 쿼리셋을 반환하는 위험 엔드포인트

| 위치 | 클래스 | 쿼리셋 | 위험도 |
|------|--------|--------|--------|
| `stocks/views.py:75-105` | `StockListAPIView(generics.ListAPIView)` | `Stock.objects.all()` (sector/min_market_cap 옵션 필터) | 🔴 SP500 + 모든 종목 풀 반환 |
| `news/api/views.py:42-46` | `NewsViewSet(viewsets.ReadOnlyModelViewSet)` | `NewsArticle.objects.all().prefetch_related('entities')` | 🔴 **모든 뉴스 기사 풀 반환** |
| `news/api/views.py @action stock_news / keywords/all 등` | DRF action | DB 필터 후 직접 직렬화 | 🟡 일부는 days 제한, 일부 미제한 |
| `thesis/views/thesis_views.py:25,146,189` | `ThesisViewSet`/`ThesisPremiseViewSet`/`ThesisIndicatorViewSet` (`ModelViewSet`) | 자동 list 액션 (queryset에 따라 풀 반환) | 🔴 사용자 가설 누적 시 풀 반환 |
| `stocks/views_screener.py` | DRF view (presets list) | `ScreenerFilter.objects.filter(is_active=True)` | 🟡 활성 필터 전체 |
| `validation/api/views.py` | DRF view (presets list) | preset 전체 | 🟢 사용자별 개수 적음 |
| `users/views.py` Watchlist/Portfolio/Favorites list | DRF view | `request.user`로 스코프 | 🟢 사용자별 (위험 낮음) |

> `views*.py` 안의 `.objects.all()` / `.objects.filter()` 호출은 합산 **174회**(166 + 7 + 1). 이 중 적지 않은 수가 list endpoint에서 발생.

### 4. ListAPIView/ViewSet 사용 정리

| 클래스 | 출현 | 위치 | 페이지네이션 |
|--------|------|------|--------------|
| `generics.ListAPIView` | 1회 | `stocks/views.py:75 StockListAPIView` | ❌ |
| `viewsets.ReadOnlyModelViewSet` | 1회 | `news/api/views.py:42 NewsViewSet` | ❌ |
| `viewsets.ModelViewSet` | 3회 | `thesis/views/thesis_views.py:25,146,189` | ❌ |
| **APIView 기반 (직접 list 구현)** | 압도적 다수 | 모든 앱 | 자체 페이지네이션도 없음 |

> 5건의 list-style 클래스 모두에서 `pagination_class` 미지정. 게다가 **APIView 기반 list 엔드포인트**는 `paginate_queryset()` 헬퍼도 호출하지 않으므로 글로벌 설정만 켜도 자동 적용되지 않는다 — 별도 마이그레이션 필요.

### 5. 수동 페이지네이션 흔적

```python
# stocks/views.py:609-614 (예시)
return Response({
    'results': serializer.data,
    'pagination': {
        ...  # 수동 dict
    }
})
```

> 표준 클래스 미사용 → 응답 형식이 또 다른 변종을 만들어 클라이언트 파싱 부담 가중.

---

## 권고사항

### P0 (즉시 — Critical)

1. **`config/settings.py REST_FRAMEWORK` 에 페이지네이션 글로벌 설정 추가**
   ```python
   'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
   'PAGE_SIZE': 50,
   ```
   - 즉시 적용 대상: `news/api/views.py NewsViewSet`(전체 뉴스), `stocks/views.py StockListAPIView`, `thesis/views/thesis_views.py` 의 3개 ViewSet — 글로벌 설정만으로 `list()` 자동 페이지네이션
   - 단, **APIView 기반 list 구현은 별도 적용 필요** (PR-#5 / PROGRESS.md 항목과 직결)

2. **APIView 기반 무제한 응답 4건 정리** (PROGRESS.md 67행 항목 그대로 유지 중)
   - `NewsViewSet` 직접 List, `StockListAPIView`, `users.get`, `UserFavorites` — 회귀 영향 큼, 별도 PR 권장

### P1 (단기 — High)

3. **응답 envelope 단일 표준 채택 → 공유 모듈로 승격**
   - 후보 비교
     | 후보 | 강점 | 약점 |
     |------|------|------|
     | (A) `serverless` 인라인 `{success, data, error:{code,message}}` | 코드 변경 적음, 가독성 | request_id 추적 불가, 다른 앱 적용 시 보일러플레이트 |
     | (B) `rag_analysis` helper `create_success_response()` + `meta:{request_id, timestamp}` | 디버깅 시 트레이싱 결정적, 일관성 | 도입 시 모든 view 수정 |
   - **권장**: (B)안을 `shared/responses.py` (또는 `core/responses.py`)로 이전 후 모든 앱에서 import. 동시에 (A)의 `error:{code, message}` nested 구조 유지.

4. **에러 키 명칭 통일**
   - 표준: envelope 안 `error: {code: <ENUM>, message: <human readable>}`
   - 단순 `error: '<message>'`(변종 A) 사용처를 위 형식으로 마이그레이션
   - `chainsight`의 변종 F(`error: '<코드>'`)는 자연스럽게 `error.code`로 흡수
   - `users/views.py`의 `Response(serializer.errors, status=400)` 9곳을 `error.code='VALIDATION_ERROR', error.message=str(...)` 로 래핑

5. **HTTP 상태 코드 표기 통일**
   - 모든 `status=<숫자>`를 `status.HTTP_*` 로 전환 (15회 대상 위치는 위 표 참고)
   - **portfolio**가 DRF 미사용 결정이라면 `DECISIONS.md`에 명시 (현재 미기재)
   - **portfolio L101의 `429`** vs serverless/users의 `503` (둘 다 budget/rate-limit 의미) → 의미 결정 필요

### P2 (중기 — Medium)

6. **POST/create 메서드의 201/200 정책 결정**
   - 현재 28개 중 14개만 201 → 가이드 부재
   - 권장: "신규 리소스 생성 → 201", "트리거/액션 → 200 또는 202"
   - 우선 대상: `users.AddFavorite`, `stocks/views_screener.py` preset 생성, `sec_pipeline.FilingDataView`(202를 명시적 `HTTP_202_ACCEPTED`로)

7. **`stocks/views_search.py` 키 일관성**
   - L172의 `'result'`(단수) vs 다른 곳 `'results'`(복수) — 클라이언트 파싱 오류 위험

8. **DRF Custom Exception Handler 도입**
   - `REST_FRAMEWORK['EXCEPTION_HANDLER']` 미설정 → DRF 자동 응답이 `{detail: ...}`로 떨어져 키 일관성을 깨뜨림
   - envelope 변환기 등록 시 `NotFound`·`ValidationError`·`ParseError`·`PermissionDenied` 자동으로 표준 envelope으로 흡수 → view 안 try/except 보일러플레이트 대폭 감소

### P3 (장기 — Low)

9. **응답 일관성 회귀 테스트**
   - `tests/api_consistency/` 디렉터리 신설
   - Snapshot 테스트로 각 endpoint 응답 키 셋 검증
   - CI 게이트: 새 view 추가 시 envelope 표준 위반 차단

10. **빈 placeholder views 정리**
    - `chainsight/views.py`(1줄), `validation/views.py`(1줄), `news/views.py`(3줄), `metrics/views.py`(3줄), `graph_analysis/views.py`(3줄)
    - URL 라우팅 확인 후 삭제 또는 `# DEPRECATED: see <path>` 명시

11. **`StockListAPIView` vs `StockDetailView` 스택 통일**
    - 같은 `stocks/views.py` 안에 DRF `APIView`/`generics.*` + Django `DetailView` (HTML 템플릿) 공존 → 단일 책임 분리 검토

---

## 부록 — 통계 한눈에

```
총 views 파일:                            28개 (views*.py 25 + thesis/views/ 3)
총 LOC:                                   14,475
Response() 호출:                           513회
DRF status 모듈 (status.HTTP_*):           252회
하드코딩 status 숫자:                       15회 (portfolio:11, sec_pipeline:3, serverless:1)

{success: True, data: ...} (작은따옴표):   63회 (serverless 62 + serverless_admin 1)
{"success": True, ...}    (큰따옴표):     18회 (stocks/views_fundamentals/screener/exchange + rag_analysis 1)
{success: False, ...}                     56회 (serverless 54 + stocks 2)
create_success_response()/error_response()  36회 (rag_analysis 단독)

'error' 키 사용 (양쪽 따옴표 합산):        208회
'message' 키 사용:                        112회
'detail' 키 사용:                          9회
serializer.errors 직접 노출:               9회 (users 단독)
JsonResponse 사용:                         13회 (portfolio 11 + config 2)

HTTP_201_CREATED 사용:                    14회
HTTP_204_NO_CONTENT 사용:                  8회
def post / def create 정의:               28회
→ 201 사용률 약 50%

페이지네이션 클래스 사용:                  0회 ⚠️
DEFAULT_PAGINATION_CLASS in settings:     ❌ 미설정
DEFAULT_RENDERER_CLASSES:                 ❌ 미설정
EXCEPTION_HANDLER:                        ❌ 미설정
generics.ListAPIView:                      1회 (페이지네이션 없음)
ReadOnlyModelViewSet:                      1회 (페이지네이션 없음)
ModelViewSet:                              3회 (thesis, 페이지네이션 없음)
.objects.all() / .filter() in views:       174회
```

---

**감사 결론**: 5/1 감사 이래 `views*.py` 변경 0건 — 모든 핵심 결함(envelope 4종 공존, 페이지네이션 0%, 에러 키 무원칙)이 **그대로 유지**되고 있다. P0 항목(글로벌 페이지네이션 + 무제한 응답 4건)은 데이터 누적 시 즉시 P&L 영향이 발생할 수 있어 단기 우선 처리를 다시 권고한다. P1(envelope 단일 helper 승격, 에러 키 표준화)은 클라이언트 코드 단순화와 디버깅 가능성(`request_id`) 측면에서 ROI가 가장 큰 작업이다.
