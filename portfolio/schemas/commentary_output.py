"""Commentary output schemas — 6 진입점 통합 output (Slice 11 Part 2 #41 close).

Slice 8 Part 2 (#28): action_items 강제 슬롯 도입 (`ActionItem`).
Slice 11 Part 2 (#41 close): `CommentaryOutputBase` + 6 sub class (E1~E6) 신설.
  - Part 1 `commentary_input.py` 구조 미러 (Base / sub class / Holding... / frozen=True/extra=forbid).
  - ActionItem은 본 모듈에 보존 (호출자 4건 import 경로 무변경 보장).
  - 신규 `E1Output`~`E6Output`은 trio 통합 진입점용. 기존 legacy `E2DiagnosticCard`,
    `E6ComparisonResponse` 등은 `portfolio/schemas/llm_outputs.py`에 그대로 존재 (대체 아님).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Slice 8 Part 2 (#28) — ActionItem (변경 없음, 호출자 4건 호환)
# ============================================================


class ActionItem(BaseModel):
    """LLM commentary의 실행 가능 액션 항목.

    모든 진입점(E1~E6, E3_portfolio)의 output schema에 강제 슬롯으로 포함.
    빈 리스트 허용 (backward-compat).

    Examples:
        >>> ActionItem(
        ...     title="현금 비중 5% 축소",
        ...     description="포트폴리오 현금 비중이 25%로 과도. 우량 종목 추가 매수 검토.",
        ...     priority="high",
        ... )
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="액션 제목 (간결, 1줄)",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=300,
        description="액션 상세 설명 (근거 + 실행 방법)",
    )
    priority: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="우선순위 (high=즉시, medium=단기, low=장기)",
    )
    category: Optional[Literal["rebalance", "review", "monitor", "research"]] = Field(
        default=None,
        description="카테고리 (선택). rebalance=재조정, review=검토, monitor=감시, research=조사",
    )


# ============================================================
# Slice 11 Part 2 (#41 close) — 6 진입점 통합 output schema
# ============================================================


ConfidenceLevel = Literal["high", "medium", "low"]


class CommentaryOutputBase(BaseModel):
    """6 진입점 공통 output base — Part 1 `CommentaryInputBase` 미러.

    모든 진입점 output은 이 base를 상속하고, 진입점별 특화 필드를 추가한다.

    설계 원칙:
        - frozen=True: output은 immutable (로깅/평가 후 변경 불가)
        - extra="forbid": 정의되지 않은 필드 거부 (schema drift 즉시 검출)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: str = Field(..., min_length=1, description="진입점별 commentary 한 줄 요약.")
    key_observations: list[str] = Field(
        default_factory=list, description="핵심 관찰 사항 list (자유 길이)."
    )
    confidence: ConfidenceLevel = Field(..., description="결과 자신도 (high/medium/low).")


class E1Output(CommentaryOutputBase):
    """E1 GARP 스코어링 output."""

    action_items: list[ActionItem] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    metrics_table: str = Field(
        default="",
        description="(deprecated #21, Slice 13+ 제거 예정) 마크다운 metrics 표.",
    )


class E2Output(CommentaryOutputBase):
    """E2 포트폴리오 종합 진단 output."""

    quoted_metrics: dict[str, Any] = Field(default_factory=dict)
    metrics_table: str = Field(
        default="",
        description="(deprecated #21, Slice 13+ 제거 예정) 마크다운 metrics 표.",
    )


class E3Output(CommentaryOutputBase):
    """E3 집중도 분석 output."""

    action_items: list[ActionItem] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class E4Output(CommentaryOutputBase):
    """E4 대화 Q&A output — base만 사용 (action_items/risk_flags 불필요)."""


class E5Output(CommentaryOutputBase):
    """E5 추출 진입점 output."""

    action_items: list[ActionItem] = Field(default_factory=list)
    quoted_metrics: dict[str, Any] = Field(default_factory=dict)


class E6Output(CommentaryOutputBase):
    """E6 분석엔진 output."""

    risk_flags: list[str] = Field(default_factory=list)
    quoted_metrics: dict[str, Any] = Field(default_factory=dict)


# Registry — Part 1 `COMMENTARY_INPUT_CLASSES` 미러.
COMMENTARY_OUTPUT_CLASSES: dict[str, type[CommentaryOutputBase]] = {
    "e1": E1Output,
    "e2": E2Output,
    "e3": E3Output,
    "e4": E4Output,
    "e5": E5Output,
    "e6": E6Output,
}
