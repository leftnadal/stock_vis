"""Slice 13 Part 4 — POST /api/v1/coach/e6/ contract test (E3 패턴 복제).

핵심 검증:
  - 정상 요청 → 200 + E6Output 스키마 부합
  - 필수 필드 누락 → 400
  - service 예외 → 500 + 스택트레이스 노출 없음
  - LLM mock 기반, real 호출 0
  - preset_id/metrics 미전달 (endpoint 표면 미노출)
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_raw


E6_ENDPOINT = "/api/v1/coach/e6/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def e6_request_body() -> dict:
    """portfolio_a2 fixture에서 E6 요청 body 추출."""
    fixture = load_portfolio_a2_raw()
    return {
        "portfolio_id": fixture["portfolio_id"],
        "fetched_at": fixture["fetched_at"],
        "preset": fixture["preset"],
        "holdings": fixture["holdings"],
        **fixture["inputs"]["e6"],  # analysis_results
    }


@pytest.fixture
def mock_llm_response_e6():
    """run_e6_coach가 반환할 mock 결과 dict (E6Output 계약 부합)."""
    return {
        "output": {
            "summary": "종목별 분석 결과 종합: 5/8 종목 매수 우위.",
            "key_observations": [
                "AAPL/MSFT 강세 신호 일치",
                "TSLA 약세 신호 다수",
            ],
            "confidence": "medium",
            "risk_flags": ["TSLA_bearish_signals"],
            "quoted_metrics": {"buy_count": 5, "sell_count": 1, "hold_count": 2},
        },
        "llm_metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1120,
            "input_tokens": 850,
            "output_tokens": 200,
            "cost_usd": 0.0014,
            "fallback_from": None,
        },
    }


# ============================================================
# 정상 경로
# ============================================================


def test_post_e6_returns_200_with_valid_request(
    api_client, e6_request_body, mock_llm_response_e6
):
    """POST /api/v1/coach/e6/ 정상 요청 → 200 + E6Output 계약 부합."""
    with patch(
        "portfolio.api.views.run_e6_coach", return_value=mock_llm_response_e6
    ) as mock_run:
        response = api_client.post(
            E6_ENDPOINT, data=e6_request_body, format="json"
        )

    assert response.status_code == 200, response.data
    assert mock_run.call_count == 1
    # ★ preset_id/metrics 미전달 검증
    call_kwargs = mock_run.call_args.kwargs
    assert "preset_id" not in call_kwargs or call_kwargs.get("preset_id") is None
    assert "metrics" not in call_kwargs or call_kwargs.get("metrics") is None

    data = response.json()
    assert "output" in data
    assert "llm_metadata" in data
    output = data["output"]
    assert isinstance(output["summary"], str) and output["summary"]
    assert isinstance(output["key_observations"], list)
    assert output["confidence"] in ("high", "medium", "low")
    assert "risk_flags" in output
    assert "quoted_metrics" in output


def test_post_e6_response_passes_e6output_validation(
    api_client, e6_request_body, mock_llm_response_e6
):
    """★ contract test 핵심 — 응답 dict가 다시 E6Output(Pydantic)으로 검증 가능."""
    from portfolio.schemas.commentary_output import E6Output

    with patch(
        "portfolio.api.views.run_e6_coach", return_value=mock_llm_response_e6
    ):
        response = api_client.post(
            E6_ENDPOINT, data=e6_request_body, format="json"
        )

    output_dict = response.json()["output"]
    revalidated = E6Output(**output_dict)
    assert revalidated.summary == mock_llm_response_e6["output"]["summary"]


# ============================================================
# 검증 실패 (400)
# ============================================================


def test_post_e6_missing_required_field_returns_400(api_client, e6_request_body):
    """필수 필드 (`analysis_results`) 누락 → 400."""
    body = dict(e6_request_body)
    del body["analysis_results"]
    response = api_client.post(E6_ENDPOINT, data=body, format="json")
    assert response.status_code == 400
    data = response.json()
    assert any("analysis_results" in k for k in data) or "analysis_results" in str(data)


def test_post_e6_invalid_type_returns_400(api_client, e6_request_body):
    """잘못된 타입 (holdings를 str으로) → 400."""
    body = dict(e6_request_body)
    body["holdings"] = "not_a_list"
    response = api_client.post(E6_ENDPOINT, data=body, format="json")
    assert response.status_code == 400


def test_post_e6_non_dict_body_returns_400(api_client):
    """JSON object가 아닌 body → 400."""
    response = api_client.post(
        E6_ENDPOINT,
        data=json.dumps([1, 2, 3]),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_post_e6_invalid_provider_returns_400(api_client, e6_request_body):
    """미등록 provider query param → 400."""
    response = api_client.post(
        f"{E6_ENDPOINT}?provider=invalid_provider",
        data=e6_request_body,
        format="json",
    )
    assert response.status_code == 400
    assert "Invalid provider" in str(response.json())


# ============================================================
# Service 예외 (500, 502, 429)
# ============================================================


def test_post_e6_service_exception_returns_500_no_stacktrace(
    api_client, e6_request_body
):
    """run_e6_coach가 일반 예외 → 500 + 스택트레이스 노출 금지."""
    with patch(
        "portfolio.api.views.run_e6_coach",
        side_effect=RuntimeError("internal database error with secret /tmp/bbb"),
    ):
        response = api_client.post(
            E6_ENDPOINT, data=e6_request_body, format="json"
        )

    assert response.status_code == 500
    body_str = json.dumps(response.json())
    assert "secret" not in body_str
    assert "/tmp/bbb" not in body_str
    assert "Internal server error" in body_str


def test_post_e6_llm_budget_exceeded_returns_429(api_client, e6_request_body):
    """LLMBudgetExceededError → 429."""
    from portfolio.llm.exceptions import LLMBudgetExceededError

    with patch(
        "portfolio.api.views.run_e6_coach",
        side_effect=LLMBudgetExceededError(scope="slice", count=51, limit=50),
    ):
        response = api_client.post(
            E6_ENDPOINT, data=e6_request_body, format="json"
        )

    assert response.status_code == 429


def test_post_e6_llm_error_returns_502(api_client, e6_request_body):
    """기타 LLMError → 502."""
    from portfolio.llm.exceptions import LLMRateLimitError

    with patch(
        "portfolio.api.views.run_e6_coach",
        side_effect=LLMRateLimitError("upstream rate limit"),
    ):
        response = api_client.post(
            E6_ENDPOINT, data=e6_request_body, format="json"
        )

    assert response.status_code == 502


# ============================================================
# Schema drift 안전망
# ============================================================


def test_post_e6_service_returns_drifted_output_caught_by_serializer(
    api_client, e6_request_body, mock_llm_response_e6
):
    """★ service 응답이 E6Output 계약을 깨면 serializer가 잡아낸다."""
    drifted = dict(mock_llm_response_e6)
    drifted["output"] = dict(drifted["output"], confidence="unknown_value")
    with patch(
        "portfolio.api.views.run_e6_coach", return_value=drifted
    ):
        response = api_client.post(
            E6_ENDPOINT, data=e6_request_body, format="json"
        )
    assert response.status_code in (400, 500)
