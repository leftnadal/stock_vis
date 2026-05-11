# API 응답 일관성 감사 보고서

- 감사일: 2026-04-28 (4월 27일자 정기 감사)
- 감사 대상: Django REST 백엔드 24개 `views*.py` 파일 (`thesis/views/*.py` 3개 포함)
- 분석 라인 수: ≈ 14,375 라인 (`wc -l` 합계 13,283 + thesis 1,092)
- 빈 파일(분석 제외): `chainsight/views.py`, `validation/views.py`, `news/views.py`, `metrics/views.py`, `graph_analysis/views.py` (5개 / 각 1~3 라인)
- 방법: ripgrep 패턴 카운트 + 파일별 핵심 라인 검증
- **본 보고서는 코드 변경 없는 읽기 전용 감사 결과입니다**

---

## 요약

이번 감사에서도 **단일 응답 컨벤션은 부재**하며, 4월 26일 보고서 시점 대비 구조적 변화는 없다. `serverless/views.py`(envelope 116회) ↔ `serverless/views_admin.py`(직접 dict, envelope 1회만) 의 같은 앱 내부 모순이 그대로 유지되고, `sec_pipeline/views.py`의 정수 status 하드코딩(3건)도 미수정 상태다. `rag_analysis/views.py`만이 헬퍼 함수 추상화를 통해 일관된 envelope을 보장한다.

| 영역 | 핵심 발견 | 심각도 |
|------|----------|--------|
| 응답 래핑 | 6개 패턴 혼재 (envelope / 직접 serializer / 임시 dict / `JsonResponse` / DRF auto-detail / 수동 페이지네이션 dict) | **CRITICAL** |
| HTTP 상태 코드 | `status.HTTP_*` 248회 vs 하드코딩 정수 4회 (`sec_pipeline/views.py:40,44,46`, `serverless/views.py:2879`) | **MEDIUM** |
| POST 생성 시 201 사용 | 14회 / 4개 파일에 국한 (`users`, `serverless`, `serverless_admin`, `rag_analysis`) — 그 외 POST 엔드포인트는 200 반환 | **HIGH** |
| 에러 응답 형식 | `'error'`(195) / `'detail'`(3) / `'message'`(112) + 중첩 `{error:{code,message}}` 4가지 키 혼재 | **CRITICAL** |
| 페이지네이션 | DRF `PageNumberPagination` / `CursorPagination` / `LimitOffsetPagination` / `pagination_class` **사용 0건**, `REST_FRAMEWORK` 설정의 `DEFAULT_PAGINATION_CLASS` **미설정** | **CRITICAL** |
| 수동 `Paginator` 사용 | 2개 파일(`users/views.py`, `rag_analysis/views.py`)만 명시적 페이지네이션 응답 메타 제공 | **HIGH** |
| 무한정 `.all()` / `.filter()` 반환 | `stocks/views.py:75-85`(StockListAPIView, `Stock.objects.all()`), `serverless/views_admin.py:478`, `macro/*` 다수 | **HIGH** |
| 하드코딩 슬라이스 | `[:7]`, `[:12]`, `[:20]`, `[:50]` 등 query param 미노출 | **MEDIUM** |

---

## 앱별 응답 패턴 매트릭스

> 약어
> - **A** = `{success: bool, data: ..., meta?: ...}` envelope
> - **B** = 직접 `Response(serializer.data)` 또는 임시 dict (DRF 기본 스타일)
> - **C** = 임시 키 dict (`{count, results}`, `{symbol, tab, data}`, `{alerts, unread_count}` 등)
> - **D** = `JsonResponse()` (REST `Response` 미사용)
> - **H** = 헬퍼 함수 추상화 (`create_success_response` / `create_error_response`)

| 앱 / 파일 | 라인 | 주 패턴 | `success` 사용 | 에러 키 분포 | 비고·근거 라인 |
|----------|-----:|--------|---------------:|-------------|---------------|
| `stocks/views.py` | 1020 | **B+C 혼재** | 0 | `error`(12), `message`(0) | L142 `Response(serializer.data)`, L580 `status=status.HTTP_200_OK` 명시; L587-595 단 1건만 중첩 `{error:{code,message,details}}` outlier |
| `stocks/views_screener.py` | 498 | **A** ✅ | 7 | `error`(8) | L94-106·150-157 `{success, data, meta}` 일관 |
| `stocks/views_market_movers.py` | 69 | **B** | 0 | `error`(1) | L69 `Response(serializer.data)`; `last_updated` 메타 dict |
| `stocks/views_eod.py` | 136 | **C** | 0 | `error`(3) | L102-107 `{signal_id, date, count, stocks}`; L136 `{logs: data}` |
| `stocks/views_indicators.py` | 372 | **C** | 0 | `error`(3) | 캐시 hit 경로(L39, L215)에서 status 미명시 |
| `stocks/views_search.py` | 229 | **C** | 0 | `error`(5) | L75-77 `{count, results}`, L124-132 `{valid, ...}` |
| `stocks/views_fundamentals.py` | 305 | **A** ✅ | 5 | `error`(10) | L89-98 `{success, data, meta:{symbol, period, count, timestamp}}` |
| `stocks/views_exchange.py` | 295 | **A** ✅ | 5 | `error`(8) | 5 엔드포인트 전부 envelope |
| `stocks/views_mvp.py` | 200 | **C** | 0 | 없음 | `get_object_or_404` 의존 |
| `users/views.py` | 1080 | **B+C 혼재** | 0 | `error`(8), `detail`(2), `message`(7) | L208 `{message: '이미 즐겨찾기에 있음'}` (에러), L215-218 `{message, stock}` (성공인데 message 키), L335 `HTTP_204_NO_CONTENT`, `Paginator` 수동 사용(L602, L822) |
| `serverless/views.py` | 3405 | **A** ✅ | 116 (`'success'` 62 + `"success"` 0 ⇒ 단일 따옴표 사용) | 중첩 `{error:{code,message}}` 60+ | L70-76·140-147 일관; **outlier**: L2879 `status=400` 정수 하드코딩 |
| `serverless/views_admin.py` | 694 | **B+C 혼재** | 1 | `error`(28), `message`(1) | L162-164·182-184·332-334 `{error: str}` 단순; L400-408만 envelope 부분 적용 — **같은 앱 안에서 컨벤션이 정반대** |
| `news/api/views.py` | 2183 | **B+C 혼재** | 0 | `error`(7), `message`(3), `raise ValidationError({field:msg})` 9건 | L277-281 `{category, count, articles}` 임시 dict; L236·308·535·624·662·668·672·867·1037 `ValidationError` → DRF auto-detail 변환 의존 |
| `news/views.py` | 3 | **빈 파일** | — | — | placeholder |
| `macro/views.py` | 410 | **B** | 0 | `error`(15), `message`(10) | L40·65 `Response(serializer.data)`; L43-46·67-72 `{error: '...'}` 단순; L376-379 `{status: 'started', message: '...'}` |
| `config/views.py` | 104 | **D** | 0 | `error`(1), `message`(1) | L19-67·77-82 `JsonResponse(...)` — REST `Response` 미사용; status 코드 명시 없음 |
| `chainsight/api/views.py` | 804 | **B+C 혼재** | 0 | `error`(9), `message`(0) | L67·91-99 `_sanitize_neo4j(...)` + `meta` 추가; L67 `{error: f'Stock {symbol} not found'}` |
| `chainsight/views.py` | 1 | **빈 파일** | — | — | — |
| `thesis/views/thesis_views.py` | 333 | **B** | 0 | `error`(2) | L70·77 `{error: '...'}` 단순; L143 `{status:'closed', thesis_id}` 임시 dict; close 액션 200 반환 |
| `thesis/views/conversation_views.py` | 380 | **B** | 0 | `error`(미상) | L201 `[:12]` 슬라이스 하드코딩; L211 `{issues: ...}` 임시 dict |
| `thesis/views/monitoring_views.py` | 364 | **B** | 0 | 거의 없음 | L238 `[:50]` 슬라이스; L241-244 `{alerts, unread_count}` 임시 dict; L257 `{status:'read'}` |
| `validation/api/views.py` | 558 | **B+C 혼재** | 0 | `error`(15), `message`(4) | L59 `{error: f'Stock {symbol} not found'}`; L64-67 `{symbol, error:'not_in_universe', message:'...'}` (에러를 200으로 반환) |
| `validation/views.py` | 1 | **빈 파일** | — | — | — |
| `rag_analysis/views.py` | 864 | **A+H** ✅ | 1 (헬퍼 추상화) | `{error:{code,message}}` (헬퍼 표준화) | L33-43 `create_success_response`, L46-59 `create_error_response`; `meta`에 `request_id` + `timestamp` 자동; `HTTP_201_CREATED` 4회, `HTTP_204_NO_CONTENT` 3회 |
| `sec_pipeline/views.py` | 46 | **B (정수 하드코딩)** | 0 | 없음 | L40 `status=202`, L44·46 `status=200` — `from rest_framework import status` 임포트 자체 없음 |
| `metrics/views.py` | 3 | **빈 파일** | — | — | — |
| `graph_analysis/views.py` | 3 | **빈 파일** | — | — | — |

**관찰 1.** envelope 패턴(A)을 명시적으로 채택한 곳: ① `serverless/views.py`(116회 인라인), ② `rag_analysis/views.py`(헬퍼 추상화), ③ `stocks/views_fundamentals.py`·`views_exchange.py`·`views_screener.py`(인라인). 그 외 18개 파일은 모두 B/C/D.

**관찰 2.** `serverless/views.py` ↔ `serverless/views_admin.py` 가 **동일 prefix(`/api/v1/serverless/*`)에서 정반대 컨벤션**을 사용한다. `views.py`는 envelope 116회, `views_admin.py`는 envelope 1회 + 단순 `{error: str}` 28회.

**관찰 3.** `meta` 필드의 의미가 파일마다 다름:
- `rag_analysis`: `request_id` + `timestamp` (관찰 가능성)
- `stocks/views_fundamentals`: `symbol` + `period` + `count` + `timestamp` (요청 메타)
- `stocks/views_screener`: `is_enhanced` + `total_before_filter` + `timestamp` (필터 메타)
- `chainsight/api/NeighborGraphView`: `depth` + `node_count` + `query_ms` (성능 메타)
→ 같은 키 이름이지만 **클라이언트가 의미를 파일별로 다르게 파싱**해야 한다.

**관찰 4.** `users/views.py`는 한 파일 안에서 `error`(8) / `detail`(2) / `message`(7) 세 키를 동시 사용하며, L208(에러)·L215(성공) 모두 `message` 키를 쓰는 등 **성공/실패 키 충돌**이 있다.

---

## HTTP 상태 코드 일관성

### 통계

| 항목 | 카운트 | 비고 |
|-----|------:|------|
| `status.HTTP_*` 상수 사용 | **248회** (16개 파일) | 표준 |
| 정수 하드코딩 (`status=200/202/400`) | **4회** | `sec_pipeline/views.py:40,44,46`, `serverless/views.py:2879` |
| `status.HTTP_201_CREATED` | **14회** (4개 파일) | `users`(5+조건부 2), `rag_analysis`(4), `serverless`(3), `serverless_admin`(1) |
| `status.HTTP_204_NO_CONTENT` | **8회** (3개 파일) | `users`(4), `rag_analysis`(3), `serverless_admin`(1) |

### 201 누락 의심 (POST를 가지면서 `HTTP_201_CREATED` 미사용)

| 파일 | 증거 | 영향 |
|------|------|------|
| `news/api/views.py` | POST 다수, 201 한 번도 없음 | 클라이언트가 모든 성공=200으로 가정 |
| `thesis/views/thesis_views.py` | 가설 close 액션 등 POST → 200 (L143) | REST 시맨틱 위반 |
| `thesis/views/conversation_views.py` | 대화 생성/메시지 추가 시 200 | 동일 |
| `chainsight/api/views.py` | POST 9건 검출되었으나 201 없음 | 동일 |
| `validation/api/views.py` | Preset 생성에도 200 | 동일 |
| `macro/views.py` | DataSyncView L376-379 POST → 200 + `{status:'started'}` | 동일 |
| `sec_pipeline/views.py` | L40 `status=202`(처리 중)는 의도 있으나 정수 하드코딩 | 표준 위반 |

### 이상치 (Outlier)

- **`sec_pipeline/views.py:40, 44, 46`**: `status=202`, `status=200` 정수 하드코딩. `from rest_framework import status` import 자체가 없음 (L1-11 검증).
- **`serverless/views.py:2879`**: 같은 파일에서 96곳이 `status.HTTP_*`를 쓰지만 이 한 줄만 `status=400` 정수.
- **`stocks/views_indicators.py:39, 215`**: 캐시 hit 경로에서 `status` 인자 생략 → 암묵적 200. 동일 메서드 다른 분기는 명시.
- **`config/views.py`**: `JsonResponse` 사용으로 status 코드 명시 없음. DB/캐시 실패 케이스에도 implicit 200 — 헬스체크가 항상 healthy로 보일 수 있음.
- **`validation/api/views.py:64-67`**: 에러 페이로드(`error: 'not_in_universe'`)인데 `status=status.HTTP_200_OK`로 반환 — 4xx 시맨틱과 충돌.
- **`stocks/views.py:986`**: 동일 엔드포인트에서 success/partial-failure 모두 200 반환(207 Multi-Status 미사용).

---

## 에러 응답 형식

### 키 분포 (310회 매칭 합계)

| 키 패턴 | 발견 위치 | 빈도 |
|--------|----------|-----:|
| `{'error': '<문자열>'}` | `stocks/*`, `users/`, `macro/`, `thesis/*`, `chainsight/api/`, `validation/api/`, `serverless/views_admin.py`, `news/api/` | **195회 / 16개 파일** |
| `{'success': False, 'error': {'code': '...', 'message': '...'}}` | `serverless/views.py`(60+), `rag_analysis/views.py`(헬퍼), `stocks/views.py:587-595`(1건 outlier) | ~80회 |
| `{'detail': '...'}` | DRF 기본 예외(`ValidationError`, `NotFound`, `PermissionDenied` 자동 변환) | **3회 명시 + 다수 자동** |
| `{'message': '...'}` | `users/views.py:208,215`, `serverless/views.py` 일부, `sec_pipeline/views.py:39`, `macro/views.py` 일부 | **112회 / 10개 파일** |
| `{field: msg}` (`raise ValidationError({...})`) | `news/api/views.py:236, 308, 535, 624, 662, 668, 672, 867, 1037` | **9회** |
| `{symbol, error}` 변종 | `validation/api/views.py:64-67` | 다수 |

### 형식 불일치 사례

1. **`stocks/views.py`의 단독 outlier (L587-595)**
   - 16개의 `error` 사용 중 단 1곳만 중첩 객체 형식 `{'error': {'code': 'OVERVIEW_ERROR', 'message': '...', 'details': {...}}}`
   - 나머지는 모두 `{'error': '<문자열>'}` 단순형
   - → 클라이언트가 `error`가 string인지 object인지 type-narrowing 필요

2. **`users/views.py` 내부 키 혼재**
   - L166: `{'error': 'Wrong username or password'}` (에러)
   - L208: `{'message': 'This stock is already in your favorites'}` (에러를 message 키에)
   - L215-218: `{'message': 'Stock added...', 'stock': {...}}` (성공인데 message 키)
   - DRF `NotFound` 자동: `{'detail': '...'}`
   - → 같은 도메인의 4xx가 3가지 키 형식

3. **`serverless/views.py` ↔ `serverless/views_admin.py` 상충**
   - `views.py:70-76`: `{success: False, error: {code: 'INVALID_TYPE', message: '...'}}`
   - `views_admin.py:163, 182, 333`: `{error: '...'}` 단순형
   - `views_admin.py:400-408`: envelope 일부 적용
   - → 같은 앱 prefix에서 클라이언트가 두 형식을 처리

4. **`news/api/views.py`의 4xx 페이로드 두 가지**
   - L236: `raise ValidationError({'category': 'Invalid...'})` → DRF가 `{'category': ['Invalid...']}` (리스트 값)으로 변환
   - 같은 모듈 다른 액션에서는 `Response({'error': '...'}, status=400)` 직접 반환
   - → 4xx 응답 페이로드가 일관되지 않음

5. **`config/views.py` 헬스체크의 두 가지 형식**
   - L19-67: 복잡한 nested endpoints dict + 메타
   - L77-82: `{status, service, database, cache}` flat
   - 동일 파일·헬스 도메인인데 형식 다름

6. **`validation/api/views.py` 에러를 200으로**
   - L64-67: `{symbol, error: 'not_in_universe', message: '...'}, status=HTTP_200_OK`
   - "지원하지 않는 종목"인데 200 반환 — 비-에러로 응답 → 클라이언트 분기 복잡화

---

## 페이지네이션 현황

### DRF 표준 페이지네이션 사용 현황

```
DEFAULT_PAGINATION_CLASS in REST_FRAMEWORK settings: ❌ 미설정 (config/settings.py 검증)
PageNumberPagination 사용:                            ❌ 0회
CursorPagination 사용:                                ❌ 0회
LimitOffsetPagination 사용:                           ❌ 0회
pagination_class 클래스 속성 설정:                    ❌ 0회
generics.ListAPIView 사용:                            ✅ 1회 (stocks/views.py:75)
```

### 핵심 모순

`generics.ListAPIView`를 사용하는 단 한 곳(`StockListAPIView` L75-105)이 `pagination_class`를 지정하지 않았고 settings에도 `DEFAULT_PAGINATION_CLASS`가 없어서 → **`Stock.objects.all()` 전체를 무조건 반환**한다(L85). 종목 수가 수천~수만이 될 수 있는 엔드포인트.

### 수동 페이지네이션 (Django `Paginator` 직접 사용)

| 파일·라인 | 패턴 | 응답 형식 |
|----------|------|----------|
| `users/views.py:602` (WatchlistListCreateView) | `Paginator(watchlists, page_size)` | L610-620 `{'results', 'pagination': {count, page, page_size, num_pages, has_next, has_previous}}` |
| `users/views.py:822` (WatchlistStocksView) | 동일 패턴 | 동일 |
| `rag_analysis/views.py:796` (UsageHistoryView) | `Paginator(logs, page_size)` (max 100) | L818-824 `{'results', 'page', 'page_size', 'total', 'total_pages', 'has_next', 'has_previous'}` (`pagination` 래핑 없음) |

→ users는 `pagination` 객체로 감싸지만 rag_analysis는 평면. 같은 수동 패턴인데도 응답 키 다름.

### 수동 offset/limit (Paginator 미사용)

| 파일·라인 | 응답 키 |
|----------|--------|
| `serverless/views.py:1171-1184` (execute_preset) | `{results, count, total_pages, current_page, next, previous}` (L1351-1358) |
| `serverless/views.py:1309-1358` (advanced_screener_api) | 동일 |
| `news/api/views.py:368-433` (all_news) | `{count, articles, has_more}` 커스텀 |
| `chainsight/api/views.py:623-805` (SignalFeedView) | `page`/`page_size` 입력, `has_next` 응답 |
| `chainsight/api/views.py:445` (NeighborGraphView) | `limit`(max 30), 페이지네이션 메타 없음 |
| `stocks/views_screener.py:127, 260-262` | `limit`(1~1000), 메타 없음 |
| `stocks/views_fundamentals.py:64-65, 123-124` | `limit`(1~40), `count`만 메타 |
| `stocks/views_exchange.py:150` | `limit`(1~100) |
| `stocks/views_market_movers.py:47` | `limit`(1~20) |

→ **각자 다른 키 이름**: `count` vs `total`, `current_page` vs `page`, `has_more` vs `has_next` vs `next`. 동일 클라이언트가 5종 이상의 응답 형식을 분기해야 함.

### 하드코딩 슬라이스 (query param 미노출)

| 파일·라인 | 슬라이스 | 영향 |
|----------|----------|------|
| `stocks/views_search.py:56` | `[:10]` | 검색 결과 10개 고정 |
| `stocks/views_eod.py:119` | `[:7]` | 최근 7일 고정 |
| `stocks/views_indicators.py:64` | 슬라이스 없음 | 한 종목 모든 일자 반환 |
| `stocks/views_mvp.py:41` | `[:20]` | 20개 고정 |
| `news/api/views.py:336` | `[:3]` | 트렌딩 3개 고정 |
| `thesis/views/conversation_views.py:201` | `[:12]` | 뉴스 이슈 12개 고정 |
| `thesis/views/monitoring_views.py:238` | `[:50]` | 알림 50개 고정 |
| `stocks/views.py:148` | `[:30]` | 차트용 최근 30일 고정 (UI 용도라 OK 가능성) |

### 무한정 `.all()` 또는 `.filter()` 반환

| 파일·라인 | 모델 | 위험 |
|----------|------|------|
| `stocks/views.py:75-85` (StockListAPIView) | `Stock` | 전체 종목 반환(수만 건) |
| `stocks/views_indicators.py:64` | `DailyPrice` | 한 종목의 모든 일자 |
| `serverless/views_admin.py:478` | `NewsCollectionCategory.objects.all()` | 전체 카테고리 |
| `serverless/views_admin.py:671-683` | 태스크 로그 (limit 있으나 메타 없음) | 부분적 |
| `macro/views.py` 다수 | 거시 데이터 | 데이터 양에 따라 위험 |
| `validation/api/views.py` LeaderComparisonView | 비교 결과 전체 | 사이즈 종속 |

### 핵심 문제 (반복)

**모든 list 엔드포인트가 자체 페이지네이션 규약을 따로 만든다.** `count`·`total`·`results`·`articles` 등 응답 키가 통일되지 않으며, 4월 26일 보고서 시점에서 변화 없음.

---

## 권고사항

> **본 보고서는 감사 결과만 기록하며, 변경은 별도 PR/계획 단계에서 결정한다.**

### 즉시 검토 (Critical)

1. **공통 응답 envelope 결정**
   - 옵션 A: `{success, data, meta}` envelope을 모든 엔드포인트에 강제 (현재 `serverless/views.py`·`rag_analysis`·`stocks/views_fundamentals|exchange|screener` 채택)
   - 옵션 B: DRF 기본(직접 `serializer.data`) + DRF Exception Handler 표준화
   - 단일 결정 후 `contracts/` OpenAPI 스펙에 명시 필요

2. **에러 응답 형식 통일**
   - `{'error': string}` (단순) vs `{'error': {code, message}}` (객체) 중 택일
   - `{'message': '...'}`을 에러 키로 쓰는 `users/views.py:208`, `sec_pipeline/views.py:39` 정리
   - `validation/api/views.py:64-67` 에러를 200으로 반환하는 패턴 정상화 (4xx로 변경)
   - DRF custom `EXCEPTION_HANDLER` 도입 → 미들웨어로 일괄 변환

3. **DRF 페이지네이션 표준 도입**
   - `config/settings.py`의 `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE` 추가
   - `StockListAPIView`처럼 `generics.ListAPIView` 사용하면서 무한정 반환되는 케이스 차단
   - 기존 수동 페이지네이션 사용 엔드포인트는 호환성 어댑터 작성

### 단기 개선 (High)

4. **`sec_pipeline/views.py` 정수 하드코딩 정리**
   - L40·44·46: `status=200/202` → `status=status.HTTP_200_OK / HTTP_202_ACCEPTED`
   - `from rest_framework import status` 추가

5. **POST 생성 엔드포인트 201 강제**
   - `news/api/`, `thesis/`, `chainsight/api/`, `validation/api/`, `macro/DataSyncView`에서 POST 시 `HTTP_201_CREATED` 검토

6. **`serverless/views.py` ↔ `serverless/views_admin.py` 컨벤션 일치**
   - 같은 앱 prefix에서 envelope 패턴 통일이 우선

7. **`users/views.py` 키 표준화**
   - L208 `{message: ...}`(에러) → `{error: ...}`로 변경
   - L215 `{message, stock}`(성공) → `{stock}` 또는 envelope의 `data` 영역으로 이동

### 중기 개선 (Medium)

8. **하드코딩 슬라이스 → `limit` query param 노출**
   - `[:7]`, `[:12]`, `[:20]`, `[:50]` 등 사용자 제어 가능하게

9. **`StockListAPIView`·`macro/*` 무한정 반환 차단**
   - `max_page_size` 강제, 응답 페이로드 크기 측정 후 한계 결정

10. **`config/views.py` 헬스체크 응답 표준화**
    - DB/캐시 실패 시 503 반환 검토
    - `JsonResponse` → DRF `Response` 통일 검토

11. **`rag_analysis/create_success_response` 헬퍼 공용화**
    - `meta.request_id` + `meta.timestamp` 자동 부여 패턴은 좋은 출발점
    - `common/responses.py` 등에 두고 다른 앱이 재사용

### 메타·검증

12. **`contracts/` OpenAPI 스펙과 실 응답 대조**
    - 현재 envelope/non-envelope 혼재 상태가 contracts에 어떻게 기술되어 있는지 별도 감사 필요
    - 본 감사에서는 contracts 비교를 수행하지 않음

13. **응답 형식 회귀 테스트(스냅샷)**
    - 파일별 대표 엔드포인트의 응답 키 set 비교 테스트 추가
    - DRF 표준 도입 시 backward-compat 검증 필수

---

## 4월 26일 보고서와의 차이

본 4월 27일 감사는 26일 보고서 이후 24시간 동안 응답 컨벤션 관련 코드 변경이 **없음을 확인**했다 (`git log --since`로 직접 검증하지는 않았으나 ripgrep 패턴 카운트·파일 라인 수가 26일 보고서 수치와 일치).

- envelope 사용 116회 (`serverless/views.py`) 동일
- `sec_pipeline/views.py` 정수 하드코딩 3건 미수정
- `serverless/views.py:2879` 정수 하드코딩 1건 미수정
- DRF 페이지네이션 도입 0건 (변화 없음)

→ 26일 보고서의 권고사항 1·2·3·4·6은 **여전히 미해결**.

---

## 부록: 카운트 출력 원본

```
['\"]error['\"]\s*:                                    → 16개 파일 195건
['\"]detail['\"]\s*:                                   → 2개 파일 3건
['\"]message['\"]\s*:                                  → 10개 파일 112건
['\"]success['\"]\s*:\s*True                           → 4개 파일 18건 (double-quoted)
'success'\s*:\s*True                                   → 6개 파일 81건 (single-quoted)
status\s*=\s*status\.HTTP_                             → 16개 파일 248건
status\s*=\s*\d{3}                                     → 4건 (sec_pipeline 3, serverless 1)
HTTP_201_CREATED                                       → 14건 (4개 파일)
HTTP_204_NO_CONTENT                                    → 8건 (3개 파일)
PageNumberPagination|CursorPagination|                 → 0건
LimitOffsetPagination|pagination_class
Paginator(                                             → 2개 파일 (users 2, rag_analysis 1)
generics.\w+ (ListAPIView 등)                          → 1건 (stocks/views.py:75)
JsonResponse (views*.py 한정)                          → 2건 (config/views.py)
raise ValidationError({...})                           → news/api/views.py 9건
DEFAULT_PAGINATION_CLASS in settings                   → 0건
```
