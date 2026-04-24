"""
E2 (진단 카드) 지시문.

Version: 1.1 (2026-04-24)
"""

E2_INSTRUCTIONS = """# Task: Generate Diagnostic Cards (E2)

Generate up to 3 diagnostic cards, one for each of the top weaknesses in the
`analysis_target_portfolio`.

## Output

Return valid JSON matching this schema (no markdown fences, no surrounding text):

{
  "cards": [
    {
      "weakness_metric_id": "...",
      "what_is_wrong": "...",
      "comparison_basis": "...",
      "why_it_matters": "...",
      "caveat_or_exception": "...",
      "severity": "high" | "medium" | "low",
      "structural_or_single": "structural" | "single_outlier"
    },
    ...
  ]
}

## Four-Element Structure (CRITICAL — use them in order)

### 1. what_is_wrong (팩트 진술)
- State WHAT is observed, not WHY.
- 1~2 Korean sentences.
- Use specific numbers when available (percentiles, ratios, counts).
- Examples:
  - "5개 종목의 평균 PEG가 2.8로, 프리셋 통과 기준 (PEG < 1.5) 대비 크게 높습니다."
  - "ROIC 5년 평균이 12%로, 업종 하위 35% 구간에 위치합니다."

### 2. comparison_basis (비교 기준 명시)
- Make the benchmark EXPLICIT.
- 1 sentence.
- State WHICH universe / industry / sector the comparison is against, or the
  preset threshold.
- Examples:
  - "비교 기준: GICS Semiconductors 산업 87개 종목."
  - "비교 기준: S&P 500 전체 유니버스."
  - "비교 기준: 프리셋 정의 임계값 (PEG < 1.5)."

### 3. why_it_matters (프리셋 철학 연결)
- Connect to the PRESET's philosophy. Do not rely on generic market wisdom.
- 1~2 Korean sentences.
- Prefer a "[프리셋명] 관점에서는…" opening when natural.
- Examples:
  - "GARP 관점에서 성장 대비 높은 밸류에이션은 성장 둔화 시 급격한 밸류에이션 조정으로 이어질 수 있어 핵심 리스크입니다."
  - "Buffett Quality Value 관점에서 지속적인 ROIC는 경제적 해자의 대표 지표로, 이 기준이 흔들리면 퀄리티 전제가 약해집니다."

### 4. caveat_or_exception (예외/트레이드오프)
- Acknowledge nuance. Prevent over-generalization.
- 1 sentence (may be empty string only if truly nothing to add).
- Common patterns:
  - Single outlier skews the portfolio average.
  - Time horizon caveat (e.g., recent CAPEX spike is temporary).
  - A different preset would read this differently.
- Examples:
  - "단, NVDA 한 종목의 PEG 4.2가 평균을 끌어올린 측면이 있어 구조적 이슈는 아닐 수 있습니다."
  - "단, 최근 1년 CAPEX 증가로 인한 일시적 효과일 수 있어 향후 2~3분기 관찰이 필요합니다."

## Severity Assignment (rubric)

- `high`: Core tier metric AND level_tag "critical" or "weak" on ≥ 50% of
  holdings.
- `medium`: Core or Supporting tier AND level_tag "weak" on 30~50% of
  holdings, OR "moderate" on most holdings.
- `low`: Supporting tier only, OR marginal weakness (1~2 holdings).

## Structural vs Single Outlier

- `single_outlier`: The metric average is skewed by ONE holding
  (e.g., one stock with extreme value, others in healthy range).
- `structural`: Most or all holdings in the portfolio exhibit the weakness.

## Rules

- DO NOT recommend actions ("사야 한다", "팔아야 한다", "비중을 줄이세요").
- DO NOT switch presets mid-analysis.
- DO use conditional language ("-수 있습니다", "-가능성이 있습니다", "-로 읽힐 수 있습니다").
- DO keep each element within the specified length.
- If the portfolio has fewer than 3 weaknesses, return fewer cards.
"""
