"""CS-P5-FE-CARD Slice B2 — 마인드맵 카드 화면 읽기 전용 API (GET only).

D1: 메인 = 업종 2단(sector→industry) 주소 + 종목 카드. 관계 그래프 동결.
D-CARD-GATE(재정의): 연결 표시 = serving_layer='evidence' AND relation_type ∈ SEC4종.
  CO_MENTIONED은 evidence여도 "같은 그룹"(연결 아님), excluded는 전 화면 미표시.
게이트 필터는 **백엔드 쿼리에서** 적용(FE 후처리 금지). 스키마·쓰기 변경 없음(전부 조회).
"""

from collections import defaultdict

from datetime import timedelta

from django.apps import apps
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.models import RelationConfidence

# D-CARD-GATE 정본(B1-2 실측 enum). ACQUIRED은 방향 관계지만 현재 착지 0(D-ACQ-DIR·빈 상태).
SEC4_TYPES = ("COMPETES_WITH", "PARTNER_WITH", "SUPPLIES_TO", "DEPENDS_ON")
DIRECTED_TYPES = ("SUPPLIES_TO", "DEPENDS_ON", "ACQUIRED")  # a→b 방향 의미 보유
EVIDENCE = "evidence"
UNCLASSIFIED = "미분류"


def _gate_qs():
    """게이트 통과 연결 = evidence AND SEC4종 (excluded 자동 제외)."""
    return RelationConfidence.objects.filter(
        serving_layer=EVIDENCE, relation_type__in=SEC4_TYPES
    )


def _comention_qs():
    return RelationConfidence.objects.filter(
        serving_layer=EVIDENCE, relation_type="CO_MENTIONED"
    )


def _degree_maps():
    """게이트 연결 수 / CO_MENTIONED 그룹 수 / 최근 7일 신규 게이트 연결(관측성) 집계.

    C-2 신규 배지: 게이트 통과 연결의 first_observed_at 기준 최근 7일 이내 생성 카운트.
    스키마 변경 없음(기존 first_observed_at=auto_now_add 재사용).
    """
    from datetime import timedelta

    from django.utils import timezone

    gate_deg = defaultdict(int)
    for a, b in _gate_qs().values_list("symbol_a", "symbol_b"):
        gate_deg[a] += 1
        gate_deg[b] += 1
    grp_deg = defaultdict(int)
    for a, b in _comention_qs().values_list("symbol_a", "symbol_b"):
        grp_deg[a] += 1
        grp_deg[b] += 1
    new_deg = defaultdict(int)
    since = timezone.now() - timedelta(days=7)
    for a, b in _gate_qs().filter(first_observed_at__gte=since).values_list("symbol_a", "symbol_b"):
        new_deg[a] += 1
        new_deg[b] += 1
    return gate_deg, grp_deg, new_deg


class MindmapTreeView(APIView):
    """GET /api/v1/chainsight/mindmap/tree/

    업종 2단(sector→industry) 트리 + 종목 카드 요약. 755종목 전량(D1).
    sector 없음 → '미분류' 버킷. sector 케이싱 중복은 최다 표기로 정규화.
    """

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request):
        Stock = apps.get_model("stocks", "Stock")
        gate_deg, grp_deg, new_deg = _degree_maps()

        rows = list(Stock.objects.values("symbol", "stock_name", "sector", "industry"))

        # sector 케이싱 정규화: upper 키로 묶고 라벨은 최다 표기 채택.
        label_votes = defaultdict(lambda: defaultdict(int))
        for r in rows:
            sec = (r["sector"] or "").strip()
            if sec:
                label_votes[sec.upper()][sec] += 1
        canon_label = {
            k: max(v.items(), key=lambda x: x[1])[0] for k, v in label_votes.items()
        }

        def sector_label(sec):
            sec = (sec or "").strip()
            return canon_label.get(sec.upper(), UNCLASSIFIED) if sec else UNCLASSIFIED

        # sector -> industry -> [card]
        tree = defaultdict(lambda: defaultdict(list))
        for r in rows:
            sym = r["symbol"]
            sec = sector_label(r["sector"])
            ind = (r["industry"] or "").strip() or UNCLASSIFIED
            tree[sec][ind].append(
                {
                    "ticker": sym,
                    "name": r["stock_name"] or sym,
                    "gate_conn_count": gate_deg.get(sym, 0),
                    "group_signal_count": grp_deg.get(sym, 0),
                    "new_conn_7d": new_deg.get(sym, 0),
                }
            )

        sectors = []
        for sec in sorted(tree.keys(), key=lambda s: (s == UNCLASSIFIED, s)):
            industries = []
            sec_stock_total = 0
            for ind in sorted(tree[sec].keys(), key=lambda s: (s == UNCLASSIFIED, s)):
                cards = sorted(tree[sec][ind], key=lambda c: c["ticker"])
                sec_stock_total += len(cards)
                industries.append(
                    {"industry": ind, "stock_count": len(cards), "cards": cards}
                )
            sectors.append(
                {
                    "sector": sec,
                    "stock_count": sec_stock_total,
                    "industry_count": len(industries),
                    "industries": industries,
                }
            )

        # C-2 관측성: 최근 7일 신규 게이트 연결 총건수(무방향 degree 합/2 = 엣지 수 근사).
        recent_new_edges = _gate_qs().filter(
            first_observed_at__gte=timezone.now() - timedelta(days=7)
        ).count()

        return Response(
            {
                "gate_definition": "serving_layer=evidence AND relation_type∈"
                + "/".join(SEC4_TYPES),
                "stock_total": len(rows),
                "sector_count": len(sectors),
                "recent_new_connections_7d": recent_new_edges,
                "sectors": sectors,
            }
        )


class MindmapCardView(APIView):
    """GET /api/v1/chainsight/mindmap/card/<symbol>/

    카드 상세: 게이트 통과 연결(상대·유형·방향·강도·계약일) + '같은 그룹'(CO_MENTIONED)
    분리 배열 + ACQUIRED 방향 구조(현재 0=빈 상태 정상). excluded 미노출.
    """

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, symbol):
        from django.db.models import Q

        symbol = symbol.upper()
        Stock = apps.get_model("stocks", "Stock")
        name_map = dict(Stock.objects.values_list("symbol", "stock_name"))

        # 계약일(8-K 유래) 룩업: (source_symbol, resolved_ticker, rel) → 최신 filing_date.
        SEC8K = apps.get_model("sec_pipeline", "SEC8KCounterpartyEvidence")
        contract = {}
        for e in SEC8K.objects.filter(
            landed=True, filing__isnull=False
        ).filter(Q(source_symbol=symbol) | Q(resolved_ticker=symbol)).values(
            "source_symbol", "resolved_ticker", "relationship_type", "filing_date"
        ):
            key = (
                frozenset([e["source_symbol"], e["resolved_ticker"]]),
                e["relationship_type"],
            )
            d = e["filing_date"]
            if key not in contract or (d and str(d) > str(contract[key])):
                contract[key] = d

        connections, acquired = [], []
        gate_rows = _gate_qs().filter(Q(symbol_a=symbol) | Q(symbol_b=symbol))
        for rc in gate_rows.values(
            "symbol_a", "symbol_b", "relation_type", "canonical_direction",
            "sync_strength", "truth_score", "relation_status", "relation_basis_summary",
        ):
            other = rc["symbol_b"] if rc["symbol_a"] == symbol else rc["symbol_a"]
            # 방향: DIRECTED 유형만 의미. a→b 기준으로 in/out 판정.
            if rc["relation_type"] in DIRECTED_TYPES:
                direction = "out" if rc["symbol_a"] == symbol else "in"
            else:
                direction = "both"
            cd = contract.get(
                (frozenset([symbol, other]), rc["relation_type"])
            )
            connections.append(
                {
                    "other": other,
                    "other_name": name_map.get(other, other),
                    "relation_type": rc["relation_type"],
                    "direction": direction,
                    "sync_strength": rc["sync_strength"],
                    "contract_date": cd.isoformat() if cd else None,
                    "truth_score": rc["truth_score"],
                    "status": rc["relation_status"],
                    "basis": rc["relation_basis_summary"],
                }
            )

        # ACQUIRED(방향 관계) — 현재 데이터 0 정상(D-ACQ-DIR). evidence AND ACQUIRED.
        acq_rows = RelationConfidence.objects.filter(
            serving_layer=EVIDENCE, relation_type="ACQUIRED"
        ).filter(Q(symbol_a=symbol) | Q(symbol_b=symbol))
        for rc in acq_rows.values("symbol_a", "symbol_b"):
            other = rc["symbol_b"] if rc["symbol_a"] == symbol else rc["symbol_a"]
            acquired.append(
                {
                    "other": other,
                    "other_name": name_map.get(other, other),
                    "role": "acquirer" if rc["symbol_a"] == symbol else "target",
                }
            )

        # 같은 그룹(CO_MENTIONED) — 연결과 분리. 허브 대비 캡(top N by co_mention_count).
        groups = []
        for rc in _comention_qs().filter(
            Q(symbol_a=symbol) | Q(symbol_b=symbol)
        ).values("symbol_a", "symbol_b", "evidence_sources", "market_score"):
            other = rc["symbol_b"] if rc["symbol_a"] == symbol else rc["symbol_a"]
            cnt = (rc.get("evidence_sources") or {}).get("co_mention_count", 0)
            groups.append(
                {"other": other, "other_name": name_map.get(other, other),
                 "co_mention_count": cnt}
            )
        groups.sort(key=lambda g: -(g["co_mention_count"] or 0))
        group_total = len(groups)
        groups = groups[:20]  # 허브(NVDA 172) 대비 캡

        return Response(
            {
                "symbol": symbol,
                "name": name_map.get(symbol, symbol),
                "connections": sorted(
                    connections, key=lambda c: -(c["truth_score"] or 0)
                ),
                "connection_count": len(connections),
                "acquired": acquired,  # 현재 0=빈 상태 정상(방향 구조는 FE가 렌더)
                "groups": groups,
                "group_total": group_total,
                "group_capped": group_total > 20,
            }
        )
