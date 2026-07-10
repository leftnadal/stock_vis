"""RegimeInputs as_of 매개변수화 회귀 (B1-S2 소급 벡터 합성).

목적: load_inputs / _latest_indicator_value / _spy_price_series 가 as_of 기준일을
  받아 "그 날 기준"으로 동일 로직을 수행함을 증명한다.
계약:
  1. 기본 경로(as_of 미지정) = 현행 동작 무변경(회귀).
  2. as_of 지정 시 date__lte=as_of 상한 → 미래 데이터 look-ahead 차단.
  3. max_age 캐리(주간 NFCI가 익주까지 캐리)가 as_of 기준으로 자연 동작.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone as django_timezone

from apps.market_pulse.regime import inputs as inputs_mod

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture(autouse=True)
def _clean_series():
    """시드된 macro 시계열을 비워 테스트를 격리(트랜잭션 롤백으로 복원)."""
    from macro.models.indicators import IndicatorValue, MarketIndexPrice

    IndicatorValue.objects.all().delete()
    MarketIndexPrice.objects.all().delete()
    yield


def _mk_indicator(code: str):
    from macro.models.indicators import EconomicIndicator

    ind, _ = EconomicIndicator.objects.get_or_create(
        code=code, defaults={"name": code, "category": "macro", "data_source": "fred"}
    )
    return ind


def _mk_value(ind, d: date, v: str):
    from macro.models.indicators import IndicatorValue

    return IndicatorValue.objects.create(indicator=ind, date=d, value=Decimal(v))


def _mk_spy():
    from macro.models.indicators import MarketIndex

    idx, _ = MarketIndex.objects.get_or_create(
        symbol="SPY", defaults={"name": "S&P 500 ETF"}
    )
    return idx


def _mk_price(idx, d: date, close: str):
    from macro.models.indicators import MarketIndexPrice

    return MarketIndexPrice.objects.create(index=idx, date=d, close=Decimal(close))


class TestLatestIndicatorValueAsOf:
    def test_carry_within_max_age(self):
        ind = _mk_indicator("NFCI")
        _mk_value(ind, date(2023, 7, 14), "-0.40")  # 주간(금요일 기준일)
        # 익주 목요일까지 캐리(14일 이내)
        assert inputs_mod._latest_indicator_value(
            "NFCI", as_of=date(2023, 7, 20)
        ) == pytest.approx(-0.40)

    def test_before_first_value_is_none(self):
        ind = _mk_indicator("NFCI")
        _mk_value(ind, date(2023, 7, 14), "-0.40")
        # 첫 값 이전 = leading gap → None
        assert inputs_mod._latest_indicator_value("NFCI", as_of=date(2023, 7, 13)) is None

    def test_stale_beyond_max_age_is_none(self):
        ind = _mk_indicator("NFCI")
        _mk_value(ind, date(2023, 7, 14), "-0.40")
        # 15일 경과 = max_age(14) 초과 → None
        assert inputs_mod._latest_indicator_value("NFCI", as_of=date(2023, 7, 29)) is None

    def test_no_lookahead_excludes_future(self):
        """핵심: as_of 이후 값은 절대 사용 금지(date__lte 상한)."""
        ind = _mk_indicator("NFCI")
        _mk_value(ind, date(2023, 7, 14), "-0.40")
        _mk_value(ind, date(2023, 7, 21), "0.90")  # as_of 이후(미래)
        # as_of=07-17 기준: 07-21 값을 보면 안 됨 → 07-14 값
        assert inputs_mod._latest_indicator_value(
            "NFCI", as_of=date(2023, 7, 17)
        ) == pytest.approx(-0.40)


class TestSpyPriceSeriesAsOf:
    def test_series_bounded_by_as_of(self):
        idx = _mk_spy()
        for i, d in enumerate(
            [date(2023, 7, 10), date(2023, 7, 11), date(2023, 7, 12), date(2023, 7, 13)]
        ):
            _mk_price(idx, d, str(100 + i))
        series = inputs_mod._spy_price_series(as_of=date(2023, 7, 11))
        dates = [d for d, _ in series]
        assert dates == [date(2023, 7, 10), date(2023, 7, 11)]  # 07-12/13 제외

    def test_series_empty_before_first_price(self):
        idx = _mk_spy()
        _mk_price(idx, date(2023, 7, 10), "100")
        assert inputs_mod._spy_price_series(as_of=date(2023, 7, 9)) == []


class TestLoadInputsAsOf:
    def test_asof_assembles_bounded_inputs(self):
        ind = _mk_indicator("VIXCLS")
        _mk_value(ind, date(2023, 7, 11), "14.0")
        _mk_value(ind, date(2023, 7, 20), "40.0")  # 미래
        idx = _mk_spy()
        _mk_price(idx, date(2023, 7, 10), "100")
        _mk_price(idx, date(2023, 7, 11), "101")
        out = inputs_mod.load_inputs(as_of=date(2023, 7, 11))
        assert out.vix == pytest.approx(14.0)  # 미래 40.0 아님
        assert out.return_1d_pct == pytest.approx(1.0)  # (101-100)/100*100

    def test_default_path_unchanged(self):
        """as_of 미지정 = localdate() 기준(현행 무변경). 최근 값 정상 로드."""
        ind = _mk_indicator("VIXCLS")
        today = django_timezone.localdate()
        _mk_value(ind, today - timedelta(days=1), "18.0")
        out = inputs_mod.load_inputs()
        assert out.vix == pytest.approx(18.0)
