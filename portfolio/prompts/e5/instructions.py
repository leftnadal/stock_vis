"""
E5 (조정 파싱) 지시문.

Version: 1.1 (2026-04-24)
"""

E5_INSTRUCTIONS = """# Task: Parse Adjustment Request (E5)

Parse the user's natural language request (from E4's `adjustment_parse_hint`)
into a list of structured `AdjustmentOverride` items.

## Output

Return valid JSON (no markdown fences):

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
  "clarification_question": "<Korean question to user, empty if not needed>"
}

## Intent Types and Override Structures

### threshold_change
User wants to change a numeric threshold for a metric.
overrides:
{
  "metric_id": "<exact metric_id from available_metrics>",
  "old_threshold": <number or null if unknown>,
  "new_threshold": <number>
}
Example description: "ROIC 임계값을 15%에서 20%로 상향"

### tier_change
User wants to move a metric between tiers.
overrides:
{
  "metric_id": "<exact metric_id>",
  "from_tier": "core" | "supporting" | "context",
  "to_tier":   "core" | "supporting" | "context"
}
Example description: "매출 성장률을 Context에서 Supporting으로 승격"

### exclude_stock
User wants to exclude a specific holding from a specific metric's evaluation
(or from the whole analysis).
overrides:
{
  "stock_symbol": "<ticker, uppercase>",
  "exclude_from_metric": "<metric_id>" | "all"
}
Example description: "NVDA를 PEG 평가에서 제외 (이번 분석 한정)"

### change_comparison_group
User wants to change the percentile / comparison base.
overrides:
{
  "from_scope": "industry" | "sector" | "universe",
  "to_scope":   "industry" | "sector" | "universe",
  "affects_metric_id": "<metric_id>" | "all"
}
Example description: "비교 기준을 GICS 섹터에서 S&P 500 유니버스로 변경"

### unknown
Use when you cannot confidently parse the intent. In this case set
`needs_clarification = true` and produce a specific `clarification_question`.

## Confidence Scoring

- 0.9~1.0: Unambiguous parse with clear target and value.
- 0.7~0.9: Clear intent but some assumption (e.g., you inferred the metric_id
  from context words).
- 0.4~0.7: Ambiguous. Consider setting `needs_clarification=true`.
- < 0.4:   Set `needs_clarification=true` and use `intent_type="unknown"`.

If ANY detected override has confidence < 0.7, prefer clarification.

## Clarification Question Patterns

When `needs_clarification=true`:
- Be SPECIFIC. Offer 2~3 concrete options if possible.
  Good: "ROIC 임계값을 20%로 올리시려는 건가요, 아니면 20% 이상만 통과시키시려는 건가요?"
  Bad (too vague): "더 자세히 설명해주세요."

## Strict Rules

- Use EXACT `metric_id` values from the provided `available_metrics` list.
  If the user names a metric in Korean (e.g., "배당성향"), map it to the
  corresponding `metric_id` based on `metric_display_name`.
- Use EXACT tier values: "core", "supporting", "context" (lowercase).
- Use EXACT scope values: "universe", "sector", "industry" (lowercase).
- Stock symbols in uppercase (e.g., "NVDA", not "nvda").
- Never invent `metric_id` values not in the input list.
- Multiple adjustments in one message → multiple items in
  `detected_overrides`.
- `description_for_user` must be concise Korean suitable for a UI
  confirmation card.
"""
