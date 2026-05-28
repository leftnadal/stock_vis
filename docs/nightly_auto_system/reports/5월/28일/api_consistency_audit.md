# API 응답 일관성 감사 보고서

- **생성일**: 2026-05-28
- **감사 범위**: Django views 28개 파일 (`views.py`, `views_*.py`, `*/api/views.py`)
- **모드**: 읽기 전용 (코드 수정 없음)
- **분석 단위**: `Response()` 반환 호출 약 456건 + 패턴 grep
- **이전 베이스라인**: `docs/nightly_auto_system/reports/5월/11일/api_consistency_audit.md`
- **분석 도구**: ripgrep 패턴 매칭 + 핵심 파일 정독 (stocks/views.py, news/api/views.py, portfolio/api/views.py, validation/api/views.py)

---

## 요약

### 🟢 5월 11일 대비 진보 (P0 권고 3건 모두 반영)

| # | 권고 (5/11) | 현 상태 (5/28) | 증거 |
|---|------------|---------------|------|
| P0-1 | `validation/api/views.py`의 200 에러 → 적절한 코드로 변경 | ✅ **완료** | `not_in_universe` → `422` (validation/api/views.py:67), `no_data` → `404` (validation/api/views.py:85) |
| P0-2 | `StockListAPIView` 페이지네이션 강제 | ✅ **완료** | `StockListPagination(PageNumberPagination)` 추가 — stocks/views.py:77-91, `page_size=50, max=200` |
| P0-3 | `NewsViewSet` 페이지네이션 적용 | ✅ **완료** | `NewsArticlePagination(PageNumberPagination)` 추가 — news/api/views.py:45-49, `page_size=20, max=100` |
| 추가 | `portfolio/views.py` DRF 미사용 → 표준화 | ✅ **완료** | Slice 13 #65에서 6개 endpoint 전수 제거 (portfolio/views.py:1-17, 비어 있음), `portfolio/api/views.py`로 단일화 — 모두 DRF `@api_view` + `Response()` |
| 추가 | `status=숫자` 하드코딩 축소 | 🟢 36 → 7 (-29) | `sec_pipeline/views.py` 3건 잔존 + `iron_trading/views.py` 4건 신규 추가 |

### 🟡 여전히 분열된 영역 (P1·P2)

1. **응답 envelope 분열은 변화 없음**: WRAP(`{success, data, error}`) vs RAW(`serializer.data` 직접 반환)이 앱 단위로 갈림. `serverless`/`rag_analysis`/`serverless_admin`만 WRAP 강제, 나머지는 RAW.
2. **에러 키 6가지 변종 (E1~E6)**: `error`/`detail`/`message` 혼재 그대로.
3. **수동 페이지네이션 4곳**: DRF `paginate_queryset()` 대신 `django.core.paginator.Paginator` 사용. 응답 메타 키도 4곳이 다 다름.
4. **`portfolio/api/views.py` DRY 위반**: 6개 endpoint(`coach_e1`~`coach_e6`)가 거의 동일한 try/except 블록을 50줄씩 복사. 향후 예외 추가 시 6곳 동시 수정 필요.

### 정량 지표 (이전 대비 변화)

| 항목 | 5/11 | 5/28 | 변화 |
|------|------|------|------|
| `Response()` 호출 총합 | 495 | **456** | -39 |
| `status.HTTP_*` 사용 | 248 | **208** | -40 |
| `status=<숫자>` 하드코딩 | 36 | **7** | **-29** 🟢 |
| `'error':` 키 사용 | 222 | **164** | -58 |
| `'message':` 키 사용 | 112 | **59** | -53 |
| `'detail':` 키 사용 | 27 | **3** | -24 |
| `'success': (True\|False)` 사용 | 138 | **19** | **-119** ⚠️ |
| `HTTP_201_CREATED` 사용 | 14 | **14** | ±0 |
| `PageNumberPagination` 클래스 정의 | 0 | **2** | **+2** 🟢 |
| `pagination_class =` 클래스 속성 | 0 | **2** | **+2** 🟢 |
| 수동 `Paginator` 사용 위치 | 5 | **4** | -1 |

> ⚠️ `'success'` 키 감소(-119)는 portfolio coach가 `portfolio/views.py`의 JsonResponse 패턴(`success: True/False` 포함)에서 `portfolio/api/views.py`의 RAW DRF로 이주하면서 dropped된 결과. **여전히 serverless/rag_analysis는 WRAP 유지** — 전체 통합은 미완.

---

## 앱별 응답 패턴 매트릭스

### 범례 (5/11과 동일)
- **Envelope**: `WRAP` = `{success, data, error}` / `RAW` = serializer/dict 직접 / `JR` = Django `JsonResponse` / `STD` = DRF 표준만
- **에러 키 ID**: E1=`{error: str}`, E2=`{success:False, error:{code,message}}`, E3=`{error+detail}`, E4=`serializer.errors`, E5=DRF 예외(`{detail}`), E6=`{error: code, message: str}`

| 앱 / 파일 | 줄 수 | 성공 envelope | 에러 키 | HTTP status | 페이지네이션 | 비고 |
|-----------|-------|--------------|--------|------------|-------------|------|
| `stocks/views.py` | 1030 | RAW | E1+E5 | `status.HTTP_*` | ✅ `StockListPagination` | **P0 반영** ✓ |
| `stocks/views_eod.py` | 136 | RAW | E1 | `status.HTTP_*` | n/a | 일관 |
| `stocks/views_market_movers.py` | 69 | RAW (serializer) | E1 | `status.HTTP_*` | n/a | 일관 |
| `stocks/views_screener.py` | 498 | WRAP↔RAW 혼재 | E4 | `status.HTTP_*` | 외부 limit | 같은 파일 내 분기 불일치 (변화 없음) ⚠️ |
| `stocks/views_fundamentals.py` | 305 | WRAP(일부)+RAW | E1 | `status.HTTP_*` | 외부 limit | 혼재 |
| `stocks/views_indicators.py` | 372 | RAW | E1 | `status.HTTP_*` | n/a | 일관 |
| `stocks/views_search.py` | 229 | RAW | E1 | `status.HTTP_*` | n/a | 일관 |
| `stocks/views_exchange.py` | 295 | WRAP-lite | E1 | `status.HTTP_*` | n/a | 부분 WRAP |
| `stocks/views_mvp.py` | 200 | RAW | (없음) | n/a | n/a | 단순 |
| `users/views.py` | 1088 | RAW | E1+E4+E5 | `status.HTTP_*` | 수동 `Paginator` (×2) | DRF 기본 + Django Paginator 혼용 (변화 없음) |
| `portfolio/views.py` | 16 | — (deprecated) | — | — | — | **Slice 13 #65에서 전수 제거 — 빈 모듈** ✅ |
| `portfolio/api/views.py` | 370 | RAW | **E1 (통일)** | `status.HTTP_*` | n/a | DRF 마이그레이션 완료 ✅. 다만 6 endpoint의 try/except 블록이 거의 복붙 — DRY 위반 |
| `news/api/views.py` | 2198 | RAW | E1+E5 | `status.HTTP_*` | ✅ `NewsArticlePagination` | **P0 반영** ✓ (단, `stock_news` action은 여전히 `{symbol, count, articles}` 자체 응답 — paginate 미경유) |
| `macro/views.py` | 410 | RAW (serializer) | E1 | `status.HTTP_*` | n/a | 광역 `except Exception → 500` 평탄화 잔존 |
| `serverless/views.py` | 2909 | **WRAP** | E2 | `status.HTTP_*` | 수동 offset/limit | 일관된 WRAP |
| `serverless/views_admin.py` | 691 | WRAP | E2 | `status.HTTP_*` | n/a | 일관 |
| `rag_analysis/views.py` | 772 | WRAP via helper | E2 | `status.HTTP_*` | 수동 `Paginator` (rag_analysis/views.py:689) | helper 강제 — 내부 일관 |
| `chainsight/api/views.py` | 814 | RAW | E1 | `status.HTTP_*` | 수동 page/page_size | 일관 |
| `chainsight/views.py` | 1 | — | — | — | — | 빈 모듈 (5/11과 동일) |
| `validation/api/views.py` | 561 | RAW | **E1+E6 (200 에러 해소)** | `status.HTTP_*` | n/a | **422/404로 수정 완료** ✅ |
| `validation/views.py` | 1 | — | — | — | — | 빈 모듈 |
| `sec_pipeline/views.py` | 51 | RAW | (없음) | **하드코딩 3회 (202, 200, 200)** | n/a | DRF지만 status 하드코딩 잔존 — 변화 없음 ⚠️ |
| `iron_trading/views.py` | 49 | RAW | **`error_body()` helper** | **하드코딩 4회 (400, 404, 503, 200)** | n/a | **신규 추가**. helper로 에러 일관성 확보. status 하드코딩 사용 |
| `metrics/views.py` | 3 | — | — | — | — | 미구현 |
| `graph_analysis/views.py` | 3 | — | — | — | — | 미구현 |
| `news/views.py` | 3 | — | — | — | — | 빈 모듈 |
| `config/views.py` | 104 | `JsonResponse` | (없음) | n/a | n/a | API root + healthcheck (변화 없음) |

### 핵심 관찰

- **WRAP 영역 변화 없음**: `serverless`, `serverless_admin`, `rag_analysis` 3개 앱만 envelope 강제. 나머지는 RAW.
- **portfolio 통합 ✅**: 이전 보고서의 "DRF 외부" 핫스팟이었던 `portfolio/views.py`(JsonResponse + 32회 하드코딩 status)가 완전히 deprecated되고 `portfolio/api/views.py`로 단일화됨.
- **iron_trading 신규 진입**: 새 앱으로 `error_body()` helper를 통한 에러 형식 통일을 시도했으나, 다른 앱과는 또 다른 형식. helper 패턴 자체는 모범적.
- **stocks/views_screener.py·views_fundamentals.py 미해결**: 같은 파일 내 분기별 WRAP/RAW 혼재(5/11 P1-6)는 그대로.

---

## HTTP 상태 코드 일관성

### 모듈 사용 vs 하드코딩

| 패턴 | 5/11 | 5/28 | 분포 (5/28) |
|------|------|------|-------------|
| `status.HTTP_*` | 248 | 208 | 17개 파일 |
| `status=<숫자>` 하드코딩 | 36 | **7** | `sec_pipeline/views.py` 3 + `iron_trading/views.py` 4 |

**판정**: 큰 진보 — portfolio가 32회 하드코딩에서 0으로, 전체 -29건. 잔존 7건은:

```
sec_pipeline/views.py:45  status=202   # 202 ACCEPTED
sec_pipeline/views.py:49  status=200
sec_pipeline/views.py:51  status=200
iron_trading/views.py:35  status=400
iron_trading/views.py:40  status=404
iron_trading/views.py:44  status=503
iron_trading/views.py:49  status=200
```

이들은 모두 `from rest_framework import status` 이미 import되어 있는 파일에서의 하드코딩이므로 **즉시 시정 가능한 1줄 패치 후보**.

### 201 Created 사용 (POST/create)

- 총 사용 횟수: 14건 (5/11과 동일)
- 분포: `rag_analysis` 4, `users` 6, `serverless` 3, `serverless_admin` 1.
- `portfolio/api/views.py`(6 endpoint, 모두 POST): **0건** — LLM 호출 RPC 의미이므로 200을 사용. 의도적이며 5/11 권고 P2-8(매핑 표준화)에서도 인정된 패턴.

### 200으로 잘못 보내진 에러 응답 ⚠️

- 5/11 베이스라인의 `validation/api/views.py` 2건은 모두 **수정 완료** (422 + 404).
- 새로 200 에러를 도입한 곳: **없음** (grep `status=status.HTTP_200_OK` 50건 head 확인 결과, 모두 정상 성공 응답).

### `portfolio/api/views.py`의 LLM 예외 매핑 — 통일됨 ✅

이전 5/11에서 지적된 "`/coach/e1`은 503, `/coach/e5`는 429" 불일치는 해소됨. **모든 6 endpoint가 동일 매핑**:

```python
LLMBudgetExceededError → 429 TOO_MANY_REQUESTS
LLMError               → 502 BAD_GATEWAY
Exception              → 500 INTERNAL_SERVER_ERROR
```

(portfolio/api/views.py:84-101 의 6회 반복)

---

## 에러 응답 형식

### 변종 카탈로그 (5/11 대비 변화)

| ID | 형식 | 5/11 사용처 | 5/28 사용처 변화 |
|----|------|------------|-------------------|
| **E1** | `{'error': '<msg>'}` | macro, stocks/* (대부분), chainsight, validation 일부 | + **portfolio/api/views.py** 추가 (6 endpoint) — DRF 표준 통일 |
| **E2** | `{'success': False, 'error': {'code', 'message'}}` | serverless, serverless_admin, rag_analysis | 동일 |
| **E3** | `{'error': '<code>', 'detail': '<msg>'}` | portfolio (deprecated) | **소멸** ✅ |
| **E4** | `serializer.errors` 또는 `{'error': serializer.errors}` 그대로 | users, stocks/views_screener | 동일 |
| **E5** | DRF 예외 → `{'detail': '...'}` | users, rag_analysis | 동일 |
| **E6** | `{'symbol': ..., 'error': '<code>', 'message': '<설명>'}` | validation 고유 | 동일 |
| **신규** | `error_body(code, message)` helper 결과 | — | iron_trading 신규 (실제 구조는 별도 확인 필요) |

### 불일치 사례 (5/11 대비 변화)

1. **"Not Found" 4가지 모양 잔존**:
   - `chainsight/api/views.py:71`: `{"error": f"Stock {symbol} not found in graph"}` + 404 (E1)
   - `stocks/views_fundamentals.py:78`: `{"error": "종목 {symbol}의 데이터를 찾을 수 없습니다."}` + 404 (E1)
   - `users/views.py`: DRF `raise NotFound` → `{"detail": "Not found."}` + 404 (E5)
   - `serverless/views.py`: `{'success': False, 'error': {'code': 'NOT_FOUND', 'message': ...}}` + 404 (E2)
   - **iron_trading/views.py:40 신규**: `error_body("snapshot_not_found", exc.message)` + 404
   - **변화**: 5가지로 증가.

2. **`serverless` 내부 코드 컨벤션 흔들림**: 변화 없음 (`INVALID_TYPE`, `NOT_FOUND`, `VALIDATION_ERROR`, `FORBIDDEN`).

3. **`serializer.errors`를 그대로 노출**: 5/11과 동일 (`users/views.py:109`, `stocks/views_screener.py:66`, `serverless/views.py:1071`).

4. **`detail` 키 이중 용도**: 5/11 27건 → 5/28 3건으로 급감 (portfolio E3 소멸 영향). 잔존 3건은 `users/views.py:2`, `config/views.py:1` — DRF 표준 예외 자동 동작이 주.

5. **i18n 혼재**: 한국어/영어 메시지 혼재 패턴은 변화 없음.

### DRF 기본 vs 커스텀

- `users/views.py`는 여전히 가장 "DRF 다운" — `raise NotFound`, `raise ParseError`, `serializer.errors` 반환.
- **portfolio/api/views.py 신규**: try/except 패턴으로 모든 예외를 `{"error": "..."}` E1 형식으로 래핑. 6 endpoint가 거의 동일하게 50줄씩 복사 — DRY 위반이나 형식 자체는 일관됨.
- `serverless`/`rag_analysis`는 여전히 helper로 envelope 강제하지만, 인증 실패는 여전히 DRF 기본 `{"detail": "..."}`로 반환 → 자체 envelope와 깨짐.

---

## 페이지네이션 현황

### DRF 페이지네이션 도입 ✅ (P0 권고 부분 반영)

**5/11 → 5/28**: DRF `pagination_class` 클래스 속성 **0 → 2건**.

```
stocks/views.py:91   pagination_class = StockListPagination     # P0-2 반영
news/api/views.py:60 pagination_class = NewsArticlePagination   # P0-3 반영
```

두 클래스 모두 `PageNumberPagination`을 확장:

| 클래스 | page_size | max_page_size | 위치 |
|--------|-----------|---------------|------|
| `StockListPagination` | 50 | 200 | stocks/views.py:77-81 |
| `NewsArticlePagination` | 20 | 100 | news/api/views.py:45-49 |

### 페이지네이션 부재 잔존 핫스팟

| 위치 | 문제 |
|------|------|
| `news/api/views.py` `NewsViewSet.stock_news` action (news/api/views.py:69-119) | `NewsViewSet`은 `pagination_class` 설정됐으나, `@action` 메서드인 `stock_news`는 직접 `Response(data)` 반환 — ViewSet 페이지네이션 미경유. 응답 본문은 `{symbol, count, articles}` 자체 envelope. **응답 크기 폭주 위험 잔존** (특정 종목 30일+ 누적 시) |
| `chainsight/api/views.py` `SignalFeedView` 등 | 수동 page/page_size 처리 잔존 (변화 없음) |
| `validation/api/views.py` | 카테고리 7개 한정으로 자연 제한, 위험 낮음 |

### 수동 페이지네이션 (Django Paginator) — 4곳

| 위치 | 응답 envelope |
|------|---------------|
| `rag_analysis/views.py:689-707` | `{success, data: {results, pagination}}` (helper) |
| `users/views.py:610-628` (Watchlist 목록) | `{results, pagination}` |
| `users/views.py:830-843` (Watchlist items) | `{results, pagination}` |
| `serverless/views.py` (offset/limit) | `{success, data: {count, results}}` |
| `chainsight/api/views.py:633-660` | `{page, page_size, total_count, has_next, results}` |

**판정**: 5/11 5곳 → 5/28 4곳 (rag_analysis 1곳 통합). 그러나 **응답 메타 키는 여전히 4가지 다른 형식**:
- `{pagination}` (users — 단일 nested 객체)
- `{count, results}` (serverless WRAP)
- `{page, page_size, total_count, has_next, results}` (chainsight)
- `{success: True, data: {results, pagination}}` (rag_analysis)

FE 입장에서 페이지네이션 유틸 함수 표준화 불가.

### ViewSet 페이지네이션 미적용

- `news/api/views.py`의 `NewsViewSet.list` 동작에는 `NewsArticlePagination`이 자동 적용되지만, **커스텀 action**(`stock_news`, `market` 등)은 직접 `Response()` 반환이라 페이지네이션을 우회한다.

---

## 권고사항

> **모든 권고는 코드 수정 없이 보고만 함.** 5/11 베이스라인의 P0 3건이 모두 반영되었으므로, 본 보고서는 P1·P2·P3로 시작한다.

### P1 — 응답 표준 합의 (앱 간 일관성, 미해결)

1. **`portfolio/api/views.py` DRY 리팩토링** (신규)
   - 6 endpoint(`coach_e1`~`coach_e6`)의 try/except 블록이 거의 동일한 구조로 50줄씩 복사됨. 단일 데코레이터(`@with_llm_error_handling`) 또는 공통 helper로 추출 권고.
   - 향후 새 예외 추가 시 6곳 동시 수정 필요 — 정합성 깨지기 쉬움.

2. **`sec_pipeline/views.py` + `iron_trading/views.py` status 하드코딩 해소**
   - 7건 모두 `from rest_framework import status` 가능한 환경 → `status.HTTP_*` 치환 1줄 패치.

3. **응답 envelope 단일화 결정 (재상정)** — 5/11 권고와 동일
   - 후보 A: WRAP 표준화 (`rag_analysis/serverless`의 helper를 공통 모듈로 승격)
   - 후보 B: RAW + DRF 표준 예외로 통일 (`serverless/rag_analysis` 의 WRAP 폐기)
   - 권고는 여전히 (B). portfolio가 (B)로 이주 완료한 것을 추진력으로.

4. **`stocks/views_screener.py` / `stocks/views_fundamentals.py` 내부 일관화**
   - 5/11 P1-6 권고 — 같은 파일 내 분기별 WRAP/RAW 혼재 그대로. 미해결.

5. **에러 키 단일화**
   - DRF 표준 `{'detail': ...}` 또는 객체형 `{'detail': {'code', 'message'}}`로 통일.
   - `serializer.errors` 노출 금지 → `field_errors`로 명시적 래핑.
   - iron_trading의 `error_body()` helper 형식과 다른 5가지 형식을 1개로 통일.

### P2 — 운영 표준

6. **`news/api/views.py` 커스텀 action에 페이지네이션 적용**
   - `stock_news`, `market` 등의 `@action`이 `NewsArticlePagination`을 우회. `self.paginate_queryset(qs)` 사용으로 통합 권고.

7. **수동 페이지네이션 응답 키 통일**
   - 5/11 P2-9와 동일. 4가지 메타 키 형식 → DRF `PageNumberPagination` 기본 `{count, next, previous, results}`로 통일.

8. **LLM 예외 → HTTP 매핑 (이미 portfolio에서 통일) 다른 LLM 호출 지점에도 적용**
   - portfolio의 `LLMBudgetExceededError → 429` 패턴을 `rag_analysis`/`serverless`의 LLM 호출에도 동일하게 강제.

### P3 — 도큐먼테이션·자동화

9. **`contracts/` 에 응답 schema 명시**
   - 5/11 P3-11과 동일. CLAUDE.md의 Contract-Driven Development 원칙. drf-spectacular OpenAPI 스펙에 표준 envelope·에러 코드 카탈로그 등재.

10. **CI 응답 컨벤션 lint**
    - `status=<숫자>` 금지 (예외: 명시 허용 목록)
    - `serializer.errors` 직접 반환 금지
    - `Response({...})` 내부 `'success'` 키 사용 여부 앱 단위 일관성 체크
    - **추가 룰**: `NewsViewSet` action에서 `self.paginate_queryset()` 미호출 시 경고 (커스텀 action 페이지네이션 우회 방지)

11. **`common-bugs.md` / KB 동기화**
    - 본 감사의 진보 사항 3건 (validation 422, StockListAPIView 페이지네이션, NewsViewSet 페이지네이션)을 LESSON으로 KB 큐에 추가.
    - 잔존 분열(envelope 6변종, 수동 페이지네이션 4가지) 도 LESSON 으로 등재 권고.

---

## 부록: 빠른 재현 명령

```bash
# Response 호출 분포 (5/28 = 456)
rg -n 'return Response\(' --type py -g '**/views*.py' | wc -l

# WRAP vs RAW 분포
rg -n "'success'\s*:\s*(True|False)" --type py -g '**/views*.py'

# 200으로 잘못 보낸 에러 (5/28에는 없음)
rg -n "'error'.*status=status\.HTTP_200_OK" --type py -g '**/views*.py' -A 1

# DRF 페이지네이션 사용 위치 (5/28 = 2)
rg -n 'PageNumberPagination|CursorPagination|LimitOffsetPagination|pagination_class' --type py -g '**/views*.py'

# status 하드코딩 위치 (5/28 = 7)
rg -n 'status=\d{3}' --type py -g '**/views*.py'

# 수동 Paginator 위치 (5/28 = 4)
rg -n 'Paginator\(|from django\.core\.paginator' --type py -g '**/views*.py'
```

---

## 5월 11일 vs 5월 28일 비교 요약

| 영역 | 5/11 상태 | 5/28 상태 | 진보도 |
|------|----------|----------|--------|
| `validation` 200 에러 | ⚠️ 2건 | ✅ 0건 (422/404로 수정) | 완료 |
| `StockListAPIView` 페이지네이션 | ❌ 없음 | ✅ `StockListPagination` | 완료 |
| `NewsViewSet` 페이지네이션 | ❌ 없음 | ✅ `NewsArticlePagination` | 완료 (단, action 미적용) |
| `portfolio` DRF 미사용 | ⚠️ JsonResponse + 32회 하드코딩 | ✅ DRF 마이그레이션 (`portfolio/api/views.py`) | 완료 |
| `status=숫자` 하드코딩 | 36건 | 7건 (sec_pipeline 3 + iron_trading 4) | 80% 해소 |
| 응답 envelope 분열 | WRAP↔RAW↔JR↔STD 4종 | WRAP↔RAW 2종 (JR/STD 소멸) | 부분 |
| 에러 키 변종 | 6종 (E1~E6) | 6종 + iron_trading helper | 무변화 |
| `stocks/views_screener.py` 내부 일관화 | ⚠️ 분기 혼재 | ⚠️ 분기 혼재 | 미해결 |
| 수동 페이지네이션 메타 키 통일 | 4종 | 4종 | 무변화 |
| LLM 예외 매핑 (portfolio) | 503↔429 충돌 | 통일 (429/502/500) | 완료 |

---

## 감사 종료 메모

- 본 보고서는 **읽기 전용**이며, 어떤 코드도 수정하지 않았다.
- 5/11 베이스라인의 **P0 권고 3건이 모두 반영**되어 가장 위험한 영역(200 에러 응답, DoS 표면 페이지네이션 미적용)은 해소됐다.
- 잔존 분열은 모두 P1·P2 영역이며, 단일 PR로 일괄 해결 불가 — 표준 결정(envelope WRAP/RAW 택1) 후 앱 단위 PR로 분리 진행 권고.
- 의도적으로 무시한 항목: `metrics/views.py`, `graph_analysis/views.py`, `news/views.py`, `chainsight/views.py`, `validation/views.py`, `portfolio/views.py` (모두 빈/placeholder), 미추적 백업 파일.
- 후속 작업: P1-1 (`portfolio/api/views.py` DRY), P1-2 (`sec_pipeline`/`iron_trading` 하드코딩 해소) 가 가장 저비용 고가치 — 각각 1~2시간 PR.
