"""AlertEvent + emit — 앱이 알림을 흘려보내는 표준 봉투.

앱은 이 봉투 하나만 emit한다(트리거 단). 디스패처·정책·전달은 shared가 소유.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class AlertEvent:
    source_app: str
    event_type: str
    dedup_key: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: Optional[datetime] = None


def emit(event: AlertEvent) -> None:
    """이벤트를 디스패처로 흘려보낸다(공개 API — 앱 진입점)."""
    from packages.shared.alerting.dispatcher import dispatch

    dispatch(event)
