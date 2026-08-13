"""MPS-1 MP-STRESS — 연속 스트레스 스코어 엔진 (결정론 코어, 뉴스·LLM·외부 API 0).

소속: apps/market_pulse/regime (intraday classifier 부속, **판정 무접촉**).
역할: 현행 완전벡터 14지표의 z(S4 baseline)를 가족 균등가중 평균해 **연속 스트레스 스코어**
  + 카테고리 서브스코어(표시축) + 자기역사 백분위 + 방향 2종(스트레스/가격)을 serve-time 산출.
  z 잣대·가족 멤버십·거리 철학은 analog/zscore(D-S4-BASELINE·D-ANALOG-DIST)에서 재사용.
주의:
  - **regime 판정 무접촉**(D-MPS-NO-CLASSIFY-INPUT): classifier·히스테리시스·stress_input 훅 미연결.
    이 스코어는 표시 전용(초판 판정 미입력).
  - 성분 동결(STRESS_SCORE_KEYS = 14): 신규 수집 3종(DTWEXBGS·STLFSI4·SOFR)은 **미편입**
    (수집만 개시, 편입은 S4-REBASE Tier1+2 심사).
  - level_band 문턱·카테고리 매핑은 **잠정**(S4-REBASE/디렉터 재산정 대상). 발명·보간 금지.
소비처: api/views/cards.py::_regime_stress_detail.
"""

from __future__ import annotations

from typing import Any

from apps.market_pulse.regime import analog
from apps.market_pulse.regime.inputs import ALL_INPUT_KEYS

# ── 성분 동결(D-MPS-SCORE) — 스코어는 현행 완전벡터 14지표만 ──────────────
#   신규 수집 3종은 INDICATOR_CODE_MAP(load_inputs 대상)에도 없어 구조적으로 진입 불가.
STRESS_SCORE_KEYS: tuple[str, ...] = ALL_INPUT_KEYS

# 4 유효 축 = analog 가족(stress/financial) + 단독(return_1d_pct·vol_20d_pct).
#   축간 균등가중(각 1.0) → 종합 = 4축 평균. 가족 내부는 균등평균(1/|fam|, analog 거리 철학).
_AXES: tuple[str, ...] = ("stress", "financial", "return_1d_pct", "vol_20d_pct")

# 표시축(카테고리) — **성분명 추론, 코드 라벨 부재**. S4-REBASE/디렉터 확정 대상.
#   합성축(가족)과 다른 축: financial 가족(9)이 신용·금리곡선·금융환경으로 쪼개지고,
#   stress 가족은 변동성(vix·vix3m)과 가격(drawdown)으로 갈라진다.
STRESS_CATEGORIES: dict[str, tuple[str, ...]] = {
    "volatility": ("vix", "vix3m", "move"),
    "credit": ("hy_oas_pct", "hy_ccc_oas_pct"),
    "curve": ("t10y2y_pct", "t10y3m_pct"),
    "financial_conditions": ("nfci", "nfci_credit", "nfci_leverage", "nfci_risk"),
    "price": ("return_1d_pct", "vol_20d_pct", "drawdown_pct"),
}

# level_band 잠정 경계(z 기준) — **S4-REBASE 재산정 대상**(문턱 캘리브레이션은 MPS-1 범위 밖).
STRESS_BAND_LOW = 0.5
STRESS_BAND_HIGH = 1.5


def _mean_present(z: dict[str, float], keys: tuple[str, ...]) -> float | None:
    """keys 중 z에 존재하는 성분만 균등평균(결측 제외, 발명 금지). round 3."""
    vals = [z[k] for k in keys if k in z and z[k] is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def axis_scores(z: dict[str, float]) -> dict[str, float | None]:
    """4 유효 축별 z(가족 평균 + 단독). 없는 축은 None."""
    return {
        "stress": _mean_present(z, analog.REGIME_FAMILIES["stress"]),
        "financial": _mean_present(z, analog.REGIME_FAMILIES["financial"]),
        "return_1d_pct": _mean_present(z, ("return_1d_pct",)),
        "vol_20d_pct": _mean_present(z, ("vol_20d_pct",)),
    }


def composite_score(z: dict[str, float]) -> float | None:
    """종합 스트레스 스코어 = 존재하는 4 유효 축의 균등평균(가족 균등가중 z 평균). round 3."""
    axes = axis_scores(z)
    present = [v for v in axes.values() if v is not None]
    return round(sum(present) / len(present), 3) if present else None


def category_subscores(
    z_today: dict[str, float], z_prior: dict[str, float] | None = None
) -> list[dict[str, Any]]:
    """표시 카테고리별 z 평균 + Δ5d(카피 재료 — '무엇이 올랐나'). z_prior 없으면 d5=None."""
    out: list[dict[str, Any]] = []
    for key, members in STRESS_CATEGORIES.items():
        z_now = _mean_present(z_today, members)
        d5 = None
        if z_prior is not None:
            z_before = _mean_present(z_prior, members)
            if z_now is not None and z_before is not None:
                d5 = round(z_now - z_before, 3)
        out.append({"key": key, "z": z_now, "d5": d5})
    return out


def percentile_of(score: float | None, population_scores: list[float]) -> float | None:
    """당일 스코어의 자기 역사 내 백분위(≤ 비율 × 100). '지난 N 중 상위 %' 재료. round 1.

    높은 스코어 = 높은 스트레스 = 높은 백분위. 모집단 공백 시 None(발명 금지).
    """
    if score is None or not population_scores:
        return None
    n = len(population_scores)
    le = sum(1 for s in population_scores if s <= score)
    return round(le / n * 100.0, 1)


def _sign_state(d5: float | None, d20: float | None) -> str | None:
    if d5 is None or d20 is None:
        return None
    if d5 > 0 and d20 > 0:
        return "worsening"
    if d5 < 0 and d20 < 0:
        return "easing"
    return "mixed"


def stress_direction(
    score_today: float | None,
    score_5d_ago: float | None,
    score_20d_ago: float | None,
) -> dict[str, Any]:
    """스트레스 방향 = 스코어 Δ5거래일·Δ20거래일 부호 조합(worsening/easing/mixed)."""
    d5 = None if score_today is None or score_5d_ago is None else round(score_today - score_5d_ago, 3)
    d20 = None if score_today is None or score_20d_ago is None else round(score_today - score_20d_ago, 3)
    return {"d5": d5, "d20": d20, "state": _sign_state(d5, d20)}


def _vs_ma(close: float | None, ma: float | None) -> str | None:
    if close is None or ma is None:
        return None
    if close > ma:
        return "above"
    if close < ma:
        return "below"
    return "at"


def price_trend(
    spy_close: float | None, ma20: float | None, ma60: float | None
) -> dict[str, Any]:
    """가격 추세 = SPY 종가 vs 20·60일 이동평균(uptrend/downtrend/mixed)."""
    vs20 = _vs_ma(spy_close, ma20)
    vs60 = _vs_ma(spy_close, ma60)
    state: str | None
    if vs20 is None or vs60 is None:
        state = None
    elif vs20 == "above" and vs60 == "above":
        state = "uptrend"
    elif vs20 == "below" and vs60 == "below":
        state = "downtrend"
    else:
        state = "mixed"
    return {"vs_ma20": vs20, "vs_ma60": vs60, "state": state}


def level_band(score: float | None) -> str | None:
    """잠정 밴드(안정/주의/위기). 경계값은 상위 밴드 포함(≥). **S4-REBASE 재산정 대상**."""
    if score is None:
        return None
    if score < STRESS_BAND_LOW:
        return "stable"
    if score < STRESS_BAND_HIGH:
        return "caution"
    return "crisis"
