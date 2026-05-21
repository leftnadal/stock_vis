# Slice 13 / Step 0b 종결 보고

**작업 범위**: estimator → CostGuard integration (#62 close, non-blocking 모드)
**완료 일자**: 2026-05-21
**브랜치**: `slice13` (Step 0a commit `f7fd62b` 위)
**비용**: $0 (실측 1회 미실시 — 선택 사항)

---

## 1. 핵심 설계 원칙 준수 검증

| 원칙 | 결과 |
|------|------|
| CostGuard `cumulative_usd`/`reset_for_slice`/50콜 budget guard 동작 무수정 | ✅ (3건 회귀 테스트 PASS) |
| estimator 추정값은 사전 추정 / 사후 실측 분리 (record_* 미호출) | ✅ (`test_estimate_call_cost_does_not_record_anything`) |
| SAFETY BUFFER 1.25 적용 (estimator max delta 24.58% 흡수) | ✅ (`PRE_CALL_SAFETY_BUFFER` 상수 분리) |
| IDENTICAL 7/7(31 테스트) 보호 | ✅ (31/31 PASS — non-blocking이라 해시 불변) |

---

## 2. 변경 사항

### 2-1. `portfolio/llm/cost_guard.py`

**신규 상수**:
```python
PRE_CALL_SAFETY_BUFFER: float = 1.25  # estimator max delta 24.58% 보수적 흡수
```

**신규 메서드 (2건, ADDITIVE — 기존 메서드 한 줄도 무수정)**:
- `estimate_call_cost(input_text, expected_output_chars, entry_point, model) -> float`
  - 지연 import로 `_ANTHROPIC_PRICING`, `estimator_v3` 로딩 (Django settings 충돌 회피)
  - 미등록 모델 → sonnet 단가 fallback (`client.py:296~297` 동일 정책)
  - 반환: buffer 미적용 원시 USD 추정
- `check_pre_call_budget(estimated_cost_usd) -> dict`
  - buffered = raw × 1.25
  - slice_usd + buffered > cap → `would_exceed_slice_cap=True` + WARNING 로그
  - cumulative_usd + buffered > threshold → `would_exceed_threshold=True` + WARNING 로그
  - ★ **raise 없음** (non-blocking) — caller가 결과 dict로 판단

### 2-2. 신규 테스트 — `portfolio/tests/test_cost_guard_pre_call.py` (12건)

| 카테고리 | 건수 | 항목 |
|---------|------|------|
| 비용 산정 | 4 | haiku/sonnet/unknown_model fallback / record 영향 없음 |
| Buffer + non-blocking | 4 | PRE_CALL_SAFETY_BUFFER 상수 + 1.25 곱 + within-budget no-warning + over-cap/threshold WARNING only |
| 기존 동작 불변 | 3 | record_call / reset_slice / 50콜 guard |
| 합계 | **12** | (목표 +5~9 약간 상회) |

---

## 3. 종결 체크리스트

- [x] 회귀 전체 PASS — **707 passed, 1 skipped** (Step 0a 695 +12, 목표 +5~9 약간 상회)
- [x] IDENTICAL 31/31 PASS (★ non-blocking 설계로 해시 불변)
- [x] 기존 CostGuard 동작 불변 (cumulative/slice/reset/50콜 guard 테스트 PASS)
- [x] `estimate_call_cost` + buffer 1.25 정상 작동
- [x] non-blocking 확인 (cap/threshold 초과 추정 시 WARNING만, raise 없음)
- [ ] 실측 1회 delta 보고 — **미실시** (선택 사항, $0 우선)
- [x] #62 close, #64 신규 등록 (debts.md §1 + §2 갱신)
- [x] 비용 $0 (실측 미실시)

---

## 4. 회귀 카운트 추이

| 단계 | 카운트 | Δ |
|------|--------|---|
| Step 0a 종결 | 695 passed | — (baseline) |
| Step 0b 신규 테스트 (cost_guard pre-call) | 707 | +12 |
| **Step 0b 종결** | **707 passed + 1 skipped** | **+12** |

> 목표 +5~9 약간 상회 (3건). cost_guard pre-call 12건 중 "기존 동작 불변 보증" 3건이 회귀 보호용으로 추가됨.

---

## 5. ADDITIVE 원칙 위반 신호 점검

- 기존 31 IDENTICAL 테스트 PASS → LLM 호출 경로 영향 없음 ✅
- 기존 cost_guard 19건 PASS → cumulative/slice/reset/50콜 guard 동작 무수정 ✅
- 신규 메서드 호출 → cumulative_usd/slice_usd/records 미변경 검증 (test_estimate_call_cost_does_not_record_anything) ✅

---

## 6. 부채 변동

| ID | 상태 변동 | 비고 |
|----|----------|------|
| **#62** | 신규 → **close** | non-blocking 모드로 도입 (estimate_call_cost + check_pre_call_budget) |
| **#64** | **신규** (PS 1.0, Slice 14+) | blocking 차단 모드 분리 — estimator delta 24.58% 흡수 후 검토 |
| **#61** | 단서 추가 | "estimator 정밀화와 함께 `PRE_CALL_SAFETY_BUFFER` 계수 재조정 대상" |

---

## 7. Step 0b 미실시 항목

**실측 1회 (선택 사항)**: 비용 절약을 위해 미실시. 후속 슬라이스에서 진입점별 첫 호출 시 자연스럽게 estimate vs 실측 delta 비교 가능 (estimator delta 모니터링은 #51/#62 통합 후속 작업).

---

**Slice 13 Step 0b 종결**. Slice 13 본체 (옵션 A — API 본체 추출) 또는 다른 진입 대기.
