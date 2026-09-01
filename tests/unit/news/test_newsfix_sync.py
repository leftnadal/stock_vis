"""
NewsEntity → StockNews 물질화 sync 테스트 (NEWSFIX-SYNC-BE · D-NEWSMATCH-FIX-PATH-V2 ⑵).

검증:
  - 매핑 정확성 (NewsEntity+NewsArticle → StockNews 컬럼)
  - 멱등성 (2회 실행 = 동일 상태)
  - 창 경계 (30일 밖 제외 / 안 포함)
  - sentiment 라벨 매핑 (score → positive/negative/neutral)
  - url 절단 (>500 → 500)
  - 빈 symbol 제외
  - enricher end-to-end 회귀: 채워진 StockNews로 실뉴스 매칭 성사(원 enricher·읽기 전용)

경계: 테스트 파일은 news 트랙 소유(tests/unit/news/·기존 news 테스트 선례). shared enricher는
      import(읽기)만·무수정.
"""

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

import pytest

from services.news.services.stock_news_sync import (
    _sentiment_label,
    sync_news_entities_to_stock_news,
)

NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=dt_timezone.utc)


def _mk_entity(symbol, published_at, *, title="H", summary="S", source="reuters",
               url="https://ex.com/a", industry="Software",
               ent_sentiment=Decimal("0.50"), art_id_url=None):
    """NewsArticle + NewsEntity 1쌍 생성. url은 고유해야 함(NewsArticle.url unique)."""
    from services.news.models import NewsArticle, NewsEntity

    art = NewsArticle.objects.create(
        url=art_id_url or url,
        title=title,
        summary=summary,
        source=source,
        published_at=published_at,
        sentiment_score=Decimal("0.10"),
        sentiment_source="marketaux",
    )
    return NewsEntity.objects.create(
        news=art,
        symbol=symbol,
        entity_name=f"{symbol} Inc.",
        entity_type="equity",
        industry=industry,
        match_score=Decimal("0.90000"),
        sentiment_score=ent_sentiment,
        source="marketaux",
    )


# ── _sentiment_label 단위 ─────────────────────────────────────────────

def test_sentiment_label_mapping():
    assert _sentiment_label(Decimal("0.50")) == "positive"
    assert _sentiment_label(Decimal("0.15")) == "positive"
    assert _sentiment_label(Decimal("-0.50")) == "negative"
    assert _sentiment_label(Decimal("-0.15")) == "negative"
    assert _sentiment_label(Decimal("0.00")) == "neutral"
    assert _sentiment_label(Decimal("0.10")) == "neutral"
    assert _sentiment_label(None) == ""


# ── 매핑 정확성 ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_mapping_accuracy():
    from packages.shared.stocks.models import StockNews

    _mk_entity(
        "msft", NOW - timedelta(days=1),
        title="MSFT 실적", summary="요약본", source="Bloomberg",
        url="https://ex.com/msft", industry="Software",
        ent_sentiment=Decimal("0.60"),
    )
    result = sync_news_entities_to_stock_news(window_days=30, now=NOW)

    assert result["created"] == 1
    assert result["symbols"] == 1
    row = StockNews.objects.get()
    assert row.symbol == "MSFT"          # upper 정규화
    assert row.headline == "MSFT 실적"    # ← NewsArticle.title
    assert row.summary == "요약본"
    assert row.source == "Bloomberg"
    assert row.url == "https://ex.com/msft"
    assert row.industry == "Software"
    assert row.sector == ""              # 원천 부재
    assert row.sentiment == "positive"   # 0.60 → positive
    assert row.stock_id is None


# ── 멱등성 ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_idempotent_double_run():
    from packages.shared.stocks.models import StockNews

    _mk_entity("AAA", NOW - timedelta(days=2), url="https://ex.com/aaa")
    _mk_entity("BBB", NOW - timedelta(days=3), url="https://ex.com/bbb")

    r1 = sync_news_entities_to_stock_news(window_days=30, now=NOW)
    count1 = StockNews.objects.count()
    r2 = sync_news_entities_to_stock_news(window_days=30, now=NOW)
    count2 = StockNews.objects.count()

    assert count1 == count2 == 2         # 중복 누적 없음
    assert r2["created"] == 2
    assert r2["deleted"] == 2            # 2회차는 1회차 물질화분을 지우고 재삽입


# ── 창 경계 ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_window_boundary():
    from packages.shared.stocks.models import StockNews

    _mk_entity("INWIN", NOW - timedelta(days=5), url="https://ex.com/in")   # 창 내
    _mk_entity("OUTWIN", NOW - timedelta(days=40), url="https://ex.com/out")  # 창 밖

    sync_news_entities_to_stock_news(window_days=30, now=NOW)

    syms = set(StockNews.objects.values_list("symbol", flat=True))
    assert "INWIN" in syms
    assert "OUTWIN" not in syms


@pytest.mark.django_db
def test_window_replace_only_touches_window():
    """창 밖 기존 StockNews 행은 sync가 건드리지 않는다(창 단위 replace)."""
    from packages.shared.stocks.models import StockNews

    # 창 밖(40일 전) 기존 StockNews 행 — 다른 경로로 존재한다고 가정
    StockNews.objects.create(
        symbol="OLD", headline="old", published_at=NOW - timedelta(days=40)
    )
    _mk_entity("NEW", NOW - timedelta(days=1), url="https://ex.com/new")

    sync_news_entities_to_stock_news(window_days=30, now=NOW)

    syms = set(StockNews.objects.values_list("symbol", flat=True))
    assert "OLD" in syms   # 창 밖 → 보존
    assert "NEW" in syms   # 창 내 → 물질화


# ── url 절단 ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_url_truncation():
    from packages.shared.stocks.models import StockNews

    long_url = "https://ex.com/" + ("x" * 600)  # 600+ 자
    _mk_entity("LONG", NOW - timedelta(days=1), url=long_url)

    sync_news_entities_to_stock_news(window_days=30, now=NOW)
    row = StockNews.objects.get(symbol="LONG")
    assert len(row.url) == 500


# ── 빈 symbol 제외 ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_empty_symbol_excluded():
    from packages.shared.stocks.models import StockNews

    _mk_entity("", NOW - timedelta(days=1), url="https://ex.com/empty")
    _mk_entity("REAL", NOW - timedelta(days=1), url="https://ex.com/real")

    sync_news_entities_to_stock_news(window_days=30, now=NOW)
    syms = set(StockNews.objects.values_list("symbol", flat=True))
    assert syms == {"REAL"}


# ── enricher end-to-end 회귀 (V2 목표 증명) ──────────────────────────

@pytest.mark.django_db
def test_enricher_matches_after_sync():
    """sync로 StockNews 물질화 후 → 원 enricher(읽기 전용)가 실뉴스 매칭 성사."""
    from packages.shared.stocks.services.eod_news_enricher import EODNewsEnricher

    _mk_entity(
        "NVDA", NOW,  # 당일
        title="NVDA 급등 뉴스", url="https://ex.com/nvda",
        industry="Semiconductors", ent_sentiment=Decimal("0.80"),
    )
    sync_news_entities_to_stock_news(window_days=30, now=NOW)

    tagged = [{
        "stock_id": "NVDA", "sector": "Tech", "industry": "Semiconductors",
        "signals": [{"direction": "bullish"}],
    }]
    ctx = EODNewsEnricher().enrich(tagged, NOW.date())[0]["news_context"]

    assert ctx["match_type"] == "symbol_today"   # profile 폴백 이탈 = V2 목표
    assert ctx["headline"] == "NVDA 급등 뉴스"
    assert ctx["sentiment"] == "positive"


@pytest.mark.django_db
def test_enricher_profile_fallback_when_no_sync():
    """sync 미실행(StockNews 빈 상태) → 여전히 profile/none (정직성 — 없는 뉴스 안 만듦)."""
    from packages.shared.stocks.services.eod_news_enricher import EODNewsEnricher

    tagged = [{
        "stock_id": "NONE", "sector": "Tech", "industry": "X",
        "signals": [],
    }]
    ctx = EODNewsEnricher().enrich(tagged, NOW.date())[0]["news_context"]
    assert ctx["match_type"] in ("profile", "none")
