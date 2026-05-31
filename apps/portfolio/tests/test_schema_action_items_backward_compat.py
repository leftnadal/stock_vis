"""7 schema action_items 필드 backward-compat 검증 (Slice 8 Part 2 Step 2, #28)."""

import pytest

from apps.portfolio.schemas.commentary_output import ActionItem
from apps.portfolio.schemas.e4_conversation import E4ConversationOutput
from apps.portfolio.schemas.llm import E2Response, E5Response, LLMResponse
from apps.portfolio.schemas.llm_outputs import (
    ConversationResponse,
    E3PortfolioCommentary,
    E6ComparisonResponse,
)

SCHEMA_TARGETS = [
    LLMResponse,
    E5Response,
    E2Response,
    E3PortfolioCommentary,
    E6ComparisonResponse,
    ConversationResponse,
    E4ConversationOutput,
]


@pytest.mark.parametrize("schema_cls", SCHEMA_TARGETS)
def test_action_items_field_exists(schema_cls):
    """모든 7 schema에 action_items 필드가 정의되어야 함."""
    assert "action_items" in schema_cls.model_fields, (
        f"{schema_cls.__name__}: action_items 필드 미정의"
    )


@pytest.mark.parametrize("schema_cls", SCHEMA_TARGETS)
def test_action_items_default_empty_list(schema_cls):
    """action_items 필드의 기본값은 빈 리스트 (backward-compat 핵심)."""
    field_info = schema_cls.model_fields["action_items"]
    # default_factory=list → 호출 시 [] 반환
    assert field_info.default_factory is not None, (
        f"{schema_cls.__name__}: action_items default_factory 누락"
    )
    assert field_info.default_factory() == []


def test_action_items_accepts_valid_items():
    """action_items가 ActionItem 리스트를 정상 수용 — LLMResponse 케이스."""
    item = ActionItem(
        title="현금 비중 축소",
        description="포트폴리오 현금 비중이 25%로 과도하여 축소 검토.",
        priority="high",
    )
    resp = LLMResponse(
        text="dummy",
        provider="anthropic",
        model="claude-haiku-4-5",
        latency_ms=100,
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.001,
        action_items=[item],
    )
    assert len(resp.action_items) == 1
    assert resp.action_items[0].title == "현금 비중 축소"
    assert resp.action_items[0].priority == "high"


def test_action_items_default_omitted_construction():
    """action_items 생략 시 빈 리스트로 초기화 (backward-compat)."""
    resp = LLMResponse(
        text="dummy",
        provider="anthropic",
        model="claude-haiku-4-5",
        latency_ms=100,
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.001,
    )
    assert resp.action_items == []
