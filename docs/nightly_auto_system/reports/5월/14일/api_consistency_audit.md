# API 응답 일관성 감사 보고서

생성일: 2026-05-14
대상: stock_vis 프로젝트 전체 views (31개 파일)

---

## 요약

전체 프로젝트에 **4종류의 서로 다른 응답 래핑 패턴**이 혼재한다. `rag_analysis`, `serverless`, `stocks/views_exchange.py`, `stocks/views_screener.py`, `stocks/views_fundamentals.py` 등은 `{"success": True, "data": ...}` 래핑을 일관되게 사용하지만, `users`, `chainsight/api`, `validation/api`, `thesis` 등은 직접 반환(bare dict)을 사용한다. `portfolio/views.py`는 DRF Response가 아닌 Django `JsonResponse`를 직접 사용하는 유일한 파일이다. 에러 키도 `'error'`, `'detail'`, `'ok'`, `'message'` 등 5종류가 혼재하며, 페이지네이션 없이 unbounded `.all()`을 반환하는 위험 지점이 6곳 이상 확인된다.

---

## 앱별 응답 패턴 매트릭스

| 앱 | 래핑 형식 | 직접 반환 | 혼용 여부 | 비고 |
| --- | --- | --- | --- | --- |
| rag_analysis | `{"success": True, "data": ..., "meta": ...}` | DELETE 시 204 body 없음 | 아니오 | `create_success_response()` 헬퍼 사용 |
| config | - | 직접 dict (JsonResponse) | - | health_check/api_root만 존재, DRF 미사용 |
| serverless/views.py | `{"success": True, "data": {...}}` | - | 아니오 | 에러는 `{"success": False, "error": {"code": ..., "message": ...}}` |
| serverless/views_admin.py | 직접 dict (래핑 없음) | 혼용 | 예 | AdminActionView.post만 `{"success": True, "data": {...}}`, 나머지는 직접 반환 |
| chainsight/api/views.py | 직접 dict | - | 아니오 | `{"error": ...}` 또는 내용 직접 반환 |
| chainsight/views/watchlist_views.py | DRF ModelViewSet 기본 | 혼용 | 예 | `create`는 표준 serializer 데이터, `archive`/`resolve`/`recheck` 등 액션은 직접 dict |
| stocks/views.py | 직접 dict | 혼용 | 예 | `StockChartDataAPIView`는 `{"symbol":..., "data":...}`, 에러는 `{"error":...}` |
| stocks/views_exchange.py | `{"success": True, "data": ..., "meta": {...}}` | - | 아니오 | 일관됨 |
| stocks/views_screener.py | `{"success": True, "data": {...}, "meta": {...}}` | - | 아니오 | 일관됨 |
| stocks/views_market_movers.py | 직접 serializer.data | - | 아니오 | 래핑 없음 |
| stocks/views_eod.py | 직접 dict | - | 아니오 | `{"error": ...}` 또는 내용 직접 반환 |
| stocks/views_indicators.py | 직접 dict | - | 아니오 | 래핑 없음, 내용 직접 반환 |
| stocks/views_search.py | 혼용 | 혼용 | 예 | `SymbolSearchView`는 `{"count":..., "results":...}`, `PopularSymbolsView`는 동일. `SymbolValidateView`는 `{"valid": bool, ...}` |
| stocks/views_fundamentals.py | `{"success": True, "data": ..., "meta": {...}}` | - | 아니오 | 일관됨 |
| stocks/views_mvp.py | 직접 dict (커스텀) | - | 아니오 | `{"mode":..., "count":..., "data":...}` |
| macro/views.py | 직접 serializer.data | 혼용 | 예 | 대부분 직접 반환, `DataSyncView`는 `{"status":..., "message":...}` |
| news/api/views.py | 직접 dict | - | 아니오 | `{"symbol":..., "count":..., "articles":...}` 형태 직접 반환 |
| users/views.py | 직접 serializer.data | 혼용 | 예 | `Me`, `PublicUser`, `PortfolioListCreateView` 등 직접 반환. 로그인 응답은 `{"ok":..., "user":...}` |
| portfolio/views.py | JsonResponse (DRF 미사용) | - | - | Django `JsonResponse` 직접 사용 (유일) |
| sec_pipeline/views.py | 직접 dict | - | 아니오 | `{'symbol':..., 'status':..., 'message':...}` |
| graph_analysis/views.py | - | - | - | 비어있음 (`# Create your views here.`) |
| validation/api/views.py | 직접 dict | 혼용 | 예 | 에러만 `{'error': ...}`, 정상 응답은 내용 직접 반환 |
| thesis/views/thesis_views.py | DRF ModelViewSet 기본 | 혼용 | 예 | ViewSet 기본값 + `close` 액션은 `{'status':'closed', 'thesis_id':...}` |
| thesis/views/conversation_views.py | 직접 dict | - | 아니오 | service 결과값 직접 반환 |
| thesis/views/monitoring_views.py | 직접 dict | - | 아니오 | 내용 직접 반환 |

---

## HTTP 상태 코드 일관성

### 정상 응답

| 케이스 | 코드 | 현황 | 위치 |
| --- | --- | --- | --- |
| POST 생성 성공 | 201 | 대체로 준수 | `rag_analysis/views.py:87`, `users/views.py:107`, `chainsight/views/watchlist_views.py:95` |
| POST 생성 — 미사용 | 200 | 일부 누락 | `serverless/views_admin.py:400` — POST 액션 트리거가 200 반환 (201 대신) |
| GET 성공 | 200 | 대부분 준수 | 전체 |
| DELETE 성공 | 204 | 준수 | `rag_analysis/views.py:132`, `users/views.py:342` |
| 수집 트리거 (비동기) | 202 | 1곳만 사용 | `sec_pipeline/views.py:45` — 202 올바르게 사용 |

**특이 케이스:**

- `stocks/views.py:986`: POST sync가 성공/실패 혼합 시 `HTTP_200_OK`를 반환하고, 전부 실패 시 `HTTP_500_INTERNAL_SERVER_ERROR`를 반환한다. 부분 성공(`any_success=True, all_success=False`)인 경우 200을 반환하는 것은 의도된 설계이나 클라이언트가 `status` 필드를 별도 확인해야 한다.
- `portfolio/views.py:59`: Django `JsonResponse(result, status=200)` — 하드코딩 정수 사용.

### 에러 응답

| 코드 | 사용 상황 | 예시 위치 |
| --- | --- | --- |
| 400 | 잘못된 입력, 유효성 실패 | 전체 앱에서 일관 사용 |
| 401 | 미인증 | `validation/api/views.py:463` — `{'error': '로그인이 필요합니다.'}` |
| 403 | 권한 없음 | `rag_analysis/views.py:665` — `PERMISSION_DENIED` |
| 404 | 리소스 없음 | 전체 앱에서 일관 사용 |
| 429 | Rate Limit / Cooldown | `serverless/views_admin.py:370`, `portfolio/views.py:107` |
| 500 | 내부 오류 | 전체 앱에서 사용 |
| 503 | 서비스 불가 | `chainsight/api/views.py:444`, `rag_analysis/views.py:759` |

### status 모듈 vs 하드코딩 숫자

**하드코딩 정수 사용 파일** (위반):

| 파일 | 라인 | 하드코딩 값 |
| --- | --- | --- |
| `sec_pipeline/views.py` | 45, 49, 51 | `status=202`, `status=200`, `status=200` |
| `portfolio/views.py` | 49, 55, 57, 59, 84 외 다수 | `status=400`, `status=503`, `status=500`, `status=200`, `status=429` |
| `serverless/views.py` | 2887 | `status=400` (1곳) |

`portfolio/views.py`는 DRF Response가 아닌 Django `JsonResponse`를 사용하므로 `rest_framework.status` 상수를 적용할 수 없는 구조다. `sec_pipeline/views.py`는 202 사용이 의미적으로 올바르나 상수화되지 않았다.

**나머지 파일**: `from rest_framework import status` 임포트 후 `status.HTTP_*` 상수 사용 — 준수.

---

## 에러 응답 형식

### 에러 키 출현 횟수

| 에러 키 | 출현 횟수 (파일 수) | 사용 앱 |
| --- | --- | --- |
| `'error'` (문자열) | 약 90회+ (18개 파일) | stocks, macro, news, users, chainsight, validation, serverless/views_admin, sec_pipeline |
| `'error'` (객체: `{"code":..., "message":...}`) | 약 20회 (2개 파일) | rag_analysis, serverless/views.py |
| `'detail'` | 약 15회 (3개 파일) | chainsight/views/watchlist_views.py, validation/api/views.py (일부) |
| `'message'` | 약 10회 (4개 파일) | users/views.py (`AddFavorite`, `RemoveFavorite`), macro/views.py (`DataSyncView`), serverless/views_admin.py |
| `'ok'` | 3회 (1개 파일) | users/views.py — `LogOut`, `LogIn` 성공 응답 |
| `'valid'` | 2회 (1개 파일) | stocks/views_search.py — `SymbolValidateView` |
| `'error'` (Pydantic) + `'detail'` | 약 20회 (1개 파일) | portfolio/views.py — `{"error": "...", "detail": "..."}` |

### 주요 불일치 사례

1. **`'error'` 문자열 vs 객체**: `macro/views.py:47`은 `{'error': 'Failed to fetch...'}`(문자열), `rag_analysis/views.py:90`은 `{'error': {'code': 'INVALID_INPUT', 'message': '...'}}`(객체). 클라이언트가 두 형식을 모두 처리해야 한다.

2. **`'ok'` 키**: `users/views.py:184`의 `{"ok": "You have been logged out"}`, `:167`의 `{"ok": "Welcome!", "user": {...}}` — 성공 여부 플래그가 boolean이 아닌 문자열이다.

3. **`'detail'` vs `'error'`**: DRF 예외(`raise_exception=True`)는 `'detail'` 키로 반환되지만, 수동 `return Response({'error': ...})`는 `'error'` 키를 사용한다. 같은 파일 내에서도 혼용된다 (`validation/api/views.py:67`은 `{'error': ...}`, `:197`은 직접 반환).

4. **`'message'` 키**: 에러 상황에서 `{'message': 'This stock is already in your favorites'}`처럼 에러 키 없이 메시지만 반환 (`users/views.py:214`).

5. **DRF 예외 vs 커스텀 응답 혼용**: `users/views.py`는 `raise NotFound`, `raise ParseError`와 `return Response({'error': ...})`를 동일 파일에서 혼용한다.

---

## 페이지네이션 현황

### 페이지네이션 적용 ViewSet

| 파일 | 클래스/함수 | 페이지네이션 방식 |
| --- | --- | --- |
| `rag_analysis/views.py` | `UsageHistoryView` | Django `Paginator` 수동 적용 (DRF PageNumberPagination 아님) |
| `news/api/views.py` | `NewsViewSet.all_news` | 수동 offset/limit 슬라이싱 |

**DRF `pagination_class` 설정 ViewSet**: 확인된 파일 범위 내에서 `pagination_class`를 명시적으로 설정한 ViewSet은 없다. `ThesisViewSet`, `ThesisPremiseViewSet`, `ThesisIndicatorViewSet`, `NewsViewSet`, `WatchlistViewSet` 모두 `pagination_class` 미설정.

### 페이지네이션 없이 .all()/.filter() 반환 (위험)

| 파일:라인 | 함수 | 반환 규모 위험도 | 비고 |
| --- | --- | --- | --- |
| `users/views.py:93` | `Users.get()` | 높음 | `User.objects.all()` 전체 반환, 관리자 전용이나 무제한 |
| `users/views.py:193` | `UserFavorites.get()` | 중간 | `user.favorite_stock.all()` 전체 반환 |
| `news/api/views.py:50` | `NewsViewSet` queryset | 높음 | `NewsArticle.objects.all().prefetch_related('entities')` — ViewSet 기본 queryset 전체, `list` 액션 호출 시 페이지네이션 없으면 전량 반환 |
| `thesis/views/monitoring_views.py:238` | `AlertListView.get()` | 낮음 | `[:50]` 슬라이스 적용되어 있으나 DRF 표준 페이지네이션 아님 |
| `stocks/views.py:85` | `StockListAPIView` | 높음 | `generics.ListAPIView` 사용, `pagination_class` 미설정 시 전체 반환 가능 |
| `validation/api/views.py` | `LeaderComparisonView.get()` | 중간 | N+1 위험 없으나 `comparisons` 리스트 제한 없음 |
| `chainsight/views/watchlist_views.py:36` | `WatchlistViewSet.get_queryset()` | 중간 | `SavedPath.objects.all()` 필터 후 `.prefetch_related('actions')`, `pagination_class` 미설정 |
| `adminviews.py:477` | `AdminNewsCategoryView.get()` | 낮음 | `NewsCollectionCategory.objects.all()` — 카테고리 수가 적어 위험도 낮음 |

**특히 위험한 케이스:**

- `news/api/views.py:50`: `queryset = NewsArticle.objects.all().prefetch_related('entities')` — `NewsViewSet`의 기본 queryset으로, `list` 액션이 `pagination_class` 없이 호출되면 DB의 모든 NewsArticle을 반환한다. 뉴스 데이터는 시간이 지날수록 급증하므로 OOM/타임아웃 위험이 있다.

- `stocks/views.py:85-105` (`StockListAPIView`): `generics.ListAPIView`를 상속했으나 `pagination_class`가 클래스에 정의되지 않았다. Django settings의 `DEFAULT_PAGINATION_CLASS`가 설정되어 있지 않으면 전체 Stock 목록(수천 건)을 반환한다.

- `users/views.py:93` (`Users.get`): `User.objects.all()`을 직렬화해 반환한다. 관리자 전용이지만 사용자가 많아질수록 위험하다.

---

## 권고사항

**P1 — 즉시 수정 권장**

1. **`news/api/views.py` — `NewsViewSet` 페이지네이션 필수 적용**: 기본 `queryset = NewsArticle.objects.all()`에 `pagination_class = PageNumberPagination` 또는 `DEFAULT_PAGINATION_CLASS`를 지정하라. 현재 `list` 액션 호출 시 전체 뉴스를 반환할 수 있다 (`news/api/views.py:50`).

2. **`portfolio/views.py` — DRF Response 전환 또는 하드코딩 상수화**: Django `JsonResponse`에 정수 status를 직접 사용하는 유일한 파일이다. DRF `Response` + `status.HTTP_*` 상수로 전환하거나 최소한 `HTTPStatus` 상수를 사용하라 (`portfolio/views.py` 전체).

3. **`sec_pipeline/views.py` — 하드코딩 status 상수화**: `status=202`, `status=200`을 `status.HTTP_202_ACCEPTED`, `status.HTTP_200_OK`로 교체하라 (`sec_pipeline/views.py:45,49,51`).

**P2 — 단기 개선 권장**

4. **에러 키 표준화**: 프로젝트 전체에서 에러 응답 키를 `'error'`(문자열) 또는 `'error': {'code': ..., 'message': ...}`(객체) 중 하나로 통일하라. 현재 `'error'`(문자열), `'error'`(객체), `'detail'`, `'message'`, `'ok'` 5종류가 혼재한다. DRF 예외(`raise NotFound` 등)는 `'detail'`을 반환하므로 커스텀 에러도 `'detail'`로 맞추거나, 커스텀 exception handler를 등록하는 것이 일관적이다.

5. **`users/views.py` — `'ok'` 키 제거**: `LogIn`, `LogOut` 응답에서 `{"ok": "..."}` 패턴을 `{"message": "..."}` 또는 DRF 표준으로 통일하라 (`users/views.py:167,184`).

6. **`StockListAPIView` 페이지네이션**: `stocks/views.py:75`의 `generics.ListAPIView` 상속 클래스에 `pagination_class`를 명시적으로 설정하라. Django settings에 `DEFAULT_PAGINATION_CLASS`가 없을 경우 무제한 반환된다.

**P3 — 중기 일관성 개선**

7. **`serverless/views_admin.py` 래핑 통일**: 동일 파일에서 `AdminOverviewView`(직접 반환)와 `AdminActionView.post`(`{"success": True, "data": {...}}` 래핑)가 혼용된다. 관리자 API는 래핑 여부를 하나로 통일하라 (`serverless/views_admin.py`).

8. **`macro/views.py` 래핑 패턴 정리**: `SectorPerformanceView.get()`은 `Response(data)` (직접 반환), `DataSyncView.post()`는 `Response({'status': ..., 'message': ...})`, `SyncStatusView.get()`도 같은 형식이나 serializer 사용 뷰들은 `serializer.data`를 직접 반환한다. 일관된 패턴을 결정하라.

9. **`WatchlistViewSet` 페이지네이션 추가**: `chainsight/views/watchlist_views.py:30`의 `WatchlistViewSet`에 `pagination_class`를 설정하라. 사용자가 많은 수의 saved path를 가질 경우 전체 반환된다.

10. **`success` 필드 표준 정의**: `serverless`, `rag_analysis`, `stocks/views_exchange.py` 등은 `{"success": True/False, "data": ...}` 패턴을 사용하지만, 다른 앱들은 이를 사용하지 않는다. 프로젝트 전체에 단일 응답 envelope 표준을 채택하거나, 현행 앱별 패턴 유지를 명시적 결정으로 문서화하라.
