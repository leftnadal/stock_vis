"""
브리핑 도메인 JSONField Pydantic v2 스키마 (PR-A2).

소속: apps/market_pulse/schemas (app 레이어 JSONField 검증).
역할: `BriefingLog.inputs_summary` 본문 섹션 구조화 + 검증.
주요 심볼:
  - BriefingSection: 섹션 단위(헤더·본문·근거) 구조
소비처: briefing/{client,prompt,safety}.py의 Gemini 입출력 검증, tasks/briefing.py 저장.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BriefingSection(BaseModel):
    """Card E (Today's Brief) 본문 섹션 1개."""

    section: Literal["regime", "flow", "macro", "focus"]
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
