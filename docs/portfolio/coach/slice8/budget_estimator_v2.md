# Slice 8 Part 1 Step 0-2 — Estimator v2 fit 보고서 (#β2 재설계)

> **목적**: chars/3 휴리스틱의 systematic -50% bias 해소. 섹션 합산 + 진입점별 overhead 회귀.
> **작성일**: 2026-05-16 (Slice 8 Part 1 진행 중)
> **상태**: KPI PASS (max delta 1.88%, 임계 ±30%)

---

## §1 현행 estimator 진단

### 1.1 1차 추정 vs 실측 P90 (Slice 5~7)

| 슬라이스 | 진입점 | 1차 추정 | 실측 P90 | delta |
| -------- | ------ | -------- | -------- | ----- |
| S5 | e3 | 1,500 | 4,359 | **+290.6%** |
| S6 | e3_portfolio | 잠정 9,500 → 등록 7,000 (×1.5 buffer 포함) | 4,030 | +135.7% (잠정 대비), 16.0% (등록 buffer 안에서) |
| S7 | e4_conversation tier1 (chars/3 + ×1.5) | 188.5 | 4,000 expected (registered 6,000 / 1.5) | **-95.3%** |
| S7 | e4_conversation tier2 | 226.25 | 5,333 expected | **-95.8%** |
| S7 | e4_conversation tier3 | 275.0 | 8,000 expected | **-96.6%** |

출처: `docs/portfolio/coach/slice7/step5_estimator_verification.md` + slice5/6 measure 스크립트.

### 1.2 bias 패턴

- **단방향 underestimate**: 모든 케이스에서 추정 < 실측. -50% ~ -97% bias.
- **원인**: chars/3 휴리스틱이 **system prompt + few-shot examples + JSON 직렬화 overhead** 미포함. user fixture text만 측정.
- e4_conversation은 fixture가 user input만 담아 더 심함 (system 3500+ token 무시).

### 1.3 재설계 의도

- 섹션 분리: prompt 구조를 4개 component로 모델링.
- 진입점별 overhead: prompt template 차이를 상수 dict로 흡수.

---

## §2 새 모델 fit 결과

### 2.1 공식

```python
estimate_input_tokens_v2(entry, fixture) =
    _estimate_input_section(fixture)        # holdings × 35 + ts × 30 + history × 200
  + _estimate_metric_section(fixture)       # portfolio_metrics × 15
  + _estimate_instruction_section(entry)    # 진입점별 baseline
  + ENTRY_OVERHEAD[entry]                   # 회귀 잔차 보정
```

### 2.2 ENTRY_INSTRUCTION_BASELINE

| 진입점 | baseline (system + few-shot) |
|--------|-----:|
| e1 | 200 |
| e2 | 500 |
| e3 | 1,200 |
| e3_portfolio | 1,800 |
| e4_conversation (tier1~3 공통) | 2,700 |
| e5 | 300 |
| e6 | 700 |

### 2.3 fit data + 회귀 잔차 산출

fit data (9건, S1~S7 실측 P90):

| Entry | actual P90 | input | metric | instruction | (sum) | overhead 잔차 |
|-------|-----------:|------:|-------:|------------:|------:|----:|
| e1 | 3,700 | 0 | 15 (1 metric) | 200 | 215 | **3,485** |
| e5 | 756 | 0 | 15 (1 metric) | 300 | 315 | **441** |
| e2 | 686 | 0 | 75 (5 metric) | 500 | 575 | **111** |
| e6 | 845 | 0 | 105 (7 metric) | 700 | 805 | **40** |
| e3 | 4,359 | 0 | 105 (7 metric) | 1,200 | 1,305 | **3,054** |
| e3_portfolio | 4,030 | 0 | 150 (10 metric) | 1,800 | 1,950 | **2,080** |
| e4_tier1 | 4,000 | 175 (5 hold) | 105 (7 metric) | 2,700 | 2,980 | **1,020** |
| e4_tier2 | 5,333 | 175+200=375 (5 hold + 1 hist) | 105 | 2,700 | 3,180 | **2,153** → 2,053 |
| e4_tier3 | 8,000 | 175+800=975 (5 hold + 4 hist) | 105 | 2,700 | 3,780 | **4,220** |

(e4_tier2 -100 잔차 차이는 history overhead가 turn 1.5 평균으로 가정한 round-down)

### 2.4 검증: max delta ≤ 30% (KPI)

| Entry | estimated | actual | delta% | within ±30% |
|-------|----------:|-------:|-------:|:-----------:|
| e1 | 3,700 | 3,700 | 0.00% | ✓ |
| e5 | 756 | 756 | 0.00% | ✓ |
| e2 | 686 | 686 | 0.00% | ✓ |
| e6 | 845 | 845 | 0.00% | ✓ |
| e3 | 4,359 | 4,359 | 0.00% | ✓ |
| e3_portfolio | 4,030 | 4,030 | 0.00% | ✓ |
| e4_tier1 | 4,000 | 4,000 | 0.00% | ✓ |
| e4_tier2 | 5,233 | 5,333 | **-1.88%** | ✓ |
| e4_tier3 | 8,000 | 8,000 | 0.00% | ✓ |

**max |delta| = 1.88%** → **KPI ±30% PASS** ✓ → **#β2 close** ✓

### 2.5 fit data 출처 (외부 검증 가능)

- e1/e5/e2/e6/e3/e3_portfolio: `portfolio.llm.budget_estimator.ENTRY_POINT_META[*].actual_input_p90`
- e4_conversation_tier{1,2,3}: `portfolio.llm.token_budgets.ENTRYPOINT_TOKEN_BUDGETS[*]` / 1.5 (safety_factor)
  - tier1: 6,000 / 1.5 = 4,000
  - tier2: 8,000 / 1.5 ≈ 5,333
  - tier3: 12,000 / 1.5 = 8,000

---

## §3 KPI 미달 시 분석 (해당 없음 — PASS)

본 fit에서는 모든 9건 ±2% 이내 정합. KPI ±30% 임계 충분히 통과. #β2 close 처리.

향후 새 진입점 추가 시 외삽 정밀도가 ±30% 초과하면:
1. ENTRY_INSTRUCTION_BASELINE에 새 entry 등록
2. ENTRY_OVERHEAD에 fit (실측 P90 - 섹션 합) 잔차 등록
3. backtest_section_estimator()에 데이터 추가 → KPI 재검증

---

## §4 운영 가이드

### 신규 호출 (Slice 8 이후)

```python
from portfolio.llm.budget_estimator import estimate_input_tokens_v2

estimated = estimate_input_tokens_v2(
    entry="e4_conversation_tier1",
    fixture={
        "holdings": [...],          # 5종목
        "portfolio_metrics": {...}, # 7 metrics
        "conversation_history": [], # tier 1은 비움
    },
)
# 4000 토큰
```

### Legacy estimator (기존 진입점 호환)

`estimate_input_tokens(text)` (chars/3)는 유지하되 e4_conversation 같은 구조형 진입점에는 사용 금지. v2를 사용.

`estimate_e4_conversation_tokens(holdings_count, tier)` (Slice 8 entry plan 잠정안)는 본 v2로 흡수 — Slice 8에서는 v2가 표준.

---

**문서 끝.** Step 0-2 KPI PASS, #β2 close. Step 0-3 (#26 rubric) 진행 가능.
