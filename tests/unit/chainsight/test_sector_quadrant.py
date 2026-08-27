"""QUAD-IMPL-1 Slice 1 — 섹터 사분면 read-only API/서비스 테스트.

케이스: 정상 / heat null / suppression(§2 재사용) + API 배선.
주의: test DB에 HeatEntity 11섹터가 시드됨(#27 SeedSnapshot) → get_or_create 사용,
      날짜는 시드/실데이터 간섭 회피용 far-future(2099)로 최신 보장. 특정 섹터 부분집합 단언.
"""
import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.chain_sight.models import (
    HeatEntity,
    SymbolDemandSignal,
    ThemeDemandScore,
    ThemeHeatScore,
)
from apps.chain_sight.services.sector_quadrant import build_quadrant

HEAT_DATE = date(2099, 1, 26)
ANCHOR_CURR = date(2099, 1, 21)
ANCHOR_PREV = date(2099, 1, 14)


def _sector(ref_id):
    obj, _ = HeatEntity.objects.get_or_create(
        kind=HeatEntity.KIND_SECTOR, ref_id=ref_id,
        defaults={"constituent_policy": "static"},
    )
    return obj


def _heat(entity, score, d=HEAT_DATE):
    return ThemeHeatScore.objects.create(
        theme=entity, date=d, score=score, status="warning", components={}
    )


def _demand(entity, d, breadth, denom):
    return ThemeDemandScore.objects.create(
        theme=entity, date=d, score=50, status="neutral",
        components={"breadth": breadth, "valid_denom": denom, "up": 0, "down": 0, "flat": 0},
    )


def _signals(anchor, up=0, down=0, flat=0, excl=0):
    """flat_ratio 제어용 SymbolDemandSignal 생성."""
    objs, i = [], 0
    for direction, cnt in ((1, up), (-1, down), (0, flat)):
        for _ in range(cnt):
            objs.append(SymbolDemandSignal(
                symbol=f"S{i}", anchor_date=anchor, fiscal_year=2100,
                direction=direction, excluded=False))
            i += 1
    for _ in range(excl):
        objs.append(SymbolDemandSignal(
            symbol=f"S{i}", anchor_date=anchor, fiscal_year=2100,
            direction=None, excluded=True, exclude_reason="analyst_delta"))
        i += 1
    SymbolDemandSignal.objects.bulk_create(objs)


@pytest.mark.django_db
def test_quadrant_normal():
    """정상: heat + breadth(2 anchor), 저 flat → arrow 미숨김."""
    for ref, sc, b in (("Technology", 50, 0.3), ("Healthcare", 48, 0.1), ("Energy", 42, -0.2)):
        e = _sector(ref)
        _heat(e, sc)
        _demand(e, ANCHOR_CURR, b, 20)
        _demand(e, ANCHOR_PREV, b - 0.05, 20)
    _signals(ANCHOR_CURR, up=15, down=5)      # flat_ratio 0
    _signals(ANCHOR_PREV, up=14, down=6)      # flat_ratio 0

    q = build_quadrant()
    assert q["heat_date"] == "2099-01-26"
    assert q["anchor_curr"] == "2099-01-21"
    assert q["anchor_prev"] == "2099-01-14"
    assert q["arrow_suppressed"] is False
    by = {s["sector"]: s for s in q["sectors"]}
    assert {"Technology", "Healthcare", "Energy"} <= set(by)
    assert by["Technology"]["heat"] == 50
    assert by["Technology"]["breadth_curr"] == 0.3
    assert by["Technology"]["denom_curr"] == 20
    assert by["Energy"]["breadth_curr"] == -0.2
    assert by["Technology"]["arrow_suppressed"] is False


@pytest.mark.django_db
def test_quadrant_heat_null():
    """heat 미산출 섹터 → heat=None (FE 하단 목록)."""
    tech = _sector("Technology")
    energy = _sector("Energy")
    _heat(tech, 50)  # energy: heat 없음
    for e in (tech, energy):
        _demand(e, ANCHOR_CURR, 0.1, 20)
        _demand(e, ANCHOR_PREV, 0.1, 20)
    _signals(ANCHOR_CURR, up=10, down=10)
    _signals(ANCHOR_PREV, up=10, down=10)

    q = build_quadrant()
    by = {s["sector"]: s for s in q["sectors"]}
    assert by["Technology"]["heat"] == 50
    assert by["Energy"]["heat"] is None


@pytest.mark.django_db
def test_quadrant_suppression():
    """어느 anchor의 flat_ratio ≥ 90% → arrow_suppressed True (전 섹터)."""
    tech = _sector("Technology")
    _heat(tech, 50)
    _demand(tech, ANCHOR_CURR, 0.1, 20)
    _demand(tech, ANCHOR_PREV, 0.1, 20)
    _signals(ANCHOR_CURR, up=15, down=5)       # flat_ratio 0
    _signals(ANCHOR_PREV, up=1, flat=19)       # flat_ratio 19/20 = 0.95 ≥ 0.90

    q = build_quadrant()
    assert q["flat_ratio_prev"] == pytest.approx(0.95)
    assert q["arrow_suppressed"] is True
    assert all(s["arrow_suppressed"] is True for s in q["sectors"])


@pytest.mark.django_db
def test_quadrant_api_wiring():
    """API 인증 후 200 + payload 형태(고정 경로가 동적 <theme>보다 먼저)."""
    _sector("Technology")
    user = get_user_model().objects.create_user(
        username=f"quad_{uuid.uuid4().hex[:8]}", password="test1234"
    )
    api = APIClient()
    api.force_authenticate(user=user)

    r = api.get("/api/v1/chainsight/theme-heat/quadrant/")
    assert r.status_code == 200
    assert "sectors" in r.data
    assert "arrow_suppressed" in r.data
    assert any(s["sector"] == "Technology" for s in r.data["sectors"])
