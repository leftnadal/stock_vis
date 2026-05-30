"""Slice 9 #44 — Rationale 생성 prompt builder.

Sonnet에게 E4 답변의 4요소 충족 여부를 평가시키는 system + user prompt 구성.
"""

from __future__ import annotations

RATIONALE_SYSTEM_PROMPT = """당신은 한국 개인 투자자용 포트폴리오 코치의 답변 품질을 평가하는 평가자입니다.

## 평가 대상

다음 4요소가 답변에 포함되었는지 평가:

1. **현재 상태**: 종목별 현재가 또는 핵심 지표(PE/PEG/ROIC) 명시
2. **임계값/기준**: 정량 기준 (예: "PE 15 이상", "ROIC 10% 미만")
3. **액션 제안**: 매수/매도/보유/축소/확대 등 액션 동사 + 종목명
4. **시점/기간**: 분기/연간 또는 "최근 N개월" 명시

## 평가 출력 형식 (JSON)

```json
{
  "rationale_text": "평가 근거 (200~500자, 4요소 충족 여부 + 강점 + 약점 명시)",
  "rationale_categories": ["data_grounding", "action_clarity", "time_anchoring", "threshold_specificity"],
  "rationale_score": 5
}
```

## 평가 기준

- 5점: 4요소 모두 명확 + 정량 임계값 + 액션 직접 제시
- 4점: 4요소 중 3개 명확
- 3점: 4요소 중 2개 명확 또는 모두 약간 모호
- 2점: 4요소 중 1개만 명확
- 1점: 4요소 전혀 충족 안 됨

## 금지

- 답변 자체를 다시 쓰지 마세요 (rationale_text만 작성)
- 단어 "좋다/나쁘다" 같은 추상적 평가 금지 — 구체적 부분 인용

답변은 반드시 JSON 형식으로만 작성하세요.
"""


def build_rationale_prompt(
    case_name: str,
    original_commentary: str,
    original_question: str,
    specificity_detail: dict[str, bool],
) -> tuple[str, str]:
    """rationale 생성 prompt 구성.

    Args:
        case_name: 시나리오 이름 (예: S01_haiku)
        original_commentary: 평가 대상 답변 본문 (parsed.answer)
        original_question: 사용자 질문
        specificity_detail: P1~P5 각각의 자동 검출 결과
            (P1_metric_mention, P2_threshold, P3_action_verb, P4_quantitative, P5_time_period)

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    user_prompt = f"""## 시나리오

{case_name}

## 사용자 질문

{original_question}

## 평가 대상 답변

{original_commentary}

## 자동 patterns 검출 결과 (참고)

- P1 (현재가/지표 언급): {specificity_detail.get('P1_metric_mention', False)}
- P2 (임계값 명시): {specificity_detail.get('P2_threshold', False)}
- P3 (액션 동사): {specificity_detail.get('P3_action_verb', False)}
- P4 (구체 수치): {specificity_detail.get('P4_quantitative', False)}
- P5 (시점/기간): {specificity_detail.get('P5_time_period', False)}

## 작업

위 답변의 품질을 평가하고 rationale을 JSON 형식으로 작성하세요.
"""

    return RATIONALE_SYSTEM_PROMPT, user_prompt
