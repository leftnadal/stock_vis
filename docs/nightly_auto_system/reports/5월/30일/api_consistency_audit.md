# API 응답 일관성 감사 보고서

- **감사 일자**: 2026-05-30
- **감사 방식**: 읽기 전용 정적 분석 (소스 코드 수정 없음). 병렬 분석 에이전트 3개가 실제 `views.py` 전수 Read.
- **감사 범위**: REST 뷰 구현이 실재하는 10개 앱 (graph_analysis는 휴면 스텁, metrics는 REST 뷰 없음 — 분석 제외)

---

## ⚠️ 사전 정정: 파일 경로 (지시서와 실제 구조 불일치)

지시서의 `apps/<app>/views.py` 경로는 **현재 코드베이스에 존재하지 않습니다.** 모노레포 마이그레이션(integrations/ 네임스페이스 이동 진행 중)으로 뷰가 아래처럼 분산되어 있습니다.

| 지시서 경로 | 실제 경로 | 비고 |
|---|---|---|
| `apps/stocks/views.py` | `packages/shared/stocks/views.py` (1126줄) | 실 구현 |
| `apps/users/views.py` | `packages/shared/users/views.py` (1172줄) | 실 구현 |
| `apps/macro/views.py` | `macro/views.py` (412줄) | 실 구현 |
| `apps/news/views.py` | `news/views.py` = **빈 스텁**, 실 구현은 `news/api/views.py` (2208줄) | ViewSet |
| `apps/chainsight/views.py` | `chainsight/views.py` = **빈 스텁**, 실 구현은 `chainsight/api/views.py` (813줄) | APIView 8개 |
| `apps/validation/views.py` | `validation/views.py` = **빈 스텁**, 실 구현은 `validation/api/views.py` (571줄) | APIView 6개 |
| `apps/rag_analysis/views.py` | `rag_analysis/views.py` | 실 구현 |
| `apps/thesis/views.py` | `thesis/views/{thesis_views,conversation_views,monitoring_views}.py` (3분할) | APIView+ViewSet |
| `apps/portfolio_coach/views.py` | 독립 앱 없음. 코치 API는 `portfolio/api/views.py` (E1~E6) | 함수형 |
| `apps/serverless/views.py` | `serverless/views.py` (2927줄) | 함수형 |
| `apps/metrics/views.py` | `packages/shared/metrics/` — **REST 뷰 0건** (CLAUDE.md "(내부 서비스)" 일치) | 분석 제외 |
| `apps/analysis/views.py` | **존재하지 않음** (코드베이스에 `analysis` 앱 없음) | — |
| `apps/graph_analysis/views.py` | `services/_dormant/graph_analysis/views.py` = 휴면 스텁(본문 없음, 1~4줄) | 분석 제외 |

> ⚠️ 데이터 무결성 주의: 감사 중 Desktop repo가 **iCloud dataless 상태로 축출(EPERM)**되는 현상이 관측됨(메모리 `troubleshoot_icloud_desktop_sync_off` 참조). 본 보고서는 축출 이전에 3개 에이전트가 전수 Read로 확보한 검증 데이터 기준. 모든 `file:line`은 위 표의 실제 경로 기준.

---

## 요약

| 차원 | 종합 판정 | 핵심 |
|---|---|---|
| **응답 래핑** | ❌ 전사 표준 없음 | `{success, data}` 패턴은 **전 앱 0건**. 대신 엔드포인트마다 ad-hoc 키 dict / 벌거벗은 리스트 / serializer 직접 반환 혼재 |
| **HTTP 상태 코드** | ⚠️ 부분 양호 | 하드코딩 숫자(`status=400`)는 **전 앱 0건** (모두 `status.HTTP_*` 상수). 그러나 ①201/204 적용 불일치 ②"데이터 없음"을 200/404/422로 제각각 ③정상 응답 status 생략 여부 앱 간 상반 |
| **에러 형식** | ❌ 5종 혼용 | `{'error': str}` / `{'error': {code,message,details}}` / `{'detail'}`(DRF) / `serializer.errors` / `{'message'}` 가 앱 내부에서도 혼용. rag_analysis만 DRF 예외로 통일 |
| **페이지네이션** | ❌ 표준 거의 없음 | DRF `pagination_class` 정식 사용은 `StockListAPIView`·`NewsViewSet` 2건뿐. 나머지는 수동 `Paginator` / `[:limit]` 슬라이스 / 무제한 전량 반환 혼재 |

**긍정 측면**: ① 전 앱이 `status.HTTP_*` 모듈 상수 사용(하드코딩 0건) ② `{success, data}` 류 군더더기 이중 래핑 없음 ③ `portfolio_coach`는 예외 타입별 상태코드 차등(429/502/500)으로 가장 정교 ④ `rag_analysis`는 에러를 DRF 예외로 100% 통일.

**가장 시급한 실증 결함 (추측 아님)**
1. **검색 응답 키 오타** — `stocks` 빈 검색어 분기 `"result"`(단수, `packages/shared/stocks/views.py:205`) vs 정상 분기 `"results"`(복수, `:214, :233`). 프론트 파싱 깨질 수 있음.
2. **`limit` 상한 미검증** — `stocks` 재무제표 `int(request.GET.get("limit", 5))`(`packages/shared/stocks/views.py:686, 767, 847`) 상한 없음 → `?limit=99999` 과대 직렬화 가능.
3. **`stock_news` 무제한 반환** — `news/api/views.py:110-119` 페이지네이션·cap 모두 없이 전량 직렬화.
4. **serverless 인증 데코레이터 모순** — `@authentication_classes([])`(인증 비활성) + `@permission_classes([IsAdminUser])`(관리자 요구) 동시 적용으로 사실상 항상 거부(`serverless/views.py:392-394`).
5. **동일 의미 에러의 상태코드 분기** — `validation` `LeaderComparisonView` 내부에서 insufficient_peers는 200(`validation/api/views.py:337`), no_data는 404(`:358`); `not_in_universe`는 422(`:74`).

---

## 앱별 응답 패턴 매트릭스

| 앱 | 뷰 타입 | 성공 응답 래핑 | 에러 키 | status 상수 | 정상 status 명시 | 페이지네이션 |
|---|---|---|---|---|---|---|
| stocks | APIView + Generic 1 | 엔드포인트별 4종(`{symbol,tab,data}` 등) | `{error:str}` + `{error:{code,...}}` + `.to_response()` | ✅ 100% | 거의 명시 | DRF 1건(StockList) + 수동 slice/무상한 |
| users | APIView | 5종(`serializer.data`/`{message}`/`{results,pagination}`/`{added,...}`/`{portfolios,summary}`) | DRF`{detail}` + `serializer.errors` + `{error}` + `{message}` (4종) | ✅ 100% | 대부분 생략 | 수동 Paginator 2건 + 다수 무제한 |
| macro | APIView | 직접 반환(일관) + sync `{status,message}` | `{error:str}` 단일 | ✅ 100% | 전부 생략 | 목록 없음(N/A) |
| news | ViewSet(ReadOnly) | dict 봉투 + 벌거벗은 리스트 혼재 | `{error}` + DRF`ValidationError` + `{status,message}` | ✅ 100% | 대부분 생략 | DRF 선언(list만) + 액션은 수동/무제한 |
| chainsight | APIView ×8 | 도메인 dict(`{center,nodes,edges,meta}` 등) | `{error}` 통일(trace만 예외) | ✅ 100% | 대부분 생략 | 수동 page 1건(SignalFeed) + limit cap |
| validation | APIView ×6 | `{symbol,...}` 평면 dict(에러도 동일 평면) | `{error}`(코드/메시지 혼용) + `{message}` | ✅ 100% | POST도 생략(200) | 없음(전량) + `[:50]` 1건 |
| rag_analysis | APIView | `serializer.data` 직접 + 커스텀 dict 일부 | **DRF 예외 100%**(`{detail}`/`{필드}`) | ✅ 100% | 200 생략(정상) | 수동 Paginator 1건 + 나머지 `.all()` 전량 |
| thesis | **APIView + ViewSet 혼용** | 커스텀 dict 다수 | `{error}` + DRF`ValidationError` 혼용 | ✅ 100% | 대부분 생략 | `[:50]` 슬라이스 캡 / days 캡 |
| portfolio_coach | 함수형 `@api_view` | `serializer.data`(`{output,llm_metadata}`) | `{error}` (+ scope/type) + DRF`{필드}` | ✅ 100% | 명시(200/4xx/5xx) | 목록 없음(N/A) |
| serverless | 함수형 `@api_view` | **엔드포인트별 dict 제각각**(키 이름 불일치) | DRF 예외 + 200 바디에 error/warning 혼입 | ✅ 100% | 대부분 생략 | **3방식 공존**(수동 page/slice/전량) |

> graph_analysis(휴면 스텁), metrics(REST 뷰 없음)는 분석 대상에서 제외.

---

## HTTP 상태 코드 일관성

### 양호 — 전 앱 공통
- **하드코딩 숫자(`status=400`) 0건.** 분석한 10개 앱 전부 `status.HTTP_*` 모듈 상수 사용.
- **`portfolio_coach`가 가장 정교**: 예외 타입별 차등 매핑 — 예산초과 `HTTP_429_TOO_MANY_REQUESTS`(`portfolio/api/views.py:88`), LLM 오류 `HTTP_502_BAD_GATEWAY`(`:94`), 그 외 `HTTP_500_INTERNAL_SERVER_ERROR`(`:100`). 6개 뷰 전부 동일 패턴.
- **`rag_analysis` 생성/삭제 위생 모범**: 201(`rag_analysis/views.py:61, 135, 290, 395`), 204(`:98, 157, 423`).
- **`users` 생성/삭제도 양호**: 201(`packages/shared/users/views.py:108, 303, 669, 774`), 204(`:348, 719, 806, 1169`), 207 Multi-Status(`:580`).

### 불일치 — 201 (생성) 적용
- **생성인데 200으로 반환되는 곳**:
  - `serverless` `generate_thesis`는 테제 생성(`serverless/views.py:1681`)이나 200(`:1693`); `share_preset`도 공유코드 생성(`:1428`)이나 200(`:1437`).
  - `thesis` `ConversationStartView.post`는 대화 생성이나 200(`thesis/views/conversation_views.py:147`).
  - `validation` `PeerPreferenceView.post`는 `update_or_create`이나 `{status:ok}` 200(`validation/api/views.py:496`).
  - `news` 트리거 액션 일괄 200 — `generate_daily_keywords`(`news/api/views.py:654`), `ml_rollback`(`:2098`), `alerts_resolve`(`:2203`).
- **202 ACCEPTED 미사용**: Celery `.delay()` 비동기 트리거도 전부 200(예: `macro/views.py:368-380`의 `already_running`/`started` 모두 200). 비동기 수락 의미의 202 사용처 0건.

### 불일치 — 에러 상태코드 정책 (가장 심각)
"데이터 없음/부족"을 200으로 줄지 4xx로 줄지가 **뷰·분기 단위로 제각각**:
- `validation` `ValidationSummaryView`: not_in_universe → **422**(`validation/api/views.py:74`), no_data → **404**(`:94`).
- `validation` `LeaderComparisonView` (한 메서드 내부 충돌): insufficient_peers → **200**(`:337-341`), no_leader → **200**(`:349`), no_data → **404**(`:358-361`).
- `chainsight` `ChainSightTraceView`: 경로 없음/예외를 `{found:False, error:...}` 형태로 **200**(`chainsight/api/views.py:212, 234`) — 같은 앱 graph/neighbor의 404(`:70, 117`)와 불일치.
- `serverless` `sector_heatmap_api`: 데이터 없을 때 404 아닌 `{sectors:[], message}` **200**(`serverless/views.py:769-774`).

→ 클라이언트가 **HTTP status만으로 성공/실패를 판정할 수 없음.**

### 불일치 — 정상 200 status 인자 명시 여부
- **거의 항상 명시**: `stocks`(예 `packages/shared/stocks/views.py:967`), `portfolio_coach`(`portfolio/api/views.py:104`).
- **거의 항상 생략(묵시적 200)**: `users`(`packages/shared/users/views.py:54, 67, 95, ...`), `macro`(`macro/views.py:41, 66, 97, ...`), `news`·`thesis`·`serverless` 대부분.
- 동작은 정상이나 앱 간 코딩 컨벤션이 상반됨.

---

## 에러 응답 형식

코드베이스 전체에서 **최소 5종**의 에러 표현이 혼용됨:

| 형식 | 사용처 (예시 `file:line`) |
|---|---|
| `{'error': '문자열'}` | `macro`(전건, `macro/views.py:46, 71, ...`), `chainsight`(`chainsight/api/views.py:70, 117, ...`), `portfolio_coach`(`portfolio/api/views.py:74, 87, 93, 99`), `stocks`(`packages/shared/stocks/views.py:243, 360, ...`) |
| `{'error': {code, message, details}}` (구조화) | `stocks` overview/sync(`packages/shared/stocks/views.py:654-662, 1016-1023`) — **같은 `error` 키가 str과 객체 두 타입** |
| `{'detail': ...}` (DRF 예외 기본) | `rag_analysis`(`NotFound`/`PermissionDenied`/`ValidationError` raise), `users` DRF 예외(`packages/shared/users/views.py:100, 121, 508, ...`) |
| `serializer.errors` (`{필드: [...]}`) | `users`(`packages/shared/users/views.py:68, 110, 307, ...`), DRF `is_valid(raise_exception=True)` 다수 |
| `{'message': ...}` | `stocks` 빈 검색(`packages/shared/stocks/views.py:204-208`), `users` 즐겨찾기 중복(`:219, 250`) |

**앱 내부 혼용이 두드러진 곳**
- **`users` (가장 혼란)**: 같은 "not found"가 `raise NotFound`(→`{detail}`, `packages/shared/users/views.py:508`)와 `Response({'error':...}, 404)`(`:558`)로 갈림. 검증 실패도 `serializer.errors`(필드맵)와 `raise ValidationError`(`{detail}`)로 갈려 클라이언트가 **404/400 본문을 최소 3~4분기** 파싱해야 함.
- **`thesis`**: ViewSet `close` 액션 raw `{error}`(`thesis/views/thesis_views.py:77-80, 84-87`) + `is_valid(raise_exception=True)` DRF 예외(`:127, 156`) 공존.
- **`portfolio_coach`**: provider 검증 실패는 `{error}` 400(`portfolio/api/views.py:74`)인데 body 검증 실패는 DRF `{필드}` 400(`:79`) — 같은 400이 두 형식.
- **`serverless`**: DRF 예외 위주이나 **정상 200 바디에 에러를 키로 섞음** — `_get_market_indices`는 개별 실패를 `{...'error': str(e)}` 200(`serverless/views.py:626`), `generate_thesis` 폴백은 `warning` 키 200(`:1711-1713`).

**가장 일관된 곳**
- `rag_analysis`: raw dict 에러 **0건**, 전부 예외 raise → DRF 표준 `{detail}`/`{필드}`로 통일 (10개 중 유일).
- `macro`: `{'error': str}` 단일 (단, 다른 앱의 구조화 에러/DRF `{detail}`과는 앱 간 불일치).
- `chainsight`: `{'error'}` 통일 (trace 1건만 예외).

**부가 — `error` 값의 의미 혼용**: `validation`은 `error` 값에 머신 코드(`'not_in_universe'`, `'no_data'`, `'insufficient_peers'` — `validation/api/views.py:72, 92, 339`)와 사람이 읽는 메시지(`f'Stock {symbol} not found'`, `'로그인이 필요합니다.'` — `:66, 475`)를 섞어, 일관된 에러 코드 체계가 없음.

---

## 페이지네이션 현황

DRF 정식 `pagination_class` 사용은 **단 2건**, 나머지는 수동 또는 무제한.

### 정식 DRF 페이지네이션 (모범)
- `stocks` `StockListAPIView`: `generics.ListAPIView` + `StockListPagination(PageNumberPagination)` page_size 50/max 200, DoS 방어 주석 포함 (`packages/shared/stocks/views.py:92-97, 100`).
- `news` `NewsViewSet`: `NewsArticlePagination(PageNumberPagination)` page 20/max 100 (`news/api/views.py:51-55, 66`) — **단, 기본 list/retrieve에만 적용. 28개+ 커스텀 `@action`은 전부 우회.**

### 수동 페이지네이션 (셰이프 제각각 → 앱 간 불일치)
- `users`: `django.core.paginator.Paginator`로 watchlist 2곳 — `{results, pagination:{count,page,page_size,num_pages,has_next,has_previous}}` (`packages/shared/users/views.py:635-641, 884-888`).
- `rag_analysis` `UsageHistoryView`: 수동 Paginator → `{results, pagination}` (`rag_analysis/views.py:708-738`).
- `chainsight` `SignalFeedView`: 수동 page → `{page, page_size, total_count, has_next, chains}` (`chainsight/api/views.py:632-656`).
- `serverless`: `advanced_screener_api`가 page/page_size + offset + next/previous URL을 손으로 생성(`serverless/views.py:1135-1172`), `execute_preset`도 동일(`:1004-1027`).
- → 페이지 메타 키가 `pagination{...}` vs `total_count/has_next` vs `next/previous` 등 **전부 다름**.

### 무제한/단순 slice (잠재 위험)
- **무제한 전량 반환 (`.all()`/`.filter()` 직반환)**:
  - `users`: `User.objects.all()`(`packages/shared/users/views.py:93`), 즐겨찾기(`:197-201`), 포트폴리오(`:271-273`), 관심사(`:1046, 1060`).
  - `rag_analysis`: DataBasket 목록(`rag_analysis/views.py:50-52`), 세션 목록(`:378-380`), 세션 메시지 `.all()`(`:439-441`).
  - `validation`: 프리셋(`validation/api/views.py:438, 449-465`), 지표(`:200-206`), 리더 비교 전량(`:369-430`) — 집합이 작아 실무 위험은 낮음.
  - `news`: `stock_news` 전량(`news/api/views.py:110-119`) ⚠️, `collection_logs`(`:1380`).
  - `serverless`: `screener_presets_api`(`serverless/views.py:911-918`), `screener_alerts_api`(`:1204-1214`).
- **상한 없는 `[:limit]` (사용자 입력 의존)**:
  - `stocks` 재무제표 `[:limit]` + `limit` 상한 검증 없음 ⚠️ (`packages/shared/stocks/views.py:708, 787, 867`; 파싱 `:686`).
  - `stocks` 차트는 기간 필터만, 개수 상한 없음(`packages/shared/stocks/views.py:456-475`).
- **고정 하드캡 `[:N]` (방어됨)**: `stocks` 검색 `[:20]`(`:223-225`), `thesis` 알림 `[:50]`(`thesis/views/monitoring_views.py:238`), `validation` LLM peer `[:50]`(`validation/api/views.py:568`), `serverless` LLM relations `[:50]`(`serverless/views.py:2524`).
- `macro`: 목록형 엔드포인트 자체가 없음. `days` 1~30 clamp(`macro/views.py:185`)는 입력 검증 모범.

---

## 권고사항

### High (정합성 결함 — 우선 수정 권장)
1. **응답 키 오타 수정** — `stocks` 빈 검색어 분기 `"result"` → `"results"` 통일 (`packages/shared/stocks/views.py:205`). 프론트 파싱 깨짐 가능성 있는 실제 버그.
2. **`limit` 상한 검증 추가** — `stocks` 재무제표/차트의 사용자 입력 `limit`에 상한(예: max 100) 적용 (`packages/shared/stocks/views.py:686, 767, 847`).
3. **`stock_news` 페이지네이션 또는 cap 적용** — 현재 전량 직렬화 (`news/api/views.py:110-119`).
4. **serverless 인증 데코레이터 모순 해소** — `@authentication_classes([])` + `[IsAdminUser]` 동시 적용 검토 (`serverless/views.py:392-394`). 항상 거부되거나 의도와 다른 동작 가능.
5. **에러 상태코드 정책 통일** — "데이터 없음/부족" 계열을 200으로 줄지 4xx로 줄지 단일 규칙 수립. 특히 `validation/api/views.py:337`(200) vs `:358`(404), `chainsight/api/views.py:212`(200) 같은 한 앱 내 충돌부터 정리.

### Medium (표준화 — 점진 적용)
6. **에러 응답 형식 단일 표준 채택** — `rag_analysis`처럼 **DRF 예외(`{detail}`/`{필드}`) 기반으로 통일**하거나, 전사 커스텀 `{error: {code, message}}` 스키마로 통일. 현재 5종 혼용은 프론트 에러 처리 분기를 강제함. 표준 채택 시 `contracts/`에 에러 스키마 명문화 권장.
7. **목록 API 페이지네이션 표준화** — DRF 전역 `DEFAULT_PAGINATION_CLASS` 설정 또는 `StockListAPIView` 패턴을 표준으로 채택. 수동 Paginator 3종(`{results,pagination}` / `total_count/has_next` / `next/previous`)을 단일 셰이프로 수렴.
8. **생성 엔드포인트 201 / 비동기 트리거 202 적용** — `serverless` `generate_thesis`(`:1693`)·`share_preset`(`:1437`), `thesis` `ConversationStartView`(conversation_views:147)에 201; Celery `.delay()` 트리거(`macro/views.py:368-380` 등)에 202 ACCEPTED 고려.
9. **무제한 목록에 상한 부여** — `User.objects.all()`(`packages/shared/users/views.py:93`) 등 관리자/대용량 가능 목록에 페이지네이션 적용.

### Low (컨벤션 정리)
10. **정상 200 status 명시 컨벤션 통일** — 현재 `stocks`/`portfolio_coach`(명시)와 `users`/`macro`/`news`(생략)가 상반. 동작엔 무해하나 가독성·일관성 차원에서 한쪽으로 수렴.
11. **응답 봉투 키 명명 통일** — `count`/`total`/`total_records`, `node_count`/`total_neighbor_count`, `movers`/`presets`/`alerts`/`results` 등 목록 카운트·데이터 키 명명을 컨벤션화. 특히 `serverless`는 엔드포인트별 dict 구조가 제각각이라 정리 효과 큼.
12. **serializer 미경유 raw 서비스 응답 점검** — `macro` VIX/sectors(`macro/views.py:230, 259`), `validation` LLM peer(`validation/api/views.py:564`) 등 외부 서비스 dict를 검증 없이 통과시키는 곳은 스키마 안정성 위해 serializer 경유 검토.

### 후속 (감사 환경)
13. **iCloud dataless 재발 방지** — 감사 중 Desktop repo가 dataless로 축출됨. 메모리 `troubleshoot_icloud_desktop_sync_off` / `project_icloud_sync_off` 참조하여 동기화 OFF 상태 재확인 권장. (소스 자체는 무손상)

---

*본 보고서는 읽기 전용 정적 분석 결과이며 소스 코드를 일절 수정하지 않았습니다. 모든 주장은 위 경로 정정표 기준의 `file:line` 증거를 동반합니다.*
