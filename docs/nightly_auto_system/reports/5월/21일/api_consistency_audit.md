# API 응답 일관성 감사 보고서

- 작성: 2026-05-21 (야간 자동 감사)
- 감사자: Claude (read-only)
- 범위: `**/views*.py` 26개 파일 (`/frontend`, 테스트 제외)
- 정책 기준: `docs/features/api_envelope/policy.md` (2026-05-12 채택, DRF 평탄 + 통일 에러 envelope)
- 핸들러: `config/exception_handler.py:custom_exception_handler` (REST_FRAMEWORK에 등록됨)

---

## 요약

| 영역 | 상태 | 핵심 문제 |
|------|------|-----------|
| ✅ 성공 응답 평탄화 | **부분 적용** | `serverless/`, `news/api/`, `rag_analysis/`, `portfolio/api/` 등 대다수는 평탄. 그러나 `stocks/views_screener.py`, `stocks/views_fundamentals.py`, `stocks/views_exchange.py` 3개 파일에서 `{success, data, meta}` 래핑 **17건 잔존** |
| ❌ 에러 응답 표준화 | **광범위한 우회** | EXCEPTION_HANDLER가 등록되어 있으나 호출부에서 `raise` 대신 `Response({'error': ...})` 직접 반환이 **38건** (validation 7, chainsight 8, serverless_admin 23, portfolio_api 24) — 표준 envelope `{detail, code, status_code}`가 생성되지 않음 |
| ❌ 페이지네이션 | **거의 미적용** | DRF `PageNumberPagination` 사용은 2 엔드포인트(`stocks/views.py:StockListAPIView`, `news/api/views.py:NewsViewSet`)뿐. 다른 목록 API는 페이지네이션 없이 `.all()`/`.filter()` 전체 반환 또는 자체 Paginator로 비표준 envelope 생성 |
| ⚠️ 201 일관성 | **양호** | 14 엔드포인트에서 일관 사용. 단, `users/views.py:918,1040`은 `201 if created else 200` ternary 패턴 — DRF idempotent upsert에서 정상 |
| ⚠️ status 모듈 vs 숫자 | **혼재** | DRF 뷰는 `status.HTTP_*` 208건으로 일관. 그러나 `portfolio/views.py`(순수 Django) 14건은 `status=400/429/500` 하드코딩 — 별도 경로라 정당화 가능 |
| ❌ 순수 Django 잔존 | **정책 사각지대** | `portfolio/views.py`(`/api/coach/eN/` legacy), `config/views.py`(health) — DRF EXCEPTION_HANDLER 미적용. 정책 문서 §9에서 명시적 제외했으나 `portfolio/api/views.py`로 V1 이전 완료된 상태이므로 dead code 가능성 |

**P0 (즉시 수정 권장)**:
- (1) `stocks/views_{screener,fundamentals,exchange}.py` 17건 래핑 → 평탄 + 에러는 raise로 전환 (정책 PR-A/B 미시행 잔재)
- (2) `serverless/views_admin.py` 23건 `{'error': ...}` → `raise ValidationError/NotFound` 또는 domain `APIException`

**P1**:
- (3) `validation/api/views.py` 7건 — Portfolio Coach 외부 코드와 동일 패턴 일관 정리
- (4) `chainsight/api/views.py` 8건 동일
- (5) 페이지네이션 표준 — `news/`, `users/`(Watchlist), `serverless/`(presets, alerts) 등 결과 누락 위험 있는 목록 API

**P2**:
- (6) `users/views.py`, `rag_analysis/views.py` 커스텀 Paginator 응답 envelope를 DRF 표준(`{count, next, previous, results}`)으로 통일
- (7) `portfolio/views.py` legacy 제거 검토 (`portfolio/api/views.py`가 동일 기능 제공)

---

## 앱별 응답 패턴 매트릭스

| 앱 / 파일 | Response 호출 | `success` 래핑 | `{'error': ...}` 반환 | `raise NotFound/etc` | 커스텀 envelope | 평탄 응답 채택 |
|-----------|:-------------:|:-------------:|:-------------------:|:-------------------:|:--------------:|:--------------:|
| `users/views.py` | 56 | 0 | 0 | 19 | Paginator 2건 | ✅ (대부분) |
| `users/views.py` (success/message) | — | 0 | 0 (`'message':'...'` 6) | — | — | ✅ |
| `stocks/views.py` | 25 | **2** (배치 응답 내부) | 0 (`'detail'` 12) | 0 | — | ⚠️ (혼재) |
| `stocks/views_screener.py` | 15 | **7** | 0 | 0 | `{success, data, meta}` | ❌ |
| `stocks/views_fundamentals.py` | 15 | **5** | 0 | 0 | `{success, data, meta}` | ❌ |
| `stocks/views_exchange.py` | 13 | **5** | 0 | 0 | `{success, data, meta}` | ❌ |
| `stocks/views_indicators.py` | 8 | 0 | 0 | 0 | — | ✅ |
| `stocks/views_eod.py` | 6 | 0 | 0 | 0 | — | ✅ |
| `stocks/views_search.py` | 10 | 0 | 0 | 0 | — | ✅ |
| `stocks/views_mvp.py` | 4 | 0 | 0 | 0 | — | ✅ |
| `stocks/views_market_movers.py` | 2 | 0 | 0 | 0 | — | ✅ |
| `serverless/views.py` | 72 | 0 | 0 (`'message'` 4) | **37** | — | ✅ |
| `serverless/views_admin.py` | 45 | 0 | **23** | 0 | — | ❌ |
| `news/api/views.py` | 61 | 0 | 0 | 10 | DRF Pagination | ✅ |
| `rag_analysis/views.py` | 19 | 0 | 0 | 14 | Paginator 1건 | ✅ |
| `validation/api/views.py` | 23 | 0 | **7** | 0 | — | ⚠️ |
| `chainsight/api/views.py` | 20 | 0 | **8** | 0 | — | ⚠️ |
| `portfolio/api/views.py` | 30 | 0 | **24** | 0 | — | ❌ (Coach 6 endpoint × 4 분기) |
| `portfolio/views.py` (Django) | 0 (JsonResponse) | 0 | 14 (`{error, detail}`) | 0 | — | N/A — 정책 §9 제외 |
| `macro/views.py` | 26 | 0 | 0 | 0 | — | ✅ |
| `sec_pipeline/views.py` | 3 | 0 | 0 | 0 | — | ✅ |
| `config/views.py` | 0 (JsonResponse) | 0 | 0 | 0 | — | N/A — health check |

**범례**:
- ✅ 정책 부합 (DRF 평탄 + raise 기반 에러)
- ⚠️ 부분 부합 (Response로 에러를 직접 반환하나 `'error'` 키 한정 — code 누락)
- ❌ 정책 위반 (래핑 또는 자체 에러 envelope)

**래핑 잔존 파일 (17건)**:
- `stocks/views_screener.py:95,151,281,330,386,435,491`
- `stocks/views_fundamentals.py:90,149,197,242,298`
- `stocks/views_exchange.py:69,118,195,239,289`

→ 정책 PR-B (stocks 마이그레이션)이 미수행. 정책 문서는 "BE 약 154건" 중 serverless/rag_analysis만 PR-A/B-F로 커버하고 stocks 3파일 17건은 PR 외였음 (정책 §1 적용 범위에는 포함되지 않음). **정책 보강 또는 별도 PR 필요**.

---

## HTTP 상태 코드 일관성

### `status` 모듈 vs 하드코딩

| 패턴 | 건수 | 위치 |
|------|-----:|------|
| `status=status.HTTP_*` | 208 | DRF 뷰 17개 파일 전반 |
| `status=200/400/404/500` 숫자 | 17 | `portfolio/views.py:14`, `sec_pipeline/views.py:3` |

→ `portfolio/views.py`는 순수 Django (DRF 미사용)이므로 `status=400` 숫자 사용 정당화. `sec_pipeline/views.py` 3건도 동일.

### 201 Created 일관성

| 위치 | 라인 | 메모 |
|------|------|------|
| `users/views.py` | 107, 295, 639, 731, 918, 1040 | 회원가입/Portfolio/Watchlist/Item 신규 생성 시 일관 |
| `serverless/views.py` | 921, 1221, 1525 | 프리셋/알림/임포트 |
| `serverless/views_admin.py` | 565 | 뉴스 카테고리 |
| `rag_analysis/views.py` | 63, 137, 291, 396 | DataBasket/Item/Session/Message |

**Idempotent 패턴** (DRF에서 흔히 권장):
- `users/views.py:918` — `status=status.HTTP_201_CREATED if added else status.HTTP_200_OK` (Watchlist 토글)
- `users/views.py:1040` — `status=status.HTTP_201_CREATED if created else status.HTTP_200_OK` (UserInterest get_or_create)

→ 표준에 부합. 클라이언트가 분기를 위해서는 body의 boolean(`added`/`created`)을 참조해야 함.

**누락 가능성** (POST 생성 응답인데 201 아님):
- `validation/api/views.py:select_preset` (PUT/POST일 가능성 — 코드 추가 확인 필요)
- `portfolio/api/views.py:coach_e1~e6` — POST이지만 신규 자원 생성 아닌 LLM 호출이므로 200 OK 정당

### 204 No Content

8개 엔드포인트에서 일관 사용:
- `users/views.py:342,688,759,1087` (탈퇴/Watchlist 삭제/Interest 삭제)
- `rag_analysis/views.py:100,159,424` (Basket/Item/Session 삭제)
- `serverless/views_admin.py:652` (카테고리 삭제)

→ 정책 부합. 다만 `serverless/views.py:973,1258,1349,1372`는 `{'message': '...deleted...'}` + 암묵 200 반환 — `204 No Content`로 통일 권장.

### 에러 status 분포

| 코드 | 건수 | 주요 위치 |
|------|-----:|----------|
| 400 (validation) | ~70 | 전 파일 |
| 401 (auth) | 6 | `validation/api/views.py:466,492` 등 — `IsAuthenticated`로 자동 401 처리 가능한데 명시적 반환 |
| 403 (permission) | 4 | `rag_analysis` (raise PermissionDenied 우선) |
| 404 (not found) | ~30 | 전 파일 |
| 429 (rate limit) | 6 | `portfolio/views.py`, `portfolio/api/views.py` (budget exceeded) |
| 500/502/503 | 24 | `portfolio/api/views.py` 6 endpoint × 3-4 분기, `chainsight/api/views.py:443,623` |

**일관성 위반**:
1. `validation/api/views.py:466,492` — `Response({'error':'로그인 필요'}, status=401)`을 명시 반환. `permission_classes=[IsAuthenticated]`로 처리하면 DRF가 자동 401 + 표준 envelope 적용.
2. `portfolio/api/views.py` — LLMError를 `502 Bad Gateway`로 처리하는 vs `serverless/`(GenerationFailed → 500)와 컨벤션 불일치.

---

## 에러 응답 형식

### 형식 분포

| 형식 | 건수 | 위치 | 정책 부합 |
|------|-----:|------|:--------:|
| `raise NotFound/ValidationError/PermissionDenied/APIException` → `{detail, code, status_code}` | 80 | users, news, rag_analysis, serverless | ✅ 표준 |
| `Response({'error': '...'}, status=...)` | 38 | validation 7, chainsight 8, serverless_admin 23, portfolio_api 24 | ❌ envelope 우회 |
| `Response({'message': '...'})` (성공) | 4 | serverless/views.py:973,1258,1349,1372 | ⚠️ 비-표준 (204 권장) |
| `JsonResponse({'error': '...', 'detail': '...'}, ...)` | 14 | portfolio/views.py | ⚠️ 정책 §9 제외 (legacy) |
| `Response({'error': ..., 'scope': ...})` | 6 | portfolio/api/views.py LLMBudgetExceededError | ❌ 비표준 + 도메인 정보 |

### 정책 우회 사례 상세

**A. `serverless/views_admin.py` — 23건 (가장 큰 위반)**

```python
# Line 512, 514, 518, 522, 527, 530, 533, 536, 584, 593, 604, 608, 611, 614, 616, 649 etc.
return Response({'error': '이름은 필수입니다'}, status=status.HTTP_400_BAD_REQUEST)
```

→ 권장 변경: `raise ValidationError({"name": ["이름은 필수입니다."]})` — 자동으로 `{detail, code:"validation_error", errors:{name:[...]}, status_code:400}` envelope 생성.

**B. `portfolio/api/views.py` — 6 endpoint × 4 분기 = 24건**

```python
# 모든 6 endpoint(coach_e1~e6)에서 동일 패턴
return Response({"error": f"Invalid provider: ..."}, status=400)
return Response({"error": "LLM budget exceeded", "scope": exc.scope}, status=429)
return Response({"error": "LLM call failed", "type": type(exc).__name__}, status=502)
return Response({"error": "Internal server error"}, status=500)
```

→ Slice 13 신규 코드이지만 정책 채택일(2026-05-12) 이후 작성. APIException 서브클래스로 도메인 코드 보존하면 일관 envelope 자동 생성.

**C. `validation/api/views.py` — 7건**

DRF에서 `Stock not found` 등 메시지가 한국어와 영어 혼재. `raise NotFound("Stock {symbol} not found")`로 변환 권장.

**D. `chainsight/api/views.py` — 8건**

`Graph service unavailable` (503 권장이지만 코드상 500-계 사용 미확인).

### EXCEPTION_HANDLER 영향 매트릭스

| 응답 종류 | EXCEPTION_HANDLER 통과 | 최종 body |
|-----------|:----------------------:|----------|
| `raise NotFound("msg")` | ✅ | `{detail:"msg", code:"not_found", status_code:404}` |
| `raise ValidationError({...})` | ✅ | `{detail:"Validation failed.", code:"validation_error", errors:{...}, status_code:400}` |
| `Response({'error':'msg'}, status=404)` | ❌ (Response는 예외 아님) | `{error:"msg"}` — 표준 envelope 적용 안 됨 |
| `Response({'detail':'msg'}, status=404)` | ❌ | `{detail:"msg"}` — code/status_code 누락 |
| `Response({'message':'msg'})` | ❌ | `{message:"msg"}` |

→ FE는 `error.response.data.code`로 도메인 분기를 권장받지만, **38건의 우회 응답에서는 `code` 키가 누락** → FE 분기 로직이 라우트별로 깨질 가능성.

---

## 페이지네이션 현황

### DRF 표준 사용 (정책 부합)

| 위치 | 클래스 | 적용 |
|------|--------|------|
| `stocks/views.py:77 StockListPagination` | PageNumberPagination | `StockListAPIView` (`/api/v1/stocks/`) |
| `news/api/views.py:45 NewsArticlePagination` | PageNumberPagination | `NewsViewSet` (`/api/v1/news/`) |

`config/settings.py:348 REST_FRAMEWORK` — **`DEFAULT_PAGINATION_CLASS` 미설정**. 즉 ViewSet 단위 명시 적용만.

### 커스텀 페이지네이션 (비-표준 envelope)

| 위치 | 패턴 | envelope |
|------|------|----------|
| `users/views.py:610-624` (`watchlists`) | `django.core.paginator.Paginator` | `{count, num_pages, results, ...}` |
| `users/views.py:830-845` (`watchlist items`) | 동일 | 동일 |
| `rag_analysis/views.py:707-733` (`usage logs`) | 동일 | `{total_pages, total_count, results, ...}` |

→ DRF 표준 `{count, next, previous, results}`와 키가 일부 다름 (`next`/`previous` URL 누락, `num_pages` vs `total_pages` 명명 충돌).

### 페이지네이션 없이 전체 반환 (잠재적 메모리/응답 크기 위험)

| 위치 | 쿼리 | 위험 |
|------|------|------|
| `users/views.py:92` | `User.objects.all()` (관리자용) | ⚠️ 사용자 전체 — 대규모 누출/지연 |
| `users/views.py:975` | `UserInterest.objects.filter(user=request.user)` | 사용자별 제한적, 보통 안전 |
| `users/views.py:264,358` | `Portfolio.objects.filter(user=request.user)` | 동일 |
| `news/api/views.py:1362` | `NewsCollectionLog.objects.filter(executed_at__gte=cutoff)` | ⚠️ cutoff 따라 수천 건 가능 |
| `serverless/views.py:886` (`ScreenerPreset.objects.all()`) | 전체 프리셋 | 양 적음, 보통 안전 |
| `serverless/views.py:1054` | `ScreenerFilter.objects.filter(is_active=True)` | 동일 |
| `serverless/views.py:1196` | `ScreenerAlert.objects.filter(user=request.user)` | 동일 |
| `serverless/views.py:1877` | `ETFProfile.objects.all().order_by(...)` | 양 적음 |
| `serverless/views_admin.py:475` | `NewsCollectionCategory.objects.all()` | 양 적음 |
| `serverless/views_admin.py:668-675` | `SP500Constituent.objects.filter(is_active=True)` | ⚠️ ~500건 |
| `validation/api/views.py:80,151,335,429` | CategorySignal/Stock/Peer/Preset filter | 종목당 제한적 |
| `chainsight/api/views.py:153` | `CoMentionEdge.objects.filter(symbol_b=...)` | ⚠️ 종목당 수백~수천 |
| `news/api/views.py:1802,2124,2141` | DailyNewsKeyword, AlertLog | ⚠️ 시간 윈도우 의존 |
| `rag_analysis/views.py:52,379` | DataBasket/Session per user | 보통 안전 |

**커서 페이지네이션 (CursorPagination) 사용 0건** — 시계열 데이터(`DailyPrice`, `NewsArticle`)에서 권장되나 미적용.

---

## 권고사항

### P0 (이번 슬라이스 종결 전 권장)

1. **`stocks/views_{screener,fundamentals,exchange}.py` 17건 래핑 제거**
   - 정책 §1.1 wrapping 폐기 미적용 잔재. 영향 범위 작아 1-2 PR로 가능.
   - FE 호출자: `screenerService.ts` 등 — 정책 §6.3에서 이미 동시 변경 명시되었으나 stocks 3파일은 PR-B-F 범위 외였음.
   - 변경: `return Response({"success": True, "data": d, "meta": m})` → `return Response(d)` + 메타는 응답 헤더 또는 함께 평탄 키로 머지.

2. **`serverless/views_admin.py` 23건 `{'error': ...}` → `raise ValidationError/NotFound`**
   - 정책 PR-G에 해당하나 미완료로 보임.
   - admin 라우트지만 envelope 표준화 시 일관성 큰 향상.

3. **`portfolio/api/views.py` 24건 — Slice 13 신규 코드인데 정책 미준수**
   - Slice 13 #65/#66 후속으로 일괄 변경 가능. 도메인 예외(`LLMBudgetError`, `LLMInvocationError`) `APIException` 서브클래스로 정의 → `raise` 패턴 통일.
   - `portfolio/exceptions.py` 신설 권장.

### P1 (다음 슬라이스)

4. **`validation/api/views.py` 7건 + `chainsight/api/views.py` 8건 — `{'error':...}` → raise**
5. **`serverless/views.py:973,1258,1349,1372` 4건 — `{'message':'...deleted...'}` → `Response(status=204)` 통일**
6. **페이지네이션 우선 적용 대상**:
   - `users/views.py:92 User.objects.all()` (보안 + 성능)
   - `news/api/views.py:1362 NewsCollectionLog`
   - `chainsight/api/views.py:153 CoMentionEdge filter`
   - `serverless/views_admin.py:668 SP500Constituent`

### P2 (정책 보강 차원)

7. **`users/views.py` + `rag_analysis/views.py` 커스텀 Paginator → DRF `PageNumberPagination`로 envelope 통일**
   - 호환성: FE가 현재 `count`, `num_pages`, `total_pages` 등 다른 키를 받고 있으므로 클라이언트 변경 동반.

8. **`portfolio/views.py` legacy 제거 검토**
   - `/api/coach/eN/` (legacy) vs `/api/v1/coach/eN/` (DRF) 중복. Slice 13에서 E1/E2/E3 legacy view 제거 진행 중 (#65). 종결 시 정책 §9 예외 항목 삭제 가능.

9. **`config/settings.py:REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS` 추가 검토**
   - 모든 `ListAPIView`/ViewSet에 자동 적용. 다만 기존 비-표준 envelope를 깨므로 마이그레이션 비용 측정 필요.

10. **계약 테스트 신설**: `tests/contracts/test_response_envelope.py` (정책 §8) — 없으면 회귀 방지 불가. 정책 PR-G 마지막 단계로 명시되었으나 미확인.

---

## 부록 A: 검색 명령 (재실행용)

```bash
# 래핑 패턴 탐색
grep -rn "'success': True" --include="views*.py" .

# 비-표준 에러 응답
grep -rn "return Response({['\"]error['\"]" --include="views*.py" .

# 페이지네이션 클래스
grep -rn "pagination_class\|PageNumberPagination" --include="views*.py" .

# 표준 raise 패턴
grep -rcn "raise \(NotFound\|ValidationError\|PermissionDenied\|APIException\)" --include="views*.py" .
```

## 부록 B: 관련 정책/감사 문서

- `docs/features/api_envelope/policy.md` (2026-05-12, envelope 결정 SoT)
- `docs/nightly_auto_system/reports/5월/5일/api_consistency_audit.md` (이전 감사 — 정책 입안 근거)
- `config/exception_handler.py` (구현체)
- `config/settings.py:348-367` (REST_FRAMEWORK 설정)
