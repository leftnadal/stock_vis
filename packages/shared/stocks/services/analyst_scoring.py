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


def resolve_realized(bars: list, capture_date: date, h: int, as_of: date):
    """capture로부터 h거래일 후 실현가 해석 (W3).

    반환 (status, realized_date, realized_close).
    status ∈ {"ok", "immature", "unscoreable:no_data", "unscoreable:no_spot",
              "unscoreable:series_break"}.
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
    return ("ok", bars[j][0], bars[j][1])


def _earliest_maturity_est(predictions: list, h: int) -> Optional[str]:
    """표본 미도달 과목용 최초 만기 추정일(달력 근사)."""
    if not predictions:
        return None
    earliest = min(p.capture_date for p in predictions)
    return (earliest + timedelta(days=round(h * _CAL_PER_TD))).isoformat()


# ============================================================
# Tier 1 채점 과목 (순수 함수: predictions·bars → dict)
# ============================================================
def direction_hit_rate(predictions, bars_by_symbol, as_of, horizons=(21, 63)) -> dict:
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
                bars_by_symbol.get(p.symbol, []), p.capture_date, h, as_of
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


def target_progress(predictions, bars_by_symbol, as_of, horizons=(63, 126, 252)) -> dict:
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
                bars_by_symbol.get(p.symbol, []), p.capture_date, h, as_of
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


def cross_sectional_ic(predictions, bars_by_symbol, as_of, horizons=(21, 63)) -> dict:
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
                    bars_by_symbol.get(p.symbol, []), p.capture_date, h, as_of
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
    """ORM 읽기 → (predictions, bars_by_symbol, counts). as_of 이하만."""
    from packages.shared.stocks.models import AnalystSignalSnapshot, DailyPrice

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
    daily_rows = 0
    for s in syms:
        bars = list(
            DailyPrice.objects.filter(stock__symbol=s, date__lte=as_of)
            .order_by("date")
            .values_list("date", "close_price")
        )
        bars_by_symbol[s] = bars
        daily_rows += len(bars)

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
    return predictions, bars_by_symbol, counts


def reproduction_header(as_of: date, counts: dict, extra_counts: Optional[dict] = None) -> dict:
    """재현 좌표 블록(규칙 2). AdvisoryRun 행수는 apps 계층(command)에서 extra로 주입."""
    row_counts = dict(counts)
    if extra_counts:
        row_counts.update(extra_counts)
    return {
        "as_of": as_of.isoformat(),
        "scoring_version": SCORING_VERSION,
        "git_head": _git_head(),
        "input_rows": row_counts,
    }


def score_tier1(as_of: date, symbols=None) -> dict:
    """Tier 1 전과목 코호트별 산출 + 재현 헤더."""
    predictions, bars, counts = load_scoring_inputs(as_of, symbols)
    result = {"header": reproduction_header(as_of, counts), "cohorts": {}}
    for cohort in ("pinned", "derived"):
        preds_c = [p for p in predictions if p.cohort == cohort]
        result["cohorts"][cohort] = {
            "prediction_count": len(preds_c),
            "direction_hit_rate": direction_hit_rate(preds_c, bars, as_of),
            "target_progress": target_progress(preds_c, bars, as_of),
            "cross_sectional_ic": cross_sectional_ic(preds_c, bars, as_of),
        }
    return result
