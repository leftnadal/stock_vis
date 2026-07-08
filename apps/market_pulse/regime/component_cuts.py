"""
MP2-TREND S3(R1) — 국면 재료 판정-거리 파생 (query-time 순수, 모델 저장 0).

소속: apps/market_pulse/regime (intraday classifier 부속 — rules.yaml 단일소스 소비).
역할: rules.yaml의 raw 절대값 복합 룰에서 **지표별 컷 목록을 평탄화 도출**하고,
  스냅샷 inputs 시계열 + 판정-거리(nearest_cut_distance)·통과 컷(crossed_cuts)을 산출.
주의: z-score/정규화 아님 — classifier가 raw 값을 절대 임계와 비교하는 실제 구조를 그대로
  노출(STEP 0 반증 결과, D-TREND-BASELINE-R1). 컷 값은 rules.yaml에서만 로드(하드코딩 0).
소비처: api/views/cards.py::_regime_detail (components payload).
"""

from __future__ import annotations

import operator
from typing import Any

# classifier와 동일 연산자 테이블(단일 진실 — 분기 방향 일치).
_OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}

# S3(R1) 대상 = 룰-구동 7지표(STEP 0 실측 확정). 순서 = 그리드 표시 순서.
TARGET_INDICATORS: list[str] = [
    "vix",
    "move",
    "hy_oas_pct",
    "nfci",
    "t10y2y_pct",
    "t10y3m_pct",
    "drawdown_pct",
]

# 표시 단위(FE 라벨 부기용). _pct 계열 = %, 지수형 = 빈 문자열.
INDICATOR_UNITS: dict[str, str] = {
    "vix": "",
    "move": "",
    "hy_oas_pct": "%",
    "nfci": "",
    "t10y2y_pct": "%",
    "t10y3m_pct": "%",
    "drawdown_pct": "%",
}


def _collect_atoms(clause: Any, regime: str, acc: list[dict[str, Any]]) -> None:
    """룰 조건(any/all/atom 중첩)에서 원자 컷을 재귀 수집 — 복합 구조 평탄화.

    복합 룰의 완전 표현(any/all 의미)은 범위 밖: 컷은 '이 지표가 룰에 등장하는 값'까지만.
    """
    if isinstance(clause, dict):
        if "always" in clause:
            return
        if "any" in clause:
            for sub in clause["any"]:
                _collect_atoms(sub, regime, acc)
            return
        if "all" in clause:
            for sub in clause["all"]:
                _collect_atoms(sub, regime, acc)
            return
        indicator = clause.get("indicator")
        op = clause.get("op")
        value = clause.get("value")
        if indicator is not None and op is not None and value is not None:
            acc.append({"indicator": indicator, "op": op, "value": value, "regime": regime})


def extract_indicator_cuts(rules: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """rules.yaml → {indicator: [{value, regime, op}, ...]} (value 오름차순 정렬)."""
    by_indicator: dict[str, list[dict[str, Any]]] = {}
    for rule in rules.get("rules", []):
        regime = rule.get("regime", "")
        conditions = rule.get("conditions", {})
        atoms: list[dict[str, Any]] = []
        _collect_atoms(conditions, regime, atoms)
        for a in atoms:
            by_indicator.setdefault(a["indicator"], []).append(
                {"value": a["value"], "regime": a["regime"], "op": a["op"]}
            )
    for key in by_indicator:
        by_indicator[key].sort(key=lambda c: c["value"])
    return by_indicator


def _crossed(op: str, current: float, value: float) -> bool:
    return bool(_OPERATORS[op](current, value))


def _distance_to_cut(op: str, current: float, value: float) -> float:
    """미통과 컷까지의 거리(양수 = 아직 통과 전). 비교 방향 존중.

    gt형(>, >=): value - current (올라가야 통과). lt형(<, <=): current - value (내려가야 통과).
    """
    if op in (">", ">="):
        return value - current
    return current - value


def build_components(
    history: list[dict[str, Any]], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    """대상 7지표의 {name, unit, series, cuts, nearest_cut_distance, crossed_cuts}.

    history = 오름차순(과거→현재) 스냅샷 rows(date, inputs JSONField 포함).
    데이터 부족/결손 구간은 null(S2 관행). 컷은 rules.yaml에서만 도출(하드코딩 0).
    """
    cuts_by_ind = extract_indicator_cuts(rules)
    out: list[dict[str, Any]] = []
    for key in TARGET_INDICATORS:
        series = [
            {
                "date": h["date"].isoformat(),
                "value": (h.get("inputs") or {}).get(key),
            }
            for h in history
        ]
        current = series[-1]["value"] if series else None
        cuts = cuts_by_ind.get(key, [])
        crossed: list[dict[str, Any]] = []
        nearest: dict[str, Any] | None = None
        if current is not None:
            for c in cuts:
                if _crossed(c["op"], current, c["value"]):
                    crossed.append(c)
                else:
                    d = _distance_to_cut(c["op"], current, c["value"])
                    if nearest is None or d < nearest["distance"]:
                        nearest = {
                            "cut": c["value"],
                            "regime": c["regime"],
                            "op": c["op"],
                            "distance": round(d, 3),
                        }
        out.append(
            {
                "key": key,
                "unit": INDICATOR_UNITS.get(key, ""),
                "current": current,
                "series": series,
                "cuts": cuts,
                "crossed_cuts": crossed,
                "nearest_cut_distance": nearest,
            }
        )
    return out
