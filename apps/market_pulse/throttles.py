"""
DRF Throttle classes (PR-M).

소속: apps/market_pulse (app 레이어 root).
역할: 마켓 펄스 API에 적용할 user/hour/LLM 별 scope throttle.
  config/settings.py의 DEFAULT_THROTTLE_RATES['market_pulse_*'] 비율과 결합.
주요 심볼: MarketPulseUserThrottle, MarketPulseHourThrottle, MarketPulseLLMThrottle.
"""

from rest_framework.throttling import UserRateThrottle


class MarketPulseUserThrottle(UserRateThrottle):
    scope = "market_pulse_user"


class MarketPulseHourThrottle(UserRateThrottle):
    scope = "market_pulse_user_hour"


class MarketPulseLLMThrottle(UserRateThrottle):
    scope = "market_pulse_llm"
