"""Market Pulse v2 — News Pairing (PR-D, 옵션 W)."""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone as django_timezone

from marketpulse.anomaly.engine import AnomalyContext, FiredRule
from marketpulse.models.news import MarketPulseNews


PAIRING_PREFERENCE = {
    'R02': [MarketPulseNews.Category.MAG7, MarketPulseNews.Category.SMART_MONEY],
    'R04': [MarketPulseNews.Category.MACRO, MarketPulseNews.Category.GEOPOLITICS],
    'R09': [MarketPulseNews.Category.SECTOR, MarketPulseNews.Category.INDEX],
    'R12': [MarketPulseNews.Category.SECTOR, MarketPulseNews.Category.INDEX],
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
                category=cat, published_at__gte=cutoff,
            )
            if rule.rule_id == 'R09' and ctx.sector_extreme_symbol:
                preferred = qs.filter(entities__tickers__contains=ctx.sector_extreme_symbol)
                hit = preferred.order_by('-published_at').first()
                if hit:
                    return hit
            hit = qs.order_by('-published_at').first()
            if hit:
                return hit
    return None
