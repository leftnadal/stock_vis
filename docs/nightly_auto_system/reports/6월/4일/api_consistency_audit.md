# API 응답 일관성 감사 보고서

> 생성일: 2026-06-04
> 범위: 전체 `views*.py` 27개 파일 (migration/pycache/node_modules 제외)
> 성격: **읽기 전용 감사** — 코드 수정 없음. 권고사항은 제안일 뿐 미적용.

---

## 요약

전체 27개 views 파일 중 **실질 분석 대상은 21개** (6개는 빈 스텁: `apps/chain_sight/views.py`, `apps/portfolio/views.py`, `packages/shared/metrics/views.py`, `services/_dormant/graph_analysis/views.py`, `services/news/views.py`, `services/validation/views.py`).

핵심 결론: **프로젝트 전체를 관통하는 단일 응답 규약이 없다.** 큰 방향은 "평탄(flat) 응답"으로 수렴하지만, 4개 축(래핑 / 에러 키 / 상태코드 / 페이지네이션) 모두에서 앱별·파일별, 심지어 같은 파일 내에서도 갈린다.

| 축 | 지배적 패턴 | 핵심 불일치 |
|----|------------|------------|
| **응답 래핑** | 평탄 응답 (도메인 키 직접 펼침). `{success, data}`는 사실상 부재 | `stocks` 앱 내 FMP 프록시 계열(`views_exchange/fundamentals/screener`)만 `{success, data, meta}` 봉투 사용 → **앱 내 이원화** |
| **에러 키** | `{'error': ...}` 문자열이 최다 | `{detail}`(DRF 기본) / `{message}` / `serializer.errors` raw / `{error: {code, message}}` 중첩 — **최대 4종 혼용**, `error` 값 타입조차 str↔dict 불일치 |
| **상태 코드** | `status.HTTP_*` 상수 (대다수) | `iron_trading`·`sec_pipeline`만 raw int 하드코딩. **에러를 200으로 반환하는 안티패턴** 다수. POST 생성 201 적용 불균일 |
| **페이지네이션** | 사실상 부재 | DRF `pagination_class` 설정은 **단 2곳**(`StockListAPIView`, `NewsViewSet`). 나머지는 수동 슬라이싱 또는 **무제한 `.all()/.filter()` 반환** |

**가장 표준화 안 된 파일**: `packages/shared/users/views.py`(에러 4종 혼용), `services/news/api/views.py`(봉투/배열·예외/Response 혼용).
**가장 일관된 파일**: `services/rag_analysis/views.py`(예외-주도 + 201/204 정확), `services/serverless/views_admin.py`(단일 `error` 키 + 상수).

---

## 앱별 응답 패턴 매트릭스

> 범례 — 래핑: `플랫`=도메인 키 직접 / `{s,d,m}`=`{success,data,meta}` 봉투 / `{cnt,arr}`=`{count, 배열}` 자체봉투
> 에러키: `error(str)` / `detail`(DRF) / `message` / `errors`(필드dict) / `error{obj}`(중첩)
> status: `상수`=`status.HTTP_*` / `int`=하드코딩 / `생략`=암묵 200
> 201: POST 생성 시 201 적용 여부

| 파일 | 래핑 | 에러 키 | status 스타일 | 201 | 페이지네이션 | 비고 |
|------|------|--------|--------------|-----|------------|------|
| `apps/chain_sight/api/views.py` | 플랫(키 제각각) | `error(str)` | 상수 | — (GET) | 수동(SignalFeed page/size) | TraceView 에러를 200으로 반환 |
| `apps/chain_sight/views.py` | — | — | — | — | — | **빈 스텁** |
| `apps/market_pulse/views.py` | 플랫(serializer/raw 혼용) | `error(str)` | 상수 | 200(트리거) | 없음 | 비즈니스 에러 전부 500으로 뭉갬 |
| `apps/portfolio/api/views.py` | 플랫(`{output,llm_metadata}`) | `error(str)`+DRF | 상수(200 명시) | 200(LLM 실행) | 해당없음 | 에러 분류 가장 정교(400/429/502/500) |
| `apps/portfolio/views.py` | — | — | — | — | — | **빈 스텁**(Slice13 #65 legacy 제거) |
| `config/views.py` | 플랫(JsonResponse) | 없음 | **전부 200** | — | 해당없음 | health_check이 실패도 200, DRF import만 dead |
| `integrations/iron_trading/views.py` | envelope(schema_version) | `error{code,message}` 중첩 | **raw int** | — (GET) | limit 상한 | 유일 하드코딩 + Retry-After 헤더 |
| `packages/shared/metrics/views.py` | — | — | — | — | — | **빈 스텁** |
| `packages/shared/stocks/views.py` | 플랫(`data`/`results` 혼용) | `error(str)`/`error{obj}`/예외 | 상수(200 명시) | 200(sync) | `StockListAPIView`만 DRF PageNumber | 검색 `result`/`results` 키 오타성 불일치 |
| `packages/shared/stocks/views_eod.py` | 플랫 | `error(str)` | 상수 | — | 없음(`[:50]` 슬라이싱) | |
| `packages/shared/stocks/views_exchange.py` | **`{s,d,m}` 봉투** | `error(str)` | 상수 | 200(Batch POST) | 없음 | 성공/에러 형식 비대칭 |
| `packages/shared/stocks/views_fundamentals.py` | **`{s,d,m}` 봉투** | `error(str)` | 상수 | — | 없음(limit 클램프) | 성공/에러 형식 비대칭 |
| `packages/shared/stocks/views_indicators.py` | 플랫 | `error(str)` | 상수 | 200(비교 POST) | 없음 | |
| `packages/shared/stocks/views_market_movers.py` | 플랫(serializer) | `error(str)` | 상수 | — | 없음(limit 클램프) | |
| `packages/shared/stocks/views_mvp.py` | 플랫(`{mode,data}`, camelCase) | `detail`(get_object_or_404) | 거의 생략 | — | 없음(`[:20]` 하드) | 키 camelCase로 타 파일과 불일치 |
| `packages/shared/stocks/views_screener.py` | **`{s,d,m}` 봉투** | `error(str)`/`error: errors(dict)` | 상수 | — | 없음(limit 클램프) | `error` 값 타입 str↔dict |
| `packages/shared/stocks/views_search.py` | 플랫(`{count,results}`) | `error(str)`/`{valid,error}` | 상수 | — | 없음(`[:10]`) | |
| `packages/shared/users/views.py` | 플랫(다종) + 커스텀 페이지봉투 | **error/detail/message/errors 4종** | 상수 | **201 정확**(+조건부) | Django Paginator 수동 + 무제한 다수 | **가장 혼란**, DELETE 204·부분성공 207 |
| `services/_dormant/graph_analysis/views.py` | — | — | — | — | — | **빈 스텁** |
| `services/news/api/views.py` | 플랫(`{cnt,arr}`)+생배열 혼용 | `error(str)`+`errors`(raise) | 상수 | 200(생성) | `NewsViewSet`만 DRF, @action 우회 | 봉투/배열·예외/Response 혼용 |
| `services/news/views.py` | — | — | — | — | — | **빈 스텁** |
| `services/rag_analysis/views.py` | 플랫(serializer/커스텀봉투) | **예외-주도(`detail`)** | 상수 | **201/204 정확** | 없음(`Paginator` 1곳) | i18n gettext 사용, 가장 일관 |
| `services/sec_pipeline/views.py` | 플랫(서비스 dict) | 없음(202 분기) | **raw int** | — (GET) | 해당없음 | 200/202 분기 |
| `services/serverless/views.py` | 플랫(`{cnt,arr}`, envelope v2 명시) | 예외-주도(`detail`/필드) | 상수 | **혼재**(일부 201, 일부 누락) | 수동 DRF모방/무제한 다수 | generate_thesis 생성인데 200 |
| `services/serverless/views_admin.py` | 플랫(`{복수명}`) | **단일 `error(str)`** | 상수 | 201(카테고리)·204 | limit만 | 가장 깔끔한 단일 에러 키 |
| `services/validation/api/views.py` | 플랫(`{symbol, 복수명}`) | `error(코드)`+`message` 2키 | 상수(422 사용) | 200(update_or_create) | 없음(`[:50]`) | **에러를 200으로** 다수, 수동 401 |
| `services/validation/views.py` | — | — | — | — | — | **빈 스텁** |

---

## HTTP 상태 코드 일관성

### 상수 vs 하드코딩
- **`status.HTTP_*` 상수가 사실상 표준** — 분석 대상 21개 중 19개.
- **이탈 2건 (raw int 하드코딩)**:
  - `integrations/iron_trading/views.py:36,41,46,50` — `status=400/404/503/200`
  - `services/sec_pipeline/views.py:43,53,55` — `status=202/200`

### POST 생성 시 201 적용
적용이 **매우 불균일**:
- **정확히 적용**: `rag_analysis`(전부 201/204), `users/views.py`(201 + 조건부 `201 if created else 200`), `serverless`의 일부(`screener_presets` `:973`, `screener_alerts` `:1284`, `import_preset` `:1601`), `views_admin`(카테고리 `:625`)
- **누락(생성인데 200)**: `serverless` `generate_thesis`(`:1758`, 테제 신규 생성), `share_preset`(`:1497`, 공유코드 생성), `news/api` `generate_daily_keywords`(`:666`), `validation/api` `PeerPreference`(`:609`)
- **의도상 타당한 200**: LLM 분석 실행(`portfolio/api`), 동기화 트리거(`market_pulse` DataSync, `stocks` sync), 배치 quote(`views_exchange`) — 리소스 생성이 아니므로 201 부적절

### 에러를 200으로 반환하는 안티패턴 (주의)
- `apps/chain_sight/api/views.py:290-292` — `TraceView` 예외를 `{from,to,found:False,error}` + **status 200**
- `validation/api/views.py:417,433,671` — `insufficient_peers`/`no_leader`/LLM parse error를 **200 + error 키**
- `news/api/views.py:601,1247` — `not_found`/`no_report`를 **200 + status 문자열**
- `config/views.py:77-82` — `health_check`이 DB/cache `disconnected`여도 **200** (모니터링이 HTTP 코드로 실패 감지 불가)

### 세분화 수준 편차
- **가장 정교**: `portfolio/api`(400/429/502/500 구분), `validation/api`(422 단독 사용 `:85`)
- **가장 거침**: `market_pulse`(비즈니스 에러를 일괄 500으로, 400/422 미구분)

---

## 에러 응답 형식

### 4종 형식 공존 (전체 표준 부재)

| 형식 | 사용처 | 특징 |
|------|--------|------|
| `{'error': '문자열'}` | 최다 — chain_sight, market_pulse, stocks 대부분, eod, exchange, fundamentals, indicators, market_movers, search, views_admin, validation/api | 가장 흔함. validation/api는 `{error(코드), message(설명)}` 2키 변형 |
| `{'detail': ...}` (DRF 기본) | `views_mvp`(get_object_or_404), `rag_analysis`(예외-주도), `serverless`(NotFound류), `users/views.py`(예외 throw) | DRF exception handler 위임 |
| `{'message': ...}` | `users/views.py`(즐겨찾기 중복/부재 `:219,250`), `stocks/views.py`(검색) | 에러용 사용은 드뭄 |
| `serializer.errors` raw / `{error: errors}` / `error{code,message}` 중첩 | `users/views.py`(필드dict 직접), `screener`(`error`에 dict `:69`), `stocks/views.py`(`error{code,message,details}` `:653`), `iron_trading`(`error{code,message}` 중첩) | `error` 값 타입이 str↔dict로 불일치 |

### 핵심 불일치
1. **`error` 값 타입 불일치**: 대부분 문자열인데 `views_screener.py:69`는 dict, `iron_trading`/`stocks` 일부는 `{code, message}` 중첩 객체 → 프론트엔드 단일 파싱 불가
2. **DRF 기본 vs 커스텀 혼재**: `portfolio/api`·`news/api`는 같은 파일에서 `raise ValidationError`(필드 dict)와 `Response({"error":...})`를 둘 다 사용
3. **에러/성공 형식 비대칭**: `{success, data}` 봉투를 쓰는 exchange/fundamentals/screener도 **에러에는 `success: False`를 안 붙임** → 봉투 일관성 깨짐
4. **`users/views.py`가 최악**: error/detail/message/serializer.errors 4종 + 일부 `{error, detail}` 동시 포함(`:534,586`)

### 예외-주도 vs 직접 Response 진영
- **예외-주도(DRF 표준 위임)**: `rag_analysis`(가장 철저, i18n gettext), `serverless`(NotFound/ValidationError/커스텀 도메인 예외)
- **직접 Response**: `views_admin`(전 핸들러 `try/except → 500 {error}`), `validation/api`(수동, DRF 예외 전혀 미사용 — serverless와 정반대)

---

## 페이지네이션 현황

### DRF `pagination_class` 설정 — 단 2곳
- `packages/shared/stocks/views.py:92-108` — `StockListAPIView` → `StockListPagination`(PageNumber, page_size=50, max=200), 응답 봉투는 DRF 기본(`count/next/previous/results`)
- `services/news/api/views.py:55-73` — `NewsViewSet` → `NewsArticlePagination`(PageNumber, page_size=20, max=100). **단 기본 list/retrieve만 적용, 커스텀 @action은 전부 우회**

> `CursorPagination`/`LimitOffsetPagination`은 **프로젝트 전체에서 미사용**.

### 수동 페이지네이션 (DRF 미경유)
- `users/views.py:635-655,884-904` — Django 코어 `Paginator` + 커스텀 봉투 `{results, pagination:{count,page,page_size,num_pages,has_next,has_previous}}` (DRF와 형식 다름)
- `rag_analysis/views.py:783-817` — Django `Paginator` + `{results, pagination}`
- `serverless/views.py:1183-1221` — `advanced_screener_api` page/page_size + `{results,count,total_pages,current_page,next,previous}` (DRF 스타일 손수 모방)
- `chain_sight/api/views.py:735-768` — `SignalFeedView` page/page_size + `total_count`/`has_next`

### limit 상한·슬라이싱만 (페이지네이션 아님)
- `views_eod`(`[:50]`/`[:7]`), `views_indicators`(`[:50]`), `views_mvp`(`[:20]` 하드), `views_search`(`[:10]`), `fundamentals`/`market_movers`/`screener`(limit 클램프), `validation/api`(`[:50]`), `serverless` 다수(`[:limit]`/`[:50]`/`[:10]` 하드)

### ⚠️ 무제한 `.all()`/`.filter()` 반환 — 잠재 폭주/DoS 표면
| 위치 | 라인 | 대상 |
|------|------|------|
| `users/views.py` | `:93-95` | `User.objects.all()` |
| `users/views.py` | `:197,271-273,1046-1060` | `UserFavorites`, Portfolio 목록, UserInterest 목록 |
| `rag_analysis/views.py` | `:52,429,496` | DataBasket 목록, AnalysisSession 목록, session.messages.all() |
| `serverless/views.py` | `:937-956,1109-1121,1255,1958` | screener_presets GET, screener_filters, screener_alerts GET, etf_collection_status |
| `serverless/views.py` | `:2956,3013` | regulatory/patent relations |
| `news/api/views.py` | `:1452` | collection_logs (period_days만 제한, list화) |
| `validation/api/views.py` | `:536` | PresetListView |
| `views_admin.py` | `:505` | NewsCollectionCategory.all() (수량 적어 상대적 저위험) |

> 현재 대부분 데이터량이 작아 즉각적 장애는 없으나, User/DataBasket/Session 계열은 사용자 증가 시 위험.

### 페이지네이션 봉투 키 불일치
- DRF 기본: `{count, next, previous, results}` (StockListAPIView)
- users 커스텀: `{results, pagination: {...}}`
- serverless 모방: `{results, count, total_pages, current_page, next, previous}`
- → 세 가지 봉투 형식이 공존

---

## 권고사항

> 아래는 제안이며 본 감사에서 적용하지 않았다. 우선순위 순.

### P1 — 보안/안정성 (즉시 검토 권장)
1. **무제한 목록 반환에 페이지네이션 도입**: `users/views.py`(User/Portfolio/UserInterest), `rag_analysis`(DataBasket/Session/messages)는 사용자 증가 시 폭주 위험. 표준 `PageNumberPagination` 또는 `LimitOffsetPagination` 적용.
2. **에러를 200으로 반환하는 안티패턴 교정**: `chain_sight TraceView`(`:290`), `validation/api`(`:417,433,671`), `news/api`(`:601,1247`) — 실패는 4xx/5xx로. 특히 `config health_check`은 DB/cache 끊김 시 **503** 반환해야 모니터링이 감지 가능.

### P2 — 일관성 (점진적 표준화)
3. **에러 응답 형식 단일화**: 프로젝트 표준 키를 하나로 결정(DRF 관례상 `{'detail': ...}` 권장). 최소한 `error` 값 타입을 str로 통일하고, `screener.py:69`의 dict·`users/views.py`의 4종 혼용·`stocks` 중첩객체를 정리.
4. **POST 생성 201 통일**: 리소스를 실제 생성하는 엔드포인트(`generate_thesis`, `share_preset`, `generate_daily_keywords`)는 201로. 트리거/실행성 POST는 200 유지(현행 타당).
5. **응답 래핑 정책 명문화**: `stocks` 앱 내 FMP 프록시(`exchange/fundamentals/screener`)만 `{success,data,meta}` 봉투를 쓰는 이원화 해소. "평탄 응답"으로 통일하거나 봉투로 통일하되 **에러에도 동일 봉투 적용**(현재 성공/에러 비대칭).

### P3 — 스타일 (낮은 우선순위)
6. **raw int status → 상수 전환**: `iron_trading/views.py`(`:36,41,46,50`), `sec_pipeline/views.py`(`:43,53,55`)를 `status.HTTP_*`로.
7. **페이지네이션 봉투 키 통일**: DRF 기본(`count/next/previous/results`)으로 수렴, `users`·`serverless`의 커스텀 봉투 정리.
8. **camelCase/snake_case 키 통일**: `views_mvp.py`의 camelCase(`changePercent`, `tokenCount`)를 프로젝트 표준(snake_case)으로.
9. **dead import 정리**: `config/views.py`의 미사용 DRF import(`Response`/`status`/`api_view`).

### 빈 스텁 6개 (정보)
`apps/chain_sight/views.py`, `apps/portfolio/views.py`, `packages/shared/metrics/views.py`, `services/_dormant/graph_analysis/views.py`, `services/news/views.py`, `services/validation/views.py` — 분석 대상 응답 없음. `portfolio/views.py`는 Slice 13 #65 legacy 제거로 의도적 공동화, `graph_analysis`는 `_dormant`(보류) 상태.

---

*본 보고서는 정적 코드 분석 기반이며, 라인 번호는 감사 시점(2026-06-04) 기준이다. 실제 런타임 응답은 serializer 정의·exception handler·미들웨어에 따라 달라질 수 있다.*
