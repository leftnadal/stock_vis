"""연합 이벤트 읽기 서비스 (EVT-IMPL-4 STEP 1, D-EVT-4B=B1 단일 구현).

4원천(CalendarEvent · EconomicEvent · StockSplit · trading_calendar)을 사용자 관심종목
스코프로 병합해 읽기 전용 피드(EventFeed)를 만든다. 사실 원장은 앱 중립(shared)이며 여기서
해석·필터·파생(서프라이즈·날짜신뢰·KST·D-day)한다. 저장 없음(P1-i surprise·P1-ii trust 모두 파생).

경계: 이 모듈은 apps→app/shared 읽기만 한다(app→app: dashboard 스트립 뷰가 이 모듈을 import,
dashboard→chain_sight 선례와 동형). shared는 무수정(shared→apps 0 유지).

스코프 규약(D-EVT-4A=A3): 관심종목 = Monitor(scope=stock) ∪ WatchlistItem(사용자 스코프).
user_id 필수 — SFI-I1 글로벌 무필터 결함(DECISIONS:6587) 재발 금지. 수집 원장은 전량,
필터는 이 읽기 계층에서만(D-EVT-SCOPE-U).
"""
from __future__ import annotations

import datetime as _dt
import logging
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")
_KST = ZoneInfo("Asia/Seoul")

# 날짜 안정 임계 N (P1-ii). EVT-IMPL-4 §0-5⑵ 재측정: scheduled date_observed_count p50=7.
# N = max(3, round(p50)) = 7. (count=7 대량 스파이크 = 시드 백필 흔적 → 7은 보수적 안정 기준.)
STABLE_N = 7

# earnings 세션 대표시각(ET) — FMP 응답에 시각 원천 없음(EVT-SESSION), KST 변환·정렬용 대표값.
_BMO_TIME = _dt.time(8, 0)
_AMC_TIME = _dt.time(16, 30)

# kind 정렬 순서(1-1): holiday → macro → earnings → dividend → split → split_effective
_KIND_ORDER = {
    "holiday": 0, "macro": 1, "earnings": 2,
    "dividend": 3, "split": 4, "split_effective": 5,
}
_IMPORTANCE_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}

_CACHE_KEY = "monitor:event_feed:v1:user:{uid}:{start}:{end}:{scope}:{kinds}:{stale}:{imp}"
_CACHE_TTL = 15 * 60  # 15분 (strip_service 선례)

_ALL_KINDS = ("holiday", "macro", "earnings", "dividend", "split", "split_effective")


@dataclass
class EventItem:
    """단일 이벤트 표시 계약(§4). JSON 직렬화 = as_dict()."""
    kind: str
    symbol: str | None
    title: str
    event_date_et: _dt.date
    event_time_et: str | None
    session: str | None
    event_dt_kst: str | None
    d_day: int
    badges: list[str]
    detail: dict
    surprise: dict | None
    date_trust: str | None
    date_observed_count: int | None
    sources: list[str]
    status: str
    _sort_time: _dt.time = field(default=_dt.time(0, 0), repr=False)

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "symbol": self.symbol,
            "title": self.title,
            "event_date_et": self.event_date_et.isoformat(),
            "event_time_et": self.event_time_et,
            "session": self.session,
            "event_dt_kst": self.event_dt_kst,
            "d_day": self.d_day,
            "badges": self.badges,
            "detail": self.detail,
            "surprise": self.surprise,
            "date_trust": self.date_trust,
            "date_observed_count": self.date_observed_count,
            "sources": self.sources,
            "status": self.status,
        }


@dataclass
class EventFeed:
    as_of: str
    start: _dt.date
    end: _dt.date
    scope: str
    symbols: dict
    counts: dict
    items: list[EventItem]

    def as_dict(self) -> dict:
        return {
            "as_of": self.as_of,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "scope": self.scope,
            "symbols": self.symbols,
            "counts": self.counts,
            "items": [it.as_dict() for it in self.items],
        }


# ────────────────────────── 심볼 집합 ──────────────────────────
def _resolve_symbols(user) -> tuple[set[str], set[str]]:
    """(monitor_syms, watchlist_syms). 둘 다 대문자. user 스코프 필수."""
    from apps.monitor.models.monitor import Monitor
    from packages.shared.users.models import WatchlistItem

    mon = {
        s.upper()
        for s in Monitor.objects.filter(
            user=user,
            scope=Monitor.Scope.STOCK,
            status__in=[Monitor.Status.ACTIVE, Monitor.Status.SETTING_UP, Monitor.Status.PAUSED],
        ).values_list("target_ref", flat=True)
        if s
    }
    wl = {
        s.upper()
        for s in WatchlistItem.objects.filter(watchlist__user=user).values_list("stock_id", flat=True)
        if s
    }
    return mon, wl


# ────────────────────────── 파싱·변환 헬퍼 ──────────────────────────
def _f(d):
    return float(d) if d is not None else None


def _parse_numeric(s):
    """거시 문자열 값 → float. %·쉼표·단위(K/M/B/T) 제거. 실패 시 None."""
    if s is None:
        return None
    t = str(s).strip().replace("%", "").replace(",", "").replace("+", "")
    if not t:
        return None
    mult = 1.0
    if t and t[-1] in "KkMmBbTt":
        mult = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}[t[-1].lower()]
        t = t[:-1].strip()
    try:
        return float(t) * mult
    except (ValueError, TypeError):
        return None


def _surprise(actual, estimated):
    """(actual, estimated) 숫자 → {pct, direction} | None. |estimated|>0 필요."""
    if actual is None or estimated is None or abs(estimated) == 0:
        return None
    pct = round((actual - estimated) / abs(estimated) * 100, 1)
    direction = "beat" if pct > 0 else ("miss" if pct < 0 else "flat")
    return {"pct": pct, "direction": direction}


def _kst_iso(date_et: _dt.date, time_et: _dt.time | None) -> str | None:
    """ET 날짜+대표시각 → KST ISO. 시각 없으면 None(날짜만 = FE가 'KST 익일' 규칙 표기)."""
    if time_et is None:
        return None
    et_dt = _dt.datetime.combine(date_et, time_et, tzinfo=_ET)
    return et_dt.astimezone(_KST).isoformat()


def _trust(status: str, doc_count: int | None) -> str:
    if status == "stale":
        return "unconfirmed"
    if doc_count is not None and doc_count >= STABLE_N:
        return "stable"
    return "fluid"


def _sources_for(symbol: str, mon: set[str], wl: set[str]) -> list[str]:
    out = []
    if symbol in mon:
        out.append("monitor")
    if symbol in wl:
        out.append("watchlist")
    return out


# ────────────────────────── 성분별 빌더 ──────────────────────────
def _build_calendar_items(syms, start, end, et_today, mon, wl, include_stale) -> list[EventItem]:
    """원천 ①: CalendarEvent(earnings/dividend/split). status scheduled/occurred(+stale 옵션)."""
    from packages.shared.stocks.models import CalendarEvent

    if not syms:
        return []
    statuses = [CalendarEvent.Status.SCHEDULED, CalendarEvent.Status.OCCURRED]
    if include_stale:
        statuses.append(CalendarEvent.Status.STALE)

    type_kind = {
        CalendarEvent.EventType.EARNINGS: "earnings",
        CalendarEvent.EventType.DIVIDEND: "dividend",
        CalendarEvent.EventType.SPLIT: "split",
    }
    label = {"earnings": "어닝", "dividend": "배당락", "split": "분할 예정"}
    items: list[EventItem] = []
    qs = CalendarEvent.objects.filter(
        symbol__in=syms, event_date__gte=start, event_date__lte=end, status__in=statuses,
    )
    for ev in qs:
        kind = type_kind[ev.event_type]
        session = None
        time_et = None
        rep_time = None
        detail: dict = {}
        surprise = None
        if kind == "earnings":
            if ev.session in ("BMO", "AMC"):
                session = ev.session
                rep_time = _BMO_TIME if ev.session == "BMO" else _AMC_TIME
            detail = {
                "eps_estimated": _f(ev.eps_estimated),
                "eps_actual": _f(ev.eps_actual),
                "revenue_estimated": _f(ev.revenue_estimated),
                "revenue_actual": _f(ev.revenue_actual),
            }
            surprise = _surprise(_f(ev.eps_actual), _f(ev.eps_estimated))
        elif kind == "dividend":
            detail = {
                "dividend_amount": _f(ev.dividend_amount),
                "payment_date": ev.payment_date.isoformat() if ev.payment_date else None,
                "record_date": ev.record_date.isoformat() if ev.record_date else None,
                "frequency": ev.frequency or "",
            }
        else:  # split
            detail = {"numerator": _f(ev.split_numerator), "denominator": _f(ev.split_denominator)}

        items.append(EventItem(
            kind=kind,
            symbol=ev.symbol,
            title=f"{ev.symbol} {label[kind]}",
            event_date_et=ev.event_date,
            event_time_et=None,  # 세션 주도(시각 원천 없음)
            session=session,
            event_dt_kst=_kst_iso(ev.event_date, rep_time),
            d_day=(ev.event_date - et_today).days,
            badges=(["today"] if ev.event_date == et_today else []),
            detail=detail,
            surprise=surprise,
            date_trust=_trust(ev.status, ev.date_observed_count),
            date_observed_count=ev.date_observed_count,
            sources=_sources_for(ev.symbol, mon, wl),
            status=ev.status,
            _sort_time=rep_time or _dt.time(0, 0),
        ))
    return items


def _build_macro_items(start, end, et_today, min_importance) -> list[EventItem]:
    """원천 ②: EconomicEvent(country=US, importance≥min). 심볼 없음."""
    from macro.models.indicators import EconomicEvent

    min_rank = _IMPORTANCE_RANK.get(min_importance, 3)
    allowed = [k for k, r in _IMPORTANCE_RANK.items() if r >= min_rank]
    items: list[EventItem] = []
    qs = EconomicEvent.objects.filter(
        country="US", event_date__gte=start, event_date__lte=end, importance__in=allowed,
    )
    for ev in qs:
        time_et = ev.event_time.strftime("%H:%M") if ev.event_time else None
        rep_time = ev.event_time if ev.event_time else None
        surprise = _surprise(_parse_numeric(ev.actual_value), _parse_numeric(ev.forecast_value))
        badges = [ev.importance]
        if ev.event_date == et_today:
            badges.append("today")
        items.append(EventItem(
            kind="macro",
            symbol=None,
            title=ev.title_ko or ev.title,
            event_date_et=ev.event_date,
            event_time_et=time_et,
            session=None,
            event_dt_kst=_kst_iso(ev.event_date, rep_time),
            d_day=(ev.event_date - et_today).days,
            badges=badges,
            detail={
                "importance": ev.importance,
                "forecast_value": ev.forecast_value or None,
                "previous_value": ev.previous_value or None,
                "actual_value": ev.actual_value or None,
                "country": ev.country,
            },
            surprise=surprise,
            date_trust=None,
            date_observed_count=None,
            sources=[],
            status=("occurred" if ev.event_date < et_today else "scheduled"),
            _sort_time=rep_time or _dt.time(0, 0),
        ))
    return items


def _build_split_effective_items(syms, start, end, et_today, mon, wl) -> list[EventItem]:
    """원천 ③: StockSplit(발효·사후, 참고 표시). kind=split_effective."""
    from packages.shared.stocks.models import StockSplit

    if not syms:
        return []
    items: list[EventItem] = []
    qs = StockSplit.objects.filter(
        stock_id__in=syms, date__gte=start, date__lte=end,
    ).select_related(None)
    for sp in qs:
        sym = sp.stock_id.upper()
        items.append(EventItem(
            kind="split_effective",
            symbol=sym,
            title=f"{sym} 분할 발효",
            event_date_et=sp.date,
            event_time_et=None,
            session=None,
            event_dt_kst=None,
            d_day=(sp.date - et_today).days,
            badges=(["today"] if sp.date == et_today else []),
            detail={"numerator": _f(sp.numerator), "denominator": _f(sp.denominator)},
            surprise=None,
            date_trust=None,
            date_observed_count=None,
            sources=_sources_for(sym, mon, wl),
            status=("occurred" if sp.date < et_today else "scheduled"),
            _sort_time=_dt.time(0, 0),
        ))
    return items


def _build_holiday_items(start, end, et_today) -> list[EventItem]:
    """원천 ④: trading_calendar 휴장일. 날짜만(이름 원천 없음 → 'NYSE 휴장')."""
    from apps.credit_signals.trading_calendar import (
        ALL_NYSE_HOLIDAYS,
        CalendarCoverageError,
        next_trading_day,
        warn_if_coverage_expiring,
    )

    warn_if_coverage_expiring(et_today)  # 커버리지 만료 임박 경보(로그, 1-3 ④)
    items: list[EventItem] = []
    for h in sorted(ALL_NYSE_HOLIDAYS):
        if not (start <= h <= end):
            continue
        try:
            ntd = next_trading_day(h).isoformat()
        except CalendarCoverageError:
            ntd = None
        items.append(EventItem(
            kind="holiday",
            symbol=None,
            title="NYSE 휴장",
            event_date_et=h,
            event_time_et=None,
            session=None,
            event_dt_kst=None,
            d_day=(h - et_today).days,
            badges=(["today"] if h == et_today else []),
            detail={"name": None, "next_trading_day": ntd},
            surprise=None,
            date_trust=None,
            date_observed_count=None,
            sources=[],
            status=("occurred" if h < et_today else "scheduled"),
            _sort_time=_dt.time(0, 0),
        ))
    return items


# ────────────────────────── 공개 API ──────────────────────────
def build_event_feed(
    user,
    *,
    start: _dt.date,
    end: _dt.date,
    scope: str = "monitor",
    kinds: set[str] | None = None,
    include_stale: bool = False,
    macro_min_importance: str = "high",
) -> dict:
    """연합 읽기 피드. 반환 = EventFeed.as_dict()(JSON 직렬화·캐시 안전).

    scope: monitor | watchlist | both — 심볼 기반 성분(earnings/div/split/split_eff)의 대상 집합.
           macro/holiday는 스코프 무관(항상 포함, kinds 필터만 적용).
    kinds: None=전체. 아니면 해당 kind만.
    include_stale: CalendarEvent stale 행 포함 여부(기본 제외).
    """
    uid = getattr(user, "id", None) or "anon"
    kinds_key = ",".join(sorted(kinds)) if kinds else "all"
    key = _CACHE_KEY.format(
        uid=uid, start=start.isoformat(), end=end.isoformat(), scope=scope,
        kinds=kinds_key, stale=int(include_stale), imp=macro_min_importance,
    )
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = _assemble(
        user, start=start, end=end, scope=scope, kinds=kinds,
        include_stale=include_stale, macro_min_importance=macro_min_importance,
    )
    cache.set(key, result, _CACHE_TTL)
    return result


def _assemble(user, *, start, end, scope, kinds, include_stale, macro_min_importance) -> dict:
    et_today = timezone.now().astimezone(_ET).date()
    as_of = timezone.now().astimezone(_ET).isoformat()

    mon, wl = _resolve_symbols(user)
    if scope == "watchlist":
        query_syms = wl
    elif scope == "both":
        query_syms = mon | wl
    else:
        query_syms = mon

    def want(k: str) -> bool:
        return kinds is None or k in kinds

    items: list[EventItem] = []
    if want("earnings") or want("dividend") or want("split"):
        cal = _build_calendar_items(query_syms, start, end, et_today, mon, wl, include_stale)
        items += [it for it in cal if want(it.kind)]
    if want("macro"):
        items += _build_macro_items(start, end, et_today, macro_min_importance)
    if want("split_effective"):
        items += _build_split_effective_items(query_syms, start, end, et_today, mon, wl)
    if want("holiday"):
        items += _build_holiday_items(start, end, et_today)

    # 정렬: (event_date, 대표시각, kind 순서, symbol)
    items.sort(key=lambda it: (
        it.event_date_et, it._sort_time, _KIND_ORDER.get(it.kind, 9), it.symbol or "",
    ))

    counts: dict[str, int] = {}
    for it in items:
        counts[it.kind] = counts.get(it.kind, 0) + 1

    feed = EventFeed(
        as_of=as_of,
        start=start,
        end=end,
        scope=scope,
        symbols={"monitor": sorted(mon), "watchlist": sorted(wl)},
        counts=counts,
        items=items,
    )
    return feed.as_dict()


# ────────────────────────── P1-iii 알림 이음새 (Phase 1.5, 발송 미구현) ──────────────────────────
def classify_trigger(item: dict, prev: dict | None) -> str | None:
    """이벤트 전이 판정 헬퍼 — alerting 구독 축과 호환되는 시그니처만 정의(P1-iii 이음새).

    Phase 1.5에서 발송 로직을 붙인다. 현재는 전이 분류만:
      - "d_minus_n": D-N 도래(prev 없음/미도래 → 창 진입)
      - "occurred": scheduled → occurred 전이
      - "stale": scheduled/occurred → stale 전이
    반환 None = 트리거 없음. (구독 필터는 symbols[]·kinds[] 축과 정렬 — build_event_feed 인자 동형.)
    """
    if prev is None:
        return None
    ps, cs = prev.get("status"), item.get("status")
    if ps != "occurred" and cs == "occurred":
        return "occurred"
    if ps != "stale" and cs == "stale":
        return "stale"
    if item.get("d_day") is not None and 0 <= item["d_day"] <= (prev.get("d_day") or 0):
        return "d_minus_n"
    return None
