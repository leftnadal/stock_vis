"""URL 정규화 provider 공통화 + cross-provider dedup 회귀 (S3).

과거: AV/FMP 는 raw url, finnhub/marketaux 만 정규화 → 같은 기사가 provider별로 다른
url 로 저장돼 이중 NewsArticle → co-mention 왜곡. 정규화를 url_utils 단일 소스로 통일하고
모든 provider 가 동일 규칙을 쓰도록 했다.
"""
from datetime import datetime, timezone

import pytest

from services.news.models import NewsArticle
from services.news.providers.base import RawNewsArticle
from services.news.providers.url_utils import normalize_news_url
from services.news.services.aggregator import NewsAggregatorService


@pytest.mark.parametrize(
    "raw,expected",
    [
        # (a) 무쿼리 / 슬래시·대소문자 정규화 (구 규칙과 동일)
        ("https://Example.com/A/", "https://example.com/a"),
        ("  https://EXAMPLE.com/Path/  ", "https://example.com/path"),
        ("https://example.com/a", "https://example.com/a"),
        (None, ""),
        ("", ""),
        # (b) tracking-only → 구 규칙과 동일하게 base 만 (IDENTICAL)
        ("https://x.com/a?utm_source=z&utm_medium=e", "https://x.com/a"),
        ("https://x.com/a?fbclid=123", "https://x.com/a"),
        ("https://x.com/a?gclid=1", "https://x.com/a"),
        ("https://x.com/a?ref=twitter", "https://x.com/a"),
        # (c) id 보존 (NEWS-URLNORM-IDQUERY 수정 목표)
        ("https://www.youtube.com/watch?v=abc", "https://www.youtube.com/watch?v=abc"),
        ("https://finviz.com/quote?t=aapl", "https://finviz.com/quote?t=aapl"),
        # (c) tracking 만 제거하고 id 는 보존
        ("https://example.com/a?utm_source=x&y=1", "https://example.com/a?y=1"),
        ("https://x.com/a?gclid=1&id=99", "https://x.com/a?id=99"),
        # ambiguous key(ocid)는 blocklist 미포함 → 보존(과소병합=가역)
        ("https://msn.com/x?ocid=abc", "https://msn.com/x?ocid=abc"),
    ],
)
def test_normalize_news_url_rules(raw, expected):
    assert normalize_news_url(raw) == expected


def _old_normalize(u):
    """구 규칙(쿼리 전량 제거) — 행위보존 오라클."""
    n = (u or "").strip().lower()
    if "?" in n:
        n = n.split("?")[0]
    if n.endswith("/"):
        n = n[:-1]
    return n


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.com/a",                 # (a)
        "https://EXAMPLE.com/Path/",             # (a)
        "https://x.com/a?utm_source=z",          # (b)
        "https://x.com/a?fbclid=1&utm_medium=e",  # (b)
        "https://x.com/a#frag",                  # (a) fragment 보존(구 규칙 동치)
        "",
    ],
)
def test_behavior_preserved_for_noquery_and_tracking_only(raw):
    """(a)무쿼리·(b)tracking-only 는 구 규칙과 IDENTICAL (골든셋 회귀)."""
    assert normalize_news_url(raw) == _old_normalize(raw)


def test_collapse_groups_now_split_by_id():
    """구 규칙이 붕괴시키던 공유경로 URL 이 id 별로 distinct 키가 된다."""
    yt = ["https://www.youtube.com/watch?v=abc", "https://www.youtube.com/watch?v=xyz"]
    fv = ["https://finviz.com/quote?t=aapl", "https://finviz.com/quote?t=msft"]
    # 구 규칙: 각 그룹이 1키로 붕괴
    assert len({_old_normalize(u) for u in yt}) == 1
    assert len({_old_normalize(u) for u in fv}) == 1
    # 신 규칙: 각 원본이 distinct 키
    assert len({normalize_news_url(u) for u in yt}) == 2
    assert len({normalize_news_url(u) for u in fv}) == 2


def test_all_providers_share_one_normalization():
    """4개 provider 가 base.normalize_url 로 동일 규칙(단일 소스)을 쓴다."""
    from services.news.providers.base import BaseNewsProvider

    messy = "https://News.SITE.com/Story/?utm_campaign=z"
    want = normalize_news_url(messy)

    # 각 provider 인스턴스 없이도 base 메서드가 util 에 위임함을 확인
    class _P(BaseNewsProvider):
        def fetch_company_news(self, *a, **k):
            return []

        def fetch_market_news(self, *a, **k):
            return []

        def get_rate_limit_key(self):
            return "k"

        def get_rate_limit(self):
            return {}

    assert _P().normalize_url(messy) == want == "https://news.site.com/story"


def _article(url, provider_name, provider_id, symbol):
    return RawNewsArticle(
        url=url,
        title="T",
        summary="s",
        source="Test",
        published_at=datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
        provider_name=provider_name,
        provider_id=provider_id,
        entities=[{"symbol": symbol, "entity_name": symbol, "entity_type": "equity",
                   "source": provider_name}],
    )


@pytest.mark.django_db
def test_cross_provider_same_url_dedups_to_one_row(settings):
    """AV·Marketaux 가 정규화 후 같은 url 을 내면 NewsArticle 은 1행으로 병합된다."""
    settings.FINNHUB_API_KEY = ""
    settings.MARKETAUX_API_KEY = ""  # S5 덕에 키 없이 인스턴스화

    agg = NewsAggregatorService()
    same_url = "https://pub.com/story-x"  # 두 provider 가 동일 정규화 url 산출 가정
    batch = [
        _article(same_url, "alpha_vantage", "avid1", "NVDA"),
        _article(same_url, "marketaux", "mkxuuid1", "AAPL"),
    ]

    saved, updated, skipped = agg._save_articles(batch)

    assert saved == 1, f"cross-provider dedup 실패 — saved={saved} (2면 이중저장)"
    assert updated == 1
    assert NewsArticle.objects.filter(url=same_url).count() == 1
