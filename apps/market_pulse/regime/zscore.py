"""MP2-TREND S4 — 국면 성분 z-이상도 baseline + serve-time 산출 (순수 함수).

소속: apps/market_pulse/regime (intraday classifier 부속).
역할: **고정 소급 모집단**(summary='[BACKFILL_V2]' 행)에서 성분별 μ·σ(표본 n−1) baseline
  산출 + z 변환 + 다운샘플. **DB 접근 0** — 입력은 이미 조회된 행 시퀀스(ANALOG 최근접
  매칭이 동일 baseline 함수를 재사용할 단일 소스).
주의: z는 저장하지 않음(serve-time, D-S4-ENDPOINT). 결측 성분 z=null(보간·캐리 생성 금지,
  D-S4 규칙 #3). σ=0 또는 n<MIN_BASELINE_N 성분은 baseline insufficient=True → z 계산 제외.
소비처: api/views/cards.py::_regime_zscore_detail.
"""

from __future__ import annotations

import statistics
from datetime import date as date_cls
from typing import Any

# 기준 분포 최소 표본. 미만이면 baseline insufficient(정직 표기, 발명 금지).
MIN_BASELINE_N = 30
# 최근 구간 일간 유지 영업일 수(그 이전은 주 마지막 영업일 1점으로 다운샘플).
RECENT_DAILY_DAYS = 90


def compute_baseline(
    inputs_rows: list[dict[str, Any] | None], keys: tuple[str, ...] | list[str]
) -> dict[str, dict[str, Any]]:
    """모집단 inputs 행들 → {key: {mean, std, n, insufficient}}.

    inputs_rows = [dict(성분키→값|None), ...] (보통 소급 모집단 행의 inputs JSON).
    std = **표본표준편차(n−1, statistics.stdev)** — 모집단이 아니라 '분포 추정'이므로.
    가드: 결측(None) 제외 후 n<MIN_BASELINE_N 또는 σ==0 → insufficient=True.
    """
    out: dict[str, dict[str, Any]] = {}
    for k in keys:
        vals = [
            r.get(k)
            for r in inputs_rows
            if r and r.get(k) is not None
        ]
        n = len(vals)
        if n < MIN_BASELINE_N:
            out[k] = {"mean": None, "std": None, "n": n, "insufficient": True}
            continue
        mean = statistics.fmean(vals)
        std = statistics.stdev(vals)  # 표본(n−1)
        if std == 0:
            out[k] = {"mean": mean, "std": 0.0, "n": n, "insufficient": True}
            continue
        out[k] = {"mean": mean, "std": std, "n": n, "insufficient": False}
    return out


def z_of(value: float | None, base: dict[str, Any] | None) -> float | None:
    """(value − μ)/σ, 소수 2자리. 결측/기준불충분/σ=0 → None(발명 금지)."""
    if value is None or base is None or base.get("insufficient"):
        return None
    std = base.get("std")
    mean = base.get("mean")
    if not std or mean is None:
        return None
    return round((value - mean) / std, 2)


def downsample(
    rows: list[tuple[date_cls, Any]], *, recent_daily: int = RECENT_DAILY_DAYS
) -> list[tuple[date_cls, Any]]:
    """rows = [(date, inputs), ...] 오름차순. 최근 recent_daily 영업일 = 일간 유지,
    그 이전 = ISO 주별 마지막 영업일 1점(payload 축소). 반환 = 오름차순 축소 리스트.
    """
    if len(rows) <= recent_daily:
        return list(rows)
    older = rows[:-recent_daily]
    recent = rows[-recent_daily:]
    kept: dict[tuple[int, int], tuple[date_cls, Any]] = {}
    for d, inp in older:
        y, w, _ = d.isocalendar()
        kept[(y, w)] = (d, inp)  # 오름차순 → 마지막 대입 = 주 마지막 영업일
    older_ds = [kept[k] for k in sorted(kept)]
    return older_ds + list(recent)
