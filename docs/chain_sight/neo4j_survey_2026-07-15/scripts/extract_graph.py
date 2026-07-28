"""SLICE B 데이터 추출 (read-only). RelationConfidence 전량 + 섹터 + EventGroup 멤버십을 JSON 덤프."""
import os, django, json
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.chain_sight.models.relation_discovery import RelationConfidence
from apps.chain_sight.models.event_group import EventGroup, GroupMembership
from packages.shared.stocks.models import Stock

OUT = os.path.join(os.path.dirname(__file__), "graph_data.json")

# 1) 엣지: RelationConfidence 전량
edges = list(
    RelationConfidence.objects.values(
        "symbol_a", "symbol_b", "relation_type", "truth_score",
        "market_score", "canonical_direction", "relation_status",
    )
)

# 2) 섹터: 그래프에 등장하는 심볼 → GICS sector
symbols = set()
for e in edges:
    symbols.add(e["symbol_a"])
    symbols.add(e["symbol_b"])
sectors = dict(
    Stock.objects.filter(symbol__in=symbols).values_list("symbol", "sector")
)

# 3) EventGroup 멤버십 (숨김 제외 = 소비 대상 38그룹)
groups = {}
for eg in EventGroup.objects.filter(is_hidden=False).prefetch_related("memberships"):
    members = list(eg.memberships.values_list("symbol_id", "role"))
    groups[eg.id] = {
        "name": eg.name,
        "as_of": str(eg.as_of_date),
        "core": [s for s, r in members if r == "core"],
        "satellite": [s for s, r in members if r == "satellite"],
        "all": [s for s, r in members],
    }

data = {
    "edges": edges,
    "sectors": sectors,
    "event_groups": groups,
    "meta": {
        "edge_count": len(edges),
        "symbol_count": len(symbols),
        "sector_known": sum(1 for s in symbols if sectors.get(s)),
        "group_count": len(groups),
    },
}
with open(OUT, "w") as f:
    json.dump(data, f, default=str)
print(json.dumps(data["meta"], indent=2))
print("wrote", OUT)
