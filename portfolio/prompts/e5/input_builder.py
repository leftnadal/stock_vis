"""
E5 입력 빌더 — 사용자 hint + 현재 프리셋의 metric 목록.

threshold 정보는 현재 preset_metrics.py 구조에 없으므로 null로 제공.
(D-0a 이후 threshold 구조화 시 확장 예정.)

Version: 1.1 (2026-04-24)
"""

from __future__ import annotations

from portfolio.metrics.definitions.metrics import METRICS
from portfolio.metrics.definitions.preset_metrics import PRESET_METRICS
from portfolio.metrics.definitions.presets import PRESETS


def build_e5_input(user_hint: str, current_preset_id: str) -> dict:
    """E5 입력 dict 조립."""
    if current_preset_id not in PRESETS:
        raise ValueError(f"Unknown preset_id: {current_preset_id}")
    preset_info = PRESETS[current_preset_id]
    preset_metric_entries = PRESET_METRICS.get(current_preset_id, [])

    available_metrics: list[dict] = []
    for entry in preset_metric_entries:
        metric_id = entry["metric_id"]
        metric_def = METRICS.get(metric_id, {})
        available_metrics.append(
            {
                "metric_id": metric_id,
                "metric_display_name": metric_def.get("display_name", metric_id),
                "current_tier": entry["tier"],
                # 현재 구조에 프리셋별 threshold 값이 없음 → null
                "current_threshold": None,
            }
        )

    return {
        "user_hint": user_hint,
        "current_preset": {
            "preset_id": current_preset_id,
            "preset_name": preset_info.get("display_name", current_preset_id),
            "preset_category": preset_info.get("category", ""),
        },
        "available_metrics": available_metrics,
    }
