"""뉴스 도메인 JSONField Pydantic v2 검증 (PR-A2).

`MarketPulseNews.matched_symbols` / `matched_keywords` 검증용.
운영 코드의 필드명 기준으로 매핑:
    matched_symbols ↔ tickers/sectors (ETF symbol 포함)
    matched_keywords ↔ topics
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NewsEntities(BaseModel):
    """MarketPulseNews 매칭 메타데이터 통합 스키마.

    `matched_symbols`(JSONField list[str]) + `matched_keywords`(JSONField list[str])를
    함께 검증하기 위한 wrapper.
    """

    tickers: list[str] = Field(default_factory=list, description="주식 ticker 심볼")
    sectors: list[str] = Field(
        default_factory=list, description="섹터 ETF 심볼 (XLF, XLK 등)"
    )
    topics: list[str] = Field(
        default_factory=list, description="주제 키워드 (Fed, CPI, FOMC 등)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tickers": ["AAPL", "MSFT"],
                "sectors": ["XLK"],
                "topics": ["Fed", "CPI"],
            }
        }
    }
