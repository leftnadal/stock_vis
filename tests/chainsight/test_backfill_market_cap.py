"""⑳-3 S3-MINDMAP S1 — mcap 백필 헬퍼."""

import pytest

from apps.chain_sight.management.commands.backfill_market_cap import (
    _market_cap,
    serving_symbols,
)
from apps.chain_sight.models import RelationConfidence


class TestMarketCapField:
    def test_extracts_marketcap_key(self):
        assert _market_cap({"marketCap": 123}) == 123

    def test_field_name_fallback(self):
        assert _market_cap({"market_cap": 456}) == 456
        assert _market_cap({"marketCapitalization": 789}) == 789

    def test_missing_returns_none(self):
        assert _market_cap({"price": 10}) is None
        assert _market_cap({"marketCap": 0}) is None  # 0은 결측 취급


@pytest.mark.django_db
def test_serving_symbols_excludes_rejected():
    RelationConfidence.objects.create(
        symbol_a="AAA", symbol_b="BBB", relation_type="PEER_OF",
        relation_category="truth",
    )
    r = RelationConfidence.objects.create(
        symbol_a="CCC", symbol_b="DDD", relation_type="PEER_OF",
        relation_category="truth", domain_review_status="rejected",
    )
    syms = serving_symbols()
    assert "AAA" in syms and "BBB" in syms
    assert "CCC" not in syms and "DDD" not in syms  # rejected 제외
