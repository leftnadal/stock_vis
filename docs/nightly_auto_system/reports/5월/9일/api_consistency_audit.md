# API 응답 일관성 감사 보고서

> **감사 일자**: 2026-05-09 / **감사 범위**: Stock-Vis 백엔드 모든 `views*.py` 25개 파일 (총 14,708줄)
> **방법**: 읽기 전용 정적 분석 (코드 변경 없음)

---

## 요약

Stock-Vis 백엔드는 **DRF `Response()` 패턴이 앱별로 4개 스타일이 혼재**해 클라이언트 입장에서 일관된 처리가 불가능한 상태다. 가장 정교한 패턴(`rag_analysis`)부터 DRF 미사용(`portfolio`, `config`)까지 스펙트럼이 넓다.

### 핵심 발견 (Top 5)

1. **응답 래핑 4가지 스타일 혼재**
   - `{success, data, meta}` 표준 헬퍼: `rag_analysis`, `serverless/views.py`, `stocks/views_screener.py`, `stocks/views_fundamentals.py`, `stocks/views_exchange.py` — 정교한 표준화
   - 직접 데이터/Serializer.data 반환: `stocks/views_indicators.py`, `users`, `macro`, `news/api/views.py`, `chainsight/api/views.py`, `thesis/*`
   - `JsonResponse` (DRF 미사용): `portfolio/views.py`, `config/views.py`
   - 혼합형 (한 파일 내 여러 스타일): `stocks/views.py`, `serverless/views_admin.py`

2. **에러 응답 키 3종 불일치**
   - `{error: ...}` (다수)
   - `{error: {code, message}}` (`serverless/views.py`, `rag_analysis`)
   - `{detail: ...}`, `{message: ...}`, `{error, detail}`, Serializer.errors 직접 — 클라이언트가 분기 처리 강제됨

3. **HTTP 상태코드 — 201 사용 부재**
   - `rag_analysis`, `users` 만 POST 생성 시 명시적 201 / DELETE 시 204 사용
   - 나머지 모든 앱은 POST 생성에서도 암묵적 200 반환 (REST 위반)

4. **페이지네이션 — DRF 표준 미사용**
   - DRF `pagination_class` 정식 사용: `users/views.py`(Watchlist) + `stocks/views.py:StockListAPIView`만
   - 대부분 `[:limit]` 슬라이싱 또는 수동 `page/page_size` offset 계산 (`serverless`, `chainsight`)
   - `news/api/views.py` 2189줄 전체에 페이지네이션 부재

5. **두 앱이 DRF를 우회**
   - `portfolio/views.py`(304줄): `JsonResponse` 사용 (Django plain view) — DRF 인증/권한/Renderer 우회
   - `config/views.py`(104줄): `JsonResponse` 사용 — 일관성 차원에서 격리됨

---

## 앱별 응답 패턴 매트릭스

| 앱 / 파일 | 줄수 | 래핑 형식 | 에러 키 | 상태코드 모듈 | 201 사용 | 204 사용 | 페이지네이션 |
|---|---:|---|---|:---:|:---:|:---:|---|
| **stocks/views.py** | 1020 | 혼합 (중첩 dict + custom 키) | `error`, `error{}`, `message` | ✅ | ❌ | ❌ | ListAPIView 자동 |
| **stocks/views_screener.py** | 498 | `{success,data,meta}` 100% | `error`, `errors` | ✅ | ❌ | ❌ | 없음 (limit) |
| **stocks/views_indicators.py** | 372 | 직접 dict | 텍스트 메시지 | ✅ | ❌ | ❌ | 없음 |
| **stocks/views_fundamentals.py** | 305 | `{success,data,meta}` 100% | `error` | ✅ | ❌ | ❌ | 없음 |
| **stocks/views_exchange.py** | 295 | `{success,data,meta}` 100% | `error` | ✅ | ❌ | ❌ | 없음 |
| **stocks/views_search.py** | 229 | 직접 dict (`count`, `results`) | `error` | ✅ | ❌ | ❌ | `[:20]` |
| **stocks/views_mvp.py** | 200 | 직접 dict (`mode`, `data`) | — | ❌(미지정) | ❌ | ❌ | `[:20]` |
| **stocks/views_eod.py** | 136 | 직접 dict | — | ✅ | ❌ | ❌ | `[:50]` |
| **stocks/views_market_movers.py** | 69 | `Response(serializer.data)` | — | ✅ | ❌ | ❌ | 없음 |
| **serverless/views.py** | 3413 | `{success, data}` / `{success, error{code,message}}` 표준 | `error{code,message}` | ✅ | ✅(L1065,1435) | ❌ | 수동 page/limit |
| **serverless/views_admin.py** | 694 | 혼합 (`{success,data}`, raw dict) | `error` | ✅ | ✅(L568) | ❌ | 없음 |
| **chainsight/api/views.py** | 814 | 직접 dict (Neo4j sanitize) | `error` (단순) | ✅ | ❌ | ❌ | 수동 page/page_size |
| **news/api/views.py** | 2189 | 직접 dict | `error` | ✅ | ❌ | ❌ | **없음** (수동 limit) |
| **rag_analysis/views.py** | 868 | `create_success/error_response()` 헬퍼 100% | `error{code,message}` | ✅ | **✅** (다수) | **✅** | `Paginator` 사용 |
| **users/views.py** | 1088 | Serializer.data + custom | `error`, `detail`, Serializer.errors | ✅ | **✅** (다수) | **✅** | DRF 페이지네이션 |
| **portfolio/views.py** | 304 | **JsonResponse** (DRF 미사용) | `{error:code, detail:msg}` | ✅ | ❌ | ❌ | 없음 |
| **thesis/views/thesis_views.py** | 336 | Serializer.data + custom | `error` | ✅ | (ModelViewSet 자동) | ❌ | 없음 |
| **thesis/views/conversation_views.py** | 380 | Service 결과 직접 | `error` | ✅ | ❌ | ❌ | 없음 |
| **thesis/views/monitoring_views.py** | 364 | 중첩 dict | — (예외 로깅만) | ✅ | ❌ | ❌ | 수동 `[:50]` |
| **validation/api/views.py** | 558 | 구조화 dict | `error`, `error+message` | ✅ | ❌ | ❌ | 없음 (`[:50]` 캡) |
| **macro/views.py** | 410 | Serializer.data + raw | `error` 일관 | ✅ | ❌ | ❌ | 없음 |
| **config/views.py** | 104 | **JsonResponse** (DRF 미사용) | — | ❌ (200만) | ❌ | ❌ | 없음 |
| **sec_pipeline/views.py** | 51 | raw dict | — | ✅ (202/200) | ❌ | ❌ | 없음 |
| **metrics/views.py**, **graph_analysis/views.py**, **news/views.py**, **validation/views.py**, **chainsight/views.py** | 1~3 | 빈 파일 | — | — | — | — |

---

## HTTP 상태 코드 일관성

### `status` 모듈 vs 하드코딩
- **모듈 사용 일관**: 거의 모든 파일에서 `from rest_framework import status` 후 `status.HTTP_*` 사용
- **상태코드 미지정**: `stocks/views_mvp.py`(200줄 전체) — 모든 응답이 암묵적 200, `config/views.py` — 모든 응답이 암묵적 200 (DB 연결 실패도 200)
- **하드코딩 숫자**: 발견되지 않음 (✅ 양호)

### POST 생성 시 201 vs 200
| 패턴 | 적용 앱 | 비율 |
|---|---|---|
| 201 명시 | `rag_analysis`(L87, 167, 349, 459), `users`(L107, 295, 639, 731, 918), `serverless/views.py`(L1065, 1435), `serverless/views_admin.py`(L568) | **약 4개 앱 / 13개** |
| 암묵적 200 | `stocks/*`, `news/api/views.py`, `thesis/*`(ModelViewSet 자동 처리 외), `portfolio`, `validation`, `macro`, `chainsight/api/views.py` | 다수 |

→ **REST 컨벤션 위반**: POST 생성 응답 대부분이 200을 반환

### 204 No Content (DELETE)
- `users`(L342, 688, 759), `rag_analysis`(L132, 205, 491)에서만 사용
- 나머지 앱은 DELETE 후에도 200 + `{message: '...'}` 반환

### 에러 코드 분포
| 코드 | 주 사용처 | 의미 |
|---|---|---|
| 400 | 모든 앱 — 가장 흔함 | 입력 검증 실패 |
| 401 | `validation`(L463, 489), `serverless/views.py`(L1420), `users` | 인증 필요 |
| 403 | `serverless/views.py`(L1115, 1138), `rag_analysis`(L667) | 권한 부족 |
| 404 | `users`, `serverless`, `chainsight`, `news`, `rag_analysis` | 리소스 없음 |
| 429 | `serverless/views_admin.py`(L369), `portfolio`(L107, 169, 230, 291) | Rate limit / 예산 초과 |
| 500 | `users`, `serverless`, `rag_analysis`, `macro`, `portfolio` | 서버 에러 |
| 503 | `chainsight`(L443, 623), `stocks/views.py`, `stocks/views_search.py`, `stocks/views_exchange.py`, `portfolio` | 외부 서비스 장애 |
| **202** | **`sec_pipeline/views.py`만** | 비동기 수집 진행 중 (REST 정합성 양호) |

---

## 에러 응답 형식

### 형식 별 분포 (앱 단위)

| 형식 | 사용 앱 | 비고 |
|---|---|---|
| `{error: '문자열'}` | stocks 대부분, news, chainsight, macro, thesis, validation, users 일부 | **가장 흔함** |
| `{error: {code, message}}` 구조화 | `serverless/views.py`, `rag_analysis` (헬퍼) | 클라이언트 친화 |
| `{success: false, error: {...}}` | `serverless/views.py`, `rag_analysis` | 표준화된 envelope |
| `{detail: '...'}` | `users/views.py`(L520, 565) — refresh 경로 | DRF 기본 형식과 부분적으로 호환 |
| `{message: '...'}` | `stocks/views.py`(L173-175), `validation`(L67-85, error+message 함께) | 단독 사용 드묾 |
| `{error: code, detail: message}` | `portfolio/views.py` | 자체 컨벤션 |
| `Serializer.errors` 직접 반환 | `users/views.py`(L68, 109, 299, 336, 678, 797), `stocks/views_screener.py`(L66) | DRF 기본 |
| 텍스트 메시지 (key 없음) | `stocks/views_indicators.py`(L69-71) | **비표준** |
| 에러 응답 자체 부재 | `config`(연결 실패도 200), `monitoring_views`(예외 로깅 후 기본값) | 디버깅 어려움 |

### 핵심 불일치
- **DRF 기본 `{detail}` 형식 거의 미사용** — 사용자 정의 `{error}`가 사실상 표준
- 같은 앱 내에서도 키가 다름:
  - `users/views.py`: 위치마다 `error`, `detail`, `Serializer.errors` 혼용
  - `stocks/views.py`: `error`, `error{}` (중첩), `message` 혼용
- **표준화된 envelope (`{success, error: {code, message}}`) 보유 앱은 `rag_analysis`, `serverless/views.py` 단 2곳**

---

## 페이지네이션 현황

### DRF 표준 페이지네이션 사용
- **`users/views.py`**: Watchlist 목록(L609-627)과 종목(L829-847)에서 `page`/`page_size` 파라미터 + `pagination` 메타 응답. 페이지 크기 최대 100 강제(L606, 826)
- **`stocks/views.py:StockListAPIView`** (L75-105): `ListAPIView` 상속 → DRF 기본 `pagination_class` 자동 적용

### 수동 페이지네이션 (DRF 미준수)
- **`serverless/views.py`**:
  - `execute_preset` (L1176-1180): `page`, `page_size` 수동 offset 계산
  - `advanced_screener_api` (L1317-1321): 동일 패턴
- **`chainsight/api/views.py`**:
  - `signal_feed_api` (L633-639): 수동 `page`/`page_size`
- **`rag_analysis/views.py`**:
  - `django.core.paginator.Paginator` 사용 (L782, 800-822) — UsageLog 1곳만
  - 나머지 목록(DataBasket, AnalysisSession, messages)은 페이지네이션 없음

### 슬라이싱(`[:N]`) 캡 처리만 — 표준 페이지네이션 부재
- `stocks/views_search.py` (`[:20]`)
- `stocks/views_mvp.py` (`[:20]`)
- `stocks/views_eod.py` (`[:50]`)
- `validation/api/views.py` (`[:50]`)
- `serverless/views.py:alert_history_api` (L1552-1564, `[:limit]`)
- `serverless/views.py:etf_holdings` (L2123-2124, `[:limit]` max 50)
- `thesis/views/monitoring_views.py` (`[:50]`)
- `serverless/views.py:sector_movers_by_sector` (L944-945, `[:limit]` max 10)

### **페이지네이션 완전 부재 (위험 — 데이터 폭증 시 응답 비대화)**
- **`news/api/views.py` (2189줄)**: `.filter().distinct().order_by(...)` 결과를 그대로 직렬화해 반환 (L95-98, 2115-2129) — 뉴스 기사가 누적되면 응답 크기 통제 불능
- **`rag_analysis/views.py`**:
  - `DataBasket.objects.filter(user=...)` 직렬화 후 반환 (L76)
  - `AnalysisSession.objects.filter(user=...)` 동일 (L437)
  - `session.messages.all().order_by('created_at')` 동일 (L507)
- **`stocks/views_screener.py`, `views_fundamentals.py`, `views_exchange.py`**: 결과 전체를 `data` 키로 반환 (limit 파라미터 있어도 페이지네이션 없음)
- **`portfolio/views.py`**, **`thesis/*`**, **`validation/api/views.py`**, **`macro/views.py`**, **`config/views.py`**, **`sec_pipeline/views.py`**: 모든 엔드포인트 페이지네이션 부재

---

## 권고사항

> 코드 수정 없이 감사만 수행하므로, 아래는 향후 리팩토링 시 우선순위 권고.

### P0 — 즉시 수정 필요
1. **포트폴리오/콘피그 DRF 마이그레이션 검토**
   - `portfolio/views.py`, `config/views.py`가 `JsonResponse` 사용 → DRF 인증/권한/Throttle 우회됨
   - 특히 `portfolio/views.py`는 LLM 비용 관련 429 처리가 있는데 DRF Throttle을 활용하지 못함

2. **`config/views.py` 헬스체크 200 고정 문제**
   - DB/캐시 disconnected여도 HTTP 200 반환 → 외부 모니터링이 실패를 감지 못함
   - 503 반환으로 변경 권장

3. **`news/api/views.py` 페이지네이션 부재**
   - 2189줄 전체에 페이지네이션 부재 — 뉴스 누적 시 응답 폭증 위험

### P1 — 표준화 권고
4. **응답 envelope 표준 채택**
   - `rag_analysis`의 `create_success_response()`/`create_error_response()` 헬퍼를 공용 모듈로 승격
   - `{success, data, meta}` / `{success, error: {code, message}, meta}` 형식을 전체 앱에 적용
   - 후보 위치: `config/api_response.py` 또는 `contracts/api_envelope.py`

5. **에러 키 통일**
   - DRF 기본 `{detail}` 또는 자체 표준 `{error: {code, message}}` 중 1개로 합의
   - 같은 앱 내 혼용(특히 `users/views.py`, `stocks/views.py`) 우선 정리

6. **POST 생성 → 201 / DELETE → 204**
   - REST 컨벤션 준수: 현재 `users`, `rag_analysis` 외 모든 앱이 200 반환
   - `serializer.save()` 직후 `status=status.HTTP_201_CREATED` 명시

### P2 — 점진 개선
7. **DRF 페이지네이션 도입**
   - `settings.py`에 `DEFAULT_PAGINATION_CLASS` 설정 + `PAGE_SIZE` 50 권장
   - 수동 `page`/`page_size` 처리 위치(`serverless/views.py`, `chainsight/api/views.py`)는 `LimitOffsetPagination` 또는 `PageNumberPagination`로 전환
   - `[:N]` 슬라이싱 위치들도 점진 마이그레이션

8. **`stocks/views.py` 1020줄 분할 + 패턴 통일**
   - 다른 `stocks/views_*.py`는 `{success, data, meta}` 표준인데 `views.py`만 혼합형 → 분할 후 표준 적용

9. **`stocks/views_mvp.py` 상태코드 명시**
   - 200줄 전체에 `status=...` 미지정 — 명시적으로 추가

### P3 — 장기 개선
10. **API 컨트랙트 검증 자동화**
    - `contracts/` OpenAPI 스펙과 실제 응답 형식 일치 여부 자동 테스트 추가
    - `qa-architect` 에이전트가 PR마다 응답 envelope 위반 검출

---

## 부록: 표준 envelope 비교 (참고용)

### A. `rag_analysis` 표준 (가장 정교)
```python
# 성공
{
  "success": True,
  "data": <payload>,
  "meta": {"request_id": "<uuid>", "timestamp": "<iso>"}
}

# 실패
{
  "success": False,
  "error": {"code": "INVALID_INPUT", "message": "종목 심볼을 입력해주세요."},
  "meta": {"request_id": "<uuid>", "timestamp": "<iso>"}
}
```

### B. `serverless/views.py` 표준
```python
# 성공
{"success": True, "data": {...}}

# 실패
{"success": False, "error": {"code": "INVALID_TYPE", "message": "..."}}
```

### C. `stocks/views_screener|fundamentals|exchange.py` 표준
```python
{"success": True, "data": {...}, "meta": {...}}
```

### D. `users/views.py` 패턴 (DRF 일부 적용)
```python
# 성공
<serializer.data>  # 직접 반환

# 페이지네이션 응답
{"results": [...], "pagination": {"page": 1, "page_size": 50, "total": 124}}

# 실패
{"error": "...", "detail": "..."}  # 또는 Serializer.errors 그대로
```

→ 위 4개 중 **A를 선정해 전사 표준으로 채택 권장** (`request_id` + `timestamp` 메타가 디버깅에 유리).

---

**감사 완료**: 14,708줄 분석. 코드 수정 없음. 보고서만 생성.
