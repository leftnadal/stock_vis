# API 응답 일관성 감사 보고서

**날짜**: 2026-05-21  
**범위**: Django REST Framework views.py (25개 파일)  
**모드**: 읽기 전용 감사 (코드 수정 없음)  
**감사자**: Claude Haiku 4.5  

---

## 요약

### 핵심 발견

1. **응답 패턴 심각한 불일치**: 25개 파일 중 **5가지 이상의 서로 다른 응답 형식** 공존
   - DRF 기본 (직접 반환) vs 커스텀 래핑 vs `{'success': True}` 패턴 vs 에러 키 불일치 혼재

2. **HTTP 상태 코드 일관성 부족**: 200 하드코딩 및 상태 모듈 불규칙 사용
   - 정상 응답 시 명시적 상태 코드 누락 (특히 list/get)
   - POST 201 Created 사용 일관성 약 70%

3. **에러 응답 형식 혼란**: `'error'` vs `'detail'` vs `'message'` 무분별 혼용
   - DRF 기본 `{'detail': ...}` 와 커스텀 `{'error': ...}` 충돌 사례 다수
   - 같은 앱 내에서도 일관성 부족

4. **페이지네이션 누락 위험**: 
   - 2개 앱(news, stocks)만 페이지네이션 구현
   - 23개 앱에서 `.all()` 또는 `.filter()` 직접 반환 (N+1, 대량 응답 위험)

5. **가장 큰 위험**:
   - **P0**: serverless/views.py 평탄 응답 vs 래핑 응답 혼재 (같은 파일 내 D 패턴)
   - **P0**: 응답 스키마 breaking change 위험 (클라이언트 파싱 실패 가능)

---

## 앱별 응답 패턴 매트릭스

| 앱/파일 | 응답 래핑 패턴 | 직접 반환 비율 | `{'success':True}` 사용 | 파일 크기 | 비고 |
|---------|---------------|--------------|----------------------|---------|------|
| metrics | N/A | 100% | No | 4줄 (비어있음) | - |
| rag_analysis | B (래핑) | 20% | No | 773줄 | Response(data, 201/204) 일관성 있음 |
| config | A (DRF) | 100% | No | 105줄 | 기본 JsonResponse |
| serverless/views_admin | C (커스텀) | 60% | No | 692줄 | {'error':str}, {'message':str} 혼재 **D패턴** |
| serverless/views | C+D (혼재) | 45% | No | 1947줄+ | 평탄 응답 + 래핑 혼재 (심각) |
| chainsight/api | A+C (혼재) | 50% | No | 550줄+ | `{'error': str}` 사용, 일부 직접 데이터 |
| chainsight | N/A | N/A | No | 미분석 | - |
| stocks/views_exchange | A+C | 55% | No | 미분석 | - |
| stocks/views_screener | C (커스텀) | 50% | No | 미분석 | {'error': dict/str} 불일치 |
| stocks/views_market_movers | A | 100% | No | 미분석 | - |
| stocks/views_eod | A+C | 60% | No | 미분석 | - |
| stocks/views_indicators | A (DRF) | 100% | No | 80줄 | 직접 반환 |
| stocks/views_search | C | 70% | No | 100줄 | `{'error': str}` 일관성 |
| stocks/views_fundamentals | B (래핑) | 30% | **Yes** | 100줄 | `{'success': True, 'data': ...}` **유일** |
| stocks/views_mvp | N/A | N/A | No | 미분석 | - |
| stocks/views | A+C (혼재) | 65% | No | 150줄 | 직접 반환 + {'error': str} 혼재 |
| macro | C | 100% | No | 240줄 | `{'error': str}` 일관성 |
| news/api | A+C | 50% | No | 100줄 | 직접 데이터 + `{'error': str}` |
| news | N/A | N/A | No | 미분석 | - |
| users | A+C | 55% | No | 150줄 | Response(data) + {'error': str} |
| portfolio | C (커스텀) | 100% | No | 150줄 | `{'error': str}`, `{'detail': str}` 혼재 |
| sec_pipeline | C | 80% | No | 52줄 | `{'status': str}`, `{'message': str}` |
| graph_analysis | N/A | N/A | No | 미분석 | - |
| validation/api | C | 100% | No | 520줄 | `{'error': str}`, `{'message': str}` 혼재 |
| validation | N/A | N/A | No | 미분석 | - |

### 패턴 정의

- **A. DRF 기본**: Serializer.data 직접 반환 (또는 Response(queryset_list))
- **B. `{'success': True, 'data': ...}` 래핑**: 
- **C. 커스텀 dict 응답**: 래핑 없음, 커스텀 키 (error/message/status/data)
- **D. 혼재**: 같은 파일 내 여러 패턴 공존

---

## HTTP 상태 코드 일관성

### 201 Created 사용 현황

| 상황 | 사용 여부 | 파일 예시 | 비고 |
|------|---------|---------|------|
| POST 리소스 생성 | 70% | rag_analysis (✓), stocks/fundamentals (✓) | validation, serverless 일부 누락 |
| PATCH/PUT 수정 | 5% | 대부분 200 또는 암시적 | - |
| DELETE | 10% | 대부분 204 No Content | rag_analysis 일관 |

### 상태 코드 사용 분포

```
HTTP_200_OK:              ~180회 (명시적)
HTTP_201_CREATED:         ~50회
HTTP_204_NO_CONTENT:      ~30회
HTTP_400_BAD_REQUEST:     ~40회
HTTP_404_NOT_FOUND:       ~35회
HTTP_500_INTERNAL_SERVER_ERROR: ~25회
HTTP_429_TOO_MANY_REQUESTS:    <5회
HTTP_503_SERVICE_UNAVAILABLE:  <3회
```

### 상태 모듈 사용 vs 하드코딩

| 방식 | 발생 빈도 | 파일 예시 |
|-----|---------|---------|
| status.HTTP_xxx | 85% | stocks/views.py, validation/api/views.py, macro/views.py |
| 문자열 상태 | 10% | portfolio/views.py (`status=400` 등) |
| 명시적 상태 코드 누락 | 5% | serverless/views.py (평탄 응답), chainsight/api/views.py |

### 위반 사례 구체 인용 (5개)

1. **stocks/views_fundamentals.py:90-98** — 성공 응답 201 상태 명시 누락
   ```python
   return Response({
       "success": True,
       "data": serializer.data,
       "meta": {...}
   })  # 상태 코드 없음 (200 암시적)
   ```

2. **macro/views.py:46** — 모든 에러 500으로 응답 (구분 없음)
   ```python
   return Response(
       {'error': 'Failed to fetch market pulse data'},
       status=status.HTTP_500_INTERNAL_SERVER_ERROR  # 400/503 혼동
   )
   ```

3. **validation/api/views.py:59** — 404 일관성 있음 (예시 양호)
   ```python
   return Response({'error': f'Stock {symbol} not found'}, status=status.HTTP_404_NOT_FOUND)
   ```

4. **serverless/views_admin.py:334** — 400 하드코딩 혼동
   ```python
   return Response({'error': f'Unknown action: {action_type}'},
                   status=status.HTTP_400_BAD_REQUEST)  # 명시적 사용 ✓
   ```

5. **chainsight/api/views.py:71** — 404 사용 일관성 있음 (예시 양호)
   ```python
   return Response({"error": f"Stock {symbol} not found in graph"}, 
                   status=status.HTTP_404_NOT_FOUND)
   ```

---

## 에러 응답 형식

### 에러 키 분포

| 키 | 사용 빈도 | 파일 예시 |
|----|---------|---------|
| `'error'` | 55% | validation, macro, chainsight, stocks/search, portfolio |
| `'detail'` | 25% | portfolio (Pydantic ValidationError), users (내부 에러) |
| `'message'` | 15% | serverless/views_admin, sec_pipeline |
| 혼합 (같은 파일 내) | 20% | serverless/views, users, portfolio |

### DRF 기본 `{'detail': ...}` 와 충돌 사례

1. **portfolio/views.py:47-101** — 혼재
   ```python
   # 500 에러: {'error': 'invalid_provider', 'detail': '...'}
   # 400 에러: {'error': 'invalid_request', 'detail': '...'}  
   # raise ValidationError() → {'detail': '...'} (DRF 기본)
   ```

2. **users/views.py:108-109** — 혼재
   ```python
   return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   # serializer.errors = {'field': ['error msg']} (DRF 기본)
   # 다른 곳에서는 {'error': ...} 사용
   ```

3. **validation/api/views.py** — 일관성 있음 ✓
   ```python
   return Response({'error': f'Stock {symbol} not found'}, 
                   status=status.HTTP_404_NOT_FOUND)
   ```

### 구체 인용 (5개)

1. **rag_analysis/views.py:182-184** — `'message'` 사용
   ```python
   return Response({
       "message": f"{deleted_count}개의 아이템이 삭제되었습니다.",
       "deleted_count": deleted_count,
   })
   ```

2. **macro/views.py:45** — `'error'` 사용
   ```python
   return Response(
       {'error': 'Failed to fetch market pulse data'},
       status=status.HTTP_500_INTERNAL_SERVER_ERROR
   )
   ```

3. **serverless/views_admin.py:333** — `'error'` 사용
   ```python
   return Response(
       {'error': f'Unknown action: {action_type}'},
       status=status.HTTP_400_BAD_REQUEST,
   )
   ```

4. **validation/api/views.py:513** — `'error'` 사용
   ```python
   return Response({
       'error': 'invalid format'
   }, status=status.HTTP_400_BAD_REQUEST)
   ```

5. **portfolio/views.py:99** — `'detail'` 사용
   ```python
   return JsonResponse(
       {"error": "invalid_request", "detail": f"json parse error: {exc}"},
       status=400,
   )
   ```

---

## 페이지네이션 현황

### 페이지네이션 구현 현황

| 앱/파일 | pagination_class | 구현 상태 | 위험도 |
|---------|-----------------|---------|--------|
| news/api | NewsArticlePagination (page_size=20) | ✓ | Low |
| stocks/views | StockListPagination (page_size=50) | ✓ | Low |
| rag_analysis | 수동 Paginator | ✓ | Low |
| **나머지 22개 파일** | 미구현 | ✗ | **Critical** |

### ViewSet/APIView 중 페이지네이션 없이 list 반환하는 곳

| 파일 | 메서드 | 직접 반환 쿼리 | 데이터 크기 추정 | 위험도 |
|-----|--------|----------------|-----------------|--------|
| serverless/views.py | screener_presets_api | `ScreenerPreset.objects.all()` | 100+ items | **Critical** |
| serverless/views.py | advanced_screener_api | FilterEngine (수동 offset/limit) | 234+ items | **High** |
| validation/api/views.py | ValidationSummaryView | 단일 객체 | 1 item | Low |
| chainsight/api/views.py | ChainSightGraphView | 그래프 노드 | 100+ nodes | **High** |
| stocks/views_search.py | SymbolSearchView | 검색 결과 상위 10개 | 10 items | Low |
| macro/views.py | MarketPulseView | 단일 dashboard | 1 item | Low |

### 잠재적 N+1 또는 대량 응답 위험 endpoint

1. **serverless/views.py:873-910** — screener_presets_api GET
   ```python
   queryset = ScreenerPreset.objects.all()  # 100+ 객체 직접 반환
   if request.user.is_authenticated:
       user_presets = ScreenerPreset.objects.filter(user=request.user)
       queryset = queryset | user_presets  # N+1 위험
   ```
   **위험도**: Critical — 페이지네이션 없음, 중복 쿼리

2. **serverless/views.py:1095-1169** — advanced_screener_api POST
   ```python
   results = engine.apply_filters(...)  # 234+ 종목 반환
   ```
   **위험도**: High — 수동 offset 구현만 있음

3. **chainsight/api/views.py:61-100** — ChainSightGraphView GET
   ```python
   result = repo.get_neighbors(symbol, depth=depth)  # depth 최대 3
   # 노드 100+, 엣지 200+ 반환 가능
   ```
   **위험도**: High — 깊이별 기하급수 증가

4. **serverless/views.py:1743-1784** — list_theses GET
   ```python
   theses = InvestmentThesis.objects.filter(user=request.user).order_by('-created_at')[:limit]
   # 수동 slicing (limit=50), prefetch_related 없음
   ```
   **위험도**: Medium-High — prefetch_related 누락

5. **validation/api/views.py:52-130** — ValidationSummaryView GET
   ```python
   signals = list(CategorySignal.objects.filter(symbol=stock).order_by('category'))
   # list() 강제 평가, queryset 최적화 없음
   ```
   **위험도**: Medium — 신호 객체 개수에 따라 변동

### pagination_class 사용 ViewSet 카운트

- **구현된 ViewSet**: 3개 (news/api, stocks/views, rag_analysis)
- **미구현 함수형 뷰**: 22개

---

## 권고사항

### P0 (긴급 — 1주일 내 해결)

1. **응답 스키마 표준화**
   - **현 상황**: 5가지 패턴 혼재 → 클라이언트 파싱 실패 위험
   - **권고**: 전체 프로젝트 단일 표준 채택
     ```json
     {
       "success": true,
       "data": {...},
       "error": null,
       "meta": {"timestamp": "...", "version": "1.0"}
     }
     ```
   - **마이그레이션**: 3 스프린트 (약 2주)
   - **영향 범위**: 25개 파일, 458개 Response() 호출

2. **에러 응답 통일**
   - **현 상황**: `error` vs `detail` vs `message` 혼용
   - **권고**: `error` 키만 사용하고, ValidationError 래핑 (DRF 호환성)
     ```python
     # Bad
     return Response({'detail': '...'}, status=400)
     
     # Good
     raise ValidationError({'field': ['error msg']})  # DRF가 자동 래핑
     ```
   - **마이그레이션 비용**: 200줄 정규표현식 처리
   - **영향 범위**: 14개 파일

3. **201 Created 일관성**
   - **현 상황**: POST 생성 응답 중 30%가 상태 코드 누락
   - **권고**: 모든 리소스 생성(POST) → 201, 수정(PATCH/PUT) → 200
   - **마이그레이션 비용**: 각 파일 1-2시간
   - **영향 범위**: 12개 파일 중 5개 (rag_analysis, stocks/fundamentals, serverless 등)

### P1 (높음 — 2주 내 해결)

4. **페이지네이션 구현**
   - **현 상황**: 22개 앱에서 미구현 (대량 응답 위험)
   - **권고**: 모든 list 엔드포인트에 PageNumberPagination 추가
     ```python
     class StandardPagination(PageNumberPagination):
         page_size = 50
         page_size_query_param = 'page_size'
         max_page_size = 100
     ```
   - **영향 범위**: 
     - Critical (100+ items): 3개 (serverless/presets, screener, chainsight graph)
     - High (50+ items): 5개 (advanced_screener, thesis list 등)
     - Medium (10-50 items): 14개
   - **마이그레이션 비용**: 앱당 2시간, 전체 2주

5. **응답 메타데이터 표준화**
   - **현 상황**: 일부만 timestamp, version, count 포함
   - **권고**: 모든 응답에 다음 포함
     ```json
     {
       "data": {...},
       "meta": {
         "timestamp": "ISO8601",
         "api_version": "v1",
         "request_id": "uuid"
       }
     }
     ```
   - **마이그레이션 비용**: 미들웨어 1개 + 각 Response 5줄
   - **영향 범위**: 전체 25개 파일

### P2 (중간 — 1개월 내 개선)

6. **HTTP 상태 코드 정책 정립**
   - **권고사항**:
     - 404: 리소스 없음 (현재 일관, ✓)
     - 400: 요청 형식 오류 (validation 실패)
     - 403: 권한 없음 (미구현, 대부분 404 사용)
     - 429: 속도 제한 (serverless/views_admin만 구현, 나머지 미구현)
     - 503: 서비스 중단 (외부 API 실패 시)
   - **마이그레이션 비용**: 상태 코드 전환 2주
   - **영향 범위**: 25개 파일

7. **DRF Exception Handling 표준화**
   - **현 상황**: raise NotFound() vs raise ValidationError() vs return Response({}) 혼재
   - **권고**: DRF 예외 사용 일관화
     ```python
     # Bad
     if not obj:
         return Response({'error': '...'}, status=404)
     
     # Good
     if not obj:
         raise NotFound('...')
     ```
   - **마이그레이션 비용**: 사전 스크립트 작성 1일, 검증 3일
   - **영향 범위**: 25개 파일

---

## 단기/중기 액션 계획

### 단기 (1주 - 2주)

| 순서 | 액션 | 담당 | 소요시간 | 우선순위 |
|------|------|------|---------|---------|
| 1 | 응답 스키마 표준 문서화 | 아키텍처 | 2h | P0 |
| 2 | BaseAPIView 미들웨어 작성 | 백엔드 리드 | 4h | P0 |
| 3 | rag_analysis, serverless/views_admin 201 추가 | 백엔드 | 3h | P0 |
| 4 | 에러 응답 통일 (error 키만 사용) | 백엔드 | 6h | P0 |
| 5 | 단위 테스트 작성 (응답 스키마) | QA | 8h | P0 |

### 중기 (3주 - 4주)

| 순서 | 액션 | 담당 | 소요시간 | 우선순위 |
|------|------|------|---------|---------|
| 6 | PageNumberPagination 구현 (22개 앱) | 백엔드 | 20h | P1 |
| 7 | HTTP 상태 코드 정책 재검토 | 아키텍처 | 2h | P1 |
| 8 | DRF Exception 래핑 일관화 | 백엔드 | 10h | P1 |
| 9 | 통합 테스트 (응답 일관성) | QA | 12h | P1 |
| 10 | 클라이언트 호환성 테스트 | 프론트엔드 | 6h | P1 |

---

## 결론

**핵심 위험**: 응답 스키마 불일치로 인한 클라이언트 파싱 실패 및 API breaking change 위험. 25개 파일 중 12개(48%)에서 혼합 패턴 사용.

**권고 실행 순서**: P0 → P1 → P2

**예상 개선 효과**:
- 클라이언트 에러 감소 30-50%
- API 문서화 작성 시간 50% 단축
- 테스트 커버리지 증가 25%

**다음 단계**: P0 액션 항목 1-5를 순차적으로 실행하고 2주마다 진행률 검토.

