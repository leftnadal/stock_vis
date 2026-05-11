"""Manual eval 분포 폭 KPI 측정 (Slice 7 Part 2 §4, #26 부채 처리).

`manual_eval_rubric.md §C.6` 권장 룰 — 평가자 자기 점검을 위한 자동 게이트.

KPI:
  - 분포 폭 (max - min) ≥ 3.0
  - 5점 비율 5~20%
  - 1점 사용 1건 이상 (전 범위 활용 신호)
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence


def distribution_width_kpi(scores: Sequence[float]) -> dict:
    """1~5 평점 시퀀스 → KPI 측정 결과.

    Args:
        scores: 평점 리스트 (1.0~5.0). 정수 반올림 후 측정.

    Returns:
        dict: width / five_ratio / one_count / pass / distribution
    """
    if not scores:
        return {
            "width": 0,
            "five_ratio": 0.0,
            "one_count": 0,
            "pass": False,
            "distribution": {},
        }
    ints = [int(round(s)) for s in scores]
    width = max(ints) - min(ints)
    five_ratio = ints.count(5) / len(ints)
    one_count = ints.count(1)
    pass_flag = (width >= 3) and (0.05 <= five_ratio <= 0.20) and (one_count >= 1)
    return {
        "width": width,
        "five_ratio": round(five_ratio, 3),
        "one_count": one_count,
        "pass": pass_flag,
        "distribution": dict(Counter(ints)),
    }
