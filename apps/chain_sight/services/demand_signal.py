"""
DSS(재무 지지 점수) 계산·적재 (DSS-IMPL-1 Slice 3).

WoW(7일) EPS 컨센서스 방향 신호 → 섹터 breadth. 순수 분류 함수 + DB 로더 분리.
append-only: SymbolDemandSignal·ThemeDemandScore INSERT만(기존 행 UPDATE/DELETE 금지).

결정: D-DSS-SIGNAL(2-A sign Δeps)·D-DSS-FY-MATCH(동일 차기FY)·D-DSS-ANALYST-FILTER(|Δna|≥2)·
      D-DSS-AGG(1-B breadth=(up−down)/유효분모)·D-DSS-LAGPARAM(WoW=7).
"""
import logging
from datetime import date, timedelta

from apps.chain_sight.models import (
    EstimateSnapshot,
    HeatEntity,
    SymbolDemandSignal,
    ThemeDemandScore,
)
from apps.chain_sight.services.heat_beat import HEAT_ENTITY_TO_SP500_SECTOR
from apps.chain_sight.services.universe_snapshot import sector_constituents

logger = logging.getLogger(__name__)

WOW_LAG_DAYS = 7
ANALYST_DELTA_MAX = 2          # |Δnum_analysts| ≥ 2 → 제외 (D-DSS-ANALYST-FILTER)
BREADTH_TAU = 0.10             # supported/detached 임계 (초판·사후 조정, D-DSS-AGG)


def _sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def classify_symbol(prev_present: bool, prev_fy_row, curr_fy_row) -> dict:
    """
    한 종목의 WoW 방향 분류 (순수 함수). fiscal_year는 호출측이 차기로 고정.

    prev_present   : 지난주(anchor−7d)에 해당 종목의 스냅샷 행이 하나라도 존재하는가.
    prev_fy_row    : 지난주 동일-FY 행 (eps, num_analysts) 또는 None.
    curr_fy_row    : 이번주 동일-FY 행 (eps, num_analysts) — 항상 존재(호출측 curr 순회).

    반환: {direction, excluded, exclude_reason, eps_prev, eps_curr, na_prev, na_curr}.
    우선순위: missing_prev → fy_mismatch → analyst_delta → direction.
    """
    eps_curr, na_curr = curr_fy_row
    base = {
        "eps_prev": None, "eps_curr": eps_curr,
        "na_prev": None, "na_curr": na_curr,
        "direction": None, "excluded": True, "exclude_reason": "",
    }
    if not prev_present:
        base["exclude_reason"] = SymbolDemandSignal.EXCLUDE_MISSING_PREV
        return base
    if prev_fy_row is None:
        base["exclude_reason"] = SymbolDemandSignal.EXCLUDE_FY_MISMATCH
        return base
    eps_prev, na_prev = prev_fy_row
    base["eps_prev"], base["na_prev"] = eps_prev, na_prev
    if na_prev is not None and na_curr is not None and abs(na_curr - na_prev) >= ANALYST_DELTA_MAX:
        base["exclude_reason"] = SymbolDemandSignal.EXCLUDE_ANALYST_DELTA
        return base
    base["excluded"] = False
    base["direction"] = _sign(float(eps_curr) - float(eps_prev))
    return base


def _load_fy_rows(snapshot_date: date, fy: int) -> dict:
    """{symbol: (eps_avg, num_analysts_eps)} for (date, fy), eps not null."""
    rows = EstimateSnapshot.objects.filter(
        snapshot_date=snapshot_date, fiscal_year=fy, eps_avg__isnull=False
    ).values_list("symbol", "eps_avg", "num_analysts_eps")
    return {s.upper(): (eps, na) for s, eps, na in rows}


def _prev_present_symbols(prev_date: date) -> set:
    """지난주에 (어떤 FY로든) 스냅샷 행이 존재하는 심볼 집합."""
    return {
        s.upper()
        for s in EstimateSnapshot.objects.filter(snapshot_date=prev_date)
        .values_list("symbol", flat=True)
    }


def compute_anchor(anchor: date) -> dict:
    """
    anchor(이번주 금) WoW 분류 결과 산출 (쓰기 없음·순수 집계). fy = anchor.year+1(차기).

    반환: {"signals": [{symbol, fiscal_year, ...classify...}], "anchor": anchor, "fy": fy,
           "prev": prev_date}.
    """
    fy = anchor.year + 1
    prev = anchor - timedelta(days=WOW_LAG_DAYS)
    curr = _load_fy_rows(anchor, fy)
    prev_fy = _load_fy_rows(prev, fy)
    prev_any = _prev_present_symbols(prev)
    signals = []
    for sym in sorted(curr):
        c = classify_symbol(sym in prev_any, prev_fy.get(sym), curr[sym])
        c.update({"symbol": sym, "fiscal_year": fy})
        signals.append(c)
    return {"signals": signals, "anchor": anchor, "fy": fy, "prev": prev}


def aggregate_breadth(signals: list, anchor_symbols: list) -> list:
    """
    섹터(HeatEntity)별 breadth 집계. anchor_symbols = 이번주 스냅샷 모집단(sector_constituents 교집합용).

    반환: [{entity, gics, up, down, flat, valid_denom, excluded, breadth, score, status}].
    """
    by_sym = {s["symbol"]: s for s in signals}
    out = []
    for entity in HeatEntity.objects.filter(kind=HeatEntity.KIND_SECTOR).order_by("ref_id"):
        gics = HEAT_ENTITY_TO_SP500_SECTOR.get(entity.ref_id)
        if gics is None:
            continue
        syms = sector_constituents(gics, anchor_symbols)
        up = down = flat = excluded = 0
        for s in syms:
            sig = by_sym.get(s)
            if sig is None:
                continue
            if sig["excluded"]:
                excluded += 1
            elif sig["direction"] == 1:
                up += 1
            elif sig["direction"] == -1:
                down += 1
            else:
                flat += 1
        valid = up + down + flat
        if valid == 0:
            breadth, score, status = None, None, ThemeDemandScore.STATUS_NOT_COMPUTED
        else:
            breadth = (up - down) / valid
            score = round((breadth + 1) / 2 * 100)
            status = (
                ThemeDemandScore.STATUS_SUPPORTED if breadth >= BREADTH_TAU
                else ThemeDemandScore.STATUS_DETACHED if breadth <= -BREADTH_TAU
                else ThemeDemandScore.STATUS_NEUTRAL
            )
        out.append({
            "entity": entity, "gics": gics, "up": up, "down": down, "flat": flat,
            "valid_denom": valid, "excluded": excluded,
            "breadth": breadth, "score": score, "status": status,
        })
    return out


def store_for_anchor(anchor: date, dry_run: bool = True) -> dict:
    """
    anchor WoW 신호·breadth 계산 + (dry_run=False 시) SymbolDemandSignal·ThemeDemandScore INSERT.

    멱등 아님(append-only) — 이미 (symbol, anchor) 존재 시 IntegrityError 방지 위해 사전 스킵.
    반환 = 요약 집계 dict.
    """
    res = compute_anchor(anchor)
    signals = res["signals"]
    anchor_symbols = [s["symbol"] for s in signals]
    breadth_rows = aggregate_breadth(signals, anchor_symbols)

    summary = {
        "anchor": str(anchor), "fy": res["fy"], "prev": str(res["prev"]),
        "n_signals": len(signals),
        "up": sum(1 for s in signals if not s["excluded"] and s["direction"] == 1),
        "down": sum(1 for s in signals if not s["excluded"] and s["direction"] == -1),
        "flat": sum(1 for s in signals if not s["excluded"] and s["direction"] == 0),
        "excluded": sum(1 for s in signals if s["excluded"]),
        "exclude_reasons": {},
        "sectors": len(breadth_rows),
        "written_signals": 0, "written_scores": 0, "dry_run": dry_run,
    }
    for s in signals:
        if s["excluded"]:
            summary["exclude_reasons"][s["exclude_reason"]] = (
                summary["exclude_reasons"].get(s["exclude_reason"], 0) + 1
            )

    if dry_run:
        return summary

    # 사전 존재 스킵(append-only, 무-UPDATE): 이미 있는 anchor는 쓰지 않는다.
    if SymbolDemandSignal.objects.filter(anchor_date=anchor).exists():
        summary["skipped_existing"] = True
        return summary

    sig_objs = [
        SymbolDemandSignal(
            symbol=s["symbol"], anchor_date=anchor, fiscal_year=s["fiscal_year"],
            eps_prev=s["eps_prev"], eps_curr=s["eps_curr"],
            direction=s["direction"], num_analysts_prev=s["na_prev"],
            num_analysts_curr=s["na_curr"], excluded=s["excluded"],
            exclude_reason=s["exclude_reason"],
        )
        for s in signals
    ]
    SymbolDemandSignal.objects.bulk_create(sig_objs)
    summary["written_signals"] = len(sig_objs)

    score_objs = [
        ThemeDemandScore(
            theme=b["entity"], date=anchor, score=b["score"], status=b["status"],
            components={
                "breadth": b["breadth"], "up": b["up"], "down": b["down"],
                "flat": b["flat"], "valid_denom": b["valid_denom"],
                "excluded": b["excluded"], "gics_sector": b["gics"],
                "tau": BREADTH_TAU, "source": "dss_wow_v1",
            },
        )
        for b in breadth_rows
    ]
    ThemeDemandScore.objects.bulk_create(score_objs)
    summary["written_scores"] = len(score_objs)
    logger.info("DSS store_for_anchor %s: signals=%d scores=%d", anchor, len(sig_objs), len(score_objs))
    return summary
