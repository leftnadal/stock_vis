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
    # MP-UX-S1: 카드 내부 지표 라벨 (전수조사 전문어 raw 노출 해소, director 확정값)
    "metric.top5": "상위5 비중",
    "metric.top10": "상위10 비중",
    "metric.hhi": "허핀달 지수",
    "metric.dispersion": "섹터 분산도",
    "metric.rotation": "로테이션 지수",
    "metric.ad_line": "등락주선",
    "metric.coverage": "지표 적용범위",
    "metric.streak": "국면 유지일",
    # MP-UX-S1: 유니버스 코드값 → 풀네임
    "universe.SP500_MCAP": "S&P500 시총가중",
    # MP-UX-S1: 매크로지표 라벨 (director 확정 5종)
    "indicator.vix": "VIX (변동성)",
    "indicator.move": "MOVE (채권 변동성)",
    "indicator.nfci": "NFCI (금융여건)",
    "indicator.hy_oas": "HY 스프레드",
    "indicator.t10y2y": "장단기 금리차(10Y-2Y)",
    # MP-UX-S2: 매크로지표 나머지 9종 한글 흡수 (director 확정 — 레이더축 raw 0)
    "indicator.return_1d_pct": "1일 수익률",
    "indicator.vol_20d_pct": "20일 변동성",
    "indicator.drawdown_pct": "52주 고점대비 낙폭",
    "indicator.nfci_credit": "NFCI 신용",
    "indicator.nfci_leverage": "NFCI 레버리지",
    "indicator.nfci_risk": "NFCI 리스크",
    "indicator.hy_ccc_oas_pct": "HY CCC 스프레드",
    "indicator.t10y3m_pct": "장단기 금리차(10Y-3M)",
    "indicator.vix3m": "VIX 3개월",
    # MP-UX-S5-B-SECTOR-LABEL: SPDR 섹터 ETF → GICS KO명 (출처: frontend screener.ts,
    #   발명 0). 섹터 스파크라인 FE(slice 2b) prerequisite — translate('sector.{SYM}') 단일소스.
    "sector.XLK": "기술",
    "sector.XLC": "통신",
    "sector.XLY": "경기소비재",
    "sector.XLP": "필수소비재",
    "sector.XLE": "에너지",
    "sector.XLF": "금융",
    "sector.XLV": "헬스케어",
    "sector.XLI": "산업재",
    "sector.XLB": "소재",
    "sector.XLRE": "부동산",
    "sector.XLU": "유틸리티",
}


LANG_LABELS: dict[str, dict[str, str]] = {"ko": KO_LABELS}


def get_labels(locale: str = "ko") -> dict[str, str]:
    return LANG_LABELS.get(locale.lower(), {})


def supported_locales() -> list[str]:
    return sorted(LANG_LABELS.keys())
