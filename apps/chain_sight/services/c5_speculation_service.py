"""
C5 투기 심리 — 거래량 백필 + fetch 배선 (TH-7d, 결정12b) — 설계 앵커 §2 C5.

C5 = 레버리지÷원본 ETF 거래량 20일 비율의 3년 z. 순수 계산은 heat_components.c5_speculation
재사용, 이 모듈은 **데이터 계층(백필 + from_db 시계열 조립)만** 신설(c2a_insider_from_db 패턴).

부호: 레버리지/원본 거래량 비율 상승 = 투기적 포지셔닝 확대 = 과열 상승 → 정방향(§2 C5).
레버리지 ETF 부재 섹터(XLB·XLC) = c5_no_leveraged_etf 결측(§3-5).
"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Sequence

from apps.chain_sight.services.heat_components import DEFAULT_MIN_N, c5_speculation, make_component

logger = logging.getLogger(__name__)

WINDOW_DAYS = 20  # 트레일링 거래일 (§2 "20일")


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


# ────────────────────────────── 백필 ──────────────────────────────
def backfill_etf_daily_bars(
    client: Any,
    symbols: Sequence[str],
    from_date: date,
    to_date: date,
) -> dict:
    """
    EtfDailyBar 3년 백필 (FMP historical-price-eod). 가드(리스트·필드) 통과분만 멱등 upsert.

    이상 응답(빈 리스트·비리스트) → 그 심볼 DB 무접촉 skip. 개별 bar 필드 결측(date·volume)
    도 skip. update_or_create(symbol, date) 멱등.
    """
    from apps.chain_sight.models import EtfDailyBar

    created = updated = skipped_syms = skipped_bars = 0
    for sym in [s.upper() for s in symbols]:
        bars = client.get_historical_price(sym, from_date.isoformat(), to_date.isoformat())
        if not isinstance(bars, list) or not bars:
            skipped_syms += 1
            logger.warning("EtfDailyBar 백필 skip(가드): %s 응답 이상 (DB 무접촉)", sym)
            continue
        for bar in bars:
            draw = bar.get("date")
            vol = bar.get("volume")
            if not draw or vol is None:
                skipped_bars += 1
                continue
            try:
                d = date.fromisoformat(str(draw)[:10])
                vol_i = int(float(vol))
            except (ValueError, TypeError):
                skipped_bars += 1
                continue
            _obj, is_created = EtfDailyBar.objects.update_or_create(
                symbol=sym, date=d,
                defaults={"close": _to_decimal(bar.get("close")), "volume": vol_i},
            )
            created += int(is_created)
            updated += int(not is_created)

    logger.info(
        "EtfDailyBar 백필 %s~%s: created=%d updated=%d skipped_syms=%d skipped_bars=%d",
        from_date, to_date, created, updated, skipped_syms, skipped_bars,
    )
    return {"created": created, "updated": updated,
            "skipped_syms": skipped_syms, "skipped_bars": skipped_bars}


# ────────────────────────────── fetch 배선 (from_db) ──────────────────────────────
def c5_speculation_from_db(
    primary_syms: Sequence[str],
    leveraged_syms: Sequence[str],
    as_of: date,
    lookback_days: int = 365 * 3,
    window: int = WINDOW_DAYS,
    step_days: int = 7,
    min_n: int = DEFAULT_MIN_N,
) -> dict:
    """
    EtfDailyBar 위 C5 계산 (§2). 레버리지Σ(20d vol) ÷ 원본Σ(20d vol) 비율의 3년 z.

    절차(c2a_insider_from_db 동형):
      1. [as_of − lookback − 여유, as_of] bars 1회 로드 (거래일 union).
      2. step_days 간격 앵커마다 직전 window 거래일 레버리지/원본 거래량 비율 → history.
      3. current = as_of 비율. c5_speculation(current, history) 순수함수 재사용(부호·계약 단일 소스).

    레버리지·원본 심볼 없음 → c5_no_leveraged_etf 결측(§3-5).
    """
    from apps.chain_sight.models import EtfDailyBar

    pris = [s.upper() for s in primary_syms]
    levs = [s.upper() for s in leveraged_syms]
    if not levs or not pris:
        return make_component(None, raw=None, missing_reason="c5_no_leveraged_etf")

    earliest = as_of - timedelta(days=lookback_days + window * 3)  # 거래일 여유
    rows = EtfDailyBar.objects.filter(
        symbol__in=set(pris) | set(levs),
        date__gte=earliest,
        date__lte=as_of,
    ).values("symbol", "date", "volume")

    by_sym: dict[str, dict[date, int]] = defaultdict(dict)
    for r in rows:
        if r["volume"] is not None:
            by_sym[r["symbol"]][r["date"]] = r["volume"]

    all_dates = sorted({d for m in by_sym.values() for d in m})
    if not all_dates:
        return make_component(None, raw=None, missing_reason="c5_no_volume_data")

    def _ratio_at(anchor: date) -> Optional[float]:
        trailing = [d for d in all_dates if d <= anchor][-window:]
        if len(trailing) < window:
            return None
        lev_vol = sum(by_sym[s].get(d, 0) for s in levs for d in trailing)
        pri_vol = sum(by_sym[s].get(d, 0) for s in pris for d in trailing)
        if pri_vol <= 0:
            return None
        return lev_vol / pri_vol

    history: list[Optional[float]] = []
    cursor = as_of - timedelta(days=lookback_days)
    while cursor < as_of:
        history.append(_ratio_at(cursor))
        cursor += timedelta(days=step_days)

    current = _ratio_at(as_of)
    if current is None:
        return make_component(None, raw=None, missing_reason="c5_no_recent_window")

    return c5_speculation(current, history, min_n=min_n)


def sector_etf_pair(entity) -> tuple[list[str], list[str]]:
    """섹터(HeatEntity) 의 active primary·leveraged ETF 심볼 (C5 입력). ThemeEtfMap 단일 소스."""
    from apps.chain_sight.models import ThemeEtfMap

    maps = ThemeEtfMap.objects.filter(theme=entity, active=True)
    pri = sorted(m.etf_symbol for m in maps if m.role == "primary")
    lev = sorted(m.etf_symbol for m in maps if m.role == "leveraged")
    return pri, lev
