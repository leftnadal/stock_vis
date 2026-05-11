"""
E1 few-shot 예시 (2개).

각 예시는 (입력 JSON 문자열, 기대 출력 JSON 문자열) 쌍.
다른 프리셋 카테고리 + 다른 트레이드오프 패턴으로 구성.

Version: 1.1 (2026-04-24)
"""

# ------------------------------------------------------------
# Example 1: GARP(growth) — 성장은 강하나 밸류에이션 부담
# ------------------------------------------------------------
EXAMPLE_1_INPUT = """{
  "analysis_target_portfolio": {
    "portfolio_name": "Tech 성장주",
    "preset_id": "garp",
    "preset_name": "GARP",
    "preset_category": "growth",
    "holding_count": 5,
    "strengths": [
      {"metric_id": "roic", "metric_display_name": "투하자본수익률",
       "level_tag": "excellent", "reason_hint": "5개 중 3개가 산업 상위 25%"},
      {"metric_id": "eps_growth_yoy", "metric_display_name": "EPS 성장률(YoY)",
       "level_tag": "good", "reason_hint": "평균 22%, 중앙값 18%"}
    ],
    "weaknesses": [
      {"metric_id": "peg_ratio", "metric_display_name": "PEG",
       "level_tag": "weak", "reason_hint": "3종목 PEG 2.5 이상"},
      {"metric_id": "pe_ratio", "metric_display_name": "PER",
       "level_tag": "moderate", "reason_hint": "산업 중앙값 대비 1.3배"}
    ],
    "portfolio_return_total": 0.14
  },
  "wallet_background": {
    "total_holdings_count": 12,
    "excluded_from_this_portfolio_count": 7
  }
}"""

EXAMPLE_1_OUTPUT = """{
  "headline": "성장성 견조하나 밸류에이션 부담",
  "summary": "GARP 관점에서 당신의 Tech 성장주 포트폴리오는 투하자본수익률과 EPS 성장률이 산업 상위권에 있습니다. 다만 5개 종목 중 3개의 PEG가 2.5 이상으로 성장 대비 가격 부담이 뚜렷하여, 성장 둔화 시 조정 리스크가 커질 수 있습니다."
}"""


# ------------------------------------------------------------
# Example 2: Dividend Growth(income) — 배당은 안정적이나 성장 모멘텀 제한
# ------------------------------------------------------------
EXAMPLE_2_INPUT = """{
  "analysis_target_portfolio": {
    "portfolio_name": "배당 코어",
    "preset_id": "dividend_growth",
    "preset_name": "Dividend Growth",
    "preset_category": "income",
    "holding_count": 7,
    "strengths": [
      {"metric_id": "dividend_yield", "metric_display_name": "배당수익률",
       "level_tag": "good", "reason_hint": "평균 3.4%, 산업 중앙값 2.1%"},
      {"metric_id": "dividend_cagr_5y", "metric_display_name": "5년 배당 성장률",
       "level_tag": "excellent", "reason_hint": "평균 8.6%"}
    ],
    "weaknesses": [
      {"metric_id": "revenue_growth_yoy", "metric_display_name": "매출 성장률(YoY)",
       "level_tag": "weak", "reason_hint": "4종목이 5% 미만"},
      {"metric_id": "earnings_momentum", "metric_display_name": "어닝 모멘텀",
       "level_tag": "moderate", "reason_hint": "상향 개정 비율 낮음"}
    ],
    "portfolio_return_total": 0.07
  },
  "wallet_background": {
    "total_holdings_count": 15,
    "excluded_from_this_portfolio_count": 8
  }
}"""

EXAMPLE_2_OUTPUT = """{
  "headline": "배당 안정적, 성장 모멘텀 제한적",
  "summary": "Dividend Growth 관점에서 배당수익률과 5년 배당 성장률이 산업 상위권에 위치합니다. 다만 7개 종목 중 4개의 매출 성장률이 5%에 미치지 못해, 장기 배당 지속성의 핵심 동력인 매출 성장이 취약하다고 읽힐 수 있습니다."
}"""


FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    (EXAMPLE_1_INPUT, EXAMPLE_1_OUTPUT),
    (EXAMPLE_2_INPUT, EXAMPLE_2_OUTPUT),
]
