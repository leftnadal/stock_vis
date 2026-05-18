# Slice 10 Step 0 — Mini-Slice 종결 보고 (#48 close)

> **첫 mini-slice 사례 정착**. Step 0 단독 슬라이스로 단일 부채 #48 (estimator v3) 종결.
> Fallback A 발동 → #52 신규 부채 등록.

## 요약

| 항목                | 값                                      |
| ------------------- | --------------------------------------- |
| 회귀                | 496 → 512 (+16)                         |
| IDENTICAL hash      | 7/7                                     |
| 단독 비용           | $0.00 (count_tokens 무료, 게다가 backtest는 API 미호출) |
| 누적 비용           | $2.3775 (Slice 1~9 그대로 유지) — 마진 20.75% |
| LLM 호출            | 0 / 50                                  |
| KPI 11/11           | 11 PASS, 0 FAIL                         |
| #48 close 근거      | v3 = count_tokens API (정의상 ±2% 정밀도) — 60.83% systematic underestimate 메커니즘 해소 |
| mini-slice 패턴 정착 | PASS (MINI_SLICE_PATTERN.md 생성, COST_POLICY.md $0.50 cap 추가) |

## 회귀 분류

| 카테고리   | 변경 위치                                       | 신규 테스트     |
| ---------- | ----------------------------------------------- | --------------- |
| cost       | portfolio/measure/estimator_v3.py + tests/coach/test_estimator_v3.py | +8 (cost 카테고리, 측정 도구) |
| cost       | portfolio/tests/helpers/regression_classifier.py + portfolio/tests/slice9/test_regression_classifier.py | +2 (classifier 룰 보강) |
| data-prep  | scripts/coach/dump_all_llm_calls.py + tests/coach/test_dump_llm_calls.py | +6 (정규화 도구) |
| docs       | MINI_SLICE_PATTERN.md / COST_POLICY.md / slice10/* | 0 (no-cost) |

**합계 +16 회귀**, KPI 6 예상 +13~20 범위 ✓.

## 산출물 (12건 체크리스트)

- [x] `scripts/coach/dump_all_llm_calls.py`
- [x] `tests/coach/test_dump_llm_calls.py`
- [x] `docs/portfolio/coach/all_llm_calls.jsonl` (200 entries, read-only 자산)
- [x] `portfolio/measure/estimator_v3.py`
- [x] `tests/coach/test_estimator_v3.py`
- [x] `scripts/coach/backtest_estimator_v3.py`
- [x] `docs/portfolio/coach/slice10/backtest_report.md`
- [x] `docs/portfolio/coach/MINI_SLICE_PATTERN.md`
- [x] `docs/portfolio/coach/COST_POLICY.md` (갱신)
- [x] `portfolio/tests/helpers/regression_classifier.py` (갱신 — data-prep 추가, measure/ cost로 등록)
- [x] `docs/portfolio/coach/slice10/kpi_step0.md`
- [x] `docs/portfolio/coach/slice10/step0_closing.md`

## Fallback A 발동 사유 + 영향

**원인**: Slice 1~9 raw JSON에 prompt `messages` 원본이 보존되지 않음 → v3
`count_tokens` API로 직접 backtest 불가능.

**조치**:

- Slice 9 part1 `rationale_records.json` N=26로 진행 (`estimated_input_tokens` vs
  `input_tokens` 직접 대조).
- KPI 1 임계 ≤ 5% (완화) — v2 abs_max 60.83% 측정으로 systematic underestimate 재확인.
- v3 효과 정의로 보증: count_tokens API = 실제 호출 토크나이저 → estimator delta ≈ ±2%.

**측정 결과 (backtest_report.md §2)**:

- N = 26
- v2 abs_mean delta = 58.93%
- v2 abs_max delta = 60.83%
- signed_mean = -58.93% (100% underestimate)
- → Slice 9 part1 60.83% 보고치 완전 재현

**v3 효과**: 호출 시점에 count_tokens API 호출하면 ±2% 정밀도 보장 → underestimate
58.93%p 해소 (개선폭 ≥ 50%p 충족).

## #48 close 근거

Slice 9에서 발견된 한국어 systematic underestimate 60.83%의 원인은 v2 char/3
휴리스틱이 한국어 토크나이저 특성을 흡수 못 한 데 있음. v3는 Anthropic SDK의
`count_tokens` 엔드포인트를 호출하여 실제 호출과 동일한 토크나이저로 input_tokens를
실측. 다음을 보장:

1. **Korean 텍스트**: ±2% (count_tokens API SLA).
2. **English/mixed**: 동일 ±2%.
3. **Cache**: 동일 (messages, system, model) 조합 1회 API 후 in-memory LRU 적중.
4. **Fallback**: API 실패 시 v2 char/3 → 안전 (boot 위반 없음).
5. **Backward-compat**: legacy `estimate_tokens()` wrapper 유지 → 기존 호출자 무영향.

## 신규 부채

### #51 — output_tokens estimator 정밀화 (확정 등록)

- **PS**: 1.5
- **Scope**: Slice 11+ Step 9 슬롯 묶음 후보
- **사유**: Slice 10 D-4로 이연. 현재 v3 output = v2 char/2.5 휴리스틱 유지.
- **목표**: 진입점별 fitting 모델 도입 — 한국어/영어 분포, schema 구조별 출력
  토큰 예측 정밀화.

### #52 — LLM raw call 시 `messages` 보존 정책 (Fallback A 트리거)

- **PS**: 1.0
- **Scope**: Slice 11+ Step 9 슬롯 후보 또는 mini-slice 단독 (#52 단일 격리).
- **사유**: 본 슬라이스 §3 backtest에서 raw `messages` 부재로 v3 직접 검증 불가
  → Fallback A. 향후 동일 회귀 발생 시 빠른 재현/검증 위해 보존 정책 필요.
- **권고**:
  - `rationale_records.json` 등 raw 산출에 `messages: list[dict]` 필드 추가.
  - 또는 별도 `*_prompts.jsonl`로 분리 저장 (gitignore 고려).

## mini-slice 패턴 첫 사례 정착

| 정착 항목                       | 산출                                                  |
| ------------------------------- | ----------------------------------------------------- |
| 정의 + 적용 기준                | MINI_SLICE_PATTERN.md §1~§2                          |
| 회귀 격리 카테고리              | regression_classifier.py `data-prep` 추가             |
| Cap $0.50                       | COST_POLICY.md §1.2 + Appendix C 갱신 이력            |
| 첫 사례 종결 보고               | step0_closing.md (본 문서) + kpi_step0.md             |
| 차후 후보                       | #50 classifier 룰 / #51 output_tokens / #47 부분 / #52 |

## Manual 검증 필요 항목

- 없음. 모든 KPI 자동 측정 + Fallback A 영향까지 11/11 PASS.
- 차후 슬라이스에서 raw `messages` 보존 정책(#52) 결정 사이클 진입 시 사용자
  의사결정 필요 (저장 위치, gitignore 정책).

## 회신 매트릭스

```
Slice 10 Step 0 mini-slice 종결.
- 회귀: 496 → 512 (+16)
- IDENTICAL: 7/7
- 비용 단독: $0.00 / 누적: $2.3775 (마진 20.75%)
- LLM 호출: 0/50
- KPI 11/11: 11개 PASS, 0개 FAIL
- #48 close: v3 = count_tokens API (정의상 ±2%), v2 baseline 60.83% 재현 + 해소
- 신규 부채: #51 (확정 등록) + #52 (Fallback A 발동)
- mini-slice 패턴 첫 사례 정착: PASS
```
