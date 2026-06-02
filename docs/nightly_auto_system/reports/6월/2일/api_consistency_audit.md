# API 응답 일관성 감사 보고서

> 생성일: 2026-06-02 · 범위: 전체 Django/DRF `views*.py` (28개 모듈, 빈 모듈 6개 제외 22개 실질 분석) · **읽기 전용 감사 — 코드 수정 없음**
> 분석 방법: 5개 영역별 병렬 코드 리딩 + 전역 설정(`config/settings.py`, `config/exception_handler.py`) 직접 검증

---

## 요약

Stock-Vis의 API 레이어는 **명문화된 에러 envelope 표준이 이미 존재함에도(`{detail, code?, errors?, status_code}`, `docs/features/api_envelope/policy.md`), 실제 구현은 이를 광범위하게 우회**하는 이중 계약 상태다.

핵심 발견 4가지:

1. **에러 응답 이중 계약 (가장 심각).** `config/exception_handler.py`의 커스텀 핸들러는 **DRF 예외(`raise NotFound/ValidationError/...`)에만** 표준 envelope를 적용한다. 그러나 대다수 뷰는 `return Response({"error": str(e)}, status=...)`로 **수동 반환**하여 핸들러를 우회한다. 결과적으로 같은 API 서버에서 `{"detail": ..., "code": ..., "status_code": ...}`와 `{"error": ...}` 두 종류의 에러 형식이 공존한다. 일부는 `{"message": ...}`, `{"status": ...}`, `{"valid": false, "error": ...}`까지 섞인다.

2. **성공 응답 래핑 패턴 3종 혼용.** ① `{"success": True, "data": ..., "meta": ...}` 완전 래핑(stocks의 exchange/fundamentals/screener), ② `{"results": ..., "count": ...}` / `{"mode": ..., "count": ..., "data": ...}` 부분 래핑, ③ `Response(serializer.data)` / `Response(dict)` 직접 반환(market_pulse, indicators, coach, news, validation 등 다수). 클라이언트가 엔드포인트마다 다른 봉투를 파싱해야 한다.

3. **페이지네이션 전역 미설정.** `REST_FRAMEWORK` 설정에 `DEFAULT_PAGINATION_CLASS`/`PAGE_SIZE`가 **아예 없다.** 따라서 `ListAPIView`/`ViewSet`도 기본 페이지네이션이 작동하지 않으며, 대부분의 목록 엔드포인트가 `.all()`/`.filter()` 결과를 슬라이싱(`[:20]`, `[:50]`)으로만 제한하거나 **통째로 반환**한다. 페이지네이션은 5~6곳에서 각기 다른 방식(DRF `PageNumberPagination`, `django.core.paginator.Paginator`, 수동 `offset/page_size`)으로 **개별 재구현**되어 있다.

4. **상태 코드는 비교적 양호하나 예외 존재.** 대부분 `status.HTTP_*` 상수를 사용하지만, `sec_pipeline/views.py`(`status=200/202`)와 `iron_trading/views.py`(`status=400/404/503/200`)는 **하드코딩 정수**를 쓴다. POST 생성 시 201 사용도 일관되지 않다(일부 앱은 201, coach·thesis·market_pulse·validation 등은 200).

| 차원 | 일관성 | 핵심 문제 |
|------|:---:|------|
| 성공 응답 래핑 | 🔴 낮음 | 완전 래핑/부분 래핑/직접 반환 3종 혼용, 앱 내에서도 혼용 |
| HTTP 상태 코드 | 🟡 보통 | 상수 사용은 대체로 양호, 201/200 생성 불일치 + 2개 모듈 하드코딩 |
| 에러 응답 형식 | 🔴 낮음 | 표준 envelope vs `{error}` vs `{message}` vs `{status}` 4종, 핸들러 우회 만연 |
| 페이지네이션 | 🔴 낮음 | 전역 설정 부재, 다수 목록이 무제한 반환, 구현 방식 3종 분산 |

---

## 앱별 응답 패턴 매트릭스

성공 응답 봉투(Envelope) 기준. `🟢 표준 래핑` = `{success/data/meta}`, `🔵 부분 래핑` = `{results/count}` 등 임의 키, `⚪ 직접 반환` = `serializer.data`/`dict` 그대로.

| 모듈 | 성공 봉투 | 에러 형식 | 상태코드 방식 | 페이지네이션 | 뷰 타입 |
|------|:---:|------|:---:|------|------|
| `stocks/views.py` | 혼용 (🔵+⚪, 일부 `_meta`/`_source`) | `{error}` + 일부 `{error:{code,message,details}}` + 커스텀 예외 | `status.HTTP_*` | `StockListPagination`(1곳) 외 슬라이싱 | APIView + ListAPIView |
| `stocks/views_eod.py` | ⚪ 직접 (`json_data` 통째) | `{error}` | `status.HTTP_*` | 없음 (`[:50]`,`[:7]`) | APIView |
| `stocks/views_exchange.py` | 🟢 `{success,data,meta}` | `{error}` | `status.HTTP_*` (503 활용) | 없음 (max 100 검증) | APIView |
| `stocks/views_fundamentals.py` | 🟢 `{success,data,meta}` | `{error}` | `status.HTTP_*` | 없음 (limit clamp) | APIView |
| `stocks/views_indicators.py` | ⚪ 직접 dict | `{error}` | `status.HTTP_*` (404만) | 없음 | APIView |
| `stocks/views_market_movers.py` | ⚪ `serializer.data` | `{error}` | `status.HTTP_*` | 없음 (limit) | APIView |
| `stocks/views_mvp.py` | 🔵 `{mode,count,data}` + 일부 직접 | 암시적(`get_object_or_404`) | **`status` 미import** | 없음 (`[:20]`) | APIView |
| `stocks/views_screener.py` | 🟢 `{success,data,meta}` | `{error}` + serializer.errors | `status.HTTP_*` | 없음 (limit) | APIView |
| `stocks/views_search.py` | 🔵 `{count,results}` + `{valid,...}` | `{error}` + `{valid:false,error}` | `status.HTTP_*` (503) | 없음 (`[:10]`) | APIView |
| `users/views.py` | 혼용 (⚪ serializer.data + `{message}` + `{ok,user}` + `{results,pagination}`) | `{error}`/`{message}`/serializer.errors + DRF 예외(`{detail}`) | `status.HTTP_*` (201/204/207/429) | `Paginator` 수동(2곳), 나머지 `.all()`/`.filter()` 무제한 | APIView |
| `metrics/views.py` | — (빈 모듈) | — | — | — | 없음 |
| `portfolio/views.py` | — (레거시 빈 모듈, #65에서 제거) | — | — | — | 없음 |
| `portfolio/api/views.py` (coach E1~E6) | ⚪ `serializer.data` | `{error}` + `{error,scope}` + `{error,type}` | `status.HTTP_*` (성공 **200**, 429/502/500) | 없음 (단건) | `@api_view` 함수형 |
| `chain_sight/views.py` | — (빈 모듈) | — | — | — | 없음 |
| `chain_sight/api/views.py` | ⚪ 직접 dict (`_sanitize_neo4j`) | `{error}` | `status.HTTP_*` (404/503) | `SignalFeedView` 수동(page/page_size), 나머지 무제한 | APIView |
| `market_pulse/views.py` | ⚪ `serializer.data`/dict + `{status,message}` | `{error}` + `{status,progress}` | `status.HTTP_*` (500 다수) | 없음 | APIView |
| `sec_pipeline/views.py` | ⚪ 직접 (`result` dict) | `{symbol,status,message}` 혼용 | **하드코딩 `status=200/202`** | 없음 (단건) | APIView |
| `serverless/views.py` | ⚪ 평탄 직접 | DRF 예외(`NotFound`/`PermissionDenied`/`ValidationError`) + 일부 `{error}` | `status.HTTP_*` (201 6곳) | 수동 offset/page_size + 일부 `.all()` 무제한 | `@api_view` + APIView 혼용 |
| `serverless/views_admin.py` | ⚪ 평탄 직접 | `{error}` (일관) | `status.HTTP_*` (201/204/429) | 없음 (`.all()` 무제한) | APIView |
| `news/views.py` | — (빈 모듈, 실제는 `news/api/`) | — | — | — | 없음 |
| `news/api/views.py` | ⚪ 평탄 직접 | `{error}`/`{status}`/`{message}` 혼용 + DRF `ValidationError` | `status.HTTP_*` (201) | `NewsArticlePagination`(ViewSet) + 수동 offset 혼용 | ViewSet + `@api_view` 혼용 |
| `rag_analysis/views.py` | 혼용 (⚪ serializer.data + `{message,items}`) | DRF 예외 위주(`{detail}`) + 커스텀 예외 | `status.HTTP_*` (201/204) | `Paginator`(history 1곳), 나머지 `.all()` 무제한 | APIView |
| `validation/views.py` | — (빈 모듈) | — | — | — | 없음 |
| `validation/api/views.py` | 혼용 (⚪ + `{symbol,...}` dict) | `{error}` + `{error,message}` + `{error,symbol}` | `status.HTTP_*` (404/422/400/401, 성공 **200**) | 없음 (`.all()`/`.filter()`/`.first()`) | APIView |
| `thesis/views/thesis_views.py` | ⚪ ViewSet 암시적 + `{status,thesis_id}` | `{error}` | `status.HTTP_*` (생성 암시적) | **pagination_class 없음** | ModelViewSet |
| `thesis/views/conversation_views.py` | ⚪ `Response(result)` | `{error}` | `status.HTTP_*` (400/401) | 없음 (대화형) | APIView |
| `thesis/views/monitoring_views.py` | 🔵 `{thesis,indicators,heatmap}` 등 | 암시적(`get_object_or_404`) | 암시적 200 | 없음 (`[:50]`,`.first()`) | APIView |
| `graph_analysis/views.py` (_dormant) | — (빈 모듈) | — | — | — | 없음 |
| `config/views.py` | ⚪ `JsonResponse` dict | 에러 경로 없음(health) | 암시적 200 | 없음 | 순수 함수 |
| `iron_trading/views.py` | ⚪ `payload` dict | `error_body(...)` 커스텀 | **하드코딩 `status=400/404/503/200`** | 없음 (단건) | APIView |

**관찰**: 완전 표준 봉투(`{success,data,meta}`)는 **stocks의 exchange/fundamentals/screener 3개 모듈에만** 일관 적용되어 있다. 나머지는 직접 반환 또는 임의 키 부분 래핑이며, 동일 앱 내(`stocks/`, `users/`)에서도 패턴이 갈린다.

---

## HTTP 상태 코드 일관성

### 양호한 점
- **전역 커스텀 EXCEPTION_HANDLER 등록됨** (`config/settings.py:373` → `config.exception_handler.custom_exception_handler`). DRF 예외는 `status_code`가 envelope에 포함된다.
- 대부분 모듈이 `from rest_framework import status` 후 `status.HTTP_*` **상수**를 사용 (하드코딩 매직넘버 회피).
- 풍부한 상태 코드 활용 사례: `users/views.py`의 207(다중 상태, L580)/204/429, `coach`의 502(LLM 게이트웨이)/429(예산 초과), `exchange`의 503.

### 불일치 항목
| # | 문제 | 위치 | 상세 |
|---|------|------|------|
| H-1 | **POST 생성 시 201 vs 200 불일치** | coach `portfolio/api/views.py`(성공 200, L108 등), `thesis_views`, `market_pulse/DataSyncView`(L368, 200), `validation/api`(L508 등 200) ↔ `users/views.py`(L108·303 201), `rag_analysis`(L63·141·303 201), `serverless`(201 6곳) | 리소스 생성 의미론 혼선. 클라이언트가 201 기대 불가 |
| H-2 | **`status` 모듈 미import** | `stocks/views_mvp.py` (L9에서 `Response`만 import) | 4xx 명시 반환 불가, 404는 `get_object_or_404`에 의존 |
| H-3 | **상태 코드 하드코딩 정수** | `sec_pipeline/views.py` (`status=200`/`202`, L49·53·55), `iron_trading/views.py` (`status=400/404/503/200`, L36·41·45·50) | 프로젝트 컨벤션(`status.HTTP_*`) 위반, 가독성/검색성 저하 |
| H-4 | **성공 상태 코드 암시적 의존** | chain_sight/api, market_pulse, indicators, thesis 다수 | `status=` 생략 → 기본 200. 의도된 200인지 누락인지 구분 불가 |
| H-5 | **404 처리 방식 혼재** | `raise NotFound`(serverless, users, rag) ↔ `get_object_or_404`(mvp, monitoring) ↔ 수동 `Response({error}, 404)`(chain_sight, validation, search) | 동일 의미(미발견)에 3가지 경로 → 에러 봉투도 갈림(아래 참조) |

---

## 에러 응답 형식

### 표준 envelope (정의됨, `config/exception_handler.py`)
```json
{ "status_code": 404, "detail": "...", "code": "error", "errors": { ... } }
```
- **적용 조건**: DRF 예외가 뷰 밖으로 **전파될 때만** 핸들러가 가로채 변환한다.
- `raise NotFound(...)`, `raise ValidationError(...)`, `raise PermissionDenied(...)` → ✅ 표준 envelope.
- 적극 활용 모듈: `serverless/views.py`(`NotFound`/`PermissionDenied`/`ValidationError`), `rag_analysis/views.py`, `news/api/views.py`(일부), `users/views.py`(일부).

### 표준을 우회하는 형식들 (수동 `Response(...)` 반환)
커스텀 핸들러는 **수동 반환 Response를 건드리지 않는다.** 아래는 모두 정책 envelope을 따르지 않는다:

| 형식 | 사용처(예시) | 비고 |
|------|------|------|
| `{"error": "<msg>"}` | stocks 전반, chain_sight/api, market_pulse, coach, serverless_admin, validation/api, thesis | **가장 흔한 비표준 형식**. `detail` 아닌 `error` 키 |
| `{"error": {"code","message","details"}}` | `stocks/views.py` StockOverview (L654) | 자체 중첩 구조 (또 다른 변종) |
| `{"error","scope"}` / `{"error","type"}` | coach `portfolio/api/views.py` (LLM 예산/오류) | 추가 메타 키 |
| `{"message": "<msg>"}` | `users/views.py`(AddFavorite 등), `news/api`(no_report) | `error`와 혼용 |
| `{"status": ..., "message": ...}` | `sec_pipeline`(L43-50), `market_pulse/SyncStatus`(L408), `news/api`(L1248) | 에러를 200+status 필드로 표현 |
| `{"valid": false, "error": ...}` | `stocks/views_search.py` SymbolValidate (L116) | 도메인 특화 변종 |
| `{"symbol":..., "error":...}` / `{"error","message"}` | `validation/api/views.py` (L82·84·110) | 또 다른 변종 |
| `serializer.errors` (필드별 dict) | `users/views.py`, `stocks/views_screener.py`(L70) | DRF 표준이나 envelope `errors` 키와 형태 상이 |
| `error_body(...)` 커스텀 함수 | `iron_trading/views.py` | 독자 헬퍼 |

**핵심 결론**: 명문화된 표준이 존재하나(2026-05-12 audit P0 #14), **실제 에러 응답의 다수는 `{"error": ...}` 수동 반환으로 표준을 우회**한다. 같은 "미발견" 에러가 엔드포인트에 따라 `{"detail":...,"code":...}`(예외 전파) 또는 `{"error":...}`(수동) 또는 `{"valid":false,...}`로 돌아온다. 프론트엔드는 두세 가지 파싱 분기를 유지해야 한다(메모리상 `authAxios` 단일 인터셉터에서 에러 정규화 부담).

---

## 페이지네이션 현황

### 전역 설정
- `config/settings.py`의 `REST_FRAMEWORK`에 **`DEFAULT_PAGINATION_CLASS`와 `PAGE_SIZE`가 없음** (L355-374 확인).
- ⇒ `ListAPIView`/`ViewSet`을 써도 **자동 페이지네이션이 발생하지 않는다.** 페이지네이션은 전적으로 뷰별 수동 구현에 의존.

### 구현 방식 3종 분산
| 방식 | 사용처 | 비고 |
|------|------|------|
| DRF `PageNumberPagination` | `stocks/views.py` `StockListPagination`(L92, ListAPIView 1곳), `news/api/views.py` `NewsArticlePagination`(L55, ViewSet) | 표준 메타(`count/next/previous/results`) 봉투. 그러나 단 2곳 |
| `django.core.paginator.Paginator` 수동 | `users/views.py`(Watchlist 2곳, `{results,pagination}` 봉투), `rag_analysis/views.py`(UsageHistory L783) | 자체 메타 형식 |
| 수동 `page`/`page_size`/`offset` 슬라이싱 | `chain_sight/api`(SignalFeed, `has_next`), `serverless/views.py`(L1048·1187), `news/api`(all_news L468, advanced_screener) | `has_next`/`offset` 등 메타 형식 제각각 |

### 페이지네이션 없이 전체 반환 (성능/응답크기 위험)
| 위치 | 쿼리 | 위험도 |
|------|------|:---:|
| `users/views.py` `Users.get()` (L92-95) | `User.objects.all()` 직접 반환 | 🔴 사용자 증가 시 무제한 |
| `users/views.py` `UserFavorites.get()` (L195) | `.all()` | 🟡 |
| `users/views.py` `PortfolioListCreateView.get()` (L269) | `.filter()` 전체 | 🟡 |
| `users/views.py` `UserInterestListCreateView.get()` (L1045) | `.filter()` 전체 | 🟡 |
| `rag_analysis/views.py` (L52, L429) | `DataBasket`/`AnalysisSession` `.filter()` 전체 (prefetch) | 🟡 사용자별 누적 증가 |
| `validation/api/views.py` (L52·106·237·536) | `.all()`/`.filter()`/`.first()` 직접 | 🟡 |
| `serverless/views.py` (L695·788·951) | `MarketBreadth`/`SectorPerformance`/screener `.all()` order_by | 🟡 시계열 누적 |
| `serverless/views_admin.py` (L505·764) | `NewsCollectionCategory.objects.all()`, SP500 전체 | 🟢 카디널리티 제한적이나 무제한 패턴 |
| `chain_sight/api/views.py` (SignalFeed 외 전부) | limit 파라미터만, 페이지네이션 X | 🟡 |
| `market_pulse/views.py` 전체 | Serializer 통과 후 전량 | 🟢 데이터셋 작으나 패턴 일관성 결여 |

> 슬라이싱(`[:20]`, `[:50]`, `[:10]`)으로 상한만 둔 곳(`stocks/views_eod`, `views_mvp`, `views_search`, `thesis/monitoring`)은 무제한은 아니나, 페이지 이동/total count 메타가 없어 "잘린 목록"을 클라이언트가 인지할 수 없다.

---

## 권고사항

> 모두 제안이며, 본 감사는 코드를 수정하지 않았다. 우선순위는 영향도×재발위험 기준.

### P0 — 에러 응답 단일화 (이미 표준이 있으므로 정합화)
1. **`{"error": ...}` 수동 반환을 DRF 예외 전파로 전환.** `return Response({"error": msg}, status=404)` → `raise NotFound(msg)` 식으로 바꾸면 `config.exception_handler`가 자동으로 `{detail, code, status_code}` envelope를 생성한다. 표준이 이미 `docs/features/api_envelope/policy.md`에 명문화되어 있으므로 **새 표준 정의가 아니라 기존 표준 준수**가 핵심.
2. **`{"message": ...}`, `{"status": ...}`, `{"valid": false, "error": ...}` 등 변종 제거** 또는 envelope의 `detail`/`errors`로 흡수.
3. 변환이 어려운 도메인 예외(coach의 `scope`/`type`, LLM 예산 등)는 envelope의 `code` + `errors` 확장 필드로 표현 통일.

### P1 — 페이지네이션 표준화
4. **`REST_FRAMEWORK`에 `DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE` 설정.** 그러면 신규 `ListAPIView`/`ViewSet`이 자동 페이지네이션된다.
5. **무제한 `.all()`/`.filter()` 반환 목록(특히 `users`, `rag_analysis`, `serverless`, `validation/api`)에 페이지네이션 적용.** 사용자/시계열 데이터 누적으로 응답 크기가 선형 증가하는 곳 우선.
6. **수동 페이지네이션 메타 형식 통일.** `Paginator` 수동(2곳), `offset/page_size`(3곳), DRF 표준(2곳)이 각기 다른 키(`pagination`/`has_next`/`next`)를 노출 → DRF `PageNumberPagination` 메타로 수렴 권장.

### P2 — 성공 응답 봉투 정책 결정
7. **봉투 정책을 명시적으로 택일.** 현재 `{success,data,meta}` 완전 래핑(stocks 3개 모듈)과 직접 반환(대다수)이 공존. 둘 중 하나를 프로젝트 표준으로 `DECISIONS.md`에 못 박고 `contracts/` 스펙과 정합화. (DRF 관례상 "직접 반환 + 표준 에러 envelope" 쪽이 마이그레이션 비용이 낮음 — 성공 응답 대부분이 이미 직접 반환.)

### P3 — 상태 코드 정리
8. **하드코딩 정수 → `status.HTTP_*` 전환**: `sec_pipeline/views.py`, `iron_trading/views.py`.
9. **`stocks/views_mvp.py`에 `status` import 추가** 후 명시적 4xx 반환.
10. **POST 생성 엔드포인트 201 통일**: coach·thesis·market_pulse·validation의 생성 응답을 201로 정렬(생성이 아닌 액션 트리거는 200/202 유지).

### 참고 — 빈 모듈 (정리 후보)
`metrics/views.py`, `portfolio/views.py`(레거시 의도적 보존), `chain_sight/views.py`, `news/views.py`, `validation/views.py`, `graph_analysis/views.py`(_dormant)는 실 코드가 없다. `portfolio/views.py`(#65 호환 보존) 외에는 제거/정리 검토 가능.

---

### 부록 — 분석 대상 (28개 모듈)
실질 분석 22개 + 빈 모듈 6개(`metrics`, `portfolio`, `chain_sight`, `news`, `validation`, `graph_analysis`).
근거 파일: `config/settings.py:355-374`(REST_FRAMEWORK), `config/exception_handler.py:1-58`(envelope 핸들러), `docs/features/api_envelope/policy.md`(정책 §4).
