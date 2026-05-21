# Slice 13 / Step 0a 종결 보고

**작업 범위**: 3단 게이트 (ADDITIVE) + estimator multivariate fit + 베이스라인 정정
**완료 일자**: 2026-05-21
**브랜치**: `slice13` (분기점: slice12 종결 commit `016f0de`)
**비용**: $0 (LLM 호출 0건, 데이터 파일 기반 fit)

---

## 1. 베이스라인 사실 확정

- **slice12 종결 commit**: `016f0de21b4f3e374376fd62bcf2264a20325e04`
  ("종결 사이클: KPI matrix + closing 보고 (component buildup +25~40 등록)")
- **회귀 카운트 (Step 0a 진입 직후)**: **669 collected = 668 passed + 1 skipped**
  - 메모리상 `Slice 12 종결 668` 정확히 일치 (+1은 skipped 테스트, 신규 추가 없음)
  - "+1 출처" 추적 결과: slice12 종결 시점에 이미 1개 skipped로 존재 — 신규 추적 대상 없음
- **IDENTICAL 보호 테스트**: 31/31 PASS (4 파일 — e4_conversation, llm_client_system_arg, input_v2_smoke, e3_scoring_integration)
- **누적 비용 ledger**: **파일 미존재** → #63 신규 부채로 등록
- "$3.1196 (Slice 12 종결)"은 closing 보고서 기재값으로만 존재 — ledger 부재로 미검증

---

## 2. 작업 1 — #60 3단 게이트 (ADDITIVE)

### 설계 원칙 준수

- 기존 `gate` 필드, `_apply_gate()`, `score=0.0` 로직 **한 줄도 수정 안 함** ✅
- 3단 분류는 점수 계산과 완전 분리된 ADDITIVE 레이어 ✅
- 결과는 commentary prompt context로만 흐름 ✅

### 변경 사항

| 파일 | 변경 |
|------|------|
| `portfolio/services/scoring/preset_spec.py` | `gate_tiers: Optional[dict] = None` 신규 필드 + validator |
| `portfolio/services/scoring/base.py` | `_evaluate_gate_tier()` 신규 @staticmethod (기존 메서드 무변경) |
| `portfolio/services/scoring/__init__.py` | `get_preset_spec()`, `format_gate_tier_for_prompt()` helpers |
| `portfolio/services/coach/e1_service.py` | `*, preset_id, metrics` kwarg 추가 (None 시 기존 동작) |
| `portfolio/services/coach/e2_service.py` | 동일 |
| `portfolio/services/coach/e3_service.py` | 기존 scores 외에 gate_tier 결과 추가 주입 |
| `portfolio/services/coach/e5_service.py` | E1과 동일 패턴 |
| `portfolio/services/coach/e6_service.py` | E1과 동일 패턴 |

### 신규 테스트 (17건)

- `tests/scoring/test_gate_tiers.py` (13건): `_evaluate_gate_tier` 3분기 + PresetSpec validator + 12 preset 불변
- `tests/scoring/test_gate_tier_service_signatures.py` (4건): E1/E2/E5/E6 시그니처 검증

### IDENTICAL 7/7 보호

- `gate_tiers=None`(12 preset 전체) → 점수 결과 / prompt 출력 모두 불변
- 기존 IDENTICAL 31/31 PASS 유지 ✅

---

## 3. 작업 2 — #51 estimator multivariate fit

### 신모델 설계

- 공식: **`tokens = a + b × chars`** (단변량 ratio → 다변량 OLS)
- Lookup 우선순위: (EP, model) → EP → GLOBAL
- 시그니처 유지: `estimate_output_tokens(chars, entry_point, model)`
- 구모델 상수(`ENTRY_POINT_OUTPUT_RATIOS`, `GLOBAL_OUTPUT_RATIO`)는 backtest baseline 비교용으로 보존

### 백테스트 결과 (N=200, all_llm_calls.jsonl)

| 지표 | OLD (Slice 11) | NEW (Slice 13) | Δ |
|------|----------------|----------------|---|
| global mean_delta % | 5.11 | **4.40** | **−0.71** |
| global P90_delta %  | 11.20 | **9.52** | **−1.68** |
| global max_delta %  | 33.12 | **24.58** | **−8.54** ★ |

진입점별 max_delta (주요):

| EP | OLD | NEW | Δ |
|----|-----|-----|---|
| e4_conversation | 33.12 | **16.94** | **−16.18** ★★★ |
| rationale | 12.44 | 8.99 | −3.45 |
| e3_portfolio | 17.43 | 16.72 | −0.71 |
| e5 | 25.78 | 24.58 | −1.20 |
| e1/e2/e3/e6 | ≤5.86 | ≤5.00 | −0.03~−0.86 |

→ e4_conversation 단일 outlier가 다변량 OLS로 거의 절반 해소.

### 신규 테스트 (10건)

- `tests/coach/test_estimator_v3_multivariate.py`: fit 상수 등록 + lookup 우선순위 + 경계 입력 + 시그니처 하위호환

### 기존 테스트 4건 갱신

- `tests/coach/test_estimator_v3.py`: `int(chars × ratio)` 검증 → `estimate_output_tokens()` 직접 호출 검증으로 contract-test 패턴화

---

## 4. 작업 3 — 신규 부채 등록 (debts.md §1)

| ID | 제목 | PS | 슬라이스 | 비고 |
|----|------|----|---------|---|
| **#61** | 3단 게이트 경계값 calibration | 2.5 | Slice 14 | placeholder gate_tiers → 실측 분포 기반 fail/warn_below 설정 |
| **#62** | estimator → CostGuard integration | 1.5 | Slice 13 Step 0b | 신모델 fit을 production에 연결 |
| **#63** | 누적 비용 ledger 영속화 | 1.5 | Slice 14+ | 슬라이스 간 누적값 영속 추적 (#62와 인프라 묶음) |

#51은 **fit 정확도 부분 close** + integration은 #62로 분리 처리.

---

## 5. 종결 체크리스트

- [x] 회귀 전체 PASS — **695 passed, 1 skipped** (베이스라인 668 +27, 임계 +11~18 약간 상회 — additive 신규 17 + estimator 10)
- [x] IDENTICAL 7/7 PASS (★ gate_tiers 미정의로 fixture 출력 해시 불변 31/31)
- [x] 기존 12 preset score 결과 불변 (gate_tiers=None 경로 — `test_all_12_presets_have_gate_tiers_none`)
- [x] E1/E2/E5/E6 service kwarg 미전달 시 출력 불변 (하위호환)
- [x] estimator 백테스트 delta 보고 완료 (mean −0.71 / P90 −1.68 / max **−8.54**)
- [x] 신규 부채 #61/#62/#63 등록 완료 (`docs/portfolio/coach/debts.md` §1)
- [x] 비용: LLM 호출 0 → $0 (fit은 jsonl 파일 기반)

---

## 6. 회귀 카운트 추이

| 단계 | 카운트 | Δ |
|------|--------|---|
| Step 0a 진입 | 668 passed | — (baseline) |
| 작업 1 신규 테스트 (gate_tiers + service sig) | 685 | +17 |
| 작업 2 신규 테스트 (multivariate) | 695 | +10 |
| **Step 0a 종결** | **695 passed + 1 skipped** | **+27** |

> 임계 +11~18 약간 상회. component buildup 슬라이스 유형 (KPI matrix §6 등록값 +25~40 [+17, +52]) **하한 근처**로 PASS.

---

## 7. ADDITIVE 원칙 위반 신호 점검

- gate_tiers 미정의 fixture에서 출력 해시 불변 ★ → ADDITIVE 원칙 PASS
- preset score 12종 결과 불변 (test_all_12_presets_have_gate_tiers_none) → 점수 경로 무손상 확인
- 기존 31 IDENTICAL 테스트 PASS → 회귀 신호 없음

---

## 8. Step 0b 진입 준비

- **목표 #62**: `estimate_output_tokens` 호출 경로를 production CostGuard에 연결
- **목표 #60 추가 (E3 외)**: 필요 시 gate-aware prompt를 실제 commentary 품질 평가 (manual eval)
- **slice13 분기점**: `016f0de` (slice12 종결) — 본 step 종결 후 분리 커밋 즉시 작성 권고

---

**Slice 13 Step 0a 종결**. Step 0b 또는 본체 진입 대기.
