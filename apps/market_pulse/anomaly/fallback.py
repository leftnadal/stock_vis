"""Market Pulse v2 — Anomaly Fallback (PR-D)."""

from __future__ import annotations

from dataclasses import dataclass

from marketpulse.anomaly.engine import AnomalyContext, FiredRule
from marketpulse.models.anomaly import AnomalySignalLog


@dataclass(frozen=True)
class FallbackPayload:
    overview: str
    sector_highlight: str
    portfolio_action: str


RULE_LABELS = {
    "R02": "집중도 극단",
    "R04": "VIX 급등",
    "R09": "섹터 z-score 극단",
    "R12": "섹터 분산 급등",
}


def _format_actual(rule_id: str, actual: float) -> str:
    if rule_id == "R02":
        return f"{actual * 100:.1f}%"
    if rule_id == "R04":
        return f"{actual:+.1f}%"
    if rule_id == "R09":
        return f"|z|={actual:.2f}"
    if rule_id == "R12":
        return f"σ={actual:.3f}"
    return f"{actual:.3f}"


def build(*, fired: list[FiredRule], ctx: AnomalyContext, mode: str) -> FallbackPayload:
    if mode == AnomalySignalLog.Mode.ANOMALY:
        rule_summary = ", ".join(
            f"{RULE_LABELS.get(f.rule_id, f.rule_id)}({_format_actual(f.rule_id, f.actual)})"
            for f in fired
        )
        overview = f"다중 이상 시그널 감지 — {rule_summary}"
    elif mode == AnomalySignalLog.Mode.HYBRID:
        f = fired[0]
        overview = (
            f"단일 이상 시그널: {RULE_LABELS.get(f.rule_id, f.rule_id)} "
            f"({_format_actual(f.rule_id, f.actual)})"
        )
    else:
        overview = "시장 정상 범위 — 4 Core 룰 미발동."

    if ctx.sector_extreme_symbol and ctx.sector_extreme_z is not None:
        direction = "강세" if ctx.sector_extreme_z > 0 else "약세"
        sector_highlight = (
            f"{ctx.sector_extreme_symbol} {direction} (z={ctx.sector_extreme_z:+.2f})"
        )
    elif ctx.cross_dispersion is not None:
        sector_highlight = f"섹터 cross-dispersion = {ctx.cross_dispersion:.3f}"
    else:
        sector_highlight = "섹터 데이터 미수집"

    if mode == AnomalySignalLog.Mode.ANOMALY:
        portfolio_action = "리스크 관리 강화 / 단기 포지션 점검 권장."
    elif mode == AnomalySignalLog.Mode.HYBRID:
        portfolio_action = "주요 보유 종목 변동성 모니터링."
    else:
        portfolio_action = "기존 포트폴리오 유지."

    return FallbackPayload(overview, sector_highlight, portfolio_action)
