"""Market Pulse v2 Pydantic v2 schemas (PR-A2).

JSONField 검증 + 후속 PR(B/C/D/E)의 service 레이어에서 import 사용.
"""
from .anomaly import R02Evidence, R04Evidence, R09Evidence, R12Evidence
from .briefing import BriefingSection
from .news import NewsEntities
from .regime import (
    IndicatorsSnapshot,
    IndicatorValue,
    MatchedCondition,
    PendingTransition,
)

__all__ = [
    'BriefingSection',
    'IndicatorValue',
    'IndicatorsSnapshot',
    'MatchedCondition',
    'NewsEntities',
    'PendingTransition',
    'R02Evidence',
    'R04Evidence',
    'R09Evidence',
    'R12Evidence',
]
