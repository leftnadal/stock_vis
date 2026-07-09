"""
C6 상관 응집 · C7 거래대금 — fetch 배선 (TH-8) — 설계 앵커 §2 C6·C7 · §3-1(3년 σ).

C6 = 구성종목 pairwise rolling Pearson(60일) 평균의 3년 z (가격, Layer C 재활용).
C7 = 테마 합산 거래대금(Σ close×volume) 20일의 3년 z.

원천 = 구성종목 DailyPrice(공유 stocks 도메인, **읽기 전용** — chainsight 는 쓰지 않음).
순수함수 heat_components.c6_correlation / c7_dollar_volume 재사용(정본 불변).

★ 3년 커버 가드: 구성종목 가격 이력이 3년의 COVERAGE_RATIO 미만이면 c*_insufficient_history
결측(§3-5). 3년 σ 정본을 짧은 창으로 근사(우회)하지 않는다 — DailyPrice 3년 백필(stocks
도메인)이 데이터 게이트. 백필 도달 시 자동 활성(C4 콜드스타트와 동형 "배선 + 데이터 대기").
"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional, Sequence

from apps.chain_sight.services.heat_components import (
    DEFAULT_MIN_N,
    c6_correlation,
    c7_dollar_volume,
    make_component,
)

logger = logging.getLogger(__name__)

CORR_WINDOW = 60      # §2 C6 "pairwise rolling Pearson(60일)"
DV_WINDOW = 20        # §2 C7 "20일"
COVERAGE_RATIO = 0.8  # 3년 lookback 의 80% 이상 커버해야 3년 σ 정본 (미달 = insufficient_history)


def _load_prices(syms: Sequence[str], as_of: date, lookback_days: int, pad_days: int) -> dict:
    """구성종목 DailyPrice(읽기) → {symbol: {date: (close, volume)}}."""
    from packages.shared.stocks.models import DailyPrice

    earliest = as_of - timedelta(days=lookback_days + pad_days)
    rows = DailyPrice.objects.filter(
        stock__symbol__in=list(syms), date__gte=earliest, date__lte=as_of
    ).values("stock__symbol", "date", "close_price", "volume")
    by_sym: dict[str, dict] = defaultdict(dict)
    for r in rows:
        by_sym[r["stock__symbol"]][r["date"]] = (r["close_price"], r["volume"])
    return by_sym


# ────────────────────────────── C7 거래대금 ──────────────────────────────
def c7_dollar_volume_from_db(
    sector_symbols: Sequence[str],
    as_of: date,
    lookback_days: int = 365 * 3,
    window: int = DV_WINDOW,
    step_days: int = 7,
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """섹터 합산 거래대금 20일의 3년 z (§2 C7). c7_dollar_volume 재사용."""
    syms = [s.upper() for s in sector_symbols]
    if not syms:
        return make_component(None, raw=None, missing_reason="c7_no_symbols")

    by_sym = _load_prices(syms, as_of, lookback_days, window * 3)
    dv_by_date: dict[date, float] = defaultdict(float)
    for _s, m in by_sym.items():
        for d, (c, v) in m.items():
            if c is not None and v is not None:
                dv_by_date[d] += float(c) * float(v)
    dates = sorted(dv_by_date)
    if not dates:
        return make_component(None, raw=None, missing_reason="c7_no_data")
    if dates[0] > as_of - timedelta(days=int(lookback_days * COVERAGE_RATIO)):
        return make_component(None, raw=None, missing_reason="c7_insufficient_history")

    def _ma_at(anchor: date) -> Optional[float]:
        trailing = [d for d in dates if d <= anchor][-window:]
        if len(trailing) < window:
            return None
        return sum(dv_by_date[d] for d in trailing)

    history: list[Optional[float]] = []
    cursor = as_of - timedelta(days=lookback_days)
    while cursor < as_of:
        history.append(_ma_at(cursor))
        cursor += timedelta(days=step_days)
    current = _ma_at(as_of)
    if current is None:
        return make_component(None, raw=None, missing_reason="c7_no_recent_window")
    return c7_dollar_volume(current, history, min_n=min_n)


# ────────────────────────────── C6 상관 응집 ──────────────────────────────
def _returns(seq: list) -> list[float]:
    """(date, close) 정렬 리스트 → 단순 수익률."""
    out = []
    for i in range(1, len(seq)):
        p0, p1 = seq[i - 1][1], seq[i][1]
        if p0 and p1:
            out.append(float(p1) / float(p0) - 1)
    return out


def _pearson(a: list, b: list) -> Optional[float]:
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[-n:], b[-n:]
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return None
    return cov / ((va * vb) ** 0.5)


def c6_correlation_from_db(
    sector_symbols: Sequence[str],
    as_of: date,
    lookback_days: int = 365 * 3,
    corr_window: int = CORR_WINDOW,
    step_days: int = 7,
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """구성종목 pairwise Pearson(60일) 평균의 3년 z (§2 C6). c6_correlation 재사용."""
    syms = [s.upper() for s in sector_symbols]
    if len(syms) < 2:
        return make_component(None, raw=None, missing_reason="c6_no_pairs")

    by_sym = _load_prices(syms, as_of, lookback_days, corr_window * 3)
    closes = {
        s: sorted((d, c) for d, (c, v) in m.items() if c is not None)
        for s, m in by_sym.items()
    }
    all_dates = sorted({d for s in closes for d, _ in closes[s]})
    if not all_dates:
        return make_component(None, raw=None, missing_reason="c6_no_data")
    if all_dates[0] > as_of - timedelta(days=int(lookback_days * COVERAGE_RATIO)):
        return make_component(None, raw=None, missing_reason="c6_insufficient_history")

    def _avg_corr_at(anchor: date) -> Optional[float]:
        rets: dict[str, list] = {}
        for s, seq in closes.items():
            w = [(d, c) for d, c in seq if d <= anchor][-corr_window:]
            if len(w) >= corr_window:
                rets[s] = _returns(w)
        names = list(rets)
        if len(names) < 2:
            return None
        corrs = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                p = _pearson(rets[names[i]], rets[names[j]])
                if p is not None:
                    corrs.append(p)
        return sum(corrs) / len(corrs) if corrs else None

    history: list[Optional[float]] = []
    cursor = as_of - timedelta(days=lookback_days)
    while cursor < as_of:
        history.append(_avg_corr_at(cursor))
        cursor += timedelta(days=step_days)
    current = _avg_corr_at(as_of)
    if current is None:
        return make_component(None, raw=None, missing_reason="c6_no_recent_window")
    return c6_correlation(current, history, min_n=min_n)
