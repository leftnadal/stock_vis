# API 응답 표준화 정책 (envelope 폐기 + DRF 평탄 통일)

- 작성: 2026-05-12
- 근거 감사: `docs/nightly_auto_system/reports/5월/5일/api_consistency_audit.md`
- 관련 audit 우선순위: P1 #14 (응답 envelope 단일화)
- 적용 범위: BE 약 154건 + DRF `raise` 41건 + FE `ragService.ts` / `screenerService.ts`
- 예외 범위: **Market Pulse v2 카드 API** (`marketpulse/api/views/cards.py:_envelope`), **SSE 스트림 이벤트 페이로드**

---

## 1. 결정 요약

| 항목 | 결정 |
|------|------|
| **성공 응답** | `serializer.data` 또는 dict **평탄 반환** (DRF 표준). 기존 `{success, data, meta}` wrapping 폐기 |
| **에러 응답** | `{detail, code?, errors?, status_code}` 단일 표준. DRF `raise NotFound/ValidationError` 기본 키 `detail` 유지 + 도메인 `code` 추가 |
| **변환 메커니즘** | `config/exception_handler.py:custom_exception_handler` — `REST_FRAMEWORK.EXCEPTION_HANDLER`로 등록 |
| **도메인 에러** | `rag_analysis/exceptions.py`, `serverless/exceptions.py`에 `APIException` 서브클래스로 코드 보존 |
| **페이지네이션** | DRF `PageNumberPagination` 표준 (`{count, next, previous, results}`) — 적용은 ViewSet 단위 (전역 미적용, audit P0 #14 Pagination 클러스터에서 처리 완료) |
| **메타데이터** | 단발 호출 시 응답 헤더(`X-Request-Id`, `X-Cache`) — 본문에서 분리. 메타가 필수인 라우트(marketpulse v2 cards)만 본문 envelope 유지 |

**Why (B 옵션 = WRAP 폐기, DRF 평탄 통일)**:
1. wrapping 사용은 6개 파일만 → 마이그레이션 비용이 envelope 통일(EXCEPTION_HANDLER 전면 변환)보다 작다.
2. DRF 생태계 표준(serializer.data, raise Exception, drf-spectacular ErrorSerializer)에 정렬 → 신규 view 작성 시 결정 비용 0.
3. 클라이언트는 status code 우선 분기(HTTP의 본질) + body `code`로 도메인 분기 보강 → status/body 이중 진실 소스 회피.

---

## 2. 표준 응답 스키마

### 2.1 성공

```json
// 단일 자원
{ "id": 12, "name": "...", ... }            // serializer.data 그대로

// 페이지네이션 목록
{ "count": 100, "next": "?page=2", "previous": null, "results": [...] }

// 평탄 dict (집계, 통계, 상태 응답 등)
{ "synced": 487, "skipped": 13, "summary": {...} }

// 비-자원 응답
{ "status": "ok" }
{ "status": "not_in_universe", "data": null }   // 비즈니스 상태 (PR-#14 패턴, 422/404 권장)
```

**메타가 필요한 경우**: 응답 헤더 `X-Request-Id`, `X-Cache: HIT|MISS`, `X-Latency-Ms`. 본문에서 분리.

### 2.2 에러

```json
{
  "detail": "Stock not found",          // 필수, 사람이 읽는 메시지 (DRF 기본 키 유지)
  "code": "stock_not_found",            // optional, 도메인 분기용 코드 (snake_case)
  "errors": {                           // optional, ValidationError 시 field-level
    "email": ["This field is required."],
    "password": ["Must be at least 8 chars."]
  },
  "status_code": 404                    // 필수, 클라 분기 편의 (status 헤더 중복이지만 명시)
}
```

**필드 의미**:
- `detail`: 항상 존재. DRF가 자동 채움 (`raise NotFound("msg")`).
- `code`: snake_case. DRF 표준 예외는 자동 변환(`not_found`/`permission_denied`/`not_authenticated`/`validation_error`/`throttled`). 도메인 예외는 `default_code` 활용.
- `errors`: ValidationError가 field-level dict인 경우만 채움. 단일 메시지 ValidationError는 `detail`로만 표현.
- `status_code`: 정수.

### 2.3 비즈니스 상태 (200 OK)

에러가 아닌 **정상 흐름**의 분기는 본문 `status` 키로 표현:

```json
// validation/api/views.py (PR-#14 이후): not_in_universe → 422, no_data → 404로 이동 완료
// 만약 200을 유지해야 하면:
{ "status": "no_data", "data": null, "reason": "fundamentals not yet synced" }
```

이미 PR-#14에서 status 코드를 정상화했으므로 envelope 정책에서는 기존 패턴 유지.

---

## 3. 도메인 에러 코드 카탈로그

### 3.1 DRF 표준 예외로 대체 (코드 살리지 않음)

| 기존 코드 | DRF 예외 | 변환 후 `code` | status |
|-----------|----------|----------------|--------|
| `AUTHENTICATION_REQUIRED`, `UNAUTHORIZED` | `NotAuthenticated` | `not_authenticated` | 401 |
| `FORBIDDEN` | `PermissionDenied` | `permission_denied` | 403 |
| `NOT_FOUND`, `SESSION_NOT_FOUND`, `ETF_NOT_FOUND`, `THEME_NOT_FOUND` | `NotFound` | `not_found` | 404 |
| `INVALID_INPUT`, `INVALID_FILTERS`, `INVALID_TYPE`, `INVALID_DATE`, `NO_STOCKS`, `TOO_MANY_STOCKS`, `VALIDATION_ERROR` | `ValidationError` | `validation_error` | 400 |

→ 호출부는 `raise NotFound("Session not found")` 형태로 변경. detail 메시지는 살림.

### 3.2 도메인 APIException 서브클래스로 보존 (코드 유지)

500계 도메인 에러는 분기에 의미 있어 코드 유지. `rag_analysis/exceptions.py` 등에 정의:

```python
# rag_analysis/exceptions.py
from rest_framework.exceptions import APIException
from rest_framework import status

class CacheError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Cache operation failed."
    default_code = "cache_error"

class CostError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Cost computation failed."
    default_code = "cost_error"

class HistoryError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = "history_error"
    default_detail = "History retrieval failed."

class StatsError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = "stats_error"
    default_detail = "Stats query failed."
```

```python
# serverless/exceptions.py
class GenerationFailed(APIException):
    status_code = 500
    default_code = "generation_failed"
    default_detail = "Generation failed."

class SyncFailed(APIException):
    status_code = 500
    default_code = "sync_failed"
    default_detail = "Sync operation failed."

class ScreenerError(APIException):
    status_code = 500
    default_code = "screener_error"
    default_detail = "Screener execution failed."

# 외부 서비스 의존 에러 (각각 별도 클래스 — Sentry breakdown에 유리)
class InstitutionalError(APIException):
    status_code = 500
    default_code = "institutional_error"

class PatentError(APIException):
    status_code = 500
    default_code = "patent_error"

class RegulatoryError(APIException):
    status_code = 500
    default_code = "regulatory_error"

class ThesisGenerationFailed(APIException):
    status_code = 500
    default_code = "thesis_generation_failed"
```

호출부 패턴:
```python
# Before
return Response({
    "success": False,
    "error": {"code": "CACHE_ERROR", "message": str(e)},
    "meta": {...}
}, status=500)

# After
raise CacheError(detail=str(e))  # detail 커스터마이즈 가능
# 또는
raise CacheError()  # default_detail 사용
```

### 3.3 제외 (HTTP envelope 정책 밖)

- `PIPELINE_ERROR`, `STREAM_ERROR` — `rag_analysis/views.py:593,604` SSE 이벤트 페이로드 내부 에러. HTTP 응답 자체는 200 OK. envelope 정책 미적용.

---

## 4. custom_exception_handler 설계

### 4.1 위치 및 등록

```python
# config/exception_handler.py (신규)
from rest_framework.views import exception_handler as drf_default_handler
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    """
    DRF 기본 핸들러를 호출 후 응답 본문을 표준 형태로 정규화.

    표준 형태:
      { "detail": str, "code": str, "errors"?: dict, "status_code": int }
    """
    response = drf_default_handler(exc, context)
    if response is None:
        # DRF가 처리 못한 예외 (대부분 500). 기본 handler가 None을 반환하면
        # Django 미들웨어가 500 페이지를 렌더하므로 그대로 둔다.
        return None

    payload = {"status_code": response.status_code}

    if isinstance(exc, ValidationError):
        # ValidationError detail은 dict 또는 list. 통일 처리:
        detail_obj = response.data
        if isinstance(detail_obj, dict):
            # field-level: {"email": ["..."], "password": ["..."]}
            payload["detail"] = "Validation failed."
            payload["code"] = getattr(exc, "default_code", "validation_error")
            payload["errors"] = detail_obj
        elif isinstance(detail_obj, list):
            # non-field: ["msg1", "msg2"]
            payload["detail"] = "; ".join(str(m) for m in detail_obj)
            payload["code"] = getattr(exc, "default_code", "validation_error")
    else:
        # NotFound, NotAuthenticated, PermissionDenied, Throttled, APIException 서브클래스
        detail_obj = response.data
        if isinstance(detail_obj, dict) and "detail" in detail_obj:
            payload["detail"] = str(detail_obj["detail"])
            payload["code"] = getattr(exc, "default_code", None) or \
                              (getattr(detail_obj["detail"], "code", None) if hasattr(detail_obj["detail"], "code") else None) or \
                              "error"
        else:
            payload["detail"] = str(detail_obj)
            payload["code"] = getattr(exc, "default_code", "error")

    response.data = payload
    return response
```

```python
# config/settings.py
REST_FRAMEWORK = {
    # ...기존 설정...
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
}
```

### 4.2 변환 예시

| Raise | HTTP | 응답 본문 |
|-------|------|----------|
| `raise NotFound("Stock not found")` | 404 | `{"detail":"Stock not found","code":"not_found","status_code":404}` |
| `raise NotAuthenticated()` | 401 | `{"detail":"Authentication credentials were not provided.","code":"not_authenticated","status_code":401}` |
| `raise PermissionDenied("Admin only")` | 403 | `{"detail":"Admin only","code":"permission_denied","status_code":403}` |
| `raise ValidationError({"email":["required"]})` | 400 | `{"detail":"Validation failed.","code":"validation_error","errors":{"email":["required"]},"status_code":400}` |
| `raise ValidationError("Bad input")` | 400 | `{"detail":"Bad input","code":"validation_error","status_code":400}` |
| `raise CacheError("Redis timeout")` | 500 | `{"detail":"Redis timeout","code":"cache_error","status_code":500}` |
| `raise Throttled(wait=30)` | 429 | `{"detail":"Request was throttled. Expected available in 30 seconds.","code":"throttled","status_code":429}` |

### 4.3 안전성

- DRF 기본 handler가 `None` 반환(예: AssertionError, ZeroDivisionError 등 비-API 예외) → Django 500 페이지 → 운영에서 Sentry로 잡힘. handler 자체가 추가 위험 없음.
- 기존 `raise NotFound("...")` 41건은 변환 결과 `detail` 메시지 동일, `code`/`status_code` 키만 추가됨 → FE 호환 (기존 분기는 `detail` 기반).
- 기존 wrapping `{success: False, error: {code, message}}` 응답을 받던 FE 호출자 → 본문 키 변경(`error.code` → `code`, `error.message` → `detail`). PR-A/B에서 FE 동시 변경 필수.

---

## 5. ErrorSerializer (drf-spectacular)

```python
# config/serializers.py 또는 각 앱 serializers.py
from rest_framework import serializers

class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField(required=False)
    errors = serializers.DictField(required=False, child=serializers.ListField(child=serializers.CharField()))
    status_code = serializers.IntegerField()
```

```python
# 신규 view 작성 시 일관 적용
@extend_schema(
    responses={
        200: MyResourceSerializer,
        400: ErrorSerializer,
        404: ErrorSerializer,
        500: ErrorSerializer,
    }
)
def my_view(request): ...
```

`contracts/shared-types.ts`에도 동일 타입 추가:
```ts
export interface ApiError {
  detail: string
  code?: string
  errors?: Record<string, string[]>
  status_code: number
}
```

---

## 6. FE 마이그레이션

### 6.1 `authAxios.ts`

변경 없음. interceptor가 unwrap 안 하는 현 동작이 정답. 단, 에러 분기 가이드를 주석으로 추가:

```ts
// 에러 분기: error.response.data.code (도메인 코드) 또는 error.response.status (HTTP)
```

### 6.2 `ragService.ts` — interceptor 제거

현재 (라인 39-46):
```ts
api.interceptors.response.use(
  (response) => {
    if (response.data && response.data.success === true && response.data.data !== undefined) {
      response.data = response.data.data
    }
    return response
  },
  ...
)
```

PR-A 후:
```ts
// interceptor 제거 — 응답이 이미 평탄. 호출자는 response.data 그대로 사용.
```

호출자 측은 변경 불필요. `getList()`에서 `response.data`가 곧 배열 또는 페이지네이션 객체.

### 6.3 `screenerService.ts` — `.data.data` → `.data`

8개 메서드에서 `return response.data.data` → `return response.data`. serverless 마이그레이션 PR(PR-B~F)와 동시 작업.

### 6.4 에러 처리 패턴 (앱 전반)

```ts
try {
  const res = await authAxios.get('/stocks/AAPL/')
  return res.data
} catch (err) {
  if (isAxiosError(err) && err.response?.data) {
    const apiErr = err.response.data as ApiError
    if (apiErr.code === 'not_found') { /* ... */ }
    if (apiErr.status_code === 429) { /* retry with backoff */ }
  }
  throw err
}
```

---

## 7. 적용 순서 (PR 분할)

```
PR-0 (선결, 외부 호환): EXCEPTION_HANDLER 등록 + APIException 서브클래스 정의 + ErrorSerializer
   ↓ (기존 raise NotFound 41건이 새 형태로 변환됨 — detail은 동일, code/status_code 추가만)

PR-A: rag_analysis 36건 + ragService interceptor 제거 + 도메인 예외 사용
   ↓ (가장 격리된 단일 파일, 회귀 위험 최소)

PR-B~F: serverless/views.py 117건 분할 (movers / screener / chain_sight / institutional / theme)
   ↓ (screenerService.ts 등 FE 호출자 동시 수정)

PR-G: serverless/views_admin.py 1건 + 계약 테스트 추가 + 최종 정리
```

**PR-0이 PR-A보다 먼저 가야 하는 이유**:
- PR-A에서 `Response(create_error_response(...))` → `raise NotFound(...)`로 바꾸는데, EXCEPTION_HANDLER 없으면 DRF 기본 `{detail: "..."}` 응답이 나가서 `code`/`status_code` 키가 빠짐.
- PR-0은 기존 41건 raise를 새 형태로 변환할 뿐 외부 인터페이스를 의미적으로 깨지 않음(`detail` 동일).

---

## 8. 계약 테스트

`tests/contracts/test_response_envelope.py` (신규, PR-G에서):

```python
@pytest.mark.django_db
def test_error_404_envelope(client, auth_user):
    client.force_login(auth_user)
    resp = client.get('/api/v1/stocks/NONEXISTENT/')
    assert resp.status_code == 404
    body = resp.json()
    assert set(body.keys()) >= {'detail', 'code', 'status_code'}
    assert body['code'] == 'not_found'
    assert body['status_code'] == 404

@pytest.mark.django_db
def test_error_validation_field_errors(client, auth_user):
    client.force_login(auth_user)
    resp = client.post('/api/v1/users/', data={'email': 'bad'})
    assert resp.status_code == 400
    body = resp.json()
    assert body['code'] == 'validation_error'
    assert 'errors' in body

@pytest.mark.django_db
def test_domain_exception_cache_error(client, auth_user, monkeypatch):
    """rag_analysis cache 실패 → CacheError → code='cache_error', status=500"""
    ...
```

---

## 9. 예외 / 명시적 제외

| 영역 | 처리 |
|------|------|
| `marketpulse/api/views/cards.py:_envelope` | 유지. v2 API contract에 별도 envelope (`{_meta, data}`) 명시. v1 정책과 분리. |
| `portfolio/views.py` (순수 Django JsonResponse) | 본 정책 적용 불가(DRF 미사용). 향후 DRF 마이그레이션 시 통합. |
| SSE 스트림 이벤트 페이로드 (`PIPELINE_ERROR`, `STREAM_ERROR`) | HTTP 200 + 이벤트 내부 에러 객체. envelope 정책 미적용. |
| 비즈니스 상태 응답 (`not_in_universe`, `no_data`) | PR-#14에서 422/404로 정상화 완료. 본 정책에서 추가 변경 없음. |

---

## 10. DECISIONS.md 추가 항목 초안

```markdown
### API 응답 표준: DRF 평탄 + 통일 에러 envelope
- **성공**: `serializer.data` 또는 dict 평탄 반환 (DRF 표준)
- **에러**: `{detail, code?, errors?, status_code}` 단일 형태
- **변환**: `config.exception_handler.custom_exception_handler` (REST_FRAMEWORK.EXCEPTION_HANDLER 등록)
- **도메인 코드 보존**: `rag_analysis/exceptions.py`, `serverless/exceptions.py`에 APIException 서브클래스
- **Why**: 2026-05-06 api_consistency_audit P1 #14 — 3종 혼재(W/D/C)로 FE가 라우트별 unwrap 분기 필요. WRAP 사용 6 파일만 → 마이그레이션 비용 적음. DRF 표준 정렬로 신규 view 결정 비용 0.
- **예외**: Market Pulse v2 cards `_envelope` 유지(별도 v2 contract), SSE 이벤트 페이로드 제외.
- 📎 상세: `docs/features/api_envelope/policy.md`
```

---

## 11. PROGRESS.md / TASKQUEUE.md 반영

- PROGRESS.md `audit P0 후속 큐` #14 항목을 본 정책 채택 + PR-0/A/B-F/G 분할로 갱신
- common-bugs.md에는 추가 항목 없음 (정책 결정이라 버그 패턴 아님)
