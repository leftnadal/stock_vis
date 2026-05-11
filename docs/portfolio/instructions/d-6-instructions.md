# D-6 Instructions: E5 Adjustment Parsing Prompt

> **세션**: D-6
> **목적**: LLM 진입점 E5 (자연어 조정 요청 → 구조화 overrides JSON) 프롬프트 작성
> **전제 세션**: D-5 완료
> **대상 에이전트**: Claude Code
> **버전**: v1.0 (2026-04-20)

---

## 0. 에이전트가 먼저 읽을 것

**필수 참조**:
1. `docs/portfolio/design/coach-llm-design-v1.md` — §3-5 E5 상세, §5-2 조정 범위
2. `docs/portfolio/implementation/schemas/llm_outputs.py` — `AdjustmentIntent`, `AdjustmentOverride`, `AdjustmentIntentType`
3. `docs/portfolio/design/preset-design-v3.1.md` — 프리셋 정의 구조 (threshold, tier 등)
4. `docs/portfolio/implementation/metrics/definitions/preset_metrics.py` — 실제 프리셋-지표 매핑

---

## 1. 목표

E5는 E4의 `adjustment_parse_hint`를 받아 **구조화된 overrides JSON**으로 변환.

### 1-1. 진입점 특성

| 항목 | E5의 특징 |
|---|---|
| 트리거 | E4에서 `has_adjustment_intent=true` 반환 시 |
| 입력 | 사용자 원메시지 + 현재 프리셋 정의 + 지표 사전 |
| 출력 | `AdjustmentIntent` (detected_overrides 리스트 or clarification 요청) |
| Tier 0 | 포함 |
| Tier 1~3 | **불필요** (순수 파싱 작업) |
| Wallet 정보 | **불필요** (PV5 스타일) |

### 1-2. 4가지 조정 유형 (결정 확인3)

1. `threshold_change` — "ROIC 20%로"
2. `tier_change` — "성장 지표를 Supporting으로"
3. `exclude_stock` — "NVDA는 PEG 평가에서 빼줘"
4. `change_comparison_group` — "섹터 대신 유니버스로"

### 1-3. 산출물

```
implementation/prompts/e5/
├── __init__.py
├── instructions.py
├── examples.py              (각 조정 유형별 예시 1개씩 = 4개)
├── input_builder.py         (프리셋 정의 + 지표 목록)
└── e5_builder.py
```

---

## 2. 사전 조건

- [x] D-5 완료

---

## 3. 단계별 작업 명세

### Step 1: `instructions.py`

**핵심 원칙**:
- 자연어 → 명확한 구조화 JSON
- 불확실한 경우 `needs_clarification=true` 반환
- 여러 조정이 한 요청에 있으면 배열로 반환

**참고 템플릿**:
```python
E5_INSTRUCTIONS = """
# Task: Parse Adjustment Request (E5)

Parse the user's natural language request into structured overrides.

## Output
Return valid JSON:
{
  "detected_overrides": [
    {
      "intent_type": "threshold_change" | "tier_change" | "exclude_stock" | "change_comparison_group" | "unknown",
      "description_for_user": "<Korean, for UI confirmation card>",
      "overrides": { ... intent-specific fields ... },
      "confidence": <0.0 to 1.0>
    },
    ...
  ],
  "needs_clarification": <true|false>,
  "clarification_question": "<Korean question to user, if clarification needed>"
}

## Intent Types and Override Structures

### threshold_change
User wants to change a numeric threshold for a metric.
overrides: {
  "metric_id": "<exact metric_id from the provided list>",
  "old_threshold": <number or null if unknown>,
  "new_threshold": <number>
}
description_for_user example: "ROIC 임계값을 15%에서 20%로 상향"

### tier_change
User wants to move a metric between tiers (core/supporting/context).
overrides: {
  "metric_id": "<exact metric_id>",
  "from_tier": "core" | "supporting" | "context",
  "to_tier": "core" | "supporting" | "context"
}
description_for_user example: "매출 성장률을 Context에서 Supporting으로 승격"

### exclude_stock
User wants to exclude a specific holding from a specific metric's evaluation.
overrides: {
  "stock_symbol": "<ticker, e.g. NVDA>",
  "exclude_from_metric": "<metric_id>" | "all"  // "all" if excluding from entire analysis
}
description_for_user example: "NVDA를 PEG 평가에서 제외 (이번 분석 한정)"

### change_comparison_group
User wants to change the percentile/comparison base.
overrides: {
  "from_scope": "industry" | "sector" | "universe",
  "to_scope": "industry" | "sector" | "universe",
  "affects_metric_id": "<metric_id>" | "all"
}
description_for_user example: "비교 기준을 GICS 산업에서 S&P 500 유니버스로 변경"

### unknown
Use when you cannot confidently parse. In this case set needs_clarification=true
and provide a specific question.

## Confidence Scoring

- 0.9-1.0: Unambiguous parse with clear target and value
- 0.7-0.9: Clear but some assumption made (use metric_id context)
- 0.4-0.7: Ambiguous; consider clarification
- < 0.4: Set needs_clarification=true

If any confidence < 0.7, consider asking for clarification.

## Clarification Question Patterns

When needs_clarification=true:
- Specific: "ROIC 임계값을 20%로 올리시려는 건가요, 아니면 20% 이상만 통과시키시려는 건가요?"
- NOT generic: "더 자세히 설명해주세요" (too vague)

## Rules
- Use EXACT metric_ids from the provided "available_metrics" list
- Use EXACT tier values: "core", "supporting", "context"
- Use EXACT scope values: "universe", "sector", "industry"
- DO NOT invent metric_ids
- Multiple overrides in one message → multiple items in detected_overrides
- description_for_user should be in Korean, user-friendly
"""
```

### Step 2: `examples.py` — Few-shot 4개 (각 intent_type 1개씩)

**예시 1** — threshold_change:
```python
EXAMPLE_1 = {
    "scenario": "ROIC 임계값 상향",
    "user_hint": "ROIC 임계값을 20%로 상향",
    "current_preset_summary": {
        "preset_id": "buffett_quality_value",
        "metrics_with_thresholds": [
            {"metric_id": "roic", "current_threshold": 0.15, "tier": "core"},
            {"metric_id": "roe", "current_threshold": 0.10, "tier": "core"},
        ]
    },
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "threshold_change",
                "description_for_user": "ROIC 임계값을 15%에서 20%로 상향",
                "overrides": {
                    "metric_id": "roic",
                    "old_threshold": 0.15,
                    "new_threshold": 0.20
                },
                "confidence": 0.95
            }
        ],
        "needs_clarification": False,
        "clarification_question": ""
    }
}
```

**예시 2** — tier_change:
```python
EXAMPLE_2 = {
    "scenario": "성장 지표 tier 상향",
    "user_hint": "revenue_growth_yoy와 eps_growth_yoy를 Context에서 Supporting으로 승격",
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "tier_change",
                "description_for_user": "매출 성장률(revenue_growth_yoy)을 Context에서 Supporting으로 승격",
                "overrides": {
                    "metric_id": "revenue_growth_yoy",
                    "from_tier": "context",
                    "to_tier": "supporting"
                },
                "confidence": 0.95
            },
            {
                "intent_type": "tier_change",
                "description_for_user": "EPS 성장률(eps_growth_yoy)을 Context에서 Supporting으로 승격",
                "overrides": {
                    "metric_id": "eps_growth_yoy",
                    "from_tier": "context",
                    "to_tier": "supporting"
                },
                "confidence": 0.95
            }
        ],
        "needs_clarification": False,
        "clarification_question": ""
    }
}
```

**예시 3** — exclude_stock:
```python
EXAMPLE_3 = {
    "scenario": "NVDA를 PEG 평가에서 제외",
    "user_hint": "NVDA는 내 확신이 있어서 PEG 평가에서 빼줘",
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "exclude_stock",
                "description_for_user": "NVDA를 PEG 평가에서 제외 (이번 분석 한정)",
                "overrides": {
                    "stock_symbol": "NVDA",
                    "exclude_from_metric": "peg_ratio"
                },
                "confidence": 0.90
            }
        ],
        "needs_clarification": False,
        "clarification_question": ""
    }
}
```

**예시 4** — change_comparison_group:
```python
EXAMPLE_4 = {
    "scenario": "비교군 변경",
    "user_hint": "섹터 기준이 아니라 S&P 500 전체로 비교해줘",
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "change_comparison_group",
                "description_for_user": "비교 기준을 GICS 섹터에서 S&P 500 유니버스 전체로 변경",
                "overrides": {
                    "from_scope": "sector",
                    "to_scope": "universe",
                    "affects_metric_id": "all"
                },
                "confidence": 0.95
            }
        ],
        "needs_clarification": False,
        "clarification_question": ""
    }
}
```

**예시 5** (선택) — clarification 필요:
```python
EXAMPLE_5 = {
    "scenario": "모호한 요청",
    "user_hint": "좀 더 엄격하게 보여줘",
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "unknown",
                "description_for_user": "",
                "overrides": {},
                "confidence": 0.3
            }
        ],
        "needs_clarification": True,
        "clarification_question": "어떤 부분을 더 엄격하게 보고 싶으신가요? 예를 들어 (1) Core 지표의 임계값을 높일까요, (2) 비교 기준을 더 좁은 산업 기준으로 바꿀까요, (3) 아니면 특정 지표(ROIC, PEG 등)에 집중할까요?"
    }
}
```

### Step 3: `input_builder.py`

```python
from portfolio.metrics.definitions.presets import PRESETS
from portfolio.metrics.definitions.preset_metrics import PRESET_METRICS
from portfolio.metrics.definitions.metrics import METRICS


def build_e5_input(
    user_hint: str,
    current_preset_id: str,
) -> dict:
    """
    E5 입력: 사용자 hint + 현재 프리셋의 metric/threshold 맥락.
    """
    preset_info = PRESETS[current_preset_id]
    preset_metric_entries = PRESET_METRICS[current_preset_id]

    available_metrics = []
    for entry in preset_metric_entries:
        m = METRICS[entry["metric_id"]]
        available_metrics.append({
            "metric_id": entry["metric_id"],
            "metric_display_name": m["display_name"],
            "current_tier": entry["tier"],
            # threshold 정보는 프리셋별로 별도 저장되어 있으면 포함
            # (현 구조에 threshold가 preset_metrics에 없으면 별도 조회 필요)
        })

    return {
        "user_hint": user_hint,
        "current_preset": {
            "preset_id": current_preset_id,
            "preset_name": preset_info["display_name"],
            "preset_category": preset_info["category"],
        },
        "available_metrics": available_metrics,
    }
```

**주의**: 프리셋 threshold 정보가 `preset_metrics.py`에 아직 없으면, E5 입력에서 `current_threshold`는 null로 두고 LLM이 `old_threshold: null`로 반환하게 함. D-0a 이후 별도 설계에서 threshold 정보 구조화 필요할 수도 있음.

### Step 4: `e5_builder.py`

```python
from portfolio.prompts.tier0 import build_tier0
from .instructions import E5_INSTRUCTIONS
from .examples import FEW_SHOT_EXAMPLES
from .input_builder import build_e5_input


def build_e5_prompt(
    user_hint: str,
    current_preset_id: str,
    prompt_version: str = "1.1",
) -> tuple[str, str]:
    """
    E5는 순수 파싱이라 Tier 1~3, Wallet 없음.
    include_style=False (자연어 응답 아니라 구조화 파싱이므로).
    """
    system_prompt = build_tier0(
        prompt_version=prompt_version,
        include_style=False,  # 문체 규칙 불필요
    )

    parts = [E5_INSTRUCTIONS]

    parts.append("## Examples\n")
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        parts.append(f"### Example {i}: {ex['scenario']}")
        parts.append(f"User hint: {ex['user_hint']}")
        parts.append(f"Output: {json.dumps(ex['expected_output'], ensure_ascii=False)}")

    input_data = build_e5_input(user_hint, current_preset_id)
    parts.append("## Parse this request:\n")
    parts.append(f"Input:\n{json.dumps(input_data, ensure_ascii=False, indent=2)}\n")
    parts.append("Output:\n")

    return system_prompt, "\n".join(parts)
```

### Step 5: `__init__.py`

---

## 4. 검증 지점

### 4-1. 4가지 intent_type 예시 포함

```python
intent_types = {
    ex["expected_output"]["detected_overrides"][0]["intent_type"]
    for ex in FEW_SHOT_EXAMPLES
    if ex["expected_output"]["detected_overrides"]
}
assert intent_types >= {"threshold_change", "tier_change", "exclude_stock", "change_comparison_group"}
```

### 4-2. clarification 예시 최소 1개

(선택, 5번째 예시 있다면)

### 4-3. 토큰 예산

E5는 비교적 간결. 예상 **2,500~4,000 토큰**.

### 4-4. Tier 1~3 배제

```python
system, user = build_e5_prompt("ROIC 20%로", "buffett_quality_value")
assert "Investment style" not in system  # Tier 3 없음
assert "conversation history" not in system.lower()  # Tier 1 없음
```

---

## 5. 에이전트 판단 허용 범위

### 5-1. 허용
- 예시 시나리오 선택
- clarification 문구 세부
- confidence 숫자 기준

### 5-2. 금지
- 새 intent_type 추가 (4가지 + unknown 외)
- enum value 변경 (tier, scope 이름)
- user_hint 원문을 override에 그대로 복사 (반드시 파싱)

### 5-3. 판단 어려운 경우
- threshold 정보가 input에 없을 때 처리 방침 → 사용자 보고

---

## 6. 산출물

**신규 파일 (5개)**: `prompts/e5/*`

---

## 7. 완료 보고 포맷

```markdown
# D-6 완료 보고

## 생성 파일
- prompts/e5/*

## 4가지 intent_type 커버리지
- [✓] threshold_change
- [✓] tier_change
- [✓] exclude_stock
- [✓] change_comparison_group
- [?] unknown/clarification (선택)

## 검증
- [✓] Tier 1~3 배제
- [✓] include_style=False 옵션 사용

## 다음 세션 준비
- D-7: E6 조정 후 해설 (원본 vs 조정본 비교 해설)
```

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 |
