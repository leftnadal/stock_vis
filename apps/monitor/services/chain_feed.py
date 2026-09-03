"""관계망 이벤트 피드 (EVT-CHAIN-1, Phase 2 슬라이스 1).

설계 앵커 v1.1 §6 / 시각 계약 docs/design/evt_chain_mockup_b.html.
RelationConfidence(apps.chain_sight) ⋈ CalendarEvent(shared) — Postgres 단독 조인, Neo4j 무관.

B1 위치 규율: apps→app/shared 읽기만(event_feed 동형). shared 무수정.
연합 읽기 재사용: event_feed._build_calendar_items로 EventItem DTO(P1-ii 신뢰 라벨·d_day) 재사용.

부호 중립 하드 규칙(§6): 방향/센티먼트 필드 생성 금지 — neighbors/items에 relation_type + truth_score만.
canonical_direction·호재/악재 판단은 DTO에 존재 자체가 위반.
"""
from __future__ import annotations

import datetime as _dt

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from apps.monitor.services.event_feed import (
    _ET,
    _build_calendar_items,
)

# ── 잠정 파라미터 (D-EVT-CHAIN-THRESH — [EVT-OBS-3] 관찰 게이트에서 확정) ──
# 이 상수 1곳만 바뀌도록 집중. truth_min은 D-RC-SCALE로 도메인 [0,1] 전환됨:
# 지시서 "truth_score ≥ 85"의 신눈금 등가 = 0.85 (§0-4⑴ 실측 max=0.85·전건 score_version 3.0).
CHAIN_PARAMS = {
    "truth_min": 0.85,
    "relation_status": "confirmed",
    "top_k": 10,
    "propagate_kinds": ("EARNINGS",),  # 전파 = 어닝만 (배당·분할 off)
    "after_days": 90,                  # 시드 다음 이벤트 없을 때 창 = 오늘 + N일
    "seed_horizon_days": 200,          # 시드 자신 다음 어닝/배당 탐색 지평
    "truth_domain": [0.0, 1.0],        # FE 눈금 표기용(× 100)
}

_CACHE_KEY = "monitor:chain_feed:v1:{symbol}"
_CACHE_TTL = 15 * 60  # 15분 (event_feed 선례)

_SEED_KINDS = {"earnings", "dividend"}  # 위젯 pill 재료


def _et_today() -> _dt.date:
    return timezone.now().astimezone(_ET).date()


def _neighbors(symbol: str) -> list[dict]:
    """RelationConfidence에서 (symbol_a=시드 OR symbol_b=시드) AND confirmed AND truth≥임계.

    truth_score 내림차순 top-k. 상대 심볼 정규화(시드가 a든 b든 상대편).
    반환 = [{symbol, relation_type, truth_score}] — 부호 중립(direction 필드 없음).
    """
    from apps.chain_sight.models.relation_discovery import RelationConfidence

    rows = (
        RelationConfidence.objects.filter(
            Q(symbol_a=symbol) | Q(symbol_b=symbol),
            relation_status=CHAIN_PARAMS["relation_status"],
            truth_score__gte=CHAIN_PARAMS["truth_min"],
        )
        .order_by("-truth_score", "id")
        .values("symbol_a", "symbol_b", "relation_type", "truth_score")[: CHAIN_PARAMS["top_k"]]
    )
    out: list[dict] = []
    for r in rows:
        other = r["symbol_b"] if r["symbol_a"] == symbol else r["symbol_a"]
        out.append(
            {
                "symbol": other,
                "relation_type": r["relation_type"],
                "truth_score": r["truth_score"],
            }
        )
    return out


def build_chain_feed(user, symbol: str) -> dict:
    """관계망 이벤트 피드. 사용자 무관(심볼 키 데이터) — user는 시그니처 일관성용.

    반환(JSON 직렬화·캐시 안전):
      {seed, as_of, seed_events[], seed_next_event, neighbors[], items[], after_count, params}
    """
    symbol = (symbol or "").upper()
    if not symbol:
        return _empty(symbol)

    key = _CACHE_KEY.format(symbol=symbol)
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = _assemble(symbol)
    cache.set(key, result, _CACHE_TTL)
    return result


def _empty(symbol: str) -> dict:
    return {
        "seed": symbol,
        "as_of": timezone.now().astimezone(_ET).isoformat(),
        "seed_events": [],
        "seed_next_event": None,
        "neighbors": [],
        "items": [],
        "after_count": 0,
        "params": _params_public(),
    }


def _params_public() -> dict:
    p = dict(CHAIN_PARAMS)
    p["propagate_kinds"] = list(CHAIN_PARAMS["propagate_kinds"])
    return p


def _assemble(symbol: str) -> dict:
    et_today = _et_today()

    # ── 시드 자신의 다음 어닝/배당 (W 위젯 pill · 연합 읽기 재사용) ──
    seed_horizon = et_today + _dt.timedelta(days=CHAIN_PARAMS["seed_horizon_days"])
    seed_all = _build_calendar_items(
        {symbol}, et_today, seed_horizon, et_today, set(), set(), include_stale=False
    )
    seed_evts = sorted(
        (it for it in seed_all if it.kind in _SEED_KINDS),
        key=lambda it: (it.event_date_et, it._sort_time),
    )
    seed_next = seed_evts[0] if seed_evts else None

    # ── 타임라인 창: 오늘 → 시드 다음 이벤트일 (없으면 오늘 + after_days) ──
    if seed_next is not None:
        window_end = seed_next.event_date_et
    else:
        window_end = et_today + _dt.timedelta(days=CHAIN_PARAMS["after_days"])

    # ── 이웃 (관계 엣지 top-k) ──
    neighbors = _neighbors(symbol)
    if not neighbors:
        # 이웃 0 → 타임라인 섹션 비표시(FE). 위젯(seed_events)은 유지.
        result = _empty(symbol)
        result["seed_events"] = [it.as_dict() for it in seed_evts]
        result["seed_next_event"] = _seed_next_dict(seed_next)
        return result

    # 이웃 심볼별 대표 관계(최고 truth) — items 뱃지용
    best_rel: dict[str, dict] = {}
    for n in neighbors:
        cur = best_rel.get(n["symbol"])
        if cur is None or n["truth_score"] > cur["truth_score"]:
            best_rel[n["symbol"]] = {"type": n["relation_type"], "truth_score": n["truth_score"]}
    nbr_syms = set(best_rel.keys())

    # ── items: 창 내 이웃 어닝 (EventItem 재사용 + relation 확장) ──
    after_end = et_today + _dt.timedelta(days=CHAIN_PARAMS["after_days"])
    nbr_events = _build_calendar_items(
        nbr_syms, et_today, after_end, et_today, set(), set(), include_stale=False
    )
    earnings = [it for it in nbr_events if it.kind == "earnings"]

    items: list[dict] = []
    after_count = 0
    for it in sorted(earnings, key=lambda x: (x.event_date_et, x.symbol or "")):
        if it.event_date_et <= window_end:
            d = it.as_dict()
            d["relation"] = best_rel.get(it.symbol)  # {type, truth_score} — 부호 중립
            items.append(d)
        else:
            after_count += 1  # 창 이후 ~ 오늘+after_days 이웃 어닝

    return {
        "seed": symbol,
        "as_of": timezone.now().astimezone(_ET).isoformat(),
        "seed_events": [it.as_dict() for it in seed_evts],
        "seed_next_event": _seed_next_dict(seed_next),
        "neighbors": neighbors,
        "items": items,
        "after_count": after_count,
        "params": _params_public(),
    }


def _seed_next_dict(seed_next) -> dict | None:
    if seed_next is None:
        return None
    return {
        "kind": seed_next.kind,
        "event_date_et": seed_next.event_date_et.isoformat(),
        "d_day": seed_next.d_day,
    }
