"""
Chain Sight REST API

Deep dive: GET /chainsight/{symbol}/graph/, suggestions/, trace/
Market view: GET /chainsight/seeds/, sector/{sector}/graph/, {symbol}/neighbors/, signals/
"""

import json
import time
import logging
from datetime import date, datetime, timedelta

from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from stocks.models import Stock
from chainsight.graph import get_graph_repository
from chainsight.graph.exceptions import GraphConnectionError
from chainsight.models import CoMentionEdge, PriceCoMovement, RelationConfidence
from chainsight.utils import get_market_date

REASON_LABELS = {
    'price_top5': '수익률 상위 이상치',
    'price_bottom5': '수익률 하위 이상치',
    'volume_surge': '거래량 급증',
    'sector_outlier': '섹터 이상치',
    'relation_upgrade': '관계 상향',
    'relation_downgrade': '관계 하향',
    'relation_new': '신규 관계 발견',
    'comention_surge': '동시출현 급증',
}

logger = logging.getLogger(__name__)


def _sanitize_neo4j(obj):
    """Neo4j DateTime/Date 등 직렬화 불가 타입을 문자열로 변환."""
    if isinstance(obj, dict):
        return {k: _sanitize_neo4j(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_neo4j(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    # neo4j.time.DateTime 등
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if hasattr(obj, 'iso_format'):
        return obj.iso_format()
    return obj


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

        return Response(_sanitize_neo4j({
            "center": result["center"],
            "nodes": result["nodes"],
            "edges": result["edges"],
            "meta": {
                "depth": depth,
                "node_count": len(result["nodes"]),
                "edge_count": len(result["edges"]),
                "query_ms": elapsed_ms,
            }
        }))


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

            return Response(_sanitize_neo4j({
                "from": from_sym, "to": to_sym,
                "found": True,
                "path_length": len(edges),
                "path": path,
            }))
        except Exception as e:
            logger.error(f"Trace {from_sym}→{to_sym}: {e}")
            return Response({"from": from_sym, "to": to_sym, "found": False, "error": str(e)})


# ============================================================
# Market View API — PR-4
# ============================================================

def _get_today_seeds() -> dict:
    """오늘 시드 데이터를 Redis에서 읽기. fallback으로 전일 시도."""
    today = get_market_date()
    for offset in range(3):  # 오늘, 어제, 그제
        d = today - timedelta(days=offset)
        cached = cache.get(f'chainsight:seeds:{d}')
        if cached:
            return json.loads(cached) if isinstance(cached, str) else cached
    return {'date': str(today), 'total_seeds': 0, 'sector_summary': [], 'seeds': []}


class SeedListView(APIView):
    """오늘의 시드 전체 + 섹터 요약. Redis 캐시 읽기 전용."""

    def get(self, request):
        data = _get_today_seeds()
        return Response(data)


class SectorGraphView(APIView):
    """섹터 overview graph — 탐색 시작점 선택용 구조 파악."""

    def get(self, request, sector):
        try:
            limit = min(int(request.query_params.get('limit', 12)), 30)
        except (ValueError, TypeError):
            limit = 12
        if limit < 1:
            return Response({'error': 'Invalid parameter: limit must be >= 1'},
                            status=status.HTTP_400_BAD_REQUEST)

        today = get_market_date()
        cache_key = f'chainsight:sector_graph:{sector}:{today}:{limit}'
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached) if isinstance(cached, str) else cached)

        seeds_data = _get_today_seeds()
        seed_set = {s['symbol']: s for s in seeds_data.get('seeds', [])}

        try:
            repo = get_graph_repository()

            # 1. 섹터 내 market_cap 상위 노드
            raw_nodes = repo.run_query("""
                MATCH (s:Stock)
                WHERE s.sector = $sector
                RETURN s.ticker AS ticker, s.name AS name, s.sector AS sector,
                       s.industry AS industry, s.market_cap AS market_cap
                ORDER BY s.market_cap DESC
                LIMIT $limit
            """, {'sector': sector, 'limit': limit})

            if not raw_nodes:
                return Response({'error': f'Sector {sector} not found or empty'},
                                status=status.HTTP_404_NOT_FOUND)

            tickers = [n['ticker'] for n in raw_nodes]

            # 2. 노드 간 관계 (confirmed + probable)
            # NOTE: 기존 sync_relations_to_neo4j가 엣지 라벨을 RELATED_TO로 고정하고
            # 실제 타입은 r.relation_type 속성에 저장하므로, coalesce로 처리
            raw_edges = repo.run_query("""
                MATCH (a:Stock)-[r]->(b:Stock)
                WHERE a.ticker IN $tickers AND b.ticker IN $tickers
                  AND r.status IN ['confirmed', 'probable']
                RETURN a.ticker AS source, b.ticker AS target,
                       COALESCE(r.relation_type, type(r)) AS type,
                       r.truth_score AS truth_score,
                       r.market_score AS market_score, r.status AS rel_status,
                       r.relation_category AS relation_category
            """, {'tickers': tickers})

            # 3. node_size 계산 (market_cap 기준 percentile)
            caps = sorted([float(n.get('market_cap') or 0) for n in raw_nodes], reverse=True)
            total = len(caps)

            def _node_size(mc):
                if total == 0:
                    return 'sm'
                mc = float(mc or 0)
                rank = sum(1 for c in caps if c > mc)
                pct = rank / total
                if pct < 0.1:
                    return 'xl'
                if pct < 0.3:
                    return 'lg'
                if pct < 0.6:
                    return 'md'
                return 'sm'

            # Stock 메타 조회 (daily_return, volume_ratio)
            stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=tickers)}

            nodes = []
            for n in raw_nodes:
                ticker = n['ticker']
                stock = stock_map.get(ticker)
                seed_info = seed_set.get(ticker)
                daily_return = 0.0
                if stock and stock.change_percent:
                    try:
                        daily_return = round(float(stock.change_percent.rstrip('%')), 2)
                    except (ValueError, AttributeError):
                        pass

                nodes.append({
                    'symbol': ticker,
                    'name': n.get('name', ''),
                    'sector': n.get('sector', ''),
                    'industry': n.get('industry', ''),
                    'market_cap': float(n.get('market_cap') or 0),
                    'daily_return': daily_return,
                    'volume_ratio': seed_info.get('volume_ratio', 0.0) if seed_info else 0.0,
                    'is_seed': ticker in seed_set,
                    'seed_type': seed_info.get('seed_type') if seed_info else None,
                    'seed_reasons': seed_info.get('seed_reasons', []) if seed_info else [],
                    'node_size': _node_size(n.get('market_cap')),
                })

            edges = []
            for e in (raw_edges or []):
                edges.append({
                    'source': e['source'],
                    'target': e['target'],
                    'type': e['type'],
                    'relation_category': e.get('relation_category', 'truth'),
                    'truth_score': e.get('truth_score'),
                    'market_score': e.get('market_score'),
                    'status': e.get('rel_status', ''),
                })

            response_data = {
                'sector': sector,
                'node_count': len(nodes),
                'edge_count': len(edges),
                'nodes': nodes,
                'edges': edges,
            }

            cache.set(cache_key, json.dumps(response_data), timeout=3600)
            return Response(response_data)

        except GraphConnectionError:
            return Response({'error': 'Graph service unavailable'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)


class NeighborGraphView(APIView):
    """마켓 뷰 탐색 핵심 API. 중심 이동 + 관계 카드 패널 렌더 데이터."""

    def get(self, request, symbol):
        symbol = symbol.upper()
        try:
            limit = min(int(request.query_params.get('limit', 8)), 30)
        except (ValueError, TypeError):
            limit = 8
        rel_types_param = request.query_params.get('rel_types', 'all')
        try:
            min_truth_score = int(request.query_params.get('min_truth_score', 35))
        except (ValueError, TypeError):
            min_truth_score = 35

        today = get_market_date()
        cache_key = f'chainsight:neighbors:{symbol}:{today}:{limit}:{rel_types_param}'
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached) if isinstance(cached, str) else cached)

        # 중심 노드 확인
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            return Response({'error': f'Stock {symbol} not found'},
                            status=status.HTTP_404_NOT_FOUND)

        seeds_data = _get_today_seeds()
        seed_set = {s['symbol']: s for s in seeds_data.get('seeds', [])}

        # 중심 노드 정보
        daily_return = 0.0
        if stock.change_percent:
            try:
                daily_return = round(float(stock.change_percent.rstrip('%')), 2)
            except (ValueError, AttributeError):
                pass

        seed_info = seed_set.get(symbol)
        center = {
            'symbol': symbol,
            'name': stock.stock_name or '',
            'sector': stock.sector or '',
            'industry': stock.industry or '',
            'market_cap': float(stock.market_capitalization) if stock.market_capitalization else 0,
            'daily_return': daily_return,
            'is_seed': symbol in seed_set,
            'seed_type': seed_info.get('seed_type') if seed_info else None,
            'seed_reasons': seed_info.get('seed_reasons', []) if seed_info else [],
        }

        try:
            repo = get_graph_repository()

            # rel_types 필터
            # NOTE: 기존 sync가 엣지 라벨을 RELATED_TO로 고정하므로
            # rel_types 필터는 r.relation_type 속성 기준으로 적용
            rel_filter = ''
            params = {'symbol': symbol, 'min_truth': min_truth_score}
            if rel_types_param != 'all':
                rel_list = [r.strip() for r in rel_types_param.split(',')]
                params['rel_types'] = rel_list
                rel_filter = 'AND r.relation_type IN $rel_types'

            # 양방향 이웃 조회
            raw_neighbors = repo.run_query(f"""
                MATCH (center:Stock {{ticker: $symbol}})-[r]-(neighbor:Stock)
                WHERE r.status IN ['confirmed', 'probable']
                  AND (r.truth_score >= $min_truth OR r.truth_score IS NULL)
                  {rel_filter}
                RETURN neighbor.ticker AS ticker,
                       COALESCE(r.relation_type, type(r)) AS rel_type,
                       r.truth_score AS truth_score, r.market_score AS market_score,
                       r.status AS rel_status, r.evidence_tier_best AS evidence_tier,
                       r.relation_category AS relation_category,
                       CASE WHEN startNode(r).ticker = $symbol THEN 'outbound' ELSE 'inbound' END AS direction
                ORDER BY r.truth_score DESC
            """, params)

            # 이웃 Stock 메타 bulk 조회
            neighbor_symbols = list(set(n['ticker'] for n in (raw_neighbors or [])))
            stock_map = {s.symbol: s for s in Stock.objects.filter(symbol__in=neighbor_symbols)}

            # display_type 파생
            def _display_type(rel_type, direction):
                if rel_type == 'SUPPLIES_TO' and direction == 'outbound':
                    return 'CUSTOMER_OF'
                return rel_type

            neighbors = []
            seen = set()
            for n in (raw_neighbors or []):
                ticker = n['ticker']
                if ticker in seen:
                    continue
                seen.add(ticker)

                ns = stock_map.get(ticker)
                ns_return = 0.0
                if ns and ns.change_percent:
                    try:
                        ns_return = round(float(ns.change_percent.rstrip('%')), 2)
                    except (ValueError, AttributeError):
                        pass

                ns_seed = seed_set.get(ticker)
                display_t = _display_type(n['rel_type'], n['direction'])

                neighbors.append({
                    'symbol': ticker,
                    'name': ns.stock_name if ns else '',
                    'sector': ns.sector if ns else '',
                    'industry': ns.industry if ns else '',
                    'market_cap': float(ns.market_capitalization) if ns and ns.market_capitalization else 0,
                    'daily_return': ns_return,
                    'volume_ratio': ns_seed.get('volume_ratio', 0.0) if ns_seed else 0.0,
                    'is_seed': ticker in seed_set,
                    'seed_type': ns_seed.get('seed_type') if ns_seed else None,
                    'seed_reasons': ns_seed.get('seed_reasons', []) if ns_seed else [],
                    'relation': {
                        'type': n['rel_type'],
                        'display_type': display_t,
                        'direction': n['direction'],
                        'truth_score': n.get('truth_score'),
                        'market_score': n.get('market_score'),
                        'status': n.get('rel_status', ''),
                        'relation_category': n.get('relation_category', 'truth'),
                        'evidence_tier': n.get('evidence_tier'),
                    },
                })

            # 정렬: is_seed 우선 → score DESC → market_cap DESC
            def _sort_key(nb):
                ts = nb['relation']['truth_score']
                ms = nb['relation']['market_score']
                score = ts if ts is not None else (ms if ms is not None else 0)
                return (not nb['is_seed'], -score, -nb['market_cap'])
            neighbors.sort(key=_sort_key)

            total = len(neighbors)
            neighbors = neighbors[:limit]

            # cross_edges: 이웃 간 관계
            nbr_symbols = [nb['symbol'] for nb in neighbors]
            cross_edges = []
            if len(nbr_symbols) >= 2:
                raw_cross = repo.run_query("""
                    MATCH (a:Stock)-[r]->(b:Stock)
                    WHERE a.ticker IN $syms AND b.ticker IN $syms
                      AND r.status IN ['confirmed', 'probable']
                    RETURN a.ticker AS source, b.ticker AS target,
                           COALESCE(r.relation_type, type(r)) AS type,
                           r.truth_score AS truth_score
                """, {'syms': nbr_symbols})
                for ce in (raw_cross or []):
                    cross_edges.append({
                        'source': ce['source'],
                        'target': ce['target'],
                        'type': ce['type'],
                        'truth_score': ce.get('truth_score'),
                    })

            response_data = {
                'center': center,
                'neighbors': neighbors,
                'cross_edges': cross_edges,
                'total_neighbor_count': total,
                'returned_count': len(neighbors),
                'truncated': total > len(neighbors),
            }

            cache.set(cache_key, json.dumps(response_data), timeout=1800)
            return Response(response_data)

        except GraphConnectionError:
            return Response({'error': 'Graph service unavailable'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)


class SignalFeedView(APIView):
    """글로벌 chain flow + 새 chain 추천."""

    def get(self, request):
        try:
            page = max(int(request.query_params.get('page', 1)), 1)
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = min(int(request.query_params.get('page_size', 5)), 20)
        except (ValueError, TypeError):
            page_size = 5
        sector = request.query_params.get('sector', None)

        today = get_market_date()
        cache_key = f'chainsight:signals:{today}:{page}:{page_size}:{sector}'
        cached = cache.get(cache_key)
        if cached:
            return Response(json.loads(cached) if isinstance(cached, str) else cached)

        chains_result = self._build_chain_signals(page, page_size, sector, today)

        response_data = {
            'date': str(today),
            'page': page,
            'page_size': page_size,
            'total_count': chains_result['total'],
            'has_next': chains_result['has_next'],
            'chains': chains_result['items'],
        }

        cache.set(cache_key, json.dumps(response_data), timeout=3600)
        return Response(response_data)

    def _build_chain_signals(self, page, page_size, sector, today):
        """
        시드 노드 간 Neo4j 경로 탐색 → 체인 구성.
        Phase 1: 같은 섹터/industry 시드 페어 → shortestPath → confidence 계산.
        """
        seeds_data = _get_today_seeds()
        seeds = seeds_data.get('seeds', [])
        if sector:
            seeds = [s for s in seeds if s.get('sector') == sector]

        if len(seeds) < 2:
            return {'total': 0, 'has_next': False, 'items': []}

        # 시드 페어 후보 (같은 섹터)
        pairs = []
        for i, s1 in enumerate(seeds):
            for s2 in seeds[i + 1:]:
                if s1.get('sector') == s2.get('sector') and s1['symbol'] != s2['symbol']:
                    pairs.append((s1, s2))

        # 최대 page_size * 3개 후보
        max_candidates = page_size * 3
        pairs = pairs[:max_candidates]

        if not pairs:
            return {'total': 0, 'has_next': False, 'items': []}

        try:
            repo = get_graph_repository()
        except Exception:
            return {'total': 0, 'has_next': False, 'items': []}

        chains = []
        seen_combos = set()
        seq = 0

        for s1, s2 in pairs:
            combo = tuple(sorted([s1['symbol'], s2['symbol']]))
            if combo in seen_combos:
                continue
            seen_combos.add(combo)

            try:
                result = repo.run_query("""
                    MATCH path = shortestPath(
                        (a:Stock {ticker: $from})-[*..3]-(b:Stock {ticker: $to})
                    )
                    WHERE ALL(r IN relationships(path) WHERE r.status IN ['confirmed', 'probable'])
                    RETURN [n IN nodes(path) | {ticker: n.ticker, name: n.name, sector: n.sector}] AS path_nodes,
                           [r IN relationships(path) | {
                               type: COALESCE(r.relation_type, type(r)),
                               truth_score: r.truth_score,
                               market_score: r.market_score
                           }] AS path_edges
                    LIMIT 1
                """, {'from': s1['symbol'], 'to': s2['symbol']})

                if not result:
                    continue

                path_nodes = result[0]['path_nodes']
                path_edges = result[0]['path_edges']

                if len(path_nodes) < 2:
                    continue

                # total_confidence 계산: mean * 0.7 + min * 0.3
                scores = []
                for e in path_edges:
                    s = e.get('truth_score') or e.get('market_score') or 0
                    scores.append(float(s))

                if not scores:
                    continue

                mean_score = sum(scores) / len(scores)
                min_score = min(scores)
                total_confidence = round(mean_score * 0.7 + min_score * 0.3, 1)

                if total_confidence < 30:
                    continue

                # strength 판정
                if total_confidence >= 70:
                    strength = 'strong'
                elif total_confidence >= 40:
                    strength = 'moderate'
                else:
                    strength = 'weak'

                # trigger_summary
                reasons = []
                for s in [s1, s2]:
                    reasons.extend(s.get('seed_reasons', []))
                translated = [REASON_LABELS.get(r, r) for r in set(reasons)]
                trigger = ', '.join(translated)[:100] if translated else '시드 기반 탐색'

                # category 결정
                edge_types = [e['type'] for e in path_edges]
                if 'SUPPLIES_TO' in edge_types:
                    category = 'supply_chain'
                elif 'COMPETES_WITH' in edge_types:
                    category = 'competition'
                elif 'CO_MENTIONED' in edge_types:
                    category = 'co_mention'
                elif 'PRICE_CORRELATED' in edge_types:
                    category = 'price_correlation'
                else:
                    category = 'peer_network'

                seq += 1
                chains.append({
                    'id': f'chain_{today}_{seq:03d}',
                    'title': f'{path_nodes[0]["ticker"]} → {path_nodes[-1]["ticker"]} chain',
                    'category': category,
                    'strength': strength,
                    'total_confidence': total_confidence,
                    'trigger_summary': trigger,
                    'root_sector': s1.get('sector', ''),
                    'path': [
                        {
                            'symbol': n.get('ticker', ''),
                            'name': n.get('name', ''),
                            'sector': n.get('sector', ''),
                        }
                        for n in path_nodes
                    ],
                    'edges': [
                        {
                            'type': e.get('type', ''),
                            'score': float(e.get('truth_score') or e.get('market_score') or 0),
                        }
                        for e in path_edges
                    ],
                })

            except Exception as e:
                logger.debug(f'Chain signal error {s1["symbol"]}→{s2["symbol"]}: {e}')
                continue

        # total_confidence DESC 정렬
        chains.sort(key=lambda c: c['total_confidence'], reverse=True)

        total = len(chains)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        items = chains[start_idx:end_idx]

        return {
            'total': total,
            'has_next': end_idx < total,
            'items': items,
        }
