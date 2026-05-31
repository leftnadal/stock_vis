"""E4 대화 Q&A prompt builder (Slice 7 Part 3 §2).

Tier 1/2/3 multi-turn 지원. system prompt + portfolio context +
conversation history + current question 조합.

LLMClient.complete은 단일 prompt string을 받으므로, build_e4_prompt가
system + user 합성 결과를 반환한다. build_e4_messages는 향후 #19
(LLMClient system 인자 별도 처리) 처리 시 사용할 messages 배열 형태.
"""

from __future__ import annotations

from portfolio.schemas.e4_conversation import E4ConversationInput
from portfolio.services._prompt_helpers import format_metrics_to_str

SYSTEM_PROMPT = """당신은 한국 개인 투자자를 위한 포트폴리오 코치입니다.
사용자의 포트폴리오 지표와 종목 구성을 바탕으로, 사용자의 질문에
간결하고 통찰력 있게 답변하세요.

답변 원칙:
1. 포트폴리오 지표(hhi_concentration, sector_hhi 등)를 의미 있게 인용하세요.
2. preset 의도(예: GARP=합리적 가격 성장, dividend_growth=안정 배당)를 반영하세요.
3. 단순 사실 나열보다 행동 시사점(예: 리밸런싱 검토)을 제시하세요.
4. multi-turn 대화에서는 이전 turn의 맥락을 고려하세요.
5. 반드시 JSON 형식 하나만으로 응답하세요 (마크다운 펜스 금지).

응답 JSON schema (E4ConversationOutput):
{
  "answer": "답변 본문 (한국어 20~2000자)",
  "referenced_metrics": ["인용한 portfolio_metrics key (snake_case)"],
  "follow_up_suggestions": ["후속 질문 추천 (최대 3개)"],
  "confidence": "high | medium | low"
}
"""


def _truncate_history(inp: E4ConversationInput) -> list:
    """I1 trigger 대응 — history 길이가 max_history_turns 초과 시 가장 오래된 turn 제거."""
    history = inp.conversation_history
    if len(history) > inp.max_history_turns:
        return history[-inp.max_history_turns :]
    return history


def build_e4_user_prompt(inp: E4ConversationInput) -> str:
    """E4 user message 본문 — portfolio context + (truncated) history + 질문."""
    history = _truncate_history(inp)
    metrics_str = format_metrics_to_str(inp.portfolio_metrics, format="markdown")

    parts: list[str] = [
        "## 포트폴리오 정보",
        f"- portfolio_id: {inp.portfolio_id}",
        f"- preset: {inp.preset_id}",
        f"- tier: {inp.tier}",
        "",
        "## 포트폴리오 지표",
        metrics_str,
        "",
        "## 보유 종목 요약",
        inp.holdings_summary,
        "",
    ]

    if history:
        parts.append("## 이전 대화")
        for turn in history:
            role_label = "사용자" if turn.role == "user" else "어시스턴트"
            parts.append(f"[{role_label}] {turn.content}")
        parts.append("")

    parts.extend(
        [
            "## 현재 질문",
            inp.current_user_question,
            "",
            "위 정보를 바탕으로 JSON 형식 하나만으로 답변하세요.",
        ]
    )
    return "\n".join(parts)


def build_e4_prompt(inp: E4ConversationInput) -> str:
    """LLMClient.complete에 전달할 단일 prompt string.

    system + user 합성. #19 처리 후 LLMClient가 system 인자 분리 지원 시
    build_e4_messages 경로로 전환 예정.
    """
    return SYSTEM_PROMPT + "\n\n" + build_e4_user_prompt(inp)


def build_e4_messages(inp: E4ConversationInput) -> list[dict]:
    """messages 배열 형태 (#19 처리 후 사용 예정).

    현재 LLMClient.complete은 단일 string만 받으므로, 본 함수는 향후 인프라
    확장 대비 + 단위 테스트용.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_e4_user_prompt(inp)},
    ]


def get_system_prompt() -> str:
    """system prompt 반환 (#19 처리 시 LLMClient에 별도 전달용)."""
    return SYSTEM_PROMPT


# ============================================================
# Slice 8 Part 3 #29 — V2: 출력 4요소 강제 + Sample 5 few-shot
# ============================================================

SYSTEM_PROMPT_V2_TEMPLATE = """당신은 한국 개인 투자자를 위한 포트폴리오 코치입니다.

## 답변 작성 규칙 (필수)

모든 답변은 다음 4요소를 반드시 포함해야 합니다:

1. **현재 상태**: 언급하는 종목의 현재가 또는 핵심 지표(PE / PEG / ROIC) 중 1개 이상 명시
2. **임계값/기준**: 판단 근거가 되는 정량 기준 (예: "PE 15 이상", "ROIC 10% 미만") 명시
3. **액션 제안**: 매수/매도/보유/축소/확대 중 하나를 종목명과 함께 직접 제시
4. **시점/기간**: 분기/연간 또는 "최근 N개월" 등 시점 정보 1회 이상 인용

## 금지 사항

- "일반적으로", "보통", "대체로" 등 추상적 표현으로만 답변 마무리하지 마세요.
- 종목명 없이 "포트폴리오가 위험합니다" 같은 일반론 금지.
- 액션 없이 분석만 제시하고 마무리 금지.

## 답변 예시 (Sample 5 few-shot)

{few_shot_samples}

## 응답 형식

반드시 JSON 형식 하나만으로 응답하세요 (마크다운 펜스 금지).

응답 JSON schema (E4ConversationOutput):
{{
  "answer": "위 4요소를 포함한 자연어 답변 (한국어 200~2000자)",
  "referenced_metrics": ["인용한 portfolio_metrics key (snake_case)"],
  "follow_up_suggestions": ["후속 질문 추천 (최대 3개)"],
  "confidence": "high | medium | low",
  "action_items": [
    {{"title": "간결한 액션 제목", "description": "근거 포함 설명", "priority": "high|medium|low"}}
  ]
}}
"""


def _format_few_shot_sample(sample: dict) -> str:
    """Sample 1건을 few-shot 포맷으로 변환."""
    action_lines = "\n".join(
        f"  - {a['title']} ({a['priority']}): {a['description']}"
        for a in sample.get("action_items", [])
    )
    return (
        f"### 예시: {sample['title']}\n"
        f"[질문] {sample['question']}\n"
        f"[답변] {sample['answer']}\n"
        f"[액션 항목]\n{action_lines}"
    )


def build_v2_system_prompt(few_shot_samples: list[dict] | None = None) -> str:
    """Slice 8 Part 3 #29 — V2 system prompt 구성 (4요소 강제 + few-shot 삽입).

    Args:
        few_shot_samples: Sample 5 few-shot. None이면 DEFAULT_FEW_SHOT_SAMPLES 사용.

    Returns:
        4요소 지시 + few-shot이 삽입된 system prompt.
    """
    if few_shot_samples is None:
        from portfolio.prompts.e4.samples import DEFAULT_FEW_SHOT_SAMPLES

        few_shot_samples = DEFAULT_FEW_SHOT_SAMPLES

    few_shot_text = "\n\n---\n\n".join(
        _format_few_shot_sample(s) for s in few_shot_samples
    )
    return SYSTEM_PROMPT_V2_TEMPLATE.format(few_shot_samples=few_shot_text)


def build_e4_prompt_v2(
    inp: E4ConversationInput,
    few_shot_samples: list[dict] | None = None,
) -> str:
    """Slice 8 Part 3 #29 — V2 prompt (4요소 강제 + Sample 5 few-shot).

    기존 build_e4_prompt와 시그니처 호환 (E4ConversationInput 객체 기반).
    Part 3 신규 호출자(Step 6 smoke / Step 7 matrix)는 본 함수 사용 권장.

    Args:
        inp: E4ConversationInput (holdings / metrics / history / question).
        few_shot_samples: Sample 5 few-shot. None이면 DEFAULT_FEW_SHOT_SAMPLES.

    Returns:
        V2 system + user 합성 단일 prompt string.
    """
    system_v2 = build_v2_system_prompt(few_shot_samples)
    user = build_e4_user_prompt(inp)
    return system_v2 + "\n\n" + user


def build_e4_messages_v2(
    inp: E4ConversationInput,
    few_shot_samples: list[dict] | None = None,
) -> list[dict]:
    """V2 messages 배열 형태 (LLMClient system 인자 분리 시 사용)."""
    return [
        {"role": "system", "content": build_v2_system_prompt(few_shot_samples)},
        {"role": "user", "content": build_e4_user_prompt(inp)},
    ]


def get_v2_system_prompt(few_shot_samples: list[dict] | None = None) -> str:
    """V2 system prompt 반환 (LLMClient에 별도 전달용)."""
    return build_v2_system_prompt(few_shot_samples)
