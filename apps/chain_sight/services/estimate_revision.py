"""
C8 추정치 리비전 괴리 (TH-4) — estimate revision divergence.

설계 앵커 theme_heat_design.md §2 C8 (v1.2.2 판정 준수):
  C8_raw = z(가격 60일 수익률) − z(EPS 컨센서스 60일 변화)
  부호: 양수 = 가격↑·이익 미확인 = 멀티플 단독 팽창 = **과열 기여**. EPS 상향 → C8 하락.

레그 (둘 중 하나라도 죽으면 C8 = None, 반쪽 계산 금지 — verifier 판정 2026-07-08):
  - EPS 레그: 현재 스냅샷 vs **lag 8**(56일) 스냅샷 diff, lag 8 부재 시 **lag 9**(63일) 폴백.
  - 가격 레그: DailyPrice 기반 **60 캘린더일 수익률**.

z_mode (양 레그 **공동** 적용 — 스케일 정합, 결정7):
  - 전환 키 = 해당 종목의 **유효 EPS diff 개수**(EPS 레그가 binding constraint, 단일 기준).
  - < 26 → cold-start: 양 레그 **cross-sectional z**(그 날짜 단면). 단면(양 레그 성립 종목) < 30
    → 그 날짜 cross-sectional 종목 C8 전체 None(얇은 단면 z 금지).
  - ≥ 26 → **time-series z**(종목별 자기 역사). 한 종목 안에서 레그 간 모드 혼합 금지.
  - z_mode 기록 = 'time_series' | 'cross_sectional' | null(C8 None).

결정7이 §5.3(시스템 전체·시간 기반 전환)을 대체 — DECISIONS 2026-07-08, 설계 v1.2.2 §5.3 주석.

순수 함수(주입 데이터로 테스트) + DB 로더 분리. winsorize/클리핑 없음(C1~C7 관례 = 순수 z).
"""

import logging
from datetime import date, timedelta
from typing import Optional

from apps.chain_sight.services.heat_components import (
    c8_estimate_revision,
    cross_sectional_z,
    timeseries_z,
)

logger = logging.getLogger(__name__)

# ── 임계 상수 (단일 정의 지점 — 하드코딩 산재 금지) ──
LAG_PRIMARY_DAYS = 56          # lag 8 (8주) — 60일 근사 기본
LAG_FALLBACK_DAYS = 63         # lag 9 (9주) — lag 8 부재 시 폴백
Z_MODE_TS_THRESHOLD = 26       # 유효 EPS diff ≥ 26 → time_series (반년 표본 = 시계열 std 최소)
CROSS_SECTIONAL_MIN_SYMBOLS = 30  # 단면 z 최소 표본 (얇은 단면 z 금지)
PRICE_TOL_DAYS = 7             # 가격 조회 시 거래일 근사 허용(주말·공휴 대비)
PRICE_RETURN_WINDOW_DAYS = 60


# ────────────────────────────── EPS 레그 (스냅샷 diff) ──────────────────────────────
def eps_diff_at(eps_by_date: dict, anchor: date) -> Optional[float]:
    """
    anchor 스냅샷의 60일 EPS diff = eps[anchor] − eps[anchor − lag]. lag 8(56d)→9(63d) 폴백.

    lag 8·9 모두 부재 → None (diff 미성립). eps_by_date = {snapshot_date: eps_avg} (단일 FY).
    """
    cur = eps_by_date.get(anchor)
    if cur is None:
        return None
    for lag in (LAG_PRIMARY_DAYS, LAG_FALLBACK_DAYS):
        prev = eps_by_date.get(anchor - timedelta(days=lag))
        if prev is not None:
            return float(cur) - float(prev)
    return None


def valid_eps_diff_dates(eps_by_date: dict, up_to: date) -> list[date]:
    """diff 가 성립하는(lag 8/9 파트너 존재) 스냅샷 날짜들 (≤ up_to). 카운트 = len."""
    return [
        d for d in sorted(eps_by_date)
        if d <= up_to and eps_diff_at(eps_by_date, d) is not None
    ]


def valid_eps_diff_count(eps_by_date: dict, up_to: date) -> int:
    """
    유효 EPS diff 개수 — **달력이 아니라 실제 diff 수**(수집 결손 구멍은 카운트에서 자동 누락).

    z_mode 전환의 단일 기준 (≥ Z_MODE_TS_THRESHOLD → time_series).
    """
    return len(valid_eps_diff_dates(eps_by_date, up_to))


# ────────────────────────────── 가격 레그 (60일 수익률) ──────────────────────────────
def _price_on_or_before(prices_by_date: dict, target: date, tol_days: int = PRICE_TOL_DAYS):
    """target 이하 가장 가까운 거래일 종가 (주말·공휴 근사, tol_days 이내). 없으면 None."""
    for i in range(tol_days + 1):
        p = prices_by_date.get(target - timedelta(days=i))
        if p is not None:
            return float(p)
    return None


def price_return_60d(
    prices_by_date: dict, as_of: date, window_days: int = PRICE_RETURN_WINDOW_DAYS
) -> Optional[float]:
    """
    60 캘린더일 수익률 = (P[as_of] − P[as_of−60d]) / P[as_of−60d]. 근사 거래일 허용.

    양 끝 가격 결측/시점가 0 → None (가격 레그 미성립 → C8 None).
    """
    end = _price_on_or_before(prices_by_date, as_of)
    start = _price_on_or_before(prices_by_date, as_of - timedelta(days=window_days))
    if end is None or start is None or start == 0:
        return None
    return (end - start) / start


# ────────────────────────────── z_mode 판정 ──────────────────────────────
def resolve_z_mode(valid_diff_count: int) -> str:
    """유효 EPS diff 개수 → 모드. ≥ 임계 → time_series, 미만 → cross_sectional (결정7)."""
    return "time_series" if valid_diff_count >= Z_MODE_TS_THRESHOLD else "cross_sectional"


# C8 성분 조립기 = heat_components.c8_estimate_revision (단일 정의, 계약·부호 단일 소스)
_c8_component = c8_estimate_revision


def compute_c8_for_symbols(symbol_series: dict, as_of: date) -> tuple[dict, dict]:
    """
    유니버스 종목별 C8 성분 계산 + 혼합 비율 로그.

    symbol_series = {symbol: {"eps_by_date": {date: eps_avg}, "price_by_date": {date: close}}}
      (eps_by_date 는 단일 FY 시리즈. DB 로더가 차기 FY 로 구성.)
    반환 = ({symbol: c8_component}, mixing_log={"ts":N,"cs":M,"none":K}).

    절차: 현재 레그 산출 → 양 레그 성립 종목 단면 구성(≥30 가드) → 종목별 mode 판정 →
    cross_sectional/time_series z → C8_raw = z_price − z_eps.
    """
    # 1) 현재 레그 + 카운트
    legs: dict[str, dict] = {}
    for sym, data in symbol_series.items():
        eps_by = data.get("eps_by_date", {})
        px_by = data.get("price_by_date", {})
        eps_diff = eps_diff_at(eps_by, as_of)
        px_ret = price_return_60d(px_by, as_of)
        legs[sym] = {
            "eps_diff": eps_diff,
            "px_ret": px_ret,
            "count": valid_eps_diff_count(eps_by, as_of),
            "both_valid": eps_diff is not None and px_ret is not None,
            "eps_by": eps_by,
            "px_by": px_by,
        }

    # 2) 단면 모집단 = 양 레그 성립 종목 (≥30 가드)
    both_valid = [s for s, L in legs.items() if L["both_valid"]]
    cs_ok = len(both_valid) >= CROSS_SECTIONAL_MIN_SYMBOLS
    cs_eps_pop = [legs[s]["eps_diff"] for s in both_valid]
    cs_px_pop = [legs[s]["px_ret"] for s in both_valid]

    # 3) 종목별 z
    components: dict[str, dict] = {}
    mix = {"ts": 0, "cs": 0, "none": 0}
    for sym, L in legs.items():
        if not L["both_valid"]:
            components[sym] = _c8_component(None, None, None, missing_reason="c8_leg_missing")
            mix["none"] += 1
            continue

        mode = resolve_z_mode(L["count"])
        raw = {
            "eps_diff": L["eps_diff"], "price_return_60d": L["px_ret"],
            "eps_diff_count": L["count"], "z_mode": mode,
        }

        if mode == "cross_sectional":
            if not cs_ok:
                components[sym] = _c8_component(
                    None, None, None, raw=raw, missing_reason="c8_thin_cross_section"
                )
                mix["none"] += 1
                continue
            z_eps = cross_sectional_z(L["eps_diff"], cs_eps_pop, min_n=CROSS_SECTIONAL_MIN_SYMBOLS)
            z_px = cross_sectional_z(L["px_ret"], cs_px_pop, min_n=CROSS_SECTIONAL_MIN_SYMBOLS)
        else:  # time_series — 종목 자기 역사 (양 레그 동일 스냅샷 날짜에서)
            hist_dates = valid_eps_diff_dates(L["eps_by"], as_of)
            eps_hist = [eps_diff_at(L["eps_by"], d) for d in hist_dates]
            px_hist = [price_return_60d(L["px_by"], d) for d in hist_dates]
            px_hist = [x for x in px_hist if x is not None]
            z_eps = timeseries_z(L["eps_diff"], eps_hist)
            z_px = timeseries_z(L["px_ret"], px_hist)

        comp = _c8_component(z_px, z_eps, mode, raw=raw)
        components[sym] = comp
        if comp["missing_reason"] is not None:
            mix["none"] += 1
        elif mode == "time_series":
            mix["ts"] += 1
        else:
            mix["cs"] += 1

    logger.info(
        "z_mode mix: ts=%d cs=%d none=%d (as_of=%s, both_valid=%d, cs_ok=%s)",
        mix["ts"], mix["cs"], mix["none"], as_of, len(both_valid), cs_ok,
    )
    return components, mix


# ────────────────────────────── DB 로더 (TH-5 Heat beat 용) ──────────────────────────────
def compute_c8_from_db(
    symbols, as_of: date, fiscal_year: Optional[int] = None
) -> tuple[dict, dict]:
    """
    EstimateSnapshot + DailyPrice 로 symbol_series 구성 → compute_c8_for_symbols.

    fiscal_year 기본 = 차기(as_of.year + 1) — C1 Fwd P/E 와 정합(전방 추정 리비전). 스냅샷
    축적 0 인 콜드 스타트 단계에선 전종목 leg_missing (정상 — beat 첫 발화 후 누적).
    """
    from apps.chain_sight.models import EstimateSnapshot
    from packages.shared.stocks.models import DailyPrice

    syms = [s.upper() for s in symbols]
    if not syms:
        return {}, {"ts": 0, "cs": 0, "none": 0}
    fy = fiscal_year if fiscal_year is not None else as_of.year + 1

    # EPS 스냅샷 (단일 FY) → {symbol: {snapshot_date: eps_avg}}
    eps_rows = EstimateSnapshot.objects.filter(
        symbol__in=syms, fiscal_year=fy, snapshot_date__lte=as_of, eps_avg__isnull=False
    ).values_list("symbol", "snapshot_date", "eps_avg")
    eps_map: dict[str, dict] = {}
    earliest = as_of
    for sym, d, eps in eps_rows:
        eps_map.setdefault(sym, {})[d] = float(eps)
        earliest = min(earliest, d)

    # 가격 (가장 이른 스냅샷 − 60d 여유 ~ as_of)
    px_start = earliest - timedelta(days=PRICE_RETURN_WINDOW_DAYS + PRICE_TOL_DAYS + 7)
    px_rows = DailyPrice.objects.filter(
        stock__symbol__in=syms, date__gte=px_start, date__lte=as_of
    ).values_list("stock__symbol", "date", "close_price")
    px_map: dict[str, dict] = {}
    for sym, d, close in px_rows:
        px_map.setdefault(sym, {})[d] = float(close)

    symbol_series = {
        s: {"eps_by_date": eps_map.get(s, {}), "price_by_date": px_map.get(s, {})}
        for s in syms
    }
    return compute_c8_for_symbols(symbol_series, as_of)
