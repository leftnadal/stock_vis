"""
apps/market_pulse/constants — 마켓 펄스 상수 모듈 패키지.

소속: apps/market_pulse (app 레이어). 의존은 apps → shared 한 방향.
역할: 화면 상수(인사이트 룰·라벨·색상·아이콘 등)를 단일 진입점으로 re-export.
주요 심볼: insights.py의 FEAR_GREED_RULES / INSIGHT_RULES / YIELD_CURVE_RULES /
  RATE_IMPACT_RULES / VIX_RULES + 헬퍼 함수 3종.
"""
from .insights import (
    FEAR_GREED_RULES,
    INSIGHT_RULES,
    RATE_IMPACT_RULES,
    VIX_RULES,
    YIELD_CURVE_RULES,
    calculate_fear_greed_index,
    get_insight_message,
    get_rate_impact_sectors,
)
from .sector_cd import (
    CD_MOMENTUM_BASELINE,
    CD_REL_STRENGTH_5D_LOOKBACK,
    CD_REL_STRENGTH_BASELINE,
    classify_cd_state,
    derive_rel_strength_5d,
    resolve_official_cd_state,
)

__all__ = [
    'INSIGHT_RULES',
    'get_insight_message',
    'get_rate_impact_sectors',
    'calculate_fear_greed_index',
    'FEAR_GREED_RULES',
    'YIELD_CURVE_RULES',
    'RATE_IMPACT_RULES',
    'VIX_RULES',
    'CD_REL_STRENGTH_BASELINE',
    'CD_MOMENTUM_BASELINE',
    'CD_REL_STRENGTH_5D_LOOKBACK',
    'classify_cd_state',
    'derive_rel_strength_5d',
    'resolve_official_cd_state',
]
