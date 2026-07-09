"""지표 카탈로그 (MON-P3-S2).

scope별로 빌더가 제시할 수 있는 지표 종류의 단일 소스.
각 항목의 `source`는 IndicatorReading을 채울 데이터 출처(향후 이식 태스크 MON-P2-INGEST가 소비).
현재 stock scope만 활성(시장/섹터/테마/펀드는 P4~P6에서 카탈로그 확장).

규칙 입력 스키마(빌더 3단계): 사용자는 카탈로그에서 지표를 고르고
  - support_direction: 값↑이 지지(positive) / 값↓이 지지(negative) — 카탈로그 default 제공, 사용자 변경 가능
  - weight: 가중치(기본 1.0)
만 정한다. name·indicator_type·source_key는 카탈로그가 확정한다(재입력 없음).
"""

# stock scope 최소 카탈로그 — EODSignal(stock·date 일간 시계열) 파생 3종.
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
