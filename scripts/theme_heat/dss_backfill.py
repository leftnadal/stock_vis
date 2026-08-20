#!/usr/bin/env python3
"""DSS 백필 + 검산 + Δ분포 (DSS-IMPL-1 Slice 4).

가용 전 인접 WoW 쌍의 anchor를 일괄 적재(store_for_anchor, append-only) 후
date-scoped invariant 검산 + |Δeps/eps_prev| 분위수 로그. foreground.

검산(정적 행수 게이트 금지): anchor별 up+down+flat+excluded = 매칭 시도 수 /
breadth ∈ [−1,+1] / 유효분모 > 0(또는 not_computed) / HONA 이른 anchor 부재.
"""
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.chain_sight.models import (  # noqa: E402
    SymbolDemandSignal,
    ThemeDemandScore,
)
from apps.chain_sight.services.demand_signal import store_for_anchor  # noqa: E402

ANCHORS = [date(2026, 7, 24), date(2026, 7, 31), date(2026, 8, 7), date(2026, 8, 14)]
BACKFILL = [date(2026, 7, 24), date(2026, 7, 31), date(2026, 8, 7)]  # 08-14는 Slice 3에서 적재


def quantile(sorted_vals, q):
    if not sorted_vals:
        return None
    idx = min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1) + 0.5))
    return sorted_vals[idx]


def main():
    apply = "--apply" in sys.argv
    print("=" * 72)
    print(f"DSS 백필 + 검산 (DSS-IMPL-1 Slice 4) {'[APPLY]' if apply else '[DRY]'}")
    print("=" * 72)

    # ── 백필 ──
    for a in BACKFILL:
        s = store_for_anchor(a, dry_run=not apply)
        tag = "written" if apply and not s.get("skipped_existing") else (
            "skip(존재)" if s.get("skipped_existing") else "dry")
        print(f"  적재 {a}: n={s['n_signals']} up={s['up']} down={s['down']} "
              f"flat={s['flat']} excl={s['excluded']} {s['exclude_reasons']} "
              f"scores={s['written_scores']} [{tag}]")

    if not apply:
        print("\n(DRY — 쓰기 없음. --apply로 실적재)")
        return

    # ── 검산 (date-scoped invariant) ──
    print("\n── 검산 (anchor별) ──")
    all_ok = True
    for a in ANCHORS:
        sigs = list(SymbolDemandSignal.objects.filter(anchor_date=a)
                    .values_list("direction", "excluded", "eps_prev", "eps_curr", "symbol"))
        n = len(sigs)
        up = sum(1 for d, e, *_ in sigs if not e and d == 1)
        down = sum(1 for d, e, *_ in sigs if not e and d == -1)
        flat = sum(1 for d, e, *_ in sigs if not e and d == 0)
        excl = sum(1 for d, e, *_ in sigs if e)
        inv1 = (up + down + flat + excl == n)
        scores = list(ThemeDemandScore.objects.filter(date=a)
                      .values_list("status", "components"))
        breadths = [c.get("breadth") for _, c in scores if c.get("breadth") is not None]
        inv2 = all(-1 <= b <= 1 for b in breadths)
        denoms = [c.get("valid_denom") for st, c in scores if st != ThemeDemandScore.STATUS_NOT_COMPUTED]
        inv3 = all(d > 0 for d in denoms)
        hona = SymbolDemandSignal.objects.filter(anchor_date=a, symbol="HONA").count()
        inv4 = (hona == 0) if a != date(2026, 8, 14) else True  # HONA는 08-14부터 유입
        ok = inv1 and inv2 and inv3 and inv4
        all_ok &= ok
        print(f"  {a}: n={n} up={up} down={down} flat={flat} excl={excl} "
              f"| 합=n {inv1} · breadth∈[-1,1] {inv2} · denom>0 {inv3} · HONA {hona}({inv4}) {'✅' if ok else '❌'}")
    print(f"  전 anchor 검산: {'✅ PASS' if all_ok else '❌ FAIL'}")

    # ── Δ분포 (excluded=false, eps_prev != 0) ──
    print("\n── Δ분포: |Δeps/eps_prev| (excluded=false) ──")
    ratios = []
    zero = 0
    tot = 0
    for a in ANCHORS:
        for d, e, ep, ec, sym in SymbolDemandSignal.objects.filter(
            anchor_date=a, excluded=False
        ).values_list("direction", "excluded", "eps_prev", "eps_curr", "symbol"):
            if ep is None or ec is None:
                continue
            tot += 1
            delta = float(ec) - float(ep)
            if delta == 0:
                zero += 1
            if float(ep) != 0:
                ratios.append(abs(delta) / abs(float(ep)))
    ratios.sort()
    print(f"  표본(유효분모 전 anchor 합) = {tot}, 0(불변) 비율 = {zero}/{tot} ({zero/tot*100:.1f}%)")
    for q in (0.50, 0.75, 0.90, 0.99):
        v = quantile(ratios, q)
        print(f"  p{int(q*100)} |Δeps/eps_prev| = {v:.5f}" if v is not None else f"  p{int(q*100)} = n/a")


if __name__ == "__main__":
    main()
