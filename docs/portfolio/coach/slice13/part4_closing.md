# Slice 13 / Part 4 종결 보고

**작업 범위**: E5 + E6 DRF endpoint 묶음 (E1~E3 패턴 순수 복제)
**완료 일자**: 2026-05-21
**브랜치**: `slice13` (Part 3 commit `ae0a9e1` 위)
**비용**: $0 (real LLM 호출 0건, mock 기반)
**슬라이스 유형**: 표준 슬라이스 × 2 묶음 (+18~22 기대 → 실제 +20 PASS)

---

## 1. 작업 0 사실 확인 결과

### 1-1. E5 스키마 + 시그니처

| 항목 | 확인 결과 |
|------|----------|
| 입력 스키마 | `CommentaryInputE5` (`portfolio/schemas/commentary_input.py:158`) |
| 핵심 필드 | `extraction_targets: list[str]` (필수, min_length=1) + `time_series_context: Optional[TimeSeriesContext]` (선택) |
| ★ TimeSeriesContext | **#27 사용 유일 진입점** — Optional 필드, Pydantic 위임으로 자동 처리 |
| 출력 스키마 | `E5Output` (`portfolio/schemas/commentary_output.py:118`) |
| `run_e5_coach` 시그니처 | `(input, provider="haiku", client=None, max_tokens=2000, *, preset_id=None, metrics=None)` — E3 동형 |
| Legacy view | `coach_e5_adjustment` (`portfolio/views.py:64`) → `/api/coach/e5/adjustment/` (`urls.py:13`) |

### 1-2. E6 스키마 + 시그니처

| 항목 | 확인 결과 |
|------|----------|
| 입력 스키마 | `CommentaryInputE6` (`portfolio/schemas/commentary_input.py:171`) |
| 핵심 필드 | `analysis_results: dict[str, dict[str, Any]]` (필수) — 종목별 분석 결과 |
| 출력 스키마 | `E6Output` (`portfolio/schemas/commentary_output.py:125`) |
| `run_e6_coach` 시그니처 | E3 동형 (kwarg 동일) |
| Legacy view | `coach_e6_comparison` (`portfolio/views.py:187`) → `/api/coach/e6/comparison/` (`urls.py:21`) |

### 1-3. 경로 충돌 검토
- 신규 `/api/v1/coach/e5/` vs legacy `/api/coach/e5/adjustment/` — 다른 경로, 충돌 없음
- 신규 `/api/v1/coach/e6/` vs legacy `/api/coach/e6/comparison/` — 다른 경로, 충돌 없음

---

## 2. 핵심 설계 원칙 준수 검증

| 원칙 | 결과 |
|------|------|
| ADDITIVE — `portfolio/views.py` / `portfolio/urls.py` / `run_e5_coach` / `run_e6_coach` 무수정 | ✅ git diff 0 |
| Pydantic 단일 진실 소스 — DRF serializer는 얇은 어댑터 | ✅ (E3 패턴 답습) |
| IDENTICAL 31/31 PASS — service/LLM 경로 무수정 | ✅ |
| contract test가 LLM mock 기반 — real 호출 0 | ✅ |
| E1~E3 패턴 순수 복제 — 새 설계 미도입 | ✅ (E5/E6 각각 E3 동형 구조) |
| preset_id / metrics endpoint 미노출 (#66와 동일 정책) | ✅ (`call_kwargs` 검증으로 보증, E5/E6 각 1건) |

---

## 3. 변경 사항

| 파일 | 변경 |
|------|------|
| `portfolio/api/serializers.py` | E5/E6 Request + Response serializer 4개 추가 |
| `portfolio/api/views.py` | `coach_e5` + `coach_e6` view 추가 (E3 동형) |
| `portfolio/api/urls.py` | `coach/e5/` + `coach/e6/` 2줄 추가 |
| **신규** `portfolio/tests/api/test_e5_endpoint.py` | 10건 contract test |
| **신규** `portfolio/tests/api/test_e6_endpoint.py` | 10건 contract test |
| `docs/portfolio/coach/kpi_matrix.md` | §5 베이스라인 757로 갱신, Part 4 묶음 단서 명기 |

### 무수정 보증
- `portfolio/views.py` (legacy): git diff **0 lines** ✅
- `portfolio/urls.py` (legacy): git diff **0 lines** ✅
- `run_e5_coach` / `run_e6_coach` services: 무수정 ✅
- E1/E2/E3 view + serializer: 무수정 ✅

---

## 4. 종결 체크리스트

- [x] 회귀 전체 PASS — **757 passed, 1 skipped** (737 +20)
- [x] ★ KPI 단서: 표준×2 묶음은 표준 범위(+9~15) 초과 정상. ±30% 임계×2 [+12, +40] 기준 PASS
- [x] IDENTICAL 31/31 PASS (service/LLM 경로 무수정)
- [x] 기존 E5·E6 순수 view 동작 불변 (git diff 0)
- [x] POST `/api/v1/coach/e5/` — 200 / 400 / 429 / 500 / 502
- [x] POST `/api/v1/coach/e6/` — 200 / 400 / 429 / 500 / 502
- [x] contract test가 E5/E6 출력 계약 위반 시 FAIL (drift 안전망 각 1건)
- [x] 작업 0 결과 본 문서 §1 기록
- [x] kpi_matrix.md §5 갱신, KPI 묶음 단서 명기
- [x] 비용: real LLM 호출 0 → $0

---

## 5. 회귀 카운트 추이

| 단계 | 카운트 | Δ |
|------|--------|---|
| Part 3 종결 | 737 passed | — (baseline) |
| 작업 3 신규 테스트 (E5+E6 contract) | 757 | **+20** |
| **Part 4 종결** | **757 passed + 1 skipped** | **+20** |

> ★ KPI 평가 단서: Part 4는 E5·E6 **2진입점 묶음** → 회귀 +Δ가 표준 범위(+9~15)를
> 초과함은 의도된 결과. ±30% 임계(+6~20) × 2 = **[+12, +40]** 기준 평가 — **PASS**.
> 단일 진입점 임계로 평가하면 false alarm 발생 → 묶음 단서 명문화 필수.

---

## 6. contract test 커버리지 (각 10건, 총 20건)

E5 / E6 동일 구조:

| 카테고리 | 건수 | 항목 |
|---------|------|------|
| 정상 경로 (200) | 2 | 응답 구조 + EnOutput 역검증 + kwarg 미전달 검증 |
| 검증 실패 (400) | 4 | 필수 필드 누락 / 잘못된 타입 / non-dict body / invalid provider |
| Service 예외 | 3 | 500 (스택트레이스 미노출) / 429 (budget) / 502 (LLMRateLimitError) |
| Schema drift 안전망 | 1 | confidence 위반 시 serializer 차단 |
| **합계 (각 진입점)** | **10** | 총 20건 |

---

## 7. ADDITIVE 원칙 위반 신호 점검

- 기존 31 IDENTICAL 테스트 PASS ✅
- 기존 `portfolio/views.py` / `portfolio/urls.py` git diff 0 ✅
- `run_e5_coach` / `run_e6_coach` service signature 무수정 ✅
- E1/E2/E3 endpoint 동작 영향 없음 (회귀 carrier 30건 PASS 유지) ✅

---

## 8. E5/E6 endpoint 동작 요약

```
POST /api/v1/coach/e5/?provider=haiku
Body:
  {
    "portfolio_id": "...", "fetched_at": "...", "preset": "garp",
    "holdings": [...],
    "extraction_targets": ["per", "peg", "roe"],
    "time_series_context": { "current": 100, "window_4q": 80 }  // optional #27
  }
Response (200): { "output": E5Output(...), "llm_metadata": {...} }

POST /api/v1/coach/e6/?provider=haiku
Body:
  {
    "portfolio_id": "...", "fetched_at": "...", "preset": "garp",
    "holdings": [...],
    "analysis_results": { "AAPL": {...}, "MSFT": {...}, ... }
  }
Response (200): { "output": E6Output(...), "llm_metadata": {...} }

Errors (E5/E6 공통): 400 / 429 / 500 / 502
★ preset_id / metrics 필드는 본 endpoint에서 받지 않는다 (#66 분리 정책).
```

---

## 9. Part 5 진입 준비 (E4 — 마지막 endpoint)

- **다음 작업**: E4 endpoint 확장 → `/api/v1/coach/e4/` (대화 Q&A 진입점)
- **E4 특이점**: `CommentaryInputE4` — `user_question: str` + `conversation_history: list[dict]` 보유
- **예상 회귀 +Δ**: +9~13 (표준 슬라이스)
- **예상 비용**: $0
- **Part 5 종결 후**: 6개 endpoint 전체 완료 → #65 (기존 순수 view 최종 처리) 진입 가능

---

**Slice 13 Part 4 종결**. Part 5 (E4) 진입 대기.
