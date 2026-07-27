"""
ETF NAV·시장가 수집 서비스 (P2a-1).

FMP 단일 provider: nav ← /stable/etf/info, price ← /stable/quote.
정본 거래일 = quote timestamp의 ET 거래일. nav updatedAt이 정본 거래일과
ETF_NAV_MAX_LAG_DAYS 영업일을 초과해 괴리하면 해당 관측을 skip + 로그한다
(자가 보정 금지 — 보고 후 대기 대상).

upsert 규약 = MacroSeriesHistory와 동형(insert-only + revise-on-change).
삭제 없음(§10 영구 누적). 디스카운트 신호값은 여기 미적재(compute-on-read).
"""
import logging
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import numpy as np
from django.utils import timezone

from ..constants import ETF_NAV_MAX_LAG_DAYS, ETF_SYMBOLS
from ..models import EtfNavHistory

logger = logging.getLogger(__name__)

_QUANT = Decimal("0.0001")
_ET = ZoneInfo("America/New_York")


def _to_decimal(raw) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(str(raw)).quantize(_QUANT)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _canonical_trading_day(quote: dict) -> date | None:
    """정본 거래일 = quote timestamp(epoch)의 ET 거래일."""
    ts = quote.get("timestamp")
    if ts is None:
        return None
    try:
        dt = datetime.fromtimestamp(int(ts), tz=dt_timezone.utc).astimezone(_ET)
    except (TypeError, ValueError, OSError, OverflowError):
        return None
    return dt.date()


def _nav_updated_date(info: dict) -> date | None:
    """etf/info updatedAt(ISO8601)의 ET 날짜."""
    raw = info.get("updatedAt")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(_ET).date()


def _business_day_lag(a: date, b: date) -> int:
    """a↔b 영업일 거리(절대값). numpy busday_count 사용(반열림 구간 보정 abs)."""
    return abs(int(np.busday_count(a, b)))


def upsert_etf_nav(symbol: str, trading_day: date, nav: Decimal, price: Decimal) -> str:
    """
    (symbol, trading_day) 행 upsert. 반환: 'created' | 'updated' | 'skipped'.

    최초 → insert(ingested_at=now). nav·price 변동 → revise(revised_at=now,
    ingested_at 유지). 동일 → no-op. 삭제 없음.
    """
    existing = EtfNavHistory.objects.filter(symbol=symbol, date=trading_day).first()
    if existing is None:
        EtfNavHistory.objects.create(
            symbol=symbol, date=trading_day, nav=nav, price=price
        )
        return "created"
    if existing.nav != nav or existing.price != price:
        existing.nav = nav
        existing.price = price
        existing.revised_at = timezone.now()
        existing.save(update_fields=["nav", "price", "revised_at"])
        return "updated"
    return "skipped"


def resolve_and_upsert_one(client, symbol: str) -> dict:
    """단일 ETF: quote+etf/info 조회 → 정본 거래일 resolve → 정합 시 upsert."""
    quote = client.get_quote(symbol)
    info = client.get_etf_info(symbol)

    trading_day = _canonical_trading_day(quote)
    price = _to_decimal(quote.get("price"))
    nav = _to_decimal(info.get("nav"))
    nav_date = _nav_updated_date(info)

    if trading_day is None or price is None or nav is None or price <= 0 or nav <= 0:
        logger.warning(
            "etf_nav skip(결측/이상): symbol=%s trading_day=%s price=%s nav=%s",
            symbol, trading_day, price, nav,
        )
        return {"symbol": symbol, "result": "skipped", "reason": "missing_or_invalid"}

    if nav_date is None:
        logger.warning("etf_nav skip(nav updatedAt 파싱 실패): symbol=%s", symbol)
        return {"symbol": symbol, "result": "skipped", "reason": "nav_date_unparseable"}

    lag = _business_day_lag(trading_day, nav_date)
    if lag > ETF_NAV_MAX_LAG_DAYS:
        logger.warning(
            "etf_nav skip(거래일 괴리 %d영업일 > %d): symbol=%s 정본거래일=%s "
            "nav_updated=%s — 자가 보정 없이 skip(상신 대상)",
            lag, ETF_NAV_MAX_LAG_DAYS, symbol, trading_day, nav_date,
        )
        return {
            "symbol": symbol, "result": "skipped", "reason": f"nav_lag_{lag}bd",
            "trading_day": trading_day.isoformat(), "nav_date": nav_date.isoformat(),
        }

    result = upsert_etf_nav(symbol, trading_day, nav, price)
    return {
        "symbol": symbol, "result": result, "trading_day": trading_day.isoformat(),
        "nav": float(nav), "price": float(price),
    }


def collect_etf_nav(client, symbols=None) -> dict:
    """ETF_SYMBOLS 전체 수집(일 1회 폴링 진입점). 한 심볼 실패가 나머지를 막지 않음."""
    symbols = symbols or ETF_SYMBOLS
    summary = {}
    for sym in symbols:
        try:
            summary[sym] = resolve_and_upsert_one(client, sym)
        except Exception as exc:  # noqa: BLE001
            logger.warning("etf_nav 수집 실패 symbol=%s: %s", sym, exc)
            summary[sym] = {"symbol": sym, "result": "error", "error": str(exc)}
    return summary
