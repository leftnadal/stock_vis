"""
E4 few-shot 예시 3개 — 다양한 의도 유형(Q&A / 조정 요청 / 비교군 변경).

각 예시는 scenario + user_message + expected_output.
Tier 2.5, Tier 1 snippet은 실제 조립 단계에서 시스템 프롬프트에 들어가므로
예시에서는 시나리오 설명과 최종 입출력만 보여준다.

Version: 1.1 (2026-04-24)
"""

# ------------------------------------------------------------
# Example 1: Pure Q&A (no adjustment intent)
# ------------------------------------------------------------
EXAMPLE_1 = {
    "scenario": "사용자가 특정 종목이 약점으로 분류된 이유를 질문 (Q&A only)",
    "user_message": "왜 INTC가 약점으로 나왔어?",
    "expected_output": {
        "response_text": (
            "INTC는 Buffett Quality Value 프리셋의 Core 지표인 ROIC 기준에서 "
            "업종 하위 35% 구간에 위치하며, 5년 지속성 통과율도 40%에 그칩니다. "
            "Buffett 관점의 '꾸준한 자본 수익'이라는 핵심 기준에서 벗어나 있어 "
            "약점으로 분류된 것으로 보입니다. 다만 최근 CAPEX 증가로 인한 일시적 "
            "효과 가능성도 있어, 향후 2~3분기 추이를 함께 관찰하실 필요가 있을 수 있습니다."
        ),
        "has_adjustment_intent": False,
        "adjustment_parse_hint": "",
    },
}


# ------------------------------------------------------------
# Example 2: Level-1 adjustment request (threshold + tier 상향)
# ------------------------------------------------------------
EXAMPLE_2 = {
    "scenario": "사용자가 ROIC 임계값 상향 + 성장 지표 가중치 상향 요청",
    "user_message": (
        "Buffett보다는 성장 요소를 좀 더 보고 싶어. "
        "ROIC 임계값을 20%로 올리고, 성장 지표 가중을 높여서 다시 보여줘."
    ),
    "expected_output": {
        "response_text": (
            "ROIC 기준을 더 높이고 성장 지표의 비중을 올리시려는 의도로 읽힙니다. "
            "조정 내용을 정리해서 확인 카드로 보여드릴게요. 실행하시면 이번 분석에만 "
            "적용됩니다."
        ),
        "has_adjustment_intent": True,
        "adjustment_parse_hint": (
            "ROIC 임계값을 현재 값에서 20%로 상향. "
            "성장 지표(revenue_growth_yoy, eps_growth_yoy) 가중치 상향."
        ),
    },
}


# ------------------------------------------------------------
# Example 3: Comparison group change
# ------------------------------------------------------------
EXAMPLE_3 = {
    "scenario": "사용자가 비교 기준을 산업에서 전체 유니버스로 변경 요청",
    "user_message": "섹터 말고 S&P 500 전체 유니버스 기준으로 봐줘.",
    "expected_output": {
        "response_text": (
            "비교 기준을 업종(섹터)에서 S&P 500 전체 유니버스로 전환하시려는 거군요. "
            "확인 카드로 조정 내용을 정리해드릴게요."
        ),
        "has_adjustment_intent": True,
        "adjustment_parse_hint": (
            "percentile_scope를 industry/sector에서 universe로 변경. "
            "전체 유니버스 = S&P 500."
        ),
    },
}


FEW_SHOT_EXAMPLES: list[dict] = [EXAMPLE_1, EXAMPLE_2, EXAMPLE_3]
