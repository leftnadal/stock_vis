"""RegimeSnapshot → iron_trading 계약의 market_pulse JSON 매핑."""

from __future__ import annotations

from datetime import date

# stock_vis 내부 RegimeSnapshot.regime → iron_trading 계약의 regime_hint
_REGIME_HINT_MAP = {
    "BULL_EXPANSION": "trend_following",
    "LATE_BULL": "risk_on_pullback",
    "TRANSITION": "risk_on_pullback",
    "BEAR_CONTRACTION": "risk_off",
    "CRISIS": "risk_off",
}

_DEFAULT_RISK_NOTES = {
    "BULL_EXPANSION": [
        "추세 강세지만 후행 과열 신호 모니터링 필요",
    ],
    "LATE_BULL": [
        "지수 변동성이 높아 신규 매수는 상위 상대강도 후보로 제한",
        "실적 발표 전후 종목은 포지션 사이징 축소",
    ],
    "TRANSITION": [
        "방향성 미확정 — 신규 진입은 짧은 손절가 기준으로 제한",
    ],
    "BEAR_CONTRACTION": [
        "지수 약세 — 신규 매수 비중 축소",
        "데드캣 바운스 가능성 인지",
    ],
    "CRISIS": [
        "변동성 위기 — 신규 매수 보류 권장",
    ],
}

_DEFAULT_OPPORTUNITY_NOTES = {
    "BULL_EXPANSION": [
        "추세 추종 후보 우선",
        "거래량 동반 돌파 종목 관찰",
    ],
    "LATE_BULL": [
        "하락장 안에서도 20일 상대강도 상위 후보는 추세 유지",
        "거래량 동반 돌파 후보를 우선 관찰",
    ],
    "TRANSITION": [
        "테마 리더 종목의 풀백 후 재진입 관찰",
    ],
    "BEAR_CONTRACTION": [
        "방어 섹터 상대강도 상위 후보 관찰",
    ],
    "CRISIS": [
        "위기 직후 회복 리더 종목 관찰 대기",
    ],
}


def build_market_pulse(snapshot, trading_date: date) -> dict:
    """RegimeSnapshot 또는 None 입력 → 계약의 market_pulse dict 반환.

    snapshot이 None이면 안전한 기본값 (regime_hint='unknown') 반환.
    """
    if snapshot is None:
        return {
            "regime_hint": "unknown",
            "summary": (
                f"{trading_date.isoformat()} 기준 시장 레짐 데이터가 아직 계산되지 않았습니다."
            ),
            "risk_notes": [
                "레짐 미확정 — 신규 결정보드 생성 시 보수적 사이징 권장",
            ],
            "opportunity_notes": [
                "후보 종목별 상대강도와 거래량 신호 위주로 평가",
            ],
        }

    regime_key = snapshot.regime
    regime_hint = _REGIME_HINT_MAP.get(regime_key, "unknown")
    summary = (
        snapshot.summary
        or snapshot.headline
        or (f"{trading_date.isoformat()} 시장 레짐: {snapshot.get_regime_display()}")
    )

    return {
        "regime_hint": regime_hint,
        "summary": summary,
        "risk_notes": list(_DEFAULT_RISK_NOTES.get(regime_key, [])),
        "opportunity_notes": list(_DEFAULT_OPPORTUNITY_NOTES.get(regime_key, [])),
    }
