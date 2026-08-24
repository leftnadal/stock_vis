"""PlaybookContext 조립 (1.6-S1) — compute-on-read, read-only.

체인 8종의 조건이 참조하는 **파생 신호 flat dict**을 한 번에 계산한다. 재료는 전부 기존
수집분(외부 API 신규 호출 0):
  - z-score(14 성분): stress 관례 준용 — RegimeSnapshot 소급 모집단 baseline + to_z(anchor/5d전).
  - anomaly ctx 4종: top10_weight·vix_change_pct·max_abs_sector_z·cross_dispersion(build_context 재사용).
  - 추세/변화/비율: IndicatorValue·MacroSeriesHistory 직접 조회(DTWEXBGS·NFCI·STLFSI4·IG·VIX term).

각 신호는 값이 없으면 None(sources=MISSING) — 조건 평가에서 "데이터 대기"로 흡수.
data_as_of: 신호별 기준일(weekly 정직 표기용).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_cls
from typing import Any

from django.utils import timezone as django_timezone

from apps.market_pulse.anomaly.engine import build_context as anomaly_build_context
from apps.market_pulse.management.commands.backfill_v2_regime_vectors import BACKFILL_MARK
from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.regime import analog, stress
from apps.market_pulse.regime.inputs import ALL_INPUT_KEYS
from apps.market_pulse.regime.zscore import compute_baseline


@dataclass
class PlaybookContext:
    signals: dict[str, float | None] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    data_as_of: dict[str, str] = field(default_factory=dict)
    fetched_at: str = ""

    def get(self, key: str) -> float | None:
        return self.signals.get(key)


def _safe(fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001 — 신호 조립은 하나가 죽어도 나머지 진행(부분 대기 허용)
        return None


def _anchor_and_5d_z() -> tuple[dict[str, float], dict[str, float] | None, dict[str, Any] | None, date_cls | None]:
    """stress 레시피 준용: 고정 소급 모집단 baseline → 최신/5거래일전 z, 최신 raw inputs."""
    pop_rows = list(
        RegimeSnapshot.objects.filter(summary=BACKFILL_MARK, coverage__gte=1.0)
        .order_by("date")
        .values_list("date", "inputs")
    )
    if not pop_rows:
        return {}, None, None, None
    baseline = compute_baseline([inp for _, inp in pop_rows], ALL_INPUT_KEYS)
    live = list(
        RegimeSnapshot.objects.order_by("date").values_list("date", "inputs")
    )
    if not live:
        return {}, None, None, None
    anchor_date, anchor_inputs = live[-1]
    anchor_z = analog.to_z(anchor_inputs or {}, baseline)
    z_5d = analog.to_z(live[-6][1] or {}, baseline) if len(live) >= 6 else None
    return anchor_z, z_5d, anchor_inputs, anchor_date


def _indicator_change(code: str, lookback: int) -> tuple[float | None, date_cls | None]:
    """EconomicIndicator code의 (최신값 − lookback행 전 값), 최신 기준일. 값 절대 변화."""
    from macro.models.indicators import EconomicIndicator, IndicatorValue

    ind = EconomicIndicator.objects.filter(code=code).first()
    if ind is None:
        return None, None
    rows = list(
        IndicatorValue.objects.filter(indicator=ind)
        .order_by("-date")
        .values_list("date", "value")[: lookback + 1]
    )
    if len(rows) < lookback + 1:
        return None, (rows[0][0] if rows else None)
    latest_d, latest_v = rows[0]
    _, prior_v = rows[lookback]
    if latest_v is None or prior_v is None:
        return None, latest_d
    return float(latest_v) - float(prior_v), latest_d


def _indicator_pct_change(code: str, lookback: int) -> tuple[float | None, date_cls | None]:
    from macro.models.indicators import EconomicIndicator, IndicatorValue

    ind = EconomicIndicator.objects.filter(code=code).first()
    if ind is None:
        return None, None
    rows = list(
        IndicatorValue.objects.filter(indicator=ind)
        .order_by("-date")
        .values_list("date", "value")[: lookback + 1]
    )
    if len(rows) < lookback + 1:
        return None, (rows[0][0] if rows else None)
    latest_d, latest_v = rows[0]
    _, prior_v = rows[lookback]
    if not latest_v or not prior_v:
        return None, latest_d
    return (float(latest_v) - float(prior_v)) / abs(float(prior_v)) * 100.0, latest_d


def _series_change(series_id: str, lookback: int) -> float | None:
    """MacroSeriesHistory(series_id) 최신−lookback행전 절대 변화(IG 등)."""
    from apps.credit_signals.models import MacroSeriesHistory

    rows = list(
        MacroSeriesHistory.objects.filter(series_id=series_id)
        .order_by("-date")
        .values_list("value", flat=True)[: lookback + 1]
    )
    if len(rows) < lookback + 1 or rows[0] is None or rows[lookback] is None:
        return None
    return float(rows[0]) - float(rows[lookback])


def _t10y2y_persistence() -> float | None:
    """T10Y2Y 최근 2 변화가 동일 부호면 1.0(지속), 아니면 0.0."""
    from macro.models.indicators import EconomicIndicator, IndicatorValue

    ind = EconomicIndicator.objects.filter(code="T10Y2Y").first()
    if ind is None:
        return None
    vals = list(
        IndicatorValue.objects.filter(indicator=ind)
        .order_by("-date")
        .values_list("value", flat=True)[:3]
    )
    if len(vals) < 3 or any(v is None for v in vals):
        return None
    d1 = float(vals[0]) - float(vals[1])
    d2 = float(vals[1]) - float(vals[2])
    return 1.0 if (d1 > 0 and d2 > 0) or (d1 < 0 and d2 < 0) else 0.0


def build_context(target_date: date_cls | None = None) -> PlaybookContext:
    ctx = PlaybookContext()
    sig = ctx.signals
    src = ctx.sources
    asof = ctx.data_as_of

    def put(key: str, val: float | None, as_of: date_cls | None = None) -> None:
        sig[key] = val
        src[key] = "OK" if val is not None else "MISSING"
        if as_of is not None:
            asof[key] = as_of.isoformat()

    # ── z-score(14 성분) + anchor/5d ──────────────────────────────────
    anchor_z, z_5d, anchor_inputs, anchor_date = _safe(_anchor_and_5d_z) or ({}, None, None, None)
    anchor_z = anchor_z or {}
    for skey, zkey in [
        ("vix_z", "vix"), ("hy_oas_z", "hy_oas_pct"), ("hy_ccc_z", "hy_ccc_oas_pct"),
        ("move_z", "move"), ("return_1d_z", "return_1d_pct"), ("drawdown_z", "drawdown_pct"),
        ("t10y2y_z", "t10y2y_pct"), ("nfci_z", "nfci"), ("vol_20d_z", "vol_20d_pct"),
    ]:
        put(skey, anchor_z.get(zkey), anchor_date)
    # z-변화 5d(확대/급변)
    if z_5d is not None:
        for skey, zkey in [("hy_oas_z_chg5d", "hy_oas_pct"), ("t10y2y_z_chg5d", "t10y2y_pct")]:
            a, b = anchor_z.get(zkey), z_5d.get(zkey)
            put(skey, (a - b) if (a is not None and b is not None) else None, anchor_date)
    else:
        put("hy_oas_z_chg5d", None); put("t10y2y_z_chg5d", None)
    # credit 축 z(anchor)
    cats = _safe(lambda: stress.category_subscores(anchor_z, z_5d)) or []
    credit_z = next((c.get("z") for c in cats if c.get("key") == "credit"), None)
    put("credit_axis_z", credit_z, anchor_date)
    # VIX term ratio(raw vix3m/vix)
    if anchor_inputs:
        vix = anchor_inputs.get("vix"); vix3m = anchor_inputs.get("vix3m")
        ratio = (float(vix3m) / float(vix)) if (vix and vix3m and float(vix) > 0) else None
        put("vix_term_ratio", ratio, anchor_date)
    else:
        put("vix_term_ratio", None)

    # ── anomaly ctx 4종 (build_context 재사용) ────────────────────────
    actx = _safe(lambda: anomaly_build_context(target_date))
    put("top10_weight", getattr(actx, "top10_weight", None) if actx else None)
    put("vix_change_pct", getattr(actx, "vix_change_pct", None) if actx else None)
    put("max_abs_sector_z", getattr(actx, "max_abs_sector_z", None) if actx else None)
    put("cross_dispersion", getattr(actx, "cross_dispersion", None) if actx else None)

    # ── 추세/변화/비율 (직접 조회) ────────────────────────────────────
    dxy_chg, dxy_d = _safe(lambda: _indicator_pct_change("DTWEXBGS", 5)) or (None, None)
    put("dtwexbgs_chg5d", dxy_chg, dxy_d)
    nfci_chg, nfci_d = _safe(lambda: _indicator_change("NFCI", 4)) or (None, None)
    put("nfci_chg4w", nfci_chg, nfci_d)
    stl_chg, stl_d = _safe(lambda: _indicator_change("STLFSI4", 4)) or (None, None)
    put("stlfsi_chg4w", stl_chg, stl_d)
    put("ig_oas_chg5d", _safe(lambda: _series_change("BAMLC0A0CM", 5)))
    dgs_chg, dgs_d = _safe(lambda: _indicator_change("DGS10", 1)) or (None, None)
    put("dgs10_chg1d_abs", abs(dgs_chg) if dgs_chg is not None else None, dgs_d)
    t2y_chg, t2y_d = _safe(lambda: _indicator_change("T10Y2Y", 5)) or (None, None)
    put("t10y2y_chg5d_abs", abs(t2y_chg) if t2y_chg is not None else None, t2y_d)
    put("t10y2y_persist", _safe(_t10y2y_persistence))

    ctx.fetched_at = django_timezone.now().isoformat()
    return ctx
