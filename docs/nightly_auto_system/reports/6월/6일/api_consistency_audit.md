# API 응답 일관성 감사 보고서

- 작성일: 2026-06-06 (야간 자동 감사)
- 범위: 전체 Django 앱의 `views*.py` 27개 파일 (migration/__pycache__/node_modules 제외)
- 성격: **읽기 전용 감사** — 코드 수정 없음
- 기준 정책: [`docs/features/api_envelope/policy.md`](../../../../features/api_envelope/policy.md) (2026-05-12 확정)
- 직전 감사: `docs/nightly_auto_system/reports/5월/5일/api_consistency_audit.md`

---

## 요약

### 핵심 발견

이 프로젝트는 **2026-05-12에 이미 응답 표준화 정책을 확정**했다(envelope 폐기 + DRF 평탄 통일 + 에러 `{detail, code?, errors?, status_code}` + `EXCEPTION_HANDLER` 등록). 따라서 본 감사는 "표준 부재"가 아니라 **"확정된 표준 대비 잔존 드리프트"** 를 측정한다.

| # | 발견 | 심각도 | 위치 |
|---|------|--------|------|
| F1 | `{success, data, meta}` 래핑이 정책 폐기 후에도 잔존 | 🔴 High | `views_exchange.py`, `views_fundamentals.py`, `views_screener.py` (stocks 3종) |
| F2 | 수동 `return Response({'error': ...})` 가 `EXCEPTION_HANDLER`를 우회 → 표준 에러 envelope(`{detail, code, status_code}`) 미적용 | 🔴 High | stocks 다수, market_pulse, validation, serverless/admin, chain_sight, iron_trading 등 광범위 |
| F3 | 에러 본문 키가 `{error}` / `{detail}` / `{message}` / `{valid,error}` 4종 혼용 | 🟠 Med | 앱 전반 (특히 users, validation, news) |
| F4 | 목록 API 다수가 페이지네이션 없이 전체 querysest 반환 (`.all()`/`.filter()`) | 🟠 Med | users, rag_analysis, serverless, validation, news ViewSet @action |
| F5 | POST 생성(create) 엔드포인트가 201 대신 200 반환 (혼재) | 🟡 Low | serverless `generate_thesis`, stocks 일부, validation `PeerPreference` |
| F6 | `status.HTTP_*` 상수 vs 하드코딩 숫자 혼용 | 🟡 Low | `iron_trading/views.py`(전부 숫자), `sec_pipeline/views.py`(전부 숫자), `cards.py`(404 숫자) |
| F7 | 에러/예외 상황을 HTTP 200으로 반환 | 🟡 Low | chain_sight Trace(L290), validation `insufficient_peers`(L417), config `health_check` |

### 전역 설정 사실 (config/settings.py:355, config/exception_handler.py)

- `EXCEPTION_HANDLER = config.exception_handler.custom_exception_handler` 등록됨 → **DRF `raise` 예외만** `{detail, code?, errors?, status_code}`로 정규화. **수동 `return Response({...}, status=...)`는 핸들러를 타지 않음** (F2의 근본 원인).
- `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE` **미설정** → 전역 페이지네이션 없음. 페이지네이션은 view마다 opt-in 필요 (F4의 근본 원인). 정책 문서도 "전역 미적용, ViewSet 단위"로 명시.
- `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` (기본 인증 필요).

---

## 앱별 응답 패턴 매트릭스

범례: 래핑 `WRAP`=`{success,data,meta}` / `FLAT`=평탄(serializer.data·도메인 dict) / `ENV`=정책 예외 envelope · 에러키 = 우세 패턴 · 뷰타입 · 페이지네이션 P=있음 N=없음 M=수동

| 파일 | 래핑 | 에러 본문 키 | 상태코드 방식 | 뷰 타입 | 페이지네이션 |
|------|------|--------------|---------------|---------|--------------|
| stocks/views.py | FLAT (ad-hoc) | `{error}` 문자열 + 구조화 `{error:{code,message}}` 혼재 | `status.HTTP_*` | APIView + generics.ListAPIView | P (ListAPIView만) / 나머지 N(슬라이싱) |
| stocks/views_eod.py | FLAT | `{error}` 문자열 | `status.HTTP_*` | APIView | N (슬라이싱) |
| stocks/views_exchange.py | **WRAP** 🔴 | `{error}` 문자열 | `status.HTTP_*` (503 다용) | APIView | N |
| stocks/views_fundamentals.py | **WRAP** 🔴 | `{error}` 문자열 | `status.HTTP_*` | APIView | N (limit 상한) |
| stocks/views_indicators.py | FLAT | `{error}` 문자열 | `status.HTTP_*` | APIView | N |
| stocks/views_market_movers.py | FLAT (serializer.data 직접) | `{error}` 문자열 | `status.HTTP_*` | APIView (AllowAny) | N |
| stocks/views_mvp.py | FLAT | 명시적 에러 없음(get_object_or_404 의존) | **status 전혀 미지정**(전부 200) | APIView | N (`.all()[:20]`, Sector 전체) |
| stocks/views_screener.py | **WRAP** 🔴 | `{error}` (1곳 `{error: serializer.errors}`) | `status.HTTP_*` | APIView | N (limit 상한) |
| stocks/views_search.py | FLAT | `{error}` + `{valid, error}` 혼재 | `status.HTTP_*` (503 사용) | APIView | N |
| chain_sight/api/views.py | FLAT | `{error}` 커스텀 dict | `status.HTTP_*` | APIView | M (SignalFeed 수동) / 나머지 limit |
| chain_sight/views.py | — | — | — | (뷰 없음) | — |
| market_pulse/views.py | FLAT | `{error}` 커스텀 dict | `status.HTTP_*` | APIView | N |
| market_pulse/api/views/cards.py | **ENV**(정책 예외) | `{error}` (404 하드코딩) | 하드코딩 숫자 | APIView | N |
| portfolio/api/views.py | FLAT (serializer.data) | `{error}` + DRF 검증(raise_exception) | `status.HTTP_*` (200 명시) | `@api_view` 함수형 | 해당없음 |
| portfolio/views.py | — | — | — | (뷰 없음, legacy 제거됨) | — |
| users/views.py | FLAT + 일부 커스텀 envelope | **혼재**: `{error}`/`{message}`/`{detail}`(raise)/`serializer.errors` 4종 | `status.HTTP_*` (201/204 정상) | APIView | M (Watchlist 2종) / 나머지 N(`.all()` 다수) |
| metrics/views.py | — | — | — | (뷰 없음) | — |
| config/views.py | FLAT(JsonResponse) | 명시적 에러 없음('disconnected' 문자열) | **상태 미지정**(항상 200) | 순수 Django 함수 | 해당없음 |
| iron_trading/views.py | FLAT | service `error_body(code,message)` dict | **하드코딩 숫자**(400/404/503/200) | APIView (AllowAny, 인증 off) | N (service 책임) |
| news/api/views.py | FLAT (커스텀 dict + bare list) | `{error}` + DRF `raise ValidationError` 혼재 | `status.HTTP_*` | **ViewSet** (ReadOnlyModelViewSet) + 28 @action | P(기본 list만) / @action 다수 N |
| news/views.py | — | — | — | (스텁) | — |
| rag_analysis/views.py | FLAT (bare serializer.data) | DRF `raise NotFound/PermissionDenied/ValidationError` 위주 | `status.HTTP_*` (201/204 정상) | APIView (+ StreamingHttpResponse) | M (UsageHistory만) / 나머지 N(`.all()`) |
| sec_pipeline/views.py | FLAT (service dict) | 명시적 에러 거의 없음 | **하드코딩 숫자**(202/200) | APIView (IsAdminUser) + Django render | 해당없음 |
| serverless/views.py | FLAT (정책상 "평탄 v2" 명시) | DRF `raise` 예외 위주(원시 `{error}` 거의 없음) | `status.HTTP_*` (201 일부) | `@api_view` 함수형 | M (execute_preset/advanced) / 나머지 N·슬라이싱 |
| serverless/views_admin.py | FLAT (service dict) | `{error: str(e)}` 커스텀 dict 전반 | `status.HTTP_*` (201/204/429/500) | APIView (IsAdminUser) | N |
| validation/api/views.py | FLAT (대형 도메인 dict) | `{error}` (+ 일부 `{error, message}`) | `status.HTTP_*` (404/422/400/401) | APIView | N |
| validation/views.py | — | — | — | (스텁) | — |
| _dormant/graph_analysis/views.py | — | — | — | (스텁, API 미구현) | — |

> 실제 뷰가 있는 파일: 19개 / 스텁·비어있음: 8개 (`chain_sight/views.py`, `portfolio/views.py`, `metrics/views.py`, `news/views.py`, `validation/views.py`, `graph_analysis/views.py`, 그리고 config·sec_pipeline의 일부는 Django HTML 뷰)

---

## HTTP 상태 코드 일관성

### 1) `status.HTTP_*` 모듈 vs 하드코딩 숫자

- **모듈 상수 사용 (표준 준수)**: stocks 전 파일, market_pulse, chain_sight, users, rag_analysis, news, serverless, serverless/admin, validation, portfolio — 대다수.
- **하드코딩 숫자 (비표준)** 🟡:
  - `integrations/iron_trading/views.py` — `status=400/404/503/200` 전부 정수 리터럴 (status 모듈 import 자체 없음).
  - `services/sec_pipeline/views.py` — `status=202/200` 정수 리터럴.
  - `apps/market_pulse/api/views/cards.py` — 에러 `status=404` 정수.

### 2) POST 생성 시 201 vs 200

- **201 정상 적용**: `users/views.py`(회원가입·Portfolio·Watchlist·WatchlistItem 생성), `rag_analysis/views.py`(DataBasket·Session 생성, DELETE 204), `serverless/views.py`(preset·alert 생성), `serverless/views_admin.py`(category 생성 201 / 삭제 204).
- **201을 써야 하나 200 반환 (혼재)** 🟡:
  - `serverless/views.py:generate_thesis` — thesis를 생성하지만 200 반환 (L1758).
  - `validation/api/views.py:PeerPreferenceView` — `update_or_create` POST인데 200 (L609), DELETE도 204 아님.
  - `stocks/views.py:StockSyncAPIView` — 동기화 POST는 의도적으로 200/500 (생성 아님 → 허용 가능).
  - `portfolio/api/views.py` coach_e1~e6 — POST지만 LLM **실행**이므로 200 명시 (생성 아님 → 적절).
- **POST인데 상태 코드 자체 미지정** → 기본 200: news `generate_daily_keywords`·`ml_rollback`, serverless 트리거형(`trigger_sync`/`sync_now`/`trigger_keyword_generation`/`trigger_breadth_sync`), admin `AdminActionView` (트리거 성격 → 200 허용 가능하나 명시 일관성 부족).

### 3) 에러 상태 코드 패턴

- 400(BadRequest), 404(NotFound), 401(Unauthorized) 대체로 표준 사용.
- 도메인별 확장 코드: **503**(stocks/exchange·search 외부데이터 없음, chain_sight, iron_trading), **422**(validation `not_in_universe`), **429**(portfolio budget, admin throttle), **502**(portfolio LLM 게이트웨이). → 의미상 적절하나 앱마다 다른 코드 매핑(예: "데이터 없음"이 곳에 따라 404 vs 503 vs 422).
- **에러를 200으로 반환** 🟡: chain_sight `Trace` 예외 시 `{found:False, error}` 200 (L290), validation `insufficient_peers` status 누락 → 200 (L417), config `health_check` DB 끊겨도 200(`'disconnected'` 문자열), stocks `views_mvp` 전반 200.

---

## 에러 응답 형식

### 표준 (정책 §2.2)

```json
{ "detail": "...", "code": "snake_case", "errors": {...}?, "status_code": 404 }
```
→ `config/exception_handler.py`가 **DRF `raise` 예외만** 이 형태로 변환.

### 현황: 두 갈래로 분기

| 경로 | 결과 본문 | 표준 부합 | 사용 파일 |
|------|-----------|-----------|-----------|
| `raise NotFound/ValidationError/PermissionDenied(...)` | `{detail, code, errors?, status_code}` ✅ | 부합 | rag_analysis(주력), serverless(주력), news(@action 검증), users(일부) |
| `return Response({"error": ...}, status=...)` | `{error: "..."}` ❌ | **우회** | stocks 전반, market_pulse, validation, serverless/admin, chain_sight, iron_trading, news(@action) |
| `return Response(serializer.errors, ...)` | 필드별 `{field: [msg]}` ❌ | 비표준 | users(L68,110,307,671), screener(`{error: serializer.errors}`) |
| `{"message": ...}` | 단일 message 키 ❌ | 비표준 | users(AddFavorite L227, L219/249) |
| `{"valid": False, "error": ...}` | valid 플래그 동반 ❌ | 비표준 | stocks/views_search(SymbolValidate L117) |
| service `error_body(code,message)` | `{code, message, ...}` ❌ | 비표준 | iron_trading |

**핵심 모순**: 정책상 에러 표준은 `{detail, code, status_code}`인데, 실제 코드의 다수는 `EXCEPTION_HANDLER`를 타지 않는 **수동 `{error}` dict**다. 즉 같은 백엔드 안에서 클라이언트가 받는 에러 본문이 **`detail` 키일 수도, `error` 키일 수도, `message` 키일 수도** 있다. FE는 두 키를 모두 방어해야 한다.

### DRF 기본 vs 커스텀 혼용 — 동일 파일 내 충돌 예시

- `users/views.py`: `raise NotFound`(→`detail`) 와 `Response({"error": "Wrong username..."})`(→`error`) 가 **한 파일에 공존** (L121 vs L175).
- `news/api/views.py`: `raise ValidationError`(→`detail/errors`) 와 `Response({"error":...})`(→`error`) 공존.

---

## 페이지네이션 현황

### 전역 설정

`REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS` **없음**. → 모든 목록은 view별 opt-in. 정책 문서도 "전역 미적용, ViewSet 단위 적용"으로 명시.

### 적용 방식 3가지

| 방식 | 사용처 |
|------|--------|
| **DRF PageNumberPagination** (`{count, next, previous, results}`) | stocks `StockListPagination`(ListAPIView, page 50/max 200), news `NewsArticlePagination`(ViewSet 기본 list, 20/max 100) |
| **수동 Paginator/슬라이싱** (커스텀 `{results, pagination}` 또는 `page/page_size`) | users `WatchlistListCreateView`·`WatchlistStocksView`(Django Paginator, max 100), rag_analysis `UsageHistoryView`(Paginator), chain_sight `SignalFeedView`(수동 slice+has_next), serverless `execute_preset`·`advanced_screener_api`(FilterEngine 위임, next/previous URL 생성) |
| **상한 슬라이싱만** (`[:limit]`, `[:N]`) | stocks 대부분, eod, indicators, search, news @action 다수, serverless trending |

### ⚠️ 페이지네이션 없이 전체 queryset 반환 (잠재 위험)

| 위치 | 코드 근거 | 비고 |
|------|-----------|------|
| `users/views.py:Users.get` | `User.objects.all()` (L93) | 전체 사용자 |
| `users/views.py:PortfolioListCreateView.get` | `.filter().select_related()` (L271) | 상한 없음 |
| `users/views.py:UserFavorites.get` | (L197) | 상한 없음 |
| `users/views.py:UserInterestListCreateView.get` | (L1046) | 상한 없음 |
| `users/views.py:PortfolioDetailTableView.get` | 전체+summary (L416) | 상한 없음 |
| `rag_analysis/views.py` 목록 GET 다수 | `DataBasket.objects.filter()`(L52), `AnalysisSession.objects.filter()`(L429), `session.messages.all()`(L496) | 사용자 데이터 누적 시 증가 |
| `news/api/views.py:collection_logs` | `list(qs.values(...))` (L1452) | 로그 전체 |
| `news/api/views.py:daily_summary`/`ml_trend` | 전체 집계·history 순회 (L1504, L1940) | |
| `serverless/views.py:screener_presets_api` GET | `queryset.distinct()` (L954) | preset 전체 |
| `serverless/views.py:screener_alerts_api` GET | 사용자 alert 전체 (L1255) | |
| `serverless/views.py:etf_collection_status` | 전 ETFProfile 순회 (L1958) | |
| `serverless/views_admin.py:AdminNewsCategoryView` GET | category 전체 (L505) | |
| `validation/api/views.py:PresetListView` | active preset 전 순회 (L536) | symbol 단위라 소규모 |
| `market_pulse/views.py:SectorPerformanceView` | service 결과 전체 (L264) | 섹터 11개 → 소규모 |
| `stocks/views_mvp.py:SectorListView` | `.values_list().distinct()` 전체 (L221) | 섹터 목록 → 소규모 |

> 대부분은 사용자 스코프(`filter(user=...)`)거나 도메인상 소규모라 즉각 위험은 낮으나, `Users.get`(전체 사용자)·rag_analysis 메시지/세션·news 로그 계열은 데이터 누적 시 **무제한 응답** 위험.

---

## 권고사항

> 본 보고서는 읽기 전용 감사이며, 아래는 후속 작업 제안이다(코드 미수정).

### P0 — 정책 드리프트 정리 (이미 확정된 표준 위반)

1. **F1: 잔존 WRAP 3종 평탄화** — `views_exchange.py`/`views_fundamentals.py`/`views_screener.py`의 `{success, data, meta}`를 정책(2026-05-12)대로 평탄 반환으로 전환. `meta.timestamp/count`는 응답 헤더(`X-Request-Id` 등) 또는 본문 평탄 키로 이전. **FE `screenerService.ts` 동시 수정 필요** (정책 적용 범위에 명시됨).
2. **F2: 수동 `{error}` → DRF 예외 전환** — `return Response({"error": ...}, status=4xx)`를 `raise NotFound/ValidationError/APIException(default_code=...)`로 교체해 `EXCEPTION_HANDLER`를 타게 한다. 도메인 코드 보존이 필요하면 `rag_analysis/exceptions.py`·`serverless/exceptions.py` 패턴처럼 `APIException` 서브클래스 사용. 우선순위: stocks(영향 큼) → market_pulse → validation → serverless/admin → chain_sight.

### P1 — 형식 통일

3. **F3: 에러 키 단일화** — `{message}`/`{valid,error}`/`serializer.errors` 직접 반환 제거. 검증 실패는 `is_valid(raise_exception=True)`로 통일(users 4곳, screener 1곳).
4. **F6: 하드코딩 상태 코드 → `status.HTTP_*`** — `iron_trading/views.py`, `sec_pipeline/views.py`, `cards.py`. (cards.py는 envelope 정책 예외지만 상태 코드 상수화는 적용.)

### P2 — 안정성

5. **F4: 무제한 목록에 페이지네이션 부여** — 최소 `Users.get`, rag_analysis 세션/메시지 목록, news `collection_logs`/`daily_summary`, serverless `screener_presets`/`alerts`/`etf_collection_status`에 `PageNumberPagination` 또는 명시적 limit 상한 도입. 정책의 표준 envelope `{count, next, previous, results}` 사용.
6. **F5/F7: 시맨틱 상태 코드** — 생성 POST는 201(`generate_thesis`, `PeerPreference`), 예외 상황은 4xx/5xx로(chain_sight Trace, validation `insufficient_peers`, config `health_check`는 DB 끊김 시 503). 비즈니스 정상 분기는 정책 §2.3의 `{status, data:null}` 패턴 유지.

### 거버넌스

7. **정책 준수 게이트** — `api_envelope/policy.md`가 존재하나 신규/기존 view가 표준을 벗어남. CI에 간단한 grep 가드(예: `views*.py`에서 `Response({"error"` 신규 추가 차단, `'success': True` 신규 추가 차단) 추가 검토.
8. **재감사 추적** — 직전 5월 5일 감사 → 5월 12일 정책 확정 → 현재(6월 6일) 잔존 위반 3파일+수동 `{error}` 다수. 정책 적용률을 다음 야간 감사에서 수치로 추적 권장.

---

## 부록 — 감사 방법

- 대상 27개 `views*.py`를 3개 그룹으로 분할, 병렬 read-only 분석.
- 전역 설정 직접 확인: `config/settings.py:355` (REST_FRAMEWORK), `config/exception_handler.py` (커스텀 핸들러), `docs/features/api_envelope/policy.md` (확정 정책).
- `grep` 교차검증: `'success': True` 잔존 = exchange/fundamentals/screener 3파일로 확정.
- 코드 미수정 — 사실 추출 및 정책 대비 분석만 수행.
