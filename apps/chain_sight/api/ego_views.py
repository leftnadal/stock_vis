"""PostgreSQL 네이티브 ego 그래프 API (⑰ S1-b, D-GRAPH-EGO-BACKEND=B).

기존 Neo4j 백엔드 endpoint(ChainSightGraphView·NeighborGraphView·sector graph)는
동결(무변경). 본 뷰는 진실 소스(RelationConfidence + RelationPairSnapshot)를
PostgreSQL에서 직접 조회해 회사 중심 1-hop 관계망을 서빙한다.

- 엣지 = RelationConfidence 양방향(symbol_a=X OR symbol_b=X), truth_score 내림차순 상위 N.
- 궤적 = RelationPairSnapshot을 canonical 쌍 단위로 join(N+1 금지, 단일 조회).
- truth_score는 미정규화 원값 그대로 노출(정규화는 별도 트랙).
"""

from collections import defaultdict

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.models import RelationConfidence, RelationPairSnapshot
from apps.chain_sight.utils import normalize_pair
from packages.shared.stocks.models import Stock

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
DEFAULT_TREND_WINDOW = 12


def _parse_int(value, default, lo, hi):
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _parse_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _trend_summary(points_raw, trend_window):
    """canonical 쌍 궤적 리스트[(period, score)] → trend 요약(방향·delta·points)."""
    pts = points_raw[-trend_window:]
    points = [{"period": str(p), "score": round(s, 2)} for p, s in pts]
    if len(pts) >= 2:
        delta = round(pts[-1][1] - pts[0][1], 2)
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
    else:
        delta = 0.0
        direction = "flat"
    return {"direction": direction, "delta": delta, "points": points}


class EgoGraphView(APIView):
    """GET /api/v1/chainsight/ego/<symbol>/ — PG 네이티브 1-hop ego 그래프."""

    def get(self, request, symbol):
        symbol = symbol.upper()
        min_score = _parse_float(request.query_params.get("min_score"), 0.0)
        limit = _parse_int(request.query_params.get("limit"), DEFAULT_LIMIT, 1, MAX_LIMIT)
        trend_window = _parse_int(
            request.query_params.get("trend_window"), DEFAULT_TREND_WINDOW, 1, 60
        )
        types_param = request.query_params.get("types")
        types = (
            [t.strip().upper() for t in types_param.split(",") if t.strip()]
            if types_param
            else None
        )
        include_cross_edges = str(
            request.query_params.get("include_cross_edges", "")
        ).lower() in ("1", "true", "yes")

        center_stock = Stock.objects.filter(symbol=symbol).only(
            "symbol", "stock_name"
        ).first()
        if center_stock is None:
            return Response(
                {"error": f"Stock {symbol} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 1-hop 엣지 (양방향) — truth_score 내림차순 상위 N 절단
        edge_qs = RelationConfidence.objects.filter(
            Q(symbol_a=symbol) | Q(symbol_b=symbol)
        )
        if min_score > 0:
            edge_qs = edge_qs.filter(truth_score__gte=min_score)
        if types:
            edge_qs = edge_qs.filter(relation_type__in=types)

        total_edges = edge_qs.count()
        edge_rows = list(
            edge_qs.order_by("-truth_score").values(
                "symbol_a", "symbol_b", "relation_type", "truth_score"
            )[:limit]
        )

        # 이웃·쌍 수집
        neighbors = set()
        pairs = set()
        for e in edge_rows:
            other = e["symbol_b"] if e["symbol_a"] == symbol else e["symbol_a"]
            neighbors.add(other)
            pairs.add(normalize_pair(e["symbol_a"], e["symbol_b"]))

        # cross_edges (A1 부분 흡수, ⑲ D②): limit 절단 후 이웃 집합 사이의 RC 엣지.
        # 단일 양방향 쿼리(N+1 금지). 궤적 계산 위해 cross 쌍도 아래 RPS 조회에 합류.
        cross_edge_rows = []
        if include_cross_edges and len(neighbors) >= 2:
            cross_edge_rows = [
                e
                for e in RelationConfidence.objects.filter(
                    symbol_a__in=neighbors, symbol_b__in=neighbors
                ).values("symbol_a", "symbol_b", "relation_type", "truth_score")
                if e["symbol_a"] != e["symbol_b"]
            ]
            for e in cross_edge_rows:
                pairs.add(normalize_pair(e["symbol_a"], e["symbol_b"]))

        # 노드 보강 (단일 쿼리)
        node_syms = {symbol} | neighbors
        stock_map = {
            s.symbol: s
            for s in Stock.objects.filter(symbol__in=node_syms).only(
                "symbol", "stock_name", "sector"
            )
        }

        # 궤적 (단일 쿼리 → canonical 쌍별 group, N+1 금지)
        traj = defaultdict(list)
        if pairs:
            rps_rows = (
                RelationPairSnapshot.objects.filter(
                    canonical_a__in=[p[0] for p in pairs],
                    canonical_b__in=[p[1] for p in pairs],
                )
                .order_by("canonical_a", "canonical_b", "period")
                .values("canonical_a", "canonical_b", "period", "truth_max")
            )
            for r in rps_rows:
                key = (r["canonical_a"], r["canonical_b"])
                if key in pairs:  # __in 카테시안 과대조회분 제거
                    traj[key].append((r["period"], r["truth_max"]))

        # 노드 payload
        nodes = []
        for sym in node_syms:
            st = stock_map.get(sym)
            nodes.append({
                "symbol": sym,
                "name": (st.stock_name if st else "") or "",
                "sector": (st.sector if st else "") or "",
            })

        # 엣지 payload (+ trend 요약)
        edges = []
        for e in edge_rows:
            other = e["symbol_b"] if e["symbol_a"] == symbol else e["symbol_a"]
            key = normalize_pair(e["symbol_a"], e["symbol_b"])
            edges.append({
                "source": symbol,
                "target": other,
                "relation_type": e["relation_type"],
                "truth_score": round(e["truth_score"] or 0.0, 2),
                "trend": _trend_summary(traj.get(key, []), trend_window),
            })

        payload = {
            "center": {"symbol": symbol, "name": center_stock.stock_name or ""},
            "nodes": nodes,
            "edges": edges,
            "meta": {
                "total_edges": total_edges,
                "returned": len(edges),
                "filtered_by": {
                    "min_score": min_score,
                    "types": types,
                    "limit": limit,
                    "trend_window": trend_window,
                },
            },
        }

        # cross_edges = additive: true일 때만 키 추가(기본 false = 응답 바이트 불변)
        if include_cross_edges:
            cross_edges = [
                {
                    "source": e["symbol_a"],
                    "target": e["symbol_b"],
                    "relation_type": e["relation_type"],
                    "truth_score": round(e["truth_score"] or 0.0, 2),
                    "trend": _trend_summary(
                        traj.get(normalize_pair(e["symbol_a"], e["symbol_b"]), []),
                        trend_window,
                    ),
                }
                for e in cross_edge_rows
            ]
            payload["cross_edges"] = cross_edges
            payload["meta"]["cross_edges_count"] = len(cross_edges)

        return Response(payload)
