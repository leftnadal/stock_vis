"""검증 스크립트 공통 — Django 초기화 + CostGuard reset."""

from __future__ import annotations

import os

import django


def init_django() -> None:
    """`DJANGO_SETTINGS_MODULE`을 `config.settings`로 고정 + django.setup()."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


def reset_for_slice(slice_id: str = "slice3", max_calls: int = 50):
    """슬라이스 진입 시 호출. 비용 가드 초기화 (멱등).

    동일 slice_id로 두 번 호출하면 두 번째는 reset 스킵 — 누적 카운트 보존.
    Slice 3 내 여러 run 스크립트가 호출해도 안전.

    Returns:
        CostGuard 인스턴스
    """
    init_django()
    from apps.portfolio.llm.cost_guard import CostGuard

    guard = CostGuard.get_instance()
    if guard.slice_id != slice_id:
        guard.reset_slice(slice_id, max_calls)
    return guard
