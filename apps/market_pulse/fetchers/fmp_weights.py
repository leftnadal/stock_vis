"""Market Pulse v2 — FMP ETF holdings fetcher (PR-H)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings

from packages.shared.api_request.circuit_breaker import get_circuit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HoldingRow:
    symbol: str
    name: str
    weight: Decimal
    shares: int | None
    rank: int


FMP_BASE_URL = "https://financialmodelingprep.com"


def _request_etf_holder(
    etf_symbol: str, *, timeout: float = 10.0
) -> list[dict[str, Any]]:
    api_key = getattr(settings, "FMP_API_KEY", None)
    if not api_key:
        raise RuntimeError("FMP_API_KEY not configured")
    url = f"{FMP_BASE_URL}/stable/etf/holdings"
    resp = requests.get(
        url,
        params={"symbol": etf_symbol.upper(), "apikey": api_key},
        timeout=timeout,
    )
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, list):
        raise ValueError(
            f"unexpected FMP etf/holdings payload type: {type(payload).__name__}"
        )
    return payload


def fetch_holdings(etf_symbol: str) -> list[HoldingRow]:
    etf_symbol = etf_symbol.upper()
    cb = get_circuit("fmp_etf")
    raw = cb.call(_request_etf_holder, etf_symbol)

    rows: list[HoldingRow] = []
    for item in raw:
        sym = (item.get("asset") or item.get("symbol") or "").upper()
        if not sym:
            continue
        weight_pct = item.get("weightPercentage")
        if weight_pct is None:
            continue
        try:
            weight = Decimal(str(weight_pct)) / Decimal("100")
        except Exception:  # noqa: BLE001
            continue
        shares = item.get("sharesNumber")
        try:
            shares_int = int(shares) if shares is not None else None
        except (TypeError, ValueError):
            shares_int = None
        rows.append(
            HoldingRow(
                symbol=sym,
                name=str(item.get("name") or "")[:200],
                weight=weight,
                shares=shares_int,
                rank=0,
            )
        )

    rows.sort(key=lambda r: r.weight, reverse=True)
    return [
        HoldingRow(
            symbol=r.symbol, name=r.name, weight=r.weight, shares=r.shares, rank=i + 1
        )
        for i, r in enumerate(rows)
    ]
