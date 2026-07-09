"""
C1 밸류에이션 — 원료 백필 + 조합/fetch 배선 (TH-10, 결정15=A) — 설계 앵커 §2 C1.

EV/Sales = enterprise_value ÷ revenue (동일 분기 라벨 강제). 순수함수 heat_components.
c1_valuation 재사용(§2 산식·부호 불변). 이 모듈은 데이터 계층(백필 + 섹터 중앙값 분기 z)만.

시점 정합 규칙(정본): EV(enterprise-values.date)와 revenue(income-statement 동일 date)를 **같은
fiscal_date 로만** 결합 — 라벨 불일치·미발표 분기 미저장(추정·직전 분기 대체 금지). 근사화되는
순간 우회로 전환되므로 완전 일치만 허용.
"""

import logging
import statistics
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Sequence

from apps.chain_sight.services.heat_components import c1_valuation, make_component

logger = logging.getLogger(__name__)

C1_MIN_QUARTERS = 8  # 3년 z 표본 하한(분기 단위 ≈ 2년). 미만 → 결측.


def _to_decimal(v: Any) -> Optional[Decimal]:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_date(v: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


def backfill_quarterly_valuation(client: Any, symbols: Sequence[str], limit: int = 16) -> dict:
    """EV + income(quarter) 동일 fiscal_date 매칭 → QuarterlyValuation 멱등 upsert."""
    from apps.chain_sight.models import QuarterlyValuation

    written = 0
    errors: dict[str, str] = {}
    for sym in [s.upper() for s in symbols]:
        evs = client.get_enterprise_values(sym, limit=limit)
        incs = client.get_income_statement(sym, period="quarter", limit=limit)
        ev_by: dict[date, Decimal] = {}
        for e in evs if isinstance(evs, list) else []:
            d = _parse_date(e.get("date"))
            if d is not None and e.get("enterpriseValue") is not None:
                ev_by[d] = _to_decimal(e.get("enterpriseValue"))
        inc_by: dict[date, Decimal] = {}
        for r in incs if isinstance(incs, list) else []:
            d = _parse_date(r.get("date"))
            if d is not None and r.get("revenue") is not None:
                inc_by[d] = _to_decimal(r.get("revenue"))

        matched = set(ev_by) & set(inc_by)  # 동일 fiscal_date 강제
        if not matched:
            errors[sym] = "no_matched_quarter"
            continue
        for d in matched:
            QuarterlyValuation.objects.update_or_create(
                symbol=sym, fiscal_date=d,
                defaults={"enterprise_value": ev_by[d], "revenue": inc_by[d]},
            )
            written += 1

    logger.info("QuarterlyValuation 백필: written=%d errors=%d", written, len(errors))
    return {"written": written, "errors": errors}


def _calendar_quarter(d: date) -> tuple[int, int]:
    return (d.year, (d.month - 1) // 3 + 1)


def c1_valuation_from_db(
    sector_symbols: Sequence[str], as_of: date, min_n: int = C1_MIN_QUARTERS
) -> dict:
    """
    QuarterlyValuation 위 C1 계산 (§2). 섹터 종목 EV/Sales 의 분기 중앙값 시계열 3년 z.

    캘린더 분기 버킷 → 각 분기 섹터 종목 EV/Sales 중앙값 → c1_valuation(current, history) 재사용.
    """
    from apps.chain_sight.models import QuarterlyValuation

    syms = [s.upper() for s in sector_symbols]
    if not syms:
        return make_component(None, raw=None, missing_reason="c1_no_symbols")

    rows = QuarterlyValuation.objects.filter(
        symbol__in=syms, fiscal_date__lte=as_of
    ).values("symbol", "fiscal_date", "enterprise_value", "revenue")

    # 캘린더 분기별 EV/Sales 값 수집
    by_quarter: dict[tuple, list[float]] = defaultdict(list)
    for r in rows:
        ev, rev = r["enterprise_value"], r["revenue"]
        if ev is None or rev is None or float(rev) <= 0:
            continue
        by_quarter[_calendar_quarter(r["fiscal_date"])].append(float(ev) / float(rev))

    if not by_quarter:
        return make_component(None, raw=None, missing_reason="c1_no_valuation")

    quarters = sorted(by_quarter)
    medians = [statistics.median(by_quarter[q]) for q in quarters]
    current = medians[-1]
    history = medians[:-1]
    return c1_valuation(current, history, min_n=min_n)
