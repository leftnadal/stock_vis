# API 응답 일관성 감사 보고서

- **작성일**: 2026-06-08
- **유형**: 읽기 전용 정적 감사 (코드 수정 없음)
- **대상**: Django REST Framework view 27개 파일 (apps/, packages/shared/, services/, integrations/, config/)
- **선행 감사**: `docs/nightly_auto_system/reports/5월/5일/api_consistency_audit.md`
- **관련 정책**: `docs/features/api_envelope/policy.md` (2026-05-12 확정)

---

## 요약

### 핵심 결론

**이 프로젝트는 이미 응답 표준화 정책을 보유하고 있으나(2026-05-12 확정), 적용이 불완전하여 정책 위반 코드가 다수 잔존한다.** 이번 감사는 "표준이 없다"가 아니라 **"표준이 있는데 지켜지지 않는다"**가 본질이다.

확정된 표준(`docs/features/api_envelope/policy.md`):
- **성공 응답**: `serializer.data` 또는 dict **평탄 반환** (DRF 표준). `{success, data, meta}` wrapping은 **폐기 결정됨**.
- **에러 응답**: `{detail, code?, errors?, status_code}` 단일 표준. `config/exception_handler.py`의 `custom_exception_handler`가 DRF `raise` 예외를 자동 변환.
- **페이지네이션**: DRF `PageNumberPagination`(`{count, next, previous, results}`)을 ViewSet 단위로 적용. 전역 기본값은 의도적으로 미설정.

### 현황 점수

| 영역 | 정책 | 실제 준수율 | 평가 |
|------|------|-----------|------|
| 성공 응답 평탄화 | 평탄 반환 (wrapping 폐기) | 부분 위반 | ⚠️ `{success:True}` wrapping 3개 파일 잔존 |
| 에러 envelope | `{detail,code,...}` (handler 경유) | **광범위 우회** | 🔴 대부분 view가 수동 `{"error":...}` 직접 반환 → handler 미경유 |
| HTTP 상태 코드 | `status.HTTP_*` 상수 | 대체로 양호 | ⚠️ 일부 숫자 하드코딩 + 암시적 200 다수 |
| 페이지네이션 | ViewSet 단위 PageNumberPagination | 산발적 | 🔴 무제한 `.all()`/슬라이싱 다수, 구현 방식 4종 혼재 |

### 가장 시급한 3가지

1. **에러 envelope 우회 (🔴 최우선)** — 표준 handler가 등록돼 있으나 대부분의 view는 `Response({"error": ...})`를 직접 반환해 handler를 타지 않는다. 결과적으로 클라이언트가 받는 에러 형식이 `{"error": str}`(다수) / `{"detail": ...}`(DRF raise) / `{"error": {...}}`(중첩) / `{"error":..., "scope":...}`(확장) 으로 4종 이상 공존한다.
2. **`{success:True, data, meta}` wrapping 잔존 (⚠️)** — `views_exchange.py`, `views_fundamentals.py`, `views_screener.py` 3개 파일이 폐기 결정된 wrapping을 여전히 사용. 같은 stocks 앱 내에서도 `views.py`/`views_indicators.py`는 평탄 반환이라 **앱 내부에서조차 불일치**.
3. **무제한 목록 반환 (🔴)** — 페이지네이션 없이 `.all()` 전체 또는 고정 슬라이싱(`[:50]`, `[:20]`)으로 반환하는 엔드포인트 다수. 데이터 증가 시 응답 비대화 + 잠재적 DoS 표면.

---

## 앱별 응답 패턴 매트릭스

> 빈 파일(legacy 보존용): `apps/chain_sight/views.py`, `apps/portfolio/views.py`, `services/validation/views.py`, `services/_dormant/graph_analysis/views.py`, `packages/shared/metrics/views.py` — 분석 대상에서 제외.

| 파일 | View 타입 | 성공 응답 래핑 | 에러 형식 | 상태코드 방식 | 페이지네이션 |
|------|----------|--------------|----------|-------------|------------|
| `stocks/views.py` | APIView + ListAPIView | 직접 반환 (일부 `{"data":...}` 중첩) | `{"error":str}` + `{"error":{...}}` 중첩 | `status.HTTP_*` | ✅ `StockListPagination`(PageNumber) — **단, 재무제표는 `[:limit]` 슬라이싱** |
| `stocks/views_eod.py` | APIView | 직접 반환 | `{"error":str}` | `status.HTTP_*` + 암시적 200 | ❌ 고정 `[:50]`,`[:7]` |
| `stocks/views_exchange.py` | APIView | 🔴 `{"success":True,"data":...,"meta":...}` | `{"error":str}` | `status.HTTP_*` + 암시적 200 | ❌ (배치 100개 cap) |
| `stocks/views_fundamentals.py` | APIView | 🔴 `{"success":True,"data":...,"meta":...}` | `{"error":str}` | `status.HTTP_*` | ❌ (`limit` 파라미터 cap) |
| `stocks/views_indicators.py` | APIView | 직접 반환 | `{"error":str}` | `status.HTTP_*` + 암시적 200 | ❌ `[:50]` 슬라이싱 |
| `stocks/views_market_movers.py` | APIView | 직접 `serializer.data` | `{"error":str}` | `status.HTTP_*` + 암시적 200 | ❌ (`limit` 1~20 cap) |
| `stocks/views_mvp.py` | APIView | 직접 dict | `get_object_or_404` (기본 404) | 암시적 200 | ❌ 하드코딩 `[:20]` |
| `stocks/views_screener.py` | APIView | 🔴 `{"success":True,"data":...,"meta":...}` | `{"error":{...}}` + `{"error":str}` 혼재 | `status.HTTP_*` + 암시적 200 | ❌ (`limit` 1~1000 cap) |
| `stocks/views_search.py` | APIView | 직접 dict (`count`/`results`) | `{"error":str}` | `status.HTTP_*` | ❌ `[:10]`,`[:20]` |
| `users/views.py` | APIView | 혼합: 직접 + `{"ok":..}`/`{"message":..}` | `{"error":..}` + `{"message":..}` + DRF raise + serializer.errors | `status.HTTP_*` (201/204/207 포함) | ⚠️ `django.core.paginator` 수동 (`{results,pagination}`) |
| `config/views.py` | 함수형 (@api_view) | `JsonResponse` 순수 dict | (에러 케이스 없음) | 암시적 200 | ❌ (단일 엔드포인트) |
| `iron_trading/views.py` | APIView | 직접 dict (`error_body()`) | 커스텀 `error_body(code,msg,...)` | 🔴 숫자 하드코딩(200/400/404/503) | ❌ |
| `market_pulse/views.py` | APIView | 혼합: 직접 + `{"error":..}` | `{"error":str}` (고정 메시지) | `status.HTTP_*` 혼용 + 암시적 200 | ❌ |
| `chain_sight/api/views.py` | APIView | 직접 반환 | `{"error":str}` + `{"error":str(e)}` | `status.HTTP_*` | ⚠️ 수동 page/page_size (일부만) |
| `portfolio/api/views.py` | 함수형 (@api_view) | 직접 `serializer.data` | `{"error":.., **extra}` (scope/type 확장) | `status.HTTP_*` | ❌ (전부 POST 단일 결과) |
| `news/api/views.py` | ViewSet (ReadOnly) | 혼합: 직접 + `{symbol,count,articles}` | `{"error":..}` + DRF ValidationError | `status.HTTP_*` (201 포함) | ⚠️ `NewsArticlePagination` 설정 + 수동 슬라이싱 혼재 |
| `news/views.py` | APIView | 혼합: 직접 + 래핑 | DRF 예외 + dict 폴백 | `status.HTTP_*` (201 포함) | ⚠️ `django.core.paginator` 수동 |
| `rag_analysis/views.py` | APIView | 혼합: 직접 + dict 래핑 + SSE 스트림 | DRF 예외 + `{"error":..}`/`{"message":..}` | `status.HTTP_*` (201 포함) | ❌ `.all()`/`.filter()` 전체 |
| `sec_pipeline/views.py` | APIView | 혼합: 직접 + dict 래핑 | `{"status":.., "message":..}` | 🔴 숫자 하드코딩(200/202) | ❌ |
| `serverless/views.py` | 함수형 (@api_view) | 혼합: 직접 + dict 래핑 | DRF ValidationError + `{"error":..}` | `status.HTTP_*` (201 포함) | ⚠️ 수동 limit/offset |
| `serverless/views_admin.py` | APIView | dict 래핑 | `{"error":str}` | `status.HTTP_*` (201 포함) | ❌ `.all()` 전체 |
| `validation/api/views.py` | APIView | dict 래핑 | `{"error":.., "message":..}`/`{"error":.., "status":..}` | `status.HTTP_*` (422 포함) | ❌ |

### 패턴 분포 요약

- **성공 응답 래핑**: 직접/평탄 반환(다수, 정책 부합) vs `{success:True}` wrapping(3개 파일, 정책 위반) vs 부분 dict 래핑(`{count, results}` 등 다수).
- **View 타입**: APIView 압도적 다수, `@api_view` 함수형 3개 영역(config, portfolio/api, serverless), ViewSet 1개(news/api)뿐 → **DRF 라우터/페이지네이션 자동화 혜택을 거의 못 받음**.

---

## HTTP 상태 코드 일관성

### 양호한 점
- 다수 파일이 `status.HTTP_*` 상수를 사용 (정책 부합).
- 생성 엔드포인트는 대체로 **201**을 일관 사용: `users/views.py`, `news/api`, `news/views.py`, `rag_analysis`, `serverless/views.py`, `serverless/views_admin.py`.
- `users/views.py`는 204(No Content), 207(Multi-Status)까지 의미에 맞게 세분 사용 — 모범 사례.
- `validation/api/views.py`는 비즈니스 상태를 200 대신 404/422로 정상화(정책 §2.3 반영).

### 불일치 / 위험

| 문제 | 위치 | 상세 |
|------|------|------|
| 🔴 숫자 하드코딩 | `iron_trading/views.py`(200/400/404/503), `sec_pipeline/views.py`(200/202) | `status.HTTP_*` 상수 미사용 — 정책 위반 |
| ⚠️ 암시적 200 남발 | `views_eod`, `views_exchange`, `views_indicators`, `views_market_movers`, `views_screener`, `market_pulse`, `config` 등 | 성공 시 `status=` 미지정. 동작은 200이나 명시성 부족, 코드 가독성·grep 추적성 저하 |
| ⚠️ 에러 코드 다양성 편차 | `portfolio/api`(400/429/502/500) vs `market_pulse`(주로 500 폴백) | 동일 성격 실패를 어디선 429/502로 세분, 어디선 전부 500으로 뭉뚱그림 |
| ⚠️ 503 사용 산발 | `views_exchange`, `views_market_movers`, `views_search`, `chain_sight/api`, `iron_trading` | 외부 API 실패를 503으로 매핑하는 곳과 500으로 매핑하는 곳 혼재 |

---

## 에러 응답 형식

### 핵심 모순: "표준 핸들러는 있으나 대부분 우회"

`config/settings.py:373`에 `EXCEPTION_HANDLER`가 등록돼 있고, `config/exception_handler.py`가 모든 DRF 예외를 다음 표준으로 변환한다:

```json
{ "detail": "...", "code": "...", "errors": {...}, "status_code": 404 }
```

**그러나 이 핸들러는 `raise`된 DRF 예외만 변환한다.** view 코드에서 `return Response({"error": ...})`로 **직접 반환하는 에러는 핸들러를 거치지 않는다.** 현재 코드베이스는 후자(수동 직접 반환)가 압도적으로 많아, 표준 envelope의 혜택을 받는 경로가 소수에 그친다.

### 실제로 클라이언트가 받는 에러 형식 (공존 중)

| 형식 | 사용처(예) | 정책 부합 |
|------|-----------|----------|
| `{"detail":.., "code":.., "status_code":..}` | DRF `raise NotFound/ValidationError` 경로 (users, news, rag_analysis, serverless 일부) | ✅ 표준 |
| `{"error": "문자열"}` | stocks 전 파일, chain_sight/api, market_pulse, serverless_admin 등 **최다** | 🔴 위반 |
| `{"error": {중첩 dict}}` | `stocks/views.py`(654-662), `views_screener.py`(69-71) | 🔴 위반 |
| `{"error":.., "scope":..}` / `{"error":.., "type":..}` | `portfolio/api/views.py`(91,97) | 🔴 위반(확장 필드 비표준) |
| `{"error":.., "message":..}` / `{"error":.., "status":..}` | `validation/api/views.py`(71,84) | 🔴 위반 |
| `{"message": ".."}` | `users/views.py`(219,227,249,256) | 🔴 위반 |
| `{"status":.., "message":..}` | `sec_pipeline/views.py`(43-50) | 🔴 위반 |
| 커스텀 `error_body(code,msg,retry_after)` | `iron_trading/views.py` | 🔴 위반(자체 스키마) |
| `get_object_or_404` 기본 404 HTML/DRF | `views_mvp.py`(82,171) | ⚠️ 비표준 경로 |

→ **에러 키만 `error` / `detail` / `message` / `status` 4종, 값 형태는 문자열 / 중첩 dict 혼재.** 클라이언트가 에러 메시지를 안정적으로 추출하려면 분기 코드가 필요한 상태.

### 권장 정합 방향
표준 핸들러가 이미 존재하므로, **수동 `Response({"error":...})`를 도메인 `APIException` 서브클래스 `raise`로 전환**하면 핸들러가 자동으로 표준 envelope를 생성한다. 정책 문서 §3에 도메인 에러 코드 카탈로그와 `rag_analysis/exceptions.py`, `serverless/exceptions.py` 선례가 이미 마련돼 있다.

---

## 페이지네이션 현황

### 전역 설정
`config/settings.py`의 `REST_FRAMEWORK`에 **`DEFAULT_PAGINATION_CLASS` 미설정**(의도적). 정책상 "ViewSet 단위 적용"이 원칙이나, View 대부분이 APIView/함수형이라 자동 페이지네이션이 걸리지 않는다.

### 구현 방식 4종 혼재 (일관성 부재)

| 방식 | 사용처 | 평가 |
|------|--------|------|
| DRF `PageNumberPagination` | `stocks/views.py`(StockListPagination), `news/api`(NewsArticlePagination) | ✅ 표준 |
| `django.core.paginator.Paginator` 수동 | `users/views.py`, `news/views.py` | ⚠️ 응답 형태가 `{results, pagination:{...}}`로 DRF `{count,next,previous,results}`와 다름 |
| 수동 page/page_size 슬라이싱 | `chain_sight/api`(SignalFeedView), `serverless/views.py` | ⚠️ next/previous URL 없음 |
| 페이지네이션 없음 (전체/고정 cap) | 아래 목록 | 🔴 위험 |

### 🔴 무제한 또는 고정 슬라이싱으로 목록 반환 (페이지네이션 부재)

- `stocks/views.py` — 재무제표 `.order_by()[:limit]` 슬라이싱 (목록 API인 StockList만 페이지네이션, 나머지 미적용)
- `stocks/views_eod.py` — `.order_by("-composite_score")[:50]`, `[:7]` 고정
- `stocks/views_indicators.py` — `[:50]` 고정
- `stocks/views_mvp.py` — 하드코딩 `[:20]`
- `stocks/views_search.py` — `[:10]`, `[:20]`
- `rag_analysis/views.py` — `.all()`/`.filter()` 전체 반환 (페이지네이션 전무)
- `serverless/views_admin.py` — `.all()` 전체 반환
- `validation/api/views.py`, `sec_pipeline/views.py`, `market_pulse/views.py` — 목록성 응답에 페이지네이션 없음

> 다수가 `limit` 쿼리 파라미터 cap(예: 1~1000, 1~40)으로 상한을 두고는 있으나, 이는 페이지네이션이 아니라 단순 절단이라 **offset/cursor 기반 후속 페이지 접근 불가** + **cap 상한이 커서 여전히 대용량 응답 가능**(예: screener 1000).

---

## 권고사항

> 본 보고서는 읽기 전용 감사이며, 아래는 후속 작업 제안이다(코드 미변경).

### P0 — 즉시 (정책 위반 정합)

1. **에러 응답 표준 핸들러로 통일**
   수동 `return Response({"error": ...}, status=4xx/5xx)`를 도메인 `APIException` 서브클래스 `raise`로 전환 → `custom_exception_handler`가 `{detail, code, errors, status_code}`를 자동 생성. 우선 대상: `stocks/*`(최다 위반), `chain_sight/api`, `market_pulse`, `serverless_admin`, `validation/api`, `sec_pipeline`, `iron_trading`, `portfolio/api`.
   - 선례 재사용: `rag_analysis/exceptions.py`, `serverless/exceptions.py` 패턴 + 정책 §3 코드 카탈로그.

2. **`{success:True, data, meta}` wrapping 제거**
   `views_exchange.py`, `views_fundamentals.py`, `views_screener.py` 3개 파일을 평탄 반환으로 전환(정책 §1에서 폐기 결정). 메타데이터는 응답 헤더(`X-Request-Id`, `X-Cache`)로 분리.
   - ⚠️ FE 동반 변경 필요: `screenerService.ts` 등 클라이언트가 `data.data` 언래핑을 기대할 수 있음 → contracts/ 스펙과 함께 검토.

### P1 — 단기 (안정성)

3. **무제한 목록에 페이지네이션 도입**
   `rag_analysis`, `serverless_admin`의 `.all()` 전체 반환부터 DRF `PageNumberPagination` 적용. 고정 슬라이싱(`[:50]` 등) 엔드포인트는 page 파라미터 지원으로 전환.

4. **상태 코드 상수화**
   `iron_trading/views.py`, `sec_pipeline/views.py`의 숫자 하드코딩을 `status.HTTP_*`로 교체. 성공 응답의 암시적 200도 `status=status.HTTP_200_OK` 명시 권장(추적성).

### P2 — 중기 (구조 정합)

5. **페이지네이션 구현 방식 단일화**
   `django.core.paginator` 수동 구현(users, news/views)을 DRF 표준 `{count,next,previous,results}`로 수렴. 응답 형태 이중 표준 제거.

6. **APIView → ViewSet 점진 전환 검토**
   목록/상세 CRUD 성격 엔드포인트는 ViewSet으로 전환 시 페이지네이션·필터·스키마 자동화 혜택. (대규모 작업이므로 신규 엔드포인트부터 적용)

### 회귀 방지

7. **CI 가드 추가 검토**
   `return Response({"error":` 패턴 / `{"success": True` 패턴을 grep하는 lint 룰을 추가해 정책 위반 신규 유입 차단. 정책 문서(`policy.md`)를 신규 view 작성 시 필독 문서로 연결.

---

## 부록: 선행 감사 대비 변화

- 본 감사는 `5월/5일/api_consistency_audit.md`(→ P1 #14 envelope 단일화 정책 도출)의 **후속 추적**이다.
- 5월 정책 수립 이후 **부분 적용**됨: DRF `raise` 경로의 에러 표준화 + validation 상태코드 정상화 + 일부 wrapping 제거는 진행됨.
- 그러나 **수동 `{"error":...}` 직접 반환 우회**와 **wrapping 3개 파일 잔존**, **페이지네이션 산발 적용**은 미완 → 정책과 구현 간 격차가 여전히 존재한다. 정책 자체는 명확하므로, 남은 작업은 "결정"이 아니라 "적용 완수"다.
