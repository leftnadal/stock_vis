"""CS-S3-1 — MarketStoryFeedView 계약 + 응답 캐시(0-2 p95>150ms → 뷰 캐시).

읽기 전용(prod write 0). 캐시 격리 = settings_test LocMemCache(#27).
"""

import datetime

import pytest
from django.core.cache import cache
from rest_framework.test import APIRequestFactory

from apps.chain_sight.api.feed_views import MarketStoryFeedView
from apps.chain_sight.models import SymbolStoryActivity

NOW = datetime.datetime(2026, 9, 2, 12, 0, tzinfo=datetime.timezone.utc)


def _cache_row(sym, partner, c7):
    SymbolStoryActivity.objects.create(
        symbol=sym, partner=partner, count_7d=c7, count_90d=c7,
        weekly_avg_90d=float(c7), activity_ratio=1.0,
        last_co_mention_date=NOW.date() - datetime.timedelta(days=1),
        thread_total=1, materialized_at=NOW,
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestFeedView:
    def test_returns_meta_and_cards(self):
        _cache_row("JPM", "BAC", 27)
        req = APIRequestFactory().get("/api/v1/chainsight/feed/")
        resp = MarketStoryFeedView.as_view()(req)
        assert resp.status_code == 200
        assert "meta" in resp.data
        assert set(resp.data["meta"]) == {"as_of", "new_today", "stories", "by_type"}
        assert isinstance(resp.data["cards"], list)

    def test_response_is_cached(self, monkeypatch):
        _cache_row("JPM", "BAC", 27)
        calls = {"n": 0}
        import apps.chain_sight.api.feed_views as fv
        real = fv.build_market_story_feed

        def counting(*a, **k):
            calls["n"] += 1
            return real(*a, **k)

        monkeypatch.setattr(fv, "build_market_story_feed", counting)
        view = MarketStoryFeedView.as_view()
        MarketStoryFeedView.as_view()  # noqa
        view(APIRequestFactory().get("/api/v1/chainsight/feed/?limit=30"))
        view(APIRequestFactory().get("/api/v1/chainsight/feed/?limit=30"))
        assert calls["n"] == 1  # 두 번째는 캐시 히트

    def test_different_limit_separate_cache(self, monkeypatch):
        _cache_row("JPM", "BAC", 27)
        calls = {"n": 0}
        import apps.chain_sight.api.feed_views as fv
        real = fv.build_market_story_feed
        monkeypatch.setattr(
            fv, "build_market_story_feed",
            lambda *a, **k: (calls.__setitem__("n", calls["n"] + 1) or real(*a, **k)),
        )
        view = MarketStoryFeedView.as_view()
        view(APIRequestFactory().get("/api/v1/chainsight/feed/?limit=10"))
        view(APIRequestFactory().get("/api/v1/chainsight/feed/?limit=30"))
        assert calls["n"] == 2  # limit 다르면 별도 캐시
