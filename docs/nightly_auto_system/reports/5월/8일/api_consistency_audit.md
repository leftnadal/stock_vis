# API 응답 일관성 감사 보고서

**작성일**: 2026-05-08
**감사 대상**: 25개 views.py 파일 (Django 앱 전체)
**범위**: 응답 envelope, HTTP status code, 에러 형식, 페이지네이션
**모드**: 읽기 전용 — 코드 수정 없음

---

## 요약

`Response()` 호출 530건을 정량 분석한 결과, **앱별로 4가지 응답 패턴이 혼재**하고 있어 클라이언트 통합/유지보수에 일관성 문제가 확인되었다.

### 핵심 통계

| 측정 항목 | 수치 | 설명 |
|---|---|---|
| `Response()` 호출 총합 | **530회** | 20개 파일 |
| `{'success': True}` envelope 사용 | **81회 / 6개 파일** | stocks/screener·fundamentals·exchange, serverless, rag_analysis |
| `status=status.HTTP_*` (DRF 상수) | **248회 / 16개 파일** | 권장 패턴 |
| `status=400/500` (하드코딩 정수) | **36회 / 3개 파일** | portfolio, serverless, sec_pipeline |
| `'error'` 키 응답 | **159회 / 12개 파일** | 가장 흔한 에러 키 |
| `'message'` 키 응답 | **112회 / 10개 파일** | 두 번째로 흔함 |
| `'detail'` 키 응답 | **27회 / 3개 파일** | DRF 표준이지만 portfolio 위주 |
| `status.HTTP_201_CREATED` 사용 | **14회 / 5개 파일** | 적절히 사용됨 |
| `PageNumberPagination` 등 import | **0회** | **페이지네이션 전무** |
| `DEFAULT_PAGINATION_CLASS` 설정 | **없음** | `config/settings.py:347` 명시적 미루기 |

### Top-3 발견사항

1. **응답 envelope 4종 혼재** — 직접 데이터, `{success, data, meta}`, `{success, data, error, meta}`, `JsonResponse(dict)`가 동일 프로젝트 내 공존.
2. **`portfolio/` 앱은 DRF 미사용** — 순수 `JsonResponse` + 하드코딩 `status=400/500/503` 사용. 다른 14개 앱과 스타일 분리.
3. **페이지네이션 완전 부재** — `User.objects.all()`, `News.objects.all()`, `Stock.objects.all()` 등 무제한 응답 다수. `settings.py:347`에 "audit P0 #14는 별도 PR에서 처리"라는 코멘트로 미해결 부채 명시.

---

## 앱별 응답 패턴 매트릭스

표기:
- `RAW`: 직렬화 결과를 직접 반환 (DRF 기본 패턴)
- `WRAP`: `{"success": bool, "data": ..., "meta": ...}` envelope
- `WRAP+E`: WRAP에 `"error": {"code", "message"}` 구조 추가 (rag_analysis 헬퍼)
- `JR`: `JsonResponse` 사용 (DRF 비사용)

| 앱 | 파일 | Response 수 | 응답 envelope | 에러 키 | status 사용 |
|---|---|---:|---|---|---|
| **portfolio** | `views.py` | 32 | **JR** (`{"error", "detail"}`) | `error` + `detail` | **하드코딩 400/429/500/503** |
| **users** | `views.py` | 56 | **RAW** + 일부 message | `error`, `message`, `detail` | `status.HTTP_*` |
| **stocks** | `views.py` | 25 | **RAW** | `error`, `message` | `status.HTTP_*` |
| stocks | `views_screener.py` | 15 | **WRAP** (`success`/`data`/`meta`) | `error` | `status.HTTP_*` |
| stocks | `views_fundamentals.py` | 15 | **WRAP** | `error` | `status.HTTP_*` |
| stocks | `views_exchange.py` | 13 | **WRAP** | `error` | `status.HTTP_*` |
| stocks | `views_market_movers.py` | 2 | **RAW** | `error` | `status.HTTP_*` |
| stocks | `views_eod.py` | 6 | **RAW** | `error` | `status.HTTP_*` |
| stocks | `views_indicators.py` | 8 | **RAW** | `error` | `status.HTTP_*` |
| stocks | `views_search.py` | 10 | **RAW** | `error` | `status.HTTP_*` |
| stocks | `views_mvp.py` | 4 | **RAW** | (없음) | 없음 |
| **macro** | `views.py` | 26 | **RAW** | `error` | `status.HTTP_*` |
| **news** | `api/views.py` | 61 | **RAW** | `error`, `message` | `status.HTTP_*` |
| **chainsight** | `api/views.py` | 20 | **RAW** | `error` | `status.HTTP_*` |
| **validation** | `api/views.py` | 23 | **RAW** | `error`, `message` | `status.HTTP_*` |
| **rag_analysis** | `views.py` | 38 | **WRAP+E** (헬퍼 함수) | `error.code`, `error.message` | `status.HTTP_*` |
| **serverless** | `views.py` | 126 | **혼재** (RAW + WRAP) | `error` (string + nested object) | 대부분 `status.HTTP_*`, 1회 하드코딩 |
| serverless | `views_admin.py` | 45 | **WRAP** 일부 | `error`, `message` | `status.HTTP_*` |
| **sec_pipeline** | `views.py` | 3 | **RAW** | `message` | **하드코딩 200/202** |
| **config** | `views.py` | 2 | **RAW** | (없음) | 없음 |
| metrics | `views.py` | 0 | (빈 파일) | — | — |
| graph_analysis | `views.py` | 0 | (빈 파일) | — | — |
| chainsight | `views.py` | 0 | (빈 파일) | — | — |
| validation | `views.py` | 0 | (빈 파일) | — | — |
| news | `views.py` | 0 | (빈 파일) | — | — |

### 패턴별 그룹 (요약)

| 패턴 | 앱/파일 | 일관성 |
|---|---|---|
| **RAW + DRF 표준** (다수) | users, stocks/views, macro, news, chainsight, validation, stocks/eod·indicators·search·mvp·market_movers, config | 가장 일반적 |
| **WRAP envelope** (일부) | stocks/screener, fundamentals, exchange, serverless, serverless/admin (혼재) | 같은 stocks 앱 내에서도 분리 |
| **WRAP+E 헬퍼** | rag_analysis (`create_success_response`/`create_error_response`) | 모듈 내부 일관 |
| **JsonResponse + 하드코딩** | portfolio (Slice 1~5 coach API 전체) | 다른 앱과 완전 분리 |

### 가장 심각한 불일치 — `serverless/views.py` 내부 혼재

`serverless/views.py`(126개 Response)에는 같은 파일 안에서 두 가지 envelope이 공존한다:

- WRAP 패턴: `market_movers_api`, `screener_alerts`, `extract_relations_from_news` 등
  ```python
  return Response({'success': True, 'data': {...}})
  return Response({'success': False, 'error': {'code': '...', 'message': '...'}}, status=...)
  ```
- RAW + 일반 dict 패턴: 다수의 GET endpoint
  ```python
  return Response(serializer.data)
  return Response({'error': '...'}, status=...)
  ```

또한 line 2887에는 유일한 하드코딩 `status=400`이 존재하여 같은 파일 내에서도 status 표기 통일이 깨져 있다.

---

## HTTP 상태 코드 일관성

### `status.HTTP_*` vs 하드코딩 정수 비교

| 표기 방식 | 파일 수 | 호출 수 |
|---|---:|---:|
| `status=status.HTTP_*` (권장) | 16 | 248 |
| `status=400/401/404/500` (하드코딩) | 3 | 36 |

#### 하드코딩이 발견된 파일

1. **`portfolio/views.py`** — 32회 (전체)
   - `status=400`, `status=429`, `status=500`, `status=503`
   - DRF를 사용하지 않으므로 `rest_framework.status` import 자체가 없음.
   - `JsonResponse(dict, status=int)` 패턴 일관 (내부 일관성은 있음).
2. **`sec_pipeline/views.py`** — 3회
   - `status=200`, `status=202` — DRF Response 사용에도 하드코딩.
3. **`serverless/views.py`** — 1회 (line 2887)
   - 거의 모든 호출은 `status.HTTP_*`인데 한 군데만 `status=400` (코드 일관성 결함).

### 201 Created 사용 현황 — 양호

생성 endpoint에서 201 CREATED가 적절히 사용되고 있다 (총 14회):

| 파일 | line | 컨텍스트 |
|---|---:|---|
| users/views.py | 107, 295, 639, 731 | 회원가입, Portfolio create, Watchlist 생성, WatchlistItem 생성 |
| users/views.py | 918, 1040 | 동적 분기 (`status.HTTP_201_CREATED if added/created else HTTP_200_OK`) — 모범 |
| serverless/views.py | 1065, 1435, 1826 | Alert 생성 |
| serverless/views_admin.py | 568 | Admin 액션 트리거 |
| rag_analysis/views.py | 87, 167, 349, 459 | DataBasket / Session / Message 생성 |

> 단, **portfolio coach API**는 POST + 결과 생성임에도 항상 `status=200`을 반환한다. (LLM 결과는 자원 생성이 아니라 계산 결과로 해석한 듯하나, 다른 앱의 POST 패턴과 다름.)

### 4xx/5xx 분포 (추출 결과)

| 코드 | 사용 위치 (대표) |
|---|---|
| 400 BAD_REQUEST | 모든 앱에서 사용 — 입력 검증 실패 |
| 401 UNAUTHORIZED | users/views.py:173 (LogIn 실패) |
| 403 FORBIDDEN | (직접 발견 없음 — DRF permission_classes가 자동 처리) |
| 404 NOT_FOUND | stocks/views_fundamentals.py:79, validation, chainsight 등 다수 |
| 429 TOO_MANY_REQUESTS | portfolio/views.py (`budget_exceeded`) |
| 500 INTERNAL_SERVER_ERROR | macro/views.py 8회, stocks/views_search.py 등 |
| 503 SERVICE_UNAVAILABLE | stocks/views_exchange.py:59, stocks/views_search.py:53 |

---

## 에러 응답 형식

### 키 사용 빈도

| 에러 키 | 파일 수 | 호출 수 | 형식 예 |
|---|---:|---:|---|
| `error` | 12 | 159 | `{"error": "메시지"}` 또는 `{"error": {"code": "X", "message": "Y"}}` |
| `message` | 10 | 112 | `{"message": "텍스트"}` (성공/에러 모두) |
| `detail` | 3 | 27 | DRF 표준 — 그러나 portfolio가 비정형으로 사용 |

### 형식 불일치 사례

#### 1. `error` 키의 두 가지 구조

```python
# 단순 문자열 (대부분의 앱: stocks, users, macro, chainsight, validation)
return Response({"error": "Stock not found"}, status=404)

# 중첩 구조 (serverless, rag_analysis)
return Response({
    "success": False,
    "error": {"code": "INVALID_TYPE", "message": "..."}
}, status=400)
```

→ 클라이언트가 `error.message`인지 `error` 자체인지 매번 분기해야 함.

#### 2. DRF 표준 `detail` 미사용

DRF의 `APIException`/`NotFound`/`ValidationError` 등은 자동으로 `{"detail": "..."}` 응답을 생성하지만, 대부분의 코드는 **수동으로 `error` 키**를 만들고 있다.

```python
# users/views.py 다수
raise NotFound("Stock not found")  # → DRF 자동 {"detail": "Stock not found"}
return Response({"error": "..."}, status=...)  # 수동 형식
```

같은 `users/views.py`(line 14, 99, 120) 안에서 `ParseError`, `NotFound`, `ValidationError` 같은 DRF exception(자동 `detail` 생성)과 수동 `Response({'error': ...})`가 섞여 있다.

#### 3. portfolio의 `error` + `detail` 결합

`portfolio/views.py`는 자체 패턴을 채택:

```python
return JsonResponse(
    {"error": "invalid_request", "detail": str(exc)[:500]},
    status=400,
)
```

여기서 `error`는 에러 코드(machine-readable), `detail`은 사람이 읽는 메시지로 사용. 의도는 좋으나 다른 앱과 다른 의미론적 구조.

#### 4. `message`의 이중 의미

`message` 키는 성공·에러 두 가지 용도로 사용된다:

```python
# 성공 (users/views.py:222)
return Response({"message": "Stock added to favorites", "stock": ...})

# 에러 (sec_pipeline/views.py:44)
return Response({'symbol': symbol.upper(), 'status': 'collecting',
                 'message': 'Collection triggered.'}, status=202)

# 에러 (serverless WRAP+E)
{"error": {"code": "X", "message": "..."}}
```

같은 키가 컨텍스트에 따라 의미가 달라져 클라이언트 핸들링이 어려워진다.

---

## 페이지네이션 현황

### 결론: DRF 페이지네이션이 전혀 사용되지 않음

| 점검 항목 | 결과 |
|---|---|
| `config/settings.py`의 `DEFAULT_PAGINATION_CLASS` | **미설정** (line 348~362 REST_FRAMEWORK dict) |
| `PageNumberPagination` import | 0건 |
| `CursorPagination` import | 0건 |
| `LimitOffsetPagination` import | 0건 |
| `pagination_class = ...` 명시 | 0건 |
| `generics.ListAPIView` 사용 | 1건 (`stocks/views.py:75 StockListAPIView`) — pagination_class 없음 |

### 명시적 인지된 부채

`config/settings.py:347`에 다음과 같은 코멘트가 있다:

> `# audit P0 #14 (페이지네이션 표준)는 별도 PR에서 처리 — 응답 envelope 결정이 선결 조건`

→ 페이지네이션 부재는 **알려진 P0 결함**이며, envelope 표준화가 선결 조건으로 묶여 있다.

### 무제한 list 반환이 의심되는 endpoint

| 파일:라인 | 엔드포인트 | 위험 |
|---|---|---|
| `users/views.py:92` | `User.objects.all()` (관리자용) | 사용자 수만큼 직렬화 |
| `users/views.py:264` | `Portfolio.objects.filter(user=...)` | 사용자별 무제한 |
| `users/views.py:193` | `user.favorite_stock.all()` | 즐겨찾기 무제한 |
| `news/api/views.py:50` | `NewsArticle.objects.all().prefetch_related('entities')` | 뉴스 무제한 (ViewSet의 queryset) |
| `news/api/views.py:95~105` | 7일치 `articles.distinct().order_by(...)` 후 전체 직렬화 | 종목당 수백~수천 가능 |
| `stocks/views.py:75 StockListAPIView` | `Stock.objects.all()` | S&P 500 = 500건, 향후 확장 시 위험 |
| `stocks/views.py:190` (`StockSearchAPIView`) | `[:20]` 슬라이싱 | 안전하지만 페이지네이션 부재 |
| `stocks/views_eod.py:79` | `[:50]` 슬라이싱 | 안전하지만 페이지네이션 부재 |
| `stocks/views_eod.py:119` | `[:7]` 슬라이싱 | 작아서 무방 |
| `validation/api/views.py:80` | `CategorySignal.objects.filter(...)` | 카테고리 7개로 한정 — OK |
| `rag_analysis/views.py:76` | `DataBasket.objects.filter(user=...).prefetch_related('items')` | 사용자당 무제한 |

### 클라이언트 측 슬라이싱 의존

다수의 endpoint는 페이지네이션 대신 코드 내부에서 `[:N]` 슬라이싱으로 응답 크기를 제한한다(`[:5]`, `[:10]`, `[:20]`, `[:50]`). 이는:

- 즉각적인 응답 폭주 방지에는 효과적
- 클라이언트가 다음 페이지를 가져올 방법 없음
- 정렬/필터링 후 잘리므로 결과 누락 가능
- 무한 스크롤·테이블 ListView UX 불가능

---

## 권고사항

### 우선순위 P0 (응답 envelope 통일)

1. **`shared/responses.py`(가칭) 헬퍼 모듈 신설**
   - `success(data, meta=None, status=200)` 와 `error(code, message, status=400, details=None)` 두 함수 표준화.
   - 이미 `rag_analysis/views.py:35-61`에 모범 구현(`create_success_response`/`create_error_response`)이 존재 — 이를 프로젝트 전역 모듈로 승격.
2. **envelope 결정**: 다음 중 1개로 통일하고 `DECISIONS.md`에 명시
   - **Option A (RAW)**: DRF 표준에 맞춤 — 변경 코스트 최소(81개 WRAP 호출 제거)
   - **Option B (WRAP)**: `{success, data, meta, error}` 헬퍼 강제 — 449개 RAW 호출 마이그레이션 필요
3. **portfolio coach API를 DRF로 통합**: 32개 `JsonResponse` 호출을 동일 envelope으로 정렬.

### 우선순위 P1 (status 코드 정상화)

4. **하드코딩 status 제거**: `portfolio/views.py`는 DRF로 마이그레이션 시 자동 해결, `serverless/views.py:2887`과 `sec_pipeline/views.py` 4건은 즉시 `status.HTTP_*`로 교체.
5. **`message` 키 의미 분리**: 성공 메시지는 `data.message` 또는 `meta.message`로, 에러 메시지는 `error.message`로 격리.

### 우선순위 P2 (페이지네이션 도입)

6. **`DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE` 설정** — envelope 결정 후 즉시 추가 (settings.py:347 코멘트가 가리키는 P0 #14 부채 해소).
7. **`generics.ListAPIView` / `viewsets.ReadOnlyModelViewSet` 우선 적용**: `stocks/views.py:75 StockListAPIView`, `news/api/views.py:47 NewsViewSet`에 `pagination_class` 지정.
8. **수동 list endpoint 마이그레이션**: `User.objects.all()`, `Portfolio.objects.filter(...)`, `DataBasket.objects.filter(...)` 등에 `Paginator` 또는 DRF pagination 적용.

### 우선순위 P3 (DRF exception 활용)

9. `Response({"error": "..."}, status=...)` 수동 패턴을 가능한 곳에서 `raise NotFound(...)`, `raise ValidationError(...)`, `raise ParseError(...)`로 대체. 그러면 `detail` 키로 자동 통일됨.
10. `users/views.py`처럼 한 파일 안에서 DRF exception과 수동 Response가 섞여 있는 곳을 우선 정리.

### Post-fix 검증

- 모든 `Response()` 호출을 정규식으로 grep해 envelope 일관성 자동 검증하는 pre-commit hook(또는 ruff plugin) 도입.
- contracts/ OpenAPI 스펙에 envelope schema를 강제 정의하고, `drf-spectacular` 응답 schema 검증.

---

## 부록 A — 분석 명령

```bash
# Response 호출 카운트
grep -rE "Response\(" --include="views*.py"

# Success envelope 사용
grep -rE "'success':\s*True" --include="views*.py"

# 하드코딩 status
grep -rE "status=\d{3}" --include="views*.py"

# DRF 표준 status
grep -rE "status=status\." --include="views*.py"

# 페이지네이션 import (0건 확인)
grep -rE "PageNumberPagination|CursorPagination|LimitOffsetPagination" --include="*.py"
```

## 부록 B — 빈 views.py 파일 (미구현 또는 ViewSet 분리)

| 파일 | 비고 |
|---|---|
| `chainsight/views.py` | API는 `chainsight/api/views.py`로 분리 |
| `news/views.py` | API는 `news/api/views.py`로 분리 |
| `validation/views.py` | API는 `validation/api/views.py`로 분리 |
| `metrics/views.py` | 내부 서비스용으로 view 미작성 |
| `graph_analysis/views.py` | 모델/서비스만 구현, API 미구현 (CLAUDE.md) |

---

**감사 종료** — 코드 변경 0건. 모든 권고사항은 후속 PR에서 처리.
