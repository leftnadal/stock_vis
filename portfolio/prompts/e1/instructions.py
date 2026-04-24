"""
E1 (한 줄 진단) 지시문 모듈.

Version: 1.1 (2026-04-24)
"""

E1_INSTRUCTIONS = """# Task: Generate One-Line Diagnosis (E1)

You will produce a concise diagnostic summary for the user's
`analysis_target_portfolio`, based on the analysis results provided below.

## Output

Return valid JSON matching this schema (no markdown fences, no surrounding text):

{
  "headline": "<25-40 character Korean diagnostic headline>",
  "summary": "<2-3 sentence Korean summary>"
}

## Content Guidelines

### headline (한 줄 진단)
- 25~40 Korean characters. Count carefully.
- Capture the PRIMARY tension or feature of the portfolio through the active
  preset's lens (preset_id / preset_name).
- When a strength/weakness trade-off exists, prefer patterns such as
  "A하나 B" or "A이지만 B": state both in one line.
- Examples of tone:
    - "퀄리티는 견조하나 밸류에이션 부담"
    - "성장성 우수, 집중도 리스크 주의"
    - "배당 안정적, 성장 모멘텀 제한적"

### summary (2~3 sentence explanation)
- Expand the headline with ONE specific strength AND ONE specific weakness.
- Reference at least one concrete metric or comparison basis
  (use metric_display_name and reason_hint from the provided data).
- Tie the implication back to the preset's philosophy in one clause.
- Do NOT recommend buy/sell/hold actions.
- Do NOT mention wallet holdings excluded from this portfolio unless the
  data explicitly flags it as relevant.

## Rules

- The preset lens is fixed for this turn. Do not suggest switching presets
  in E1. (E6 handles comparison after adjustment.)
- Base your claims strictly on the provided `strengths`, `weaknesses`,
  `holding_count`, and `portfolio_return_total` fields. Do not invent
  metrics or market narratives.
- Korean polite form ("-입니다", "-세요"). Follow STYLE rules in the
  system prompt.
- Wallet context is provided ONLY for background awareness
  (total_holdings_count and excluded count). Do not analyze wallet-level
  holdings in E1.
"""
