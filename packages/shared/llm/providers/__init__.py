"""provider 레지스트리 — gemini(우선) / anthropic(2nd)."""

from __future__ import annotations

from packages.shared.llm.providers.anthropic import AnthropicProvider
from packages.shared.llm.providers.base import Provider
from packages.shared.llm.providers.gemini import GeminiProvider
from packages.shared.llm.types import LLMInvalidPromptError

# 인스턴스는 무상태(per-call SDK client 생성) → 모듈 레벨 단일 인스턴스 안전.
_REGISTRY: dict[str, Provider] = {
    "gemini": GeminiProvider(),
    "anthropic": AnthropicProvider(),
}


def get_provider(name: str) -> Provider:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise LLMInvalidPromptError(f"Unknown provider: {name}") from None


__all__ = [
    "Provider",
    "GeminiProvider",
    "AnthropicProvider",
    "get_provider",
]
