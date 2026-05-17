"""Slice 9 #44 — Rationale record schema.

matrix 1:1 대응 rationale (Sonnet 26건 자체 평가) 단위 record + batch 진행 추적.

지시서 §1.1 정의를 코드베이스 시그니처에 맞게 적용.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RationaleRecord(BaseModel):
    """matrix 26 entries 1:1 대응 rationale 단위 record.

    Slice 8 Part 3 matrix_summary.json의 results 26 entries 각각에 대해
    Sonnet으로 자체 평가 rationale을 생성한 결과.
    """

    case_id: str = Field(
        description="rationale case ID (예: S01_haiku, S01_sonnet)",
    )
    case_name: str = Field(
        description="시나리오 case short (예: S01, S02, ...)",
    )
    original_model: str = Field(
        description="원본 답변 생성 모델 (claude-haiku-4-5 / claude-sonnet-4-5)",
    )
    rationale_model: str = Field(
        default="claude-sonnet-4-6",
        description="rationale 생성 모델",
    )

    original_commentary: str = Field(
        description="평가 대상 답변 (parsed.answer) 전체",
    )
    original_specificity_score: int = Field(
        ge=0,
        le=5,
        description="P1~P5 patterns count (0~5)",
    )
    original_specificity_detail: dict[str, bool] = Field(
        description="P1~P5 각각 발동 여부 (P1_metric_mention, P2_threshold, ...)",
    )

    rationale_text: str = Field(
        description="Sonnet이 생성한 평가 근거 (200~500자)",
    )
    rationale_categories: list[str] = Field(
        default_factory=list,
        description="진단 카테고리 (예: ['data_grounding', 'action_clarity'])",
    )
    rationale_score: int = Field(
        ge=0,
        le=5,
        description="Sonnet 자체 평가 점수 (0~5)",
    )

    cost_usd: float = Field(description="rationale 생성 비용 (USD)")
    input_tokens: int = Field(description="rationale 입력 토큰")
    output_tokens: int = Field(description="rationale 출력 토큰")
    latency_ms: int = Field(description="rationale latency")

    estimated_input_tokens: int = Field(
        default=0,
        description="#β2 estimator 예측값 (실측 vs 예측 비교용)",
    )


class RationaleBatch(BaseModel):
    """batch 단위 진행 추적 (5+5+5+5+5+1 = 26)."""

    batch_id: int = Field(ge=1, le=6)
    case_ids: list[str] = Field(description="batch에 포함된 case_id 리스트")
    completed_count: int = Field(
        default=0,
        description="batch 내 완료된 case 수",
    )
    batch_cost_usd: float = Field(default=0.0)
    slice_cost_after_batch: float = Field(
        default=0.0,
        description="batch 종료 시 누적 slice_usd",
    )
    cap_warning_triggered: bool = Field(default=False)
    aborted: bool = Field(
        default=False,
        description="batch 도중 정지 여부",
    )
