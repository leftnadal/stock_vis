# Slice 11 Part 5 — Merged Eval (병진 + Claude)

라벨 재공개 + 두 평가자 점수 매핑.

| Case | entry | model  | rep | fit | 병진 nat | 병진 ins | 병진 actn | Claude nat | Claude ins | Claude actn |
|------|-------|--------|-----|-----|----------|----------|-----------|------------|------------|-------------|
| # 1 | e4 | haiku  | #2 | P | 3 | 4 |  N/A | 4 | 4 |  N/A |
| # 2 | e6 | haiku  | #1 | P | 4 | 3 |  N/A | 3 | 4 |  N/A |
| # 3 | e1 | sonnet | #2 | P | 3 | 3 |   OK | 5 | 5 |   OK |
| # 4 | e6 | sonnet | #2 | P | 3 | 3 |  N/A | 5 | 4 |  N/A |
| # 5 | e2 | haiku  | #2 | P | 4 | 4 |  N/A | 4 | 3 |  N/A |
| # 6 | e5 | sonnet | #1 | P | 2 | 4 |   OK | 5 | 5 |   OK |
| # 7 | e6 | haiku  | #2 | P | 4 | 4 |  N/A | 4 | 4 |  N/A |
| # 8 | e6 | sonnet | #1 | P | 2 | 2 |  N/A | 5 | 4 |  N/A |
| # 9 | e3 | haiku  | #2 | P | 4 | 3 |   NG | 4 | 4 |   NG |
| #10 | e5 | haiku  | #2 | P | 3 | 3 |   OK | 4 | 4 |   OK |
| #11 | e2 | haiku  | #1 | P | 4 | 4 |  N/A | 4 | 3 |  N/A |
| #12 | e1 | haiku  | #2 | P | 3 | 3 |   OK | 4 | 5 |   OK |
| #13 | e4 | sonnet | #2 | P | 4 | 5 |  N/A | 5 | 4 |  N/A |
| #14 | e1 | sonnet | #1 | P | 3 | 2 |   OK | 4 | 5 |   OK |
| #15 | e4 | sonnet | #1 | P | 3 | 5 |  N/A | 5 | 4 |  N/A |
| #16 | e3 | haiku  | #1 | F | 3 | 3 |   OK | 5 | 5 |   OK |
| #17 | e5 | sonnet | #2 | P | 4 | 4 |   NG | 5 | 4 |   NG |
| #18 | e5 | haiku  | #1 | P | 4 | 4 |   OK | 4 | 4 |   NG |
| #19 | e2 | sonnet | #2 | P | 3 | 3 |  N/A | 5 | 4 |  N/A |
| #20 | e2 | sonnet | #1 | P | 4 | 4 |  N/A | 4 | 4 |  N/A |
| #21 | e3 | sonnet | #1 | P | 3 | 3 |   OK | 5 | 4 |   OK |
| #22 | e1 | haiku  | #1 | P | 5 | 5 |   OK | 4 | 4 |   OK |
| #23 | e4 | haiku  | #1 | P | 2 | 5 |  N/A | 4 | 4 |  N/A |
| #24 | e3 | sonnet | #2 | P | 3 | 3 |   NG | 5 | 4 |   OK |
