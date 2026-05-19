# Slice 12 Part 1 종결 — preset scoring base + 5 adapter 스켈레톤

**브랜치**: `slice12`
**작업일**: 2026-05-20
**선행 commit**: `f013c48` (Slice 12 Step 0)
**비용**: $0 (LLM 호출 없음)

---

## §1. 회귀 & 비용

| 항목                  | 값                                       |
| --------------------- | ---------------------------------------- |
| 회귀 (Step 0 → Part 1) | **580 → 605** (+25)                     |
| Part 1 단독 비용       | $0 (LLM 호출 0)                          |
| Slice 12 누적          | $0.0554 / $1.00 (마진 94.5% 유지)        |
| 전체 누적              | $2.6998 / $4.00 (마진 32.5% 유지)        |
| LLM 호출               | 4 / 50 (Slice 12 cap 마진 46)            |
| IDENTICAL              | 7/7 PASS                                 |

---

## §2. KPI Matrix (Part 1, 12건)

| #   | KPI                                     | 측정값      | 기대값             | PASS/FAIL    |
| --- | --------------------------------------- | ----------- | ------------------ | ------------ |
| 1   | Production scoring 인벤토리             | 5/5         | 5/5                | PASS         |
| 2   | ScoringEngineBase 정의                  | ABC+BaseModel | O              | PASS         |
| 3   | 5 adapter 스켈레톤 (NotImplementedError) | 5/5         | 5/5                | PASS         |
| 4   | PRESET_SCORERS dict 5 entry             | 5           | 5                  | PASS         |
| 5   | get_scorer 5 PASS + KeyError 1          | 5+1         | 5+1                | PASS         |
| 6   | 단위 테스트 (base 3 + dict 22)          | 25/25       | +15~20             | PASS         |
| 7   | 호출자 무변경 검증                      | 0건         | 0건 (Part 2 진입 전) | PASS       |
| 8   | 기존 회귀 580 baseline 유지             | 605 (+25)   | 580 + 신규         | PASS         |
| 9   | 신규 회귀 +Δ (표준 임계)                | **+25**     | +9~15 (±30% +6~20) | **OVER**     |
| 10  | IDENTICAL                               | 7/7         | 7/7                | PASS         |
| 11  | 비용 $0 (LLM 호출 0)                    | $0          | $0                 | PASS         |
| 12  | Pre-commit hook 정상 동작               | OK          | OK (slice12 등록)  | PASS         |

### KPI 9 OVER 사유 분석

- 측정 +25 vs 표준 슬라이스 임계 +6~20 (±30%) → **OVER 마진 외**
- 분해:
  - `test_scoring_engine_base.py`: 3건
  - `test_preset_scorers_dict.py`: 4 simple + parametrize 5×4 = **22건** (parametrize 폭발)
  - 합계 25건
- **사유**: parametrize 5 카테고리 × 4 종류 (inherits/instance/score raises/required raises) = 20건이 핵심. Slice 11 Part 1은 parametrize 미사용으로 +9였음.
- **#57 패턴 재발**: parametrize 회귀 영향이 표준 임계를 초과하는 패턴 — `kpi_matrix.md` §6에 **신규 슬라이스 유형 후보** (parametrize-heavy: +20~30) 등록 후보. Slice 12 종결 시 D5-A 추가 보정 검토.

---

## §3. 산출물 (10건)

| #   | 파일                                                    | 변경 유형       |
| --- | ------------------------------------------------------- | --------------- |
| 1   | `.git/hooks/pre-commit` (사전)                          | ALLOWED_BRANCHES + "slice12" |
| 2   | `docs/portfolio/coach/slice12/part1_inventory.md`       | 신규            |
| 3   | `portfolio/services/scoring/base.py`                    | 신규            |
| 4   | `portfolio/services/scoring/presets/__init__.py`        | 신규            |
| 5   | `portfolio/services/scoring/presets/value.py`           | 신규            |
| 6   | `portfolio/services/scoring/presets/growth.py`          | 신규            |
| 7   | `portfolio/services/scoring/presets/income.py`          | 신규            |
| 8   | `portfolio/services/scoring/presets/factor.py`          | 신규            |
| 9   | `portfolio/services/scoring/presets/special.py`         | 신규            |
| 10  | `portfolio/services/scoring/__init__.py`                | 신규 (registry) |
| 11  | `tests/scoring/__init__.py`                             | 신규 (빈 패키지) |
| 12  | `tests/scoring/test_scoring_engine_base.py`             | 신규 (+3)       |
| 13  | `tests/scoring/test_preset_scorers_dict.py`             | 신규 (+22)      |
| 14  | `docs/portfolio/coach/slice12/part1_closing.md`         | 신규 (본 문서)  |

---

## §4. 주요 발견 & 결정

### Slice 11 PresetType vs 카테고리 비대칭
- Slice 11 `PresetType = Literal["garp", "focused", "income", "growth", "factor"]`
- presets.py 카테고리: value/growth/income/factor/special
- 비대칭: garp→growth, focused→special, value/special 미포함
- **처리 방침**: Part 2에서 adapter가 매핑 처리, Slice 13+ schema 통합 후보 (PS 0.5)

### 별도 score() 함수 부재
- 현재 production에 preset score 정량 계산 함수 없음
- Part 2는 신규 책임 정의 (ROIC, PEG, dividend yield, factor 합성 등)

### `category` ClassVar 도입
- 지시서는 `preset_id`로 카테고리명 사용했으나, 실제 preset_id (예: "buffett_quality_value")와 카테고리명 충돌
- 본 구현: `category` ClassVar로 명확히 구분
- Part 2에서 score() 시 `input_data.preset` (Slice 11 PresetType) 받아 개별 preset 분기

---

## §5. Part 2 진입 준비

| 항목             | 값                                                              |
| ---------------- | --------------------------------------------------------------- |
| Part 2 작업      | 5 ScoringEngine 풀 구현 (NotImplementedError → production logic) |
| 예상 시간        | ~2h                                                             |
| 예상 LLM         | 0 콜                                                            |
| 예상 비용        | $0                                                              |
| 예상 회귀        | +20~30 (5 score + 5 required_metrics 풀 테스트)                 |
| Part 1 자산      | ScoringEngineBase + 5 adapter 스켈레톤 + PRESET_SCORERS dict     |
| **불확실성**     | production score logic 신규 정의 책임 — Part 2 첫 단계에서 카테고리별 spec 확정 필요 |

---

## §6. Slice 12 누적 상태

| Part   | 작업                                          | commit    | 회귀 +Δ | 비용     |
| ------ | --------------------------------------------- | --------- | ------- | -------- |
| Step 0 | #58 + #59 E3 multi-debt mini                  | `f013c48` | +9      | $0.0554  |
| Part 1 | scoring base + 5 adapter 스켈레톤             | (다음)    | +25     | $0       |

전체 누적: 571 → 605 (+34), $0.0554 (cap 5.54%, 마진 94.46%).
