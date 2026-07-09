"""
C4 ETF 플로우 원료 스냅샷 수집 (TH-7c, 결정11=A) — 설계 앵커 §2 C4 원료.

FMP Starter 는 shares_outstanding 이력을 주지 않으므로(TH-7 프로브 확정), 일간 스냅샷을
EtfSnapshot 에 직접 축적한다(EstimateSnapshot §6.6 전례). 이 서비스는 **원료 적립만** 하며
C4 산식/z/콜드스타트는 TH-C4-COLDSTART 비준 후 별도 배선한다.

가드(설계 관례 = 유니버스/필링 수집과 동형): 심볼별 필드 검증(shares_out>0 · nav>0)을
통과한 행만 DB 접촉. 결측·이상 심볼은 skip(개별 격리, 부분 저장 금지). 멱등 upsert
(update_or_create(symbol, snapshot_date)) — 같은 날 재수집 = 무변화.
"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)


def _to_decimal(value: Any) -> Optional[Decimal]:
    """FMP 응답값(문자열/실수/None) → Decimal. 파싱 불능·None → None."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def snapshot_etf_metrics(
    client: Any,
    symbols: Iterable[str],
    snapshot_date: date,
) -> dict:
    """
    대상 ETF 심볼들의 shares_out·nav·aum 현재 스냅샷을 수집해 EtfSnapshot 에 멱등 적립.

    - client: FMPClient (get_etf_shares_float / get_etf_info).
    - 가드: shares_out·nav 둘 다 유효(양수)여야 저장 (C4 산식 = Σ(Δshares_out×NAV)는 둘 다
      필요 — 반쪽 원료 금지). aum 은 보조(nullable).
    - 반환 = {created, updated, skipped, stored_symbols, skipped_symbols}.
    """
    from apps.chain_sight.models import EtfSnapshot

    syms = [s.upper() for s in symbols]
    created = updated = skipped = 0
    stored_symbols: list[str] = []
    skipped_symbols: list[str] = []

    for sym in syms:
        sf = client.get_etf_shares_float(sym) or {}
        info = client.get_etf_info(sym) or {}

        shares = _to_decimal(sf.get("outstandingShares"))
        nav = _to_decimal(info.get("nav"))
        aum = _to_decimal(info.get("assetsUnderManagement"))

        # 필드 가드 — 반쪽 원료(부분 저장) 금지, 개별 격리 skip.
        if shares is None or shares <= 0 or nav is None or nav <= 0:
            skipped += 1
            skipped_symbols.append(sym)
            logger.warning(
                "EtfSnapshot skip(가드): %s shares=%s nav=%s (DB 무접촉)",
                sym, shares, nav,
            )
            continue

        _obj, is_created = EtfSnapshot.objects.update_or_create(
            symbol=sym,
            snapshot_date=snapshot_date,
            defaults={"shares_outstanding": shares, "nav": nav, "aum": aum},
        )
        stored_symbols.append(sym)
        if is_created:
            created += 1
        else:
            updated += 1

    logger.info(
        "EtfSnapshot 수집 %s: created=%d updated=%d skipped=%d (대상 %d)",
        snapshot_date, created, updated, skipped, len(syms),
    )
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "stored_symbols": stored_symbols,
        "skipped_symbols": skipped_symbols,
    }


def active_primary_etf_symbols() -> list[str]:
    """C4 원료 수집 대상 = ThemeEtfMap active primary(섹터 SPDR 11종 원본). 정렬 고정."""
    from apps.chain_sight.models import ThemeEtfMap

    return sorted(
        ThemeEtfMap.objects.filter(active=True, role="primary")
        .values_list("etf_symbol", flat=True)
        .distinct()
    )
