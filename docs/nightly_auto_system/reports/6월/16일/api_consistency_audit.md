# API 응답 일관성 감사 보고서

- **작성일**: 2026-06-16
- **방식**: 읽기 전용 감사 (코드 수정 없음)
- **대상**: `views*.py` 전체 27개 파일, 약 14,411줄
- **선행 감사**: `docs/nightly_auto_system/reports/5월/5일/api_consistency_audit.md`
- **기준 정책**: `docs/features/api_envelope/policy.md` (2026-05-12, envelope 폐기 + DRF 평탄 통일 결정)

---

## 요약

### 핵심 결론

2026-05-12 정책(`{success, data, meta}` envelope **폐기**, DRF 평탄 응답 + `{detail, code?, errors?, status_code}` 에러 통일)이 채택되었으나, **마이그레이션이 미완**이다. 전역 인프라(`EXCEPTION_HANDLER`, 도메인 `APIException`)는 정착했지만, 개별 view 레벨에서 **3종의 응답 스키마가 여전히 공존**한다.

| # | 발견 | 심각도 | 위치 |
|---|------|--------|------|
| **F1** | 폐기된 `{success, data, meta}` envelope 잔존 (stocks 앱 3개 파일 17건) | 🔴 높음 | `views_fundamentals.py`, `views_exchange.py`, `views_screener.py` |
| **F2** | 동일 앱(stocks) 내 2가지 스키마 공존 → FE가 엔드포인트별 unwrap 분기 필요 | 🔴 높음 | stocks 앱 전반 |
| **F3** | 에러 키 3종 혼재 (`{error}` 우세, `{detail}`은 DRF raise 자동, `{message}` 성공/진행용) | 🟡 중간 | 전 앱 |
| **F4** | 생성(POST) 응답에서 201 vs 200(기본값) 불일치 — 201은 극소수 | 🟡 중간 | serverless, users, rag_analysis |
| **F5** | DRF `pagination_class` 사용 0건 — 목록 API 대부분 무제한/하드코딩 슬라이싱 | 🟡 중간 | 전 앱 (특히 serverless, users, chain_sight) |
| **F6** | `status.HTTP_*` 상수 미사용(하드코딩 숫자) | 🟢 낮음 | `iron_trading/views.py`, `sec_pipeline/views.py` |

### 정책 대비 진척도

| 정책 항목 | 상태 | 비고 |
|-----------|------|------|
| `EXCEPTION_HANDLER` 등록 | ✅ 완료 | `config/exception_handler.py` 운영 중 |
| 도메인 `APIException` 서브클래스 | ✅ 완료 | serverless/rag_analysis 8종 import 확인 |
| 에러 envelope `{detail, code, status_code}` | 🟡 부분 | `raise` 경로만 적용. `return Response({error})` 직반환 다수 잔존 |
| 성공 응답 평탄화 (envelope 폐기) | 🔴 미완 | stocks 3개 파일에서 `{success}` envelope 잔존 |
| `PageNumberPagination` 표준 | 🔴 미완 | 클래스 사용 0건 |

---

## 앱별 응답 패턴 매트릭스

성공 응답 스키마를 3종으로 분류: **W**=`{success, data, meta}` envelope (폐기 대상), **F**=평탄(serializer.data/dict 직접), **C**=커스텀 dict(`{count, results}` 등 키 래핑).

| 파일 | 주 패턴 | W | F | C | 에러 키 | 에러 방식 | 비고 |
|------|---------|---|---|---|---------|-----------|------|
| `stocks/views_fundamentals.py` | **W** | 5 | 0 | 0 | `error` | return | 🔴 envelope 전수 잔존 |
| `stocks/views_exchange.py` | **W** | 5 | 0 | 0 | `error` | return | 🔴 envelope 전수 잔존 |
| `stocks/views_screener.py` | **W** | 7 | 0 | 0 | `error` | return | 🔴 envelope 전수 잔존, raise 0 |
| `stocks/views.py` | F+C | 0 | ~18 | ~7 | `error`(중첩 code/message 혼재) | return+raise | 차트/탭별 독자 구조 |
| `stocks/views_indicators.py` | F | 0 | 4 | 0 | `error` | return | 평탄 일관 |
| `stocks/views_mvp.py` | F | 0 | 4 | 0 | (get_object_or_404) | raise | view레벨 에러 0 |
| `stocks/views_search.py` | F+C | 0 | 1 | 2 | `error` | return | `{count, results}` |
| `stocks/views_eod.py` | F+C | 0 | 1 | 2 | `error` | return | DB 사전구성 JSON |
| `stocks/views_market_movers.py` | F | 0 | 1 | 0 | `error` | return | serializer.data |
| `users/views.py` | F+C | 0 | 20 | 36 | `error`/`detail`/`message` 혼재 | return+raise(23) | 🔴 일관성 최저, 키 `ok`까지 |
| `serverless/views.py` | C 우세 | 0 | 8 | 60+ | `message`(22)/`error`(6) | raise(28)+return(5) | `{count, items}` 래핑 우세 |
| `serverless/views_admin.py` | F | 0 | 31 | 0 | `error`(26) | return(26) | raise 0, status 상수 일관 |
| `news/api/views.py` | F | 0 | 67 | 0 | `error`(6)/`message`(2) | raise ValidationError(10)+return(6) | `{success}` 0건, 평탄 일관 |
| `chain_sight/api/views.py` | F(meta 선택) | 0 | 7 | 0 | `error`(9) | return(9) | raise 0, meta 선택적 포함 |
| `rag_analysis/views.py` | F+C | 0 | 다수 | 일부 | `error`(1)/`message`(2)/detail(raise) | raise(12)+return(3) | SSE 이벤트 에러 별도 |
| `validation/api/views.py` | F | 0 | ~7 | 0 | `error`(8) | return(10) | raise 0, `{error}` 일관 |
| `market_pulse/views.py` | F | 0 | 11 | 0(progress는 message) | `error`(10) | return | v2 cards `_envelope`는 별도(정책 예외) |
| `portfolio/api/views.py` | F | 0 | 6 | 0 | `error`(+scope/type) | return+raise(6) | 429/502 세밀 활용 ⭐ |
| `iron_trading/views.py` | F | 0 | 1 | 0 | `error_body()`(code/message) | return | 🟢 하드코딩 status |
| `sec_pipeline/views.py` | F | 0 | 1 | 0 | 없음 | — | 🟢 하드코딩 status(200/202) |
| `config/views.py` | JsonResponse | — | — | — | — | — | 순수 Django(DRF 아님) |
| `portfolio/views.py` | 빈 파일(16줄) | — | — | — | — | — | Slice 13 legacy 제거 잔재 |
| `chain_sight/views.py`, `validation/views.py`, `news/views.py`, `metrics/views.py`, `graph_analysis/views.py` | 빈 스켈레톤 | — | — | — | — | — | 구현 없음 |

### 매트릭스 해석

- **W(폐기 envelope) 잔존**: `stocks/views_fundamentals.py`(5) + `views_exchange.py`(5) + `views_screener.py`(7) = **17건**. 정책 직접 위반.
- **stocks 앱 내부 분열**: 같은 앱에서 fundamentals/exchange/screener는 `{success}` envelope, indicators/mvp/search/eod/market_movers는 평탄 → FE가 동일 앱인데 엔드포인트별로 unwrap 로직을 달리해야 함 (F2).
- **C(커스텀 래핑) 집중**: `serverless/views.py`(60+), `users/views.py`(36) — `{count, items/alerts/presets}` 형태. envelope은 아니지만 자원 목록을 키로 감싸 평탄 정책과 다름.
- **평탄(F) 우세 앱**: news, serverless_admin, chain_sight, validation, market_pulse, portfolio — 정책 정렬 양호.

---

## HTTP 상태 코드 일관성

### 생성(POST) 응답: 201 vs 200

| 파일 | 201 사용 | 200 기본값(생성인데 200) | 평가 |
|------|----------|--------------------------|------|
| `serverless/views.py` | 3 (L973, L1284, L1601) | 47+ (trigger_sync, sync_now 등) | 🔴 생성·트리거 대부분 200 |
| `users/views.py` | 6 (회원가입 L108, 포트폴리오/워치리스트 생성) | — | ✅ 생성 엔드포인트 201 일관 |
| `serverless/views_admin.py` | 1 (L625 카테고리 생성) + 204(L746 삭제) | — | ✅ 양호 |
| `rag_analysis/views.py` | 3 (L62, L139, L295) + 204(L101, L164) | — | ✅ 양호 |
| `news/api/views.py` | 0 (읽기 전용 ViewSet) | — | N/A |

**결론**: 생성 시 201 사용이 앱별로 갈린다. users/rag_analysis/serverless_admin은 201 준수, **serverless/views.py는 트리거·생성 작업을 대부분 200으로 반환**(47+건). 단, 비동기 트리거는 의미상 202(Accepted)가 더 적합한데 `sec_pipeline`만 202를 사용(L49).

### 에러 상태 코드 사용 폭

| 상태 코드 | 사용 앱 | 비고 |
|-----------|---------|------|
| 400 | 전 앱 | 가장 보편 |
| 401 | users, rag_analysis, validation, serverless | `raise NotAuthenticated` 또는 직접 401 |
| 403 | serverless (PermissionDenied 7건) | 권한 분기 |
| 404 | 전 앱 | `raise NotFound` 또는 직접 404 |
| 422 | **validation/api** (L85 not_in_universe) | 비즈니스 상태 정상화(PR-#14) ⭐ |
| 429 | **portfolio/api**(6), serverless(1), news, stocks(L1025) | LLM 예산/throttle |
| 502 | **portfolio/api**(6) | LLM 게이트웨이 실패 ⭐ |
| 503 | chain_sight(2), stocks_exchange(3), stocks_search(1) | 외부 서비스 불가 |

**모범 사례**: `portfolio/api/views.py`는 429(예산 초과)·502(LLM 호출 실패)·500(예상외)을 분리해 에러 타입을 명확히 구분. `validation/api`는 422로 비즈니스 상태를 정상화.

### status 모듈 vs 하드코딩

| 방식 | 현황 |
|------|------|
| `status.HTTP_*` 상수 | 약 95% (대다수 파일) |
| 하드코딩 숫자(`status=200`, `status=404` 등) | 🟢 2개 파일: `iron_trading/views.py`(L36/41/45/50), `sec_pipeline/views.py`(L49/53/55) |

**결론**: 상수 사용은 대체로 정착. iron_trading·sec_pipeline 2개 파일만 정수 하드코딩.

---

## 에러 응답 형식

### 에러 키 분포

| 키 | 의미 | 주 사용처 | 건수(대략) |
|----|------|-----------|-----------|
| `{'error': ...}` | 에러 메시지(직반환) | serverless_admin(26), stocks 전반, chain_sight(9), validation(8) | **최다** |
| `{'detail': ...}` | DRF `raise` 자동 생성(정책 표준) | users, rag_analysis, serverless(raise 경로) | raise 시 자동 |
| `{'message': ...}` | 성공/진행 메시지(에러 아님) | serverless(22), market_pulse(progress) | — |
| `{code, message}` | error_body() 헬퍼 | iron_trading | 3 |

### 에러 반환 방식: raise vs return

| 방식 | 결과 | 사용처 |
|------|------|--------|
| `raise NotFound/ValidationError/PermissionDenied` | ✅ EXCEPTION_HANDLER → `{detail, code, status_code}` 표준 변환 | serverless(28), users(23), rag_analysis(12), news/api(10) |
| 도메인 `APIException`(CacheError 등) | ✅ 표준 변환 + 도메인 code 보존 | rag_analysis, serverless |
| `return Response({'error': ...}, status=)` | ❌ 표준 변환 우회 → `{error}` 평면 그대로 노출 | stocks 전반, chain_sight(9), validation(10), serverless_admin(26), market_pulse(10) |

### 핵심 문제 (F3)

- **표준 에러 envelope를 받는 클라이언트와 `{error}` 직반환을 받는 클라이언트가 공존**. 같은 백엔드에서 어떤 에러는 `{detail, code, status_code}`, 어떤 에러는 `{error: "..."}` → FE가 양쪽을 모두 처리해야 함.
- 특히 `chain_sight/api`(raise 0, return 9), `validation/api`(raise 0, return 10), `serverless_admin`(raise 0, return 26), `stocks/views_screener`(raise 0)는 **DRF 예외를 전혀 쓰지 않아** EXCEPTION_HANDLER 표준화 혜택을 받지 못한다.
- **SSE 예외**: `rag_analysis/views.py`의 `PIPELINE_ERROR`(L579-584)·`STREAM_ERROR`(L592-594)는 HTTP 200 + 이벤트 페이로드 내부 에러. 정책상 명시적 제외 대상(정상).

---

## 페이지네이션 현황

### DRF 페이지네이션 클래스 사용

| 방식 | 건수 | 위치 |
|------|------|------|
| `PageNumberPagination`(DRF 표준) | **소수** | `stocks/views.py` StockListAPIView (StockListPagination, page_size=50/max=200), `news/api` ViewSet list/retrieve(NewsArticlePagination) |
| Django `Paginator`(수동) | 일부 | `users/views.py`(Watchlist 2개), `rag_analysis`(UsageHistoryView L762), `serverless`(execute_preset/advanced_screener 수동 page/page_size) |
| 하드코딩 슬라이싱 `[:N]` | 다수 | indicators `[:50]`, mvp `[:20]`, eod `[:50]`/`[:7]`, serverless `[:50]`/`[:10]`, stocks `[:20]`/`[:5]` |
| 무제한 반환(`.all()`/`.filter()` 통째) | 🔴 다수 | 아래 표 |

### 페이지네이션 없이 통째 반환하는 위험 엔드포인트

| 엔드포인트 | 위치 | 위험 |
|-----------|------|------|
| `screener_presets_api` GET | `serverless/views.py:937,954,956` | `.all()+distinct()` 전체 직렬화 (캐시로 일부 완화) |
| `screener_alerts_api` GET | `serverless/views.py:1255` | 사용자 알림 무제한 |
| `market_breadth_history` GET | `serverless/views.py:695` | 히스토리 전체(캐시 있음) |
| `Watchlist*` 외 목록 | `users/views.py` Users.get(L92), UserFavorites(L195), Portfolio(L269), UserInterest(L1045) | 페이지네이션 없음 |
| `SeedListView` | `chain_sight/api/views.py:371` | 전체 시드 배열 |
| `DataBasketListCreateView`, `AnalysisSessionListCreateView`, `SessionMessagesView` | `rag_analysis/views.py:50,427,489` | 목록 통째 반환 |
| `PresetListView` | `validation/api/views.py:534` | 활성 프리셋 전체 |

### 핵심 문제 (F5)

- **DRF `pagination_class`를 ViewSet 단위로 표준 적용한 곳은 stocks StockList + news ViewSet 2곳뿐**. 나머지는 수동 Paginator·하드코딩 슬라이싱·무제한 반환이 혼재.
- 정책 §2.1은 페이지네이션 목록을 `{count, next, previous, results}`로 규정했으나, 실제 목록 응답은 `{count, items}`, `{count, results}`, `{count, presets}`, raw 배열 등 제각각.
- 데이터 증가 시 메모리/지연 위험(특히 serverless screener_presets/alerts, users 목록, chain_sight seed).

---

## 권고사항

우선순위 순. 모두 후속 작업 제안이며 본 감사에서는 수정하지 않음.

### P0 — 폐기 envelope 제거 (정책 직접 위반)

1. **`{success, data, meta}` envelope 17건 평탄화** (F1)
   - 대상: `stocks/views_fundamentals.py`(5), `stocks/views_exchange.py`(5), `stocks/views_screener.py`(7)
   - `Response({"success": True, "data": X, "meta": M})` → `Response(X)` 또는 메타는 응답 헤더(`X-Request-Id` 등)로 분리(정책 §2.1).
   - **FE 동시 수정 필수**: `screenerService.ts` 등에서 `.data.data` → `.data`. (정책 §6.3 미완 항목)
   - 검증: stocks 앱 내 모든 엔드포인트가 동일 스키마(평탄)로 수렴하는지 계약 테스트.

### P1 — 에러 응답 표준 수렴 (F3)

2. **`return Response({'error': ...})` 직반환을 `raise` 경로로 전환**
   - 최우선: `chain_sight/api`(9), `validation/api`(10), `serverless_admin`(26), `stocks/views_screener` — raise를 전혀 안 쓰는 파일.
   - `return Response({"error": msg}, status=404)` → `raise NotFound(msg)` → EXCEPTION_HANDLER가 `{detail, code, status_code}`로 통일.
   - 이렇게 하면 `{error}` vs `{detail}` 이중 형식 소멸.

3. **`users/views.py` 응답 키 정리** (F2 최악 사례)
   - 성공 키 `ok`/`message`/커스텀 dict 36건 정돈, 에러 키 `error`/`detail`/`message` 혼용 해소.

### P2 — 상태 코드/페이지네이션 표준화

4. **생성/트리거 상태 코드 정상화** (F4)
   - `serverless/views.py` 생성 응답 201, 비동기 트리거는 202(Accepted)로 통일(현재 200 기본값 47+건).

5. **DRF `PageNumberPagination` 표준 도입** (F5)
   - 무제한 반환 목록(serverless screener_presets/alerts, users 목록, chain_sight seed, rag_analysis basket/session)부터 `pagination_class` 적용.
   - 응답 형태를 정책 §2.1 `{count, next, previous, results}`로 통일.

6. **`status.HTTP_*` 상수 통일** (F6)
   - `iron_trading/views.py`, `sec_pipeline/views.py`의 하드코딩 숫자를 상수로 교체.

### 정책 문서 갱신 제안

7. `docs/features/api_envelope/policy.md`의 "적용은 ViewSet 단위(완료)" 표현이 실제(클래스 사용 2곳)와 불일치 → **페이지네이션 클러스터 미완**으로 상태 정정 필요.

---

## 부록: 감사 범위

- **분석 파일**: 27개 `views*.py` (빈 스켈레톤 5개 포함)
- **총 라인**: 14,411줄
- **방법**: 파일 그룹 5분할 병렬 정독 + 핵심 발견(envelope 잔존) 직접 재확인(`views_fundamentals.py:92`, `views_screener.py:98`)
- **정책 예외(감사 제외 정당)**: Market Pulse v2 cards `_envelope`(별도 v2 contract), SSE 스트림 이벤트 페이로드(`PIPELINE_ERROR`/`STREAM_ERROR`), `config/views.py`(순수 Django JsonResponse), `portfolio/views.py`(legacy 제거 잔재)
