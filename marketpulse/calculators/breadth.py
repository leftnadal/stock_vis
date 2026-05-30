"""Market Pulse v2 — Breadth Calculator (PR-F)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date as date_cls
from datetime import timedelta
from decimal import Decimal
from typing import Iterable

from django.db.models import Max, Min, Q
from django.utils import timezone as django_timezone

from marketpulse.models.snapshot import BreadthSnapshot
from packages.shared.stocks.models import DailyPrice, SP500Constituent

logger = logging.getLogger(__name__)


@dataclass
class BreadthMetrics:
    advance_count: int
    decline_count: int
    unchanged_count: int
    total_count: int
    new_high_52w: int
    new_low_52w: int
    ad_line: int
    ad_line_change: int


WINDOW_DAYS = 252


def _resolve_universe_symbols(universe: str) -> list[str]:
    universe = universe.upper()
    if universe == 'SPY':
        return list(
            SP500Constituent.objects.filter(is_active=True).values_list('symbol', flat=True)
        )
    return []


def _latest_two_closes(symbols: Iterable[str], target_date: date_cls) -> dict[str, tuple[Decimal, Decimal | None]]:
    symbols_list = list(symbols)
    if not symbols_list:
        return {}

    today_qs = (
        DailyPrice.objects
        .filter(stock_id__in=symbols_list, date=target_date)
        .values_list('stock_id', 'close_price')
    )
    today_map: dict[str, Decimal] = {sym: close for sym, close in today_qs}

    prev_qs = (
        DailyPrice.objects
        .filter(stock_id__in=list(today_map.keys()), date__lt=target_date)
        .values('stock_id')
        .annotate(prev_date=Max('date'))
    )
    prev_dates = {row['stock_id']: row['prev_date'] for row in prev_qs}

    if prev_dates:
        prev_close_qs = DailyPrice.objects.filter(
            Q(*[Q(stock_id=s, date=d) for s, d in prev_dates.items()], _connector=Q.OR),
        ).values_list('stock_id', 'close_price')
        prev_map = {sym: close for sym, close in prev_close_qs}
    else:
        prev_map = {}

    return {sym: (close, prev_map.get(sym)) for sym, close in today_map.items()}


def _compute_52w_extrema(
    symbols: Iterable[str], target_date: date_cls, window: int = WINDOW_DAYS,
) -> dict[str, tuple[Decimal | None, Decimal | None]]:
    symbols_list = list(symbols)
    if not symbols_list:
        return {}
    window_start = target_date - timedelta(days=window)
    qs = (
        DailyPrice.objects
        .filter(stock_id__in=symbols_list, date__gte=window_start, date__lt=target_date)
        .values('stock_id')
        .annotate(max_c=Max('close_price'), min_c=Min('close_price'))
    )
    return {row['stock_id']: (row['max_c'], row['min_c']) for row in qs}


def compute_breadth(
    *,
    universe: str = 'SPY',
    target_date: date_cls | None = None,
    previous_ad_line: int | None = None,
) -> BreadthMetrics:
    target_date = target_date or django_timezone.localdate()
    symbols = _resolve_universe_symbols(universe)
    closes = _latest_two_closes(symbols, target_date)
    extrema = _compute_52w_extrema(symbols, target_date)

    advance = decline = unchanged = 0
    new_high = new_low = 0

    for sym, (today, prev) in closes.items():
        if prev is not None:
            if today > prev:
                advance += 1
            elif today < prev:
                decline += 1
            else:
                unchanged += 1
        max_c, min_c = extrema.get(sym, (None, None))
        if max_c is not None and today >= max_c:
            new_high += 1
        if min_c is not None and today <= min_c:
            new_low += 1

    total = advance + decline + unchanged

    if previous_ad_line is None:
        prev_snapshot = (
            BreadthSnapshot.objects
            .filter(universe=universe, date__lt=target_date)
            .order_by('-date')
            .first()
        )
        previous_ad_line = prev_snapshot.ad_line if prev_snapshot else 0

    delta = advance - decline
    ad_line = previous_ad_line + delta

    return BreadthMetrics(
        advance_count=advance,
        decline_count=decline,
        unchanged_count=unchanged,
        total_count=total,
        new_high_52w=new_high,
        new_low_52w=new_low,
        ad_line=ad_line,
        ad_line_change=delta,
    )


def upsert_snapshot(
    metrics: BreadthMetrics,
    *,
    universe: str = 'SPY',
    target_date: date_cls | None = None,
    snapshot_time=None,
) -> BreadthSnapshot:
    target_date = target_date or django_timezone.localdate()
    snapshot_time = snapshot_time or django_timezone.now()
    obj, _created = BreadthSnapshot.objects.update_or_create(
        date=target_date,
        universe=universe,
        defaults={
            'snapshot_time': snapshot_time,
            'advance_count': metrics.advance_count,
            'decline_count': metrics.decline_count,
            'unchanged_count': metrics.unchanged_count,
            'total_count': metrics.total_count,
            'new_high_52w': metrics.new_high_52w,
            'new_low_52w': metrics.new_low_52w,
            'ad_line': metrics.ad_line,
            'ad_line_change': metrics.ad_line_change,
            'is_finalized': False,
            'finalized_at': None,
        },
    )
    return obj


def calculate(universe: str = 'SPY', target_date: date_cls | None = None) -> BreadthSnapshot:
    metrics = compute_breadth(universe=universe, target_date=target_date)
    return upsert_snapshot(metrics, universe=universe, target_date=target_date)
