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
        # TH-C3-LLM-DICT-1 override(ovr_v1) 개정일 마커 (결정35, 쓰기 3b 2026-07-28 등재).
        # 3b 에서 heat 를 date>=07-12 로만 override 반영 재산출(경로 b). 07-10(마커 이전)은
        # 무접촉이므로 이 마커가 이제 heat delta 에 참으로 적용된다(3단의 "거짓 적용" 해소).
        # date=07-11 = override 재작성 코퍼스 경계. 07-12 이후 heat delta 는 override 방법론 반영.
        # affected_themes(결정30): 07-12 이후 재산출로 score/C3 변동 = FinSvc/CC/Energy/Ind/
        # Tech(기존) + Healthcare(결측 해소 신규).
        "date": date(2026, 7, 11),
        "kind": "ovr_v1_dict_recompute",
        "note": "TH-C3-LLM-DICT-1 override(ovr_v1) 사전 재산출 — heat date>=07-12 override 반영(결정35, 3b). 07-12 이후 C3 delta 방법론 불연속.",
        "affected_themes": [
            "Financial Services", "Consumer Cyclical", "Energy",
            "Industrials", "Technology", "Healthcare",
        ],
    },
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
