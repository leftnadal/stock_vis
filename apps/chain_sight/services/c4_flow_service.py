"""
C4 ETF 플로우 — 콜드스타트 게이트 + fetch 배선 (TH-8, 결정13=C) — 설계 앵커 §2 C4 · §5.3 상수체계.

C4 = Σ(Δshares_out × NAV) 20일 이동합의 3년 z (§2). FMP shares_out 이력 부재로 EtfSnapshot
(TH-7c)을 일간 축적 → diff 시계열 자체 구성. 산식·부호는 순수함수 heat_components.c4_etf_flow
재사용(정본 불변). 이 모듈은 데이터 계층(diff 계수 게이트 + 시계열 조립)만.

결정13=C 게이트 (횡단 z 기각 — n=11 통계 부적격, 시계열 전용):
  - 유효 diff < 26            → §3-5 결측(c4_insufficient_history)
  - 26 ≤ 유효 diff < 60       → 확장 창 z(window = min(이력, 60), z_mode=time_series_expanding)
  - 유효 diff ≥ 60           → 정식 60 창 z(z_mode=time_series)
자동 수렴(데이터 도달 시 창 확장 → 정식), 재비준 지점 없음. 상수 26/60 = 결정7 체계 병기
(estimate_revision.Z_MODE_TS_THRESHOLD=26 과 동일 반년 표본 하한, 정식 창 60 = §2 3년 창의
시계열 표준화 창).
"""

import logging
from collections import defaultdict
from datetime import date
from typing import Optional, Sequence

from apps.chain_sight.services.heat_components import c4_etf_flow, make_component

logger = logging.getLogger(__name__)

C4_EXPAND_MIN = 26   # 유효 diff ≥ 26 → 확장 창 z (결정7 체계 병기 = 반년 표본 하한)
C4_WINDOW_FULL = 60  # 유효 diff ≥ 60 → 정식 창 z
FLOW_MA_WINDOW = 20  # §2 "20일 이동합"


def _sector_flow_series(
    primary_syms: Sequence[str], as_of: date
) -> tuple[list[date], dict]:
    """섹터 primary ETF들의 일간 플로우 Σ(Δshares_out × NAV) 를 날짜별 합산 → (dates, flow_by_date)."""
    from apps.chain_sight.models import EtfSnapshot

    rows = (
        EtfSnapshot.objects.filter(symbol__in=list(primary_syms), snapshot_date__lte=as_of)
        .order_by("snapshot_date")
        .values("symbol", "snapshot_date", "shares_outstanding", "nav")
    )
    by_sym: dict[str, list] = defaultdict(list)
    for r in rows:
        by_sym[r["symbol"]].append((r["snapshot_date"], r["shares_outstanding"], r["nav"]))

    flow_by_date: dict[date, float] = defaultdict(float)
    for _sym, seq in by_sym.items():
        for i in range(1, len(seq)):
            d, sh, nav = seq[i]
            _d0, sh0, _nav0 = seq[i - 1]
            if sh is None or sh0 is None or nav is None:
                continue
            flow_by_date[d] += float(sh - sh0) * float(nav)
    return sorted(flow_by_date), flow_by_date


def _rolling_ma_series(
    dates: list[date], flow_by_date: dict, window: int = FLOW_MA_WINDOW
) -> list[float]:
    """20일 이동합 시계열 (가용분 부분합 포함 — 결측 게이트는 diff 계수가 담당)."""
    flows = [flow_by_date[d] for d in dates]
    series = []
    for i in range(len(flows)):
        lo = max(0, i - window + 1)
        series.append(sum(flows[lo : i + 1]))
    return series


def c4_etf_flow_from_db(
    primary_syms: Sequence[str],
    as_of: date,
    expand_min: int = C4_EXPAND_MIN,
    window_full: int = C4_WINDOW_FULL,
) -> dict:
    """
    EtfSnapshot 위 C4 계산 + 결정13 콜드스타트 게이트. 순수함수 c4_etf_flow 재사용.

    반환 계약에 C4 전용 z_mode('time_series'|'time_series_expanding'|None) 추가.
    """
    pris = [s.upper() for s in primary_syms]
    if not pris:
        comp = make_component(None, raw=None, missing_reason="c4_no_primary_etf")
        comp["z_mode"] = None
        return comp

    dates, flow_by_date = _sector_flow_series(pris, as_of)
    valid_diff = len(dates)  # 유효 일간 diff 개수 (연속 스냅샷 쌍)

    if valid_diff < expand_min:
        comp = make_component(None, raw=None, missing_reason="c4_insufficient_history")
        comp["z_mode"] = None
        return comp

    series = _rolling_ma_series(dates, flow_by_date)
    win = min(valid_diff, window_full)
    current = series[-1]
    history = series[-win:-1]  # 표준화 창(current 제외)

    comp = c4_etf_flow(current, history, min_n=min(expand_min - 1, len(history)))
    comp["z_mode"] = (
        ("time_series" if valid_diff >= window_full else "time_series_expanding")
        if comp["z"] is not None
        else None
    )
    return comp
