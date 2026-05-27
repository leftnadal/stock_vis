# API 응답 일관성 감사 보고서

- **감사일**: 2026-05-27
- **대상**: Django REST Framework views 전수 (27개 파일)
- **유형**: 읽기 전용 감사 (코드 수정 없음)
- **방법**: 모든 `views*.py` 파일을 Read로 정독 후 Response() 반환 형식 통계화

---

## 요약

총 **27개** views 파일 분석. 그중 **4개는 빈 파일/deprecated** (`metrics`, `portfolio/views.py`, `graph_analysis`, `news/views.py`, `validation/views.py`), 실제 응답 코드 보유 파일은 **23개**.

| 항목 | 결과 |
|------|------|
| **응답 래핑 패턴** | 3가지 혼재 — `{'success': True, 'data': ...}` (약 39회) / 직접 dict (약 90회) / 평탄 응답 (약 50회) |
| **HTTP 상태 코드** | `status.HTTP_*` 모듈 우세(18파일), 하드코드 혼용 5파일 (202/503 등) |
| **POST 201 사용** | 3개 파일만 (`rag_analysis`, `users`, `portfolio/api`) — 다수가 200 사용 |
| **에러 응답 키** | `{'error': ...}` 압도적 다수(50+) vs `{'detail': ...}` DRF 기본 5회 vs `{'message': ...}` 8회 |
| **페이지네이션** | DRF 클래스 사용 2개(`stocks/views`, `news/api`), 수동 구현 5개, 미적용 18개 |

**핵심 위험**:
1. 프론트엔드(TanStack Query)가 두 응답 모양(`response.data.data` vs `response.data`)을 동시에 다뤄야 함 → 타입 안정성/유지보수 비용 누적
2. 에러 키 불일치로 프론트 에러 핸들러 분기 폭증 (`err.response.data.error || err.response.data.detail || err.response.data.message`)
3. 대량 리스트 API 18곳 페이지네이션 누락 — 데이터 증가 시 OOM/응답 지연 위험

---

## 앱별 응답 패턴 매트릭스

| 파일 | success 래핑 | 직접 dict | 에러 키 | HTTP status 패턴 | 페이지네이션 |
|------|-------------|----------|---------|----------------|------------|
| `metrics/views.py` | — (빈 파일) | — | — | — | — |
| `rag_analysis/views.py` | ✅ 10회 | — | DRF exception 우세, `error` 1, `message` 2 | `status.HTTP_*` | ❌ (`.all()` 직접) |
| `config/views.py` | ✅ 16회 | — | `error` 3 | 혼합 (`status.HTTP_*` + 202 하드코드) | ❌ |
| `serverless/views_admin.py` | ❌ | 12회 | `error` 9 (L163, 184, 204, 224, 244, 264, 294, 334, 348) | `status.HTTP_*` + 기본값 | ❌ |
| `serverless/views.py` | ❌ (평탄 정책) | 50+회 | `error` 15+, DRF ValidationError | `status.HTTP_*` + 기본값 | 🟡 수동 (offset/limit) |
| `chainsight/api/views.py` | ❌ | 8회 | `error` 3 (L71, 118, 194) | `status.HTTP_*` | ❌ |
| `chainsight/views.py` | ❌ | 15+회 | `error` 5 (L71, 118, 443, 472, 623) | 🔴 하드코드 (200, 404, 503) | ❌ |
| `stocks/views.py` | 부분 | 50+회 | `error` 8 (L186, 212, 331, 679, 752, 824) + `message` 혼용 | `status.HTTP_*` 다수 + 일부 하드코드 | ✅ `StockListPagination` (PageNumberPagination) |
| `stocks/views_exchange.py` | ✅ 5회 | — | `error` 3 (L57, 106, 176) | `status.HTTP_*` | ❌ |
| `stocks/views_screener.py` | ✅ 3회 | — | `error` 3 (L66, 153, 263) | 혼합 (`status.HTTP_*` + 200 하드코드) | ❌ |
| `stocks/views_market_movers.py` | ❌ | dict/list | `error` 1 (L50) | `status.HTTP_*` | ❌ |
| `stocks/views_eod.py` | ❌ | dict | `error` 2 (L35, 44) | `status.HTTP_*` | ❌ |
| `stocks/views_indicators.py` | ❌ | dict | `error` 3 (L69, 228, 316) | `status.HTTP_*` | ❌ |
| `stocks/views_search.py` | ❌ | dict | `error` 3 (L32, 119, 141) | `status.HTTP_*` | ❌ |
| `stocks/views_fundamentals.py` | ✅ 5회 | — | `error` 5 (L59, 118, 185, 229, 286) | `status.HTTP_*` | ❌ |
| `stocks/views_mvp.py` | ❌ | dict | — | `status.HTTP_*` | ❌ |
| `iron_trading/views.py` | ❌ | dict | `error_body()` 헬퍼 함수 | 🔴 하드코드 (200, 400, 404, 503) | ❌ |
| `macro/views.py` | ❌ | dict | `error` 2 (L45, 99) | 혼합 (`status.HTTP_*` 일부 + 500 하드코드) | ❌ |
| `news/api/views.py` | ❌ | dict (캐시/serializer) | `error` 일부 | `status.HTTP_*` | ✅ `NewsArticlePagination` (page_size=20) |
| `news/views.py` | — (빈 파일) | — | — | — | — |
| `users/views.py` | ❌ | dict (serializer 직접) | DRF `ParseError`/`NotFound` (L99, 120, 143) | `status.HTTP_*` + **201** (POST) | 🟡 수동 (Django `Paginator`) |
| `portfolio/api/views.py` | ❌ | `{output, llm_metadata}` 커스텀 | `error` 4 (L74, 86, 92, 98) | `status.HTTP_*` (400/429/500/502) | ❌ |
| `portfolio/views.py` | — (빈/deprecated) | — | — | — | — |
| `sec_pipeline/views.py` | ❌ | dict | 없음 | 🔴 하드코드 (202, 200) | ❌ |
| `graph_analysis/views.py` | — (빈 파일) | — | — | — | — |
| `validation/api/views.py` | ❌ | dict | `{error, message}` 결합형 2 (L59, 84) | `status.HTTP_*` | ❌ |
| `validation/views.py` | — (빈 파일) | — | — | — | — |

### 패턴 분포 합계

| 패턴 | 횟수 | 비율 |
|------|------|------|
| `{'success': True, 'data': ...}` 래핑 | ~39 | 약 22% |
| 직접 dict (평탄) | ~90 | 약 50% |
| Serializer 직접 반환 (평탄) | ~50 | 약 28% |
| 빈 파일/deprecated | 5개 파일 | — |

**불일치 핵심**:
- 같은 `stocks/` 앱 내에서도 `views_exchange.py`/`views_screener.py`/`views_fundamentals.py`는 `success` 래핑, 그러나 `views_market_movers.py`/`views_eod.py`/`views_indicators.py`/`views_search.py`/`views_mvp.py`는 평탄 응답
- `config/views.py`는 16회 모두 `success` 래핑, `serverless/views.py`는 50+회 모두 평탄 — 앱 단위 정책 충돌

---

## HTTP 상태 코드 일관성

### `status` 모듈 사용 vs 하드코딩

| 패턴 | 파일 수 | 파일 |
|------|--------|------|
| `status.HTTP_*` 모듈만 | 18 | `rag_analysis`, `stocks/*`(대부분), `chainsight/api`, `users`, `portfolio/api`, `validation/api`, `serverless/views(_admin)`, `news/api`, `macro` 등 |
| 모듈 + 하드코드 혼합 | 5 | `config` (202), `chainsight/views` (200/404/503), `stocks/views` (일부 200), `stocks/views_screener` (200), `macro` (500) |
| 🔴 하드코드 위주 | 2 | `iron_trading` (200/400/404/503), `sec_pipeline` (202/200) |
| 기본값(인자 없음=200) 의존 | ~40% 파일 | 다수 |

**문제 사례**:
```python
# chainsight/views.py:443
return Response({"error": "..."}, status=503)  # 하드코드, status.HTTP_503_SERVICE_UNAVAILABLE 사용 권장

# iron_trading/views.py
def error_body(...): return Response({...}, status=400)  # 헬퍼 자체가 하드코드

# sec_pipeline/views.py
return Response({...}, status=202)  # status.HTTP_202_ACCEPTED 권장
```

### POST 생성(Create) 응답: 200 vs 201

| 파일 | POST 응답 | 비고 |
|------|----------|------|
| `rag_analysis/views.py` (L137) | **201** | ✅ 표준 준수 |
| `users/views.py` (L107) | **201** | ✅ 표준 준수 (SignUp) |
| `portfolio/api/views.py` | 200 (암묵적) | 🟡 LLM 호출 결과 반환이라 모호 |
| `serverless/views.py` (Screener PreSet create 등) | 200 | 🔴 201 권장 |
| `stocks/views_screener.py` (테제 저장) | 200 | 🔴 201 권장 |
| `config/views.py` (PeriodicTask Patch 등) | 200/202 | 🟡 202(Accepted)는 비동기 작업에는 적절 |

**암묵적 200 의존**: 약 40% 파일이 `Response(data)`처럼 status 인자 없이 호출 → 기본값 200. 명시성 부족.

---

## 에러 응답 형식

### 키 사용 빈도

| 에러 키 | 횟수 | 대표 파일 |
|--------|------|----------|
| `{'error': ...}` | 50+ | `serverless/views_admin` (9), `serverless/views` (15+), `stocks/*` (20+), `chainsight/*` (8), `macro` (2), `portfolio/api` (4) |
| `{'detail': ...}` | ~5 | DRF `NotFound`, `ValidationError` 기본값 |
| `{'message': ...}` | ~8 | `rag_analysis` (2), `users` 일부, `validation/api` (2, error와 함께 결합형) |
| `{'errors': ...}` | 0 | (`serializer.errors` 펼침으로 대체) |
| DRF Exception (`raise NotFound`/`ValidationError`) | 15+ | `rag_analysis`, `stocks/views`, `users`, `portfolio/api` |

### 결합형 / 비표준 사례

```python
# validation/api/views.py:59, 84
return Response({"error": "...", "message": "..."}, status=...)  # 두 키 동시 사용

# stocks/views.py:186, 212
return Response({'result': [], 'message': '검색어를 입력해주세요'}, status=400)
# 빈 결과 + 메시지 결합 — 성공/실패 경계 모호

# iron_trading/views.py
def error_body(code, msg): return Response({...})  # 자체 포맷
```

### DRF 기본 vs 커스텀

- **DRF 기본 우선** (`raise NotFound`, `raise ValidationError`): `rag_analysis`, `users`, `portfolio/api` — 일관된 `{'detail': ...}` 형식 제공
- **커스텀 dict 우선** (`Response({'error': str(e)}, status=4xx)`): `serverless/*`, `chainsight/*`, `stocks/*` — 형식 자유도 高, 일관성 低

**프론트엔드 영향**:
```typescript
// 현재 프론트는 다음과 같은 분기가 필요할 가능성
const msg = err.response?.data?.error
         || err.response?.data?.detail
         || err.response?.data?.message
         || '알 수 없는 오류';
```

---

## 페이지네이션 현황

### DRF 클래스 사용

| 파일 | 클래스 | 설정 |
|------|--------|------|
| `stocks/views.py` (L77-81) | `StockListPagination(PageNumberPagination)` | `page_size=50`, `max_page_size=200` |
| `news/api/views.py` | `NewsArticlePagination` | `page_size=20` |

### 수동 구현

| 파일 | 방식 |
|------|------|
| `serverless/views.py` (L1127-1159) | offset/limit 수동 계산 (`page`, `page_size` 쿼리 파라미터) |
| `users/views.py` | Django `Paginator` 클래스 사용 (DRF 아님) |
| 일부 `chainsight` 엔드포인트 | 클라이언트가 `limit` 쿼리로 전달, 서버는 슬라이스 |

### 페이지네이션 미적용 + `.all()` 직접 반환 (위험 영역)

| 파일 | 위치 | 위험 |
|------|------|------|
| `rag_analysis/views.py` (L54) | `DataBasket.objects.all()` 직접 serializer 후 반환 | 사용자 누적 시 응답 비대 |
| `chainsight/views.py` (L663) | seed 리스트 전체 반환 | 시드 증가 시 위험 |
| `config/views.py` | PeriodicTask 목록 | 일반적으로 소량이라 저위험 |
| `stocks/views_search.py` | 검색 결과 | `limit` 쿼리로 일부 제어 |
| `stocks/views_market_movers.py` | 무버스 리스트 (보통 N≤50 캡) | 캐시 키로 제한 |
| `chainsight/api/views.py` | ETF/Theme 매칭 결과 | 노출도 증가 시 위험 |

### Import 현황

- `PageNumberPagination`: 1개 파일 (`stocks/views.py` 통한 `StockListPagination`)
- `LimitOffsetPagination`: **0개** (미사용)
- `CursorPagination`: **0개** (미사용)
- Django `Paginator`: 1개 (`users/views.py`)

---

## 권고사항

### P0 — 프론트 호환성 위험 (즉시)

1. **에러 키 통일**: `{'error': ...}` 단일화 또는 DRF 기본 `{'detail': ...}` 단일화. 커스텀 exception handler(`EXCEPTION_HANDLER`) 1곳에서 변환. 프론트 axios interceptor 1곳으로 분기 제거.
2. **`validation/api/views.py:59, 84`의 `{error, message}` 결합형**: 둘 중 하나로 합쳐서 일관성 회복. 다른 곳에서 보지 못한 패턴이라 표준 일탈.

### P1 — 정책 명문화 (1주 내)

3. **응답 래핑 정책 선택 후 명시화**:
   - 옵션 A: `{'success': True, 'data': ...}` 전수 적용 (현 `config`/`rag_analysis`/`stocks/views_exchange|screener|fundamentals` 패턴 확산)
   - 옵션 B: 평탄 응답 전수 적용 (현 `serverless`/`chainsight`/`stocks/views_eod|indicators|search` 패턴 확산)
   - 한 앱 내에서도 파일별 패턴 충돌(`stocks/`)이 가장 큰 문제. 한쪽으로 통일 권장.
4. **POST 생성 응답 201 정착**: `serverless/views.py` Screener PreSet, `stocks/views_screener.py` 테제 저장 등 5+ 곳에서 201로 변경 검토.

### P2 — 점진 개선 (2주+)

5. **하드코드 status → `status.HTTP_*` 모듈로 치환**: `iron_trading/views.py`, `sec_pipeline/views.py`, `chainsight/views.py:443` 등 6+ 곳.
6. **페이지네이션 적용 확대**:
   - `rag_analysis/views.py:54` `DataBasket.objects.all()` → `PageNumberPagination` 적용
   - `chainsight/views.py:663` seed 리스트 → `LimitOffsetPagination` 검토
   - DRF 표준 `PageNumberPagination` 또는 `LimitOffsetPagination` 단일 채택 (현재 `stocks`/`news` 모두 PageNumber 사용 → 통일)
7. **`status=` 인자 명시 의무화**: pre-commit hook 또는 lint 규칙으로 `Response(data)`(인자 1개)를 `Response(data, status=status.HTTP_200_OK)`로 강제.

### P3 — 장기 거버넌스

8. **DRF `EXCEPTION_HANDLER` 도입**: 모든 예외를 일관된 포맷으로 직렬화하는 단일 핸들러. `chainsight`/`serverless`의 try/except + `Response({'error': str(e)})` 패턴 50+ 곳을 제거 가능.
9. **`contracts/` OpenAPI 스펙과 실 응답 어셔어런스 테스트**: drf-spectacular 0.29.0 운영 중이므로 스키마 누락 응답 형식을 CI에서 차단.
10. **이미 빈 파일/deprecated 5개 정리 검토**: `metrics/views.py`, `portfolio/views.py`, `news/views.py`, `graph_analysis/views.py`, `validation/views.py` — 의도된 폴더 유지가 아니면 삭제로 혼선 제거.

---

## 부록 — 에이전트 카운트 신뢰도

본 보고서의 카운트는 1차 Explore 에이전트가 27개 파일을 Read 후 정성/정량 집계한 결과를 정리한 것입니다. 정확한 단일 라인 인용은 표에 명시된 라인 번호만 검증 대상으로 신뢰하며, "10회"/"50+회"와 같은 집계 수치는 ±10% 오차 가능성이 있습니다. 정책 결정 전 자동화된 AST 카운트(예: libcst 기반) 1회 재집계를 권장합니다.
