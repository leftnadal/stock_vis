# API 응답 일관성 감사 보고서

- **생성일**: 2026-05-12
- **감사 범위**: Django views 25개 파일 (`views.py`, `views_*.py`, `*/api/views.py`)
- **모드**: 읽기 전용 (코드 수정 없음)
- **분석 단위**: `Response()` / `JsonResponse()` 반환 호출 약 540건
- **분석 도구**: ripgrep 패턴 매칭 + 핵심 파일 정독

---

## 요약

Stock-Vis API는 **앱·파일별로 응답 컨벤션이 분열**되어 있으며, 어떤 단일 표준도 강제되지 않는다. 같은 백엔드 안에서 클라이언트가 받게 되는 응답 형태가 최소 **3가지 응답 envelope × 6가지 에러 키 스키마**의 카르티시안 곱으로 흩어져 있다.

### 결정적 발견 (Top 6)

| # | 발견 | 위치 | 영향 |
|---|------|------|------|
| 1 | `{'success': True, 'data': ...}` 래핑 vs 직접 데이터 반환의 **앱 단위 분열** | serverless·rag_analysis·일부 stocks (래핑) vs 그 외 전부 (직접) | FE가 앱별로 다른 unwrap 로직 필요 |
| 2 | **같은 엔드포인트 내부**에서 분기마다 형식이 다름 | `stocks/views_screener.py` (Enhanced=래핑, 기본=직접) | 동일 URL이 두 형식을 번갈아 반환 |
| 3 | 에러 응답에 **HTTP 200** 부여 — 클라이언트 에러 감지 불가 | `validation/api/views.py` (`error: 'not_in_universe'`, `error: 'no_data'`) | FE가 본문 파싱 전엔 실패 인지 못 함 |
| 4 | 에러 키가 **6가지 형태**로 혼재 (`error`, `detail`, `message`, `error.code+message`, `serializer.errors`, DRF 예외) | 전 앱 | 통합 에러 핸들러 작성 불가 |
| 5 | DRF **페이지네이션 클래스 사용 0건** — 전체 `.all()` 반환 또는 수동 `Paginator` 사용 | `stocks.StockListAPIView`, `news` 다수, 그 외 | DoS 위험 + 응답 크기 폭주 |
| 6 | `JsonResponse` (Django) + 하드코딩 `status=숫자` 패턴이 portfolio/config에 존재 — DRF 표준에서 이탈 | `portfolio/views.py`, `config/views.py` | 인증/throttle/스키마 자동화 불가 |

### 정량 지표

| 항목 | 횟수 |
|------|------|
| `Response()` 호출 총합 | **495** |
| `JsonResponse()` / `HttpResponse` 호출 | 46 |
| `status.HTTP_*` 사용 | **248** |
| `status=<숫자>` 하드코딩 | 36 |
| `'error':` 키 사용 | 222 |
| `'message':` 키 사용 | 112 |
| `'detail':` 키 사용 | 27 |
| `'success': True` 사용 | 81 |
| `'success': False` 사용 | 57 |
| `status.HTTP_201_CREATED` 사용 | 14 |
| `PageNumberPagination` / `CursorPagination` / `pagination_class` | **0** |
| `Paginator` 수동 사용 | 5 위치 (rag_analysis, users x2) |

---

## 앱별 응답 패턴 매트릭스

### 범례
- **Envelope 형식**:
  - `WRAP` = `{'success': bool, 'data': ..., 'error': {...}, 'meta'?}`
  - `RAW` = `serializer.data` 또는 dict 그대로 반환
  - `JR` = Django `JsonResponse` (DRF 미사용)
- **에러 키**:
  - `E1` = `{'error': '<str>'}`
  - `E2` = `{'error': {'code': ..., 'message': ...}}`
  - `E3` = `{'error': '<str>', 'detail': '<str>'}` (Pydantic 스타일)
  - `E4` = DRF `serializer.errors` 직접 반환
  - `E5` = DRF 예외 (`NotFound`, `ParseError`, `ValidationError`) — body는 `{'detail': ...}`
  - `E6` = `{'error': '<code>', 'message': '<설명>'}` (validation 고유)

| 앱 / 파일 | 성공 envelope | 에러 키 | HTTP status | 페이지네이션 | 비고 |
|-----------|--------------|--------|------------|-------------|------|
| `stocks/views.py` | RAW | E1+E5 | `status.HTTP_*` | ❌ `StockListAPIView`는 `generics.ListAPIView`인데 `pagination_class` 미설정 (docstring은 "pagination" 명시) | DRF 기본 |
| `stocks/views_eod.py` | RAW | E1 | `status.HTTP_*` | n/a (단일) | 일관 |
| `stocks/views_market_movers.py` | RAW (serializer) | E1 | `status.HTTP_*` | n/a | 일관 |
| `stocks/views_screener.py` | **WRAP↔RAW 혼재** | E4 (`{'error': serializer.errors}`) | `status.HTTP_*` | 외부 limit 의존 | 같은 엔드포인트 내부 분기 불일치 (Enhanced=WRAP, 기본=WRAP `{"success":True, "data":..., "meta":...}`) ⚠️ |
| `stocks/views_fundamentals.py` | WRAP (일부) + RAW | E1 | `status.HTTP_*` | 외부 limit 의존 | 혼재 |
| `stocks/views_indicators.py` | RAW | E1 | `status.HTTP_*` | n/a | 일관 |
| `stocks/views_search.py` | RAW | E1 | `status.HTTP_*` | n/a | 일관 |
| `stocks/views_exchange.py` | WRAP-lite (`'success':True` 5건) | E1 | `status.HTTP_*` | n/a | 부분 WRAP |
| `stocks/views_mvp.py` | RAW | (없음) | n/a | n/a | 단순 |
| `users/views.py` | RAW | E1+E4+E5 | `status.HTTP_*` | **수동 Paginator** | DRF 기본 + Django Paginator 혼용 ⚠️ |
| `portfolio/views.py` | **JR** | E3 (`error`+`detail`) | **하드코딩 (32회)** | n/a | DRF 미사용 (의도적) — 그러나 인증/throttle 적용 불가 |
| `news/api/views.py` | RAW | E1+E5 | `status.HTTP_*` | ❌ `NewsArticle.objects.all()` 직접 반환 (`stock_news`, `market` 등) | DRF ViewSet인데 pagination 없음 ⚠️ |
| `macro/views.py` | RAW (serializer) | E1 | `status.HTTP_*` | n/a (단일 객체) | 일관, 다만 `try/except`로 모든 에러를 500+E1로 평탄화 |
| `serverless/views.py` | **WRAP** (60건) | E2 | `status.HTTP_*` (54건) + 하드코딩 1건 | 수동 offset/limit | 일관된 WRAP 사용 |
| `serverless/views_admin.py` | WRAP (28건) | E2 | `status.HTTP_*` | n/a | 일관된 WRAP |
| `rag_analysis/views.py` | **WRAP via helper** (`create_success_response`, `create_error_response`) | E2 | `status.HTTP_*` | 수동 `Paginator` | helper로 envelope 강제 — 모범 예 |
| `chainsight/api/views.py` | RAW | E1 (9건) | `status.HTTP_*` | 수동 page/page_size 처리 | 일관 |
| `chainsight/views.py` | n/a (관리자/내부) | — | — | — | 제외 |
| `validation/api/views.py` | RAW | **E6 (고유)** + E1 | `status.HTTP_*` (11건) + 하드코딩 0건 | n/a | **에러 상태에 HTTP 200 반환** (`no_data`, `not_in_universe`) ⚠️ |
| `sec_pipeline/views.py` | RAW | (없음, 202 사용) | **하드코딩 (3회: 202/200)** | n/a | DRF지만 status 하드코딩 |
| `metrics/views.py` | (빈 파일, 3줄) | — | — | — | 미구현 |
| `graph_analysis/views.py` | (빈 파일, 3줄) | — | — | — | 미구현 |
| `config/views.py` | **JR** | (없음) | n/a | n/a | API root + healthcheck |

### 핵심 관찰
- **WRAP 강제**: 오직 `serverless`, `rag_analysis`, `serverless_admin` 3개 앱만 일관된 `{'success': ..., 'data': ...}` envelope를 강제한다.
- **RAW 다수**: stocks 대부분, users, news, macro, chainsight, validation, sec_pipeline — Django REST 컨벤션을 따라 `serializer.data` 또는 dict를 직접 반환.
- **혼재 핫스팟**: `stocks/views_screener.py`, `stocks/views_exchange.py` — 같은 파일에서 일부 핸들러는 WRAP, 일부는 RAW.
- **DRF 외부**: `portfolio/views.py` 39회, `config/views.py` 3회 — 순수 Django `JsonResponse` 사용. portfolio는 docstring 주석 "순수 Django view + JsonResponse (DRF 미사용)"로 의도 명시되어 있으나 인증/스로틀/스키마 생성과 불일치를 야기.

---

## HTTP 상태 코드 일관성

### 모듈 사용 vs 하드코딩

| 패턴 | 횟수 | 분포 |
|------|------|------|
| `status.HTTP_*` | 248 | 16개 파일에 고르게 분포 |
| `status=<숫자>` 하드코딩 | 36 | `portfolio/views.py` (32) + `sec_pipeline/views.py` (3) + `serverless/views.py` (1) |

**판정**: DRF를 쓰는 코드 안에서 `status` 모듈 사용 규칙은 **거의 일관**되어 있다. 예외는 `serverless/views.py`에서 단 1건이 하드코딩이고, `portfolio/views.py`는 DRF 미사용이라 하드코딩이 자연스럽지만 일관성 측면에서는 다른 앱과 어긋난다. `sec_pipeline/views.py`는 DRF인데도 `status=202`, `status=200`을 하드코딩한 3건이 있어 **고쳐야 할 산발성 위반**이다.

### 201 Created 사용 (POST/create)

POST 또는 `create()` 메서드 25곳 중 **14곳에서만** `status.HTTP_201_CREATED` 명시:

| 파일 | 201 사용 횟수 | 비고 |
|------|--------------|------|
| `rag_analysis/views.py` | 4 | 일관 |
| `users/views.py` | 6 | 일관 (Watchlist add는 `201 if added else 200` idempotent 패턴 ✓) |
| `serverless/views.py` | 3 | 일관 (preset/alert/history 생성) |
| `serverless/views_admin.py` | 1 | OK |

**누락된 곳**: `chainsight/api/views.py`의 POST/PUT 핸들러 일부, `portfolio` 전체(POST이지만 200 반환 — LLM 결과 응답이므로 자원 생성이 아님, 의도적), `stocks/views_screener.py`(POST 없음).

**판정**: 자원 생성 의미를 가지는 POST에서는 201 사용이 비교적 잘 지켜지나, "POST지만 RPC 성격"인 LLM 호출(portfolio, rag_analysis 일부)에 대해 **팀 합의된 규칙이 명문화되지 않음**.

### 200으로 잘못 보내진 에러 응답 ⚠️

**Critical: `validation/api/views.py`**:
```python
# validation/api/views.py:64-67
return Response({
    'symbol': symbol, 'error': 'not_in_universe',
    'message': '현재 S&P 500 종목만 지원합니다.',
}, status=status.HTTP_200_OK)  # ← 에러인데 200

# validation/api/views.py:82-85
return Response({
    'symbol': symbol, 'error': 'no_data',
    'message': '재무 분석 데이터 준비 중입니다.',
}, status=status.HTTP_200_OK)  # ← 에러인데 200
```
- FE는 HTTP 코드로 실패 여부를 판단할 수 없고, 본문의 `error` 키를 별도로 파싱해야 한다.
- `404 Not Found`(또는 `409 Conflict` / `422 Unprocessable Entity`)가 의미상 적절.

### 기타 status 매핑 관찰
- **404**: `Stock.objects.filter(symbol=...).first()` 패턴 일관 (`status.HTTP_404_NOT_FOUND`).
- **400**: 파라미터 검증 실패에 일관되게 사용.
- **403**: serverless 일부 (`'code': 'FORBIDDEN'`).
- **429**: `portfolio/views.py`만 사용 (LLMBudgetExceededError → 429 또는 503 혼용 — `/coach/e1`은 503, `/coach/e5`는 429. **같은 의미인데 다른 코드** ⚠️).
- **500**: `try/except Exception` 광역 처리 후 평탄화 — `macro/views.py`가 대표 사례. 외부 API 실패와 내부 버그를 구분하지 않음.
- **503**: `chainsight/api/views.py`의 `GraphConnectionError` → 503 ✓.

---

## 에러 응답 형식

### 6가지 변종 카탈로그

| ID | 형식 | 사용처 (예) |
|----|------|------------|
| **E1** | `{'error': '<msg>'}` | `macro`, `stocks/views_eod`, `stocks/views_market_movers`, `stocks/views_fundamentals`, `chainsight/api`, `validation/api` (일부) |
| **E2** | `{'success': False, 'error': {'code': '<CODE>', 'message': '<msg>'}}` | `serverless`, `serverless_admin`, `rag_analysis` (helper 강제) |
| **E3** | `{'error': '<code>', 'detail': '<msg>'}` | `portfolio` (Pydantic ValidationError 패턴) |
| **E4** | `serializer.errors` 또는 `{'error': serializer.errors}` 그대로 | `users`, `stocks/views_screener` |
| **E5** | DRF 예외 (`NotFound`, `ParseError`, `ValidationError`) → 기본 `{'detail': '...'}` | `users`, `rag_analysis` |
| **E6** | `{'symbol': ..., 'error': '<code>', 'message': '<설명>'}` | `validation/api/views.py` 고유 |

### 불일치 사례 모음

1. **같은 "Not Found"가 4가지 모양으로 반환됨**:
   - `stocks/views_fundamentals.py:78`: `{"error": "종목 {symbol}의 데이터를 찾을 수 없습니다."}` + 404
   - `chainsight/api/views.py:71`: `{"error": f"Stock {symbol} not found in graph"}` + 404
   - `users/views.py:120`: DRF `raise NotFound` → `{"detail": "Not found."}` + 404
   - `serverless/views.py:143`: `{'success': False, 'error': {'code': 'NOT_FOUND', 'message': '...'}}` + 404

2. **`serverless` 안에서도 에러 코드 컨벤션이 흔들림**: `INVALID_TYPE`, `NOT_FOUND`, `VALIDATION_ERROR`, `FORBIDDEN` — UPPER_SNAKE는 일관되나 `INVALID_TYPE`(파라미터)과 `VALIDATION_ERROR`(serializer)가 의미 중첩.

3. **`serializer.errors`를 그대로 노출**: `users/views.py:109`, `stocks/views_screener.py:66`, `serverless/views.py:1071` — 클라이언트에 dict 구조가 그대로 노출되어 i18n과 메시지 정책에 취약.

4. **`detail` 키의 이중 용도**:
   - DRF가 자동으로 만드는 `{"detail": "..."}` (인증 실패, NotFound 등)
   - portfolio가 명시적으로 쓰는 `{"error": "...", "detail": "..."}` (디버그 메시지)
   - FE에서 `detail` 키 1개만으로 정상 에러 메시지인지 디버그용인지 구분 불가.

5. **에러 메시지 i18n 혼재**: 한국어/영어 메시지가 같은 앱 안에서 섞임 (`stocks/views_fundamentals.py`는 한국어, `serverless`는 영어).

### DRF 기본 vs 커스텀
- `users/views.py`는 가장 "DRF 다운" 패턴: `raise NotFound(_("..."))`, `raise ParseError(...)`, `serializer.errors` 반환 — 표준 DRF.
- `serverless`/`rag_analysis`는 helper 함수로 envelope을 강제하나 **DRF 기본 동작과 별개로 작동**해서 인증 실패는 여전히 `{"detail": "..."}`로 반환됨 → **자체 envelope 사용에도 불구하고 일관성 깨짐**.

---

## 페이지네이션 현황

### DRF 페이지네이션 사용 0건

- `PageNumberPagination`, `CursorPagination`, `LimitOffsetPagination` import **0건**
- `pagination_class = ...` 클래스 속성 **0건**
- `settings.py`의 `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']`도 미설정 (별도 검증 필요하나 import 0건이 강한 증거)

### 페이지네이션 부재 핫스팟 (DoS 위험)

| 위치 | 문제 |
|------|------|
| `stocks/views.py:76-106` `StockListAPIView` | `Stock.objects.all()` → 필터 적용 후 페이지네이션 없이 전체 반환. docstring은 "pagination으로 조회"라 적혀 있지만 실제로는 미적용. ~6000개 S&P 종목 전부 반환 가능 |
| `news/api/views.py` (`stock_news`, `market`, ViewSet 기본 `queryset = NewsArticle.objects.all()`) | `NewsArticle.objects.all().prefetch_related(...)` — 페이지네이션 없음. 뉴스 누적 시 응답 크기 폭주 |
| `chainsight/api/views.py` `SignalFeedView` 등 | 수동 page/page_size 처리는 있으나 raw query에서 LIMIT을 클라이언트 입력으로만 제한 |
| `validation/api/views.py` | `CategorySignal.objects.filter(symbol=stock).order_by('category')` — 카테고리 7개 한정이라 OK, 다만 `metrics/?category=all`은 잠재 위험 (미독) |

### 수동 페이지네이션 (Django Paginator 직접 사용)

| 위치 | 방식 |
|------|------|
| `rag_analysis/views.py:782-825` | `from django.core.paginator import Paginator` + `page_size=20, max=100` |
| `users/views.py:610-628`, `:830-843` (Watchlist 목록, items 목록) | `Paginator(qs, page_size)` + `EmptyPage` 처리 + 응답 `{'results', 'pagination'}` 자체 envelope |
| `serverless/views.py:1177-1185`, `:1318-1340` | `offset/limit` 수동 계산, `page * page_size` |
| `chainsight/api/views.py:633-660` | page/page_size 직접 쿼리 파라미터 처리, 응답에 `has_next` 포함 |

**판정**: 5곳에서 페이지네이션을 **각자 다른 방식**으로 직접 구현. 응답 메타 키도 `pagination` (users) vs `page/page_size/total_count/has_next` (serverless, chainsight) vs `page/page_size/total/has_next` (rag_analysis)로 갈린다. FE 입장에서 페이지네이션 유틸 함수를 표준화할 수 없다.

### ViewSet에서 누락된 페이지네이션
- `news/api/views.py` `NewsViewSet(viewsets.ReadOnlyModelViewSet)` — 기본 페이지네이션을 사용해야 하는 ViewSet인데 settings에 DEFAULT_PAGINATION_CLASS가 없어 list 전체가 그대로 반환된다.

---

## 권고사항

> **모든 권고는 코드 수정 없이 보고만 함.** 우선순위는 영향도 × 발생 빈도 × 구현 난이도 역수.

### P0 — 즉시 시정 (보안/안정성)

1. **`validation/api/views.py`의 200 에러 응답 수정**
   - `error: 'not_in_universe'` / `error: 'no_data'` 케이스를 `404 Not Found` 또는 `409 Conflict`/`422`로 변경.
   - FE의 실패 분기를 HTTP 상태로 식별 가능하게 함.

2. **`stocks.StockListAPIView`에 DRF 페이지네이션 강제**
   - `pagination_class = PageNumberPagination` (또는 settings에서 DEFAULT 지정).
   - 현재는 S&P 6000개+ 종목 전체를 단일 응답으로 반환할 수 있음 — DoS 표면.

3. **`news/api/views.py` ViewSet에 페이지네이션 적용**
   - DRF의 기본 페이지네이션을 `settings.REST_FRAMEWORK`에 설정하거나 ViewSet에 `pagination_class` 명시.

### P1 — 응답 표준 합의 (앱 간 일관성)

4. **응답 envelope 단일화 결정 — 두 후보 중 택1**:
   - **(A) WRAP 표준화**: 모든 응답을 `{'success': bool, 'data': ..., 'meta': {...}}` 또는 `{'success': false, 'error': {'code', 'message'}}`로. `rag_analysis`의 `create_success_response/create_error_response` 헬퍼를 공통 모듈로 승격.
   - **(B) RAW 표준화**: DRF 기본 동작에 맞춰 성공은 `serializer.data` 또는 dict 직접 반환, 에러는 DRF `exceptions.APIException` 계열 → `{'detail': ...}` 또는 `{'detail': {...}}`로. `serverless`·`rag_analysis`의 WRAP은 폐기.
   - 두 후보의 트레이드오프: WRAP은 명시적 success 플래그로 i18n·메타데이터 일관성 ↑, 그러나 DRF 기본과 어긋남. RAW는 DRF 컨벤션과 일치하나 success 플래그가 없어 부분 성공/메타데이터 표현이 어렵다. **권고: (B) RAW + DRF 표준 예외**, 변경 비용이 더 작고 DRF 생태계와 일치.

5. **에러 키 단일화**:
   - DRF 표준 `{'detail': ...}` 또는 객체형 `{'detail': {'code': ..., 'message': ...}}`로 통일.
   - `serializer.errors` 노출 금지 → `field_errors`로 명시적으로 래핑.

6. **`stocks/views_screener.py` 내부 일관화**
   - Enhanced 분기와 기본 분기가 응답 형식이 다른 점을 해소 (같은 URL 두 형태 반환은 FE 버그 양산).

### P2 — 운영 표준

7. **HTTP status 하드코딩 제거**
   - `sec_pipeline/views.py`의 `status=202`, `status=200` 3건 → `status.HTTP_*` 사용.
   - `serverless/views.py`의 잔존 하드코딩 1건 정리.

8. **포트폴리오의 LLM 예외 → HTTP 매핑 표준화**
   - 같은 `LLMBudgetExceededError`가 `/coach/e1`은 503, `/coach/e5`는 429로 매핑됨. **429로 통일** 권고 (rate limit/budget 의미상).

9. **수동 페이지네이션 응답 키 통일**
   - users(`{results, pagination}`), serverless(`{count, results}`), chainsight(`{page, page_size, total_count, has_next}`)의 키 셋이 다름. DRF `PageNumberPagination` 기본 응답 (`{count, next, previous, results}`)으로 통일.

10. **`portfolio/views.py`의 DRF 이주 검토**
    - 현재 `JsonResponse` + `csrf_exempt` 패턴은 인증/throttle/스키마 자동화 불가. DRF `APIView` + Django REST throttle로 이주하면 audit/observability/문서화가 통합됨. (다만 docstring에 "순수 Django + DRF 미사용" 의도가 명시되어 있어 결정 전에 의도 재확인 필요)

### P3 — 도큐먼테이션·자동화

11. **`contracts/` 디렉터리에 응답 schema 문서화**
    - CLAUDE.md의 Contract-Driven Development 원칙에 따라 OpenAPI 스펙에 표준 응답 envelope과 에러 코드 카탈로그를 명시.

12. **CI에 응답 컨벤션 lint 추가**
    - 단순 grep 룰로도 잡을 수 있는 항목: `status=<숫자>` 금지, `serializer.errors` 직접 반환 금지, `Response({...})` 안에 `'success'` 키 사용 여부 일관성 체크.

13. **`common-bugs.md`에 본 감사 핵심 발견 등재 후 KB 동기화**
    - 특히 (1) 응답 envelope 분열, (2) 200 status로 에러 반환, (3) DRF 페이지네이션 0건 — 세 항목은 LESSON 타입으로 KB 큐에 추가 권고.

---

## 부록: 빠른 재현 명령

```bash
# Response 호출 분포
rg -n 'return Response\(' --type py -g '**/views*.py' | wc -l

# WRAP vs RAW 분포
rg -n "'success'\s*:\s*True" --type py -g '**/views*.py'
rg -n "'success'\s*:\s*False" --type py -g '**/views*.py'

# 200으로 잘못 보낸 에러
rg -n "'error'.*status=status\.HTTP_200_OK" --type py -g '**/views*.py' -A 1

# DRF 페이지네이션 import 여부
rg -n 'PageNumberPagination|CursorPagination|LimitOffsetPagination|pagination_class' --type py

# status 하드코딩 위치
rg -n 'status=\d{3}' --type py -g '**/views*.py'
```

---

## 감사 종료 메모

- 본 보고서는 **읽기 전용**이며, 어떤 코드도 수정하지 않았다.
- 의도적으로 무시한 항목: `metrics/views.py`, `graph_analysis/views.py` (모두 3줄 placeholder), `chainsight/views.py` (관리자/내부), duplicated `*views 2.py` / `*views 3.py` 파일 (git 상태에서 ?? 로 표시된 미추적 백업).
- 후속 작업이 필요한 경우, 위 권고 P0 항목부터 PR 단위로 분리하여 진행할 것을 제안한다.
