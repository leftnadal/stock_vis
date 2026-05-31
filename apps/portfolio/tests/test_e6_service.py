"""E6 service 단위 테스트 (Slice 4 Step 4).

build_e6_prompt / parse_e6_response / run_e6 (Mock client) 검증.
fallback / error 시나리오는 test_e6_view.py에서 view 통합으로 검증.
"""

from __future__ import annotations

import pytest

from apps.portfolio.llm.mocks import MockLLMClient
from apps.portfolio.schemas.llm import AdjustmentItem, E6Request
from apps.portfolio.schemas.llm_outputs import E6ComparisonResponse
from apps.portfolio.services.e6_comparison import (
    _format_adjustments_block,
    build_e6_prompt,
    parse_e6_response,
    run_e6,
)


def _sample_request(*, with_intent: bool = True) -> E6Request:
    return E6Request(
        analysis_context={
            "preset_id": "garp",
            "holdings": [
                {"ticker": "MSFT", "weight": 0.30},
                {"ticker": "TSLA", "weight": 0.20},
                {"ticker": "NVDA", "weight": 0.50},
            ],
            "analysis_summary": {
                "one_line_diagnosis": "기술주 집중 + 변동성 높음",
            },
        },
        adjustments=[
            AdjustmentItem(
                ticker="TSLA",
                action="decrease",
                delta_weight=-0.10,
                reason_quote="TSLA 줄여줘",
            ),
            AdjustmentItem(
                ticker="JNJ",
                action="add",
                target_weight=0.15,
                reason_quote="존슨앤존슨 추가",
            ),
        ],
        user_intent="테슬라 줄이고 존슨앤존슨 추가" if with_intent else None,
    )


def test_build_prompt_contains_holdings_and_preset():
    prompt = build_e6_prompt(_sample_request())
    assert "MSFT" in prompt
    assert "TSLA" in prompt
    assert "garp" in prompt


def test_build_prompt_contains_adjustments_block():
    prompt = build_e6_prompt(_sample_request())
    # _format_adjustments_block 결과가 prompt에 들어가야 함
    assert "축소" in prompt  # decrease verb
    assert "신규 진입" in prompt  # add verb
    assert "JNJ" in prompt


def test_build_prompt_user_intent_optional():
    """user_intent 없으면 prompt에서 사용자 발화 블록 생략."""
    prompt_with = build_e6_prompt(_sample_request(with_intent=True))
    prompt_without = build_e6_prompt(_sample_request(with_intent=False))
    assert "사용자 발화" in prompt_with
    assert "사용자 발화" not in prompt_without


def test_format_adjustments_block_empty():
    """빈 adjustments 리스트 → 안내 문구."""
    out = _format_adjustments_block([])
    assert "조정 사항 없음" in out


def test_parse_e6_response_valid():
    raw = (
        '{"headline":"테스트 비교 한 줄 요약입니다",'
        '"before_summary":"조정 전 포트폴리오 핵심 특징 자연어 요약입니다.",'
        '"after_summary":"조정 후 예상 포트폴리오 핵심 특징 자연어 요약입니다.",'
        '"key_changes":[{"aspect":"allocation","description":"비중 조정 변경 사항 설명"}],'
        '"risk_assessment":"위험 변화 해설 자연어 텍스트입니다.",'
        '"closing_remarks":"마무리 해설 텍스트"}'
    )
    parsed = parse_e6_response(raw)
    assert isinstance(parsed, E6ComparisonResponse)
    assert parsed.headline.startswith("테스트")
    assert len(parsed.key_changes) == 1


def test_parse_e6_response_with_markdown_fence():
    """LLM이 반환하는 ```json...``` 펜스 사후 제거 확인."""
    raw = (
        "```json\n"
        '{"headline":"펜스 포함 응답 처리 확인용 요약입니다",'
        '"before_summary":"조정 전 포트폴리오 핵심 특징 자연어 요약입니다.",'
        '"after_summary":"조정 후 예상 포트폴리오 핵심 특징 자연어 요약입니다.",'
        '"key_changes":[{"aspect":"risk","description":"위험 차원 변경 사항 설명"}],'
        '"risk_assessment":"위험 변화 해설 자연어 텍스트입니다.",'
        '"closing_remarks":"마무리 해설 텍스트"}'
        "\n```"
    )
    parsed = parse_e6_response(raw)
    assert parsed.headline.startswith("펜스")


def test_run_e6_normal_flow_with_mock():
    """Mock client (text_strategy='e6') 정상 흐름: schema 통과 → response/metadata."""
    mock = MockLLMClient(text_strategy="e6")
    result = run_e6(_sample_request(), provider="haiku", client=mock)
    assert "response" in result and "metadata" in result
    assert result["response"]["headline"]
    assert len(result["response"]["key_changes"]) >= 1
    # PROVIDER_KWARGS["haiku"] → provider="anthropic"
    assert result["metadata"]["provider"] == "anthropic"


def test_run_e6_unknown_provider_raises():
    """등록되지 않은 provider label → ValueError."""
    with pytest.raises(ValueError, match="Unknown provider label"):
        run_e6(_sample_request(), provider="not_a_provider")  # type: ignore[arg-type]
