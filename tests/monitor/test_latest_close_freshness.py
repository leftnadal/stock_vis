"""DIRECTIVE-PRICE-FRESH-1 — latest_close 신선도 비교.

결함: EODSignal을 무조건 우선해 EODSignal이 뒤처진 종목에서 stale 종가가 통과했다.
가드(ensure_price_freshness)는 DailyPrice만 보장하므로 두 소스의 신선도가 갈린다.
2026-09-17 TLN 실측에서 4일 묵은 값으로 손절 접근이 거짓 발화 → T-6 회귀 고정.
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.monitor.services.price_zone import is_near_stop
from apps.monitor.services.scenario import latest_close

AS_OF = date(2026, 9, 17)


@pytest.fixture
def stock(db):
    from packages.shared.stocks.models import Stock

    return Stock.objects.create(symbol="TLN", stock_name="Talen Energy")


@pytest.fixture
def mk_daily(stock):
    from packages.shared.stocks.models import DailyPrice

    def _mk(d, close):
        return DailyPrice.objects.create(
            stock=stock, date=d,
            open_price=Decimal(str(close)), high_price=Decimal(str(close)),
            low_price=Decimal(str(close)), close_price=Decimal(str(close)),
            volume=1_000_000,
        )
    return _mk


@pytest.fixture
def mk_eod(stock):
    from packages.shared.stocks.models import EODSignal

    def _mk(d, close):
        return EODSignal.objects.create(stock=stock, date=d, close_price=Decimal(str(close)))
    return _mk


@pytest.mark.django_db
class TestLatestCloseFreshness:
    def test_t1_eod_newer_wins(self, mk_eod, mk_daily):
        """T-1: EODSignal이 더 최신 → EODSignal 값."""
        mk_daily(date(2026, 9, 15), 100.0)
        mk_eod(date(2026, 9, 17), 111.0)
        assert latest_close("TLN") == pytest.approx(111.0)

    def test_t2_daily_newer_wins(self, mk_eod, mk_daily):
        """T-2: DailyPrice가 더 최신 → DailyPrice 값. ★ 이번 결함의 재현 케이스."""
        mk_eod(date(2026, 9, 14), 286.52)
        mk_daily(date(2026, 9, 17), 293.31)
        assert latest_close("TLN") == pytest.approx(293.31)

    def test_t3_same_date_prefers_eod(self, mk_eod, mk_daily):
        """T-3: 같은 날짜 → EODSignal 우선 (기존 동작 보존)."""
        d = date(2026, 9, 17)
        mk_eod(d, 200.0)
        mk_daily(d, 201.0)
        assert latest_close("TLN") == pytest.approx(200.0)

    def test_t4_eod_only(self, mk_eod):
        mk_eod(date(2026, 9, 17), 150.0)
        assert latest_close("TLN") == pytest.approx(150.0)

    def test_t4_daily_only(self, mk_daily):
        mk_daily(date(2026, 9, 17), 160.0)
        assert latest_close("TLN") == pytest.approx(160.0)

    def test_t4_neither(self, stock):
        assert latest_close("TLN") is None

    def test_t4_unknown_symbol(self, db):
        assert latest_close("NOSUCH") is None

    def test_t5_as_of_cuts_both_sources(self, mk_eod, mk_daily):
        """T-5: as_of 컷오프가 두 소스 모두에 적용된다."""
        mk_eod(date(2026, 9, 14), 286.52)
        mk_daily(date(2026, 9, 17), 293.31)
        mk_daily(date(2026, 9, 18), 292.30)
        # 09-17까지 → DailyPrice 09-17
        assert latest_close("TLN", as_of=date(2026, 9, 17)) == pytest.approx(293.31)
        # 09-16까지 → DailyPrice 09-17은 잘리고 EODSignal 09-14만 남는다
        assert latest_close("TLN", as_of=date(2026, 9, 16)) == pytest.approx(286.52)
        # 09-13까지 → 둘 다 잘림
        assert latest_close("TLN", as_of=date(2026, 9, 13)) is None

    def test_as_of_cutoff_applies_to_eod_too(self, mk_eod):
        mk_eod(date(2026, 9, 14), 286.52)
        mk_eod(date(2026, 9, 17), 300.0)
        assert latest_close("TLN", as_of=date(2026, 9, 15)) == pytest.approx(286.52)

    def test_close_price_is_not_null_on_both_models(self):
        """전제 고정: 양 모델 close_price가 NOT NULL이라 값-null 분기가 불요하다.

        이 전제가 깨지면(null 허용으로 마이그레이션) latest_close는 NULL 행을 최신으로
        집어 float(None)에서 죽는다 — 그때 이 테스트가 먼저 알린다.
        """
        from django.apps import apps

        for name in ("EODSignal", "DailyPrice"):
            assert apps.get_model("stocks", name)._meta.get_field("close_price").null is False


@pytest.mark.django_db
class TestTlnRegression:
    """T-6: 2026-09-17 실측 회귀 — stale EODSignal이 손절 접근을 거짓 발화시켰다."""

    STOP = Decimal("271.20")
    BAND = 0.0707  # 09-17 기준 실측 밴드 7.07%

    def test_t6_stale_eod_would_have_fired(self, mk_eod, mk_daily):
        """수리 전 동작(= EODSignal 무조건 우선)이면 발화했을 값임을 고정."""
        stale = 286.52  # EODSignal 09-14
        assert is_near_stop(stale, self.STOP, self.BAND) is True

    def test_t6_fresh_daily_does_not_fire(self, mk_eod, mk_daily):
        """수리 후: DailyPrice 09-17이 선택되어 무발화."""
        mk_eod(date(2026, 9, 14), 286.52)
        mk_daily(date(2026, 9, 17), 293.31)
        close = latest_close("TLN", as_of=AS_OF)
        assert close == pytest.approx(293.31)
        assert is_near_stop(close, self.STOP, self.BAND) is False

    def test_t6_required_buffer_crosses_band(self, mk_eod, mk_daily):
        """경계 수치 고정: stale 5.65% < 밴드 7.07% < fresh 8.15%."""
        stale, fresh = 286.52, 293.31
        s = float(self.STOP)
        assert (stale / s - 1) == pytest.approx(0.0565, abs=1e-4)
        assert (fresh / s - 1) == pytest.approx(0.0815, abs=1e-4)
        assert (stale / s - 1) < self.BAND < (fresh / s - 1)
