"""MP-UX-S5-B-SECTOR-BE — _sector_detail sector_history 데이터원 테스트.

섹터 스파크라인(slice 2 FE) 데이터원(렌더 아님). breadth/concentration history_30d
패턴 미러 — 단 섹터×날짜 2-D, rel_strength only. SectorFlowSnapshot 실데이터만(합성 0).
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
    user = User.objects.create_user(username="sh", email="sh@e.com", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _url():
    return reverse("marketpulse_api_v2:card-detail", kwargs={"card_id": "sector"})


def _mk_index(symbol, grp=None):
    # MarketIndex(XL*)는 migration 0004로 test DB에 기시드 → get_or_create(충돌 방지).
    mi, _ = MarketIndex.objects.get_or_create(
        symbol=symbol,
        defaults={"name": symbol, "sector_group": grp or MarketIndex.SectorGroup.TECH},
    )
    return mi


def _mk_snap(mi, d, rel, rank=1):
    return SectorFlowSnapshot.objects.create(
        date=d, snapshot_time=timezone.now(), market_index=mi,
        rel_strength=Decimal(str(rel)),
        momentum_1d=Decimal("0.5"), momentum_5d=Decimal("0.5"), momentum_20d=Decimal("0.5"),
        flow_proxy=Decimal("0.3"),
        cross_dispersion=Decimal("0.8"), rotation_index=Decimal("1.5"),
        rank_in_universe=rank,
    )


@pytest.mark.django_db
class TestSectorHistory:
    def test_shape_and_order(self, auth_client):
        base = date_cls(2026, 6, 15)
        xlk = _mk_index("XLK", MarketIndex.SectorGroup.TECH)
        xle = _mk_index("XLE", MarketIndex.SectorGroup.ENERGY)
        # 3일치, 섹터 2개
        for i in range(3):
            d = base - timedelta(days=i)
            _mk_snap(xlk, d, 1.0 + i, rank=1)
            _mk_snap(xle, d, -1.0 - i, rank=2)

        body = auth_client.get(_url()).json()["data"]
        sh = body["sector_history"]
        # 2 섹터 그룹, sectors[]와 동일 rank 순(XLK rank1, XLE rank2)
        assert [g["symbol"] for g in sh] == ["XLK", "XLE"]
        xlk_hist = sh[0]["history"]
        # 날짜 오름차순(과거→현재)
        assert [p["date"] for p in xlk_hist] == [
            (base - timedelta(days=2)).isoformat(),
            (base - timedelta(days=1)).isoformat(),
            base.isoformat(),
        ]
        # 최신(base) rel_strength = 1.0 (i=0)
        assert xlk_hist[-1]["rel_strength"] == 1.0
        assert xlk_hist[0]["rel_strength"] == 3.0  # base-2 (i=2)

    def test_rel_strength_only_no_other_metrics(self, auth_client):
        """지표 격리 — history 포인트에 flow_proxy/momentum 없음, rel_strength만."""
        xlk = _mk_index("XLK")
        _mk_snap(xlk, date_cls(2026, 6, 15), 2.0)
        sh = auth_client.get(_url()).json()["data"]["sector_history"]
        point = sh[0]["history"][0]
        assert set(point.keys()) == {"date", "rel_strength"}
        assert "flow_proxy" not in point
        assert "momentum_1d" not in point and "momentum_5d" not in point

    def test_caps_at_30_dates(self, auth_client):
        base = date_cls(2026, 6, 15)
        xlk = _mk_index("XLK")
        for i in range(35):
            _mk_snap(xlk, base - timedelta(days=i), 1.0)
        sh = auth_client.get(_url()).json()["data"]["sector_history"]
        assert len(sh[0]["history"]) == 30  # 최근 30일로 절단

    def test_all_sectors_returned_no_truncation(self, auth_client):
        """11섹터 전부 반환(BE 절단 0). 여기선 5섹터로 검증."""
        base = date_cls(2026, 6, 15)
        syms = ["XLK", "XLE", "XLF", "XLV", "XLY"]
        for rank, s in enumerate(syms, 1):
            mi = _mk_index(s)
            _mk_snap(mi, base, float(rank), rank=rank)
        sh = auth_client.get(_url()).json()["data"]["sector_history"]
        assert len(sh) == 5
        assert {g["symbol"] for g in sh} == set(syms)

    def test_existing_fields_preserved(self, auth_client):
        """기존 필드 행위보존 — sectors[]/cross_dispersion/rotation_index 불변."""
        xlk = _mk_index("XLK")
        _mk_snap(xlk, date_cls(2026, 6, 15), 2.0, rank=1)
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is True
        assert body["cross_dispersion"] == 0.8
        assert body["rotation_index"] == 1.5
        assert len(body["sectors"]) == 1
        assert body["sectors"][0]["symbol"] == "XLK"
        assert body["sectors"][0]["rel_strength"] == 2.0
        # 기존 sectors[]엔 momentum/flow 유지(history만 rel_strength 격리)
        assert "flow_proxy" in body["sectors"][0]

    def test_no_snapshot_unavailable(self, auth_client):
        body = auth_client.get(_url()).json()["data"]
        assert body["available"] is False
        assert "sector_history" not in body
