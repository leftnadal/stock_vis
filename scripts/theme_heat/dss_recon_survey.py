#!/usr/bin/env python3
"""TH-DSS-IMPL 설계 정찰 — EstimateSnapshot 커버리지·WoW·함정 A/B 실측 (DSS-RECON-1).

read-only · 결정론(재실행 동일) · DB 쓰기 0 · LLM 0 · 외부 API 0.

산출: ②커버리지 · ④WoW 매칭 · ⑤함정 A(회계기간 롤오버) · ⑥함정 B(컨센서스 구성).
매칭 단위 = (symbol, fiscal_year) — 스냅샷당 당기·차기 2 FY 행이므로 FY 분리 필수.
롤오버 의심 기준(사실 태그, 판정 아님) = |WoW EPS diff| > 직전 EPS 절대값의 30%.
"""
import os
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402

UNIVERSE_REF = 503


def load():
    with connection.cursor() as cur:
        cur.execute(
            "SELECT symbol, snapshot_date, fiscal_year, eps_avg, num_analysts_eps "
            "FROM chainsight_estimatesnapshot ORDER BY snapshot_date, symbol, fiscal_year"
        )
        rows = cur.fetchall()
        # 유니버스 (SP500 active)
        try:
            cur.execute("SELECT symbol, sector FROM stocks_sp500_constituent WHERE is_active=true")
            uni = {r[0].upper(): (r[1] or "(none)") for r in cur.fetchall()}
        except Exception:
            uni = {}
    return rows, uni


def main():
    rows, uni = load()
    dates = sorted(set(r[1] for r in rows))
    # 인덱스
    by_date_sym_fy = {}          # (date, sym, fy) -> (eps, n)
    syms_by_date = defaultdict(set)
    fys_by_date_sym = defaultdict(set)  # (date, sym) -> {fy}
    for sym, d, fy, eps, n in rows:
        s = sym.upper()
        by_date_sym_fy[(d, s, fy)] = (float(eps) if eps is not None else None, n)
        syms_by_date[d].add(s)
        fys_by_date_sym[(d, s)].add(fy)

    print("=" * 78)
    print("TH-DSS-IMPL 정찰 — EstimateSnapshot 실측 (DSS-RECON-1, read-only·결정론)")
    print("=" * 78)
    print(f"회차 = {[str(d) for d in dates]}  (총 {len(dates)}회)\n")

    # ── ② 커버리지 ──
    print("── ② 커버리지 ──")
    print(f"  유니버스 참조 = {UNIVERSE_REF} (SP500 active 로드 = {len(uni)})")
    for d in dates:
        n = len(syms_by_date[d])
        print(f"  {d} ({d.strftime('%a')}): 종목 {n}  ({n/UNIVERSE_REF*100:.1f}% of {UNIVERSE_REF})")
    all_syms = set().union(*syms_by_date.values()) if syms_by_date else set()
    core = set(all_syms)
    for d in dates:
        core &= syms_by_date[d]
    intermittent = all_syms - core
    print(f"  코어(전 {len(dates)}회차 연속 존재) = {len(core)}  |  간헐 = {len(intermittent)}  |  합집합 = {len(all_syms)}")
    # 결측 패턴: 간헐 종목이 어느 회차에 빠지는지
    miss_by_date = {d: 0 for d in dates}
    for s in intermittent:
        for d in dates:
            if s not in syms_by_date[d]:
                miss_by_date[d] += 1
    print(f"  간헐 종목 회차별 결측 수: {[(str(d), miss_by_date[d]) for d in dates]}")
    print(f"  결측 패턴 = {'특정 회차 집중' if max(miss_by_date.values())>len(intermittent)*0.7 else '종목별 산발'}")
    # 섹터 분포 (유니버스 기준 분모)
    if uni:
        sec_uni = defaultdict(int)
        for s, sec in uni.items():
            sec_uni[sec] += 1
        latest = dates[-1]
        sec_cov = defaultdict(int)
        for s in syms_by_date[latest]:
            if s in uni:
                sec_cov[uni[s]] += 1
        print(f"  섹터별 커버리지(최신 {latest} 기준, 분모=유니버스 섹터 종목수):")
        for sec in sorted(sec_uni):
            cov = sec_cov.get(sec, 0)
            print(f"    {sec:26s}: {cov:3d}/{sec_uni[sec]:3d} ({cov/sec_uni[sec]*100:.0f}%)")
        print(f"  섹터 최소 분모 = {min(sec_uni.values())} ({min(sec_uni, key=sec_uni.get)})")
    # BRK.B / BF.B
    for tkr in ("BRK.B", "BF.B"):
        pres = [str(d) for d in dates if tkr in syms_by_date[d]]
        print(f"  {tkr} 존재 회차: {pres or '없음'}")

    # ── ④ WoW 매칭 (7일 인접 금요일 쌍) ──
    print("\n── ④ WoW 매칭 (7일 정확) ──")
    # 모든 7일 인접 금요일 쌍 (정렬-인접이 아니라 d+7d 존재 여부로 — 고아 07-29가 끼어도 07-24→07-31 포착)
    dateset = set(dates)
    pairs = [(d, d + timedelta(days=7)) for d in dates if (d + timedelta(days=7)) in dateset]
    orphans = [d for d in dates if (d - timedelta(days=7)) not in dateset
               and (d + timedelta(days=7)) not in dateset]
    print(f"  7일 쌍 = {[(str(a), str(b)) for a, b in pairs]}")
    print(f"  고아(±7일 파트너 부재) = {[str(d) for d in orphans]}")
    wow_match = {}
    for a, b in pairs:
        # (sym, fy) 매칭: 양 회차 모두 eps_avg not null
        keys_a = {(s, fy) for (dd, s, fy), (eps, n) in by_date_sym_fy.items() if dd == a and eps is not None}
        keys_b = {(s, fy) for (dd, s, fy), (eps, n) in by_date_sym_fy.items() if dd == b and eps is not None}
        m = keys_a & keys_b
        wow_match[(a, b)] = m
        syms = set(s for s, fy in m)
        print(f"  {a}→{b}: 매칭 (sym,fy) 쌍 = {len(m)}  (distinct symbol = {len(syms)})")
    # 검산: 매칭 symbol 수 ≤ 각 회차 존재 수
    print("  검산(매칭 distinct symbol ≤ min(양 회차 종목수)):")
    for a, b in pairs:
        syms = set(s for s, fy in wow_match[(a, b)])
        ok = len(syms) <= min(len(syms_by_date[a]), len(syms_by_date[b]))
        print(f"    {a}→{b}: {len(syms)} ≤ min({len(syms_by_date[a])},{len(syms_by_date[b])}) {'✅' if ok else '❌'}")

    # ── ⑤ 함정 A: WoW EPS diff 분포 + |diff| 상위 20 + fiscal 전환 ──
    print("\n── ⑤ 함정 A (회계기간 롤오버) ──")
    diffs = []  # (abs_diff, sym, fy, a, b, prev_eps, cur_eps, pct, suspect)
    for a, b in pairs:
        for (s, fy) in wow_match[(a, b)]:
            prev_eps = by_date_sym_fy[(a, s, fy)][0]
            cur_eps = by_date_sym_fy[(b, s, fy)][0]
            diff = cur_eps - prev_eps
            pct = abs(diff) / abs(prev_eps) if prev_eps not in (0, None) else float("inf")
            suspect = pct > 0.30
            diffs.append((abs(diff), s, fy, a, b, prev_eps, cur_eps, pct, suspect))
    n_suspect = sum(1 for x in diffs if x[8])
    print(f"  WoW diff 표본 = {len(diffs)} (전 쌍 합산)  |  |diff|>30%·직전EPS 의심 태그 = {n_suspect}")
    diffs.sort(reverse=True)
    print("  |diff| 상위 20 (sym FY | 쌍 | prev→cur | Δ | %prev | 의심):")
    for ad, s, fy, a, b, pe, ce, pct, susp in diffs[:20]:
        pj = f"{pct*100:.0f}%" if pct != float("inf") else "inf"
        print(f"    {s:6s} FY{fy} | {a}→{b} | {pe:+.4f}→{ce:+.4f} | Δ{ce-pe:+.4f} | {pj:>5s} | {'의심' if susp else ''}")
    # fiscal_year 전환: 인접 회차 간 동일 종목의 FY 집합 변화
    fy_transitions = 0
    trans_examples = []
    for a, b in pairs:
        for s in syms_by_date[a] & syms_by_date[b]:
            fa = fys_by_date_sym[(a, s)]
            fb = fys_by_date_sym[(b, s)]
            if fa != fb:
                fy_transitions += 1
                if len(trans_examples) < 8:
                    trans_examples.append((s, str(a), sorted(fa), str(b), sorted(fb)))
    print(f"  fiscal_year 집합 전환(인접 회차 동일종목 FY집합 변화) = {fy_transitions}건")
    for s, a, fa, b, fb in trans_examples:
        print(f"    {s}: {a}{fa} → {b}{fb}")

    # ── ⑥ 함정 B: num_analysts 변동 분포 ──
    print("\n── ⑥ 함정 B (컨센서스 구성 = num_analysts_eps) ──")
    buckets = {"unchanged": 0, "±1": 0, "±2+": 0, "null_any": 0}
    for a, b in pairs:
        for (s, fy) in wow_match[(a, b)]:
            na = by_date_sym_fy[(a, s, fy)][1]
            nb = by_date_sym_fy[(b, s, fy)][1]
            if na is None or nb is None:
                buckets["null_any"] += 1
                continue
            d = abs(nb - na)
            buckets["unchanged" if d == 0 else "±1" if d == 1 else "±2+"] += 1
    tot = sum(buckets.values())
    print(f"  WoW 표본 = {tot}")
    for k, v in buckets.items():
        print(f"    {k:10s}: {v:5d} ({v/tot*100:.1f}%)" if tot else f"    {k}: {v}")

    print("\n[실측 근거일 = 회차 최신 " + str(dates[-1]) + " · 표본 재실행 결정론]")


if __name__ == "__main__":
    main()
