"""
CS-UNIV Part A(T1) + Part B — DB만으로 계산 (FMP 콜 0).
실행: python manage.py shell -c "exec(open('docs/chain_sight/univ_analysis/measure_db.py').read())"
READ-ONLY. DB 쓰기 없음.
"""
import statistics
from collections import defaultdict, Counter
from packages.shared.stocks.models import Stock, SP500Constituent
from services.serverless.models import ETFProfile, ETFHolding
from apps.chain_sight.models import CompanyChainProfile
from apps.chain_sight.management.commands.load_themes_to_neo4j import ETF_THEME_MAP


def pctile(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


print("=" * 70)
# ── 0. 유니버스 정의 ──
univ = set(Stock.objects.values_list("symbol", flat=True))
sp500_active = set(SP500Constituent.objects.filter(is_active=True).values_list("symbol", flat=True))
print(f"Stock(유니버스): {len(univ)}")
print(f"SP500Constituent active: {len(sp500_active)} / total: {SP500Constituent.objects.count()}")
print(f"Stock ∩ SP500active: {len(univ & sp500_active)} | Stock-SP500: {len(univ - sp500_active)} | SP500-Stock: {len(sp500_active - univ)}")

# ── 1. T1: ETFHolding 유니크 티커 중 유니버스 외 ──
etf_tickers = set(t.upper() for t in ETFHolding.objects.values_list("stock_symbol", flat=True))
t1_new = etf_tickers - univ
print(f"\nETFHolding 유니크 티커: {len(etf_tickers)}")
print(f"T1 신규(ETF holdings 중 유니버스 외): {len(t1_new)}")
print(f"T1 누적 유니버스: {len(univ | t1_new)}")

# T1 신규 종목의 weight 분포 (해당 티커의 max weight per holding row)
t1_weights = sorted(
    float(w) for sym, w in ETFHolding.objects.exclude(weight_percent__isnull=True).values_list("stock_symbol", "weight_percent")
    if sym.upper() in t1_new
)
if t1_weights:
    print(f"T1 신규 weight 분포: median={statistics.median(t1_weights):.3f} "
          f"p25={pctile(t1_weights, 25):.3f} p75={pctile(t1_weights, 75):.3f} (n={len(t1_weights)})")

# ── 2. Part B: tier별 theme 보드 시뮬레이션 (w>=1.0 고정) ──
WEIGHT_THR = 1.0
cp_syms = set(CompanyChainProfile.objects.values_list("symbol__symbol", flat=True))


def theme_board(universe, profile_required=True):
    """주어진 universe 집합에서 theme-only(w>=1.0) 보드 재계산."""
    sym_themes = defaultdict(set)
    for etf_sym, info in ETF_THEME_MAP.items():
        etf = ETFProfile.objects.filter(symbol=etf_sym, tier="theme").first()
        if not etf:
            continue
        for h in ETFHolding.objects.filter(etf=etf, weight_percent__gte=WEIGHT_THR):
            s = h.stock_symbol.upper()
            if s in universe:
                sym_themes[s].add(info["name"])
    # 커버 종목 = universe 내 theme 태그 보유 (profile_required면 ChainProfile 있는 것만)
    covered = [s for s in sym_themes if (not profile_required or s in cp_syms or s in universe)]
    c = Counter()
    for s in sym_themes:
        for t in sym_themes[s]:
            c[t] += 1
    counts = sorted(c.values())
    return {
        "groups": len(c),
        "covered": len(sym_themes),
        "per_group_median": statistics.median(counts) if counts else 0,
        "per_group_min": min(counts) if counts else 0,
        "per_group_max": max(counts) if counts else 0,
        "coverage_pct": 100 * len(sym_themes) / len(universe) if universe else 0,
        "detail": dict(c.most_common()),
    }


print("\n── Part B: tier별 theme-only 보드 (w>=1.0, profile 무관 universe 기준) ──")
scenarios = {
    "현행(535)": univ,
    "T1(누적)": univ | t1_new,
}
for label, u in scenarios.items():
    r = theme_board(u, profile_required=False)
    print(f"  [{label}] 종목 {len(u)} | 테마그룹 {r['groups']} | 그룹당 med {r['per_group_median']} "
          f"(min {r['per_group_min']}/max {r['per_group_max']}) | 커버 {r['covered']} ({r['coverage_pct']:.1f}%)")
    print(f"      detail: {r['detail']}")
print("=" * 70)
