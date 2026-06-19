# API 응답 일관성 감사 보고서

> 생성일: 2026-06-19
> 대상: `/Users/byeongjinjeong/Desktop/stock_vis` — 전체 `views*.py` 27개 파일 (14,411 라인)
> 모드: **읽기 전용 감사 (코드 수정 없음)**
> 방법: 4개 병렬 탐색 에이전트로 전 파일 정독 후 종합

---

## 요약

Stock-Vis 백엔드의 27개 views 파일을 전수 조사한 결과, **앱·서비스마다 응답 규약이 제각각**으로 4가지 차원(래핑/상태코드/에러형식/페이지네이션) 모두에서 일관성 결함이 확인되었다. 단일한 API 응답 표준이 존재하지 않으며, 같은 `stocks` 앱 내부에서조차 파일별로 패턴이 갈린다.

### 핵심 발견 (심각도 순)

| # | 발견 | 심각도 | 영향 범위 |
|---|------|--------|----------|
| 1 | **응답 래핑 3종 혼재** — `{success, data}` / 직접 dict / `{count, list}`가 표준 없이 공존 | 🔴 높음 | 전체 (프론트 파싱 분기 강제) |
| 2 | **에러 형식 4종 혼재** — `{error}` / `{detail}` / `{message}` / `{error:{code,message}}` | 🔴 높음 | 전체 (프론트 에러 핸들링 불가 통일) |
| 3 | **목록 API 페이지네이션 부재** — 대부분 `.all()`/`.filter()`를 limit 슬라이싱으로 통째 반환 | 🟠 중간 | 목록 엔드포인트 다수 |
| 4 | **POST 생성 시 201 미적용** — `users`/`rag_analysis`/`serverless`만 201, 나머지는 200 | 🟡 낮음 | portfolio, news, validation 등 |
| 5 | **상태코드 하드코딩** — `iron_trading`, `sec_pipeline`은 `status=400`/`202` 숫자 직접 사용 | 🟡 낮음 | 2개 파일 |

### 빈 파일 (분석 제외)
`packages/shared/metrics/views.py`, `apps/chain_sight/views.py`, `apps/portfolio/views.py`, `services/news/views.py`, `services/validation/views.py`, `services/_dormant/graph_analysis/views.py` — 스켈레톤/주석만 존재. 실제 API는 각 앱의 `api/views.py` 또는 `views_*.py`에 구현됨.

---

## 앱별 응답 패턴 매트릭스

| 파일 | 래핑 패턴 | 일관성 | POST 201 | 상태코드 방식 | 에러 형식 | 페이지네이션 |
|------|----------|:------:|:--------:|--------------|----------|--------------|
| **stocks/views.py** | 혼합 (`{symbol,tab,data}` / 직접 / `{error:{code..}}`) | ❌ | 200 | `status.HTTP_*` | `{error}` + `{error:{code,message,details}}` | ✅ `StockListPagination` (유일) |
| **stocks/views_exchange.py** | `{success, data, meta}` | ✅ | N/A | `status.HTTP_*` | `{error}` | ❌ (`many=True` 통째) |
| **stocks/views_screener.py** | `{success, data, meta}` | ✅ | N/A | `status.HTTP_*` | `{error}` + `{error: serializer.errors}` | ❌ (limit 파라미터) |
| **stocks/views_market_movers.py** | `serializer.data` 직접 | ✅ | N/A | `status.HTTP_*` | `{error}` | ❌ (limit≤20) |
| **stocks/views_eod.py** | 직접 dict / `json_data` | ❌ | N/A | `status.HTTP_*` | `{error}` | ❌ (`[:50]` 하드코딩) |
| **stocks/views_indicators.py** | 직접 dict | ❌ | N/A | `status.HTTP_*` (400 미사용) | `{error}` | ❌ |
| **stocks/views_search.py** | 혼합 (`{count,results}` / `{valid,symbol}`) | ❌ | N/A | `status.HTTP_*` | `{error}` | ❌ (`[:10]` 하드코딩) |
| **stocks/views_fundamentals.py** | `{success, data, meta}` | ✅ | N/A | `status.HTTP_*` | `{error}` | ❌ (limit 파라미터) |
| **stocks/views_mvp.py** | 혼합 (`{mode,count,data}` / `{sectors}`) | ❌ | N/A | 명시 없음(암묵 200) | `get_object_or_404` | ❌ (`[:20]` 하드코딩) |
| **config/views.py** | 직접 dict | ✅ | N/A | 암묵 200 | 없음 (health) | N/A |
| **iron_trading/views.py** | `error_body()` / payload 직접 | ✅ | N/A | **하드코딩 (400/404/503/200)** | `error_body(code, msg)` 커스텀 | ❌ |
| **users/views.py** | 혼합 (직접 / `{ok,user}` / `{message,stock}`) | ❌ | ✅ **201** | `status.HTTP_*` | `{error}` + `{message}` + DRF 예외 | ✅ Django `Paginator` (수동) |
| **chain_sight/api/views.py** | 직접 dict | ✅ | N/A | `status.HTTP_*` | `{error}` (+from/to/found) | 수동 슬라이싱 (`chains[start:end]`) |
| **portfolio/api/views.py** | `serializer.data` / 직접 dict | ✅ | ❌ **200** | `status.HTTP_*` | `{error}` (+scope/type) 커스텀 예외 | N/A (POST 전용) |
| **market_pulse/views.py** | `serializer.data` / `{status,message}` | ✅ | 암묵 200 | `status.HTTP_*` | `{error}` | N/A |
| **rag_analysis/views.py** | 혼합 (직접 / `{message,items}`) | ❌ | ✅ **201/204** | `status.HTTP_*` | **DRF 예외 → `{detail}`** + 커스텀 예외 | ❌ (`UsageHistory`만 Paginator) |
| **serverless/views_admin.py** | 혼합 (`{error}` / `{key:data}` / 직접) | ❌ | ✅ **201/204** | `status.HTTP_*` | `{error}` + DRF 예외 혼합 | ❌ (limit 수동) |
| **serverless/views.py** | `{count, list/presets}` / 직접 / `{message,id}` | 🔶 비교적 | ✅ **201** | `status.HTTP_*` | **DRF 예외 → `{detail}`** + 커스텀 | ❌ (수동 offset/limit) |
| **news/api/views.py** | 혼합 (`{symbol,count,articles}` / 직접 list) | ❌ | ❌ **200** | `status.HTTP_*` | `{error}` + DRF `ValidationError` | ✅ `NewsArticlePagination` + 수동 슬라이싱 혼재 |
| **sec_pipeline/views.py** | 직접 dict | ✅ | N/A (202) | **하드코딩 (202/200)** | 에러 처리 없음 | N/A |
| **validation/api/views.py** | 직접 dict | ✅ | ❌ **200** | `status.HTTP_*` | `{error}` + `{error, message}` | N/A |

> 범례: ✅ 일관 / ❌ 불일관 / 🔶 부분 일관 / N/A 해당 엔드포인트 없음

### 래핑 패턴 진영 분류

- **A. `{success, data, meta}` 봉투** (3): `views_exchange`, `views_screener`, `views_fundamentals` — stocks 앱 일부만
- **B. 직접 dict / `serializer.data`** (다수): `chain_sight`, `portfolio`, `market_pulse`, `validation`, `sec_pipeline`, `config` 등 — 가장 흔한 사실상 기본값
- **C. `{count, list/results}` 목록 봉투** (일부): `serverless`, `views_search`, `news` 일부 액션
- **D. 임시 키 혼합** (혼란): `stocks/views.py`, `views_mvp`, `users`, `rag_analysis` — 엔드포인트마다 키 이름이 다름

→ **단일 앱(`stocks`) 안에서 A/B/D 세 진영이 동시 존재.** 프론트엔드는 엔드포인트별로 파싱 로직을 분기해야 한다. (참고: 최근 커밋 `b59b28a` "events/ranking 봉투 응답에서 배열 추출" — 이미 이 불일치로 보드 데이터 로드 실패 버그 발생)

---

## HTTP 상태 코드 일관성

### status 모듈 vs 하드코딩

| 방식 | 파일 |
|------|------|
| ✅ `status.HTTP_*` 상수 | stocks 전체, users, chain_sight, portfolio, market_pulse, rag_analysis, serverless(×2), news, validation |
| ❌ **하드코딩 숫자** | `iron_trading/views.py` (`status=400/404/503/200`), `sec_pipeline/views.py` (`status=202/200`) |
| 암묵 200 (status 미지정) | `config`, `views_mvp`, `market_pulse` 일부, `views_exchange`(성공시) |

→ 대다수는 상수를 쓰나 **2개 파일이 하드코딩**. `news/api/views.py`는 `status.HTTP_404` 상수를 쓰면서도 `status=202`를 하드코딩하는 혼용도 존재.

### POST 생성 시 200 vs 201

| 201 사용 (정석) | 200 사용 (비표준) |
|----------------|------------------|
| `users/views.py` (회원가입/watchlist 추가) | `portfolio/api/views.py` (POST 전용인데 200) |
| `rag_analysis/views.py` (basket/session 생성, 삭제 204) | `news/api/views.py` (POST도 200) |
| `serverless/views.py` + `views_admin.py` (생성 201, 삭제 204) | `validation/api/views.py` (POST 200) |
| | `sec_pipeline` (수집 트리거 202 — 비동기라 합리적) |
| | `market_pulse` DataSyncView (암묵 200) |

→ **생성 응답 201 적용이 절반만 됨.** `rag_analysis`/`serverless`/`users`는 201/204를 올바르게 쓰지만, `portfolio`/`news`/`validation`은 생성·변경에도 200을 반환.

### 에러 상태코드 사용 패턴

- **400 BAD_REQUEST**: 검증 실패 시 광범위 사용 (대부분 파일)
- **401 UNAUTHORIZED**: `users`, `validation`(`'로그인이 필요합니다.'`)
- **403 FORBIDDEN / PermissionDenied**: `rag_analysis`, `serverless` (DRF 예외)
- **404 NOT_FOUND**: 거의 모든 파일에서 사용 (일관적)
- **422 UNPROCESSABLE_ENTITY**: `validation/api/views.py`만 사용 (특이)
- **429 TOO_MANY_REQUESTS**: `stocks/views.py`, `portfolio`, `serverless`
- **500 INTERNAL_SERVER_ERROR**: try/except 폴백에서 광범위 사용
- **502/503 SERVICE_UNAVAILABLE**: `portfolio`(502), `views_exchange`/`iron_trading`/`views_search`(503)

→ 404는 통일됐으나, **검증 실패에 400 vs 422가 갈리고**(validation만 422), **LLM/외부 실패에 500 vs 502 vs 503이 제각각**이다.

---

## 에러 응답 형식

### 형식 4종 분포

| 형식 | 사용처 | 비고 |
|------|--------|------|
| **`{'error': '...'}`** | stocks 전체, users, chain_sight, portfolio, market_pulse, validation, news, serverless_admin | **사실상 다수파** |
| **`{'detail': '...'}`** | `rag_analysis`, `serverless/views.py` | DRF 예외(`raise NotFound/ValidationError`) 자동 변환 결과 |
| **`{'message': '...'}`** | `users`(일부), `validation`(`{error, message}` 병기) | `error`와 혼용 |
| **`{'error': {'code', 'message', 'details'}}`** | `stocks/views.py` (Fallback 체인) | 중첩 구조 — 단독 |
| **커스텀 `error_body(code, msg)`** | `iron_trading` | 자체 헬퍼 |

### DRF 기본 예외 vs 커스텀 dict

- **DRF 예외 사용** (`raise ValidationError/NotFound/PermissionDenied` → 자동 `{detail}`):
  `rag_analysis`, `serverless/views.py`, `users`(일부), `news`(`raise ValidationError`)
- **커스텀 dict 직접 반환** (`Response({'error': ...}, status=...)`):
  stocks 전체, chain_sight, portfolio, market_pulse, validation, iron_trading

→ **같은 코드베이스에서 두 철학이 충돌.** DRF 예외 파일은 `{detail}`을, 커스텀 파일은 `{error}`를 반환하므로, 프론트엔드는 두 키를 모두 검사해야 한다. 일부 파일(`serverless_admin`, `users`, `news`)은 **한 파일 내에서도 두 방식을 혼용**한다.

---

## 페이지네이션 현황

### DRF 표준 페이지네이션 사용 (소수)

| 파일 | 클래스 | 적용 범위 |
|------|--------|----------|
| `stocks/views.py` | `StockListPagination` (PageNumberPagination, 기본 50/최대 200) | `StockListView` (ListAPIView)만 |
| `news/api/views.py` | `NewsArticlePagination` (PageNumberPagination) | `NewsViewSet.list()` 기본 액션만 — `@action` 커스텀 메서드는 수동 슬라이싱 |

### 수동/부재 (다수) — 무한정 반환 위험

| 파일 | 방식 | 위험 |
|------|------|------|
| `users/views.py` | Django `Paginator` (전체 fetch 후 메모리 페이징) | watchlist 대량 시 메모리 |
| `chain_sight/api/views.py` | 메모리 list 슬라이싱 `chains[start:end]` | 전체 빌드 후 슬라이싱 |
| `rag_analysis/views.py` | `UsageHistory`만 Paginator, **나머지 list는 통째 반환** | basket/session 무한정 |
| `serverless/views.py` | 수동 `offset/limit` (DRF 미사용) | screener/alert 통째 |
| `views_eod.py` | `[:50]` 하드코딩 | 페이지 이동 불가 |
| `views_search.py` | `[:10]` 하드코딩 | 페이지 이동 불가 |
| `views_mvp.py` | `[:20]` 하드코딩 | 페이지 이동 불가 |
| `views_screener` / `views_fundamentals` / `views_indicators` / `views_exchange` / `market_movers` | `limit` 파라미터 또는 `many=True` 통째 | **표준 페이지네이션 없음** |

### 핵심 위험: 페이지네이션 없는 목록 반환

다음 엔드포인트는 `.all()`/`.filter()` 결과를 **페이지네이션 없이** 반환한다 (데이터 증가 시 응답 비대화):
- `rag_analysis` — `DataBasketListCreateView.get()` (`prefetch_related` 후 통째), `AnalysisSessionListCreateView.get()`, `SessionMessagesView.get()`
- `serverless/views.py` — breadth history, screener 결과 (수동 offset만)
- `views_indicators.py` — POST로 심볼 리스트 받아 전부 반환
- `serverless/views_admin.py` — `AdminNewsCategoryView` 전체 반환

→ 표준화된 `DEFAULT_PAGINATION_CLASS` 전역 설정이 없어, 각 뷰가 개별적으로 limit을 박거나 누락한다.

---

## 권고사항

> ⚠️ 본 보고서는 읽기 전용 감사이며 아래는 **제안**이다. 적용은 별도 결정/PR 필요.

### P1 — 응답 봉투 표준 단일화 (🔴)
- **단일 출처 결정 필요**: `{success, data, meta}` 봉투(현 stocks 일부) vs 직접 dict(현 다수파) 중 하나를 `DECISIONS.md`에 명문화.
- 신규 코드부터 강제하고, 프론트 공용 파서를 단일화. 최근 `b59b28a` 봉투 배열 추출 버그가 이 불일치의 실증 비용이다.
- 점진 전환: DRF `Renderer` 커스터마이즈로 전역 봉투를 씌우면 기존 뷰 수정 최소화 가능.

### P2 — 에러 형식 통일 (🔴)
- `{error}` vs `{detail}` 중 택일. DRF 생태계 정합성을 보면 **`{detail}`(DRF 기본) 채택 + 커스텀 `exception_handler`** 가 유지보수 유리.
- `Response({'error': ...})` 직접 반환을 `raise APIException` 계열로 점진 이관하면 형식이 자동 통일됨.
- 한 파일 내 혼용(`users`, `serverless_admin`, `news`)부터 우선 정리.

### P3 — 전역 페이지네이션 도입 (🟠)
- `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']` + `PAGE_SIZE` 전역 설정.
- `.all()`/`.filter()` 통째 반환 엔드포인트(특히 `rag_analysis` basket/session, `serverless` screener)에 우선 적용.
- 하드코딩 `[:N]` 슬라이싱(`eod`/`search`/`mvp`)을 표준 페이지네이션 또는 명시적 cursor로 대체.

### P4 — POST 201 / 상태코드 정합 (🟡)
- 생성 엔드포인트(`portfolio`, `news`, `validation`)에 `status.HTTP_201_CREATED` 적용.
- `iron_trading`, `sec_pipeline`의 하드코딩 숫자(`400`/`202`)를 `status.HTTP_*` 상수로 교체.
- 검증 실패 코드 통일: `validation`의 422 vs 나머지 400 정책 결정.

### P5 — 회귀 방지
- `contracts/` OpenAPI 스펙에 표준 봉투·에러 스키마를 정의하고, drf-spectacular(`/api/v2/schema/`)로 실제 응답과 대조하는 계약 테스트 추가.
- pre-commit 또는 테스트에서 "신규 뷰가 표준 응답 헬퍼를 쓰는지" 린트.

---

## 부록: 분석 대상 파일 인벤토리 (27개)

**실 구현 (21)**: stocks/views.py, views_exchange, views_screener, views_market_movers, views_eod, views_indicators, views_search, views_fundamentals, views_mvp / users/views.py / config/views.py / iron_trading/views.py / chain_sight/api/views.py / portfolio/api/views.py / market_pulse/views.py / rag_analysis/views.py / serverless/views.py, views_admin.py / news/api/views.py / sec_pipeline/views.py / validation/api/views.py

**빈/스켈레톤 (6)**: metrics/views.py, chain_sight/views.py, portfolio/views.py, news/views.py, validation/views.py, _dormant/graph_analysis/views.py
