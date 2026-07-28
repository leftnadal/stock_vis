"""backfill_v2_regime_vectors 커맨드 회귀 (B1-S2 소급 벡터 합성).

검증 계약:
  - 대상 = SPY 영업일(창 내), 시계열 순차 hysteresis chaining.
  - coverage 실측 저장(완전벡터/leading gap 정직).
  - 기존 라이브 행 불가침(창 필터 + get_or_create).
  - 멱등(재실행 시 synthesized 0 / skipped N), dry-run 무쓰기.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

pytestmark = [pytest.mark.django_db]

# BULL로 안정 분류되는 벤치 지표값(전 구간 동일 — 전환 없음, streak 누적)
_IND_VALUES = {
    "NFCI": "-0.40", "NFCICREDIT": "-0.20", "NFCILEVERAGE": "-0.30",
    "NFCIRISK": "-0.50", "BAMLH0A0HYM2": "2.20", "BAMLH0A3HYC": "5.00",
    "T10Y2Y": "0.60", "T10Y3M": "1.20", "VIXCLS": "14.0",
    "VIX3M": "15.0", "MOVE": "80.0",
}
_NFCI_FAMILY = ("NFCI", "NFCICREDIT", "NFCILEVERAGE", "NFCIRISK")


@pytest.fixture(autouse=True)
def _clean_series():
    from macro.models.indicators import IndicatorValue, MarketIndexPrice

    IndicatorValue.objects.all().delete()
    MarketIndexPrice.objects.all().delete()
    yield


def _weekdays(start: date, n: int) -> list[date]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


@pytest.fixture
def seeded():
    """SPY 25 영업일 + 지표(NFCI 계열은 3일째부터 = leading gap 2일) + 라이브 행 1건."""
    from macro.models.indicators import (
        EconomicIndicator,
        IndicatorValue,
        MarketIndex,
        MarketIndexPrice,
    )
    from apps.market_pulse.models.regime import RegimeSnapshot

    days = _weekdays(date(2024, 1, 1), 25)
    spy, _ = MarketIndex.objects.get_or_create(symbol="SPY", defaults={"name": "SPY"})
    for i, d in enumerate(days):
        MarketIndexPrice.objects.create(
            index=spy, date=d, close=Decimal(str(100.0 + i * 0.3))
        )
    for code, v in _IND_VALUES.items():
        ind, _ = EconomicIndicator.objects.get_or_create(
            code=code, defaults={"name": code, "category": "macro", "data_source": "fred"}
        )
        start_i = 2 if code in _NFCI_FAMILY else 0  # NFCI 계열 leading gap
        for d in days[start_i:]:
            IndicatorValue.objects.create(indicator=ind, date=d, value=Decimal(v))

    # 라이브 행(창 밖) — 불가침 대상
    live_date = date(2024, 3, 1)
    live = RegimeSnapshot.objects.create(
        date=live_date,
        snapshot_time=datetime(2024, 3, 1, 20, 0),
        regime=RegimeSnapshot.Regime.CRISIS,
        status=RegimeSnapshot.Status.OK,
        inputs={"marker": "LIVE"},
        coverage=0.42,
        is_finalized=False,
    )
    return {"days": days, "live": live, "spy": spy}


def _run(**kw):
    out = StringIO()
    call_command("backfill_v2_regime_vectors", stdout=out, stderr=out, **kw)
    return out.getvalue()


class TestSynthesis:
    def test_synthesizes_all_business_days(self, seeded):
        from apps.market_pulse.models.regime import RegimeSnapshot

        _run(**{"from": "2024-01-01"})
        # 라이브(2024-03-01) 제외한 25 영업일 합성
        synth = RegimeSnapshot.objects.exclude(date=seeded["live"].date)
        assert synth.count() == 25

    def test_coverage_honest_leading_gap_and_complete(self, seeded):
        from apps.market_pulse.models.regime import RegimeSnapshot

        _run(**{"from": "2024-01-01"})
        days = seeded["days"]
        first = RegimeSnapshot.objects.get(date=days[0])
        last = RegimeSnapshot.objects.get(date=days[-1])
        # 첫날: price 미완 + NFCI 계열 결측 → coverage < 1.0(정직)
        assert first.coverage < 1.0
        assert first.status == RegimeSnapshot.Status.INSUFFICIENT_DATA
        # 마지막날(25일째, vol_20d 확보 + 전지표) → 완전벡터
        assert last.coverage == pytest.approx(1.0)
        assert last.status == RegimeSnapshot.Status.OK
        assert last.is_finalized is True

    def test_hysteresis_chained_streak_grows(self, seeded):
        from apps.market_pulse.models.regime import RegimeSnapshot

        _run(**{"from": "2024-01-01"})
        days = seeded["days"]
        s_last = RegimeSnapshot.objects.get(date=days[-1])
        # 안정 BULL → streak가 1보다 큼(순차 chaining 증거)
        assert s_last.regime == RegimeSnapshot.Regime.BULL_EXPANSION
        assert s_last.hysteresis_streak > 1

    def test_snapshot_time_deterministic(self, seeded):
        from apps.market_pulse.models.regime import RegimeSnapshot

        _run(**{"from": "2024-01-01"})
        s = RegimeSnapshot.objects.get(date=seeded["days"][0])
        assert s.snapshot_time.hour == 20  # UTC 마감 결정론


class TestGuards:
    def test_live_row_untouched(self, seeded):
        from apps.market_pulse.models.regime import RegimeSnapshot

        before = RegimeSnapshot.objects.get(date=seeded["live"].date)
        # 창 상한을 라이브 이후로 강제 요청해도 라이브 구간은 하드 차단
        _run(**{"from": "2024-01-01", "to": "2024-03-15"})
        after = RegimeSnapshot.objects.get(date=seeded["live"].date)
        assert after.regime == before.regime == RegimeSnapshot.Regime.CRISIS
        assert after.coverage == 0.42
        assert after.inputs == {"marker": "LIVE"}
        # 라이브 날짜엔 신규 합성행 없음(1건 유지)
        assert RegimeSnapshot.objects.filter(date=seeded["live"].date).count() == 1
        # 라이브 이후 날짜에 합성 0
        assert not RegimeSnapshot.objects.filter(date__gte=seeded["live"].date).exclude(
            date=seeded["live"].date
        ).exists()

    def test_idempotent_rerun(self, seeded):
        from apps.market_pulse.models.regime import RegimeSnapshot

        _run(**{"from": "2024-01-01"})
        n1 = RegimeSnapshot.objects.count()
        out = _run(**{"from": "2024-01-01"})
        n2 = RegimeSnapshot.objects.count()
        assert n1 == n2  # 추가 생성 0
        assert "skipped=25" in out


class TestDryRun:
    def test_dry_run_writes_nothing(self, seeded):
        from apps.market_pulse.models.regime import RegimeSnapshot

        # 라이브 1건만 존재하는 상태에서 dry-run
        base = RegimeSnapshot.objects.count()
        out = _run(**{"from": "2024-01-01", "dry_run": True})
        assert RegimeSnapshot.objects.count() == base  # 무쓰기
        assert "[DRY-RUN]" in out
        assert "완전벡터" in out
