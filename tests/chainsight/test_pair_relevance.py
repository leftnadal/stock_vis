"""
RelationPairSnapshot 쌍 집계 + opp/risk 공식 테스트 (해자 궤적 적립 — 옵션3).

공식: t=truth_max/100, m=market_max/100
      relevance_opp  = max(0, t-m) * t   → [0,1]
      relevance_risk = max(0, m-t) * m   → [0,1]
"""

import datetime

import pytest

from apps.chain_sight.services.pair_aggregation import (
    aggregate_relation_pairs,
    compute_pair_relevance,
    latest_pair_snapshots,
    top_opportunities,
)


class TestComputePairRelevance:
    """공식 단위 테스트 (테스트 1)."""

    def test_pure_truth_is_opportunity(self):
        opp, risk = compute_pair_relevance(85, 0)
        assert opp == pytest.approx(0.7225, abs=1e-6)
        assert risk == pytest.approx(0.0, abs=1e-6)

    def test_pure_market_is_risk(self):
        opp, risk = compute_pair_relevance(0, 85)
        assert opp == pytest.approx(0.0, abs=1e-6)
        assert risk == pytest.approx(0.7225, abs=1e-6)

    def test_balanced_is_zero(self):
        opp, risk = compute_pair_relevance(85, 85)
        assert opp == pytest.approx(0.0, abs=1e-6)
        assert risk == pytest.approx(0.0, abs=1e-6)

    def test_mild_truth_lead(self):
        opp, risk = compute_pair_relevance(60, 35)
        assert opp == pytest.approx(0.15, abs=1e-6)
        assert risk == pytest.approx(0.0, abs=1e-6)

    def test_mild_market_lead(self):
        opp, risk = compute_pair_relevance(35, 60)
        assert opp == pytest.approx(0.0, abs=1e-6)
        assert risk == pytest.approx(0.15, abs=1e-6)

    def test_none_market_treated_as_zero(self):
        # market_max가 None으로 들어와도 0으로 처리 (테스트 5 보강)
        opp, risk = compute_pair_relevance(85, None)
        assert opp == pytest.approx(0.7225, abs=1e-6)
        assert risk == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.parametrize("t", [0, 35, 60, 85, 100])
    @pytest.mark.parametrize("m", [0, 35, 60, 85, 100])
    def test_opp_and_risk_mutually_exclusive(self, t, m):
        """상호배타 (테스트 2): opp>0 and risk>0 가 동시에 참인 경우는 없다."""
        opp, risk = compute_pair_relevance(t, m)
        assert not (opp > 0 and risk > 0)
        assert 0.0 <= opp <= 1.0
        assert 0.0 <= risk <= 1.0


PERIOD = datetime.date(2026, 6, 29)


def _mk(symbol_a, symbol_b, relation_type, category, truth=0, market=None):
    from apps.chain_sight.models import RelationConfidence

    return RelationConfidence.objects.create(
        symbol_a=symbol_a,
        symbol_b=symbol_b,
        relation_type=relation_type,
        relation_category=category,
        truth_score=truth,
        market_score=market,
    )


@pytest.mark.django_db
class TestAggregateRelationPairs:
    def test_aggregates_truth_and_market_rows_into_one_snapshot(self):
        """테스트 3: PEER_OF(truth 85) + CO_MENTIONED(market 35) → 한 스냅샷."""
        from apps.chain_sight.models import RelationPairSnapshot

        _mk("AAA", "BBB", "PEER_OF", "truth", truth=85)
        _mk("AAA", "BBB", "CO_MENTIONED", "market", market=35)

        aggregate_relation_pairs(period=PERIOD)

        snaps = RelationPairSnapshot.objects.filter(period=PERIOD)
        assert snaps.count() == 1
        s = snaps.first()
        assert (s.canonical_a, s.canonical_b) == ("AAA", "BBB")
        assert s.truth_max == 85
        assert s.market_max == 35
        assert s.relevance_opp == pytest.approx(0.425, abs=1e-6)
        assert s.relevance_risk == pytest.approx(0.0, abs=1e-6)
        assert s.truth_edge_count == 1
        assert s.market_edge_count == 1

    def test_undirected_rows_merge_into_one_pair(self):
        """무방향: (A,B)와 (B,A) 방향이 한 스냅샷으로 합쳐진다."""
        from apps.chain_sight.models import RelationPairSnapshot

        _mk("AAA", "BBB", "PEER_OF", "truth", truth=85)
        _mk("BBB", "AAA", "SUPPLIES_TO", "truth", truth=60)  # 역방향 truth

        aggregate_relation_pairs(period=PERIOD)

        snaps = RelationPairSnapshot.objects.filter(period=PERIOD)
        assert snaps.count() == 1
        s = snaps.first()
        assert (s.canonical_a, s.canonical_b) == ("AAA", "BBB")
        assert s.truth_max == 85  # max(85, 60)
        assert s.truth_edge_count == 2

    def test_null_market_score_treated_as_zero(self):
        """테스트 5: market_score=null → market_max=0."""
        from apps.chain_sight.models import RelationPairSnapshot

        _mk("AAA", "BBB", "PEER_OF", "truth", truth=85)
        _mk("AAA", "BBB", "PRICE_CORRELATED", "market", market=None)

        aggregate_relation_pairs(period=PERIOD)

        s = RelationPairSnapshot.objects.get(period=PERIOD)
        assert s.market_max == 0
        assert s.relevance_opp == pytest.approx(0.7225, abs=1e-6)

    def test_idempotent_same_period(self):
        """테스트 4: 같은 period 2회 집계 → 행 수 불변, 값 동일."""
        from apps.chain_sight.models import RelationPairSnapshot

        _mk("AAA", "BBB", "PEER_OF", "truth", truth=85)
        _mk("AAA", "BBB", "CO_MENTIONED", "market", market=35)

        aggregate_relation_pairs(period=PERIOD)
        first = RelationPairSnapshot.objects.get(period=PERIOD)
        aggregate_relation_pairs(period=PERIOD)

        snaps = RelationPairSnapshot.objects.filter(period=PERIOD)
        assert snaps.count() == 1
        s = snaps.first()
        assert s.id == first.id  # 새 행 생성 아님 (upsert)
        assert s.relevance_opp == pytest.approx(0.425, abs=1e-6)

    def test_idempotent_across_periods_keeps_both(self):
        """다른 period 2회 → 궤적 2점 누적(forward-only)."""
        from apps.chain_sight.models import RelationPairSnapshot

        _mk("AAA", "BBB", "PEER_OF", "truth", truth=85)
        aggregate_relation_pairs(period=datetime.date(2026, 6, 22))
        aggregate_relation_pairs(period=datetime.date(2026, 6, 29))

        pair = RelationPairSnapshot.objects.filter(canonical_a="AAA", canonical_b="BBB")
        assert pair.count() == 2  # 궤적 2점

    def test_dry_run_writes_nothing_but_returns_distribution(self):
        """backfill --dry-run: 쓰지 않고 쌍 수 + opp/risk 분포만 반환."""
        from apps.chain_sight.models import RelationPairSnapshot

        _mk("AAA", "BBB", "PEER_OF", "truth", truth=85)
        _mk("AAA", "BBB", "CO_MENTIONED", "market", market=35)

        result = aggregate_relation_pairs(period=PERIOD, dry_run=True)

        assert RelationPairSnapshot.objects.filter(period=PERIOD).count() == 0
        assert result["pairs"] == 1
        assert result["created"] == 0
        assert result["opp_values"] == [pytest.approx(0.425, abs=1e-6)]
        assert result["risk_values"] == [pytest.approx(0.0, abs=1e-6)]


def _snap(a, b, period, opp, risk=0.0, t_edges=1, m_edges=0, truth=0, market=0):
    from apps.chain_sight.models import RelationPairSnapshot

    return RelationPairSnapshot.objects.create(
        canonical_a=a,
        canonical_b=b,
        period=period,
        truth_max=truth,
        market_max=market,
        relevance_opp=opp,
        relevance_risk=risk,
        truth_edge_count=t_edges,
        market_edge_count=m_edges,
    )


@pytest.mark.django_db
class TestPairSnapshotQueries:
    def test_latest_returns_newest_period_per_pair(self):
        old = datetime.date(2026, 6, 1)
        new = datetime.date(2026, 6, 29)
        _snap("AAA", "BBB", old, opp=0.36)
        _snap("AAA", "BBB", new, opp=0.7225)

        latest = list(latest_pair_snapshots())
        assert len(latest) == 1
        assert latest[0].period == new
        assert latest[0].relevance_opp == pytest.approx(0.7225, abs=1e-6)

    def test_top_opportunities_orders_desc_and_filters_zero(self):
        p = datetime.date(2026, 6, 29)
        _snap("AAA", "BBB", p, opp=0.7225)
        _snap("CCC", "DDD", p, opp=0.15)
        _snap("EEE", "FFF", p, opp=0.0)  # 괴리 없음 → 제외

        top = list(top_opportunities(limit=10))
        assert [(s.canonical_a, s.canonical_b) for s in top] == [
            ("AAA", "BBB"),
            ("CCC", "DDD"),
        ]

    def test_top_opportunities_tiebreak_by_edge_count(self):
        p = datetime.date(2026, 6, 29)
        _snap("AAA", "BBB", p, opp=0.5, t_edges=1, m_edges=1)  # 합 2
        _snap("CCC", "DDD", p, opp=0.5, t_edges=2, m_edges=2)  # 합 4 → 먼저

        top = list(top_opportunities(limit=10))
        assert (top[0].canonical_a, top[0].canonical_b) == ("CCC", "DDD")
