# Slice 7 Refactor Backlog — Slice 8+ 이연

> **작성일**: 2026-05-15 (Slice 7 종결 시점)
> **누적 백로그**: Slice 5 백로그 4건 (#19~#22) + Slice 6 백로그 (#24, #β2) + Slice 7 신규 5건 (#26~#31)

---

## 처리 완료 (Slice 7 Part 4)

| ID | 항목 | 처리 |
|----|------|------|
| **#19** | LLMClient.complete `system` 인자 분리 | Part 4 §12 완료 |
| **#25** | manual_eval_rubric §B sample 표준화 | Part 4 §2 완료 |

---

## Slice 8 진입 백로그 (우선순위순)

### **#27** E4 input에 종목별 holdings 데이터 추가 (PS 3.0) ★최우선

**문제**: 현재 `portfolio_metrics`는 집계 지표(hhi, sector_hhi, top3_weight 등)만 제공. LLM이 "어떤 종목을 줄이고 늘릴지" 답할 정보 자체가 없음.

**Insight rationale 분석 (52건)**:
- **75%**가 "구체성 부족" 지적
- "어떤 종목인지, 왜 편입됐는지, 리밸런싱이 필요한지 구체적 행동 제안 부재"

**제안**:
```python
class E4ConversationInput(BaseModel):
    portfolio_metrics: dict[str, float]  # 기존
    holdings: list[Holding] = []          # 신규
    user_question: str
    ...

class Holding(BaseModel):
    symbol: str               # "AAPL"
    weight: float             # 0.30
    pe: float | None
    peg: float | None
    roic: float | None
    sector: str
    ttm_growth: float | None
```

**기대**: 모델이 "AAPL을 5% 줄이고 UNH를 10% 늘리세요" 같은 구체 권고 가능.

**진입**: Slice 8 Step 1
**회귀 영향**: +5~10 (fixture 갱신 + schema 회귀)

---

### **#28** E4 output schema에 `action_items` 강제 슬롯 (PS 3.0) ★최우선

**문제**: `E4ConversationOutput`이 `answer: str` 자유 텍스트 1필드로 통합. 모델이 구체 행동을 "추상적으로 묻어버림".

**제안**:
```python
class E4ActionItem(BaseModel):
    target: Literal["symbol", "sector", "overall"]
    target_name: str
    current_value: float          # 현재 비중 또는 지표값
    suggested_value: float
    rationale: str                # 1줄 60자
    priority: Literal["high", "medium", "low"]

class E4ConversationOutput(BaseModel):
    answer: str
    action_items: list[E4ActionItem]  # min_length=1 강제
    referenced_metrics: list[str]
    confidence: Literal["high", "medium", "low"]
```

**기대**: 모델이 구조화된 슬롯에 강제 응답 → 추상화 회피 불가.

**진입**: Slice 8 Step 2 (#27과 동시 머지 권장)
**회귀 영향**: +3~5 (schema 회귀 + Pydantic validator)

---

### **#29** E4 system prompt "출력 형식 4요소" + Sample 5 few-shot (PS 2.5)

**문제**: rubric §B.1 Sample 5 수준 = "구체 종목·변경폭·목표지표·근거 1줄" 형태이지만, prompt가 이를 요구 안 함 → **generator-evaluator gap**.

**제안**:
```
당신의 모든 권고는 반드시 다음 4요소 포함:
1. 대상 (종목 ticker 또는 sector)
2. 변경 폭 (% 단위, 명사형)
3. 목표 지표값 (예: "sector_hhi 0.35로")
4. 근거 (1줄, preset 키워드 포함)

추상적 표현 금지:
  ✗ "분산 고려"
  ✓ "Tech 50%→30%로 축소, sector_hhi 0.35 달성, GARP 균형 원칙 반영"

다음 Sample 5 수준 답변 작성:
[rubric §B.1 Sample 5 inline]
```

**기대**: Sample 3 (현재 평균 3.58) → Sample 4~5 수준으로 상향.

**진입**: Slice 8 Step 3
**회귀 영향**: 0 (prompt만, IDENTICAL hash KPI에서 e4_conversation은 제외)

---

### **#26** 분포 폭 KPI keep_open + rubric §B sample 확장 (PS 2.0)

**문제**: Slice 7 Part 4 manual eval 분포 폭 = 2 (3~5만 사용). §C.6 임계 ≥ 3.0 미달.

**제안**:
- rubric §B sample 5건 → **10건 확장**
- 양극단 (1점, 5점) sample 추가 + 사용자 평가 가이드 명시 ("1·5점 적극 사용")
- 또는 평가 form에 분포 폭 실시간 표시 (z-score 계산)

**진입**: Slice 8 Step 0
**비용 영향**: 0 (docs only)

---

### **#β2** Budget estimator systematic -50% bias 재설계 (PS 3.0) — Slice 6 이연

**문제**: estimator 1차/2차 측정 모두 max -52%, avg -49.41% (random noise 아닌 systematic bias).

**현재**: `estimated = chars / 3` 단순 휴리스틱.

**제안**:
```python
def estimate_input_tokens(prompt: str, holdings_count: int = 0) -> int:
    base = len(prompt) / 3.0
    serialization_overhead = holdings_count * 35  # JSON 직렬화 1 holding ≈ 35 token
    system_overhead = 200 if "system" in prompt.lower() else 0
    return int(base + serialization_overhead + system_overhead)
```

**진입**: Slice 8 Step 0 (#26과 함께)

---

### **#30** 2-stage generation (narrative + action 분리) (PS 1.5)

**아이디어**: #27 + #28을 했을 때 답변 길이가 폭증할 수 있음. 분리 처리:
1. Stage 1: 일반 답변 생성 (haiku)
2. Stage 2: 답변에서 `action_items` 추출 (haiku 별도, output 짧음)

**예상**: 비용 1.3× ↑, 구체성 보장

**진입**: Slice 9 후보 (Slice 8에서 #27+#28+#29 효과 검증 후)

---

### **#31** Slice 7 Tier 3 mock fixture 확장 (PS 1.0)

**문제**: Tier 3 n=6 (haiku 6, sonnet 6) → weak signal warning. 통계적 신뢰도 부족.

**제안**: V3·V4·V5에 Tier 3 fixture 4건 추가 → n=10.

**진입**: Slice 8 백로그
**회귀 영향**: +4 (fixture 회귀)

---

### **#24** preset 외삽 일반화 — Slice 6 이연 (PS 2.5)

**상태**: Slice 7 Part 1 Step 0.2에서 H3 confirmed → 진짜 신호.

**Slice 7 결과**: gap 1.0 유지 (rubric 적용 후 분포 폭 1 → 1).

**진입**: Slice 9 후보 (PSrenker 낮음 vs #27~30)

---

## 누적 PS 점수 (Slice 8 진입 분량 결정)

| 우선순위 | 항목 | PS |
|---------|------|-----|
| 1 | #27 + #28 (insight trio core) | **6.0** |
| 2 | #29 (insight trio prompt) | 2.5 |
| 3 | #β2 (estimator 재설계) | 3.0 |
| 4 | #26 (rubric 확장) | 2.0 |
| 5 | #31 (Tier 3 fixture) | 1.0 |
| **합계 (Slice 8 후보)** | | **14.5** |

→ Slice 8은 **#27~29 trio + #β2 + #26** 동시 진행 권장. **#30, #31, #24는 Slice 9로 분할**.

---

## Slice 5 백로그 (이전 → 처리 상태)

| # | 항목 | 상태 |
|---|------|------|
| #19 | LLMClient.complete `system` 인자 | ✓ Slice 7 Part 4 §12 처리 |
| #20 | concentrated_portfolio E3 별도 슬라이스 | Slice 6에서 처리 (별도 진입) |
| #21 | format_metrics_table deprecated wrapper 제거 | Slice 9 후보 |
| #22 | LLMResponse.metadata_dict 표준 정착 검증 | Slice 7에서 일관 확인 |
