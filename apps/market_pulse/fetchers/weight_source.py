"""
Constituent weight source seam (MP-LV-D1, 옵션 B).

소속: apps/market_pulse/fetchers (app 레이어 외부 데이터 fetcher).
역할: concentration 산출용 종목별 비중(HoldingRow)의 **단일 공급원 접점**.
  기본 = 시총 가중 근사(market_cap, FMP Starter 호환). holdings(ETF weightPercentage)
  경로는 프리미엄 엔드포인트(`/stable/etf/holdings`) 의존이라 휴면 보존.
전환점: `ACTIVE_WEIGHT_SOURCE` 1곳만 'holdings'로 바꾸면 미래 옵션 A(FMP 플랜
  업그레이드) 전환 완료 — holdings 경로(fmp_weights.fetch_holdings) 그대로 재활성.
의존: fetchers.fmp_weights(HoldingRow·fetch_holdings, 휴면), packages.shared.stocks
  (S&P500 심볼), packages.shared FMP `FMPClient`(per-symbol quote).
주의: market_cap 경로는 종목당 1 quote 호출(Starter 콤마배치 402 → 개별). ~500종목.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from apps.market_pulse.fetchers.fmp_weights import HoldingRow, fetch_holdings

logger = logging.getLogger(__name__)

# ── 산식 전환점 — 미래 옵션 A(holdings) 전환 = 이 상수만 변경 ──
ACTIVE_WEIGHT_SOURCE = "market_cap"  # "market_cap" | "holdings"

# 산식 전환이 데이터에 남도록 source별 universe 값 구분
UNIVERSE_BY_SOURCE = {"market_cap": "SP500_MCAP", "holdings": "SPY"}


def active_universe() -> str:
    return UNIVERSE_BY_SOURCE.get(ACTIVE_WEIGHT_SOURCE, "SP500_MCAP")


def _sp500_symbols() -> list[str]:
    """S&P500 유니버스 심볼 (DB Stock, 무료 — FMP 호출 0)."""
    from packages.shared.stocks.models import Stock

    return [s.upper() for s in Stock.objects.values_list("symbol", flat=True) if s]


def _to_cap(quote: dict | None) -> Decimal | None:
    if not quote:
        return None
    raw = quote.get("marketCap") or quote.get("mktCap")
    if raw in (None, 0, "0", ""):
        return None
    try:
        cap = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return cap if cap > 0 else None


def market_cap_weights() -> tuple[list[HoldingRow], dict]:
    """
    시총 가중 근사: weight_i = cap_i / Σcap. 결측 심볼은 제외 후 재정규화.

    Returns: (rank순 HoldingRow 리스트, meta dict{source,coverage,n_symbols,n_resolved,n_missing}).
    """
    from packages.shared.api_request.providers.fmp.market_pulse_client import FMPClient

    symbols = _sp500_symbols()
    client = FMPClient()
    caps: dict[str, Decimal] = {}
    missing: list[str] = []
    for sym in symbols:
        cap = _to_cap(client.get_quote(sym))
        if cap is None:
            missing.append(sym)
            continue
        caps[sym] = cap

    if not caps:
        raise RuntimeError("market_cap_weights: 시총 확보 0 — 비중 산출 불가")

    total = sum(caps.values(), Decimal("0"))
    rows = sorted(
        (
            HoldingRow(symbol=s, name="", weight=cap / total, shares=None, rank=0)
            for s, cap in caps.items()
        ),
        key=lambda r: r.weight,
        reverse=True,
    )
    ranked = [
        HoldingRow(symbol=r.symbol, name=r.name, weight=r.weight, shares=r.shares, rank=i + 1)
        for i, r in enumerate(rows)
    ]
    coverage = round(len(caps) / len(symbols), 4) if symbols else 0.0
    meta = {
        "source": "market_cap",
        "coverage": coverage,
        "n_symbols": len(symbols),
        "n_resolved": len(caps),
        "n_missing": len(missing),
    }
    logger.info(
        "market_cap_weights: coverage=%.3f resolved=%d/%d missing=%d",
        coverage,
        len(caps),
        len(symbols),
        len(missing),
    )
    return ranked, meta


def holdings_weights(etf_symbol: str = "SPY") -> tuple[list[HoldingRow], dict]:
    """휴면 경로 — ETF holdings(weightPercentage). 프리미엄 엔드포인트 의존."""
    rows = fetch_holdings(etf_symbol)
    return rows, {"source": "holdings", "coverage": 1.0, "etf": etf_symbol.upper()}


def get_constituent_weights() -> tuple[list[HoldingRow], dict]:
    """활성 공급원에서 종목별 비중을 가져온다 (concentration 산출 단일 진입점)."""
    if ACTIVE_WEIGHT_SOURCE == "holdings":
        return holdings_weights()
    return market_cap_weights()
