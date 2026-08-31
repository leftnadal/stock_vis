"""백본 뷰 API (RC-C-1 슬라이스 1) — 활성 해자 부분그래프 중심성 + θ 엣지.

GET /api/v1/chainsight/backbone/?limit=20  (IsAuthenticated)

compute-on-read(D-RC-C1-STORAGE 옵션 C): 지속 모델·마이그레이션 없이 요청 시
services.centrality.compute_backbone_centrality 로 582노드/2,365엣지 부분그래프를
즉석 계산(수십 ms) + 15분 캐시. ⑲ SymbolCentrality(전량·일별 append)와 별개 표면.

응답:
  as_of        기준일(계산일)
  computed_at  계산 시각(ISO, 캐시 스냅샷 생성 시각)
  graph_size   {nodes, edges} 백본 그래프 규모
  top_symbols  [{symbol, pagerank, degree}] pagerank 내림차순 상위 limit
  edges        상위 심볼 유도 부분그래프의 θ≥0.85 엣지만
               [{symbol_a, symbol_b, score(=max), category, evidence_count,
                 observed_count, trust}]

θ 는 하드코딩 금지 — services.score_scale.GRADE_CONFIRMED_MIN 단일 소스 import.
"""

import json
import logging

from django.core.cache import cache
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chain_sight.models import RelationConfidence
from apps.chain_sight.services.centrality import (
    BACKBONE_STATUS_ALLOW,
    compute_backbone_centrality,
)
from apps.chain_sight.services.score_scale import GRADE_CONFIRMED_MIN

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
CACHE_TTL = 60 * 15  # 15분 (선례 동형)


class BackboneView(APIView):
    """활성 해자 백본 — 중심성 상위 + θ≥0.85 유도 부분그래프 엣지."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_LIMIT
        limit = max(1, min(MAX_LIMIT, limit))

        cache_key = f"chainsight:backbone:v1:{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(json.loads(cached))

        rows, meta = compute_backbone_centrality()
        top = rows[:limit]
        top_symbols = [
            {"symbol": r["symbol"], "pagerank": r["pagerank"], "degree": r["degree"]}
            for r in top
        ]

        edges = self._induced_theta_edges({r["symbol"] for r in top})

        payload = {
            "as_of": str(timezone.now().date()),
            "computed_at": timezone.now().isoformat(),
            "graph_size": {"nodes": meta["graph_nodes"], "edges": meta["graph_edges"]},
            "theta": GRADE_CONFIRMED_MIN,
            "top_symbols": top_symbols,
            "edges": edges,
        }

        # B(궤적 discriminator) 판단 재료: top-20 순위 INFO 로그.
        logger.info(
            "chainsight backbone computed: nodes=%d edges=%d top20=%s",
            meta["graph_nodes"], meta["graph_edges"],
            [(r["symbol"], round(r["pagerank"], 6), r["degree"]) for r in rows[:20]],
        )

        cache.set(cache_key, json.dumps(payload), timeout=CACHE_TTL)
        return Response(payload)

    @staticmethod
    def _induced_theta_edges(top_set):
        """상위 심볼 유도 부분그래프의 θ≥0.85 엣지(무향 collapse, 쌍당 최고점 행)."""
        theta = GRADE_CONFIRMED_MIN
        pair_best = {}
        rows = RelationConfidence.objects.filter(
            relation_status__in=BACKBONE_STATUS_ALLOW,
            symbol_a__in=top_set,
            symbol_b__in=top_set,
        ).values(
            "symbol_a", "symbol_b", "truth_score", "market_score",
            "relation_category", "evidence_count_total", "evidence_streak",
            "relation_status",
        )
        for r in rows:
            a, b = r["symbol_a"], r["symbol_b"]
            if a == b:
                continue
            score = max(r["truth_score"] or 0.0, r["market_score"] or 0.0)
            if score < theta:
                continue
            key = (a, b) if a <= b else (b, a)
            prev = pair_best.get(key)
            if prev is None or score > prev["score"]:
                pair_best[key] = {
                    "symbol_a": key[0],
                    "symbol_b": key[1],
                    "score": score,
                    "category": r["relation_category"],
                    "evidence_count": r["evidence_count_total"],
                    "observed_count": r["evidence_streak"],
                    "trust": r["relation_status"],
                }
        return sorted(
            pair_best.values(), key=lambda e: (-e["score"], e["symbol_a"], e["symbol_b"])
        )
