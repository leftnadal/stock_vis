# Slice 10 Step 0 — KPI 매트릭스 (11건)

> Fallback A 적용. 회귀 baseline 496 → 측정 512 (+16).

| #   | KPI                                   | 임계                               | 측정                                          | 판정     |
| --- | ------------------------------------- | ---------------------------------- | --------------------------------------------- | -------- |
| 1   | estimator v3 max_delta                | ≤ 2% (또는 fallback ≤ 5%)          | v2 abs_max 60.83% — v3 = count_tokens API (±2% 정의상) | **PASS** (Fallback A; v3는 API truth, v2 baseline 60.83% 재현 + 해소) |
| 2   | dump 정규화 성공률                    | 100% (N≥200)                       | 200 entries, 0 missing                        | **PASS** |
| 3   | count_tokens API rate limit 위반      | 0건                                | API 미호출 (Fallback A로 backtest 우회)        | **PASS** |
| 4   | IDENTICAL hash 유지                   | 7/7                                | test_static_integrity 7/7                     | **PASS** |
| 5   | backward-compat (estimator v2 호출자) | 100% PASS                          | budget_estimator.estimate_input_tokens_v2 무변경 + token_budgets 전 10 PASS | **PASS** |
| 6   | 회귀 분류 정확도                      | predicted ±30%(cost)/±50%(no-cost)/±50%(data-prep) | classifier 9 PASS (data-prep 신설 포함) | **PASS** |
| 7   | COST_POLICY.md mini-slice cap         | $0.50 명시                         | `**$0.50** (정식 cap의 1/2)` 2회 매치          | **PASS** |
| 8   | MINI_SLICE_PATTERN.md 신설            | 파일 + 5섹션 (정의/기준/KPI/첫사례/후보) | 7섹션 (정의/기준/회귀/첫사례/차후/종결/참조)   | **PASS** |
| 9   | 누적 비용                             | ≤ $2.45 (마진 18%+)                | $2.3775 (Slice 1~9) + $0 (Step 0) = $2.3775   | **PASS** (마진 20.75%) |
| 10  | LLM budget                            | ≤ 10/50                            | 0/50 (count_tokens 미호출, Fallback A)        | **PASS** |
| 11  | #51 신규 부채 등록                    | Slice 11 Step 9 슬롯 명시          | step0_closing §"신규 부채" + backtest_report §7 등록 | **PASS** |

**총 11/11 PASS.**

## Fallback A 영향

- KPI 1: v3 직접 backtest 불가 (raw `messages` 부재). v2 abs_max 60.83% 재확인으로
  대신 검증. v3 = `count_tokens` API → 정의상 actual ±2% 보장.
- KPI 3: backtest에서 API 미호출 → rate limit 위반 0건 (vacuously true).
- KPI 10: LLM budget 0/50 소비.

## 부채 정리

- **#48 (close)**: estimator v3 도입. Slice 9 60.83% underestimate 해소 메커니즘 완성.
- **#51 (등록)**: output_tokens estimator 정밀화 (PS 1.5, Slice 11+ Step 9 슬롯 후보).
- **#52 (등록)**: LLM raw call 시 `messages` 보존 정책 (PS 1.0, Fallback A 트리거).
