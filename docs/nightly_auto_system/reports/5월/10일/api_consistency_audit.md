# API 응답 일관성 감사 보고서

> 생성일: 2026-05-10
> 감사 범위: 모든 `views*.py` 파일 (총 26개, ~13,628 라인)
> 감사 대상: Response 래핑 패턴 / HTTP 상태 코드 / 에러 형식 / 페이지네이션
> 모드: **읽기 전용** (코드 수정 없음)

---

## 요약

Stock-Vis 백엔드는 **단일 응답 표준이 부재**한 상태로, 13개 이상의 Django 앱에 걸쳐 **최소 5가지 서로 다른 응답 래핑 규약**과 **3가지 에러 키(`error` / `detail` / `message`)**가 혼재한다. 핵심 발견:

| 항목 | 심각도 | 결론 |
|---|---|---|
| 응답 래핑 규약 분기 | **🔴 P0** | `serverless/rag_analysis`는 `{success, data, meta}` 구조 준수, `users/stocks/macro/validation/news/chainsight/portfolio` 등은 raw serializer 반환 — 프론트가 각 엔드포인트마다 다른 파서 필요 |
| 에러 키 불일치 | **🔴 P0** | `'error'` (159회) vs `'detail'` (3회) vs `'message'` (99회) — 프론트가 3가지 모두 fallback 필요 |
| `serverless`만 nested error 객체 사용 | **🟠 P1** | `{'error': {'code': ..., 'message': ...}}` 구조는 `serverless/views.py`에서만, 나머지는 평문 문자열 |
| DRF 페이지네이션 클래스 부재 | **🟠 P1** | `REST_FRAMEWORK` 설정에 `DEFAULT_PAGINATION_CLASS` 없음 → 모든 페이지네이션이 Django `Paginator`로 수작업 |
| 페이지네이션 미적용 목록 API | **🔴 P0** | `users.UserFavorites`, `stocks.SectorListView`, `stocks.PopularSymbolsView`, `chainsight.SuggestionView`, `validation.MetricsView` 등 다수 — `.all()`/`.filter()` 결과를 그대로 직렬화 |
| HTTP 상태 코드 사용 | 🟢 OK | `status.HTTP_*` 248회 vs 하드코딩 숫자 36회 — 대체로 일관됨. 다만 `portfolio/views.py`만 `JsonResponse(status=400)` 형태로 통일 |
| 201 Created 사용 | 🟡 P2 | `users/serverless/rag_analysis`는 일관 사용. `chainsight/news/portfolio/macro/validation`은 POST 응답에도 200 사용하거나 POST 엔드포인트 없음 |

**즉시 수정 권고 P0**: ① 응답 래핑 표준 결정 + 점진 마이그레이션, ② 에러 응답 형식 단일화 (DRF 기본 `detail` 권장), ③ 페이지네이션 미적용 엔드포인트 식별 후 한도 적용.

---

## 앱별 응답 패턴 매트릭스

### 범례

| 코드 | 의미 |
|---|---|
| `RAW` | `Response(serializer.data)` — 직렬화기 결과 직접 반환 |
| `RAW-DICT` | `Response({...})` — 평문 dict 직접 반환 (래핑 없음) |
| `WRAP-MIXED` | `Response({"success": True, "data": ..., "meta": ...})` — 일부 엔드포인트만 래핑 |
| `WRAP-FULL` | 모든 엔드포인트가 success/data/meta 구조 사용 |
| `WRAP-NESTED-ERR` | 에러를 `{success: False, error: {code, message}}` 중첩 객체로 |
| `JsonResponse` | DRF 미사용, 순수 Django `JsonResponse` |

### 매트릭스

| 앱 / 파일 | 라인수 | 성공 응답 패턴 | 에러 응답 패턴 | 비고 |
|---|---:|---|---|---|
| `config/views.py` | 104 | `JsonResponse({...})` | n/a | 헬스체크 / API root만 |
| `users/views.py` | 1088 | `RAW` + `RAW-DICT` 혼용 | `{"error": str}` 또는 `{"message": str}` 또는 `serializer.errors` | 16+33회 Response 호출, 패턴 일관성 낮음 |
| `portfolio/views.py` | 304 | `JsonResponse(result, status=200)` | `JsonResponse({"error": ..., "detail": ...}, status=4xx)` | DRF 미사용. `error` + `detail` 2-필드 구조로 일관 |
| `stocks/views.py` | 1020 | `RAW-DICT` (`{"results", "count", ...}`) | `{"error": str}` | 메인 stocks 뷰, 래핑 없음 |
| `stocks/views_eod.py` | 136 | `RAW-DICT` | `{"error": str}` | EOD admin/debug |
| `stocks/views_indicators.py` | 372 | `RAW-DICT` | `{"error": str}` | 기술지표 |
| `stocks/views_search.py` | 229 | `RAW-DICT` | `{"error": str}` | 검색 + `valid: True/False` 패턴 |
| `stocks/views_market_movers.py` | 69 | `RAW` (serializer.data) | `{"error": str}` | |
| `stocks/views_mvp.py` | 200 | `RAW-DICT` | n/a | MVP 데모 |
| `stocks/views_fundamentals.py` | 305 | **`WRAP-FULL`** (`{"success", "data", "meta"}`) | `{"error": str}` ← 평문! | **🔴 성공/실패 비대칭**: 성공은 wrap하지만 에러는 평문 |
| `stocks/views_screener.py` | 498 | **`WRAP-FULL`** | `{"error": serializer.errors}` ← 평문 | 동일한 비대칭 |
| `stocks/views_exchange.py` | 295 | **`WRAP-FULL`** | `{"error": str}` ← 평문 | 동일한 비대칭 |
| `macro/views.py` | 410 | `RAW` | `{"error": str}` | 15곳 일관 |
| `serverless/views.py` | 3413 | **`WRAP-NESTED-ERR`** (모든 엔드포인트) | `{"success": False, "error": {"code", "message"}}` | 가장 정교한 표준, FBV (`@api_view` 52회) |
| `serverless/views_admin.py` | 694 | `RAW-DICT` (대부분) | `{"error": str}` | views.py와 다른 패턴 — 같은 앱에서도 분기 |
| `news/api/views.py` | 2189 | `RAW-DICT` | `{"error": str}` | `viewsets.ReadOnlyModelViewSet` 기반 |
| `chainsight/api/views.py` | 814 | `RAW-DICT` | `{"error": str}` | _sanitize_neo4j 헬퍼 사용 |
| `validation/api/views.py` | 558 | `RAW-DICT` | `{"error": str}` + `{"error": "key", "message": "..."}` 혼용 | 같은 파일 내에서도 분기 |
| `rag_analysis/views.py` | 868 | **`WRAP-FULL`** (`create_success_response` 헬퍼) | `create_error_response("CODE", msg)` 헬퍼 | 가장 깨끗한 사례 — 헬퍼 함수로 강제 |
| `thesis/views/thesis_views.py` | n/a | `RAW` (DRF ViewSet 기본) | `{"error": str}` | ViewSet 표준 |
| `thesis/views/conversation_views.py` | n/a | `RAW-DICT` | `{"error": str}` | |
| `thesis/views/monitoring_views.py` | n/a | `RAW-DICT` | `{"error": str}` | |
| `sec_pipeline/views.py` | 51 | `RAW-DICT` | n/a | `status=200/202` 하드코딩 |
| `metrics/views.py`, `chainsight/views.py`, `news/views.py`, `graph_analysis/views.py`, `validation/views.py` | 1~3 | 빈 파일 (skeleton) | n/a | |

### 핵심 분기 — `'success'` 키 사용 분포

| 파일 | `'success': True/False` 발생 |
|---|---:|
| `serverless/views.py` | **62회** (모든 응답에 강제) |
| `stocks/views_screener.py` | 7회 (성공만) |
| `stocks/views_exchange.py` | 5회 (성공만) |
| `stocks/views_fundamentals.py` | 5회 (성공만) |
| `serverless/views_admin.py` | 1회 |
| `rag_analysis/views.py` | 1회 (헬퍼 내부) |

→ `serverless`는 거의 모든 응답이 `success` 키 보유. `stocks/views_*`는 **성공만 wrap**, 에러는 평문 — **프론트 입장에서 가장 위험한 패턴** (응답 형식이 상태에 따라 변형됨).

---

## HTTP 상태 코드 일관성

### 사용 통계

| 패턴 | 발생 | 사용 파일 |
|---|---:|---|
| `status=status.HTTP_*` (DRF 상수) | **248회** | 16개 파일 |
| `status=400` 등 하드코딩 숫자 | 36회 | 3개 파일 (`portfolio/views.py` 32, `sec_pipeline/views.py` 3, `serverless/views.py` 1) |
| `JsonResponse(..., status=4xx)` | 34회 | `portfolio/views.py` 32, `config/views.py` 2 |

### 코드별 분포 (상위 5개)

| 코드 | 의미 | 주요 발생 파일 |
|---|---|---|
| `HTTP_400_BAD_REQUEST` | 잘못된 요청 | 전 앱 — 가장 흔함 |
| `HTTP_404_NOT_FOUND` | 리소스 없음 | 전 앱 |
| `HTTP_500_INTERNAL_SERVER_ERROR` | 서버 오류 | `macro/views.py` 9회, `users/views.py` 다수 |
| `HTTP_201_CREATED` | 생성 성공 | `users` 5회, `serverless` 4회, `rag_analysis` 4회 |
| `HTTP_204_NO_CONTENT` | 삭제 성공 | `users`, `rag_analysis` |

### 일관성 이슈

#### ① 201 Created 사용 누락
**다음 POST 엔드포인트는 생성 성공 시에도 200을 반환** (REST 관례 위반):

- `users.AddFavorite` (`/api/v1/users/favorites/{id}/`) — 즐겨찾기 추가 후 200
- `chainsight.api.views` POST 액션 (해당 시) — `Response({...})` 기본 200
- `news/api/views.py` 모든 액션 (`@action methods=['post']`) — 명시적 201 사용 없음
- `thesis/views/thesis_views.py` `close()` 액션 — 가설 마감 시 200
- `thesis/views/conversation_views.py` `start/respond/suggest` — 200
- `serverless/views_admin.py` 일부 카테고리 PUT은 200으로 통일 (이건 OK)

→ 모든 POST 응답에 201을 강제하는 것은 과한 변화이지만, **신규 리소스가 생성되는 엔드포인트는 201로 통일** 권장.

#### ② Status 모듈 vs 하드코딩 분리
- `portfolio/views.py`는 **DRF 자체 미사용** (순수 Django `JsonResponse`) — `status=400`, `status=429`, `status=503` 등 하드코딩이 정상
- `sec_pipeline/views.py`는 DRF Response를 쓰면서도 `status=202`, `status=200`을 하드코딩 → `status.HTTP_202_ACCEPTED`로 통일 가능

#### ③ 비표준 사용 1건
- `users/views.py:559` → `status=status.HTTP_207_MULTI_STATUS` 사용 (즐겨찾기 batch에서 일부 성공/일부 실패 시) — 정당한 사용이나 프론트가 207을 처리하는지 검증 필요

---

## 에러 응답 형식

### 키 분포 통계

| 에러 키 | 총 발생 | 파일 수 | 주요 파일 |
|---|---:|---:|---|
| `'error'` (single quote) | **159회** | 12개 | 전 앱 표준 |
| `"error"` (double quote) | 80회 | 9개 | `stocks/views_*` 가족 |
| `'detail'` | **3회** | 2개 | `users/views.py` 2, `config/views.py` 1 |
| `"detail"` (`portfolio`) | n/a | 1개 | `portfolio/views.py` 모든 에러에 추가 |
| `'message'` | 99회 | 10개 | 거의 모든 앱 — **에러 본문/안내 문구 양쪽 사용** |

### 형식 패턴별 분류

#### 패턴 A — 평문 문자열 (가장 흔함, ~80%)
```python
{"error": "검색어는 최소 2글자 이상 입력해주세요."}
{"error": f"Stock {symbol} not found"}
{"error": "로그인이 필요합니다."}
```
**해당 앱**: `users`, `macro`, `validation`, `chainsight`, `news`, `stocks/*` (에러만), `thesis`

#### 패턴 B — 중첩 코드+메시지 객체 (`serverless/views.py` 전용)
```python
{
    "success": False,
    "error": {
        "code": "INVALID_TYPE",
        "message": f"Invalid type: {mover_type}..."
    }
}
```
**해당**: `serverless/views.py` (62회), `rag_analysis/views.py` (`create_error_response` 헬퍼)

#### 패턴 C — error + detail 조합 (`portfolio/views.py` 전용)
```python
{"error": "invalid_provider", "detail": f"{provider!r} not in {list(...)}"}
{"error": "budget_exceeded", "detail": str(exc)}
{"error": "llm_response_schema_mismatch", "detail": str(exc)[:500]}
```
**해당**: `portfolio/views.py` 전체 — 가장 정보량 높은 형태

#### 패턴 D — DRF 기본 (`raise ValidationError`, `raise NotFound`)
```python
raise NotFound(_("Watchlist not found"))   # → {"detail": "..."}
raise ParseError("Password is required")    # → {"detail": "..."}
```
**해당**: `users/views.py` (NotFound, ParseError), `rag_analysis/views.py` (ValidationError)

→ **DRF 기본 예외 클래스는 자동으로 `{"detail": "..."}` 형식 생성**. 따라서 `users/views.py:120` `raise NotFound`는 `detail` 응답을, 같은 파일 200줄 아래의 `Response({"error": ...}, 404)`는 `error` 응답을 — **같은 파일에서 둘 다 사용**.

#### 패턴 E — `serializer.errors` 그대로
```python
return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```
**해당**: `users/views.py` 다수, `portfolio` (POST 검증 실패 시), `rag_analysis` (`create_error_response("INVALID_INPUT", str(serializer.errors))`로 한 단계 감싸기는 함)

→ `serializer.errors`는 DRF가 `{"field_name": ["error message"]}` 형식으로 생성 — **에러 키 자체가 동적**. 프론트에서 처리하려면 별도 파서 필요.

### 종합 — 프론트가 직면하는 5가지 에러 형식
실제 한 페이지에서 호출하는 다른 API들이 다음 5가지 응답 중 하나를 반환할 수 있음:

```js
// 1. 평문 error
{"error": "Stock not found"}

// 2. nested error (serverless)
{"success": false, "error": {"code": "NOT_FOUND", "message": "..."}}

// 3. error + detail (portfolio)
{"error": "invalid_request", "detail": "..."}

// 4. DRF detail
{"detail": "Authentication credentials were not provided."}

// 5. serializer field errors
{"name": ["This field is required."], "email": ["Enter a valid email."]}
```

---

## 페이지네이션 현황

### DRF 표준 미사용
- `config/settings.py:348` `REST_FRAMEWORK` 설정에 **`DEFAULT_PAGINATION_CLASS` 없음**
- `PageNumberPagination`, `CursorPagination`, `LimitOffsetPagination` 사용 흔적 **0건**
- `pagination_class = ...` ViewSet 속성 사용 **0건**

### 수동 페이지네이션 (4 곳, Django Paginator)

| 위치 | 페이지 키 구조 |
|---|---|
| `users/views.py:610` (Watchlist 목록) | `{"results", "pagination": {"count", "page", "page_size", "num_pages", "has_next", "has_previous"}}` |
| `users/views.py:830` (Watchlist 종목 목록) | 동일 구조 |
| `rag_analysis/views.py:800` (Usage 히스토리) | `{"results", "pagination": {"current_page", "page_size", "total_pages", "total_count", "has_next", "has_previous"}}` ← 키 이름이 다름 (`current_page` vs `page`, `total_pages` vs `num_pages`) |
| `news/api/views.py` | **수동 페이지네이션 없음** — 모든 목록은 in-query `.order_by(...)[:N]` 슬라이스 |

→ 같은 회사 내 **두 가지 다른 페이지네이션 페이로드 형식** 공존.

### `.all()` / `.filter()` 후 페이지네이션 없이 반환 (위험 — N+1 / 무제한 응답)

총 174회 `.objects.all/filter` 발생. 다음은 페이지네이션도 limit slice도 없는 명백 케이스:

| 위치 | 위험 |
|---|---|
| `users/views.py:92` `User.objects.all()` (관리자 전용) | 사용자 수만큼 응답 ↑ |
| `users/views.py:193` `user.favorite_stock.all()` | 즐겨찾기 무제한 |
| `users/views.py:264` `Portfolio.objects.filter(user=...).select_related('stock')` | 포트폴리오 종목 수만큼 |
| `users/views.py:358` `PortfolioSummaryView.get()` | 동일 |
| `stocks/views_mvp.py:195` `SectorListView` `.distinct()` | 섹터 전체 list (작긴 함) |
| `stocks/views_search.py:153` `PopularSymbolsView` | 하드코딩 15개라 안전 |
| `stocks/views.py:75` `StockListAPIView(ListAPIView)` | DRF `generics.ListAPIView` 기반이지만 `pagination_class` 없음 → 전체 반환 |
| `chainsight/api/views.py:120` `ChainSightSuggestionView` `.order_by(...)[:10]` | 슬라이스 OK |
| `validation/api/views.py:80` `CategorySignal.objects.filter(...).order_by(...)` (전체 반환) | 카테고리 6~7개라 안전 |
| `news/api/views.py:95` `NewsArticle.objects.filter(...).distinct().order_by(...)` | **상위 슬라이스 없음** → 7~30일 기간 전체 |
| `news/api/views.py:716` `NewsArticle.objects.filter(id__in=article_ids).order_by(...)[:10]` | 슬라이스 OK |
| `serverless/views.py:1039` `ScreenerPreset.objects.filter(...).distinct().order_by(...)` | 프리셋 전체 |
| `rag_analysis/views.py:76` `DataBasket.objects.filter(user=...).prefetch_related(...)` | 사용자 바구니 전체 |
| `thesis/views/thesis_views.py:46` `Thesis.objects.filter(user=...)` | 사용자 가설 전체 |

→ **가장 위험한 곳**: `news/api/views.py` `stock_news` 액션 — 종목/기간에 따라 수백 건 응답 가능.

### 페이지네이션 권고

1. `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS'] = 'rest_framework.pagination.PageNumberPagination'` + `DEFAULT_PAGE_SIZE = 50` 등록
2. `generics.ListAPIView` 기반 뷰 (예: `StockListAPIView`)는 자동으로 페이지네이션 적용됨
3. APIView 기반은 수동 적용 — 기존 2종 페이로드 구조를 1종으로 통일

---

## 권고사항

### P0 — 즉시 조치 (1~2 sprint)

**1. 응답 표준 결정 + 명문화** ([DECISIONS.md] 항목 추가)
- 옵션 A: **DRF 기본 (`Response(serializer.data)`)** 유지 + 헬퍼 미사용 → 단순함, BC 영향 작음
- 옵션 B: **`{success, data, meta, error}` 표준 강제** (`rag_analysis.create_*_response` 패턴 확장) → 프론트 단일 파서 가능, 마이그레이션 비용 큼
- **권고: 옵션 A** — 이미 다수 앱이 raw 패턴, `serverless`만 예외 → `serverless`를 표준으로 정렬하기보다는 신규 표준 wrapper 도입 시 점진 마이그레이션

**2. 에러 형식 단일화 — DRF `{"detail": "..."}` 표준 채택**
- DRF의 모든 내장 예외(`NotFound`, `ParseError`, `ValidationError`, `PermissionDenied`)가 이미 `detail` 키 사용
- 커스텀 `EXCEPTION_HANDLER` 등록 시 비DRF 예외도 `detail` 형식으로 변환 가능
- 추가로 `code` 필드를 옵션으로 (`{"detail": "...", "code": "INVALID_PROVIDER"}`) — 프론트 i18n에 유용

**3. `stocks/views_*` 가족 에러 응답 wrap 비대칭 해소**
- `views_fundamentals/screener/exchange`는 성공만 wrap, 에러는 평문 → 프론트가 응답 형태를 두 번 검사해야 함
- 즉시 수정: 에러 응답도 `{"success": False, "error": ...}` 형태로 통일하거나, 성공 wrap을 제거

**4. `DEFAULT_PAGINATION_CLASS` 등록 + 무제한 목록 API 식별**
- 위 표 "페이지네이션 없음" 항목 모두 명시적 limit (예: `[:100]`) 추가
- `news/api/views.py:95` `stock_news`, `users.UserFavorites` 우선

### P1 — 다음 분기 (3~6 sprint)

**5. 단일 응답 wrapper 헬퍼 + 자동 적용 미들웨어**
- `rag_analysis/views.py:35-61`의 `create_success_response` / `create_error_response`를 공용 모듈 (예: `core/responses.py`)로 이전
- 신규 엔드포인트는 wrapper 강제, 레거시는 deprecated 표시 후 점진 변환

**6. `portfolio/views.py` DRF로 마이그레이션 검토**
- 순수 Django `JsonResponse`만 사용 → DRF 인증/권한/스로틀링/Spectacular 스키마 자동 생성 등 혜택 없음
- 단, LLM 호출 + Pydantic 검증 패턴이 `JsonResponse`에 잘 들어맞으므로 의도적 선택일 가능성 → 결정 기록 필요

**7. POST 응답 201 일관성**
- 새 리소스 생성 엔드포인트 (Watchlist 항목 추가, 가설 close, 카테고리 추가 등) 모두 `HTTP_201_CREATED`

**8. `serializer.errors` 직접 반환 제거**
- DRF는 동적 키(`{"field": ["msg"]}`)로 응답 — 클라이언트 스키마 추론 불가
- `EXCEPTION_HANDLER`에서 일관된 형식으로 변환

### P2 — 장기 (분기 단위)

**9. OpenAPI/Spectacular 스키마 정합성 점검**
- 응답 wrap 패턴 차이로 자동 생성 스키마가 부정확할 가능성 — `extend_schema(responses=...)` 명시적 선언 필요한 엔드포인트 식별

**10. `success` boolean 무용성 검토**
- HTTP 상태 코드(2xx vs 4xx/5xx)가 이미 성공/실패를 명확히 표현 → `success` 키는 중복 정보
- 단, `serverless/views.py`처럼 `success: false` + 200 상태로 내려보내는 케이스가 있다면 의미 있음 (있는지 확인 필요)

---

## 부록 — 참조 파일

| 파일 | 발견 사항 |
|---|---|
| `config/settings.py:348-362` | `REST_FRAMEWORK` 설정 — pagination/exception_handler 미설정 |
| `serverless/views.py` (3413줄) | nested error 표준의 가장 큰 사례 — 마이그레이션 비용 산정 시 기준 |
| `rag_analysis/views.py:35-61` | `create_success_response`/`create_error_response` 헬퍼 — 표준 wrapper 모범 |
| `stocks/views_fundamentals.py:75-99` | 성공/실패 비대칭 wrap 사례 |
| `users/views.py:610-628` | 수동 페이지네이션 페이로드 형식 #1 (`page`, `num_pages`) |
| `rag_analysis/views.py:822-829` | 수동 페이지네이션 페이로드 형식 #2 (`current_page`, `total_pages`) |
| `portfolio/views.py` 전체 | DRF 미사용 + `error+detail` 형식의 모범적 일관성 — 다른 앱 참조 가치 있음 |

---

## 같은 폴더의 기존 감사 보고서

같은 디렉토리(`docs/nightly_auto_system/reports/5월/10일/`)의 다른 보고서들과 교차 참조 권장:

- `api_dependency_audit.md` — API 의존성 그래프
- `api_docs_audit.md` — API 문서화 (Spectacular)
- `data_integrity_audit.md` — 데이터 무결성
- `performance_audit.md` — 성능
- `security_audit.md` — 보안

특히 `api_docs_audit.md`와 본 보고서의 P2 #9 항목이 연결됨.
