"""
i18n 영문 키 → 한글 라벨 매핑 (PR-J).

소속: apps/market_pulse/i18n (app 레이어 화면 상수).
역할: 카드/레짐/지표 영문 키를 한글 표시 라벨로 단방향 매핑.
주요 심볼:
  - KO_LABELS: 영문 키 → 한글 dict (regime/카드 명칭 + 단위 등)
소비처: serializers·api/views/* 응답에서 한글 라벨 부착.
"""

from __future__ import annotations

KO_LABELS: dict[str, str] = {
    "card.regime": "시장 레짐",
    "card.breadth": "시장 폭",
    "card.sector": "섹터 흐름",
    "card.concentration": "집중도",
    "card.brief": "브리핑",
    "regime.BULL_EXPANSION": "강세 확장",
    "regime.LATE_BULL": "상승 후반 경계",
    "regime.TRANSITION": "전환",
    "regime.BEAR_CONTRACTION": "약세 수축",
    "regime.CRISIS": "위기",
    "status.OK": "정상",
    "status.INSUFFICIENT_DATA": "데이터 수집 부족",
    "status.STALE": "데이터 오래됨",
    "status.FAILED": "계산 실패",
    "status.MARKET_CLOSED": "장 마감",
    "mode.ANOMALY": "이상 신호",
    "mode.HYBRID": "주의 모드",
    "mode.CALM": "정상",
    "rule.R02": "집중도 극단",
    "rule.R04": "VIX 급등",
    "rule.R09": "섹터 z-score 극단",
    "rule.R12": "섹터 분산 급등",
    "news.MACRO": "거시",
    "news.GEOPOLITICS": "지정학",
    "news.SECTOR": "섹터",
    "news.INDEX": "지수",
    "news.MAG7": "매그니피센트 7",
    "news.SMART_MONEY": "스마트머니",
}


LANG_LABELS: dict[str, dict[str, str]] = {"ko": KO_LABELS}


def get_labels(locale: str = "ko") -> dict[str, str]:
    return LANG_LABELS.get(locale.lower(), {})


def supported_locales() -> list[str]:
    return sorted(LANG_LABELS.keys())
