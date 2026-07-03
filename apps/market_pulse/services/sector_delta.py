"""MP2-DELTA 슬라이스 1 — 섹터 순위 어제 대비 델타 (조회-시 무상태 파생).

D-DELTA-CALC(후보 A): 요청마다 최근 2 distinct 스냅샷 날짜를 읽어 rank 델타 계산.
  저장·캐시·마이그레이션 0 (prod 쓰기 0). 선례 = overview `_ticker_bar`의 [:2] change_pct.
D-DELTA-YDAY: "어제" = 직전 distinct 스냅샷 날짜(calendar −1 아님, 주말·휴장 갭 자동 흡수).
"""
from __future__ import annotations

from datetime import date as date_cls
from typing import Any

from apps.market_pulse.models.snapshot import SectorFlowSnapshot


def compute_sector_deltas(today: date_cls) -> list[dict[str, Any]]:
    """오늘 vs 직전 distinct 스냅샷 날짜의 섹터 순위 변동.

    반환: |rank_delta| 내림차순 리스트. 절삭(상위 N)은 FE 소관.
      rank_delta > 0 = 순위 상승(숫자 작아짐). as_of/vs_date는 서버 실날짜(ISO).
    데이터 1날짜뿐 → 빈 리스트(예외 아님). 어제 없던 섹터 → 제외(델타 날조 금지).
    """
    dates = list(
        SectorFlowSnapshot.objects.filter(date__lte=today)
        .values_list("date", flat=True)
        .distinct()
        .order_by("-date")[:2]
    )
    if len(dates) < 2:
        return []
    curr_d, prev_d = dates[0], dates[1]
    curr = {
        r.market_index_id: r
        for r in SectorFlowSnapshot.objects.filter(date=curr_d)
    }
    prev = {
        r.market_index_id: r
        for r in SectorFlowSnapshot.objects.filter(date=prev_d)
    }
    out: list[dict[str, Any]] = []
    for sym, snap in curr.items():
        p = prev.get(sym)
        if p is None:
            continue  # 어제 없던 섹터 → 델타 산출 불가, 제외
        delta = p.rank_in_universe - snap.rank_in_universe  # 양수 = 순위 상승
        out.append(
            {
                "sector": sym,
                "rank": snap.rank_in_universe,
                "prev_rank": p.rank_in_universe,
                "rank_delta": delta,
                "as_of": curr_d.isoformat(),
                "vs_date": prev_d.isoformat(),
            }
        )
    out.sort(key=lambda x: abs(x["rank_delta"]), reverse=True)
    return out
