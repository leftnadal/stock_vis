# API 응답 일관성 감사 보고서

- **감사 일자**: 2026-05-23
- **감사 대상**: Stock-Vis 전체 Django REST Framework 백엔드 뷰 파일
- **감사 축**: (A) 응답 래핑 패턴, (B) HTTP 상태 코드, (C) 에러 응답 형식, (D) 페이지네이션
- **전체 일관성 점수**: 3/10

---

## 1. 요약

Stock-Vis 백엔드는 18개 이상의 앱에 걸쳐 API 응답 형식이 심각하게 파편화되어 있다. `success/data/meta` 표준 래퍼를 일관되게 사용하는 앱은 3개(stocks/views_fundamentals, stocks/views_screener, stocks/views_exchange)에 불과하며, 나머지 앱은 직접 반환, 커스텀 딕셔너리, ViewSet 기본 반환이 혼재한다. HTTP 상태 코드는 대체로 상수를 사용하나 sec_pipeline에서 정수 리터럴 사용이 확인되었다. 에러 메시지는 영문/국문 혼용이 15개 파일 이상에서 확인된다. 페이지네이션은 ThesisViewSet에서 누락이 확인되어 데이터 증가 시 위험하다.

---

## 2. 앱별 응답 패턴 매트릭스 (A축)

| 앱 / 파일 | success/data/meta | 직접 반환 | 커스텀 dict | 비고 |
|---|---|---|---|---|
| stocks/views_fundamentals.py | 전체 (L89, L148, L197, L242, L297) | - | - | 가장 일관적 |
| stocks/views_screener.py | 전체 (L94, L150, L280, L329, L385, L434, L490) | - | - | 일관적 |
| stocks/views_exchange.py | 전체 (L68, L117, L194, L238, L288) | - | - | 일관적 |
| stocks/views.py | 일부 | 일부 | symbol/tab/data 래퍼 (재무탭) | 혼용 — L183 `result` vs L193 `results` 오타 포함 |
| stocks/views_eod.py | - | 일부 (L48 `snapshot.json_data`) | `{'logs': data}` (L135) | 혼용 |
| stocks/views_mvp.py | - | - | `{'mode':..., 'count':..., 'data':...}` | hard cap `[:20]` |
| stocks/views_indicators.py | - | 전체 (L197, L261, L372) | - | 영문 에러 메시지 |
| stocks/views_market_movers.py | - | 전체 (L69 `serializer.data`) | - | |
| stocks/views_search.py | - | - | `{'count':..., 'results':...}` (L74, L171) | `{'valid': True/False, ...}` (L124/119) |
| news/api/views.py | - | 전체 (ViewSet) | 일부 커스텀 | `{'symbol':..., 'articles':...}` (L110) |
| users/views.py | - | 일부 | `{"ok": "...", "user": ...}` login (L168) | `{"ok"...}` 유일 |
| macro/views.py | - | 전체 (L40, L65 등) | `{'status': 'already_running', ...}` | 영문 에러 |
| rag_analysis/views.py | - | 전체 | `{'results':..., 'pagination':...}` (L727) | SSE 스트리밍 포함 |
| validation/api/views.py | - | - | `{'status':'ok', 'mode':..., 'preset_key':...}` (L487) | 422 사용 |
| chainsight/api/views.py | - | - | `_sanitize_neo4j({...})` 패턴 | 영문 에러 |
| serverless/views.py | - | 일부 | `{'date':..., 'type':..., 'movers':...}` (L98) | 혼용 |
| thesis/views/thesis_views.py | - | 일부 | `{'status':'closed', 'thesis_id':...}` (L144) | ViewSet, pagination_class 미설정 |
| thesis/views/monitoring_views.py | - | - | `{'thesis':{...}, 'indicators':[...], 'heatmap':{...}}` (L205) | |
| thesis/views/conversation_views.py | - | 전체 | - | `{'error': '...'}` (L163, L178) |
| sec_pipeline/views.py | - | - | `{'symbol':..., 'status':..., 'data':...}` | 정수 리터럴 status=202 |
| config/views.py | - | - | JsonResponse (DRF Response 아님) (L19, L77) | DRF 렌더링 미적용 |
| graph_analysis/views.py | 해당 없음 | - | - | 빈 스텁 |
| metrics/views.py | 해당 없음 | - | - | 빈 스텁 |
| chainsight/views.py | 해당 없음 | - | - | 빈 스텁 |

**결론**: `success/data/meta` 표준 래퍼를 완전히 준수하는 파일은 3개뿐이며, 나머지 21개 파일은 직접 반환 또는 앱별 고유 커스텀 딕셔너리를 사용한다.

---

## 3. HTTP 상태 코드 일관성 (B축)

### 3-1. 올바른 2xx 사용 사례

| 위치 | 코드 | 설명 |
|---|---|---|
| users/views.py:107 | 201 | 유저 POST 생성 |
| users/views.py:639 | 201 | Watchlist 아이템 추가 |
| users/views.py:559 | 207 | RefreshStockDataView 부분 성공 |
| rag_analysis/views.py:62 | 201 | RAG 분석 POST 생성 |
| serverless/views.py:919 | 201 | screener preset POST 생성 |
| validation/api/views.py:67 | 422 | S&P 500 비포함 종목 (비표준 활용) |
| chainsight/api/views.py | 503 | GraphConnectionError |
| stocks/views_exchange.py | 503 | 외부 API 연결 실패 |

### 3-2. 문제 있는 상태 코드 사례

| 위치 | 현재 코드 | 권장 코드 | 문제 설명 |
|---|---|---|---|
| stocks/views.py:996 (StockSyncAPIView.post) | 200 (성공 시), 500 (전체 실패 시) | 202 Accepted 또는 명확한 분기 | sync 실패여도 `sync_status='failed'` 포함 200 반환 — 성공/실패 구분 불가 |
| serverless/views.py DELETE screener_alert_detail | 200 + `{'message': 'Alert deleted successfully'}` | 204 No Content | DELETE 성공은 204가 REST 표준 |
| sec_pipeline/views.py:46 | `status=202` (정수 리터럴) | `status=status.HTTP_202_ACCEPTED` | 매직 넘버 사용 — 코딩 규칙 위반 |
| macro/views.py DataSyncView.post() | 200 + `{'status': 'already_running', ...}` | 409 Conflict 또는 202 Accepted | 이미 실행 중임을 오류 없이 200으로 처리 |

### 3-3. DELETE 204 미사용 현황

- `users/views.py` WatchlistItemDeleteView: 204 올바르게 사용
- `rag_analysis/views.py` DELETE: 204 올바르게 사용
- `serverless/views.py` screener_alert_detail DELETE: **200 오사용** — `{'message': 'Alert deleted successfully'}` 반환

### 3-4. 상태 코드 상수 vs 정수 리터럴

전체 파일 중 `sec_pipeline/views.py:46` 1건만 정수 리터럴(`status=202`) 사용 확인. 나머지는 `status.HTTP_*` 상수 사용.

---

## 4. 에러 응답 형식 (C축)

### 4-1. 에러 키 이름 현황

| 패턴 | 사용 위치 | 건수 |
|---|---|---|
| `{'error': '문자열'}` | stocks/views.py, views_indicators, views_search, macro, chainsight, thesis/conversation, serverless, users | ~15개 파일 (가장 많음) |
| `{'error': {'code':..., 'message':..., 'details':...}}` 중첩 | stocks/views.py:596 (StockOverviewAPIView), stocks/views.py:930 (StockSyncAPIView) | 2곳만 사용 — 고유 형식 |
| `{'detail': '...'}` (DRF 기본) | raise_exception=True 사용 시 DRF 자동 생성 | rag_analysis, thesis, validation, news |
| `{"ok": "Welcome!", "user": ...}` | users/views.py:168 (login 성공) | 1곳만 — 유일한 "ok" 키 |
| `{'valid': False, 'error': '...'}` | stocks/views_search.py:119 | 1곳만 |
| `{'status': 'no_report', 'message': '...'}` | news/api/views.py (ml_shadow_report) | 1곳만 |

### 4-2. 에러 메시지 언어 혼용

**영문 에러 메시지 사용 파일:**

| 파일 | 예시 |
|---|---|
| stocks/views_indicators.py | `'No price data available for {symbol}'` |
| users/views.py:173 | `"Wrong username or password"` |
| macro/views.py | `'Failed to fetch market data'` |
| chainsight/api/views.py:71, 118, 194, 354 | `'Stock not found in graph'`, `'Graph service unavailable'` |
| news/api/views.py:693 | `f'No completed keywords for {target_date}'` |
| news/api/views.py:699 | `f'Invalid index {index}...'` |

**한국어 에러 메시지 사용 파일:**

| 파일 | 예시 |
|---|---|
| thesis/views/ | `'테제를 찾을 수 없습니다'` |
| validation/api/views.py | `'S&P 500에 포함된 종목이 아닙니다'` |
| serverless/views.py (신규 코드) | 일부 한국어 |

**결론**: 같은 프로젝트에서 영문/국문이 혼용되며 통일 기준이 없다. 신규 코드일수록 한국어 경향이 있으나 일관성 없음.

### 4-3. `detail` vs `error` vs `message` 키 불일치

- DRF `raise_exception=True` → `detail` 키 자동 생성
- 직접 작성한 에러 → `error` 키 사용
- 일부 응답 → `message` 키 사용 (serverless 성공 메시지에서도 혼용)
- 동일 앱 내에서도 `error`와 `detail`이 혼재 (rag_analysis: serializer 에러는 `detail`, 직접 작성은 `error`)

---

## 5. 페이지네이션 현황 (D축)

### 5-1. 페이지네이션 올바르게 적용된 엔드포인트

| 위치 | 방식 | 페이지 크기 |
|---|---|---|
| stocks/views.py StockListAPIView | PageNumberPagination (page_size=50, max=200) | 50 |
| news/api/views.py NewsArticlePagination | PageNumberPagination (page_size=20, max=100) | 20 |
| users/views.py WatchlistListCreateView | 수동 Django Paginator | 20 |
| rag_analysis/views.py UsageHistoryView | 수동 Paginator, `{'results':..., 'pagination':{...}}` (L727) | 20 |

### 5-2. 페이지네이션 누락 — 위험 엔드포인트

| 위치 | 문제 | 위험도 |
|---|---|---|
| thesis/views/thesis_views.py ThesisViewSet | `pagination_class` 미설정, ModelViewSet 기본 전체 반환 | 높음 — 가설 증가 시 전체 반환 |
| stocks/views_mvp.py StockMVPListView:41 | `queryset[:20]` 하드 캡, 실제 페이지네이션 없음 | 중간 — 20개 고정 |
| news/api/views.py collection_logs 액션 | offset/limit 파라미터 있으나 list 직접 반환 | 중간 |

### 5-3. DEFAULT_PAGINATION_CLASS 설정 확인

`config/settings.py`를 별도 확인하지 않았으나, DRF 기본값은 `None`이므로 `ThesisViewSet`처럼 `pagination_class`를 명시하지 않은 ViewSet은 전체 queryset을 반환한다. 각 뷰에서 명시적으로 설정하거나 전역 기본값 설정이 필요하다.

---

## 6. 권고사항

### 우선순위 1 — 즉시 수정 (기능 정확성 영향)

| # | 위치 | 문제 | 수정 방향 |
|---|---|---|---|
| R-01 | stocks/views.py:183 | `'result': []` vs L193 `'results': []` 오타 불일치 | `results`로 통일 |
| R-02 | stocks/views.py:996 (StockSyncAPIView) | 동기화 실패여도 200 반환 — 클라이언트 오류 감지 불가 | 실패 시 400/500 명확히 분기 |
| R-03 | serverless/views.py DELETE screener_alert_detail | 200 + body 반환 | 204 No Content로 변경 |
| R-04 | sec_pipeline/views.py:46 | `status=202` 정수 리터럴 | `status=status.HTTP_202_ACCEPTED`로 변경 |
| R-05 | thesis/views/thesis_views.py ThesisViewSet | `pagination_class` 미설정 | `PageNumberPagination` 추가 |

### 우선순위 2 — 단기 개선 (일관성 향상)

| # | 위치 | 문제 | 수정 방향 |
|---|---|---|---|
| R-06 | users/views.py:168 | `{"ok": "Welcome!"}` 비표준 키 | `{"success": true, "message": "..."}` 또는 DRF 표준화 |
| R-07 | macro/views.py DataSyncView | already_running을 200으로 반환 | 409 Conflict 또는 명확한 상태 분리 |
| R-08 | config/views.py | JsonResponse 직접 사용 (DRF 렌더링 미적용) | DRF Response로 통일 |
| R-09 | 전체 | 에러 키 `error` / `detail` / `message` 혼용 | 프로젝트 표준 하나 선택 후 통일 |

### 우선순위 3 — 장기 리팩토링 (구조적 일관성)

| # | 대상 | 방향 |
|---|---|---|
| R-10 | stocks/views.py, views_eod, views_indicators 등 | `success/data/meta` 표준 래퍼 순차 적용 |
| R-11 | 전체 영문 에러 메시지 | 한국어 통일 또는 i18n 도입 결정 |
| R-12 | stocks/views_mvp.py | `[:20]` 하드 캡을 PageNumberPagination으로 교체 |
| R-13 | news/api/views.py collection_logs | offset/limit 파라미터 실제 페이지네이션으로 연결 |

---

## 7. 핵심 발견 요약

1. **응답 래퍼 표준 채택률 14%** — 3/21개 파일만 `success/data/meta` 완전 준수
2. **에러 키 3종 혼용** — `error`, `detail`, `message` 동시 사용, 프로젝트 표준 없음
3. **DELETE 204 미준수 1건** — serverless/views.py screener_alert_detail
4. **정수 리터럴 상태 코드 1건** — sec_pipeline/views.py:46
5. **페이지네이션 누락 1건 (위험)** — ThesisViewSet, 가설 증가 시 전체 반환
6. **언어 불일치** — 영문 에러 6개 파일, 한국어 3개 파일, 혼용 다수
7. **유일 키 패턴 2건** — `"ok"` (users login), 중첩 `error.code` (stocks overview/sync만)
