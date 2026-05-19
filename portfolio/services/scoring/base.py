"""Slice 12 Part 1 — preset scoring engine abstract base class.

Slice 11 Part 1 `CommentaryInputBase` 패턴 미러:
  - Pydantic v2 (frozen + extra=forbid)
  - 5 sub class per category (value/growth/income/factor/special)
  - Part 1: 스켈레톤만 (score / required_metrics는 NotImplementedError)
  - Part 2: 풀 구현 (production scoring logic 신규 작성)

설계 참고:
  - Slice 11 Part 3 `PromptBuilderBase` E2~E6 skel 패턴 동일 (Part 1 골격 → Part 2 풀)
  - frontend 보호: 기존 production scoring 함수 부재 → 신규 영역, 기존 코드 무변경
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

from portfolio.schemas.commentary_input import CommentaryInputBase


class ScoringEngineBase(ABC, BaseModel):
    """Preset scoring engine abstract base.

    Sub class per category (Slice 12 Part 1 5종):
      - ValueScoringEngine (value)
      - GrowthScoringEngine (growth)
      - IncomeScoringEngine (income)
      - FactorScoringEngine (factor)
      - SpecialScoringEngine (special)

    카테고리 안에 1+개 preset 매핑 (예: value → buffett_quality_value, piotroski_f_score).
    Part 2에서 preset_id 인자로 카테고리 내 세부 분기 처리.

    설계 원칙 (Slice 11 Part 1 미러):
      - frozen=True: 인스턴스 immutable
      - extra="forbid": 의도하지 않은 필드 차단
      - @abstractmethod: sub class에서 score/required_metrics 구현 강제
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ClassVar — 카테고리 식별 (sub class에서 override)
    category: ClassVar[str] = ""

    @abstractmethod
    def score(self, input_data: CommentaryInputBase) -> dict[str, Any]:
        """카테고리별 scoring 로직.

        Args:
            input_data: Slice 11 Part 1 통합 input schema 인스턴스
                       (CommentaryInputBase 또는 sub class).

        Returns:
            dict with keys:
              - score: float (정규화 단위, Part 2에서 0.0~1.0 결정)
              - metrics: dict[str, float] (HHI, sector_concentration 등 산출 메트릭)
              - reasoning: str (선택, 카테고리별 점수 해석)
        """

    @abstractmethod
    def required_metrics(self) -> list[str]:
        """이 카테고리 scoring이 필요로 하는 메트릭 키 목록.

        Part 2에서 `PRESET_METRICS[preset_id]` 또는 카테고리별 commonly required
        메트릭 list로 풀 구현.
        """
