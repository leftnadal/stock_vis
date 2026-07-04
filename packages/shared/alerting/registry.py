"""알림 렌더러 registry — (source_app, event_type) → 렌더러.

BOUNDARY-3 vix_provider 선례 동형(module 싱글톤 + register/get), 단 단일 슬롯 대신
(source_app, event_type) 키 dict로 확장. 렌더러는 payload(dict)만 받아
(subject, text_body, html_body) 튜플을 반환한다 — shared는 앱 문구를 모른다.
"""
from __future__ import annotations

from typing import Callable

# 렌더러: payload dict → (subject, text_body, html_body)
Renderer = Callable[[dict], "tuple[str, str, str]"]


class AlertRendererNotRegistered(RuntimeError):
    """(source_app, event_type)에 등록된 렌더러가 없을 때."""


_renderers: dict[tuple[str, str], Renderer] = {}


def register_alert_renderer(
    source_app: str, event_type: str, renderer: Renderer
) -> None:
    """렌더러 등록(idempotent — 동일 키 재등록 시 최신 구현체 active)."""
    _renderers[(source_app, event_type)] = renderer


def get_alert_renderer(source_app: str, event_type: str) -> Renderer:
    """등록된 렌더러 반환. 미등록 시 명시적 예외."""
    renderer = _renderers.get((source_app, event_type))
    if renderer is None:
        raise AlertRendererNotRegistered(f"{source_app}:{event_type}")
    return renderer
