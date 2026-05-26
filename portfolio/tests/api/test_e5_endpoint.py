"""Slice 13 Part 4 — POST /api/v1/coach/e5/ contract test (E3 패턴 복제).

★ E5는 TimeSeriesContext(#27) 사용 가능한 유일한 진입점 — Optional 필드라 fixture에서 선택적 처리.

핵심 검증:
  - 정상 요청 → 200 + E5Output 스키마 부합
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


E5_ENDPOINT = "/api/v1/coach/e5/"


# Slice 16 Step 0-B #70: api_client fixture는 conftest.py로 이전 — IsAuthenticated 통과.
@pytest.fixture
def e5_request_body() -> dict:
    """portfolio_a2 fixture에서 E5 요청 body 추출."""
    fixture = load_portfolio_a2_raw()
    return {
        "portfolio_id": fixture["portfolio_id"],
        "fetched_at": fixture["fetched_at"],
        "preset": fixture["preset"],
        "holdings": fixture["holdings"],
        **fixture["inputs"]["e5"],  # extraction_targets, time_series_context
    }


@pytest.fixture
def mock_llm_response_e5():
    """run_e5_coach가 반환할 mock 결과 dict (E5Output 계약 부합)."""
    return {
        "output": {
            "summary": "추출 대상 3종 (per, peg, roe) 산출 완료.",
            "key_observations": [
                "PER 25 — 시장 평균 20보다 25% 높음",
                "PEG 1.3 — GARP 임계 1.5 이하",
            ],
            "confidence": "high",
            "action_items": [],
            "quoted_metrics": {"per": 25, "peg": 1.3, "roe": 0.18},
        },
        "llm_metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1050,
            "input_tokens": 700,
            "output_tokens": 150,
            "cost_usd": 0.0009,
            "fallback_from": None,
        },
    }


# ============================================================
# 정상 경로
# ============================================================


def test_post_e5_returns_200_with_valid_request(
    api_client, e5_request_body, mock_llm_response_e5
):
    """POST /api/v1/coach/e5/ 정상 요청 → 200 + E5Output 계약 부합."""
    with patch(
        "portfolio.api.views.run_e5_coach", return_value=mock_llm_response_e5
    ) as mock_run:
        response = api_client.post(
            E5_ENDPOINT, data=e5_request_body, format="json"
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
    assert "action_items" in output
    assert "quoted_metrics" in output


def test_post_e5_response_passes_e5output_validation(
    api_client, e5_request_body, mock_llm_response_e5
):
    """★ contract test 핵심 — 응답 dict가 다시 E5Output(Pydantic)으로 검증 가능."""
    from portfolio.schemas.commentary_output import E5Output

    with patch(
        "portfolio.api.views.run_e5_coach", return_value=mock_llm_response_e5
    ):
        response = api_client.post(
            E5_ENDPOINT, data=e5_request_body, format="json"
        )

    output_dict = response.json()["output"]
    revalidated = E5Output(**output_dict)
    assert revalidated.summary == mock_llm_response_e5["output"]["summary"]


# ============================================================
# 검증 실패 (400)
# ============================================================


def test_post_e5_missing_required_field_returns_400(api_client, e5_request_body):
    """필수 필드 (`extraction_targets`) 누락 → 400."""
    body = dict(e5_request_body)
    del body["extraction_targets"]
    response = api_client.post(E5_ENDPOINT, data=body, format="json")
    assert response.status_code == 400


def test_post_e5_invalid_type_returns_400(api_client, e5_request_body):
    """잘못된 타입 (holdings를 str으로) → 400."""
    body = dict(e5_request_body)
    body["holdings"] = "not_a_list"
    response = api_client.post(E5_ENDPOINT, data=body, format="json")
    assert response.status_code == 400


def test_post_e5_non_dict_body_returns_400(api_client):
    """JSON object가 아닌 body → 400."""
    response = api_client.post(
        E5_ENDPOINT,
        data=json.dumps([1, 2, 3]),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_post_e5_invalid_provider_returns_400(api_client, e5_request_body):
    """미등록 provider query param → 400."""
    response = api_client.post(
        f"{E5_ENDPOINT}?provider=invalid_provider",
        data=e5_request_body,
        format="json",
    )
    assert response.status_code == 400
    assert "Invalid provider" in str(response.json())


# ============================================================
# Service 예외 (500, 502, 429)
# ============================================================


def test_post_e5_service_exception_returns_500_no_stacktrace(
    api_client, e5_request_body
):
    """run_e5_coach가 일반 예외 → 500 + 스택트레이스 노출 금지."""
    with patch(
        "portfolio.api.views.run_e5_coach",
        side_effect=RuntimeError("internal database error with secret /tmp/aaa"),
    ):
        response = api_client.post(
            E5_ENDPOINT, data=e5_request_body, format="json"
        )

    assert response.status_code == 500
    body_str = json.dumps(response.json())
    assert "secret" not in body_str
    assert "/tmp/aaa" not in body_str
    assert "Internal server error" in body_str


def test_post_e5_llm_budget_exceeded_returns_429(api_client, e5_request_body):
    """LLMBudgetExceededError → 429."""
    from portfolio.llm.exceptions import LLMBudgetExceededError

    with patch(
        "portfolio.api.views.run_e5_coach",
        side_effect=LLMBudgetExceededError(scope="slice", count=51, limit=50),
    ):
        response = api_client.post(
            E5_ENDPOINT, data=e5_request_body, format="json"
        )

    assert response.status_code == 429


def test_post_e5_llm_error_returns_502(api_client, e5_request_body):
    """기타 LLMError → 502."""
    from portfolio.llm.exceptions import LLMRateLimitError

    with patch(
        "portfolio.api.views.run_e5_coach",
        side_effect=LLMRateLimitError("upstream rate limit"),
    ):
        response = api_client.post(
            E5_ENDPOINT, data=e5_request_body, format="json"
        )

    assert response.status_code == 502


# ============================================================
# Schema drift 안전망
# ============================================================


def test_post_e5_service_returns_drifted_output_caught_by_serializer(
    api_client, e5_request_body, mock_llm_response_e5
):
    """★ service 응답이 E5Output 계약을 깨면 serializer가 잡아낸다."""
    drifted = dict(mock_llm_response_e5)
    drifted["output"] = dict(drifted["output"], confidence="unknown_value")
    with patch(
        "portfolio.api.views.run_e5_coach", return_value=drifted
    ):
        response = api_client.post(
            E5_ENDPOINT, data=e5_request_body, format="json"
        )
    assert response.status_code in (400, 500)
