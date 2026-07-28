"""MP2-ANALOG Slice B — 유사 국면 매칭 엔진 (결정론 코어, 뉴스·LLM 무의존).

소속: apps/market_pulse/regime (Phase2 촉발 표면).
역할: 오늘 국면 z-벡터 vs 소급 모집단(완전벡터 683) 가족가중 거리 → 최근접 이웃(②C) +
  이웃별 SPY 선도수익률 → 지평별 정직 팬(①C). z 잣대 = S4 baseline(compute_baseline) 재사용.
주의: **결정론**(뉴스·LLM·외부 API 0). 가족 멤버십은 사이클 2 판정 시점 **동결**(S4-REBASE만 재판정).
  문턱(K·τ_radius·τ_alert·지평·군집창)은 **잠정**(Phase5/S4-REBASE 재산정).
소비처: api/views/cards.py::_regime_analog_detail.
"""

from __future__ import annotations

import statistics
from datetime import date as date_cls
from typing import Any

from apps.market_pulse.regime.inputs import ALL_INPUT_KEYS

# ── 가족 멤버십(동결, D-ANALOG-DIST 사이클2 판정) ──
# ANALOG-STEP0 상관 실측(683 완전벡터) = 2단 사다리: |ρ|≥0.7 군집 2개(가족간|ρ|0.178<0.5).
#   FAM 내부는 접고(가중 1/|fam|), 단독 성분은 유효 축 1. 총 14성분 → 유효 축 4.
REGIME_FAMILIES: dict[str, tuple[str, ...]] = {
    "stress": ("drawdown_pct", "vix", "vix3m"),
    "financial": (
        "nfci", "nfci_credit", "nfci_leverage", "nfci_risk",
        "hy_oas_pct", "hy_ccc_oas_pct", "t10y2y_pct", "t10y3m_pct", "move",
    ),
}
SINGLETON_KEYS: tuple[str, ...] = ("return_1d_pct", "vol_20d_pct")

# ── 잠정 문턱(Phase5/S4-REBASE 재산정) ──
TAU_RADIUS = 0.60      # ②C: 이웃 후보 최대 거리
K_MAX = 8              # ②C: 최대 이웃 수
TAU_ALERT = 0.80       # ②C: 최근접 > τ_alert → "전례 희박" 경보
SEP_MIN_DAYS = 10      # 트랙 헌법: 선정 이웃 상호 최소 10영업일 분리(같은 에피소드 중복 방지)
CLUSTER_WINDOW = 60    # ①C n_eff: 상호 60영업일 내 이웃 = 한 에피소드로 접기
HORIZONS: tuple[int, ...] = (1, 5, 10, 20, 60)


def component_weights() -> dict[str, float]:
    """성분별 가중 wᵢ = 1/|가족| (단독 = 1). 유효 축 합 = 4."""
    w: dict[str, float] = {}
    for members in REGIME_FAMILIES.values():
        for k in members:
            w[k] = 1.0 / len(members)
    for k in SINGLETON_KEYS:
        w[k] = 1.0
    return w


def to_z(inputs: dict[str, Any] | None, baseline: dict[str, dict[str, Any]]) -> dict[str, float]:
    """inputs(성분→raw) → {key: z}. 결측·기준불충분 성분은 제외(발명 금지)."""
    out: dict[str, float] = {}
    if not inputs:
        return out
    for k in ALL_INPUT_KEYS:
        b = baseline.get(k)
        x = inputs.get(k)
        if x is None or b is None or b.get("insufficient") or not b.get("std"):
            continue
        out[k] = (x - b["mean"]) / b["std"]
    return out


def distance_sq(z_a: dict[str, float], z_b: dict[str, float], weights: dict[str, float]) -> float | None:
    """가족가중 거리제곱 d² = Σ wᵢ(z_a−z_b)². 공통 성분 없으면 None."""
    common = [k for k in weights if k in z_a and k in z_b]
    if not common:
        return None
    return sum(weights[k] * (z_a[k] - z_b[k]) ** 2 for k in common)


def select_neighbors(
    today_z: dict[str, float],
    population: list[tuple[date_cls, dict[str, float]]],
    weights: dict[str, float],
    *,
    tau_radius: float = TAU_RADIUS,
    k_max: int = K_MAX,
    sep_min_days: int = SEP_MIN_DAYS,
) -> tuple[list[dict[str, Any]], float | None]:
    """②C: 거리 오름차순, radius 안, 상호 sep_min_days 분리로 최대 K 선정.
    반환 (neighbors[{date, dist}], nearest_dist). nearest_dist = radius 무관 최소 거리(경보용).
    """
    scored: list[tuple[float, date_cls]] = []
    for d, z in population:
        d2 = distance_sq(today_z, z, weights)
        if d2 is None:
            continue
        scored.append((d2 ** 0.5, d))
    scored.sort(key=lambda t: (t[0], t[1]))
    nearest = scored[0][0] if scored else None

    picked: list[dict[str, Any]] = []
    for dist, d in scored:
        if dist > tau_radius:
            break
        if any(abs((d - p["date"]).days) < sep_min_days for p in picked):
            continue  # 같은 에피소드 근접일 배제(≥10영업일 분리)
        picked.append({"date": d, "dist": round(dist, 4)})
        if len(picked) >= k_max:
            break
    return picked, nearest


def is_alert(nearest_dist: float | None, *, tau_alert: float = TAU_ALERT) -> bool:
    """②C 경보: 최근접 거리 > τ_alert(또는 이웃 0) → '전례 희박 — 통계 보류'."""
    return nearest_dist is None or nearest_dist > tau_alert


def _n_eff(dates: list[date_cls], *, window: int = CLUSTER_WINDOW) -> int:
    """유효표본 = 상호 window영업일(근사: 달력일 window*1.5) 내 이웃을 한 에피소드로 접은 수."""
    if not dates:
        return 0
    ordered = sorted(dates)
    clusters = 1
    anchor = ordered[0]
    for d in ordered[1:]:
        if (d - anchor).days > window * 1.5:  # 영업일→달력일 근사
            clusters += 1
            anchor = d
    return clusters


def build_fan(
    neighbor_fwd: list[dict[str, Any]],
    *,
    horizons: tuple[int, ...] = HORIZONS,
    k: int | None = None,
) -> list[dict[str, Any]]:
    """①C 정직 팬: 지평별 중앙값 + IQR 밴드 × √(K/n_eff), 가용 N·n_eff 노출.

    neighbor_fwd = [{date, fwd:{h: ret|None}}, ...]. 지평별로 실현(non-null) 이웃만 집계(정직 N).
    밴드 확대 √(K/n_eff): n_eff = 실현 이웃의 시간군집 접기 수(에피소드 중복 시 밴드 확대).
    """
    k = k if k is not None else len(neighbor_fwd)
    fan: list[dict[str, Any]] = []
    for h in horizons:
        vals: list[float] = []
        dates: list[date_cls] = []
        for nb in neighbor_fwd:
            r = nb["fwd"].get(h)
            if r is not None:
                vals.append(r)
                dates.append(nb["date"])
        n = len(vals)
        if n == 0:
            fan.append({"horizon": h, "median": None, "lo": None, "hi": None, "n": 0, "n_eff": 0})
            continue
        med = statistics.median(vals)
        if n >= 2:
            q = statistics.quantiles(vals, n=4)  # [q1,q2,q3]
            lo_raw, hi_raw = q[0], q[2]
        else:
            lo_raw = hi_raw = med
        neff = _n_eff(dates)
        widen = (k / neff) ** 0.5 if neff else 1.0
        lo = med - (med - lo_raw) * widen
        hi = med + (hi_raw - med) * widen
        fan.append({
            "horizon": h,
            "median": round(med, 5),
            "lo": round(lo, 5),
            "hi": round(hi, 5),
            "n": n,
            "n_eff": neff,
        })
    return fan


def forward_returns(
    ref_date: date_cls,
    price_index: dict[date_cls, int],
    closes: list[float],
    *,
    horizons: tuple[int, ...] = HORIZONS,
) -> dict[int, float | None]:
    """ref_date 기준 +h 거래일 SPY 수익률. price_index=거래일→위치, closes=위치별 종가.

    T+h가 시리즈 밖(우변 절단)이면 None(정직 — ①C 지평별 가용 N에 반영).
    """
    i = price_index.get(ref_date)
    out: dict[int, float | None] = {}
    n = len(closes)
    for h in horizons:
        if i is None or i + h >= n or closes[i] in (0, None):
            out[h] = None
        else:
            out[h] = round(closes[i + h] / closes[i] - 1.0, 6)
    return out
