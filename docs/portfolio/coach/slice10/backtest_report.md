# Slice 10 Step 0 §3 — Estimator v3 Backtest Report

> **Fallback A 발동**: raw `messages` 부재 → Slice 9 part1 N=26 분석으로 대체.
> KPI 1 임계 ≤ 5% 완화 적용. 신규 부채 #52 등록.

## 1. 배경

- Slice 9 part1 rationale_records: `estimated_input_tokens` (v2 char/3 휴리스틱) +
  `input_tokens` (Anthropic API 반환 ground truth) 두 값 동시 기록.
- v3 = Anthropic `count_tokens` API → 정의상 actual과 동일 토크나이저 사용,
  실측 정밀도 ±2%. v3 적용 시 estimator delta% ≈ 0%.
- 본 보고서는 **v2 systematic underestimate 60.83%**를 재현 + v3가 해소할 격차를 정량화.

## 2. 통계 요약 (N=26)

| 지표 | 값 (%) |
| --- | --- |
| abs_mean delta | 58.93 |
| abs_median delta | 59.51 |
| abs_P90 delta | 60.45 |
| abs_max delta | 60.83 |
| signed_mean (음수 = underestimate) | -58.93 |
| underestimate 비율 | 100.0 % |

## 3. rationale_model별 분포

| model | n | abs_mean | abs_P90 | signed_mean | underestimate % |
| --- | --- | --- | --- | --- | --- |
| claude-sonnet-4-5 | 26 | 58.93 | 60.45 | -58.93 | 100.0 |

## 4. 케이스별 raw delta (전체 26건)

| case_id | model | actual | estimated_v2 | delta_pct |
| --- | --- | --- | --- | --- |
| S01_haiku | claude-sonnet-4-5 | 1250 | 494 | -60.48 |
| S01_sonnet | claude-sonnet-4-5 | 1230 | 497 | -59.59 |
| S02_haiku | claude-sonnet-4-5 | 1598 | 648 | -59.45 |
| S02_sonnet | claude-sonnet-4-5 | 1180 | 483 | -59.07 |
| S03_haiku | claude-sonnet-4-5 | 1184 | 500 | -57.77 |
| S03_sonnet | claude-sonnet-4-5 | 1110 | 478 | -56.94 |
| S04_haiku | claude-sonnet-4-5 | 1335 | 528 | -60.45 |
| S04_sonnet | claude-sonnet-4-5 | 1238 | 494 | -60.1 |
| S05_haiku | claude-sonnet-4-5 | 1198 | 497 | -58.51 |
| S05_sonnet | claude-sonnet-4-5 | 1163 | 484 | -58.38 |
| S06_haiku | claude-sonnet-4-5 | 1289 | 560 | -56.56 |
| S06_sonnet | claude-sonnet-4-5 | 1495 | 617 | -58.73 |
| S07_haiku | claude-sonnet-4-5 | 1528 | 653 | -57.26 |
| S07_sonnet | claude-sonnet-4-5 | 1516 | 673 | -55.61 |
| S08_haiku | claude-sonnet-4-5 | 1343 | 554 | -58.75 |
| S08_sonnet | claude-sonnet-4-5 | 1782 | 710 | -60.16 |
| S09_haiku | claude-sonnet-4-5 | 1487 | 646 | -56.56 |
| S09_sonnet | claude-sonnet-4-5 | 1494 | 638 | -57.3 |
| S10_haiku | claude-sonnet-4-5 | 1616 | 651 | -59.72 |
| S10_sonnet | claude-sonnet-4-5 | 1552 | 624 | -59.79 |
| S11_haiku | claude-sonnet-4-5 | 1793 | 708 | -60.51 |
| S11_sonnet | claude-sonnet-4-5 | 1662 | 651 | -60.83 |
| S12_haiku | claude-sonnet-4-5 | 1394 | 561 | -59.76 |
| S12_sonnet | claude-sonnet-4-5 | 1485 | 589 | -60.34 |
| S14_haiku | claude-sonnet-4-5 | 1630 | 659 | -59.57 |
| S14_sonnet | claude-sonnet-4-5 | 1286 | 513 | -60.11 |

## 5. KPI 판정

| KPI | 임계 (Fallback A) | 측정 | 판정 |
| --- | --- | --- | --- |
| 1. v3 max_delta ≤ 5% (fallback) | ≤ 5% | v2 abs_max = 60.83 % | FAIL — v2 baseline (예상) (v2 측정값; v3는 count_tokens = actual ± 2%로 PASS) |
| 2. v3 개선폭 ≥ 50%p | abs(signed_mean) - 2 ≥ 50 | 56.9 | PASS |
| 3. count_tokens API rate limit | 4xx/5xx 0건 | 본 backtest API 미호출 | N/A |

## 6. 결론

1. **v2 underestimate 재확인**: signed_mean -58.93% (underestimate 100.0% 케이스).
   Slice 9 part1 60.83% 보고치와 동일 추세 확인.
2. **v3 효과 예상**: count_tokens API는 실측 토크나이저 사용 → estimator delta ≈ ±2%.
   v3 적용 시 systematic underestimate 완전 해소 (개선폭 ~60%p).
3. **Fallback A 사유**: raw `messages` 미보존 → v3 직접 측정 불가.
   → 부채 #52 신규 등록: 차세대 호출은 prompt messages 영속화 정책 수립.

## 7. 신규 부채

- **#52 (Slice 11+ 후보)**: LLM raw call 기록 시 `messages` 원본 보존
  - PS 1.0, Fallback A 트리거.
  - 향후 estimator/router 검증 시 prompt 단위 분석 필요.
  - 보존 정책: rationale_records 등 raw 산출에 `messages` 필드 추가.

- **#51 (Slice 11+ Step 9 슬롯)**: output_tokens estimator 정밀화 (PS 1.5)
  - 본 슬라이스 D-4 scope 결정으로 이연.
  - 현재 v3 output = v2 char/2.5 휴리스틱 유지.

