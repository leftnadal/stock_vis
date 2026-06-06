"""
Pydantic v2 schemas 패키지 (PR-A2).

소속: apps/market_pulse/schemas (app 레이어 — Django models의 JSONField 검증).
역할: 도메인별 JSONField 입출력 구조를 Pydantic v2로 검증·직렬화.
주요 심볼: anomaly·briefing·news·regime 4 도메인 스키마 + 통합 re-export.
소비처: services·tasks·api 레이어에서 import. JSONField 저장 전 검증 / API 응답 직렬화.
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
    "BriefingSection",
    "IndicatorValue",
    "IndicatorsSnapshot",
    "MatchedCondition",
    "NewsEntities",
    "PendingTransition",
    "R02Evidence",
    "R04Evidence",
    "R09Evidence",
    "R12Evidence",
]
