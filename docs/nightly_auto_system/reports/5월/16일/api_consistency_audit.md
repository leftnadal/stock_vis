# API 응답 일관성 감사 보고서

생성일: 2026-05-17
분석 대상: 29개 views 파일 (12개 앱)
실질 분석 대상: 20개 파일 (나머지 9개는 비어 있거나 Django 템플릿 뷰 전용)

---

## 요약

### 핵심 발견 5개

1. **래핑 형식이 앱마다 제각각**: `{'success': True, 'data': ...}` (stocks 일부), 직접 데이터 반환 (users, rag_analysis 등), `JsonResponse` (portfolio 전체), DRF `Response` 혼용이 같은 프로젝트 안에 공존한다. 프론트엔드가 응답을 처리하는 방식이 앱마다 달라야 하므로 유지보수 비용이 높다.

2. **에러 키가 세 가지 이상 혼용**: `{'error': str}` (가장 많음, 12개 파일), `{'detail': str}` (portfolio에서 에러 보조 키로 사용), `{'message': str}` (macro, serverless, users 일부)가 같은 HTTP 상태 코드에서 다른 키로 에러를 내려준다. 클라이언트가 에러 메시지를 일관되게 파싱할 수 없다.

3. **HTTP 상태 코드 하드코딩**: `sec_pipeline/views.py`와 `portfolio/views.py` 전체가 숫자 리터럴(200, 202, 400, 500)을 사용한다. `portfolio/views.py`는 DRF `Response` 대신 Django `JsonResponse`를 쓰므로 DRF 미들웨어(인증, 콘텐츠 협상 등)를 우회한다.

4. **POST에서 201 미반환**: `macro/views.py:361`(DataSyncView.post)와 `users/views.py:511`(RefreshPortfolioDataView.post) 등 동작을 트리거하는 POST 엔드포인트들이 200을 반환한다. 생성/트리거 성공 시 201이 관례이나, 앱별로 기준이 다르다.

5. **페이지네이션 사각지대**: 목록을 반환하는 뷰가 17개 이상이나 `pagination_class`를 명시한 파일은 `stocks/views.py`와 `news/api/views.py` 단 2개다. 나머지는 ORM 결과를 슬라이싱(`[:20]`, `[:50]`)하거나 그대로 직렬화하여 반환한다.

### 일관성 점수 (정성 평가)

| 카테고리 | 점수 | 비고 |
|---------|------|------|
| 래핑 형식 | 3/10 | 5개 이상 패턴 혼재 |
| 에러 응답 형식 | 4/10 | 3가지 키 혼용 |
| HTTP 상태 코드 스타일 | 6/10 | 대부분 status 모듈 사용, 2개 파일 예외 |
| POST 201 준수 | 5/10 | 일부 준수, 일부 200 반환 |
| 페이지네이션 | 2/10 | 2개 파일만 공식 클래스 사용 |

---

## 앱별 응답 패턴 매트릭스

| 앱 | 주 래핑 형식 | 에러 형식 | 상태코드 스타일 | 페이지네이션 | 비고 |
|---|---|---|---|---|---|
| stocks (views.py) | 직접 dict | `{'error': str}` | `status.HTTP_*` | `StockListPagination` (ListAPIView만) | 기타 뷰는 래핑 없음 |
| stocks (views_exchange.py) | `{'success': True, 'data': ..., 'meta': {...}}` | `{"error": str}` | `status.HTTP_*` | 없음 | 가장 완성도 높은 래핑 |
| stocks (views_fundamentals.py) | `{'success': True, 'data': ..., 'meta': {...}}` | `{"error": str}` | `status.HTTP_*` | 없음 | views_exchange와 동일 패턴 |
| stocks (views_screener.py) | `{'success': True, 'data': ..., 'meta': {...}}` | `{"error": str}` | `status.HTTP_*` | 없음 | Enhanced/비Enhanced 분기 |
| stocks (views_market_movers.py) | 직접 Serializer.data | `{"error": str}` | `status.HTTP_*` | 없음 | |
| stocks (views_eod.py) | 직접 dict (snapshot.json_data 등) | `{'error': str}` | `status.HTTP_*` | 없음 | |
| stocks (views_search.py) | `{'count': N, 'results': [...]}` | `{'error': str}` | `status.HTTP_*` | 없음 | |
| stocks (views_indicators.py) | 직접 dict | `{'error': str}` | `status.HTTP_*` | 없음 | |
| stocks (views_mvp.py) | `{'mode': ..., 'count': N, 'data': [...]}` | 없음 | 미지정 (디폴트 200) | 없음 | 에러 처리 없음 |
| users | 직접 Serializer.data | `{'error': str}` + `{'detail': str}` 혼용 | `status.HTTP_*` | Django 수동 Paginator (views.py:수동 구현) | DRF raise 예외 패턴도 혼용 |
| macro | 직접 Serializer.data | `{'error': str}` | `status.HTTP_*` | 없음 | 모든 뷰 try/except + 500 |
| news/api | ViewSet + DRF 기본 | `raise ValidationError({...})` | `status.HTTP_*` | `NewsArticlePagination` | DRF 예외 패턴 일관 |
| serverless (views.py) | 직접 dict / Serializer.data | `raise ValidationError/NotFound` | `status.HTTP_*` | 없음 | api_view 함수형 + 클래스형 혼용 |
| serverless (views_admin.py) | `{'actions': ...}` / 직접 dict | `{'error': str}` | `status.HTTP_*` | 없음 | |
| rag_analysis | 직접 Serializer.data | `raise NotFound/ValidationError` | `status.HTTP_*` | 없음 | DRF 예외 패턴 일관 |
| chainsight/api | 직접 dict | `{"error": str}` | `status.HTTP_*` | 없음 | |
| chainsight/views/watchlist | ViewSet 기본 + 커스텀 | `raise` DRF 예외 | `status.HTTP_*` | 없음 | |
| validation/api | 직접 dict | `{'error': str}` | `status.HTTP_*` | 없음 | |
| portfolio | 직접 dict | `{"error": str}` | **하드코딩 숫자** | 없음 | DRF 미사용, JsonResponse 전용 |
| sec_pipeline | 직접 dict | `{'message': str}` | **하드코딩 숫자** | 없음 | |
| thesis | ViewSet 기본 / 직접 dict | `raise` DRF 예외 | `status.HTTP_*` | 없음 | |
| graph_analysis | 없음 (미구현) | — | — | — | views.py 비어 있음 |
| metrics | 없음 (미구현) | — | — | — | views.py 비어 있음 |
| config | JsonResponse (루트/헬스체크) | `JsonResponse({'status': ...})` | 하드코딩 없음 | — | API 인프라 뷰 |

---

## HTTP 상태 코드 일관성

### status 모듈 vs 하드코딩 통계

- `status.HTTP_*` 사용: 16개 파일 (178개 사용처)
- 하드코딩 숫자: 2개 파일 집중 발생

**하드코딩 위치**:

| 파일:라인 | 코드 | 권고 |
|---------|------|------|
| `sec_pipeline/views.py:45` | `status=202` | `status.HTTP_202_ACCEPTED` |
| `sec_pipeline/views.py:49` | `status=200` | `status.HTTP_200_OK` |
| `sec_pipeline/views.py:51` | `status=200` | `status.HTTP_200_OK` |
| `portfolio/views.py:49` | `status=400` | `status.HTTP_400_BAD_REQUEST` |
| `portfolio/views.py:55` | `status=503` | `status.HTTP_503_SERVICE_UNAVAILABLE` |
| `portfolio/views.py:57` | `status=500` | `status.HTTP_500_INTERNAL_SERVER_ERROR` |
| `portfolio/views.py:59` | `status=200` | `status.HTTP_200_OK` |
| `portfolio/views.py:84~304` | `status=400/429/500/200` (반복 10회+) | 전체 교체 필요 |

### POST에서 200 반환 (201 누락) 사례

| 파일:라인 | 메서드 | 설명 | 현재 | 권고 |
|---------|------|------|------|------|
| `macro/views.py:376` | `DataSyncView.post` | 동기화 트리거 | 미지정(200) | 202 Accepted 또는 200 유지 가능 (트리거 의미) |
| `users/views.py:511` | `RefreshPortfolioDataView.post` | 데이터 갱신 트리거 | 200 명시 | 202 Accepted 권고 |
| `serverless/views.py:907` | `screener_preset_list POST` | 프리셋 생성 | 201 (정상) | — |
| `stocks/views_exchange.py:147` | `BatchQuotesView.post` | 배치 조회 | 미지정(200) | GET으로 설계 권고 또는 200 유지 가능 |
| `stocks/views_indicators.py:300` | `IndicatorCustomizeView.post` | 지표 설정 저장 | 확인 필요 | 생성 시 201 |

### 디폴트 200 의존 사례

`views_mvp.py` 전체 (4개 뷰)와 `thesis/views/monitoring_views.py`의 일부 뷰가 `status` 인자를 명시하지 않아 디폴트 200에 의존한다. 성공 경로에서는 문제가 없으나, 명시적 코드가 가독성과 유지보수에 유리하다.

---

## 에러 응답 형식

### 형식별 분포

| 에러 키 | 개수 (대략) | 대표 위치 |
|--------|---------|---------|
| `{'error': str}` | 약 105개 | `stocks/views.py`, `macro/views.py`, `chainsight/api/views.py`, `portfolio/views.py` 등 12개 파일 |
| `raise ValidationError({...})` | 약 40건 | `news/api/views.py`, `serverless/views.py`, `rag_analysis/views.py` — DRF가 `{'field': ['msg']}` 형식으로 직렬화 |
| `raise NotFound / PermissionDenied` | 약 60건 | `users/views.py`, `serverless/views.py`, `rag_analysis/views.py` — DRF가 `{'detail': str}` 형식으로 직렬화 |
| `{'message': str}` | 약 59개 | `macro/views.py`, `serverless/views.py`, `config/views.py` — 성공 메시지에도 사용 |
| `{'detail': str}` | 약 27개 | `portfolio/views.py` 에러 보조 키, `users/views.py` 일부 |

### 같은 앱 내 불일치 사례

**users 앱 (가장 심함)**

- `users/views.py:519`: `return Response({'error': 'Failed to refresh portfolio data', 'detail': str(e)}, status=HTTP_500)`
- `users/views.py:120`: `raise NotFound` — DRF가 `{'detail': 'Not found.'}` 반환
- `users/views.py:863`: `raise ValidationError("...")` — DRF가 `['...']` 반환
- 동일 파일에 `{'error': ...}` 수동 반환, DRF `raise NotFound`, DRF `raise ValidationError` 3가지 패턴이 혼재한다.

**stocks 앱 내 모듈 간 불일치**

- `views_exchange.py`: `{"success": True, "data": ...}` 래핑 + `{"error": str}` 에러
- `views.py`: 직접 dict 반환 + `{'error': str}` 에러
- `views_mvp.py`: 에러 처리 없음 (빈 except 블록 `except: pass`가 존재)

**sec_pipeline 앱**

- `sec_pipeline/views.py:44`: `{'symbol': ..., 'status': 'collecting', 'message': '...'}` — 에러가 아닌 202 응답이지만 `message` 키 사용
- 성공 응답도 `{'status': 'available'}` 구조로 래핑 없음

### try/except에서 500 노출 패턴

`stocks/views_search.py:87`과 `:142`에서 `except Exception as e`를 잡아 `{'error': f'서버 오류: {str(e)}'}` 형식으로 내부 예외 메시지를 클라이언트에 노출한다. 운영 환경에서 스택 트레이스나 내부 경로가 노출될 위험이 있다.

동일 패턴이 `macro/views.py` 전체(10개 뷰) 및 `stocks/views.py`(8개 위치)에 있으나, 이 파일들은 `str(e)` 대신 고정 메시지를 반환하여 상대적으로 안전하다.

---

## 페이지네이션 현황

### 집계

| 항목 | 수치 |
|-----|------|
| ListAPIView 또는 ViewSet 목록 뷰 | 약 8개 (StockListAPIView, NewsViewSet, ThesisViewSet.list, WatchlistViewSet.list 등) |
| `pagination_class` 명시 | 2개 파일 (`stocks/views.py`, `news/api/views.py`) |
| DRF 공식 페이지네이션 없이 슬라이싱 | 다수 |

### 페이지네이션 없는 목록 반환 위치 (주요 사례)

| 파일:라인 | 뷰/메서드 | 반환 규모 위험도 |
|---------|---------|---------|
| `stocks/views_mvp.py:41` | `StockMVPListView.get` | `[:20]` 슬라이싱 — 상한 있음, 낮음 |
| `stocks/views.py:200` | `StockSearchAPIView.get` | `[:20]` 슬라이싱 — 낮음 |
| `users/views.py` | Portfolio/Watchlist 목록 | Django `Paginator` 수동 구현 — DRF 표준과 다름 |
| `chainsight/api/views.py` | 각종 Graph 탐색 뷰 | Neo4j LIMIT으로 제한 — 낮음 |
| `rag_analysis/views.py:52` | `DataBasketListCreateView.get` | `DataBasket.objects.filter(...)` 전체 반환 — 중간 (사용자별이므로 상한 불명확) |
| `news/api/views.py` (action 함수들) | `stock_news`, `trending_stocks` 등 | ViewSet이지만 `@action` 메서드는 `pagination_class` 미적용 — 고위험 |
| `validation/api/views.py` | `ValidationSummaryView`, `MetricsView` 등 | 집계 결과 반환, 직접 dict — 낮음 |
| `thesis/views/thesis_views.py` | `ThesisViewSet.list` | DRF ViewSet이지만 `pagination_class` 미설정 — 중간 |

**특이 사례**: `news/api/views.py:60`에 `pagination_class = NewsArticlePagination`이 ViewSet 레벨에 선언되어 있으나, `@action` 데코레이터로 정의된 `stock_news`, `trending_stocks` 등의 커스텀 액션은 자동으로 페이지네이션이 적용되지 않는다. 이 액션들은 수동으로 `self.paginate_queryset()`을 호출해야 한다. 확인이 필요하다.

---

## 권고사항

### P0 — 즉시 조치 (보안/운영 위험)

| 번호 | 항목 | 위치 | 조치 |
|-----|------|------|------|
| P0-1 | 내부 예외 메시지 클라이언트 노출 | `stocks/views_search.py:87, 142` | `str(e)` 대신 고정 메시지로 교체 |
| P0-2 | `portfolio` 앱 DRF 미사용 | `portfolio/views.py` 전체 | DRF `Response` + `status.HTTP_*`로 교체, JWT 인증 미들웨어 적용 여부 검토 |

### P1 — 단기 표준화 (2주 내)

| 번호 | 항목 | 영향 파일 | 조치 |
|-----|------|---------|------|
| P1-1 | 에러 응답 키 통일 | 12개 파일 | `{'error': str}` 단일 키로 통일, DRF `raise` 예외 사용 시 `EXCEPTION_HANDLER` 커스터마이징으로 형식 맞춤 |
| P1-2 | 상태 코드 하드코딩 제거 | `sec_pipeline/views.py`, `portfolio/views.py` | `status.HTTP_*` 상수 교체 |
| P1-3 | `ThesisViewSet` 페이지네이션 추가 | `thesis/views/thesis_views.py` | `pagination_class` 명시 |
| P1-4 | `rag_analysis` DataBasket 목록 페이지네이션 | `rag_analysis/views.py:52` | `pagination_class` 또는 `page_size` 상한 추가 |

### P2 — 중기 아키텍처 개선 (1개월 내)

| 번호 | 항목 | 조치 |
|-----|------|------|
| P2-1 | 성공 응답 래핑 형식 표준화 | 공통 `ResponseMixin` 또는 `StandardResponse(data, meta)` 유틸 도입. `{'data': ..., 'meta': {'timestamp': ...}}` 형식 권장 |
| P2-2 | 공통 예외 핸들러 등록 | `REST_FRAMEWORK['EXCEPTION_HANDLER']`에 커스텀 핸들러 등록 — `ValidationError`, `NotFound` 등을 `{'error': ..., 'code': ...}` 통일 형식으로 직렬화 |
| P2-3 | `news/api/views.py` @action 페이지네이션 | `stock_news` 등 @action 메서드에 `self.paginate_queryset()` + `self.get_paginated_response()` 추가 |
| P2-4 | `portfolio` 앱 아키텍처 정렬 | DRF APIView + `Response`로 전환 (DRF 미들웨어 혜택 확보) |

### 표준화 제안 — 공통 ResponseMixin 예시

```python
# utils/response.py
from rest_framework.response import Response
from django.utils import timezone

class StandardResponseMixin:
    def success(self, data, meta=None, status=200):
        body = {'data': data}
        if meta:
            body['meta'] = meta
        body['meta'] = {**(meta or {}), 'timestamp': timezone.now()}
        return Response(body, status=status)

    def error(self, message, code=None, status=400):
        body = {'error': message}
        if code:
            body['code'] = code
        return Response(body, status=status)
```

이 Mixin을 도입하면 현재 5가지 이상의 래핑 패턴을 단일 형식으로 수렴시킬 수 있다.
