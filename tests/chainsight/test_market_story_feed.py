"""R2-S2 — 오늘 시장의 이야기 피드 서비스 회귀.

임계 경계(일간급등 단일일·count·창)·fallback(정문 무공허)·혼합 정렬·cross-type dedup·
신뢰 위계(kind)·빈 윈도우. 마이그 0·prod write 0(읽기 서빙).
"""

import datetime

import pytest

from apps.chain_sight.models import CoMentionEdge, SymbolStoryActivity
from apps.chain_sight.services.market_story_feed import build_market_story_feed

NOW = datetime.datetime(2026, 9, 2, 12, 0, tzinfo=datetime.timezone.utc)


def _edge(a, b, count, last_days_ago, span_days=0):
    last = NOW.date() - datetime.timedelta(days=last_days_ago)
    first = last - datetime.timedelta(days=span_days)
    CoMentionEdge.objects.create(
        symbol_a=a, symbol_b=b, co_mention_count=count,
        last_co_mention_date=last, first_co_mention_date=first,
    )


def _cache(sym, partner, c7, last_days_ago=1):
    SymbolStoryActivity.objects.create(
        symbol=sym, partner=partner, count_7d=c7, count_90d=c7,
        weekly_avg_90d=float(c7), activity_ratio=1.0,
        last_co_mention_date=NOW.date() - datetime.timedelta(days=last_days_ago),
        thread_total=1, materialized_at=NOW,
    )


def _sec(a, b, rel, filing_days_ago, item="1.01"):
    from packages.shared.stocks.models import Stock
    from services.sec_pipeline.models import (
        SEC8KCounterpartyEvidence,
        SEC8KFiling,
    )

    st, _ = Stock.objects.get_or_create(symbol=a, defaults={"stock_name": a})
    fdate = NOW.date() - datetime.timedelta(days=filing_days_ago)
    f = SEC8KFiling.objects.create(
        symbol=st, cik="0000000001",
        accession_no=f"acc-{a}-{b}-{filing_days_ago}", filing_date=fdate,
    )
    SEC8KCounterpartyEvidence.objects.create(
        filing=f, source_symbol=a, resolved_ticker=b, raw_target_name=b,
        relationship_type=rel, item_code=item, filing_date=fdate, landed=True,
    )


@pytest.mark.django_db
class TestDailySpike:
    def test_single_day_high_count_within_window_included(self):
        _edge("ORCL", "PANW", 13, last_days_ago=12, span_days=0)  # 단일일·14일내·>=5
        feed = build_market_story_feed(now=NOW)
        spikes = [c for c in feed["cards"] if c["type"] == "daily_spike"]
        assert any(frozenset((c["symbol_a"], c["symbol_b"])) == frozenset(("ORCL", "PANW")) for c in spikes)
        card = spikes[0]
        assert card["count"] == 13
        assert card["occurred_on"] == (NOW.date() - datetime.timedelta(days=12)).isoformat()
        assert card["kind"] == "co_mention"

    def test_low_count_excluded(self):
        _edge("AAA", "BBB", 4, last_days_ago=1, span_days=0)  # count<5
        feed = build_market_story_feed(now=NOW)
        assert not [c for c in feed["cards"] if c["type"] == "daily_spike"]

    def test_multiday_excluded_from_spike(self):
        _edge("JPM", "BAC", 28, last_days_ago=1, span_days=6)  # 다일 span → 급등 아님
        feed = build_market_story_feed(now=NOW)
        assert not [c for c in feed["cards"] if c["type"] == "daily_spike"]

    def test_old_edge_excluded(self):
        _edge("AAA", "BBB", 20, last_days_ago=20, span_days=0)  # 14일 밖
        feed = build_market_story_feed(now=NOW)
        assert not [c for c in feed["cards"] if c["type"] == "daily_spike"]

    def test_companions_from_same_day(self):
        _edge("ORCL", "PANW", 13, last_days_ago=12, span_days=0)
        _edge("PANW", "TJX", 12, last_days_ago=12, span_days=0)  # 같은 날 클러스터
        feed = build_market_story_feed(now=NOW)
        card = next(c for c in feed["cards"] if frozenset((c["symbol_a"], c["symbol_b"])) == frozenset(("ORCL", "PANW")))
        assert "TJX" in card["companions"]


@pytest.mark.django_db
class TestWeeklyActive:
    def test_from_cache_top_by_count7d(self):
        _cache("JPM", "BAC", 27)
        _cache("BLK", "MS", 19)
        feed = build_market_story_feed(now=NOW)
        wa = [c for c in feed["cards"] if c["type"] == "weekly_active"]
        assert wa[0]["count"] == 27  # 내림차순
        assert wa[0]["kind"] == "co_mention"

    def test_undirected_dedup(self):
        _cache("JPM", "BAC", 27)
        _cache("BAC", "JPM", 27)  # 역방향 중복
        feed = build_market_story_feed(now=NOW)
        pairs = [frozenset((c["symbol_a"], c["symbol_b"])) for c in feed["cards"] if c["type"] == "weekly_active"]
        assert pairs.count(frozenset(("JPM", "BAC"))) == 1


@pytest.mark.django_db
class TestNewSec:
    def test_within_filing_window(self):
        _sec("MRVL", "GOOGL", "PARTNER_WITH", filing_days_ago=14)
        feed = build_market_story_feed(now=NOW)
        sec = [c for c in feed["cards"] if c["type"] == "new_sec"]
        assert len(sec) == 1
        assert sec[0]["kind"] == "sec_evidence"
        assert sec[0]["relation_type"] == "PARTNER_WITH"
        assert sec[0]["item_code"] == "1.01"

    def test_old_filing_excluded(self):
        _sec("AAA", "BBB", "PARTNER_WITH", filing_days_ago=40)  # 30일 밖
        feed = build_market_story_feed(now=NOW)
        assert not [c for c in feed["cards"] if c["type"] == "new_sec"]


@pytest.mark.django_db
class TestFeedComposition:
    def test_fallback_only_steady_no_events(self):
        # 사건(급등·SEC) 0 + steady 존재 → 정문 무공허, has_event False.
        _cache("JPM", "BAC", 27)
        _cache("BLK", "MS", 19)
        feed = build_market_story_feed(now=NOW)
        assert feed["has_event"] is False
        assert feed["summary"]["weekly_active"] == 2
        assert feed["total"] == 2
        assert all(c["type"] == "weekly_active" for c in feed["cards"])

    def test_empty_window(self):
        feed = build_market_story_feed(now=NOW)
        assert feed["cards"] == []
        assert feed["has_event"] is False
        assert feed["total"] == 0

    def test_sort_sec_then_spike_then_steady(self):
        _cache("JPM", "BAC", 27)
        _edge("ORCL", "PANW", 13, last_days_ago=1, span_days=0)
        _sec("MRVL", "GOOGL", "PARTNER_WITH", filing_days_ago=5)
        feed = build_market_story_feed(now=NOW)
        types = [c["type"] for c in feed["cards"]]
        assert types.index("new_sec") < types.index("daily_spike") < types.index("weekly_active")

    def test_cross_type_dedup_event_wins(self):
        # 같은 페어가 급등+steady 둘 다 → steady 에서 제거(사건 우선).
        _edge("ORCL", "PANW", 13, last_days_ago=1, span_days=0)
        _cache("ORCL", "PANW", 13)
        feed = build_market_story_feed(now=NOW)
        pairs_steady = [frozenset((c["symbol_a"], c["symbol_b"])) for c in feed["cards"] if c["type"] == "weekly_active"]
        assert frozenset(("ORCL", "PANW")) not in pairs_steady
        assert any(c["type"] == "daily_spike" for c in feed["cards"])

    def test_limit_cap(self):
        for i in range(40):
            _cache("HUB", f"P{i:02d}", 40 - i)
        feed = build_market_story_feed(now=NOW, limit=10)
        assert feed["total"] == 10
