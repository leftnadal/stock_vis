"""Playbook evaluator (1.6-S1) — anomaly evaluate() 패턴 준용, 완전 분리.

anomaly = 단일 지표 boolean 발화. playbook = 다신호 합류의 **부분 점등**(lit_count/total) + 상태.
판단은 여기(BE)서 완성 — FE 재판정 0. chains.yaml 선언 → PlaybookContext 신호로 조건 평가.

⚠ playbook·anomaly evaluator 간 실제 drift 버그 발생 시 공용 evaluator 수렴 검토
  (TASKQUEUE EVALUATOR-CONVERGE). 그 전까지는 행위보존 위해 분리 유지.
"""

from __future__ import annotations

import operator
from datetime import date as date_cls
from pathlib import Path
from typing import Any

import yaml
from django.utils import timezone as django_timezone

from apps.market_pulse.playbook.context import PlaybookContext, build_context

CHAINS_PATH = Path(__file__).parent / "chains.yaml"

OPERATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
}

# 상태 어휘 — dormant(무점등)/partial(부분)/active(전점등)/pending(데이터 대기).
STATE_DORMANT = "dormant"
STATE_PARTIAL = "partial"
STATE_ACTIVE = "active"
STATE_PENDING = "pending"

_cache: dict[str, Any] = {"mtime": None, "data": None}


def load_chains(path: Path | None = None, *, force: bool = False) -> dict[str, Any]:
    """chains.yaml mtime 캐시 로더(anomaly load_rules 준용)."""
    p = path or CHAINS_PATH
    mtime = p.stat().st_mtime
    if force or _cache["mtime"] != mtime or _cache["data"] is None:
        with p.open("r", encoding="utf-8") as f:
            _cache["data"] = yaml.safe_load(f)
        _cache["mtime"] = mtime
    return _cache["data"]


def _eval_condition(ctx: PlaybookContext, cond: dict[str, Any]) -> bool | None:
    """조건 판정. 신호 부재(None) = None(대기). 아니면 op 비교 결과 bool."""
    signal = cond.get("signal")
    op_str = cond.get("op", ">=")
    threshold = cond.get("threshold")
    actual = ctx.get(signal)
    if actual is None or op_str not in OPERATORS or threshold is None:
        return None
    return bool(OPERATORS[op_str](actual, threshold))


def _chain_data_as_of(ctx: PlaybookContext, conditions: list[dict]) -> str | None:
    """체인 신호들 중 가장 오래된 기준일(지배 신선도 — weekly 정직 표기)."""
    dates = [ctx.data_as_of.get(c.get("signal")) for c in conditions]
    dates = [d for d in dates if d]
    return min(dates) if dates else None


def evaluate_chain(ctx: PlaybookContext, chain: dict[str, Any]) -> dict[str, Any]:
    conditions = chain.get("conditions", [])
    results = [(c.get("label", c.get("signal")), _eval_condition(ctx, c)) for c in conditions]
    total = len(results)
    lit_count = sum(1 for _, r in results if r is True)
    missing = sum(1 for _, r in results if r is None)

    if total == 0:
        state = STATE_DORMANT
    elif missing == total:
        state = STATE_PENDING
    elif lit_count == total:
        state = STATE_ACTIVE
    elif lit_count >= 1:
        state = STATE_PARTIAL
    else:
        state = STATE_DORMANT

    return {
        "id": chain.get("id"),
        "name": chain.get("name"),
        "narrative": chain.get("narrative"),
        "cadence": chain.get("cadence", "daily"),
        "lit_count": lit_count,
        "total": total,
        "state": state,
        "data_as_of": _chain_data_as_of(ctx, conditions),
        "conditions": [{"label": lbl, "lit": r} for lbl, r in results],
    }


def evaluate(
    ctx: PlaybookContext | None = None,
    *,
    chains: dict[str, Any] | None = None,
    target_date: date_cls | None = None,
) -> list[dict[str, Any]]:
    ctx = ctx or build_context(target_date)
    chains = chains or load_chains()
    return [evaluate_chain(ctx, ch) for ch in chains.get("chains", [])]


def build_payload(target_date: date_cls | None = None) -> dict[str, Any]:
    """compute-on-read 체인 카드 payload (판단 단일소스 — FE는 표시만)."""
    ctx = build_context(target_date)
    rows = evaluate(ctx)
    active = [r for r in rows if r["state"] == STATE_ACTIVE]
    # top_chain = 점등 비율 최고(active 우선, 없으면 partial 최고 lit_count)
    ranked = sorted(
        rows,
        key=lambda r: (r["lit_count"] / r["total"] if r["total"] else 0, r["lit_count"]),
        reverse=True,
    )
    top = next((r for r in ranked if r["lit_count"] > 0), None)
    return {
        "chains": rows,
        "summary": {
            "total": len(rows),
            "total_lit": len(active),
            "top_chain": {"id": top["id"], "name": top["name"]} if top else None,
            "evaluated_at": django_timezone.now().isoformat(),
        },
    }
