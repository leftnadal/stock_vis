"""
NewsAggregatorService._save_articles 기사별 savepoint 격리 회귀.

배치 중 한 기사의 DB 에러(필드 길이 초과 등)가 transaction을 오염시켜 나머지를
연쇄 실패시키던 버그(2026-07-04, AV broad 백필 596건 유실)의 회귀 방지.
정상 기사 사이에 '포이즌'(초장 url) 1건을 끼워 넣어, 그 1건만 skip되고 나머지는
전부 저장됨을 단언한다.
"""
from datetime import datetime, timezone

import pytest

from services.news.providers.base import RawNewsArticle
from services.news.services.aggregator import NewsAggregatorService
from services.news.models import NewsArticle


def _article(url, title):
    return RawNewsArticle(
        url=url,
        title=title,
        summary="s",
        source="Test",
        published_at=datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
        provider_name="alpha_vantage",
        provider_id=url,
        entities=[{"symbol": "NVDA", "entity_name": "NVDA", "entity_type": "equity",
                   "source": "alpha_vantage"}],
    )


@pytest.mark.django_db
def test_poison_article_isolated_by_savepoint():
    agg = NewsAggregatorService()
    poison_url = "https://x.com/" + "z" * 2100  # varchar(2000) 초과 → DataError 유발
    batch = [
        _article("https://ok.com/a", "A"),
        _article(poison_url, "POISON"),          # 이 1건만 실패해야
        _article("https://ok.com/b", "B"),
        _article("https://ok.com/c", "C"),
    ]

    saved, updated, skipped = agg._save_articles(batch)

    # 포이즌 1건만 skip, 정상 3건 저장 (오염 연쇄 실패 없음)
    assert saved == 3, f"savepoint 격리 실패 — saved={saved} (오염 연쇄 시 <3)"
    assert skipped == 1
    urls = set(NewsArticle.objects.values_list("url", flat=True))
    assert {"https://ok.com/a", "https://ok.com/b", "https://ok.com/c"} <= urls
    assert poison_url not in urls
