"""SFI-I3 Part 2 — 애널리스트 신호 Tier 1 채점 코어 (packages/shared, 순수 함수).

D-I3-1(파생 계산 계층·신규 테이블 없음) / D-I3-2(C안 5과목 2계층).
전 함수 = ORM 읽기 → 계산(DB 쓰기 0). 모든 채점은 as_of 파라미터를 받고 as_of 이하
데이터만 사용한다(재현 좌표 규약, 규칙 2). SCORING_VERSION 상수로 버전 박제.

Tier 1(판정): ① 방향 적중률 · ② 목표가 진행률 · ③ 횡단면 IC.
W3 정책(규칙 5): 만기 = capture로부터 h '거래일'. 종목 DailyPrice 거래일 시퀀스로 직접
인덱싱 → 무거래일 자동 회피. 계열 단절·상폐(만기 인접 큰 홀·데이터 조기 종료)는
unscoreable 반환(무리한 채점 금지). 유니버스 이탈 종목의 기존 예측도 채점 지속.

코호트 분리: pinned(spot_at_capture 존재 = post-pinning 정본) vs derived(pre-pinning →
capture일 DailyPrice.close 파생 + 캐비앗). 채점은 코호트별 분리 산출.
"""
from __future__ import annotations

import math
import statistics
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

SCORING_VERSION = 1
W3_ALLOWANCE_TRADING_DAYS = 5
# 거래일 → 달력일 근사 계수 (주 5거래일 / 7일).
_CAL_PER_TD = 7 / 5
# SPOT-DAY-CONVENTION 수리: 첫 T-관례(19:30 ET) 발화일(D-I3-5). 이 날(포함) 이후 pinned
# spot = T 종가 관례. 실측: 구 18:30 ET 스케줄 발화 = 08-06·08-07 각 9행 = 총 18행 혼합
# 코호트(T/T−1 혼재) — 소급 미수정, epoch 前으로 분리. 08-08~09 주말(dow1-5) 스킵 →
# beat 19:30 이동 후 첫 발화 = 2026-08-10(월).
CONVENTION_EPOCH = date(2026, 8, 10)


# ============================================================
# 자료구조
# ============================================================
@dataclass
class Prediction:
    symbol: str
    capture_date: date
    spot: Decimal
    target_consensus: Decimal
    cohort: str  # "pinned" | "derived"


# ============================================================
# 순수 통계 (scipy 무의존)
# ============================================================
def _sign(x) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def binom_p_two_sided(k: int, n: int, p: float = 0.5) -> Optional[float]:
    """이항검정 양측 p (H0: 성공확률 p). p=0.5 대칭 가정에서 작은 꼬리 2배."""
    if n == 0:
        return None
    p_le = sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k + 1))
    p_ge = sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))
    return min(1.0, 2 * min(p_le, p_ge))


def binom_p_greater(k: int, n: int, p: float = 0.5) -> Optional[float]:
    """단측 상방 p = P(X >= k) under Binom(n, p). (승격 트리거 '상방 유의'용)."""
    if n == 0:
        return None
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _avg_ranks(values: list[float]) -> list[float]:
    """동점 평균 순위(1-based)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for m in range(i, j + 1):
            ranks[order[m]] = avg
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    rx, ry = _avg_ranks(xs), _avg_ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def _median(xs: list[float]) -> Optional[float]:
    return statistics.median(xs) if xs else None


def _iqr(xs: list[float]) -> Optional[tuple]:
    if len(xs) < 2:
        return None
    q = statistics.quantiles(xs, n=4, method="inclusive")
    return (q[0], q[2])


# ============================================================
# W3 만기 해석
# ============================================================
def _index_at_or_before(dates: list, d: date) -> Optional[int]:
    lo, hi, res = 0, len(dates) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if dates[mid] <= d:
            res, lo = mid, mid + 1
        else:
            hi = mid - 1
    return res


def resolve_realized(bars: list, capture_date: date, h: int, as_of: date, splits=None):
    """capture로부터 h거래일 후 실현가 해석 (W3).

    반환 (status, realized_date, realized_close).
    status ∈ {"ok", "immature", "unscoreable:no_data", "unscoreable:no_spot",
              "unscoreable:series_break", "unscoreable:corporate_action"}.

    splits = 해당 종목 분할일 리스트(date). capture_date < split ≤ realized_date인 분할이
    있으면 원시(비조정) close가 오염되므로 unscoreable:corporate_action(I3-SPLIT-GUARD,
    D-SPLIT-1). splits=None/빈 리스트면 분기 미발동 → 기존 산출 IDENTICAL.
    """
    if not bars:
        return ("unscoreable:no_data", None, None)
    dates = [b[0] for b in bars]
    i0 = _index_at_or_before(dates, capture_date)
    if i0 is None:
        return ("unscoreable:no_spot", None, None)
    j = i0 + h
    if j > len(bars) - 1:
        # 만기 미도달 vs 계열 단절/상폐 구분: 충분한 달력시간 경과했는데 bar 부재 = 단절.
        elapsed_cal = (as_of - capture_date).days
        needed_cal = h * _CAL_PER_TD
        if elapsed_cal > needed_cal + 7:
            return ("unscoreable:series_break", None, None)
        return ("immature", None, None)
    # 만기 인접 거래일 간 홀이 허용창 초과 = 거래정지/단절.
    gap_days = (bars[j][0] - bars[j - 1][0]).days
    if gap_days > W3_ALLOWANCE_TRADING_DAYS * _CAL_PER_TD + 3:
        return ("unscoreable:series_break", None, None)
    realized_date = bars[j][0]
    # 예측~만기 구간(capture 배타 ~ realized 포함) 내 분할 = 원시 close 오염 → 채점 불가.
    if splits:
        for sd in splits:
            if capture_date < sd <= realized_date:
                return ("unscoreable:corporate_action", None, None)
    return ("ok", realized_date, bars[j][1])


def _earliest_maturity_est(predictions: list, h: int) -> Optional[str]:
    """표본 미도달 과목용 최초 만기 추정일(달력 근사)."""
    if not predictions:
        return None
    earliest = min(p.capture_date for p in predictions)
    return (earliest + timedelta(days=round(h * _CAL_PER_TD))).isoformat()


# ============================================================
# Tier 1 채점 과목 (순수 함수: predictions·bars → dict)
# ============================================================
def direction_hit_rate(
    predictions, bars_by_symbol, as_of, horizons=(21, 63), splits_by_symbol=None
) -> dict:
    """① 방향 적중률. 예측 방향 = sign(target − spot). 적중/표본/이항 p."""
    out = {}
    for h in horizons:
        hits = sample = 0
        unscoreable = []
        for p in predictions:
            if p.spot is None or p.target_consensus is None:
                continue
            pred_dir = _sign(p.target_consensus - p.spot)
            if pred_dir == 0:
                continue
            status, _, rclose = resolve_realized(
                bars_by_symbol.get(p.symbol, []), p.capture_date, h, as_of,
                (splits_by_symbol or {}).get(p.symbol, []),
            )
            if status == "ok":
                sample += 1
                if _sign(rclose - p.spot) == pred_dir:
                    hits += 1
            elif status.startswith("unscoreable"):
                unscoreable.append((p.symbol, p.capture_date.isoformat(), status))
        out[h] = {
            "hits": hits,
            "sample": sample,
            "hit_rate": (hits / sample) if sample else None,
            "p_value": binom_p_two_sided(hits, sample) if sample else None,
            "p_greater": binom_p_greater(hits, sample) if sample else None,
            "unscoreable": unscoreable,
            "earliest_maturity_est": _earliest_maturity_est(predictions, h)
            if sample == 0
            else None,
        }
    return out


def target_progress(
    predictions, bars_by_symbol, as_of, horizons=(63, 126, 252), splits_by_symbol=None
) -> dict:
    """② 목표가 진행률. 실현폭/예측폭 비율의 중앙값·IQR."""
    out = {}
    for h in horizons:
        ratios = []
        unscoreable = []
        for p in predictions:
            if p.spot is None or p.target_consensus is None:
                continue
            pred_move = p.target_consensus - p.spot
            if pred_move == 0:
                continue
            status, _, rclose = resolve_realized(
                bars_by_symbol.get(p.symbol, []), p.capture_date, h, as_of,
                (splits_by_symbol or {}).get(p.symbol, []),
            )
            if status == "ok":
                ratios.append(float((rclose - p.spot) / pred_move))
            elif status.startswith("unscoreable"):
                unscoreable.append((p.symbol, p.capture_date.isoformat(), status))
        out[h] = {
            "sample": len(ratios),
            "median_ratio": _median(ratios),
            "iqr": _iqr(ratios),
            "unscoreable": unscoreable,
            "earliest_maturity_est": _earliest_maturity_est(predictions, h)
            if not ratios
            else None,
        }
    return out


def cross_sectional_ic(
    predictions, bars_by_symbol, as_of, horizons=(21, 63), splits_by_symbol=None
) -> dict:
    """③ 횡단면 IC. 주간 코호트 upside% 순위 vs 실현수익 순위 Spearman."""
    weeks = defaultdict(list)
    for p in predictions:
        iso = p.capture_date.isocalendar()
        weeks[(iso[0], iso[1])].append(p)

    out = {}
    for h in horizons:
        per_week = []
        for wk, preds in sorted(weeks.items()):
            xs, ys = [], []
            for p in preds:
                if p.spot is None or p.spot == 0 or p.target_consensus is None:
                    continue
                status, _, rclose = resolve_realized(
                    bars_by_symbol.get(p.symbol, []), p.capture_date, h, as_of,
                    (splits_by_symbol or {}).get(p.symbol, []),
                )
                if status != "ok":
                    continue
                xs.append(float((p.target_consensus - p.spot) / p.spot))
                ys.append(float((rclose - p.spot) / p.spot))
            if len(xs) >= 2:
                per_week.append(
                    {"week": f"{wk[0]}-W{wk[1]:02d}", "n": len(xs), "ic": spearman(xs, ys)}
                )
        ics = [w["ic"] for w in per_week if w["ic"] is not None]
        out[h] = {
            "weeks": per_week,
            "cohorts_scored": len(per_week),
            "mean_ic": (sum(ics) / len(ics)) if ics else None,
            "caveat": "소표본(≈9종/주) — IC 추정 불안정, 방향 참고만",
            "earliest_maturity_est": _earliest_maturity_est(predictions, h)
            if not per_week
            else None,
        }
    return out


# ============================================================
# 입력 로더 + 집계
# ============================================================
def _git_head() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:  # noqa: BLE001 — 재현 좌표 best-effort
        return "unknown"


def load_scoring_inputs(as_of: date, symbols=None):
    """ORM 읽기 → (predictions, bars_by_symbol, splits_by_symbol, counts). as_of 이하만."""
    from packages.shared.stocks.models import (
        AnalystSignalSnapshot,
        DailyPrice,
        StockSplit,
    )

    qs = AnalystSignalSnapshot.objects.filter(captured_at__date__lte=as_of)
    if symbols:
        qs = qs.filter(symbol__in=[s.upper() for s in symbols])
    rows = list(
        qs.order_by("captured_at").values(
            "symbol", "captured_at", "target_consensus", "spot_at_capture"
        )
    )
    syms = sorted({r["symbol"] for r in rows})
    bars_by_symbol = {}
    splits_by_symbol = {}
    daily_rows = 0
    splits_rows = 0
    for s in syms:
        bars = list(
            DailyPrice.objects.filter(stock__symbol=s, date__lte=as_of)
            .order_by("date")
            .values_list("date", "close_price")
        )
        bars_by_symbol[s] = bars
        daily_rows += len(bars)
        split_dates = list(
            StockSplit.objects.filter(stock__symbol=s, date__lte=as_of)
            .order_by("date")
            .values_list("date", flat=True)
        )
        splits_by_symbol[s] = split_dates
        splits_rows += len(split_dates)

    predictions = []
    for r in rows:
        cap_date = r["captured_at"].date()
        if r["spot_at_capture"] is not None:
            spot, cohort = r["spot_at_capture"], "pinned"
        else:
            bars = bars_by_symbol.get(r["symbol"], [])
            i0 = _index_at_or_before([b[0] for b in bars], cap_date)
            if i0 is None:
                continue  # 파생 spot 불가 → 채점 대상 제외
            spot, cohort = bars[i0][1], "derived"
        predictions.append(
            Prediction(r["symbol"], cap_date, spot, r["target_consensus"], cohort)
        )
    counts = {"ass_rows": len(rows), "daily_price_rows": daily_rows}
    return predictions, bars_by_symbol, splits_by_symbol, counts


def reproduction_header(
    as_of: date,
    counts: dict,
    extra_counts: Optional[dict] = None,
    splits_input_rows: Optional[int] = None,
    splits_max_date: Optional[str] = None,
) -> dict:
    """재현 좌표 블록(규칙 2). AdvisoryRun 행수는 apps 계층(command)에서 extra로 주입.

    splits_input_rows·splits_max_date = 채점 시점 StockSplit 좌표(I3-SPLIT-GUARD, additive).
    """
    row_counts = dict(counts)
    if extra_counts:
        row_counts.update(extra_counts)
    return {
        "as_of": as_of.isoformat(),
        "scoring_version": SCORING_VERSION,
        "git_head": _git_head(),
        "input_rows": row_counts,
        "splits_input_rows": splits_input_rows,
        "splits_max_date": splits_max_date,
    }


def score_tier1(as_of: date, symbols=None) -> dict:
    """Tier 1 전과목 코호트별 산출 + 재현 헤더."""
    predictions, bars, splits, counts = load_scoring_inputs(as_of, symbols)
    splits_rows = sum(len(v) for v in splits.values())
    splits_max = max((d for v in splits.values() for d in v), default=None)
    result = {
        "header": reproduction_header(
            as_of,
            counts,
            splits_input_rows=splits_rows,
            splits_max_date=splits_max.isoformat() if splits_max else None,
        ),
        "cohorts": {},
    }
    for cohort in ("pinned", "derived"):
        preds_c = [p for p in predictions if p.cohort == cohort]
        entry = {
            "prediction_count": len(preds_c),
            "direction_hit_rate": direction_hit_rate(preds_c, bars, as_of, splits_by_symbol=splits),
            "target_progress": target_progress(preds_c, bars, as_of, splits_by_symbol=splits),
            "cross_sectional_ic": cross_sectional_ic(preds_c, bars, as_of, splits_by_symbol=splits),
        }
        if cohort == "pinned":
            # epoch 태깅(D-I3-5): 수리 前=혼합 관례(캐비앗) / 後=T 관례. 수식 무변경.
            entry["epoch_split"] = {
                "convention_epoch": CONVENTION_EPOCH.isoformat(),
                "pre_mixed": sum(1 for p in preds_c if p.capture_date < CONVENTION_EPOCH),
                "post_t": sum(1 for p in preds_c if p.capture_date >= CONVENTION_EPOCH),
            }
        result["cohorts"][cohort] = entry
    return result


# ============================================================
# D1-SCOREBOARD Part 1 — 성적판 read 표면 (compute-on-read, 순수 함수)
# ============================================================
# 성적판은 기존 집계(score_tier1)와 별개의 '신호별 상세' 뷰다. 위 Tier1 집계 함수를
# 무접촉(행위보존)으로 두고, 동일 순수 코어(load_scoring_inputs·resolve_realized·
# cross_sectional_ic·_sign)만 재사용해 신호 단위로 재조립한다. DB 쓰기 0.
# significance_threshold = 방향 적중 표본이 이 수 미만이면 '참고용'으로 표기(통계적
# 유의성 최소 표본 근사). 값은 계약 상수(디렉터 확정).
SCOREBOARD_SIGNIFICANCE_THRESHOLD = 60


def _direction_label(spot, target) -> Optional[str]:
    """예측 방향 라벨 = sign(target − spot). target/spot 부재 시 None(방향 판정 불가)."""
    if spot is None or target is None:
        return None
    return {1: "up", -1: "down", 0: "flat"}[_sign(target - spot)]


def _est_maturity_date(capture_date: date, h: int) -> date:
    """immature 신호의 만기 추정일(거래일 → 달력 근사, W3 정책과 동일 계수)."""
    return capture_date + timedelta(days=round(h * _CAL_PER_TD))


def _scorecard_signal(p: "Prediction", bars, splits, h: int, as_of: date) -> dict:
    """신호 1건(Prediction) → 성적판 표시 dict. resolve_realized 재사용."""
    status, rdate, rclose = resolve_realized(
        bars.get(p.symbol, []), p.capture_date, h, as_of, splits.get(p.symbol, [])
    )
    direction = _direction_label(p.spot, p.target_consensus)
    entry = {
        "direction": direction,
        "captured_at": p.capture_date.isoformat(),
        "spot_at_capture": float(p.spot) if p.spot is not None else None,
        "target_price": float(p.target_consensus) if p.target_consensus is not None else None,
        "maturity_date": None,
        "status": None,
        "realized": None,
        "unscoreable_reason": None,
        "pending_d_day": None,
        "cohort": p.cohort,  # additive — derived(파생 spot) 캐비앗 표기용
    }
    if status == "ok":
        entry["status"] = "scored"
        entry["maturity_date"] = rdate.isoformat()
        spot = p.spot
        ret_pct = float((rclose - spot) / spot * 100) if spot else None
        pred_move = (p.target_consensus - spot) if p.target_consensus is not None else None
        tp_pct = (
            float((rclose - spot) / pred_move * 100)
            if pred_move not in (None, 0)
            else None
        )
        if direction in ("up", "down"):
            pred_dir = 1 if direction == "up" else -1
            verdict = "hit" if _sign(rclose - spot) == pred_dir else "miss"
        else:
            verdict = "flat"  # 유지(방향 0)·방향불명 = 적중 판정 대상 아님(0-5 ①)
        entry["realized"] = {
            "close": float(rclose),
            "return_pct": round(ret_pct, 2) if ret_pct is not None else None,
            "target_progress_pct": round(tp_pct, 2) if tp_pct is not None else None,
            "verdict": verdict,
        }
    elif status == "immature":
        entry["status"] = "pending"
        est = _est_maturity_date(p.capture_date, h)
        entry["maturity_date"] = est.isoformat()
        entry["pending_d_day"] = (est - as_of).days
    else:  # unscoreable:*
        entry["status"] = "unscoreable"
        entry["unscoreable_reason"] = status.split(":", 1)[1] if ":" in status else status
    return entry


def build_scorecard(as_of: date, h: int, symbols=None) -> dict:
    """성적판 payload (compute-on-read). h거래일 지평.

    전역 read: user 스코프 없음(모든 AnalystSignalSnapshot 대상, symbols 필터는 테스트용).
    코호트(pinned/derived) 전건을 신호 단위로 표시하되 각 신호에 cohort 태그 부착.
    board 집계는 status=scored 신호에서 산출(방향 적중은 방향 up/down만 분모).
    computed_at은 뷰가 캐시 저장 직전 주입(순수성 유지 — 여기선 미포함).
    """
    predictions, bars, splits, counts = load_scoring_inputs(as_of, symbols)
    splits_rows = sum(len(v) for v in splits.values())
    splits_max = max((d for v in splits.values() for d in v), default=None)

    by_symbol: dict[str, list] = defaultdict(list)
    for p in predictions:
        by_symbol[p.symbol].append(p)

    board_hits = board_total = 0
    board_tp: list[float] = []
    total_scored = 0
    symbols_out = []
    for sym in sorted(by_symbol):
        s_scored = s_pending = s_unscoreable = 0
        s_hits = s_total = 0
        s_tp: list[float] = []
        sig_list = []
        for p in sorted(by_symbol[sym], key=lambda x: x.capture_date):
            entry = _scorecard_signal(p, bars, splits, h, as_of)
            sig_list.append(entry)
            if entry["status"] == "scored":
                s_scored += 1
                total_scored += 1
                r = entry["realized"]
                if r["verdict"] in ("hit", "miss"):
                    s_total += 1
                    board_total += 1
                    if r["verdict"] == "hit":
                        s_hits += 1
                        board_hits += 1
                if r["target_progress_pct"] is not None:
                    s_tp.append(r["target_progress_pct"])
                    board_tp.append(r["target_progress_pct"])
            elif entry["status"] == "pending":
                s_pending += 1
            else:
                s_unscoreable += 1
        symbols_out.append(
            {
                "symbol": sym,
                "counts": {"scored": s_scored, "pending": s_pending, "unscoreable": s_unscoreable},
                "hit": {"hits": s_hits, "total": s_total} if s_total else None,
                "avg_target_progress": round(sum(s_tp) / len(s_tp), 2) if s_tp else None,
                "signals": sig_list,
            }
        )

    # ③ 횡단면 IC = 공유 함수 재사용(주간 코호트 Spearman). 표본 미도달 시 null+사유.
    ic = cross_sectional_ic(predictions, bars, as_of, horizons=(h,), splits_by_symbol=splits)[h]
    if ic["cohorts_scored"] == 0:
        ic_value = None
        ic_reason = "표본 미도달" + (
            f" — 최초 만기 {ic['earliest_maturity_est']}" if ic["earliest_maturity_est"] else ""
        )
    else:
        ic_value = round(ic["mean_ic"], 4) if ic["mean_ic"] is not None else None
        ic_reason = None if ic_value is not None else ic["caveat"]

    return {
        "as_of": as_of.isoformat(),
        "horizon": h,
        "reproduction": reproduction_header(
            as_of,
            counts,
            splits_input_rows=splits_rows,
            splits_max_date=splits_max.isoformat() if splits_max else None,
        ),
        "board": {
            "sample_n": total_scored,
            "significance_threshold": SCOREBOARD_SIGNIFICANCE_THRESHOLD,
            "direction_hit": {"hits": board_hits, "total": board_total},
            "avg_target_progress": round(sum(board_tp) / len(board_tp), 2) if board_tp else None,
            "cross_sectional_ic": ic_value,
            "cross_sectional_ic_reason": ic_reason,  # additive — null 시 사유
        },
        "symbols": symbols_out,
    }
