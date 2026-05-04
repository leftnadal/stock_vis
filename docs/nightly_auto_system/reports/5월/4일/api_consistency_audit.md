# API 응답 일관성 감사 보고서

- **감사 일자**: 2026-05-05
- **범위**: Django REST Framework views.py 전체 (28개 파일, ~14,000 LOC, Response/JsonResponse 호출 ~530건)
- **방법**: 읽기 전용 정적 분석 (코드 수정 없음)
- **분석 대상 파일**:
  - stocks: `views.py`, `views_screener.py`, `views_market_movers.py`, `views_eod.py`, `views_indicators.py`, `views_search.py`, `views_fundamentals.py`, `views_mvp.py`, `views_exchange.py`
  - users: `views.py`
  - portfolio: `views.py`
  - macro: `views.py`
  - news: `api/views.py`
  - serverless: `views.py`, `views_admin.py`
  - chainsight: `api/views.py`
  - validation: `api/views.py`
  - rag_analysis: `views.py`
  - thesis: `views/{thesis,conversation,monitoring}_views.py`
  - sec_pipeline: `views.py`
  - config: `views.py`
  - 기타: `metrics/`, `graph_analysis/`, `news/views.py`, `validation/views.py`, `chainsight/views.py` (모두 placeholder/empty)

---

## 요약

| 항목 | 발견 사항 | 심각도 |
|------|----------|--------|
| 응답 래핑 패턴 | **3가지 패턴 혼재** — `{success, data, meta}` 래핑 / 직접 반환 / 일부 hybrid (전체 12개 앱 중 통일된 컨벤션 부재) | 🔴 High |
| 에러 응답 형식 | `error` (152회), `detail` (DRF 기본 + 9회), `message` (자체) — 단일 종목 안에서도 혼용 (users/views.py) | 🔴 High |
| 구조화된 에러 코드 | serverless/rag_analysis만 `{code, message}` 사용. 그 외는 자유 문자열 → 클라이언트가 분기 불가 | 🟡 Medium |
| HTTP 201/204 | 일관성 양호 (DRF status 모듈 사용) — but `users/views.py`는 password 변경 시 200, `serverless`는 일부 201 누락 의심 | 🟢 Low |
| status= 하드코딩 | `portfolio/views.py` 전체 (`status=400/500/503/429`), `sec_pipeline/views.py` (`status=200/202`), `serverless/views.py:2879` (1건) — DRF status 모듈 미사용 | 🟡 Medium |
| 페이지네이션 | **`DEFAULT_PAGINATION_CLASS` 미설정**. `pagination_class` 명시 0건. 4가지 자체 구현 방식이 혼재 (Django `Paginator`, 수동 offset/limit, `FilterEngine` 내부, limit만) | 🔴 High |
| .all()/.filter() 무제한 반환 | `users.UserFavorites`, `users.PortfolioListCreateView`, `users.PortfolioSummaryView`, `users.PortfolioDetailTableView`, `stocks.StockSearchAPIView`, `chainsight` 다수 — DDoS/메모리 위험 | 🔴 High |
| JsonResponse vs Response | `portfolio/views.py`, `config/views.py`만 `JsonResponse` 사용. 나머지 26개 파일은 `Response` (DRF) → 반환 타입 일관성 결여 | 🟡 Medium |

---

## 앱별 응답 패턴 매트릭스

### 범례
- **W**: `{success: True/False, data: {...}, meta: {...}}` 래핑 형식
- **D**: 직접 데이터 반환 (`Response(serializer.data)` 또는 `Response({...})`)
- **H**: Hybrid (한 파일 안에서 W와 D 혼용)
- **J**: `JsonResponse` (Django 기본, DRF 미사용)
- **DRF**: DRF 예외 raise (`raise NotFound`, `raise ValidationError` 등)

| 앱 / 파일 | 성공 응답 패턴 | 에러 응답 형식 | 인증 응답 | 일관성 |
|-----------|----------------|----------------|-----------|--------|
| `stocks/views.py` | **H** (검색·차트 D, 일부 dict 직접) | `{error: str}` + DRF | `IsAuthenticatedOrReadOnly` | ⚠️ 동일 파일 내 형태 혼재 |
| `stocks/views_screener.py` | **W** `{success, data, meta}` | `{error: serializer.errors}` 래핑 X | `IsAuthenticated` | ⚠️ 에러는 비래핑 |
| `stocks/views_fundamentals.py` | **W** `{success, data, meta}` | `{error: str}` (래핑 X) | `IsAuthenticated` | ⚠️ 에러는 비래핑 |
| `stocks/views_exchange.py` | **W** `{success, data, meta}` | `{error: str}` (래핑 X) | `IsAuthenticated` | ⚠️ 에러는 비래핑 |
| `stocks/views_market_movers.py` | **D** (serializer.data) | `{error: str}` | `AllowAny` | ✅ 단일 형식 |
| `stocks/views_eod.py` | **D** (dict 직접) | `{error: str}` | (미지정) | ✅ |
| `stocks/views_indicators.py` | **D** (dict 직접) | `{error: str}` | (미지정) | ✅ |
| `stocks/views_search.py` | **D** (dict 직접) | `{error: str}` | (미지정) | ✅ |
| `stocks/views_mvp.py` | **D** | `{error: str}` | (혼재) | ✅ |
| `users/views.py` | **H** (대부분 D, refresh류는 `{message, data}`/`{message, error}`) | `{error}` + `{message}` + DRF (`raise NotFound` / `raise ParseError`) | `IsAuthenticated` | 🔴 동일 파일 내 3가지 형식 혼재 |
| `portfolio/views.py` | **J + D** (`JsonResponse(result, status=200)`) | `{error: str, detail: str}` (JsonResponse) | (미지정, csrf_exempt) | 🟡 DRF 미사용, 200 명시 |
| `macro/views.py` | **D** (serializer.data) | `{error: str}` | `AllowAny` | ✅ 단일 형식 |
| `news/api/views.py` | **D** (dict 직접) | DRF 예외 (`raise ValidationError`) + `{error: str}` | `AllowAny`/`IsAuthenticated` | ⚠️ 일부 list/retrieve action만 직접, viewset의 `paginate_queryset` 미사용 |
| `serverless/views.py` | **W** `{success, data}` (구조화) | **W** `{success: False, error: {code, message}}` | `AllowAny` (TODO: IsAdminUser) | ✅ 일관성 가장 높음 |
| `serverless/views_admin.py` | **D** (dict 직접) — admin api는 직접 반환 | `{error: str}` (래핑 X) | `IsAdminUser` | ⚠️ serverless 본체와 다름 |
| `chainsight/api/views.py` | **D** (dict 직접, `_sanitize_neo4j` 후) | `{error: str}` | (미지정 → `IsAuthenticatedOrReadOnly` 글로벌) | ✅ |
| `validation/api/views.py` | **D** (dict 직접) | `{error: str}` + 일부 `{symbol, error, message}` | (미지정) | ⚠️ 에러 키 구조 가변 |
| `rag_analysis/views.py` | **W** `create_success_response()` 헬퍼 | **W** `create_error_response(code, message)` 헬퍼 | `IsAuthenticated` | ✅ 헬퍼 강제 — serverless와 약간 다른 스키마 (`error.code/error.message`) |
| `thesis/views/*.py` | **D** (DRF ViewSet 표준) | `{error: str}` | `IsAuthenticated` | ✅ |
| `sec_pipeline/views.py` | **D** (dict 직접) | (없음, 200/202 위주) | `staff_member_required` | ✅ |
| `config/views.py` | **J + D** (`JsonResponse`) | (없음, health check) | (미지정) | ✅ |

### 핵심 충돌 사례

1. **stocks 앱 내부 분열**
   - `views_screener.py`, `views_fundamentals.py`, `views_exchange.py`: `{success, data, meta}` 래핑
   - `views_eod.py`, `views_indicators.py`, `views_market_movers.py`, `views_search.py`, `views.py`: 직접 반환
   - 같은 앱(`/api/v1/stocks/*`)에서 화면 컴포넌트별로 응답 구조가 다름 → 프론트 클라이언트 분기 비용 증가

2. **serverless 앱 내부 분열**
   - `views.py`: `{success, data}` 래핑 (구조화된 에러)
   - `views_admin.py`: 직접 반환 (`{error: str}`)
   - 동일 앱 prefix(`/api/v1/serverless/*`) 내에서 일관성 없음

3. **rag_analysis vs serverless 스키마 차이**
   - `rag_analysis`: `error: {code, message}`
   - `serverless`: `error: {code, message}` (동일하지만 헬퍼 부재로 inline 작성)
   - 두 앱 모두 구조화 에러를 사용하나 헬퍼 함수가 별도 → 점진적 drift 위험

4. **users/views.py 단일 파일 3중 충돌** (rows 137~244)
   - `LogIn`: 성공 `{ok, user}` (래핑 X), 실패 `{error}` (래핑 X)
   - `LogOut`: `{ok}` 키 사용 — 다른 곳에는 없음
   - `AddFavorite`/`RemoveFavorite`: `{message, stock}` 사용 — 다른 곳에는 없음
   - `RefreshPortfolioDataView`: `{message, results}` / `{error, detail}`
   - `RefreshStockDataView`: 207 Multi-Status 사용 — 프로젝트 전체에서 유일

---

## HTTP 상태 코드 일관성

### 200/201 사용

| 상황 | 일관 사용 | 위반 사례 |
|------|----------|----------|
| 리소스 생성(POST) | 대부분 `status.HTTP_201_CREATED` 사용 (22건) | `users.ChangePassword`: 비밀번호 변경 후 `200` 반환 (적절) |
| 단순 조회(GET) | 대부분 200 (기본값) | `users.AddFavorite`/`RemoveFavorite`: 200 반환 + `{message}` (논쟁의 여지) |
| 비동기 작업 트리거 | `serverless`는 200, `sec_pipeline`은 **202 Accepted** 사용 | `macro.DataSyncView`: 비동기 트리거인데 200 반환 (202가 적절) |
| 다중 상태 | `users.RefreshStockDataView`: **207 Multi-Status** 사용 | 프로젝트 전체에서 유일 사례 — 클라이언트 처리 가능성 의문 |

**create_or_get 패턴 (201/200 분기)** — 모범 사례:
- `users/views.py:910`: `status.HTTP_201_CREATED if added else status.HTTP_200_OK`
- `users/views.py:1032`: `status.HTTP_201_CREATED if created else status.HTTP_200_OK`

### 에러 코드 사용 패턴

| 상태 코드 | 사용 빈도 | 주된 용도 | 이슈 |
|-----------|----------|----------|------|
| `400 BAD_REQUEST` | 매우 빈번 | validation 실패, 잘못된 파라미터 | ✅ 일관 |
| `401 UNAUTHORIZED` | 1회 (`users.LogIn`) | 로그인 실패 | DRF 기본은 403 (`IsAuthenticated`) — `users.LogIn`만 401 직접 반환 |
| `403 FORBIDDEN` | 3회 (`serverless` preset 권한) | 리소스 권한 부족 | ✅ 적절 |
| `404 NOT_FOUND` | 매우 빈번 | 종목/리소스 없음 | ✅ 일관 (단, `news.stock_sentiment`는 빈 데이터 반환 = 200, 의도적) |
| `429 TOO_MANY_REQUESTS` | 1회 (`portfolio.coach_e5_adjustment`) | LLM 예산 초과 | ⚠️ Rate limit과 비즈니스 예산 모두 429 사용 — 구분 필요할 수 있음 |
| `500 INTERNAL_SERVER_ERROR` | 빈번 | catch-all `except Exception` | 🔴 너무 광범위 — 외부 API 실패도 500 (503이 적절) |
| `503 SERVICE_UNAVAILABLE` | 일부 | 외부 API 미응답 | ⚠️ `stocks/views_search.py`는 503, `macro/views.py`는 500 — 동일 시나리오인데 코드 다름 |
| `207 MULTI_STATUS` | 1회 | 부분 성공 | 프로젝트 단일 사례 |
| `202 ACCEPTED` | 1회 | 비동기 수집 트리거 | `sec_pipeline`만 사용 — 다른 비동기 트리거(`serverless.trigger_sync` 등)는 200 |

### `status=숫자` 하드코딩 vs `status=status.HTTP_*`

- **DRF status 모듈 사용**: 248건 (대다수 — 권장 패턴)
- **숫자 하드코딩**: 16건
  - `portfolio/views.py`: 전체 (200, 400, 429, 500, 503) — DRF 미사용 view라서 일관성은 있음
  - `sec_pipeline/views.py`: 200, 202
  - `serverless/views.py:2879`: 1건 (`status=400`) — 다른 곳은 모두 `status.HTTP_*`, drift 의심

**권고 위반 사례**:
```python
# serverless/views.py:2879 — 같은 파일 내 다른 곳과 다름
}, status=400)
# 정상: status=status.HTTP_400_BAD_REQUEST
```

---

## 에러 응답 형식

### 형식별 빈도 (자체 작성, DRF 자동 반환 제외)

| 형식 | 빈도 | 사용 파일 |
|------|------|----------|
| `{'error': str(message)}` | ~152회 (17개 파일) | 광범위 — stocks/*, macro, validation, chainsight, users, news, ... |
| `{'success': False, 'error': {'code': str, 'message': str}}` | 30+회 | serverless/views.py, rag_analysis (헬퍼) |
| `{'message': str}` | 9회 | users/views.py(2), portfolio(6), config(1) |
| `{'detail': str}` | 9회 | portfolio (`{error, detail}` 조합), config |
| `{'error': str, 'detail': str}` | 5회 | portfolio/views.py |
| DRF 예외 raise (`NotFound`, `ParseError`, `ValidationError`) | 19회 | users (자주), news, rag_analysis | 

### DRF 기본 vs 커스텀 충돌

DRF는 예외 발생 시 자동으로 `{'detail': ...}` 형식을 반환:
- `raise NotFound("Stock not found")` → `{"detail": "Stock not found"}` (HTTP 404)
- `raise ParseError("Password is required")` → `{"detail": "Password is required"}` (HTTP 400)
- `raise ValidationError({...})` → `{...}` (HTTP 400)

그러나 **같은 의미의 에러를 직접 `Response({'error': ...})` 로도 반환** — 클라이언트는 두 형식 모두 처리해야 함.

**users/views.py 한 파일 내 동시 사용 사례**:
```python
# 같은 "Stock not found" 시나리오, 다른 응답 형식
raise NotFound("Stock not found")                        # → {"detail": "..."}, 404
return Response({"error": "Stock not found in your portfolio"}, status=404)  # → {"error": "..."}, 404
return Response({"message": "This stock is already..."},  status=400)  # → {"message": "..."}, 400
```

### 구조화 에러 코드 부재의 영향

`serverless`/`rag_analysis`만 `error.code` 보유 → 클라이언트가 i18n 또는 분기 처리 가능:
```python
# serverless 모범 사례
{"success": False, "error": {"code": "NOT_FOUND", "message": "Preset not found: 42"}}
```

다른 모든 앱은 자유 문자열만 보유 → 클라이언트가 메시지 매칭으로 분기해야 하며 i18n/메시지 변경 시 깨짐.

### `serializer.errors` 직렬화 문제

```python
# stocks/views_screener.py:65
return Response({"error": serializer.errors}, status=...)  # error 안에 dict 들어감
```
vs
```python
# users/views.py:107
return Response(serializer.errors, status=...)  # error 키 없이 dict 자체 반환
```
같은 validation 에러라도 클라이언트가 받는 구조가 다름.

---

## 페이지네이션 현황

### settings.py (전역 설정)

`config/settings.py:341-349` REST_FRAMEWORK 설정에 **`DEFAULT_PAGINATION_CLASS` 미정의** — 모든 list view는 페이지네이션이 자동 적용되지 않음.

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
    # DEFAULT_PAGINATION_CLASS 없음
    # PAGE_SIZE 없음
}
```

### `pagination_class` 명시 사용

전체 코드베이스에서 `PageNumberPagination`, `CursorPagination`, `LimitOffsetPagination`, `pagination_class` 사용 — **0건** (Grep 결과 확인).

### 자체 구현 패턴 4가지 (혼재)

| 패턴 | 사용 위치 | 응답 구조 |
|------|----------|----------|
| **Django `Paginator` + 수동 응답** | `users.WatchlistListCreateView` (`views.py:602-620`) | `{results, pagination: {count, page, page_size, num_pages, has_next, has_previous}}` |
| **수동 offset/limit + has_more** | `news.all_news` (`api/views.py:419-433`) | `{total, count, offset, limit, has_more, articles}` |
| **`FilterEngine` 내부 페이지네이션** | `serverless.advanced_screener_api`, `serverless.execute_preset` | `engine.apply_filters(limit, offset)` — 응답에 `**results`로 spread |
| **limit만 적용, page 없음** | `stocks.StockSearchAPIView`, `stocks.StockScreenerView`, `news.market`, `news.trending` | `{count, results}` — 페이지네이션 부재 |

응답 키 충돌:
- 페이지네이션 메타가 `pagination` (users) vs flat (news) vs serializer 자체 spread (serverless)
- `count`의 의미가 다름: `users`는 전체 개수, `news.market`은 현재 페이지 개수

### 무제한 `.all()` / `.filter()` 반환 (위험)

전수조사 결과 다음 view들이 페이지네이션 없이 전체 결과 반환 — DB 부하/메모리/응답 크기 위험:

| 위치 | 쿼리 | 위험도 | 비고 |
|------|------|--------|------|
| `users.UserFavorites` (`users/views.py:187`) | `user.favorite_stock.all()` | 🟡 사용자별이라 보통 작음 | 상한 없음 |
| `users.PortfolioListCreateView.get` (`users/views.py:257`) | `Portfolio.objects.filter(user=...)` | 🟡 사용자별 | 정렬 없음 |
| `users.PortfolioSummaryView.get` | `Portfolio.objects.filter(user=...)` (전체 순회 합산) | 🟡 사용자별 | aggregate로 대체 가능 |
| `users.PortfolioDetailTableView.get` | `Portfolio.objects.filter(user=...)` | 🟡 사용자별 | 풀스캔 + 비중 계산 |
| `users.Users.get` (admin) | `User.objects.all()` | 🔴 전체 사용자 | 관리자 전용이지만 무한정 |
| `stocks.StockListAPIView` | `Stock.objects.all()` (`ListAPIView` 상속이지만 pagination_class 없음) | 🔴 ~5000 종목 | 정렬 후 그대로 반환 |
| `stocks.StockSearchAPIView` (`views.py:192`) | `[:20]` 적용 | ✅ 안전 | hard-coded 20 |
| `news.NewsViewSet.queryset` | `NewsArticle.objects.all()` (rest framework `ReadOnlyModelViewSet`) | 🔴 누적 수백만 가능 | viewset 기본 list가 pagination_class 없이 호출됨 — 실제 list endpoint 확인 필요 |
| `news.market` | `[:limit]` 적용 (limit ≤ 100) | ✅ 안전 | |
| `news.trending` | `[:limit]` 적용 | ✅ 안전 | |
| `news.daily_keywords` | 단일 객체 | ✅ | |
| `validation.ValidationSummaryView` | `CategorySignal.objects.filter(symbol=stock)` | ✅ | per-symbol 카테고리 7개 |
| `chainsight.ChainSightSeedsView` | (확인 필요) | ⚠️ | 시드 종목 N개 |
| `serverless.screener_presets_api` | `ScreenerPreset.objects.all()` 후 union | 🟡 운영 후 증가 위험 | 시스템 + 사용자 프리셋 |
| `serverless.screener_filters_api` | `ScreenerFilter.objects.filter(is_active=True)` | ✅ | ~50개 고정 |
| `chainsight.api.views` 다수 | Neo4j `run_query` (LIMIT 명시 — `LIMIT 10` 등) | ✅ | Cypher LIMIT 사용 |

특히 우려:
- **`stocks.StockListAPIView`** (`stocks/views.py:75-105`): `generics.ListAPIView` 상속하지만 `DEFAULT_PAGINATION_CLASS`가 없어 페이지네이션 없이 전체 종목 반환. 5000+ 행을 매번 직렬화.
- **`news.NewsViewSet`** (`news/api/views.py:42`): `ReadOnlyModelViewSet`의 기본 `list` endpoint가 노출되며 pagination_class 미설정 — articles 누적 시 응답 폭증.

---

## 권고사항

### 1. 응답 컨벤션 통합 (우선순위: High)

**선택 A — DRF 표준 채택 (권장):**
- 모든 view를 직접 반환(`Response(serializer.data)` / `Response({...})`)으로 통일
- `serverless`, `stocks/views_screener.py`, `stocks/views_fundamentals.py`, `stocks/views_exchange.py`, `rag_analysis/views.py`의 `{success, data, meta}` 래핑 제거
- 메타데이터(`timestamp`, `count`)가 필요하면 응답 dict에 직접 포함하거나 페이지네이션 클래스의 `paginated_response`로 흡수

**선택 B — 래핑 표준화:**
- 모든 view를 `{success, data, meta}` 래핑으로 통일
- `rag_analysis`의 헬퍼(`create_success_response` / `create_error_response`)를 `core/responses.py`로 승격해 전 앱이 import
- `serverless/views.py`의 inline 래핑을 헬퍼로 대체

**의사결정 근거**: 프론트엔드가 `data.results` vs `results`를 분기 중인지 확인 후 결정. 현재 frontend가 두 형태를 모두 받고 있다면 점진 마이그레이션이 필요. (검증은 `frontend/src/lib/api/` 클라이언트 코드 별도 감사 필요)

### 2. 에러 응답 통일 (우선순위: High)

- 키를 `error`로 고정하고, 객체 형태 강제: `{"error": {"code": "...", "message": "..."}}`
- DRF 기본 `{"detail": ...}` 형식과의 충돌 해결을 위해 `EXCEPTION_HANDLER` 커스터마이즈:
  ```
  # config/settings.py
  REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'core.exception_handler.unified_handler'
  ```
- `core/exception_handler.py`에서 DRF 기본 응답을 위 형식으로 변환
- `error.code`는 enum 또는 도메인별 상수 정의: `INVALID_INPUT`, `NOT_FOUND`, `RATE_LIMIT`, `EXTERNAL_API_FAILED` 등

### 3. 페이지네이션 강제 (우선순위: High)

- `config/settings.py`에 추가:
  ```python
  REST_FRAMEWORK = {
      ...,
      'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',  # 또는 PageNumberPagination
      'PAGE_SIZE': 50,
  }
  ```
- 무제한 `.all()`/`.filter()` 반환하는 list view들을 `ListAPIView` 또는 `paginate_queryset`으로 마이그레이션:
  - `stocks.StockListAPIView` ← 이미 `ListAPIView`이므로 자동 적용
  - `users.PortfolioListCreateView`, `users.UserFavorites`, `users.PortfolioDetailTableView`
  - `news.NewsViewSet` (viewset 기본 list)
  - `serverless.screener_presets_api`
- 자체 구현(`Paginator`, `offset/limit`, `FilterEngine`)도 표준 페이지네이션 클래스로 흡수 검토

### 4. HTTP 상태 코드 정리 (우선순위: Medium)

- **외부 API 실패 → 503**: `macro/views.py`의 `except Exception → 500`을 `502/503`으로 분리. 현재 `stocks.views_search`는 503을 쓰고 `macro`는 500을 쓰는 비대칭 해소.
- **비동기 트리거 → 202**: `macro.DataSyncView`, `serverless.trigger_sync`, `serverless.trigger_keyword_generation`을 200 → 202로 변경 (sec_pipeline과 일치)
- **status 하드코딩 제거**: `serverless/views.py:2879`, `portfolio/views.py` 전체 → `status.HTTP_*` 사용 (단, portfolio는 `JsonResponse` 의존이므로 DRF 마이그레이션과 연계)
- **207 Multi-Status 재검토**: `users.RefreshStockDataView`만 사용 — 클라이언트가 처리하는지 확인. 미처리 시 200 + `{partial: true}` 또는 별도 200/500 분기로 단순화.

### 5. JsonResponse → Response 전환 (우선순위: Medium)

- `portfolio/views.py`: `JsonResponse` + `csrf_exempt` + `require_POST` 패턴을 DRF `APIView` + `IsAuthenticated`로 마이그레이션
- 이렇게 하면 권고 1~4가 자동 적용됨
- `config/views.py`의 `api_root`, `health_check`은 단순 메타 엔드포인트라 유지 가능 (`JsonResponse` OK)

### 6. 운영 보호 장치 (우선순위: Medium)

- **무제한 .all() 검출 CI**: `Stock.objects.all()`, `Model.objects.filter(user=request.user)` 같은 패턴을 lint로 차단 (단, 조건부)
- **응답 크기 모니터링**: 응답 본문 > 1MB인 엔드포인트를 metrics로 추적
- **OpenAPI 스펙 동기화**: `contracts/` 하위 OpenAPI 스펙과 실제 응답 키 일치 검증 — 현재 응답 패턴 혼재로 spec drift 발생 가능 (api_dependency_audit / api_docs_audit 보고서 교차 확인)

---

## 부록 — 위반 사례 핫스팟 (코드 위치)

### 응답 형식 혼재
- `users/views.py:160-168` — LogIn: `{ok}` vs `{error}`
- `users/views.py:178` — LogOut: `{ok}` (다른 곳에 없는 키)
- `users/views.py:215-218`, `:242-244` — Favorites: `{message, stock}` (다른 곳에 없는 구조)
- `users/views.py:548-552` — RefreshStockData: 207 + `{message, data, errors}`
- `serverless/views.py:71-76` (구조화) vs `serverless/views_admin.py:587` (단순) — 같은 앱 다른 형식

### 하드코딩 status
- `portfolio/views.py:43,49,51,53,78,86,94,101,106,112,115` (전체)
- `sec_pipeline/views.py:40,44,46`
- `serverless/views.py:2879` (단일 drift)

### DRF 미사용 / JsonResponse
- `portfolio/views.py:1-115` (전체)
- `config/views.py:19,77` (의도적, 메타 엔드포인트)

### 페이지네이션 누락
- `config/settings.py:341-349` — DEFAULT_PAGINATION_CLASS 미설정
- `stocks/views.py:75-105` — StockListAPIView, ListAPIView이지만 미적용
- `news/api/views.py:42-45` — NewsViewSet 기본 list
- `users/views.py:90-92` — Users.get (admin all())
- `serverless/views.py:1014-1044` — screener_presets_api

### 자체 페이지네이션 4종 혼재
- `users/views.py:602-620` — Django `Paginator` + `pagination` 메타 키
- `news/api/views.py:419-433` — flat offset/limit/has_more
- `serverless/views.py:1191-1198` — FilterEngine 내부, 응답에 spread
- `stocks/views_screener.py` — limit만 (페이지 없음)

---

**감사 종료**: 코드 변경 없이 정적 분석만 수행. 권고사항 적용은 PR 단위로 응답 스키마/페이지네이션 호환성 마이그레이션 계획 수립 후 착수 권장.
