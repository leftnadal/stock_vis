"""Market Pulse v2 — News Aggregator (PR-B)."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from django.conf import settings
from django.utils import timezone as django_timezone

from apps.market_pulse.models.news import MarketPulseNews
from packages.shared.api_request.circuit_breaker import (
    CircuitBreakerError,
    get_circuit,
)

logger = logging.getLogger(__name__)

MAG7_SYMBOLS_FETCH = ("AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA")


@dataclass
class RawItem:
    source: str
    url: str
    title: str
    summary: str
    image_url: str
    publisher: str
    published_at: datetime
    explicit_symbols: list[str]


def _hash_url(url: str) -> str:
    norm = (url or "").strip().lower()
    if norm.endswith("/"):
        norm = norm[:-1]
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _ensure_aware(dt: datetime | None) -> datetime:
    if dt is None:
        return django_timezone.now()
    if django_timezone.is_naive(dt):
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _build_fmp_provider():
    api_key = getattr(settings, "FMP_API_KEY", None)
    if not api_key:
        return None
    try:
        from services.news.providers.fmp import FMPNewsProvider
        from packages.shared.api_request.providers.fmp.client import FMPClient
    except Exception as exc:  # noqa: BLE001
        logger.warning("FMP provider import failed: %s", exc)
        return None
    return FMPNewsProvider(FMPClient(api_key=api_key))


def _build_marketaux_provider():
    api_key = getattr(settings, "MARKETAUX_API_KEY", "") or ""
    if not api_key:
        return None
    try:
        from services.news.providers.marketaux import MarketauxNewsProvider
    except Exception as exc:  # noqa: BLE001
        logger.warning("Marketaux provider import failed: %s", exc)
        return None
    return MarketauxNewsProvider(api_key=api_key, request_delay=0)


def _to_raw_item(article, source: str) -> RawItem | None:
    if not article or not article.url or not article.title:
        return None
    explicit = [
        e.get("symbol", "").upper() for e in (article.entities or []) if e.get("symbol")
    ]
    return RawItem(
        source=source,
        url=article.url,
        title=article.title.strip(),
        summary=(article.summary or "").strip(),
        image_url=article.image_url or "",
        publisher=article.source or "",
        published_at=_ensure_aware(article.published_at),
        explicit_symbols=list(dict.fromkeys(explicit)),
    )


def fetch_all(
    *,
    fmp_general_limit: int = 50,
    fmp_stock_limit_per_symbol: int = 5,
    marketaux_limit: int = 20,
    mag7_symbols: tuple[str, ...] = MAG7_SYMBOLS_FETCH,
    lookback_hours: int = 24,
) -> dict[str, Any]:
    fmp = _build_fmp_provider()
    marketaux = _build_marketaux_provider()
    cb_fmp = get_circuit("fmp_news")
    cb_mx = get_circuit("marketaux")

    by_hash: dict[str, RawItem] = {}
    duplicates = 0
    stats = {
        "fmp_general": {"fetched": 0, "error": None},
        "fmp_stock": {"fetched": 0, "error": None},
        "marketaux": {"fetched": 0, "error": None},
        "duplicates": 0,
    }

    def _add(item: RawItem | None) -> None:
        nonlocal duplicates
        if item is None:
            return
        h = _hash_url(item.url)
        if h in by_hash:
            duplicates += 1
            return
        by_hash[h] = item

    if fmp is not None:
        try:
            articles = cb_fmp.call(fmp.fetch_market_news, "general", fmp_general_limit)
            stats["fmp_general"]["fetched"] = len(articles)
            for art in articles:
                _add(_to_raw_item(art, MarketPulseNews.Source.FMP_GENERAL))
        except CircuitBreakerError as exc:
            stats["fmp_general"]["error"] = f"circuit_open:{exc}"
        except Exception as exc:  # noqa: BLE001
            stats["fmp_general"]["error"] = str(exc)
    else:
        stats["fmp_general"]["error"] = "fmp_provider_unavailable"

    if fmp is not None:
        to_date = django_timezone.now().replace(tzinfo=None)
        from_date = to_date - timedelta(hours=lookback_hours)
        total_stock = 0
        last_err: str | None = None
        for sym in mag7_symbols:
            try:
                articles = cb_fmp.call(
                    fmp.fetch_company_news,
                    sym,
                    from_date,
                    to_date,
                    fmp_stock_limit_per_symbol,
                )
                total_stock += len(articles)
                for art in articles:
                    _add(_to_raw_item(art, MarketPulseNews.Source.FMP_STOCK))
            except CircuitBreakerError as exc:
                last_err = f"circuit_open:{exc}"
                break
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
                continue
        stats["fmp_stock"]["fetched"] = total_stock
        stats["fmp_stock"]["error"] = last_err

    if marketaux is not None:
        try:
            articles = cb_mx.call(
                marketaux.fetch_market_news, "general", marketaux_limit
            )
            stats["marketaux"]["fetched"] = len(articles)
            for art in articles:
                _add(_to_raw_item(art, MarketPulseNews.Source.MARKETAUX))
        except CircuitBreakerError as exc:
            stats["marketaux"]["error"] = f"circuit_open:{exc}"
        except Exception as exc:  # noqa: BLE001
            stats["marketaux"]["error"] = str(exc)
    else:
        stats["marketaux"]["error"] = "marketaux_provider_unavailable"

    stats["duplicates"] = duplicates
    items = sorted(by_hash.values(), key=lambda x: x.published_at, reverse=True)
    return {"items": items, "stats": stats}


def url_hash(url: str) -> str:
    return _hash_url(url)
