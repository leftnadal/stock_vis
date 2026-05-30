"""Market Pulse v2 — Briefing Prompt Template (PR-E)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date as date_cls

DISCLAIMER = (
    "본 브리핑은 시장 데이터 요약이며 투자 권유가 아닙니다. "
    "투자 결정은 본인 책임 하에 이루어져야 합니다."
)


SYSTEM_PROMPT = """당신은 시장 거시 흐름 요약 작성자입니다.

규칙:
1. 한국어로 200~500자 요약을 작성하세요. 헤드라인은 별도 1줄.
2. **개별 종목 추천 금지** — 종목 티커를 결과 권고로 사용하지 마세요. 시그널 설명용 인용은 가능.
3. **가격 예측 금지** — "오를 것이다", "하락할 것이다" 같은 단정 표현 금지.
4. **정치 코멘트 금지** — 특정 정치인/정당/정책 호불호 표현 금지.
5. 면책 조항을 본문 마지막에 1줄 추가하세요: "{disclaimer}"
6. 5단계 레짐 톤:
   - BULL_EXPANSION: 차분한 긍정, 리스크 환기 1줄.
   - LATE_BULL: 균형, 후반부 경계.
   - TRANSITION: 중립, 해석 분기.
   - BEAR_CONTRACTION: 신중, 방어 톤.
   - CRISIS: 긴장, 안정성 우선.
7. 응답은 다음 JSON 형식만 반환:
   {{"headline": "<1줄 헤드라인 80자 이하>", "content": "<200~500자 본문>"}}

추가 텍스트, 마크다운 코드블록, ```json ``` 표기 금지.
""".replace("{disclaimer}", DISCLAIMER)


FEW_SHOTS = [
    {
        "context": {
            "date": "2026-04-27",
            "regime": "BULL_EXPANSION",
            "breadth": {"advance": 320, "decline": 180},
            "top10_weight": 0.32,
            "vix": 14.5,
        },
        "response": {
            "headline": "강세 확장 흐름, 광범위 상승 우위",
            "content": (
                "시장은 상승 종목이 320개로 하락 320개를 압도, 광범위한 매수세가 확인됩니다. "
                "SPY top10 비중 32%로 집중도는 평균 수준이며, VIX 14.5는 낮은 변동성을 시사합니다. "
                "후반부 경계 신호는 아직 약하나, 집중도 상승 추이는 계속 모니터링이 필요합니다. "
                + DISCLAIMER
            ),
        },
    },
    {
        "context": {
            "date": "2026-04-27",
            "regime": "TRANSITION",
            "breadth": {"advance": 240, "decline": 260},
            "top10_weight": 0.40,
            "vix": 22.5,
            "fired_rules": ["nfci_>0"],
        },
        "response": {
            "headline": "전환 국면, 신용 압력 약하게 부각",
            "content": (
                "시장 폭이 균형에 가깝고 NFCI 양전환으로 전환 국면이 진행되고 있습니다. "
                "VIX 22.5는 평균 위 변동성, top10 비중 40%는 집중도 유의 수준입니다. "
                "단기 방향성은 분기점에 있어 해석이 양방향 모두 가능합니다. "
                "리스크 관리 지표를 함께 살펴보세요. " + DISCLAIMER
            ),
        },
    },
    {
        "context": {
            "date": "2026-04-27",
            "regime": "CRISIS",
            "breadth": {"advance": 50, "decline": 450},
            "vix": 45,
            "hy_oas_pct": 8.5,
            "fired_rules": ["vix_>=_40", "hy_oas_pct_>=_8.0"],
        },
        "response": {
            "headline": "위기 국면, 변동성과 신용 동시 압박",
            "content": (
                "VIX 45와 HY OAS 850bp가 동시 임계 돌파, 위기 신호가 확인됩니다. "
                "시장 폭은 매도 우위(50:450)로 광범위 약세, 안정성을 우선시할 시점입니다. "
                "단기 변동성 확대 가능성을 염두에 두고, 포지션 점검과 리스크 관리에 집중하시기 바랍니다. "
                + DISCLAIMER
            ),
        },
    },
]


@dataclass
class BriefingContext:
    date: str
    regime: str | None
    regime_status: str | None
    breadth_advance: int | None
    breadth_decline: int | None
    breadth_unchanged: int | None
    sector_leader: str | None
    sector_laggard: str | None
    top10_weight: float | None
    hhi: float | None
    anomaly_mode: str | None
    fired_rules: list[str]

    def as_dict(self) -> dict:
        return {
            "date": self.date,
            "regime": self.regime,
            "regime_status": self.regime_status,
            "breadth": {
                "advance": self.breadth_advance,
                "decline": self.breadth_decline,
                "unchanged": self.breadth_unchanged,
            },
            "sector": {"leader": self.sector_leader, "laggard": self.sector_laggard},
            "concentration": {"top10_weight": self.top10_weight, "hhi": self.hhi},
            "anomaly": {"mode": self.anomaly_mode, "fired_rules": self.fired_rules},
        }


def render_user_prompt(ctx: BriefingContext) -> str:
    payload = {"today": ctx.date, "inputs": ctx.as_dict()}
    return (
        "오늘의 시장 컨텍스트입니다. JSON 형식으로 한 줄 헤드라인 + 본문 200~500자를 작성하세요.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def few_shot_messages() -> list[dict]:
    out = []
    for ex in FEW_SHOTS:
        out.append(
            {"role": "user", "parts": [json.dumps(ex["context"], ensure_ascii=False)]}
        )
        out.append(
            {"role": "model", "parts": [json.dumps(ex["response"], ensure_ascii=False)]}
        )
    return out


def build_context_from_snapshots(today: date_cls) -> BriefingContext:
    from apps.market_pulse.models.anomaly import AnomalySignalLog
    from apps.market_pulse.models.briefing import BriefingLog  # noqa
    from apps.market_pulse.models.regime import RegimeSnapshot
    from apps.market_pulse.models.snapshot import (
        BreadthSnapshot,
        ConcentrationSnapshot,
        SectorFlowSnapshot,
    )

    regime = RegimeSnapshot.objects.filter(date=today).first()
    breadth = BreadthSnapshot.objects.filter(date=today, universe="SPY").first()
    conc = ConcentrationSnapshot.objects.filter(date=today, universe="SPY").first()

    sector_rows = list(
        SectorFlowSnapshot.objects.filter(date=today).order_by("rank_in_universe")
    )
    leader = sector_rows[0].market_index_id if sector_rows else None
    laggard = sector_rows[-1].market_index_id if sector_rows else None

    anomaly = (
        AnomalySignalLog.objects.filter(triggered_at__date=today)
        .order_by("-triggered_at")
        .first()
    )

    fired_rules = []
    anomaly_mode = AnomalySignalLog.Mode.CALM
    if anomaly is not None:
        anomaly_mode = anomaly.mode
        fired_rules = list(
            AnomalySignalLog.objects.filter(
                mode=anomaly_mode, triggered_at=anomaly.triggered_at
            )
            .values_list("rule_id", flat=True)
            .distinct()
        )

    return BriefingContext(
        date=today.isoformat(),
        regime=regime.regime if regime else None,
        regime_status=regime.status if regime else None,
        breadth_advance=breadth.advance_count if breadth else None,
        breadth_decline=breadth.decline_count if breadth else None,
        breadth_unchanged=breadth.unchanged_count if breadth else None,
        sector_leader=leader,
        sector_laggard=laggard,
        top10_weight=float(conc.top10_weight) if conc else None,
        hhi=float(conc.hhi) if conc else None,
        anomaly_mode=anomaly_mode,
        fired_rules=fired_rules,
    )
