"""SFI-I3 Part 2 — Tier 1 채점 코어 테스트.

순수 함수(적중·미달·unscoreable·휴장 대체·immature)는 DB 없이 합성 픽스처로,
load_scoring_inputs 코호트 분기(pinned/derived)는 DB로 검증.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from packages.shared.stocks.services import analyst_scoring as sc
from packages.shared.stocks.services.analyst_scoring import Prediction


def _wk_bars(start: date, closes):
    """연속 평일(주말 스킵) bar 시퀀스 [(date, Decimal(close))]."""
    out, d = [], start
    for c in closes:
        while d.weekday() >= 5:
            d += timedelta(days=1)
        out.append((d, Decimal(str(c))))
        d += timedelta(days=1)
    return out


# ── 통계 헬퍼 ──
def test_binom_symmetric_half():
    assert sc.binom_p_two_sided(5, 10) == pytest.approx(1.0)
    assert sc.binom_p_two_sided(10, 10) < 0.01
    assert sc.binom_p_greater(10, 10) == pytest.approx(0.5**10)


def test_spearman_monotonic():
    assert sc.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert sc.spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


# ── W3 만기 해석 ──
def test_resolve_ok_and_immature():
    bars = _wk_bars(date(2026, 1, 5), [100, 101, 102, 103])
    # capture=bars[0], h=2 → j=2 존재, as_of=마지막 bar
    status, rdate, rclose = sc.resolve_realized(bars, bars[0][0], 2, bars[-1][0])
    assert status == "ok" and rclose == Decimal("102")
    # h=10 → j 범위 밖 + 달력 얼마 안 지남 → immature
    status2, _, _ = sc.resolve_realized(bars, bars[0][0], 10, bars[-1][0])
    assert status2 == "immature"


def test_resolve_series_break_when_data_ends_but_time_passed():
    bars = _wk_bars(date(2026, 1, 5), [100, 101])
    as_of = date(2026, 3, 30)  # 충분히 경과했는데 bar 부재 = 단절/상폐
    status, _, _ = sc.resolve_realized(bars, bars[0][0], 5, as_of)
    assert status == "unscoreable:series_break"


def test_resolve_no_data_and_no_spot():
    assert sc.resolve_realized([], date(2026, 1, 5), 2, date(2026, 2, 1))[0] == "unscoreable:no_data"
    bars = _wk_bars(date(2026, 2, 1), [100, 101, 102])
    # capture 이전 bar 없음
    assert sc.resolve_realized(bars, date(2026, 1, 1), 1, bars[-1][0])[0] == "unscoreable:no_spot"


def test_resolve_holiday_substitution_uses_trading_day():
    # 주말 낀 시퀀스 — h거래일 인덱싱이 거래일로 자동 대체(무거래일 회피)
    bars = _wk_bars(date(2026, 1, 2), [100, 101, 102, 103, 104])  # 금 시작 → 주말 스킵
    status, rdate, _ = sc.resolve_realized(bars, bars[0][0], 3, bars[-1][0])
    assert status == "ok"
    assert rdate == bars[3][0]  # 정확히 3거래일 후 실제 거래일


# ── ① 방향 적중률 ──
def test_direction_hit_and_miss():
    up_bars = _wk_bars(date(2026, 1, 5), [100, 105, 120])
    p_hit = Prediction("HIT", up_bars[0][0], Decimal("100"), Decimal("110"), "pinned")
    r = sc.direction_hit_rate([p_hit], {"HIT": up_bars}, up_bars[-1][0], horizons=(2,))
    assert r[2]["sample"] == 1 and r[2]["hits"] == 1 and r[2]["hit_rate"] == 1.0

    down_bars = _wk_bars(date(2026, 1, 5), [100, 99, 90])
    p_miss = Prediction("MISS", down_bars[0][0], Decimal("100"), Decimal("110"), "pinned")
    r2 = sc.direction_hit_rate([p_miss], {"MISS": down_bars}, down_bars[-1][0], horizons=(2,))
    assert r2[2]["sample"] == 1 and r2[2]["hits"] == 0


def test_direction_immature_reports_earliest_maturity():
    bars = _wk_bars(date(2026, 1, 5), [100, 101])
    p = Prediction("X", bars[0][0], Decimal("100"), Decimal("110"), "pinned")
    r = sc.direction_hit_rate([p], {"X": bars}, bars[-1][0], horizons=(21,))
    assert r[21]["sample"] == 0
    assert r[21]["earliest_maturity_est"] is not None


def test_direction_unscoreable_collected():
    bars = _wk_bars(date(2026, 1, 5), [100, 101])
    p = Prediction("X", bars[0][0], Decimal("100"), Decimal("110"), "pinned")
    r = sc.direction_hit_rate([p], {"X": bars}, date(2026, 3, 30), horizons=(5,))
    assert r[5]["sample"] == 0
    assert len(r[5]["unscoreable"]) == 1
    assert r[5]["unscoreable"][0][2] == "unscoreable:series_break"


# ── ② 목표가 진행률 ──
def test_target_progress_ratio():
    # 예측폭 +20 (100→120), 실현폭 +10 (100→110) → ratio 0.5
    bars = _wk_bars(date(2026, 1, 5), [100, 105, 110])
    p = Prediction("X", bars[0][0], Decimal("100"), Decimal("120"), "pinned")
    r = sc.target_progress([p], {"X": bars}, bars[-1][0], horizons=(2,))
    assert r[2]["sample"] == 1
    assert r[2]["median_ratio"] == pytest.approx(0.5)


# ── ③ 횡단면 IC ──
def test_cross_sectional_ic_perfect_rank():
    # 같은 주 3종목: upside 순위 == 실현수익 순위 → IC=1
    start = date(2026, 1, 5)  # 월요일
    preds, bars = [], {}
    for i, sym in enumerate(["A", "B", "C"]):
        b = _wk_bars(start, [100, 100 + (i + 1) * 5, 100 + (i + 1) * 10])
        bars[sym] = b
        # upside% 서로 다르게: target = spot*(1 + (i+1)*0.1)
        preds.append(Prediction(sym, b[0][0], Decimal("100"), Decimal(str(100 + (i + 1) * 10)), "pinned"))
    r = sc.cross_sectional_ic(preds, bars, list(bars["A"])[-1][0], horizons=(2,))
    assert r[2]["cohorts_scored"] == 1
    assert r[2]["mean_ic"] == pytest.approx(1.0)


# ── load_scoring_inputs 코호트 분기 (DB) ──
@pytest.mark.django_db
def test_load_inputs_cohort_split():
    from packages.shared.stocks.models import AnalystSignalSnapshot, DailyPrice, Stock

    s = Stock.objects.create(symbol="ZZZ", currency="USD")
    cap = date(2026, 1, 5)
    DailyPrice.objects.create(
        stock=s, date=cap, open_price=99, high_price=101, low_price=98,
        close_price=Decimal("100.0000"), volume=1000,
    )
    # pinned 행 (spot_at_capture 존재)
    a1 = AnalystSignalSnapshot.objects.create(
        symbol="ZZZ", target_consensus=Decimal("110"), spot_at_capture=Decimal("100"),
    )
    # derived 행 (spot null → DailyPrice에서 파생)
    a2 = AnalystSignalSnapshot.objects.create(
        symbol="ZZZ", target_consensus=Decimal("120"), spot_at_capture=None,
    )
    ts = datetime(2026, 1, 5, 22, 30, tzinfo=timezone.utc)
    AnalystSignalSnapshot.objects.filter(pk__in=[a1.pk, a2.pk]).update(captured_at=ts)

    preds, bars, counts = sc.load_scoring_inputs(date(2026, 1, 10))
    cohorts = {p.cohort for p in preds}
    assert cohorts == {"pinned", "derived"}
    derived = next(p for p in preds if p.cohort == "derived")
    assert derived.spot == Decimal("100.0000")  # DailyPrice.close 파생
    assert counts["ass_rows"] == 2 and counts["daily_price_rows"] == 1


@pytest.mark.django_db
def test_score_tier1_smoke_has_header_and_cohorts():
    r = sc.score_tier1(date(2026, 1, 10))
    assert r["header"]["scoring_version"] == sc.SCORING_VERSION
    assert set(r["cohorts"]) == {"pinned", "derived"}
