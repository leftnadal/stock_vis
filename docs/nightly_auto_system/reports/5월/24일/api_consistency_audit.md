# API 응답 일관성 감사 보고서

생성일: 2026-05-24
감사자: qa-architect
대상: 26개 views.py 파일 (실제 코드 내용 없는 stub 5개 제외, 실질 21개 분석)

---

## 요약

- **응답 래핑 불일치 (P0)**: `{'success': True, 'data': ...}` 래핑이 `stocks/views_exchange.py`, `stocks/views_fundamentals.py`, `stocks/views_screener.py`에만 집중적으로 사용되고, 동일 앱 내 다른 파일(`stocks/views.py`, `stocks/views_market_movers.py`)은 직접 반환 방식이다. 프론트엔드가 앱 단위로 응답 형태를 다르게 처리해야 한다.
- **에러 키 혼용 (P1)**: 에러 응답에 `'error'`, `'detail'`, `'message'` 키가 섞여 있다. `users/views.py` 단일 파일에서 세 가지를 동시에 사용하는 사례가 있다.
- **POST 201 누락 (P1)**: POST 엔드포인트 중 `serverless/views.py`의 다수 함수(`trigger_sync`, `sync_now`, `trigger_keyword_generation` 등 약 20개)가 생성 작업임에도 기본 200을 반환한다. `macro/views.py:DataSyncView.post`도 동일.
- **상태코드 하드코딩 (P2)**: `sec_pipeline/views.py:45,49,51` 세 곳 모두 숫자 리터럴(`200`, `202`)을 직접 사용한다.
- **페이지네이션 미적용 목록 API (P1)**: `users/views.py:92` (`User.objects.all()`), `serverless/views_admin.py:475` (`NewsCollectionCategory.objects.all()`), `stocks/views_mvp.py:29` (`Stock.objects.all()[:20]` — 하드코딩 슬라이싱), `news/api/views.py:2124` (`AlertLog.objects.all()` — limit 파라미터로 직접 자름)에서 DRF 페이지네이션 클래스를 사용하지 않는다.

---

## 앱별 응답 패턴 매트릭스

| 앱 | 래핑 방식 | 에러 키 | 상태코드 방식 | 페이지네이션 |
|----|----------|---------|-------------|------------|
| stocks/views.py | 직접 반환 (일부 `results`, `count` 키 포함) | `'error'` + `'message'` 혼용 | `status.HTTP_*` 상수 | StockListPagination (ListAPIView) |
| stocks/views_exchange.py | `{'success': True, 'data': ..., 'meta': {...}}` | `'error'` | `status.HTTP_*` 상수 | 없음 |
| stocks/views_fundamentals.py | `{'success': True, 'data': ..., 'meta': {...}}` | `'error'` (double-quoted) | `status.HTTP_*` 상수 | 없음 |
| stocks/views_market_movers.py | 직접 Serializer 데이터 반환 | `'error'` (double-quoted) | `status.HTTP_*` 상수 | 없음 |
| stocks/views_screener.py | `{'stocks': ..., 'total_count': ..., 'filters_applied': ...}` | `'error'` | `status.HTTP_*` 상수 | 없음 |
| stocks/views_eod.py | 직접 반환 (`snapshot.json_data`, 커스텀 dict) | `'error'` | `status.HTTP_*` 상수 | 없음 |
| stocks/views_indicators.py | 직접 Serializer 데이터 반환 | `'error'` | `status.HTTP_*` 상수 | 없음 |
| stocks/views_search.py | 직접 반환 (`{'count': ..., 'results': ...}`) | `'error'` | `status.HTTP_*` 상수 | 없음 |
| stocks/views_mvp.py | `{'mode': ..., 'count': ..., 'data': ...}` | 없음 (예외 silenced) | `status.HTTP_*` 상수 | 없음 (`:20` 슬라이싱) |
| users/views.py | 직접 Serializer 데이터 반환 | `'error'` + `'detail'` + `'message'` 혼용 | `status.HTTP_*` 상수 | 커스텀 Paginator (Watchlist) |
| rag_analysis/views.py | 직접 Serializer 데이터 반환 | `{'code': ..., 'message': ...}` 중첩 구조 | `status.HTTP_*` 상수 | 없음 |
| macro/views.py | 직접 Serializer 데이터 반환 | `'error'` | `status.HTTP_*` 상수 | 없음 |
| news/api/views.py | 직접 반환 (ViewSet — DRF 기본) | `'error'` + `'message'` 혼용 | `status.HTTP_*` 상수 | NewsArticlePagination |
| serverless/views.py | 직접 반환 (`'message'`, `'task_id'` 등) | `'error'` | `status.HTTP_*` 상수 | 없음 |
| serverless/views_admin.py | 직접 반환 | `'error'` | `status.HTTP_*` 상수 | 없음 |
| validation/api/views.py | 직접 반환 (커스텀 dict) | `'error'` + `'message'` 혼용 | `status.HTTP_*` 상수 | 없음 |
| chainsight/api/views.py | 직접 반환 (커스텀 dict) | `'error'` (double-quoted) | `status.HTTP_*` 상수 | 없음 |
| portfolio/api/views.py | 직접 Serializer 데이터 반환 | `'error'` (double-quoted) | `status.HTTP_*` 상수 | 없음 |
| sec_pipeline/views.py | 직접 반환 | `'status'`+`'message'` | **숫자 리터럴** `200`, `202` | 없음 |
| config/views.py | JsonResponse 직접 사용 (DRF Response 아님) | 없음 | 없음 (기본 200) | 없음 |
| metrics/views.py, validation/views.py, chainsight/views.py, portfolio/views.py, graph_analysis/views.py, news/views.py | **stub (빈 파일)** | — | — | — |

---

## HTTP 상태 코드 일관성

### POST에서 201 누락

`trigger_sync`, `sync_now`, `trigger_keyword_generation` 등 `serverless/views.py`의 POST 엔드포인트 20여 개는 비동기 태스크 시작 응답을 기본 200으로 반환한다. 이 중 실제 리소스를 생성하지 않고 태스크만 트리거하는 경우는 200 또는 202가 더 적절하지만, 일관된 기준이 없다.

- `serverless/views.py:184` — `trigger_sync` POST → 기본 200 (`{'message': 'Sync task started', 'task_id': ...}`)
- `serverless/views.py:231` — `sync_now` POST → 기본 200 (`{'message': 'Sync completed', 'results': ...}`)
- `serverless/views.py:378` — `trigger_keyword_generation` POST → 기본 200 (`{'message': 'Keyword generation started', ...}`)
- `serverless/views.py:693` — `sync_market_breadth` POST → 기본 200 (`{'message': 'Market breadth sync started'}`)
- `serverless/views.py:855` — 섹터 히트맵 동기화 POST → 기본 200 (`{'message': 'Sector heatmap sync started'}`)
- `macro/views.py:377` — `DataSyncView.post` → 기본 200 (`{'status': 'started', 'message': ...}`)

반면 리소스를 명시적으로 생성하는 POST는 201을 올바르게 사용하고 있다.

- `serverless/views.py:921` — 프리셋 생성 → `status.HTTP_201_CREATED`
- `serverless/views.py:1221` — 알림 생성 → `status.HTTP_201_CREATED`
- `users/views.py:107` — 회원가입 → `status.HTTP_201_CREATED`
- `users/views.py:295` — 포트폴리오 생성 → `status.HTTP_201_CREATED`
- `rag_analysis/views.py:63,137,291,396` — 바구니/아이템/세션 생성 → `status.HTTP_201_CREATED`

### 상태코드 하드코딩 (숫자 리터럴)

- `sec_pipeline/views.py:45` — `status=202` (숫자 직접 사용, `status.HTTP_202_ACCEPTED` 권장)
- `sec_pipeline/views.py:49` — `status=200` (숫자 직접 사용)
- `sec_pipeline/views.py:51` — `status=200` (숫자 직접 사용)

나머지 20개 파일은 모두 `status.HTTP_*` 상수를 사용하고 있다.

### 특수 상태코드 사용 현황

- `users/views.py:559` — `status.HTTP_207_MULTI_STATUS` (부분 성공 응답, 프로젝트에서 유일하게 사용)
- `validation/api/views.py:67` — `status.HTTP_422_UNPROCESSABLE_ENTITY` (S&P 500 외 종목 요청 시)
- `chainsight/api/views.py:444,624` — `status.HTTP_503_SERVICE_UNAVAILABLE` (Neo4j 연결 실패 시)
- `stocks/views.py:938`, `serverless/views_admin.py:369`, `portfolio/api/views.py:82` — `status.HTTP_429_TOO_MANY_REQUESTS`
- `portfolio/api/views.py:88` — `status.HTTP_502_BAD_GATEWAY` (LLM 외부 호출 실패 시)

이 중 207과 422는 프로젝트 전체에서 각 1회씩만 사용되어 클라이언트 처리 로직 파편화 가능성이 있다.

---

## 에러 응답 형식

### 키 혼용 현황

프로젝트 전반에서 에러 키가 세 가지로 분산되어 있다.

**`'error'` 키 (다수 앱 사용)**
- `macro/views.py:45` — `{'error': 'Failed to fetch market pulse data'}`
- `stocks/views_search.py:32` — `{'error': '검색어는 최소 2글자 이상 입력해주세요.'}`
- `validation/api/views.py:59` — `{'error': f'Stock {symbol} not found'}`
- `chainsight/api/views.py:71` — `{"error": f"Stock {symbol} not found in graph"}`
- `portfolio/api/views.py:68` — `{"error": ...}` (double-quoted)
- `serverless/views_admin.py:512~649` — `{'error': '이름은 필수입니다'}` 등 다수

**`'detail'` 키 (users 앱 일부)**
- `users/views.py:520` — `{'error': 'Failed to refresh portfolio data', 'detail': str(e)}`
- `users/views.py:565` — `{'error': f'Failed to refresh data for {symbol}', 'detail': str(e)}`
- `config/views.py:38` — 엔드포인트 목록에서 `'detail'` 키 사용 (에러 응답이 아닌 데이터 키로 사용)

**`'message'` 키 (에러 + 성공 공용)**
- `stocks/views.py:184` — `{'result': [], 'message': '검색어를 입력해주세요'}` (400 상태에서 message 사용)
- `stocks/views.py:192` — `{'results': [], 'message': '검색어는 2자 이상 입력해주세요.'}` (400 상태)
- `validation/api/views.py:66` — `{'symbol': symbol, 'error': 'not_in_universe', 'message': '현재 S&P 500 종목만 지원합니다.'}` (422 상태에서 error + message 동시 사용)
- `sec_pipeline/views.py:44` — `{'symbol': ..., 'status': 'collecting', 'message': 'Collection triggered...'}` (202 상태)

### 동일 파일 내 혼용 사례

`users/views.py`는 단일 파일에서 세 키를 모두 사용한다.

- `users/views.py:519` — `'error': 'Failed to refresh portfolio data'`
- `users/views.py:520` — `'detail': str(e)` (error와 detail 동시 사용)
- `users/views.py:512` — `'message': 'Portfolio data refresh initiated'` (성공 응답에 message)

### rag_analysis 중첩 에러 구조

`rag_analysis/views.py`는 다른 앱과 다르게 에러를 중첩 객체로 반환한다.

- `rag_analysis/views.py:520` — `{'phase': 'error', 'error': {'code': 'PIPELINE_ERROR', 'message': str(e)}}`
- `rag_analysis/views.py:531` — `{'phase': 'stream_error', 'error': {'code': 'STREAM_ERROR', 'message': str(e)}}`

SSE(Server-Sent Events) 스트림 응답이므로 HTTP 상태코드 대신 페이로드 내 에러 표현을 사용한 설계이다. 다만 이 구조는 나머지 REST 응답과 완전히 다르다.

### 따옴표 불일치 (따옴표 스타일 혼용)

- `stocks/views_fundamentals.py`, `stocks/views_exchange.py`, `portfolio/api/views.py`, `chainsight/api/views.py`는 에러 키에 double-quote(`"error"`) 사용
- 나머지 파일은 single-quote(`'error'`) 사용
- Python에서 기능 차이는 없으나 코드 스타일 불일치

---

## 페이지네이션 현황

### DRF 페이지네이션 클래스 사용 (2개 파일)

- `stocks/views.py:77-91` — `StockListPagination(PageNumberPagination)`, `page_size=50`, `max_page_size=200`, `StockListAPIView`에 적용
- `news/api/views.py:45-60` — `NewsArticlePagination(PageNumberPagination)`, `page_size=20`, `max_page_size=100`, `NewsViewSet`에 적용

### 페이지네이션 없는 목록 API (성능/DoS 위험)

**비인증 접근 가능 + 페이지네이션 없음 (위험도 높음)**
- `stocks/views_mvp.py:29` — `Stock.objects.all()[:20]` 하드코딩 슬라이싱, DRF 페이지네이션 미사용. `StockMVPListView.get()`에서 `queryset[:20]`으로 잘라내지만 count 계산을 위해 전체 쿼리가 실행될 수 있음.

**관리자 전용이나 페이지네이션 없음 (위험도 중간)**
- `users/views.py:92` — `User.objects.all()` 직접 반환. `Users.get()`은 `IsAdminUser`이나 사용자 수가 증가하면 응답 크기가 무제한으로 커짐.
- `serverless/views_admin.py:475` — `NewsCollectionCategory.objects.all()` 직접 순회하여 result 배열 반환. `AdminNewsCategoryView.get()`은 `IsAdminUser`이나 페이지네이션 없음.
- `news/api/views.py:2124` — `AlertLog.objects.all()`에 `limit` 파라미터로 직접 자름 (`qs[:limit]`). DRF 표준 페이지네이션이 아닌 커스텀 limit 방식.

### 커스텀 페이지네이션 사용 (DRF 표준 미사용)

`users/views.py`의 Watchlist 목록 조회는 Django 내장 `Paginator`를 직접 사용한다.

- `users/views.py:601-614` — `django.core.paginator.Paginator` 직접 사용, 응답에 `'pagination'` 키로 메타 정보 포함. DRF `PageNumberPagination`과 응답 구조가 다름 (`results` 키 사용하지만 DRF 기본 `count`/`next`/`previous` 구조와 불일치).

---

## 권고사항

### P0 — 즉시 수정 권장

| 번호 | 위치 | 문제 | 표준화 방안 |
|------|------|------|------------|
| P0-1 | `stocks/views_exchange.py`, `stocks/views_fundamentals.py` vs `stocks/views.py`, `stocks/views_market_movers.py` | 동일 앱 내 래핑 패턴 불일치 (`success/data/meta` vs 직접 반환) | `stocks` 앱 전체를 직접 반환 또는 `success/data` 래핑 중 하나로 통일 |
| P0-2 | `sec_pipeline/views.py:45,49,51` | 상태코드 숫자 리터럴 하드코딩 | `status.HTTP_202_ACCEPTED`, `status.HTTP_200_OK` 상수로 교체 |

### P1 — 우선 수정 권장

| 번호 | 위치 | 문제 | 표준화 방안 |
|------|------|------|------------|
| P1-1 | 전체 앱 | 에러 키 `'error'` / `'detail'` / `'message'` 혼용 | 에러 응답 표준: `{'error': str}` 단일 키로 통일. `detail`은 DRF 내부 예외용으로 예약 |
| P1-2 | `users/views.py:519-520` | 단일 응답 객체에 `'error'`와 `'detail'` 동시 사용 | `'error'` 키 하나로 통합, 상세 정보는 `'error_detail'` 또는 제거 |
| P1-3 | `stocks/views.py:184,192` | 400 에러 응답에 `'message'` 키 사용 (성공 응답 키와 동일) | 에러 시 `'error'` 키로 통일 |
| P1-4 | `serverless/views.py:184,231,378,693,855`, `macro/views.py:377` | 비동기 작업 트리거 POST에서 201/202 미반환 | 리소스 생성 없는 트리거는 `HTTP_202_ACCEPTED`, 리소스 생성은 `HTTP_201_CREATED`로 구분 |
| P1-5 | `users/views.py:92` | `User.objects.all()` 무제한 반환 | `IsAdminUser` 유지하되 `PageNumberPagination` 추가 |
| P1-6 | `news/api/views.py:2124` | `AlertLog.objects.all()`에 커스텀 limit만 사용 | DRF `LimitOffsetPagination` 또는 표준 `PageNumberPagination`으로 교체 |

### P2 — 중기 개선 권장

| 번호 | 위치 | 문제 | 표준화 방안 |
|------|------|------|------------|
| P2-1 | `users/views.py:601-614` | Django 내장 Paginator 직접 사용 | DRF `PageNumberPagination` 표준으로 교체하여 `count/next/previous` 구조 통일 |
| P2-2 | `stocks/views_mvp.py:29` | `Stock.objects.all()[:20]` 슬라이싱 | MVP 파일 전반적으로 DRF 페이지네이션 적용 또는 명시적 limit 파라미터 + 최대값 제한 |
| P2-3 | `serverless/views_admin.py:475` | `NewsCollectionCategory.objects.all()` 무제한 | limit 파라미터 또는 페이지네이션 추가 |
| P2-4 | `validation/api/views.py:67` | `HTTP_422_UNPROCESSABLE_ENTITY` 단독 사용 | 클라이언트 처리 일관성을 위해 422 처리를 문서화하거나 400으로 통일 검토 |
| P2-5 | `rag_analysis/views.py:520,531` | SSE 스트림 에러 구조 (`{'code': ..., 'message': ...}`) 별도 | SSE 특성상 불가피하나 클라이언트 사이드 처리 문서화 필요 |
| P2-6 | `stocks/views_fundamentals.py`, `chainsight/api/views.py`, `portfolio/api/views.py` | 에러 키 double-quote 사용 | Python 스타일 통일을 위해 single-quote로 교체 (기능 무관, lint 규칙 추가 권장) |
| P2-7 | `metrics/views.py`, `validation/views.py`, `chainsight/views.py`, `portfolio/views.py`, `graph_analysis/views.py`, `news/views.py` | stub 파일 6개 존재 | 사용하지 않는 파일 정리 또는 placeholder 주석으로 의도 명시 |

---

## 부록: 감사 범위 외 관찰 사항

- `config/views.py`는 DRF `Response`가 아닌 Django `JsonResponse`를 직접 사용한다. 건강 체크 엔드포인트이므로 기능상 문제없으나, DRF 미들웨어(인증, throttling 등) 우회 가능성에 유의.
- `users/views.py:559`의 `HTTP_207_MULTI_STATUS`는 Watchlist 벌크 추가 부분 성공 시 사용되는데, 이 상태코드를 처리하는 프론트엔드 코드가 존재하는지 확인 필요.
- `chainsight/api/views.py:444,624`의 `HTTP_503_SERVICE_UNAVAILABLE`은 Neo4j 연결 실패 시 반환되는데, 이 에러를 클라이언트에서 재시도(retry) 로직으로 처리하는지 확인 권장.
