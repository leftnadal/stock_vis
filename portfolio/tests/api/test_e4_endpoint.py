"""Slice 13 Part 5 — POST /api/v1/coach/e4/ contract test (E5/E6 패턴 복제).

★ E4 특이점: run_e4_coach는 preset_id/metrics kwarg를 받지 않는다 → 다른 진입점의
  "kwarg 미전달 검증" 패턴을 그대로 복제하지 않는다. 함수 시그니처 자체가
  (input_data, provider, client, max_tokens)뿐이므로 mock이 받는 인자만 검증.

핵심 검증:
  - 정상 요청 → 200 + E4Output 스키마 부합 (base만)
  - 필수 필드 누락 (user_question) → 400
  - service 예외 → 500 + 스택트레이스 노출 없음
  - LLM mock 기반, real 호출 0
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from portfolio.tests.fixtures.coach.loaders import load_portfolio_a2_raw

E4_ENDPOINT = "/api/v1/coach/e4/"


# Slice 16 Step 0-B #70: api_client fixture는 conftest.py로 이전 — IsAuthenticated 통과.
@pytest.fixture
def e4_request_body() -> dict:
    """portfolio_a2 fixture에서 E4 요청 body 추출."""
    fixture = load_portfolio_a2_raw()
    return {
        "portfolio_id": fixture["portfolio_id"],
        "fetched_at": fixture["fetched_at"],
        "preset": fixture["preset"],
        "holdings": fixture["holdings"],
        **fixture["inputs"]["e4"],  # user_question, conversation_history
    }


@pytest.fixture
def mock_llm_response_e4():
    """run_e4_coach가 반환할 mock 결과 dict (E4Output 계약 부합 — base만)."""
    return {
        "output": {
            "summary": "NVDA는 PEG 1.8로 GARP 임계 초과 — 성장 대비 밸류에이션 부담.",
            "key_observations": [
                "NVDA PEG 1.8 (임계 1.5 초과)",
                "FY2025 가이던스 보수적 수정 후 EPS 추정치 하향",
            ],
            "confidence": "medium",
        },
        "llm_metadata": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "latency_ms": 1180,
            "input_tokens": 920,
            "output_tokens": 210,
            "cost_usd": 0.0016,
            "fallback_from": None,
        },
    }


# ============================================================
# 정상 경로
# ============================================================


def test_post_e4_returns_200_with_valid_request(
    api_client, e4_request_body, mock_llm_response_e4
):
    """POST /api/v1/coach/e4/ 정상 요청 → 200 + E4Output 계약 부합 (base만)."""
    with patch(
        "portfolio.api.views.run_e4_coach", return_value=mock_llm_response_e4
    ) as mock_run:
        response = api_client.post(
            E4_ENDPOINT, data=e4_request_body, format="json"
        )

    assert response.status_code == 200, response.data
    assert mock_run.call_count == 1
    # ★ E4 특이 검증: run_e4_coach는 preset_id/metrics kwarg를 받지 않음.
    # 다른 진입점처럼 "None 미전달"을 검증하지 않는다 — 시그니처 자체에 없음.
    call_kwargs = mock_run.call_args.kwargs
    assert "preset_id" not in call_kwargs, "E4 signature에 preset_id 미존재 — endpoint가 전달하면 안 됨"
    assert "metrics" not in call_kwargs, "E4 signature에 metrics 미존재 — endpoint가 전달하면 안 됨"

    data = response.json()
    assert "output" in data
    assert "llm_metadata" in data
    output = data["output"]
    # E4Output은 base만 — summary/key_observations/confidence
    assert isinstance(output["summary"], str) and output["summary"]
    assert isinstance(output["key_observations"], list)
    assert output["confidence"] in ("high", "medium", "low")
    # ★ E4Output에는 action_items/risk_flags/quoted_metrics 등 특화 필드 없음
    # (base만 사용 — extra="forbid" 정책으로 추가 필드 들어오면 schema drift)


def test_post_e4_response_passes_e4output_validation(
    api_client, e4_request_body, mock_llm_response_e4
):
    """★ contract test 핵심 — 응답 dict가 다시 E4Output(Pydantic)으로 검증 가능."""
    from portfolio.schemas.commentary_output import E4Output

    with patch(
        "portfolio.api.views.run_e4_coach", return_value=mock_llm_response_e4
    ):
        response = api_client.post(
            E4_ENDPOINT, data=e4_request_body, format="json"
        )

    output_dict = response.json()["output"]
    revalidated = E4Output(**output_dict)
    assert revalidated.summary == mock_llm_response_e4["output"]["summary"]


# ============================================================
# 검증 실패 (400)
# ============================================================


def test_post_e4_missing_required_field_returns_400(api_client, e4_request_body):
    """필수 필드 (`user_question`) 누락 → 400."""
    body = dict(e4_request_body)
    del body["user_question"]
    response = api_client.post(E4_ENDPOINT, data=body, format="json")
    assert response.status_code == 400
    data = response.json()
    assert any("user_question" in k for k in data) or "user_question" in str(data)


def test_post_e4_invalid_type_returns_400(api_client, e4_request_body):
    """잘못된 타입 (holdings를 str으로) → 400."""
    body = dict(e4_request_body)
    body["holdings"] = "not_a_list"
    response = api_client.post(E4_ENDPOINT, data=body, format="json")
    assert response.status_code == 400


def test_post_e4_non_dict_body_returns_400(api_client):
    """JSON object가 아닌 body → 400."""
    response = api_client.post(
        E4_ENDPOINT,
        data=json.dumps([1, 2, 3]),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_post_e4_invalid_provider_returns_400(api_client, e4_request_body):
    """미등록 provider query param → 400."""
    response = api_client.post(
        f"{E4_ENDPOINT}?provider=invalid_provider",
        data=e4_request_body,
        format="json",
    )
    assert response.status_code == 400
    assert "Invalid provider" in str(response.json())


# ============================================================
# Service 예외 (500, 502, 429)
# ============================================================


def test_post_e4_service_exception_returns_500_no_stacktrace(
    api_client, e4_request_body
):
    """run_e4_coach가 일반 예외 → 500 + 스택트레이스 노출 금지."""
    with patch(
        "portfolio.api.views.run_e4_coach",
        side_effect=RuntimeError("internal database error with secret /tmp/ccc"),
    ):
        response = api_client.post(
            E4_ENDPOINT, data=e4_request_body, format="json"
        )

    assert response.status_code == 500
    body_str = json.dumps(response.json())
    assert "secret" not in body_str
    assert "/tmp/ccc" not in body_str
    assert "Internal server error" in body_str


def test_post_e4_llm_budget_exceeded_returns_429(api_client, e4_request_body):
    """LLMBudgetExceededError → 429."""
    from portfolio.llm.exceptions import LLMBudgetExceededError

    with patch(
        "portfolio.api.views.run_e4_coach",
        side_effect=LLMBudgetExceededError(scope="slice", count=51, limit=50),
    ):
        response = api_client.post(
            E4_ENDPOINT, data=e4_request_body, format="json"
        )

    assert response.status_code == 429


def test_post_e4_llm_error_returns_502(api_client, e4_request_body):
    """기타 LLMError → 502."""
    from portfolio.llm.exceptions import LLMRateLimitError

    with patch(
        "portfolio.api.views.run_e4_coach",
        side_effect=LLMRateLimitError("upstream rate limit"),
    ):
        response = api_client.post(
            E4_ENDPOINT, data=e4_request_body, format="json"
        )

    assert response.status_code == 502


# ============================================================
# Schema drift 안전망
# ============================================================


def test_post_e4_service_returns_drifted_output_caught_by_serializer(
    api_client, e4_request_body, mock_llm_response_e4
):
    """★ service 응답이 E4Output 계약을 깨면 serializer가 잡아낸다."""
    drifted = dict(mock_llm_response_e4)
    drifted["output"] = dict(drifted["output"], confidence="unknown_value")
    with patch(
        "portfolio.api.views.run_e4_coach", return_value=drifted
    ):
        response = api_client.post(
            E4_ENDPOINT, data=e4_request_body, format="json"
        )
    assert response.status_code in (400, 500)
