"""MP2-SECTOR-CD Slice 2 — sector_history per-date momentum_5d 노출 + baseline 메타.

momentum_5d는 저장 필드 노출(재계산 0). null 저장은 null 그대로 서빙.
판정선 단일소스 = payload 메타 cd_momentum_baseline(= CD_MOMENTUM_BASELINE 상수).
"""
from __future__ import annotations

from datetime import date as date_cls
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.market_pulse.constants import CD_MOMENTUM_BASELINE
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
    user = User.objects.create_user(username="sm", email="sm@e.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _url():
    return reverse("marketpulse_api_v2:card-detail", kwargs={"card_id": "sector"})


def _mk_index(symbol):
    mi, _ = MarketIndex.objects.get_or_create(
        symbol=symbol,
        defaults={"name": symbol, "sector_group": MarketIndex.SectorGroup.TECH},
    )
    return mi


def _mk_snap(mi, d, rel, mom5, rank=1):
    return SectorFlowSnapshot.objects.create(
        date=d, snapshot_time=timezone.now(), market_index=mi,
        rel_strength=Decimal(str(rel)),
        momentum_1d=Decimal("0.1"),
        momentum_5d=None if mom5 is None else Decimal(str(mom5)),
        momentum_20d=Decimal("0.2"),
        flow_proxy=Decimal("0.3"),
        cross_dispersion=Decimal("0.8"), rotation_index=Decimal("1.5"),
        rank_in_universe=rank,
    )


@pytest.mark.django_db
class TestSectorMomentumExposure:
    def test_per_date_momentum_exposed_and_matches_storage(self, auth_client):
        """날짜별 momentum_5d 노출 + 저장값 대조(재계산 0)."""
        base = date_cls(2026, 6, 15)
        xlk = _mk_index("XLK")
        # 날짜별 상이한 momentum 저장
        _mk_snap(xlk, base - timedelta(days=2), 1.0, -1.5, rank=1)
        _mk_snap(xlk, base - timedelta(days=1), 1.0, 0.75, rank=1)
        _mk_snap(xlk, base, 1.0, 2.25, rank=1)
        hist = auth_client.get(_url()).json()["data"]["sector_history"][0]["history"]
        # 날짜 오름차순, 저장값 그대로
        assert [p["momentum_5d"] for p in hist] == [-1.5, 0.75, 2.25]

    def test_momentum_field_is_non_nullable(self):
        """STEP 0-2 확증 — momentum_5d 필드는 non-nullable(저장 null 불가 → NULL 0건 근거).
        따라서 payload의 방어 가드(None→None)는 도달 불가 dead path이나 미래 방어용 유지.
        """
        field = SectorFlowSnapshot._meta.get_field("momentum_5d")
        assert field.null is False

    def test_existing_keys_unchanged(self, auth_client):
        """rel_strength·rank 기존 키 불변 — momentum_5d additive만."""
        xlk = _mk_index("XLK")
        _mk_snap(xlk, date_cls(2026, 6, 15), 2.0, 0.5, rank=1)
        point = auth_client.get(_url()).json()["data"]["sector_history"][0]["history"][0]
        assert set(point.keys()) == {"date", "rel_strength", "rank", "momentum_5d"}
        assert point["rel_strength"] == 2.0
        assert point["rank"] == 1


@pytest.mark.django_db
class TestCdMomentumBaselineMeta:
    def test_baseline_meta_present_and_matches_constant(self, auth_client):
        """payload 메타 cd_momentum_baseline = CD_MOMENTUM_BASELINE 상수(값 복제 아님)."""
        _mk_snap(_mk_index("XLK"), date_cls(2026, 6, 15), 2.0, 0.5, rank=1)
        body = auth_client.get(_url()).json()["data"]
        assert "cd_momentum_baseline" in body
        assert body["cd_momentum_baseline"] == CD_MOMENTUM_BASELINE

    def test_baseline_absent_when_unavailable(self, auth_client):
        """스냅샷 없으면 unavailable — baseline 메타 미포함."""
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is False
        assert "cd_momentum_baseline" not in body
