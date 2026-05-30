"""Market Pulse v2 — Regime Classifier engine (PR-C)."""

from __future__ import annotations

import logging
import operator
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.regime.inputs import RegimeInputs

logger = logging.getLogger(__name__)

RULES_PATH = Path(__file__).parent / "rules.yaml"

OPERATORS: dict[str, Any] = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


@dataclass
class _RulesCache:
    mtime: float = 0.0
    data: dict[str, Any] | None = None


_cache = _RulesCache()


def load_rules(path: Path | None = None, *, force: bool = False) -> dict[str, Any]:
    p = path or RULES_PATH
    mtime = os.path.getmtime(p)
    if not force and _cache.data is not None and _cache.mtime == mtime:
        return _cache.data
    with open(p) as f:
        data = yaml.safe_load(f)
    _cache.mtime = mtime
    _cache.data = data
    return data


def _eval_atom(
    atom: dict[str, Any], inputs: RegimeInputs
) -> tuple[bool | None, str | None]:
    indicator = atom.get("indicator")
    op_str = atom.get("op")
    value = atom.get("value")
    if indicator is None or op_str is None or value is None:
        raise ValueError(f"invalid atom: {atom}")
    if op_str not in OPERATORS:
        raise ValueError(f"unknown operator: {op_str}")
    actual = getattr(inputs, indicator, None)
    if actual is None:
        return None, indicator
    return OPERATORS[op_str](actual, value), indicator


def _eval_clause(clause, inputs: RegimeInputs, fired: list[str]) -> bool | None:
    if isinstance(clause, dict):
        if "always" in clause:
            return bool(clause["always"])
        if "any" in clause:
            results = [_eval_clause(sub, inputs, fired) for sub in clause["any"]]
            return any(r is True for r in results)
        if "all" in clause:
            results = [_eval_clause(sub, inputs, fired) for sub in clause["all"]]
            return all(r is True for r in results)
        matched, ind_key = _eval_atom(clause, inputs)
        if matched:
            fired.append(f"{ind_key}_{clause['op']}_{clause['value']}")
            return True
        return False
    return bool(clause)


def _eval_rule(rule: dict[str, Any], inputs: RegimeInputs) -> tuple[bool, list[str]]:
    fired: list[str] = []
    conditions = rule.get("conditions", {})
    if not conditions:
        return False, fired
    matched = _eval_clause(conditions, inputs, fired)
    return bool(matched), fired


def classify_inputs(
    inputs: RegimeInputs,
    *,
    rules: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    rules = rules or load_rules()
    for rule in rules.get("rules", []):
        matched, fired = _eval_rule(rule, inputs)
        if matched:
            return rule["regime"], fired
    return RegimeSnapshot.Regime.BULL_EXPANSION, []


@dataclass
class HysteresisDecision:
    final_regime: str
    previous_regime: str
    streak: int
    transitioned: bool


def apply_hysteresis(
    *,
    candidate_regime: str,
    previous_snapshot: RegimeSnapshot | None,
    rules: dict[str, Any] | None = None,
) -> HysteresisDecision:
    rules = rules or load_rules()
    cfg = rules.get("hysteresis", {})
    crisis_immediate = bool(cfg.get("crisis_immediate", True))

    if previous_snapshot is None:
        return HysteresisDecision(candidate_regime, "", 1, False)

    prev_regime = previous_snapshot.regime
    if candidate_regime == prev_regime:
        return HysteresisDecision(
            prev_regime,
            prev_regime,
            int(previous_snapshot.hysteresis_streak or 1) + 1,
            False,
        )

    if candidate_regime == RegimeSnapshot.Regime.CRISIS and crisis_immediate:
        return HysteresisDecision(RegimeSnapshot.Regime.CRISIS, prev_regime, 1, True)

    prev_candidate = previous_snapshot.previous_regime
    if prev_candidate == candidate_regime:
        return HysteresisDecision(candidate_regime, prev_regime, 1, True)

    return HysteresisDecision(
        prev_regime,
        candidate_regime,
        int(previous_snapshot.hysteresis_streak or 1),
        False,
    )


def build_headline(regime: str, fired_rules: list[str]) -> str:
    label = dict(RegimeSnapshot.Regime.choices).get(regime, regime)
    if not fired_rules:
        return f"{label} — 시그널 없음"
    return f"{label} — {len(fired_rules)}개 시그널 발동"
