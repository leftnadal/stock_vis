"""Marketaux match_score 저장 정규화 회귀 (S4).

Marketaux match_score 는 상한 없는 relevance(실측 1.75~299.6)라 모델 [0,1] 제약을
위반한 채 저장돼 왔다. 저장 경로에서 100 saturation clamp 로 [0,1] 정규화한다.
"""
from decimal import Decimal

import pytest

from services.news.providers.marketaux import MarketauxNewsProvider


@pytest.fixture
def provider():
    return MarketauxNewsProvider(api_key="test_key", request_delay=0)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (58.1502, Decimal("0.581502")),   # 라이브 실측
        (9.438551, Decimal("0.09438551")),
        (100, Decimal("1.0")),
        (219.6874, Decimal("1.0")),       # 문서 예시 — clamp
        (299.577, Decimal("1.0")),        # 저장 max — clamp
        (0, Decimal("0")),
        (None, Decimal("1.0")),           # 미제공 = 기본 만점
    ],
)
def test_normalize_match_score(provider, raw, expected):
    assert provider._normalize_match_score(raw) == expected


def test_parse_article_stores_normalized_0_1(provider):
    """_parse_article 결과의 entity match_score 가 [0,1] 범위."""
    item = {
        "uuid": "u1", "title": "T", "description": "d",
        "url": "https://x.com/a", "published_at": "2026-07-13T00:00:00.000000Z",
        "source": "Src",
        "entities": [
            {"symbol": "AAPL", "name": "Apple", "type": "equity", "match_score": 58.15},
            {"symbol": "MSFT", "name": "MS", "type": "equity", "match_score": 250.0},
        ],
    }
    art = provider._parse_article(item)
    scores = [e["match_score"] for e in art.entities]
    assert all(Decimal("0") <= s <= Decimal("1") for s in scores)
    assert scores[0] == Decimal("0.5815")
    assert scores[1] == Decimal("1.0")  # clamp
