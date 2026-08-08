"""indicator_scorer 이식 검증 (MON-P2-S2)."""
from datetime import date, timedelta

import pytest

from apps.monitor.services.indicator_scorer import (
    check_extreme_volatility,
    score_indicator,
    score_indicator_from_model,
    source_row_count,
)
from apps.monitor.services.technical import score_indicator_dispatch


class TestScoreIndicatorPure:
    def _dates(self, n):
        base = date(2026, 1, 1)
        return [base + timedelta(days=i) for i in range(n)]

    def test_insufficient_readings(self):
        r = score_indicator([1, 2, 3], self._dates(3), "positive")
        assert r["is_sufficient"] is False
        assert r["score"] == 0.0

    def test_constant_readings_neutral_mad(self):
        vals = [5.0] * 10
        r = score_indicator(vals, self._dates(10), "positive")
        assert r["is_neutral_mad"] is True
        assert r["score"] == 0.0

    def test_rising_series_positive_score(self):
        vals = [float(i) for i in range(10)]
        r = score_indicator(vals, self._dates(10), "positive", window=10)
        assert r["score"] > 0
        assert r["is_sufficient"] is True

    def test_support_direction_negative_flips(self):
        vals = [float(i) for i in range(10)]
        pos = score_indicator(vals, self._dates(10), "positive", window=10)
        neg = score_indicator(vals, self._dates(10), "negative", window=10)
        assert neg["score"] == pytest.approx(-pos["score"])

    def test_check_extreme_volatility(self):
        class _Ind:
            id = "x"
            name = "급변 지표"

        assert check_extreme_volatility(6.0, _Ind()) is not None
        assert check_extreme_volatility(1.0, _Ind()) is None


@pytest.mark.django_db
class TestScoreFromModel:
    def test_paused_returns_neutral(self, make_indicator):
        ind = make_indicator(is_paused=True)
        r = score_indicator_from_model(ind)
        assert r["score"] == 0.0
        assert r.get("is_paused") is True

    def test_override_score_used(self, make_indicator):
        ind = make_indicator(override_score=0.7)
        r = score_indicator_from_model(ind)
        assert r["score"] == 0.7
        assert r.get("is_override") is True

    def test_reads_from_model_readings(self, make_indicator, add_readings):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(10)])
        r = score_indicator_from_model(ind)
        assert r["is_sufficient"] is True
        assert r["score"] > 0

    def test_rejected_readings_excluded(self, make_indicator, add_readings):
        ind = make_indicator(window=10)
        add_readings(ind, [float(i) for i in range(10)], status="rejected")
        r = score_indicator_from_model(ind)
        assert r["is_sufficient"] is False  # 유효 판독 0


@pytest.mark.django_db
class TestSourceNSufficiency:
    """MON-P2A(교정): 충분성 = 계산 소스 행수(source_n) >= min_n.

    reading-count(IndicatorReading 행수)는 충분성 판정에 쓰지 않는다 — z 히스토리와
    계산 소스 유효성은 별개 범주. momentum/sma가 DailyPrice로는 값 유효인데
    reading-count로 배제되던 P2A 범주 오류를 고정한다.
    """

    # monitor fixture의 target_ref = "AAPL"

    def _stock(self, symbol="AAPL"):
        from packages.shared.stocks.models import Stock
        return Stock.objects.create(symbol=symbol)

    def _daily(self, stock, n):
        from packages.shared.stocks.models import DailyPrice
        base = date(2026, 1, 1)
        DailyPrice.objects.bulk_create([
            DailyPrice(
                stock=stock, date=base + timedelta(days=i),
                open_price=1, high_price=1, low_price=1, close_price=1, volume=100,
            )
            for i in range(n)
        ])

    def _eod(self, stock, n):
        from packages.shared.stocks.models import EODSignal
        base = date(2026, 1, 1)
        EODSignal.objects.bulk_create([
            EODSignal(stock=stock, date=base + timedelta(days=i), close_price=1)
            for i in range(n)
        ])

    def test_source_row_count_dispatches_by_source(self, make_indicator):
        from apps.monitor.catalog import catalog_entry
        stock = self._stock()
        self._daily(stock, 40)
        self._eod(stock, 3)
        ind_dp = make_indicator(source_key="momentum_12_1")
        ind_eod = make_indicator(source_key="eod_composite")
        assert source_row_count(ind_dp, catalog_entry("stock", "momentum_12_1")) == 40
        assert source_row_count(ind_eod, catalog_entry("stock", "eod_composite")) == 3

    def test_zscore_insufficient_source_despite_many_readings(self, make_indicator, add_readings):
        # 핵심: readings 100개(z 히스토리 충분)여도 DailyPrice 100 < min_n 252면 불충분.
        stock = self._stock()
        self._daily(stock, 100)
        ind = make_indicator(source_key="momentum_12_1", window=60)
        add_readings(ind, [float(i) for i in range(100)])
        r = score_indicator_from_model(ind)
        assert r["is_sufficient"] is False
        assert r["source_n"] == 100

    def test_zscore_sufficient_source_despite_few_readings(self, make_indicator, add_readings):
        # 핵심(대칭): readings 10개(적음)여도 DailyPrice 300 >= 252면 충분·계산 수행.
        stock = self._stock()
        self._daily(stock, 300)
        ind = make_indicator(source_key="momentum_12_1", window=10)
        add_readings(ind, [float(i) for i in range(10)])
        r = score_indicator_from_model(ind)
        assert r["is_sufficient"] is True
        assert r["score"] != 0.0

    def test_bounded_source_gate(self, make_indicator, add_readings):
        # bounded(high_52w_proximity, min_n=252)도 source_n으로 통일 판정.
        stock = self._stock()
        self._daily(stock, 100)  # < 252
        ind = make_indicator(source_key="high_52w_proximity")
        add_readings(ind, [0.8])
        r = score_indicator_dispatch(ind)
        assert r["is_sufficient"] is False
        assert r["scoring_mode"] == "bounded"

    def test_eod_indicator_zero_source_insufficient(self, make_indicator, add_readings):
        # EODSignal=0이면 eod 계열(min_n=1) 불충분.
        stock = self._stock()
        self._daily(stock, 300)  # DailyPrice 있어도 eod_composite는 EODSignal 소스
        ind = make_indicator(source_key="eod_composite", window=10)
        add_readings(ind, [float(i) for i in range(10)])
        r = score_indicator_from_model(ind)
        assert r["is_sufficient"] is False
        assert r["source_n"] == 0

    def _matrix_sufficiency(self, monitor, make_indicator, add_readings):
        from apps.monitor.catalog import catalog_for
        suff = 0
        for entry in catalog_for("stock"):
            ind = make_indicator(name=entry["key"], source_key=entry["key"], window=10)
            add_readings(ind, [float(i) for i in range(10)])
            r = score_indicator_dispatch(ind)
            if r["is_sufficient"]:
                suff += 1
        return suff

    def test_matrix_non_sp500_6_of_9(self, monitor, make_indicator, add_readings):
        # 비SP500형: DailyPrice 273행(momentum/sma/w52 전부 >= min_n) · EODSignal 0.
        # → DailyPrice 6지표 충분 + EOD 3지표 불충분 = 6/9.
        stock = self._stock()
        self._daily(stock, 273)
        assert self._matrix_sufficiency(monitor, make_indicator, add_readings) == 6

    def test_matrix_sp500_9_of_9(self, monitor, make_indicator, add_readings):
        # SP500형: DailyPrice 273 + EODSignal 존재 → 9/9.
        stock = self._stock()
        self._daily(stock, 273)
        self._eod(stock, 60)
        assert self._matrix_sufficiency(monitor, make_indicator, add_readings) == 9
