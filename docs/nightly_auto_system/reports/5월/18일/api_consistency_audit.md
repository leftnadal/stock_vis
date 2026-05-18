# API 응답 일관성 감사 보고서

- 감사일: 2026-05-18
- 범위: 모든 `views*.py` (총 26개 파일, 약 13,047 LOC) — `migrations`, `node_modules`, `__pycache__`, `.venv` 제외
- 정책 기준: [`docs/features/api_envelope/policy.md`](../../../../features/api_envelope/policy.md) (2026-05-12 채택)
- 감사 방식: 읽기 전용 (코드 수정 없음)

---

## 요약

| 항목 | 결론 |
|------|------|
| 표준 정책 존재 | ✅ `{detail, code?, errors?, status_code}` 단일 envelope (`config/exception_handler.py` 등록 완료) |
| 정책 준수율 (성공 응답 평탄 반환) | ⚠️ **3개 파일에서 `success: True` 래핑 17건 잔존** (정책상 전면 폐기 대상) |
| 정책 준수율 (에러 응답 envelope 통일) | ❌ **17개 파일에서 `Response({'error': ...})` 직접 반환 167건** — `raise NotFound/ValidationError` 패턴 미적용 |
| 페이지네이션 적용률 | ⚠️ 표준화된 ViewSet 단 2건 (`stocks/views.py:StockListAPIView`, `news/api/views.py:NewsViewSet`). 그 외 목록 응답은 비페이지네이션 직렬화 |
| HTTP status 일관성 | ⚠️ DRF `status` 모듈 사용 178건 / 하드코딩 숫자 35건 (`portfolio/views.py`는 정책상 DRF 미사용 — 제외) |
| 가장 큰 위험 | `serverless/views.py` 2,909 LOC 단일 파일에 72건 `Response()` 호출, `{'error': str(e)}` 직접 반환 — PR-B~F 분할 마이그레이션 작업 미완 |

**한 줄 결론**: envelope 정책은 채택되었으나 **PR-0 (EXCEPTION_HANDLER 등록)만 완료**된 상태. PR-A (rag_analysis), PR-B~F (serverless), PR-G (admin/계약 테스트) 실제 view 마이그레이션은 거의 미수행 — 167건의 `Response({'error': ...})` 직접 반환이 정책 위반으로 남아 있음.

---

## 앱별 응답 패턴 매트릭스

| 파일 | LOC | `Response()` | `success: True` 래핑 | `'error'` 키 | `'detail'` 키 | `'message'` 키 | `status=status.HTTP_*` | `status=숫자` | 정책 준수 |
|------|-----|--------------|----------------------|-------------|--------------|----------------|------------------------|---------------|-----------|
| `stocks/views.py` | 1030 | 25 | 0 | 12 | 0 | 0 | 25 | 0 | ⚠️ 부분 |
| `stocks/views_fundamentals.py` | 305 | 15 | **10** | 10 | 0 | 0 | 10 | 0 | ❌ |
| `stocks/views_screener.py` | 498 | 15 | **8** | 8 | 0 | 0 | 8 | 0 | ❌ |
| `stocks/views_exchange.py` | 295 | 13 | **8** | 8 | 0 | 0 | 8 | 0 | ❌ |
| `stocks/views_search.py` | 229 | 10 | 0 | 5 | 0 | 0 | 5 | 0 | ⚠️ |
| `stocks/views_indicators.py` | 372 | 8 | 0 | 3 | 0 | 0 | 3 | 0 | ⚠️ |
| `stocks/views_eod.py` | 136 | 6 | 0 | 3 | 0 | 0 | 3 | 0 | ⚠️ |
| `stocks/views_market_movers.py` | 69 | 2 | 0 | 1 | 0 | 0 | 1 | 0 | ⚠️ |
| `stocks/views_mvp.py` | 200 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | ✅ |
| `users/views.py` | 1088 | 56 | 0 | 8 | 2 | 7 | 33 | 0 | ⚠️ |
| `serverless/views.py` | 2909 | **72** | 0 | 6 | 22¹ | 6 | 3 | 0 | ❌ |
| `serverless/views_admin.py` | 691 | 45 | 0 | **28** | 1 | 0 | 30 | 0 | ❌ |
| `news/api/views.py` | 2198 | 61 | 0 | 7 | 3¹ | 3 | 7 | 0 | ⚠️ |
| `chainsight/api/views.py` | 814 | 20 | 0 | 9 | 0 | 0 | 8 | 0 | ❌ |
| `rag_analysis/views.py` | 772 | 20 | 0 | 2 | 6¹ | 0 | 7 | 0 | ⚠️ |
| `macro/views.py` | 410 | 26 | 0 | 15 | 10¹ | 0 | 15 | 0 | ❌ |
| `validation/api/views.py` | 561 | 23 | 0 | 15 | 4¹ | 4 | 12 | 0 | ❌ |
| `sec_pipeline/views.py` | 51 | 3 | 0 | 0 | 0 | 1 | 0 | **3** | ❌ |
| `portfolio/views.py` | 304 | 0 (`JsonResponse`) | 0 | 27 | 24 | 0 | 0 | **32** | ⚪ 정책 제외 |
| `config/views.py` | 104 | 0 (`JsonResponse`) | 0 | 0 | 0 | 0 | 0 | 0 | ⚪ 비-API |
| `news/views.py` | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ⚪ stub |
| `chainsight/views.py` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ⚪ stub |
| `validation/views.py` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ⚪ stub |
| `graph_analysis/views.py` | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ⚪ 미구현 |
| `metrics/views.py` | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | ⚪ 미구현 |
| **합계** | **13,047** | **458** | **17** | **167** | **59²** | **27²** | **178** | **35** | — |

¹ `'detail'` 키 일부는 **에러 envelope이 아닌 정상 응답 본문 필드** (예: `serverless/views.py`의 데이터 detail). 표는 단순 grep 카운트.
² 일부는 에러 메시지, 일부는 정상 응답 메타 필드. `portfolio/views.py`는 정책상 DRF 미사용으로 제외 (정책 §9).

### `success: True` 래핑 잔존 위치 (정책 명백 위반)

- `stocks/views_fundamentals.py` L89, L148, L196, L241, L297 (총 10건, 한 호출당 2회 검색 매칭 가능)
- `stocks/views_screener.py` L94, L150, L280, L329, L385, L434, L490 (총 8건)
- `stocks/views_exchange.py` L68, L117, L194, L238, L288 (총 8건)

→ 정책 §2.1에 따라 `{success: True, data: ..., meta: ...}` 패턴은 **전면 폐기**, `serializer.data` 또는 dict 평탄 반환으로 마이그레이션 필요.

### 정상 평탄 반환 패턴 모범 예시

- `stocks/views_mvp.py` — `success` 래핑 없음, 에러 키 없음 (success path만 있음)
- `news/api/views.py:NewsViewSet` — ViewSet + Pagination 표준 사용
- `stocks/views.py:StockListAPIView` — `generics.ListAPIView` + `pagination_class`

---

## HTTP 상태 코드 일관성

### status 모듈 사용 vs 하드코딩

| 패턴 | 발생 횟수 | 위치 |
|------|----------|------|
| `status=status.HTTP_*_*` (DRF 상수) | **178** | DRF view 전반 |
| `status=200`, `status=400` 등 정수 하드코딩 | **35** | `portfolio/views.py` 32 (DRF 미사용), `sec_pipeline/views.py` 3 (DRF view지만 정수 사용) |

**문제 위치**:
- `sec_pipeline/views.py:49,51` — `return Response(result, status=200)` — DRF view인데 정수 사용. `status.HTTP_200_OK`로 통일 필요.
- `portfolio/views.py` — 32회 정수 사용. 정책 §9에 따라 **DRF 미사용 (순수 `JsonResponse`)**으로 환경 자체가 다름. 향후 DRF 마이그레이션 시 통합 예정.

### 201 Created 일관성

`HTTP_201_CREATED` 사용 위치 (총 14건):
- ✅ `users/views.py` 5건 — 회원가입(L107), 포트폴리오 생성(L295), Watchlist 생성(L639), Watchlist 아이템 추가(L731), Interest 추가 (L918, L1040 — `201 if created else 200` 분기 적용)
- ✅ `rag_analysis/views.py` 4건 — 분석 세션/바스켓 생성
- ✅ `serverless/views.py` 3건 — 프리셋 생성(L919), 알림 생성(L1219), 프리셋 import (L1523)
- ✅ `serverless/views_admin.py` 1건 — 수집 카테고리 생성(L565)

**누락 의심**:
- `validation/api/views.py:487` — `UserPeerPreference` `update_or_create` 후 `Response({'status': 'ok', ...})` 반환. `created` 분기 없이 항상 200. **신규 생성 시 201 권장**.

### 4xx/5xx 에러 코드 사용 패턴

| 코드 | 주요 사용처 |
|------|------------|
| `400 BAD_REQUEST` | 입력 검증 실패 (모든 앱) — 자주 `Response({'error': msg}, status=400)` 형태 |
| `401 UNAUTHORIZED` | `users/views.py:172`, `validation/api/views.py:466,492` — 수동 인증 체크 (DRF `permission_classes` 우회) |
| `403 FORBIDDEN` | (확인된 위치 없음 — DRF가 `PermissionDenied`로 자동 처리) |
| `404 NOT_FOUND` | 종목/리소스 미존재 — `Response({'error': '...not found'}, status=404)` 다수. **정책 위반** (raise NotFound 권장) |
| `429 TOO_MANY_REQUESTS` | `portfolio/views.py`만 사용 (budget exceeded) |
| `500 INTERNAL_SERVER_ERROR` | `stocks/views.py:218`, `stocks/views_search.py:86,140` 등 — `except Exception as e: Response({'error': str(e)}, status=500)`. **민감정보 노출 + 정책 위반** |
| `503 SERVICE_UNAVAILABLE` | `chainsight/api/views.py:443,623` — Graph service unavailable |

**핵심 문제**: `404 NOT_FOUND`와 `500 INTERNAL_SERVER_ERROR`를 `Response()`로 직접 반환하는 패턴이 모든 앱에 광범위 — 정책 §3에 따라 `raise NotFound(...)` / `raise APIException(...)` (도메인 서브클래스) 사용해야 응답이 standard envelope으로 변환됨.

---

## 에러 응답 형식

### 표준 envelope (정책)

```json
{ "detail": "Stock not found", "code": "stock_not_found", "errors": {...}, "status_code": 404 }
```

### 실제 발견 패턴 (혼재)

| 패턴 | 발생 | 예시 | 평가 |
|------|-----|------|------|
| `{'error': str}` | **167** | `Response({'error': f'Stock {symbol} not found'}, status=404)` | ❌ 정책 위반 (직접 반환) |
| `{'error': dict}` | 다수 | `stocks/views.py:596,929` — `{'error': {'code': '...', 'message': '...'}}` 중첩 구조 | ❌ **이전 wrapping 잔존** |
| `{'error': str, 'detail': str}` | 27 | `portfolio/views.py` 전반 | ⚪ 정책 §9 제외 (Django 순수) |
| `{'error': code, 'message': str, 'symbol': ...}` | 6+ | `validation/api/views.py:64,82,328` — 비즈니스 상태 응답 200 OK | ⚠️ 비즈니스 status 패턴 (정책 §2.3 — 422/404로 정상화 필요) |
| `raise NotFound(...)`, `raise ValidationError(...)` | 41 (정책 추정) | DRF 표준 예외 → exception_handler 변환 | ✅ 정책 준수 |
| `raise PermissionDenied(...)` | 1 | `serverless/views.py:955` | ✅ 정책 준수 |
| `{'detail': msg}` 직접 반환 | 6 | `rag_analysis/views.py` 일부 — 일관성 측면에서 envelope 흉내내기 | ⚠️ 일관성 ↑이나 `code`/`status_code` 누락 |

### 심각한 패턴

1. **`Exception` 전역 catch 후 `str(e)` 노출** (5건+):
   ```python
   # stocks/views_search.py:86, 140
   except Exception as e:
       return Response({'error': f'서버 오류: {str(e)}'}, status=500)
   ```
   → 민감 정보 (스택, DB 쿼리, 내부 경로) 노출 위험. `raise APIException` 또는 sentry + 일반 메시지.

2. **`stocks/views.py:596,929` 중첩 `error.code/error.message`**:
   ```python
   return Response({
       'error': {'code': 'INVALID_PARAMETER', 'message': str(e)}
   }, status=400)
   ```
   → **구 wrapping 패턴 잔존**. 정책 §6.2 FE 마이그레이션 가이드에 따라 `code`/`detail`로 평탄화 필요.

3. **`users/views.py:518,520,563,565` `error + detail` 조합**:
   ```python
   return Response({'error': 'Failed', 'detail': str(e)}, status=500)
   ```
   → `detail` 키가 정책 envelope의 `detail`과 의미가 다름 (여기선 stack-like 정보). 혼동 유발.

### envelope 변환기 (exception_handler) 무력화 위험

`config/exception_handler.py`는 **DRF 예외가 raise 될 때만 동작**한다. 위 167건 `Response({'error': ...})` 직접 반환은 변환기를 건너뛰므로 — FE 입장에서는 같은 의미의 404가 두 가지 응답 형태로 도착한다:
- `raise NotFound("X")` → `{detail, code, status_code}` ✅
- `Response({'error': 'X'}, status=404)` → `{error}` ❌

이는 정책 §2의 "FE가 라우트별 unwrap 분기 필요"라는 원래 문제를 여전히 살려둔다.

---

## 페이지네이션 현황

### REST_FRAMEWORK 전역 설정

`config/settings.py:348` — `DEFAULT_PAGINATION_CLASS` **미설정**.
정책 §1: "PageNumberPagination 표준, 적용은 ViewSet 단위 (전역 미적용)"

### 명시적으로 페이지네이션 적용된 View

| 위치 | 클래스 | 페이지 크기 |
|------|--------|------------|
| `stocks/views.py:77 StockListPagination` | `PageNumberPagination` | 50 (max 200) |
| `stocks/views.py:84 StockListAPIView` | `generics.ListAPIView` + `StockListPagination` | ✅ |
| `news/api/views.py:45 NewsArticlePagination` | `PageNumberPagination` | 20 (max 100) |
| `news/api/views.py:55 NewsViewSet` | `viewsets.ReadOnlyModelViewSet` + `NewsArticlePagination` | ✅ |

### 수동 페이지네이션 (DRF 표준 미사용)

| 위치 | 패턴 | 평가 |
|------|------|------|
| `users/views.py:608-624` | `django.core.paginator.Paginator` 수동 사용, 응답 본문에 `{results, pagination: {count, num_pages, ...}}` | ⚠️ 자체 envelope. DRF 표준 응답(`{count, next, previous, results}`)과 불일치 |
| `users/views.py:830-844` | 위와 동일 — Watchlist 아이템 목록 | ⚠️ 동일 |
| `rag_analysis/views.py:689-733` | `django.core.paginator.Paginator`, 응답 `{results, pagination: {page, total_pages, total_count}}` | ⚠️ 동일 |

### 페이지네이션 미적용 — 목록 반환 (잠재적 DoS / 응답 크기 폭주)

다음 목록 API는 **페이지네이션 없이 전체 결과 직렬화**:

| 위치 | 쿼리셋 | 비고 |
|------|--------|------|
| `serverless/views.py:907` `screener_preset_list_create` | `ScreenerPreset.objects.all().distinct()` | `len(serializer.data)`만 보고 ✅ count는 첨부. but 전체 반환 |
| `serverless/views.py:1203` 알림 목록 | 전체 알림 직렬화 후 `{count, ...}` | 동일 |
| `serverless/views.py:1323` 알림 히스토리 | 동일 | 동일 |
| `serverless/views.py:1584` (preset import 이후 목록) | 동일 | 동일 |
| `serverless/views.py:1780` Watchlist 비교 | 동일 | 동일 |
| `serverless/views.py:1919, 2023, 2117` ETF/Theme/Chain Sight 결과 목록 | 비페이지네이션 | ETF Holdings 등은 항목 수가 많을 수 있음 |
| `validation/api/views.py:181` `categories` | 전체 카테고리 반환 (소량 — 위험 낮음) | OK |
| `chainsight/api/views.py:181, 314` | 전체 카테고리/엔티티 반환 | OK (도메인상 소량) |
| `stocks/views_screener.py:280, 329, 385, 434, 490` | 결과 `limit` 파라미터로 제한 (서비스 레벨 처리) | ⚠️ 클라이언트 제어 안전 (limit가 검증됨) |
| `news/api/views.py:996, 1019` | personalized-feed 등 | 비페이지네이션 |

**위험도가 높은 경우**: 사용자 수와 무관하게 데이터가 늘어나는 알림 히스토리, ETF Holdings, Screener 프리셋 — **명시적 `PageNumberPagination` 권장**.

### CursorPagination 사용 여부

- `Pagination|paginate_queryset|PageNumberPagination|CursorPagination` 정규식 grep 결과: `news/api/views.py`, `stocks/views.py` 2개 파일만 매칭. **`CursorPagination` 사용 0건**.
- 시계열성 응답 (뉴스 기사, 알림 이력)에는 CursorPagination이 페이지 깊이 증가 시 더 안정적이나 현재 미적용.

---

## 권고사항

### P0 — 즉시 (정책 PR-0 후속 마이그레이션 완료)

1. **`success: True` 래핑 17건 제거**
   - `stocks/views_fundamentals.py`, `stocks/views_screener.py`, `stocks/views_exchange.py` — 정책 §2.1 평탄 반환으로 마이그레이션.
   - FE 호출자: `screenerService.ts` 등에서 `.data.data` → `.data` 동시 수정 필수.

2. **`Response({'error': ...}, status=4xx)` 167건 → `raise NotFound/ValidationError`로 변환**
   - 가장 격리된 `rag_analysis/views.py` (PR-A) → `serverless/views.py` 분할 (PR-B~F) → `serverless/views_admin.py` (PR-G) 순서.
   - `chainsight/api/views.py`, `macro/views.py`, `validation/api/views.py`, `users/views.py` 추가 PR 필요 (정책 문서에는 미포함된 범위).

3. **`except Exception as e: Response({'error': str(e)}, status=500)` 패턴 제거**
   - 발견 위치: `stocks/views_search.py:86,140`, `stocks/views.py:340`, `users/views.py:518,563`, `serverless/views_admin.py` (28건 동일 패턴).
   - 정책 §3.2 — `serverless/exceptions.py`/`rag_analysis/exceptions.py` 도메인 `APIException` 서브클래스로 변환.
   - **민감정보 노출 + 정책 위반 동시 해결**.

### P1 — 단기

4. **`sec_pipeline/views.py:49,51` 하드코딩 `status=200` → `status.HTTP_200_OK`**
   - DRF view인데 정수 사용. 일관성 개선 (실질 효과는 없음).

5. **`stocks/views.py:596,929` 중첩 `{'error': {'code': ..., 'message': ...}}` 평탄화**
   - 구 wrapping 잔존. 정책 envelope과 충돌.

6. **`users/views.py` 수동 Paginator → DRF `PageNumberPagination` 마이그레이션**
   - L608-624 (Watchlist 목록), L830-844 (Watchlist 아이템 목록), `rag_analysis/views.py:689` 분석 이력.
   - 응답 본문 `{results, pagination: {...}}` → 정책 §2.1 `{count, next, previous, results}` 표준.
   - FE 호출자 동시 수정 필요.

7. **`validation/api/views.py:487` `update_or_create` 결과에 따른 201/200 분기 추가**
   - 현재 항상 200. `users/views.py:918` 패턴 참고 (`status=status.HTTP_201_CREATED if added else status.HTTP_200_OK`).

### P2 — 중기 (정책 §1 페이지네이션 ViewSet 단위 확대)

8. **`serverless/views.py` 알림 히스토리·ETF/Theme 결과 페이지네이션 적용**
   - L1323 알림 히스토리: 시계열 → `CursorPagination` 고려.
   - L907 screener 프리셋: `PageNumberPagination`.
   - L1919, 2023, 2117 ETF/Theme 결과: 데이터 양 늘어남에 따라 `page_size` 제한.

9. **계약 테스트 추가 (정책 §8)**
   - `tests/contracts/test_response_envelope.py` 미생성 상태로 추정. 정책 PR-G 작업 미완.
   - 404 / 400 / 500 envelope 형태 회귀 테스트.

### P3 — 장기

10. **`portfolio/views.py` 순수 Django → DRF 마이그레이션 검토**
    - 정책 §9에서 명시적으로 "향후 DRF 마이그레이션 시 통합"으로 미룬 상태.
    - 304 LOC 단일 파일이며 이미 envelope 형태 (`{error, detail}`)를 흉내내고 있어 마이그레이션 비용 낮음.

11. **`graph_analysis/views.py`, `metrics/views.py` 빈 stub 정리 또는 미구현 표시**
    - 3-line placeholder만 존재. CLAUDE.md "graph_analysis (API 미구현)"과 일치하나, 파일이 있는데 빈 상태라 IDE/검색 시 혼동 가능.

12. **`config/exception_handler.py` 보강 — APIException 서브클래스 `default_code` 자동 매핑 일관성 점검**
    - 정책 §3.2의 `CacheError`, `CostError`, `GenerationFailed` 등 도메인 예외가 실제로 정의되어 있는지 확인 필요 (이번 감사 범위 밖).

---

## 부록 — 정책 문서 채택 후 미완 작업 추적

정책 문서(`docs/features/api_envelope/policy.md` 2026-05-12) §7 PR 순서 기준:

| PR | 범위 | 추정 상태 |
|----|------|----------|
| PR-0 | EXCEPTION_HANDLER 등록 + APIException 서브클래스 + ErrorSerializer | ✅ `config/exception_handler.py` 존재 + `settings.py:366` 등록 확인 |
| PR-A | rag_analysis 36건 마이그레이션 + ragService interceptor 제거 | ⚠️ `rag_analysis/views.py`에 여전히 `Response({...}, status=...)` 20건 — 마이그레이션 미수행 추정 |
| PR-B~F | serverless/views.py 117건 분할 | ❌ 72건 잔존 (movers/screener/chain_sight/institutional/theme) |
| PR-G | serverless/views_admin.py + 계약 테스트 | ❌ admin 45건 잔존, 계약 테스트 파일 미확인 |

**제언**: 정책 PR-A부터 재개. 가장 격리된 단위라 회귀 위험 최소. `shared_kb/queue`에 LESSON 추가 — "정책 채택 ≠ 마이그레이션 완료. 후속 PR을 PROGRESS.md/TASKQUEUE.md에 명시적으로 등록해야 잊혀지지 않음."

---

## 부록 B — 통계 요약 (raw 카운트)

```
총 Response() 호출:                     458건
총 'success': True 래핑:                 17건 (정책 위반)
총 'error' 키 직접 반환:                167건 (정책 위반)
총 'detail' 키 직접 사용:                59건 (일부는 정상 응답 데이터 필드)
총 'message' 키 사용:                    27건
총 status=status.HTTP_* 사용:           178건
총 status=정수 하드코딩:                 35건 (portfolio 32 + sec_pipeline 3)
총 페이지네이션 적용 View:                  2건 (stocks, news)
총 수동 Paginator 사용 View:               3건 (users 2 + rag 1)
```
