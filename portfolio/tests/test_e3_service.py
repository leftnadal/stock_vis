"""E3 service 단위 테스트 (Slice 5 Step 4).

build_e3_prompt wrapper / parse_e3_response / run_e3 (Mock client) 검증.
fallback / error 시나리오는 test_e3_view.py에서 view 통합으로 검증.
"""

from __future__ import annotations

import pytest

from portfolio.llm.mocks import MockLLMClient
from portfolio.schemas.llm import E3Request
from portfolio.schemas.llm_outputs import MetricComments
from portfolio.services.e3_metric_comment import (
    build_e3_prompt,
    parse_e3_response,
    run_e3,
)
from portfolio.tests.fixtures.sample_analysis_context import (
    get_context_garp_tech,
)


def _sample_request() -> E3Request:
    """garp_tech AnalysisContext → E3Request."""
    ctx = get_context_garp_tech()
    return E3Request(analysis_context=ctx.model_dump(mode="json"))


def test_build_e3_prompt_wrapper_concat():
    """raw build_e3_prompt가 (system, user) tuple → wrapper가 concat 단일 str."""
    ctx = get_context_garp_tech()
    prompt = build_e3_prompt(ctx)
    assert isinstance(prompt, str)
    # system + "\n\n" + user 형식 — system 끝과 user 시작이 \n\n으로 분리
    assert "\n\n" in prompt
    # E3_INSTRUCTIONS 헤더 포함 확인
    assert "Per-Metric Commentary" in prompt or "E3" in prompt


def test_build_e3_prompt_contains_metrics():
    """prompt에 Core/Supporting metric_id 포함 확인."""
    ctx = get_context_garp_tech()
    prompt = build_e3_prompt(ctx)
    p = ctx.analysis_target_portfolio
    # Core + Supporting metric ids 중 최소 1개 포함
    metric_ids = [
        m.metric_id
        for m in p.core_metric_results + p.supporting_metric_results
    ]
    assert any(mid in prompt for mid in metric_ids)


def test_parse_e3_response_valid():
    """JSON 응답 → MetricComments parse 성공."""
    raw = (
        '{"comments": ['
        '{"metric_id": "roic", "one_liner": "ROIC 지표가 동종 업계 대비 우수합니다."}'
        ']}'
    )
    parsed = parse_e3_response(raw)
    assert isinstance(parsed, MetricComments)
    assert len(parsed.comments) == 1
    assert parsed.comments[0].metric_id == "roic"


def test_parse_e3_response_with_markdown_fence():
    """LLM이 ```json...``` 펜스를 추가해도 parse 성공."""
    raw = (
        "```json\n"
        '{"comments": ['
        '{"metric_id": "pe_ratio", "one_liner": "PE 비율이 적정 수준에서 유지되고 있습니다."}'
        ']}\n'
        "```"
    )
    parsed = parse_e3_response(raw)
    assert parsed.comments[0].metric_id == "pe_ratio"


def test_parse_e3_response_invalid_json_raises():
    """잘못된 JSON → ValidationError 또는 JSONDecodeError raise."""
    with pytest.raises(Exception):  # ValidationError | JSONDecodeError
        parse_e3_response("not a json content")


def test_run_e3_normal_flow_with_mock():
    """Mock client (text_strategy='e3') 정상 흐름 → response/metadata."""
    mock = MockLLMClient(text_strategy="e3")
    result = run_e3(_sample_request(), provider="haiku", client=mock)
    assert "response" in result and "metadata" in result
    assert "comments" in result["response"]
    assert len(result["response"]["comments"]) >= 1
    # PROVIDER_KWARGS["haiku"] → provider="anthropic"
    assert result["metadata"]["provider"] == "anthropic"


def test_run_e3_default_provider_is_haiku():
    """default provider 미지정 시 haiku 사용 (글쓰기 가설 5번째 외삽)."""
    mock = MockLLMClient(text_strategy="e3")
    # provider 인자 미전달 — default haiku 사용
    result = run_e3(_sample_request(), client=mock)
    assert result["metadata"]["provider"] == "anthropic"


def test_run_e3_unknown_provider_raises():
    """등록되지 않은 provider label → ValueError."""
    with pytest.raises(ValueError, match="Unknown provider label"):
        run_e3(_sample_request(), provider="not_a_provider")  # type: ignore[arg-type]
