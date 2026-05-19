"""Slice 12 Step 0 #59 — E3 prompt action_items measurability 규칙 검증.

Slice 11 Part 5 E3 actionability NG ratio 50% (2/4) 발견 →
prompt에 action_items 작성 규칙 4종 명시하여 NG 감소 목표 (< 30%).

테스트 항목 (3건):
1. E3 prompt에 action_items 작성 규칙 헤더 명시
2. 금지 패턴 명시 ("모니터링 필요"/"검토하세요"/"주시하세요" 단독 금지)
3. priority 정합성 규칙 명시 (high/medium/low 기준)
"""

from __future__ import annotations

from portfolio.services.coach.prompt_builder import E3PromptBuilder
from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_input


def test_e3_prompt_includes_action_rules_header():
    """E3 prompt에 'action_items 작성 규칙' 헤더 + 구체성/측정가능성 항목 포함."""
    inp = load_portfolio_a2_input("e3")
    msgs = E3PromptBuilder.build_messages(inp)
    user = msgs[1]["content"]
    assert "action_items 작성 규칙" in user
    assert "구체성 필수" in user
    assert "측정 가능성 필수" in user
    # Slice 12 Step 0 #59 marker
    assert "#59" in user


def test_e3_prompt_forbids_single_monitor_phrases():
    """금지 패턴 3종 명시 (단독 사용 금지)."""
    inp = load_portfolio_a2_input("e3")
    msgs = E3PromptBuilder.build_messages(inp)
    user = msgs[1]["content"]
    assert "모니터링 필요" in user
    assert "검토하세요" in user
    assert "주시하세요" in user
    assert "단독 사용 금지" in user or "단독" in user


def test_e3_prompt_priority_consistency_rules():
    """priority 정합성 규칙 (high/medium/low 기준) 명시."""
    inp = load_portfolio_a2_input("e3")
    msgs = E3PromptBuilder.build_messages(inp)
    user = msgs[1]["content"]
    assert "priority 정합성" in user
    assert "high" in user
    assert "medium" in user
    assert "low" in user
