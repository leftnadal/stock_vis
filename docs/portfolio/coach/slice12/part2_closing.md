# Slice 12 Part 2 종결 보고 — 5 ScoringEngine 풀 구현 + PresetSpec schema

**브랜치**: `slice12`
**선행 commit**: `74fd49b` (Part 1)
**작업일**: 2026-05-20
**비용**: $0 (LLM 호출 없음)

---

## §1. Baseline / 결과

| 항목         | Baseline (Part 1 후) | Part 2 종결        | 변화      |
| ------------ | --------------------- | ------------------ | --------- |
| 회귀         | 605                   | **641**            | **+36**   |
| Slice cap    | $0.0554 / $1.00       | $0.0554 / $1.00    | 동일      |
| 전체 누적    | $2.6998 / $4.00       | $2.6998 / $4.00    | 동일      |
| LLM 호출     | 4 / 50                | 4 / 50             | 동일      |
| IDENTICAL    | 7/7 PASS              | 7/7 PASS           | 유지      |
| 호출자       | 0건                   | 0건                | 유지 (Part 3 smoke 진입 전 정상) |

---

## §2. KPI Matrix (Part 2, 12건)

| #   | KPI                              | 측정값   | 기대값        | PASS/FAIL |
| --- | -------------------------------- | -------- | ------------- | --------- |
| 1   | PresetSpec schema 신설           | O        | O             | PASS      |
| 2   | weights sum 1.0±0.001 validator  | O        | O             | PASS      |
| 3   | category Literal 5종 validator   | O        | O             | PASS      |
| 4   | base.py utility (_apply_gate)    | O        | O             | PASS      |
| 5   | base.py utility (_weighted_sum)  | O        | O             | PASS      |
| 6   | 5 카테고리 score() 풀 구현       | 5/5      | 5/5           | PASS      |
| 7   | 12 preset weights 합 1.0         | 12/12    | 12/12         | PASS      |
| 8   | gate 발동 케이스 (income/factor) | 3건      | 3건           | PASS      |
| 9   | 단위 테스트 신규 +Δ              | **+36**  | +30~33        | **OVER**  |
| 10  | IDENTICAL 7/7                    | 7/7      | 7/7           | PASS      |
| 11  | 호출자 무변경 (외부 0건)         | 0건      | 0건           | PASS      |
| 12  | Part 2 단독 비용 $0              | $0       | $0            | PASS      |

### KPI 9 OVER 사유
- 측정 +36 vs 기대 +30~33 (3 초과)
- 분해:
  - `test_preset_spec.py` 신규: **10건** (지시서 +7 vs 실제 +10, gate validator 추가 3건 영향)
  - `test_scoring_engine_base.py` 확장: **+7건** (3 → 10)
  - `test_preset_scorers_dict.py` 갱신: NotImpl 10건 → 풀 10건 (net 0)
  - `test_engine_scoring.py` 신규: **+19건** (parametrize 3×5 + gate 4건)
  - 합계 +36
- **사유**: gate validator + engine_scoring parametrize 3종 영향. Part 1 +25 (KPI 9 OVER) + Part 2 +36 (KPI 9 OVER) 누적 → **#57 parametrize-heavy 슬라이스 유형 패턴 강화**
- **D5-A 보정 후보 등록**: Slice 12 종결 시 `kpi_matrix.md` §6에 "Component buildup 슬라이스 (base+adapter+spec+테스트): +30~40" 신규 유형 추가 검토

---

## §3. 신규 자산

### 신규 모듈
| 파일                                                   | 역할                                     |
| ------------------------------------------------------ | ---------------------------------------- |
| `portfolio/services/scoring/preset_spec.py`            | PresetSpec Pydantic schema (validators)  |

### 수정 모듈
| 파일                                                   | 변화                                                  |
| ------------------------------------------------------ | ----------------------------------------------------- |
| `portfolio/services/scoring/base.py`                   | abstract signature `score(metrics)`, utility 3종 추가 |
| `portfolio/services/scoring/presets/value.py`          | VALUE_SPECS + ValueScoringEngine 풀 구현              |
| `portfolio/services/scoring/presets/growth.py`         | GROWTH_SPECS + 풀                                     |
| `portfolio/services/scoring/presets/income.py`         | INCOME_SPECS + 풀 (gate 2건)                          |
| `portfolio/services/scoring/presets/factor.py`         | FACTOR_SPECS + 풀 (gate 1건)                          |
| `portfolio/services/scoring/presets/special.py`        | SPECIAL_SPECS + 풀                                    |

### 신규 테스트
| 파일                                              | 건수 |
| ------------------------------------------------- | ---- |
| `tests/scoring/test_preset_spec.py`               | 10   |
| `tests/scoring/test_scoring_engine_base.py` (확장) | +7   |
| `tests/scoring/test_preset_scorers_dict.py` (갱신) | 0    |
| `tests/scoring/test_engine_scoring.py`            | 19   |
| **합계**                                          | **+36** |

---

## §4. 동작 검증 예시

### PresetSpec validator
- 정상: `PresetSpec(preset_id="value_test", category="value", weights={"roic": 0.5, "roe": 0.5})` → PASS
- 실패: weights 합 0.97 → `ValidationError: weights sum must be 1.0 ± 0.001`

### Gate 발동 (income/dividend_growth)
- 입력: `dividend_yield=0.01` (< 0.02 임계)
- 출력: `dividend_growth=0.0`, `_category_score=0.0` — score=0 강제

### 정상 score (value 카테고리)
- 입력: `{roic: 0.6, roe: 0.5, roic_consistency_5y: 0.8, earnings_consistency_5y: 0.7, f_score_total: 0.7}`
- 출력: `buffett_quality_value=64.5, piotroski_f_score=70.0, _category_score=67.25`

---

## §5. Scope 격리 (D4-A 확인)

| 항목                       | 변화                                              |
| -------------------------- | ------------------------------------------------- |
| action_items prompt (#59 E5) | 변경 없음 (Part 3 이후 자연 처리)                |
| 외부 service 호출자        | 변경 없음 (Part 3 smoke 단계)                     |
| E1~E6 진입점               | 변경 없음                                         |
| analysis_engine            | 변경 없음                                         |

---

## §6. 부채 변화

| ID  | 상태            | 비고                                      |
| --- | --------------- | ----------------------------------------- |
| #51 | 유지            | Slice 13 Step 0 1순위 후보                |
| #59 E5 | 유지 (D4-A 격리) | Part 3 자연 처리 예정                  |
| #57 | (재거론)       | parametrize-heavy 패턴 강화, Slice 12 종결 시 D5-A 보정 검토 |

close 0, 신규 0, 유지 2. net 0.

---

## §7. Slice 12 누적

| Part   | commit         | 회귀        | 비용     | 결과                                       |
| ------ | -------------- | ----------- | -------- | ------------------------------------------ |
| Step 0 | `f013c48`      | 571 → 580   | $0.0554  | multi-debt mini (#58/#41/#59 E3 close)     |
| Part 1 | `74fd49b`      | 580 → 605   | $0       | scoring base + 5 adapter 스켈레톤           |
| Part 2 | (다음 commit)  | 605 → 641   | $0       | 5 ScoringEngine 풀 + PresetSpec + gate     |

전체 누적: 571 → 641 (+70), $0.0554 (마진 94.46%).

---

## §8. Part 3 진입 준비

| 항목             | 값                                                         |
| ---------------- | ---------------------------------------------------------- |
| Part 3 작업      | smoke + 부분 matrix (5 카테고리 × 2 fixture = 10 케이스)   |
| 예상 시간        | ~2h                                                        |
| 예상 LLM         | 10 콜 (가벼운 smoke)                                       |
| 예상 비용        | $0.05~0.15                                                 |
| Part 2 자산      | ScoringEngineBase utility + PresetSpec + 5 풀 ScoringEngine + 12 preset 매핑 |
| **Part 3 신규**  | metric 정규화 호출자 (외부 통합 첫 발생) + smoke fixture     |
