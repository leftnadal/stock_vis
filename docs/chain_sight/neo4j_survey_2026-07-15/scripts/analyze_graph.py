"""SLICE B 드라이런 (read-only, networkx). PostgreSQL 덤프(graph_data.json)를 분석.
Neo4j 미기동 — 순수 in-memory 분석."""
import json, os, time, statistics as st
from collections import defaultdict, Counter
import networkx as nx

HERE = os.path.dirname(__file__)
data = json.load(open(os.path.join(HERE, "graph_data.json")))
edges = data["edges"]
sectors = data["sectors"]
groups = data["event_groups"]

T0 = time.time()

def wt(e):
    ts = e.get("truth_score") or 0.0
    ms = e.get("market_score") or 0.0
    return max(ts, ms)

# ---- 페어 collapse (무방향 simple graph) ----
pair_types = defaultdict(set)          # frozenset(a,b) -> {relation_type}
pair_weight = defaultdict(float)       # frozenset -> max weight
by_type_edges = defaultdict(list)      # relation_type -> [(a,b,w,dir)]
dir_counter = defaultdict(Counter)     # relation_type -> Counter(direction)
score_by_type = defaultdict(list)      # relation_type -> [truth_score]
for e in edges:
    a, b = e["symbol_a"], e["symbol_b"]
    if a == b:
        continue
    rt = e["relation_type"]
    key = frozenset((a, b))
    pair_types[key].add(rt)
    pair_weight[key] = max(pair_weight[key], wt(e))
    by_type_edges[rt].append((a, b, wt(e), e["canonical_direction"]))
    dir_counter[rt][e["canonical_direction"]] += 1
    score_by_type[rt].append(e.get("truth_score") or 0.0)

# 전체 그래프 (collapse)
G = nx.Graph()
for key, w in pair_weight.items():
    a, b = tuple(key)
    G.add_edge(a, b, weight=w, types=pair_types[key])

def dist(vals):
    vals = sorted(vals)
    n = len(vals)
    if not n:
        return {}
    def pct(p):
        return vals[min(n - 1, int(p * n))]
    return {"min": vals[0], "median": vals[n // 2], "p90": pct(0.9),
            "max": vals[-1], "n": n}

report = {}

# ================= B1 형상 =================
b1 = {}
b1["nodes"] = G.number_of_nodes()
b1["edges"] = G.number_of_edges()
b1["density"] = round(nx.density(G), 6)
degs = [d for _, d in G.degree()]
b1["degree_dist"] = dist(degs)
top_deg = sorted(G.degree(), key=lambda x: -x[1])[:10]
b1["top10_degree"] = top_deg

# 연결 성분
comps = sorted(nx.connected_components(G), key=len, reverse=True)
b1["num_components"] = len(comps)
giant = comps[0]
b1["giant_size"] = len(giant)
b1["giant_pct"] = round(100 * len(giant) / G.number_of_nodes(), 2)
b1["component_size_hist"] = Counter(len(c) for c in comps).most_common(8)

# 엣지 타입별 서브그래프
b1["by_type"] = {}
for rt, elist in by_type_edges.items():
    H = nx.Graph()
    for a, b, w, d in elist:
        if a != b:
            H.add_edge(a, b)
    hc = sorted(nx.connected_components(H), key=len, reverse=True)
    b1["by_type"][rt] = {
        "raw_rows": len(elist),
        "nodes": H.number_of_nodes(),
        "edges": H.number_of_edges(),
        "components": len(hc),
        "giant": len(hc[0]) if hc else 0,
    }

# 방향성
b1["directionality"] = {rt: dict(c) for rt, c in dir_counter.items()}

# 타입별 truth_score 분포
b1["truth_score_dist_by_type"] = {
    rt: {"min": round(min(v), 2), "median": round(sorted(v)[len(v)//2], 2),
         "max": round(max(v), 2), "mean": round(sum(v)/len(v), 2), "n": len(v)}
    for rt, v in score_by_type.items() if v
}
report["B1"] = b1

# ================= B2.1 커뮤니티 (Louvain) =================
def louvain_summary(graph, seed=42):
    comms = nx.community.louvain_communities(graph, weight="weight", seed=seed)
    mod = nx.community.modularity(graph, comms, weight="weight")
    sizes = sorted((len(c) for c in comms), reverse=True)
    return comms, mod, sizes

# 자이언트 컴포넌트에서 수행 (분리 노드 제외)
Ggiant = G.subgraph(giant).copy()
comms, mod, sizes = louvain_summary(Ggiant)
b21 = {"modularity": round(mod, 4), "num_communities": len(comms),
       "size_dist": sizes[:15], "giant_nodes": Ggiant.number_of_nodes()}

# (a) 커뮤니티 ↔ GICS 섹터 순도
def sector_purity(comms):
    purities = []
    detail = []
    for c in comms:
        secs = [sectors.get(s) for s in c if sectors.get(s)]
        if not secs:
            continue
        cnt = Counter(secs)
        top_sec, top_n = cnt.most_common(1)[0]
        purity = top_n / len(secs)
        purities.append(purity)
        if len(c) >= 5:
            detail.append({"size": len(c), "dominant": top_sec,
                           "purity": round(purity, 2)})
    return purities, detail
pur, pur_detail = sector_purity(comms)
b21["sector_purity_mean"] = round(sum(pur)/len(pur), 3) if pur else None
b21["sector_purity_weighted"] = round(
    sum(p*1 for p in pur)/len(pur), 3) if pur else None
b21["sector_purity_detail_big"] = sorted(pur_detail, key=lambda x: -x["size"])[:12]

# (b) 커뮤니티 ↔ EventGroup 겹침
# 각 EventGroup(all 멤버)이 몇 개 커뮤니티에 흩어지는지 + 최대 겹침률
node2comm = {}
for i, c in enumerate(comms):
    for s in c:
        node2comm[s] = i
eg_overlap = []
for gid, g in groups.items():
    mem = [s for s in g["all"] if s in node2comm]
    if not mem:
        continue
    spread = Counter(node2comm[s] for s in mem)
    top_comm, top_n = spread.most_common(1)[0]
    eg_overlap.append({"group": g["name"][:30], "members_in_giant": len(mem),
                       "total_members": len(g["all"]),
                       "spread_communities": len(spread),
                       "max_containment": round(top_n/len(mem), 2)})
b21["eventgroup_overlap"] = sorted(eg_overlap, key=lambda x: -x["members_in_giant"])[:15]
b21["eventgroup_overlap_summary"] = {
    "groups_analyzed": len(eg_overlap),
    "avg_max_containment": round(sum(e["max_containment"] for e in eg_overlap)/len(eg_overlap), 3) if eg_overlap else None,
    "avg_spread": round(sum(e["spread_communities"] for e in eg_overlap)/len(eg_overlap), 2) if eg_overlap else None,
}

# co-movement(PRICE_CORRELATED) 제외 버전
G_nopc = nx.Graph()
for key, tset in pair_types.items():
    non_pc = tset - {"PRICE_CORRELATED"}
    if non_pc:
        a, b = tuple(key)
        G_nopc.add_edge(a, b, weight=pair_weight[key])
comps_np = sorted(nx.connected_components(G_nopc), key=len, reverse=True)
if comps_np:
    Gnp_giant = G_nopc.subgraph(comps_np[0]).copy()
    comms_np, mod_np, sizes_np = louvain_summary(Gnp_giant)
    pur_np, _ = sector_purity(comms_np)
    b21["no_pricecomovement"] = {
        "nodes": G_nopc.number_of_nodes(), "edges": G_nopc.number_of_edges(),
        "num_components": len(comps_np), "giant": len(comps_np[0]),
        "modularity": round(mod_np, 4), "num_communities": len(comms_np),
        "sector_purity_mean": round(sum(pur_np)/len(pur_np), 3) if pur_np else None,
        "size_dist": sizes_np[:12],
    }
report["B2_community"] = b21

# ================= B2.2 중심성 =================
pr = nx.pagerank(Ggiant, weight="weight")
bt = nx.betweenness_centrality(Ggiant, weight=None, k=min(300, Ggiant.number_of_nodes()), seed=7)
top_pr = sorted(pr.items(), key=lambda x: -x[1])[:20]
top_bt = sorted(bt.items(), key=lambda x: -x[1])[:20]
pr_set = {s for s, _ in top_pr}
bt_set = {s for s, _ in top_bt}
report["B2_centrality"] = {
    "top20_pagerank": [(s, round(v, 5), sectors.get(s)) for s, v in top_pr],
    "top20_betweenness": [(s, round(v, 5), sectors.get(s)) for s, v in top_bt],
    "hub_only(pr_not_bt)": sorted(pr_set - bt_set),
    "bridge_only(bt_not_pr)": sorted(bt_set - pr_set),
    "overlap": sorted(pr_set & bt_set),
}

# ================= B2.3 경로 =================
# 자이언트 평균 최단경로 (샘플링, 규모 큰 경우)
n_giant = Ggiant.number_of_nodes()
t_path = time.time()
if n_giant <= 1500:
    avg_path = nx.average_shortest_path_length(Ggiant)
else:
    avg_path = None
report["B2_path"] = {"giant_nodes": n_giant,
                     "avg_shortest_path": round(avg_path, 3) if avg_path else "skipped(too big)",
                     "diameter_approx": nx.approximation.diameter(Ggiant) if n_giant <= 2000 else None}
# 이종 섹터 대표 쌍 경로 3개
def find_cross_pair(secA, secB):
    a = [s for s in Ggiant if sectors.get(s) == secA]
    b = [s for s in Ggiant if sectors.get(s) == secB]
    for x in a[:20]:
        for y in b[:20]:
            if nx.has_path(Ggiant, x, y):
                p = nx.shortest_path(Ggiant, x, y)
                return p
    return None
pairs_to_try = [("Technology", "Energy"),
                ("Financial Services", "Healthcare"),
                ("Consumer Cyclical", "Utilities")]
report["B2_path"]["sample_paths"] = {
    f"{x}->{y}": find_cross_pair(x, y) for x, y in pairs_to_try
}

# ================= B2.4 링크 예측 =================
t_lp = time.time()
# Jaccard / Adamic-Adar 상위 미연결 쌍 (자이언트 한정, 연산량 관리)
jc = sorted(nx.jaccard_coefficient(Ggiant), key=lambda x: -x[2])[:20]
aa = sorted(nx.adamic_adar_index(Ggiant), key=lambda x: -x[2])[:20]
report["B2_linkpred"] = {
    "top20_jaccard": [(u, v, round(p, 3), sectors.get(u), sectors.get(v)) for u, v, p in jc],
    "top20_adamic_adar": [(u, v, round(p, 3)) for u, v, p in aa],
}

report["_timing_sec"] = {
    "total_analysis": round(time.time() - T0, 2),
    "path_stage": round(t_lp - t_path, 2),
    "linkpred_stage": round(time.time() - t_lp, 2),
}
report["_meta"] = data["meta"]

OUT = os.path.join(HERE, "analysis_report.json")
json.dump(report, open(OUT, "w"), default=list, indent=2)
print("=== TIMING ===", report["_timing_sec"])
print("wrote", OUT)
