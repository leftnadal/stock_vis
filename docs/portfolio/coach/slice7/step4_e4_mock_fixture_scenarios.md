# Slice 7 Part 1 Step 4 — E4 Mock Fixture 시나리오 (docs only)

> **작성일**: 2026-05-11
> **상태**: 시나리오 정의 only — JSON 파일 구현은 Part 2.
> **근거**: Slice 6 매트릭스 10 cases 기반 확장 (+5 cases는 tier 2/3 multi-turn + 분기 트리거). preset 5종 cover, tier 3종 cover.

---

## §1. 시나리오 매트릭스 (15 cases)

| ID  | preset                  | tier | turn 수 | 분기 케이스         | 의도                                       |
| --- | ----------------------- | ---- | ------- | ------------------- | ------------------------------------------ |
| S1  | V1 (balanced)           | 1    | 1       | baseline            | Tier 1 단일 turn baseline                  |
| S2  | V1                      | 2    | 2       | follow-up           | Tier 2 follow-up baseline                  |
| S3  | V1                      | 3    | 3       | deep                | Tier 3 deep analysis baseline              |
| S4  | V2 (focused/misaligned) | 1    | 1       | baseline            | misalignment 단일 turn                     |
| S5  | V2                      | 2    | 2       | follow-up           | misalignment follow-up                     |
| S6  | V3 (factor)             | 1    | 1       | baseline            | factor preset 단일 turn                    |
| S7  | V3                      | 2    | 2       | follow-up           | factor preset follow-up                    |
| S8  | V4 (concentrated_value) | 1    | 1       | baseline (G6 관찰)  | V4 alignment 단일 turn                     |
| S9  | V4                      | 2    | 2       | follow-up (#23 영향) | V4 alignment follow-up                     |
| S10 | V5 (aligned)            | 1    | 1       | baseline            | aligned baseline                           |
| S11 | V5                      | 3    | 3       | deep                | aligned deep analysis                      |
| S12 | V1                      | 2    | 6       | **I1 trigger**      | history overflow (max_history_turns 초과) |
| S13 | V1                      | 2    | 0       | **I2 trigger**      | empty history downgrade                    |
| S14 | V2                      | 3    | 4       | **I4 후보**         | metrics inconsistent (hallucination 의심) |
| S15 | V3                      | 1    | 1       | confidence=low 분기 | LLM 자신도 낮음 시나리오                   |

**Cover 분석**:
- preset cover: V1 (S1·S2·S3·S12·S13), V2 (S4·S5·S14), V3 (S6·S7·S15), V4 (S8·S9), V5 (S10·S11) — **5/5 ✓**
- tier cover: Tier 1 (S1·S4·S6·S8·S10·S15), Tier 2 (S2·S5·S7·S9·S12·S13), Tier 3 (S3·S11·S14) — **3/3 ✓**
- 분기 트리거: I1 (S12), I2 (S13), I4 (S14), confidence=low (S15) — **4종 cover**

---

## §2. Fixture 파일 구조 (Part 2 구현 대상)

```
portfolio/tests/fixtures/portfolio/e4_conversation/
├── S01_V1_tier1.json                    # baseline
├── S02_V1_tier2.json                    # follow-up
├── S03_V1_tier3.json                    # deep
├── S04_V2_tier1.json                    # misalignment baseline
├── S05_V2_tier2.json                    # misalignment follow-up
├── S06_V3_tier1.json                    # factor baseline
├── S07_V3_tier2.json                    # factor follow-up
├── S08_V4_tier1.json                    # aligned (G6 관찰)
├── S09_V4_tier2.json                    # aligned follow-up
├── S10_V5_tier1.json                    # dividend baseline
├── S11_V5_tier3.json                    # dividend deep
├── S12_V1_tier2_history_overflow.json   # I1 trigger
├── S13_V1_tier2_empty_history.json      # I2 trigger
├── S14_V2_tier3_metrics_inconsistent.json # I4 후보
└── S15_V3_tier1_low_conf.json           # confidence=low
```

### 2.1 단일 fixture JSON 구조

```json
{
  "scenario_id": "S01",
  "preset_label": "V1",
  "tier": 1,
  "input": {
    "portfolio_id": "test_v1_balanced",
    "preset_id": "garp",
    "portfolio_metrics": { /* E3 portfolio Core 7 */ },
    "holdings_summary": "MSFT(30%), NVDA(20%), AAPL(15%), GOOG(20%), META(15%)",
    "conversation_history": [],
    "current_user_question": "내 포트폴리오 집중도가 높은 편이야?",
    "tier": 1,
    "session_id": "sess_S01",
    "max_history_turns": 5
  },
  "expected_output": {
    "answer": "...",
    "referenced_metrics": ["sector_concentration", "diversification_score"],
    "follow_up_suggestions": ["분산을 어떻게 늘릴까?", "리밸런싱 우선순위?"],
    "confidence": "high"
  },
  "expected_branch_case": null    // 또는 "I1" | "I2" | "I3" | "I4"
}
```

### 2.2 분기 트리거 fixture 특이사항

| ID  | 특이사항                                                                |
| --- | ----------------------------------------------------------------------- |
| S12 | `conversation_history`에 6턴 (max 5 초과) → 가장 오래된 턴 제거 검증    |
| S13 | `tier=2`인데 `conversation_history=[]` → Tier 1 다운그레이드 검증       |
| S14 | `referenced_metrics`에 portfolio_metrics에 없는 key 인용 → I4 manual eval |
| S15 | `confidence="low"` 명시 + answer가 짧고 hedging 표현                    |

---

## §3. 글쓰기 가설 검증 매트릭스 (Part 3 진입 시)

각 fixture × {haiku, sonnet} = 30 cases (15 × 2) 실측 예정. gemini 제외 (Slice 1 9/9 폴백 후 매트릭스 일관 제외 정책).

| 평가 차원         | 측정 방법                                          |
| ----------------- | -------------------------------------------------- |
| Schema 준수율     | Pydantic parse PASS / Total                        |
| Tier 일관성       | 답변이 tier에 맞는 깊이 유지 (Tier 1 짧음, 3 깊음) |
| Metric 인용 정확도 | referenced_metrics가 portfolio_metrics 내 존재     |
| Follow-up 품질    | follow_up_suggestions가 실제로 후속 질문스러운가   |
| 분기 케이스 처리  | I1·I2·I4 트리거가 expected_branch_case와 일치       |

---

## §4. 비용 추정 (Part 3 진입 시)

- Tier 1 단건: haiku $0.005 / sonnet $0.020
- Tier 2 단건: haiku $0.008 / sonnet $0.030
- Tier 3 단건: haiku $0.012 / sonnet $0.045
- 매트릭스 15 cases × 2 model = 평균 $0.32~0.42

→ COST_POLICY 갱신 임계 $1.50 대비 약 21~28% 점유 (단일 슬라이스). 임계 내 안전.

---

## §5. Part 2 구현 체크리스트 (사전 등록)

- [ ] fixture JSON 15건 작성 (S01~S15)
- [ ] expected_output은 schema valid (Pydantic parse PASS)
- [ ] 분기 트리거 fixture (S12·S13·S14·S15) 메타 정합
- [ ] tier별 길이 제약 검증 (Tier 1 ≤ 500 chars, Tier 3 ≤ 2000)
- [ ] cover 매트릭스 자동 검증 테스트 (preset 5/5, tier 3/3)
