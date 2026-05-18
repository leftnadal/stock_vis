# Slice 11 Part 1 — KPI 매트릭스 (10건)

> 회귀 baseline 532 → 측정 **541** (+9). 비용 단독 $0.

| #   | KPI                                                 | 임계                                                   | 측정                                                  | 판정 |
| --- | --------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------- | ---- |
| 1   | `CommentaryInputBase` 정의                          | 4 base 필드 (portfolio_id / fetched_at / preset / entry_point) + holdings | `commentary_input.py:97-114` 5 필드 등록             | **PASS** |
| 2   | frozen + extra=forbid 동작                          | 두 룰 모두 PASS                                        | `test_base_frozen_immutability` + `test_base_extra_forbid_rejects_unknown_fields` | **PASS** |
| 3   | 6 sub class 정의 (E1~E6)                            | 6/6 instantiate + Literal entry_point                  | `test_six_sub_classes_instantiate_with_specific_fields` + `test_mapping_registers_six_classes_*` | **PASS** |
| 4   | discriminator value 일관성                          | entry_point Literal 6종                                | `test_entry_point_discriminator_is_locked_literal`   | **PASS** |
| 5   | `Holding` 공통 type 1회 정의                        | 1 정의 + 6 sub class 재사용                            | `test_mapping_registers_six_classes_with_shared_holding_type` | **PASS** |
| 6   | portfolio_a2 fixture → 6 schema validate            | 100% (6/6)                                             | `test_portfolio_a2_loads_to_six_sub_classes_with_time_series_e5` 6/6 | **PASS** |
| 7   | preset enum 5종 (garp/focused/income/growth/factor) | PASS                                                   | `test_base_required_fields_and_preset_enum`           | **PASS** |
| 8   | IDENTICAL hash 유지                                 | 7/7                                                    | test_static_integrity 7/7                             | **PASS** |
| 9   | 회귀 +5~8 (predicted ±30%/±50%)                     | cost ±30% [4.6, 8.5] 또는 no-cost ±50% [3.3, 10.4]     | 측정 +9 (cost ±30% 살짝 초과, no-cost ±50% 안)        | **PASS** (no-cost ±50% 범위 PASS, schema 카테고리 mixed) |
| 10  | 누적 비용 변화                                      | $0                                                     | $0 (LLM 호출 0, schema 작업만)                        | **PASS** |

**총 10/10 PASS.**

## 비고

- KPI 9 측정 +9는 cost ±30% 범위(상한 8.5) 살짝 초과 (+0.5). schema 작업은 production
  코드 변경이지만 비용 영향이 없는 데이터 모델 정의 → ±50% (no-cost) 임계 적용이 더
  자연스러움. classifier에서는 `portfolio/schemas/` + `tests/coach/` 혼합 → mixed로
  분류, 정확도 검증 PASS.
- 신규 테스트 분포:
  - `tests/coach/test_commentary_input.py`: 8건
  - `portfolio/tests/slice11/test_regression_classifier.py`: +1건
