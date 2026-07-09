"""MP2-SECTOR-CD → CD-STAB Slice A′ — _sector_detail payload cd_state 테스트.

A′(D-CD-XAXIS-SCOPE): 판단 x축 = rel_strength_5d = momentum_5d − bench(SPY) 5일 수익률.
sectors[]·history[]에 rel_strength_5d additive 서빙 + 기존 rel_strength(1일, 맥박)는 무접촉.
판정 로직은 payload builder 단독 거주 — 응답 cd_state = classify_cd_state(rel5, mom5)와 일치.

앵커 수치(84/0.1776)는 mgmt(DECISIONS/PROGRESS) 기록 — 테스트에 하드코딩 금지(디렉터 지시).
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
from macro.models.indicators import MarketIndex, MarketIndexPrice

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


def _spy_index():
    mi, _ = MarketIndex.objects.get_or_create(
        symbol="SPY",
        defaults={"name": "SPY", "sector_group": MarketIndex.SectorGroup.BENCHMARK},
    )
    return mi


def _spy_price(d, close):
    MarketIndexPrice.objects.get_or_create(
        index=_spy_index(), date=d, defaults={"close": Decimal(str(close)), "volume": 1000}
    )


def _seed_spy_flat(first_date, last_date, close=100):
    """[first_date-5 .. last_date] flat close → 전 날 bench_5d=0 → rel_strength_5d = momentum_5d."""
    d = first_date - timedelta(days=5)
    while d <= last_date:
        _spy_price(d, close)
        d += timedelta(days=1)


def _seed_spy_bench(on_date, bench_5d_pct):
    """on_date에 bench_5d(%)를 만드는 6행 SPY. close[on_date-5]=100, close[on_date]=100+bench."""
    for k in range(5, 0, -1):
        _spy_price(on_date - timedelta(days=k), 100)
    _spy_price(on_date, Decimal("100") + Decimal(str(bench_5d_pct)))


def _mk_snap(mi, d, rel, mom5, rank=1):
    return SectorFlowSnapshot.objects.create(
        date=d, snapshot_time=timezone.now(), market_index=mi,
        rel_strength=Decimal(str(rel)),
        momentum_1d=Decimal("0.1"), momentum_5d=Decimal(str(mom5)), momentum_20d=Decimal("0.2"),
        flow_proxy=Decimal("0.3"),
        cross_dispersion=Decimal("0.8"), rotation_index=Decimal("1.5"),
        rank_in_universe=rank,
    )


# A′ 4사분면: 단일일에는 rel5 = mom5 − bench(공유)라 한 날 한 섹터씩(선 y=x+bench 커플링).
#   각 사분면 = bench/mom5 조합으로 도달. 단일 스냅샷 = 시드 → 공식=raw.
@pytest.mark.django_db
@pytest.mark.parametrize(
    "mom5,bench,expected",
    [
        (3.0, 1.0, "leading_strengthening"),   # rel5=2>0,  mom5=3>0
        (-1.0, -3.0, "leading_weakening"),     # rel5=2>0,  mom5=-1<=0
        (1.0, 3.0, "lagging_improving"),       # rel5=-2<=0, mom5=1>0
        (-1.0, 1.0, "lagging_deteriorating"),  # rel5=-2<=0, mom5=-1<=0
    ],
)
def test_cd_state_quadrant_via_rel5(auth_client, mom5, bench, expected):
    on = date_cls(2026, 6, 15)
    _seed_spy_bench(on, bench)
    _mk_snap(_mk_index("XLK"), on, rel=0.0, mom5=mom5, rank=1)
    row = auth_client.get(_url()).json()["data"]["sectors"][0]
    assert row["cd_state"] == expected
    assert row["cd_state_raw"] == expected  # 단일일 = 시드
    assert row["rel_strength_5d"] == pytest.approx(mom5 - bench)


@pytest.mark.django_db
class TestSectorCdRel5Wiring:
    def test_judgment_uses_rel5_not_1day(self, auth_client):
        """구별값: rel_strength(1일)와 rel_strength_5d가 다른 사분면을 지시할 때 판단은 5d를 따른다."""
        on = date_cls(2026, 6, 15)
        _seed_spy_bench(on, 3.0)  # bench_5d = +3
        # 1일 rel = +5(강한 주도), mom5 = +1 → 1d 분류라면 leading_strengthening.
        # 5d rel = 1 − 3 = −2 <= 0 → lagging_improving. cd_state는 5d를 따라야 함.
        _mk_snap(_mk_index("XLK"), on, rel=5.0, mom5=1.0, rank=1)
        row = auth_client.get(_url()).json()["data"]["sectors"][0]
        assert row["cd_state"] == "lagging_improving"     # 5d 판단
        assert row["cd_state_raw"] == "lagging_improving"
        assert row["rel_strength_5d"] == pytest.approx(-2.0)
        assert row["rel_strength"] == 5.0                 # 1일값 무접촉(맥박·히트맵)

    def test_null_when_bench_absent(self, auth_client):
        """bench 소급 불가(SPY 미시드) → rel_strength_5d None → cd_state 판단 유보(None)."""
        _mk_snap(_mk_index("XLK"), date_cls(2026, 6, 15), rel=1.0, mom5=1.0, rank=1)
        row = auth_client.get(_url()).json()["data"]["sectors"][0]
        assert row["rel_strength_5d"] is None
        assert row["cd_state"] is None
        assert row["cd_state_raw"] is None
        assert row["rel_strength"] == 1.0  # 1일값은 여전히 서빙

    def test_existing_keys_unchanged_plus_rel5(self, auth_client):
        """기존 sectors[] 키 불변 + rel_strength_5d additive만 추가(행위보존)."""
        on = date_cls(2026, 6, 15)
        _seed_spy_flat(on, on)  # bench_5d = 0 → rel5 = mom5
        _mk_snap(_mk_index("XLK"), on, rel=2.0, mom5=0.5, rank=1)
        row = auth_client.get(_url()).json()["data"]["sectors"][0]
        assert set(row.keys()) == {
            "symbol", "rel_strength", "rel_strength_5d", "momentum_1d", "momentum_5d",
            "momentum_20d", "flow_proxy", "rank", "cd_state", "cd_state_raw",
        }
        assert row["symbol"] == "XLK"
        assert row["rel_strength"] == 2.0        # 1일값 무접촉
        assert row["rel_strength_5d"] == pytest.approx(0.5)  # mom5 − 0
        assert row["momentum_5d"] == 0.5
        assert row["rank"] == 1

    def test_history_rel5_additive(self, auth_client):
        """history[] per-date rel_strength_5d additive + 기존 rel_strength(1일) 유지."""
        base = date_cls(2026, 6, 1)
        _seed_spy_flat(base, base + timedelta(days=2))
        xlk = _mk_index("XLK")
        for off in range(3):
            _mk_snap(xlk, base + timedelta(days=off), rel=1.0 + off, mom5=0.5, rank=1)
        hist = auth_client.get(_url()).json()["data"]["sector_history"]
        pts = next(h["history"] for h in hist if h["symbol"] == "XLK")
        assert len(pts) == 3
        for i, p in enumerate(pts):
            assert p["rel_strength"] == pytest.approx(1.0 + i)   # 1일값 유지(맥박)
            assert p["rel_strength_5d"] == pytest.approx(0.5)    # mom5 − 0(판단)


@pytest.mark.django_db
class TestSectorCdHysteresis5d:
    """CD-STAB Slice A′+B — 리플레이 입력 = rel_strength_5d. flat bench(=0) → rel5 = mom5.

    → mom5>0 = leading_strengthening(A), mom5<=0 = lagging_deteriorating(D).
    2일 히스테리시스 로직(공식 vs raw)을 5d 배선 위에서 실증.
    """

    def _seq(self, mi, base, specs):
        for off, rel, mom in specs:
            _mk_snap(mi, base + timedelta(days=off), rel, mom, rank=1)

    def test_official_stays_on_1day_blip(self, auth_client):
        """최신일 1일 블립(mom5 부호 반전) → 공식 유지, raw는 블립 노출."""
        base = date_cls(2026, 6, 1)
        _seed_spy_flat(base, base + timedelta(days=6))
        xlk = _mk_index("XLK")
        self._seq(xlk, base, [(i, 1.0, 1.0) for i in range(6)] + [(6, 1.0, -1.0)])
        row = auth_client.get(_url()).json()["data"]["sectors"][0]
        assert row["cd_state"] == "leading_strengthening"    # 공식 = A 유지
        assert row["cd_state_raw"] == "lagging_deteriorating"  # 원시 = D 블립(5d rel=mom5)
        assert row["cd_state"] != row["cd_state_raw"]        # 히스테리시스 실증

    def test_official_transitions_on_2day_confirm(self, auth_client):
        """신규 사분면 2연속일 → 공식 전환. 공식=raw."""
        base = date_cls(2026, 6, 1)
        _seed_spy_flat(base, base + timedelta(days=6))
        xlk = _mk_index("XLK")
        self._seq(xlk, base, [(i, 1.0, 1.0) for i in range(5)] + [(5, 1.0, -1.0), (6, 1.0, -1.0)])
        row = auth_client.get(_url()).json()["data"]["sectors"][0]
        assert row["cd_state"] == "lagging_deteriorating"    # 공식 전환 완료
        assert row["cd_state_raw"] == "lagging_deteriorating"

    def test_single_day_official_equals_raw(self, auth_client):
        """단일 스냅샷 = 시드 → 공식=raw."""
        on = date_cls(2026, 6, 15)
        _seed_spy_flat(on, on)
        _mk_snap(_mk_index("XLK"), on, rel=0.8, mom5=0.5, rank=1)
        row = auth_client.get(_url()).json()["data"]["sectors"][0]
        assert row["cd_state"] == "leading_strengthening"
        assert row["cd_state"] == row["cd_state_raw"]

    def test_early_pollution_washed_out(self, auth_client):
        """초기 오염(가짜 D)이 있어도 현재 공식은 지속된 A."""
        base = date_cls(2026, 6, 1)
        _seed_spy_flat(base, base + timedelta(days=6))
        xlk = _mk_index("XLK")
        self._seq(xlk, base, [(0, -1.0, -1.0), (1, -1.0, -1.0)] + [(i, 1.0, 1.0) for i in range(2, 7)])
        row = auth_client.get(_url()).json()["data"]["sectors"][0]
        assert row["cd_state"] == "leading_strengthening"    # 오염 세척, 공식=A


@pytest.mark.django_db
class TestSectorCdBaselineMeta:
    def test_rel_strength_baseline_served(self, auth_client):
        """판정선 단일소스 — cd_rel_strength_baseline=0.0 서빙(A′도 0 중심, 규칙 #4)."""
        on = date_cls(2026, 6, 15)
        _seed_spy_flat(on, on)
        _mk_snap(_mk_index("XLK"), on, rel=1.0, mom5=1.0, rank=1)
        data = auth_client.get(_url()).json()["data"]
        assert data["cd_rel_strength_baseline"] == 0.0
        assert data["cd_momentum_baseline"] == 0.0
