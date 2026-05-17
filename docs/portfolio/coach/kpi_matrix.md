# KPI Matrix

> **버전**: v2 (Slice 9 #43 / E1 보정)
> **총 KPI 수**: 12개 (core 8 + auxiliary 4)
> **마지막 갱신**: 2026-05-17

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

| 시점        | 변경                                                                                |
| ----------- | ----------------------------------------------------------------------------------- |
| Slice 1     | KPI 7개 (회귀 + IDENTICAL + 단건 cost + 누적 cost + LLM 호출 + 4판정 + winner)      |
| Slice 8     | KPI 11개 (+ trio 진단 + 분포 폭 + #β2 estimator)                                    |
| **Slice 9** | **KPI 12개 (+ 슬라이스 cap, 회귀 9a/9b 분리)**                                      |

---

## §5. KPI 기준선 (Slice 8 종결 → Slice 9 진입)

| #   | KPI                | Slice 8 종결값 | Slice 9 임계 비고 |
| --- | ------------------ | -------------- | ----------------- |
| 1   | 회귀 통과          | 458 passed     | Slice 9 +20~25 예상 |
| 2   | IDENTICAL hash     | 7/7 PASS       | 유지 필수        |
| 3   | 단건 cost          | matrix 전건 PASS | 유지            |
| 4   | 누적 cost          | $2.0483        | 임계 $3.00       |
| 5   | 슬라이스 cap       | (신규)         | $1.00            |
| 6   | LLM 호출           | 27/100         | 100 유지         |
| 7   | 4판정 PASS         | 100% (26/26)   | ≥90% 유지        |
| 8   | winner             | Haiku +335%    | rationale 후 재확정 |
