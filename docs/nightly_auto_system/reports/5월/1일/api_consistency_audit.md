# API 응답 일관성 감사 보고서

- **감사 일자**: 2026-05-02
- **감사 대상**: Stock-Vis Django REST Framework 백엔드
- **감사 범위**: `**/views*.py` (총 25개 파일, 약 14,485 LOC)
- **감사 모드**: 읽기 전용 (코드 수정 없음)
- **감사 도구**: Grep (ripgrep), Read

---

## 요약

Stock-Vis 백엔드의 API 응답 형식은 **앱별·파일별로 4종 이상의 패턴이 혼재**하며, 단일 앱 내부에서도 성공 응답과 에러 응답이 다른 패턴을 사용하는 사례가 다수 발견되었다.

### 핵심 발견 (Top 5)

| # | 발견 | 영향도 | 위치 |
|---|------|--------|------|
| 1 | **DEFAULT_PAGINATION_CLASS 미설정 + 전체 코드베이스에서 paginate_queryset / pagination_class 사용 0회** | 🔴 Critical | `config/settings.py:341-349` + 모든 `views*.py` |
| 2 | `StockListAPIView`, `NewsViewSet` 등 **ListAPIView/ModelViewSet에 페이지네이션 없이 `.objects.all()` 반환** | 🔴 Critical | `stocks/views.py:75-105`, `news/api/views.py:42-46` |
| 3 | **응답 envelope 형식 4종 혼재**: `{success, data}`(serverless), `create_success_response()`(rag_analysis), 직접 반환(다수), `JsonResponse`(portfolio) | 🟡 High | 앱별 |
| 4 | **에러 키 명칭 불일치**: `error` 204회 / `message` 112회 / `detail` 9회 — DRF 기본(`detail`)과 다른 커스텀 형식이 우세 | 🟡 High | 앱별 |
| 5 | **HTTP 상태 코드 표기 불일치**: `status.HTTP_*` 248회 vs **하드코딩 숫자 15회**(`portfolio`:11, `sec_pipeline`:3, `serverless`:1) | 🟢 Medium | `portfolio/views.py`, `sec_pipeline/views.py`, `serverless/views.py` |

### 일관성 점수 (10점 만점)

| 영역 | 점수 | 메모 |
|------|------|------|
| 응답 envelope | **3/10** | 4종 패턴 공존, 동일 앱 내 혼재 |
| HTTP 상태 코드 (사용 모듈) | **9/10** | `status.HTTP_*` 248회로 우세, 일부 하드코딩 |
| 201/204 사용 | **5/10** | POST 메서드 27개 중 201은 14개만 사용(절반) |
| 에러 응답 키 | **2/10** | `error`/`message`/`detail` 무원칙 혼용 |
| 페이지네이션 | **0/10** | 전혀 적용되지 않음 |

---

## 앱별 응답 패턴 매트릭스

> 표기: `🟢` 일관됨 · `🟡` 부분 일관 · `🔴` 혼재

| 앱/파일 | LOC | 스택 | 성공 envelope | 에러 형식 | 페이지네이션 | 상태 코드 표기 | 비고 |
|---------|-----|------|---------------|-----------|--------------|----------------|------|
| **portfolio/views.py** | 115 | Django (DRF 미사용) | 직접 dict | `{error, detail}` | N/A | **하드코딩 숫자(11회)** 🔴 | 유일한 비-DRF 모듈, JsonResponse 사용 |
| **users/views.py** | 1,080 | DRF APIView | 직접/`{message}`/`serializer.data` | `{error}` `{message}` `serializer.errors` 혼용 🔴 | 없음 | `status.HTTP_*` | 동일 view 내 `error`와 `message` 혼재 |
| **stocks/views.py** | 1,020 | DRF APIView + `ListAPIView` | 직접/`{results, count, query}`/nested `{error: {code, message}}` 🔴 | `{error}` 위주, 일부 `{error: {code, message, details}}` | **없음 (ListAPIView)** 🔴 | `StockListAPIView`(75행)은 풀 쿼리셋 직렬화 |
| stocks/views_screener.py | 498 | DRF APIView | `{success, data, count}` 🟢 | `{error}` 단순 🟡 | 없음 | `status.HTTP_*` | 성공/에러 envelope 비대칭 |
| stocks/views_fundamentals.py | 305 | DRF APIView | `{success, data}` 🟢 | `{error}` 단순 🟡 | 없음 | `status.HTTP_*` | 성공만 envelope |
| stocks/views_exchange.py | 295 | DRF APIView | `{success, data}` 🟢 | `{error}` 단순 🟡 | 없음 | `status.HTTP_*` | 성공만 envelope |
| stocks/views_indicators.py | 372 | DRF APIView | 직접 (`indicators_data`, `signal_data`) 🟢 | `{error}` 단순 | 없음 | `status.HTTP_*` | envelope 미사용 |
| stocks/views_eod.py | 136 | DRF APIView | 직접 (`snapshot.json_data`) 🟢 | `{error}` 단순 | 없음 | `status.HTTP_*` | envelope 미사용 |
| stocks/views_search.py | 229 | DRF APIView | 직접 / `{results, count, query}` 혼재 🟡 | `{error}` 단순, 일부 `{valid, error}` | 없음 | `status.HTTP_*` | |
| stocks/views_market_movers.py | 69 | DRF APIView | 직접 (`serializer.data`) 🟢 | `{error}` 단순 | 없음 | `status.HTTP_*` | envelope 미사용 |
| stocks/views_mvp.py | 200 | DRF APIView | `{mode, count, data}` 🟡 | (에러 처리 미흡) | `[:20]` 슬라이스 | (에러 미사용) | 자체 envelope 변형 |
| **serverless/views.py** | 3,405 | DRF APIView | `{success, data}` (62회) 🟢 | `{success: False, error: {code, message}}` (54회) 🟢 | 없음 | `status.HTTP_*` (1회 하드코딩 200) | **표준 envelope 가장 충실히 적용** |
| serverless/views_admin.py | 694 | DRF APIView | 직접 (`data`) 🟢 | `{error}` 단순 🔴 | 없음 | `status.HTTP_*` | views.py와 envelope 패턴 다름 |
| **rag_analysis/views.py** | 864 | DRF APIView | `create_success_response(data)` → `{success, data, meta:{request_id, timestamp}}` 🟢 | `create_error_response(code, message)` → `{success: False, error:{code, message}, meta}` 🟢 | 없음 | `status.HTTP_*` | **자체 envelope helper 사용** |
| **chainsight/api/views.py** | 804 | DRF APIView | 직접 (`{symbol, categories}`, sanitize_neo4j 결과) 🟢 | `{error}` 단순, 일부 `{symbol, error: 'code', message}` 🟡 | 없음 | `status.HTTP_*` | envelope 미사용, error를 enum-like 코드로 사용 |
| chainsight/views.py | 2 | (빈 파일) | — | — | — | — | placeholder |
| **news/api/views.py** | 2,183 | DRF `ReadOnlyModelViewSet` + `@action` | 직접 (`data`, `serializer.data`) 🟢 | `{error}` 단순 | **없음 (ViewSet에서도 미적용)** 🔴 | `status.HTTP_*` | `NewsArticle.objects.all()` 풀 반환 |
| news/views.py | 4 | (빈 파일) | — | — | — | — | placeholder |
| **macro/views.py** | 410 | DRF APIView | 직접 (`serializer.data`) 🟢 | `{error}` 단순 🟢 | 없음 | `status.HTTP_*` | envelope 미사용, 가장 단순 |
| **validation/api/views.py** | 558 | DRF APIView | 직접 / `{message, ...}` 혼재 🟡 | `{error}` 단순 | 없음 | `status.HTTP_*` | |
| validation/views.py | 2 | (빈 파일) | — | — | — | — | placeholder |
| **thesis/views/thesis_views.py** | 333 | DRF `ModelViewSet` | 직접 (`{indicators, count}`, `{status, thesis_id}`) 🟢 | `{error}` 단순 (한국어 메시지) 🟡 | 없음 | `status.HTTP_*` | |
| thesis/views/conversation_views.py | 380 | DRF APIView | 직접 (`result`, `{issues}`) 🟢 | `{error}` 단순 (한국어) 🟡 | 없음 | `status.HTTP_*` | |
| thesis/views/monitoring_views.py | 364 | DRF APIView | 직접 (`{thesis, ...}`, `{alerts, unread_count}`) 🟢 | (에러 처리 미흡) | 없음 | `status.HTTP_*` | |
| **sec_pipeline/views.py** | 46 | DRF APIView + Admin view | 직접 🟢 | `{symbol, status, message}` (에러 명시 없음) | N/A | **하드코딩 숫자(3회)** 🔴 | `status=200`, `status=202` |
| **config/views.py** | 104 | Django JsonResponse | 직접 (`{message, version, endpoints, ...}`) 🟡 | (에러 처리 미흡) | N/A | (사용 안 함) | API root + health check |
| metrics/views.py | 3 | (빈 파일) | — | — | — | — | placeholder |
| graph_analysis/views.py | 3 | (빈 파일) | — | — | — | — | placeholder, CLAUDE.md에 "API 미구현" 명시 |

### Envelope 패턴 분포 (정량)

| Envelope 패턴 | 사용처 | 출현 횟수 |
|--------------|--------|-----------|
| **`{success: True, data: ...}`** (표준 envelope) | `serverless/views.py`(62), `stocks/views_screener.py`/`views_fundamentals.py`/`views_exchange.py` 등 (1) | **63회** (2개 파일) |
| **`{success: False, error: {code, message}}`** | `serverless/views.py`(54), `stocks/views.py`(2) | **56회** (2개 파일) |
| **`create_success_response()` / `create_error_response()` helper** (envelope + meta) | `rag_analysis/views.py` | 38+ 회 (단일 파일) |
| **직접 반환 (no envelope)** | 나머지 19+ 파일 | 압도적 다수 |
| **`JsonResponse` 직접** | `portfolio/views.py`, `config/views.py` | 12+ 회 |

> **3개의 서로 다른 envelope helper/스타일이 공존**한다: ① `serverless` 인라인 dict, ② `rag_analysis` `create_success_response()`, ③ `portfolio` `JsonResponse`. 공통 helper로 통합되지 않음.

---

## HTTP 상태 코드 일관성

### 1. 상태 코드 표기 방식

| 표기 방식 | 출현 횟수 | 분포 |
|-----------|-----------|------|
| `status=status.HTTP_*` (DRF 모듈) | **248회** | 16개 파일 |
| `status=<숫자>` (하드코딩) | **15회** | `portfolio/views.py`(11), `sec_pipeline/views.py`(3), `serverless/views.py`(1) |
| 명시 없음 (200 기본) | 다수 | 모든 성공 응답 |

#### 하드코딩 숫자 사용 위치

```
portfolio/views.py
  - status=400 (3회)  → HTTP_400_BAD_REQUEST와 등가
  - status=429 (1회)  → HTTP_429_TOO_MANY_REQUESTS와 등가
  - status=500 (3회)  → HTTP_500_INTERNAL_SERVER_ERROR
  - status=503 (1회)  → HTTP_503_SERVICE_UNAVAILABLE
  - status=200 (3회)  → 명시적 200

sec_pipeline/views.py
  - status=200 (2회)
  - status=202 (1회)  → HTTP_202_ACCEPTED 미사용

serverless/views.py
  - status=200 (1회)
```

> portfolio는 DRF 미사용(JsonResponse)이므로 `from rest_framework import status` 임포트가 부재하다. DRF 모듈로 전환해야 일관됨.

### 2. 상태 코드별 사용 현황

| 상태 코드 | 출현 | 사용 위치 | 일관성 평가 |
|-----------|------|-----------|------------|
| **200 OK** | 다수 (기본) | 거의 모든 GET | 🟢 |
| **201 Created** | 14회 | `users`(6), `serverless`(3), `serverless_admin`(1), `rag_analysis`(4) | 🔴 **POST 27회 중 14회만 사용** — 절반은 200 반환 |
| **202 Accepted** | 1회 | `sec_pipeline/views.py:40` (하드코딩) | 🟡 비동기 트리거 패턴 표준화 안 됨 |
| **204 No Content** | 8회 | `users`(4), `serverless_admin`(1), `rag_analysis`(3) | 🟡 DELETE에서 일부만 사용 |
| **400 Bad Request** | 매우 많음 | 거의 모든 앱 | 🟢 일관 |
| **401 Unauthorized** | 다수 | `users`, `validation`, `serverless`, etc. | 🟢 |
| **403 Forbidden** | `serverless` 내부에서만 | `{error: {code: 'FORBIDDEN'}}` 패턴 | 🟡 다른 앱에서는 401로 처리 |
| **404 Not Found** | 다수 | `get_object_or_404`(자동 404) + 명시적 `HTTP_404_NOT_FOUND` 혼재 | 🟢 |
| **429 Too Many Requests** | 1회 | `portfolio/views.py:101` (하드코딩) | 🔴 다른 곳은 503 사용 (`serverless`, `users`) |
| **500 Internal Server Error** | 다수 | 거의 모든 try/except 블록 | 🟢 |
| **503 Service Unavailable** | 다수 | `chainsight`, `stocks`, `portfolio` (외부 API 실패 시) | 🟢 |

#### 주요 불일치

- **201 vs 200 (생성 시)**: `users.PortfolioListCreate` 가 `Portfolio` 생성에는 201을 반환하지만, 다른 POST 엔드포인트(`users.AddFavorite`, `stocks/views_screener.py`의 preset 생성 등)는 200 반환 — **표준 부재**
- **delete 시 200 vs 204**: `users.WatchlistDetailItemAPIView.delete`는 204 반환하지만, `users.UserViewLogoutAPIView`는 200 + `{ok: ...}` 반환

### 3. POST/CREATE 메서드 통계

```
def post(...) / def create(...) 정의: 27회 (8개 파일)
HTTP_201_CREATED 사용:              14회 (4개 파일)
→ 약 48% 의 POST가 200 반환
```

---

## 에러 응답 형식

### 1. 에러 키 명칭 통계

| 키 | 출현 | 사용 파일 수 | 의미 |
|----|------|--------------|------|
| **`error`** | **204회** | 17개 | 가장 일반적 (커스텀 형식) |
| **`message`** | **112회** | 10개 | 일부 envelope 내부, 일부 단순 메시지 |
| **`detail`** | **9회** | 3개 | DRF 표준(`portfolio`:6, `users`:2, `config`:1) |
| **`serializer.errors` 직접 노출** | 9회 | 1개 (`users/views.py`) | DRF ValidationError 원본 |

> **DRF 기본 에러 형식 `{detail: "..."}` 는 거의 사용되지 않음** — DRF 자체가 던지는 예외(`NotFound`, `ParseError` 등)에서만 발생. 커스텀 응답은 일관되게 `error` 키를 선호.

### 2. 에러 형식 변종

#### 변종 A — 단순 문자열 (`stocks`, `users`, `chainsight`, `macro`, `thesis`, `validation` 등)

```python
return Response({'error': '...'}, status=status.HTTP_400_BAD_REQUEST)
```

#### 변종 B — 코드 + 메시지 nested (`serverless`)

```python
return Response({
    'success': False,
    'error': {
        'code': 'NOT_FOUND',
        'message': f"Preset not found: {preset_id}"
    }
}, status=status.HTTP_404_NOT_FOUND)
```

#### 변종 C — Helper로 캡슐화 (`rag_analysis`)

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

#### 변종 E — message + 한국어 (`users/views.py:207-208`)

```python
return Response(
    {"message": "This stock is already in your favorites"},
    status=status.HTTP_400_BAD_REQUEST
)
```

> `users/views.py` 내부에서 동일한 400 응답이 **`error`** 와 **`message`** 두 키를 혼용한다. 클라이언트 입장에서 어떤 키를 읽어야 하는지 예측 불가능.

#### 변종 F — `{error: "code_string", message: "...", ...}` (`chainsight`)

```python
return Response({
    'symbol': symbol, 'error': 'not_in_universe',
    'message': '현재 S&P 500 종목만 지원합니다.',
    ...
})
```

> 여기서 `error`는 **에러 코드 enum** 으로 사용되어 변종 A의 `error: <메시지>` 와 의미가 다르다.

### 3. `serializer.errors` 직접 노출 (보안/UX 이슈)

`users/views.py` 9개 위치에서 `Response(serializer.errors, status=400)` 형태로 DRF 검증 에러를 그대로 노출. 다른 앱(`rag_analysis`)은 `create_error_response("INVALID_INPUT", str(serializer.errors))` 로 envelope 안에 넣음. 형식이 통일되지 않음.

---

## 페이지네이션 현황

### 1. DRF 글로벌 설정

```python
# config/settings.py:341-349
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
    # ❌ DEFAULT_PAGINATION_CLASS 미설정
    # ❌ PAGE_SIZE 미설정
}
```

> DRF 페이지네이션은 **`DEFAULT_PAGINATION_CLASS`** 가 설정되어 있어야 `ListAPIView` 와 `ModelViewSet` 의 `list()` 가 자동으로 페이지네이션을 적용한다. 현재 설정 없음 → ListAPIView도 풀 쿼리셋을 직렬화한다.

### 2. 페이지네이션 사용 검색 결과

```
검색어: pagination_class\s*=|PageNumberPagination|LimitOffsetPagination|CursorPagination|paginate_queryset
대상: 전체 코드베이스 (.py)
결과: 0 matches
```

> **전체 백엔드 코드 어디에도 DRF 페이지네이션 클래스를 import 하거나 사용하지 않는다.**

### 3. 페이지네이션 없이 풀 쿼리셋을 반환하는 위험 엔드포인트

| 위치 | 클래스 | 쿼리셋 | 위험도 |
|------|--------|--------|--------|
| `stocks/views.py:75-105` | `StockListAPIView(generics.ListAPIView)` | `Stock.objects.all()` (sector/min_market_cap 필터 옵션) | 🔴 S&P 500 + 모든 종목 풀 반환 |
| `news/api/views.py:42-46` | `NewsViewSet(viewsets.ReadOnlyModelViewSet)` | `NewsArticle.objects.all().prefetch_related('entities')` | 🔴 **모든 뉴스 기사 풀 반환** |
| `news/api/views.py` `@action` 들 | `stock_news`, `keywords/all`, etc. | DB에서 필터 후 직접 직렬화 | 🟡 일부는 days 필터로 제한, 일부 미제한 |
| `stocks/views_screener.py` ScreenerFilter list | DRF view | `ScreenerFilter.objects.filter(is_active=True)` | 🟡 활성 필터 전체 반환 |
| `validation/api/views.py` | DRF view (presets list) | 모든 preset 반환 | 🟢 사용자별 개수 적음 (낮은 위험) |
| `users/views.py` Watchlist/Portfolio list | DRF view | `request.user`로 스코프됨 | 🟢 사용자별 (보통 적음) |

> `.objects.all()` / `.objects.filter()` 호출은 **views 파일에서만 95회** 발생. 그중 절반 이상이 list endpoint이므로 페이지네이션 부재의 잠재적 영향 범위는 넓다.

### 4. 수동 페이지네이션 흔적

```python
# stocks/views.py:609-614
return Response({
    'results': serializer.data,
    'pagination': {
        ...  # 수동 dict
    }
})
```

> 일부 위치에서 `'pagination'` 키를 수동 구성한 흔적이 있으나 표준 클래스가 아님. 응답 형식이 또 다른 변종을 낳음.

### 5. ListAPIView/ViewSet 사용 정리

| 클래스 | 출현 | 위치 |
|--------|------|------|
| `generics.ListAPIView` | 1회 | `stocks/views.py:75` |
| `viewsets.ReadOnlyModelViewSet` | 1회 | `news/api/views.py:42` |
| `viewsets.ModelViewSet` | 0회 (직접 사용 없음, thesis는 import만) | `thesis/views/thesis_views.py` |
| **APIView 기반** | 압도적 다수 | 모든 앱 |

> 대부분의 list endpoint를 `APIView` 로 직접 구현하면서 `paginate_queryset()` 헬퍼 미사용 → 페이지네이션 자동화 기회 상실.

---

## 권고사항

### P0 (즉시 권장 — Critical)

1. **페이지네이션 글로벌 설정 추가**
   - `config/settings.py REST_FRAMEWORK` 에 `DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE` 추가
   - 권장: `LimitOffsetPagination` (기존 `?limit=&offset=` 스타일 호환) 또는 `PageNumberPagination` (`?page=`)
   - 적용 대상 우선순위: `news/api/views.py NewsViewSet` (전체 뉴스 풀 반환) → `stocks/views.py StockListAPIView` (전체 종목 반환)

2. **`StockListAPIView`, `NewsViewSet` 페이지네이션 강제**
   - `Stock.objects.all()`, `NewsArticle.objects.all()` 직렬화 시 페이지네이션 반드시 통과
   - 응답 페이로드 규모를 측정해 회귀 모니터링 추가

### P1 (단기 — High)

3. **응답 envelope 단일 표준 채택**
   - 후보 ① `serverless` 인라인 패턴: `{success, data, error: {code, message}}`
   - 후보 ② `rag_analysis` helper 패턴: `create_success_response()` + `meta: {request_id, timestamp}`
   - **권장**: ②안을 `core/responses.py` (또는 공유 모듈)로 승격, **모든 앱에서 import 사용**
   - 이유: 디버깅 시 `request_id` 가 결정적, 클라이언트 에러 처리 단일 코드 경로

4. **에러 키 명칭 통일**
   - 현재 `error` (204) / `message` (112) / `detail` (9) 혼재
   - **권장**: envelope 안에 `error: {code: <ENUM>, message: <human readable>}` 로 표준화
   - DRF 기본 `detail` 은 envelope 어댑터에서 흡수 (custom exception handler)
   - `users/views.py` 의 `serializer.errors` 직접 노출 9곳을 `error.code='VALIDATION_ERROR', error.message=str(serializer.errors)` 로 래핑

5. **HTTP 상태 코드 표기 통일**
   - 모든 `status=<숫자>` 를 `status.HTTP_*` 로 변환
   - 우선 대상: `portfolio/views.py` (DRF 도입 검토 또는 명시 매핑), `sec_pipeline/views.py:37-44`, `serverless/views.py:1` 위치
   - 또는 `portfolio` 는 의도적으로 DRF 미사용 (Django pure) 라는 결정을 `DECISIONS.md` 에 명시

### P2 (중기 — Medium)

6. **POST/CREATE 메서드의 201 vs 200 정책 결정**
   - 27개 POST 메서드 중 14개만 201 → 정책 부재
   - **권장**: "리소스 신규 생성 → 201", "트리거/액션 → 200/202" 가이드 명시 후 점진적 정렬
   - 우선 대상: `users.AddFavorite`, `stocks/views_screener.py` preset 생성 등

7. **스택 통일 결정**
   - `portfolio/views.py` 만 `JsonResponse` (Django 순수). 의도적 결정인지 확인
   - DRF 통일 시 envelope 표준화 자연 적용
   - 의도적 분리 결정이라면 `DECISIONS.md` 에 사유와 함께 기록

8. **`chainsight/api/views.py` 의 `error: <코드_문자열>` 응답 통일**
   - `error: 'not_in_universe'`, `error: 'no_data'` 형태는 **에러 코드 enum**
   - `error: '검색어는 최소 2자 이상...'` 형태는 **메시지**
   - 동일 키에 두 의미가 공존 → envelope 표준 적용 시 자연 해결

### P3 (장기 — Low)

9. **응답 일관성 회귀 테스트**
   - `tests/api_consistency/` 디렉터리 신설
   - Snapshot 테스트: 각 endpoint 의 응답 구조 키 셋 검증
   - CI 게이트: 새 view 추가 시 envelope 표준 위반 차단

10. **DRF Custom Exception Handler 도입**
    - `REST_FRAMEWORK['EXCEPTION_HANDLER']` 에 envelope 변환기 등록
    - 모든 DRF 예외(`NotFound`, `ValidationError`, `ParseError`, `PermissionDenied`)를 자동으로 표준 envelope으로 매핑
    - view 안의 try/except 보일러플레이트 대폭 감소

11. **빈 placeholder views 정리**
    - `chainsight/views.py`, `validation/views.py`, `news/views.py`, `metrics/views.py`, `graph_analysis/views.py` 는 사실상 미사용
    - URL 라우팅 확인 후 삭제 또는 명시적으로 deprecated 표시

---

## 부록 — 통계 한눈에

```
총 views 파일:                   25개
총 LOC:                          14,485
Response() 호출:                  512회
DRF status 모듈 사용:             248회
하드코딩 status 숫자:              15회
{success: True, ...} 패턴:        63회 (2개 파일에 집중)
{success: False, ...} 패턴:       56회 (2개 파일에 집중)
'error' 키 사용:                  204회
'message' 키 사용:                112회
'detail' 키 사용:                  9회
HTTP_201_CREATED 사용:             14회
HTTP_204_NO_CONTENT 사용:           8회
페이지네이션 클래스 사용:           0회 ⚠️
ListAPIView 사용:                   1회 (페이지네이션 없음)
ReadOnlyModelViewSet 사용:          1회 (페이지네이션 없음)
.objects.all/filter() in views:    95회
```

---

**감사 결론**: 코드 품질 자체는 양호하나, **응답 형식 통일성과 페이지네이션 부재**는 클라이언트 측 코드 복잡성과 운영 위험을 동시에 야기한다. P0 항목(페이지네이션)은 데이터 규모 증가 시 즉시 P&L 영향을 미칠 수 있어 **단기 우선 처리**를 권고한다.
