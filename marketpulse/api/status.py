"""Market Pulse v2 — API Status Enum (PR-I)."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone as django_timezone


class APIStatus:
    OK = "OK"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    STALE = "STALE"
    FAILED = "FAILED"
    MARKET_CLOSED = "MARKET_CLOSED"


STALE_THRESHOLD_MINUTES = 30


def is_market_open(now=None) -> bool:
    now = now or django_timezone.now()
    local = now.astimezone()
    if local.weekday() >= 5:
        return False
    h, m = local.hour, local.minute
    if (h, m) < (9, 30):
        return False
    if (h, m) >= (16, 0):
        return False
    return True


def derive_status(
    *,
    has_required_snapshots: bool,
    any_indicator_stale: bool = False,
    has_failure: bool = False,
    ignore_market_hours: bool = False,
) -> str:
    if has_failure:
        return APIStatus.FAILED
    if any_indicator_stale:
        return APIStatus.STALE
    if not has_required_snapshots:
        return APIStatus.INSUFFICIENT_DATA
    if not ignore_market_hours and not is_market_open():
        return APIStatus.MARKET_CLOSED
    return APIStatus.OK


def is_stale(snapshot_time, *, minutes: int = STALE_THRESHOLD_MINUTES) -> bool:
    if snapshot_time is None:
        return True
    age = django_timezone.now() - snapshot_time
    return age > timedelta(minutes=minutes)
