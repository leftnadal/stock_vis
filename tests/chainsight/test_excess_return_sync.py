"""CS-P1B: 초과수익 동조성 순수 계산 단위 테스트.

DB 무의존 — 합성 시계열로 경계 검증(지시서 Slice 1):
  완전 동조 / 무상관 / 짧은 이력(관측 부족) + 초과수익 특유의 경계(벤치마크 차감·분산 0).
"""

from datetime import date, timedelta

import pytest

from apps.chain_sight.services import excess_return_sync as ers


def _series(start, values):
    """(date, price) 리스트 생성. 연속 캘린더일에 값 배치(순수 계층은 거래일 캘린더 무관)."""
    return [(start + timedelta(days=i), v) for i, v in enumerate(values)]


# ─────────────────────────── pearson ───────────────────────────

def test_pearson_perfect_positive():
    assert ers.pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)


def test_pearson_perfect_negative():
    assert ers.pearson([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)


def test_pearson_zero_variance_returns_none():
    # 한쪽이 상수 → 분산 0 → 상관 정의 불가 → None
    assert ers.pearson([1, 1, 1, 1], [1, 2, 3, 4]) is None


def test_pearson_too_few_points():
    assert ers.pearson([1], [2]) is None


# ─────────────────────────── daily_returns ───────────────────────────

def test_daily_returns_basic():
    d = date(2026, 1, 1)
    prices = _series(d, [100.0, 110.0, 99.0])
    r = ers.daily_returns(prices)
    assert r[d + timedelta(days=1)] == pytest.approx(0.10)
    assert r[d + timedelta(days=2)] == pytest.approx(-0.10)
    # 첫날은 수익률 없음
    assert d not in r


def test_daily_returns_skips_none_and_zero():
    d = date(2026, 1, 1)
    prices = [(d, 100.0), (d + timedelta(days=1), None), (d + timedelta(days=2), 121.0)]
    r = ers.daily_returns(prices)
    # None 관측 건너뛰고 100→121 로 이어붙임
    assert r[d + timedelta(days=2)] == pytest.approx(0.21)


def test_daily_returns_unsorted_input():
    d = date(2026, 1, 1)
    prices = [(d + timedelta(days=2), 121.0), (d, 100.0), (d + timedelta(days=1), 110.0)]
    r = ers.daily_returns(prices)
    assert r[d + timedelta(days=1)] == pytest.approx(0.10)
    assert r[d + timedelta(days=2)] == pytest.approx(0.10)


# ─────────────────────────── excess_return_correlation ───────────────────────────

def _returns_from_prices(start, values):
    return ers.daily_returns(_series(start, values))


def test_excess_perfectly_synchronized():
    """두 종목이 벤치마크 차감 후 초과수익이 동일 방향으로 완전 동조 → 강도≈1."""
    d = date(2026, 1, 1)
    n = 70
    # 벤치마크: 매일 +1% 고정
    bench = _returns_from_prices(d, [100.0 * (1.01 ** i) for i in range(n)])
    # A, B: 벤치마크 대비 같은 초과 패턴(교대 ±). 초과수익 부호가 완전 일치.
    pa, pb = [100.0], [100.0]
    for i in range(1, n):
        bump = 1.02 if i % 2 == 0 else 1.005  # 벤치(1.01) 위/아래 교대
        pa.append(pa[-1] * bump)
        pb.append(pb[-1] * bump)
    ra = _returns_from_prices(d, pa)
    rb = _returns_from_prices(d, pb)
    strength, n_obs, reason = ers.excess_return_correlation(ra, rb, bench, min_obs=60)
    assert reason is None
    assert n_obs >= 60
    assert strength == pytest.approx(1.0, abs=1e-9)


def test_excess_uncorrelated_near_zero():
    """초과수익이 서로 독립 패턴 → 강도 |값|이 1과 뚜렷이 구분(완전 동조 아님)."""
    d = date(2026, 1, 1)
    n = 80
    bench = _returns_from_prices(d, [100.0 * (1.005 ** i) for i in range(n)])
    # A: 주기 2, B: 주기 3 의 서로소 패턴 → 저상관
    pa, pb = [100.0], [100.0]
    for i in range(1, n):
        pa.append(pa[-1] * (1.02 if i % 2 == 0 else 0.99))
        pb.append(pb[-1] * (1.02 if i % 3 == 0 else 0.995))
    ra = _returns_from_prices(d, pa)
    rb = _returns_from_prices(d, pb)
    strength, n_obs, reason = ers.excess_return_correlation(ra, rb, bench, min_obs=60)
    assert reason is None
    assert strength is not None
    assert abs(strength) < 0.5  # 완전 동조와 뚜렷이 구분


def test_excess_insufficient_history_returns_none():
    """짧은 이력(공통 관측 < min_obs) → 강도 None + insufficient 사유."""
    d = date(2026, 1, 1)
    bench = _returns_from_prices(d, [100.0 + i for i in range(20)])
    ra = _returns_from_prices(d, [50.0 + i for i in range(20)])
    rb = _returns_from_prices(d, [70.0 + i * 0.5 for i in range(20)])
    strength, n_obs, reason = ers.excess_return_correlation(ra, rb, bench, min_obs=60)
    assert strength is None
    assert n_obs < 60
    assert reason.startswith("insufficient_obs")


def test_excess_window_truncates_to_recent():
    """공통 관측이 window_days 초과 시 최근 window_days개만 사용."""
    d = date(2026, 1, 1)
    n = 200
    bench = _returns_from_prices(d, [100.0 * (1.001 ** i) for i in range(n)])
    ra = _returns_from_prices(d, [100.0 * (1.002 ** i) for i in range(n)])
    rb = _returns_from_prices(d, [100.0 * (1.0015 ** i) for i in range(n)])
    strength, n_obs, reason = ers.excess_return_correlation(
        ra, rb, bench, window_days=90, min_obs=60
    )
    assert reason is None
    assert n_obs == 90  # 199 공통 관측 → 최근 90개로 절단


def test_excess_zero_variance_after_benchmark_subtraction():
    """종목 수익이 벤치마크와 항상 동일 → 초과수익 전부 0 → 분산 0 → None(zero_variance)."""
    d = date(2026, 1, 1)
    n = 70
    prices = [100.0 * (1.01 ** i) for i in range(n)]
    bench = _returns_from_prices(d, prices)
    ra = _returns_from_prices(d, prices)  # 벤치와 동일 → 초과수익 0
    rb = _returns_from_prices(d, [100.0 * (1.02 ** i) for i in range(n)])
    strength, n_obs, reason = ers.excess_return_correlation(ra, rb, bench, min_obs=60)
    assert strength is None
    assert reason == "zero_variance"


def test_excess_only_common_dates_used():
    """세 시계열의 공통 거래일만 사용(부분 결측 정합)."""
    d = date(2026, 1, 1)
    n = 70
    bench = _returns_from_prices(d, [100.0 * (1.01 ** i) for i in range(n)])
    ra = _returns_from_prices(d, [100.0 * (1.015 ** i) for i in range(n)])
    # B 는 앞부분 결측(뒤 65일만) → 공통 관측 축소되지만 여전히 >=60
    rb = _returns_from_prices(d + timedelta(days=5), [100.0 * (1.012 ** i) for i in range(n - 5)])
    strength, n_obs, reason = ers.excess_return_correlation(ra, rb, bench, min_obs=60)
    assert reason is None
    assert n_obs <= n - 5
