"""
MacroVIXProvider — VIXProvider 포트(packages/shared)의 macro.models 기반 구현(BOUNDARY-3).

소속: apps/market_pulse/services (app 레이어 — shared 포트 구현체).
역할: packages.shared.stocks.services.vix_provider.VIXProvider ABC의 두 메서드를
  macro.IndicatorValue(code='VIXCLS') 쿼리로 구현. VIX 종가 시계열·최신값 공급.
소스: macro.IndicatorValue(FRED VIXCLS 시리즈). 이전엔 macro.MarketIndex/
  MarketIndexPrice(category='volatility')를 읽었으나 해당 소스가 0건이라 regime이
  항상 'normal'로 degraded → 실제 적재된 VIXCLS(IndicatorValue)로 교체(MP-VIX-SRC).
주요 심볼:
  - VIX_INDICATOR_CODE: IndicatorValue 조회 코드('VIXCLS').
  - MacroVIXProvider: get_latest_vix(target_date) -> float|None, get_vix_series(
    date_from, date_to) -> list[Decimal].
의존: macro.models (apps→app 합법). IndicatorValue도 macro app 소속이라 명칭 'Macro' 유지.
등록: apps/market_pulse/apps.py::MarketpulseConfig.ready()에서 register_vix_provider(...).
주의: BOUNDARY-3(2026-06-04) 채택한 의존 역전 + 등록 패턴의 한 축. shared가 macro·apps를
  거꾸로 import하지 않게 하는 유일한 통로. shared 코드는 이 클래스를 직접 import하지 않는다.
계약보존: VIXProvider ABC 시그니처(get_latest_vix/get_vix_series)·반환 타입(float|None /
  list[Decimal] 날짜 오름차순)·빈 결과 처리([]/None) 불변. 내부 읽기 소스만 교체.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from packages.shared.stocks.services.vix_provider import VIXProvider


VIX_INDICATOR_CODE = "VIXCLS"


class MacroVIXProvider(VIXProvider):
    """macro.IndicatorValue(VIXCLS) 기반 VIX 공급체."""

    def get_latest_vix(self, target_date: date) -> Optional[float]:
        from macro.models import IndicatorValue

        value = (
            IndicatorValue.objects.filter(
                indicator__code=VIX_INDICATOR_CODE,
                date__lte=target_date,
            )
            .order_by("-date")
            .values_list("value", flat=True)
            .first()
        )
        if value is None:
            return None
        return float(value)

    def get_vix_series(
        self, date_from: date, date_to: date
    ) -> list[Decimal]:
        from macro.models import IndicatorValue

        return list(
            IndicatorValue.objects.filter(
                indicator__code=VIX_INDICATOR_CODE,
                date__gt=date_from,
                date__lte=date_to,
            )
            .order_by("date")
            .values_list("value", flat=True)
        )
