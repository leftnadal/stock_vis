"""
E3 (지표별 한 줄 코멘트) 지시문.

Version: 1.1 (2026-04-24)
"""

E3_INSTRUCTIONS = """# Task: Generate Per-Metric Commentary (E3)

For each metric in the input, generate a concise 1~2 sentence Korean
commentary. Keep the output ordering identical to the input ordering.

## Output

Return valid JSON matching this schema (no markdown fences, no surrounding text):

{
  "comments": [
    {"metric_id": "...", "one_liner": "<1~2 Korean sentences>"},
    ...
  ]
}

## Content Guidelines per Comment

Each one_liner should:
1. State the OBSERVATION first (value, percentile, pass/fail status).
2. If room remains, add a CONCISE interpretation tied to the preset.

Structure patterns:
- "[값/등급 팩트]. [프리셋 맥락 해석]."
- "[종목별 분포 특징]. [주목할 점 혹은 예외]."

Length:
- 1 sentence if the metric is clearly pass or clearly fail.
- 2 sentences if there's notable nuance (mixed within portfolio, outlier,
  threshold borderline, etc.).

Style:
- Conditional language for interpretation ("-수 있습니다", "-로 읽힙니다").
- Reference the preset's tier (Core / Supporting) briefly when it clarifies
  importance ("Core 지표로서…", "보조 지표이지만…").
- AVOID: "추천합니다", "사야/팔아야", imperative forms.
- PREFER: "주목할 만합니다", "[프리셋] 관점에서는 ___한 의미입니다".

## Rules

- Generate EXACTLY one comment per input metric. No more, no fewer.
- Keep the order identical to the `metrics` array in the input.
- Context-tier metrics are NOT in the input. Do not invent them.
- Do not add sentences beyond 2.
- Do not reference wallet-level information. E3 is a metric-focused view.
"""
