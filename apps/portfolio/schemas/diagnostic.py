"""
DiagnosticCard (Pydantic) — E2 4요소 진단 카드 LLM 출력 스키마.
Django 모델 portfolio.models.DiagnosticCard 와는 별개의 DTO.

설계 근거: coach-llm-design-v1.md §3-2 + preset-design-v3.1.md §7-3
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    """약점의 심각도 레벨."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StructuralOrSingle(StrEnum):
    """약점이 구조적인가 단일 이상치인가."""

    STRUCTURAL = "structural"
    SINGLE_OUTLIER = "single_outlier"


class DiagnosticCard(BaseModel):
    """4요소 진단 카드 — E2 출력 + AnalysisContext.diagnostic_cards 입력 공용."""

    model_config = ConfigDict(extra="forbid")

    weakness_metric_id: str = Field(
        ...,
        description="약점 대상 지표 ID (복합이면 대표 지표).",
    )
    what_is_wrong: str = Field(
        ...,
        min_length=10,
        max_length=400,
        description="팩트 진술 (1~2문장). 예: 'PEG 2.5 이상 종목이 3개.'",
    )
    comparison_basis: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="비교 기준 명시 (1문장). 예: '산업 중앙값 1.4 대비.'",
    )
    why_it_matters: str = Field(
        ...,
        min_length=10,
        max_length=400,
        description="프리셋 철학 연결 (1~2문장). 왜 이 프리셋에서 중요한가.",
    )
    caveat_or_exception: str = Field(
        "",
        max_length=300,
        description="예외/트레이드오프 (1문장, 없으면 빈 문자열).",
    )
    severity: Severity = Field(
        ...,
        description="심각도 (high | medium | low).",
    )
    structural_or_single: StructuralOrSingle = Field(
        ...,
        description="구조적 이슈인가 단일 이상치인가.",
    )

    # Example:
    # {
    #   "weakness_metric_id": "peg_ratio",
    #   "what_is_wrong": "5개 종목 중 3개의 PEG가 2.5 이상으로 밸류에이션 부담이 있습니다.",
    #   "comparison_basis": "산업 중앙값 PEG 1.4 대비 약 80% 고평가.",
    #   "why_it_matters": "GARP 관점에서 성장 대비 가격의 비율은 핵심 지표입니다.",
    #   "caveat_or_exception": "NVDA는 AI 특수성으로 단일 이상치일 가능성 있음.",
    #   "severity": "medium",
    #   "structural_or_single": "structural"
    # }
