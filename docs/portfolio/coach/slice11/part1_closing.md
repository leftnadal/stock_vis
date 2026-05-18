# Slice 11 Part 1 종결 보고 — 6 진입점 통합 input schema

> trio 5-Part 첫 진입점 작업 Part 종결. A2 통합 시연용 input schema 완성.

## 요약

| 항목                | 값                                            |
| ------------------- | --------------------------------------------- |
| 회귀                | 532 → 541 (+9, ±50% no-cost 범위 PASS)        |
| IDENTICAL hash      | 7/7                                           |
| 단독 비용           | $0.00 (LLM 호출 없음 — schema 작업만)         |
| 누적 비용           | $2.3775 (Slice 1~10 보존)                     |
| LLM 호출            | 0 / 50                                        |
| KPI 10/10           | 10 PASS, 0 FAIL                               |
| schema 모듈         | `CommentaryInputBase` + 6 sub class (E1~E6) + `Holding` 공통 type |
| portfolio_a2 fixture | 6 진입점 validate **6/6 PASS**                |
| Fallback 발동       | 없음                                          |

## 산출물

### 신규 (3건)
- [x] `tests/coach/test_commentary_input.py` (8건)
- [x] `portfolio/tests/fixtures/coach/loaders.py` (`load_portfolio_a2_input`, `load_portfolio_a2_all_inputs`)
- [x] `portfolio/tests/fixtures/coach/__init__.py`
- [x] `docs/portfolio/coach/slice11/kpi_part1.md`
- [x] `docs/portfolio/coach/slice11/part1_closing.md`

### 갱신 (4건)
- [x] `portfolio/schemas/commentary_input.py` (base + 6 sub class + Holding + preset enum + COMMENTARY_INPUT_CLASSES)
- [x] `portfolio/tests/fixtures/coach/portfolio_a2.json` (`portfolio_id` / `fetched_at` / `preset` / `inputs.{e1~e6}` 추가)
- [x] `portfolio/tests/slice11/test_regression_classifier.py` (+1 schema 룰)

## §1 CommentaryInputBase 설계

`portfolio/schemas/commentary_input.py:97-114`:

| 필드            | 타입                              | 설명                                     |
| --------------- | --------------------------------- | ---------------------------------------- |
| portfolio_id    | str (min_length=1)                | 포트폴리오 식별자                        |
| fetched_at      | datetime                          | 데이터 수집 snapshot 시점                |
| preset          | Literal["garp", "focused", "income", "growth", "factor"] | 투자 스타일 (Slice 11 `income` 추가) |
| entry_point     | str (Literal in sub class)        | discriminator                            |
| holdings        | list[Holding] (min_length=1)      | 포트폴리오 보유 종목                     |

설정: `frozen=True, extra="forbid"` → schema drift 즉시 검출.

## §2 6 sub class (E1~E6)

`commentary_input.py:117-177`. 모두 `CommentaryInputBase` 상속 + 진입점별 특화 필드:

| Sub class             | entry_point (Literal) | 특화 필드                                                   |
| --------------------- | --------------------- | ----------------------------------------------------------- |
| CommentaryInputE1     | "e1"                  | `garp_metrics: dict[str, dict[str, Any]]`                   |
| CommentaryInputE2     | "e2"                  | `portfolio_return_1y`, `sector_allocation`                  |
| CommentaryInputE3     | "e3"                  | `concentration_metrics`                                     |
| CommentaryInputE4     | "e4"                  | `user_question`, `conversation_history`                     |
| CommentaryInputE5     | "e5"                  | `extraction_targets`, `time_series_context: TimeSeriesContext` |
| CommentaryInputE6     | "e6"                  | `analysis_results: dict[str, dict[str, Any]]`               |

**`Holding`** (공통 type, 1회 정의): `ticker / weight (0.0~1.0) / sector? / asset_class? / name?` —
6 sub class 모두 동일 `list[Holding]` 사용. `model_config = ConfigDict(extra="forbid", frozen=True)`.

**`COMMENTARY_INPUT_CLASSES`** dict: `{"e1": E1, ..., "e6": E6}` (loader / discriminator 활용).

## §3 portfolio_a2 fixture 매핑

`portfolio/tests/fixtures/coach/portfolio_a2.json`:
- top-level: `portfolio_id` / `fetched_at` / `preset` / `holdings` (5종) 추가 보존.
- `inputs.{e1, e2, e3, e4, e5, e6}` 신규 dict: 각 진입점별 특화 input 값.
- 기존 키 (`fixture_id`, `preset_id`, `portfolio_metrics`, `analysis_summary` 등) 보존
  → Step 0 fixture 테스트 4건 무영향 (4 PASS).

`loaders.py`:
- `load_portfolio_a2_raw(path)` → 원본 dict.
- `load_portfolio_a2_input(entry_point, path)` → 단일 sub class instance.
- `load_portfolio_a2_all_inputs(path)` → `{e1~e6: instance}` dict.

검증 결과: **6/6 fixture validate PASS**. E5에는 TimeSeriesContext 동반.

## §4 회귀 분류

`schema 카테고리`는 신규 추가 없이 기존 cost (`portfolio/schemas/`) 룰 재사용.
`tests/coach/test_commentary_input.py`는 data-prep 카테고리. 혼합 시 mixed로
보수적 분류 검증 (`test_commentary_input_schema_changes_are_mixed` 신규 +1).

## §6 KPI 매트릭스

`docs/portfolio/coach/slice11/kpi_part1.md` 별도 문서. **10/10 PASS**.

## Slice 11 Part 2 진입 준비

| 자산                                           | 상태                |
| ---------------------------------------------- | ------------------- |
| input schema (base + 6 sub class)              | **PRODUCTION READY** |
| portfolio_a2 fixture (6 진입점 inputs)         | **PRODUCTION READY** |
| fixture loader                                 | **READY**           |
| 회귀 baseline                                  | **541**             |

**Part 2 scope (예정)**:
- 6 진입점 통합 output schema (`commentary_output.py` 갱신)
- input/output 1:1 대응 + `#41 자연 close` 검증
- prompt builder 본격 구현은 Part 3

## 회신 매트릭스

```
Slice 11 Part 1 종결 (6 진입점 통합 input schema).
- 회귀: 532 → 541 (+9)
- IDENTICAL: 7/7
- 비용 단독: $0 / 누적: $2.3775 (마진 41%)
- LLM 호출: 0/50
- KPI 10/10: 10 PASS, 0 FAIL
- schema 모듈: CommentaryInputBase + 6 sub class (E1~E6) + Holding
- portfolio_a2 fixture: 6 진입점 validate 6/6
- Fallback 발동: 없음

Slice 11 Part 2 진입 준비 상태: 완료
#41 자연 close 예상 (Part 2 output schema 통합 시점)
```

## Manual 검증 필요 항목

- 없음. 모든 KPI 자동 측정 10/10 PASS.
- Slice 11 Part 3 prompt builder 작성 시점에 기존 진입점 service (E1~E6) input과
  본 schema 1:1 fitting 필요 — Fallback §2 룰에 따라 prompt builder 작업 시 본격 정합.
