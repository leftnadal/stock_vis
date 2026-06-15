"""
intraday regime "다음 단계까지 거리"(margin) 산출 (MP-UX-S3b).

소속: apps/market_pulse/regime (app 레이어).
역할: 현재 regime + 14지표 inputs → 인접 상위(더 심각) 단계 진입 조건까지의 지표별 거리.
  rules.yaml은 classifier.load_rules로 **읽기만**(임계 단일소스, FE/하드카피 0). 모델 저장 0(즉석 산출).
주의: intraday(market_pulse, classifier.py 5단계) 전용. EOD(shared, VIX z-score 3단계) 무관.
rules.yaml 평가 순서 = severity 내림차순(CRISIS first … BULL_EXPANSION default last) → 인접 상위 = idx-1.
"""

from __future__ import annotations

from typing import Any

from apps.market_pulse.regime.classifier import load_rules

_GE_OPS = {">=", ">"}
_LE_OPS = {"<=", "<"}


def _flatten_atoms(cond: Any) -> list[dict]:
    """conditions 트리(any/all/atom) → atom 평탄화. atom = {indicator, op, value}.
    nested all/any는 평탄화해 지표별 거리를 모두 보고(집계 해석은 소비처 몫)."""
    out: list[dict] = []
    if not isinstance(cond, dict):
        return out
    if "any" in cond:
        for sub in cond["any"]:
            out.extend(_flatten_atoms(sub))
    elif "all" in cond:
        for sub in cond["all"]:
            out.extend(_flatten_atoms(sub))
    elif "always" in cond:
        pass  # default 단계(BULL_EXPANSION) — 임계 없음
    elif {"indicator", "op", "value"} <= set(cond):
        out.append(
            {"indicator": cond["indicator"], "op": cond["op"], "value": cond["value"]}
        )
    return out


def _to_threshold(op: str, actual: float, value: float) -> float | None:
    """조건이 참이 되기까지 남은 거리(>0 = 미발동, <=0 = 이미 발동)."""
    if op in _GE_OPS:
        return value - actual  # actual이 value까지 올라야 발동
    if op in _LE_OPS:
        return actual - value  # actual이 value까지 내려야 발동
    return None  # ==/!= 등은 거리 정의 안 함


def compute_next_stage_margin(
    regime: str, inputs: dict | None, *, rules: dict | None = None
) -> dict:
    """현재 단계 → 인접 상위(더 심각) 단계 진입까지의 지표별 margin.

    반환: {
      "next_stage": <regime enum|None>,   # None = 최상위(CRISIS) 또는 단계 미상
      "margins": [{indicator, op, threshold, actual, to_threshold}],
      "closest": <margins 중 가장 가까운 미발동 atom|None>,
    }
    임계는 rules.yaml 단일소스(load_rules). 하드카피 없음.
    """
    rules = rules or load_rules()
    rule_list = rules.get("rules", [])
    idx = next(
        (i for i, r in enumerate(rule_list) if r.get("regime") == regime), None
    )
    if idx is None or idx == 0:
        # 단계 미상 또는 이미 최상위(CRISIS) → 다음 상위 단계 없음
        return {"next_stage": None, "margins": [], "closest": None}

    nxt = rule_list[idx - 1]
    atoms = _flatten_atoms(nxt.get("conditions", {}))
    inputs = inputs or {}

    margins: list[dict] = []
    for a in atoms:
        actual = inputs.get(a["indicator"])
        actual_f = float(actual) if isinstance(actual, (int, float)) else None
        td = (
            _to_threshold(a["op"], actual_f, float(a["value"]))
            if actual_f is not None
            else None
        )
        margins.append(
            {
                "indicator": a["indicator"],
                "op": a["op"],
                "threshold": float(a["value"]),
                "actual": actual_f,
                "to_threshold": td,
            }
        )

    # closest = 아직 발동 안 한(to_threshold>0) atom 중 가장 가까운 것. OR-단계의 대표 거리.
    pending = [m for m in margins if m["to_threshold"] is not None and m["to_threshold"] > 0]
    closest = min(pending, key=lambda m: m["to_threshold"]) if pending else None

    return {"next_stage": nxt.get("regime"), "margins": margins, "closest": closest}
