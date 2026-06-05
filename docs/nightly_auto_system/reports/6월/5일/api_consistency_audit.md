# API 응답 일관성 감사 보고서

> **생성일**: 2026-06-05
> **유형**: 읽기 전용 감사 (코드 수정 없음)
> **범위**: 전체 `views*.py` 27개 파일 (migration/pycache/node_modules 제외)
> **방법**: DRF `Response()` 반환 패턴을 응답 래핑·HTTP 상태 코드·에러 형식·페이지네이션 4개 차원으로 전수 분석

---

## 요약

Stock-Vis의 REST API는 **앱·파일마다 응답 규약이 분열되어 있어 프론트엔드가 엔드포인트별로 분기 처리를 강제당하는 구조**다. 핵심 발견 4가지:

1. **응답 래핑 3분파**: `{success, data, meta}` 표준 래퍼는 단 3개 파일(`views_screener.py`, `views_fundamentals.py`, `views_exchange.py`)에서만 사용되고, 나머지 전부는 비래핑(도메인 dict 직접 반환)이다. 같은 `packages/shared/stocks/` 패키지 안에서도 fundamentals/exchange(래핑) vs search/mvp/eod(비래핑)로 갈린다. **프로젝트 전역 지배 패턴은 "비래핑 직접 반환"**.

2. **에러 형식 2종 공존 (가장 큰 구조 결함)**: 커스텀 `{'error': ...}`(약 130건 추정)와 DRF 기본 `{'detail': ...}`(예외 raise 경로)가 한 코드베이스에 공존한다. 더 심각하게 **앱 단위로 정반대 컨벤션**을 쓴다 — `chain_sight`/`serverless`(admin)/`stocks`/`validation`/`market_pulse`는 `{error}`, `rag_analysis`/`serverless`(메인)/`users`(일부)는 DRF `{detail}`(예외 위임).

3. **HTTP 상태 코드는 양호하나 2가지 함정**: `status.HTTP_xxx` 모듈 상수 사용률이 매우 높고 하드코딩 숫자는 소수 파일에 국한된다. 단 ① **HTTP 200 본문에 에러를 실어 보내는 패턴**(validation, chain_sight Trace)과 ② **외부 API 실패를 500 vs 503으로 파일마다 다르게 매핑**하는 불일치가 있다.

4. **DRF 표준 페이지네이션 거의 전무**: 27개 파일 중 `PageNumberPagination`을 정식 사용하는 곳은 `stocks/views.py`(StockListAPIView)와 `news/api/views.py`(ViewSet 기본 list)뿐. 나머지는 수동 슬라이싱/limit 가드에 의존하며, **상한 없는 전량 반환 목록 API가 다수** 존재한다.

| 차원 | 상태 | 핵심 리스크 |
|------|------|------------|
| 응답 래핑 | 🔴 분열 | 표준 래퍼 3파일 vs 비래핑 다수, success/실패 비대칭 |
| HTTP 상태 코드 | 🟡 양호+함정 | 200에 에러 탑재, 500/503 혼재, 일부 하드코딩 |
| 에러 형식 | 🔴 분열 | `{error}` vs `{detail}` 앱별 정반대 |
| 페이지네이션 | 🟠 미흡 | DRF 표준 2곳, 상한 없는 전량 반환 목록 다수 |

---

## 앱별 응답 패턴 매트릭스

| 앱 / 파일 | 뷰 스타일 | 응답 래핑 | 에러 형식 | 페이지네이션 |
|-----------|----------|-----------|-----------|--------------|
| `serverless/views.py` | FBV(`@api_view`) ~40 | 커스텀 평탄 dict (`{count, <키>}`) + 단건은 raw `serializer.data` | **DRF `{detail}`** (예외 위임) | DRF ❌ / 수동 offset 일부 |
| `serverless/views_admin.py` | CBV(`APIView`) 11 | 서비스 dict 패스스루 + 수작업 dict | **커스텀 `{error}`** (~23건) | DRF ❌ |
| `news/api/views.py` | ViewSet 1 (action 30+) | 액션별 ad-hoc dict, 일부 top-level array | `{error}`(5) + `ValidationError`→`detail` **혼재** | ViewSet만 PageNumber, 액션은 수동 |
| `sec_pipeline/views.py` | APIView 1 | 서비스 dict 패스스루 | 없음(상태 문자열) | N/A |
| `iron_trading/views.py` | APIView 1 | payload 패스스루 | **`error_body{code,message}` 단일화** | 서비스 위임 |
| `users/views.py` | CBV(`APIView`) 21 | 직접 반환 + `{results,pagination}` + 벌크 래퍼 혼재 | `{error}`(5) + `{message}`(4) + DRF `{detail}`(예외 ~12) **3종** | Django `Paginator` 수동 2곳 |
| `stocks/views.py` | CBV 11 (DRF 9) | 도메인 envelope(`{symbol,tab,data,_source}`) | `{error:str}`(7) + `{error:{code,...}}`(2) **타입 충돌** | **DRF PageNumber 1곳** (StockListAPIView) |
| `chain_sight/api/views.py` | APIView 7 | 도메인 dict 직접 (serializer 0) | **`{error}` 단일**(7) | DRF ❌ / SignalFeed만 수동 |
| `rag_analysis/views.py` | APIView 13 | serializer 직접 + 수기 dict 혼재 | **DRF `{detail}`** (raise 13+) | DRF ❌ / UsageHistory만 Django Paginator |
| `validation/api/views.py` | APIView 7 | 도메인 dict 직접 | **`{error}`**(12) + 일부 `error+message` | DRF ❌ |
| `views_screener.py` | APIView 6 | **`{success,data,meta}` 래핑** | `{error}`(8) — 성공만 래핑(비대칭) | DRF ❌ / 수동 limit≤1000 |
| `views_fundamentals.py` | APIView 5 | **`{success,data,meta}` 래핑** | `{error}`(8) | DRF ❌ / limit≤40 |
| `views_exchange.py` | APIView 5 | **`{success,data,meta}` 래핑** | `{error}`(9) | 고정 소수 ETF |
| `views_indicators.py` | APIView 3 | 직접 dict 반환 | `{error}`(3) + `get_object_or_404`→`detail` 공존 | DRF ❌ |
| `views_search.py` | APIView 3 | 직접 dict (`{count,results}`) | `{error}`(5), 일부 `{valid,error}` 혼합 | `[:10]` 슬라이스 |
| `views_mvp.py` | APIView 4 | 커스텀 dict (`{mode,count,data}`) | **에러 응답 부재** (`except: pass`) | `[:20]` 슬라이스 |
| `views_eod.py` | APIView 3 | 직접 dict | `{error}`(3) | `[:50]`/`[:7]` 슬라이스 |
| `views_market_movers.py` | APIView 1 | `Response(serializer.data)` 직접 | `{error}`(1) | 외부 API limit |
| `market_pulse/views.py` | APIView 9 | 직접 반환 (대시보드/스칼라) | **`{error}`**(13) | 목록 API 없음 |
| `portfolio/api/views.py` | FBV 6 (coach_e1~e6) | `serializer.data` 직접 | `{error}`(24) + `{error,scope}`/`{error,type}` 확장 | 목록 API 없음 |
| `config/views.py` | Django FBV 2 | `JsonResponse` (DRF 아님) | 에러 분기 없음 | N/A |

**빈/스캐폴드 파일** (분석 대상 없음): `news/views.py`(3줄), `validation/views.py`(1줄), `chain_sight/views.py`(1줄), `portfolio/views.py`(16줄, 빈 호환 모듈), `metrics/views.py`(3줄), `_dormant/graph_analysis/views.py`(3줄).

**`{success: True, data: ...}` 봉투 사용 현황**: 전 코드베이스에서 `{success, data, meta}` 형태를 쓰는 곳은 **`views_screener.py` / `views_fundamentals.py` / `views_exchange.py` 3개 파일(16개 뷰)뿐**이다. 나머지 모든 뷰는 봉투 없이 데이터를 직접 반환한다.

---

## HTTP 상태 코드 일관성

### 양호한 점
- **`status.HTTP_xxx` 모듈 상수 사용률이 압도적**. `serverless`, `news/api`, `users`, `stocks`, `chain_sight`, `rag_analysis`, `validation`, `market_pulse`, `portfolio/api` 및 stocks 하위 뷰 대부분에서 하드코딩 숫자 0건.
- **POST 201 적용이 대체로 합리적**:
  - 실제 리소스 생성에 201 명시: `serverless/views.py:973`(screener_presets), `:1284`(alerts), `:1601`(import_preset); `users/views.py:108/303/669/774`; `rag_analysis/views.py:63/141/303/448`; `serverless/views_admin.py:625`.
  - 비생성 POST(트리거/조회/LLM)는 200 — `portfolio/api`(coach LLM 호출), `views_exchange.py:150`(BatchQuotes 조회), `validation`(검증 연산) 등은 의도적으로 200이 적합.
- **DELETE 204** 일관: `serverless/views_admin.py:746`, `rag_analysis/views.py:101/164/479`.
- **세분화된 상태 코드 사용처**: 429(rate limit — `serverless/views_admin.py:378`, `stocks/views.py:1025`, `portfolio/api` budget), 503(외부 API 다운 — `views_exchange.py`, `iron_trading`), 207(부분 성공 — `users/views.py:580`), 422(`validation/api/views.py:85`).

### 함정 / 불일치
1. **🔴 HTTP 200 본문에 에러 탑재** (상태 코드로 실패 판별 불가):
   - `validation/api/views.py`: `insufficient_peers`(:417), `no_leader`(:433), parse error(:672) — HTTP 200인데 본문에 `error` 키.
   - `chain_sight/api/views.py:288-292`: `ChainSightTraceView` 예외를 200 + `{"found": False, "error": ...}`로 반환.
2. **🟡 외부 API 실패 매핑 불일치**: 동일 성격(외부 데이터 소스 장애)을 `market_pulse`/`views_search`는 **500**, `views_exchange`/`iron_trading`은 **503**, `views_fundamentals`는 try 없이 예외 전파로 처리.
3. **🟡 하드코딩 숫자 잔존** (소수 파일 국한):
   - `sec_pipeline/views.py:49/53/55`: `status=202`, `status=200` 직접.
   - `iron_trading/views.py:36/41/45/50`: `status=400/404/503/200` 직접.
   - (단 이 두 파일은 자체 내에서는 일관됨.)
4. **🟡 생성/갱신 경계 모호**:
   - `serverless/views.py:1758` `generate_thesis` — InvestmentThesis를 DB insert하면서 200 반환(201 기대).
   - `rag_analysis/views.py:303` `AddStockData` — 기존 아이템 갱신도 201 고정.
   - `rag_analysis/views.py:187` `DataBasketClearView` — 삭제 작업인데 204가 아닌 200+메시지.
   - `validation/api/views.py:609` `PeerPreferenceView.post` — `update_or_create`로 신규 생성 가능하나 200.
5. **🟡 헬스체크 상태 무반영**: `config/views.py:77` `health_check`가 DB/cache 장애에도 항상 200 반환 → 모니터링이 상태 코드로 실패 감지 불가.
6. **🟡 unused import**: `views_mvp.py:9`(status import 후 미사용), `config/views.py:7-9`(Response/api_view/status 전부 미사용).

---

## 에러 응답 형식

### 형식별 분포 (추정 집계)

| 형식 | 사용 앱 / 파일 | 비고 |
|------|---------------|------|
| `{'error': str}` | chain_sight(7), serverless/admin(23), stocks(7), validation(12), market_pulse(13), portfolio/api(24), fundamentals(8), exchange(9), search(5), indicators(3), eod(3), screener(8), market_movers(1), users(5), news(5) | **가장 흔한 커스텀 형식** (합계 130건+) |
| `{'detail': str}` (DRF 기본) | serverless/views.py(예외 위임 다수), rag_analysis(13+), users(예외 ~12), `get_object_or_404` 경로 전반 | **`raise NotFound/ValidationError/PermissionDenied` 경유** |
| `{'message': str}` | users(4, 안내성), validation(error와 동반) | 단독 에러 식별자로는 거의 안 씀 |
| `{'error': {code, message, details}}` | stocks/views.py(2: Overview, Sync) | 같은 파일 내 `error:str`와 **타입 충돌** |
| `error_body{code, message}` | iron_trading | **헬퍼로 단일화한 유일 사례** |
| 에러 응답 부재 | views_mvp(`except: pass`), sec_pipeline(상태 문자열) | |

### 핵심 불일치
1. **🔴 앱 단위로 정반대 컨벤션**:
   - **커스텀 `{error}` 진영**: chain_sight, serverless/admin, stocks, validation, market_pulse, portfolio/api, stocks 하위 뷰 → 직접 `Response({"error": ...}, status=...)`.
   - **DRF `{detail}` 진영**: rag_analysis, serverless/views.py(메인), users(예외 경로) → `raise NotFound/ValidationError` 위임.
   - 클라이언트는 같은 백엔드에서 `response.data.error`와 `response.data.detail` 두 경로를 모두 파싱해야 함.
2. **🔴 단일 파일 내 형식 혼재**:
   - `stocks/views.py`: `error` 값이 str(7건)과 구조화 dict(2건)로 갈림.
   - `users/views.py`: `{error}`(5) + `{message}`(4) + DRF `{detail}`(예외) 3종 공존.
   - `news/api/views.py`: 직접 `{error}`(5)와 `raise ValidationError`(→detail/필드맵) 혼재.
   - `views_indicators.py`: 커스텀 `{error}`(3)와 `get_object_or_404`→`{detail}` 공존.
3. **🟡 `error` 값 타입 불일치**: `validation/api/views.py`에서 사람이 읽는 문장(`:71`)과 머신 코드(`"not_in_universe":82`, `"no_data":112`, `"insufficient_peers":421`)가 같은 `error` 키에 섞임 → 클라이언트가 표시용/분기용을 구분 못 함.
4. **🟡 success/실패 비대칭**: `{success, data, meta}` 래퍼를 쓰는 screener/fundamentals/exchange조차 **에러는 `{error}` 평탄 형식** → 성공/실패 응답 구조가 비대칭.
5. **🟢 모범 사례**: `iron_trading`만 `error_body(code, message, retry_after)` 헬퍼로 에러 형식을 단일화하고 503에 `Retry-After` 헤더까지 부착.

---

## 페이지네이션 현황

### DRF 표준 페이지네이션 사용 (전체에서 2곳뿐)
- `stocks/views.py:92-108` — `StockListPagination(PageNumberPagination)` (page_size 50, max 200), `StockListAPIView`에 적용. **유일한 정식 DRF 페이지네이션**.
- `news/api/views.py:55-60` — `NewsArticlePagination(PageNumberPagination)` (page_size 20), ViewSet 기본 list/retrieve에만 적용. **커스텀 `@action`은 모두 우회**.

### 수동 페이지네이션
- `serverless/views.py:1148-1226`(advanced_screener), `:1030-1074`(execute_preset) — `page`/`page_size`→offset/limit 계산 + `next`/`previous` URL 수동 생성.
- `users/views.py:635-655`, `:884-904` — Django `core.paginator.Paginator` (page_size 20, max 100).
- `rag_analysis/views.py:762-817`(UsageHistory) — Django `Paginator` + `{results, pagination}` 응답.
- `chain_sight/api/views.py:739-768`(SignalFeed) — `page`/`page_size` 슬라이싱 + `has_next`/`total_count`.
- **주의**: 수동 구현 간에도 응답 스키마가 불일치 — 평면 `has_next`/`total_count`(chain_sight) vs 중첩 `pagination` 객체(rag, users).

### 🔴 상한 없는 전량 반환 목록 API (성능/노출 리스크)
| 파일:line | 엔드포인트 | 내용 |
|-----------|-----------|------|
| `serverless/views.py:937-963` | screener_presets_api GET | `.all()` 필터 후 전량, limit 없음 |
| `serverless/views.py:1109-1140` | screener_filters_api | `filter(is_active=True)` 전량 |
| `serverless/views.py:1255-1269` | screener_alerts_api GET | 사용자 알림 전량 |
| `serverless/views_admin.py:505-531` | AdminNewsCategoryView.get | `.all()` 전량 루프 직렬화 |
| `news/api/views.py:117-130` | stock_news | `filter().distinct()` 전량, slice 없음 |
| `news/api/views.py:1452` | collection_logs | `list(qs.values(...))` 전량 |
| `users/views.py:92-95` | Users.get | `User.objects.all()` 전량 |
| `users/views.py:195-201` | UserFavorites.get | favorite_stock 전량 |
| `users/views.py:271-273` | PortfolioListCreateView.get | portfolio filter 전량 |
| `users/views.py:1045-1060` | UserInterest.get | interest filter 전량 |
| `rag_analysis/views.py:52-54` | DataBasketList.get | basket filter 전량 |
| `rag_analysis/views.py:429-433` | AnalysisSessionList.get | session 전량 |
| `rag_analysis/views.py:496-498` | SessionMessages.get | `messages.all()` 전량 |
| `chain_sight/api/views.py:370-372` | SeedListView | 시드 전량 |
| `validation/api/views.py:519/569` | LeaderComparison/PresetList | comparisons/presets 전량 |
| `views_mvp.py:220-227` | SectorListView | distinct sector 전량 (카디널리티 낮음) |

### 🟢 하드 슬라이스로 방어된 목록 (페이지 이동은 불가)
- `serverless/views.py`: list_theses `[:50]`, alert_history `[:100]`, trending `[:10]`, etf_holdings `[:50]`.
- `views_fundamentals.py`: limit≤40 / `views_screener.py`: limit≤1000 / `views_mvp.py`: `[:20]` / `views_eod.py`: `[:50]`/`[:7]` / `views_search.py`: `[:10]`.

---

## 권고사항

> 본 보고서는 읽기 전용 감사이며, 아래는 우선순위별 개선 제안이다 (코드 미수정).

### P0 — 에러 형식 단일화 (영향도 최상)
- **커스텀 DRF Exception Handler 도입**: `settings.REST_FRAMEWORK['EXCEPTION_HANDLER']`에 단일 핸들러를 등록해 모든 에러를 `{error: {code, message}}` 또는 `{detail}` 중 하나로 정규화. 현재 `{error}`(130건+)와 `{detail}`(예외 위임)가 공존해 FE 파싱이 이원화돼 있음.
- **`error` 값 타입 통일**: 머신 코드는 `error.code`, 사람용 메시지는 `error.message`로 분리 (현재 validation에서 혼재).
- **HTTP 200 + 에러 본문 제거**: `validation/api/views.py:417/433/672`, `chain_sight/api/views.py:288-292`를 적절한 4xx로 교정.

### P1 — 응답 래핑 정책 결정
- `{success, data, meta}` 래퍼를 **전면 채택하거나 전면 폐기** 중 하나로 통일. 현재 3개 파일만 래핑해 동일 패키지 내에서도 불일치.
- 채택 시 **에러도 동일 봉투**(`{success: false, error: {...}}`)로 감싸 success/실패 비대칭 해소.
- 폐기 시 비래핑 직접 반환을 표준으로 명문화하고 screener/fundamentals/exchange를 정렬.

### P2 — 페이지네이션 표준화
- 공통 `StandardResultsSetPagination(PageNumberPagination)`를 정의하고 상한 없는 전량 반환 목록 16곳(위 표)에 적용.
- 우선순위: 사용자 증가에 비례해 커지는 `users/views.py`(Users/Portfolio/Interest), `rag_analysis`(Session/Messages), `news/api`(stock_news/collection_logs), `serverless`(presets/filters/alerts).
- 수동 페이지네이션 응답 스키마를 `{results, pagination: {...}}` 형태로 통일.

### P3 — HTTP 상태 코드 정리
- 외부 API 장애 매핑을 **503으로 통일**(현재 500/503 혼재).
- 생성/갱신 경계 교정: `generate_thesis`(201), `DataBasketClearView`(204), `PeerPreferenceView`(생성 시 201).
- 하드코딩 숫자(`sec_pipeline`, `iron_trading`)를 `status.HTTP_xxx` 상수로 교체.
- `config/views.py:health_check`가 DB/cache 장애 시 503 반환하도록 수정.
- unused import 제거(`views_mvp.py:9`, `config/views.py:7-9`).

### P4 — 모범 사례 확산
- `iron_trading`의 `error_body` 헬퍼 + `Retry-After` 헤더 패턴을 공통 유틸로 승격해 전 앱에 재사용.

---

## 부록: 분석 메타

- **분석 파일**: 27개 (코드 있는 21개 + 빈 스캐폴드 6개)
- **총 라인 수**: 약 17,000줄
- **방법**: 6개 병렬 에이전트가 파일 그룹별로 4개 차원 전수 분석 후 종합
- **한계**: `error` 키 카운트는 각 에이전트의 정적 분석 추정치이며, 일부 커스텀 APIException(`SyncFailed`, `BasketFull` 등)의 최종 직렬화 형식은 `.exceptions` 모듈 미확인분이 포함됨. 정확한 런타임 형식 검증은 별도 통합 테스트 권장.
