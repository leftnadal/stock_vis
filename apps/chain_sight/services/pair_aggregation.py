"""
관계 쌍 집계 + opp/risk 공식 (해자 궤적 적립 — 옵션3).

RelationConfidence(per-row, relation_type별 분리)를 정규화 쌍 단위로 모아
truth_max/market_max를 구하고, relevance_opp/relevance_risk를 [0,1]로 파생해
RelationPairSnapshot에 period별 멱등 upsert한다.

집계 분기는 relation_category('truth'|'market')로 한다(relation_type 하드코딩 금지).
"""

from __future__ import annotations


def compute_pair_relevance(truth_max, market_max) -> tuple[float, float]:
    """
    truth_max/market_max([0,100], None→0) → (relevance_opp, relevance_risk) ([0,1]).

    opp  = max(0, t-m) * t   (진실이 시장을 앞선 정도 × 진실 강도 = 기회)
    risk = max(0, m-t) * m   (시장이 진실을 앞선 정도 × 시장 강도 = 과열 위험)

    곱(게이트 AND)이라 가중합이 아니다 — 한쪽이 0이면 신호도 0.
    t==m이면 둘 다 0이라 opp/risk는 상호배타.
    """
    t = (truth_max or 0.0) / 100.0
    m = (market_max or 0.0) / 100.0
    opp = max(0.0, t - m) * t
    risk = max(0.0, m - t) * m
    return opp, risk


def aggregate_relation_pairs(period, dry_run: bool = False) -> dict:
    """
    현재 RelationConfidence 전수를 정규화 쌍 단위로 집계해 RelationPairSnapshot에
    period별 멱등 upsert. period(date)는 멱등 키이므로 같은 날 재실행은 덮어쓴다.

    반드시 update_relation_confidence(confidence write) 완료 후 호출한다.
    dry_run=True면 아무것도 쓰지 않고 쌍 수 + opp/risk 분포만 반환한다.
    """
    from apps.chain_sight.models import RelationConfidence, RelationPairSnapshot
    from apps.chain_sight.utils import normalize_pair

    # 전 행을 한 번에 당겨 Python group-by (N+1 금지).
    rows = RelationConfidence.objects.values_list(
        "symbol_a",
        "symbol_b",
        "relation_category",
        "truth_score",
        "market_score",
        "last_observed_at",
    )

    # 정규화 쌍 → 누적 dict
    agg: dict[tuple[str, str], dict] = {}
    for sym_a, sym_b, category, truth_score, market_score, last_obs in rows.iterator():
        key = normalize_pair(sym_a, sym_b)
        bucket = agg.get(key)
        if bucket is None:
            bucket = {
                "truth_max": 0.0,
                "market_max": 0.0,
                "truth_edge_count": 0,
                "market_edge_count": 0,
                "last_observed_at": None,
            }
            agg[key] = bucket

        if category == "truth":
            bucket["truth_max"] = max(bucket["truth_max"], truth_score or 0.0)
            bucket["truth_edge_count"] += 1
        elif category == "market":
            bucket["market_max"] = max(bucket["market_max"], market_score or 0.0)
            bucket["market_edge_count"] += 1

        if last_obs is not None:
            prev = bucket["last_observed_at"]
            if prev is None or last_obs > prev:
                bucket["last_observed_at"] = last_obs

    if dry_run:
        opp_values, risk_values = [], []
        for b in agg.values():
            opp, risk = compute_pair_relevance(b["truth_max"], b["market_max"])
            opp_values.append(opp)
            risk_values.append(risk)
        return {
            "pairs": len(agg),
            "created": 0,
            "updated": 0,
            "opp_values": opp_values,
            "risk_values": risk_values,
        }

    created, updated = 0, 0
    for (canonical_a, canonical_b), b in agg.items():
        opp, risk = compute_pair_relevance(b["truth_max"], b["market_max"])
        _, is_new = RelationPairSnapshot.objects.update_or_create(
            canonical_a=canonical_a,
            canonical_b=canonical_b,
            period=period,
            defaults={
                "truth_max": b["truth_max"],
                "market_max": b["market_max"],
                "relevance_opp": opp,
                "relevance_risk": risk,
                "truth_edge_count": b["truth_edge_count"],
                "market_edge_count": b["market_edge_count"],
                "last_observed_at": b["last_observed_at"],
            },
        )
        if is_new:
            created += 1
        else:
            updated += 1

    return {"pairs": len(agg), "created": created, "updated": updated}


def latest_pair_snapshots():
    """쌍별 최신 period 스냅샷 (DISTINCT ON — Postgres). 현재 단면."""
    from apps.chain_sight.models import RelationPairSnapshot

    return (
        RelationPairSnapshot.objects.order_by("canonical_a", "canonical_b", "-period")
        .distinct("canonical_a", "canonical_b")
    )


def top_opportunities(limit: int = 20, min_opp: float = 0.0):
    """
    발견 랭킹: 최신 단면에서 relevance_opp > min_opp 인 쌍을 내림차순.
    동점 2차 키 = (truth_edge_count + market_edge_count) desc, last_observed_at desc.
    """
    from django.db.models import F

    from apps.chain_sight.models import RelationPairSnapshot

    latest_ids = list(latest_pair_snapshots().values_list("id", flat=True))
    return (
        RelationPairSnapshot.objects.filter(
            id__in=latest_ids, relevance_opp__gt=min_opp
        )
        .annotate(_edge_total=F("truth_edge_count") + F("market_edge_count"))
        .order_by("-relevance_opp", "-_edge_total", "-last_observed_at")[:limit]
    )
