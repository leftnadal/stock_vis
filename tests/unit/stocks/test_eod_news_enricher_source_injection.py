"""
EODNewsEnricher NewsSource 주입 seam 단위 테스트 (NEWSFIX-BE · D-NEWSMATCH-FIX-PATH 1′).

검증:
  ① 주입 source로 실뉴스 매칭 성사 (symbol_today/7d/30d/industry)
  ② 무뉴스 심볼 → profile 폴백 유지 (정직성)
  ③ match_type / confidence 회귀 보존 (주입 경로 관통)
  ④ 매칭 창 규약 (today / 7d / 30d) 준수 — source 호출 인자 대조
  ⑤ 출력 형상(news_context 키/형) 무변
  + 기본 source = StockNewsSource (행위 보존)
  + EODPipeline이 news_source를 주입받아 보관 (앱 계층 배선 seam)

배선(실 NewsEntity 어댑터)은 앱 계층 슬라이스로 HALT — 여기서는 주입 seam의
메커니즘을 가짜 source로 증명한다(테스트 수준 before/after).
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest

from packages.shared.stocks.services.eod_news_enricher import EODNewsEnricher
from packages.shared.stocks.services.eod_pipeline import EODPipeline
from packages.shared.stocks.services.news_source import StockNewsSource

TARGET = date(2026, 8, 28)


class FakeNews:
    """duck-typed 뉴스 객체 (StockNews / NewsEntity 어댑터가 만족해야 할 형)."""

    def __init__(self, headline="H", summary="S", source="reuters",
                 url="http://x", sentiment="", published_at=None):
        self.headline = headline
        self.summary = summary
        self.source = source
        self.url = url
        self.sentiment = sentiment
        self.published_at = published_at or datetime(2026, 8, 28, 12, 0, 0)


class SpyNewsSource:
    """설정 가능한 가짜 source — 호출 인자 기록 + 단계별 반환 제어."""

    def __init__(self, on_date=None, between=None, industry=None):
        # between: dict {(start, end): FakeNews} 또는 단일 FakeNews (모든 창)
        self._on_date = on_date
        self._between = between
        self._industry = industry
        self.calls = []

    def latest_on_date(self, symbol, target_date):
        self.calls.append(("on_date", symbol, target_date))
        return self._on_date

    def latest_between(self, symbol, start_date, end_date):
        self.calls.append(("between", symbol, start_date, end_date))
        if isinstance(self._between, dict):
            return self._between.get((start_date, end_date))
        return self._between

    def latest_by_industry_between(self, industry, start_date, end_date):
        self.calls.append(("industry", industry, start_date, end_date))
        return self._industry


def _enrich_one(enricher, symbol="MSFT", industry="Software"):
    """단일 종목 enrich → news_context 반환."""
    tagged = [{
        "stock_id": symbol,
        "sector": "Tech",
        "industry": industry,
        "signals": [{"direction": "bullish"}],
    }]
    return enricher.enrich(tagged, TARGET)[0]["news_context"]


# ── ① 주입 source 실뉴스 매칭 성사 ────────────────────────────────────

def test_injected_source_symbol_today_match():
    src = SpyNewsSource(on_date=FakeNews(headline="MSFT 실적 서프라이즈"))
    ctx = _enrich_one(EODNewsEnricher(news_source=src))
    assert ctx["match_type"] == "symbol_today"
    assert ctx["headline"] == "MSFT 실적 서프라이즈"
    assert ctx["confidence"] == "high"


def test_injected_source_symbol_7d_match():
    # 당일 없음 → 7d 창에서 매칭
    cutoff_7d = TARGET - timedelta(days=7)
    src = SpyNewsSource(between={(cutoff_7d, TARGET): FakeNews(headline="7일 전 뉴스")})
    ctx = _enrich_one(EODNewsEnricher(news_source=src))
    assert ctx["match_type"] == "symbol_7d"
    assert ctx["headline"] == "7일 전 뉴스"


def test_injected_source_symbol_30d_match():
    # 당일·7d 없음 → 30d 창에서만 매칭
    cutoff_30d = TARGET - timedelta(days=30)
    src = SpyNewsSource(between={(cutoff_30d, TARGET): FakeNews(headline="30일 내 뉴스")})
    ctx = _enrich_one(EODNewsEnricher(news_source=src))
    assert ctx["match_type"] == "symbol_30d"
    assert ctx["confidence"] == "low"


def test_injected_source_industry_match():
    # symbol 전건 없음 → industry 매칭
    src = SpyNewsSource(industry=FakeNews(headline="섹터 뉴스"))
    ctx = _enrich_one(EODNewsEnricher(news_source=src))
    assert ctx["match_type"] == "industry_7d"


# ── ② 무뉴스 → profile 폴백 유지 (정직성) ─────────────────────────────

def test_no_news_falls_back_to_profile():
    src = SpyNewsSource()  # 전건 None
    enricher = EODNewsEnricher(news_source=src)
    with patch.object(
        enricher, "_build_profile_fallback",
        return_value={"match_type": "profile", "confidence": "info", "headline": "P"},
    ):
        ctx = _enrich_one(enricher)
    assert ctx["match_type"] == "profile"


def test_no_news_no_stock_returns_none_type():
    src = SpyNewsSource()  # 전건 None
    enricher = EODNewsEnricher(news_source=src)
    with patch.object(enricher, "_build_profile_fallback", return_value={}):
        ctx = _enrich_one(enricher)
    assert ctx["match_type"] == "none"


# ── ③ confidence 회귀 (주입 경로 관통) ────────────────────────────────

def test_confidence_upgrade_through_injected_7d():
    # 7d + positive sentiment + bullish 시그널 → medium→high 상향 (기존 규약)
    cutoff_7d = TARGET - timedelta(days=7)
    news = FakeNews(headline="호재", sentiment="positive")
    src = SpyNewsSource(between={(cutoff_7d, TARGET): news})
    ctx = _enrich_one(EODNewsEnricher(news_source=src))
    assert ctx["match_type"] == "symbol_7d"
    assert ctx["confidence"] == "high"  # medium +1


def test_confidence_downgrade_through_injected_today():
    # 당일 + positive + bearish 시그널 → 충돌 → high→medium 하향
    news = FakeNews(sentiment="positive")
    src = SpyNewsSource(on_date=news)
    tagged = [{
        "stock_id": "MSFT", "sector": "Tech", "industry": "Software",
        "signals": [{"direction": "bearish"}],
    }]
    ctx = EODNewsEnricher(news_source=src).enrich(tagged, TARGET)[0]["news_context"]
    assert ctx["confidence"] == "medium"


# ── ④ 매칭 창 규약 준수 (source 호출 인자 대조) ───────────────────────

def test_match_window_contract():
    src = SpyNewsSource()  # 전건 None → 모든 단계 호출됨
    enricher = EODNewsEnricher(news_source=src)
    with patch.object(enricher, "_build_profile_fallback", return_value={}):
        _enrich_one(enricher, symbol="AAPL", industry="Hardware")

    cutoff_7d = TARGET - timedelta(days=7)
    cutoff_30d = TARGET - timedelta(days=30)
    assert ("on_date", "AAPL", TARGET) in src.calls
    assert ("between", "AAPL", cutoff_7d, TARGET) in src.calls
    assert ("between", "AAPL", cutoff_30d, TARGET) in src.calls
    assert ("industry", "Hardware", cutoff_7d, TARGET) in src.calls
    # 계층 순서: on_date → 7d → 30d → industry
    kinds = [c[0] for c in src.calls]
    assert kinds == ["on_date", "between", "between", "industry"]


# ── ⑤ 출력 형상 무변 ──────────────────────────────────────────────────

def test_output_shape_invariant_on_match():
    src = SpyNewsSource(on_date=FakeNews())
    ctx = _enrich_one(EODNewsEnricher(news_source=src))
    assert set(ctx.keys()) == {
        "headline", "summary", "source", "url", "match_type",
        "confidence", "age_days", "sentiment", "published_at",
    }
    assert isinstance(ctx["age_days"], int)
    assert isinstance(ctx["published_at"], str)


def test_age_days_computed_from_published_at():
    news = FakeNews(published_at=datetime(2026, 8, 25, 9, 0, 0))
    src = SpyNewsSource(on_date=news)
    ctx = _enrich_one(EODNewsEnricher(news_source=src))
    assert ctx["age_days"] == 3  # 08-28 - 08-25


# ── 기본 source = StockNewsSource (행위 보존) ─────────────────────────

def test_default_source_is_stocknews_source():
    assert isinstance(EODNewsEnricher().news_source, StockNewsSource)


# ── 매칭률 before/after 메커니즘 증명 (테스트 수준) ───────────────────

def test_match_rate_default_vs_injected():
    symbols = ["A", "B", "C", "D"]
    tagged = [
        {"stock_id": s, "sector": "T", "industry": "I", "signals": []}
        for s in symbols
    ]

    # before: 빈 source(운영 StockNews=0행 대응) + profile 폴백 → 매칭 0
    empty = SpyNewsSource()
    e0 = EODNewsEnricher(news_source=empty)
    with patch.object(e0, "_build_profile_fallback", return_value={}):
        before = e0.enrich(tagged, TARGET)
    before_matched = sum(
        1 for x in before
        if x["news_context"]["match_type"] not in ("none", "profile", "")
    )
    assert before_matched == 0

    # after: 실뉴스 주입 → 전건 symbol_today 매칭
    live = SpyNewsSource(on_date=FakeNews())
    after = EODNewsEnricher(news_source=live).enrich(tagged, TARGET)
    after_matched = sum(
        1 for x in after
        if x["news_context"]["match_type"] not in ("none", "profile", "")
    )
    assert after_matched == len(symbols)


# ── EODPipeline 주입 seam (앱 계층 배선 지점) ─────────────────────────

def test_pipeline_stores_news_source():
    src = SpyNewsSource()
    assert EODPipeline(news_source=src).news_source is src
    assert EODPipeline().news_source is None


# ── DB 통합: 기본 StockNewsSource 행위 보존 ──────────────────────────

@pytest.mark.django_db
def test_default_stocknewssource_matches_real_row():
    from packages.shared.stocks.models import StockNews

    StockNews.objects.create(
        symbol="MSFT",
        headline="MSFT 당일 뉴스",
        summary="요약",
        source="reuters",
        url="http://x",
        sentiment="positive",
        published_at=datetime(2026, 8, 28, 10, 0, 0),
    )
    ctx = _enrich_one(EODNewsEnricher())  # 기본 source
    assert ctx["match_type"] == "symbol_today"
    assert ctx["headline"] == "MSFT 당일 뉴스"


@pytest.mark.django_db
def test_default_empty_stocknews_profile_fallback():
    from packages.shared.stocks.models import Stock

    Stock.objects.create(symbol="NOSTK", stock_name="No News Inc", sector="Tech")
    ctx = _enrich_one(EODNewsEnricher(), symbol="NOSTK")
    assert ctx["match_type"] == "profile"
    assert "No News Inc" in ctx["headline"]
