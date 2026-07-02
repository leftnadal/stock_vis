"""
AlphaVantageNewsProvider broad 재설계 테스트.

검증 포인트 (co-mention 소스 복구의 핵심 계약):
- broad(symbol=None) 파싱이 ticker_sentiment[] 다종목을 그대로 entities로 보존(=co-mention).
- relevance 컷 미만 종목 제외(곁다리 노이즈 방지).
- broad 문맥에선 "요청 심볼 강제 추가"를 하지 않는다(per-symbol 편향 제거).
- per-symbol 회귀 금지: fetch_company_news/fetch_market_news는 no-op.
- fetch_broad_news가 tickers 미지정 + topics/시간창/limit 파라미터로 호출.
- AV 스로틀/한도(feed 부재 + Note/Information)를 RateLimitExceeded로 표면화.
"""
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from services.news.providers.alphavantage import (
    AlphaVantageNewsProvider,
    RateLimitExceeded,
)


@pytest.fixture
def provider():
    return AlphaVantageNewsProvider(api_key="test_key", throttle=False)


@pytest.fixture
def feed_item_multi():
    """다종목(co-mention) 기사 — relevance 낮은 곁다리 1개 포함."""
    return {
        "url": "https://ex.com/a",
        "title": "AI chip supply chain",
        "summary": "S",
        "time_published": "20260501T103000",
        "source": "Yahoo",
        "banner_image": "https://ex.com/img.jpg",
        "overall_sentiment_score": "0.25",
        "ticker_sentiment": [
            {"ticker": "NVDA", "relevance_score": "0.95", "ticker_sentiment_score": "0.4"},
            {"ticker": "TSM", "relevance_score": "0.62", "ticker_sentiment_score": "0.2"},
            {"ticker": "FRINGE", "relevance_score": "0.05", "ticker_sentiment_score": "0.0"},
        ],
    }


class TestBroadParsing:
    def test_multi_ticker_preserved_as_comention(self, provider, feed_item_multi):
        """다종목 ticker_sentiment → 다종목 entities (co-mention 신호)."""
        art = provider._parse_article(feed_item_multi, symbol=None)
        syms = [e["symbol"] for e in art.entities]
        # relevance 0.05 곁다리(FRINGE) 제외, NVDA·TSM 보존 → 2+종목
        assert syms == ["NVDA", "TSM"]
        assert len(art.entities) >= 2

    def test_relevance_cut_excludes_fringe(self, feed_item_multi):
        prov = AlphaVantageNewsProvider("k", relevance_cut=Decimal("0.15"), throttle=False)
        art = prov._parse_article(feed_item_multi, symbol=None)
        assert "FRINGE" not in [e["symbol"] for e in art.entities]

    def test_no_forced_symbol_injection_in_broad(self, provider, feed_item_multi):
        """broad(symbol=None)에서는 요청 심볼 강제 추가 로직이 돌지 않는다."""
        art = provider._parse_article(feed_item_multi, symbol=None)
        # entities는 응답 ticker_sentiment 기반만 (강제 삽입 없음)
        assert len(art.entities) == 2
        assert art.provider_name == "alpha_vantage"
        assert all(e["source"] == "alpha_vantage" for e in art.entities)

    def test_missing_url_or_title_returns_none(self, provider):
        assert provider._parse_article({"url": "", "title": "T"}) is None
        assert provider._parse_article({"url": "u"}) is None

    def test_unparseable_date_returns_none(self, provider):
        assert (
            provider._parse_article(
                {"url": "u", "title": "T", "time_published": "garbage"}
            )
            is None
        )

    def test_date_parsing_formats(self, provider):
        # AV time_published는 항상 초 포함(예: 20260424T000728) — 실측 15자 형식.
        assert provider._parse_av_date("20260501T103000") == datetime(2026, 5, 1, 10, 30, 0)
        assert provider._parse_av_date("20260424T000728") == datetime(2026, 4, 24, 0, 7, 28)
        assert provider._parse_av_date("") is None
        assert provider._parse_av_date("garbage") is None


class TestPerSymbolRegressionBlocked:
    def test_company_news_is_noop(self, provider):
        assert provider.fetch_company_news("AAPL", datetime(2026, 5, 1), datetime(2026, 5, 2)) == []

    def test_market_news_is_noop(self, provider):
        assert provider.fetch_market_news() == []


class TestFetchBroad:
    def test_broad_omits_tickers_and_sets_params(self, provider):
        captured = {}

        def fake_get(url, params=None, timeout=None):
            captured["params"] = params
            resp = Mock()
            resp.raise_for_status = Mock()
            resp.json = Mock(return_value={"feed": []})
            return resp

        with patch("services.news.providers.alphavantage.requests.get", side_effect=fake_get):
            provider.fetch_broad_news(
                time_from=datetime(2026, 4, 24, 0, 0),
                time_to=datetime(2026, 4, 25, 0, 0),
                limit=1000,
                sort="EARLIEST",
            )
        p = captured["params"]
        assert p["function"] == "NEWS_SENTIMENT"
        assert "tickers" not in p  # broad — 종목 미지정
        assert p["limit"] == 1000
        assert p["time_from"] == "20260424T0000"
        assert p["sort"] == "EARLIEST"
        assert "topics" in p  # 기본 topic 세트

    def test_broad_parses_multi_ticker_feed(self, provider, feed_item_multi):
        def fake_get(url, params=None, timeout=None):
            resp = Mock()
            resp.raise_for_status = Mock()
            resp.json = Mock(return_value={"feed": [feed_item_multi]})
            return resp

        with patch("services.news.providers.alphavantage.requests.get", side_effect=fake_get):
            arts = provider.fetch_broad_news()
        assert len(arts) == 1
        assert len(arts[0].entities) == 2

    def test_throttle_message_raises_ratelimit(self, provider):
        def fake_get(url, params=None, timeout=None):
            resp = Mock()
            resp.raise_for_status = Mock()
            resp.json = Mock(
                return_value={"Information": "please spread out your free API requests"}
            )
            return resp

        with patch("services.news.providers.alphavantage.requests.get", side_effect=fake_get):
            with pytest.raises(RateLimitExceeded):
                provider.fetch_broad_news()

    def test_error_message_returns_empty(self, provider):
        def fake_get(url, params=None, timeout=None):
            resp = Mock()
            resp.raise_for_status = Mock()
            resp.json = Mock(return_value={"Error Message": "invalid api call"})
            return resp

        with patch("services.news.providers.alphavantage.requests.get", side_effect=fake_get):
            assert provider.fetch_broad_news() == []
