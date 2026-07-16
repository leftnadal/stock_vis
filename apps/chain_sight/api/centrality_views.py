"""중심성 조회 API (⑲ S3 + ⑳-1 rank/rank_delta). 리더보드 데이터 엔드포인트.

GET /api/v1/chainsight/centrality/top/?metric=pagerank|betweenness&n=20&as_of=
  - metric: pagerank(기본) | betweenness
  - n: 상위 개수(기본 20, 1~200)
  - as_of: 기준일(기본 = 최신 스냅샷)

results 각 항목(⑳-1 additive):
  - rank: 요청 지표 기준 당일 순위(1-base, = {metric}_rank)
  - rank_delta: 전일_rank − 당일_rank (상승=양수). 전일 = 당일보다 앞선 가장
    최근 as_of(주말·휴일 갭 허용). 전일 데이터 부재 시 null.
  - name: 종목명(리더보드 표시용, Stock join). 미등재 심볼은 "".
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.models import SymbolCentrality
from packages.shared.stocks.models import Stock

DEFAULT_N = 20
MAX_N = 200
VALID_METRICS = {"pagerank", "betweenness"}


class CentralityTopView(APIView):
    """일별 중심성 상위 N 조회."""

    def get(self, request):
        metric = request.query_params.get("metric", "pagerank")
        if metric not in VALID_METRICS:
            return Response(
                {"error": f"metric must be one of {sorted(VALID_METRICS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            n = max(1, min(MAX_N, int(request.query_params.get("n", DEFAULT_N))))
        except (TypeError, ValueError):
            n = DEFAULT_N

        as_of_param = request.query_params.get("as_of")
        if as_of_param:
            as_of = as_of_param
        else:
            as_of = (
                SymbolCentrality.objects.order_by("-as_of")
                .values_list("as_of", flat=True)
                .first()
            )
        if as_of is None:
            return Response({"as_of": None, "metric": metric, "results": []})

        rank_field = f"{metric}_rank"
        qs = (
            SymbolCentrality.objects.filter(as_of=as_of)
            .order_by(rank_field)
            .values(
                "symbol", "pagerank", "betweenness",
                "pagerank_rank", "betweenness_rank",
                "graph_nodes", "graph_edges",
            )[:n]
        )
        results = list(qs)

        # ⑳-1 additive: rank(요청 지표 순위) + rank_delta(전일 대비).
        # 전일 = 당일보다 앞선 가장 최근 as_of(갭 허용). 2쿼리로 N+1 방지.
        prev_as_of = (
            SymbolCentrality.objects.filter(as_of__lt=as_of)
            .order_by("-as_of")
            .values_list("as_of", flat=True)
            .first()
        )
        prev_rank_map = {}
        if prev_as_of is not None and results:
            prev_rank_map = {
                row["symbol"]: row[rank_field]
                for row in SymbolCentrality.objects.filter(
                    as_of=prev_as_of,
                    symbol__in=[r["symbol"] for r in results],
                ).values("symbol", rank_field)
            }
        # 종목명 (리더보드 표시용, 단일 쿼리 join)
        name_map = dict(
            Stock.objects.filter(
                symbol__in=[r["symbol"] for r in results]
            ).values_list("symbol", "stock_name")
        )
        for r in results:
            r["rank"] = r[rank_field]
            prev = prev_rank_map.get(r["symbol"])
            r["rank_delta"] = (prev - r[rank_field]) if prev is not None else None
            r["name"] = name_map.get(r["symbol"]) or ""

        graph_size = (
            {"nodes": results[0]["graph_nodes"], "edges": results[0]["graph_edges"]}
            if results
            else None
        )
        return Response({
            "as_of": str(as_of),
            "metric": metric,
            "n": n,
            "graph_size": graph_size,
            "results": results,
        })
