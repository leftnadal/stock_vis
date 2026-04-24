# API 응답 일관성 감사 보고서

**감사일**: 2026-04-24
**대상**: Stock-Vis Django REST Framework 백엔드 전체 views
**감사 파일 수**: 24개 (13개 앱)
**감사 방법**: 읽기 전용 정적 분석 (코드 수정 없음)

---

## 요약

Stock-Vis 백엔드의 API 응답 형식은 **앱별로 서로 다른 3~4가지 패턴이 혼재**하여 프론트엔드 타입 일관성과 클라이언트 에러 처리에 장애가 되고 있다. 동일한 정보를 요청해도 앱에 따라 `{'success': True, 'data': ...}`, `{'symbol': ..., 'data': ...}`, 또는 `serializer.data` 원본 등 구조가 달라지고, 에러 키는 `error` / `detail` / `message`가 혼용된다.

### 핵심 지표

| 항목 | 상태 | 수치 |
|------|------|------|
| 성공 응답 래핑 패턴 | 🔴 불일치 | 최소 4개 패턴 (success 래핑 / 커스텀 dict / serializer 직접 / JsonResponse) |
| 에러 응답 키 통일 | 🔴 불일치 | `error` (주류) + `detail` (DRF 기본) + `message` (users/macro/sec_pipeline) 혼용 |
| HTTP 201 사용 | 🟡 부분 준수 | users/rag_analysis는 준수, stocks/thesis POST는 200 반환 |
| `status` 모듈 사용 | 🟡 부분 준수 | 대부분 준수, `sec_pipeline/views.py`는 숫자 하드코딩 |
| 페이지네이션 표준화 | 🔴 미준수 | `pagination_class` 사용 0건, 모두 수동 `[:limit]` 또는 커스텀 Paginator |

### 핵심 발견

1. **성공 응답 래핑의 이원화**: `views_exchange.py` / `views_screener.py` / `views_fundamentals.py` / `rag_analysis/views.py` / `serverless/views.py`만 `{'success': True, 'data': ..., 'meta': ...}` 헬퍼 패턴을 쓰고, 나머지 18개 파일은 각자 다른 커스텀 dict를 반환한다.
2. **페이지네이션 미도입**: DRF `pagination_class`를 사용하는 엔드포인트가 전혀 없다. `users/views.py`와 `chainsight/api/views.py`는 수동 Paginator를, 나머지는 하드코딩된 `[:10]`, `[:20]`, `[:50]` 슬라이싱을 사용한다. 재무제표 조회는 제한 없이 전체 로드하는 구간이 있다 (잠재 성능 이슈).
3. **201/200 혼용**: users/rag_analysis는 POST 생성 시 `201 CREATED`를 준수하나, stocks/thesis/serverless 일부는 200을 반환한다.
4. **graph_analysis/views.py, validation/views.py, chainsight/views.py, news/views.py, metrics/views.py는 비어있음** — URL 라우팅은 하위 모듈(`api/views.py`)로 위임.
5. **에러 응답 구조 3종 혼재**: `{'error': str}` (대부분) / `{'error': {'code': ..., 'message': ..., 'details': ...}}` (stocks/rag_analysis/serverless) / `{'message': str}` (users 일부) / `{'detail': str}` (DRF 예외 자동).

---

## 앱별 응답 패턴 매트릭스

### 성공 응답 래핑 패턴

| 앱 / 파일 | 주 패턴 | 부 패턴 | 일관성 | 비고 |
|-----------|---------|---------|--------|------|
| `stocks/views.py` | 직접 dict | 커스텀 `{'results', 'count'}` | 🟡 혼용 | 차트/재무/검색별로 다름 |
| `stocks/views_exchange.py` | **`{'success', 'data', 'meta'}`** | - | 🟢 일관 | 표준 래퍼 사용 |
| `stocks/views_screener.py` | **`{'success', 'data', 'meta'}`** | - | 🟢 일관 | 표준 래퍼 사용 |
| `stocks/views_market_movers.py` | `serializer.data` 직접 | - | 🟡 래핑 없음 | |
| `stocks/views_eod.py` | `snapshot.json_data` 또는 dict | - | 🔴 구조 불명 | JSON Baking 결과 그대로 |
| `stocks/views_indicators.py` | 직접 dict | - | 🟡 | |
| `stocks/views_search.py` | `{'count', 'results'}` | - | 🟡 | Screener와 필드 다름 |
| `stocks/views_fundamentals.py` | **`{'success', 'data', 'meta'}`** | - | 🟢 일관 | 표준 래퍼 사용 |
| `stocks/views_mvp.py` | `{'mode', 'count', 'data'}` | - | 🟡 | 고유 래퍼 |
| `users/views.py` | 혼용 (직접 + `{'results', 'pagination'}` + `{'message', 'stock'}`) | - | 🔴 혼용 | |
| `macro/views.py` | `serializer.data` 직접 | `{'status', 'message'}` (sync) | 🟡 혼용 | |
| `news/api/views.py` | 커스텀 dict (`symbol, count, articles`) | - | 🟡 래핑 없음 | 엔드포인트별 다름 |
| `config/views.py` | `JsonResponse` (DRF 아님) | - | ⚠️ DRF 이탈 | |
| `rag_analysis/views.py` | **`{'success', 'data', 'meta'}`** (헬퍼 함수) | - | 🟢 일관 | `create_success_response()` |
| `serverless/views.py` | **`{'success', 'data'}`** | - | 🟢 일관 | 명시적 래핑 |
| `serverless/views_admin.py` | 서비스 응답 직접 반환 | - | 🔴 래핑 없음 | Admin만 예외 |
| `validation/api/views.py` | 직접 dict (`symbol, data_fiscal_year, ...`) | - | 🟡 래핑 없음 | |
| `chainsight/api/views.py` | 직접 dict (`center, nodes, edges, meta`) | - | 🟡 래핑 없음 | |
| `sec_pipeline/views.py` | 서비스 dict 직접 | - | 🟡 래핑 없음 | |
| `thesis/views/thesis_views.py` | 직접 dict | - | 🟡 래핑 없음 | |
| `thesis/views/conversation_views.py` | 직접 dict | - | 🟡 래핑 없음 | |
| `thesis/views/monitoring_views.py` | 중첩 dict `{'thesis', 'indicators', 'heatmap'}` | - | 🟡 | |
| `metrics/views.py` | 구현 없음 (빈 파일) | - | - | |
| `graph_analysis/views.py` | 구현 없음 (빈 파일) | - | - | |

**범례**: 🟢 일관 / 🟡 혼용 또는 래핑 없음 / 🔴 명확한 불일치 / ⚠️ 구조적 이탈

### 패턴 집계

| 패턴 | 사용 파일 수 | 예시 파일 |
|------|-------------|-----------|
| `{'success': True, 'data': ..., 'meta': ...}` | 5 | views_exchange/screener/fundamentals, rag_analysis, serverless |
| 커스텀 dict (앱별 고유 구조) | 13 | stocks/views.py, users, news/api, chainsight, thesis, validation, sec_pipeline 등 |
| `serializer.data` 직접 | 3 | market_movers, macro (대부분), users (일부) |
| `JsonResponse` (DRF 외) | 1 | config/views.py |
| 구현 없음 | 2 | metrics, graph_analysis |

---

## HTTP 상태 코드 일관성

### 생성(POST) 201 vs 200

| 앱 | POST 201 준수 | 근거 | 비고 |
|----|---------------|------|------|
| `users/views.py` | 🟢 준수 | L105(회원가입), L288(portfolio), L631(watchlist), L723(add-item) | DRF 표준 |
| `users/views.py` (bulk) | 🟡 조건부 | L910, L1032: 상황에 따라 201 또는 200 | 일관성 저하 |
| `rag_analysis/views.py` | 🟢 준수 | L84, L164, L346, L455 | |
| `serverless/views.py` | 🟡 부분 준수 | L1060, L1428는 201. 일부 POST(L400-408)는 200 암묵적 | |
| `stocks/views.py` | 🔴 미준수 | L986 StockSyncAPIView: POST 성공도 200 | |
| `thesis/views/thesis_views.py` | 🔴 미준수 | L143: POST 생성도 기본 200 | |
| `sec_pipeline/views.py` | ⚠️ 독자 | L40: 202 Accepted, L44: 200 (비동기 처리라 202는 정당할 수 있음) | |

### `status` 모듈 사용 vs 하드코딩

| 앱 | `from rest_framework import status` 사용 | 비고 |
|----|----------------------------------------|------|
| `stocks/*` (대부분) | 🟢 사용 | `status.HTTP_400_BAD_REQUEST` 등 |
| `users/views.py` | 🟢 사용 | |
| `macro/views.py` | 🟢 사용 | |
| `rag_analysis/views.py` | 🟢 사용 | |
| `serverless/views.py` | 🟢 사용 | |
| `validation/api/views.py` | 🟢 사용 | |
| `chainsight/api/views.py` | 🟢 사용 | |
| `thesis/views/thesis_views.py` | 🟢 사용 | L71, 78 |
| `sec_pipeline/views.py` | 🔴 하드코딩 | L40: `status=202`, L44: `status=200` (정수 직접) |

### 에러 시 사용 코드 분포

| 코드 | 사용 빈도 | 용도 | 일관성 |
|------|----------|------|--------|
| 400 | 매우 높음 | 유효성 검증 실패 | 🟢 |
| 401 | 중 | 인증 실패 | 🟢 |
| 403 | 낮음 | 권한 없음 (serverless 주로) | 🟢 |
| 404 | 높음 | 리소스 없음 | 🟢 |
| 429 | 낮음 | Rate limit (stocks/views.py 사용) | 🟢 |
| 500 | 중 | 서버 오류 | 🟢 |
| 503 | 낮음 | 외부 서비스 장애 (chainsight) | 🟢 |

**결론**: 상태 코드 *선택*은 일관되나, *생성 시 201 사용*과 *`status` 모듈 사용*은 앱별로 불일치.

---

## 에러 응답 형식

### 에러 키 분포

| 키 | 사용 앱 / 파일 | 예시 구조 |
|----|-----------------|-----------|
| `error` (문자열) | stocks 대부분, macro, news/api, validation/api, chainsight/api, thesis, serverless/views_admin.py | `{'error': 'Stock not found'}` |
| `error` (구조화) | `stocks/views.py` L587-596, `rag_analysis/views.py`, `serverless/views.py` L72-76 | `{'error': {'code': 'XXX', 'message': '...', 'details': {...}}}` |
| `error` (serializer.errors dict) | `stocks/views_screener.py` L66 | `{'error': {...ValidationError dict...}}` |
| `detail` (DRF 기본) | `raise NotFound()`, `raise ValidationError()` 자동 변환 (users, news/api) | `{'detail': '...'}` |
| `message` | `users/views.py` L209, L237, `macro/views.py`, `sec_pipeline/views.py` | `{'message': '...'}` |
| `error` + `message` 조합 | `validation/api/views.py` L65-66, `users/views.py` L97 | `{'error': 'code', 'message': 'human readable'}` |
| `status` + `message` | `sec_pipeline/views.py` L38-39 | `{'status': 'collecting', 'message': '...'}` |

### 구조적 불일치 사례

1. **구조화 vs 단순형**
   - 구조화 (권장): `rag_analysis/views.py:46-59`의 `create_error_response("INVALID_INPUT", str(err))` 헬퍼
   - 단순형: `validation/api/views.py:67`의 `{'error': 'not_in_universe'}`
   - 일부 앱은 같은 파일 내에서도 혼용 (`stocks/views.py`)

2. **DRF 예외 vs 커스텀 Response**
   - DRF 예외(`raise ValidationError()`, `raise NotFound()`)는 자동으로 `{'detail': ...}` 반환 → 프론트 기대 키와 다를 수 있음
   - 커스텀 Response는 `{'error': ...}` 반환 → 프론트는 두 경우 모두 대비해야 함

3. **sec_pipeline의 이상 케이스**
   - `{'status': 'collecting', 'message': '...'}` (200)과 `{'status': 'success', ...}` (200)를 상태 구분에 사용하나, **HTTP 상태는 모두 200** → HTTP 프로토콜 대신 JSON 필드로 에러 전달 (안티패턴)

---

## 페이지네이션 현황

### DRF `pagination_class` 사용 여부

**모든 views에서 `pagination_class` 명시적 사용: 0건**

### 목록 API 페이지네이션 구현 방식

| 파일 / 엔드포인트 | 방식 | 상세 | 위험도 |
|-------------------|------|------|--------|
| `stocks/views.py` StockListAPIView | DRF `ListAPIView` 묵시적 | L75-105, `PAGE_SIZE` 프로젝트 설정 의존 | 🟢 |
| `stocks/views.py` 재무제표 조회 | **페이지네이션 없음** | L636-639, 710-713, 782-785: `.filter()` 전체 로드 후 응답 | 🔴 대량 데이터 위험 |
| `stocks/views_screener.py` | 수동 `limit` 파라미터 | L110-127: `?limit=N`만 지원, 페이지 없음 | 🟡 |
| `stocks/views_search.py` SymbolSearchView | **하드코딩 `[:10]`** | L56 | 🟡 |
| `stocks/views_eod.py` SignalDetail | **하드코딩 `[:50]`** | L78 | 🟡 |
| `stocks/views_eod.py` PipelineStatus | **하드코딩 `[:7]`** | L119 | 🟡 |
| `stocks/views_mvp.py` MVPList | **하드코딩 `[:20]`** | L41 | 🟡 |
| `users/views.py` Watchlist | **수동 Django `Paginator`** | L602-620: `{'results', 'pagination'}` 커스텀 응답 | 🟡 비표준 |
| `users/views.py` WatchlistStocks | **수동 Django `Paginator`** | L822-840 | 🟡 비표준 |
| `users/views.py` PortfolioList | **페이지네이션 없음** | L257-259: queryset 전체 반환 | 🔴 |
| `macro/views.py` 전체 | 페이지네이션 없음 | 단건 또는 소량 조회라 허용 | 🟢 |
| `news/api/views.py` /news/all | **수동 `offset/limit` + `has_more`** | L418-432 | 🟡 비표준 |
| `news/api/views.py` /trending | **하드코딩 `[:limit]`** | L327-348 | 🟡 |
| `validation/api/views.py` PresetList | 페이지네이션 없음 | L426-451, 프리셋 소량이라 허용 | 🟢 |
| `chainsight/api/views.py` SignalFeedView | **수동 `page/page_size`** | L568-595: `page = max(int(...), 1)`, `page_size = min(..., 20)` | 🟡 비표준 |
| `thesis/views/monitoring_views.py` AlertListView | **하드코딩 `[:50]`** | L238 | 🟡 |
| `thesis/views/conversation_views.py` NewsIssuesView | **하드코딩 `[:12]`** | L201 | 🟡 |
| `rag_analysis/views.py` UsageHistoryView | **수동 Django `Paginator`** | L796-826, 메타: `current_page, page_size, total_pages, total_count, has_next, has_previous` | 🟡 비표준 |
| `serverless/views.py` FilterEngine 관련 | **수동 `offset/limit`** | L1175-1176, L1312-1316, 메타: `current_page, total_pages, count, total_count` | 🟡 비표준 |

### 메타 필드명 불일치

| 소스 | 메타 필드 |
|------|-----------|
| `rag_analysis/views.py` | `current_page`, `page_size`, `total_pages`, `total_count`, `has_next`, `has_previous` |
| `serverless/views.py` | `current_page`, `total_pages`, `count`, `total_count` |
| `users/views.py` (Watchlist) | `{'results', 'pagination'}` 래핑 (내부 필드 불명) |
| `chainsight/api/views.py` | `page`, `page_size` (total 없음) |
| `news/api/views.py` | `has_more` (boolean만) |

→ **필드명 4~5가지 변형**: `current_page` vs `page`, `page_size` vs (없음), `total_count` vs `count` vs `total_pages`.

### 🔴 잠재 성능 위험 지점

1. `stocks/views.py` 재무제표 3개 (BalanceSheet/IncomeStatement/CashFlow) → 제한 없이 전체 로드
2. `users/views.py` PortfolioList (L257-259) → 사용자 포트폴리오 전체 반환 (수량 증가 시 문제)
3. `stocks/views_mvp.py` SectorListView (L200) → 섹터 전체 직렬화

---

## 권고사항

### High 우선순위 (P0 — 서비스 품질·DX 직접 영향)

1. **성공 응답 래퍼 표준화 (통일안 정의 필요)**
   - **표준안 제시**: `rag_analysis/views.py`의 `create_success_response()` / `create_error_response()` 헬퍼 패턴을 `config/` 혹은 `utils/` 공용 모듈로 승격
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
   - **적용 대상**: 현재 구조화 래퍼를 쓰지 않는 18개 파일 (단계적 마이그레이션: stocks/views.py → thesis → chainsight → validation 순)

2. **페이지네이션 표준 확립**
   - `config/pagination.py`에 `StandardPageNumberPagination(PageNumberPagination)` 정의 (page_size=20, max_page_size=100)
   - `settings.REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']`에 기본값 설정
   - 목록 API 16곳의 수동 `[:N]` 슬라이싱을 DRF `pagination_class`로 교체
   - 재무제표 조회(L636-639, 710-713, 782-785) 우선 적용

3. **에러 키 단일화**
   - DRF 관례인 `error` 사용 (프로젝트 다수결). `detail`은 DRF 기본 예외가 자동 생성하므로, 커스텀 exception handler로 `{'error': {'code', 'message'}}`로 변환
   - `users/views.py`의 `message` 키, `sec_pipeline/views.py`의 `status/message` 키를 `error/success` 표준으로 통일

### Medium 우선순위 (P1 — 일관성·유지보수성)

4. **POST 생성 시 201 Created 강제**
   - `stocks/views.py:986`, `thesis/views/thesis_views.py:143`, `users/views.py` 조건부 201/200 구간 리뷰
   - 단, 비동기 태스크 트리거는 202 Accepted 사용 허용 (`sec_pipeline:40`)

5. **`status` 모듈 사용 강제**
   - `sec_pipeline/views.py:40-44`의 하드코딩된 `status=200/202` → `status.HTTP_200_OK` / `status.HTTP_202_ACCEPTED`로 교체
   - pre-commit / ruff rule로 `Response(..., status=숫자)` 패턴 차단

6. **페이지네이션 메타 필드명 통일**
   - 표준: `{current_page, page_size, total_pages, total_count, has_next, has_previous}` (rag_analysis 기준)
   - OpenAPI 스펙(`contracts/`)에 반영 후 프론트 공유 타입 업데이트

7. **DRF 예외 → 표준 응답 매핑**
   - `config/exceptions.py`에 `custom_exception_handler` 정의
   - `NotFound`, `ValidationError`, `PermissionDenied` 등을 `{'success': False, 'error': {'code': ..., 'message': ...}}`로 변환
   - `REST_FRAMEWORK['EXCEPTION_HANDLER']`에 등록

### Low 우선순위 (P2 — 코드 품질·정리)

8. **빈 views.py 정리**
   - `metrics/views.py`, `graph_analysis/views.py`, `validation/views.py`, `chainsight/views.py`, `news/views.py` → 사용하지 않으면 삭제, 플레이스홀더면 주석 명시

9. **`config/views.py`의 `JsonResponse` → DRF `Response` 마이그레이션**
   - L19-67 `api_root`를 `@api_view(['GET'])` 데코레이터 기반으로 변경

10. **serverless/views_admin.py 래핑 적용**
    - 현재 서비스 응답 직접 반환 → 표준 래퍼 적용으로 일관성 확보

### 마이그레이션 전략 제안

| 단계 | 범위 | 기대 효과 |
|------|------|-----------|
| Phase 1 | `config/response.py` 헬퍼 + 예외 핸들러 + 표준 Pagination 클래스 추가 (기존 코드 무변경) | 기반 마련 |
| Phase 2 | 신규 API는 헬퍼 강제. 기존 중 **에러율 높은 3개 앱**(stocks, users, thesis) 우선 마이그레이션 | DX 개선 |
| Phase 3 | 재무제표/포트폴리오 조회의 페이지네이션 적용 | 성능 리스크 해소 |
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

**총 24개 파일, 그 중 6개 빈 파일**

---

*본 보고서는 읽기 전용 정적 분석 결과이며, 코드 수정은 수행되지 않았다.*
