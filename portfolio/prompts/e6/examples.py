"""
E6 few-shot 예시 2개 — threshold 상향 효과 + exclude_stock 효과.

Version: 1.1 (2026-04-24)
"""

# ------------------------------------------------------------
# Example 1: ROIC threshold 15% → 20% 상향 후
# ------------------------------------------------------------
EXAMPLE_1 = {
    "scenario": "Buffett Quality Value 프리셋에서 ROIC 임계값 15%→20% 상향",
    "input": {
        "preset_id": "buffett_quality_value",
        "preset_name": "Buffett Quality Value",
        "original_summary": {
            "strengths": [
                {"metric_id": "roic", "level_tag": "excellent",
                 "reason_hint": "5종목 중 4개가 15% 상회"},
                {"metric_id": "earnings_consistency_5y", "level_tag": "good",
                 "reason_hint": "5종목 중 4개 안정적"},
            ],
            "weaknesses": [
                {"metric_id": "pe_ratio", "level_tag": "moderate",
                 "reason_hint": "업종 대비 상단"},
                {"metric_id": "debt_to_equity", "level_tag": "weak",
                 "reason_hint": "1종목 0.8"},
            ],
            "diagnostic_cards": [
                {"weakness_metric_id": "pe_ratio",
                 "severity": "medium", "structural_or_single": "structural"}
            ],
            "total_return": 0.11,
        },
        "adjusted_summary": {
            "strengths": [
                {"metric_id": "roic", "level_tag": "excellent",
                 "reason_hint": "5종목 중 3개가 20% 상회"},
                {"metric_id": "earnings_consistency_5y", "level_tag": "good",
                 "reason_hint": "5종목 중 4개 안정적"},
                {"metric_id": "revenue_growth_yoy", "level_tag": "good",
                 "reason_hint": "평가 가중 상승으로 부각"},
            ],
            "weaknesses": [
                {"metric_id": "pe_ratio", "level_tag": "moderate",
                 "reason_hint": "업종 대비 상단"},
                {"metric_id": "debt_to_equity", "level_tag": "weak",
                 "reason_hint": "1종목 0.8"},
                {"metric_id": "roic", "level_tag": "weak",
                 "reason_hint": "INTC가 20% 미달"},
            ],
            "diagnostic_cards": [
                {"weakness_metric_id": "pe_ratio",
                 "severity": "medium", "structural_or_single": "structural"},
                {"weakness_metric_id": "roic",
                 "severity": "medium", "structural_or_single": "single_outlier"},
            ],
            "total_return": 0.11,
        },
        "applied_overrides": [
            {
                "intent_type": "threshold_change",
                "overrides": {
                    "metric_id": "roic",
                    "old_threshold": 0.15,
                    "new_threshold": 0.20,
                },
            }
        ],
    },
    "expected_output": {
        "key_changes": [
            "ROIC 통과 종목이 4개에서 3개로 감소. INTC가 새로 ROIC 약점에 편입",
            "INTC ROIC level_tag: moderate → weak 로 전환",
            "revenue_growth_yoy가 새롭게 강점으로 부각 (평가 가중 상승 효과)",
            "약점 구성: 기존 'pe_ratio + debt_to_equity' → 'pe_ratio + debt_to_equity + ROIC(INTC 단일)'",
            "진단 카드 수 1개 → 2개 (ROIC single_outlier 카드 추가)",
        ],
        "summary": (
            "ROIC 기준을 상향하자 INTC의 취약성이 단일 이상치 형태로 드러났고, 동시에 "
            "성장 지표가 강점으로 부각되었습니다. 현재 구성이 순수 Buffett보다는 "
            "Quality Growth 관점에 더 가까울 수 있음을 시사합니다."
        ),
        "implication_for_user": (
            "Quality Growth 프리셋으로도 한 번 분석해보시면 성장 관점에서의 강약점이 "
            "더 뚜렷하게 드러날 수 있습니다."
        ),
    },
}


# ------------------------------------------------------------
# Example 2: NVDA를 PEG 평가에서 제외
# ------------------------------------------------------------
EXAMPLE_2 = {
    "scenario": "GARP 프리셋에서 NVDA를 PEG 평가에서 제외",
    "input": {
        "preset_id": "garp",
        "preset_name": "GARP",
        "original_summary": {
            "strengths": [
                {"metric_id": "roic", "level_tag": "good",
                 "reason_hint": "평균 18%"}
            ],
            "weaknesses": [
                {"metric_id": "peg_ratio", "level_tag": "critical",
                 "reason_hint": "평균 PEG 2.8, 모두 2.0 이상"}
            ],
            "diagnostic_cards": [
                {"weakness_metric_id": "peg_ratio",
                 "severity": "high", "structural_or_single": "structural"}
            ],
            "total_return": 0.14,
        },
        "adjusted_summary": {
            "strengths": [
                {"metric_id": "roic", "level_tag": "good",
                 "reason_hint": "평균 18%"}
            ],
            "weaknesses": [
                {"metric_id": "peg_ratio", "level_tag": "weak",
                 "reason_hint": "NVDA 제외 평균 PEG 2.4"}
            ],
            "diagnostic_cards": [
                {"weakness_metric_id": "peg_ratio",
                 "severity": "medium", "structural_or_single": "structural"}
            ],
            "total_return": 0.14,
        },
        "applied_overrides": [
            {
                "intent_type": "exclude_stock",
                "overrides": {
                    "stock_symbol": "NVDA",
                    "exclude_from_metric": "peg_ratio",
                },
            }
        ],
    },
    "expected_output": {
        "key_changes": [
            "PEG 평가 평균: 2.8 → 2.4 (NVDA 제외 효과)",
            "PEG 약점 level_tag: critical → weak 로 완화",
            "PEG 진단 카드 severity: high → medium",
            "structural_or_single: structural 유지 (나머지 4종목이 모두 PEG 2.0 이상)",
        ],
        "summary": (
            "NVDA 제외는 평균 수치와 severity 완화에 기여했으나, 나머지 4개 종목도 "
            "모두 PEG 2.0 이상으로 구조적 밸류에이션 부담은 남아있습니다."
        ),
        "implication_for_user": (
            "NVDA에 대한 확신은 반영되었지만, 포트폴리오 전반의 성장 대비 가격 부담은 "
            "여전히 관찰 대상입니다."
        ),
    },
}


FEW_SHOT_EXAMPLES: list[dict] = [EXAMPLE_1, EXAMPLE_2]
