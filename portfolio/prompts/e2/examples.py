"""
E2 few-shot 예시 3개.

다양성 요건:
- severity: high / medium / low 각 1개
- structural_or_single: 최소 1개 single_outlier 포함
- 서로 다른 프리셋 사용 (GARP, Dividend Growth, Buffett Quality Value)

Version: 1.1 (2026-04-24)
"""

# ------------------------------------------------------------
# Example 1: GARP + Tech — high severity, structural
# ------------------------------------------------------------
EXAMPLE_1 = {
    "scenario": "GARP + Tech portfolio — broad valuation pressure (high / structural)",
    "input": """{
  "analysis_target_portfolio": {
    "portfolio_name": "Tech 성장주",
    "preset_id": "garp",
    "preset_name": "GARP",
    "preset_category": "growth",
    "holding_count": 5,
    "weaknesses_detail": [
      {
        "metric_id": "peg_ratio",
        "metric_display_name": "PEG 비율",
        "tier": "core",
        "avg_value": 2.8,
        "percentile_scope": "industry",
        "threshold_applied": 1.5,
        "passed_threshold_count": 0,
        "industry_median": 1.8,
        "per_holding": [
          {"symbol": "NVDA",  "value": 4.2, "level_tag": "critical"},
          {"symbol": "MSFT",  "value": 2.5, "level_tag": "weak"},
          {"symbol": "AAPL",  "value": 2.7, "level_tag": "weak"},
          {"symbol": "AMD",   "value": 2.4, "level_tag": "weak"},
          {"symbol": "GOOGL", "value": 2.1, "level_tag": "moderate"}
        ]
      }
    ]
  },
  "wallet_background": {"excluded_from_this_portfolio_count": 7}
}""",
    "output": """{
  "cards": [
    {
      "weakness_metric_id": "peg_ratio",
      "what_is_wrong": "5개 종목 모두 PEG가 2.0 이상이며, 포트폴리오 평균 PEG는 2.8입니다. 프리셋 통과 기준 (PEG < 1.5)을 만족하는 종목은 없습니다.",
      "comparison_basis": "비교 기준: GICS Software/Semiconductors 산업 중앙값 (PEG 1.8)과 프리셋 임계값 (PEG < 1.5).",
      "why_it_matters": "GARP 관점에서 성장 대비 높은 밸류에이션은 성장 둔화 시 급격한 가격 조정 리스크로 직결됩니다. 현재 수준은 '합리적 가격의 성장' 이라는 프리셋 핵심 가정을 벗어난 상태로 읽힐 수 있습니다.",
      "caveat_or_exception": "단, NVDA 한 종목의 PEG 4.2가 평균을 크게 끌어올린 측면이 있어 NVDA를 제외하면 평균은 2.4로 다소 완화됩니다.",
      "severity": "high",
      "structural_or_single": "structural"
    }
  ]
}""",
}


# ------------------------------------------------------------
# Example 2: Dividend Growth — medium severity, single outlier
# ------------------------------------------------------------
EXAMPLE_2 = {
    "scenario": "Dividend Growth — one holding cut dividend (medium / single_outlier)",
    "input": """{
  "analysis_target_portfolio": {
    "portfolio_name": "배당 코어",
    "preset_id": "dividend_growth",
    "preset_name": "Dividend Growth",
    "preset_category": "income",
    "holding_count": 7,
    "weaknesses_detail": [
      {
        "metric_id": "dividend_cagr_5y",
        "metric_display_name": "5년 배당 성장률",
        "tier": "core",
        "avg_value": 0.046,
        "percentile_scope": "sector",
        "threshold_applied": 0.05,
        "passed_threshold_count": 6,
        "sector_median": 0.054,
        "per_holding": [
          {"symbol": "JNJ", "value": 0.061, "level_tag": "good"},
          {"symbol": "PG",  "value": 0.058, "level_tag": "good"},
          {"symbol": "KO",  "value": 0.051, "level_tag": "good"},
          {"symbol": "MMM", "value": 0.072, "level_tag": "excellent"},
          {"symbol": "PEP", "value": 0.063, "level_tag": "good"},
          {"symbol": "ABBV","value": 0.081, "level_tag": "excellent"},
          {"symbol": "T",   "value": -0.18, "level_tag": "critical"}
        ]
      }
    ]
  },
  "wallet_background": {"excluded_from_this_portfolio_count": 8}
}""",
    "output": """{
  "cards": [
    {
      "weakness_metric_id": "dividend_cagr_5y",
      "what_is_wrong": "7개 종목 중 6개가 5년 배당 성장률 5% 이상을 유지하지만, 1개 종목(T)이 -18%의 배당 축소를 기록하며 포트폴리오 평균을 4.6%로 끌어내렸습니다.",
      "comparison_basis": "비교 기준: Consumer Staples / Healthcare 섹터 중앙값 (5.4%)과 프리셋 임계값 (5% 이상).",
      "why_it_matters": "Dividend Growth 관점에서 평균치보다 '지속성의 일관성' 자체가 중요합니다. 한 종목의 배당 삭감이 전체 소득 프로파일의 예측가능성을 훼손하는 것으로 해석될 수 있습니다.",
      "caveat_or_exception": "단, 다른 6개 종목의 배당 성장은 모두 양호하여 구조적 문제로 보기는 어렵고, T의 단일 이슈로 한정됩니다.",
      "severity": "medium",
      "structural_or_single": "single_outlier"
    }
  ]
}""",
}


# ------------------------------------------------------------
# Example 3: Buffett Quality Value — low severity, context tier
# ------------------------------------------------------------
EXAMPLE_3 = {
    "scenario": "Buffett Quality Value — mild insider ownership concern (low / structural)",
    "input": """{
  "analysis_target_portfolio": {
    "portfolio_name": "Quality 장기",
    "preset_id": "buffett_quality_value",
    "preset_name": "Buffett Quality Value",
    "preset_category": "value",
    "holding_count": 6,
    "weaknesses_detail": [
      {
        "metric_id": "insider_ownership",
        "metric_display_name": "내부자 지분율",
        "tier": "context",
        "avg_value": 0.018,
        "percentile_scope": "universe",
        "threshold_applied": null,
        "passed_threshold_count": null,
        "universe_median": 0.024,
        "per_holding": [
          {"symbol": "BRK.B", "value": 0.015, "level_tag": "moderate"},
          {"symbol": "JNJ",   "value": 0.012, "level_tag": "moderate"},
          {"symbol": "PG",    "value": 0.016, "level_tag": "moderate"},
          {"symbol": "KO",    "value": 0.019, "level_tag": "moderate"},
          {"symbol": "MCD",   "value": 0.021, "level_tag": "moderate"},
          {"symbol": "WMT",   "value": 0.025, "level_tag": "good"}
        ]
      }
    ]
  },
  "wallet_background": {"excluded_from_this_portfolio_count": 3}
}""",
    "output": """{
  "cards": [
    {
      "weakness_metric_id": "insider_ownership",
      "what_is_wrong": "6개 종목의 내부자 지분율 평균이 1.8%로, 유니버스 중앙값 2.4% 대비 다소 낮습니다.",
      "comparison_basis": "비교 기준: 전체 S&P 500 유니버스 중앙값 (2.4%). 프리셋에 임계값은 없으며 Context tier 지표입니다.",
      "why_it_matters": "Buffett Quality Value 관점에서 내부자 지분은 경영진의 장기 이해관계 일치 여부를 보는 보조 지표로, 낮을수록 주주 친화성에 대한 작은 의문으로 읽힐 수 있습니다.",
      "caveat_or_exception": "단, Context tier 지표이므로 Core 지표가 양호하다면 진단에서 차지하는 비중은 제한적입니다.",
      "severity": "low",
      "structural_or_single": "structural"
    }
  ]
}""",
}


FEW_SHOT_EXAMPLES: list[dict] = [EXAMPLE_1, EXAMPLE_2, EXAMPLE_3]
