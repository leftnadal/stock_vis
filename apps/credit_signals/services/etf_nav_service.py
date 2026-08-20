"""
ETF NAV·시장가 수집 서비스 (P2a-1 → P2a-1c C″).

FMP 채권 ETF etf/info nav = 전일(T-1) 종가 NAV를 익일 오전(~11:3x ET) 또는 당일
저녁(~17:1x ET)에 게시(iShares 역산 2/2 확정). 따라서 quote 정본거래일에 nav를
묶으면 항상 1일 밀린 혼합이 된다. C″ 귀속 규칙:
  - nav_trade_date = updatedAt(ET) 날짜 당일 (P2a-1e T-0: fix 08-14 후 저녁 스윕 =
    당일 확정 NAV, iShares 교차검증. 비거래일 pub은 가드 P2a-1d가 선차단.)
  - price = EOD 이력(/stable/historical-price-eod/full)의 당일 종가 (주 소스 ⓑ)
    · quote.previousClose 확보 시 교차검증(ⓐ), 불일치는 행 생성 + mismatch 플래그(ⓑ 우선)
  - 게이트: 마감시각(C′) 폐기 → 피드 정체 게이트. updatedAt 날짜가 오늘(ET) 기준
    ETF_NAV_STALE_TRADING_DAYS 거래일 이상 과거면 skip(nav_stale).

upsert 규약 = MacroSeriesHistory와 동형(insert-only + revise-on-change). nav_updated_at
감사 추적 불변. 삭제 없음(§10). 디스카운트는 compute-on-read(원장 미적재).
"""
import logging
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import numpy as np
from django.utils import timezone

from ..constants import (
    ETF_NAV_STALE_TRADING_DAYS,
    ETF_PRICE_MISMATCH_TOL,
    ETF_SYMBOLS,
)
from ..models import EtfNavHistory
from ..trading_calendar import (
    is_trading_day,
    next_trading_day,
    warn_if_coverage_expiring,
)

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


def _nav_updated_dt(info: dict) -> datetime | None:
    """etf/info updatedAt(ISO8601)의 ET tz-aware datetime (시각 포함, C′ 마감 게이트용)."""
    raw = info.get("updatedAt")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(_ET)


def _business_day_lag(a: date, b: date) -> int:
    """a↔b 영업일 거리(절대값). numpy busday_count 사용(반열림 구간 보정 abs)."""
    return abs(int(np.busday_count(a, b)))


def upsert_etf_nav(
    symbol: str, trading_day: date, nav: Decimal, price: Decimal,
    nav_updated_at: datetime | None = None,
) -> str:
    """
    (symbol, trading_day) 행 upsert. 반환: 'created' | 'updated' | 'skipped'.

    최초 → insert(ingested_at=now). nav·price 변동 → revise(revised_at=now,
    ingested_at 유지). 동일 → no-op. 삭제 없음. nav_updated_at(FMP strike 시각)은
    감사용으로 병기 저장하며, revise 시 함께 갱신한다.
    """
    existing = EtfNavHistory.objects.filter(symbol=symbol, date=trading_day).first()
    if existing is None:
        EtfNavHistory.objects.create(
            symbol=symbol, date=trading_day, nav=nav, price=price,
            nav_updated_at=nav_updated_at,
        )
        return "created"
    if existing.nav != nav or existing.price != price:
        existing.nav = nav
        existing.price = price
        existing.nav_updated_at = nav_updated_at
        existing.revised_at = timezone.now()
        existing.save(update_fields=["nav", "price", "nav_updated_at", "revised_at"])
        return "updated"
    return "skipped"


def _eod_close(client, symbol: str, target: date) -> Decimal | None:
    """EOD 이력(/stable/historical-price-eod/full)의 target 거래일 종가(close). 주 소스 ⓑ."""
    frm = (target - timedelta(days=10)).isoformat()
    to = (target + timedelta(days=2)).isoformat()
    try:
        rows = client.get_historical_price(symbol, from_date=frm, to_date=to)
    except Exception as exc:  # noqa: BLE001
        logger.warning("etf_nav EOD 조회 실패 symbol=%s target=%s: %s", symbol, target, exc)
        return None
    if not isinstance(rows, list):
        return None
    tgt = target.isoformat()
    for r in rows:
        if isinstance(r, dict) and r.get("date") == tgt:
            return _to_decimal(r.get("close"))
    return None


def _trading_days_between(a: date, b: date) -> int:
    """(a, b] 사이 거래일 수 (a < b 가정). 피드 정체 감지용."""
    n, c = 0, a
    while c < b:
        c = next_trading_day(c)
        n += 1
    return n


def resolve_and_upsert_one(client, symbol: str, today_et: date | None = None) -> dict:
    """
    단일 ETF C″ 귀속: etf/info nav(=전일 종가) → updatedAt D-1 거래일에 귀속,
    price는 EOD 이력의 D-1 종가로 페어링. quote.previousClose로 교차검증.
    """
    quote = client.get_quote(symbol)
    info = client.get_etf_info(symbol)

    nav = _to_decimal(info.get("nav"))
    nav_dt = _nav_updated_dt(info)  # ET tz-aware datetime | None

    if nav is None or nav <= 0:
        logger.warning("etf_nav skip(nav 결측/이상): symbol=%s nav=%s", symbol, nav)
        return {"symbol": symbol, "result": "skipped", "reason": "missing_or_invalid"}
    if nav_dt is None:
        logger.warning("etf_nav skip(nav updatedAt 파싱 실패): symbol=%s", symbol)
        return {"symbol": symbol, "result": "skipped", "reason": "nav_date_unparseable"}

    if today_et is None:
        today_et = datetime.now(_ET).date()
    warn_if_coverage_expiring(today_et)

    nav_pub_date = nav_dt.date()  # updatedAt(ET)의 게시 날짜 D

    # 가드(P2a-1d) — 비거래일 게시: 게시일이 미국 거래일이 아니면(주말·휴장일) FMP가
    # 내놓은 값은 직전 거래일치 잔존값 이월분이지 새 strike가 아니다. create·revise를
    # 원천 차단하고 기존행은 무접촉(대조만) 한다. 키 = 게시일(updatedAt의 ET 날짜)이지
    # 발화일이 아니다 — 거래일 게시의 클린 create/revise 경로는 그대로 살린다.
    # (08-16 오귀속: 토·일 게시가 prev_trading_day=금요일 행을 잔존값으로 조기 생성.)
    if not is_trading_day(nav_pub_date):
        logger.warning(
            "etf_nav skip(비거래일 게시): pub=%s — create 차단", nav_pub_date
        )
        return {
            "symbol": symbol, "result": "skipped", "reason": "non_trading_day_pub",
            "nav_updated_at": nav_dt.isoformat(),
        }

    # 게이트 — 피드 정체: 게시 날짜가 오늘 기준 N거래일 이상 과거면 skip(nav_stale).
    if nav_pub_date < today_et:
        gap = _trading_days_between(nav_pub_date, today_et)
        if gap >= ETF_NAV_STALE_TRADING_DAYS:
            logger.warning(
                "etf_nav skip(피드 정체 %d거래일 ≥ %d): symbol=%s nav_updated=%s 오늘=%s "
                "— 새 strike 미게시, 자가 보정 없이 skip",
                gap, ETF_NAV_STALE_TRADING_DAYS, symbol, nav_pub_date, today_et,
            )
            return {
                "symbol": symbol, "result": "skipped", "reason": "nav_stale",
                "nav_updated_at": nav_dt.isoformat(), "today_et": today_et.isoformat(),
            }

    # 귀속(P2a-1e T-0): nav_trade_date = 게시 날짜 D 당일 (당일 확정 NAV).
    # fix(08-14) 이후 FMP 저녁 스윕(20:1x~20:5x ET)이 당일 확정 NAV를 게시 —
    # iShares 공식치 양 ETF 교차검증. T-1(전일 귀속)은 로테이션 시절 오전 파싱의
    # 부산물로 소멸. 비거래일 pub은 위 가드(P2a-1d)가 선차단하므로 여기 도달하는
    # 것은 거래일 pub뿐 = nav_trade_date는 항상 거래일. price 페어링이 '당일 nav
    # vs 당일 EOD'로 정렬되어 ⓐ/ⓑ mismatch 판별력 회복.
    nav_trade_date = nav_pub_date

    # price = EOD 이력의 nav_trade_date 종가 (주 소스 ⓑ).
    price = _eod_close(client, symbol, nav_trade_date)
    if price is None or price <= 0:
        logger.warning(
            "etf_nav skip(EOD 종가 미확보): symbol=%s nav_trade_date=%s — price 페어링 불가",
            symbol, nav_trade_date,
        )
        return {
            "symbol": symbol, "result": "skipped", "reason": "price_unavailable",
            "nav_trade_date": nav_trade_date.isoformat(),
        }

    # ⓐ 교차검증: quote.previousClose(전일 시장 종가)와 EOD 종가 비교.
    prev_close = _to_decimal(quote.get("previousClose")) if isinstance(quote, dict) else None
    mismatch = False
    if prev_close is not None and abs(prev_close - price) > ETF_PRICE_MISMATCH_TOL:
        mismatch = True
        logger.warning(
            "etf_nav price mismatch(ⓑ 우선): symbol=%s nav_trade_date=%s "
            "ⓑ_eod_close=%s vs ⓐ_prev_close=%s (tol %s)",
            symbol, nav_trade_date, price, prev_close, ETF_PRICE_MISMATCH_TOL,
        )

    result = upsert_etf_nav(symbol, nav_trade_date, nav, price, nav_updated_at=nav_dt)
    return {
        "symbol": symbol, "result": result, "trade_date": nav_trade_date.isoformat(),
        "nav": float(nav), "price": float(price),
        "nav_updated_at": nav_dt.isoformat(), "price_mismatch": mismatch,
    }


def collect_etf_nav(client, symbols=None, today_et: date | None = None) -> dict:
    """ETF_SYMBOLS 전체 수집(일 1회 폴링 진입점). 한 심볼 실패가 나머지를 막지 않음."""
    symbols = symbols or ETF_SYMBOLS
    summary = {}
    for sym in symbols:
        try:
            summary[sym] = resolve_and_upsert_one(client, sym, today_et=today_et)
        except Exception as exc:  # noqa: BLE001
            logger.warning("etf_nav 수집 실패 symbol=%s: %s", sym, exc)
            summary[sym] = {"symbol": sym, "result": "error", "error": str(exc)}
    return summary
