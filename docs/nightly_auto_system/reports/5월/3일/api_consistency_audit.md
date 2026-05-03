# API 응답 일관성 감사 보고서

**감사 대상**: Stock-Vis Backend API (Django REST Framework)
**감사 일자**: 2026-05-04
**감사 범위**: 14개 앱, 28개 views 파일, 14,490 라인
**감사자**: Claude (read-only audit)

---

## 요약

Stock-Vis 백엔드는 **DRF + Django 순수 view 혼용** 환경에서 운영되며, 13개 앱 전반에 **5가지 서로 다른 응답 패턴**이 공존하고 있다. 클라이언트(특히 frontend/)는 앱마다 **다른 응답 구조를 처리해야 한다**.

### 핵심 발견 (Severity 순)

| # | 심각도 | 항목 | 영향 |
|---|--------|------|------|
| 1 | 🔴 Critical | **DRF 전역 페이지네이션 미설정** (`REST_FRAMEWORK` dict에 `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` 없음) | 목록 API가 전체 레코드를 반환 → OOM 위험 |
| 2 | 🔴 Critical | **응답 래핑 패턴 5종 혼재** (`{success, data}` vs raw vs `{detail}` vs JsonResponse vs DRF 기본) | 프론트엔드 분기 로직 비대화, 신규 개발자 혼란 |
| 3 | 🟠 High | **에러 키 3종 혼재** (`error` 204회 / `message` 112회 / `detail` 9회) | 클라이언트 에러 핸들러가 모든 키를 검사해야 함 |
| 4 | 🟠 High | **`generics.ListAPIView` 2곳에 `pagination_class` 미설정** | StockListAPIView, NewsViewSet이 전체 데이터 반환 |
| 5 | 🟡 Medium | **`status` 모듈 vs 하드코딩 정수 혼용** (`status=400` 15회) | 가독성/일관성 저하 (portfolio, sec_pipeline) |
| 6 | 🟡 Medium | **portfolio 앱이 DRF 미사용 (`JsonResponse`)** | 인증/권한/throttle 정책에서 격리됨 |
| 7 | 🟢 Low | **201 CREATED 미사용 view 다수** | RESTful 시멘틱 부정확 |

---

## 앱별 응답 패턴 매트릭스

### 패턴 분류

| 코드 | 패턴 | 예시 |
|------|------|------|
| **W** | Wrapped: `{"success": bool, "data": {...}, "meta": {...}}` | `serverless/views.py`, `rag_analysis/views.py` |
| **H** | Hybrid: 성공만 wrap, 에러는 raw | `stocks/views_screener.py`, `stocks/views_fundamentals.py`, `stocks/views_exchange.py` |
| **R** | Raw DRF: `serializer.data` 또는 dict 직접 반환 | `macro/`, `news/`, `validation/`, `chainsight/`, `thesis/`, `users/`, `stocks/views.py`, `stocks/views_eod.py` |
| **D** | Django JsonResponse: DRF 우회 | `portfolio/views.py` |
| **N** | DRF 기본 예외 (`raise NotFound` → `{"detail": ...}`) | `users/views.py` 일부, `rag_analysis/` 일부 |

### 매트릭스 (Response 호출 횟수 / 'success' 키 사용 횟수)

| 앱 | 파일 | Response | success 키 | error 키 | message 키 | detail 키 | 패턴 |
|----|------|----------|------------|----------|-------------|-----------|------|
| serverless | views.py | 126 | **161** | 60 | 56 | - | **W** (전체 wrap) |
| serverless | views_admin.py | 45 | 1 | 28 | 30 | - | **R** + AdminAction post 1곳만 W |
| rag_analysis | views.py | 38 | 2 (helper) | 6 | 25 | - | **W** (`create_success_response()` 헬퍼 사용) |
| stocks | views.py | 25 | **5** | 12 | 25 | - | **R** (단, search/screener 일부 W) |
| stocks | views_screener.py | 15 | **7** | 8 | 8 | - | **H** (성공만 W, 에러 R) |
| stocks | views_fundamentals.py | 15 | **5** | 10 | 10 | - | **H** |
| stocks | views_exchange.py | 13 | **5** | 8 | 8 | - | **H** |
| stocks | views_eod.py | 6 | 0 | 3 | 3 | - | **R** |
| stocks | views_indicators.py | 8 | 0 | 3 | 3 | - | **R** |
| stocks | views_search.py | 10 | 0 | 5 | 5 | - | **R** |
| stocks | views_market_movers.py | 2 | 0 | 1 | 1 | - | **R** |
| stocks | views_mvp.py | 4 | 0 | 0 | 0 | - | **R** |
| users | views.py | 56 | 0 | 8 | 33 | 2 | **R + N** (`raise NotFound`/`ParseError`) |
| portfolio | views.py | 0 (JsonResponse 11) | 0 | 9 | 0 | 6 | **D** (DRF 미사용) |
| macro | views.py | 26 | 0 | 15 | 15 | - | **R** |
| news | api/views.py | 61 | 0 | 7 | 7 | - | **R** + ViewSet |
| validation | api/views.py | 23 | 0 | 15 | 11 | - | **R** |
| chainsight | api/views.py | 20 | 0 | 9 | 8 | - | **R** |
| thesis | views/*.py | 18 | 0 | 4 | 0 | - | **R** + ViewSet |
| sec_pipeline | views.py | 3 | 0 | 0 | 1 | - | **R** (`status=200/202` 하드코딩) |
| config | views.py | 0 (JsonResponse 3) | 0 | 0 | 1 | 1 | **D** (root + health check) |
| metrics, graph_analysis, chainsight/views.py, validation/views.py, news/views.py | (빈 파일) | 0 | 0 | 0 | 0 | 0 | — |

### 결정적 불일치 사례

#### Case 1: 성공/에러 응답 형태가 같은 view 내에서 다름

`stocks/views_screener.py:60-156`
```python
# 에러 (raw)
return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# 성공 (wrapped)
return Response({
    "success": True,
    "data": {...},
    "meta": {...}
})
```
→ 클라이언트가 `response.data.results`인지 `response.data.data.stocks`인지 분기 필요.

#### Case 2: 같은 앱 내에서 view 별 패턴 다름

`stocks/` 내부:
- `views_exchange.py` IndexQuotesView: **W** 패턴 (`{success, data, meta}`)
- `views_eod.py` EODDashboardView: **R** 패턴 (raw dict)
- `views_indicators.py` TechnicalIndicatorView: **R** 패턴
- `views.py` StockOverviewAPIView: **R** 패턴 (raw, `_meta`/`_source` 언더스코어 prefix)
- `views.py` StockSearchAPIView: 부분 R, 응답에 `'result'`/`'results'` 오타까지 존재 (line 173 vs 181)

#### Case 3: serverless `success: false` 에러 vs DRF 기본 예외 혼재

`serverless/views.py:140-147`
```python
return Response({
    'success': False,
    'error': {'code': 'NOT_FOUND', 'message': '...'}
}, status=status.HTTP_404_NOT_FOUND)
```
vs `users/views.py:115`
```python
raise NotFound  # DRF가 자동으로 {"detail": "Not found."} 반환
```
→ 동일 의미(404 Not Found)에 대해 클라이언트는 `data.error.message` 와 `data.detail` 두 경로를 모두 처리해야 함.

#### Case 4: `'result'` vs `'results'` 키 오타

`stocks/views.py:172-181` — 같은 view에서 `result` 와 `results` 혼용:
```python
return Response({
    'result': [],          # ← 단수
    'message': '검색어를 입력해주세요',
}, status=status.HTTP_400_BAD_REQUEST)

if len(query) < 2:
    return Response({
        'results': [],     # ← 복수
        'message': '검색어는 2자 이상 입력해주세요.'
    }, status=status.HTTP_400_BAD_REQUEST)
```

---

## HTTP 상태 코드 일관성

### 사용 통계

| 패턴 | 사용 횟수 | 사용 앱 | 권장 |
|------|----------|---------|------|
| `status.HTTP_*` 상수 | **248회** (16개 파일) | 대부분 | ✅ |
| `status=200/400/...` 정수 | **15회** (3개 파일) | portfolio (10), sec_pipeline (3), serverless (1), users (1) | ❌ |
| 라인 끝 매직넘버 (`status=400)`) | 15회 | 위와 동일 | ❌ |

### 201 CREATED 사용 분석

**올바른 사용 (POST 생성 시 201)**:
- `users/views.py:105` (회원가입), `:288` (관리자 회원생성)
- `users/views.py:631, :723` (Watchlist/Item 생성)
- `users/views.py:910, :1032` — **조건부 패턴**: `status=status.HTTP_201_CREATED if added else status.HTTP_200_OK`
- `serverless/views.py:1060, :1428, :1819` (Preset/Alert 생성)
- `rag_analysis/views.py:84, :164, :346, :455` (DataBasket/Item 생성)
- `serverless/views_admin.py:568`

**누락 사례 (POST 생성하지만 200 또는 wrapped success 반환)**:
- `serverless/views.py:166-200` `trigger_sync` — Celery task 시작은 작업 생성이지만 200으로 반환
- `serverless/views.py:2820-2872` `extract_relations_from_news_api` — task 트리거에 201 미사용
- `validation/api/views.py:475-484` `PeerPreferenceView.post` — `update_or_create` 결과를 200으로 반환

### 에러 코드 사용 패턴

| 코드 | 사용처 | 일관성 |
|------|--------|-------|
| 400 | 입력 검증 (`serializer.errors`, 잘못된 파라미터) | ✅ 광범위 사용 |
| 401 | `serverless/views.py:1413` (Login required), `validation:463` (로그인 필요) | ⚠️ 일부 view는 `IsAuthenticated`로 자동 처리 → DRF 기본 401 |
| 403 | `serverless/views.py:1110, :1133, :1138, :1458` (Preset 소유권) | ✅ |
| 404 | `Stock not found`, `Watchlist not found` 등 | ⚠️ users는 `raise NotFound`, serverless는 `Response({success:false,...}, 404)` 혼용 |
| 429 | `serverless/views_admin.py:369` (admin action cooldown), `portfolio/views.py:101` (LLM budget) | ✅ |
| 500 | `try/except Exception` blanket catch + 일반 메시지 | ⚠️ 너무 광범위, 디버깅 어려움 |
| 503 | `stocks/views_search.py:52`, `views_exchange.py:58, :177` (외부 API 실패) | ✅ |
| 202 | `sec_pipeline/views.py:41` (수집 트리거됨) | ✅ 단일 사용 |
| 204 | `users/views.py:680, :751, :1079`, `rag_analysis/views.py:129` (DELETE 성공) | ✅ |

### 정수 하드코딩 사례 (수정 권고)

```
portfolio/views.py:43,51,53,78,86,94,106,112,115  → status=400/500/200/...
sec_pipeline/views.py:38,44,46                    → status=202/200
serverless/views.py:2879                          → status=400
users/views.py:910                                → status.HTTP_201_CREATED if added else status.HTTP_200_OK (이건 OK)
```

---

## 에러 응답 형식

### 에러 응답 키 분포

| 키 형식 | 출현 횟수 | 사용 앱 | 예시 |
|---------|----------|---------|------|
| `{'error': 'string'}` | **204회** | 거의 전 앱 | `{'error': 'Stock AAPL not found'}` |
| `{'message': '...'}` | **112회** | macro, users, rag_analysis | `{'message': '검색어를 입력하세요'}` |
| `{'error': {'code': '...', 'message': '...'}}` | ~30회 (rag_analysis, serverless) | 구조화된 에러 | `{'error': {'code': 'BASKET_FULL', 'message': '...'}}` |
| `{'detail': '...'}` | 9회 (portfolio:6, users:2, config:1) | DRF 기본 + portfolio | `{'detail': 'Not found.'}` |
| DRF 자동 (`raise NotFound`) | 9회 (users) | users | DRF가 `{"detail": "Not found."}` 반환 |

### 4종 동시 사용 사례

같은 컨셉의 "리소스를 찾을 수 없음"을 4가지 다른 형태로 응답:

1. `{'error': 'Stock AAPL not found'}` — `validation/api/views.py:59`, `chainsight/api/views.py:67`, `stocks/views_fundamentals.py:78`
2. `{'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Market mover not found: AAPL on 2026-05-04'}}` — `serverless/views.py:140`
3. `{'symbol': 'AAPL', 'error': 'no_data', 'message': '재무 분석 데이터 준비 중입니다.'}` — `validation/api/views.py:82` ⚠️ **여기서는 200으로 반환** (404가 아님)
4. `{"detail": "Not found."}` — DRF 기본 (`raise NotFound`)

### `generate_error_response` 헬퍼 사용 사례

`rag_analysis/views.py:46-59`만 표준 헬퍼 보유:
```python
def create_error_response(code, message, meta=None):
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "meta": {"request_id": ..., "timestamp": ...}
    }
```
→ **다른 앱에서는 임시변수로 dict 직접 작성**. 헬퍼 부재로 다양성이 발생.

### Validation 에러의 비표준 처리

`stocks/views_screener.py:65-68`:
```python
return Response(
    {"error": serializer.errors},  # DRF errors dict를 그대로 'error' 키 안에 nested
    status=status.HTTP_400_BAD_REQUEST
)
```
vs `users/views.py:107`:
```python
return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  # 최상위 dict
```
→ 클라이언트가 `data.error.field_name` 인지 `data.field_name` 인지 분기 필요.

### `severity` 비교 - 같은 에러 의미, 다른 status

| 의미 | 응답 | status |
|------|------|--------|
| Stock not found (validation) | `{'error': 'Stock AAPL not found'}` | **404** |
| Stock not in S&P500 (validation) | `{'symbol':..., 'error': 'not_in_universe', 'message':...}` | **200** ⚠️ |
| Stock has no data (validation) | `{'symbol':..., 'error': 'no_data', 'message':...}` | **200** ⚠️ |

→ Validation 앱은 "리소스가 있지만 분석 불가"를 200으로 반환하면서 `error` 키를 함께 보냄. 클라이언트가 `if (response.data.error) { ... }` 로 status code와 별개로 분기해야 함.

---

## 페이지네이션 현황

### 🔴 전역 설정 부재

`config/settings.py:341-349`:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    # ❌ DEFAULT_PAGINATION_CLASS 없음
    # ❌ PAGE_SIZE 없음
}
```

→ DRF의 `ListAPIView` / `ModelViewSet`이 **기본적으로 모든 결과를 단일 응답으로 반환**.

### 페이지네이션 미적용 List 엔드포인트

| 위치 | 엔드포인트 | 데이터 크기 | 페이지네이션 |
|------|-----------|-------------|-------------|
| `stocks/views.py:75` `StockListAPIView(generics.ListAPIView)` | `/api/v1/stocks/list/` | Stock 전체 (수천 종목) | ❌ |
| `stocks/views.py:91-105` get_queryset | (ListAPIView) | sector/min_market_cap 필터만 | ❌ |
| `news/api/views.py:42` `NewsViewSet(viewsets.ReadOnlyModelViewSet)` | `/api/v1/news/` | NewsArticle 전체 (수십만 건) | ❌ |
| `users/views.py:89-92` `Users.get` | `/api/v1/users/` (관리자) | User 전체 | ❌ |
| `users/views.py:967-979` UserInterestListCreateView.get | `/api/v1/users/interests/` | 단일 사용자 관심사 (소량) | ❌ |
| `validation/api/views.py:421` PresetListView | `/api/v1/validation/{symbol}/presets/` | 6개 프리셋 (소량) | ❌ |
| `thesis/views/monitoring_views.py:229` AlertListView | `/alerts/` | **하드코딩 `[:50]`** 슬라이스 | ❌ (하드 limit) |
| `stocks/views_eod.py:51` EODSignalDetailView | `/api/v1/stocks/eod/signal/...` | **하드코딩 `[:50]`** | ❌ (하드 limit) |
| `stocks/views_eod.py:110` EODPipelineStatusView | (admin) | **하드코딩 `[:7]`** | ❌ |
| `serverless/views.py:1014-1044` screener_presets_api | (GET 분기) | 시스템+사용자 프리셋 union | ❌ |
| `serverless/views.py:1393` screener_alerts_api | (GET 분기) | 사용자 알림 전체 | ❌ |
| `chainsight/api/views.py:104` ChainSightSuggestionView | top 10 + co_mention 10 + sector | ❌ (하드 LIMIT 10) |

### 페이지네이션 적용 사례 (수동)

| 위치 | 방식 | 응답 키 |
|------|------|---------|
| `users/views.py:580-620` WatchlistListCreateView | `django.core.paginator.Paginator` 수동 | `{'results': [...], 'pagination': {...}}` |
| `users/views.py:792-840` WatchlistStocksView | 동일 | 동일 |
| `rag_analysis/views.py:778-825` (LogList) | `Paginator(logs, page_size)` | `{'pagination': {'page', 'total_pages', 'total_count', ...}}` |
| `serverless/views.py:1278-1358` advanced_screener_api | offset/limit 직접 계산 | `{'results', 'count', 'total_pages', 'current_page', 'next', 'previous'}` |
| `serverless/views.py:1148-1198` execute_preset | offset/limit 직접 | `{**results}` (FilterEngine이 내부 처리) |
| `news/api/views.py:350-438` all_news | `[offset:offset+limit]` 슬라이스 | `{'total', 'count', 'offset', 'limit', 'has_more', 'articles'}` |

### 페이지네이션 응답 키 불일치

같은 "페이지네이션 응답"을 4가지 형태로 직렬화:

```python
# users/views.py 패턴
{'results': [...], 'pagination': {'count', 'page', 'page_size', 'num_pages', 'has_next', 'has_previous'}}

# rag_analysis/views.py 패턴
{'pagination': {'page', 'total_pages', 'total_count', ...}}

# serverless 고급 스크리너 패턴
{'results', 'count', 'total_pages', 'current_page', 'next', 'previous'}

# news/api 패턴
{'total', 'count', 'offset', 'limit', 'has_more', 'articles'}
```

→ 프론트엔드가 페이지네이션 컴포넌트를 **목록 API마다 다르게 작성**해야 함.

### `pagination_class` 명시적 사용

전체 28개 view 파일에서 `pagination_class = ...` 패턴 검색 결과: **0건**.

---

## 권고사항

권고사항은 **Quick Win → 구조 개선** 순서로 정렬했다. 모든 권고는 read-only 감사이므로 사용자 검토 후 시행하기를 권한다.

### 🔴 P0 — 즉시 시행 (보안/안정성)

#### 1. DRF 전역 페이지네이션 활성화

`config/settings.py:341` 의 `REST_FRAMEWORK` 에 추가:
```python
REST_FRAMEWORK = {
    ...,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}
```

→ `stocks/views.py:75 StockListAPIView`, `news/api/views.py:42 NewsViewSet`이 자동으로 페이지네이션 적용. 메모리 OOM 위험 제거.

⚠️ **회귀 위험**: 응답 구조가 `[...]` → `{count, next, previous, results: [...]}` 로 변경됨. 프론트엔드 클라이언트도 동시 수정 필요.

#### 2. 명시적 `[:N]` 슬라이스 → 페이지네이션 클래스로 마이그레이션

| 위치 | 현재 | 권고 |
|------|------|------|
| `thesis/views/monitoring_views.py:238` `[:50]` | 하드 limit | `LimitOffsetPagination` + `?limit=50` |
| `stocks/views_eod.py:79` `[:50]` | 하드 limit | 동일 |
| `chainsight/api/views.py:120-145` `LIMIT 10` (Cypher) | 하드 limit | `?limit=` 파라미터 노출 |

### 🟠 P1 — 단기 (1-2 sprint)

#### 3. 응답 표준 정의 + 점진적 마이그레이션

`contracts/api-response-envelope.md` 신설 권장:
```markdown
## 표준 성공 응답
{
  "data": ...,           // 단일 객체 또는 배열
  "meta": {...}          // 선택: timestamp, pagination, source 등
}

## 표준 에러 응답
{
  "error": {
    "code": "STRING_CODE",       // ex: "NOT_FOUND", "INVALID_INPUT"
    "message": "human-readable", // 한국어
    "field": "optional_field"    // 검증 에러 시
  }
}
```

선택지 A (권장): **`success` 키 제거** — HTTP status code로 성공/실패 판정.
- 이유: REST 원칙. status code가 이미 success를 표현하므로 `success: true` 중복.
- `serverless/views.py` 의 161개 `success` 키, `rag_analysis/views.py` 의 헬퍼 영향.

선택지 B: **`{success, data}` 패턴 유지** — 모든 앱이 따르도록 통일.
- 이유: 기존 코드 보존, 프론트엔드 변경 최소.
- 에러 시 `success: false` 필드 일관성 확보.

→ **결정 권한은 PM/리드 엔지니어**. 본 보고서는 양 선택지의 영향도만 제시.

#### 4. 에러 키 통일 (`error` 단일화)

현재 `error`(204) vs `message`(112) vs `detail`(9) 혼재.

권고:
- **DRF exception (`raise NotFound`, `raise ValidationError`) → `{"detail": ...}`**: DRF 기본 동작. 변경 어려움 → **유지**.
- **수동 `Response({'error': ...})` 형태 → `{"error": {"code": "...", "message": "..."}}`** 로 단일화: rag_analysis 헬퍼 패턴 차용.
- **`message` 단독 키 제거**: 항상 `error.message` 또는 `data.message` 로 위치 명시.

영향: `macro/views.py` 15회, `serverless/views.py` 56회, `users/views.py` 33회 수정 필요.

#### 5. validation/api/views.py 의 200+error 패턴 재검토

`ValidationSummaryView:62-67`:
```python
if not is_sp500:
    return Response({
        'symbol': symbol, 'error': 'not_in_universe',
        'message': '현재 S&P 500 종목만 지원합니다.',
    }, status=status.HTTP_200_OK)  # ⚠️ 200으로 에러 응답
```

권고: 422 Unprocessable Entity 또는 200 + `data: { unsupported: true, reason: ... }` 형태로 재설계.
→ 클라이언트가 `if (data.error)` 분기를 status code와 분리해서 검사하지 않도록.

### 🟡 P2 — 중기 (백로그)

#### 6. portfolio 앱 DRF 마이그레이션

현재 `portfolio/views.py` 만 `JsonResponse + @csrf_exempt` 패턴 사용:
- ❌ 권한 클래스 미적용 (auth 우회 가능)
- ❌ Throttle 미적용
- ❌ `request.data` (DRF) 미지원으로 `json.loads(request.body)` 수동 파싱
- ❌ Pydantic ValidationError → 수동 변환 (DRF Serializer 미사용)

→ DRF `APIView` 로 마이그레이션하면 `IsAuthenticatedOrReadOnly`, throttle, 표준 에러 핸들링이 자동 적용됨.

#### 7. 정수 status code 하드코딩 → `status.HTTP_*` 상수로 교체

`portfolio/views.py:43,51,53,78,86,94,106,112,115` (10곳), `sec_pipeline/views.py:38,44,46` (3곳), `serverless/views.py:2879` (1곳).

#### 8. 표준 페이지네이션 응답 envelope 통일

DRF 기본 `PageNumberPagination` 응답 (`{count, next, previous, results}`)을 표준으로 채택하고, 수동 페이지네이션 view들 (users, rag_analysis, serverless, news/api) 을 점진 마이그레이션.

### 🟢 P3 — 장기/스타일

#### 9. `'result'` vs `'results'` 오타 수정

`stocks/views.py:173` `'result': []` → `'results': []`.

#### 10. 빈 view 파일 정리

`metrics/views.py`, `graph_analysis/views.py`, `chainsight/views.py`, `validation/views.py`, `news/views.py` 는 `# Create your views here.` 만 존재. 미사용임이 확실하면 삭제 또는 `__init__.py` 처리.

---

## 부록

### 통계 메소드

본 감사는 ripgrep 패턴 매칭으로 정량 데이터를 수집한 후, 핵심 파일을 직접 읽어 패턴을 분류했다.

```
Response()                  : 509회 / 20개 파일
'success':                  : 186회 / 7개 파일
'error':                    : 204회 / 17개 파일
'message':                  : 112회 / 10개 파일
'detail':                   : 9회 / 3개 파일
status.HTTP_*               : 248회 / 16개 파일
status=400/200/...          : 15회 / 3개 파일
status=status.HTTP_201      : 14회 (users/serverless/rag_analysis)
pagination_class            : 0회 (전체 코드베이스)
PageNumberPagination 등     : 0회 (전체 코드베이스)
DEFAULT_PAGINATION_CLASS    : 0회 (settings.py 미설정)
```

### 본 감사가 다루지 않은 영역

- WebSocket consumer 응답 (`*/consumers.py`)
- Celery task 반환값
- `frontend/` 클라이언트 측 응답 처리 코드
- 응답 스키마 자체의 정확성 (필드명, 타입)
- Performance / N+1 (별도 `performance_audit.md` 참고)

### 관련 문서

- 의존성/계약 분석: `docs/nightly_auto_system/reports/5월/3일/api_dependency_audit.md`
- API 문서 정합성: `docs/nightly_auto_system/reports/5월/3일/api_docs_audit.md`
- 데이터 무결성: `docs/nightly_auto_system/reports/5월/3일/data_integrity_audit.md`
- 보안 검토: `docs/nightly_auto_system/reports/5월/3일/security_audit.md`
