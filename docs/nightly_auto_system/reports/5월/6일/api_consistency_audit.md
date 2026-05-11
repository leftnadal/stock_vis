# API 응답 일관성 감사 보고서

- **감사일**: 2026-05-07
- **대상**: Stock-Vis Backend 전체 `views*.py` (25개 파일, 약 9,991 LoC)
- **방법**: 코드 수정 없이 정적 분석 (Read + Grep)
- **목적**: 앱 간 Response 형식 불일치, HTTP 상태 코드 정합성, 에러 포맷, 페이지네이션 누락 식별

---

## 요약

Stock-Vis는 **단일한 Response 컨벤션이 없음** — 같은 도메인(stocks)·같은 사용자 흐름(Watchlist↔Portfolio) 내부에서도 서로 다른 래핑 형식을 혼용한다. 핵심 문제는 다음 5가지로 요약된다.

1. **응답 래핑 형식 4종 혼재**: `{success, data, meta}` / 직접 데이터 / `{error: {code, message}}` / DRF 기본 (`{detail}`/`serializer.errors`)이 앱별·뷰별로 무규칙 혼용. 프론트엔드 단일 클라이언트가 `data.data?.x ?? data.x` 같은 방어 코드를 쓰게 만들 가능성이 높다.
2. **에러 응답 4종 혼재**: `error` 키와 `detail` 키, 구조화 에러(`{code, message, details}`)와 평문 에러가 섞여 있다 — 동일 앱(stocks, users, validation) 내에서도 일관되지 않음.
3. **DRF 페이지네이션 글로벌 미설정**: `config/settings.py`의 `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS` 자체가 없으며, 어느 ViewSet/APIView도 `pagination_class`를 지정하지 않는다. 페이지네이션이 필요한 목록 API 다수가 **무제한 반환** 또는 **하드코딩 슬라이스**(`[:50]`, `[:20]`)로 처리.
4. **HTTP 상태 코드 사용은 비교적 양호**: `status.HTTP_xxx` 모듈 사용이 보편적이나, `portfolio/views.py`(JsonResponse + DRF 미사용)와 `sec_pipeline/views.py`만 하드코딩 숫자(`status=200/202/400/500/503`) 사용.
5. **207 MULTI_STATUS**, **202 ACCEPTED** 등 비표준 코드를 단발성으로 사용한 위치가 있어 전체 컨벤션 부재를 시사.

---

## 앱별 응답 패턴 매트릭스

`✓` = 해당 패턴이 그 앱에서 우세, `△` = 일부 뷰에서만, `✗` = 사용 안 함.

| 앱 / 파일 | `{success, data, meta}` | 직접 데이터 (`Response(data)`) | `{success, error:{code,message}}` | DRF 기본 (`{detail}`) | 비고 |
|---|---|---|---|---|---|
| `stocks/views.py` (StockSearch, Chart, Overview, Sync) | ✗ | ✓ | △ (Overview 500 에러만) | ✗ | OverviewError는 `{error:{code,message,details}}`, 외 평문 |
| `stocks/views_eod.py` | ✗ | ✓ | ✗ | ✗ | 평문 `{error: str}` |
| `stocks/views_market_movers.py` | ✗ | ✓ | ✗ | ✗ | Serializer 결과 직접 반환 |
| `stocks/views_indicators.py` | ✗ | ✓ | ✗ | ✗ | 평문 `{error: str}` |
| `stocks/views_search.py` | ✗ | ✓ | ✗ | ✗ | 평문 `{error: str}` |
| `stocks/views_fundamentals.py` | ✓ | ✗ | ✗ | ✗ | `{success, data, meta:{symbol, period, count, timestamp}}` 일관 |
| `stocks/views_screener.py` | ✓ | ✗ | ✗ | ✗ | Enhanced/Instant 두 분기 모두 wrapped |
| `stocks/views_exchange.py` | ✓ | ✗ | ✗ | ✗ | 동일 wrapped |
| `stocks/views_mvp.py` | ✗ | ✓ | ✗ | ✗ | 자체 형식 (`{mode, count, data}`) |
| `users/views.py` (auth, portfolio, watchlist) | ✗ | ✓ | ✗ | △ | Login은 `{ok, user}`, Favorite은 `{message, stock}`; Bulk는 `{added, skipped, errors, summary}` |
| `portfolio/views.py` (Coach E1/E5) | ✗ | ✓ (JsonResponse) | ✗ | ✗ | DRF 비사용, `{"error": "code", "detail": "..."}` 자체 형식 |
| `macro/views.py` | ✗ | ✓ | ✗ | ✗ | Service 데이터 그대로 + 에러 시 `{error: str}` |
| `news/api/views.py` (NewsViewSet 등) | ✗ | ✓ | ✗ | ✗ | 빈 데이터 시 404 대신 빈 객체 반환 정책 |
| `chainsight/api/views.py` | ✗ | ✓ | ✗ | ✗ | `{center, nodes, edges, meta}` 자체 구조 |
| `chainsight/views/watchlist_views.py` (ViewSet) | ✗ | ✓ | ✗ | ✓ | `{detail: '...'}` DRF 컨벤션 일관 |
| `serverless/views.py` (Movers, Screener Preset, Alert) | ✓ (대다수) | △ | ✓ (에러 60건+) | ✗ | `{success, data, error:{code, message}}` — **가장 체계적** |
| `serverless/views_admin.py` | ✗ | ✓ | ✗ | ✗ | 평문 `{error: str}` 위주 |
| `rag_analysis/views.py` | ✓ (helper로 일관) | ✗ | ✓ | ✗ | `create_success_response`/`create_error_response` 헬퍼 사용 — **유일한 helper 패턴** |
| `validation/api/views.py` | ✗ | ✓ | ✗ | ✗ | 자체 `{symbol, error: 'code', message}` 형식 (200 OK로 비즈니스 에러 반환) |
| `thesis/views/thesis_views.py` (ViewSet) | ✗ | ✓ | ✗ | △ | close 액션은 `{status, thesis_id}`; 검증 실패는 `{error: str}` 평문 |
| `thesis/views/conversation_views.py` | ✗ | ✓ | ✗ | ✗ | Service result 그대로 반환 |
| `thesis/views/monitoring_views.py` | ✗ | ✓ | ✗ | ✗ | `{thesis, indicators, heatmap}` 자체 구조 |
| `sec_pipeline/views.py` | ✗ | ✓ | ✗ | ✗ | 단일 Filing 엔드포인트, 하드코딩 status |
| `config/views.py` | ✗ | ✓ (JsonResponse) | ✗ | ✗ | api_root, health_check |
| `metrics/views.py` | — | — | — | — | **빈 파일** (stub) |
| `validation/views.py` | — | — | — | — | **빈 파일** (stub) |
| `chainsight/views.py` | — | — | — | — | **빈 파일** (stub) |
| `graph_analysis/views.py` | — | — | — | — | **빈 파일** (stub) |
| `news/views.py` | — | — | — | — | **빈 파일** (stub) |

### 통계 (`Grep -c` 기반)

| 패턴 | 매치 파일 수 | 총 매치 |
|---|---|---|
| `'success': True` (또는 큰따옴표 변형) | 6 | **81** |
| `'error':` 어디든 등장 | 17 | **204** |
| `'message':` | 10 | 112 |
| `'detail':` (DRF/직접) | 3 | 9 |
| `'error': {` (구조화 에러) | 1 (serverless/views.py) | 30+ |

→ **`error`(204) ≫ `detail`(9), `message`(112)**: DRF의 `{detail}` 컨벤션을 따르지 않고 자체 `error` 키로 통일하려는 시도가 있으나 **20% 미만 뷰만이 `success` 래핑까지 동반**하므로 결과적으로 일관성 없음.

---

## HTTP 상태 코드 일관성

### `status.HTTP_xxx` 모듈 사용 vs 하드코딩

`status=NUM` 하드코딩이 발견된 **유일한** 두 파일:

| 파일 | 라인 | 코드 |
|---|---|---|
| `sec_pipeline/views.py` | 40, 44, 46 | `status=202`, `status=200` |
| `portfolio/views.py` | 43, 49, 51, 53, 78, 86, 94, 101, 106, 112, 115 | `status=400/500/503/429` 등 (DRF 비사용 — `JsonResponse`) |
| `serverless/views.py` | 2879 | `status=400` (1건만 누락) |

→ 그 외 **모든 파일**은 `status=status.HTTP_xxx` 모듈 import 사용. **96% 이상 일관적**이며 이 항목은 큰 위험은 아님. 다만 `portfolio/views.py`는 DRF 자체를 미사용하므로 다른 앱들과 인증/렌더링 파이프라인이 달라질 수 있음 (별도 위험).

### 201 Created (생성 시) 사용 일관성

POST 후 201을 반환해야 하는 위치를 점검:

| 파일 | 위치 | 상태 |
|---|---|---|
| `users/views.py` | Users.post (회원가입), PortfolioListCreate.post, WatchlistListCreate.post, WatchlistItemAdd.post | ✓ 모두 201 |
| `users/views.py` | WatchlistBulkAdd.post (910), UserInterestListCreate.post (1032) | △ 조건부 — `201 if created else 200` (있으면 201, 없으면 200) — 합리적이지만 명세 필요 |
| `users/views.py` | RefreshStockData.post (line 552) | △ 207 MULTI_STATUS 사용 — 부분 성공 의도, 하지만 다른 부분 성공 케이스(BulkAdd)는 201/200으로 처리 — 정책 불일치 |
| `serverless/views.py` | 1060, 1428, 1819 | ✓ 201 |
| `rag_analysis/views.py` | 84, 164, 346, 455 | ✓ 201 |
| `chainsight/views/watchlist_views.py` | create() (line 95) | ✓ 201 |
| `serverless/views_admin.py` | 568 | ✓ 201 |
| `stocks/views.py` | StockSync.post | ✗ — **POST지만 200 반환** (idempotent sync이므로 의도적일 수 있으나 명세 필요) |
| `macro/views.py` | DataSyncView.post | ✗ — **POST지만 200 반환** (started/already_running) |
| `stocks/views_indicators.py` | IndicatorComparisonView.post | ✗ — **POST지만 200 반환** (조회 의미라면 GET이 적절) |
| `stocks/views_exchange.py` | BatchQuotesView.post | ✗ — **POST지만 200 반환** (조회 의미) |
| `thesis/views/conversation_views.py` | ConversationStart.post 등 | ✗ — **POST지만 200 반환** (대화 진행이므로 의도적) |

→ **POST=201**의 엄격한 적용은 안 됨. "조회를 POST로 하는 패턴(BatchQuotes, IndicatorComparison)"이 다수 존재해 의미적 불일치를 만든다. 그러나 의도적 200 반환(idempotent action)도 섞여 있어 단순 일률 적용은 위험.

### 비표준/희소 상태 코드

| 코드 | 위치 | 비고 |
|---|---|---|
| **HTTP_207_MULTI_STATUS** | `users/views.py:552` (RefreshStockData) | 1건만 사용 — 다른 부분 성공 흐름과 불일치 |
| **HTTP_202_ACCEPTED** | `sec_pipeline/views.py:40` | on-demand collection 트리거 — 적절. 그러나 코드는 `status=202` 하드코딩 |
| **HTTP_503_SERVICE_UNAVAILABLE** | `stocks/views_search.py`, `stocks/views_exchange.py` (다수), `chainsight/views/watchlist_views.py`, `chainsight/api/views.py` | 외부 API/Neo4j 실패 시. 전반적으로 합리적 사용 |
| **HTTP_429_TOO_MANY_REQUESTS** | `stocks/views.py:928` (StockSync rate limit) | 1건. throttling은 DRF 자동 401/429 미사용 |
| **HTTP_401_UNAUTHORIZED** | `users/views.py:167` (LogIn 실패), `validation/api/views.py:463/489` (로그인 필요) | 2가지 의미(인증 실패 vs 인증 필요)에 동일 코드 사용 — DRF 표준은 `permission_classes`로 자동 401/403, 명시 401은 일관성 부족 |
| **200 OK + 비즈니스 에러** | `validation/api/views.py:67, 85` | `not_in_universe`, `no_data`를 200으로 반환 — REST 컨벤션 위반(에러여도 200) |

---

## 에러 응답 형식

### 패턴 분류

| 패턴 | 사용 위치 (대표) | 누적 매치 |
|---|---|---|
| `{'error': '<문자열>'}` | macro, stocks(eod/screener/exchange/fundamentals/indicators/search), users, validation, news, chainsight/api, serverless/views_admin | **204 매치** (17 파일) |
| `{'error': {'code': ..., 'message': ..., 'details': ...}}` | `serverless/views.py` (30+), `stocks/views.py:587-596` (Overview 500만) | 30+ |
| `{'success': False, 'error': {'code': ..., 'message': ...}}` | `serverless/views.py` 60+, `rag_analysis/views.py` (helper) | 60+ |
| `{'detail': '<문자열>'}` (DRF 컨벤션) | `chainsight/views/watchlist_views.py` (대부분), `portfolio/views.py` (일부) | 9 매치 |
| `{'message': '<문자열>'}` | `users/views.py` Favorites, `macro/views.py` sync | 12+ |
| `serializer.errors` 직접 반환 | `users/views.py` 다수 (회원가입, Watchlist CRUD, Portfolio CRUD) | 다수 |
| `raise NotFound("...")` (DRF 예외) | `users/views.py` PublicUser, Portfolio, Watchlist | 다수 |
| `raise ValidationError(...)` | `users/views.py` BulkAdd/BulkRemove | 2건 |
| `e.to_response()` 커스텀 예외 | `stocks/views.py:583` (StockNotFoundError) | 1건 |

### 핵심 불일치

1. **DRF 기본 동작 vs 명시 응답 혼용**
   - `serializer.errors`를 그대로 반환하는 곳(users)과 `{'error': serializer.errors}`로 한 번 더 감싸는 곳(stocks/views_screener:67) 공존 → 프론트 검증 에러 파서가 두 케이스 모두 처리해야 함.
   - `raise NotFound(...)`(DRF 예외 핸들러 → `{'detail': '...'}`)과 `return Response({'error': '...'}, 404)`(직접) 혼용 → **404 응답 본문 형식이 두 가지**.

2. **`error` 키 의미 충돌**
   - `validation/api/views.py:64-66`에서 `{'symbol': ..., 'error': 'not_in_universe', 'message': '...'}`을 **HTTP 200**으로 반환. `error`가 실제 HTTP 에러가 아니라 비즈니스 상태 코드로 사용됨 → 클라이언트가 HTTP 상태와 본문 모두 봐야 분기 가능.

3. **에러 코드 체계 부재**
   - `serverless/views.py`만 `INVALID_TYPE`, `SYNC_FAILED`, `NOT_FOUND`, `FORBIDDEN`, `VALIDATION_ERROR`, `UNAUTHORIZED`, `SCREENER_ERROR` 등 자체 코드를 정의 — 다른 앱은 코드 없음. **공통 에러 코드 카탈로그 미존재.**
   - `stocks/views.py:588`만 Overview 에러에 `OVERVIEW_ERROR` 코드 사용 — 같은 파일 내 다른 500 에러는 평문.

4. **국제화 불일치**
   - 에러 메시지가 한국어/영어/혼합으로 흩어짐:
     - `users/views.py`: `_(...)` gettext 사용 → 일부만 i18n
     - `stocks/views.py`: 한국어 평문 (`'잘못된 파라미터입니다: ...'`)
     - `news/api/views.py`, `chainsight/api/views.py`: 영어 평문 (`'Stock {symbol} not found'`)
     - `portfolio/views.py`: 영어 코드 (`'invalid_provider'`, `'budget_exceeded'`)

---

## 페이지네이션 현황

### DRF 글로벌 설정

`config/settings.py:341-349`:

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

→ **`DEFAULT_PAGINATION_CLASS` 미설정**, `PAGE_SIZE` 미설정. ListAPIView·ModelViewSet의 list 액션이 자동 페이지네이션을 적용하지 못함.

### 페이지네이션 사용 현황

| 방식 | 위치 | 상태 |
|---|---|---|
| `PageNumberPagination` / `CursorPagination` / `LimitOffsetPagination` (DRF) | **0건** | 아무도 사용 안 함 |
| `pagination_class = ...` 클래스 속성 | **0건** | |
| Django `Paginator` 수동 사용 | `users/views.py:602` (WatchlistList), `users/views.py:822` (WatchlistStocks), `rag_analysis/views.py:796` | 3건만 — `{'results': ..., 'pagination': {count, page, page_size, num_pages, has_next, has_previous}}` 자체 형식 |
| 슬라이스 하드코딩 (`[:N]`) | 다수 | 아래 표 참조 |
| 무제한 반환 | 일부 | 아래 표 참조 |

### 페이지네이션 누락이 의심되는 목록 API

| 위치 | 응답 구조 | 위험도 | 비고 |
|---|---|---|---|
| `stocks/views.py:75` `StockListAPIView(generics.ListAPIView)` | DRF 기본 list (페이지네이션 없음) | **높음** | Stock 전체 반환 가능. 글로벌 `DEFAULT_PAGINATION_CLASS` 없으므로 모든 결과 직렬화 |
| `users/views.py:90` `Users.get` (admin) | `User.objects.all()` 직접 직렬화 | 높음 | 페이지네이션 없음 |
| `users/views.py:188` `UserFavorites.get` | `user.favorite_stock.all()` 직접 직렬화 | 중 | 즐겨찾기 수가 적다는 가정에 의존 |
| `users/views.py:255` `PortfolioListCreate.get` | `Portfolio.objects.filter(user=request.user)` 전체 | 중 | 사용자별 보유 종목 수에 비례 |
| `users/views.py:967` `UserInterestListCreate.get` | `UserInterest.objects.filter(user=request.user)` 전체 | 중 | 관심사 수에 비례 |
| `news/api/views.py:89` `stock_news` | `NewsArticle.objects.filter(...).distinct().order_by(...)` 전체 | **높음** | days 파라미터로만 제한, 기사 수 제한 없음 |
| `news/api/views.py` 다수 (count 230+ 매치) | order_by 후 직접 반환 | 높음 | 추가 점검 필요 |
| `serverless/views.py` 다수 | order_by 후 캐시 → 반환 | 중-높음 | 캐시는 있으나 페이지네이션 없음 |
| `chainsight/api/views.py:65` `ChainSightGraphView.get` | `repo.get_neighbors(symbol, depth)` 전체 (depth ≤ 3) | 중 | depth로만 제한, 노드 수 제한 없음 |
| `chainsight/views/watchlist_views.py` `WatchlistViewSet` (`ModelViewSet`) | DRF list 기본 동작 | 높음 | `pagination_class` 미지정 + 글로벌 미설정 → **모든 SavedPath 반환** |
| `thesis/views/thesis_views.py` `ThesisViewSet` (`ModelViewSet`) | 동일 — 페이지네이션 없음 | 중-높음 | 사용자별 가설 수가 늘면 위험 |
| `thesis/views/monitoring_views.py:238` `AlertListView.get` | `[:50]` 하드코딩 슬라이스 | 낮음 | 50 이상 알림이 보이지 않는 정책 부작용 — 명시 필요 |
| `news/api/views.py` (다양한 목록) | 다수 | 중-높음 | 별도 점검 필요 |
| `validation/api/views.py:111` `rank_metrics` | `[:5]` 하드코딩 | 낮음 | 5개 고정 의도라면 OK, 명세 필요 |
| `chainsight/api/views.py:120` peers | LIMIT 10 (Cypher) | 낮음 | DB-side 제한, 클라이언트 페이징은 없음 |

→ **권장**: `DEFAULT_PAGINATION_CLASS = 'rest_framework.pagination.PageNumberPagination'` 글로벌 설정 + `PAGE_SIZE = 50` 시작 → ListAPIView/ModelViewSet 자동 적용. 자체 Paginator 사용 3곳은 응답 구조가 DRF 표준과 다르므로(`{results, pagination}`) 마이그레이션 시 호환 레이어 필요.

---

## 권고사항

도입 비용 vs 영향 기준으로 단계별 제시. **모두 별도 PR로 분리 권장** (이 보고서는 읽기 전용 감사이며 수정 미수행).

### Phase 1 — 무위험 정합성 정비 (1주 이내)

1. **하드코딩 status 숫자 제거**
   - `sec_pipeline/views.py:40,44,46` → `status.HTTP_202_ACCEPTED`, `status.HTTP_200_OK` 치환
   - `serverless/views.py:2879` → `status.HTTP_400_BAD_REQUEST` 치환
   - `portfolio/views.py`는 DRF 비사용 — Phase 3에서 통합 검토

2. **stub 파일 제거 또는 명시적 `__init__` 처리**
   - `metrics/views.py`, `chainsight/views.py`, `validation/views.py`, `news/views.py`, `graph_analysis/views.py`: `# Create your views here.`만 있는 파일 — URL conf에서 import되는지 확인 후 삭제 또는 docstring 추가.

3. **AlertListView `[:50]` 매직넘버 제거**
   - `thesis/views/monitoring_views.py:238`을 페이지네이션으로 전환 또는 명시 상수화 (`MAX_RECENT_ALERTS = 50`).

### Phase 2 — 응답 컨벤션 단일화 (2~4주, 프론트엔드와 동시 작업)

4. **글로벌 페이지네이션 설정**
   ```python
   REST_FRAMEWORK = {
       ...,
       'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
       'PAGE_SIZE': 50,
   }
   ```
   - 영향: `StockListAPIView`, `WatchlistViewSet`, `ThesisViewSet`이 자동으로 `{count, next, previous, results}` 반환으로 변경됨 → 프론트 동기 마이그레이션 필요.
   - `users/views.py`의 자체 Paginator 3곳(`{results, pagination:{...}}`)을 DRF 표준 `{count, next, previous, results}`로 점진 통합.

5. **에러 응답 단일 형식 결정 후 강제**
   - 권장: `{"error": {"code": "STRING_CODE", "message": "human readable", "details": {...}}}` (serverless 패턴) — HTTP status로 1차 분류 + `code`로 세부 분기.
   - DRF 전역 exception handler를 작성해 `NotFound`, `ValidationError`, `serializer.errors`도 동일 형식으로 변환.
   - 점진 마이그레이션 — 신규 엔드포인트 먼저, 기존은 deprecation 표시.

6. **성공 응답 래핑 정책 결정**
   - 옵션 A (권장): **래핑 안 함 + 상위 헤더(X-Request-ID, X-Source 등)로 메타 전달** — 가장 단순하고 DRF 친화적.
   - 옵션 B: rag_analysis의 `create_success_response` 헬퍼를 `shared_utils/response.py`로 승격 후 모든 신규 뷰가 사용 — `{success, data, meta}` 통일.
   - 어느 쪽이든 **stocks 앱 내부 분열**(views.py vs views_fundamentals.py)은 가장 빠르게 정리해야 함.

7. **POST 시 200 vs 201 정책 명시**
   - "리소스 생성"은 201, "idempotent 동기화/조회를 POST로 받음"은 200 — 각 엔드포인트에 docstring으로 명시.
   - `BatchQuotesView`(POST) 같은 조회용 POST는 GET으로 마이그레이션 검토 (URL 길이 문제만 없다면).

### Phase 3 — 고비용 정비 (선택)

8. **`portfolio/views.py` DRF 통합 검토**
   - 현재 `JsonResponse` + `pydantic` 사용 — 다른 앱과 인증/스로틀링 파이프라인이 다름.
   - 변환 시 portfolio Coach E1/E5 schema가 DRF Serializer와 충돌 가능 → 별도 ADR 필요.

9. **에러 메시지 i18n 정책**
   - 현재 한국어/영어/`gettext_lazy` 혼재.
   - 권장: 사용자 노출 메시지는 한국어 + `gettext_lazy`, 내부 코드는 영어 ENUM (`code`).

10. **OpenAPI 스펙(contracts/) 동기화**
    - `CLAUDE.md`의 "Contract-Driven Development" 원칙과 현 응답 형식의 불일치 정도를 별도 감사 (이 보고서 범위 외).
    - 응답 형식 통일 PR마다 `contracts/` 업데이트를 PR Checklist에 추가.

---

## 부록: 측정값 요약

```
Total view files:        25 (stub 5개 포함)
Total LOC (views):       9,991
Response() 호출 매치:    600+ (정확치 측정 안 함)

성공 래핑 사용 파일:     6
DRF detail 사용 파일:    3
error 키 사용 파일:      17
HTTP_xxx 모듈 사용:      대부분 (16+ 파일)
하드코딩 status:         3 파일 (sec_pipeline, portfolio, serverless 1건)

DRF 페이지네이션 사용:   0
Django Paginator 수동:   3 위치 (users 2, rag_analysis 1)
```
