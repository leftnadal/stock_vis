# API 응답 일관성 감사 보고서

- **감사 일시**: 2026-04-25 (야간 자동화 세션)
- **대상 범위**: Backend 27개 view 파일 + DRF 전역 설정
- **모드**: 읽기 전용 (코드 수정 없음)
- **분석 기준**: Response() 래핑 패턴, HTTP 상태 코드, 에러 형식, 페이지네이션

---

## 요약

Stock-Vis 백엔드 API는 앱별로 응답 패턴이 **4가지 이상으로 분기**되어 있어 프론트엔드가 단일 응답 컨트랙트를 가질 수 없는 상태입니다. 가장 심각한 이슈는 다음 4가지입니다.

| # | 이슈 | 심각도 | 영향 범위 |
|---|------|--------|---------|
| 1 | **응답 래핑 4가지 패턴 공존** (직접 반환 / `{success, data}` / `{success, error}` / `{message, data}`) | 🔴 높음 | 전체 앱 |
| 2 | **에러 키 3종 혼용** (`error` / `detail` / `message`) | 🔴 높음 | users, chainsight, validation, news 등 |
| 3 | **페이지네이션 부재** — DRF 전역 설정 없음, 목록 API 대다수가 `.all()`/`.filter()` 직접 반환 | 🔴 높음 | stocks, news, serverless, users, validation |
| 4 | **POST 생성 시 201 사용 불일치** — 일부는 201, 일부는 200, 일부는 조건부 | 🟡 중간 | users, thesis, chainsight, news |

긍정적 발견: `status.HTTP_xxx` 상수는 거의 모든 파일에서 일관되게 사용되며 하드코딩된 숫자는 발견되지 않았습니다.

---

## 앱별 응답 패턴 매트릭스

성공 응답 래핑 + 에러 응답 형식을 앱 단위로 정리한 매트릭스입니다.

| 앱 | 성공 응답 래핑 | 에러 키 | 에러 본문 형식 | DRF Pagination | 비고 |
|----|---------------|---------|---------------|----------------|------|
| **stocks/** | 혼용 (`{success, data}` + 직접) | `error` (단순) + `error` (중첩) + `message` | `{'error': str}`, `{'error': {code, message, details}}` | 없음 | 가장 심한 혼용 |
| **users/** | 혼용 (직접 + `{message, ...}` + `{ok, ...}`) | `error`, `message`, `serializer.errors`, ParseError/NotFound 예외 | `{'error': str}` 14회 + `{'message': str}` 8회 | 수동 (Paginator) | 7가지 패턴 공존 |
| **thesis/** | 직접 반환 | `error` (수동) + ValidationError (DRF) | `{'error': str}` | ❌ 없음 (`pagination_class` 미정의) | 비교적 일관됨 |
| **chainsight/** | 직접 반환 | `error` (api/views.py) vs `detail` (watchlist_views.py) | `{'error': str}` vs `{'detail': str}` | ❌ 없음 (SignalFeedView만 수동 페이지) | 같은 앱 내 키 충돌 |
| **validation/** | 직접 반환 | `error` (수동) | `{'error': str}` | ❌ 없음 | |
| **serverless/** | 분기: `views.py`는 `{success, data/error}`, `views_admin.py`는 직접 | `error` 객체 (`{code, message}`) vs 단순 `error` | views.py 35회 구조화 vs views_admin.py 단순 | 부분 (수동 offset/limit, advanced_screener/alert_history만) | 같은 앱 내 두 형식 |
| **rag_analysis/** | `create_success_response()` 헬퍼 (`{success, data}`) | `create_error_response()` (`{success, error: {code, message}}`) | 일관됨 | Django Paginator (UsageHistoryView만) | **가장 표준화됨** |
| **news/** | 직접 반환 | `error` + DRF ValidationError 혼용 | `{'error': str}` | ❌ 없음 | stock_news 등 전체 반환 위험 |
| **macro/** | 직접 반환 | `error` | `{'error': str}` (일관됨) | ❌ 없음 | |
| **graph_analysis/** | (모델/서비스만, API 미구현) | - | - | - | |
| **sec_pipeline/** | 직접 반환 | `error` | `{'error': str}` | ❌ 없음 | |
| **metrics/** | 직접 반환 | `error` | `{'error': str}` | ❌ 없음 | |

### 패턴별 카운트 (대표 사례)

| 패턴 | 사용 앱 | 대표 예시 |
|------|---------|----------|
| `Response(serializer.data)` 직접 | stocks/, users/, thesis/, chainsight/, validation/, news/, macro/ | `users/views.py:52, 92, 190` / `thesis/views/conversation_views.py:136` |
| `{'success': True, 'data': ...}` | stocks/views_exchange.py, stocks/views_fundamentals.py, serverless/views.py, rag_analysis/views.py | `stocks/views_exchange.py:68-75` / `serverless/views.py:91-98` / `rag_analysis/views.py:75` |
| `{'success': False, 'error': {'code', 'message'}}` | serverless/views.py, rag_analysis/views.py | `serverless/views.py:71-76` / `rag_analysis/views.py:150-154` |
| `{'message': str, 'data': ...}` 또는 `{'ok': '...', 'user': ...}` | users/ | `users/views.py:160-168` (LogIn) / `215-218` (AddFavorite) |
| `{'results': [...], 'pagination': {...}}` 수동 | users/ | `users/views.py:610-620, 830-840` |

---

## HTTP 상태 코드 일관성

### 모듈 사용

`status.HTTP_xxx_xxx` 상수가 거의 모든 파일에서 일관되게 사용됩니다. **하드코딩된 숫자는 발견되지 않았습니다**. (확인 파일: `users/views.py:10`, `macro/views.py:7`, `config/views.py:9`, stocks/* 전체)

### POST 생성 시 201 vs 200 불일치

| 앱/뷰 | POST 생성 응답 | 라인 |
|------|--------------|------|
| `users/views.py` (UserCreate, Portfolio create 등) | **201 CREATED** ✅ | `105, 288, 631, 723` |
| `users/views.py` WatchlistBulkAddView | **조건부**: 추가된 항목 있으면 201, 없으면 200 | `910` (`status=status.HTTP_201_CREATED if added else status.HTTP_200_OK`) |
| `users/views.py` UserInterestListCreateView | **조건부**: 동일 | `1032` |
| `chainsight/views/watchlist_views.py` create | **201 CREATED** ✅ | `95` |
| `serverless/views.py` POST 엔드포인트 | **201 CREATED** ✅ | `1060, 1428, 1819` |
| `rag_analysis/views.py` POST | **201 CREATED** ✅ | `84, 164, 346` |
| `thesis/views/thesis_views.py` ThesisViewSet.perform_create | **암묵적 200** ⚠️ | DRF 기본 동작에 의존 |
| `thesis/views/conversation_views.py` post | **암묵적 200** ⚠️ | `136, 144, 173, 188` |
| `validation/api/views.py` PeerPreferenceView post | **200 OK** ⚠️ | `484` |
| `news/api/views.py` 일부 POST | **암묵적 200** ⚠️ | `104, 217` |
| `stocks/views.py` StockSyncAPIView.post | **200 OK** ⚠️ | `981-986` (생성/갱신을 200으로 통합) |

### DELETE 응답 코드

| 앱 | DELETE 응답 |
|----|-----------|
| `users/views.py` | **204 NO_CONTENT** ✅ (`335, 680, 751, 1079`) |
| `rag_analysis/views.py` | **204 NO_CONTENT** ✅ (`129, 202, 487`) |
| `serverless/views.py` | 200/204 혼용 |

### 에러 상태 코드 분포

| 상태 코드 | 사용 빈도 | 일관성 |
|---------|---------|-------|
| 400 BAD_REQUEST | 매우 많음 | 양호 (검증 실패 표준 사용) |
| 401 UNAUTHORIZED | 적음 | `users/views.py:167` (LogIn), `serverless/views.py:1413, 2112`, `validation/api/views.py:463, 489` 정도만 사용 |
| 403 FORBIDDEN | 중간 | `serverless/views.py` 8회 (`1110, 1133, 1139, 1459, 1512`) — 다른 앱은 거의 안 씀 |
| 404 NOT_FOUND | 많음 | 양호 |
| 207 MULTI_STATUS | 1회 | `users/views.py:552` (부분 성공) — 매우 예외적 |
| 429 TOO_MANY_REQUESTS | 2회 | `stocks/views.py:928`, `serverless/views_admin.py:369` |
| 500 INTERNAL_SERVER_ERROR | 많음 | 양호 |
| 503 SERVICE_UNAVAILABLE | 일부 | FMP/외부 API 실패 시 (`stocks/views_exchange.py:58`, `chainsight/api/views.py:435` 등) |

### 동일 의미 다른 코드 사례

같은 "데이터 없음" 상황을 어느 곳은 404, 어느 곳은 503으로 반환하는 사례가 stocks/views_screener.py와 stocks/views_exchange.py에서 관찰됩니다.

---

## 에러 응답 형식

### 키 사용 매트릭스

| 에러 키 | 사용 파일 (대표) | 출현 |
|--------|----------------|------|
| `error` (단순 문자열) | `stocks/views.py:172-176, 207-208, 310-312`, `users/views.py:166, 209, 237, 432, 536, 557, 707-708`, `validation/api/views.py:59, 180, 189, 508`, `chainsight/api/views.py:67, 113, 188, 228`, `news/api/views.py:678-679`, `serverless/views_admin.py:163, 183, 203`, `macro/views.py:46, 71, 102, 133, 164, 210, 240, 264, 385`, `thesis/views/conversation_views.py:164, 179` | 매우 많음 (50+회) |
| `error` (중첩 객체 `{code, message, details}`) | `stocks/views.py:587-595, 920-927`, `serverless/views.py:71-76, 141-147`, `rag_analysis/views.py:150-154, 169-174` | 다수 |
| `detail` | `chainsight/views/watchlist_views.py:102, 119, 136, 143, 174, 214, 233` | 7회 |
| `message` | `stocks/views.py:174, 182`, `users/views.py:208, 236, 505, 544, 557-558` | 8회 + |
| `serializer.errors` (raw) | `users/views.py:66, 107, 292, 329, 467, 632, 669, 725, 789`, `stocks/views_screener.py:66-67` | 9+회 |
| DRF `raise ValidationError` | `news/api/views.py:624, 662, 668, 672`, `users/views.py:855, 925, 995`, `thesis/views/conversation_views.py:124`, `thesis/views/thesis_views.py:124`, `chainsight/views/watchlist_views.py:57` | 다수 |
| DRF `raise ParseError`/`NotFound` | `users/views.py:97, 116, 132, 139, 150, 204, 309, 487, 649, 697, 741, 753, 769, 778` | 14회 |

### 동일 앱 내 키 충돌 (핵심 사례)

**chainsight/** — `api/views.py`는 `error`, `views/watchlist_views.py`는 `detail` 사용
```
api/views.py:67           {'error': '...'}
views/watchlist_views.py:102 {'detail': '이미 archived 상태입니다.'}
```

**users/** — 같은 뷰 내에서도 키가 다름
```
users/views.py:160-168 (LogIn)            {'ok': '...', 'user': ...} (성공)
users/views.py:166 (LogIn)                {'error': '...'} (실패)
users/views.py:215-218 (AddFavorite)      {'message': '...', 'stock': ...} (성공)
users/views.py:208 (AddFavorite)          {'message': '...'} (실패에도 message)
```

**serverless/** — 같은 앱 내에서 단순 문자열 vs 중첩 객체
```
serverless/views.py:71-76     {'success': False, 'error': {'code': 'INVALID_TYPE', 'message': '...'}}
serverless/views_admin.py:163-165 {'error': str(e)}
```

**stocks/** — 단순 문자열, 중첩 객체, message 키 3종 공존
```
stocks/views.py:172-176       {'error': '...'}
stocks/views.py:587-595       {'error': {'code': 'OVERVIEW_ERROR', 'message': '...', 'details': {...}}}
stocks/views.py:174           {'result': [], 'message': '...'}  # 'result' 오타 (다른 곳은 'results')
```

### DRF 표준 vs 수동 Response 혼용

`raise ValidationError`(DRF)와 `return Response({'error': ...}, status=400)`(수동)이 **같은 뷰 안에서도** 섞여 사용됩니다.
- `users/views.py` WatchlistItemAddView (`706-709`): 수동 Response
- `users/views.py` WatchlistListCreateView (`855`): `raise ValidationError`
- `news/api/views.py` (`624, 662`): `raise ValidationError`
- `news/api/views.py` (`678-679`): 수동 Response

---

## 페이지네이션 현황

### DRF 전역 설정

`config/settings.py:321-329`:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}
```

| 설정 | 값 | 평가 |
|------|---|------|
| `DEFAULT_PAGINATION_CLASS` | **미설정** | ❌ |
| `PAGE_SIZE` | **미설정** | ❌ |
| `EXCEPTION_HANDLER` | **미설정** (DRF 기본) | ❌ (커스텀 핸들러 없음 → 에러 통일 불가) |
| `DEFAULT_AUTHENTICATION_CLASSES` | JWT + Session | ✅ |
| `DEFAULT_PERMISSION_CLASSES` | IsAuthenticatedOrReadOnly | ✅ |

### 페이지네이션 부재 목록 API (위험도 순)

| 위험도 | 엔드포인트 | 파일:라인 | 반환 형태 |
|-------|----------|---------|---------|
| 🔴 높음 | `StockListAPIView` | `stocks/views.py:75-105` | `Stock.objects.all()` 전체 반환 (전체 종목 - 수만 row 가능) |
| 🔴 높음 | `stock_news` | `news/api/views.py:87-104` | `.filter().distinct()` 전체 |
| 🔴 높음 | `stock_sentiment` | `news/api/views.py:129-133` | 필터된 전체 데이터 |
| 🔴 높음 | `screener_presets_api` | `serverless/views.py:1017-1044` | 전체 queryset 직렬화 |
| 🔴 높음 | `screener_filters_api` | `serverless/views.py:1234-1268` | 전체 queryset |
| 🟡 중간 | `screener_alerts_api` (GET) | `serverless/views.py:1393-1406` | 전체 알림 |
| 🟡 중간 | `PortfolioListCreateView.get()` | `users/views.py:255-259` | `Portfolio.objects.filter(user=...)` 전체 |
| 🟡 중간 | `UserFavorites.get()` | `users/views.py:185-190` | `user.favorite_stock.all()` 직접 배열 |
| 🟡 중간 | `ThesisViewSet` 목록 | `thesis/views/thesis_views.py` | `pagination_class` 미정의 |
| 🟡 중간 | `WatchlistViewSet` 목록 | `chainsight/views/watchlist_views.py` | `pagination_class` 미정의 |
| 🟢 낮음 (수동 limit 있음) | `StockScreenerView` | `stocks/views_screener.py:110-127` | 서비스 레벨 `limit` 파라미터 |
| 🟢 낮음 (수동 limit 있음) | `LargeCapStocksView` | `stocks/views_screener.py:269-270` | 서비스 레벨 `limit` |
| 🟢 낮음 (수동 limit 있음) | `StockMVPListView` | `stocks/views_mvp.py:41` | `queryset[:20]` |
| 🟢 낮음 (수동 limit 있음) | `EODSignalDetailView` | `stocks/views_eod.py:78` | `[:50]` |
| 🟢 낮음 (수동 limit 있음) | `AlertListView` | `thesis/views/monitoring_views.py:238` | `[:50]` |
| 🟢 낮음 (수동 limit 있음) | `NewsIssuesView` | `thesis/views/conversation_views.py:200-201` | `[:12]` |

### 페이지네이션 구현 사례

| 파일 | 방식 | 평가 |
|------|------|------|
| `users/views.py:602-620, 822-840` (WatchlistListCreateView) | `django.core.paginator.Paginator` 수동 + `{results, pagination: {count, page, page_size, num_pages, has_next, has_previous}}` | 자체 표준 형성, **DRF 표준 형식과 다름** |
| `rag_analysis/views.py:778-826` (UsageHistoryView) | `django.core.paginator.Paginator` | 양호 |
| `serverless/views.py:1312-1357` (advanced_screener), `1550-1573` (alert_history) | 수동 offset/limit 계산 | 위 두 형식과도 다른 별개 |
| `chainsight/api/views.py:796-798` (SignalFeedView) | 수동 page/page_size 슬라이싱 | 또 다른 형식 |

**총평**: DRF `pagination_class`/`paginate_queryset()` 사용은 **0건**. 모든 페이지네이션은 4가지 다른 수동 형식으로 구현됨.

---

## 권고사항

> 본 보고서는 읽기 전용 감사이며, 아래 권고는 후속 작업 계획용입니다.

### P0 (즉시 — 동일 앱 내 키 충돌부터)

1. **chainsight 앱 에러 키 통일** — `api/views.py`(`error`)와 `views/watchlist_views.py`(`detail`)이 한 앱 내에서 다름. 둘 중 하나로 일원화 필요. (관련: `chainsight/api/views.py:67`, `chainsight/views/watchlist_views.py:102`)
2. **stocks/views.py 오타 정리** — `'result'` (`172-176`)와 `'results'` (`180-183`) 키 혼용. 단일 키로 정정.
3. **users/views.py LogIn 응답 일관화** — `{'ok': ...}`는 다른 어떤 뷰에서도 사용되지 않는 비표준 키 (`160-168`).

### P1 (단기 — 컨트랙트 표준화)

1. **응답 래핑 표준 결정** — 다음 두 안 중 하나를 `DECISIONS.md`에 명시:
   - **(A) DRF 표준**: 성공 = `Response(data)` 직접, 에러 = `{'detail': str}` (DRF 기본 ValidationError 재사용)
   - **(B) 봉투 패턴**: `rag_analysis/`/`serverless/views.py`의 `{success, data, error: {code, message}}` 형식을 전역 표준으로 채택
2. **커스텀 EXCEPTION_HANDLER 도입** — `REST_FRAMEWORK['EXCEPTION_HANDLER']`에 핸들러 등록하여 `{'error': str}` / `{'detail': str}` / `{'message': str}` 혼용을 1지점에서 표준화.
3. **POST 생성 응답을 201로 통일** — `thesis/`, `validation/api/`, `news/api/`, `stocks/views.py:981-986`의 200 반환을 201로 정리. 조건부 201/200 (users `WatchlistBulkAddView`, `UserInterestListCreateView`)도 정책 결정 필요.

### P2 (중기 — 페이지네이션 도입)

1. **DRF 전역 페이지네이션 설정**:
   ```python
   REST_FRAMEWORK = {
       ...,
       'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
       'PAGE_SIZE': 50,
   }
   ```
2. **위험도 🔴 목록 API 우선 적용** — `StockListAPIView`, `stock_news`, `stock_sentiment`, `screener_presets_api`, `screener_filters_api` 5개부터.
3. **수동 페이지네이션 4종 통일** — `users/`, `rag_analysis/`, `serverless/`, `chainsight/SignalFeedView`의 4가지 다른 형식을 DRF 표준으로 점진 마이그레이션.

### P3 (장기 — 컨트랙트-드리븐 강화)

1. `contracts/` OpenAPI 스펙에 표준 응답 봉투 정의 추가 (Component 재사용)
2. `@frontend`가 사용하는 axios 인터셉터에서 봉투 풀어주는 단일 어댑터 도입
3. CI에 응답 형식 lint 추가 (예: `Response({'message': ...})` 패턴 검출)

---

## 부록: 분석 대상 파일 목록 (27개)

```
config/views.py
metrics/views.py
macro/views.py
users/views.py
graph_analysis/views.py
sec_pipeline/views.py

stocks/views.py
stocks/views_exchange.py
stocks/views_screener.py
stocks/views_market_movers.py
stocks/views_eod.py
stocks/views_indicators.py
stocks/views_search.py
stocks/views_fundamentals.py
stocks/views_mvp.py

thesis/views/__init__.py
thesis/views/conversation_views.py
thesis/views/monitoring_views.py
thesis/views/thesis_views.py

validation/views.py
validation/api/views.py

chainsight/views.py
chainsight/views/__init__.py
chainsight/views/watchlist_views.py
chainsight/api/views.py

serverless/views.py
serverless/views_admin.py

rag_analysis/views.py

news/views.py
news/api/views.py
```

DRF 전역 설정 확인: `config/settings.py:321-329`
