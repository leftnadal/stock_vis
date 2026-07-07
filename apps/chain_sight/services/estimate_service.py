"""
C8 원장 스냅샷 서비스 (TH-3) — FMP analyst-estimates → EstimateSnapshot.

설계서 theme_heat_design.md v1.2.1 §5.3 · §6.6:
- FMP annual estimates 에는 **리비전 타임스탬프가 없다** → 엔드포인트는 컨센서스 스냅샷
  공급원이고, 리비전 시계열은 우리가 **주간 스냅샷(EstimateSnapshot) → 60일 diff** 로 생성.
- **콜드 스타트**: 백필 불가(과거 컨센서스 재구성 불능) → Cycle 1 첫 배포일부터 스냅샷 축적
  시작(시계를 최대한 앞당김). C8 계산은 60일 축적 후(크로스섹셔널 z) → 365일 후(시계열 z).
- 저장 단위 = (symbol, snapshot_date, fiscal_year) — **당기·차기 연도별 행**(§6.6).

필드 매핑 (2026-07-08 전건 대조 = 8/8 일치):
  symbol←symbol / snapshot_date←수집일(금) / fiscal_year←year(date) /
  eps_avg←epsAvg / eps_high←epsHigh / eps_low←epsLow /
  num_analysts_eps←numAnalystsEps / revenue_avg←revenueAvg.

본 슬라이스 = **스냅샷 수집만**(콜드 스타트 시계 기동). C8 계산(diff+z_mode)은 후속 슬라이스.
"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

from apps.chain_sight.models import EstimateSnapshot

logger = logging.getLogger(__name__)


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _fiscal_year(row: dict) -> Optional[int]:
    """date(대상기간 종료일, 예 '2027-09-27')에서 회계연도 추출."""
    d = str(row.get("date") or "")[:4]
    return int(d) if d.isdigit() else None


def select_current_and_next(rows: list[dict], as_of_year: int) -> list[dict]:
    """
    당기·차기 회계연도 행만 추림 (§6.6 "당기·차기 연도별 행").

    당기 = as_of_year 이상 최소 연도, 차기 = 그 다음 연도. FMP 는 미래연도만 줄 수도
    있으므로(예 AAPL 2027~) as_of_year 이상 중 가장 작은 2개를 당기·차기로 본다.
    """
    dated = [(fy, r) for r in rows if (fy := _fiscal_year(r)) is not None]
    future = sorted((fr for fr in dated if fr[0] >= as_of_year), key=lambda x: x[0])
    return [r for _, r in future[:2]]


def snapshot_symbol(client, symbol: str, snapshot_date: date) -> dict:
    """
    한 종목 컨센서스를 당기·차기 2행으로 EstimateSnapshot upsert (멱등).

    반환 = {created, updated, rows}. FMP 데이터 없으면 rows=0.
    """
    rows = client.get_analyst_estimates(symbol, period="annual", limit=10)
    if not rows:
        return {"created": 0, "updated": 0, "rows": 0}

    picked = select_current_and_next(rows, snapshot_date.year)
    created = updated = 0
    for r in picked:
        fy = _fiscal_year(r)
        if fy is None:
            continue
        _, was_created = EstimateSnapshot.objects.update_or_create(
            symbol=symbol.upper(),
            snapshot_date=snapshot_date,
            fiscal_year=fy,
            defaults={
                "eps_avg": _to_decimal(r.get("epsAvg")),
                "eps_high": _to_decimal(r.get("epsHigh")),
                "eps_low": _to_decimal(r.get("epsLow")),
                "num_analysts_eps": r.get("numAnalystsEps") or None,
                "revenue_avg": _to_decimal(r.get("revenueAvg")),
            },
        )
        created += was_created
        updated += not was_created
    return {"created": created, "updated": updated, "rows": len(picked)}


def snapshot_estimates_for_symbols(
    client, symbols: Iterable[str], snapshot_date: date
) -> dict:
    """
    유니버스 전종목 컨센서스 주간 스냅샷 (§5.3). 성분별 try/except 격리. 멱등.
    """
    agg = {"symbols": 0, "created": 0, "updated": 0, "no_data": 0, "errors": 0}
    for sym in symbols:
        agg["symbols"] += 1
        try:
            res = snapshot_symbol(client, sym, snapshot_date)
            agg["created"] += res["created"]
            agg["updated"] += res["updated"]
            if res["rows"] == 0:
                agg["no_data"] += 1
        except Exception as e:  # noqa: BLE001 — 종목 실패 격리
            agg["errors"] += 1
            logger.warning("EstimateSnapshot %s 실패: %s", sym, e)
    return agg
