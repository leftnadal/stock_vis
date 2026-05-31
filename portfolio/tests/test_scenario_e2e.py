"""D-8 end-to-end 시나리오 테스트.

LLM 실제 호출 없이 dry-run. 각 진입점이 AnalysisContext를 받아 system/user
프롬프트를 정상 생성하는지 flow 검증.
"""

from __future__ import annotations

import pytest

from portfolio.tests.fixtures import sample_analysis_context


@pytest.mark.django_db
def test_scenario_analyze_question_adjust_compare():
    """전체 사용자 흐름: 분석 실행 → E1~E3 → E4 대화 → E5 파싱 → E6 비교."""
    from django.contrib.auth import get_user_model

    from portfolio.models import ChatSession
    from portfolio.prompts.e1 import build_e1_prompt
    from portfolio.prompts.e2 import build_e2_prompt
    from portfolio.prompts.e3 import build_e3_prompt
    from portfolio.prompts.e4 import build_e4_prompt
    from portfolio.prompts.e5 import build_e5_prompt
    from portfolio.prompts.e6 import build_e6_prompt

    # Context 준비
    ctx = sample_analysis_context.get_context_garp_tech()

    # Step 1: 분석 완료 직후 E1~E3
    e1_system, e1_user = build_e1_prompt(ctx)
    assert e1_user

    e2_system, e2_user = build_e2_prompt(ctx)
    assert e2_user

    e3_system, e3_user = build_e3_prompt(ctx)
    assert e3_user

    # Step 2: 사용자 질문 (E4 대화)
    User = get_user_model()
    user = User.objects.create_user(username="e2e-user")
    session = ChatSession.objects.create(user=user)

    e4 = build_e4_prompt(ctx, session, None, "왜 NVDA가 약점이야?")
    assert e4["messages"][-1]["content"] == "왜 NVDA가 약점이야?"

    # Step 3: 조정 요청 의도 (E4 재호출 — has_adjustment_intent=true 예상)
    e4_adjust = build_e4_prompt(
        ctx, session, None, "ROIC 기준을 20%로 올려서 다시 봐줘"
    )
    assert "ROIC" in e4_adjust["messages"][-1]["content"]

    # Step 4: E5 조정 파싱
    e5_system, e5_user = build_e5_prompt(
        user_hint="ROIC 임계값을 20%로 상향",
        current_preset_id="garp",
    )
    assert "threshold_change" in e5_user

    # Step 5: 조정된 분석 결과 (mock) + E6 비교
    adjusted_ctx = sample_analysis_context.get_context_garp_tech_with_roic_20()
    overrides = [
        {
            "intent_type": "threshold_change",
            "overrides": {
                "metric_id": "roic",
                "old_threshold": 0.15,
                "new_threshold": 0.20,
            },
        }
    ]
    e6_system, e6_user = build_e6_prompt(ctx, adjusted_ctx, overrides)
    assert "applied_overrides" in e6_user
    # 조정 결과에만 overrides_applied가 있어야 함
    assert adjusted_ctx.analysis_target_portfolio.overrides_applied is not None
    assert ctx.analysis_target_portfolio.overrides_applied is None


def test_scenario_dividend_preset():
    """배당 프리셋 플로우도 동일하게 동작."""
    from portfolio.prompts.e1 import build_e1_prompt
    from portfolio.prompts.e3 import build_e3_prompt

    ctx = sample_analysis_context.get_context_dividend()
    e1_system, e1_user = build_e1_prompt(ctx)
    assert "Dividend Growth" in e1_user or "dividend_growth" in e1_user

    e3_system, e3_user = build_e3_prompt(ctx)
    assert "dividend_yield" in e3_user
