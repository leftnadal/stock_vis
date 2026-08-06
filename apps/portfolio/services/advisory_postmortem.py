"""SFI-I3 Part 3 — Tier 2 ⑤ advisory 사후분석 v0 (apps/portfolio, 관측 과목).

규칙 6: AdvisoryRun·PortfolioSnapshot은 apps/portfolio 소속 → 사후분석은 여기 배치
(shared에 두면 역방향 import 위반). 순수 관측(ORM 읽기 → 계산, DB 쓰기 0).

STEP0 #5 실측: AdvisoryRun.snapshot(non-null)·holdings_detail[{symbol,shares,...}]+total_krw
확인 → h=21d 근사 NAV 궤적 산출. 단 PortfolioSnapshot은 date-unique update_or_create라
run 시점 총액이 박제되지 않음 → "근사 — 총액 박제 유보(RUN-TOTAL-PERSIST)" 캐비앗 의무.
as_of 이하만 사용(규칙 2).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

_KNOB_KEYS = ("A", "G", "w", "L", "E")
_H21_CAL_APPROX = round(21 * 7 / 5)  # ≈29 달력일 (21거래일 근사)
NAV_CAVEAT = "근사 — 총액 박제 유보(RUN-TOTAL-PERSIST). PortfolioSnapshot date-unique 시계열 재구성."


def advisory_postmortem_v0(as_of: date, user=None) -> dict:
    """auto run 수·트리거 분포·knobs 변동 + h=21d 근사 NAV 궤적."""
    from apps.portfolio.models_my import AdvisoryRun, PortfolioSnapshot

    runs = AdvisoryRun.objects.filter(run_at__date__lte=as_of)
    if user is not None:
        runs = runs.filter(user=user)

    auto = list(runs.filter(trigger="auto").order_by("run_at").values("run_at", "knobs_snapshot"))
    manual_count = runs.filter(trigger="manual").count()

    # knobs 변동 요약 (auto 표본)
    knob_variation = {}
    for key in _KNOB_KEYS:
        vals = [r["knobs_snapshot"].get(key) for r in auto if isinstance(r["knobs_snapshot"], dict) and r["knobs_snapshot"].get(key) is not None]
        if vals:
            knob_variation[key] = {
                "distinct": len(set(map(str, vals))),
                "min": min(vals, key=lambda v: float(v)),
                "max": max(vals, key=lambda v: float(v)),
            }
        else:
            knob_variation[key] = {"distinct": 0, "min": None, "max": None}

    # h=21d 근사 NAV 궤적 (PortfolioSnapshot 시계열)
    snap_qs = PortfolioSnapshot.objects.filter(date__lte=as_of)
    if user is not None:
        snap_qs = snap_qs.filter(user=user)
    nav_by_user: dict[str, list] = {}
    for s in snap_qs.order_by("user_id", "date").values("user__username", "date", "total_krw"):
        nav_by_user.setdefault(s["user__username"], []).append((s["date"], s["total_krw"]))

    nav_trajectory = {}
    for uname, series in nav_by_user.items():
        path = [(d.isoformat(), str(t)) for d, t in series]
        # h=21d 실현: 최초 스냅에서 ~21거래일(≈29일) 후 스냅 존재 시 총액 변화
        realized = None
        if series:
            d0, t0 = series[0]
            target = d0 + timedelta(days=_H21_CAL_APPROX)
            later = [(d, t) for d, t in series if d >= target]
            if later:
                d1, t1 = later[0]
                realized = {
                    "from": (d0.isoformat(), str(t0)),
                    "to": (d1.isoformat(), str(t1)),
                    "delta_krw": str(t1 - t0),
                    "pct": float((t1 - t0) / t0) if t0 else None,
                }
            else:
                realized = {
                    "status": "immature",
                    "earliest_maturity_est": target.isoformat(),
                }
        nav_trajectory[uname] = {
            "path": path,
            "h21_realized": realized,
            "caveat": NAV_CAVEAT,
        }

    return {
        "as_of": as_of.isoformat(),
        "auto_run_count": len(auto),
        "manual_run_count": manual_count,
        "auto_run_at_range": (
            auto[0]["run_at"].isoformat() if auto else None,
            auto[-1]["run_at"].isoformat() if auto else None,
        ),
        "knob_variation": knob_variation,
        "nav_trajectory": nav_trajectory,
    }
