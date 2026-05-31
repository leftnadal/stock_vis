"""
Slice 2 Step 0.5 — MockLLMClient text_strategy 단위 테스트.

Step 0.5에서 도입한 진입점별 mock text strategy의 분기/검증 동작 확인.
"""

from __future__ import annotations

import json

import pytest

from apps.portfolio.llm.mocks import MockLLMClient


def test_mock_text_strategy_e1_default():
    """default text_strategy는 'e1' — OneLineDiagnosis JSON 반환."""
    mock = MockLLMClient()
    resp = mock.complete(prompt="test", provider="gemini")
    payload = json.loads(resp.text)
    assert "headline" in payload
    assert "summary" in payload


def test_mock_text_strategy_e5_explicit():
    """text_strategy='e5' — E5Response schema 통과 JSON 반환."""
    mock = MockLLMClient(text_strategy="e5")
    resp = mock.complete(prompt="test", provider="anthropic")
    payload = json.loads(resp.text)
    assert "adjustments" in payload
    assert "confidence" in payload
    assert "no_actionable_intent" in payload
    assert payload["adjustments"][0]["ticker"] == "TSLA"
    assert payload["adjustments"][0]["action"] == "decrease"


def test_mock_text_strategy_unknown_rejected():
    """미등록 strategy는 ValueError 즉시 실패 (오타 방지)."""
    with pytest.raises(ValueError, match="Unknown text_strategy"):
        MockLLMClient(text_strategy="e99_nonexistent")


def test_mock_text_strategy_e2_explicit():
    """e2 strategy 선택 시 DiagnosticCard 4요소 JSON (Slice 3 Step 0.6)."""
    mock = MockLLMClient(text_strategy="e2")
    resp = mock.complete(prompt="test", provider="anthropic")
    payload = json.loads(resp.text)
    assert "summary" in payload
    assert "strengths" in payload
    assert "weaknesses" in payload
    assert "actions" in payload
    assert isinstance(payload["strengths"], list)
    assert len(payload["strengths"]) >= 1
