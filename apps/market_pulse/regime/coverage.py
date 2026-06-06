"""
Coverage Gate (PR-C) — intraday regime 입력 충분도 게이트.

소속: apps/market_pulse/regime (app 레이어).
역할: RegimeInputs 14 키 중 채워진 비율을 계산해 분류 결과 신뢰도 판정.
  ratio < min_ratio(0.6) → RegimeSnapshot.Status.INSUFFICIENT_DATA로 표기,
  히스테리시스만 유지하고 신규 전환은 보류.
주요 심볼:
  - evaluate(...): inputs + rules → CoverageResult(ratio, status, missing).
의존: classifier.load_rules(min_ratio 룰 추출), inputs.RegimeInputs.
소비처: tasks/regime.py의 mp_calc_regime_15min 본 분기.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.market_pulse.models.regime import RegimeSnapshot
from apps.market_pulse.regime.classifier import load_rules
from apps.market_pulse.regime.inputs import RegimeInputs


@dataclass(frozen=True)
class CoverageEvaluation:
    ratio: float
    status: str
    missing: list[str]
    threshold: float


def evaluate(inputs: RegimeInputs, *, rules: dict | None = None) -> CoverageEvaluation:
    rules = rules or load_rules()
    threshold = float(rules.get("coverage", {}).get("min_ratio", 0.6))
    ratio = inputs.coverage_ratio()
    status = (
        RegimeSnapshot.Status.INSUFFICIENT_DATA
        if ratio < threshold
        else RegimeSnapshot.Status.OK
    )
    return CoverageEvaluation(
        ratio=ratio, status=status, missing=inputs.missing_keys(), threshold=threshold
    )
