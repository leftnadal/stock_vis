# Slice 7 Part 1 Step 3 — E4 Conversation Schema 설계 (docs only)

> **작성일**: 2026-05-11
> **상태**: docs only — Pydantic 코드 구현은 Part 2.
> **선결 결정**: Slice 7 = E4 진입 + Step 0 #25 처리 (rubric 표준화).

---

## §1. E4 진입점 정의

**E4 = 대화 Q&A**: 사용자가 자기 포트폴리오에 대해 질문하면 LLM이 답변하는 multi-turn 대화 기능. Stock-Vis 사용자 경험을 "정적 코멘트 생성"(E1~E3) → "동적 대화"(E4)로 확장하는 6번째 글쓰기 외삽 슬라이스.

### 1.1 Tier 정의 (PRD 기반)

| Tier   | 정의                                | turn 수 | 예시                                                                       |
| ------ | ----------------------------------- | ------- | -------------------------------------------------------------------------- |
| Tier 1 | 단일 turn Q&A                       | 1       | "내 포트폴리오 집중도가 높아?" → 답변 종료                                 |
| Tier 2 | 후속 질문 (세션 단기 기억)          | 2~3     | Tier 1 답변 후 "그럼 어떻게 분산해야 해?"                                  |
| Tier 3 | 심층 분석 (세션 + 분석엔진 컨텍스트) | 3+      | 추가로 "현재 보유 종목 중 어떤 걸 줄여야 해?"                              |

**Tier 2 세션 요약 정책**: Phase 2 (사용자 메모리 정책). Slice 7 Part 1에서는 턴별 raw 컨텍스트 누적만 schema에 반영.

---

## §2. Schema 구조 (Pydantic 설계안)

구현 위치 (Part 2 예정): `portfolio/coach/schemas/e4_conversation.py`

```python
"""E4 대화 Q&A schema 설계 (Slice 7 Part 1, docs only).

Tier 1~3 multi-turn 지원. Tier 2 세션 요약은 Phase 2.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ===== Input =====

class E4ConversationTurn(BaseModel):
    """단일 turn (사용자 질문 또는 LLM 답변)."""

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    turn_idx: int = Field(ge=0)


class E4ConversationInput(BaseModel):
    """E4 대화 진입점 입력."""

    # 포트폴리오 컨텍스트 (E3 portfolio-level과 공통)
    portfolio_id: str
    preset_id: str
    portfolio_metrics: dict  # E3 portfolio Core 7 지표 재활용
    holdings_summary: str    # Top-N holdings 텍스트 요약

    # 대화 컨텍스트
    conversation_history: list[E4ConversationTurn]
    # Tier 1: 0건 / Tier 2: 1~2건 / Tier 3: 3+건
    current_user_question: str
    tier: Literal[1, 2, 3]

    # 메타
    session_id: str
    max_history_turns: int = 5  # 토큰 절약: 마지막 N 턴만 prompt에 반영


# ===== Output =====

class E4ConversationOutput(BaseModel):
    """LLM 답변."""

    answer: str = Field(min_length=20, max_length=2000)

    # tier별 추가 필드
    referenced_metrics: list[str] = Field(
        default_factory=list,
        description="이 답변에서 인용한 portfolio_metrics key들",
    )
    follow_up_suggestions: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="후속 질문 추천 (Tier 2/3에서 활용)",
    )
    confidence: Literal["high", "medium", "low"] = "medium"
```

---

## §3. Token Budget 추정 (Part 2 실측 전 보수 추정)

`portfolio/llm/token_budgets.py`에 `e4_conversation` entry 추가 예정.

| Tier   | input estimate                            | output estimate | budget 권장 (안전 마진 70%) |
| ------ | ----------------------------------------- | --------------- | --------------------------- |
| Tier 1 | ~3,500 (portfolio context + question)     | ~600            | **6,000**                   |
| Tier 2 | ~5,000 (Tier 1 + history 1~2턴)           | ~600            | **8,000**                   |
| Tier 3 | ~7,500 (history 3+턴)                     | ~800            | **12,000**                  |

**근거**:
- Slice 6 e3_portfolio P90/max input 4,030 → portfolio context 약 3,500 char
- 대화 history는 turn당 ~700 char 추정 (질문 200 + 답변 500)
- `#β2` (estimator 외삽 정밀도) 재오픈 상태이므로, Part 2에서 실측 후 재조정

---

## §4. 분기 시나리오 (E4 특수 케이스)

기존 케이스 A~E (schema/completeness/cost/token/fallback) 외 E4 추가 케이스:

| 케이스 | 조건                                                          | 처리                                              |
| ------ | ------------------------------------------------------------- | ------------------------------------------------- |
| I1     | history 턴 5개 초과 (max_history_turns 위반)                  | 가장 오래된 턴부터 제거, fallback flag set        |
| I2     | tier=2/3인데 history 비어있음                                 | Tier 1로 자동 다운그레이드, warning log           |
| I3     | answer가 history와 일관성 없음 (LLM 평가)                     | manual eval 단계에서 분기                         |
| I4     | referenced_metrics가 portfolio_metrics에 없는 key 인용         | hallucination 의심 — manual eval 분기             |

---

## §5. 글쓰기 가설 외삽 차원

| Slice | 진입점         | 외삽 차원        | 글쓰기 가설 정착 |
| ----- | -------------- | ---------------- | ---------------- |
| 1     | E1 한 줄 진단  | baseline         | ✓                |
| 2     | E5 조정 파싱   | 추출 반례        | ✓                |
| 3     | E2 4요소 카드  | preset 종류 확장 | ✓                |
| 4     | E6 비교 해설   | 다종목 비교      | ✓                |
| 5     | E3 지표 코멘트 | 종목별 지표 깊이 | ✓                |
| 6     | E3 portfolio   | 종목 → portfolio | ✓                |
| **7** | **E4 대화**    | **multi-turn**   | **검증 대상**    |

→ 6번째 외삽 차원 (turn → multi-turn). Slice 7에서 글쓰기 가설이 대화 차원에서도 유지되는지 검증.

---

## §6. Part 2 구현 체크리스트 (사전 등록)

- [ ] `portfolio/coach/schemas/e4_conversation.py` 작성 (위 Pydantic 코드)
- [ ] `portfolio/llm/token_budgets.py`에 `e4_conversation` 3 tier 등록
- [ ] mock fixture JSON 15 cases 구현 (§4 시나리오 doc 참조)
- [ ] E4 estimator 정확도 검증 (#β2 재오픈 대상)
- [ ] 회귀 +10~15 예상
- [ ] 비용 $0 (mock 단계, LLM 호출 0)
