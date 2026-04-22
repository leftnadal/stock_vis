# API 응답 일관성 감사 보고서

- **감사일**: 2026-04-22
- **감사 범위**: Django REST Framework 기반 26개 views 파일 (stocks/users/macro/news/rag_analysis/serverless/chainsight/validation/sec_pipeline/thesis/graph_analysis/metrics/config)
- **감사 방식**: 코드 정적 분석 (읽기 전용)
- **전역 설정 확인**: `config/settings.py:331` — `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS`, `DEFAULT_RENDERER_CLASSES`, `EXCEPTION_HANDLER` 미설정

---

## 요약

Stock-Vis 백엔드는 **12개 앱에 걸쳐 최소 5종의 응답 래핑 패턴**과 **5종의 에러 키 스타일**이 혼재하며, 프로젝트 전역 기본 페이지네이션이 설정되지 않은 상태에서 모든 목록 API가 개별적으로 페이지네이션을 처리(또는 누락)하고 있다. 동일 앱 내에서도 패턴이 뒤섞여 있어 프론트엔드 API 소비 레이어에서 응답 형태별 분기 처리가 불가피하다.

**심각 이슈 3건**
- **S1**: `validation/api/views.py:64-85`에서 실패/누락 상황에 `HTTP_200_OK` 반환 (시맨틱 위반)
- **S2**: 전체 프로젝트에 `pagination_class` 지정 view 0개, `DEFAULT_PAGINATION_CLASS` 설정도 없음 → 목록 API 대부분 전체 로드 또는 하드코딩 슬라이스(`[:50]`, `[:20]`)
- **S3**: POST 생성 엔드포인트 중 `HTTP_201_CREATED` 사용처는 `users/views.py`(4곳), `rag_analysis/views.py`(1곳), `serverless/views_admin.py:568`만이며, 대부분 생성/삭제에서 200만 반환

**주요 이슈 2건**
- **M1**: 에러 키 혼용 (`error` / `message` / `detail` / 중첩 `error.code`·`error.message`) — 동일 파일 내에서도 혼용
- **M2**: 응답 본문 래핑 비일관 (`serializer.data` 직접 / 평면 dict / `success`+`data`+`meta` 3단 구조 / 커스텀 헬퍼) — 동일 앱 내에서도 파일마다 다름

---

## 앱별 응답 패턴 매트릭스

응답 패턴 분류:
- **A**: `Response(serializer.data)` DRF 직렬화 결과 직접 반환
- **B**: 평면 dict `Response({'key': value, ...})` 직접 반환 (래핑 없음)
- **C**: 표준 성공 래핑 `{'success': True, 'data': ..., 'meta': ...}`
- **D**: 커스텀 헬퍼 함수(`create_success_response` 등) 기반 구조화 래핑
- **E**: 수동 페이지네이션 래핑 `{'results': [...], 'pagination': {...}}`

| 앱 | 파일 | 엔드포인트 수 | 주 패턴 | 혼용 여부 | 비고 |
|---|---|---:|:---:|:---:|---|
| stocks | views.py | 9 | B (+ 일부 A, D-유사) | ● 심함 | `error` 단순 문자열과 `error.code/message` 중첩 공존 (L204 vs L586) |
| stocks | views_exchange.py | 5 | C | – | `{'success', 'data', 'meta'}` 일관 |
| stocks | views_screener.py | 6 | C | ◐ 일부 | L94-106 vs L150-157 `data` 내부 구조 상이 |
| stocks | views_market_movers.py | 1 | A | – | serializer.data만 반환, 다른 stocks 패턴과 이질 |
| stocks | views_eod.py | 3 | B | – | 하드코딩 슬라이스 `[:50]` 사용 |
| stocks | views_indicators.py | 3 | B | – | 캐시 히트 시 status 생략 |
| stocks | views_search.py | 4 | B | – | `{'count', 'results'}` 자체 구조 |
| stocks | views_fundamentals.py | 5 | C | – | exchange와 동일, 일관 ✓ |
| stocks | views_mvp.py | 4 | B | – | 에러 핸들링 최소 |
| users | views.py | 27 | A + B + E | ● 심함 | Watchlist 수동 페이지네이션(L602-620, L822-840), `{'ok': ..., 'user': ...}`(L161-162), `detail`(L513)/`message`(L208)/`error` 혼용 |
| macro | views.py | 8 | A | – | 모든 에러 `{'error': ...}` 일관 |
| news | api/views.py | 5+ | A + B | ◐ | ViewSet 기반, 캐시 히트 시 원본 반환 |
| news | views.py | 0 | – | – | 빈 파일 |
| rag_analysis | views.py | 13 | D + E | – | `create_success_response`/`create_error_response` 헬퍼로 가장 일관된 앱, 페이지네이션 수동 구현(L796-826) |
| serverless | views.py | 함수형 다수 | C + D-유사 | ◐ | `{'success': False, 'error': {'code', 'message'}}` (L70-75) |
| serverless | views_admin.py | 11 | B | – | 201 사용 1건(L568), 204 사용 |
| chainsight | views.py | 0 | – | – | 빈 파일 |
| chainsight | api/views.py | 6 | B | – | 모두 `{'error': ...}` 일관, SignalFeedView L568-574 수동 페이지네이션 |
| chainsight | views.py (루트) | 0 | – | – | 빈 파일 |
| validation | views.py | 0 | – | – | 빈 파일 |
| validation | api/views.py | 6 | B | ● 심함 | **L64-67, L82-85에서 에러 상황에 200 반환** (S1), 에러 키 혼용 |
| sec_pipeline | views.py | 2 (APIView 1) | B | – | 202 Accepted 적절히 사용 (L40-41) |
| thesis | views/thesis_views.py | 3 ViewSet + 1 action | A + B | ● | CRUD는 A, `close`/`auto` 액션은 B (L143, L268-271) |
| thesis | views/conversation_views.py | 4 | B | ◐ | 서비스 반환 dict 직접 래핑, fallback 구조 변형(L376-380) |
| thesis | views/monitoring_views.py | 3 + 1 | B | – | `status` 모듈 미사용, 하드코딩 `[:50]`(L238) |
| graph_analysis | views.py | 0 | – | – | 빈 파일 |
| metrics | views.py | 0 | – | – | 빈 파일 |
| config | views.py | 2 | `JsonResponse` | – | health/api_root, DRF 미사용 |

> 범례: ● 심함 (파일 내 3가지 이상 패턴), ◐ 일부 (2가지 패턴), – 단일 패턴

---

## HTTP 상태 코드 일관성

### `status` 모듈 사용 여부

| 상태 | 앱/파일 |
|---|---|
| 일관 사용 | stocks/views.py · views_exchange · views_screener · views_market_movers · views_eod · views_indicators · views_fundamentals · users · macro · rag_analysis · serverless/views_admin · chainsight/api · validation/api · sec_pipeline · thesis/thesis_views · thesis/conversation |
| 선택적 사용 (생략 잦음) | stocks/views_search · stocks/views_mvp · news/api/views · thesis/monitoring_views (status 모듈 import 없음) |
| 하드코딩 숫자 | 확인된 사용처 없음 — 대부분 `status.HTTP_xxx` 사용 |

### POST 생성 시 201 사용

**201 CREATED 사용처 (총 6곳)**
- `users/views.py:105, 288, 631, 723` (회원가입, Watchlist 생성 등)
- `rag_analysis/views.py` (POST 생성 엔드포인트)
- `serverless/views_admin.py:568` (카테고리 생성)

**200 OK로 생성 응답 반환 (잘못된 관행)**
- `stocks/views.py:986` `SyncAPIView POST` — `HTTP_200_OK` / `HTTP_500_INTERNAL_SERVER_ERROR`로 성공/실패 구분하지만 생성 의미 201 미사용
- `thesis/views/thesis_views.py` — ViewSet 기본 동작에만 의존, `close`/`auto` 커스텀 액션은 200
- 대부분의 함수형 POST 엔드포인트

### 에러 상태 코드 사용 현황

| 코드 | 사용 빈도 | 대표 사용처 |
|---|---|---|
| `HTTP_400_BAD_REQUEST` | 매우 많음 | stocks/views_screener.py:L65, L264, L313, L364, L418, L468; validation/api:L189, L473, L509 |
| `HTTP_401_UNAUTHORIZED` | 적음 | validation/api/views.py:L463, L488 |
| `HTTP_403_FORBIDDEN` | 거의 없음 | 드문 사용 |
| `HTTP_404_NOT_FOUND` | 많음 | chainsight/api:L67, L113; validation/api:L59, L180, L324 |
| `HTTP_500_INTERNAL_SERVER_ERROR` | 중간 | stocks/views.py:L986, macro 전반 |
| `HTTP_503_SERVICE_UNAVAILABLE` | 드묾 | stocks/views_exchange.py:L58; chainsight/api:L381, L560 |
| `HTTP_202_ACCEPTED` | 단일 | sec_pipeline/views.py:L40-41 (비동기 트리거) — 좋은 관행 |
| `HTTP_204_NO_CONTENT` | 적음 | serverless/views_admin.py (삭제) |

### 심각한 위반 사항 (S1)

**`validation/api/views.py:64-67, 82-85`** — 데이터 없음/엔진 실패 상황에서 `HTTP_200_OK` 반환

```python
# L64-67 예시 (감사 시 확인된 패턴)
return Response({
    'symbol': symbol,
    'error': '...',
    'message': '...'
}, status=status.HTTP_200_OK)
```
→ 프론트엔드가 `response.ok`만 확인하면 오류를 성공으로 오인.

### 상태 코드 누락

- `chainsight/api/views.py:L229` try/except 블록 내 예외 응답에 status 미지정
- `thesis/views/monitoring_views.py` — `status` 모듈 import 없이 모든 응답 암묵적 200
- `stocks/views_indicators.py:L39` 캐시 히트 응답 시 status 생략

---

## 에러 응답 형식

### 관찰된 5가지 스타일

| 스타일 | 형태 | 사용처 |
|---|---|---|
| **E1 평면 error** | `{'error': 'message'}` | 대다수 (macro, stocks 대부분, chainsight, users 다수) |
| **E2 평면 message** | `{'message': '...'}` | stocks/views.py:L174, L182; users/views.py:L208 |
| **E3 평면 detail** | `{'detail': '...'}` | users/views.py:L513 |
| **E4 중첩 code/message** | `{'error': {'code': '...', 'message': '...', 'details': ...}}` | stocks/views.py:L580-596; rag_analysis/views.py (헬퍼); serverless/views.py:L70-75 |
| **E5 다중 필드** | `{'symbol': ..., 'error': ..., 'message': ...}` | validation/api/views.py:L64-67, L82-85, L328-332 |

### 동일 파일 내 혼용 예시

- **`stocks/views.py`**:
  - L174, L182 → `{'message': ...}`
  - L204-208 → `{'error': '...'}`
  - L586-596 → `{'error': {'code': ..., 'message': ..., 'details': ...}}`
- **`users/views.py`**:
  - L167, L209, L536 → `{'error': ...}`
  - L208 → `{'message': ...}`
  - L513 → `{'detail': ...}`
- **`validation/api/views.py`**:
  - L59, L180, L189, L324 → `{'error': ...}`
  - L64-67 → `{'symbol', 'error', 'message'}` 혼합
  - L542-546 → 별도 구조

### DRF 기본 예외 처리

- `config/settings.py:331`의 `REST_FRAMEWORK` 설정에 `EXCEPTION_HANDLER` 미지정
- 대부분의 view가 try/except로 직접 커스텀 에러 응답 생성 → DRF 기본 `ValidationError`/`NotFound` 핸들러 통과 시 `{'detail': ...}` 형식이 출현하지만, 커스텀 경로는 `{'error': ...}`라서 **동일 엔드포인트에서도 실패 원인에 따라 에러 키가 달라질 수 있음**.

---

## 페이지네이션 현황

### 전역 설정

`config/settings.py:331-339`
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
}
```
→ **`DEFAULT_PAGINATION_CLASS` 미설정**, `PAGE_SIZE` 미설정.

### 프로젝트 전체 검색 결과

`grep -rn "pagination_class|PageNumberPagination|CursorPagination|LimitOffsetPagination"` 결과 **0건** — 어떤 view도 DRF 공식 페이지네이션을 명시적으로 사용하지 않음.

### 목록 API 처리 유형

| 처리 방식 | 사용처 | 문제점 |
|---|---|---|
| 전체 반환 (`.all()` / `.filter()` → list) | stocks/views_exchange (5개 엔드포인트), validation/api/views.py:L426, L554, chainsight/api 대부분, thesis ViewSets 전체 | 데이터 증가 시 성능 폭발 |
| 하드코딩 슬라이스 | stocks/views_eod.py:L78 `[:50]`, stocks/views_mvp.py:L41 `[:20]`, thesis/monitoring_views.py:L238 `[:50]`, thesis/conversation_views.py:L199-202 `[:12]` | 페이지 이동 불가, 프론트 무한스크롤/페이지네이션 구현 불가 |
| 수동 페이지네이션 (Django Paginator) | users/views.py:L602-620, L822-840 (Watchlist); rag_analysis/views.py:L796-826 (UsageHistoryView); chainsight/api/views.py:L568-574 (SignalFeedView) | 응답 형식 제각각 (`{'results', 'pagination'}` 구조 앱별로 상이) |
| `limit` 파라미터만 | stocks/views_screener.py — cursor 없음 | 다음 페이지 이동 표준 없음 |
| `ListAPIView` 기본 (페이지네이션 없는) | stocks/views.py:L75-105 `StockListAPIView` — `ListAPIView` 상속이지만 전역 설정 없으므로 페이지네이션 무효 | 전체 종목 리스트 한 번에 반환 |

### 추정 위험 지점

- **Stock 종목 수가 수천 개**일 경우 `StockListAPIView`는 전체 직렬화 → 메모리/응답 지연
- `chainsight/api/views.py`의 그래프 엔드포인트가 전체 노드를 반환하면서 캐싱에만 의존
- `validation/api/views.py:L554`가 peer set 전체를 페이지네이션 없이 반환

---

## 권고사항

### P0 (즉시 수정 권장)

1. **S1 수정 — 200 OK + 에러 혼합 제거**
   - `validation/api/views.py:L64-67, L82-85`: 데이터 없음은 `HTTP_404_NOT_FOUND` 또는 `HTTP_422_UNPROCESSABLE_ENTITY`로 변경
   - 프론트엔드가 `response.ok`만으로 성공 판정 가능하도록 시맨틱 일치

2. **전역 예외 핸들러 도입**
   - `config/settings.py`에 `'EXCEPTION_HANDLER': 'config.exceptions.unified_exception_handler'` 추가
   - 모든 에러 응답을 `{'error': {'code': '<ENUM>', 'message': '...', 'details': {...}}}` 단일 형식으로 정규화

### P1 (다음 스프린트)

3. **응답 래핑 표준 선정 & 문서화**
   - 후보 A: `rag_analysis/views.py`의 `create_success_response`/`create_error_response` 헬퍼 프로젝트 공통화
   - 후보 B: `stocks/views_exchange.py` / `views_fundamentals.py`의 `{'success', 'data', 'meta'}` 3단 구조 표준화
   - **선정 후 `docs/architecture/api_response_contract.md` 신규 작성 → `contracts/` 하위 OpenAPI 스펙에 반영**

4. **POST 생성 엔드포인트 201 일괄 적용**
   - `thesis/views/thesis_views.py` ViewSet `create()` 오버라이드 혹은 기본 동작 검증
   - `stocks/views.py:L986` `SyncAPIView` → `HTTP_201_CREATED` 적용 검토

5. **전역 페이지네이션 클래스 설정**
   - `DEFAULT_PAGINATION_CLASS = 'rest_framework.pagination.PageNumberPagination'`
   - `PAGE_SIZE = 50`
   - 시계열 API는 `CursorPagination`으로 개별 지정

### P2 (기술 부채 장기 상환)

6. **하드코딩 슬라이스 제거**
   - `stocks/views_eod.py:L78`, `stocks/views_mvp.py:L41`, `thesis/views/monitoring_views.py:L238`, `thesis/views/conversation_views.py:L199-202`
   - `?limit=&offset=` 쿼리 파라미터로 전환

7. **수동 페이지네이션 통합**
   - `users/views.py`, `rag_analysis/views.py`, `chainsight/api/views.py` 각자의 `{'results', 'pagination'}` 구조를 DRF 표준 `{'count', 'next', 'previous', 'results'}`로 통일

8. **에러 키 혼용 제거**
   - 동일 파일 내 `error`/`message`/`detail` 혼용: `stocks/views.py`, `users/views.py`, `validation/api/views.py` 우선 정리

9. **status 모듈 누락 파일 보강**
   - `thesis/views/monitoring_views.py` — `from rest_framework import status` 추가 후 의미 있는 상태 코드 명시

### P3 (빈 파일 정리)

10. **불필요한 빈 views.py 제거 또는 실제 구현 위치 주석**
    - `chainsight/views.py`, `validation/views.py`, `news/views.py`, `graph_analysis/views.py`, `metrics/views.py` — 실제 API는 `<app>/api/views.py`에 있음을 파일 상단에 명시 또는 파일 삭제

---

## 감사 한계 및 주의

- **정적 분석 한정**: 실제 응답 본문은 런타임에서만 확인 가능 — 본 보고서는 `Response(...)` 호출 시점의 구조만 기록
- **서비스 레이어 미추적**: `thesis/views/conversation_views.py`는 서비스에서 dict를 받아 그대로 래핑하므로, 실제 응답 구조 완전 파악에는 services 계층 분석 필요
- **DRF Renderer 영향**: `DEFAULT_RENDERER_CLASSES` 미설정 → `BrowsableAPIRenderer`가 프로덕션에도 노출될 가능성 (본 감사 범위 외, 별도 보안/성능 감사 필요)
- **OpenAPI 스펙과 대조 미수행**: `contracts/` 디렉터리에 스펙이 존재하는 경우 실제 구현과 스펙 간 드리프트 추가 감사 권장 (본 감사에는 포함하지 않음)
