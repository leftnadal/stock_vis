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
# MP2-ALERTS S1: 선택적 폴백 렌더러 — primary가 예외를 던지면 디스패처가 이걸로 대체(발송 무실패).
_fallbacks: dict[tuple[str, str], Renderer] = {}


def register_alert_renderer(
    source_app: str, event_type: str, renderer: Renderer, fallback: Renderer | None = None
) -> None:
    """렌더러 등록(idempotent — 동일 키 재등록 시 최신 구현체 active).

    fallback: primary 렌더가 예외를 던질 때 디스패처가 대체할 렌더러(선택). 미지정 시 폴백 없음
      (기존 동작: primary 예외 → 발송 실패). fallback은 결정적·무예외여야 한다(호출부 계약).
    """
    _renderers[(source_app, event_type)] = renderer
    if fallback is not None:
        _fallbacks[(source_app, event_type)] = fallback
    else:
        _fallbacks.pop((source_app, event_type), None)


def get_alert_renderer(source_app: str, event_type: str) -> Renderer:
    """등록된 렌더러 반환. 미등록 시 명시적 예외."""
    renderer = _renderers.get((source_app, event_type))
    if renderer is None:
        raise AlertRendererNotRegistered(f"{source_app}:{event_type}")
    return renderer


def get_alert_fallback(source_app: str, event_type: str) -> Renderer | None:
    """등록된 폴백 렌더러 반환(없으면 None). 미등록은 예외 아님(폴백은 선택)."""
    return _fallbacks.get((source_app, event_type))
