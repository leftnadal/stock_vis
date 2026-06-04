"""VIX Provider 포트 (의존 역전).

shared의 EOD 코드가 macro.models를 거꾸로 import하는 위반을 끊기 위한 계약.
구현체는 app 계층(apps/market_pulse/)에 위치하며 `apps.ready()`에서 등록한다.
shared 코드는 이 모듈만 import한다 — apps.market_pulse를 lazy로라도 가리키지 않는다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Optional


class VIXProviderNotRegistered(RuntimeError):
    """VIX provider 미등록 상태에서 get_vix_provider() 호출 시."""


class VIXProvider(ABC):
    """VIX 종가 공급 계약.

    행위보존 규약:
    - get_latest_vix는 호출자가 20.0(float)과 비교/사용하던 그대로 float을 반환한다.
      못 찾으면 None. 호출자가 fallback(20.0)을 결정한다.
    - get_vix_series는 values_list("close", flat=True)와 동치인 Decimal 리스트를
      날짜 오름차순으로 반환한다. float 변환은 호출자가 numpy 진입 직전에 수행한다.
    """

    @abstractmethod
    def get_latest_vix(self, target_date: date) -> Optional[float]:
        """target_date 이하 가장 최근 VIX 종가(float). 없으면 None."""

    @abstractmethod
    def get_vix_series(
        self, date_from: date, date_to: date
    ) -> list[Decimal]:
        """date_from < date <= date_to 범위 VIX 종가 시계열, 날짜 오름차순.

        Returns: values_list('close', flat=True)와 동치인 Decimal 리스트.
        """


_provider: Optional[VIXProvider] = None


def register_vix_provider(impl: VIXProvider) -> None:
    """provider 구현체를 등록한다. idempotent — 동일 호출 반복 안전."""
    global _provider
    _provider = impl


def get_vix_provider() -> VIXProvider:
    """등록된 provider를 반환한다. 미등록 시 명시적 예외."""
    if _provider is None:
        raise VIXProviderNotRegistered(
            "VIX provider not registered. "
            "Ensure apps.market_pulse is in INSTALLED_APPS and its ready() ran."
        )
    return _provider
