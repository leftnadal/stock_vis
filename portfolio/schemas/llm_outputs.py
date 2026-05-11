"""
E1~E6 LLM 진입점 출력 스키마.

설계 근거: coach-llm-design-v1.md §3-1~§3-6
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .diagnostic import DiagnosticCard


# ============================================================
# E1: 한 줄 진단
# ============================================================

class OneLineDiagnosis(BaseModel):
    """E1 출력: Portfolio 전체에 대한 한 줄 + 2~3문장 요약."""

    model_config = ConfigDict(extra="forbid")

    headline: str = Field(
        ...,
        min_length=10,
        max_length=60,
        description="25~40자 헤드라인 (한국어).",
    )
    summary: str = Field(
        ...,
        min_length=30,
        max_length=500,
        description="2~3문장 요약 (한국어).",
    )

    # Example:
    # {
    #   "headline": "퀄리티는 견조하나 밸류에이션 부담",
    #   "summary": "GARP 관점에서 당신의 Tech 성장주 포트폴리오는 ROIC와 성장성은 상위권이지만, 3개 종목의 PEG가 2.5 이상으로 밸류에이션 부담이 뚜렷합니다. 향후 성장 둔화 시 조정 리스크를 주시할 필요가 있습니다."
    # }


# ============================================================
# E2: 진단 카드
# ============================================================

class DiagnosticCards(BaseModel):
    """E2 출력: 최대 3개의 4요소 진단 카드."""

    model_config = ConfigDict(extra="forbid")

    cards: list[DiagnosticCard] = Field(
        ...,
        max_length=3,
        description="약점 진단 카드. priority 1~3 순.",
    )


# ============================================================
# E3: 지표별 한 줄 코멘트
# ============================================================

class MetricComment(BaseModel):
    """단일 지표에 대한 1~2문장 코멘트."""

    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(..., description="지표 식별자.")
    one_liner: str = Field(
        ...,
        min_length=10,
        max_length=300,
        description="1~2문장 코멘트 (한국어).",
    )


class MetricComments(BaseModel):
    """E3 출력: 지표별 코멘트 리스트."""

    model_config = ConfigDict(extra="forbid")

    comments: list[MetricComment] = Field(
        default_factory=list,
        description="Core + Supporting 지표 수만큼.",
    )


# ============================================================
# E4: 대화 Q&A
# ============================================================

class ConversationResponse(BaseModel):
    """E4 출력: 사용자 메시지에 대한 응답."""

    model_config = ConfigDict(extra="forbid")

    response_text: str = Field(
        ...,
        description="자연어 응답 (한국어). 사용자에게 보여질 전문.",
    )
    has_adjustment_intent: bool = Field(
        False,
        description="조정 의도 감지 여부. True이면 E5로 라우팅.",
    )
    adjustment_parse_hint: str = Field(
        "",
        description="E5로 넘길 힌트 (조정 의도 요약).",
    )


# ============================================================
# E5: 의도 분류 + 조정 파싱
# ============================================================

class AdjustmentIntentType(StrEnum):
    """조정 의도 유형."""

    THRESHOLD_CHANGE = "threshold_change"
    TIER_CHANGE = "tier_change"
    EXCLUDE_STOCK = "exclude_stock"
    CHANGE_COMPARISON_GROUP = "change_comparison_group"
    UNKNOWN = "unknown"


class AdjustmentOverride(BaseModel):
    """단일 조정 override."""

    model_config = ConfigDict(extra="forbid")

    intent_type: AdjustmentIntentType = Field(..., description="조정 유형.")
    description_for_user: str = Field(
        ...,
        description="확인 카드에 표시할 한국어 설명. 예: 'ROIC 임계값 15% → 20%'.",
    )
    overrides: dict = Field(
        ...,
        description=(
            "intent_type별 구조화 payload. "
            "threshold_change: {metric_id, new_threshold}. "
            "tier_change: {metric_id, from_tier, to_tier}. "
            "exclude_stock: {stock_symbol, exclude_from_metric}. "
            "change_comparison_group: {metric_id, new_scope}."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="파싱 확신도 (0~1). 0.7 미만이면 clarification 권장.",
    )


class AdjustmentIntent(BaseModel):
    """E5 출력: 감지된 조정 의도 집합 + clarification 필요 여부."""

    model_config = ConfigDict(extra="forbid")

    detected_overrides: list[AdjustmentOverride] = Field(
        default_factory=list,
        description="감지된 조정 목록 (복수 가능).",
    )
    needs_clarification: bool = Field(
        False,
        description="True이면 사용자에게 clarification_question 제시.",
    )
    clarification_question: str = Field(
        "",
        description="한국어 질문. needs_clarification=True일 때만 의미.",
    )


# ============================================================
# E6: 조정 후 해설
# ============================================================

class AdjustmentComparison(BaseModel):
    """E6 출력: 원본 vs 조정 분석 비교 해설."""

    model_config = ConfigDict(extra="forbid")

    key_changes: list[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="주요 변화 포인트 3~5개 (한국어 bullet).",
    )
    summary: str = Field(
        ...,
        min_length=20,
        max_length=400,
        description="전체 요약 1~2문장.",
    )
    implication_for_user: str = Field(
        ...,
        min_length=20,
        max_length=400,
        description="사용자에게 의미하는 바 (추천 프리셋 제안 포함 가능).",
    )
