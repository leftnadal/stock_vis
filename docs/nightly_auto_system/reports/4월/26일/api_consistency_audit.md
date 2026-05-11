# API 응답 일관성 감사 보고서

- 감사일: 2026-04-27
- 범위: Django REST 백엔드 24개 views 파일 (`thesis/views/*.py` 3개 포함, `metrics/views.py`·`graph_analysis/views.py`·`chainsight/views.py`·`validation/views.py`·`news/views.py` 5개는 빈 파일이라 분석 제외)
- 총 라인 수: 약 13,283 라인 + thesis 3개 파일 (1,200 라인) ≈ 14,500 라인
- 방법: ripgrep 패턴 카운트 + 파일별 샘플 라인 검증
- **본 보고서는 코드 변경 없는 읽기 전용 감사 결과입니다**

---

## 요약

이 백엔드는 **단일 응답 컨벤션이 존재하지 않으며**, 앱·모듈마다 6가지 이상의 응답 형식이 혼재한다. 특히 `serverless/views.py`(116회 `success` 사용)·`rag_analysis/views.py`(헬퍼 함수 `create_success_response`)·`stocks/views_fundamentals|exchange|screener`는 `{success, data, meta}` 봉투 패턴을 채택했으나, 그 외 다수 앱(`stocks/views.py`, `users/views.py`, `macro/`, `thesis/`, `chainsight/`, `validation/`, `news/api/`, `serverless/views_admin.py`)은 직접 데이터 또는 임시 키 dict를 반환한다.

| 영역 | 핵심 발견 | 심각도 |
|------|----------|--------|
| 응답 래핑 | 6개 패턴 혼재(envelope / 직접 serializer / 임시 dict / `JsonResponse` / DRF 기본 / Pagination dict) | **CRITICAL** |
| HTTP 상태코드 | `status.HTTP_*` 248회 사용 vs 하드코딩 숫자 4회 (`sec_pipeline/views.py`, `serverless/views.py:2879`) | **MEDIUM** |
| POST 생성 시 201 | 5개 파일에서만 `HTTP_201_CREATED` 사용 — `news/api/`·`stocks/*`·`thesis/*`·`chainsight/`·`validation/`·`macro/`·`sec_pipeline/`은 POST에도 200 반환 | **HIGH** |
| 에러 형식 | `'error'`/`'detail'`/`'message'` + 중첩 `{error: {code, message}}` 4가지 혼재 (227회) | **CRITICAL** |
| 페이지네이션 | DRF `PageNumberPagination`/`CursorPagination`/`LimitOffsetPagination` **사용 0건**, `REST_FRAMEWORK` 설정에 `DEFAULT_PAGINATION_CLASS` **미설정** | **CRITICAL** |
| `Paginator` 수동 사용 | 3곳(`users/views.py:602,822`, `rag_analysis/views.py:796`)만 명시적 페이지네이션 | **HIGH** |
| `.all()` 무한정 반환 | `stocks/views.py:85` (StockListAPIView), `macro/*` 등 다수 | **HIGH** |
| 하드코딩 슬라이스 | `[:7]`, `[:12]`, `[:20]`, `[:50]` 등 파라미터 없는 고정 슬라이스 다수 | **MEDIUM** |

---

## 앱별 응답 패턴 매트릭스

> 약어
> - **A** = `{success: bool, data: ..., meta?: ...}` 봉투(envelope)
> - **B** = 직접 `Response(serializer.data)` 또는 직접 dict (DRF 기본 스타일)
> - **C** = 임시 키 dict (`{count, results}`, `{symbol, tab, data}` 등)
> - **D** = `JsonResponse()` (REST `Response` 사용 안 함)

| 앱 / 파일 | 라인 | 주 패턴 | `success` 사용 | 에러 키 분포 | 비고·근거 라인 |
|----------|-----:|--------|---------------:|-------------|---------------|
| `stocks/views.py` | 1020 | **B+C 혼재** | 2 | `error`(16) | L142 `Response(serializer.data)`, L199-202 `{results, count}`, L514-518 `{symbol, tab, data}`, L587-595 중첩 `{error:{code,message,details}}` (1건만 outlier) |
| `stocks/views_screener.py` | 498 | **A** ✅ | 8 | `error`(9) | L94-106·150-157 일관된 `{success, data, meta}` |
| `stocks/views_market_movers.py` | 69 | **B** | 0 | `error`(1) | L69 `Response(serializer.data)`, L59 dict에 `last_updated` 추가 |
| `stocks/views_eod.py` | 136 | **C** | 0 | `error`(3) | L48·102-107 임시 dict (`stocks`, `logs` 키) |
| `stocks/views_indicators.py` | 372 | **C** | 0 | `error`(3) | L249 `{symbol, period, indicators, composite_signal}` |
| `stocks/views_search.py` | 229 | **C** | 0 | `error`(5) | L75-77 `{count, results}`, L124-132 `{valid, ...}` |
| `stocks/views_fundamentals.py` | 305 | **A** ✅ | (포함됨) | `error`(6) | 모든 엔드포인트 `{success, data, meta}` |
| `stocks/views_exchange.py` | 295 | **A** ✅ | (포함됨) | `error`(6) | L68-75 외 5엔드포인트 동일 |
| `stocks/views_mvp.py` | 200 | **C** | 0 | 없음 | L62-66 `{mode, count, data}`, 에러는 `get_object_or_404`로만 |
| `users/views.py` | 1080 | **B+C 혼재** | 0 | `error`+`detail`+`message`(10) | L52·92 직접 serializer; L208 `{message: '...'}`, L215-218 `{message, stock}`; `Paginator` 수동 사용(L602, 822) |
| `serverless/views.py` | 3405 | **A** ✅ | 116 | 중첩 `{error:{code,message}}`(96) | L90-98·154-156 envelope 일관, L71-76 에러 객체화. 하드코딩 `status=400` 1건(L2879) |
| `serverless/views_admin.py` | 694 | **B+C 혼재** | 1 | `error`(29) + `{success:False, error:{code,message}}` 혼용(L401-408) | L323 `{actions}`, L478 `.all()`, 같은 모듈인데 `views.py`와 다른 패턴 |
| `news/api/views.py` | 2183 | **B+C 혼재** | 0 | `ValidationError`/`error`(10) | L94-99·277-281 임시 키 dict, `ValidationError` 자동 400 의존 |
| `news/views.py` | 3 | **빈 파일** | — | — | placeholder |
| `macro/views.py` | 410 | **B** | 0 | `error`(25) | 모두 `Response(serializer.data)` 직접, `{error: '...'}` 단순 형식 일관 |
| `config/views.py` | 104 | **D** | 0 | `error`(2) | L19·77 `JsonResponse(...)` 사용 — REST `Response` 미사용 |
| `chainsight/api/views.py` | 804 | **B** | 0 | `error`(5) | L67·113·188 직접 dict, 일부 `_sanitize_neo4j` 통과; SignalFeedView만 수동 페이지네이션 |
| `chainsight/views.py` | 1 | **빈 파일** | — | — | — |
| `thesis/views/thesis_views.py` | (≈300) | **B** | 0 | `error`(2) | L70·77 `{error}` 직접 dict, L143 `{status: 'closed', thesis_id}` |
| `thesis/views/conversation_views.py` | (≈220) | **B** | 0 | `error`(2) | L201 `[:12]` 하드코딩 슬라이스, L211 `{issues: ...}` |
| `thesis/views/monitoring_views.py` | (≈300) | **B** | 0 | 거의 없음 | L238 `[:50]` 하드코딩, L257 `{status: 'read'}` 임시 dict |
| `validation/api/views.py` | 558 | **B+C 혼재** | 0 | `error`+`{symbol, error}`(19) | L59·180·324 `{error}`; L463 401 명시 |
| `validation/views.py` | 1 | **빈 파일** | — | — | — |
| `rag_analysis/views.py` | 864 | **A** ✅ | 0 (헬퍼로 추상화) | `{error:{code,message}}`(3) | L33-43 `create_success_response`, L46-59 `create_error_response` 표준 헬퍼; `meta`에 `request_id`+`timestamp` 자동 부여 |
| `sec_pipeline/views.py` | 46 | **B (status 하드코딩)** | 0 | 없음 | L40 `status=202`, L44·46 `status=200` — `status.HTTP_*` 미사용 |
| `metrics/views.py` | 3 | **빈 파일** | — | — | — |
| `graph_analysis/views.py` | 3 | **빈 파일** | — | — | — |

**관찰 1.** `serverless/views.py`(116회) 와 `serverless/views_admin.py`(1회) 는 **같은 앱이면서도 응답 컨벤션이 정반대**다. 프론트엔드는 동일 prefix(`/api/v1/serverless/*`)에서 두 가지 형식을 분기 처리해야 한다.

**관찰 2.** A 패턴(envelope)을 명시적으로 구현한 것은 ① `serverless/views.py`(116회 인라인), ② `rag_analysis/views.py`(헬퍼 추상화), ③ `stocks/views_fundamentals|exchange|screener`(인라인). 그 외 17개 파일은 모두 B/C 패턴.

**관찰 3.** `meta` 필드는 `rag_analysis`만 `request_id` + `timestamp`를 자동 채운다. 다른 envelope 사용 파일들은 `meta`에 페이지네이션 정보 또는 캐시 힌트를 넣지만 형식이 다르다.

---

## HTTP 상태 코드 일관성

### 통계

| 항목 | 카운트 | 비고 |
|-----|------:|------|
| `status.HTTP_*` 상수 사용 | **248회** (16개 파일) | 표준 |
| 하드코딩 숫자 (`status=200/202/400`) | **4회** | `sec_pipeline/views.py:40,44,46`, `serverless/views.py:2879` |
| `status.HTTP_201_CREATED` | **14회** (5개 파일) | `users`(5), `rag_analysis`(4), `serverless`(3), `serverless_admin`(1), 조건부(`serverless`,`users` L910/1032) |
| `status.HTTP_204_NO_CONTENT` | **8회** (3개 파일) | `users`(4), `rag_analysis`(3), `serverless_admin`(1) |

### 201/204 누락 의심 파일 (POST/DELETE를 가지면서 201/204를 한 번도 사용하지 않는 파일)

| 파일 | 문제 | 영향 |
|------|------|------|
| `news/api/views.py` | POST/DELETE 다수 존재하지만 201·204 미사용 | 클라이언트가 모든 성공=200으로 가정 |
| `thesis/views/thesis_views.py` | 가설 생성 후 200 반환 | REST 시맨틱 위반 |
| `thesis/views/conversation_views.py` | 대화 생성/메시지 추가 시 200 | 동일 |
| `chainsight/api/views.py` | 시그널 생성 등 POST에 201 없음 | 동일 |
| `validation/api/views.py` | Preset 생성에 201 없음 | 동일 |
| `macro/views.py` | DataSyncView POST → 200 (L379) | 동일 |
| `sec_pipeline/views.py` | 202(처리 중) 의도는 의미 있지만 하드코딩 숫자 사용 | 표준 위반 |

### 이상치 (Outlier)

- **`sec_pipeline/views.py:40, 44, 46`**: `status=202`, `status=200` 정수 하드코딩. `from rest_framework import status`도 import 안 함.
- **`serverless/views.py:2879`**: `}, status=400)` 한 곳만 하드코딩 (다른 96곳은 모두 `status.HTTP_*`).
- **`stocks/views_indicators.py`**: 캐시 hit 경로(L39, L215)에서 `status` 미명시 → 암묵적 200. 내부 헬퍼와 명시 응답 간 일관성 부재.
- **`stocks/views.py:986`**: 동일 엔드포인트에서 success/partial-failure 모두 200 반환. 207(Multi-Status) 또는 별도 코드 도입 검토 여지.
- **`config/views.py`**: `JsonResponse`만 사용, status 코드 명시 없음(implicit 200). 헬스체크인데 DB 실패에도 200 반환 가능.

---

## 에러 응답 형식

### 키 분포 (227회 매칭)

| 키 패턴 | 발견 위치 | 빈도 |
|--------|----------|-----:|
| `{'error': '<문자열>'}` | `stocks/*`, `users/`, `macro/`, `thesis/*`, `chainsight/api/`, `validation/api/`, `serverless/views_admin.py` | 가장 많음 |
| `{'success': False, 'error': {'code': '...', 'message': '...'}}` | `serverless/views.py`(96곳), `rag_analysis/views.py`(헬퍼), `stocks/views.py:587-595`(1건) | ~100 |
| `{'detail': '...'}` | DRF 기본 예외(`ValidationError`, `NotFound`, `PermissionDenied` 등 자동 생성) | 다수(자동) |
| `{'message': '...'}` | `users/views.py:208,214`, `serverless/views.py` 일부, `sec_pipeline/views.py:39` | ~10 |
| `{'symbol': ..., 'error': ...}` | `validation/api/views.py` | 다수 |
| `Django ValidationError({...})` | `news/api/views.py:236, 308, 535` | DRF 자동 변환 의존 |

### 형식 불일치 사례

1. **`stocks/views.py`의 단일 outlier (L587-595, L920-927)**
   - 다른 16개 `error` 사용 위치는 모두 `{'error': 'string'}` 단순형
   - 단 두 곳만 `{'error': {'code': 'X', 'message': 'Y', 'details': {...}}}` 중첩
   - → 클라이언트가 `error`가 string인지 object인지 type-narrowing 해야 함

2. **`users/views.py` 내부 혼재**
   - L166: `{'error': 'Wrong username or password'}`
   - L208: `{'message': 'This stock is already in your favorites'}`
   - L214-218: `{'message': '...', 'stock': {...}}` (성공 응답인데 `message` 키 사용)
   - DRF `NotFound` 자동 발생: `{'detail': '...'}`

3. **`serverless/views.py` ↔ `serverless/views_admin.py` 불일치**
   - `views.py`: `{'success': False, 'error': {'code': 'NOT_FOUND', 'message': '...'}}`(L71-76)
   - `views_admin.py:163, 182, 333`: `{'error': '...'}` 단순형 — 일부(L401-408)만 `success=False` 형식 따름

4. **DRF 기본 예외 vs 커스텀 응답 충돌**
   - `news/api/views.py:236`: `raise ValidationError({'symbol': 'required'})` → DRF가 `{'symbol': ['required']}` 으로 변환(필드 키 구조)
   - 같은 앱 다른 액션에서는 `Response({'error': '...'}, status=400)` 직접 반환
   - → 같은 도메인에서 4xx 에러 페이로드 형식이 두 가지

5. **`config/views.py` 헬스체크의 두 가지 형식**
   - L19: 복잡한 nested endpoints dict
   - L77: `{'status': '...', 'database': '...', 'cache': '...'}` flat
   - 같은 파일·같은 헬스 도메인인데 형식 다름

---

## 페이지네이션 현황

### DRF 표준 페이지네이션 사용 현황

```
DEFAULT_PAGINATION_CLASS in REST_FRAMEWORK settings: ❌ 미설정 (config/settings.py:321-329)
PageNumberPagination 사용:                         ❌ 0회
CursorPagination 사용:                             ❌ 0회
LimitOffsetPagination 사용:                        ❌ 0회
pagination_class 속성 설정:                        ❌ 0회 (모든 ListAPIView에서)
```

### `generics.ListAPIView` 사용 현황

`generics.ListAPIView`/`ListCreateAPIView`/`generics.*` 사용은 **`stocks/views.py:75 StockListAPIView` 단 1곳**. 그러나 `pagination_class`가 지정되지 않았고 `REST_FRAMEWORK`에도 `DEFAULT_PAGINATION_CLASS`가 없어 **결과적으로 `Stock.objects.all()` 전체를 반환**한다(L85).

### 수동 페이지네이션 (Django Paginator 직접 사용)

| 파일·라인 | 패턴 | 응답 형식 |
|----------|------|----------|
| `users/views.py:602` (WatchlistListCreateView) | `Paginator(watchlists, page_size)` | L610-620 `{'results': ..., 'pagination': {...}}` |
| `users/views.py:822` (WatchlistStocksView) | `Paginator(items, page_size)` | 동일 |
| `rag_analysis/views.py:796` (UsageHistoryView) | `Paginator(logs, page_size)` (max 100) | L818-824 `{'results', 'page', 'page_size', 'total', 'total_pages', 'has_next', 'has_previous'}` |

### 수동 offset/limit (Paginator 미사용)

| 파일·라인 | 응답 키 |
|----------|--------|
| `serverless/views.py:1171-1184` (execute_preset) | `{results, count, total_pages, current_page, next, previous}` (L1351-1358) |
| `serverless/views.py:1309-1358` (advanced_screener_api) | 동일 |
| `news/api/views.py:368-433` (all_news) | `{count, articles, has_more}` 커스텀 |
| `chainsight/api/views.py:623-805` (SignalFeedView) | `page`/`page_size` 입력, `has_next` 응답 |
| `chainsight/api/views.py:445` (NeighborGraphView) | `limit` 파라미터(max 30), 페이지네이션 메타 없음 |
| `stocks/views_screener.py:127, 260-262` | `limit`(1~1000) 파라미터, 메타 없음 |
| `stocks/views_fundamentals.py:64-65, 123-124` | `limit`(1~40) 파라미터 |
| `stocks/views_exchange.py:150` | `limit`(1~100) |
| `stocks/views_market_movers.py:47` | `limit`(1~20) |

→ **각자 다른 응답 키**: `count` vs `total`, `current_page` vs `page`, `has_more` vs `has_next` 등.

### 하드코딩 슬라이스 (파라미터 없음)

| 파일·라인 | 슬라이스 | 영향 |
|----------|----------|------|
| `stocks/views_search.py:56` | `[:10]` | 검색 결과 10개 고정 |
| `stocks/views_eod.py:119` | `[:7]` | 7일 고정 |
| `stocks/views_indicators.py:64` | `.values(...).order_by(...)` 미슬라이스 | 모든 가격 반환 |
| `stocks/views_mvp.py:41` | `[:20]` | 20개 고정 |
| `news/api/views.py:274` | `[:limit]` (limit 입력 받음) | OK |
| `news/api/views.py:336` | `[:3]` | 3개 고정 |
| `thesis/views/conversation_views.py:201` | `[:12]` | 12개 고정 |
| `thesis/views/monitoring_views.py:238` | `[:50]` | 50개 고정 |

### 무한정 `.all()` 또는 `.filter()` 반환

| 파일·라인 | 모델 | 위험 |
|----------|------|------|
| `stocks/views.py:75-85` (StockListAPIView) | `Stock` | 전체 종목 반환(수만 건 가능) |
| `stocks/views_indicators.py:64` | `DailyPrice` 무한정 | 한 종목 모든 일자 반환 |
| `serverless/views_admin.py:478` | 카테고리 전체 | 무한정 |
| `serverless/views_admin.py:671-683` | 태스크 로그 `limit` 있으나 메타 없음 | 부분적 |
| `macro/views.py` 전체 | 모든 GET 무페이지네이션 | 거시 데이터 양에 따라 위험 |
| `validation/api/views.py:LeaderComparisonView` | 비교 결과 전체 반환 | 사이즈 종속 |

### 핵심 문제

**모든 list 엔드포인트가 자체 페이지네이션 규약을 따로 만든다**. 동일 클라이언트가 5종 이상의 응답 형식을 분기해야 하며, `count`·`total`·`results`·`articles` 등 응답 키가 통일되지 않는다.

---

## 권고사항

> **본 보고서는 감사 결과만 기록하며, 변경은 별도 PR/계획 단계에서 결정한다.**

### 즉시 검토(Critical)

1. **공통 응답 envelope 결정**
   - 옵션 A: `{success, data, meta}` envelope을 모든 엔드포인트에 강제
   - 옵션 B: DRF 기본(직접 `serializer.data`) + DRF Exception Handler 표준화
   - 현재 `serverless/`(envelope) ↔ 그 외(직접 dict)의 분기 구조는 **프론트엔드가 두 형식을 모두 처리해야 함**
   - 단일 결정 후 `contracts/` 스펙에 명시 필요

2. **에러 응답 형식 통일**
   - `{'error': string}` (단순) vs `{'error': {code, message}}` (객체) 중 택일
   - DRF `ValidationError`/`NotFound` 자동 응답과 충돌하지 않는 방향 권장
   - DRF custom `EXCEPTION_HANDLER` 도입 검토 → 미들웨어로 일괄 변환

3. **DRF 페이지네이션 표준 도입**
   - `config/settings.py`의 `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS`·`PAGE_SIZE` 추가
   - 모든 `ListAPIView`·`@api_view` list 엔드포인트가 자동 페이지네이션 받도록
   - 기존 수동 envelope 사용 엔드포인트는 호환성 어댑터 작성

### 단기 개선(High)

4. **`sec_pipeline/views.py` 하드코딩 status 정리**
   - L40·44·46: `status=200` → `status=status.HTTP_200_OK`
   - `from rest_framework import status` 추가

5. **POST 생성 엔드포인트 201 강제**
   - `news/api/`, `thesis/`, `chainsight/api/`, `validation/api/`, `macro/DataSyncView`에서 POST 응답 시 `HTTP_201_CREATED` 검토

6. **`serverless/views.py` ↔ `serverless/views_admin.py` 컨벤션 일치**
   - 같은 앱 내부에서만이라도 envelope 패턴 통일

### 중기 개선(Medium)

7. **하드코딩 슬라이스 → `limit` 파라미터화**
   - `[:7]`, `[:12]`, `[:20]`, `[:50]` 등을 query param으로 노출

8. **`StockListAPIView`·`macro/*` 무한정 반환 차단**
   - `max_page_size`·`default_page_size` 강제
   - 로드 테스트로 응답 페이로드 크기 측정 후 한계 결정

9. **`config/views.py` 헬스체크 응답 표준화**
   - DB/캐시 실패 시 503 반환 검토(현재는 모두 200)
   - `JsonResponse` → DRF `Response` 통일 검토

10. **`rag_analysis/create_success_response` 헬퍼를 공용화**
    - `meta.request_id`·`meta.timestamp` 자동 부여 패턴은 좋은 출발점
    - `common/responses.py` 등에 두고 다른 앱이 재사용

### 메타·검증

11. **`contracts/` OpenAPI 스펙과 실 응답 대조**
    - 현재 envelope/non-envelope 혼재 상태가 contracts에 어떻게 기술되어 있는지 별도 감사 필요
    - 본 감사에서는 contracts 비교를 수행하지 않음

12. **테스트 추가 영역**
    - 응답 형식 회귀 테스트(스냅샷): 파일별 대표 엔드포인트의 응답 키 set 비교
    - DRF 표준 도입 시 backward-compat 검증 필수

---

## 부록: 카운트 출력 원본

```
'error':|'detail':|'message':                 → 14개 파일 227건
'success': True|'success': False              → 3개 파일 119건
status.HTTP_*                                  → 16개 파일 248건
status=<digit>                                 → 4건 (sec_pipeline 3, serverless 1)
HTTP_201_CREATED                               → 14건 (5개 파일)
HTTP_204_NO_CONTENT                            → 8건 (3개 파일)
PageNumberPagination|CursorPagination|         → 0건
LimitOffsetPagination|pagination_class
Paginator(                                     → 3건 (users 2, rag_analysis 1)
generics.ListAPIView                            → 1건 (stocks/views.py:75)
JsonResponse                                    → 2건 (config/views.py)
DEFAULT_PAGINATION_CLASS in settings           → 0건
```
