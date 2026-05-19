# Slice 12 Part 1 Step 1 — Production Scoring 인벤토리

**작성일**: 2026-05-20
**작업 범위**: 현재 preset 관련 scoring/평가 logic이 어디 분산되어 있는지 식별 + ScoringEngineBase 설계 근거 도출

---

## §1. 5 카테고리 — 12 preset 매핑

`portfolio/metrics/definitions/presets.py`의 `PRESETS` dict가 **Single Source of Truth**.

| 카테고리 (Part 1 base 분기) | 소속 preset (12)                                    | 개수 |
| ---------------------------- | --------------------------------------------------- | ---- |
| **value**                    | buffett_quality_value, piotroski_f_score            | 2    |
| **growth**                   | garp, quality_growth                                | 2    |
| **income**                   | dividend_growth, shareholder_yield                  | 2    |
| **factor**                   | quality_factor, low_volatility, price_momentum, multi_factor | 4 |
| **special**                  | contrarian, concentrated_portfolio                  | 2    |

> ScoringEngineBase의 sub class 5개는 **카테고리 단위**로 분기. 카테고리 내 individual preset(예: garp vs quality_growth)은 Part 2에서 같은 ScoringEngine이 preset_id 인자로 받아 분기 처리.

---

## §2. 현재 preset 분기 위치 (production 코드 분산)

| 영역                   | 위치                                          | 분기 방식                                           |
| ---------------------- | --------------------------------------------- | --------------------------------------------------- |
| **Preset 정의**        | `portfolio/metrics/definitions/presets.py`    | `PRESETS` dict 단일 소스 (12 preset)                |
| **Preset별 metric**    | `portfolio/metrics/definitions/preset_metrics.py` | `PRESET_METRICS[preset_id]` list[dict]              |
| **AnalysisContext**    | `portfolio/schemas/analysis_context.py`       | `preset_id`, `preset_category` 필드                 |
| **E3 portfolio prompt** | `portfolio/prompts/e3_portfolio/`            | preset_id/intent/score를 prompt 인자로 직접 전달   |
| **E5 prompt**          | `portfolio/prompts/e5/e5_builder.py`          | `current_preset_id` 인자                            |
| **E4 conversation**    | `portfolio/schemas/e4_conversation.py`        | `preset_id` 필드                                    |
| **Slice 11 input**     | `portfolio/schemas/commentary_input.py`       | `preset: PresetType` Literal (garp/focused/income/growth/factor) |
| **Django 모델**        | `portfolio/models.py`                         | `Run.preset_id` CharField, dedup_key에 포함        |
| **선택지표 / scoring**  | (없음)                                        | 별도 함수 없음 — prompt 안 자연어 + metric 선택만   |

### 핵심 발견
- **별도 `score()` 함수 부재**: production에 preset score를 정량 계산하는 단일 함수 없음
- preset 영향은 (a) metric 선택 (b) prompt 텍스트 삽입 두 가지로만 발현
- Slice 12 Part 2가 풀 구현할 ScoringEngine은 **신규 영역** — 기존 코드 이식보다는 새 책임 정의

---

## §3. Slice 11 input schema `PresetType` vs 카테고리 매핑 정합

Slice 11 Part 1에서 정의된 `PresetType` Literal:
```python
PresetType = Literal["garp", "focused", "income", "growth", "factor"]
```

vs presets.py 카테고리:
```
value, growth, income, factor, special
```

### 비대칭 표

| `PresetType` Literal | presets.py 카테고리 | 매핑                                           |
| -------------------- | ------------------- | ---------------------------------------------- |
| `garp`               | (growth 내 1 preset) | growth 카테고리                                |
| `focused`            | (special 내 concentrated_portfolio) | special 카테고리                         |
| `income`             | income              | 일치                                           |
| `growth`             | growth              | 일치                                           |
| `factor`             | factor              | 일치                                           |
| (없음)               | value               | Slice 11 schema 미포함                         |
| (없음)               | special             | Slice 11 schema 미포함 (`focused`로 부분 흡수) |

### 처리 방침 (Part 1 스켈레톤 단계)
- Slice 12 ScoringEngineBase는 **5 카테고리 그대로** (value/growth/income/factor/special)
- Slice 11 schema의 `PresetType`은 Part 2에서 카테고리 매핑 (`garp` → growth, `focused` → special) adapter 책임
- 본 비대칭은 Slice 13+ schema 통합 작업 후보 (PS 0.5, low priority)

---

## §4. ScoringEngineBase 책임 정의 (Part 1 base class 설계 근거)

### 공통 입력
- `input_data: CommentaryInputBase` — Slice 11 Part 1 통합 schema
  - holdings (list[Holding])
  - preset (PresetType — 진입점 카테고리 매핑은 adapter 책임)
  - fetched_at, portfolio_id
  - 진입점별 추가 필드 (E1: garp_metrics, E3: concentration_metrics 등)

### 공통 출력
- `dict[str, Any]` with keys:
  - `score`: float (정규화 단위, Part 2에서 0.0~1.0 결정 예정)
  - `metrics`: dict[str, float] (HHI, sector_concentration, beta 등 산출 메트릭)
  - `reasoning`: str (선택, 카테고리별 점수 해석)

### 카테고리별 분기 패턴
- **value**: ROIC + 안정성 점수 (buffett_quality_value, piotroski_f_score)
- **growth**: PEG + growth quality (garp, quality_growth)
- **income**: dividend yield + dividend growth (dividend_growth, shareholder_yield)
- **factor**: 5+ 팩터 합성 (quality_factor, low_volatility, price_momentum, multi_factor)
- **special**: 집중도 + contrarian (concentrated_portfolio, contrarian)

### 공통 헬퍼 후보 (Part 2 풀 구현 시)
- HHI 계산 (sum(weight^2)) — special / 전체 진단 공통
- 섹터 집중도 (max(sector_weight)) — special / E3
- weighted_avg(metrics, weights) — 전 카테고리

---

## §5. KPI 1 결과

| 항목                                     | 결과 | 비고                                      |
| ---------------------------------------- | ---- | ----------------------------------------- |
| 5 카테고리 모두 식별                     | PASS | value/growth/income/factor/special        |
| 카테고리 내 12 preset 분포 확인           | PASS | 2/2/2/4/2                                 |
| 공통 입력 (CommentaryInputBase) 정합     | PASS | Slice 11 Part 1 자산 그대로 활용 가능     |
| 공통 출력 dict 패턴                       | PASS | score/metrics/reasoning 3 키              |
| 카테고리별 분기 메타데이터 정리           | PASS | §4-카테고리별 분기 패턴                   |
| Slice 11 PresetType vs 카테고리 비대칭   | 식별 | Slice 13+ schema 통합 후보 (PS 0.5)       |
| 별도 score() 함수 부재 확인              | PASS | Part 2 신규 풀 구현 영역                  |

**Step 1 결론**: 카테고리 단위 5 adapter + ScoringEngineBase 신규 골격 적합. Slice 11 schema 자산 100% 재활용.
