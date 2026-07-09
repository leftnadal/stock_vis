"""
유니버스 갱신 감시 (TH-6) — TH-UNIVERSE-REFRESH-ALERT staleness arm.

설계 앵커에 유니버스 갱신 주기 사양 없음 → 주 1회 갱신(월 07:00 ET) + 주간 staleness 감시.
staleness 임계는 **결정8 상수 재사용**(heat_beat.UNIVERSE_STALE_DAYS=30, 중복 정의 금지) +
경고 임계 STALE_WARN_DAYS=7(감시 조기 경보).

갱신 성공 시 SP500Constituent.updated_at 이 신선(auto_now) → is_universe_stale=False 자연 전환
(결정8 연동). 소스 = Wikipedia(결정9 B, serverless_client.get_sp500_constituents).
"""

import logging
from datetime import date
from typing import Optional

from apps.chain_sight.services.heat_beat import UNIVERSE_STALE_DAYS
from apps.chain_sight.services.universe_snapshot import live_universe_symbols  # noqa: F401

logger = logging.getLogger(__name__)

# 조기 경고 임계 (감시). 30일(stale)은 결정8 상수 재사용.
STALE_WARN_DAYS = 7


def universe_staleness_status(as_of: Optional[date] = None) -> dict:
    """
    유니버스 신선도 상태 — {last_updated, days_since, warn, stale}.

    last_updated = max(SP500Constituent.updated_at). warn = >7일, stale = >30일(결정8).
    """
    from django.db.models import Max
    from django.utils import timezone

    from packages.shared.stocks.models import SP500Constituent

    if as_of is None:
        as_of = timezone.now().date()
    dt = SP500Constituent.objects.filter(is_active=True).aggregate(
        m=Max("updated_at")
    )["m"]
    last = dt.date() if dt else None
    days = (as_of - last).days if last else None
    return {
        "last_updated": last.isoformat() if last else None,
        "days_since": days,
        "warn": days is None or days > STALE_WARN_DAYS,
        "stale": days is None or days > UNIVERSE_STALE_DAYS,
    }
