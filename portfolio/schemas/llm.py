"""
LLMResponse — LLM 호출 메타데이터 컨테이너.
E5 (조정 파싱) 입력/출력 스키마.

§1.1 확정 결정 (Slice 1): Pydantic BaseModel. 필드 추가/제거 금지.
§1 결정 (Slice 2 v2):
  - I2 — AdjustmentItem `model_validator` (action↔delta 일관성)
  - I3 — E5Response `model_validator` (intent↔adjustments 일관성)
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMResponse(BaseModel):
    text: str
    provider: Literal["gemini", "anthropic"]
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    fallback_from: Optional[Literal["gemini", "anthropic"]] = None

    def metadata_dict(self) -> dict:
        """text를 제외한 메타데이터 dict (provider/model/latency/tokens/cost/fallback)."""
        return self.model_dump(exclude={"text"})


# ============================================================
# E5 (조정 파싱) 진입점 — Slice 2
# ============================================================

AdjustmentAction = Literal["increase", "decrease", "remove", "add", "info_only"]


class AdjustmentItem(BaseModel):
    """
    단일 종목 조정. delta_weight는 음수(축소) / 양수(확대) / 0(정보용).

    I2 검증: action ↔ delta_weight ↔ target_weight 명확한 모순 거름.
    LLM 자유도 보장 위해 borderline 케이스는 통과시킴.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., min_length=1, max_length=10)
    action: AdjustmentAction
    delta_weight: Optional[float] = Field(
        None,
        ge=-1.0,
        le=1.0,
        description="포트폴리오 비중 변화량 (-1.0 ~ +1.0). action=info_only 시 None 또는 0.",
    )
    target_weight: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="명시적 목표 비중. delta_weight과 동시 지정 가능.",
    )
    reason_quote: str = Field(
        ...,
        max_length=300,
        description="사용자 자연어 명령에서 이 조정을 추출한 근거 부분 인용. 추측/의역 금지.",
    )

    @model_validator(mode="after")
    def _check_action_consistency(self) -> "AdjustmentItem":
        """action과 delta/target 명확한 모순만 거름."""
        if (
            self.action == "decrease"
            and self.delta_weight is not None
            and self.delta_weight > 0
        ):
            raise ValueError("decrease action requires delta_weight <= 0")
        if (
            self.action == "increase"
            and self.delta_weight is not None
            and self.delta_weight < 0
        ):
            raise ValueError("increase action requires delta_weight >= 0")
        if self.action == "remove" and self.target_weight not in (None, 0.0):
            raise ValueError("remove action requires target_weight None or 0")
        if self.action == "info_only":
            if self.delta_weight not in (None, 0.0):
                raise ValueError("info_only action requires no delta_weight change")
            if self.target_weight is not None:
                raise ValueError("info_only action requires no target_weight")
        return self


class E5Response(BaseModel):
    """
    조정 파싱 응답. LLM이 사용자 자연어 → 구조화 override 변환.

    I3 검증: no_actionable_intent ↔ adjustments 일관성.
    confidence ↔ ambiguity_notes 관계는 LLM 자율 판단에 맡김.
    """

    model_config = ConfigDict(extra="forbid")

    adjustments: list[AdjustmentItem] = Field(default_factory=list)
    confidence: int = Field(
        ...,
        ge=1,
        le=5,
        description="LLM이 자연어 의도를 얼마나 확실히 파악했는지 (1=불확실, 5=확실).",
    )
    ambiguity_notes: Optional[str] = Field(
        None,
        max_length=500,
        description="명령이 모호한 경우 다중 해석 메모. 명확하면 None.",
    )
    no_actionable_intent: bool = Field(
        False,
        description="자연어 명령이 조정 의도가 아닌 경우(질문/잡담) True.",
    )

    @model_validator(mode="after")
    def _check_intent_consistency(self) -> "E5Response":
        """no_actionable_intent=True인데 adjustments 비어있지 않으면 거절."""
        if self.no_actionable_intent and self.adjustments:
            raise ValueError(
                "no_actionable_intent=True but adjustments non-empty"
            )
        return self


class E5Request(BaseModel):
    """조정 파싱 요청 컨텍스트."""

    model_config = ConfigDict(extra="forbid")

    analysis_context: dict[str, Any] = Field(
        ...,
        description=(
            "AnalysisContext 또는 그 dict 형태 (holdings, metrics, "
            "analysis_summary 등). E5는 자연어 추출 작업이라 dict 그대로 받음."
        ),
    )
    user_command: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
