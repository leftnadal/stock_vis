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
        ("https://Example.com/A/", "https://example.com/a"),
        ("https://example.com/a?utm_source=x&y=1", "https://example.com/a"),
        ("  https://EXAMPLE.com/Path/  ", "https://example.com/path"),
        ("https://example.com/a", "https://example.com/a"),
        (None, ""),
        ("", ""),
    ],
)
def test_normalize_news_url_rules(raw, expected):
    assert normalize_news_url(raw) == expected


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
