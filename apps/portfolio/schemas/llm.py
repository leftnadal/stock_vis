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

from apps.portfolio.schemas.commentary_output import ActionItem


class LLMResponse(BaseModel):
    text: str
    provider: Literal["gemini", "anthropic"]
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    fallback_from: Optional[Literal["gemini", "anthropic"]] = None
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Slice 8 Part 2 #28: LLM이 제안한 실행 가능 액션 항목 (없으면 빈 리스트).",
    )

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
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Slice 8 Part 2 #28: LLM이 제안한 실행 가능 액션 항목 (없으면 빈 리스트).",
    )

    @model_validator(mode="after")
    def _check_intent_consistency(self) -> "E5Response":
        """no_actionable_intent=True인데 adjustments 비어있지 않으면 거절."""
        if self.no_actionable_intent and self.adjustments:
            raise ValueError("no_actionable_intent=True but adjustments non-empty")
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


# ============================================================
# E2 (진단 카드 4요소) 진입점 — Slice 3
# ============================================================


class E2DiagnosticCard(BaseModel):
    """E2 출력: 진단 카드 4요소 (D-3, Slice 3).

    네이밍 — 기존 portfolio/schemas/diagnostic.py의 단일-약점 DiagnosticCard와
    이름 충돌 회피. Slice 3 E2 진입점의 4요소 카드는 E2DiagnosticCard로 분리.
    legacy DiagnosticCard는 weakness 카드용으로 그대로 유지.

    completeness 자동 측정 (Q3.C):
    - 4개 필드 모두 존재 + 최소 길이 충족 → schema 통과
    - schema_pass = completeness_auto = True

    필드별 최소 길이는 Step 7 토큰 측정 후 조정 가능.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description="포트폴리오 요약 (1~2문장).",
    )
    strengths: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="강점 항목 1~5개. 각 항목 10자 이상.",
    )
    weaknesses: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="약점 항목 1~5개. 각 항목 10자 이상.",
    )
    actions: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="제안 액션 1~5개. 각 항목 10자 이상.",
    )

    @model_validator(mode="after")
    def check_item_min_length(self):
        """리스트 항목 최소 길이 — completeness 자동 측정 보강."""
        for field_name in ("strengths", "weaknesses", "actions"):
            items = getattr(self, field_name)
            for i, item in enumerate(items):
                if len(item) < 10:
                    raise ValueError(
                        f"{field_name}[{i}] is too short: {len(item)} chars (min 10)"
                    )
        return self


class E2Request(BaseModel):
    """E2 입력: AnalysisContext (Tier 1 분석 결과)."""

    model_config = ConfigDict(extra="forbid")

    analysis_context: dict[str, Any] = Field(
        ...,
        description=(
            "AnalysisContext dict (preset_id, holdings, metrics, analysis_summary). "
            "E2는 글쓰기 작업이라 자연어 명령 없음 — context만 입력."
        ),
    )
    session_id: Optional[str] = None


class E2Response(BaseModel):
    """E2 응답 wrapper. E2DiagnosticCard 본체 + preset 메타."""

    model_config = ConfigDict(extra="forbid")

    card: E2DiagnosticCard
    preset_id: str = Field(..., description="입력 preset 식별 (garp, buffett 등)")
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Slice 8 Part 2 #28: LLM이 제안한 실행 가능 액션 항목 (없으면 빈 리스트).",
    )


# ============================================================
# E6 (조정 후 비교 해설) 진입점 — Slice 4
# ============================================================


class E6Request(BaseModel):
    """E6 입력. E5 결과(adjustments)와 원본 AnalysisContext를 함께 받는다.

    분석 엔진 재계산 의존성 회피 — 조정 후 AnalysisContext를 _수치적으로_ 다시
    계산하지 않고, 원본 + adjustments를 LLM에 그대로 전달하여 자연어 추론으로만
    비교 해설을 수행한다 (Phase 2에서 재계산 엔진 별도 슬라이스 추가 예정).
    """

    model_config = ConfigDict(extra="forbid")

    analysis_context: dict[str, Any] = Field(
        ...,
        description="원본 AnalysisContext dict (조정 *전* 상태).",
    )
    adjustments: list[AdjustmentItem] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="E5 결과 — 사용자가 적용하려는 조정 명령 리스트.",
    )
    user_intent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="원본 사용자 발화 (E5 raw input). None이면 prompt에서 생략.",
    )
    session_id: Optional[str] = None


# ============================================================
# E3 (지표 코멘트, 한 줄 자연어) 진입점 — Slice 5
# ============================================================


class E3Request(BaseModel):
    """E3 입력. AnalysisContext.model_dump() 결과를 받아 Core+Supporting 지표를
    5단계 level_tag → 자연어 한 줄 코멘트로 변환.

    분석 엔진 의존성 회피 — 산출된 MetricResult만 받음. 정량 재계산 없음.
    분석 엔진이 산출한 AnalysisContext 전체 구조를 그대로 받음 (다른 슬라이스 일관).

    실제 prompt 작성은 service에서 AnalysisContext.model_validate(dict) 후 build_e3_prompt 호출.
    Slice 5 진입 시점 자동 변환 — 지시서 §4.1.2 validator는 AnalysisContext nested 구조와 불일치
    (top-level preset_id/holdings 없음). E5/E2/E6와 일관 (validator 없음).
    """

    model_config = ConfigDict(extra="forbid")

    analysis_context: dict[str, Any] = Field(
        ...,
        description=(
            "AnalysisContext.model_dump() 결과 (analysis_target_portfolio + wallet_background 등 nested)."
        ),
    )
    session_id: Optional[str] = None
