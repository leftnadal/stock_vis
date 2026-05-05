# API 응답 일관성 감사 보고서

- 감사 일자: 2026-05-06
- 감사 대상: `**/views*.py` 26개 파일 (총 13,398 LOC)
- 분석 도구: Grep / Read 정적 분석 (코드 변경 없음)
- Response 호출 총합: **512건** (20개 파일) + thesis 18건 = **약 530건**

---

## 요약

| 항목 | 결과 |
|------|------|
| 응답 래핑 패턴 | **3종 혼재** — wrapping(success/data/meta) / 직접 / 커스텀 dict |
| HTTP 상태 코드 | DRF `status.*` 상수 248건 + 하드코딩 숫자 약 17건 (portfolio·sec_pipeline·serverless) |
| 201 Created 사용 | 14건만 사용 — portfolio.create처럼 누락된 곳 일부 발견 |
| 에러 응답 형식 | **5종 혼재** — `error: str` / `error: {code,message}` / `detail` / `message` / `error+detail` |
| 페이지네이션 | DRF 전역 미설정, 수동 `Paginator` 2곳, `offset/limit` 1곳, **목록 무한 반환 다수** |
| 가장 일관된 앱 | `serverless/`, `rag_analysis/` — 통일된 wrapping 헬퍼 사용 |
| 가장 비일관 앱 | `stocks/` — views.py / views_screener / views_fundamentals 간 패턴 불일치 |

**핵심 리스크 3가지**
1. **프론트엔드가 앱마다 응답 unwrap 분기 처리 필요** — `success/data` 추출 vs 평탄 dict 추출이 라우트별로 갈림.
2. **`Users.get()`(전체 사용자), `news.market/trending`, `validation.PresetList` 등 페이지네이션 없는 목록 응답** — 데이터 증가 시 응답 비대화·메모리 폭증 위험.
3. **`portfolio/views.py`는 DRF가 아닌 순수 Django + `JsonResponse`** 라 라우트 단위로 인증/권한/throttle/예외 핸들링이 달라짐.

---

## 앱별 응답 패턴 매트릭스

표기 범례
- **W** = `{success: bool, data: ..., (meta?, error?)}` 래핑
- **D** = serializer.data 또는 평탄 dict 직접 반환 (DRF 기본)
- **C** = 커스텀 dict (e.g. `{results: [], pagination: {...}}`, `{added, skipped, errors, summary}`)
- **R** = JsonResponse (DRF 미사용)

| 앱/파일 | 패턴 | success 사용 | error 형태 | 비고 |
|---------|------|-------------|-----------|------|
| `serverless/views.py` | **W** (62개) | True/False 모두 | `error: {code, message}` | 가장 일관된 W 형식 |
| `serverless/views_admin.py` | **W** | 1건만 | `error: {code, message}` | 일부 D 혼재 |
| `rag_analysis/views.py` | **W** (헬퍼 `create_success_response/create_error_response`) | 모두 | `error: {code, message}` + `meta.request_id` | DRF 4xx에서도 일관 |
| `stocks/views_fundamentals.py` | **W** (5개 엔드포인트) | True | 그러나 에러는 `{error: str}` (15건) | wrapping과 평탄 에러 혼재 |
| `stocks/views_screener.py` | **W** (7개) | True | `{error: str}` (8건) | 위와 동일 |
| `stocks/views_exchange.py` | **W** (5개) | True | `{error: str}` (8건) | 위와 동일 |
| `stocks/views.py` | **D 우세 + C 일부** | 2건만 False | `{error: str}` 12건, `{message,...}` 1건 | `StockSearchAPIView`만 search 결과 wrapping 시도 |
| `stocks/views_market_movers.py` | **D** | 0 | `{error: str}` | serializer.data 그대로 |
| `stocks/views_eod.py` | **D** | 0 | `{error: str}` | snapshot.json_data를 raw 반환 |
| `stocks/views_indicators.py` | **D** | 0 | `{error: str}` | 평탄 dict |
| `stocks/views_search.py` | **D** | 0 | `{error: str}` | 평탄 dict |
| `stocks/views_mvp.py` | **D** | 0 | (Http404) | |
| `users/views.py` | **D + C** | 0 | `{error: str}` + `{detail}` (raise) + `{message}` | Watchlist 목록은 `{results, pagination}`, JWT는 simplejwt 기본 |
| `macro/views.py` | **D** | 0 | `{error: str}` 15건 | 매 view try/except로 500 + `{error}` |
| `news/api/views.py` | **D + C** | 0 | `{detail}` (DRF raise) + `{error}` | 페이지네이션은 자체 offset/limit, ViewSet은 DRF 기본 |
| `chainsight/api/views.py` | **D** | 0 | `{error: str}` 9건 | Neo4j sanitize 후 평탄 dict |
| `validation/api/views.py` | **D** | 0 | `{error: str}` 15건 | preset/peer 단순 dict |
| `thesis/views/*.py` | **D** | 0 | `{error: str}` (e.g. close action) | DRF ModelViewSet — 4xx는 ValidationError raise |
| `metrics/views.py` | (사실상 비어 있음, 3 LOC) | — | — | 미구현 |
| `graph_analysis/views.py` | (사실상 비어 있음, 3 LOC) | — | — | 미구현 |
| `validation/views.py` | (1 LOC) | — | — | 모듈 비어 있음 |
| `chainsight/views.py` | (1 LOC) | — | — | 모듈 비어 있음 |
| `news/views.py` | (3 LOC) | — | — | 미구현 |
| `sec_pipeline/views.py` | **D** + 하드코딩 status | 0 | `{message: str}` | DRF지만 `status=200/202` 정수 |
| `portfolio/views.py` | **R** (JsonResponse) | 0 | `{error: 'code', detail: str}` 6건 / `{error: str}` 6건 | 순수 Django, DRF 미사용 |
| `config/views.py` | **R** (JsonResponse) | 0 | — | API root + health check |

### 패턴 충돌 핫스팟

`stocks/views_fundamentals.py:77-80` — 같은 메서드 내에서 성공은 `W`, 실패는 평탄 `{error: str}`
```python
return Response({"error": "..."}, status=...)         # 평탄
...
return Response({"success": True, "data": ..., "meta": ...})  # 래핑
```
같은 패턴이 `views_screener.py`, `views_exchange.py` 모두에서 발견됨 — 클라이언트가 `body.success`를 체크하면 에러는 `undefined`라 분기 실패.

---

## HTTP 상태 코드 일관성

### 상수 vs 하드코딩

| 종류 | 빈도 | 분포 |
|------|------|------|
| `status.HTTP_*` (DRF 상수) | **248건 / 16개 파일** | 대부분의 DRF view |
| 하드코딩 숫자 (`status=200`, `status=400`, ...) | **약 17건** | `portfolio/views.py`(11), `sec_pipeline/views.py`(3), `serverless/views.py`(1: 2879 라인), `users/views.py`(일부) |

**구체 위치**
- `portfolio/views.py:43,49,51,53,78,86,94,101,106,112,115` — DRF 미사용으로 정수만 가능. 다만 `429` 같은 숫자는 직관성 떨어짐.
- `sec_pipeline/views.py:40,44,46` — DRF Response인데 `status=202`, `status=200` 정수.
- `serverless/views.py:2879` — wrapping 패턴 일관성에서 1건 일탈.

### 코드별 사용 분포

| 코드 | 빈도 | 비고 |
|------|------|------|
| 200 | (기본값, 명시 거의 안 함) | |
| **201 Created** | 14건 (5개 파일) | 후술하는 누락 사례 있음 |
| **202 Accepted** | 1건 | `sec_pipeline.FilingDataView` (수집 트리거) |
| 204 No Content | 다수 | DELETE 응답 표준 — 일관됨 |
| **400 Bad Request** | 85건 (16개 파일) | 가장 흔한 에러 |
| **401 Unauthorized** | 6건 (3개 파일) | `validation.PeerPreference`가 직접 401 (보통 DRF가 자동 처리해야 함) |
| **403 Forbidden** | 10건 (2개 파일) | `serverless/views.py`(9), `rag_analysis`(1) |
| **404 Not Found** | 45건 (15개 파일) | `raise NotFound()` 41건과 별개로 직접 Response 반환 |
| **429 Too Many Requests** | 1건 | `portfolio/views.py` (LLM budget) |
| **500 Internal Server Error** | 49건 (7개 파일) | `macro/views.py`(13)에 집중 — 모든 try/except를 500으로 묶음 |
| **503 Service Unavailable** | (`stocks/views_search.py`, `stocks/views_exchange.py`, `portfolio/views.py`) | Provider 실패 시 |

### 201 Created 누락/혼선

| 파일 | 라인 | 메서드 | 현재 코드 | 문제 |
|------|------|--------|----------|------|
| `users/views.py:910` | bulk add | `status_code=201 if added else 200` | 부분 추가 시에만 201 — 원리상 멀티 자원 생성은 207 적합 |
| `users/views.py:1032` | UserInterest | `status_code=201 if created else 200` | 동일 |
| `portfolio/views.py:53,115` | E1/E5 응답 | `status=200` 고정 | E5 LLM 결과는 신규 리소스 아님 — OK |
| `stocks/views.py:StockSearch` | search 결과 | 200 (기본) | OK |
| `news.NewsViewSet` | DRF default | 자동 처리 | OK |

`Users.post(self, request)` (`users/views.py:105`) 등 단일 자원 POST는 모두 201 사용 — 이쪽은 일관됨.

### 비표준/오용

- `validation/api/views.py:67-68` — Stock이 S&P500이 아닐 때 **`status=200`** 으로 `{error: 'not_in_universe'}` 반환. body는 에러지만 status는 정상 — 클라이언트가 `200 OK`로 인식 → 분기 누락 위험.
- `validation/api/views.py:82-86` — 데이터 준비 중 `error: 'no_data'`도 200 반환. 동일 이슈.
- `news/api/views.py:151` — sentiment 데이터 없을 때 의도적으로 200 + 빈 dict — 코멘트로 "404 대신"이라 명시. 의도적이지만 다른 view와 정책 불일치.
- `portfolio/views.py:101` — LLM budget 초과 시 **429 vs 503** 두 곳에서 다르게 처리됨 (`/e1`은 503, `/e5`는 429). 동일 예외인데 코드가 다름.

---

## 에러 응답 형식

`Response({...})`로 직접 반환하는 에러 본문은 5가지 형식이 혼재.

| 형식 | 예시 | 사용처 | 비고 |
|------|------|--------|------|
| **A. `{error: str}`** | `{"error": "Stock not found"}` | macro, stocks/*, validation, chainsight, news 일부 | 가장 흔함 (204건) |
| **B. `{error: {code, message}}`** | `{"error": {"code": "INVALID_TYPE", "message": "..."}}` | serverless, serverless_admin, rag_analysis | wrapping 패턴과 함께 — 구조적이며 좋은 모범 |
| **C. `{detail: str}`** | `{"detail": "Watchlist not found"}` | DRF 기본 (`raise NotFound`, `raise ValidationError` 등 41건) | 명시적으로 쓰지 않아도 자동 발생 |
| **D. `{message: str}`** | `{"message": "This stock is already in your favorites"}` | `users/views.py` 즐겨찾기 (3건), `sec_pipeline` 1건 | 에러인데 `message` 키로 200/400 모두 반환 |
| **E. `{error: 'code', detail: str}`** | `{"error": "invalid_request", "detail": "..."}` | `portfolio/views.py` 6건 | 코드+상세 분리 — B와 유사하나 평탄 |

### 형식 충돌 사례

`users/views.py`에서만 같은 ViewSet 안에 A·C·D 세 형식이 혼재:
- `users/views.py:707` — `{error: "stock is already in this watchlist"}` (400)
- `users/views.py:208` — `{message: "This stock is already in your favorites"}` (400)  ← 에러인데 `message`
- `users/views.py:117 (raise NotFound)` — DRF 자동 `{detail: "Not found."}` (404)

### DRF 기본 동작 vs 커스텀

`raise NotFound("Stock not found")` 41건 → DRF가 `{detail: "Stock not found"}`로 변환.
반면 `Response({"error": "..."}, status=404)` 45건 → `{error: "..."}` 그대로.
**같은 도메인 에러(404)인데 라우트 별로 키가 `detail` 또는 `error`로 갈림.**

특히 `stocks/views_fundamentals.py`는 동일 종목 not-found에 대해 `{error: ...}` 사용, `users/views.py`는 `raise NotFound()` 사용 → 클라이언트에서 동일 의미 에러를 두 분기로 처리해야 함.

---

## 페이지네이션 현황

### 전역 설정

`config/settings.py:341` REST_FRAMEWORK
```
'DEFAULT_PAGINATION_CLASS' 미설정
'PAGE_SIZE' 미설정
```
→ DRF의 **자동 페이지네이션 비활성**. 모든 목록은 명시적으로 처리해야 함.

### 적용 현황

| 분류 | 위치 | 방식 | 평가 |
|------|------|------|------|
| **DRF generics + 페이지네이션** | (없음) | — | `StockListAPIView`(`generics.ListAPIView`)도 `pagination_class` 미지정 → 무한 반환 |
| **DRF ViewSet 자동** | `news.NewsViewSet` (`ReadOnlyModelViewSet`) list 액션 | DRF default | 전역 미설정 + 클래스 미설정 → 사실상 무한 반환 |
| **수동 `Paginator`** | `users/views.py:602` Watchlist 목록 / `rag_analysis/views.py:796` 사용량 히스토리 | `django.core.paginator.Paginator` + 커스텀 wrapping (`{results, pagination}`) | 동작은 정상이나 다른 ViewSet과 응답 구조 불일치 |
| **offset/limit 수동** | `news/api/views.py:419-432` `all_news` | query param으로 offset/limit 받고 슬라이싱 | OK이지만 ViewSet 다른 액션과 일관성 없음 |
| **`[:N]` 단순 슬라이싱** | 다수 | hard-coded limit (e.g. `[:30]`, `[:50]`, `[:limit]`) | 클라이언트가 페이지 다음으로 갈 수 없음 |

### 무한 반환 위험 엔드포인트

페이지네이션 없이 전체/대량 데이터를 반환하는 곳:

| 엔드포인트 | 파일:라인 | 근거 |
|-----------|----------|------|
| `GET /api/v1/users/` (관리자 사용자 목록) | `users/views.py:90` | `User.objects.all()` → many=True |
| `GET /api/v1/news/` (NewsViewSet list) | `news/api/views.py:42-46` | `queryset = NewsArticle.objects.all()` — DRF 페이지네이션 미설정 |
| `GET /api/v1/news/trending/` | `news/api/views.py:327` | `[:limit]`만 적용, query param `limit` 검증 없음 (1억 입력 가능) |
| `GET /api/v1/validation/{symbol}/presets/` | `validation/api/views.py:421` | `PeerPreset.objects.filter(...)` 전체 |
| `GET /api/v1/validation/{symbol}/metrics/` | `validation/api/views.py:173` | 카테고리 전체 순회 |
| `GET /api/v1/stocks/` (StockListAPIView) | `stocks/views.py:75` | `pagination_class` 미설정, 전체 Stock |
| `GET /api/v1/serverless/movers` | `serverless/views.py:33` | `count`만 반환, 페이지 없음 |
| `GET /api/v1/chainsight/{symbol}/graph/` | `chainsight/api/views.py:54` | depth=3까지 그래프 전체 — 그래프 특성상 OK이나 max depth만 제한 |
| `GET /api/v1/stocks/eod/dashboard/` | `stocks/views_eod.py:48` | `snapshot.json_data` 전체 반환 — 의도적(JSON Baking) |

### `limit` 파라미터 검증 누락

- `news/api/views.py:230,298,367` — `int(request.query_params.get('limit', N))`에 상한 검증 없음 또는 100으로만 제한.
- `stocks/views_fundamentals.py:64-65` — `min(max(1, limit), 40)` 잘 적용됨. 모범 사례.
- `stocks/views_market_movers.py:46-47` — `min(max(1, limit), 20)` 잘 적용됨.

---

## 권고사항

### 우선순위 1 — 같은 라우트 내 형식 충돌 제거 (사용자 영향 큼)

1. `stocks/views_fundamentals.py`, `views_screener.py`, `views_exchange.py` — 성공 응답이 `{success, data, meta}` 래핑인데 에러 응답은 평탄 `{error}`. 에러도 `{success: False, error: {code, message}}`로 통일하거나, 래핑을 모두 걷어내고 평탄 응답으로 통일.
2. `validation/api/views.py:67,85` — body에 `error` 키가 있는데 status가 200. 클라이언트 계약 어긋남. 비즈니스 상태(`not_in_universe`, `no_data`)는 200 + `{status: '...', data: null}` 처럼 별도 키로 표현하거나 422/204로 변경.

### 우선순위 2 — 응답 형식 표준화 정책 수립

1. 한 가지 정책을 선택해 `DECISIONS.md`에 박는다. 후보:
   - **(A) DRF 표준 평탄 응답**: 성공은 serializer.data, 에러는 `{detail}` 또는 `{field: [errors]}`. → wrapping을 사용하는 serverless/rag_analysis/일부 stocks를 평탄화.
   - **(B) Envelope 일관**: 모든 응답을 `{success, data?, error?, meta}` 형식으로 통일. → DRF의 `EXCEPTION_HANDLER`를 커스텀 작성하여 `raise NotFound()`도 envelope으로 변환.
2. 의사결정 후 한쪽으로 일괄 통일. 현재 패턴 분포로 보면 **(A)가 마이그레이션 비용이 적음** (W 사용은 약 6개 파일).
3. 최소한 에러 키만이라도 통일: `{error: {code, message, details?}}` 표준을 두고 `raise NotFound("...")`도 같은 모양으로 변환되도록 `custom_exception_handler` 추가.

### 우선순위 3 — 하드코딩 상태 코드 → 상수

1. `sec_pipeline/views.py:40,44,46` → `status.HTTP_202_ACCEPTED`, `status.HTTP_200_OK`로 교체.
2. `serverless/views.py:2879` 등 일탈 1건 정리.
3. `portfolio/views.py`는 DRF 미사용이라 정수 그대로 둘 수밖에 없으나, 가독성을 위해 `from http import HTTPStatus` 도입 검토.
4. `portfolio/views.py:101` LLM budget 응답이 `/e1`은 503, `/e5`은 429 — 한쪽으로 통일 (RFC 6585에 따라 budget exceeded는 429가 더 적합).

### 우선순위 4 — 페이지네이션 정책

1. `config/settings.py`에 다음 추가 검토:
   ```
   REST_FRAMEWORK = {
     ...
     'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
     'PAGE_SIZE': 50,
   }
   ```
   단, 기존 평탄 응답이 `{...}`로 가정하고 있던 클라이언트가 깨지므로 **`pagination_class`를 ListAPIView 단위로만 적용** 권장.
2. **즉시 조치 필요**:
   - `users.Users.get()` — `User.objects.all()` 페이지네이션 또는 query 검색 강제.
   - `news.NewsViewSet` — `pagination_class = PageNumberPagination` 명시.
   - `stocks.StockListAPIView` — 동일.
3. `news/api/views.py:230` 등 `limit` query param에 `min(int(...), 100)` 가드 일괄 추가.

### 우선순위 5 — 비-DRF 라우트 리팩토링 (장기)

`portfolio/views.py`는 순수 Django + JsonResponse. DRF의 인증/권한/throttle/예외 핸들러가 적용되지 않아 다른 라우트와 정책이 다름. JWT 인증 통합·throttle 일관 적용을 위해 DRF APIView로 마이그레이션 검토 (Slice 단위 작업).

### 우선순위 6 — 검증 가능한 최소 가드

1. **계약 테스트**: `tests/test_response_envelope.py` 추가 — 각 라우트의 200/4xx 응답 키 셋이 정책과 일치하는지 자동 검증.
2. **OpenAPI 스펙 동기화**: `contracts/` 하위에 응답 스키마 명시. 클라이언트 타입 자동 생성으로 분기 누락 방지.

---

## 부록 — 참조 라인 인덱스

- 가장 일관된 W 패턴: `serverless/views.py:30-103, 164-269, 272-321`
- 가장 일관된 envelope 헬퍼: `rag_analysis/views.py:33-59` (`create_success_response`, `create_error_response`)
- W↔평탄 충돌 사례: `stocks/views_fundamentals.py:53-98, 113-157`
- 200 + error body 사례: `validation/api/views.py:64-67, 82-86`
- 하드코딩 상태 코드: `sec_pipeline/views.py:40,44,46`
- 페이지네이션 미설정 ListAPIView: `stocks/views.py:75-105`
- 수동 Paginator wrapping: `users/views.py:602-620`, `rag_analysis/views.py:776-826`
- 비-DRF JsonResponse: `portfolio/views.py:31-115`, `config/views.py:12-105`
