"""
LLMResponse — LLM 호출 메타데이터 컨테이너.

§1.1 확정 결정: Pydantic BaseModel. 필드 추가/제거 금지.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class LLMResponse(BaseModel):
    text: str
    provider: Literal["gemini", "anthropic"]
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    fallback_from: Optional[Literal["gemini", "anthropic"]] = None
