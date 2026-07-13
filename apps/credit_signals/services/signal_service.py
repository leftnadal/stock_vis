"""
파생 크레딧 신호 계산 서비스 (PR §4).

z-score = Robust Z(MAD 기반, MAD_FLOOR 적용) — Thesis Control 확정 수학 모델과
동일 규약(indicator_scorer.py). 현재 관측치가 3년 롤링 분포 대비 얼마나
벌어졌는지를 나타낸다.

grade 규칙 (§4):
  - z < 1        → gray
  - 1 ≤ z < 2    → yellow
  - z ≥ 2        → orange
  - red          → orange 조건 + (HY_OAS 절대값 ≥ HY_OAS_CRISIS_BP/100), HY_OAS 한정
  - 관측치 60개 미만 → z_score=null, grade=gray (콜드스타트)
"""
import logging
from decimal import Decimal

import numpy as np

from ..constants import (
    DERIVED_SIGNAL_MAP,
    HY_OAS_CRISIS_BP,
    MAD_CONSISTENCY,
    MAD_FLOOR,
    MIN_OBSERVATIONS,
    SIGNAL_SERIES_MAP,
    Z_ORANGE,
    Z_WINDOW_DAYS,
    Z_YELLOW,
)
from ..models import CreditSignalState, MacroSeriesHistory

logger = logging.getLogger(__name__)

_QUANT_Z = Decimal("0.0001")


def robust_z(values) -> float | None:
    """
    시계열 오름차순 값 리스트에서 최신 관측치의 Robust Z(MAD)를 반환.

    관측치가 MIN_OBSERVATIONS 미만이면 None(콜드스타트).
    MAD < MAD_FLOOR(거의 안 움직이는 시리즈)이면 0.0(중립) — Thesis 규약 동형.
    """
    if values is None or len(values) < MIN_OBSERVATIONS:
        return None

    arr = np.asarray(values, dtype=float)
    window = arr[-Z_WINDOW_DAYS:]
    med = np.median(window)
    mad = np.median(np.abs(window - med))

    if mad < MAD_FLOOR:
        return 0.0

    robust_sigma = MAD_CONSISTENCY * mad
    current = window[-1]
    return float((current - med) / robust_sigma)


def grade_from_z(z: float | None, value, signal_key: str) -> str:
    """z-score(+ HY_OAS 절대값 조건)로 grade 판정."""
    if z is None:
        return "gray"
    if z >= Z_ORANGE:
        grade = "orange"
    elif z >= Z_YELLOW:
        grade = "yellow"
    else:
        grade = "gray"

    # red 승격: orange(z≥2) + HY_OAS 절대값 ≥ 임계 (HY_OAS 한정)
    if (
        grade == "orange"
        and signal_key == "HY_OAS"
        and value is not None
        and float(value) >= HY_OAS_CRISIS_BP / 100.0
    ):
        return "red"
    return grade


def compute_signal(signal_key: str) -> CreditSignalState | None:
    """
    단일 signal_key의 원장을 읽어 z/grade를 계산하고 CreditSignalState upsert.
    원장에 데이터가 전혀 없으면 None (상태 미생성).
    """
    series_id = SIGNAL_SERIES_MAP[signal_key]
    rows = list(
        MacroSeriesHistory.objects.filter(series_id=series_id)
        .order_by("date")
        .values_list("date", "value")
    )
    if not rows:
        return None

    dates = [r[0] for r in rows]
    values = [float(r[1]) for r in rows]
    as_of = dates[-1]
    current_value = rows[-1][1]  # Decimal 원본 보존

    z = robust_z(values)
    grade = grade_from_z(z, current_value, signal_key)
    z_dec = None if z is None else Decimal(str(z)).quantize(_QUANT_Z)

    detail = {
        "series_id": series_id,
        "window_days": Z_WINDOW_DAYS,
        "n_obs": len(values),
        "min_obs": MIN_OBSERVATIONS,
        "mad_floor": float(MAD_FLOOR),
        "consistency": MAD_CONSISTENCY,
        "cold_start": z is None,
    }

    state, _ = CreditSignalState.objects.update_or_create(
        signal_key=signal_key,
        defaults={
            "as_of": as_of,
            "value": current_value,
            "z_score": z_dec,
            "grade": grade,
            "detail": detail,
        },
    )
    return state


def compute_derived_signal(key: str) -> CreditSignalState | None:
    """
    파생 스프레드 키(CCC_MINUS_BB / BBB_MINUS_A)를 compute-on-read로 계산.

    두 소스 시리즈(피감·감수)의 원장을 각각 로드 → **날짜 inner-join**(양쪽 다
    있는 날짜만) → 스프레드 = 피감 − 감수 → robust_z → grade_from_z.
    파생키는 signal_key != "HY_OAS" 이므로 red 자동 미발화(orange 상한없음).
    ★ 스프레드값은 CreditSignalState에만 upsert하고 MacroSeriesHistory(원장)에는
      절대 적재하지 않는다(원장 순수성 — raw 관측 전용).
    소스 원장이 비었거나 정합 날짜가 없으면 None(상태 미생성).
    """
    minuend_id, subtrahend_id = DERIVED_SIGNAL_MAP[key]
    m_rows = dict(
        MacroSeriesHistory.objects.filter(series_id=minuend_id)
        .values_list("date", "value")
    )
    s_rows = dict(
        MacroSeriesHistory.objects.filter(series_id=subtrahend_id)
        .values_list("date", "value")
    )
    if not m_rows or not s_rows:
        return None

    common = sorted(set(m_rows) & set(s_rows))
    if not common:
        return None

    spreads = [m_rows[d] - s_rows[d] for d in common]  # Decimal − Decimal (원본 정밀도 보존)
    as_of = common[-1]
    current_spread = spreads[-1]
    values = [float(x) for x in spreads]

    z = robust_z(values)
    grade = grade_from_z(z, current_spread, key)  # key != HY_OAS → red 미발화
    z_dec = None if z is None else Decimal(str(z)).quantize(_QUANT_Z)

    n_dropped = len(set(m_rows) | set(s_rows)) - len(common)
    detail = {
        "derived": True,
        "minuend": minuend_id,
        "subtrahend": subtrahend_id,
        "n_aligned": len(common),
        "n_dropped": n_dropped,
        "window_days": Z_WINDOW_DAYS,
        "n_obs": len(values),
        "min_obs": MIN_OBSERVATIONS,
        "mad_floor": float(MAD_FLOOR),
        "consistency": MAD_CONSISTENCY,
        "cold_start": z is None,
    }

    state, _ = CreditSignalState.objects.update_or_create(
        signal_key=key,
        defaults={
            "as_of": as_of,
            "value": current_spread,
            "z_score": z_dec,
            "grade": grade,
            "detail": detail,
        },
    )
    return state


def compute_all_signals() -> dict:
    """
    수집 대상 6 raw signal_key + 파생 2키 전부 계산 (flag 무관 — 서비스 계층 진입점).
    태스크(compute_credit_signals_task)와 백필 커맨드가 공유한다.
    """
    results = {}
    for signal_key in SIGNAL_SERIES_MAP:
        state = compute_signal(signal_key)
        results[signal_key] = None if state is None else state.grade
    for key in DERIVED_SIGNAL_MAP:
        state = compute_derived_signal(key)
        results[key] = None if state is None else state.grade
    return results
