# Slice 13 / Part 2 종결 보고

**작업 범위**: E2 DRF endpoint 추출 (E1 패턴 복제)
**완료 일자**: 2026-05-21
**브랜치**: `slice13` (Part 1.5 commit `28d19c4` 위)
**비용**: $0 (real LLM 호출 0건, mock 기반)
**슬라이스 유형**: 표준 슬라이스 (+9~13 기대 → 실제 +10 PASS)

---

## 1. 작업 0 사실 확인 결과

| 항목 | 확인 결과 |
|------|----------|
| **0-1 E2 스키마** | `CommentaryInputE2` (`portfolio/schemas/commentary_input.py:126`), `E2Output` (`portfolio/schemas/commentary_output.py:97`) |
| **0-2 run_e2_coach 시그니처** | `(input_data, provider="haiku", client=None, max_tokens=2000, *, preset_id=None, metrics=None)` — E1과 동형. Step 0a #60 kwarg 존재하나 Part 2에서는 미전달 (기존 동작 유지) |
| **0-3 기존 E2 순수 view 경로** | `/api/coach/e2/diagnostic-card/` (`portfolio/urls.py:15`, view `coach_e2_diagnostic_card`) — Part 2 신규 `/api/v1/coach/e2/`와 경로 충돌 없음 |

---

## 2. 핵심 설계 원칙 준수 검증

| 원칙 | 결과 |
|------|------|
| ADDITIVE — 기존 `portfolio/views.py` / `portfolio/urls.py` / `run_e2_coach` 무수정 | ✅ git diff 0 |
| Pydantic 단일 진실 소스 — DRF serializer는 얇은 어댑터 | ✅ (E1 패턴 답습) |
| IDENTICAL 31/31 PASS — service/LLM 경로 무수정 | ✅ |
| contract test가 LLM mock 기반 — real 호출 0 | ✅ |
| E1 패턴 답습 — 새 설계 미도입 | ✅ (serializer/view 코드 구조 동형) |

---

## 3. 변경 사항

| 파일 | 변경 |
|------|------|
| `portfolio/api/serializers.py` | `E2RequestSerializer` + `E2ResponseSerializer` 추가 (E1 동형) |
| `portfolio/api/views.py` | `coach_e2` view 추가 (E1 view와 처리 흐름 동일) |
| `portfolio/api/urls.py` | `path("coach/e2/", views.coach_e2)` 1줄 추가 |
| **신규** `portfolio/tests/api/test_e2_endpoint.py` | 10건 contract test (E1 패턴 복제) |
| `docs/portfolio/coach/kpi_matrix.md` | §5 베이스라인 727로 갱신, Part 1/1.5/2 종결 추적 추가 |

### 무수정 보증
- `portfolio/views.py` (legacy): git diff **0 lines** ✅
- `portfolio/urls.py` (legacy 라우팅): git diff **0 lines** ✅
- `run_e2_coach` service: 무수정 ✅
- `coach_e1` view + E1 serializer: 무수정 ✅

---

## 4. 종결 체크리스트

- [x] 회귀 전체 PASS — **727 passed, 1 skipped** (717 +10, 표준 슬라이스 +9~13 임계 정확히 중앙값 PASS)
- [x] IDENTICAL 31/31 PASS (service/LLM 경로 무수정)
- [x] 기존 E2 순수 view 동작 불변 (git diff 0)
- [x] POST `/api/v1/coach/e2/` — 정상 200 / 검증 실패 400 / 예외 500 / budget 429 / LLM 502
- [x] contract test가 E2Output 계약 위반 시 FAIL하도록 동작 (drift 안전망 1건)
- [x] 작업 0 사실 확인 결과가 본 문서에 기록됨
- [x] kpi_matrix.md §5 베이스라인 갱신
- [x] 비용: real LLM 호출 0 → $0

---

## 5. 회귀 카운트 추이

| 단계 | 카운트 | Δ |
|------|--------|---|
| Part 1.5 종결 | 717 passed | — (baseline) |
| 작업 3 신규 테스트 (E2 contract) | 727 | **+10** |
| **Part 2 종결** | **727 passed + 1 skipped** | **+10** |

> 표준 슬라이스 임계 +9~13, ±30% 임계 [+6, +17]. **임계 중앙값 PASS** — Part 1과 동일 +10 답습.

---

## 6. contract test 커버리지 (10건)

| 카테고리 | 건수 | 항목 |
|---------|------|------|
| 정상 경로 (200) | 2 | 응답 구조 + E2Output 역검증 (contract 핵심) |
| 검증 실패 (400) | 4 | 필수 필드 누락 (portfolio_return_1y) / 잘못된 타입 / non-dict body / invalid provider |
| Service 예외 | 3 | 500 (스택트레이스 미노출) / 429 (budget) / 502 (LLMRateLimitError) |
| Schema drift 안전망 | 1 | service confidence 위반 시 serializer 차단 |
| **합계** | **10** | (E1 동일 커버리지) |

---

## 7. ADDITIVE 원칙 위반 신호 점검

- 기존 31 IDENTICAL 테스트 PASS ✅
- 기존 `portfolio/views.py` / `portfolio/urls.py` git diff 0 ✅
- `run_e2_coach` service signature 무수정 (Step 0a kwarg는 Part 2에서 미전달) ✅
- E1 endpoint 동작 영향 없음 (E1 contract test 10/10 PASS 유지) ✅

---

## 8. E2 endpoint 동작 요약

```
POST /api/v1/coach/e2/?provider=haiku

Request body (JSON):
  {
    "portfolio_id": "...",
    "fetched_at": "2026-05-21T00:00:00Z",
    "preset": "garp",
    "holdings": [{ "ticker": "AAPL", "weight": 0.5 }, ...],
    "portfolio_return_1y": 0.12,
    "sector_allocation": { "IT": 0.6, "Healthcare": 0.2, ... }
  }

Response (200):
  {
    "output": E2Output(summary, key_observations, confidence, quoted_metrics),
    "llm_metadata": { provider, model, latency_ms, ... }
  }

Errors:
  400 — 요청 검증 실패
  429 — LLM budget 초과
  500 — service 예외 (스택트레이스 노출 금지)
  502 — LLM 호출 실패
```

---

## 9. Part 3 진입 준비

- **다음 작업**: E3 endpoint 동일 패턴 확장 → `/api/v1/coach/e3/` + E3Output contract test
- **E3 특이점 검토 필요**: Step 0a #60에서 E3는 `preset_id + metrics` kwarg를 이미 활용 중. Part 3에서는 이 kwarg를 endpoint에 노출할지(쿼리/바디) 결정 필요. 본 Part 2에서는 미적용.
- **예상 회귀 +Δ**: +9~13 (표준 슬라이스 동일)
- **예상 비용**: $0 (mock 기반 contract test)
- **남은 endpoint**: E3 → E4 → E5 → E6 (4건). 완료 시 #65 (기존 view 최종 처리) 진입.

---

**Slice 13 Part 2 종결**. Part 3 (E3) 진입 대기.
