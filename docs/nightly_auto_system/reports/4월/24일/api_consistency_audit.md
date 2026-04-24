# API 응답 일관성 감사 보고서

**감사일**: 2026-04-25
**대상**: Stock-Vis Django REST Framework 백엔드 전체 views
**감사 파일 수**: 24개 (14개 앱)
**감사 방법**: 읽기 전용 정적 분석 (코드 수정 없음)

---

## 요약

Stock-Vis 백엔드의 API 응답 형식은 **앱별로 서로 다른 4가지 패턴이 혼재**하여 프론트엔드 타입 일관성과 클라이언트 에러 처리에 장애가 되고 있다. 같은 정보를 조회하더라도 앱에 따라 `{'success': True, 'data': ..., 'meta': ...}`, `{'symbol': ..., 'data': ...}`, `serializer.data` 원본 등 구조가 달라지고, 에러 키는 `error` / `detail` / `message`가 혼용된다. DRF 공식 `pagination_class` 사용은 **전체 0건**이며, `REST_FRAMEWORK` 설정에도 `DEFAULT_PAGINATION_CLASS`가 누락되어 있다.

### 핵심 지표

| 항목 | 상태 | 수치 |
|------|------|------|
| 성공 응답 래핑 패턴 | 🔴 불일치 | 4가지 패턴 (success 래퍼 5개 파일 / 커스텀 dict 13개 / serializer 직접 3개 / JsonResponse 1개) |
| 에러 응답 키 통일 | 🔴 불일치 | `error` (주류) + `detail` (DRF 자동) + `message` (users/macro/sec_pipeline) + `status` (sec_pipeline) 혼용 |
| HTTP 201 사용 | 🟡 부분 준수 | users/rag_analysis 준수, stocks/thesis POST는 200 |
| `status` 모듈 사용 | 🟡 부분 준수 | 13개 파일 준수, `sec_pipeline/views.py`·`serverless/views.py:2879`만 숫자 하드코딩 |
| 페이지네이션 표준화 | 🔴 미준수 | DRF `pagination_class` 사용 **0건**, `DEFAULT_PAGINATION_CLASS` 설정 없음 |

### 핵심 발견

1. **표준 래퍼 사용은 소수**: `{'success': True, 'data': ..., 'meta': ...}` 패턴은 5개 파일(stocks/views_exchange.py, views_screener.py, views_fundamentals.py, rag_analysis/views.py, serverless/views.py)에만 적용됨. 헬퍼 함수는 `rag_analysis/views.py`의 `create_success_response()`/`create_error_response()`가 유일한 사례이며 다른 앱에서 재사용되지 않음.
2. **DRF 공식 페이지네이션 0건**: `pagination_class` 지정과 `PageNumberPagination` 사용 **0곳**. 대신 `django.core.paginator.Paginator`(users/rag_analysis 3곳)와 수동 `offset/limit`(serverless/news/chainsight), 하드코딩 슬라이싱(`[:10]`, `[:20]`, `[:50]`, `[:7]`)이 혼재.
3. **201/200 혼용**: users L910/L1032는 `status.HTTP_201_CREATED if added else status.HTTP_200_OK`로 조건부 분기. stocks/views.py:986의 `StockSyncAPIView.post`는 성공도 200. thesis/views/thesis_views.py:143의 `close` 액션은 생성성 side effect(ValidityRecord)가 있으나 기본 200.
4. **빈 views.py 6개**: `metrics/views.py`, `graph_analysis/views.py`, `validation/views.py`, `chainsight/views.py`, `news/views.py` — 모두 Django 스캐폴딩 기본 내용만 존재. URL 라우팅은 하위 `api/views.py` 또는 다른 모듈로 위임됨.
5. **에러 응답 구조 4종 혼재**: `{'error': str}`(대부분) / `{'error': {'code', 'message', 'details'}}`(stocks/rag_analysis/serverless) / `{'message': str}`(users/macro/sec_pipeline) / `{'detail': str}`(DRF 예외 자동).
6. **sec_pipeline 안티패턴**: `status=202`, `status=200` 숫자 하드코딩 + 모든 상태를 HTTP 200으로 반환하면서 `{'status': 'collecting' / 'available'}` JSON 필드로 상태 전달 (HTTP 프로토콜 무시).
7. **config/views.py는 DRF 이탈**: `api_root`, `health_check`가 `JsonResponse`를 직접 사용. DRF `@api_view` 적용 안 됨.

---

## 앱별 응답 패턴 매트릭스

### 성공 응답 래핑 패턴

| 앱 / 파일 | 주 패턴 | 부 패턴 | 일관성 | 비고 |
|-----------|---------|---------|--------|------|
| `stocks/views.py` | 직접 dict(`symbol`,`data`,`_source`) | 구조화 에러 | 🟡 혼용 | 차트/재무/검색마다 다름 |
| `stocks/views_exchange.py` | **`{'success', 'data', 'meta'}`** | - | 🟢 일관 | 표준 래퍼 |
| `stocks/views_screener.py` | **`{'success', 'data', 'meta'}`** | - | 🟢 일관 | Enhanced/Instant 모두 래퍼 사용 |
| `stocks/views_market_movers.py` | `serializer.data` 직접 | - | 🟡 래핑 없음 | |
| `stocks/views_eod.py` | `snapshot.json_data` 또는 custom dict(`signal_id, date, count, stocks`) | - | 🔴 래핑 없음 | JSON Baking 결과 그대로 |
| `stocks/views_indicators.py` | 직접 dict | - | 🟡 | |
| `stocks/views_search.py` | `{'count', 'results'}` | - | 🟡 | Screener/Watchlist와 필드 불일치 |
| `stocks/views_fundamentals.py` | **`{'success', 'data', 'meta'}`** | - | 🟢 일관 | 표준 래퍼 |
| `stocks/views_mvp.py` | `{'mode', 'count', 'data'}` | - | 🟡 | 고유 래퍼 |
| `users/views.py` | 혼용 (직접 serializer / `{'results', 'pagination'}` / `{'message', 'stock'}`) | - | 🔴 혼용 | 5종 이상 |
| `macro/views.py` | `serializer.data` 직접 | `{'status', 'message'}` (sync 엔드포인트) | 🟡 혼용 | |
| `news/api/views.py` | 커스텀 dict (`symbol, count, articles`) | - | 🟡 래핑 없음 | 엔드포인트별 다름 |
| `config/views.py` | `JsonResponse` (DRF 아님) | - | ⚠️ DRF 이탈 | |
| `rag_analysis/views.py` | **`{'success', 'data', 'meta'}`** (헬퍼) | - | 🟢 일관 | `create_success_response()` |
| `serverless/views.py` | **`{'success', 'data'}`** | - | 🟢 일관 | 명시적 래핑 |
| `serverless/views_admin.py` | 서비스 응답 직접 반환 | 일부 래퍼 | 🔴 혼용 | Admin만 예외적 |
| `validation/api/views.py` | 직접 dict (`symbol`, `fiscal_year`, ...) | - | 🟡 래핑 없음 | |
| `chainsight/api/views.py` | 직접 dict (`center`, `nodes`, `edges`, `meta`) | - | 🟡 래핑 없음 | |
| `sec_pipeline/views.py` | 서비스 dict 직접 | `{'symbol', 'status', 'message'}` | 🟡 래핑 없음 | |
| `thesis/views/thesis_views.py` | ViewSet 자동 serializer | `{'status', 'thesis_id'}` (close) | 🟡 | |
| `thesis/views/conversation_views.py` | 직접 dict | - | 🟡 래핑 없음 | |
| `thesis/views/monitoring_views.py` | 중첩 dict `{'thesis', 'indicators', 'heatmap'}` / `{'alerts', 'unread_count'}` | - | 🟡 | |
| `metrics/views.py` | 구현 없음 (빈 파일) | - | - | |
| `graph_analysis/views.py` | 구현 없음 (빈 파일) | - | - | |

**범례**: 🟢 일관 / 🟡 혼용 또는 래핑 없음 / 🔴 명확한 불일치 / ⚠️ 구조적 이탈

### 패턴 집계

| 패턴 | 사용 파일 수 | 예시 파일 |
|------|-------------|-----------|
| `{'success': True, 'data': ..., 'meta': ...}` | 5 | views_exchange/screener/fundamentals, rag_analysis, serverless |
| 커스텀 dict (앱별 고유 구조) | 13 | stocks/views.py, users, news/api, chainsight/api, thesis 3종, validation, sec_pipeline 등 |
| `serializer.data` 직접 반환 | 3 | views_market_movers, macro (대부분), users (Me/PublicUser 등) |
| `JsonResponse` (DRF 외) | 1 | config/views.py |
| 구현 없음 (빈 파일) | 6 | metrics, graph_analysis, validation, chainsight, news |

---

## HTTP 상태 코드 일관성

### 생성(POST) 201 vs 200

| 앱 | POST 201 준수 | 근거 | 비고 |
|----|---------------|------|------|
| `users/views.py` | 🟢 준수 | L105(회원가입), L288(portfolio), L631(watchlist 생성), L723(item 추가) | DRF 표준 |
| `users/views.py` (bulk) | 🟡 조건부 | L910, L1032: `HTTP_201_CREATED if added else HTTP_200_OK` | 일관성 저하 |
| `rag_analysis/views.py` | 🟢 준수 | L84, L164, L346, L455 | |
| `serverless/views.py` | 🟡 부분 준수 | L1060, L1428, L1819는 201. 일부 POST(L400 이하)는 200 암묵적 | |
| `serverless/views_admin.py` | 🟡 부분 준수 | L568만 201 | |
| `stocks/views.py` StockSyncAPIView | 🔴 미준수 | L986: `HTTP_200_OK if any_success else HTTP_500_INTERNAL_SERVER_ERROR` — 성공도 200 | |
| `thesis/views/thesis_views.py` | 🔴 미준수 | L143 close 액션: 기본 200, `{'status': 'closed'}` 반환 | |
| `sec_pipeline/views.py` | ⚠️ 독자 | L40: 202 Accepted, L44/46: 200 (비동기 트리거이므로 202는 정당) |

### `status` 모듈 사용 vs 하드코딩

| 앱 | `from rest_framework import status` 사용 | 비고 |
|----|----------------------------------------|------|
| `stocks/*` | 🟢 사용 | 모든 서브뷰 준수 |
| `users/views.py` | 🟢 사용 | |
| `macro/views.py` | 🟢 사용 | |
| `news/api/views.py` | 🟢 사용 | |
| `rag_analysis/views.py` | 🟢 사용 | |
| `serverless/views.py` | 🟡 대부분 사용 | L2879: `status=400` 숫자 하드코딩 1건 |
| `serverless/views_admin.py` | 🟢 사용 | |
| `validation/api/views.py` | 🟢 사용 | |
| `chainsight/api/views.py` | 🟢 사용 | |
| `thesis/views/thesis_views.py` | 🟢 사용 | L71, 78 |
| `config/views.py` | ⚠️ 사용하나 JsonResponse와 혼용 | |
| `sec_pipeline/views.py` | 🔴 하드코딩 | L40: `status=202`, L44: `status=200`, L46: `status=200` (정수 직접) |

### 에러 시 사용 코드 분포

| 코드 | 사용 빈도 | 용도 | 일관성 |
|------|----------|------|--------|
| 400 | 매우 높음 | 유효성 검증 실패 | 🟢 |
| 401 | 중 | 인증 실패 | 🟢 |
| 403 | 낮음 | 권한 없음 (serverless 주로) | 🟢 |
| 404 | 높음 | 리소스 없음 | 🟢 |
| 429 | 낮음 | Rate limit (stocks/views.py L928) | 🟢 |
| 500 | 중 | 서버 오류 | 🟢 |
| 503 | 낮음 | 외부 서비스 장애 (chainsight L615, stocks/views_exchange L58) | 🟢 |

**결론**: 상태 코드 *선택*은 일관되나, *생성 시 201 사용*과 *`status` 모듈 사용*은 앱별로 불일치.

---

## 에러 응답 형식

### 에러 키 분포

| 키 | 사용 앱 / 파일 | 예시 구조 |
|----|-----------------|-----------|
| `error` (문자열) | stocks 대부분, macro, news/api, validation/api, chainsight/api, thesis, stocks/views_search | `{'error': 'Stock not found'}` |
| `error` (구조화 dict) | `stocks/views.py` L587-596, `rag_analysis/views.py`, `serverless/views.py` L72-76, L1168, L1326 | `{'error': {'code': 'XXX', 'message': '...', 'details': {...}}}` |
| `error` (serializer.errors dict) | `stocks/views_screener.py` L66, `users/views.py` L107/L292/L329/L632 | `{'error': {...ValidationError dict...}}` 또는 `serializer.errors` 원본 |
| `detail` (DRF 기본) | `raise NotFound()`, `raise ValidationError()` → DRF 자동 변환 (users 23건, news/api 10건, rag_analysis 8건) | `{'detail': '...'}` |
| `message` | `users/views.py` L208/L216/L236, `macro/views.py` L281-404 (sync), `sec_pipeline/views.py` | `{'message': '...'}` |
| `error` + `message` 조합 | `validation/api/views.py` L65-66, L83-84, `users/views.py` L97 | `{'error': 'code', 'message': 'human readable'}` |
| `status` + `message` | `sec_pipeline/views.py` L38-39, `macro/views.py` sync 엔드포인트 | `{'status': 'collecting', 'message': '...'}` |

### 구조적 불일치 사례

1. **구조화 vs 단순형 혼용**
   - 구조화 (권장): `rag_analysis/views.py:46-59`의 `create_error_response("INVALID_INPUT", str(err))` 헬퍼
   - 단순형: `validation/api/views.py:67`의 `{'error': 'not_in_universe'}`
   - 동일 파일 내 혼용: `stocks/views.py` L596(구조화) vs L670(단순형)

2. **DRF 예외 vs 커스텀 Response**
   - DRF 예외(`raise ValidationError()`, `raise NotFound()`)는 자동으로 `{'detail': '...'}` 반환 → 프론트 기대 키와 다를 수 있음
   - users/news/rag_analysis 3개 앱에서 41회 `raise` 사용, 같은 앱 내 커스텀 Response는 `error` 키 사용 → 프론트는 두 경우 모두 대비 필요

3. **sec_pipeline의 이상 케이스**
   - `{'status': 'collecting', 'message': '...'}` (202)과 `{'status': 'available', ...}` (200), `{'status': <?>, ...}` (200)을 JSON 필드로 에러 구분
   - `result.get('status') == 'available'`이 아니어도 HTTP 200으로 반환(L46) → HTTP 프로토콜 우회, 클라이언트가 body 파싱해야 실패 감지

4. **users 즐겨찾기 API 안티패턴**
   - `{'message': 'This stock is already in your favorites'}` + `HTTP_400_BAD_REQUEST` (L208) → `error` 키 없이 `message`만 사용. 프론트에서 키 감지 불일치

---

## 페이지네이션 현황

### DRF `pagination_class` 사용 여부

**모든 views에서 `pagination_class` 명시적 사용: 0건** (`PageNumberPagination`, `CursorPagination`, `LimitOffsetPagination` import도 0건)

`config/settings.py:332-340`의 `REST_FRAMEWORK` 설정에도 `DEFAULT_PAGINATION_CLASS` 미설정 → 프로젝트 차원의 기본 페이지네이션이 존재하지 않음.

### 목록 API 페이지네이션 구현 방식

| 파일 / 엔드포인트 | 방식 | 상세 | 위험도 |
|-------------------|------|------|--------|
| `stocks/views.py` StockListAPIView | `generics.ListAPIView` 묵시적 | L75-105, 프로젝트 설정에 pagination 없음 → 실제로 페이지네이션 안 됨 | 🔴 전체 Stock 반환 |
| `stocks/views.py` 재무제표 3개 | **페이지네이션 없음** | L636-639, 710-713, 782-785: `.filter()[:limit]` 상한만 적용, 기본 5 | 🟡 |
| `stocks/views_screener.py` | 수동 `limit` 파라미터 | L126: `?limit=N` (기본 100, 최대 1000), 페이지 없음 | 🟡 |
| `stocks/views_search.py` SymbolSearchView | **하드코딩 `[:10]`** | L56 | 🟡 |
| `stocks/views_eod.py` EODSignalDetailView | **하드코딩 `[:50]`** | L78 | 🟡 |
| `stocks/views_eod.py` EODPipelineStatusView | **하드코딩 `[:7]`** | L119 | 🟡 |
| `stocks/views_mvp.py` StockMVPListView | **하드코딩 `[:20]`** | L41 | 🟡 |
| `users/views.py` Users.get | **페이지네이션 없음** | L90-92: `User.objects.all()` 전체 반환 | 🔴 관리자용이라도 위험 |
| `users/views.py` Watchlist | **수동 Django `Paginator`** | L602-620, 메타: `{count, page, page_size, num_pages, has_next, has_previous}` | 🟡 비표준 |
| `users/views.py` WatchlistStocks | **수동 Django `Paginator`** | L822-840, 메타 동일 | 🟡 비표준 |
| `users/views.py` PortfolioList | **페이지네이션 없음** | L257-259: queryset 전체 반환 | 🔴 |
| `macro/views.py` 전체 | 페이지네이션 없음 | 단건/소량 조회 | 🟢 |
| `news/api/views.py` stock_news | **하드코딩 `[:limit]`** | limit min(100) | 🟡 |
| `news/api/views.py` /news/all | **수동 `offset/limit` + `has_more`** | L418-432, 메타: `{source, category, days, total, count, offset, limit, has_more}` | 🟡 비표준 |
| `news/api/views.py` /trending | **하드코딩 `[:limit]`** | L327-348 | 🟡 |
| `news/api/views.py` alerts | `AlertLog.objects.all()` 필터 후 수동 | L2109 | 🟡 |
| `validation/api/views.py` PresetList | 페이지네이션 없음 | L426-451, 프리셋 소량이라 허용 | 🟢 |
| `chainsight/api/views.py` 이웃 조회 | **수동 슬라이싱** | L578-579: `neighbors[:limit]` | 🟡 |
| `chainsight/api/views.py` SignalFeedView | **수동 `page/page_size`** | `page = max(int(...), 1)`, `page_size = min(..., 20)` | 🟡 비표준 |
| `thesis/views/monitoring_views.py` AlertListView | **하드코딩 `[:50]`** | L238 | 🟡 |
| `thesis/views/conversation_views.py` NewsIssuesView | **하드코딩 `[:12]`** | L201 | 🟡 |
| `rag_analysis/views.py` UsageHistoryView | **수동 Django `Paginator`** | L796-826, 메타: `{current_page, page_size, total_pages, total_count, has_next, has_previous}` | 🟡 비표준 |
| `serverless/views.py` FilterEngine 계열 | **수동 `offset/limit`** | L1175-1176, L1312-1316, 메타: `{current_page, total_pages, count, total_count, next, previous}` | 🟡 비표준 |
| `serverless/views.py` L1017, L2248 | `.all()` 후 수동 페이지네이션 | ScreenerPreset, ETFProfile | 🟡 |
| `serverless/views_admin.py` L478 | `NewsCollectionCategory.objects.all()` 전체 | 카테고리 소량이라 허용 | 🟢 |

### 메타 필드명 불일치

| 소스 | 메타 필드 |
|------|-----------|
| `rag_analysis/views.py` UsageHistoryView | `current_page`, `page_size`, `total_pages`, `total_count`, `has_next`, `has_previous` |
| `serverless/views.py` advanced screener | `current_page`, `total_pages`, `count`, `total_count`, `next` (URL), `previous` (URL) |
| `users/views.py` Watchlist/WatchlistStocks | `count`, `page`, `page_size`, `num_pages`, `has_next`, `has_previous` |
| `chainsight/api/views.py` SignalFeed | `page`, `page_size` (total 없음) |
| `news/api/views.py` /news/all | `total`, `count`, `offset`, `limit`, `has_more` |

→ **필드명 5가지 변형**: `current_page` vs `page`, `page_size` vs (없음), `total_count` vs `count` vs `total_pages` vs `num_pages` vs `total`.

### 🔴 잠재 성능 위험 지점

1. `stocks/views.py` StockListAPIView (L85) → `Stock.objects.all()` 후 DRF 기본 페이지네이션 없어 **전체 Stock 반환 가능성**.
2. `stocks/views.py` 재무제표 3개(BalanceSheet/IncomeStatement/CashFlow) → `[:limit]`만 적용, 기본 5개로 작지만 `limit` 상한 없음.
3. `users/views.py` PortfolioList (L257-259) → 사용자 포트폴리오 전체 반환.
4. `users/views.py` Users.get (L90) → `User.objects.all()` 관리자용이나 전체 로드.
5. `stocks/views_mvp.py` StockMVPListView (L29, 41) → `[:20]` 하드코딩, 페이지 이동 불가.

---

## 권고사항

### High 우선순위 (P0 — 서비스 품질·DX 직접 영향)

1. **성공 응답 래퍼 표준화**
   - **표준안 제시**: `rag_analysis/views.py`의 `create_success_response()`/`create_error_response()` 헬퍼를 `config/response.py`(또는 `utils/`) 공용 모듈로 승격
   - 응답 구조:
     ```json
     {
       "success": true,
       "data": {...} | [...],
       "meta": {"request_id": "...", "timestamp": "...", "pagination": {...}}
     }
     ```
   - 에러 구조:
     ```json
     {
       "success": false,
       "error": {"code": "ERROR_CODE", "message": "human readable", "details": {...}}
     }
     ```
   - **적용 대상**: 표준 래퍼를 쓰지 않는 18개 파일 (단계적 마이그레이션: stocks/views.py → thesis → chainsight → validation 순)

2. **페이지네이션 표준 확립**
   - `config/pagination.py`에 `StandardPageNumberPagination(PageNumberPagination)` 정의 (page_size=20, max_page_size=100)
   - `settings.REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']`에 기본값 설정
   - 목록 API 16곳의 수동 `[:N]` 슬라이싱과 `Paginator` 수동 래핑을 DRF `pagination_class`로 교체
   - stocks/views.py StockListAPIView, PortfolioList, 재무제표 조회 3종 우선 적용

3. **에러 키 단일화**
   - DRF 관례와 프로젝트 다수결인 `error` 사용. `detail`은 DRF 기본 예외가 자동 생성하므로, 커스텀 exception handler로 `{'error': {'code', 'message'}}`로 변환
   - `users/views.py` 즐겨찾기 API의 `{'message': ...}`, `sec_pipeline/views.py`의 `{'status', 'message'}` 패턴을 `error/success` 표준으로 통일

### Medium 우선순위 (P1 — 일관성·유지보수성)

4. **POST 생성 시 201 Created 강제**
   - `stocks/views.py:986`(`StockSyncAPIView`), `thesis/views/thesis_views.py:143`(`close` 액션), `users/views.py:910/1032`의 조건부 201/200 구간 리뷰
   - 단, 비동기 태스크 트리거는 202 Accepted 사용 허용 (`sec_pipeline:40`)

5. **`status` 모듈 사용 강제**
   - `sec_pipeline/views.py:40-46`의 하드코딩된 `status=200/202` → `status.HTTP_200_OK` / `status.HTTP_202_ACCEPTED`로 교체
   - `serverless/views.py:2879`의 `status=400` 교체
   - pre-commit / ruff rule로 `Response(..., status=숫자)` 패턴 차단

6. **페이지네이션 메타 필드명 통일**
   - 표준: `{current_page, page_size, total_pages, total_count, has_next, has_previous}` (rag_analysis 기준, DRF 기본과 정합)
   - OpenAPI 스펙(`contracts/`)에 반영 후 프론트 공유 타입 업데이트

7. **DRF 예외 → 표준 응답 매핑**
   - `config/exceptions.py`에 `custom_exception_handler` 정의
   - `NotFound`, `ValidationError`, `PermissionDenied` 등을 `{'success': False, 'error': {'code': ..., 'message': ...}}`로 변환
   - `REST_FRAMEWORK['EXCEPTION_HANDLER']`에 등록
   - users(23건), news/api(10건), rag_analysis(8건)에 즉시 효과

### Low 우선순위 (P2 — 코드 품질·정리)

8. **빈 views.py 정리**
   - `metrics/views.py`, `graph_analysis/views.py`, `validation/views.py`, `chainsight/views.py`, `news/views.py` → 사용하지 않으면 삭제, 플레이스홀더면 주석 명시

9. **`config/views.py`의 `JsonResponse` → DRF `Response` 마이그레이션**
   - `api_root`(L12-70), `health_check`(L73-82)를 `@api_view(['GET'])` 데코레이터 기반으로 변경

10. **`serverless/views_admin.py` 래핑 적용**
    - 현재 서비스 응답 직접 반환 구간 → 표준 래퍼 적용

11. **sec_pipeline HTTP 프로토콜 준수**
    - `result.get('status') != 'available'`인 경우 적절한 4xx/5xx 사용하거나 202 유지 시 body 구조 명확화

### 마이그레이션 전략 제안

| 단계 | 범위 | 기대 효과 |
|------|------|-----------|
| Phase 1 | `config/response.py` 헬퍼 + `config/exceptions.py` 핸들러 + `config/pagination.py` 표준 Pagination 클래스 추가 (기존 코드 무변경) | 기반 마련 |
| Phase 2 | 신규 API는 헬퍼 강제. 기존 중 **사용 빈도 높은 3개 앱**(stocks/users/thesis) 우선 마이그레이션 | DX 개선 |
| Phase 3 | StockListAPIView/재무제표/포트폴리오 조회의 DRF pagination 적용 | 성능 리스크 해소 |
| Phase 4 | 나머지 앱 마이그레이션 + 프론트 공유 타입(`contracts/shared-types.ts`) 업데이트 | 전면 일관성 확보 |

---

## 부록: 감사 대상 파일 목록

```
stocks/views.py, views_exchange.py, views_screener.py, views_market_movers.py,
stocks/views_eod.py, views_indicators.py, views_search.py, views_fundamentals.py, views_mvp.py
users/views.py
macro/views.py
news/views.py (빈 파일), news/api/views.py
config/views.py
rag_analysis/views.py
serverless/views.py, serverless/views_admin.py
validation/views.py (빈 파일), validation/api/views.py
chainsight/views.py (빈 파일), chainsight/api/views.py
sec_pipeline/views.py
thesis/views/__init__.py, thesis_views.py, conversation_views.py, monitoring_views.py
graph_analysis/views.py (빈 파일)
metrics/views.py (빈 파일)
```

**총 24개 파일, 그 중 6개 빈 파일(`# Create your views here.`만 존재)**

### 검증한 정적 증거

- `grep` 결과: `'success': True/False` 사용 파일 = 3개 (serverless/views.py, serverless/views_admin.py, stocks/views.py)
- `create_success_response` 정의·호출: rag_analysis/views.py 내부에서만 사용
- `pagination_class`·`PageNumberPagination` import: 전체 0건
- `from django.core.paginator import Paginator`: users/views.py, rag_analysis/views.py 2곳
- `raise NotFound|ValidationError|ParseError|PermissionDenied`: users(23), news/api(10), rag_analysis(8) = 총 41건
- `status=숫자 하드코딩`: sec_pipeline/views.py L40/44/46, serverless/views.py L2879
- `config/settings.py:332-340` REST_FRAMEWORK에 `DEFAULT_PAGINATION_CLASS` 없음 확인

---

*본 보고서는 읽기 전용 정적 분석 결과이며, 코드 수정은 수행되지 않았다.*
