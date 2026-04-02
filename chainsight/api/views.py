"""
Chain Sight REST API (Phase 4)

CS-4-1: GET /chainsight/{symbol}/graph/
CS-4-2: GET /chainsight/{symbol}/suggestions/
CS-4-3: GET /chainsight/trace/
"""

import time
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from chainsight.graph import get_graph_repository
from chainsight.models import CoMentionEdge, PriceCoMovement

logger = logging.getLogger(__name__)


class ChainSightGraphView(APIView):
    """CS-4-1: N-depth 그래프 탐색."""

    def get(self, request, symbol):
        symbol = symbol.upper()
        depth = int(request.query_params.get('depth', 1))
        depth = min(depth, 3)

        start = time.time()
        repo = get_graph_repository()

        result = repo.get_neighbors(symbol, depth=depth)
        if not result["center"]:
            return Response({"error": f"Stock {symbol} not found in graph"}, status=status.HTTP_404_NOT_FOUND)

        # edges에 market_signals 보강
        for edge in result.get("edges", []):
            from_t = edge.get("from", "")
            to_t = edge.get("to", "")
            if from_t and to_t:
                a, b = (from_t, to_t) if from_t < to_t else (to_t, from_t)
                # co-mention
                cm = CoMentionEdge.objects.filter(symbol_a=a, symbol_b=b).first()
                # price correlation
                pc = PriceCoMovement.objects.filter(symbol_a=a, symbol_b=b).first()
                edge["market_signals"] = {}
                if cm:
                    edge["market_signals"]["co_mention_count"] = cm.co_mention_count
                if pc:
                    edge["market_signals"]["price_correlation"] = float(pc.correlation)

                # SUPPLIES_TO 역방향
                if edge.get("type") == "SUPPLIES_TO" and edge.get("to") == symbol:
                    edge["derived_type"] = "CUSTOMER_OF"

        elapsed_ms = int((time.time() - start) * 1000)

        return Response({
            "center": result["center"],
            "nodes": result["nodes"],
            "edges": result["edges"],
            "meta": {
                "depth": depth,
                "node_count": len(result["nodes"]),
                "edge_count": len(result["edges"]),
                "query_ms": elapsed_ms,
            }
        })


class ChainSightSuggestionView(APIView):
    """CS-4-2: 카테고리별 탐색 제안."""

    def get(self, request, symbol):
        symbol = symbol.upper()
        repo = get_graph_repository()

        node = repo.get_node(symbol)
        if not node:
            return Response({"error": f"Stock {symbol} not found"}, status=status.HTTP_404_NOT_FOUND)

        categories = []

        # 1. 경쟁사 (PEER_OF)
        peers = repo.run_query("""
            MATCH (s:Stock {ticker: $t})-[:PEER_OF]-(p:Stock)
            RETURN p.ticker AS ticker ORDER BY p.market_cap DESC LIMIT 10
        """, {"t": symbol})
        if peers:
            categories.append({
                "id": "peers", "label": "경쟁사",
                "count": len(peers), "rel_types": ["PEER_OF"],
                "top_tickers": [p["ticker"] for p in peers[:5]],
                "strength": "strong",
            })

        # 2. 같은 산업
        same_ind = repo.run_query("""
            MATCH (s:Stock {ticker: $t})-[:BELONGS_TO_INDUSTRY]->(i:Industry)<-[:BELONGS_TO_INDUSTRY]-(p:Stock)
            WHERE p.ticker <> $t
            RETURN p.ticker AS ticker ORDER BY p.market_cap DESC LIMIT 10
        """, {"t": symbol})
        if same_ind:
            categories.append({
                "id": "same_industry", "label": "같은 산업",
                "count": len(same_ind), "rel_types": ["BELONGS_TO_INDUSTRY"],
                "top_tickers": [p["ticker"] for p in same_ind[:5]],
                "strength": "moderate",
            })

        # 3. 뉴스 동시출현
        co_mentions = CoMentionEdge.objects.filter(
            symbol_a=symbol
        ).union(
            CoMentionEdge.objects.filter(symbol_b=symbol)
        ).order_by('-co_mention_count')[:10]

        if co_mentions:
            tickers = []
            for cm in co_mentions:
                tickers.append(cm.symbol_b if cm.symbol_a == symbol else cm.symbol_a)
            categories.append({
                "id": "co_mentioned", "label": "뉴스 동시출현",
                "count": len(tickers), "rel_types": ["CO_MENTIONED"],
                "top_tickers": tickers[:5],
                "strength": "signal",
            })

        # 4. 같은 섹터
        same_sector = repo.run_query("""
            MATCH (s:Stock {ticker: $t})-[:BELONGS_TO_SECTOR]->(sec:Sector)<-[:BELONGS_TO_SECTOR]-(p:Stock)
            WHERE p.ticker <> $t
            RETURN count(p) AS cnt
        """, {"t": symbol})
        if same_sector and same_sector[0]["cnt"] > 0:
            categories.append({
                "id": "same_sector", "label": "같은 섹터",
                "count": same_sector[0]["cnt"], "rel_types": ["BELONGS_TO_SECTOR"],
                "top_tickers": [],
                "strength": "weak",
            })

        return Response({"symbol": symbol, "categories": categories})


class ChainSightTraceView(APIView):
    """CS-4-3: 두 종목 간 최단 경로."""

    def get(self, request):
        from_sym = request.query_params.get('from', '').upper()
        to_sym = request.query_params.get('to', '').upper()
        max_depth = int(request.query_params.get('max_depth', 5))

        if not from_sym or not to_sym:
            return Response({"error": "from, to 파라미터 필수"}, status=status.HTTP_400_BAD_REQUEST)

        repo = get_graph_repository()

        try:
            result = repo.run_query(f"""
                MATCH path = shortestPath(
                    (a:Stock {{ticker: $from}})-[*..{min(max_depth, 5)}]-(b:Stock {{ticker: $to}})
                )
                RETURN [n IN nodes(path) | n {{.*}}] AS path_nodes,
                       [r IN relationships(path) | {{
                           from: startNode(r).ticker,
                           to: endNode(r).ticker,
                           type: type(r),
                           props: properties(r)
                       }}] AS path_edges
            """, {"from": from_sym, "to": to_sym})

            if not result:
                return Response({"from": from_sym, "to": to_sym, "found": False, "path_length": 0, "path": []})

            nodes = result[0]["path_nodes"]
            edges = result[0]["path_edges"]

            path = []
            for i, node in enumerate(nodes):
                entry = {"node": node}
                if i < len(edges):
                    entry["next_relation"] = edges[i]
                else:
                    entry["next_relation"] = None
                path.append(entry)

            return Response({
                "from": from_sym, "to": to_sym,
                "found": True,
                "path_length": len(edges),
                "path": path,
            })
        except Exception as e:
            logger.error(f"Trace {from_sym}→{to_sym}: {e}")
            return Response({"from": from_sym, "to": to_sym, "found": False, "error": str(e)})
