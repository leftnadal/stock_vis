# Slice 12 Part 4 — Sonnet Matrix Dump (15 case)

## §1. Summary

- 케이스 실행: **15/15**
- schema fitting PASS: **15/15**
- gate 발동 actual: **7**
- gate match: **12/15**
- 총 비용: **$0.3207**
- 평균 latency: 20176ms

## §2. 케이스별 결과

| # | fixture | preset | fit | category_score | gate(actual/expected) | cost | latency |
| - | ------- | ------ | --- | -------------- | --------------------- | ---- | ------- |
| 1 | value_normal | buffett_quality_value | P | 66.12 | False/False | $0.01580 | 14039ms |
| 2 | value_edge | piotroski_f_score | P | 0.00 | True/False | $0.02473 | 23812ms |
| 3 | value_gate | buffett_quality_value | P | 26.12 | False/False | $0.02148 | 17884ms |
| 4 | growth_normal | garp | P | 63.38 | False/False | $0.02510 | 24388ms |
| 5 | growth_edge | quality_growth | P | 0.00 | True/False | $0.01786 | 15478ms |
| 6 | growth_gate | garp | P | 26.62 | False/False | $0.01843 | 18223ms |
| 7 | income_normal | dividend_growth | P | 25.52 | False/False | $0.02257 | 23549ms |
| 8 | income_edge | dividend_growth | P | 0.00 | True/True | $0.02204 | 21355ms |
| 9 | income_gate | dividend_growth | P | 0.00 | True/True | $0.02121 | 21884ms |
| 10 | factor_normal | low_volatility | P | 51.50 | False/False | $0.02106 | 18654ms |
| 11 | factor_edge | quality_factor | P | 0.00 | True/True | $0.02077 | 20141ms |
| 12 | factor_gate | low_volatility | P | 38.62 | True/True | $0.02493 | 25238ms |
| 13 | special_normal | concentrated_portfolio | P | 49.50 | False/False | $0.01933 | 16280ms |
| 14 | special_edge | contrarian | P | 0.00 | True/False | $0.02075 | 18698ms |
| 15 | special_gate | concentrated_portfolio | P | 57.75 | False/False | $0.02465 | 23021ms |
