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


def _chain_event(symbol, co_syms, title, days_ago, url="http://cne/x"):
    from apps.chain_sight.models.news_event import ChainNewsEvent
    from packages.shared.stocks.models import Stock

    Stock.objects.get_or_create(symbol=symbol, defaults={"stock_name": symbol})
    pub = NOW - datetime.timedelta(days=days_ago)
    return ChainNewsEvent.objects.create(
        symbol_id=symbol, source="marketaux", source_id=f"cne-{symbol}-{title[:8]}",
        title=title, url=url, published_at=pub, co_mentioned_symbols=list(co_syms),
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

    def test_same_day_shared_member_merges_into_one_group_card(self):
        # A-2: 같은 날 멤버 공유 쌍 → 묶음 카드 1장(members 합집합·pairs 보존).
        _edge("ORCL", "PANW", 13, last_days_ago=12, span_days=0)
        _edge("PANW", "TJX", 12, last_days_ago=12, span_days=0)  # PANW 공유 → 병합
        feed = build_market_story_feed(now=NOW)
        spikes = [c for c in feed["cards"] if c["type"] == "daily_spike"]
        assert len(spikes) == 1
        card = spikes[0]
        assert card["is_group"] is True
        assert set(card["members"]) == {"ORCL", "PANW", "TJX"}
        assert len(card["pairs"]) == 2
        assert card["max_mentions"] == 13
        # 상위 쌍 = 최다 언급(ORCL-PANW 13)
        assert frozenset((card["symbol_a"], card["symbol_b"])) == frozenset(("ORCL", "PANW"))


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

    def test_sort_same_day_type_tiebreak_sec_spike_steady(self):
        # A-5 정렬: occurred_on desc 우선 → 동일일이면 사건성(sec>spike>steady) tiebreak.
        _cache("JPM", "BAC", 27, last_days_ago=1)
        _edge("ORCL", "PANW", 13, last_days_ago=1, span_days=0)
        _sec("MRVL", "GOOGL", "PARTNER_WITH", filing_days_ago=1)  # 동일일로 맞춤
        feed = build_market_story_feed(now=NOW)
        types = [c["type"] for c in feed["cards"]]
        assert types.index("new_sec") < types.index("daily_spike") < types.index("weekly_active")

    def test_sort_event_tier_beats_recency(self):
        # 확정 스펙: 사건성 1차 → 오래된 SEC(20일 전)도 최신 급등(어제)보다 위.
        _edge("ORCL", "PANW", 13, last_days_ago=1, span_days=0)   # 어제
        _sec("MRVL", "GOOGL", "PARTNER_WITH", filing_days_ago=20)  # 20일 전(창내)
        feed = build_market_story_feed(now=NOW)
        types = [c["type"] for c in feed["cards"]]
        assert types.index("new_sec") < types.index("daily_spike")

    def test_sort_key_places_sec_above_recent_steady(self):
        # 디렉터 확정: 그저께 new_sec 1건 + 어제 weekly_active 2건 → new_sec가 index 0.
        _sec("MRVL", "GOOGL", "PARTNER_WITH", filing_days_ago=2)   # 그저께
        _cache("JPM", "BAC", 27, last_days_ago=1)                   # 어제
        _cache("BLK", "MS", 19, last_days_ago=1)                    # 어제
        feed = build_market_story_feed(now=NOW)
        assert feed["cards"][0]["type"] == "new_sec"

    def test_sort_within_tier_recent_first(self):
        # 같은 티어(daily_spike) 안에서는 occurred_on desc(최근 발생일 먼저).
        _edge("AAA", "BBB", 9, last_days_ago=6, span_days=0)   # 6일 전
        _edge("CCC", "DDD", 8, last_days_ago=2, span_days=0)   # 2일 전(더 최근)
        feed = build_market_story_feed(now=NOW)
        spikes = [c for c in feed["cards"] if c["type"] == "daily_spike"]
        assert spikes[0]["occurred_on"] > spikes[1]["occurred_on"]

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


@pytest.mark.django_db
class TestGrouping:
    def test_disjoint_same_day_two_group_cards(self):
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        _edge("AAA", "BBB", 9, last_days_ago=2, span_days=0)  # 멤버 공유 없음
        feed = build_market_story_feed(now=NOW)
        spikes = [c for c in feed["cards"] if c["type"] == "daily_spike"]
        assert len(spikes) == 2

    def test_single_pair_group_shape(self):
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        feed = build_market_story_feed(now=NOW)
        card = [c for c in feed["cards"] if c["type"] == "daily_spike"][0]
        assert card["is_group"] is True
        assert set(card["members"]) == {"ORCL", "PANW"}
        assert len(card["pairs"]) == 1
        assert card["count"] == 13  # backward compat = max_mentions

    def test_companions_outside_excludes_members(self):
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        _edge("PANW", "TJX", 12, last_days_ago=2, span_days=0)   # TJX = 멤버
        _edge("ORCL", "EBAY", 8, last_days_ago=2, span_days=0)   # EBAY = 멤버(ORCL 공유)
        feed = build_market_story_feed(now=NOW)
        card = [c for c in feed["cards"] if c["type"] == "daily_spike"][0]
        assert {"ORCL", "PANW", "TJX", "EBAY"} <= set(card["members"])
        assert "TJX" not in card["companions_outside"]
        assert "EBAY" not in card["companions_outside"]

    def test_different_days_not_merged(self):
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        _edge("PANW", "TJX", 12, last_days_ago=5, span_days=0)  # 다른 날 → 병합 안 함
        feed = build_market_story_feed(now=NOW)
        spikes = [c for c in feed["cards"] if c["type"] == "daily_spike"]
        assert len(spikes) == 2


@pytest.mark.django_db
class TestStoryId:
    def test_cards_have_deterministic_story_id_and_key(self):
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        _sec("MRVL", "GOOGL", "PARTNER_WITH", filing_days_ago=3)
        f1 = build_market_story_feed(now=NOW)
        f2 = build_market_story_feed(now=NOW)
        for c in f1["cards"]:
            assert len(c["story_id"]) == 10
            int(c["story_id"], 16)
            assert ":" in c["story_key"]
        # 결정론: 같은 입력 → 같은 id
        ids1 = {c["story_key"]: c["story_id"] for c in f1["cards"]}
        ids2 = {c["story_key"]: c["story_id"] for c in f2["cards"]}
        assert ids1 == ids2


@pytest.mark.django_db
class TestTitles:
    def test_8k_card_title_template(self):
        _sec("MRVL", "GOOGL", "PARTNER_WITH", filing_days_ago=3, item="1.01")
        feed = build_market_story_feed(now=NOW)
        sec = [c for c in feed["cards"] if c["type"] == "new_sec"][0]
        assert sec["title"] == "MRVL, GOOGL와 중요 계약 체결 공시"

    def test_co_mention_card_title_from_article_quote(self):
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        _chain_event("ORCL", ["PANW"], "오라클·팔로알토 클라우드 계약", days_ago=2)
        feed = build_market_story_feed(now=NOW)
        card = [c for c in feed["cards"] if c["type"] == "daily_spike"][0]
        assert card["title"] == "오라클·팔로알토 클라우드 계약"  # 원문 인용

    def test_co_mention_card_title_null_when_no_article(self):
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        feed = build_market_story_feed(now=NOW)
        card = [c for c in feed["cards"] if c["type"] == "daily_spike"][0]
        assert card["title"] is None


@pytest.mark.django_db
class TestHeaderMeta:
    def test_meta_new_today_counts_today_cards(self):
        _edge("ORCL", "PANW", 13, last_days_ago=0, span_days=0)  # 오늘 발생
        _edge("AAA", "BBB", 9, last_days_ago=3, span_days=0)     # 3일 전
        feed = build_market_story_feed(now=NOW)
        assert feed["meta"]["new_today"] == 1
        assert feed["meta"]["stories"] == feed["total"]
        assert set(feed["meta"]["by_type"]) == {"new_sec", "daily_spike", "weekly_active"}

    def test_meta_new_today_zero_ok(self):
        _cache("JPM", "BAC", 27, last_days_ago=2)
        feed = build_market_story_feed(now=NOW)
        assert feed["meta"]["new_today"] == 0

    def test_meta_has_no_single_window_claim(self):
        # 발견 2(B안): 단일 창 N이 없다 → meta 에 window 필드 없음.
        _cache("JPM", "BAC", 27, last_days_ago=2)
        feed = build_market_story_feed(now=NOW)
        assert "window" not in feed["meta"]
        assert "window_days" not in feed["meta"]


@pytest.mark.django_db
class TestCardWindow:
    def test_each_card_states_own_window_label(self):
        # B안(디렉터 확정): 카드가 자기 창을 문자열로 말함(window_label).
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        _sec("MRVL", "GOOGL", "PARTNER_WITH", filing_days_ago=3)
        _cache("JPM", "BAC", 27, last_days_ago=2)
        feed = build_market_story_feed(now=NOW)
        wl = {c["type"]: c["window_label"] for c in feed["cards"]}
        assert wl["daily_spike"] == "14일 중 이 하루"
        assert wl["new_sec"] == "30일 내 신규 공시"
        assert wl["weekly_active"] == "최근 7일 활동"

    def test_window_label_derives_from_constant(self, monkeypatch):
        # 하드코딩 금지: 상수를 바꾸면 문구가 따라온다.
        import apps.chain_sight.services.market_story_feed as msf
        monkeypatch.setattr(msf, "DAILY_SPIKE_DAYS", 9)
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        feed = build_market_story_feed(now=NOW)
        card = [c for c in feed["cards"] if c["type"] == "daily_spike"][0]
        assert card["window_label"] == "9일 중 이 하루"


@pytest.mark.django_db
class TestEvidence:
    def test_8k_evidence_schema(self):
        _sec("MRVL", "GOOGL", "PARTNER_WITH", filing_days_ago=3)
        feed = build_market_story_feed(now=NOW)
        sec = [c for c in feed["cards"] if c["type"] == "new_sec"][0]
        assert len(sec["evidence"]) >= 1
        ev = sec["evidence"][0]
        assert ev["kind"] == "8k"
        assert set(ev) == {"kind", "ref", "title", "url", "date"}

    def test_article_evidence_schema(self):
        _edge("ORCL", "PANW", 13, last_days_ago=2, span_days=0)
        _chain_event("ORCL", ["PANW"], "동반 기사", days_ago=2)
        feed = build_market_story_feed(now=NOW)
        card = [c for c in feed["cards"] if c["type"] == "daily_spike"][0]
        assert card["evidence"][0]["kind"] == "article"
        assert set(card["evidence"][0]) == {"kind", "ref", "title", "url", "date"}
