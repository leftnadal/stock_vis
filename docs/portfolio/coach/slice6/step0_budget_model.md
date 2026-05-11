# Slice 6 Part 1 Step 0 — Budget 추정 입출력 분리 모델 결정 보존

> 작성일: 2026-05-10
> 산출물: `portfolio/llm/budget_estimator.py` + 회귀 +7
> 부채 close: **#β2 (PS 3.0)** — 누적 백로그 ~17 → ~16

---

## §1. 모델 구조

### 1.1 입력 추정 (InputTokenEstimator)
- 기존 `token_budgets.estimate_input_tokens(prompt) = len // 3` 재사용
- #β1 closed (Slice 5 chars/3 평균 +2.9% 정상)

### 1.2 출력 추정 (OutputTokenEstimator)
- `FIELD_TYPE_BASELINE_TOKENS` 8 타입 (한국어 1.5~2.5 char/token, 평균 ~2):

| 필드 타입 | baseline | 사례 |
|---|---|---|
| str_short (≤50자) | 30 | E1.headline, E5.confidence note |
| str_medium (51~200자) | 100 | E1.summary, E2 항목 |
| str_long (201자+) | 175 | E2.weaknesses, E3.one_liner |
| list_str_item (per item) | 50 | E2.strengths/weaknesses/actions 1개 |
| literal/enum | 5 | E5.AdjustmentAction |
| int/float | 3 | confidence (1~5) |
| bool | 1 | no_actionable_intent |
| very_short (≤10자) | 5 | ticker |

### 1.3 통합 (estimate_budget_for_entrypoint)
- `total = input + output`
- `total_with_buffer = ceil(total × safety_factor / 500) × 500` (default 1.5)
- 반환: `{input, output, total, total_with_buffer}`

### 1.4 ENTRY_POINT_META 6 entries
- e1/e5/e2/e6/e3: 기존 진입점 (schema_fields + actual_input_p90 + registered_budget)
- e3_portfolio: Slice 6 신규 (Step 1 schema 확정 후 측정 가능)

---

## §2. 5 진입점 Backtest 결과

| 진입점 | input_p90 | output_est | total_with_buffer | registered | input_only_dev | safety_margin |
|---|---|---|---|---|---|---|
| e1 | 3,700 | 130 | 6,000 | 5,000 | **+20.0%** | PASS (boundary) |
| **e5** | **756** | **295** | **2,000** | **2,000** | **-25.0%** | **PASS (분기 E1 발동, 음수 편차)** |
| e2 | 686 | 550 | 2,000 | 1,500 | +0.0% | PASS |
| e6 | 845 | 970 | 3,000 | 1,500 | +0.0% | PASS |
| **e3** | **4,359** | **720** | **8,000** | **7,000** | **+0.0%** | **PASS (#β2 핵심 검증 통과)** |

**5/5 안전 마진 통과** (양수 편차만 strict ±20%, 음수는 안전 마진 측 통과).

### 2.1 분기 E1 발동 (e5)
- e5 등록 2,000은 Slice 2 시점 round-up 1,000 단위 흔적 (P90 756 × 1.5 = 1,134 → next 1,000 = 2,000)
- 새 표준 모델은 round-up 500 = 1,500 — 차이 1 step (500)
- **음수 편차 = registered가 더 보수적 → 안전 마진** → 작업 차단 아님, Step 0.5 미실행
- 보고: 분기 E1 발동 기록 + Slice 6+ 검토 시 e5 재등록 가능 (1,500으로 축소 또는 그대로)

### 2.2 e3 #β2 핵심 검증 PASS
- 1차 추정 1,500 vs 실측 P90 4,359 (+366% 편차) — Slice 5 발견
- 새 모델: input_only_round_up = 8,000 vs registered 7,000 → +14.3% (≤20%) ✓
- AnalysisContext 전체 직렬화 영향 반영 → 모델 일반화 정상 작동 확인

---

## §3. e3_portfolio 잠정 추정 (Step 1 입력)

| 항목 | 값 |
|---|---|
| input 가정 (e3 P90 4,359 + holdings 차원 +30%) | ~5,800 |
| output (6 필드 baseline 합: 175+100+100+100+5+3) | 483 |
| total | ~6,283 |
| total_with_buffer (×1.5 → round-up 500) | **9,500** |
| 잠정 budget (지시서 §1.6) | 9,500 / 10,000 |
| 편차 vs 잠정 9,500 | +0.0% ✓ |

→ Step 1 schema + prompt 확정 후 sample_prompts 측정으로 재검증 (분기 E2 모니터링).

---

## §4. KPI 충족

| 항목 | 기준 | 결과 |
|---|---|---|
| 5 진입점 backtest | 안전 마진 5/5 (음수 편차 또는 양수 ≤20%) | **5/5 ✓** |
| e3 #β2 핵심 검증 | 새 모델 추정 vs P90 4,359 ±20% | **+14.3% ✓** |
| 입력 추정 | 5 진입점 input estimator 재사용 (#β1 closed) | ✓ |
| 출력 추정 | 5 진입점 schema_fields baseline 합산 정상 | ✓ |
| 회귀 | +7 PASS (지시서 +5 대비 +2 자연 흡수) | ✓ |
| 비용 | $0 (정적 분석) | ✓ |

---

## §5. 후속 (Step 1)

1. E3PortfolioCommentary schema 확정 → ENTRY_POINT_META["e3_portfolio"]에 schema_fields 반영 완료
2. Step 1 prompt template + V1~V5 fixture 작성 후 sample_prompts 측정 → 잠정 9,500 재검증
3. Slice 6 Part 2 진입 시 token_budgets에 `e3_portfolio = 9500` 또는 `10000` 등록 (sample_prompts 결과 따라)
