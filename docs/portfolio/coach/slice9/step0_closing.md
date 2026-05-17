# Slice 9 Step 0 종결 보고서

> **작성일**: 2026-05-17
> **브랜치**: slice9 (slice8에서 분기)
> **종결 상태**: ✓ ALL PASS (KPI 6/6)

---

## §1. KPI 통과 현황 (6개)

| #   | 항목                 | 기준                            | 결과                                                                    | 통과 |
| --- | -------------------- | ------------------------------- | ----------------------------------------------------------------------- | :--: |
| 1   | 회귀 (no-cost)       | 458 → +18~25 (±50% deviation)   | **458 → 476 (+18, predicted +18, deviation 0.0%)**                      |  ✓   |
| 2   | IDENTICAL hash       | 7/7 PASS                        | 7/7 PASS (test_static_integrity.py 전건)                                |  ✓   |
| 3   | COST_POLICY.md       | 임계 $3.00 + cap $1.00          | threshold $3.00=True, cap $1.00=True                                    |  ✓   |
| 4   | CostGuard 인터페이스 | cap_per_slice + reset_for_slice | cap_per_slice=1.0, threshold=3.0, record_cost=True, check_warnings=True |  ✓   |
| 5   | E1 분류 룰           | docs + classifier 모두 존재     | docs=True, classifier=True                                              |  ✓   |
| 6   | 누적 cost 변화 없음  | $2.048 유지                     | Step 0은 LLM 호출 0건 (코드/docs/단위 테스트만)                         |  ✓   |

**판정**: ALL PASS

---

## §2. 부채 처리

| 부채                 | 상태   | 비고                                                       |
| -------------------- | ------ | ---------------------------------------------------------- |
| #43 COST_POLICY 갱신 | close  | 임계 $2.00 → $3.00, 슬라이스 cap $1.00 신설                 |
| E1 룰 보정           | close  | KPI 9a/9b 분리, regression_classifier 자동 분류 도입       |
| #44 §5 rationale     | open   | Slice 9 Part 1 진입점                                      |
| #45 §6 KPI 11→12     | open   | Slice 9 Part 1 (Part 1 마지막 단계로 통합)                 |
| #46 §7 manual eval   | open   | Slice 9 Part 2 진입점                                      |
| #47 S13 trigger_case | defer  | Slice 10 보류 (service layer 격리)                         |

---

## §3. 회귀 분류 (E1 자동 분류)

- Step 0 변경 경로:
  - `portfolio/llm/cost_guard.py` (cost 경로)
  - `portfolio/tests/helpers/regression_classifier.py` + `__init__.py` (no-cost)
  - `portfolio/tests/slice9/test_cost_guard_cap.py` + `test_regression_classifier.py` + `__init__.py` (no-cost)
  - `docs/portfolio/coach/COST_POLICY.md` (no-cost)
  - `docs/portfolio/coach/kpi_matrix.md` (no-cost)
  - `docs/portfolio/coach/slice9/kpi_e1_regression_classification.md` + `step_0.md` + `step0_closing.md` (no-cost)
  - `scripts/slice9/verify_step0_kpi.py` + `__init__.py` (out-of-scope)
  - `.env.example` (out-of-scope)

- **자동 분류 결과**: `mixed` (`portfolio/llm/cost_guard.py` 포함 → 보수적 cost로 처리)
- **적용 KPI**: 9a (cost 회귀 ±30%) — deviation 0.0% PASS
- **9b 참고**: no-cost 단독으로 봐도 deviation 0.0% PASS

---

## §4. 산출물 체크리스트 (10건)

| #   | 산출물                 | 위치                                                                            | 상태  |
| --- | ---------------------- | ------------------------------------------------------------------------------- | :---: |
| 1   | COST_POLICY.md 갱신    | docs/portfolio/coach/COST_POLICY.md                                             |  ✓    |
| 2   | CostGuard 코드 갱신    | portfolio/llm/cost_guard.py                                                     |  ✓    |
| 3   | CostGuard 단위 테스트  | portfolio/tests/slice9/test_cost_guard_cap.py (11건 PASS)                       |  ✓    |
| 4   | E1 분류 룰 docs        | docs/portfolio/coach/slice9/kpi_e1_regression_classification.md                 |  ✓    |
| 5   | 회귀 분류 helper       | portfolio/tests/helpers/regression_classifier.py                                |  ✓    |
| 6   | 회귀 분류 단위 테스트  | portfolio/tests/slice9/test_regression_classifier.py (7건 PASS)                 |  ✓    |
| 7   | KPI 매트릭스 docs      | docs/portfolio/coach/kpi_matrix.md (12 KPI)                                     |  ✓    |
| 8   | .env / .env.example    | COST_THRESHOLD/CAP/PER_CALL 변수 6개 추가                                       |  ✓    |
| 9   | KPI 자동 검증 스크립트 | scripts/slice9/verify_step0_kpi.py (ALL PASS)                                   |  ✓    |
| 10  | 종결 보고서            | docs/portfolio/coach/slice9/step0_closing.md (본 문서)                          |  ✓    |

---

## §5. 회귀 누적 (Slice 8 → Slice 9 Step 0)

| 시점                | 회귀  | IDENTICAL | 누적 cost | 누적 LLM 호출 |
| ------------------- | ----- | --------- | --------- | ------------- |
| Slice 8 Part 3 종결 | 458   | 7/7       | $2.0483   | 27/100        |
| **Slice 9 Step 0**  | **476** | **7/7** | **$2.0483 (불변)** | **27/100 (불변)** |
| Slice 9 Part 1 예상 | +2~3  | 7/7       | $2.78 (rationale $0.73) | 27 + 28 = 55  |
| Slice 9 Part 2 예상 | +3~5  | 7/7       | $2.78 (불변)            | 55 (불변)     |

---

## §6. 신규 인프라 (Slice 9 Step 0 누적)

- `portfolio/llm/cost_guard.py` (확장):
  - 신규 필드: `threshold`, `warning`, `cap_per_slice`, `cap_warning`, `per_call_haiku`, `per_call_sonnet`, `cumulative_usd`, `slice_usd`
  - 신규 메서드: `record_cost(cost_usd)`, `check_warnings()`
  - 신규 예외: `CostCapExceeded`, `CostThresholdExceeded`
  - `reset_slice`/`reset_for_slice` 갱신 → `slice_usd=0`도 함께 reset
- `portfolio/tests/helpers/regression_classifier.py` (신규) — git diff 기반 cost/no-cost/mixed 자동 분류
- `docs/portfolio/coach/COST_POLICY.md` (전면 재편) — §1 임계값 (누적/cap/단건) + §2 갱신 이력 + §3 갱신 트리거 + Appendix A~D
- `docs/portfolio/coach/kpi_matrix.md` (신규) — core 8 + auxiliary 4 = 12 KPI 정착
- `docs/portfolio/coach/slice9/kpi_e1_regression_classification.md` (신규) — KPI 9a/9b 분리 룰
- `scripts/slice9/verify_step0_kpi.py` (신규) — KPI 6개 자동 검증

---

## §7. lock 블록 위반 점검

| 결정                         | 값                                              | 본 작업 적용 결과               |
| ---------------------------- | ----------------------------------------------- | ------------------------------- |
| **A3** 슬라이스 cap          | $1.00                                           | COST_POLICY §1.2 + CostGuard ✓  |
| **#43** 누적 임계            | $2.00 → $3.00                                   | COST_POLICY §1.1 ✓              |
| **B2** Part 구조             | Step0 / Part1=#44+#45 / Part2=#46              | 다음 단계 (Part 1 진입 대기) ✓  |
| **E1** 회귀 KPI 분리         | no-cost ±50% / cost ±30%                        | kpi_e1.md + classifier ✓        |
| **F2** 모델 정책             | haiku primary + sonnet fallback 유지            | 변경 없음 ✓                      |
| 단건 임계                    | haiku $0.03 / sonnet $0.10                      | CostGuard env default 유지 ✓     |
| LLM budget                   | PER_INSTANCE 50 / PER_SLICE 100                 | 기존 ClassVar 유지 ✓             |
| KPI 매트릭스                 | 12개 (core 8 + auxiliary 4)                     | kpi_matrix.md ✓                  |

**위반**: 없음.

---

## §8. 다음 단계 (Slice 9 Part 1)

- **진입점**: #44 §5 Sonnet rationale 28건 (Slice 8 Part 3 matrix_summary.json 입력)
- **예상 비용**: $0.73 (Sonnet 28콜)
  - 슬라이스 cap $1.00 마진: ($1.00 - $0.73) / $1.00 = **27%**
  - 누적 임계 $3.00 마진: ($3.00 - $2.78) / $3.00 = **7.3%**
- **예상 회귀**: +2~3 (KPI 자동 검증 스크립트 보강)
- **#45 통합**: Part 1 후반에 KPI 11 → 12 자동 검증 스크립트 추가 (slice9 디렉토리에 verify_part1_kpi.py 신규)
- **이연 부채 호출**: rationale 결과의 patterns_score 분석을 통해 #44에서 part3 matrix 결과 28건의 자체 평가 자동 생성

---

## §9. 환경/자동화 모니터링

- 야간 자동화 충돌: **0건** (Part 2 정착 이후 누적 0건 유지)
- pre-commit hook 차단: **0건** (브랜치 화이트리스트에 slice9 신규 진입 필요 시 별도 작업)
- 외래 commit 진입: **0건**

---

## §10. 종결 선언

Slice 9 Step 0 #43은 정상 종결. Slice 9 Part 1 진입 준비 완료.

- LLM 호출 0건 ($0 비용)
- 회귀 458 → 476 (+18, KPI 9b/9a 모두 PASS)
- IDENTICAL hash 7/7 유지
- 산출물 10건 모두 정착
- lock 블록 변경 없음

**다음 세션 진입 시**: `pytest portfolio/tests -q` 회귀 476 확인 → Part 1 진입 (#44 rationale 비용 사용자 승인 필요).
