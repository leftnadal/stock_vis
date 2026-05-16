"""Commentary output schemas.

Slice 8 Part 2 (#28): action_items 강제 슬롯 도입.
Slice 9 #41 후보: CommentaryOutputBase 통합 모델은 본 파일에 추가 예정.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


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
