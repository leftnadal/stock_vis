# Slice 11 Part 2 종결 보고 — 6 진입점 통합 Output Schema (#41 close)

> Part 1 input schema와 1:1 대응되는 통합 output schema 완성. **#41 자연 close**.

## 요약

| 항목                | 값                                            |
| ------------------- | --------------------------------------------- |
| 회귀                | 541 → **550** (+9, ±30% 범위 PASS)            |
| IDENTICAL hash      | 7/7                                           |
| 단독 비용           | $0.00 (LLM 호출 없음 — schema 작업만)         |
| 누적 비용           | $2.3775 (Slice 1~10 보존)                     |
| LLM 호출            | 0 / 50                                        |
| KPI 10/10           | 10 PASS, 0 FAIL                               |
| 호출자 인벤토리     | **4건** (모두 ActionItem 단일 import) → in-place 진행 |
| 호출자 갱신         | **0건** (ActionItem 보존으로 자동 호환)       |
| #41 부채            | **close** (자연 종결)                         |
| Fallback 발동       | 없음                                          |

## §1 baseline 확인

- 브랜치: `slice11`
- Part 1 commit: `ca272b0`
- baseline 회귀: 541 (Part 1 종결 후)
- 기존 `commentary_output.py`: 존재 (47 라인, ActionItem만)

## §2 호출자 인벤토리 (Step 1)

| # | 파일                                                              | import 형태 |
| - | ----------------------------------------------------------------- | ----------- |
| 1 | `portfolio/schemas/llm.py:17`                                     | `ActionItem` |
| 2 | `portfolio/schemas/e4_conversation.py:17`                         | `ActionItem` |
| 3 | `portfolio/tests/test_action_item_schema.py:6`                    | `ActionItem` |
| 4 | `portfolio/tests/test_schema_action_items_backward_compat.py:5`   | `ActionItem` |

**Fallback B2 미발동** (4 ≤ 5).

자세히: `docs/portfolio/coach/slice11/part2_caller_inventory.md`.

## §3 schema 매핑 (Step 2)

- **Base 필드** (3종): `summary`, `key_observations`, `confidence` (Literal["high","medium","low"])
- **E1 sub class**: `action_items`, `risk_flags`, `metrics_table` (#21 deprecated 유지)
- **E2 sub class**: `quoted_metrics`, `metrics_table` (#21 deprecated 유지)
- **E3 sub class**: `action_items`, `risk_flags`
- **E4 sub class**: base만 (대화 Q&A는 추가 필드 불필요)
- **E5 sub class**: `action_items`, `quoted_metrics`
- **E6 sub class**: `risk_flags`, `quoted_metrics`
- **ActionItem**: 기존 정의 **변경 0** (title/description/priority/category 동일)

자세히: `docs/portfolio/coach/slice11/part2_schema_mapping.md`.

## §4 호출자 갱신 (Step 4)

- 갱신 호출자: **0건**
- legacy import 잔존: **0**
- 이유: `ActionItem`을 신규 `commentary_output.py`에 그대로 보존 →
  `from portfolio.schemas.commentary_output import ActionItem`이 그대로 동작.
- 검증: `portfolio/tests/test_action_item_schema.py` + `test_schema_action_items_backward_compat.py` 23/23 PASS.

## §5 회귀 (Step 6)

- 541 → **550** (+9)
- KPI 6 PASS (±30% [3.5, 9.1])
- IDENTICAL 7/7 PASS
- 분배: `test_commentary_output.py` 8건 + `test_regression_classifier.py` +1건

## §6 신규 테스트

- **8/8 PASS** (`tests/coach/test_commentary_output.py`):
  1. `test_base_required_fields_and_confidence_enum`
  2. `test_base_frozen_immutability`
  3. `test_base_extra_forbid_rejects_unknown_fields`
  4. `test_six_sub_classes_instantiate_with_specific_fields`
  5. `test_sub_classes_have_base_fields_inherited`
  6. `test_mapping_registers_six_classes` (input/output 키 일관 검증 포함)
  7. `test_sub_class_specific_fields_present`
  8. `test_action_item_definition_unchanged`

## §7 비용

- 단독: **$0** (LLM 호출 없음, schema 리팩토링만)
- 누적: **$2.3775** 유지 (Slice 10 보존, 마진 41%)

## §8 KPI matrix

10/10 PASS — `docs/portfolio/coach/slice11/kpi_part2.md` 참조.

## §9 #41 처리

| close 조건                                              | 충족 |
| ------------------------------------------------------- | ---- |
| KPI 1~10 모두 PASS                                      | ✓    |
| `CommentaryOutputBase` 정의 존재                        | ✓    |
| `COMMENTARY_OUTPUT_CLASSES` dict 6 entry                | ✓    |
| 호출자 갱신 완료 (legacy import 0)                      | ✓    |

**최종 판정**: **#41 close** (자연 종결).

**재오픈 트리거** (Part 3 prompt builder 작성 시점):
- service input과 본 schema 1:1 fitting 실패 시 (Pydantic ValidationError)
- 신규 필드가 prompt builder 단계에서 발견되어 schema 보강 필요 시
- 재오픈 시 Slice 12 Step 0 후보로 자동 등록

## §10 산출물 dump

| 영역    | 파일                                                            | 신규/수정       |
| ------- | --------------------------------------------------------------- | --------------- |
| schema  | `portfolio/schemas/commentary_output.py`                        | **수정** (Base + 6 sub + ActionItem 보존 + dict) |
| 테스트  | `tests/coach/test_commentary_output.py`                         | **신규** (8건)  |
| 분류    | `portfolio/tests/slice11/test_regression_classifier.py`         | 수정 (+1건)     |
| 문서    | `docs/portfolio/coach/slice11/part2_caller_inventory.md`        | **신규**        |
| 문서    | `docs/portfolio/coach/slice11/part2_schema_mapping.md`          | **신규**        |
| 문서    | `docs/portfolio/coach/slice11/kpi_part2.md`                     | **신규**        |
| 문서    | `docs/portfolio/coach/slice11/part2_closing.md` (본 문서)       | **신규**        |

## §11 커밋

- 예정 commit message: `[slice11] Part 2 종결: 통합 output schema (Base + 6 sub + ActionItem 보존, #41 close)`

## §12 Part 3 진입 준비

| 자산                                              | 상태               |
| ------------------------------------------------- | ------------------ |
| input schema (Part 1)                             | **READY**          |
| output schema (Part 2)                            | **PRODUCTION READY** |
| `COMMENTARY_INPUT_CLASSES` ↔ `COMMENTARY_OUTPUT_CLASSES` 키 1:1 | **READY** |
| portfolio_a2 fixture                              | READY              |
| #41 부채                                          | **CLOSE**          |
| 회귀 baseline                                     | **550**            |

**Part 3 scope** (예정): prompt builder — Part 1 input + Part 2 output schema 1:1 fitting.

## 회신 매트릭스

```
Slice 11 Part 2 종결 (통합 output schema, #41 close).
- 회귀: 541 → 550 (+9)
- IDENTICAL: 7/7
- 비용 단독: $0 / 누적: $2.3775 (마진 41%)
- LLM 호출: 0/50
- KPI 10/10: 10 PASS, 0 FAIL
- schema 모듈: CommentaryOutputBase + 6 sub class (E1~E6) + ActionItem 보존
- 호출자 인벤토리: 4건 (in-place) / 갱신 0건
- #41: close (자연 종결)
- Fallback 발동: 없음

Slice 11 Part 3 진입 준비 상태: 완료
다음 작업: prompt builder (input + output schema 1:1 fitting)
```

## Manual 검증 필요 항목

- 없음. 10/10 PASS, IDENTICAL 7/7 유지, 호출자 갱신 0건.
- Part 3 prompt builder 작성 중 schema fitting 실패 시 #41 재오픈 (조건 명시).
