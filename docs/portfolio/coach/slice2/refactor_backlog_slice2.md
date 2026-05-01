# Slice 2 Refactor Backlog

> 작성: 2026-05-01 (Step 6 실행 중 발견)
> 정책: P × R × S / C 우선순위 (참고자료 §4)

## 발견 항목

### 1. fixture `clear_decrease` holdings vs user_command 불일치

- **위치**: `portfolio/tests/fixtures/sample_adjustment_context.py`
- **현상**: user_command="TSLA 비중 좀 줄여줘"인데 holdings는 NVDA/MSFT/AAPL/GOOGL/INTC (TSLA 없음).
- **영향**: Step 6 실 호출에서 LLM이 "TSLA가 명시되지 않아"로 ambiguity_notes 작성 — 의도 매칭은 5점이지만 fixture 자체가 "clear" 케이스가 아님.
- **퀀트 평가**:
  | 차원 | 점수 | 근거 |
  | --- | --- | --- |
  | Priority (P) | 2 | Step 8 의도 매칭 평가 noise 가능성 |
  | Reusability (R) | 1 | clear_decrease 단일 fixture |
  | Severity (S) | 2 | 평가는 통과하나 의미 일관성 결여 |
  | Cost (C) | 1 | holdings 수정만 — 5분 |
  | Score | **4.0** | YES (재사용성 낮으나 cost도 낮음) |
- **권장 수정**: clear_decrease fixture의 holdings에 TSLA를 추가 (예: weight 0.20). 또는 user_command를 holdings 종목으로 교체.
- **결정 시점**: Step 8 진입 전 (Step 8에서 clear_decrease가 다시 사용됨).

---

## Step 8 진입 전 결정 항목

위 fixture 수정을 Step 8 전에 적용할지 결정 필요. Step 6은 이미 5점이라 영향 없으나 Step 8의 의도 매칭 평가에서 동일 noise가 7 fixture × 2 model = 14회 반복될 가능성.

옵션 A. Step 8 전에 fixture 수정 (5분 비용)
옵션 B. Step 8에서 평가 시 ambiguity_notes 출력은 "정상 동작"으로 간주 (fixture 미수정)

**권장: 옵션 A** — Step 8 평가 noise 차단.
