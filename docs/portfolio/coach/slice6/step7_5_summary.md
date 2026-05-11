# Slice 6 Part 3 → Part 4 Manual Eval 입력 자료

> 작성: 2026-05-11T03:53:41.237598+00:00
> Step 6 smoke + Step 7 매트릭스 10 cases + Step 7.5 KPI 8/8 PASS 종결.
> Part 4 manual eval 항목: winner / 글쓰기 가설 5/5 vs 4/5 / preset 외삽 robustness.

## 자동 단계 종결 상태

| 항목 | 결과 |
|---|---|
| Step 6 4판정 | 4/4 PASS ✓ (cost $0.004470) |
| Step 7 매트릭스 | 10/10 schema + completeness PASS ✓ |
| Step 7 fallback | 0건 ✓ |
| Step 7 총 비용 (smoke+matrix) | $0.114524 / $0.150 ✓ |
| Step 7.5 KPI 8/8 | PASS ✓ |
| Slice 1·3 IDENTICAL hash | 유지 ✓ |
| 자동 케이스 A~E | 0/5 발동 ✓ |

## Part 4 Manual Eval 입력 데이터

### 10 entries (naturalness/insight 1~5 사용자 입력 필요)

| # | fixture | model | output | preset_alignment_LLM | vs fixture expected |
|---|---|---|---|---|---|
| 1 | v1_concentrated_balanced | haiku | 378t | partial | ✓ |
| 2 | v1_concentrated_balanced | sonnet | 366t | partial | ✓ |
| 3 | v2_concentrated_misfit | haiku | 405t | misaligned | ✓ |
| 4 | v2_concentrated_misfit | sonnet | 428t | misaligned | ✓ |
| 5 | v3_concentrated_large | haiku | 373t | partial | ✓ |
| 6 | v3_concentrated_large | sonnet | 335t | partial | ✓ |
| 7 | v4_concentrated_value | haiku | 419t | partial | ≠ (aligned) |
| 8 | v4_concentrated_value | sonnet | 376t | partial | ≠ (aligned) |
| 9 | v5_concentrated_dividend | haiku | 351t | aligned | ✓ |
| 10 | v5_concentrated_dividend | sonnet | 427t | aligned | ✓ |

### preset_alignment 분기 cases (Part 4 정밀 분석)

- **v4_concentrated_value**: fixture expected=aligned, haiku LLM=partial, sonnet LLM=partial

> LLM이 fixture 의도와 다르게 평가한 case. Part 4에서 LLM 평가가 합리적인지 vs fixture 정의가 보수적인지 분석.

## 비용 / Token 자동 측정값

### 모델별 비용
- haiku 5건 총합: $0.023150
- sonnet 5건 총합: $0.086904
- cost gap (sonnet vs haiku): +275.4% (Slice 5 e3 ~+260% mirror)

### Token usage
- input P90 / max: 4030 / 4030 (budget 7,000)
- output P90 / max: 428 / 428
- input+output max ≤ budget: 4458 / 7,000

## Part 4 Manual Eval 진입 절차

1. `step8_2way_e3_portfolio_raw.json` 10 entry × 2 필드 (`naturalness_manual` / `insight_manual` 1~5) 사용자 입력
2. `python -m scripts.validation.score_step8 --entrypoint e3_portfolio` → scored.json 산출
3. winner 결정 (haiku vs sonnet)
4. 글쓰기 가설 5/5 정착 vs 4/5 재평가 판정
5. preset 외삽 robustness 평가 (insight 그룹차 ≤ 0.50 안전 vs > 0.50 신호)
6. Slice 5 e3 결과와 비교 (e3 종목 단위 → e3_portfolio 단위 외삽 성공도)

## 후속 Slice 6 작업

- Slice 6 Step 9 슬롯 후보 결정: **#19 LLMClient system 인자 (PS 2.0)** vs **#β2 재오픈 (PS 2.0)**
  - V4 alignment 분기로 인해 #β2 재오픈 우선순위 ↑ 가능
- 누적 광의 비용: $0.764 → **~$0.879** (smoke 0.00447 + matrix 0.11005 = $0.11452 누적)
- Slice 7 진입점 후보 평가 (현재 1순위 E4, manual eval 결과로 재검토)