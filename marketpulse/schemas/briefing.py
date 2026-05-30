"""브리핑 도메인 JSONField Pydantic v2 스키마 (PR-A2).

`BriefingLog.inputs_summary` JSONField에서 본문 섹션을 구조화할 때 사용.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BriefingSection(BaseModel):
    """Card E (Today's Brief) 본문 섹션 1개."""

    section: Literal["regime", "flow", "macro", "focus"]
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
