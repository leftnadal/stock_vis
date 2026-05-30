"""Market Pulse v2 — Sector Flow Calculator (PR-G)."""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from datetime import date as date_cls
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from django.utils import timezone as django_timezone

from macro.models.indicators import MarketIndex, MarketIndexPrice
from marketpulse.models.snapshot import SectorFlowSnapshot

logger = logging.getLogger(__name__)

# PR-A1 (2026-04-29): GICS 11-sector 확장. 기존 'SECTOR' 단일 → GICS 11종 enum.
GICS_SECTOR_GROUPS = (
    "FINANCIALS",
    "TECH",
    "HEALTHCARE",
    "CONSUMER_DISC",
    "CONSUMER_STAPLES",
    "ENERGY",
    "INDUSTRIALS",
    "MATERIALS",
    "UTILITIES",
    "REAL_ESTATE",
    "COMMUNICATION",
)
BENCHMARK_SYMBOL = "SPY"


@dataclass
class SectorMetrics:
    market_index: MarketIndex
    rel_strength: Decimal
    momentum_1d: Decimal
    momentum_5d: Decimal
    momentum_20d: Decimal
    flow_proxy: Decimal
    cross_dispersion: Decimal
    rotation_index: Decimal
    rank_in_universe: int


def _round(value: Decimal, places: int) -> Decimal:
    quant = Decimal(1).scaleb(-places)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def _pct_change(end: Decimal, start: Decimal) -> Decimal:
    if start is None or start == 0 or end is None:
        return Decimal("0")
    return (end - start) / start * Decimal("100")


def _load_close_series(
    symbol: str,
    *,
    target_date: date_cls,
    days: int = 25,
) -> list[tuple[date_cls, Decimal, int | None]]:
    idx = MarketIndex.objects.filter(symbol=symbol).first()
    if idx is None:
        return []
    rows = list(
        MarketIndexPrice.objects.filter(
            index=idx,
            date__lte=target_date,
            date__gte=target_date - timedelta(days=days * 3),
        )
        .order_by("-date")
        .values_list("date", "close", "volume")[:days]
    )
    rows.reverse()
    return [(d, c, v) for d, c, v in rows if c is not None]


def _momentum(series, n: int) -> Decimal:
    if len(series) <= n:
        return Decimal("0")
    end = series[-1][1]
    start = series[-1 - n][1]
    return _pct_change(end, start)


def _flow_proxy(series) -> Decimal:
    if not series:
        return Decimal("0")
    _, close, volume = series[-1]
    if volume is None:
        return Decimal("0")
    return Decimal(close) * Decimal(volume)


def compute_sector_block(
    *,
    target_date: date_cls,
    sector_indices: Iterable[MarketIndex],
    benchmark_index: MarketIndex,
) -> list[SectorMetrics]:
    bench_series = _load_close_series(benchmark_index.symbol, target_date=target_date)
    bench_return_1d = _momentum(bench_series, 1)

    raw = []
    rel_strengths: list[Decimal] = []
    for sector in sector_indices:
        s_series = _load_close_series(sector.symbol, target_date=target_date)
        m1 = _momentum(s_series, 1)
        m5 = _momentum(s_series, 5)
        m20 = _momentum(s_series, 20)
        flow = _flow_proxy(s_series)
        rel = m1 - bench_return_1d
        rel_strengths.append(rel)
        raw.append((sector, rel, m1, m5, m20, flow))

    if len(rel_strengths) >= 2:
        floats = [float(x) for x in rel_strengths]
        dispersion = Decimal(str(statistics.pstdev(floats)))
        median = Decimal(str(statistics.median(floats)))
        max_val = max(rel_strengths)
        rotation = dispersion + abs(max_val - median)
    else:
        dispersion = Decimal("0")
        rotation = Decimal("0")

    sorted_by_rel = sorted(enumerate(raw), key=lambda kv: kv[1][1], reverse=True)
    ranks = {orig: i + 1 for i, (orig, _) in enumerate(sorted_by_rel)}

    out: list[SectorMetrics] = []
    for i, (sector, rel, m1, m5, m20, flow) in enumerate(raw):
        out.append(
            SectorMetrics(
                market_index=sector,
                rel_strength=_round(rel, 6),
                momentum_1d=_round(m1, 6),
                momentum_5d=_round(m5, 6),
                momentum_20d=_round(m20, 6),
                flow_proxy=_round(flow, 2),
                cross_dispersion=_round(dispersion, 6),
                rotation_index=_round(rotation, 6),
                rank_in_universe=ranks[i],
            )
        )
    return out


def upsert_snapshots(
    metrics_list: list[SectorMetrics],
    *,
    target_date: date_cls,
    snapshot_time=None,
) -> list[SectorFlowSnapshot]:
    snapshot_time = snapshot_time or django_timezone.now()
    out = []
    for m in metrics_list:
        obj, _ = SectorFlowSnapshot.objects.update_or_create(
            date=target_date,
            market_index=m.market_index,
            defaults={
                "snapshot_time": snapshot_time,
                "rel_strength": m.rel_strength,
                "momentum_1d": m.momentum_1d,
                "momentum_5d": m.momentum_5d,
                "momentum_20d": m.momentum_20d,
                "flow_proxy": m.flow_proxy,
                "cross_dispersion": m.cross_dispersion,
                "rotation_index": m.rotation_index,
                "rank_in_universe": m.rank_in_universe,
                "is_finalized": False,
                "finalized_at": None,
            },
        )
        out.append(obj)
    return out


def calculate(target_date: date_cls | None = None) -> list[SectorFlowSnapshot]:
    target_date = target_date or django_timezone.localdate()
    bench = MarketIndex.objects.filter(symbol=BENCHMARK_SYMBOL).first()
    if bench is None:
        raise RuntimeError(f"benchmark {BENCHMARK_SYMBOL} MarketIndex not found")
    sectors = list(
        MarketIndex.objects.filter(sector_group__in=GICS_SECTOR_GROUPS).order_by(
            "symbol"
        )
    )
    if not sectors:
        raise RuntimeError("GICS sector MarketIndex empty")
    metrics_list = compute_sector_block(
        target_date=target_date,
        sector_indices=sectors,
        benchmark_index=bench,
    )
    return upsert_snapshots(metrics_list, target_date=target_date)
