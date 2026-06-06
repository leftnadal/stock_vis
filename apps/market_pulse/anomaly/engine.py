"""
Anomaly Engine (PR-D) — 4 Core 룰 평가 + 컨텍스트 빌더.

소속: apps/market_pulse/anomaly (app 레이어 — 이상 신호 감지).
역할:
  - build_context: ConcentrationSnapshot + macro VIXCLS + SectorFlowSnapshot로
    AnomalyContext(top10_weight·vix_change_pct·max_abs_sector_z·cross_dispersion 등) 조립.
  - load_rules: rules.yaml mtime 캐시 로더.
  - evaluate: 룰별 임계 평가 → FiredRule 리스트.
  - select_mode: 발동 룰 수 기준 (ANOMALY ≥2 / HYBRID =1 / CALM =0).
주요 심볼: AnomalyContext, FiredRule, build_context, load_rules, evaluate, select_mode.
의존: macro.models(EconomicIndicator·IndicatorValue), models.snapshot.
소비처: tasks/anomaly.py의 mp_detect_anomaly_5min.
"""

from __future__ import annotations

import logging
import operator
import os
import statistics
from dataclasses import dataclass, field
from datetime import date as date_cls
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from django.utils import timezone as django_timezone

from apps.market_pulse.models.anomaly import AnomalySignalLog
from apps.market_pulse.models.snapshot import (
    ConcentrationSnapshot,
    SectorFlowSnapshot,
)
from macro.models.indicators import EconomicIndicator, IndicatorValue

logger = logging.getLogger(__name__)

RULES_PATH = Path(__file__).parent / "rules.yaml"

OPERATORS = {
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


@dataclass
class AnomalyContext:
    top10_weight: float | None = None
    vix_change_pct: float | None = None
    max_abs_sector_z: float | None = None
    cross_dispersion: float | None = None
    sector_extreme_symbol: str | None = None
    sector_extreme_z: float | None = None
    fetched_at: str = ""
    sources: dict[str, str] = field(default_factory=dict)


def _vix_change_pct() -> float | None:
    ind = EconomicIndicator.objects.filter(code="VIXCLS").first()
    if ind is None:
        return None
    today = django_timezone.localdate()
    rows = list(
        IndicatorValue.objects.filter(
            indicator=ind, date__gte=today - timedelta(days=14)
        )
        .order_by("-date")
        .values_list("date", "value")[:2]
    )
    if len(rows) < 2:
        return None
    today_v, prev_v = rows[0][1], rows[1][1]
    if prev_v == 0:
        return None
    return float((today_v - prev_v) / prev_v * Decimal("100"))


def _max_abs_sector_z(
    target_date: date_cls | None = None,
) -> tuple[float | None, str | None, float | None]:
    target_date = target_date or django_timezone.localdate()
    rows = list(
        SectorFlowSnapshot.objects.filter(date=target_date).values_list(
            "market_index_id", "rel_strength"
        )
    )
    if len(rows) < 3:
        return None, None, None
    rels = [float(r[1]) for r in rows]
    mu = statistics.fmean(rels)
    sigma = statistics.pstdev(rels) or 1e-9
    best_sym, best_z = None, 0.0
    for sym, rel in rows:
        z = (float(rel) - mu) / sigma
        if abs(z) > abs(best_z):
            best_z = z
            best_sym = sym
    return abs(best_z), best_sym, best_z


def build_context(target_date: date_cls | None = None) -> AnomalyContext:
    target_date = target_date or django_timezone.localdate()
    ctx = AnomalyContext()
    sources: dict[str, str] = {}

    conc = (
        ConcentrationSnapshot.objects.filter(date__lte=target_date)
        .order_by("-date")
        .first()
    )
    if conc is not None:
        ctx.top10_weight = float(conc.top10_weight)
        sources["top10_weight"] = "OK"
    else:
        sources["top10_weight"] = "MISSING"

    v = _vix_change_pct()
    ctx.vix_change_pct = v
    sources["vix_change_pct"] = "OK" if v is not None else "MISSING"

    sf = (
        SectorFlowSnapshot.objects.filter(date__lte=target_date)
        .order_by("-date")
        .first()
    )
    if sf is not None:
        ctx.cross_dispersion = float(sf.cross_dispersion)
        sources["cross_dispersion"] = "OK"
        max_abs_z, sym, signed_z = _max_abs_sector_z(sf.date)
        if max_abs_z is not None:
            ctx.max_abs_sector_z = max_abs_z
            ctx.sector_extreme_symbol = sym
            ctx.sector_extreme_z = signed_z
            sources["max_abs_sector_z"] = "OK"
        else:
            sources["max_abs_sector_z"] = "MISSING"
    else:
        sources["cross_dispersion"] = "MISSING"
        sources["max_abs_sector_z"] = "MISSING"

    ctx.sources = sources
    ctx.fetched_at = django_timezone.now().isoformat()
    return ctx


@dataclass
class FiredRule:
    rule_id: str
    name: str
    threshold: dict[str, float]
    actual: float


def evaluate(
    ctx: AnomalyContext, *, rules: dict[str, Any] | None = None
) -> list[FiredRule]:
    rules = rules or load_rules()
    fired: list[FiredRule] = []
    for rule in rules.get("rules", []):
        op_str = rule.get("op", ">=")
        against = rule.get("against")
        threshold_map = rule.get("threshold", {})
        if not against or against not in threshold_map:
            continue
        threshold_val = threshold_map[against]
        actual = getattr(ctx, against, None)
        if actual is None:
            continue
        if OPERATORS[op_str](actual, threshold_val):
            fired.append(
                FiredRule(
                    rule_id=rule["id"],
                    name=rule["name"],
                    threshold=dict(threshold_map),
                    actual=float(actual),
                )
            )
    return fired


def select_mode(fired: list[FiredRule]) -> str:
    n = len(fired)
    if n >= 2:
        return AnomalySignalLog.Mode.ANOMALY
    if n == 1:
        return AnomalySignalLog.Mode.HYBRID
    return AnomalySignalLog.Mode.CALM
