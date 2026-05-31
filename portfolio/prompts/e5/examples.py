"""
E5 few-shot 예시 5개 — 4개 intent_type 각 1개 + clarification 1개.

Version: 1.1 (2026-04-24)
"""

# ------------------------------------------------------------
# Example 1: threshold_change
# ------------------------------------------------------------
EXAMPLE_1 = {
    "scenario": "ROIC 임계값 상향 요청",
    "user_hint": "ROIC 임계값을 20%로 상향",
    "current_preset_hint": {
        "preset_id": "buffett_quality_value",
        "available_metric_ids_sample": ["roic", "roe", "peg_ratio"],
    },
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "threshold_change",
                "description_for_user": "ROIC 임계값을 15%에서 20%로 상향",
                "overrides": {
                    "metric_id": "roic",
                    "old_threshold": 0.15,
                    "new_threshold": 0.20,
                },
                "confidence": 0.95,
            }
        ],
        "needs_clarification": False,
        "clarification_question": "",
    },
}


# ------------------------------------------------------------
# Example 2: tier_change (복수 조정 한 메시지)
# ------------------------------------------------------------
EXAMPLE_2 = {
    "scenario": "성장 지표 두 개를 Context에서 Supporting으로 승격",
    "user_hint": "revenue_growth_yoy 와 eps_growth_yoy 를 Context 에서 Supporting 으로 올려줘",
    "current_preset_hint": {
        "preset_id": "buffett_quality_value",
        "available_metric_ids_sample": [
            "revenue_growth_yoy",
            "eps_growth_yoy",
            "roic",
        ],
    },
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "tier_change",
                "description_for_user": "매출 성장률(revenue_growth_yoy)을 Context에서 Supporting으로 승격",
                "overrides": {
                    "metric_id": "revenue_growth_yoy",
                    "from_tier": "context",
                    "to_tier": "supporting",
                },
                "confidence": 0.95,
            },
            {
                "intent_type": "tier_change",
                "description_for_user": "EPS 성장률(eps_growth_yoy)을 Context에서 Supporting으로 승격",
                "overrides": {
                    "metric_id": "eps_growth_yoy",
                    "from_tier": "context",
                    "to_tier": "supporting",
                },
                "confidence": 0.95,
            },
        ],
        "needs_clarification": False,
        "clarification_question": "",
    },
}


# ------------------------------------------------------------
# Example 3: exclude_stock
# ------------------------------------------------------------
EXAMPLE_3 = {
    "scenario": "특정 종목을 특정 지표 평가에서 제외",
    "user_hint": "NVDA는 내 확신이 있어서 PEG 평가에서 빼줘",
    "current_preset_hint": {
        "preset_id": "garp",
        "available_metric_ids_sample": ["peg_ratio", "pe_ratio", "roic"],
    },
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "exclude_stock",
                "description_for_user": "NVDA를 PEG 평가에서 제외 (이번 분석 한정)",
                "overrides": {
                    "stock_symbol": "NVDA",
                    "exclude_from_metric": "peg_ratio",
                },
                "confidence": 0.90,
            }
        ],
        "needs_clarification": False,
        "clarification_question": "",
    },
}


# ------------------------------------------------------------
# Example 4: change_comparison_group
# ------------------------------------------------------------
EXAMPLE_4 = {
    "scenario": "비교군을 섹터에서 전체 유니버스로 변경",
    "user_hint": "섹터 기준이 아니라 S&P 500 전체로 비교해줘",
    "current_preset_hint": {
        "preset_id": "garp",
        "available_metric_ids_sample": ["roic", "peg_ratio"],
    },
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "change_comparison_group",
                "description_for_user": "비교 기준을 GICS 섹터에서 S&P 500 유니버스 전체로 변경",
                "overrides": {
                    "from_scope": "sector",
                    "to_scope": "universe",
                    "affects_metric_id": "all",
                },
                "confidence": 0.95,
            }
        ],
        "needs_clarification": False,
        "clarification_question": "",
    },
}


# ------------------------------------------------------------
# Example 5: ambiguous → clarification
# ------------------------------------------------------------
EXAMPLE_5 = {
    "scenario": "모호한 '더 엄격하게' 요청",
    "user_hint": "좀 더 엄격하게 보여줘",
    "current_preset_hint": {
        "preset_id": "buffett_quality_value",
        "available_metric_ids_sample": ["roic", "roe", "peg_ratio"],
    },
    "expected_output": {
        "detected_overrides": [
            {
                "intent_type": "unknown",
                "description_for_user": "",
                "overrides": {},
                "confidence": 0.30,
            }
        ],
        "needs_clarification": True,
        "clarification_question": (
            "어떤 부분을 더 엄격하게 보고 싶으신가요? 예를 들어 "
            "(1) Core 지표의 임계값을 높일까요, "
            "(2) 비교 기준을 산업 단위로 좁힐까요, "
            "(3) 특정 지표(ROIC, PEG 등)에 집중할까요?"
        ),
    },
}


FEW_SHOT_EXAMPLES: list[dict] = [
    EXAMPLE_1,
    EXAMPLE_2,
    EXAMPLE_3,
    EXAMPLE_4,
    EXAMPLE_5,
]
