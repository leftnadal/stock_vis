"""
주도주 지표 엔진 v1 — 종목 레벨 4지표 (CS-M2).

M1(StockAttentionScore, 거래 기반)과 별개 신규 엔진. 종목 레벨 4지표만:
  T2  추세품질    trend_quality = (slope × 252) × R²       (윈도우별, 테마무관)
  T3  테마알파/베타 theme_alpha = α × 252, theme_beta = β     (윈도우별, LOO 회귀)
  ②   포착률       up_capture / down_capture / capture_spread (윈도우별, LOO)

설계 사실(확정):
- WINDOWS=[20, 120], MIN_OBS_RATIO=0.8, MIN_THEME_MEMBERS=3.
- T2·T3 단순 가산 금지(ρ=0.66 중복) — 분리 노출. 합성 단일점수 만들지 말 것.
- 회귀는 LOO(자기 제외 등가중 테마평균) 기본.
- 룩어헤드 금지: t지표는 t까지 데이터만 사용.
- 정규화는 표시단(serializer) — 산출은 raw 보존, 게이트 미달은 NULL(에러 아님).

이 모듈은 순수 함수만 노출(DB 접근 없음). 영속/로드는 Slice 3 서비스에서.
"""

from __future__ import annotations

import math

import numpy as np

# ── 상수 ──────────────────────────────────────────────────────────────────────
WINDOWS = [20, 120]
MIN_OBS_RATIO = 0.8
MIN_THEME_MEMBERS = 3
TRADING_DAYS = 252


# ── OLS 헬퍼 ──────────────────────────────────────────────────────────────────

def _ols_simple(x: list[float], y: list[float]) -> tuple[float, float, float] | None:
    """
    단순 OLS: y ~ a + b·x.

    Returns:
        (intercept a, slope b, r_squared) — 또는 분산 0/관측 부족 시 None.
    """
    n = len(x)
    if n < 2 or len(y) != n:
        return None

    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)

    x_mean = xa.mean()
    y_mean = ya.mean()
    dx = xa - x_mean
    dy = ya - y_mean

    sxx = float((dx * dx).sum())
    if sxx == 0.0:
        return None  # x 분산 0 → 회귀 불가

    sxy = float((dx * dy).sum())
    slope = sxy / sxx
    intercept = float(y_mean - slope * x_mean)

    # R² = 1 - SSE/SST
    syy = float((dy * dy).sum())
    if syy == 0.0:
        # y 분산 0: 완전 평탄. 잔차 0이면 R²=1, 그 외엔 정의 모호 → 0.
        r_squared = 1.0 if sxy == 0.0 else 0.0
    else:
        sse = syy - slope * sxy
        r_squared = 1.0 - sse / syy
        # 수치 오차 클리핑
        r_squared = max(0.0, min(1.0, r_squared))

    return intercept, slope, r_squared


# ── T2: 추세품질 ──────────────────────────────────────────────────────────────

def trend_quality(closes: list[float]) -> dict | None:
    """
    윈도우 내 log(close) ~ t OLS → slope, R².

    trend_quality = (slope × 252) × R².

    Args:
        closes: 윈도우 내 종가 시계열(시간순). 양수 종가만 유효.

    Returns:
        {"slope": annualized_slope_pre_R2?, "r_squared", "trend_quality"} 또는 None.
        반환 slope는 일별 로그-기울기(raw). 게이트/룩어헤드 판정은 호출측 책임.
    """
    if not closes:
        return None
    # 로그 변환 — 비양수 종가는 무효
    if any(c is None or c <= 0 for c in closes):
        return None

    n = len(closes)
    if n < 2:
        return None

    t = list(range(n))
    log_close = [math.log(c) for c in closes]

    res = _ols_simple(t, log_close)
    if res is None:
        return None

    _intercept, slope, r2 = res
    tq = (slope * TRADING_DAYS) * r2
    return {
        "slope": slope,
        "r_squared": r2,
        "trend_quality": tq,
    }


# ── 일수익률 헬퍼 ─────────────────────────────────────────────────────────────

def daily_returns(closes: list[float]) -> list[float]:
    """종가 시계열 → 단순 일수익률 list (길이 n-1). 비양수 직전종가는 0.0."""
    out = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        cur = closes[i]
        if prev and prev > 0:
            out.append(cur / prev - 1.0)
        else:
            out.append(0.0)
    return out


def loo_theme_returns(
    member_returns: dict[str, list[float]],
    target_symbol: str,
) -> list[float] | None:
    """
    자기 제외(LOO) 등가중 테마 일수익률.

    Args:
        member_returns: {symbol: [일수익률...]} — 동일 길이 정렬 가정.
        target_symbol: 제외할 종목.

    Returns:
        타깃 제외 멤버들의 일별 등가중 평균 수익률 list. 멤버 < MIN_THEME_MEMBERS
        (자기 포함) → None. 길이 불일치 멤버는 제외.
    """
    if target_symbol not in member_returns:
        return None
    if len(member_returns) < MIN_THEME_MEMBERS:
        return None

    target_len = len(member_returns[target_symbol])
    if target_len == 0:
        return None

    others = [
        r for s, r in member_returns.items()
        if s != target_symbol and len(r) == target_len
    ]
    if not others:
        return None

    arr = np.asarray(others, dtype=float)  # (m, target_len)
    return arr.mean(axis=0).tolist()


# ── T3: 테마 알파/베타 ────────────────────────────────────────────────────────

def theme_alpha_beta(
    stock_returns: list[float],
    theme_loo_returns: list[float],
) -> dict | None:
    """
    r_i ~ α + β·r_theme_LOO + ε OLS.

    theme_alpha = α × 252, theme_beta = β.

    Args:
        stock_returns: 타깃 종목 일수익률.
        theme_loo_returns: 동일 일자의 자기 제외 등가중 테마 일수익률.

    Returns:
        {"theme_alpha", "theme_beta", "r_squared"} 또는 None(분산 0/길이 불일치/부족).
    """
    if not stock_returns or not theme_loo_returns:
        return None
    if len(stock_returns) != len(theme_loo_returns):
        return None
    if len(stock_returns) < 2:
        return None

    res = _ols_simple(theme_loo_returns, stock_returns)
    if res is None:
        return None

    alpha, beta, r2 = res
    return {
        "theme_alpha": alpha * TRADING_DAYS,
        "theme_beta": beta,
        "r_squared": r2,
    }


# ── ②: 포착률 ─────────────────────────────────────────────────────────────────

def capture_ratios(
    stock_returns: list[float],
    theme_loo_returns: list[float],
) -> dict | None:
    """
    포착률(capture ratio).

    up   = (Σ r_i over theme>0 days) / (Σ r_theme over theme>0 days) × 100
    down = (Σ r_i over theme<0 days) / (Σ r_theme over theme<0 days) × 100
    capture_spread = up − down.

    분모 0(상승일 또는 하락일 부재 / 합 0) → 해당 항목 None.

    Returns:
        {"up_capture", "down_capture", "capture_spread"} 또는 None(길이 불일치/빈입력).
        개별 항목은 분모 0 시 None일 수 있고, 그 경우 capture_spread도 None.
    """
    if not stock_returns or not theme_loo_returns:
        return None
    if len(stock_returns) != len(theme_loo_returns):
        return None

    up_num = up_den = 0.0
    down_num = down_den = 0.0
    for r_i, r_t in zip(stock_returns, theme_loo_returns):
        if r_t > 0:
            up_num += r_i
            up_den += r_t
        elif r_t < 0:
            down_num += r_i
            down_den += r_t

    up = (up_num / up_den * 100.0) if up_den != 0.0 else None
    down = (down_num / down_den * 100.0) if down_den != 0.0 else None
    spread = (up - down) if (up is not None and down is not None) else None

    return {
        "up_capture": up,
        "down_capture": down,
        "capture_spread": spread,
    }


# ── 윈도우 게이트 ─────────────────────────────────────────────────────────────

def passes_obs_gate(valid_obs: int, window: int) -> bool:
    """윈도우 내 유효 관측일이 window × MIN_OBS_RATIO 이상이면 True."""
    return valid_obs >= window * MIN_OBS_RATIO
