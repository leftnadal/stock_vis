"""
코어-위성 EventGroup 파이프라인 단위 테스트 (M2 v1.1 Phase 1).

합성 co-mention으로 클러스터링 로직 검증:
- 코어(연결요소 + ≥3 게이트), 위성(1-hop), 13F 가산 confidence, 적재.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.chain_sight.models.event_group import EventGroup, GroupMembership
from apps.chain_sight.models.news_event import ChainNewsEvent
from apps.chain_sight.services import event_group_pipeline as pipe
from packages.shared.stocks.models import Stock


def _mk_stock(sym, sector="Technology"):
    return Stock.objects.create(symbol=sym, stock_name=f"{sym} Inc.", sector=sector)


def _mk_event(primary, others, day_offset=0):
    ChainNewsEvent.objects.create(
        symbol_id=primary,
        source="finnhub",
        source_id=f"{primary}-{others}-{day_offset}",
        title="t",
        published_at=timezone.now() - timedelta(days=day_offset),
        co_mentioned_symbols=others,
    )


@pytest.fixture
def synthetic(db):
    for s in ["A", "B", "C", "D", "E", "F", "G"]:
        _mk_stock(s)
    # 코어 삼각형 {A,B,C} — 5회 동시언급 → jaccard=1.0
    for i in range(5):
        _mk_event("A", ["B", "C"], i)
    # 위성 D — A와 1회만 → jaccard(A,D)=1/(doc(A)+1-1) 낮음 → satellite
    _mk_event("A", ["D"], 10)
    # 별도 코어 {E,F,G} — 5회
    for i in range(5):
        _mk_event("E", ["F", "G"], i)


class TestCoreSatellite:
    def test_two_core_groups_form(self, synthetic):
        res = pipe.compute_event_groups(core_thr=0.2, sat_thr=0.05, min_members=3)
        cores = [set(g["core"]) for g in res["groups"]]
        assert {"A", "B", "C"} in cores
        assert {"E", "F", "G"} in cores
        assert len(res["groups"]) == 2

    def test_satellite_attached_to_core(self, synthetic):
        res = pipe.compute_event_groups(core_thr=0.2, sat_thr=0.05, min_members=3)
        abc = next(g for g in res["groups"] if set(g["core"]) == {"A", "B", "C"})
        sats = [m for m in abc["members"] if m["role"] == "satellite"]
        assert any(m["symbol"] == "D" for m in sats)
        d = next(m for m in sats if m["symbol"] == "D")
        assert d["anchor_symbol"] == "A"
        assert d["edge_confidence"] > 0

    def test_min_members_gate(self, synthetic):
        # min_members=4 면 3인 코어는 자격 미달 → 그룹 0
        res = pipe.compute_event_groups(core_thr=0.2, sat_thr=0.05, min_members=4)
        assert len(res["groups"]) == 0

    def test_13f_additive_confidence(self, synthetic):
        """13F 공동보유가 위성 confidence를 가산(없을 때보다 큼)."""
        from services.serverless.models import InstitutionalHolding
        from datetime import date

        base = pipe.compute_event_groups(core_thr=0.2, sat_thr=0.05, min_members=3)
        abc0 = next(g for g in base["groups"] if set(g["core"]) == {"A", "B", "C"})
        d0 = next(m for m in abc0["members"] if m["symbol"] == "D")

        # A,D를 같은 3개 기관이 보유 → cohold(A,D)=3
        for cik in ["0000000001", "0000000002", "0000000003"]:
            for sym in ["A", "D"]:
                InstitutionalHolding.objects.create(
                    institution_cik=cik, stock_symbol=sym,
                    report_date=date(2026, 3, 31), institution_name="x",
                    filing_date=date(2026, 3, 31), accession_number="",
                    shares=1, value_thousands=1,
                )
        after = pipe.compute_event_groups(core_thr=0.2, sat_thr=0.05, min_members=3)
        abc1 = next(g for g in after["groups"] if set(g["core"]) == {"A", "B", "C"})
        d1 = next(m for m in abc1["members"] if m["symbol"] == "D")

        assert d1["cohold_institutions"] == 3
        assert d1["edge_confidence"] > d0["edge_confidence"]  # 가산만 — 더 커야


class TestCohesionGating:
    def _add_prices(self, syms, corr_returns):
        """corr_returns: 길이 25 수익률 시퀀스(공통이면 상관 1.0)."""
        from datetime import date as _d, timedelta as _td

        from packages.shared.stocks.models import DailyPrice
        for s in syms:
            px = 100.0
            for i, r in enumerate(corr_returns):
                px *= (1 + r)
                DailyPrice.objects.create(
                    stock_id=s, date=_d(2026, 1, 1) + _td(days=i),
                    open_price=px, high_price=px, low_price=px,
                    close_price=round(px, 4), volume=1000,
                )

    def test_high_cohesion_not_gated(self, synthetic):
        # A,B,C 동일 수익률 → 코어 cohesion=1.0 > 0.2 → is_hidden=False
        self._add_prices(["A", "B", "C"], [0.01, -0.02, 0.015, -0.01] * 7)
        from apps.chain_sight.models.event_group import EventGroup
        pipe.load_event_groups()
        abc = EventGroup.objects.filter(memberships__symbol_id="B").first()
        assert abc.cohesion is not None and abc.cohesion > 0.2
        assert abc.is_hidden is False

    def test_no_cohesion_gated(self, synthetic):
        # 가격 없음 → cohesion None → is_hidden=True (산출불가 게이팅)
        from apps.chain_sight.models.event_group import EventGroup
        summary = pipe.load_event_groups()
        assert summary["gated_no_cohesion"] >= 1
        efg = EventGroup.objects.filter(memberships__symbol_id="E").first()
        assert efg.cohesion is None and efg.is_hidden is True


class TestTfidfNames:
    def test_core_names_attached(self, db):
        from datetime import timedelta as _td

        for s in ["X1", "X2", "X3"]:
            _mk_stock(s)
        # 코어 X1,X2,X3 — 일관된 키워드 "battery lithium"
        for i in range(5):
            ChainNewsEvent.objects.create(
                symbol_id="X1", source="finnhub", source_id=f"x-{i}", title="battery lithium surge",
                summary="battery lithium demand", published_at=timezone.now() - _td(days=i),
                co_mentioned_symbols=["X2", "X3"],
            )
        res = pipe.compute_event_groups(core_thr=0.2, sat_thr=0.05, min_members=3)
        g = next(g for g in res["groups"] if set(g["core"]) == {"X1", "X2", "X3"})
        assert g["name_candidates"].get("terms")
        assert "battery" in g["name_candidates"]["terms"] or "lithium" in g["name_candidates"]["terms"]
        assert len(g["name_candidates"]["n2"].split()) <= 2


class TestLoad:
    def test_shadow_load_writes_groups(self, synthetic):
        summary = pipe.load_event_groups(core_thr=0.2, sat_thr=0.05, min_members=3)
        assert summary["groups"] == 2
        assert EventGroup.objects.count() == 2
        # 코어 멤버 role 확인
        abc = EventGroup.objects.filter(memberships__symbol_id="B").first()
        assert abc is not None
        core_roles = GroupMembership.objects.filter(
            group=abc, role="core"
        ).values_list("symbol_id", flat=True)
        assert set(core_roles) >= {"A", "B", "C"}

    def test_load_is_idempotent_overwrite(self, synthetic):
        pipe.load_event_groups(core_thr=0.2, sat_thr=0.05, min_members=3)
        n1 = EventGroup.objects.count()
        pipe.load_event_groups(core_thr=0.2, sat_thr=0.05, min_members=3)
        n2 = EventGroup.objects.count()
        assert n1 == n2 == 2  # 덮어쓰기 — 중복 누적 없음
