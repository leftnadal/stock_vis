# API 응답 일관성 감사 보고서

> 생성일: 2026-06-01 · 범위: 전체 `views*.py` 27개 파일 (읽기 전용 감사, 코드 미수정)
> 방법: 각 파일의 DRF `Response()` 반환부 정밀 분석 + 전역 `REST_FRAMEWORK` 설정 교차 검증

---

## 요약

전체 27개 view 파일 중 **실제 view가 구현된 파일은 18개**, 나머지 9개는 빈 스텁(`# Create your views here.`)이다.

핵심 결론은 **"부분적으로 일관, 전역적으로 분열"**이다. 상태 코드 상수화(`status.HTTP_*`)는 대부분 잘 지켜지지만, **응답 래핑 형식**과 **에러 응답 형식**은 앱마다, 심지어 같은 파일 안에서도 갈린다.

### 가장 시급한 5대 발견

| # | 심각도 | 발견 | 위치 |
|---|--------|------|------|
| 1 | 🔴 높음 | **에러인데 HTTP 200 반환** — 클라이언트가 실패를 감지 못함 | `validation/api/views.py` L417·L433·L671, `chain_sight/api/views.py` L288 |
| 2 | 🟠 중간 | **성공 응답 래핑 2분열** — `{success,data,meta}` 래핑(stocks 3파일) vs 비래핑(나머지 전부). 프론트가 엔드포인트마다 다른 형태 처리 필요 | 전역 |
| 3 | 🟠 중간 | **에러 형식 3분열** — `raise` 경로(`{detail,code}` 표준화) vs 직접 `{error}` vs `{message}`. 같은 404가 파일/경로별로 다른 형태 | `users/views.py`, `validation/api/views.py` 등 |
| 4 | 🟡 낮음 | **상태 코드 하드코딩** — `status.HTTP_*` 상수 미사용 | `iron_trading/views.py` L36·41·46·50, `sec_pipeline/views.py` L49·53·55 |
| 5 | 🟡 낮음 | **잠재 버그** — 동일 view가 `result`(단수)와 `results`(복수) 키 혼용 | `stocks/views.py` L204 vs L214/233 |

### 전역 설정 (모든 판단의 기준선)

`config/settings.py` L355-374 의 `REST_FRAMEWORK`:

| 키 | 값 | 함의 |
|----|----|------|
| `EXCEPTION_HANDLER` | `config.exception_handler.custom_exception_handler` | 예외를 `{status_code, detail, code, (errors)}`로 표준화. **단 `raise`된 예외에만 적용 — view가 만든 `Response({...})`는 우회** |
| `DEFAULT_PAGINATION_CLASS` | **미설정** (`PAGE_SIZE`도 없음) | 전역 자동 페이지네이션 비활성. `ListAPIView`조차 자동 페이징 안 됨 |
| `DEFAULT_AUTHENTICATION_CLASSES` | JWT(우선) + Session | — |
| `DEFAULT_PERMISSION_CLASSES` | `IsAuthenticated` | — |
| `DEFAULT_RENDERER_CLASSES` | 미설정 → JSON + BrowsableAPI 기본 | — |

> **이 두 가지가 분열의 근원이다.** ① 전역 페이지네이션 미설정 → 각 view가 제각각 수동 처리. ② 예외 핸들러가 `raise`에만 동작 → 직접 `Response(error)` 반환 시 형식이 표준화되지 않음.

---

## 앱별 응답 패턴 매트릭스

범례: ✅ 일관 · ⚠️ 혼용/부분 · ❌ 위반/누락 · — 해당 없음

| 앱 / 파일 | 성공 래핑 | status 상수화 | POST→201 | 에러 키 | 페이지네이션 |
|-----------|-----------|----------------|----------|---------|--------------|
| `stocks/views.py` | ⚠️ 커스텀 envelope 혼용 | ✅ | — (RPC 200) | ⚠️ `{error}` + 중첩 `{error:{code,message,details}}` | ✅ `StockListPagination` (유일한 정식 DRF 페이징) |
| `stocks/views_exchange.py` | ✅ `{success,data,meta}` | ✅ | — (배치 200) | ✅ `{error}` | — (고정 소량) |
| `stocks/views_fundamentals.py` | ✅ `{success,data,meta}` | ✅ | — | ✅ `{error}` | — (limit≤40) |
| `stocks/views_screener.py` | ✅ `{success,data,meta}` | ✅ | — (GET) | ⚠️ `{error}` (값이 문자열 vs dict 혼재 L70) | — (limit≤1000) |
| `stocks/views_eod.py` | ❌ 비래핑/커스텀 | ✅ | — | ✅ `{error}` | — (slice 캡) |
| `stocks/views_indicators.py` | ❌ 비래핑 raw dict | ✅ | — (비교 200) | ✅ `{error}` | ❌ `symbols` 무제한 L361 |
| `stocks/views_market_movers.py` | ❌ `serializer.data` 직접 | ✅ | — | ✅ `{error}` | — (limit≤20) |
| `stocks/views_mvp.py` | ❌ 커스텀 envelope | ❌ `status` import만 미사용 | — | ❌ 에러 응답 없음 + `bare except:pass` L150 | — (slice ≤20) |
| `stocks/views_search.py` | ❌ 커스텀 `{count,results}` | ✅ | — | ✅ `{error}` (+`{valid,error}`) | — (slice ≤10) |
| `users/views.py` | ⚠️ 3종 혼용 (`serializer.data`/커스텀dict/`{ok,message}`) | ✅ (하드코딩 0) | ⚠️ 대부분 201, AddFavorite 200 L227, 조건부 L981·L1119 | ⚠️ **`error`/`message`/`detail` 3종** | ⚠️ Django Paginator 수동 2곳, 나머지 무제한 `.all()` |
| `metrics/views.py` | — 빈 스텁 | — | — | — | — |
| `market_pulse/views.py` | ⚠️ `serializer.data` + raw dict 혼용 | ✅ | ⚠️ sync POST 200 (생성 아님) | ✅ `{error}` | — (대시보드형) |
| `chain_sight/api/views.py` | ❌ 비래핑 수동 dict (serializer 미사용) | ✅ | — (GET) | ✅ `{error}` | ⚠️ `SignalFeedView` 수동 슬라이스, `SeedListView` 전량 |
| `chain_sight/views.py` | — 빈 스텁 | — | — | — | — |
| `portfolio/api/views.py` (coach e1~e6) | ✅ `serializer.data` | ✅ | — (분석 POST 의도적 200) | ✅ `{error}` (+scope/type) | — (단건) |
| `portfolio/views.py` | — 빈 스텁(legacy 제거) | — | — | — | — |
| `news/api/views.py` (`NewsViewSet`) | ⚠️ dict 래핑 + raw list 직접(L396) 혼용 | ✅ | — (트리거 200) | ⚠️ `{error}` + 예외 `detail` 혼재 | ⚠️ `NewsArticlePagination` (기본 list만), `@action`은 우회 |
| `news/views.py` | — 빈 스텁 | — | — | — | — |
| `rag_analysis/views.py` | ⚠️ `serializer.data` + 커스텀 dict | ✅ | ✅ **201 정상** (L61·139·295·446) + DELETE 204 | ✅ 예외 기반 `detail` (가장 표준적) | ⚠️ Django Paginator 수동 1곳, 목록 전량 |
| `sec_pipeline/views.py` | ❌ 비래핑 | ❌ **하드코딩 202/200** L49·53·55 | — (GET) | — (에러 분기 없음) | — (단건) |
| `serverless/views.py` | ⚠️ 평탄/`{count,목록}`/serializer 3종 혼용 | ✅ | ✅ 201(presets/alerts/import) + 트리거 200 | ✅ 예외 기반 `detail` (직접 error dict 0건) | ⚠️ FilterEngine 수동 페이징, 나머지 `[:limit]`/`.all()` |
| `serverless/views_admin.py` | ⚠️ 단일 키 래핑(`{actions}`/`{categories}`) | ✅ | ⚠️ 카테고리 201 L625, 트리거 200 | ✅ 직접 `{error}` + status (예외 raise 안 함) | ❌ `.all()` 전량 |
| `validation/api/views.py` | ❌ 평탄 dict 직접 (serializer 미사용) | ✅ | — (upsert 200) | ❌ **`{error}` vs `{symbol,error,message}` 혼용** | — (소규모 고정) |
| `validation/views.py` | — 빈 스텁 | — | — | — | — |
| `_dormant/graph_analysis/views.py` | — 빈 스텁(휴면) | — | — | — | — |
| `config/views.py` | ❌ DRF 아님 (`JsonResponse`/`render`), `Response` import 미사용 | — | — | — (health 실패도 200) | — |
| `iron_trading/views.py` | ❌ 비래핑 (`error_body` 헬퍼) | ❌ **하드코딩 400/404/503/200** L36·41·46·50 | — (GET) | ⚠️ `error_body(code,message)` 자체 구조 | — (단건) |

**래핑 컨벤션 분포:**
- `{success, data, meta}` 정식 래핑 → **`stocks/views_exchange` · `views_fundamentals` · `views_screener` 3개 파일뿐**
- 나머지 모든 활성 파일 → 비래핑 / 커스텀 envelope / `serializer.data` 직접 / `{count,목록}` 등 제각각
- `serverless/views.py`는 주석으로 **"envelope v2 = 평탄 응답"** 정책을 명시 → 의도적 비래핑 (stocks의 래핑 방침과 정면 충돌)

---

## HTTP 상태 코드 일관성

### 상수화 (`status.HTTP_*` vs 하드코딩 숫자)

대부분 양호. **하드코딩 위반은 단 2개 파일**:

| 파일 | 하드코딩 라인 | 비고 |
|------|---------------|------|
| `integrations/iron_trading/views.py` | L36 `status=400`, L41 `status=404`, L46 `status=503`, L50 `status=200` | `status` 모듈 import조차 안 함 |
| `services/sec_pipeline/views.py` | L49 `status=202`, L53 `status=200`, L55 `status=200` | `status.HTTP_*` 상수 미사용 |

기타 특이: `stocks/views_mvp.py`는 `status`를 import(L9)하나 **단 한 번도 사용 안 함** (모든 응답 기본 200).

### 생성(POST) → 201 일관성

**규칙 자체는 대체로 합리적이나 통일되지 않음:**

- **DB 리소스 생성 = 201 (정상 적용):**
  - `rag_analysis/views.py` L61·139·295·446 (Basket/Item/Session/StockData) — 가장 모범적
  - `serverless/views.py` L971·1282·1599 (preset/alert/import)
  - `serverless/views_admin.py` L625 (카테고리)
  - `users/views.py` L108·303·669·774 (회원가입/Portfolio/Watchlist/Item)
- **RPC/트리거/upsert/LLM = 200 (방어 가능):** Celery sync 트리거, peer 선호 upsert, 코치 분석 POST 등 — "생성"이 아니므로 200이 타당
- **누락/불일치:**
  - `users/views.py` L227 `AddFavorite` — 종목을 추가하면서 **201 미지정 → 200** (다른 생성 엔드포인트와 불일치)
  - `users/views.py` L981·L1119 — 조건부 `201 if added else 200` (BulkAdd/UserInterest)
  - `serverless/views.py` `generate_thesis` (L1677) — 생성 의미인데 200 + 폴백도 200

### 에러 상태 코드 — ⚠️ "에러인데 성공 코드 반환"

가장 위험한 패턴. HTTP 상태로는 200/found이면서 본문에 `error`를 담아 **클라이언트가 실패를 못 잡음**:

| 위치 | 증상 |
|------|------|
| `validation/api/views.py` L417 (insufficient_peers) | `status` 미지정 → 200, 본문은 에러 |
| `validation/api/views.py` L433 (no_leader) | 동상 200 + 에러 |
| `validation/api/views.py` L671 (LLM parse error) | 동상 200 + 에러 |
| `chain_sight/api/views.py` L288-292 (`ChainSightTraceView` except) | `error` 키 담으면서 status 미지정 → 200 |
| `config/views.py` `health_check` | DB 끊겨도 200 + `'disconnected'` 문자열 (헬스체크 의미 무력화) |

에러 코드 사용 분포(정상 케이스): 400(검증), 401(미인증), 403(권한), 404(미존재)는 광범위 사용. 422(`validation` L85 not_in_universe), 429(throttle/budget), 502/503(외부 API), 207(`users` L580 MULTI_STATUS)도 적재적소 등장.

---

## 에러 응답 형식

### 3가지 형식이 공존 — 근원은 "예외 핸들러 우회"

전역 `EXCEPTION_HANDLER`(`config.exception_handler`)는 `raise`된 DRF 예외를 `{status_code, detail, code, (errors)}`로 표준화한다. **그러나 view가 `Response({...}, status=...)`를 직접 만들면 이 핸들러를 거치지 않는다.** 결과적으로 두 경로가 갈린다:

| 형식 | 발생 경로 | 대표 파일 |
|------|-----------|-----------|
| `{detail, code, status_code}` | 예외 `raise` (NotFound/ValidationError/PermissionDenied) | `rag_analysis`, `serverless/views.py` (직접 error dict 0건 — 가장 표준적) |
| `{error: ...}` | `Response` 직접 반환 | `stocks/*`, `market_pulse`, `chain_sight`, `serverless/views_admin`, `validation/api` |
| `{message: ...}` | `Response` 직접 반환 (비즈니스 거부를 400으로) | `users/views.py` L219·250 (status 400인데 키가 `message`) |

### 같은 파일 내 혼용 사례

- **`users/views.py`**: `raise NotFound`(→`detail`) vs `Response({"error"}, 404)`(L557 RefreshStockData) vs `Response({"message"}, 400)`(L219·250) — **같은 앱에서 404/400 에러가 3가지 형태**. L534·586은 `{"error":..., "detail": str(e)}`로 두 키 동시 사용.
- **`validation/api/views.py`**: 단순 `{"error": "..."}`(L71·231·412 등) vs 구조화 `{"symbol", "error", "message"}`(L81·110·418·444) 혼용.
- **`stocks/views.py`**: 평문 `{error}` vs 중첩 `{error:{code,message,details}}`(L654·1016) 혼용. `StockSearchAPIView`는 `{result, message}`(L204)와 `{results, message}`(L214) — **`result`/`results` 키 불일치(잠재 버그)**.

### 헬퍼 기반 (별도 계열)

`iron_trading/views.py`는 `error_body(code, message, ...)` 공유 헬퍼로 `{error, code, message}` 구조를 만든다 — 다른 어느 파일과도 형식이 다름.

---

## 페이지네이션 현황

### 정식 DRF 페이지네이션 — 단 2곳

| 위치 | 클래스 | 적용 범위 |
|------|--------|-----------|
| `stocks/views.py` L92·100 `StockListAPIView` | `StockListPagination(PageNumberPagination)` (page_size=50, max 200) | 정상 |
| `news/api/views.py` L55 `NewsArticlePagination` | `PageNumberPagination` (page_size=20, max 100) | **ViewSet 기본 `list`에만** — `@action` 커스텀은 전부 우회 |

> `CursorPagination`은 **사용처 0건**. 전역 `DEFAULT_PAGINATION_CLASS`도 미설정.

### 수동/유사 페이지네이션

- `rag_analysis/views.py` `UsageHistoryView` (L750) — Django `Paginator` + `{results, pagination}` 커스텀
- `serverless/views.py` `advanced_screener`/`execute_preset` — FilterEngine 내부 page/page_size + `next`/`previous` URL 직접 생성
- `users/views.py` `WatchlistListCreateView`(L635)·`WatchlistStocksView`(L884) — Django `Paginator` 수동, `{results, pagination}` dict

### 페이지네이션 없이 통째 반환 (잠재 성능/페이로드 리스크)

| 위치 | 패턴 |
|------|------|
| `users/views.py` L93 `Users.get` | `User.objects.all()` 전량 |
| `users/views.py` L272·200·423·1049 | Portfolio/Favorites/Interest 목록 전량 |
| `serverless/views_admin.py` L505·763 | 카테고리·섹터 `.all()` 전량 |
| `serverless/views.py` `etf_collection_status` L1958 | `.all()` 전량 + 파이썬 루프 |
| `rag_analysis/views.py` L52·429·496 | baskets/sessions/messages `.filter().all()` 전량 |
| `news/api/views.py` `collection_logs` L1452 | `list(qs.values(...))` 전량 |
| `chain_sight/api/views.py` `SeedListView` L367 | 시드 전량 |
| `stocks/views_indicators.py` `IndicatorComparisonView` L361 | 호출자 제공 `symbols` 서버 상한 없음 |

> 대부분은 `[:limit]` slice 캡 또는 외부 API limit으로 사실상 제한되나, 위 목록은 **상한 없는 `.all()` 직렬화** 또는 **무제한 입력**으로 데이터 증가 시 위험.

---

## 권고사항

우선순위 순. (※ 본 보고서는 감사 전용 — 아래는 제안이며 코드는 미변경)

### P0 — 정확성 (즉시)

1. **에러를 HTTP 200으로 반환하는 5곳 수정**
   `validation/api/views.py` L417·L433·L671, `chain_sight/api/views.py` L288, `config/views.py` health_check — 에러 시 4xx/5xx 명시. 현재 프론트의 에러 핸들링이 무력화될 수 있음.
2. **`stocks/views.py` `result`/`results` 키 통일** (L204 vs L214) — 빈 쿼리 분기의 잠재 버그.

### P1 — 일관성 (단기)

3. **에러 응답 형식 단일화** — `EXCEPTION_HANDLER`가 이미 `{detail, code}`를 표준화하므로, **직접 `Response({"error"/"message"})` 반환을 예외 `raise`로 전환**하거나, 최소한 키를 `detail` 하나로 통일. 특히 `users/views.py`(error/message/detail 3종 혼재)와 `validation/api/views.py` 우선.
4. **상태 코드 상수화 강제** — `iron_trading/views.py`, `sec_pipeline/views.py`의 하드코딩 숫자를 `status.HTTP_*`로 교체. lint 규칙(예: flake8 커스텀/grep CI 게이트)으로 재발 방지.
5. **`stocks/views_mvp.py`의 `bare except: pass`(L150) 제거** — 무성 실패는 디버깅 불가. 로깅 + 적절한 status로 전환.

### P2 — 구조 (중기, 결정 필요)

6. **성공 응답 래핑 정책 1개로 확정** — 현재 `{success,data,meta}`(stocks 3파일)와 평탄 응답(serverless "envelope v2")이 **상반된 정책으로 공존**. 둘 중 하나를 `DECISIONS.md`에 단일 소스로 명문화하고, 신규 코드는 그 규약을 따르도록 강제. (기존 코드 일괄 마이그레이션은 프론트 영향 크므로 별도 계획)
7. **목록 API 페이지네이션 표준 도입** — 상한 없는 `.all()` 직렬화 엔드포인트(users `Users`/`Portfolio`/`Interest`, serverless_admin 카테고리, rag baskets/sessions/messages)에 페이지네이션 적용. 전역 `DEFAULT_PAGINATION_CLASS` 설정 시 부작용(기존 비래핑 응답 형태 변경)을 검토한 뒤, 영향 없는 곳부터 view 단위 `pagination_class` 지정 권장.
8. **빈 스텁 정리** — `metrics`, `news/views`, `validation/views`, `chain_sight/views`, `portfolio/views`, `graph_analysis` 6개 스텁은 실제 API 위치(`*/api/views.py`)와 혼동 유발. 주석 또는 `__all__`로 "이 모듈은 미사용, API는 api/views.py" 명시.

### 참고 — 모범 사례로 삼을 파일

- **에러 형식**: `rag_analysis/views.py`, `serverless/views.py` (예외 raise 일관, `detail` 표준)
- **상태 코드**: `rag_analysis/views.py` (201/204 정확)
- **성공 래핑**: `stocks/views_exchange.py` 계열 (`{success,data,meta}` 일관) — 단 전역 정책으로 채택할지는 결정 필요

---

*감사 종료. 분석 파일 18개(활성) + 9개(스텁) = 27개. 코드 변경 0건.*
