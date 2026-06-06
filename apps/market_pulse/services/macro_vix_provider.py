"""
MacroVIXProvider — VIXProvider 포트(packages/shared)의 macro.models 기반 구현(BOUNDARY-3).

소속: apps/market_pulse/services (app 레이어 — shared 포트 구현체).
역할: packages.shared.stocks.services.vix_provider.VIXProvider ABC의 두 메서드를
  macro.MarketIndex/MarketIndexPrice 쿼리로 구현. VIX(`VIX`/`^VIX`/`VIXX`, category=
  volatility) 종가 시계열·최신값 공급.
주요 심볼:
  - VIX_SYMBOLS / VIX_CATEGORY: 쿼리 상수.
  - MacroVIXProvider: get_latest_vix(target_date) -> float|None, get_vix_series(
    date_from, date_to) -> list[Decimal].
의존: macro.models (apps→app 합법).
등록: apps/market_pulse/apps.py::MarketpulseConfig.ready()에서 register_vix_provider(...).
주의: BOUNDARY-3(2026-06-04) 채택한 의존 역전 + 등록 패턴의 한 축. shared가 macro·apps를
  거꾸로 import하지 않게 하는 유일한 통로. shared 코드는 이 클래스를 직접 import하지 않는다.
행위보존: 옛 eod_pipeline._get_vix_value / eod_regime_calculator._calculate_regime이
  사용하던 쿼리·반환 타입을 그대로 옮긴 것 — 산출 동등성 유지.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from packages.shared.stocks.services.vix_provider import VIXProvider


VIX_SYMBOLS = ["VIX", "^VIX", "VIXX"]
VIX_CATEGORY = "volatility"


class MacroVIXProvider(VIXProvider):
    """macro.MarketIndex/MarketIndexPrice 기반 VIX 공급체."""

    def get_latest_vix(self, target_date: date) -> Optional[float]:
        from macro.models import MarketIndex, MarketIndexPrice

        vix_index = MarketIndex.objects.filter(
            symbol__in=VIX_SYMBOLS,
            category=VIX_CATEGORY,
        ).first()
        if not vix_index:
            return None
        price = (
            MarketIndexPrice.objects.filter(
                index=vix_index,
                date__lte=target_date,
            )
            .order_by("-date")
            .values_list("close", flat=True)
            .first()
        )
        if price is None:
            return None
        return float(price)

    def get_vix_series(
        self, date_from: date, date_to: date
    ) -> list[Decimal]:
        from macro.models import MarketIndex, MarketIndexPrice

        vix_index = MarketIndex.objects.filter(
            symbol__in=VIX_SYMBOLS,
            category=VIX_CATEGORY,
        ).first()
        if not vix_index:
            return []
        return list(
            MarketIndexPrice.objects.filter(
                index=vix_index,
                date__gt=date_from,
                date__lte=date_to,
            )
            .order_by("date")
            .values_list("close", flat=True)
        )
