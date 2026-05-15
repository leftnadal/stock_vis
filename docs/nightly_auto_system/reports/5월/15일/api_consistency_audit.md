# API 응답 일관성 감사 보고서

> 작성일: 2026-05-15
> 범위: 프로젝트 내 모든 `views*.py` 25개 (총 13,047 라인) — 마이그레이션/캐시/노드 제외
> 모드: 읽기 전용 (코드 변경 없음)

---

## 요약

| 카테고리 | 현황 | 평가 |
|---|---|---|
| 응답 래핑 | 최소 6가지 형식 공존 — `{success,data,meta}` / 평탄 / `{results,pagination}` / `{count,items}` / raw list / `{error}` | 🔴 일관성 없음 |
| HTTP 상태 코드 | `status=status.HTTP_*` 178건 vs `status=숫자` 35건 (portfolio·sec_pipeline) | 🟡 혼용 |
| 201 Created 사용 | 14건만 사용 — POST 생성 엔드포인트 다수가 200 반환 또는 누락 | 🟡 부분 일관 |
| 204 No Content | 8건뿐 — 대부분 DELETE 엔드포인트가 `{message}` 또는 200 반환 | 🟡 미준수 |
| 에러 키 | `{'error': ...}` 167건, `{'message': ...}` 59건, `{'detail': ...}` 27건 (raw view 코드 기준) | 🔴 3가지 키 공존 |
| 글로벌 EXCEPTION_HANDLER | `{detail, code?, errors?, status_code}` 표준화됨 (settings.py:366) | 🟢 설정 OK |
| view 내 hand-rolled error vs handler | 표준 envelope는 raised 예외에만 적용, **`Response({'error':...}, status=...)` 패턴은 envelope를 우회** | 🔴 일관성 결손 |
| DRF 페이지네이션 (`pagination_class`) | **2 클래스만** (`StockListAPIView`, `NewsViewSet`) — `DEFAULT_PAGINATION_CLASS` 미설정 | 🔴 표면 미세팅 |
| 수동 페이지네이션 응답 형식 | `{results, pagination:{...}}` (users) vs `{count, history:[...]}` (rag_analysis) vs `{page, page_size, chains}` (chainsight) vs `{results, count, next, previous}` (serverless advanced_screener) | 🔴 4가지 형식 공존 |
| `.all()` / `.filter()` 페이지네이션 없이 직렬화 | 최소 8개소 (users, rag, validation, eod 등) | 🟡 응답 크기 폭주 위험 |

**핵심 결론**: `config/settings.py:344-367` 의 P0 #14 주석이 명시한 "응답 envelope 결정이 페이지네이션 전역화의 선결 조건"이 아직 미완료 → 5월 11일자 동일 감사 결과와 큰 변화 없음. envelope 표준이 view 레벨 코드까지 침투되지 않은 상태.

---

## 앱별 응답 패턴 매트릭스

| 파일 | 라인 | 성공 응답 1차 형식 | 에러 1차 키 | HTTP 코드 표기 | 201 사용 | 204 사용 | 페이지네이션 | 비고 |
|---|---:|---|---|---|:---:|:---:|---|---|
| `config/views.py` | 104 | `JsonResponse({...})` 평탄 | `JsonResponse` 평탄 | (없음) | — | — | — | 루트/헬스 — `endpoints/documentation/status` 평탄 |
| `metrics/views.py` | 3 | 빈 파일 | — | — | — | — | — | view 없음 |
| `chainsight/views.py` | 1 | 빈 파일 | — | — | — | — | — | API는 `chainsight/api/views.py` |
| `chainsight/api/views.py` | 814 | 평탄 dict (`center/nodes/edges/meta`, `chains/page/page_size`) | `{'error': str}` (8) | `status.HTTP_*` (8) | — | — | **수동** `page`/`page_size` (SignalFeedView) | Neo4j 직렬화 헬퍼 `_sanitize_neo4j` 사용 |
| `rag_analysis/views.py` | 772 | 평탄 dict / `{'results', 'pagination':{...}}` (UsageHistory) | `raise` 위주 (커스텀 예외 → handler envelope), 일부 `{'error': str}` (7) | `status.HTTP_*` (7) | 4건 | 3건 | **수동** `Paginator` (UsageHistoryView) | DELETE는 204 사용 (양호) |
| `serverless/views.py` | 2909 | **혼합** — 평탄 (`movers/breadth/heatmap` v2 envelope) / `{count, ...}` / `{results, count, next, previous}` (advanced_screener) | `{'error': str}` (6), `raise ValidationError` 다수 | `status.HTTP_*` (3) | 3건 | — | **수동** `page/page_size` (advanced_screener, execute_preset) | `function-based @api_view` 다수, `authentication_classes([])` 패턴 반복 |
| `serverless/views_admin.py` | 691 | 평탄 dict | `{'error': str}` (28) — `Response({'error': str(e)}, status=500)` 반복 패턴 | `status.HTTP_*` (30) | 1건 | 1건 | — | 모든 view에서 `try/except → 500 + 'error'` 동일 패턴 |
| `news/api/views.py` | 2198 | DRF `ViewSet` — list는 paginator envelope (`count/next/previous/results`), action은 평탄 dict | `raise ValidationError`, 일부 `{'error': str}` (3) | `status.HTTP_*` (7) | — | — | ✅ `PageNumberPagination` (`NewsArticlePagination`) | `pagination_class` 적용 — list/retrieve만, custom `@action`은 평탄 |
| `users/views.py` | 1088 | 평탄 dict 다수 / `{results, pagination}` (watchlist) / serializer.data raw | `{'error': str}` (8), `{'message': str}` (2), `raise NotFound/ParseError` | `status.HTTP_*` (33) | 6건 | 4건 | **수동** `Paginator` (Watchlist 2개소) | 회원가입 `serializer.errors` 그대로 반환 vs raise 분기 |
| `stocks/views.py` | 1030 | 평탄 dict (`symbol/tab/data/_meta/_source`), `_meta` 패턴 일관 | `{'error': str}` (12), 일부 `{'error': {'code', 'message', 'details'}}` (StockSyncAPIView, StockOverviewAPIView) | `status.HTTP_*` (25) | — | — | ✅ `PageNumberPagination` (`StockListPagination`) | 동일 파일 내 평탄 error vs 구조화 error 혼재 |
| `stocks/views_screener.py` | 498 | **`{success: True, data, meta}` envelope** (7건) | `{'error': str}` (8) | `status.HTTP_*` (8) | — | — | (limit param만, 페이지 없음) | screener 6개 view 전부 envelope 적용 |
| `stocks/views_exchange.py` | 295 | **`{success: True, data, meta}` envelope** (5건) | `{'error': str}` (8) | `status.HTTP_*` (8) | — | — | — | quotes 5개 view 전부 envelope 적용 |
| `stocks/views_fundamentals.py` | 305 | **`{success: True, data, meta}` envelope** (5건) | `{'error': str}` (10) | `status.HTTP_*` (10) | — | — | — | fundamentals 5개 view 전부 envelope |
| `stocks/views_market_movers.py` | 69 | 평탄 (`serializer.data`) | `{'error': str}` (1) | `status.HTTP_*` (1) | — | — | — | envelope 적용 안 함 |
| `stocks/views_search.py` | 229 | 평탄 (`count/results`) | `{'error': str}` (5) | `status.HTTP_*` (5) | — | — | hard-coded `[:10]` slice | envelope 미적용 |
| `stocks/views_indicators.py` | 372 | 평탄 dict (`indicators` 중첩) | `{'error': str}` (3) | `status.HTTP_*` (3) | — | — | — | envelope 미적용 |
| `stocks/views_eod.py` | 136 | 평탄 dict (`logs`, `stocks` 평탄) | `{'error': str}` (3) | `status.HTTP_*` (3) | — | — | hard-coded `[:50]`, `[:7]` | envelope 미적용 |
| `stocks/views_mvp.py` | 200 | 평탄 (`mode/count/data`) | (예외 없음) | — | — | — | hard-coded `[:20]` | envelope 미적용 |
| `macro/views.py` | 410 | `serializer.data` 평탄 | `{'error': str}` (15) | `status.HTTP_*` (15) | — | — | — | 동일 `try/except → 500 + 'error'` 패턴 7회 반복 |
| `portfolio/views.py` | 304 | `JsonResponse(result, status=200)` 평탄 | `{'error', 'detail'}` 이중 키 (24 + 27) | **숫자** `status=400/429/500/503` (32) | — | — | — | DRF 미사용 (순수 Django) — exception_handler 우회 |
| `sec_pipeline/views.py` | 51 | 평탄 (`symbol/status/message`) | (없음) | **숫자** `status=200/202` (3) | — | — | — | DRF Response 사용하지만 코드 하드코딩 |
| `graph_analysis/views.py` | 3 | 빈 파일 | — | — | — | — | — | — |
| `validation/api/views.py` | 561 | 평탄 dict (`symbol/categories/comparisons/peers`) | `{'error': str}` (15) | `status.HTTP_*` (12) | — | — | hard-coded `[:5]`, `[:50]` slice | envelope 미적용; 일부 view는 200으로 error semantics 응답 (`{symbol, error: 'insufficient_peers'}`) |
| `validation/views.py` | 1 | 빈 파일 | — | — | — | — | — | — |
| `news/views.py` | 3 | 빈 파일 | — | — | — | — | — | — |

### 응답 envelope 형식 — 동시 6종 공존

```text
1) {success: bool, data, meta}        — stocks/views_{screener,exchange,fundamentals}.py 만 (총 17건)
2) 평탄 dict (raw)                     — 압도적 다수 (chainsight, macro, rag, users 일부, validation, serverless 일부)
3) {results, pagination:{count,page,page_size,num_pages,has_next,has_previous}}
                                       — users/views.py (Watchlist 2개소)
4) {results, pagination:{current_page,page_size,total_pages,total_count,has_next,has_previous}}
                                       — rag_analysis/views.py (UsageHistoryView)  ← 키 이름 (3)과 다름
5) {results, count, next, previous, total_pages, current_page}
                                       — serverless/views.py advanced_screener_api
6) DRF NewsViewSet 기본 pagination     — news/api/views.py (PageNumberPagination)
   → {count, next, previous, results}
```

**문제**: 같은 코드베이스에서 "페이지네이션 응답"을 받는 프론트엔드는 endpoint마다 다른 키 (`count` vs `total_count` vs `total_pages` vs `num_pages`)를 파싱해야 함. 클라이언트 페이지네이션 헬퍼 표준화 불가.

---

## HTTP 상태 코드 일관성

### 표기 방식 — `status` 모듈 vs 하드코딩 숫자

```text
status=status.HTTP_*    — 178건 (16 파일)
status=<숫자 리터럴>     — 35건 (sec_pipeline/views.py 3건, portfolio/views.py 32건)
status=숫자=숫자 무인자  — 0건
```

- `portfolio/views.py` — 32건 전부 하드코딩. `status=400 / 429 / 500 / 503` 직접 사용. 다른 모든 파일은 `from rest_framework import status` 후 `status.HTTP_400_BAD_REQUEST` 사용.
- `sec_pipeline/views.py:45` `status=202` 직접 숫자. `202`는 `status.HTTP_202_ACCEPTED` 상수가 존재하지만 사용 안 함.

### 201 Created — POST 생성 시 일관성

| 위치 | POST 결과 → 응답 | 평가 |
|---|---|---|
| `users/views.py:107` 회원가입 | 201 + 직렬화 user | ✅ |
| `users/views.py:295` Portfolio 생성 | 201 + 직렬화 | ✅ |
| `users/views.py:639` Watchlist 생성 | 201 | ✅ |
| `users/views.py:731` WatchlistItem 추가 | 201 | ✅ |
| `users/views.py:918` WatchlistBulkAdd | **201 if added else 200** — 조건부 분기 | 🟡 |
| `users/views.py:1040` UserInterest bulk | **201 if created else 200** — 조건부 분기 | 🟡 |
| `serverless/views.py:921, 1221, 1525` (preset, alert, share) | 201 | ✅ |
| `serverless/views_admin.py:565` admin action | 201 | ✅ |
| `rag_analysis/views.py:63, 137, 291, 396` | 201 | ✅ |
| `portfolio/views.py` 의 POST endpoints (e2/e3/e5/e6) | **200** 으로 LLM 결과 반환 — 새로운 리소스 생성 아니므로 의도된 동작 | ✅ |
| `stocks/views.py` `StockSyncAPIView.post` | 200 / 500 분기 — 동기화 트리거지만 새 리소스 아님 | ✅ |
| `serverless/views.py` `trigger_sync`, `sync_now`, `trigger_keyword_generation` | **200** — Celery task 시작 결과지만 task가 새 리소스로 볼 여지 있음 | 🟡 |
| `validation/api/views.py:487` `PeerPreferenceView.post` | `update_or_create` 후 200 — 처음 생성이어도 200 | 🟡 |

**불일치**: bulk POST에서 `added/created`가 비어 있으면 200, 채워지면 201로 조건부 분기 (users 2건). 이 패턴은 다른 곳에선 사용되지 않음 — 클라이언트에서 200 응답을 보고 "성공" 처리하면 부분 실패 표현이 모호함.

### 204 No Content — DELETE 시 일관성

```text
HTTP_204_NO_CONTENT 사용:                 8건
  users/views.py:342, 688, 759, 1087     (Portfolio/Watchlist/Item/Interest DELETE)
  rag_analysis/views.py:100, 159, 424    (Basket/Item/Session DELETE)
  serverless/views_admin.py:1건
```

**DELETE 응답이 204가 아닌 사례** (불일치):

| 위치 | DELETE 응답 | 권장 |
|---|---|---|
| `serverless/views.py:973` `screener_preset_detail` DELETE | `Response({'message': 'Preset deleted successfully'})` (200) | 204 |
| `serverless/views.py:1257` `screener_alert_detail` DELETE | `Response({'message': 'Alert deleted successfully'})` (200) | 204 |
| `users/views.py:228` `RemoveFavorite.delete` | `Response({'message': 'Stock removed from favorites'})` (200) | 204 |
| `validation/api/views.py:494` `PeerPreferenceView.delete` | `Response({'status': 'ok', 'message': 'default로 리셋'})` (200) | 204 또는 일관 |
| `rag_analysis/views.py:184` `DataBasketClearView.delete` | `Response({'message': ..., 'deleted_count': ...})` (200) — 영향 받은 행 수 반환 필요 → 200 정당화 가능 | (의도된 200) |

### 에러 상태 코드 사용 패턴

```text
HTTP_400_BAD_REQUEST   → 가장 많이 사용 (검증 실패, 잘못된 파라미터)
HTTP_401_UNAUTHORIZED  → 거의 미사용 (로그인 분기에서 `raise NotAuthenticated`로 처리)
HTTP_403_FORBIDDEN     → `raise PermissionDenied`로 처리 — 직접 status= 사용 0건
HTTP_404_NOT_FOUND     → view 코드 직접 사용 (`'Stock {symbol} not found'`)
HTTP_422_UNPROCESSABLE_ENTITY — validation/api/views.py:67 1건만 ('not_in_universe')
HTTP_429_TOO_MANY_REQUESTS — stocks/views.py:938, portfolio/views.py(*4) 'budget_exceeded'
HTTP_500_INTERNAL_SERVER_ERROR — 전 view에 산재 (try/except)
HTTP_503_SERVICE_UNAVAILABLE  — stocks/views_exchange.py, portfolio/views.py, stocks/views_search.py
HTTP_207_MULTI_STATUS         — users/views.py:559 1건만 ('partially refreshed')
```

**일관성 결함**:

1. `404` 응답 형식 — 동일 의미에서 5가지 키:
   ```
   {'error': 'Stock {symbol} not found'}                   — validation, chainsight 등
   {'error': f'No price data available for {symbol}'}      — stocks/views_indicators.py
   {'error': f'종목 {symbol}의 데이터를 찾을 수 없습니다.'} — stocks/views_fundamentals.py (한글)
   raise NotFound(f"Portfolio not found")                  — users/views.py (DRF default → handler envelope)
   {'valid': False, 'error': 'Symbol not found'}           — stocks/views_search.py SymbolValidateView (다른 키)
   ```
2. validation `{symbol, error: 'no_leader'}` 같은 응답이 `200` 코드로 반환 — 에러 의미를 200에 실어 보냄 (semantic mismatch).

---

## 에러 응답 형식

### 키 사용 빈도 (view 코드의 직접 `Response({...})` 기준)

| 키 | 발생 건수 | 사용 파일 |
|---|---:|---|
| `'error'` | 167 | 17개 파일 (거의 전부) |
| `'message'` | 59 | portfolio, users, serverless, config, news 등 — 에러보단 성공 메시지로도 사용 |
| `'detail'` | 27 (raw view 코드) | portfolio (24), config(1), users(2) |

**핵심 모순**: `config/settings.py:366` 의 글로벌 `EXCEPTION_HANDLER` 가 표준 envelope를 정의함:

```python
# config/exception_handler.py:21-50
{detail, code?, errors?, status_code}
```

이 envelope는 `raise NotFound`, `raise ValidationError`, `raise PermissionDenied` 같이 **DRF 예외를 raise한 경우만** 적용. view 코드에서 `Response({'error': ...}, status=400)`로 직접 반환하면 handler를 거치지 않음 → 같은 endpoint의 검증 실패 응답이 두 가지 형식으로 갈라짐:

```python
# 같은 view 안에서
return Response({'error': '검색어를 입력하세요.'}, status=400)
# vs
raise ValidationError({'symbols': [...]})  # → {detail:"Validation failed.", code:"validation_error", errors:{...}, status_code:400}
```

### 가장 두드러진 anti-pattern

`serverless/views_admin.py` 의 모든 view 함수가 동일 구조 반복 (28회):

```python
try:
    data = AdminStatusService.get_*()
    return Response(data)
except Exception as e:
    logger.error(...)
    return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

- 글로벌 handler가 잡지 않는 평범한 `Exception` 으로 변환되므로 envelope 미적용
- `str(e)` 직접 노출 → stack 정보 누출 가능성
- 동일 코드 28회 복붙

`macro/views.py` 도 동일 패턴 7회 반복.

### portfolio/views.py 의 독자 envelope

`{"error": "code_str", "detail": str(exc)}` (예: `{"error": "budget_exceeded", "detail": "..."}`) — DRF 미사용으로 글로벌 handler 우회. portfolio만의 mini-envelope. 표면적으로는 envelope의 `code`/`detail` 와 유사하지만 키 이름 `error` vs 표준 `code`로 mismatch.

---

## 페이지네이션 현황

### DRF 공식 페이지네이션 (`pagination_class`) 사용

| 위치 | 클래스 | 응답 키 |
|---|---|---|
| `stocks/views.py:91` `StockListAPIView` | `StockListPagination(PageNumberPagination)` page_size=50, max=200 | DRF 기본: `{count, next, previous, results}` |
| `news/api/views.py:60` `NewsViewSet` | `NewsArticlePagination(PageNumberPagination)` page_size=20, max=100 | DRF 기본: `{count, next, previous, results}` (단, `@action` custom action은 미적용) |

전 코드베이스에서 **총 2개의 클래스 기반 view만** DRF 공식 페이지네이션 적용. `CursorPagination`/`LimitOffsetPagination` 사용 0건.

### 수동 페이지네이션 — 4가지 형식

| 위치 | 메커니즘 | 응답 envelope |
|---|---|---|
| `users/views.py:603-628` WatchlistListCreateView.get | Django `Paginator` | `{'results':[...], 'pagination':{count,page,page_size,num_pages,has_next,has_previous}}` |
| `users/views.py:823-848` WatchlistStocksView.get | Django `Paginator` | 위와 동일 |
| `rag_analysis/views.py:707-737` UsageHistoryView.get | Django `Paginator` | `{'results':[...], 'pagination':{current_page,page_size,total_pages,total_count,has_next,has_previous}}` ← 키 이름 (`current_page`/`total_count`/`total_pages`) 다름 |
| `chainsight/api/views.py:631-810` SignalFeedView.get | 수동 `page`/`page_size` 슬라이스 (FilterEngine 내부) | `{page,page_size,sector,total,...,chains:[]}` |
| `serverless/views.py:1095-1164` advanced_screener_api | `FilterEngine` 내부 + `next_url`/`previous_url` 수동 빌드 | `{results, count, next, previous, total_pages, current_page}` ← 또 다른 키 조합 |
| `serverless/views.py:978-1020` execute_preset | 수동 `page/page_size/offset` | `FilterEngine` 결과 그대로 spread |

### `.all()` / `.filter()` 페이지네이션 없이 반환 — 응답 폭주 위험

```text
.objects.(all|filter) 의 view 내 사용:  174건 (11 파일)
```

페이지네이션 없이 직렬화하여 반환하는 endpoint (대표적):

| 위치 | 쿼리 | 위험도 |
|---|---|---|
| `users/views.py:92` `Users.get` | `User.objects.all()` (admin 한정) | 🟡 admin only |
| `users/views.py:193` `UserFavorites.get` | `user.favorite_stock.all()` | 🟡 사용자별이지만 무제한 |
| `users/views.py:264` `PortfolioListCreateView.get` | `Portfolio.objects.filter(user=...)` | 🟡 사용자별이지만 무제한 |
| `users/views.py:403` `PortfolioDetailTableView.get` | `Portfolio.objects.filter(user=...)` | 🟡 사용자별 |
| `users/views.py:975` `UserInterestListCreateView.get` | `UserInterest.objects.filter(user=...).order_by('-created_at')` | 🟡 사용자별 |
| `rag_analysis/views.py:52` `DataBasketListCreateView.get` | `DataBasket.objects.filter(user=...)` | 🟡 |
| `rag_analysis/views.py:379` `AnalysisSessionListCreateView.get` | `AnalysisSession.objects.filter(user=...)` | 🟡 |
| `rag_analysis/views.py:440` `SessionMessagesView.get` | `session.messages.all().order_by('created_at')` | 🟡 길이 가능성 |
| `stocks/views.py:264` `StockOverviewAPIView` 등 — 단일 객체 | (해당 없음) | — |
| `validation/api/views.py` `LeaderComparisonView` | 카테고리×지표 곱 — 내부적으로 모든 metric 순회 | 🟡 |
| `stocks/views_eod.py:42` `EODDashboardView` | `EODDashboardSnapshot.objects.filter(date=...).first()` JSON 통째 반환 | 🟢 단건이지만 payload 큼 |
| `stocks/views_eod.py:78` `EODSignalDetailView` | `[:50]` hard-coded slice | 🟢 캡 있음 |
| `stocks/views_eod.py:119` `EODPipelineStatusView` | `[:7]` hard-coded slice | 🟢 캡 있음 |
| `stocks/views_search.py:202` `StockSearchAPIView` | `[:20]` slice | 🟢 캡 있음 |
| `stocks/views_indicators.py:333` `IndicatorComparisonView` | 50개 인덱스 슬라이스 + 50 종목 반복 | 🟢 캡 있음 |
| `stocks/views_mvp.py:41` `StockMVPListView` | `queryset[:20]` | 🟢 캡 있음 |

**관찰**: 무제한 `.filter(user=...)` 반환은 "사용자별로 적당히 적을 것"이라는 암묵 가정에 의존. 5월 11일 감사에서 동일 지적, 변화 없음. portfolios/baskets/watchlists 등에 봇/이상 행위 시 응답 폭주 가능.

---

## 권고사항

코드 변경은 권고 대상 — 본 보고서는 읽기 전용. 우선순위 순으로 정리:

### P0 — 즉시 결정 필요 (다른 P1/P2의 선결 조건)

1. **응답 envelope 표준 단일화** — 글로벌 EXCEPTION_HANDLER 가 이미 `{detail, code?, errors?, status_code}` 를 정의하고 있으므로:
   - 성공 envelope을 표준화 (예: `{data: <T>, meta?: {...}}` 또는 평탄 dict — 둘 중 하나로 통일)
   - 현재 `stocks/views_{screener,exchange,fundamentals}.py` 의 `{success, data, meta}` vs 평탄 dict 둘 중 정책 결정
   - `settings.py:347` 주석에 명시된 "응답 envelope 결정이 선결 조건"이 이미 한 달 이상 미해결

2. **view 코드의 `Response({'error': str})` 패턴 일소** → `raise ValidationError/NotFound/...` 로 마이그레이션
   - `serverless/views_admin.py`, `macro/views.py` 의 동일한 `try/except Exception → Response({'error': str(e)}, status=500)` 코드 28+7회 = 35회 → 글로벌 handler에 위임 (또는 `APIException` 서브클래스 1개 정의)
   - portfolio는 DRF 미사용 → DRF로 마이그레이션하거나 별도 portfolio용 envelope 명시적 분리

### P1 — 일관성 회복

3. **HTTP 상태 코드 표기 통일** — `status=숫자` (portfolio 32건, sec_pipeline 3건) → `status=status.HTTP_*` 로 통일.

4. **201 Created 규칙 명문화** — POST 후 새 리소스 생성 시 무조건 201, bulk endpoint도 201 (부분 실패는 응답 body 의 `errors` 배열로 표현). 현재 users의 "added 있으면 201, 없으면 200" 분기는 불일치.

5. **DELETE → 204 통일** — `users/views.py:228` (RemoveFavorite), `serverless/views.py:973/1257` (preset/alert) 등 5건 → 204. 200으로 반환할 수밖에 없는 경우 (`deleted_count` 반환)는 별도 문서화.

6. **에러 키 통일** — view 코드 직접 응답이 남아 있는 한 `'error'` 키만 사용 (가장 빈도 높음). 단, 글로벌 handler 통과 응답은 `'detail'` — 두 채널이 공존하므로 **클라이언트는 두 키를 모두 처리해야 함**을 명시. 또는 P0 #2로 view 코드 응답을 0건으로 만들면 자연스럽게 `'detail'` 단일화.

### P2 — 페이지네이션 표준화

7. **`REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']` 설정** — `PageNumberPagination` 또는 `LimitOffsetPagination` 전역 도입. `PAGE_SIZE`/`DEFAULT_PAGE_SIZE` 명시.
   - 단, `@api_view` 함수형 view (serverless의 17개 endpoint)와 `APIView` 내 수동 list는 자동 적용 안 됨 → 별도 마이그레이션 필요.
   - 현재 envelope 형식(`{success,data,meta}`)이 DRF 기본 envelope(`{count,next,previous,results}`)와 충돌 → P0 #1 선결 필요.

8. **수동 페이지네이션 응답 키 통일** — `users/views.py` (`page/num_pages`) vs `rag_analysis/views.py` (`current_page/total_pages/total_count`) vs `serverless/views.py` (`current_page/total_pages/count`) 의 3가지 키 조합을 하나로 통일 (DRF 기본 `{count,next,previous,results}` 권장).

9. **무제한 `.filter()` 직렬화에 페이지네이션 도입** — Portfolio/Watchlist/Basket/Interest/Session 등 사용자별 리스트는 모두 페이지네이션 또는 hard-coded `[:N]` slice 보강. 특히 `Watchlist`는 이미 `Paginator` 사용했으므로 `Portfolio`도 동일 패턴 도입 가능.

### P3 — 미세 개선

10. `chainsight/api/views.py` 의 200 응답에 `{'error': 'no_leader'}` 같은 semantic-error 형식 제거 → 404/422로 정정 또는 별도 `status` 필드 명시.

11. `stocks/views.py` `StockSyncAPIView` 의 `{'error': {'code', 'message', 'details'}}` 중첩 envelope는 글로벌 handler 와 키가 다름 (`code` 위치) → 글로벌 envelope로 통합.

12. `validation/api/views.py:67` HTTP_422 — 코드베이스에서 유일한 422 사용. 422 사용 정책(검증 vs semantic mismatch) 결정 후 일관 적용.

---

## 참고 데이터 (raw grep 결과 요약)

```text
Response()                : 458건 / 20 파일
JsonResponse()            :  34건 /  2 파일 (config, portfolio)
'success': True           :  17건 /  3 파일 (stocks/views_screener|exchange|fundamentals)
'success': False          :   0건
'error': ...              : 167건 / 17 파일
'detail': ...             :  27건 /  3 파일 (portfolio 24, users 2, config 1)
'message': ...            :  59건 / 10 파일
status=숫자(리터럴)        :  35건 /  2 파일 (sec_pipeline, portfolio)
status=status.HTTP_*      : 178건 / 16 파일
HTTP_201_CREATED          :  14건
HTTP_204_NO_CONTENT       :   8건
PageNumberPagination 사용  :   2 클래스 (StockListAPIView, NewsViewSet)
CursorPagination 사용      :   0건
LimitOffsetPagination 사용 :   0건
pagination_class=          :   2건
수동 page/page_size       :  최소 6 endpoints (chainsight, serverless 2개, rag 1개, users 2개)
.objects.(all|filter)     : 174건 / 11 파일
```

EXCEPTION_HANDLER: `config/exception_handler.py` — `{detail, code?, errors?, status_code}` (DRF raised exceptions only)
DEFAULT_PAGINATION_CLASS: **미설정** (`config/settings.py:348-367`)
DEFAULT_PERMISSION_CLASSES: `IsAuthenticated` (2026-04-29 P0 #5)

---

(보고서 끝)
