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

from apps.chain_sight.models import (
    RelationConfidence,
    RelationPairSnapshot,
    SymbolCentrality,
)
from apps.chain_sight.utils import normalize_pair
from packages.shared.stocks.models import Stock

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
DEFAULT_TREND_WINDOW = 12

# ⑳-G S1: 정직화 additive 상수 — 카드가 연속 신뢰도인 척하지 않도록
# 계단 등급/소스/근거를 서버가 명시한다(⑳-F 진단 반영).
# 표시점수(truth 관계=truth_score, market 관계=market_score) 계단값→등급 코드.
# STEP 0-4 대응표 ground truth: 계단값 85/60/35 (+ 미검증 0/기타).
GRADE_CONFIRMED = "confirmed"
GRADE_LIKELY = "likely"
GRADE_OBSERVED = "observed"
GRADE_UNVERIFIED = "unverified"


def _grade_by_score(score):
    """표시점수 계단값 → 등급 코드(FE가 문구로 렌더). 원점수 체계는 불변."""
    if score is None:
        return GRADE_UNVERIFIED
    if score >= 85:
        return GRADE_CONFIRMED
    if score >= 60:
        return GRADE_LIKELY
    if score >= 35:
        return GRADE_OBSERVED
    return GRADE_UNVERIFIED


# relation_type → 근거 소스 코드. SEC 공시 계열은 basis_summary가 근거 역할
# (evidence_count_total은 SEC 텍스트 미집계 → '근거 0건' 오해 방지, ⑳-F Q2-3).
SOURCE_SEC = "sec_filing"
SOURCE_MARKET_PEER = "market_peer"
SOURCE_CO_MENTION = "co_mention"
SOURCE_PRICE_CORR = "price_corr"
SOURCE_UNKNOWN = "unknown"

GRADE_SOURCE_BY_TYPE = {
    "SUPPLIES_TO": SOURCE_SEC,
    "COMPETES_WITH": SOURCE_SEC,
    "DEPENDS_ON": SOURCE_SEC,
    "PARTNER_WITH": SOURCE_SEC,
    "PEER_OF": SOURCE_MARKET_PEER,
    "PEER": SOURCE_MARKET_PEER,
    "CO_MENTIONED": SOURCE_CO_MENTION,
    "PRICE_CORRELATED": SOURCE_PRICE_CORR,
}

# 카드 1줄 노출용 서버측 길이 캡(방어). basis_summary 실측 최대 110자이나
# 파이프라인 변경 시 대비해 상한을 둔다(HALT 조건: 비정형 대용량 방지).
BASIS_SUMMARY_MAX_LEN = 160

# 표시점수는 관계 카테고리에 따라 다른 컬럼에서 온다(truth vs market).
TRUTH_CATEGORY = "truth"


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
                # ⑳-2: 카드 필드 additive — evidence_count_total·last_observed_at 는
                # 동일 쿼리에 컬럼만 추가(N+1 없음). 기존 필드 불변.
                "symbol_a",
                "symbol_b",
                "relation_type",
                "truth_score",
                "evidence_count_total",
                "last_observed_at",
                # ⑳-G S1: 등급·소스·근거 additive — 동일 쿼리 컬럼 추가(N+1 없음).
                "relation_category",
                "market_score",
                "relation_basis_summary",
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

        # 중심성 순위 (⑲ S3, additive) — 최신 as_of 스냅샷 기준, 없으면 null.
        # 단일 조회(최신 as_of) + 단일 조회(순위) — N+1 없음. 스냅샷 부재 시 1쿼리로 종료.
        latest_as_of = (
            SymbolCentrality.objects.filter(symbol__in=node_syms)
            .order_by("-as_of")
            .values_list("as_of", flat=True)
            .first()
        )
        rank_map = {}
        if latest_as_of is not None:
            rank_map = {
                r["symbol"]: r
                for r in SymbolCentrality.objects.filter(
                    symbol__in=node_syms, as_of=latest_as_of
                ).values("symbol", "pagerank_rank", "betweenness_rank")
            }

        # 노드 payload
        nodes = []
        for sym in node_syms:
            st = stock_map.get(sym)
            rk = rank_map.get(sym)
            nodes.append({
                "symbol": sym,
                "name": (st.stock_name if st else "") or "",
                "sector": (st.sector if st else "") or "",
                "pagerank_rank": rk["pagerank_rank"] if rk else None,
                "betweenness_rank": rk["betweenness_rank"] if rk else None,
            })

        # 엣지 payload (+ trend 요약)
        edges = []
        for e in edge_rows:
            other = e["symbol_b"] if e["symbol_a"] == symbol else e["symbol_a"]
            key = normalize_pair(e["symbol_a"], e["symbol_b"])
            last_obs = e.get("last_observed_at")
            # ⑳-G S1: 표시점수는 카테고리별 컬럼에서(truth vs market). 원값 불변.
            display_score = (
                e["truth_score"]
                if e.get("relation_category") == TRUTH_CATEGORY
                else e.get("market_score")
            )
            basis = (e.get("relation_basis_summary") or "")[:BASIS_SUMMARY_MAX_LEN]
            last_obs_iso = last_obs.date().isoformat() if last_obs else None
            edges.append({
                "source": symbol,
                "target": other,
                "relation_type": e["relation_type"],
                "truth_score": round(e["truth_score"] or 0.0, 2),
                # ⑳-2 카드 필드(additive): 근거 건수·최근 관측일(YYYY-MM-DD).
                "evidence_count": e.get("evidence_count_total") or 0,
                "last_mentioned": last_obs_iso,  # 기존 필드 유지(호환)
                "trend": _trend_summary(traj.get(key, []), trend_window),
                # ⑳-G S1 additive: 정직화 카드용 등급·소스·근거·확인일.
                "grade": _grade_by_score(display_score),
                "grade_source": GRADE_SOURCE_BY_TYPE.get(
                    e["relation_type"], SOURCE_UNKNOWN
                ),
                "basis_summary": basis,
                "last_observed_at": last_obs_iso,  # 신규 명시 필드(FE는 "확인일"로 사용)
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
