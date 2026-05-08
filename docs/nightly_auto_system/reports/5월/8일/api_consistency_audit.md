# API 응답 일관성 감사 보고서

**감사 일자**: 2026-05-08
**감사 범위**: Backend Django 앱 25개 views.py 파일
**총 Response() 호출**: 530건 (20개 파일)
**분석 방식**: 정적 코드 패턴 분석 (Read + Grep)

---

## 요약

### 핵심 결론

Stock-Vis 백엔드는 **표준화된 응답 형식이 존재하지 않으며**, 앱별·뷰별로 응답 래핑 패턴이 심각하게 분산되어 있다. 동일 앱 내에서도 일관성이 깨져 있어 프론트엔드는 매 엔드포인트마다 응답 형태를 따로 파싱해야 한다.

### 4대 위험

| # | 위험 | 영향 | 심각도 |
|---|------|------|--------|
| 1 | **응답 래핑 패턴 4종 혼재** (`{success, data}` / `{results, pagination}` / `{success, data, meta}` / 직접 반환) | FE 파싱 코드 분기 폭증, 타입 안정성 붕괴 | 🔴 P0 |
| 2 | **DRF 기본 페이지네이션 미설정** (`DEFAULT_PAGINATION_CLASS` 없음) | 대용량 목록 API 무한 반환 가능, OOM 위험 | 🔴 P0 |
| 3 | **에러 키 5종 혼재** (`error` / `detail` / `message` / `error.code` / DRF 기본) | 에러 처리 분기 코드 폭증, 사용자 메시지 노출 일관성 깨짐 | 🟠 P1 |
| 4 | **HTTP 상태 코드 표기 3종 혼재** (`status.HTTP_*` / 숫자 / 생략) | 가독성 저하, 200으로 401/500 반환 사례 존재 | 🟡 P2 |

### 정량 지표

- **Response 래핑 패턴 5종**: `{success, data, meta}` (rag_analysis, stocks fundamentals/exchange, screener), `{success, data}` (serverless), `{success: false, error}` (serverless 에러), `{results, pagination}` (users watchlist), 직접 데이터 반환 (users, stocks main)
- **에러 키 분포** (Grep 결과): `{'error': ...}` 239건, `{'detail': ...}` 일부 portfolio, `{'message': ...}` users/news 일부, `{success: false, error: {code, message}}` serverless
- **HTTP 상태 코드 표기**: `status=status.HTTP_*` 248건, `status=숫자` 38건, 미지정 다수
- **DRF 글로벌 페이지네이션**: 0건 (`DEFAULT_PAGINATION_CLASS` 미설정)
- **수동 페이지네이션 사용**: 3개 뷰 (users WatchlistList/WatchlistStocks, rag_analysis 1개)

---

## 앱별 응답 패턴 매트릭스

| 앱 / 파일 | 라인 | 주요 패턴 | 에러 키 | 페이지네이션 | 일관성 |
|-----------|------|-----------|---------|------------|-------|
| **portfolio/views.py** | 305 | 직접 데이터 (`JsonResponse(result, 200)`) | `{error, detail}` | ❌ | ✅ 단일 패턴 (DRF 미사용) |
| **users/views.py** | 1089 | 직접 데이터 / `{results, pagination}` 혼재 | `{error}` / `{message}` / `{ok}` | ✅ Watchlist 2개만 | ⚠️ 패턴 3종 |
| **stocks/views.py** | 1021 | 직접 데이터 (`{symbol, tab, data}`) | `{error: {code,message,details}}` / `{error: str}` | ❌ | ⚠️ 에러 형식 2종 |
| **stocks/views_fundamentals.py** | 305 | `{success, data, meta}` | `{error: str}` | ❌ | ✅ 단일 |
| **stocks/views_exchange.py** | 295 | `{success, data, meta}` | `{error: str}` | ❌ | ✅ 단일 |
| **stocks/views_screener.py** | 498 | `{success, data, meta}` | `{error: serializer.errors}` | ❌ | ⚠️ |
| **stocks/views_search.py** | 229 | 직접 데이터 (`{count, results}`) | `{error: str}` / `{valid: false, error}` | ❌ | ⚠️ |
| **stocks/views_indicators.py** | 372 | 직접 데이터 (`indicators_data`) | `{error: str}` | ❌ | ✅ |
| **stocks/views_eod.py** | 137 | 직접 데이터 (`{signal_id,date,count,stocks}`) | `{error: str}` | ❌ | ✅ |
| **stocks/views_market_movers.py** | 69 | 직접 (Serializer.data) | `{error: str}` | ❌ | ✅ |
| **stocks/views_mvp.py** | 200 | 직접 (`{mode, count, data}`) | 없음 | ❌ | ✅ |
| **macro/views.py** | 411 | 직접 (Serializer.data) / `{status, message}` (sync) | `{error: str}` | ❌ | ⚠️ sync vs 데이터 |
| **serverless/views.py** | 3413 | **`{success, data}` / `{success:false, error:{code,message}}`** | `{success:false, error:{code,message}}` | ❌ (수동 limit/page 일부) | ✅ 가장 일관 |
| **serverless/views_admin.py** | 694 | 직접 (`data`) / `{success, data}` 혼재 | `{error: str}` | ❌ | ⚠️ |
| **rag_analysis/views.py** | 868 | **헬퍼 `create_success_response`/`create_error_response`** | `{success:false, error:{code,message}, meta}` | ✅ 1개 | ✅ 헬퍼 통일 |
| **chainsight/api/views.py** | 814 | 직접 (`{center, nodes, edges}`) | `{error: str}` | ❌ (수동 page/page_size 사용) | ⚠️ |
| **validation/api/views.py** | 558 | 직접 (`{symbol, ...}`) | `{error: str}` / `{symbol, error, message}` | ❌ | ⚠️ 에러 객체 2종 |
| **news/api/views.py** | 2189 | 직접 (`data`) | `{error: str}` / `{status, message}` | ❌ | ⚠️ |
| **sec_pipeline/views.py** | 51 | 직접 (`result`) | 없음 | ❌ | ✅ |
| **config/views.py** | 104 | `JsonResponse` 직접 | 없음 | ❌ | ✅ |
| **metrics/views.py** | 3 | (비어있음) | — | — | — |
| **graph_analysis/views.py** | 4 | (비어있음) | — | — | — |
| **validation/views.py** | 1 | (비어있음) | — | — | — |
| **chainsight/views.py** | 1 | (비어있음) | — | — | — |
| **news/views.py** | 3 | (비어있음) | — | — | — |

### 패턴 그룹 정리

#### 그룹 A — 직접 반환형 (~54%)
```python
return Response(serializer.data)        # macro, market_movers
return Response({'symbol': sym, 'data': ...})   # stocks main
return Response({'count': N, 'results': [...]})  # stocks_search
```
**특징**: DRF 관례에 가까움, 그러나 페이로드 형태가 뷰마다 제각각.

#### 그룹 B — `{success, data, meta}` 래핑 (~15%)
```python
return Response({
    "success": True,
    "data": serializer.data,
    "meta": {"count": N, "timestamp": ...}
})
```
**사용처**: stocks/views_fundamentals, views_exchange, views_screener (Enhanced).

#### 그룹 C — `{success, data}` 래핑 (~25%)
```python
return Response({'success': True, 'data': {...}})
return Response({'success': False, 'error': {'code': 'X', 'message': 'Y'}}, status=400)
```
**사용처**: serverless/views.py 거의 전체 (가장 일관성 있음).

#### 그룹 D — RAG 헬퍼형 (~5%)
```python
create_success_response(data, meta=None)  # {success, data, meta:{request_id, timestamp}}
create_error_response(code, message)      # {success:false, error:{code,message}, meta}
```
**사용처**: rag_analysis/views.py만. 가장 진화된 형태이나 다른 앱이 따라가지 않음.

#### 그룹 E — Django 직접 (`JsonResponse`, ~2%)
```python
return JsonResponse(result, status=200, json_dumps_params={"ensure_ascii": False})
```
**사용처**: portfolio/views.py 전체 (DRF를 의도적으로 미사용).

---

## HTTP 상태 코드 일관성

### 상태 코드 사용 통계

| 표기 방식 | 건수 | 예시 위치 |
|----------|------|----------|
| `status=status.HTTP_XXX` | 248건 | DRF 일반적 |
| `status=숫자` (200, 400, 500 등) | 38건 | portfolio (전체), serverless 1건, sec_pipeline (전체) |
| `status` 미지정 (200 기본) | 다수 | 정상 응답 대부분 |

### 발견된 일관성 문제

#### 1) 생성 시 201 vs 200 혼용
- **201 사용 (정상)**: `users/views.py:107` (User), `users/views.py:296` (Portfolio), `users/views.py:639` (Watchlist), `users/views.py:731` (WatchlistItem), `rag_analysis/views.py:87` (DataBasket), `rag_analysis/views.py:167` (BasketItem)
- **200 사용 (잘못된 사례)**:
  - `users/views.py:1040` `UserInterestListCreateView.post`: 생성 후 `created` 비어있으면 200, 비어있지 않으면 201 → 동작은 합리적이나 클라이언트 분기 부담
  - `users/views.py:918` `WatchlistBulkAddView.post`: `added if added else 200` → bulk 결과에 따라 분기
- **POST 후 200 반환 (성공/실패 둘 다)**: `validation/api/views.py:484` `UserPeerPreferenceView.put` (`{status: 'ok'}`)

#### 2) 204 No Content 사용 — 적절
- `users/views.py:342, 688, 759, 1087`, `rag_analysis/views.py:132, 205` (DELETE 시)

#### 3) 500과 503 혼용 (외부 API 실패)
- **503 사용**: `stocks/views_search.py:53`, `stocks/views_exchange.py:58, 178, 228, 277` (FMP API 실패 시)
- **500 사용**: `stocks/views.py:332, 596, 671, 745`, `users/views.py:521, 566`, `macro/views.py 전체` — 외부 API 실패 시에도 500
- **권고**: 외부 API 의존 실패는 503, 내부 코드 버그는 500으로 통일.

#### 4) 401 vs 403
- `validation/api/views.py:463, 489`: 로그인 필요 시 401 사용 — 그러나 DRF의 `IsAuthenticated`는 기본적으로 403 반환.
  - 권고: `permission_classes=[IsAuthenticated]`로 통일하거나 DRF 동작에 맞춰 401/403 명시.

#### 5) 202 Accepted 사용 — 적절
- `sec_pipeline/views.py:45`: 비동기 수집 트리거 시 202 반환 (모범 사례).

#### 6) 상태 코드 미설정으로 인한 잠재 버그
- `validation/api/views.py:340, 349`: `{symbol, error: 'no_leader'}` / `{error: 'no_data'}` 반환 시 status 미지정 → **200 OK로 응답** 됨.
  - 해당 응답은 실패 의미를 담고 있으나 HTTP 200이라 클라이언트가 성공으로 처리할 가능성 있음.

#### 7) 숫자 하드코딩
- `portfolio/views.py 전체`: `status=400`, `status=500`, `status=429`, `status=503` 모두 숫자.
- `sec_pipeline/views.py:45-51`: `status=202`, `status=200` 숫자.
- `serverless/views.py:2887`: `status=400` 숫자 (다른 라인은 `status=status.HTTP_*`).
- 권고: 일관성을 위해 `rest_framework.status` 상수를 사용하거나, portfolio처럼 의도적으로 DRF를 회피한 경우 숫자를 명시적으로 통일.

---

## 에러 응답 형식

### 에러 키 사용 분포 (앱별)

| 에러 키 패턴 | 건수 | 사용처 |
|-------------|------|--------|
| `{'error': str}` | ~150건 | macro, stocks (search/eod/quote/market_movers/fundamentals/exchange/screener), users, validation |
| `{'error': str, 'message': str}` | ~10건 | validation/api/views.py (in_universe, no_data) |
| `{'error': {'code': str, 'message': str, 'details': dict}}` | ~10건 | stocks/views.py:586 (Overview), stocks/views.py:920 (Sync) |
| `{'success': False, 'error': {'code': str, 'message': str}}` | ~70건 | serverless/views.py 전체 |
| `{'success': False, 'error': {'code': str, 'message': str}, 'meta': dict}` | ~30건 | rag_analysis/views.py 전체 |
| `{'detail': str}` | DRF 기본 (raised exceptions) | DRF 표준 (`raise NotFound`, `raise ParseError`) |
| `{'message': str}` | ~5건 | users/views.py:213, 242, 248 (favorites), `{'ok': str}` (login/logout) |
| serializer.errors (raw) | ~30건 | 모든 ModelSerializer is_valid 검증 실패 시 |
| `{status: 'ok'/'started'/'no_report', message: str}` | ~10건 | macro/sync, news/ml_shadow, validation/preference |

### 핵심 문제

#### 1) **에러 키 5종 혼재** — FE에서 `error?.message ?? detail ?? error ?? message` 같은 로직 필요
가장 큰 일관성 위반. 같은 stocks 앱 내에서도:
- `views.py:586` → `{error: {code, message, details}}`
- `views_fundamentals.py:78` → `{error: str}`
- `views_search.py:32` → `{error: str}`

#### 2) **serializer.errors 직접 노출**
```python
# users/views.py:299, 336, 474, 640, 677, 733, 797
return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```
DRF 기본 동작이지만 다른 앱은 래핑함:
```python
# stocks/views_screener.py:65
return Response({"error": serializer.errors}, status=...)
# rag_analysis/views.py:90
return Response(create_error_response("INVALID_INPUT", str(serializer.errors)), ...)
```
- **문제**: serializer.errors는 dict (필드별 에러 리스트). FE는 어떤 모양일지 매번 추론해야 함.
- **권고**: 전역 exception handler로 `{success:false, error:{code:'VALIDATION_ERROR', fields: serializer.errors}}` 형태로 통일.

#### 3) **DRF 표준 `{detail: ...}` 와 커스텀 형식 충돌**
- `raise NotFound("...")` → DRF가 `{detail: '...'}` 반환 (users, rag_analysis 다수)
- `return Response({'error': '...'}, status=404)` → 커스텀 형식 (stocks, validation, serverless)
- 동일 앱 내에서도 혼재: `users/views.py:120` (NotFound) vs `users/views.py:439` (custom error).

#### 4) **에러 메시지에 `{str(e)}` 직접 노출**
```python
# stocks/views.py:331, 671, 744, 816
return Response({'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'}, status=500)
# stocks/views_search.py:86, 142
return Response({'error': f'서버 오류: {str(e)}'}, status=...)
# users/views.py:521, 566
return Response({'error': '...', 'detail': str(e)}, status=500)
```
- **보안 우려**: 내부 트레이스/SQL/파일 경로가 클라이언트로 노출될 수 있음. (`security_audit.md`와 교차 점검 필요)
- **권고**: `str(exc)[:300]`처럼 길이 제한 및 운영 모드에서는 일반 메시지로 마스킹.

#### 5) **에러 코드 vs 에러 메시지 분리 부재**
- serverless / rag_analysis 만 `code` 필드를 가짐. 다른 앱은 자연어 메시지만 반환.
- FE 다국어 처리 시 코드 기반 매핑이 불가능.

---

## 페이지네이션 현황

### 글로벌 설정

```python
# config/settings.py:348-362
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
    'DEFAULT_THROTTLE_RATES': {...},
    'DEFAULT_SCHEMA_CLASS': '...',
    # ❌ DEFAULT_PAGINATION_CLASS 없음
    # ❌ PAGE_SIZE 없음
}
```

**결과**: DRF의 모든 ListView/list 액션은 페이지네이션 없이 전체 결과를 반환한다. `Glob`/`Grep`으로 검색한 결과, **`PageNumberPagination`, `CursorPagination`, `LimitOffsetPagination`, `pagination_class`, `paginate_queryset` 사용 0건**.

### 페이지네이션을 적용한 뷰 (수동 구현)

| 위치 | 방식 | 응답 형식 |
|------|------|----------|
| `users/views.py:597` `WatchlistListCreateView.get` | Django `Paginator` (page/page_size) | `{results, pagination: {count, page, page_size, num_pages, has_next, has_previous}}` |
| `users/views.py:810` `WatchlistStocksView.get` | Django `Paginator` 동일 | 동일 |
| `rag_analysis/views.py:782-826` (분석 로그) | Django `Paginator` | `{..., pagination: {page, page_size, total_pages, total_count}}` |
| `serverless/views.py:1277` 영역 | 수동 `limit`/`offset` 쿼리 파라미터 | 정해진 limit만큼 반환 |
| `chainsight/api/views.py` | `page`/`page_size` 쿼리 파라미터 | `_build_chain_signals(page, page_size, ...)` |

### 페이지네이션이 누락된 위험 뷰 (대용량 잠재)

| 위치 | 쿼리 | 위험도 |
|------|------|-------|
| `users/views.py:91` `Users.get` | `User.objects.all()` 전체 | 🔴 (관리자 전용이지만 사용자 폭증 시 OOM) |
| `users/views.py:264, 358, 404` Portfolio 목록 | `Portfolio.objects.filter(user=request.user)` | 🟡 (사용자별이지만 보유 종목 수 무제한) |
| `users/views.py:975` UserInterest | `UserInterest.objects.filter(user=...)` | 🟢 (사용자별, 적은 갯수) |
| `stocks/views.py:75` `StockListAPIView` (`generics.ListAPIView`) | `Stock.objects.all().order_by('-market_capitalization')` | 🔴 (S&P 500 + 전체 = 수천 건이 한 번에 반환됨, 글로벌 페이지네이션 없으므로 무한 반환) |
| `stocks/views_mvp.py:41` | `Stock.objects.all()[:20]` 하드코딩 | 🟢 (limit 20) |
| `stocks/views.py:190` 검색 | `[:20]` 하드코딩 | 🟢 |
| `stocks/views_eod.py:78` 시그널 상세 | `[:50]` 하드코딩 | 🟢 |
| `stocks/views_eod.py:119` 파이프라인 로그 | `[:7]` 하드코딩 | 🟢 |
| `news/api/views.py:50` `NewsViewSet.queryset` | `NewsArticle.objects.all().prefetch_related(...)` | 🔴 (DRF ReadOnlyModelViewSet에 페이지네이션이 없으면 전부 반환) |
| `validation/api/views.py:151, 335` peer 목록 | `Stock.objects.filter(symbol__in=peer_symbols)` | 🟡 (peer는 보통 5–20개) |
| `serverless/views.py:2963` LLM 관계 | `[:50]` 하드코딩 | 🟢 |

### 핵심 문제

1. **`stocks/StockListAPIView`** (`generics.ListAPIView`): `DEFAULT_PAGINATION_CLASS`가 없으므로 `Stock.objects.all()`을 전부 반환. S&P 500 ETF 등 수천 건이 한 응답에 들어감.
2. **`news/NewsViewSet`** (`ReadOnlyModelViewSet`): 동일 이유로 전체 NewsArticle 반환 위험. `prefetch_related('entities')`까지 포함되어 페이로드 폭발.
3. **수동 페이지네이션 응답 형식 불일치**:
   - users: `{results, pagination: {count, page, page_size, num_pages, has_next, has_previous}}`
   - rag_analysis: `{..., pagination: {page, page_size, total_pages, total_count}}` — `count` vs `total_count`, `num_pages` vs `total_pages` 키 불일치.

---

## 권고사항

### 🔴 P0 — 즉시 수정 (1주 내)

#### R1. DRF 글로벌 페이지네이션 활성화
```python
# config/settings.py REST_FRAMEWORK
REST_FRAMEWORK = {
    ...
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}
```
- **Why**: `StockListAPIView`, `NewsViewSet` 등 ListView가 무한 반환되는 즉각적 위험 차단.
- **영향**: 기존 응답이 `[...]` → `{count, next, previous, results}` 로 변경 → FE 동기 변경 필요. 영향 큰 변경이므로 별도 PR로 분리.

#### R2. 응답 형식 표준 정립
- **선택지**:
  - **(권장) Option A**: `rag_analysis`의 헬퍼 패턴을 전역화 — `{success, data, meta:{request_id,timestamp}}` / 에러는 `{success:false, error:{code,message}, meta}`.
  - Option B: DRF 기본 그대로 (`Response(data)`) + DRF 예외 핸들러 통일.
- **Why**: 현재 5종 혼재로 FE 코드가 매 엔드포인트마다 분기. 헬퍼 강제 사용 + lint 룰로 점진적 마이그레이션.
- **How**:
  1. `core/api_helpers.py`에 `success_response`/`error_response` 신설.
  2. 새 엔드포인트는 헬퍼 의무화 (CI에 grep 룰 추가).
  3. 기존 엔드포인트는 `/api/v2/` 네임스페이스에서 마이그레이션, `/api/v1/`은 deprecated.

#### R3. 전역 DRF 예외 핸들러
```python
# REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'core.exceptions.custom_exception_handler'
```
- 모든 `raise NotFound`, `raise ValidationError` 등을 `{success:false, error:{code, message}}` 형식으로 변환.
- serializer.errors도 `{success:false, error:{code:'VALIDATION_ERROR', fields:{...}}}`로 통일.

### 🟠 P1 — 1개월 내

#### R4. 에러 메시지에서 내부 정보 노출 제거
- `str(e)` 직접 반환을 차단. 운영(`DEBUG=False`) 환경에서는 일반화된 메시지만, 디버그용 상세는 로그로만.
- 영향: `stocks/views.py:331, 671, 744, 816, 596`, `stocks/views_search.py:86, 142`, `users/views.py:521, 566`, `macro/views.py 다수`.

#### R5. HTTP 상태 코드 표기 통일
- `status=숫자` → `status=status.HTTP_*` 일괄 변환 (sec_pipeline, serverless 일부, portfolio).
- 단, portfolio는 DRF 미사용이므로 예외 처리.

#### R6. validation/api 에러 시 status 명시
- `validation/api/views.py:340, 349`처럼 status 미지정으로 200을 반환하는 케이스를 점검하여 적절한 4xx로 변경.

#### R7. 외부 API 실패 시 503 통일
- 외부 API(FMP, Alpha Vantage, FRED) 실패 → 503 (사용 처: `stocks/views_search`, `stocks/views_exchange`).
- 내부 버그 → 500.
- 현재 macro 전체가 외부 API 실패에도 500을 반환 → 503으로 변경.

### 🟡 P2 — 3개월 내 / 점진적

#### R8. 페이지네이션 응답 키 통일
- users vs rag_analysis 키 불일치 (`num_pages` vs `total_pages`, `count` vs `total_count`).
- DRF 기본 `PageNumberPagination` 사용으로 자연 해결.

#### R9. 401 vs 403 명시
- `validation/api/views.py:463, 489`: 수동 401 반환을 DRF `IsAuthenticated`에 위임.

#### R10. 빈 views.py 정리
- `metrics/views.py`, `graph_analysis/views.py`, `validation/views.py`, `chainsight/views.py`, `news/views.py`: 사용하지 않으면 `# Create your views here.` 주석을 제거하거나 파일 자체를 삭제.

### 우선순위 요약

| 권고 | 파일 영향 범위 | 예상 작업 시간 | 비고 |
|------|---------------|--------------|------|
| R1 글로벌 페이지네이션 | 1 (settings) + FE 다수 | 1일 + FE 1주 | API 호환성 깨짐, v2 분기 필요 |
| R2 응답 형식 표준 | 신규 코드 정책 + 점진 마이그 | 1주 + 분기별 | v1 유지하며 v2로 |
| R3 전역 예외 핸들러 | 1 (handler) | 2일 | DRF 활용으로 즉시 효과 |
| R4 내부 정보 노출 | ~10 파일 | 1주 | security_audit과 교차 |
| R5 status 표기 통일 | ~5 파일 | 반나절 | mechanical |
| R6 status 미지정 fix | validation 1 파일 | 2시간 | 안전 픽스 |
| R7 503 통일 | macro 1 파일 | 반나절 | 정책 결정 후 |
| R8 페이지네이션 키 | 글로벌 페이지네이션 채택 시 자연 해결 | — | R1과 함께 |
| R9 401/403 | validation 1 파일 | 1시간 | 안전 픽스 |
| R10 빈 파일 정리 | 5 파일 | 30분 | cleanup |

---

## 부록 A — 패턴 분포 데이터 (Grep 카운트)

### Response 호출 분포 (파일별)
```
serverless/views.py: 126
users/views.py: 56
serverless/views_admin.py: 45
news/api/views.py: 61
rag_analysis/views.py: 38
portfolio/views.py: 32
macro/views.py: 26
stocks/views.py: 25
validation/api/views.py: 23
chainsight/api/views.py: 20
stocks/views_screener.py: 15
stocks/views_fundamentals.py: 15
stocks/views_exchange.py: 13
stocks/views_search.py: 10
stocks/views_indicators.py: 8
stocks/views_eod.py: 6
stocks/views_mvp.py: 4
sec_pipeline/views.py: 3
config/views.py: 2
stocks/views_market_movers.py: 2
```

### `success` 키 사용 (Multiline grep, ~100건 표본)
- `serverless/views.py`: 다수 (success: true/false 양쪽)
- `stocks/views_fundamentals.py`, `views_exchange.py`, `views_screener.py`: success: true (응답 래핑)
- `rag_analysis/views.py`: 헬퍼 통해 사용
- 그 외: 미사용

### 에러 키 사용 분포
```
{'error': ...}     239건  18 파일
{'detail': ...}    portfolio 다수 (커스텀 + DRF NotFound 등 raise)
{'message': ...}   users 일부, news 일부
{success:false, error:{...}} serverless, rag_analysis
```

### HTTP 상태 코드 표기
```
status=status.HTTP_*   248건  16 파일
status=숫자             38건  portfolio (32건), serverless 1건, sec_pipeline 4건, macro 1건
status 미지정 (200 기본)  다수
```

---

## 부록 B — 대표 코드 스니펫

### 좋은 예 (참고할 만한 패턴)

**rag_analysis 헬퍼 패턴** (`rag_analysis/views.py:35-61`):
```python
def create_success_response(data, meta=None):
    return {"success": True, "data": data, "meta": meta or {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat()
    }}

def create_error_response(code, message, meta=None):
    return {"success": False, "error": {"code": code, "message": message}, ...}
```

**serverless 일관 패턴** (`serverless/views.py:73-79`):
```python
return Response({
    'success': False,
    'error': {'code': 'INVALID_TYPE', 'message': '...'}
}, status=status.HTTP_400_BAD_REQUEST)
```

**sec_pipeline 202 사용** (`sec_pipeline/views.py:42-46`):
```python
return Response(
    {'symbol': symbol.upper(), 'status': 'collecting',
     'message': 'Collection triggered. Check back shortly.'},
    status=202,
)
```

### 위험한 예 (수정 필요)

**str(e) 노출** (`stocks/views.py:331`):
```python
return Response({'error': f'데이터 조회 중 오류가 발생했습니다: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

**status 미지정** (`validation/api/views.py:340`):
```python
return Response({'symbol': symbol, 'error': 'no_leader'})
# → HTTP 200 반환됨 (의도와 불일치)
```

**같은 앱에서 에러 형식 다름** (stocks):
```python
# views.py:586 (stocks/Overview)
return Response({'error': {'code': 'OVERVIEW_ERROR', 'message': '...', 'details': {...}}}, status=500)
# views_fundamentals.py:78
return Response({"error": "..."}, status=status.HTTP_404_NOT_FOUND)
```

---

## 부록 C — 영향 받는 프론트엔드 파일 추정

본 감사는 백엔드 전용이지만, 권고 R1·R2·R3 적용 시 프론트엔드 동기화가 필수다. 추정 영향 범위:

- `frontend/lib/api/authAxios.ts` — 응답 파싱 인터셉터
- `frontend/lib/api/*.ts` — 각 도메인별 API 호출 함수
- TanStack Query 훅 다수 — 응답 모양 변경 시 일괄 수정 필요

**권고**: R1·R2는 `/api/v2/` 네임스페이스로 별도 도입하고 `/api/v1/`은 6개월 후 sunset.

---

**감사자 메모**: 본 보고서는 정적 코드 분석으로 작성되었으며, 실제 런타임 응답은 DRF 미들웨어 / 인증 / 권한 / 시리얼라이저 동작에 따라 부분적으로 차이가 있을 수 있다. 마이그레이션 전에는 통합 테스트(`tests/`)에서 응답 형식 단언이 깨지는지 사전 검증 필요.
