"""MacroVIXProvider — VIXProvider 포트의 macro.models 기반 구현.

apps/market_pulse가 macro.models를 import하는 것은 합법(app→app).
shared/eod 코드는 이 클래스를 직접 알지 못하고 포트만 사용한다.

행위보존: 기존 eod_pipeline._get_vix_value, eod_regime_calculator._calculate_regime
이 사용하던 쿼리·반환 타입을 그대로 옮긴다.
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
