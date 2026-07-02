"""
EventGroup 역할별 비대칭 leadership 컴퓨트 (정책 C) — Slice A 단위 테스트.

검증:
- 새 행 키 분리(theme='eg:{slug}', benchmark_kind core_loo/sat_coremean).
- 코어=코어LOO, 위성=코어평균 벤치마크로 산출.
- 옛 theme_tags 행 IDENTICAL(무영향).
- 엣지: 코어1개→코어 α/β NULL, 코어0개→ValueError, 120윈도 fallback, 멱등.
"""

import math
from datetime import date, timedelta

import pytest

from apps.chain_sight.models.event_group import EventGroup, GroupMembership
from apps.chain_sight.models.leadership import StockLeadershipScore
from apps.chain_sight.services.leadership_eventgroup import (
    KIND_CORE,
    KIND_SAT,
    compute_eventgroup_leadership_scores,
    eg_theme_key,
)
from packages.shared.stocks.models import DailyPrice, Stock

AS_OF = date(2026, 6, 12)


def _stock(sym):
    return Stock.objects.get_or_create(
        symbol=sym, defaults={"stock_name": f"{sym} Inc.", "sector": "Technology"}
    )[0]


def _make_prices(sym, n_days=30, drift=0.005, base=100.0):
    stock = _stock(sym)
    objs = []
    for i in range(n_days):
        d = AS_OF - timedelta(days=(n_days - 1 - i))
        close = base * math.exp(drift * i)
        objs.append(DailyPrice(
            stock=stock, date=d,
            open_price=close, high_price=close * 1.01,
            low_price=close * 0.99, close_price=close, volume=1_000_000,
        ))
    DailyPrice.objects.bulk_create(objs, ignore_conflicts=True)


def _mk_group(slug, members, cohesion=0.5, is_hidden=False, n_days=30, drifts=None):
    """members=[(sym, role)]. drifts: per-member drift dict(다양성)."""
    eg = EventGroup.objects.create(
        name=f"grp {slug}", slug=slug, source="news_jaccard",
        confidence=0.5, cohesion=cohesion,
        member_count=len(members),
        core_count=sum(1 for _, r in members if r == "core"),
        is_hidden=is_hidden,
    )
    for sym, role in members:
        d = (drifts or {}).get(sym, 0.005)
        _make_prices(sym, n_days=n_days, drift=d)
        GroupMembership.objects.create(group=eg, symbol_id=sym, role=role)
    return eg


@pytest.mark.django_db
class TestComputeKeys:
    def test_rows_use_eg_theme_and_kind(self):
        _mk_group("g-1", [("A", "core"), ("B", "core"), ("C", "core"),
                          ("D", "satellite"), ("E", "satellite")],
                  drifts={"A": 0.004, "B": 0.006, "C": 0.005, "D": 0.003, "E": 0.007})
        n = compute_eventgroup_leadership_scores(AS_OF)
        assert n > 0
        theme = eg_theme_key("g-1")
        rows = StockLeadershipScore.objects.filter(theme=theme, window=20)
        assert rows.count() == 5  # core 3 + sat 2
        # 코어/위성 benchmark_kind 분리
        assert set(rows.filter(stock_id__in=["A", "B", "C"]).values_list("benchmark_kind", flat=True)) == {KIND_CORE}
        assert set(rows.filter(stock_id__in=["D", "E"]).values_list("benchmark_kind", flat=True)) == {KIND_SAT}

    def test_core_metrics_filled(self):
        _mk_group("g-2", [("A", "core"), ("B", "core"), ("C", "core")],
                  drifts={"A": 0.004, "B": 0.006, "C": 0.005})
        compute_eventgroup_leadership_scores(AS_OF)
        a = StockLeadershipScore.objects.get(theme=eg_theme_key("g-2"), stock_id="A", window=20)
        assert a.trend_quality is not None     # theme-무관
        assert a.theme_beta is not None        # 코어 3 → LOO 가능
        assert a.benchmark_kind == KIND_CORE

    def test_satellite_metrics_filled(self):
        _mk_group("g-3", [("A", "core"), ("B", "core"), ("C", "core"), ("S", "satellite")],
                  drifts={"A": 0.004, "B": 0.006, "C": 0.005, "S": 0.008})
        compute_eventgroup_leadership_scores(AS_OF)
        s = StockLeadershipScore.objects.get(theme=eg_theme_key("g-3"), stock_id="S", window=20)
        assert s.benchmark_kind == KIND_SAT
        assert s.theme_beta is not None        # 코어 3 평균 벤치마크 → 산출


@pytest.mark.django_db
class TestLegacyUntouched:
    def test_legacy_row_identical(self):
        # 레거시 행(theme=sector명) 선적재
        _stock("A")
        legacy = StockLeadershipScore.objects.create(
            stock_id="A", theme="Technology", window=20, as_of_date=AS_OF,
            trend_quality=1.23, theme_beta=0.9, obs_count=20,
        )
        _mk_group("g-leg", [("A", "core"), ("B", "core"), ("C", "core")])
        compute_eventgroup_leadership_scores(AS_OF)
        legacy.refresh_from_db()
        # 레거시 행 불변 + benchmark_kind NULL
        assert legacy.trend_quality == 1.23
        assert legacy.theme_beta == 0.9
        assert legacy.benchmark_kind is None
        # 새 행은 eg: 키로 별개 존재
        assert StockLeadershipScore.objects.filter(theme=eg_theme_key("g-leg")).exists()


@pytest.mark.django_db
class TestEdgeCases:
    def test_single_core_loo_null(self):
        # 코어 1개 → LOO 자기제외 후 공집합 → 코어 α/β NULL, tq는 산출
        _mk_group("g-1c", [("A", "core"), ("S1", "satellite"), ("S2", "satellite")])
        compute_eventgroup_leadership_scores(AS_OF)
        a = StockLeadershipScore.objects.get(theme=eg_theme_key("g-1c"), stock_id="A", window=20)
        assert a.theme_beta is None        # 코어 LOO 불가
        assert a.trend_quality is not None  # theme-무관 산출
        assert a.benchmark_kind == KIND_CORE

    def test_zero_core_raises(self):
        _mk_group("g-0c", [("S1", "satellite"), ("S2", "satellite"), ("S3", "satellite")])
        with pytest.raises(ValueError, match="코어 0개"):
            compute_eventgroup_leadership_scores(AS_OF)

    def test_window120_fallback(self):
        _mk_group("g-fb", [("A", "core"), ("B", "core"), ("C", "core")], n_days=30)
        compute_eventgroup_leadership_scores(AS_OF)
        a120 = StockLeadershipScore.objects.get(theme=eg_theme_key("g-fb"), stock_id="A", window=120)
        assert a120.is_fallback is True     # 30일 < 120 게이트
        assert a120.theme_beta is None      # 게이트 미달 → NULL

    def test_idempotent(self):
        _mk_group("g-idem", [("A", "core"), ("B", "core"), ("C", "core")])
        n1 = compute_eventgroup_leadership_scores(AS_OF)
        n2 = compute_eventgroup_leadership_scores(AS_OF)
        assert n1 == n2
        assert StockLeadershipScore.objects.filter(theme=eg_theme_key("g-idem")).count() == n1 / 1  # 멱등(중복 없음)
