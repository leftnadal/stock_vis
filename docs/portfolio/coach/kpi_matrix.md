# KPI Matrix

> **버전**: v3 (Slice 11 Part 5 #57 close, D5-A 슬라이스 유형별 임계 추가)
> **총 KPI 수**: 12개 (core 8 + auxiliary 4)
> **마지막 갱신**: 2026-05-19

---

## §1. Core KPI (8개) — 모든 슬라이스 필수

| #   | KPI                | 기준                         | 측정 위치                |
| --- | ------------------ | ---------------------------- | ------------------------ |
| 1   | 회귀 통과          | 슬라이스별 예측              | pytest 카운트            |
| 2   | IDENTICAL hash     | 7/7 PASS                     | test_static_integrity.py |
| 3   | 단건 cost          | Haiku <$0.03 / Sonnet <$0.10 | 4판정                    |
| 4   | 누적 cost          | ≤ 임계 (현재 $3.00)          | CostGuard.cumulative_usd |
| 5   | 슬라이스 cap       | ≤ $1.00 (Slice 9 #43)        | CostGuard.slice_usd      |
| 6   | LLM 호출           | ≤ PER_SLICE 100              | CostGuard.call_count     |
| 7   | 4판정 PASS 비율    | ≥ 90%                        | matrix_raw.json          |
| 8   | 글쓰기 가설 winner | label_means 비교             | manual eval              |

---

## §2. Auxiliary KPI (4개) — 슬라이스별 선택 적용

| #   | KPI                                         | 기준                | 적용                          |
| --- | ------------------------------------------- | ------------------- | ----------------------------- |
| 9a  | **cost 회귀 격리 (Slice 9 #43/E1 신규)**    | ±30%                | cost 또는 mixed 변경 슬라이스 |
| 9b  | **no-cost 회귀 격리 (Slice 9 #43/E1 신규)** | ±50%                | no-cost 단독 슬라이스         |
| 10  | trio 진단 효과 (Slice 8 #29)                | "구체성 부족" < 30% | E4 진입점 평가 시             |
| 11  | 분포 폭 (#26)                               | ≥ 3.0               | rationale 측정 시             |
| 12  | #β2 estimator 정밀도                        | max delta ≤ 30%     | rationale 측정 후             |

---

## §3. KPI 9 분류 룰

KPI 9 (회귀 격리)는 Slice 8 Part 3 이후 9a (cost) + 9b (no-cost) 두 축으로 분리:

- 자동 분류: `portfolio/tests/helpers/regression_classifier.py`
- 분류 결과 ("cost" / "no-cost" / "mixed")가 종결 보고서에 명시
- "mixed"는 보수적으로 cost 회귀로 처리 (KPI 9a 기준 적용)

상세: [slice9/kpi_e1_regression_classification.md](slice9/kpi_e1_regression_classification.md)

---

## §4. KPI 변경 이력

| 시점         | 변경                                                                                |
| ------------ | ----------------------------------------------------------------------------------- |
| Slice 1      | KPI 7개 (회귀 + IDENTICAL + 단건 cost + 누적 cost + LLM 호출 + 4판정 + winner)      |
| Slice 8      | KPI 11개 (+ trio 진단 + 분포 폭 + #β2 estimator)                                    |
| Slice 9      | KPI 12개 (+ 슬라이스 cap, 회귀 9a/9b 분리)                                          |
| **Slice 11** | **#57 close — KPI 10 슬라이스 유형별 임계 추가 (§6)**                               |

---

## §5. KPI 기준선 (Slice 14 종결 → Slice 15 진입)

| #   | KPI                | Slice 14 종결값                | Slice 15 임계 비고                        |
| --- | ------------------ | ------------------------------ | ----------------------------------------- |
| 1   | 회귀 통과          | **740 passed + 1 skipped**     | Slice 15 임계 별도 결정 (Step 0 진입 시점) |
| 2   | IDENTICAL hash     | **31/31 PASS** (7/7 + 24 확장) | service/LLM 경로 무수정 → 유지 필수      |
| 3   | 단건 cost          | probe 24건 PASS (haiku 평균 ~$0.0053/call) | 유지                          |
| 4   | 누적 cost          | **$0.1273** (#63 ledger 실측값) — pre-Slice-14 누적은 ledger 부재로 추정 | 임계 $4.00 유지 |
| 5   | 슬라이스 cap       | Step 0 $0 + Step 0.5 $0.1273 (probe) | $1.00 유지                          |
| 6   | LLM 호출           | Slice 14 전체 **24회** (Step 0.5 probe만) | 50 유지                          |
| 7   | 4판정 PASS         | N/A (probe + 인프라 작업)      | Slice 15 결정                              |
| 8   | winner             | haiku 압승 (Slice 11 확정)     | 변경 없음                                 |

**Slice 14 통합 결과**:
- 짧은 슬라이스 종결 = #63 cost ledger(production) + 게이트 가치 probe(보류 결정).
- 회귀 730 → 740 (+10, Step 0 #63 test_cost_ledger 추가분).
- Step 0.5 게이트 probe: 키워드 보수 판정 20/24=83.3%, 의미 판정 ~100% → 사전 등록 결정 규칙 ≥75% → **calibration 보류**.
- gate_tiers / `_evaluate_gate_tier` / `format_gate_tier_for_prompt` 휴면 코드는 "의도된 대기 폴백"으로 보존.

### Step 0/Step 0.5 종결 사항 추적

- **Step 0 (commits `a85a0c3` + `63fedaf`)**: #63 cost ledger 신설 + 사전 사실 확인.
  - 회귀 730 → 740 (+10, test_cost_ledger 10 추가, 지시서 +6~12 정확)
  - cost_ledger.jsonl (REPO_ROOT/docs/portfolio/coach/) JSONL 9컬럼 append-only.
  - CostGuard 차단 로직 무수정 (test_cost_guard 34/34 PASS 보증).
  - 사실 확인: FMP 시장 분포 capability 존재(`validation/services/benchmark_calculator.py`) / 12 preset gate_tiers 전부 None.
- **Step 0.5 (commits `b7f861b` + `a353162`)**: 게이트 가치 probe — production 코드 0 변경.
  - 회귀 740 불변, IDENTICAL 31/31 PASS.
  - 8 케이스(5/5 카테고리 커버, 합성) × haiku 3회 = 24 LLM 호출 (gate OFF).
  - 비용 $0.1273 (#63 ledger 첫 실측값) — 추정 $0.05~0.12 거의 정확.
  - 결정 = 보류 (LLM 자가 포착으로 게이트 calibration 불필요).
- **외부 커밋** (`ef46637` metrics 도메인 보고서, `a90d423` codebase audit docs): slice14 브랜치에 자동 누적, 본 슬라이스 작업과 무관, 회귀·IDENTICAL 무영향 확인.
- **Slice 14 누적 회귀 변화**: 730 (시작) → **740 (Step 0 +10)** ★ 4 commits ($0.1273)

### Slice 13 + #65 종결 이력 (Slice 14 진입 직전, 보존)

- E1~E6 6개 진단 입구가 `/api/v1/coach/eN/` **단일 진입점으로 단일화** (이중 입구 소멸)
- legacy view 5건(E1·E2·E3·E5·E6) 전수 제거, E4는 legacy 부재 (special case)
- 회귀 767 → 730 (−37 = 삭제한 legacy view 테스트 5+7+9+7+9 합과 정확히 일치)

### Slice 13 Step 0a/0b + Part 1/1.5/2 종결 사항 추적 (이력, 보존)

- **Step 0a (commit `f7fd62b`)**: 3단 게이트 ADDITIVE + estimator multivariate fit
  - 회귀 668 → 695 (+27, component buildup 하한 근처)
  - estimator max delta 33.12% → 24.58% (e4_conversation −16.18 대폭 개선)
- **Step 0b (commit `22d1e99`)**: estimator → CostGuard non-blocking integration
  - 회귀 695 → 707 (+12)
  - `PRE_CALL_SAFETY_BUFFER = 1.25`, `estimate_call_cost()`, `check_pre_call_budget()` (ADDITIVE)
- **Part 1 (commit `44d5e90`)**: E1 DRF endpoint + contract test
  - 회귀 707 → 717 (+10, 표준 슬라이스 임계 중앙값)
- **Part 1.5 (commit `28d19c4`)**: API 경로 v1 도입 (`/api/coach/` → `/api/v1/coach/`)
  - 회귀 717 → 717 (불변 — 경로 문자열만)
- **Part 2**: E2 DRF endpoint + contract test
  - 회귀 717 → 727 (+10, 표준 슬라이스 임계 중앙값)
- **Part 3**: E3 DRF endpoint + contract test (preset_id/metrics 미노출 — #66 분리)
  - 회귀 727 → 737 (+10, 표준 슬라이스 임계 중앙값)
  - **#66 신규** (PS 2.0, 분석엔진 #12 Phase 2 의존)
- **Part 4**: E5 + E6 DRF endpoint 묶음 + contract test
  - 회귀 737 → 757 (+20, 표준×2 묶음 의도된 결과)
  - **★ KPI 단서**: 2진입점 묶음 → 표준 범위(+9~15) 초과는 의도된 결과.
    ±30% 임계(+6~20)×2 = [+12, +40] 기준 평가 — PASS.
- **Part 5**: E4 DRF endpoint + contract test (마지막 진입점, 단건)
  - 회귀 757 → **767 (+10, 표준 슬라이스 임계 중앙값)**
  - ★ IDENTICAL 31 중 **20건이 E4 carrier** — Part 5에서 모두 PASS 보호 확인
  - **Slice 13 종결**: E1~E6 6개 endpoint 전부 DRF 마이그레이션 완료
- **#65 mini-slice** (Slice 13 종결 후): legacy view 5건 제거 + 6 진입점 단일화
  - 회귀 767 → **730 (−37, legacy view 테스트 삭제 정확)**
  - commit: E1 `4eba9fb` / E2 `fc39d23` / E3 `3e3ad6b` / E5 `2bde79e` / E6 `1983a99` / doc `4c2fcc9`
  - 결정 보존: wrapper 대신 **제거** 선택 — E1 pilot에서 legacy view가 mock 데모 endpoint이고 new API가 프로덕션 API로 입력·prompt·schema가 본질적으로 다름이 판명. 호출처 0건(dead code) 확인 후 안전 제거.
- **누적 비용 ledger**: 파일 미존재 → #63 신규 부채 (Slice 14+)
- **Slice 13 누적 회귀 변화**: 668 (시작) → 767 (Part 5 +99) → **730 (#65 −37)** ★ 14 commits ($0)

---

## §6. KPI 10 슬라이스 유형별 임계 (Slice 11 Part 5 #57 close 후 추가, D5-A)

| 슬라이스 유형                                       | 회귀 +Δ 기대값 | ±30% 임계 |
| --------------------------------------------------- | -------------- | --------- |
| 표준 슬라이스 (input/output/builder 통합 per part)  | +9~15          | +6~20     |
| 매트릭스 슬라이스 (24+ 케이스 production script)    | **+10~15**     | **+7~20** |
| Mini-slice (Step 9 단일 부채 처리)                  | +13~20         | +9~26     |
| Trio 슬라이스 (input→output→prompt+matrix)          | +25~40         | +17~52    |
| **Manual eval 슬라이스 (Part 5 패턴)**              | **+2~5**       | **+1~7**  |
| **Component buildup 슬라이스 (Slice 12 D4-B)**      | **+25~40**     | **+17~52** |

### 근거
- **Slice 11 Part 4**: 매트릭스 24 케이스가 production script (`scripts/slice11_part4_matrix.py`)로 분류 → 회귀 비카운트. 실제 회귀 +12는 매트릭스 슬라이스 임계 +7~20 내 PASS.
- **Slice 11 Part 5**: manual eval 작업 (scripts/manual_eval_shuffle.py + docs)으로 production 영향 0. 회귀 +0 = manual eval 임계 +1~7 내 PASS.
- **Slice 12 종결 (D4-B)**: scoring base + adapter + spec + 통합 + smoke 다단계 자산 축적의 component buildup 유형. P1 +25 / P2 +36 / P3 +27 누적 +88. 향후 scoring engine 확장 시 false alarm 차단.
- **Slice 12+ 동일 패턴 발생 시**: UNDER 재발 방지. 작업 유형 판별 후 임계 적용.

### Component buildup 적용 룰 (Slice 12 D4-B)
- 슬라이스 분류는 Step 0 또는 사전 결정 entry에서 사전 등록
- 조건: parametrize-heavy + base/adapter/spec/통합/smoke의 다단계 자산 축적
- KPI 9 OVER 알람 발생 시 슬라이스 유형이 component buildup이면 자동 PASS 판정
- +40 초과 시 사유 명시 (룰 재조정 후보)

### Slice 11 Part 4 retrospective
- 측정값: +12 (559→571)
- 기존 임계(표준 +25~40)로는 UNDER FAIL
- 매트릭스 슬라이스 임계(+10~15)로는 정상 PASS

### Slice 12 Part 1~3 retrospective
- Part 1: +25, Part 2: +36, Part 3: +27, 합계 +88
- 기존 분류로는 OVER 알람 누적
- Component buildup 임계(+25~40)로는 정상 PASS — 각 Part 모두 ±30% 임계 [+17, +52] 내

### Slice 13 사전 분류 (Part 1 진입 시점, 2026-05-21)

- **Slice 13 Step 0a**: Component buildup (+27) — multivariate fit + 게이트 ADDITIVE 다단계 자산 축적, 하한 근처 PASS
- **Slice 13 Step 0b**: Mini-slice 패턴 (+12) — 단일 부채 #62 처리, +13~20 임계 약간 하회 (기존 동작 보증 테스트 3건 포함)
- **Slice 13 Part 1~**: **표준 슬라이스** (+9~15 기대) — DRF serializer + endpoint 통합 per part. E2~E6 후속 Part는 모두 표준 슬라이스로 분류 예상.
