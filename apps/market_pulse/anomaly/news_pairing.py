"""
News Pairing (PR-D, 옵션 W) — 이상 신호와 가장 가까운 뉴스 1건 매칭.

소속: apps/market_pulse/anomaly (app 레이어).
역할: FiredRule + AnomalyContext 기준으로 시간/심볼/카테고리 매칭이 가장 가까운
  MarketPulseNews 1건을 선택. 페어링 실패 시 None.
주요 심볼: find_pair(fired, ctx) -> Optional[MarketPulseNews].
의존: apps.market_pulse.models.news.MarketPulseNews.
소비처: tasks/anomaly.py의 mp_detect_anomaly_5min — AnomalySignalLog.paired_news FK.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone as django_timezone

from apps.market_pulse.anomaly.engine import AnomalyContext, FiredRule
from apps.market_pulse.models.news import MarketPulseNews

PAIRING_PREFERENCE = {
    "R02": [MarketPulseNews.Category.MAG7, MarketPulseNews.Category.SMART_MONEY],
    "R04": [MarketPulseNews.Category.MACRO, MarketPulseNews.Category.GEOPOLITICS],
    "R09": [MarketPulseNews.Category.SECTOR, MarketPulseNews.Category.INDEX],
    "R12": [MarketPulseNews.Category.SECTOR, MarketPulseNews.Category.INDEX],
}


def find_pair(
    fired: list[FiredRule],
    ctx: AnomalyContext,
    *,
    lookback_hours: int = 24,
) -> MarketPulseNews | None:
    if not fired:
        return None
    cutoff = django_timezone.now() - timedelta(hours=lookback_hours)
    for rule in fired:
        prefs = PAIRING_PREFERENCE.get(rule.rule_id, [])
        for cat in prefs:
            qs = MarketPulseNews.objects.filter(
                category=cat,
                published_at__gte=cutoff,
            )
            if rule.rule_id == "R09" and ctx.sector_extreme_symbol:
                preferred = qs.filter(
                    entities__tickers__contains=ctx.sector_extreme_symbol
                )
                hit = preferred.order_by("-published_at").first()
                if hit:
                    return hit
            hit = qs.order_by("-published_at").first()
            if hit:
                return hit
    return None
