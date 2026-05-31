"""
HoldingSummary — 분석 컨텍스트(Tier 2.5)에서 종목 정보를 LLM에 전달할 때 사용.

설계 근거: coach-llm-design-v1.md §4-5 holdings_summary 항목
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class HoldingSummary(BaseModel):
    """분석 대상 Portfolio(또는 Wallet)의 단일 종목 요약."""

    model_config = ConfigDict(extra="forbid")

    holding_id: str = Field(
        ...,
        description="WalletHolding UUID (문자열 표현).",
    )
    stock_symbol: str = Field(..., description="티커 (예: 'NVDA').")
    stock_name: str = Field(..., description="종목 명 (예: 'NVIDIA Corporation').")
    sector: str | None = Field(
        None,
        description="섹터 (stocks.Stock.sector). 데이터 없으면 None.",
    )
    industry: str | None = Field(
        None,
        description="산업 (stocks.Stock.industry). 데이터 없으면 None.",
    )
    shares: Decimal = Field(..., description="보유 수량.")
    weight: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Portfolio 내 비중 (0~1).",
    )
    market_value: Decimal = Field(..., description="평가금액 (USD).")
    unrealized_return: Decimal = Field(
        ...,
        description="미실현 수익률 (-1 ~ ∞). 예: 0.15 = +15%.",
    )
    investment_thesis: str | None = Field(
        None,
        description="매수 시 투자 근거 (WalletHolding.investment_thesis).",
    )

    # Example:
    # {
    #   "holding_id": "550e8400-e29b-41d4-a716-446655440000",
    #   "stock_symbol": "NVDA",
    #   "stock_name": "NVIDIA Corporation",
    #   "sector": "Technology",
    #   "industry": "Semiconductors",
    #   "shares": "10.0000",
    #   "weight": "0.25",
    #   "market_value": "12500.00",
    #   "unrealized_return": "0.32",
    #   "investment_thesis": "AI 인프라 수요 초과 예상"
    # }
