# Slice 11 Part 3 — KPI 매트릭스 (12건)

> 회귀 baseline 550 → 측정 **559** (+9, ±30% [4.2, 13] 안). 비용 단독 **$0.0290** (cap 마진 97.1%).

| #   | KPI                          | 측정값                                                                | 기대값                         | PASS/FAIL |
| --- | ---------------------------- | --------------------------------------------------------------------- | ------------------------------ | --------- |
| 1   | E1 service 파일 식별         | `portfolio/services/e1_garp.py` 74 라인 + prompt `e1_builder.py` 48 라인 | 1건 + prompt 추출        | **PASS**  |
| 2   | prompt_builder 모듈 import   | `PROMPT_BUILDER_CLASSES` 6 entry + `E1PromptBuilder.entry_point == "e1"` | 6 entry, e1 일관           | **PASS**  |
| 3   | E1 service 호출자 영향       | **0건** (신규 coach service 추가, 기존 e1_garp 무변경)                | 영향 0                         | **PASS**  |
| 4   | builder 단위 테스트          | **8/8 PASS** (`test_prompt_builder.py`)                               | 8/8 PASS                       | **PASS**  |
| 5   | schema fitting               | haiku + sonnet 양 모델 **E1Output validate PASS**                    | validate PASS                  | **PASS**  |
| 6   | smoke 비용                   | **$0.0290** (haiku $0.00684 + sonnet $0.02213)                       | ≤ $0.05                        | **PASS**  |
| 7   | 회귀 +Δ                      | 550 → 559 (+9)                                                       | +6~10 (±30% [4.2, 13])         | **PASS**  |
| 8   | IDENTICAL hash 유지          | 7/7                                                                  | 7/7 유지                       | **PASS**  |
| 9   | E1 service 회귀              | 기존 `run_e1_garp` 무변경 → 기존 테스트 모두 PASS                    | 마이그레이션 후 PASS           | **PASS**  |
| 10  | classifier deviation         | slice11 룰 +1건 (`prompt_builder_and_coach_service_are_mixed`)        | cost ±30%, no-cost ±50%        | **PASS**  |
| 11  | #48 v3 max_delta             | **0.0%** (haiku 0.0% + sonnet 0.0%, N=2)                             | ≤ 10% (N=2) / weak signal (N=1)| **PASS** (강 신호) |
| 12  | 슬라이스 cap 마진            | $0.0290 사용 → **마진 97.1%** ($1.00 - $0.0290 = $0.9710 잔여)        | ≥ 80% ($0.80 미만 사용)        | **PASS**  |

**총 12/12 PASS.**

## #48 v3 측정 상세

| #   | 모델                | predicted | counted | actual | output | delta_pred | delta_count | latency_ms | cost     |
| --- | ------------------- | --------- | ------- | ------ | ------ | ---------- | ----------- | ---------- | -------- |
| 1   | claude-haiku-4-5    | 1807      | 1807    | 1807   | 1349   | 0.0%       | 0.0%        | 14374      | $0.00684 |
| 2   | claude-sonnet-4-5   | 1807      | 1807    | 1807   | 1114   | 0.0%       | 0.0%        | 23066      | $0.02213 |

**v3 정책 정착 확정** — count_tokens API 정의상 ±2% 보장이 실측 N=2에서 **0% delta** 로 확인.

## 회귀 분배

- `tests/coach/test_prompt_builder.py`: 8건
- `portfolio/tests/slice11/test_regression_classifier.py`: +1건
- **합계 +9**

## 부채 처리

| 부채 | 처리                                              |
| ---- | ------------------------------------------------- |
| #48  | **v3 정책 정착 확정** (N=2, max_delta 0.0%) — Slice 12+ 자연 활용 |
| #41  | **close 유지** (Part 2 결정 그대로, E1Output validate PASS) |

## 비용 누적

| 항목       | 값       |
| ---------- | -------- |
| 단독 (Part 3) | $0.0290 |
| 누적 (Slice 1~10 + Part 3) | $2.4065 (2.3775 + 0.0290) |
| 신 임계 $4.00 마진 | **39.8%** |
