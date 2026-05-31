"""E2 service 단위 테스트 (Slice 3 Step 2)."""

from __future__ import annotations

import pytest

from portfolio.schemas.llm import E2Request, E2Response
from portfolio.services.e2_diagnostic_card import (
    build_e2_prompt,
    parse_e2_response,
)


def _sample_request() -> E2Request:
    return E2Request(
        analysis_context={
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.4},
                {"ticker": "GOOGL", "weight": 0.3},
                {"ticker": "AAPL", "weight": 0.3},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "GARP 적합도 양호. 안정적 균형.",
            },
            "metrics": {
                "P/E": 22.5,
                "ROE": 0.18,
                "Debt/Equity": 0.35,
            },
        },
    )


def test_build_prompt_contains_holdings():
    prompt = build_e2_prompt(_sample_request())
    assert "MSFT" in prompt
    assert "GOOGL" in prompt
    assert "garp" in prompt


def test_build_prompt_contains_4_elements_directive():
    prompt = build_e2_prompt(_sample_request())
    assert "summary" in prompt
    assert "strengths" in prompt
    assert "weaknesses" in prompt
    assert "actions" in prompt


def test_build_prompt_contains_metrics_table():
    prompt = build_e2_prompt(_sample_request())
    assert "P/E" in prompt
    assert "ROE" in prompt


def test_parse_e2_response_valid():
    raw = """{
        "summary": "GARP 적합도 우수. 균형 잡힌 포트폴리오 구성.",
        "strengths": ["P/E 22.5 적정 수준", "ROE 18% 양호한 수익성"],
        "weaknesses": ["기술주 비중 다소 높음"],
        "actions": ["분기별 ROE 모니터링 권장"]
    }"""
    parsed = parse_e2_response(raw, preset_id="garp")
    assert isinstance(parsed, E2Response)
    assert parsed.card.summary.startswith("GARP")
    assert len(parsed.card.strengths) == 2
    assert parsed.preset_id == "garp"


def test_parse_e2_response_with_markdown_fence():
    raw = (
        "```json\n"
        '{"summary":"포트폴리오 요약 텍스트 충분히 긴 길이로 작성한 예시입니다.",'
        '"strengths":["강점 항목 충분히 길다"],'
        '"weaknesses":["약점 항목 충분히 길다"],'
        '"actions":["액션 항목 충분히 길다"]}\n'
        "```"
    )
    parsed = parse_e2_response(raw)
    assert parsed.card.summary.startswith("포트폴리오")


def test_parse_e2_response_completeness_violation():
    """리스트 항목 10자 미만 → ValidationError (completeness 자동 측정)."""
    raw = (
        '{"summary":"요약 텍스트 충분한 길이로 작성합니다.",'
        '"strengths":["짧음"],'
        '"weaknesses":["약점 적당한 길이"],'
        '"actions":["액션 적당한 길이"]}'
    )
    with pytest.raises(Exception):  # ValidationError 또는 LLM parse error
        parse_e2_response(raw)
