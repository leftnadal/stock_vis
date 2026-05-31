"""E4 대화 Q&A schema (Slice 7 Part 2).

Tier 1~3 multi-turn 지원. Tier 2 세션 요약은 Phase 2 (사용자 메모리 정책).
Slice 7 Part 1 step3_e4_schema_design.md 기반.

기존 `portfolio/schemas/llm_outputs.py`의 `ConversationResponse`는 초기 stub.
본 모듈은 Tier·history·metric 인용 등 multi-turn 대화에 필요한 풍부한 schema 제공.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from portfolio.schemas.commentary_output import ActionItem

# ============================================================
# Conversation Turn
# ============================================================


class E4ConversationTurn(BaseModel):
    """단일 turn (사용자 질문 또는 LLM 답변)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)
    timestamp: datetime
    turn_idx: int = Field(ge=0)


# ============================================================
# Input
# ============================================================


class E4ConversationInput(BaseModel):
    """E4 대화 진입점 입력."""

    model_config = ConfigDict(extra="forbid")

    # 포트폴리오 컨텍스트 (E3 portfolio-level과 공통)
    portfolio_id: str = Field(min_length=1)
    preset_id: str = Field(min_length=1)
    portfolio_metrics: dict[str, float]  # Core 7 portfolio 지표
    holdings_summary: str = Field(min_length=1, max_length=2000)

    # 대화 컨텍스트
    conversation_history: list[E4ConversationTurn] = Field(default_factory=list)
    current_user_question: str = Field(min_length=1, max_length=1000)
    tier: Literal[1, 2, 3]

    # 메타
    session_id: str = Field(min_length=1)
    max_history_turns: int = Field(default=5, ge=0, le=20)

    @model_validator(mode="after")
    def validate_tier_consistency(self) -> "E4ConversationInput":
        """Tier·history 일관성 검증 — I2 분기 사전 차단.

        Tier 2/3는 history가 비어있으면 ValueError (service layer에서 downgrade 처리).
        Tier 1 + history는 허용 (이전 세션 컨텍스트가 있더라도 단일 turn 응답 가능).
        """
        n_turns = len(self.conversation_history)
        if self.tier in (2, 3) and n_turns == 0:
            raise ValueError(
                f"Tier {self.tier} requires non-empty conversation_history "
                f"(use tier=1 for first turn)"
            )
        return self


# ============================================================
# Output
# ============================================================


class E4ConversationOutput(BaseModel):
    """LLM 답변."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=20, max_length=2000)

    referenced_metrics: list[str] = Field(
        default_factory=list,
        description="이 답변에서 인용한 portfolio_metrics key들",
    )
    follow_up_suggestions: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="후속 질문 추천 (Tier 2/3 활용)",
    )
    confidence: Literal["high", "medium", "low"] = "medium"
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Slice 8 Part 2 #28: LLM이 제안한 실행 가능 액션 항목 (없으면 빈 리스트).",
    )

    @model_validator(mode="after")
    def validate_referenced_metrics_format(self) -> "E4ConversationOutput":
        """referenced_metrics key 형식 검증 — I4 hallucination 사전 차단 1차.

        snake_case (공백 없음 + 소문자) 강제. portfolio_metrics와 key 형식 일관.
        실제 portfolio_metrics dict 내 존재 검증은 service layer.
        """
        for key in self.referenced_metrics:
            if not key or " " in key or key != key.lower():
                raise ValueError(f"referenced_metrics key must be snake_case: '{key}'")
        return self


# ============================================================
# Metadata (분기 케이스 trace)
# ============================================================


class E4ConversationMetadata(BaseModel):
    """E4 호출 메타데이터 — 분기 케이스 I1~I4 trace."""

    model_config = ConfigDict(extra="forbid")

    case_flags: list[Literal["I1", "I2", "I3", "I4"]] = Field(default_factory=list)
    history_truncated: bool = (
        False  # I1: max_history_turns 초과로 가장 오래된 turn 제거
    )
    tier_downgraded_from: Optional[Literal[1, 2, 3]] = (
        None  # I2: history 비어 Tier 다운그레이드
    )
    hallucinated_metrics: list[str] = Field(
        default_factory=list
    )  # I4: portfolio_metrics에 없는 key 인용
