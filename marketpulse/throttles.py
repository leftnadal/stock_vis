"""Market Pulse v2 — Throttle classes (PR-M)."""

from rest_framework.throttling import UserRateThrottle


class MarketPulseUserThrottle(UserRateThrottle):
    scope = "market_pulse_user"


class MarketPulseHourThrottle(UserRateThrottle):
    scope = "market_pulse_user_hour"


class MarketPulseLLMThrottle(UserRateThrottle):
    scope = "market_pulse_llm"
