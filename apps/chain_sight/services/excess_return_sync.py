"""CS-P1B: 초과수익 동조성(excess return synchronization) 계산.

evidence 계층 관계 쌍의 '연결 강도'를 두 종목의 초과수익(일간수익 − 벤치마크수익)
간 Pearson 상관으로 측정한다. 기존 PriceCoMovement(원수익 상관·Neo4j PEER_OF 종속)와
독립 — 소비자 1(chain_sight)이므로 shared 승격 없이 앱 내 순수 함수로 구현(YAGNI).

계층 분리:
  - 순수 함수(`daily_returns`·`excess_return_correlation`·`pearson`)는 DB 무의존 →
    합성 시계열로 단위 테스트. 부동소수·경계(완전 동조·무상관·짧은 이력·분산 0)를 여기서 검증.
  - DB 어댑터(`load_stock_returns`·`load_benchmark_returns`)는 얇게 유지 —
    DailyPrice / macro.MarketIndexPrice 를 읽어 순수 계층에 넘긴다(읽기 전용).

벤치마크: macro.MarketIndexPrice(index='SPY') — Market Pulse가 유지하는 시장 프록시 일별 시계열.
  (주의: shared.stocks.DailyPrice 의 SPY 행은 스테일 — STEP 0-4 실측. macro 쪽이 정본.)

윈도우: 90 거래일(관행 유지). 최소 관측치 60 거래일 미만이면 강도 = None.
"""

from datetime import date as _date, timedelta

# 90 거래일 수익률을 확보하기 위한 캘린더 조회 여유폭(주말·공휴일 흡수).
# 90 거래일 ≈ 126 캘린더일 → 넉넉히 160일 조회 후 순수 계층에서 최근 window_days개로 절단.
GATHER_CALENDAR_DAYS = 160
DEFAULT_WINDOW_DAYS = 90
DEFAULT_MIN_OBS = 60
BENCHMARK_INDEX = "SPY"


def pearson(xs, ys):
    """Pearson 상관계수(순수). 표본<2 또는 한쪽 분산 0이면 None(상관 정의 불가)."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0.0 or syy <= 0.0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / (sxx ** 0.5 * syy ** 0.5)


def daily_returns(prices):
    """(date, price) 이터러블 → {date: 단순수익률}.

    날짜 오름차순 정렬 후 연속 관측 간 r_t = p_t/p_{t-1} − 1 (later date 키).
    price None/0 은 건너뛴다(0 분모 방지). 결측 거래일은 다음 유효 관측과 이어붙여 계산.
    """
    rows = sorted(
        ((d, float(p)) for d, p in prices if p is not None), key=lambda x: x[0]
    )
    out = {}
    prev_d, prev_p = None, None
    for d, p in rows:
        if prev_p is not None and prev_p != 0.0:
            out[d] = p / prev_p - 1.0
        prev_d, prev_p = d, p
    return out


def excess_return_correlation(
    returns_a,
    returns_b,
    returns_bench,
    window_days=DEFAULT_WINDOW_DAYS,
    min_obs=DEFAULT_MIN_OBS,
):
    """두 종목의 초과수익 상관.

    초과수익 = 종목 일간수익 − 벤치마크 일간수익(공통 거래일 한정). 세 시계열이 모두
    존재하는 날짜만 사용, 최근 window_days개로 절단. 공통 관측치 < min_obs 면 강도 None.

    반환: (strength: float|None, n_obs: int, reason: str|None)
      - reason 은 None 이면 정상, 아니면 null 사유(관측 부족 / 분산 0).
    """
    common = sorted(
        set(returns_a) & set(returns_b) & set(returns_bench)
    )
    if window_days is not None and len(common) > window_days:
        common = common[-window_days:]
    n = len(common)
    if n < min_obs:
        return None, n, f"insufficient_obs:{n}<{min_obs}"
    excess_a = [returns_a[d] - returns_bench[d] for d in common]
    excess_b = [returns_b[d] - returns_bench[d] for d in common]
    strength = pearson(excess_a, excess_b)
    if strength is None:
        return None, n, "zero_variance"
    return strength, n, None


# ─────────────────────────── DB 어댑터 (읽기 전용) ───────────────────────────


def _cutoff(asof):
    base = asof or None
    if base is None:
        from django.utils import timezone

        base = timezone.now().date()
    if isinstance(base, _date) and not hasattr(base, "hour"):
        d = base
    else:
        d = base.date() if hasattr(base, "date") else base
    return d - timedelta(days=GATHER_CALENDAR_DAYS)


def load_stock_returns(symbol, cutoff):
    """DailyPrice(close_price) → 일간수익 dict. 읽기 전용."""
    from packages.shared.stocks.models import DailyPrice

    prices = (
        DailyPrice.objects.filter(stock_id=symbol, date__gte=cutoff)
        .values_list("date", "close_price")
    )
    return daily_returns(prices)


def load_benchmark_returns(cutoff, index_symbol=BENCHMARK_INDEX):
    """macro.MarketIndexPrice(close) → 벤치마크 일간수익 dict. 읽기 전용."""
    from macro.models import MarketIndexPrice

    prices = (
        MarketIndexPrice.objects.filter(index_id=index_symbol, date__gte=cutoff)
        .values_list("date", "close")
    )
    return daily_returns(prices)


def compute_pair_strength(
    symbol_a,
    symbol_b,
    returns_bench,
    returns_cache,
    cutoff,
    window_days=DEFAULT_WINDOW_DAYS,
    min_obs=DEFAULT_MIN_OBS,
):
    """한 쌍의 초과수익 동조성 강도. returns_cache 로 종목 수익 재조회 방지.

    반환: (strength|None, n_obs, reason|None)
    """
    if symbol_a not in returns_cache:
        returns_cache[symbol_a] = load_stock_returns(symbol_a, cutoff)
    if symbol_b not in returns_cache:
        returns_cache[symbol_b] = load_stock_returns(symbol_b, cutoff)
    return excess_return_correlation(
        returns_cache[symbol_a],
        returns_cache[symbol_b],
        returns_bench,
        window_days=window_days,
        min_obs=min_obs,
    )
