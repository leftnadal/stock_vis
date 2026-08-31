"""연합 이벤트 읽기 서비스 단위 테스트 (EVT-IMPL-4 STEP 1-7).

타 유저 누출 0 / scope 3종·sources 마크 / 서프라이즈·None / date_trust 임계 /
stale 제외·include / 휴장 인터리브·정렬 / 세션 UNKNOWN→None / KST 변환 / 캐시 키 분리.
DB = pytest 자동 생성. 휴장·macro 원천은 결정적 창으로 고정.
"""
from datetime import date, time

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.monitor.models.monitor import Monitor
from apps.monitor.services.event_feed import (
    STABLE_N,
    _parse_numeric,
    _surprise,
    build_event_feed,
)
from macro.models.indicators import EconomicEvent
from packages.shared.stocks.models import CalendarEvent, Stock
from packages.shared.users.models import Watchlist, WatchlistItem

User = get_user_model()

# 2026-09-07 = Labor Day(휴장, trading_calendar 커버). 창을 이 날 포함하도록 고정.
START = date(2026, 8, 24)
END = date(2026, 11, 30)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="evt_u1", password="pw12345")


def _stock(sym):
    return Stock.objects.create(symbol=sym, stock_name=f"{sym} Inc", exchange="NASDAQ", currency="USD")


def _monitor(user, sym, status=Monitor.Status.ACTIVE):
    return Monitor.objects.create(
        user=user, scope=Monitor.Scope.STOCK, target_ref=sym, name=f"{sym} 감시", status=status
    )


def _earnings(sym, d, *, session=CalendarEvent.Session.UNKNOWN, est=None, actual=None,
              status=CalendarEvent.Status.SCHEDULED, doc=1):
    ev = CalendarEvent.objects.create(
        event_type=CalendarEvent.EventType.EARNINGS, symbol=sym, event_date=d,
        session=session, status=status, eps_estimated=est, eps_actual=actual, date_observed_count=doc,
    )
    return ev


# ────────────────────────── 누출·스코프 ──────────────────────────
class TestScopeIsolation:
    def test_other_user_symbols_never_leak(self, user):
        other = User.objects.create_user(username="evt_other", password="pw")
        _monitor(user, "AAPL")
        _monitor(other, "MSFT")
        _earnings("AAPL", date(2026, 9, 4), est="1.0")
        _earnings("MSFT", date(2026, 9, 4), est="2.0")
        feed = build_event_feed(user, start=START, end=END, scope="both")
        syms = {it["symbol"] for it in feed["items"] if it["symbol"]}
        assert "AAPL" in syms
        assert "MSFT" not in syms  # 타 유저 종목 누출 0

    def test_scope_three_variants_and_source_marks(self, user):
        _stock("AAPL")
        _stock("MSFT")
        _monitor(user, "AAPL")  # AAPL = monitor
        wl = Watchlist.objects.create(user=user, name="관심")
        WatchlistItem.objects.create(watchlist=wl, stock=Stock.objects.get(symbol="AAPL"))  # AAPL = both
        WatchlistItem.objects.create(watchlist=wl, stock=Stock.objects.get(symbol="MSFT"))  # MSFT = watch만
        _earnings("AAPL", date(2026, 9, 4), est="1.0")
        _earnings("MSFT", date(2026, 9, 4), est="2.0")

        mon = build_event_feed(user, start=START, end=END, scope="monitor")
        assert {it["symbol"] for it in mon["items"] if it["symbol"]} == {"AAPL"}
        aapl = next(it for it in mon["items"] if it["symbol"] == "AAPL")
        assert sorted(aapl["sources"]) == ["monitor", "watchlist"]  # 교집합 → both 마크

        watch = build_event_feed(user, start=START, end=END, scope="watchlist")
        assert {it["symbol"] for it in watch["items"] if it["symbol"]} == {"AAPL", "MSFT"}
        msft = next(it for it in watch["items"] if it["symbol"] == "MSFT")
        assert msft["sources"] == ["watchlist"]

        both = build_event_feed(user, start=START, end=END, scope="both")
        assert {it["symbol"] for it in both["items"] if it["symbol"]} == {"AAPL", "MSFT"}
        assert both["symbols"] == {"monitor": ["AAPL"], "watchlist": ["AAPL", "MSFT"]}

    def test_paused_and_setting_up_monitors_included(self, user):
        _monitor(user, "AAPL", status=Monitor.Status.PAUSED)
        _monitor(user, "TSLA", status=Monitor.Status.SETTING_UP)
        _earnings("AAPL", date(2026, 9, 4), est="1.0")
        _earnings("TSLA", date(2026, 9, 4), est="1.0")
        feed = build_event_feed(user, start=START, end=END, scope="monitor")
        assert {it["symbol"] for it in feed["items"] if it["symbol"]} == {"AAPL", "TSLA"}


# ────────────────────────── 서프라이즈 ──────────────────────────
class TestSurprise:
    def test_earnings_beat_miss_and_none(self, user):
        _monitor(user, "NVDA")
        _monitor(user, "CRM")
        _monitor(user, "XX")
        _earnings("NVDA", date(2026, 9, 4), est="0.98", actual="1.05", status=CalendarEvent.Status.OCCURRED)
        _earnings("CRM", date(2026, 9, 4), est="2.78", actual="2.71", status=CalendarEvent.Status.OCCURRED)
        _earnings("XX", date(2026, 9, 4), est="1.00")  # actual 없음 → None
        feed = build_event_feed(user, start=START, end=END, scope="monitor")
        by = {it["symbol"]: it["surprise"] for it in feed["items"] if it["symbol"]}
        assert by["NVDA"]["direction"] == "beat" and by["NVDA"]["pct"] == 7.1
        assert by["CRM"]["direction"] == "miss" and by["CRM"]["pct"] == -2.5
        assert by["XX"] is None

    def test_macro_numeric_parse(self):
        assert _parse_numeric("2.6%") == 2.6
        assert _parse_numeric("+75K") == 75000.0
        assert _parse_numeric("1,250") == 1250.0
        assert _parse_numeric("") is None
        assert _parse_numeric("N/A") is None

    def test_surprise_helper_flat_and_zero_estimate(self):
        assert _surprise(2.6, 2.6) == {"pct": 0.0, "direction": "flat"}
        assert _surprise(1.0, 0.0) is None  # |est|==0 → None


# ────────────────────────── date_trust ──────────────────────────
class TestDateTrust:
    def test_stable_fluid_thresholds(self, user):
        _monitor(user, "STB")
        _monitor(user, "FLD")
        _earnings("STB", date(2026, 9, 4), est="1.0", doc=STABLE_N)      # >= N → stable
        _earnings("FLD", date(2026, 9, 4), est="1.0", doc=STABLE_N - 1)  # < N → fluid
        feed = build_event_feed(user, start=START, end=END, scope="monitor")
        by = {it["symbol"]: it for it in feed["items"] if it["symbol"]}
        assert by["STB"]["date_trust"] == "stable" and by["STB"]["date_observed_count"] == STABLE_N
        assert by["FLD"]["date_trust"] == "fluid"

    def test_stale_excluded_by_default_and_unconfirmed_when_included(self, user):
        _monitor(user, "ORCL")
        _earnings("ORCL", date(2026, 9, 11), est="1.0", status=CalendarEvent.Status.STALE, doc=3)
        default = build_event_feed(user, start=START, end=END, scope="monitor")
        assert all(it["symbol"] != "ORCL" for it in default["items"])  # 기본 제외
        incl = build_event_feed(user, start=START, end=END, scope="monitor", include_stale=True)
        orcl = next(it for it in incl["items"] if it["symbol"] == "ORCL")
        assert orcl["status"] == "stale" and orcl["date_trust"] == "unconfirmed"


# ────────────────────────── 세션·KST ──────────────────────────
class TestSessionAndKst:
    def test_session_unknown_yields_none_and_no_kst(self, user):
        _monitor(user, "UNK")
        _earnings("UNK", date(2026, 9, 4), est="1.0", session=CalendarEvent.Session.UNKNOWN)
        feed = build_event_feed(user, start=START, end=END, scope="monitor")
        it = next(i for i in feed["items"] if i["symbol"] == "UNK")
        assert it["session"] is None            # UNKNOWN → None(FE 미표기)
        assert it["event_dt_kst"] is None        # 날짜만

    def test_bmo_amc_kst_conversion(self, user):
        _monitor(user, "BM")
        _monitor(user, "AM")
        _earnings("BM", date(2026, 9, 4), est="1.0", session=CalendarEvent.Session.BMO)
        _earnings("AM", date(2026, 9, 4), est="1.0", session=CalendarEvent.Session.AMC)
        feed = build_event_feed(user, start=START, end=END, scope="monitor")
        by = {it["symbol"]: it for it in feed["items"] if it["symbol"]}
        # BMO 08:00 ET(EDT -04) → 21:00 KST 같은 날
        assert by["BM"]["session"] == "BMO"
        assert by["BM"]["event_dt_kst"].startswith("2026-09-04T21:00:00+09:00")
        # AMC 16:30 ET → 05:30 KST 익일
        assert by["AM"]["session"] == "AMC"
        assert by["AM"]["event_dt_kst"].startswith("2026-09-05T05:30:00+09:00")

    def test_macro_time_kst(self, user, db):
        EconomicEvent.objects.create(
            event_id="cpi-2026-09", title="CPI", country="US", event_date=date(2026, 9, 11),
            event_time=time(8, 30), importance=EconomicEvent.EventImportance.CRITICAL,
            forecast_value="2.9", previous_value="2.7",
        )
        feed = build_event_feed(user, start=START, end=END, scope="monitor")
        mac = next(it for it in feed["items"] if it["kind"] == "macro")
        assert mac["event_time_et"] == "08:30"
        # 08:30 ET(EDT) → 21:30 KST 같은 날
        assert mac["event_dt_kst"].startswith("2026-09-11T21:30:00+09:00")
        assert mac["badges"] == ["critical"] or "critical" in mac["badges"]


# ────────────────────────── macro 필터·휴장·정렬 ──────────────────────────
class TestMacroHolidaySort:
    def test_macro_min_importance_filter(self, user, db):
        for imp, eid in [("critical", "c"), ("high", "h"), ("medium", "m"), ("low", "l")]:
            EconomicEvent.objects.create(
                event_id=eid, title=imp, country="US", event_date=date(2026, 9, 9),
                importance=imp,
            )
        hi = build_event_feed(user, start=START, end=END, scope="monitor", macro_min_importance="high")
        imps = {it["detail"]["importance"] for it in hi["items"] if it["kind"] == "macro"}
        assert imps == {"critical", "high"}  # medium/low 제외

    def test_holiday_interleave_and_kind_sort(self, user, db):
        # 같은 날(9/7)은 아니지만 휴장(9/7) 존재 확인 + kind 정렬(holiday 먼저)
        EconomicEvent.objects.create(
            event_id="pmi", title="PMI", country="US", event_date=date(2026, 9, 7),
            importance="high",
        )
        feed = build_event_feed(user, start=START, end=END, scope="monitor")
        sep7 = [it for it in feed["items"] if it["event_date_et"] == "2026-09-07"]
        assert sep7[0]["kind"] == "holiday"       # 같은 날 holiday가 macro보다 먼저
        assert any(it["kind"] == "macro" for it in sep7)
        hol = next(it for it in feed["items"] if it["kind"] == "holiday")
        assert hol["title"] == "NYSE 휴장" and hol["detail"]["next_trading_day"] == "2026-09-08"

    def test_items_sorted_by_date(self, user):
        _monitor(user, "A")
        _earnings("A", date(2026, 9, 20), est="1.0")
        _earnings("A", date(2026, 9, 4), est="1.0")
        feed = build_event_feed(user, start=START, end=END, scope="monitor")
        dates = [it["event_date_et"] for it in feed["items"]]
        assert dates == sorted(dates)


# ────────────────────────── 캐시 키 분리 ──────────────────────────
class TestCacheKeySeparation:
    def test_scope_and_stale_keys_isolated(self, user):
        _monitor(user, "AAPL")
        _stock("MSFT")
        wl = Watchlist.objects.create(user=user, name="w")
        WatchlistItem.objects.create(watchlist=wl, stock=Stock.objects.get(symbol="MSFT"))
        _earnings("AAPL", date(2026, 9, 4), est="1.0")
        _earnings("MSFT", date(2026, 9, 4), est="1.0")
        # 서로 다른 scope → 다른 키 → 서로 오염 없이 정확
        mon = build_event_feed(user, start=START, end=END, scope="monitor")
        both = build_event_feed(user, start=START, end=END, scope="both")
        mon_syms = {it["symbol"] for it in mon["items"] if it["symbol"]}
        both_syms = {it["symbol"] for it in both["items"] if it["symbol"]}
        assert mon_syms == {"AAPL"}
        assert both_syms == {"AAPL", "MSFT"}
