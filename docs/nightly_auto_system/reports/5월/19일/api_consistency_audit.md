# API 응답 일관성 감사 보고서

작성일: 2026-05-19
범위: `views*.py` 25개 파일 (총 13,047 LOC), `Response()` 호출 423건

## 요약

본 감사에서는 Django REST Framework 백엔드의 응답 일관성을 5개 축(래핑 패턴, HTTP 상태 코드, 에러 응답, 페이지네이션, 뷰 구현 스타일)으로 점검했다. 결론은 한 줄로: **앱별로 다른 컨벤션이 공존하고 있으며, 동일 도메인 내에서도 일관성이 깨져 있다.**

핵심 발견:

1. **응답 래핑 불일치** — `{'success': True, ...}` 형식은 `stocks/views_fundamentals.py`, `stocks/views_screener.py`, `stocks/views_exchange.py` 3개 파일(17건)에서만 사용되고, 나머지 22개 파일은 raw serializer 데이터를 직접 반환한다. 같은 `stocks/` 앱 안에서도 `views.py`(직접 반환) vs `views_screener.py`(래핑)로 갈라져 있다.
2. **HTTP 201 누락** — POST 생성 엔드포인트 다수가 200을 반환한다. `status.HTTP_201_CREATED` 사용처는 14건뿐이며 `users/views.py`(6), `rag_analysis/views.py`(4), `serverless/views.py`(3), `serverless/views_admin.py`(1)에 집중되어 있다. 다른 앱의 POST는 모두 기본 200.
3. **하드코딩 상태 코드 35건** — `portfolio/views.py`(32건)와 `sec_pipeline/views.py`(3건)가 `status.HTTP_*` 모듈 대신 `status=400`, `status=500` 같은 정수 리터럴을 사용한다. `portfolio/views.py`는 추가로 DRF `Response` 대신 `JsonResponse` 32건을 쓴다.
4. **페이지네이션 사실상 부재** — `pagination_class` 선언은 단 2건(`stocks/views.py:91`, `news/api/views.py:60`). `config/settings.py:348` `REST_FRAMEWORK` 블록에 `DEFAULT_PAGINATION_CLASS`/`PAGE_SIZE`가 **설정되어 있지 않다**. 즉 list 엔드포인트들이 전체 결과를 반환한다(DoS·메모리 위험).
5. **`@api_view` 함수형 뷰 52건이 모두 `serverless/views.py` 한 파일에 집중** — 다른 앱은 클래스 기반(APIView 117건)을 쓴다. 단일 도메인 내에서 스타일이 갈라진 게 아니라, 앱 자체가 다른 컨벤션을 채택했다.

전체 23개 운영 가능 앱 중 **응답 컨벤션이 일관적인 앱은 0개**다(가장 일관된 `validation/api/views.py`도 `{'error': ...}` 형식만 통일됨, 페이지네이션·201 없음).

---

## 앱별 응답 패턴 매트릭스

| 앱 / 파일군 | 응답 래핑 | 201 사용 | 에러 형식 | 페이지네이션 | 뷰 스타일 | 일관성 등급 |
|---|---|---|---|---|---|---|
| `metrics/` | (뷰 없음, 3 LOC) | — | — | — | — | N/A |
| `rag_analysis/views.py` | 직접 + 일부 `{'message': ...}` | ✓ 4건 | `{'error': ...}` / `{'message': ...}` 혼용 | 없음 | APIView 19 | 中 |
| `config/views.py` | 직접 | — | — | 없음 | (헬스체크 등) | 中 |
| `serverless/views.py` | 직접 / `{'status': 'error', 'error': ...}` 혼용 | ✓ 3건 (line 921, 1221, 1525) | `{'error': ...}`/`{'message': ...}` 혼용 | 없음 | **`@api_view` 52건** (유일) | **下** |
| `serverless/views_admin.py` | 직접 | ✓ 1건 (line 565) | `{'error': ...}` | 없음 | APIView 45 | 中 |
| `chainsight/api/views.py` | 직접 | 없음 | `{'error': ...}` | 없음 | APIView 20 | 中 |
| `stocks/views.py` | 직접 + `{'success': False}` 2건 | 없음 | `{'error': ...}` | **✓ `StockListPagination`** (line 91) | APIView 25 | 中 |
| `stocks/views_fundamentals.py` | **`{'success': True, ...}` 5건** | 없음 | `{'success': False, 'error': ...}` (래핑 일관) | 없음 | APIView 15 | 上(내부 일관) |
| `stocks/views_screener.py` | **`{'success': True, ...}` 7건** | 없음 | `{'success': False, 'error': ...}` | 없음 | APIView 15 | 上(내부 일관) |
| `stocks/views_exchange.py` | **`{'success': True, ...}` 5건** | 없음 | `{'success': False, 'error': ...}` | 없음 | APIView 13 | 上(내부 일관) |
| `stocks/views_eod.py`, `views_indicators.py`, `views_mvp.py`, `views_search.py`, `views_market_movers.py` | 직접 | 없음 | `{'error': ...}` | 없음 | APIView 28 | 中 |
| `macro/views.py` | 직접 | 없음 | `{'error': ...}` | 없음 | APIView 10 | 中 |
| `news/api/views.py` | serializer 직접 | 없음 | DRF 기본 | **✓ `NewsArticlePagination`** (line 60) | ViewSet 1 + APIView | 上 |
| `users/views.py` | 직접 / 일부 `{'message': ...}` | **✓ 6건** (회원가입/포트폴리오/워치리스트) | `{'error': ...}` | 없음 | APIView 27 | 中 |
| `portfolio/views.py` | **`JsonResponse(dict, ...)`** (DRF 아님) | 없음 | `{"error": "..."}` + `{"detail": ...}` 혼용 (line 107) | 없음 | Django View | **下** (DRF 패턴 위반) |
| `sec_pipeline/views.py` | 직접 | 없음 + **HTTP 202** 사용 (line 45) | `{'error': ...}` / `{'message': ...}` | 없음 | APIView 1 | 中 |
| `graph_analysis/views.py` | (3 LOC, 미구현) | — | — | — | — | N/A |
| `validation/api/views.py` | 직접 | 없음 | `{'error': ...}` (23건, 일관) + `{'symbol': ..., 'error': ...}` 12건 변형 | 없음 | APIView 23 | 上(에러만 일관) |

**일관성 등급 범례:**
- 上: 단일 컨벤션을 일관 적용 (그러나 다른 앱과 어긋남)
- 中: 단일 컨벤션이지만 변형/혼용 일부 존재
- 下: 다중 컨벤션 혼용, DRF 표준 이탈

---

## HTTP 상태 코드 일관성

### `status.HTTP_*` 모듈 사용 (정상 패턴)

```text
HTTP_201_CREATED: 14건
  users/views.py:107, 295, 639, 731, 918, 1040   ← 가장 일관된 사용
  rag_analysis/views.py:63, 137, 291, 396
  serverless/views.py:921, 1221, 1525
  serverless/views_admin.py:565

HTTP_400_BAD_REQUEST: ~24건
HTTP_404_NOT_FOUND:   ~15건
HTTP_500_INTERNAL_SERVER_ERROR: ~11건
```

### 하드코딩된 정수 상태 코드 (안티 패턴) — 총 35건

```text
portfolio/views.py:49   status=400  (deal_validation 실패)
portfolio/views.py:55   status=503  (외부 API down)
portfolio/views.py:57   status=500
portfolio/views.py:59   status=200
portfolio/views.py:107  status=429  ("budget_exceeded")
portfolio/views.py:121  status=200
... (portfolio/views.py 32건 전부)

sec_pipeline/views.py:45  status=202  (Celery 비동기 작업 시작)
sec_pipeline/views.py:49  status=200
sec_pipeline/views.py:51  status=200
```

→ `portfolio/views.py`는 DRF `Response` 대신 `JsonResponse`(32건)를 사용하고, 그래서 `status.*` 상수 import 없이 정수로 처리한다. DRF 트랜잭션·렌더러·throttle 미작동 위험.

### POST/생성 엔드포인트에서 201 누락

- `stocks/views_screener.py:281` 등 `save_screener`, `save_thesis` 류는 200으로 반환 (의도된 동작인지 불명확)
- `chainsight/api/views.py`의 mutation 엔드포인트 다수 200 반환
- 반면 `users/views.py:918, 1040`은 `HTTP_201_CREATED if created else HTTP_200_OK`로 모범적인 분기

---

## 에러 응답 형식

DRF 컨벤션(`{'detail': str}`) 대신 **`{'error': str}`이 사실상의 사내 표준**이다.

```text
Response({'error': ...}) — 33+ (DRF Response 호출만 카운트, validation/portfolio/chainsight/admin 등)
Response({'message': ...}) — 5건 (validation/api/views.py:1, serverless/views.py:4)
Response({'detail': ...}) — 0건 (단, DRF 예외 핸들러 자동 생성분 제외)
{'success': False, 'error': ...} — 9건 (stocks/views_*.py 패밀리)
{'symbol': ..., 'error': ...} — 12건 (validation/api/views.py 변형)
{'status': 'error', 'error': ...} — 1건 (serverless/views.py:2018)
JsonResponse({"error": ...}) — portfolio/views.py 다수
{"error": "budget_exceeded", "detail": str(exc)} — portfolio/views.py:107 (혼합형)
```

**문제점:**

1. **DRF 표준 `detail` 키와 사내 `error` 키가 공존** — `raise NotFound(...)`이나 권한 거부 시 DRF는 `{'detail': '...'}`를 자동 생성하지만, 명시적 에러는 `{'error': ...}`를 쓴다. 프론트엔드는 두 키를 모두 처리해야 한다.
2. **`portfolio/views.py:107`** 한 줄에 `{"error": "budget_exceeded", "detail": str(exc)}`로 두 키가 동시 등장 — 형식 통일 의지가 부재함을 보여주는 대표 사례.
3. **`stocks/views_*` 패밀리의 `{'success': False, ...}`** — 프론트가 HTTP 상태 코드 대신 `success` 필드로 분기하게 만든다. 같은 앱 다른 파일(`stocks/views_eod.py`)은 `{'error': ...}`만 쓰므로, 프론트는 엔드포인트별로 다른 처리 로직을 가져야 한다.
4. **try/except 500 처리 비일관** — `serverless/views.py:623`은 `Response({'error': str(e)}, status=500)`, `serverless/views.py:2018`은 `{'status': 'error', 'error': str(e)}`. 예외 메시지를 그대로 노출하는 것 자체도 보안 리스크.

---

## 페이지네이션 현황

### 전역 설정 (config/settings.py:348-)

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (...),
    'DEFAULT_PERMISSION_CLASSES': [...],
    'DEFAULT_THROTTLE_RATES': {...},
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # ❌ DEFAULT_PAGINATION_CLASS 미설정
    # ❌ PAGE_SIZE 미설정
}
```

→ DRF가 자동 페이지네이션을 적용하지 않는다. 각 뷰에서 명시적으로 처리해야 함.

### 실제 적용

```text
stocks/views.py:91             pagination_class = StockListPagination   (page_size=50)
news/api/views.py:60           pagination_class = NewsArticlePagination (page_size=20)
```

전체 13,047 LOC, 117개 APIView, 52개 `@api_view`에서 **단 2건**만 명시 페이지네이션 적용.

### 위험한 무제한 반환 사례 (대표)

- `serverless/views.py` Market Movers·Screener 목록 — 결과 수백~수천 건을 한 번에 반환 (Lambda 전환 보류 중)
- `validation/api/views.py` peer group 멤버 목록 — 카테고리에 따라 수십~수백 종목
- `macro/views.py` 거시 시계열 — 모든 데이터 포인트 반환
- `chainsight/api/views.py` ETF/Supply Chain 관계 목록 — 종목당 수십~수백 노드
- `users/views.py` 포트폴리오/워치리스트 — 사용자당 무제한

→ 사용자 N명, 종목 M개 스케일이 커지면 응답 페이로드/메모리/네트워크가 선형 폭발. 캐시 미스 시 DB 풀스캔.

### 페이지네이션 사용 클래스

`PageNumberPagination` 2건만 확인됨. `CursorPagination`, `LimitOffsetPagination` 사용 0건.

---

## 권고사항

우선순위 순서 (위에서 아래로):

### P0 — 사용자 영향 즉시 발생 위험

1. **전역 페이지네이션 디폴트 설정** — `config/settings.py:REST_FRAMEWORK`에 다음을 추가:
   ```python
   'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
   'PAGE_SIZE': 50,
   ```
   단, 함수형 뷰(`@api_view`)는 자동 적용 안 됨 → `serverless/views.py` 52개 뷰는 개별 처리 필요.
2. **list 엔드포인트 무제한 반환 차단** — 우선 `serverless/views.py` Market Movers·Screener, `validation/api/views.py` peer 목록, `chainsight/api/views.py` 관계 목록에 `LimitOffsetPagination` 적용.

### P1 — 프론트엔드 통합 부담 감소

3. **에러 형식 단일화** — DRF 표준 `{'detail': str}`로 통일 권장. 또는 사내 표준 `{'error': str}`로 통일하되 DRF `EXCEPTION_HANDLER` 커스텀으로 자동 변환:
   ```python
   # config/exceptions.py
   def custom_exception_handler(exc, context):
       response = exception_handler(exc, context)
       if response and 'detail' in response.data:
           response.data = {'error': response.data['detail']}
       return response
   ```
   설정: `REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'config.exceptions.custom_exception_handler'`
4. **`{'success': True, ...}` 래핑 제거 또는 전체 적용** — 현재 `stocks/views_fundamentals.py`, `views_screener.py`, `views_exchange.py` 3개 파일만 사용. 둘 중 하나 선택:
   - **(권장)** 3개 파일에서 제거 → DRF 표준 따름. HTTP 상태 코드로 success/failure 표현.
   - 전체 적용 → 기존 컨벤션 유지 비용 큼.

### P2 — DRF 컨벤션 정렬

5. **`portfolio/views.py`를 DRF로 리팩터** — `JsonResponse` → `Response`, 하드코딩 정수 → `status.HTTP_*`. 32곳 일괄 치환.
6. **POST 생성 엔드포인트 201 적용** — `chainsight/api/views.py`, `stocks/views_screener.py`의 save_* 류, `serverless/views_admin.py` mutation 엔드포인트에서 `HTTP_201_CREATED` 사용. `users/views.py:918` 패턴(`HTTP_201_CREATED if created else HTTP_200_OK`) 채택 권장.
7. **`serverless/views.py`의 `@api_view` 패턴 정리** — 52개 함수형 뷰를 단계적으로 APIView 클래스 기반으로 마이그레이션 (Lambda 전환 시점과 연동 가능).

### P3 — 컨벤션 문서화

8. **`sub_claude_md/coding-rules.md`에 API 응답 컨벤션 섹션 추가** — 새 코드의 일관성 보장:
   - 성공 응답: 직접 데이터 반환 (`Response(serializer.data)`)
   - 에러 응답: `{'error': str}` + `status.HTTP_*` 명시
   - 생성: `HTTP_201_CREATED`
   - 목록: `pagination_class` 필수
   - `JsonResponse` 사용 금지 (DRF `Response`만)
   - try/except에서 `str(exc)` 직접 노출 금지 (메시지 sanitize)

### 참고: 영향 규모

| 권고 | 변경 파일 수 | 추정 LOC | 리스크 |
|---|---|---|---|
| P0-1 (전역 페이지네이션) | 1 | +2 | 하위호환 깨질 가능성 — 프론트 영향 검증 필요 |
| P0-2 (list 페이지네이션) | 4-5 | +20 | 프론트 페이징 UI 동시 변경 필요 |
| P1-3 (에러 단일화) | 1 + EXCEPTION_HANDLER | +30 | 낮음 (자동 변환) |
| P1-4 (`success` 래핑 제거) | 3 (stocks/views_*.py) | -17 | 프론트 응답 파서 수정 필수 |
| P2-5 (portfolio DRF화) | 1 | ~64 (32 × 2줄) | 중간 (테스트 재작성) |
| P2-6 (201 적용) | 5-8 | +30 | 낮음 |
| P2-7 (`@api_view` 마이그레이션) | 1 (serverless) | ~500 | 높음 — Lambda 전환과 연동 권장 |

---

## 부록 A — 도구·증거 출처

- `find` 결과: views*.py 25개 파일, 13,047 LOC
- `Grep` 카운트: `Response(`(423), `@api_view`(52), `APIView` 클래스(117), `JsonResponse(`(34), `{'success': True}`(17), `status.HTTP_201_CREATED`(14), 하드코딩 `status=NNN`(35), `pagination_class=`(2)
- `config/settings.py:348-363` `REST_FRAMEWORK` 블록 확인 — 페이지네이션 디폴트 부재
- 코드 인용은 모두 `file_path:line` 형식, 실제 파일에서 추출

## 부록 B — 본 감사가 다루지 않은 항목

- 응답 페이로드 크기/응답 시간 실측 (별도 performance_audit 참조)
- WebSocket consumers 응답 형식
- Celery 태스크 반환 값 형식
- Frontend 측 응답 파싱 로직 (TanStack Query 핸들러 등)
- OpenAPI 스펙(`contracts/`)과 실제 응답 간 정합성 검증

위 항목은 후속 감사 대상으로 권고함.
