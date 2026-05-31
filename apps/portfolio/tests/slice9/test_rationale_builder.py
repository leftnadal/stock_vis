"""Slice 9 #44 — rationale prompt builder 단위 테스트.

지시서 §1.3 — builder 단위 테스트 2건.
"""

from __future__ import annotations

from portfolio.prompts.rationale.builder import (
    RATIONALE_SYSTEM_PROMPT,
    build_rationale_prompt,
)

SPECIFICITY_DETAIL_FIXTURE = {
    "P1_metric_mention": True,
    "P2_threshold": True,
    "P3_action_verb": False,
    "P4_quantitative": False,
    "P5_time_period": True,
}


class TestRationaleBuilder:
    def test_system_prompt_quotes_four_elements(self) -> None:
        """system prompt에 4요소(현재 상태/임계값/액션 제안/시점)가 모두 인용되어야 함."""
        prompt = RATIONALE_SYSTEM_PROMPT
        assert "현재 상태" in prompt
        assert "임계값" in prompt
        assert "액션 제안" in prompt
        assert "시점/기간" in prompt
        # 출력 형식 JSON 강제
        assert "rationale_text" in prompt
        assert "rationale_score" in prompt
        assert "rationale_categories" in prompt

    def test_user_prompt_embeds_patterns_detail(self) -> None:
        """user prompt에 P1~P5 자동 검출 결과가 포함되어야 함."""
        system, user = build_rationale_prompt(
            case_name="S01_haiku",
            original_commentary="현재 PE 15 이상 …",
            original_question="포트폴리오 평가해줘",
            specificity_detail=SPECIFICITY_DETAIL_FIXTURE,
        )
        assert system == RATIONALE_SYSTEM_PROMPT
        # case + commentary + question 인용
        assert "S01_haiku" in user
        assert "현재 PE 15 이상" in user
        assert "포트폴리오 평가해줘" in user
        # P1~P5 detail 인용 (True/False 문자열)
        assert "P1 (현재가/지표 언급): True" in user
        assert "P2 (임계값 명시): True" in user
        assert "P3 (액션 동사): False" in user
        assert "P4 (구체 수치): False" in user
        assert "P5 (시점/기간): True" in user
