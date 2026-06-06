"""
뉴스 도메인 JSONField Pydantic v2 검증 (PR-A2).

소속: apps/market_pulse/schemas (app 레이어 JSONField 검증).
역할: `MarketPulseNews.matched_symbols`·`matched_keywords` 구조 검증.
주요 심볼:
  - NewsEntities: 매칭된 심볼/키워드 모음 구조
필드명 매핑(운영 코드 기준):
  - matched_symbols ↔ tickers/sectors (ETF symbol 포함)
  - matched_keywords ↔ topics
소비처: services/news_classifier.py·tasks/news.py — 분류 결과 저장 직전 검증.
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
