"""
FX 수집·조회 서비스 (packages/shared/fx).

- 수집: shared FMP 래퍼(FMPClient) 경유만 — 외부 직접 호출 금지.
- 조회: `get_spot_rate`(최근 영업일 fallback) = portfolio가 소비할 유일한 이음새.
- shared 내부(api_request)만 import — apps.* import 0(한 방향 규칙).
"""

from __future__ import annotations

import logging
import os
from datetime import date as date_cls
from decimal import Decimal

from django.db import transaction

from packages.shared.fx.models import ExchangeRate

logger = logging.getLogger(__name__)

DEFAULT_PAIR = "USDKRW"
# FMP historical-price-eod에 넣는 forex 심볼(pair와 동일 표기).
_FMP_SYMBOL = {"USDKRW": "USDKRW"}


def _fmp_client():
    from packages.shared.api_request.providers.fmp.client import FMPClient

    return FMPClient(api_key=os.getenv("FMP_API_KEY"))


def fetch_rate_rows(pair: str = DEFAULT_PAIR) -> list[dict]:
    """FMP에서 통화쌍 과거 일간 시계열을 [{date, close}, ...]로 반환(수집 전용)."""
    symbol = _FMP_SYMBOL.get(pair, pair)
    client = _fmp_client()
    data = client.get_historical_price(symbol)
    rows = data if isinstance(data, list) else (data or {}).get("historical", [])
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        d, c = r.get("date"), r.get("close")
        if d and c is not None:
            out.append({"date": d, "close": Decimal(str(c))})
    return out


@transaction.atomic
def backfill_rates(pair: str = DEFAULT_PAIR) -> dict:
    """과거 시계열을 ExchangeRate에 적재. 재실행 idempotent(update_or_create)."""
    rows = fetch_rate_rows(pair)
    created, updated = 0, 0
    for row in rows:
        _, is_new = ExchangeRate.objects.update_or_create(
            pair=pair,
            date=row["date"],
            defaults={"close": row["close"], "source": "fmp"},
        )
        created += int(is_new)
        updated += int(not is_new)
    logger.info("fx backfill %s: created=%d updated=%d", pair, created, updated)
    return {"pair": pair, "fetched": len(rows), "created": created, "updated": updated}


def get_rate_on(target: date_cls, pair: str = DEFAULT_PAIR) -> Decimal | None:
    """특정 일자의 환율. 휴장일이면 그 이전 가장 가까운 영업일 환율(fallback)."""
    row = (
        ExchangeRate.objects.filter(pair=pair, date__lte=target)
        .order_by("-date")
        .values_list("close", flat=True)
        .first()
    )
    return Decimal(row) if row is not None else None


def get_spot_rate(pair: str = DEFAULT_PAIR) -> Decimal | None:
    """현재 환율 = 저장된 최신 영업일 종가. portfolio 소비 이음새."""
    row = (
        ExchangeRate.objects.filter(pair=pair)
        .order_by("-date")
        .values_list("close", flat=True)
        .first()
    )
    return Decimal(row) if row is not None else None


def oldest_available(pair: str = DEFAULT_PAIR) -> Decimal | None:
    """백필 창에서 가장 오래된 환율(창 밖 매수의 approx_low_confidence용)."""
    row = (
        ExchangeRate.objects.filter(pair=pair)
        .order_by("date")
        .values_list("close", flat=True)
        .first()
    )
    return Decimal(row) if row is not None else None
