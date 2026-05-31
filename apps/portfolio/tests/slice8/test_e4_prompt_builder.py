"""Slice 8 Part 3 §1 #29 — E4 V2 prompt builder 검증 (no-cost).

지시서 §1.4 명시 6건 + samples 4요소 사전 검증 (C3 하이브리드).
실제 builder 시그니처는 E4ConversationInput 객체 기반이라 sample fixture를 그에 맞게 구성.
"""

from __future__ import annotations

import re

import pytest

from apps.portfolio.prompts.e4.builder import (
    SYSTEM_PROMPT_V2_TEMPLATE,
    build_e4_messages_v2,
    build_e4_prompt_v2,
    build_v2_system_prompt,
    get_v2_system_prompt,
)
from apps.portfolio.prompts.e4.samples import DEFAULT_FEW_SHOT_SAMPLES
from apps.portfolio.schemas.e4_conversation import E4ConversationInput


@pytest.fixture
def sample_inp():
    """tier 1 (history 없음) 기본 입력."""
    return E4ConversationInput(
        portfolio_id="P001",
        preset_id="GARP",
        portfolio_metrics={
            "hhi_concentration": 0.45,
            "sector_hhi": 0.50,
            "top3_weight": 0.65,
            "holding_count": 5,
            "portfolio_beta": 1.10,
            "max_position_weight": 0.30,
            "avg_correlation": 0.40,
        },
        holdings_summary="삼성전자(005930) PE 12.5 ROIC 11.3% 비중 30%, Apple PE 28.0 ROIC 35% 비중 20%",
        current_user_question="리스크 어때?",
        tier=1,
        session_id="S001",
    )


class TestE4PromptBuilderV2:
    """V2 system prompt 4요소 + few-shot 삽입 검증."""

    def test_system_prompt_includes_4_elements(self, sample_inp):
        """system prompt에 4요소 강제 지시가 포함되어야 함."""
        system = build_v2_system_prompt()
        assert "현재 상태" in system
        assert "임계값" in system or "기준" in system
        assert "액션 제안" in system or "액션" in system
        assert "시점" in system or "기간" in system

    def test_system_prompt_includes_few_shot(self):
        """Sample 5 few-shot이 system prompt에 삽입되어야 함."""
        system = build_v2_system_prompt()
        for sample in DEFAULT_FEW_SHOT_SAMPLES:
            assert sample["title"] in system

    def test_default_samples_count(self):
        """Sample 5건 정확히 정의되어야 함."""
        assert len(DEFAULT_FEW_SHOT_SAMPLES) == 5

    def test_default_samples_have_4_elements(self):
        """각 sample answer는 4요소를 포함해야 함 (C3 하이브리드 사전 검증)."""
        for sample in DEFAULT_FEW_SHOT_SAMPLES:
            answer = sample["answer"]
            # P1: 현재가 또는 PE/PEG/ROIC
            assert any(
                kw in answer for kw in ["현재가", "주가", "PE", "PEG", "ROIC"]
            ), f"{sample['title']}: P1 미충족"
            # P2: 임계값 - 숫자 + (이상|이하|초과|미만|배|↑|↓)
            assert re.search(
                r"\d+.*?(이상|이하|초과|미만|보다|넘|않|배|↑|↓)", answer
            ), f"{sample['title']}: P2 미충족"
            # P3: 액션 동사
            assert any(
                kw in answer
                for kw in [
                    "매수",
                    "매도",
                    "보유",
                    "축소",
                    "확대",
                    "편입",
                    "제외",
                    "유지",
                ]
            ), f"{sample['title']}: P3 미충족"
            # P5: 시점/기간
            assert re.search(
                r"(분기|반기|연간|YoY|QoQ|최근\s*\d+(년|개월|주|일)|2주)", answer
            ), f"{sample['title']}: P5 미충족"

    def test_user_prompt_includes_holdings_summary(self, sample_inp):
        """v2 prompt에 holdings_summary가 포함되어야 함."""
        prompt = build_e4_prompt_v2(sample_inp)
        assert "삼성전자" in prompt
        assert "PE 12.5" in prompt
        assert "ROIC 11.3%" in prompt

    def test_question_passthrough(self, sample_inp):
        """v2 prompt에 사용자 질문이 그대로 포함되어야 함."""
        prompt = build_e4_prompt_v2(sample_inp)
        assert "리스크 어때?" in prompt


class TestE4PromptBuilderV2Auxiliary:
    """보조 함수 검증 (messages 형태, custom few-shot)."""

    def test_messages_v2_structure(self, sample_inp):
        """v2 messages는 system + user 2건 list."""
        msgs = build_e4_messages_v2(sample_inp)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        # system에 4요소 포함
        assert "현재 상태" in msgs[0]["content"]
        # user에 질문 포함
        assert "리스크 어때?" in msgs[1]["content"]

    def test_custom_few_shot_override(self, sample_inp):
        """custom few_shot_samples 전달 시 default를 대체."""
        custom = [
            {
                "title": "custom-test-title",
                "source": "test",
                "question": "테스트 질문",
                "answer": "테스트 답변",
                "action_items": [],
            }
        ]
        system = build_v2_system_prompt(few_shot_samples=custom)
        assert "custom-test-title" in system
        # default sample 제거 확인
        assert "포트폴리오 전반 리스크 평가" not in system

    def test_get_v2_system_prompt_alias(self):
        """get_v2_system_prompt가 build_v2_system_prompt와 동일 결과."""
        a = get_v2_system_prompt()
        b = build_v2_system_prompt()
        assert a == b
