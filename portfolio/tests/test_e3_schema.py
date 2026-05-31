"""E3 schema + Mock 단위 테스트 (Slice 5 Step 1).

E3Request validator + _mock_text_e3 schema 통과 검증.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from portfolio.llm.mocks import MockLLMClient, _mock_text_e3
from portfolio.schemas.llm import E3Request
from portfolio.schemas.llm_outputs import MetricComments


def test_e3_request_valid():
    """analysis_context dict 포함 시 model_validate 성공."""
    req = E3Request(
        analysis_context={
            "analysis_target_portfolio": {"preset_id": "garp"},
        }
    )
    assert req.session_id is None
    assert "analysis_target_portfolio" in req.analysis_context


def test_e3_request_extra_forbidden():
    """extra='forbid' — 정의되지 않은 필드 거절."""
    with pytest.raises(ValidationError):
        E3Request(
            analysis_context={"analysis_target_portfolio": {}},
            unknown_key="hack",
        )


def test_e3_request_missing_analysis_context():
    """analysis_context 필드 누락 시 ValidationError."""
    with pytest.raises(ValidationError):
        E3Request()  # type: ignore[call-arg]


def test_mock_text_e3_returns_valid_json():
    """_mock_text_e3 출력이 MetricComments schema 통과."""
    raw = _mock_text_e3('{"metric_id": "roic"}')
    data = json.loads(raw)
    parsed = MetricComments.model_validate(data)
    assert len(parsed.comments) >= 1
    for c in parsed.comments:
        assert 10 <= len(c.one_liner) <= 300


def test_mock_text_e3_extracts_metric_ids():
    """prompt에 'metric_id': 'roic' 포함 시 출력 metric_id에 roic 포함."""
    prompt = (
        '{"metrics": ['
        '{"metric_id": "roic", "tier": "core"},'
        '{"metric_id": "pe_ratio", "tier": "supporting"}'
        "]}"
    )
    raw = _mock_text_e3(prompt)
    data = json.loads(raw)
    metric_ids = {c["metric_id"] for c in data["comments"]}
    assert "roic" in metric_ids
    assert "pe_ratio" in metric_ids
    # MockLLMClient 통합 호환 확인
    mock = MockLLMClient(text_strategy="e3")
    resp = mock.complete(prompt=prompt, provider="anthropic")
    assert "comments" in resp.text
