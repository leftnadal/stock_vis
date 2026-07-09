"""
DailyPrice 3년 백필 (TH-9, 결정14=A) — stocks 도메인 소유 쓰기.

C6/C7(Theme Heat) 활성용 구성종목 3년 가격 이력을 **공유 정본 DailyPrice** 에 백필한다
(전용 원장 신설 기각 = 이중 정본 drift 방지, 결정14). chainsight 는 이 데이터를 읽기만 한다.

조정 규약: FMP `/stable/historical-price-eod/full` 의 `close` 필드 = 기존 DailyPrice.close_price
와 동일 소스·규약(stock_sync_service 정합). 별도 adjClose 미사용.

겹침 대조 게이트(쓰기 전 필수): 기존 보유 구간 ∩ FMP 응답의 close 상대오차 > threshold(기본
0.5%) 종목은 **쓰기 정지 + 목록 상신**(조정 규약 불일치 = 이력 오염 위험), 나머지 진행.
"""

import logging
import statistics
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Sequence

logger = logging.getLogger(__name__)


def backfill_daily_prices(
    client: Any,
    symbols: Sequence[str],
    from_date: date,
    to_date: date,
    error_threshold: float = 0.005,
    dry_run: bool = False,
) -> dict:
    """
    symbols 각 종목의 [from_date, to_date] DailyPrice 를 FMP 로 백필. 겹침 대조 → 멱등 upsert.

    반환 = {written, halted:[(sym,max_err)], errors:{sym:reason}, coverage:{sym:earliest},
            overlap_max_err, overlap_median_err, symbols_written}.
    """
    from packages.shared.stocks.models import DailyPrice, Stock

    written = 0
    halted: list[tuple] = []
    errors: dict[str, str] = {}
    coverage: dict[str, str] = {}
    symbols_written: list[str] = []
    all_rel_errs: list[float] = []

    for sym in [s.upper() for s in symbols]:
        st = Stock.objects.filter(symbol=sym).first()
        if st is None:
            errors[sym] = "stock_not_registered"
            continue

        bars = client.get_historical_price(sym, from_date.isoformat(), to_date.isoformat())
        if not isinstance(bars, list) or not bars:
            errors[sym] = "no_data"
            continue

        fmp_by_date: dict[date, dict] = {}
        for b in bars:
            draw = b.get("date")
            if not draw or b.get("close") is None:
                continue
            try:
                fmp_by_date[date.fromisoformat(str(draw)[:10])] = b
            except (ValueError, TypeError):
                continue
        if not fmp_by_date:
            errors[sym] = "no_valid_bars"
            continue

        # 겹침 대조 게이트
        max_err = 0.0
        overlap = 0
        existing = DailyPrice.objects.filter(
            stock=st, date__in=list(fmp_by_date)
        ).values_list("date", "close_price")
        for d, exc in existing:
            fc = fmp_by_date[d].get("close")
            if exc is not None and float(exc) > 0 and fc is not None:
                e = abs(float(fc) - float(exc)) / float(exc)
                max_err = max(max_err, e)
                overlap += 1
                all_rel_errs.append(e)
        if overlap > 0 and max_err > error_threshold:
            halted.append((sym, round(max_err, 5)))
            logger.warning("백필 정지(겹침 오차 %.4f > %.4f): %s", max_err, error_threshold, sym)
            continue

        coverage[sym] = min(fmp_by_date).isoformat()
        if dry_run:
            continue

        objs = [
            DailyPrice(
                stock=st, currency=getattr(st, "currency", "USD") or "USD", date=d,
                open_price=Decimal(str(b.get("open", 0) or 0)),
                high_price=Decimal(str(b.get("high", 0) or 0)),
                low_price=Decimal(str(b.get("low", 0) or 0)),
                close_price=Decimal(str(b.get("close", 0) or 0)),
                volume=int(b.get("volume", 0) or 0),
            )
            for d, b in fmp_by_date.items()
        ]
        DailyPrice.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=["stock", "date"],
            update_fields=["open_price", "high_price", "low_price", "close_price", "volume"],
        )
        written += len(objs)
        symbols_written.append(sym)

    return {
        "written": written,
        "halted": halted,
        "errors": errors,
        "coverage": coverage,
        "symbols_written": symbols_written,
        "overlap_max_err": round(max(all_rel_errs), 5) if all_rel_errs else 0.0,
        "overlap_median_err": round(statistics.median(all_rel_errs), 5) if all_rel_errs else 0.0,
    }
