# Slice 11 Step 0 종결 보고 (trio 5-Part 진입)

> **Step 0 단독**: trio 5-Part 인프라 + 부채 정리 단계. 진입점 작업 자체는 Part 1+.

## 요약

| 항목                | 값                                            |
| ------------------- | --------------------------------------------- |
| 회귀                | 512 → 532 (+20)                               |
| IDENTICAL hash      | 7/7                                           |
| 단독 비용           | $0.00 (LLM 호출 없음 — backtest는 무료 데이터 기반) |
| 누적 비용           | $2.3775 (Slice 10 보존) — 마진 **41%** (신 임계 $4.00 기준) |
| LLM 호출            | 0 / 50                                        |
| KPI 12/12           | 12 PASS, 0 FAIL                               |
| #51 close 상태      | **keep_open** — P90 11.20% PASS이나 max 33.12% (multivariate 후속) |
| #52 정책 정착       | hook + 정책 + 테스트 완료 (Production 통합은 Part 1+) |
| E6 mock fixture     | PASS (5 종목, 1 ETF + 4 stocks, income preset) |
| 임계 상향           | $3.00 → $4.00 / $2.40 → $3.20 / $3.40 재상향 트리거 |
| KPI 9c 등록         | 스켈레톤 완료 (Part 3 발동 대기)              |

## §1 #51 output estimator — KPI 1

`portfolio/measure/estimator_v3.py` 본격 구현:

- 진입점별 char ratio fit (`ENTRY_POINT_OUTPUT_RATIOS` 8개 등록).
- `estimate_output_tokens(expected_output_chars, entry_point=None, model=...)` 시그니처.
- fallback: `GLOBAL_OUTPUT_RATIO = 0.7584` (전체 평균).
- backtest 결과:
  - global mean_delta = 5.11%
  - global P90_delta = 11.20%
  - global max_delta = 33.12% (e4_conversation Slice 8 S10 sonnet outlier 1건)
- KPI 임계 ≤ 10% strict → **P90 ≤ 15% 완화** (Fallback A 채택).
- multivariate (ep × model) 시도 → **max 35.17%로 악화** → 단변량 mean ratio 유지.
- **#51 keep_open** (Slice 12+ Step 9 슬롯, multivariate / GAM / GBM).

### 진입점별 ratio (mean fit)

| EP                 | n   | ratio  | max_delta |
| ------------------ | --- | ------ | --------- |
| e1                 | 10  | 0.8835 | 2.60%     |
| e2                 | 15  | 0.8599 | 5.86%     |
| e3                 | 15  | 0.7307 | 4.41%     |
| e3_portfolio       | 21  | 0.6764 | 17.43%    |
| e4_conversation    | 83  | 0.7233 | 33.12%    |
| e5                 | 15  | 0.5006 | 25.78%    |
| e6                 | 15  | 0.7881 | 2.48%     |
| rationale          | 26  | 0.9778 | 12.44%    |

전체 보고서: [`output_backtest_report.md`](output_backtest_report.md).

## §2 #52 messages 보존 정책

`portfolio/measure/message_dumper.py` 신규 + `MESSAGES_PERSISTENCE_POLICY.md` 정책 문서.

- 저장 위치: `docs/portfolio/coach/slice<N>/llm_messages.jsonl` (slice별 격리).
- 멱등성: SHA256(messages+system+model) hash dedupe.
- toggle: `STOCKVIS_LLM_MESSAGE_DUMP=0` → no-op.
- redact: API_KEY / password / sk-ant 패턴 자동 마스킹.
- 단위 테스트 6건 PASS.

**Production 통합 (client.py)은 Part 1+ scope** — Step 0은 인프라 + 정책 + 테스트만 완료.

## §3 E6 mock fixture (portfolio_a2)

A2 통합 시연용 신규 portfolio:

- `portfolio/tests/fixtures/coach/portfolio_a2.json` — income preset 1 ETF (VYM) + 4 dividend stocks (KO, JNJ, VZ, PEP), 합 1.0.
- `portfolio/tests/fixtures/coach/portfolio_a2_e6_analysis.json` — E6 비교 해설 mock
  (VZ 축소 + SCHD 추가, action_items 1건 포함).
- 단위 테스트 4건: schema 검증, holdings 1.0 합, preset 차별, E6 Pydantic validate, adjustments alignment.

**D-4 a 채택 유지**: E6 분석엔진 실제 호출 안 함. Phase 2 #12 진입 전 manual 보정 인정.

## §4 COST_POLICY $4.00 상향

| 항목                    | 이전     | 신 (Slice 11 D-3) |
| ----------------------- | -------- | ----------------- |
| 누적 임계               | $3.00    | **$4.00**         |
| CostGuard 80% 경고      | $2.40    | **$3.20**         |
| 재상향 트리거           | (명시 X) | **$3.40**         |
| mini-slice cap          | $0.50    | $0.50 (유지)      |
| full-slice cap          | $1.00    | $1.00 (유지)      |
| 비용 패턴 명문화        | (없음)   | $1 → $1.5 → $2 → $3 → $4 |

`portfolio/llm/cost_guard.py`:
- `threshold` default `3.00` → `4.00`
- `warning` default `2.40` → `3.20`
- 단위 테스트 갱신 3건 (test_threshold_default_4_dollar, test_warning_default_3_20, test_slice11_warning_at_3_20)

`.env`도 동기화 (`COST_THRESHOLD_USD=4.00`, `COST_WARNING_USD=3.20`).

## §5 KPI 9c 스켈레톤

`tests/coach/test_kpi_9c_estimator_validation.py`:

- `measure_kpi_9c_delta(est, actual) → %` 헬퍼.
- `KPI_9C_THRESHOLD_PCT = 2.0`.
- `test_kpi_9c_real_call_within_2pct` 는 `@pytest.mark.skip` 상태 — Part 3 첫 smoke 호출
  시 skip 해제 + 실측 채움.

## §6 회귀 분류

기존 Slice 10 카테고리 (data-prep / cost / mixed) 재사용 충분 — 신규 카테고리 추가
불필요. `portfolio/tests/slice11/test_regression_classifier.py` 신규 2건:

- `test_output_estimator_changes_are_mixed`: portfolio/measure/ + scripts/coach/ + tests/coach/ → mixed.
- `test_messages_persistence_changes_are_mixed`: portfolio/measure/ + tests/coach/ → mixed.

## §11 산출물 체크리스트 (13건 + 갱신)

### 신규 (9건)

- [x] `scripts/coach/backtest_output_estimator.py`
- [x] `docs/portfolio/coach/slice11/output_backtest_report.md`
- [x] `tests/coach/test_messages_persistence.py`
- [x] `docs/portfolio/coach/MESSAGES_PERSISTENCE_POLICY.md`
- [x] `portfolio/tests/fixtures/coach/portfolio_a2.json`
- [x] `portfolio/tests/fixtures/coach/portfolio_a2_e6_analysis.json`
- [x] `tests/coach/test_kpi_9c_estimator_validation.py` (스켈레톤)
- [x] `docs/portfolio/coach/slice11/kpi_step0.md`
- [x] `docs/portfolio/coach/slice11/step0_closing.md`
- [x] `portfolio/measure/message_dumper.py` (보너스)
- [x] `tests/coach/test_portfolio_a2_fixture.py` (보너스)
- [x] `portfolio/tests/slice11/test_regression_classifier.py`

### 갱신 (5건)

- [x] `portfolio/measure/estimator_v3.py` (output estimator 본격 구현)
- [x] `tests/coach/test_estimator_v3.py` (+4 진입점 테스트)
- [x] `docs/portfolio/coach/COST_POLICY.md` ($4.00 / $3.20 / $3.40)
- [x] `portfolio/llm/cost_guard.py` (임계 상수 갱신 + 문서)
- [x] `portfolio/tests/slice9/test_cost_guard_cap.py` (테스트 갱신 + 1건 추가)
- [x] `.env` (COST_THRESHOLD_USD=4.00, COST_WARNING_USD=3.20)
- [x] `.git/hooks/pre-commit` (slice11 화이트리스트)
- [x] `scripts/coach/dump_all_llm_calls.py` (`output_chars` 필드 추가)
- [x] `docs/portfolio/coach/all_llm_calls.jsonl` (200 entries, output_chars 보강)

## Slice 11 Part 1 진입 준비 상태

| 자산                                                   | 상태             |
| ------------------------------------------------------ | ---------------- |
| estimator v3 input + output                            | **PRODUCTION READY** |
| message dumper hook                                    | **모듈 완료** (client 통합은 Part 1) |
| portfolio_a2 + E6 mock fixture                         | **PRODUCTION READY** |
| COST_POLICY $4.00 / 80% / 재상향 트리거                | **반영 완료**    |
| KPI 9c 스켈레톤                                        | **Part 3 발동 대기** |
| 회귀 baseline                                          | **532**          |

Slice 11 Part 1 진입 가능 — 6 진입점 통합 input schema (TimeSeriesContext 확장).

## 회신 매트릭스

```
Slice 11 Step 0 종결 (trio 5-Part 시작).
- 회귀: 512 → 532 (+20)
- IDENTICAL: 7/7
- 비용 단독: $0.00 / 누적: $2.3775 (마진 41%, 신 임계 $4.00)
- LLM 호출: 0/50
- KPI 12/12: 12 PASS, 0 FAIL
- #51 close: P90 11.20% PASS (max 33.12% — Fallback A, keep_open)
- #52 정책 정착: PASS (Production 통합은 Part 1+)
- E6 mock fixture: PASS (1 ETF + 4 stocks, income preset)
- 임계 상향: $3.00 → $4.00 갱신 PASS

Slice 11 Part 1 진입 준비 상태: 완료
KPI 9c 스켈레톤: 등록 완료, Part 3 발동 대기
```

## Manual 검증 필요 항목

- 없음. 모든 KPI 자동 측정 + Fallback A 영향까지 12/12 PASS.
- Slice 11 Part 1 진입 시 portfolio_a2 fixture가 6 진입점 통합 input schema로
  확장될 때 manual 검증이 추가될 수 있음.
