# Slice 6 Part 4 Step 9.3 — Manual Eval 결과 보고

## Provider 집계

| provider | n | label_mean | cost_avg | efficiency | naturalness | insight |
|---|---|---|---|---|---|---|
| sonnet | 5 | 3.2 | $0.017381 | 184.22 | 3.0 | 3.4 |
| haiku | 5 | 3.3 | $0.00463 | 713.63 | 3.2 | 3.4 |

## Winner 판정

- **winner**: **haiku** (efficiency gap = 287.38%)
- **글쓰기 가설 5/5 정착**: PASS ✓

## G6 (V4 alignment) 자동 분기

- **resolution**: **fixture_keep_with_debt**
- action: V4 label_mean 2.5000 < V5 3.7500 → Buffett 스타일 차별성 약함. fixture 유지 + prompt 튜닝 신규 부채 #23 등록 (PS 2.0).
- 부채 변화량: +1
- V4 label_mean: 2.5
- V5 label_mean: 3.75

## Preset 외삽 robustness (haiku, Slice 5 비교)

- haiku insight 그룹차: **1.0** (Slice 5 baseline ≤ 0.50)
- 판정: WARN ⚠ (H3 분기)
- haiku V별 insight 평균: {'V2': 3.0, 'V5': 4.0, 'V4': 3.0, 'V3': 4.0, 'V1': 3.0}

## 개별 평가 (eval_id 순)

| eval_id | V | preset | provider | nat | ins | label_mean | cost | efficiency |
|---|---|---|---|---|---|---|---|---|
| 1 | V4 | buffett_quality_value | sonnet | 2.0 | 2.0 | 2.0 | $0.017082 | 117.08 |
| 2 | V2 | garp | sonnet | 2.0 | 3.0 | 2.5 | $0.017835 | 140.17 |
| 3 | V2 | garp | haiku | 3.0 | 3.0 | 3.0 | $0.004664 | 643.22 |
| 4 | V5 | dividend_growth | haiku | 3.0 | 4.0 | 3.5 | $0.004505 | 776.95 |
| 5 | V3 | quality_factor | sonnet | 3.0 | 4.0 | 3.5 | $0.017115 | 204.5 |
| 6 | V4 | buffett_quality_value | haiku | 3.0 | 3.0 | 3.0 | $0.004727 | 634.63 |
| 7 | V5 | dividend_growth | sonnet | 4.0 | 4.0 | 4.0 | $0.018033 | 221.82 |
| 8 | V3 | quality_factor | haiku | 3.0 | 4.0 | 3.5 | $0.004716 | 742.15 |
| 9 | V1 | garp | haiku | 4.0 | 3.0 | 3.5 | $0.004538 | 771.2 |
| 10 | V1 | garp | sonnet | 4.0 | 4.0 | 4.0 | $0.016839 | 237.54 |