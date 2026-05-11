"""
Slice 2 Step 2 — services/e5_adjustment_parser 단위 테스트.

검증 항목:
  1. build_e5_prompt: 종목/명령 포함
  2. build_e5_prompt: schema 지시문 포함
  3. parse + validate: 정상 JSON
  4. parse + validate: 마크다운 펜스 자동 제거
  5. parse + validate: invalid action 거절
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from portfolio.llm.parsers import parse_json_response
from portfolio.schemas.llm import E5Request, E5Response
from portfolio.services.e5_adjustment_parser import build_e5_prompt


def _sample_request(command: str) -> E5Request:
    return E5Request(
        analysis_context={
            "holdings": [
                {"ticker": "MSFT", "weight": 0.3},
                {"ticker": "TSLA", "weight": 0.2},
                {"ticker": "NVDA", "weight": 0.5},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "GARP 적합도 양호. TSLA 비중 과다.",
            },
        },
        user_command=command,
    )


def test_build_prompt_contains_holdings_and_command():
    req = _sample_request("TSLA 좀 줄여줘")
    prompt = build_e5_prompt(req)
    assert "MSFT" in prompt
    assert "TSLA" in prompt
    assert "TSLA 좀 줄여줘" in prompt


def test_build_prompt_contains_schema_directive():
    req = _sample_request("아무거나")
    prompt = build_e5_prompt(req)
    assert "JSON" in prompt
    assert "마크다운" in prompt
    assert "no_actionable_intent" in prompt
    assert "reason_quote" in prompt


def test_parse_e5_valid_json():
    raw = (
        '{"adjustments":[{"ticker":"TSLA","action":"decrease",'
        '"delta_weight":-0.05,"target_weight":null,'
        '"reason_quote":"TSLA 줄여"}],'
        '"confidence":4,"ambiguity_notes":null,'
        '"no_actionable_intent":false}'
    )
    parsed = parse_json_response(E5Response, raw)
    assert isinstance(parsed, E5Response)
    assert len(parsed.adjustments) == 1
    assert parsed.adjustments[0].ticker == "TSLA"


def test_parse_e5_with_markdown_fence():
    raw = (
        "```json\n"
        '{"adjustments":[],"confidence":3,"ambiguity_notes":null,'
        '"no_actionable_intent":true}\n'
        "```"
    )
    parsed = parse_json_response(E5Response, raw)
    assert parsed.no_actionable_intent is True
    assert parsed.adjustments == []


def test_parse_e5_invalid_action_rejected():
    raw = (
        '{"adjustments":[{"ticker":"X","action":"INVALID_ACTION",'
        '"delta_weight":null,"target_weight":null,"reason_quote":"..."}],'
        '"confidence":3,"ambiguity_notes":null,"no_actionable_intent":false}'
    )
    with pytest.raises(ValidationError):
        parse_json_response(E5Response, raw)
