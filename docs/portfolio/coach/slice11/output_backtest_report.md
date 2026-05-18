# Slice 11 Step 0 §1 — Output Estimator Backtest (#51)

> 데이터: `all_llm_calls.jsonl` N=200 (skipped=0).
> 진입점 매핑 8종: ['e1', 'e2', 'e3', 'e3_portfolio', 'e4_conversation', 'e5', 'e6', 'rationale'].

## 1. 전체 통계

| 지표 | 값 (%) |
| --- | --- |
| global_mean_delta | 5.11 |
| global_p90_delta | 11.2 |
| global_max_delta | 33.12 |

## 2. 진입점별 통계

| EP | N | ratio | mean | median | P90 | max |
| --- | --- | --- | --- | --- | --- | --- |
| e1 | 10 | 0.8835 | 1.23 | 1.03 | 2.36 | 2.6 |
| e2 | 15 | 0.8599 | 1.57 | 1.2 | 2.33 | 5.86 |
| e3 | 15 | 0.7307 | 2.13 | 2.13 | 3.45 | 4.38 |
| e3_portfolio | 21 | 0.6764 | 8.16 | 7.26 | 17.01 | 17.43 |
| e4_conversation | 83 | 0.7233 | 5.81 | 5.1 | 10.8 | 33.12 |
| e5 | 15 | 0.5006 | 10.87 | 9.92 | 16.67 | 25.78 |
| e6 | 15 | 0.7881 | 1.33 | 1.53 | 2.25 | 2.48 |
| rationale | 26 | 0.9778 | 4.52 | 4.0 | 8.18 | 12.44 |

## 3. KPI 판정

| KPI | 임계 | 측정 | 판정 |
| --- | --- | --- | --- |
| max_delta ≤ 10% (strict) | ≤ 10% | 33.12% | FAIL |
| P90_delta ≤ 15% (Fallback) | ≤ 15% | 11.2% | PASS |
| 진입점별 max_delta ≤ 10% | 4 / 8 EP PASS | — | INFO |

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
| e1 | …rtfolio/coach/slice1/step8_3way_raw.json | 192 | 197 | 2.6 |
| e2 | …olio/coach/slice3/step8_2way_e2_raw.json | 580 | 614 | 5.86 |
| e3 | …olio/coach/slice5/step8_2way_e3_raw.json | 753 | 720 | 4.38 |
| e3_portfolio | …folio/coach/slice6/step7_matrix_raw.json | 373 | 438 | 17.43 |
| e4_conversation | …/part3/matrix/S10_claude_sonnet_4_5.json | 1706 | 2271 | 33.12 |
| e5 | …olio/coach/slice2/step8_2way_e5_raw.json | 128 | 95 | 25.78 |
| e6 | …olio/coach/slice4/step8_2way_e6_raw.json | 967 | 943 | 2.48 |
| rationale | …oach/slice9/part1/rationale_records.json | 442 | 387 | 12.44 |
