# D-7 Instructions: E6 Post-Adjustment Comparison Prompt

> **세션**: D-7
> **목적**: LLM 진입점 E6 (조정된 분석 재실행 후, 원본 대비 변화 해설) 프롬프트 작성
> **전제 세션**: D-6 완료
> **대상 에이전트**: Claude Code
> **버전**: v1.0 (2026-04-20)

---

## 0. 에이전트가 먼저 읽을 것

**필수 참조**:
1. `docs/portfolio/design/coach-llm-design-v1.md` — §3-6 E6 상세
2. `docs/portfolio/implementation/schemas/llm_outputs.py` — `AdjustmentComparison`
3. `docs/portfolio/implementation/schemas/analysis_context.py` — `AnalysisContext`

---

## 1. 목표

조정이 적용되어 재실행된 AnalysisRun의 결과를, **원본 AnalysisRun과 비교해 해설**.

### 1-1. 진입점 특성

| 항목 | E6의 특징 |
|---|---|
| 트리거 | 조정된 AnalysisRun 완료 |
| 입력 | 원본 AnalysisContext + 조정된 AnalysisContext + 적용된 overrides |
| 출력 | `AdjustmentComparison` (key_changes + summary + implication_for_user) |
| Wallet 주입 | **최소** (total_holdings_count 정도) |
| Tier 1~3 | 불필요 |

### 1-2. 산출물

```
implementation/prompts/e6/
├── __init__.py
├── instructions.py
├── examples.py           (조정 유형별 비교 예시 2~3개)
├── input_builder.py      (두 AnalysisContext를 diff로 요약)
└── e6_builder.py
```

---

## 2. 사전 조건

- [x] D-6 완료

---

## 3. 단계별 작업 명세

### Step 1: `instructions.py`

**참고 템플릿**:
```python
E6_INSTRUCTIONS = """
# Task: Post-Adjustment Comparison (E6)

The user applied an adjustment and the analysis was re-run. Compare the
ORIGINAL analysis to the ADJUSTED analysis and explain what changed.

## Output
Return valid JSON:
{
  "key_changes": [
    "<Change point 1>",
    "<Change point 2>",
    ...  // 3-5 items
  ],
  "summary": "<Overall interpretation of what the adjustment revealed, 2-3 sentences>",
  "implication_for_user": "<Optional forward-looking suggestion, 1-2 sentences>"
}

## Content Guidelines

### key_changes (3-5 items)
Focus on what SHIFTED:
- Strength/weakness composition changes ("Buffett 기준 강점이 ROIC 중심에서 ROIC + 성장 중심으로")
- Specific stocks newly appearing/disappearing in strengths or weaknesses
- Level tag transitions ("INTC ROIC level_tag: weak → critical")
- Diagnostic card severity changes
- Return breakdown shifts (if applicable)

NOT key changes (skip these):
- Trivial numeric differences (0.12 → 0.13)
- Changes in Context-tier metrics (usually too minor to mention)

### summary (2-3 sentences)
- What did the adjustment reveal about the portfolio?
- Did it align with or differ from the user's intent?
- Does the adjusted view suggest the portfolio "fits" a different preset or sub-angle?

Example:
"ROIC 기준을 올리고 성장을 중시하자, 퀄리티 + 성장 복합 종목(LLY, MSFT)이
부각됩니다. 현재 포트폴리오는 Buffett보다 Quality Growth 프리셋에 더
가까울 수 있습니다."

### implication_for_user (1-2 sentences, OPTIONAL)
A gentle forward suggestion:
- "다른 프리셋으로 분석해보기" 유도
- "이 조정이 일회성이 아니라면 Phase 2의 영구 조정 기능이 출시될 때까지
   같은 조정을 매번 적용하실 수 있습니다"
- Leave blank ("") if no meaningful suggestion.

## Rules
- Reference SPECIFIC metrics and holdings by name
- Use before/after framing: "A → B", "before: ..., after: ..."
- Preserve preset lens (don't suggest switching mid-analysis)
- No buy/sell recommendations
- Korean, honorific form
"""
```

### Step 2: `examples.py`

**예시 1** — threshold_change after effects:
```python
EXAMPLE_1 = {
    "scenario": "ROIC 임계값 15→20% 상향 후",
    "input": {
        "original_context_summary": {
            "preset_id": "buffett_quality_value",
            "strengths": ["ROIC (excellent, 5종목 중 4)", "earnings_consistency_5y (good)"],
            "weaknesses": ["pe_ratio (moderate)", "debt_to_equity (weak, 1종목)"],
        },
        "adjusted_context_summary": {
            "strengths": ["ROIC (excellent, 5종목 중 3)", "earnings_consistency_5y (good)", "revenue_growth_yoy (good)"],
            "weaknesses": ["pe_ratio (moderate)", "debt_to_equity (weak, 1종목)", "ROIC (weak, INTC만)"],
        },
        "applied_overrides": [
            {
                "intent_type": "threshold_change",
                "overrides": {"metric_id": "roic", "old_threshold": 0.15, "new_threshold": 0.20}
            }
        ]
    },
    "expected_output": {
        "key_changes": [
            "ROIC 통과 종목이 4개에서 3개로 감소. INTC가 새로 ROIC 약점에 편입",
            "revenue_growth_yoy가 새롭게 강점으로 부각 (평가 비중 상승으로)",
            "약점 카드 구성이 '밸류에이션 부담' + '재무 건전성'에서 '밸류에이션 부담' + '재무 건전성' + 'ROIC 구조적 약점'으로 확장",
            "INTC의 level_tag: moderate → weak로 전환"
        ],
        "summary": "ROIC 기준을 상향하자 INTC의 취약성이 구조적으로 드러났습니다. 동시에 성장 지표가 강점으로 부각되어, 현재 구성이 순수 Buffett보다는 Quality Growth 관점에 더 잘 맞을 수 있음을 시사합니다.",
        "implication_for_user": "Quality Growth 프리셋으로도 한 번 분석해보시면 다른 관점의 강점이 드러날 수 있습니다."
    }
}
```

**예시 2** — exclude_stock after effects:
```python
EXAMPLE_2 = {
    "scenario": "NVDA를 PEG 평가에서 제외",
    "input": {
        "original": {"avg_peg": 2.8, "peg_weakness": "critical"},
        "adjusted": {"avg_peg": 2.4, "peg_weakness": "weak"},
        "applied_overrides": [{"intent_type": "exclude_stock", "overrides": {...}}]
    },
    "expected_output": {
        "key_changes": [
            "평균 PEG가 2.8 → 2.4로 감소 (NVDA 제외 효과)",
            "PEG 약점의 severity가 critical → weak로 완화",
            "진단 카드 #1의 structural_or_single: structural → 여전히 structural 유지 (나머지 4종목이 모두 2.0+)"
        ],
        "summary": "NVDA 제외는 평균 수치 개선에 기여했으나, 나머지 4종목도 모두 PEG 2.0 이상이라 구조적 밸류에이션 부담은 여전합니다.",
        "implication_for_user": "NVDA 제외로 '특정 종목 신뢰'라는 의도는 반영되었지만, 포트폴리오 전반의 성장 대비 가격 부담은 남아있음을 염두에 두시면 좋겠습니다."
    }
}
```

**예시 3** (선택) — change_comparison_group:
비교 기준을 섹터 → 유니버스로 바꾸면 percentile이 어떻게 달라졌는지.

### Step 3: `input_builder.py`

```python
def build_e6_input(
    original_context: AnalysisContext,
    adjusted_context: AnalysisContext,
    applied_overrides: list[dict],
) -> dict:
    """
    두 AnalysisContext를 받아서 비교에 필요한 diff 요약 생성.
    """
    op = original_context.analysis_target_portfolio
    ap = adjusted_context.analysis_target_portfolio

    return {
        "preset_id": op.preset_id,
        "preset_name": op.preset_name,
        "original_summary": {
            "strengths": [
                {
                    "metric_id": s.metric_id,
                    "level_tag": s.level_tag,
                    "reason_hint": s.reason_hint,
                }
                for s in op.strengths
            ],
            "weaknesses": [
                {
                    "metric_id": w.metric_id,
                    "level_tag": w.level_tag,
                    "reason_hint": w.reason_hint,
                }
                for w in op.weaknesses
            ],
            "diagnostic_cards": [
                {
                    "weakness_metric_id": c.weakness_metric_id,
                    "severity": c.severity.value,
                    "structural_or_single": c.structural_or_single.value,
                }
                for c in op.diagnostic_cards
            ],
            "total_return": float(op.return_breakdown.current.total_return),
        },
        "adjusted_summary": {
            # 같은 구조를 adjusted로
            "strengths": [ ... ],
            "weaknesses": [ ... ],
            "diagnostic_cards": [ ... ],
            "total_return": float(ap.return_breakdown.current.total_return),
        },
        "applied_overrides": applied_overrides,  # E5에서 생성된 것 그대로
    }
```

### Step 4: `e6_builder.py`

```python
def build_e6_prompt(
    original_context: AnalysisContext,
    adjusted_context: AnalysisContext,
    applied_overrides: list[dict],
    prompt_version: str = "1.1",
) -> tuple[str, str]:
    system_prompt = build_tier0(prompt_version=prompt_version)

    parts = [E6_INSTRUCTIONS]
    parts.append("## Examples\n")
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        parts.append(f"### Example {i}: {ex['scenario']}")
        parts.append(f"Input: {json.dumps(ex['input'], ensure_ascii=False)}")
        parts.append(f"Output: {json.dumps(ex['expected_output'], ensure_ascii=False)}")

    input_data = build_e6_input(original_context, adjusted_context, applied_overrides)
    parts.append("## Compare these two analyses:\n")
    parts.append(f"Input:\n{json.dumps(input_data, ensure_ascii=False, indent=2, default=str)}\n")
    parts.append("Output:\n")

    return system_prompt, "\n".join(parts)
```

### Step 5: `__init__.py`

---

## 4. 검증 지점

### 4-1. key_changes 품질 기준

각 예시에서 key_changes는 3~5개 항목, 각 항목은 before/after 구조 포함.

### 4-2. summary 흐름

summary는 "조정의 효과 + 의미" 흐름. 단순 나열 금지.

### 4-3. implication 조건부

implication_for_user는 비어있어도 OK (모든 상황에 forward suggestion이 자연스럽지 않음).

### 4-4. 토큰 예산

E6는 두 AnalysisContext 요약을 함께 보내므로 **4,500~6,500 토큰**.

---

## 5. 에이전트 판단 허용 범위

### 5-1. 허용
- 예시 시나리오 선택
- diff 요약 구조 세부
- implication 포함 여부

### 5-2. 금지
- 프리셋 전환 직접 추천 ("GARP 쓰세요" 금지. "GARP으로도 보시면 도움될 수 있습니다"는 OK)
- key_changes가 2개 미만 or 6개 초과

---

## 6. 산출물

**신규 파일 (5개)**: `prompts/e6/*`

---

## 7. 완료 보고 포맷

```markdown
# D-7 완료 보고

## 생성 파일
- prompts/e6/*

## 검증
- [✓] key_changes 3-5 items
- [✓] summary quality
- [✓] before/after framing

## 다음 세션 준비
- D-8: 전체 end-to-end 시나리오 테스트 + 통합 검증
```

---

## 8. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| v1.0 | 2026-04-20 | 초판 |
