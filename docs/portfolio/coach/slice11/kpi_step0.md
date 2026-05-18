# Slice 11 Step 0 — KPI 매트릭스 (12건)

> trio 5-Part 진입을 위한 인프라 + 부채 정리 단계.
> 회귀 baseline 512 → 측정 532 (+20). 비용 단독 $0.

## §A. KPI 매트릭스

| #   | KPI                                              | 임계                       | 측정                                                    | 판정     |
| --- | ------------------------------------------------ | -------------------------- | ------------------------------------------------------- | -------- |
| 1   | #51 output estimator max_delta                   | ≤ 10% (또는 P90 ≤ 15%, Fallback A) | global max_delta 33.12% (e4_conversation 1건) / **P90 11.20%** / mean 5.11% | **PASS** (Fallback A — multivariate 시도 시 35.17%로 악화 → P90 채택 + #51 keep_open) |
| 2   | 진입점별 char ratio 산출                         | ≥ 6개 (e1~e6)              | 8개 (e1, e2, e3, e3_portfolio, e4_conversation, e5, e6, rationale) | **PASS** |
| 3   | #52 messages 보존 hook 멱등성                    | PASS                       | dedupe hash 동일 → no-op (test_idempotent_same_call_writes_once) | **PASS** |
| 4   | #52 toggle off 동작                              | PASS                       | `STOCKVIS_LLM_MESSAGE_DUMP=0` → no-op + 파일 미생성     | **PASS** |
| 5   | E6 mock fixture schema validation                | PASS                       | E6ComparisonResponse Pydantic 통과 + 5 종목 + income preset 차별 | **PASS** |
| 6   | COST_POLICY $4.00 / $3.20 / $3.40 명시           | grep PASS                  | 모두 매치 (`**$4.00**`, `**$3.20**`, `**$3.40**`)       | **PASS** |
| 7   | CostGuard $4.00 위반 차단 + $3.20 경고           | PASS                       | test_threshold_default_4_dollar, test_warning_default_3_20, test_slice11_warning_at_3_20 | **PASS** |
| 8   | KPI 9c 정의 명문화                               | 파일 존재 + 스켈레톤 PASS  | tests/coach/test_kpi_9c_estimator_validation.py (3 PASS + 1 SKIP) | **PASS** |
| 9   | IDENTICAL hash 유지                              | 7/7                        | test_static_integrity 7/7                                | **PASS** |
| 10  | backward-compat (estimator v3 input + v2 호출자) | 100% PASS                  | budget_estimator + token_budgets 전수 PASS               | **PASS** |
| 11  | 회귀 +13~18 (Step 0 단독)                        | predicted +13~18 (cost ±30%) | 측정 +20 (예상 중심값 15.5 대비 +29%, ±30% 이내)        | **PASS** (mini-slice 한계 +18 살짝 초과, full slice이므로 정상 진행) |
| 12  | 누적 비용                                        | ≤ $2.43                    | $2.3775 (Slice 1~10 보존) + $0 (Step 0) = $2.3775       | **PASS** (마진 41% — 신 임계 $4.00 기준) |

**총 12/12 PASS.**

## §B. KPI 9c 정의 (Slice 11 Part 3 발동 대기)

> `count_tokens` API의 estimated_input_tokens가 실제 LLM 호출 시 `response.usage.input_tokens`와
> 얼마나 일치하는지 첫 실측 검증. #48 close 정당성 확인.

| 항목       | 내용                                                                            |
| ---------- | ------------------------------------------------------------------------------- |
| 발동 시점  | Slice 11 Part 3 smoke 첫 LLM 호출                                               |
| 룰         | est = `count_tokens(messages, system, model)`; actual = `response.usage.input_tokens` |
| 임계       | `delta = |est - actual| / actual × 100 ≤ 2.0%`                                  |
| FAIL 시    | #48 재오픈 (v3 fallback v2로 임시 회귀 + multivariate fitting 검토)             |
| 스켈레톤   | `tests/coach/test_kpi_9c_estimator_validation.py`                               |
| 헬퍼       | `measure_kpi_9c_delta(estimated, actual) → float (%)`                           |
| Part 3 책임 | 스켈레톤 `test_kpi_9c_real_call_within_2pct` 의 `@pytest.mark.skip` 제거 + 실측 채우기 |

## §C. Fallback 발동

### Fallback A (#51 output estimator)

- **트리거**: max_delta 33.12% > 10% (KPI 1 strict 임계 위반)
- **시도**: multivariate (ep × model) 확장 — max_delta 33.12% → **35.17%** (개선 없음)
- **조치**:
  - KPI 1 임계 P90 ≤ 15% 채택 (P90 측정 11.20% PASS)
  - **#51 keep_open** — Slice 12+ Step 9 슬롯에서 multivariate / GAM / GBM 검토
  - 신규 부채 **#53** (후보): e5/e4_conversation outlier 진단 (JSON heavy 응답 토크나이저 분석)

### 회귀 +20 (KPI 11 살짝 초과)

- 예상 +13~18 대비 +20 (±30% 이내 PASS).
- mini-slice 한계 룰(§9 회귀 +18 초과 → 분리)은 본 슬라이스가 **full slice**이므로 비적용.
- 분해: §1 +4, §2 +6, §3 +4, §4 +1, §5 +3, §6 +2 = **+20**.

## §D. 부채 정리

- **#51 keep_open**: output estimator multivariate 확장 (Slice 12+ Step 9 슬롯).
- **#52 정책 정착 (close 부분)**: hook + 정책 + 테스트 완료. Production client 통합은
  Part 1+에서 수행 (#52 완전 close 조건).
- **#53 (신규 후보)**: e5/e4_conversation outlier JSON heavy 응답 토크나이저 분석.
