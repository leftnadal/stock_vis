# Slice 7 Part 2 Step 2 — E4 Tier별 Budget 추정 근거

> **작성일**: 2026-05-11
> **등록 위치**: `portfolio/llm/token_budgets.py` `ENTRYPOINT_TOKEN_BUDGETS`
> **선결**: Slice 6 e3_portfolio P100=4,030 measurement.

---

## 추정 기반

- Slice 6 e3_portfolio P90/max input: **4,030 tokens** (reinforced builder — system + AnalysisContext dump + few-shot 4)
- 대화 turn 평균 길이 추정: **700 chars/turn** (질문 200 + 답변 500)
- token 환산: 한국어 평균 3 chars/token (`estimate_input_tokens` 기준)

---

## Tier별 산식

| Tier   | input 추정                       | 안전 마진 | 등록 budget | 근거                                       |
| ------ | -------------------------------- | --------- | ----------- | ------------------------------------------ |
| Tier 1 | 3,500 (portfolio + question)     | 1.71×     | **6,000**   | history 0 turns                            |
| Tier 2 | 4,900 (Tier 1 + 2 turns × 700)   | 1.63×     | **8,000**   | history 1~2 turns                          |
| Tier 3 | 7,000 (Tier 1 + 5 turns × 700)   | 1.71×     | **12,000**  | history 3~5 turns (max_history_turns=5)    |

- 안전 마진 ≥ 1.5× 일관: 기존 진입점 패턴 mirror (e3 7,000 / e3_portfolio 7,000도 1.5×~1.7× 적용)
- round-up 500 단위로 정합

---

## #β2 재오픈 검증 (Step 5 연동)

- Slice 6 e3_portfolio 추정 1,500 vs 실측 P100=4,030 → +366% 편차 (#β2 재오픈)
- Slice 7 Part 2 mock fixture 15 cases 평균 input × 1.5 vs 등록 budget = **±30% 이내** 검증 KPI
- 통과 시 #β2 close 가능 (Slice 8 Step 0 후보 변경)
- `scripts/slice7/verify_estimator_e4.py` 자동 수행

---

## 향후 조정 시나리오

| 시나리오                                | 처리                                                 |
| --------------------------------------- | ---------------------------------------------------- |
| Tier 3 실측 P90 > 10,000                | budget 14,000으로 상향 (round-up 500)                |
| Tier 1 실측 P90 < 3,000 (input 과소)    | prompt builder 보강 (Slice 6 minimal→reinforced mirror) |
| Tier 2/3 history 평균 turn 길이 > 1,000 | turn당 chars 가정 700 → 1,000으로 보정              |
