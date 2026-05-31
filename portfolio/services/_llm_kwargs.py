"""LLMClient 호출 시 사용하는 provider kwargs 공유 모듈.

Slice 2 백로그 #3 — e1_garp.py와 e5_adjustment_parser.py의 PROVIDER_KWARGS
중복 제거. 모든 진입점 service에서 본 모듈 import.

Slice 3 Step 2에서 자연 흡수.
"""

from __future__ import annotations

from typing import Literal

from portfolio.llm.client import (
    ANTHROPIC_HAIKU_MODEL,
    ANTHROPIC_SONNET_MODEL,
)

ProviderLabel = Literal["gemini", "anthropic", "sonnet", "haiku"]


PROVIDER_KWARGS: dict[str, dict] = {
    "gemini": {"provider": "gemini", "model": None},
    "anthropic": {"provider": "anthropic", "model": None},  # = Sonnet (LLMClient 기본)
    "sonnet": {"provider": "anthropic", "model": ANTHROPIC_SONNET_MODEL},
    "haiku": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
}


def resolve_provider_kwargs(label: str) -> dict:
    """Provider label → LLMClient kwargs 변환.

    Args:
        label: "haiku" | "sonnet" | "gemini" | "anthropic"

    Raises:
        ValueError: 미등록 label
    """
    if label not in PROVIDER_KWARGS:
        raise ValueError(
            f"Unknown provider label: {label!r}. Available: {sorted(PROVIDER_KWARGS)}"
        )
    return PROVIDER_KWARGS[label]
