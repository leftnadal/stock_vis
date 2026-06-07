# API 응답 일관성 감사 보고서

> **감사 일자**: 2026-06-07
> **범위**: 전체 `views*.py` (28개 파일, 약 14,400줄) — DRF View의 `Response()` 반환 형식
> **방식**: 읽기 전용 정적 분석 (코드 수정 없음). 앱 그룹 5개를 병렬 분석 후 종합
> **대상 앱**: stocks, serverless, market_pulse, portfolio, chain_sight, news, rag_analysis, sec_pipeline, validation, thesis, users, metrics, api_request, config, iron_trading, graph_analysis(dormant)

---

## 요약

전체 API 표면에 **단일한 응답 컨트랙트가 존재하지 않는다.** `{'success': True, 'data': ...}` 형태의 표준 envelope는 **28개 파일 어디에도 없으며**, 대신 4~6종의 서로 다른 응답 형식이 앱별·파일별·뷰별로 혼재한다. 핵심 발견 4가지:

1. **응답 래핑 — 4개 진영으로 분열**
   - `{success, data, meta}` envelope: stocks의 exchange/fundamentals/screener 3개 파일만
   - `{_meta, <도메인키>}` envelope: market_pulse v2(`api/views/*`)만
   - serializer.data **직접 반환**(벌거벗은): rag_analysis, portfolio coach, market_movers 등
   - 도메인별 **평탄 dict**(`{count, <plural>}` 등): serverless, news, validation, thesis 등 (지배적)
   - → 프론트엔드가 뷰마다 `res.data` vs `res.data.data` vs `res.data._meta`를 다르게 파싱해야 함

2. **HTTP 상태 코드 — 대체로 양호하나 2가지 누수**
   - `status.HTTP_*` 상수 사용이 표준(하드코딩 숫자 거의 없음). **예외 3곳**: `sec_pipeline`(200/202 하드코딩), `iron_trading`(200/400/404/503 하드코딩), `market_pulse/cards.py`(404 하드코딩)
   - **201 누수**: 생성(POST) 응답이 201을 일관되게 쓰지 못함. serverless thesis 생성·admin action·news 생성 액션·conversation start 등이 200으로 샘

3. **에러 형식 — 3종 파편화 + soft-error 패턴**
   - `{'error': ...}`: serverless admin, market_pulse v1, validation, thesis, users, api_request, chain_sight (지배적)
   - `{'detail': ...}`: DRF 예외(`NotFound`/`ValidationError`) 위임 — rag_analysis, serverless views.py, chain_sight/watchlist (정석)
   - `{'message': ...}`: users/views.py가 일부 400 응답에 사용 (혼용 사고)
   - **위험: status code 없이 200 body에 `{"error": ...}`를 흘리는 soft-error** — validation, chain_sight TraceView, news 다수

4. **페이지네이션 — 사실상 부재**
   - DRF `PageNumberPagination`을 `pagination_class`로 실제 설정한 곳: **stocks `StockListAPIView` 1곳 + news `NewsViewSet` 1곳**(후자도 커스텀 @action엔 미적용)
   - 나머지 목록 API는 전부 `[:N]` 슬라이스 상한 / `limit` 클램프 / 수동 `Paginator` / 무제한 `.all()` 통째 반환으로 분산
   - **최대 노출**: screener `limit` 최대 1000개 단일 응답 가능

> **종합 등급**: 상태 코드는 **양호(B)**, 응답 래핑·에러 형식은 **불량(D)**, 페이지네이션은 **취약(D-)**. 데이터 규모가 작은 user/peer-scoped 도메인이 많아 실질 장애 위험은 낮으나, 프론트엔드 계약 비용과 신규 엔드포인트 추가 시 형식 표류 위험이 구조적으로 누적되고 있다.

---

## 앱별 응답 패턴 매트릭스

| 앱 / 파일 | 뷰 종류 | 응답 래핑 | 에러 형식 | 상태코드 방식 | 201 사용 | 페이지네이션 |
|-----------|---------|-----------|-----------|---------------|----------|--------------|
| **stocks/views.py** | APIView+generics | 평탄 dict (envelope 키 제각각) | `{error}` (일부 중첩 `{error:{code,message}}`) | `status.HTTP_*` | ✗(Sync도 200) | PageNumberPagination 1곳 |
| stocks/views_eod.py | APIView | raw JSON 통과 / `{count, stocks}` | `{error}` | `status.HTTP_*` | N/A | `[:50]`/`[:7]` 슬라이스 |
| stocks/views_exchange.py | APIView | **`{success, data, meta}`** ✅ | `{error}` | `status.HTTP_*` | ✗(Batch 200) | 없음(serializer many) |
| stocks/views_fundamentals.py | APIView | **`{success, data, meta}`** ✅ | `{error}` | `status.HTTP_*` | N/A | limit 클램프 ≤40 |
| stocks/views_indicators.py | APIView | 평탄 dict | `{error}` (영문 메시지) | `status.HTTP_*` | ✗ | 없음(상한도 없음) |
| stocks/views_market_movers.py | APIView | **serializer.data raw** | `{error}` | `status.HTTP_*` | N/A | limit 클램프 ≤20 |
| stocks/views_mvp.py | APIView | 평탄 dict (**camelCase**) | DRF `{detail}`(404만) | status **미사용** | N/A | `[:20]` 하드 슬라이스 |
| stocks/views_screener.py | APIView | **`{success, data, meta}`** ✅ | `{error}` (일부 `{error: serializer.errors}`) | `status.HTTP_*` | N/A | limit 클램프 **≤1000** ⚠️ |
| stocks/views_search.py | APIView | 평탄 dict | `{error}` (일부 도메인 필드 혼합) | `status.HTTP_*` | N/A | `[:10]` 슬라이스 |
| **serverless/views.py** | 함수형 `@api_view` ~40 | 평탄 dict / serializer.data raw 혼재 | **DRF 예외(`detail`/field)** | `status.HTTP_*` | △(preset/alert 201, thesis 200) | 없음(수동 slice + FilterEngine 자작) |
| serverless/views_admin.py | APIView ×11 | 평탄 dict / 서비스 dict raw | **`{error}` 직접 반환** | `status.HTTP_*` | △(category 201, action 200) | 없음(전체 `.all()` 통째) |
| **market_pulse/api/views/cards.py** | APIView | `{_meta, data}` | `{error}` | **raw 404** ⚠️ | N/A | `[:30]` 슬라이스 |
| market_pulse/api/views/health.py | APIView | `{_meta, probes, last_runs}` | 페이로드 `ok:False` | 200만 | N/A | N/A |
| market_pulse/api/views/i18n.py | APIView | `{_meta, labels}` | `_meta.warning` (200) | 200만 | N/A | N/A |
| market_pulse/api/views/news_refresh.py | APIView | `{_meta, items}` | 없음 | 200(POST) | ✗(픽 작업) | 고정 LIMIT=6 |
| market_pulse/api/views/overview.py | APIView | `{_meta, ticker_bar, news, anomaly, cards}` | `_meta.status` (200) | 200만 | N/A | limit=6 |
| market_pulse/views.py (macro v1) | APIView ×10 | **serializer.data / service dict raw** | `{error}` | `status.HTTP_*` | ✗(Sync 200) | 외부 API 통째 |
| **portfolio/views.py** | 빈 stub | N/A (legacy 전수 제거) | N/A | N/A | N/A | N/A |
| portfolio/api/views.py | 함수형 `@api_view` ×6 | **serializer.data raw** | `{error}` + scope/type (검증은 DRF) | `status.HTTP_*` (429/502 세분화) | ✗(POST LLM) | N/A |
| **chain_sight/api/views.py** | APIView ×7 | 평탄 dict (키 제각각) | `{error}` (Trace는 200+error ⚠️) | `status.HTTP_*` | ✗(GET only) | **수동 page/page_size 슬라이싱** |
| chain_sight/views/watchlist_views.py | ModelViewSet | serializer.data / service dict raw | **`{detail}`** | `status.HTTP_*` | ✅(create 201) | ModelViewSet 전역설정 의존 |
| **news/api/views.py** | ReadOnlyModelViewSet (god, ~30 action) | 도메인 dict / raw list 혼재 | DRF `ValidationError` + `{error}` 혼용 | `status.HTTP_*` | ✗(생성 액션도 200) | **PageNumberPagination(list만)** + 액션 `[:limit]` |
| news/views.py | 빈 stub | N/A | N/A | N/A | N/A | N/A |
| **rag_analysis/views.py** | APIView ×13 | **serializer.data raw / 도메인 dict** | **DRF 예외(`detail`/field)** ✅ | `status.HTTP_*` | ✅(201/204 일관) | 없음(통째) + UsageHistory 수동 Paginator |
| **sec_pipeline/views.py** | APIView ×1 (+HTML) | 서비스 result dict raw | 분기 없음 | **하드코딩 200/202** ⚠️ | ✗(202 Accepted) | N/A |
| **validation/api/views.py** | APIView ×7 | 도메인 dict | **`{error}` (status 누락 200 soft-error 다발)** ⚠️ | `status.HTTP_*` (401/422 사용) | ✗(POST 200) | 없음(통째) + LLM `[:50]` |
| validation/views.py | 빈 stub | N/A | N/A | N/A | N/A | N/A |
| **thesis/views/conversation_views.py** | APIView ×4 | service dict raw / `{issues}` | `{error}` + DRF 검증 혼재 | `status.HTTP_*` | ✗(start 200) | `[:12]` 슬라이스 |
| thesis/views/monitoring_views.py | APIView ×4 | named-key dict | `get_object_or_404` → `{detail}` | 200만 | N/A | `[:50]` 슬라이스 |
| thesis/views/thesis_views.py | ModelViewSet ×3 | CRUD 기본 / 액션 dict | `{error}` + DRF 혼재 | `status.HTTP_*` | ✅(ViewSet 자동 201) | 전역설정 의존 |
| **users/views.py** | APIView ×17 | **6종 이상 shape 공존** ⚠️ | **`{error}` + `{message}` + DRF 혼용** ⚠️ | `status.HTTP_*` (207도 사용) | ✅(동적 201/200 분기) | **수동 Paginator**(Watchlist만) + 나머지 통째 |
| users/jwt_views.py | APIView ×7 | named-key dict (`{user,tokens,message}`) | `{error}` / 성공 `{message}` (일관) | `status.HTTP_*` | ✅(signup 201) | N/A |
| **metrics/views.py** | 빈 stub | N/A | N/A | N/A | N/A | N/A |
| **api_request/admin_views.py** | APIView ×6 | 서비스 dict raw | `{error}` (`str(e)` 노출 ⚠️) | `status.HTTP_*` | ✗(POST 200) | N/A |
| **config/views.py** | 순수 Django 함수형 | `JsonResponse` (DRF 아님) | 없음(문자열 상태) | 200(JsonResponse) | N/A | N/A |
| **iron_trading/views.py** | APIView ×1 | 서비스 payload raw | **`error_body(code, message)` 단일계약** ✅ | **하드코딩 200/400/404/503** ⚠️ | ✗(외부봇) | 서비스 레벨 limit |
| graph_analysis/views.py (dormant) | 빈 stub | N/A | N/A | N/A | N/A | N/A |

> **빈 stub 5개**: portfolio/views.py, news/views.py, validation/views.py, metrics/views.py, graph_analysis/views.py — 실제 뷰는 `api/views.py` 또는 분할 모듈에 위치하거나 legacy 제거됨.

---

## HTTP 상태 코드 일관성

### 양호한 점
- **`status.HTTP_*` 상수 사용이 표준**. 대부분의 파일에서 하드코딩 숫자(`status=400`)는 0건이다. serverless 두 파일(3,800줄)도 상수만 사용.

### 하드코딩 숫자 사용처 (3건 — 이탈)
| 파일 | 하드코딩 코드 | 비고 |
|------|---------------|------|
| `sec_pipeline/views.py` | `status=202`, `status=200` (L49/L53/L55) | `status.HTTP_*` 전혀 안 씀 |
| `iron_trading/views.py` | 200/400/404/503 (L36~L50) | 외부 봇용 계약 API, 의도적 설계로 보임 |
| `market_pulse/api/views/cards.py` | `status=404` (L84) | 같은 그룹 overview는 `_meta.status` 사용 |
| `stocks/views_mvp.py` | `status` import만 하고 **미사용** | 모든 응답 암묵 200 |

### 201(Created) 일관성 — **누수 다발**
생성 시 201을 일관되게 쓰는 파일은 소수다.

| 201을 올바르게 쓰는 곳 | 201을 써야 하나 200으로 새는 곳 |
|------------------------|--------------------------------|
| rag_analysis (201/204 완비) ✅ | serverless `generate_thesis` (L1758) — 200 |
| users/jwt signup (L120) ✅ | serverless `AdminActionView.post` (L412) — 200 |
| users/views.py (L108/303/669/774) ✅ | news 생성성 @action (generate_daily_keywords 등) — 200 |
| serverless preset/alert (L974/L1284) ✅ | conversation `/start/`, `/suggest/` POST — 200 |
| serverless_admin category (L625) ✅ | validation PeerPreference POST (L609) — 200 |
| watchlist create (L90), thesis ViewSet 자동 | (coach/macro/news_refresh POST는 비생성이라 200이 타당) |

> 즉 **생성 의미론(201)이 "DRF가 자동으로 해주는 경로"(ModelViewSet/CreateAPIView)에서만 보장**되고, 함수형 `@api_view`로 직접 만든 생성 응답은 대부분 200으로 흐른다.

### 삭제(204) 일관성
- **올바른 204**: rag_analysis(L101/164/479), users(L348/719/806/1169), serverless_admin category(L746)
- **204 대신 메시지+200**: serverless views.py의 DELETE — `{"message": "...deleted"}` + 200 (L1025/L1321)

### 에러 코드 분포
- 400(BAD_REQUEST): 전 앱 광범위
- 401(NotAuthenticated): serverless(L1275/1567/1846), validation(L581/615), users
- 403(PermissionDenied): serverless(L1007/1019/1305 등)
- 404(NotFound): 광범위
- 422(UNPROCESSABLE_ENTITY): **validation만 사용** (L85) — 그룹 내 유일
- 429(TOO_MANY_REQUESTS): serverless_admin 쿨다운(L378), stocks(L1025), portfolio coach budget
- 502(BAD_GATEWAY): **portfolio coach만** — LLM 실패 세분화 (가장 정교)
- 503(SERVICE_UNAVAILABLE): stocks exchange/search(외부데이터 없음), chain_sight(GraphConnectionError), iron_trading
- 207(MULTI_STATUS): **users/views.py만** bulk 응답 (L580)

> **빈 데이터 처리 불일치**: 같은 "데이터 없음" 상황을 stocks exchange/search는 **503**, fundamentals/screener는 **404**, news/validation은 **200+빈배열**로 서로 다르게 매핑한다.

---

## 에러 응답 형식

### 3종 키가 파편화

| 에러 키 | 사용 파일 | 비고 |
|---------|-----------|------|
| **`{'error': ...}`** (지배적) | serverless_admin, market_pulse v1, validation, thesis, users, jwt, api_request, chain_sight/api, stocks 대부분 | 값 타입 불안정: 문자열 / 중첩 dict / `serializer.errors` 혼재 |
| **`{'detail': ...}`** (DRF 정석) | rag_analysis, serverless/views.py, chain_sight/watchlist, monitoring(`get_object_or_404`) | DRF 예외(`NotFound`/`ValidationError`) raise로 자동 생성 |
| **`{'message': ...}`** | users/views.py 일부 400 (L219/249) | `error`와 같은 400 상황에서 혼용 — **사고성 불일치** |
| **`error_body(code, message)`** | iron_trading | 유일한 명시적 단일 계약 ✅ |
| **`{'error': {code, message, details}}`** | stocks/views.py Overview/Sync (L653/L1016) | 같은 파일 내 평탄 `{error: str}`과 혼용 |

### DRF 기본 예외 vs 커스텀 dict — 정반대 두 진영
- **DRF 예외 진영** (정석): rag_analysis, serverless/views.py — `raise NotFound/ValidationError/PermissionDenied` + 커스텀 도메인 예외(APIException 상속) → 본문이 `detail`/필드 기반으로 자동 통일
- **커스텀 dict 진영**: serverless_admin, validation, api_request — `try/except → Response({"error": str(e)}, status=500)` 직접 반환
- **같은 serverless 앱 안에서 views.py(DRF 예외) vs views_admin.py(`{error}` 직접)가 정반대** — 앱 내부 컨트랙트 분열의 대표 사례

### 위험 패턴 1 — status code 없는 soft-error (200으로 에러 전달)
프론트가 HTTP status가 아닌 body를 까봐야 에러를 알 수 있는 구조:
- `validation/api/views.py`: `{"error":"insufficient_peers"}`(L418), `{"symbol","error":"no_leader"}`(L433), `parsed["error"]`(L673) — status 누락 다발
- `chain_sight/api/views.py` TraceView: 예외 시 `200 + {found:False, error:str(e)}` (L288)
- `news/api/views.py`: `{"status":"no_report","message":...}` status 없이 (L1248), 404 상황을 200+빈데이터로 (L167/594)

### 위험 패턴 2 — 내부 예외 메시지 노출
- `api_request/admin_views.py`, `serverless_admin`: `Response({"error": str(e)}, status=500)`로 **`str(e)` 원문 노출** → 정보 누출 가능 (admin 전용이라 영향 제한적이나 패턴 자체가 위험)

---

## 페이지네이션 현황

### DRF 페이지네이터를 실제로 쓰는 곳 (2곳뿐)
| 위치 | 클래스 | 적용 범위 |
|------|--------|-----------|
| `stocks/views.py` `StockListAPIView` | `StockListPagination`(PageNumberPagination, page_size 50/max 200) | 전체 적용 ✅ |
| `news/api/views.py` `NewsViewSet` | `NewsArticlePagination`(PageNumberPagination) | **기본 list/retrieve만** — 커스텀 @action 30개엔 미적용 |

### 페이지네이션 "대용" 패턴 분류
1. **고정 슬라이스 상한** (`[:N]`): eod(`[:50]`/`[:7]`), search(`[:10]`), mvp(`[:20]`), cards(`[:30]`), conversation(`[:12]`), monitoring/alerts(`[:50]`), news_refresh(LIMIT=6), overview(limit=6)
2. **limit 쿼리 클램프**: fundamentals(≤40), market_movers(≤20), **screener(≤1000 ⚠️)**, news 액션(≤200)
3. **수동 Django `Paginator`**: users/views.py Watchlist 2곳, rag_analysis UsageHistory — `{results, pagination}` 커스텀 형식 (DRF `next`/`previous` URL 표준과 다름)
4. **수동 page/page_size 슬라이싱 + has_next 자작**: chain_sight SignalFeedView (L741)
5. **FilterEngine 자작 페이지네이션**: serverless screener — total_pages/current_page + 수동 next/previous URL 생성
6. **전역 설정 의존**: watchlist ViewSet, thesis ViewSet (`DEFAULT_PAGINATION_CLASS` 설정 여부에 좌우)

### 무제한 `.all()`/`.filter()` 통째 반환 (페이지네이션·상한 없음)
| 위치 | 대상 | 위험도 |
|------|------|--------|
| serverless `screener_presets_api` GET (L954) | 전체 활성 preset | 낮음(소규모) |
| serverless `screener_filters_api` (L1109) | 전체 활성 필터 | 낮음 |
| serverless `screener_alerts_api` GET (L1255) | 사용자 알림 전체 | 낮음(user-scoped) |
| serverless `etf_collection_status` (L1958) | 전체 ETFProfile 순회 | **중간**(증가 추세) |
| serverless_admin NewsCategory/SectorOptions | 전체 통째 | 낮음 |
| rag_analysis DataBasket/Session/Messages 목록 | user-scoped 전체 | 낮음 |
| validation presets/LeaderComparison | metric 전체 순회 | 낮음 |
| users Users/UserFavorites/Portfolio/UserInterest 목록 | 일부 user-scoped, 일부 전역 | 중간 |
| stocks `views_indicators` IndicatorComparison | **클라이언트가 보낸 symbols 전부 처리(상한 0)** | **중간**(DoS 표면) |

> **가장 큰 노출**: screener `limit ≤ 1000` 단일 응답 + indicators 무상한 symbol 루프. 둘 다 공개(`AllowAny`) 또는 인증 없이 접근 가능한 경로에서 대량 응답/연산을 유발할 수 있다.

---

## 권고사항

> 모두 **읽기 전용 감사 결과에 따른 제안**이며, 실제 적용은 별도 작업으로 분리한다. 우선순위는 "프론트 계약 비용 + 보안 표면"을 기준으로 산정.

### P1 — 즉시 정렬 권장 (낮은 비용, 높은 효과)
1. **에러 키 단일화 결정 필요**: `{'error'}` vs `{'detail'}` 중 하나를 프로젝트 표준으로 `DECISIONS.md`에 박는다. DRF 관용을 따른다면 `{'detail'}`(예외 raise) 권장. 현재 users/views.py의 `error`/`message` 혼용(L219 vs L455)은 명백한 버그성 불일치이므로 우선 정리.
2. **soft-error(200+error) 제거**: validation(L418/433/673), chain_sight TraceView(L288), news(L1248)의 "status 없이 body.error" 패턴은 클라이언트 에러 핸들링을 망가뜨린다. 적절한 4xx/5xx status를 부여한다.
3. **`str(e)` 노출 차단**: api_request/serverless_admin의 `Response({"error": str(e)}, 500)`을 일반화된 메시지 + 서버 로깅으로 교체(정보 누출 방지).

### P2 — 페이지네이션 가드레일
4. **무상한 응답에 상한 부여**: screener(현 ≤1000)를 합리적 page_size로 낮추고, `indicators` IndicatorComparison의 symbols 배열에 상한(예 ≤20)을 건다 — 공개 경로 DoS 표면 축소.
5. **공통 `PageNumberPagination` 기본값 검토**: 전역 `DEFAULT_PAGINATION_CLASS` 부재 시 ViewSet(watchlist/thesis) list가 통째 반환되므로, 설정 여부를 명시적으로 확정한다.

### P3 — 응답 래핑 표준 (대규모, 신중히)
6. **신규 엔드포인트부터 단일 envelope 채택**: 기존 4개 진영을 일괄 마이그레이션하는 것은 프론트 동시 변경을 요구하므로 위험. 대신 **신규 API는 한 가지 형식으로 통일**하고(예: stocks exchange/fundamentals/screener의 `{success, data, meta}` 또는 의도적 평탄 dict 중 택1), `contracts/` OpenAPI 스펙에 명문화하여 표류를 막는다.
7. **`count` 키 이름 통일**: serverless의 `count`/`total`/`total_count`/`total_institutions`/`total_peers`가 제각각 — 페이지네이션 메타 키 규약을 정한다.

### P4 — 상태 코드 마감
8. **201 누수 정리**: 함수형 `@api_view` 생성 응답(serverless thesis/action, news 생성 액션, conversation start)에 `status.HTTP_201_CREATED`를 부여한다.
9. **하드코딩 status 상수화**: sec_pipeline, cards.py의 raw 숫자를 `status.HTTP_*`로 교체(iron_trading은 외부 계약 API라 보존 검토 가능).
10. **빈 데이터 매핑 통일**: "데이터 없음"을 503/404/200 중 무엇으로 볼지 결정(외부 API 일시 장애=503, 리소스 부재=404, 정상 빈 목록=200 권장).

---

### 부록 — 분석 메타
- **분석 파일**: 28개 `views*.py` (빈 stub 5개 포함). 실제 뷰 보유 23개.
- **뷰 총량(추정)**: 함수형 `@api_view` ~46, APIView 클래스 ~90, ViewSet ~5, generics ~1
- **표준 envelope `{success, data}` 사용률**: stocks 3개 파일(`{success, data, meta}`) 외 0% — 전체 약 13%
- **DRF 페이지네이터 실사용률**: 2 / 23 파일 (약 9%)
- **참고 동급 보고서**: 같은 디렉토리의 `api_dependency_audit.md`, `api_docs_audit.md`, `data_integrity_audit.md`와 교차 검토 권장
