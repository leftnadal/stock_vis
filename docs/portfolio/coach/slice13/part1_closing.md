# Slice 13 / Part 1 종결 보고

**작업 범위**: E1 DRF endpoint 추출 (serializer + endpoint + contract test)
**완료 일자**: 2026-05-21
**브랜치**: `slice13` (Step 0b commit `22d1e99` 위)
**비용**: $0 (real LLM 호출 0건, mock 기반)
**슬라이스 유형**: 표준 슬라이스 (+9~15 기대 → 실제 +10 PASS)

---

## 1. 핵심 설계 원칙 준수 검증

| 원칙 | 결과 |
|------|------|
| ADDITIVE — 기존 `portfolio/views.py` / `portfolio/urls.py` / `run_e1_coach` 무수정 | ✅ |
| Pydantic 단일 진실 소스 — DRF serializer는 얇은 어댑터 | ✅ (`_pydantic_errors_to_dict` 변환만) |
| IDENTICAL 31/31 PASS — service/LLM 경로 무수정 | ✅ |
| contract test가 LLM mock 기반 — real 호출 0 | ✅ |

---

## 2. 사전 작업 — 문서 동기화

### kpi_matrix.md §5/§6 갱신
- §5 헤더: "Slice 13 Step 0b 종결 → Part 1 진입"으로 교체
- 회귀 707, IDENTICAL 31/31, 누적 cost "ledger 부재로 미검증(#63)" 단서 명기
- §6에 Slice 13 사전 분류 추가: Step 0a = Component buildup / Step 0b = Mini-slice / Part 1~ = **표준 슬라이스**

### debts.md §4/§5 갱신
- §4 변화 요약: Slice 13 Step 0a+0b 기준으로 재작성 (close 2 / 신규 4 / 잔여 1, net +2)
- §5 진입점: Slice 14+ 기준으로 교체 — #61/#59/#63/#64/#65 우선순위 사전 등록

---

## 3. 변경 사항

### 3-1. 신규 파일 — `portfolio/api/` (DRF 패키지)

| 파일 | 역할 |
|------|------|
| `__init__.py` | 패키지 정의 + 설계 원칙 명시 |
| `serializers.py` | `E1RequestSerializer` / `E1ResponseSerializer` (Pydantic 어댑터) |
| `views.py` | `coach_e1` (POST endpoint, @api_view + @permission_classes([AllowAny])) |
| `urls.py` | `path("coach/e1/", views.coach_e1, name="coach_e1")` |

### 3-2. 수정 — `config/urls.py`

- 1줄 추가: `path('api/', include('portfolio.api.urls', namespace='portfolio_api'))`
- 기존 `path('api/', include('portfolio.urls'))` (legacy 순수 view) 무수정 유지

### 3-3. 신규 테스트 — `portfolio/tests/api/test_e1_endpoint.py` (10건)

| 카테고리 | 건수 | 항목 |
|---------|------|------|
| 정상 경로 (200) | 2 | 응답 구조 + E1Output 역검증 (contract 핵심) |
| 검증 실패 (400) | 4 | 필수 필드 누락 / 잘못된 타입 / non-dict body / invalid provider |
| Service 예외 | 3 | 500 (스택트레이스 미노출) / 429 (budget exceeded) / 502 (LLMRateLimitError) |
| Schema drift 안전망 | 1 | service가 계약 위반 출력 시 serializer가 잡아냄 |
| 합계 | **10** | (목표 +9~15 정확히 PASS 하한) |

---

## 4. 종결 체크리스트

- [x] 회귀 전체 PASS — **717 passed, 1 skipped** (Step 0b 707 +10, 표준 슬라이스 +9~15 PASS)
- [x] IDENTICAL 31/31 PASS (service/LLM 경로 무수정)
- [x] 기존 `coach/e1/garp/` view 동작 불변 (기존 회귀 테스트 PASS로 자동 보증)
- [x] POST `/api/coach/e1/` — 정상 200 / 검증 실패 400 / 예외 500 / budget 429 / LLM 502
- [x] contract test가 E1Output 계약 위반 시 FAIL하도록 동작 (`test_post_e1_service_returns_drifted_output_caught_by_serializer`)
- [x] kpi_matrix.md §5/§6, debts.md §4/§5 동기화 완료
- [x] #65 신규 등록 (E1~E6 마이그레이션 완료 후 기존 view 최종 처리)
- [x] 비용: real LLM 호출 0 → $0

---

## 5. 회귀 카운트 추이

| 단계 | 카운트 | Δ |
|------|--------|---|
| Step 0b 종결 | 707 passed | — (baseline) |
| 작업 3 신규 테스트 (contract test) | 717 | **+10** |
| **Part 1 종결** | **717 passed + 1 skipped** | **+10** |

> 표준 슬라이스 임계 +9~15, ±30% 임계 [+6, +20]. **정확히 임계 중앙값에 해당하는 안전 PASS**.

---

## 6. ADDITIVE 원칙 위반 신호 점검

- 기존 31 IDENTICAL 테스트 PASS ✅
- 기존 `portfolio/views.py` 코드 무수정 (git diff 0) ✅
- 기존 `portfolio/urls.py` 라우팅 무수정 ✅
- `run_e1_coach` service signature 무수정 (Step 0a kwarg는 Part 1에서 미전달) ✅
- 회귀 707 → 717: 표준 슬라이스 +9~15 임계 정확히 PASS ✅

---

## 7. API endpoint 동작 요약

```
POST /api/coach/e1/?provider=haiku

Request body (JSON):
  {
    "portfolio_id": "...",
    "fetched_at": "2026-05-21T00:00:00Z",
    "preset": "garp",
    "holdings": [{ "ticker": "AAPL", "weight": 0.5 }, ...],
    "garp_metrics": { "AAPL": { "per": 25, "peg": 1.3, ... }, ... }
  }

Response (200):
  {
    "output": E1Output(summary, key_observations, confidence, action_items, risk_flags),
    "llm_metadata": { provider, model, latency_ms, input_tokens, output_tokens, cost_usd }
  }

Errors:
  400 — 요청 검증 실패 (Pydantic 에러 평탄화)
  429 — LLM budget 초과 (LLMBudgetExceededError)
  500 — service 예외 (스택트레이스 노출 금지)
  502 — LLM 호출 실패 (LLMRateLimitError 등)
```

---

## 8. Part 2 진입 준비

- **다음 작업**: E2 endpoint 동일 패턴 확장 → `/api/coach/e2/` + E2Output contract test
- **예상 회귀 +Δ**: +9~15 (표준 슬라이스 동일)
- **예상 비용**: $0 (mock 기반 contract test)
- **남은 작업 (#65 선행)**: E3 → E4 → E5 → E6 endpoint 4건 마이그레이션 완료 시 #65 진입

---

**Slice 13 Part 1 종결**. Part 2 (E2) 진입 대기.
