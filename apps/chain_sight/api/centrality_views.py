"""중심성 조회 API (⑲ S3). 화면 노출은 ⑳ — 여기선 데이터 엔드포인트까지.

GET /api/v1/chainsight/centrality/top/?metric=pagerank|betweenness&n=20&as_of=
  - metric: pagerank(기본) | betweenness
  - n: 상위 개수(기본 20, 1~200)
  - as_of: 기준일(기본 = 최신 스냅샷)
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.models import SymbolCentrality

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
