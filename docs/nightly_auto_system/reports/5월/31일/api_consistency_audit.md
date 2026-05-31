# API 응답 일관성 감사 보고서

- 작성: 2026-05-31 (야간 자동 감사)
- 범위: 전체 `views*.py` 28개 파일 (migrations/__pycache__/node_modules 제외)
- 모드: **읽기 전용** (코드 수정 없음)
- 기준 정책: `docs/features/api_envelope/policy.md` (2026-05-12 수립) — "envelope 폐기 + DRF 평탄 통일"
- 이전 감사: `docs/nightly_auto_system/reports/5월/5일/api_consistency_audit.md`

---

## 요약

### 핵심 결론

2026-05-12에 **API 응답 표준 정책이 이미 명문화**되어 있다. 따라서 이번 감사의 가치는 "표준이 무엇인가"가 아니라 **"명문화된 표준 대비 현재 코드가 얼마나 준수/위반하는가"**에 있다.

| 영역 | 정책 표준 | 현재 준수도 | 판정 |
|------|-----------|-------------|------|
| **성공 응답 래핑** | 평탄 반환 (`{success, data, meta}` wrapping 폐기) | 부분 준수 — **3개 파일이 wrapping 잔존** | 🔴 위반 잔존 |
| **에러 응답 형식** | `{detail, code?, errors?, status_code}` 단일 표준 (DRF `raise` 경유) | 부분 준수 — **다수 view가 `Response({'error':...})` 직접 반환** | 🔴 광범위 위반 |
| **HTTP 상태 코드** | `status.HTTP_*` 상수 사용 | 대체로 준수 — 2개 파일 하드코딩 | 🟡 경미 |
| **201/204 사용** | 생성=201, 삭제=204 | 불일치 — 앱별 편차 큼 | 🟡 경미 |
| **페이지네이션** | DRF `PageNumberPagination` 표준 (`{count, next, previous, results}`) | 미준수 — **DRF 표준 0건, 전부 수동/슬라이싱/미적용** | 🔴 광범위 위반 |

### 최우선 이슈 (P1)

1. **에러 형식 이중 진실 소스**: `config/exception_handler.py`는 `{detail, code, status_code}` envelope를 강제하지만, 이는 **DRF 예외(`raise NotFound` 등)를 통과할 때만** 적용된다. 다수 view가 `Response({'error': '...'}, status=400)`을 **직접 반환**하여 exception handler를 우회 → 같은 API 군에서 에러 키가 `detail`(예외 경유)과 `error`(직접 반환)로 갈린다. 클라이언트는 두 형식을 모두 분기해야 한다.
2. **성공 응답 wrapping 잔존**: 정책상 폐기된 `{'success': True, 'data':..., 'meta':...}`가 `views_exchange.py`, `views_screener.py`, `views_fundamentals.py` 3개 파일에 그대로 남아있다. (정책 예외 범위 = marketpulse v2 cards / SSE 뿐 → 이 3개는 위반)
3. **페이지네이션 표준 미적용**: 정책은 DRF `PageNumberPagination`을 표준으로 명시했으나, 실제 코드에는 DRF 페이지네이터 사용처가 **단 1건도 없다**. Django `Paginator` 수동 구현, 리스트 슬라이싱(`[:N]`), 또는 무제한 `.all()` 직렬화가 혼재.

### 비어있는 파일 (구현 없음, 분석 제외)

`apps/chain_sight/views.py`, `apps/portfolio/views.py`, `validation/views.py`, `news/views.py`, `packages/shared/metrics/views.py`, `services/_dormant/graph_analysis/views.py` — 주석/빈 템플릿. (포트폴리오·체인사이트·검증은 모두 `api/views.py`로 이전 완료)

---

## 앱별 응답 패턴 매트릭스

| 파일 | 성공 래핑 | 에러 키 | 상태코드 방식 | 201/204 | 페이지네이션 | 정책 준수 |
|------|-----------|---------|---------------|---------|--------------|-----------|
| `packages/shared/stocks/views.py` | 평탄(직접 dict) | `{error}` + 구조화 `{error:{code,message,details}}` | `status.HTTP_*` | 없음 | `PageNumberPagination` 클래스 정의(L92) but 일부는 `[:N]` 슬라이싱 | 🟡 |
| `packages/shared/stocks/views_exchange.py` | **`{success,data,meta}` wrapping** | `{error}` | 성공 생략, 에러만 명시 | 없음 | 없음 | 🔴 wrapping |
| `packages/shared/stocks/views_screener.py` | **`{success,data,meta}` wrapping** | `{error}` | 성공 생략, 에러 명시 | 없음 | 없음 (`limit`만) | 🔴 wrapping |
| `packages/shared/stocks/views_market_movers.py` | 평탄(serializer 직접) | `{error}` | 성공 생략 | 없음 | 없음 (`limit`만) | 🟢 |
| `packages/shared/stocks/views_eod.py` | 평탄(직접 dict) | `{error}` | `status.HTTP_*` | 없음 | `[:50]` 슬라이싱 | 🟡 |
| `packages/shared/stocks/views_indicators.py` | 평탄(직접 dict) | `{error}` | `status.HTTP_*` | 없음 | 없음 | 🟢 |
| `packages/shared/stocks/views_search.py` | 평탄(직접 dict) | `{error}` | `status.HTTP_*` | 없음 | `[:10]` 슬라이싱 | 🟡 |
| `packages/shared/stocks/views_fundamentals.py` | **`{success,data,meta}` wrapping** | `{error}` | 성공 생략, 에러 명시 | 없음 | 없음 | 🔴 wrapping |
| `packages/shared/stocks/views_mvp.py` | 평탄(직접 dict) | 없음(`get_object_or_404`) | 모두 기본 200 | 없음 | `[:20]` 슬라이싱 | 🟡 |
| `packages/shared/users/views.py` | 평탄/혼합(serializer·dict·Paginator) | `{error}` + `{message}` + DRF `raise` 혼재 | `status.HTTP_*` (201/204/207 사용) | ✅ 201/204 사용 | Django `Paginator` 수동 구현 | 🟡 |
| `apps/chain_sight/api/views.py` | 평탄(직접 dict) | `{error}` | `status.HTTP_*` | 없음(전부 GET) | 수동 슬라이싱(`page`/`page_size`) | 🟡 |
| `apps/portfolio/api/views.py` | 평탄(serializer 직접) | `{error}` + 필드 추가(`scope`,`type`) | `status.HTTP_*` | **POST인데 201 미사용→200** | 없음 | 🟡 |
| `validation/api/views.py` | 평탄(직접 dict) | `{error}` + `{error,message}` 혼재 | `status.HTTP_*` (422 사용) | POST인데 201 미사용→200 | 없음 | 🟡 |
| `sec_pipeline/views.py` | 평탄(직접 dict) | 미정의 | **하드코딩 숫자**(`status=202/200`) | 202 사용 | 없음 | 🟡 |
| `serverless/views.py` | 평탄(직접 dict) | DRF 도메인 예외(`exceptions.py`) | `status.HTTP_*` (201 사용) | ✅ 201 사용 | 수동 offset/limit | 🟢 |
| `serverless/views_admin.py` | 평탄(직접 dict) | `{error}` + 구조화(`requires_confirm`,`cooldown_remaining`) | `status.HTTP_*` (201/204/429 사용) | ✅ 201/204 사용 | 없음(`.all()` 전체 조회) | 🟡 |
| `news/api/views.py` | 평탄(직접 dict) | `{error}` + DRF `ValidationError` | `status.HTTP_*` (204 사용) | 204 사용 | `PageNumberPagination` 클래스 정의 + 수동 offset/limit 혼용 | 🟡 |
| `rag_analysis/views.py` | 평탄(직접 dict) + 일부 dict 래퍼 | DRF 도메인 예외(`exceptions.py`) | `status.HTTP_*` (201/204 사용) | ✅ 201/204 사용 | 일부 무제한 `.all()` + Django `Paginator` 수동 | 🟢 |
| `macro/views.py` | 평탄(직접 dict) | `{error}` | `status.HTTP_*` | 없음 | 없음 | 🟡 |
| `integrations/iron_trading/views.py` | 평탄(`error_body()` helper) | **`{error:{code,message}}`** (독자 구조) | **하드코딩 숫자**(`status=400/404/503/200`) | 없음 | 없음 | 🔴 독자형식 |
| `thesis/views/conversation_views.py` | 평탄(직접 dict) | `{error}` | `status.HTTP_*` | 없음 | 없음 | 🟡 |
| `thesis/views/thesis_views.py` | 평탄(직접 dict/serializer) | `{error}` | `status.HTTP_*` | 없음 | 없음 | 🟡 |
| `thesis/views/monitoring_views.py` | 평탄(직접 dict) | `{error}` | 모두 기본 200(미명시) | 없음 | `[:50]` 슬라이싱 | 🟡 |
| `config/views.py` | `JsonResponse` (DRF 아님) | N/A | 일반 HTTP | 없음 | 없음 | — (health check) |

범례: 🟢 정책 대체로 부합 / 🟡 경미한 불일치 / 🔴 명백한 정책 위반

---

## HTTP 상태 코드 일관성

### `status` 모듈 사용 vs 하드코딩

- **`status.HTTP_*` 상수 사용 (다수, 권장 패턴)**: stocks 전반, users, chain_sight, portfolio, validation, serverless, news, rag_analysis, macro, thesis 전반
- **하드코딩 숫자 사용 (정리 필요)**:
  - `sec_pipeline/views.py:46` → `status=202`, `:49,:51` → `status=200`
  - `integrations/iron_trading/views.py:36,41,44,50` → `status=400/404/503/200`

### 성공 상태 코드 (200 vs 201)

정책상 자원 생성은 201이 표준이나 실제로는 **앱별 편차가 크다**:

| 패턴 | 해당 위치 |
|------|-----------|
| **201 올바르게 사용** | `users/views.py:108,303,669,774` · `serverless/views.py:929,1229,1534` · `serverless/views_admin.py:565` · `rag_analysis/views.py:61,135,290,395` |
| **204 (DELETE) 사용** | `users/views.py:348,719,806` · `serverless/views_admin.py:652` · `rag_analysis/views.py:98,157,423` · `news/api/views.py:652` |
| **🔴 POST/생성인데 200 반환 (201 누락)** | `apps/portfolio/api/views.py` (coach POST 6종 모두 200) · `validation/api/views.py:496` (POST, status 미명시→200) |
| **성공 시 상태 생략(기본 200)** | exchange/screener/fundamentals/market_movers/mvp/monitoring — 일관성은 있으나 명시성 부족 |

### 에러 상태 코드 사용 분포

- 400: 입력 검증 — 전 앱 광범위 사용 (일관적)
- 401: `users/views.py:176` · `validation/api/views.py:475,501` (소수만 명시, 대부분 `IsAuthenticated` permission이 자동 처리)
- 403: DRF `PermissionDenied` 경유 (`serverless/views.py:963`)
- 404: 광범위 사용 — `get_object_or_404` 또는 `status.HTTP_404_NOT_FOUND` 직접
- 422: `validation/api/views.py:74` (`not_in_universe` — 비즈니스 상태를 422로 정상화, 정책 §2.3 부합)
- 429: `stocks/views.py:1025` · `portfolio/api/views.py` · `serverless/views_admin.py:369` (rate limit / cooldown)
- 500: 다수 — try/except로 직접 반환하는 경향 (`macro`, `stocks` 일부). 정책상으론 도메인 `APIException` 서브클래스(`code` 보존)가 권장이나 직접 `Response({'error'}, status=500)`도 혼재
- 502/503: `portfolio/api/views.py` (502, LLM 게이트웨이) · `exchange`/`search` (503, 외부 API 다운)

---

## 에러 응답 형식

### 정책 표준 (`config/exception_handler.py`)

```json
{
  "detail": "사람이 읽는 메시지",   // 필수 (DRF 기본 키)
  "code": "snake_case_code",       // optional, 도메인 분기
  "errors": { "field": [...] },    // optional, ValidationError field-level
  "status_code": 404               // 필수, 정수
}
```

이 envelope는 **DRF가 처리하는 예외(`raise NotFound/ValidationError/PermissionDenied`, `APIException` 서브클래스)에만 적용**된다.

### 🔴 핵심 불일치: 직접 반환이 exception handler를 우회

다수 view가 `Response({'error': '...'}, status=4xx)`를 **직접 반환**한다. 이 경로는 exception handler를 거치지 않으므로 표준 envelope(`detail`/`code`/`status_code`)가 **적용되지 않는다**. 결과적으로 같은 백엔드가 두 가지 에러 형식을 내보낸다:

| 형식 | 발생 경로 | 대표 위치 |
|------|-----------|-----------|
| **`{detail, code, status_code}`** (표준) | DRF `raise ...` → exception_handler | `serverless/views.py`, `rag_analysis/views.py`, news `ValidationError` |
| **`{error: "..."}`** (비표준, 직접 반환) | `Response({'error':...}, status=4xx)` | stocks 전반, exchange, screener, fundamentals, search, indicators, eod, chain_sight, validation, macro, thesis 전반, serverless_admin |
| **`{error: {code, message, details}}`** (구조화, 독자) | 직접 반환 | `stocks/views.py:654-662` |
| **`{error: {code, message}}`** (독자 helper) | `error_body()` | `integrations/iron_trading/views.py:36,41,44` |
| **`{message: "..."}`** (또 다른 변형) | 직접 반환 | `users/views.py:219,229,256` |
| **`{symbol, error, message}`** (혼합) | 직접 반환 | `validation/api/views.py:71-74,91-94` |

→ **프론트엔드는 `error`, `detail`, `message` 세 키를 모두 방어적으로 파싱해야 하는 상태.** 정책 §1의 "단일 표준" 목표가 view 레벨에서 미달성.

### 에러 키 사용 빈도 (정성)

- `{'error': ...}`: 가장 흔함 (직접 반환 view 대부분) — **정책 비표준**
- `{'detail': ...}`: DRF 예외 경유 view (serverless, rag_analysis 일부) — **정책 표준**
- `{'message': ...}`: 소수 (users 긍정 응답, iron_trading error_body 내부) — 변형

---

## 페이지네이션 현황

### 전역 설정

`config/settings.py`의 `REST_FRAMEWORK`에 **`DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` 정의 없음**. (정책 §1 "전역 미적용, ViewSet 단위 적용" 방침과 일치하나, 실제 ViewSet 적용이 미흡)

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (JWT, Session),
    'DEFAULT_PERMISSION_CLASSES': [IsAuthenticated],
    'DEFAULT_THROTTLE_RATES': {...},
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
    # ❌ DEFAULT_PAGINATION_CLASS 없음
    # ❌ PAGE_SIZE 없음
}
```

### 페이지네이션 구현 방식 분포

| 방식 | 위치 | 평가 |
|------|------|------|
| **DRF `PageNumberPagination` 정의했으나 미사용/부분사용** | `stocks/views.py:92-108` (`StockListPagination` 정의 but 일부 LIST는 `[:N]` 슬라이싱) · `news/api/views.py:51-66` (정의 + 수동 offset 혼용) | 🟡 정의만, 일관 적용 안 됨 |
| **Django `Paginator` 수동 구현** (DRF 비표준 응답 `{results, pagination:{...}}`) | `users/views.py:635-655,884-904` · `rag_analysis/views.py:708-737` | 🔴 정책 `{count,next,previous,results}`와 키 불일치 |
| **수동 offset/limit 슬라이싱** | `serverless/views.py:1006-1028,1139` · `chain_sight/api/views.py:926-928` | 🟡 |
| **하드코딩 리스트 슬라이싱** (`[:N]`, 페이지네이션 자체 없음) | `stocks/views.py:175,928` · `eod:82([:50])` · `search([:10])` · `mvp([:20])` · `monitoring:238([:50])` | 🔴 무한 스크롤/페이지 이동 불가 |
| **무제한 `.all()` 직렬화** (제한 없음) | `rag_analysis/views.py:50-52`(DataBasket), `378-380`(AnalysisSession) · `serverless/views_admin.py:475`(NewsCollectionCategory) | 🔴 데이터 증가 시 성능 위험 |
| **`limit` 파라미터로만 크기 제한** | `exchange`, `screener`, `market_movers` | 🟡 페이지 이동 없음 |

### 🔴 DRF 표준 페이지네이션 응답(`{count, next, previous, results}`) 실제 사용처: **0건**

정책이 표준으로 지정한 형식을 따르는 엔드포인트가 하나도 없다. 수동 구현은 모두 `{results, pagination:{count, page, page_size, ...}}` 같은 **독자 키 구조**를 사용 → 클라이언트 페이지네이션 처리도 엔드포인트별로 갈린다.

### 무제한 반환 위험 목록 (페이지네이션 부재 + 증가 가능 데이터)

| 엔드포인트 | 위치 | 위험 |
|-----------|------|------|
| DataBasket 목록 | `rag_analysis/views.py:50-52` | 사용자별 바구니 누적 시 응답 비대 |
| AnalysisSession 목록 | `rag_analysis/views.py:378-380` | 분석 세션 누적 |
| NewsCollectionCategory 전체 | `serverless/views_admin.py:475` | 카테고리 증가 시 |
| News 기사 목록 (슬라이싱만) | `news/api/views.py:441` | 기사량 대비 offset 페이징 비효율 |

---

## 권고사항

> ⚠️ 본 보고서는 읽기 전용 감사다. 아래는 후속 작업 제안이며 본 세션에서 코드 수정은 수행하지 않았다.

### P1 — 에러 형식 단일화 (이중 진실 소스 제거)

1. **직접 `Response({'error':...}, status=4xx)` → DRF `raise` 전환.** 정책 §3 카탈로그대로 `raise NotFound/ValidationError/PermissionDenied` 또는 도메인 `APIException` 서브클래스로 교체. 그래야 `exception_handler`를 통과해 `{detail, code, status_code}` envelope가 강제된다.
   - 우선 대상: stocks 전반, validation, macro, thesis 전반, serverless_admin (= `{error}` 직접 반환 군)
2. **`integrations/iron_trading/views.py`의 `error_body()` 독자 형식 폐기** → 표준 envelope로 통일하거나, 외부 통합 전용이라면 정책 예외 범위에 명시적으로 등재.
3. **프론트엔드 영향 확인**: `error`/`detail`/`message` 키를 모두 파싱하는 방어 코드가 있는지 점검 후, 표준 전환과 동기화.

### P1 — 성공 응답 wrapping 잔존 제거

4. `views_exchange.py`, `views_screener.py`, `views_fundamentals.py`의 `{success, data, meta}` wrapping을 **평탄 반환으로 마이그레이션** (정책 §1 결정사항, 미완료분). `meta`의 timestamp/count는 응답 헤더(`X-Request-Id` 등) 또는 평탄 dict 최상위로 이동.

### P1 — 페이지네이션 표준화

5. **DRF `PageNumberPagination`을 ViewSet 단위로 실제 적용** (정책 §1). 최소한 무제한 `.all()` 반환 4곳(DataBasket, AnalysisSession, NewsCollectionCategory, News 목록)부터 우선 적용.
6. 수동 `{results, pagination:{...}}` 구조를 DRF 표준 `{count, next, previous, results}`로 통일 → `users`, `rag_analysis`, `serverless` 수동 페이저.
7. 하드코딩 `[:N]` 슬라이싱(eod/search/mvp/monitoring/stocks)은 의도된 "top-N 미리보기"인지, 페이지네이션 누락인지 케이스별 판정 필요.

### P2 — 상태 코드 정리

8. `sec_pipeline/views.py`, `integrations/iron_trading/views.py`의 **하드코딩 숫자 → `status.HTTP_*` 상수** 전환.
9. **POST/생성 엔드포인트 201 정상화**: `apps/portfolio/api/views.py` coach POST 6종, `validation/api/views.py:496`. (단, coach는 "자원 생성"이 아닌 "분석 실행" 성격이면 200 유지가 타당 — 의미 확인 후 결정)

### 추적 관리

10. 본 감사는 2026-05-12 정책의 **시행 격차(enforcement gap)**를 드러낸다. 정책은 존재하나 신규/기존 view가 일관 적용하지 않음. → `common-bugs.md` #15(캐시 키) 패턴처럼 **"신규 view 작성 시 에러는 반드시 `raise`, 성공은 평탄 반환, 목록은 DRF 페이저"** 체크리스트를 PR Completion Checklist에 추가 권장.

---

## 부록: 분석 메타데이터

- 분석 파일 수: 28개 (구현 있음 22개 + 빈 파일 6개)
- 빈 파일: `apps/chain_sight/views.py`, `apps/portfolio/views.py`, `validation/views.py`, `news/views.py`, `packages/shared/metrics/views.py`, `services/_dormant/graph_analysis/views.py`
- 추가 확인 파일: `config/exception_handler.py`, `config/settings.py` (REST_FRAMEWORK), `docs/features/api_envelope/policy.md`
- thesis 앱 위치: `thesis/views/{conversation,thesis,monitoring}_views.py` (단일 views.py 아닌 패키지 분할)
- 감사 방법: 병렬 read-only 에이전트 4종으로 파일군 분산 분석 후 교차 종합
