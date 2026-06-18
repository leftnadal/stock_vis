# API 응답 일관성 감사 보고서

- **감사일**: 2026-06-18
- **대상**: `/Users/byeongjinjeong/Desktop/stock_vis` 전체 `views*.py` (마이그레이션/캐시 제외)
- **모드**: 읽기 전용 (코드 수정 없음)
- **대상 파일**: 27개 (실 분석 22개 + 빈 스텁 5개), 총 14,411줄

---

## 요약

### 한눈에 보는 결론

| 차원 | 상태 | 핵심 발견 |
|------|------|----------|
| **응답 래핑** | 🔴 강한 혼재 | `{'success':True,'data':...}` 표준 envelope **전체 0건**. 대신 **3종 봉투 변종**이 앱/파일 경계로 공존 |
| **HTTP 상태코드** | 🟡 대체로 양호 | `status` 모듈 사용은 일관(stocks/apps/services). **iron_trading·sec_pipeline만 정수 하드코딩**. POST 생성 시 201 거의 미사용 |
| **에러 형식** | 🔴 강한 혼재 | `{'error'}` / `{'detail'}` / `{'message'}` / 중첩 `{'error':{code,...}}` / `serializer.errors` **최대 5종 공존**. 에러를 200으로 반환하는 곳 다수 |
| **페이지네이션** | 🔴 전역 부채 | DRF `pagination_class` **전체 0건**. 전부 수동 `Paginator`/`limit` 슬라이스/무제한 전건 반환 |

### 가장 중요한 4가지 시스템 리스크

1. **표준 응답 봉투 부재** — 22개 분석 파일 어디에도 공통 envelope가 없어, 프론트엔드가 엔드포인트마다 응답 스키마를 개별 파싱해야 함.
2. **에러를 HTTP 200으로 반환** — `validation/api/views.py`(3건), `chain_sight/api/views.py`(trace 예외) 등에서 에러 페이로드를 200으로 반환 → 클라이언트가 상태코드로 실패를 감지 불가.
3. **앱별 에러 컨벤션 정반대** — `chain_sight`(수동 `{'error'}`) vs `rag_analysis`(DRF 예외 `{'detail'}`)가 전사적으로 충돌.
4. **무제한 전건 반환 다수** — `screener_presets_api`(전체 테이블 스캔), `stock_news`, `collection_logs` 등 row 상한 없는 목록 반환이 DoS/성능 표면.

### 부가 리스크

- **내부 예외 메시지 노출**: `str(e)`를 응답 본문에 직접 싣는 곳 다수 (`stocks/views.py`, `chain_sight`, `rag_analysis`, `search`). 정보 노출 우려.
- **모범 사례 존재**: `portfolio/api/views.py`(6뷰 완전 동형 + 4단 에러 분기 + 스택트레이스 비노출)가 표준화의 레퍼런스로 적합.

---

## 앱별 응답 패턴 매트릭스

> 봉투 범례: `{success,data}` = 표준 envelope · `flat` = 도메인 키 평탄 dict · `serializer.data` = 직접 반환 · `자체봉투` = 비표준 고유 봉투

| 앱 / 파일 | 줄수 | 응답 래핑 | 에러 키 | status 모듈 | 페이지네이션 | 일관성 |
|-----------|------|-----------|---------|:-----------:|--------------|:------:|
| `serverless/views.py` | 3045 | flat (도메인키) | DRF 예외 raise | ✅ | 수동 page/offset 2건 + limit 슬라이스 | 🟡 |
| `serverless/views_admin.py` | 792 | flat / 단일키 래핑 혼재 | `{'error'}` | ✅ | 없음 (limit≤200) | 🟡 |
| `news/api/views.py` | 2493 | flat + top-level array 혼재 | `{'error'}` + ValidationError | ✅ | 클래스 정의됐으나 액션 미적용 | 🔴 |
| `users/views.py` | 1171 | serializer.data / ad-hoc키 / `{message}` | 4종 혼재 | ✅ | Django Paginator 수동 (7중 2) | 🔴 |
| `stocks/views.py` | 1125 | flat (`{symbol,tab,data}`) | 5종 혼재 (중첩 error 포함) | ✅ | DRF 1건(StockList)만 | 🔴 |
| `chain_sight/api/views.py` | 934 | 직접 (뷰마다 상이) | `{'error'}` 단일 | ✅ (1건 누락) | 수동 1건 + truncation | 🟡 |
| `rag_analysis/views.py` | 857 | serializer.data + dict 혼재 | DRF/커스텀 예외 `{'detail'}` | ✅ | Django Paginator 1건 | 🟡 |
| `validation/api/views.py` | 692 | flat / `{status:"ok"}` 혼재 | `{'error'}` (의미 이중성) | ✅ | 없음 (`[:50]` 1건) | 🔴 |
| `market_pulse/views.py` | 416 | serializer.data / raw dict | `{'error'}` 단일 | ✅ | 해당없음 (단일객체) | 🟢 |
| `portfolio/api/views.py` | 384 | serializer.data (6뷰 동형) | `{'error'}` + 부가필드 | ✅ | 해당없음 (POST 분석) | 🟢 |
| `stocks/views_screener.py` | 538 | **`{success,data,meta}`** | `{'error'}` | ✅ | 없음 (limit 1~1000) | 🟢 |
| `stocks/views_indicators.py` | 436 | 직접 (계산 dict) | `{'error'}` + `{'detail'}` 혼재 | ✅ | 없음 | 🟡 |
| `stocks/views_fundamentals.py` | 316 | **`{success,data,meta}`** | `{'error'}` | ✅ | 없음 (limit 1~40) | 🟢 |
| `stocks/views_exchange.py` | 296 | **`{success,data,meta}`** | `{'error'}` | ✅ | 없음 (≤100) | 🟢 |
| `stocks/views_search.py` | 237 | 자체봉투 `{count,results}` | `{'error'}` / `{valid,error}` | ✅ | 없음 (`[:10]`) | 🟡 |
| `stocks/views_mvp.py` | 227 | 자체봉투 `{mode,count,data}` | 없음 (bare except) | ⚠️ get_object만 | 없음 (`[:20]`) | 🟡 |
| `stocks/views_eod.py` | 144 | 직접 (json_data 원본) | `{'error'}` | ✅ | 없음 (`[:50]`/`[:7]`) | 🟡 |
| `stocks/views_market_movers.py` | 72 | serializer.data 직접 | `{'error'}` | ✅ | 없음 (1~20) | 🟡 |
| `config/views.py` | 104 | JsonResponse (DRF 아님) | body 필드 | ❌ 미지정 | 해당없음 | ⚠️ |
| `iron_trading/views.py` | 50 | 직접 | `error_body()` 헬퍼 | ❌ 정수 하드코딩 | 없음 | ⚠️ |
| `sec_pipeline/views.py` | 55 | 직접 (result) | result.status 필드 | ❌ 정수 하드코딩 | 해당없음 | ⚠️ |
| `metrics/views.py` 외 4개 | 1~3 | **빈 스텁** | — | — | — | — |

> 빈 스텁(뷰 0건): `metrics/views.py`, `_dormant/graph_analysis/views.py`, `news/views.py`, `chain_sight/views.py`, `validation/views.py`, `portfolio/views.py`(Slice 13 #65로 legacy 제거됨)

### 봉투 군집 분류

- **A군 — `{success,data,meta}` 풀 래핑** (가장 일관): `stocks/views_screener.py`, `views_fundamentals.py`, `views_exchange.py` (총 16개 뷰)
- **B군 — 봉투 없음/원본 직접**: `stocks/views_indicators.py`, `views_eod.py`, `views_market_movers.py`, `iron_trading`, `sec_pipeline`
- **C군 — 자체 변종 봉투**: `search` `{count,results}`, `mvp` `{mode,count,data}`
- ⚠️ **단일 앱 내 불일치**: 같은 stocks/FMP 군집인데 `market_movers`만 비래핑 → A군 규칙 이탈

---

## HTTP 상태 코드 일관성

### ✅ 양호한 부분

- **`status.HTTP_*` 상수 사용**: stocks/* 전체, apps/*, services/serverless·news·rag·validation 전부 모듈 사용. **하드코딩 정수 status 0건**.
- **DELETE 204**: `users`(`:348,:719,:806,:1169`), `rag_analysis`(`:101,:164,:479`), `serverless/views_admin`(`:746`) 일관 적용.
- **에러 코드 계층화 모범**: `portfolio/api/views.py` — 400(검증)/429(예산)/502(LLM)/500(기타) 4단 분기를 6개 뷰 전부 동형 적용.

### 🟡 불일치 / 누락

**1) POST 생성 시 201 누락 — 대부분 200**

| 위치 | 동작 | 반환 | 비고 |
|------|------|------|------|
| `serverless/views.py:971,1282,1599` | preset/alert/import 생성 | ✅ 201 | 올바름 (3건) |
| `serverless/views_admin.py:625` | 카테고리 생성 | ✅ 201 | 올바름 |
| `users/views.py:108,303,669,774` | 회원가입/portfolio/watchlist | ✅ 201 | 올바름 |
| `users/views.py:981,1119` | bulk add | 조건부 201/200 | `if added else 200` |
| `rag_analysis/views.py:63,141,303,448` | basket/item/session 생성 | ✅ 201 | 단 `:303`은 update에도 201 |
| `news/api/views.py:637,2319` | 키워드 생성/롤백 (비동기 트리거) | 🟡 200 | **202 Accepted가 적절** |
| `serverless/views.py:190,239,396,1068...` | sync/keyword/execute 트리거 | 🟡 200 | 비동기 트리거 다수 200 |
| `market_pulse/views.py:373,382` | DataSync 트리거 | 🟡 200 | 202가 의미상 적절 |

> **202 Accepted 모범 사례**: `sec_pipeline/views.py:50` — 수집 트리거에 의도적으로 202 사용(주석 명시). 다른 비동기 트리거 뷰들은 이를 따르지 않고 200 사용.

**2) 에러를 HTTP 200으로 반환 (🔴 가장 심각)**

| 위치 | 상황 | 문제 |
|------|------|------|
| `validation/api/views.py:417` | insufficient_peers | status 미지정 → 200 |
| `validation/api/views.py:433` | no_leader | 200 |
| `validation/api/views.py:671` | LLM parse error | 200 |
| `chain_sight/api/views.py:290` | trace 내부 예외 | status 누락 → 200 (의미상 500) |

> 동일 "not-found" 개념이 곳에 따라 404 / 200+`status:not_found` / 200+`status:no_report`로 3중 분기 (`news/api/views.py:602,1251` vs `:714`).

**3) 특이 상태코드 (의미 부여 불일치)**

- **422**: `validation/api/views.py:85`만 사용. 같은 파일 `:114`는 유사 상황(no_data)을 404로 처리 → 422/404 혼선.
- **502**: `portfolio/api/views.py`만 (LLM Bad Gateway).
- **503**: `stocks/views_exchange.py`(외부 미수신 시) vs 같은 상황을 다른 stocks 파일은 404로 처리.
- **429**: `serverless:378`, `portfolio:92`, `stocks/views.py:1025`.

**4) 상태코드 미지정 (DRF 아님)**

- `config/views.py:73` — health_check가 DB/캐시 실패해도 200 + body에 `'disconnected'`. `rest_framework` import는 데드 코드.
- `iron_trading/views.py:36~50`, `sec_pipeline/views.py:50~55` — 정수 하드코딩(`status=400/404/503/202`). 단 iron_trading은 503에 `Retry-After` 헤더 수동 설정(유일한 표준 사례).

---

## 에러 응답 형식

### 형식 분포 (전사)

| 형식 | 사용 위치 | 비고 |
|------|----------|------|
| `{'error': str}` | stocks/* 전역, chain_sight, market_pulse, serverless_admin, validation, iron_trading | 가장 흔한 사실상 표준 |
| `{'error': {code, message, details}}` 중첩 | `stocks/views.py:653,1016`만 | 평면 error와 같은 파일 내 공존 |
| `{'detail': ...}` (DRF 예외) | `rag_analysis` 전역, `serverless/views.py` 전역, `users`(예외 raise), `indicators`(get_object_or_404) | DRF 핸들러 위임 |
| `{'message': ...}` | `users:219,249`, `stocks:206`에서 **에러를 message로 표현** + 400 | 에러 신호 모호 |
| `serializer.errors` (필드 dict) | `users`(9건), `stocks` POST, `portfolio` 검증 | 또 다른 구조 |
| `{'error': "machine_code", 'message': ...}` | `validation:81,110,419` | error가 코드값, 자유텍스트 error와 이중성 |
| `{'valid': False, 'error': ...}` | `stocks/views_search.py:117`만 | 동일 파일 내 불일치 |
| `error_body(code, message)` 헬퍼 | `iron_trading`만 | 독자 규약 |

### 핵심 불일치

1. **앱 간 정반대 컨벤션**: `chain_sight`(수동 `Response({'error'},status)`) ↔ `rag_analysis`(`raise NotFound/ValidationError` → `{'detail'}`). 프론트엔드 에러 파싱 분기 강제.

2. **단일 파일 내 다중 스키마**: `users/views.py`는 한 파일에서 **4종**(`{error}`/`{message}`/`{detail}`/`serializer.errors`)을 클라이언트가 모두 파싱해야 함. `stocks/views.py`는 평면 `{error:str}`과 중첩 `{error:{code,message,details}}`가 공존.

3. **error 키 의미 이중성**: `validation/api/views.py`에서 `error: str(e)`(자유 텍스트, `:71,:231`)와 `error: "not_in_universe"`(머신 코드 + 별도 message, `:81,:110,:419`)가 혼재 → 클라이언트 파싱 규칙 통일 불가.

4. **`{'message'}`로 에러 표현**: `users:219,249`, `stocks:206` — 400과 함께 `{'message'}` 사용. 성공 응답에서도 `message` 키를 쓰기 때문에(`users:227`, `serverless` 다수) 키만으로 성공/실패 구분 불가.

### 정보 노출 (보안)

`str(e)`/예외 원문을 응답 본문에 직접 노출하는 곳:
- `stocks/views.py:377,386,659,744,825,903`
- `chain_sight/api/views.py:291` (trace error 키)
- `rag_analysis/views.py:663,725,747,821` (커스텀 예외에 raw str(e) 전달)
- `stocks/views_search.py:85,144` (broad except → str(e))

> **모범**: `portfolio/api/views.py` — `logger.exception()` 로깅 + 일반 메시지("Internal server error")만 반환, 스택트레이스 비노출.

---

## 페이지네이션 현황

### 🔴 전역 결론: DRF `pagination_class` 실효 적용 사실상 0건

- **DRF 표준 페이지네이션 동작**: `stocks/views.py` `StockListAPIView`(`:100`, `StockListPagination` page_size=50/max 200)가 **유일하게 올바른 DRF 페이지네이션**. 주석에 "S&P 6000+ 종목 DoS 표면 축소" 명시.
- `news/api/views.py`는 `NewsArticlePagination` 클래스를 정의(`:55`)·연결(`:73`)했으나 커스텀 `@action` 메서드들이 `paginate_queryset`을 **전혀 호출하지 않아** 표준 list/retrieve에만 적용됨.

### 수동 페이지네이션 (Django `Paginator` 또는 page/offset 직접 구현)

| 위치 | 방식 | 응답 스키마 |
|------|------|-------------|
| `users/views.py:622,860` | Django `Paginator` | `{results, pagination:{...}}` |
| `rag_analysis/views.py:762` | Django `Paginator` | `{results, pagination:{current_page,...}}` |
| `serverless/views.py:1048,1183` | page/offset → FilterEngine | `{**results, next, previous}` (DRF 흉내) |
| `chain_sight/api/views.py:739` | 메모리 슬라이싱 | `{date, page, page_size, total_count, has_next, chains}` |

> ⚠️ **수동 페이지네이션 스키마조차 불일치**: `users`/`rag`는 중첩 `pagination` 객체, `chain_sight`는 평면 `page/has_next`, `serverless`는 `next/previous` URL. 4가지 서로 다른 페이지네이션 응답 형태.

### 🔴 무제한 전건 반환 (성능/DoS 표면)

| 위치 | 쿼리 | 위험도 |
|------|------|--------|
| `serverless/views.py:937` `screener_presets_api` | `ScreenerPreset.objects.all()` 전량 + union | **1순위 (전체 테이블 스캔, 상한 없음)** |
| `news/api/views.py:117` `stock_news` | `.filter().distinct()` row 무제한 (days만 제한) | 높음 |
| `news/api/views.py:1452,1939,2034,2162` | collection_logs/ml_trend/llm_usage/task_timeline | 시간 윈도만, row 무제한 |
| `users/views.py:93` `Users.get` | `User.objects.all()` 전량 | 관리자용이나 무제한 |
| `validation/api/views.py:519` `comparisons` | 전 카테고리×전 지표 루프, 상한 없음 | 중간 |
| `stocks/views_mvp.py:221`, `views_search.py:182` | SectorList/popular 전건 | 낮음 (소량) |

### limit 슬라이스 방어 (페이지네이션 아님, 후속 페이지 불가)

- 클램프형: `screener`(1~1000), `fundamentals`(1~40), `exchange`(≤100), `market_movers`(1~20), `serverless` task logs(≤200)
- 하드코딩형: `search`(`[:10]`), `mvp`(`[:20]`), `eod`(`[:50]`,`[:7]`), `serverless`(`[:10]`,`[:50]`), `validation`(`[:50]`)

---

## 권고사항

### P0 — 우선 (정합성/안정성 직접 영향)

1. **에러를 200으로 반환하는 버그성 코드 교정**
   - `validation/api/views.py:417,433,671`, `chain_sight/api/views.py:290`에 적절한 4xx/5xx status 부여.
   - 영향: 클라이언트가 HTTP 상태로 실패를 감지 가능해짐.

2. **무제한 전건 반환에 상한/페이지네이션 도입**
   - 1순위 `serverless/views.py:937 screener_presets_api`, `news/api/views.py:117 stock_news` 및 monitoring 목록들(`:1452,1939,2034,2162`).
   - 기존 `StockListPagination`(`stocks/views.py:92`)을 공용 페이지네이션 베이스로 승격.

3. **내부 예외 메시지 노출 차단**
   - `str(e)` 응답 노출 위치(stocks/chain_sight/rag/search)를 `portfolio/api/views.py` 패턴(logger.exception + 일반 메시지)으로 통일.

### P1 — 표준화 (중기)

4. **공통 응답 envelope 결정 → `DECISIONS.md` 등재**
   - 현재 3군집(A `{success,data,meta}` / B 직접 / C 자체봉투)이 공존. **단일 출처는 repo 하네스**(CLAUDE.md Harness Protocol)이므로, envelope 채택 여부를 결정으로 박고 `contracts/`에 반영.
   - 권고: A군의 `{success,data,meta}`를 표준 후보로 채택(이미 16개 뷰 적용·테스트됨).

5. **에러 응답 형식 단일화**
   - DRF 예외(`raise NotFound/ValidationError/PermissionDenied`) 기반으로 통일 → 자동 `{'detail'}` + status. `rag_analysis`가 이미 이 방식이므로 레퍼런스로 사용.
   - `{'message'}`로 에러를 표현하는 곳(`users:219,249`, `stocks:206`) 제거.
   - `validation`의 머신코드 error vs 자유텍스트 error 이중성 해소(`{code, detail}` 형태로 통일).

6. **POST 의미론 정리**
   - 리소스 생성 → 201, 비동기 트리거 → 202 Accepted(`sec_pipeline:50` 패턴). 현재 200으로 통일된 트리거들(`news:637`, `market_pulse:373`, `serverless` sync류) 검토.

### P2 — 정리 (저위험)

7. **상태코드 하드코딩 제거**: `iron_trading/views.py`, `sec_pipeline/views.py`의 정수 status를 `status.HTTP_*` 상수로 (단 202는 의도적이므로 `status.HTTP_202_ACCEPTED`로 유지).
8. **`config/views.py` health_check**: DB/캐시 실패 시 503 반환하도록(현재 200). 데드 `rest_framework` import 정리.
9. **단일 앱 내 이탈 정렬**: `stocks/views_market_movers.py`를 A군 `{success,data,meta}`로 맞춤.
10. **페이지네이션 응답 스키마 통일**: 수동 페이지네이션 4종(users/rag/chain_sight/serverless)을 단일 형태로.

### 레퍼런스 모델

- **응답 일관성 표준**: `portfolio/api/views.py` (6뷰 동형, 4단 에러 분기, 스택트레이스 비노출)
- **페이지네이션 표준**: `stocks/views.py:92 StockListPagination`
- **봉투 표준 후보**: `stocks/views_screener.py` A군 `{success,data,meta}`

---

> 본 보고서는 읽기 전용 정적 분석 결과입니다. 줄번호는 감사 시점(2026-06-18) 기준이며, 권고 적용 전 해당 라인을 재확인하십시오. 코드는 수정하지 않았습니다.
