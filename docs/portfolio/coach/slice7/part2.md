# Slice 7 Part 2 작업 지시서 — E4 Schema 구현 + Mock Fixture + Rubric §C 강화

> **Part 2 범위**: Part 1에서 docs로 설계한 E4 schema와 mock fixture 시나리오를 **실제 코드/JSON으로 구현**.
>
> - rubric §C 룰 명문화 (#26 부채 처리) + #β2 estimator 외삽 정밀도 검증.
>   **회귀 영향**: 신규 회귀 +10~15건 예상 (E4 schema validation + mock fixture round-trip).
>   **비용**: $0 (LLM 호출 0, mock 단계).
>   **선행 컨텍스트**: H3 verdict = h3_confirmed (J2) — 단 신뢰도 weak signal로 분류.

---

## §0. 사전 체크 (5초)

```bash
git status
git log --oneline -5
pytest -q  # 395 passed 확인

# Part 1 산출물 확인
ls docs/portfolio/coach/slice7/step3_e4_schema_design.md
ls docs/portfolio/coach/slice7/step4_e4_mock_fixture_scenarios.md
ls docs/portfolio/coach/manual_eval_rubric.md
cat docs/portfolio/coach/COST_POLICY.md | head -20  # 임계 $1.50 확인

# 기존 schema 패턴 확인 (E3 portfolio-level 참고)
ls portfolio/coach/schemas/
cat portfolio/coach/token_budgets.py
```

- [ ] 395 passed
- [ ] Part 1 산출물 5건 존재 (rubric / step3 / step4 / COST_POLICY / step0_2 H3 결과)
- [ ] 기존 schema 디렉토리 구조 확인

---

## §1. E4 Pydantic Schema 구현

### 1.1 파일 생성: `portfolio/coach/schemas/e4_conversation.py`

Part 1 §3.2에서 설계한 schema를 코드로 구현. 기존 schema 패턴 (E1~E3, E5~E6) 일관성 유지.

```python
"""
E4 대화 Q&A schema (Slice 7 Part 2).

Tier 1~3 multi-turn 지원. Tier 2 세션 요약은 Phase 2 (사용자 메모리 정책).
Slice 7 Part 1 step3_e4_schema_design.md 기반.

References:
- portfolio/coach/schemas/e3_portfolio_concentration.py (E3 portfolio-level 패턴)
- portfolio/coach/schemas/e1_garp.py (Pydantic v2 패턴)
"""

from __future__ import annotations
from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


# ===== Conversation Turn =====

class E4ConversationTurn(BaseModel):
    """단일 turn (사용자 질문 또는 LLM 답변)."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)
    timestamp: datetime
    turn_idx: int = Field(ge=0)

    model_config = {"frozen": True}


# ===== Input =====

class E4ConversationInput(BaseModel):
    """E4 대화 진입점 입력."""

    # 포트폴리오 컨텍스트 (E3 portfolio-level과 공통)
    portfolio_id: str = Field(min_length=1)
    preset_id: str = Field(min_length=1)
    portfolio_metrics: dict[str, float]  # Core 7 portfolio 지표
    holdings_summary: str = Field(min_length=1, max_length=2000)

    # 대화 컨텍스트
    conversation_history: list[E4ConversationTurn] = Field(default_factory=list)
    current_user_question: str = Field(min_length=1, max_length=1000)
    tier: Literal[1, 2, 3]

    # 메타
    session_id: str = Field(min_length=1)
    max_history_turns: int = Field(default=5, ge=0, le=20)

    @model_validator(mode="after")
    def validate_tier_consistency(self) -> "E4ConversationInput":
        """Tier와 conversation_history 일관성 검증 (분기 케이스 I2 사전 차단)."""
        n_turns = len(self.conversation_history)
        if self.tier == 1 and n_turns > 0:
            # Tier 1인데 history 존재 → 경고만 (downgrade 로직은 service layer)
            pass
        if self.tier in (2, 3) and n_turns == 0:
            # Tier 2/3인데 history 비어있음 → I2 분기
            raise ValueError(
                f"Tier {self.tier} requires non-empty conversation_history "
                f"(use tier=1 for first turn)"
            )
        return self


# ===== Output =====

class E4ConversationOutput(BaseModel):
    """LLM 답변."""

    answer: str = Field(min_length=20, max_length=2000)

    referenced_metrics: list[str] = Field(
        default_factory=list,
        description="이 답변에서 인용한 portfolio_metrics key들",
    )
    follow_up_suggestions: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="후속 질문 추천 (Tier 2/3 활용)",
    )
    confidence: Literal["high", "medium", "low"] = "medium"

    @model_validator(mode="after")
    def validate_referenced_metrics_format(self) -> "E4ConversationOutput":
        """referenced_metrics key 형식 검증 (I4 분기 사전 체크 일부)."""
        # snake_case 검증 (portfolio_metrics와 일관)
        for key in self.referenced_metrics:
            if not key or " " in key or key != key.lower():
                raise ValueError(
                    f"referenced_metrics key must be snake_case: '{key}'"
                )
        return self


# ===== Metadata (분기 케이스 trace) =====

class E4ConversationMetadata(BaseModel):
    """E4 호출 메타데이터 (분기 케이스 trace용)."""

    case_flags: list[Literal["I1", "I2", "I3", "I4"]] = Field(default_factory=list)
    history_truncated: bool = False  # I1 발동 여부
    tier_downgraded_from: Optional[Literal[1, 2, 3]] = None  # I2 발동 시 원래 tier
    hallucinated_metrics: list[str] = Field(default_factory=list)  # I4 발동 시
```

### 1.2 회귀 테스트 추가

`tests/portfolio/coach/test_e4_conversation_schema.py`:

```python
"""E4 conversation schema 회귀 테스트 (Slice 7 Part 2)."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from portfolio.coach.schemas.e4_conversation import (
    E4ConversationTurn,
    E4ConversationInput,
    E4ConversationOutput,
    E4ConversationMetadata,
)


# ===== Turn =====

def test_turn_valid():
    t = E4ConversationTurn(
        role="user",
        content="내 포트폴리오 집중도가 높아?",
        timestamp=datetime(2026, 5, 11, 10, 0, 0),
        turn_idx=0,
    )
    assert t.role == "user"
    assert t.turn_idx == 0


def test_turn_content_empty_rejected():
    with pytest.raises(ValidationError):
        E4ConversationTurn(
            role="user",
            content="",
            timestamp=datetime.now(),
            turn_idx=0,
        )


def test_turn_invalid_role_rejected():
    with pytest.raises(ValidationError):
        E4ConversationTurn(
            role="system",  # only user/assistant allowed
            content="hi",
            timestamp=datetime.now(),
            turn_idx=0,
        )


def test_turn_frozen():
    t = E4ConversationTurn(
        role="user",
        content="hi",
        timestamp=datetime.now(),
        turn_idx=0,
    )
    with pytest.raises(ValidationError):
        t.role = "assistant"  # frozen


# ===== Input =====

def _base_input_kwargs():
    return dict(
        portfolio_id="p_001",
        preset_id="V1_garp",
        portfolio_metrics={
            "hhi_concentration": 0.45,
            "sector_hhi": 0.50,
            "top3_weight": 0.65,
            "holding_count": 5,
            "portfolio_beta": 1.10,
            "max_position_weight": 0.30,
            "avg_correlation": 0.40,
        },
        holdings_summary="Tech 50%, Healthcare 30%, Financials 20%. Top 3: AAPL/MSFT/NVDA.",
        current_user_question="내 포트폴리오 집중도가 높아?",
        tier=1,
        session_id="s_001",
    )


def test_input_tier1_no_history_ok():
    inp = E4ConversationInput(
        conversation_history=[],
        **_base_input_kwargs(),
    )
    assert inp.tier == 1


def test_input_tier2_empty_history_rejected():
    """I2 분기 사전 차단: tier=2/3인데 history 비어있음."""
    kwargs = _base_input_kwargs()
    kwargs["tier"] = 2
    with pytest.raises(ValidationError) as exc:
        E4ConversationInput(conversation_history=[], **kwargs)
    assert "non-empty conversation_history" in str(exc.value)


def test_input_tier3_with_history_ok():
    history = [
        E4ConversationTurn(role="user", content="Q1", timestamp=datetime.now(), turn_idx=0),
        E4ConversationTurn(role="assistant", content="A1 답변 내용 (20자 이상 필요).", timestamp=datetime.now(), turn_idx=1),
    ]
    kwargs = _base_input_kwargs()
    kwargs["tier"] = 3
    inp = E4ConversationInput(conversation_history=history, **kwargs)
    assert len(inp.conversation_history) == 2


def test_input_max_history_turns_default():
    inp = E4ConversationInput(conversation_history=[], **_base_input_kwargs())
    assert inp.max_history_turns == 5


# ===== Output =====

def _base_output_kwargs():
    return dict(
        answer="포트폴리오 hhi_concentration 0.45는 중간 집중도이며 분산 검토를 권장합니다.",
        referenced_metrics=["hhi_concentration", "sector_hhi"],
        follow_up_suggestions=["어떻게 분산하나요?", "추가 종목 추천"],
        confidence="medium",
    )


def test_output_valid():
    out = E4ConversationOutput(**_base_output_kwargs())
    assert out.confidence == "medium"
    assert len(out.referenced_metrics) == 2


def test_output_answer_too_short_rejected():
    kwargs = _base_output_kwargs()
    kwargs["answer"] = "짧음"
    with pytest.raises(ValidationError):
        E4ConversationOutput(**kwargs)


def test_output_referenced_metrics_non_snake_case_rejected():
    """I4 사전 체크: snake_case 위반."""
    kwargs = _base_output_kwargs()
    kwargs["referenced_metrics"] = ["HHI Concentration"]  # 공백 + 대문자
    with pytest.raises(ValidationError) as exc:
        E4ConversationOutput(**kwargs)
    assert "snake_case" in str(exc.value)


def test_output_follow_up_max_3():
    kwargs = _base_output_kwargs()
    kwargs["follow_up_suggestions"] = ["q1", "q2", "q3", "q4"]  # >3
    with pytest.raises(ValidationError):
        E4ConversationOutput(**kwargs)


# ===== Metadata =====

def test_metadata_default_empty():
    m = E4ConversationMetadata()
    assert m.case_flags == []
    assert m.history_truncated is False
    assert m.tier_downgraded_from is None
    assert m.hallucinated_metrics == []


def test_metadata_i1_flag():
    m = E4ConversationMetadata(case_flags=["I1"], history_truncated=True)
    assert "I1" in m.case_flags
    assert m.history_truncated is True


def test_metadata_i2_downgrade_trace():
    m = E4ConversationMetadata(case_flags=["I2"], tier_downgraded_from=3)
    assert m.tier_downgraded_from == 3
```

### 1.3 회귀 실행

```bash
pytest -q tests/portfolio/coach/test_e4_conversation_schema.py
```

**기대**: 15건 신규 PASS, 누적 회귀 395 → 410 예상.

### 1.4 DIMENSION_LOOKUP entry 추가

`portfolio/coach/dimensions.py` (또는 동일 역할 파일)에 E4 dispatch 1줄 추가:

```python
DIMENSION_LOOKUP = {
    # ... 기존 entries ...
    "e4_conversation": {
        "input_schema": E4ConversationInput,
        "output_schema": E4ConversationOutput,
        "metadata_schema": E4ConversationMetadata,
        "prompt_builder": None,  # Slice 7 Part 3에서 추가
        "budget_key": "e4_conversation_tier1",  # Tier별 분기는 service layer
    },
}
```

> **참고**: Slice 4부터 정착한 `_main_unified` + DIMENSION_LOOKUP 1줄 entry 자동 dispatch 패턴 일관 유지.

---

## §2. `token_budgets.py` 갱신

### 2.1 E4 Tier별 budget 추가

```python
# portfolio/coach/token_budgets.py
BUDGETS = {
    "e1_garp": 5000,
    "e5_extraction": 2000,
    "e2_diversification": 1500,
    "e6_quality_score": 1500,
    "e3_concentration": 7000,
    "e3_portfolio": 7000,
    # === Slice 7 Part 2 신규 ===
    "e4_conversation_tier1": 6000,
    "e4_conversation_tier2": 8000,
    "e4_conversation_tier3": 12000,
}
```

### 2.2 budget 추정 근거 docs

`docs/portfolio/coach/slice7/step2_e4_budget_rationale.md`:

```markdown
# E4 Tier별 Budget 추정 근거

## 추정 기반

- Slice 6 e3_portfolio P90/max input: 4,030 (portfolio context ~3,500 chars)
- 대화 turn 평균 길이 추정: 700 chars/turn (질문 200 + 답변 500)

## Tier별 산식

| Tier   | input 추정                      | 안전 마진 | budget     | 근거                                    |
| ------ | ------------------------------- | --------- | ---------- | --------------------------------------- |
| Tier 1 | 3,500 (portfolio + question)    | 1.7×      | **6,000**  | history 0                               |
| Tier 2 | 3,500 + (2 turns × 700) = 4,900 | 1.6×      | **8,000**  | history 1~2 turns                       |
| Tier 3 | 3,500 + (5 turns × 700) = 7,000 | 1.7×      | **12,000** | history 3~5 turns (max_history_turns=5) |

## #β2 재오픈 검증 대상

- Slice 6 e3_portfolio 추정 1500 vs 실측 4359 = +366% 편차
- Slice 7 Part 2에서 mock fixture 15 cases input 길이 실측 → estimator 정확도 KPI
- 정확도 ±30% 이내면 #β2 close 가능 (Slice 8 Step 0 후보 변경)
```

---

## §3. Mock Fixture 15 Cases JSON 구현

### 3.1 디렉토리 구조

```
tests/fixtures/portfolio/e4_conversation/
├── S01_V1_tier1.json
├── S02_V1_tier2.json
├── S03_V1_tier3.json
├── S04_V2_tier1.json
├── S05_V2_tier2.json
├── S06_V3_tier1.json
├── S07_V3_tier2.json
├── S08_V4_tier1.json
├── S09_V4_tier2.json
├── S10_V5_tier1.json
├── S11_V5_tier3.json
├── S12_V1_tier2_overflow.json     # I1 trigger
├── S13_V1_tier2_empty_history.json # I2 trigger
├── S14_V2_tier3_hallucination.json # I4 trigger
└── S15_V3_tier1_low_conf.json
```

### 3.2 fixture 표준 양식

```json
{
	"scenario_id": "S01",
	"description": "V1 balanced GARP, Tier 1 baseline",
	"preset_id": "V1_garp",
	"tier": 1,
	"trigger_case": null,
	"input": {
		"portfolio_id": "p_001",
		"preset_id": "V1_garp",
		"portfolio_metrics": {
			"hhi_concentration": 0.35,
			"sector_hhi": 0.4,
			"top3_weight": 0.6,
			"holding_count": 5,
			"portfolio_beta": 1.05,
			"max_position_weight": 0.25,
			"avg_correlation": 0.35
		},
		"holdings_summary": "Tech 50%, Healthcare 25%, Financials 25%. Top 3: AAPL/UNH/JPM.",
		"conversation_history": [],
		"current_user_question": "내 포트폴리오의 집중도가 높은 편인가요?",
		"tier": 1,
		"session_id": "s_001",
		"max_history_turns": 5
	},
	"expected_output": {
		"answer": "hhi_concentration 0.35는 중간 수준이며...",
		"referenced_metrics": ["hhi_concentration", "top3_weight"],
		"follow_up_suggestions": ["어떻게 분산할까요?", "현재 비중 적절한가요?"],
		"confidence": "medium"
	},
	"expected_metadata": {
		"case_flags": [],
		"history_truncated": false,
		"tier_downgraded_from": null,
		"hallucinated_metrics": []
	},
	"notes": "GARP preset baseline, history 없음, 표준 응답 기대"
}
```

### 3.3 분기 trigger fixture 양식 (S12 예시)

```json
{
	"scenario_id": "S12",
	"description": "V1 garp, Tier 2 with history overflow (I1 trigger)",
	"preset_id": "V1_garp",
	"tier": 2,
	"trigger_case": "I1",
	"input": {
		"...": "...",
		"conversation_history": [
			{ "role": "user", "content": "Q1", "timestamp": "...", "turn_idx": 0 },
			{
				"role": "assistant",
				"content": "A1 답변...",
				"timestamp": "...",
				"turn_idx": 1
			},
			{ "role": "user", "content": "Q2", "timestamp": "...", "turn_idx": 2 },
			{
				"role": "assistant",
				"content": "A2 답변...",
				"timestamp": "...",
				"turn_idx": 3
			},
			{ "role": "user", "content": "Q3", "timestamp": "...", "turn_idx": 4 },
			{
				"role": "assistant",
				"content": "A3 답변...",
				"timestamp": "...",
				"turn_idx": 5
			}
		],
		"max_history_turns": 5
	},
	"expected_metadata": {
		"case_flags": ["I1"],
		"history_truncated": true
	}
}
```

### 3.4 fixture round-trip 회귀 테스트

`tests/portfolio/coach/test_e4_fixtures.py`:

```python
"""E4 mock fixture round-trip 회귀 (Slice 7 Part 2)."""

import json
import pytest
from pathlib import Path

from portfolio.coach.schemas.e4_conversation import (
    E4ConversationInput,
    E4ConversationOutput,
    E4ConversationMetadata,
)

FIXTURE_DIR = Path("tests/fixtures/portfolio/e4_conversation")
ALL_FIXTURES = sorted(FIXTURE_DIR.glob("S*.json"))


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=lambda p: p.stem)
def test_fixture_input_valid(fixture_path):
    """모든 fixture의 input이 schema validation 통과."""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    # I2 trigger fixture는 validation 실패 기대
    if data.get("trigger_case") == "I2":
        with pytest.raises(Exception):
            E4ConversationInput(**data["input"])
    else:
        inp = E4ConversationInput(**data["input"])
        assert inp.portfolio_id


@pytest.mark.parametrize("fixture_path", ALL_FIXTURES, ids=lambda p: p.stem)
def test_fixture_expected_output_valid(fixture_path):
    """모든 fixture의 expected_output이 schema validation 통과."""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if "expected_output" in data and data["expected_output"] is not None:
        out = E4ConversationOutput(**data["expected_output"])
        assert len(out.answer) >= 20


def test_fixture_count_matches_scenarios():
    """15 cases 정의대로 fixture 15건 존재."""
    assert len(ALL_FIXTURES) == 15, f"expected 15 fixtures, got {len(ALL_FIXTURES)}"


def test_fixture_preset_coverage():
    """V1~V5 5종 preset 모두 cover."""
    presets = set()
    for fp in ALL_FIXTURES:
        data = json.loads(fp.read_text(encoding="utf-8"))
        presets.add(data["preset_id"])
    assert len(presets) >= 4, f"expected ≥4 presets covered, got {presets}"
    # V1~V5 prefix 매칭
    prefixes = {p.split("_")[0] for p in presets}
    assert prefixes >= {"V1", "V2", "V3", "V4", "V5"}, f"missing preset prefixes: {prefixes}"


def test_fixture_tier_coverage():
    """Tier 1·2·3 모두 cover."""
    tiers = set()
    for fp in ALL_FIXTURES:
        data = json.loads(fp.read_text(encoding="utf-8"))
        tiers.add(data["tier"])
    assert tiers == {1, 2, 3}, f"missing tiers: {tiers}"


def test_fixture_trigger_case_coverage():
    """분기 케이스 I1/I2/I4 + low_conf cover."""
    triggers = set()
    for fp in ALL_FIXTURES:
        data = json.loads(fp.read_text(encoding="utf-8"))
        if data.get("trigger_case"):
            triggers.add(data["trigger_case"])
    assert "I1" in triggers
    assert "I2" in triggers
    assert "I4" in triggers
```

**기대 회귀 추가**: 약 15 × 2 (input/output) + 4 (coverage) = **~34건**. Slice 4·5 패턴 (1 fixture × 2~3 회귀)와 일관.

---

## §4. Rubric §C 룰 명문화 (#26 부채 처리)

### 4.1 manual_eval_rubric.md §C 갱신

기존 §C ("안전 평가 회피 (분포 사용)") 마지막에 룰 추가:

```markdown
## C. 안전 평가 회피 (분포 사용)

[기존 내용 유지]

### C.6 분포 폭 KPI 자동 게이트 (Slice 7 Part 2 신설, #26 부채 처리)

평가 종료 후 score 스크립트가 자동 측정·보고:

- **분포 폭 (max - min) ≥ 3.0** → PASS
- **5점 비율 5~20%** → PASS
- **1점 사용 1건 이상** → PASS (전 범위 활용 신호)

**미달 시 권장 조치**:

- 분포 폭 < 2.0: rubric 미숙지 의심 → 재평가 권장
- 분포 폭 2.0~2.9: 분포 좁음 경고 → 다음 평가에서 양극단 적극 사용

> 이 룰은 강제가 아닌 권장이지만, score 스크립트 출력에 KPI 결과를
> 항상 명시적으로 보고하여 평가자 자기 점검을 돕는다.
> Slice 7 E4 매트릭스 평가에서 자연 검증되며, ≥ 3.0 달성 시 #26 close.
```

### 4.2 score 스크립트 출력 형식 갱신

기존 `scripts/slice7/remeasure_h3_with_rubric.py` (Part 1 산출물)에 분포 폭 KPI 출력을 명시적으로 추가. 또는 별도 헬퍼 모듈로 분리:

`portfolio/coach/eval_metrics.py` (신규):

```python
"""Manual eval 분포 폭 KPI 계산 (rubric §C.6 자동 게이트)."""

from collections import Counter


def distribution_width_kpi(scores: list[float]) -> dict:
    """1~5 평점 리스트 입력 → KPI 측정 결과 반환."""
    if not scores:
        return {"width": 0, "five_ratio": 0.0, "one_count": 0, "pass": False}
    ints = [int(round(s)) for s in scores]
    width = max(ints) - min(ints)
    five_ratio = ints.count(5) / len(ints)
    one_count = ints.count(1)
    pass_flag = (width >= 3) and (0.05 <= five_ratio <= 0.20) and (one_count >= 1)
    return {
        "width": width,
        "five_ratio": round(five_ratio, 3),
        "one_count": one_count,
        "pass": pass_flag,
        "distribution": dict(Counter(ints)),
    }
```

회귀 테스트 `tests/portfolio/coach/test_eval_metrics.py` 추가 (~5건).

---

## §5. #β2 Estimator 외삽 정밀도 검증

### 5.1 스크립트 신설: `scripts/slice7/verify_estimator_e4.py`

```python
"""
#β2 재오픈 검증 (Slice 7 Part 2):
E4 mock fixture 15 cases input 길이를 estimator로 추정 vs 실측 비교.

목표 KPI: 정확도 ±30% 이내 (S6 e3_portfolio +366% 편차 대비 개선)
- 통과 시 #β2 close 가능
- 미통과 시 Slice 8 Step 0 후보 유지
"""

import json
from pathlib import Path

from portfolio.coach.estimators import estimate_input_tokens

FIXTURE_DIR = Path("tests/fixtures/portfolio/e4_conversation")
OUT_PATH = Path("docs/portfolio/coach/slice7/step5_estimator_verification.json")
REPORT_PATH = Path("docs/portfolio/coach/slice7/step5_estimator_verification.md")


def main():
    results = []
    for fp in sorted(FIXTURE_DIR.glob("S*.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        # E4 input의 prompt 합성 시뮬레이션 (간단 추정)
        inp = data["input"]
        text_blob = (
            inp["holdings_summary"]
            + str(inp["portfolio_metrics"])
            + "".join(t.get("content", "") for t in inp["conversation_history"])
            + inp["current_user_question"]
        )
        actual_chars = len(text_blob)
        estimated = estimate_input_tokens(text_blob)
        # token = chars / 3 approx (S5 #β1 close 기준)
        actual_tokens_approx = actual_chars // 3
        delta_pct = (
            (estimated - actual_tokens_approx) / actual_tokens_approx * 100
            if actual_tokens_approx
            else 0
        )
        results.append({
            "scenario_id": data["scenario_id"],
            "tier": data["tier"],
            "actual_chars": actual_chars,
            "actual_tokens_approx": actual_tokens_approx,
            "estimated_tokens": estimated,
            "delta_pct": round(delta_pct, 2),
        })

    # KPI 판정
    deltas = [abs(r["delta_pct"]) for r in results]
    max_delta = max(deltas)
    avg_delta = sum(deltas) / len(deltas)
    kpi_pass = max_delta <= 30.0

    summary = {
        "results": results,
        "max_delta_pct_abs": round(max_delta, 2),
        "avg_delta_pct_abs": round(avg_delta, 2),
        "kpi_threshold_pct": 30.0,
        "kpi_pass": kpi_pass,
        "beta2_action": "close" if kpi_pass else "keep_open",
    }
    OUT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Slice 7 Part 2 Step 5 — Estimator 외삽 정밀도 검증 (#β2)\n",
        f"## KPI: 정확도 ±30% 이내 → {'**PASS** ✓' if kpi_pass else '**FAIL** ✗'}\n",
        f"- max delta: {max_delta:.2f}%",
        f"- avg delta: {avg_delta:.2f}%",
        f"- #β2 처리: **{summary['beta2_action']}**\n",
        "## 상세 (15 cases)\n",
        "| scenario | tier | chars | tokens_approx | estimated | delta% |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        md.append(
            f"| {r['scenario_id']} | {r['tier']} | {r['actual_chars']} | "
            f"{r['actual_tokens_approx']} | {r['estimated_tokens']} | {r['delta_pct']:+.2f}% |"
        )
    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"✓ verification: {OUT_PATH}")
    print(f"  max delta: {max_delta:.2f}% / avg: {avg_delta:.2f}%")
    print(f"  KPI: {'PASS' if kpi_pass else 'FAIL'} → #β2 {summary['beta2_action']}")


if __name__ == "__main__":
    main()
```

### 5.2 실행

```bash
python scripts/slice7/verify_estimator_e4.py
```

### 5.3 분기

- **KPI PASS (max delta ≤ 30%)**: #β2 close → Slice 8 Step 0 후보에서 제외
- **KPI FAIL (max delta > 30%)**: #β2 keep_open → Slice 8 Step 0 후보 유지

---

## §6. 회귀 영향 KPI

| 단계                              | 회귀 영향       | 비용 | 부채 변화                               |
| --------------------------------- | --------------- | ---- | --------------------------------------- |
| §1 (E4 schema 구현 + 테스트)      | +15건           | $0   | 0                                       |
| §2 (token_budgets 갱신)           | 0               | $0   | 0                                       |
| §3 (mock fixture 15 + round-trip) | +34건           | $0   | 0                                       |
| §4 (rubric §C.6 + eval_metrics)   | +5건            | $0   | 0 (#26는 Slice 7 E4 평가 후 close 후보) |
| §5 (#β2 estimator 검증)           | 0 (script only) | $0   | -1 (KPI PASS) 또는 0 (FAIL)             |

**총 회귀 추가 예상**: **+54건** (395 → 449)

**IDENTICAL hash KPI**: Slice 1 e1 + Slice 3 e2 유지 확인 필수 (E4 추가가 기존 진입점에 영향 없어야 함).

---

## §7. 완료 보고 양식

```
[Slice 7 Part 2 완료 보고]

== §1 (E4 schema 구현) ==
- portfolio/coach/schemas/e4_conversation.py: ✓ (3 schema + 1 metadata)
- 회귀 추가: 15 PASS ✓
- DIMENSION_LOOKUP entry 추가: ✓

== §2 (token_budgets 갱신) ==
- BUDGETS[e4_conversation_tier1/2/3] = 6000/8000/12000: ✓
- budget rationale docs: ✓

== §3 (mock fixture 15 cases) ==
- fixture 파일 15건 생성: ✓
- preset coverage V1~V5: ✓
- tier coverage 1/2/3: ✓
- trigger coverage I1/I2/I4: ✓
- round-trip 회귀: 34 PASS ✓

== §4 (rubric §C.6 + eval_metrics) ==
- manual_eval_rubric.md §C.6 갱신: ✓
- portfolio/coach/eval_metrics.py 신설: ✓
- distribution_width_kpi 회귀: 5 PASS ✓

== §5 (#β2 estimator 검증) ==
- 15 cases 추정 vs 실측 비교: ✓
- max delta: ???%
- KPI ±30%: ??? (PASS / FAIL)
- #β2 처리: close / keep_open

== 종합 ==
- 회귀: 395 → ??? (목표 449, ±5건 허용)
- 비용: $0 (LLM 호출 0)
- 누적 광의: $0.879 (변화 없음, 임계 $1.50 마진 41%)
- IDENTICAL hash: Slice 1 e1 ✓ / Slice 3 e2 ✓
- #β2 처리: close 또는 keep_open (verdict에 따라)

§I. 산출물 (~10건)
§II. #β2 KPI 결과 (delta + 분기)
§III. Slice 7 Part 3 진입 준비도
§IV. Commit 메시지 권장
§V. 핵심 결과
```

---

## §8. 분기 시나리오 (Part 2 안에서)

| 시나리오 | 트리거                                                 | 조치                                           |
| -------- | ------------------------------------------------------ | ---------------------------------------------- |
| **K1**   | 회귀 추가 +54 ±5 벗어남 (449 미달 또는 460 초과)       | 누락 fixture 또는 중복 회귀 점검, 재집계       |
| **K2**   | IDENTICAL hash 깨짐 (Slice 1 e1 또는 Slice 3 e2 변화)  | 즉시 보고, 회귀 환경 변경 의심                 |
| **K3**   | #β2 KPI FAIL (delta > 30%)                             | #β2 keep_open, Slice 8 Step 0 후보 유지        |
| **K4**   | fixture preset coverage 미달 (V1~V5 중 누락)           | 누락 preset fixture 추가                       |
| **K5**   | Tier 2/3 history 길이가 max_history_turns(5) 자주 초과 | I1 분기 빈도 ↑ 우려 → token budget 재산정 검토 |

---

## §9. Commit 메시지 권장

```
feat(slice7/part2/step1): E4 conversation schema (Pydantic + Tier 1~3)
test(slice7/part2/step1): E4 schema 회귀 +15
feat(slice7/part2/step2): token_budgets e4_conversation tier1/2/3 추가
test(slice7/part2/step3): E4 mock fixture 15 cases + round-trip 회귀 +34
docs(slice7/part2/step4): rubric §C.6 분포 폭 KPI 자동 게이트 (#26 처리)
feat(slice7/part2/step4): eval_metrics.distribution_width_kpi
feat(slice7/part2/step5): estimator 외삽 정밀도 검증 스크립트 (#β2 검증)
docs(slice7/part2/step5): #β2 verdict 보고
```

---

## §10. Part 2 종결 KPI (완료 기준)

- [ ] E4 schema 구현 완료 (3 schema + metadata)
- [ ] 회귀 추가 +54 ±5 (목표 회귀 449)
- [ ] mock fixture 15 cases 모두 round-trip PASS
- [ ] preset V1~V5 + Tier 1/2/3 + I1/I2/I4 trigger coverage
- [ ] rubric §C.6 갱신 + eval_metrics 신설
- [ ] #β2 estimator 검증 + verdict 확정
- [ ] IDENTICAL hash KPI 유지 (Slice 1 e1 + Slice 3 e2)
- [ ] 누적 비용 $0.879 유지
- [ ] commit 7~8건 완료

---

## §11. Part 3 진입 사전 등록

Part 2 종결 후 Part 3 작업 범위:

- E4 prompt builder 구현 (`portfolio/coach/prompts/e4_conversation_prompt.py`)
- DIMENSION_LOOKUP `prompt_builder` slot 채움
- Step 6 smoke test (V1 Tier 1 × haiku × 1 call, ~$0.005)
- Step 7 matrix 매트릭스 (15 cases × haiku/sonnet × Tier 1~3)
  - 비용 추정: $0.32~0.42 (Part 1 §2.1 산정 기반)
- Step 7.5 KPI 자동 검증 (8 + 보조)
- Step 8 raw + scored dump 준비
- 회귀 변화 없음 예상 (prompt builder만)
