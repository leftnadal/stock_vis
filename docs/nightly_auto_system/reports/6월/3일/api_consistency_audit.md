# API 응답 일관성 감사 보고서

- 작성일: 2026-06-03 (nightly auto system)
- 감사 범위: 전체 `views*.py` 27개 파일 (migration / `__pycache__` / `node_modules` 제외)
- 분석 방식: 읽기 전용. 모든 `Response(...)` 반환 지점의 래핑·상태코드·에러키·페이지네이션 추출
- 기준 정책: [`docs/features/api_envelope/policy.md`](../../../../features/api_envelope/policy.md) (2026-05-12 수립) 대비 준수 현황 측정
- **코드 수정 없음** — 권고만 제시

---

## 요약

### 핵심 사실: 표준 정책은 이미 존재한다

2026-05-12 감사(`5월/5일/api_consistency_audit.md`)의 결론으로 **응답 표준화 정책이 이미 수립·문서화**되어 있다. 핵심은 두 가지다.

1. **성공 응답**: `{success, data, meta}` 래핑을 **폐기**하고 `serializer.data` / 평탄 dict 직접 반환(DRF 표준)으로 통일.
2. **에러 응답**: `config/exception_handler.py:custom_exception_handler`(전역 등록 완료)가 DRF 예외를 `{detail, code?, errors?, status_code}` 단일 형식으로 변환.

이번 감사의 결론은 **"정책은 맞으나 코드베이스가 절반만 따라왔다"**이다. 정책 수립 후 3주가 지났지만 다음 두 부류의 위반이 광범위하게 잔존한다.

### 발견된 2대 구조적 위반

| # | 위반 | 영향 파일 | 심각도 |
|---|------|----------|--------|
| **V1** | **`{success, data, meta}` 래핑 잔존** — 정책상 폐기 대상인데 3개 파일이 여전히 사용 | `views_screener.py`, `views_fundamentals.py`, `views_exchange.py` | 🔴 높음 |
| **V2** | **에러를 `Response({'error': ...}, status=...)`로 직접 반환** — 전역 exception_handler를 우회하므로 표준 `{detail, code, status_code}`로 변환되지 않음. 클라이언트는 `err.detail`(정책)과 `err.error`(우회) 두 형식을 모두 파싱해야 함 | serverless, news, chain_sight, validation, stocks, market_pulse, fundamentals, exchange, search/eod/mvp, iron_trading | 🔴 매우 높음 |

### 양호한 항목

- **상태코드 상수화**: `iron_trading/views.py` 1개 파일을 제외하면 **전부 `status.HTTP_*` 상수** 사용 (하드코딩 숫자 사실상 없음).
- **에러 핸들러 인프라**: 전역 변환기가 이미 등록되어 있어, 우회 코드를 `raise`로 바꾸기만 하면 표준화가 자동 완성됨.

### 추가 발견 — "에러를 200으로 반환"하는 안티패턴 (3개 지점)

내부 에러/실패 상황인데 HTTP 200 + body에 `error`/`found:False` 키를 넣어 반환하는 곳이 있다. 클라이언트가 실패를 성공으로 인식한다.

- `validation/api/views.py:417, 433, 671` (insufficient_peers / no_leader / LLM parse error)
- `apps/chain_sight/api/views.py:288-292` (`ChainSightTraceView` 예외 시 status 미지정 → 200)
- `services/news/api/views.py:601-604, 1248-1253` (not_found / no_report를 200+`{status, message}`로)

> 단, 정책 §2.3은 "**정상 흐름**의 비즈니스 분기"는 200+`status` 키를 허용한다. 위 3건 중 일부는 그 경계가 모호하므로 케이스별 판단 필요(권고 §6 참조).

---

## 앱별 응답 패턴 매트릭스

범례: 🟢 정책 준수 · 🟡 부분 준수/혼용 · 🔴 정책 위반 · ⚪ 빈 스텁(분석 대상 없음)

| 앱 / 파일 | 성공 래핑 | 에러 키 | 상태코드 | 페이지네이션 | 종합 |
|-----------|----------|---------|----------|-------------|------|
| `serverless/views.py` | 🟢 평탄(리스트키 비표준) | 🟢 `detail`(raise) + 필드dict | 🟡 상수✓ / 201 일부누락 | 🟡 수동 page/limit, 무제한 일부 | 🟡 |
| `serverless/views_admin.py` | 🟢 평탄 | 🔴 `{error}` 직접반환 | 🟢 상수✓ 201/204✓ | 🟡 limit, 무제한(관리자) | 🟡 |
| `news/api/views.py` | 🟡 dict + bare list 혼용 | 🔴 `{error}`+`{detail}`+200`message` 3종 | 🟡 상수✓ / 201 없음 | 🟡 list만 페이지네이션, action 무제한 | 🔴 |
| `news/views.py` | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| `sec_pipeline/views.py` | 🟢 평탄 | 🟡 에러키 없음(200/202+status) | 🔴 **하드코딩 200/202** | 🟢 N/A | 🟡 |
| `graph_analysis/views.py` (_dormant) | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| `users/views.py` | 🔴 직접/ad-hoc/수동봉투/bulk봉투 4종 | 🔴 `detail`/`error`/`message`/serializer.errors 4종 | 🟡 상수✓ / AddFavorite 201누락 | 🟡 수동 Paginator 2, 무제한 5 | 🔴 |
| `stocks/views.py` | 🟡 `_source`/`tab` 메타(준일관) | 🔴 `{error}`문자열 + 중첩`{error:{code}}` + `.to_response()` | 🟡 상수✓ / 207·200/500 비즈니스인코딩 | 🟢 DRF pagination 1 + 슬라이스 | 🔴 |
| `chain_sight/api/views.py` | 🟢 평탄 dict | 🔴 `{error}` 직접반환(9건) | 🟡 상수✓ / **Trace 에러→200** | 🟡 수동 1, 무제한 2~3 | 🔴 |
| `chain_sight/views.py` | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| `rag_analysis/views.py` | 🟢 serializer.data + 평탄 | 🟢 `detail`(raise) + 커스텀예외 | 🟢 상수✓ 201/204✓ | 🟡 수동 Paginator 1, 무제한(SessionMessages) | 🟡 |
| `validation/api/views.py` | 🟢 평탄 | 🔴 `{error}`+`{error,message}` 혼용, **에러→200 3건** | 🟡 상수✓ 422✓ / 201없음 | 🔴 전무, `[:50]` 1건 | 🔴 |
| `validation/views.py` | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| `stocks/views_screener.py` | 🔴 **`{success,data,meta}` 래핑** | 🔴 비대칭(`{error}` 비래핑, serializer.errors=dict) | 🟢 상수✓ | 🔴 전무(limit≤1000 통째) | 🔴 |
| `stocks/views_indicators.py` | 🟢 평탄 | 🟡 `get_object_or_404`→`{detail}` | 🟢 상수✓ | 🔴 전무 | 🟡 |
| `stocks/views_fundamentals.py` | 🔴 **`{success,data,meta}` 래핑** | 🔴 `{error}` 직접반환 | 🟡 상수✓ / 201없음 | 🟡 limit clamp(페이지 아님) | 🔴 |
| `stocks/views_exchange.py` | 🔴 **`{success,data,meta}` 래핑** | 🔴 `{error}` 직접반환 | 🟡 상수✓ / no-data를 503 | 🔴 전무 | 🔴 |
| `market_pulse/views.py` | 🟢 평탄 | 🔴 `{error}` 직접반환 | 🟡 상수✓ / no-data를 404 | 🔴 전무 | 🟡 |
| `portfolio/api/views.py` (coach) | 🟢 serializer.data | 🔴 DRF`detail`(검증) + 커스텀`{error,scope,type}` 혼용 | 🟢 상수✓ 200명시 | 🟢 N/A(단건) | 🟡 |
| `portfolio/views.py` | ⚪ (#65로 전뷰 제거) | ⚪ | ⚪ | ⚪ | ⚪ |
| `stocks/views_search.py` | 🟢 평탄 | 🔴 `{error}` + 예외원문노출 | 🟢 상수✓ | 🟡 `[:10]` 슬라이스 | 🟡 |
| `stocks/views_mvp.py` | 🟡 `data`키 + ad-hoc | 🟡 `get_object_or_404`→`{detail}` | 🟢 상수✓ | 🟡 `[:20]` 슬라이스, Sector 무제한 | 🟡 |
| `stocks/views_eod.py` | 🟢 평탄 | 🔴 `{error}` 직접반환 | 🟢 상수✓ | 🟡 `[:50]`/`[:7]` 슬라이스 | 🟡 |
| `stocks/views_market_movers.py` | 🟢 평탄 | 🔴 `{error}` 직접반환 | 🟢 상수✓ | 🟡 limit 수동 | 🟡 |
| `config/views.py` | 🟢 API root | 🟢 N/A(`message`=정상본문) | 🟢 상수✓ | 🟢 N/A | 🟢 |
| `iron_trading/views.py` | 🟢 평탄(payload) | 🟡 `error_body(code,message)` 구조화(독자형식) | 🔴 **하드코딩 400/404/503/200** | 🟡 service단 limit | 🟡 |
| `metrics/views.py` | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |

> 빈 스텁 7개(`news/views.py`, `_dormant/graph_analysis/views.py`, `chain_sight/views.py`, `validation/views.py`, `metrics/views.py`, `portfolio/views.py`): 실제 라우팅은 각각의 `api/views.py` 또는 `views_*.py`가 담당. `portfolio/views.py`는 Slice 13 #65로 전 뷰가 제거된 호환용 빈 모듈.

---

## HTTP 상태 코드 일관성

### 1. 상수 vs 하드코딩 — 거의 통일 (🟢)

`status.HTTP_*` 상수 사용이 **사실상 전면 정착**. 하드코딩 숫자는 단 한 파일에만 존재한다.

- 🔴 `integrations/iron_trading/views.py:36,41,46,50` — `status=400`, `status=404`, `status=503`, `status=200` 숫자 직접 사용. 유일한 예외.
- 🔴 `services/sec_pipeline/views.py:49,53` — `status=202`, `status=200` 숫자 직접 사용 (`status` 모듈 import조차 안 함).

### 2. 201 CREATED — 적용 불완전 (🟡)

생성 POST에 201을 일관되게 쓰는 곳과 빠뜨리는 곳이 갈린다.

**201 적용 (양호)**:
- `rag_analysis/views.py:63,141,303,448` (DataBasket/AddItem/Session 생성) — 가장 모범적
- `users/views.py:108,303,669,774` (User/Portfolio/Watchlist 생성)
- `serverless/views.py:971,1282,1599` (Preset/Alert/Import)

**201 누락 (생성인데 200)**:
- `users/views.py:227` `AddFavorite.post` — 즐겨찾기 생성인데 암묵 200
- `serverless/views.py:1674` `generate_thesis` — 새 테제 DB 생성인데 `Response(serializer.data)` = 200
- `news/api/views.py:637,2325,2453` — POST 액션 전부 200 (비동기 트리거는 202가 적합)
- `validation/api/views.py:609` `PeerPreferenceView.post` — `update_or_create` 후 200

### 3. "데이터 없음"의 상태코드 — 앱별 제각각 (🟡)

동일 의미("외부 데이터 없음")가 파일마다 다른 코드로 매핑된다.

| 상황 | exchange | fundamentals | market_pulse |
|------|----------|--------------|--------------|
| 데이터 없음 | **503** (`views_exchange.py:61,180`) | **404** (`views_fundamentals.py:82,144`) | **404** (VIX `:234`) |

→ 클라이언트가 "재시도 가능(503)"인지 "리소스 없음(404)"인지 앱별로 다르게 해석하게 됨.

### 4. 비즈니스 결과의 HTTP 상태 인코딩 (🟡)

- `stocks/views.py:1085-1087` `StockSyncAPIView` — 전부 실패=500, 일부성공=200 (부분 실패를 HTTP로 표현)
- `users/views.py:580` `RefreshStockDataView` — 부분 성공 `207 MULTI_STATUS` (코드베이스 유일)

---

## 에러 응답 형식

### 표준 (정책 §2.2)

```json
{ "detail": "Stock not found", "code": "stock_not_found", "errors": {...}, "status_code": 404 }
```

이 형식은 **DRF 예외를 `raise`했을 때만** `custom_exception_handler`가 자동 생성한다. **`Response({...}, status=...)`로 직접 반환하면 핸들러를 거치지 않아 표준화되지 않는다.** 이것이 V2 위반의 메커니즘이다.

### 현황: 4종 형식이 혼재

| 형식 | 발생 경로 | 주요 위치 | 정책 |
|------|----------|----------|------|
| `{detail, code, status_code}` | DRF `raise NotFound/ValidationError` → 핸들러 | rag_analysis, serverless, users(일부), coach(검증) | 🟢 표준 |
| `{error: "문자열"}` | `Response({'error':...}, status=)` 직접 | serverless_admin, chain_sight(9건), market_pulse, exchange, fundamentals, eod, market_movers, search | 🔴 우회 |
| `{error: {code, message, details}}` | 직접(중첩) | `stocks/views.py:653-663,1016-1024` | 🔴 우회(별도 스키마) |
| `{error: <code>, message: <한글>}` | 직접(이중의미) | `validation/api/views.py:82-86,419-423` | 🔴 우회(`error`가 코드/문장 이중) |
| `error_body(code, message, retry_after)` | 헬퍼함수 | `iron_trading/views.py:36,41` | 🟡 독자 구조화 |
| `serializer.errors` 직접 | `Response(serializer.errors, 400)` | `users/views.py` 9곳, `views_screener.py:70` | 🔴 우회(필드dict 노출) |

### 같은 의미 404가 4가지 키로 갈리는 사례

- `views_indicators.py` / `views_mvp.py` → `get_object_or_404` → DRF `{detail: "Not found."}` → 핸들러 통과 → 표준
- `views_search.py:118` / `views_eod.py:48` → `{error: ...}` 직접 → 우회
- `users/views.py:215` → `raise NotFound` → 표준
- `chain_sight/api/views.py:73` → `{error: ...}` 직접 → 우회

→ **동일 코드베이스의 404 응답 body가 `{detail}` / `{error}` 두 형태로 공존**. 프론트는 단일 에러 핸들러를 만들 수 없다.

### 부가 이슈

- **예외 원문 노출**: `views_search.py:85,144` `f"서버 오류: {str(e)}"` — 내부 예외 문자열을 클라이언트에 그대로 반환(정보 노출).
- **에러를 200+`warning`으로 위장**: `serverless/views.py:1776-1781` `generate_thesis` 폴백 — 실패를 200 성공 응답에 `warning` 키로 끼워넣음.
- **에러 메시지 언어 혼용**: stocks 계열은 한국어("...찾을 수 없습니다"), macro/coach 계열은 영어("Internal server error"). 정책 §1은 "응답 본체는 영문 키, 한글은 /i18n"을 지향하나 메시지 언어가 통일 안 됨.
- **`message` 키의 이중 용도**: 성공 통지(`"Preset created"`)와 에러 표현(`users/views.py:219,251` AddFavorite 400 에러)에 동시 사용 → 성공/실패 구분 불가.

---

## 페이지네이션 현황

### 전역 설정: DEFAULT_PAGINATION_CLASS 미설정

`config/settings.py`의 `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS` / `PAGE_SIZE`가 **없다**. 즉 페이지네이션은 전적으로 ViewSet/뷰 단위 옵트인이며, 코드베이스 대다수가 `APIView`/`@api_view` 기반이라 **선언적 페이지네이션이 구조적으로 적용 불가능**하다.

### DRF 표준 페이지네이션 적용 (🟢) — 단 2곳

- `stocks/views.py:92-108` `StockListAPIView` → `StockListPagination(page_size=50, max=200)` (주석: "S&P 6000+ 종목 일괄 반환 차단, DoS 표면 축소")
- `news/api/views.py:73` `NewsViewSet.pagination_class = NewsArticlePagination(page_size=20, max=100)` — 단 기본 `list`/`retrieve`에만 작동, 커스텀 `@action`은 전부 우회

### 수동 페이지네이션 (🟡) — 스키마 불일치

`Paginator` 또는 page/page_size 직접 구현. **응답 메타 스키마가 구현마다 다름**:

- 평면형 `{page, page_size, total_count, has_next}`: `serverless/views.py:1183`(advanced_screener), `chain_sight/api/views.py:758`(SignalFeed)
- 중첩형 `{results, pagination: {current_page, total_pages, ...}}`: `users/views.py:643,892`(Watchlist), `rag_analysis/views.py:805`(UsageHistory)
- DRF 표준형 `{count, next, previous, results}`과 **셋 다 불일치**

### limit 슬라이스만 (🟡) — 페이지네이션 아님

`[:N]` 하드 슬라이스로 상한만 둠. `next`/`offset` 없어 N+1번째 데이터 접근 불가:
- `views_mvp.py:41` `[:20]`, `views_eod.py:82` `[:50]`/`:125` `[:7]`, `views_search.py:57` `[:10]`
- `serverless/views.py:1381,1853,2635,2275`, `validation/api/views.py:688` `[:50]`(하드코딩)
- `views_fundamentals.py` limit 1~40 클램프(2페이지 접근 불가)

### 무제한 전건 반환 (🔴) — 잠재 부하 지점

페이지네이션·상한 없이 `.all()`/`.filter()`/`for` 전량 반환. 데이터 누적 시 응답 폭주·N+1 위험.

| 위치 | 내용 | 위험도 |
|------|------|--------|
| `serverless/views.py:937` `screener_presets_api` GET | 공개(AllowAny) 프리셋 전건, 상한 없음 | 🔴 공개+무제한 |
| `serverless/views.py:1958` `etf_collection_status` | ETFProfile 전건 + **profile마다 count() N+1** (`:1969`) | 🔴 N+1 동반 |
| `serverless/views.py:2956,3013` | regulatory/patent 관계 전건 | 🟡 |
| `news/api/views.py:1452,2162,1940,2035` | collection_logs/task_timeline/ml_trend/llm_usage — 시간윈도우 필터만, 행 상한 없음 | 🔴 모니터링 누적 폭주 |
| `rag_analysis/views.py:496` `SessionMessagesView` | 세션 메시지 전량(무제한) | 🔴 대화 누적 최상위 위험 |
| `rag_analysis/views.py:429` `AnalysisSessionListCreateView` | 세션+메시지 prefetch 전량 | 🟡 |
| `users/views.py:93` `Users.get` | `User.objects.all()` 전건(관리자) | 🟡 |
| `validation/api/views.py:519` comparisons / `views_indicators.py:436` | 입력 길이만큼 전량, 상한 없음 | 🟡 |
| `views_screener.py` 전 뷰 | limit≤1000 통째 반환 | 🟡 |
| `views_mvp.py:221` `SectorListView` / `views_exchange.py:283` SectorPerformance | 섹터 전건(건수 작아 실질 위험 낮음) | 🟢 |

---

## 권고사항

> 읽기 전용 감사이므로 미적용. 우선순위순.

### P1 — V2 위반 제거: 에러를 `raise`로 전환 (최대 효과)

전역 `custom_exception_handler`가 이미 있으므로, `Response({'error': ...}, status=4xx)` 직접 반환을 DRF 예외 `raise`로 바꾸기만 하면 표준 `{detail, code, status_code}`가 **자동 완성**된다. 도메인 코드가 필요하면 `rag_analysis/exceptions.py`·`serverless/exceptions.py` 패턴(`APIException` + `default_code`)을 따른다.

- 대상: serverless_admin, chain_sight/api(9건), market_pulse, exchange, fundamentals, eod, market_movers, search, validation, stocks
- 효과: 404 응답 body의 `{detail}`/`{error}` 이원화 해소 → 프론트 단일 에러 핸들러 가능
- 부수: `views_search.py:85,144`의 `str(e)` 노출 제거(`raise APIException`로 일반화)

### P2 — V1 위반 제거: `{success, data, meta}` 래핑 폐기

정책상 이미 폐기 결정된 래핑이 3개 파일에 잔존. `serializer.data`/평탄 dict 직접 반환으로 전환하고, 메타는 응답 헤더(`X-Request-Id`, `X-Cache`)로 분리(정책 §2.1).

- 대상: `views_screener.py`, `views_fundamentals.py`, `views_exchange.py`
- 주의: 프론트 `screenerService.ts`·`ragService.ts`의 `response.data.data` 접근부 동시 수정 필요(정책 "적용 범위"에 명시됨)

### P3 — "에러를 200으로 반환" 정상화

- 명백한 내부 에러: `chain_sight/api/views.py:288`(예외→200), `validation/api/views.py:671`(LLM parse error) → 적절한 4xx/5xx로
- 비즈니스 분기(정책 §2.3 허용): `validation:417,433`(insufficient_peers/no_leader), `news:601`(not_found) → 200 유지하되 `{status, data:null, reason}` 형식으로 표준화할지 케이스별 결정

### P4 — 무제한 목록에 상한/페이지네이션 부여

- 즉시: `serverless:937`(공개 프리셋), `rag_analysis:496`(세션 메시지), `news` 모니터링 4개 액션 → limit 캡 또는 페이지네이션
- `serverless:1958` `etf_collection_status`의 N+1 → `annotate(Count(...))`로 단일 쿼리화
- 중기: `REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS` 전역 설정 검토(단, `APIView` 다수라 효과 제한적 → ListAPIView 전환과 병행)

### P5 — 상태코드 마감

- `iron_trading/views.py`·`sec_pipeline/views.py`의 하드코딩 숫자 → `status.HTTP_*` 상수
- 생성 POST에 201 일괄 적용(`AddFavorite`, `generate_thesis`, validation `PeerPreference`), 비동기 트리거(`news` POST 3건)는 202 검토
- "데이터 없음" 상태코드를 앱 간 통일(404 권장, 일시적 외부 장애만 503)

### P6 — 수동 페이지네이션 스키마 통일

평면형/중첩형으로 갈린 수동 페이지네이션을 DRF 표준 `{count, next, previous, results}`(정책 §2.1)로 정렬.

---

## 부록: 분석 통계

- 분석 파일: 27개 (실 구현 20개 + 빈 스텁 7개)
- 누적 `Response(...)` 반환: 약 280건
- `{success, data}` 래핑 사용 파일: **3개** (정책 위반, 폐기 대상)
- 에러 직접반환(`{error}` 등 핸들러 우회): **13개 파일 이상**
- DRF 표준 페이지네이션 적용: **2개 뷰** / 무제한 전건 반환: **10개 지점 이상**
- 하드코딩 상태코드: **2개 파일** (iron_trading, sec_pipeline)
- "에러를 200으로 반환": **3개 파일 / 6개 지점**

### 이전 감사 대비

본 감사는 2026-05-12 정책 수립의 후속 점검이다. 정책은 마이그레이션 범위를 "BE 약 154건 + DRF raise 41건"으로 추정했으나, **3주 경과 시점에도 V1(래핑 3파일)·V2(에러 우회 13파일+)가 잔존**한다. 정책 자체는 타당하므로 신규 작업이 아닌 **잔존 마이그레이션 완수**가 핵심 과제다.
