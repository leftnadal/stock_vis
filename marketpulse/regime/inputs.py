"""Market Pulse v2 — Regime Inputs Loader (PR-C)."""
from __future__ import annotations

import logging
import statistics
from dataclasses import asdict, dataclass, field
from datetime import date as date_cls, timedelta
from decimal import Decimal
from typing import Any

from django.utils import timezone as django_timezone

from macro.models.indicators import (
    EconomicIndicator,
    IndicatorValue,
    MarketIndex,
    MarketIndexPrice,
)

logger = logging.getLogger(__name__)

INDICATOR_CODE_MAP: dict[str, str] = {
    'nfci': 'NFCI',
    'nfci_credit': 'NFCICREDIT',
    'nfci_leverage': 'NFCILEVERAGE',
    'nfci_risk': 'NFCIRISK',
    'hy_oas_pct': 'BAMLH0A0HYM2',
    'hy_ccc_oas_pct': 'BAMLH0A3HYC',
    't10y2y_pct': 'T10Y2Y',
    't10y3m_pct': 'T10Y3M',
    'vix': 'VIXCLS',
    'vix3m': 'VIX3M',
    'move': 'MOVE',
}

PRICE_KEYS = ('return_1d_pct', 'vol_20d_pct', 'drawdown_pct')
ALL_INPUT_KEYS = PRICE_KEYS + tuple(INDICATOR_CODE_MAP.keys())


@dataclass
class RegimeInputs:
    return_1d_pct: float | None = None
    vol_20d_pct: float | None = None
    drawdown_pct: float | None = None
    nfci: float | None = None
    nfci_credit: float | None = None
    nfci_leverage: float | None = None
    nfci_risk: float | None = None
    hy_oas_pct: float | None = None
    hy_ccc_oas_pct: float | None = None
    t10y2y_pct: float | None = None
    t10y3m_pct: float | None = None
    vix: float | None = None
    vix3m: float | None = None
    move: float | None = None

    fetched_at: str = ''
    sources: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def coverage_ratio(self) -> float:
        present = sum(1 for k in ALL_INPUT_KEYS if getattr(self, k) is not None)
        return present / len(ALL_INPUT_KEYS)

    def missing_keys(self) -> list[str]:
        return [k for k in ALL_INPUT_KEYS if getattr(self, k) is None]


def _latest_indicator_value(code: str, *, max_age_days: int = 14) -> float | None:
    ind = EconomicIndicator.objects.filter(code=code).first()
    if ind is None:
        return None
    today = django_timezone.localdate()
    val = (
        IndicatorValue.objects
        .filter(indicator=ind, date__gte=today - timedelta(days=max_age_days * 2))
        .order_by('-date')
        .first()
    )
    if val is None:
        return None
    if (today - val.date).days > max_age_days:
        return None
    return float(val.value)


def _spy_price_series(*, days: int = 260) -> list[tuple[date_cls, Decimal]]:
    spy = MarketIndex.objects.filter(symbol='SPY').first()
    if spy is None:
        return []
    today = django_timezone.localdate()
    rows = list(
        MarketIndexPrice.objects
        .filter(index=spy, date__gte=today - timedelta(days=days * 2))
        .order_by('-date')
        .values_list('date', 'close')[:days]
    )
    rows.reverse()
    return [(d, c) for d, c in rows if c is not None]


def _compute_price_block(series: list[tuple[date_cls, Decimal]]) -> dict[str, float | None]:
    out: dict[str, float | None] = {
        'return_1d_pct': None, 'vol_20d_pct': None, 'drawdown_pct': None,
    }
    if len(series) < 2:
        return out
    closes = [float(c) for _, c in series]
    if closes[-2] > 0:
        out['return_1d_pct'] = (closes[-1] - closes[-2]) / closes[-2] * 100.0
    if len(closes) >= 21:
        window = closes[-21:]
        daily_returns = [
            (window[i] - window[i - 1]) / window[i - 1] * 100.0
            for i in range(1, len(window))
            if window[i - 1] > 0
        ]
        if len(daily_returns) >= 5:
            out['vol_20d_pct'] = statistics.pstdev(daily_returns)
    window_252 = closes[-252:] if len(closes) >= 252 else closes
    peak = max(window_252) if window_252 else None
    if peak and peak > 0:
        out['drawdown_pct'] = (closes[-1] - peak) / peak * 100.0
    return out


def load_inputs() -> RegimeInputs:
    inputs = RegimeInputs()
    sources: dict[str, str] = {}

    series = _spy_price_series()
    if not series:
        for k in PRICE_KEYS:
            sources[k] = 'MISSING'
    else:
        block = _compute_price_block(series)
        for k, v in block.items():
            setattr(inputs, k, v)
            sources[k] = 'OK' if v is not None else 'STALE'

    for key, code in INDICATOR_CODE_MAP.items():
        v = _latest_indicator_value(code)
        if v is not None:
            setattr(inputs, key, v)
            sources[key] = 'OK'
        else:
            sources[key] = 'MISSING'

    inputs.sources = sources
    inputs.fetched_at = django_timezone.now().isoformat()
    return inputs
