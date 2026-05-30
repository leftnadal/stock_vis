"""Tests for marketpulse.services.news_classifier."""
from __future__ import annotations

import pytest

from apps.market_pulse.models.news import MarketPulseNews
from apps.market_pulse.services import news_classifier


class TestClassify:
    def test_mag7_symbol(self):
        r = news_classifier.classify('AAPL surges on iPhone sales beat',
                                     'Apple Inc. reported record quarterly revenue.')
        assert r.category == MarketPulseNews.Category.MAG7
        assert 'AAPL' in r.matched_symbols

    def test_macro_fomc(self):
        r = news_classifier.classify('FOMC meeting minutes signal hawkish stance', '')
        assert r.category == MarketPulseNews.Category.MACRO

    def test_geopolitics_sanctions(self):
        r = news_classifier.classify('New sanctions imposed on Russia',
                                     'Tensions escalate over Ukraine')
        assert r.category == MarketPulseNews.Category.GEOPOLITICS

    def test_smart_money_buffett(self):
        r = news_classifier.classify('Berkshire 13F filing reveals new positions',
                                     'Warren Buffett discloses major holdings')
        assert r.category == MarketPulseNews.Category.SMART_MONEY

    def test_sector_etf(self):
        r = news_classifier.classify('XLK rallies on tech earnings', '')
        assert r.category == MarketPulseNews.Category.SECTOR
        assert 'XLK' in r.matched_symbols

    def test_index_spy(self):
        r = news_classifier.classify('SPY closes at record high', '')
        assert r.category == MarketPulseNews.Category.INDEX

    def test_unrelated_returns_none(self):
        assert news_classifier.classify('Best vacation spots in Europe', 'travel guide') is None

    def test_priority_mag7_over_macro(self):
        r = news_classifier.classify('AAPL stock falls after Fed rate hike',
                                     'Federal Reserve raises rates as Apple guidance cuts.')
        assert r.category == MarketPulseNews.Category.MAG7


class TestApplyQuota:
    def _build(self, cats):
        return [
            (f'h{i}',
             news_classifier.ClassificationResult(category=c, matched_symbols=[], matched_keywords=[]),
             {'i': i})
            for i, c in enumerate(cats)
        ]

    def test_caps_macro_at_ten(self):
        # 2026-05-26 C 옵션: MACRO hourly cap 2 → 10 (commit 3e76bc8). 분석률 5배 상향 정책.
        items = self._build([MarketPulseNews.Category.MACRO] * 12)
        out = news_classifier.apply_quota(items)
        assert len(out) == 10

    def test_six_categories_all_pass(self):
        items = self._build([
            MarketPulseNews.Category.MACRO,
            MarketPulseNews.Category.MAG7,
            MarketPulseNews.Category.GEOPOLITICS,
            MarketPulseNews.Category.SECTOR,
            MarketPulseNews.Category.INDEX,
            MarketPulseNews.Category.SMART_MONEY,
        ])
        out = news_classifier.apply_quota(items)
        assert {r[1].category for r in out} == {
            MarketPulseNews.Category.MACRO, MarketPulseNews.Category.MAG7,
            MarketPulseNews.Category.GEOPOLITICS, MarketPulseNews.Category.SECTOR,
            MarketPulseNews.Category.INDEX, MarketPulseNews.Category.SMART_MONEY,
        }
