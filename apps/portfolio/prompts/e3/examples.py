"""
E3 few-shot 예시 3개 — 서로 다른 프리셋과 지표 상태(strong / weak-with-outlier / moderate).

Version: 1.1 (2026-04-24)
"""

# ------------------------------------------------------------
# Example 1: Buffett Quality Value — ROIC strong (Core)
# ------------------------------------------------------------
EXAMPLE_1_INPUT = """{
  "preset_id": "buffett_quality_value",
  "preset_name": "Buffett Quality Value",
  "preset_category": "value",
  "metrics": [
    {
      "metric_id": "roic",
      "metric_display_name": "투하자본수익률(ROIC)",
      "tier": "core",
      "value": 0.18,
      "percentile": 0.92,
      "percentile_scope": "industry",
      "level_tag": "excellent",
      "threshold_applied": 0.12,
      "passed_threshold": true
    }
  ]
}"""

EXAMPLE_1_OUTPUT = """{
  "comments": [
    {
      "metric_id": "roic",
      "one_liner": "ROIC 평균이 18%로 업종 상위 8% 구간에 위치하며 프리셋 임계값(12%)을 모두 통과합니다. Buffett Quality Value의 Core 지표인 '지속적 자본 수익'을 견조히 충족하는 구성으로 읽힙니다."
    }
  ]
}"""


# ------------------------------------------------------------
# Example 2: GARP — PEG weak with single outlier (Core)
# ------------------------------------------------------------
EXAMPLE_2_INPUT = """{
  "preset_id": "garp",
  "preset_name": "GARP",
  "preset_category": "growth",
  "metrics": [
    {
      "metric_id": "peg_ratio",
      "metric_display_name": "PEG 비율",
      "tier": "core",
      "value": 2.8,
      "percentile": 0.15,
      "percentile_scope": "industry",
      "level_tag": "weak",
      "threshold_applied": 1.5,
      "passed_threshold": false
    }
  ]
}"""

EXAMPLE_2_OUTPUT = """{
  "comments": [
    {
      "metric_id": "peg_ratio",
      "one_liner": "포트폴리오 평균 PEG가 2.8로 프리셋 기준 1.5를 크게 상회합니다. 단, 1종목의 극단값이 평균을 끌어올린 측면이 있어 개별 종목별로는 해석의 여지가 남아있는 것으로 읽힐 수 있습니다."
    }
  ]
}"""


# ------------------------------------------------------------
# Example 3: Dividend Growth — payout_ratio moderate (Supporting)
# ------------------------------------------------------------
EXAMPLE_3_INPUT = """{
  "preset_id": "dividend_growth",
  "preset_name": "Dividend Growth",
  "preset_category": "income",
  "metrics": [
    {
      "metric_id": "payout_ratio",
      "metric_display_name": "배당성향",
      "tier": "supporting",
      "value": 0.55,
      "percentile": 0.48,
      "percentile_scope": "sector",
      "level_tag": "moderate",
      "threshold_applied": 0.70,
      "passed_threshold": true
    }
  ]
}"""

EXAMPLE_3_OUTPUT = """{
  "comments": [
    {
      "metric_id": "payout_ratio",
      "one_liner": "배당성향 평균이 55%로 Dividend Growth 프리셋의 주목 구간(40~70%) 내에 있습니다. 보조 지표이지만 60% 초과 종목이 일부 존재하여 경기 둔화 시 배당 축소 리스크가 부분적으로 잠재되어 있는 것으로 읽힐 수 있습니다."
    }
  ]
}"""


FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    (EXAMPLE_1_INPUT, EXAMPLE_1_OUTPUT),
    (EXAMPLE_2_INPUT, EXAMPLE_2_OUTPUT),
    (EXAMPLE_3_INPUT, EXAMPLE_3_OUTPUT),
]
