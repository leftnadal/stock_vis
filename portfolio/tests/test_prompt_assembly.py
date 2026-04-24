"""D-8 Prompt assembly tests."""

from __future__ import annotations

import json

import pytest

from portfolio.tests.fixtures import sample_analysis_context, sample_user_profile


# ------------------------------------------------------------
# Tier 0
# ------------------------------------------------------------


def test_tier0_pv3_terminology_present():
    """Tier 0 system prompt에 PV3 용어 정의 블록 존재."""
    from portfolio.prompts.tier0 import build_tier0

    prompt = build_tier0()
    assert "analysis_target_portfolio" in prompt
    assert "wallet_all_holdings" in prompt
    assert "excluded_from_this_portfolio" in prompt


def test_tier0_char_budget():
    """Tier 0 char 예산 5000~9000."""
    from portfolio.prompts.tier0 import build_tier0

    prompt = build_tier0()
    assert 5000 <= len(prompt) <= 9000


def test_tier0_include_style_flag():
    """include_style=False이면 더 짧아야 함."""
    from portfolio.prompts.tier0 import build_tier0

    full = build_tier0()
    no_style = build_tier0(include_style=False)
    assert len(no_style) < len(full)


# ------------------------------------------------------------
# E1~E3 (analysis-result 기반, 동기)
# ------------------------------------------------------------


def test_e1_assembly():
    from portfolio.prompts.e1 import build_e1_input, build_e1_prompt

    ctx = sample_analysis_context.get_context_garp_tech()
    system, user = build_e1_prompt(ctx)
    assert len(system) > 100 and len(user) > 100

    # E1 input에는 return_breakdown 상세가 없어야 함 (총 수익률만)
    input_data = build_e1_input(ctx)
    assert "analysis_target_portfolio" in input_data
    assert "wallet_background" in input_data
    assert "core_metric_results" not in input_data["analysis_target_portfolio"]


def test_e2_assembly_and_input_has_weakness_detail():
    from portfolio.prompts.e2 import build_e2_input, build_e2_prompt

    ctx = sample_analysis_context.get_context_garp_tech()
    system, user = build_e2_prompt(ctx)
    assert len(user) > 100

    data = build_e2_input(ctx)
    assert "weaknesses_detail" in data["analysis_target_portfolio"]


def test_e3_excludes_wallet_and_context_tier():
    """E3는 Wallet 미포함 + Context tier 미포함."""
    from portfolio.prompts.e3 import build_e3_input, build_e3_prompt

    ctx = sample_analysis_context.get_context_garp_tech()
    data = build_e3_input(ctx)

    assert "wallet_background" not in data
    for m in data["metrics"]:
        assert m["tier"] in ("core", "supporting")

    system, user = build_e3_prompt(ctx)
    assert "wallet_background" not in user  # E3 input JSON 안에 없어야 함


# ------------------------------------------------------------
# E4 (Django DB 필요)
# ------------------------------------------------------------


@pytest.mark.django_db
def test_e4_assembly_all_tiers():
    from django.contrib.auth import get_user_model

    from portfolio.models import ChatSession
    from portfolio.prompts.e4 import build_e4_prompt

    User = get_user_model()
    user = User.objects.create_user(username="e4-test")
    session = ChatSession.objects.create(user=user)

    ctx = sample_analysis_context.get_context_garp_tech()
    profile = sample_user_profile.get_aggressive_tech_profile()

    prompt = build_e4_prompt(ctx, session, profile, "왜 NVDA가 약점이야?")
    assert "system" in prompt and "messages" in prompt
    assert prompt["messages"][-1] == {"role": "user", "content": "왜 NVDA가 약점이야?"}
    # Tier 3 블록은 profile 있으므로 system 에 포함
    assert "Investment style" in prompt["system"]


@pytest.mark.django_db
def test_e4_empty_profile_omits_tier3():
    from django.contrib.auth import get_user_model

    from portfolio.models import ChatSession
    from portfolio.prompts.e4 import build_e4_prompt

    User = get_user_model()
    user = User.objects.create_user(username="e4-empty")
    session = ChatSession.objects.create(user=user)

    ctx = sample_analysis_context.get_context_garp_tech()
    prompt = build_e4_prompt(ctx, session, None, "hi")

    assert "Investment style" not in prompt["system"]


# ------------------------------------------------------------
# E5, E6
# ------------------------------------------------------------


def test_e5_no_tier1_or_tier3():
    from portfolio.prompts.e5 import build_e5_prompt

    system, user = build_e5_prompt("ROIC 20%로", "buffett_quality_value")
    assert "Investment style" not in system
    # include_style=False 효과 확인 — STYLE 섹션 헤더가 없어야 함
    assert "STYLE & TONE RULES" not in system
    # 하지만 terminology는 있어야 함
    assert "TERMINOLOGY DEFINITIONS" in system


def test_e6_assembly_with_overrides():
    from portfolio.prompts.e6 import build_e6_input, build_e6_prompt

    original = sample_analysis_context.get_context_garp_tech()
    adjusted = sample_analysis_context.get_context_garp_tech_with_roic_20()
    overrides = [{
        "intent_type": "threshold_change",
        "overrides": {"metric_id": "roic", "old_threshold": 0.15, "new_threshold": 0.20},
    }]

    system, user = build_e6_prompt(original, adjusted, overrides)
    assert "applied_overrides" in user
    data = build_e6_input(original, adjusted, overrides)
    assert data["applied_overrides"] == overrides


# ------------------------------------------------------------
# Few-shot 예시 JSON 유효성 (전 진입점 공통)
# ------------------------------------------------------------


def test_all_few_shot_examples_valid_json():
    """E1/E2/E3/E5/E6 예시의 input/output JSON이 모두 파싱 가능해야 함."""
    from portfolio.prompts.e1.examples import FEW_SHOT_EXAMPLES as E1
    from portfolio.prompts.e2.examples import FEW_SHOT_EXAMPLES as E2
    from portfolio.prompts.e3.examples import FEW_SHOT_EXAMPLES as E3

    for inp, out in E1 + E3:
        json.loads(inp)
        json.loads(out)

    for ex in E2:
        json.loads(ex["input"])
        json.loads(ex["output"])
