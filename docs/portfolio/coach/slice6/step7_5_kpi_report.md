# Slice 6 Part 3 Step 7.5 — KPI 자동 검증 보고서

> 실행: 자동 검증 산출

## KPI 8/8 (핵심)

| # | KPI | 결과 |
|---|---|---|
| 1 | Slice 1 e1 IDENTICAL hash | ✓ PASS |
| 2 | Slice 3 e2 IDENTICAL hash | ✓ PASS |
| 3 | 호출 카운트 11/50 (smoke 1 + matrix 10 = 11) | ✓ PASS |
| 4 | schema 10/10 (실제 10/10) | ✓ PASS |
| 5 | completeness 10/10 (실제 10/10) | ✓ PASS |
| 6 | fallback 0건 (실제 0) | ✓ PASS |
| 7 | 단건 비용 PASS (haiku ≤ $0.010, sonnet ≤ $0.030) | ✓ PASS |
| 8 | 총 비용 PASS (smoke+matrix $0.114524 ≤ $0.150) | ✓ PASS |

**KPI 8/8 전체 결과: 8/8 PASS ✓**

## 보조 KPI 9~12

### 9. label_means (cost/output 기반, manual eval은 Part 4)
- haiku avg cost: $0.004630, output 385 tokens
- sonnet avg cost: $0.017381, output 386 tokens
- cost gap (sonnet vs haiku): **+275.4%**

### 10. preset 외삽 (alignment proxy)
- haiku alignment matches: 4/5
- sonnet alignment matches: 4/5
- 분기 cases:
  - v4_concentrated_value: expected=aligned, haiku=partial, sonnet=partial

### 11. lex coverage (chars proxy)
- haiku avg chars: 580
- sonnet avg chars: 567

### 12. token usage vs budget 7000
- input P90/max: 4030 / 4030
- output P90/max: 428 / 428
- input within budget: True
- input+output_max within budget: True

## 케이스 A~G 발동

| 케이스 | 발동 | 처리 |
|---|---|---|
| A schema FAIL ≥ 1 | ✓ 미발동 | - |
| B completeness FAIL ≥ 1 | ✓ 미발동 | - |
| C fallback ≥ 1 | ✓ 미발동 | - |
| D 단건 비용 초과 | ✓ 미발동 | - |
| E 총 비용 초과 | ✓ 미발동 | - |
| F label_means 비정상 | manual eval (Part 4) | - |
| G preset 외삽 > 0.50 | manual eval (Part 4) | - |

**자동 케이스 A~E: 0/5 발동**

## IDENTICAL Hash KPI

- Slice 1 e1: `917fa3ef821426e8…` ✓ IDENTICAL
- Slice 3 e2: `5594c6ab9291213b…` ✓ IDENTICAL
