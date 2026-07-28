"""packages/shared/stocks/llm — 캐러셀 카드 LLM 채움 (bake in-zone). [D-LLMFILL ⑴]

프롬프트 소유 = bake 구획 단일출처(MP-TRANSLATION `apps/market_pulse/llm/` 선례 동형).
shared LLM 래퍼(`packages/shared/llm`)는 **소비만** — 외부-LLM 직접 호출 없음. [D-LLMFILL ⑵]
"""

from __future__ import annotations

from packages.shared.stocks.llm.card_fill_prompt import build_card_fill_prompt
from packages.shared.stocks.llm.fill_service import fill_recommendations

__all__ = ["build_card_fill_prompt", "fill_recommendations"]
