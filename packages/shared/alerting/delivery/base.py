"""DeliveryProvider 포트(ABC) + 채널 registry — 무상태 전달 추상.

채널 추가 = 이 포트 구현체 하나 추가 + register_provider(채널명, 구현체).
vix_provider 선례 동형(module 싱글톤 dict + register/get + 미등록 예외).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class DeliveryProviderNotRegistered(RuntimeError):
    """등록되지 않은 채널로 get_provider 호출 시."""


class DeliveryProvider(ABC):
    """전달 채널 계약(무상태). deliver는 렌더된 subject/본문을 destination으로 보낸다."""

    @abstractmethod
    def deliver(
        self, *, subject: str, text_body: str, html_body: str, destination: str
    ) -> None:
        """subject/본문을 destination으로 전달. 실패 시 예외 raise(디스패처가 failed 기록)."""


_providers: dict[str, DeliveryProvider] = {}


def register_provider(channel: str, impl: DeliveryProvider) -> None:
    """채널 구현체 등록(idempotent)."""
    _providers[channel] = impl


def get_provider(channel: str) -> DeliveryProvider:
    """등록된 채널 구현체 반환. 미등록 시 명시적 예외."""
    provider = _providers.get(channel)
    if provider is None:
        raise DeliveryProviderNotRegistered(channel)
    return provider
