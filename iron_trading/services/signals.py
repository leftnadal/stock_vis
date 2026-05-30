"""Iron Trading 후보 시그널 계산.

내부 모델을 직접 노출하지 않기 위해 OHLCV row tuple 기반으로만 계산한다.
입력은 (date, open, high, low, close, volume) 정렬된 list (오래된→최근).
모든 출력은 string으로 직렬화 (Decimal/float precision drift 방지).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import fmean
from typing import Sequence


@dataclass(frozen=True)
class OHLCVRow:
    date: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


def _q(value: Decimal | float | None, places: int = 4) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return f"{value:.{places}f}"
    return f"{Decimal(str(value)):.{places}f}"


def _safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _sma(rows: Sequence[OHLCVRow], window: int) -> Decimal | None:
    if len(rows) < window:
        return None
    closes = [float(r.close) for r in rows[-window:]]
    return Decimal(str(fmean(closes)))


def _momentum(rows: Sequence[OHLCVRow], window: int) -> Decimal | None:
    if len(rows) < window + 1:
        return None
    base = rows[-(window + 1)].close
    last = rows[-1].close
    return _safe_divide(last - base, base)


def _distance_pct(price: Decimal, anchor: Decimal | None) -> Decimal | None:
    if anchor is None or anchor == 0:
        return None
    return (price - anchor) / anchor


def _volume_ratio(rows: Sequence[OHLCVRow], window: int = 20) -> Decimal | None:
    if len(rows) < window + 1:
        return None
    recent = rows[-1].volume
    historical = [r.volume for r in rows[-(window + 1) : -1]]
    avg = fmean(historical)
    if avg == 0:
        return None
    return Decimal(str(recent / avg))


def _breakout_score(rows: Sequence[OHLCVRow], window: int = 20) -> Decimal | None:
    """최근 종가가 직전 window 봉의 최고가를 얼마나 돌파했는지.

    0.0 = 미돌파 또는 동률 미만. >0 = 돌파 비율. clip [0, 1].
    """
    if len(rows) < window + 1:
        return None
    last = rows[-1].close
    prior_high = max(r.high for r in rows[-(window + 1) : -1])
    if prior_high == 0:
        return None
    raw = (last - prior_high) / prior_high
    # clip 0~1 (0보다 작으면 미돌파)
    if raw < 0:
        raw = Decimal("0")
    elif raw > 1:
        raw = Decimal("1")
    return raw


def _pullback_quality(rows: Sequence[OHLCVRow], window: int = 20) -> Decimal | None:
    """추세 안에서 얕은 조정인지. 1에 가까울수록 얕은 풀백.

    score = 1 - (window 최고가 대비 현재 종가 하락폭). 마이너스이면 0으로 clip.
    """
    if len(rows) < window:
        return None
    window_high = max(r.high for r in rows[-window:])
    if window_high == 0:
        return None
    last = rows[-1].close
    drawdown = (window_high - last) / window_high
    score = Decimal("1") - drawdown
    if score < 0:
        score = Decimal("0")
    elif score > 1:
        score = Decimal("1")
    return score


def compute_candidate_signals(rows: Sequence[OHLCVRow]) -> dict:
    """후보 종목 signals 묶음 계산. 부족하면 None을 string으로 만들지 않고 None 유지.

    응답에서는 None 필드는 그대로 null로 직렬화됨.
    """
    if not rows:
        return {
            "momentum_20d": None,
            "momentum_60d": None,
            "sma20_distance_pct": None,
            "sma50_distance_pct": None,
            "volume_ratio_20d": None,
            "relative_strength_rank": None,
            "breakout_score": None,
            "pullback_quality": None,
        }

    last_close = rows[-1].close
    sma20 = _sma(rows, 20)
    sma50 = _sma(rows, 50)

    return {
        "momentum_20d": _q(_momentum(rows, 20)),
        "momentum_60d": _q(_momentum(rows, 60)),
        "sma20_distance_pct": _q(_distance_pct(last_close, sma20)),
        "sma50_distance_pct": _q(_distance_pct(last_close, sma50)),
        "volume_ratio_20d": _q(_volume_ratio(rows, 20), places=2),
        "relative_strength_rank": None,  # caller fills after cross-candidate ranking
        "breakout_score": _q(_breakout_score(rows, 20)),
        "pullback_quality": _q(_pullback_quality(rows, 20)),
    }


def assign_relative_strength_rank(candidates: list[dict]) -> None:
    """후보 list를 momentum_20d 기준 내림차순으로 rank 부여 (in-place).

    momentum_20d 없는 경우 가장 낮은 순위.
    """

    def _key(c):
        v = c["signals"].get("momentum_20d")
        return Decimal(v) if v is not None else Decimal("-9999")

    ordered = sorted(candidates, key=_key, reverse=True)
    for idx, c in enumerate(ordered, start=1):
        c["signals"]["relative_strength_rank"] = idx
