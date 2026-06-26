"""
독립 오라클 — EventGroup 정책 C leadership 벤치마크 (L3 게이트, 회귀 정답지).

프로덕션 코드(leadership_eventgroup / leadership_service)와 **독립**으로 작성한
느리고 단순한 참조 구현. 최적화·벡터화 안 함(읽기 쉬움 우선). 향후 leadership
정교화의 회귀 정답지로 재사용한다.

독립성:
- 가격/수익률을 DailyPrice에서 직접 재로드(프로덕션 로더 미사용).
- OLS는 numpy.polyfit(프로덕션의 _ols_simple과 다른 구현)로 교차검산.
- 벤치마크 평균·capture는 순수 파이썬 루프.

정책 C:
- 코어 종목 벤치마크 = 코어 자기제외 등가중 평균(LOO).
- 위성 종목 벤치마크 = 전체 코어 등가중 평균(자기 제외 없음).
"""

from datetime import date

import numpy as np

from packages.shared.stocks.models import DailyPrice

TRADING_DAYS = 252


def load_window_returns(symbol: str, as_of: date, window: int) -> list[float] | None:
    """
    as_of 이하 DailyPrice 종가에서 마지막 window+1개 → 일수익률 window개.

    프로덕션 _window_closes/daily_returns와 독립(직접 쿼리·직접 계산).
    종가 부족(<2)이면 None.
    """
    rows = list(
        DailyPrice.objects.filter(stock_id=symbol, date__lte=as_of)
        .order_by("date")
        .values_list("close_price", flat=True)
    )
    closes = [float(c) for c in rows]
    tail = closes[-(window + 1):]
    if len(tail) < 2:
        return None
    rets = []
    for i in range(1, len(tail)):
        prev = tail[i - 1]
        rets.append(tail[i] / prev - 1.0 if prev > 0 else 0.0)
    return rets


def core_loo_benchmark(core_returns: dict[str, list[float]], target: str) -> list[float] | None:
    """코어 자기제외 등가중 평균(순수 루프). 다른 코어 <2면 None."""
    others = [r for s, r in core_returns.items() if s != target]
    others = [r for r in others if len(r) == len(core_returns.get(target, []))]
    if len(others) < 2:
        return None
    n = len(others[0])
    return [sum(o[i] for o in others) / len(others) for i in range(n)]


def core_mean_benchmark(core_returns: dict[str, list[float]], length: int) -> list[float] | None:
    """전체 코어 등가중 평균(순수 루프). 코어 <3이면 None."""
    members = [r for r in core_returns.values() if len(r) == length]
    if len(members) < 3:
        return None
    return [sum(m[i] for m in members) / len(members) for i in range(length)]


def alpha_beta(stock_rets: list[float], bench: list[float]) -> tuple[float, float]:
    """
    numpy.polyfit으로 stock ~ a + b·bench 회귀(프로덕션과 다른 OLS 구현).

    Returns:
        (theme_alpha=a×252, theme_beta=b).
    """
    beta, alpha = np.polyfit(np.asarray(bench), np.asarray(stock_rets), 1)
    return float(alpha) * TRADING_DAYS, float(beta)


def capture(stock_rets: list[float], bench: list[float]) -> tuple[float | None, float | None, float | None]:
    """순수 루프 up/down capture (×100). 분모 0이면 해당 항목 None."""
    up_num = up_den = down_num = down_den = 0.0
    for r_i, r_t in zip(stock_rets, bench):
        if r_t > 0:
            up_num += r_i
            up_den += r_t
        elif r_t < 0:
            down_num += r_i
            down_den += r_t
    up = (up_num / up_den * 100.0) if up_den != 0 else None
    down = (down_num / down_den * 100.0) if down_den != 0 else None
    spread = (up - down) if (up is not None and down is not None) else None
    return up, down, spread
