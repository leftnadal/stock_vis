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
