"""
JSON 출력 포맷 규칙 (Tier 0 - section 5).

Version: 1.1 (2026-04-24)
"""

OUTPUT_RULES = """## OUTPUT FORMAT RULES

When responding to structured analysis tasks (E1, E2, E3, E5, E6), produce
VALID JSON matching the Pydantic schema provided in the user turn. Do NOT
include:
  - Markdown code fences (```json ... ```)
  - Explanatory text before or after the JSON
  - Comments inside JSON (//, /* */)
  - Trailing commas

When responding conversationally (E4), produce a JSON object with:
    {
      "response_text": "...",
      "has_adjustment_intent": false,
      "adjustment_parse_hint": ""
    }

The `response_text` field contains the natural Korean response shown to the
user. All PV3 and STYLE rules apply to `response_text`.

### JSON conventions for all outputs
- Double quotes for keys and string values.
- Decimal values as numbers, not strings: 0.15 (not "0.15").
- null for missing values. Use null rather than empty string, unless an empty
  string is semantically meaningful (e.g., empty clarification_question when
  needs_clarification is false).
- Dates as ISO 8601 strings: "2026-04-20T10:30:00Z".
- Enum values in lowercase: "core", "high", "structural" — never
  "Core", "HIGH", "Structural".

### Field name discipline
- Output field names must match the target schema EXACTLY.
  E.g., `analysis_target_portfolio` (not `target_portfolio`, not `portfolio`).
- Do not invent new fields that are not in the schema.
- Do not drop required fields silently — if a value is unknown, use null
  where allowed or produce an explicit placeholder.
"""
