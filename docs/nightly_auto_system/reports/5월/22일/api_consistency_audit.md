# API 응답 일관성 감사 보고서

생성일: 2026-05-22
대상: /Users/byeongjinjeong/Desktop/stock_vis
스캔 파일 수: 26개 (빈 stub 5개 제외 실질 분석 21개)

---

## 요약

- **래핑 패턴 혼재 (Critical)**: `{'success': True, 'data': ...}` 형식과 직접(flat) 반환이 같은 프로젝트에 공존하며, 심지어 **같은 앱(stocks) 내부**에서도 혼재. 프론트엔드가 응답 형식을 분기 처리해야 하는 부채를 유발함.
- **에러 키 비일관성 (High)**: `{'error': ...}`, `{'detail': ...}`, `{'errors': ...}`, `{'error': {'code':..., 'message':...}}` 네 가지 형태가 혼재. 특히 중첩 구조(`error.code`) vs 평탄 문자열 혼용이 심각.
- **POST 201/200 혼용 (High)**: 생성(Create) endpoint에서 `status.HTTP_201_CREATED` 와 `status.HTTP_200_OK` 가 일관 없이 사용됨. `validation/api/views.py`의 `PeerPreferenceView.post`는 상태코드 미지정(기본 200).
- **전역 페이지네이션 미설정 (High)**: `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS`가 없음(audit P0 #14 미처리). 목록 endpoint 다수가 쿼리셋 전체를 무제한 반환하며 OOM 위험이 있음.
- **숫자 리터럴 status 코드 혼재 (Medium)**: `sec_pipeline/views.py`에서 `status=200`, `status=202` 숫자 리터럴을 직접 사용. 대부분의 앱은 `status.HTTP_*` 상수를 사용하여 불일치.

---

## 앱별 응답 패턴 매트릭스

| 앱 | 래핑 패턴 | 에러 키 형태 | 페이지네이션 | status 상수 사용 | 비고 |
|----|----------|------------|------------|----------------|------|
| stocks/views.py | **혼재** | `error` (flat/중첩 혼재) | 부분 (StockListPagination 클래스 정의) | 거의 전체 | StockSearchAPIView는 `result`/`results` 키 오타 혼재 |
| stocks/views_fundamentals.py | `success+data+meta` | `error` (flat) | 미적용 | 전체 | 가장 일관된 패턴 사용 |
| stocks/views_indicators.py | **직접(flat)** | `error` (flat) | 미적용 | 전체 | Response(indicators_data) 직접 반환 |
| stocks/views_market_movers.py | **직접(flat)** | `error` (flat) | 미적용 | 전체 | serializer.data 직접 반환 |
| stocks/views_screener.py | `success+data+meta` | `error` (flat) | 미적용 | 전체 | Enhanced 경로와 기존 경로 모두 동일 형식 |
| stocks/views_search.py | **직접(flat)** | `error` (flat/503) | 미적용 | 전체 | `{'count', 'results'}` 직접 반환 |
| stocks/views_eod.py | **혼재** | `error` (flat, 영문) | `:50` 슬라이싱 | 전체 | EODDashboardView는 `snapshot.json_data` 직접 반환 (래핑 없음) |
| stocks/views_exchange.py | `success+data+meta` | `error` (flat) | 미적용 | 전체 | |
| stocks/views_mvp.py | `{'mode', 'count', 'data'}` | 없음 | `:20` 슬라이싱 | 전체 | 커스텀 래퍼, auth 없음 |
| users/views.py | **혼재** | `error`/`errors`(serializer)/`ok` | Paginator 수동 | 전체 | `{'ok': '...'}` 독자 성공 키 |
| macro/views.py | **직접(flat)** | `error` (flat, 영문) | 미적용 | 전체 | serializer.data 직접 반환 |
| news/views.py | **직접(flat)** | `error` + ValidationError | NewsArticlePagination 적용 | 전체 | ViewSet, 대부분 커스텀 action dict 반환 |
| rag_analysis/views.py | **혼재** | DRF 예외 + 커스텀 | Paginator 수동 | 전체 | 직접 반환과 래핑 혼재; SSE 스트리밍 별도 |
| serverless/views.py | **직접(flat)** | NotFound/ValidationError DRF 예외 | 미적용 | 전체 | `api_view` 데코레이터 함수 뷰 |
| serverless/views_admin.py | - | `error` | 미적용 | 전체 | 관리자 전용 |
| validation/api/views.py | **직접(flat)** | `error` (flat, 한국어/영어 혼재) | 미적용 | 전체 | |
| chainsight/api/views.py | **직접(flat)** | `error` (flat) | `:50` 슬라이싱 | 전체 | `_sanitize_neo4j()` 래핑 후 직접 반환 |
| sec_pipeline/views.py | **직접(flat)** | 없음 | 미적용 | **숫자 리터럴** | `status=200`, `status=202` 숫자 하드코딩 |
| portfolio/api/views.py | **직접(flat)** | `error` (flat, 영문) | 미적용 | 전체 | `resp_serializer.data` 직접 반환 |
| config/views.py | **직접(flat)** | 없음 | 미적용 | 전체 | health_check/api_root 유틸 뷰 |
| graph_analysis/views.py | - | - | - | - | stub (빈 파일) |
| metrics/views.py | - | - | - | - | stub (빈 파일) |
| validation/views.py | - | - | - | - | stub (빈 파일) |
| chainsight/views.py | - | - | - | - | stub (빈 파일) |
| news/views.py | - | - | - | - | stub (빈 파일) |
| portfolio/views.py | - | - | - | - | 역사적 보존 stub |

---

## HTTP 상태 코드 일관성

### POST(생성) 시 201 vs 200 사용 현황

| 파일 | 위치 | 반환 코드 | 평가 |
|------|------|----------|------|
| users/views.py:107 | `Users.post` (회원가입) | `HTTP_201_CREATED` | 올바름 |
| users/views.py:639 | `WatchlistListCreateView.post` | `HTTP_201_CREATED` | 올바름 |
| users/views.py:731 | `WatchlistItemAddView.post` | `HTTP_201_CREATED` | 올바름 |
| users/views.py:918 | `WatchlistBulkAddView.post` | `HTTP_201_CREATED` (added 있을 때) / `HTTP_200_OK` | 혼재, 조건부 상태코드 |
| users/views.py:1040 | `UserInterestListCreateView.post` | `HTTP_201_CREATED` (created 있을 때) / `HTTP_200_OK` | 혼재, 조건부 상태코드 |
| rag_analysis/views.py:63 | `DataBasketListCreateView.post` | `HTTP_201_CREATED` | 올바름 |
| rag_analysis/views.py:396 | `AnalysisSessionListCreateView.post` | `HTTP_201_CREATED` | 올바름 |
| stocks/views.py:996 | `StockSyncAPIView.post` (sync) | `HTTP_200_OK` | sync는 생성이 아니므로 수용 |
| validation/api/views.py:487 | `PeerPreferenceView.post` | **코드 미지정 (기본 200)** | 문제 — 명시 필요 |
| portfolio/api/views.py:98 | `coach_e1` | `HTTP_200_OK` | LLM 응답이므로 수용 가능 |

### status 상수 vs 숫자 리터럴

- **숫자 리터럴 직접 사용 (문제)**: `sec_pipeline/views.py:47` — `status=202`, `status=200`
- **`status.HTTP_*` 상수 사용**: 나머지 21개 파일 전체 (올바름)
- **status 생략 (기본 200)**: `stocks/views_indicators.py:197` `return Response(indicators_data)` 등 다수 — 의도는 명확하나 가독성 저하

### status 생략 사례 목록 (주요)

```
stocks/views_indicators.py:197  — return Response(indicators_data)
stocks/views_indicators.py:261  — return Response(signal_data)
stocks/views_indicators.py:372  — return Response(comparison_data)
stocks/views_market_movers.py:69 — return Response(serializer.data)
macro/views.py:46               — return Response(serializer.data)
macro/views.py:66               — return Response(serializer.data) (여러 곳)
chainsight/api/views.py:181     — return Response({...}) 여러 곳
news/api/views.py (ViewSet action 다수) — return Response(data)
```

---

## 에러 응답 형식

### 에러 키 분포 (앱별)

| 앱 | `error` (flat str) | `error` (중첩 dict) | `errors` (serializer) | `detail` (DRF) | `ok` | `valid`/기타 |
|----|-------------------|--------------------|-----------------------|---------------|------|------------|
| stocks/views.py | 다수 | StockSyncAPIView (rate_limit), StockOverviewAPIView | - | - | - | - |
| stocks/views_fundamentals.py | 5곳 | - | - | - | - | - |
| stocks/views_indicators.py | 2곳 | - | - | - | - | - |
| stocks/views_exchange.py | 4곳 | - | - | - | - | - |
| stocks/views_screener.py | 4곳 | - | - | - | - | - |
| stocks/views_search.py | 3곳 | - | - | - | `valid: False` | |
| users/views.py | 5곳 | - | serializer.errors 다수 | DRF NotFound 예외 | `ok` (로그인 성공) | |
| validation/api/views.py | 8곳 | - | - | - | - | - |
| chainsight/api/views.py | 4곳 | - | - | - | - | - |
| portfolio/api/views.py | 5곳 | - | - | - | - | `scope` (budget 에러) |
| macro/views.py | 다수 | - | - | - | - | - |

### 중첩 에러 구조 사례 (불일치)

**`stocks/views.py:597-605`** — `StockOverviewAPIView` 500 에러:
```python
return Response({
    'error': {
        'code': 'OVERVIEW_ERROR',
        'message': '...',
        'details': {'symbol': ..., 'original_error': ..., 'can_retry': True}
    }
}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

**`stocks/views.py:929-938`** — `StockSyncAPIView` 429 에러:
```python
return Response({
    'error': {
        'code': 'RATE_LIMIT_EXCEEDED',
        'message': '...',
        'details': {'usage': ..., 'can_retry': True}
    }
}, status=status.HTTP_429_TOO_MANY_REQUESTS)
```

같은 파일(`stocks/views.py`)의 다른 뷰(`StockBalanceSheetAPIView:679`)는:
```python
return Response({
    'error': f'대차대조표 데이터 조회 중 오류가 발생했습니다: {str(e)}'
}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

**동일 앱 내 500 에러 형식이 두 가지로 분기됨.**

### 성공 응답 키 오타: `stocks/views.py`

`StockSearchAPIView.get` 내부:
- L182: 검색어 없을 때 → `'result': []` (단수)
- L193: 검색어 짧을 때 → `'results': []` (복수)

동일 endpoint의 에러 응답에서 **같은 키가 `result` / `results`로 다름** — 프론트엔드 버그 유발 가능성.

### 에러 메시지 언어 혼재

| 앱 | 한국어 에러 메시지 사례 | 영문 에러 메시지 사례 |
|----|----------------------|-------------------|
| stocks/* | `'대차대조표 데이터 조회 중 오류...'` | `'No price data available for {symbol}'` (indicators) |
| users/views.py | `"'{stock.symbol}' stock is already in this watchlist"` (한영혼재 f-string) | `"Stock not found in your portfolio"` |
| validation/api/views.py | `'현재 S&P 500 종목만 지원합니다.'`, `'비교 대상 부족'` | `'Stock {symbol} not found'` |
| chainsight/api/views.py | `"from, to 파라미터 필수"` | `"Stock {symbol} not found in graph"` |
| macro/views.py | `'Failed to fetch market pulse data'` | 전부 영문 |
| portfolio/api/views.py | `"Internal server error"` | 전부 영문 |

**결론**: 한국어/영문이 앱 간 기준 없이 혼재. 특히 `users/views.py:715`의 f-string `"'{stock.symbol}' stock is already in this watchlist"` 는 한글 따옴표 `'` 와 영문이 섞인 이상한 형태.

---

## 페이지네이션 현황

### 전역 설정 검증

`config/settings.py`의 `REST_FRAMEWORK` 딕셔너리에 아래 두 키가 **존재하지 않음**:

```python
# 없음:
'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
'PAGE_SIZE': 50,
```

주석으로 `audit P0 #14 (페이지네이션 표준)는 별도 PR에서 처리 — 응답 envelope 결정이 선결 조건` 이라고 명시되어 있어 의도적으로 미처리 상태.

### 페이지네이션이 적용된 endpoint 목록

| 파일 | 클래스/함수 | 페이지네이션 방식 | 비고 |
|------|-----------|----------------|------|
| stocks/views.py | `StockListAPIView` | `StockListPagination` (page_size=50, max=200) | ListAPIView 자동 적용 |
| news/api/views.py | `NewsViewSet` | `NewsArticlePagination` (page_size=20, max=100) | ViewSet 자동 적용 |
| users/views.py | `WatchlistListCreateView.get` | `django.core.paginator.Paginator` (수동, max=100) | 커스텀 `pagination` 키로 래핑 |
| users/views.py | `WatchlistStocksView.get` | `django.core.paginator.Paginator` (수동, max=100) | 커스텀 `pagination` 키로 래핑 |
| rag_analysis/views.py | `UsageHistoryView.get` | `django.core.paginator.Paginator` (수동, max=100) | 커스텀 `pagination` 키로 래핑 |

**DRF 기본 PageNumberPagination vs Django 수동 Paginator가 혼재** — 응답 키 구조가 다름:
- DRF: `{'count', 'next', 'previous', 'results'}`
- 수동: `{'results', 'pagination': {'count', 'page', 'page_size', 'num_pages', ...}}`

### 무제한 반환 위험 endpoint 목록 (OOM/응답 비대)

| 파일:라인 | View/함수 | 쿼리셋 규모 추정 | 위험도 |
|----------|---------|----------------|--------|
| `stocks/views.py:95` | `StockListAPIView.get_queryset` | `Stock.objects.all()` — S&P 500 기준 ~6,000+ 종목 → **StockListPagination으로 보호됨** | 보호됨 |
| `stocks/views_mvp.py:29` | `StockMVPListView.get` | `Stock.objects.all()[:20]` — 슬라이싱으로 제한 | 저위험 |
| `users/views.py:93` | `Users.get` (관리자 사용자 목록) | `User.objects.all()` — 무제한, 페이지네이션 없음 | **High** |
| `users/views.py:191` | `UserFavorites.get` | `user.favorite_stock.all()` — 즐겨찾기 전체 무제한 | Medium |
| `users/views.py:264` | `PortfolioListCreateView.get` | `Portfolio.objects.filter(user=...).select_related(...)` — 사용자 포트폴리오, 수백 건 가능 | Medium |
| `rag_analysis/views.py:52` | `DataBasketListCreateView.get` | `DataBasket.objects.filter(user=...).prefetch_related(...)` — 무제한 | Medium |
| `rag_analysis/views.py:378` | `AnalysisSessionListCreateView.get` | `AnalysisSession.objects.filter(user=...).prefetch_related(...)` — 무제한 | Medium |
| `rag_analysis/views.py:440` | `SessionMessagesView.get` | `session.messages.all().order_by('created_at')` — 세션 메시지 전체 무제한 | **High** (긴 대화 세션) |
| `validation/api/views.py:361-401` | `LeaderComparisonView.get` | 내부에서 `all_metrics` 전체 순회 + 다중 N+1 쿼리 | **High** (쿼리 폭발) |
| `macro/views.py` 모든 뷰 | 각 대시보드 뷰 | Service 계층에 위임 — 내부 미확인 | 추적 필요 |
| `chainsight/api/views.py:343` | `SectorGraphView.get` | `repo.run_query(... LIMIT $limit)` — LIMIT 파라미터 있음 | 보호됨 |
| `stocks/views_fundamentals.py:73` | `KeyMetricsView.get` | 외부 FMP API, `limit` 파라미터 제한 있음 | 보호됨 |

**특히 위험 사례 상세**:

```python
# users/views.py:93 — 관리자 사용자 목록, 무제한
def get(self, request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)  # 사용자 수가 수만 명이면 OOM

# rag_analysis/views.py:440 — 세션 메시지 무제한
messages = session.messages.all().order_by('created_at')
serializer = AnalysisMessageSerializer(messages, many=True)
return Response(serializer.data)  # 수백 메시지 세션이면 응답 수MB
```

---

## 권고사항

### Critical: 같은 앱 내 응답 래핑 패턴 통일

**영향 파일**: `stocks/views.py`, `stocks/views_indicators.py`, `stocks/views_eod.py`

현재 `stocks` 앱에만 최소 3가지 패턴이 공존:
1. `{'symbol': ..., 'tab': ..., 'data': {...}}` — StockOverviewAPIView
2. `{'success': True, 'data': ..., 'meta': {...}}` — views_fundamentals.py
3. `{'symbol': ..., 'period': ..., 'data': [...], 'count': ...}` — StockChartDataAPIView (flat)
4. `{'indicators': {...}, 'symbol': ..., 'dates': [...]}` — views_indicators.py (flat)

**표준 응답 형식 제안** (DECISIONS.md에 기록 필요):

```python
# 성공 (목록)
{
    "success": True,
    "data": [...],
    "meta": {"count": 10, "symbol": "AAPL", "timestamp": "..."}
}

# 성공 (단건)
{
    "success": True,
    "data": {...},
    "meta": {"symbol": "AAPL", "timestamp": "..."}
}

# 실패
{
    "success": False,  # 또는 DRF 기본 형식 사용
    "error": {
        "code": "NOT_FOUND",
        "message": "종목을 찾을 수 없습니다."
    }
}
```

---

### Critical: StockSearchAPIView 에러 키 오타 수정 필요

**파일**: `stocks/views.py:182`

```python
# 현재 (버그)
return Response({
    'result': [],       # ← 단수 (오타)
    'message': '검색어를 입력해주세요',
}, status=status.HTTP_400_BAD_REQUEST)

# 2자 미만 케이스 (정상)
return Response({
    'results': [],      # ← 복수 (다른 키)
    'message': '검색어는 2자 이상 입력해주세요.'
}, ...)
```

동일 endpoint 내에서 `result` / `results` 키가 달라 클라이언트 파싱 버그 유발.

---

### High: 전역 DEFAULT_PAGINATION_CLASS 미설정

**파일**: `config/settings.py`

`audit P0 #14` 주석이 있으나 미처리. 아래 추가 필요:

```python
REST_FRAMEWORK = {
    ...
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}
```

단, 현재 일부 뷰가 커스텀 pagination 클래스를 명시(`pagination_class = None`)하거나 Paginator를 수동으로 쓰고 있어, 전역 설정 적용 시 **기존 커스텀 pagination과 충돌** 가능. 영향 파일 사전 검토 필수.

---

### High: 무제한 반환 endpoint 페이지네이션 적용

우선순위 순서:

1. `users/views.py:93` — `Users.get` 관리자 사용자 목록 → `IsAdminUser`이므로 남용 가능성 낮으나 `[:100]` 슬라이싱 최소 적용
2. `rag_analysis/views.py:440` — `SessionMessagesView.get` → 긴 대화 세션 보호 위해 최신 50개 슬라이싱 또는 pagination
3. `rag_analysis/views.py:52` — `DataBasketListCreateView.get` → 사용자 바구니 목록 페이지네이션
4. `users/views.py:191` — `UserFavorites.get` → 즐겨찾기 목록 max 200 슬라이싱

---

### High: PeerPreferenceView POST 상태코드 명시 누락

**파일**: `validation/api/views.py:487`

```python
# 현재
return Response({'status': 'ok', 'mode': mode, 'preset_key': preset_key})
# → HTTP 200 (DRF 기본) — 의도는 200이지만 명시 필요

# 권고
return Response({'status': 'ok', ...}, status=status.HTTP_200_OK)
```

---

### High: 에러 응답 중첩 구조 통일

**파일**: `stocks/views.py`

같은 파일 내에서 500 에러 형식이 두 가지:
- `StockOverviewAPIView`: `{'error': {'code': ..., 'message': ..., 'details': {...}}}`
- `StockBalanceSheetAPIView`: `{'error': 'f-string 메시지'}`

settings.py에 이미 `EXCEPTION_HANDLER: 'config.exception_handler.custom_exception_handler'` 가 등록되어 있음. DRF 예외는 커스텀 핸들러가 처리하지만, **직접 `Response({'error': ...})`로 반환하는 경우는 미적용**. 직접 반환 패턴을 DRF 예외(`raise NotFound`, `raise ValidationError`)로 전환하거나, 헬퍼 함수로 통일 권고.

---

### Medium: sec_pipeline/views.py 숫자 리터럴 status 코드

**파일**: `sec_pipeline/views.py:47,50,51`

```python
# 현재 (문제)
return Response({...}, status=202)
return Response(result, status=200)

# 권고
from rest_framework import status
return Response({...}, status=status.HTTP_202_ACCEPTED)
return Response(result, status=status.HTTP_200_OK)
```

---

### Medium: 에러 메시지 언어 통일

현재 기준 없이 한국어/영문이 혼재. 프로젝트 방향에 따라 결정:
- **한국어 우선** (B2C 서비스): 모든 `error.message` 필드를 한국어로
- **영문 우선** (API 다국어 대응): 영문 코드 + `i18n` endpoint 별도 제공

**즉시 수정 필요한 사례** (`users/views.py:715`):
```python
# 현재 (한영 혼재 + 이상한 따옴표)
{"error": _(f"'{stock.symbol}' stock is already in this watchlist")}

# 권고 (한국어 통일)
{"error": _(f"'{stock.symbol}' 종목이 이미 이 Watchlist에 포함되어 있습니다.")}
```

---

### Low: DRF vs 수동 Paginator 방식 통일

`users/views.py`, `rag_analysis/views.py`에서 `django.core.paginator.Paginator`를 수동으로 사용하며 커스텀 `pagination` 키로 래핑. DRF `PageNumberPagination` 사용 시 `{'count', 'next', 'previous', 'results'}` 표준 키로 변경됨.

프론트엔드(`authAxios` 기반)가 현재 커스텀 `pagination` 키를 파싱하고 있다면 **마이그레이션 시 프론트엔드 동시 수정 필요**. `@frontend`와 API 계약 협의 필수.

---

## 부록: 검사 기준별 앱 요약

### 래핑 패턴 완전 일관 앱 (동일 앱 내 패턴 통일)
- `stocks/views_fundamentals.py` — `success+data+meta` 100% 일관
- `stocks/views_exchange.py` — `success+data+meta` 100% 일관
- `stocks/views_screener.py` — `success+data+meta` 100% 일관
- `portfolio/api/views.py` — `resp_serializer.data` 직접 반환 100% 일관

### 래핑 패턴 혼재 앱 (개선 우선순위 높음)
- `stocks/views.py` — flat/`symbol+tab+data`/`success+data+meta` 3가지 혼재
- `stocks/views_eod.py` — `snapshot.json_data` 직접 / `{'signal_id', 'date', 'count', 'stocks'}` / `{'logs'}` 혼재
- `users/views.py` — `{'ok'}` / serializer.data 직접 / `{'results', 'pagination'}` / `{'portfolios', 'summary'}` 혼재
- `rag_analysis/views.py` — serializer.data 직접 / `{'message', 'deleted_count'}` / stats dict / SSE 스트리밍
