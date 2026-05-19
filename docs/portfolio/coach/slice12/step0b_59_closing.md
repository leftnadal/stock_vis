# Slice 12 Step 0b 종결 — #59 E3 action measurability prompt 보강

**작업명**: E3PromptBuilder action_items 작성 규칙 4종 명시 + micro-matrix 검증
**브랜치**: `slice12`
**작업일**: 2026-05-20
**비용**: $0.0554 (4 케이스 LLM)

---

## §1. Prompt 보강 요약

### 신규 `_E3_ACTION_RULES` 블록 (E3PromptBuilder 안에 명시)

4종 규칙:
1. **구체성 필수** — ticker / 정량 지표 / 비율 중 하나 이상
2. **측정 가능성 필수** — 목표 수치 / 기한 중 하나 이상
3. **금지 패턴** — "모니터링 필요/검토하세요/주시하세요" 단독 사용 금지
4. **priority 정합성** — high(즉각) / medium(분기) / low(장기 + 임계 명시)

### 단위 테스트 3/3 PASS
- `test_e3_prompt_includes_action_rules_header`
- `test_e3_prompt_forbids_single_monitor_phrases`
- `test_e3_prompt_priority_consistency_rules`

---

## §2. Micro-Matrix 결과 (4 케이스)

| # | model  | rep | fit | n_items | NG/OK actions | case actn | cost      | latency |
| - | ------ | --- | --- | ------- | ------------- | --------- | --------- | ------- |
| 1 | haiku  | #1  | P   | 3       | 0/3           | **OK**    | $0.00666  | 11863ms |
| 2 | sonnet | #1  | P   | 3       | 0/3           | **OK**    | $0.02227  | 21197ms |
| 3 | haiku  | #2  | P   | 3       | 0/3           | **OK**    | $0.00647  | 11576ms |
| 4 | sonnet | #2  | P   | 3       | 0/3           | **OK**    | $0.02003  | 21091ms |

### 핵심 지표
- **schema fitting**: **4/4 PASS** (Slice 12 #58 보강 효과 — Slice 11 매트릭스 1/24 FAIL 없음)
- **NG ratio**: **0.0%** (Slice 11 Part 5 baseline 50% → 운영 기준 < 30% 압도적 충족)
- 총 action_items: 12개 (3개 × 4 케이스), 12개 모두 OK
- 총 비용: $0.0554

### 자동 NG 판정 휴리스틱
- 구체성: ticker 인용 또는 정량 지표/비율 인용
- 측정 가능성: 수치/기한 키워드 (정규식 매칭)
- 금지 패턴: "모니터링 필요/검토하세요/주시하세요" 단독 사용 시 NG 신호
- 3 조건 점수 ≥ 2 → OK, < 2 → NG

---

## §3. #59 close 판정

| 조건                     | 측정             | 기준          | 결과 |
| ------------------------ | ---------------- | ------------- | ---- |
| NG ratio 운영 기준       | **0.0%**         | < 30%         | PASS |
| 매트릭스 case 모두 OK    | 4/4 OK           | 4/4           | PASS |
| 단위 테스트              | 3/3 PASS         | 3/3           | PASS |
| schema fitting           | 4/4 PASS         | 4/4           | PASS |

**#59 → close 확정**

---

## §4. Before vs After

| 측정                | Slice 11 Part 5 (Before) | Slice 12 Step 0b (After) | 개선 |
| ------------------- | ------------------------ | ------------------------- | ---- |
| E3 NG ratio         | **50%** (2/4)            | **0%** (0/4)              | -50%p |
| schema fitting      | 3/4 PASS                 | 4/4 PASS                  | +25%p |
| 평균 action_items   | 2~3개                    | 3개                       | 안정 |
| 측정 가능 수치 인용 | 일부                     | 100%                      | 압도적 |

---

## §5. 사용자 영향

| 영역                       | 변화                                                                                                |
| -------------------------- | --------------------------------------------------------------------------------------------------- |
| **앱 사용자 UX (E3 진단)** | "비중 조정 검토" 추상 → "소비재 35% → 25% 축소 (현재 분기 리밸런싱 시)" 구체로 100% 개선           |
| **prompt 신뢰성**          | E3 진단 코멘트의 actionability NG 0% 달성, 사용자 즉시 행동 가능                                   |
| **회귀**                   | 단위 테스트 +3 추가, 기존 prompt builder 12건 회귀 영향 0                                          |

---

## §6. KPI

| #   | KPI                                | 측정값 | 기대값  | PASS/FAIL |
| --- | ---------------------------------- | ------ | ------- | --------- |
| 0b-1 | E3PromptBuilder action 규칙 명시   | O      | O       | PASS      |
| 0b-2 | 단위 테스트 +3                     | 3      | 3       | PASS      |
| 0b-3 | E3 micro-matrix 4 케이스 실행      | 4/4    | 4/4     | PASS      |
| 0b-4 | NG ratio < 30%                     | 0.0%   | < 30%   | PASS      |
| 0b-5 | #59 close                          | close  | close   | PASS      |
| 0b-6 | 매트릭스 비용                      | $0.0554 | < $0.50 | PASS      |
