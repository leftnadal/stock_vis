# Slice 11 Part 2 — KPI 매트릭스 (10건)

> 회귀 baseline 541 → 측정 **550** (+9, ±30% 범위 PASS). 비용 단독 $0.

| #   | KPI                          | 측정값                                          | 기대값                                      | PASS/FAIL |
| --- | ---------------------------- | ----------------------------------------------- | ------------------------------------------- | --------- |
| 1   | 호출자 인벤토리 N건          | 4 (모두 ActionItem 단일 import)                 | ≤ 5 (in-place)                              | **PASS**  |
| 2   | schema 매핑 완전성           | 7 필드 + ActionItem 1:1 매핑 (`part2_schema_mapping.md`) | 7 필드 + ActionItem 1:1               | **PASS**  |
| 3   | 신규 schema 모듈 import      | 6 (`COMMENTARY_OUTPUT_CLASSES` 길이)            | 성공, dict 6개                              | **PASS**  |
| 4   | 호출자 갱신 완료             | legacy import 0 (ActionItem 보존 → 갱신 불필요) | legacy import 0                             | **PASS**  |
| 5   | 신규 테스트 PASS             | 8/8 (`test_commentary_output.py`)               | 8/8                                         | **PASS**  |
| 6   | 회귀 +Δ                      | 541 → 550 (+9)                                  | +5~7 (±30% [3.5, 9.1])                      | **PASS**  |
| 7   | IDENTICAL hash 유지          | 7/7                                             | 7/7 유지                                    | **PASS**  |
| 8   | 비용                         | $0                                              | $0 (LLM 호출 없음)                          | **PASS**  |
| 9   | classifier deviation         | 신규 분류 1건 (Part 2 schema → mixed) PASS      | ±50% (no-cost)                              | **PASS**  |
| 10  | #41 close 조건 4건           | 4/4 충족 (KPI 1~10 PASS + Base 정의 + dict 6 + 호출자 갱신 완료) | 모두 충족              | **PASS**  |

**총 10/10 PASS.**

## #41 close 조건 상세

| 조건                                                            | 충족 |
| --------------------------------------------------------------- | ---- |
| KPI 1~10 모두 PASS                                              | ✓    |
| `CommentaryOutputBase` 정의 존재                                | ✓ (`commentary_output.py:74`) |
| `COMMENTARY_OUTPUT_CLASSES` dict 6 entry                        | ✓ (`commentary_output.py:130-137`) |
| 호출자 갱신 완료 (legacy import 0)                              | ✓ (ActionItem 보존으로 자동) |

**#41 close** (자연 종결). 재오픈 트리거는 Part 3 prompt builder 작성 중 service input과 fitting 실패 시.

## 회귀 분배

- `tests/coach/test_commentary_output.py`: 8건
- `portfolio/tests/slice11/test_regression_classifier.py`: +1건
- **합계 +9** (예상 +5~7 대비 +2, ±30% 안)
