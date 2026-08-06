"""SFI-I3 Part 3 — Tier 2 ④ 개정 추적 (packages/shared, 관측 과목).

우리가 append한 AnalystSignalSnapshot 시계열에서 심볼별 target consensus 일간 delta와
의견 분포(grade_consensus·grade_* 카운트) 변화를 관측한다. 순수 관측(판정 아님, D-I3-2 Tier 2).
as_of 이하만 사용(규칙 2). #6 실측 구조: grade_strong_buy~grade_strong_sell + grade_consensus.
"""
from __future__ import annotations

import statistics
from datetime import date
from typing import Optional


def _abs(x) -> float:
    return float(x if x >= 0 else -x)


def revision_tracking(as_of: date, symbols=None) -> dict:
    """심볼별 연속 스냅샷 간 target consensus delta·의견 합의 변화.

    반환 = {as_of, per_symbol:{sym:{snapshots, target_deltas:[(date,delta)],
            consensus_changes:[(date,from,to)], last_consensus}}, aggregate:{...}}.
    """
    from packages.shared.stocks.models import AnalystSignalSnapshot

    qs = AnalystSignalSnapshot.objects.filter(captured_at__date__lte=as_of)
    if symbols:
        qs = qs.filter(symbol__in=[s.upper() for s in symbols])
    rows = list(
        qs.order_by("symbol", "captured_at").values(
            "symbol", "captured_at", "target_consensus", "grade_consensus"
        )
    )

    per_symbol: dict[str, dict] = {}
    all_abs_deltas: list[float] = []
    total_revisions = 0
    total_consensus_changes = 0

    by_sym: dict[str, list] = {}
    for r in rows:
        by_sym.setdefault(r["symbol"], []).append(r)

    for sym, srows in by_sym.items():
        target_deltas = []
        consensus_changes = []
        for prev, cur in zip(srows, srows[1:]):
            d = cur["captured_at"].date().isoformat()
            pt, ct = prev["target_consensus"], cur["target_consensus"]
            if pt is not None and ct is not None and ct != pt:
                delta = float(ct - pt)
                target_deltas.append((d, delta))
                all_abs_deltas.append(abs(delta))
                total_revisions += 1
            pc, cc = prev["grade_consensus"], cur["grade_consensus"]
            if (pc or "") != (cc or ""):
                consensus_changes.append((d, pc or "", cc or ""))
                total_consensus_changes += 1
        per_symbol[sym] = {
            "snapshots": len(srows),
            "target_deltas": target_deltas,
            "revision_count": len(target_deltas),
            "consensus_changes": consensus_changes,
            "last_consensus": srows[-1]["grade_consensus"] or "",
        }

    aggregate = {
        "symbols": len(by_sym),
        "total_revisions": total_revisions,
        "total_consensus_changes": total_consensus_changes,
        "median_abs_delta": statistics.median(all_abs_deltas) if all_abs_deltas else None,
        "max_abs_delta": max(all_abs_deltas) if all_abs_deltas else None,
    }
    return {"as_of": as_of.isoformat(), "per_symbol": per_symbol, "aggregate": aggregate}
