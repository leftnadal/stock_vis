# API 응답 일관성 감사 보고서

- 감사 일자: 2026-04-28
- 감사 대상: Django REST Framework 기반 모든 `views*.py` (총 19개 활성 파일)
- 감사 방식: 정적 분석 (소스코드 직접 읽기 + Grep 패턴 매칭)
- 코드 수정 없음, 읽기 전용

---

## 요약

`config/settings.py`에 `DEFAULT_PAGINATION_CLASS`나 `EXCEPTION_HANDLER` 설정이 없는 상태에서, 각 앱이 **독자적인 응답 컨벤션**을 형성하고 있다. 결과적으로 **6가지 이상의 서로 다른 응답 래핑 패턴**이 공존하며, 동일한 backend 안에서도 같은 앱(`stocks/`) 내부에서조차 파일별로 패턴이 다르다.

핵심 발견:

| 항목 | 현황 | 영향 |
|------|------|------|
| 응답 래핑 표준 | **없음** — `success/data/meta` 봉투 vs raw payload 혼재 | 프론트엔드는 엔드포인트마다 분기 필요 |
| 에러 키 | `error`(159회), `message`(99회), `detail`(3회) 혼재 | 에러 핸들러를 일관되게 작성할 수 없음 |
| `error` 값 타입 | 문자열 / `{code, message}` 객체 / 단일 메시지 혼재 | 클라이언트가 타입 분기 필요 |
| 페이지네이션 | DRF 기본 미설정, 6개 앱이 **3가지 서로 다른 자체 구현** | 무한 스크롤·페이징 UI 통일 불가 |
| HTTP 상태 코드 | `status.HTTP_*`(248회) 우선이나, `status=200/202/404` 하드코딩(7회) 혼재 | 일관성은 있으나 일부 sec_pipeline 등에서 직접 숫자 사용 |
| 401 응답 | 라우트별로 5개 앱이 자체 구현(IsAuthenticated 미사용 + 수동 처리) | DRF 기본 401과 페이로드가 달라짐 |
| `content_type/Accept` 분기 | `config/views.py`만 자체 처리, 그 외 앱은 DRF에 위임 | 정상이나 root view의 일관성은 떨어짐 |

전반적으로 **MVP 단계의 자유로운 응답 패턴이 누적된 상태**이며, 추후 OpenAPI 스펙 자동 생성·SDK 생성·에러 모니터링 통합 시 큰 마찰을 일으킬 수 있다.

---

## 앱별 응답 패턴 매트릭스

응답 본체(envelope) 구조를 기준으로 분류했다. "Raw"는 도메인 데이터를 그대로 반환, "Wrapped"는 `{success, data, meta}` 형태의 봉투를 사용함을 의미한다.

| 앱 / 파일 | 성공 응답 패턴 | 에러 키 | 상태코드 표기 | 비고 |
|-----------|---------------|---------|--------------|------|
| `stocks/views.py` | **혼재**: `Response(serializer.data)` (Overview), `{symbol, data, _meta}` (Overview FMP fallback), `{result, message}` (Search) | `error` (str/객체) | `status.HTTP_*` | Overview 에러는 `{error: {code, message, details}}` 객체 |
| `stocks/views_eod.py` | Raw: `snapshot.json_data` 또는 `{signal_id, date, count, stocks}` | `error` (str) | `status.HTTP_*` | DB raw JSON을 그대로 반환 |
| `stocks/views_fundamentals.py` | **Wrapped**: `{success: True, data, meta}` | `error` (str) | `status.HTTP_*` | 5개 엔드포인트 모두 `success/data/meta` 패턴 일관 |
| `stocks/views_exchange.py` | **Wrapped**: `{success: True, data, meta}` | `error` (str) | `status.HTTP_*` | fundamentals와 동일 패턴 |
| `stocks/views_screener.py` | **Wrapped**: `{success: True, data, meta}` | `error` (str/dict) | `status.HTTP_*` | meta에 `is_enhanced`, `total_before_filter` 등 자유 필드 |
| `stocks/views_market_movers.py` | Raw: `serializer.data` 직접 반환 | `error` (str) | `status.HTTP_*` | 같은 stocks 앱 안에서도 다른 패턴 |
| `stocks/views_indicators.py` | Raw: `indicators_data` 그대로 | `error` (str) | `status.HTTP_*` | dict 그대로 반환 |
| `stocks/views_search.py` | Raw: `{count, results}` | `error` (str) | `status.HTTP_*` | DRF pagination 미사용 |
| `stocks/views_mvp.py` | (소수의 raw payload) | — | `status.HTTP_*` | 메인 흐름과 격리됨 |
| `users/views.py` | Raw: `serializer.data` / `{message: ...}` / `{ok, user}` | `error`/`message`/`detail` 혼재 | `status.HTTP_*` | 동일 파일 내 패턴 다양 (Login: `error`, Logout: `ok`, Password: `message`) |
| `users/views.py` (Watchlist) | Raw: `{results, pagination}` | `error` | `status.HTTP_*` | Django Paginator 자체 사용 (DRF Pagination 미사용) |
| `news/api/views.py` | Raw: `{symbol, count, articles}`, `{date, total, articles}` 등 엔드포인트별 자유 형식 | `detail`/`error` (DRF ValidationError raise + manual) | `status.HTTP_*` | `ReadOnlyModelViewSet` + `@action` 다수 |
| `macro/views.py` | Raw: `serializer.data` 또는 service dict 그대로 | `error` (str) | `status.HTTP_*` | 모든 view에서 try/except 후 `{'error': ...}` 단일 키 |
| `serverless/views.py` | **Wrapped 다수**: `{success: True, data}`, 일부 raw 혼재 | `error: {code, message}` 객체 또는 str | `status.HTTP_*` | 가장 정형화되어 있으나 일부 함수형 view가 raw |
| `serverless/views_admin.py` | Raw: 도메인 dict 또는 `{actions: ...}`. 단 1곳만 `{success: True, data}` | `error` (str) | `status.HTTP_*` | POST action 응답에서만 `success` 봉투 사용 |
| `chainsight/api/views.py` | Raw: 도메인 그대로 (`center/nodes/edges/meta`) | `error` (str) | `status.HTTP_*` | 일부 뷰에서 `meta` 서브 객체 사용 |
| `validation/api/views.py` | Raw: 도메인 그대로 (`symbol/category_signals/...`) | `error` (str) | `status.HTTP_*` | 일부 응답에서 `status: 'ok'` 키 사용 (`PeerPreferenceView`) |
| `thesis/views/*.py` | Raw: ViewSet 표준 + `{indicators, count}` | `error` (str) | `status.HTTP_*` | ModelViewSet 기반, close 액션은 `{status: 'closed', thesis_id}` |
| `rag_analysis/views.py` | **Wrapped**: `create_success_response(data)` 헬퍼 사용 → `{success, data, meta:{request_id, timestamp}}` | `create_error_response(code, message)` → `{success:False, error:{code, message}}` | `status.HTTP_*` | 가장 표준화된 봉투, 다른 앱이 따라가지 않음 |
| `marketpulse/api/views/overview.py` | Raw + `_meta`: `{_meta:{status, latency_ms, cache, ...}, ticker_bar, news, ...}` | `error` (str) | hardcoded `status=404` 일부 | v2 자체 `_meta` 봉투 컨벤션 — 다른 앱과 다름 |
| `marketpulse/api/views/cards.py` | Wrapped: `{_meta, data}` 단순 봉투 | `error` (str) | hardcoded `status=404` | v2 카드 detail 전용 |
| `marketpulse/api/views/health.py` | Raw: `{_meta, probes, last_runs}` | — | — | admin only |
| `sec_pipeline/views.py` | Raw: `{symbol, status, message}` 또는 `{status: 'available', ...}` | `error` 미사용 | **하드코딩 `status=200/202`** | 유일하게 `status` 모듈 import 안 함 |
| `metrics/views.py`, `graph_analysis/views.py`, `chainsight/views.py`, `news/views.py`, `validation/views.py` | (구현 없음, placeholder) | — | — | `# Create your views here.` |
| `config/views.py` | Raw `JsonResponse({...})` (DRF 미경유) | — | — | `Accept` 헤더로 HTML/JSON 분기 |

### 같은 앱 내 불일치 사례

`stocks/` 앱은 단일 앱 내에서 4가지 패턴이 공존한다. 같은 클라이언트가 아래 응답을 동시에 다뤄야 한다.

```python
# stocks/views_fundamentals.py — Wrapped envelope
return Response({
    "success": True,
    "data": serializer.data,
    "meta": {"symbol": ..., "period": ..., "count": ..., "timestamp": ...}
})

# stocks/views.py StockSearchAPIView — Raw with mixed keys
return Response({'results': serializer.data, 'count': len(stocks), 'query': query},
                status=status.HTTP_200_OK)

# stocks/views_eod.py — Pure raw (DB JSON pass-through)
return Response(snapshot.json_data)

# stocks/views_indicators.py — Raw dict
return Response(indicators_data)
```

`users/views.py` 내부에서도 메소드별 패턴이 다르다.

```python
# Login → {"ok": "Welcome!", "user": {...}}
# AddFavorite → {"message": "Stock added", "stock": {...}}
# Watchlist list → {"results": [...], "pagination": {...}}
# RefreshStockDataView 에러 → {"error": "...", "detail": "..."}  ← 두 키 동시 사용
```

---

## HTTP 상태 코드 일관성

### 종합 통계 (Grep 카운트)

- `status.HTTP_*` 사용: **248회** / 16 파일 — 정상 패턴
- 하드코딩된 `status=숫자` 사용: **4회** (sec_pipeline 3, serverless 1)

### 200 vs 201 (생성)

대부분의 POST 엔드포인트는 `status.HTTP_201_CREATED`를 정확히 사용한다.

- **정상**: `users/views.py` (Portfolio create, Watchlist create/Add), `stocks/views.py` 회원가입, `serverless/views_admin.py` 카테고리 생성, `rag_analysis/views.py` Basket/Item 생성
- **세부 의도된 분기**: `WatchlistBulkAdd`는 *added 항목 존재 여부에 따라* 201/200 동적 선택. `RefreshStockData`는 부분 성공 시 `207_MULTI_STATUS`까지 사용. 의도가 명확하므로 OK.
- **누락 사례**:
  - `thesis/views/thesis_views.py::ThesisIndicatorViewSet.auto` POST 응답이 `Response({...})` (200) — 신규 추천 indicator 목록을 반환하지만, 검색 API에 가깝다 보니 200이 합리적. 회색 영역.
  - `thesis_views.py::ThesisViewSet.close`는 `{'status': 'closed'}`를 200으로 반환 — 리소스 변경이지만 새 리소스 생성은 아니므로 200이 맞다.

### 4xx 사용 패턴

| 상태코드 | 주 사용처 | 빈도 |
|---------|----------|------|
| 400 | serializer.errors, 파라미터 검증 실패 | 매우 높음 |
| 401 | 수동 401 (로그인 필요) — `users/views.py::LogIn`, `validation/api/views.py::PeerPreferenceView` (DRF 표준 401과 다른 페이로드) | 중간 |
| 403 | 거의 사용 안 됨 (DRF 권한 클래스에 위임) | 낮음 |
| 404 | `Stock not found`, `Watchlist not found` 등 — `raise NotFound(...)` 와 직접 `Response({'error':...}, status=404)` 혼재 | 매우 높음 |
| 429 | `serverless/views_admin.py::AdminActionView` 쿨다운 | 1회 |
| 500 | 광범위한 try/except 후 `{error: '...'}` 반환 — `macro/views.py`의 모든 view, `users/views.py::RefreshPortfolio` 등 | 높음 |
| 503 | `chainsight/api/views.py` `GraphConnectionError`, `stocks/views_exchange.py` FMP 실패, `stocks/views_search.py` provider 실패 | 중간 |

### 하드코딩된 숫자 vs `status` 모듈

```python
# sec_pipeline/views.py:41,44,46  ← 직접 숫자
return Response({...}, status=202)
return Response(result, status=200)
return Response(result, status=200)

# marketpulse/api/views/cards.py:71  ← 직접 숫자
return Response({'error': f'unknown card: {card_id}'}, status=404)
```

`status` 모듈을 import하지 않은 채 raw 정수를 사용하는 곳은 sec_pipeline가 유일하게 일관되며, marketpulse v2는 일부만 raw 정수를 쓴다. 변환은 사소하나 grep/문서화 시 일관성을 해친다.

### `IsAuthenticated`를 우회한 수동 401

DRF는 `permission_classes = [IsAuthenticated]`를 두면 401(미인증) / 403(인증됐으나 권한 없음)을 자동 반환한다. 그러나 다음은 권한 클래스를 `IsAuthenticatedOrReadOnly` / 미설정으로 두고 본문에서 직접 401을 반환한다:

```python
# validation/api/views.py::PeerPreferenceView
permission_classes = [IsAuthenticatedOrReadOnly]
def post(self, request, symbol):
    if not request.user.is_authenticated:
        return Response({'error': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
```

DRF 기본 401은 `{"detail": "Authentication credentials were not provided."}` 형태이지만, 이 코드는 `{"error": "..."}` 라 클라이언트가 미들웨어로 통일된 인증 처리를 하기 어렵다.

---

## 에러 응답 형식

### 키 사용 빈도 (Grep 카운트)

| 키 | 횟수 | 주 사용 앱 |
|----|------|-----------|
| `error` | 159 | validation, users, news, macro, chainsight, serverless, stocks, rag_analysis |
| `message` | 99 | validation, sec_pipeline, users, news, macro, serverless, rag_analysis, config, stocks |
| `detail` | 3 | users(2), config(1) |

DRF가 기본으로 사용하는 `detail` 키는 거의 사용되지 않는다. 즉 **DRF 기본 예외 핸들러가 만든 응답과 우리 코드가 만든 응답의 키가 다르다.** 클라이언트는 `error`와 `detail` 두 케이스를 모두 처리해야 한다.

### `error` 값의 타입 불일치

같은 키임에도 값의 타입이 다르다.

```python
# 문자열 (대다수)
return Response({'error': 'Stock not found'}, status=404)

# 객체 with code (rag_analysis, serverless 일부, stocks Overview)
return Response({
    'success': False,
    'error': {'code': 'INVALID_TYPE', 'message': '...'}
}, status=400)

# 객체 with details (stocks/views.py Overview)
return Response({
    'error': {
        'code': 'OVERVIEW_ERROR',
        'message': '...',
        'details': {'symbol': ..., 'original_error': ..., 'can_retry': True}
    }
}, status=500)

# serializer.errors 그대로 노출 (stocks/views_screener.py)
return Response({"error": serializer.errors}, status=400)

# 한 응답에 error+detail 동시 반환 (users/views.py)
return Response({
    'error': 'Failed to refresh portfolio data',
    'detail': str(e),
}, status=500)
```

이 불일치 때문에 프론트엔드 에러 표시 컴포넌트가 분기 처리되거나, 일부 에러는 `[object Object]` 형태로 표시될 가능성이 있다. (실제 운영에서는 `String(error)` fallback 처리가 흔히 누적된다.)

### `message` 단독 사용 사례

`{'message': '...'}` 키만 쓰는 케이스도 있다. 성공 메시지인지 에러인지 컨텍스트로 추정해야 한다.

```python
# users/views.py::AddFavorite — 성공
return Response({"message": "Stock added to favorites", "stock": ...})

# users/views.py::AddFavorite — 실패 (이미 등록됨)
return Response({"message": "This stock is already in your favorites"},
                status=status.HTTP_400_BAD_REQUEST)
```

같은 키가 success/error 양쪽에 쓰여서 의미가 모호하다.

### DRF Exception 사용 패턴

DRF의 `NotFound`, `ValidationError`, `ParseError`를 일부 앱은 적극적으로 사용하고(`users/views.py`, `news/api/views.py`, `rag_analysis/views.py`), 일부 앱은 거의 쓰지 않는다(`macro/views.py`, `chainsight/api/views.py`, `stocks/views_eod.py`). raise 방식을 쓰면 응답 본문은 `{"detail": "..."}`가 되지만, 같은 의미의 수동 처리 응답은 `{"error": "..."}`가 된다 — 같은 의미를 가진 두 종류의 응답이 같은 앱 내에서 발생한다.

---

## 페이지네이션 현황

### 글로벌 설정 부재

`config/settings.py:338`의 `REST_FRAMEWORK`에는:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
    'DEFAULT_THROTTLE_RATES': {...},
}
```

**`DEFAULT_PAGINATION_CLASS`, `PAGE_SIZE` 모두 미설정**. 즉 DRF의 generic ListAPIView·ModelViewSet은 페이지네이션 없이 전체 결과를 반환한다.

### 자체 구현된 페이지네이션 (3가지 방식)

#### 1. Django Paginator 직접 사용 (`users/views.py`, `rag_analysis/views.py`)

```python
paginator = Paginator(queryset, page_size)
page_obj = paginator.page(page_number)
return Response({
    'results': serializer.data,
    'pagination': {
        'count': ..., 'page': ..., 'page_size': ...,
        'num_pages': ..., 'has_next': ..., 'has_previous': ...
    }
})
```

#### 2. Offset/Limit 수동 슬라이싱 (`serverless/views.py`, `news/api/views.py::all_news`)

```python
total_count = queryset.count()
articles = queryset.order_by('-published_at')[offset:offset + limit]
return Response({
    'total': total_count, 'count': ..., 'offset': ..., 'limit': ...,
    'has_more': (offset + limit) < total_count, 'articles': serializer.data
})
```

#### 3. page+page_size 응답 봉투 (`chainsight/api/views.py::SignalFeedView`)

```python
chains_result = self._build_chain_signals(page, page_size, sector, today)
response_data = {
    'date': ..., 'page': page, 'page_size': page_size,
    'total_count': chains_result['total'],
    'has_next': chains_result['has_next'],
    'chains': chains_result['items'],
}
```

**3가지 응답 키마저 모두 다르다**:
- 결과 리스트: `results` / `articles` / `chains`
- 총합: `count` / `total` / `total_count`
- 다음 페이지 표시: `has_next` / `has_more` / `has_next`

### 페이지네이션 없는 목록 반환 (잠재적 위험)

쿼리셋을 그대로 리턴하면서 페이지네이션이 없는 목록 엔드포인트는 다음과 같이 분포한다 (`.objects.all()` / `.filter()` 174회 발견 중 표본):

| 위치 | 반환 데이터 | 잠재 규모 | 비고 |
|------|-------------|----------|------|
| `stocks/views.py::StockListAPIView` (`generics.ListAPIView`) | Stock 전체 | S&P500 ~500개 + 자유 종목 → 수천 | DRF pagination 미설정이므로 ListAPIView는 그냥 전부 반환 |
| `users/views.py::Users.get` | `User.objects.all()` | 사용자 수에 비례 | 관리자 전용이라 즉각 위험은 낮음 |
| `users/views.py::PortfolioListCreateView.get` | 사용자별 portfolio 전체 | 사용자별 평균 N개 | 보통 수백건 이하라 OK |
| `users/views.py::UserFavorites.get` | 즐겨찾기 전체 | 사용자별 N개 | OK |
| `users/views.py::UserInterestListCreateView.get` | UserInterest 전체 (사용자별) | 사용자별 N개 | OK |
| `news/api/views.py::trending` | NewsEntity aggregation 결과 | limit param 적용 | OK |
| `chainsight/api/views.py::SeedListView` | seeds 전체 | 일별 시드 수 (수백 이하) | OK |
| `chainsight/api/views.py::SectorGraphView` | sector 노드 + 엣지 | limit 30 cap | OK |
| `validation/api/views.py::ValidationMetricsView` | 카테고리별 지표 전체 | 카테고리 ~7개 × 5~10 metric | OK |
| `validation/api/views.py::PresetListView` | preset 전체 (per symbol) | 6개 이하 | OK |
| `serverless/views_admin.py::AdminNewsCategoryView` | NewsCollectionCategory 전체 | 수십건 | OK |
| `stocks/views_eod.py::EODSignalDetailView` | top 50 limit | OK |
| `stocks/views_eod.py::EODPipelineStatusView` | 최근 7일 limit | OK |

→ 즉시 위험한 곳은 `StockListAPIView`(전 종목 반환) 정도이며, 나머지는 도메인 상한 또는 limit param으로 제어되고 있다. 그러나 **클라이언트가 일관된 페이징 UI를 만들 수 없는 것**이 더 큰 문제다.

---

## 권고사항

### 단기 (블로커성, 1~2일 작업)

1. **`config/settings.py`에 `DEFAULT_PAGINATION_CLASS` 등록**
   - 현재 `users/views.py`, `chainsight/api/views.py`, `serverless/views.py`, `news/api/views.py`, `rag_analysis/views.py`에 흩어진 자체 구현을 PageNumberPagination 한 가지로 통일
   - 또는 결과 리스트가 클 가능성이 있는 `StockListAPIView`만이라도 명시적 `pagination_class` 지정

2. **에러 응답 키 통일 결정**
   - DRF `EXCEPTION_HANDLER`를 직접 작성해 모든 raise → `{"error": {"code": ..., "message": ...}}` 봉투로 변환
   - 기존 `error: 문자열` / `detail` / `message` 사용처는 한 분기에 일괄 마이그레이션
   - 결정 기록은 `DECISIONS.md`에 추가

3. **수동 401 응답 제거**
   - `validation/api/views.py::PeerPreferenceView` 등은 `permission_classes = [IsAuthenticated]`로 변경하면 DRF가 자동으로 401을 반환
   - DRF 기본 응답으로 통일하면 클라이언트 인증 미들웨어가 단순해진다

### 중기 (1주 작업)

4. **응답 봉투(envelope) 컨벤션 채택 결정**
   - 옵션 A — **Wrapped 봉투 표준화**: `rag_analysis/views.py`의 `create_success_response`/`create_error_response` 헬퍼를 공통 모듈로 승격해 모든 앱이 `{success, data, meta:{request_id, timestamp}}` 사용
   - 옵션 B — **Raw 표준화**: 봉투를 걷어내고 도메인 데이터를 그대로 반환, 메타정보는 `X-*` 헤더로 이동 (DRF idiomatic 한 쪽)
   - 어느 쪽이든 결정해야 클라이언트 generic 클라이언트(예: TanStack Query 응답 변환기)를 통일할 수 있음
   - 결정 후 단계적으로 마이그레이션 (한 PR에 몰아 처리하지 말 것 — 회귀 위험)

5. **OpenAPI 스펙 자동 생성 도입**
   - `drf-spectacular`로 모든 view를 스펙화하면 응답 형식 불일치가 컴파일타임 에러로 노출된다
   - 도입 후 첫 PR에서 contracts/와 실제 응답 차이 6건 이상 발견될 가능성이 높음 (KB의 `LESSON: contracts와 실제 API 응답 6건 불일치`와 부합)

### 장기 (점진 개선)

6. **`marketpulse/api/views/*.py`의 `_meta` 봉투를 다른 앱으로 확산**
   - `_meta: {generated_at, latency_ms, cache: HIT/MISS}` 패턴은 디버깅에 유용. `stocks/views_fundamentals.py`의 meta와도 자연스럽게 결합 가능
   - 단 `cache: HIT/MISS` 같은 운영 정보 노출이 보안 정책에 부합하는지 검토 필요

7. **에러 코드 체계 도입**
   - 현재 `INVALID_TYPE`, `BASKET_FULL`, `OVERVIEW_ERROR`, `INVALID_INPUT`, `DUPLICATE_ITEM` 등 ad-hoc 코드가 흩어져 있음
   - 앱 prefix(`STOCKS_NOT_FOUND`, `USERS_DUPLICATE_FAVORITE` 등) + 카탈로그를 `contracts/error-codes.md`로 정리

8. **테스트 추가**
   - `tests/contracts/test_response_shapes.py` 같은 계약 테스트로 모든 ListView가 `{count, results}` 키를 갖는지, 모든 에러 응답이 `error` 키를 갖는지 단정
   - 회귀를 막는 가드레일

---

## 부록 — 분석에 사용한 Grep 데이터 요약

| 패턴 | 매칭 횟수 | 매칭 파일 수 |
|------|----------|-------------|
| `Response(` | 498 | 19 |
| `'success': True` | 63 | 2 (serverless, serverless_admin) |
| `"success": True` | 18 | 4 (stocks_fundamentals, rag_analysis, stocks_screener, stocks_exchange) |
| `'error':` | 159 | 12 |
| `'message':` | 99 | 10 |
| `'detail':` | 3 | 2 (users, config) |
| `status.HTTP_*` | 248 | 16 |
| `status=숫자` 하드코딩 | 4 | 2 (sec_pipeline, serverless) |
| `.objects.all()` / `.objects.filter(` | 174 | 11 |
| `paginate_queryset` / `PageNumberPagination` 등 DRF pagination | 0 | 0 |

> 주: rag_analysis는 `create_success_response()` 헬퍼를 거치므로 grep 카운트가 실제 사용량보다 낮게 잡힘.

