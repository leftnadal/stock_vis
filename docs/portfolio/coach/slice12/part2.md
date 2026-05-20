# Slice 12 Part 2 — 5 ScoringEngine 풀 구현 + PresetSpec schema

> **사전 결정 채택 (Part 2 진입 직전 확정)**
>
> - **D1-A**: 5 카테고리 독립 spec (preset 12종 → 5 카테고리 합성)
> - **D2-B**: weighted_sum + threshold gate 혼합 패턴
> - **D3-B**: PresetSpec Pydantic schema 신설 (frozen + extra=forbid + weights sum validator)
> - **D4-A**: action_items (#59 E5) Part 2 scope 격리, Part 3 이후 자연 처리

---

## 0. 진입 Baseline (실행 전 확인 필수)

| 항목          | 값                                                                        |
| ------------- | ------------------------------------------------------------------------- |
| 브랜치        | `slice12`                                                                 |
| 선행 commit   | `74fd49b` (Part 1 종결)                                                   |
| 회귀 baseline | **605 passed**                                                            |
| 누적 비용     | $2.6998 / $4.00 (마진 32.5%)                                              |
| Slice cap     | $0.0554 / $1.00 (마진 94.46%)                                             |
| LLM 호출      | 4 / 50 (마진 46)                                                          |
| 잔존 부채     | #51 (S13 Step 0 1순위), #59 E5 (PS 0.5, 격리)                             |
| Part 1 산출물 | ScoringEngineBase + 5 카테고리 skel + PRESET_SCORERS + part1_inventory.md |

**진입 전 검증 명령**:

```bash
git log --oneline -1                      # 74fd49b 확인
pytest --co -q | tail -5                  # 605 collected 확인
git status                                # clean tree
```

---

## 1. Part 2 본질 (Scope 명시)

Part 1 inventory에서 명시된 **"별도 score() 함수 부재 → Part 2 신규 책임"**.

Part 2의 책임:

1. **PresetSpec schema 신설** — 가중치·임계·gate 데이터 캡슐화 (D3-B)
2. **5 카테고리 score() 풀 구현** — weighted_sum + gate 패턴 (D1-A + D2-B)
3. **단위 테스트** — schema validator + 정상/gate/경계 case
4. **호출자 무변경** — 외부 통합은 Part 3 smoke에서 자연 발생

**Scope 격리 (D4-A)**:

- action_items 변경 ❌ (#59 E5는 Part 3 이후)
- 외부 service 호출자 수정 ❌ (Part 3 smoke 단계)
- E1~E6 진입점 코드 변경 ❌
- analysis_engine 의존 ❌ (5슬라이스 일관)

---

## 2. Step 0: PresetSpec Pydantic schema 신설 (D3-B)

### 2.1 파일 경로

```
portfolio/services/scoring/preset_spec.py
```

### 2.2 schema 요구사항

```python
from typing import ClassVar
from pydantic import BaseModel, ConfigDict, Field, model_validator

class PresetSpec(BaseModel):
    """Preset scoring 공식 정의 schema.

    D3-B: Slice 11 InputBase/OutputBase 패턴 정합.
    frozen + extra=forbid → 런타임 typo·가중치 합 오류 사전 차단.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    preset_id: str = Field(..., min_length=1)          # 예: "value_classic"
    category: str = Field(..., min_length=1)           # value/growth/income/factor/special
    weights: dict[str, float] = Field(..., min_length=1)   # 지표명 → 가중치
    gate: dict[str, float] | None = None               # D2-B: 임계 조건 (선택)
    description: str = ""

    @model_validator(mode="after")
    def _validate_weights_sum(self) -> "PresetSpec":
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"weights sum must be 1.0 ± 0.001, got {total:.4f} "
                f"for preset {self.preset_id}"
            )
        if any(w < 0 for w in self.weights.values()):
            raise ValueError(
                f"weights must be non-negative for preset {self.preset_id}"
            )
        return self

    @model_validator(mode="after")
    def _validate_category(self) -> "PresetSpec":
        ALLOWED = {"value", "growth", "income", "factor", "special"}
        if self.category not in ALLOWED:
            raise ValueError(
                f"category must be one of {ALLOWED}, got {self.category!r}"
            )
        return self
```

### 2.3 gate 필드 사양 (D2-B 핵심)

`gate`는 카테고리별 threshold 조건. 형식:

```python
{
    "metric_name": threshold_value,
    "_op": "gte"  # 또는 "lte", "gt", "lt" — 기본 "gte"
}
```

**실제 사용 예**:

- income preset: `{"dividend_yield": 0.03, "_op": "gte"}` → yield 3% 미만이면 score=0
- special preset (예: low_volatility): `{"beta": 1.2, "_op": "lte"}` → beta 1.2 초과면 score=0

**구현 위치**: `ScoringEngineBase`에 `_apply_gate(metrics, gate) -> bool` utility (gate 통과 여부 반환).

---

## 3. Step 1: ScoringEngineBase utility 추가

Part 1에서 만든 `portfolio/services/scoring/base.py`에 아래 utility 메서드 추가 (ABC 시그니처는 무변경).

### 3.1 추가 메서드

```python
class ScoringEngineBase(ABC):
    # ... (Part 1 기존 내용 유지)

    category: ClassVar[str]  # Part 1에서 이미 정의

    def _apply_gate(
        self,
        metrics: dict[str, float],
        gate: dict[str, float] | None,
    ) -> bool:
        """D2-B: gate 통과 여부.

        gate=None → 항상 True.
        gate에 _op 키가 없으면 기본 'gte'.

        Returns:
            True: 통과 (정상 score 계산)
            False: 미통과 (score=0 강제)
        """
        if gate is None:
            return True
        op = gate.get("_op", "gte")
        for metric, threshold in gate.items():
            if metric.startswith("_"):
                continue
            value = metrics.get(metric)
            if value is None:
                return False  # 지표 부재 시 미통과
            if op == "gte" and value < threshold:
                return False
            if op == "lte" and value > threshold:
                return False
            if op == "gt" and value <= threshold:
                return False
            if op == "lt" and value >= threshold:
                return False
        return True

    def _weighted_sum(
        self,
        metrics: dict[str, float],
        weights: dict[str, float],
    ) -> float:
        """D2-B: 가중합 계산.

        지표 부재 시 0으로 처리 (gate가 사전 차단해야 정상).
        정규화는 호출자 책임 (카테고리별 자유도).
        """
        return sum(
            metrics.get(name, 0.0) * weight
            for name, weight in weights.items()
        )
```

### 3.2 base.py 수정 후 회귀 확인

```bash
pytest tests/scoring/test_scoring_engine_base.py -v
# Part 1의 3건 PASS 유지 + 신규 utility 테스트 추가 예정 (Step 5)
```

---

## 4. Step 2-6: 5 카테고리 score() 풀 구현 (D1-A)

각 카테고리 파일은 Part 1 스켈레톤 위에 score() 본문 채움.

### 4.1 카테고리별 PresetSpec instance 정의 (12 preset → 5 카테고리 mapping)

**Part 1 inventory 기준 mapping**:

```
value (2):   value_classic, value_deep
growth (2):  growth_quality, growth_momentum
income (2):  income_dividend, income_reit
factor (4):  factor_momentum, factor_quality, factor_low_vol, factor_size
special (2): special_esg, special_thematic
```

> ⚠️ **실제 preset_id 명명은 Part 1 inventory(`part1_inventory.md`)와 일치시킬 것**. 위는 예시이며, 코드 작성 시 inventory 파일을 1차 source로 사용.

### 4.2 카테고리별 score() 구현 패턴

#### value 카테고리 (gate 없음)

```python
# portfolio/services/scoring/presets/value.py
from typing import ClassVar
from portfolio.services.scoring.base import ScoringEngineBase
from portfolio.services.scoring.preset_spec import PresetSpec

VALUE_SPECS: list[PresetSpec] = [
    PresetSpec(
        preset_id="value_classic",
        category="value",
        weights={"pe_ratio_inv": 0.4, "pb_ratio_inv": 0.3, "ev_ebitda_inv": 0.3},
        gate=None,
        description="고전적 가치 평가",
    ),
    PresetSpec(
        preset_id="value_deep",
        category="value",
        weights={"pb_ratio_inv": 0.5, "ps_ratio_inv": 0.3, "fcf_yield": 0.2},
        gate=None,
        description="딥 밸류 평가",
    ),
]

class ValueScoringEngine(ScoringEngineBase):
    category: ClassVar[str] = "value"

    def score(self, metrics: dict[str, float]) -> dict[str, float]:
        result = {}
        for spec in VALUE_SPECS:
            if not self._apply_gate(metrics, spec.gate):
                result[spec.preset_id] = 0.0
                continue
            raw = self._weighted_sum(metrics, spec.weights)
            # 정규화: 0~100 clip
            result[spec.preset_id] = max(0.0, min(100.0, raw * 100))
        # 카테고리 점수 = preset 평균
        result["_category_score"] = (
            sum(v for k, v in result.items() if not k.startswith("_"))
            / len(VALUE_SPECS)
        )
        return result
```

#### income 카테고리 (gate 필수)

```python
# portfolio/services/scoring/presets/income.py
INCOME_SPECS: list[PresetSpec] = [
    PresetSpec(
        preset_id="income_dividend",
        category="income",
        weights={"dividend_yield": 0.6, "payout_ratio_inv": 0.2, "dividend_growth": 0.2},
        gate={"dividend_yield": 0.03, "_op": "gte"},  # yield 3% 미만 컷
        description="배당주",
    ),
    PresetSpec(
        preset_id="income_reit",
        category="income",
        weights={"dividend_yield": 0.5, "ffo_yield": 0.3, "debt_ratio_inv": 0.2},
        gate={"dividend_yield": 0.04, "_op": "gte"},  # REIT yield 4% 미만 컷
        description="리츠",
    ),
]
# class IncomeScoringEngine — value 동일 패턴
```

#### special 카테고리 (gate 비선형 임계)

```python
# portfolio/services/scoring/presets/special.py
SPECIAL_SPECS: list[PresetSpec] = [
    PresetSpec(
        preset_id="special_esg",
        category="special",
        weights={"esg_score": 0.7, "controversy_inv": 0.3},
        gate={"esg_score": 0.5, "_op": "gte"},  # ESG 0.5 미만 컷
        description="ESG",
    ),
    PresetSpec(
        preset_id="special_thematic",
        category="special",
        weights={"theme_relevance": 0.6, "growth_potential": 0.4},
        gate=None,
        description="테마",
    ),
]
```

#### growth / factor 카테고리

- growth: gate 없음, 2 preset
- factor: gate 없음, 4 preset (카테고리 평균 시 4건 합산 / 4)

### 4.3 PRESET_SCORERS dict 갱신

```python
# portfolio/services/scoring/__init__.py
from portfolio.services.scoring.presets.value import ValueScoringEngine
from portfolio.services.scoring.presets.growth import GrowthScoringEngine
from portfolio.services.scoring.presets.income import IncomeScoringEngine
from portfolio.services.scoring.presets.factor import FactorScoringEngine
from portfolio.services.scoring.presets.special import SpecialScoringEngine

PRESET_SCORERS: dict[str, type[ScoringEngineBase]] = {
    "value": ValueScoringEngine,
    "growth": GrowthScoringEngine,
    "income": IncomeScoringEngine,
    "factor": FactorScoringEngine,
    "special": SpecialScoringEngine,
}

def get_scorer(category: str) -> ScoringEngineBase:
    """Part 1 시그니처 유지, 인스턴스 반환."""
    if category not in PRESET_SCORERS:
        raise KeyError(f"Unknown category: {category!r}")
    return PRESET_SCORERS[category]()
```

---

## 5. Step 5: 단위 테스트

### 5.1 PresetSpec validator 테스트

```
tests/scoring/test_preset_spec.py
```

| 테스트                                | 검증                              |
| ------------------------------------- | --------------------------------- |
| `test_valid_spec`                     | 정상 spec 생성 PASS               |
| `test_weights_sum_not_one`            | weights 합 0.97 → ValidationError |
| `test_weights_sum_one_with_tolerance` | 1.0001 → PASS (±0.001)            |
| `test_negative_weight`                | -0.1 가중치 → ValidationError     |
| `test_invalid_category`               | "unknown" → ValidationError       |
| `test_frozen`                         | spec.weights = {} → frozen 에러   |
| `test_extra_forbid`                   | 추가 필드 → ValidationError       |

**예상 +7건**

### 5.2 ScoringEngineBase utility 테스트

```
tests/scoring/test_scoring_engine_base.py (Part 1 파일에 추가)
```

| 테스트                                  | 검증                      |
| --------------------------------------- | ------------------------- |
| `test_gate_none_passes`                 | gate=None → True          |
| `test_gate_gte_pass`                    | yield 0.05 ≥ 0.03 → True  |
| `test_gate_gte_fail`                    | yield 0.02 < 0.03 → False |
| `test_gate_lte_pass`                    | beta 1.0 ≤ 1.2 → True     |
| `test_gate_missing_metric`              | 지표 부재 → False         |
| `test_weighted_sum_basic`               | 기본 합 계산              |
| `test_weighted_sum_missing_metric_zero` | 부재 지표 → 0             |

**예상 +7건** (Part 1 3건 유지 + 신규 7건)

### 5.3 카테고리별 score() 테스트

```
tests/scoring/test_value_engine.py
tests/scoring/test_growth_engine.py
tests/scoring/test_income_engine.py
tests/scoring/test_factor_engine.py
tests/scoring/test_special_engine.py
```

각 카테고리별 표준 테스트 케이스:

| 케이스                                | 검증               |
| ------------------------------------- | ------------------ |
| 정상 metrics → 0~100 범위             | clip 동작          |
| gate 발동 (해당 카테고리만) → score=0 | gate 효과          |
| 모든 preset 0~100 boundary            | 정규화             |
| `_category_score` 평균 일치           | 카테고리 점수 계산 |

**예상 +12~15건** (카테고리당 2~3건, parametrize 활용)

### 5.4 PRESET_SCORERS 통합 테스트

```
tests/scoring/test_preset_scorers_dict.py (Part 1 파일에 추가)
```

| 테스트                                | 검증                   |
| ------------------------------------- | ---------------------- |
| `test_all_5_categories_present`       | dict 5건               |
| `test_get_scorer_returns_instance`    | 인스턴스 반환          |
| `test_get_scorer_unknown_raises`      | KeyError               |
| `test_each_engine_score_returns_dict` | parametrize 5 카테고리 |

**예상 +4건 추가** (Part 1 22건 유지 + 신규 4건)

### 5.5 총 신규 테스트 예상

| 항목                      | 건수       |
| ------------------------- | ---------- |
| PresetSpec validator      | +7         |
| ScoringEngineBase utility | +7         |
| 카테고리별 score()        | +12~15     |
| PRESET_SCORERS 통합       | +4         |
| **합계**                  | **+30~33** |

> ⚠️ **KPI 9 OVER 위험**: 표준 +6~20 대비 +30~33은 OVER. Part 1에서 +25 이미 OVER.
> **D5-A 적용 (Slice 12 종결 시 보정)**: parametrize-heavy 슬라이스 유형으로 분류, #57 패턴 재현. 종결 closing.md에서 명시.

---

## 6. Step 6: 호출자 무변경 확인

```bash
# Part 2 종결 시점 외부 호출자 0건 유지 확인
grep -rn "from portfolio.services.scoring" portfolio/ --include="*.py" \
  | grep -v "portfolio/services/scoring/" \
  | grep -v "tests/"
# 출력 0줄이어야 정상
```

E1~E6 진입점·analysis_engine·view 코드 변경 ❌.

---

## 7. 회귀 + IDENTICAL + 비용 KPI

### 7.1 회귀 KPI

| 항목         | 목표                                            |
| ------------ | ----------------------------------------------- |
| baseline     | 605                                             |
| 신규         | +30~33 (parametrize 영향, KPI 9 OVER 사전 등록) |
| 종결         | **635~638 예상**                                |
| no-cost 분류 | KPI 9a 적용 (cost 0이므로 ±50%)                 |

### 7.2 IDENTICAL 7/7

- E1 (GARP), E2, E3, E3 concentrated, E5, E6, E7 사전 등록 entries 모두 hash 불변
- 외부 호출자 0건이므로 자연 보장

### 7.3 비용

- LLM 호출 0건 목표 (자산 구축 단계)
- Slice cap $0.0554 유지 (마진 94.46%)
- 누적 $2.6998 / $4.00 유지

### 7.4 IDENTICAL 검증

```bash
pytest tests/ -k "identical" -v
# 7/7 PASS 확인
```

---

## 8. 산출물 체크리스트 (예상 ~13건)

| #   | 경로                                                | 내용                                                |
| --- | --------------------------------------------------- | --------------------------------------------------- |
| 1   | `portfolio/services/scoring/preset_spec.py`         | PresetSpec schema (신규)                            |
| 2   | `portfolio/services/scoring/base.py`                | `_apply_gate` + `_weighted_sum` 추가 (수정)         |
| 3   | `portfolio/services/scoring/presets/value.py`       | VALUE_SPECS + ValueScoringEngine 풀                 |
| 4   | `portfolio/services/scoring/presets/growth.py`      | GROWTH_SPECS + GrowthScoringEngine 풀               |
| 5   | `portfolio/services/scoring/presets/income.py`      | INCOME_SPECS + IncomeScoringEngine 풀 (gate 필수)   |
| 6   | `portfolio/services/scoring/presets/factor.py`      | FACTOR_SPECS + FactorScoringEngine 풀 (4 preset)    |
| 7   | `portfolio/services/scoring/presets/special.py`     | SPECIAL_SPECS + SpecialScoringEngine 풀             |
| 8   | `portfolio/services/scoring/__init__.py`            | PRESET_SCORERS dict 갱신 + get_scorer 인스턴스 반환 |
| 9   | `tests/scoring/test_preset_spec.py`                 | validator 7건                                       |
| 10  | `tests/scoring/test_scoring_engine_base.py`         | utility +7건 (Part 1 3건 유지)                      |
| 11  | `tests/scoring/test_value_engine.py` 외 5건         | 카테고리별 12~15건                                  |
| 12  | `tests/scoring/test_preset_scorers_dict.py`         | +4건 (Part 1 22건 유지)                             |
| 13  | `docs/portfolio/coach/slice12/part2_preset_spec.md` | PresetSpec 명세 + 12 preset mapping                 |
| 14  | `docs/portfolio/coach/slice12/part2_closing.md`     | 종결 보고                                           |

---

## 9. 종결 보고 항목 (part2_closing.md)

종결 시 아래 항목 필수 포함:

```markdown
# Slice 12 Part 2 종결 보고

## Baseline

- 선행 commit: 74fd49b (Part 1)
- 회귀 baseline: 605
- 부채 상태: #51, #59 E5 (D4-A 격리 유지)

## 결과

- 회귀: 605 → 635~638 (+30~33)
- KPI 9: OVER (parametrize-heavy 유형, D5-A 적용)
- IDENTICAL: 7/7 PASS
- 비용 Part 2 단독: $0
- Slice 12 누적: $0.0554 / $1.00 (마진 94.46%)
- 전체 누적: $2.6998 / $4.00 (마진 32.5%)

## 신규 자산

- PresetSpec Pydantic schema (frozen+forbid+weights validator)
- 5 카테고리 풀 ScoringEngine (value/growth/income/factor/special)
- gate 패턴 (income 2건, special 1건)
- PRESET_SCORERS dict (5건)

## 부채 변화

- close: 없음 (자산 구축 단계)
- 유지: #51 (S13 1순위), #59 E5 (Part 3 자연 처리)
- 신규: 없음 예상

## 다음 단계

- Part 3: smoke + 부분 matrix ($0.05~0.15, 5×2=10 fixture)
```

---

## 10. 실행 가드 (Claude Code 진입 전 확인)

```bash
# 1. 브랜치 확인
git branch --show-current   # slice12

# 2. baseline 확인
git log --oneline -1        # 74fd49b

# 3. clean tree
git status                  # clean

# 4. pre-commit hook 확인 (Step 0 갱신본)
cat .git/hooks/pre-commit | grep ALLOWED_BRANCHES
# slice12 포함 확인

# 5. Part 1 inventory 1차 확인 (preset_id 명명 source)
cat docs/portfolio/coach/slice12/part1_inventory.md
```

---

## 11. 실행 후 회신 필요 사항

Claude Code 회신 시 아래 보고:

1. commit hash
2. 회귀 변화 (605 → ?)
3. IDENTICAL 7/7 PASS 여부
4. 비용 (Part 2 단독 $0 확인)
5. 산출물 14건 체크리스트
6. PresetSpec validator 동작 케이스 (정상 + 실패 예시 각 1건)
7. gate 발동 케이스 1건 (income_dividend yield 0.02 → score=0)
8. 부채 변화 (close 0, 유지 #51 + #59 E5, 신규 0)
9. `--no-verify` 사용 횟수 (목표 0)

---

## 12. Part 3 사전 등록

Part 2 종결 후 Part 3 진입:

- smoke test 5 카테고리 × 2 fixture = 10 case
- E1~E6 통합 호출자 추가 (외부 호출 처음 발생)
- 비용 $0.05~0.15 예상
- #59 E5 close 기회 (action_items 매트릭스 검증)
