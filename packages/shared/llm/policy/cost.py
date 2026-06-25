"""정책: 단가 단일출처 맵 + cost 계산/기록 훅. cost_track=True일 때만 기록.

흩어진 단가(베이스 #1 portfolio/llm/client.py 모듈 상수 + `_ANTHROPIC_PRICING`,
rag cost_tracker pricing dict)를 `(provider, model) -> (input_rate, output_rate)` 단일 맵으로
흡수. 골격 — 소비처 cost_tracker/cost_ledger 결선은 이관 슬라이스(여기선 훅 자리만).
"""

from __future__ import annotations

from typing import Callable, Optional

# USD per 1M tokens — 베이스 #1 portfolio/llm/client.py 단가 흡수 (2026-04 기준, 수동 갱신).
PRICING: dict[tuple[str, str], tuple[float, float]] = {
    ("gemini", "gemini-2.5-flash"): (0.075, 0.30),
    ("anthropic", "claude-sonnet-4-5"): (3.0, 15.0),
    ("anthropic", "claude-haiku-4-5"): (0.80, 4.0),
}

# provider별 미등록 모델 폴백 단가 (베이스 #1: anthropic 미등록 모델 → sonnet 기본).
_FALLBACK_RATE: dict[str, tuple[float, float]] = {
    "gemini": (0.075, 0.30),
    "anthropic": (3.0, 15.0),
}


def resolve_rate(provider: str, model: str) -> tuple[float, float]:
    """(provider, model) 단가. 미등록 모델은 provider 폴백 단가."""
    rate = PRICING.get((provider, model))
    if rate is not None:
        return rate
    return _FALLBACK_RATE.get(provider, (0.0, 0.0))


def compute_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    in_rate, out_rate = resolve_rate(provider, model)
    return input_tokens / 1_000_000 * in_rate + output_tokens / 1_000_000 * out_rate


# cost_track=True일 때 호출되는 기록 훅. 기본 None(no-op) — 골격.
# 이관 슬라이스에서 rag cost_tracker / portfolio cost_ledger를 여기에 결선.
CostHook = Callable[[str, str, int, int, float], None]
_cost_hook: Optional[CostHook] = None


def set_cost_hook(hook: Optional[CostHook]) -> None:
    """cost 기록 훅 결선(이관 슬라이스용). None이면 no-op."""
    global _cost_hook
    _cost_hook = hook


def record_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int, cost_usd: float
) -> None:
    if _cost_hook is not None:
        _cost_hook(provider, model, input_tokens, output_tokens, cost_usd)
