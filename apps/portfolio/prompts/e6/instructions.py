"""
E6 (조정 후 비교 해설) 지시문.

Version: 1.1 (2026-04-24)
"""

E6_INSTRUCTIONS = """# Task: Post-Adjustment Comparison (E6)

The user applied an adjustment and the analysis was re-run. Compare the
ORIGINAL analysis to the ADJUSTED analysis, and explain what changed.

## Output

Return valid JSON (no markdown fences):

{
  "key_changes": [
    "<Change point 1>",
    "<Change point 2>",
    ...  // 3~5 items
  ],
  "summary": "<Overall interpretation, 2~3 Korean sentences>",
  "implication_for_user": "<Optional forward-looking note, 1~2 Korean sentences; empty string if nothing meaningful>"
}

## Content Guidelines

### key_changes (3~5 items)

Focus on what SHIFTED, not on static facts. Good examples:
- Strength/weakness composition changes:
  "강점 구성이 ROIC 중심에서 ROIC + 성장 중심으로 변화"
- Specific stocks newly appearing/disappearing in strengths or weaknesses:
  "INTC가 새로 ROIC 약점에 편입 (5종목 중 1종목)"
- Level tag transitions:
  "INTC ROIC level_tag: moderate → weak"
- Diagnostic card severity changes:
  "PEG 약점 카드 severity: critical → weak"
- Return breakdown shifts when comparison-group scope changes:
  "섹터 기준 percentile 78% → 유니버스 기준 62%"

Skip these (do NOT list as key changes):
- Trivial numeric differences (0.122 → 0.128).
- Changes in Context-tier metrics unless they flip a tag.

### summary (2~3 sentences)

- What did the adjustment reveal about the portfolio?
- Did the result align with or differ from the user's stated intent?
- Does the adjusted view suggest the portfolio fits a different preset
  angle? (Hint, do not prescribe.)

Example:
"ROIC 기준을 올리고 성장을 중시하자 퀄리티 + 성장 복합 종목이 부각됩니다.
현재 구성이 순수 Buffett보다는 Quality Growth 관점에 더 가까울 수 있음을
시사합니다."

### implication_for_user (1~2 sentences, OPTIONAL)

A gentle forward suggestion when natural:
- Suggesting another preset as additional lens ("Quality Growth로도 분석해보시면
  다른 관점의 강점이 드러날 수 있습니다").
- Noting that this adjustment is session-scoped only ("이번 조정은 이번 분석에만
  적용됩니다").

Leave as empty string if no meaningful suggestion.

## Rules

- Reference SPECIFIC metrics and holdings by name where possible.
- Use before/after framing inside key_changes items.
- Preserve the preset lens (do not command switching presets; suggest
  additional angles at most).
- No buy/sell recommendations.
- Korean, honorific form.
- key_changes must have 3 to 5 items. Fewer or more is invalid.
"""
