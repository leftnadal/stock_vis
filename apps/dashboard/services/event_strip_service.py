"""홈 이벤트 스트립 BFF 서비스 (EVT-IMPL-4 STEP 2-2).

동일 연합 읽기(build_event_feed)의 축소판 — dashboard 뷰가 monitor 서비스 import(B1,
dashboard→chain_sight 선례 동형). 창 = ET 오늘 .. +45일, scope=both.
성분 = 거시(critical·high) + 휴장 + 관심 어닝 티저(D-7 이내, 최대 2). 실패 격리: 예외 → {items: []}.
"""
from __future__ import annotations

import datetime as _dt
import logging
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")
_WINDOW_DAYS = 45
_TEASER_MAX = 2   # 관심 어닝 티저 상한
_TEASER_DDAY = 7  # D-7 이내
_ITEMS_MAX = 12


def build_event_strip(user) -> dict:
    """홈 스트립 응답 {as_of, window_days, items[≤12]}. 실패 시 {items: []}(FE 실패 격리 짝).

    구성(목업 S 시각 계약): 휴장·관심 어닝 티저(D-7 이내 ≤2)를 우선 보장하고, 남는 슬롯을
    거시(critical 우선 → high)로 채운다. 실데이터에서 거시가 조밀해 날짜순 단순 cap이 휴장·
    티저를 굶기는 것을 방지(계약의 '혼합' 준수). 최종 표시는 날짜 오름차순.
    """
    from apps.monitor.services.event_feed import build_event_feed

    et_today = _dt.datetime.now(tz=_ET).date()
    end = et_today + _dt.timedelta(days=_WINDOW_DAYS)
    try:
        feed = build_event_feed(
            user, start=et_today, end=end, scope="both",
            kinds={"macro", "holiday", "earnings"}, include_stale=False,
            macro_min_importance="high",
        )
        as_of = feed["as_of"]
        items = feed["items"]
        holidays = [it for it in items if it["kind"] == "holiday"]
        teasers = [
            it for it in items
            if it["kind"] == "earnings"
            and it.get("d_day") is not None and 0 <= it["d_day"] <= _TEASER_DDAY
        ][:_TEASER_MAX]
        # 거시: critical 우선, 그다음 high — 각 날짜 오름차순.
        macro_crit = [it for it in items if it["kind"] == "macro" and it["detail"].get("importance") == "critical"]
        macro_high = [it for it in items if it["kind"] == "macro" and it["detail"].get("importance") == "high"]

        selected = holidays + teasers
        remaining = _ITEMS_MAX - len(selected)
        if remaining > 0:
            selected += (macro_crit + macro_high)[:remaining]
        selected.sort(key=lambda it: (it["event_date_et"], it.get("event_time_et") or "", it["kind"]))
        return {"as_of": as_of, "window_days": _WINDOW_DAYS, "items": selected[:_ITEMS_MAX]}
    except Exception:
        logger.exception("build_event_strip 실패 — 빈 스트립 반환(FE 실패 격리)")
        return {"as_of": None, "window_days": _WINDOW_DAYS, "items": []}
