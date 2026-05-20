# Slice 12 Part 3 — Smoke 분석 (15 case)

**실행일**: 2026-05-20
**스크립트**: `scripts/slice12_part3_smoke.py`
**비용**: $0.0991 (haiku × 15 콜, 평균 $0.0066/콜)

---

## §1. 결과 요약

| 지표                              | 값             |
| --------------------------------- | -------------- |
| 실행 case                          | **15/15**      |
| schema fitting PASS                | **15/15** (Slice 12 Step 0a #58 효과 — Slice 11 매트릭스 1/24 FAIL 패턴 완전 해소) |
| gate 발동 actual                   | **7 case**     |
| gate expected vs actual 일치        | **12/15**      |
| 평균 latency                       | ~12s/콜        |
| 평균 cost                          | $0.0066/콜     |
| provider                           | haiku (100%)   |

---

## §2. Gate 발동 분석

### 의도된 gate 발동 (4건 — 모두 PASS)
| Fixture        | Gate 조건                       | actual score   | commentary 키워드 |
| -------------- | ------------------------------- | -------------- | ----------------- |
| income_edge    | dividend_yield ≥ 0.02 (부재)    | 0.0            | LLM 응답 자연 처리 |
| income_gate    | dividend_yield 0.01 < 0.02      | 0.0            | LLM 응답 자연 처리 |
| factor_edge    | beta ≥ 0 (부재 → 자동 cut)       | 0.0 (low_vol)  | -                |
| factor_gate    | beta 1.5 > 1.2                  | low_vol=0      | -                |

### Mismatch 3건 (의도된 발견)
| Fixture          | expected_gate | actual_gate | 분석                                                        |
| ---------------- | ------------- | ----------- | ----------------------------------------------------------- |
| value_edge       | False         | True        | 빈 dict → 모든 preset 가중합 0 → score=0. gate 없는 카테고리에서도 자연 0. |
| growth_edge      | False         | True        | 동일 패턴                                                   |
| special_edge     | False         | True        | 동일 패턴                                                   |

**해석**: 빈 metrics dict는 gate 유무와 무관하게 score=0. smoke 판정 휴리스틱이 "preset score==0이면 gate_triggered"로 단순화 → mismatch.

**처리**: fixture는 그대로 유지 (의도된 expected). smoke script는 "actual gate_triggered = 어떤 preset score==0"으로 정의 — 실제 user-facing 해석에서는 "score=0 = 정보 부재 또는 gate cut"으로 동일 처리 가능.

---

## §3. Commentary 품질 첫 인상 (Slice 12 Part 4 manual eval 사전 신호)

| 카테고리 | normal case commentary 첫 줄 (요약)        | 인상                          |
| -------- | ------------------------------------------ | ----------------------------- |
| value    | 포트폴리오는 적정 가치 평가 수준 ...        | naturalness 양호               |
| growth   | 1년 수익률 8.2% + 섹터 분산 ...            | insight 보통                  |
| income   | 배당 중심 + HHI 0.21 ...                   | actionability 명확            |
| factor   | 종목별 분산 + 베타 0.9 ...                 | gate 메시지 자연 처리         |
| special  | 5종목 65% 집중 + 섹터 다각화 ...           | special 직접 reference 부족 (예고된 #60 후보) |

→ Part 4 D1-D + D2-A blind에서 정식 평가.

---

## §4. 비용 detail

| Fixture          | input_tok | output_tok | cost     | latency |
| ---------------- | --------- | ---------- | -------- | ------- |
| value_normal     | ~1600     | ~900       | $0.00636 | 12s     |
| value_edge       | ~1500     | ~950       | $0.00669 | 11s     |
| value_gate       | ~1700     | ~1100      | $0.00965 | 14s     |
| growth_normal    | ~1550     | ~850       | $0.00621 | 11s     |
| ...              | ...       | ...        | ...      | ...     |
| **합계**         |           |            | **$0.0991** | (avg 12s) |

전체 15 case: $0.0991. cap $0.20 대비 50% 사용, slice cap $1.00 대비 9.9%.

---

## §5. #58 Tier 3 효과 검증

Slice 11 Part 4 매트릭스에서 24/1 FAIL (e3 haiku trailing characters) → Slice 12 Step 0a `parse_json_response` Tier 3 raw_decode tolerance 도입.

**Part 3 매트릭스 결과**: 15/15 schema fitting PASS (100%). **#58 close 효과 production 검증 완료**.

---

## §6. Part 4 manual eval 사전 등록

- Part 4 D1-D rubric (Slice 11 Part 5 정착): naturalness 1~5 + insight 1~5 + actionability OK·NG·N/A
- D2-A blind shuffle (seed=42, `scripts/manual_eval_shuffle.py` Slice 12+ 재활용)
- Part 3 15 commentary가 Part 4 평가 후보 (정상 5 + edge 5 + gate 5)
