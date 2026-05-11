"""Market Pulse v2 — 6 카테고리 뉴스 분류기 (PR-B)."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable

from marketpulse.models.news import MarketPulseNews

logger = logging.getLogger(__name__)

MAG7_SYMBOLS = ('AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA')
MAG7_NAMES = (
    'apple', 'microsoft', 'alphabet', 'google',
    'amazon', 'meta platforms', 'meta ', 'facebook',
    'nvidia', 'tesla',
)

MACRO_KEYWORDS = (
    'federal reserve', 'fed ', 'fomc', 'powell', 'rate cut', 'rate hike',
    'rate decision', 'central bank', 'ecb ', 'boj ', 'bank of england',
    'interest rate', 'monetary policy', 'inflation', 'cpi', 'ppi', 'pce',
    'nonfarm payroll', 'jobs report', 'unemployment rate', 'gdp',
    'treasury yield', 'yield curve', 'recession', 'soft landing',
    'consumer confidence', 'retail sales',
    'jackson hole', 'beige book',
)

GEOPOLITICS_KEYWORDS = (
    'sanction', 'tariff', 'trade war', 'trade deal',
    'ukraine', 'russia', 'putin',
    'israel', 'gaza', 'hamas', 'iran',
    'china tension', 'taiwan', 'beijing',
    'opec', 'middle east',
    'embargo', 'export control',
)

SMART_MONEY_KEYWORDS = (
    '13f', '13-f', 'hedge fund', 'hedge-fund',
    'berkshire', 'buffett', 'warren buffett',
    'bridgewater', 'ray dalio', 'ackman', 'pershing square',
    'institutional investor', 'institutional flow', 'institutional buying',
    'big short', 'michael burry',
    'family office',
    'activist investor', 'soros',
    'blackrock', 'vanguard', 'citadel', 'renaissance technologies',
    'point72', 'tiger global', 'd1 capital', 'two sigma',
    'short seller', 'short position', 'short interest',
    'insider buying', 'insider selling',
)

SECTOR_ETF_SYMBOLS = (
    'XLK', 'XLF', 'XLV', 'XLE', 'XLI',
    'XLP', 'XLY', 'XLU', 'XLRE', 'XLB', 'XLC',
)
SECTOR_NAMES = (
    'technology sector', 'financial sector', 'healthcare sector',
    'energy sector', 'industrial sector', 'consumer staples',
    'consumer discretionary', 'utilities sector', 'real estate sector',
    'materials sector', 'communication services',
    'semiconductor', 'chipmaker', 'biotech', 'pharma', 'pharmaceutical',
    'oil prices', 'crude oil', 'natural gas', 'gold price',
    'bank stocks', 'tech stocks', 'energy stocks', 'health stocks',
    'utility stocks', 'industrial stocks',
    'airline stocks', 'retail stocks', 'auto stocks', 'homebuilder',
    'reit ', 'reits',
)

INDEX_SYMBOLS = ('SPY', 'QQQ', 'DIA', 'IWM')
INDEX_NAMES = (
    's&p 500', 'sp500', 's&p500',
    'nasdaq 100', 'nasdaq100', 'nasdaq composite',
    'dow jones', 'dow industrial',
    'russell 2000', 'russell2000',
)


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    matched_symbols: list[str]
    matched_keywords: list[str]


DEFAULT_QUOTA: dict[str, tuple[int, int]] = {
    MarketPulseNews.Category.MACRO: (1, 2),
    MarketPulseNews.Category.SMART_MONEY: (1, 2),
    MarketPulseNews.Category.MAG7: (0, 2),
    MarketPulseNews.Category.SECTOR: (0, 2),
    MarketPulseNews.Category.GEOPOLITICS: (0, 1),
    MarketPulseNews.Category.INDEX: (0, 1),
}


def _normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').lower()).strip()


def _find_symbols(text_upper: str, symbols: Iterable[str]) -> list[str]:
    found: list[str] = []
    for sym in symbols:
        if re.search(rf'(?<![A-Z]){re.escape(sym)}(?![A-Z])', text_upper):
            found.append(sym)
    return found


def _find_keywords(text_lower: str, keywords: Iterable[str]) -> list[str]:
    return [kw for kw in keywords if kw in text_lower]


def classify(
    title: str,
    summary: str = '',
    explicit_symbols: Iterable[str] | None = None,
) -> ClassificationResult | None:
    text_lower = _normalize(f'{title} {summary}')
    text_upper = (f'{title} {summary}').upper()
    explicit = [s.upper() for s in (explicit_symbols or [])]

    mag7_hits = list({s for s in explicit if s in MAG7_SYMBOLS})
    mag7_hits += [s for s in _find_symbols(text_upper, MAG7_SYMBOLS) if s not in mag7_hits]
    mag7_name_hits = _find_keywords(text_lower, MAG7_NAMES)
    if mag7_hits or mag7_name_hits:
        return ClassificationResult(MarketPulseNews.Category.MAG7, mag7_hits, mag7_name_hits)

    macro_hits = _find_keywords(text_lower, MACRO_KEYWORDS)
    if macro_hits:
        return ClassificationResult(MarketPulseNews.Category.MACRO, [], macro_hits)

    geo_hits = _find_keywords(text_lower, GEOPOLITICS_KEYWORDS)
    if geo_hits:
        return ClassificationResult(MarketPulseNews.Category.GEOPOLITICS, [], geo_hits)

    sm_hits = _find_keywords(text_lower, SMART_MONEY_KEYWORDS)
    if sm_hits:
        return ClassificationResult(MarketPulseNews.Category.SMART_MONEY, [], sm_hits)

    sector_sym = list({s for s in explicit if s in SECTOR_ETF_SYMBOLS})
    sector_sym += [s for s in _find_symbols(text_upper, SECTOR_ETF_SYMBOLS) if s not in sector_sym]
    sector_name = _find_keywords(text_lower, SECTOR_NAMES)
    if sector_sym or sector_name:
        return ClassificationResult(MarketPulseNews.Category.SECTOR, sector_sym, sector_name)

    index_sym = list({s for s in explicit if s in INDEX_SYMBOLS})
    index_sym += [s for s in _find_symbols(text_upper, INDEX_SYMBOLS) if s not in index_sym]
    index_name = _find_keywords(text_lower, INDEX_NAMES)
    if index_sym or index_name:
        return ClassificationResult(MarketPulseNews.Category.INDEX, index_sym, index_name)

    return None


def apply_quota(
    classified: list[tuple[str, ClassificationResult, object]],
    quota: dict[str, tuple[int, int]] | None = None,
) -> list[tuple[str, ClassificationResult, object]]:
    quota = quota or DEFAULT_QUOTA
    counts: dict[str, int] = {cat: 0 for cat in quota}
    out: list[tuple[str, ClassificationResult, object]] = []
    for url_hash, result, payload in classified:
        cat = result.category
        max_n = quota.get(cat, (0, 99))[1]
        if counts.get(cat, 0) >= max_n:
            continue
        out.append((url_hash, result, payload))
        counts[cat] = counts.get(cat, 0) + 1
    return out
