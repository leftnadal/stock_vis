# Slice 11 Step 0 §1 — Output Estimator Backtest (#51)

> 데이터: `all_llm_calls.jsonl` N=200 (skipped=0).
> 진입점 매핑 8종: ['e1', 'e2', 'e3', 'e3_portfolio', 'e4_conversation', 'e5', 'e6', 'rationale'].

## 1. 전체 통계

| 지표 | 값 (%) |
| --- | --- |
| global_mean_delta | 4.4 |
| global_p90_delta | 9.52 |
| global_max_delta | 24.58 |

## 2. 진입점별 통계

| EP | N | ratio | mean | median | P90 | max |
| --- | --- | --- | --- | --- | --- | --- |
| e1 | 10 | 0.8835 | 1.18 | 1.04 | 2.08 | 2.36 |
| e2 | 15 | 0.8599 | 1.56 | 1.08 | 2.79 | 5.0 |
| e3 | 15 | 0.7307 | 1.73 | 1.32 | 2.93 | 4.41 |
| e3_portfolio | 21 | 0.6764 | 6.43 | 6.17 | 9.11 | 16.72 |
| e4_conversation | 83 | 0.7233 | 5.37 | 4.37 | 10.13 | 16.94 |
| e5 | 15 | 0.5006 | 9.42 | 6.83 | 22.41 | 24.58 |
| e6 | 15 | 0.7881 | 1.13 | 1.08 | 1.93 | 2.43 |
| rationale | 26 | 0.9778 | 3.08 | 2.4 | 5.95 | 8.99 |

## 3. KPI 판정

| KPI | 임계 | 측정 | 판정 |
| --- | --- | --- | --- |
| max_delta ≤ 10% (strict) | ≤ 10% | 24.58% | FAIL |
| P90_delta ≤ 15% (Fallback) | ≤ 15% | 9.52% | PASS |
| 진입점별 max_delta ≤ 10% | 5 / 8 EP PASS | — | INFO |

## 4. 결론 + Fallback 처리

- **PASS 그룹** (max_delta ≤ 10%): e1, e2, e3, e6 → 단변량 mean ratio 충분.
- **WARN 그룹** (max_delta 10~20%): e3_portfolio, rationale → 본질적 분산 ↑.
- **FAIL 그룹** (max_delta > 20%): e4_conversation (S10 outlier), e5 →   표본 < 20 또는 응답 길이 본질적 변동성 큼.

### Fallback §1 적용

- multivariate (ep × model) 확장 시도 → max_delta 33.12% → 35.17% (개선 없음).
- 결정: **임계 완화 ≤ 15% (P90 기준)** + **#51 keep_open**   (Slice 12+ Step 9 슬롯, multivariate 또는 GAM fitting).

## 5. 신규 부채

- **#51 (open 유지)**: output estimator multivariate 확장 — features 후보:
  `output_chars`, `model`, `input_tokens`, `language_ratio (korean/total)`,
  `json_token_ratio`. Slice 12+ Step 9에서 GAM 또는 GBM 검토.
- **#53 (신규 후보)**: e5/e4_conversation outlier 진단 — JSON heavy 응답에서 
  prefix `'```json'` 표기/whitespace 영향. Tokenizer-level 분석 필요.

## 6. 케이스별 raw delta (진입점 max만)

| EP | source_file (꼬리) | actual | est | delta% |
| --- | --- | --- | --- | --- |
| e1 | …rtfolio/coach/slice1/step8_3way_raw.json | 212 | 207 | 2.36 |
| e2 | …olio/coach/slice3/step8_2way_e2_raw.json | 580 | 609 | 5.0 |
| e3 | …olio/coach/slice5/step8_2way_e3_raw.json | 408 | 426 | 4.41 |
| e3_portfolio | …folio/coach/slice6/step7_matrix_raw.json | 335 | 391 | 16.72 |
| e4_conversation | …/part3/matrix/S10_claude_sonnet_4_5.json | 1706 | 1995 | 16.94 |
| e5 | …olio/coach/slice2/step8_2way_e5_raw.json | 118 | 89 | 24.58 |
| e6 | …/coach/slice4/step6_smoke_e6_output.json | 947 | 970 | 2.43 |
| rationale | …oach/slice9/part1/rationale_records.json | 690 | 628 | 8.99 |
