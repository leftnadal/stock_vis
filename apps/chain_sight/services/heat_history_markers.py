"""
Heat 이력 방법론 마커 (TH-HISTORY-MARKER 초석 + 결정29 driver 보류 트리거원).

개정일(산식·사전 변경) 목록의 단일 소스. delta_1d 구간(직전 스냅샷~당일)이 마커를 가로지르면
그 delta 는 방법론 artifact → driver(견인 서사) 산출 보류(결정29=B). 온도·신뢰 칩은 무관하게 노출.

향후 TH-HISTORY-MARKER 정식 구현(DB·admin) 시 이 목록을 원장으로 승격.
"""

from datetime import date
from typing import Optional

# 방법론 개정일 (오름차순). date=개정 적용일(그날 재산출로 delta 불연속 발생).
HISTORY_MARKERS = [
    {
        "date": date(2026, 7, 12),
        "kind": "c1_thin_quarter_guard",
        "note": "C1 얇은 분기 가드 도입(결정28) — 07-12 재산출로 전 테마 delta 불연속.",
    },
]


def crossing_marker(prior_date: Optional[date], day: date) -> Optional[dict]:
    """
    delta 구간 (prior_date, day] 이 개정 마커를 가로지르면 그 마커 반환, 아니면 None (결정29 산식).

    prior_date 부재(첫 스냅샷) → None(가로지를 이전 구간 없음). 복수 마커면 최초 반환.
    """
    if prior_date is None:
        return None
    for m in HISTORY_MARKERS:
        if prior_date < m["date"] <= day:
            return m
    return None
