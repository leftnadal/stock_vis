# API 응답 일관성 감사 보고서

- 작성일: 2026-06-15
- 범위: 전체 `views*.py` 37개 파일 (REST 엔드포인트 보유 파일 + 스텁/휴면 포함)
- 방식: 읽기 전용 정적 분석 (코드 수정 없음)
- 기준선: **`docs/features/api_envelope/policy.md` (2026-05-12 표준)** — 직전 감사 `reports/5월/5일/api_consistency_audit.md`의 P1 #14 후속
- 판정 범례: ✅ 준수 / ⚠️ 부분/회색지대 / ❌ 위반

---

## 요약

### 기준 정책 (2026-05-12 표준)
| 항목 | 표준 |
|------|------|
| 성공 응답 | `serializer.data` 또는 dict **평탄 반환**. `{success, data, meta}` 래핑 **폐기** |
| 에러 응답 | `{detail, code?, errors?, status_code}` 단일 표준. **`raise` → `config.exception_handler.custom_exception_handler`가 변환** |
| 도메인 에러 | `rag_analysis/exceptions.py`, `serverless/exceptions.py`의 `APIException` 서브클래스로 `code` 보존 (CacheError/GenerationFailed/SyncFailed 등) |
| 페이지네이션 | DRF `PageNumberPagination` per-view (`{count, next, previous, results}`) |
| 명시적 예외 | **Market Pulse v2 카드 API** (`cards.py:_envelope`), **SSE 스트림 이벤트 페이로드**만 envelope 허용 |

### 핵심 발견 (심각도순)

1. **🔴 에러 형식 표준 위반이 가장 광범위** — 표준은 `{detail, code?, status_code}`인데, 분석한 대다수 파일이 인라인 `Response({"error": ...})`를 사용. **에러 키 `{error}` 사용 파일이 20개+, 누적 위반 100건+.** 같은 프로젝트 내에서 표준 준수(`serverless`, `rag_analysis`)와 위반(`validation`, `chain_sight`, `admin`, `market_pulse v1`)이 공존 → **클라이언트가 `detail`/`error`/`message` 3종 형식을 모두 처리해야 하는 이중 진실 소스.**

2. **🟠 폐기된 `{success, data, meta}` 래핑 잔존** — `views_exchange.py`(5), `views_fundamentals.py`(5), `views_screener.py`(7) = **17개 view가 폐기 패턴 그대로.** 2026-05-12 마이그레이션이 이 3개 파일에 미적용.

3. **🟠 비즈니스 "없음/실패"를 200으로 반환 (정상화 누락)** — `validation`(insufficient_peers/no_leader/LLM parse error), `news`(daily_keywords not_found/ml no_report), `chain_sight`(trace 예외 삼킴) 등에서 에러·빈 결과를 HTTP 200 + body status 필드로 처리. 모니터링·클라이언트 분기 혼선.

4. **🟡 페이지네이션 표준(PageNumberPagination per-view) 거의 미적용** — 표준 클래스 보유는 `stocks/views.py:StockListPagination`, `news:NewsArticlePagination` 2곳뿐. 나머지는 전량 반환 또는 수동 `page/limit` 슬라이싱 + 자체 `{results, pagination}` envelope (DRF 표준 `{count,next,previous,results}`와도 불일치).

5. **🟢 HTTP status 코드 / 모듈 사용은 대체로 양호** — 대부분 `status.HTTP_*` 모듈 상수 사용. 하드코딩 정수는 `iron_trading/views.py`, `sec_pipeline/views.py:50/53/55`, `cards.py:85` 소수. POST 201은 생성성 엔드포인트에서 대체로 준수(`users`, `rag_analysis`, `serverless`).

### 모범 사례 (표준 정확 부합)
- **`services/rag_analysis/views.py`** — 도메인 APIException(CacheError/CostError/HistoryError) raise + 201/204 정확. 에러 모델 모범.
- **`services/serverless/views.py`** — DRF + 도메인 예외 raise 일관, env2(평탄) 캐시 설계.
- **`thesis/views/monitoring_views.py`** — `get_object_or_404` 위임으로 표준 에러 자동화.
- **`packages/shared/stocks/views_market_movers.py:72`** — `Response(serializer.data)` 순수 평탄.

---

## 앱별 응답 패턴 매트릭스

| 파일 (앱) | 성공 래핑 | 에러 형식 | status 코드 | 페이지네이션 | 종합 |
|-----------|-----------|-----------|-------------|--------------|------|
| **stocks**/views.py | ⚠️ ad-hoc envelope(`{symbol,tab,data,_meta}`) | ❌ `{error}`+`{message}`+중첩 혼재 | ✅ status 모듈 | ✅ StockListPagination(유일 모범) | ❌ |
| stocks/views_eod.py | ✅ 평탄 | ❌ `{error}` | ✅ | ⚠️ `[:n]` 상한 | ⚠️ |
| stocks/views_exchange.py | ❌ **`{success,data,meta}`×5** | ❌ `{error}` | ✅(정수 일부) | N/A(외부 API) | ❌ |
| stocks/views_fundamentals.py | ❌ **`{success,data,meta}`×5** | ❌ `{error}` | ✅ | ⚠️ limit 상한 | ❌ |
| stocks/views_indicators.py | ✅ 평탄 | ❌ `{error}` | ✅ | ⚠️ 입력 심볼 상한 없음 | ⚠️ |
| stocks/views_market_movers.py | ✅ 평탄(모범) | ❌ `{error}`×1 | ✅ | N/A | ⚠️ |
| stocks/views_mvp.py | ⚠️ ad-hoc(`{mode,data}`) | ✅ get_object_or_404 | ✅ | ❌ `all()[:20]` | ⚠️ |
| stocks/views_screener.py | ❌ **`{success,data,meta}`×7** | ❌ `{error}`+serializer.errors 수동래핑 | ✅ | ⚠️ limit max 1000 | ❌ |
| stocks/views_search.py | ✅ 평탄 | ❌ `{error}`+`{valid,error}` 비대칭 | ✅ | N/A | ⚠️ |
| **users**/views.py | ⚠️ 일부 키 래핑(`{portfolios}`,`{results,pagination}`) | ❌ `{error}`+`{message}` 에러용 | ✅ status 모듈, 201/204 준수 | ⚠️ Django Paginator 커스텀 + 무제한 목록 | ❌ |
| users/jwt_views.py | ⚠️ serializer.data를 `user`키 래핑 | ❌ `{error}` 전건 | ✅ 201 | N/A | ❌ |
| **metrics**/views.py | — 스텁(view 없음) | — | — | — | — |
| api_request/admin_views.py | ✅ 평탄 | ❌ `{error: str(e)}` 전건(500 직노출) | ✅ | N/A(상태조회) | ❌ |
| **config**/views.py | — JsonResponse(DRF 외부) | — handler 미경유 | ⚠️ health 장애시도 200 | N/A | ⚠️ |
| iron_trading/views.py | ✅ 평탄 | ⚠️ 커스텀 `error_body(code,message)` | ❌ 정수 하드코딩(36/41/46/50) | N/A(단건) | ⚠️ |
| **market_pulse**/views.py (v1) | ✅ 평탄 | ❌ `{error}`×11(전 에러경로) | ✅ status 모듈 | ⚠️ 소규모 통째 | ❌ |
| market_pulse/api/views/cards.py (v2) | ✅ **`_envelope` 허용 예외** | ❌ `{error}`×1(`:85`) | ⚠️ 404 정수(`:85`) | N/A | ⚠️ |
| market_pulse/api/views/overview.py | ⚠️ `_meta` 병합형(예외 미등록) | ✅ soft-fail | ✅ 200 단일 | N/A(상한고정) | ⚠️ |
| market_pulse/api/views/news_refresh.py | ⚠️ `_meta` 병합형(예외 미등록) | ✅ | ✅ | 상한 고정 | ⚠️ |
| market_pulse/api/views/i18n.py | ⚠️ `_meta` 병합형(예외 미등록) | ✅ warning soft-fail | ✅ | N/A | ⚠️ |
| market_pulse/api/views/health.py | ⚠️ `_meta` 병합형(예외 미등록) | ✅ | ⚠️ 장애시도 200 | N/A | ⚠️ |
| **portfolio**/api/views.py (coach E1~6) | ✅ 평탄 | ❌ `{error}` 수동 + `{detail}` DRF **혼재** | ✅ 200/400/429/502/500 모범 | N/A(단건) | ⚠️ |
| portfolio/views.py | — 빈 모듈(Slice13 #65 제거) | — | — | — | — |
| **chain_sight**/api/views.py | ✅ 평탄 | ❌ `{error}`×9 + 예외 200 삼킴(`:288-292`) | ✅ status 모듈 | ❌ 수동 limit/page×4, DRF 미적용 | ❌ |
| chain_sight/api/event_views.py | ✅ 평탄 | ❌ `{error}`×4 | ✅ | ❌ 목록 전량 | ❌ |
| chain_sight/views.py | — 빈 파일 | — | — | — | — |
| **serverless**/views.py | ✅ 평탄(env2, 모범) | ✅ DRF+도메인 raise(모범) | ✅ 201/status | ⚠️ 수동 page, DRF 미통일 | ✅ |
| serverless/views_admin.py | ✅ 평탄 | ❌ `{error: str(e)}` 30+건(500 직노출) | ✅ 201/204 | ❌ 목록 전량 | ❌ |
| **sec_pipeline**/views.py | ✅ 평탄 | ✅ handler 위임 | ❌ 정수 하드코딩(50/53/55) | N/A(단건) | ⚠️ |
| _dormant/graph_analysis/views.py | — 휴면, 빈 파일 | — | — | — | — |
| **news**/api/views.py | ✅ 평탄 | ⚠️ ValidationError(표준)/`{error}` 혼용 | ⚠️ 일부 200 정상화 누락 | ⚠️ NewsArticlePagination 있으나 custom action 우회 | ⚠️ |
| news/views.py | — 스텁 | — | — | — | — |
| **rag_analysis**/views.py | ✅ 평탄 | ✅ 도메인 APIException(모범) | ✅ 201/204 | ⚠️ UsageHistory 커스텀 envelope | ✅ |
| **validation**/api/views.py | ✅ 평탄 | ❌ `{error}` 전면(최대 위반) | ⚠️ 422/404 정상화 일부 + insufficient_peers 200 | ⚠️ 없음(소규모) | ❌ |
| validation/views.py | — 스텁 | — | — | — | — |
| **thesis**/views/conversation_views.py | ✅ 평탄 | ⚠️ `{error}`×2 + serializer raise(표준) | ⚠️ 생성 201 미사용 | ⚠️ `[:12]` 상한 | ⚠️ |
| thesis/views/monitoring_views.py | ✅ 평탄 | ✅ get_object_or_404(모범) | ✅ | ⚠️ `[:50]` 상한 | ✅ |

> 스텁/빈/휴면 파일: `metrics/views.py`, `news/views.py`, `validation/views.py`, `chain_sight/views.py`, `portfolio/views.py`, `_dormant/graph_analysis/views.py` — view 0건, 감사 대상 없음.

---

## HTTP 상태 코드 일관성

### status 모듈 vs 하드코딩 정수
- **`status.HTTP_*` 모듈 사용 (표준)**: 대다수 파일. stocks 전체, users, market_pulse v1, portfolio coach, chain_sight, serverless, rag_analysis, validation, thesis.
- **정수 하드코딩 (⚠️ 컨벤션 불일치, 동작은 정확)**:
  - `integrations/iron_trading/views.py:36/41/46/50` — `status` 임포트 없이 `200/400/404/503` 리터럴.
  - `services/sec_pipeline/views.py:50/53/55` — `status=202`, `status=200`.
  - `apps/market_pulse/api/views/cards.py:85` — `status=404`.

### 생성(POST) 시 201 일관성
- **201 정확 사용**: `users/views.py`(108/303/669/774), `jwt_views.py:120`, `rag_analysis/views.py`(61/139/295/446), `serverless/views.py`(971/1282/1599), `admin_views.py:606`.
- **조건부 201 (bulk, 합리적)**: `users WatchlistBulkAddView:981`, `UserInterestListCreateView:1119` (`201 if created else 200`).
- **201 미사용이 적절한 POST**: batch quote / sync trigger / LLM 코멘터리 / screener 등 조회·트리거성 — 200 정상.
- **⚠️ 생성 의미론 약한 200**: `thesis/conversation_views`(대화 turn), `news generate_daily_keywords:666`(task 트리거) — 경계 케이스, 위반 아님.

### 4xx/5xx 사용 패턴
- **세분화 모범**: `portfolio/api/views.py` — 400(검증)/429(budget)/502(LLMError)/500(unexpected) 분리.
- **422 비즈니스 상태**: `validation/api/views.py:79-86` (not_in_universe→422), `:108-115`(no_data→404) — 정책의 status 정상화 부분 반영.
- **🔴 비즈니스 "없음/실패"를 200으로 반환 (정상화 누락 / 에러 삼킴)**:
  - `validation/api/views.py:416-423` insufficient_peers → 200
  - `validation/api/views.py:432-433` no_leader → 200
  - `validation/api/views.py:671-678` LLM parse error → 200
  - `news/api/views.py:594-604` daily_keywords not_found → 200
  - `news/api/views.py:1247-1253` ml_shadow_report no_report → 200
  - `chain_sight/api/views.py:288-292` trace 예외를 `{found:False, error}` + 200으로 삼킴
- **🔴 500 내부 메시지 직노출 (정보 노출)**: `admin_views.py`(7 dashboard view `{"error": str(e)}` 500), `serverless/views_admin.py` 동일 패턴.
- **⚠️ health 엔드포인트가 장애 시에도 200**: `config/views.py:73-82`(DB/cache disconnected도 200), `market_pulse/api/views/health.py`(probe 실패 body 플래그만) — 모니터링 관점 약점.

---

## 에러 응답 형식

### 표준 vs 실제 (키 분포)
| 형식 | 의미 | 사용처 |
|------|------|--------|
| `{detail, code?, errors?, status_code}` | **표준** (raise→handler) | `serverless/views.py`, `rag_analysis/views.py`, `monitoring_views.py`, `sec_pipeline`, `stocks/views_mvp` (get_object_or_404 경유) |
| `{"error": ...}` | ❌ **비표준 (최다)** | stocks(views/eod/exchange/fundamentals/indicators/market_movers/screener/search), users, jwt_views, admin_views, market_pulse v1, cards.py:85, portfolio coach(혼재), chain_sight(api/event), serverless_admin, validation, news(혼용), conversation_views |
| `{"message": ...}` (에러용) | ❌ 비표준 | `stocks/views.py:206/214`, `users AddFavorite:219`/`RemoveFavorite:250`(400인데 message) |
| `{"error": {code, message, details}}` 중첩 | ❌ 자기모순 | `stocks/views.py:652-665`(Overview), `:1014-1026`(RateLimit) — 같은 파일 내 평탄 `{error:str}`와 불일치 |
| `error_body(code, message)` 커스텀 | ⚠️ 별도 계약 | `iron_trading/views.py`(외부 봇 전용, 의도적 가능성 — `daily_context.py` 스키마 확인 필요) |

### 구조적 문제
1. **단일 파일 내 혼재**: `portfolio/api/views.py` — 수동 에러는 `{error}`, serializer `raise_exception=True`는 DRF `{detail/errors}`. 동일 엔드포인트가 실패 경로마다 다른 형식. `news/api/views.py`, `conversation_views.py`도 동일 혼용.
2. **handler 우회**: `stocks/views.py:649` `StockNotFoundError.to_response()` 직접 호출 — custom_exception_handler 경유 안 함.
3. **성공/실패 비대칭**: `stocks/views_search.py:116-123` — 성공 `{valid:True}` vs 실패 `{valid:False, error}`.
4. **serializer.errors 수동 래핑**: `stocks/views_screener.py:69-71` `{'error': serializer.errors}` — `is_valid(raise_exception=True)` 쓰면 표준 변환되는데 수동.

### 예외(위반 아님)
- **SSE 스트림 payload**: `rag_analysis/views.py:582/593`(ChatStreamView), serverless 스트림 — StreamingHttpResponse 데이터이므로 표준 에러 모델 비대상.
- **계약 테스트 통과 확인**: `tests/contracts/test_response_envelope.py` — custom_exception_handler가 raise 기반 에러를 표준 envelope로 변환함을 검증. 즉 **`raise` 경로는 표준 보장, 인라인 `Response({"error":...})` 경로만 우회**가 문제의 본질.

---

## 페이지네이션 현황

### DRF `PageNumberPagination` 클래스 보유 (표준)
- `packages/shared/stocks/views.py:92 StockListPagination` (page_size 50, max 200) → `StockListAPIView`. **유일하게 완전 모범.**
- `services/news/api/views.py:55 NewsArticlePagination` (page_size 20) → ViewSet list/retrieve. **단, custom action(`stock_news`, `market`, `trending`, `all_news`, `collection_logs`)은 우회하여 전량/수동 슬라이싱.**

### 수동 페이지네이션 (자체 `{results, pagination}` envelope — DRF 표준 형식과 불일치)
- `users/views.py:635/884` (WatchlistListCreate/WatchlistStocks) — Django Paginator + `{results, pagination}`.
- `rag_analysis/views.py:783-817` (UsageHistoryView) — Django Paginator + `{results, pagination}`.
- `serverless/views.py:1183-1222`(advanced_screener), `:1048-1073`(execute_preset) — `page/page_size/next/previous` 수동 생성.
- `chain_sight/api/views.py:739-768`(SignalFeedView) — `page/page_size/has_next/total_count` 수동.

### 페이지네이션 없이 목록 전량 반환 (잠재 위험)
- **무제한 목록**: `users`(Users.get:93 `User.objects.all()`, UserFavorites:197, PortfolioListCreate:271, UserInterest:1045), `chain_sight`(SeedListView:367 전량, event board/ranking), `serverless_admin`(NewsCategory/SectorOptions), `rag_analysis`(basket/session/messages 전건), `validation`(presets/metrics/comparisons — 소규모).
- **상한 슬라이싱(`[:n]`)으로만 통제 (page 이동 불가)**: `stocks/views_mvp.py:30` `all()[:20]`, `views_eod`(`[:50]`/`[:7]`), `views_fundamentals`(limit max 40), `views_screener`(**limit max 1000** — 상한 큼), `thesis`(`[:12]`/`[:50]`), `serverless`(get_llm_relations `[:50]`).

### 평가
- 정책은 "PageNumberPagination per-view, 전역 미적용"인데 실제로는 **2개 view만 표준 적용.** 나머지는 (a) 전량 반환, (b) 수동 envelope, (c) 상한 슬라이싱으로 3분화.
- 대부분 목록이 소규모(대시보드/프리셋/세션)라 즉각적 DoS 위험은 낮으나, **`screener` limit max 1000**, **`users User.objects.all()`**, **`chain_sight SeedListView` 전량**은 데이터 증가 시 표면 확대.

---

## 권고사항

> 본 보고서는 읽기 전용 감사이며, 아래는 후속 작업 제안임 (코드 수정 없음).

### P0 — 에러 형식 표준화 (영향 최대, 20+ 파일)
1. **인라인 `Response({"error": ...}, status=...)` → DRF/도메인 `raise` 전환.** custom_exception_handler가 이미 `{detail, code, status_code}`로 변환하므로(계약 테스트 통과 확인됨), 호출부를 `raise NotFound(...)` / `raise ValidationError(...)` / 도메인 APIException으로 바꾸면 자동 일관화.
   - 최대 위반자 우선: `validation/api/views.py`, `serverless/views_admin.py`(+`str(e)` 노출 제거), `chain_sight/api/views.py`+`event_views.py`, `market_pulse/views.py`(v1), `users`/`jwt_views`.
2. **`{"message": ...}` 에러 응답 제거** — `stocks/views.py:206/214`, `users:219/250`.
3. **단일 파일 내 혼재 해소** — `portfolio/api/views.py`, `news/api/views.py`: serializer raise와 수동 `{error}`가 섞이지 않도록 수동 분기도 raise로 통일.
4. **`str(e)` 500 직노출 차단** — `admin_views.py`, `serverless/views_admin.py`: 도메인 예외 raise로 전환(메시지 새니타이즈).

### P1 — 폐기된 `{success, data, meta}` 래핑 평탄화 (17 view)
- `stocks/views_exchange.py`(5), `views_fundamentals.py`(5), `views_screener.py`(7) — 2026-05-12 마이그레이션 누락분. `data` 언래핑 + `meta`는 응답 헤더(X-Request-Id 등)로 분리 또는 평탄 dict 병합.
- ⚠️ **FE 영향 확인 필수**: `screenerService.ts`, `ragService.ts`가 정책에 마이그레이션 대상으로 명시됨 → 언래핑 시 FE 파서 동기 수정 필요.

### P2 — 비즈니스 상태 정상화 일관화
- 200으로 삼키는 "없음/실패"를 정책대로 처리: `validation`(insufficient_peers/no_leader/LLM parse → 422/404 또는 명시 status), `news`(not_found/no_report), `chain_sight trace`(예외 200 삼킴 → 적절한 4xx/5xx).

### P3 — v2 `_meta` 병합형 정책 정합화 (결정 필요)
- `market_pulse/api/views/`의 `overview.py`/`news_refresh.py`/`i18n.py`/`health.py`는 `_meta`를 페이로드에 병합 — `cards.py:_envelope`만 명시 예외이고 이들은 미등록. **2가지 선택**: (a) policy.md 예외 목록에 등록(계약 고정 인정), (b) `_meta` → 응답 헤더 분리. **권장: (a)** — 이미 OpenAPI 계약(OverviewResponseSerializer)으로 고정됨.

### P4 — 페이지네이션 표준화 (낮은 긴급도)
- 무제한 목록에 PageNumberPagination 적용 우선순위: `users User.objects.all()`, `chain_sight SeedListView`, `screener`(limit 1000 축소).
- 수동 `{results, pagination}` envelope(`users`, `rag_analysis UsageHistory`, `serverless`)를 DRF 표준 `{count, next, previous, results}`로 통일.

### P5 — 미세 컨벤션
- status 정수 하드코딩 → `status.HTTP_*` 모듈: `iron_trading/views.py`, `sec_pipeline/views.py:50/53/55`, `cards.py:85`.
- health 엔드포인트 장애 시 503 반환 검토: `config/views.py`, `market_pulse health.py`.
- `iron_trading error_body` 스키마(`daily_context.py`)가 표준 `{detail, code, status_code}`와 부합하는지 별도 확인(외부 봇 계약이라 의도적 분리일 수 있음).

### 부채 추적 권고
- 본 감사는 직전 `5월/5일` 감사의 P1 #14 후속 검증 성격. **#14 마이그레이션이 17개 view(P1)와 인라인 `{error}`(P0)에서 미완료**임을 확인 → `common-bugs.md` 또는 KB `TROUBLESHOOT`에 "에러 envelope 마이그레이션 잔여분" 등록 권장.
