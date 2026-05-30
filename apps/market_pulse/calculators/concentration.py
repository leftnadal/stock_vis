"""Market Pulse v2 — Concentration Calculator (PR-H)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date as date_cls
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from django.utils import timezone as django_timezone

from apps.market_pulse.fetchers.fmp_weights import HoldingRow, fetch_holdings
from apps.market_pulse.models.snapshot import ConcentrationSnapshot

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConcentrationMetrics:
    top5_weight: Decimal
    top10_weight: Decimal
    hhi: Decimal
    top_holdings: list[dict[str, str | float]]


def _round(value: Decimal, places: int) -> Decimal:
    quant = Decimal(1).scaleb(-places)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def compute_metrics(holdings: Iterable[HoldingRow]) -> ConcentrationMetrics:
    sorted_h = sorted(holdings, key=lambda h: h.weight, reverse=True)
    total = sum((h.weight for h in sorted_h), Decimal("0"))
    if total > Decimal("1.005"):
        sorted_h = [
            HoldingRow(
                symbol=h.symbol,
                name=h.name,
                weight=h.weight / total,
                shares=h.shares,
                rank=h.rank,
            )
            for h in sorted_h
        ]
    top5 = sum((h.weight for h in sorted_h[:5]), Decimal("0"))
    top10 = sum((h.weight for h in sorted_h[:10]), Decimal("0"))
    if top10 > Decimal("1.0"):
        top10 = Decimal("1.0")
    if top5 > top10:
        top5 = top10
    hhi = sum((h.weight * h.weight for h in sorted_h), Decimal("0"))
    if hhi > Decimal("1.0"):
        hhi = Decimal("1.0")
    top_holdings = [
        {"symbol": h.symbol, "weight": float(_round(h.weight, 6))}
        for h in sorted_h[:10]
    ]
    return ConcentrationMetrics(
        top5_weight=_round(top5, 4),
        top10_weight=_round(top10, 4),
        hhi=_round(hhi, 6),
        top_holdings=top_holdings,
    )


def upsert_snapshot(
    metrics: ConcentrationMetrics,
    *,
    universe: str = "SPY",
    target_date: date_cls | None = None,
    snapshot_time=None,
) -> ConcentrationSnapshot:
    target_date = target_date or django_timezone.localdate()
    snapshot_time = snapshot_time or django_timezone.now()
    obj, _ = ConcentrationSnapshot.objects.update_or_create(
        date=target_date,
        universe=universe,
        defaults={
            "snapshot_time": snapshot_time,
            "top5_weight": metrics.top5_weight,
            "top10_weight": metrics.top10_weight,
            "hhi": metrics.hhi,
            "top_holdings": metrics.top_holdings,
            "is_finalized": False,
            "finalized_at": None,
        },
    )
    obj.full_clean(exclude=["snapshot_time", "finalized_at"])
    return obj


def calculate_for_etf(etf_symbol: str = "SPY") -> ConcentrationSnapshot:
    holdings = fetch_holdings(etf_symbol)
    if not holdings:
        raise RuntimeError(f"fetch_holdings returned empty list for {etf_symbol}")
    metrics = compute_metrics(holdings)
    return upsert_snapshot(metrics, universe=etf_symbol.upper())
