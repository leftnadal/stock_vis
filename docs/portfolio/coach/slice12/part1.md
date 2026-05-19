# Slice 12 Part 1 — 작업 지시서 (preset scoring base + 5 adapter 스켈레톤)

**브랜치**: `slice12`
**선행 commit**: f013c48 (Slice 12 Step 0 종결)
**작업 명칭**: preset 일반화 본 work 진입 — scoring engine base class + 5 preset adapter 스켈레톤
**예상 시간**: ~1h
**예상 LLM**: **0 콜**
**예상 비용**: **$0**
**패턴**: Slice 11 Part 1 패턴 그대로 (CommentaryInputBase → ScoringEngineBase, 6 sub → 5 preset adapter, dict 매핑)

---

## §0. baseline 확인 (Part 1 시작 전)

순서대로 확인. 불일치 시 **즉시 중단** 후 보고.

| 항목          | 확인 명령                                                      | 기대값                                                                |
| ------------- | -------------------------------------------------------------- | --------------------------------------------------------------------- |
| 브랜치        | `git branch --show-current`                                    | `slice12`                                                             |
| 선행 commit   | `git log -1 --format='%H %s'`                                  | f013c48 [slice12] Step 0                                              |
| 회귀 baseline | `pytest portfolio/tests tests/coach -q 2>&1 \| tail -3`        | **580 passed**                                                        |
| 부채 상태     | `cat docs/portfolio/coach/debts.md`                            | #51 유지(S13 Step 0 1순위), #59 E5 유지(PS 0.5), #58/#41/#59 E3 close |
| IDENTICAL     | `pytest portfolio/tests/test_identical_hash.py -q`             | 7/7 PASS                                                              |
| 누적 비용     | `cat docs/portfolio/coach/COST_POLICY.md \| grep "cumulative"` | $2.6998 / $4.00 (마진 32.5%)                                          |
| Slice cap     | Step 0 종결.md                                                 | $0.0554 / $1.00 (마진 94.5%)                                          |
| LLM 호출 누적 | Step 0 = 4/50                                                  | 마진 46                                                               |

---

## §1. 사전 작업 — Pre-commit Hook ALLOWED_BRANCHES 갱신 (5분)

### 1-1. 배경

Step 0 commit 시 `--no-verify` 1회 사용 (사용자 허락) — pre-commit hook ALLOWED_BRANCHES에 `slice12` 미등록. Part 1, Part 2, Part 3 매 commit마다 동일 이슈 재발 가능.

### 1-2. 작업

```bash
# pre-commit hook 위치 확인 (일반적으로 .git/hooks/pre-commit 또는 .pre-commit-config.yaml)
find . -name "pre-commit*" -not -path "*/node_modules/*" -not -path "*/.git/objects/*"

# ALLOWED_BRANCHES 변수 위치 검색
grep -rn "ALLOWED_BRANCHES" . --include="*.py" --include="*.sh" --include="*.yaml" --include="*.yml" 2>/dev/null | grep -v ".git/"
```

### 1-3. 갱신 명세

ALLOWED_BRANCHES 정의 위치에서 `slice12` 추가:

```python
# Before
ALLOWED_BRANCHES = ["main", "portfolio", "slice11"]

# After
ALLOWED_BRANCHES = ["main", "portfolio", "slice11", "slice12"]
```

또는 **패턴 매칭**으로 자동 확장 (권장 — 향후 Slice 13+ 자동 호환):

```python
ALLOWED_BRANCHES_PATTERNS = [
    "main",
    "portfolio",
    r"^slice\d+$",  # slice11, slice12, slice13, ... 자동 포함
]
```

### 1-4. 검증

```bash
# 빈 commit으로 hook 동작 확인
git commit --allow-empty -m "test: pre-commit hook on slice12" --dry-run

# 정상이면 다음 단계 진행, 실패 시 ALLOWED_BRANCHES 수정 위치 재확인
```

> **이 사전 작업은 별도 commit으로 분리**. Part 1 본 작업 commit과 섞지 않음.

---

## §2. Step 1 — Production Scoring 인벤토리 (사전 분석)

### 2-1. 산출물

`docs/portfolio/coach/slice12/part1_inventory.md`

### 2-2. 인벤토리 작업

Slice 11 Part 1 §1 패턴 그대로. 현재 preset별 scoring logic이 어디 분산되어 있는지 식별.

**검색 명령**:

```bash
# preset_id 분기 패턴 검색
grep -rn "preset_id" portfolio/ --include="*.py" | grep -v "test_" | head -30

# scoring 관련 모듈 검색
find portfolio/ -path "*/scoring/*" -name "*.py" -not -path "*/test_*"
find portfolio/ -name "*score*.py" -not -path "*/test_*"
find portfolio/ -name "*preset*.py" -not -path "*/test_*"

# 5 preset enum 정의 위치 (Slice 11 Part 1에서 도입)
grep -rn "value.*growth.*income.*factor.*special" portfolio/ --include="*.py" | head -5
```

### 2-3. 인벤토리 표 (예상 형식, 실제 코드베이스 분석 후 갱신)

| preset  | 현재 scoring 위치 | 함수/클래스    | 호출자         | 일반화 가능 영역 |
| ------- | ----------------- | -------------- | -------------- | ---------------- |
| value   | (분석 후 dump)    | (분석 후 dump) | (분석 후 dump) | (분석 후 dump)   |
| growth  |                   |                |                |                  |
| income  |                   |                |                |                  |
| factor  |                   |                |                |                  |
| special |                   |                |                |                  |

### 2-4. 공통 패턴 추출

- **공통 입력**: holdings, preset_id, weights, metrics
- **공통 출력**: score (float), reasoning (str|dict), 또는 dict 형식 결과
- **분기 패턴**: preset별 가중치 / 메트릭 선택 / 임계값 차이
- **공통 헬퍼**: HHI 계산, 섹터 집중도, beta 계산 등

### 2-5. KPI 1: 인벤토리 완성

| 항목                                | 결과      |
| ----------------------------------- | --------- |
| 5 preset 모두 scoring 위치 식별     | PASS/FAIL |
| 공통 입력/출력 패턴 추출            | PASS/FAIL |
| 분기 패턴 정리                      | PASS/FAIL |
| Slice 11 input schema와 정합성 확인 | PASS/FAIL |

---

## §3. Step 2 — ScoringEngineBase 정의

### 3-1. 산출물

`portfolio/services/scoring/base.py` (또는 적정 위치, 인벤토리 결과에 따라)

### 3-2. 설계 명세 (Slice 11 Part 1 패턴 미러)

```python
"""
Slice 12 Part 1 — preset scoring engine base class.
Slice 11 Part 1 CommentaryInputBase 패턴 미러.
"""
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, ConfigDict
from portfolio.schemas.commentary_input import CommentaryInputBase


class ScoringEngineBase(ABC, BaseModel):
    """
    Preset scoring engine abstract base.

    Subclass per preset (value/growth/income/factor/special).
    Slice 11 Part 1 패턴: frozen + extra=forbid는 BaseModel이 강제,
    abstract 메서드는 ABC가 강제.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    preset_id: str  # value/growth/income/factor/special 중 하나

    @abstractmethod
    def score(self, input_data: CommentaryInputBase) -> dict[str, Any]:
        """
        Preset별 scoring 로직.

        Args:
            input_data: Slice 11 Part 1 통합 input schema (CommentaryInputBase 또는 sub class)

        Returns:
            dict with keys:
            - score: float (0.0~1.0 또는 0~100 — 인벤토리 결과 따라 통일)
            - metrics: dict[str, float] (HHI, sector_concentration, etc.)
            - reasoning: str (preset별 설명, 선택)
        """
        ...

    @abstractmethod
    def required_metrics(self) -> list[str]:
        """이 preset이 필요로 하는 메트릭 키 목록."""
        ...
```

### 3-3. 구현 제약 (Slice 11 Part 1 패턴 학습 적용)

| 제약              | 근거                                                               |
| ----------------- | ------------------------------------------------------------------ |
| `frozen=True`     | 인스턴스 immutable, race condition 차단                            |
| `extra="forbid"`  | 의도하지 않은 필드 차단 (Slice 11 Part 1 정착)                     |
| `@abstractmethod` | subclass에서 score/required_metrics 구현 강제                      |
| Pydantic v2 사용  | 기존 코드베이스 호환 (Slice 11 동일)                               |
| frontend 보호     | 기존 코드 무변경 (Part 2에서 adapter 풀 구현 후에도 호출자 무변경) |

### 3-4. KPI 2: ScoringEngineBase 정의

| 항목                            | 결과      |
| ------------------------------- | --------- |
| ABC + BaseModel 상속            | PASS/FAIL |
| frozen + extra=forbid           | PASS/FAIL |
| score/required_metrics abstract | PASS/FAIL |
| Slice 11 input schema import    | PASS/FAIL |

---

## §4. Step 3 — 5 Preset Adapter 스켈레톤

### 4-1. 산출물

`portfolio/services/scoring/presets/value.py`
`portfolio/services/scoring/presets/growth.py`
`portfolio/services/scoring/presets/income.py`
`portfolio/services/scoring/presets/factor.py`
`portfolio/services/scoring/presets/special.py`

### 4-2. 각 adapter 명세 (Slice 11 Part 1 6 sub 패턴 미러)

각 adapter 파일 구조 (예: `value.py`):

```python
"""
Slice 12 Part 1 — value preset scoring adapter (스켈레톤).
실 로직은 Part 2에서 production scoring 코드 이식 후 풀 구현.
"""
from portfolio.services.scoring.base import ScoringEngineBase
from portfolio.schemas.commentary_input import CommentaryInputBase


class ValueScoringEngine(ScoringEngineBase):
    """Value preset scoring engine.

    Slice 12 Part 1: 스켈레톤만 — score/required_metrics는 raise NotImplementedError.
    Slice 12 Part 2: 풀 구현 (production scoring 코드 이식).
    """
    preset_id: str = "value"

    def score(self, input_data: CommentaryInputBase) -> dict[str, Any]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 풀 구현 예정. "
            "Slice 11 Part 3 PromptBuilderBase E2~E6 skel 패턴 동일."
        )

    def required_metrics(self) -> list[str]:
        raise NotImplementedError(
            "Slice 12 Part 1 스켈레톤 — Part 2에서 인벤토리 결과 따라 정의."
        )
```

> 5개 모두 동일 패턴, preset_id만 다름. Slice 11 Part 3 PromptBuilderBase E2~E6 skel 패턴 동일.

### 4-3. KPI 3: 5 adapter 스켈레톤

| 항목                                             | 결과            |
| ------------------------------------------------ | --------------- |
| 5 preset adapter 파일 모두 생성                  | PASS/FAIL (5/5) |
| 각 adapter ScoringEngineBase 상속                | PASS/FAIL (5/5) |
| preset_id 필드 default 값 정확                   | PASS/FAIL (5/5) |
| score/required_metrics raise NotImplementedError | PASS/FAIL (5/5) |

---

## §5. Step 4 — PRESET_SCORERS Dict

### 5-1. 산출물

`portfolio/services/scoring/__init__.py` 또는 `portfolio/services/scoring/registry.py`

### 5-2. 명세 (Slice 11 Part 1 COMMENTARY_INPUT_CLASSES 패턴 미러)

```python
"""
Slice 12 Part 1 — preset scoring registry.
Slice 11 Part 1 COMMENTARY_INPUT_CLASSES 패턴 미러.
"""
from portfolio.services.scoring.base import ScoringEngineBase
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


def get_scorer(preset_id: str) -> ScoringEngineBase:
    """preset_id로 scorer 인스턴스 반환.

    Raises:
        KeyError: preset_id가 PRESET_SCORERS에 없을 때
    """
    cls = PRESET_SCORERS[preset_id]
    return cls()  # frozen Pydantic 인스턴스
```

### 5-3. KPI 4: PRESET_SCORERS dict

| 항목                                                   | 결과      |
| ------------------------------------------------------ | --------- |
| 5 entry 모두 등록 (value/growth/income/factor/special) | PASS/FAIL |
| get_scorer() 5/5 PASS                                  | PASS/FAIL |
| 잘못된 preset_id KeyError raise                        | PASS/FAIL |
| Slice 11 input schema preset enum과 정합               | PASS/FAIL |

---

## §6. Step 5 — 단위 테스트

### 6-1. 산출물

`tests/scoring/test_scoring_engine_base.py` (신규)
`tests/scoring/test_preset_scorers_dict.py` (신규)

### 6-2. 테스트 명세 (Slice 11 Part 1 단위 테스트 패턴 미러 → ~10건 예상)

```python
# tests/scoring/test_scoring_engine_base.py
import pytest
from portfolio.services.scoring.base import ScoringEngineBase


class TestScoringEngineBase:
    """Slice 12 Part 1 #base class"""

    def test_abstract_cannot_instantiate(self):
        """ScoringEngineBase 직접 인스턴스화 불가"""
        with pytest.raises(TypeError):
            ScoringEngineBase()

    def test_frozen_extra_forbid_config(self):
        """Pydantic config 검증"""
        assert ScoringEngineBase.model_config.get("frozen") is True
        assert ScoringEngineBase.model_config.get("extra") == "forbid"

    def test_abstract_methods_defined(self):
        """abstract 메서드 정의 확인"""
        assert "score" in ScoringEngineBase.__abstractmethods__
        assert "required_metrics" in ScoringEngineBase.__abstractmethods__


# tests/scoring/test_preset_scorers_dict.py
import pytest
from portfolio.services.scoring import PRESET_SCORERS, get_scorer
from portfolio.services.scoring.base import ScoringEngineBase


class TestPresetScorersDict:
    """Slice 12 Part 1 #registry"""

    def test_five_presets_registered(self):
        """5 preset 모두 등록 확인"""
        expected = {"value", "growth", "income", "factor", "special"}
        assert set(PRESET_SCORERS.keys()) == expected

    @pytest.mark.parametrize("preset_id", ["value", "growth", "income", "factor", "special"])
    def test_each_scorer_inherits_base(self, preset_id):
        """각 adapter ScoringEngineBase 상속"""
        cls = PRESET_SCORERS[preset_id]
        assert issubclass(cls, ScoringEngineBase)

    @pytest.mark.parametrize("preset_id", ["value", "growth", "income", "factor", "special"])
    def test_get_scorer_returns_instance(self, preset_id):
        """get_scorer 5/5 PASS"""
        scorer = get_scorer(preset_id)
        assert scorer.preset_id == preset_id

    def test_invalid_preset_id_raises(self):
        """잘못된 preset_id KeyError"""
        with pytest.raises(KeyError):
            get_scorer("nonexistent")

    @pytest.mark.parametrize("preset_id", ["value", "growth", "income", "factor", "special"])
    def test_skeleton_score_raises_notimplemented(self, preset_id):
        """Part 1 스켈레톤: score 호출 시 NotImplementedError"""
        scorer = get_scorer(preset_id)
        with pytest.raises(NotImplementedError):
            scorer.score(None)  # Part 2에서 풀 구현

    @pytest.mark.parametrize("preset_id", ["value", "growth", "income", "factor", "special"])
    def test_skeleton_required_metrics_raises(self, preset_id):
        """Part 1 스켈레톤: required_metrics 호출 시 NotImplementedError"""
        scorer = get_scorer(preset_id)
        with pytest.raises(NotImplementedError):
            scorer.required_metrics()
```

### 6-3. 단위 테스트 카운트 예상

- ScoringEngineBase: 3건
- PRESET_SCORERS dict: 4건 + parametrize 3개 (5×3=15 — 단, pytest parametrize는 collected count = 15이므로 회귀 +Δ에 +15 직접 포함됨)

**총 회귀 영향**: +18 (base 3 + dict 4 + parametrize 15 - 단, pytest collect 방식에 따라 ±2)

> Slice 11 Part 1 회귀 +9 (parametrize 미사용) 패턴과 비교 시 더 많을 수 있음. KPI 10 임계 +9~15 표준이지만 parametrize 15건이 핵심이라 임계 ±30% 외 가능 — 사유 명시.

### 6-4. KPI 5: 단위 테스트

| 항목                                  | 결과            |
| ------------------------------------- | --------------- |
| test_scoring_engine_base.py 3/3 PASS  | PASS/FAIL       |
| test_preset_scorers_dict.py 모두 PASS | PASS/FAIL       |
| parametrize 5 preset 모두 PASS        | PASS/FAIL (5/5) |
| 단위 테스트 회귀 +Δ                   | +15~20          |

---

## §7. Step 6 — 호출자 무변경 검증 (Frontend 보호)

### 7-1. 검증 작업

Slice 11 Part 1/2 패턴 — 새 base class 도입했으나 기존 호출자 코드 변경 없음 확인.

```bash
# 1. 새 모듈 import한 곳 없는지 (Part 1 단계)
grep -rn "from portfolio.services.scoring" portfolio/ --include="*.py" | grep -v "test_" | grep -v "portfolio/services/scoring/"
# 기대: 빈 결과 (Part 2에서 호출자 통합 시작 예정)

# 2. 기존 production scoring 함수 인터페이스 변경 없음
git diff f013c48 HEAD -- portfolio/ | grep -E "^-(def |class )" | head -10
# 기대: production scoring 함수 시그니처 변경 0

# 3. 기존 회귀 580 그대로
pytest portfolio/tests tests/coach -q 2>&1 | tail -3
```

### 7-2. KPI 6: 호출자 무변경

| 항목                                   | 결과                            |
| -------------------------------------- | ------------------------------- |
| 기존 production scoring 함수 0 변경    | PASS/FAIL                       |
| Part 1 새 모듈 호출자 0건              | PASS/FAIL (Part 2 시작 전 정상) |
| 기존 회귀 580 그대로 (신규 +α만 추가)  | PASS/FAIL                       |
| frontend 보호 (전체 production 무변경) | PASS/FAIL                       |

---

## §8. 회귀 + IDENTICAL + KPI 종합

### 8-1. 회귀 측정

```bash
pytest portfolio/tests tests/coach tests/scoring -q 2>&1 | tail -3
```

**기대값**: 580 → 595~600 (+15~20, parametrize 영향)

**KPI 10 판정 기준** (Slice 11 D5-A 갱신 기준):

- 표준 슬라이스 part: +9~15 (±30% +6~20)
- 본 케이스 (+15~20): 임계 내 PASS

### 8-2. IDENTICAL 확인

```bash
pytest portfolio/tests/test_identical_hash.py -q 2>&1 | tail -3
```

**기대값**: 7/7 PASS

### 8-3. 비용

- Part 1 단독: $0 (LLM 호출 0)
- Slice 12 누적: $0.0554 / $1.00 (마진 94.5% 그대로)
- 전체 누적: $2.6998 / $4.00 (마진 32.5% 그대로)

---

## §9. KPI Matrix (Part 1 종합)

| #   | KPI                                     | 측정값 | 기대값                        | PASS/FAIL |
| --- | --------------------------------------- | ------ | ----------------------------- | --------- |
| 1   | Production scoring 인벤토리 (5 preset)  | \_     | 5/5                           | PASS      |
| 2   | ScoringEngineBase 정의 (ABC+BaseModel)  | \_     | O                             | PASS      |
| 3   | 5 adapter 스켈레톤 생성                 | \_     | 5/5                           | PASS      |
| 4   | PRESET_SCORERS dict 5 entry             | \_     | 5                             | PASS      |
| 5   | get_scorer 5/5 + KeyError 1             | \_     | PASS                          | PASS      |
| 6   | 단위 테스트 (base 3 + dict parametrize) | \_     | +15~20                        | PASS      |
| 7   | 호출자 무변경 검증                      | \_     | O                             | PASS      |
| 8   | 기존 회귀 580 baseline 유지             | \_     | 580                           | PASS      |
| 9   | 신규 회귀 +Δ (표준 슬라이스 임계)       | \_     | +9~15 또는 +15~20 parametrize | PASS      |
| 10  | IDENTICAL                               | \_     | 7/7                           | PASS      |
| 11  | 비용 $0 (LLM 호출 0)                    | \_     | $0                            | PASS      |
| 12  | Pre-commit hook 정상 동작               | \_     | --no-verify 불필요            | PASS      |

---

## §10. 회신 형식 (Claude Code → 병진)

```
## Slice 12 Part 1 완료 보고 (preset scoring base + 5 adapter 스켈레톤)

### baseline 확인
- [O/X] 브랜치: slice12 (from f013c48)
- [O/X] 회귀 baseline: 580 passed
- [O/X] 부채 상태: #51/#59 E5 유지, 나머지 close

### 사전 작업: Pre-commit hook 갱신
- [O/X] ALLOWED_BRANCHES에 slice12 추가 (또는 패턴 매칭 도입)
- [O/X] 검증: 빈 commit dry-run PASS
- [O/X] 별도 commit 분리

### Step 1: Production scoring 인벤토리
- [O/X] part1_inventory.md 생성
- 5 preset scoring 위치 식별: value=_, growth=_, income=_, factor=_, special=_
- 공통 입력/출력 패턴 추출
- 분기 패턴 정리

### Step 2: ScoringEngineBase 정의
- [O/X] portfolio/services/scoring/base.py 생성
- ABC + BaseModel(frozen + extra=forbid)
- score/required_metrics abstract

### Step 3: 5 adapter 스켈레톤
- [O/X] presets/{value,growth,income,factor,special}.py 5/5 생성
- 각 adapter NotImplementedError raise (Part 2 풀 구현 예정)

### Step 4: PRESET_SCORERS dict
- [O/X] portfolio/services/scoring/__init__.py 또는 registry.py 생성
- 5 entry 등록, get_scorer() 5/5 + KeyError 1

### Step 5: 단위 테스트
- [O/X] test_scoring_engine_base.py +3
- [O/X] test_preset_scorers_dict.py +4 + parametrize ~15
- 단위 테스트 회귀 영향 +Δ

### Step 6: 호출자 무변경
- [O/X] 기존 production scoring 함수 0 변경
- [O/X] Part 1 새 모듈 호출자 0건 (정상)
- [O/X] frontend 보호 확인

### 회귀 + IDENTICAL
- 회귀: 580 → N (변화 +Δ)
- KPI 10: PASS (표준 슬라이스 임계 +9~15) 또는 +15~20 parametrize 사유 명시
- IDENTICAL: 7/7 PASS

### 비용
- Part 1 단독: $0
- Slice 12 누적: $0.0554 / $1.00 (마진 94.5%)
- 전체 누적: $2.6998 / $4.00 (마진 32.5%)

### 산출물 (10~12건)
1. (사전) Pre-commit hook 갱신 (별도 commit)
2. docs/portfolio/coach/slice12/part1_inventory.md
3. portfolio/services/scoring/base.py
4. portfolio/services/scoring/presets/value.py
5. portfolio/services/scoring/presets/growth.py
6. portfolio/services/scoring/presets/income.py
7. portfolio/services/scoring/presets/factor.py
8. portfolio/services/scoring/presets/special.py
9. portfolio/services/scoring/__init__.py (또는 registry.py)
10. tests/scoring/test_scoring_engine_base.py
11. tests/scoring/test_preset_scorers_dict.py
12. docs/portfolio/coach/slice12/part1_closing.md

### git commit
- [pre-commit hook] "build: pre-commit hook allows slice12"
- [Part 1 본 작업] "[slice12] Part 1: preset scoring base + 5 adapter 스켈레톤"

### 다음 단계 (사용자에게)
1. Part 1 종결 확정 여부
2. Slice 12 Part 2 진입 (5 preset adapter 풀 구현) 또는 결정 사이클 추가
```

---

## §11. Fallback 가이드

| 상황                                                                          | 대응                                                                                          |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| baseline 회귀 ≠ 580                                                           | 즉시 중단. Slice 12 Step 0 종결 commit 확인                                                   |
| 인벤토리에서 5 preset 중 일부 미발견                                          | 사용자 보고. Slice 5 preset enum 등록 시점과 실제 production scoring 분기 패턴 차이 확인      |
| ScoringEngineBase ABC 인스턴스화 가능 (test_abstract_cannot_instantiate FAIL) | abstractmethod decorator 정상 적용 확인                                                       |
| 5 adapter 중 일부에서 ScoringEngineBase 상속 누락                             | adapter 파일 검토 후 수정                                                                     |
| PRESET_SCORERS dict 5 entry 미충족                                            | **init**.py 또는 registry.py에서 import + 등록 확인                                           |
| parametrize 단위 테스트 카운트 비정상 (예: 1개만 collected)                   | conftest.py 또는 pytest 설정 확인                                                             |
| 기존 production scoring 회귀 깨짐 (580 미만)                                  | 즉시 중단. 호출자 무변경 검증 다시 확인. Part 1에서 production 코드 변경 없어야 함            |
| 회귀 +Δ가 +20 초과                                                            | parametrize 카운트 정상이나 다른 사유 점검 (classifier 신규 등)                               |
| IDENTICAL ≠ 7/7                                                               | 즉시 중단. hash 변경 위치 보고                                                                |
| Pre-commit hook 갱신 후 동작 안 함                                            | ALLOWED_BRANCHES 변경 사항 hook 파일에 정확히 반영됐는지 재확인                               |
| Pre-commit hook 위치 검색 실패                                                | `.git/hooks/pre-commit` (실행 권한 있음) 또는 `.pre-commit-config.yaml` (yaml 형식) 모두 검사 |

---

## §12. Part 2 진입 준비 (Part 1 종결 후 자연 흐름)

### 12-1. Part 2 사전 등록 사항

| 항목             | 값                                                                      |
| ---------------- | ----------------------------------------------------------------------- |
| 작업명           | 5 preset adapter 풀 구현 (production scoring 코드 이식)                 |
| 예상 시간        | ~2h                                                                     |
| 예상 LLM         | 0 콜                                                                    |
| 예상 비용        | $0                                                                      |
| 예상 회귀        | +20~30 (5 adapter 풀 구현 + 단위 테스트)                                |
| Part 1 자산 활용 | ScoringEngineBase + 5 adapter 스켈레톤 + PRESET_SCORERS dict + 인벤토리 |

### 12-2. Part 2 작업 흐름 (예고)

1. 인벤토리 결과 따라 5 preset 각각의 score / required_metrics 풀 구현
2. 기존 production scoring 함수 → adapter 위임 (점진 마이그레이션, frontend 보호)
3. 단위 테스트 풀 추가 (preset별 score 정확성 검증)
4. 회귀 + IDENTICAL 확인

---

## 📋 Part 1 작업 요약 (Stock-Vis Portfolio Coach의 어느 부분?)

**서비스 위치**: Slice 12 본 work인 **preset 스코어링 엔진 일반화**의 **첫 단계 (base class + 스켈레톤)**. 사용자가 포트폴리오 진단 받을 때 preset(value/growth/income/factor/special)별로 다르게 적용되던 스코어링 logic을 **공통 base class 기반으로 일반화**. Part 1은 구조만 잡고 실제 logic은 Part 2에서 이식.

### 무엇을 진행하나?

| Step   | 작업                                       | 예상 결과                           |
| ------ | ------------------------------------------ | ----------------------------------- |
| 사전   | Pre-commit hook 갱신 (slice12 + 패턴 매칭) | --no-verify 불필요                  |
| Step 1 | Production scoring 인벤토리 분석           | 5 preset 현재 위치 + 공통 패턴 식별 |
| Step 2 | ScoringEngineBase 정의 (ABC + Pydantic)    | base.py 1건                         |
| Step 3 | 5 adapter 스켈레톤 (NotImplementedError)   | presets/\*.py 5건                   |
| Step 4 | PRESET_SCORERS dict 등록                   | registry.py 또는 **init**.py 1건    |
| Step 5 | 단위 테스트 (base + dict + parametrize 5)  | test 파일 2건, +15~20 테스트        |
| Step 6 | 호출자 무변경 검증                         | frontend 보호 확인                  |

### 예상 결과 (Part 1 종결 시점)

- **회귀**: 580 → 595~600 (+15~20)
- **부채 변화**: 0 (Part 1은 신규 자산 구축 단계, 부채 미발생)
- **비용**: $0 (LLM 호출 0)
- **IDENTICAL**: 7/7 유지
- **frontend 보호**: 기존 production scoring 코드 무변경 확인
- **--no-verify 사용**: 0 (pre-commit hook 갱신 효과)

### 사용자 영향 (Part 1 단독)

| 영역              | 변화                                                                        |
| ----------------- | --------------------------------------------------------------------------- |
| **앱 사용자 UX**  | 0 (Part 1은 internal 구조 작업, 사용자 영향 0)                              |
| **개발자**        | 향후 preset 추가 시 ScoringEngineBase 상속 + dict 등록만으로 자연 확장 가능 |
| **시스템 안정성** | frontend 보호 (기존 회귀 그대로)                                            |

### 다음 흐름

Part 1 회신 → Part 2 (5 preset adapter 풀 구현, production scoring 이식) 작업 지시서 작성 → Part 3 (smoke + 부분 matrix) → Part 4 (manual eval D1-D + D2-A blind) → Slice 12 종결 결정 사이클.
