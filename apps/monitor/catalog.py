"""지표 카탈로그 (MON-P3-S2).

scope별로 빌더가 제시할 수 있는 지표 종류의 단일 소스.
각 항목의 `source`는 IndicatorReading을 채울 데이터 출처(향후 이식 태스크 MON-P2-INGEST가 소비).
현재 stock scope만 활성(시장/섹터/테마/펀드는 P4~P6에서 카탈로그 확장).

규칙 입력 스키마(빌더 3단계): 사용자는 카탈로그에서 지표를 고르고
  - support_direction: 값↑이 지지(positive) / 값↓이 지지(negative) — 카탈로그 default 제공, 사용자 변경 가능
  - weight: 가중치(기본 1.0)
만 정한다. name·indicator_type·source_key는 카탈로그가 확정한다(재입력 없음).
"""

# stock scope 카탈로그.
#   기존 3종(EODSignal 파생) — 파이프라인 불변, 그대로 공존.
#   S계열 6종(D-TIMING-DECISIONS-5 ①-A) — DailyPrice(3년 OHLC) → TechnicalIndicators 산출.
#
# S계열 dict 신규 메타 키(빌더·스코어러 소비):
#   - evidence_strength: "strong"/"medium"/"weak" (UI 근거강도 표시)
#   - scoring_mode: "zscore"(기본, indicator_scorer robust-Z) / "bounded"([0,1]→[-1,1] 선형)
#   - default_selected: 빌더 3단계 기본 선택 여부(약근거 2종 False)
#   - compute_key: 신규 ingest 경로(ingest_technical)가 소비하는 계산 종류 키
STOCK_INDICATOR_CATALOG = [
    {
        "key": "eod_composite",
        "name": "EOD 종합 신호",
        "indicator_type": "market_data",
        "default_direction": "positive",
        "source": "stocks.EODSignal.composite_score",
        "unit": "점수(-1~1)",
        "description": "장 마감 후 14개 시그널 합성 점수. 높을수록 강세.",
    },
    {
        "key": "change_percent",
        "name": "일간 등락률",
        "indicator_type": "market_data",
        "default_direction": "positive",
        "source": "stocks.EODSignal.change_percent",
        "unit": "%",
        "description": "전일 대비 종가 변동률.",
    },
    {
        "key": "dollar_volume",
        "name": "거래대금",
        "indicator_type": "market_data",
        "default_direction": "positive",
        "source": "stocks.EODSignal.dollar_volume",
        "unit": "USD",
        "description": "당일 달러 거래대금(수급 강도 프록시).",
    },
    # ── S계열 (타이밍 프리셋, DailyPrice 산출) ──────────────────────────────
    {
        "key": "sma200_gap",
        "name": "200일선 괴리율",
        "indicator_type": "technical",
        "default_direction": "positive",
        "source": "stocks.DailyPrice → TechnicalIndicators.calculate_sma(200)",
        "unit": "%",
        "description": "종가가 200일 이동평균 대비 얼마나 위/아래인지(추세 방향·강도). BLL 1992·Faber 2007.",
        "evidence_strength": "strong",
        "scoring_mode": "zscore",
        "default_selected": True,
        "compute_key": "sma200_gap",
    },
    {
        "key": "momentum_12_1",
        "name": "12-1 모멘텀",
        "indicator_type": "technical",
        "default_direction": "positive",
        "source": "stocks.DailyPrice(252/21행)",
        "unit": "%",
        "description": "최근 1개월 제외 12개월 수익률(시계열 모멘텀). Moskowitz 2012.",
        "evidence_strength": "strong",
        "scoring_mode": "zscore",
        "default_selected": True,
        "compute_key": "momentum_12_1",
    },
    {
        "key": "high_52w_proximity",
        "name": "52주 고가 근접도",
        "indicator_type": "technical",
        "default_direction": "positive",
        "source": "stocks.DailyPrice(252행 high)",
        "unit": "비율(0~1)",
        "description": "종가가 52주 최고가에 얼마나 가까운지(0=최저·1=신고가). George&Hwang 2004.",
        "evidence_strength": "medium",
        "scoring_mode": "bounded",
        "default_selected": True,
        "compute_key": "high_52w_proximity",
    },
    {
        "key": "volume_ratio",
        "name": "거래량 비율",
        "indicator_type": "technical",
        "default_direction": "positive",
        "source": "stocks.DailyPrice(20행 volume)",
        "unit": "배수",
        "description": "당일 거래량 / 20일 평균 거래량(수급 확인용). Lo 2000.",
        "evidence_strength": "medium",
        "scoring_mode": "zscore",
        "default_selected": True,
        "compute_key": "volume_ratio",
    },
    {
        "key": "macd_histogram",
        "name": "MACD 히스토그램",
        "indicator_type": "technical",
        "default_direction": "positive",
        "source": "stocks.DailyPrice → TechnicalIndicators.calculate_macd",
        "unit": "값",
        "description": "MACD선과 시그널선 차이(모멘텀 전환). 근거 약 — 참고용.",
        "evidence_strength": "weak",
        "scoring_mode": "zscore",
        "default_selected": False,
        "compute_key": "macd_histogram",
    },
    {
        "key": "rsi14",
        "name": "RSI 오실레이터",
        "indicator_type": "technical",
        "default_direction": "positive",
        "source": "stocks.DailyPrice → TechnicalIndicators.calculate_rsi(14)",
        "unit": "0~100",
        "description": "14일 상대강도지수(과매도·과매수). 근거 약 — 참고용.",
        "evidence_strength": "weak",
        "scoring_mode": "bounded",
        "default_selected": False,
        "compute_key": "rsi14",
    },
]

CATALOG_BY_SCOPE = {
    "stock": STOCK_INDICATOR_CATALOG,
    # 'market'·'sector'·'theme'·'fund' → P4~P6에서 추가
}


def catalog_for(scope: str) -> list[dict]:
    """scope의 지표 카탈로그. 미지원 scope는 빈 목록."""
    return CATALOG_BY_SCOPE.get(scope, [])


def catalog_entry(scope: str, key: str) -> dict | None:
    for entry in catalog_for(scope):
        if entry["key"] == key:
            return entry
    return None
