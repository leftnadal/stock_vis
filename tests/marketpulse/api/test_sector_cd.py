"""MP2-SECTOR-CD Slice 1 — _sector_detail payload cd_state additive 테스트.

sectors[] 각 항목에 cd_state 필드가 서빙되는지 + 기존 키 불변(행위보존).
판정 로직은 payload builder 단독 거주 — 응답에 서빙된 값이 classify_cd_state와 일치.
"""
from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.market_pulse.models.snapshot import SectorFlowSnapshot
from macro.models.indicators import MarketIndex

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="cd", email="cd@e.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _url():
    return reverse("marketpulse_api_v2:card-detail", kwargs={"card_id": "sector"})


def _mk_index(symbol, grp=None):
    mi, _ = MarketIndex.objects.get_or_create(
        symbol=symbol,
        defaults={"name": symbol, "sector_group": grp or MarketIndex.SectorGroup.TECH},
    )
    return mi


def _mk_snap(mi, d, rel, mom5, rank=1):
    return SectorFlowSnapshot.objects.create(
        date=d, snapshot_time=timezone.now(), market_index=mi,
        rel_strength=Decimal(str(rel)),
        momentum_1d=Decimal("0.1"), momentum_5d=Decimal(str(mom5)), momentum_20d=Decimal("0.2"),
        flow_proxy=Decimal("0.3"),
        cross_dispersion=Decimal("0.8"), rotation_index=Decimal("1.5"),
        rank_in_universe=rank,
    )


@pytest.mark.django_db
class TestSectorCdState:
    def test_cd_state_present_all_quadrants(self, auth_client):
        """사분면 4섹터 → 각 cd_state 정확 서빙."""
        base = date_cls(2026, 6, 15)
        # (rel, mom5) → 기대 상태
        cases = [
            ("XLK", 0.5, 0.5, "leading_strengthening"),
            ("XLE", 0.5, -0.5, "leading_weakening"),
            ("XLF", -0.5, 0.5, "lagging_improving"),
            ("XLV", -0.5, -0.5, "lagging_deteriorating"),
        ]
        for rank, (sym, rel, mom5, _exp) in enumerate(cases, 1):
            _mk_snap(_mk_index(sym), base, rel, mom5, rank=rank)

        sectors = auth_client.get(_url()).json()["data"]["sectors"]
        by_sym = {s["symbol"]: s for s in sectors}
        for sym, _rel, _mom5, exp in cases:
            assert by_sym[sym]["cd_state"] == exp

    def test_cd_state_boundary_lower_attribution(self, auth_client):
        """경계 동률(rel==0, mom==0) → 하위 상태(lagging_deteriorating)."""
        _mk_snap(_mk_index("XLK"), date_cls(2026, 6, 15), 0.0, 0.0, rank=1)
        sectors = auth_client.get(_url()).json()["data"]["sectors"]
        assert sectors[0]["cd_state"] == "lagging_deteriorating"

    def test_existing_keys_unchanged_snapshot(self, auth_client):
        """기존 sectors[] 키 불변 — cd_state additive만."""
        _mk_snap(_mk_index("XLK"), date_cls(2026, 6, 15), 2.0, 0.5, rank=1)
        row = auth_client.get(_url()).json()["data"]["sectors"][0]
        assert set(row.keys()) == {
            "symbol", "rel_strength", "momentum_1d", "momentum_5d",
            "momentum_20d", "flow_proxy", "rank", "cd_state",
        }
        # 기존 값 행위보존
        assert row["symbol"] == "XLK"
        assert row["rel_strength"] == 2.0
        assert row["momentum_5d"] == 0.5
        assert row["rank"] == 1
