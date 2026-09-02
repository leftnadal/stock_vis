"""R2-S1 — co-mention 파트너 활동 스레드 집계 정확성.

7일/90일 경계·주간평균 비율·조용함(quiet) 플래그·활동순 정렬·상한·빈상태.
소스=CoMentionEdge(90d/last) + NewsEntity(7d live). 마이그0.
"""

import datetime

import pytest
from django.test import Client
from django.utils import timezone

from apps.chain_sight.models import CoMentionEdge
from apps.chain_sight.services.story_activity import get_symbol_story_threads
from services.news.models import NewsArticle, NewsEntity

NOW = datetime.datetime(2026, 8, 28, 12, 0, tzinfo=datetime.timezone.utc)


def _edge(a, b, count90, last_days_ago):
    CoMentionEdge.objects.create(
        symbol_a=a, symbol_b=b, co_mention_count=count90,
        last_co_mention_date=(NOW.date() - datetime.timedelta(days=last_days_ago)),
        first_co_mention_date=NOW.date() - datetime.timedelta(days=89),
    )


_seq = [0]


def _article(symbols, days_ago):
    _seq[0] += 1
    art = NewsArticle.objects.create(
        url=f"http://x/{_seq[0]}", url_hash=f"h{_seq[0]}", title="t", source="av",
        published_at=NOW - datetime.timedelta(days=days_ago),
    )
    for s in symbols:
        NewsEntity.objects.create(
            news=art, symbol=s, entity_name=s, entity_type="equity", source="av"
        )
    return art


@pytest.mark.django_db
class TestStoryActivity:
    def test_counts_ratio_and_quiet(self):
        # R2-S2 ⑷: weekly_avg 분모 = 페어 실관측 스팬(주). _edge 헬퍼 span=88일(≈12.57주).
        # BBB: 90/12.57=7.16(주간평균), 7일 내 3기사 → 7d=3, ratio=3/7.16=0.42.
        _edge("AAA", "BBB", 90, last_days_ago=1)
        for d in (1, 3, 6):
            _article(["AAA", "BBB"], days_ago=d)
        # CCC: 마지막 40일 전(7일 내 0) → quiet
        _edge("AAA", "CCC", 13, last_days_ago=40)

        out = get_symbol_story_threads("AAA", now=NOW)
        by = {t["partner"]: t for t in out["threads"]}
        assert out["thread_total"] == 2
        assert by["BBB"]["count_7d"] == 3
        assert by["BBB"]["count_90d"] == 90
        assert by["BBB"]["weekly_avg_90d"] == 7.16
        assert by["BBB"]["activity_ratio"] == 0.42
        assert by["BBB"]["quiet"] is False
        assert by["CCC"]["count_7d"] == 0
        assert by["CCC"]["quiet"] is True
        assert by["CCC"]["days_since"] == 40

    def test_7d_boundary(self):
        _edge("AAA", "BBB", 30, last_days_ago=1)
        _article(["AAA", "BBB"], days_ago=6)  # 창 안
        _article(["AAA", "BBB"], days_ago=8)  # 창 밖
        out = get_symbol_story_threads("AAA", now=NOW)
        assert out["threads"][0]["count_7d"] == 1  # 6일만 포함, 8일 제외

    def test_sort_by_activity_desc(self):
        _edge("AAA", "LOW", 60, last_days_ago=1)
        _edge("AAA", "HIGH", 20, last_days_ago=1)
        for _ in range(5):
            _article(["AAA", "HIGH"], days_ago=2)
        _article(["AAA", "LOW"], days_ago=2)
        out = get_symbol_story_threads("AAA", now=NOW)
        assert [t["partner"] for t in out["threads"]] == ["HIGH", "LOW"]  # 7d 활동순

    def test_cap_top_n(self):
        for i in range(15):
            _edge("AAA", f"P{i:02d}", 10 + i, last_days_ago=1)
        out = get_symbol_story_threads("AAA", top_n=10, now=NOW)
        assert out["shown"] == 10
        assert out["thread_total"] == 15
        assert out["threads_capped"] is True

    def test_empty_no_partners(self):
        out = get_symbol_story_threads("ZZZ", now=NOW)
        assert out == {"threads": [], "thread_total": 0, "threads_capped": False, "shown": 0}

    def test_card_api_includes_story(self):
        _edge("AAA", "BBB", 14, last_days_ago=2)
        _article(["AAA", "BBB"], days_ago=1)
        d = Client().get("/api/v1/chainsight/mindmap/card/AAA/").json()
        assert "story" in d
        assert d["story"]["thread_total"] == 1
        assert d["story"]["threads"][0]["partner"] == "BBB"
        assert d["story"]["threads"][0]["partner_name"] == "BBB"
