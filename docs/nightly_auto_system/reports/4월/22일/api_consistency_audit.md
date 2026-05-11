# API 응답 일관성 감사 보고서

**감사 일자**: 2026-04-22
**감사 범위**: Stock-Vis 백엔드 27개 views 파일 (Django REST Framework)
**감사 모드**: 읽기 전용 (코드 미수정)

---

## 요약

Stock-Vis 백엔드는 **응답 형식의 표준화 부재**가 가장 두드러진 일관성 문제로 확인됨. 동일 프로젝트 내에서 4가지 이상의 응답 래핑 패턴이 공존하며, 같은 앱 내에서도 파일별로 패턴이 상이함.

### 핵심 통계

| 항목 | 발견 사항 |
|------|----------|
| 분석 대상 views 파일 | 27개 (stocks 9 + thesis 3 + 기타 15) |
| 공백/미구현 파일 | 3개 (`config/views.py`, `graph_analysis/views.py`, `metrics/views.py`) |
| 응답 래핑 패턴 종류 | **4종** (`{success, data}`, `{results, count}`, `{key: value}` flat, `serializer.data` 직접) |
| 에러 키 변종 | 3종 (`error`, `message`, `detail`) — 같은 파일 내 혼용 발견 |
| POST 201 미사용 비율 | 약 60% (대부분 200으로 반환) |
| 페이지네이션 미적용 LIST API | 약 80% (수동 슬라이싱 또는 무제한 반환) |

### 우선순위별 권고

| 우선순위 | 항목 | 영향 |
|---------|------|------|
| 🔴 P0 | 응답 표준 래퍼 도입 (`create_success_response` 패턴 전사 확대) | 클라이언트 파싱 복잡도 + 타입 정의 부담 |
| 🟠 P1 | 에러 응답 형식 단일화 (`{'error': {'code', 'message'}}`) | 프론트엔드 에러 핸들링 분기 폭증 |
| 🟠 P1 | LIST API 페이지네이션 클래스 강제 적용 | 메모리/성능 리스크, N+1 노출 |
| 🟡 P2 | POST 생성 시 201 일관 적용 | 의미론적 정확성, 캐싱 정책 |
| 🟡 P2 | `status` 모듈 사용 강제 (하드코딩 제거) | 가독성, 정적 분석 |

---

## 앱별 응답 패턴 매트릭스

각 셀의 표기:
- ✅ = 일관됨
- ⚠️ = 부분 사용/혼용
- ❌ = 미사용 또는 부재
- ─ = 해당 없음(공백 파일)

| 앱/파일 | `{success, data}` 래핑 | 직접 반환 (`serializer.data`) | Flat dict (`{key: ...}`) | 표준 래퍼 함수 사용 | 비고 |
|---------|:-:|:-:|:-:|:-:|------|
| `stocks/views.py` | ❌ | ⚠️ | ✅ | ❌ | `result` vs `results` vs `data` 키 혼용 (L172-176, 198-202, 275-285) |
| `stocks/views_exchange.py` | ✅ | ❌ | ❌ | ❌ | 일관된 `{success, data, meta}` 패턴 |
| `stocks/views_screener.py` | ✅ | ❌ | ❌ | ❌ | `{success, data, meta}` 일관 |
| `stocks/views_market_movers.py` | ❌ | ✅ | ❌ | ❌ | `Response(serializer.data)` 단일 사용 |
| `stocks/views_eod.py` | ❌ | ⚠️ | ✅ | ❌ | `Response(snapshot.json_data)` + flat dict 혼용 |
| `stocks/views_indicators.py` | ❌ | ✅ | ❌ | ❌ | 모두 직접 반환 (L197, 261, 373) |
| `stocks/views_search.py` | ❌ | ⚠️ | ✅ | ❌ | `{count, results}` 패턴 |
| `stocks/views_fundamentals.py` | ✅ | ❌ | ❌ | ❌ | `{success, data, meta}` 일관 |
| `stocks/views_mvp.py` | ❌ | ❌ | ✅ | ❌ | `{mode, count, data}` 패턴 |
| `chainsight/api/views.py` | ❌ | ⚠️ | ✅ | ❌ | 중첩 dict `{center, nodes, edges}` |
| `chainsight/views.py` | ❌ | ⚠️ | ✅ | ❌ | (래거시) 직접 반환 |
| `news/api/views.py` (2,183줄) | ❌ | ⚠️ | ✅ | ❌ | `{symbol, count, articles}` + `count` 산정 방식 혼용 (`articles.count()` vs `len(serializer.data)`) |
| `news/views.py` | ❌ | ⚠️ | ✅ | ❌ | (래거시) |
| `validation/api/views.py` | ❌ | ❌ | ✅ | ❌ | 중첩 dict `{symbol, categories}`, 200 OK + `error` 본문 혼합 |
| `validation/views.py` | ❌ | ⚠️ | ✅ | ❌ | (래거시) |
| `thesis/views/conversation_views.py` | ⚠️ | ❌ | ✅ | ❌ | 서비스 결과 `Response(result)` 직접 반환 |
| `thesis/views/monitoring_views.py` | ❌ | ❌ | ✅ | ❌ | `{alerts, unread_count}`, `{indicator_id, readings}` 등 임의 dict |
| `thesis/views/thesis_views.py` | ❌ | ❌ | ✅ | ❌ | `{status, thesis_id}`, `{indicators, count}` 등 |
| `rag_analysis/views.py` | ✅ | ❌ | ❌ | ✅ | `create_success_response`/`create_error_response` 표준 래퍼 |
| `serverless/views.py` | ✅ | ❌ | ❌ | ✅ | 동일 표준 래퍼 적용 |
| `serverless/views_admin.py` | ⚠️ | ❌ | ⚠️ | ⚠️ | L163 `{'error': '...'}` vs L400 `{success, data}` 혼용 |
| `users/views.py` | ❌ | ⚠️ | ⚠️ | ❌ | `serializer.data` + `{message, data}` + 페이지네이션 응답 `{results, pagination}` 혼용 |
| `macro/views.py` | ❌ | ⚠️ | ⚠️ | ❌ | `serializer.data` + `{status, message}` 혼용 |
| `sec_pipeline/views.py` | ❌ | ❌ | ✅ | ❌ | `Response(result, status=200)` 하드코딩 |
| `api_request/admin_views.py` | ❌ | ❌ | ✅ | ❌ | `{error}` + `{message}` 혼용 |
| `config/views.py` | ─ | ─ | ─ | ─ | 공백 파일 |
| `graph_analysis/views.py` | ─ | ─ | ─ | ─ | 공백 파일 |
| `metrics/views.py` | ─ | ─ | ─ | ─ | 공백 파일 |

### 패턴 분포 (구현된 24개 파일 기준)

```
{success, data} 일관 적용         : 5개 (21%) — exchange, screener, fundamentals, rag_analysis, serverless
표준 래퍼 함수 (create_*_response): 2개 (8%)  — rag_analysis, serverless
직접 반환 (serializer.data)        : 9개 (38%) — 부분 또는 단독 사용
Flat dict ({key: value} 임의 구조) : 17개 (71%) — 가장 흔함
혼용 (같은 파일 2개 이상 패턴)     : 11개 (46%) — 일관성 위험
```

---

## HTTP 상태 코드 일관성

### 1) status 모듈 사용 vs 하드코딩

| 패턴 | 파일 수 | 대표 예시 |
|------|--------|----------|
| `status.HTTP_*` 모듈 일관 사용 | 18개 | `stocks/views.py` L11 import 후 전역 사용 |
| 하드코딩 (`status=200`, `status=202`) | 3개 | `sec_pipeline/views.py` L40/44/46, `stocks/views.py` L986 |
| 성공 응답 시 status 미명시 (기본 200) | 24개 거의 전부 | `Response(serializer.data)` 형태 |
| `import status` 후 미사용 | 1개 | `sec_pipeline/views.py` L9 (import만 있고 하드코딩 사용) |

### 2) POST 생성 시 200 vs 201

| 파일 | 201 사용 라인 | 200 (기본) 사용 라인 | 평가 |
|------|--------------|---------------------|------|
| `users/views.py` | L105, 288, 631, 723, 910 | — | ✅ POST 생성 시 일관 적용 |
| `rag_analysis/views.py` | L84, 164, 346 | — | ✅ 일관 적용 |
| `serverless/views_admin.py` | L568 | L184 외 | ⚠️ 조건부 사용 |
| `validation/api/views.py` | — | L484 (POST) | ❌ 생성에도 200 |
| `news/api/views.py` | — | 다수 | ❌ POST에도 기본 200 |
| `stocks/views.py` | — | L986 (`HTTP_200_OK if any_success else HTTP_500`) | ❌ 201 미사용 |
| `thesis/views/thesis_views.py` | — | 미명시 (기본 200) | ❌ ViewSet 기본값 의존 |

**결론**: POST 201 사용 비율 약 40%. 명세-구현 불일치 발생 시 클라이언트가 응답 코드로 분기할 수 없음.

### 3) 에러 시 상태 코드 분포

| 코드 | 사용 빈도 | 사용 파일 (대표) |
|------|----------|----------------|
| 400 BAD_REQUEST | 매우 빈번 | 거의 모든 파일 (입력 검증 실패) |
| 401 UNAUTHORIZED | 드뭄 | `validation/api/views.py` L463/489만 명시적 사용 |
| 403 FORBIDDEN | **0건** | 직접 사용 사례 없음 (DRF permission_classes에 위임) |
| 404 NOT_FOUND | 빈번 | `get_object_or_404` 활용 + 명시적 반환 혼용 |
| 429 TOO_MANY_REQUESTS | 1건 | `serverless/views_admin.py` L369 (쿨다운) |
| 500 INTERNAL_SERVER_ERROR | 빈번 | `macro/views.py` 다수, `api_request/admin_views.py` |
| 503 SERVICE_UNAVAILABLE | 드뭄 | `stocks/views_exchange.py` L58, `chainsight/api/views.py` L381 |

### 4) 비즈니스 오류를 200으로 반환 (안티패턴)

| 위치 | 사례 |
|------|------|
| `validation/api/views.py` L67, L85 | `status=HTTP_200_OK`로 반환하면서 본문에 `'error': 'not_in_universe'` 포함 |

→ 클라이언트가 응답 본문을 파싱해야 에러 여부 판별 가능. HTTP 시맨틱과 본문 시맨틱이 분리되어 일관성을 해침.

---

## 에러 응답 형식

### 1) 에러 키 변종

| 키 형식 | 사용 파일 |
|---------|----------|
| `{'error': '문자열'}` | 대부분 (가장 빈번) |
| `{'error': {'code': ..., 'message': ..., 'details': ...}}` | `rag_analysis/views.py`, `serverless/views.py`, 일부 `stocks/views.py` (L587-596) |
| `{'error': serializer.errors}` (DRF 객체) | `stocks/views_screener.py` L66 |
| `{'message': '...'}` | `users/views.py` L161/208/216, `api_request/admin_views.py` L105/147/154 |
| `{'detail': '...'}` (DRF 기본) | DRF 예외 핸들러 자동 생성분 (명시 사용 사례 없음) |

### 2) 같은 파일 내 혼용 (위험)

| 파일 | 혼용 사례 |
|------|----------|
| `users/views.py` AddFavorite | L208 `{error}` + L216 `{message}` 함께 사용 |
| `serverless/views_admin.py` | L163 `{'error': '...'}` + L400 `{success, data}` 형식 |
| `stocks/views.py` | L207 단순 `{error}` + L587-596 중첩 `{error: {code, message}}` |
| `stocks/views_screener.py` | L66 `{error: serializer.errors}` (객체) + L374 `{error: 'message'}` (문자열) |
| `api_request/admin_views.py` | `{error}` + `{message}` 혼용 |

### 3) 누락 패턴

| 파일 | 문제 |
|------|------|
| `thesis/views/monitoring_views.py` | 에러 응답 자체가 구현되지 않음 (예외는 로깅만, 사용자에게 500 노출) |
| `sec_pipeline/views.py` | 에러 케이스 처리 부재 |
| `stocks/views_mvp.py` | try/except 없음 (`get_object_or_404`만 의존) |

### 4) DRF 기본 vs 커스텀

- **DRF 기본 (`{'detail': ...}`)**: 명시 사용 0건. 모든 커스텀 에러 응답이 `{'error': ...}` 또는 변종 사용.
- **DRF Exception Handler 사용 여부**: `EXCEPTION_HANDLER` 커스텀 설정 미확인 (settings.py 별도 검토 필요).

→ 결과: DRF가 자동 생성한 인증 실패 응답은 `{'detail': ...}`, 코드에서 명시한 응답은 `{'error': ...}`로 클라이언트 입장에서 두 형식이 혼재.

---

## 페이지네이션 현황

### 1) LIST API에서 페이지네이션 부재 사례

| 파일/함수 | 라인 | 패턴 |
|----------|------|------|
| `stocks/views.py` StockListAPIView | L85 | `Stock.objects.all()` — `pagination_class` 미설정인 generics.ListAPIView |
| `stocks/views.py` (다수) | L192/639/713/785 | `[:limit]` 또는 `[:5]` 슬라이싱으로만 제한 |
| `stocks/views_eod.py` | L78/119 | `[:50]`, `[:7]` 하드코딩 슬라이싱 |
| `stocks/views_search.py` | L56 | `[:10]` 하드코딩 |
| `stocks/views_screener.py` | — | 페이지네이션 없음, `limit=1000`까지 허용 |
| `stocks/views_indicators.py` | — | 슬라이싱도 페이지네이션도 없음 |
| `chainsight/api/views.py` | L149, L523-524 | `[:10]`, neighbors 제한 슬라이싱 |
| `news/api/views.py` | L2129 | `[:limit]` 슬라이싱 |
| `validation/api/views.py` | L105 | `peer_symbols[:5]` 슬라이싱 |
| `thesis/views/monitoring_views.py` AlertListView | L238 | `[:50]` 하드코딩 |
| `thesis/views/monitoring_views.py` IndicatorReadingsView | L269 | `min(..., 1825)` 상한 슬라이싱 |
| `users/views.py` PortfolioListCreateView | — | `.all()` 직접 반환, 페이지네이션 없음 |
| `macro/views.py` | 모두 | 페이지네이션 미사용 |

### 2) 페이지네이션 적용 사례

| 파일/함수 | 라인 | 방식 |
|----------|------|------|
| `users/views.py` WatchlistListCreateView | L602-620 | Django Paginator + `{'results', 'pagination'}` 응답 |
| `users/views.py` WatchlistStocksView | L822-840 | 동일 패턴 |
| `rag_analysis/views.py` UsageHistoryView | L796-824 | Django Paginator |

### 3) ViewSet 자동 페이지네이션

- `thesis/views/thesis_views.py`: ViewSet 사용하나 `pagination_class` 명시적 설정 없음. DRF 글로벌 설정에 의존하지만 (`config/settings.py` 별도 검증 필요) 명시 부재로 추적성이 떨어짐.

### 4) 위험도 평가

| 위험 | 영향 파일 | 심각도 |
|------|----------|-------|
| `Stock.objects.all()` 무제한 반환 (L85) | `stocks/views.py` StockListAPIView | 🔴 (전체 종목 N=수만 건 잠재) |
| `screener` `limit=1000` 한도 | `stocks/views_screener.py` | 🟠 (LLM/필터 결과 누적 시 메모리) |
| `news` 슬라이싱 의존 | `news/api/views.py` | 🟠 (히스토리 누적 위험) |
| 알림/지표 시계열 슬라이싱 | `thesis/views/monitoring_views.py` | 🟡 (사용자별 데이터, 상한 명확) |

---

## 권고사항

### P0 (즉시 도입 권장)

1. **표준 응답 래퍼를 전사 표준으로 격상**
   - `rag_analysis/views.py`와 `serverless/views.py`의 `create_success_response` / `create_error_response` 패턴을 `config/utils/responses.py` 등 공용 모듈로 승격
   - 신규 view 작성 시 표준 래퍼 사용을 코드 리뷰 게이트로 강제
   - 기존 ✅ 일관 파일(`exchange`, `screener`, `fundamentals`)의 `{success, data, meta}` 패턴과 통합 검토

2. **에러 응답 스키마 1종으로 통일**
   ```json
   {
     "success": false,
     "error": {"code": "string", "message": "string", "details": {...}},
     "meta": {"timestamp": "...", "request_id": "..."}
   }
   ```
   - DRF `EXCEPTION_HANDLER`를 커스터마이징하여 `{'detail'}` → `{'error'}` 자동 변환
   - `users/views.py`의 `{message}` ↔ `{error}` 혼용 우선 정리

### P1 (단기 — 2주 이내)

3. **LIST API 페이지네이션 강제**
   - DRF 글로벌 `DEFAULT_PAGINATION_CLASS` 설정 확인 후, 없으면 `PageNumberPagination` 기본화
   - `stocks/views.py` StockListAPIView를 우선 적용 대상으로 선정 (전체 종목 부하 위험)
   - 슬라이싱(`[:N]`) 패턴은 페이지네이션 클래스로 대체

4. **POST 생성 시 201 적용**
   - `validation/api/views.py` L484, `news/api/views.py`의 POST 엔드포인트 우선 수정
   - `stocks/views.py` L986의 `200 if any_success else 500` 안티패턴 재설계 (부분 성공 시 207 Multi-Status 또는 본문 분리)

### P2 (중기 — 1개월 이내)

5. **`status` 모듈 사용 강제**
   - `sec_pipeline/views.py`의 하드코딩 `status=200/202` 제거
   - lint 룰(예: flake8 커스텀 룰) 추가하여 하드코딩 차단

6. **비즈니스 오류 200 반환 안티패턴 제거**
   - `validation/api/views.py` L67/85의 `'not_in_universe'` 케이스를 적절한 4xx로 변경 (예: 422 Unprocessable Entity)

7. **`count` 산정 방식 통일**
   - `news/api/views.py`의 `articles.count()` vs `len(serializer.data)` 혼용 → 한 가지로 통일 (페이지네이션 도입 시 자동 해결됨)

### 참고: 영향 분석

| 변경 항목 | 클라이언트 호환성 | 마이그레이션 난이도 |
|----------|----------------|------------------|
| 응답 래퍼 통일 | 🔴 Breaking (프론트 전체 영향) | High — 점진적 적용 필요 (v2 API 분기 권장) |
| 에러 형식 통일 | 🟠 부분 Breaking | Medium — DRF Exception Handler로 백엔드 한 곳에서 통제 |
| 페이지네이션 강제 | 🔴 Breaking (응답 구조 변경) | High — `?page=N` 미지원 클라이언트 식별 필요 |
| 201 코드 적용 | 🟢 Non-breaking | Low — 클라이언트가 2xx 전체를 성공 처리하면 영향 없음 |
| status 모듈 사용 | 🟢 Non-breaking | Low — 코드 가독성만 개선 |

---

## 부록: 분석 메서드

- 분석 대상: `find . -name 'views*.py' -not -path '*migration*'` 로 식별된 27개 파일
- 분석 방식: 4개 병렬 Explore 에이전트가 앱 그룹별로 라인 단위 분석
- 검증 항목: 응답 래핑(4종), HTTP 상태 코드(8종), 에러 형식(3종), 페이지네이션(3종)
- 비분석 항목: WebSocket consumers, Celery tasks 응답 구조 (별도 감사 권장)
- 미검증: DRF 글로벌 설정(`config/settings.py`의 `DEFAULT_PAGINATION_CLASS`, `EXCEPTION_HANDLER`) — 후속 감사 시 통합 검토 필요
